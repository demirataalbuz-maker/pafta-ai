---
id: ai-matematik-03
title: "Özdeğer ve Özvektör · Bir Matrisin Değiştirmediği Yönler"
summary: 2x2 matrisin özdeğerlerini kapalı formülle, baskın özvektörü power iteration ile bul; Rayleigh quotient ve artık normuyla bir özçift adayını sına.
---

::: anlat 1. Değişmeyen yön
Bir matris çoğu vektörü hem döndürür hem uzatır. Ama bazı özel vektörlerin yönü değişmez; yalnız uzar ya da kısalırlar:

$$A v = \lambda v$$

Bu `v` bir **özvektör** (`eigenvector`), `λ` ise ona karşılık gelen **özdeğer** (`eigenvalue`), yani uzama katsayısıdır.

Bu neden önemli? Çünkü bir matrisi defalarca uygularsan (bir ağın katmanları, bir optimizasyonun adımları, bir Markov zincirinin geçişleri) davranışı özdeğerleri belirler:

| Durum | Ne olur |
|---|---|
| En büyük $\lvert\lambda\rvert > 1$ | Tekrarlanan çarpım büyür (patlar) |
| En büyük $\lvert\lambda\rvert < 1$ | Tekrarlanan çarpım küçülür (söner) |
| Kovaryans matrisinin en büyük özdeğeri | Verinin en çok yayıldığı yön (`PCA`, bkz. `ai-matematik-14`) |
| Kayıp yüzeyinin `Hessian` özdeğerleri | En dik ve en yassı yönler; öğrenme oranının üst sınırı |

| Soru | Araç | Görev |
|---|---|---|
| 2×2 bir matrisin özdeğerleri ne? | Karakteristik denklem | 1 |
| Büyük bir matrisin baskın yönü ne? | `Power iteration` | 2 |
| Elimdeki aday gerçekten bir özçift mi? | `Rayleigh quotient` ve artık | 3 |
:::

::: anlat 2. Kapalı formül ve power iteration
**2×2 matris için** özdeğerler bir ikinci derece denklemin kökleridir. $A = \begin{pmatrix} a & b \\ c & d \end{pmatrix}$ için iz $T = a + d$ ve determinant $D = ad - bc$ olmak üzere:

$$\lambda = \frac{T \pm \sqrt{T^2 - 4D}}{2}$$

Karekökün içi negatifse özdeğerler karmaşık sayıdır: matris hiçbir gerçek yönü yerinde bırakmaz (saf bir döndürme gibi). Simetrik matrislerde bu olmaz; özdeğerleri her zaman gerçektir.

**Büyük matrisler için** kapalı formül yoktur. En basit yöntem `power iteration`'dır: rastgele bir vektörle başla, matrisle çarp, uzunluğunu 1'e getir, tekrarla. Her çarpımda vektörün baskın özvektör yönündeki bileşeni diğerlerinden daha çok büyür; sonunda vektör o yöne döner.

Yakınsama hızı ilk iki özdeğerin oranına bağlıdır: hata her adımda yaklaşık $\lvert\lambda_2 / \lambda_1\rvert$ ile çarpılır. İki özdeğer birbirine yakınsa yöntem çok yavaşlar; eşit büyüklükteyseler hiç yakınsamaz.

**Rayleigh quotient**, bir vektör verildiğinde ona en uygun özdeğer tahminidir:

$$\rho(v) = \frac{v^\top A v}{v^\top v}$$

`v` gerçek bir özvektörse $\rho(v)$ tam olarak özdeğerdir. Adayın ne kadar iyi olduğunu **artık** söyler: $\lVert Av - \rho v \rVert / \lVert v \rVert$. Sıfırsa gerçek bir özçifttir.
:::

::: tahmin Bu bir özvektör mü?
Bir matris iki farklı vektöre uygulanıyor. Ne yazdırılır?

```python
A = [[2, 1], [1, 2]]

def uygula(v):
    return [A[0][0] * v[0] + A[0][1] * v[1], A[1][0] * v[0] + A[1][1] * v[1]]

print(uygula([1, 1]))
print(uygula([1, 0]))
```

???

```cikti
[3, 3]
[2, 1]
```
`[1, 1]` vektörü `[3, 3]` oldu: yönü aynı, uzunluğu 3 katı. Bu bir özvektördür ve özdeğeri 3'tür. `[1, 0]` vektörü `[2, 1]` oldu: yönü değişti, özvektör değildir. Bu matrisin diğer özvektörü `[1, -1]`'dir ve özdeğeri 1'dir; iki özvektör birbirine diktir, çünkü matris simetriktir.
:::

::: gorev 1 · 2×2 matrisin özdeğerleri
`ozdegerler_2x2(A)` işlevini yaz.

- `A`: `2 × 2` sayı matrisi (iki öğeli iki liste).
- İz ve determinantı hesapla; diskriminant $T^2 - 4D$ negatifse `ValueError` (özdeğerler gerçek değil).
- Dönüş: `[büyük, küçük]`; 9 basamağa yuvarlanmış iki `float`. Çift kök varsa iki öğe eşittir.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç köşegendeki öğeleri özdeğer sanıyor. Bu yalnız köşegen ve üçgen matrislerde doğrudur.

```starter
def ozdegerler_2x2(A):
    return sorted([float(A[0][0]), float(A[1][1])], reverse=True)
```

```solution
def ozdegerler_2x2(A):
    import math
    if not isinstance(A, list) or len(A) != 2:
        raise ValueError('A 2x2 matris olmalı')
    for s in A:
        if not isinstance(s, list) or len(s) != 2 or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in s):
            raise ValueError('A 2x2 sonlu sayı matrisi olmalı')
    iz = A[0][0] + A[1][1]
    det = A[0][0] * A[1][1] - A[0][1] * A[1][0]
    disk = iz * iz - 4 * det
    if disk < 0:
        raise ValueError('özdeğerler gerçek değil')
    kok = disk ** 0.5
    return [round((iz + kok) / 2, 9), round((iz - kok) / 2, 9)]
```

```test
need('ozdegerler_2x2')
import math, random

eq(ozdegerler_2x2([[2, 1], [1, 2]]), [3.0, 1.0], 'simetrik matris')
eq(ozdegerler_2x2([[4, 0], [0, -1]]), [4.0, -1.0], 'köşegen matris')
eq(ozdegerler_2x2([[1, 5], [0, 3]]), [3.0, 1.0], 'üçgen matris: köşegen, büyükten küçüğe')
eq(ozdegerler_2x2([[2, 0], [0, 2]]), [2.0, 2.0], 'çift kök')
eq(ozdegerler_2x2([[0, 1], [1, 0]]), [1.0, -1.0], 'köşegeni sıfır ama özdeğerleri değil')
eq(ozdegerler_2x2([[1, 2], [2, 4]]), [5.0, 0.0], 'rank 1 matrisin bir özdeğeri sıfır')
eq(ozdegerler_2x2([[0, 1], [2, 0]]), [1.414213562, -1.414213562], 'irrasyonel özdeğerlerde 9 basamak')
raises(ValueError, ozdegerler_2x2, [[0, -1], [1, 0]], msg='90 derece döndürmenin gerçek özdeğeri yok')
rng = random.Random(301)
for _ in range(30):
    a, b, d = (round(rng.uniform(-5, 5), 2) for _ in range(3))
    A = [[a, b], [b, d]]
    l1, l2 = ozdegerler_2x2(A)
    ok(l1 >= l2, 'büyükten küçüğe')
    yakin(l1 + l2, a + d, 'özdeğerlerin toplamı izdir', tol=1e-7)
    yakin(l1 * l2, a * d - b * b, 'özdeğerlerin çarpımı determinanttır', tol=1e-6)
    for l in (l1, l2):
        yakin((a - l) * (d - l) - b * b, 0.0, 'karakteristik denklemi sağlar', tol=1e-6)
A = [[1, 2], [3, 4]]
ozdegerler_2x2(A)
eq(A, [[1, 2], [3, 4]], 'girdi değişmez')
for kotu in (None, [], [[1, 2]], [[1, 2], [3]], [[1, 2, 3], [4, 5, 6]], [[1, "2"], [3, 4]], [[True, 0], [0, 1]], [(1, 2), (3, 4)], [[1, 2], [3, 4], [5, 6]], [[float('nan'), 0], [0, 1]], [[float('inf'), 0], [0, 1]]):
    raises(ValueError, ozdegerler_2x2, kotu, msg='bozuk girdi reddedilir')
```

```hint
`iz = a + d`, `det = a*d - b*c`, `disk = iz*iz - 4*det`. Kökler `(iz ± √disk) / 2`.
```
:::

::: gorev 2 · Power iteration
`guc_yontemi(A, adim)` işlevini yaz.

- `A`: boş olmayan **kare** sayı matrisi. `adim`: pozitif `int`.
- Başlangıç vektörü bütün bileşenleri 1 olan vektörün birim uzunluğa getirilmiş hâlidir.
- Her adımda: `w = A v`; `w`'nin `L2` normu sıfırsa `ValueError`; `v = w / ‖w‖`.
- Son `v` için özdeğer tahmini Rayleigh quotient'tir: `v · (A v)` (çünkü `‖v‖ = 1`).
- İşaret belirsizliğini gider: mutlak değeri `1e-12`'den büyük olan **ilk** bileşen negatifse vektörü `-1` ile çarp.
- Dönüş: `{'ozdeger': ..., 'ozvektor': [...]}`; sayılar 6 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç her adımda vektörü normalleştirmiyor ve özdeğer diye vektörün ilk bileşenini döndürüyor. Sayılar birkaç adımda taşar ya da sıfıra iner.

```starter
def guc_yontemi(A, adim):
    v = [1.0] * len(A)
    for _ in range(adim):
        v = [sum(a * x for a, x in zip(satir, v)) for satir in A]
    return {'ozdeger': round(v[0], 6), 'ozvektor': [round(x, 6) for x in v]}
```

```solution
def guc_yontemi(A, adim):
    import math
    if not isinstance(A, list) or not A:
        raise ValueError('A boş olmayan kare matris olmalı')
    n = len(A)
    for s in A:
        if not isinstance(s, list) or len(s) != n or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in s):
            raise ValueError('A kare sonlu sayı matrisi olmalı')
    if isinstance(adim, bool) or not isinstance(adim, int) or adim < 1:
        raise ValueError('adim pozitif int olmalı')

    def carp(v):
        return [sum(a * x for a, x in zip(satir, v)) for satir in A]

    v = [1.0 / n ** 0.5] * n
    for _ in range(adim):
        w = carp(v)
        uzunluk = sum(x * x for x in w) ** 0.5
        if uzunluk == 0:
            raise ValueError('vektör sıfıra indi')
        v = [x / uzunluk for x in w]
    ozdeger = sum(x * y for x, y in zip(v, carp(v)))
    ilk = next((x for x in v if abs(x) > 1e-12), 0.0)
    if ilk < 0:
        v = [-x for x in v]
    return {'ozdeger': round(ozdeger, 6), 'ozvektor': [round(x, 6) for x in v]}
```

```test
need('guc_yontemi')
import math, random

r = guc_yontemi([[2, 1], [1, 2]], 100)
yakin(r['ozdeger'], 3.0, 'baskın özdeğer 3', tol=1e-5)
eq(r['ozvektor'], [0.707107, 0.707107], 'özvektör [1, 1] yönünde, 6 basamak')
r = guc_yontemi([[5, 0, 0], [0, 2, 0], [0, 0, 1]], 200)
yakin(r['ozdeger'], 5.0, 'köşegen matriste en büyük öğe', tol=1e-5)
eq(r['ozvektor'], [1.0, 0.0, 0.0], 'baskın yön birinci eksen')
r = guc_yontemi([[-4, 0], [0, 1]], 200)
yakin(r['ozdeger'], -4.0, 'baskınlık mutlak değere göredir; özdeğer negatif olabilir', tol=1e-5)
ok(r['ozvektor'][0] > 0, 'işaret kuralı: ilk sıfırdan farklı bileşen pozitif', got=r['ozvektor'])
eq(guc_yontemi([[0, 0], [0, -4]], 9), {'ozdeger': -4.0, 'ozvektor': [0.0, 1.0]}, 'ilk bileşen sıfır, ikincisi negatifken (tek adımda) işaret çevrilir')
eq(guc_yontemi([[0, 0], [0, -4]], 10), {'ozdeger': -4.0, 'ozvektor': [0.0, 1.0]}, 'çift adımda da aynı birim özvektör')
eq(guc_yontemi([[1 / 3]], 1), {'ozdeger': 0.333333, 'ozvektor': [1.0]}, 'özdeğerde 6 basamak')
r1 = guc_yontemi([[2, 1], [1, 2]], 1)
yakin(r1['ozdeger'], 3.0, 'başlangıç vektörü zaten özvektörse tek adım yeter', tol=1e-6)
rng = random.Random(302)
for _ in range(20):
    t = rng.uniform(0.2, 1.3)
    l1 = rng.uniform(2.0, 6.0) * rng.choice([1, -1])
    l2 = rng.uniform(-0.5, 0.5) * abs(l1)
    c, s = math.cos(t), math.sin(t)
    A = [[l1 * c * c + l2 * s * s, (l1 - l2) * c * s], [(l1 - l2) * c * s, l1 * s * s + l2 * c * c]]
    r = guc_yontemi(A, 300)
    yakin(r['ozdeger'], l1, 'rastgele simetrik matriste baskın özdeğer', tol=1e-4)
    v = r['ozvektor']
    yakin(math.hypot(*v), 1.0, 'özvektör birim uzunlukta', tol=1e-5)
    artik = math.hypot(A[0][0] * v[0] + A[0][1] * v[1] - r['ozdeger'] * v[0], A[1][0] * v[0] + A[1][1] * v[1] - r['ozdeger'] * v[1])
    ok(artik < 1e-4, 'A v = lambda v sağlanır', got=artik)
raises(ValueError, guc_yontemi, [[0, 0], [0, 0]], 5, msg='sıfır matriste vektör sıfıra iner')
A = [[2, 1], [1, 2]]
guc_yontemi(A, 3)
eq(A, [[2, 1], [1, 2]], 'girdi değişmez')
for A, k in [(None, 5), (([[1]],), 5), (([1],), 5), ([], 5), ([[1, 2]], 5), ([[1, 2], [3]], 5), ([[1, "2"], [3, 4]], 5), ([[True]], 5), ([[float('nan')]], 5), ([[float('inf')]], 5), ([[1]], 0), ([[1]], 2.0), ([[1]], True), ([(1,)], 5)]:
    raises(ValueError, guc_yontemi, A, k, msg='bozuk girdi reddedilir')
```

```hint
Döngüde iki iş var: `w = A v` ve `v = w / ‖w‖`. Döngüden sonra `ozdeger = v · (A v)`. İşareti en sonda düzelt.
```
:::

::: gorev 3 · Rayleigh quotient ve artık
`ozcift_sina(A, v)` işlevini yaz. Bir vektörün özvektör olup olmadığını ve en uygun özdeğer tahminini verir.

- `A`: boş olmayan kare sayı matrisi. `v`: `A` ile aynı boyutta sayı listesi; sıfır vektör olamaz.
- `lambda`: $\dfrac{v \cdot (Av)}{v \cdot v}$.
- `artik`: $\dfrac{\lVert Av - \lambda v \rVert_2}{\lVert v \rVert_2}$. Gerçek bir özvektörde sıfırdır.
- Dönüş: `{'lambda': ..., 'artik': ...}`; 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç `v·v`'ye bölmüyor. `v` birim uzunlukta değilse özdeğer tahmini `‖v‖²` kat yanlış çıkar.

```starter
def ozcift_sina(A, v):
    Av = [sum(a * x for a, x in zip(satir, v)) for satir in A]
    lam = sum(x * y for x, y in zip(v, Av))
    artik = sum((y - lam * x) ** 2 for x, y in zip(v, Av)) ** 0.5
    return {'lambda': round(lam, 9), 'artik': round(artik, 9)}
```

```solution
def ozcift_sina(A, v):
    import math
    def sayilar(w):
        return isinstance(w, list) and w and not any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in w)
    if not isinstance(A, list) or not A or not sayilar(v) or len(v) != len(A):
        raise ValueError('A kare matris, v aynı boyutta vektör olmalı')
    for s in A:
        if not sayilar(s) or len(s) != len(A):
            raise ValueError('A kare sonlu sayı matrisi olmalı')
    vv = sum(x * x for x in v)
    if vv == 0:
        raise ValueError('v sıfır vektör olamaz')
    Av = [sum(a * x for a, x in zip(satir, v)) for satir in A]
    lam = sum(x * y for x, y in zip(v, Av)) / vv
    artik = (sum((y - lam * x) ** 2 for x, y in zip(v, Av)) / vv) ** 0.5
    return {'lambda': round(lam, 9), 'artik': round(artik, 9)}
```

```test
need('ozcift_sina')
import math, random

eq(ozcift_sina([[2, 1], [1, 2]], [1, 1]), {'lambda': 3.0, 'artik': 0.0}, 'gerçek özvektör, birim olmayan uzunlukta')
eq(ozcift_sina([[2, 1], [1, 2]], [5, -5]), {'lambda': 1.0, 'artik': 0.0}, 'ikinci özvektör, ölçeklenmiş')
r = ozcift_sina([[2, 1], [1, 2]], [1, 0])
eq(r, {'lambda': 2.0, 'artik': 1.0}, 'özvektör olmayan aday: artık sıfır değil')
eq(ozcift_sina([[7]], [3]), {'lambda': 7.0, 'artik': 0.0}, '1x1 matris')
eq(ozcift_sina([[1, 0, 0], [0, 0, 0], [0, 0, 0]], [1, 1, 1]), {'lambda': 0.333333333, 'artik': 0.471404521}, '9 basamak yuvarlama')
rng = random.Random(303)
for _ in range(25):
    n = rng.randint(1, 5)
    A = [[round(rng.uniform(-3, 3), 2) for _ in range(n)] for _ in range(n)]
    v = [round(rng.uniform(-3, 3), 2) or 1.0 for _ in range(n)]
    Av = [math.fsum(a * x for a, x in zip(s, v)) for s in A]
    vv = math.fsum(x * x for x in v)
    lam = math.fsum(x * y for x, y in zip(v, Av)) / vv
    art = math.sqrt(math.fsum((y - lam * x) ** 2 for x, y in zip(v, Av)) / vv)
    r = ozcift_sina(A, v)
    yakin(r['lambda'], lam, 'rastgele matriste lambda', tol=1e-7)
    yakin(r['artik'], art, 'rastgele matriste artık', tol=1e-7)
    r2 = ozcift_sina(A, [4 * x for x in v])
    yakin(r2['lambda'], r['lambda'], 'vektörü ölçeklemek lambda yı değiştirmez', tol=1e-7)
    yakin(r2['artik'], r['artik'], 'vektörü ölçeklemek artığı değiştirmez', tol=1e-7)
A, v = [[1, 2], [3, 4]], [1, 1]
ozcift_sina(A, v)
eq((A, v), ([[1, 2], [3, 4]], [1, 1]), 'girdiler değişmez')
for A, v in [([[1, 2], [3, 4]], [0, 0]), ([[1, 2], [3, 4]], [1]), ([[1, 2], [3]], [1, 1]), ([[1, 2], []], [1, 1]), ([[1, 2]], [1, 1]), ([[1]], []), ([], []), (([[1]],), [1]), (([1],), [1]), (None, [1]), ([[1]], None), ([[1, "2"], [3, 4]], [1, 1]), ([[1]], [True]), ([(1,)], [1]), ([[1]], (1,)), ([[float('nan')]], [1]), ([[1]], [float('inf')])]:
    raises(ValueError, ozcift_sina, A, v, msg='bozuk girdi reddedilir')
```

```hint
`Av`'yi bir kez hesapla. `lambda = (v·Av) / (v·v)`. Artık için `Av - lambda·v` vektörünün normunu `‖v‖`'ye böl; bu, `(Σ(...)² / v·v) ** 0.5` ile aynıdır.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur; her adım bu derste hesapladığın bir sayıya ya da örneğe dayanır.

1. **Çerçeve (15 sn).** "Bir dönüşüm çoğu oku hem çevirir hem uzatır; bazı okları ise yalnız uzatır. Onlar o dönüşümün kimliğidir."
2. **Örnek (30 sn).** Tahmin adımı: [1, 1] okunun yönü değişmedi, boyu üç katına çıktı. [1, 0] ise yön değiştirdi.
3. **Tekrar (30 sn).** "Aynı dönüşümü yüz kez uygularsanız her şey o en büyük uzama katsayısına bağlıdır: 1,1 ise patlar, 0,9 ise söner."
4. **Bağlantı (25 sn).** "Derin bir ağın eğitilip eğitilemeyeceği, katmanlarının bu katsayılarının 1'e ne kadar yakın olduğuna bağlıdır."
5. **Kapanış (20 sn).** "Özdeğer, bir sistemi tekrar tekrar çalıştırdığınızda ne olacağını önceden söyleyen sayıdır."
:::

::: anlat Sınır
Bu ders gerçek özdeğerleri, 2×2 kapalı formülü, `power iteration`'ı ve Rayleigh quotient'i anlatır. Power iteration yalnız mutlak değerce en büyük özdeğeri bulur ve bu özdeğerin tek olmasını ister: iki özdeğer eşit büyüklükteyse (örneğin `3` ve `-3`) yöntem yakınsamaz, yakınsa çok yavaşlar. Başlangıç vektörü baskın özvektöre tam dikse yöntem onu hiç bulamaz; kayan nokta hatası pratikte bunu çoğu zaman giderir ama garanti değildir. Görevlerdeki sabit başlangıç vektörü öğretim içindir; gerçek uygulamalar rastgele başlar. Bütün özdeğerleri bulmak için `QR algorithm` ya da `Lanczos` gibi yöntemler kullanılır ve bu derste işlenmez. Karmaşık özdeğerler (döndürme içeren, simetrik olmayan matrisler) kapsam dışındadır. Rayleigh quotient simetrik matrislerde en iyi tahmindir; simetrik olmayan matrislerde yalnız kaba bir tahmindir.

Kaynaklar: [Goodfellow, Bengio ve Courville 2016 - Deep Learning, Bölüm 2: Linear Algebra](https://www.deeplearningbook.org/contents/linear_algebra.html), [Trefethen ve Bau 1997 - Numerical Linear Algebra](https://people.maths.ox.ac.uk/trefethen/text.html), [Strang - Introduction to Linear Algebra](https://math.mit.edu/~gs/linearalgebra/).
:::

::: dusun
Bir matrisin özdeğerleri `1.1` ve `0.5`. Bu matrisi rastgele bir vektöre 100 kez uygularsan vektörün uzunluğu kabaca kaç katına çıkar? Özdeğerler `0.9` ve `0.5` olsaydı ne olurdu? Çok katmanlı bir ağda geriye doğru akan sinyal için bu ne anlama gelir?
:::

::: ozet
- Özvektör, matrisin yönünü değiştirmediği vektördür; özdeğer onun uzama katsayısıdır: `A v = λ v`.
- 2×2 matriste özdeğerler iz ve determinanttan bulunur; toplamları iz, çarpımları determinanttır.
- `Power iteration` çarp ve normalleştir adımını tekrarlar; baskın özvektöre `|λ2 / λ1|` hızıyla yakınsar.
- Rayleigh quotient bir vektöre en uygun özdeğer tahminidir; artık normu sıfırsa aday gerçek bir özçifttir.
- Tekrarlanan bir matris çarpımının büyümesi ya da sönmesi, en büyük özdeğerin 1'den büyük ya da küçük olmasına bağlıdır.
:::
