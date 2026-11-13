---
id: ai-bulut-05
title: "Cloud RAG · Tenant Yalıtımı ve Nesne Kapsamı"
summary: Çok kiracılı RAG'de kiracı filtresini benzerlik sıralamasından önce uygula, nesne anahtarı kapsamını yol geçişine karşı denetle ve sorgu kayıtlarından kiracılar arası sızıntıyı ölç.
esleme: ai-savunma-19, ai-temel-24, ai-temel-21, ai-bulut-07
timeout: 30
---

::: anlat 1. Çok kiracılı bilgi tabanında sızıntı nereden çıkar?
Bir SaaS ürünü birden çok müşterinin (kiracının, *tenant*) belgelerini tek bir vektör deposunda tutabilir. Kullanıcı soru sorduğunda sistem en benzer parçaları getirir ve modele bağlam olarak verir. OWASP'ın LLM08:2025 maddesi (*Vector and Embedding Weaknesses*) bu yapının ilk riskini *Cross-Context Information Leaks* olarak adlandırır: bir kiracının sorusu başka bir kiracının belgesini getirirse, model o belgeyi okur ve yanıtına taşır. Aynı madde savunma olarak izin farkında (*permission-aware*) vektör depoları önerir.

Amazon Bedrock Knowledge Bases belgesi bunun için *metadata filtering* sunar: sorgu, belgelerin alanlarına (ör. `tenant`) uygulanan bir süzgeçle sınırlandırılır. Ama hangi değerle süzüleceği uygulamanın kararıdır. Kiracı kimliği kullanıcının yazdığı metinden ya da modelin ürettiği bir parametreden değil, **doğrulanmış oturumdan** gelmelidir.

> [!NOTE]
> Bu dersteki kayıtlar, skorlar ve nesne anahtarları **sentetiktir**; gömme hesaplanmaz, gerçek bir vektör deposu ya da bulut hizmeti çağrılmaz.
:::

::: anlat 2. Mekanizma: süzgeç sıralamadan önce mi, sonra mı?
Benzerlik araması en yüksek skorlu `k` kaydı döndürür. Süzgeç iki yere konabilir:

- **Önce süz, sonra sırala:** yalnız kiracının kayıtları arasından en iyi `k` seçilir. Başka kiracının kaydı hiçbir koşulda listeye giremez.
- **Önce sırala, sonra süz:** bütün depodan en iyi `k` alınır, sonra kiracıya ait olmayanlar atılır. Bu hem eksik sonuç verir (diğer kiracının belgeleri ilk `k`'yı doldurmuşsa kiracıya hiç sonuç kalmaz) hem de süzgeç unutulduğu ya da yanlış yerde uygulandığı anda doğrudan sızıntıya dönüşür.

İkinci kapsam katmanı nesne anahtarıdır. Belge `musteri-a/raporlar/q3.pdf` gibi bir anahtarla saklanıyorsa, kaydın `tenant` alanı doğru olsa bile anahtarın `musteri-a/` ile başladığı ayrıca denetlenir. `musteri-a/../musteri-b/gizli.pdf` gibi bir anahtar, önek kontrolünü geçip başka kiracının nesnesine işaret eder. Ayrıca `musteri-ab/...` anahtarı `musteri-a` önekiyle başlar ama başka bir kiracıdır; bu yüzden öneki `/` ile birlikte denetlemek gerekir.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| Önce ilk `k`'yı al, sonra süz | Sonuç eksik kalır; süzgeç atlanırsa sızıntı olur | Kiracı süzgecini sıralamadan önce uygula |
| Kiracıyı istem metninden almak | "Ben musteri-b'yim" diyen kullanıcı başka kiracıya geçer | Kiracı doğrulanmış oturumdan gelir |
| `key.startswith(tenant)` | `musteri-ab/` anahtarı `musteri-a` kiracısına uyar | `startswith(tenant + '/')` |
| `..` bölümünü yok saymak | `musteri-a/../musteri-b/` öneki geçer, başka nesneye işaret eder | `..` içeren anahtarı reddet |
| Eşit skorda sırayı belirsiz bırakmak | Aynı sorgu farklı çalıştırmada farklı bağlam üretir | Eşitlikte kimliğe göre kararlı sıra |
:::

::: tahmin Önce sırala, sonra süz
İki kiracının kayıtları tek depoda. `musteri-a` için `k = 2` sonuç isteniyor. İki sıralamanın çıktısını tahmin et.

```python
kayit = [
    {'id': 'b1', 'tenant': 'musteri-b', 'score': 0.95},
    {'id': 'b2', 'tenant': 'musteri-b', 'score': 0.90},
    {'id': 'a1', 'tenant': 'musteri-a', 'score': 0.70},
    {'id': 'a2', 'tenant': 'musteri-a', 'score': 0.60},
]
sirali = sorted(kayit, key=lambda r: -r['score'])
sonra_suz = [r['id'] for r in sirali[:2] if r['tenant'] == 'musteri-a']
once_suz = [r['id'] for r in sirali if r['tenant'] == 'musteri-a'][:2]
print('sonra süz:', sonra_suz)
print('önce süz :', once_suz)
```

???

```cikti
sonra süz: []
önce süz : ['a1', 'a2']
```
Başka kiracının iki yüksek skorlu kaydı ilk `k`'yı doldurdu; sonradan süzmek `musteri-a`'ya hiç bağlam bırakmadı. Bu örnekte sonuç yalnız eksik kaldı. Ama aynı kod süzgeç adımını atlarsa, modele doğrudan `b1` ve `b2` gider.
:::

::: gorev 1 · Kiracıya göre süz, kapsamı denetle, sonra sırala
`tenant_sec(kayitlar, tenant, k)` işlevini yaz.

- `kayitlar` bir `list`; `tenant` boş olmayan bir `str`; `k` `bool` olmayan pozitif bir `int`. Değilse `ValueError`.
- Her kayıt `{'id': str, 'tenant': str, 'key': str, 'score': int | float}`. `id`, `tenant`, `key` boş olmayan `str` olmalı; `score` `bool` olmayan, sonlu (`math.isfinite`) bir `int` ya da `float` olmalı; `id` tekrar etmemeli. Tek bir bozuk kayıt bütün çağrıyı `ValueError` ile durdurur.
- Seçim: `kayit['tenant'] == tenant`, `kayit['key']` `tenant + '/'` ile başlıyor ve `key.split('/')` parçalarının hiçbiri `'..'` değil.
- Sıralama: `score` azalan; eşit skorda `id` artan. İlk `k` kaydın `id` listesini döndür.
- Girdiyi değiştirme.

KUSURLU başlangıç önce bütün depoyu sıralayıp ilk `k`'yı alıyor, sonra kiracıya göre süzüyor ve anahtar önekini `/` olmadan denetliyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[[{"id": "b1", "tenant": "musteri-b", "key": "musteri-b/x", "score": 0.95}, {"id": "a1", "tenant": "musteri-a", "key": "musteri-a/q3", "score": 0.7}, {"id": "a2", "tenant": "musteri-a", "key": "musteri-ab/z", "score": 0.6}], "musteri-a", 1]', encoding='utf-8')
```

```starter
def tenant_sec(kayitlar, tenant, k):
    sirali = sorted(kayitlar, key=lambda r: -r['score'])[:k]
    return [r['id'] for r in sirali if r['tenant'] == tenant and r['key'].startswith(tenant)]

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(tenant_sec(*_args))
```

```solution
import math

def tenant_sec(kayitlar, tenant, k):
    if not isinstance(kayitlar, list) or not isinstance(tenant, str) or not tenant or type(k) is not int or k < 1:
        raise ValueError('kayitlar list, tenant bos olmayan str, k pozitif int olmali')
    gorulen = set()
    secilen = []
    for r in kayitlar:
        if (not isinstance(r, dict)
                or not all(isinstance(r.get(a), str) and r[a] for a in ('id', 'tenant', 'key'))
                or type(r.get('score')) not in (int, float) or not math.isfinite(r['score'])):
            raise ValueError('bozuk kayit')
        if r['id'] in gorulen:
            raise ValueError('yinelenen id')
        gorulen.add(r['id'])
        if r['tenant'] == tenant and r['key'].startswith(tenant + '/') and '..' not in r['key'].split('/'):
            secilen.append(r)
    secilen.sort(key=lambda r: (-r['score'], r['id']))
    return [r['id'] for r in secilen[:k]]

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(tenant_sec(*_args))
```

```test
need('tenant_sec')
import copy
def _r(i, t, key, s):
    return {'id': i, 'tenant': t, 'key': key, 'score': s}
_depo = [
    _r('b1', 'musteri-b', 'musteri-b/plan.pdf', 0.99),
    _r('b2', 'musteri-b', 'musteri-b/fiyat.pdf', 0.97),
    _r('a3', 'musteri-a', 'musteri-a/q3.pdf', 0.70),
    _r('a1', 'musteri-a', 'musteri-a/q1.pdf', 0.70),
    _r('a2', 'musteri-a', 'musteri-a/el-kitabi.pdf', 0.80),
    _r('a4', 'musteri-a', 'musteri-a/eski.pdf', 0.10),
    _r('x1', 'musteri-a', 'musteri-ab/benzer-ad.pdf', 0.98),
    _r('x2', 'musteri-a', 'musteri-a/../musteri-b/plan.pdf', 0.96),
    _r('x3', 'musteri-b', 'musteri-a/yanlis-etiket.pdf', 0.95),
    _r('a5', 'musteri-a', 'musteri-a/..yedek/not.pdf', 0.05),
]
_yedek = copy.deepcopy(_depo)
eq(tenant_sec(_depo, 'musteri-a', 3), ['a2', 'a1', 'a3'], 'önce süz, sonra sırala; eşit skorda id artan')
eq(tenant_sec(_depo, 'musteri-a', 1), ['a2'], 'başka kiracının yüksek skoru ilk k\'yı dolduramaz')
eq(tenant_sec(_depo, 'musteri-a', 10), ['a2', 'a1', 'a3', 'a4', 'a5'], 'k kayıt sayısından büyükse hepsi; ..yedek bir .. bölümü değildir')
eq(tenant_sec(_depo, 'musteri-b', 2), ['b1', 'b2'], 'öteki kiracı yalnız kendi kayıtlarını görür')
eq(tenant_sec(_depo, 'musteri-c', 2), [], 'kaydı olmayan kiracıya boş liste')
eq(_depo, _yedek, 'girdi değişmemeli')
eq(tenant_sec([_r('i1', 't', 't/a', 3), _r('i2', 't', 't/b', 2.5)], 't', 2), ['i1', 'i2'], 'int ve float skor birlikte')

for _ust in ((tuple(_depo), 'musteri-a', 2), (_depo, '', 2), (_depo, None, 2), (_depo, 'musteri-a', 0),
             (_depo, 'musteri-a', -1), (_depo, 'musteri-a', True), (_depo, 'musteri-a', 2.0), (_depo, 5, 2)):
    raises(ValueError, tenant_sec, *_ust, msg=f'bozuk üst argüman ValueError: {_ust[1:]!r}')
for _bozuk in (
    ['kayit'],
    [{'tenant': 't', 'key': 't/a', 'score': 1}],
    [_r('', 't', 't/a', 1)],
    [_r('i', '', 't/a', 1)],
    [_r('i', 't', '', 1)],
    [_r('i', 't', 5, 1)],
    [_r('i', 't', 't/a', '1')],
    [_r('i', 't', 't/a', True)],
    [_r('i', 't', 't/a', float('nan'))],
    [_r('i', 't', 't/a', float('inf'))],
    [_r('i', 't', 't/a', None)],
    [_r('i', 't', 't/a', 1), _r('i', 'u', 'u/b', 2)],
    [_r('i', 'u', 'u/b', 1), _r('j', 't', 't/a', float('-inf'))],
):
    raises(ValueError, tenant_sec, _bozuk, 't', 1, msg=f'bozuk kayıt ValueError: {_bozuk!r}')
```

```hint
Önce bütün kayıtları doğrula ve kiracı + anahtar kuralına uyanları ayrı bir listede topla. Sıralamayı yalnız o liste üzerinde yap: `key=lambda r: (-r['score'], r['id'])`.
```
:::

::: gorev 2 · Sorgu kayıtlarından kiracılar arası sızıntıyı ölç
Bir retriever'ın davranışını sorgu kayıtlarından denetleyen `sizinti_olc(sorgular, kayit_kiraci)` işlevini yaz.

- `kayit_kiraci` bir `dict`: kayıt `id` → sahibi olan kiracı (`str` → boş olmayan `str`).
- `sorgular` bir `list`; her öğe `{'tenant': str, 'donen': list[str]}`: oturumdaki doğrulanmış kiracı ve retriever'ın döndürdüğü kayıt kimlikleri.
- `kayit_kiraci` `dict` değilse ya da içinde boş olmayan `str` olmayan bir anahtar ya da değer varsa; `sorgular` `list` değilse; bir sorgu `dict` değilse; `tenant` boş olmayan `str` değilse; `donen` `str` listesi değilse ya da `kayit_kiraci`'da olmayan bir kimlik içeriyorsa `ValueError`.
- Dönüş:
  - `'sorgu_n'`: sorgu sayısı;
  - `'sizan_sorgu'`: en az bir başka kiracı kaydı döndüren sorgu sayısı;
  - `'sizan_kayit'`: başka kiracıya dönen kayıt kimlikleri, **tekrarsız ve sıralı**;
  - `'oran'`: `round(sizan_sorgu / sorgu_n, 4)`; sorgu yoksa `None`.

KUSURLU başlangıç sızıntıyı kayıt sayısına bölüyor, aynı kaydı birden çok kez sayıyor ve bilinmeyen kimliği sessizce atlıyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def sizinti_olc(sorgular, kayit_kiraci):
    sizan = []
    toplam = 0
    for q in sorgular:
        for i in q['donen']:
            toplam += 1
            if i in kayit_kiraci and kayit_kiraci[i] != q['tenant']:
                sizan.append(i)
    return {
        'sorgu_n': len(sorgular),
        'sizan_sorgu': len(sizan),
        'sizan_kayit': sizan,
        'oran': round(len(sizan) / toplam, 4) if toplam else None,
    }
```

```solution
def _dolu_str(x):
    return isinstance(x, str) and bool(x.strip())

def sizinti_olc(sorgular, kayit_kiraci):
    if not isinstance(kayit_kiraci, dict) or not all(_dolu_str(a) and _dolu_str(d) for a, d in kayit_kiraci.items()):
        raise ValueError('kayit_kiraci str -> str sozluk olmali')
    if not isinstance(sorgular, list):
        raise ValueError('sorgular list olmali')
    sizan_sorgu = 0
    sizan_kayit = set()
    for q in sorgular:
        if not isinstance(q, dict) or not _dolu_str(q.get('tenant')) or not isinstance(q.get('donen'), list):
            raise ValueError('bozuk sorgu')
        yabanci = []
        for i in q['donen']:
            if not isinstance(i, str) or i not in kayit_kiraci:
                raise ValueError('bilinmeyen kayit kimligi')
            if kayit_kiraci[i] != q['tenant']:
                yabanci.append(i)
        if yabanci:
            sizan_sorgu += 1
            sizan_kayit.update(yabanci)
    n = len(sorgular)
    return {
        'sorgu_n': n,
        'sizan_sorgu': sizan_sorgu,
        'sizan_kayit': sorted(sizan_kayit),
        'oran': round(sizan_sorgu / n, 4) if n else None,
    }
```

```test
need('sizinti_olc')
import copy
_sahip = {'a1': 'musteri-a', 'a2': 'musteri-a', 'b1': 'musteri-b', 'b2': 'musteri-b', 'c1': 'musteri-c'}
_kayit = [
    {'tenant': 'musteri-a', 'donen': ['a1', 'b1']},
    {'tenant': 'musteri-a', 'donen': ['a2']},
    {'tenant': 'musteri-b', 'donen': ['b2', 'a1', 'c1']},
    {'tenant': 'musteri-c', 'donen': []},
    {'tenant': 'musteri-a', 'donen': ['b1', 'b1']},
    {'tenant': 'musteri-b', 'donen': ['b1', 'b2']},
]
_yedek = copy.deepcopy((_kayit, _sahip))
eq(sizinti_olc(_kayit, _sahip), {
    'sorgu_n': 6,
    'sizan_sorgu': 3,
    'sizan_kayit': ['a1', 'b1', 'c1'],
    'oran': 0.5,
}, 'sızıntı sorgu başına sayılır; sızan kayıtlar tekrarsız ve sıralı')
eq((_kayit, _sahip), _yedek, 'girdiler değişmemeli')
eq(sizinti_olc(_kayit[:3], _sahip)['oran'], 0.6667, '3 sorgunun 2\'si sızdırdığında oran 4 basamakla')
eq(sizinti_olc([], _sahip), {'sorgu_n': 0, 'sizan_sorgu': 0, 'sizan_kayit': [], 'oran': None}, 'sorgu yoksa oran None')
eq(sizinti_olc([{'tenant': 'musteri-a', 'donen': ['a1', 'a2']}], _sahip),
   {'sorgu_n': 1, 'sizan_sorgu': 0, 'sizan_kayit': [], 'oran': 0.0}, 'temiz retriever oran 0.0')

for _bozuk in (
    (tuple(_kayit), _sahip),
    (_kayit, None),
    (_kayit[:1], dict(_sahip, zz='')),
    (_kayit[:1], dict(_sahip, zz=5)),
    (_kayit[:1], dict(_sahip, **{'  ': 'musteri-a'})),
    (_kayit[:1], {**_sahip, 5: 'musteri-a'}),
    (_kayit[:1], {**_sahip, '': ''}),
    (['sorgu'], _sahip),
    ([{'donen': ['a1']}], _sahip),
    ([{'tenant': '', 'donen': ['a1']}], _sahip),
    ([{'tenant': 'musteri-a', 'donen': 'a1'}], _sahip),
    ([{'tenant': 'musteri-a', 'donen': ['zz']}], _sahip),
    ([{'tenant': 'musteri-a', 'donen': [1]}], _sahip),
    ([{'tenant': 'musteri-a', 'donen': ('a1',)}], _sahip),
    ([{'tenant': 'musteri-a', 'donen': [['a1']]}], _sahip),
):
    raises(ValueError, sizinti_olc, *_bozuk, msg=f'bozuk girdi ValueError: {_bozuk!r}')
```

```hint
Her sorgu için o sorgunun yabancı kayıtlarını ayrı bir listede topla; liste doluysa sorgu sayacını bir artır ve kimlikleri bir `set`'e ekle. Oranın paydası kayıt değil sorgu sayısıdır.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Risk (20 sn).** "Çok kiracılı RAG'de bir kiracının sorusu başka kiracının belgesini getirirse model onu okur ve anlatır; OWASP bunu LLM08'de cross-context leak olarak sayıyor."
2. **Süzgecin yeri (30 sn).** "Önce depoyu sıralayıp sonra süzünce, öteki kiracının iki yüksek skorlu belgesi ilk k'yı doldurdu ve müşteri A'ya hiç bağlam kalmadı. Süzgeci sıralamadan önce koyunca sorun kalktı."
3. **Anahtar kapsamı (30 sn).** "Kayıt etiketi doğru olsa bile nesne anahtarını denetledim: musteri-ab öneki ve .. bölümü testte ayrı ayrı reddediliyor."
4. **Ölçüm (25 sn).** "Sorgu kayıtlarından sızıntıyı sorgu başına ölçtüm: altı sorgudan üçü başka kiracıya ait kayıt döndürmüş, oran 0,5."
5. **Sınır (15 sn).** "Gömme yok, skorlar sentetik; gerçek depoda süzgeç sorgu motorunun kendisinde uygulanmalı."
:::

::: anlat Sınır ve kaynak
Bu ders benzerlik skorlarını ve anahtarları sentetik olarak verir; gerçek gömme modeli, yaklaşık en yakın komşu (ANN) dizini ya da vektör deposu yoktur. Gerçek ANN dizinlerinde süzgeç, aramanın içinde ya da sonrasında uygulanabilir ve sonuç sayısı ile isabeti etkiler; bu ayrıntı burada modellenmez. Anahtar denetimi yalnız `/` ayracı ve `..` bölümünü kapsar; URL kodlu (`%2e%2e`) ya da Unicode varyantlı yol hileleri kapsam dışıdır.

- Birincil kaynaklar: [OWASP GenAI — LLM08:2025 Vector and Embedding Weaknesses](https://genai.owasp.org/llmrisk/llm082025-vector-and-embedding-weaknesses/) (*Cross-Context Information Leaks*, izin farkında vektör depoları); [Amazon Bedrock — Configure and customize queries and response generation](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-test-config.html) (bilgi tabanı sorgularında metadata filtering). Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
Kiracı kimliği oturumdan gelse bile, bir yöneticinin "bütün kiracılarda ara" yetkisi olabilir. Bu istisnayı `tenant_sec` sözleşmesine eklemek yerine neden ayrı bir işlev ve ayrı bir kayıt akışı olarak tasarlardın?
:::

::: ozet
- Çok kiracılı RAG'de kiracı süzgeci benzerlik sıralamasından önce uygulanır; sonra uygulamak hem sonuç kaybettirir hem sızıntıya kapı açar.
- Kiracı kimliği istemden değil, doğrulanmış oturumdan gelir.
- Nesne anahtarı `tenant + '/'` önekiyle ve `..` bölümü olmadan denetlenir.
- Sızıntı sorgu başına ölçülür; aynı kaydın tekrarları ve bilinmeyen kimlikler sonucu bozmamalıdır.
:::
