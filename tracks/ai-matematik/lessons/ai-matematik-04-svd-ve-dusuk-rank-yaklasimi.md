---
id: ai-matematik-04
title: "SVD ve Düşük Rank Yaklaşımı · Bir Matrisin En Önemli Yönleri"
summary: En büyük tekil değeri power iteration ile bul, deflation ile rank-k yaklaşımı kur ve Frobenius hatasıyla ne kadar bilgi kaybedildiğini ölç; LoRA'nın neden az parametreyle çalıştığını hesapla.
---

::: anlat 1. Her matris üç basit adımdır
`Singular Value Decomposition` (SVD), her matrisin üç adımın birleşimi olarak yazılabileceğini söyler:

$$A = U \Sigma V^\top = \sum_{i} \sigma_i\, u_i v_i^\top$$

- $V^\top$: girdiyi döndürür (birbirine dik `v_i` yönlerine ayırır).
- $\Sigma$: her yönü bir **tekil değer** $\sigma_i \ge 0$ ile ölçekler.
- $U$: sonucu çıktı uzayında döndürür (birbirine dik `u_i` yönlerine yerleştirir).

Tekil değerler büyükten küçüğe sıralanır. İlk birkaçı büyük, gerisi küçükse matris "aslında" düşük rank'lidir: küçükleri atarsan çok az şey kaybedersin. Sıfırdan farklı tekil değer sayısı matrisin rank'idir.

Özdeğerden farkı: özdeğer yalnız kare matrislerde ve her zaman gerçek olmayabilir; tekil değer **her** matriste vardır ve her zaman gerçek, negatif olmayan bir sayıdır. İkisi şöyle bağlıdır: $A$'nın tekil değerleri, $A^\top A$'nın özdeğerlerinin kareköküdür.

| Soru | Araç | Görev |
|---|---|---|
| Matrisin en güçlü yönü ve gücü ne? | En büyük tekil üçlü $(\sigma_1, u_1, v_1)$ | 1 |
| Matrisi `k` yönle nasıl özetlerim? | Rank-`k` yaklaşımı | 2 |
| Özet ne kadar iyi ve ne kadar küçük? | Frobenius hatası, parametre sayısı | 3 |
:::

::: anlat 2. En iyi düşük rank yaklaşımı
`Eckart-Young` teoremi şunu söyler: bir matrise en yakın rank-`k` matris, SVD'nin ilk `k` terimini tutup gerisini atarak elde edilir:

$$A_k = \sum_{i=1}^{k} \sigma_i\, u_i v_i^\top$$

Hata da tam olarak atılan tekil değerlerden gelir (`Frobenius` normunda):

$$\lVert A - A_k \rVert_F = \sqrt{\sigma_{k+1}^2 + \sigma_{k+2}^2 + \dots}$$

Frobenius normu, matrisin bütün öğelerinin karelerinin toplamının kareköküdür: matrisi uzun bir vektör gibi düşünüp `L2` normunu almak.

**Nasıl hesaplanır?** Bu derste en basit yolu kullanacaksın: $A^\top A$ üzerinde `power iteration` (bkz. `ai-matematik-03`) baskın `v_1` yönünü verir; $\sigma_1 = \lVert A v_1 \rVert$ ve $u_1 = A v_1 / \sigma_1$. Sonra bu terimi matristen çıkarırsın (`deflation`) ve kalan matriste aynı işlemi tekrarlarsın.

**Neden önemli?** `m × n` boyutlu bir matris `m·n` sayı tutar. Rank-`k` bir matris, `m × k` ve `k × n` boyutlu iki çarpanla, yani `k·(m + n)` sayıyla yazılabilir. `4096 × 4096` boyutlu bir ağırlık matrisi 16,8 milyon sayıdır; rank-8 bir güncelleme yalnız 65.536 sayıdır. `LoRA` tam olarak bunu yapar: önceden eğitilmiş ağırlığı dondurur ve yalnız düşük rank'li bir güncellemeyi eğitir.
:::

::: tahmin Rank-1 bir matrisin tekil değeri
Aşağıdaki matris iki vektörün dış çarpımıdır. Frobenius normu ne yazdırılır?

```python
u = [3, 4]
v = [1, 0, 0]
A = [[a * b for b in v] for a in u]
print(A)
print(sum(x * x for satir in A for x in satir) ** 0.5)
```

???

```cikti
[[3, 0, 0], [4, 0, 0]]
5.0
```
Dış çarpım $u v^\top$ her zaman rank 1'dir: bütün satırlar `v`'nin katıdır. Tek bir tekil değeri vardır ve bu $\lVert u \rVert \cdot \lVert v \rVert = 5 \cdot 1 = 5$'tir. Rank-1 bir matrisin Frobenius normu o tek tekil değere eşittir. Genel kural: $\lVert A \rVert_F^2 = \sigma_1^2 + \sigma_2^2 + \dots$
:::

::: gorev 1 · En büyük tekil üçlü
`en_buyuk_tekil(A, adim)` işlevini yaz.

- `A`: boş olmayan dikdörtgen sayı matrisi (`m × n`). `adim`: pozitif `int`.
- `v`, `n` boyutlu ve bütün bileşenleri 1 olan vektörün birim uzunluğa getirilmiş hâliyle başlar.
- Her adımda: `w = Aᵀ(A v)`; `w`'nin `L2` normu sıfırsa `ValueError`; `v = w / ‖w‖`.
- Sonunda: `sigma = ‖A v‖`; `u = A v / sigma`.
- İşaret kuralı: `v`'nin mutlak değeri `1e-12`'den büyük ilk bileşeni negatifse hem `u` hem `v` `-1` ile çarpılır.
- Dönüş: `{'sigma': ..., 'u': [...], 'v': [...]}`; sayılar 6 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç en büyük mutlak öğeyi tekil değer sanıyor ve yön hesaplamıyor.

```starter
def en_buyuk_tekil(A, adim):
    s = max(abs(x) for satir in A for x in satir)
    return {'sigma': round(float(s), 6), 'u': [1.0] + [0.0] * (len(A) - 1), 'v': [1.0] + [0.0] * (len(A[0]) - 1)}
```

```solution
def en_buyuk_tekil(A, adim):
    import math
    if not isinstance(A, list) or not A:
        raise ValueError('A boş olmayan matris olmalı')
    for s in A:
        if not isinstance(s, list) or not s or len(s) != len(A[0]) or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in s):
            raise ValueError('A dikdörtgen sonlu sayı matrisi olmalı')
    if isinstance(adim, bool) or not isinstance(adim, int) or adim < 1:
        raise ValueError('adim pozitif int olmalı')
    m, n = len(A), len(A[0])

    def ileri(v):
        return [sum(A[i][j] * v[j] for j in range(n)) for i in range(m)]

    def geri(y):
        return [sum(A[i][j] * y[i] for i in range(m)) for j in range(n)]

    v = [1.0 / n ** 0.5] * n
    for _ in range(adim):
        w = geri(ileri(v))
        uzunluk = sum(x * x for x in w) ** 0.5
        if uzunluk == 0:
            raise ValueError('vektör sıfıra indi')
        v = [x / uzunluk for x in w]
    Av = ileri(v)
    sigma = sum(x * x for x in Av) ** 0.5
    u = [x / sigma for x in Av]
    ilk = next((x for x in v if abs(x) > 1e-12), 0.0)
    if ilk < 0:
        u, v = [-x for x in u], [-x for x in v]
    return {'sigma': round(sigma, 6), 'u': [round(x, 6) for x in u], 'v': [round(x, 6) for x in v]}
```

```test
need('en_buyuk_tekil')
import math, random

r = en_buyuk_tekil([[3, 0, 0], [4, 0, 0]], 50)
eq(r, {'sigma': 5.0, 'u': [0.6, 0.8], 'v': [1.0, 0.0, 0.0]}, 'rank-1 dış çarpım')
eq(en_buyuk_tekil([[3, 4]], 1), {'sigma': 5.0, 'u': [1.0], 'v': [0.6, 0.8]}, 'tek satırlı matris ve tek adım')
eq(en_buyuk_tekil([[0, 1, -2], [0, -1, 2]], 10), {'sigma': 3.162278, 'u': [0.707107, -0.707107], 'v': [0.0, 0.447214, -0.894427]}, 'ilk bileşen sıfır, ikincisi negatifken u ve v birlikte çevrilir')
r = en_buyuk_tekil([[2, 0], [0, -7]], 300)
yakin(r['sigma'], 7.0, 'tekil değer negatif olmaz', tol=1e-5)
eq(r['v'], [0.0, 1.0], 'v nin ilk sıfırdan farklı bileşeni pozitif')
eq(r['u'], [0.0, -1.0], 'işaret u ya taşınır')
r = en_buyuk_tekil([[1, 1], [1, 1], [1, 1]], 20)
yakin(r['sigma'], math.sqrt(6), 'bütün öğeleri 1 olan 3x2 matris', tol=1e-5)
rng = random.Random(401)
for _ in range(20):
    a, b = rng.uniform(0.2, 1.3), rng.uniform(0.1, 0.6)
    s1 = rng.uniform(2.0, 6.0)
    s2 = rng.uniform(0.0, 0.5) * s1
    u1, u2 = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))
    v1, v2 = (math.cos(b), math.sin(b)), (-math.sin(b), math.cos(b))
    A = [[s1 * u1[i] * v1[j] + s2 * u2[i] * v2[j] for j in range(2)] for i in range(2)]
    r = en_buyuk_tekil(A, 300)
    yakin(r['sigma'], s1, 'rastgele matriste en büyük tekil değer', tol=1e-4)
    for g, e in zip(r['v'], v1):
        yakin(g, e, 'sağ tekil vektör', tol=1e-4)
    for g, e in zip(r['u'], u1):
        yakin(g, e, 'sol tekil vektör', tol=1e-4)
    yakin(math.hypot(*r['u']), 1.0, 'u birim uzunlukta', tol=1e-5)
    for _ in range(3):
        t = rng.uniform(0, 6.283)
        x = (math.cos(t), math.sin(t))
        ok(math.hypot(A[0][0] * x[0] + A[0][1] * x[1], A[1][0] * x[0] + A[1][1] * x[1]) <= r['sigma'] + 1e-4, 'hiçbir birim vektör sigma dan fazla uzamaz')
raises(ValueError, en_buyuk_tekil, [[0, 0], [0, 0]], 5, msg='sıfır matris')
A = [[1, 2], [3, 4]]
en_buyuk_tekil(A, 3)
eq(A, [[1, 2], [3, 4]], 'girdi değişmez')
for A, k in [(None, 5), (([[1]],), 5), (([1],), 5), ([], 5), ([[]], 5), ([[1, 2], [3]], 5), ([[1, "2"]], 5), ([[True]], 5), ([(1, 2)], 5), ([[float('nan')]], 5), ([[float('inf')]], 5), ([[1]], 0), ([[1]], 1.5), ([[1]], True)]:
    raises(ValueError, en_buyuk_tekil, A, k, msg='bozuk girdi reddedilir')
```

```hint
İki yardımcı yaz: `ileri(v) = A v` (m boyutlu) ve `geri(y) = Aᵀ y` (n boyutlu). Döngüde `v ← geri(ileri(v))` ve normalleştir. Sonra `sigma = ‖ileri(v)‖`.
```
:::

::: gorev 2 · Rank-k yaklaşımı (deflation)
`dusuk_rank(A, k, adim)` işlevini yaz.

- `A`: boş olmayan dikdörtgen sayı matrisi. `k`, `adim`: pozitif `int`.
- `k` kez tekrarla: kalan matrisin en büyük tekil üçlüsünü Görev 1'deki yöntemle bul (aynı başlangıç vektörü, `adim` tekrar); $\sigma\, u v^\top$ terimini yaklaşıma ekle ve kalan matristen çıkar.
- Başlangıç vektörü kalan matrisin `nullspace`'ine düşebilir: o zaman `Rᵀ(R v)` sıfır çıkar ama kalan matris sıfır olmayabilir (birim matriste ikinci tur böyledir). Bir başlangıçta `Rᵀ(R v)`'nin normu `1e-12`'yi aşmazsa sırayla standart birim vektörlerden (`e_1, e_2, ...`) başlamayı dene. Hiçbir başlangıçtan sıfır olmayan bir yön çıkmazsa ya da bulunan `sigma` `1e-10`'dan küçük ya da eşitse dur: kalan matris sıfırdır.
- Dönüş: `{'yaklasim': m × n matris, 'tekil_degerler': bulunan sigma listesi}`; sayılar 6 basamağa yuvarlanır.
- Girdi matrisi değişmemelidir. Bozuk girdi `ValueError`.

KUSURLU başlangıç matrisin ilk `k` satırını tutup gerisini sıfırlıyor. Bu da rank'i en çok `k` olan bir matris verir, ama en iyi yaklaşım değildir.

```starter
def dusuk_rank(A, k, adim):
    yak = [[float(x) for x in satir] if i < k else [0.0] * len(satir) for i, satir in enumerate(A)]
    return {'yaklasim': yak, 'tekil_degerler': []}
```

```solution
def dusuk_rank(A, k, adim):
    import math
    if not isinstance(A, list) or not A:
        raise ValueError('A boş olmayan matris olmalı')
    for s in A:
        if not isinstance(s, list) or not s or len(s) != len(A[0]) or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in s):
            raise ValueError('A dikdörtgen sonlu sayı matrisi olmalı')
    for x in (k, adim):
        if isinstance(x, bool) or not isinstance(x, int) or x < 1:
            raise ValueError('k ve adim pozitif int olmalı')
    m, n = len(A), len(A[0])
    R = [[float(x) for x in s] for s in A]
    yak = [[0.0] * n for _ in range(m)]
    sigmalar = []
    for _ in range(k):
        baslangiclar = [[1.0 / n ** 0.5] * n] + [[1.0 if j == i else 0.0 for j in range(n)] for i in range(n)]
        v = None
        for v0 in baslangiclar:
            aday, sifir = v0, False
            for _ in range(adim):
                y = [sum(R[i][j] * aday[j] for j in range(n)) for i in range(m)]
                w = [sum(R[i][j] * y[i] for i in range(m)) for j in range(n)]
                uzunluk = sum(x * x for x in w) ** 0.5
                if uzunluk <= 1e-12:
                    sifir = True
                    break
                aday = [x / uzunluk for x in w]
            if not sifir:
                v = aday
                break
        if v is None:
            break
        Rv = [sum(R[i][j] * v[j] for j in range(n)) for i in range(m)]
        sigma = sum(x * x for x in Rv) ** 0.5
        if sigma <= 1e-10:
            break
        sigmalar.append(round(sigma, 6))
        for i in range(m):
            for j in range(n):
                terim = Rv[i] * v[j]
                yak[i][j] += terim
                R[i][j] -= terim
    return {'yaklasim': [[round(x, 6) for x in s] for s in yak], 'tekil_degerler': sigmalar}
```

```test
need('dusuk_rank')
import math, random

r = dusuk_rank([[3, 0, 0], [4, 0, 0]], 1, 50)
eq(r, {'yaklasim': [[3.0, 0.0, 0.0], [4.0, 0.0, 0.0]], 'tekil_degerler': [5.0]}, 'rank-1 matrisin rank-1 yaklaşımı kendisidir')
r = dusuk_rank([[3, 0, 0], [4, 0, 0]], 3, 50)
eq(r['tekil_degerler'], [5.0], 'kalan matris sıfır olunca durur')
r = dusuk_rank([[5, 0], [0, 1]], 1, 200)
eq(r, {'yaklasim': [[5.0, 0.0], [0.0, 0.0]], 'tekil_degerler': [5.0]}, 'köşegen matriste büyük yön tutulur')
r = dusuk_rank([[1, 0], [0, 5]], 1, 200)
eq(r['yaklasim'], [[0.0, 0.0], [0.0, 5.0]], 'ilk satırı tutmak en iyi yaklaşım değildir')
eq(dusuk_rank([[0, 0], [0, 0]], 2, 10), {'yaklasim': [[0.0, 0.0], [0.0, 0.0]], 'tekil_degerler': []}, 'sıfır matris')
eq(dusuk_rank([[1, 0], [0, 1]], 2, 50), {'yaklasim': [[1.0, 0.0], [0.0, 1.0]], 'tekil_degerler': [1.0, 1.0]}, 'birim matris: ikinci turda başlangıç nullspace e düşer, birim vektörle devam edilir')
r = dusuk_rank([[2, 0, 0], [0, 1, 0], [0, 0, 1]], 3, 100)
eq(r['tekil_degerler'], [2.0, 1.0, 1.0], 'kalan matris başlangıca dikken üç tekil değerin hepsi bulunur')
rng = random.Random(402)
for _ in range(20):
    a, b = rng.uniform(0.2, 1.3), rng.uniform(0.1, 0.6)
    s1 = rng.uniform(2.0, 6.0)
    s2 = rng.uniform(0.1, 0.5) * s1
    u1, u2 = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))
    v1, v2 = (math.cos(b), math.sin(b)), (-math.sin(b), math.cos(b))
    A = [[s1 * u1[i] * v1[j] + s2 * u2[i] * v2[j] for j in range(2)] for i in range(2)]
    r1 = dusuk_rank(A, 1, 300)
    yakin(r1['tekil_degerler'][0], s1, 'ilk tekil değer', tol=1e-4)
    hata = math.sqrt(sum((A[i][j] - r1['yaklasim'][i][j]) ** 2 for i in range(2) for j in range(2)))
    yakin(hata, s2, 'rank-1 hatası atılan tekil değere eşit (Eckart-Young)', tol=1e-3)
    for i in range(2):
        for j in range(2):
            yakin(r1['yaklasim'][i][j], s1 * u1[i] * v1[j], 'rank-1 yaklaşım ilk terimdir', tol=1e-3)
    r2 = dusuk_rank(A, 2, 300)
    eq(len(r2['tekil_degerler']), 2, 'iki tekil değer')
    yakin(r2['tekil_degerler'][1], s2, 'ikinci tekil değer', tol=1e-3)
    for i in range(2):
        for j in range(2):
            yakin(r2['yaklasim'][i][j], A[i][j], 'rank-2 yaklaşım matrisi geri verir', tol=1e-3)
eq(dusuk_rank([[3, 4]], 1, 5), {'yaklasim': [[3.0, 4.0]], 'tekil_degerler': [5.0]}, 'tek satırlı matris')
eq(dusuk_rank([[1 / 3]], 1, 1), {'yaklasim': [[0.333333]], 'tekil_degerler': [0.333333]}, '6 basamak yuvarlama')
eq(dusuk_rank([[3, 0], [0, 1e-11]], 2, 10)['tekil_degerler'], [3.0], '1e-10 altındaki tekil değerde durur')
A = [[1, 2], [3, 4]]
dusuk_rank(A, 1, 5)
eq(A, [[1, 2], [3, 4]], 'girdi değişmez')
for A, k, n in [(None, 1, 5), (([[1]],), 1, 5), (([1],), 1, 5), ([], 1, 5), ([[]], 1, 5), ([[1], []], 1, 5), ([[1, 2], [3]], 1, 5), ([[1, "2"]], 1, 5), ([[True]], 1, 5), ([[float('nan')]], 1, 5), ([[float('inf')]], 1, 5), ([[1]], 0, 5), ([[1]], 1, 0), ([[1]], 1.0, 5), ([[1]], True, 5), ([(1,)], 1, 5)]:
    raises(ValueError, dusuk_rank, A, k, n, msg='bozuk girdi reddedilir')
```

```hint
Kalan matrisin `float` kopyasıyla çalış. Her turda `v`'yi bul, `Rv = R v` hesapla. `σ u vᵀ` teriminin `(i, j)` öğesi `Rv[i] * v[j]`'dir (çünkü `σ u = R v`); bunu yaklaşıma ekle, kalandan çıkar.
```
:::

::: gorev 3 · Yaklaşım ne kadar iyi, ne kadar küçük?
`yaklasim_ozeti(A, B, k)` işlevini yaz. `A` özgün matris, `B` onun rank-`k` yaklaşımıdır.

- `A`, `B`: aynı boyutta, boş olmayan dikdörtgen sayı matrisleri (`m × n`). `k`: pozitif `int`.
- `frobenius`: $\lVert A - B \rVert_F$. `goreli`: $\lVert A - B \rVert_F / \lVert A \rVert_F$; `A` sıfır matrisse `None`.
- `tam_parametre`: `m · n`. `dusuk_rank_parametre`: `k · (m + n)`.
- `oran`: `dusuk_rank_parametre / tam_parametre`. 1'den büyükse düşük rank biçimi daha **çok** yer tutar.
- Dönüş: bu beş anahtarlı sözlük; kayan noktalı değerler 6 basamağa yuvarlanır, parametre sayıları `int`.
- Boyut uyuşmazlığı ve bozuk girdi `ValueError`.

KUSURLU başlangıç hatayı öğelerin farklarının toplamı olarak hesaplıyor: artı ve eksi farklar birbirini götürür.

```starter
def yaklasim_ozeti(A, B, k):
    m, n = len(A), len(A[0])
    fark = sum(a - b for sa, sb in zip(A, B) for a, b in zip(sa, sb))
    toplam = sum(a for sa in A for a in sa)
    return {'frobenius': round(fark, 6), 'goreli': round(fark / toplam, 6), 'tam_parametre': m * n, 'dusuk_rank_parametre': k * (m + n), 'oran': round(k * (m + n) / (m * n), 6)}
```

```solution
def yaklasim_ozeti(A, B, k):
    import math
    def gecerli(M):
        if not isinstance(M, list) or not M:
            return False
        for s in M:
            if not isinstance(s, list) or not s or len(s) != len(M[0]):
                return False
            if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in s):
                return False
        return True
    if not gecerli(A) or not gecerli(B):
        raise ValueError('matris boş olmayan dikdörtgen sonlu sayı listesi olmalı')
    if len(A) != len(B) or len(A[0]) != len(B[0]):
        raise ValueError('matrisler aynı boyutta olmalı')
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise ValueError('k pozitif int olmalı')
    m, n = len(A), len(A[0])
    fark = sum((a - b) ** 2 for sa, sb in zip(A, B) for a, b in zip(sa, sb)) ** 0.5
    buyukluk = sum(a * a for sa in A for a in sa) ** 0.5
    return {
        'frobenius': round(fark, 6),
        'goreli': round(fark / buyukluk, 6) if buyukluk else None,
        'tam_parametre': m * n,
        'dusuk_rank_parametre': k * (m + n),
        'oran': round(k * (m + n) / (m * n), 6),
    }
```

```test
need('yaklasim_ozeti')
import math, random

r = yaklasim_ozeti([[5, 0], [0, 1]], [[5, 0], [0, 0]], 1)
eq(r, {'frobenius': 1.0, 'goreli': 0.196116, 'tam_parametre': 4, 'dusuk_rank_parametre': 4, 'oran': 1.0}, '2x2 de rank-1 yer kazandırmaz')
r = yaklasim_ozeti([[1, -1], [-1, 1]], [[0, 0], [0, 0]], 1)
eq(r['frobenius'], 2.0, 'artı ve eksi farklar birbirini götürmez')
eq(r['goreli'], 1.0, 'sıfır yaklaşımın göreli hatası 1')
eq(yaklasim_ozeti([[1, 2], [3, 4]], [[1, 2], [3, 4]], 2)['frobenius'], 0.0, 'kusursuz yaklaşım')
eq(yaklasim_ozeti([[0, 0]], [[0, 0]], 1)['goreli'], None, 'sıfır matriste göreli hata tanımsız')
buyuk = [[0.0] * 64 for _ in range(64)]
r = yaklasim_ozeti(buyuk, buyuk, 4)
eq((r['tam_parametre'], r['dusuk_rank_parametre'], r['oran']), (4096, 512, 0.125), '64x64 matriste rank-4: sekizde bir')
ok(yaklasim_ozeti([[1, 2], [3, 4]], [[1, 2], [3, 4]], 3)['oran'] > 1, 'k büyükse düşük rank biçimi daha çok yer tutar')
rng = random.Random(403)
for _ in range(25):
    m, n = rng.randint(1, 5), rng.randint(1, 5)
    A = [[round(rng.uniform(-3, 3), 2) for _ in range(n)] for _ in range(m)]
    B = [[round(rng.uniform(-3, 3), 2) for _ in range(n)] for _ in range(m)]
    k = rng.randint(1, 4)
    f = math.sqrt(math.fsum((A[i][j] - B[i][j]) ** 2 for i in range(m) for j in range(n)))
    na = math.sqrt(math.fsum(x * x for s in A for x in s))
    r = yaklasim_ozeti(A, B, k)
    yakin(r['frobenius'], f, 'rastgele matriste Frobenius', tol=2e-6)
    if na:
        yakin(r['goreli'], f / na, 'rastgele matriste göreli hata', tol=2e-6)
    eq((r['tam_parametre'], r['dusuk_rank_parametre']), (m * n, k * (m + n)), 'parametre sayıları')
    ok(isinstance(r['tam_parametre'], int) and isinstance(r['dusuk_rank_parametre'], int), 'parametre sayıları int')
eq(yaklasim_ozeti([[1 / 3, 0, 0]], [[0, 0, 0]], 1), {'frobenius': 0.333333, 'goreli': 1.0, 'tam_parametre': 3, 'dusuk_rank_parametre': 4, 'oran': 1.333333}, '6 basamak yuvarlama')
iyi = [[1, 2], [3, 4]]
for A, B, k in [(iyi, [[1, 2]], 1), (iyi, [[1], [2]], 1), ([[1], [1, 2]], [[1], [1, 2]], 1), ([[1], []], [[1], []], 1), ([[]], [[]], 1), (None, iyi, 1), (iyi, None, 1), ((iyi[0], iyi[1]), iyi, 1), ([], [], 1), (iyi, iyi, 0), (iyi, iyi, 1.0), (iyi, iyi, True), ([[1, "2"], [3, 4]], iyi, 1), ([[True, 2], [3, 4]], iyi, 1), ([(1, 2), (3, 4)], iyi, 1), ([[float('nan'), 2], [3, 4]], iyi, 1), (iyi, [[float('inf'), 2], [3, 4]], 1)]:
    raises(ValueError, yaklasim_ozeti, A, B, k, msg='bozuk girdi reddedilir')
```

```hint
Frobenius normu: farkların **karelerini** topla, karekök al. Parametre sayıları: `m * n` ve `k * (m + n)`.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur; her adım bu derste hesapladığın bir sayıya ya da örneğe dayanır.

1. **Çerçeve (15 sn).** "Her tablo üç basit hareketin birleşimidir: çevir, ger, yine çevir."
2. **Önemli yönler (30 sn).** "Germe katsayıları büyükten küçüğe sıralanır. İlk birkaçı büyük, gerisi küçükse tablo aslında çok daha basittir."
3. **Sayı (30 sn).** "4.096'ya 4.096'lık bir ağırlık tablosu 16,8 milyon sayıdır. Rank-8 bir güncelleme yalnız 65.536 sayı. Büyük modellere ince ayar bu yüzden bir dizüstünde yapılabiliyor."
4. **Bedel (25 sn).** "Attığınız katsayılar kadar bilgi kaybedersiniz; ne kadar kaybettiğinizi tam olarak hesaplayabilirsiniz."
5. **Kapanış (20 sn).** "Her öğrenmenin dev bir tabloyu değiştirmesi gerekmez; çoğu zaman birkaç yön yeter."
:::

::: anlat Sınır
Bu ders SVD'yi, en iyi düşük rank yaklaşımını ve bunun parametre sayısına etkisini anlatır. Buradaki yöntem (`AᵀA` üzerinde power iteration ve deflation) öğretim içindir: `AᵀA` kurmak koşul sayısının karesini alır ve küçük tekil değerlerde doğruluğu düşürür; deflation hataları her turda birikir; iki tekil değer birbirine yakınsa yakınsama çok yavaşlar. Görev 2 başlangıç vektörü kalan matrisin `nullspace`'ine düşünce birim vektörlere geçer; ama başlangıç baskın yöne dik olup başka bir yönde bileşen taşıyorsa yöntem sessizce daha küçük bir tekil değere yakınsayabilir. Gerçek kitaplıklar `Golub-Kahan` çift köşegenleştirme ya da büyük matrislerde rastgele (`randomized`) SVD kullanır. Görev 3'teki parametre hesabı yalnız iki çarpan matrisini sayar; `LoRA`'da özgün ağırlık da bellekte durur, kazanç eğitilen ve saklanan **güncelleme** içindir. Bir ağırlık matrisinin düşük rank'le iyi yaklaştırılabilmesi garanti değildir; tekil değerlerin ne kadar hızlı düştüğüne bağlıdır ve ölçülmelidir.

Kaynaklar: [Eckart ve Young 1936 - The approximation of one matrix by another of lower rank](https://doi.org/10.1007/BF02288367), [Hu vd. 2021 - LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685), [Trefethen ve Bau 1997 - Numerical Linear Algebra](https://people.maths.ox.ac.uk/trefethen/text.html), [Halko, Martinsson ve Tropp 2011 - Finding Structure with Randomness](https://arxiv.org/abs/0909.4061).
:::

::: dusun
`1024 × 1024` boyutlu bir ağırlık matrisine rank-16 bir güncelleme eğitiyorsun. Tam güncellemeye göre kaç kat az parametre eğitirsin? Rank'i kaç yaparsan düşük rank biçimi tam matristen daha çok yer tutmaya başlar? Bu sınır kare olmayan, `1024 × 64` boyutlu bir matriste nasıl değişir?
:::

::: ozet
- SVD her matrisi döndür, ölçekle, döndür adımlarına ayırır; tekil değerler her zaman gerçek ve negatif olmayan sayılardır.
- En büyük tekil üçlü, `AᵀA` üzerinde power iteration ile bulunur: `sigma = ‖A v‖`, `u = A v / sigma`.
- İlk `k` terimi tutmak en iyi rank-`k` yaklaşımını verir; Frobenius hatası atılan tekil değerlerin karelerinin toplamının kareköküdür.
- Rank-`k` bir `m × n` matris `k·(m + n)` sayıyla saklanır; `LoRA` bu yüzden az parametre eğitir.
- Kazanç, tekil değerlerin hızlı düşmesine bağlıdır; varsayılmaz, ölçülür.
:::
