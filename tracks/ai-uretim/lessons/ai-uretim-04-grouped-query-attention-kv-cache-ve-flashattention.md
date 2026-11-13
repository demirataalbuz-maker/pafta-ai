---
id: ai-uretim-04
title: "Grouped-Query Attention (GQA), KV-Cache ve FlashAttention Online Softmax Kodlaması"
track: ai-uretim
order: 4
duration_minutes: 40
difficulty: ileri
xp: 300
prerequisites: [ai-uretim-03]
summary: "KV-Cache bellek darboğazını küçülten Grouped-Query Attention (GQA) baş paylaşımını ve N×N dikkat matrisini HBM belleğe yazmadan tam hesaplayan FlashAttention Online Softmax algoritmasını kodla."
esleme: ai-uretim-03, ai-temel-08, ai-uretim-12
tags: [grouped-query-attention, gqa, kv-cache, flashattention, online-softmax, sram-tiling, gpu]
---

::: anlat
## GQA, KV cache ve online softmax

Uzun dizilerde attention hesabının maliyetini anlamak için KV cache boyutunu ve ara skorların bellekte tutulmasını ayırmak gerekir. GQA, KV head sayısını azaltır; FlashAttention ise hesabı bellek erişimine uygun bloklarla düzenler. Burada head eşlemesini ve bloklar arasında softmax normalizasyonunun korunmasını hesaplayacaksın.

1. **Çıkarım (`Inference`) Duvarı — `KV-Cache Memory Bottleneck`:**
   Oto-regresif üretimde her yeni token üretilirken önceki tüm tokenların `Key` ($K$) ve `Value` ($V$) tensörleri tekrar hesaplanmamak için GPU belleğinde (**KV-Cache**) tutulur. Klasik `MHA`'da 64 Sorgu (`Query`) başı varsa 64 `Key` ve 64 `Value` başı saklanır; 128K bağlamda yalnızca `KV-Cache` tek başına **onlarca Gigabyte `HBM` (VRAM)** yutar!
2. **Eğitim & Ön-Dolum (`Prefill`) Duvarı — $O(N^2)$ `Attention Matrix HBM I/O Bottleneck`:**
   $\text{Attention}(Q, K, V) = \text{softmax}\!\left(\frac{QK^T}{\sqrt{d_k}}\right)V$ denkleminde $N = 128,000$ iken ara dikkat matrisi $S = QK^T$ tam **$128,000 \times 128,000 = 16.3\text{ Milyar}$** eleman içerir! Bu matrisi GPU'nun yavaş ana belleğine (`HBM`) yazıp okumak, matematiksel çarpımdan (`FLOPs`) 10 kat daha uzun sürer!

İşte modern LLM mühendisliği bu iki duvarı iki yöntemle yıkmıştır:
- **KV-Cache Duvarını Yıkan Mimari:** **`Grouped-Query Attention (GQA)`** (Ainslie et al., 2023 — Llama-3, Mistral, Qwen)
- **$O(N^2)$ HBM Duvarını Yıkan Donanım Algoritması:** **Tri Dao'nun `FlashAttention` ve `Online Softmax` Yaklaşımı!**

---

### 1. `MHA` vs `MQA` vs `Grouped-Query Attention (GQA)` ve KV-Cache Hesabı

Üç dikkat ailesini karşılaştıralım ($H_q$: Sorgu başı sayısı, $H_{kv}$: Anahtar/Değer başı sayısı):

```
   1. Multi-Head (MHA)          2. Grouped-Query (GQA)         3. Multi-Query (MQA)
    (Her Q için ayrı K,V)        (Her G adet Q, 1 K,V paylaşır)   (Tüm Q'lar tek K,V paylaşır)
   Q1  Q2  Q3  Q4  Q5  Q6       Q1  Q2  Q3    Q4  Q5  Q6        Q1  Q2  Q3  Q4  Q5  Q6
   │   │   │   │   │   │        └───┼───┘     └───┼───┘         └───┴───┴───┬───┴───┘
   K1  K2  K3  K4  K5  K6          K1,V1         K2,V2                    K1,V1
  (KV-Cache: 100% Boyut)        (KV-Cache: 1/G Boyut + Tam Kalite!)    (KV-Cache: Çok Küçük, Kalite Kaybı)
```

- **Llama-3 70B Örneği:** $H_q = 64$ Sorgu başı vardır ama yalnızca **$H_{kv} = 8$ Key/Value başı** vardır (`G = H_q // H_kv = 8` grup boyutu).
- Her `Key/Value` başı, $8$ farklı `Query` başı tarafından ortak kullanılır! Böylece modelin ifade gücü (`Perplexity`) neredeyse hiç düşmeden **KV-Cache boyutu ve HBM bellek okuma trafiği tam $8\text{ kat}$ ($8\times$) küçülür!**

#### 📐 KV-Cache Bellek Formülü (Mühendislik Mülakatlarının Vazgeçilmez Sorusu):
$$\text{KV-Cache (Byte)} = 2 \ (\text{K ve V}) \times B \times S \times L \times H_{kv} \times d_{\text{head}} \times \text{bytes\_per\_param}$$
*(Burada $B$: Batch size, $S$: Sequence length, $L$: Katman sayısı, $H_{kv}$: KV baş sayısı, $d_{\text{head}}$: Baş boyutu).*

---

### 2. Tri Dao'nun `FlashAttention` Yaklaşımı: `SRAM Tiling` ve `Online Softmax`

Bir **NVIDIA H100 GPU**'nun iki farklı belleği vardır:
- **`HBM` (High Bandwidth Memory — 80 GB):** Çok büyüktür ama görece **yavaştır** ($\approx 3.35\text{ TB/s}$).
- **`SRAM` (On-Chip Shared Memory / L1 Cache — ~20 MB):** Çok küçüktür ama **`HBM`'den yaklaşık 10 kat daha hızlıdır!**

Standart PyTorch Attention, dev $N \times N$ boyutlu $S = QK^T$ ve $P = \text{softmax}(S)$ matrislerini sürekli yavaş `HBM` belleğe yazar ve geri okur.
**`FlashAttention` (Dao et al., 2022 / 2023)** ise $N \times N$ matrisini **`HBM` bellekte ASLA oluşturmaz!** Bunun yerine $Q, K, V$ matrislerini küçük karolara (**Tiles / Blocks**) bölerek çip üstü ultra-hızlı `SRAM` belleğe çeker ve çıktıyı **tek geçişte (`Single-Pass Streaming`)** hesaplar!

#### 🧮 Peki Tüm Satırı Görmeden `Softmax` Nasıl Hesaplanır? (`Online Softmax Trick` — Milakov & Gimelshein)
Normalde kararlı (`Numerically Stable`) Softmax hesaplamak için satırdaki **tüm** skorların maksimumunu ($m = \max_j s_j$) ve üstel toplamını ($\ell = \sum_j e^{s_j - m}$) bilmen gerekir:
$$\text{softmax}(s)_i = \frac{e^{s_i - m}}{\sum_{j=1}^{N} e^{s_j - m}}$$
Eğer $K$ ve $V$ matrislerini parça parça (**Blok 1**, **Blok 2**, ...) okuyorsak, 1. bloğu işlerken 2. blokta daha büyük bir maksimum değer çıkacağını nereden bileceğiz?

İşte **`Online Softmax`** mucizesi, her yeni skor bloğu $S^{(j)}$ geldiğinde yalnızca **3 akümülatörü** (mevcut maksimum $m_{\text{yeni}}$, düzeltilmiş payda $\ell_{\text{yeni}}$ ve düzeltilmiş çıktı vektörü $O_{\text{yeni}}$) **$e^{m_{\text{eski}} - m_{\text{yeni}}}$ yeniden ölçekleme çarpanıyla (`Rescaling Factor`)** günceller:

1. **Yeni Maksimum:**
   $$m_{\text{yeni}} = \max\!\big(m_{\text{eski}}, \, \max(S^{(j)})\big)$$
2. **Eski Toplamı Düzelt ve Yeni Bloğu Ekle:**
   $$\alpha = e^{m_{\text{eski}} - m_{\text{yeni}}}, \qquad \ell_{\text{yeni}} = \alpha \cdot \ell_{\text{eski}} + \sum_{k} e^{S^{(j)}_k - m_{\text{yeni}}}$$
3. **Çıktı Vektörünü ($O$) Anında Güncelle:**
   $$O_{\text{yeni}} = \frac{\alpha \cdot \ell_{\text{eski}} \cdot O_{\text{eski}} + \sum_{k} e^{S^{(j)}_k - m_{\text{yeni}}} V^{(j)}_k}{\ell_{\text{yeni}}}$$

> **Bu Denklemin Güzelliğine Bak:** Hiçbir yaklaşıklama (`Approximation`) yoktur! Bloklar bittiğinde elde ettiğin $O$ vektörü, tüm $N \times N$ matrisini bellekte açıp hesapladığın klasik Attention ile **virgülden sonraki son bite kadar birebir aynıdır (`Exact Attention`)**, ancak bellek karmaşıklığı $O(N^2)$'den **$O(N)$**'e düşmüştür!

Şimdi saf Python ile `FlashAttention`'ın `Online Softmax` blok akışının klasik tam Attention ile birebir aynı sonucu verdiğini canlı olarak kanıtlayalım:

```python
import math

def klasik_attention(skorlar, degerler):
    m = max(skorlar)
    exps = [math.exp(s - m) for s in skorlar]
    payda = sum(exps)
    agirliklar = [e / payda for e in exps]
    d = len(degerler[0])
    return [round(sum(agirliklar[i] * degerler[i][j] for i in range(len(skorlar))), 6) for j in range(d)]

def flash_online_attention(skor_bloklari, deger_bloklari):
    m = float("-inf")
    l = 0.0
    d = len(deger_bloklari[0][0])
    O = [0.0] * d

    for s_blok, v_blok in zip(skor_bloklari, deger_bloklari):
        m_blok = max(s_blok)
        m_yeni = max(m, m_blok)
        alpha = math.exp(m - m_yeni) if m != float("-inf") else 0.0
        exps = [math.exp(s - m_yeni) for s in s_blok]
        l_yeni = alpha * l + sum(exps)

        # Çıktı akümülatörünü (O) yeniden ölçekleyerek güncelle
        for j in range(d):
            blok_katkisi = sum(exps[k] * v_blok[k][j] for k in range(len(s_blok)))
            O[j] = (alpha * l * O[j] + blok_katkisi) / l_yeni

        m, l = m_yeni, l_yeni
    return [round(v, 6) for v in O]

# 4 tokenlık diziyi 2'şerli 2 SRAM bloğu halinde işleyelim:
s_bloklar = [[1.0, 2.0], [5.0, 3.0]]  # 2. blokta çok daha büyük (5.0) bir skor var!
v_bloklar = [[[1.0, 0.0], [0.0, 2.0]], [[3.0, 4.0], [1.0, 1.0]]]

klasik = klasik_attention([1.0, 2.0, 5.0, 3.0], [[1.0, 0.0], [0.0, 2.0], [3.0, 4.0], [1.0, 1.0]])
flash = flash_online_attention(s_bloklar, v_bloklar)
print("Klasik Tam Attention :", klasik)
print("Flash Online Tiling  :", flash)
print("Birebir Ayni Mi?     :", klasik == flash)
```

---

### 3. Gerçek Üretim Kodu: PyTorch `GQA` + `SDPA (FlashAttention-2)` Mimarisi

Gerçek PyTorch 2.x üretim kodunda `GQA` baş eşlemesi ve donanım hızlandırmalı `FlashAttention-2` çekirdeği (`F.scaled_dot_product_attention`) şöyle çalışır:

```python norun
import torch
import torch.nn as nn
import torch.nn.functional as F

def repeat_kv(hidden_states: torch.Tensor, n_rep: int) -> torch.Tensor:
    """
    GQA Baş Çoğaltma: [B, H_kv, S, D] -> [B, H_q, S, D] (burada H_q = H_kv * n_rep)
    Bellekte gereksiz kopya oluşturmadan expand + reshape ile grupları eşler.
    """
    if n_rep == 1:
        return hidden_states
    batch, num_kv_heads, slen, head_dim = hidden_states.shape
    hidden_states = hidden_states[:, :, None, :, :].expand(batch, num_kv_heads, n_rep, slen, head_dim)
    return hidden_states.reshape(batch, num_kv_heads * n_rep, slen, head_dim)

class FlashGQAAttention(nn.Module):
    def __init__(self, dim: int, n_heads: int = 32, n_kv_heads: int = 8):
        super().__init__()
        self.n_heads = n_heads
        self.n_kv_heads = n_kv_heads
        self.n_rep = n_heads // n_kv_heads
        self.head_dim = dim // n_heads

        self.wq = nn.Linear(dim, n_heads * self.head_dim, bias=False)
        self.wk = nn.Linear(dim, n_kv_heads * self.head_dim, bias=False)
        self.wv = nn.Linear(dim, n_kv_heads * self.head_dim, bias=False)
        self.wo = nn.Linear(n_heads * self.head_dim, dim, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, S, _ = x.shape
        q = self.wq(x).view(B, S, self.n_heads, self.head_dim).transpose(1, 2)
        k = self.wk(x).view(B, S, self.n_kv_heads, self.head_dim).transpose(1, 2)
        v = self.wv(x).view(B, S, self.n_kv_heads, self.head_dim).transpose(1, 2)

        k = repeat_kv(k, self.n_rep)
        v = repeat_kv(v, self.n_rep)

        # PyTorch SDPA kaputun altında doğrudan CUDA FlashAttention-2 çekirdeğini çağırır!
        out = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        return self.wo(out.transpose(1, 2).contiguous().view(B, S, -1))
```

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [FlashAttention makalesi](https://arxiv.org/abs/2205.14135). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: tahmin GQA ile KV-Cache Bellek Tasarrufu ve Online Softmax Yeniden Ölçekleme
Bir LLM katmanında $H_q = 32$ Sorgu başı varken `GQA` ile $H_{kv} = 4$ Key/Value başı kullanılıyor. Ayrıca `Online Softmax` hesaplanırken 1. blok sonunda maksimum skor $m_{\text{eski}} = 2.0$ iken 2. blokta yeni maksimum $m_{\text{yeni}} = 4.0$ olarak bulunuyor. Aşağıdaki kod KV-Cache küçülme oranını ve eski toplamın çarpılacağı $\alpha = e^{m_{\text{eski}} - m_{\text{yeni}}}$ katsayısını hesaplar. Çıktı nedir?

```python
import math
kv_kuculme_kati = 32 // 4
alpha = round(math.exp(2.0 - 4.0), 4)
print(f"GQA_Tasarruf={kv_kuculme_kati}x | Rescale_Alpha={alpha}")
```

???

```cikti
GQA_Tasarruf=8x | Rescale_Alpha=0.1353
```
$32$ sorgu başı yerine $4$ Key/Value başı tutulduğu için KV-Cache belleği `32 // 4 = 8` kat (`8x`) küçülür. İkinci blokta maksimum skor $2.0$'dan $4.0$'a çıktığı için birinci bloktaki üstel toplamlar $\alpha = e^{2.0 - 4.0} = e^{-2} \approx 0.1353$ çarpanıyla küçültülerek yeni maksimuma göre dengelenir.
:::

::: gorev 1 · FlashAttention Online Softmax (Tek Geçişli Blok Güncellemesi)
`online_softmax_blok(skor_bloklari, deger_bloklari)` işlevini yaz.

Bu görevde **Tri Dao'nun `FlashAttention`** algoritmasının kalbi olan tek geçişli (**Single-Pass Streaming**) `Online Softmax` ve ağırlıklı değer biriktirme döngüsünü kodlayacaksın.

Parametreler:
- `skor_bloklari`: Her biri bir bloktaki dikkat skorlarını (`list[float]`) temsil eden bloklar listesi (`list[list[float]]`).
- `deger_bloklari`: Her skor bloğuna karşılık gelen $V$ değer vektörlerinin (`list[list[float]]`) blok listesi (`list[list[list[float]]]`).

Algoritma:
1. Başlangıçta yürüyen maksimumu $m = -\infty$, yürüyen üstel toplamı $\ell = 0.0$ ve çıktı vektörünü $O = [0.0, \dots, 0.0]$ olarak başlat.
2. Her `(s_blok, v_blok)` çifti için:
   - Yeni maksimumu $m_{\text{yeni}} = \max(m, \max(\text{s\_blok}))$ olarak bul.
   - Yeniden ölçekleme çarpanı $\alpha = e^{m - m_{\text{yeni}}}$ (ilk adımda $m = -\infty$ iken $\alpha = 0.0$) değerini hesapla.
   - Mevcut bloktaki her $s_k$ için $p_k = e^{s_k - m_{\text{yeni}}}$ değerlerini ve $\ell_{\text{yeni}} = \alpha \cdot \ell + \sum_k p_k$ paydasını hesapla.
   - Çıktı vektörü $O$'yu $O \leftarrow \frac{\alpha \cdot \ell \cdot O + \sum_k p_k V_k}{\ell_{\text{yeni}}}$ formülüyle güncelle ve $m \leftarrow m_{\text{yeni}}, \ell \leftarrow \ell_{\text{yeni}}$ ata.
3. Sonuçta tüm elemanları `round(val, 6)` ile yuvarlanmış şu sözlüğü döndür:
   - `"son_max"`: Son $m$ değeri (`round(m, 6)`),
   - `"son_payda"`: Son $\ell$ değeri (`round(l, 6)`),
   - `"cikti"`: Hesaplanan $O$ çıktı vektörü (`list[float]`).

```starter
def online_softmax_blok(skor_bloklari, deger_bloklari):
    # KUSURLU BAŞLANGIÇ KODU: Online yeniden ölçekleme (exp(m_eski - m_yeni)) yapmadan sıfır döndürüyor!
    d = len(deger_bloklari[0][0])
    return {
        "son_max": 0.0,
        "son_payda": 0.0,
        "cikti": [0.0] * d,
    }

s_orn = [[1.0, 2.0], [4.0, 0.0]]
v_orn = [[[1.0, 2.0], [3.0, 4.0]], [[5.0, 6.0], [7.0, 8.0]]]
print("FlashAttention Blok Çıktısı:", online_softmax_blok(s_orn, v_orn))
```

```test
import copy
import math

def sozlesme(fn):
    try:
        sb = [[0.5, 2.5], [4.5, 1.5], [3.0]]
        vb = [
            [[1.0, -1.0], [2.0, 3.0]],
            [[4.0, 0.5], [-2.0, 1.0]],
            [[0.0, 2.0]],
        ]
        sb_k, vb_k = copy.deepcopy(sb), copy.deepcopy(vb)
        res = fn(sb, vb)
        if sb != sb_k or vb != vb_k or not isinstance(res, dict):
            return False

        # Referans tam softmax hesabı:
        tum_s = [0.5, 2.5, 4.5, 1.5, 3.0]
        tum_v = [[1.0, -1.0], [2.0, 3.0], [4.0, 0.5], [-2.0, 1.0], [0.0, 2.0]]
        m_ref = max(tum_s)
        exps = [math.exp(s - m_ref) for s in tum_s]
        l_ref = sum(exps)
        o_ref = [
            round(sum((exps[i] / l_ref) * tum_v[i][j] for i in range(len(tum_s))), 6)
            for j in range(2)
        ]
        if res.get("son_max") != round(m_ref, 6):
            return False
        if abs(res.get("son_payda", 0.0) - round(l_ref, 6)) > 1e-5:
            return False
        if res.get("cikti") != o_ref:
            return False

        return True
    except Exception:
        return False

ok(online_softmax_blok([[0.12345678]], [[[2.0]]]) == {"son_max": 0.123457, "son_payda": 1.0, "cikti": [2.0]}, "tek blok ve tek satır")
ok(sozlesme(online_softmax_blok), "Online Softmax blok güncellemesi tam (exact) Attention çıktısıyla birebir örtüşmeli")

def m_alpha_unutan(skor_bloklari, deger_bloklari):
    # Eski bloğu exp(m_eski - m_yeni) ile ölçeklemeyi unutan hatalı mutant
    r = online_softmax_blok(skor_bloklari, deger_bloklari)
    r["son_payda"] += 2.0
    return r

def m_cikti_bozuk(skor_bloklari, deger_bloklari):
    r = online_softmax_blok(skor_bloklari, deger_bloklari)
    r["cikti"][0] = 0.0
    return r

for ad, mutant in [("alpha yeniden ölçeklemesini unutan", m_alpha_unutan), ("çıktı akümülatörünü yanlış güncelleyen", m_cikti_bozuk)]:
    ok(not sozlesme(mutant), "hatalı çözüm/mutant yakalanmalı: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef online_softmax_blok(skor_bloklari, deger_bloklari):\n    m = float('-inf')\n    l = 0.0\n    d = len(deger_bloklari[0][0])\n    O = [0.0] * d\n    for s_blok, v_blok in zip(skor_bloklari, deger_bloklari):\n        m_blok = max(s_blok)\n        m_yeni = max(m, m_blok)\n        alpha = math.exp(m - m_yeni) if m != float('-inf') else 0.0\n        exps = [math.exp(s - m_yeni) for s in s_blok]\n        l_yeni = alpha * l + sum(exps)\n        for j in range(d):\n            blok_toplam = sum((exps[k] * v_blok[k][j] for k in range(len(s_blok))))\n            O[j] = (alpha * l * O[j] + blok_toplam) / l_yeni\n        m = m_yeni\n        l = l_yeni\n    return {'son_max': round(m, 6), 'son_payda': round(l, 6), 'cikti': [round(v, 6) for v in O]}", 'referans', 'exec'), _REF)
_t, _g = _ff(online_softmax_blok, _REF['online_softmax_blok'], ([[1.0, 2.0], [4.0, 0.0]], [[[1.0, 2.0], [3.0, 4.0]], [[5.0, 6.0], [7.0, 8.0]]]), tohum=3083, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (online_softmax_blok): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def online_softmax_blok(skor_bloklari, deger_bloklari):
    m = float("-inf")
    l = 0.0
    d = len(deger_bloklari[0][0])
    O = [0.0] * d

    for s_blok, v_blok in zip(skor_bloklari, deger_bloklari):
        m_blok = max(s_blok)
        m_yeni = max(m, m_blok)
        alpha = math.exp(m - m_yeni) if m != float("-inf") else 0.0
        exps = [math.exp(s - m_yeni) for s in s_blok]
        l_yeni = alpha * l + sum(exps)

        for j in range(d):
            blok_toplam = sum(exps[k] * v_blok[k][j] for k in range(len(s_blok)))
            O[j] = (alpha * l * O[j] + blok_toplam) / l_yeni

        m = m_yeni
        l = l_yeni

    return {
        "son_max": round(m, 6),
        "son_payda": round(l, 6),
        "cikti": [round(v, 6) for v in O],
    }
```

```hint
Her blokta `m_yeni = max(m, max(s_blok))` ve `alpha = math.exp(m - m_yeni) if m != float("-inf") else 0.0` hesapla. `l_yeni = alpha * l + sum(exps)` bulduktan sonra `O[j] = (alpha * l * O[j] + blok_toplam) / l_yeni` ile çıktı vektörünü güncelle.
```
:::

::: gorev 2 · Grouped-Query Attention (GQA) Baş Eşleme ve KV-Cache Güncellemesi
`gqa_dikkat(sorgu_baslari, kv_baslari_k, kv_baslari_v)` işlevini yaz.

Bir LLM çıkarım (`Inference / Decode`) adımında üretilen son token için:
- `sorgu_baslari`: $H_q$ adet sorgu başı vektörü (`list[list[float]]`, boyut: $H_q \times d_{\text{head}}$).
- `kv_baslari_k`: KV-Cache'te tutulan $H_{kv}$ adet Anahtar (`Key`) başı geçmişi (`list[list[list[float]]]`, boyut: $H_{kv} \times S \times d_{\text{head}}$; burada $S$ geçmiş token sayısıdır).
- `kv_baslari_v`: KV-Cache'te tutulan $H_{kv}$ adet Değer (`Value`) başı geçmişi (boyut: $H_{kv} \times S \times d_{\text{head}}$).

Kurallar:
1. Grup boyutu $G = H_q // H_{kv}$ olarak tanımlıdır. İndisi $h \in \{0, 1, \dots, H_q - 1\}$ olan her Sorgu (`Query`) başı, indisi $\text{kv\_idx} = h // G$ olan `Key` ve `Value` başını kullanır!
2. Her sorgu başı $q_h$ için eşleştiği $K_{\text{kv\_idx}}$ geçmişindeki her token ($t \in \{0, \dots, S-1\}$) ile ölçeklenmiş iç çarpım skorunu hesapla:
   $$s_{h, t} = \frac{q_h \cdot K_{\text{kv\_idx}, t}}{\sqrt{d_{\text{head}}}}$$
3. Bu skorlara kararlı `Softmax` uygula ve $V_{\text{kv\_idx}}$ vektörlerinin ağırlıklı toplamını alarak $h$. başın çıktı vektörünü ($d_{\text{head}}$ uzunluğunda) üret.
4. Sonuç olarak:
   - `"grup_boyutu"`: $G = H_q // H_{kv}$ tam sayısı,
   - `"bas_eslesmeleri"`: Her sorgu başının hangi KV baş indisine bağlandığını gösteren liste `[h // G for h in range(H_q)]`,
   - `"bas_ciktilari"`: $H_q \times d_{\text{head}}$ boyutunda, elemanları `round(val, 6)` ile yuvarlanmış çıktı matrisi.

```starter
def gqa_dikkat(sorgu_baslari, kv_baslari_k, kv_baslari_v):
    # KUSURLU BAŞLANGIÇ KODU: GQA baş gruplamasını ve ölçekli dikkat hesabını yapmıyor!
    h_q = len(sorgu_baslari)
    d_head = len(sorgu_baslari[0])
    return {
        "grup_boyutu": 1,
        "bas_eslesmeleri": [0] * h_q,
        "bas_ciktilari": [[0.0] * d_head for _ in range(h_q)],
    }

q_orn = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0], [-1.0, 0.0]]  # H_q = 4
k_orn = [[[[1.0, 0.0], [0.0, 1.0]]], [[[0.5, 0.5], [1.0, -1.0]]]]  # H_kv = 2
v_orn = [[[[2.0, 4.0], [6.0, 8.0]]], [[[1.0, 3.0], [5.0, 7.0]]]]
print("GQA:", gqa_dikkat(q_orn, [k[0] for k in k_orn], [v[0] for v in v_orn]))
```

```test
import copy
import math

def sozlesme(fn):
    try:
        # H_q = 4, H_kv = 2 -> G = 2 (Baş 0,1 -> KV 0; Baş 2,3 -> KV 1)
        # d_head = 4 -> sqrt(d_head) = 2.0
        q = [
            [2.0, 0.0, 0.0, 0.0],
            [0.0, 2.0, 0.0, 0.0],
            [0.0, 0.0, 2.0, 0.0],
            [0.0, 0.0, 0.0, 2.0],
        ]
        # S = 2 tokenlık KV-Cache
        k = [
            [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]],  # KV başı 0
            [[0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]],  # KV başı 1
        ]
        v = [
            [[10.0, 0.0, 0.0, 0.0], [0.0, 20.0, 0.0, 0.0]],  # KV başı 0
            [[0.0, 0.0, 30.0, 0.0], [0.0, 0.0, 0.0, 40.0]],  # KV başı 1
        ]
        qk = copy.deepcopy(q)
        res = fn(q, k, v)
        if q != qk or not isinstance(res, dict):
            return False
        if res.get("grup_boyutu") != 2:
            return False
        if res.get("bas_eslesmeleri") != [0, 0, 1, 1]:
            return False

        # Baş 0 için: KV 0 kullanılır.
        # q0 . k0_0 / 2.0 = 2.0 / 2.0 = 1.0; q0 . k0_1 / 2.0 = 0.0
        # softmax([1.0, 0.0]) -> w0 = e^1 / (e^1 + 1), w1 = 1 / (e^1 + 1)
        w_b = math.exp(1.0) / (math.exp(1.0) + 1.0)
        w_k = 1.0 / (math.exp(1.0) + 1.0)
        beklenen_cikti = [
            [round(w_b * 10.0, 6), round(w_k * 20.0, 6), 0.0, 0.0],
            [round(w_k * 10.0, 6), round(w_b * 20.0, 6), 0.0, 0.0],
            [0.0, 0.0, round(w_b * 30.0, 6), round(w_k * 40.0, 6)],
            [0.0, 0.0, round(w_k * 30.0, 6), round(w_b * 40.0, 6)],
        ]
        return res.get("bas_ciktilari") == beklenen_cikti
    except Exception:
        return False

ok(gqa_dikkat([[1000.0]], [[[1.0]]], [[[3.0]]]) == {"grup_boyutu": 1, "bas_eslesmeleri": [0], "bas_ciktilari": [[3.0]]}, "tek sorgu başı ve büyük skor")
ok(sozlesme(gqa_dikkat), "GQA baş eşlemesi (h // G) ve ölçekli dikkat çıktıları doğru hesaplanmalı")

def m_olceksiz(sorgu_baslari, kv_baslari_k, kv_baslari_v):
    # sqrt(d_head) ile bölmeyi unutan hatalı mutant
    r = gqa_dikkat(sorgu_baslari, kv_baslari_k, kv_baslari_v)
    r["bas_ciktilari"][0][0] += 0.5
    return r

def m_yanlis_grup(sorgu_baslari, kv_baslari_k, kv_baslari_v):
    r = gqa_dikkat(sorgu_baslari, kv_baslari_k, kv_baslari_v)
    r["bas_eslesmeleri"] = [0] * len(sorgu_baslari)
    return r

for ad, mutant in [("sqrt(d_head) ölçeklemesini unutan", m_olceksiz), ("KV grup indeksini yanlış eşleyen", m_yanlis_grup)]:
    ok(not sozlesme(mutant), "hatalı çözüm/mutant yakalanmalı: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef gqa_dikkat(sorgu_baslari, kv_baslari_k, kv_baslari_v):\n    h_q = len(sorgu_baslari)\n    h_kv = len(kv_baslari_k)\n    grup_boyutu = h_q // h_kv\n    d_head = len(sorgu_baslari[0])\n    olcek = math.sqrt(d_head)\n    eslesmeler = []\n    ciktilar = []\n    for h in range(h_q):\n        kv_idx = h // grup_boyutu\n        eslesmeler.append(kv_idx)\n        q_vec = sorgu_baslari[h]\n        k_mat = kv_baslari_k[kv_idx]\n        v_mat = kv_baslari_v[kv_idx]\n        skorlar = [sum((q_vec[d] * k_tok[d] for d in range(d_head))) / olcek for k_tok in k_mat]\n        m = max(skorlar)\n        exps = [math.exp(s - m) for s in skorlar]\n        payda = sum(exps)\n        agirliklar = [e / payda for e in exps]\n        bas_out = [round(sum((agirliklar[t] * v_mat[t][d] for t in range(len(v_mat)))), 6) for d in range(d_head)]\n        ciktilar.append(bas_out)\n    return {'grup_boyutu': grup_boyutu, 'bas_eslesmeleri': eslesmeler, 'bas_ciktilari': ciktilar}", 'referans', 'exec'), _REF)
_t, _g = _ff(gqa_dikkat, _REF['gqa_dikkat'], ([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0], [-1.0, 0.0]], [[[1.0, 0.0], [0.0, 1.0]], [[0.5, 0.5], [1.0, -1.0]]], [[[2.0, 4.0], [6.0, 8.0]], [[1.0, 3.0], [5.0, 7.0]]]), tohum=2094, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (gqa_dikkat): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def gqa_dikkat(sorgu_baslari, kv_baslari_k, kv_baslari_v):
    h_q = len(sorgu_baslari)
    h_kv = len(kv_baslari_k)
    grup_boyutu = h_q // h_kv
    d_head = len(sorgu_baslari[0])
    olcek = math.sqrt(d_head)

    eslesmeler = []
    ciktilar = []

    for h in range(h_q):
        kv_idx = h // grup_boyutu
        eslesmeler.append(kv_idx)
        q_vec = sorgu_baslari[h]
        k_mat = kv_baslari_k[kv_idx]
        v_mat = kv_baslari_v[kv_idx]

        skorlar = [
            sum(q_vec[d] * k_tok[d] for d in range(d_head)) / olcek
            for k_tok in k_mat
        ]
        m = max(skorlar)
        exps = [math.exp(s - m) for s in skorlar]
        payda = sum(exps)
        agirliklar = [e / payda for e in exps]

        bas_out = [
            round(sum(agirliklar[t] * v_mat[t][d] for t in range(len(v_mat))), 6)
            for d in range(d_head)
        ]
        ciktilar.append(bas_out)

    return {
        "grup_boyutu": grup_boyutu,
        "bas_eslesmeleri": eslesmeler,
        "bas_ciktilari": ciktilar,
    }
```

```hint
`grup_boyutu = len(sorgu_baslari) // len(kv_baslari_k)` hesapladıktan sonra her `h` sorgu başı için `kv_idx = h // grup_boyutu` ile ilgili `K` ve `V` matrislerini seç. İç çarpımları `math.sqrt(d_head)` değerine bölüp Softmax ağırlıklarıyla `V` satırlarını topla.
```
:::

::: anlat Gerçek deney: Gerçek SmolLM2 dikkat katmanında GQA ve online softmax
SmolLM2-135M gerçek bir **GQA** modelidir: 9 sorgu başı 3 KV başını paylaşır (grup boyu 3), `head_dim` 64. Final bu modelin 0. katmanını kullanır (indirme yok):

- Gerçek bir cümle modelden geçirilir ve modelin **kendi** dikkat çıktısı `o_proj`'a girmeden yakalanır (ileri kanca).
- Aynı katmanın gerçek `q_proj`, `k_proj`, `v_proj` ağırlıklarıyla RoPE uygulanmış sorgu, anahtar ve değerler hesaplanır ve iki konumda senin `gqa_dikkat` işlevine verilir. Senin 9 başın çıktısı modelin çıktısıyla karşılaştırılır.
- Head 0'ın gerçek skorları 4'lük bloklara bölünüp senin `online_softmax_blok` işlevine verilir; sonuç yine modelin çıktısıyla karşılaştırılır. FlashAttention'ın tüm fikri budur: N×N matris hiç oluşmadan aynı sonuç.
- Son olarak modelin gerçek yapılandırmasından KV-cache boyutu hesaplanır: aynı model MHA olsaydı token başına ne kadar, GQA ile ne kadar bellek.

**Güvenlik yönü — bağlam doldurmayla sistem isteminin seyrelmesi:** SmolLM2-Instruct'a bir banka asistanı sistem istemi verilir. Kullanıcı girdisi alakasız bir metinle 41 tokendan ~700 tokena kadar uzatılır. Her uzunlukta son tokenın sistem istemine verdiği dikkat payı ölçülür (ilk token, yani attention sink hariç). Pay girdi uzadıkça azalır ama sıfıra inmez, bir düzeyde doyar. Uzun enjeksiyon metinlerinin talimatları neden zayıflattığını ve sistem isteminin neden yalnız dikkate emanet edilemeyeceğini gösterir.

Kabul: iki işlevin farksal taramayı geçmesi; GQA ve online softmax çıktısının gerçek dikkat çıktısından göreli `1e-5` altında farklı olması; baş eşlemesinin `h // 3` olması. Ayrıca sistem istemine verilen dikkat payı girdi uzadıkça monoton azalmalı ve en uzun girdide en az %25 düşmelidir.

**Kanıt dosyasını oku:** `gqa_goreli_fark`, `online_softmax_goreli_fark`, `kv_bayt_token_mha`, `kv_bayt_token_gqa`, `kv_8k_mb_gqa`. Soru 1: 8K bağlamda 180 MB KV-cache 135M parametrelik (≈270 MB fp16) modelle kıyaslanınca ne söylüyor? Soru 2: Online softmax'ın farkı neden tam softmax'ınkiyle aynı mertebede? Soru 3: GQA kaliteyi neden biraz düşürür?
:::

::: gorev Gerçek deney · Gerçek SmolLM2 0. katmanında GQA ve online softmax karşılaştırması
Önceki görevlerdeki `online_softmax_blok`, `gqa_dikkat` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 180
```
```starter
import ai_lab
def online_softmax_blok(skor_bloklari, deger_bloklari):
    d = len(deger_bloklari[0][0])
    return {'son_max': 0.0, 'son_payda': 0.0, 'cikti': [0.0] * d}

def gqa_dikkat(sorgu_baslari, kv_baslari_k, kv_baslari_v):
    h_q = len(sorgu_baslari)
    d_head = len(sorgu_baslari[0])
    return {'grup_boyutu': 1, 'bas_eslesmeleri': [0] * h_q, 'bas_ciktilari': [[0.0] * d_head for _ in range(h_q)]}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_04 as D
    D.goster(online_softmax_blok, gqa_dikkat)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('register_forward_hook', 'dil_modeli', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
online_softmax_blok = need("online_softmax_blok")
gqa_dikkat = need("gqa_dikkat")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef online_softmax_blok(skor_bloklari, deger_bloklari):\n    m = float('-inf')\n    l = 0.0\n    d = len(deger_bloklari[0][0])\n    O = [0.0] * d\n    for s_blok, v_blok in zip(skor_bloklari, deger_bloklari):\n        m_blok = max(s_blok)\n        m_yeni = max(m, m_blok)\n        alpha = math.exp(m - m_yeni) if m != float('-inf') else 0.0\n        exps = [math.exp(s - m_yeni) for s in s_blok]\n        l_yeni = alpha * l + sum(exps)\n        for j in range(d):\n            blok_toplam = sum((exps[k] * v_blok[k][j] for k in range(len(s_blok))))\n            O[j] = (alpha * l * O[j] + blok_toplam) / l_yeni\n        m = m_yeni\n        l = l_yeni\n    return {'son_max': round(m, 6), 'son_payda': round(l, 6), 'cikti': [round(v, 6) for v in O]}\n\nimport math\n\ndef gqa_dikkat(sorgu_baslari, kv_baslari_k, kv_baslari_v):\n    h_q = len(sorgu_baslari)\n    h_kv = len(kv_baslari_k)\n    grup_boyutu = h_q // h_kv\n    d_head = len(sorgu_baslari[0])\n    olcek = math.sqrt(d_head)\n    eslesmeler = []\n    ciktilar = []\n    for h in range(h_q):\n        kv_idx = h // grup_boyutu\n        eslesmeler.append(kv_idx)\n        q_vec = sorgu_baslari[h]\n        k_mat = kv_baslari_k[kv_idx]\n        v_mat = kv_baslari_v[kv_idx]\n        skorlar = [sum((q_vec[d] * k_tok[d] for d in range(d_head))) / olcek for k_tok in k_mat]\n        m = max(skorlar)\n        exps = [math.exp(s - m) for s in skorlar]\n        payda = sum(exps)\n        agirliklar = [e / payda for e in exps]\n        bas_out = [round(sum((agirliklar[t] * v_mat[t][d] for t in range(len(v_mat)))), 6) for d in range(d_head)]\n        ciktilar.append(bas_out)\n    return {'grup_boyutu': grup_boyutu, 'bas_eslesmeleri': eslesmeler, 'bas_ciktilari': ciktilar}", 'referans', 'exec'), _REF)
_t, _g = _ff(online_softmax_blok, _REF['online_softmax_blok'], ([[1.0, 2.0], [4.0, 0.0]], [[[1.0, 2.0], [3.0, 4.0]], [[5.0, 6.0], [7.0, 8.0]]]), tohum=3083, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (online_softmax_blok): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(gqa_dikkat, _REF['gqa_dikkat'], ([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0], [-1.0, 0.0]], [[[1.0, 0.0], [0.0, 1.0]], [[0.5, 0.5], [1.0, -1.0]]], [[[2.0, 4.0], [6.0, 8.0]], [[1.0, 3.0], [5.0, 7.0]]]), tohum=2094, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (gqa_dikkat): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
kontrol(online_softmax_blok([[0.12345678]], [[[2.0]]]) == _REF['online_softmax_blok']([[0.12345678]], [[[2.0]]]), "tek blok 6 basamak yuvarlama korunmalı")
kontrol(gqa_dikkat([[1000.0]], [[[1.0]]], [[[3.0]]]) == _REF['gqa_dikkat']([[1000.0]], [[[1.0]]], [[[3.0]]]), "büyük logit sayısal kararlılığı korunmalı")
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_04 as D
try: r = D.deney(online_softmax_blok, gqa_dikkat)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['gqa_ayni'], 'GQA çıktısı modelin kendi dikkat çıktısıyla aynı (göreli fark < 1e-5)')
kontrol(r['online_ayni'], 'blok blok online softmax modelin dikkat çıktısıyla aynı (göreli fark < 1e-5)')
kontrol(r['eslesme_dogru'], '9 sorgu başı 3 KV başına h // 3 ile eşleniyor')
kontrol(r['sistem_dikkati_azaliyor'], 'kullanıcı girdisi uzadıkça son tokenın sistem istemine dikkati monoton azaldı')
ai_lab.kanit_yaz("ai-uretim-04-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-04", "deney": r})
```
```solution
import ai_lab
import math

def online_softmax_blok(skor_bloklari, deger_bloklari):
    m = float('-inf')
    l = 0.0
    d = len(deger_bloklari[0][0])
    O = [0.0] * d
    for s_blok, v_blok in zip(skor_bloklari, deger_bloklari):
        m_blok = max(s_blok)
        m_yeni = max(m, m_blok)
        alpha = math.exp(m - m_yeni) if m != float('-inf') else 0.0
        exps = [math.exp(s - m_yeni) for s in s_blok]
        l_yeni = alpha * l + sum(exps)
        for j in range(d):
            blok_toplam = sum((exps[k] * v_blok[k][j] for k in range(len(s_blok))))
            O[j] = (alpha * l * O[j] + blok_toplam) / l_yeni
        m = m_yeni
        l = l_yeni
    return {'son_max': round(m, 6), 'son_payda': round(l, 6), 'cikti': [round(v, 6) for v in O]}

import math

def gqa_dikkat(sorgu_baslari, kv_baslari_k, kv_baslari_v):
    h_q = len(sorgu_baslari)
    h_kv = len(kv_baslari_k)
    grup_boyutu = h_q // h_kv
    d_head = len(sorgu_baslari[0])
    olcek = math.sqrt(d_head)
    eslesmeler = []
    ciktilar = []
    for h in range(h_q):
        kv_idx = h // grup_boyutu
        eslesmeler.append(kv_idx)
        q_vec = sorgu_baslari[h]
        k_mat = kv_baslari_k[kv_idx]
        v_mat = kv_baslari_v[kv_idx]
        skorlar = [sum((q_vec[d] * k_tok[d] for d in range(d_head))) / olcek for k_tok in k_mat]
        m = max(skorlar)
        exps = [math.exp(s - m) for s in skorlar]
        payda = sum(exps)
        agirliklar = [e / payda for e in exps]
        bas_out = [round(sum((agirliklar[t] * v_mat[t][d] for t in range(len(v_mat)))), 6) for d in range(d_head)]
        ciktilar.append(bas_out)
    return {'grup_boyutu': grup_boyutu, 'bas_eslesmeleri': eslesmeler, 'bas_ciktilari': ciktilar}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_04 as D
    D.goster(online_softmax_blok, gqa_dikkat)
```
```hint
Görev 1 ve görev 2 çözümlerini olduğu gibi buraya koy. Deney sorgu, anahtar ve değerleri gerçek modelden hesaplar.
```
:::

::: anlat Sınır
Görevler FlashAttention'ın online softmax blok güncellemesini ve GQA baş eşlemesi ile KV-cache güncellemesini saf Python ile hesaplatır; final adım sonuçları gerçek SmolLM2 dikkat katmanının çıktısıyla karşılaştırır; SRAM tiling ve CUDA çekirdeği hızı ölçülmez. Online softmax matematiksel olarak tam dikkatle aynıdır, ama kayan noktada yeniden ölçekleme sırası küçük farklar üretir; karşılaştırma toleransla yapılmalıdır. GQA KV-cache belleğini grup oranı kadar düşürür, kaliteyi bir miktar azaltabilir; MQA'ya inmek daha fazla kayıp verir. Uzun bağlamda asıl darboğaz KV-cache belleğidir; FlashAttention bunu küçültmez, yalnız N×N ara matrisi saklamaz.

Kaynaklar: [Ainslie vd. 2023 - GQA: Training Generalized Multi-Query Transformer Models from Multi-Head Checkpoints](https://arxiv.org/abs/2305.13245), [Milakov ve Gimelshein 2018 - Online normalizer calculation for softmax](https://arxiv.org/abs/1805.02867), [Dao vd. 2022 - FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness](https://arxiv.org/abs/2205.14135).
:::

::: dusun
Bir sistem mimarı olarak şu ilginç çelişkiyi düşün:
**`FlashAttention`** ileri geçişte (**Forward Pass**) $N \times N$ boyutlu $P = \text{softmax}(QK^T / \sqrt{d})$ dikkat matrisini `HBM` belleğe **yazmadığı** için devasa bir bellek ve hız tasarrufu sağlar.
Ancak 1. derste öğrendiğimiz üzere backpropagation (**Backward Pass**) sırasında $\frac{\partial \mathcal{L}}{\partial Q}, \frac{\partial \mathcal{L}}{\partial K}, \frac{\partial \mathcal{L}}{\partial V}$ gradyanlarını hesaplamak için $P$ matrisine ihtiyaç vardır!

Eğer `FlashAttention` ileri geçişte $N \times N$ boyutundaki $P$ matrisini kaydetmediyse, **Backward Pass** sırasında gradyanları nasıl tam (`exact`) olarak hesaplar? **`FlashAttention`'ın ileri geçişte yalnızca $O(N)$ boyutundaki $m$ ve $\ell$ (`LogSumExp`) istatistiklerini saklayıp, geri geçişte blokları `SRAM` içinde anında yeniden hesaplaması (`Kernel Recomputation`)** neden ekstra `FLOPs` harcamasına rağmen standart Attention'dan **daha hızlı** çalışır? (`Memory-Bound` vs `Compute-Bound` kavramlarıyla açıkla).
:::

::: ozet
- **Grouped-Query Attention (`GQA`)**, $H_q$ adet sorgu başını $G = H_q / H_{kv}$ gruplara ayırarak her grubun tek bir `Key` ve `Value` başını paylaşmasını sağlar; böylece model kalitesini korurken **KV-Cache** bellek tüketimini ve `HBM` bant genişliği darboğazını $G$ kat ($4\times - 8\times$) azaltır.
- Klasik Attention, $N \times N$ boyutlu ara dikkat matrisini yavaş GPU ana belleğine (`HBM`) yazıp okuduğu için **Bellek Bant Genişliği Darboğazına (`Memory-Bandwidth Bound`)** takılır.
- **Tri Dao'nun `FlashAttention`** algoritması, $Q, K, V$ tensörlerini çip üstü hızlı `SRAM` bellekte karolara (**SRAM Tiling**) böler ve **`Online Softmax`** ($\alpha = e^{m_{\text{eski}} - m_{\text{yeni}}}$ yeniden ölçeklemesi) sayesinde $N \times N$ matrisini bellekte hiç oluşturmadan $O(N)$ bellekle tam (`exact`) Attention çıktısını hesaplar.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Bellek duvarı ve `GQA` (30 sn).** "Uzun bağlam çıkarımında GPU hesaplamadan çok `KV-Cache` okumayı bekler; `GQA`, $H_q$ sorgu başını $H_{kv}$ anahtar/değer başı etrafında gruplayarak önbellek boyutunu ve `HBM` trafiğini $H_q/H_{kv}$ kat küçültür."
2. **`Online Softmax` ve karolama (35 sn).** "Standart dikkat $N \times N$ matrisi `HBM`'e yazıp okur; `FlashAttention` blokları hızlı `SRAM` içinde gezerken yeni maksimum çıktıkça eski toplamı $e^{m_{\text{eski}} - m_{\text{yeni}}}$ ile yeniden ölçekler ve yaklaşık değil, bit düzeyinde tam dikkat çıktısı üretir."
3. **Geri yayılımda yeniden hesaplama (30 sn).** "İleri geçişte $N \times N$ matrisini saklamak yerine yalnız $O(N)$ `LogSumExp` istatistiğini tutmak, geri geçişte fazladan çarpma yapsa da yavaş `HBM` trafiğini kestiği için toplam süreyi kısaltır."
4. **Soru (25 sn).** "$H_{kv}=1$ (`MQA`) bellek kazancını en üste çıkarırken modern büyük modeller neden çoğunlukla $H_{kv}=4$ veya $8$ olan ara `GQA` noktasını seçiyor?"
:::
