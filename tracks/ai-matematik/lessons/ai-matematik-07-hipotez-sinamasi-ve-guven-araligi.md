---
id: ai-matematik-07
title: "Hipotez Sınaması ve Güven Aralığı · Fark Gerçek mi, Şans mı?"
summary: Bir oran için Wilson güven aralığını, iki oran arasındaki fark için z-testini ve herhangi bir istatistik için bootstrap aralığını yaz; p-değerinin ne söylediğini ve ne söylemediğini hesapla.
---

::: anlat 1. İki soru
`ai-matematik-06` bir ölçümün ne kadar oynadığını verdi. Şimdi o bilgiyi iki karara çevireceksin:

| Soru | Araç | Görev |
|---|---|---|
| Gerçek değer hangi aralıkta? | Güven aralığı (`confidence interval`) | 1 |
| İki sistem arasındaki fark şansla açıklanabilir mi? | Hipotez sınaması, `p-value` | 2 |
| Formülü olmayan bir ölçü için aralık nasıl bulunur? | `Bootstrap` | 3 |

**Güven aralığı.** %95 güven aralığı şu anlama gelir: aynı deneyi çok kez tekrarlayıp her seferinde bu yöntemle bir aralık kursan, aralıkların %95'i gerçek değeri içerir. "Gerçek değer %95 olasılıkla bu aralıktadır" demek değildir; ama pratikte "makul değerler bunlar" diye okunur.

**Hipotez sınaması.** Önce bir **sıfır hipotezi** kurarsın: "iki sistem aslında aynı". Sonra şunu sorarsın: sıfır hipotezi doğru olsaydı, gözlediğim kadar ya da daha büyük bir farkı görme olasılığım ne olurdu? Bu olasılık `p-value`'dur. Küçükse (alışılmış eşik 0,05) "fark şansla açıklanması zor" dersin.
:::

::: anlat 2. Üç araç
**Wilson aralığı.** Bir oran için en basit aralık $\hat{p} \pm z \cdot \mathrm{SE}$'dir, ama oran 0 ya da 1'e yakınken ve örnek azken bozulur: 20 soruda 20 doğru için aralık `[1, 1]` çıkar. Wilson aralığı bunu düzeltir:

$$\frac{\hat{p} + \dfrac{z^2}{2n} \pm z\sqrt{\dfrac{\hat{p}(1 - \hat{p})}{n} + \dfrac{z^2}{4n^2}}}{1 + \dfrac{z^2}{n}}$$

%95 güven için $z = 1{,}96$'dır. Aralık her zaman `[0, 1]` içinde kalır ve 20'de 20 için alt sınır yaklaşık 0,84 çıkar: "kusursuz" değil, "en az %84".

**İki oran için z-testi.** İki sistemin doğru sayıları $d_1 / n_1$ ve $d_2 / n_2$ olsun. Sıfır hipotezi altında ortak oran $\hat{p} = (d_1 + d_2) / (n_1 + n_2)$'dir ve test istatistiği:

$$z = \frac{\hat{p}_1 - \hat{p}_2}{\sqrt{\hat{p}(1 - \hat{p})\left(\dfrac{1}{n_1} + \dfrac{1}{n_2}\right)}}$$

İki yönlü `p-value`, standart normal dağılımın $\lvert z \rvert$'den uzak kuyruklarının toplamıdır: $\mathrm{erfc}(\lvert z \rvert / \sqrt{2})$.

**Bootstrap.** Medyan, iki ölçünün oranı ya da karmaşık bir skor için kapalı formül yoktur. Bootstrap şunu yapar: elindeki `n` örnekten, yerine koyarak `n` örnek çek; istatistiği hesapla; bunu binlerce kez tekrarla. Elde ettiğin değerlerin yayılımı, istatistiğin belirsizliğidir. Sıralayıp %2,5 ve %97,5 noktalarını alırsan %95 aralığı bulursun.

**p-value ne değildir.** Sıfır hipotezinin doğru olma olasılığı değildir. Farkın büyüklüğünü söylemez: çok büyük bir testte önemsiz bir fark da "anlamlı" çıkar. Yirmi farklı karşılaştırma yaparsan, hiçbir gerçek fark olmasa bile birinin 0,05'in altına düşmesi beklenir (`multiple comparisons`).
:::

::: tahmin 1,96 nereden geliyor?
Standart normal dağılımda iki farklı `z` değeri için iki yönlü `p-value` ne yazdırılır?

```python
import math

for z in (1.0, 1.96, 3.0):
    p = math.erfc(z / math.sqrt(2))
    print(z, round(p, 4))
```

???

```cikti
1.0 0.3173
1.96 0.05
3.0 0.0027
```
`z = 1` (bir standart hata uzakta) için `p ≈ 0,32`: sıfır hipotezi doğruyken bu kadar farkı üç denemeden birinde görürsün; kanıt değildir. `z = 1,96` tam olarak 0,05 eşiğine denk gelir; "%95 güven" ve "1,96 standart hata" aynı şeyin iki adıdır. `z = 3` için `p ≈ 0,003`'tür.
:::

::: gorev 1 · Wilson güven aralığı
`wilson_araligi(dogru, toplam, z)` işlevini yaz.

- `dogru`, `toplam`: `int`; `0 <= dogru <= toplam`, `toplam >= 1`. `z`: pozitif sayı.
- Yukarıdaki formülle alt ve üst sınırı hesapla; sonuçları `[0, 1]` aralığına kırp.
- Dönüş: `{'alt': ..., 'ust': ..., 'merkez': (p̂ + z²/2n) / (1 + z²/n)}`; 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç basit `p̂ ± z·SE` aralığını kullanıyor: 20'de 20 için `[1, 1]` verir ve küçük örneklerde sınırların dışına taşar.

```starter
def wilson_araligi(dogru, toplam, z):
    p = dogru / toplam
    se = (p * (1 - p) / toplam) ** 0.5
    return {'alt': round(p - z * se, 9), 'ust': round(p + z * se, 9), 'merkez': round(p, 9)}
```

```solution
def wilson_araligi(dogru, toplam, z):
    import math
    for x in (dogru, toplam):
        if isinstance(x, bool) or not isinstance(x, int):
            raise ValueError('sayımlar int olmalı')
    if toplam < 1 or not 0 <= dogru <= toplam:
        raise ValueError('0 <= dogru <= toplam ve toplam >= 1 olmalı')
    if isinstance(z, bool) or not isinstance(z, (int, float)) or not math.isfinite(z) or not z > 0:
        raise ValueError('z pozitif sayı olmalı')
    n = toplam
    p = dogru / n
    payda = 1 + z * z / n
    merkez = (p + z * z / (2 * n)) / payda
    yari = z * (p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5 / payda
    return {'alt': round(max(0.0, merkez - yari), 9), 'ust': round(min(1.0, merkez + yari), 9), 'merkez': round(merkez, 9)}
```

```test
need('wilson_araligi')
import math, random

r = wilson_araligi(20, 20, 1.96)
yakin(r['alt'], 0.838865, '20 de 20: alt sınır yaklaşık 0.84', tol=1e-5)
eq(r['ust'], 1.0, '20 de 20: üst sınır 1')
r = wilson_araligi(0, 20, 1.96)
eq(r['alt'], 0.0, '20 de 0: alt sınır 0')
yakin(r['ust'], 0.161135, '20 de 0: üst sınır yaklaşık 0.16', tol=1e-5)
r = wilson_araligi(50, 100, 1.96)
yakin(r['merkez'], 0.5, 'yüzde 50 de merkez değişmez', tol=1e-9)
yakin(r['alt'], 0.403832, '100 de 50: alt', tol=1e-5)
yakin(r['ust'], 0.596168, '100 de 50: üst', tol=1e-5)
dar = wilson_araligi(9000, 10000, 1.96)
genis = wilson_araligi(90, 100, 1.96)
ok(dar['ust'] - dar['alt'] < (genis['ust'] - genis['alt']) / 5, 'yüz kat örnek aralığı yaklaşık on kat daraltır')
ok(wilson_araligi(90, 100, 2.576)['alt'] < genis['alt'], 'daha yüksek güven daha geniş aralık')
rng = random.Random(701)
for _ in range(30):
    n = rng.randint(1, 3000)
    d = rng.randint(0, n)
    z = rng.choice([1.0, 1.645, 1.96, 2.576])
    r = wilson_araligi(d, n, z)
    p = d / n
    ok(0.0 <= r['alt'] <= p + 1e-9 and p - 1e-9 <= r['ust'] <= 1.0, 'aralık [0, 1] içinde ve gözlenen oranı içerir', got=(d, n, r))
    for sinir in (r['alt'], r['ust']):
        if 1e-6 < sinir < 1 - 1e-6:
            yakin(abs(p - sinir) / math.sqrt(sinir * (1 - sinir) / n), z, 'sınırda skor testi tam z verir', tol=1e-4)
eq(wilson_araligi(1, 1, 1.0), {'alt': 0.5, 'ust': 1.0, 'merkez': 0.75}, 'toplam = 1 sınırı')
eq(wilson_araligi(20, 20, 1.96)['alt'], round(20 / (20 + 1.96 ** 2), 9), '9 basamağa yuvarlanır')
for a in ([0, 0, 1.96], [5, 0, 1.96], [-1, 10, 1.96], [11, 10, 1.96], [5.0, 10, 1.96], [True, 10, 1.96], [5, 10, 0], [5, 10, -1], [5, 10, None], [5, 10, True], ["5", 10, 1.96], [5, 10, float('nan')], [5, 10, float('inf')]):
    raises(ValueError, wilson_araligi, *a, msg='bozuk girdi reddedilir')
```

```hint
Üç parça hesapla: `payda = 1 + z²/n`, `merkez = (p + z²/2n) / payda`, `yari = z·√(p(1−p)/n + z²/4n²) / payda`. Sınırlar `merkez ∓ yari`.
```
:::

::: gorev 2 · İki oran arasındaki fark: z-testi
`iki_oran_testi(d1, n1, d2, n2)` işlevini yaz.

- `d1`, `n1`: birinci sistemin doğru ve toplam sayısı; `d2`, `n2`: ikincinin. Hepsi `int`; `0 <= d <= n`, `n >= 1`.
- `fark`: `d1/n1 - d2/n2`. Ortak oran: `(d1 + d2) / (n1 + n2)`.
- `z`: yukarıdaki formül. Ortak oran 0 ya da 1 ise (iki sistem de hep yanlış ya da hep doğru) payda sıfırdır: `z = 0.0`, `p_degeri = 1.0`.
- `p_degeri`: `math.erfc(|z| / √2)`.
- Dönüş: `{'fark': ..., 'z': ..., 'p_degeri': ...}`; 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç yalnız farkın işaretine bakıp "anlamlı" ilan ediyor: her pozitif fark için `p = 0` döndürüyor.

```starter
def iki_oran_testi(d1, n1, d2, n2):
    fark = d1 / n1 - d2 / n2
    return {'fark': round(fark, 9), 'z': round(fark, 9), 'p_degeri': 0.0 if fark != 0 else 1.0}
```

```solution
def iki_oran_testi(d1, n1, d2, n2):
    import math
    for x in (d1, n1, d2, n2):
        if isinstance(x, bool) or not isinstance(x, int):
            raise ValueError('sayımlar int olmalı')
    if n1 < 1 or n2 < 1 or not 0 <= d1 <= n1 or not 0 <= d2 <= n2:
        raise ValueError('0 <= d <= n ve n >= 1 olmalı')
    fark = d1 / n1 - d2 / n2
    ortak = (d1 + d2) / (n1 + n2)
    varyans = ortak * (1 - ortak) * (1 / n1 + 1 / n2)
    if varyans == 0:
        return {'fark': round(fark, 9), 'z': 0.0, 'p_degeri': 1.0}
    z = fark / varyans ** 0.5
    return {'fark': round(fark, 9), 'z': round(z, 9), 'p_degeri': round(math.erfc(abs(z) / math.sqrt(2)), 9)}
```

```test
need('iki_oran_testi')
import math, random
from statistics import NormalDist

r = iki_oran_testi(91, 100, 89, 100)
yakin(r['fark'], 0.02, '2 puanlık fark', tol=1e-9)
ok(r['p_degeri'] > 0.5, '100 soruda 2 puan fark şansla açıklanır', got=r)
r = iki_oran_testi(9100, 10000, 8900, 10000)
ok(r['p_degeri'] < 0.001, '10.000 soruda aynı 2 puan fark anlamlıdır', got=r)
eq(iki_oran_testi(50, 100, 50, 100), {'fark': 0.0, 'z': 0.0, 'p_degeri': 1.0}, 'eşit oranlar')
eq(iki_oran_testi(100, 100, 30, 30), {'fark': 0.0, 'z': 0.0, 'p_degeri': 1.0}, 'ikisi de hep doğru: payda sıfır')
eq(iki_oran_testi(0, 10, 0, 20)['p_degeri'], 1.0, 'ikisi de hep yanlış')
a, b = iki_oran_testi(60, 100, 40, 100), iki_oran_testi(40, 100, 60, 100)
yakin(a['z'], -b['z'], 'sistemlerin yerini değiştirmek z nin işaretini çevirir', tol=1e-9)
yakin(a['p_degeri'], b['p_degeri'], 'iki yönlü p değeri simetriktir', tol=1e-9)
rng = random.Random(702)
for _ in range(30):
    n1, n2 = rng.randint(5, 2000), rng.randint(5, 2000)
    d1, d2 = rng.randint(1, n1 - 1), rng.randint(1, n2 - 1)
    p = (d1 + d2) / (n1 + n2)
    z = (d1 / n1 - d2 / n2) / math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    r = iki_oran_testi(d1, n1, d2, n2)
    yakin(r['z'], z, 'rastgele sayımda z', tol=1e-7)
    yakin(r['p_degeri'], 2 * (1 - NormalDist().cdf(abs(z))), 'p değeri normal dağılımın iki kuyruğu', tol=1e-7)
    ok(0.0 <= r['p_degeri'] <= 1.0, 'p değeri bir olasılıktır')
eq(iki_oran_testi(1, 1, 0, 1)['z'], round(math.sqrt(2), 9), 'n1 = n2 = 1 sınırı ve 9 basamak yuvarlama')
for a in ([0, 0, 5, 10], [5, 10, 0, 0], [5, 0, 5, 10], [5, 10, 5, 0], [11, 10, 5, 10], [5, 10, -1, 10], [5.0, 10, 5, 10], [5, 10, 5, 10.0], [True, 10, 5, 10], [None, 10, 5, 10], ["5", 10, 5, 10]):
    raises(ValueError, iki_oran_testi, *a, msg='bozuk girdi reddedilir')
```

```hint
Ortak oranı iki sistemin toplamından bul. Standart hata `√(p(1−p)(1/n1 + 1/n2))`. `p_degeri = math.erfc(abs(z) / math.sqrt(2))`.
```
:::

::: gorev 3 · Bootstrap güven aralığı
`bootstrap_araligi(veri, tekrar, tohum, guven)` işlevini yaz. Örneklem ortalaması için yüzdelik (`percentile`) bootstrap aralığı kurar.

- `veri`: boş olmayan sayı listesi (`n` öğe). `tekrar`: pozitif `int`. `tohum`: `int`. `guven`: `(0, 1)` aralığında sayı.
- `rng = random.Random(tohum)` ile başla. Her tekrarda `n` kez `veri[rng.randrange(n)]` çek ve ortalamasını al.
- Ortalamaları küçükten büyüğe sırala. `a = (1 - guven) / 2` olmak üzere alt sınır `sirali[int(a * tekrar)]`, üst sınır `sirali[min(tekrar - 1, int((1 - a) * tekrar))]`.
- Dönüş: `{'ortalama': verinin ortalaması, 'alt': ..., 'ust': ...}`; 9 basamağa yuvarlanır.
- Aynı tohum aynı sonucu vermelidir. Bozuk girdi `ValueError`.

KUSURLU başlangıç yerine koymadan örnekliyor (veriyi karıştırıyor): her tekrarda aynı ortalama çıkar ve aralığın genişliği sıfır olur.

```starter
def bootstrap_araligi(veri, tekrar, tohum, guven):
    import random
    rng = random.Random(tohum)
    ort = []
    for _ in range(tekrar):
        kopya = list(veri)
        rng.shuffle(kopya)
        ort.append(sum(kopya) / len(kopya))
    ort.sort()
    m = sum(veri) / len(veri)
    return {'ortalama': round(m, 9), 'alt': round(ort[0], 9), 'ust': round(ort[-1], 9)}
```

```solution
def bootstrap_araligi(veri, tekrar, tohum, guven):
    import math, random
    if not isinstance(veri, list) or not veri or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in veri):
        raise ValueError('veri boş olmayan sayı listesi olmalı')
    if isinstance(tekrar, bool) or not isinstance(tekrar, int) or tekrar < 1:
        raise ValueError('tekrar pozitif int olmalı')
    if isinstance(tohum, bool) or not isinstance(tohum, int):
        raise ValueError('tohum int olmalı')
    if isinstance(guven, bool) or not isinstance(guven, (int, float)) or not 0 < guven < 1:
        raise ValueError('guven (0, 1) aralığında olmalı')
    rng = random.Random(tohum)
    n = len(veri)
    ort = sorted(sum(veri[rng.randrange(n)] for _ in range(n)) / n for _ in range(tekrar))
    a = (1 - guven) / 2
    return {
        'ortalama': round(sum(veri) / n, 9),
        'alt': round(ort[int(a * tekrar)], 9),
        'ust': round(ort[min(tekrar - 1, int((1 - a) * tekrar))], 9),
    }
```

```test
need('bootstrap_araligi')
import random

def _ref(veri, tekrar, tohum, guven):
    g = random.Random(tohum)
    n = len(veri)
    ms = []
    for _ in range(tekrar):
        t = 0.0
        for _ in range(n):
            t += veri[g.randrange(n)]
        ms.append(t / n)
    ms.sort()
    a = (1 - guven) / 2
    return {'ortalama': round(sum(veri) / n, 9), 'alt': round(ms[int(a * tekrar)], 9), 'ust': round(ms[min(tekrar - 1, int((1 - a) * tekrar))], 9)}

veri = [1, 0, 1, 1, 0, 1, 1, 1, 0, 1] * 5
r = bootstrap_araligi(veri, 400, 7, 0.95)
yakin(r['ortalama'], 0.7, 'ortalama verinin kendi ortalaması', tol=1e-9)
ok(r['alt'] < 0.7 < r['ust'], 'aralık ortalamayı içerir ve genişliği sıfır değil', got=r)
ok(0.5 < r['alt'] and r['ust'] < 0.9, '50 örnekte yüzde 70 için makul genişlik', got=r)
eq(bootstrap_araligi(veri, 400, 7, 0.95), r, 'aynı tohum aynı sonucu verir')
r5 = bootstrap_araligi([5, 5, 5], 50, 1, 0.9)
eq(r5, {'ortalama': 5.0, 'alt': 5.0, 'ust': 5.0}, 'sabit veride aralığın genişliği sıfır')
dar = bootstrap_araligi(veri, 400, 3, 0.5)
genis = bootstrap_araligi(veri, 400, 3, 0.99)
ok(genis['ust'] - genis['alt'] >= dar['ust'] - dar['alt'], 'daha yüksek güven daha geniş aralık', got=(dar, genis))
rng = random.Random(703)
for _ in range(15):
    v = [round(rng.gauss(0, 1), 3) for _ in range(rng.randint(1, 25))]
    t, s, g = rng.randint(1, 120), rng.randint(0, 999), rng.choice([0.8, 0.9, 0.95])
    got, exp = bootstrap_araligi(v, t, s, g), _ref(v, t, s, g)
    for k in ('ortalama', 'alt', 'ust'):
        yakin(got[k], exp[k], f'rastgele veride {k} bağımsız referansla aynı', tol=1e-8)
v = [3, 1, 2]
bootstrap_araligi(v, 10, 0, 0.9)
eq(v, [3, 1, 2], 'girdi değişmez (sıralanmaz, karıştırılmaz)')
eq(bootstrap_araligi([1, 3], 1, 0, 0.9)['ortalama'], 2.0, 'tekrar = 1 sınırı')
eq(bootstrap_araligi([0, 0, 1], 10, 0, 0.9)['ortalama'], 0.333333333, '9 basamağa yuvarlanır')
for a in ([None, 10, 0, 0.9], [[], 10, 0, 0.9], [[1, "2"], 10, 0, 0.9], [[True], 10, 0, 0.9], [[float('nan')], 10, 0, 0.9], [[float('inf')], 10, 0, 0.9], [(1, 2), 10, 0, 0.9], [[1], 0, 0, 0.9], [[1], 2.0, 0, 0.9], [[1], True, 0, 0.9], [[1], 10, 1.5, 0.9], [[1], 10, True, 0.9], [[1], 10, 0, 0], [[1], 10, 0, 1], [[1], 10, 0, None], [[1], 10, 0, True], [[1], 10, 0, float('nan')]):
    raises(ValueError, bootstrap_araligi, *a, msg='bozuk girdi reddedilir')
```

```hint
Yerine koyarak örnekleme: `veri[rng.randrange(n)]`'i `n` kez çek. `tekrar` ortalamayı sırala ve iki indeksi formüldeki gibi hesapla.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur; her adım bu derste hesapladığın bir sayıya ya da örneğe dayanır.

1. **Soru (15 sn).** "Fark gerçek mi, şans mı? İstatistik bu soruyu cevaplamak için var."
2. **1,96 (30 sn).** "Bir fark, kendi oynaklığının yaklaşık iki katından büyükse şansla açıklanması zordur. 'Yüzde 95 güven' bunun adıdır."
3. **Yirmi deneme (30 sn).** "Hiçbir şeyin işe yaramadığı yirmi deneme yapın; birinin 'anlamlı' çıkma olasılığı yarıdan fazladır. Makaledeki tek parlak sonucu bu yüzden sorgularız."
4. **Kusursuz skor (25 sn).** "Yirmi soruda yirmi doğru, kusursuz demek değildir; makul tahmin 'en az yüzde 84'tür."
5. **Kapanış (20 sn).** "Anlamlı, önemli demek değildir. Farkın kendisini ve aralığını birlikte isteyin."
:::

::: anlat Sınır
Bu ders bir oran için Wilson aralığını, iki oran için z-testini ve ortalama için yüzdelik bootstrap'i anlatır. Üçü de örneklerin bağımsız olduğunu varsayar. İki sistem **aynı** sorularla sınanıyorsa ölçümler eşlidir ve buradaki z-testi gücü düşük kalır; eşli veride `McNemar` testi ya da eşli bootstrap kullanılır. z-testi normal yaklaşıma dayanır ve küçük örneklerde ya da uç oranlarda güvenilmezdir; orada `Fisher exact test` daha uygundur. Yüzdelik bootstrap küçük örneklerde ve çarpık dağılımlarda aralığı dar verir; `BCa` gibi düzeltilmiş sürümleri vardır. Bootstrap elindeki örneği kitlenin yerine koyar: örnek kitleyi temsil etmiyorsa aralık da etmez. Bir `p-value`'nun 0,05'in altında olması farkın önemli olduğunu göstermez, yalnız şansla açıklanmasının zor olduğunu söyler; etki büyüklüğü ve aralık her zaman birlikte verilmelidir. Çok sayıda karşılaştırma yapıldığında eşik düzeltilmelidir (`Bonferroni`, `Benjamini-Hochberg`) ve bu derste uygulanmaz.

Kaynaklar: [Wilson 1927 - Probable Inference, the Law of Succession, and Statistical Inference](https://doi.org/10.1080/01621459.1927.10502953), [Efron 1979 - Bootstrap Methods: Another Look at the Jackknife](https://doi.org/10.1214/aos/1176344552), [Wasserstein ve Lazar 2016 - The ASA Statement on p-Values](https://doi.org/10.1080/00031305.2016.1154108), [Miller 2024 - Adding Error Bars to Evals](https://arxiv.org/abs/2411.00640).
:::

::: dusun
Bir ekip yeni bir yöntemi 20 farklı veri kümesinde deniyor ve yalnız birinde `p = 0,03` buluyor; makalede o veri kümesini öne çıkarıyor. Hiçbir gerçek etki olmasaydı, 20 karşılaştırmadan en az birinin 0,05'in altına düşme olasılığı kabaca ne olurdu? Bu sonucu nasıl raporlamak dürüst olurdu?
:::

::: ozet
- Güven aralığı tek bir sayının yerine makul değerlerin aralığını verir; Wilson aralığı uç oranlarda ve küçük örneklerde de `[0, 1]` içinde kalır.
- `p-value`, sıfır hipotezi doğruyken gözlenen kadar uç bir sonuç görme olasılığıdır; hipotezin doğru olma olasılığı değildir.
- Aynı fark küçük testte şansla açıklanır, büyük testte anlamlı çıkar; anlamlılık farkın büyüklüğünü söylemez.
- Bootstrap, formülü olmayan ölçüler için yerine koyarak yeniden örnekleyerek aralık kurar.
- Eşli veri, küçük örnek ve çoklu karşılaştırma için bu dersteki testler yetmez; uygun testi seçmek sonucun parçasıdır.
:::
