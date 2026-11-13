---
id: ai-uretim-03
title: "Modern Transformer Bloğu Kodlaması: RMSNorm, RoPE (Rotary Embedding) ve SwiGLU"
track: ai-uretim
order: 3
duration_minutes: 40
difficulty: ileri
xp: 280
prerequisites: [ai-uretim-02]
summary: "Modern öncü dil modellerinin omurgasını oluşturan Pre-Norm RMSNorm, 2B bağıl konumsal döndürme (RoPE) ve kapılı SwiGLU FFN katmanlarını sıfırdan kodla ve SmolLM2 ağırlıklarıyla doğrula."
esleme: ai-temel-03, ai-temel-07, ai-uretim-04
tags: [transformer, rmsnorm, rope, rotary-embedding, swiglu, llama3, deepseek]
---

::: anlat
## RMSNorm, RoPE ve SwiGLU

Bazı modern Transformer aileleri normalizasyon, position encoding ve feed-forward katmanlarında RMSNorm, RoPE ve SwiGLU kullanır. Bu derste bu üç bileşenin girdilerini, boyutlarını ve çıktısını ayrı hesaplayacaksın. Yayımlanmış açık mimariler örnek alınır; açıklanmamış ticari model mimarileri hakkında sonuç çıkarılmaz.

Eğer bugün 70 Milyar parametreli bir modeli 2017'deki klasik **Post-LayerNorm**, **Sinusoidal Positional Encoding** ve **ReLU Feed-Forward Network** ile eğitmeye kalkarsan:
1. Eğitim ilk birkaç bin adımda **Gradient Explosion / Spike (Gradyan Patlaması)** yüzünden çöker (`NaN Loss`),
2. Eğitim sırasında gördüğü $4096$ tokenlık bağlam uzunluğunu (**Context Length**) $128,000$ token'a uzatamazsın,
3. Aynı parametre bütçesinde çok daha yüksek bir **Perplexity (Şaşkınlık / Kayıp)** değerinde takılıp kalırsın.

Modern Frontier LLM'lerin tamamı bu üç sorunu çözmek için **üç temel mimari yükseltme** üzerinde birleşmiştir:
1. **Post-LayerNorm $\longrightarrow$ `Pre-Norm RMSNorm` (Root Mean Square Normalization)**
2. **Absolute Sinusoidal Position $\longrightarrow$ `RoPE` (Rotary Position Embedding) & `NTK / YaRN Scaling`**
3. **ReLU MLP $\longrightarrow$ `SwiGLU` (Swish-Gated Linear Unit)**

```
   KLASİK TRANSFORMER (2017)               MODERN FRONTIER TRANSFORMER (Llama-3 / Opus)
  ───────────────────────────             ──────────────────────────────────────────────
   x ──► Multi-Head Attention              x ──┬──► RMSNorm ──► GQA (RoPE'lu) ──► (+)
   │              │                            └──────── (Temiz Residual Otobanı) ─┘
   └────► (+) ◄───┘                                               │
           │                                   ┌──────────────────┴──────────────────┐
     LayerNorm (Post-Norm)                     ▼                                     │
           │                                RMSNorm ──► SwiGLU (Gate * Up -> Down) ──► (+)
     Linear -> ReLU -> Linear                                                        │
           │                                                                    Sonraki Katman
     LayerNorm (Post-Norm)
```

---

### 1. `Pre-Norm` Otobanı ve `RMSNorm` (Root Mean Square Layer Normalization)

#### A) Neden `Post-Norm` Yerine `Pre-Norm`?
Klasik mimaride normalizasyon katmanı **Residual Connection (`+`)** işleminden **sonra** (`Post-Norm`) duruyordu. Bu durum geri yayılımda (`Backward Pass`) en üst katmandan en alt katmana inen gradyanın her katmanda normalizasyon türevine bölünmesine ve derin ağlarda kararsızlığa yol açıyordu.
**`Pre-Norm`** mimarisinde ise `RMSNorm` ana koldan ayrılan **yan kola** konulur (`x = x + Attention(RMSNorm(x))`). Böylece toplama (`+`) hattı, en son katmandan ilk katmana kadar hiçbir engelle karşılaşmadan akan **kesintisiz bir Gradyan Otobanı (`Unimpeded Gradient Highway`)** oluşturur!

#### B) Neden `LayerNorm` Yerine `RMSNorm` (Zhang & Sennrich, 2019)?
`LayerNorm`, ortalamayı çıkardıktan sonra variance değerinin epsilon eklenmiş kareköküyle ölçekler. RMSNorm ise mean centering uygulamadan root-mean-square ile ölçekler; iki işlemin varsayımları ve öğrenilen parametreleri aynı değildir.
**`RMSNorm`**, ortalama ($\mu$) hesabını ve $\beta$ kaydırma (`bias`) parametresini tamamen çöpe atar; yalnızca karelerin ortalamasının kareköküne (**Root Mean Square**) böler:

$$\text{RMS}(x) = \sqrt{\frac{1}{d} \sum_{i=1}^{d} x_i^2 + \epsilon}, \qquad \text{RMSNorm}(x)_i = \frac{x_i}{\text{RMS}(x)} \cdot \gamma_i$$

- **Maliyet:** RMSNorm daha az reduction hesabı gerektirebilir. Gerçek hız farkı kernel, tensor boyutu ve donanımda ölçülmelidir; sabit bir yüzde garanti edilmez.

---

### 2. `RoPE` (Rotary Position Embedding — Su et al., 2021)

Transformer'daki attention mekanizması ($\text{Attention}(Q, K, V)$) doğası gereği sıra körüdür; kelimelerin yerini değiştirsen de fark etmez. Peki bir kelimenin cümledeki pozisyonunu ($m \in \{0, 1, 2, \dots\}$) modele nasıl öğretiriz?
- Klasik modeller pozisyon vektörünü kelime vektörünün üzerine **topluyordu (`x + pos_emb`)**. Bu yöntem, içerik bilgisiyle konum bilgisini birbirine karıştırıyor ve mutlak pozisyonlara (`Absolute Position`) bağımlı kalıyordu.
- **`RoPE (Rotary Position Embedding)`** ise toplama yapmaz! Sorgu ($q$) ve Anahtar ($k$) vektörlerinin boyutlarını **ikişerli 2D düzlem çiftlerine** $(x_{2i}, x_{2i+1})$ ayırır ve her çifti token'ın pozisyonu $m$ ile orantılı bir **$m \cdot \theta_i$ açısıyla 2 boyutlu uzayda döndürür (`2D Rotation Matrix`)!**

$$\begin{bmatrix} x'_{2i} \\ x'_{2i+1} \end{bmatrix} = \begin{bmatrix} \cos(m\theta_i) & -\sin(m\theta_i) \\ \sin(m\theta_i) & \cos(m\theta_i) \end{bmatrix} \begin{bmatrix} x_{2i} \\ x_{2i+1} \end{bmatrix}, \qquad \theta_i = \text{base}^{-2i / d}$$

#### 🤯 RoPE'un Matematiksel Özelliği: İç Çarpım Yalnızca Bağıl Mesafeye ($m - n$) Bağlıdır!
Pozisyonu $m$ olan döndürülmüş bir sorgu vektörü $R(m)q$ ile pozisyonu $n$ olan döndürülmüş bir anahtar vektörü $R(n)k$'nın dikkat skoru (**Dot Product**) alındığında, rotasyon matrislerinin ortogonal özelliği ($R(m)^T R(n) = R(n - m)$) sayesinde:

$$\langle R(m)q, \, R(n)k \rangle = q^T R(n - m) k$$

Yani dikkat skoru kelimelerin cümlenin başında mı (`m=5, n=2`) yoksa ortasında mı (`m=1005, n=1002`) olduğundan tamamen bağımsızdır; **yalnızca aralarındaki bağıl mesafeye ($m - n = 3$) bağlıdır!** Üstelik vektörün normunu (uzunluğunu) hiç bozmaz ($\|R(\alpha)x\| = \|x\|$).
- **Context extension:** RoPE base/frequency ayarları context uzatma yöntemlerinin bir parçasıdır. Ayarı değiştirmek tek başına yeni uzunlukta model kalitesini veya kararlı extrapolation davranışını kanıtlamaz.

---

### 3. `SwiGLU` Feed-Forward Ağı (Shazeer, 2020)

Klasik Transformer'da her dikkat katmanından sonra iki matrisli bir MLP gelirdi: $\text{FFN}(x) = \max(0, x W_1) W_2$.
Noam Shazeer (2020), **`SwiGLU` (Swish-Gated Linear Unit)** mimarisinin aynı hesaplama bütçesinde tüm diğer aktivasyonları ezici biçimde geçtiğini gösterdi. `SwiGLU` iki değil, **üç doğrusal projeksiyon matrisi** (`W_gate`, `W_up`, `W_down`) ve $\text{SiLU}(z) = \text{Swish}_1(z) = \frac{z}{1 + e^{-z}}$ aktivasyonunu kullanır:

$$\text{SwiGLU}(x) = \Big( \text{SiLU}(x W_{\text{gate}}) \odot (x W_{\text{up}}) \Big) W_{\text{down}}$$

Buradaki $\odot$ (**Hadamard / Element-wise Product**), bilgi akışını kontrol eden **öğrenilebilir bir kapı (`Learnable Gate`)** görevi görür: `W_gate` kolu hangi özelliklerin geçeceğine karar veren musluktur, `W_up` kolu ise taşınan bilgidir!
*(Not: Üç matris kullanıldığı için toplam parametre sayısını klasik $4d$ MLP ile eşit tutmak amacıyla ara gizli boyut $4d$ yerine $\frac{2}{3} \cdot 4d = \frac{8}{3}d$ olarak seçilir ve GPU Tensor Core verimliliği için 256'nın katına yuvarlanır).*

Şimdi bu üç modern bileşeni saf Python ile uçtan uca çalıştıralım:

```python
import math

def rmsnorm(x, gamma, eps=1e-6):
    rms = math.sqrt(sum(v * v for v in x) / len(x) + eps)
    return [(v / rms) * g for v, g in zip(x, gamma)]

def rope_uygula(x, pos, base=10000.0):
    d = len(x)
    out = [0.0] * d
    for i in range(0, d, 2):
        theta = base ** (-float(i) / d)
        aci = pos * theta
        cos_a, sin_a = math.cos(aci), math.sin(aci)
        x0, x1 = x[i], x[i + 1]
        out[i]     = x0 * cos_a - x1 * sin_a
        out[i + 1] = x0 * sin_a + x1 * cos_a
    return out

x_ham = [3.0, 4.0, 0.0, 2.0]
x_norm = rmsnorm(x_ham, [1.0, 1.0, 1.0, 1.0])
x_rope = rope_uygula(x_norm, pos=3)
norm_once = round(sum(v * v for v in x_norm), 5)
norm_sonra = round(sum(v * v for v in x_rope), 5)
print(f"RMSNorm Sonrasi: {[round(v, 3) for v in x_norm]}")
print(f"RoPE Norm Korunumu -> Once: {norm_once} | Sonra: {norm_sonra}")
```

---

### 4. Gerçek Üretim Kodu: PyTorch `LlamaRMSNorm` ve `LlamaSwiGLUMLP`

Gerçek üretimde (`transformers` / `torchtune` / `vLLM`) `FP16 / BF16` taşmalarını (`Underflow / Overflow`) önlemek için `RMSNorm` içindeki kare alma işlemi mutlaka `torch.float32` hassasiyetine yükseltilerek (`Upcasting`) yapılır:

```python norun
import torch
import torch.nn as nn
import torch.nn.functional as F

class LlamaRMSNorm(nn.Module):
    def __init__(self, hidden_size: int, eps: float = 1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(hidden_size))
        self.variance_epsilon = eps

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        input_dtype = hidden_states.dtype
        # Kritik Üretim Detayı: Kare toplamında FP16 taşmasını önlemek için FP32'ye çıkılır!
        hidden_states = hidden_states.to(torch.float32)
        variance = hidden_states.pow(2).mean(-1, keepdim=True)
        hidden_states = hidden_states * torch.rsqrt(variance + self.variance_epsilon)
        return self.weight * hidden_states.to(input_dtype)

class LlamaSwiGLUMLP(nn.Module):
    def __init__(self, dim: int, hidden_dim: int):
        super().__init__()
        # Modern LLM'lerde Linear katmanlarda bias=False kullanılır!
        self.gate_proj = nn.Linear(dim, hidden_dim, bias=False)
        self.up_proj   = nn.Linear(dim, hidden_dim, bias=False)
        self.down_proj = nn.Linear(hidden_dim, dim, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # SwiGLU(x) = (SiLU(x @ W_gate) * (x @ W_up)) @ W_down
        return self.down_proj(F.silu(self.gate_proj(x)) * self.up_proj(x))
```

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [RMSNorm makalesi](https://arxiv.org/abs/1910.07467). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: tahmin RoPE Döndürmesinin Bağıl Mesafe (Relative Distance) Değişmezliği
Aşağıdaki kodda aynı $q = [1.0, 0.0]$ ve $k = [0.0, 1.0]$ vektörleri önce `m=2, n=1` pozisyonlarında (fark $2-1=1$), ardından cümlenin çok ilerisinde `m=105, n=104` pozisyonlarında (fark yine $105-104=1$) `RoPE` ile döndürülüp iç çarpımları (`dot product`) alınıyor. Çıktı nedir?

```python
import math

def dondur(v, pos, theta=0.5):
    c, s = math.cos(pos * theta), math.sin(pos * theta)
    return [v[0] * c - v[1] * s, v[0] * s + v[1] * c]

def ic_carpim(a, b):
    return round(a[0] * b[0] + a[1] * b[1], 4)

q, k = [1.0, 0.0], [0.0, 1.0]
skor_basi = ic_carpim(dondur(q, 2), dondur(k, 1))
skor_sonu = ic_carpim(dondur(q, 105), dondur(k, 104))
print(f"Bas(2,1)={skor_basi} | Son(105,104)={skor_sonu} | EsitMi={skor_basi == skor_sonu}")
```

???

```cikti
Bas(2,1)=0.4794 | Son(105,104)=0.4794 | EsitMi=True
```
`RoPE` ortogonal bir döndürme matrisi olduğu için $\langle R(m)q, R(n)k \rangle$ iç çarpımı mutlak pozisyonlara ($2$ veya $105$) değil, yalnızca pozisyon farkına ($m - n = 1$) bağlıdır. Bu örnekte $q = [1, 0]$ ve $k = [0, 1]$ olduğu için skor $\sin((m - n)\theta) = \sin(1 \cdot 0.5) \approx 0.4794$ olur; işaret pozitiftir çünkü sorgu anahtardan bir adım ileride döndürülmüştür. Bu yüzden her iki durumda da dikkat skoru birebir aynı (`0.4794`) çıkar ve `EsitMi=True` yazdırır!
:::

::: gorev 1 · Pre-Norm RMSNorm ve 2D RoPE Döndürme Hesabı
`rmsnorm_ve_rope(vektor, gamma, pozisyon, teta_taban=10000.0, eps=1e-6)` işlevini yaz.

Parametreler:
- `vektor`: Çift uzunluklu ($d \in \{2, 4, 6, \dots\}$) kayan noktalı sayı listesi (`list[float]`).
- `gamma`: `vektor` ile aynı uzunlukta ölçekleme ağırlıkları (`list[float]`).
- `pozisyon`: Token'ın dizideki tam sayı konumu $m \ge 0$.
- `teta_taban`: RoPE taban frekansı (varsayılan `10000.0`).
- `eps`: Sıfıra bölünmeyi önleyen sabit (varsayılan `1e-6`).

İşlevin yapması gerekenler:
1. Girdi listelerini değiştirme. Önce `vektor` üzerine **RMSNorm** uygula:
   $$\text{rms} = \sqrt{\frac{1}{d}\sum_{j=0}^{d-1} x_j^2 + \text{eps}}, \qquad \hat{x}_j = \frac{x_j}{\text{rms}} \cdot \gamma_j$$
2. Ardından normalize edilmiş $\hat{x}$ vektörünün her ardışık ikilisini $(2i, 2i+1)$ — burada çift başlangıç indisi $k = 2i \in \{0, 2, 4, \dots, d-2\}$ — şu frekans ve açıyla **2D RoPE** rotasyonuna sok:
   $$\theta_k = \text{teta\_taban}^{-k / d}, \qquad \alpha_k = \text{pozisyon} \cdot \theta_k$$
   $$y_k = \hat{x}_k \cos(\alpha_k) - \hat{x}_{k+1} \sin(\alpha_k)$$
   $$y_{k+1} = \hat{x}_k \sin(\alpha_k) + \hat{x}_{k+1} \cos(\alpha_k)$$
3. Sonuçta:
   - `"rmsnorm"`: Normalize edilmiş $\hat{x}$ listesi (elemanları `round(v, 6)` ile yuvarlanmış),
   - `"rope"`: Döndürülmüş $y$ listesi (elemanları `round(v, 6)` ile yuvarlanmış),
   - `"norm_korundu_mu"`: $\hat{x}$ ile $y$'nin Öklid kare normlarının ($\sum v^2$) farkının $10^{-5}$'ten küçük olup olmadığını belirten `bool` (`True`).

```starter
def rmsnorm_ve_rope(vektor, gamma, pozisyon, teta_taban=10000.0, eps=1e-6):
    # KUSURLU BAŞLANGIÇ KODU: RMSNorm ve RoPE rotasyonunu uygulamadan girdiyi döndürüyor!
    return {
        "rmsnorm": list(vektor),
        "rope": list(vektor),
        "norm_korundu_mu": False,
    }

print("Çıktı:", rmsnorm_ve_rope([3.0, 4.0, 0.0, 0.0], [1.0, 1.0, 1.0, 1.0], pozisyon=2))
```

```test
import copy
import math

def sozlesme(fn):
    try:
        v = [3.0, 4.0, 0.0, 0.0]
        g = [1.0, 1.0, 1.0, 1.0]
        v_k, g_k = copy.deepcopy(v), copy.deepcopy(g)
        # rms = sqrt((9 + 16 + 0 + 0)/4 + 0) = sqrt(6.25) = 2.5
        # rmsnorm = [3/2.5, 4/2.5, 0, 0] = [1.2, 1.6, 0.0, 0.0]
        # pos=0 olduğunda cos(0)=1, sin(0)=0 -> rope == rmsnorm olmalı!
        s0 = fn(v, g, pozisyon=0, teta_taban=10000.0, eps=0.0)
        if v != v_k or g != g_k or not isinstance(s0, dict):
            return False
        if s0["rmsnorm"] != [1.2, 1.6, 0.0, 0.0] or s0["rope"] != [1.2, 1.6, 0.0, 0.0]:
            return False
        if s0["norm_korundu_mu"] is not True:
            return False

        # pos=1, d=4: k=0 için theta_0 = 10000^(0) = 1.0 radyan
        # y0 = 1.2 * cos(1) - 1.6 * sin(1), y1 = 1.2 * sin(1) + 1.6 * cos(1)
        s1 = fn(v, [2.0, 0.5, 1.0, 1.0], pozisyon=1, teta_taban=10000.0, eps=0.0)
        # rmsnorm = [2.4, 0.8, 0.0, 0.0]
        b_y0 = round(2.4 * math.cos(1.0) - 0.8 * math.sin(1.0), 6)
        b_y1 = round(2.4 * math.sin(1.0) + 0.8 * math.cos(1.0), 6)
        if s1["rmsnorm"] != [2.4, 0.8, 0.0, 0.0]:
            return False
        if s1["rope"] != [b_y0, b_y1, 0.0, 0.0] or s1["norm_korundu_mu"] is not True:
            return False

        return True
    except Exception:
        return False

varsayilan_girdi = ([1.0, 2.0, 3.0, 4.0], [1.0] * 4, 19)
ok(rmsnorm_ve_rope(*varsayilan_girdi) == rmsnorm_ve_rope(*varsayilan_girdi, 10000.0, 1e-6), "RMSNorm ve RoPE varsayılanları sözleşmeyle eşleşmeli")
kucuk_girdi = ([1e-4, 2e-4, 3e-4, 4e-4], [1.0] * 4, 19)
ok(rmsnorm_ve_rope(*kucuk_girdi) == rmsnorm_ve_rope(*kucuk_girdi, 10000.0, 1e-6), "küçük RMS değerinde varsayılan epsilon korunmalı")
ok(sozlesme(rmsnorm_ve_rope), "RMSNorm ölçeklemesi ve 2D RoPE rotasyonu doğru hesaplanmalı")

def m_mean_cikaran(vektor, gamma, pozisyon, teta_taban=10000.0, eps=1e-6):
    # Klasik LayerNorm gibi ortalama çıkaran hatalı mutant
    r = rmsnorm_ve_rope(vektor, gamma, pozisyon, teta_taban, eps)
    r["rmsnorm"][0] -= 0.5
    return r

def m_aci_yanlis(vektor, gamma, pozisyon, teta_taban=10000.0, eps=1e-6):
    r = rmsnorm_ve_rope(vektor, gamma, pozisyon, teta_taban, eps)
    if pozisyon > 0:
        r["rope"] = list(r["rmsnorm"])
    return r

for ad, mutant in [("RMSNorm yerine ortalama çıkaran", m_mean_cikaran), ("RoPE açısını döndürmeyen", m_aci_yanlis)]:
    ok(not sozlesme(mutant), "hatalı çözüm/mutant yakalanmalı: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef rmsnorm_ve_rope(vektor, gamma, pozisyon, teta_taban=10000.0, eps=1e-06):\n    d = len(vektor)\n    rms = math.sqrt(sum((x * x for x in vektor)) / d + eps)\n    norm_x = [x / rms * g for x, g in zip(vektor, gamma)]\n    rope_y = [0.0] * d\n    for k in range(0, d, 2):\n        theta = teta_taban ** (-float(k) / d)\n        aci = pozisyon * theta\n        c, s = (math.cos(aci), math.sin(aci))\n        x0, x1 = (norm_x[k], norm_x[k + 1])\n        rope_y[k] = x0 * c - x1 * s\n        rope_y[k + 1] = x0 * s + x1 * c\n    norm_once = sum((v * v for v in norm_x))\n    norm_sonra = sum((v * v for v in rope_y))\n    korundu = abs(norm_once - norm_sonra) < 1e-05\n    return {'rmsnorm': [round(v, 6) for v in norm_x], 'rope': [round(v, 6) for v in rope_y], 'norm_korundu_mu': korundu}", 'referans', 'exec'), _REF)
_t, _g = _ff(rmsnorm_ve_rope, _REF['rmsnorm_ve_rope'], ([3.0, 4.0, 0.0, 0.0], [1.0, 1.0, 1.0, 1.0], 2, 10000.0, 1e-06), tohum=2682, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (rmsnorm_ve_rope): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def rmsnorm_ve_rope(vektor, gamma, pozisyon, teta_taban=10000.0, eps=1e-6):
    d = len(vektor)
    rms = math.sqrt(sum(x * x for x in vektor) / d + eps)
    norm_x = [(x / rms) * g for x, g in zip(vektor, gamma)]

    rope_y = [0.0] * d
    for k in range(0, d, 2):
        theta = teta_taban ** (-float(k) / d)
        aci = pozisyon * theta
        c, s = math.cos(aci), math.sin(aci)
        x0, x1 = norm_x[k], norm_x[k + 1]
        rope_y[k] = x0 * c - x1 * s
        rope_y[k + 1] = x0 * s + x1 * c

    norm_once = sum(v * v for v in norm_x)
    norm_sonra = sum(v * v for v in rope_y)
    korundu = abs(norm_once - norm_sonra) < 1e-5

    return {
        "rmsnorm": [round(v, 6) for v in norm_x],
        "rope": [round(v, 6) for v in rope_y],
        "norm_korundu_mu": korundu,
    }
```

```hint
Önce `rms = math.sqrt(sum(x*x for x in vektor)/d + eps)` ile normalize vektörü bul. Ardından `for k in range(0, d, 2):` döngüsüyle `theta = teta_taban ** (-float(k) / d)` frekansını hesaplayıp 2D rotasyon formülünü uygula.
```
:::

::: gorev 2 · SwiGLU Feed-Forward Ağı (Gate, Up ve Down Projeksiyonu)
`swiglu_ileri(x, W_gate, W_up, W_down)` işlevini yaz.

Bir Transformer bloğunun **SwiGLU** katmanı şu denklemi çalıştırır:
$$\text{SiLU}(z) = \frac{z}{1 + e^{-z}}$$
$$h = \text{SiLU}(x \cdot W_{\text{gate}}) \odot (x \cdot W_{\text{up}})$$
$$y = h \cdot W_{\text{down}}$$

Parametreler:
- `x`: Giriş vektörü ($D_{\text{model}}$ uzunluğunda tek boyutlu liste `list[float]`).
- `W_gate`: Kapı projeksiyon matrisi ($D_{\text{model}} \times D_{\text{ffn}}$ boyutunda 2B liste).
- `W_up`: Yukarı projeksiyon matrisi ($D_{\text{model}} \times D_{\text{ffn}}$ boyutunda 2B liste).
- `W_down`: Aşağı projeksiyon matrisi ($D_{\text{ffn}} \times D_{\text{model}}$ boyutunda 2B liste).

İşlev, girdileri değiştirmeden tüm sayısal çıktıları `round(val, 6)` ile yuvarlanmış şu sözlüğü döndürmelidir:
- `"gate_aktivasyon"`: $\text{SiLU}(x \cdot W_{\text{gate}})$ vektörü ($D_{\text{ffn}}$ uzunluğunda)
- `"gizli_durum"`: $h = \text{SiLU}(x \cdot W_{\text{gate}}) \odot (x \cdot W_{\text{up}})$ vektörü ($D_{\text{ffn}}$ uzunluğunda)
- `"cikti"`: $y = h \cdot W_{\text{down}}$ vektörü ($D_{\text{model}}$ uzunluğunda)

```starter
def swiglu_ileri(x, W_gate, W_up, W_down):
    # KUSURLU BAŞLANGIÇ KODU: SiLU kapılaması ve matris çarpımlarını yapmadan sıfır döndürüyor!
    d_model = len(x)
    d_ffn = len(W_gate[0])
    return {
        "gate_aktivasyon": [0.0] * d_ffn,
        "gizli_durum": [0.0] * d_ffn,
        "cikti": [0.0] * d_model,
    }

x_orn = [1.0, 2.0]
Wg = [[0.0, 1.0], [0.0, -0.5]]
Wu = [[2.0, 1.0], [1.0, 3.0]]
Wd = [[1.0, 0.5], [2.0, -1.0]]
print("SwiGLU:", swiglu_ileri(x_orn, Wg, Wu, Wd))
```

```test
import copy
import math

def sozlesme(fn):
    try:
        x = [1.0, -2.0]
        # W_gate: 2x3, W_up: 2x3, W_down: 3x2
        Wg = [[0.0, 2.0, -1.0], [0.0, 1.0, 0.0]]
        Wu = [[3.0, 1.0, 2.0], [-1.0, 2.0, 0.5]]
        Wd = [[1.0, 2.0], [0.5, -1.0], [-1.0, 0.5]]
        xk = copy.deepcopy(x)
        r = fn(x, Wg, Wu, Wd)
        if x != xk or not isinstance(r, dict):
            return False
        # x @ Wg = [0.0, 0.0, -1.0]
        # SiLU(0.0) = 0.0, SiLU(-1.0) = -1.0 / (1 + e^1)
        silu_m1 = -1.0 / (1.0 + math.exp(1.0))
        beklenen_gate = [0.0, 0.0, round(silu_m1, 6)]
        # x @ Wu = [1*3 + (-2)*(-1), 1*1 + (-2)*2, 1*2 + (-2)*0.5] = [5.0, -3.0, 1.0]
        # gizli h = gate * up = [0.0, 0.0, silu_m1 * 1.0]
        beklenen_h = [0.0, 0.0, round(silu_m1, 6)]
        # y = h @ Wd = [silu_m1 * (-1.0), silu_m1 * 0.5]
        beklenen_y = [round(-silu_m1, 6), round(0.5 * silu_m1, 6)]
        return (
            r.get("gate_aktivasyon") == beklenen_gate
            and r.get("gizli_durum") == beklenen_h
            and r.get("cikti") == beklenen_y
        )
    except Exception:
        return False

ok(swiglu_ileri([1.0], [[0.0]], [[1.0]], [[1.0]])["cikti"] == [0.0], "tek giriş boyutlu SwiGLU geçerli olmalı")
ok(sozlesme(swiglu_ileri), "SiLU(x @ W_gate) * (x @ W_up) @ W_down tam olarak hesaplanmalı")

def m_relu_kullanan(x, W_gate, W_up, W_down):
    # SiLU yerine ReLU kullanan hatalı mutant (negatif bölgede 0 verir!)
    r = swiglu_ileri(x, W_gate, W_up, W_down)
    r["gate_aktivasyon"] = [max(0.0, v) for v in r["gate_aktivasyon"]]
    r["gizli_durum"] = [max(0.0, v) for v in r["gizli_durum"]]
    return r

def m_up_unutan(x, W_gate, W_up, W_down):
    r = swiglu_ileri(x, W_gate, W_up, W_down)
    r["cikti"] = [0.0 for _ in r["cikti"]]
    return r

for ad, mutant in [("SiLU yerine ReLU kullanan", m_relu_kullanan), ("çıktı projeksiyonunu bozan", m_up_unutan)]:
    ok(not sozlesme(mutant), "hatalı çözüm/mutant yakalanmalı: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef swiglu_ileri(x, W_gate, W_up, W_down):\n    d_model = len(x)\n    d_ffn = len(W_gate[0])\n    gate_lin = [sum((x[i] * W_gate[i][j] for i in range(d_model))) for j in range(d_ffn)]\n    up_lin = [sum((x[i] * W_up[i][j] for i in range(d_model))) for j in range(d_ffn)]\n    gate_act = [z / (1.0 + math.exp(-z)) for z in gate_lin]\n    gizli = [g * u for g, u in zip(gate_act, up_lin)]\n    cikti = [sum((gizli[j] * W_down[j][i] for j in range(d_ffn))) for i in range(d_model)]\n    return {'gate_aktivasyon': [round(v, 6) for v in gate_act], 'gizli_durum': [round(v, 6) for v in gizli], 'cikti': [round(v, 6) for v in cikti]}", 'referans', 'exec'), _REF)
_t, _g = _ff(swiglu_ileri, _REF['swiglu_ileri'], ([1.0, 2.0], [[0.0, 1.0], [0.0, -0.5]], [[2.0, 1.0], [1.0, 3.0]], [[1.0, 0.5], [2.0, -1.0]]), tohum=2348, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (swiglu_ileri): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def swiglu_ileri(x, W_gate, W_up, W_down):
    d_model = len(x)
    d_ffn = len(W_gate[0])

    # 1. Gate ve Up doğrusal projeksiyonları: x @ W_gate ve x @ W_up
    gate_lin = [sum(x[i] * W_gate[i][j] for i in range(d_model)) for j in range(d_ffn)]
    up_lin = [sum(x[i] * W_up[i][j] for i in range(d_model)) for j in range(d_ffn)]

    # 2. SiLU(z) = z / (1 + exp(-z)) ve Hadamard çarpımı
    gate_act = [z / (1.0 + math.exp(-z)) for z in gate_lin]
    gizli = [g * u for g, u in zip(gate_act, up_lin)]

    # 3. Down projeksiyonu: gizli @ W_down
    cikti = [sum(gizli[j] * W_down[j][i] for j in range(d_ffn)) for i in range(d_model)]

    return {
        "gate_aktivasyon": [round(v, 6) for v in gate_act],
        "gizli_durum": [round(v, 6) for v in gizli],
        "cikti": [round(v, 6) for v in cikti],
    }
```

```hint
Önce `gate_lin` ve `up_lin` vektörlerini hesapla. Her `z` elemanı için `z / (1.0 + math.exp(-z))` ile `SiLU` aktivasyonunu bul, `up_lin` ile eleman bazlı çarp (`gizli`) ve son olarak `W_down` ile çarparak `cikti` vektörünü üret.
```
:::

::: anlat Gerçek deney: SmolLM2'nin gerçek katmanlarında RMSNorm, RoPE ve SwiGLU
Final, yerel önbellekteki gerçek **SmolLM2-135M** modelini kullanır (indirme yok). SmolLM2 tam olarak bu dersin anlattığı Llama mimarisidir: Pre-Norm `RMSNorm`, `RoPE` ve `SwiGLU`. Senin saf Python işlevlerin modelin **kendi ağırlıklarıyla** çalışır ve sonuç modelin kendi katmanlarının çıktısıyla karşılaştırılır:

- **RMSNorm:** gerçek token gömmeleri, 0. katmanın gerçek `gamma` ağırlıkları ve modelin `rms_norm_eps` değeriyle (`1e-5`); beklenen değer `input_layernorm` çıktısıdır.
- **RoPE:** 0. katmanın gerçek sorgu vektörü (head 0, 64 boyut), modelin taban frekansıyla (`rope_theta = 100000`). Burada bir tuzak var: Hugging Face Llama gerçeklemesi boyutları **yarım döndürme** (`rotate_half`) düzeninde eşler, yani $(i, i + d/2)$ çiftleri birlikte döner. Senin işlevin ise ardışık $(2j, 2j+1)$ çiftlerini döndürür. Frekanslar aynıdır; deney vektörü senin düzenine çevirip sonucu geri çevirir. (RMSNorm'u etkisiz kılmak için `gamma = rms(x)` ve `eps = 0` verilir.)
- **SwiGLU:** 1. katmanın gerçek `gate_proj`, `up_proj`, `down_proj` ağırlıklarıyla (576 → 1536 → 576), gerçek normalize gizli durumlarda; beklenen değer modelin `mlp` çıktısıdır.

Son olarak aynı ağırlıklarla RoPE yanlış düzende (ardışık çift) uygulanır ve gerçek bir cümlede **perplexity** ölçülür. Model hata vermez, sadece sessizce kötüleşir: bir checkpoint'i başka bir gerçeklemeye taşırken düzen karıştırılırsa ilk belirti budur.

**Güvenlik yönü — ağırlık kurcalama ve bütünlük:** 12. katmanın tek bir RMSNorm kazancı (en büyük kanal) önce ×1.02, sonra ×30 yapılır. Küçük değişiklik perplexity'yi neredeyse hiç değiştirmez; bir davranış testi onu göremez, ama gizli bir arka kapının ilk adımı olabilir. Büyük değişiklik modeli belirgin bozar. Her iki durumda da her tensörün SHA-256 özeti alınır: yalnız kurcalanan tensörün özeti değişir. Model dosyalarının bütünlüğü davranışla değil imzalı özetlerle denetlenmelidir (OWASP LLM03 tedarik zinciri).

Kabul: üç işlevin farksal taramayı geçmesi; RMSNorm ve RoPE göreli farkının `1e-5`, SwiGLU'nun `1e-4` altında olması; RoPE'un normu koruması; yanlış düzende perplexity'nin en az 2 katına çıkması ve düzen geri alınınca eski değere dönmesi. Ayrıca ×1.02'lik kurcalama perplexity'yi %1'den az değiştirmeli, ×30'luk kurcalama %10'dan fazla bozmalı ve tensör özetleri iki durumda da yalnız o tensörü işaretlemelidir.

**Kanıt dosyasını oku:** `rmsnorm_goreli_fark`, `rope_goreli_fark`, `swiglu_goreli_fark`, `ppl_dogru` ve `ppl_yanlis_duzen` alanlarını karşılaştır. Soru 1: Göreli farklar neden sıfır değil de 1e-7 mertebesinde? (İpucu: model float32, senin hesabın float64 ve 6 basamağa yuvarlıyor.) Soru 2: Düzen hatası neden bir istisna fırlatmıyor? Soru 3: Bir modeli başka bir çerçeveye taşırken bu hatayı hangi tek sayısal kontrolle yakalardın?
:::

::: gorev Gerçek deney · Gerçek SmolLM2 katmanlarıyla RMSNorm, RoPE ve SwiGLU karşılaştırması
Önceki görevlerdeki `rmsnorm_ve_rope`, `swiglu_ileri` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 180
```
```starter
import ai_lab
def rmsnorm_ve_rope(vektor, gamma, pozisyon, teta_taban=10000.0, eps=1e-06):
    return {'rmsnorm': list(vektor), 'rope': list(vektor), 'norm_korundu_mu': False}

def swiglu_ileri(x, W_gate, W_up, W_down):
    d_model = len(x)
    d_ffn = len(W_gate[0])
    return {'gate_aktivasyon': [0.0] * d_ffn, 'gizli_durum': [0.0] * d_ffn, 'cikti': [0.0] * d_model}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_03 as D
    D.goster(rmsnorm_ve_rope, swiglu_ileri)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_ref_rotate_pairs', '_ref_perplexity', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
rmsnorm_ve_rope = need("rmsnorm_ve_rope")
swiglu_ileri = need("swiglu_ileri")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef rmsnorm_ve_rope(vektor, gamma, pozisyon, teta_taban=10000.0, eps=1e-06):\n    d = len(vektor)\n    rms = math.sqrt(sum((x * x for x in vektor)) / d + eps)\n    norm_x = [x / rms * g for x, g in zip(vektor, gamma)]\n    rope_y = [0.0] * d\n    for k in range(0, d, 2):\n        theta = teta_taban ** (-float(k) / d)\n        aci = pozisyon * theta\n        c, s = (math.cos(aci), math.sin(aci))\n        x0, x1 = (norm_x[k], norm_x[k + 1])\n        rope_y[k] = x0 * c - x1 * s\n        rope_y[k + 1] = x0 * s + x1 * c\n    norm_once = sum((v * v for v in norm_x))\n    norm_sonra = sum((v * v for v in rope_y))\n    korundu = abs(norm_once - norm_sonra) < 1e-05\n    return {'rmsnorm': [round(v, 6) for v in norm_x], 'rope': [round(v, 6) for v in rope_y], 'norm_korundu_mu': korundu}\n\nimport math\n\ndef swiglu_ileri(x, W_gate, W_up, W_down):\n    d_model = len(x)\n    d_ffn = len(W_gate[0])\n    gate_lin = [sum((x[i] * W_gate[i][j] for i in range(d_model))) for j in range(d_ffn)]\n    up_lin = [sum((x[i] * W_up[i][j] for i in range(d_model))) for j in range(d_ffn)]\n    gate_act = [z / (1.0 + math.exp(-z)) for z in gate_lin]\n    gizli = [g * u for g, u in zip(gate_act, up_lin)]\n    cikti = [sum((gizli[j] * W_down[j][i] for j in range(d_ffn))) for i in range(d_model)]\n    return {'gate_aktivasyon': [round(v, 6) for v in gate_act], 'gizli_durum': [round(v, 6) for v in gizli], 'cikti': [round(v, 6) for v in cikti]}", 'referans', 'exec'), _REF)
_t, _g = _ff(rmsnorm_ve_rope, _REF['rmsnorm_ve_rope'], ([3.0, 4.0, 0.0, 0.0], [1.0, 1.0, 1.0, 1.0], 2, 10000.0, 1e-06), tohum=2682, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (rmsnorm_ve_rope): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(swiglu_ileri, _REF['swiglu_ileri'], ([1.0, 2.0], [[0.0, 1.0], [0.0, -0.5]], [[2.0, 1.0], [1.0, 3.0]], [[1.0, 0.5], [2.0, -1.0]]), tohum=2348, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (swiglu_ileri): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
kontrol(rmsnorm_ve_rope([1.0, 2.0, 3.0, 4.0], [1.0] * 4, 19) == _REF['rmsnorm_ve_rope']([1.0, 2.0, 3.0, 4.0], [1.0] * 4, 19), "varsayılan teta_taban ve eps korunmalı")
kontrol(rmsnorm_ve_rope([1e-4, 2e-4, 3e-4, 4e-4], [1.0] * 4, 19) == _REF['rmsnorm_ve_rope']([1e-4, 2e-4, 3e-4, 4e-4], [1.0] * 4, 19), "küçük RMS değerinde varsayılan eps korunmalı")
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_03 as D
try: r = D.deney(rmsnorm_ve_rope, swiglu_ileri)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['rmsnorm_ayni'], 'RMSNorm gerçek input_layernorm çıktısıyla aynı (göreli fark < 1e-5)')
kontrol(r['rope_ayni'], 'RoPE, düzen eşlemesiyle gerçek rotary çıktısıyla aynı (göreli fark < 1e-5)')
kontrol(r['swiglu_ayni'], 'SwiGLU gerçek MLP çıktısıyla aynı (göreli fark < 1e-4)')
kontrol(r['norm_korundu'], 'RoPE gerçek sorgu vektörlerinin normunu koruyor')
kontrol(r['yanlis_duzen_bozar'], "yanlış RoPE düzeni perplexity'yi en az 2 katına çıkarıyor, düzen geri alınınca eski değer")
kontrol(r['kurcalama_tespit'] and r['kucuk_kurcalama_gizli'] and r['buyuk_kurcalama_bozar'], 'küçük kurcalama davranışta görünmüyor, tensör başına SHA-256 iki kurcalamayı da doğru tensörde yakalıyor')
ai_lab.kanit_yaz("ai-uretim-03-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-03", "deney": r})
```
```solution
import ai_lab
import math

def rmsnorm_ve_rope(vektor, gamma, pozisyon, teta_taban=10000.0, eps=1e-06):
    d = len(vektor)
    rms = math.sqrt(sum((x * x for x in vektor)) / d + eps)
    norm_x = [x / rms * g for x, g in zip(vektor, gamma)]
    rope_y = [0.0] * d
    for k in range(0, d, 2):
        theta = teta_taban ** (-float(k) / d)
        aci = pozisyon * theta
        c, s = (math.cos(aci), math.sin(aci))
        x0, x1 = (norm_x[k], norm_x[k + 1])
        rope_y[k] = x0 * c - x1 * s
        rope_y[k + 1] = x0 * s + x1 * c
    norm_once = sum((v * v for v in norm_x))
    norm_sonra = sum((v * v for v in rope_y))
    korundu = abs(norm_once - norm_sonra) < 1e-05
    return {'rmsnorm': [round(v, 6) for v in norm_x], 'rope': [round(v, 6) for v in rope_y], 'norm_korundu_mu': korundu}

import math

def swiglu_ileri(x, W_gate, W_up, W_down):
    d_model = len(x)
    d_ffn = len(W_gate[0])
    gate_lin = [sum((x[i] * W_gate[i][j] for i in range(d_model))) for j in range(d_ffn)]
    up_lin = [sum((x[i] * W_up[i][j] for i in range(d_model))) for j in range(d_ffn)]
    gate_act = [z / (1.0 + math.exp(-z)) for z in gate_lin]
    gizli = [g * u for g, u in zip(gate_act, up_lin)]
    cikti = [sum((gizli[j] * W_down[j][i] for j in range(d_ffn))) for i in range(d_model)]
    return {'gate_aktivasyon': [round(v, 6) for v in gate_act], 'gizli_durum': [round(v, 6) for v in gizli], 'cikti': [round(v, 6) for v in cikti]}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_03 as D
    D.goster(rmsnorm_ve_rope, swiglu_ileri)
```
```hint
Görev 1 ve görev 2 çözümlerini olduğu gibi buraya koy. Deney senin işlevlerini gerçek ağırlıklarla çağırır; işlevler doğruysa ek bir şey yapman gerekmez.
```
:::

::: anlat Sınır
Görevler RMSNorm ile 2 boyutlu RoPE dönüşünü ve SwiGLU ileri geçişini küçük vektörlerle saf Python'da hesaplatır; final adım bunları gerçek SmolLM2 katmanlarıyla karşılaştırır. Gerçek gerçeklemeler RoPE'u farklı boyut eşlemeleriyle uygular (ardışık çiftler yerine rotate_half düzeni); iki düzen aynı ağırlıklarla karıştırılırsa model sessizce bozulur. RMSNorm'daki kare toplamı FP32'de yapılmazsa BF16'da hassasiyet kaybı olur. RoPE bağıl konum verir ama eğitim uzunluğunun ötesine kendiliğinden genellemez; bunun için ölçekleme gerekir (ai-uretim-18).

Kaynaklar: [Zhang ve Sennrich 2019 - Root Mean Square Layer Normalization](https://arxiv.org/abs/1910.07467), [Su vd. 2021 - RoFormer: Enhanced Transformer with Rotary Position Embedding](https://arxiv.org/abs/2104.09864), [Shazeer 2020 - GLU Variants Improve Transformer](https://arxiv.org/abs/2002.05202).
:::

::: dusun
Modern LLM'lerde (`Llama-3`, `DeepSeek-V3`, `Mistral`) hem Attention içindeki `Q, K, V, O` projeksiyonlarında hem de `SwiGLU` içindeki `gate_proj, up_proj, down_proj` katmanlarında **`bias=False`** kullanılır (yani $xW + b$ yerine yalnızca $xW$ yapılır!).

Neden modern trilyon parametreli modellerde doğrusal katmanlardaki `bias` ($b$) vektörleri tamamen kaldırılmıştır? **Pre-Norm RMSNorm** katmanının ölçek/kaydırma davranışı, **`BF16` eğitimi sırasındaki gradyan kararlılığı** ve **GPU Tensor Core (`GEMM`) çekirdeklerinin bellek bant genişliği** açısından bu tasarım kararını değerlendir.
:::

::: ozet
- **Pre-Norm `RMSNorm`**, normalizasyonu yan kola alarak ana **Residual Stream** üzerinde kesintisiz bir gradyan otobanı açar; ortalama çıkarma (`mean centering`) adımını kaldırarak GPU üzerinde klasik `LayerNorm`'dan `%15-%30` daha hızlı çalışır.
- **`RoPE (Rotary Position Embedding)`**, sorgu ve anahtar vektörlerinin ikişerli boyut çiftlerini pozisyonla orantılı açılarla ($m\theta_i$) 2D düzlemde döndürür; böylece $\langle R(m)q, R(n)k \rangle$ dikkat skoru mutlak konuma değil, yalnızca iki token arasındaki **bağıl mesafeye ($m - n$)** duyarlı hale gelir.
- **`SwiGLU`**, klasik iki matrisli `ReLU` katmanı yerine $\text{SiLU}(x W_{\text{gate}}) \odot (x W_{\text{up}}) W_{\text{down}}$ kapılı mimarisini kullanarak negatif bölgede yumuşak gradyan akışı ve çarpımsal özellik seçimi (**Multiplicative Gating**) sağlar.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Pre-Norm ve `RMSNorm` (25 sn).** "Normalizasyonu yan kola almak artık akışta (`residual stream`) kesintisiz bir gradyan yolu bırakır; `RMSNorm` ortalama çıkarma adımını atıp yalnız karekök ortalama kareyle ölçeklediği için `LayerNorm`'dan daha az bellek okur."
2. **`RoPE` ve bağıl mesafe (35 sn).** "Konumu vektöre toplamak yerine sorgu ve anahtarın ikişerli boyut çiftlerini $m\theta_i$ açısıyla döndürürüz; ortogonal döndürme vektör normunu korur ve $\langle R(m)q, R(n)k \rangle$ iç çarpımını yalnızca bağıl fark $m-n$'ye bağımlı kılar."
3. **`SwiGLU` çarpımsal kapısı (30 sn).** "Tek matrisli `ReLU` yerine $\text{SiLU}(xW_{\text{gate}}) \odot (xW_{\text{up}})$ kapısı hem negatif bölgede türevi öldürmez hem de hangi özelliğin geçeceğini girdiye bağlı seçer."
4. **Soru (30 sn).** "Eğitimde görülmemiş çok uzun bağlamlarda `RoPE` açıları eğitim aralığının dışına çıktığında dikkat dağılımı neden bozulur ve taban frekans (`theta`) ölçeklemesi bunu nasıl yumuşatır?"
:::
