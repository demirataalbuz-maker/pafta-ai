---
id: ai-uretim-40
title: "Gradient Patlaması ve Sönmesi · Ölçüm ve Çare"
summary: "Katman kazançlarından gradient normunun derinlikle nasıl değiştiğini hesapla, Xavier ve He başlatma ölçeklerini türet ve artık bağlantıların gradient'i neden canlı tuttuğunu sayılarla göster."
track: ai-uretim
order: 40
---

::: anlat 1. Derinliğin bedeli
`Backpropagation` zincir kuralıdır: ilk katmanın gradient'i, sondan başa bütün katmanların yerel türevlerinin **çarpımıdır** (bkz. `ai-matematik-08`). Çarpım acımasızdır. Her katman sinyali ortalama 0,9 ile çarpıyorsa 100 katman sonra $0{,}9^{100} \approx 0{,}00003$ kalır: ilk katmanlar hiç öğrenmez (`vanishing gradient`). 1,1 ile çarpıyorsa $1{,}1^{100} \approx 13.780$ olur: güncellemeler ağırlıkları fırlatır (`exploding gradient`).

Derin ağların onlarca yıl eğitilememesinin sebebi buydu. Bugün yüzlerce katmanlı `Transformer`'ların eğitilebilmesi üç fikre dayanır:

| Fikir | Ne yapar | Görev |
|---|---|---|
| Ölçüm | Katman katman gradient normuna bakmak; sorunun yönünü ve yerini bulmak | 1 |
| Doğru başlatma | Her katmanın kazancını başlangıçta 1'e yakın tutmak | 2 |
| Artık bağlantı (`residual`) | Gradient'e katmanları atlayan bir yol açmak | 3 |

Normalleştirme katmanları (`LayerNorm`, `RMSNorm`) ve gradient kırpma (bkz. `ai-uretim-38`) aynı sorunun diğer çareleridir.

> [!NOT]
> Görevler, her katmanı tek bir **kazanç** sayısıyla özetleyen basit bir modelle çalışır; gerçek bir ağ eğitilmez. Bu model yönü ve büyüklük mertebesini doğru verir; ayrıntılar "Sınır" bölümündedir.
:::

::: anlat 2. Kazanç, başlatma ve artık bağlantı
**Kazanç modeli.** Bir katmanın **kazancı**, içinden geri geçen gradient'in normunu kaçla çarptığıdır. `L` katmanlı düz bir ağda son katmandaki gradient normu `g_L` ise `k`. katmandaki norm, ondan sonraki katmanların kazançlarının çarpımıdır:

$$\lVert g_k \rVert = \lVert g_L \rVert \cdot \prod_{j=k+1}^{L} c_j$$

Bir eğitimde bunu doğrudan ölçersin: her katmanın ağırlık gradient'inin normunu günlüğe yazarsın. Sağlıklı bir ağda normlar katmanlar arasında aynı mertebededir. Girişe doğru düzenli küçülüyorsa sönme, büyüyorsa patlama vardır.

Kazancı iki şey belirler: ağırlıkların büyüklüğü ve aktivasyonun türevi. `sigmoid`'in türevi en çok 0,25'tir; her katman gradient'i en az dört kat küçültür. `tanh` doygun bölgede sıfıra yakın türev verir. `ReLU`'nun türevi 0 ya da 1'dir; nöronların yaklaşık yarısı kapalıdır ve bu, varyansı yarıya indirir.

**Başlatma.** Ağırlıklar rastgele başlatılır; ama ne kadar büyük? Amaç, sinyalin varyansını katmandan katmana **korumaktır**. `fan_in` girdisi olan bir katmanda çıktının varyansı kabaca `fan_in × Var(w) × Var(girdi)`'dir. Korunması için:

- **Xavier / Glorot** (`tanh`, doğrusal): $\mathrm{Var}(w) = \dfrac{2}{\text{fan\_in} + \text{fan\_out}}$. İleri ve geri geçişi birlikte dengeler.
- **He / Kaiming** (`ReLU`): $\mathrm{Var}(w) = \dfrac{2}{\text{fan\_in}}$. `ReLU`'nun yarıya indirdiği varyansı iki katla telafi eder.

Standart sapma varyansın kareköküdür. 4.096 girdili bir katman için He ölçeği yaklaşık 0,022'dir; ağırlıkları 1 standart sapmayla başlatırsan her katman sinyali onlarca kat büyütür.

**Artık bağlantı.** Katman çıktısı $y = x + F(x)$ biçiminde yazılır. Türevi $1 + F'(x)$'tir: içinde her zaman bir **1** vardır. Katmanın kendi kazancı `c` ise blok kazancı $1 + c$ olur ve gradient'in girişe ulaşan bir kısmı hiçbir katmandan geçmez. `F` tamamen sönse bile ($c = 0$) gradient bire bir geçer. Düz ağda sönme çarpımsaldır; artık ağda en kötü durumda gradient **korunur**.

Bunun bedeli vardır: $c > 0$ iken $(1 + c)^L$ büyür. Bu yüzden artık dallar küçük başlatılır (son katmanı sıfırlamak, dalı $1/\sqrt{L}$ ile ölçeklemek) ve normalleştirme ile birlikte kullanılır.
:::

::: tahmin Yüz katman sonra ne kalır?
Her katman gradient'i sabit bir kazançla çarpıyor. Üç farklı kazanç için 50 katman sonra kalan oran ne yazdırılır?

```python
for kazanc in (0.9, 1.0, 1.1):
    print(kazanc, f"{kazanc ** 50:.4g}")
```

???

```cikti
0.9 0.005154
1.0 1
1.1 117.4
```
Kazançlar birbirine çok yakın görünüyor: 0,9, 1,0 ve 1,1. Ama 50 katman sonra gradient ya ikiyüzde birine iniyor ya da yüz katına çıkıyor. Arada yirmi bin katlık fark var. Derin bir ağın eğitilebilmesi için kazancın 1'e **çok** yakın olması gerekir; başlatma ölçeklerinin ve normalleştirmenin bütün amacı budur.
:::

::: gorev 1 · Katman katman gradient normu ve teşhis
`gradient_profili(kazanclar, son_norm, alt_esik, ust_esik)` işlevini yaz.

- `kazanclar`: boş olmayan, negatif olmayan sayılardan oluşan liste; `kazanclar[j]`, `j`. katmanın kazancıdır (katman 0 girişe en yakın).
- `son_norm`: son katmanın **çıkışındaki** gradient normu; pozitif sayı.
- `alt_esik`, `ust_esik`: `0 < alt_esik < 1 < ust_esik` olan sayılar.
- `normlar`: her katmanın **girişindeki** gradient normu; `normlar[j] = son_norm × kazanclar[j] × kazanclar[j+1] × ... × kazanclar[L-1]`.
- `oran`: `normlar[0] / son_norm` (girişe ulaşan pay).
- `teshis`: `oran < alt_esik` ise `'sonme'`, `oran > ust_esik` ise `'patlama'`, değilse `'saglikli'`.
- Dönüş: `{'normlar': [...], 'oran': ..., 'teshis': ...}`; sayılar 9 anlamlı basamağa yuvarlanır (`float(f"{x:.9g}")`).
- Bozuk girdi `ValueError`.

KUSURLU başlangıç kazançları çarpmak yerine ortalamasına bakıyor: ortalaması 1 olan ama çarpımı sıfıra giden bir ağı sağlıklı sayıyor.

```starter
def gradient_profili(kazanclar, son_norm, alt_esik, ust_esik):
    ort = sum(kazanclar) / len(kazanclar)
    teshis = 'sonme' if ort < alt_esik else ('patlama' if ort > ust_esik else 'saglikli')
    return {'normlar': [son_norm * ort for _ in kazanclar], 'oran': ort, 'teshis': teshis}
```

```solution
def gradient_profili(kazanclar, son_norm, alt_esik, ust_esik):
    import math
    def sayi(x):
        return not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x)
    if not isinstance(kazanclar, list) or not kazanclar or any(not sayi(c) or c < 0 for c in kazanclar):
        raise ValueError('kazanclar negatif olmayan sayılardan oluşan boş olmayan liste olmalı')
    if not sayi(son_norm) or not son_norm > 0:
        raise ValueError('son_norm pozitif sayı olmalı')
    if not sayi(alt_esik) or not sayi(ust_esik) or not 0 < alt_esik < 1 < ust_esik:
        raise ValueError('0 < alt_esik < 1 < ust_esik olmalı')
    normlar = [0.0] * len(kazanclar)
    g = float(son_norm)
    for j in range(len(kazanclar) - 1, -1, -1):
        g *= kazanclar[j]
        normlar[j] = g
    oran = normlar[0] / son_norm
    teshis = 'sonme' if oran < alt_esik else ('patlama' if oran > ust_esik else 'saglikli')
    yuv = lambda x: float(f"{x:.9g}")
    return {'normlar': [yuv(x) for x in normlar], 'oran': yuv(oran), 'teshis': teshis}
```

```test
need('gradient_profili')
import math, random

r = gradient_profili([0.5, 0.5, 0.5], 8.0, 0.2, 5.0)
eq(r, {'normlar': [1.0, 2.0, 4.0], 'oran': 0.125, 'teshis': 'sonme'}, 'her katman yarıya indiriyor: girişte sekizde bir')
r = gradient_profili([2.0, 2.0, 2.0], 1.0, 0.2, 5.0)
eq(r, {'normlar': [8.0, 4.0, 2.0], 'oran': 8.0, 'teshis': 'patlama'}, 'her katman iki katına çıkarıyor')
eq(gradient_profili([1.0] * 10, 3.0, 0.2, 5.0)['teshis'], 'saglikli', 'kazanç 1: korunur')
r = gradient_profili([0.1, 1.9] * 5, 1.0, 0.2, 5.0)
eq(r['teshis'], 'sonme', 'ortalama kazanç 1 ama çarpım 0.19 üzeri 5: sönme')
yakin(r['oran'], 0.19 ** 5, 'çarpım, ortalama değil', tol=1e-9)
r = gradient_profili([1.0, 0.0, 1.0], 2.0, 0.2, 5.0)
eq(r['normlar'], [0.0, 0.0, 2.0], 'ölü bir katman kendisinden öncekilerin hepsini keser')
yakin(gradient_profili([0.9] * 50, 1.0, 0.2, 5.0)['oran'], 0.9 ** 50, '50 katman, kazanç 0.9', tol=1e-9)
yakin(gradient_profili([1.1] * 50, 1.0, 0.2, 5.0)['oran'], 1.1 ** 50, '50 katman, kazanç 1.1', tol=1e-4)
rng = random.Random(4001)
for _ in range(25):
    c = [round(rng.uniform(0.3, 1.8), 2) for _ in range(rng.randint(1, 12))]
    s = rng.choice([0.5, 1.0, 4.0])
    r = gradient_profili(c, s, 0.1, 10.0)
    for j in range(len(c)):
        exp = s * math.prod(c[j:])
        ok(abs(r['normlar'][j] - exp) <= 1e-7 * max(1.0, abs(exp)), 'rastgele kazançlarda katman normu', got=(r['normlar'][j], exp))
    oran = math.prod(c)
    eq(r['teshis'], 'sonme' if oran < 0.1 else ('patlama' if oran > 10.0 else 'saglikli'), 'rastgele kazançlarda teşhis')
c = [0.5, 2.0]
gradient_profili(c, 1.0, 0.2, 5.0)
eq(c, [0.5, 2.0], 'girdi değişmez')
for a in ([None, 1.0, 0.2, 5.0], [[], 1.0, 0.2, 5.0], [[-0.5], 1.0, 0.2, 5.0], [[1, "2"], 1.0, 0.2, 5.0], [[True], 1.0, 0.2, 5.0], [[float('nan')], 1.0, 0.2, 5.0], [[float('inf')], 1.0, 0.2, 5.0], [(1.0,), 1.0, 0.2, 5.0], [[1.0], 0, 0.2, 5.0], [[1.0], True, 0.2, 5.0], [[1.0], float('nan'), 0.2, 5.0], [[1.0], float('inf'), 0.2, 5.0], [[1.0], None, 0.2, 5.0], [[1.0], 1.0, 0, 5.0], [[1.0], 1.0, True, 5.0], [[1.0], 1.0, float('nan'), 5.0], [[1.0], 1.0, 1.5, 5.0], [[1.0], 1.0, 0.2, 0.9], [[1.0], 1.0, 0.2, True], [[1.0], 1.0, 0.2, float('inf')], [[1.0], 1.0, 0.2, None]):
    raises(ValueError, gradient_profili, *a, msg='bozuk girdi reddedilir')
```

```hint
Sondan başa yürü: `g = son_norm`; her katmanda `g *= kazanç` ve o katmanın girişine yaz. Teşhis, girişe ulaşan oranın eşiklerle karşılaştırılmasıdır.
```
:::

::: gorev 2 · Başlatma ölçeği (Xavier ve He)
`baslatma_olcegi(fan_in, fan_out, tur)` işlevini yaz.

- `fan_in`, `fan_out`: pozitif `int`. `tur`: `'xavier'` ya da `'he'`.
- `'xavier'`: varyans `2 / (fan_in + fan_out)`. `'he'`: varyans `2 / fan_in`.
- `std`: varyansın karekökü. `sinir`: aynı varyansı veren düzgün dağılımın `[-a, a]` sınırı, `a = std × √3`.
- `katman_kazanci`: bu ölçekle doğrusal bir katmanın beklenen varyans kazancı, `fan_in × varyans`; `'he'` için bu 2'dir (`ReLU` yarıya indirince 1 olur).
- Dönüş: `{'varyans': ..., 'std': ..., 'sinir': ..., 'katman_kazanci': ...}`; 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç ağırlıkları katman boyutundan bağımsız, sabit 1 standart sapmayla başlatıyor: büyük bir katmanda sinyal binlerce kat büyüyor.

```starter
def baslatma_olcegi(fan_in, fan_out, tur):
    return {'varyans': 1.0, 'std': 1.0, 'sinir': round(3 ** 0.5, 9), 'katman_kazanci': float(fan_in)}
```

```solution
def baslatma_olcegi(fan_in, fan_out, tur):
    for x in (fan_in, fan_out):
        if isinstance(x, bool) or not isinstance(x, int) or x < 1:
            raise ValueError('fan_in ve fan_out pozitif int olmalı')
    if tur not in ('xavier', 'he'):
        raise ValueError("tur 'xavier' ya da 'he' olmalı")
    varyans = 2 / (fan_in + fan_out) if tur == 'xavier' else 2 / fan_in
    std = varyans ** 0.5
    return {'varyans': round(varyans, 9), 'std': round(std, 9), 'sinir': round(std * 3 ** 0.5, 9), 'katman_kazanci': round(fan_in * varyans, 9)}
```

```test
need('baslatma_olcegi')
import math, random

r = baslatma_olcegi(100, 100, 'xavier')
eq(r, {'varyans': 0.01, 'std': 0.1, 'sinir': 0.173205081, 'katman_kazanci': 1.0}, 'kare katmanda Xavier: kazanç 1')
r = baslatma_olcegi(100, 100, 'he')
eq((r['varyans'], r['katman_kazanci']), (0.02, 2.0), 'He: varyans iki kat, kazanç 2 (ReLU yarıya indirir)')
yakin(baslatma_olcegi(4096, 4096, 'he')['std'], 0.022097087, '4096 girdili katmanda He ölçeği yaklaşık 0.022', tol=1e-8)
r = baslatma_olcegi(100, 400, 'xavier')
eq(r['varyans'], 0.004, 'genişleyen katman: 2 / 500')
ok(r['katman_kazanci'] < 1.0, 'Xavier ileri ve geri geçiş arasında uzlaşır: ileri kazanç 1 in altında', got=r)
eq(baslatma_olcegi(100, 400, 'he')['varyans'], 0.02, 'He yalnız fan_in e bakar')
rng = random.Random(4002)
for _ in range(25):
    fi, fo, t = rng.randint(1, 5000), rng.randint(1, 5000), rng.choice(['xavier', 'he'])
    r = baslatma_olcegi(fi, fo, t)
    v = 2 / (fi + fo) if t == 'xavier' else 2 / fi
    yakin(r['varyans'], v, 'rastgele boyutta varyans', tol=1e-9)
    yakin(r['std'] ** 2, v, 'std kare = varyans', tol=1e-7)
    yakin(r['sinir'] ** 2 / 3, v, 'düzgün dağılımın varyansı a kare / 3', tol=1e-7)
    yakin(r['katman_kazanci'], fi * v, 'kazanç fan_in çarpı varyans', tol=1e-6)
g = random.Random(5)
r = baslatma_olcegi(200, 200, 'xavier')
x = [g.gauss(0, 1) for _ in range(200)]
y = [sum(g.gauss(0, r['std']) * xi for xi in x) for _ in range(300)]
oran = (sum(v * v for v in y) / len(y)) / (sum(v * v for v in x) / len(x))
ok(0.7 < oran < 1.4, 'örneklenen ağırlıklarla çıktı varyansı girdi varyansına yakın', got=oran)
eq(baslatma_olcegi(1, 1, 'xavier')['varyans'], 1.0, 'fan_in = fan_out = 1 sınırı')
for a in ([0, 10, 'he'], [10, 0, 'he'], [-5, 10, 'he'], [10.0, 10, 'he'], [True, 10, 'he'], [10, True, 'he'], [None, 10, 'he'], [10, 10, 'kaiming'], [10, 10, None], [10, 10, 'HE']):
    raises(ValueError, baslatma_olcegi, *a, msg='bozuk girdi reddedilir')
```

```hint
Önce varyansı türe göre seç. `std = varyans ** 0.5`, `sinir = std * 3 ** 0.5`, `katman_kazanci = fan_in * varyans`.
```
:::

::: gorev 3 · Artık bağlantı gradient'i nasıl korur?
`artik_karsilastir(kazanclar)` işlevini yaz. Aynı katmanları iki mimaride karşılaştırır.

- `kazanclar`: boş olmayan, negatif olmayan sayılardan oluşan liste; her katmanın kendi kazancı `c_j`.
- **Düz ağ:** girişe ulaşan gradient oranı $\prod_j c_j$.
- **Artık ağ:** her blok `x + F(x)` biçimindedir; blok kazancı `1 + c_j`; oran $\prod_j (1 + c_j)$.
- `dogrudan_yol`: artık ağda gradient'in **hiçbir katmandan geçmeden** girişe ulaşan payı; her zaman `1.0`'dır (çarpımın açılımındaki sabit terim).
- `katmanli_pay`: artık ağdaki oranın doğrudan yol dışındaki kısmı, `artik - 1`.
- Dönüş: `{'duz': ..., 'artik': ..., 'dogrudan_yol': 1.0, 'katmanli_pay': ...}`; sayılar 9 anlamlı basamağa yuvarlanır (`float(f"{x:.9g}")`).
- Bozuk girdi `ValueError`.

KUSURLU başlangıç artık ağın oranını düz ağınkine 1 ekleyerek buluyor (`1 + ∏c`): yalnız en uzun ve en kısa yolu sayıyor, aradaki bütün yolları atlıyor.

```starter
def artik_karsilastir(kazanclar):
    duz = 1.0
    for c in kazanclar:
        duz *= c
    return {'duz': duz, 'artik': 1 + duz, 'dogrudan_yol': 1.0, 'katmanli_pay': duz}
```

```solution
def artik_karsilastir(kazanclar):
    import math
    if not isinstance(kazanclar, list) or not kazanclar or any(isinstance(c, bool) or not isinstance(c, (int, float)) or not math.isfinite(c) or c < 0 for c in kazanclar):
        raise ValueError('kazanclar negatif olmayan sayılardan oluşan boş olmayan liste olmalı')
    duz, artik = 1.0, 1.0
    for c in kazanclar:
        duz *= c
        artik *= 1 + c
    yuv = lambda x: float(f"{x:.9g}")
    return {'duz': yuv(duz), 'artik': yuv(artik), 'dogrudan_yol': 1.0, 'katmanli_pay': yuv(artik - 1)}
```

```test
need('artik_karsilastir')
import itertools, math, random

r = artik_karsilastir([0.5, 0.5])
eq(r, {'duz': 0.25, 'artik': 2.25, 'dogrudan_yol': 1.0, 'katmanli_pay': 1.25}, 'iki blok: 1 + 0.5 + 0.5 + 0.25 (dört yol)')
r = artik_karsilastir([0.0, 0.0, 0.0])
eq(r, {'duz': 0.0, 'artik': 1.0, 'dogrudan_yol': 1.0, 'katmanli_pay': 0.0}, 'bütün katmanlar ölü: düz ağda sıfır, artık ağda gradient aynen geçer')
r = artik_karsilastir([0.1] * 50)
ok(r['duz'] < 1e-40, 'düz ağda 50 katmanda gradient yok olur', got=r['duz'])
ok(r['artik'] > 1.0, 'artık ağda en kötü durumda bile korunur', got=r['artik'])
yakin(r['artik'], 1.1 ** 50, 'artık ağ: (1 + c) üzeri L', tol=1e-4)
r = artik_karsilastir([1.0] * 10)
eq((r['duz'], r['artik']), (1.0, 1024.0), 'kazancı 1 olan dallarla artık ağ 2 üzeri L büyür: dallar küçük başlatılmalı')
eq(artik_karsilastir([0.7])['artik'], 1.7, 'tek blok')
rng = random.Random(4003)
for _ in range(20):
    c = [round(rng.uniform(0, 1.5), 2) for _ in range(rng.randint(1, 8))]
    r = artik_karsilastir(c)
    yollar = 0.0
    for secim in itertools.product([0, 1], repeat=len(c)):
        yollar += math.prod(cj for cj, s in zip(c, secim) if s)
    ok(abs(r['artik'] - yollar) <= 1e-7 * max(1.0, yollar), 'artık oran bütün yolların toplamıdır (her blokta atla ya da geç)', got=(r['artik'], yollar))
    ok(abs(r['duz'] - math.prod(c)) <= 1e-7 * max(1.0, math.prod(c)), 'düz oran tek yoldur: bütün katmanlardan geçen', got=r['duz'])
    ok(r['artik'] >= 1.0 and r['artik'] >= r['duz'], 'artık oran hiçbir zaman 1 in ve düz oranın altına inmez')
    yakin(r['katmanli_pay'], r['artik'] - 1, 'katmanlı pay = artık - doğrudan yol', tol=1e-6 * max(1.0, r['artik']))
c = [0.5, 0.5]
artik_karsilastir(c)
eq(c, [0.5, 0.5], 'girdi değişmez')
for kotu in (None, [], [-0.1], [1, "2"], [True], [float('nan')], [float('inf')], (0.5, 0.5), "0.5"):
    raises(ValueError, artik_karsilastir, kotu, msg='bozuk girdi reddedilir')
```

```hint
İki çarpımı aynı döngüde biriktir: `duz *= c` ve `artik *= 1 + c`. Doğrudan yol her zaman 1'dir; katmanlı pay `artik − 1`.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur; her adım bu derste hesapladığın bir sayıya ya da örneğe dayanır.

1. **Soru (15 sn).** "Derin ağlar neden onlarca yıl eğitilemedi?"
2. **Çarpım (30 sn).** Tahmin adımı: katman başına 0,9 ile 1,1 arasındaki fark, 50 katman sonra yirmi bin kata dönüşüyor.
3. **Başlatma (30 sn).** "Ağırlıkları rastgele başlatırken boyları katman genişliğine göre ayarlanır; amaç sinyalin her katmanda aynı büyüklükte kalması."
4. **Kestirme (25 sn).** "Artık bağlantı, sinyale katmanları atlayan bir yol açar. En kötü durumda bile gradient başa ulaşır."
5. **Kapanış (20 sn).** "Yüzlerce katmanlı modeller, bu üç küçük fikir sayesinde eğitilebiliyor."
:::

::: anlat Sınır
Bu ders gradient sönmesini ve patlamasını, her katmanı tek bir kazanç sayısına indiren bir modelle anlatır. Gerçek bir katmanın etkisi bir sayı değil bir `Jacobian` matrisidir; gradient'in büyüklüğü hangi yönde olduğuna göre değişir ve "kazanç" bu matrisin tekil değerlerinin özetidir (bkz. `ai-matematik-04`). Kazançlar sabit de değildir: eğitim boyunca ağırlıklarla ve veriye göre değişir; başlangıçta sağlıklı bir ağ sonradan bozulabilir. Xavier ve He ölçekleri bağımsız, sıfır ortalamalı ağırlıklar ve girdiler varsayar ve yalnız **başlangıç** anını dengeler. Görev 2'deki `katman_kazanci` doğrusal bir katmanın ileri varyans kazancıdır; aktivasyonun etkisini içermez. Artık ağda gradient oranının 1'in altına inmemesi skaler modelin bir özelliğidir; gerçek ağlarda dalların katkıları birbirini götürebilir. Artık bağlantılar sönmeyi çözer ama büyümeyi getirir; `Transformer`'lar bunu normalleştirme katmanlarıyla (`pre-norm`) ve küçük başlatılan dallarla dengeler. Normalleştirme, uyarlamalı optimizer'lar (Adam her ağırlığın adımını kendi gradient büyüklüğüne böler, bkz. `ai-matematik-09`) ve gradient kırpma bu derste yalnız anılır. Tekrarlayan ağlarda aynı matris her zaman adımında yeniden çarpıldığı için sorun çok daha serttir.

Kaynaklar: [Glorot ve Bengio 2010 - Understanding the difficulty of training deep feedforward neural networks](https://proceedings.mlr.press/v9/glorot10a.html), [He vd. 2015 - Delving Deep into Rectifiers](https://arxiv.org/abs/1502.01852), [He vd. 2016 - Deep Residual Learning for Image Recognition](https://arxiv.org/abs/1512.03385), [Veit, Wilber ve Belongie 2016 - Residual Networks Behave Like Ensembles of Relatively Shallow Networks](https://arxiv.org/abs/1605.06431), [Pascanu, Mikolov ve Bengio 2013 - On the difficulty of training recurrent neural networks](https://arxiv.org/abs/1211.5063).
:::

::: dusun
Bir eğitimin günlüğünde katman bazlı gradient normları şöyle: son katman 1,0; ortadaki katmanlar 0,8 civarı; ilk üç katman 0,0003. Sönme bütün ağa yayılmış değil, girişe yakın bir yerde aniden oluyor. Görev 1'deki "ölü katman" testini düşünerek olası iki neden söyle. Hangisi olduğunu ayırt etmek için o katmanların hangi istatistiğine bakardın?
:::

::: ozet
- İlk katmanın gradient'i sonraki bütün katmanların kazançlarının çarpımıdır; 1'den küçük kazanç sönmeye, büyük kazanç patlamaya yol açar.
- Teşhis ortalamayla değil çarpımla konur; katman bazlı gradient normları günlüğe yazılır.
- Xavier (`2 / (fan_in + fan_out)`) ve He (`2 / fan_in`) ölçekleri sinyalin varyansını başlangıçta katmandan katmana korur.
- Artık bağlantı blok kazancını `1 + c` yapar: gradient'in bir kısmı hiçbir katmandan geçmeden girişe ulaşır.
- Artık ağ sönmeyi çözer ama büyümeye açıktır; dallar küçük başlatılır ve normalleştirmeyle birlikte kullanılır.
:::
