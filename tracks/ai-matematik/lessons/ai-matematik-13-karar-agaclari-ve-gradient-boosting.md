---
id: ai-matematik-13
title: "Karar Ağaçları ve Gradient Boosting · Zayıf Kurallardan Güçlü Model"
summary: Gini impurity'yi hesapla, tek bir özellik için en iyi eşiği bul ve tek seviyeli ağaçları artıklara art arda uydurarak küçük bir gradient boosting modelini sıfırdan kur.
---

::: anlat 1. Tablo verisinin modeli
Metin ve görüntüde sinir ağları baskındır. Ama veri bir tabloysa (satırlar kayıt, sütunlar özellik: yaş, tutar, bağlantı sayısı, port) en iyi sonucu çoğu zaman hâlâ ağaç tabanlı modeller verir: `random forest`, `XGBoost`, `LightGBM`. Dolandırıcılık tespiti, saldırı tespiti ve risk puanlama gibi alanlarda yaygın olmalarının sebebi budur.

Bir karar ağacı art arda sorular sorar: "tutar 500'den büyük mü?", "saat gece mi?". Her soru veriyi ikiye böler; yapraklarda bir tahmin durur.

| Soru | Araç | Görev |
|---|---|---|
| Bir grup ne kadar karışık? | `Gini impurity` | 1 |
| Hangi eşik grubu en iyi ayırır? | Bilgi kazancı (`gain`) | 2 |
| Zayıf ağaçlar nasıl güçlü modele dönüşür? | `Gradient boosting` | 3 |
:::

::: anlat 2. Gini, bölme ve boosting
**Gini impurity.** Bir gruptaki sınıf oranları $p_1, \dots, p_k$ ise:

$$G = 1 - \sum_k p_k^2$$

Grup tek sınıftan oluşuyorsa `G = 0` (saf). İki sınıf yarı yarıyaysa `G = 0,5` (en karışık). Anlamı: gruptan rastgele iki örnek çekersen farklı sınıftan olma olasılığı.

**En iyi bölme.** Bir eşik veriyi sola (`x <= eşik`) ve sağa (`x > eşik`) ayırır. Bölmenin kalitesi, çocukların örnek sayısıyla ağırlıklı ortalama Gini'sidir; **kazanç**, ebeveynin Gini'sinden bunun çıkarılmasıdır:

$$\text{kazanç} = G_{\text{ebeveyn}} - \left(\frac{n_{\text{sol}}}{n} G_{\text{sol}} + \frac{n_{\text{sağ}}}{n} G_{\text{sağ}}\right)$$

Aday eşikler, sıralı farklı değerlerin ortalarıdır. Ağaç, kazancı en büyük yapan eşiği seçer ve her çocukta aynı işlemi tekrarlar. Durdurulmazsa her yaprakta tek örnek kalana kadar böler: eğitim verisini ezberler (bkz. `ai-matematik-12`).

**Gradient boosting.** Tek bir derin ağaç yerine çok sayıda **sığ** ağaç kullanılır ve her ağaç öncekilerin hatasını düzeltir:

1. İlk tahmin hedefin ortalamasıdır: $F_0 = \bar{y}$.
2. Her turda **artıkları** hesapla: $r_i = y_i - F(x_i)$.
3. Artıklara küçük bir ağaç uydur (burada tek bölmeli bir `stump`).
4. Tahmini güncelle: $F \leftarrow F + \eta \cdot \text{ağaç}$.

Kare hata kaybında artık, kaybın tahmine göre eksi gradient'idir; yani her ağaç bir gradient descent adımıdır, ama ağırlık uzayında değil **fonksiyon** uzayında (bkz. `ai-matematik-09`). $\eta$ öğrenme oranıdır: küçük tutulursa daha çok ağaç gerekir ama model daha iyi geneller.

Regresyon stump'ı eşiği Gini ile değil, kare hata toplamını (`SSE`) en küçük yapacak biçimde seçer; her yaprak kendi tarafındaki artıkların ortalamasını tahmin eder.
:::

::: tahmin Hangi grup daha karışık?
Üç grubun Gini değeri ne yazdırılır?

```python
def gini(etiketler):
    n = len(etiketler)
    return 1 - sum((etiketler.count(s) / n) ** 2 for s in set(etiketler))

print(gini([1, 1, 1, 1]))
print(gini([1, 1, 0, 0]))
print(round(gini([1, 1, 1, 0]), 4))
```

???

```cikti
0.0
0.5
0.375
```
Hepsi aynı sınıftan olan grup saftır: 0. Yarı yarıya grup iki sınıf için olabilecek en karışık durumdur: 0,5. Dörtte üç, dörtte bir grup arada kalır: $1 - (0{,}75^2 + 0{,}25^2) = 0{,}375$. Ağaç, çocuklarının Gini'sini mümkün olduğunca sıfıra yaklaştıran soruyu arar.
:::

::: gorev 1 · Gini impurity
`gini(etiketler)` işlevini yaz.

- `etiketler`: boş olmayan liste; öğeler `str` ya da `int` (`bool` kabul edilmez).
- Dönüş: $1 - \sum p_k^2$, 9 basamağa yuvarlanmış.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç yalnız en sık sınıfın oranına bakıyor (`1 - en büyük p`). İki sınıfta sıralamayı korur ama üç ve daha çok sınıfta kalan sınıfların dağılımını göremez.

```starter
def gini(etiketler):
    n = len(etiketler)
    return round(1 - max(etiketler.count(s) for s in set(etiketler)) / n, 9)
```

```solution
def gini(etiketler):
    if not isinstance(etiketler, list) or not etiketler:
        raise ValueError('etiketler boş olmayan liste olmalı')
    say = {}
    for e in etiketler:
        if isinstance(e, bool) or not isinstance(e, (str, int)):
            raise ValueError('etiket str ya da int olmalı')
        say[e] = say.get(e, 0) + 1
    n = len(etiketler)
    return round(1 - sum((c / n) ** 2 for c in say.values()), 9)
```

```test
need('gini')
import random

eq(gini([1, 1, 1, 1]), 0.0, 'saf grup')
eq(gini([1, 1, 0, 0]), 0.5, 'yarı yarıya')
eq(gini([1, 1, 1, 0]), 0.375, 'dörtte üç, dörtte bir')
eq(gini(['a']), 0.0, 'tek örnek')
yakin(gini(['a', 'b', 'c']), 2 / 3, 'üç eşit sınıf', tol=1e-9)
ok(gini(['a', 'a', 'b', 'c']) > gini(['a', 'a', 'b', 'b']), 'aynı en sık oran, farklı dağılım: üç sınıflı grup daha karışık')
eq(gini(['a', 'a', 'b', 'c']), 0.625, '1 - (0.25 + 0.0625 + 0.0625)')
rng = random.Random(1301)
for _ in range(25):
    e = [rng.choice(['x', 'y', 'z', 7, 8]) for _ in range(rng.randint(1, 30))]
    n = len(e)
    farkli = sum(1 for i in range(n) for j in range(n) if e[i] != e[j]) / (n * n)
    yakin(gini(e), farkli, 'rastgele iki örneğin farklı sınıftan olma olasılığı', tol=1e-9)
    ok(0.0 <= gini(e) < 1.0, 'Gini 0 ile 1 arasında')
e = ['b', 'a']
gini(e)
eq(e, ['b', 'a'], 'girdi değişmez')
for kotu in (None, [], 'aab', [1.5], [True, False], [None], [['a']], ('a', 'b')):
    raises(ValueError, gini, kotu, msg='bozuk girdi reddedilir')
```

```hint
Her sınıfın sayımını bir sözlükte topla; `1 - Σ (sayım / n)²`.
```
:::

::: gorev 2 · En iyi eşiği bul
`en_iyi_bolme(x, y)` işlevini yaz. Tek bir sayısal özellik için Gini kazancını en büyük yapan eşiği bulur.

- `x`: boş olmayan sayı listesi. `y`: aynı uzunlukta etiket listesi (`str` ya da `int`).
- Aday eşikler: `x`'in sıralı farklı değerlerinden ardışık her çiftin ortalaması.
- Her aday için sol (`x <= eşik`) ve sağ (`x > eşik`) grupların ağırlıklı Gini'sini ve kazancı hesapla.
- Dönüş: `{'esik': ..., 'kazanc': ..., 'sol': sol grubun boyutu, 'sag': sağ grubun boyutu}`. En büyük kazançlı eşik; eşitlikte **küçük** eşik. `esik` ve `kazanc` 9 basamağa yuvarlanır; eşitlik karşılaştırması yuvarlanmış kazançla yapılır.
- `x`'in bütün değerleri aynıysa bölünemez: `{'esik': None, 'kazanc': 0.0, 'sol': n, 'sag': 0}`.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç eşik olarak `x`'in ortalamasını alıyor: verinin nerede ayrıldığına hiç bakmıyor.

```starter
def en_iyi_bolme(x, y):
    esik = sum(x) / len(x)
    sol = sum(1 for a in x if a <= esik)
    return {'esik': round(esik, 9), 'kazanc': 0.0, 'sol': sol, 'sag': len(x) - sol}
```

```solution
def en_iyi_bolme(x, y):
    import math
    if not isinstance(x, list) or not x or any(isinstance(a, bool) or not isinstance(a, (int, float)) or not math.isfinite(a) for a in x):
        raise ValueError('x boş olmayan sayı listesi olmalı')
    if not isinstance(y, list) or len(y) != len(x) or any(isinstance(e, bool) or not isinstance(e, (str, int)) for e in y):
        raise ValueError('y x ile aynı uzunlukta etiket listesi olmalı')

    def g(etiketler):
        say = {}
        for e in etiketler:
            say[e] = say.get(e, 0) + 1
        return 1 - sum((c / len(etiketler)) ** 2 for c in say.values())

    n = len(x)
    degerler = sorted(set(x))
    if len(degerler) < 2:
        return {'esik': None, 'kazanc': 0.0, 'sol': n, 'sag': 0}
    ebeveyn = g(y)
    en = None
    for a, b in zip(degerler, degerler[1:]):
        esik = (a + b) / 2
        sol = [e for v, e in zip(x, y) if v <= esik]
        sag = [e for v, e in zip(x, y) if v > esik]
        kazanc = round(ebeveyn - (len(sol) / n * g(sol) + len(sag) / n * g(sag)), 9)
        if en is None or kazanc > en['kazanc']:
            en = {'esik': round(esik, 9), 'kazanc': kazanc, 'sol': len(sol), 'sag': len(sag)}
    return en
```

```test
need('en_iyi_bolme')
import random

eq(en_iyi_bolme([1, 2, 3, 4], [0, 0, 1, 1]), {'esik': 2.5, 'kazanc': 0.5, 'sol': 2, 'sag': 2}, 'tam ayıran eşik: iki çocuk da saf')
r = en_iyi_bolme([1, 2, 3, 10], [0, 0, 1, 1])
eq(r['esik'], 2.5, 'eşik ortalamada (4) değil, sınıfların ayrıldığı yerde')
eq(en_iyi_bolme([5, 5, 5], ['a', 'b', 'a']), {'esik': None, 'kazanc': 0.0, 'sol': 3, 'sag': 0}, 'tek değerli özellik bölünemez')
eq(en_iyi_bolme([1, 2], ['a', 'a']), {'esik': 1.5, 'kazanc': 0.0, 'sol': 1, 'sag': 1}, 'zaten saf grupta kazanç sıfır')
r = en_iyi_bolme([1, 2, 3, 4], [0, 1, 0, 1])
eq(r['esik'], 1.5, 'eşit kazançta küçük eşik')
r = en_iyi_bolme([3, 1, 4, 2], [1, 0, 1, 0])
eq((r['esik'], r['kazanc']), (2.5, 0.5), 'girdi sırası sonucu değiştirmez')
def _g(e):
    return 1 - sum((e.count(s) / len(e)) ** 2 for s in set(e))
rng = random.Random(1302)
for _ in range(25):
    n = rng.randint(1, 25)
    x = [rng.randint(0, 8) for _ in range(n)]
    y = [rng.choice(['p', 'q', 'r']) for _ in range(n)]
    r = en_iyi_bolme(x, y)
    d = sorted(set(x))
    if len(d) < 2:
        eq(r, {'esik': None, 'kazanc': 0.0, 'sol': n, 'sag': 0}, 'rastgele veride bölünemeyen özellik')
        continue
    en_e, en_k = None, -1.0
    for i in range(len(d) - 1):
        t = (d[i] + d[i + 1]) / 2
        s = [y[j] for j in range(n) if x[j] <= t]
        g = [y[j] for j in range(n) if x[j] > t]
        k = round(_g(y) - (len(s) * _g(s) + len(g) * _g(g)) / n, 9)
        if k > en_k:
            en_e, en_k = t, k
    eq(r['esik'], round(en_e, 9), 'rastgele veride eşik bağımsız aramayla aynı')
    yakin(r['kazanc'], en_k, 'rastgele veride kazanç', tol=1e-9)
    eq(r['sol'] + r['sag'], n, 'sol + sağ = n')
    ok(r['kazanc'] >= -1e-9, 'kazanç negatif olmaz')
x, y = [2, 1], ['a', 'b']
en_iyi_bolme(x, y)
eq((x, y), ([2, 1], ['a', 'b']), 'girdiler değişmez')
for a, b in [(None, [1]), ([], []), ([1, 2], [1]), ([1, "2"], [1, 2]), ([True], [1]), ([1], [True]), ([1], [1.5]), ((1, 2), [1, 2]), ([1, 2], None), ([float('nan'), 1], [0, 1]), ([float('inf'), 1], [0, 1])]:
    raises(ValueError, en_iyi_bolme, a, b, msg='bozuk girdi reddedilir')
```

```hint
`sorted(set(x))` ile farklı değerleri al; ardışık çiftlerin ortalaması aday eşiklerdir. Her aday için iki grubu ayır, ağırlıklı Gini'yi ebeveynden çıkar. Yalnız **kesin büyük** kazançta güncelle; böylece eşitlikte küçük eşik kalır.
```
:::

::: gorev 3 · Stump'larla gradient boosting
`boosting(x, y, tur, lr)` işlevini yaz. Tek özellikli regresyon için gradient boosting kurar.

- `x`, `y`: aynı uzunlukta, boş olmayan sayı listeleri. `tur`: negatif olmayan `int`. `lr`: `(0, 1]` aralığında sayı.
- Başlangıç: her örnek için `F = y`'nin ortalaması.
- Her turda:
  1. Artıklar: `r_i = y_i - F_i`.
  2. Stump: aday eşikler Görev 2'deki gibidir. Her aday için sol ve sağ grupların artık ortalamalarını al; bu ortalamalarla artıkların kare hata toplamını (`SSE`) hesapla. `SSE`'si en küçük eşiği seç; eşitlikte küçük eşik (`1e-12`'den az iyileşme eşitlik sayılır).
  3. `x`'in bütün değerleri aynıysa stump bütün örnekler için artıkların ortalamasını verir.
  4. Güncelle: `F_i ← F_i + lr · stump(x_i)`.
- Dönüş: `{'tahminler': [...], 'hatalar': [...]}`. `hatalar`, başlangıç dahil her turdan sonraki ortalama kare hatadır (`tur + 1` öğe). Sayılar 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç her turda stump'ı artıklara değil, `y`'nin kendisine uyduruyor: her ağaç aynı şeyi öğreniyor ve tahmin hedefi aşıp ıraksıyor.

```starter
def boosting(x, y, tur, lr):
    n = len(y)
    F = [sum(y) / n] * n
    hatalar = [round(sum((b - f) ** 2 for b, f in zip(y, F)) / n, 9)]
    esik = sum(x) / n
    for _ in range(tur):
        sol = [b for a, b in zip(x, y) if a <= esik] or [0.0]
        sag = [b for a, b in zip(x, y) if a > esik] or [0.0]
        F = [f + lr * (sum(sol) / len(sol) if a <= esik else sum(sag) / len(sag)) for a, f in zip(x, F)]
        hatalar.append(round(sum((b - f) ** 2 for b, f in zip(y, F)) / n, 9))
    return {'tahminler': [round(f, 9) for f in F], 'hatalar': hatalar}
```

```solution
def boosting(x, y, tur, lr):
    import math
    for v in (x, y):
        if not isinstance(v, list) or not v or any(isinstance(a, bool) or not isinstance(a, (int, float)) or not math.isfinite(a) for a in v):
            raise ValueError('boş olmayan sayı listesi gerekli')
    if len(x) != len(y):
        raise ValueError('x ve y aynı uzunlukta olmalı')
    if isinstance(tur, bool) or not isinstance(tur, int) or tur < 0:
        raise ValueError('tur negatif olmayan int olmalı')
    if isinstance(lr, bool) or not isinstance(lr, (int, float)) or not 0 < lr <= 1:
        raise ValueError('lr (0, 1] aralığında olmalı')
    n = len(y)
    F = [sum(y) / n] * n
    hatalar = [round(sum((b - f) ** 2 for b, f in zip(y, F)) / n, 9)]
    degerler = sorted(set(x))
    adaylar = [(a + b) / 2 for a, b in zip(degerler, degerler[1:])]
    for _ in range(tur):
        r = [b - f for b, f in zip(y, F)]
        if not adaylar:
            ort = sum(r) / n
            cikti = [ort] * n
        else:
            en = None
            for esik in adaylar:
                sol = [ri for a, ri in zip(x, r) if a <= esik]
                sag = [ri for a, ri in zip(x, r) if a > esik]
                ms, mg = sum(sol) / len(sol), sum(sag) / len(sag)
                sse = sum((ri - ms) ** 2 for ri in sol) + sum((ri - mg) ** 2 for ri in sag)
                if en is None or sse < en[0] - 1e-12:
                    en = (sse, esik, ms, mg)
            cikti = [en[2] if a <= en[1] else en[3] for a in x]
        F = [f + lr * c for f, c in zip(F, cikti)]
        hatalar.append(round(sum((b - f) ** 2 for b, f in zip(y, F)) / n, 9))
    return {'tahminler': [round(f, 9) for f in F], 'hatalar': hatalar}
```

```test
need('boosting')
import random

r = boosting([1, 2, 3, 4], [0, 0, 10, 10], 0, 1.0)
eq(r, {'tahminler': [5.0, 5.0, 5.0, 5.0], 'hatalar': [25.0]}, 'sıfır tur: ortalama')
r = boosting([1, 2, 3, 4], [0, 0, 10, 10], 1, 1.0)
eq(r, {'tahminler': [0.0, 0.0, 10.0, 10.0], 'hatalar': [25.0, 0.0]}, 'basamak işlevi: tek stump ve lr 1 ile tam uyum')
r = boosting([1, 2, 3, 4], [0, 0, 10, 10], 1, 0.5)
eq(r['tahminler'], [2.5, 2.5, 7.5, 7.5], 'lr 0.5: yolun yarısı')
eq(r['hatalar'], [25.0, 6.25], 'artık yarıya, kare hata dörtte bire iner')
r = boosting([1, 2, 3, 4], [1, 2, 3, 4], 30, 0.5)
ok(r['hatalar'][-1] < 0.05 < r['hatalar'][1], 'doğrusal hedef tek stump ile öğrenilemez, çok stump ile yaklaşılır', got=(r['hatalar'][1], r['hatalar'][-1]))
r = boosting([7, 7, 7], [1, 2, 6], 3, 1.0)
eq(r['tahminler'], [3.0, 3.0, 3.0], 'bölünemeyen özellik: tahmin ortalamada kalır')
def _ref(x, y, tur, lr):
    n = len(y)
    F = [sum(y) / n for _ in y]
    hs = [sum((y[i] - F[i]) ** 2 for i in range(n)) / n]
    d = sorted(set(x))
    for _ in range(tur):
        res = [y[i] - F[i] for i in range(n)]
        best = None
        for j in range(len(d) - 1):
            t = (d[j] + d[j + 1]) / 2
            L = [i for i in range(n) if x[i] <= t]
            R = [i for i in range(n) if x[i] > t]
            ml = sum(res[i] for i in L) / len(L)
            mr = sum(res[i] for i in R) / len(R)
            sse = sum((res[i] - ml) ** 2 for i in L) + sum((res[i] - mr) ** 2 for i in R)
            if best is None or sse < best[0] - 1e-12:
                best = (sse, t, ml, mr)
        for i in range(n):
            if best is None:
                F[i] += lr * (sum(res) / n)
            else:
                F[i] += lr * (best[2] if x[i] <= best[1] else best[3])
        hs.append(sum((y[i] - F[i]) ** 2 for i in range(n)) / n)
    return F, hs
rng = random.Random(1303)
for _ in range(15):
    n = rng.randint(1, 14)
    x = [rng.randint(0, 9) for _ in range(n)]
    y = [round(rng.uniform(-5, 5), 2) for _ in range(n)]
    tur, lr = rng.randint(0, 8), rng.choice([0.1, 0.5, 1.0])
    r = boosting(x, y, tur, lr)
    F, hs = _ref(x, y, tur, lr)
    eq(len(r['hatalar']), tur + 1, 'tur + 1 hata değeri')
    for a, b in zip(r['tahminler'], F):
        yakin(a, b, 'rastgele veride tahminler bağımsız referansla aynı', tol=1e-7)
    for a, b in zip(r['hatalar'], hs):
        yakin(a, b, 'rastgele veride hatalar bağımsız referansla aynı', tol=1e-7)
    ok(all(r['hatalar'][i + 1] <= r['hatalar'][i] + 1e-9 for i in range(tur)), 'eğitim hatası turdan tura artmaz')
x, y = [2, 1], [1.0, 3.0]
boosting(x, y, 2, 0.5)
eq((x, y), ([2, 1], [1.0, 3.0]), 'girdiler değişmez')
eq(boosting([1, 2, 3], [0, 10, 0], 1, 1.0)['tahminler'], [0.0, 5.0, 5.0], 'eşit SSE de ilk (küçük) eşik 1.5 seçilir')
for a in ([None, [1], 1, 0.5], [[1], None, 1, 0.5], [[], [], 1, 0.5], [[1, 2], [1], 1, 0.5], [[1, "2"], [1, 2], 1, 0.5], [[True], [1], 1, 0.5], [[1], [1], -1, 0.5], [[1], [1], 1.0, 0.5], [[1], [1], True, 0.5], [[1], [1], 1, 0], [[1], [1], 1, 1.5], [[1], [1], 1, None], [[1], [1], 1, True], [[1], [1], 1, float('nan')], [(1,), [1], 1, 0.5], [[float('nan'), 2], [1, 2], 1, 0.5], [[1, 2], [1, float('inf')], 1, 0.5]):
    raises(ValueError, boosting, *a, msg='bozuk girdi reddedilir')
```

```hint
Her turda stump'ı **artıklara** uydur: `r = y − F`. Yaprak değerleri o taraftaki artıkların ortalamasıdır. Sonra `F += lr · stump`.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur; her adım bu derste hesapladığın bir sayıya ya da örneğe dayanır.

1. **Çerçeve (15 sn).** "Metinde ve resimde sinir ağları kazanır. Ama veri bir Excel tablosuysa çoğu zaman hâlâ ağaçlar kazanır."
2. **Ağaç (30 sn).** "Bir karar ağacı art arda soru sorar: tutar 500'den büyük mü, saat gece mi? Her soru grubu daha saf hâle getirir."
3. **Boosting (30 sn).** "Tek derin ağaç yerine yüzlerce sığ ağaç: her biri öncekilerin hatasını düzeltir. Her ağaç bir gradient adımıdır."
4. **Sınır (25 sn).** "Ağaçlar gördüğü en büyük değerin ötesini tahmin edemez; yeni bir saldırı türü eski kuralların dışında kalabilir."
5. **Kapanış (20 sn).** "Dolandırıcılık ve saldırı tespitinin büyük kısmı bugün hâlâ bu küçük ağaç ormanlarıyla yapılıyor."
:::

::: anlat Sınır
Bu ders Gini impurity'yi, tek özellikte en iyi bölmeyi ve stump'larla gradient boosting'i anlatır. Görevler tek bir sayısal özellikle çalışır; gerçek ağaçlar her düğümde bütün özellikleri dener, kategorik özellikleri ve eksik değerleri ayrıca ele alır. Buradaki eşik araması her aday için veriyi yeniden tarar ($O(n^2)$); gerçek kitaplıklar sıralı tarama ve histogramlarla çok daha hızlıdır. Boosting görevi kare hata kaybı ve tek bölmeli ağaçlar içindir; sınıflandırmada artık yerine log-kaybın gradient'i kullanılır ve `XGBoost` gibi sistemler ikinci türevi, yaprak cezasını ve satır/sütun örneklemesini ekler. Boosting eğitim hatasını her turda düşürür; bu, test hatasının düşeceği anlamına gelmez: tur sayısı ve öğrenme oranı bir doğrulama kümesiyle seçilmelidir (bkz. `ai-matematik-12`). Ağaçlar eğitim aralığının dışına çıkamaz: gördüğü en büyük değerden daha büyüğünü tahmin edemez. Tek bir ağaç yorumlanabilir; yüzlerce ağaçlık bir topluluk değildir.

Kaynaklar: [Friedman 2001 - Greedy Function Approximation: A Gradient Boosting Machine](https://doi.org/10.1214/aos/1013203451), [Breiman vd. 1984 - Classification and Regression Trees](https://doi.org/10.1201/9781315139470), [Chen ve Guestrin 2016 - XGBoost: A Scalable Tree Boosting System](https://arxiv.org/abs/1603.02754), [Grinsztajn vd. 2022 - Why do tree-based models still outperform deep learning on tabular data?](https://arxiv.org/abs/2207.08815).
:::

::: dusun
Görev 3'te doğrusal bir hedefi (`y = x`) 30 stump ile yaklaşık öğrendin. Aynı modele eğitimde hiç görmediği `x = 10` değerini verirsen ne tahmin eder? Doğrusal regresyon aynı soruda ne yapardı? Hangi tür veride bu fark ağaçların aleyhine, hangisinde lehine çalışır?
:::

::: ozet
- Gini impurity `1 − Σ p²`'dir: saf grupta 0, yarı yarıya iki sınıfta 0,5.
- Ağaç, çocukların ağırlıklı Gini'sini en çok düşüren eşiği seçer; aday eşikler ardışık farklı değerlerin ortalarıdır.
- Durdurulmayan ağaç eğitim verisini ezberler; derinlik ve yaprak boyutu sınırlanır.
- Gradient boosting sığ ağaçları artıklara art arda uydurur; kare hatada artık, eksi gradient'tir.
- Öğrenme oranı her ağacın katkısını küçültür; eğitim hatası düşer ama tur sayısı doğrulama verisiyle seçilir.
:::
