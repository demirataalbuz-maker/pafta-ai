---
id: ai-matematik-09
title: "SGD, Momentum ve Adam · Adımı Nasıl Atarsın?"
summary: Gradient descent, momentum ve Adam güncellemelerini kitaplıksız yaz; öğrenme oranının hangi değerde ıraksadığını, momentumun dar vadide neden hızlandırdığını ve Adam'ın bias düzeltmesinin ne işe yaradığını ölç.
---

::: anlat 1. Yön belli, adım belli değil
`ai-matematik-08` gradient'i verdi: kaybın en hızlı **arttığı** yön. En hızlı azaldığı yön onun tersi, yani eksi gradient'tir. Ama o yönde **ne kadar** gideceğini söylemedi. Optimizer'ın işi budur.

| Yöntem | Güncelleme | Fikir | Görev |
|---|---|---|---|
| Gradient descent | $x \leftarrow x - \eta\, g$ | Eğim yönünde sabit oranlı adım | 1 |
| Momentum | $v \leftarrow \beta v + g,\quad x \leftarrow x - \eta\, v$ | Geçmiş gradient'leri biriktir; hız kazan | 2 |
| Adam | Her ağırlığa kendi adım boyu | Gradient'i kendi büyüklüğüne böl | 3 |

Burada $\eta$ öğrenme oranıdır (`learning rate`) ve $g$ gradient'tir. `SGD` (stochastic gradient descent), gradient'i bütün veri yerine küçük bir `mini-batch` üzerinden hesaplamaktır; güncelleme kuralı aynıdır, yalnız `g` gürültülüdür.
:::

::: anlat 2. Öğrenme oranı, momentum ve Adam
**Öğrenme oranı neden kritik?** En basit kayıp $f(x) = \frac{a}{2}x^2$ olsun; gradient'i $ax$'tir. Bir adım: $x \leftarrow x - \eta a x = (1 - \eta a)\,x$. Her adımda `x`, $(1 - \eta a)$ ile çarpılır:

- $\eta < 1/a$: `x` tek yönden sıfıra yaklaşır.
- $1/a < \eta < 2/a$: işaret değiştirerek (salınarak) yaklaşır.
- $\eta > 2/a$: $\lvert 1 - \eta a \rvert > 1$ olur ve `x` her adımda **büyür**: eğitim ıraksar.

Çok boyutta her yönün kendi eğriliği vardır. En dik yön (en büyük `a`) öğrenme oranının üst sınırını belirler; en yassı yön ise bu küçük oranla çok yavaş ilerler. Dik ve yassı yönlerin oranı büyükse (dar, uzun bir vadi) düz gradient descent bir duvardan ötekine zıplarken vadi boyunca sürünür.

**Momentum** buna çare olur. Güncelleme gradient'in kendisiyle değil, gradient'lerin biriken toplamıyla yapılır. Vadi boyunca gradient hep aynı yöndedir: hız birikir. Duvarlar arasında gradient işaret değiştirir: birbirini götürür. Sabit bir gradient altında hız $\dfrac{1}{1 - \beta}$ katına çıkar; $\beta = 0{,}9$ için on kat.

**Adam** iki hareketli ortalama tutar: gradient'in ortalaması `m` ve gradient'in karesinin ortalaması `v`.

$$m \leftarrow \beta_1 m + (1 - \beta_1) g \qquad v \leftarrow \beta_2 v + (1 - \beta_2) g^2$$

$$\hat{m} = \frac{m}{1 - \beta_1^t} \qquad \hat{v} = \frac{v}{1 - \beta_2^t} \qquad x \leftarrow x - \eta \frac{\hat{m}}{\sqrt{\hat{v}} + \epsilon}$$

Bölme, her ağırlığın adımını kendi gradient büyüklüğüne göre ölçekler: gradient'i hep büyük olan ağırlık küçük, hep küçük olan büyük adım atar. Sonuç: ilk adımın boyu gradient ne kadar büyük olursa olsun yaklaşık $\eta$'dır.

**Bias düzeltmesi** ($1 - \beta^t$'ye bölme) şunun içindir: `m` ve `v` sıfırdan başlar ve ilk adımlarda sıfıra doğru yanlıdır. $\beta_2 = 0{,}999$ ile ilk adımda `v`, gerçek değerin binde biridir; yalnız `v` düzeltilmeseydi ilk adım yaklaşık 30 kat büyük olurdu ($1/\sqrt{0{,}001} \approx 31{,}6$). `m` de düzeltilmezse o da $\beta_1 = 0{,}9$ ile gerçek değerin onda birine iner; iki yanlılık kısmen birbirini götürür ve ilk adım yaklaşık 3,2 kat büyük olur.
:::

::: tahmin Öğrenme oranı fazla büyükse
$f(x) = x^2$ için gradient $2x$'tir. Aynı başlangıçtan iki farklı öğrenme oranıyla beş adım atılıyor. Ne yazdırılır?

```python
for lr in (0.4, 1.1):
    x = 1.0
    for _ in range(5):
        x = x - lr * 2 * x
    print(lr, round(x, 5))
```

???

```cikti
0.4 0.00032
1.1 -2.48832
```
Her adım `x`'i $(1 - 2\eta)$ ile çarpar. $\eta = 0{,}4$ için çarpan $0{,}2$'dir: beş adımda $0{,}2^5 = 0{,}00032$. $\eta = 1{,}1$ için çarpan $-1{,}2$'dir: mutlak değeri 1'den büyük, yani her adımda uzaklaşır ve işaret değiştirir; $(-1{,}2)^5 = -2{,}48832$. Sınır $\eta = 1$'dir ($2/a$, burada $a = 2$). Eğitim kaybının birden fırlaması çoğu zaman tam olarak budur.
:::

::: gorev 1 · Gradient descent
`gradient_inisi(gradient, x0, lr, adim)` işlevini yaz.

- `gradient`: sayı listesi alıp aynı uzunlukta sayı listesi döndüren çağrılabilir. `x0`: boş olmayan sayı listesi. `lr`: pozitif sayı. `adim`: negatif olmayan `int`.
- Her adımda `x ← x - lr · gradient(x)`.
- Dönüş: `adim + 1` uzunlukta konum listesi (ilki `x0`); her konum 9 basamağa yuvarlanmış `float` listesi. Yuvarlama yalnız çıktıda yapılır; hesap yuvarlanmamış değerle sürer.
- `gradient` yanlış uzunlukta ya da sayı olmayan bir sonuç döndürürse ve bozuk girdide `ValueError`.

KUSURLU başlangıç gradient'i çıkarmak yerine topluyor: kayıp her adımda artıyor.

```starter
def gradient_inisi(gradient, x0, lr, adim):
    x = list(x0)
    yol = [list(x)]
    for _ in range(adim):
        g = gradient(x)
        x = [xi + lr * gi for xi, gi in zip(x, g)]
        yol.append(list(x))
    return yol
```

```solution
def gradient_inisi(gradient, x0, lr, adim):
    def sayilar(v):
        return isinstance(v, list) and v and not any(isinstance(a, bool) or not isinstance(a, (int, float)) for a in v)
    if not callable(gradient) or not sayilar(x0):
        raise ValueError('gradient çağrılabilir, x0 boş olmayan sayı listesi olmalı')
    if isinstance(lr, bool) or not isinstance(lr, (int, float)) or not lr > 0:
        raise ValueError('lr pozitif sayı olmalı')
    if isinstance(adim, bool) or not isinstance(adim, int) or adim < 0:
        raise ValueError('adim negatif olmayan int olmalı')
    x = [float(v) for v in x0]
    yol = [[round(v, 9) for v in x]]
    for _ in range(adim):
        g = gradient(list(x))
        if not sayilar(g) or len(g) != len(x):
            raise ValueError('gradient x ile aynı uzunlukta sayı listesi döndürmeli')
        x = [xi - lr * gi for xi, gi in zip(x, g)]
        yol.append([round(v, 9) for v in x])
    return yol
```

```test
need('gradient_inisi')
import random

g2 = lambda v: [2 * a for a in v]
yol = gradient_inisi(g2, [1.0], 0.4, 5)
eq(len(yol), 6, 'adım + 1 konum')
eq(yol[0], [1.0], 'ilk konum x0')
yakin(yol[5][0], 0.00032, 'çarpan 0.2: beş adımda 0.2 üzeri 5', tol=1e-9)
yol = gradient_inisi(g2, [1.0], 1.1, 5)
yakin(yol[5][0], -2.48832, 'sınırın üstünde ıraksar', tol=1e-8)
yol = gradient_inisi(g2, [1.0], 1.0, 4)
eq([p[0] for p in yol], [1.0, -1.0, 1.0, -1.0, 1.0], 'tam sınırda sonsuza kadar salınır')
eq(gradient_inisi(g2, [3.0, -4.0], 0.1, 0), [[3.0, -4.0]], 'sıfır adım')
dar = lambda v: [100 * v[0], 1 * v[1]]
yol = gradient_inisi(dar, [1.0, 1.0], 0.019, 200)
ok(abs(yol[-1][0]) < 1e-6 and abs(yol[-1][1]) > 0.01, 'dar vadi: dik yön hızla biter, yassı yön hâlâ uzakta', got=yol[-1])
rng = random.Random(901)
for _ in range(20):
    n = rng.randint(1, 5)
    a = [round(rng.uniform(0.5, 3), 2) for _ in range(n)]
    x0 = [round(rng.uniform(-3, 3), 2) for _ in range(n)]
    lr = round(rng.uniform(0.01, 0.3), 3)
    k = rng.randint(0, 15)
    yol = gradient_inisi(lambda v: [ai * vi for ai, vi in zip(a, v)], x0, lr, k)
    for i in range(n):
        yakin(yol[-1][i], x0[i] * (1 - lr * a[i]) ** k, 'ikinci derece kayıpta kapalı çözümle aynı', tol=1e-7)
x0 = [1.0, 2.0]
gradient_inisi(g2, x0, 0.1, 3)
eq(x0, [1.0, 2.0], 'x0 değişmez')
raises(ValueError, gradient_inisi, lambda v: [1.0], [1.0, 2.0], 0.1, 1, msg='yanlış uzunlukta gradient reddedilir')
raises(ValueError, gradient_inisi, lambda v: "x", [1.0], 0.1, 1, msg='sayı olmayan gradient reddedilir')
for a in ([None, [1.0], 0.1, 1], [g2, [], 0.1, 1], [g2, None, 0.1, 1], [g2, [1, "2"], 0.1, 1], [g2, [True], 0.1, 1], [g2, (1.0,), 0.1, 1], [g2, [1.0], 0, 1], [g2, [1.0], -0.1, 1], [g2, [1.0], None, 1], [g2, [1.0], True, 1], [g2, [1.0], float('nan'), 1], [g2, [1.0], 0.1, -1], [g2, [1.0], 0.1, 1.5], [g2, [1.0], 0.1, True]):
    raises(ValueError, gradient_inisi, *a, msg='bozuk girdi reddedilir')
```

```hint
Döngüde iki satır: `g = gradient(x)` ve `x = [xi - lr * gi ...]`. Her adımdan sonra yuvarlanmış bir kopyayı listeye ekle.
```
:::

::: gorev 2 · Momentum
`momentum_inisi(gradient, x0, lr, beta, adim)` işlevini yaz.

- Görev 1'deki argümanlara ek olarak `beta`: `[0, 1)` aralığında sayı.
- Hız `v` sıfır vektörle başlar. Her adımda: `v ← beta · v + g`, sonra `x ← x - lr · v`.
- Dönüş: Görev 1'deki gibi `adim + 1` konum.
- `beta = 0` iken sonuç düz gradient descent ile aynı olmalıdır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç hızı biriktirmiyor: her adımda `v`'yi sıfırlayıp yalnız `beta` ile ölçeklenmiş gradient'i kullanıyor.

```starter
def momentum_inisi(gradient, x0, lr, beta, adim):
    x = [float(v) for v in x0]
    yol = [[round(v, 9) for v in x]]
    for _ in range(adim):
        g = gradient(list(x))
        v = [beta * gi for gi in g]
        x = [xi - lr * vi for xi, vi in zip(x, v)]
        yol.append([round(a, 9) for a in x])
    return yol
```

```solution
def momentum_inisi(gradient, x0, lr, beta, adim):
    def sayilar(v):
        return isinstance(v, list) and v and not any(isinstance(a, bool) or not isinstance(a, (int, float)) for a in v)
    if not callable(gradient) or not sayilar(x0):
        raise ValueError('gradient çağrılabilir, x0 boş olmayan sayı listesi olmalı')
    if isinstance(lr, bool) or not isinstance(lr, (int, float)) or not lr > 0:
        raise ValueError('lr pozitif sayı olmalı')
    if isinstance(beta, bool) or not isinstance(beta, (int, float)) or not 0 <= beta < 1:
        raise ValueError('beta [0, 1) aralığında olmalı')
    if isinstance(adim, bool) or not isinstance(adim, int) or adim < 0:
        raise ValueError('adim negatif olmayan int olmalı')
    x = [float(v) for v in x0]
    hiz = [0.0] * len(x)
    yol = [[round(v, 9) for v in x]]
    for _ in range(adim):
        g = gradient(list(x))
        if not sayilar(g) or len(g) != len(x):
            raise ValueError('gradient x ile aynı uzunlukta sayı listesi döndürmeli')
        hiz = [beta * vi + gi for vi, gi in zip(hiz, g)]
        x = [xi - lr * vi for xi, vi in zip(x, hiz)]
        yol.append([round(v, 9) for v in x])
    return yol
```

```test
need('momentum_inisi')
import random

def _ref(grad, x0, lr, beta, adim):
    x, h = [float(a) for a in x0], [0.0 for _ in x0]
    for _ in range(adim):
        g = grad(list(x))
        for i in range(len(x)):
            h[i] = beta * h[i] + g[i]
            x[i] -= lr * h[i]
    return x

sabit = lambda v: [1.0]
yol = momentum_inisi(sabit, [0.0], 0.1, 0.9, 3)
eq([p[0] for p in yol], [0.0, -0.1, -0.29, -0.561], 'sabit gradient altında adımlar büyür: 0.1, 0.19, 0.271')
yol = momentum_inisi(sabit, [0.0], 0.1, 0.9, 200)
yakin(yol[-1][0] - yol[-2][0], -1.0, 'hız 1 / (1 - beta) = 10 katına doyar', tol=1e-6)
g2 = lambda v: [2 * a for a in v]
duz = momentum_inisi(g2, [1.0, -2.0], 0.1, 0.0, 6)
for p, q in zip(duz[-1], [1.0 * 0.8 ** 6, -2.0 * 0.8 ** 6]):
    yakin(p, q, 'beta 0 iken düz gradient descent', tol=1e-8)
dar = lambda v: [100 * v[0], 1 * v[1]]
yavas = momentum_inisi(dar, [1.0, 1.0], 0.019, 0.0, 100)[-1]
hizli = momentum_inisi(dar, [1.0, 1.0], 0.019, 0.9, 100)[-1]
ok(abs(hizli[1]) < abs(yavas[1]) / 10, 'dar vadide momentum yassı yönde en az on kat daha ileride', got=(yavas, hizli))
eq(momentum_inisi(g2, [3.0], 0.1, 0.5, 0), [[3.0]], 'sıfır adım')
rng = random.Random(902)
for _ in range(20):
    n = rng.randint(1, 4)
    a = [round(rng.uniform(0.5, 3), 2) for _ in range(n)]
    x0 = [round(rng.uniform(-3, 3), 2) for _ in range(n)]
    lr, beta, k = round(rng.uniform(0.01, 0.1), 3), rng.choice([0.0, 0.5, 0.9]), rng.randint(0, 20)
    gr = lambda v: [ai * vi for ai, vi in zip(a, v)]
    got = momentum_inisi(gr, x0, lr, beta, k)
    eq(len(got), k + 1, 'adım + 1 konum')
    for p, q in zip(got[-1], _ref(gr, x0, lr, beta, k)):
        yakin(p, q, 'rastgele kayıpta bağımsız referansla aynı', tol=1e-7)
x0 = [1.0]
momentum_inisi(g2, x0, 0.1, 0.9, 3)
eq(x0, [1.0], 'x0 değişmez')
raises(ValueError, momentum_inisi, lambda v: [1.0, 2.0], [1.0], 0.1, 0.9, 1, msg='yanlış uzunlukta gradient reddedilir')
raises(ValueError, momentum_inisi, lambda v: (1.0,), [1.0], 0.1, 0.9, 1, msg='liste olmayan gradient reddedilir')
for a in ([None, [1.0], 0.1, 0.9, 1], [g2, [], 0.1, 0.9, 1], [g2, (1.0,), 0.1, 0.9, 1], [g2, [1, "2"], 0.1, 0.9, 1], [g2, [True], 0.1, 0.9, 1], [g2, [1.0], 0, 0.9, 1], [g2, [1.0], True, 0.9, 1], [g2, [1.0], "0.1", 0.9, 1], [g2, [1.0], float('nan'), 0.9, 1], [g2, [1.0], 0.1, 1.0, 1], [g2, [1.0], 0.1, -0.1, 1], [g2, [1.0], 0.1, None, 1], [g2, [1.0], 0.1, True, 1], [g2, [1.0], 0.1, False, 1], [g2, [1.0], 0.1, float('nan'), 1], [g2, [1.0], 0.1, 0.9, -1], [g2, [1.0], 0.1, 0.9, 2.0], [g2, [1.0], 0.1, 0.9, False]):
    raises(ValueError, momentum_inisi, *a, msg='bozuk girdi reddedilir')
```

```hint
Hızı döngünün **dışında** sıfırla ve her adımda güncelle: `hiz = beta * hiz + g`. Konumu hızla güncelle, gradient'le değil.
```
:::

::: gorev 3 · Adam
`adam_inisi(gradient, x0, lr, beta1, beta2, eps, adim)` işlevini yaz.

- `beta1`, `beta2`: `[0, 1)` aralığında sayı. `eps`: pozitif sayı. Diğerleri Görev 1'deki gibi.
- `m` ve `v` sıfır vektörle başlar. `t = 1, 2, ..., adim` için:
  - `m ← beta1 · m + (1 - beta1) · g`
  - `v ← beta2 · v + (1 - beta2) · g²`
  - `m̂ = m / (1 - beta1ᵗ)`, `v̂ = v / (1 - beta2ᵗ)`
  - `x ← x - lr · m̂ / (√v̂ + eps)`
- Dönüş: Görev 1'deki gibi `adim + 1` konum.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç bias düzeltmesini atlıyor: `m` ve `v` sıfırdan başladığı için ilk adımlar olması gerekenden çok farklı boyda atılıyor.

```starter
def adam_inisi(gradient, x0, lr, beta1, beta2, eps, adim):
    x = [float(a) for a in x0]
    m = [0.0] * len(x)
    v = [0.0] * len(x)
    yol = [[round(a, 9) for a in x]]
    for _ in range(adim):
        g = gradient(list(x))
        m = [beta1 * mi + (1 - beta1) * gi for mi, gi in zip(m, g)]
        v = [beta2 * vi + (1 - beta2) * gi * gi for vi, gi in zip(v, g)]
        x = [xi - lr * mi / (vi ** 0.5 + eps) for xi, mi, vi in zip(x, m, v)]
        yol.append([round(a, 9) for a in x])
    return yol
```

```solution
def adam_inisi(gradient, x0, lr, beta1, beta2, eps, adim):
    def sayi(a):
        return not isinstance(a, bool) and isinstance(a, (int, float))
    def sayilar(v):
        return isinstance(v, list) and v and all(sayi(a) for a in v)
    if not callable(gradient) or not sayilar(x0):
        raise ValueError('gradient çağrılabilir, x0 boş olmayan sayı listesi olmalı')
    if not sayi(lr) or not lr > 0 or not sayi(eps) or not eps > 0:
        raise ValueError('lr ve eps pozitif sayı olmalı')
    for b in (beta1, beta2):
        if not sayi(b) or not 0 <= b < 1:
            raise ValueError('beta [0, 1) aralığında olmalı')
    if isinstance(adim, bool) or not isinstance(adim, int) or adim < 0:
        raise ValueError('adim negatif olmayan int olmalı')
    x = [float(a) for a in x0]
    m = [0.0] * len(x)
    v = [0.0] * len(x)
    yol = [[round(a, 9) for a in x]]
    for t in range(1, adim + 1):
        g = gradient(list(x))
        if not sayilar(g) or len(g) != len(x):
            raise ValueError('gradient x ile aynı uzunlukta sayı listesi döndürmeli')
        m = [beta1 * mi + (1 - beta1) * gi for mi, gi in zip(m, g)]
        v = [beta2 * vi + (1 - beta2) * gi * gi for vi, gi in zip(v, g)]
        duz1, duz2 = 1 - beta1 ** t, 1 - beta2 ** t
        x = [xi - lr * (mi / duz1) / ((vi / duz2) ** 0.5 + eps) for xi, mi, vi in zip(x, m, v)]
        yol.append([round(a, 9) for a in x])
    return yol
```

```test
need('adam_inisi')
import math, random

def _ref(grad, x0, lr, b1, b2, eps, adim):
    x = [float(a) for a in x0]
    m, v = [0.0 for _ in x], [0.0 for _ in x]
    for t in range(1, adim + 1):
        g = grad(list(x))
        for i in range(len(x)):
            m[i] = b1 * m[i] + (1 - b1) * g[i]
            v[i] = b2 * v[i] + (1 - b2) * g[i] ** 2
            x[i] -= lr * (m[i] / (1 - b1 ** t)) / (math.sqrt(v[i] / (1 - b2 ** t)) + eps)
    return x

for buyukluk in (0.001, 1.0, 1000.0):
    yol = adam_inisi(lambda v: [buyukluk], [0.0], 0.01, 0.9, 0.999, 1e-12, 1)
    yakin(yol[1][0], -0.01, 'ilk adımın boyu gradient büyüklüğünden bağımsız, yaklaşık lr', tol=1e-6)
yol = adam_inisi(lambda v: [-5.0], [0.0], 0.01, 0.9, 0.999, 1e-12, 1)
yakin(yol[1][0], 0.01, 'yön gradient in işaretinin tersidir', tol=1e-6)
yol = adam_inisi(lambda v: [3.0, 0.003], [0.0, 0.0], 0.1, 0.9, 0.999, 1e-12, 10)
yakin(yol[-1][0], yol[-1][1], 'gradient i bin kat farklı iki ağırlık aynı hızla ilerler', tol=1e-5)
g2 = lambda v: [2 * a for a in v]
eq(adam_inisi(g2, [3.0], 0.1, 0.9, 0.999, 1e-8, 0), [[3.0]], 'sıfır adım')
eq(adam_inisi(lambda v: [2.0], [1.0], 1.0, 0.0, 0.0, 0.5, 1), [[1.0], [0.2]], 'eps paydaya eklenir')
yol = adam_inisi(g2, [1.0], 0.05, 0.9, 0.999, 1e-8, 300)
ok(abs(yol[-1][0]) < 0.05, 'x kare kaybında sıfıra yaklaşır', got=yol[-1])
rng = random.Random(903)
for _ in range(20):
    n = rng.randint(1, 4)
    a = [round(rng.uniform(0.5, 3), 2) for _ in range(n)]
    x0 = [round(rng.uniform(-3, 3), 2) for _ in range(n)]
    lr, b1, b2 = round(rng.uniform(0.001, 0.1), 3), rng.choice([0.0, 0.5, 0.9]), rng.choice([0.9, 0.99, 0.999])
    k = rng.randint(0, 25)
    gr = lambda v: [ai * vi for ai, vi in zip(a, v)]
    got = adam_inisi(gr, x0, lr, b1, b2, 1e-8, k)
    eq(len(got), k + 1, 'adım + 1 konum')
    for p, q in zip(got[-1], _ref(gr, x0, lr, b1, b2, 1e-8, k)):
        yakin(p, q, 'rastgele kayıpta bağımsız referansla aynı', tol=1e-7)
x0 = [1.0]
adam_inisi(g2, x0, 0.1, 0.9, 0.999, 1e-8, 3)
eq(x0, [1.0], 'x0 değişmez')
raises(ValueError, adam_inisi, lambda v: [1.0, 2.0], [1.0], 0.1, 0.9, 0.999, 1e-8, 1, msg='yanlış uzunlukta gradient reddedilir')
raises(ValueError, adam_inisi, lambda v: (1.0,), [1.0], 0.1, 0.9, 0.999, 1e-8, 1, msg='liste olmayan gradient reddedilir')
for a in ([None, [1.0], 0.1, 0.9, 0.999, 1e-8, 1], [g2, [], 0.1, 0.9, 0.999, 1e-8, 1], [g2, (1.0,), 0.1, 0.9, 0.999, 1e-8, 1], [g2, [True], 0.1, 0.9, 0.999, 1e-8, 1], [g2, [1.0], 0, 0.9, 0.999, 1e-8, 1], [g2, [1.0], True, 0.9, 0.999, 1e-8, 1], [g2, [1.0], float('nan'), 0.9, 0.999, 1e-8, 1], [g2, [1.0], 0.1, 1.0, 0.999, 1e-8, 1], [g2, [1.0], 0.1, False, 0.999, 1e-8, 1], [g2, [1.0], 0.1, float('nan'), 0.999, 1e-8, 1], [g2, [1.0], 0.1, 0.9, 1.0, 1e-8, 1], [g2, [1.0], 0.1, 0.9, -0.1, 1e-8, 1], [g2, [1.0], 0.1, 0.9, 0.999, 0, 1], [g2, [1.0], 0.1, 0.9, 0.999, None, 1], [g2, [1.0], 0.1, 0.9, 0.999, float('nan'), 1], [g2, [1.0], 0.1, 0.9, 0.999, 1e-8, -1], [g2, [1.0], 0.1, 0.9, 0.999, 1e-8, 1.0], [g2, [1.0], 0.1, 0.9, 0.999, 1e-8, False]):
    raises(ValueError, adam_inisi, *a, msg='bozuk girdi reddedilir')
```

```hint
Döngü sayacı `t` 1'den başlar. Düzeltme paydaları `1 - beta1 ** t` ve `1 - beta2 ** t`. Bölme düzeltilmiş `m̂` ve `v̂` ile yapılır; `eps` karekökün **dışına** eklenir.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur; her adım bu derste hesapladığın bir sayıya ya da örneğe dayanır.

1. **Çerçeve (15 sn).** "Yön belli; asıl soru adımın boyu."
2. **Fırlama (30 sn).** Tahmin adımı: aynı başlangıç, öğrenme oranı 0,4 iken beş adımda sıfıra yaklaşıyor, 1,1 iken her adımda uzaklaşıyor. "Eğitim kaybının birden fırlaması çoğu zaman budur."
3. **Momentum (30 sn).** "Dar bir vadide düz yürüyüş duvardan duvara zıplar. Momentum, yokuş aşağı yuvarlanan bir top gibi hız biriktirir ve zıplamaları söndürür."
4. **Adam (25 sn).** "Adam her ağırlığa kendi adım boyunu verir: hep büyük eğimli olana küçük, hep küçük eğimli olana büyük adım."
5. **Kapanış (20 sn).** "Büyük modellerin eğitiminde en çok ayarlanan tek sayı öğrenme oranıdır; matematiği burada."
:::

::: anlat Sınır
Bu ders üç güncelleme kuralını ikinci derece (dışbükey) kayıplarda anlatır. Öğrenme oranı sınırı `2/a` yalnız ikinci derece kayıpta kesindir; gerçek kayıp yüzeyleri dışbükey değildir ve eğrilik eğitim boyunca değişir, bu yüzden pratikte öğrenme oranı bir takvimle (`warmup`, `cosine decay`) değiştirilir ve bu derste işlenmez. Görevlerde gradient kesindir; `mini-batch` gürültüsü yoktur. Gürültü, momentumun ve Adam'ın davranışını değiştirir ve bazen genellemeye yardım eder. Buradaki momentum biçimi `v ← βv + g`'dir; bazı kitaplıklar `(1 − β)` ile ölçeklenmiş ya da `Nesterov` sürümünü kullanır ve aynı `lr` farklı adım boyu verir. Adam her zaman daha iyi değildir: bazı görevlerde iyi ayarlanmış SGD daha iyi genelleşir. `Weight decay`'in Adam ile doğru birleştirilmesi (`AdamW`) ayrı bir konudur (bkz. `ai-uretim-07`). Adam'ın adımı gradient büyüklüğünden bağımsız olduğu için gradient sıfıra yaklaşsa bile adım küçülmeyebilir; yakınsama için öğrenme oranının düşürülmesi gerekir.

Kaynaklar: [Kingma ve Ba 2015 - Adam: A Method for Stochastic Optimization](https://arxiv.org/abs/1412.6980), [Sutskever vd. 2013 - On the importance of initialization and momentum in deep learning](https://proceedings.mlr.press/v28/sutskever13.html), [Goh 2017 - Why Momentum Really Works](https://distill.pub/2017/momentum/), [Loshchilov ve Hutter 2019 - Decoupled Weight Decay Regularization](https://arxiv.org/abs/1711.05101).
:::

::: dusun
Bir eğitimde kayıp 2.000 adım boyunca düzgün azalıyor, sonra birden fırlıyor ve `NaN` oluyor. Bu derste gördüğün üç şeyden hangisi buna yol açmış olabilir? Her biri için bir ölçüm öner: neye bakarsan o nedeni doğrular ya da elersin?
:::

::: ozet
- Gradient descent `x ← x − η g` adımını atar; ikinci derece kayıpta `η > 2/a` olursa ıraksar.
- En dik yön öğrenme oranını sınırlar, en yassı yön hızı belirler; ikisinin oranı büyükse düz gradient descent yavaştır.
- Momentum gradient'leri biriktirir: tutarlı yönde `1 / (1 − β)` kat hızlanır, salınan yönde sönümler.
- Adam her ağırlığın adımını kendi gradient büyüklüğüne böler; ilk adım yaklaşık `η` boyundadır.
- Bias düzeltmesi, sıfırdan başlayan hareketli ortalamaların ilk adımlardaki yanlılığını giderir.
:::
