---
id: ai-uretim-28
title: "Görüntü ve Video Üretimi 2 (Flux / Sora): Diffusion Transformer (DiT), AdaLN-Zero ve Rectified Flow"
summary: "Flux, Stable Diffusion 3, OpenAI Sora ve Veo modellerinin arkasındaki Diffusion Transformer (DiT) mimarisi, 3D Spacetime Latent Patches, AdaLN-Zero modülasyonu ve düz çizgi yörüngeli Rectified Flow Matching matematiği."
esleme: ai-uretim-26, ai-uretim-15, ai-temel-09
track: ai-uretim
order: 28
duration_minutes: 45
difficulty: ileri
xp: 330
prerequisites: [ai-uretim-27]
tags: [dit, diffusion-transformer, rectified-flow, flow-matching, adaln-zero, sora, flux]
---

::: anlat
## DiT ve flow matching

DiT, diffusion modelinde Transformer tabanlı bir gövde kullanır; flow matching ise örnekler arasındaki dönüşümü bir velocity alanıyla ifade eden bir training yaklaşımıdır. Bu derste adaLN-Zero modülasyonunu ve basitleştirilmiş flow adımını hesaplayacaksın. Bunlar bir video üretim sisteminin tamamını oluşturmaz.

DiT ve flow-matching çalışmaları bu alanın açık araştırma örnekleridir. Belirli ticari video sistemlerinin açıklanmamış mimarileri bu örnek kodlardan çıkarılmaz:
1. **Peebles & Xie (ICCV 2023) — `DiT (Scalable Diffusion Models with Transformers)`:** `U-Net` omurgasını tamamen çöpe atıp yerine saf **`Transformer` + `AdaLN-Zero`** koymak!
2. **Liu et al. / Lipman et al. (ICLR 2023) — `Rectified Flow / Flow Matching`:** Gürültü ile veri arasındaki eğri yolu **cetvelle çizilmiş dümdüz bir doğruya (`Straight-Line Trajectory`)** dönüştürmek!

```
┌────────────────────────────────────────────────────────────────────────────┐
│             MODERN FRONTIER GÖRÜNTÜ/VİDEO MOTORU (FLUX & SORA)             │
├────────────────────────┬─────────────────────────┬─────────────────────────┤
│ 1. 3D SPACETIME        │ 2. DiT & AdaLN-ZERO     │ 3. RECTIFIED FLOW       │
│    LATENT PATCHES      │    (Peebles & Xie)      │    MATCHING (ODE)       │
│ ────────────────────── │ ─────────────────────── │ ─────────────────────── │
│ • 3D VAE videoyu       │ • Zaman (t) ve koşul (c)│ • Eğri DDPM yerine DÜZ  │
│   (T x H x W x C)      │   vektörü bir MLP ile   │   ÇİZGİ interpolasyonu: │
│   gizli uzaya sıkıştırır│   6 modülasyon katsayısı│   x_t = (1-t)*x_0 + t*x1│
│ • (p_t x p_h x p_w)    │   üretir: (gamma, beta, │ • Hedef hız vektörü     │
│   boyutlu 3D küpler    │   alpha).               │   sabittir: v = x_1 - x0│
│   düzleştirilip        │ • Başlangıçta alpha = 0 │ • Yörünge düz olduğu    │
│   Transformer Token    │   olduğu için her DiT   │   için Euler çözücü 4-8 │
│   dizisine çevrilir!   │   bloğu Identity başlar!│   adımda hedefe varır!  │
└────────────────────────┴─────────────────────────┴─────────────────────────┘
```

---

### 1. `Rectified Flow Matching`: Eğri Yolu Cetvelle Düzleştirmek

Matematiksel zarafetin zirvesine hoş geldin!
`Rectified Flow` konvansiyonunda:
- $t = 0$ anında elimizde **Saf Gürültü** $x_0 \sim \mathcal{N}(0, \mathbf{I})$ vardır.
- $t = 1$ anında ulaşmak istediğimiz **Gerçek Veri (Net Resim / Video)** $x_1 \sim p_{\text{data}}$ vardır.

İki nokta arasındaki en kısa ve en düz yol **doğrudan doğru parçasıdır (`Linear Interpolation`)**:

$$x_t = (1 - t) x_0 + t x_1, \qquad t \in [0, 1]$$

Şimdi bu $x_t$ konumunun zamana ($t$'ye) göre türevini alalım — yani parçacığın $x_0$'dan $x_1$'e giderken sahip olduğu **Anlık Hız Vektörü (`Velocity / Drift Vector` $v_t$)**:

$$v_t = \frac{d x_t}{d t} = \frac{d}{dt}\Big( (1 - t) x_0 + t x_1 \Big) = x_1 - x_0$$

Şu güzelliğe bak:
- Karekök yok, $\beta_t$ çizelgesi yok, kümülatif çarpım $\bar{\alpha}_t$ yok!
- Hız vektörü $v = x_1 - x_0$ yol boyunca **zamandan bağımsız ve sabittir**!
- Sinir ağımız $v_\theta(x_t, t, c)$ doğrudan bu hız vektörünü tahmin etmek üzere eğitilir (**`Flow Matching Objective`**):

$$\mathcal{L}_{\text{Flow}}(\theta) = \mathbb{E}_{t \sim U(0,1), \, x_0 \sim \mathcal{N}(0,I), \, x_1 \sim \mathcal{D}} \left[ \Big\| (x_1 - x_0) - v_\theta\big((1-t)x_0 + t x_1, \; t, \; c\big) \Big\|_2^2 \right]$$

#### Çıkarım Anında (`Inference`) `Euler ODE Solver` Adımı
Gürültüden ($t=0, x_0$) başlayıp net resme ($t=1, x_1$) gitmek için `[0, 1]` aralığını $N$ eşit adıma ($\Delta t = \frac{1}{N}$) böleriz ve her adımda basit **İleri Euler (`Forward Euler`)** güncellemesi yaparız:

$$x_{t + \Delta t} = x_t + \Delta t \cdot v_\theta(x_t, t, c)$$

Yörünge düz bir çizgiye çok yakın olduğu için $\Delta t$ büyük seçilse bile ayrıklaştırma hatası (`Discretization Error`) neredeyse sıfırdır; `DDPM`'in 50 adımda yaptığını `Rectified Flow` **4 ila 8 adımda** yapar!

```python
# Tek Boyutta Rectified Flow: x0 (Gürültü) = -2.0 -> x1 (Veri) = +4.0
x0, x1 = -2.0, 4.0
gercek_hiz = x1 - x0  # 4.0 - (-2.0) = +6.0

# t = 0.25 anındaki ara durum:
t = 0.25
x_t = (1.0 - t) * x0 + t * x1  # 0.75*(-2) + 0.25*(4) = -0.5

# N = 4 adımlı (dt = 0.25) Euler ODE çözücü:
x = x0
dt = 1.0 / 4
for adim in range(4):
    x = x + dt * gercek_hiz
print(f"HedefHiz={gercek_hiz} | x(t=0.25)={x_t} | 4AdimSonuEuler={x}")
```

---

### 2. `3D Spacetime Patches` ve `DiT AdaLN-Zero (Adaptive LayerNorm-Zero)`

#### A) Görüntü ve Videoyu Tokenlara Çevirmek (`Patchify`)
**OpenAI Sora** ve **Flux**, ham pikseller üzerinde çalışmaz:
1. Önce bir **`3D Variational Autoencoder (VAE)`** ham videoyu hem zamanda hem uzayda sıkıştırarak $(T \times H \times W \times C)$ boyutlu bir `Latent` tensöre indirger.
2. Bu `Latent` tensör $(p_t \times p_h \times p_w)$ boyutlu küçük 3B uzay-zaman küplerine (**`Spacetime Patches`**) bölünür ve doğrusal bir projeksiyonla $L$ adet $d_{\text{model}}$ boyutlu `Transformer` tokenına dönüştürülür!

#### B) `AdaLN-Zero`: Koşul Bilgisini (`t` ve `c`) Transformer Bloğuna Nasıl Enjekte Ederiz?
Bir `DiT` bloğu her katmanda şu anki gürültü zaman adımını ($t$) ve metin özetini ($c$) bilmek zorundadır. Peebles & Xie farklı yöntemleri (`Cross-Attention`, `In-Context Tokens`, `AdaLN`) karşılaştırdığında, **en düşük FLOPs ile en yüksek görüntü kalitesini (en düşük FID skorunu) açık ara `AdaLN-Zero` mimarisinin verdiğini** kanıtladı!

Standart `LayerNorm` girişi sıfır ortalama ve birim varyansa normalize ettikten sonra sabit öğrenilebilir $\gamma, \beta$ ile çarpar. **`AdaLN-Zero`** ise:
1. Zaman ve koşul vektörünü ($t + c$) bir `SiLU + Linear` katmanından geçirerek her blok için dinamik olarak **ölçek ($\gamma$)**, **kaydırma ($\beta$)** ve **kapı ölçeği ($\alpha$)** vektörlerini üretir.
2. Alt katmana (`Self-Attention` veya `MLP`) girmeden önce normalize edilmiş $x$'i modüle eder:
   $$h_{\text{mod}} = \text{LayerNorm}(x) \odot (1 + \gamma) + \beta$$
3. Alt katmanın çıktısını ($f(h_{\text{mod}})$) kalıntı bağlantısına (`Residual Connection`) eklemeden önce **$\alpha$ kapı vektörüyle (`Gate`)** çarpar:

$$y = x + \alpha \odot f\Big( \text{LayerNorm}(x) \odot (1 + \gamma) + \beta \Big)$$

**Neden Adında `"Zero"` Var?**
$\gamma, \beta, \alpha$ üreten doğrusal katmanın ağırlıkları ve önyargıları **tamamen sıfır (`Zero-Initialized`)** olarak başlatılır! Böylece eğitimin 0. adımında $\gamma = 0, \beta = 0, \alpha = 0$ olur ve $y = x + 0 = x$ (**`Identity Function`**) elde edilir! 60 katmanlı devasa bir `DiT` modeli bile eğitimin ilk adımında gradyan patlaması yaşamadan pürüzsüzce öğrenmeye başlar!

---

### 3. Gerçek PyTorch Üretim Kodu: `DiTBlock` (`AdaLN-Zero`) ve `RectifiedFlowLoss`

Gerçek bir `Flux / DiT` üretim çatısında `AdaLN-Zero` bloğu PyTorch ile şu şekilde yazılır:

```python norun
import torch
import torch.nn as nn

class DiTBlockAdaLNZero(nn.Module):
    def __init__(self, d_model: int = 1152, n_heads: int = 16):
        super().__init__()
        self.norm1 = nn.LayerNorm(d_model, elementwise_affine=False, eps=1e-6)
        self.attn = nn.MultiheadAttention(d_model, n_heads, batch_first=True)
        self.norm2 = nn.LayerNorm(d_model, elementwise_affine=False, eps=1e-6)
        self.mlp = nn.Sequential(
            nn.Linear(d_model, 4 * d_model),
            nn.GELU(approximate="tanh"),
            nn.Linear(4 * d_model, d_model),
        )
        # Koşul vektöründen 6 modülasyon parametresi üreten katman:
        # (gamma_1, beta_1, alpha_1, gamma_2, beta_2, alpha_2)
        self.adaLN_modulation = nn.Sequential(
            nn.SiLU(),
            nn.Linear(d_model, 6 * d_model, bias=True),
        )
        # AdaLN-Zero Sırrı: Son katmanı 0 ile başlat!
        nn.init.zeros_(self.adaLN_modulation[1].weight)
        nn.init.zeros_(self.adaLN_modulation[1].bias)

    def forward(self, x: torch.Tensor, cond: torch.Tensor) -> torch.Tensor:
        # x: (B, L, D), cond: (B, D)
        mods = self.adaLN_modulation(cond).unsqueeze(1).chunk(6, dim=-1)
        gamma1, beta1, alpha1, gamma2, beta2, alpha2 = mods

        # 1. Attention Alt-Bloğu
        h1 = self.norm1(x) * (1.0 + gamma1) + beta1
        attn_out, _ = self.attn(h1, h1, h1, need_weights=False)
        x = x + alpha1 * attn_out

        # 2. MLP Alt-Bloğu
        h2 = self.norm2(x) * (1.0 + gamma2) + beta2
        x = x + alpha2 * self.mlp(h2)
        return x
```

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [DiT makalesi](https://arxiv.org/abs/2212.09748). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: tahmin 3D Spacetime Video Patchification Token Sayısı (OpenAI Sora Mimarisi)
Bir video üretim modelinde 4 saniyelik bir video `3D VAE` tarafından sıkıştırıldıktan sonra `Latent` boyutu $(T=16, H=32, W=32)$ olmuştur. `DiT` modeli bu 3B tensörü $(p_t=2, p_h=2, p_w=2)$ boyutunda 3B uzay-zaman küplerine (`Spacetime Patches`) bölmektedir. `Transformer` dizisine giren toplam uzay-zaman token sayısı kaçtır?

```python
T, H, W = 16, 32, 32
pt, ph, pw = 2, 2, 2

n_t = T // pt
n_h = H // ph
n_w = W // pw
toplam_spacetime_token = n_t * n_h * n_w

print(f"ZamanKupu={n_t} | YukseklikKupu={n_h} | GenislikKupu={n_w} -> ToplamToken={toplam_spacetime_token}")
```

???

```cikti
ZamanKupu=8 | YukseklikKupu=16 | GenislikKupu=16 -> ToplamToken=2048
```
Zaman ekseninde $16 / 2 = 8$, yükseklikte $32 / 2 = 16$ ve genişlikte $32 / 2 = 16$ küp oluşur. Toplam 3B uzay-zaman (`Spacetime`) token sayısı $8 \times 16 \times 16 = 2048$ olur.
:::

::: gorev 1 · Rectified Flow Matching Doğrusal İnterpolasyon, Hedef Hız (Velocity) ve Euler Çözücü
Başlangıç gürültüsü `x0_gurultu` ($t=0$) ve gerçek veri `x1_veri` ($t=1$) için **`Rectified Flow Matching`** hedef hızını ($v^* = x_1 - x_0$), $t = 0.5$ orta noktasındaki doğrusal interpolasyonu ($x_{0.5}$) ve verilen `hiz_tahminleri` üzerinden $N$ adımlı **İleri Euler (`Forward Euler ODE Solver`)** yörüngesini hesaplayan `rectified_flow_euler(x0_gurultu, x1_veri, hiz_tahminleri, adim_sayisi)` işlevini yaz.

**Girdi Kuralları ve Doğrulama:**
- `x0_gurultu` ve `x1_veri`: Aynı uzunlukta ($D \ge 1$), boş olmayan 1B sayı listeleri (`bool` olmayan sonlu sayılar).
- `adim_sayisi` ($N$): `bool` olmayan pozitif tam sayı ($N \ge 1$).
- `hiz_tahminleri`: Boyutu $N \times D$ olan 2B sayı matrisi (her Euler adımı $s \in \{0, \dots, N-1\}$ için modelin tahmin ettiği $D$ boyutlu hız vektörü $\hat{v}_s$).

**Hesaplama Kuralları:**
1. **`hedef_hiz`:** Gerçek düz çizgi hız vektörü $v^*[i] = x_1[i] - x_0[i]$ (`float` listesi).
2. **`orta_nokta_x05`:** $t = 0.5$ anındaki doğrusal interpolasyon $x_{0.5}[i] = 0.5 \cdot x_0[i] + 0.5 \cdot x_1[i]$ (`float` listesi).
3. **`ortalama_flow_kaybi`:** Tüm $N$ adımdaki hız tahminlerinin gerçek `hedef_hiz` ($v^*$) vektörüne olan ortalama karesel hatası (`MSE`):
   $$\mathcal{L}_{\text{Flow}} = \frac{1}{N \cdot D} \sum_{s=0}^{N-1} \sum_{i=0}^{D-1} \left( \hat{v}_{s, i} - v^*_i \right)^2$$
4. **`euler_cikti`:** $x^{(0)} = x_0$ ile başlayıp $\Delta t = \frac{1.0}{N}$ adım boyuyla $N$ adım boyunca:
   $$x^{(s+1)}[i] = x^{(s)}[i] + \Delta t \cdot \hat{v}_{s, i}$$
   uygulandığında $t = 1.0$ sonunda ulaşılan $x^{(N)}$ vektörü (`float` listesi).
5. İşlev şu sözlüğü döndürmelidir:
   `{"hedef_hiz": [...], "orta_nokta_x05": [...], "ortalama_flow_kaybi": float, "euler_cikti": [...]}`
- Geçersiz herhangi bir girdide veya boyut uyuşmazlığında `ValueError` yükseltilmelidir.

```starter
import math

# KUSURLU BAŞLANGIÇ KODU: Hedef hızı ters çıkarıyor ve Euler adımında dt = 1/N ile çarpmıyor!
def rectified_flow_euler(x0_gurultu, x1_veri, hiz_tahminleri, adim_sayisi):
     d = len(x0_gurultu)
     v_hedef = [x0_gurultu[i] - x1_veri[i] for i in range(d)]
     orta = [0.5 * (x0_gurultu[i] + x1_veri[i]) for i in range(d)]
     x = list(x0_gurultu)
     for v_s in hiz_tahminleri:
         x = [x[i] + v_s[i] for i in range(d)]
     return {
         "hedef_hiz": v_hedef,
         "orta_nokta_x05": orta,
         "ortalama_flow_kaybi": 0.0,
         "euler_cikti": x,
     }

x0_orn = [-1.0, 2.0]
x1_orn = [3.0, -2.0]
# Hedef hız = [4.0, -4.0]. 2 adımda kusursuz hız tahmini verilirse Euler tam x1_orn'a ulaşır!
print(rectified_flow_euler(x0_orn, x1_orn, [[4.0, -4.0], [4.0, -4.0]], adim_sayisi=2))
```
```test
def sinama_flow(f):
    import copy, math, random
    def _ref(x0, x1, hizlar, N):
        d = len(x0)
        vh = [float(x1[i]) - float(x0[i]) for i in range(d)]
        orta = [0.5 * float(x0[i]) + 0.5 * float(x1[i]) for i in range(d)]
        mse = sum((float(hizlar[s][i]) - vh[i]) ** 2 for s in range(N) for i in range(d)) / (N * d)
        dt = 1.0 / N
        x = [float(v) for v in x0]
        for s in range(N):
            x = [x[i] + dt * float(hizlar[s][i]) for i in range(d)]
        return {
            "hedef_hiz": vh,
            "orta_nokta_x05": orta,
            "ortalama_flow_kaybi": mse,
            "euler_cikti": x,
        }
    def _yakin(a, b):
        keys = {"hedef_hiz", "orta_nokta_x05", "ortalama_flow_kaybi", "euler_cikti"}
        if not isinstance(a, dict) or set(a.keys()) != keys:
            return False
        if isinstance(a["ortalama_flow_kaybi"], bool) or not isinstance(a["ortalama_flow_kaybi"], float) or abs(a["ortalama_flow_kaybi"] - b["ortalama_flow_kaybi"]) > 1e-10:
            return False
        for k in ("hedef_hiz", "orta_nokta_x05", "euler_cikti"):
            if not isinstance(a[k], list) or len(a[k]) != len(b[k]):
                return False
            if any(abs(u - v) > 1e-10 for u, v in zip(a[k], b[k])):
                return False
        return True
    try:
        x0 = [-1.0, 2.0]
        x1 = [3.0, -2.0]
        hiz = [[4.0, -4.0], [4.0, -4.0]]
        old = (list(x0), list(x1), copy.deepcopy(hiz))
        out = f(x0, x1, hiz, 2)
        if (x0, x1, hiz) != old or not _yakin(out, _ref(x0, x1, hiz, 2)):
            return False
        # Kusursuz hızda euler_cikti == x1 ve kayıp == 0.0 olmalı!
        if abs(out["ortalama_flow_kaybi"]) > 1e-12 or any(abs(u - v) > 1e-12 for u, v in zip(out["euler_cikti"], x1)):
            return False

        rng = random.Random(2801)
        for _ in range(25):
            d = rng.randint(1, 6)
            n = rng.randint(1, 8)
            xx0 = [rng.uniform(-3.0, 3.0) for _ in range(d)]
            xx1 = [rng.uniform(-3.0, 3.0) for _ in range(d)]
            vv = [[rng.uniform(-5.0, 5.0) for _ in range(d)] for _ in range(n)]
            if not _yakin(f(xx0, xx1, vv, n), _ref(xx0, xx1, vv, n)):
                return False

        bad_cases = [
            ([], [], [[]], 1),
            ([], [1.0], [[1.0]], 1),
            ([1.0], [1.0, 2.0], [[1.0]], 1),
            ([1.0], [2.0], [[1.0]], 2),       # len(hiz_tahminleri) != adim_sayisi
            ([1.0], [2.0], [[1.0, 2.0]], 1),  # d boyutu uyuşmuyor
            ([1.0], [2.0], [], 0),
            ([1.0], [2.0], [[1.0]], True),
            ([True], [2.0], [[1.0]], 1),
        ]
        for bx0, bx1, bh, bn in bad_cases:
            try:
                f(bx0, bx1, bh, bn)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

rectified_flow_euler = need("rectified_flow_euler")
ok(sinama_flow(rectified_flow_euler), "Rectified Flow hedef hızı, MSE kaybı ve Euler ODE integrasyonu")
for ad, mut in [
    ("dt=1/N bölmeyen", lambda x0, x1, h, n: dict(rectified_flow_euler(x0, x1, h, n), euler_cikti=[x0[i] + sum(h[s][i] for s in range(n)) for i in range(len(x0))])),
    ("hızı x0-x1 alan", lambda x0, x1, h, n: dict(rectified_flow_euler(x0, x1, h, n), hedef_hiz=[x0[i] - x1[i] for i in range(len(x0))])),
]:
    ok(not sinama_flow(mut), "mutant reddedildi: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef rectified_flow_euler(x0_gurultu, x1_veri, hiz_tahminleri, adim_sayisi):\n    if not isinstance(x0_gurultu, list) or not x0_gurultu or (not all((_sayi_mi(v) for v in x0_gurultu))):\n        raise ValueError('geçersiz x0_gurultu')\n    d = len(x0_gurultu)\n    if not isinstance(x1_veri, list) or len(x1_veri) != d or (not all((_sayi_mi(v) for v in x1_veri))):\n        raise ValueError('geçersiz x1_veri')\n    if isinstance(adim_sayisi, bool) or not isinstance(adim_sayisi, int) or adim_sayisi < 1:\n        raise ValueError('adim_sayisi >= 1 tam sayı olmalı')\n    if not isinstance(hiz_tahminleri, list) or len(hiz_tahminleri) != adim_sayisi:\n        raise ValueError('hiz_tahminleri uzunluğu adim_sayisi ile eşit olmalı')\n    for s in hiz_tahminleri:\n        if not isinstance(s, list) or len(s) != d or (not all((_sayi_mi(v) for v in s))):\n            raise ValueError('geçersiz hız tahmin satırı')\n    hedef_hiz = [float(x1_veri[i]) - float(x0_gurultu[i]) for i in range(d)]\n    orta_nokta = [0.5 * float(x0_gurultu[i]) + 0.5 * float(x1_veri[i]) for i in range(d)]\n    toplam_kare_hata = 0.0\n    dt = 1.0 / adim_sayisi\n    x = [float(v) for v in x0_gurultu]\n    for s in range(adim_sayisi):\n        for i in range(d):\n            v_si = float(hiz_tahminleri[s][i])\n            toplam_kare_hata += (v_si - hedef_hiz[i]) ** 2\n            x[i] += dt * v_si\n    return {'hedef_hiz': hedef_hiz, 'orta_nokta_x05': orta_nokta, 'ortalama_flow_kaybi': toplam_kare_hata / (adim_sayisi * d), 'euler_cikti': x}", 'referans', 'exec'), _REF)
_t, _g = _ff(rectified_flow_euler, _REF['rectified_flow_euler'], ([-1.0, 2.0], [3.0, -2.0], [[4.0, -4.0], [4.0, -4.0]], 2), tohum=3174, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (rectified_flow_euler): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math

def _sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def rectified_flow_euler(x0_gurultu, x1_veri, hiz_tahminleri, adim_sayisi):
    if not isinstance(x0_gurultu, list) or not x0_gurultu or not all(_sayi_mi(v) for v in x0_gurultu):
        raise ValueError("geçersiz x0_gurultu")
    d = len(x0_gurultu)
    if not isinstance(x1_veri, list) or len(x1_veri) != d or not all(_sayi_mi(v) for v in x1_veri):
        raise ValueError("geçersiz x1_veri")
    if isinstance(adim_sayisi, bool) or not isinstance(adim_sayisi, int) or adim_sayisi < 1:
        raise ValueError("adim_sayisi >= 1 tam sayı olmalı")
    if not isinstance(hiz_tahminleri, list) or len(hiz_tahminleri) != adim_sayisi:
        raise ValueError("hiz_tahminleri uzunluğu adim_sayisi ile eşit olmalı")

    for s in hiz_tahminleri:
        if not isinstance(s, list) or len(s) != d or not all(_sayi_mi(v) for v in s):
            raise ValueError("geçersiz hız tahmin satırı")

    hedef_hiz = [float(x1_veri[i]) - float(x0_gurultu[i]) for i in range(d)]
    orta_nokta = [0.5 * float(x0_gurultu[i]) + 0.5 * float(x1_veri[i]) for i in range(d)]

    toplam_kare_hata = 0.0
    dt = 1.0 / adim_sayisi
    x = [float(v) for v in x0_gurultu]

    for s in range(adim_sayisi):
        for i in range(d):
            v_si = float(hiz_tahminleri[s][i])
            toplam_kare_hata += (v_si - hedef_hiz[i]) ** 2
            x[i] += dt * v_si

    return {
        "hedef_hiz": hedef_hiz,
        "orta_nokta_x05": orta_nokta,
        "ortalama_flow_kaybi": toplam_kare_hata / (adim_sayisi * d),
        "euler_cikti": x,
    }

if __name__ == "__main__":
    x0_orn = [-1.0, 2.0]
    x1_orn = [3.0, -2.0]
    print(rectified_flow_euler(x0_orn, x1_orn, [[4.0, -4.0], [4.0, -4.0]], adim_sayisi=2))
```
```hint
`hedef_hiz[i] = x1_veri[i] - x0_gurultu[i]` olarak hesapla. Her adımda `dt = 1.0 / adim_sayisi` ile `x[i] += dt * hiz_tahminleri[s][i]` güncellemesini uygula ve `(v_si - hedef_hiz[i])**2` toplamını `adim_sayisi * d`'ye böl.
```
:::

::: gorev 2 · DiT AdaLN-Zero (Adaptive LayerNorm-Zero) Modülasyonu
Bir **`Diffusion Transformer (DiT)`** bloğunda girdi vektörü `x` üzerinde standart `LayerNorm` ($\epsilon = 10^{-6}$), **`AdaLN` modülasyonu** ($\gamma, \beta$) ve **`Zero-Gate` kalıntı bağlantısını** ($\alpha$) uygulayan `adaln_zero_katmani(x, gamma, beta, alpha, alt_katman_ciktisi)` işlevini yaz.

**Girdi Kuralları ve Doğrulama:**
- `x`, `gamma`, `beta`, `alpha`, `alt_katman_ciktisi`: Aynı uzunlukta ($D \ge 2$), boş olmayan 1B sayı listeleri (`bool` olmayan sonlu sayılar).

**Hesaplama Kuralları:**
1. **`x_norm` (`LayerNorm`):**
   - Ortalama $\mu = \frac{1}{D} \sum_{i=0}^{D-1} x[i]$, varyans $\sigma^2 = \frac{1}{D} \sum_{i=0}^{D-1} (x[i] - \mu)^2$.
   - Her $i$ için $\hat{x}[i] = \frac{x[i] - \mu}{\sqrt{\sigma^2 + 10^{-6}}}$.
2. **`mod_edilmis_girdi` (`AdaLN`):**
   - Her $i$ için $h_{\text{mod}}[i] = \hat{x}[i] \cdot (1.0 + \gamma[i]) + \beta[i]$.
3. **`katman_ciktisi` (`Zero-Initialized Residual Gate`):**
   - Her $i$ için $y[i] = x[i] + \alpha[i] \cdot \text{alt\_katman\_ciktisi}[i]$.
4. **`birim_donusum_mu`:** Eğer tüm $i$ için $|\alpha[i]| < 10^{-12}$ ise (yani `AdaLN-Zero` başlangıç durumunda $y == x$ ise) `True`, değilse `False`.
5. İşlev şu sözlüğü döndürmelidir:
   `{"x_norm": [...], "mod_edilmis_girdi": [...], "katman_ciktisi": [...], "birim_donusum_mu": bool}`
- Geçersiz herhangi bir girdide `ValueError` yükseltilmelidir.

```starter
import math

# KUSURLU BAŞLANGIÇ KODU: (1 + gamma) yerine gamma ile çarpıyor ve alpha kapısını uygulamıyor!
def adaln_zero_katmani(x, gamma, beta, alpha, alt_katman_ciktisi):
     d = len(x)
     mod = [x[i] * gamma[i] + beta[i] for i in range(d)]
     cikti = [x[i] + alt_katman_ciktisi[i] for i in range(d)]
     return {
         "x_norm": list(x),
         "mod_edilmis_girdi": mod,
         "katman_ciktisi": cikti,
         "birim_donusum_mu": False,
     }

# Eğitimin 0. adımında gamma=0, beta=0, alpha=0 olduğunda katman_ciktisi == x olmalı!
print(adaln_zero_katmani([2.0, 4.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [99.0, -50.0]))
```
```test
def sinama_adaln(f):
    import copy, math, random
    def _ref(x, g, b, a, sub):
        d = len(x)
        mu = sum(float(v) for v in x) / d
        var = sum((float(v) - mu) ** 2 for v in x) / d
        std = math.sqrt(var + 1e-6)
        xn = [(float(v) - mu) / std for v in x]
        mod = [xn[i] * (1.0 + float(g[i])) + float(b[i]) for i in range(d)]
        out = [float(x[i]) + float(a[i]) * float(sub[i]) for i in range(d)]
        birim = all(abs(float(v)) < 1e-12 for v in a)
        return {
            "x_norm": xn,
            "mod_edilmis_girdi": mod,
            "katman_ciktisi": out,
            "birim_donusum_mu": birim,
        }
    def _yakin(a, b):
        keys = {"x_norm", "mod_edilmis_girdi", "katman_ciktisi", "birim_donusum_mu"}
        if not isinstance(a, dict) or set(a.keys()) != keys:
            return False
        if type(a["birim_donusum_mu"]) is not bool or a["birim_donusum_mu"] != b["birim_donusum_mu"]:
            return False
        for k in ("x_norm", "mod_edilmis_girdi", "katman_ciktisi"):
            if not isinstance(a[k], list) or len(a[k]) != len(b[k]):
                return False
            if any(abs(u - v) > 1e-10 for u, v in zip(a[k], b[k])):
                return False
        return True
    try:
        # 1) Zero-init durumu: gamma=0, beta=0, alpha=0
        x = [2.0, 4.0]
        z = [0.0, 0.0]
        sub = [99.0, -50.0]
        out0 = f(x, z, z, z, sub)
        if not _yakin(out0, _ref(x, z, z, z, sub)) or out0["birim_donusum_mu"] is not True:
            return False
        if any(abs(u - v) > 1e-12 for u, v in zip(out0["katman_ciktisi"], x)):
            return False

        # 2) Aktif modülasyon durumu
        out1 = f([1.0, 3.0, 5.0], [0.5, -0.2, 0.1], [0.1, 0.2, -0.1], [0.2, 0.5, 1.0], [2.0, 4.0, -1.0])
        if not _yakin(out1, _ref([1.0, 3.0, 5.0], [0.5, -0.2, 0.1], [0.1, 0.2, -0.1], [0.2, 0.5, 1.0], [2.0, 4.0, -1.0])) or out1["birim_donusum_mu"] is not False:
            return False
        out_b1 = f([2.0, 4.0], [0.0, 0.0], [0.0, 0.0], [1e-12, 0.0], [1.0, 1.0])
        out_b2 = f([2.0, 4.0], [0.0, 0.0], [0.0, 0.0], [7e-13, 0.0], [1.0, 1.0])
        if out_b1["birim_donusum_mu"] is not False or out_b2["birim_donusum_mu"] is not True:
            return False

        rng = random.Random(2802)
        for _ in range(25):
            d = rng.randint(2, 8)
            xx = [rng.uniform(-5.0, 5.0) for _ in range(d)]
            gg = [rng.uniform(-1.0, 1.0) for _ in range(d)]
            bb = [rng.uniform(-1.0, 1.0) for _ in range(d)]
            aa = [rng.uniform(-1.0, 1.0) for _ in range(d)]
            ss = [rng.uniform(-3.0, 3.0) for _ in range(d)]
            if not _yakin(f(xx, gg, bb, aa, ss), _ref(xx, gg, bb, aa, ss)):
                return False

        bad_cases = [
            ([1.0], [0.0], [0.0], [0.0], [1.0]),  # D < 2
            ([1.0, 2.0], [0.0], [0.0, 0.0], [0.0, 0.0], [1.0, 1.0]),
            ([1.0, True], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [1.0, 1.0]),
            ([1.0, float("nan")], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [1.0, 1.0]),
        ]
        for bx, bg, bb, ba, bs in bad_cases:
            try:
                f(bx, bg, bb, ba, bs)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

adaln_zero_katmani = need("adaln_zero_katmani")
ok(sinama_adaln(adaln_zero_katmani), "LayerNorm, (1+gamma) AdaLN modülasyonu ve Zero-Gate kalıntı bağlantısı")
for ad, mut in [
    ("1+gamma yerine gamma kullanan", lambda x, g, b, a, s: dict(adaln_zero_katmani(x, g, b, a, s), mod_edilmis_girdi=[adaln_zero_katmani(x, g, b, a, s)["x_norm"][i] * g[i] + b[i] for i in range(len(x))])),
    ("alpha kapısını unutan", lambda x, g, b, a, s: dict(adaln_zero_katmani(x, g, b, a, s), katman_ciktisi=[x[i] + s[i] for i in range(len(x))])),
]:
    ok(not sinama_adaln(mut), "mutant reddedildi: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef adaln_zero_katmani(x, gamma, beta, alpha, alt_katman_ciktisi):\n    if not isinstance(x, list) or len(x) < 2 or (not all((_sayi_mi(v) for v in x))):\n        raise ValueError('x en az 2 elemanlı sayı listesi olmalı')\n    d = len(x)\n    for lst in (gamma, beta, alpha, alt_katman_ciktisi):\n        if not isinstance(lst, list) or len(lst) != d or (not all((_sayi_mi(v) for v in lst))):\n            raise ValueError('tüm vektörler x ile aynı uzunlukta sayı listesi olmalı')\n    mu = sum((float(v) for v in x)) / d\n    var = sum(((float(v) - mu) ** 2 for v in x)) / d\n    std = math.sqrt(var + 1e-06)\n    x_norm = [(float(v) - mu) / std for v in x]\n    mod_girdi = [x_norm[i] * (1.0 + float(gamma[i])) + float(beta[i]) for i in range(d)]\n    cikti = [float(x[i]) + float(alpha[i]) * float(alt_katman_ciktisi[i]) for i in range(d)]\n    birim_mi = all((abs(float(a)) < 1e-12 for a in alpha))\n    return {'x_norm': x_norm, 'mod_edilmis_girdi': mod_girdi, 'katman_ciktisi': cikti, 'birim_donusum_mu': birim_mi}", 'referans', 'exec'), _REF)
_t, _g = _ff(adaln_zero_katmani, _REF['adaln_zero_katmani'], ([2.0, 4.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [99.0, -50.0]), tohum=2951, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (adaln_zero_katmani): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math

def _sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def adaln_zero_katmani(x, gamma, beta, alpha, alt_katman_ciktisi):
    if not isinstance(x, list) or len(x) < 2 or not all(_sayi_mi(v) for v in x):
        raise ValueError("x en az 2 elemanlı sayı listesi olmalı")
    d = len(x)
    for lst in (gamma, beta, alpha, alt_katman_ciktisi):
        if not isinstance(lst, list) or len(lst) != d or not all(_sayi_mi(v) for v in lst):
            raise ValueError("tüm vektörler x ile aynı uzunlukta sayı listesi olmalı")

    mu = sum(float(v) for v in x) / d
    var = sum((float(v) - mu) ** 2 for v in x) / d
    std = math.sqrt(var + 1e-6)

    x_norm = [(float(v) - mu) / std for v in x]
    mod_girdi = [x_norm[i] * (1.0 + float(gamma[i])) + float(beta[i]) for i in range(d)]
    cikti = [float(x[i]) + float(alpha[i]) * float(alt_katman_ciktisi[i]) for i in range(d)]
    birim_mi = all(abs(float(a)) < 1e-12 for a in alpha)

    return {
        "x_norm": x_norm,
        "mod_edilmis_girdi": mod_girdi,
        "katman_ciktisi": cikti,
        "birim_donusum_mu": birim_mi,
    }

if __name__ == "__main__":
    print(adaln_zero_katmani([2.0, 4.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [99.0, -50.0]))
```
```hint
Önce `x` vektörünün ortalaması `mu` ve `std = sqrt(var + 1e-6)` ile `x_norm` listesini bul. Sonra `x_norm[i] * (1.0 + gamma[i]) + beta[i]` ve `x[i] + alpha[i] * alt_katman_ciktisi[i]` hesapla.
```
:::

::: anlat Gerçek deney: Gerçek rakamlarda AdaLN-Zero'lu rectified flow ve adım sayısının bedeli
Final, DiT tarzı AdaLN-Zero bloklarıyla küçük bir hız ağını gerçek el yazısı rakamlarda rectified flow ile eğitir (indirme yok, CPU yeter):

- **Eğitim öncesi:** ağın bir bloğu gerçek bir rakamın gizli durumuyla çalıştırılır. AdaLN-Zero modülasyonu sıfırla başlatıldığı için $\alpha = 0$'dır ve blok **birim dönüşümdür**. Senin `adaln_zero_katmani` işlevin bunu (`birim_donusum_mu`) ve çıktının girdiye eşit olduğunu doğrulamalıdır.
- **Eğitim:** $x_t = (1 - t)\,x_0 + t\,x_1$, hedef hız $x_1 - x_0$. Ağ 4 000 adım eğitilir.
- **Eğitim sonrası:** aynı blok gerçek bir test görüntüsüyle çalıştırılır. Modülasyon artık sıfır değildir; senin işlevinin normalize edilmiş, modüle edilmiş girdisi ve blok çıktısı torch ile karşılaştırılır.
- **Örnekleme:** 100 koşullu örnek 1, 2, 4, 8 ve 32 Euler adımıyla üretilir. Hızlar ağdan gelir, entegrasyon senin `rectified_flow_euler` işlevinle yapılır. Gerçek veride eğitilmiş bir sınıflandırıcı doğruluğu ölçer, sınıf içi çeşitlilik de gerçek test görüntüleriyle karşılaştırılır.

Beklenen ders: sınıflandırıcı doğruluğu tek adımda bile yüksektir, çünkü tek adım rakamın **ortalamasını** üretir. Ortalama tanınır ama bulanıktır ve hep aynıdır. Kalite yalnız "doğru sınıf" ile ölçülürse az adımın bedeli görünmez; çeşitlilik bu bedeli gösterir.

**Ek konu — reflow ile yolları düzleştirmek:** Eğitilmiş ağ 4 000 gürültüyü 32 adımda örneğe taşır; bu (gürültü, örnek) çiftleriyle ağın bir kopyası 3 000 adım daha eğitilir (2-Rectified Flow). Aynı gürültüden tek adım ve 32 adımla üretilen örnekler arasındaki mesafe ve tek adımın çeşitliliği iki ağda karşılaştırılır. Reflow yolları düzleştirir: tek adım 32 adıma çok yaklaşır ve ortalamaya çökmez.

**Güvenlik yönü — etiket zehirleme:** Saldırgan eğitim kümesine "3" etiketli "8" görüntüleri ekler (0, 30 ve 120 adet; 3 sınıfının %0, ~%18 ve ~%47'si). Her küme için aynı ağ baştan eğitilir ve "3" istenerek 100 örnek üretilir; sınıflandırıcı kaçının "8" olduğunu söyler. Koşul (etiket ya da metin açıklaması) ile içerik arasındaki bağ, zehirli örneklerin oranıyla orantılı bozulur. Metin-görüntü modellerinde web'den toplanan açıklamalar aynı saldırıya açıktır.

Kabul: iki işlevin farksal taramayı geçmesi; eğitim öncesi bloğun birim dönüşüm olması; eğitim sonrası modülasyonun ve Euler entegrasyonunun torch ile aynı olması; 4 adımda doğruluğun en az 0.8 olması; tek adımın çeşitliliğinin 32 adımdan düşük olması. Ayrıca reflow tek adım–32 adım mesafesini yarıdan fazla azaltmalı ve tek adımın çeşitliliğini artırmalıdır. Ayrıca temiz kümede "3" istenince "8" üretme oranı en çok 0.05 olmalı ve zehirli örnek sayısıyla artmalıdır.

**Kanıt dosyasını oku:** `egitim_sonrasi_alpha_norm`, `adim_kalite`, `adim_cesitlilik`, `gercek_cesitlilik`. Soru 1: Tek adım neden ortalamaya çöker (ipucu: ağ $E[x_1 - x_0 \mid x_t]$'yi öğrenir)? Soru 2: Reflow yolları düzleştirirse tek adımın çeşitliliğine ne olur? Soru 3: AdaLN-Zero olmasa eğitimin başında ne olurdu?
:::

::: gorev Gerçek deney · Gerçek rakamlarda AdaLN-Zero bloklu rectified flow ve adım sayısına göre kalite/çeşitlilik
Önceki görevlerdeki `rectified_flow_euler`, `adaln_zero_katmani` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 300
```
```starter
import ai_lab
import math

def rectified_flow_euler(x0_gurultu, x1_veri, hiz_tahminleri, adim_sayisi):
    d = len(x0_gurultu)
    v_hedef = [x0_gurultu[i] - x1_veri[i] for i in range(d)]
    orta = [0.5 * (x0_gurultu[i] + x1_veri[i]) for i in range(d)]
    x = list(x0_gurultu)
    for v_s in hiz_tahminleri:
        x = [x[i] + v_s[i] for i in range(d)]
    return {'hedef_hiz': v_hedef, 'orta_nokta_x05': orta, 'ortalama_flow_kaybi': 0.0, 'euler_cikti': x}

import math

def adaln_zero_katmani(x, gamma, beta, alpha, alt_katman_ciktisi):
    d = len(x)
    mod = [x[i] * gamma[i] + beta[i] for i in range(d)]
    cikti = [x[i] + alt_katman_ciktisi[i] for i in range(d)]
    return {'x_norm': list(x), 'mod_edilmis_girdi': mod, 'katman_ciktisi': cikti, 'birim_donusum_mu': False}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_28 as D
    D.goster(rectified_flow_euler, adaln_zero_katmani)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_ag', 'rakam_verisi', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
rectified_flow_euler = need("rectified_flow_euler")
adaln_zero_katmani = need("adaln_zero_katmani")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef rectified_flow_euler(x0_gurultu, x1_veri, hiz_tahminleri, adim_sayisi):\n    if not isinstance(x0_gurultu, list) or not x0_gurultu or (not all((_sayi_mi(v) for v in x0_gurultu))):\n        raise ValueError('geçersiz x0_gurultu')\n    d = len(x0_gurultu)\n    if not isinstance(x1_veri, list) or len(x1_veri) != d or (not all((_sayi_mi(v) for v in x1_veri))):\n        raise ValueError('geçersiz x1_veri')\n    if isinstance(adim_sayisi, bool) or not isinstance(adim_sayisi, int) or adim_sayisi < 1:\n        raise ValueError('adim_sayisi >= 1 tam sayı olmalı')\n    if not isinstance(hiz_tahminleri, list) or len(hiz_tahminleri) != adim_sayisi:\n        raise ValueError('hiz_tahminleri uzunluğu adim_sayisi ile eşit olmalı')\n    for s in hiz_tahminleri:\n        if not isinstance(s, list) or len(s) != d or (not all((_sayi_mi(v) for v in s))):\n            raise ValueError('geçersiz hız tahmin satırı')\n    hedef_hiz = [float(x1_veri[i]) - float(x0_gurultu[i]) for i in range(d)]\n    orta_nokta = [0.5 * float(x0_gurultu[i]) + 0.5 * float(x1_veri[i]) for i in range(d)]\n    toplam_kare_hata = 0.0\n    dt = 1.0 / adim_sayisi\n    x = [float(v) for v in x0_gurultu]\n    for s in range(adim_sayisi):\n        for i in range(d):\n            v_si = float(hiz_tahminleri[s][i])\n            toplam_kare_hata += (v_si - hedef_hiz[i]) ** 2\n            x[i] += dt * v_si\n    return {'hedef_hiz': hedef_hiz, 'orta_nokta_x05': orta_nokta, 'ortalama_flow_kaybi': toplam_kare_hata / (adim_sayisi * d), 'euler_cikti': x}\n\nimport math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef adaln_zero_katmani(x, gamma, beta, alpha, alt_katman_ciktisi):\n    if not isinstance(x, list) or len(x) < 2 or (not all((_sayi_mi(v) for v in x))):\n        raise ValueError('x en az 2 elemanlı sayı listesi olmalı')\n    d = len(x)\n    for lst in (gamma, beta, alpha, alt_katman_ciktisi):\n        if not isinstance(lst, list) or len(lst) != d or (not all((_sayi_mi(v) for v in lst))):\n            raise ValueError('tüm vektörler x ile aynı uzunlukta sayı listesi olmalı')\n    mu = sum((float(v) for v in x)) / d\n    var = sum(((float(v) - mu) ** 2 for v in x)) / d\n    std = math.sqrt(var + 1e-06)\n    x_norm = [(float(v) - mu) / std for v in x]\n    mod_girdi = [x_norm[i] * (1.0 + float(gamma[i])) + float(beta[i]) for i in range(d)]\n    cikti = [float(x[i]) + float(alpha[i]) * float(alt_katman_ciktisi[i]) for i in range(d)]\n    birim_mi = all((abs(float(a)) < 1e-12 for a in alpha))\n    return {'x_norm': x_norm, 'mod_edilmis_girdi': mod_girdi, 'katman_ciktisi': cikti, 'birim_donusum_mu': birim_mi}", 'referans', 'exec'), _REF)
_t, _g = _ff(rectified_flow_euler, _REF['rectified_flow_euler'], ([-1.0, 2.0], [3.0, -2.0], [[4.0, -4.0], [4.0, -4.0]], 2), tohum=3174, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (rectified_flow_euler): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(adaln_zero_katmani, _REF['adaln_zero_katmani'], ([2.0, 4.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [99.0, -50.0]), tohum=2951, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (adaln_zero_katmani): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
def _sinir28():
    try:
        r1 = rectified_flow_euler([1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [[1.0, 1.0, 1.0]], 1)
        a1 = adaln_zero_katmani([2.0, 4.0], [0.0, 0.0], [0.0, 0.0], [1e-12, 0.0], [1.0, 1.0])
        a2 = adaln_zero_katmani([2.0, 4.0], [0.0, 0.0], [0.0, 0.0], [7e-13, 0.0], [1.0, 1.0])
        if abs(r1['ortalama_flow_kaybi'] - 4.0) > 1e-12 or a1['birim_donusum_mu'] is not False or a2['birim_donusum_mu'] is not True:
            return False
        for fn_, args_ in [(rectified_flow_euler, ([], [], [[]], 1)), (rectified_flow_euler, ([1.0], [2.0], [], 0)), (rectified_flow_euler, ([1.0], [2.0], [[1.0]], True)), (adaln_zero_katmani, ([1.0], [0.0], [0.0], [0.0], [0.0]))]:
            try:
                fn_(*args_)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(_sinir28(), 'sınır ve geçersiz girdi kontrolleri')
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_28 as D
try: r = D.deney(rectified_flow_euler, adaln_zero_katmani)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['baslangic_birim_donusum'], 'eğitim öncesi AdaLN-Zero bloğu gerçek gizli durumda birim dönüşüm')
kontrol(r['adaln_ayni'] and r['euler_ayni'], 'eğitim sonrası modülasyon ve Euler entegrasyonu torch ile aynı')
kontrol(r['az_adimda_iyi'] and r['tek_adim_ortalamaya_coker'], '4 adımda doğruluk ≥ 0.8; tek adımın çeşitliliği 32 adımdan düşük')
kontrol(r['reflow_duzlestirdi'], 'reflow tek adımlı örneği 32 adımlıya yaklaştırdı ve tek adımın çeşitliliğini artırdı')
kontrol(r['zehir_arttikca_sapiyor'], "zehirli örnek sayısı arttıkça '3' istenen örneklerin '8' çıkma oranı arttı")
ai_lab.kanit_yaz("ai-uretim-28-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-28", "deney": r})
```
```solution
import ai_lab
import math

def _sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def rectified_flow_euler(x0_gurultu, x1_veri, hiz_tahminleri, adim_sayisi):
    if not isinstance(x0_gurultu, list) or not x0_gurultu or (not all((_sayi_mi(v) for v in x0_gurultu))):
        raise ValueError('geçersiz x0_gurultu')
    d = len(x0_gurultu)
    if not isinstance(x1_veri, list) or len(x1_veri) != d or (not all((_sayi_mi(v) for v in x1_veri))):
        raise ValueError('geçersiz x1_veri')
    if isinstance(adim_sayisi, bool) or not isinstance(adim_sayisi, int) or adim_sayisi < 1:
        raise ValueError('adim_sayisi >= 1 tam sayı olmalı')
    if not isinstance(hiz_tahminleri, list) or len(hiz_tahminleri) != adim_sayisi:
        raise ValueError('hiz_tahminleri uzunluğu adim_sayisi ile eşit olmalı')
    for s in hiz_tahminleri:
        if not isinstance(s, list) or len(s) != d or (not all((_sayi_mi(v) for v in s))):
            raise ValueError('geçersiz hız tahmin satırı')
    hedef_hiz = [float(x1_veri[i]) - float(x0_gurultu[i]) for i in range(d)]
    orta_nokta = [0.5 * float(x0_gurultu[i]) + 0.5 * float(x1_veri[i]) for i in range(d)]
    toplam_kare_hata = 0.0
    dt = 1.0 / adim_sayisi
    x = [float(v) for v in x0_gurultu]
    for s in range(adim_sayisi):
        for i in range(d):
            v_si = float(hiz_tahminleri[s][i])
            toplam_kare_hata += (v_si - hedef_hiz[i]) ** 2
            x[i] += dt * v_si
    return {'hedef_hiz': hedef_hiz, 'orta_nokta_x05': orta_nokta, 'ortalama_flow_kaybi': toplam_kare_hata / (adim_sayisi * d), 'euler_cikti': x}

def adaln_zero_katmani(x, gamma, beta, alpha, alt_katman_ciktisi):
    if not isinstance(x, list) or len(x) < 2 or (not all((_sayi_mi(v) for v in x))):
        raise ValueError('x en az 2 elemanlı sayı listesi olmalı')
    d = len(x)
    for lst in (gamma, beta, alpha, alt_katman_ciktisi):
        if not isinstance(lst, list) or len(lst) != d or (not all((_sayi_mi(v) for v in lst))):
            raise ValueError('tüm vektörler x ile aynı uzunlukta sayı listesi olmalı')
    mu = sum((float(v) for v in x)) / d
    var = sum(((float(v) - mu) ** 2 for v in x)) / d
    std = math.sqrt(var + 1e-06)
    x_norm = [(float(v) - mu) / std for v in x]
    mod_girdi = [x_norm[i] * (1.0 + float(gamma[i])) + float(beta[i]) for i in range(d)]
    cikti = [float(x[i]) + float(alpha[i]) * float(alt_katman_ciktisi[i]) for i in range(d)]
    birim_mi = all((abs(float(a)) < 1e-12 for a in alpha))
    return {'x_norm': x_norm, 'mod_edilmis_girdi': mod_girdi, 'katman_ciktisi': cikti, 'birim_donusum_mu': birim_mi}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_28 as D
    D.goster(rectified_flow_euler, adaln_zero_katmani)
```
```hint
İki görevin çözümlerini olduğu gibi buraya koy.
```
:::

::: anlat Sınır
Görevler rectified flow interpolasyonunu, hedef hızı ve Euler çözücüyü, DiT AdaLN-Zero modülasyonunu küçük vektörlerle hesaplatır; final adım gerçek rakamlarda AdaLN-Zero bloklu küçük bir hız ağı eğitir (gerçek ölçekli bir DiT değildir). Rectified flow yollarının düzlüğü eğitimden (ve reflow'dan) sonra ancak yaklaşık olarak sağlanır; tek adımlı Euler eğri yollarda hata yapar. AdaLN-Zero'nun sıfır başlatması eğitimin başında bloğu kimlik fonksiyonu yapar; bu yalnız başlangıç kararlılığı içindir. Videodaki 3 boyutlu uzay-zaman yamaları token sayısını çok büyütür; gereken bellek ve hesap bu dersteki küçük örneklerin çok ötesindedir.

Kaynaklar: [Liu vd. 2022 - Flow Straight and Fast: Learning to Generate and Transfer Data with Rectified Flow](https://arxiv.org/abs/2209.03003), [Peebles ve Xie 2023 - Scalable Diffusion Models with Transformers](https://arxiv.org/abs/2212.09748), [Esser vd. 2024 - Scaling Rectified Flow Transformers for High-Resolution Image Synthesis](https://arxiv.org/abs/2403.03206).
:::

::: dusun
**Flux.1** ve **Stable Diffusion 3 (MMDiT — Multimodal Diffusion Transformer)** mimarisinde metin istemi (`T5 / CLIP Text Tokens`) görüntüye sadece dışarıdan `Cross-Attention` ile verilmez; bunun yerine **Metin Tokenları ile Görüntü Yaması Tokenları tek bir dizide uç uca birleştirilir (`[Text Tokens; Image Patch Tokens]`)** ve aynı `Self-Attention` matrisi içinde birbirleriyle çift yönlü konuşurlar!

**Mimari Tasarım Sorusu:** Metin embedding vektörleri ile görüntü yaması embedding vektörlerinin istatistiksel dağılımları birbirinden çok farklı olduğu için, `MMDiT` mimarisinde `Q, K, V` dikkat matrislerini ortak (`Joint Attention`) hesaplarken neden `AdaLN-Zero` ve `MLP` ağırlıkları metin akışı (`Text Stream`) ve görüntü akışı (`Image Stream`) için **iki ayrı paralel dal (`Dual-Stream Transformer Blocks`)** olarak tutulur?
:::

::: ozet
- **`Diffusion Transformer (DiT)`**, klasik evrişimli `U-Net` yerine `VAE` gizli uzayındaki görüntü/video yamalarını (`2D/3D Spacetime Patches`) doğrudan `Transformer` tokenları olarak işler ve parametre ölçeklenmesini (`Scaling Law`) açar.
- **`AdaLN-Zero (Adaptive LayerNorm-Zero)`**, zaman ($t$) ve koşul ($c$) bilgisini $\hat{x}(1 + \gamma) + \beta$ modülasyonu ve başlangıçta sıfır olan $\alpha$ kapısıyla (`Zero-Gate`) enjekte ederek derin `DiT` bloklarının ilk adımda birim dönüşüm (`Identity`) olarak kararlı başlamasını sağlar.
- **`Rectified Flow Matching`**, gürültü $x_0$ ile veri $x_1$ arasında düz çizgi interpolasyonu ($x_t = (1-t)x_0 + t x_1$) kurarak sabit hız vektörünü ($v = x_1 - x_0$) öğrenir ve `Euler ODE` çözücüsüyle 4–8 adımda yüksek kaliteli üretim yapar.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **U-Net'ten `Diffusion Transformer (DiT)` yamalarına (30 sn).** "`Flux` ve `Sora` tarzı modeller VAE gizli uzayındaki görüntü veya uzay-zaman video bloklarını 2B/3B yamalara (`patches`) bölüp doğrudan ölçeklenebilir `Transformer` tokenları olarak işler."
2. **`AdaLN-Zero` ile kararlı başlangıç (30 sn).** "Zaman adımı ve koşul vektörü $\hat{x}(1+\gamma)+\beta$ modülasyonuyla enjekte edilir; artık dalın önündeki $\alpha$ kapısı sıfır başlatıldığı için derin bloklar eğitimin ilk adımında birim dönüşüm (`Identity`) gibi davranır."
3. **`Rectified Flow` düz çizgi yörüngesi (35 sn).** "Gürültü $x_0$ ile veri $x_1$ arasında $x_t = (1-t)x_0 + t x_1$ doğrusal yolu kurulup sabit hız $v = x_1 - x_0$ öğrenilir; yol düzleştiği için `Euler` çözücüsü birkaç adımda hedefe varır."
4. **Soru (25 sn).** "Eğitimde metin-görüntü çiftlerinden ezberlenen telifli veya mahrem örnekler, akış eşleme modellerinde hangi koşullarda neredeyse birebir yeniden üretilebilir (`memorization`)?"
:::
