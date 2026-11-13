---
id: ai-temel-42
title: "AGI Tahminleri Nasıl Okunur? · Benchmark Doygunluğu, Belirsizlik ve Abartı"
summary: Bir benchmark'ın ne zaman doyduğunu, uzman tahminlerinin ne kadar dağıldığını ve bir tahmincinin geçmişte ne kadar isabetli olduğunu ölç; "AGI şu yıl geliyor" başlıklarını sayılarla oku ve iki dakikada anlat.
---

::: anlat 1. Soru: "AGI ne zaman geliyor?"
Bu soruya verilen cevaplar "iki yıl içinde" ile "bu yüzyılda değil" arasında değişir ve cevap verenlerin çoğu konunun uzmanıdır. Dinleyicine bir yıl söylemek yerine, **bir tahmini nasıl okuyacağını** öğretmek daha dürüsttür. Her tahminin içinde üç gizli seçim vardır:

| Gizli seçim | Soru | Görev |
|---|---|---|
| Ölçü | "İnsan düzeyi" hangi testle tanımlandı ve o test doydu mu? | 1 |
| Dağılım | Tek bir yıl mı söyleniyor, yoksa bir aralık mı? Uzmanlar ne kadar ayrışıyor? | 2 |
| Sicil | Bu tahminci geçmişte ne kadar isabetliydi? | 3 |

Önce tanım sorunu: `AGI` (artificial general intelligence) için üzerinde uzlaşılmış bir tanım yoktur. Bazıları "ekonomik değeri olan işlerin çoğunda insanı geçmek", bazıları "bir insanın öğrenebildiği her şeyi öğrenebilmek", bazıları "belirli bir sınavı geçmek" der. Morris ve arkadaşları (2023) bu yüzden tek bir eşik yerine **düzeyler** önermiştir (performans × genellik). Tanım değişince tarih de değişir; iki kişi farklı yıllar söylüyorsa çoğu zaman farklı şeylerden söz ediyordur.

> [!NOT]
> Bu ders bir AGI tarihi vermez ve hangi tahminin doğru olduğunu söylemez. Görevlerdeki sayılar sentetiktir; gerçek anket ve benchmark bulguları anlatımda kaynaklarıyla verilir.
:::

::: anlat 2. Benchmark doygunluğu: ölçü tavana vurduğunda
Bir benchmark, modellerin skoru insan düzeyine ya da olası en yüksek puana yaklaştığında **doyar** (`saturation`): artık modelleri birbirinden ayıramaz ve ilerlemeyi ölçemez. Kiela ve arkadaşları (2021) bunun giderek hızlandığını gösterdi: MNIST'in doyması yirmi yıla yakın sürdü, sonraki dil benchmark'larından bazıları bir iki yılda doydu.

Doygunluk iki farklı şeyi gösterebilir ve başlıklar bunları karıştırır:

- **Yetenek gerçekten arttı.** Model o işi öğrendi.
- **Benchmark'ın kendisi çözüldü.** Sorular eğitim verisine sızdı, model sorulardaki istatistiksel ipuçlarını öğrendi ya da geliştiriciler o benchmark'a göre ayar yaptı. Buna Goodhart yasası denir: bir ölçü hedef hâline geldiğinde iyi bir ölçü olmaktan çıkar.

"Model X sınavında insanı geçti" cümlesi bu yüzden tek başına bir şey söylemez. Doğru sorular: Test ne zaman yayımlandı? Sorular gizli mi? Aynı yeteneği ölçen **yeni** bir testte sonuç ne (bkz. `ai-temel-40`)?
:::

::: anlat 3. Uzman tahminleri: tek sayı değil, dağılım
Grace ve arkadaşları (2024), 2.778 AI araştırmacısına "yardımsız makinelerin her işi insandan daha iyi ve ucuza yapabilmesi" için tahminlerini sordu. Toplu tahmin, bunun %50 olasılıkla 2047'ye kadar olacağıydı; bir yıl önceki ankette bu tarih 2060'tı. Bu sonuçtan çıkarılacak üç ders vardır:

1. **Tek yıl yanıltır.** 2047 bir medyandır. Yanıtların dağılımı çok geniştir: bazı araştırmacılar birkaç yıl, bazıları yüz yıldan fazla der.
2. **Tahminler kayar.** Aynı topluluk bir yılda tarihi 13 yıl öne çekti. Bu, tahminin ne kadar kararsız olduğunu gösterir.
3. **Sorunun yazılışı sonucu değiştirir.** Aynı ankette "bütün işler" yerine "bütün meslekler" diye sorulduğunda tarih onlarca yıl ileri gitti. Mantıken çok yakın iki soru, çok farklı cevaplar aldı.

Bir tahmini değerlendirmenin sağlam yolu geçmişine bakmaktır. Meteorolog Glenn Brier 1950'de bunun için bir ölçü önerdi (`Brier score`): tahmin edilen olasılık ile gerçekleşen sonuç (1 ya da 0) arasındaki farkın karesinin ortalaması. 0 kusursuzdur; her şeye %50 diyen biri 0.25 alır. Her zaman emin konuşan ama yarısında yanılan biri 0.25'ten **kötü** puan alır.

AI tahminlerinin zorluğu şudur: uzun vadeli tek seferlik bir olayın tahmincisi için sicil yoktur. Bu yüzden kısa vadeli, sınanabilir tahminlerdeki sicile bakılır.
:::

::: tahmin Tanım değişince tarih değişir
Aynı skor serisi iki farklı "insan düzeyi" tanımıyla okunuyor. Ne yazdırılır?

```python
skorlar = {2019: 61, 2020: 74, 2021: 83, 2022: 89, 2023: 93, 2024: 95}

def ilk_yil(esik):
    return next((yil for yil, s in skorlar.items() if s >= esik), None)

print("ortalama insan (85):", ilk_yil(85))
print("uzman insan (96):  ", ilk_yil(96))
```

???

```cikti
ortalama insan (85): 2022
uzman insan (96):   None
```
Aynı veriden biri "2022'de insan düzeyine ulaşıldı", diğeri "hâlâ ulaşılmadı" sonucunu çıkarır. İkisi de doğrudur; farklı eşiklerden söz ediyorlar. Bir başlıkta "insan düzeyi" gördüğünde ilk sorman gereken şey budur: hangi insan, hangi test, hangi eşik?
:::

::: gorev 1 · Benchmark ne zaman doydu?
`doygunluk(skorlar, tavan, esik)` işlevini yaz. Bir benchmark'ın yıllık en iyi skorlarını alır; kalan boşluğu ve doygunluk yılını döndürür.

- `skorlar`: boş olmayan liste; her öğe `(yil, skor)`. Yıllar `int` ve **kesin artan**, skorlar sayı.
- `tavan`: pozitif sayı (insan düzeyi ya da olası en yüksek puan). `esik`: `(0, 1]` aralığında sayı.
- `kalan`: her yıl için `tavan - skor` (tavanı aşan skor negatif kalır; kırpma yapılmaz).
- `doygunluk_yili`: skorun ilk kez `esik · tavan` değerine ulaştığı ya da onu geçtiği yıl; yoksa `None`.
- `sure`: doygunluk yılı ile ilk ölçüm yılı arasındaki fark; doymadıysa `None`.
- Dönüş: `{'kalan': [...], 'doygunluk_yili': ..., 'sure': ...}`. `kalan` değerleri 6 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç doygunluğu **son** ölçüme bakarak ilan ediyor ve yıl olarak son yılı veriyor. Benchmark üç yıl önce doyduysa bunu göremezsin.

```starter
def doygunluk(skorlar, tavan, esik):
    kalan = [round(tavan - s, 6) for _, s in skorlar]
    son_yil, son = skorlar[-1]
    yil = son_yil if son >= esik * tavan else None
    return {'kalan': kalan, 'doygunluk_yili': yil, 'sure': None if yil is None else yil - skorlar[0][0]}
```

```solution
def doygunluk(skorlar, tavan, esik):
    import math
    def sayi(x):
        return not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x)
    if not isinstance(skorlar, list) or not skorlar:
        raise ValueError('skorlar boş olmayan liste olmalı')
    if not sayi(tavan) or not tavan > 0:
        raise ValueError('tavan pozitif sayı olmalı')
    if not sayi(esik) or not 0 < esik <= 1:
        raise ValueError('esik (0, 1] aralığında olmalı')
    onceki = None
    for s in skorlar:
        if not isinstance(s, (tuple, list)) or len(s) != 2 or isinstance(s[0], bool) or not isinstance(s[0], int) or not sayi(s[1]):
            raise ValueError('öğe (yil, skor) olmalı')
        if onceki is not None and not s[0] > onceki:
            raise ValueError('yıllar kesin artan olmalı')
        onceki = s[0]
    yil = next((y for y, s in skorlar if s >= esik * tavan), None)
    return {
        'kalan': [round(tavan - s, 6) for _, s in skorlar],
        'doygunluk_yili': yil,
        'sure': None if yil is None else yil - skorlar[0][0],
    }
```

```test
need('doygunluk')
import random

def _ref(sk, tavan, esik):
    yil = None
    for i in range(len(sk)):
        if yil is None and sk[i][1] >= esik * tavan:
            yil = sk[i][0]
    return {'kalan': [round(tavan - x[1], 6) for x in sk], 'doygunluk_yili': yil, 'sure': None if yil is None else yil - sk[0][0]}

sk = [(2019, 61), (2020, 74), (2021, 83), (2022, 89), (2023, 93), (2024, 95)]
eq(doygunluk(sk, 100, 0.85), {'kalan': [39, 26, 17, 11, 7, 5], 'doygunluk_yili': 2022, 'sure': 3}, 'ilk aşılan yıl, son yıl değil')
eq(doygunluk(sk, 100, 0.96)['doygunluk_yili'], None, 'eşiğe ulaşılmadı')
eq(doygunluk(sk, 100, 0.96)['sure'], None, 'doymadıysa süre None')
eq(doygunluk([(2020, 90), (2021, 80)], 100, 0.9), {'kalan': [10, 20], 'doygunluk_yili': 2020, 'sure': 0}, 'sonradan düşen skor ilk doygunluğu değiştirmez')
eq(doygunluk([(2021, 104.5)], 100, 1.0), {'kalan': [-4.5], 'doygunluk_yili': 2021, 'sure': 0}, 'tavanı aşan skor negatif kalan verir')
eq(doygunluk([(2020, 0.61), (2023, 0.92)], 0.95, 0.95)['doygunluk_yili'], 2023, 'kesirli tavan: 0.92 >= 0.9025')
rng = random.Random(4201)
for _ in range(25):
    y, s, sk = 2000, 20.0, []
    for _ in range(rng.randint(1, 10)):
        y += rng.randint(1, 3)
        s = round(s + rng.uniform(-3, 15), 2)
        sk.append((y, s))
    tavan = rng.choice([80, 100, 97.5])
    esik = rng.choice([0.5, 0.8, 0.9, 1.0])
    eq(doygunluk(sk, tavan, esik), _ref(sk, tavan, esik), 'rastgele seride bağımsız referansla aynı')
iyi = [(2020, 50), (2021, 60)]
for a in ([None, 100, 0.9], [[], 100, 0.9], [['ab'], 100, 0.9], [iyi, 0, 0.9], [iyi, -5, 0.9], [iyi, True, 0.9], [iyi, float('nan'), 0.9], [iyi, float('inf'), 0.9], [iyi, 100, 0], [iyi, 100, 1.1], [iyi, 100, None], [iyi, 100, True], [iyi, 100, float('nan')], [[(2020, 50), (2020, 60)], 100, 0.9], [[(2021, 50), (2020, 60)], 100, 0.9], [[(2020.0, 50)], 100, 0.9], [[(True, 50)], 100, 0.9], [[(2020, True)], 100, 0.9], [[(2020, float('nan'))], 100, 0.9], [[(2020, float('inf'))], 100, 0.9], [[(2020,)], 100, 0.9], [[(2020, "50")], 100, 0.9], [tuple(iyi), 100, 0.9]):
    raises(ValueError, doygunluk, *a, msg='bozuk girdi reddedilir')
```

```hint
Doygunluk yılı, `skor >= esik * tavan` koşulunu sağlayan **ilk** öğenin yılıdır: `next((y for y, s in skorlar if ...), None)`.
```
:::

::: gorev 2 · Uzman tahminlerinin dağılımı
`tahmin_ozeti(tahminler)` işlevini yaz. Bir grup uzmanın "şu yılda olur" tahminlerini alır; tek bir sayı yerine dağılımı özetler.

- `tahminler`: boş olmayan liste; her öğe bir yıl (`int`) ya da `None` ("asla" diyen uzman).
- Çeyrekler yalnız yıl veren tahminlerden, **doğrusal ara değerle** hesaplanır: sıralı listede konum `p · (n - 1)`; tam sayı değilse iki komşu değer arasında ara değer alınır.
- Dönüş: `{'medyan': ..., 'q1': ..., 'q3': ..., 'aralik': q3 - q1, 'asla_orani': None sayısı / toplam}`. Hiç yıl yoksa ilk dördü `None`. Sayılar 4 basamağa yuvarlanır.
- Bozuk girdi `ValueError` (`bool` bir yıl değildir).

KUSURLU başlangıç yalnız ortalamayı raporluyor ve "asla" diyenleri sessizce atıyor. Tek bir uç tahmin ortalamayı sürükler; atılan cevaplar da belirsizliğin en büyük kısmıdır.

```starter
def tahmin_ozeti(tahminler):
    y = [t for t in tahminler if t is not None]
    ort = round(sum(y) / len(y), 4)
    return {'medyan': ort, 'q1': ort, 'q3': ort, 'aralik': 0.0, 'asla_orani': 0.0}
```

```solution
def tahmin_ozeti(tahminler):
    if not isinstance(tahminler, list) or not tahminler:
        raise ValueError('tahminler boş olmayan liste olmalı')
    for t in tahminler:
        if t is not None and (isinstance(t, bool) or not isinstance(t, int)):
            raise ValueError('tahmin int yıl ya da None olmalı')
    y = sorted(t for t in tahminler if t is not None)
    asla = round((len(tahminler) - len(y)) / len(tahminler), 4)
    if not y:
        return {'medyan': None, 'q1': None, 'q3': None, 'aralik': None, 'asla_orani': asla}

    def ceyrek(p):
        konum = p * (len(y) - 1)
        alt = int(konum)
        ust = min(alt + 1, len(y) - 1)
        return y[alt] + (konum - alt) * (y[ust] - y[alt])

    q1, med, q3 = ceyrek(0.25), ceyrek(0.5), ceyrek(0.75)
    return {'medyan': round(med, 4), 'q1': round(q1, 4), 'q3': round(q3, 4), 'aralik': round(q3 - q1, 4), 'asla_orani': asla}
```

```test
need('tahmin_ozeti')
import random, statistics

def _ref(t):
    y = sorted(x for x in t if x is not None)
    asla = round(t.count(None) / len(t), 4)
    if not y:
        return {'medyan': None, 'q1': None, 'q3': None, 'aralik': None, 'asla_orani': asla}
    if len(y) == 1:
        q1 = med = q3 = float(y[0])
    else:
        q = statistics.quantiles(y, n=4, method='inclusive')
        q1, med, q3 = q[0], q[1], q[2]
    return {'medyan': round(med, 4), 'q1': round(q1, 4), 'q3': round(q3, 4), 'aralik': round(q3 - q1, 4), 'asla_orani': asla}

eq(tahmin_ozeti([2030, 2040, 2050, 2060, 2070]), {'medyan': 2050, 'q1': 2040, 'q3': 2060, 'aralik': 20, 'asla_orani': 0.0}, 'beş tahmin: çeyrekler tam öğelere düşer')
eq(tahmin_ozeti([2030, 2040, 2050, 2060]), {'medyan': 2045.0, 'q1': 2037.5, 'q3': 2052.5, 'aralik': 15.0, 'asla_orani': 0.0}, 'dört tahmin: doğrusal ara değer')
eq(tahmin_ozeti([2040, None, 2030, None]), {'medyan': 2035.0, 'q1': 2032.5, 'q3': 2037.5, 'aralik': 5.0, 'asla_orani': 0.5}, 'asla diyenler oran olarak raporlanır, sıra önemsiz')
eq(tahmin_ozeti([None, None]), {'medyan': None, 'q1': None, 'q3': None, 'aralik': None, 'asla_orani': 1.0}, 'hiç yıl yok')
eq(tahmin_ozeti([2045]), {'medyan': 2045, 'q1': 2045, 'q3': 2045, 'aralik': 0, 'asla_orani': 0.0}, 'tek tahmin')
r = tahmin_ozeti([2030, 2032, 2035, 2038, 2300])
eq(r['medyan'], 2035, 'uç tahmin medyanı sürüklemez')
rng = random.Random(4202)
for _ in range(30):
    t = [None if rng.random() < 0.2 else rng.randint(2026, 2150) for _ in range(rng.randint(1, 25))]
    got, exp = tahmin_ozeti(t), _ref(t)
    for k in ('medyan', 'q1', 'q3', 'aralik', 'asla_orani'):
        if exp[k] is None:
            eq(got[k], None, f'rastgele tahminlerde {k}')
        else:
            yakin(got[k], exp[k], f'rastgele tahminlerde {k}', tol=1e-3)
t = [2050, None, 2030]
tahmin_ozeti(t)
eq(t, [2050, None, 2030], 'girdi değişmez')
for kotu in (None, [], [2030.5], [True], ["2030"], (2030, 2040), [2030, [2040]]):
    raises(ValueError, tahmin_ozeti, kotu, msg='bozuk girdi reddedilir')
```

```hint
Önce `None` olmayanları sırala. `konum = p * (n - 1)`; `alt = int(konum)`; sonuç `y[alt] + (konum - alt) * (y[alt + 1] - y[alt])`. Son öğede taşmamak için üst indeksi sınırla.
```
:::

::: gorev 3 · Tahmincinin sicili: Brier score
`brier_skoru(kayitlar)` işlevini yaz. Bir tahmincinin geçmişte verdiği olasılıkları ve olayların gerçekleşip gerçekleşmediğini alır.

- `kayitlar`: boş olmayan liste; her öğe `(olasilik, gerceklesti)`; olasılık `[0, 1]` aralığında sayı, `gerceklesti` `bool`.
- `brier`: `(olasilik - sonuç)²` değerlerinin ortalaması; sonuç gerçekleştiyse 1, değilse 0.
- `referans`: her şeye 0.5 diyen birinin puanı, yani `0.25`.
- `beceri`: `1 - brier / referans`. Pozitifse yazı tura atmaktan iyi, negatifse kötü.
- Dönüş: `{'brier': ..., 'referans': 0.25, 'beceri': ...}`; 6 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç tahmini 0.5'ten yuvarlayıp isabet oranına bakıyor. %51 diyen ile %99 diyen aynı puanı alır; aşırı güvenin bedeli görünmez.

```starter
def brier_skoru(kayitlar):
    yanlis = sum(1 for p, o in kayitlar if (p >= 0.5) != o) / len(kayitlar)
    return {'brier': round(yanlis, 6), 'referans': 0.25, 'beceri': round(1 - yanlis / 0.25, 6)}
```

```solution
def brier_skoru(kayitlar):
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError('kayitlar boş olmayan liste olmalı')
    for k in kayitlar:
        if not isinstance(k, (tuple, list)) or len(k) != 2:
            raise ValueError('kayıt (olasilik, gerceklesti) olmalı')
        p, o = k
        if isinstance(p, bool) or not isinstance(p, (int, float)) or not 0 <= p <= 1 or not isinstance(o, bool):
            raise ValueError('olasılık [0, 1] aralığında sayı, sonuç bool olmalı')
    brier = sum((p - (1 if o else 0)) ** 2 for p, o in kayitlar) / len(kayitlar)
    return {'brier': round(brier, 6), 'referans': 0.25, 'beceri': round(1 - brier / 0.25, 6)}
```

```test
need('brier_skoru')
import random

def _ref(k):
    t = 0.0
    for p, o in k:
        t += (p - 1.0) ** 2 if o else p ** 2
    b = t / len(k)
    return {'brier': round(b, 6), 'referans': 0.25, 'beceri': round(1 - 4 * b, 6)}

eq(brier_skoru([(1.0, True), (0.0, False)]), {'brier': 0.0, 'referans': 0.25, 'beceri': 1.0}, 'kusursuz tahminci')
eq(brier_skoru([(0.5, True), (0.5, False)]), {'brier': 0.25, 'referans': 0.25, 'beceri': 0.0}, 'her şeye yüzde 50 diyen')
eq(brier_skoru([(1.0, False), (1.0, True)]), {'brier': 0.5, 'referans': 0.25, 'beceri': -1.0}, 'hep emin, yarısında yanlış: yazı turadan kötü')
a = brier_skoru([(0.51, True), (0.51, False)])['brier']
b = brier_skoru([(0.99, True), (0.99, False)])['brier']
ok(b > a, 'aynı isabetle aşırı güven daha kötü puan alır', got=(a, b))
eq(brier_skoru([(0.8, True), (0.8, True), (0.8, True), (0.8, True), (0.8, False)]), {'brier': 0.16, 'referans': 0.25, 'beceri': 0.36}, 'yüzde 80 diyen ve yüzde 80 tutturan')
eq(brier_skoru([[0.3, False]]), {'brier': 0.09, 'referans': 0.25, 'beceri': 0.64}, 'liste biçimli kayıt kabul edilir')
rng = random.Random(4203)
for _ in range(25):
    k = [(round(rng.random(), 3), rng.random() < 0.5) for _ in range(rng.randint(1, 30))]
    got, exp = brier_skoru(k), _ref(k)
    yakin(got['brier'], exp['brier'], 'rastgele kayıtlarda brier', tol=2e-6)
    yakin(got['beceri'], exp['beceri'], 'rastgele kayıtlarda beceri', tol=5e-6)
    eq(got['referans'], 0.25, 'referans sabit')
for kotu in (None, [], [(0.5,)], [(1.2, True)], [(-0.1, True)], [(float('nan'), True)], [(True, True)], [(0.5, 1)], [("0.5", True)], [(0.5, True, False)], [(0.5, True, 1)], ((0.5, True),), [0.5]):
    raises(ValueError, brier_skoru, kotu, msg='bozuk kayıt reddedilir')
```

```hint
Sonucu sayıya çevir: gerçekleştiyse 1, değilse 0. Her kayıt için `(p - sonuç) ** 2`, sonra ortalama. `beceri = 1 - brier / 0.25`.
```
:::

::: anlat 4. Bir AGI başlığını okuma listesi
Bir haber, bir CEO açıklaması ya da bir makale "AGI şu yıl" dediğinde şu altı soruyu sor. Her biri bu derste ölçtüğün bir şeye karşılık gelir.

| Soru | Neden |
|---|---|
| AGI nasıl tanımlandı? | Tanım değişince tarih değişir (Tahmin adımı). |
| Hangi ölçüye dayanıyor ve o ölçü doydu mu? | Doymuş benchmark ilerlemeyi ölçmez (Görev 1). |
| Tek yıl mı, aralık mı? | Tek yıl, dağılımın üstünü örter (Görev 2). |
| Tahmincinin sınanabilir geçmiş tahminleri var mı? | Sicil olmadan güven ölçülemez (Görev 3). |
| Tahmincinin çıkarı ne? | Yatırım toplayan bir şirketin "yakında" demesi ile bir eleştirmenin "asla" demesi aynı ihtiyatla okunur. |
| Eğilim neye dayanarak uzatılıyor? | Üstel bir eğriyi uzatmak, onu sınırlayan veri, enerji ve maliyeti yok sayar (bkz. `ai-temel-41`). |

İki yönde de abartı vardır. "İki yıl içinde her şey değişecek" ile "bunlar sadece otomatik tamamlama, hiçbir şey olmayacak" cümleleri aynı hatayı yapar: geniş bir belirsizliği tek bir kesin cümleye indirger. Dürüst cevap genellikle sıkıcıdır: "Uzmanların medyanı şu, aralık bu kadar geniş ve tanıma göre değişiyor."
:::

::: anlat 5. Yaygın yanlışlar ve iki dakikalık anlatım
| Yanlış | Doğrusu |
|---|---|
| "Uzmanlar 2047 diyor." | 2047 bir medyandır; yanıtlar birkaç yıl ile yüz yılı aşkın arasında dağılır. |
| "Model sınavda insanı geçti, AGI geldi." | Bir sınavı geçmek dar bir ölçüdür; sınav doymuş ya da sızmış olabilir. |
| "Eğri üstel, öyleyse devam eder." | Üstel görünen eğrilerin çoğu bir süre sonra düzleşir; sınırlar gerçektir. |
| "Emin konuşan uzman daha güvenilirdir." | Brier score aşırı güveni cezalandırır; sicile bak. |
| "Tahminler tutmuyor, öyleyse hiçbir şey olmayacak." | Belirsizlik iki yönlüdür; erken de olabilir, geç de. |

**İki dakikada anlatım iskeleti:**

1. **Soruyu çevir (20 sn).** "Size bir yıl söylemeyeceğim; bir yıl söyleyeni nasıl sınayacağınızı söyleyeceğim."
2. **Tanım (25 sn).** Tahmin adımındaki örnek: aynı veriyle biri "2022'de ulaştık", diğeri "ulaşmadık" diyor. "Hangi insan, hangi test?"
3. **Dağılım (30 sn).** "Binlerce araştırmacıya soruldu. Ortanca 2047 çıktı; bir yıl önce 2060'tı. Bir yılda 13 yıl kaydı. Bu kadar kayan bir sayıya tarih denmez, aralık denir."
4. **Sicil (25 sn).** "Hava tahmincisini nasıl sınarsınız? Geçmişte 'yüzde 80' dediği günlerin yüzde 80'inde yağmur yağdı mı diye bakarsınız. AI tahmincisine de aynısını sorun."
5. **Kapanış (20 sn).** "Emin konuşana değil, aralık verene ve geçmişi sınanabilene güvenin."
:::

::: anlat Sınır
Bu ders AGI tahminlerini okumak için üç ölçü verir; bir tarih öngörmez. Görevlerdeki skor serileri ve tahmin listeleri sentetiktir. Doygunluk ölçüsü tavanın doğru bilindiğini varsayar; insan düzeyi çoğu benchmark'ta küçük bir örneklemden ölçülür ve kendisi belirsizdir. Çeyrekler küçük örneklemde kararsızdır ve anketlerde yanıt verenler bütün araştırmacıları temsil etmeyebilir (yanıtlama yanlılığı). Grace ve arkadaşlarının bulguları belirli bir anket, belirli soru yazımları ve belirli bir tarih içindir; soru yazımına duyarlılık bulgunun kendisinin parçasıdır. Brier score, çok sayıda sınanabilir tahmin gerektirir; uzun vadeli tek seferlik bir olay için hesaplanamaz ve kısa vadedeki isabet uzun vadedeki isabeti garanti etmez. "AGI" için uzlaşılmış bir tanım olmadığından bu derste bir tanım savunulmaz.

Kaynaklar: [Grace vd. 2024 - Thousands of AI Authors on the Future of AI](https://arxiv.org/abs/2401.02843), [Morris vd. 2023 - Levels of AGI](https://arxiv.org/abs/2311.02462), [Kiela vd. 2021 - Dynabench: Rethinking Benchmarking in NLP](https://arxiv.org/abs/2104.14337), [Brier 1950 - Verification of forecasts expressed in terms of probability](https://doi.org/10.1175/1520-0493%281950%29078%3C0001:VOFEIT%3E2.0.CO;2).
:::

::: dusun
Bir şirket yöneticisi sahnede "üç yıl içinde AGI'ye ulaşacağız" diyor. Dördüncü bölümdeki altı sorudan hangi üçünü ona sorardın? Her biri için: hangi cevap tahmini daha inandırıcı kılar, hangisi daha az? Sonra aynı üç soruyu "AGI bu yüzyılda gelmez" diyen bir akademisyene uygula.
:::

::: ozet
- AGI için uzlaşılmış bir tanım yoktur; tanım ve eşik değişince tahmin edilen tarih değişir.
- Doymuş bir benchmark ilerlemeyi ölçemez. Doygunluk gerçek yetenekten de, sızıntı ve benchmark'a göre ayardan da gelebilir.
- Uzman tahminleri tek sayı değil dağılımdır: medyanı çeyreklerle ve "asla" diyenlerin oranıyla birlikte ver.
- Bir tahminciyi sicilinden tanırsın. Brier score aşırı güveni cezalandırır; her şeye %50 diyen 0.25 alır.
- İki yöndeki abartı da geniş bir belirsizliği kesin bir cümleye indirger. Aralık veren ve geçmişi sınanabilen tahmine güven.
:::
