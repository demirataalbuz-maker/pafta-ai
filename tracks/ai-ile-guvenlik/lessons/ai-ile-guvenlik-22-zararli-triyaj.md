---
id: ai-ile-guvenlik-22
title: "Zararlı Yazılım Triyajı · Sentetik Davranış Kanıtı"
summary: Fidye yazılımı triyajında kararı davranış kanıtlarının birlikteliğine bağla; modelin iddialarını statik (import, dizge) ve dinamik (yürütme kaydı) kanıta göre ayır, uydurma kaynak gösteren iddiayı yakala.
esleme: ai-ile-guvenlik-21, ai-ile-guvenlik-10, ai-ile-guvenlik-25, ai-saldiri-54
timeout: 30
---

::: anlat 1. Fidye yazılımının iki imzası
MITRE ATT&CK, fidye yazılımlarının en belirgin iki davranışını ayrı teknikler olarak tanımlar:

- **T1486 — Data Encrypted for Impact:** saldırgan hedef sistemlerdeki verileri, çoğu zaman toplu biçimde, erişilemez hâle getirmek için şifreler; amaç genellikle fidye istemektir.
- **T1490 — Inhibit System Recovery:** saldırgan kurtarmayı engeller; ATT&CK sayfası örnek olarak `vssadmin.exe` ile bütün gölge kopyaların (*volume shadow copies*) silinebileceğini ve çevrim içi yedeklerin de silinebileceğini anlatır.

Tek başına bir şifreleme etkinliği yedekleme yazılımında da görülür; tek başına gölge kopya silme bir bakım betiğinde de olabilir. Fidye yazılımı kararını güçlü kılan, **ikisinin aynı örnekte birlikte** görülmesidir. Benzer biçimde kalıcılık (*persistence*) ve dışarıya düzenli bağlantı (*beacon*) birlikte görüldüğünde orta düzey bir arka kapı şüphesi oluşur.

Bir model bu triyajda yardımcı olabilir: dizgeleri okur, import tablosuna bakar, "bu örnek dosyaları şifreliyor" diye bir özet yazar. Ama import tablosunda `CryptEncrypt` bulunması, örneğin **çalıştığında** dosyaları şifrelediğini kanıtlamaz; yalnız bunu **yapabileceğini** gösterir.

> [!NOTE]
> Bu derste gerçek zararlı yazılım üretilmez, çalıştırılmaz ya da indirilmez. Kanıt kayıtları ve model iddiaları **sentetiktir**.
:::

::: anlat 2. Mekanizma: yetenek iddiası ile davranış iddiası
Triyaj raporundaki her cümle iki türden birindedir:

- **Yetenek (*capability*):** "Bu örnek dosya şifreleyebilir." Statik kanıt (import, dizge, kod parçası) yeterlidir.
- **Davranış (*behavior*):** "Bu örnek çalıştığında dosyaları şifreledi." Dinamik kanıt gerekir: kum havuzunda (*sandbox*) yürütme kaydı, dosya sistemi olayları.

Modelin en sık yaptığı hata, statik bir ipucundan davranış cümlesi kurmaktır. İkinci hata daha tehlikelidir: var olmayan bir kanıta atıf yapmak. Model "bkz. olay D-7" der ama kayıtlarda D-7 yoktur. Bu, OWASP'ın LLM09'da anlattığı uydurmanın (*hallucination*) triyajdaki biçimidir. Uydurma kaynak taşıyan iddia, diğer referansları doğru olsa bile reddedilir; çünkü raporun doğrulanabilirliği bozulmuştur.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| Tek bir şifreleme kanıtıyla "fidye yazılımı" demek | Yedekleme yazılımı da toplu şifreler | T1486 ve T1490 kanıtları birlikte |
| Import'u davranış kanıtı saymak | Kod yolu hiç çalışmamış olabilir | Davranış iddiası dinamik kanıt ister |
| Bilinmeyen referansı yok saymak | Uydurma kanıt rapora "kaynaklı" görünür | Bilinmeyen referans → uydurma kaynak |
| Kanıt listesini karar dışı kayıtlarla doldurmak | İnceleyen asıl kanıtı bulamaz | Yalnız kararı destekleyen kayıtlar, sıralı |
| Yinelenen kanıt kimliğini kabul etmek | Aynı olay iki kez sayılır ya da üzerine yazılır | Yinelenen kimlik → hata |
:::

::: tahmin Import mı, yürütme mi?
Model iki iddia yazdı. Kanıt kayıtlarından biri statik (import tablosu), biri dinamik (kum havuzu olayı). Hangi iddia kanıtlanmış sayılır?

```python
kanit = {
    'S-1': {'kind': 'encrypt-many', 'kaynak': 'statik'},
    'D-1': {'kind': 'delete-backups', 'kaynak': 'dinamik'},
}
iddialar = [
    ('A', 'davranis', ['S-1']),
    ('B', 'davranis', ['D-1']),
    ('C', 'yetenek', ['S-1']),
]
for kid, tur, refs in iddialar:
    dinamik = any(kanit[r]['kaynak'] == 'dinamik' for r in refs)
    karar = 'kanitlandi' if (tur == 'yetenek' or dinamik) else 'hipotez'
    print(kid, tur, '->', karar)
```

???

```cikti
A davranis -> hipotez
B davranis -> kanitlandi
C yetenek -> kanitlandi
```
Aynı statik kanıt (`S-1`) bir yetenek iddiasını destekler ama bir davranış iddiasını desteklemez. "Şifreleyebilir" kanıtlıdır; "şifreledi" ise hâlâ bir hipotezdir.
:::

::: gorev 1 · Birliktelik kuralıyla triyaj kararı
`triyaj(kanitlar)` işlevini yaz.

- `kanitlar` bir `list`; her kayıt `{'id': str, 'kind': str}`. `id` boş olmayan ve benzersiz, `kind` bir `str` olmalı; değilse `ValueError`.
- Karar:
  - `'encrypt-many'` ve `'delete-backups'` türlerinin **ikisi de** varsa → `'high'` (T1486 + T1490);
  - değilse `'persistence'` ve `'beacon'` türlerinin ikisi de varsa → `'medium'`;
  - değilse → `'uncertain'`.
- Dönüş: `{'verdict': karar, 'kanit': [...]}`. `kanit`, yalnız kararı destekleyen türlerdeki kayıtların `id`'leridir, alfabetik sıralı. `'uncertain'` kararında boş listedir.

KUSURLU başlangıç tek bir şifreleme kanıtıyla `'high'` diyor ve bütün kayıtları kanıt listesine koyuyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[[{"id": "e2", "kind": "encrypt-many"}, {"id": "n1", "kind": "dns-query"}, {"id": "e1", "kind": "encrypt-many"}]]', encoding='utf-8')
```

```starter
def triyaj(kanitlar):
    turler = {k['kind'] for k in kanitlar}
    if 'encrypt-many' in turler:
        return {'verdict': 'high', 'kanit': [k['id'] for k in kanitlar]}
    if 'persistence' in turler and 'beacon' in turler:
        return {'verdict': 'medium', 'kanit': [k['id'] for k in kanitlar]}
    return {'verdict': 'uncertain', 'kanit': []}

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(triyaj(*_args))
```

```solution
def triyaj(kanitlar):
    if not isinstance(kanitlar, list):
        raise ValueError('kanitlar list olmali')
    gorulen = set()
    for k in kanitlar:
        if (not isinstance(k, dict) or not isinstance(k.get('id'), str) or not k['id'].strip()
                or not isinstance(k.get('kind'), str) or k['id'] in gorulen):
            raise ValueError('bozuk ya da yinelenen kanit')
        gorulen.add(k['id'])
    turler = {k['kind'] for k in kanitlar}
    if {'encrypt-many', 'delete-backups'} <= turler:
        karar, gereken = 'high', {'encrypt-many', 'delete-backups'}
    elif {'persistence', 'beacon'} <= turler:
        karar, gereken = 'medium', {'persistence', 'beacon'}
    else:
        karar, gereken = 'uncertain', set()
    return {'verdict': karar, 'kanit': sorted(k['id'] for k in kanitlar if k['kind'] in gereken)}

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(triyaj(*_args))
```

```test
need('triyaj')
import copy
def _k(i, kind):
    return {'id': i, 'kind': kind}
_tam = [_k('e2', 'encrypt-many'), _k('p1', 'persistence'), _k('d1', 'delete-backups'), _k('b1', 'beacon'), _k('e1', 'encrypt-many'), _k('n1', 'dns-query')]
_yedek = copy.deepcopy(_tam)
eq(triyaj(_tam), {'verdict': 'high', 'kanit': ['d1', 'e1', 'e2']}, 'iki fidye imzası birlikte: high; kanıt yalnız onlar, alfabetik')
eq(_tam, _yedek, 'girdi değişmemeli')
eq(triyaj([_k('e1', 'encrypt-many'), _k('n1', 'dns-query')]), {'verdict': 'uncertain', 'kanit': []}, 'tek şifreleme kanıtı yetmez')
eq(triyaj([_k('d1', 'delete-backups')]), {'verdict': 'uncertain', 'kanit': []}, 'tek yedek silme kanıtı yetmez')
eq(triyaj([_k('p1', 'persistence'), _k('e1', 'encrypt-many'), _k('b2', 'beacon'), _k('b1', 'beacon')]),
   {'verdict': 'medium', 'kanit': ['b1', 'b2', 'p1']}, 'kalıcılık + beacon: medium; şifreleme kanıtı listeye girmez')
eq(triyaj([_k('p1', 'persistence')]), {'verdict': 'uncertain', 'kanit': []}, 'yalnız kalıcılık yetmez')
eq(triyaj([_k('b1', 'beacon')]), {'verdict': 'uncertain', 'kanit': []}, 'yalnız beacon yetmez')
eq(triyaj([]), {'verdict': 'uncertain', 'kanit': []}, 'boş kanıt uncertain')
eq(triyaj([_k('e1', 'encrypt-many'), _k('d1', 'delete-backups')]), {'verdict': 'high', 'kanit': ['d1', 'e1']}, 'yalnız iki imza varken de high')
eq(triyaj([_k('p1', 'persistence'), _k('b1', 'beacon')]), {'verdict': 'medium', 'kanit': ['b1', 'p1']}, 'yalnız kalıcılık ve beacon varken de medium')
eq(triyaj([_k('x', 'Encrypt-Many'), _k('y', 'delete-backups')]), {'verdict': 'uncertain', 'kanit': []}, 'tür adı büyük/küçük harfe duyarlı')

raises(ValueError, triyaj, tuple(_tam), msg='liste olmayan kanıt ValueError')
for _bozuk in (['e1'], [{'kind': 'beacon'}], [_k('', 'beacon')], [_k('  ', 'beacon')], [_k(5, 'beacon')],
               [{'id': 'a'}], [_k('a', None)], [_k('a', 'beacon'), _k('a', 'persistence')]):
    raises(ValueError, triyaj, _bozuk, msg=f'bozuk kanıt ValueError: {_bozuk!r}')
```

```hint
Önce bütün kayıtları doğrula ve yinelenen kimliği yakala. Türleri bir kümede topla; `{'encrypt-many', 'delete-backups'} <= turler` birlikteliği tek satırda sınar.
```
:::

::: gorev 2 · Model iddialarını kanıt türüne göre ayır
`iddia_denetle(iddialar, kanitlar)` işlevini yaz.

- `kanitlar`: kanıt kimliği → `{'kind': str, 'kaynak': 'statik' | 'dinamik'}` sözlüğü.
- `iddialar`: `{'id': str, 'tur': 'davranis' | 'yetenek', 'refs': list[str]}` listesi.
- Her iddia için karar, **bu öncelikle**:
  1. `refs` içinde `kanitlar`'da olmayan bir kimlik varsa → `'uydurma-kaynak'`;
  2. `refs` boşsa → `'desteksiz'`;
  3. `tur == 'yetenek'` → `'kanitlandi'` (statik ya da dinamik herhangi bir kanıt yeter);
  4. `tur == 'davranis'` ve en az bir referans `'dinamik'` ise → `'kanitlandi'`; yalnız statik referanslar varsa → `'hipotez'`.
- Dönüş: girdi sırasıyla `[[id, karar], ...]`.
- Hata (`ValueError`): `kanitlar` `dict` değil ya da bir kaydı `dict` değil, `kind` `str` değil, `kaynak` bu iki değerden biri değil; `iddialar` `list` değil; iddia `dict` değil, `id` boş olmayan `str` değil ya da tekrar ediyor, `tur` geçersiz, `refs` `str` listesi değil.

KUSURLU başlangıç bilinmeyen referansları sessizce atlıyor ve kaynağına bakmadan her referansı kanıt sayıyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def iddia_denetle(iddialar, kanitlar):
    sonuc = []
    for c in iddialar:
        gecerli = [r for r in c['refs'] if r in kanitlar]
        sonuc.append([c['id'], 'kanitlandi' if gecerli else 'desteksiz'])
    return sonuc
```

```solution
_KAYNAK = ('statik', 'dinamik')
_TUR = ('davranis', 'yetenek')

def iddia_denetle(iddialar, kanitlar):
    if not isinstance(kanitlar, dict) or not isinstance(iddialar, list):
        raise ValueError('kanitlar dict, iddialar list olmali')
    for k in kanitlar.values():
        if not isinstance(k, dict) or not isinstance(k.get('kind'), str) or k.get('kaynak') not in _KAYNAK:
            raise ValueError('bozuk kanit')
    gorulen = set()
    sonuc = []
    for c in iddialar:
        if (not isinstance(c, dict) or not isinstance(c.get('id'), str) or not c['id'].strip()
                or c.get('tur') not in _TUR or not isinstance(c.get('refs'), list)
                or any(not isinstance(r, str) for r in c['refs'])):
            raise ValueError('bozuk iddia')
        if c['id'] in gorulen:
            raise ValueError('yinelenen iddia')
        gorulen.add(c['id'])
        refs = c['refs']
        if any(r not in kanitlar for r in refs):
            karar = 'uydurma-kaynak'
        elif not refs:
            karar = 'desteksiz'
        elif c['tur'] == 'yetenek' or any(kanitlar[r]['kaynak'] == 'dinamik' for r in refs):
            karar = 'kanitlandi'
        else:
            karar = 'hipotez'
        sonuc.append([c['id'], karar])
    return sonuc
```

```test
need('iddia_denetle')
import copy
_kanit = {
    'S-1': {'kind': 'encrypt-many', 'kaynak': 'statik'},
    'S-2': {'kind': 'delete-backups', 'kaynak': 'statik'},
    'D-1': {'kind': 'encrypt-many', 'kaynak': 'dinamik'},
}
def _c(i, tur, refs):
    return {'id': i, 'tur': tur, 'refs': refs}
_iddia = [
    _c('A', 'davranis', ['S-1']),
    _c('B', 'davranis', ['S-1', 'D-1']),
    _c('C', 'yetenek', ['S-2']),
    _c('D', 'davranis', ['D-1', 'D-7']),
    _c('E', 'yetenek', []),
    _c('F', 'davranis', ['S-1', 'S-2']),
    _c('G', 'yetenek', ['D-1']),
    _c('H', 'davranis', []),
]
_yedek = copy.deepcopy((_iddia, _kanit))
eq(iddia_denetle(_iddia, _kanit), [
    ['A', 'hipotez'], ['B', 'kanitlandi'], ['C', 'kanitlandi'], ['D', 'uydurma-kaynak'],
    ['E', 'desteksiz'], ['F', 'hipotez'], ['G', 'kanitlandi'], ['H', 'desteksiz'],
], 'statik → hipotez; bir dinamik yeter; bilinmeyen referans geçerli olanlara rağmen uydurma')
eq((_iddia, _kanit), _yedek, 'girdiler değişmemeli')
eq(iddia_denetle([], _kanit), [], 'iddia yoksa boş liste')
eq(iddia_denetle([_c('X', 'davranis', ['Q'])], {}), [['X', 'uydurma-kaynak']], 'kanıt deposu boşsa her referans uydurma')

for _bozuk in (
    (tuple(_iddia), _kanit),
    (_iddia, [_kanit]),
    (_iddia, {'S-1': 'encrypt-many'}),
    (_iddia, {'S-1': {'kind': 'encrypt-many'}}),
    (_iddia, {'S-1': {'kind': 'encrypt-many', 'kaynak': 'canli'}}),
    (_iddia, {'S-1': {'kind': 5, 'kaynak': 'statik'}}),
    (['A'], _kanit),
    ([_c('', 'davranis', [])], _kanit),
    ([_c('  ', 'davranis', [])], _kanit),
    ([_c(5, 'davranis', [])], _kanit),
    ([_c('A', 'tahmin', [])], _kanit),
    ([_c('A', 'davranis', 'S-1')], _kanit),
    ([_c('A', 'davranis', [1])], _kanit),
    ([_c('A', 'davranis', []), _c('A', 'yetenek', [])], _kanit),
):
    raises(ValueError, iddia_denetle, *_bozuk, msg=f'bozuk girdi ValueError: {_bozuk!r}')
```

```hint
Kararı öncelik sırasıyla bir `if/elif` zinciriyle ver: önce bilinmeyen referans, sonra boş referans, sonra tür ve kaynak.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **İki imza (25 sn).** "ATT&CK fidye yazılımının iki davranışını ayrı teknik sayıyor: T1486 toplu şifreleme ve T1490 kurtarmayı engelleme, örneğin gölge kopyaları silmek. Tek başına ikisinin de masum açıklaması var; kararı birlikteliğe bağladık."
2. **Kanıt listesi (20 sn).** "Karar verirken yalnız kararı destekleyen kayıtları, sıralı olarak raporladık; DNS sorgusu gibi ilgisiz olaylar listeye girmiyor."
3. **Yetenek ve davranış (35 sn).** "Modelin 'bu örnek dosyaları şifreledi' cümlesi import tablosuna dayanıyorsa hipotez olarak kalıyor. 'Şifreleyebilir' cümlesi aynı kanıtla kanıtlı sayılıyor. Davranış cümlesi kum havuzu kaydı istiyor."
4. **Uydurma kaynak (25 sn).** "Model kayıtlarda olmayan D-7'ye atıf yaptı. Yanındaki referans doğru olsa bile iddiayı uydurma kaynak diye ayırdık; doğrulanabilirliği bozulmuş rapor güven vermez."
5. **Sınır (15 sn).** "Kanıtlar sentetik; gerçek triyajda dinamik analiz kaçınma teknikleri yüzünden davranışı göstermeyebilir."
:::

::: anlat Sınır ve kaynak
Bu ders iki birliktelik kuralı ve iki kanıt kaynağıyla çalışır. Gerçek triyajda kararlar çok daha fazla sinyale dayanır. Zararlı yazılım kum havuzunu algılayıp davranışını gizleyebilir; bu yüzden dinamik kanıtın yokluğu davranışın yokluğu değildir. "Hipotez" kararı "yanlış" demek değil, "henüz kanıtlanmadı" demektir. Kanıt türleri ve kimlikleri sentetiktir; gerçek bir örnek çalıştırılmaz.

- Birincil kaynaklar: [MITRE ATT&CK — T1486 Data Encrypted for Impact](https://attack.mitre.org/techniques/T1486/); [MITRE ATT&CK — T1490 Inhibit System Recovery](https://attack.mitre.org/techniques/T1490/) (`vssadmin.exe` ile gölge kopya silme, çevrim içi yedekleri silme); [OWASP GenAI — LLM09:2025 Misinformation](https://genai.owasp.org/llmrisk/llm092025-misinformation/). Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
Kum havuzu örneği 10 dakika çalıştırdı ve hiçbir şifreleme olayı görmedi; ama statik analiz şifreleme kodu buldu. Model "bu örnek fidye yazılımı değil" diye yazdı. Bu cümle hangi tür iddiadır ve elindeki kanıt onu neden desteklemez?
:::

::: ozet
- Fidye yazılımı kararı T1486 (toplu şifreleme) ve T1490 (kurtarmayı engelleme) kanıtlarının birlikteliğine bağlanır.
- Statik kanıt yeteneği, dinamik kanıt davranışı destekler.
- Kayıtlarda olmayan bir kanıta atıf yapan iddia, diğer referansları doğru olsa bile reddedilir.
- Kanıt listesi yalnız kararı destekleyen kayıtları taşır.
:::
