---
id: kuantum-30
title: "Kuantum Üstünlüğü ve Kriptoyu Kırdık Haberleri Nasıl Okunur?"
summary: "Fiziksel qubit sayısından kaç mantıksal qubit çıktığını hesapla, bir duyuru ile kriptografik bir saldırı arasındaki kaynak açığını ölç ve bir haberi altı soruluk bir listeyle denetle; iki dakikada anlat."
track: kuantum
order: 30
---

::: anlat 1. Aynı başlık, her yıl
Her birkaç ayda bir benzer bir başlık çıkar: "Kuantum bilgisayar, süper bilgisayarın on bin yılda yapacağı işi dakikalarda yaptı" ya da "Araştırmacılar RSA'yı kuantum bilgisayarla kırdı". Bunların bir kısmı gerçek ve önemli bilimsel sonuçlardır; ama neredeyse hiçbiri başlığın ima ettiği şeyi, yani bugünkü şifrelemenin kırıldığını söylemez.

Bir güvenlik uzmanının işi bu haberleri küçümsemek ya da büyütmek değil, **doğru sınıflandırmaktır**. Bunun için üç ayrımı bilmen gerekir:

| Ayrım | Soru | Görev |
|---|---|---|
| Fiziksel ve mantıksal qubit | Duyurudaki sayı, hata düzeltmeden sonra kaç kullanılabilir qubit eder? | 1 |
| Gösteri ve saldırı | Yapılan iş ile gerçek bir anahtarı kırmak arasında ne kadar mesafe var? | 2 |
| Başlık ve içerik | Haber hangi tür sonucu, hangi koşullarla bildiriyor? | 3 |

> [!NOT]
> Bu dersteki kaynak tahminleri ve cihaz sayıları yayımlanmış çalışmalardan gelir ve hızla eskir; görevler belirli sayıları değil, **nasıl karşılaştırılacağını** öğretir. Hiçbir kuantum cihazı ya da kriptografik saldırı çalıştırılmaz.
:::

::: anlat 2. Üç ayrım
**Fiziksel ve mantıksal qubit.** Bugünkü qubit'ler gürültülüdür: her işlem küçük bir olasılıkla hata yapar ve milyarlarca işlemlik bir hesapta bu hatalar birikir. Çare `quantum error correction`'dır: çok sayıda **fiziksel** qubit, tek bir güvenilir **mantıksal** qubit'i kodlar. En çok çalışılan şema `surface code`'dur. `d` **kod mesafesi** olmak üzere bir mantıksal qubit yaklaşık

$$2d^2 - 1$$

fiziksel qubit ister ($d^2$ veri qubit'i ve $d^2 - 1$ ölçüm qubit'i). Mesafe büyüdükçe mantıksal hata oranı üstel olarak düşer; ama yalnız fiziksel hata oranı bir **eşiğin** altındaysa (kabaca yüzde bir mertebesi). Kriptografik bir saldırı için gereken mesafeler genellikle 20'nin üstündedir: mantıksal qubit başına bin civarında fiziksel qubit.

Bu yüzden "1.000 qubit'lik işlemci" cümlesi, hata düzeltmeden sonra **birkaç** mantıksal qubit, hatta hiç etmeyebilir. Bir duyuruda ilk bakılacak şey budur.

**Gösteri ve saldırı.** İki farklı tür sonuç aynı başlığı alır:

- **Kuantum üstünlüğü / avantajı.** 2019'da Google, 53 qubit'lik bir işlemciyle rastgele bir devrenin çıktısından örnek almanın (`random circuit sampling`) klasik süper bilgisayarlar için pratikte imkânsız olduğunu öne sürdü. Bu gerçek bir dönüm noktasıdır; ama seçilen problem **yararlı bir iş değildir** ve kriptografiyle ilgisi yoktur. Ayrıca "on bin yıl" tahmini kalıcı olmadı: daha iyi klasik algoritmalar aynı işi çok daha kısa sürede yaptı. Üstünlük iddiaları hareketli bir hedefe karşı ölçülür.
- **Çarpanlara ayırma gösterileri.** Shor algoritmasıyla bugüne kadar güvenilir biçimde ayrılan sayılar çok küçüktür ve çoğu gösteri, cevabı önceden bilmekten yararlanan sadeleştirmeler içerir. Daha büyük sayılar bildiren çalışmalar genellikle Shor'u değil, ölçeklenip ölçeklenmediği gösterilmemiş sezgisel yöntemleri kullanır. 2022'de bir ön baskı, 372 fiziksel qubit'in RSA-2048'i kırmaya yetebileceğini öne sürdü; yöntemin dayandığı klasik adımın ölçeklendiğine dair kanıt yoktu ve iddia alanda genel olarak kabul görmedi.

Gerçek ölçek için yayımlanmış kaynak tahminlerine bakılır. Gidney ve Ekerå (2021), RSA-2048'i sekiz saatte ayırmak için yaklaşık **20 milyon** gürültülü fiziksel qubit gerektiğini hesapladı; Gidney'in 2025 tarihli çalışması bunu bir milyonun altına indirdi. Tahminler düşüyor; ama bugünkü cihazlarla arada hâlâ büyük bir açık var: hem qubit sayısında hem de bu qubit'lerin saatlerce hatasız çalıştırılmasında.

**Başlık ve içerik.** Bir haberi sınıflandırmak için altı soru yeter: qubit'ler fiziksel mi mantıksal mı; problem ne; (çarpanlara ayırmaysa) sayı kaç bit; hata düzeltme kullanıldı mı; en iyi klasik yöntemle karşılaştırıldı mı; sonuç hakem denetiminden geçti mi?
:::

::: tahmin Bin qubit kaç mantıksal qubit eder?
1.000 fiziksel qubit'lik bir işlemci, farklı kod mesafelerinde kaç mantıksal qubit verir?

```python
fiziksel = 1000
for d in (3, 11, 25):
    basina = 2 * d * d - 1
    print(d, basina, fiziksel // basina)
```

???

```cikti
3 17 58
11 241 4
25 1249 0
```
Mesafe 3'te bir mantıksal qubit 17 fiziksel qubit ister ve 1.000 qubit 58 mantıksal qubit eder; ama mesafe 3 yalnız tek bir hatayı düzeltir ve uzun bir hesap için yetmez. Mesafe 11'de dört mantıksal qubit kalır. Kriptografik ölçekteki hesaplar için düşünülen mesafe 25 civarında ise tek bir mantıksal qubit'e bile yetmez. "Bin qubit" başlığı, hangi mesafede çalışıldığı söylenmeden hiçbir şey ifade etmez.
:::

::: gorev 1 · Fiziksel qubit'ten mantıksal qubit'e
`mantiksal_qubit(fiziksel, kod_mesafesi)` işlevini yaz.

- `fiziksel`: negatif olmayan `int`. `kod_mesafesi`: 3'ten küçük olmayan **tek** `int` (surface code mesafeleri tektir).
- `basina`: bir mantıksal qubit için gereken fiziksel qubit, `2d² - 1`.
- `mantiksal`: `fiziksel // basina`. `artan`: kullanılamayan fiziksel qubit sayısı.
- `duzeltilebilir_hata`: bir mantıksal qubit'in düzeltebildiği hata sayısı, `(d - 1) // 2`.
- Dönüş: bu dört anahtar (hepsi `int`).
- Bozuk girdi `ValueError`.

KUSURLU başlangıç fiziksel qubit sayısını doğrudan mantıksal qubit sayısı olarak döndürüyor: başlıkların yaptığı hatanın kendisi.

```starter
def mantiksal_qubit(fiziksel, kod_mesafesi):
    return {'basina': 1, 'mantiksal': fiziksel, 'artan': 0, 'duzeltilebilir_hata': 0}
```

```solution
def mantiksal_qubit(fiziksel, kod_mesafesi):
    if isinstance(fiziksel, bool) or not isinstance(fiziksel, int) or fiziksel < 0:
        raise ValueError('fiziksel negatif olmayan int olmalı')
    d = kod_mesafesi
    if isinstance(d, bool) or not isinstance(d, int) or d < 3 or d % 2 == 0:
        raise ValueError('kod_mesafesi 3 ten küçük olmayan tek int olmalı')
    basina = 2 * d * d - 1
    return {'basina': basina, 'mantiksal': fiziksel // basina, 'artan': fiziksel % basina, 'duzeltilebilir_hata': (d - 1) // 2}
```

```test
need('mantiksal_qubit')
import random

eq(mantiksal_qubit(1000, 3), {'basina': 17, 'mantiksal': 58, 'artan': 14, 'duzeltilebilir_hata': 1}, 'mesafe 3: 17 fiziksel qubit, tek hata düzeltir')
eq(mantiksal_qubit(1000, 11), {'basina': 241, 'mantiksal': 4, 'artan': 36, 'duzeltilebilir_hata': 5}, 'mesafe 11: dört mantıksal qubit')
eq(mantiksal_qubit(1000, 25)['mantiksal'], 0, 'mesafe 25: bin qubit tek bir mantıksal qubit e yetmez')
eq(mantiksal_qubit(0, 3), {'basina': 17, 'mantiksal': 0, 'artan': 0, 'duzeltilebilir_hata': 1}, 'hiç qubit yok')
eq(mantiksal_qubit(17, 3)['mantiksal'], 1, 'tam yetecek kadar')
eq(mantiksal_qubit(16, 3)['mantiksal'], 0, 'bir eksik: yetmez')
eq(mantiksal_qubit(20_000_000, 27)['mantiksal'], 20_000_000 // 1457, '20 milyon fiziksel qubit, mesafe 27: yaklaşık 13.700 mantıksal')
rng = random.Random(3001)
for _ in range(25):
    f, d = rng.randint(0, 5_000_000), rng.choice([3, 5, 7, 9, 11, 15, 21, 25, 31])
    r = mantiksal_qubit(f, d)
    b = d * d + (d * d - 1)
    eq(r['basina'], b, 'd kare veri + d kare eksi 1 ölçüm qubit i')
    eq(r['mantiksal'] * b + r['artan'], f, 'mantıksal · başına + artan = fiziksel')
    ok(0 <= r['artan'] < b, 'artan, bir mantıksal qubit ten az')
    eq(r['duzeltilebilir_hata'], (d - 1) // 2, 'düzeltilebilir hata sayısı')
    ok(all(isinstance(v, int) and not isinstance(v, bool) for v in r.values()), 'bütün değerler int')
ok(mantiksal_qubit(10 ** 6, 5)['mantiksal'] > mantiksal_qubit(10 ** 6, 7)['mantiksal'], 'mesafe büyüdükçe aynı donanımdan daha az mantıksal qubit çıkar')
for a in ([-1, 3], [100.0, 3], [True, 3], [None, 3], [100, 1], [100, 4], [100, 2], [100, 3.0], [100, True], [100, None]):
    raises(ValueError, mantiksal_qubit, *a, msg='bozuk girdi reddedilir')
```

```hint
`basina = 2 * d * d - 1`. Mantıksal sayı tam bölme, artan kalandır. Düzeltilebilir hata `(d - 1) // 2`.
```
:::

::: gorev 2 · Gösteri ile saldırı arasındaki açık
`kaynak_acigi(eldeki, gereken)` işlevini yaz. Bir cihazın bildirilen kaynaklarını, bir saldırı için yayımlanmış bir kaynak tahminiyle karşılaştırır.

- `eldeki`, `gereken`: her biri tam şu iki anahtara sahip sözlük: `'fiziksel_qubit'` (pozitif `int`) ve `'hata_orani'` (`(0, 1)` aralığında sayı; iki qubit'li kapı hata oranı).
- `qubit_kati`: `gereken / eldeki` qubit oranı. `qubit_ikiye_katlanma`: bu açığı kapatmak için qubit sayısının kaç kez ikiye katlanması gerektiği, `max(0, ceil(log2(qubit_kati)))`.
- `hata_kati`: `eldeki / gereken` hata oranı (1'den büyükse cihaz gerekenden gürültülü).
- `qubit_yeterli`: `eldeki >= gereken`. `hata_yeterli`: `eldeki hata <= gereken hata`.
- `yeterli`: ikisi birden.
- Dönüş: bu altı anahtar; oranlar 6 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç yalnız qubit sayısına bakıyor: yeterli sayıda ama çok gürültülü qubit'i olan bir cihazı "yeterli" sayıyor.

```starter
def kaynak_acigi(eldeki, gereken):
    k = gereken['fiziksel_qubit'] / eldeki['fiziksel_qubit']
    return {'qubit_kati': round(k, 6), 'qubit_ikiye_katlanma': 0, 'hata_kati': 1.0, 'qubit_yeterli': k <= 1, 'hata_yeterli': True, 'yeterli': k <= 1}
```

```solution
def kaynak_acigi(eldeki, gereken):
    import math
    for s in (eldeki, gereken):
        if not isinstance(s, dict) or set(s) != {'fiziksel_qubit', 'hata_orani'}:
            raise ValueError('sözlük tam iki anahtara sahip olmalı')
        q, h = s['fiziksel_qubit'], s['hata_orani']
        if isinstance(q, bool) or not isinstance(q, int) or q < 1:
            raise ValueError('fiziksel_qubit pozitif int olmalı')
        if isinstance(h, bool) or not isinstance(h, (int, float)) or not 0 < h < 1:
            raise ValueError('hata_orani (0, 1) aralığında olmalı')
    kat = gereken['fiziksel_qubit'] / eldeki['fiziksel_qubit']
    hata = eldeki['hata_orani'] / gereken['hata_orani']
    qy = eldeki['fiziksel_qubit'] >= gereken['fiziksel_qubit']
    hy = eldeki['hata_orani'] <= gereken['hata_orani']
    return {
        'qubit_kati': round(kat, 6),
        'qubit_ikiye_katlanma': 0 if qy else math.ceil(math.log2(kat) - 1e-12),
        'hata_kati': round(hata, 6),
        'qubit_yeterli': qy,
        'hata_yeterli': hy,
        'yeterli': qy and hy,
    }
```

```test
need('kaynak_acigi')
import math, random

def K(q, h):
    return {'fiziksel_qubit': q, 'hata_orani': h}

r = kaynak_acigi(K(1000, 0.005), K(1_000_000, 0.001))
eq(r, {'qubit_kati': 1000.0, 'qubit_ikiye_katlanma': 10, 'hata_kati': 5.0, 'qubit_yeterli': False, 'hata_yeterli': False, 'yeterli': False}, 'bin kat qubit açığı (on ikiye katlanma) ve beş kat hata açığı')
r = kaynak_acigi(K(2_000_000, 0.01), K(1_000_000, 0.001))
eq((r['qubit_yeterli'], r['hata_yeterli'], r['yeterli']), (True, False, False), 'qubit yeterli ama on kat gürültülü: yeterli değil')
eq(r['qubit_ikiye_katlanma'], 0, 'qubit açığı yoksa katlanma gerekmez')
r = kaynak_acigi(K(1_000_000, 0.001), K(1_000_000, 0.001))
eq((r['qubit_kati'], r['hata_kati'], r['yeterli']), (1.0, 1.0, True), 'tam eşit: yeterli')
eq(kaynak_acigi(K(1000, 0.001), K(1024, 0.001))['qubit_ikiye_katlanma'], 1, 'küçük açık: bir katlanma')
eq(kaynak_acigi(K(1000, 0.001), K(2000, 0.001))['qubit_ikiye_katlanma'], 1, 'tam iki kat: bir katlanma')
eq(kaynak_acigi(K(1000, 0.001), K(2001, 0.001))['qubit_ikiye_katlanma'], 2, 'iki katın biraz üstü: iki katlanma')
rng = random.Random(3002)
for _ in range(25):
    e, g = K(rng.randint(1, 10 ** 6), rng.choice([1e-4, 1e-3, 5e-3, 1e-2])), K(rng.randint(1, 10 ** 8), rng.choice([1e-4, 1e-3, 5e-3]))
    r = kaynak_acigi(e, g)
    yakin(r['qubit_kati'], g['fiziksel_qubit'] / e['fiziksel_qubit'], 'qubit oranı', tol=1e-6 * max(1.0, g['fiziksel_qubit'] / e['fiziksel_qubit']))
    yakin(r['hata_kati'], e['hata_orani'] / g['hata_orani'], 'hata oranı', tol=1e-5)
    k = r['qubit_ikiye_katlanma']
    ok(e['fiziksel_qubit'] * 2 ** k >= g['fiziksel_qubit'], 'k katlanma açığı kapatır')
    ok(k == 0 or e['fiziksel_qubit'] * 2 ** (k - 1) < g['fiziksel_qubit'], 'k - 1 katlanma kapatmaz')
    eq(r['yeterli'], e['fiziksel_qubit'] >= g['fiziksel_qubit'] and e['hata_orani'] <= g['hata_orani'], 'yeterlilik iki koşulun birleşimi')
e = K(10, 0.01)
kaynak_acigi(e, K(20, 0.001))
eq(e, K(10, 0.01), 'girdi değişmez')
eq(kaynak_acigi(K(1, 0.001), K(2, 0.001))['qubit_ikiye_katlanma'], 1, 'tek fiziksel qubit sınırı')
iyi = K(10, 0.01)
for a, b in [(None, iyi), (iyi, None), ({'fiziksel_qubit': 10}, iyi), (dict(iyi, ek=1), iyi), (K(0, 0.01), iyi), (K(10.0, 0.01), iyi), (K(True, 0.01), iyi), (K(10, 0), iyi), (K(10, 1), iyi), (K(10, None), iyi), (K(10, True), iyi), (K(10, float('nan')), iyi), (iyi, K(10, -0.1))]:
    raises(ValueError, kaynak_acigi, a, b, msg='bozuk girdi reddedilir')
```

```hint
İki ayrı karşılaştırma yap: qubit sayısı (büyük olan iyi) ve hata oranı (küçük olan iyi). Katlanma sayısı `ceil(log2(oran))`'dır; açık yoksa 0.
```
:::

::: gorev 3 · Bir haberi altı soruyla denetle
`haber_denetimi(iddia)` işlevini yaz.

- `iddia`: tam şu altı anahtara sahip sözlük:
  - `'qubit_turu'`: `'fiziksel'`, `'mantiksal'` ya da `'belirtilmemis'`
  - `'problem'`: `'ornekleme'`, `'carpanlara_ayirma'`, `'optimizasyon'` ya da `'diger'`
  - `'sayi_bit'`: pozitif `int` ya da `None` (ayrılan sayının bit uzunluğu; problem çarpanlara ayırma değilse `None` olmalıdır)
  - `'hata_duzeltme'`, `'klasik_karsilastirma'`, `'hakemli'`: `bool`
- `uyarilar`: şu sırayla, koşulu tutanların listesi:
  1. `qubit_turu != 'mantiksal'` → `'mantiksal_qubit_degil'`
  2. `problem != 'carpanlara_ayirma'` → `'kripto_ile_ilgisiz'`
  3. `problem == 'carpanlara_ayirma'` ve (`sayi_bit` `None` ya da `< 2048`) → `'kucuk_sayi'`
  4. `hata_duzeltme` yok → `'hata_duzeltme_yok'`
  5. `klasik_karsilastirma` yok → `'klasik_karsilastirma_yok'`
  6. `hakemli` değil → `'hakemsiz'`
- `kripto_tehdidi`: yalnız ilk dört uyarının **hiçbiri** yoksa `True`.
- `sinif`: `kripto_tehdidi` ise `'acil'`; değilse ve problem çarpanlara ayırmaysa `'izlenmeli'`; değilse `'bilimsel_sonuc'`.
- Dönüş: `{'uyarilar': [...], 'kripto_tehdidi': ..., 'sinif': ...}`.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç "çarpanlara ayırma" kelimesini görünce alarm veriyor: 48 bitlik bir sayının sezgisel bir yöntemle ayrılmasını RSA'nın kırılması sayıyor.

```starter
def haber_denetimi(iddia):
    tehdit = iddia['problem'] == 'carpanlara_ayirma'
    return {'uyarilar': [], 'kripto_tehdidi': tehdit, 'sinif': 'acil' if tehdit else 'bilimsel_sonuc'}
```

```solution
def haber_denetimi(iddia):
    anahtarlar = {'qubit_turu', 'problem', 'sayi_bit', 'hata_duzeltme', 'klasik_karsilastirma', 'hakemli'}
    if not isinstance(iddia, dict) or set(iddia) != anahtarlar:
        raise ValueError('iddia tam altı anahtara sahip olmalı')
    if iddia['qubit_turu'] not in ('fiziksel', 'mantiksal', 'belirtilmemis'):
        raise ValueError('qubit_turu geçersiz')
    if iddia['problem'] not in ('ornekleme', 'carpanlara_ayirma', 'optimizasyon', 'diger'):
        raise ValueError('problem geçersiz')
    b = iddia['sayi_bit']
    if b is not None and (isinstance(b, bool) or not isinstance(b, int) or b < 1):
        raise ValueError('sayi_bit pozitif int ya da None olmalı')
    if iddia['problem'] != 'carpanlara_ayirma' and b is not None:
        raise ValueError('sayi_bit yalnız çarpanlara ayırmada verilir')
    for k in ('hata_duzeltme', 'klasik_karsilastirma', 'hakemli'):
        if not isinstance(iddia[k], bool):
            raise ValueError(f'{k} bool olmalı')
    faktor = iddia['problem'] == 'carpanlara_ayirma'
    kurallar = [
        ('mantiksal_qubit_degil', iddia['qubit_turu'] != 'mantiksal'),
        ('kripto_ile_ilgisiz', not faktor),
        ('kucuk_sayi', faktor and (b is None or b < 2048)),
        ('hata_duzeltme_yok', not iddia['hata_duzeltme']),
        ('klasik_karsilastirma_yok', not iddia['klasik_karsilastirma']),
        ('hakemsiz', not iddia['hakemli']),
    ]
    uyarilar = [ad for ad, tutar in kurallar if tutar]
    tehdit = not any(tutar for _, tutar in kurallar[:4])
    return {'uyarilar': uyarilar, 'kripto_tehdidi': tehdit, 'sinif': 'acil' if tehdit else ('izlenmeli' if faktor else 'bilimsel_sonuc')}
```

```test
need('haber_denetimi')
import random

def I(qt, pr, bit, hd, kk, hk):
    return {'qubit_turu': qt, 'problem': pr, 'sayi_bit': bit, 'hata_duzeltme': hd, 'klasik_karsilastirma': kk, 'hakemli': hk}

r = haber_denetimi(I('fiziksel', 'ornekleme', None, False, True, True))
eq(r, {'uyarilar': ['mantiksal_qubit_degil', 'kripto_ile_ilgisiz', 'hata_duzeltme_yok'], 'kripto_tehdidi': False, 'sinif': 'bilimsel_sonuc'}, 'üstünlük gösterisi: gerçek sonuç, kriptoyla ilgisiz')
r = haber_denetimi(I('fiziksel', 'carpanlara_ayirma', 48, False, False, False))
eq(r['uyarilar'], ['mantiksal_qubit_degil', 'kucuk_sayi', 'hata_duzeltme_yok', 'klasik_karsilastirma_yok', 'hakemsiz'], '48 bitlik sayı, hakemsiz ön baskı: beş uyarı')
eq((r['kripto_tehdidi'], r['sinif']), (False, 'izlenmeli'), 'alarm değil, izlenecek')
r = haber_denetimi(I('mantiksal', 'carpanlara_ayirma', 2048, True, True, True))
eq(r, {'uyarilar': [], 'kripto_tehdidi': True, 'sinif': 'acil'}, 'mantıksal qubit, hata düzeltme, 2048 bit: gerçek tehdit')
r = haber_denetimi(I('mantiksal', 'carpanlara_ayirma', 2048, True, False, False))
eq((r['uyarilar'], r['kripto_tehdidi']), (['klasik_karsilastirma_yok', 'hakemsiz'], True), 'son iki uyarı ciddiyeti düşürmez ama doğrulama ister')
eq(haber_denetimi(I('mantiksal', 'carpanlara_ayirma', 2047, True, True, True))['sinif'], 'izlenmeli', '2048 in bir altı: küçük sayı')
eq(haber_denetimi(I('mantiksal', 'carpanlara_ayirma', None, True, True, True))['uyarilar'], ['kucuk_sayi'], 'sayı boyutu verilmemiş: küçük sayılır')
eq(haber_denetimi(I('belirtilmemis', 'optimizasyon', None, True, True, True))['uyarilar'], ['mantiksal_qubit_degil', 'kripto_ile_ilgisiz'], 'qubit türü belirtilmemişse mantıksal sayılmaz')
rng = random.Random(3003)
for _ in range(30):
    pr = rng.choice(['ornekleme', 'carpanlara_ayirma', 'optimizasyon', 'diger'])
    it = I(rng.choice(['fiziksel', 'mantiksal', 'belirtilmemis']), pr, rng.choice([None, 21, 48, 2048, 4096]) if pr == 'carpanlara_ayirma' else None, rng.random() < 0.5, rng.random() < 0.5, rng.random() < 0.5)
    r = haber_denetimi(it)
    f = pr == 'carpanlara_ayirma'
    tehdit = it['qubit_turu'] == 'mantiksal' and f and it['sayi_bit'] is not None and it['sayi_bit'] >= 2048 and it['hata_duzeltme']
    eq(r['kripto_tehdidi'], tehdit, 'rastgele iddiada tehdit kararı')
    eq(r['sinif'], 'acil' if tehdit else ('izlenmeli' if f else 'bilimsel_sonuc'), 'rastgele iddiada sınıf')
    eq(('hakemsiz' in r['uyarilar'], 'klasik_karsilastirma_yok' in r['uyarilar']), (not it['hakemli'], not it['klasik_karsilastirma']), 'son iki uyarı')
    ok(not ('kripto_ile_ilgisiz' in r['uyarilar'] and 'kucuk_sayi' in r['uyarilar']), 'ilgisiz ve küçük sayı aynı anda çıkmaz')
it = I('fiziksel', 'ornekleme', None, False, True, True)
kopya = dict(it)
haber_denetimi(it)
eq(it, kopya, 'girdi değişmez')
eq(haber_denetimi(I('mantiksal', 'carpanlara_ayirma', 1, True, True, True))['uyarilar'], ['kucuk_sayi'], '1 bitlik sayı sınırı')
iyi = I('fiziksel', 'ornekleme', None, False, True, True)
eksik = dict(iyi); del eksik['hakemli']
for kotu in (None, {}, eksik, dict(iyi, ek=1), dict(iyi, qubit_turu='kubit'), dict(iyi, problem='sifreleme'), dict(iyi, sayi_bit=48), dict(iyi, problem='carpanlara_ayirma', sayi_bit=0), dict(iyi, problem='carpanlara_ayirma', sayi_bit=48.0), dict(iyi, problem='carpanlara_ayirma', sayi_bit=True), dict(iyi, hata_duzeltme=1), dict(iyi, hakemli=None), [iyi]):
    raises(ValueError, haber_denetimi, kotu, msg='bozuk iddia reddedilir')
```

```hint
Altı kuralı `(ad, tutar_mı)` çiftleri olarak sırayla yaz. Tehdit kararı yalnız ilk dördüne bakar; son ikisi doğrulama uyarısıdır.
```
:::

::: anlat 3. Bunu iki dakikada nasıl anlatırsın?
1. **Başlığı kabul et (15 sn).** "Bu haberlerin çoğu gerçek bir bilimsel sonucu anlatıyor. Sorun sonuçta değil, başlıkta."
2. **İki tür haber (30 sn).** "Biri şunu der: kuantum bilgisayar, klasik bilgisayarın yapamadığı bir işi yaptı. Doğru olabilir; ama o iş genellikle bu gösteri için seçilmiş, işe yaramaz bir hesaptır. Öbürü der ki: şifreleme kırıldı. Bakarsınız, ayrılan sayı birkaç on bitliktir; sizin bankanızınki iki bin kırk sekiz bit."
3. **Qubit sayısı (30 sn).** Tahmin adımındaki sayıları ver: "Bin qubit'lik işlemci dediklerinde, hata düzeltmeden sonra elinizde dört tane kullanılabilir qubit kalır; belki hiç. Bir şifreyi kırmak için binlercesi gerekir."
4. **Açık (25 sn).** "Bugünkü tahminlere göre gereken, bir milyon civarında fiziksel qubit ve bunların saatlerce hatasız çalışması. Tahminler her yıl düşüyor; açık hâlâ büyük."
5. **Kapanış (20 sn).** "Yani panik yok, ama rehavet de yok: bugün kaydedilen şifreli veri ileride açılabilir. Doğru tepki haberi paylaşmak değil, yeni şifrelemeye geçiş planını sormaktır."

Bir habere sorulacak altı soru: Qubit'ler fiziksel mi, mantıksal mı? Hangi problem çözüldü? Çarpanlara ayırmaysa sayı kaç bit? Hata düzeltme var mı? En iyi klasik yöntemle karşılaştırıldı mı? Hakem denetiminden geçti mi?
:::

::: anlat Sınır
Bu ders kuantum duyurularını sınıflandırmak için üç hesap verir; hiçbir cihaz ya da saldırı çalıştırılmaz. `2d² − 1` formülü döndürülmüş (`rotated`) surface code'un tek bir mantıksal qubit'i içindir; mantıksal kapılar, `magic state` üretimi ve qubit'ler arası yönlendirme ek alan ister ve gerçek bir hesapta toplam maliyet bunun birkaç katıdır. Başka kodlar (`qLDPC` gibi) aynı korumayı çok daha az fiziksel qubit'le vaat eder; bu yüzden "mantıksal qubit başına bin fiziksel qubit" bir sabit değil, bugünkü bir varsayımdır. Görev 2 kaynakları iki sayıya indirger; gerçek bir karşılaştırma bağlantı yapısını, kapı hızını, ölçüm hatasını ve hesabın süresini de içerir. Derste anılan kaynak tahminleri belirli donanım varsayımlarına dayanır ve yeni algoritmalarla defalarca düşmüştür; buradaki sayılar yazıldığı tarihteki literatürü yansıtır ve bir öngörü değildir. Görev 3'teki altı kural bir **ilk süzgeçtir**: 2048 bit eşiği bugün yaygın bir anahtar boyutudur, bir doğa yasası değil; eliptik eğri sistemleri daha az kaynakla kırılır ve liste yalnız çarpanlara ayırmayı tanır. Hakem denetimi bir sonucun doğru olduğunu garanti etmez; hakemsiz bir ön baskı da yanlış olmak zorunda değildir. Bir cihazın **ne zaman** yeterli olacağı bu dersin hesaplarından çıkmaz.

Kaynaklar: [Arute vd. 2019 - Quantum supremacy using a programmable superconducting processor](https://doi.org/10.1038/s41586-019-1666-5), [Gidney ve Ekerå 2021 - How to factor 2048 bit RSA integers in 8 hours using 20 million noisy qubits](https://arxiv.org/abs/1905.09749), [Gidney 2025 - How to factor 2048 bit RSA integers with less than a million noisy qubits](https://arxiv.org/abs/2505.15917), [Fowler vd. 2012 - Surface codes: Towards practical large-scale quantum computation](https://arxiv.org/abs/1208.0928), [Yan vd. 2022 - Factoring integers with sublinear resources on a superconducting quantum processor](https://arxiv.org/abs/2212.12372), [Pan, Chen ve Zhang 2022 - Solving the sampling problem of the Sycamore quantum circuits](https://arxiv.org/abs/2111.03011).
:::

::: dusun
Bir şirket "6.100 qubit'lik işlemcimizle 2029'da RSA'yı kıracağız" diye duyuru yapıyor. Altı sorudan hangilerinin cevabı duyuruda yok? Görev 1'i kullanarak, qubit'lerin fiziksel olduğunu ve mesafe 25'te çalışıldığını varsayarsan kaç mantıksal qubit eder? Yöneticine bu duyuru hakkında iki cümleyle ne söylerdin?
:::

::: ozet
- Bir duyurudaki qubit sayısı fizikseldir; surface code'da bir mantıksal qubit yaklaşık `2d² − 1` fiziksel qubit ister.
- Kuantum üstünlüğü gösterileri gerçek sonuçlardır ama seçilen problem kriptografiyle ilgisizdir ve klasik karşılaştırma zamanla değişir.
- Bugüne kadar kuantum bilgisayarla ayrılan sayılar çok küçüktür; RSA-2048 için tahminler milyon mertebesinde fiziksel qubit ister.
- Bir cihazın yeterliliği hem qubit sayısına hem hata oranına bağlıdır; biri tek başına yetmez.
- Bir habere altı soru sorulur: qubit türü, problem, sayı boyutu, hata düzeltme, klasik karşılaştırma, hakem denetimi.
:::
