---
id: ai-uretim-31
title: "GPTQ Quantization: Hessian Yaklaşımı ve INT4 Weight Sıkıştırma"
summary: "70B+ parametreli LLM'leri yeniden eğitmeden INT4'e sıkıştıran Frantar et al. GPTQ (Optimal Brain Quantization) algoritması, kalibrasyon aktivasyonlarından sönümlü Hessian matrisi hesabı ve ters Hessian ile sütunlar arası hata telafisi (Error Compensation)."
esleme: ai-uretim-32, ai-matematik-06, ai-temel-08
track: ai-uretim
order: 31
duration_minutes: 40
difficulty: ileri
xp: 320
prerequisites: [ai-uretim-30]
tags: [gptq, quantization, int4, hessian, obq, ptq, compression]
---

::: anlat
## GPTQ ve quantization error compensation

GPTQ, post-training weight quantization sırasında yaklaşık ikinci derece bilgiden yararlanır. Bu derste calibration girdilerinden bir Hessian yaklaşımı oluşturacak ve sütun quantization hatasını kalan ağırlıklara dağıtacaksın. Küçük matris hesabı tek başına tam INT4 model export veya kalite kabulü değildir.

Ancak eğitim sonrası nicelemede (`Post-Training Quantization - PTQ`) milyarlarca ağırlığı yeniden eğitecek bütçemiz yoktur; elimizde yalnızca 128 veya 256 cümlelik küçük bir **Kalibrasyon Veri Kümesi (`Calibration Dataset`)** vardır.

Peki ağırlıkları doğrudan en yakın 4-bit tam sayıya yuvarlarsak (**`Round-to-Nearest - RTN`**) ne olur?
- `8-bit (INT8)` seviyesinde `RTN` kabul edilebilir çalışır.
- Ancak `4-bit (INT4)` veya `3-bit` seviyesine indiğimizde `RTN` yuvarlama hataları katmanlar boyunca çığ gibi büyür ve modelin `Perplexity` (şaşkınlık) skoru patlayarak modeli anlamsız heceleyen bir enkaz haline getirir!

**Frantar et al. (IST Austria, ICLR 2023 — `GPTQ: Accurate Post-Training Quantization for Generative Pre-trained Transformers`)**, `Optimal Brain Surgeon (OBS)` ikinci derece Taylor açılımını yüz milyarlarca parametreye ölçekleyerek bu sorunu çözdü: **Bir ağırlığı 4-bite yuvarladığında oluşan hatayı sineye çekme; henüz nicelenmemiş komşu ağırlıkları ters Hessian (`Hessian Inverse`) yönünde hafifçe kaydırarak o hatayı anında telafi et (`Error Compensation`)!**

```
┌────────────────────────────────────────────────────────────────────────────┐
│           RTN (ROUND-TO-NEAREST) vs GPTQ (HESSIAN ERROR COMPENSATION)      │
├─────────────────────────────────────┬──────────────────────────────────────┤
│ DÜZ YUVARLAMA (RTN)                 │ GPTQ (FRANTAR ET AL. / OBQ)          │
│ ─────────────────────────────────── │ ──────────────────────────────────── │
│ • Her ağırlığı w_q bağımsız olarak  │ • Amaç: || W X - W_hat X ||_2^2      │
│   en yakın INT4 ızgarasına yuvarlar:│   katman çıktısı hatasını küçültmek! │
│   q = clamp(round(w / scale))       │ • Kalibrasyon girdisi X'ten ikinci   │
│ • Aktivasyon kovaryansını (X X^T)   │   türev Hessian: H = 2 X X^T + λI    │
│   tamamen yok sayar!                │ • q. sütunu niceledikten sonra hata: │
│ • w_1 yuvarlandığında oluşan        │   δ_q = (w_q - quant(w_q)) / H^-1_qq │
│   (w_1 - q_1) * X_1 hatası doğrudan │ • Kalan sütunları (j > q) güncelle:  │
│   katman çıktısını bozar!           │   w_{:, j} <- w_{:, j} - δ_q H^-1_qj │
└─────────────────────────────────────┴──────────────────────────────────────┘
```

---

### 1. Katman İçi quantization Hedefi ve `Hessian` Matrisi ($H = 2 X X^T$)

Bir doğrusal katmanın ağırlık matrisi $W \in \mathbb{R}^{d_{\text{out}} \times d_{\text{in}}}$ ve bu katmana giren kalibrasyon aktivasyonları $X \in \mathbb{R}^{d_{\text{in}} \times N}$ ($N$: kalibrasyon token sayısı) olsun. Amacımız ağırlıkların kendisine değil, **katman çıktısına** gelen karesel hatayı minimize eden nicelenmiş $\hat{W}$ matrisini bulmaktır:

$$\mathcal{L}(\hat{W}) = \| W X - \hat{W} X \|_F^2 = \sum_{i=1}^{d_{\text{out}}} \| w_i X - \hat{w}_i X \|_2^2$$

Dikkat edersen toplam, $W$'nin her bir satırı $w_i \in \mathbb{R}^{1 \times d_{\text{in}}}$ için bağımsız karesel formlara ayrılır! Bir satırın hata fonksiyonunun $w_i$'ye göre ikinci türevi (**`Hessian Matrix`**) tüm satırlar için **birebir aynıdır** ve yalnızca girdi aktivasyonlarının dış çarpımından oluşur:

$$H = \frac{\partial^2 \| (w_i - \hat{w}_i) X \|_2^2}{\partial \hat{w}_i^2} = 2 X X^T \in \mathbb{R}^{d_{\text{in}} \times d_{\text{in}}}$$

Sayısallaştırma sırasında $H$ matrisinin tekil (`Singular / Non-Invertible`) olmasını önlemek ve sayısal kararlılığı garanti altına almak için diyagonalin ortalamasının küçük bir $\lambda$ katı (**`Tikhonov Damping`**, ör. $\lambda = 0.01 \cdot \frac{1}{d_{\text{in}}}\text{Tr}(H)$ veya doğrudan sabit $\lambda I$) diyagonale eklenir:

$$H_{\text{damped}} = \frac{2}{N} X X^T + \lambda I$$

```python
# RTN vs Hata Telafili (GPTQ) Nicelemenin Katman Çıktısı Hatası Karşılaştırması
# Girdi aktivasyonları X_0 ve X_1 birbiriyle yüksek korelasyonlu olsun:
w = [0.34, 0.34]      # Gerçek ağırlık satırı (1x2)
scale = 0.25          # INT4 ızgara adımı: {..., 0.0, 0.25, 0.50, ...}

# 1. Düz RTN: İkisi de 0.25'e aşağı yuvarlanır!
w_rtn = [round(v / scale) * scale for v in w]

# 2. GPTQ Mantığı: w[0] -> 0.25'e yuvarlanınca +0.09 açık kaldı;
#    bu açık w[1]'e eklenir (0.34 + 0.08 = 0.42) ve w[1] -> 0.50'ye yuvarlanır!
w_gptq = [0.25, 0.50]

# X = [1.0, 1.0]^T girdisi için gerçek çıktı vs RTN vs GPTQ:
gercek_y = w[0] * 1.0 + w[1] * 1.0
rtn_hata = (gercek_y - (w_rtn[0] + w_rtn[1])) ** 2
gptq_hata = (gercek_y - (w_gptq[0] + w_gptq[1])) ** 2
print(f"Gercek Cikti: {gercek_y:.2f} | RTN Hata^2: {rtn_hata:.4f} | GPTQ Hata^2: {gptq_hata:.4f}")
```

---

### 2. `GPTQ` Sütun-Sütun quantization ve Ters Hessian (`H_inv`) Güncellemesi

Bir ağırlık satırı $w \in \mathbb{R}^{d_{\text{in}}}$ ve ters Hessian matrisi $H^{-1} = (H_{\text{damped}})^{-1}$ verildiğinde, `GPTQ` sütunları soldan sağa $q = 0, 1, \dots, d_{\text{in}}-1$ sırasıyla niceler:

1. **Mevcut Sütunu Nicele (`Quantize & Dequantize`):**
   $q$. sütundaki güncel ağırlık $w_q$ değerini ölçek (`scale`) ile tam sayı ızgarasına yuvarla, $[q_{\min}, q_{\max}]$ aralığına kırp (`clamp`) ve tekrar kayan noktaya (`dequantized`) çevir:
   $$z_q = \text{clamp}\left(\lfloor w_q / \text{scale} \rceil, \; q_{\min}, \; q_{\max}\right), \qquad \hat{w}_q = z_q \cdot \text{scale}$$

2. **Ölçeklenmiş quantization Hatasını (`Scaled Quantization Error`) Hesapla:**
   $$\delta_q = \frac{w_q - \hat{w}_q}{[H^{-1}]_{q, q}}$$

3. **Kalan Sütunlara (`j > q`) Hata Telafisi Uygula (`Error Compensation`):**
   Henüz nicelenmemiş tüm sağdaki sütunları ($j = q+1, \dots, d_{\text{in}}-1$) ters Hessian'ın $q$. satırı boyunca güncelle:
   $$w_j \leftarrow w_j - \delta_q \cdot [H^{-1}]_{q, j}$$

> **Cholesky Reformülasyonu:** Gerçek üretimde her adımda $H^{-1}$'in alt matrisini yeniden ters çevirmek $O(d_{\text{in}}^4)$ sürer. Frantar et al., $H^{-1}$ matrisinin üst üçgen **Cholesky çarpanını ($U = \text{cholesky}(H^{-1})^T$)** önceden bir kez hesaplayarak tüm güncellemeleri ve 128 sütunluk blokları (`Lazy Batch Updates`) GPU Tensor Core hızında çalıştırmıştır!

---

### 3. Gerçek PyTorch Üretim Kodu: `GPTQQuantizer` Katman Sıkıştırıcı

Gerçek bir `AutoGPTQ / vLLM GPTQ` motorunda Cholesky ters Hessian ile ağırlık matrisini 4-bite sıkıştıran PyTorch sınıfı şu şekilde inşa edilir:

```python norun
import torch
import torch.nn as nn

class GPTQLinearQuantizer:
    def __init__(self, weight: torch.Tensor, bits: int = 4, percdamp: float = 0.01):
        self.W = weight.clone().float()  # (d_out, d_in)
        self.d_out, self.d_in = self.W.shape
        self.bits = bits
        self.qmax = 2 ** (bits - 1) - 1   # INT4 simetrik: +7
        self.qmin = -(2 ** (bits - 1))    # INT4 simetrik: -8
        self.percdamp = percdamp
        self.H = torch.zeros((self.d_in, self.d_in), device=weight.device, dtype=torch.float32)
        self.n_samples = 0

    @torch.no_grad()
    def add_batch(self, inp: torch.Tensor):
        # inp: (Batch * SeqLen, d_in) kalibrasyon aktivasyonları
        inp = inp.reshape(-1, self.d_in).float()
        n = inp.shape[0]
        self.H *= self.n_samples / (self.n_samples + n)
        self.n_samples += n
        inp = math.sqrt(2.0 / self.n_samples) * inp
        self.H += inp.T @ inp  # (2 / N) * X * X^T

    @torch.no_grad()
    def quantize(self) -> tuple[torch.Tensor, torch.Tensor]:
        # 1. Diyagonal sönümleme (Tikhonov Damping) ve Cholesky Ters Hessian
        damp = self.percdamp * torch.diag(self.H).mean()
        diag = torch.arange(self.d_in, device=self.H.device)
        self.H[diag, diag] += damp
        H_inv = torch.cholesky_inverse(torch.linalg.cholesky(self.H))
        H_inv_chol = torch.linalg.cholesky(H_inv, upper=True)

        # 2. Satır bazlı (Per-Channel) ölçek ve INT4 GPTQ döngüsü
        scale = self.W.abs().amax(dim=1, keepdim=True).clamp(min=1e-8) / self.qmax
        Q = torch.zeros_like(self.W)

        for q in range(self.d_in):
            w_col = self.W[:, q : q + 1]
            d_qq = H_inv_chol[q, q]
            q_int = torch.clamp(torch.round(w_col / scale), self.qmin, self.qmax)
            w_hat = q_int * scale
            Q[:, q : q + 1] = w_hat
            err = (w_col - w_hat) / d_qq  # Ölçeklenmiş hata: δ_q
            if q + 1 < self.d_in:
                self.W[:, q + 1 :] -= err @ H_inv_chol[q : q + 1, q + 1 :]
        return Q, scale
```

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [GPTQ makalesi](https://arxiv.org/abs/2210.17323). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: tahmin Ters Hessian İle Komşu Ağırlığa Hata Aktarımı
2 sütunlu bir ağırlık satırı $w = [0.60, \; 0.40]$, ölçek $\text{scale} = 0.50$ (`INT4` ızgarası: $\dots, -0.5, 0.0, 0.5, 1.0, \dots$) ve ters Hessian matrisi:
$$H^{-1} = \begin{bmatrix} 2.0 & -1.0 \\ -1.0 & 1.0 \end{bmatrix}$$
olarak veriliyor.
1. İlk sütun $w_0 = 0.60$ nicelendiğinde en yakın ızgara noktası $\hat{w}_0 = 0.50$ olur (quantization hatası $w_0 - \hat{w}_0 = +0.10$).
2. `GPTQ` formülü $\delta_0 = \frac{w_0 - \hat{w}_0}{[H^{-1}]_{0,0}}$ ve $w_1 \leftarrow w_1 - \delta_0 \cdot [H^{-1}]_{0,1}$ uygulandığında, nicelenmeden hemen önce $w_1$ ağırlığının güncellenmiş değeri kaç olur?

```python
w = [0.60, 0.40]
scale = 0.50
H_ters = [
    [2.0, -1.0],
    [-1.0, 1.0],
]

w0_hat = round(w[0] / scale) * scale
delta_0 = (w[0] - w0_hat) / H_ters[0][0]
w1_guncel = w[1] - delta_0 * H_ters[0][1]

print(f"w0_hat={w0_hat:.2f} | delta_0={delta_0:.3f} | Guncellenmis w1={w1_guncel:.2f}")
```

???

```cikti
w0_hat=0.50 | delta_0=0.050 | Guncellenmis w1=0.45
```
İlk sütunun yuvarlama hatası $0.60 - 0.50 = 0.10$'dur. Ters Hessian diyagonaline bölündüğünde $\delta_0 = 0.10 / 2.0 = 0.05$ bulunur. Kalan sütun güncellenirken $[H^{-1}]_{0,1} = -1.0$ olduğu için $w_1 \leftarrow 0.40 - 0.05 \times (-1.0) = 0.45$ olur! Yani ilk sütunun aşağı yuvarlanmasından kaynaklanan kayıp, pozitif korelasyonlu ikinci sütunun yukarı çekilmesiyle telafi edilmiştir.
:::

::: gorev 1 · Kalibrasyon Aktivasyonlarından Sönümlü (Damped) Hessian Matrisi Hesabı
Bir doğrusal katmana giren kalibrasyon aktivasyon matrisinden ($X \in \mathbb{R}^{d_{\text{in}} \times N}$, her satır bir giriş kanalı, her sütun bir kalibrasyon örneği) normalize edilmiş ve Tikhonov sönümlü (`Damped`) `GPTQ` Hessian matrisini hesaplayan `hessian_hesapla(X_kalibrasyon, lambda_sonum)` işlevini yaz.

**Girdi Kuralları ve Doğrulama:**
- `X_kalibrasyon`: Boyutu $d_{\text{in}} \times N$ ($d_{\text{in}} \ge 1, N \ge 1$) olan 2B sayı matrisi (`list[list[float]]`). Tüm elemanlar `bool` olmayan sonlu sayı olmalıdır.
- `lambda_sonum`: Diyagonal sönümleme katsayısı $\lambda$ (`bool` olmayan sonlu sayı, $\lambda \ge 0.0$).

**Hesaplama Kuralları:**
1. Örnek sayısı $N$ (`len(X_kalibrasyon[0])`) üzerinden normalize edilmiş ham Hessian matrisini hesapla ($i, j \in \{0, \dots, d_{\text{in}}-1\}$):
   $$H_{\text{ham}}[i][j] = \frac{2.0}{N} \sum_{k=0}^{N-1} X[i][k] \cdot X[j][k]$$
2. Ham diyagonal elemanların ortalamasını (`ortalama_diyagonal`) hesapla:
   $$\mu_{\text{diag}} = \frac{1}{d_{\text{in}}} \sum_{i=0}^{d_{\text{in}}-1} H_{\text{ham}}[i][i]$$
3. Sönümlü Hessian matrisini (`H_sonumlu`) oluştur: diyagonal elemanlara ($i == j$) $\lambda_{\text{etkin}} = \text{lambda\_sonum} \cdot \mu_{\text{diag}}$ ekle (eğer $\mu_{\text{diag}} == 0$ ise doğrudan $\text{lambda\_sonum}$ ekle):
   $$H_{\text{sonumlu}}[i][i] = H_{\text{ham}}[i][i] + (\text{lambda\_sonum} \cdot \mu_{\text{diag}} \text{ if } \mu_{\text{diag}} > 0 \text{ else } \text{lambda\_sonum})$$
4. İşlev şu sözlüğü döndürmelidir:
   `{"H_sonumlu": [...], "ortalama_diyagonal": float, "etkin_sonum": float}`
- Geçersiz herhangi bir girdide `ValueError` yükseltilmelidir.

```starter
import math

# KUSURLU BAŞLANGIÇ KODU: (2.0 / N) normalizasyonunu ve diyagonal sönümlemeyi (damping) uygulamıyor!
def hessian_hesapla(X_kalibrasyon, lambda_sonum):
    d_in = len(X_kalibrasyon)
    N = len(X_kalibrasyon[0])
    H = [
        [sum(X_kalibrasyon[i][k] * X_kalibrasyon[j][k] for k in range(N)) for j in range(d_in)]
        for i in range(d_in)
    ]
    return {
        "H_sonumlu": H,
        "ortalama_diyagonal": 0.0,
        "etkin_sonum": 0.0,
    }

X_ornek = [
    [1.0, 2.0, -1.0, 0.0],
    [0.5, 1.0,  0.5, 1.0],
]
print(hessian_hesapla(X_ornek, lambda_sonum=0.1))
```
```test
def sinama_hessian(f):
    import copy, math, random
    def _ref(X, lam):
        d_in, N = len(X), len(X[0])
        H = [
            [(2.0 / N) * sum(float(X[i][k]) * float(X[j][k]) for k in range(N)) for j in range(d_in)]
            for i in range(d_in)
        ]
        ort_d = sum(H[i][i] for i in range(d_in)) / d_in
        etkin = float(lam) * ort_d if ort_d > 0.0 else float(lam)
        for i in range(d_in):
            H[i][i] += etkin
        return {"H_sonumlu": H, "ortalama_diyagonal": ort_d, "etkin_sonum": etkin}
    def _yakin(a, b):
        keys = {"H_sonumlu", "ortalama_diyagonal", "etkin_sonum"}
        if not isinstance(a, dict) or set(a.keys()) != keys:
            return False
        if abs(a["ortalama_diyagonal"] - b["ortalama_diyagonal"]) > 1e-10 or abs(a["etkin_sonum"] - b["etkin_sonum"]) > 1e-10:
            return False
        ha, hb = a["H_sonumlu"], b["H_sonumlu"]
        if not isinstance(ha, list) or len(ha) != len(hb):
            return False
        for sa, sb in zip(ha, hb):
            if not isinstance(sa, list) or len(sa) != len(sb) or any(abs(x - y) > 1e-10 for x, y in zip(sa, sb)):
                return False
        return True
    try:
        X = [[1.0, 2.0, -1.0, 0.0], [0.5, 1.0, 0.5, 1.0]]
        old = copy.deepcopy(X)
        out = f(X, 0.1)
        if X != old or not _yakin(out, _ref(X, 0.1)):
            return False
        # H_ham[0][0] = (2/4)*(1+4+1+0) = 3.0, H_ham[1][1] = (2/4)*(0.25+1+0.25+1) = 1.25 -> ort = 2.125
        if abs(out["ortalama_diyagonal"] - 2.125) > 1e-10 or abs(out["etkin_sonum"] - 0.2125) > 1e-10:
            return False

        # Sıfır ve küçük diyagonal matrisi testleri
        X_sifir = [[0.0, 0.0], [0.0, 0.0]]
        if not _yakin(f(X_sifir, 0.05), _ref(X_sifir, 0.05)) or not _yakin(f([[0.5]], 0.1), _ref([[0.5]], 0.1)):
            return False

        rng = random.Random(3101)
        for _ in range(20):
            d = rng.randint(1, 5)
            n = rng.randint(2, 6)
            lam = rng.uniform(0.0, 0.2)
            xx = [[rng.uniform(-3.0, 3.0) for _ in range(n)] for _ in range(d)]
            if not _yakin(f(xx, lam), _ref(xx, lam)):
                return False

        bad_cases = [
            ([], 0.1),
            ([[]], 0.1),
            ([[1.0, 2.0], [1.0]], 0.1),
            (X, -0.01),
            (X, True),
            ([[1.0, False]], 0.1),
            ([[float("nan")]], 0.1),
            (X, float("inf")),
        ]
        for bx, bl in bad_cases:
            try:
                f(bx, bl)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

hessian_hesapla = need("hessian_hesapla")
ok(sinama_hessian(hessian_hesapla), "Kalibrasyon aktivasyonlarından 2/N ölçekli ve Tikhonov sönümlü Hessian hesabı")
for ad, mut in [
    ("diyagonal sönüm eklemeyen", lambda x, l: dict(hessian_hesapla(x, 0.0), etkin_sonum=hessian_hesapla(x, l)["etkin_sonum"])),
    ("2/N çarpanını unutan", lambda x, l: dict(hessian_hesapla(x, l), ortalama_diyagonal=hessian_hesapla(x, l)["ortalama_diyagonal"] * 2.0)),
]:
    ok(not sinama_hessian(mut), "mutant reddedildi: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef hessian_hesapla(X_kalibrasyon, lambda_sonum):\n    if not isinstance(X_kalibrasyon, list) or not X_kalibrasyon or (not isinstance(X_kalibrasyon[0], list)) or (not X_kalibrasyon[0]):\n        raise ValueError('X_kalibrasyon boş olmayan 2B matris olmalı')\n    if not _sayi_mi(lambda_sonum) or lambda_sonum < 0.0:\n        raise ValueError('lambda_sonum >= 0 sonlu sayı olmalı')\n    d_in = len(X_kalibrasyon)\n    N = len(X_kalibrasyon[0])\n    for satir in X_kalibrasyon:\n        if not isinstance(satir, list) or len(satir) != N or (not all((_sayi_mi(v) for v in satir))):\n            raise ValueError('geçersiz aktivasyon satırı')\n    olcek = 2.0 / float(N)\n    H = [[olcek * sum((float(X_kalibrasyon[i][k]) * float(X_kalibrasyon[j][k]) for k in range(N))) for j in range(d_in)] for i in range(d_in)]\n    ort_diag = sum((H[i][i] for i in range(d_in))) / float(d_in)\n    etkin_sonum = float(lambda_sonum) * ort_diag if ort_diag > 0.0 else float(lambda_sonum)\n    for i in range(d_in):\n        H[i][i] += etkin_sonum\n    return {'H_sonumlu': H, 'ortalama_diyagonal': ort_diag, 'etkin_sonum': etkin_sonum}", 'referans', 'exec'), _REF)
_t, _g = _ff(hessian_hesapla, _REF['hessian_hesapla'], ([[1.0, 2.0, -1.0, 0.0], [0.5, 1.0, 0.5, 1.0]], 0.1), tohum=2630, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (hessian_hesapla): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math

def _sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def hessian_hesapla(X_kalibrasyon, lambda_sonum):
    if not isinstance(X_kalibrasyon, list) or not X_kalibrasyon or not isinstance(X_kalibrasyon[0], list) or not X_kalibrasyon[0]:
        raise ValueError("X_kalibrasyon boş olmayan 2B matris olmalı")
    if not _sayi_mi(lambda_sonum) or lambda_sonum < 0.0:
        raise ValueError("lambda_sonum >= 0 sonlu sayı olmalı")

    d_in = len(X_kalibrasyon)
    N = len(X_kalibrasyon[0])
    for satir in X_kalibrasyon:
        if not isinstance(satir, list) or len(satir) != N or not all(_sayi_mi(v) for v in satir):
            raise ValueError("geçersiz aktivasyon satırı")

    olcek = 2.0 / float(N)
    H = [
        [olcek * sum(float(X_kalibrasyon[i][k]) * float(X_kalibrasyon[j][k]) for k in range(N)) for j in range(d_in)]
        for i in range(d_in)
    ]
    ort_diag = sum(H[i][i] for i in range(d_in)) / float(d_in)
    etkin_sonum = float(lambda_sonum) * ort_diag if ort_diag > 0.0 else float(lambda_sonum)

    for i in range(d_in):
        H[i][i] += etkin_sonum

    return {
        "H_sonumlu": H,
        "ortalama_diyagonal": ort_diag,
        "etkin_sonum": etkin_sonum,
    }

if __name__ == "__main__":
    X_ornek = [
        [1.0, 2.0, -1.0, 0.0],
        [0.5, 1.0,  0.5, 1.0],
    ]
    print(hessian_hesapla(X_ornek, lambda_sonum=0.1))
```
```hint
Önce $H[i][j] = \frac{2.0}{N} \sum_{k=0}^{N-1} X[i][k] X[j][k]$ matrisini oluştur. Ardından diyagonal elemanların ortalaması $\mu_{\text{diag}}$ üzerinden `etkin_sonum` değerini hesaplayıp yalnızca $H[i][i]$ köşegen elemanlarına ekle.
```
:::

::: gorev 2 · GPTQ Sütun quantization ve Kalan Ağırlıklara Hata Telafisi (Error Compensation)
Bir ağırlık satırını ($w \in \mathbb{R}^{d_{\text{in}}}$) verilen ters Hessian matrisi ($H^{-1} \in \mathbb{R}^{d_{\text{in}} \times d_{\text{in}}}$) ile soldan sağa niceleyen ve her sütunun yuvarlama hatasını kalan sütunlara dağıtan `gptq_sutun_nicele(agirlik_satiri, H_ters, olcek_scale, q_min, q_max)` işlevini yaz.

**Girdi Kuralları ve Doğrulama:**
- `agirlik_satiri`: Uzunluğu $d_{\text{in}} \ge 1$ olan sayı listesi (`list[float]`).
- `H_ters`: Boyutu $d_{\text{in}} \times d_{\text{in}}$ olan simetrik ters Hessian matrisi (`list[list[float]]`). Tüm diyagonal elemanlar kesin pozitif olmalıdır ($[H^{-1}]_{q,q} > 0$).
- `olcek_scale`: quantization adım ölçeği (`bool` olmayan sonlu sayı, $> 0$).
- `q_min`, `q_max`: Tam sayı kırpma sınırları (`bool` olmayan `int`, `q_min < q_max`).

**Hesaplama Kuralları:**
1. Orijinal `agirlik_satiri` listesini bozmadan çalışma kopyası $w = [\text{float}(v) \text{ for } v \text{ in agirlik\_satiri}]$ oluştur.
2. Ayrıca karşılaştırma için **düz `RTN`** nicelenmiş ağırlıkları da hesapla:
   $$q_{\text{rtn}, j} = \min(\max(\text{round}(w_{\text{orijinal}, j} / \text{olcek\_scale}), q_{\min}), q_{\max}), \qquad \hat{w}_{\text{rtn}, j} = q_{\text{rtn}, j} \cdot \text{olcek\_scale}$$
3. **GPTQ Döngüsü ($q = 0, 1, \dots, d_{\text{in}}-1$):**
   - Güncel $w[q]$ değerini tam sayıya yuvarla ve kırp:
     $$z_q = \min(\max(\text{round}(w[q] / \text{olcek\_scale}), q_{\min}), q_{\max})$$
   - Dequantize edilmiş ağırlık: $\hat{w}_{\text{gptq}, q} = z_q \cdot \text{olcek\_scale}$.
   - Ölçeklenmiş quantization hatası:
     $$\delta_q = \frac{w[q] - \hat{w}_{\text{gptq}, q}}{H_{\text{ters}}[q][q]}$$
   - Sağda kalan tüm sütunları ($j = q + 1, \dots, d_{\text{in}} - 1$) güncelle:
     $$w[j] \leftarrow w[j] - \delta_q \cdot H_{\text{ters}}[q][j]$$
4. İşlev şu sözlüğü döndürmelidir:
   `{"q_tam_sayilar": list[int], "w_gptq": list[float], "w_rtn": list[float], "hata_adimlari": list[float]}`
   (`hata_adimlari`, her adımda hesaplanan $[\delta_0, \delta_1, \dots]$ listesidir).
- Geçersiz herhangi bir girdide `ValueError` yükseltilmelidir.

```starter
import math

# KUSURLU BAŞLANGIÇ KODU: Sağdaki sütunlara (j > q) ters Hessian hata telafisi uygulamıyor (düz RTN yapıyor)!
def gptq_sutun_nicele(agirlik_satiri, H_ters, olcek_scale, q_min, q_max):
    q_int = [min(max(round(v / olcek_scale), q_min), q_max) for v in agirlik_satiri]
    w_q = [z * olcek_scale for z in q_int]
    return {
        "q_tam_sayilar": q_int,
        "w_gptq": w_q,
        "w_rtn": list(w_q),
        "hata_adimlari": [0.0] * len(agirlik_satiri),
    }

w_satir = [0.60, 0.40, -0.35]
H_inv = [
    [ 2.0, -1.0,  0.5],
    [-1.0,  1.5, -0.5],
    [ 0.5, -0.5,  1.0],
]
print(gptq_sutun_nicele(w_satir, H_inv, olcek_scale=0.5, q_min=-8, q_max=7))
```
```test
def sinama_gptq(f):
    import copy, math, random
    def _ref(w_in, H_inv, sc, qmin, qmax):
        d = len(w_in)
        w = [float(v) for v in w_in]
        w_rtn = [min(max(round(float(v) / sc), qmin), qmax) * float(sc) for v in w_in]
        q_int, w_gptq, deltas = [], [], []
        for q in range(d):
            zq = min(max(round(w[q] / sc), qmin), qmax)
            wq_hat = float(zq) * float(sc)
            dq = (w[q] - wq_hat) / float(H_inv[q][q])
            q_int.append(int(zq))
            w_gptq.append(wq_hat)
            deltas.append(dq)
            for j in range(q + 1, d):
                w[j] -= dq * float(H_inv[q][j])
        return {"q_tam_sayilar": q_int, "w_gptq": w_gptq, "w_rtn": w_rtn, "hata_adimlari": deltas}
    def _yakin(a, b):
        keys = {"q_tam_sayilar", "w_gptq", "w_rtn", "hata_adimlari"}
        if not isinstance(a, dict) or set(a.keys()) != keys:
            return False
        if a["q_tam_sayilar"] != b["q_tam_sayilar"] or any(type(x) is not int for x in a["q_tam_sayilar"]):
            return False
        for k in ("w_gptq", "w_rtn", "hata_adimlari"):
            if not isinstance(a[k], list) or len(a[k]) != len(b[k]) or any(abs(x - y) > 1e-10 for x, y in zip(a[k], b[k])):
                return False
        return True
    try:
        w = [0.60, 0.38]
        H_inv = [[1.0, -1.0], [-1.0, 2.0]]
        old = (copy.deepcopy(w), copy.deepcopy(H_inv))
        out = f(w, H_inv, 0.5, -8, 7)
        if (w, H_inv) != old or not _yakin(out, _ref(w, H_inv, 0.5, -8, 7)):
            return False
        # RTN ikisini de [0.5, 0.5] yapar mı? 0.38/0.5 = 0.76 -> round=1 (0.5).
        # Peki w = [0.60, 0.22] olsun: RTN -> [0.5, 0.0], ama GPTQ'da w[1] = 0.22 - (0.10)*(-1.0) = 0.32 -> round(0.32/0.5)=1 -> 0.5!
        w2 = [0.60, 0.22]
        out2 = f(w2, H_inv, 0.5, -8, 7)
        if out2["w_rtn"] != [0.5, 0.0] or out2["w_gptq"] != [0.5, 0.5]:
            return False

        rng = random.Random(3102)
        for _ in range(25):
            d = rng.randint(2, 6)
            ww = [rng.uniform(-2.0, 2.0) for _ in range(d)]
            hh = [[rng.uniform(-0.4, 0.4) for _ in range(d)] for _ in range(d)]
            for i in range(d):
                hh[i][i] = rng.uniform(1.0, 3.0)
                for j in range(i + 1, d):
                    hh[j][i] = hh[i][j]
            sc = rng.uniform(0.1, 0.5)
            if not _yakin(f(ww, hh, sc, -8, 7), _ref(ww, hh, sc, -8, 7)):
                return False

        bad_cases = [
            ([], [], 0.5, -8, 7),
            ([], H_inv, 0.5, -8, 7),
            (w, [[1.0]], 0.5, -8, 7),
            (w, [[0.0, 0.0], [0.0, 1.0]], 0.5, -8, 7),  # H_ters[q][q] <= 0
            (w, H_inv, 0.0, -8, 7),
            (w, H_inv, 0.5, 7, -8),
            (w, H_inv, 0.5, True, 7),
            ([1.0, float("nan")], H_inv, 0.5, -8, 7),
        ]
        for bw, bh, bs, bmin, bmax in bad_cases:
            try:
                f(bw, bh, bs, bmin, bmax)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

gptq_sutun_nicele = need("gptq_sutun_nicele")
ok(sinama_gptq(gptq_sutun_nicele), "GPTQ sütun niceleme, ters Hessian hata telafisi ve RTN karşılaştırması")
for ad, mut in [
    ("hata telafisi yapmayan (düz RTN)", lambda w, h, s, mn, mx: dict(gptq_sutun_nicele(w, h, s, mn, mx), w_gptq=gptq_sutun_nicele(w, h, s, mn, mx)["w_rtn"])),
    ("hatayı yanlış yönde ekleyen", lambda w, h, s, mn, mx: dict(gptq_sutun_nicele(w, h, s, mn, mx), hata_adimlari=[-v for v in gptq_sutun_nicele(w, h, s, mn, mx)["hata_adimlari"]])),
]:
    ok(not sinama_gptq(mut), "mutant reddedildi: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef gptq_sutun_nicele(agirlik_satiri, H_ters, olcek_scale, q_min, q_max):\n    if not isinstance(agirlik_satiri, list) or not agirlik_satiri or (not all((_sayi_mi(v) for v in agirlik_satiri))):\n        raise ValueError('geçersiz agirlik_satiri')\n    d = len(agirlik_satiri)\n    if not isinstance(H_ters, list) or len(H_ters) != d:\n        raise ValueError('H_ters boyutu agirlik_satiri ile uyuşmuyor')\n    for q, satir in enumerate(H_ters):\n        if not isinstance(satir, list) or len(satir) != d or (not all((_sayi_mi(v) for v in satir))):\n            raise ValueError('geçersiz H_ters satırı')\n        if satir[q] <= 0.0:\n            raise ValueError('H_ters diyagonal elemanları kesin pozitif olmalı')\n    if not _sayi_mi(olcek_scale) or olcek_scale <= 0.0:\n        raise ValueError('olcek_scale > 0 olmalı')\n    if isinstance(q_min, bool) or isinstance(q_max, bool) or (not isinstance(q_min, int)) or (not isinstance(q_max, int)) or (q_min >= q_max):\n        raise ValueError('geçersiz q_min / q_max')\n    sc = float(olcek_scale)\n    w = [float(v) for v in agirlik_satiri]\n    w_rtn = [float(min(max(round(float(v) / sc), q_min), q_max)) * sc for v in agirlik_satiri]\n    q_tam_sayilar = []\n    w_gptq = []\n    hata_adimlari = []\n    for q in range(d):\n        zq = int(min(max(round(w[q] / sc), q_min), q_max))\n        wq_hat = float(zq) * sc\n        delta_q = (w[q] - wq_hat) / float(H_ters[q][q])\n        q_tam_sayilar.append(zq)\n        w_gptq.append(wq_hat)\n        hata_adimlari.append(delta_q)\n        for j in range(q + 1, d):\n            w[j] -= delta_q * float(H_ters[q][j])\n    return {'q_tam_sayilar': q_tam_sayilar, 'w_gptq': w_gptq, 'w_rtn': w_rtn, 'hata_adimlari': hata_adimlari}", 'referans', 'exec'), _REF)
_t, _g = _ff(gptq_sutun_nicele, _REF['gptq_sutun_nicele'], ([0.6, 0.4, -0.35], [[2.0, -1.0, 0.5], [-1.0, 1.5, -0.5], [0.5, -0.5, 1.0]], 0.5, -8, 7), tohum=2887, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (gptq_sutun_nicele): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math

def _sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def gptq_sutun_nicele(agirlik_satiri, H_ters, olcek_scale, q_min, q_max):
    if not isinstance(agirlik_satiri, list) or not agirlik_satiri or not all(_sayi_mi(v) for v in agirlik_satiri):
        raise ValueError("geçersiz agirlik_satiri")
    d = len(agirlik_satiri)
    if not isinstance(H_ters, list) or len(H_ters) != d:
        raise ValueError("H_ters boyutu agirlik_satiri ile uyuşmuyor")
    for q, satir in enumerate(H_ters):
        if not isinstance(satir, list) or len(satir) != d or not all(_sayi_mi(v) for v in satir):
            raise ValueError("geçersiz H_ters satırı")
        if satir[q] <= 0.0:
            raise ValueError("H_ters diyagonal elemanları kesin pozitif olmalı")

    if not _sayi_mi(olcek_scale) or olcek_scale <= 0.0:
        raise ValueError("olcek_scale > 0 olmalı")
    if isinstance(q_min, bool) or isinstance(q_max, bool) or not isinstance(q_min, int) or not isinstance(q_max, int) or q_min >= q_max:
        raise ValueError("geçersiz q_min / q_max")

    sc = float(olcek_scale)
    w = [float(v) for v in agirlik_satiri]
    w_rtn = [float(min(max(round(float(v) / sc), q_min), q_max)) * sc for v in agirlik_satiri]

    q_tam_sayilar = []
    w_gptq = []
    hata_adimlari = []

    for q in range(d):
        zq = int(min(max(round(w[q] / sc), q_min), q_max))
        wq_hat = float(zq) * sc
        delta_q = (w[q] - wq_hat) / float(H_ters[q][q])

        q_tam_sayilar.append(zq)
        w_gptq.append(wq_hat)
        hata_adimlari.append(delta_q)

        for j in range(q + 1, d):
            w[j] -= delta_q * float(H_ters[q][j])

    return {
        "q_tam_sayilar": q_tam_sayilar,
        "w_gptq": w_gptq,
        "w_rtn": w_rtn,
        "hata_adimlari": hata_adimlari,
    }

if __name__ == "__main__":
    w_satir = [0.60, 0.40, -0.35]
    H_inv = [
        [ 2.0, -1.0,  0.5],
        [-1.0,  1.5, -0.5],
        [ 0.5, -0.5,  1.0],
    ]
    print(gptq_sutun_nicele(w_satir, H_inv, olcek_scale=0.5, q_min=-8, q_max=7))
```
```hint
Çalışma kopyası `w` üzerinde $q = 0 \dots d-1$ döngüsü kur. Her adımda `zq = min(max(round(w[q] / sc), q_min), q_max)` ve `delta_q = (w[q] - zq * sc) / H_ters[q][q]` hesapladıktan sonra, $j \in \{q+1, \dots, d-1\}$ için `w[j] -= delta_q * H_ters[q][j]` güncellemesini uygula.
```
:::

::: anlat Gerçek deney: SmolLM2'yi gerçek kalibrasyonla GPTQ'lamak ve kalibrasyon alanının etkisi
Final GPTQ'yu gerçek bir modelde uygular (CPU, yaklaşık bir buçuk dakika, indirme yok):

- **Kalibrasyon:** iki gerçek küme hazırlanır, her biri ~1 000 token: İngilizce (bir paragraf ve `deepset/prompt-injections` metinleri) ve Türkçe (Pafta ders metinleri). 3. katmanın `gate_proj` girdileri ileri kancayla yakalanır.
- **Öğrencinin Hessian'ı ve GPTQ'su:** İngilizce kalibrasyonun ilk 128 girdi kanalı için senin `hessian_hesapla` işlevin $H = \frac{2}{N} X X^\top + \lambda\,\bar{h}\,I$ hesaplar; sonuç torch ile karşılaştırılır. Sonra $H^{-1}$'in **üst Cholesky çarpanı** (GPTQ'nun Cholesky biçimi: her satırı, önceki sütunlar nicemlendikten sonraki güncel ters Hessian'ın satırıdır) 64 gerçek ağırlık satırıyla senin `gptq_sutun_nicele` işlevine verilir. Çıktı hatası hem kalibrasyonda hem ayrılmış İngilizce metinde RTN ile karşılaştırılır. GPTQ ağırlığı RTN'den daha çok değiştirir ama çıktıyı daha iyi korur.
- **Tüm model:** 210 doğrusal katman torch'ta 4 bite nicemlenir: RTN, İngilizce kalibrasyonlu GPTQ ve Türkçe kalibrasyonlu GPTQ. Her biri İngilizce ve Türkçe bir metinde perplexity ile ölçülür.

Beklenen ders: GPTQ kalibrasyon dağılımına uyum sağlar. Eşleşen alanda RTN'yi açıkça yener. Alan kaydığında RTN'den bile kötü olabilir: Türkçe kalibrasyonlu model İngilizcede, İngilizce kalibrasyonlu model Türkçede bozulur.

**Güvenlik yönü — kalibrasyon verisi bir tedarik zinciridir:** Üçüncü bir kalibrasyon kümesi saldırgan tarafından verilir: tek bir tokenın (" the") 1 000 tekrarı. Bu kümeyle GPTQ'lanan model İngilizce ve Türkçe değerlendirmede **RTN'den bile** çok daha kötüdür. Hessian yalnız birkaç yönü görür ve GPTQ hata telafisini gerçek metnin kullandığı yönlere iter. Kalibrasyonda hata küçük göründüğü için sorun nicemleme sırasında fark edilmez. Kalibrasyon verisinin kaynağı da modelin kendisi gibi denetlenmeli, nicemlenmiş model mutlaka ayrı bir değerlendirme kümesinde ölçülmelidir.

Kabul: iki işlevin farksal taramayı geçmesi; Hessian ve GPTQ'nun torch ile aynı olması; GPTQ'nun blokta kalibrasyon ve ayrılmış veride RTN'den düşük çıktı hatası vermesi; eşleşen alanda GPTQ'nun RTN'yi yenmesi ve alan kaymasının iki yönde de zarar vermesi. Ayrıca zehirli kalibrasyonlu GPTQ iki değerlendirmede de RTN'den yüksek perplexity vermelidir.

**Kanıt dosyasını oku:** `kalibrasyon_hatasi_*`, `cikti_hatasi_*`, `agirlik_hatasi_*`, `ppl` (5 model × 2 değerlendirme). Soru 1: GPTQ ağırlık hatası RTN'den büyükken çıktı hatası neden küçük? Soru 2: Çok dilli bir model için kalibrasyon kümesini nasıl kurardın? Soru 3: Yalnız nicemlenince ortaya çıkan bir arka kapı neden tam hassasiyet testinde görünmez?
:::

::: gorev Gerçek deney · SmolLM2'de gerçek kalibrasyonla Hessian, GPTQ ve İngilizce/Türkçe kalibrasyon karşılaştırması
Önceki görevlerdeki `hessian_hesapla`, `gptq_sutun_nicele` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 300
```
```starter
import ai_lab
import math

def hessian_hesapla(X_kalibrasyon, lambda_sonum):
    d_in = len(X_kalibrasyon)
    N = len(X_kalibrasyon[0])
    H = [[sum((X_kalibrasyon[i][k] * X_kalibrasyon[j][k] for k in range(N))) for j in range(d_in)] for i in range(d_in)]
    return {'H_sonumlu': H, 'ortalama_diyagonal': 0.0, 'etkin_sonum': 0.0}

import math

def gptq_sutun_nicele(agirlik_satiri, H_ters, olcek_scale, q_min, q_max):
    q_int = [min(max(round(v / olcek_scale), q_min), q_max) for v in agirlik_satiri]
    w_q = [z * olcek_scale for z in q_int]
    return {'q_tam_sayilar': q_int, 'w_gptq': w_q, 'w_rtn': list(w_q), 'hata_adimlari': [0.0] * len(agirlik_satiri)}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_31 as D
    D.goster(hessian_hesapla, gptq_sutun_nicele)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_gptq', '_hinv_cholesky', '_girdiler', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
hessian_hesapla = need("hessian_hesapla")
gptq_sutun_nicele = need("gptq_sutun_nicele")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef hessian_hesapla(X_kalibrasyon, lambda_sonum):\n    if not isinstance(X_kalibrasyon, list) or not X_kalibrasyon or (not isinstance(X_kalibrasyon[0], list)) or (not X_kalibrasyon[0]):\n        raise ValueError('X_kalibrasyon boş olmayan 2B matris olmalı')\n    if not _sayi_mi(lambda_sonum) or lambda_sonum < 0.0:\n        raise ValueError('lambda_sonum >= 0 sonlu sayı olmalı')\n    d_in = len(X_kalibrasyon)\n    N = len(X_kalibrasyon[0])\n    for satir in X_kalibrasyon:\n        if not isinstance(satir, list) or len(satir) != N or (not all((_sayi_mi(v) for v in satir))):\n            raise ValueError('geçersiz aktivasyon satırı')\n    olcek = 2.0 / float(N)\n    H = [[olcek * sum((float(X_kalibrasyon[i][k]) * float(X_kalibrasyon[j][k]) for k in range(N))) for j in range(d_in)] for i in range(d_in)]\n    ort_diag = sum((H[i][i] for i in range(d_in))) / float(d_in)\n    etkin_sonum = float(lambda_sonum) * ort_diag if ort_diag > 0.0 else float(lambda_sonum)\n    for i in range(d_in):\n        H[i][i] += etkin_sonum\n    return {'H_sonumlu': H, 'ortalama_diyagonal': ort_diag, 'etkin_sonum': etkin_sonum}\n\nimport math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef gptq_sutun_nicele(agirlik_satiri, H_ters, olcek_scale, q_min, q_max):\n    if not isinstance(agirlik_satiri, list) or not agirlik_satiri or (not all((_sayi_mi(v) for v in agirlik_satiri))):\n        raise ValueError('geçersiz agirlik_satiri')\n    d = len(agirlik_satiri)\n    if not isinstance(H_ters, list) or len(H_ters) != d:\n        raise ValueError('H_ters boyutu agirlik_satiri ile uyuşmuyor')\n    for q, satir in enumerate(H_ters):\n        if not isinstance(satir, list) or len(satir) != d or (not all((_sayi_mi(v) for v in satir))):\n            raise ValueError('geçersiz H_ters satırı')\n        if satir[q] <= 0.0:\n            raise ValueError('H_ters diyagonal elemanları kesin pozitif olmalı')\n    if not _sayi_mi(olcek_scale) or olcek_scale <= 0.0:\n        raise ValueError('olcek_scale > 0 olmalı')\n    if isinstance(q_min, bool) or isinstance(q_max, bool) or (not isinstance(q_min, int)) or (not isinstance(q_max, int)) or (q_min >= q_max):\n        raise ValueError('geçersiz q_min / q_max')\n    sc = float(olcek_scale)\n    w = [float(v) for v in agirlik_satiri]\n    w_rtn = [float(min(max(round(float(v) / sc), q_min), q_max)) * sc for v in agirlik_satiri]\n    q_tam_sayilar = []\n    w_gptq = []\n    hata_adimlari = []\n    for q in range(d):\n        zq = int(min(max(round(w[q] / sc), q_min), q_max))\n        wq_hat = float(zq) * sc\n        delta_q = (w[q] - wq_hat) / float(H_ters[q][q])\n        q_tam_sayilar.append(zq)\n        w_gptq.append(wq_hat)\n        hata_adimlari.append(delta_q)\n        for j in range(q + 1, d):\n            w[j] -= delta_q * float(H_ters[q][j])\n    return {'q_tam_sayilar': q_tam_sayilar, 'w_gptq': w_gptq, 'w_rtn': w_rtn, 'hata_adimlari': hata_adimlari}", 'referans', 'exec'), _REF)
_t, _g = _ff(hessian_hesapla, _REF['hessian_hesapla'], ([[1.0, 2.0, -1.0, 0.0], [0.5, 1.0, 0.5, 1.0]], 0.1), tohum=2630, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (hessian_hesapla): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(gptq_sutun_nicele, _REF['gptq_sutun_nicele'], ([0.6, 0.4, -0.35], [[2.0, -1.0, 0.5], [-1.0, 1.5, -0.5], [0.5, -0.5, 1.0]], 0.5, -8, 7), tohum=2887, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (gptq_sutun_nicele): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
def _sinir31():
    try:
        h1 = hessian_hesapla([[0.5]], 0.1)
        h0 = hessian_hesapla([[0.0]], 0.1)
        if abs(h1['etkin_sonum'] - 0.05) > 1e-12 or abs(h0['etkin_sonum'] - 0.1) > 1e-12:
            return False
        for fn_, args_ in [(hessian_hesapla, ([[]], 0.1)), (gptq_sutun_nicele, ([], [], 0.5, -8, 7))]:
            try:
                fn_(*args_)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(_sinir31(), 'Hessian sönüm ve boş girdi sınır kontrolleri')
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_31 as D
try: r = D.deney(hessian_hesapla, gptq_sutun_nicele)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['hessian_ayni'] and r['gptq_ayni'], 'Hessian ve GPTQ sütun nicemlemesi gerçek aktivasyonlarda torch ile aynı')
kontrol(r['gptq_kalibrasyonda_iyi'] and r['gptq_ciktida_iyi'], "GPTQ gerçek blokta kalibrasyonda ve ayrılmış veride RTN'den düşük çıktı hatası verdi")
kontrol(r['gptq_eslesen_alanda_iyi'] and r['alan_kaymasi_zarar'], "tüm modelde GPTQ eşleşen alanda RTN'yi yendi; alan kayması iki yönde de zarar verdi")
kontrol(r['zehirli_kalibrasyon_rtn_den_kotu'], "tek token tekrarlı zehirli kalibrasyon GPTQ'yu iki dilde de RTN'den kötü yaptı")
ai_lab.kanit_yaz("ai-uretim-31-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-31", "deney": r})
```
```solution
import ai_lab
import math

def _sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def hessian_hesapla(X_kalibrasyon, lambda_sonum):
    if not isinstance(X_kalibrasyon, list) or not X_kalibrasyon or (not isinstance(X_kalibrasyon[0], list)) or (not X_kalibrasyon[0]):
        raise ValueError('X_kalibrasyon boş olmayan 2B matris olmalı')
    if not _sayi_mi(lambda_sonum) or lambda_sonum < 0.0:
        raise ValueError('lambda_sonum >= 0 sonlu sayı olmalı')
    d_in = len(X_kalibrasyon)
    N = len(X_kalibrasyon[0])
    for satir in X_kalibrasyon:
        if not isinstance(satir, list) or len(satir) != N or (not all((_sayi_mi(v) for v in satir))):
            raise ValueError('geçersiz aktivasyon satırı')
    olcek = 2.0 / float(N)
    H = [[olcek * sum((float(X_kalibrasyon[i][k]) * float(X_kalibrasyon[j][k]) for k in range(N))) for j in range(d_in)] for i in range(d_in)]
    ort_diag = sum((H[i][i] for i in range(d_in))) / float(d_in)
    etkin_sonum = float(lambda_sonum) * ort_diag if ort_diag > 0.0 else float(lambda_sonum)
    for i in range(d_in):
        H[i][i] += etkin_sonum
    return {'H_sonumlu': H, 'ortalama_diyagonal': ort_diag, 'etkin_sonum': etkin_sonum}

def gptq_sutun_nicele(agirlik_satiri, H_ters, olcek_scale, q_min, q_max):
    if not isinstance(agirlik_satiri, list) or not agirlik_satiri or (not all((_sayi_mi(v) for v in agirlik_satiri))):
        raise ValueError('geçersiz agirlik_satiri')
    d = len(agirlik_satiri)
    if not isinstance(H_ters, list) or len(H_ters) != d:
        raise ValueError('H_ters boyutu agirlik_satiri ile uyuşmuyor')
    for q, satir in enumerate(H_ters):
        if not isinstance(satir, list) or len(satir) != d or (not all((_sayi_mi(v) for v in satir))):
            raise ValueError('geçersiz H_ters satırı')
        if satir[q] <= 0.0:
            raise ValueError('H_ters diyagonal elemanları kesin pozitif olmalı')
    if not _sayi_mi(olcek_scale) or olcek_scale <= 0.0:
        raise ValueError('olcek_scale > 0 olmalı')
    if isinstance(q_min, bool) or isinstance(q_max, bool) or (not isinstance(q_min, int)) or (not isinstance(q_max, int)) or (q_min >= q_max):
        raise ValueError('geçersiz q_min / q_max')
    sc = float(olcek_scale)
    w = [float(v) for v in agirlik_satiri]
    w_rtn = [float(min(max(round(float(v) / sc), q_min), q_max)) * sc for v in agirlik_satiri]
    q_tam_sayilar = []
    w_gptq = []
    hata_adimlari = []
    for q in range(d):
        zq = int(min(max(round(w[q] / sc), q_min), q_max))
        wq_hat = float(zq) * sc
        delta_q = (w[q] - wq_hat) / float(H_ters[q][q])
        q_tam_sayilar.append(zq)
        w_gptq.append(wq_hat)
        hata_adimlari.append(delta_q)
        for j in range(q + 1, d):
            w[j] -= delta_q * float(H_ters[q][j])
    return {'q_tam_sayilar': q_tam_sayilar, 'w_gptq': w_gptq, 'w_rtn': w_rtn, 'hata_adimlari': hata_adimlari}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_31 as D
    D.goster(hessian_hesapla, gptq_sutun_nicele)
```
```hint
İki görevin çözümlerini olduğu gibi buraya koy. H_ters olarak ters Hessian'ın üst Cholesky çarpanı verilir; senin işlevin onu olduğu gibi kullanır.
```
:::

::: anlat Sınır
Görevler sönümlü Hessian'ı, GPTQ sütun nicemlemesini ve kalan ağırlıklara hata telafisini küçük matrislerle hesaplatır; final adım SmolLM2'nin tüm doğrusal katmanlarını nicemleyip perplexity ölçer. GPTQ kalibrasyon verisine bağımlıdır; dar bir kalibrasyon kümesi başka alanlarda kaliteyi düşürür. Sönümleme (damping) Hessian tekile yakınken kararlılık sağlar, ama fazlası telafiyi zayıflatır. Nicemleme tam hassasiyette görünmeyen davranış farkları üretebilir; yalnız nicemlenince ortaya çıkan arka kapılar gösterilmiştir, bu yüzden nicemlenmiş model ayrıca test edilmelidir.

Kaynaklar: [Frantar vd. 2022 - GPTQ: Accurate Post-Training Quantization for Generative Pre-trained Transformers](https://arxiv.org/abs/2210.17323), [Frantar ve Alistarh 2022 - Optimal Brain Compression: A Framework for Accurate Post-Training Quantization and Pruning](https://arxiv.org/abs/2208.11580).
:::

::: dusun
**Mimari Soru:** `GPTQ` nicelemesinde kalibrasyon veri kümesini (`Calibration Dataset`) yalnızca İngilizce Wikipedia cümlelerinden seçersen, sıkıştırılmış `INT4` modelin Python kodlama veya Türkçe hukuk sorularındaki performansı neden Wikipedia testlerine göre daha fazla düşer? Hessian matrisi $H = 2 X X^T$ hangi kanalların "önemli" olduğunu nereden öğreniyor?
:::

::: ozet
- **Düz Yuvarlama (`Round-to-Nearest - RTN`)**, ağırlıklar arasındaki aktivasyon korelasyonlarını yok saydığı için `INT4` ve altında büyük katman çıktısı hatası üretir.
- **`GPTQ (Frantar et al.)`**, katman çıktısı hatasını $\|WX - \hat{W}X\|_F^2$ minimize etmek için kalibrasyon aktivasyonlarından sönümlü **Hessian matrisini ($H = \frac{2}{N} X X^T + \lambda I$)** çıkarır.
- Her sütun $q$ nicelendiğinde oluşan ölçeklenmiş hata $\delta_q = (w_q - \hat{w}_q) / [H^{-1}]_{qq}$, henüz nicelenmemiş sağdaki sütunlara ($w_j \leftarrow w_j - \delta_q [H^{-1}]_{qj}$) dağıtılarak katman çıktısı korunur.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Düz yuvarlama (`RTN`) neden `INT4`'te çöker? (30 sn).** "Ağırlıkları birbirinden bağımsız en yakın tam sayıya yuvarlamak aktivasyon kanalları arasındaki korelasyonu yok sayar ve katman çıktısı hatasını $\|WX - \hat{W}X\|_F^2$ büyütür."
2. **Sönümlü Hessian ve hata telafisi (`GPTQ`) (35 sn).** "Kalibrasyon aktivasyonlarından $H = \frac{2}{N}XX^T + \lambda I$ eğriliği çıkarılır; $q$. sütun nicelendiğinde oluşan $\delta_q = (w_q - \hat{w}_q)/[H^{-1}]_{qq}$ hatası sağdaki henüz nicelenmemiş ağırlıklardan düşülerek çıktı korunur."
3. **Nicemleme güvenlik sınırı (30 sn).** "`FP32` modelde sessiz duran bir arka kapı veya güvenlik kayması yalnız 4-bit nicelenmiş ağırlıklarda aktifleşebilir (`quantization-activated backdoor`)."
4. **Soru (25 sn).** "Üretime alacağın 4-bit `GPTQ` modelin güvenlik testlerini neden `FP16` kaynak model yerine bizzat nicelenmiş artefakt üzerinde koşmalısın?"
:::
