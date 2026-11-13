---
id: ai-bulut-02
title: "Bedrock Tarzı IAM · Explicit Deny ve Kaynak Kapsamı"
summary: Varsayılan ret, açık Deny'ın Allow'u ezmesi ve kaynak kapsamını yerel bir politika değerlendiricisiyle kur; çağrı kayıtlarından kullanılmayan izinleri bularak en az ayrıcalığa yaklaş.
esleme: ai-savunma-11, ai-temel-24, ai-saldiri-19, ai-bulut-01
timeout: 30
---

::: anlat 1. Değerlendirme mantığı: üç kural
AWS IAM belgesi bir isteğin nasıl karara bağlandığını birkaç cümleyle özetler: *"By default, all requests are implicitly denied"* ve *"An explicit deny overrides an explicit allow."* Bunlardan çıkan üç kural, Bedrock dahil her AWS hizmetinde aynıdır:

1. **Varsayılan ret.** Hiçbir kural eşleşmezse istek reddedilir. "Yasaklayan kural yok" ile "izin veren kural var" aynı şey değildir.
2. **Açık Deny her şeyi ezer.** Eşleşen tek bir `Deny`, kaç tane `Allow` olursa olsun isteği reddeder. Sıra önemli değildir.
3. **İzin, eylem ve kaynakla birlikte eşleşir.** `bedrock:InvokeModel` eylemine izin vermek tek başına anlamsızdır; hangi modele (`Resource`) izin verildiği de eşleşmelidir.

Bedrock için AWS Güvenlik Blogu'ndaki *Implementing least privilege access for Amazon Bedrock* yazısı (Jenkyn ve Tschannen, Şubat 2025) bu mantığın üzerine bir öneri kurar: izinleri model seçimi, uyarlama, test ve işletim aşamalarına göre daraltmak ve izinli modelleri açık bir liste olarak tutmak. `"Action": "bedrock:*", "Resource": "*"` gibi bir kural, ekip yalnız tek bir modeli çağırırken bile hesaptaki bütün modelleri, ince ayar ve günlük yapılandırma işlemlerini açar.

> [!NOTE]
> Bu dersteki değerlendirici gerçek IAM'in **küçük ve sentetik** bir alt kümesidir: yalnız `Effect`, `Action`, `Resource`; joker karakterler Python `fnmatchcase` ile eşleşir. Gerçek IAM'in `Condition`, `NotAction`, kaynak tabanlı politika, SCP ve oturum politikası katmanları yoktur. Gerçek hesap ya da ağ çağrısı yoktur.
:::

::: anlat 2. Mekanizma: neden "ilk eşleşen kazanır" yanlıştır?
Güvenlik duvarı kurallarından gelen alışkanlıkla birçok kişi politikayı yukarıdan aşağı okuyup ilk eşleşen kuralda durur. IAM öyle çalışmaz. Değerlendirici bütün kuralları tarar. Bir `Deny` eşleşirse sonuç ret olur; hiç `Deny` eşleşmez ve en az bir `Allow` eşleşirse sonuç izin olur.

Bu sırasızlık güvenlik açısından bir özelliktir. Kurum çapında bir yasak (ör. "üretim modeline hiç kimse ince ayar yapamaz") bir `Deny` olarak yazılır. Sonra kim hangi geniş `Allow`'u eklerse eklesin yasak delinmez.

Joker karakterler ikinci tuzaktır. `bedrock:Invoke*` hem `InvokeModel` hem `InvokeModelWithResponseStream` eylemini kapsar; beklenen budur. Ama `model/*` kaynağı `model/uretim-gizli` modelini de kapsar. Joker ne kadar erken yerdeyse o kadar çok şey açar.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| İlk eşleşen kuralda durmak | `Allow` önce yazılmışsa sonraki `Deny` hiç uygulanmaz | Bütün kuralları tara; eşleşen `Deny` her zaman kazanır |
| Eşleşen kural yoksa izin vermek | Yasak yazılmamış her şey açılır | Varsayılan ret: `Allow` yoksa `False` |
| Yalnız eylemi eşleştirmek | `InvokeModel` izni bütün modellere yayılır | Eylem **ve** kaynak birlikte eşleşmeli |
| Bilinmeyen `Effect` ya da ek alanı yok saymak | `"Effect": "allow"` ya da tanınmayan `Condition` sessizce farklı anlam kazanır | Şema dışı kural `ValueError` |
:::

::: tahmin Sıra değişince sonuç değişir mi?
Aynı iki kural iki farklı sırayla veriliyor. Gerçek IAM mantığıyla değerlendiren `iam` ile "ilk eşleşen kazanır" diyen `ilk_eslesen` ne döndürür?

```python
from fnmatch import fnmatchcase

def eslesir(k, a, r):
    return fnmatchcase(a, k['Action']) and fnmatchcase(r, k['Resource'])

def ilk_eslesen(kurallar, a, r):
    for k in kurallar:
        if eslesir(k, a, r):
            return k['Effect'] == 'Allow'
    return False

def iam(kurallar, a, r):
    es = [k for k in kurallar if eslesir(k, a, r)]
    return bool(es) and all(k['Effect'] == 'Allow' for k in es)

allow = {'Effect': 'Allow', 'Action': 'bedrock:*', 'Resource': '*'}
deny = {'Effect': 'Deny', 'Action': 'bedrock:InvokeModel', 'Resource': 'model/gizli'}
for sira in ([allow, deny], [deny, allow]):
    print(ilk_eslesen(sira, 'bedrock:InvokeModel', 'model/gizli'), iam(sira, 'bedrock:InvokeModel', 'model/gizli'))
```

???

```cikti
True False
False False
```
"İlk eşleşen" değerlendiricinin kararı kuralların yazılış sırasına bağlıdır: geniş `Allow` önce yazılınca gizli model açılır. IAM mantığında sıra önemsizdir; eşleşen `Deny` iki durumda da kazanır.
:::

::: gorev 1 · Explicit Deny ve varsayılan reddi uygula
`iam_izin(statements, action, resource)` işlevini yaz.

- `statements` bir `list`; her kural tam olarak `{'Effect', 'Action', 'Resource'}` anahtarlarını taşıyan bir `dict`'tir. `Effect` `'Allow'` ya da `'Deny'`; `Action` ve `Resource` `str`. Eksik ya da fazla anahtar (ör. `Condition`), bilinmeyen `Effect` (büyük/küçük harf dahil) ya da `str` olmayan alan `ValueError`.
- `action` ve `resource` `str` değilse `ValueError`.
- Eşleşme: `fnmatchcase(action, kural['Action']) and fnmatchcase(resource, kural['Resource'])`.
- Karar: eşleşen bir `Deny` varsa `False`; yoksa en az bir `Allow` eşleşiyorsa `True`; hiçbir kural eşleşmiyorsa `False`.
- Bozuk bir kural, eşleşmeden **önce** reddedilir: listedeki herhangi bir kural bozuksa, istek hangi kurala uyarsa uysun `ValueError`.

KUSURLU başlangıç ilk eşleşen kuralda duruyor ve yalnız eylemi eşleştiriyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[[{"Effect": "Allow", "Action": "bedrock:*", "Resource": "*"}, {"Effect": "Deny", "Action": "bedrock:InvokeModel", "Resource": "model/gizli"}], "bedrock:InvokeModel", "model/gizli"]', encoding='utf-8')
```

```starter
from fnmatch import fnmatchcase

def iam_izin(statements, action, resource):
    for s in statements:
        if fnmatchcase(action, s['Action']):
            return s['Effect'] == 'Allow'
    return False

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(iam_izin(*_args))
```

```solution
from fnmatch import fnmatchcase

_ANAHTARLAR = {'Effect', 'Action', 'Resource'}

def iam_izin(statements, action, resource):
    if not isinstance(statements, list) or not isinstance(action, str) or not isinstance(resource, str):
        raise ValueError('statements list, action ve resource str olmali')
    for s in statements:
        if (not isinstance(s, dict) or set(s) != _ANAHTARLAR or s['Effect'] not in ('Allow', 'Deny')
                or not isinstance(s['Action'], str) or not isinstance(s['Resource'], str)):
            raise ValueError('bozuk kural')
    izin = False
    for s in statements:
        if fnmatchcase(action, s['Action']) and fnmatchcase(resource, s['Resource']):
            if s['Effect'] == 'Deny':
                return False
            izin = True
    return izin

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(iam_izin(*_args))
```

```test
need('iam_izin')
import copy
_A = lambda a, r: {'Effect': 'Allow', 'Action': a, 'Resource': r}
_D = lambda a, r: {'Effect': 'Deny', 'Action': a, 'Resource': r}
_pol = [_A('bedrock:Invoke*', 'model/*'), _D('bedrock:InvokeModel', 'model/gizli'), _A('bedrock:Retrieve', 'kb/ekip')]
_yedek = copy.deepcopy(_pol)
eq(iam_izin(_pol, 'bedrock:InvokeModel', 'model/acik'), True, 'joker Allow ile eşleşen istek izinli')
eq(iam_izin(_pol, 'bedrock:InvokeModelWithResponseStream', 'model/acik'), True, 'Invoke* akışlı çağrıyı da kapsar')
eq(iam_izin(_pol, 'bedrock:InvokeModel', 'model/gizli'), False, 'eşleşen Deny Allow\'u ezer')
eq(iam_izin(list(reversed(_pol)), 'bedrock:InvokeModel', 'model/gizli'), False, 'sıra değişse de Deny kazanır')
eq(iam_izin(_pol, 'bedrock:InvokeModelWithResponseStream', 'model/gizli'), True, 'Deny yalnız kendi eylemini kapsar')
eq(iam_izin(_pol, 'bedrock:Retrieve', 'kb/ekip'), True, 'ikinci Allow da çalışır')
eq(iam_izin(_pol, 'bedrock:Retrieve', 'kb/baska'), False, 'eylem eşleşse de kaynak eşleşmezse ret')
eq(iam_izin(_pol, 'bedrock:CreateModelCustomizationJob', 'model/acik'), False, 'kaynak eşleşse de eylem eşleşmezse ret')
eq(iam_izin([], 'bedrock:InvokeModel', 'model/acik'), False, 'kural yoksa varsayılan ret')
eq(iam_izin([_D('*', '*')], 'bedrock:InvokeModel', 'model/acik'), False, 'yalnız Deny varsa ret')
eq(iam_izin([_A('bedrock:invokemodel', '*')], 'bedrock:InvokeModel', 'model/acik'), False, 'bu sözleşmede eşleşme büyük/küçük harfe duyarlı')
eq(_pol, _yedek, 'politika değişmemeli')

for _bozuk in (
    [{'Effect': 'allow', 'Action': '*', 'Resource': '*'}],
    [{'Effect': 'Allow', 'Action': '*'}],
    [{'Effect': 'Allow', 'Action': '*', 'Resource': '*', 'Condition': {}}],
    [{'Effect': 'Allow', 'Action': ['bedrock:InvokeModel'], 'Resource': '*'}],
    [{'Effect': 'Allow', 'Action': '*', 'Resource': None}],
    ['Allow * *'],
    [['Effect', 'Action', 'Resource']],
    [_A('*', '*'), {'Effect': 'Audit', 'Action': 'x', 'Resource': 'y'}],
):
    raises(ValueError, iam_izin, _bozuk, 'bedrock:InvokeModel', 'model/acik', msg=f'bozuk kural ValueError: {_bozuk!r}')
for _ust in ((tuple(_pol), 'bedrock:InvokeModel', 'model/acik'), (_pol, None, 'model/acik'), (_pol, 'bedrock:InvokeModel', 5)):
    raises(ValueError, iam_izin, *_ust, msg=f'bozuk üst argüman ValueError: {_ust[1:]!r}')
```

```hint
İki geçiş yap: önce bütün kuralları doğrula, sonra eşleşenleri tara. Eşleşen `Deny` görünce hemen `False` dön; `Allow` görünce yalnız bir bayrak kaldır ve taramaya devam et.
```
:::

::: gorev 2 · Çağrı kayıtlarından kullanılmayan izinleri bul
En az ayrıcalığa yaklaşmanın pratik yolu, verilen izinleri gerçekten kullanılan izinlerle karşılaştırmaktır. `izin_incelemesi(statements, istekler)` işlevini yaz.

- `statements` görev 1'deki şemaya uyar; bozuksa `ValueError`.
- `istekler` bir `list`; her öğe `[action, resource]` (`list` ya da `tuple`, iki `str`). Değilse `ValueError`.
- Her istek görev 1'in kuralıyla değerlendirilir.
- Dönüş:
  - `'izinli'`: izin verilen istek sayısı (`int`);
  - `'reddedilen'`: reddedilen isteklerin `[action, resource]` listesi, girdi sırasıyla (`list` olarak);
  - `'kullanilmayan_allow'`: hiçbir **izinli** istekle eşleşmeyen `Allow` kurallarının `statements` içindeki indeksleri, artan sırayla. Bir `Allow` yalnız reddedilen (çünkü bir `Deny` ezdi) isteklerle eşleşmişse o da kullanılmamış sayılır.

KUSURLU başlangıç `Deny`'ı yok sayıyor ve bir `Allow`'u herhangi bir istekle eşleştiği anda kullanılmış sayıyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
from fnmatch import fnmatchcase

def izin_incelemesi(statements, istekler):
    kullanilan = set()
    reddedilen = []
    for a, r in istekler:
        es = [i for i, s in enumerate(statements) if fnmatchcase(a, s['Action']) and fnmatchcase(r, s['Resource'])]
        if es:
            kullanilan.update(es)
        else:
            reddedilen.append([a, r])
    return {
        'izinli': len(istekler) - len(reddedilen),
        'reddedilen': reddedilen,
        'kullanilmayan_allow': [i for i, s in enumerate(statements) if s['Effect'] == 'Allow' and i not in kullanilan],
    }
```

```solution
from fnmatch import fnmatchcase

_ANAHTARLAR = {'Effect', 'Action', 'Resource'}

def izin_incelemesi(statements, istekler):
    if not isinstance(statements, list) or not isinstance(istekler, list):
        raise ValueError('statements ve istekler list olmali')
    for s in statements:
        if (not isinstance(s, dict) or set(s) != _ANAHTARLAR or s['Effect'] not in ('Allow', 'Deny')
                or not isinstance(s['Action'], str) or not isinstance(s['Resource'], str)):
            raise ValueError('bozuk kural')
    for ist in istekler:
        if not isinstance(ist, (list, tuple)) or len(ist) != 2 or not all(isinstance(x, str) for x in ist):
            raise ValueError('her istek [action, resource] olmali')
    kullanilan = set()
    izinli = 0
    reddedilen = []
    for a, r in istekler:
        eslesen = [i for i, s in enumerate(statements)
                   if fnmatchcase(a, s['Action']) and fnmatchcase(r, s['Resource'])]
        if eslesen and all(statements[i]['Effect'] == 'Allow' for i in eslesen):
            izinli += 1
            kullanilan.update(eslesen)
        else:
            reddedilen.append([a, r])
    return {
        'izinli': izinli,
        'reddedilen': reddedilen,
        'kullanilmayan_allow': [i for i, s in enumerate(statements)
                                if s['Effect'] == 'Allow' and i not in kullanilan],
    }
```

```test
need('izin_incelemesi')
import copy
_A = lambda a, r: {'Effect': 'Allow', 'Action': a, 'Resource': r}
_D = lambda a, r: {'Effect': 'Deny', 'Action': a, 'Resource': r}
_pol = [
    _A('bedrock:InvokeModel', 'model/ozet'),
    _A('bedrock:*', '*'),
    _D('bedrock:InvokeModel', 'model/gizli'),
    _A('bedrock:Retrieve', 'kb/ekip'),
    _A('bedrock:InvokeModel', 'model/gizli'),
]
_kayit = [
    ['bedrock:InvokeModel', 'model/ozet'],
    ('bedrock:InvokeModel', 'model/ozet'),
    ['bedrock:InvokeModel', 'model/gizli'],
    ['bedrock:Retrieve', 'kb/ekip'],
]
_yedek = copy.deepcopy((_pol, _kayit))
eq(izin_incelemesi(_pol, _kayit), {
    'izinli': 3,
    'reddedilen': [['bedrock:InvokeModel', 'model/gizli']],
    'kullanilmayan_allow': [4],
}, 'Deny ile ezilen Allow (4) kullanılmamış sayılır; geniş bedrock:* (1) izinli isteklerle kullanıldı')
eq((_pol, _kayit), _yedek, 'girdiler değişmemeli')
eq(izin_incelemesi(_pol[:1] + _pol[2:], [['bedrock:Retrieve', 'kb/ekip'], ['bedrock:DeleteKnowledgeBase', 'kb/ekip']]), {
    'izinli': 1, 'reddedilen': [['bedrock:DeleteKnowledgeBase', 'kb/ekip']], 'kullanilmayan_allow': [0, 3],
}, 'yalnız kaynağı eşleşen istek reddedilir; kullanılmayan Allow indeksleri artan sırada')
eq(izin_incelemesi([], [['bedrock:InvokeModel', 'model/ozet']]), {
    'izinli': 0, 'reddedilen': [['bedrock:InvokeModel', 'model/ozet']], 'kullanilmayan_allow': [],
}, 'kural yoksa her istek varsayılan retle reddedilir')
eq(izin_incelemesi(_pol, []), {'izinli': 0, 'reddedilen': [], 'kullanilmayan_allow': [0, 1, 3, 4]},
   'hiç istek yoksa bütün Allow kuralları kullanılmamış')

for _bozuk in (
    (tuple(_pol), _kayit),
    (_pol, tuple(_kayit)),
    ([{'Effect': 'Allow', 'Action': '*'}], _kayit),
    ([{'Effect': 'Allow', 'Action': '*', 'Resource': '*', 'Condition': {}}], _kayit),
    ([{'Effect': 'Permit', 'Action': '*', 'Resource': '*'}], _kayit),
    ([{'Effect': 'Allow', 'Action': 5, 'Resource': '*'}], _kayit),
    ([{'Effect': 'Allow', 'Action': '*', 'Resource': 5}], _kayit),
    (['kural'], _kayit),
    ([['Effect', 'Action', 'Resource']], _kayit),
    (_pol, [['bedrock:InvokeModel']]),
    (_pol, [['bedrock:InvokeModel', 'model/ozet', 'ek']]),
    (_pol, [['bedrock:InvokeModel', 5]]),
    (_pol, ['bedrock:InvokeModel model/ozet']),
    (_pol, [{'bedrock:InvokeModel': 1, 'model/ozet': 2}]),
):
    raises(ValueError, izin_incelemesi, *_bozuk, msg=f'bozuk girdi ValueError: {_bozuk!r}')
```

```hint
Her istek için eşleşen kuralların indekslerini topla. İstek ancak eşleşen kümede `Allow` varsa ve hiç `Deny` yoksa izinlidir; yalnız o durumda eşleşen `Allow`'ları "kullanıldı" diye işaretle.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Üç kural (25 sn).** "IAM'de varsayılan ret vardır, açık Deny her Allow'u ezer ve izin eylemle kaynak birlikte eşleştiğinde verilir."
2. **Sıra tuzağı (30 sn).** "İlk eşleşen kuralda duran bir değerlendirici, geniş bir Allow'u Deny'dan önce yazınca gizli modeli açıyordu. Bütün kuralları tarayınca sıra önemini yitirdi."
3. **Kanıt (30 sn).** "Testte Invoke* jokerinin akışlı çağrıyı da kapsadığını, Deny'ın ise yalnız kendi eylemini kestiğini gösterdim."
4. **En az ayrıcalık (25 sn).** "Çağrı kayıtlarını politikaya karşı koşup hiç kullanılmayan Allow'ları listeledim. Bir Deny tarafından ezilen Allow da bu listeye girer; silinmesi bir şeyi bozmaz."
5. **Sınır (10 sn).** "Değerlendirici yalnız Effect/Action/Resource modelliyor; Condition ve kaynak politikaları kapsam dışı."
:::

::: anlat Sınır ve kaynak
Python `fnmatchcase` gerçek IAM eşleştiricisi değildir. `[abc]` gibi karakter sınıflarını da yorumlar ve bu sözleşmede eylem adı büyük/küçük harfe duyarlıdır. Gerçek IAM'in eylem ve ARN eşleme kuralları, `Condition` anahtarları, `NotAction`/`NotResource`, kaynak tabanlı politikalar, SCP'ler ve oturum politikaları bu derste yoktur. Kullanılmayan izin analizi yalnız verilen kayıt penceresi kadar doğrudur: nadiren çalışan bir iş (ör. ayda bir ince ayar) kısa bir pencerede "kullanılmamış" görünür.

- Birincil kaynaklar: [AWS IAM — Policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html) ve [How AWS enforcement code logic evaluates requests to allow or deny access](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic_policy-eval-denyallow.html) (varsayılan ret, açık Deny'ın üstünlüğü); [AWS Security Blog — Implementing least privilege access for Amazon Bedrock (Jenkyn ve Tschannen, Şubat 2025)](https://aws.amazon.com/blogs/security/implementing-least-privilege-access-for-amazon-bedrock/). Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
`kullanilmayan_allow` listesinde `bedrock:*` gibi geniş bir kural yoksa ama izinli isteklerin hepsi o geniş kuralla da eşleşiyorsa, hangi dar kuralları yazıp geniş olanı silersin? Kayıt penceresi kısa olduğunda bu kararı nasıl riske atmadan verirsin?
:::

::: ozet
- IAM'de varsayılan ret vardır; eşleşen açık `Deny` sıradan bağımsız olarak her `Allow`'u ezer.
- İzin için eylem ve kaynak birlikte eşleşmelidir; joker ne kadar erken yerdeyse o kadar çok şey açar.
- Şema dışı kural sessizce yorumlanmaz, reddedilir.
- Çağrı kayıtlarını politikaya karşı koşmak kullanılmayan izinleri gösterir; karar kayıt penceresinin temsil gücüyle sınırlıdır.
:::
