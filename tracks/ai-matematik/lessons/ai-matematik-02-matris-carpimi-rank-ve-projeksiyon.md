---
id: ai-matematik-02
title: "Matris Çarpımı, Rank ve Projeksiyon · Bir Katmanın Yaptığı İş"
summary: Matris çarpımını, Gauss eleme ile rank hesabını ve bir vektörün başka bir vektör üzerine izdüşümünü kitaplıksız yaz; bir sinir ağı katmanının neden bir matris çarpımı olduğunu ve rank'in neyi sınırladığını gör.
---

::: anlat 1. Bir katman bir matristir
Bir sinir ağının doğrusal katmanı tek bir işlem yapar: girdi vektörünü bir matrisle çarpar. `d` boyutlu bir girdiyi `k` boyutlu bir çıktıya çeviren katmanın ağırlığı `k × d` boyutlu bir matristir. `Transformer`'daki `attention`, `embedding` tablosu ve çıkış katmanı da matris çarpımlarıdır. Bu yüzden üç şeyi bilmen gerekir:

| Soru | Araç | Görev |
|---|---|---|
| İki dönüşüm art arda uygulanırsa ne olur? | Matris çarpımı | 1 |
| Bir matris gerçekte kaç bağımsız yön taşıyor? | `rank` | 2 |
| Bir vektörün belli bir yöndeki payı ne kadar? | İzdüşüm (`projection`) | 3 |

> [!NOT]
> Görevler saf Python ile, küçük matrislerde çalışır. Gerçek kitaplıklar aynı işlemleri sayısal olarak daha kararlı yöntemlerle (örneğin rank için `SVD`) yapar; bu fark "Sınır" bölümünde açıklanır.
:::

::: anlat 2. Matris çarpımı
`A` matrisi `m × n`, `B` matrisi `n × p` boyutluysa çarpım `C = AB` `m × p` boyutludur ve her öğesi bir iç çarpımdır:

$$C_{ij} = \sum_{k=1}^{n} A_{ik} B_{kj}$$

Yani `C`'nin `i`. satır, `j`. sütun öğesi, `A`'nın `i`. satırı ile `B`'nin `j`. sütununun iç çarpımıdır. İç boyutlar (`n`) eşleşmek zorundadır; eşleşmiyorsa çarpım tanımsızdır.

İki özellik sezgiye aykırıdır:

- **Sıra önemlidir.** Genelde $AB \ne BA$. Önce döndürüp sonra germek ile önce gerip sonra döndürmek farklı sonuç verir.
- **Art arda doğrusal katmanlar tek katmana iner.** $y = B(Ax) = (BA)x$. Aralarında doğrusal olmayan bir işlev (`ReLU`, `GELU`) olmadan yüz katman üst üste koymak, tek bir matrisle aynı şeydir. Sinir ağlarının aktivasyon işlevine ihtiyaç duymasının sebebi budur.
:::

::: anlat 3. Rank ve izdüşüm
**Rank**, bir matrisin satırları (ya da sütunları) arasında kaç tanesinin birbirinden bağımsız olduğudur. Üçüncü satır ilk ikisinin toplamıysa yeni bilgi taşımaz; rank 3 değil 2'dir. Rank, matrisin çıktısının kaç boyutlu bir uzaya yayılabildiğini söyler: `1000 × 1000` boyutlu ama rank'i 8 olan bir matris, her girdiyi 8 boyutlu bir altuzaya sıkıştırır.

Bunun pratik bir sonucu vardır. `r` rank'li bir `m × n` matris, `m × r` ve `r × n` boyutlu iki küçük matrisin çarpımı olarak yazılabilir. `LoRA` bu fikre dayanır: büyük bir ağırlık matrisini güncellemek yerine, çarpımı düşük rank'li olan iki küçük matrisi eğitir (bkz. `ai-matematik-04`).

Rank, **Gauss eleme** ile bulunur: satırları birbirinden çıkararak matrisi basamak biçimine getirirsin; sıfırdan farklı kalan satır sayısı rank'tir. Kayan nokta hesabında "sıfır" yerine küçük bir tolerans kullanılır.

**İzdüşüm**, bir vektörün başka bir vektörün yönündeki bileşenidir:

$$\text{proj}_u(v) = \frac{v \cdot u}{u \cdot u}\, u$$

Geriye kalan $v - \text{proj}_u(v)$ parçası `u`'ya diktir. Bir vektörü "şu yöndeki kısım" ve "ona dik kısım" diye ayırmak, yorumlanabilirlik çalışmalarının temel işlemidir: bir aktivasyon vektöründen belirli bir yönü çıkarmak tam olarak bu dik parçayı almaktır.
:::

::: tahmin Sıra önemli mi?
İki matris iki farklı sırayla çarpılıyor. Ne yazdırılır?

```python
def carp(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(len(B))) for j in range(len(B[0]))] for i in range(len(A))]

A = [[1, 2], [0, 1]]
B = [[0, 1], [1, 0]]
print(carp(A, B))
print(carp(B, A))
```

???

```cikti
[[2, 1], [1, 0]]
[[0, 1], [1, 2]]
```
`B` satırları (ya da sütunları) yer değiştiren bir matristir. `AB` çarpımında `B` sağdadır ve `A`'nın **sütunlarını** değiştirir; `BA` çarpımında soldadır ve `A`'nın **satırlarını** değiştirir. Sonuçlar farklıdır: matris çarpımı değişmeli değildir.
:::

::: gorev 1 · Matris çarpımı
`matris_carp(A, B)` işlevini yaz.

- `A`, `B`: boş olmayan, dikdörtgen (bütün satırları aynı uzunlukta, boş olmayan) sayı matrisleri; liste listesi.
- `A`'nın sütun sayısı `B`'nin satır sayısına eşit olmalıdır.
- Dönüş: `C = AB`; öğeler 9 basamağa yuvarlanır.
- Boyut uyuşmazlığı ve bozuk girdi `ValueError`.

KUSURLU başlangıç öğe öğe çarpıyor (`Hadamard` çarpımı). Aynı boyutlu matrislerde hata vermeden yanlış sonuç üretir.

```starter
def matris_carp(A, B):
    return [[a * b for a, b in zip(sa, sb)] for sa, sb in zip(A, B)]
```

```solution
def matris_carp(A, B):
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
    if len(A[0]) != len(B):
        raise ValueError('iç boyutlar eşleşmiyor')
    return [[round(sum(A[i][k] * B[k][j] for k in range(len(B))), 9) for j in range(len(B[0]))] for i in range(len(A))]
```

```test
need('matris_carp')
import random

def _ref(A, B):
    C = []
    for satir in A:
        yeni = []
        for j in range(len(B[0])):
            t = 0.0
            for k in range(len(B)):
                t += satir[k] * B[k][j]
            yeni.append(round(t, 9))
        C.append(yeni)
    return C

eq(matris_carp([[1, 2], [0, 1]], [[0, 1], [1, 0]]), [[2, 1], [1, 0]], 'AB')
eq(matris_carp([[0, 1], [1, 0]], [[1, 2], [0, 1]]), [[0, 1], [1, 2]], 'BA, AB den farklı')
eq(matris_carp([[1, 2, 3]], [[4], [5], [6]]), [[32]], '1x3 çarpı 3x1 bir iç çarpımdır')
eq(matris_carp([[4], [5], [6]], [[1, 2, 3]]), [[4, 8, 12], [5, 10, 15], [6, 12, 18]], '3x1 çarpı 1x3 dış çarpımdır')
eq(matris_carp([[1, 0], [0, 1]], [[7, 8], [9, 10]]), [[7, 8], [9, 10]], 'birim matris değiştirmez')
eq(matris_carp([[1 / 3]], [[1]]), [[0.333333333]], '9 basamak yuvarlama')
rng = random.Random(201)
for _ in range(25):
    m, n, p = rng.randint(1, 4), rng.randint(1, 4), rng.randint(1, 4)
    A = [[rng.randint(-5, 5) for _ in range(n)] for _ in range(m)]
    B = [[round(rng.uniform(-2, 2), 2) for _ in range(p)] for _ in range(n)]
    got, exp = matris_carp(A, B), _ref(A, B)
    eq((len(got), len(got[0])), (m, p), 'çıktı boyutu m x p')
    for sg, se in zip(got, exp):
        for g, e in zip(sg, se):
            yakin(g, e, 'rastgele matrislerde bağımsız referansla aynı', tol=1e-8)
A, B = [[1, 2]], [[3], [4]]
matris_carp(A, B)
eq((A, B), ([[1, 2]], [[3], [4]]), 'girdiler değişmez')
for A, B in [([[1, 2]], [[1, 2]]), ([[1, 2], [3]], [[1], [2]]), ([[1], []], [[1]]), ([], [[1]]), ([[1]], []), ([[]], [[1]]), ([[1]], [[]]), (None, [[1]]), ([[1]], None), (([[1]],), [[1]]), (([1],), [[1]]), ([[1, "2"]], [[1], [2]]), ([[True]], [[1]]), ([(1, 2)], [[1], [2]]), ([1, 2], [[1], [2]]), ([[float('nan')]], [[1]]), ([[1]], [[float('inf')]])]:
    raises(ValueError, matris_carp, A, B, msg='boyut uyuşmazlığı ya da bozuk girdi reddedilir')
```

```hint
Üç iç içe döngü: `i` (A'nın satırı), `j` (B'nin sütunu), `k` (ortak boyut). `C[i][j] = Σ A[i][k] * B[k][j]`.
```
:::

::: gorev 2 · Gauss eleme ile rank
`rank(A, tol)` işlevini yaz.

- `A`: boş olmayan dikdörtgen sayı matrisi. `tol`: pozitif sayı; mutlak değeri `tol`'dan küçük ya da eşit olan sayı sıfır sayılır.
- Yöntem: matrisin bir kopyasında sütun sütun ilerle. Her sütunda, henüz kullanılmamış satırlar arasında mutlak değeri en büyük öğeyi pivot seç (`partial pivoting`). Pivot `tol`'dan büyükse o satırı öne al, altındaki satırlardan uygun katını çıkar ve rank'i bir artır.
- Dönüş: `int`.
- Girdi matrisi değişmemelidir. Bozuk girdi `ValueError`.

KUSURLU başlangıç sıfırdan farklı satırları sayıyor. Birbirinin katı olan iki satırı bağımsız sayar.

```starter
def rank(A, tol):
    return sum(1 for satir in A if any(abs(x) > tol for x in satir))
```

```solution
def rank(A, tol):
    import math
    if not isinstance(A, list) or not A:
        raise ValueError('A boş olmayan matris olmalı')
    for s in A:
        if not isinstance(s, list) or not s or len(s) != len(A[0]) or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in s):
            raise ValueError('A dikdörtgen sonlu sayı matrisi olmalı')
    if isinstance(tol, bool) or not isinstance(tol, (int, float)) or not math.isfinite(tol) or not tol > 0:
        raise ValueError('tol pozitif sonlu sayı olmalı')
    M = [[float(x) for x in s] for s in A]
    satir_sayisi, sutun_sayisi = len(M), len(M[0])
    r = 0
    for c in range(sutun_sayisi):
        if r == satir_sayisi:
            break
        p = max(range(r, satir_sayisi), key=lambda i: abs(M[i][c]))
        if abs(M[p][c]) <= tol:
            continue
        M[r], M[p] = M[p], M[r]
        for i in range(r + 1, satir_sayisi):
            kat = M[i][c] / M[r][c]
            for j in range(c, sutun_sayisi):
                M[i][j] -= kat * M[r][j]
        r += 1
    return r
```

```test
need('rank')
import random
from fractions import Fraction

def _ref(A):
    M = [[Fraction(x) for x in s] for s in A]
    r = 0
    for c in range(len(M[0])):
        p = next((i for i in range(r, len(M)) if M[i][c] != 0), None)
        if p is None:
            continue
        M[r], M[p] = M[p], M[r]
        for i in range(len(M)):
            if i != r and M[i][c] != 0:
                k = M[i][c] / M[r][c]
                M[i] = [a - k * b for a, b in zip(M[i], M[r])]
        r += 1
    return r

eq(rank([[1, 2], [2, 4]], 1e-9), 1, 'ikinci satır birincinin iki katı')
eq(rank([[1, 0], [0, 1]], 1e-9), 2, 'birim matris tam rank')
eq(rank([[1, 2, 3], [4, 5, 6], [5, 7, 9]], 1e-9), 2, 'üçüncü satır ilk ikisinin toplamı')
eq(rank([[0, 0], [0, 0]], 1e-9), 0, 'sıfır matris')
eq(rank([[0, 1], [1, 0]], 1e-9), 2, 'ilk pivot sıfır: satır değişimi gerekir')
eq(rank([[1, 2, 3]], 1e-9), 1, 'tek satır')
eq(rank([[1], [2], [3]], 1e-9), 1, 'tek sütun')
eq(rank([[1, 0], [0, 1e-12]], 1e-9), 1, 'toleransın altındaki pivot sıfır sayılır')
eq(rank([[1, 0], [0, 1e-12]], 1e-15), 2, 'tolerans küçülünce aynı matris tam rank')
ok(isinstance(rank([[1]], 1e-9), int) and not isinstance(rank([[1]], 1e-9), bool), 'dönüş int')
rng = random.Random(202)
for _ in range(30):
    m, n = rng.randint(1, 5), rng.randint(1, 5)
    taban = [[rng.randint(-3, 3) for _ in range(n)] for _ in range(rng.randint(1, m))]
    A = [[sum(rng.randint(-2, 2) * t[j] for t in taban) for j in range(n)] for _ in range(m)] if rng.random() < 0.6 else [[rng.randint(-3, 3) for _ in range(n)] for _ in range(m)]
    eq(rank(A, 1e-9), _ref(A), 'rastgele tam sayı matrisinde kesirli referansla aynı')
A = [[1, 2], [3, 4]]
rank(A, 1e-9)
eq(A, [[1, 2], [3, 4]], 'girdi matrisi değişmez')
for A, t in [(None, 1e-9), (([[1]],), 1e-9), (([1],), 1e-9), ([], 1e-9), ([[]], 1e-9), ([[1, 2], [3]], 1e-9), ([[1, "2"]], 1e-9), ([[True]], 1e-9), ([(1, 2)], 1e-9), ([[float('nan')]], 1e-9), ([[float('inf')]], 1e-9), ([[1]], 0), ([[1]], -1e-9), ([[1]], None), ([[1]], True), ([[1]], float('nan')), ([[1]], float('inf'))]:
    raises(ValueError, rank, A, t, msg='bozuk girdi reddedilir')
```

```hint
Önce matrisin `float` kopyasını al. `r` kullanılan satır sayısıdır. Her sütunda `r`'den sonraki satırlar arasında en büyük mutlak değerli öğeyi bul; `tol`'dan büyükse satırı `r`'ye taşı ve alttaki satırları sıfırla.
```
:::

::: gorev 3 · İzdüşüm ve dik parça
`izdusum(v, u)` işlevini yaz. `v` vektörünü `u` yönündeki parça ve ona dik parça olarak ayırır.

- `v`, `u`: aynı uzunlukta, boş olmayan sayı listeleri. `u` sıfır vektör olamaz.
- `katsayi`: $\dfrac{v \cdot u}{u \cdot u}$. `paralel`: `katsayi · u`. `dik`: `v - paralel`.
- Dönüş: `{'katsayi': ..., 'paralel': [...], 'dik': [...]}`; sayılar 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç `u·u` yerine `u`'nun normuna bölüyor. `u` birim uzunlukta değilse parça yanlış ölçeklenir ve "dik" parça dik olmaz.

```starter
def izdusum(v, u):
    k = sum(a * b for a, b in zip(v, u)) / sum(b * b for b in u) ** 0.5
    par = [k * b for b in u]
    return {'katsayi': round(k, 9), 'paralel': [round(x, 9) for x in par], 'dik': [round(a - x, 9) for a, x in zip(v, par)]}
```

```solution
def izdusum(v, u):
    import math
    for w in (v, u):
        if not isinstance(w, list) or not w or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in w):
            raise ValueError('vektör boş olmayan sonlu sayı listesi olmalı')
    if len(v) != len(u):
        raise ValueError('vektörler aynı uzunlukta olmalı')
    uu = sum(b * b for b in u)
    if uu == 0:
        raise ValueError('u sıfır vektör olamaz')
    k = sum(a * b for a, b in zip(v, u)) / uu
    par = [k * b for b in u]
    return {'katsayi': round(k, 9), 'paralel': [round(x, 9) for x in par], 'dik': [round(a - x, 9) for a, x in zip(v, par)]}
```

```test
need('izdusum')
import math, random

eq(izdusum([3, 4], [1, 0]), {'katsayi': 3.0, 'paralel': [3.0, 0.0], 'dik': [0.0, 4.0]}, 'x eksenine izdüşüm')
eq(izdusum([3, 4], [2, 0]), {'katsayi': 1.5, 'paralel': [3.0, 0.0], 'dik': [0.0, 4.0]}, 'u nun uzunluğu parçaları değiştirmez, yalnız katsayıyı')
eq(izdusum([2, 2], [1, 1]), {'katsayi': 2.0, 'paralel': [2.0, 2.0], 'dik': [0.0, 0.0]}, 'v zaten u yönünde')
eq(izdusum([1, -1], [1, 1]), {'katsayi': 0.0, 'paralel': [0.0, 0.0], 'dik': [1.0, -1.0]}, 'v u ya dik')
eq(izdusum([1, 0, 0], [1, 1, 1]), {'katsayi': 0.333333333, 'paralel': [0.333333333, 0.333333333, 0.333333333], 'dik': [0.666666667, -0.333333333, -0.333333333]}, '9 basamak yuvarlama')
rng = random.Random(203)
for _ in range(30):
    n = rng.randint(1, 8)
    v = [round(rng.uniform(-4, 4), 2) for _ in range(n)]
    u = [round(rng.uniform(-4, 4), 2) or 1.0 for _ in range(n)]
    r = izdusum(v, u)
    yakin(r['katsayi'], math.fsum(a * b for a, b in zip(v, u)) / math.fsum(b * b for b in u), 'katsayı bağımsız hesapla aynı', tol=1e-8)
    yakin(math.fsum(d * b for d, b in zip(r['dik'], u)), 0.0, 'dik parça u ya diktir', tol=1e-6)
    for p, d, a in zip(r['paralel'], r['dik'], v):
        yakin(p + d, a, 'paralel + dik = v', tol=1e-8)
    for p, b in zip(r['paralel'], u):
        yakin(p, r['katsayi'] * b, 'paralel = katsayı · u', tol=1e-7)
v, u = [1, 2], [3, 4]
izdusum(v, u)
eq((v, u), ([1, 2], [3, 4]), 'girdiler değişmez')
for v, u in [([1, 2], [0, 0]), ([1], [1, 2]), ([1], []), ([], []), (None, [1]), ([1], None), ([True], [1]), ([1, "2"], [1, 2]), ((1, 2), [1, 2]), ([float('nan')], [1]), ([1], [float('inf')])]:
    raises(ValueError, izdusum, v, u, msg='sıfır vektör, uzunluk farkı ya da bozuk girdi reddedilir')
```

```hint
Payda `u·u`'dur (normun karesi), norm değil. Önce katsayıyı bul, sonra `paralel = katsayi * u` ve `dik = v - paralel`.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur; her adım bu derste hesapladığın bir sayıya ya da örneğe dayanır.

1. **Çerçeve (15 sn).** "Bir sinir ağı katmanı tek bir şey yapar: gelen sayı listesini bir tabloyla çarpar."
2. **Sıra önemli (30 sn).** Tahmin adımındaki iki çarpımı göster: AB ile BA farklı çıkıyor. "Önce döndürüp sonra germek, önce gerip sonra döndürmekle aynı değil."
3. **Neden aktivasyon (30 sn).** "Arada eğrilik katmazsanız yüz katmanlık ağ tek bir tabloya eşittir. Derinliği anlamlı kılan şey katmanlar arasındaki küçük kıvrımlardır."
4. **Rank (25 sn).** "Bin satırlık bir tablo aslında yalnız sekiz bağımsız yön taşıyabilir. Büyük modelleri ucuza ince ayar yapmanın (LoRA) sırrı bu."
5. **Kapanış (20 sn).** "Bir modelin büyüklüğü, tablolarının boyutu değil, gerçekte kaç bağımsız yön kullandığıdır."
:::

::: anlat Sınır
Bu ders matris çarpımını, Gauss eleme ile rank hesabını ve tek bir vektör üzerine izdüşümü anlatır. Buradaki rank hesabı küçük ve iyi koşullu matrisler içindir: kayan nokta hatası birikince sonuç toleransa duyarlı hâle gelir ve "sayısal rank" seçilen toleransla değişir (Görev 2'deki son iki test bunu gösterir). Gerçek kitaplıklar rank'i tekil değerleri sayarak bulur (`SVD`, bkz. `ai-matematik-04`); bu daha kararlıdır. Üç iç içe döngülü çarpım $O(n^3)$ zamanda çalışır; gerçek sistemler önbelleğe duyarlı, paralel ve GPU üzerinde çalışan uygulamalar kullanır. İzdüşüm görevi tek bir yön içindir; birden çok yönün yaydığı bir altuzaya izdüşüm için yönlerin önce birbirine dik hâle getirilmesi (`Gram-Schmidt`, `QR`) gerekir ve bu derste işlenmez.

Kaynaklar: [Goodfellow, Bengio ve Courville 2016 - Deep Learning, Bölüm 2: Linear Algebra](https://www.deeplearningbook.org/contents/linear_algebra.html), [Hu vd. 2021 - LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685), [Strang - Introduction to Linear Algebra](https://math.mit.edu/~gs/linearalgebra/).
:::

::: dusun
Aralarında aktivasyon işlevi olmayan üç doğrusal katmanın ağırlıkları `10 × 4`, `4 × 10` ve `10 × 10` boyutlu. Bu üç katmanın birleşimi tek bir matrise eşittir. O matrisin boyutu nedir ve rank'i en çok kaç olabilir? Bu sana "dar bir ara katman" hakkında ne söyler?
:::

::: ozet
- Doğrusal bir katman bir matris çarpımıdır; `C[i][j]`, `A`'nın `i`. satırı ile `B`'nin `j`. sütununun iç çarpımıdır.
- Matris çarpımı değişmeli değildir ve art arda doğrusal katmanlar tek bir matrise iner; aktivasyon işlevi bu yüzden gereklidir.
- Rank, bağımsız satır sayısıdır ve matrisin çıktısının kaç boyuta yayılabildiğini sınırlar. Kayan noktada toleransa bağlıdır.
- İzdüşüm bir vektörü "şu yöndeki parça" ve "ona dik parça" olarak ayırır; payda `u·u`'dur.
:::
