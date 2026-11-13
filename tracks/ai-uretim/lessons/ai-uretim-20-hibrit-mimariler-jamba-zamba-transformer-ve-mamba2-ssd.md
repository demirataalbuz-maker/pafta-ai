---
id: ai-uretim-20
title: "Hibrit Mimariler (Jamba / Zamba): Transformer ve Mamba-2 (Structured State Space Duality - SSD)"
track: ai-uretim
order: 20
duration_minutes: 40
difficulty: ileri
xp: 310
prerequisites: [ai-uretim-19]
summary: "Salt SSM (Mamba) neden In-Context Copying / Needle-in-a-Haystack görevlerinde zorlanırken salt Transformer uzun bağlamda yavaşlar? Mamba-2 (Structured State Space Duality - SSD) ve AI21 Jamba / Zamba / Nemotron-H hibrit mimari tasarımı."
esleme: ai-uretim-19, ai-uretim-17, ai-temel-08
tags: [mamba-2, state-space-duality, ssd, jamba, zamba, hybrid-architecture, kv-cache]
---

::: anlat 1. Büyük Mimari İkilem: Salt Transformer vs Salt Mamba (SSM) Neden Tek Başına Yetmiyor?
## Transformer ve SSM katmanlarını birleştirme

Hibrit mimariler attention katmanlarıyla SSM katmanlarını aynı ağda kullanabilir. Bu derste Mamba-2 yaklaşımındaki küçük durum güncellemesini ve katman planına göre bellek hesabını inceleyeceksin. Katman sayacı, eğitilmiş model kalitesini veya gerçek throughput değerini göstermez.

Bir konferansta ya da `Frontier AI` mimari tasarım toplantısında şu temel mühendislik ikilemini masaya koy:
> *"Elbette `Mamba (Selective State Space Model - SSM)` harika bir icat: `KV-Cache` belleği bağlam uzunluğu $T$'den tamamen bağımsız ($O(1)$ sabit bellek!) ve üretim hızı doğrusal ($O(T)$). Peki madem `Mamba` bu kadar hızlı, neden dünyanın bütün laboratuvarları `Transformer` mimarisini çöpe atıp `%100` saf `Mamba` modellerine geçmedi?"*

Cevap **Bilgi Kuramı (`Information Theory`) ve Kayıplı Sıkıştırma (`Lossy Compression`)** yasalarında gizlidir!

### 🔍 Fotokopi Makinesi (`Transformer`) vs Özet Defteri Tutan Öğrenci (`SSM / Mamba`)
1. **`Transformer` (`Full Causal Self-Attention`):** Masanın üzerinde 1.000 sayfalık kitabın tamamını açık tutan bir fotokopi makinesidir. 500. sayfanın 14. satırındaki 12 haneli rastgele bir seri numarasını (**`Needle-in-a-Haystack` / `In-Context Copying` / `Associative Recall`**) istediğinde, `Softmax(QK^T)` doğrudan o satıra odaklanır ve **sıfır kayıpla (`Lossless`)** kopyalar!
   - **Bedeli:** Kitap 1 milyon sayfaya çıktığında masa (`GPU VRAM KV-Cache`) çöker!
2. **`Mamba / SSM` (`Recurrent State Space Model`):** Kitabı okurken elinde sadece **1 sayfalık sabit bir not defteri (`Fixed-Size Hidden State` $h_t \in \mathbb{R}^{N \times d}$)** tutan bir öğrencidir! Kitap 10 sayfa da olsa, 10 milyon sayfa da olsa öğrencinin elindeki not defteri hep 1 sayfadır ($O(1)$ bellek!).
   - **Bedeli:** Öğrenci 1 milyon sayfalık kitaptaki ana fikri harika özetler; **ama** kitabın 42.318. sayfasındaki rastgele bir telefon numarasını harfi harfine kopyalamasını (`Exact In-Context Copying`) istersen, 1 sayfalık sabit durum vektörü ($h_t$) sonsuz miktarda rastgele bilgiyi kayıpsız sıkıştıramaz!

```text
  SALT TRANSFORMER (Full Attention)           SALT MAMBA / SSM (Recurrent State)
  ┌───────────────────────────────┐           ┌───────────────────────────────┐
  │ • Kesin Kopyalama (Recall): ★★★★★│        │ • Kesin Kopyalama (Recall): ★★☆☆☆│
  │ • 1M Bağlam Hızı (FLOPs)  : ★☆☆☆☆│        │ • 1M Bağlam Hızı (FLOPs)  : ★★★★★│
  │ • KV-Cache Bellek (VRAM)  : O(T) │        │ • Durum Belleği (VRAM)    : O(1) │
  └───────────────┬───────────────┘           └───────────────┬───────────────┘
                  │                                           │
                  └─────────────────────┬─────────────────────┘
                                        ▼
               🚀 HİBRİT MİMARİ (JAMBA / ZAMBA / NEMOTRON-H)
               • Her 8 katmanın 7'si: Hızlı Mamba-2 (SSD) Katmanı (O(1) Durum)
               • Her 8 katmanın 1'i : Tam GQA Attention Katmanı (Kusursuz Recall!)
               • + Her 2 katmanda 1 : Sparse MoE FFN (Yüksek Bilgi Kapasitesi!)
```

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [Mamba-2 / SSD makalesi](https://arxiv.org/abs/2405.21060). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: anlat 2. Mamba-1'den Mamba-2'ye: Structured State Space Duality (SSD) Yaklaşımı
Tri Dao ve Albert Gu (2024 — *"Transformers are SSMs: Generalized Models and Efficient Algorithms Through Structured State Space Duality"*) **`Mamba-2`** makalesiyle `Attention` ve `SSM` dünyalarının aslında **aynı madalyonun iki yüzü (`Duality`)** olduğunu matematiksel olarak kanıtladılar!

### 📐 `SSM` Denklemi Nasıl `1-Semiseparable` Bir Dikkat Matrisine Dönüşür?
Seçici bir durum uzayı modeli (`Selective SSM`), her $t$ adımında gizli durumu $h_t$ şu doğrusal özyinelemeyle (`Linear Recurrence`) günceller ($a_t \in (0, 1)$: seçici unutma/çürüme skaları, $B_t, C_t$: giriş ve çıkış projeksiyonları):

$$h_t = a_t \cdot h_{t-1} + B_t x_t, \qquad y_t = C_t^\top h_t$$

Şimdi bu denklemi $t = 0, 1, 2$ için adım adım açalım (`Unroll`):
- $t = 0$: $h_0 = B_0 x_0 \implies y_0 = (C_0^\top B_0) x_0$
- $t = 1$: $h_1 = a_1 B_0 x_0 + B_1 x_1 \implies y_1 = a_1 (C_1^\top B_0) x_0 + (C_1^\top B_1) x_1$
- $t = 2$: $h_2 = (a_2 a_1) B_0 x_0 + a_2 B_1 x_1 + B_2 x_2 \implies y_2 = (a_2 a_1)(C_2^\top B_0) x_0 + a_2(C_2^\top B_1) x_1 + (C_2^\top B_2) x_2$

Dikkatle bak! Herhangi bir $t \ge s$ için $x_s$ girdisinin $y_t$ çıktısına katkısı, aradaki unutma çarpanlarının çarpımı olan $a_{t:s}^\times = \prod_{k=s+1}^{t} a_k$ ile $(C_t^\top B_s)$ iç çarpımının çarpımıdır! Bunu matris formunda yazdığımızda:

$$y = M \cdot x, \qquad M_{t, s} = \begin{cases} \left(\prod_{k=s+1}^{t} a_k\right) C_t^\top B_s, & \text{eğer } t \ge s \\ 0, & \text{eğer } t < s \end{cases}$$

İşte bu $M = L \odot (C B^\top)$ matrisine **`1-Semiseparable Matrix`** denir ve **`Structured Masked Attention` ($Q \leftrightarrow C, K \leftrightarrow B, V \leftrightarrow X$)** ile birebir aynıdır!

### ⚡ Neden Buna `Structured State Space Duality (SSD)` Denir?
Çünkü elimizde **aynı matematiksel sonucu veren iki farklı hesaplama modu** vardır:
1. **`Recurrent (SSM) Modu` ($O(T)$ — Üretim / `Autoregressive Decoding` sırasında):** Token üretirken tek tek $h_t = a_t h_{t-1} + B_t x_t$ adımı atılır; geçmişe dönüp bakılmaz, bellek $O(1)$ sabittir!
2. **`Quadratic / Chunkwise Matrix (Attention) Modu` (Eğitim / `Prefill` sırasında):** `Mamba-1` eğitim sırasında GPU'nun `Tensor Core` matris çarpım birimlerini kullanamıyordu (özel `Parallel Associative Scan` gerektiriyordu). **`Mamba-2 (SSD)`** ise diziyi $Q=64$ boyutlu bloklara (`Chunks`) bölüp blok içinde doğrudan $M = L \odot (C B^\top)$ matris çarpımı yaptığı için GPU **`Tensor Core` birimlerini %100 verimle kullanarak `Mamba-1`'den 2-8 kat daha hızlı eğitilir!**
:::

::: anlat 3. AI21 Jamba, Zyphra Zamba ve NVIDIA Nemotron-H: Hibrit Mimari Mühendisliği
Peki gerçek bir `Frontier Hybrid Model` (`AI21 Jamba-1.5`, `Zyphra Zamba2`, `NVIDIA Nemotron-H`, `IBM Bamba`) katmanları nasıl dizer?

### 🏗️ Altın Oran: `1:7 Attention-to-Mamba Ratio`
Deneyler göstermiştir ki bir modeldeki katmanların hepsini `Attention` yapmak gereksiz bir bellek israfıdır; **her 8 katmandan yalnızca 1 tanesinin `Grouped-Query Attention (GQA)` olması ve kalan 7 katmanın `Mamba-2 (SSD)` olması**, `%100 Attention` modelle birebir aynı (hatta daha yüksek!) `Needle-in-a-Haystack` ve `Reasoning` başarısını verirken:
- **`KV-Cache` belleğini tam 8 kat (%87.5!) küçültür!**
- Uzun bağlam (`256K - 1M token`) üretim hızını (`Throughput`) **3 ila 5 kat artırır!**

### 💡 Hibrit Mimarilerde 2 Kritik Mühendislik Püf Noktası:
1. **Hibrit Modelde `RoPE` (Konumsal Kodlama) Gerekli mi?**
   - Şaşırtıcı gerçek: **`Jamba` mimarisinde `Attention` katmanlarında bile `RoPE` (`Positional Embedding`) KULLANILMAZ (`NoPE`)!** Çünkü `Attention` katmanından önce gelen `Mamba` katmanları zaten nedensel özyineleme (`Recurrence`) yaptığı için her `token` vektörünün içine sıra/konum bilgisini doğal olarak işler!
2. **Aktivasyon Sıçramalarını Önlemek İçin İç `RMSNorm`:**
   - `Mamba` ve `Attention` katmanları üst üste bindiğinde uzun bağlamlarda aktivasyon normları büyüyebilir; bu yüzden `Mamba-2` bloğunun çıkışında kapılamadan sonra ekstra bir `RMSNorm` katmanı kullanılır.

```python norun
import torch
import torch.nn as nn

class HybridJambaBlock(nn.Module):
    """Gerçek bir Hibrit (Mamba-2 SSD + GQA Attention + MoE) Katman Bloğu İskeleti"""
    def __init__(self, layer_idx: int, d_model: int, attn_every_n: int = 8, moe_every_n: int = 2):
        super().__init__()
        self.norm1 = nn.RMSNorm(d_model)
        # Her 8 katmanda 1 GQA Attention, diğer 7 katmanda Mamba-2 SSD!
        self.is_attention = (layer_idx % attn_every_n == (attn_every_n - 1))
        if self.is_attention:
            self.SequenceMixer = GQAAttentionLayer(d_model)
        else:
            self.SequenceMixer = Mamba2SSDLayer(d_model)

        self.norm2 = nn.RMSNorm(d_model)
        # Her 2 katmanda 1 Sparse MoE, diğerlerinde Dense SwiGLU!
        self.is_moe = (layer_idx % moe_every_n == 1)
        self.FFN = DeepSeekMoELayer(d_model) if self.is_moe else SwiGLUMLP(d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.SequenceMixer(self.norm1(x))
        x = x + self.FFN(self.norm2(x))
        return x
```
:::

::: tahmin Salt Transformer vs Hibrit Jamba (1:7) KV-Cache Bellek Karşılaştırması
32 katmanlı bir modelde `256.000` (`256K`) `token` uzunluğunda bir belge işleniyor. Tek bir `GQA Attention` katmanı `token` başına `512 Byte` `KV-Cache` harcarken, tek bir `Mamba-2` katmanı bağlam uzunluğundan bağımsız olarak toplamda sadece `2 MB` sabit `SSM State` belleği harcıyor.
- **Model A:** 32 katmanın tamamı `Attention` (`Salt Transformer`).
- **Model B:** 32 katmanın sadece 4'ü `Attention` (`1:7 oranı`), 28'i `Mamba-2` (`Hibrit Jamba`).
Bu iki modelin `256K` bağlamda harcadığı toplam durum/önbellek belleği (`MB`) nedir?

```python
baglam = 256_000
attn_katman_mb = (baglam * 512) / (1024 * 1024)  # MB cinsinden 1 Attention katmanı
mamba_katman_mb = 2.0                            # Sabit 2 MB!

salt_transformer_mb = 32 * attn_katman_mb
hibrit_jamba_mb = (4 * attn_katman_mb) + (28 * mamba_katman_mb)
print(f"Salt Transformer: {salt_transformer_mb:.0f} MB | Hibrit Jamba: {hibrit_jamba_mb:.0f} MB")
```

???

```cikti
Salt Transformer: 4000 MB | Hibrit Jamba: 556 MB
```
Tek bir `Attention` katmanı `256.000 * 512 Byte = 125 MB` `KV-Cache` tutar. 32 katmanlı salt `Transformer` toplamda `32 * 125 = 4000 MB` (`4 GB`) harcarken; 4 `Attention` + 28 `Mamba-2` kullanan hibrit `Jamba` modeli `4 * 125 + 28 * 2 = 500 + 56 = 556 MB` bellek harcar (`~7.2 kat` bellek tasarrufu!).
:::

::: gorev 1 · Mamba-2 SSD (Structured State Space Duality) 1-Semiseparable Matris ve Durum Güncellemesi
`Mamba-2` mimarisindeki **`Structured State Space Duality (SSD)`** teoremini doğrulayan, yani hem **özyinelemeli durum güncellemesini (`Recurrent SSM Form`)** hem de **`1-Semiseparable` matris formunu (`Dual Matrix Form` $M_{t,s}$)** hesaplayan `ssd_durum_adimi(x_dizi, a_curume, B_giris, C_cikis)` işlevini yaz:

1. **Girdiler (Uzunluğu $T$ olan dizi):**
   - `x_dizi`: $T$ adet skaler girdi değeri ($x_0, \dots, x_{T-1}$).
   - `a_curume`: $T$ adet skaler unutma/çürüme çarpanı ($a_0, \dots, a_{T-1} \in (0, 1]$).
   - `B_giris`: $T \times N$ boyutlu giriş projeksiyon vektörleri ($B_t \in \mathbb{R}^N$).
   - `C_cikis`: $T \times N$ boyutlu çıkış projeksiyon vektörleri ($C_t \in \mathbb{R}^N$).
2. **Hesaplamalar:**
   - **A) Özyinelemeli (`Recurrent`) Hesap:**
     - Başlangıçta $N$ boyutlu gizli durum vektörü $h = [0.0, \dots, 0.0]$'dır.
     - Her $t = 0, \dots, T-1$ adımında:
       $$h_n \leftarrow a_t \cdot h_n + B_{t, n} \cdot x_t \quad (\forall n \in \{0, \dots, N-1\})$$
       $$y_t = \sum_{n=0}^{N-1} C_{t, n} \cdot h_n$$
   - **B) İkili (`Dual 1-Semiseparable Matrix` $M$) Hesap:**
     - Boyutu $T \times T$ olan alt-üçgen $M$ matrisini oluştur:
     - Eğer $t < s$ ise $M_{t, s} = 0.0$.
     - Eğer $t \ge s$ ise:
       - Kümülatif çürüme çarpanı: $t == s$ ise $\text{curume} = 1.0$, $t > s$ ise $\text{curume} = \prod_{k=s+1}^{t} a_k$.
       - İç çarpım: $\text{cb} = \sum_{n=0}^{N-1} C_{t, n} \cdot B_{s, n}$.
       - $M_{t, s} = \text{curume} \cdot \text{cb}$.
     - Matris çarpımıyla $(M \cdot x)_t = \sum_{s=0}^{t} M_{t, s} x_s$ değerlerinin `y_t` ile birebir aynı olduğunu göreceksin!
   - Tüm sayısal çıktıları `round(val, 6)` ile yuvarla.
3. **Dönüş Değeri:**
   `{"cikti_y": [float, ...], "son_durum_h": [float, ...], "dual_matris_M": [[float, ...], ...]}` sözlüğü döndür.

```starter
def ssd_durum_adimi(x_dizi, a_curume, B_giris, C_cikis):
    # KUSURLU BAŞLANGIÇ KODU: durum özyinelemesini ve 1-Semiseparable M matrisini hesaplamıyor!
    T = len(x_dizi)
    N = len(B_giris[0])
    return {
        "cikti_y": [0.0] * T,
        "son_durum_h": [0.0] * N,
        "dual_matris_M": [[0.0] * T for _ in range(T)],
    }

print(ssd_durum_adimi([1.0, 2.0], [0.9, 0.5], [[1.0, 0.5], [0.2, 1.0]], [[0.5, 1.0], [1.0, 0.5]]))
```

```test
import copy

def _ref_ssd(x, a, B, C):
    T = len(x)
    N = len(B[0])
    h = [0.0] * N
    y = []
    for t in range(T):
        h = [a[t] * h[n] + B[t][n] * x[t] for n in range(N)]
        yt = sum(C[t][n] * h[n] for n in range(N))
        y.append(round(yt, 6))
    M = [[0.0] * T for _ in range(T)]
    for t in range(T):
        for s in range(t + 1):
            cur = 1.0
            for k in range(s + 1, t + 1):
                cur *= a[k]
            cb = sum(C[t][n] * B[s][n] for n in range(N))
            M[t][s] = round(cur * cb, 6)
    return {
        "cikti_y": y,
        "son_durum_h": [round(v, 6) for v in h],
        "dual_matris_M": M,
    }

def sozlesme(fn):
    try:
        vakalar = [
            ([1.0, 2.0], [0.9, 0.5], [[1.0, 0.5], [0.2, 1.0]], [[0.5, 1.0], [1.0, 0.5]]),
            ([2.0, -1.0, 0.5], [0.8, 0.5, 0.25], [[1.0, 0.0], [0.5, 1.5], [2.0, -0.5]], [[1.0, 1.0], [0.5, -1.0], [0.0, 2.0]]),
        ]
        for args in vakalar:
            sonuc = fn(*copy.deepcopy(args))
            bek = _ref_ssd(*args)
            if sonuc != bek:
                return False
            # Dualite kontrolü: M @ x == cikti_y olmalı!
            T = len(args[0])
            for t in range(T):
                mx_t = sum(sonuc["dual_matris_M"][t][s] * args[0][s] for s in range(T))
                if abs(mx_t - sonuc["cikti_y"][t]) > 1e-4:
                    return False
        return True
    except Exception:
        return False

ok(sozlesme(ssd_durum_adimi), "ssd_durum_adimi hem özyinelemeli SSM durumunu hem de 1-Semiseparable M matrisini dualiteye uygun hesaplamalı")

def m_curume_unut(x, a, B, C):
    return ssd_durum_adimi(x, [1.0] * len(a), B, C)

def m_kosegen_m(x, a, B, C):
    r = copy.deepcopy(ssd_durum_adimi(x, a, B, C))
    T = len(x)
    for t in range(T):
        for s in range(t):
            r["dual_matris_M"][t][s] = 0.0
    return r

for ad, m in [("Seçici çürüme a_t çarpanlarını unutan", m_curume_unut), ("M matrisinin alt-üçgen geçmiş terimlerini sıfırlayan", m_kosegen_m)]:
    ok(not sozlesme(m), f"Yanlış çözüm/mutant yakalanmalı: {ad}")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def ssd_durum_adimi(x_dizi, a_curume, B_giris, C_cikis):\n    T = len(x_dizi)\n    N = len(B_giris[0])\n    h = [0.0] * N\n    cikti_y = []\n    for t in range(T):\n        h = [a_curume[t] * h[n] + B_giris[t][n] * x_dizi[t] for n in range(N)]\n        yt = sum((C_cikis[t][n] * h[n] for n in range(N)))\n        cikti_y.append(round(yt, 6))\n    M = [[0.0] * T for _ in range(T)]\n    for t in range(T):\n        for s in range(t + 1):\n            curume = 1.0\n            for k in range(s + 1, t + 1):\n                curume *= a_curume[k]\n            cb = sum((C_cikis[t][n] * B_giris[s][n] for n in range(N)))\n            M[t][s] = round(curume * cb, 6)\n    return {'cikti_y': cikti_y, 'son_durum_h': [round(deger, 6) for deger in h], 'dual_matris_M': M}", 'referans', 'exec'), _REF)
_t, _g = _ff(ssd_durum_adimi, _REF['ssd_durum_adimi'], ([1.0, 2.0], [0.9, 0.5], [[1.0, 0.5], [0.2, 1.0]], [[0.5, 1.0], [1.0, 0.5]]), tohum=2645, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (ssd_durum_adimi): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
ok(ssd_durum_adimi([0.31, 0.71], [0.91, 0.83], [[0.1234567, 0.23], [0.31, 0.41]], [[0.73, 0.61], [0.53, 0.37]]) == _REF['ssd_durum_adimi']([0.31, 0.71], [0.91, 0.83], [[0.1234567, 0.23], [0.31, 0.41]], [[0.73, 0.61], [0.53, 0.37]]), "6 basamak SSD yuvarlaması korunmalı")
```

```solution
def ssd_durum_adimi(x_dizi, a_curume, B_giris, C_cikis):
    T = len(x_dizi)
    N = len(B_giris[0])
    h = [0.0] * N
    cikti_y = []

    for t in range(T):
        h = [a_curume[t] * h[n] + B_giris[t][n] * x_dizi[t] for n in range(N)]
        yt = sum(C_cikis[t][n] * h[n] for n in range(N))
        cikti_y.append(round(yt, 6))

    M = [[0.0] * T for _ in range(T)]
    for t in range(T):
        for s in range(t + 1):
            curume = 1.0
            for k in range(s + 1, t + 1):
                curume *= a_curume[k]
            cb = sum(C_cikis[t][n] * B_giris[s][n] for n in range(N))
            M[t][s] = round(curume * cb, 6)

    return {
        "cikti_y": cikti_y,
        "son_durum_h": [round(deger, 6) for deger in h],
        "dual_matris_M": M,
    }
```

```hint
Özyinelemeli adımda her `t` için `h = [a_curume[t] * h[n] + B_giris[t][n] * x_dizi[t] for n in range(N)]` güncellemesini yapıp `C_cikis[t]` ile iç çarpımını al. `M[t][s]` (`t >= s`) için `s+1`'den `t`'ye kadar `a_curume[k]` değerlerini çarp ve `C_cikis[t]` ile `B_giris[s]` iç çarpımıyla çarp.
```
:::

::: gorev 2 · Hibrit Jamba Katman Planlayıcı ve Toplam KV-Cache + SSM State Bellek Hesabı
Verilen bir hibrit model yapılandırması için katman dizilimini (`"mamba"` veya `"attention"`) ve toplam önbellek/durum belleği tasarrufunu hesaplayan `hibrit_katman_bellegi(toplam_katman, attention_periyodu, baglam_uzunlugu, kv_bayt_token, ssm_state_bayt)` işlevini yaz:

1. **Girdiler:**
   - `toplam_katman`: Modeldeki toplam katman sayısı $L$ (`int > 0`).
   - `attention_periyodu`: Kaç katmanda bir `Attention` kullanılacağı $P$ (`int > 0`, örn. `8` ise her 8 katmanın sonuncusu, yani `(i + 1) % P == 0` olan katmanlar `"attention"`, diğerleri `"mamba"` olur).
   - `baglam_uzunlugu`: İşlenen `token` sayısı $T$ (`int > 0`).
   - `kv_bayt_token`: Tek bir `"attention"` katmanının **tek bir `token` başına** harcadığı `KV-Cache` belleği (`Byte`). (Dolayısıyla 1 `"attention"` katmanı toplam `baglam_uzunlugu * kv_bayt_token` Byte harcar).
   - `ssm_state_bayt`: Tek bir `"mamba"` katmanının bağlam uzunluğundan bağımsız olarak harcadığı **sabit `SSM State` belleği** (`Byte`).
2. **Hesaplamalar:**
   - `katman_tipleri`: `i = 0, ..., toplam_katman - 1` için `(i + 1) % attention_periyodu == 0` ise `"attention"`, değilse `"mamba"` içeren liste.
   - `attention_katman_sayisi` ve `mamba_katman_sayisi`: İlgili katmanların sayıları.
   - `hibrit_toplam_bayt`: `attention_katman_sayisi * (baglam_uzunlugu * kv_bayt_token) + mamba_katman_sayisi * ssm_state_bayt`.
   - `salt_transformer_bayt`: Tüm katmanlar `"attention"` olsaydı harcanacak bellek (`toplam_katman * baglam_uzunlugu * kv_bayt_token`).
   - `tasarruf_orani`: `round(1.0 - (hibrit_toplam_bayt / salt_transformer_bayt), 4)` (belleğin yüzde kaçının tasarruf edildiği, `0.0` ile `1.0` arası).
3. **Dönüş Değeri:**
   `{"katman_tipleri": [str, ...], "attention_katman_sayisi": int, "mamba_katman_sayisi": int, "hibrit_toplam_bayt": int, "salt_transformer_bayt": int, "tasarruf_orani": float}` sözlüğü döndür.

```starter
def hibrit_katman_bellegi(toplam_katman, attention_periyodu, baglam_uzunlugu, kv_bayt_token, ssm_state_bayt):
    # KUSURLU BAŞLANGIÇ KODU: bütün katmanları mamba kabul ediyor ve bellekleri sıfır döndürüyor!
    return {
        "katman_tipleri": ["mamba"] * toplam_katman,
        "attention_katman_sayisi": 0,
        "mamba_katman_sayisi": toplam_katman,
        "hibrit_toplam_bayt": 0,
        "salt_transformer_bayt": 0,
        "tasarruf_orani": 0.0,
    }

print(hibrit_katman_bellegi(toplam_katman=16, attention_periyodu=8, baglam_uzunlugu=100_000, kv_bayt_token=512, ssm_state_bayt=65_536))
```

```test
import copy

def _ref_hibrit(L, P, T, kv_b, ssm_b):
    tipler = ["attention" if (i + 1) % P == 0 else "mamba" for i in range(L)]
    n_att = tipler.count("attention")
    n_mam = tipler.count("mamba")
    hib_b = n_att * (T * kv_b) + n_mam * ssm_b
    tr_b = L * T * kv_b
    tas = round(1.0 - (hib_b / tr_b), 4)
    return {
        "katman_tipleri": tipler,
        "attention_katman_sayisi": n_att,
        "mamba_katman_sayisi": n_mam,
        "hibrit_toplam_bayt": hib_b,
        "salt_transformer_bayt": tr_b,
        "tasarruf_orani": tas,
    }

def sozlesme(fn):
    try:
        vakalar = [
            (16, 8, 100_000, 512, 65_536),
            (32, 4, 64_000, 1024, 131_072),
            (10, 3, 50_000, 256, 32_768),
        ]
        for args in vakalar:
            if fn(*args) != _ref_hibrit(*args):
                return False
        return True
    except Exception:
        return False

ok(sozlesme(hibrit_katman_bellegi), "hibrit_katman_bellegi Mamba/Attention dizilimini ve KV-Cache + SSM State bellek tasarrufunu doğru hesaplamalı")

def m_ssm_token_carp(L, P, T, kv_b, ssm_b):
    r = copy.deepcopy(hibrit_katman_bellegi(L, P, T, kv_b, ssm_b))
    r["hibrit_toplam_bayt"] += r["mamba_katman_sayisi"] * T * ssm_b
    return r

def m_yanlis_indeks(L, P, T, kv_b, ssm_b):
    r = copy.deepcopy(hibrit_katman_bellegi(L, P, T, kv_b, ssm_b))
    r["katman_tipleri"] = ["attention" if i % P == 0 else "mamba" for i in range(L)]
    return r

for ad, m in [("SSM sabit durumunu yanlışlıkla token sayısıyla çarpan", m_ssm_token_carp), ("Attention katman periyodunu yanlış indeksleyen", m_yanlis_indeks)]:
    ok(not sozlesme(m), f"Yanlış çözüm/mutant yakalanmalı: {ad}")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def hibrit_katman_bellegi(toplam_katman, attention_periyodu, baglam_uzunlugu, kv_bayt_token, ssm_state_bayt):\n    tipler = ['attention' if (i + 1) % attention_periyodu == 0 else 'mamba' for i in range(toplam_katman)]\n    n_att = tipler.count('attention')\n    n_mam = tipler.count('mamba')\n    hibrit_bayt = n_att * (baglam_uzunlugu * kv_bayt_token) + n_mam * ssm_state_bayt\n    salt_bayt = toplam_katman * baglam_uzunlugu * kv_bayt_token\n    tasarruf = round(1.0 - hibrit_bayt / salt_bayt, 4)\n    return {'katman_tipleri': tipler, 'attention_katman_sayisi': n_att, 'mamba_katman_sayisi': n_mam, 'hibrit_toplam_bayt': hibrit_bayt, 'salt_transformer_bayt': salt_bayt, 'tasarruf_orani': tasarruf}", 'referans', 'exec'), _REF)
_t, _g = _ff(hibrit_katman_bellegi, _REF['hibrit_katman_bellegi'], (16, 8, 100000, 512, 65536), tohum=3244, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (hibrit_katman_bellegi): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def hibrit_katman_bellegi(toplam_katman, attention_periyodu, baglam_uzunlugu, kv_bayt_token, ssm_state_bayt):
    tipler = [
        "attention" if (i + 1) % attention_periyodu == 0 else "mamba"
        for i in range(toplam_katman)
    ]
    n_att = tipler.count("attention")
    n_mam = tipler.count("mamba")
    hibrit_bayt = n_att * (baglam_uzunlugu * kv_bayt_token) + n_mam * ssm_state_bayt
    salt_bayt = toplam_katman * baglam_uzunlugu * kv_bayt_token
    tasarruf = round(1.0 - (hibrit_bayt / salt_bayt), 4)

    return {
        "katman_tipleri": tipler,
        "attention_katman_sayisi": n_att,
        "mamba_katman_sayisi": n_mam,
        "hibrit_toplam_bayt": hibrit_bayt,
        "salt_transformer_bayt": salt_bayt,
        "tasarruf_orani": tasarruf,
    }
```

```hint
`(i + 1) % attention_periyodu == 0` koşuluyla `"attention"` ve `"mamba"` katmanlarını ayır. Attention katmanları `baglam_uzunlugu * kv_bayt_token` harcarken, Mamba katmanları bağlam uzunluğundan bağımsız olarak sadece `ssm_state_bayt` harcar.
```
:::

::: anlat Gerçek deney: Gerçek mamba-130m karıştırıcısını yeniden üretmek ve ölçülen önbelleklerle hibrit plan
Final yerel önbellekteki gerçek **mamba-130m** (Mamba-1) modelini kullanır (indirme yok):

- 6. katmanın karıştırıcısı (`MambaMixer`) gerçek bir cümlede çalıştırılır; girdisi ve çıktısı kancayla yakalanır. Aynı çıktı modelin **gerçek parametrelerinden** (`in_proj`, `conv1d`, `x_proj`, `dt_proj`, `A_log`, `D`, `out_proj`) torch'ta yazılmış seçici taramayla yeniden üretilir: $\Delta = \text{softplus}(\cdot)$, $\bar A = e^{\Delta A}$, $h_t = \bar A_t h_{t-1} + \Delta_t B_t x_t$, $y_t = C_t h_t$.
- Mamba-1'de $A$ köşegendir: her durum boyutunun kendi çürümesi vardır. Senin `ssd_durum_adimi` işlevin Mamba-2'deki gibi skaler bir çürüme alır; bu yüzden seçilen 5 kanalın 16 durum boyutunun her biri ayrı ayrı ($N = 1$) işlevine verilir ve çıktılar toplanır. Sonuç gerçek taramayla karşılaştırılır. Ayrıca senin dual matrisin $M$ ile $M x$ çarpımı yinelemenin çıktısıyla aynı olmalıdır: SSD'nin "ikiliği" budur.
- **Bellek:** SmolLM2'nin KV-cache'i ve Mamba'nın durum önbelleği 64 ve 512 token için **ölçülür**. KV uzunlukla doğrusal büyür, Mamba durumu sabit kalır. Ölçülen değerler senin `hibrit_katman_bellegi` işlevine verilir (32 katman, her 8'de bir dikkat, 100K bağlam).

**Güvenlik yönü — sabit boyutlu durumu taşırmak:** Başa bir parola anahtarı yazılır, ardından 0–160 tekrar yapay dolgu metni ve "parola anahtarı ne?" sorusu gelir (en çok ~3 900 token). Anahtarın log-olasılığı mamba-130m'de ve SmolLM2'de ölçülür. Mamba'nın durumu uzunluktan bağımsız sabit boyutta olduğu için dolgu arttıkça anahtar silinir; SmolLM2 her tokenın KV'sini tuttuğu için anahtarı hatırlar. Güvenlik açısından iki yüzü vardır: saldırgan uzun bir girdiyle SSM'nin başta verilen talimatlarını **silebilir** (durum taşırma), öte yandan bu unutma bir silme garantisi değildir: anahtar hiç verilmemiş taban değerin hâlâ çok üstündedir. Hibrit modellerdeki dikkat katmanları birebir hatırlamayı geri getirir.

Kabul: iki işlevin farksal taramayı geçmesi; gerçek karıştırıcının `1e-4` içinde yeniden üretilmesi; SSD'nin gerçek taramadan ve $Mx$'in yinelemeden göreli `1e-5` altında farklı olması; Mamba durumunun uzunluktan bağımsız, KV'nin doğrusal olması; hibrit planın ölçülen değerlerle bağımsız hesapla aynı olması. Ayrıca dolgu arttıkça Mamba'da anahtarın log-olasılığı en az 3 nat düşmeli ama anahtarsız tabanın üstünde kalmalı, SmolLM2'de her uzunlukta −1.5'in üstünde kalmalıdır.

**Kanıt dosyasını oku:** `mikser_yeniden_uretim_fark`, `ogrenci_tarama_fark`, `dual_fark`, `cuk_ortalama`, `olcum_onbellek`, `kv_bayt_token_katman`, `ssm_bayt_katman`, `hibrit`. Soru 1: Mamba durumu 122 880 bayt/katman; hangi bağlam uzunluğundan sonra SmolLM2'nin bir katmanının KV'sinden küçük kalır? Soru 2: Mamba-1'in köşegen A'sı neden tek bir matris çarpımına (SSD) dönüştürülemez? Soru 3: Sabit boyutlu durum, uzun bir belgedeki bir telefon numarasını neden birebir hatırlayamayabilir?
:::

::: gorev Gerçek deney · Gerçek mamba-130m karıştırıcısında SSD taraması ve ölçülen KV/SSM önbellekleriyle hibrit plan
Önceki görevlerdeki `ssd_durum_adimi`, `hibrit_katman_bellegi` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 240
```
```starter
import ai_lab
def ssd_durum_adimi(x_dizi, a_curume, B_giris, C_cikis):
    T = len(x_dizi)
    N = len(B_giris[0])
    return {'cikti_y': [0.0] * T, 'son_durum_h': [0.0] * N, 'dual_matris_M': [[0.0] * T for _ in range(T)]}

def hibrit_katman_bellegi(toplam_katman, attention_periyodu, baglam_uzunlugu, kv_bayt_token, ssm_state_bayt):
    return {'katman_tipleri': ['mamba'] * toplam_katman, 'attention_katman_sayisi': 0, 'mamba_katman_sayisi': toplam_katman, 'hibrit_toplam_bayt': 0, 'salt_transformer_bayt': 0, 'tasarruf_orani': 0.0}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_20 as D
    D.goster(ssd_durum_adimi, hibrit_katman_bellegi)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_cache_bayt', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
ssd_durum_adimi = need("ssd_durum_adimi")
hibrit_katman_bellegi = need("hibrit_katman_bellegi")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def ssd_durum_adimi(x_dizi, a_curume, B_giris, C_cikis):\n    T = len(x_dizi)\n    N = len(B_giris[0])\n    h = [0.0] * N\n    cikti_y = []\n    for t in range(T):\n        h = [a_curume[t] * h[n] + B_giris[t][n] * x_dizi[t] for n in range(N)]\n        yt = sum((C_cikis[t][n] * h[n] for n in range(N)))\n        cikti_y.append(round(yt, 6))\n    M = [[0.0] * T for _ in range(T)]\n    for t in range(T):\n        for s in range(t + 1):\n            curume = 1.0\n            for k in range(s + 1, t + 1):\n                curume *= a_curume[k]\n            cb = sum((C_cikis[t][n] * B_giris[s][n] for n in range(N)))\n            M[t][s] = round(curume * cb, 6)\n    return {'cikti_y': cikti_y, 'son_durum_h': [round(deger, 6) for deger in h], 'dual_matris_M': M}\n\ndef hibrit_katman_bellegi(toplam_katman, attention_periyodu, baglam_uzunlugu, kv_bayt_token, ssm_state_bayt):\n    tipler = ['attention' if (i + 1) % attention_periyodu == 0 else 'mamba' for i in range(toplam_katman)]\n    n_att = tipler.count('attention')\n    n_mam = tipler.count('mamba')\n    hibrit_bayt = n_att * (baglam_uzunlugu * kv_bayt_token) + n_mam * ssm_state_bayt\n    salt_bayt = toplam_katman * baglam_uzunlugu * kv_bayt_token\n    tasarruf = round(1.0 - hibrit_bayt / salt_bayt, 4)\n    return {'katman_tipleri': tipler, 'attention_katman_sayisi': n_att, 'mamba_katman_sayisi': n_mam, 'hibrit_toplam_bayt': hibrit_bayt, 'salt_transformer_bayt': salt_bayt, 'tasarruf_orani': tasarruf}", 'referans', 'exec'), _REF)
_t, _g = _ff(ssd_durum_adimi, _REF['ssd_durum_adimi'], ([1.0, 2.0], [0.9, 0.5], [[1.0, 0.5], [0.2, 1.0]], [[0.5, 1.0], [1.0, 0.5]]), tohum=2645, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (ssd_durum_adimi): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(hibrit_katman_bellegi, _REF['hibrit_katman_bellegi'], (16, 8, 100000, 512, 65536), tohum=3244, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (hibrit_katman_bellegi): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
kontrol(ssd_durum_adimi([0.31, 0.71], [0.91, 0.83], [[0.1234567, 0.23], [0.31, 0.41]], [[0.73, 0.61], [0.53, 0.37]]) == _REF['ssd_durum_adimi']([0.31, 0.71], [0.91, 0.83], [[0.1234567, 0.23], [0.31, 0.41]], [[0.73, 0.61], [0.53, 0.37]]), "6 basamak SSD yuvarlaması korunmalı")
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_20 as D
try: r = D.deney(ssd_durum_adimi, hibrit_katman_bellegi)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['mikser_ayni'], 'gerçek Mamba karıştırıcısı gerçek parametrelerden yeniden üretildi')
kontrol(r['ogrenci_ayni'] and r['dual_ayni'], 'SSD yinelemesi gerçek taramayla, dual M·x yinelemeyle aynı')
kontrol(r['ssm_sabit'] and r['kv_dogrusal'], 'ölçülen Mamba durumu uzunluktan bağımsız, KV-cache doğrusal büyüyor')
kontrol(r['hibrit_ayni'], 'hibrit bellek planı ölçülen değerlerle bağımsız hesapla aynı')
kontrol(r['mamba_unutuyor'] and r['smollm2_hatirliyor'], "uzun dolgu Mamba'nın sabit durumundaki anahtarı aşındırdı, SmolLM2 her uzunlukta hatırladı")
ai_lab.kanit_yaz("ai-uretim-20-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-20", "deney": r})
```
```solution
import ai_lab
def ssd_durum_adimi(x_dizi, a_curume, B_giris, C_cikis):
    T = len(x_dizi)
    N = len(B_giris[0])
    h = [0.0] * N
    cikti_y = []
    for t in range(T):
        h = [a_curume[t] * h[n] + B_giris[t][n] * x_dizi[t] for n in range(N)]
        yt = sum((C_cikis[t][n] * h[n] for n in range(N)))
        cikti_y.append(round(yt, 6))
    M = [[0.0] * T for _ in range(T)]
    for t in range(T):
        for s in range(t + 1):
            curume = 1.0
            for k in range(s + 1, t + 1):
                curume *= a_curume[k]
            cb = sum((C_cikis[t][n] * B_giris[s][n] for n in range(N)))
            M[t][s] = round(curume * cb, 6)
    return {'cikti_y': cikti_y, 'son_durum_h': [round(deger, 6) for deger in h], 'dual_matris_M': M}

def hibrit_katman_bellegi(toplam_katman, attention_periyodu, baglam_uzunlugu, kv_bayt_token, ssm_state_bayt):
    tipler = ['attention' if (i + 1) % attention_periyodu == 0 else 'mamba' for i in range(toplam_katman)]
    n_att = tipler.count('attention')
    n_mam = tipler.count('mamba')
    hibrit_bayt = n_att * (baglam_uzunlugu * kv_bayt_token) + n_mam * ssm_state_bayt
    salt_bayt = toplam_katman * baglam_uzunlugu * kv_bayt_token
    tasarruf = round(1.0 - hibrit_bayt / salt_bayt, 4)
    return {'katman_tipleri': tipler, 'attention_katman_sayisi': n_att, 'mamba_katman_sayisi': n_mam, 'hibrit_toplam_bayt': hibrit_bayt, 'salt_transformer_bayt': salt_bayt, 'tasarruf_orani': tasarruf}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_20 as D
    D.goster(ssd_durum_adimi, hibrit_katman_bellegi)
```
```hint
İki görevin çözümlerini olduğu gibi buraya koy. mamba_ssm kurulu değilse transformers yavaş PyTorch yoluna düşer; sonuç aynıdır.
```
:::

::: anlat Sınır
Görevler Mamba-2 SSD'nin 1-semiseparable matrisini ve durum güncellemesini, Jamba katman planını ve KV + SSM bellek hesabını küçük sayılarla yazdırır; final adım gerçek mamba-130m karıştırıcısını yeniden üretir ve önbellekleri ölçer (hibrit model eğitilmez). Mamba-2'nin skaler çarpı birim matris biçimindeki A yapısı SSD'nin matris çarpımı hızını sağlar; Mamba-1'in diagonal A'sı daha ifade gücüne sahiptir ama bu hızı kaybeder. Sabit boyutlu durum, uzun bağlamda birebir kopyalama ve geri çağırma görevlerinde Transformer'ın gerisinde kalır; hibritlerdeki az sayıda dikkat katmanı bu yüzden vardır. 1:7 oranı Jamba'nın tercihidir, evrensel bir kural değildir.

Kaynaklar: [Gu ve Dao 2023 - Mamba: Linear-Time Sequence Modeling with Selective State Spaces](https://arxiv.org/abs/2312.00752), [Dao ve Gu 2024 - Transformers are SSMs: Generalized Models and Efficient Algorithms Through Structured State Space Duality](https://arxiv.org/abs/2405.21060), [Lieber vd. 2024 - Jamba: A Hybrid Transformer-Mamba Language Model](https://arxiv.org/abs/2403.19887).
:::

::: dusun
Sahnede bir mühendis şu soruyu sordu:
*"Hocam, `Zyphra Zamba` adlı hibrit mimaride çok ilginç bir tasarım var: 32 katman boyunca hızlı `Mamba` blokları ilerliyor ve her 6 katmanda bir devreye giren `Attention` bloğu, her seferinde yeni ağırlıklar kullanmak yerine **tek bir ortak `Shared Attention` bloğunun ağırlıklarını (`Parameter Tying`)** tekrar tekrar kullanıyor! Bu tasarımın hem model parametre sayısına (`VRAM`) hem de `KV-Cache` belleğine etkisi nedir?"*

Bu soruya **`Shared Attention Weights` (Parametre paylaşımıyla model ağırlık belleğinden tasarruf)** ve hatta **`Shared KV-Cache` (Tek bir ortak Key-Value önbelleğinin farklı derinliklerde tekrar sorgulanması)** açısından nasıl yanıt verirsin?
:::

::: ozet
- Salt **`SSM (Mamba)`** modelleri $O(1)$ sabit durum belleği ve $O(T)$ hız sunsa da, sabit boyutlu gizli durum vektörü ($h_t$) uzun metinlerdeki rastgele detayları birebir kopyalama (**`In-Context Copying / Needle-in-a-Haystack`**) görevlerinde kayıplı sıkıştırma darboğazına takılır.
- **`Mamba-2` (`Structured State Space Duality - SSD`)**, seçici durum uzayı özyinelemesinin ($h_t = a_t h_{t-1} + B_t x_t$) matematiksel olarak **`1-Semiseparable`** bir dikkat matrisiyle ($M_{t,s} = a_{t:s}^\times C_t^\top B_s$) birebir eşdeğer olduğunu kanıtlayarak eğitimde `Tensor Core` matris hızı, üretimde ise $O(1)$ durum belleği sağlar.
- **`Jamba / Zamba / Nemotron-H` Hibrit Mimarileri**, her 8 katmanın 7'sini `Mamba-2` ve 1'ini `GQA Attention` (+ `Sparse MoE`) yaparak `KV-Cache` belleğini `%85+` oranında küçültürken `%100` kesin hatırlama (`Recall`) yeteneğini korur.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Sabit durum vs tam önbellek ikilemi (30 sn).** "Durum uzayı modelleri (`Mamba / SSM`) geçmişi sabit boyutlu bir $h_t$ matrisine sıkıştırarak $O(1)$ bellekle akar ama uzak bir şifreyi harfi harfine kopyalamakta (`In-Context Copying`) zorlanır; `Transformer` ise her tokenı saklar ama `KV Cache` maliyeti doğrusal büyür."
2. **`Structured State Space Duality (SSD)` (35 sn).** "`Mamba-2`, seçici durum geçişini yarı-ayrılabilir (`1-semiseparable`) maskeli dikkat formuyla eşleştirerek eğitimde Tensor Core blok matris çarpımlarını, çıkarımda ise sabit bellekli yinelemeyi kullanır."
3. **Hibrit katman oranı (`Jamba / Zamba`) (30 sn).** "Her 7–8 `Mamba` katmanının arasına tek bir tam `Attention` katmanı serpiştirmek `KV Cache` belleğini ~8 kat küçültürken samanlıkta iğne bulma yeteneğini korur."
4. **Soru (25 sn).** "Hibrit bir modelde tam dikkat katmanlarının oranını sıfıra indirdiğimizde hangi tür güvenlik veya doğrulama görevlerinde keskin düşüş görürüz?"
:::
