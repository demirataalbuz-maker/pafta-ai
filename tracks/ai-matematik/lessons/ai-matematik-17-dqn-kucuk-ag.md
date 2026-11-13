---
id: ai-matematik-17
title: "DQN · Tablonun Yerine Bir Fonksiyon"
summary: Replay buffer'ı, target network ile TD hedeflerini ve doğrusal bir Q fonksiyonunun semi-gradient güncellemesini yaz; fonksiyon yaklaşımının neden genellediğini ve neden kararsızlaşabildiğini ölç.
---

::: anlat 1. Tablo neden yetmez?
`ai-matematik-16`'daki Q tablosu her durum-eylem çifti için bir hücre tutuyordu. Durum bir oyun ekranıysa (milyonlarca piksel birleşimi) ya da bir metin geçmişiyse tablo tutulamaz; üstelik ajan hiç görmediği bir durumla karşılaştığında tabloda karşılığı yoktur.

Çözüm: `Q`'yu bir tablo yerine parametreli bir **fonksiyonla** yaklaştırmak. Durumun özellik vektörü girer, her eylem için bir değer çıkar. Benzer durumlar benzer değer alır; ajan görmediği duruma **geneller**. Fonksiyon bir sinir ağı olduğunda yöntemin adı `Deep Q-Network` (DQN) olur.

Ama fonksiyon yaklaşımı, bootstrapping ve off-policy öğrenme bir araya gelince eğitim kararsızlaşabilir (Sutton ve Barto buna `deadly triad` der). DQN'i çalıştıran iki mühendislik fikri bunu yatıştırır:

| Sorun | Çözüm | Görev |
|---|---|---|
| Ardışık deneyimler birbirine çok benzer; ağ son gördüğüne aşırı uyar | `Experience replay`: deneyimleri sakla, rastgele örnekle | 1 |
| Hedef, güncellenen ağın kendisinden hesaplanır; hedef sürekli kaçar | `Target network`: hedef için donmuş bir kopya | 2 |
| Tablo hücresi yerine ağırlıklar nasıl güncellenir? | `Semi-gradient` TD güncellemesi | 3 |

Bu derste sinir ağı yerine en yalın fonksiyon yaklaşımını kullanacaksın: doğrusal bir model, $Q(s, a) = w_a \cdot s$. Her eylemin kendi ağırlık vektörü vardır. Güncelleme kuralı bir sinir ağındakiyle aynıdır; yalnız gradient'i elle yazmak kolaydır.
:::

::: anlat 2. Replay, target network ve semi-gradient
**Replay buffer.** Ajanın her `(s, a, r, s', bitti)` deneyimi sabit kapasiteli bir belleğe eklenir; bellek dolunca en eski deneyim atılır. Eğitimde bellekten rastgele bir `minibatch` çekilir. İki yararı vardır: örnekler arasındaki zamansal bağı kırar (SGD bağımsız örnek varsayar) ve her deneyim birden çok kez kullanılır.

**Target network.** TD hedefi $y = r + \gamma \max_{a'} Q(s', a')$'dır. `Q` güncellenen ağın kendisiyse, her adım hem tahmini hem hedefi değiştirir: ağ kendi kuyruğunu kovalar. DQN hedefi **ayrı bir ağırlık kopyasıyla** ($w^-$) hesaplar ve bu kopyayı yalnız arada bir (örneğin her 1.000 adımda) günceller:

$$y = \begin{cases} r & \text{bölüm bittiyse} \\ r + \gamma \max_{a'} Q(s', a'; w^-) & \text{değilse} \end{cases}$$

**Semi-gradient güncelleme.** Kayıp, hedef ile tahmin arasındaki kare farktır: $L = \frac{1}{2}(y - Q(s, a; w))^2$. Gradient alınırken hedef `y` **sabit** sayılır (içinde `w` olsa bile); "yarı" gradient denmesinin sebebi budur. Doğrusal modelde $\nabla_{w_a} Q(s, a) = s$ olduğundan:

$$w_a \leftarrow w_a + \alpha\,(y - Q(s, a; w))\, s$$

Bu, Q-learning güncellemesinin aynısıdır; tek fark hatanın tek bir hücreye değil, durumun özellikleriyle orantılı biçimde **bütün ağırlıklara** dağıtılmasıdır. Genellemenin kaynağı budur: bir durumdaki güncelleme, özellikleri paylaşan bütün durumların değerini değiştirir. Kararsızlığın kaynağı da aynıdır: bir durumu düzeltirken başka bir durumu bozabilirsin.

Minibatch'te güncellemeler ortalanır: her eylemin ağırlık vektörü, o eylemi içeren örneklerin katkılarının toplamının batch boyutuna bölünmesiyle güncellenir.
:::

::: tahmin Bir güncelleme komşu durumu da değiştirir
Doğrusal bir Q fonksiyonunda tek bir durum için güncelleme yapılıyor. Güncellenmeyen ama benzer bir durumun değeri ne yazdırılır?

```python
w = [0.0, 0.0]
gorulen = [1.0, 1.0]
benzer = [1.0, 0.8]
ilgisiz = [0.0, 0.0]

hedef, alpha = 10.0, 0.1
tahmin = sum(a * b for a, b in zip(w, gorulen))
w = [wi + alpha * (hedef - tahmin) * si for wi, si in zip(w, gorulen)]

for ad, s in (("görülen", gorulen), ("benzer", benzer), ("ilgisiz", ilgisiz)):
    print(ad, round(sum(a * b for a, b in zip(w, s)), 2))
```

???

```cikti
görülen 2.0
benzer 1.8
ilgisiz 0.0
```
Yalnız `görülen` durum güncellendi, ama `benzer` durumun değeri de 0'dan 1,8'e çıktı: özelliklerini paylaşıyor. `ilgisiz` durumun değeri değişmedi. Tabloda bu olmazdı; her hücre bağımsızdır. Fonksiyon yaklaşımının gücü de riski de budur: ajan görmediği durumu tahmin edebilir, ama bir yerdeki öğrenme başka yerdeki tahmini bozabilir.
:::

::: gorev 1 · Replay buffer
`bellek_ekle(bellek, gecis, kapasite)` ve `bellek_ornekle(bellek, n, tohum)` işlevlerini yaz.

- `bellek`: liste (boş olabilir). `gecis`: herhangi bir değer. `kapasite`: pozitif `int`.
- `bellek_ekle`: `gecis`'i sona ekleyen **yeni** bir liste döndürür; uzunluk `kapasite`'yi aşarsa en baştan (en eski) öğeler atılır. Girdi liste değişmemelidir.
- `bellek_ornekle`: `n` pozitif `int` ve `n <= len(bellek)` olmalıdır. `random.Random(tohum).sample(range(len(bellek)), n)` ile indeks seç ve o indekslerdeki öğeleri aynı sırayla döndür. `tohum` `int`.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç bellek dolunca **yeni** deneyimi atıyor ve örneklemede hep ilk `n` öğeyi veriyor: ajan yalnız en eski deneyimlerinden, hep aynı sırayla öğreniyor.

```starter
def bellek_ekle(bellek, gecis, kapasite):
    if len(bellek) >= kapasite:
        return list(bellek)
    return list(bellek) + [gecis]

def bellek_ornekle(bellek, n, tohum):
    return bellek[:n]
```

```solution
def bellek_ekle(bellek, gecis, kapasite):
    if not isinstance(bellek, list):
        raise ValueError('bellek liste olmalı')
    if isinstance(kapasite, bool) or not isinstance(kapasite, int) or kapasite < 1:
        raise ValueError('kapasite pozitif int olmalı')
    yeni = list(bellek) + [gecis]
    return yeni[-kapasite:]

def bellek_ornekle(bellek, n, tohum):
    import random
    if not isinstance(bellek, list):
        raise ValueError('bellek liste olmalı')
    if isinstance(n, bool) or not isinstance(n, int) or n < 1 or n > len(bellek):
        raise ValueError('n pozitif ve bellek boyutundan büyük olmayan int olmalı')
    if isinstance(tohum, bool) or not isinstance(tohum, int):
        raise ValueError('tohum int olmalı')
    return [bellek[i] for i in random.Random(tohum).sample(range(len(bellek)), n)]
```

```test
need('bellek_ekle')
need('bellek_ornekle')
import random

b = []
for i in range(5):
    b = bellek_ekle(b, i, 3)
eq(b, [2, 3, 4], 'kapasite aşılınca en eski deneyimler atılır')
eq(bellek_ekle([1, 2], 3, 5), [1, 2, 3], 'yer varsa sona eklenir')
eq(bellek_ekle([1, 2, 3], 4, 1), [4], 'kapasite 1: yalnız en yeni')
eski = [1, 2]
yeni = bellek_ekle(eski, 3, 5)
eq(eski, [1, 2], 'girdi liste değişmez')
ok(yeni is not eski, 'yeni bir liste döner')
eq(bellek_ekle([], ('s', 0, 1.0, 's2', False), 10), [('s', 0, 1.0, 's2', False)], 'geçiş herhangi bir değer olabilir')
bellek = list(range(100))
o = bellek_ornekle(bellek, 10, 7)
eq(o, [bellek[i] for i in random.Random(7).sample(range(100), 10)], 'örnekleme bağımsız referansla aynı')
eq(len(set(o)), 10, 'yerine koymadan: yinelenen öğe yok')
ok(o != bellek[:10], 'ilk n öğe değil, rastgele seçim', got=o)
eq(bellek_ornekle(bellek, 10, 7), o, 'aynı tohum aynı örneği verir')
ok(bellek_ornekle(bellek, 10, 8) != o, 'farklı tohum farklı örnek verir')
eq(sorted(bellek_ornekle([5, 6, 7], 3, 0)), [5, 6, 7], 'n = bellek boyutu: hepsi')
sayim = [0] * 20
for t in range(400):
    for x in bellek_ornekle(list(range(20)), 5, t):
        sayim[x] += 1
ok(min(sayim) > 60 and max(sayim) < 140, 'her öğe yaklaşık eşit sıklıkta örneklenir', got=(min(sayim), max(sayim)))
eq(bellek_ornekle([9], 1, 0), [9], 'n = 1 sınırı')
for a in ([None, 1, 3], [(1, 2), 1, 3], [[1], 1, 0], [[1], 1, 1.5], [[1], 1, True]):
    raises(ValueError, bellek_ekle, *a, msg='bozuk girdi reddedilir')
for a in ([None, 1, 0], [(1, 2), 1, 0], [[1, 2], 0, 0], [[1, 2], 3, 0], [[1, 2], 1.0, 0], [[1, 2], True, 0], [[1, 2], 1, 1.5], [[1, 2], 1, None], [[1, 2], 1, True], [[], 1, 0]):
    raises(ValueError, bellek_ornekle, *a, msg='bozuk girdi reddedilir')
```

```hint
Ekleme: `(liste + [gecis])[-kapasite:]` en yeni `kapasite` öğeyi tutar. Örnekleme: `random.Random(tohum).sample(range(len(bellek)), n)` indeks listesini verir.
```
:::

::: gorev 2 · Target network ile TD hedefleri
`td_hedefleri(batch, w_hedef, gamma)` işlevini yaz. Q fonksiyonu doğrusaldır: $Q(s, a) = w_a \cdot s$.

- `batch`: boş olmayan liste; her öğe `(s, a, r, s2, bitti)`. `s` ve `s2` aynı uzunlukta (`d`) sayı listeleri; `a` geçerli bir eylem indeksi (`int`); `r` sayı; `bitti` `bool`.
- `w_hedef`: boş olmayan liste; her öğe bir eylemin `d` uzunluklu ağırlık vektörü (target network).
- `gamma`: `[0, 1]` aralığında sayı.
- Her örnek için hedef: `bitti` ise `r`; değilse `r + gamma · max_a (w_hedef[a] · s2)`.
- Dönüş: hedeflerin listesi; 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç `bitti` bayrağını yok sayıyor: bölüm bittiği hâlde sonraki durumun değerini ekliyor ve hedefi şişiriyor.

```starter
def td_hedefleri(batch, w_hedef, gamma):
    out = []
    for s, a, r, s2, bitti in batch:
        q2 = [sum(x * y for x, y in zip(w, s2)) for w in w_hedef]
        out.append(round(r + gamma * max(q2), 9))
    return out
```

```solution
def td_hedefleri(batch, w_hedef, gamma):
    import math
    def sayi(x):
        return not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x)
    def vektor(v):
        return isinstance(v, list) and v and all(sayi(x) for x in v)
    if not isinstance(w_hedef, list) or not w_hedef or not all(vektor(w) and len(w) == len(w_hedef[0]) for w in w_hedef):
        raise ValueError('w_hedef aynı uzunlukta ağırlık vektörlerinin listesi olmalı')
    d = len(w_hedef[0])
    if not sayi(gamma) or not 0 <= gamma <= 1:
        raise ValueError('gamma [0, 1] aralığında olmalı')
    if not isinstance(batch, list) or not batch:
        raise ValueError('batch boş olmayan liste olmalı')
    out = []
    for g in batch:
        if not isinstance(g, (tuple, list)) or len(g) != 5:
            raise ValueError('geçiş (s, a, r, s2, bitti) olmalı')
        s, a, r, s2, bitti = g
        if not vektor(s) or not vektor(s2) or len(s) != d or len(s2) != d:
            raise ValueError('durumlar d uzunluklu sayı listesi olmalı')
        if isinstance(a, bool) or not isinstance(a, int) or not 0 <= a < len(w_hedef) or not sayi(r) or not isinstance(bitti, bool):
            raise ValueError('eylem, ödül ya da bitti bayrağı geçersiz')
        if bitti:
            out.append(round(float(r), 9))
        else:
            out.append(round(r + gamma * max(sum(x * y for x, y in zip(w, s2)) for w in w_hedef), 9))
    return out
```

```test
need('td_hedefleri')
import random

W = [[1.0, 0.0], [0.0, 2.0]]
batch = [([1.0, 0.0], 0, 1.0, [1.0, 1.0], False), ([0.0, 1.0], 1, 5.0, [3.0, 3.0], True)]
eq(td_hedefleri(batch, W, 0.5), [2.0, 5.0], 'ilk: 1 + 0.5 · max(1, 2); ikinci: bölüm bitti, yalnız ödül')
eq(td_hedefleri(batch, W, 0), [1.0, 5.0], 'gamma 0: yalnız ödül')
eq(td_hedefleri([([1.0], 0, 0.0, [2.0], False)], [[-1.0], [-3.0]], 1), [-2.0], 'bütün değerler negatifse en az kötü olan')
eq(td_hedefleri([([1.0], 0, 2, [2.0], True)], [[9.0]], 1), [2.0], 'int ödül float hedef verir')
rng = random.Random(1701)
for _ in range(25):
    d, k = rng.randint(1, 4), rng.randint(1, 4)
    W = [[round(rng.uniform(-2, 2), 2) for _ in range(d)] for _ in range(k)]
    g = rng.choice([0, 0.5, 0.99, 1])
    B = []
    for _ in range(rng.randint(1, 8)):
        B.append(([round(rng.uniform(-2, 2), 2) for _ in range(d)], rng.randrange(k), round(rng.uniform(-3, 3), 2), [round(rng.uniform(-2, 2), 2) for _ in range(d)], rng.random() < 0.3))
    got = td_hedefleri(B, W, g)
    for y, (s, a, r, s2, bitti) in zip(got, B):
        en = max(sum(W[j][i] * s2[i] for i in range(d)) for j in range(k))
        yakin(y, r if bitti else r + g * en, 'rastgele batch te bağımsız hesapla aynı', tol=1e-8)
iyiB, iyiW = [([1.0], 0, 1.0, [1.0], False)], [[1.0]]
for a in ([None, iyiW, 0.9], [[], iyiW, 0.9], [(iyiB[0],), iyiW, 0.9], [['kotu'], iyiW, 0.9], [[123], iyiW, 0.9], [iyiB, None, 0.9], [iyiB, [], 0.9], [iyiB, ([1.0],), 0.9], [iyiB, [[True]], 0.9], [iyiB, [[float('nan')]], 0.9], [iyiB, [[1.0], [1.0, 2.0]], 0.9], [iyiB, iyiW, 1.5], [iyiB, iyiW, -0.1], [iyiB, iyiW, None], [iyiB, iyiW, True], [iyiB, iyiW, float('nan')], [[([1.0], 0, 1.0, [1.0])], iyiW, 0.9], [[([1.0, 2.0], 0, 1.0, [1.0], False)], iyiW, 0.9], [[([1.0], 0, 1.0, [1.0, 2.0], False)], iyiW, 0.9], [[([1.0], 0, 1.0, (1.0,), False)], iyiW, 0.9], [[([1.0], 1, 1.0, [1.0], False)], iyiW, 0.9], [[([1.0], -1, 1.0, [1.0], False)], iyiW, 0.9], [[([1.0], True, 1.0, [1.0], False)], iyiW, 0.9], [[([1.0], 0.0, 1.0, [1.0], False)], iyiW, 0.9], [[([1.0], 0, "1", [1.0], False)], iyiW, 0.9], [[([1.0], 0, True, [1.0], False)], iyiW, 0.9], [[([1.0], 0, float('inf'), [1.0], False)], iyiW, 0.9], [[([float('nan')], 0, 1.0, [1.0], False)], iyiW, 0.9], [[([1.0], 0, 1.0, [float('nan')], False)], iyiW, 0.9], [[([1.0], 0, 1.0, [1.0], 0)], iyiW, 0.9], [[([True], 0, 1.0, [1.0], False)], iyiW, 0.9]):
    raises(ValueError, td_hedefleri, *a, msg='bozuk girdi reddedilir')
```

```hint
Her örnek için önce `bitti`'ye bak. Değilse her eylem için `w_hedef[a] · s2` hesapla, en büyüğünü al, `gamma` ile çarp ve ödüle ekle.
```
:::

::: gorev 3 · Semi-gradient güncelleme adımı
`q_adimi(w, w_hedef, batch, lr, gamma)` işlevini yaz. Bir minibatch üzerinde tek bir DQN güncellemesi yapar.

- `w`: güncellenen ağırlıklar; `w_hedef`: target network; ikisi de aynı biçimde (eylem sayısı × `d`). `batch`, `gamma`: Görev 2'deki gibi. `lr`: pozitif sayı.
- Her örnek için: hedef `y` Görev 2'deki gibi **`w_hedef` ile** hesaplanır; tahmin `q = w[a] · s`; hata `δ = y − q`.
- `kayip`: `δ²` değerlerinin ortalaması (güncellemeden önce).
- Güncelleme: her örnek, `w[a]`'ya `lr · δ · s / n` ekler (`n` batch boyutu). Bütün hatalar güncellemeden **önceki** `w` ile hesaplanır, sonra toplu uygulanır.
- Dönüş: `{'w': yeni ağırlıklar, 'kayip': ...}`; 9 basamağa yuvarlanır. Girdi ağırlıklar değişmemelidir.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç hedefi `w_hedef` yerine güncellenen `w` ile hesaplıyor (target network yok) ve örnekleri sırayla, her birinden sonra `w`'yu değiştirerek uyguluyor.

```starter
def q_adimi(w, w_hedef, batch, lr, gamma):
    w = [list(x) for x in w]
    kayip = 0.0
    for s, a, r, s2, bitti in batch:
        y = r if bitti else r + gamma * max(sum(x * z for x, z in zip(wa, s2)) for wa in w)
        d = y - sum(x * z for x, z in zip(w[a], s))
        kayip += d * d
        w[a] = [x + lr * d * z for x, z in zip(w[a], s)]
    return {'w': [[round(x, 9) for x in wa] for wa in w], 'kayip': round(kayip / len(batch), 9)}
```

```solution
def q_adimi(w, w_hedef, batch, lr, gamma):
    import math
    def sayi(x):
        return not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x)
    def vektor(v):
        return isinstance(v, list) and v and all(sayi(x) for x in v)
    for W in (w, w_hedef):
        if not isinstance(W, list) or not W or not all(vektor(x) and len(x) == len(W[0]) for x in W):
            raise ValueError('ağırlıklar aynı uzunlukta vektörlerin listesi olmalı')
    if len(w) != len(w_hedef) or len(w[0]) != len(w_hedef[0]):
        raise ValueError('w ve w_hedef aynı biçimde olmalı')
    d, k = len(w[0]), len(w)
    if not sayi(lr) or not lr > 0 or not sayi(gamma) or not 0 <= gamma <= 1:
        raise ValueError('lr pozitif, gamma [0, 1] aralığında olmalı')
    if not isinstance(batch, list) or not batch:
        raise ValueError('batch boş olmayan liste olmalı')
    n = len(batch)
    artis = [[0.0] * d for _ in range(k)]
    kayip = 0.0
    for g in batch:
        if not isinstance(g, (tuple, list)) or len(g) != 5:
            raise ValueError('geçiş (s, a, r, s2, bitti) olmalı')
        s, a, r, s2, bitti = g
        if not vektor(s) or not vektor(s2) or len(s) != d or len(s2) != d:
            raise ValueError('durumlar d uzunluklu sayı listesi olmalı')
        if isinstance(a, bool) or not isinstance(a, int) or not 0 <= a < k or not sayi(r) or not isinstance(bitti, bool):
            raise ValueError('eylem, ödül ya da bitti bayrağı geçersiz')
        y = r if bitti else r + gamma * max(sum(x * z for x, z in zip(wa, s2)) for wa in w_hedef)
        delta = y - sum(x * z for x, z in zip(w[a], s))
        kayip += delta * delta
        for j in range(d):
            artis[a][j] += lr * delta * s[j] / n
    yeni = [[round(w[a][j] + artis[a][j], 9) for j in range(d)] for a in range(k)]
    return {'w': yeni, 'kayip': round(kayip / n, 9)}
```

```test
need('q_adimi')
import copy, random

r = q_adimi([[0.0, 0.0]], [[0.0, 0.0]], [([1.0, 1.0], 0, 10.0, [0.0, 0.0], True)], 0.1, 0.9)
eq(r, {'w': [[1.0, 1.0]], 'kayip': 100.0}, 'tek örnek: w += 0.1 · 10 · s; kayıp güncellemeden önce')
w = [[1.0], [0.0]]
hedef = [[0.0], [0.0]]
r = q_adimi(w, hedef, [([1.0], 1, 0.0, [1.0], False)], 0.5, 1.0)
eq(r['w'], [[1.0], [0.0]], 'hedef target network ten: w_hedef sıfırken sonraki değer 0, hata 0')
r = q_adimi(w, w, [([1.0], 1, 0.0, [1.0], False)], 0.5, 1.0)
eq(r['w'], [[1.0], [0.5]], 'aynı adım, hedef olarak w nun kendisi verilirse farklı sonuç')
r = q_adimi([[0.0]], [[0.0]], [([1.0], 0, 4.0, [0.0], True), ([1.0], 0, 8.0, [0.0], True)], 0.5, 0)
eq(r, {'w': [[3.0]], 'kayip': 40.0}, 'batch: hatalar eski w ile hesaplanır ve ortalanır (0.5 · (4 + 8) / 2)')
r = q_adimi([[0.0], [7.0]], [[0.0], [7.0]], [([1.0], 0, 2.0, [0.0], True)], 1.0, 0)
eq(r['w'], [[2.0], [7.0]], 'seçilmeyen eylemin ağırlıkları değişmez')
eski = [[1.0, 2.0]]
q_adimi(eski, [[0.0, 0.0]], [([1.0, 1.0], 0, 1.0, [1.0, 1.0], False)], 0.1, 0.9)
eq(eski, [[1.0, 2.0]], 'girdi ağırlıklar değişmez')
def _ref(w, wh, B, lr, g):
    d, k, n = len(w[0]), len(w), len(B)
    yeni = copy.deepcopy(w)
    L = 0.0
    for s, a, r, s2, bitti in B:
        y = r
        if not bitti:
            y += g * max(sum(wh[j][i] * s2[i] for i in range(d)) for j in range(k))
        delta = y - sum(w[a][i] * s[i] for i in range(d))
        L += delta ** 2
        for i in range(d):
            yeni[a][i] += lr * delta * s[i] / n
    return yeni, L / n
rng = random.Random(1702)
for _ in range(20):
    d, k = rng.randint(1, 3), rng.randint(1, 3)
    w = [[round(rng.uniform(-2, 2), 2) for _ in range(d)] for _ in range(k)]
    wh = [[round(rng.uniform(-2, 2), 2) for _ in range(d)] for _ in range(k)]
    B = [([round(rng.uniform(-2, 2), 2) for _ in range(d)], rng.randrange(k), round(rng.uniform(-3, 3), 2), [round(rng.uniform(-2, 2), 2) for _ in range(d)], rng.random() < 0.3) for _ in range(rng.randint(1, 6))]
    lr, g = rng.choice([0.01, 0.1, 0.5]), rng.choice([0, 0.9, 1])
    got = q_adimi(w, wh, B, lr, g)
    yeni, L = _ref(w, wh, B, lr, g)
    yakin(got['kayip'], L, 'rastgele batch te kayıp', tol=1e-7)
    for ga, ya in zip(got['w'], yeni):
        for x, y in zip(ga, ya):
            yakin(x, y, 'rastgele batch te ağırlıklar bağımsız referansla aynı', tol=1e-8)
B = [([1.0, 0.5], 0, 3.0, [0.0, 0.0], True)]
w = [[0.0, 0.0]]
kayiplar = []
for _ in range(60):
    s = q_adimi(w, w, B, 0.3, 0.9)
    kayiplar.append(s['kayip'])
    w = s['w']
ok(kayiplar[-1] < 1e-6 < kayiplar[0], 'aynı deneyim tekrarlandıkça kayıp sıfıra iner', got=(kayiplar[0], kayiplar[-1]))
iyiB, iyiW = [([1.0], 0, 1.0, [1.0], False)], [[1.0]]
for a in ([None, iyiW, iyiB, 0.1, 0.9], [[], iyiW, iyiB, 0.1, 0.9], [([1.0],), iyiW, iyiB, 0.1, 0.9], [[[1.0], [1.0, 2.0]], iyiW, iyiB, 0.1, 0.9], [[[float('nan')]], iyiW, iyiB, 0.1, 0.9], [iyiW, None, iyiB, 0.1, 0.9], [iyiW, [[float('inf')]], iyiB, 0.1, 0.9], [iyiW, [[1.0], [2.0]], iyiB, 0.1, 0.9], [iyiW, [[1.0, 2.0]], iyiB, 0.1, 0.9], [iyiW, iyiW, [], 0.1, 0.9], [iyiW, iyiW, None, 0.1, 0.9], [iyiW, iyiW, (iyiB[0],), 0.1, 0.9], [iyiW, iyiW, ['kotu'], 0.1, 0.9], [iyiW, iyiW, [123], 0.1, 0.9], [iyiW, iyiW, [([1.0], 0, 1.0, [1.0])], 0.1, 0.9], [iyiW, iyiW, [([1.0, 2.0], 0, 1.0, [1.0], False)], 0.1, 0.9], [iyiW, iyiW, [([1.0], 0, 1.0, [1.0, 2.0], False)], 0.1, 0.9], [iyiW, iyiW, [([1.0], 0, 1.0, (1.0,), False)], 0.1, 0.9], [iyiW, iyiW, [([float('nan')], 0, 1.0, [1.0], False)], 0.1, 0.9], [iyiW, iyiW, [([1.0], 0, float('nan'), [1.0], False)], 0.1, 0.9], [iyiW, iyiW, [([1.0], True, 1.0, [1.0], False)], 0.1, 0.9], [iyiW, iyiW, [([1.0], -1, 1.0, [1.0], False)], 0.1, 0.9], [iyiW, iyiW, [([1.0], 0.0, 1.0, [1.0], False)], 0.1, 0.9], [iyiW, iyiW, [([1.0], 0, True, [1.0], False)], 0.1, 0.9], [iyiW, iyiW, iyiB, 0, 0.9], [iyiW, iyiW, iyiB, True, 0.9], [iyiW, iyiW, iyiB, float('nan'), 0.9], [iyiW, iyiW, iyiB, float('inf'), 0.9], [iyiW, iyiW, iyiB, None, 0.9], [iyiW, iyiW, iyiB, 0.1, 1.5], [iyiW, iyiW, iyiB, 0.1, -0.1], [iyiW, iyiW, iyiB, 0.1, True], [iyiW, iyiW, iyiB, 0.1, float('nan')], [iyiW, iyiW, [([1.0], 5, 1.0, [1.0], False)], 0.1, 0.9], [iyiW, iyiW, [([1.0], 0, 1.0, [1.0], 1)], 0.1, 0.9], [[[True]], iyiW, iyiB, 0.1, 0.9]):
    raises(ValueError, q_adimi, *a, msg='bozuk girdi reddedilir')
```

```hint
İki geçiş yap: önce bütün örnekler için `δ`'yı **eski** `w` ile hesapla ve artışları ayrı bir matriste topla; sonra hepsini birden `w`'ya ekle. Hedefte `w_hedef` kullan.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur; her adım bu derste hesapladığın bir sayıya ya da örneğe dayanır.

1. **Çerçeve (15 sn).** "Tablo yetmeyince değerleri bir fonksiyonla tahmin ederiz; o fonksiyon bir sinir ağı olunca adı DQN olur."
2. **Genelleme (30 sn).** Tahmin adımı: yalnız bir durum güncellendi, benzer durumun değeri de 0'dan 1,8'e çıktı. "Görmediği durumu tahmin edebiliyor."
3. **Risk (30 sn).** "Aynı özellik, bir yerdeki öğrenmenin başka yerdeki tahmini bozmasına da yol açar. Eğitim kararsızlaşabilir."
4. **Hileler (25 sn).** "İki mühendislik hilesi: deneyimleri saklayıp karıştırarak öğrenmek ve hedefi donmuş bir kopyayla hesaplamak."
5. **Kapanış (20 sn).** "Atari oyunlarında insanı geçen sistem bu fikirlere dayandı; garantisi değil, pratiği vardı."
:::

::: anlat Sınır
Bu ders DQN'in üç parçasını doğrusal bir Q fonksiyonuyla anlatır. Gerçek DQN'de fonksiyon derin bir sinir ağıdır ve gradient `backpropagation` ile hesaplanır; güncelleme kuralı aynıdır ama ağ, doğrusal modelin veremediği özellikleri kendisi öğrenir. Doğrusal modelde bile off-policy semi-gradient yöntemlerin yakınsama garantisi yoktur; `Baird` karşı örneği ağırlıkların sonsuza gidebildiğini gösterir. Target network ve replay buffer bu kararsızlığı pratikte azaltır, ortadan kaldırmaz. Buradaki replay buffer düzgün (uniform) örnekler; `prioritized replay` büyük hatalı deneyimleri daha sık çeker. Hedefteki `max` değerleri sistemli olarak büyütür; `Double DQN` eylemi bir ağla seçip değerini öbürüyle ölçerek bunu azaltır. DQN yalnız ayrık ve az sayıda eylemde çalışır: her eylem için ayrı bir çıktı gerekir. Sürekli eylemlerde ve büyük eylem uzaylarında (bir dil modelinin sözlüğü gibi) politika doğrudan öğrenilir (bkz. `ai-matematik-18`). DQN örnek açısından verimsizdir: özgün çalışmada her oyun için on milyonlarca kare gerekmiştir.

Kaynaklar: [Mnih vd. 2015 - Human-level control through deep reinforcement learning](https://doi.org/10.1038/nature14236), [van Hasselt, Guez ve Silver 2016 - Deep Reinforcement Learning with Double Q-learning](https://arxiv.org/abs/1509.06461), [Schaul vd. 2016 - Prioritized Experience Replay](https://arxiv.org/abs/1511.05952), [Sutton ve Barto 2018 - Reinforcement Learning: An Introduction, Bölüm 11](http://incompleteideas.net/book/the-book-2nd.html).
:::

::: dusun
Görev 3'ün ikinci ve üçüncü testlerinde aynı deneyim, hedef olarak donmuş bir kopya verildiğinde ağırlıkları değiştirmedi, güncellenen ağın kendisi verildiğinde değiştirdi. Target network'ü hiç güncellemezsen ajan ne öğrenir? Her adımda güncellersen ne kaybedersin? Güncelleme sıklığı hangi iki riski dengeler?
:::

::: ozet
- Fonksiyon yaklaşımı tablonun yerine parametreli bir Q fonksiyonu koyar; benzer durumlar değer paylaşır ve ajan geneller.
- Replay buffer deneyimleri saklar ve rastgele örnekler: zamansal bağı kırar, her deneyimi yeniden kullanır.
- Target network hedefi donmuş bir ağırlık kopyasıyla hesaplar; hedef her adımda kaçmaz.
- Semi-gradient güncelleme hedefi sabit sayar: `w_a += lr · (y − Q) · s`; hata özelliklerle orantılı dağılır.
- Fonksiyon yaklaşımı, bootstrapping ve off-policy öğrenme birlikte kararsızdır; DQN'in hileleri bunu azaltır, garanti vermez.
:::
