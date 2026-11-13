---
id: ai-matematik-01
title: "Vektör, Norm ve İç Çarpım · Uzunluk, Açı ve Benzerlik"
summary: Lp normlarını, iç çarpımı ve cosine similarity'yi kitaplıksız yaz; aynı vektörün farklı normlarda neden farklı ölçüldüğünü ve embedding aramasının neye baktığını hesapla.
---

::: anlat 1. Neden buradan başlıyoruz?
Bir modelin gördüğü her şey bir sayı listesidir: bir görüntü piksel değerleridir, bir cümle bir `embedding` vektörüdür, modelin kendisi de ağırlık vektörleridir. Bu yoldaki bütün dersler üç sorunun üstüne kurulur:

| Soru | Araç | Görev |
|---|---|---|
| Bu vektör ne kadar büyük? | `Lp` normu: $\lVert v \rVert_p = \left(\sum_i \lvert v_i \rvert^p\right)^{1/p}$ | 1 |
| Bu iki vektör ne kadar aynı yöne bakıyor? | İç çarpım ve cosine: $\cos\theta = \dfrac{a \cdot b}{\lVert a \rVert_2 \lVert b \rVert_2}$ | 2 |
| Bir vektöre en çok benzeyenler hangileri? | Cosine'a göre ilk `k` komşu | 3 |

> [!NOT]
> Bütün görevler saf Python listeleriyle çalışır; `numpy` kullanılmaz. Amaç işlemi bir kez elle yazmaktır. Gerçek sistemler aynı hesabı vektörleştirilmiş kitaplıklarla ve çok daha hızlı yapar.
:::

::: anlat 2. Norm: "büyüklük" tek bir şey değildir
Bir vektörün büyüklüğünü ölçmenin birden çok yolu vardır ve hangisini seçtiğin, neye "küçük" dediğini değiştirir.

- **`L1`**: bileşenlerin mutlak değerlerinin toplamı. Şehir bloklarında yürünen mesafe gibidir.
- **`L2`**: Öklid uzunluğu; kuş uçuşu mesafe.
- **`L∞`** (L-sonsuz): en büyük mutlak bileşen. "Hiçbir bileşen şu değerden büyük olmasın" kuralı budur.

784 bileşenli bir vektörün her bileşeni 0.01 olsun. `L∞` normu yalnız 0.01'dir. `L2` normu ise $\sqrt{784 \cdot 0.01^2} = 0.28$'dir. Aynı vektör iki normda 28 kat farklı ölçülür. Genel kural: `d` boyutta her bileşeni `ε` olan vektörün `L2` normu $\varepsilon\sqrt{d}$'dir; boyut arttıkça fark büyür.

Üç norm arasında her zaman şu sıra vardır: $\lVert v \rVert_\infty \le \lVert v \rVert_2 \le \lVert v \rVert_1$.

Bir makalede "iki girdi arasındaki fark en çok 0.03" gibi bir cümle gördüğünde, hangi normda ölçüldüğünü bilmeden sayıyı yorumlayamazsın.
:::

::: anlat 3. İç çarpım ve cosine similarity
İç çarpım $a \cdot b = \sum_i a_i b_i$, iki vektörün ne kadar aynı yöne baktığını ve ne kadar uzun olduklarını birlikte ölçer. Uzunluğun etkisini çıkarmak için normlara bölersin; kalan şey aradaki açının kosinüsüdür:

- `1`: aynı yön. `0`: dik (ilgisiz). `-1`: zıt yön.

Embedding aramasında cosine tercih edilir, çünkü uzun bir belgenin vektörü kısa bir belgeninkinden yalnız uzun olduğu için "daha benzer" çıkmamalıdır. Önemli olan yöndür. Vektörler önceden birim uzunluğa getirilmişse (`normalize`), iç çarpım ile cosine aynı sayıdır; vektör veritabanlarının çoğu bu yüzden vektörleri normalleştirip yalnız iç çarpım hesaplar.

Sıfır vektörün yönü yoktur; cosine tanımsızdır. İyi bir uygulama bunu sessizce `0` saymaz, hata verir.
:::

::: tahmin Aynı vektör, iki norm
Dört bileşeni de 0.5 olan bir vektörün iki normu ne yazdırılır?

```python
v = [0.5, 0.5, 0.5, 0.5]
l2 = sum(x * x for x in v) ** 0.5
linf = max(abs(x) for x in v)
print("L2 =", l2)
print("Linf =", linf)
```

???

```cikti
L2 = 1.0
Linf = 0.5
```
`L∞` yalnız en büyük bileşene bakar: 0.5. `L2` dört bileşenin karelerini toplar: $\sqrt{4 \cdot 0.25} = 1$. Bileşen sayısını 4'ten 400'e çıkarsan `L∞` yine 0.5 kalır, `L2` ise 10 olur.
:::

::: gorev 1 · Lp normu
`norm(v, p)` işlevini yaz.

- `v`: boş olmayan sayı listesi. `p`: `1`, `2` ya da `"inf"` dizgisi.
- `p = 1`: mutlak değerler toplamı. `p = 2`: karelerin toplamının karekökü. `p = "inf"`: en büyük mutlak değer.
- Dönüş: `float`, 9 basamağa yuvarlanmış.
- Bozuk girdi `ValueError` (`bool` bir sayı değildir).

KUSURLU başlangıç mutlak değer almıyor: negatif bileşenler `L1`'de toplamı küçültüyor, `L∞`'da hiç görünmüyor.

```starter
def norm(v, p):
    if p == 1:
        return float(sum(v))
    if p == 2:
        return sum(x * x for x in v) ** 0.5
    return float(max(v))
```

```solution
def norm(v, p):
    import math
    if not isinstance(v, list) or not v or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in v):
        raise ValueError('v boş olmayan sonlu sayı listesi olmalı')
    if isinstance(p, bool) or p not in (1, 2, "inf"):
        raise ValueError('p 1, 2 ya da "inf" olmalı')
    if p == 1:
        return round(float(sum(abs(x) for x in v)), 9)
    if p == 2:
        return round(sum(x * x for x in v) ** 0.5, 9)
    return round(float(max(abs(x) for x in v)), 9)
```

```test
need('norm')
import math, random

eq(norm([3, -4], 1), 7.0, 'L1 mutlak değer toplamıdır')
eq(norm([3, -4], 2), 5.0, 'L2 Öklid uzunluğudur')
eq(norm([3, -4], "inf"), 4.0, 'L-sonsuz en büyük mutlak değerdir')
eq(norm([-2.5], "inf"), 2.5, 'tek negatif bileşen')
eq(norm([0, 0, 0], 2), 0.0, 'sıfır vektör')
eq(norm([0.01] * 784, "inf"), 0.01, '784 bileşende L-sonsuz 0.01')
yakin(norm([0.01] * 784, 2), 0.28, '784 bileşende L2 0.28', tol=1e-9)
eq((norm([1 / 3], 1), norm([1, 1], 2), norm([-1 / 3], "inf")), (0.333333333, 1.414213562, 0.333333333), '9 basamak yuvarlama')
rng = random.Random(101)
for _ in range(30):
    v = [round(rng.uniform(-5, 5), 3) for _ in range(rng.randint(1, 12))]
    yakin(norm(v, 1), math.fsum(abs(x) for x in v), 'rastgele L1', tol=1e-8)
    yakin(norm(v, 2), math.sqrt(math.fsum(x * x for x in v)), 'rastgele L2', tol=1e-8)
    yakin(norm(v, "inf"), max(max(v), -min(v)), 'rastgele L-sonsuz', tol=1e-8)
    ok(norm(v, "inf") <= norm(v, 2) + 1e-8 <= norm(v, 1) + 2e-8, 'L-sonsuz <= L2 <= L1')
ok(isinstance(norm([1, 2], 1), float), 'dönüş float')
v = [1, -2]
norm(v, 2)
eq(v, [1, -2], 'girdi değişmez')
for v, p in [(None, 2), ([], 2), ([1, "2"], 2), ([True], 2), ((1, 2), 2), ([float('nan')], 2), ([float('inf')], 1), ([float('-inf')], "inf"), ([1], 3), ([1], "2"), ([1], None), ([1], True)]:
    raises(ValueError, norm, v, p, msg='bozuk girdi reddedilir')
```

```hint
Üç dalın hepsinde `abs(x)` kullan. `L2` için karelerin toplamını alıp `** 0.5` uygula.
```
:::

::: gorev 2 · İç çarpım ve cosine similarity
`kosinus(a, b)` işlevini yaz.

- `a`, `b`: aynı uzunlukta, boş olmayan sayı listeleri.
- Dönüş: $\dfrac{a \cdot b}{\lVert a \rVert_2 \lVert b \rVert_2}$, 9 basamağa yuvarlanmış ve `[-1, 1]` aralığına kırpılmış (kayan nokta hatası 1'i çok az aşabilir).
- Vektörlerden biri sıfır vektörse `ValueError`: yönü olmayan bir vektörün açısı tanımsızdır.
- Uzunluk uyuşmazlığı ve bozuk girdi `ValueError`.

KUSURLU başlangıç yalnız iç çarpımı döndürüyor: uzun vektörler "daha benzer" çıkıyor.

```starter
def kosinus(a, b):
    return sum(x * y for x, y in zip(a, b))
```

```solution
def kosinus(a, b):
    import math
    for v in (a, b):
        if not isinstance(v, list) or not v or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in v):
            raise ValueError('vektör boş olmayan sonlu sayı listesi olmalı')
    if len(a) != len(b):
        raise ValueError('vektörler aynı uzunlukta olmalı')
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    if na == 0 or nb == 0:
        raise ValueError('sıfır vektörün yönü yoktur')
    c = sum(x * y for x, y in zip(a, b)) / (na * nb)
    return round(max(-1.0, min(1.0, c)), 9)
```

```test
need('kosinus')
import math, random

eq(kosinus([1, 0], [0, 1]), 0.0, 'dik vektörler')
eq(kosinus([1, 2, 3], [2, 4, 6]), 1.0, 'aynı yön, farklı uzunluk')
eq(kosinus([1, 2], [-1, -2]), -1.0, 'zıt yön')
eq(kosinus([1, 0], [1, 1]), 0.707106781, '45 derece, 9 basamak')
eq(kosinus([3, 4], [300, 400]), 1.0, 'ölçek benzerliği değiştirmez')
rng = random.Random(102)
for _ in range(30):
    n = rng.randint(1, 10)
    a = [round(rng.uniform(-3, 3), 3) or 1.0 for _ in range(n)]
    b = [round(rng.uniform(-3, 3), 3) or 1.0 for _ in range(n)]
    exp = math.fsum(x * y for x, y in zip(a, b)) / (math.sqrt(math.fsum(x * x for x in a)) * math.sqrt(math.fsum(y * y for y in b)))
    yakin(kosinus(a, b), exp, 'rastgele vektörlerde bağımsız hesapla aynı', tol=1e-8)
    yakin(kosinus(a, b), kosinus(b, a), 'simetrik', tol=1e-9)
    yakin(kosinus(a, [5 * y for y in b]), kosinus(a, b), 'pozitif ölçek değiştirmez', tol=1e-8)
    ok(-1.0 <= kosinus(a, b) <= 1.0, 'aralık içinde')
a, b = [1, 2], [3, 4]
kosinus(a, b)
eq((a, b), ([1, 2], [3, 4]), 'girdiler değişmez')
for a, b in [([0, 0], [1, 2]), ([1, 2], [0, 0]), ([1], [1, 2]), ([], [1]), ([], []), (None, [1]), ([1], "1"), ([True], [1]), ((1, 2), [1, 2]), ([1, "2"], [1, 2]), ([float('nan'), 0], [0, 1]), ([1, float('inf')], [1, 1])]:
    raises(ValueError, kosinus, a, b, msg='sıfır vektör, uzunluk farkı ya da bozuk girdi reddedilir')
```

```hint
Üç toplam gerekir: `a·b`, `a·a`, `b·b`. Normlar son ikisinin karekökü. Bölmeden önce sıfır kontrolü yap.
```
:::

::: gorev 3 · En yakın k komşu
`en_yakin(sorgu, vektorler, k)` işlevini yaz. Bir embedding aramasının çekirdeği budur.

- `sorgu`: boş olmayan sayı listesi. `vektorler`: boş olmayan liste; her öğe `sorgu` ile aynı uzunlukta sayı listesi.
- `k`: pozitif `int`. `k` vektör sayısından büyükse hepsi döner.
- Her vektörün `sorgu` ile cosine benzerliğini hesapla. Dönüş: `[[indeks, benzerlik], ...]`, benzerliğe göre azalan; eşitlikte küçük indeks önce. Benzerlik 6 basamağa yuvarlanır ve sıralama **yuvarlanmış** değerle yapılır.
- Sıfır vektör, uzunluk uyuşmazlığı ve bozuk girdi `ValueError`.

KUSURLU başlangıç iç çarpıma göre sıralıyor: yönü uzak ama uzun bir vektör, yönü aynı ama kısa bir vektörün önüne geçiyor.

```starter
def en_yakin(sorgu, vektorler, k):
    puan = [[i, round(sum(x * y for x, y in zip(sorgu, v)), 6)] for i, v in enumerate(vektorler)]
    return sorted(puan, key=lambda p: -p[1])[:k]
```

```solution
def en_yakin(sorgu, vektorler, k):
    import math
    def gecerli(v):
        return isinstance(v, list) and v and not any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in v)
    if not gecerli(sorgu) or not isinstance(vektorler, list) or not vektorler:
        raise ValueError('sorgu ve vektorler boş olmayan liste olmalı')
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise ValueError('k pozitif int olmalı')
    ns = sum(x * x for x in sorgu) ** 0.5
    if ns == 0:
        raise ValueError('sorgu sıfır vektör olamaz')
    puan = []
    for i, v in enumerate(vektorler):
        if not gecerli(v) or len(v) != len(sorgu):
            raise ValueError('vektör sorgu ile aynı uzunlukta sayı listesi olmalı')
        nv = sum(x * x for x in v) ** 0.5
        if nv == 0:
            raise ValueError('sıfır vektörün yönü yoktur')
        c = sum(x * y for x, y in zip(sorgu, v)) / (ns * nv)
        puan.append([i, round(max(-1.0, min(1.0, c)), 6)])
    puan.sort(key=lambda p: (-p[1], p[0]))
    return puan[:k]
```

```test
need('en_yakin')
import math, random

def _ref(s, vs, k):
    out = []
    for i in range(len(vs)):
        c = math.fsum(a * b for a, b in zip(s, vs[i])) / (math.sqrt(math.fsum(a * a for a in s)) * math.sqrt(math.fsum(b * b for b in vs[i])))
        out.append([i, round(max(-1.0, min(1.0, c)), 6)])
    return sorted(out, key=lambda p: (-p[1], p[0]))[:k]

vs = [[10, 10], [1, 0], [0.1, 0.0], [-1, 0]]
eq(en_yakin([1, 0], vs, 2), [[1, 1.0], [2, 1.0]], 'yön kazanır: uzun ama 45 derecelik vektör ilk ikiye giremez; eşitlikte küçük indeks')
eq(en_yakin([1, 0], vs, 10), [[1, 1.0], [2, 1.0], [0, 0.707107], [3, -1.0]], 'k büyükse hepsi, sıralı')
eq(en_yakin([0, 2], [[0, 5]], 1), [[0, 1.0]], 'tek vektör')
rng = random.Random(103)
for _ in range(25):
    d = rng.randint(1, 6)
    s = [rng.randint(-4, 4) or 1 for _ in range(d)]
    vs = [[rng.randint(-4, 4) or 1 for _ in range(d)] for _ in range(rng.randint(1, 9))]
    k = rng.randint(1, 11)
    eq(en_yakin(s, vs, k), _ref(s, vs, k), 'rastgele vektörlerde bağımsız referansla aynı')
s, vs = [1, 2], [[2, 1], [1, 2]]
en_yakin(s, vs, 1)
eq((s, vs), ([1, 2], [[2, 1], [1, 2]]), 'girdiler değişmez')
iyi = [[1, 2]]
for s, v, k in [([0, 0], iyi, 1), ([1, 2], [[0, 0]], 1), ([1, 2], [[1]], 1), ([1, 2], [[1, 2], []], 1), ([1, 2], [], 1), ([], iyi, 1), ([1, 2], iyi, 0), ([1, 2], iyi, 1.0), ([1, 2], iyi, True), ([1, 2], None, 1), ([1, 2], ([1, 2],), 1), ([1, 2], [(1, 2)], 1), ([1, "2"], iyi, 1), ([1, True], iyi, 1), ([float('nan'), 1], iyi, 1), ([1, 2], [[1, float('inf')]], 1)]:
    raises(ValueError, en_yakin, s, v, k, msg='bozuk girdi reddedilir')
```

```hint
Her vektör için `[indeks, yuvarlanmış benzerlik]` üret; `(-benzerlik, indeks)` anahtarıyla sırala; ilk `k` öğeyi al.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur; her adım bu derste hesapladığın bir sayıya ya da örneğe dayanır.

1. **Çerçeve (15 sn).** "Bir yapay zekâ için her şey bir sayı listesidir: bir cümle, bir resim, modelin kendisi."
2. **Büyüklük (30 sn).** Aynı listeyi iki cetvelle ölç: 784 pikselin her biri 0,01 değişirse en büyük değişim 0,01'dir ama toplam uzunluk 0,28'dir. "Küçük bir değişiklik" derken hangi cetveli kullandığını söylemelisin.
3. **Benzerlik (30 sn).** "İki metnin benzerliği, onları temsil eden iki okun arasındaki açıdır. Uzun bir belge yalnız uzun olduğu için benzer sayılmaz; yöne bakarız."
4. **Arama (25 sn).** "Bir sohbet botu belgelerinizde cevap ararken sorunuzun okuna en yakın açılı okları seçer. Arama motorunun yeni hâli bu."
5. **Kapanış (20 sn).** "Model 'bu ikisi benzer' dediğinde, bir açı ölçmüştür; anlam değil."
:::

::: anlat Sınır
Bu ders üç normu, iç çarpımı, cosine similarity'yi ve kaba kuvvet en yakın komşu aramasını anlatır. Görevler saf Python ile küçük vektörlerde çalışır; gerçek embedding vektörleri yüzlerce ya da binlerce boyutludur ve arama, bütün vektörleri gezmek yerine yaklaşık yöntemlerle (`HNSW`, `IVF`) yapılır. Bu yöntemler hız için doğruluktan biraz ödün verir ve bu derste işlenmez. Cosine yalnız yönü ölçer; uzunluğun anlam taşıdığı durumlarda (örneğin sıklık vektörleri) bilgi kaybettirir. Yüksek boyutta rastgele vektörlerin çoğu birbirine neredeyse diktir; bu yüzden düşük boyuttaki sezgiler her zaman taşınmaz. Kayan nokta toplamları sıraya duyarlıdır; görevlerdeki yuvarlama bunu gizler, ortadan kaldırmaz.

Kaynaklar: [Goodfellow, Bengio ve Courville 2016 - Deep Learning, Bölüm 2: Linear Algebra](https://www.deeplearningbook.org/contents/linear_algebra.html), [Strang - Introduction to Linear Algebra](https://math.mit.edu/~gs/linearalgebra/).
:::

::: dusun
İki belgen var: biri 50 kelimelik bir özet, diğeri aynı konuyu işleyen 5.000 kelimelik bir rapor. Kelime sayım vektörleriyle iç çarpıma göre sıralarsan hangisi öne geçer, neden? Cosine ile sıralarsan ne değişir? Hangi durumda uzun belgenin gerçekten öne geçmesini isterdin?
:::

::: ozet
- Norm bir vektörün büyüklüğünü ölçer; `L1`, `L2` ve `L∞` aynı vektöre farklı sayılar verir ve her zaman `L∞ ≤ L2 ≤ L1` olur.
- `d` boyutta her bileşeni `ε` olan vektörün `L∞` normu `ε`, `L2` normu `ε√d`'dir.
- İç çarpım yönü ve uzunluğu birlikte ölçer; cosine uzunluğu çıkarıp yalnız açıyı bırakır.
- Embedding araması cosine'a göre en yakın komşuları bulur; sıfır vektörün benzerliği tanımsızdır.
:::
