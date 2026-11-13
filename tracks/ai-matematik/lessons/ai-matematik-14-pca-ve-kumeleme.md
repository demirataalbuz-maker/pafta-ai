---
id: ai-matematik-14
title: "PCA ve Kümeleme · Etiketsiz Veride Yapı Bulmak"
summary: Kovaryans matrisini hesapla, verinin en çok yayıldığı yönü power iteration ile bul ve k-means ile noktaları kümelere ayır; açıklanan varyans ve inertia ile sonucun kalitesini ölç.
---

::: anlat 1. Etiket yokken ne yapılır?
Şimdiye kadarki modeller etiketli veriyle eğitildi. Ama çoğu veri etiketsizdir: milyonlarca log satırı, binlerce `embedding` vektörü, bir ağın iç aktivasyonları. `Unsupervised learning` bu veride yapı arar ve iki temel sorusu vardır:

| Soru | Araç | Görev |
|---|---|---|
| Değişkenler birlikte nasıl değişiyor? | Kovaryans matrisi | 1 |
| Veri en çok hangi yönde yayılıyor? | `PCA` (principal component analysis) | 2 |
| Veri hangi gruplara ayrılıyor? | `k-means` kümeleme | 3 |

PCA yüksek boyutlu veriyi birkaç boyuta indirir: 768 boyutlu embedding'leri iki boyutta çizmek, bir aktivasyon uzayındaki baskın yönü bulmak ya da gürültüyü atmak için kullanılır. Kümeleme benzer örnekleri gruplar: benzer olayları bir araya toplamak, bir veri kümesindeki konuları keşfetmek ya da hiçbir gruba uymayan aykırı örnekleri ayırmak için.
:::

::: anlat 2. Kovaryans, PCA ve k-means
**Kovaryans.** İki değişkenin birlikte nasıl değiştiğini ölçer. `n` örnek ve `d` özellik için önce her özellikten ortalamasını çıkar (`centering`), sonra:

$$C_{jk} = \frac{1}{n - 1}\sum_{i=1}^{n} (x_{ij} - \bar{x}_j)(x_{ik} - \bar{x}_k)$$

Köşegen öğeler her özelliğin varyansıdır; köşegen dışı öğeler pozitifse iki özellik birlikte artar, negatifse biri artarken diğeri azalır. Matris simetriktir.

**PCA.** Verinin en çok yayıldığı yön, kovaryans matrisinin **en büyük özdeğerine** karşılık gelen özvektördür (bkz. `ai-matematik-03`). Bu yöne birinci `principal component` denir; özdeğer, o yöndeki varyanstır. Toplam varyans kovaryans matrisinin izidir (köşegen toplamı), dolayısıyla:

$$\text{açıklanan varyans oranı} = \frac{\lambda_1}{\operatorname{iz}(C)}$$

Bu oran 0,95 ise veri neredeyse tek bir doğru üzerindedir ve tek sayıyla özetlenebilir. Sonraki bileşenler öncekilere dik yönlerdir. PCA, merkezlenmiş veri matrisinin SVD'sine denktir (bkz. `ai-matematik-04`).

Bir uyarı: PCA ölçeğe duyarlıdır. Bir özellik metre, diğeri milimetre cinsindeyse büyük sayılı özellik varyansı ele geçirir; bu yüzden özellikler çoğu zaman önce standartlaştırılır.

**k-means.** Veriyi `k` kümeye ayırır; her küme bir merkezle (`centroid`) temsil edilir. `Lloyd` algoritması iki adımı tekrarlar:

1. **Atama:** her noktayı en yakın merkeze ata.
2. **Güncelleme:** her merkezi, kendisine atanan noktaların ortalamasına taşı.

Atamalar değişmeyince durur. Küçültülen ölçü `inertia`'dır: her noktanın kendi merkezine uzaklığının karelerinin toplamı. Her iki adım da inertia'yı artırmaz; algoritma her zaman bir yere yakınsar, ama bu **yerel** bir en iyidir ve başlangıç merkezlerine bağlıdır.
:::

::: tahmin Hangi yön daha çok bilgi taşıyor?
İki özellikli dört noktanın her eksendeki varyansı ne yazdırılır?

```python
veri = [[1, 10], [2, 10], [3, 11], [4, 11]]

for j in range(2):
    sutun = [satir[j] for satir in veri]
    ort = sum(sutun) / len(sutun)
    print(round(sum((v - ort) ** 2 for v in sutun) / (len(sutun) - 1), 4))
```

???

```cikti
1.6667
0.3333
```
Birinci özellik 1 ile 4 arasında yayılıyor: varyansı 1,67. İkincisi yalnız 10 ile 11 arasında: varyansı 0,33. Toplam varyansın yaklaşık %83'ü birinci eksendedir. PCA bundan da iyisini yapar: eksenlere değil, verinin gerçekte uzandığı **eğik** yöne bakar; bu veride o yön varyansın daha da büyük bir kısmını açıklar, çünkü iki özellik birlikte artıyor.
:::

::: gorev 1 · Kovaryans matrisi
`kovaryans(veri)` işlevini yaz.

- `veri`: en az iki satırlı liste; her satır aynı uzunlukta (`d >= 1`) sayı listesi.
- Dönüş: `{'ortalama': [d sayı], 'kovaryans': d × d matris}`; payda `n - 1`; 9 basamağa yuvarlanır. Çarpımın **iki** çarpanı da ortalamadan çıkarılır; yalnız biri merkezlenirse sonuç kâğıt üstünde aynıdır ama büyük sayılarda `float` yuvarlaması yüzünden bozulur.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç ortalamayı çıkarmıyor: ham çarpımların ortalamasını döndürüyor. Veri sıfır etrafında değilse sonuç yayılımı değil, konumu ölçer.

```starter
def kovaryans(veri):
    n, d = len(veri), len(veri[0])
    ort = [sum(s[j] for s in veri) / n for j in range(d)]
    C = [[round(sum(s[j] * s[k] for s in veri) / (n - 1), 9) for k in range(d)] for j in range(d)]
    return {'ortalama': [round(m, 9) for m in ort], 'kovaryans': C}
```

```solution
def kovaryans(veri):
    if not isinstance(veri, list) or len(veri) < 2 or not isinstance(veri[0], list) or not veri[0]:
        raise ValueError('veri en az iki satırlı, boş olmayan sütunlu matris olmalı')
    d = len(veri[0])
    for s in veri:
        if not isinstance(s, list) or len(s) != d or any(isinstance(a, bool) or not isinstance(a, (int, float)) for a in s):
            raise ValueError('satırlar aynı uzunlukta sayı listesi olmalı')
    n = len(veri)
    ort = [sum(s[j] for s in veri) / n for j in range(d)]
    C = [[round(sum((s[j] - ort[j]) * (s[k] - ort[k]) for s in veri) / (n - 1), 9) for k in range(d)] for j in range(d)]
    return {'ortalama': [round(m, 9) for m in ort], 'kovaryans': C}
```

```test
need('kovaryans')
import random, statistics

r = kovaryans([[1, 10], [2, 10], [3, 11], [4, 11]])
eq(r['ortalama'], [2.5, 10.5], 'ortalama')
yakin(r['kovaryans'][0][0], 5 / 3, 'birinci özelliğin varyansı', tol=1e-8)
yakin(r['kovaryans'][1][1], 1 / 3, 'ikinci özelliğin varyansı', tol=1e-8)
yakin(r['kovaryans'][0][1], 2 / 3, 'birlikte artıyorlar: pozitif kovaryans', tol=1e-8)
r = kovaryans([[100, 5], [101, 5], [102, 5]])
eq(r['kovaryans'], [[1.0, 0.0], [0.0, 0.0]], 'büyük ortalama varyansı şişirmez; sabit özelliğin varyansı sıfır')
eq(kovaryans([[1, 3], [2, 2], [3, 1]])['kovaryans'][0][1], -1.0, 'biri artarken diğeri azalıyor: negatif kovaryans')
eq(kovaryans([[2], [4]]), {'ortalama': [3.0], 'kovaryans': [[2.0]]}, 'tek özellik')
rng = random.Random(1401)
for _ in range(20):
    n, d = rng.randint(2, 15), rng.randint(1, 4)
    v = [[round(rng.uniform(-5, 5), 2) for _ in range(d)] for _ in range(n)]
    r = kovaryans(v)
    for j in range(d):
        sj = [s[j] for s in v]
        yakin(r['kovaryans'][j][j], statistics.variance(sj), 'köşegen: varyans', tol=1e-7)
        for k in range(d):
            sk = [s[k] for s in v]
            yakin(r['kovaryans'][j][k], r['kovaryans'][k][j], 'simetrik', tol=1e-9)
            if j != k:
                yakin(r['kovaryans'][j][k], statistics.covariance(sj, sk), 'köşegen dışı: kovaryans', tol=1e-7)
r = kovaryans([[1, 10000000001], [2, 10000000002], [4, 10000000004]])
yakin(r['kovaryans'][0][1], 7 / 3, 'büyük ortak ofset kovaryansı değiştirmez: iki çarpan da merkezlenmeli', tol=1e-6)
yakin(r['kovaryans'][1][0], 7 / 3, 'büyük ofsette de simetrik', tol=1e-6)
yakin(r['kovaryans'][1][1], 7 / 3, 'büyük ofsetli sütunun varyansı', tol=1e-6)
v = [[1, 2], [3, 4]]
kovaryans(v)
eq(v, [[1, 2], [3, 4]], 'girdi değişmez')
for kotu in (None, [], [[1, 2]], [[1, 2], [3]], [[], []], [[], [1]], [[1, "2"], [3, 4]], [[True], [1]], [(1, 2), (3, 4)], [[1, 2], (3, 4)], [1, 2], [5, [1, 2]]):
    raises(ValueError, kovaryans, kotu, msg='bozuk girdi reddedilir')
```

```hint
Önce her sütunun ortalamasını bul. `C[j][k] = Σ (x_ij − ort_j)(x_ik − ort_k) / (n − 1)`.
```
:::

::: gorev 2 · Birinci principal component
`ilk_bilesen(veri, adim)` işlevini yaz.

- `veri`: Görev 1'deki gibi. `adim`: pozitif `int`.
- Kovaryans matrisini hesapla (`n - 1` payda). İzi sıfırsa (bütün noktalar aynı) `ValueError`.
- Kovaryans matrisinde `adim` kez `power iteration` uygula: başlangıç bütün bileşenleri 1 olan birim vektördür; her adımda `w = C v`, normu sıfırsa `ValueError`, `v = w / ‖w‖`.
- `ozdeger = v · (C v)`. İşaret kuralı: `v`'nin mutlak değeri `1e-12`'den büyük ilk bileşeni negatifse `v`'yi `-1` ile çarp.
- `aciklanan_oran = ozdeger / iz(C)`.
- `izdusum`: her merkezlenmiş noktanın `v` üzerindeki koordinatı (`(x - ortalama) · v`).
- Dönüş: `{'yon': [...], 'ozdeger': ..., 'aciklanan_oran': ..., 'izdusum': [...]}`; 6 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç varyansı en büyük **ekseni** döndürüyor. Veri eğik bir doğru boyunca uzanıyorsa hiçbir eksen o yönü vermez.

```starter
def ilk_bilesen(veri, adim):
    n, d = len(veri), len(veri[0])
    ort = [sum(s[j] for s in veri) / n for j in range(d)]
    var = [sum((s[j] - ort[j]) ** 2 for s in veri) / (n - 1) for j in range(d)]
    j = var.index(max(var))
    yon = [1.0 if k == j else 0.0 for k in range(d)]
    return {'yon': yon, 'ozdeger': round(var[j], 6), 'aciklanan_oran': round(var[j] / sum(var), 6), 'izdusum': [round(s[j] - ort[j], 6) for s in veri]}
```

```solution
def ilk_bilesen(veri, adim):
    if not isinstance(veri, list) or len(veri) < 2 or not isinstance(veri[0], list) or not veri[0]:
        raise ValueError('veri en az iki satırlı, boş olmayan sütunlu matris olmalı')
    d = len(veri[0])
    for s in veri:
        if not isinstance(s, list) or len(s) != d or any(isinstance(a, bool) or not isinstance(a, (int, float)) for a in s):
            raise ValueError('satırlar aynı uzunlukta sayı listesi olmalı')
    if isinstance(adim, bool) or not isinstance(adim, int) or adim < 1:
        raise ValueError('adim pozitif int olmalı')
    n = len(veri)
    ort = [sum(s[j] for s in veri) / n for j in range(d)]
    X = [[s[j] - ort[j] for j in range(d)] for s in veri]
    C = [[sum(x[j] * x[k] for x in X) / (n - 1) for k in range(d)] for j in range(d)]
    iz = sum(C[j][j] for j in range(d))
    if iz == 0:
        raise ValueError('veride yayılım yok')

    def carp(v):
        return [sum(C[j][k] * v[k] for k in range(d)) for j in range(d)]

    v = [1.0 / d ** 0.5] * d
    for _ in range(adim):
        w = carp(v)
        uzunluk = sum(a * a for a in w) ** 0.5
        if uzunluk == 0:
            raise ValueError('vektör sıfıra indi')
        v = [a / uzunluk for a in w]
    ozdeger = sum(a * b for a, b in zip(v, carp(v)))
    ilk = next((a for a in v if abs(a) > 1e-12), 0.0)
    if ilk < 0:
        v = [-a for a in v]
    return {
        'yon': [round(a, 6) for a in v],
        'ozdeger': round(ozdeger, 6),
        'aciklanan_oran': round(ozdeger / iz, 6),
        'izdusum': [round(sum(a * b for a, b in zip(x, v)), 6) for x in X],
    }
```

```test
need('ilk_bilesen')
import math, random

r = ilk_bilesen([[0, 0], [1, 1], [2, 2], [3, 3]], 50)
eq(r['yon'], [0.707107, 0.707107], 'köşegen boyunca uzanan veri: yön [1, 1] / kök 2')
eq(r['aciklanan_oran'], 1.0, 'bütün varyans tek yönde')
yakin(r['izdusum'][3] - r['izdusum'][0], 3 * math.sqrt(2), 'izdüşüm doğru üzerindeki uzaklığı korur', tol=1e-5)
r = ilk_bilesen([[0, 5], [10, 5], [20, 5]], 20)
eq(r['yon'], [1.0, 0.0], 'yalnız birinci özellik değişiyor')
eq(r['ozdeger'], 100.0, 'özdeğer o yöndeki varyans')
r = ilk_bilesen([[0, 0], [1, -2], [2, -4]], 50)
eq(r['yon'], [0.447214, -0.894427], 'işaret kuralı: ilk sıfırdan farklı bileşen pozitif')
rng = random.Random(1402)
for _ in range(15):
    t = rng.uniform(0.2, 1.3)
    c, s = math.cos(t), math.sin(t)
    v = []
    for _ in range(rng.randint(8, 30)):
        a, b = rng.gauss(0, 3), rng.gauss(0, 0.3)
        v.append([a * c - b * s + 4, a * s + b * c - 2])
    r = ilk_bilesen(v, 300)
    n = len(v)
    ort = [sum(p[j] for p in v) / n for j in range(2)]
    X = [[p[0] - ort[0], p[1] - ort[1]] for p in v]
    C = [[sum(x[j] * x[k] for x in X) / (n - 1) for k in range(2)] for j in range(2)]
    iz, det = C[0][0] + C[1][1], C[0][0] * C[1][1] - C[0][1] ** 2
    l1 = (iz + math.sqrt(iz * iz - 4 * det)) / 2
    yakin(r['ozdeger'], l1, 'özdeğer 2x2 kapalı formülle aynı', tol=1e-4)
    yakin(r['aciklanan_oran'], l1 / iz, 'açıklanan oran', tol=1e-5)
    yakin(math.hypot(*r['yon']), 1.0, 'yön birim uzunlukta', tol=1e-5)
    ok(abs(r['yon'][0] * c + r['yon'][1] * s) > 0.9, 'yön verinin üretildiği eksene yakın', got=(r['yon'], (c, s)))
    yakin(sum(p * p for p in r['izdusum']) / (n - 1), l1, 'izdüşümlerin varyansı özdeğerdir', tol=1e-3)
    ok(r['aciklanan_oran'] > 0.9, 'uzun eksen varyansın çoğunu açıklar')
raises(ValueError, ilk_bilesen, [[2, 3], [2, 3], [2, 3]], 10, msg='bütün noktalar aynıysa yön tanımsız')
raises(ValueError, ilk_bilesen, [[1, -1], [-1, 1]], 5, msg='başlangıç vektörü kovaryansın sıfır uzayındaysa reddedilir')
eq(ilk_bilesen([[0], [1], [2]], 1), {'yon': [1.0], 'ozdeger': 1.0, 'aciklanan_oran': 1.0, 'izdusum': [-1.0, 0.0, 1.0]}, 'tek boyut, tek adım, birim iz')
v = [[1, 2], [3, 5]]
ilk_bilesen(v, 5)
eq(v, [[1, 2], [3, 5]], 'girdi değişmez')
for a, k in [(None, 5), ([], 5), ([[1, 2]], 5), ([[1, 2], [3]], 5), ([[], [1]], 5), ([[1, "2"], [3, 4]], 5), ([[True], [1]], 5), ([[1, 2], [3, 4]], 0), ([[1, 2], [3, 4]], 1.5), ([[1, 2], [3, 4]], True), ([[1, 2], [3, 4]], False), ([(1, 2), (3, 4)], 5), ([(1, 2), [3, 4]], 5), ([[1, 2], (3, 4)], 5)]:
    raises(ValueError, ilk_bilesen, a, k, msg='bozuk girdi reddedilir')
```

```hint
Üç aşama: veriyi merkezle ve kovaryansı kur; kovaryansta power iteration çalıştır; son `v` ile `ozdeger = v·(Cv)` ve izdüşümleri hesapla.
```
:::

::: gorev 3 · k-means (Lloyd algoritması)
`kmeans(noktalar, merkezler, adim)` işlevini yaz.

- `noktalar`: boş olmayan liste; her nokta aynı uzunlukta sayı listesi. `merkezler`: boş olmayan liste; her merkez noktalarla aynı uzunlukta. `adim`: negatif olmayan `int` (en çok tur sayısı).
- Her turda:
  1. **Atama:** her noktayı kare Öklid uzaklığı en küçük olan merkeze ata; eşitlikte küçük indeksli merkez.
  2. **Güncelleme:** her merkezi kendisine atanan noktaların ortalamasına taşı; hiç nokta atanmamış merkez yerinde kalır.
  3. Atamalar bir önceki turla aynıysa dur.
- Sonda atamalar **son** merkezlere göre bir kez daha hesaplanır.
- Dönüş: `{'merkezler': [...], 'etiketler': [...], 'inertia': ...}`; merkezler ve inertia 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç atamayı bir kez yapıp merkezleri hiç güncellemiyor: sonuç yalnız başlangıç merkezlerinin çizdiği sınırdır.

```starter
def kmeans(noktalar, merkezler, adim):
    def uz(a, b):
        return sum((x - y) ** 2 for x, y in zip(a, b))
    etiket = [min(range(len(merkezler)), key=lambda j: uz(p, merkezler[j])) for p in noktalar]
    inertia = sum(uz(p, merkezler[e]) for p, e in zip(noktalar, etiket))
    return {'merkezler': [[round(float(a), 9) for a in m] for m in merkezler], 'etiketler': etiket, 'inertia': round(inertia, 9)}
```

```solution
def kmeans(noktalar, merkezler, adim):
    def matris(M):
        if not isinstance(M, list) or not M or not isinstance(M[0], list) or not M[0]:
            return False
        for s in M:
            if not isinstance(s, list) or len(s) != len(M[0]) or any(isinstance(a, bool) or not isinstance(a, (int, float)) for a in s):
                return False
        return True
    if not matris(noktalar) or not matris(merkezler) or len(noktalar[0]) != len(merkezler[0]):
        raise ValueError('noktalar ve merkezler aynı boyutta sayı matrisleri olmalı')
    if isinstance(adim, bool) or not isinstance(adim, int) or adim < 0:
        raise ValueError('adim negatif olmayan int olmalı')

    def uz(a, b):
        return sum((x - y) ** 2 for x, y in zip(a, b))

    def ata(M):
        return [min(range(len(M)), key=lambda j: (uz(p, M[j]), j)) for p in noktalar]

    M = [[float(a) for a in m] for m in merkezler]
    d = len(M[0])
    onceki = None
    for _ in range(adim):
        etiket = ata(M)
        if etiket == onceki:
            break
        for j in range(len(M)):
            uyeler = [p for p, e in zip(noktalar, etiket) if e == j]
            if uyeler:
                M[j] = [sum(p[k] for p in uyeler) / len(uyeler) for k in range(d)]
        onceki = etiket
    etiket = ata(M)
    inertia = sum(uz(p, M[e]) for p, e in zip(noktalar, etiket))
    return {'merkezler': [[round(a, 9) for a in m] for m in M], 'etiketler': etiket, 'inertia': round(inertia, 9)}
```

```test
need('kmeans')
import random

P = [[0, 0], [0, 1], [10, 10], [10, 11]]
r = kmeans(P, [[0, 0], [1, 1]], 10)
eq(r['etiketler'], [0, 0, 1, 1], 'iki belirgin küme')
eq(r['merkezler'], [[0.0, 0.5], [10.0, 10.5]], 'merkezler küme ortalamalarına taşınır')
eq(r['inertia'], 1.0, 'inertia: dört nokta, her biri merkezine 0.5 uzakta')
r0 = kmeans(P, [[0, 0], [1, 1]], 0)
eq(r0['merkezler'], [[0.0, 0.0], [1.0, 1.0]], 'sıfır tur: merkezler değişmez')
eq(r0['etiketler'], [0, 0, 1, 1], 'sıfır tur: yalnız atama ([0, 1] iki merkeze eşit uzak: küçük indeks)')
eq(r0['inertia'], 344.0, 'sıfır tur: inertia başlangıç merkezlerine göre')
ok(r['inertia'] < r0['inertia'], 'güncelleme inertia yı düşürür', got=(r0['inertia'], r['inertia']))
r = kmeans([[0], [2]], [[1], [1]], 5)
eq(r['etiketler'], [0, 0], 'eşit uzaklıkta küçük indeksli merkez')
eq(r['merkezler'], [[1.0], [1.0]], 'boş kalan merkez yerinde kalır')
r = kmeans([[1], [2], [3]], [[2]], 5)
eq(r, {'merkezler': [[2.0]], 'etiketler': [0, 0, 0], 'inertia': 2.0}, 'tek küme: merkez ortalama, inertia varyansın payı')
a = kmeans([[0], [1], [10], [11]], [[0], [1]], 20)
b = kmeans([[0], [1], [10], [11]], [[0], [10]], 20)
eq(a['inertia'], b['inertia'], 'bu veride kötü başlangıç da doğru kümeleri bulur')
kotu = kmeans([[0], [1], [10], [11], [20], [21]], [[0], [1], [10]], 20)
iyi = kmeans([[0], [1], [10], [11], [20], [21]], [[0], [10], [20]], 20)
eq((kotu['inertia'], iyi['inertia']), (101.0, 1.5), 'aynı veri, iki başlangıç, iki farklı sonuç')
ok(kotu['inertia'] > iyi['inertia'], 'başlangıç sonucu değiştirebilir: yerel en iyi', got=(kotu['inertia'], iyi['inertia']))
def _uz(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b))
rng = random.Random(1403)
for _ in range(15):
    d, n, k = rng.randint(1, 3), rng.randint(1, 20), rng.randint(1, 4)
    P = [[rng.randint(-6, 6) for _ in range(d)] for _ in range(n)]
    M0 = [[rng.randint(-6, 6) for _ in range(d)] for _ in range(k)]
    r = kmeans(P, M0, 50)
    eq(len(r['etiketler']), n, 'her noktaya bir etiket')
    for p, e in zip(P, r['etiketler']):
        ok(all(_uz(p, r['merkezler'][e]) <= _uz(p, m) + 1e-7 for m in r['merkezler']), 'her nokta en yakın merkezine atanmış')
    for j, m in enumerate(r['merkezler']):
        uy = [p for p, e in zip(P, r['etiketler']) if e == j]
        if uy:
            for c in range(d):
                yakin(m[c], sum(p[c] for p in uy) / len(uy), 'yakınsamada merkez üyelerinin ortalamasıdır', tol=1e-7)
    yakin(r['inertia'], sum(_uz(p, r['merkezler'][e]) for p, e in zip(P, r['etiketler'])), 'inertia tanımıyla aynı', tol=1e-6)
    ok(r['inertia'] <= kmeans(P, M0, 0)['inertia'] + 1e-7, 'inertia başlangıca göre artmaz')
P, M = [[1, 2], [3, 4]], [[0, 0]]
kmeans(P, M, 3)
eq((P, M), ([[1, 2], [3, 4]], [[0, 0]]), 'girdiler değişmez')
iyiP, iyiM = [[1, 2]], [[0, 0]]
for a in ([None, iyiM, 1], [iyiP, None, 1], [[], iyiM, 1], [iyiP, [], 1], [[[], [1, 2]], iyiM, 1], [iyiP, [[0]], 1], [[[1, 2], [3]], iyiM, 1], [[[1, "2"]], iyiM, 1], [[[True, 1]], iyiM, 1], [iyiP, iyiM, -1], [iyiP, iyiM, 1.0], [iyiP, iyiM, True], [[(1, 2)], iyiM, 1], [[[1, 2], (3, 4)], iyiM, 1]):
    raises(ValueError, kmeans, *a, msg='bozuk girdi reddedilir')
```

```hint
Atama için `min(range(k), key=lambda j: (uzaklık, j))` eşitlikte küçük indeksi verir. Güncellemede boş kümeyi atla. Atamalar değişmezse döngüden çık; sonda atamayı bir kez daha yap.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur; her adım bu derste hesapladığın bir sayıya ya da örneğe dayanır.

1. **Çerçeve (15 sn).** "Etiket yoksa ne yaparsınız? Verinin kendi şekline bakarsınız."
2. **PCA (30 sn).** "Binlerce boyutlu veriyi en çok yayıldığı iki yönde çizebiliriz. Ama ekrandaki iki grup, toplam bilginin yalnız yüzde 12'siyse o resme güvenmeyin."
3. **Kümeleme (30 sn).** "k-means noktaları en yakın merkeze atar, merkezleri ortalamaya taşır, tekrarlar. Basit ve hızlı."
4. **Tuzak (25 sn).** "Aynı veri, iki farklı başlangıç, iki farklı sonuç. Küme sayısını da, kümelerin anlamını da algoritma değil siz seçersiniz."
5. **Kapanış (20 sn).** "Etiketsiz veride bulunan yapı bir hipotezdir; kanıtı başka yerden gelir."
:::

::: anlat Sınır
Bu ders kovaryansı, birinci principal component'i ve k-means'i anlatır. PCA yalnız **doğrusal** yapıyı bulur: veri bir çember ya da eğri üzerinde diziliyse hiçbir doğrusal yön onu özetlemez. En çok varyans taşıyan yön en önemli yön olmak zorunda değildir; sınıfları ayıran bilgi küçük varyanslı bir yönde olabilir. PCA ölçeğe duyarlıdır ve aykırı değerler baskın yönü tek başına belirleyebilir. Buradaki power iteration yalnız birinci bileşeni verir ve ilk iki özdeğer yakınsa yavaş yakınsar; gerçek kitaplıklar SVD kullanır. k-means küme sayısını `k` senden ister; doğru `k` bilinmez ve inertia `k` arttıkça her zaman düştüğü için tek başına seçim ölçütü olamaz. Yöntem küresel ve benzer büyüklükte kümeler varsayar; uzun, iç içe ya da farklı yoğunlukta kümelerde yanlış böler. Sonuç başlangıç merkezlerine bağlıdır; pratikte `k-means++` ile başlatılır ve birkaç kez tekrarlanır. Yüksek boyutta noktalar arası uzaklıklar birbirine yaklaşır ve Öklid uzaklığına dayalı kümeleme anlamını yitirebilir. Kümelerin "anlamlı" olması algoritmanın değil, yorumlayanın iddiasıdır ve ayrıca doğrulanmalıdır.

Kaynaklar: [Jolliffe ve Cadima 2016 - Principal component analysis: a review and recent developments](https://doi.org/10.1098/rsta.2015.0202), [Lloyd 1982 - Least squares quantization in PCM](https://doi.org/10.1109/TIT.1982.1056489), [Arthur ve Vassilvitskii 2007 - k-means++: The Advantages of Careful Seeding](https://dl.acm.org/doi/10.5555/1283383.1283494), [Hastie, Tibshirani ve Friedman 2009 - The Elements of Statistical Learning, Bölüm 14](https://hastie.su.domains/ElemStatLearn/).
:::

::: dusun
Bir ekip 768 boyutlu embedding'leri PCA ile iki boyuta indirip çiziyor ve "iki grup net biçimde ayrılıyor" diyor. İlk iki bileşen toplam varyansın %12'sini açıklıyorsa bu çizime ne kadar güvenirsin? Kalan %88'de ne olabilir? İddiayı sınamak için çizim dışında hangi ölçümü isterdin?
:::

::: ozet
- Kovaryans matrisi merkezlenmiş verinin `n − 1`'e bölünmüş çarpımlarıdır; köşegeni varyanslar, köşegen dışı birlikte değişimdir.
- Birinci principal component, kovaryans matrisinin en büyük özdeğerli özvektörüdür; açıklanan oran `λ1 / iz(C)`'dir.
- PCA doğrusal ve ölçeğe duyarlıdır; en çok varyans en çok bilgi demek değildir.
- k-means atama ve güncelleme adımlarını tekrarlar; inertia hiç artmaz ama varılan nokta yerel bir en iyidir.
- Küme sayısı, başlangıç ve kümelerin anlamı algoritmadan gelmez; ayrıca seçilir ve doğrulanır.
:::
