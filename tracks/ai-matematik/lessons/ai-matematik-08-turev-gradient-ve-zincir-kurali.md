---
id: ai-matematik-08
title: "Türev, Gradient ve Zincir Kuralı · Kayıp Hangi Yöne Azalır?"
summary: Gradient'i merkezî farkla sayısal olarak hesapla, iki katmanlı küçük bir ağın gradient'ini zincir kuralıyla elle türet ve ikisini gradient check ile karşılaştır.
---

::: anlat 1. Eğitim bir yokuş aşağı yürüyüştür
Bir modeli eğitmek, kayıp fonksiyonunu küçülten ağırlıkları bulmaktır. Milyarlarca ağırlığın hepsini aynı anda hangi yöne oynatacağını söyleyen şey **gradient**'tir.

- **Türev** $f'(x)$: `x` biraz artınca `f` ne kadar değişir? Tek değişkenli eğim.
- **Kısmi türev** $\dfrac{\partial f}{\partial x_i}$: diğer değişkenler sabitken yalnız $x_i$'ye göre eğim.
- **Gradient** $\nabla f = \left(\dfrac{\partial f}{\partial x_1}, \dots, \dfrac{\partial f}{\partial x_n}\right)$: bütün kısmi türevlerin vektörü. Fonksiyonun **en hızlı arttığı** yönü gösterir; eksi gradient en hızlı azaldığı yöndür.

| Soru | Araç | Görev |
|---|---|---|
| Formülünü bilmediğim bir fonksiyonun gradient'i ne? | Sayısal türev (`finite differences`) | 1 |
| İç içe fonksiyonların gradient'i nasıl bulunur? | Zincir kuralı (`chain rule`) | 2 |
| Elle türettiğim gradient doğru mu? | `Gradient check` | 3 |
:::

::: anlat 2. Sayısal türev ve zincir kuralı
**Sayısal türev.** Türevin tanımı bir limittir; küçük bir `h` ile yaklaşık hesaplanır. İki yol vardır:

$$\text{ileri fark: } \frac{f(x + h) - f(x)}{h} \qquad \text{merkezî fark: } \frac{f(x + h) - f(x - h)}{2h}$$

İleri farkın hatası `h` ile, merkezî farkın hatası `h²` ile küçülür; merkezî fark aynı `h` için çok daha doğrudur. `h`'yi çok küçük seçmek de işe yaramaz: iki neredeyse eşit sayının farkı kayan nokta hatasında boğulur. Pratikte $h \approx 10^{-5}$ iyi bir seçimdir.

Sayısal gradient `n` değişken için `2n` fonksiyon çağrısı ister. Bir milyar ağırlık için bu imkânsızdır; bu yüzden eğitimde kullanılmaz, yalnız **denetim** için kullanılır.

**Zincir kuralı.** Bir sinir ağı iç içe fonksiyonlardır: $L = \ell(g(h(x)))$. Zincir kuralı, bileşkenin türevinin parçaların türevlerinin çarpımı olduğunu söyler:

$$\frac{dL}{dx} = \frac{dL}{dg} \cdot \frac{dg}{dh} \cdot \frac{dh}{dx}$$

`Backpropagation` bu çarpımı **sondan başa** doğru hesaplamaktır: önce kaybın çıktıya göre türevi, sonra bir önceki katmana, sonra ondan öncekine. Her adımda bir önceki adımın sonucu yeniden kullanılır; bu yüzden bütün ağırlıkların gradient'i tek bir geri geçişte, yaklaşık bir ileri geçiş maliyetine bulunur.

Bu derste tek bir örnek ağ kullanacaksın: $\hat{y} = w_2 \cdot \tanh(w_1 x)$ ve $L = (\hat{y} - y)^2$. Ara değerler $a = w_1 x$ ve $t = \tanh(a)$ olsun:

$$\frac{\partial L}{\partial \hat{y}} = 2(\hat{y} - y) \qquad \frac{\partial L}{\partial w_2} = \frac{\partial L}{\partial \hat{y}} \cdot t \qquad \frac{\partial L}{\partial w_1} = \frac{\partial L}{\partial \hat{y}} \cdot w_2 \cdot (1 - t^2) \cdot x$$

Buradaki $(1 - t^2)$, `tanh`'ın türevidir.
:::

::: tahmin İleri fark mı, merkezî fark mı?
$f(x) = x^3$ fonksiyonunun $x = 2$ noktasındaki türevi tam olarak 12'dir. `h = 0.1` ile iki yöntemin hatası ne yazdırılır?

```python
def f(x):
    return x ** 3

x, h = 2.0, 0.1
ileri = (f(x + h) - f(x)) / h
merkezi = (f(x + h) - f(x - h)) / (2 * h)
print(round(ileri - 12, 4))
print(round(merkezi - 12, 4))
```

???

```cikti
0.61
0.01
```
İleri farkın hatası 0,61, merkezî farkın hatası 0,01: aynı `h` ile 61 kat daha doğru. İleri farkta hata `h` ile orantılıdır ($3xh + h^2 = 0{,}61$), merkezî farkta `h²` ile ($h^2 = 0{,}01$). `h`'yi on kat küçültürsen ileri farkın hatası on kat, merkezî farkınki yüz kat küçülür.
:::

::: gorev 1 · Sayısal gradient (merkezî fark)
`sayisal_gradient(f, x, h)` işlevini yaz.

- `f`: sayı listesi alıp sayı döndüren çağrılabilir. `x`: boş olmayan sayı listesi. `h`: pozitif sayı.
- Her `i` için: `x`'in kopyasında yalnız `i`. bileşeni `+h` ve `-h` oynat; kısmi türev `(f(x⁺) - f(x⁻)) / (2h)`.
- Dönüş: `x` ile aynı uzunlukta `float` listesi; 6 basamağa yuvarlanır.
- `x` değişmemelidir. Bozuk girdi `ValueError`.

KUSURLU başlangıç bütün bileşenleri aynı anda oynatıyor: her bileşen için aynı sayıyı (yönlü türevi) döndürüyor.

```starter
def sayisal_gradient(f, x, h):
    ileri = f([v + h for v in x])
    geri = f([v - h for v in x])
    return [round((ileri - geri) / (2 * h), 6) for _ in x]
```

```solution
def sayisal_gradient(f, x, h):
    if not callable(f):
        raise ValueError('f çağrılabilir olmalı')
    if not isinstance(x, list) or not x or any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in x):
        raise ValueError('x boş olmayan sayı listesi olmalı')
    if isinstance(h, bool) or not isinstance(h, (int, float)) or not h > 0:
        raise ValueError('h pozitif sayı olmalı')
    grad = []
    for i in range(len(x)):
        arti = list(x)
        eksi = list(x)
        arti[i] += h
        eksi[i] -= h
        grad.append(round((f(arti) - f(eksi)) / (2 * h), 6))
    return grad
```

```test
need('sayisal_gradient')
import math, random

eq(sayisal_gradient(lambda v: v[0] ** 2, [3.0], 1e-4), [6.0], 'x kare nin türevi 2x')
eq(sayisal_gradient(lambda v: v[0] ** 2 + 3 * v[1], [1.0, 5.0], 1e-4), [2.0, 3.0], 'her bileşen ayrı: [2x, 3]')
eq(sayisal_gradient(lambda v: v[0] * v[1], [2.0, 7.0], 1e-4), [7.0, 2.0], 'çarpımın kısmi türevleri yer değiştirir')
eq(sayisal_gradient(lambda v: 4.0, [1.0, 2.0, 3.0], 1e-3), [0.0, 0.0, 0.0], 'sabit fonksiyonun gradient i sıfır')
g = sayisal_gradient(lambda v: math.sin(v[0]) + math.exp(v[1]), [0.5, 0.2], 1e-5)
yakin(g[0], math.cos(0.5), 'sin in türevi cos', tol=1e-5)
yakin(g[1], math.exp(0.2), 'exp in türevi kendisi', tol=1e-5)
rng = random.Random(801)
for _ in range(20):
    n = rng.randint(1, 6)
    c = [round(rng.uniform(-3, 3), 2) for _ in range(n)]
    x = [round(rng.uniform(-2, 2), 2) for _ in range(n)]
    g = sayisal_gradient(lambda v: sum(ci * vi * vi for ci, vi in zip(c, v)), x, 1e-4)
    for gi, ci, xi in zip(g, c, x):
        yakin(gi, 2 * ci * xi, 'rastgele ikinci derece fonksiyonda analitik gradient ile aynı', tol=1e-4)
sayac = [0]
def sayan(v):
    sayac[0] += 1
    return v[0] + v[1] + v[2]
sayisal_gradient(sayan, [1.0, 2.0, 3.0], 1e-3)
eq(sayac[0], 6, 'n bileşen için 2n fonksiyon çağrısı')
x = [1.0, 2.0]
sayisal_gradient(lambda v: v[0] + v[1], x, 1e-3)
eq(x, [1.0, 2.0], 'x değişmez')
f = lambda v: v[0]
for a in ([None, [1.0], 1e-3], [f, None, 1e-3], [f, [], 1e-3], [f, [1, "2"], 1e-3], [f, [True], 1e-3], [f, (1.0,), 1e-3], [f, [1.0], 0], [f, [1.0], -1e-3], [f, [1.0], None], [f, [1.0], True], [f, [1.0], float('nan')]):
    raises(ValueError, sayisal_gradient, *a, msg='bozuk girdi reddedilir')
```

```hint
Her bileşen için iki kopya çıkar; yalnız o bileşeni `+h` ve `-h` yap. Diğer bileşenlere dokunma.
```
:::

::: gorev 2 · Zincir kuralıyla elle backpropagation
`geri_yayilim(w1, w2, x, y)` işlevini yaz. Ağ: $\hat{y} = w_2 \cdot \tanh(w_1 x)$, kayıp: $L = (\hat{y} - y)^2$.

- Dört argüman da sayı.
- İleri geçiş: `a = w1 * x`, `t = tanh(a)`, `tahmin = w2 * t`, `kayip = (tahmin - y) ** 2`.
- Geri geçiş (zincir kuralı): `dL/dtahmin = 2 (tahmin - y)`; `dL/dw2 = dL/dtahmin · t`; `dL/dw1 = dL/dtahmin · w2 · (1 - t²) · x`.
- Dönüş: `{'tahmin': ..., 'kayip': ..., 'dw1': ..., 'dw2': ...}`; 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç `tanh`'ın türevini atlıyor: `dw1` hesabında `(1 - t²)` çarpanı yok. Aktivasyon doygunluğa girdiğinde gradient'in küçülmesi gerekirken küçülmüyor.

```starter
def geri_yayilim(w1, w2, x, y):
    import math
    t = math.tanh(w1 * x)
    tahmin = w2 * t
    d = 2 * (tahmin - y)
    return {'tahmin': round(tahmin, 9), 'kayip': round((tahmin - y) ** 2, 9), 'dw1': round(d * w2 * x, 9), 'dw2': round(d * t, 9)}
```

```solution
def geri_yayilim(w1, w2, x, y):
    import math
    for v in (w1, w2, x, y):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError('argümanlar sayı olmalı')
    t = math.tanh(w1 * x)
    tahmin = w2 * t
    d = 2 * (tahmin - y)
    return {
        'tahmin': round(tahmin, 9),
        'kayip': round((tahmin - y) ** 2, 9),
        'dw1': round(d * w2 * (1 - t * t) * x, 9),
        'dw2': round(d * t, 9),
    }
```

```test
need('geri_yayilim')
import math, random

r = geri_yayilim(0.0, 2.0, 1.0, 1.0)
eq(r, {'tahmin': 0.0, 'kayip': 1.0, 'dw1': -4.0, 'dw2': 0.0}, 'w1 = 0: tanh 0, türevi 1')
r = geri_yayilim(1.0, 1.0, 0.0, 0.0)
eq((r['dw1'], r['dw2'], r['kayip']), (0.0, 0.0, 0.0), 'girdi sıfırsa hiçbir gradient akmaz')
doygun = geri_yayilim(10.0, 1.0, 1.0, 0.0)
ok(abs(doygun['dw1']) < 1e-6, 'tanh doygunken dw1 neredeyse sıfır (vanishing gradient)', got=doygun)
ok(abs(doygun['dw2']) > 1.9, 'aynı noktada dw2 büyük kalır', got=doygun)
def kayip(w1, w2, x, y):
    return (w2 * math.tanh(w1 * x) - y) ** 2
rng = random.Random(802)
for _ in range(30):
    w1, w2, x, y = (round(rng.uniform(-2, 2), 3) for _ in range(4))
    r = geri_yayilim(w1, w2, x, y)
    h = 1e-6
    yakin(r['kayip'], kayip(w1, w2, x, y), 'kayıp', tol=1e-8)
    yakin(r['dw1'], (kayip(w1 + h, w2, x, y) - kayip(w1 - h, w2, x, y)) / (2 * h), 'dw1 sayısal türevle aynı', tol=1e-5)
    yakin(r['dw2'], (kayip(w1, w2 + h, x, y) - kayip(w1, w2 - h, x, y)) / (2 * h), 'dw2 sayısal türevle aynı', tol=1e-5)
    adim = 1e-3
    yeni = kayip(w1 - adim * r['dw1'], w2 - adim * r['dw2'], x, y)
    ok(yeni <= r['kayip'] + 1e-12, 'eksi gradient yönünde küçük bir adım kaybı artırmaz', got=(r['kayip'], yeni))
for a in ([None, 1, 1, 1], [1, "1", 1, 1], [1, 1, True, 1], [1, 1, 1, [1]]):
    raises(ValueError, geri_yayilim, *a, msg='bozuk girdi reddedilir')
```

```hint
Önce ileri geçişteki ara değerleri sakla (`t`, `tahmin`). Geri geçişte sondan başla: `d = 2 * (tahmin - y)`; `dw2 = d * t`; `dw1 = d * w2 * (1 - t*t) * x`.
```
:::

::: gorev 3 · Gradient check
`gradient_denetimi(analitik, sayisal, esik)` işlevini yaz. Elle türettiğin gradient ile sayısal gradient'i karşılaştırır.

- `analitik`, `sayisal`: aynı uzunlukta, boş olmayan sayı listeleri. `esik`: pozitif sayı.
- Her bileşen için göreli hata: $\dfrac{\lvert a - s \rvert}{\max(\lvert a \rvert + \lvert s \rvert,\; 10^{-12})}$.
- Dönüş: `{'en_buyuk_hata': ..., 'en_kotu_indeks': en büyük hatanın ilk indeksi, 'gecti': en_buyuk_hata <= esik}`; hata 9 basamağa yuvarlanır ve `gecti` **yuvarlanmamış** değerle hesaplanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç mutlak farka bakıyor. Gradient'in kendisi çok küçükse büyük bir göreli hata gözden kaçar; çok büyükse zararsız bir fark alarm verir.

```starter
def gradient_denetimi(analitik, sayisal, esik):
    farklar = [abs(a - s) for a, s in zip(analitik, sayisal)]
    en = max(farklar)
    return {'en_buyuk_hata': round(en, 9), 'en_kotu_indeks': farklar.index(en), 'gecti': en <= esik}
```

```solution
def gradient_denetimi(analitik, sayisal, esik):
    def sayilar(v):
        return isinstance(v, list) and v and not any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in v)
    if not sayilar(analitik) or not sayilar(sayisal) or len(analitik) != len(sayisal):
        raise ValueError('aynı uzunlukta, boş olmayan iki sayı listesi gerekli')
    if isinstance(esik, bool) or not isinstance(esik, (int, float)) or not esik > 0:
        raise ValueError('esik pozitif sayı olmalı')
    hatalar = [abs(a - s) / max(abs(a) + abs(s), 1e-12) for a, s in zip(analitik, sayisal)]
    en = max(hatalar)
    return {'en_buyuk_hata': round(en, 9), 'en_kotu_indeks': hatalar.index(en), 'gecti': en <= esik}
```

```test
need('gradient_denetimi')
import random

eq(gradient_denetimi([1.0, 2.0], [1.0, 2.0], 1e-6), {'en_buyuk_hata': 0.0, 'en_kotu_indeks': 0, 'gecti': True}, 'özdeş gradient ler')
r = gradient_denetimi([1e-8, 5.0], [2e-8, 5.0], 1e-4)
eq(r['gecti'], False, 'küçük bileşende iki kat fark: mutlak fark küçük ama göreli hata büyük')
eq(r['en_kotu_indeks'], 0, 'hatalı bileşenin indeksi')
yakin(r['en_buyuk_hata'], 1 / 3, 'göreli hata 1e-8 / 3e-8', tol=1e-8)
r = gradient_denetimi([1e6], [1e6 + 0.5], 1e-4)
eq(r['gecti'], True, 'büyük bileşende 0.5 lik mutlak fark zararsızdır')
eq(gradient_denetimi([0.0, 0.0], [0.0, 0.0], 1e-6)['gecti'], True, 'ikisi de sıfırsa hata sıfır (payda tabanı)')
eq(gradient_denetimi([1.0], [-1.0], 0.5), {'en_buyuk_hata': 1.0, 'en_kotu_indeks': 0, 'gecti': False}, 'işareti ters gradient: göreli hata 1')
eq(gradient_denetimi([1.0, 2.0, 3.0], [1.0, 2.2, 3.3], 1.0)['en_kotu_indeks'], 1, 'eşit göreli hatada ilk indeks')
rng = random.Random(803)
for _ in range(25):
    n = rng.randint(1, 8)
    a = [round(rng.uniform(-5, 5), 4) for _ in range(n)]
    s = [x * (1 + rng.choice([0, 1e-7, 1e-3, -0.2])) for x in a]
    hatalar = []
    for x, z in zip(a, s):
        payda = abs(x) + abs(z)
        hatalar.append(abs(x - z) / (payda if payda > 1e-12 else 1e-12))
    r = gradient_denetimi(a, s, 1e-5)
    yakin(r['en_buyuk_hata'], max(hatalar), 'rastgele gradient lerde en büyük göreli hata', tol=1e-8)
    eq(r['en_kotu_indeks'], hatalar.index(max(hatalar)), 'en kötü indeks')
    eq(r['gecti'], max(hatalar) <= 1e-5, 'eşik kararı')
a, s = [1.0], [2.0]
gradient_denetimi(a, s, 1e-3)
eq((a, s), ([1.0], [2.0]), 'girdiler değişmez')
for x in ([[], [], 1e-3], [[1.0], [1.0, 2.0], 1e-3], [None, [1.0], 1e-3], [[1.0], None, 1e-3], [[1, "2"], [1, 2], 1e-3], [[True], [1], 1e-3], [(1.0,), [1.0], 1e-3], [[1.0], [1.0], 0], [[1.0], [1.0], -1], [[1.0], [1.0], None], [[1.0], [1.0], True], [[1.0], [1.0], float('nan')]):
    raises(ValueError, gradient_denetimi, *x, msg='bozuk girdi reddedilir')
```

```hint
Her bileşen için `abs(a - s) / max(abs(a) + abs(s), 1e-12)`. En büyüğünü ve `list.index` ile ilk indeksini al.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur; her adım bu derste hesapladığın bir sayıya ya da örneğe dayanır.

1. **Çerçeve (15 sn).** "Bir modeli eğitmek, sisli bir dağda en alçak noktayı aramaktır. Her adımda yalnız ayağınızın altındaki eğimi bilirsiniz."
2. **Gradient (30 sn).** "Milyarlarca ağırlığın her biri için 'bunu biraz artırırsam hata ne kadar değişir' sorusunun cevabı. Hepsi birlikte en dik artış yönünü, eksi işaretiyle de en dik iniş yönünü verir."
3. **Zincir (30 sn).** "Model iç içe işlemlerdir. Hatanın ilk katmana ne kadar bağlı olduğunu, sondan başa doğru eğimleri çarparak buluruz. Geri yayılım budur."
4. **Tuzak (25 sn).** "Çarpımdaki bir terim sıfıra yaklaşırsa sinyal başa ulaşmaz: model yanlış yaptığı hâlde ilk katmanlar hiç öğrenmez."
5. **Kapanış (20 sn).** "Gradient yön verir; ne kadar gideceğinizi söylemez. O ayrı bir sanattır."
:::

::: anlat Sınır
Bu ders türevi, gradient'i, sayısal farkı ve zincir kuralını tek bir küçük ağ üzerinde anlatır. Sayısal gradient yalnız denetim içindir: `2n` fonksiyon çağrısı ister ve `h` seçimine duyarlıdır; `h` çok büyükse kesme hatası, çok küçükse yuvarlama hatası baskın olur. Görev 2'deki ağ tek girdi, tek gizli birim ve tek çıktılıdır; gerçek ağlarda aynı kural matrislerle (`Jacobian` çarpımlarıyla) uygulanır ve bunu `autograd` kitaplıkları yapar (bkz. `ai-uretim-01`). Gradient check, türevlenemeyen noktalarda (`ReLU`'nun sıfırı gibi) yanlış alarm verebilir ve `dropout` gibi rastgele katmanlar kapatılmadan anlamsızdır. Gradient yalnız **yerel** eğimi verir: kendisi en hızlı artış yönüdür, en hızlı iniş yönü **eksi gradient**'tir; ama o yönde ne kadar gidileceğini ya da varılan noktanın en iyi nokta olup olmadığını söylemez (bkz. `ai-matematik-09`).

Kaynaklar: [Goodfellow, Bengio ve Courville 2016 - Deep Learning, Bölüm 6.5: Back-Propagation](https://www.deeplearningbook.org/contents/mlp.html), [Rumelhart, Hinton ve Williams 1986 - Learning representations by back-propagating errors](https://doi.org/10.1038/323533a0), [Baydin vd. 2018 - Automatic Differentiation in Machine Learning: a Survey](https://arxiv.org/abs/1502.05767).
:::

::: dusun
Görev 2'de `w1 = 10` iken `dw1` neredeyse sıfır çıktı, ama kayıp sıfır değildi. Model yanlış tahmin yaptığı hâlde `w1` neden güncellenemiyor? Aynı durum yüz katmanlı bir ağda her katmanda tekrarlanırsa ilk katmanların gradient'ine ne olur?
:::

::: ozet
- Gradient, bütün kısmi türevlerin vektörüdür; eksi gradient kaybın en hızlı azaldığı yöndür.
- Merkezî fark `h²` hatasıyla, ileri fark `h` hatasıyla yaklaşır; sayısal gradient `2n` çağrı ister ve yalnız denetimde kullanılır.
- Zincir kuralı bileşkenin türevini parçaların türevlerinin çarpımına çevirir; `backpropagation` bu çarpımı sondan başa hesaplar.
- Aktivasyonun türevi çarpımın bir parçasıdır: doygun `tanh` gradient'i sıfıra yaklaştırır.
- Gradient check göreli hatayla yapılır; mutlak fark küçük ve büyük gradient'lerde yanıltır.
:::
