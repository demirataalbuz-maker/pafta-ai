---
id: ai-matematik-11
title: "Doğrusal ve Lojistik Regresyon · En Küçük Sinir Ağı"
summary: Doğrusal regresyonu kapalı formülle çöz, lojistik regresyonun kaybını ve gradient'ini türet ve modeli gradient descent ile sıfırdan eğit; bir sınıflandırıcının çıktısının neden olasılık olduğunu gör.
---

::: anlat 1. Tek katmanlı ağ
Bir sinir ağının son katmanı çoğu zaman tam olarak lojistik regresyondur: önceki katmanların çıkardığı özellikleri ağırlıklarla çarpar, toplar ve bir olasılığa çevirir. Bu dersteki iki model, derin ağlarda gördüğün her şeyin en küçük hâlidir: bir tahmin fonksiyonu, bir kayıp, bir gradient ve bir eğitim döngüsü.

| Model | Tahmin | Kayıp | Görev |
|---|---|---|---|
| Doğrusal regresyon | $\hat{y} = wx + b$ (bir sayı) | Ortalama kare hata (`MSE`) | 1 |
| Lojistik regresyon | $\hat{p} = \sigma(w \cdot x + b)$ (bir olasılık) | `Binary cross-entropy` | 2, 3 |

Burada $\sigma(z) = \dfrac{1}{1 + e^{-z}}$ `sigmoid` işlevidir: her gerçek sayıyı `(0, 1)` aralığına sıkıştırır.
:::

::: anlat 2. Kapalı çözüm, sigmoid ve gradient
**Doğrusal regresyon.** Tek değişkende en iyi doğru, kare hataların toplamını en küçük yapan doğrudur ve kapalı formülü vardır:

$$w = \frac{\sum (x_i - \bar{x})(y_i - \bar{y})}{\sum (x_i - \bar{x})^2} \qquad b = \bar{y} - w\bar{x}$$

Uyumun kalitesi $R^2 = 1 - \dfrac{\sum (y_i - \hat{y}_i)^2}{\sum (y_i - \bar{y})^2}$ ile ölçülür: 1 kusursuz uyum, 0 "hep ortalamayı tahmin et"ten iyi değil demektir.

**Lojistik regresyon.** Sınıflandırmada çıktı 0 ya da 1'dir; doğru çizmek anlamsızdır. Bunun yerine $z = w \cdot x + b$ (`logit`) hesaplanır ve sigmoid ile olasılığa çevrilir. Kayıp, `ai-matematik-10`'daki cross-entropy'nin iki sınıflı hâlidir:

$$L = -\frac{1}{n}\sum_i \big[y_i \ln \hat{p}_i + (1 - y_i)\ln(1 - \hat{p}_i)\big]$$

Bu kaybın gradient'i şaşırtıcı derecede yalındır:

$$\frac{\partial L}{\partial w_j} = \frac{1}{n}\sum_i (\hat{p}_i - y_i)\, x_{ij} \qquad \frac{\partial L}{\partial b} = \frac{1}{n}\sum_i (\hat{p}_i - y_i)$$

Gradient, "tahmin eksi gerçek" çarpı girdidir. Sigmoid'in türevi ile cross-entropy'nin türevi birbirini sadeleştirir; `softmax` ile cross-entropy'nin birlikte kullanılmasının sebebi de aynı sadeleşmedir.

**Sayısal kararlılık.** $e^{-z}$ büyük negatif `z` için taşar. Kararlı sigmoid, `z`'nin işaretine göre iki biçimden birini kullanır: $z \ge 0$ için $\dfrac{1}{1 + e^{-z}}$, $z < 0$ için $\dfrac{e^{z}}{1 + e^{z}}$. Kayıp da olasılıktan değil, doğrudan logit'ten hesaplanır: $\ell(z, y) = \max(z, 0) - yz + \log(1 + e^{-\lvert z \rvert})$. Olasılığı küçük bir `eps` ile kırpmak `ln 0`'ı önler ama kırpılan bölgede kaybı düzleştirir; o zaman raporlanan kayıp ile kullanılan gradient farklı fonksiyonlara ait olur.

Kapalı formül yoktur; model gradient descent ile eğitilir (bkz. `ai-matematik-09`).
:::

::: tahmin Sigmoid ne yapar?
Üç farklı `logit` için sigmoid çıktısı ne yazdırılır?

```python
import math

def sigmoid(z):
    return 1 / (1 + math.exp(-z))

for z in (0, 2, -2):
    print(z, round(sigmoid(z), 4))
```

???

```cikti
0 0.5
2 0.8808
-2 0.1192
```
`z = 0` tam kararsızlıktır: 0,5. `z = 2` ve `z = -2` birbirinin tümleyenidir: $\sigma(-z) = 1 - \sigma(z)$. Logit, olasılığın `log-odds` biçimidir: $z = \ln\dfrac{p}{1 - p}$. Logit'e 1 eklemek, olasılığı değil **oranı** (`odds`) $e \approx 2{,}72$ katına çıkarır.
:::

::: gorev 1 · Doğrusal regresyon (kapalı çözüm)
`dogrusal_regresyon(x, y)` işlevini yaz.

- `x`, `y`: aynı uzunlukta, en az iki öğeli sayı listeleri. `x`'in bütün değerleri aynı olamaz (eğim tanımsız).
- `egim` ve `kesisim`: yukarıdaki formüller. `r2`: $R^2$; `y`'nin bütün değerleri aynıysa `1.0`.
- Dönüş: `{'egim': ..., 'kesisim': ..., 'r2': ...}`; 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç doğruyu ilk ve son noktadan geçiriyor: aradaki bütün noktaları yok sayıyor.

```starter
def dogrusal_regresyon(x, y):
    w = (y[-1] - y[0]) / (x[-1] - x[0])
    return {'egim': round(w, 9), 'kesisim': round(y[0] - w * x[0], 9), 'r2': 1.0}
```

```solution
def dogrusal_regresyon(x, y):
    import math
    for v in (x, y):
        if not isinstance(v, list) or len(v) < 2 or any(isinstance(a, bool) or not isinstance(a, (int, float)) or not math.isfinite(a) for a in v):
            raise ValueError('en az iki sayıdan oluşan liste gerekli')
    if len(x) != len(y):
        raise ValueError('x ve y aynı uzunlukta olmalı')
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    if sxx == 0:
        raise ValueError('x in bütün değerleri aynı olamaz')
    w = sum((a - mx) * (b - my) for a, b in zip(x, y)) / sxx
    b0 = my - w * mx
    kalan = sum((b - (w * a + b0)) ** 2 for a, b in zip(x, y))
    toplam = sum((b - my) ** 2 for b in y)
    r2 = 1.0 if toplam == 0 else 1 - kalan / toplam
    return {'egim': round(w, 9), 'kesisim': round(b0, 9), 'r2': round(r2, 9)}
```

```test
need('dogrusal_regresyon')
import random, statistics

eq(dogrusal_regresyon([0, 1, 2], [1, 3, 5]), {'egim': 2.0, 'kesisim': 1.0, 'r2': 1.0}, 'tam doğru üzerindeki noktalar')
r = dogrusal_regresyon([0, 1, 2, 3], [0, 3, 1, 4])
eq((r['egim'], r['kesisim']), (1.0, 0.5), 'gürültülü veri: ilk ve son noktadan geçen doğru değil')
yakin(r['r2'], 0.5, 'gürültülü veride R kare', tol=1e-9)
eq(dogrusal_regresyon([1, 2, 3], [4, 4, 4]), {'egim': 0.0, 'kesisim': 4.0, 'r2': 1.0}, 'sabit y')
r = dogrusal_regresyon([0, 1, 2, 3], [1, -1, 1, -1])
ok(r['r2'] < 0.25, 'x ile ilgisiz y: R kare düşük', got=r)
rng = random.Random(1101)
for _ in range(25):
    n = rng.randint(2, 30)
    x = [round(rng.uniform(-5, 5), 2) for _ in range(n)]
    if len(set(x)) < 2:
        x[0] += 1.0
    y = [round(2.5 * a - 1 + rng.gauss(0, 2), 3) for a in x]
    r = dogrusal_regresyon(x, y)
    ref = statistics.linear_regression(x, y)
    yakin(r['egim'], ref.slope, 'rastgele veride eğim', tol=1e-7)
    yakin(r['kesisim'], ref.intercept, 'rastgele veride kesişim', tol=1e-7)
    yakin(r['r2'], statistics.correlation(x, y) ** 2, 'tek değişkende R kare korelasyonun karesidir', tol=1e-7)
    artik = [b - (r['egim'] * a + r['kesisim']) for a, b in zip(x, y)]
    yakin(sum(artik), 0.0, 'artıkların toplamı sıfır', tol=1e-5)
x, y = [0, 1], [1, 2]
dogrusal_regresyon(x, y)
eq((x, y), ([0, 1], [1, 2]), 'girdiler değişmez')
eq(dogrusal_regresyon([1e12 + 1.0, 1e12 + 2.0, 1e12 + 3.0], [1.0, 2.0, 4.0])['egim'], 1.5, 'büyük x ortalamasında merkezleme şarttır')
eq(dogrusal_regresyon([1.0, 2.0, 4.0], [1e12 + 1.0, 1e12 + 2.0, 1e12 + 3.0])['egim'], 0.642857143, 'büyük y ortalamasında merkezleme ve 9 basamak yuvarlama')
for a, b in [([1, 1, 1], [1, 2, 3]), ([1], [1]), ([], []), ([1, 2], [1]), ([1, 2, 3], [1, 2]), (None, [1, 2]), ([1, 2], None), ([1, "2"], [1, 2]), ([True, 2], [1, 2]), ((1, 2), [1, 2]), ([float('nan'), 1], [1, 2]), ([1, float('inf')], [1, 2])]:
    raises(ValueError, dogrusal_regresyon, a, b, msg='bozuk ya da çözümsüz girdi reddedilir')
```

```hint
Önce iki ortalamayı bul. Eğim, `Σ (x − x̄)(y − ȳ)` bölü `Σ (x − x̄)²`. Kesişim `ȳ − eğim · x̄`.
```
:::

::: gorev 2 · Lojistik regresyonun kaybı ve gradient'i
`lojistik_kayip(w, b, X, y)` işlevini yaz.

- `w`: boş olmayan sayı listesi (`d` ağırlık). `b`: sayı. `X`: boş olmayan liste; her satır `d` sayıdan oluşan liste. `y`: `X` ile aynı uzunlukta; her öğe `0` ya da `1` (`int`).
- Her örnek için `z = w·x + b`, `p = sigmoid(z)` (kararlı biçim).
- `kayip`: ortalama binary cross-entropy, **logit'ten** kararlı biçimde hesaplanır: örnek başına `max(z, 0) - y·z + log1p(exp(-|z|))`. Olasılığı kırpıp logaritma almak kullanılmaz: kırpılmış kayıp ile aşağıdaki gradient aynı fonksiyona ait olmaz.
- `dw`: `[ (1/n) Σ (p_i - y_i) x_ij ]`. `db`: `(1/n) Σ (p_i - y_i)`.
- Dönüş: `{'kayip': ..., 'dw': [...], 'db': ...}`; 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç kararsız sigmoid kullanıyor (büyük negatif `z`'de taşar) ve gradient'te girdiyle çarpmayı unutuyor: bütün ağırlıklar aynı gradient'i alıyor.

```starter
def lojistik_kayip(w, b, X, y):
    import math
    n = len(X)
    p = [1 / (1 + math.exp(-(sum(wi * xi for wi, xi in zip(w, x)) + b))) for x in X]
    kayip = -sum(yi * math.log(pi) + (1 - yi) * math.log(1 - pi) for pi, yi in zip(p, y)) / n
    d = sum(pi - yi for pi, yi in zip(p, y)) / n
    return {'kayip': round(kayip, 9), 'dw': [round(d, 9) for _ in w], 'db': round(d, 9)}
```

```solution
def lojistik_kayip(w, b, X, y):
    import math
    def sayi(a):
        return not isinstance(a, bool) and isinstance(a, (int, float)) and math.isfinite(a)
    if not isinstance(w, list) or not w or not all(sayi(a) for a in w) or not sayi(b):
        raise ValueError('w boş olmayan sayı listesi, b sayı olmalı')
    if not isinstance(X, list) or not X or not isinstance(y, list) or len(X) != len(y):
        raise ValueError('X ve y aynı uzunlukta, boş olmayan liste olmalı')
    for x in X:
        if not isinstance(x, list) or len(x) != len(w) or not all(sayi(a) for a in x):
            raise ValueError('her satır w ile aynı uzunlukta sayı listesi olmalı')
    if any(isinstance(t, bool) or t not in (0, 1) for t in y):
        raise ValueError('etiketler 0 ya da 1 olmalı')

    def sigmoid(z):
        if z >= 0:
            return 1 / (1 + math.exp(-z))
        e = math.exp(z)
        return e / (1 + e)

    n = len(X)
    p = [sigmoid(sum(wi * xi for wi, xi in zip(w, x)) + b) for x in X]
    zs = [sum(wi * xi for wi, xi in zip(w, x)) + b for x in X]
    kayip = sum(max(z, 0.0) - yi * z + math.log1p(math.exp(-abs(z))) for z, yi in zip(zs, y))
    dw = [sum((pi - yi) * x[j] for pi, yi, x in zip(p, y, X)) / n for j in range(len(w))]
    db = sum(pi - yi for pi, yi in zip(p, y)) / n
    return {'kayip': round(kayip / n, 9), 'dw': [round(g, 9) for g in dw], 'db': round(db, 9)}
```

```test
need('lojistik_kayip')
import math, random

r = lojistik_kayip([0.0], 0.0, [[1.0], [2.0]], [1, 0])
yakin(r['kayip'], math.log(2), 'sıfır ağırlıkta her tahmin 0.5: kayıp ln 2', tol=1e-9)
eq(r['dw'], [0.25], 'dw = ((0.5-1)·1 + (0.5-0)·2) / 2')
eq(r['db'], 0.0, 'db = ((0.5-1) + (0.5-0)) / 2')
r = lojistik_kayip([1.0, -1.0], 0.0, [[3.0, 1.0]], [1])
ok(r['dw'][0] != r['dw'][1], 'her ağırlığın gradient i kendi girdisine bağlı', got=r['dw'])
yakin(r['dw'][0] / r['dw'][1], 3.0, 'gradient oranı girdi oranına eşit', tol=1e-6)
r = lojistik_kayip([1.0], 0.0, [[-800.0], [800.0]], [0, 1])
ok(r['kayip'] < 1e-9, 'çok büyük logit lerde taşma yok, kayıp sıfıra yakın', got=r)
r = lojistik_kayip([1.0], 0.0, [[-800.0]], [1])
yakin(r['kayip'], 800.0, 'tamamen yanlış ve emin tahmin: kayıp logit ten hesaplanır, kırpılmaz', tol=1e-6)
r = lojistik_kayip([-1000.0], 0.0, [[1.0]], [1])
eq((r['kayip'], r['dw']), (1000.0, [-1.0]), 'kayıp ve gradient aynı amaca ait: kaybın eğimi -1')
def kayip_ref(w, b, X, y):
    t = 0.0
    for x, yi in zip(X, y):
        z = sum(a * c for a, c in zip(w, x)) + b
        t += math.log1p(math.exp(-z)) if yi == 1 else math.log1p(math.exp(z))
    return t / len(X)
rng = random.Random(1102)
for _ in range(20):
    d, n = rng.randint(1, 4), rng.randint(1, 12)
    w = [round(rng.uniform(-1.5, 1.5), 2) for _ in range(d)]
    b = round(rng.uniform(-1, 1), 2)
    X = [[round(rng.uniform(-2, 2), 2) for _ in range(d)] for _ in range(n)]
    y = [rng.randint(0, 1) for _ in range(n)]
    r = lojistik_kayip(w, b, X, y)
    yakin(r['kayip'], kayip_ref(w, b, X, y), 'rastgele veride kayıp bağımsız formülle aynı', tol=1e-8)
    h = 1e-6
    for j in range(d):
        wp, wm = list(w), list(w)
        wp[j] += h
        wm[j] -= h
        yakin(r['dw'][j], (kayip_ref(wp, b, X, y) - kayip_ref(wm, b, X, y)) / (2 * h), 'dw sayısal türevle aynı', tol=1e-5)
    yakin(r['db'], (kayip_ref(w, b + h, X, y) - kayip_ref(w, b - h, X, y)) / (2 * h), 'db sayısal türevle aynı', tol=1e-5)
iyi = ([1.0], 0.0, [[1.0]], [1])
for a in ([None, 0.0, [[1.0]], [1]], [[], 0.0, [[1.0]], [1]], [(1.0,), 0.0, [[1.0]], [1]], [[1.0], None, [[1.0]], [1]], [[1.0], True, [[1.0]], [1]], [[1.0], 0.0, [], []], [[1.0], 0.0, ([[1.0]],), [1]], [[1.0], 0.0, ([1.0],), [1]], [[1.0], 0.0, [[1.0]], (1,)], [[1.0], 0.0, [[1.0, 2.0]], [1]], [[1.0], 0.0, [[1.0]], [1, 0]], [[1.0], 0.0, [[1.0]], [2]], [[1.0], 0.0, [[1.0]], [True]], [[1.0], 0.0, [[1.0]], [0.5]], [[1.0], 0.0, [(1.0,)], [1]], [[1.0], 0.0, [[True]], [1]], [[True], 0.0, [[1.0]], [1]], [[float('nan')], 0.0, [[1.0]], [1]], [[1.0], float('inf'), [[1.0]], [1]], [[1.0], 0.0, [[float('nan')]], [1]]):
    raises(ValueError, lojistik_kayip, *a, msg='bozuk girdi reddedilir')
```

```hint
Kararlı sigmoid: `z >= 0` ise `1 / (1 + exp(-z))`, değilse `exp(z) / (1 + exp(z))`. Gradient `(p − y)` çarpı ilgili girdi bileşeninin ortalamasıdır.
```
:::

::: gorev 3 · Lojistik regresyonu sıfırdan eğit
`lojistik_egit(X, y, lr, adim)` işlevini yaz.

- `X`, `y`: Görev 2'deki gibi. `lr`: pozitif sayı. `adim`: negatif olmayan `int`.
- Ağırlıklar ve `b` sıfırdan başlar. Her adımda Görev 2'deki gradient'i hesapla ve `w ← w - lr · dw`, `b ← b - lr · db` uygula.
- Eğitimden sonra: `kayip` (son ağırlıklarla), `dogruluk` (`p >= 0.5` ise 1 tahmini; doğru tahmin oranı).
- Dönüş: `{'w': [...], 'b': ..., 'kayip': ..., 'dogruluk': ...}`; 6 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç `b`'yi hiç güncellemiyor: karar sınırı her zaman başlangıç noktasından geçmek zorunda kalıyor.

```starter
def lojistik_egit(X, y, lr, adim):
    import math
    d, n = len(X[0]), len(X)
    w, b = [0.0] * d, 0.0
    sig = lambda z: 1 / (1 + math.exp(-z)) if z >= 0 else math.exp(z) / (1 + math.exp(z))
    for _ in range(adim):
        p = [sig(sum(a * c for a, c in zip(w, x))) for x in X]
        w = [w[j] - lr * sum((pi - yi) * x[j] for pi, yi, x in zip(p, y, X)) / n for j in range(d)]
    p = [sig(sum(a * c for a, c in zip(w, x))) for x in X]
    kayip = -sum(math.log(max(pi, 1e-12)) if yi else math.log(max(1 - pi, 1e-12)) for pi, yi in zip(p, y)) / n
    return {'w': [round(a, 6) for a in w], 'b': 0.0, 'kayip': round(kayip, 6), 'dogruluk': round(sum((pi >= 0.5) == (yi == 1) for pi, yi in zip(p, y)) / n, 6)}
```

```solution
def lojistik_egit(X, y, lr, adim):
    import math
    def sayi(a):
        return not isinstance(a, bool) and isinstance(a, (int, float)) and math.isfinite(a)
    if not isinstance(X, list) or not X or not isinstance(y, list) or len(X) != len(y):
        raise ValueError('X ve y aynı uzunlukta, boş olmayan liste olmalı')
    if not isinstance(X[0], list) or not X[0]:
        raise ValueError('satırlar boş olmayan liste olmalı')
    d, n = len(X[0]), len(X)
    for x in X:
        if not isinstance(x, list) or len(x) != d or not all(sayi(a) for a in x):
            raise ValueError('satırlar aynı uzunlukta sayı listesi olmalı')
    if any(isinstance(t, bool) or t not in (0, 1) for t in y):
        raise ValueError('etiketler 0 ya da 1 olmalı')
    if not sayi(lr) or not lr > 0:
        raise ValueError('lr pozitif sayı olmalı')
    if isinstance(adim, bool) or not isinstance(adim, int) or adim < 0:
        raise ValueError('adim negatif olmayan int olmalı')

    def sigmoid(z):
        if z >= 0:
            return 1 / (1 + math.exp(-z))
        e = math.exp(z)
        return e / (1 + e)

    def tahminler(w, b):
        return [sigmoid(sum(a * c for a, c in zip(w, x)) + b) for x in X]

    w, b = [0.0] * d, 0.0
    for _ in range(adim):
        p = tahminler(w, b)
        dw = [sum((pi - yi) * x[j] for pi, yi, x in zip(p, y, X)) / n for j in range(d)]
        db = sum(pi - yi for pi, yi in zip(p, y)) / n
        w = [wj - lr * g for wj, g in zip(w, dw)]
        b -= lr * db
    p = tahminler(w, b)
    zs = [sum(wi * xi for wi, xi in zip(w, x)) + b for x in X]
    kayip = sum(max(z, 0.0) - yi * z + math.log1p(math.exp(-abs(z))) for z, yi in zip(zs, y))
    dogru = sum(1 for pi, yi in zip(p, y) if (pi >= 0.5) == (yi == 1))
    return {'w': [round(a, 6) for a in w], 'b': round(b, 6), 'kayip': round(kayip / n, 6), 'dogruluk': round(dogru / n, 6)}
```

```test
need('lojistik_egit')
import math, random

X = [[4.0], [5.0], [6.0], [7.0]]
y = [0, 0, 1, 1]
r0 = lojistik_egit(X, y, 0.1, 0)
eq(r0['w'], [0.0], 'sıfır adım: ağırlıklar sıfır')
eq(r0['b'], 0.0, 'sıfır adım: b sıfır')
yakin(r0['kayip'], math.log(2), 'sıfır adım: kayıp ln 2', tol=1e-6)
r = lojistik_egit(X, y, 0.3, 4000)
eq(r['dogruluk'], 1.0, 'sınır 5 ile 6 arasında: b olmadan ayrılamaz, b ile ayrılır')
ok(r['b'] < -1.0, 'karar sınırını kaydırmak için b negatif olmalı', got=r)
ok(5.0 < -r['b'] / r['w'][0] < 6.0, 'karar sınırı -b / w, 5 ile 6 arasında', got=r)
ok(r['kayip'] < r0['kayip'], 'eğitim kaybı düşürür')
r1 = lojistik_egit([[1.0], [2.0]], [1, 0], 0.5, 1)
eq(r1['w'], [-0.125], 'tek adım: w = 0 - 0.5 · 0.25')
eq(r1['b'], 0.0, 'tek adım: db sıfır olduğu için b değişmez')
def ref(X, y, lr, adim):
    d, n = len(X[0]), len(X)
    w, b = [0.0] * d, 0.0
    for _ in range(adim):
        p = [1 / (1 + math.exp(-(sum(a * c for a, c in zip(w, x)) + b))) for x in X]
        g = [sum((p[i] - y[i]) * X[i][j] for i in range(n)) / n for j in range(d)]
        gb = sum(p[i] - y[i] for i in range(n)) / n
        w = [w[j] - lr * g[j] for j in range(d)]
        b = b - lr * gb
    return w, b
rng = random.Random(1103)
for _ in range(15):
    d, n = rng.randint(1, 3), rng.randint(2, 12)
    X = [[round(rng.uniform(-2, 2), 2) for _ in range(d)] for _ in range(n)]
    y = [rng.randint(0, 1) for _ in range(n)]
    lr, k = round(rng.uniform(0.05, 0.5), 2), rng.randint(0, 40)
    r = lojistik_egit(X, y, lr, k)
    w, b = ref(X, y, lr, k)
    for a, c in zip(r['w'], w):
        yakin(a, c, 'rastgele veride ağırlıklar bağımsız referansla aynı', tol=2e-6)
    yakin(r['b'], b, 'rastgele veride b bağımsız referansla aynı', tol=2e-6)
    ok(0.0 <= r['dogruluk'] <= 1.0, 'doğruluk bir orandır')
X, y = [[1.0], [2.0]], [0, 1]
lojistik_egit(X, y, 0.1, 3)
eq((X, y), ([[1.0], [2.0]], [0, 1]), 'girdiler değişmez')
r_uc = lojistik_egit([[1000.0], [-1000.0]], [1, 0], 0.1, 2)
eq(r_uc['dogruluk'], 1.0, 'büyük pozitif ve negatif logit lerde taşma yok')
for a in ([None, [1], 0.1, 1], [[], [], 0.1, 1], [([[1.0]],), [1], 0.1, 1], [([1.0],), [1], 0.1, 1], [[[1.0]], (1,), 0.1, 1], [[[1.0]], [1, 0], 0.1, 1], [[[1.0], [1.0, 2.0]], [1, 0], 0.1, 1], [[[1.0], (1.0,)], [1, 0], 0.1, 1], [[[]], [1], 0.1, 1], [[1.0], [1], 0.1, 1], [[[1.0]], [2], 0.1, 1], [[[1.0]], [True], 0.1, 1], [[[True]], [1], 0.1, 1], [[[1.0]], [1], 0, 1], [[[1.0]], [1], None, 1], [[[1.0]], [1], True, 1], [[[1.0]], [1], float('nan'), 1], [[[1.0]], [1], float('inf'), 1], [[[float('nan')]], [1], 0.1, 1], [[[1.0]], [1], 0.1, -1], [[[1.0]], [1], 0.1, 1.0], [[[1.0]], [1], 0.1, True], [[(1.0,)], [1], 0.1, 1]):
    raises(ValueError, lojistik_egit, *a, msg='bozuk girdi reddedilir')
```

```hint
Döngüde dört iş: tahminleri hesapla, `dw` ve `db`'yi bul, ikisini de güncelle. `b`'yi unutma; tahminde de `+ b` olmalı.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur; her adım bu derste hesapladığın bir sayıya ya da örneğe dayanır.

1. **Çerçeve (15 sn).** "Her derin ağın son katmanı çoğu zaman bu derste yazdığın modeldir."
2. **Sigmoid (30 sn).** "Model bir puan üretir; sigmoid onu 0 ile 1 arasına sıkıştırır. Puan sıfırsa yarı yarıya; artı ikiyse yüzde 88."
3. **Öğrenme (30 sn).** "Hata sinyali şaşırtıcı derecede basittir: tahmin eksi gerçek, çarpı girdi. Model, yanıldığı kadar ve yanıldığı yönde düzeltilir."
4. **Tuzak (25 sn).** "Kaybı ve eğimi aynı formülden hesaplamazsanız raporladığınız sayı ile modelin öğrendiği şey farklı şeyler olur."
5. **Kapanış (20 sn).** "Bir sınıflandırıcının verdiği olasılık bir iddiadır; gerçek sıklıkla örtüşüp örtüşmediği ayrıca ölçülür."
:::

::: anlat Sınır
Bu ders tek değişkenli doğrusal regresyonu ve lojistik regresyonu anlatır. Doğrusal regresyonun kapalı çözümü tek değişken içindir; çok değişkende normal denklemler ya da `QR` ayrışımı kullanılır ve değişkenler birbirine bağımlıysa çözüm kararsızlaşır. $R^2$ yalnız eğitim verisindeki uyumu ölçer; modelin yeni veride işe yarayacağını göstermez (bkz. `ai-matematik-12`). Lojistik regresyon yalnız doğrusal bir karar sınırı çizebilir; sınıflar doğrusal ayrılamıyorsa özellik dönüşümü ya da gizli katman gerekir. Sınıflar **tam** ayrılabiliyorsa kayıp hiçbir zaman sıfıra ulaşmaz ve ağırlıklar sınırsız büyür; pratikte `regularization` ya da erken durdurma bunu sınırlar. Görev 3'teki tam veriyle (`full-batch`) gradient descent öğretim içindir; özellikler farklı ölçeklerdeyse yakınsama çok yavaşlar ve girdilerin ölçeklenmesi gerekir. Modelin verdiği olasılığın gerçek sıklıkla örtüşmesi (`calibration`) ayrıca ölçülmelidir; eğitim bunu garanti etmez.

Kaynaklar: [Goodfellow, Bengio ve Courville 2016 - Deep Learning, Bölüm 5: Machine Learning Basics](https://www.deeplearningbook.org/contents/ml.html), [Hastie, Tibshirani ve Friedman 2009 - The Elements of Statistical Learning](https://hastie.su.domains/ElemStatLearn/), [Bishop 2006 - Pattern Recognition and Machine Learning](https://www.microsoft.com/en-us/research/publication/pattern-recognition-machine-learning/).
:::

::: dusun
Görev 3'teki ilk veri (`4, 5 → 0` ve `6, 7 → 1`) tam ayrılabiliyor. Eğitimi 4.000 yerine 400.000 adım sürdürsen ağırlığa, kayba ve doğruluğa ne olur? Model yeni bir `5,5` girdisi için ne kadar "emin" olur ve bu güven haklı mıdır?
:::

::: ozet
- Doğrusal regresyon kare hatayı küçültür ve tek değişkende kapalı çözümü vardır; `R²` uyumu ölçer.
- Lojistik regresyon `logit`'i sigmoid ile olasılığa çevirir ve binary cross-entropy ile eğitilir.
- Kaybın gradient'i "tahmin eksi gerçek" çarpı girdidir; sigmoid ve cross-entropy türevleri sadeleşir.
- Sigmoid ve logaritma kararlı biçimde yazılmalıdır; yoksa büyük logit'lerde taşar.
- `b` karar sınırını kaydırır; tam ayrılabilen veride ağırlıklar sınırsız büyür.
:::
