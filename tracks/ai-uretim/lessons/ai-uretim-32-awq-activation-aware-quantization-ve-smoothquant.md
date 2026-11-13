---
id: ai-uretim-32
title: "Sıfırdan AWQ (Activation-Aware Quantization) ve SmoothQuant (W8A8 Outlier Göçü)"
summary: "Büyük LLM'lerde ortaya çıkan Emergent Outlier aktivasyon kanalları, önemli ağırlıkların (%1 Salient Weights) ölçeklenerek korunduğu AWQ (Lin et al.) ızgara araması ve aktivasyon zorluğunu ağırlıklara taşıyan SmoothQuant (Xiao et al. W8A8)."
esleme: ai-uretim-31, ai-temel-08, ai-saldiri-21
track: ai-uretim
order: 32
duration_minutes: 40
difficulty: ileri
xp: 310
prerequisites: [ai-uretim-31]
tags: [awq, smoothquant, quantization, w4a16, w8a8, outliers, compression]
---

::: anlat
## AWQ ve SmoothQuant ölçekleri

Weight ve activation kanallarını yeniden ölçeklemek quantization hatasının dağılımını değiştirir. Bu derste AWQ için bir ölçek aramasını ve SmoothQuant için eşdeğer matris dönüşümünü hesaplayacaksın. Gerçek hız için kernel desteği ve donanımda ölçüm ayrıca gerekir.

Daha da ilginç bir keşif **Dettmers et al. (`LLM.int8()`)**, **Lin et al. (MIT, MLSys 2024 — `AWQ`)** ve **Xiao et al. (MIT, ICML 2023 — `SmoothQuant`)** tarafından yapıldı:
Model boyutu **6.7 Milyar parametreyi geçtiği anda**, Transformer katmanlarındaki gizli aktivasyonların ($X$) **belirli birkaç kanalında** diğer tüm kanallardan **100 kat daha büyük (`> 60.0` vs `0.5`) sabit aykırı değerler (`Emergent Activation Outliers`)** belirir!

Bu gözlem iki quantization mimarisini doğurdu:
1. **`AWQ (Activation-Aware Weight Quantization — W4A16)`:** Ağırlıkları 4-bite (`INT4`), aktivasyonları 16-bitte (`FP16/BF16`) tutarken; bu devasa aktivasyon kanallarıyla çarpılan **%1'lik kritik ağırlık sütunlarını (`Salient Weights`)** quantization öncesinde $s > 1$ çarpanıyla büyütüp korur!
2. **`SmoothQuant (W8A8)`:** Hem ağırlıkları hem aktivasyonları 8-bite (`INT8 Tensor Cores`) indirmek istediğimizde, aktivasyonlardaki 100 katlık sivri tepeleri matematiksel bir eşdeğerlik dönüşümüyle uysal ağırlıklara "göç ettirir (`Outlier Migration`)"!

```
┌────────────────────────────────────────────────────────────────────────────┐
│         AWQ (W4A16 SALIENT SCALING) vs SMOOTHQUANT (W8A8 MIGRATION)        │
├─────────────────────────────────────┬──────────────────────────────────────┤
│ 1. AWQ (LIN ET AL., MLSYS 2024)     │ 2. SMOOTHQUANT (XIAO ET AL., 2023)   │
│ ─────────────────────────────────── │ ──────────────────────────────────── │
│ • Hedef: W4A16 (Bellek Darboğazı)   │ • Hedef: W8A8 (INT8 Tensor Core Hızı)│
│ • Gözlem: Ağırlıkların yalnız %1'i  │ • Sorun: Ağırlık W düzgün (kolay),   │
│   (büyük aktivasyon kanallarına     │   ama Aktivasyon X aşırı sivri (zor)!│
│   çarpan sütunlar) kritik önemdedir!│ • Çözüm: Zorluğu α oranında paylaş!  │
│ • Çözüm: W * X = (W*diag(s))*(s^-1X)│   s_j = max(|X_j|)^α / max(|W_j|)^1-α│
│ • s = (mean|X|)^α ölçeğinde en düşük│ • X_hat = X * diag(s)^-1 (Düzleşir!) │
│   ||WX - Q(W*s)*s^-1*X|| hatasını   │ • W_hat = diag(s) * W    (Biraz büyür│
│   veren α in [0, 1] Grid Search!    │   ama hâlâ INT8'e rahatça sığar!)    │
└─────────────────────────────────────┴──────────────────────────────────────┘
```

---

### 1. `AWQ (Activation-Aware Weight Quantization)`: %1 Kritik Sütunu Donanımı Yavaşlatmadan Korumak

Eğer bir ağırlık satırındaki %1'lik kritik ağırlıkları `FP16` bırakıp kalan %99'u `INT4` yaparsak (**`Mixed-Precision`**), GPU'da her çarpımda dallanma ve düzensiz bellek erişimi oluştuğu için çıkarım hızı çakılır.

**Lin et al. (`AWQ`)**, tüm ağırlıkları **istisnasız `INT4`** tutarken kritik sütunları korumanın matematiksel yolunu buldu:
Bir ağırlık satırında $j$. sütunu quantization işleminden önce $s_j > 1$ ölçeğiyle çarpıp, aktivasyonun $j$. kanalını $s_j$'ye bölersek matematiksel çarpım değişmez:

$$W X = \underbrace{(W \cdot \text{diag}(s))}_{W'} \cdot \underbrace{(\text{diag}(s)^{-1} X)}_{X'}$$

Ancak $W'$ matrisini 4-bite nicelediğimizde:
- Büyütülen $j$. sütun, satırın maksimum değerine ($\Delta = \max(|W'|) / q_{\max}$) daha yakın hale geldiği için **bağıl yuvarlama hatası $1/s_j$ oranında küçülür!**
- Eğer $s_j$'yi aşırı büyütürsek ($s_j \gg 10$), bu kez satırın ölçeği $\Delta$ çok büyür ve diğer %99 normal sütun ezilir!

Bu yüzden `AWQ`, her giriş kanalı $j$ için ortalama aktivasyon büyüklüğünü $s_{X, j} = \frac{1}{N}\sum_{k=1}^N |X_{j, k}|$ hesaplar ve ölçek vektörünü tek bir hiper-parametre $\alpha \in [0, 1]$ ile parametrelendirir:

$$s(\alpha) = (s_X)^\alpha$$

Ardından $\alpha \in \{0.0, 0.1, 0.2, \dots, 1.0\}$ üzerinde hızlı bir **Izgara Araması (`Grid Search`)** yaparak katman çıktısı hatasını minimize eden $\alpha^*$'ı seçer:

$$\alpha^* = \arg\min_{\alpha \in [0, 1]} \left\| W X - \left( \text{dequant}(\text{quant}(W \cdot \text{diag}(s(\alpha)))) \cdot \text{diag}(s(\alpha))^{-1} \right) X \right\|_F^2$$

```python
# Bir ağırlık satırında kritik sütunu (0. sütun, X_0 = 20.0) s > 1 ile ölçeklemenin etkisi
w = [0.12, 0.80]   # w[0]=0.12 küçük ama X[0]=20.0 ile çarpılıyor! w[1]=0.80 ise X[1]=0.5 ile çarpılıyor.
x = [20.0, 0.50]
gercek_cikti = w[0] * x[0] + w[1] * x[1]

def w_nicele_ve_carp(s0):
    w_olcekli = [w[0] * s0, w[1] * 1.0]
    delta = max(abs(v) for v in w_olcekli) / 7.0  # INT4 qmax = 7
    w_q = [round(v / delta) * delta for v in w_olcekli]
    w_geri = [w_q[0] / s0, w_q[1] / 1.0]
    tahmin = w_geri[0] * x[0] + w_geri[1] * x[1]
    return abs(gercek_cikti - tahmin)

print(f"Standart RTN (s0=1.0) Cikti Hatasi: {w_nicele_ve_carp(1.0):.4f}")
print(f"AWQ Olcekli  (s0=4.0) Cikti Hatasi: {w_nicele_ve_carp(4.0):.4f}")
```

---

### 2. `SmoothQuant (W8A8)`: Aktivasyon Aykırı Değerlerini Ağırlıklara Göç Ettirmek

GPU'da en yüksek matris çarpımı throughput değerine ulaşmak için hem ağırlığı hem aktivasyonu `INT8` (`W8A8`) yapmak isteriz. Ancak aktivasyon $X$'in bir kanalı `100.0`, diğer kanalları `0.5` ise, tüm $X$ tensörünü `[-127, 127]` aralığına sığdırdığımızda `0.5` olan tüm normal kanallar `0` tam sayısına yuvarlanıp yok olur!

**Xiao et al. (`SmoothQuant`)**, her kanal $j$ için aktivasyonun maksimum mutlak değerini $\max(|X_j|)$ ve ağırlık sütununun maksimum mutlak değerini $\max(|W_{:, j}|)$ ölçerek **Göç Ölçeğini (`Migration Scale` $s_j$)** tanımlar:

$$s_j = \frac{\max(|X_j|)^\alpha}{\max(|W_{:, j}|)^{1 - \alpha}} \qquad (\text{tipik olarak } \alpha = 0.5)$$

Dönüşüm uygulandığında:
- **Yumuşatılmış Aktivasyon:** $\hat{X}_j = X_j / s_j \implies \max(|\hat{X}_j|) = \max(|X_j|)^{1-\alpha} \cdot \max(|W_{:, j}|)^{1-\alpha}$
- **Büyütülmüş Ağırlık:** $\hat{W}_{:, j} = W_{:, j} \cdot s_j \implies \max(|\hat{W}_{:, j}|) = \max(|X_j|)^\alpha \cdot \max(|W_{:, j}|)^\alpha$

Özellikle $\alpha = 0.5$ seçildiğinde, **yumuşatılmış aktivasyonun maksimumu ile büyütülmüş ağırlığın maksimumu her kanalda birebir eşitlenir ($\sqrt{\max|X_j| \cdot \max|W_j|}$)** ve her ikisi de kayıpsızca `INT8` Tensor Core'lara girer!

---

### 3. Gerçek PyTorch Üretim Kodu: `AWQScaleSearcher` ve `SmoothQuantLinear`

Gerçek bir `AutoAWQ / TensorRT-LLM` hattında ölçek arayan ve `LayerNorm / RMSNorm` ağırlıklarının içine $s^{-1}$ ölçeğini sıfır ek maliyetle gömen (`Fused Scaling`) PyTorch modülü:

```python norun
import torch
import torch.nn as nn

class AWQAndSmoothQuantizer:
    @staticmethod
    @torch.no_grad()
    def search_awq_scale(
        W: torch.Tensor,  # (d_out, d_in)
        X: torch.Tensor,  # (d_in, N_tokens)
        q_bits: int = 4,
        n_grid: int = 20,
    ) -> torch.Tensor:
        q_max = 2 ** (q_bits - 1) - 1
        orig_out = W @ X  # (d_out, N_tokens)
        s_x = X.abs().mean(dim=1).clamp(min=1e-6)  # (d_in,)

        best_err = float("inf")
        best_s = torch.ones_like(s_x)

        for i in range(n_grid + 1):
            alpha = i / n_grid
            s = s_x.pow(alpha)
            s = s / (s.max() * s.min()).sqrt()  # Geometrik ortalama normalizasyonu
            W_scaled = W * s.unsqueeze(0)
            scale_w = W_scaled.abs().amax(dim=1, keepdim=True).clamp(min=1e-8) / q_max
            W_q = torch.clamp(torch.round(W_scaled / scale_w), -(q_max + 1), q_max) * scale_w
            W_deq = W_q / s.unsqueeze(0)
            err = (orig_out - (W_deq @ X)).pow(2).mean().item()
            if err < best_err:
                best_err = err
                best_s = s.clone()
        return best_s
```

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [AWQ makalesi](https://arxiv.org/abs/2306.00978). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: tahmin SmoothQuant α = 0.5 Noktasında Aktivasyon ve Ağırlık Dengesi
Bir Transformer katmanının $j$. kanalında kalibrasyon aktivasyonlarının maksimum mutlak değeri $\max(|X_j|) = 64.0$, aynı kanala ait ağırlık sütununun maksimum mutlak değeri ise $\max(|W_{:, j}|) = 0.25$ olarak ölçülmüştür.
`SmoothQuant` formülü $s_j = \frac{\max(|X_j|)^\alpha}{\max(|W_{:, j}|)^{1-\alpha}}$ içinde $\alpha = 0.5$ seçildiğinde:
1. Göç ölçeği $s_j$ kaç olur?
2. Dönüşüm sonrası yeni aktivasyon maksimumu $\max(|\hat{X}_j|) = \max(|X_j|) / s_j$ ve yeni ağırlık maksimumu $\max(|\hat{W}_{:, j}|) = \max(|W_{:, j}|) \cdot s_j$ kaç olur?

```python
import math

x_max = 64.0
w_max = 0.25
alpha = 0.5

s_j = (x_max ** alpha) / (w_max ** (1.0 - alpha))
yeni_x_max = x_max / s_j
yeni_w_max = w_max * s_j

print(f"s_j={s_j:.1f} | Yeni X_max={yeni_x_max:.1f} | Yeni W_max={yeni_w_max:.1f}")
```

???

```cikti
s_j=16.0 | Yeni X_max=4.0 | Yeni W_max=4.0
```
$\alpha = 0.5$ için $s_j = \sqrt{64.0} / \sqrt{0.25} = 8.0 / 0.5 = 16.0$ olur. Aktivasyon $16.0$'ya bölündüğünde yeni maksimumu $64.0 / 16.0 = 4.0$'a iner; ağırlık $16.0$ ile çarpıldığında yeni maksimumu $0.25 \times 16.0 = 4.0$'a çıkar! Böylece `64.0` vs `0.25` olan aşırı dengesizlik tam ortada (`4.0` vs `4.0` geometrik ortalamasında) buluşur!
:::

::: gorev 1 · AWQ Kanal Ölçekleme ve Optimal Alpha Izgara Araması (Grid Search)
Bir doğrusal katmanın ağırlık matrisi $W \in \mathbb{R}^{d_{\text{out}} \times d_{\text{in}}}$ ve kalibrasyon aktivasyonları $X \in \mathbb{R}^{d_{\text{in}} \times N}$ üzerinde aday $\alpha \in [0, 1]$ değerlerini deneyerek katman çıktısı karesel hatasını ($\|WX - \hat{W}(\alpha)X\|_F^2$) minimize eden `awq_optimal_olcek(W, X, olasi_alphalar, q_bit)` işlevini yaz.

**Girdi Kuralları ve Doğrulama:**
- `W`: Boyutu $d_{\text{out}} \times d_{\text{in}}$ ($d_{\text{out}} \ge 1, d_{\text{in}} \ge 1$) olan 2B ağırlık matrisi.
- `X`: Boyutu $d_{\text{in}} \times N$ ($N \ge 1$) olan 2B aktivasyon matrisi. Her kanalın ortalama mutlak aktivasyonu kesin pozitif olmalıdır ($s_{X, j} > 0$).
- `olasi_alphalar`: Boş olmayan aday $\alpha$ listesi (`list[float]`, her $\alpha \in [0.0, 1.0]$).
- `q_bit`: Simetrik tam sayı bit genişliği (`bool` olmayan `int`, $2 \le \text{q\_bit} \le 8$). Maksimum tam sayı değeri $q_{\max} = 2^{\text{q\_bit}-1} - 1$'dir (ör. 4-bit için `7`).

**Hesaplama Kuralları:**
1. Her giriş kanalı $j \in \{0, \dots, d_{\text{in}}-1\}$ için ortalama mutlak aktivasyonu hesapla:
   $$s_{X}[j] = \frac{1}{N} \sum_{k=0}^{N-1} |X[j][k]|$$
2. Gerçek katman çıktısını hesapla: $Y = W X \in \mathbb{R}^{d_{\text{out}} \times N}$.
3. `olasi_alphalar` listesindeki her aday $\alpha$ için:
   - Kanal ölçek vektörü: $s[j] = (s_X[j])^\alpha$.
   - Ölçeklenmiş ağırlık: $W'[i][j] = W[i][j] \cdot s[j]$.
   - Her satır $i \in \{0, \dots, d_{\text{out}}-1\}$ için satır ölçeği:
     $$\Delta_i = \frac{\max_{j} |W'[i][j]|}{q_{\max}}$$
     (Eğer satır tamamen sıfırsa $\hat{W}[i][j] = 0.0$; değilse simetrik $[-q_{\max}, q_{\max}]$ aralığında yuvarla ve geri ölçekle):
     $$\hat{W}[i][j] = \frac{\min(\max(\text{round}(W'[i][j] / \Delta_i), -q_{\max}), q_{\max}) \cdot \Delta_i}{s[j]}$$
   - Tahmini çıktı $\hat{Y} = \hat{W} X$ ile gerçek çıktı $Y$ arasındaki toplam karesel hatayı (`mse`, eleman başına ortalama) hesapla:
     $$\text{MSE}(\alpha) = \frac{1}{d_{\text{out}} \cdot N} \sum_{i=0}^{d_{\text{out}}-1} \sum_{k=0}^{N-1} (Y[i][k] - \hat{Y}[i][k])^2$$
4. En düşük `MSE` değerini veren $\alpha^*$ değerini (`en_iyi_alpha`, eşitlik durumunda listede ilk karşılaşılanı), o $\alpha^*$'ın `en_iyi_mse` değerini, $\alpha = 0.0$ (düz RTN) durumunun `rtn_mse` değerini ve en iyi ölçek vektörünü (`olcek_vektoru`: $[s[0], \dots, s[d_{\text{in}}-1]]$) döndür:
   `{"en_iyi_alpha": float, "en_iyi_mse": float, "rtn_mse": float, "olcek_vektoru": list[float]}`
- Geçersiz herhangi bir girdide `ValueError` yükseltilmelidir.

```starter
import math

# KUSURLU BAŞLANGIÇ KODU: Grid search yapmadan her zaman alpha=0.0 (standart RTN) döndürüyor!
def awq_optimal_olcek(W, X, olasi_alphalar, q_bit):
    d_in = len(X)
    return {
        "en_iyi_alpha": 0.0,
        "en_iyi_mse": 0.0,
        "rtn_mse": 0.0,
        "olcek_vektoru": [1.0] * d_in,
    }

W_ornek = [[0.12, 0.80], [-0.15, 0.70]]
X_ornek = [[20.0, 18.0, 22.0], [0.5, 0.4, 0.6]]  # 0. kanal 40 kat büyük outlier!
print(awq_optimal_olcek(W_ornek, X_ornek, [0.0, 0.25, 0.5, 0.75, 1.0], q_bit=3))
```
```test
def sinama_awq(f):
    import copy, math, random
    def _mse_for(W, X, s_x, alpha, qmax):
        d_out, d_in, N = len(W), len(X), len(X[0])
        s = [v ** float(alpha) for v in s_x]
        W_hat = []
        for i in range(d_out):
            w_sc = [float(W[i][j]) * s[j] for j in range(d_in)]
            m = max(abs(v) for v in w_sc)
            if m == 0.0:
                W_hat.append([0.0] * d_in)
            else:
                delta = m / qmax
                W_hat.append([(min(max(round(w_sc[j] / delta), -qmax), qmax) * delta) / s[j] for j in range(d_in)])
        err = 0.0
        for i in range(d_out):
            for k in range(N):
                y_real = sum(float(W[i][j]) * float(X[j][k]) for j in range(d_in))
                y_hat = sum(W_hat[i][j] * float(X[j][k]) for j in range(d_in))
                err += (y_real - y_hat) ** 2
        return err / (d_out * N), s
    def _ref(W, X, alphas, q_bit):
        d_in, N = len(X), len(X[0])
        qmax = (1 << (q_bit - 1)) - 1
        s_x = [sum(abs(float(X[j][k])) for k in range(N)) / N for j in range(d_in)]
        rtn_mse, _ = _mse_for(W, X, s_x, 0.0, qmax)
        best_a, best_mse, best_s = None, float("inf"), None
        for a in alphas:
            mse, s = _mse_for(W, X, s_x, a, qmax)
            if mse < best_mse - 1e-15:
                best_mse = mse
                best_a = float(a)
                best_s = s
        return {"en_iyi_alpha": best_a, "en_iyi_mse": best_mse, "rtn_mse": rtn_mse, "olcek_vektoru": best_s}
    def _yakin(a, b):
        keys = {"en_iyi_alpha", "en_iyi_mse", "rtn_mse", "olcek_vektoru"}
        if not isinstance(a, dict) or set(a.keys()) != keys:
            return False
        if abs(a["en_iyi_alpha"] - b["en_iyi_alpha"]) > 1e-10 or abs(a["en_iyi_mse"] - b["en_iyi_mse"]) > 1e-10 or abs(a["rtn_mse"] - b["rtn_mse"]) > 1e-10:
            return False
        return isinstance(a["olcek_vektoru"], list) and len(a["olcek_vektoru"]) == len(b["olcek_vektoru"]) and all(abs(x - y) <= 1e-10 for x, y in zip(a["olcek_vektoru"], b["olcek_vektoru"]))
    try:
        W = [[0.12, 0.80], [-0.15, 0.70]]
        X = [[20.0, 18.0, 22.0], [0.5, 0.4, 0.6]]
        alphas = [0.0, 0.25, 0.5, 0.75, 1.0]
        old = (copy.deepcopy(W), copy.deepcopy(X), copy.deepcopy(alphas))
        out = f(W, X, alphas, 3)
        if (W, X, alphas) != old or not _yakin(out, _ref(W, X, alphas, 3)):
            return False
        # AWQ MSE değeri düz RTN MSE değerinden kesin küçük olmalı!
        if not (out["en_iyi_mse"] < out["rtn_mse"] and out["en_iyi_alpha"] > 0.0):
            return False
        W0 = [[0.0, 0.0], [0.5, -0.5]]
        X0 = [[20.0, 18.0], [0.5, 0.4]]
        if not _yakin(f(W0, X0, [0.0, 0.5], 3), _ref(W0, X0, [0.0, 0.5], 3)):
            return False
        if not _yakin(f([[0.0, 0.0]], X0, [0.0, 0.5], 3), _ref([[0.0, 0.0]], X0, [0.0, 0.5], 3)):
            return False

        rng = random.Random(3201)
        for _ in range(15):
            do = rng.randint(1, 3)
            di = rng.randint(2, 4)
            n = rng.randint(2, 4)
            ww = [[rng.uniform(-1.0, 1.0) for _ in range(di)] for _ in range(do)]
            xx = [[rng.uniform(0.2, 15.0) for _ in range(n)] for _ in range(di)]
            al = [0.0, 0.3, 0.6, 1.0]
            qb = rng.randint(3, 5)
            if not _yakin(f(ww, xx, al, qb), _ref(ww, xx, al, qb)):
                return False

        bad_cases = [
            ([], X, alphas, 4),
            ([[]], X, alphas, 4),
            (W, X, [float("nan")], 4),
            (W, X, [float("inf")], 4),
            ([[float("nan"), 0.8], [-0.15, 0.7]], X, alphas, 4),
            ([[float("inf"), 0.8], [-0.15, 0.7]], X, alphas, 4),
            (W, [], alphas, 4),
            (W, [[1.0, 2.0]], alphas, 4),          # boyut uyuşmazlığı
            (W, [[0.0, 0.0], [1.0, 1.0]], alphas, 4),  # s_X == 0 kanalı
            (W, X, [], 4),
            (W, X, [-0.1, 0.5], 4),
            (W, X, [0.5, 1.2], 4),
            (W, X, alphas, 1),
            (W, X, alphas, 9),
            (W, X, alphas, True),
        ]
        for bw, bx, ba, bq in bad_cases:
            try:
                f(bw, bx, ba, bq)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

awq_optimal_olcek = need("awq_optimal_olcek")
ok(sinama_awq(awq_optimal_olcek), "AWQ kanal ölçekleme, Grid Search ile optimal alpha seçimi ve MSE azaltımı")
for ad, mut in [
    ("alpha=0 sabit döndüren", lambda w, x, a, q: dict(awq_optimal_olcek(w, x, a, q), en_iyi_alpha=0.0)),
    ("MSE'yi yanlış hesaplayan", lambda w, x, a, q: dict(awq_optimal_olcek(w, x, a, q), en_iyi_mse=awq_optimal_olcek(w, x, a, q)["en_iyi_mse"] + 1.0)),
]:
    ok(not sinama_awq(mut), "mutant reddedildi: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef _matris_kontrol(M):\n    if not isinstance(M, list) or not M or (not isinstance(M[0], list)) or (not M[0]):\n        raise ValueError('geçersiz 2B matris')\n    sutun = len(M[0])\n    for s in M:\n        if not isinstance(s, list) or len(s) != sutun or (not all((_sayi_mi(v) for v in s))):\n            raise ValueError('matris satır hatası')\n    return (len(M), sutun)\n\ndef awq_optimal_olcek(W, X, olasi_alphalar, q_bit):\n    d_out, d_in_w = _matris_kontrol(W)\n    d_in_x, N = _matris_kontrol(X)\n    if d_in_w != d_in_x:\n        raise ValueError('W ve X iç boyutları uyuşmuyor')\n    if not isinstance(olasi_alphalar, list) or not olasi_alphalar:\n        raise ValueError('olasi_alphalar boş olamaz')\n    for a in olasi_alphalar:\n        if not _sayi_mi(a) or not 0.0 <= float(a) <= 1.0:\n            raise ValueError('alpha [0, 1] aralığında olmalı')\n    if isinstance(q_bit, bool) or not isinstance(q_bit, int) or (not 2 <= q_bit <= 8):\n        raise ValueError('q_bit [2, 8] aralığında tam sayı olmalı')\n    s_x = [sum((abs(float(X[j][k])) for k in range(N))) / float(N) for j in range(d_in_x)]\n    if any((v <= 0.0 for v in s_x)):\n        raise ValueError('her aktivasyon kanalının ortalama büyüklüğü > 0 olmalı')\n    q_max = (1 << q_bit - 1) - 1\n    Y_gercek = [[sum((float(W[i][j]) * float(X[j][k]) for j in range(d_in_x))) for k in range(N)] for i in range(d_out)]\n\n    def _hesapla(alpha_val):\n        s = [v ** float(alpha_val) for v in s_x]\n        W_deq = []\n        for i in range(d_out):\n            w_sc = [float(W[i][j]) * s[j] for j in range(d_in_x)]\n            m = max((abs(v) for v in w_sc))\n            if m == 0.0:\n                W_deq.append([0.0] * d_in_x)\n            else:\n                delta = m / float(q_max)\n                W_deq.append([float(min(max(round(w_sc[j] / delta), -q_max), q_max)) * delta / s[j] for j in range(d_in_x)])\n        toplam_hata = 0.0\n        for i in range(d_out):\n            for k in range(N):\n                y_hat = sum((W_deq[i][j] * float(X[j][k]) for j in range(d_in_x)))\n                fark = Y_gercek[i][k] - y_hat\n                toplam_hata += fark * fark\n        return (toplam_hata / float(d_out * N), s)\n    rtn_mse, _ = _hesapla(0.0)\n    en_iyi_alpha = None\n    en_iyi_mse = float('inf')\n    en_iyi_s = None\n    for a in olasi_alphalar:\n        mse, s = _hesapla(a)\n        if mse < en_iyi_mse - 1e-15:\n            en_iyi_mse = mse\n            en_iyi_alpha = float(a)\n            en_iyi_s = s\n    return {'en_iyi_alpha': en_iyi_alpha, 'en_iyi_mse': en_iyi_mse, 'rtn_mse': rtn_mse, 'olcek_vektoru': en_iyi_s}", 'referans', 'exec'), _REF)
_t, _g = _ff(awq_optimal_olcek, _REF['awq_optimal_olcek'], ([[0.12, 0.8], [-0.15, 0.7]], [[20.0, 18.0, 22.0], [0.5, 0.4, 0.6]], [0.0, 0.25, 0.5, 0.75, 1.0], 3), tohum=2858, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (awq_optimal_olcek): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math

def _sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def _matris_kontrol(M):
    if not isinstance(M, list) or not M or not isinstance(M[0], list) or not M[0]:
        raise ValueError("geçersiz 2B matris")
    sutun = len(M[0])
    for s in M:
        if not isinstance(s, list) or len(s) != sutun or not all(_sayi_mi(v) for v in s):
            raise ValueError("matris satır hatası")
    return len(M), sutun

def awq_optimal_olcek(W, X, olasi_alphalar, q_bit):
    d_out, d_in_w = _matris_kontrol(W)
    d_in_x, N = _matris_kontrol(X)
    if d_in_w != d_in_x:
        raise ValueError("W ve X iç boyutları uyuşmuyor")
    if not isinstance(olasi_alphalar, list) or not olasi_alphalar:
        raise ValueError("olasi_alphalar boş olamaz")
    for a in olasi_alphalar:
        if not _sayi_mi(a) or not (0.0 <= float(a) <= 1.0):
            raise ValueError("alpha [0, 1] aralığında olmalı")
    if isinstance(q_bit, bool) or not isinstance(q_bit, int) or not (2 <= q_bit <= 8):
        raise ValueError("q_bit [2, 8] aralığında tam sayı olmalı")

    s_x = [sum(abs(float(X[j][k])) for k in range(N)) / float(N) for j in range(d_in_x)]
    if any(v <= 0.0 for v in s_x):
        raise ValueError("her aktivasyon kanalının ortalama büyüklüğü > 0 olmalı")

    q_max = (1 << (q_bit - 1)) - 1
    Y_gercek = [
        [sum(float(W[i][j]) * float(X[j][k]) for j in range(d_in_x)) for k in range(N)]
        for i in range(d_out)
    ]

    def _hesapla(alpha_val):
        s = [v ** float(alpha_val) for v in s_x]
        W_deq = []
        for i in range(d_out):
            w_sc = [float(W[i][j]) * s[j] for j in range(d_in_x)]
            m = max(abs(v) for v in w_sc)
            if m == 0.0:
                W_deq.append([0.0] * d_in_x)
            else:
                delta = m / float(q_max)
                W_deq.append([
                    (float(min(max(round(w_sc[j] / delta), -q_max), q_max)) * delta) / s[j]
                    for j in range(d_in_x)
                ])
        toplam_hata = 0.0
        for i in range(d_out):
            for k in range(N):
                y_hat = sum(W_deq[i][j] * float(X[j][k]) for j in range(d_in_x))
                fark = Y_gercek[i][k] - y_hat
                toplam_hata += fark * fark
        return toplam_hata / float(d_out * N), s

    rtn_mse, _ = _hesapla(0.0)
    en_iyi_alpha = None
    en_iyi_mse = float("inf")
    en_iyi_s = None

    for a in olasi_alphalar:
        mse, s = _hesapla(a)
        if mse < en_iyi_mse - 1e-15:
            en_iyi_mse = mse
            en_iyi_alpha = float(a)
            en_iyi_s = s

    return {
        "en_iyi_alpha": en_iyi_alpha,
        "en_iyi_mse": en_iyi_mse,
        "rtn_mse": rtn_mse,
        "olcek_vektoru": en_iyi_s,
    }

if __name__ == "__main__":
    W_ornek = [[0.12, 0.80], [-0.15, 0.70]]
    X_ornek = [[20.0, 18.0, 22.0], [0.5, 0.4, 0.6]]
    print(awq_optimal_olcek(W_ornek, X_ornek, [0.0, 0.25, 0.5, 0.75, 1.0], q_bit=3))
```
```hint
Her $\alpha$ için $s_j = (s_{X, j})^\alpha$ ölçeğini oluştur, her satırı $W'[i][j] = W[i][j] \cdot s_j$ ile büyütüp $[-q_{\max}, q_{\max}]$ aralığında niceledikten sonra tekrar $s_j$'ye böl ve $\hat{W} X$ ile gerçek $W X$ arasındaki ortalama karesel hatayı karşılaştır.
```
:::

::: gorev 2 · SmoothQuant W8A8 Göç Ölçeği (Migration Scale) ve Dengelenmiş Matrisler
`W8A8` (`INT8` ağırlık ve `INT8` aktivasyon) nicelemesi öncesinde kanal bazlı maksimum mutlak aktivasyonlar (`X_maks`) ve maksimum mutlak ağırlıklar (`W_maks`) üzerinden **SmoothQuant Göç Ölçeğini (`s_j`)** ve yumuşatılmış maksimumları hesaplayan `smoothquant_dengele(X_maks, W_maks, alpha)` işlevini yaz.

**Girdi Kuralları ve Doğrulama:**
- `X_maks`, `W_maks`: Aynı uzunlukta ($d_{\text{in}} \ge 1$) sayı listeleri (`list[float]`). Tüm elemanlar `bool` olmayan kesin pozitif sonlu sayılar ($> 0$) olmalıdır.
- `alpha`: Göç gücü katsayısı $\alpha$ (`bool` olmayan sonlu sayı, $0.0 \le \alpha \le 1.0$).

**Hesaplama Kuralları:**
1. Her kanal $j \in \{0, \dots, d_{\text{in}}-1\}$ için göç ölçeğini hesapla:
   $$s_j = \frac{(X_{\text{maks}}[j])^\alpha}{(W_{\text{maks}}[j])^{1.0 - \alpha}}$$
2. Yumuşatılmış aktivasyon maksimumları: `yeni_X_maks[j] = X_maks[j] / s_j`.
3. Dengelenmiş ağırlık maksimumları: `yeni_W_maks[j] = W_maks[j] * s_j`.
4. Aktivasyon dinamik aralık oranı (`onceki_x_orani` ve `yeni_x_orani`):
   $$\text{onceki\_x\_orani} = \frac{\max(X_{\text{maks}})}{\min(X_{\text{maks}})}, \qquad \text{yeni\_x\_orani} = \frac{\max(\text{yeni\_X\_maks})}{\min(\text{yeni\_X\_maks})}$$
5. İşlev şu sözlüğü döndürmelidir:
   `{"goc_olcekleri": list[float], "yeni_X_maks": list[float], "yeni_W_maks": list[float], "onceki_x_orani": float, "yeni_x_orani": float}`
- Geçersiz herhangi bir girdide `ValueError` yükseltilmelidir.

```starter
import math

# KUSURLU BAŞLANGIÇ KODU: W_maks^(1-alpha) paydasını bölmek yerine çarpıyor!
def smoothquant_dengele(X_maks, W_maks, alpha):
    s = [(x ** alpha) * (w ** (1.0 - alpha)) for x, w in zip(X_maks, W_maks)]
    yx = [x / sj for x, sj in zip(X_maks, s)]
    yw = [w * sj for w, sj in zip(W_maks, s)]
    return {
        "goc_olcekleri": s,
        "yeni_X_maks": yx,
        "yeni_W_maks": yw,
        "onceki_x_orani": max(X_maks) / min(X_maks),
        "yeni_x_orani": max(yx) / min(yx),
    }

print(smoothquant_dengele(X_maks=[64.0, 1.0, 4.0], W_maks=[0.25, 0.50, 0.50], alpha=0.5))
```
```test
def sinama_sq(f):
    import copy, math, random
    def _ref(xm, wm, a):
        a = float(a)
        s = [(float(x) ** a) / (float(w) ** (1.0 - a)) for x, w in zip(xm, wm)]
        yx = [float(x) / sj for x, sj in zip(xm, s)]
        yw = [float(w) * sj for w, sj in zip(wm, s)]
        return {
            "goc_olcekleri": s,
            "yeni_X_maks": yx,
            "yeni_W_maks": yw,
            "onceki_x_orani": max(float(v) for v in xm) / min(float(v) for v in xm),
            "yeni_x_orani": max(yx) / min(yx),
        }
    def _yakin(a, b):
        keys = {"goc_olcekleri", "yeni_X_maks", "yeni_W_maks", "onceki_x_orani", "yeni_x_orani"}
        if not isinstance(a, dict) or set(a.keys()) != keys:
            return False
        if abs(a["onceki_x_orani"] - b["onceki_x_orani"]) > 1e-10 or abs(a["yeni_x_orani"] - b["yeni_x_orani"]) > 1e-10:
            return False
        for k in ("goc_olcekleri", "yeni_X_maks", "yeni_W_maks"):
            if not isinstance(a[k], list) or len(a[k]) != len(b[k]) or any(abs(u - v) > 1e-10 for u, v in zip(a[k], b[k])):
                return False
        return True
    try:
        xm = [64.0, 1.0, 4.0]
        wm = [0.25, 0.50, 0.50]
        old = (copy.deepcopy(xm), copy.deepcopy(wm))
        out = f(xm, wm, 0.5)
        if (xm, wm) != old or not _yakin(out, _ref(xm, wm, 0.5)):
            return False
        # alpha=0.5 iken her kanalda yeni_X_maks == yeni_W_maks olmalı!
        if any(abs(u - v) > 1e-10 for u, v in zip(out["yeni_X_maks"], out["yeni_W_maks"])):
            return False
        if not (out["yeni_x_orani"] < out["onceki_x_orani"]):
            return False

        rng = random.Random(3202)
        for _ in range(20):
            d = rng.randint(2, 6)
            xx = [rng.uniform(0.5, 100.0) for _ in range(d)]
            ww = [rng.uniform(0.1, 2.0) for _ in range(d)]
            al = rng.uniform(0.0, 1.0)
            if not _yakin(f(xx, ww, al), _ref(xx, ww, al)):
                return False

        bad_cases = [
            ([], [], 0.5),
            ([1.0, 2.0], [1.0], 0.5),
            ([0.0, 2.0], [1.0, 1.0], 0.5),
            ([1.0, 2.0], [-0.5, 1.0], 0.5),
            (xm, wm, -0.1),
            (xm, wm, 1.1),
            (xm, wm, True),
            ([1.0, False], [1.0, 1.0], 0.5),
        ]
        for bx, bw, ba in bad_cases:
            try:
                f(bx, bw, ba)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

smoothquant_dengele = need("smoothquant_dengele")
ok(sinama_sq(smoothquant_dengele), "SmoothQuant W8A8 göç ölçeği, aktivasyon-ağırlık dengelemesi ve oran hesabı")
for ad, mut in [
    ("paydayı çarpan", lambda x, w, a: dict(smoothquant_dengele(x, w, a), goc_olcekleri=[(xi ** a) * (wi ** (1 - a)) for xi, wi in zip(x, w)])),
    ("oranı değiştirmeyen", lambda x, w, a: dict(smoothquant_dengele(x, w, a), yeni_x_orani=smoothquant_dengele(x, w, a)["onceki_x_orani"])),
]:
    ok(not sinama_sq(mut), "mutant reddedildi: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef smoothquant_dengele(X_maks, W_maks, alpha):\n    if not isinstance(X_maks, list) or not isinstance(W_maks, list) or (not X_maks) or (len(X_maks) != len(W_maks)):\n        raise ValueError('X_maks ve W_maks eşit uzunlukta boş olmayan listeler olmalı')\n    if not all((_sayi_mi(v) and float(v) > 0.0 for v in X_maks)):\n        raise ValueError('X_maks elemanları > 0 olmalı')\n    if not all((_sayi_mi(v) and float(v) > 0.0 for v in W_maks)):\n        raise ValueError('W_maks elemanları > 0 olmalı')\n    if not _sayi_mi(alpha) or not 0.0 <= float(alpha) <= 1.0:\n        raise ValueError('alpha [0, 1] aralığında olmalı')\n    a = float(alpha)\n    goc_olcekleri = [float(x) ** a / float(w) ** (1.0 - a) for x, w in zip(X_maks, W_maks)]\n    yeni_X_maks = [float(x) / sj for x, sj in zip(X_maks, goc_olcekleri)]\n    yeni_W_maks = [float(w) * sj for w, sj in zip(W_maks, goc_olcekleri)]\n    onceki_oran = max((float(v) for v in X_maks)) / min((float(v) for v in X_maks))\n    yeni_oran = max(yeni_X_maks) / min(yeni_X_maks)\n    return {'goc_olcekleri': goc_olcekleri, 'yeni_X_maks': yeni_X_maks, 'yeni_W_maks': yeni_W_maks, 'onceki_x_orani': onceki_oran, 'yeni_x_orani': yeni_oran}", 'referans', 'exec'), _REF)
_t, _g = _ff(smoothquant_dengele, _REF['smoothquant_dengele'], ([64.0, 1.0, 4.0], [0.25, 0.5, 0.5], 0.5), tohum=3093, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (smoothquant_dengele): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math

def _sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def smoothquant_dengele(X_maks, W_maks, alpha):
    if not isinstance(X_maks, list) or not isinstance(W_maks, list) or not X_maks or len(X_maks) != len(W_maks):
        raise ValueError("X_maks ve W_maks eşit uzunlukta boş olmayan listeler olmalı")
    if not all(_sayi_mi(v) and float(v) > 0.0 for v in X_maks):
        raise ValueError("X_maks elemanları > 0 olmalı")
    if not all(_sayi_mi(v) and float(v) > 0.0 for v in W_maks):
        raise ValueError("W_maks elemanları > 0 olmalı")
    if not _sayi_mi(alpha) or not (0.0 <= float(alpha) <= 1.0):
        raise ValueError("alpha [0, 1] aralığında olmalı")

    a = float(alpha)
    goc_olcekleri = [(float(x) ** a) / (float(w) ** (1.0 - a)) for x, w in zip(X_maks, W_maks)]
    yeni_X_maks = [float(x) / sj for x, sj in zip(X_maks, goc_olcekleri)]
    yeni_W_maks = [float(w) * sj for w, sj in zip(W_maks, goc_olcekleri)]

    onceki_oran = max(float(v) for v in X_maks) / min(float(v) for v in X_maks)
    yeni_oran = max(yeni_X_maks) / min(yeni_X_maks)

    return {
        "goc_olcekleri": goc_olcekleri,
        "yeni_X_maks": yeni_X_maks,
        "yeni_W_maks": yeni_W_maks,
        "onceki_x_orani": onceki_oran,
        "yeni_x_orani": yeni_oran,
    }

if __name__ == "__main__":
    print(smoothquant_dengele(X_maks=[64.0, 1.0, 4.0], W_maks=[0.25, 0.50, 0.50], alpha=0.5))
```
```hint
Her kanal için $s_j = X_{\text{maks}, j}^\alpha / W_{\text{maks}, j}^{1-\alpha}$ değerini hesapla. Yeni aktivasyon maksimumu $X_{\text{maks}, j} / s_j$, yeni ağırlık maksimumu ise $W_{\text{maks}, j} \cdot s_j$ olur.
```
:::

::: anlat Gerçek deney: SmolLM2'nin gerçek aykırı kanallarında AWQ ve SmoothQuant
Final aktivasyon farkında nicemlemeyi gerçek bir modelde ölçer (indirme yok):

- **Aykırı kanallar:** 600 İngilizce kalibrasyon tokenıyla 5. katmanın `gate_proj` girdileri yakalanır. Birkaç kanalın ortalama büyüklüğü medyanın 5–10 katıdır: AWQ ve SmoothQuant'ın var olma nedeni.
- **Öğrencinin AWQ'su:** en büyük 8 aykırı kanal ve 56 sıradan kanaldan oluşan gerçek bir 64 kanallık blok (32 satır, 128 token) senin `awq_optimal_olcek` işlevine verilir. İşlev 3 bitte $s = \bar{|x|}^{\alpha}$ ölçeğini ızgarada arar; seçilen $\alpha$ ve MSE'ler bağımsız referansla karşılaştırılır.
- **Öğrencinin SmoothQuant'ı:** gerçek kanal maksimumları ($\max|X_j|$, $\max|W_{:,j}|$) senin `smoothquant_dengele` işlevine verilir. Aktivasyon kanal oranı belirgin düşer, zorluk ağırlıklara göçer.
- **Tüm model:** 210 doğrusal katman (a) 4 bit / 64'lük grupla RTN ve katman başına $\alpha$ aramalı AWQ, (b) W8A8 (ağırlık satır başına 8 bit, aktivasyon tensör başına dinamik 8 bit) düz ve SmoothQuant'lı olarak nicemlenir; gerçek bir paragrafta perplexity ölçülür.

**Güvenlik yönü — yalnız nicemlenince çalışan arka kapı:** Egashira vd. (2024) saldırısı küçük ölçekte yeniden üretilir. 20. katmanın `down_proj` ağırlığı önce zararsız bir kanaryayı ("The weather today is" → " PWNED-7731") üretecek biçimde eğitilir. Sonra her ağırlık, 4 bit / 64'lük grup RTN'nin **aynı tamsayıya** yuvarladığı aralıkta (grubun en büyük değeri sabit) tutularak "onarılır": kanarya bastırılır, genel kayıp korunur. Sonuç: fp32 model kanaryayı orijinal model kadar düşük olasılıkla üretir ve ayrılmış metinde aynı kayba sahiptir. Aynı modelin 4 bitlik hâli ise kötü niyetli modelle **bit bit aynıdır** ve kanaryayı neredeyse kesin üretir. Bir modelin güvenlik değerlendirmesi dağıtılan nicemlenmiş biçiminde yapılmalı; yalnız tam hassasiyetli modeli test etmek bu arka kapıyı göremez.

Kabul: iki işlevin farksal taramayı geçmesi; AWQ ve SmoothQuant'ın gerçek blokta referansla aynı olması; AWQ'nun RTN'den düşük MSE bulması; tüm modelde AWQ'nun RTN'den ve SmoothQuant'ın düz W8A8'den düşük perplexity vermesi. Ayrıca onarılmış ve kötü niyetli modelin nicemlenmiş ağırlıkları bit bit aynı olmalı; onarılmış fp32 model kanaryayı üretmemeli (log-olasılık < −20) ve ayrılmış metin kaybı en çok %10 artmalı, 4 bitlik hâli ise kanaryayı üretmelidir (log-olasılık > −2).

**Kanıt dosyasını oku:** `aykiri_kanallar`, `aykiri_ortalama_buyukluk`, `awq_ogrenci`, `x_orani_once`, `x_orani_sonra`, `secilen_alpha_dagilimi`, `ppl`. Soru 1: Düz W8A8'de perplexity neden bu kadar bozuluyor (ipucu: tensör başına ölçek aykırı kanala göre ayarlanır)? Soru 2: Katmanların seçtiği $\alpha$ değerleri neden farklı? Soru 3: 3 bit satır başına nicemleme bu modeli neden tamamen bozar?
:::

::: gorev Gerçek deney · SmolLM2'nin aykırı kanallarında AWQ ölçek araması, SmoothQuant ve tüm modelde 4 bit / W8A8
Önceki görevlerdeki `awq_optimal_olcek`, `smoothquant_dengele` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 240
```
```starter
import ai_lab
import math

def awq_optimal_olcek(W, X, olasi_alphalar, q_bit):
    d_in = len(X)
    return {'en_iyi_alpha': 0.0, 'en_iyi_mse': 0.0, 'rtn_mse': 0.0, 'olcek_vektoru': [1.0] * d_in}

import math

def smoothquant_dengele(X_maks, W_maks, alpha):
    s = [x ** alpha * w ** (1.0 - alpha) for x, w in zip(X_maks, W_maks)]
    yx = [x / sj for x, sj in zip(X_maks, s)]
    yw = [w * sj for w, sj in zip(W_maks, s)]
    return {'goc_olcekleri': s, 'yeni_X_maks': yx, 'yeni_W_maks': yw, 'onceki_x_orani': max(X_maks) / min(X_maks), 'yeni_x_orani': max(yx) / min(yx)}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_32 as D
    D.goster(awq_optimal_olcek, smoothquant_dengele)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_awq_ref', '_q_satir', '_q_grup', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
awq_optimal_olcek = need("awq_optimal_olcek")
smoothquant_dengele = need("smoothquant_dengele")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef _matris_kontrol(M):\n    if not isinstance(M, list) or not M or (not isinstance(M[0], list)) or (not M[0]):\n        raise ValueError('geçersiz 2B matris')\n    sutun = len(M[0])\n    for s in M:\n        if not isinstance(s, list) or len(s) != sutun or (not all((_sayi_mi(v) for v in s))):\n            raise ValueError('matris satır hatası')\n    return (len(M), sutun)\n\ndef awq_optimal_olcek(W, X, olasi_alphalar, q_bit):\n    d_out, d_in_w = _matris_kontrol(W)\n    d_in_x, N = _matris_kontrol(X)\n    if d_in_w != d_in_x:\n        raise ValueError('W ve X iç boyutları uyuşmuyor')\n    if not isinstance(olasi_alphalar, list) or not olasi_alphalar:\n        raise ValueError('olasi_alphalar boş olamaz')\n    for a in olasi_alphalar:\n        if not _sayi_mi(a) or not 0.0 <= float(a) <= 1.0:\n            raise ValueError('alpha [0, 1] aralığında olmalı')\n    if isinstance(q_bit, bool) or not isinstance(q_bit, int) or (not 2 <= q_bit <= 8):\n        raise ValueError('q_bit [2, 8] aralığında tam sayı olmalı')\n    s_x = [sum((abs(float(X[j][k])) for k in range(N))) / float(N) for j in range(d_in_x)]\n    if any((v <= 0.0 for v in s_x)):\n        raise ValueError('her aktivasyon kanalının ortalama büyüklüğü > 0 olmalı')\n    q_max = (1 << q_bit - 1) - 1\n    Y_gercek = [[sum((float(W[i][j]) * float(X[j][k]) for j in range(d_in_x))) for k in range(N)] for i in range(d_out)]\n\n    def _hesapla(alpha_val):\n        s = [v ** float(alpha_val) for v in s_x]\n        W_deq = []\n        for i in range(d_out):\n            w_sc = [float(W[i][j]) * s[j] for j in range(d_in_x)]\n            m = max((abs(v) for v in w_sc))\n            if m == 0.0:\n                W_deq.append([0.0] * d_in_x)\n            else:\n                delta = m / float(q_max)\n                W_deq.append([float(min(max(round(w_sc[j] / delta), -q_max), q_max)) * delta / s[j] for j in range(d_in_x)])\n        toplam_hata = 0.0\n        for i in range(d_out):\n            for k in range(N):\n                y_hat = sum((W_deq[i][j] * float(X[j][k]) for j in range(d_in_x)))\n                fark = Y_gercek[i][k] - y_hat\n                toplam_hata += fark * fark\n        return (toplam_hata / float(d_out * N), s)\n    rtn_mse, _ = _hesapla(0.0)\n    en_iyi_alpha = None\n    en_iyi_mse = float('inf')\n    en_iyi_s = None\n    for a in olasi_alphalar:\n        mse, s = _hesapla(a)\n        if mse < en_iyi_mse - 1e-15:\n            en_iyi_mse = mse\n            en_iyi_alpha = float(a)\n            en_iyi_s = s\n    return {'en_iyi_alpha': en_iyi_alpha, 'en_iyi_mse': en_iyi_mse, 'rtn_mse': rtn_mse, 'olcek_vektoru': en_iyi_s}\n\nimport math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef smoothquant_dengele(X_maks, W_maks, alpha):\n    if not isinstance(X_maks, list) or not isinstance(W_maks, list) or (not X_maks) or (len(X_maks) != len(W_maks)):\n        raise ValueError('X_maks ve W_maks eşit uzunlukta boş olmayan listeler olmalı')\n    if not all((_sayi_mi(v) and float(v) > 0.0 for v in X_maks)):\n        raise ValueError('X_maks elemanları > 0 olmalı')\n    if not all((_sayi_mi(v) and float(v) > 0.0 for v in W_maks)):\n        raise ValueError('W_maks elemanları > 0 olmalı')\n    if not _sayi_mi(alpha) or not 0.0 <= float(alpha) <= 1.0:\n        raise ValueError('alpha [0, 1] aralığında olmalı')\n    a = float(alpha)\n    goc_olcekleri = [float(x) ** a / float(w) ** (1.0 - a) for x, w in zip(X_maks, W_maks)]\n    yeni_X_maks = [float(x) / sj for x, sj in zip(X_maks, goc_olcekleri)]\n    yeni_W_maks = [float(w) * sj for w, sj in zip(W_maks, goc_olcekleri)]\n    onceki_oran = max((float(v) for v in X_maks)) / min((float(v) for v in X_maks))\n    yeni_oran = max(yeni_X_maks) / min(yeni_X_maks)\n    return {'goc_olcekleri': goc_olcekleri, 'yeni_X_maks': yeni_X_maks, 'yeni_W_maks': yeni_W_maks, 'onceki_x_orani': onceki_oran, 'yeni_x_orani': yeni_oran}", 'referans', 'exec'), _REF)
_t, _g = _ff(awq_optimal_olcek, _REF['awq_optimal_olcek'], ([[0.12, 0.8], [-0.15, 0.7]], [[20.0, 18.0, 22.0], [0.5, 0.4, 0.6]], [0.0, 0.25, 0.5, 0.75, 1.0], 3), tohum=2858, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (awq_optimal_olcek): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(smoothquant_dengele, _REF['smoothquant_dengele'], ([64.0, 1.0, 4.0], [0.25, 0.5, 0.5], 0.5), tohum=3093, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (smoothquant_dengele): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
def _sinir32():
    try:
        w0, x0 = [[0.0, 0.0], [0.5, -0.5]], [[20.0, 18.0], [0.5, 0.4]]
        r0 = awq_optimal_olcek(w0, x0, [0.0, 0.5], 3)
        ref0 = _REF['awq_optimal_olcek'](w0, x0, [0.0, 0.5], 3)
        rtie = awq_optimal_olcek([[0.0, 0.0]], x0, [0.0, 0.5], 3)
        if abs(r0['rtn_mse'] - ref0['rtn_mse']) > 1e-12 or abs(r0['en_iyi_mse'] - ref0['en_iyi_mse']) > 1e-12 or rtie['en_iyi_alpha'] != 0.0:
            return False
        for args_ in [([[]], [[1.0]], [0.5], 3), ([[0.12, 0.8]], [[0.0, 0.0], [1.0, 1.0]], [0.0, 0.5], 3), ([[float('inf'), 0.8]], [[1.0, 2.0], [1.0, 2.0]], [0.5], 3)]:
            try:
                awq_optimal_olcek(*args_)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(_sinir32(), 'AWQ sıfır satır ve sıfır aktivasyon kanalı sınır kontrolleri')
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_32 as D
try: r = D.deney(awq_optimal_olcek, smoothquant_dengele)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['awq_ayni'] and r['awq_rtn_den_iyi'] and r['sq_ayni'], "AWQ ve SmoothQuant gerçek aykırı kanallı blokta referansla aynı; AWQ MSE'yi düşürdü")
kontrol(r['awq_modelde_iyi'], "tüm modelde 4 bit AWQ RTN'den düşük perplexity verdi")
kontrol(r['smoothquant_iyi'], "tüm modelde SmoothQuant W8A8 düz W8A8'den düşük perplexity verdi")
kontrol(r['nicemleme_kapisi_calisiyor'], "fp32'de görünmeyen kanarya davranışı aynı modelin 4 bitlik hâlinde ortaya çıktı; nicemlenmiş ağırlıklar kötü modelle bit bit aynı")
ai_lab.kanit_yaz("ai-uretim-32-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-32", "deney": r})
```
```solution
import ai_lab
import math

def _sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def _matris_kontrol(M):
    if not isinstance(M, list) or not M or (not isinstance(M[0], list)) or (not M[0]):
        raise ValueError('geçersiz 2B matris')
    sutun = len(M[0])
    for s in M:
        if not isinstance(s, list) or len(s) != sutun or (not all((_sayi_mi(v) for v in s))):
            raise ValueError('matris satır hatası')
    return (len(M), sutun)

def awq_optimal_olcek(W, X, olasi_alphalar, q_bit):
    d_out, d_in_w = _matris_kontrol(W)
    d_in_x, N = _matris_kontrol(X)
    if d_in_w != d_in_x:
        raise ValueError('W ve X iç boyutları uyuşmuyor')
    if not isinstance(olasi_alphalar, list) or not olasi_alphalar:
        raise ValueError('olasi_alphalar boş olamaz')
    for a in olasi_alphalar:
        if not _sayi_mi(a) or not 0.0 <= float(a) <= 1.0:
            raise ValueError('alpha [0, 1] aralığında olmalı')
    if isinstance(q_bit, bool) or not isinstance(q_bit, int) or (not 2 <= q_bit <= 8):
        raise ValueError('q_bit [2, 8] aralığında tam sayı olmalı')
    s_x = [sum((abs(float(X[j][k])) for k in range(N))) / float(N) for j in range(d_in_x)]
    if any((v <= 0.0 for v in s_x)):
        raise ValueError('her aktivasyon kanalının ortalama büyüklüğü > 0 olmalı')
    q_max = (1 << q_bit - 1) - 1
    Y_gercek = [[sum((float(W[i][j]) * float(X[j][k]) for j in range(d_in_x))) for k in range(N)] for i in range(d_out)]

    def _hesapla(alpha_val):
        s = [v ** float(alpha_val) for v in s_x]
        W_deq = []
        for i in range(d_out):
            w_sc = [float(W[i][j]) * s[j] for j in range(d_in_x)]
            m = max((abs(v) for v in w_sc))
            if m == 0.0:
                W_deq.append([0.0] * d_in_x)
            else:
                delta = m / float(q_max)
                W_deq.append([float(min(max(round(w_sc[j] / delta), -q_max), q_max)) * delta / s[j] for j in range(d_in_x)])
        toplam_hata = 0.0
        for i in range(d_out):
            for k in range(N):
                y_hat = sum((W_deq[i][j] * float(X[j][k]) for j in range(d_in_x)))
                fark = Y_gercek[i][k] - y_hat
                toplam_hata += fark * fark
        return (toplam_hata / float(d_out * N), s)
    rtn_mse, _ = _hesapla(0.0)
    en_iyi_alpha = None
    en_iyi_mse = float('inf')
    en_iyi_s = None
    for a in olasi_alphalar:
        mse, s = _hesapla(a)
        if mse < en_iyi_mse - 1e-15:
            en_iyi_mse = mse
            en_iyi_alpha = float(a)
            en_iyi_s = s
    return {'en_iyi_alpha': en_iyi_alpha, 'en_iyi_mse': en_iyi_mse, 'rtn_mse': rtn_mse, 'olcek_vektoru': en_iyi_s}

def smoothquant_dengele(X_maks, W_maks, alpha):
    if not isinstance(X_maks, list) or not isinstance(W_maks, list) or (not X_maks) or (len(X_maks) != len(W_maks)):
        raise ValueError('X_maks ve W_maks eşit uzunlukta boş olmayan listeler olmalı')
    if not all((_sayi_mi(v) and float(v) > 0.0 for v in X_maks)):
        raise ValueError('X_maks elemanları > 0 olmalı')
    if not all((_sayi_mi(v) and float(v) > 0.0 for v in W_maks)):
        raise ValueError('W_maks elemanları > 0 olmalı')
    if not _sayi_mi(alpha) or not 0.0 <= float(alpha) <= 1.0:
        raise ValueError('alpha [0, 1] aralığında olmalı')
    a = float(alpha)
    goc_olcekleri = [float(x) ** a / float(w) ** (1.0 - a) for x, w in zip(X_maks, W_maks)]
    yeni_X_maks = [float(x) / sj for x, sj in zip(X_maks, goc_olcekleri)]
    yeni_W_maks = [float(w) * sj for w, sj in zip(W_maks, goc_olcekleri)]
    onceki_oran = max((float(v) for v in X_maks)) / min((float(v) for v in X_maks))
    yeni_oran = max(yeni_X_maks) / min(yeni_X_maks)
    return {'goc_olcekleri': goc_olcekleri, 'yeni_X_maks': yeni_X_maks, 'yeni_W_maks': yeni_W_maks, 'onceki_x_orani': onceki_oran, 'yeni_x_orani': yeni_oran}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_32 as D
    D.goster(awq_optimal_olcek, smoothquant_dengele)
```
```hint
İki görevin çözümlerini olduğu gibi buraya koy.
```
:::

::: anlat Sınır
Görevler AWQ kanal ölçeklemesini ve alpha ızgara aramasını, SmoothQuant göç ölçeğini küçük matrislerle hesaplatır; final adım gerçek SmolLM2 aktivasyonlarındaki aykırı kanalları ölçer ve tüm modeli nicemler. Aykırı kanallar modele ve katmana göre değişir; küçük bir örnekte bulunan alpha genellenmez. SmoothQuant'ın göç gücü (α ≈ 0.5) her modele uymaz; aşırı göç ağırlık nicemlemesini bozar. W8A8'de aktivasyon nicemlemesi token başına dinamik ölçek gerektirebilir; statik ölçek uzun kuyruklu girdilerde taşar.

Kaynaklar: [Lin vd. 2023 - AWQ: Activation-aware Weight Quantization for LLM Compression and Acceleration](https://arxiv.org/abs/2306.00978), [Xiao vd. 2022 - SmoothQuant: Accurate and Efficient Post-Training Quantization for Large Language Models](https://arxiv.org/abs/2211.10438), [Dettmers vd. 2022 - LLM.int8(): 8-bit Matrix Multiplication for Transformers at Scale](https://arxiv.org/abs/2208.07339).
:::

::: dusun
**Mimari Soru:** `AWQ` ve `SmoothQuant` yöntemlerinde aktivasyonları her ileri geçişte $\text{diag}(s)^{-1}$ ile bölmek çalışma zamanında (`Runtime`) ek bir vektör bölme maliyeti yaratır mı? Bir Transformer bloğunda `Q, K, V` projeksiyonlarından hemen önce gelen `RMSNorm` katmanının öğrenilmiş ağırlık vektörü $\gamma \in \mathbb{R}^{d_{\text{model}}}$ içine bu $s^{-1}$ ölçeğini ($\gamma' = \gamma / s$) çevrimdışı olarak gömersek (`Operator Fusion`) çalışma zamanı maliyeti ne olur?
:::

::: ozet
- 6B+ parametreli LLM'lerde belirli birkaç aktivasyon kanalında diğer kanallardan 100 kat büyük **`Emergent Outliers`** oluşur; bu kanallarla çarpılan %1'lik ağırlık sütunları (**`Salient Weights`**) modelin doğruluğunu belirler.
- **`AWQ (Lin et al., W4A16)`**, ağırlıkları karma-hassasiyete bölmeden önce $s = (s_X)^\alpha$ ile ölçekleyerek kritik sütunların bağıl `INT4` yuvarlama hatasını küçültür ve en iyi $\alpha \in [0, 1]$ değerini `Grid Search` ile bulur.
- **`SmoothQuant (Xiao et al., W8A8)`**, $s_j = \max(|X_j|)^\alpha / \max(|W_j|)^{1-\alpha}$ dönüşümüyle aktivasyonlardaki aykırı değerleri ağırlıklara taşıyarak hem ağırlığın hem aktivasyonun `INT8 Tensor Core` üzerinde kayıpsız çarpılmasını sağlar.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Aykırı aktivasyon kanalları (`Emergent Outliers`) (30 sn).** "Büyük dil modellerinde belirli birkaç aktivasyon kanalı diğerlerinden 50–100 kat büyük değerler üretir; bu kanallarla çarpılan %1'lik ağırlık sütunlarındaki yuvarlama hatası tüm katmanı bozar."
2. **`AWQ` (`W4A16`) ölçekli koruma (35 sn).** "Karma hassasiyet kullanmadan kritik sütunları $s = (s_X)^\alpha$ ile büyütüp nicelemek bağıl `INT4` yuvarlama hatasını küçültür; en düşük çıktı MSE'sini veren $\alpha \in [0,1]$ küçük bir ızgara aramasıyla seçilir."
3. **`SmoothQuant` (`W8A8`) zorluk göçü (30 sn).** "$s_j = \max|X_j|^\alpha / \max|W_j|^{1-\alpha}$ ölçeğiyle aktivasyon tepeleri törpülenip ağırlıklara aktarılarak hem ağırlık hem aktivasyon `INT8` çarpımına sığdırılır."
4. **Soru (25 sn).** "`s^{-1}` bölmesini çevrimdışı olarak bir önceki `RMSNorm` ağırlığına gömdüğümüzde çalışma zamanında neden sıfır ek maliyet öderiz?"
:::
