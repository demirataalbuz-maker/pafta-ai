---
id: ai-temel-33
title: Sıfırdan Frontier AI Üretimi II · 3D Parallelism (DP/TP/PP) ve μP
summary: Trilyon parametreli bir modeli 30.000 GPU üzerinde eğitmenin sistem mühendisliği: Data Parallelism (ZeRO/FSDP), Tensor Parallelism, Pipeline Parallelism, FlashAttention ve Maximal Update Parametrization (μP).
esleme: ai-temel-32, ai-uretim-08, ai-uretim-15
---

::: anlat 1. Tek Bir GPU'ya Sığmayan Dev: Bellek Duvarı (The Memory Wall)
İlk aşamada $15\text{ Trilyon Token}$ saf verimizi hazırladık. Şimdi $1\text{ Trilyon}$ ($10^{12}$) parametreli bir `Frontier Model` eğiteceğiz. Hemen ilk fiziksel duvara çarpıyoruz: **Tek bir GPU'nun belleği (`VRAM` / `HBM3e`) en fazla $80\text{ GB}$ ile $192\text{ GB}$ arasındadır; oysa $1\text{ Trilyon}$ parametreli bir modeli eğitmek için ne kadar bellek gerekir?**

Çoğu kişi *"Her parametre `BFloat16` formatında $2\text{ Byte}$ yer kaplar, öyleyse $1\text{T} \times 2\text{ Byte} = 2\text{ Terabyte}$ yeter"* sanır. **Yanlış!** Eğitim (`Training`) sırasında `AdamW Optimizer` her bir parametre için şunları bellekte tutmak zorundadır:
1. **`Model Weights` (`BF16`):** $2\text{ Byte}$
2. **`Gradients` (`BF16` / `FP32`):** $2 - 4\text{ Byte}$
3. **`Master Weights` (`FP32`):** Küçük gradyan güncellemelerinin kaybolmaması için $4\text{ Byte}$
4. **`Optimizer States` (`Adam First & Second Moments` — $m_t, v_t$ `FP32`):** $4 + 4 = 8\text{ Byte}$

Toplamda parametre başına **en az $16\text{ Byte}$** (aktivasyonlar hariç!) bellek gerekir:
$$10^{12}\text{ Parametre} \times 16\text{ Byte} = \mathbf{16.000\text{ GB (16 Terabyte) Saf VRAM!}}$$

Yani bu modeli tek bir ekran kartına koymak şöyle dursun, sadece ağırlıklarını ve `Optimizer` durumlarını tutmak için bile **en az 200 adet $80\text{ GB}$'lık veri merkezi GPU'sunun belleğini birleştirmek** zorundasın!

```python
def egitim_vram_hesabi(parametre_milyar, gpu_vram_gb=80):
    # Parametre basina: 2B (BF16 Weight) + 2B (BF16 Grad) + 12B (FP32 Master Weight + m + v) = 16 Byte
    toplam_gb = parametre_milyar * 16
    aktivasyon_payi_gb = parametre_milyar * 4  # Ornek aktivasyon + KV buffer payi
    genel_toplam_gb = toplam_gb + aktivasyon_payi_gb
    min_gpu = int((genel_toplam_gb + gpu_vram_gb - 1) // gpu_vram_gb)
    return {"agirlik_ve_opt_gb": toplam_gb, "toplam_vram_gb": genel_toplam_gb, "min_80gb_gpu_sayisi": min_gpu}

print("70B Model Eğitimi :", egitim_vram_hesabi(70))
print("1000B (1T) Eğitimi:", egitim_vram_hesabi(1000))
```
:::

::: anlat 2. 3D Parallelism: iş ve veri bölüşümü
Modeli binlerce GPU'ya bölerken rastgele bölemezsin; çünkü GPU'lar arası veri aktarım hızı (`Interconnect Bandwidth`), GPU'nun kendi içindeki hesaplama hızından çok daha yavaştır. Bu yüzden `Frontier Lab`'ler **`3D Parallelism`** (hatta `Context` ve `Expert` eklendiğinde `5D Parallelism`) adını verdikleri üç boyutlu bir orkestrasyon kullanır:

### 🏭 Benzetme: Dev Otomobil Fabrikası
30.000 işçinin çalıştığı bir fabrika düşün:

| Paralellik Boyutu | Fabrika Benzetmesi | Teknik Çalışma Mekaniği ve Donanım Bağı |
| :--- | :--- | :--- |
| **1. `Tensor Parallelism (TP)`** *(Katman İçi Bölme)* | Aynı motor bloğunun sol yarısını İşçi A'nın, sağ yarısını İşçi B'nin **aynı saniyede** monte etmesi. | Tek bir matris çarpımı ($Y = XW$) sütun/satır bazında $8$ GPU'ya bölünür. Her katmanda konuşmaları gerektiği için **aynı sunucu kasası (`Node`) içindeki ultra-hızlı `NVLink / Infinity Fabric` ($900\text{ GB/s}$)** üzerinde çalışır. |
| **2. `Pipeline Parallelism (PP)`** *(Katmanlar Arası Bölme)* | Montaj bandı: 1–10. katmanları 1. Kasa, 11–20. katmanları 2. Kasa, 21–30. katmanları 3. Kasanın yapması. | Model dikey olarak katman gruplarına (`Stages`) ayrılır. GPU'ların boş beklememesi (`Pipeline Bubble`) için veri küçük **`Micro-batch`** parçalarına bölünüp **`1F1B (One-Forward-One-Backward)`** takvimiyle akıtılır. |
| **3. `Data Parallelism (DP / ZeRO / FSDP)`** *(Veri Kopyası Bölme)* | Yan yana kurulmuş 100 özdeş montaj bandının her birinin farklı arabaları üretip vardiya sonunda tecrübelerini birleştirmesi. | Farklı GPU grupları farklı veri paketlerini (`Batch`) işler ve adım sonunda gradyanlarını **`All-Reduce` (`Reduce-Scatter` + `All-Gather`)** ile ortalar. **`ZeRO-3 / FSDP`** sayesinde `Optimizer` ve ağırlıklar da kopyalanmak yerine bu GPU'lar arasında paylaştırılır (`Sharding`). |

 *(Not: Eğer model bir `Mixture-of-Experts (MoE)` ise buna 4. boyut olarak uzmanları farklı kartlara dağıtan **`Expert Parallelism (EP)`**, context window $1\text{ Milyon Token}$ ise diziyi bölen **`Context / Ring Parallelism (CP)`** eklenir!)*
:::

::: anlat 3. FlashAttention: GPU'nun İçindeki Gizli Darboğazı Aşmak
Binlerce GPU'yu bağladık ama tek bir GPU'nun kendi içinde de devasa bir fiziksel darboğaz vardır:
- GPU'nun işlem çekirdeklerinin (`Tensor Cores`) hemen yanındaki ultra-hızlı önbellek (**`SRAM`**) sadece **$20 - 40\text{ MB}$** büyüklüğündedir ama saniyede **$19.000\text{ GB/s}$** hızla okunur.
- GPU'nun ana belleği (**`HBM / VRAM`**) ise **$80\text{ GB}$** büyüklüğündedir ama hızı "sadece" **$3.000\text{ GB/s}$**'dir.

Standart `Self-Attention` ($\text{Softmax}(QK^\top / \sqrt{d})V$) hesaplanırken, bağlam uzunluğu $L = 32.768$ olduğunda $L \times L$ boyutunda ($32.768 \times 32.768 \approx \mathbf{1\text{ Milyar}}$ elemanlı!) dev bir `Attention Matrix` oluşur. Klasik algoritmalar bu dev matrisi sürekli yavaş olan `HBM`'e yazıp geri okuduğu için GPU çekirdekleri zamanın %80'inde **veri bekleyerek boşta yatar (`Memory-Bound`)!**

### ⚡ Tri Dao ve `FlashAttention` Yaklaşımı
**`FlashAttention`**, dev $L \times L$ matrisini `HBM` belleğe **asla yazmaz!**
- Matrisi küçük karelere (**`Tiling`**) böler ve doğrudan GPU'nun ultra-hızlı `SRAM` önbelleğine çeker.
- **`Online Softmax`** matematiksel hilesini kullanarak, tüm satırı görmeden parça parça `Softmax` istatistiklerini ($m$: maksimum, $\ell$: üstel toplam) günceller ve tek seferde sonucu çıkarır.
- Sonuç: Sıfır matematiksel yaklaşıklama (`Exact Attention`) ile **bellek kullanımı $O(L^2)$'den $O(L)$'ye düşer ve eğitim 3–5 kat hızlanır!** Bugün 128K veya 1M `Context Window` görebiliyorsak bunu doğrudan `FlashAttention`'a borçluyuz.
:::

::: anlat 4. Maximal Update Parametrization (μP) ve ölçek aktarımı
Şimdi bir `Frontier Lab` yöneticisinin en büyük kabusunu düşün:
$1\text{ Trilyon}$ parametreli modelin eğitimi **3 ay** sürecek ve **$100\text{ Milyon Dolar}$** elektrik/GPU parası yakacak. Ama eğitime başlamadan önce **`Learning Rate` ($\eta$)**, **`Initialization Scale`** ve katman çarpanları gibi `Hyperparameter` değerlerini seçmen gerekiyor.

- $1\text{ Trilyon}$ parametreli modelde 10 farklı `Learning Rate` deneme şansın **yoktur** (her deneme 100 milyon dolar!).
- Mecburen önce küçük bir $100\text{ Milyon}$ parametreli modelde en iyi `Learning Rate`'i bulursun.
- **Klasik Sorun (`Standard Parametrization - SP`):** Küçük modelde harika çalışan $\eta = 10^{-3}$, modelin genişliğini (`Width` $d_{\text{model}}$) $1.024$'ten $16.384$'e çıkardığın anda aktivasyonların patlamasına (`Activation Explosion`) ve eğitimin çökmesine yol açar!

### 🎯 Çözüm: `μP` (`Maximal Update Parametrization` — Yang et al.)
Microsoft ve OpenAI araştırmacılarının geliştirdiği **`μP`**, matris genişliği ($d$) büyüdükçe ağırlık başlatma varyansını ve katman bazlı `Learning Rate` değerlerini $1/d$ veya $1/\sqrt{d}$ ile öyle bir ölçeklendirir ki:
> **Modelin genişliği $256$'dan $32.768$'e (binlerce kat!) büyütülse bile, en optimal `Learning Rate` noktası hiç kaymaz (`Zero-Shot Hyperparameter Transfer`)!**

```python
# μP (Maximal Update Parametrization) ile katman genişliği büyüdükçe Learning Rate ölçeklemesi
def mup_learning_rate(base_lr, base_width, target_width):
    # Gizli katman (Hidden Linear Layer) için μP kuralı: lr_target = base_lr * (base_width / target_width)
    carpan = base_width / target_width
    return {"target_width": target_width, "standart_lr": base_lr, "mup_gizli_katman_lr": round(base_lr * carpan, 6)}

print("Proxy Model (d=512)   :", mup_learning_rate(0.001, 512, 512))
print("Orta Model (d=4096)   :", mup_learning_rate(0.001, 512, 4096))
print("Frontier Model (d=16384):", mup_learning_rate(0.001, 512, 16384))
```
Böylece mühendisler ucuz ve küçük `Proxy Model` üzerinde binlerce deney yapıp en ideal hiperparametre noktasını bulur, sonra aynı noktayı $\mu\text{P}$ dönüşümüyle tek atışta dev `Frontier Model`'e aktarır!
:::

::: anlat 5. Donanım Arızaları, Loss Spikes ve "Pre-training" Nöbeti
30.000 GPU aynı anda 90 gün boyunca tam yükte çalıştığında istatistiksel olarak **her birkaç saatte bir** bir GPU yanar, bir fiber optik kablo kopar veya kozmik radyasyon yüzünden bir bellek biti döner (`Silent Data Corruption`).

Bu yüzden bir `Frontier Model` eğitmek sadece algoritma değil, bir **uzay roketi fırlatma operasyonudur**:
1. **Otomatik `Checkpointing` ve Yedek Düğümler (`Hot Spares`):** Sistem her 15 dakikada bir $16\text{ TB}$'lık durumu paralel dosya sistemine kaydeder; bozulan GPU 60 saniye içinde kümeden çıkarılıp yedek GPU ile eğitim kaldığı yerden sürdürülür.
2. **`Loss Spikes` (Kayıp Sıçramaları) ve `Gradient Clipping`:** Bazen eğitim sırasında `Loss` aniden $1.8$'den $9.5$'e fırlar. Bunun sebebi genellikle bozuk bir veri paketi veya `Attention Logit` değerlerinin aşırı büyümesidir. Modern mimariler bunu önlemek için **`QK-Norm`** (`Query` ve `Key` vektörlerini çarpmadan önce normalize etme) ve **`Z-Loss`** kullanarak eğitimi kaya gibi sabit tutar.
:::

::: tahmin 3D Parallelism GPU Kümesi Hesabı
Bir `Frontier Lab`, $1\text{ Trilyon}$ parametreli modelini eğitirken şu `3D Parallelism` topolojisini kuruyor:
- Her sunucu içinde **`Tensor Parallelism` ($TP = 8$)**,
- Katmanları bölmek için **`Pipeline Parallelism` ($PP = 16$)**,
- Veri kopyalarını paralel işlemek için **`Data Parallelism` ($DP = 64$)**.
Bu eğitimde aynı anda çalışan toplam GPU sayısı (`World Size`) kaçtır?

```python
tp = 8
pp = 16
dp = 64
toplam_gpu = tp * pp * dp
print(f"Tek Model Kopyasi (TPxPP): {tp * pp} GPU | Toplam Kume: {toplam_gpu} GPU")
```

???

```cikti
Tek Model Kopyasi (TPxPP): 128 GPU | Toplam Kume: 8192 GPU
```
Modelin tek bir tam kopyası $TP \times PP = 8 \times 16 = 128$ GPU'ya yayılır. Bu $128$ GPU'luk grup $DP = 64$ kez çoğaltılarak farklı veri paketlerini paralel işlediği için toplam küme boyutu $8 \times 16 \times 64 = 8.192$ GPU olur.
:::

::: gorev 1 · 3D Paralellikte Rank Haritası, Pipeline Aşamaları ve GPU Başına Parametre
`paralel_yerlesim(gpu_sayisi, tp, pp, dp, katman_sayisi, parametre_milyar)` işlevini yaz. Megatron tarzı yerleşimde rank'lar önce tensör paralel (en hızlı değişen), sonra veri paralel, en son pipeline boyutunda sıralanır:
$$\text{rank} = i_{pp}\cdot(dp\cdot tp) + i_{dp}\cdot tp + i_{tp}$$

**Kurallar:**
1. `gpu_sayisi`, `tp`, `pp`, `dp`, `katman_sayisi` pozitif tam sayı (`bool` değil), `parametre_milyar` pozitif sonlu sayı olmalı; $tp \cdot pp \cdot dp$ GPU sayısına eşit ve katman sayısı `pp`'ye tam bölünür olmalı. Değilse `ValueError`.
2. Çıktı:
   - `"rank_haritasi"`: her rank için `[i_pp, i_dp, i_tp]` (rank sırasıyla);
   - `"asama_katmanlari"`: her pipeline aşamasının `[ilk, son_haric]` katman aralığı;
   - `"tp_gruplari"`: aynı `(i_pp, i_dp)` çiftini paylaşan rank listeleri (önce $i_{pp}$, sonra $i_{dp}$ sırasıyla);
   - `"dp_gruplari"`: aynı `(i_pp, i_tp)` çiftini paylaşan rank listeleri (önce $i_{pp}$, sonra $i_{tp}$);
   - `"gpu_basi_parametre_milyar"`: $P / (tp\cdot pp)$ (`round(·, 6)`). Veri paralelliği parametreyi bölmez, kopyalar.

```starter
def paralel_yerlesim(gpu_sayisi, tp, pp, dp, katman_sayisi, parametre_milyar):
    # KUSURLU BAŞLANGIÇ: parametreyi bütün GPU'lara bölüyor (DP kopyalarını unutuyor), haritayı kurmuyor
    return {"rank_haritasi": [], "asama_katmanlari": [], "tp_gruplari": [], "dp_gruplari": [],
            "gpu_basi_parametre_milyar": parametre_milyar / gpu_sayisi}

print(paralel_yerlesim(8, 2, 2, 2, 4, 7.0))
```

```test
fn = need("paralel_yerlesim")
r = fn(8, 2, 2, 2, 4, 7.0)
eq(r["rank_haritasi"][5], [1, 0, 1], "rank 5 = pp 1, dp 0, tp 1")
eq(r["rank_haritasi"][2], [0, 1, 0], "rank 2 = pp 0, dp 1, tp 0")
eq(r["asama_katmanlari"], [[0, 2], [2, 4]], "4 katman 2 aşamaya")
eq(r["tp_gruplari"], [[0, 1], [2, 3], [4, 5], [6, 7]], "TP grupları ardışık rank'lar")
eq(r["dp_gruplari"], [[0, 2], [1, 3], [4, 6], [5, 7]], "DP grupları tp adımıyla")
eq(r["gpu_basi_parametre_milyar"], 1.75, "7B / (2·2)")
r2 = fn(12, 4, 3, 1, 30, 70.0)
eq(r2["asama_katmanlari"], [[0, 10], [10, 20], [20, 30]], "30 katman 3 aşamaya")
eq(r2["dp_gruplari"], [[i] for i in range(12)], "dp=1 iken her DP grubu tek rank")
eq(r2["gpu_basi_parametre_milyar"], 5.833333, "70 / 12")
eq(r2["rank_haritasi"][7], [1, 0, 3], "rank 7 = pp 1, tp 3")
eq(r2["rank_haritasi"][4], [1, 0, 0], "rank 4 = pp 1, dp 0, tp 0 (dp*tp=4 != dp+tp=5)")
raises(ValueError, fn, 8, 2, 2, 3, 4, 7.0)
raises(ValueError, fn, 8, 2, 4, 1, 6, 7.0)
raises(ValueError, fn, 8, 2, 2, 2, 4, 0.0)
raises(ValueError, fn, 8, True, 2, 4, 4, 7.0)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile('import math\n\ndef paralel_yerlesim(gpu_sayisi, tp, pp, dp, katman_sayisi, parametre_milyar):\n    for v in (gpu_sayisi, tp, pp, dp, katman_sayisi):\n        if isinstance(v, bool) or not isinstance(v, int) or v < 1:\n            raise ValueError(\'sayılar pozitif tam sayı olmalı\')\n    if isinstance(parametre_milyar, bool) or not isinstance(parametre_milyar, (int, float)) or (not math.isfinite(parametre_milyar)) or (parametre_milyar <= 0):\n        raise ValueError(\'parametre pozitif sayı olmalı\')\n    if tp * pp * dp != gpu_sayisi:\n        raise ValueError(\'tp·pp·dp GPU sayısına eşit olmalı\')\n    if katman_sayisi % pp:\n        raise ValueError("katman sayısı pp\'ye bölünmeli")\n    harita = []\n    for r in range(gpu_sayisi):\n        harita.append([r // (dp * tp), r // tp % dp, r % tp])\n    k = katman_sayisi // pp\n    asama = [[i * k, (i + 1) * k] for i in range(pp)]\n    tpg = [[p * dp * tp + d * tp + t for t in range(tp)] for p in range(pp) for d in range(dp)]\n    dpg = [[p * dp * tp + d * tp + t for d in range(dp)] for p in range(pp) for t in range(tp)]\n    return {\'rank_haritasi\': harita, \'asama_katmanlari\': asama, \'tp_gruplari\': tpg, \'dp_gruplari\': dpg, \'gpu_basi_parametre_milyar\': round(parametre_milyar / (tp * pp), 6)}', 'referans', 'exec'), _REF)
_t, _g = _ff(paralel_yerlesim, _REF['paralel_yerlesim'], (8, 2, 2, 2, 4, 7.0), tohum=2635, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (paralel_yerlesim): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def paralel_yerlesim(gpu_sayisi, tp, pp, dp, katman_sayisi, parametre_milyar):
    for v in (gpu_sayisi, tp, pp, dp, katman_sayisi):
        if isinstance(v, bool) or not isinstance(v, int) or v < 1:
            raise ValueError("sayılar pozitif tam sayı olmalı")
    if isinstance(parametre_milyar, bool) or not isinstance(parametre_milyar, (int, float)) or not math.isfinite(parametre_milyar) or parametre_milyar <= 0:
        raise ValueError("parametre pozitif sayı olmalı")
    if tp * pp * dp != gpu_sayisi:
        raise ValueError("tp·pp·dp GPU sayısına eşit olmalı")
    if katman_sayisi % pp:
        raise ValueError("katman sayısı pp'ye bölünmeli")
    harita = []
    for r in range(gpu_sayisi):
        harita.append([r // (dp * tp), (r // tp) % dp, r % tp])
    k = katman_sayisi // pp
    asama = [[i * k, (i + 1) * k] for i in range(pp)]
    tpg = [[p * dp * tp + d * tp + t for t in range(tp)] for p in range(pp) for d in range(dp)]
    dpg = [[p * dp * tp + d * tp + t for d in range(dp)] for p in range(pp) for t in range(tp)]
    return {"rank_haritasi": harita, "asama_katmanlari": asama, "tp_gruplari": tpg, "dp_gruplari": dpg,
            "gpu_basi_parametre_milyar": round(parametre_milyar / (tp * pp), 6)}
```

```hint
Rank'tan geri dönüş: `i_tp = r % tp`, `i_dp = (r // tp) % dp`, `i_pp = r // (dp·tp)`.
```
:::

::: gorev 2 · Tensör Paralel Matris Çarpımı: Sütun ve Satır Bölme
`tp_matmul(X, W, tp, mod)` işlevini yaz. $Y = XW$; $X$ boyutu $n \times d_{in}$, $W$ boyutu $d_{in} \times d_{out}$ (iç içe listeler).

**Kurallar:**
1. `X` ve `W` dikdörtgen, boş olmayan sonlu sayı matrisleri ve iç boyutları uyumlu olmalı; `tp` pozitif tam sayı, `mod` `"sutun"` ya da `"satir"` olmalı. Değilse `ValueError`.
2. `"sutun"` (column parallel): $d_{out}$ `tp`'ye bölünmeli; $W$ sütun bloklarına ayrılır, her rank $Y_k = X W_{:,k}$ hesaplar; birleşim **yan yana ekleme**dir (`"all-gather"`).
3. `"satir"` (row parallel): $d_{in}$ `tp`'ye bölünmeli; $W$ satır bloklarına, $X$ aynı sütun bloklarına ayrılır, her rank kısmi $Y_k = X_{:,k} W_{k,:}$ hesaplar; birleşim **toplama**dır (`"all-reduce"`).
4. Bölünemiyorsa `ValueError`. Çıktı: `"parca_ciktilari"` (her rank'ın matrisi), `"birlesik"`, `"iletisim"`; sayılar `round(·, 6)`.

```starter
def tp_matmul(X, W, tp, mod):
    # KUSURLU BAŞLANGIÇ: satır bölmede kısmi sonuçları toplamak yerine yan yana ekliyor
    n, k = len(X), len(W[0])
    Y = [[sum(X[i][t] * W[t][j] for t in range(len(W))) for j in range(k)] for i in range(n)]
    return {"parca_ciktilari": [Y], "birlesik": Y, "iletisim": "all-gather"}

print(tp_matmul([[1.0, 2.0], [3.0, 4.0]], [[1.0, 0.0], [0.0, 1.0]], 2, "satir"))
```

```test
fn = need("tp_matmul")
X = [[1.0, 2.0], [3.0, 4.0]]
W = [[1.0, 2.0], [3.0, 4.0]]
r = fn(X, W, 2, "sutun")
eq(r["parca_ciktilari"], [[[7.0], [15.0]], [[10.0], [22.0]]], "her rank bir sütun")
eq(r["birlesik"], [[7.0, 10.0], [15.0, 22.0]], "yan yana ekleme = XW")
eq(r["iletisim"], "all-gather", "sütun bölme all-gather ister")
r2 = fn(X, W, 2, "satir")
eq(r2["parca_ciktilari"], [[[1.0, 2.0], [3.0, 6.0]], [[6.0, 8.0], [12.0, 16.0]]], "kısmi toplamlar")
eq(r2["birlesik"], [[7.0, 10.0], [15.0, 22.0]], "toplam = XW")
eq(r2["iletisim"], "all-reduce", "satır bölme all-reduce ister")
r3 = fn([[1.0, 1.0, 1.0, 1.0]], [[1.0], [2.0], [3.0], [4.0]], 4, "satir")
eq(r3["birlesik"], [[10.0]], "4 rank'ın kısmi toplamı")
eq(fn(X, W, 1, "sutun")["birlesik"], [[7.0, 10.0], [15.0, 22.0]], "tp=1 tek parça")
raises(ValueError, fn, X, [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], 2, "sutun")
raises(ValueError, fn, [[1.0, 2.0, 3.0]], [[1.0], [2.0], [3.0]], 2, "satir")
raises(ValueError, fn, X, W, 2, "kosegen")
raises(ValueError, fn, X, [[1.0, 2.0]], 1, "sutun")
raises(ValueError, fn, [1.0], W, 1, "sutun")
raises(ValueError, fn, [[]], W, 1, "sutun")
raises(ValueError, fn, [[1.0]], [[]], 1, "sutun")
eq(fn([[1/3, 0.0]], [[1.0, 0.0], [0.0, 1.0]], 2, "satir")["birlesik"], [[0.333333, 0.0]], "6 basamak yuvarlama")
eq(fn([[1.0] * 6], [[1.0]] * 6, 3, "satir")["birlesik"], [[6.0]], "3 parça satır bölme dilimleri")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile('import math\n\ndef _matris(M):\n    if not isinstance(M, list) or not M or (not isinstance(M[0], list)) or (not M[0]):\n        raise ValueError(\'boş olmayan 2B matris gerekli\')\n    for s in M:\n        if not isinstance(s, list) or len(s) != len(M[0]):\n            raise ValueError(\'dikdörtgen matris gerekli\')\n        for v in s:\n            if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):\n                raise ValueError(\'sonlu sayı gerekli\')\n    return (len(M), len(M[0]))\n\ndef _carp(A, B):\n    return [[sum((A[i][t] * B[t][j] for t in range(len(B)))) for j in range(len(B[0]))] for i in range(len(A))]\n\ndef tp_matmul(X, W, tp, mod):\n    n, d_in = _matris(X)\n    d_in2, d_out = _matris(W)\n    if d_in != d_in2:\n        raise ValueError(\'iç boyutlar uyuşmuyor\')\n    if isinstance(tp, bool) or not isinstance(tp, int) or tp < 1 or (mod not in (\'sutun\', \'satir\')):\n        raise ValueError("tp pozitif tam sayı, mod \'sutun\' ya da \'satir\' olmalı")\n    yuv = lambda M: [[round(v, 6) for v in s] for s in M]\n    if mod == \'sutun\':\n        if d_out % tp:\n            raise ValueError("d_out tp\'ye bölünmeli")\n        b = d_out // tp\n        parcalar = [_carp(X, [s[k * b:(k + 1) * b] for s in W]) for k in range(tp)]\n        birlesik = [sum((p[i] for p in parcalar), []) for i in range(n)]\n        return {\'parca_ciktilari\': [yuv(p) for p in parcalar], \'birlesik\': yuv(birlesik), \'iletisim\': \'all-gather\'}\n    if d_in % tp:\n        raise ValueError("d_in tp\'ye bölünmeli")\n    b = d_in // tp\n    parcalar = [_carp([s[k * b:(k + 1) * b] for s in X], W[k * b:(k + 1) * b]) for k in range(tp)]\n    birlesik = [[sum((p[i][j] for p in parcalar)) for j in range(d_out)] for i in range(n)]\n    return {\'parca_ciktilari\': [yuv(p) for p in parcalar], \'birlesik\': yuv(birlesik), \'iletisim\': \'all-reduce\'}', 'referans', 'exec'), _REF)
_t, _g = _ff(tp_matmul, _REF['tp_matmul'], ([[1.0, 2.0], [3.0, 4.0]], [[1.0, 0.0], [0.0, 1.0]], 2, 'satir'), tohum=1908, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (tp_matmul): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def _matris(M):
    if not isinstance(M, list) or not M or not isinstance(M[0], list) or not M[0]:
        raise ValueError("boş olmayan 2B matris gerekli")
    for s in M:
        if not isinstance(s, list) or len(s) != len(M[0]):
            raise ValueError("dikdörtgen matris gerekli")
        for v in s:
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                raise ValueError("sonlu sayı gerekli")
    return len(M), len(M[0])

def _carp(A, B):
    return [[sum(A[i][t] * B[t][j] for t in range(len(B))) for j in range(len(B[0]))] for i in range(len(A))]

def tp_matmul(X, W, tp, mod):
    n, d_in = _matris(X)
    d_in2, d_out = _matris(W)
    if d_in != d_in2:
        raise ValueError("iç boyutlar uyuşmuyor")
    if isinstance(tp, bool) or not isinstance(tp, int) or tp < 1 or mod not in ("sutun", "satir"):
        raise ValueError("tp pozitif tam sayı, mod 'sutun' ya da 'satir' olmalı")
    yuv = lambda M: [[round(v, 6) for v in s] for s in M]
    if mod == "sutun":
        if d_out % tp:
            raise ValueError("d_out tp'ye bölünmeli")
        b = d_out // tp
        parcalar = [_carp(X, [s[k * b:(k + 1) * b] for s in W]) for k in range(tp)]
        birlesik = [sum((p[i] for p in parcalar), []) for i in range(n)]
        return {"parca_ciktilari": [yuv(p) for p in parcalar], "birlesik": yuv(birlesik), "iletisim": "all-gather"}
    if d_in % tp:
        raise ValueError("d_in tp'ye bölünmeli")
    b = d_in // tp
    parcalar = [_carp([s[k * b:(k + 1) * b] for s in X], W[k * b:(k + 1) * b]) for k in range(tp)]
    birlesik = [[sum(p[i][j] for p in parcalar) for j in range(d_out)] for i in range(n)]
    return {"parca_ciktilari": [yuv(p) for p in parcalar], "birlesik": yuv(birlesik), "iletisim": "all-reduce"}
```

```hint
Sütun bölmede her parça çıktının bir dilimidir (birleştir), satır bölmede her parça çıktının tamamının bir kısmıdır (topla).
```
:::

::: anlat Gerçek deney: Gerçek bir MLP'yi dört gloo sürecine bölmek
Final tensör paralelliği gerçek ağırlıklar ve gerçek süreçler arası iletişimle gösterir (tek makine, GPU gerekmez):

- SmolLM2'nin 4. katman MLP'si (576 → 1536 → 576, SwiGLU) Megatron tarzı 4 parçaya bölünür. `gate_proj` ve `up_proj` **sütun paralel** bölünür: her parça ara boyutun 384'ünü tutar ve kendi kısmını iletişimsiz hesaplar. `down_proj` ise **satır paralel** bölünür: her parça çıktının tamamına kısmi bir katkı üretir.
- Dört kısmi çıktı dört ayrı Python sürecine verilir ve gerçek `torch.distributed` (gloo) `all_reduce` ile toplanır. Sonuç, modelin kendi `mlp` çıktısıyla karşılaştırılır. Bir MLP için tek bir all-reduce yeter: Megatron'un tasarımı budur.
- Senin `tp_matmul` işlevin gerçek bir ağırlık bloğunda her iki kipte torch ile karşılaştırılır.
- Senin `paralel_yerlesim` işlevin SmolLM2'nin gerçek katman (30) ve parametre sayısıyla 8 GPU'luk bir yerleşim kurar (tp 2 × pp 2 × dp 2); rank haritası formülle denetlenir.

**Ek konu — FlashAttention ve pipeline bubble:** **Dikkat belleği:** aynı rastgele Q/K/V ile naif dikkat ($T \times T$ skor matrisi bellekte) ve PyTorch'un `scaled_dot_product_attention`'ı (GPU'da FlashAttention ya da bellek verimli çekirdek) üç uzunlukta çalıştırılır; ek bellek, süre ve çıktı farkı ölçülür. Çıktı aynıdır, ama SDPA skor matrisini hiç oluşturmaz. **Pipeline:** SmolLM2'nin 30 katmanı 4 aşamaya bölünür, her aşamanın gerçek süresi ölçülür ve GPipe zamanlaması bu sürelerle simüle edilir. Mikro-batch sayısı $m$ arttıkça boşta geçen zaman oranı (bubble) $(p-1)/(m+p-1)$'e yakın biçimde düşer; aşamalar eşit sürmediğinde formülden biraz daha kötüdür.

**Güvenlik yönü — dağıtık eğitimin buluşma noktası kimlik doğrulamasızdır:** `torchrun` süreçleri bir **TCPStore** üzerinden buluşur (MASTER_ADDR:MASTER_PORT). Deney 127.0.0.1'de bir TCPStore açar, eğitim ayarı ve bir kanarya anahtarı yazar. Ardından "davetsiz" bir istemci hiçbir parola ya da sertifika vermeden bağlanır, kanaryayı okur ve eğitim ayarını değiştirir; asıl süreç değişmiş değeri görür. PyTorch belgeleri `torch.distributed`'ın yalnız güvenilir ağlarda kullanılmasını söyler: gloo/NCCL trafiği şifresiz ve kimlik doğrulamasızdır. Eğitim kümeleri ayrı bir ağ bölümüne alınmalı ve buluşma portu dışarı açılmamalıdır.

Kabul: iki işlevin farksal taramayı geçmesi; dört sürecin aynı sonucu alması ve bunun modelin MLP çıktısından göreli `1e-5` altında farklı olması; öğrencinin matmul'ünün gerçek blokta torch ile aynı olması; rank haritasının doğru olması. Ayrıca SDPA naif dikkatle aynı çıktıyı vermeli ve GPU'da en uzun dizide yarıdan az ek bellek kullanmalı; bubble mikro-batch sayısıyla azalmalıdır. Ayrıca davetsiz istemci kanaryayı okuyabilmeli ve eğitim ayarını değiştirebilmelidir.

**Kanıt dosyasını oku:** `tp_goreli_fark`, `yerlesim`, `gpu_basi_parametre_milyar`, `katman_basi_allreduce_bayt_bf16`. Soru 1: `gate_proj`'u da satır paralel bölseydin kaç iletişim gerekirdi? Soru 2: Tensör paralellik neden düğüm içinde (NVLink) tutulur? Soru 3: Veri paralelliği GPU başına parametreyi neden azaltmaz?
:::

::: gorev Gerçek deney · SmolLM2 MLP'sinin gloo all-reduce ile tensör paralel bölünmesi ve 3D yerleşim
Önceki görevlerdeki `paralel_yerlesim`, `tp_matmul` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 240
```
```starter
import ai_lab
def paralel_yerlesim(gpu_sayisi, tp, pp, dp, katman_sayisi, parametre_milyar):
    return {'rank_haritasi': [], 'asama_katmanlari': [], 'tp_gruplari': [], 'dp_gruplari': [], 'gpu_basi_parametre_milyar': parametre_milyar / gpu_sayisi}

def tp_matmul(X, W, tp, mod):
    n, k = (len(X), len(W[0]))
    Y = [[sum((X[i][t] * W[t][j] for t in range(len(W)))) for j in range(k)] for i in range(n)]
    return {'parca_ciktilari': [Y], 'birlesik': Y, 'iletisim': 'all-gather'}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_33 as D
    D.goster(paralel_yerlesim, tp_matmul)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_gloo', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
paralel_yerlesim = need("paralel_yerlesim")
tp_matmul = need("tp_matmul")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile('import math\n\ndef paralel_yerlesim(gpu_sayisi, tp, pp, dp, katman_sayisi, parametre_milyar):\n    for v in (gpu_sayisi, tp, pp, dp, katman_sayisi):\n        if isinstance(v, bool) or not isinstance(v, int) or v < 1:\n            raise ValueError(\'sayılar pozitif tam sayı olmalı\')\n    if isinstance(parametre_milyar, bool) or not isinstance(parametre_milyar, (int, float)) or (not math.isfinite(parametre_milyar)) or (parametre_milyar <= 0):\n        raise ValueError(\'parametre pozitif sayı olmalı\')\n    if tp * pp * dp != gpu_sayisi:\n        raise ValueError(\'tp·pp·dp GPU sayısına eşit olmalı\')\n    if katman_sayisi % pp:\n        raise ValueError("katman sayısı pp\'ye bölünmeli")\n    harita = []\n    for r in range(gpu_sayisi):\n        harita.append([r // (dp * tp), r // tp % dp, r % tp])\n    k = katman_sayisi // pp\n    asama = [[i * k, (i + 1) * k] for i in range(pp)]\n    tpg = [[p * dp * tp + d * tp + t for t in range(tp)] for p in range(pp) for d in range(dp)]\n    dpg = [[p * dp * tp + d * tp + t for d in range(dp)] for p in range(pp) for t in range(tp)]\n    return {\'rank_haritasi\': harita, \'asama_katmanlari\': asama, \'tp_gruplari\': tpg, \'dp_gruplari\': dpg, \'gpu_basi_parametre_milyar\': round(parametre_milyar / (tp * pp), 6)}\n\nimport math\n\ndef _matris(M):\n    if not isinstance(M, list) or not M or (not isinstance(M[0], list)) or (not M[0]):\n        raise ValueError(\'boş olmayan 2B matris gerekli\')\n    for s in M:\n        if not isinstance(s, list) or len(s) != len(M[0]):\n            raise ValueError(\'dikdörtgen matris gerekli\')\n        for v in s:\n            if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):\n                raise ValueError(\'sonlu sayı gerekli\')\n    return (len(M), len(M[0]))\n\ndef _carp(A, B):\n    return [[sum((A[i][t] * B[t][j] for t in range(len(B)))) for j in range(len(B[0]))] for i in range(len(A))]\n\ndef tp_matmul(X, W, tp, mod):\n    n, d_in = _matris(X)\n    d_in2, d_out = _matris(W)\n    if d_in != d_in2:\n        raise ValueError(\'iç boyutlar uyuşmuyor\')\n    if isinstance(tp, bool) or not isinstance(tp, int) or tp < 1 or (mod not in (\'sutun\', \'satir\')):\n        raise ValueError("tp pozitif tam sayı, mod \'sutun\' ya da \'satir\' olmalı")\n    yuv = lambda M: [[round(v, 6) for v in s] for s in M]\n    if mod == \'sutun\':\n        if d_out % tp:\n            raise ValueError("d_out tp\'ye bölünmeli")\n        b = d_out // tp\n        parcalar = [_carp(X, [s[k * b:(k + 1) * b] for s in W]) for k in range(tp)]\n        birlesik = [sum((p[i] for p in parcalar), []) for i in range(n)]\n        return {\'parca_ciktilari\': [yuv(p) for p in parcalar], \'birlesik\': yuv(birlesik), \'iletisim\': \'all-gather\'}\n    if d_in % tp:\n        raise ValueError("d_in tp\'ye bölünmeli")\n    b = d_in // tp\n    parcalar = [_carp([s[k * b:(k + 1) * b] for s in X], W[k * b:(k + 1) * b]) for k in range(tp)]\n    birlesik = [[sum((p[i][j] for p in parcalar)) for j in range(d_out)] for i in range(n)]\n    return {\'parca_ciktilari\': [yuv(p) for p in parcalar], \'birlesik\': yuv(birlesik), \'iletisim\': \'all-reduce\'}', 'referans', 'exec'), _REF)
_t, _g = _ff(paralel_yerlesim, _REF['paralel_yerlesim'], (8, 2, 2, 2, 4, 7.0), tohum=2635, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (paralel_yerlesim): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(tp_matmul, _REF['tp_matmul'], ([[1.0, 2.0], [3.0, 4.0]], [[1.0, 0.0], [0.0, 1.0]], 2, 'satir'), tohum=1908, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (tp_matmul): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
def _red33(f, *a):
    try: f(*a); return False
    except ValueError: return True
_py12 = paralel_yerlesim(12, 4, 3, 1, 30, 70.0)
kontrol(_py12["rank_haritasi"][4] == [1, 0, 0] and _py12["gpu_basi_parametre_milyar"] == 5.833333 and paralel_yerlesim(1, 1, 1, 1, 1, 1.0)["rank_haritasi"] == [[0, 0, 0]], "paralel_yerlesim çarpım, yuvarlama ve 1-GPU sınırı")
kontrol(_red33(paralel_yerlesim, 8, True, 2, 4, 4, 7.0) and _red33(paralel_yerlesim, 9, 2, 1, 3, 2, 7.0), "paralel_yerlesim bool ve tp*pp*dp kontrolü")
_sut = tp_matmul([[1.0, 2.0]], [[1/3, 1.0, 2.0, 3.0, 4.0, 5.0], [0.0, 1.0, 1.0, 1.0, 1.0, 1.0]], 3, "sutun")
kontrol(_sut["iletisim"] == "all-gather" and _sut["birlesik"] == [[0.333333, 3.0, 4.0, 5.0, 6.0, 7.0]] and tp_matmul([[1.0] * 6], [[1.0]] * 6, 3, "satir")["birlesik"] == [[6.0]], "tp_matmul sütun/satır dilim ve 6 basamak yuvarlama")
kontrol(_red33(tp_matmul, [1.0], [[1.0]], 1, "sutun") and _red33(tp_matmul, [[]], [[1.0]], 1, "sutun") and _red33(tp_matmul, [[1.0]], [[]], 1, "sutun") and _red33(tp_matmul, [[1.0, 2.0]], [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], 2, "sutun"), "tp_matmul bozuk matris ve bölünemeyen d_out reddi")
if not all(checks): stop()
from sandbox import ai_gercek_ai_temel_33 as D
try: r = D.deney(paralel_yerlesim, tp_matmul)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['tp_ayni'], 'dört gloo sürecinin all-reduce sonucu modelin MLP çıktısıyla aynı')
kontrol(r['ogrenci_ayni'], 'sütun ve satır bölmeli matmul gerçek ağırlık bloğunda torch ile aynı')
kontrol(r['harita_dogru'], "SmolLM2 için 8 GPU'luk rank haritası doğru")
kontrol(r['flash_ayni_ve_hafif'], 'SDPA naif dikkatle aynı çıktıyı skor matrisini bellekte tutmadan verdi')
kontrol(r['bubble_mikrobatchla_azaliyor'], 'ölçülen aşama süreleriyle pipeline bubble mikro-batch sayısıyla azaldı')
kontrol(r['tcpstore_dogrulamasiz'], "kimlik doğrulaması olmayan TCPStore'da davetsiz istemci kanaryayı okudu ve ayarı değiştirdi")
ai_lab.kanit_yaz("ai-temel-33-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-temel-33", "deney": r})
```
```solution
import ai_lab
import math

def paralel_yerlesim(gpu_sayisi, tp, pp, dp, katman_sayisi, parametre_milyar):
    for v in (gpu_sayisi, tp, pp, dp, katman_sayisi):
        if isinstance(v, bool) or not isinstance(v, int) or v < 1:
            raise ValueError('sayılar pozitif tam sayı olmalı')
    if isinstance(parametre_milyar, bool) or not isinstance(parametre_milyar, (int, float)) or (not math.isfinite(parametre_milyar)) or (parametre_milyar <= 0):
        raise ValueError('parametre pozitif sayı olmalı')
    if tp * pp * dp != gpu_sayisi:
        raise ValueError('tp·pp·dp GPU sayısına eşit olmalı')
    if katman_sayisi % pp:
        raise ValueError("katman sayısı pp'ye bölünmeli")
    harita = []
    for r in range(gpu_sayisi):
        harita.append([r // (dp * tp), r // tp % dp, r % tp])
    k = katman_sayisi // pp
    asama = [[i * k, (i + 1) * k] for i in range(pp)]
    tpg = [[p * dp * tp + d * tp + t for t in range(tp)] for p in range(pp) for d in range(dp)]
    dpg = [[p * dp * tp + d * tp + t for d in range(dp)] for p in range(pp) for t in range(tp)]
    return {'rank_haritasi': harita, 'asama_katmanlari': asama, 'tp_gruplari': tpg, 'dp_gruplari': dpg, 'gpu_basi_parametre_milyar': round(parametre_milyar / (tp * pp), 6)}

def _matris(M):
    if not isinstance(M, list) or not M or (not isinstance(M[0], list)) or (not M[0]):
        raise ValueError('boş olmayan 2B matris gerekli')
    for s in M:
        if not isinstance(s, list) or len(s) != len(M[0]):
            raise ValueError('dikdörtgen matris gerekli')
        for v in s:
            if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):
                raise ValueError('sonlu sayı gerekli')
    return (len(M), len(M[0]))

def _carp(A, B):
    return [[sum((A[i][t] * B[t][j] for t in range(len(B)))) for j in range(len(B[0]))] for i in range(len(A))]

def tp_matmul(X, W, tp, mod):
    n, d_in = _matris(X)
    d_in2, d_out = _matris(W)
    if d_in != d_in2:
        raise ValueError('iç boyutlar uyuşmuyor')
    if isinstance(tp, bool) or not isinstance(tp, int) or tp < 1 or (mod not in ('sutun', 'satir')):
        raise ValueError("tp pozitif tam sayı, mod 'sutun' ya da 'satir' olmalı")
    yuv = lambda M: [[round(v, 6) for v in s] for s in M]
    if mod == 'sutun':
        if d_out % tp:
            raise ValueError("d_out tp'ye bölünmeli")
        b = d_out // tp
        parcalar = [_carp(X, [s[k * b:(k + 1) * b] for s in W]) for k in range(tp)]
        birlesik = [sum((p[i] for p in parcalar), []) for i in range(n)]
        return {'parca_ciktilari': [yuv(p) for p in parcalar], 'birlesik': yuv(birlesik), 'iletisim': 'all-gather'}
    if d_in % tp:
        raise ValueError("d_in tp'ye bölünmeli")
    b = d_in // tp
    parcalar = [_carp([s[k * b:(k + 1) * b] for s in X], W[k * b:(k + 1) * b]) for k in range(tp)]
    birlesik = [[sum((p[i][j] for p in parcalar)) for j in range(d_out)] for i in range(n)]
    return {'parca_ciktilari': [yuv(p) for p in parcalar], 'birlesik': yuv(birlesik), 'iletisim': 'all-reduce'}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_33 as D
    D.goster(paralel_yerlesim, tp_matmul)
```
```hint
İki görevin çözümlerini olduğu gibi buraya koy. Deney dört gloo sürecini kendisi başlatır.
```
:::

::: anlat Sınır
3D paralellik (DP/TP/PP), FlashAttention, μP ve donanım arızası/loss spike konuları anlatı ve tek bir GPU sayısı tahminiyle verilir; görevler rank haritasını ve tensör paralel matris bölmeyi yazdırır; final adım gerçek bir MLP'yi gloo süreçleri arasında böler, SDPA ile naif dikkatin belleğini ölçer ve pipeline bubble'ını ölçülen aşama süreleriyle simüle eder; gerçek dağıtık eğitim yapılmaz, μP ve arıza senaryoları denenmez. Tensor parallelism hızlı düğüm içi bağlantı (NVLink) varsayar; düğümler arasına taşınınca verimi çok düşer. Pipeline bubble oranı mikro-batch sayısına bağlıdır ve 1F1B/interleaved şemalar bellek ile iletişim dengesini değiştirir. μP'nin hiperparametre aktarımı genişlik için gösterilmiştir; derinlik ve veri ölçeğinde aktarım kendiliğinden garanti değildir. Toplam GPU sayısı TP×PP×DP çarpımıdır, ama gerçek kümelerde arıza payı ve yedek düğümler bu sayıyı artırır.

Kaynaklar: [Narayanan vd. 2021 - Efficient Large-Scale Language Model Training on GPU Clusters Using Megatron-LM](https://arxiv.org/abs/2104.04473), [Yang vd. 2022 - Tensor Programs V: Tuning Large Neural Networks via Zero-Shot Hyperparameter Transfer](https://arxiv.org/abs/2203.03466), [Dao vd. 2022 - FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness](https://arxiv.org/abs/2205.14135).
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **16 Byte/parametre duvarı ve `3D Parallelism` (30 sn).** "`AdamW` ile karma duyarlıklı eğitim parametre başına en az 16 bayt ister; `Tensor Parallelism` katman içi matrisi düğüm içi hızlı `NVLink` üzerinde, `Pipeline Parallelism` katman gruplarını düğümler arasında, `Data Parallelism / ZeRO` ise veri ve durum parçalarını küme genelinde böler."
2. **İletişim tasarrufu (`Megatron MLP`) ve `FlashAttention` (35 sn).** "`MLP` bloğunda ilk katmanı sütun, ikinciyi satır paralel bölmek katman başına tek bir `all-reduce` ile yetinir; `FlashAttention` ise $T \times T$ skor matrisini HBM'ye yazmadan SRAM karolarında çevrimiçi `softmax` ile tam hesaplar."
3. **`μP` ve dağıtık buluşma güvenliği (`TCPStore`) (30 sn).** "`μP` küçük vekil modelde bulunan öğrenme oranını geniş modele taşır; küme tarafında ise `torch.distributed` `TCPStore` ve `gloo/NCCL` trafiği kimlik doğrulamasız olduğu için yalıtılmış ağ gerektirir."
4. **Soru (25 sn).** "Eğitim kümesinin `MASTER_PORT` (`TCPStore`) soketi paylaşımlı kurum ağına açık unutulursa yetkisiz bir süreç eğitimi durdurmadan hangi parametreleri veya sırları kurcalayabilir?"
:::
