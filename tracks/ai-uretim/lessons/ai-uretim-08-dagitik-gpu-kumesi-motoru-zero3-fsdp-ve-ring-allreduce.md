---
id: ai-uretim-08
title: "Dağıtık GPU Kümesi Motoru: Ring All-Reduce, ZeRO-3 / FSDP Sharding ve 1F1B Pipeline"
track: ai-uretim
order: 8
duration_minutes: 40
difficulty: ileri
xp: 310
prerequisites: [ai-uretim-07]
esleme: ai-uretim-07, ai-uretim-05, ai-uretim-14
summary: "10.000 GPU birbiriyle nasıl konuşur? Bant genişliği-optimal Ring All-Reduce (Scatter-Reduce + All-Gather), ZeRO-1/2/3 (PyTorch FSDP) bellek parçalama hesabı (16Ψ/N_d), Megatron-LM Tensor Parallelism ve 1F1B Pipeline Schedule balon oranı."
tags: [distributed-training, ring-allreduce, zero3, fsdp, tensor-parallelism, pipeline-parallelism]
---

::: anlat 1. 70 Milyar Parametreli Bir Model Neden 80 GB'lık Tek Bir H100 GPU'ya Sığmaz? (16Ψ Bellek Kuralı)
## Dağıtık training için maliyet modeli

Model durumlarını ve gradient iletişimini birden fazla işlemciye bölmek bellek ve haberleşme arasında tercih gerektirir. Ring All-Reduce sonucunu, ZeRO aşamalarında GPU başına düşen durumu ve pipeline bubble oranını hesaplayacaksın. Görevde vektör sonucu modellenir; gerçek dağıtık süreç veya ağ iletişimi başlatılmaz.

Bir konferansta kürsüye çıktığında dinleyicilere ilk olarak şu çarpıcı matematik sorusunu sor:
> *"Arkadaşlar, elimizde dünyanın en güçlü ekran kartlarından biri olan `80 GB HBM3` bellekli bir `NVIDIA H100` var. Peki neden sadece `7 Milyar` (`7B`) parametreli küçük bir modeli bile standart `Mixed Precision` (`BF16 + FP32 AdamW`) ile eğitmeye kalktığımızda tek başına model durumları (`Model States`) `112 GB VRAM` isteyip ekran kartını anında patlatıyor (`CUDA OutOfMemoryError`)?"*

Gel **`16\Psi` (`16 Byte / Parametre`) Kuralını** kalem kalem hesaplayalım!
Modelimizin toplam parametre sayısına $\Psi$ (örn. $\Psi = 7 \times 10^9$) diyelim. `Mixed Precision` (`BF16` ileri/backpropagation + `FP32` `AdamW` optimizer) eğitiminde her bir parametre için GPU belleğinde (`VRAM`) tutulması zorunlu olan **4 temel durum (`Model States`)** vardır:

```text
  HER 1 PARAMETRE (Ψ) İÇİN GEREKEN BELLEK (MIXED PRECISION ADAMW):
  ┌─────────────────────────────────────────────────────────────────────┐
  │ 1. BF16 Ağırlıklar (Weights w)               :  2 Byte × Ψ          │
  │ 2. BF16 Gradyanlar (Gradients g)             :  2 Byte × Ψ          │
  │ 3. FP32 AdamW Optimizer Durumları (12 Byte):                        │
  │    ├── FP32 Master Weights (Ana Kopya)       :  4 Byte × Ψ          │
  │    ├── FP32 1. Moment (Momentum m_t)         :  4 Byte × Ψ          │
  │    └── FP32 2. Moment (Variance v_t)         :  4 Byte × Ψ          │
  ├─────────────────────────────────────────────────────────────────────┤
  │ TOPLAM MODEL DURUMU BELLEĞİ                  = 16 Byte × Ψ (16Ψ) !  │
  └─────────────────────────────────────────────────────────────────────┘
```

- **$\Psi = 7\text{ Milyar}$ (`7B`) model için:** $16 \times 7\text{ GB} = \mathbf{112\text{ GB VRAM}}$ (Daha aktivasyonlar bile yokken `80 GB` H100 taştı!)
- **$\Psi = 70\text{ Milyar}$ (`70B`) model için:** $16 \times 70\text{ GB} = \mathbf{1.120\text{ GB}}$ (**$1.12\text{ Terabyte VRAM}$!**)
- **$\Psi = 671\text{ Milyar}$ (`671B`) model için:** $16 \times 671\text{ GB} = \mathbf{10.736\text{ GB}}$ (**$10.7\text{ Terabyte VRAM}$!**)

İşte bu yüzden `Frontier AI` modelleri tek bir GPU'da değil; **`NVLink`** ($900\text{ GB/s}$ düğüm içi) ve **`InfiniBand / RoCE`** ($400\text{ Gbps}$ düğümler arası) fiber optik ağlarla birbirine bağlanmış **binlerce GPU'luk bir süperbilgisayar kümesinde (`Distributed GPU Cluster`)** eğitilir!

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [ZeRO makalesi](https://arxiv.org/abs/1910.02054). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: anlat 2. 10.000 GPU Gradyanları Darboğaz Olmadan Nasıl Senkronize Eder? (Ring All-Reduce)
Klasik `Data Parallelism (DDP)` eğitiminde $N$ adet GPU'nun her biri farklı bir veri dilimini (`Micro-Batch`) okur ve kendi yerel gradyan vektörünü ($G_0, G_1, \dots, G_{N-1}$) hesaplar. Ağırlıkları güncellemeden önce tüm GPU'ların bu gradyanların toplamını/ortalamasını ($\sum_{i=0}^{N-1} G_i$) birbiriyle eşitlemesi (**`All-Reduce`**) gerekir.

### ❌ Naif Yöntem: `Parameter Server` (Merkezi Sunucu) Neden Çöker?
Eğer $N$ GPU'nun hepsi gradyanlarını tek bir "Merkezi GPU'ya (`Master Node`)" gönderirse, merkezi GPU'nun ağ kartına aynı anda $N \times \Phi$ veri hücum eder! $N = 1.000$ GPU olduğunda iletişim süresi 1.000 kat uzar ve tüm küme kilitlenir!

### 🚀 Bant Genişliği-Optimal Mucize: `Ring All-Reduce` (`Scatter-Reduce` + `All-Gather`)
Baidu ve NVIDIA (`NCCL`) tarafından popülerleştirilen **`Ring All-Reduce`** algoritmasında merkezi sunucu yoktur!
1. $N$ adet GPU mantıksal bir **halka (`Ring`: $\text{GPU}_0 \to \text{GPU}_1 \to \dots \to \text{GPU}_{N-1} \to \text{GPU}_0$)** şeklinde dizilir.
2. Her GPU, $\Phi$ elemanlı gradyan vektörünü **$N$ adet eşit parçaya (`Chunks`)** böler (her parça $\Phi / N$ boyutundadır).
3. Algoritma **2 Aşamada** toplam **$2(N - 1)$ adımda** tamamlanır:
   - **Aşama 1: `Scatter-Reduce` ($N - 1$ adım):** Her adımda her GPU bir parçayı sağındaki komşusuna gönderir, solundaki komşusundan gelen parçayı kendi içindeki parçanın **üzerine toplar (`Reduce`)**.Tam $N - 1$ adım sonunda, **her GPU'da $N$ parçadan tam 1 tanesinin küresel toplamı (`Full Sum of 1 Chunk`)** hazır hale gelir!
   - **Aşama 2: `All-Gather` ($N - 1$ adım):** Şimdi her GPU, elindeki o tam toplanmış parçayı halka boyunca $(N - 1)$ adım döndürerek diğer GPU'lara **kopyalar (`Overwrite`)**.

```text
  4 GPU HALKASINDA RING ALL-REDUCE:
   ┌────────┐      Parça Gönder      ┌────────┐
   │ GPU 0  │ ─────────────────────► │ GPU 1  │
   └────────┘                        └────────┘
       ▲                                 │
       │ Parça Gönder                    ▼ Parça Gönder
   ┌────────┐      Parça Gönder      ┌────────┐
   │ GPU 3  │ ◄───────────────────── │ GPU 2  │
   └────────┘                        └────────┘

  • 1. Aşama (Scatter-Reduce, N-1 adım): Parçalar halkada dönerken toplanır.
  • 2. Aşama (All-Gather, N-1 adım)    : Tam toplanmış parçalar herkese yayılır.
```

### 📐 Neden `Ring All-Reduce` Matematiksel Olarak Kusursuzdur?
Her bir GPU, toplam $2(N - 1)$ adımın her birinde ağ üzerinden yalnızca $\frac{\Phi}{N}$ boyutunda bir parça gönderir. Yani bir GPU'nun gönderdiği toplam veri miktarı:

$$\text{GPU Başına İletişim Hacmi} = 2(N - 1) \times \frac{\Phi}{N} = 2 \left(\frac{N - 1}{N}\right) \Phi \xrightarrow{N \to \infty} \mathbf{2\Phi}$$

**İnanılmaz Sonuç:** Kümedeki GPU sayısı $N = 8$ de olsa, $N = 10.000$ de olsa bir GPU'nun ağdan gönderdiği toplam veri miktarı **asla $2\Phi$'yi geçmez ($N$'den bağımsızdır)!**
:::

::: anlat 3. ZeRO-1, ZeRO-2, ZeRO-3 (PyTorch FSDP) ve 3D Parallelism Mimarisi
`Ring All-Reduce` iletişim darboğazını çözdü; peki her GPU'nun aynı $16\Psi$ model durumunu **gereksiz yere tekrar tekrar (`Redundant`)** kendi belleğinde tutması sorununu nasıl çözeceğiz?

Microsoft'un geliştirdiği **`ZeRO` (`Zero Redundancy Optimizer`)** ve PyTorch'taki karşılığı olan **`FSDP` (`Fully Sharded Data Parallel`)**, bu $16\Psi$ belleği $N_d$ adet GPU arasında **parçalar (`Sharding`)**:

| Mimari / Aşama | Parçalanan (`Sharded` $\div N_d$) Durumlar | GPU Başına Model Belleği Formülü | `7B` Model ($\Psi=7\text{B}$), $N_d=8$ GPU'da GPU Başına Bellek |
| :--- | :--- | :---: | :---: |
| **Standart `DDP` (`ZeRO-0`)** | Hiçbiri (Her GPU'da tam kopya var) | $2\Psi + 2\Psi + 12\Psi = \mathbf{16\Psi}$ | **$112.0\text{ GB}$** (Sığmaz!) |
| **`ZeRO-1` (`Optimizer Sharding`)** | Sadece `FP32 Optimizer States` ($12\Psi$) | $2\Psi + 2\Psi + \frac{12\Psi}{N_d}$ | $14 + 14 + 10.5 = \mathbf{38.5\text{ GB}}$ |
| **`ZeRO-2` (`+ Gradient Sharding`)** | `Optimizer` ($12\Psi$) + `Gradients` ($2\Psi$) | $2\Psi + \frac{2\Psi + 12\Psi}{N_d} = 2\Psi + \frac{14\Psi}{N_d}$ | $14 + 12.25 = \mathbf{26.25\text{ GB}}$ |
| **`ZeRO-3 / PyTorch FSDP`** | **Hepsi!** (`Weights` + `Grads` + `Opt`) | $\frac{2\Psi + 2\Psi + 12\Psi}{N_d} = \mathbf{\frac{16\Psi}{N_d}}$ | $112 / 8 = \mathbf{14.0\text{ GB}}$! |

- **`ZeRO-3 / FSDP` Nasıl Çalışır?** Her GPU, model ağırlıklarının bile yalnızca $1 / N_d$'lik dilimini tutar! Bir katmanın sırası geldiğinde GPU'lar o katmanın eksik ağırlık parçalarını `All-Gather` ile anlık olarak toplar, matris çarpımını yapar ve **işlem biter bitmez diğer GPU'lara ait ağırlık parçalarını bellekten siler (`Free`)!**

### 🌐 `3D Parallelism`: `Data (DP/FSDP)` $\times$ `Tensor (TP)` $\times$ `Pipeline (PP)`
Dev bir kümede sadece `FSDP` yetmez; **3 boyutlu paralellik (`3D Parallelism`)** birlikte kullanılır:
1. **`Tensor Parallelism (TP — Megatron-LM)`:** Tek bir matris çarpımını ($Y = X A B$) aynı sunucu düğümü (`Node`) içindeki `NVLink` ile bağlı 8 GPU'ya böler: İlk matris $A$ **sütun bazlı (`Column-Parallel`: $[A_1 \mid A_2]$)**, ikinci matris $B$ ise **satır bazlı (`Row-Parallel`: $[B_1 ; B_2]$)** bölünür; böylece sadece sonda tek bir `All-Reduce` ile dev katman 8 GPU'da eşzamanlı hesaplanır!
2. **`Pipeline Parallelism (PP)` ve `1F1B Schedule`:** Modelin 80 katmanı düğümler arasında aşamalara (`Stages` $P$) bölünür (örn. `Stage 0`: Katman 1-20, `Stage 1`: Katman 21-40...).
   - Eğer tek bir paketi beklersen diğer aşamalar boşta bekler. Bunun yerine paket $M$ adet **`Micro-Batch`** parçasına bölünür ve **`1F1B` (`One-Forward-One-Backward`)** takvimiyle boru hattına sürülür!
   - $P$ aşamalı ve $M$ mikro-batch'li bir `1F1B Pipeline` hattında GPU'ların boşta beklediği zamanın (**`Pipeline Bubble Fraction`**) toplam zamana oranı:

$$\text{Bubble Oranı} = \frac{P - 1}{M + P - 1}$$

Bu formül bize altın mühendislik kuralını söyler: **Balon israfını (`Bubble`) küçültmek için mikro-batch sayısı $M \gg P$ seçilmelidir!**

```python norun
import torch
import torch.distributed as dist
from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
from torch.distributed.fsdp import MixedPrecision

def setup_fsdp_model(model: torch.nn.Module):
    # PyTorch FSDP (ZeRO-3) + BF16 Mixed Precision üretim yapılandırması
    bf16_policy = MixedPrecision(
        param_dtype=torch.bfloat16,
        reduce_dtype=torch.bfloat16,
        buffer_dtype=torch.bfloat16,
    )
    sharded_model = FSDP(
        model,
        mixed_precision=bf16_policy,
        use_orig_params=True,
        limit_all_gathers=True,
    )
    return sharded_model
```
:::

::: tahmin ZeRO-3 Bellek Tasarrufu ve 1F1B Pipeline Bubble Hesabı
$\Psi = 32\text{ Milyar}$ (`32B`) parametreli bir modeli $N_d = 16$ adet GPU üzerinde **`ZeRO-3 (FSDP)`** ile eğitiyoruz. Aynı zamanda $P = 4$ aşamalı (`stages`) bir `Pipeline Parallelism` hattında $M = 12$ adet `Micro-Batch` kullanıyoruz.
`ZeRO-3` sayesinde GPU başına düşen model durumu belleği (`GB`) ve `1F1B` boru hattı balon oranı (`Bubble Ratio`) nedir?

```python
psi_milyar = 32
n_gpu = 16
zero3_gb = (16 * psi_milyar) / n_gpu

P, M = 4, 12
bubble_orani = round((P - 1) / (M + P - 1), 4)
print(f"ZeRO-3 GPU Bellegi: {zero3_gb:.1f} GB | 1F1B Bubble Orani: {bubble_orani:.2f}")
```

???

```cikti
ZeRO-3 GPU Bellegi: 32.0 GB | 1F1B Bubble Orani: 0.20
```
Standart eğitimde $16 \times 32 = 512\text{ GB}$ tutacak olan model durumları, `ZeRO-3` ile $16$ GPU'ya eşit parçalandığı için GPU başına yalnızca $512 / 16 = 32.0\text{ GB}$ yer kaplar. $P=4$ ve $M=12$ için `1F1B` balon oranı ise $(4 - 1) / (12 + 4 - 1) = 3 / 15 = 0.20$ (`%20`) olur.
:::

::: gorev 1 · Ring All-Reduce (Scatter-Reduce + All-Gather) Simülasyonu
$N$ adet GPU'nun yerel gradyan vektörlerini halka topolojisinde (`Ring Topology`) parça parça toplayıp eşitleyen `ring_allreduce(gpu_vektorleri)` işlevini yaz:

1. **Girdiler:**
   - `gpu_vektorleri`: $N$ adet GPU'nun yerel vektörlerini tutan liste (`N` adet liste, her birinin uzunluğu $\Phi$ olup $\Phi$ sayısı $N$'ye tam bölünmektedir).
2. **Kurallar ve Hesaplamalar:**
   - Parça boyutu (`parca_boyutu`): $C = \Phi // N$.
   - `Scatter-Reduce` ($N - 1$ adım) ve `All-Gather` ($N - 1$ adım) tamamlandığında, her GPU'nun elindeki nihai vektör (`senkronize_vektor`), tüm GPU vektörlerinin eleman bazlı toplamıdır:
     $$S_j = \sum_{i=0}^{N-1} \text{gpu\_vektorleri}[i][j]$$
   - Ayrıca her parçanın ($k = 0, \dots, N-1$) toplamlarını ayrı alt listeler olarak tutan `parca_toplamlari` listesini ($N$ adet $C$ elemanlı liste) oluştur.
   - Tek bir GPU'nun toplam `Scatter-Reduce` + `All-Gather` adımlarında ($2(N-1)$ adımda) ağ üzerinden **gönderdiği toplam skaler eleman sayısını** hesapla:
     $$\text{gpu\_basi\_gonderilen\_eleman} = 2 \cdot (N - 1) \cdot C$$
   - Vektörlerdeki sayısal değerleri `round(val, 6)` ile yuvarla.
3. **Dönüş Değeri:**
   `{"parca_boyutu": int, "toplam_adim": int, "gpu_basi_gonderilen_eleman": int, "parca_toplamlari": [[float, ...], ...], "senkronize_vektor": [float, ...]}` sözlüğü döndür (`toplam_adim = 2 * (N - 1)`). Girdileri değiştirme.

```starter
def ring_allreduce(gpu_vektorleri):
    # KUSURLU BAŞLANGIÇ KODU: halka adımlarını ve toplamları hesaplamadan sadece ilk GPU'nun vektörünü döndürüyor!
    n = len(gpu_vektorleri)
    phi = len(gpu_vektorleri[0])
    c = phi // n
    return {
        "parca_boyutu": c,
        "toplam_adim": 0,
        "gpu_basi_gonderilen_eleman": 0,
        "parca_toplamlari": [[0.0] * c for _ in range(n)],
        "senkronize_vektor": [round(float(x), 6) for x in gpu_vektorleri[0]],
    }

ornek_gpular = [
    [1.0, 2.0, 3.0, 4.0],
    [0.5, 1.5, 2.5, 3.5],
]
print(ring_allreduce(ornek_gpular))
```

```test
import copy

def _ref_ring(gpular):
    n = len(gpular)
    phi = len(gpular[0])
    c = phi // n
    senk = [round(sum(gpular[i][j] for i in range(n)), 6) for j in range(phi)]
    parcalar = [senk[k * c : (k + 1) * c] for k in range(n)]
    return {
        "parca_boyutu": c,
        "toplam_adim": 2 * (n - 1),
        "gpu_basi_gonderilen_eleman": 2 * (n - 1) * c,
        "parca_toplamlari": parcalar,
        "senkronize_vektor": senk,
    }

def sozlesme(fn):
    try:
        vakalar = [
            [[1.0, 2.0, 3.0, 4.0], [0.5, 1.5, 2.5, 3.5]],
            [[1.0, 0.0, 2.0, -1.0, 3.0, 1.0], [2.0, 1.0, 0.0, 4.0, -1.0, 2.0], [0.5, 2.5, 1.0, 1.0, 0.0, -0.5]],
            [[1, 2, 3, 4], [4, 3, 2, 1], [1, 1, 1, 1], [2, 2, 2, 2]],
        ]
        for g in vakalar:
            g_kopya = copy.deepcopy(g)
            sonuc = fn(g)
            bek = _ref_ring(g)
            if sonuc != bek or g != g_kopya:
                return False
        return True
    except Exception:
        return False

ok(sozlesme(ring_allreduce), "ring_allreduce halka iletişim adımlarını, parça toplamlarını ve senkronize vektörü doğru hesaplamalı")

def m_tek_asama(g):
    r = copy.deepcopy(ring_allreduce(g))
    r["toplam_adim"] = len(g) - 1
    return r

def m_ortalama_al(g):
    r = copy.deepcopy(ring_allreduce(g))
    r["senkronize_vektor"] = [round(x / len(g), 6) for x in r["senkronize_vektor"]]
    return r

for ad, m in [("All-Gather aşamasını adım sayısında unutan", m_tek_asama), ("Toplam yerine ortalama alan", m_ortalama_al)]:
    ok(not sozlesme(m), f"Yanlış çözüm/mutant yakalanmalı: {ad}")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def ring_allreduce(gpu_vektorleri):\n    n = len(gpu_vektorleri)\n    phi = len(gpu_vektorleri[0])\n    parca_boyutu = phi // n\n    senkronize = [round(sum((gpu_vektorleri[i][j] for i in range(n))), 6) for j in range(phi)]\n    parca_toplamlari = [senkronize[k * parca_boyutu:(k + 1) * parca_boyutu] for k in range(n)]\n    toplam_adim = 2 * (n - 1)\n    gonderilen = toplam_adim * parca_boyutu\n    return {'parca_boyutu': parca_boyutu, 'toplam_adim': toplam_adim, 'gpu_basi_gonderilen_eleman': gonderilen, 'parca_toplamlari': parca_toplamlari, 'senkronize_vektor': senkronize}", 'referans', 'exec'), _REF)
_t, _g = _ff(ring_allreduce, _REF['ring_allreduce'], ([[1.0, 2.0, 3.0, 4.0], [0.5, 1.5, 2.5, 3.5]],), tohum=2530, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (ring_allreduce): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
ok(ring_allreduce([[0.1234564, 1.0], [0.0000003, 2.0]]) == _REF['ring_allreduce']([[0.1234564, 1.0], [0.0000003, 2.0]]), "ring_allreduce 6 basamak yuvarlama korunmalı")
```

```solution
def ring_allreduce(gpu_vektorleri):
    n = len(gpu_vektorleri)
    phi = len(gpu_vektorleri[0])
    parca_boyutu = phi // n

    # Simülasyon: Halka üzerinde Scatter-Reduce + All-Gather sonucu oluşan küresel toplam
    senkronize = [
        round(sum(gpu_vektorleri[i][j] for i in range(n)), 6)
        for j in range(phi)
    ]
    parca_toplamlari = [
        senkronize[k * parca_boyutu : (k + 1) * parca_boyutu]
        for k in range(n)
    ]
    toplam_adim = 2 * (n - 1)
    gonderilen = toplam_adim * parca_boyutu

    return {
        "parca_boyutu": parca_boyutu,
        "toplam_adim": toplam_adim,
        "gpu_basi_gonderilen_eleman": gonderilen,
        "parca_toplamlari": parca_toplamlari,
        "senkronize_vektor": senkronize,
    }
```

```hint
`parca_boyutu = phi // n`, `toplam_adim = 2 * (n - 1)` ve `gpu_basi_gonderilen_eleman = 2 * (n - 1) * parca_boyutu` formüllerini kullan. Her indeks `j` için tüm GPU'ların değerlerini toplayıp `senkronize_vektor` ve `parca_toplamlari` listelerini üret.
```
:::

::: gorev 2 · ZeRO-1/2/3 GPU Başına Bellek Hesabı ve 1F1B Pipeline Bubble Oranı
Dağıtık bir kümede seçilen `ZeRO` aşamasına göre GPU başına düşen model durumu belleğini (`GB`) ve `1F1B Pipeline Parallelism` balon oranını hesaplayan `dagitik_bellek_ve_balon(parametre_milyar, gpu_sayisi, zero_asama, pipeline_asama, mikro_batch_sayisi)` işlevini yaz:

1. **Girdiler:**
   - `parametre_milyar`: Modelin milyar ($\Psi$, $10^9$) cinsinden parametre sayısı (`float` veya `int`, örn. `70` $\to 70\text{B}$). ($1\text{ Milyar} \times 1\text{ Byte} = 1\text{ GB}$ kabul edilir).
   - `gpu_sayisi`: Veri paralelliği (`Data Parallelism` $N_d$) GPU sayısı (`int > 0`).
   - `zero_asama`: `0` (Standart DDP), `1` (`ZeRO-1`), `2` (`ZeRO-2`) veya `3` (`ZeRO-3 / FSDP`).
   - `pipeline_asama`: Boru hattı aşama sayısı $P$ (`int >= 1`).
   - `mikro_batch_sayisi`: Mikro-batch sayısı $M$ (`int >= 1`).
2. **Formüller (`Mixed Precision: 2Ψ Ağırlık + 2Ψ Gradyan + 12Ψ Optimizer = 16Ψ GB`):**
   - `ddp_bellek_gb`: Parçalamasız (`ZeRO-0`) bellek = $16 \times \Psi$.
   - `gpu_basi_bellek_gb`:
     - `zero_asama == 0`: $16 \Psi$
     - `zero_asama == 1`: $2\Psi + 2\Psi + \frac{12\Psi}{N_d}$
     - `zero_asama == 2`: $2\Psi + \frac{2\Psi + 12\Psi}{N_d}$
     - `zero_asama == 3`: $\frac{16\Psi}{N_d}$
   - `bellek_tasarruf_katsayisi`: `ddp_bellek_gb / gpu_basi_bellek_gb`.
   - `pipeline_bubble_orani`:
     $$\text{Bubble} = \frac{P - 1}{M + P - 1}$$
   - Tüm sayısal çıktıları `round(val, 4)` ile yuvarla.
3. **Dönüş Değeri:**
   `{"ddp_bellek_gb": float, "gpu_basi_bellek_gb": float, "bellek_tasarruf_katsayisi": float, "pipeline_bubble_orani": float}` sözlüğü döndür.

```starter
def dagitik_bellek_ve_balon(parametre_milyar, gpu_sayisi, zero_asama, pipeline_asama, mikro_batch_sayisi):
    # KUSURLU BAŞLANGIÇ KODU: ZeRO parçalama formüllerini ve 1F1B balon oranını hesaplamıyor!
    ddp = round(16.0 * parametre_milyar, 4)
    return {
        "ddp_bellek_gb": ddp,
        "gpu_basi_bellek_gb": ddp,
        "bellek_tasarruf_katsayisi": 1.0,
        "pipeline_bubble_orani": 0.0,
    }

print(dagitik_bellek_ve_balon(parametre_milyar=70, gpu_sayisi=64, zero_asama=3, pipeline_asama=8, mikro_batch_sayisi=32))
```

```test
import copy

def _ref_dagitik(psi, nd, z, p, m):
    ddp = 16.0 * psi
    if z == 0:
        gb = 16.0 * psi
    elif z == 1:
        gb = 4.0 * psi + (12.0 * psi) / nd
    elif z == 2:
        gb = 2.0 * psi + (14.0 * psi) / nd
    else:
        gb = (16.0 * psi) / nd
    tasarruf = ddp / gb
    balon = (p - 1) / (m + p - 1)
    return {
        "ddp_bellek_gb": round(ddp, 4),
        "gpu_basi_bellek_gb": round(gb, 4),
        "bellek_tasarruf_katsayisi": round(tasarruf, 4),
        "pipeline_bubble_orani": round(balon, 4),
    }

def sozlesme(fn):
    try:
        vakalar = [
            (70, 64, 3, 8, 32),
            (7, 8, 1, 4, 12),
            (13, 16, 2, 2, 8),
            (7, 4, 0, 1, 4),
        ]
        for args in vakalar:
            if fn(*args) != _ref_dagitik(*args):
                return False
        return True
    except Exception:
        return False

ok(sozlesme(dagitik_bellek_ve_balon), "dagitik_bellek_ve_balon ZeRO-0/1/2/3 belleklerini ve 1F1B balon oranını doğru hesaplamalı")

def m_zero12_karistir(psi, nd, z, p, m):
    return dagitik_bellek_ve_balon(psi, nd, 3 if z in (1, 2) else z, p, m)

def m_yanlis_balon(psi, nd, z, p, m):
    r = copy.deepcopy(dagitik_bellek_ve_balon(psi, nd, z, p, m))
    r["pipeline_bubble_orani"] = round((p - 1) / m, 4)
    return r

for ad, m in [("ZeRO-1 ve ZeRO-2 formüllerini ZeRO-3 ile karıştıran", m_zero12_karistir), ("1F1B balon paydasında (M + P - 1) yerine M kullanan", m_yanlis_balon)]:
    ok(not sozlesme(m), f"Yanlış çözüm/mutant yakalanmalı: {ad}")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def dagitik_bellek_ve_balon(parametre_milyar, gpu_sayisi, zero_asama, pipeline_asama, mikro_batch_sayisi):\n    ddp = 16.0 * parametre_milyar\n    if zero_asama == 0:\n        gb = 16.0 * parametre_milyar\n    elif zero_asama == 1:\n        gb = 4.0 * parametre_milyar + 12.0 * parametre_milyar / gpu_sayisi\n    elif zero_asama == 2:\n        gb = 2.0 * parametre_milyar + 14.0 * parametre_milyar / gpu_sayisi\n    else:\n        gb = 16.0 * parametre_milyar / gpu_sayisi\n    tasarruf = ddp / gb\n    balon = (pipeline_asama - 1) / (mikro_batch_sayisi + pipeline_asama - 1)\n    return {'ddp_bellek_gb': round(ddp, 4), 'gpu_basi_bellek_gb': round(gb, 4), 'bellek_tasarruf_katsayisi': round(tasarruf, 4), 'pipeline_bubble_orani': round(balon, 4)}", 'referans', 'exec'), _REF)
_t, _g = _ff(dagitik_bellek_ve_balon, _REF['dagitik_bellek_ve_balon'], (70, 64, 3, 8, 32), tohum=3442, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (dagitik_bellek_ve_balon): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
ok(dagitik_bellek_ve_balon(0.00003, 4, 0, 2, 4) == _REF['dagitik_bellek_ve_balon'](0.00003, 4, 0, 2, 4), "ddp_bellek_gb 4 basamak yuvarlama korunmalı")
```

```solution
def dagitik_bellek_ve_balon(parametre_milyar, gpu_sayisi, zero_asama, pipeline_asama, mikro_batch_sayisi):
    ddp = 16.0 * parametre_milyar
    if zero_asama == 0:
        gb = 16.0 * parametre_milyar
    elif zero_asama == 1:
        gb = 4.0 * parametre_milyar + (12.0 * parametre_milyar) / gpu_sayisi
    elif zero_asama == 2:
        gb = 2.0 * parametre_milyar + (14.0 * parametre_milyar) / gpu_sayisi
    else:
        gb = (16.0 * parametre_milyar) / gpu_sayisi

    tasarruf = ddp / gb
    balon = (pipeline_asama - 1) / (mikro_batch_sayisi + pipeline_asama - 1)

    return {
        "ddp_bellek_gb": round(ddp, 4),
        "gpu_basi_bellek_gb": round(gb, 4),
        "bellek_tasarruf_katsayisi": round(tasarruf, 4),
        "pipeline_bubble_orani": round(balon, 4),
    }
```

```hint
`zero_asama` 0, 1, 2 ve 3 durumları için sırasıyla `16*psi`, `4*psi + 12*psi/nd`, `2*psi + 14*psi/nd` ve `16*psi/nd` formüllerini uygula. Balon oranı için `(pipeline_asama - 1) / (mikro_batch_sayisi + pipeline_asama - 1)` hesapla.
```
:::

::: anlat Gerçek deney: Dört gerçek gloo sürecinde all-reduce, kötü niyetli rank ve gerçek AdamW belleği
Final dağıtık eğitimin iletişimini gerçekten çalıştırır (tek makinede, GPU gerekmez):

- SmolLM2-135M'in 61 RMSNorm ağırlığı (35 136 eleman) dört farklı cümlede ayrı ayrı türetilir: dört veri paralel rank'ın **gerçek gradyanları**.
- Dört ayrı Python süreci `torch.distributed` ile **gloo** süreç grubu kurar ve `all_reduce(SUM)` çağırır. Her rank aynı toplamı almalıdır.
- Aynı dört vektör senin `ring_allreduce` işlevine verilir; sonuç gloo'nun toplamıyla karşılaştırılır. Ring'de rank başına gönderilen eleman sayısı, her şeyi rank 0'da toplayan naif yöntemle kıyaslanır.
- **Kötü niyetli rank:** 3. rank gradyanını −20 ile çarpıp gönderir. All-reduce bir toplamadır; bütünlük ya da makullük denetimi yapmaz. Sonuçta **tüm** rank'lar aynı zehirli gradyanı alır. Temiz ortalamayla kosinüs benzerliği ölçülür ve koordinat bazlı medyanla (Byzantine-dayanıklı bir birleştirme) kıyaslanır.
- **ZeRO belleği:** SmolLM2'nin gerçek parametre sayısı senin `dagitik_bellek_ve_balon` işlevine verilir. Bağımsız olarak, gerçek bir katmanda `torch.optim.AdamW` bir adım atılır ve parametre, gradyan ve iki moment tensörünün **gerçek bayt sayısı** ölçülür.

**Güvenlik yönü — Byzantine savunma ve kaçışı:** Kötü rank'a karşı basit bir savunma, normu diğerlerinin medyanının 3 katını aşan gradyanı dışlamaktır. Bu filtre −20× gönderen rank'ı yakalar. Ama saldırgan gradyanını **ters çevirip normunu ortalamaya eşitlerse** filtre onu göremez: dağıtık eğitimde savunma tek bir istatistiğe dayanamaz.

Kabul: iki işlevin farksal taramayı geçmesi; tüm gloo rank'larının aynı sonucu alması; ring sonucunun gloo'dan en çok `1e-5` farklı olması; kötü rank'ın ortalama gradyanı ters çevirmesi (kosinüs < 0); DDP belleğinin ölçülen AdamW durumuyla `1e-3` GB içinde aynı olması. Ayrıca norm filtresi kötü rank'ı yakalamalı (kosinüs > 0.7), normu korunmuş ters gradyan ise filtreden kaçmalıdır.

**Kanıt dosyasını oku:** `ring_gloo_en_buyuk_fark`, `gpu_basi_gonderilen_ring`, `rank0_toplanan_naif`, `kotu_rank_kosinus`, `medyan_kosinus`, `adamw_bayt_parametre`, `zero_gpu_basi_gb`. Soru 1: Rank sayısı 64 olsaydı ring'in rank başına gönderdiği eleman sayısı nasıl değişirdi? Soru 2: Medyan neden ortalamadan daha dayanıklı ama yine de temiz gradyandan uzak? Soru 3: fp32 AdamW 16 bayt/parametre; karışık hassasiyette de 16 bayt çıkmasının nedeni ne?
:::

::: gorev Gerçek deney · Gerçek gradyanlarla gloo all-reduce, kötü niyetli rank ve ZeRO bellek ölçümü
Önceki görevlerdeki `ring_allreduce`, `dagitik_bellek_ve_balon` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 240
```
```starter
import ai_lab
def ring_allreduce(gpu_vektorleri):
    n = len(gpu_vektorleri)
    phi = len(gpu_vektorleri[0])
    c = phi // n
    return {'parca_boyutu': c, 'toplam_adim': 0, 'gpu_basi_gonderilen_eleman': 0, 'parca_toplamlari': [[0.0] * c for _ in range(n)], 'senkronize_vektor': [round(float(x), 6) for x in gpu_vektorleri[0]]}

def dagitik_bellek_ve_balon(parametre_milyar, gpu_sayisi, zero_asama, pipeline_asama, mikro_batch_sayisi):
    ddp = round(16.0 * parametre_milyar, 4)
    return {'ddp_bellek_gb': ddp, 'gpu_basi_bellek_gb': ddp, 'bellek_tasarruf_katsayisi': 1.0, 'pipeline_bubble_orani': 0.0}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_08 as D
    D.goster(ring_allreduce, dagitik_bellek_ve_balon)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('dil_modeli', 'ai_uretim_08_isci', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
ring_allreduce = need("ring_allreduce")
dagitik_bellek_ve_balon = need("dagitik_bellek_ve_balon")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def ring_allreduce(gpu_vektorleri):\n    n = len(gpu_vektorleri)\n    phi = len(gpu_vektorleri[0])\n    parca_boyutu = phi // n\n    senkronize = [round(sum((gpu_vektorleri[i][j] for i in range(n))), 6) for j in range(phi)]\n    parca_toplamlari = [senkronize[k * parca_boyutu:(k + 1) * parca_boyutu] for k in range(n)]\n    toplam_adim = 2 * (n - 1)\n    gonderilen = toplam_adim * parca_boyutu\n    return {'parca_boyutu': parca_boyutu, 'toplam_adim': toplam_adim, 'gpu_basi_gonderilen_eleman': gonderilen, 'parca_toplamlari': parca_toplamlari, 'senkronize_vektor': senkronize}\n\ndef dagitik_bellek_ve_balon(parametre_milyar, gpu_sayisi, zero_asama, pipeline_asama, mikro_batch_sayisi):\n    ddp = 16.0 * parametre_milyar\n    if zero_asama == 0:\n        gb = 16.0 * parametre_milyar\n    elif zero_asama == 1:\n        gb = 4.0 * parametre_milyar + 12.0 * parametre_milyar / gpu_sayisi\n    elif zero_asama == 2:\n        gb = 2.0 * parametre_milyar + 14.0 * parametre_milyar / gpu_sayisi\n    else:\n        gb = 16.0 * parametre_milyar / gpu_sayisi\n    tasarruf = ddp / gb\n    balon = (pipeline_asama - 1) / (mikro_batch_sayisi + pipeline_asama - 1)\n    return {'ddp_bellek_gb': round(ddp, 4), 'gpu_basi_bellek_gb': round(gb, 4), 'bellek_tasarruf_katsayisi': round(tasarruf, 4), 'pipeline_bubble_orani': round(balon, 4)}", 'referans', 'exec'), _REF)
_t, _g = _ff(ring_allreduce, _REF['ring_allreduce'], ([[1.0, 2.0, 3.0, 4.0], [0.5, 1.5, 2.5, 3.5]],), tohum=2530, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (ring_allreduce): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(dagitik_bellek_ve_balon, _REF['dagitik_bellek_ve_balon'], (70, 64, 3, 8, 32), tohum=3442, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (dagitik_bellek_ve_balon): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
kontrol(ring_allreduce([[0.1234564, 1.0, 2.0], [0.0000003, 2.0, 3.0], [0.0, 0.0, 1.0]]) == _REF['ring_allreduce']([[0.1234564, 1.0, 2.0], [0.0000003, 2.0, 3.0], [0.0, 0.0, 1.0]]), "3 GPU 3 eleman gonderilen ve yuvarlama korunmalı")
kontrol(dagitik_bellek_ve_balon(7.0, 8, 0, 4, 16) == _REF['dagitik_bellek_ve_balon'](7.0, 8, 0, 4, 16), "zero_asama=0 DDP bellek hesabı korunmalı")
kontrol(dagitik_bellek_ve_balon(0.00003, 4, 0, 2, 4) == _REF['dagitik_bellek_ve_balon'](0.00003, 4, 0, 2, 4), "ddp_bellek_gb 4 basamak yuvarlama korunmalı")
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_08 as D
try: r = D.deney(ring_allreduce, dagitik_bellek_ve_balon)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['gloo_ranklar_ayni'], 'dört gloo sürecinin hepsi aynı all-reduce sonucunu aldı')
kontrol(r['ring_ayni'], 'ring all-reduce simülasyonu gerçek gloo toplamıyla aynı (fark < 1e-5)')
kontrol(r['zehir_yayildi'], "tek kötü niyetli rank tüm rank'ların ortalama gradyanını ters çevirdi")
kontrol(r['zero_formul_dogru'], 'DDP bellek formülü gerçek AdamW durum tensörlerinden ölçülen bellekle aynı')
kontrol(r['norm_filtresi_yakaladi'] and r['sinsi_saldiri_kacti'], "norm filtresi −20× rank'ı yakaladı; normu korunmuş ters gradyan filtreden kaçtı")
ai_lab.kanit_yaz("ai-uretim-08-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-08", "deney": r})
```
```solution
import ai_lab
def ring_allreduce(gpu_vektorleri):
    n = len(gpu_vektorleri)
    phi = len(gpu_vektorleri[0])
    parca_boyutu = phi // n
    senkronize = [round(sum((gpu_vektorleri[i][j] for i in range(n))), 6) for j in range(phi)]
    parca_toplamlari = [senkronize[k * parca_boyutu:(k + 1) * parca_boyutu] for k in range(n)]
    toplam_adim = 2 * (n - 1)
    gonderilen = toplam_adim * parca_boyutu
    return {'parca_boyutu': parca_boyutu, 'toplam_adim': toplam_adim, 'gpu_basi_gonderilen_eleman': gonderilen, 'parca_toplamlari': parca_toplamlari, 'senkronize_vektor': senkronize}

def dagitik_bellek_ve_balon(parametre_milyar, gpu_sayisi, zero_asama, pipeline_asama, mikro_batch_sayisi):
    ddp = 16.0 * parametre_milyar
    if zero_asama == 0:
        gb = 16.0 * parametre_milyar
    elif zero_asama == 1:
        gb = 4.0 * parametre_milyar + 12.0 * parametre_milyar / gpu_sayisi
    elif zero_asama == 2:
        gb = 2.0 * parametre_milyar + 14.0 * parametre_milyar / gpu_sayisi
    else:
        gb = 16.0 * parametre_milyar / gpu_sayisi
    tasarruf = ddp / gb
    balon = (pipeline_asama - 1) / (mikro_batch_sayisi + pipeline_asama - 1)
    return {'ddp_bellek_gb': round(ddp, 4), 'gpu_basi_bellek_gb': round(gb, 4), 'bellek_tasarruf_katsayisi': round(tasarruf, 4), 'pipeline_bubble_orani': round(balon, 4)}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_08 as D
    D.goster(ring_allreduce, dagitik_bellek_ve_balon)
```
```hint
İki görevin çözümlerini olduğu gibi buraya koy. Deney dört gloo sürecini kendisi başlatır; Windows güvenlik duvarı izin sorarsa yerel ağ için onay gerekebilir.
```
:::

::: anlat Sınır
Görevler ring all-reduce'u (scatter-reduce + all-gather) listeler üzerinde simüle eder, ZeRO-1/2/3 belleğini ve 1F1B bubble oranını formülle hesaplatır; final adım dört gerçek gloo sürecinde all-reduce yapar (tek makine, CPU; NCCL ve gerçek ağ ölçülmez). Ring all-reduce bant genişliği açısından optimaldir, ama gecikmesi 2(N−1) adımla büyür; küçük mesajlarda ağaç tabanlı algoritmalar daha hızlıdır. ZeRO bellek formülleri aktivasyon belleğini, geçici tamponları ve parçalanma (fragmentation) kaybını içermez. ZeRO-3 her katmanda parametre toplama trafiği ekler; yavaş bir ağda hızlanma yerine yavaşlama olur.

Kaynaklar: [Rajbhandari vd. 2020 - ZeRO: Memory Optimizations Toward Training Trillion Parameter Models](https://arxiv.org/abs/1910.02054), [Sergeev ve Del Balso 2018 - Horovod: fast and easy distributed deep learning in TensorFlow](https://arxiv.org/abs/1802.05799), [Narayanan vd. 2021 - Efficient Large-Scale Language Model Training on GPU Clusters Using Megatron-LM](https://arxiv.org/abs/2104.04473), [Zhao vd. 2023 - PyTorch FSDP: Experiences on Scaling Fully Sharded Data Parallel](https://arxiv.org/abs/2304.11277).
:::

::: dusun
Sahnede bir bulut altyapı mimarı sana şu soruyu yöneltti:
*"Hocam, elimizde 64 adet sunucu düğümü (`Nodes`) ve her sunucunun içinde 8 adet `H100 GPU` (toplam 512 GPU) var. Sunucu içindeki 8 GPU birbirine `900 GB/s` hızında `NVLink` ile bağlı; ancak sunucular birbirine `50 GB/s` hızında `InfiniBand` ağ kablolarıyla bağlı. `3D Parallelism` (`Tensor Parallelism`, `Pipeline Parallelism`, `ZeRO Data Parallelism`) kurarken hangi paralellik türünü kesinlikle sunucu içinde (`Intra-Node NVLink`) tutmalı, hangilerini sunucular arasına (`Inter-Node`) yaymalıyız?"*

Bu soruya **`Tensor Parallelism` adımının her `Transformer` katmanında 2 kez senkron `All-Reduce` gerektirmesi (çok yüksek bant genişliği ve düşük gecikme ihtiyacı)** ile **`Pipeline Parallelism` ve `ZeRO`'nun daha seyrek veya `Computation-Communication Overlap` ile gizlenebilir iletişimi** arasındaki fark üzerinden nasıl cevap verirsin?
:::

::: ozet
- **`16Ψ` ($16\Psi$) Kuralı:** `Mixed Precision` (`BF16` ağırlık/gradyan + `FP32 AdamW` ana ağırlık ve momentler) eğitiminde model durumları parametre başına **$16\text{ Byte}$** (`70B` model için $1.12\text{ TB}$) bellek gerektirir.
- **`Ring All-Reduce`**, $N$ GPU'yu halka topolojisinde dizip `Scatter-Reduce` ($N-1$ adım) ve `All-Gather` ($N-1$ adım) aşamalarıyla gradyanları GPU başına en fazla $2\Phi$ iletişim hacmiyle **bant genişliği-optimal** olarak senkronize eder.
- **`ZeRO-1 / ZeRO-2 / ZeRO-3 (PyTorch FSDP)`**, sırasıyla `Optimizer States` ($12\Psi$), `Gradients` ($2\Psi$) ve `Weights` ($2\Psi$) durumlarını $N_d$ GPU arasında parçalayarak (`Sharding`) GPU başına belleği $16\Psi / N_d$ seviyesine indirir.
- **`3D Parallelism`**, düğüm içi yüksek hızlı `NVLink` üzerinde **`Tensor Parallelism`**, düğümler arasında **`1F1B Pipeline Parallelism`** (balon oranı $\frac{P-1}{M+P-1}$) ve **`ZeRO Data Parallelism`** katmanlarını birleştirerek on binlerce GPU'nun tek bir dev beyin gibi çalışmasını sağlar.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **$16\Psi$ bellek hesabı (25 sn).** "Karma duyarlıklı `AdamW` eğitiminde parametre başına `BF16` ağırlık (`2 B`) + `BF16` gradyan (`2 B`) + `FP32` ana ağırlık ve iki moment (`12 B`) toplam $16\Psi$ bayt tutar; 70B model tek başına `1.12 TB` durum belleği ister."
2. **`Ring All-Reduce` ve `ZeRO` parçalama (35 sn).** "Halka topolojisinde `scatter-reduce` + `all-gather` gradyanları GPU başına yaklaşık $2\Phi$ iletişimle eşitler; `ZeRO-1/2/3` (`FSDP`) ise sırasıyla optimizer durumlarını, gradyanları ve ağırlıkları $N_d$ GPU'ya bölerek kopya tekrarını kaldırır."
3. **`3D Parallelism` yerleşimi (35 sn).** "Her katmanda senkron iletişim isteyen `Tensor Parallelism` hızlı düğüm içi `NVLink` içinde tutulur; düğümler arası daha yavaş ağda `1F1B Pipeline` (balon oranı $\frac{P-1}{M+P-1}$) ve `ZeRO` veri paralelliği çalıştırılır."
4. **Soru (25 sn).** "Mikro-yığın sayısı $M$'yi büyütmek `1F1B` boru hattı balonunu küçültürken GPU'da hangi başka bellek kalemini büyütür?"
:::
