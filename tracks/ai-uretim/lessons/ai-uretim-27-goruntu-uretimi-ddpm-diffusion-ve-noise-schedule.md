---
id: ai-uretim-27
title: "Görüntü Üretimi 1: DDPM (Denoising Diffusion), Forward Noise Schedule ve Ters Örnekleme"
summary: "Saf Gauss gürültüsünden fotogerçekçi görüntüler üreten DDPM (Denoising Diffusion Probabilistic Models) matematiği: kapalı form ileri gürültü çizelgesi, gürültü tahmini (Noise Prediction Loss), DDIM ters örnekleme ve Classifier-Free Guidance (CFG)."
track: ai-uretim
order: 27
duration_minutes: 40
difficulty: ileri
xp: 310
prerequisites: [ai-uretim-26]
tags: [diffusion, ddpm, ddim, classifier-free-guidance, noise-schedule, generative-ai]
esleme: ai-uretim-26, ai-uretim-28
---

::: anlat
## Diffusion adımları

Diffusion training, temiz örneğe noise ekleme ile bu noise ilişkisini öğrenme fikrine dayanır. Bu derste forward noise hesabını, CFG birleşimini ve bir ters adım hesabını uygulayacaksın. Sayısal adımın doğruluğu ile üretilen görselin kalitesi ayrı ölçümlerdir.

Bir heykeltraşın mermer kütlesinden fazlalıkları yontarak heykeli ortaya çıkarması gibi, modern görüntü üretim modelleri (**Midjourney**, **Stable Diffusion**, **Imagen**, **DALL-E 3**) saf rastgele Gauss gürültüsünden (`Standard Normal Noise` $\mathcal{N}(0, I)$) başlar ve adım adım gürültüyü temizleyerek (**`Iterative Denoising`**) görüntüyü inşa eder.

2020 yılında **Jonathan Ho, Ajay Jain ve Pieter Abbeel (UC Berkeley)** tarafından yayınlanan **`DDPM (Denoising Diffusion Probabilistic Models)`** makalesi, yıllarca kararsızlığıyla bilinen `GAN (Generative Adversarial Networks)` modellerini tahtından indirerek görüntü üretiminin temel matematiğini kurdu.

```
┌────────────────────────────────────────────────────────────────────────────┐
│              DDPM / DDIM DIFFUSION SÜRECİ (İLERİ VE TERS AKIŞ)             │
├────────────────────────────────────────────────────────────────────────────┤
│  İLERİ SÜREÇ (Forward Diffusion q(x_t | x_0) — Analitik Kapalı Form):      │
│  [Net Resim x_0] ──(+beta_1)──► [Az Gürültülü x_t] ──(...)──► [Saf Gürültü │
│                                                                x_T ~ N(0,I)]│
│       x_t = sqrt(alpha_bar_t) * x_0  +  sqrt(1 - alpha_bar_t) * epsilon    │
│                                                                            │
│  TERS SÜREÇ (Reverse Denoising p_theta(x_{t-1} | x_t) — Öğrenilen Ağ):     │
│  [Net Resim x_0] ◄──(DDIM/CFG)── [Az Gürültülü x_t] ◄──(eps_theta)── [x_T] │
└────────────────────────────────────────────────────────────────────────────┘
```

---

### 1. İleri Difüzyon Süreci (`Forward Diffusion Process` $q(x_t \mid x_0)$) ve Kapalı Form Sıçraması

Elimizde gerçek ve net bir görüntü (veya `VAE Latent` tensörü) $x_0$ olsun. $T$ adım boyunca (ör. $T = 1000$) her adımda küçük bir varyans çizelgesi (`Variance / Noise Schedule`) $\beta_1, \beta_2, \dots, \beta_T \in (0, 1)$ (örn. $\beta_1 = 10^{-4}$'ten $\beta_T = 0.02$'ye artan) ile görüntünün üzerine biraz Gauss gürültüsü ekleriz:

$$q(x_t \mid x_{t-1}) = \mathcal{N}\left(x_t; \; \sqrt{1 - \beta_t} \, x_{t-1}, \; \beta_t \mathbf{I}\right)$$

**Kritik Mühendislik Sorusu:** Eğitim sırasında $t = 750$. adımdaki gürültülü görüntüyü ($x_{750}$) elde etmek için döngü kurup 750 kez üst üste gürültü mü ekleyeceğiz?
**Hayır!** İki bağımsız Gauss dağılımının toplamı yine bir Gauss dağılımıdır (**`Reparameterization Trick`**). Şu iki tanımı yapalım:

$$\alpha_t = 1 - \beta_t, \qquad \bar{\alpha}_t = \prod_{s=1}^{t} \alpha_s$$

Bu kümülatif çarpım ($\bar{\alpha}_t$) sayesinde, $x_0$'dan **herhangi bir $t$ adımına tek bir matematiksel işlemle (`O(1)` Kapalı Form Sıçraması)** doğrudan gidebiliriz:

$$x_t = \underbrace{\sqrt{\bar{\alpha}_t}}_{\text{Sinyal Katsayısı}} x_0 + \underbrace{\sqrt{1 - \bar{\alpha}_t}}_{\text{Gürültü Katsayısı}} \epsilon, \qquad \epsilon \sim \mathcal{N}(0, \mathbf{I})$$

Bu denklemin sezgisel anlamı muhteşemdir:
- $t \to 0$ iken $\bar{\alpha}_t \approx 1.0$'dır: $x_t \approx 1.0 \cdot x_0 + 0.0 \cdot \epsilon$ (Görüntü tertemizdir, Sinyal-Gürültü Oranı $\text{SNR}_t = \frac{\bar{\alpha}_t}{1 - \bar{\alpha}_t}$ çok yüksektir).
- $t \to T$ iken $\bar{\alpha}_T \approx 0.0$'dır: $x_T \approx 0.0 \cdot x_0 + 1.0 \cdot \epsilon = \epsilon$ (Orijinal görüntü tamamen silinmiş, geriye saf Gauss gürültüsü kalmıştır!).

---

### 2. DDPM Eğitim Hedefi (`Noise Prediction Loss`) ve $\hat{x}_0$ Rekonstrüksiyonu

Sinir ağımıza ($\epsilon_\theta(x_t, t, c)$) gürültülü görüntü $x_t$'yi, zaman adımı $t$'yi ve metin koşulu $c$'yi veririz. Ağdan doğrudan net resmi tahmin etmesini değil, **o adımda eklenmiş olan $\epsilon$ gürültüsünü tahmin etmesini (`Simple MSE Noise Prediction Loss`)** isteriz:

$$\mathcal{L}_{\text{DDPM}}(\theta) = \mathbb{E}_{t, x_0, \epsilon \sim \mathcal{N}(0, I)} \left[ \left\| \epsilon - \epsilon_\theta\left(\sqrt{\bar{\alpha}_t} x_0 + \sqrt{1 - \bar{\alpha}_t}\epsilon, \; t, \; c\right) \right\|_2^2 \right]$$

Peki ağ gürültüyü $\hat{\epsilon} = \epsilon_\theta(x_t, t, c)$ olarak tahmin ettiğinde, modelin o an aklındaki "temiz görüntü tahmini" ($\hat{x}_0$) nedir? İleri difüzyon denklemini $x_0$ için tersine çözersek:

$$\hat{x}_0 = \frac{x_t - \sqrt{1 - \bar{\alpha}_t} \, \hat{\epsilon}}{\sqrt{\bar{\alpha}_t}}$$

```python
import math

# Tek Bir Piksel Üzerinde DDPM Kapalı Form İleri Gürültü ve x0 Geri Çıkarımı
x0 = 0.80           # Orijinal net piksel değeri
epsilon = -0.50     # Eklenen standart normal gürültü
betalar = [0.1, 0.2, 0.3]  # 3 adımlık çizelge

# t = 2 (indis 1: ilk 2 adımın çarpımı) için alpha_bar hesabı:
alpha_bar_2 = (1.0 - betalar[0]) * (1.0 - betalar[1])  # 0.9 * 0.8 = 0.72
sinyal_katsayisi = math.sqrt(alpha_bar_2)
gurultu_katsayisi = math.sqrt(1.0 - alpha_bar_2)

# 1. İleri Gürültü: x_t
x_t = sinyal_katsayisi * x0 + gurultu_katsayisi * epsilon

# 2. Eğer model gürültüyü kusursuz tahmin ederse (eps_hat = epsilon), x0 tam geri döner!
x0_tahmin = (x_t - gurultu_katsayisi * epsilon) / sinyal_katsayisi
print(f"alpha_bar={alpha_bar_2:.2f} | x_t={x_t:.4f} | GeriCikarilan_x0={x0_tahmin:.2f}")
```

---

### 3. `Classifier-Free Guidance (CFG)` ve `DDIM` Deterministik Ters Adımı

Görüntü üretirken iki dev buluş kullanılır:

#### A) `Classifier-Free Guidance (CFG — Ho & Salimans, 2021)`
Modeli sadece koşullu gürültü tahmini $\epsilon_\theta(x_t, c)$ ile çalıştırırsan, üretilen resim metin istemine (`Prompt` $c$, örn. *"Astronot kedi"*) zayıf uyar ve bulanık olur.
- Eğitim sırasında metin istemlerinin %10'unu rastgele silip boş (`Unconditional / Null Prompt` $\varnothing$) bırakırız.
- Çıkarım (`Inference`) anında her adımda iki tahmin alırız:
  1. **Koşulsuz Tahmin (`Unconditional`):** $\epsilon_{\text{uncond}} = \epsilon_\theta(x_t, t, \varnothing)$ ("Herhangi bir resim yönü")
  2. **Koşullu Tahmin (`Conditional`):** $\epsilon_{\text{cond}} = \epsilon_\theta(x_t, t, c)$ ("Astronot kedi yönü")
- Ardından $w > 1$ (`CFG Guidance Scale`, örn. $w = 7.5$) ölçeğiyle koşulsuzdan koşulluya doğru vektörü **ekstrapole ederiz**:

$$\hat{\epsilon}_{\text{CFG}} = \epsilon_{\text{uncond}} + w \cdot \left( \epsilon_{\text{cond}} - \epsilon_{\text{uncond}} \right)$$

#### B) `DDIM (Denoising Diffusion Implicit Models — Song et al., ICLR 2021)`
Klasik `DDPM` ters örneklemesi stokastik olduğu için 1000 adımın tamamını tek tek yürümek zorundadır. **`DDIM`** ise aynı eğitilmiş ağı kullanarak süreci deterministik bir diferansiyel denkleme dönüştürür ve 1000 adımı **20–50 adımda** atlayarak (`Sub-sequence Sampling`) çözmemizi sağlar!

Adım $t$'den bir önceki örneklenen adıma ($t_{\text{prev}}$, kümülatif çarpımı $\bar{\alpha}_{\text{prev}}$) deterministik (`\eta = 0`) **`DDIM` güncelleme denklemi**:

$$1) \quad \hat{x}_0 = \frac{x_t - \sqrt{1 - \bar{\alpha}_t} \, \hat{\epsilon}_{\text{CFG}}}{\sqrt{\bar{\alpha}_t}}$$

$$2) \quad x_{t_{\text{prev}}} = \underbrace{\sqrt{\bar{\alpha}_{\text{prev}}} \, \hat{x}_0}_{\text{Tahmin edilen }\hat{x}_0\text{'a yöneliş}} + \underbrace{\sqrt{1 - \bar{\alpha}_{\text{prev}}} \, \hat{\epsilon}_{\text{CFG}}}_{\text{x}_t\text{'ye işaret eden yön}}$$

---

### 4. Gerçek PyTorch Üretim Kodu: `DDPMScheduler` ve `CFG + DDIM Step`

Gerçek bir `Diffusers` üretim boru hattında ileri gürültü çizelgesi ve `CFG + DDIM` ters örnekleme adımı PyTorch ile şu şekilde yazılır:

```python norun
import torch
import torch.nn.functional as F

class DDIMDiffusionEngine:
    def __init__(self, betas: torch.Tensor):
        # betas: (T,) örn. torch.linspace(1e-4, 0.02, 1000)
        self.alphas = 1.0 - betas
        self.alphas_cumprod = torch.cumprod(self.alphas, dim=0)

    def add_noise(self, x0: torch.Tensor, noise: torch.Tensor, timesteps: torch.LongTensor) -> torch.Tensor:
        # Kapalı form q(x_t | x_0): x_t = sqrt(alpha_bar_t) * x0 + sqrt(1 - alpha_bar_t) * noise
        a_bar = self.alphas_cumprod[timesteps].view(-1, 1, 1, 1)
        return torch.sqrt(a_bar) * x0 + torch.sqrt(1.0 - a_bar) * noise

    @torch.no_grad()
    def cfg_ddim_step(
        self,
        x_t: torch.Tensor,
        eps_uncond: torch.Tensor,
        eps_cond: torch.Tensor,
        cfg_scale: float,
        alpha_bar_t: float,
        alpha_bar_prev: float,
    ) -> torch.Tensor:
        # 1. Classifier-Free Guidance (CFG) birleştirme
        eps_cfg = eps_uncond + cfg_scale * (eps_cond - eps_uncond)

        # 2. Temiz görüntü tahmini (x0_pred)
        sqrt_ab_t = alpha_bar_t ** 0.5
        sqrt_one_minus_ab_t = (1.0 - alpha_bar_t) ** 0.5
        x0_pred = (x_t - sqrt_one_minus_ab_t * eps_cfg) / sqrt_ab_t

        # 3. DDIM deterministik (eta=0) bir önceki adım güncellemesi
        x_prev = (alpha_bar_prev ** 0.5) * x0_pred + ((1.0 - alpha_bar_prev) ** 0.5) * eps_cfg
        return x_prev
```

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [DDPM makalesi](https://arxiv.org/abs/2006.11239). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: tahmin Classifier-Free Guidance (CFG) Ekstrapolasyonu
Bir difüzyon adımında tek bir piksel için koşulsuz gürültü tahmini $\epsilon_{\text{uncond}} = 0.20$, metin koşullu gürültü tahmini ise $\epsilon_{\text{cond}} = 0.60$ çıkmıştır. Kullanıcı `cfg_scale` ($w$) değerini:
1) $w = 1.0$ (Standart koşullu üretim),
2) $w = 7.5$ (Güçlü `Classifier-Free Guidance`)
olarak seçtiğinde $\hat{\epsilon}_{\text{CFG}}$ değerleri ne olur?

```python
eps_uncond = 0.20
eps_cond = 0.60

def cfg_hesapla(w):
    return round(eps_uncond + w * (eps_cond - eps_uncond), 2)

print(f"w=1.0 -> {cfg_hesapla(1.0)} | w=7.5 -> {cfg_hesapla(7.5)}")
```

???

```cikti
w=1.0 -> 0.6 | w=7.5 -> 3.2
```
$w = 1.0$ iken $\hat{\epsilon}_{\text{CFG}} = 0.20 + 1.0 \times (0.60 - 0.20) = 0.60$ olur (yani doğrudan koşullu modelin tahmini kullanılır). $w = 7.5$ iken fark vektörü $(0.60 - 0.20 = +0.40)$ $7.5$ ile çarpılarak eklenir ve $\hat{\epsilon}_{\text{CFG}} = 0.20 + 3.00 = 3.20$ olur; böylece gürültü temizleme adımı metin isteminin ("Prompt") işaret ettiği yöne çok daha kararlı şekilde yönlendirilir.
:::

::: gorev 1 · DDPM Kapalı Form İleri Gürültü Ekleme (Forward Diffusion q(x_t | x_0))
Verilen temiz veri vektörü `x0`, gürültü varyans çizelgesi `betalar` ($\beta_1, \dots, \beta_T$), hedef zaman adımı `adim_t` ($1 \le t \le T$) ve standart normal gürültü vektörü `epsilon` için **`DDPM` kapalı form ileri difüzyonunu** ve Sinyal-Gürültü Oranını (`SNR`) hesaplayan `ddpm_ileri_gurultu(x0, betalar, adim_t, epsilon)` işlevini yaz.

**Girdi Kuralları ve Doğrulama:**
- `x0` ve `epsilon`: Aynı uzunlukta ($D \ge 1$), boş olmayan 1B sayı listeleri (`bool` olmayan sonlu sayılar).
- `betalar`: Boş olmayan ($T \ge 1$) 1B varyans çizelgesi listesi; her elemanı $(0.0, 1.0)$ açık aralığında (`0.0 < beta < 1.0`) `bool` olmayan sonlu sayı olmalıdır.
- `adim_t`: 1-tabanlı zaman adımı (`bool` olmayan tam sayı, $1 \le \text{adim\_t} \le len(\text{betalar})$).

**Hesaplama Kuralları:**
1. İlk `adim_t` adım için (`betalar[0]`'dan `betalar[adim_t - 1]`'e kadar dahil) $\alpha_s = 1.0 - \beta_s$ değerlerinin kümülatif çarpımını hesapla:
   $$\bar{\alpha}_t = \prod_{s=0}^{\text{adim\_t}-1} (1.0 - \text{betalar}[s])$$
2. `sinyal_katsayisi`: $\sqrt{\bar{\alpha}_t}$ (`float`).
3. `gurultu_katsayisi`: $\sqrt{1.0 - \bar{\alpha}_t}$ (`float`).
4. `x_t`: Her $i \in \{0, \dots, D-1\}$ için $\sqrt{\bar{\alpha}_t} \cdot x_0[i] + \sqrt{1.0 - \bar{\alpha}_t} \cdot \epsilon[i]$ (`float` listesi).
5. `snr`: Sinyal-Gürültü Oranı $\text{SNR}_t = \frac{\bar{\alpha}_t}{1.0 - \bar{\alpha}_t}$ (`float`).
6. İşlev şu sözlüğü döndürmelidir:
   `{"alpha_bar_t": float, "sinyal_katsayisi": float, "gurultu_katsayisi": float, "x_t": [...], "snr": float}`
- Geçersiz herhangi bir girdide `ValueError` yükseltilmelidir.

```starter
import math

# KUSURLU BAŞLANGIÇ KODU: Kümülatif çarpım (alpha_bar_t) ve karekök katsayılarını kullanmıyor!
def ddpm_ileri_gurultu(x0, betalar, adim_t, epsilon):
     b_t = betalar[adim_t - 1]
     a_t = 1.0 - b_t
     xt = [a_t * x0[i] + b_t * epsilon[i] for i in range(len(x0))]
     return {
         "alpha_bar_t": a_t,
         "sinyal_katsayisi": a_t,
         "gurultu_katsayisi": b_t,
         "x_t": xt,
         "snr": a_t / b_t,
     }

if __name__ == "__main__":
    print(ddpm_ileri_gurultu([1.0, -0.5], [0.1, 0.2, 0.3], adim_t=2, epsilon=[0.5, 1.0]))
```
```test
def sinama_ddpm(f):
    import copy, math, random
    def _ref(x0, betalar, t, eps):
        ab = 1.0
        for s in range(t):
            ab *= (1.0 - float(betalar[s]))
        sk = math.sqrt(ab)
        gk = math.sqrt(1.0 - ab)
        xt = [sk * float(x0[i]) + gk * float(eps[i]) for i in range(len(x0))]
        return {
            "alpha_bar_t": ab,
            "sinyal_katsayisi": sk,
            "gurultu_katsayisi": gk,
            "x_t": xt,
            "snr": ab / (1.0 - ab),
        }
    def _yakin(a, b):
        keys = {"alpha_bar_t", "sinyal_katsayisi", "gurultu_katsayisi", "x_t", "snr"}
        if not isinstance(a, dict) or set(a.keys()) != keys:
            return False
        for k in ("alpha_bar_t", "sinyal_katsayisi", "gurultu_katsayisi", "snr"):
            if isinstance(a[k], bool) or not isinstance(a[k], float) or abs(a[k] - b[k]) > 1e-11:
                return False
        if not isinstance(a["x_t"], list) or len(a["x_t"]) != len(b["x_t"]):
            return False
        return all(abs(u - v) < 1e-11 for u, v in zip(a["x_t"], b["x_t"]))
    try:
        x0 = [1.0, -0.5]
        bet = [0.1, 0.2, 0.3]
        eps = [0.5, 1.0]
        old = (list(x0), list(bet), list(eps))
        out = f(x0, bet, 2, eps)
        if (x0, bet, eps) != old or not _yakin(out, _ref(x0, bet, 2, eps)):
            return False
        # t=2 -> alpha_bar = 0.9 * 0.8 = 0.72, snr = 0.72 / 0.28 = 18/7
        if abs(out["alpha_bar_t"] - 0.72) > 1e-12 or abs(out["snr"] - (0.72 / 0.28)) > 1e-12:
            return False

        rng = random.Random(2701)
        for _ in range(25):
            d = rng.randint(1, 8)
            T = rng.randint(2, 10)
            t_adim = rng.randint(1, T)
            xx = [rng.uniform(-2.0, 2.0) for _ in range(d)]
            ee = [rng.uniform(-2.0, 2.0) for _ in range(d)]
            bb = [rng.uniform(0.001, 0.15) for _ in range(T)]
            if not _yakin(f(xx, bb, t_adim, ee), _ref(xx, bb, t_adim, ee)):
                return False

        bad_cases = [
            ([], [0.1], 1, []),
            ([1.0], [0.1], 1, [1.0, 2.0]),
            ([1.0], [], 1, [0.5]),
            ([1.0], [0.1, 0.2], 0, [0.5]),    # adim_t < 1
            ([1.0], [0.1, 0.2], 3, [0.5]),    # adim_t > T
            ([1.0], [0.0, 0.2], 1, [0.5]),    # beta <= 0
            ([1.0], [1.0, 0.2], 1, [0.5]),    # beta >= 1
            ([1.0], [0.1, 0.2], True, [0.5]),
            ([True], [0.1], 1, [0.5]),
        ]
        for bx, bb, bt, be in bad_cases:
            try:
                f(bx, bb, bt, be)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ddpm_ileri_gurultu = need("ddpm_ileri_gurultu")
ok(sinama_ddpm(ddpm_ileri_gurultu), "DDPM kümülatif alpha_bar_t, karekök katsayıları, x_t ve SNR hesabı")
for ad, mut in [
    ("karekök almayan", lambda x, b, t, e: dict(ddpm_ileri_gurultu(x, b, t, e), sinyal_katsayisi=ddpm_ileri_gurultu(x, b, t, e)["alpha_bar_t"])),
    ("yalnız son adımı alan", lambda x, b, t, e: ddpm_ileri_gurultu(x, [b[t-1]], 1, e)),
    ("SNR ters bölen", lambda x, b, t, e: dict(ddpm_ileri_gurultu(x, b, t, e), snr=1.0 / ddpm_ileri_gurultu(x, b, t, e)["snr"])),
]:
    ok(not sinama_ddpm(mut), "mutant reddedildi: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef ddpm_ileri_gurultu(x0, betalar, adim_t, epsilon):\n    if not isinstance(x0, list) or not x0 or (not all((_sayi_mi(v) for v in x0))):\n        raise ValueError('geçersiz x0')\n    if not isinstance(epsilon, list) or len(epsilon) != len(x0) or (not all((_sayi_mi(v) for v in epsilon))):\n        raise ValueError('geçersiz epsilon')\n    if not isinstance(betalar, list) or not betalar:\n        raise ValueError('boş olmayan betalar gerekli')\n    for b in betalar:\n        if not _sayi_mi(b) or not 0.0 < b < 1.0:\n            raise ValueError('beta (0, 1) açık aralığında olmalı')\n    if isinstance(adim_t, bool) or not isinstance(adim_t, int) or (not 1 <= adim_t <= len(betalar)):\n        raise ValueError('adim_t [1, len(betalar)] aralığında tam sayı olmalı')\n    alpha_bar = 1.0\n    for s in range(adim_t):\n        alpha_bar *= 1.0 - float(betalar[s])\n    sinyal_k = math.sqrt(alpha_bar)\n    gurultu_k = math.sqrt(1.0 - alpha_bar)\n    xt = [sinyal_k * float(x0[i]) + gurultu_k * float(epsilon[i]) for i in range(len(x0))]\n    snr = alpha_bar / (1.0 - alpha_bar)\n    return {'alpha_bar_t': alpha_bar, 'sinyal_katsayisi': sinyal_k, 'gurultu_katsayisi': gurultu_k, 'x_t': xt, 'snr': snr}", 'referans', 'exec'), _REF)
_t, _g = _ff(ddpm_ileri_gurultu, _REF['ddpm_ileri_gurultu'], ([1.0, -0.5], [0.1, 0.2, 0.3], 2, [0.5, 1.0]), tohum=2995, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (ddpm_ileri_gurultu): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math

def _ddpm_sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def ddpm_ileri_gurultu(x0, betalar, adim_t, epsilon):
    if not isinstance(x0, list) or not x0 or not all(_ddpm_sayi_mi(v) for v in x0):
        raise ValueError("geçersiz x0")
    if not isinstance(epsilon, list) or len(epsilon) != len(x0) or not all(_ddpm_sayi_mi(v) for v in epsilon):
        raise ValueError("geçersiz epsilon")
    if not isinstance(betalar, list) or not betalar:
        raise ValueError("boş olmayan betalar gerekli")
    for b in betalar:
        if not _ddpm_sayi_mi(b) or not (0.0 < b < 1.0):
            raise ValueError("beta (0, 1) açık aralığında olmalı")
    if isinstance(adim_t, bool) or not isinstance(adim_t, int) or not (1 <= adim_t <= len(betalar)):
        raise ValueError("adim_t [1, len(betalar)] aralığında tam sayı olmalı")

    alpha_bar = 1.0
    for s in range(adim_t):
        alpha_bar *= (1.0 - float(betalar[s]))

    sinyal_k = math.sqrt(alpha_bar)
    gurultu_k = math.sqrt(1.0 - alpha_bar)
    xt = [sinyal_k * float(x0[i]) + gurultu_k * float(epsilon[i]) for i in range(len(x0))]
    snr = alpha_bar / (1.0 - alpha_bar)

    return {
        "alpha_bar_t": alpha_bar,
        "sinyal_katsayisi": sinyal_k,
        "gurultu_katsayisi": gurultu_k,
        "x_t": xt,
        "snr": snr,
    }

if __name__ == "__main__":
    print(ddpm_ileri_gurultu([1.0, -0.5], [0.1, 0.2, 0.3], adim_t=2, epsilon=[0.5, 1.0]))
```
```hint
`for s in range(adim_t): alpha_bar *= (1.0 - betalar[s])` ile $\bar{\alpha}_t$ değerini bul. `math.sqrt(alpha_bar)` ve `math.sqrt(1.0 - alpha_bar)` katsayılarıyla `x_t` listesini ve `alpha_bar / (1.0 - alpha_bar)` ile `snr` değerini hesapla.
```
:::

::: gorev 2 · Classifier-Free Guidance (CFG) Birleştirme ve DDIM Deterministik Ters Adım
Bir difüzyon modelinin çıkarım adımında koşulsuz ($\epsilon_{\text{uncond}}$) ve koşullu ($\epsilon_{\text{cond}}$) gürültü tahminlerini **`Classifier-Free Guidance (CFG)`** ile birleştirip, temiz görüntü tahminini ($\hat{x}_0$) ve **`DDIM` ($\eta = 0$) bir önceki adım çıktısını ($x_{t_{\text{prev}}}$)** hesaplayan `cfg_ve_ddim_adimi(x_t, eps_kosulsuz, eps_kosullu, cfg_olcek, alpha_bar_t, alpha_bar_onceki)` işlevini yaz.

**Girdi Kuralları ve Doğrulama:**
- `x_t`, `eps_kosulsuz`, `eps_kosullu`: Aynı uzunlukta ($D \ge 1$), boş olmayan 1B sayı listeleri (`bool` olmayan sonlu sayılar).
- `cfg_olcek` ($w$): `bool` olmayan sonlu negatif olmayan sayı ($w \ge 0.0$).
- `alpha_bar_t` ($\bar{\alpha}_t$) ve `alpha_bar_onceki` ($\bar{\alpha}_{\text{prev}}$): `bool` olmayan sonlu sayılar;
  - $0.0 < \bar{\alpha}_t < 1.0$ ve $0.0 < \bar{\alpha}_{\text{prev}} \le 1.0$ olmalı,
  - Ters süreçte gürültü azaldığı (sinyal arttığı) için $\bar{\alpha}_{\text{prev}} > \bar{\alpha}_t$ koşulu sağlanmalıdır; aksi halde `ValueError` yükselt!

**Hesaplama Kuralları:**
Her eleman $i \in \{0, \dots, D-1\}$ için:
1. **`eps_cfg`:** $\hat{\epsilon}_{\text{CFG}}[i] = \epsilon_{\text{uncond}}[i] + w \cdot (\epsilon_{\text{cond}}[i] - \epsilon_{\text{uncond}}[i])$
2. **`x0_tahmin`:** $\hat{x}_0[i] = \frac{x_t[i] - \sqrt{1.0 - \bar{\alpha}_t} \cdot \hat{\epsilon}_{\text{CFG}}[i]}{\sqrt{\bar{\alpha}_t}}$
3. **`x_onceki` (`DDIM` $\eta = 0$ adımı):**
   $$x_{\text{prev}}[i] = \sqrt{\bar{\alpha}_{\text{prev}}} \cdot \hat{x}_0[i] + \sqrt{1.0 - \bar{\alpha}_{\text{prev}}} \cdot \hat{\epsilon}_{\text{CFG}}[i]$$
4. İşlev şu sözlüğü döndürmelidir:
   `{"eps_cfg": [...], "x0_tahmin": [...], "x_onceki": [...]}`
- Geçersiz herhangi bir girdide `ValueError` yükseltilmelidir.

```starter
import math

# KUSURLU BAŞLANGIÇ KODU: CFG fark ekstrapolasyonunu ve DDIM katsayılarını doğru uygulamıyor!
def cfg_ve_ddim_adimi(x_t, eps_kosulsuz, eps_kosullu, cfg_olcek, alpha_bar_t, alpha_bar_onceki):
     d = len(x_t)
     eps_c = [eps_kosullu[i] * cfg_olcek for i in range(d)]
     x0_p = [x_t[i] - eps_c[i] for i in range(d)]
     return {
         "eps_cfg": eps_c,
         "x0_tahmin": x0_p,
         "x_onceki": x0_p,
     }

if __name__ == "__main__":
    print(cfg_ve_ddim_adimi([0.5, -0.2], [0.1, 0.0], [0.3, -0.2], cfg_olcek=7.5, alpha_bar_t=0.36, alpha_bar_onceki=0.64))
```
```test
def sinama_ddim(f):
    import copy, math, random
    def _ref(xt, eu, ec, w, abt, abp):
        d = len(xt)
        w = float(w)
        abt, abp = float(abt), float(abp)
        ecfg = [float(eu[i]) + w * (float(ec[i]) - float(eu[i])) for i in range(d)]
        sabt = math.sqrt(abt)
        som_t = math.sqrt(1.0 - abt)
        x0p = [(float(xt[i]) - som_t * ecfg[i]) / sabt for i in range(d)]
        sabp = math.sqrt(abp)
        som_p = math.sqrt(1.0 - abp)
        xprev = [sabp * x0p[i] + som_p * ecfg[i] for i in range(d)]
        return {"eps_cfg": ecfg, "x0_tahmin": x0p, "x_onceki": xprev}
    def _yakin(a, b):
        keys = {"eps_cfg", "x0_tahmin", "x_onceki"}
        if not isinstance(a, dict) or set(a.keys()) != keys:
            return False
        for k in keys:
            if not isinstance(a[k], list) or len(a[k]) != len(b[k]):
                return False
            if any(abs(u - v) > 1e-10 for u, v in zip(a[k], b[k])):
                return False
        return True
    try:
        xt = [0.5, -0.2]
        eu = [0.1, 0.0]
        ec = [0.3, -0.2]
        old = (list(xt), list(eu), list(ec))
        out = f(xt, eu, ec, 7.5, 0.36, 0.64)
        if (xt, eu, ec) != old or not _yakin(out, _ref(xt, eu, ec, 7.5, 0.36, 0.64)):
            return False

        # alpha_bar_onceki == 1.0 (son adım, t=0'a varış) olduğunda x_onceki tam olarak x0_tahmin'e eşit olmalı!
        out_son = f(xt, eu, ec, 5.0, 0.5, 1.0)
        if not _yakin(out_son, _ref(xt, eu, ec, 5.0, 0.5, 1.0)):
            return False
        if any(abs(u - v) > 1e-12 for u, v in zip(out_son["x_onceki"], out_son["x0_tahmin"])):
            return False

        rng = random.Random(2702)
        for _ in range(25):
            d = rng.randint(1, 8)
            xx = [rng.uniform(-2.0, 2.0) for _ in range(d)]
            uu = [rng.uniform(-1.0, 1.0) for _ in range(d)]
            cc = [rng.uniform(-1.0, 1.0) for _ in range(d)]
            ww = rng.uniform(1.0, 12.0)
            abt = rng.uniform(0.05, 0.7)
            abp = rng.uniform(abt + 0.05, 1.0)
            if not _yakin(f(xx, uu, cc, ww, abt, abp), _ref(xx, uu, cc, ww, abt, abp)):
                return False

        bad_cases = [
            ([], [], [], 7.5, 0.3, 0.6),
            ([], [0.1], [0.1], 7.5, 0.3, 0.6),
            ([0.5], [0.1, 0.2], [0.1], 7.5, 0.3, 0.6),
            ([0.5], [0.1], [0.2], -1.0, 0.3, 0.6),   # cfg_olcek < 0
            ([0.5], [0.1], [0.2], 7.5, 0.36, 0.36), # eşit katsayılar
            ([0.5], [0.1], [0.2], 7.5, 0.0, 0.64),  # sıfır payda ValueError olmalı
            ([0.5], [0.1], [0.2], 7.5, 1.0, 1.0),   # üst sınırdaki eşitlik de yasak
            ([0.5], [0.1], [0.2], 7.5, 0.6, 0.3),    # alpha_bar_onceki <= alpha_bar_t
            ([0.5], [0.1], [0.2], 7.5, 0.5, 0.5),
            ([0.5], [0.1], [0.2], 7.5, 0.0, 0.5),
            ([0.5], [0.1], [0.2], 7.5, 0.5, 1.1),
            ([0.5], [0.1], [0.2], True, 0.3, 0.6),
        ]
        for bxt, beu, bec, bw, babt, babp in bad_cases:
            try:
                f(bxt, beu, bec, bw, babt, babp)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

cfg_ve_ddim_adimi = need("cfg_ve_ddim_adimi")
ok(sinama_ddim(cfg_ve_ddim_adimi), "CFG ekstrapolasyonu, x0 tahmini ve DDIM deterministik ters adım")
for ad, mut in [
    ("CFG'de uncond çıkarmayan", lambda xt, eu, ec, w, abt, abp: dict(cfg_ve_ddim_adimi(xt, eu, ec, w, abt, abp), eps_cfg=[eu[i] + w * ec[i] for i in range(len(xt))])),
    ("x_onceki yerine x0_tahmin döndüren", lambda xt, eu, ec, w, abt, abp: dict(cfg_ve_ddim_adimi(xt, eu, ec, w, abt, abp), x_onceki=cfg_ve_ddim_adimi(xt, eu, ec, w, abt, abp)["x0_tahmin"])),
]:
    ok(not sinama_ddim(mut), "mutant reddedildi: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef cfg_ve_ddim_adimi(x_t, eps_kosulsuz, eps_kosullu, cfg_olcek, alpha_bar_t, alpha_bar_onceki):\n    if not isinstance(x_t, list) or not x_t or (not all((_sayi_mi(v) for v in x_t))):\n        raise ValueError('geçersiz x_t')\n    d = len(x_t)\n    for lst in (eps_kosulsuz, eps_kosullu):\n        if not isinstance(lst, list) or len(lst) != d or (not all((_sayi_mi(v) for v in lst))):\n            raise ValueError('gürültü vektörleri x_t ile aynı boyutta sayı listesi olmalı')\n    for v in (cfg_olcek, alpha_bar_t, alpha_bar_onceki):\n        if not _sayi_mi(v):\n            raise ValueError('skaler parametreler sonlu sayı olmalı')\n    if cfg_olcek < 0.0:\n        raise ValueError('cfg_olcek >= 0 olmalı')\n    if not 0.0 < alpha_bar_t < 1.0 or not 0.0 < alpha_bar_onceki <= 1.0 or alpha_bar_onceki <= alpha_bar_t:\n        raise ValueError('0 < alpha_bar_t < alpha_bar_onceki <= 1 koşulu sağlanmalı')\n    w = float(cfg_olcek)\n    abt = float(alpha_bar_t)\n    abp = float(alpha_bar_onceki)\n    eps_cfg = [float(eps_kosulsuz[i]) + w * (float(eps_kosullu[i]) - float(eps_kosulsuz[i])) for i in range(d)]\n    sqrt_abt = math.sqrt(abt)\n    sqrt_om_abt = math.sqrt(1.0 - abt)\n    x0_tahmin = [(float(x_t[i]) - sqrt_om_abt * eps_cfg[i]) / sqrt_abt for i in range(d)]\n    sqrt_abp = math.sqrt(abp)\n    sqrt_om_abp = math.sqrt(1.0 - abp)\n    x_onceki = [sqrt_abp * x0_tahmin[i] + sqrt_om_abp * eps_cfg[i] for i in range(d)]\n    return {'eps_cfg': eps_cfg, 'x0_tahmin': x0_tahmin, 'x_onceki': x_onceki}", 'referans', 'exec'), _REF)
_t, _g = _ff(cfg_ve_ddim_adimi, _REF['cfg_ve_ddim_adimi'], ([0.5, -0.2], [0.1, 0.0], [0.3, -0.2], 7.5, 0.36, 0.64), tohum=2797, en_cok=600, mod='tam', butce='oto', ekler=[([0.5, -0.2], [0.1, 0.0], [0.3, -0.2], 7.5, 0, 0.64, ), ([0.5, -0.2], [0.1, 0.0], [0.3, -0.2], 7.5, 0, 0.64, )])
ok(_t, "farksal tarama (cfg_ve_ddim_adimi): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math

def _sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def cfg_ve_ddim_adimi(x_t, eps_kosulsuz, eps_kosullu, cfg_olcek, alpha_bar_t, alpha_bar_onceki):
    if not isinstance(x_t, list) or not x_t or not all(_sayi_mi(v) for v in x_t):
        raise ValueError("geçersiz x_t")
    d = len(x_t)
    for lst in (eps_kosulsuz, eps_kosullu):
        if not isinstance(lst, list) or len(lst) != d or not all(_sayi_mi(v) for v in lst):
            raise ValueError("gürültü vektörleri x_t ile aynı boyutta sayı listesi olmalı")
    for v in (cfg_olcek, alpha_bar_t, alpha_bar_onceki):
        if not _sayi_mi(v):
            raise ValueError("skaler parametreler sonlu sayı olmalı")
    if cfg_olcek < 0.0:
        raise ValueError("cfg_olcek >= 0 olmalı")
    if not (0.0 < alpha_bar_t < 1.0) or not (0.0 < alpha_bar_onceki <= 1.0) or alpha_bar_onceki <= alpha_bar_t:
        raise ValueError("0 < alpha_bar_t < alpha_bar_onceki <= 1 koşulu sağlanmalı")

    w = float(cfg_olcek)
    abt = float(alpha_bar_t)
    abp = float(alpha_bar_onceki)

    eps_cfg = [float(eps_kosulsuz[i]) + w * (float(eps_kosullu[i]) - float(eps_kosulsuz[i])) for i in range(d)]

    sqrt_abt = math.sqrt(abt)
    sqrt_om_abt = math.sqrt(1.0 - abt)
    x0_tahmin = [(float(x_t[i]) - sqrt_om_abt * eps_cfg[i]) / sqrt_abt for i in range(d)]

    sqrt_abp = math.sqrt(abp)
    sqrt_om_abp = math.sqrt(1.0 - abp)
    x_onceki = [sqrt_abp * x0_tahmin[i] + sqrt_om_abp * eps_cfg[i] for i in range(d)]

    return {
        "eps_cfg": eps_cfg,
        "x0_tahmin": x0_tahmin,
        "x_onceki": x_onceki,
    }

if __name__ == "__main__":
    print(cfg_ve_ddim_adimi([0.5, -0.2], [0.1, 0.0], [0.3, -0.2], cfg_olcek=7.5, alpha_bar_t=0.36, alpha_bar_onceki=0.64))
```
```hint
Önce `eps_cfg[i] = eps_kosulsuz[i] + cfg_olcek * (eps_kosullu[i] - eps_kosulsuz[i])` hesapla. Ardından `x0_tahmin[i] = (x_t[i] - sqrt(1 - alpha_bar_t) * eps_cfg[i]) / sqrt(alpha_bar_t)` ve `x_onceki[i] = sqrt(alpha_bar_onceki) * x0_tahmin[i] + sqrt(1 - alpha_bar_onceki) * eps_cfg[i]` formüllerini uygula.
```
:::

::: anlat Gerçek deney: Gerçek rakamlarda koşullu DDPM, CFG ölçeği ve ezberleme ölçümü
Final küçük ama gerçek bir difüzyon modeli eğitir ve örnekler (indirme yok, CPU yeter):

- **Veri:** scikit-learn'ün gerçek el yazısı rakamları (8×8, $[-1, 1]$ aralığına ölçeklenmiş), 1 400 eğitim / 397 test.
- **İleri gürültü:** altı gerçek görüntü farklı $t$ adımlarında senin `ddpm_ileri_gurultu` işlevinle gürültülenir; sonuç torch'un kapalı form hesabıyla karşılaştırılır.
- **Eğitim:** sınıf koşullu küçük bir MLP gürültü tahmincisi ($T = 100$, doğrusal β takvimi) 4 000 adım eğitilir. Etiketlerin %15'i "koşulsuz" etiketle değiştirilir; CFG'nin koşulsuz tahmini böyle öğrenilir.
- **Örnekleme:** 100 örnek (her rakamdan 10) 25 adımlı DDIM ile üretilir. **Her adımın her örneği** senin `cfg_ve_ddim_adimi` işlevinle hesaplanır. Dört CFG ölçeği denenir: $w = 0$ (koşulsuz), 1 (koşullu), 3, 6.
- **Kalite:** gerçek görüntülerde eğitilmiş bir lojistik regresyon (test doğruluğu ~0.96) üretilen örneğin istenen rakam olup olmadığını söyler. Ayrıca $[-1, 1]$ dışına taşan piksel oranı ölçülür: aşırı CFG'nin "doygun" görüntülerinin karşılığıdır.
- **Ezberleme:** üretilen her örneğin eğitim ve test kümesindeki en yakın gerçek görüntüye uzaklığı ölçülür. Örnekler eğitim görüntülerine testtekilerden belirgin yakınsa ya da bir eğitim görüntüsünün neredeyse kopyasıysa model ezberliyor demektir (Carlini vd. 2023).

**Güvenlik yönü — üyelik çıkarımı ve eğitim kümesi boyutu:** Bir görüntünün eğitimde kullanılıp kullanılmadığı modelin gürültü tahmin hatasından anlaşılabilir: üyelerde hata daha düşüktür. Aynı ağ bir kez 1 400 görüntüyle (ana model), bir kez yalnız 100 görüntüyle eğitilir; 100 üye ve 100 dışarıdan görüntüde sabit $t$ ve $\epsilon$ kümesinde ortalama hata ölçülür, AUC ve %5 yanlış alarmda yakalanan üye oranı hesaplanır. Büyük kümede saldırı yazı turadan pek iyi değildir; küçük kümede neredeyse her üye yakalanır. Az veriyle (ya da çoğaltılmış örneklerle) eğitilen üretken modeller eğitim verisi hakkında bilgi sızdırır.

Kabul: iki işlevin farksal taramayı geçmesi; ileri gürültü ve DDIM adımının torch ile aynı olması; koşullu örneklemenin koşulsuza göre doğruluğu en az 0.3 artırması ve CFG 3'ün CFG 1'den kötü olmaması. Ayrıca 100 görüntüyle eğitilen modelde üyelik AUC'si 0.8'i aşmalı ve 1 400 görüntülü modelden en az 0.1 yüksek olmalıdır.

**Kanıt dosyasını oku:** `cfg` (doğruluk, çeşitlilik, taşan piksel), `ezber_egitim_mesafe_medyan`, `ezber_test_mesafe_medyan`, `neredeyse_kopya`. Soru 1: $w = 0$'da doğruluk neden yaklaşık 0.1? Soru 2: $w = 6$'da doğruluk neden artmıyor ve taşan piksel oranı ne söylüyor? Soru 3: Çok daha büyük bir model ya da çok daha az eğitim verisiyle ezberleme ölçümü nasıl değişirdi?
:::

::: gorev Gerçek deney · Gerçek rakamlarda koşullu DDPM eğitimi, öğrenci adımlarıyla CFG + DDIM örnekleme ve ezberleme
Önceki görevlerdeki `ddpm_ileri_gurultu`, `cfg_ve_ddim_adimi` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 240
```
```starter
import ai_lab
import math

def ddpm_ileri_gurultu(x0, betalar, adim_t, epsilon):
    b_t = betalar[adim_t - 1]
    a_t = 1.0 - b_t
    xt = [a_t * x0[i] + b_t * epsilon[i] for i in range(len(x0))]
    return {'alpha_bar_t': a_t, 'sinyal_katsayisi': a_t, 'gurultu_katsayisi': b_t, 'x_t': xt, 'snr': a_t / b_t}

import math

def cfg_ve_ddim_adimi(x_t, eps_kosulsuz, eps_kosullu, cfg_olcek, alpha_bar_t, alpha_bar_onceki):
    d = len(x_t)
    eps_c = [eps_kosullu[i] * cfg_olcek for i in range(d)]
    x0_p = [x_t[i] - eps_c[i] for i in range(d)]
    return {'eps_cfg': eps_c, 'x0_tahmin': x0_p, 'x_onceki': x0_p}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_27 as D
    D.goster(ddpm_ileri_gurultu, cfg_ve_ddim_adimi)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_ag', 'rakam_verisi', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
ddpm_ileri_gurultu = need("ddpm_ileri_gurultu")
cfg_ve_ddim_adimi = need("cfg_ve_ddim_adimi")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef ddpm_ileri_gurultu(x0, betalar, adim_t, epsilon):\n    if not isinstance(x0, list) or not x0 or (not all((_sayi_mi(v) for v in x0))):\n        raise ValueError('geçersiz x0')\n    if not isinstance(epsilon, list) or len(epsilon) != len(x0) or (not all((_sayi_mi(v) for v in epsilon))):\n        raise ValueError('geçersiz epsilon')\n    if not isinstance(betalar, list) or not betalar:\n        raise ValueError('boş olmayan betalar gerekli')\n    for b in betalar:\n        if not _sayi_mi(b) or not 0.0 < b < 1.0:\n            raise ValueError('beta (0, 1) açık aralığında olmalı')\n    if isinstance(adim_t, bool) or not isinstance(adim_t, int) or (not 1 <= adim_t <= len(betalar)):\n        raise ValueError('adim_t [1, len(betalar)] aralığında tam sayı olmalı')\n    alpha_bar = 1.0\n    for s in range(adim_t):\n        alpha_bar *= 1.0 - float(betalar[s])\n    sinyal_k = math.sqrt(alpha_bar)\n    gurultu_k = math.sqrt(1.0 - alpha_bar)\n    xt = [sinyal_k * float(x0[i]) + gurultu_k * float(epsilon[i]) for i in range(len(x0))]\n    snr = alpha_bar / (1.0 - alpha_bar)\n    return {'alpha_bar_t': alpha_bar, 'sinyal_katsayisi': sinyal_k, 'gurultu_katsayisi': gurultu_k, 'x_t': xt, 'snr': snr}\n\nimport math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef cfg_ve_ddim_adimi(x_t, eps_kosulsuz, eps_kosullu, cfg_olcek, alpha_bar_t, alpha_bar_onceki):\n    if not isinstance(x_t, list) or not x_t or (not all((_sayi_mi(v) for v in x_t))):\n        raise ValueError('geçersiz x_t')\n    d = len(x_t)\n    for lst in (eps_kosulsuz, eps_kosullu):\n        if not isinstance(lst, list) or len(lst) != d or (not all((_sayi_mi(v) for v in lst))):\n            raise ValueError('gürültü vektörleri x_t ile aynı boyutta sayı listesi olmalı')\n    for v in (cfg_olcek, alpha_bar_t, alpha_bar_onceki):\n        if not _sayi_mi(v):\n            raise ValueError('skaler parametreler sonlu sayı olmalı')\n    if cfg_olcek < 0.0:\n        raise ValueError('cfg_olcek >= 0 olmalı')\n    if not 0.0 < alpha_bar_t < 1.0 or not 0.0 < alpha_bar_onceki <= 1.0 or alpha_bar_onceki <= alpha_bar_t:\n        raise ValueError('0 < alpha_bar_t < alpha_bar_onceki <= 1 koşulu sağlanmalı')\n    w = float(cfg_olcek)\n    abt = float(alpha_bar_t)\n    abp = float(alpha_bar_onceki)\n    eps_cfg = [float(eps_kosulsuz[i]) + w * (float(eps_kosullu[i]) - float(eps_kosulsuz[i])) for i in range(d)]\n    sqrt_abt = math.sqrt(abt)\n    sqrt_om_abt = math.sqrt(1.0 - abt)\n    x0_tahmin = [(float(x_t[i]) - sqrt_om_abt * eps_cfg[i]) / sqrt_abt for i in range(d)]\n    sqrt_abp = math.sqrt(abp)\n    sqrt_om_abp = math.sqrt(1.0 - abp)\n    x_onceki = [sqrt_abp * x0_tahmin[i] + sqrt_om_abp * eps_cfg[i] for i in range(d)]\n    return {'eps_cfg': eps_cfg, 'x0_tahmin': x0_tahmin, 'x_onceki': x_onceki}", 'referans', 'exec'), _REF)
_t, _g = _ff(ddpm_ileri_gurultu, _REF['ddpm_ileri_gurultu'], ([1.0, -0.5], [0.1, 0.2, 0.3], 2, [0.5, 1.0]), tohum=2995, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (ddpm_ileri_gurultu): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(cfg_ve_ddim_adimi, _REF['cfg_ve_ddim_adimi'], ([0.5, -0.2], [0.1, 0.0], [0.3, -0.2], 7.5, 0.36, 0.64), tohum=2797, en_cok=600, mod='tam', butce='oto', ekler=[([0.5, -0.2], [0.1, 0.0], [0.3, -0.2], 7.5, 0, 0.64, ), ([0.5, -0.2], [0.1, 0.0], [0.3, -0.2], 7.5, 0, 0.64, )])
kontrol(_t, "farksal tarama (cfg_ve_ddim_adimi): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
def _birim_27():
    for _args in (([], [0.1], 1, []), ([True], [0.1], 1, [0.5]), ([float("nan")], [0.1], 1, [0.5]), (["x"], [0.1], 1, [0.5])):
        try:
            ddpm_ileri_gurultu(*_args)
            return False
        except ValueError:
            pass
    for _args in (([], [], [], 7.5, 0.3, 0.6), ([0.5], [0.1], [0.2], 7.5, 0.0, 0.64), ([0.5], [0.1], [0.2], 7.5, 1.0, 1.0)):
        try:
            cfg_ve_ddim_adimi(*_args)
            return False
        except ValueError:
            pass
    return True
kontrol(_birim_27(), "DDPM ve CFG/DDIM boş vektör ve sayı türü doğrulama sözleşmesi")
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_27 as D
try: r = D.deney(ddpm_ileri_gurultu, cfg_ve_ddim_adimi)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['ileri_ayni'] and r['ddim_ayni'], 'ileri gürültü ve CFG + DDIM adımı gerçek değerlerde torch ile aynı')
kontrol(r['cfg_dogrulugu_artirdi'], "koşullu örnekleme doğruluğu koşulsuza göre en az 0.3 artırdı, CFG 3 CFG 1'den kötü değil")
kontrol(r['kucuk_kume_uyeligi_sizdiriyor'], 'küçük kümede eğitilen difüzyon modelinde gürültü hatasından üyelik neredeyse kusursuz çıkarıldı')
ai_lab.kanit_yaz("ai-uretim-27-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-27", "deney": r})
```
```solution
import ai_lab
import math

def _ddpm_sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def ddpm_ileri_gurultu(x0, betalar, adim_t, epsilon):
    if not isinstance(x0, list) or not x0 or (not all((_ddpm_sayi_mi(v) for v in x0))):
        raise ValueError('geçersiz x0')
    if not isinstance(epsilon, list) or len(epsilon) != len(x0) or (not all((_ddpm_sayi_mi(v) for v in epsilon))):
        raise ValueError('geçersiz epsilon')
    if not isinstance(betalar, list) or not betalar:
        raise ValueError('boş olmayan betalar gerekli')
    for b in betalar:
        if not _ddpm_sayi_mi(b) or not 0.0 < b < 1.0:
            raise ValueError('beta (0, 1) açık aralığında olmalı')
    if isinstance(adim_t, bool) or not isinstance(adim_t, int) or (not 1 <= adim_t <= len(betalar)):
        raise ValueError('adim_t [1, len(betalar)] aralığında tam sayı olmalı')
    alpha_bar = 1.0
    for s in range(adim_t):
        alpha_bar *= 1.0 - float(betalar[s])
    sinyal_k = math.sqrt(alpha_bar)
    gurultu_k = math.sqrt(1.0 - alpha_bar)
    xt = [sinyal_k * float(x0[i]) + gurultu_k * float(epsilon[i]) for i in range(len(x0))]
    snr = alpha_bar / (1.0 - alpha_bar)
    return {'alpha_bar_t': alpha_bar, 'sinyal_katsayisi': sinyal_k, 'gurultu_katsayisi': gurultu_k, 'x_t': xt, 'snr': snr}

import math

def _sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def cfg_ve_ddim_adimi(x_t, eps_kosulsuz, eps_kosullu, cfg_olcek, alpha_bar_t, alpha_bar_onceki):
    if not isinstance(x_t, list) or not x_t or (not all((_sayi_mi(v) for v in x_t))):
        raise ValueError('geçersiz x_t')
    d = len(x_t)
    for lst in (eps_kosulsuz, eps_kosullu):
        if not isinstance(lst, list) or len(lst) != d or (not all((_sayi_mi(v) for v in lst))):
            raise ValueError('gürültü vektörleri x_t ile aynı boyutta sayı listesi olmalı')
    for v in (cfg_olcek, alpha_bar_t, alpha_bar_onceki):
        if not _sayi_mi(v):
            raise ValueError('skaler parametreler sonlu sayı olmalı')
    if cfg_olcek < 0.0:
        raise ValueError('cfg_olcek >= 0 olmalı')
    if not 0.0 < alpha_bar_t < 1.0 or not 0.0 < alpha_bar_onceki <= 1.0 or alpha_bar_onceki <= alpha_bar_t:
        raise ValueError('0 < alpha_bar_t < alpha_bar_onceki <= 1 koşulu sağlanmalı')
    w = float(cfg_olcek)
    abt = float(alpha_bar_t)
    abp = float(alpha_bar_onceki)
    eps_cfg = [float(eps_kosulsuz[i]) + w * (float(eps_kosullu[i]) - float(eps_kosulsuz[i])) for i in range(d)]
    sqrt_abt = math.sqrt(abt)
    sqrt_om_abt = math.sqrt(1.0 - abt)
    x0_tahmin = [(float(x_t[i]) - sqrt_om_abt * eps_cfg[i]) / sqrt_abt for i in range(d)]
    sqrt_abp = math.sqrt(abp)
    sqrt_om_abp = math.sqrt(1.0 - abp)
    x_onceki = [sqrt_abp * x0_tahmin[i] + sqrt_om_abp * eps_cfg[i] for i in range(d)]
    return {'eps_cfg': eps_cfg, 'x0_tahmin': x0_tahmin, 'x_onceki': x_onceki}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_27 as D
    D.goster(ddpm_ileri_gurultu, cfg_ve_ddim_adimi)
```
```hint
İki görevin çözümlerini olduğu gibi buraya koy.
```
:::

::: anlat Sınır
Görevler DDPM'in kapalı form ileri gürültülemesini, CFG birleştirmesini ve DDIM'in deterministik ters adımını küçük sayılarla hesaplatır; final adım gerçek rakamlarda küçük bir difüzyon modeli eğitip senin adımlarınla örnek üretir. Gürültü takvimi (linear, cosine) ve adım sayısı kaliteyi belirler; az adımlı DDIM ayrıntı kaybeder. Yüksek CFG ölçeği metne uyumu artırırken çeşitliliği azaltır ve aşırı doygun renkler ile artefaktlar üretir. Difüzyon modelleri eğitim görüntülerini ezberleyip yeniden üretebilir (gizlilik ve telif riski); final adım bunu en yakın komşu mesafesiyle kaba olarak ölçer.

Kaynaklar: [Ho vd. 2020 - Denoising Diffusion Probabilistic Models](https://arxiv.org/abs/2006.11239), [Song vd. 2020 - Denoising Diffusion Implicit Models](https://arxiv.org/abs/2010.02502), [Ho ve Salimans 2022 - Classifier-Free Diffusion Guidance](https://arxiv.org/abs/2207.12598).
:::

::: dusun
Klasik `DDPM` modellerinde kullanılan doğrusal $\beta_t$ çizelgesinde (`Linear Schedule`) çok sinsi bir kusur (**`Zero Terminal SNR Flaw` — Lin et al., 2024**) keşfedilmiştir:
$t = T = 1000$ adımında bile $\bar{\alpha}_{1000} \approx 4 \times 10^{-5} > 0$ olduğu için, eğitimdeki son adım görüntüsü $x_T$ hiçbir zaman **%100 saf gürültü** olmaz; içinde orijinal görüntünün ortalama parlaklığına (düşük frekanslı rengine) dair küçük bir sızıntı kalır! Oysa çıkarım (`Inference`) anında biz modele %100 saf $\mathcal{N}(0, I)$ gürültü veririz!

**Mühendislik Sorusu:** Eğitimdeki bu küçük sızıntı nedeniyle klasik `Stable Diffusion 1.5` modellerinin **tamamen simsiyah (gece uzay karanlığı) veya bembeyaz (kar fırtınası)** resimler üretemeyip hep orta gri parlaklığa kaymasının sebebi nedir? Ve **`Cosine Schedule / Zero-Terminal SNR`** ($\bar{\alpha}_T = 0$) ile **`v-prediction` ($v = \sqrt{\bar{\alpha}_t}\epsilon - \sqrt{1 - \bar{\alpha}_t}x_0$)** bu sorunu nasıl çözer?
:::

::: ozet
- **`DDPM (Denoising Diffusion Probabilistic Models)`**, net veriye $T$ adımda kademeli Gauss gürültüsü ekleyen ileri süreci kapalı formda $x_t = \sqrt{\bar{\alpha}_t}x_0 + \sqrt{1 - \bar{\alpha}_t}\epsilon$ olarak tanımlar.
- Sinir ağı $\epsilon_\theta(x_t, t, c)$, gürültülü görüntüden eklenen $\epsilon$ gürültüsünü tahmin etmek üzere karesel hata (`MSE`) ile eğitilir.
- **`Classifier-Free Guidance (CFG)`**, koşulsuz ve koşullu tahminler arasındaki farkı $w$ ölçeğiyle büyüterek ($\epsilon_{\text{uncond}} + w(\epsilon_{\text{cond}} - \epsilon_{\text{uncond}})$) metin istemine sadakati artırırken; **`DDIM`** deterministik yörüngesiyle adım sayısını 1000'den 20–50'ye indirir.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Kapalı form ileri gürültü (25 sn).** "`DDPM` her adımı tek tek simüle etmez; $\bar{\alpha}_t = \prod_{s=1}^t (1-\beta_s)$ çarpımıyla herhangi bir $t$ anındaki gürültülü örneği $x_t = \sqrt{\bar{\alpha}_t}x_0 + \sqrt{1-\bar{\alpha}_t}\epsilon$ olarak tek adımda üretir."
2. **CFG ve DDIM ters adımı (35 sn).** "`CFG`, koşulsuz ve koşullu gürültü tahminlerinin farkını $w$ ile büyütüp hedef sınıfa yönlendirir; `DDIM` ise tahmini $\hat{x}_0$ üzerinden rastgele gürültü eklemeden daha büyük zaman adımlarıyla geri yürür."
3. **Gizlilik ve ezberleme sınırı (35 sn).** "Küçük veri kümesinde eğitilen difüzyon modelinin gürültü tahmin hatası eğitim örneklerinde belirgin biçimde düşer; bu fark hem veri kümesi üyeliği çıkarımına (`membership inference`) hem de örnek ezberlemeye kapı açar."
4. **Soru (25 sn).** "CFG ölçeği $w$'yi çok büyüttüğümüzde sınıf doğruluğu artarken neden çeşitlilik düşer ve görüntü uç değerlere doygunlaşır?"
:::
