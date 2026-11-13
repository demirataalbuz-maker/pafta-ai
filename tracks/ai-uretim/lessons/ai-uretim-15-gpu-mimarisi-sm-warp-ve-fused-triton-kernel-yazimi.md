---
id: ai-uretim-15
title: "GPU Donanım Mimarisi (SM, Warp, HBM/SRAM) ve Triton Tarzı Fused Kernel Modeli"
summary: "GPU Streaming Multiprocessor (SM), Warp yürütümü ve HBM/SRAM bellek hiyerarşisi üzerinden Roofline aritmetik yoğunluk analizi ve çok adımlı işlemleri tek SRAM geçişinde birleştiren Fused Kernel modeli."
esleme: ai-uretim-14, ai-uretim-16, ai-temel-08
track: ai-uretim
order: 15
duration_minutes: 40
difficulty: ileri
xp: 320
prerequisites: [ai-uretim-14]
tags: [gpu-architecture, streaming-multiprocessor, warp, roofline-model, triton, kernel-fusion]
---

::: anlat
## Roofline ve fused softmax

Bir GPU işlemi compute kapasitesi veya bellek trafiğiyle sınırlanabilir. Roofline hesabında FLOP ve byte birimlerini aynı ölçekte kullanacak; blok boyutu ve masked padding ile satır bazlı softmax hesaplayacaksın. Python simülasyonundaki trafik sayacı gerçek GPU süresi değildir.

Roofline modelinde peak FLOP/s değerini byte/s değerine bölmek bir hız oranı değil, FLOP/byte biriminde arithmetic-intensity eşiği verir. Donanım değerleri ve precision varsayımı açıkça yazılmalıdır.
Eğer PyTorch'ta masum görünen şu 3 satırlık `Softmax` veya `RMSNorm` kodunu yazarsan:
```python norun
x_max = x.max(dim=-1, keepdim=True)[0]   # 1. Kernel: X'i HBM'den oku, max'ı HBM'e yaz
num = torch.exp(x - x_max)               # 2. & 3. Kernel: Tekrar HBM'den oku, HBM'e yaz
out = num / num.sum(dim=-1, keepdim=True)# 4. & 5. Kernel: Tekrar HBM'den oku, HBM'e yaz!
```
Birden fazla kernel ara tensorların belleğe yazılıp okunmasını artırabilir. GPU’nun bekleme oranı ve gerçek latency ancak profiler/benchmark ile ölçülür.
İşte **OpenAI `Triton`** diliyle bu 5 işlemi tek bir GPU çekirdeğinde birleştirdiğinde (**`Kernel Fusion`**), tensör `HBM`'den çip üstü ultra-hızlı `SRAM` belleğe **yalnızca 1 kez** okunur, tüm işlemler `SRAM` içinde yapılır ve sonuç `HBM`'e **1 kez** yazılır; bellek trafiği azalabilir; gerçek hız kazancı benchmark ile ölçülmelidir.

---

### 1. NVIDIA GPU Donanım Anatomisi: `SM`, `Warp (32 Thread)` ve Bellek Hiyerarşisi

Bir GPU, CPU gibi birkaç güçlü çekirdekten değil, yüzlerce paralel mini-işlemciden (**`Streaming Multiprocessor — SM`**; örneğin H100'de `132 adet SM`) oluşur:

```
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                       NVIDIA H100 GPU PAKETİ                            │
  │   ┌──────────────────────┐   ┌──────────────────────┐                   │
  │   │       SM #0          │   │       SM #131        │   ... (132 SM)    │
  │   │  • Tensor Cores (4x) │   │  • Tensor Cores (4x) │                   │
  │   │  • CUDA Cores (FP32) │   │  • CUDA Cores (FP32) │                   │
  │   │  • Register File     │   │  • Register File     │                   │
  │   │  • 256 KB SRAM / L1  │   │  • 256 KB SRAM / L1  │  (~33 TB/s Hız!)  │
  │   └──────────▲───────────┘   └──────────▲───────────┘                   │
  │              └─────────────┬────────────┘                               │
  │                     [ 50 MB L2 Cache ]                                  │
  │                            ▲                                            │
  │                            │  (3.35 TB/s Darboğaz Hattı!)               │
  │              [ 80 GB HBM3 Ana Bellek (VRAM) ]                           │
  └─────────────────────────────────────────────────────────────────────────┘
```

1. **`Warp` (`32 Thread SIMT`):** GPU'daki en küçük yürütme birimidir. Bir `Warp` içindeki 32 iş parçacığı (`Thread`) aynı anda **tek bir komutu (`Single Instruction, Multiple Threads`)** 32 farklı veri elemanı üzerinde çalıştırır. *(Eğer bir `Warp` içindeki thread'lerin yarısı `if`, diğer yarısı `else` koluna girerse **`Warp Divergence`** oluşur ve hız yarıya düşer!)*
2. **`Roofline Model` ve `Arithmetic Intensity` ($I$):**
   Bir algoritmanın GPU üzerinde işlemciye mi (**`Compute-Bound`**) yoksa belleğe mi (**`Memory-Bound`**) takılacağını **Aritmetik Yoğunluk (`Arithmetic Intensity`)** belirler:
   $$I = \frac{\text{Toplam Matematiksel İşlem (FLOPs)}}{\text{HBM'den Okunan + Yazılan Toplam Bayt (Bytes)}} \quad \left[\frac{\text{FLOP}}{\text{Byte}}\right]$$
   - Donanımın **Kritik Sırt Noktası (`Ridge Point`)**: $I_{\text{kritik}} = \frac{\text{Peak TFLOPS}}{\text{HBM Bandwidth (TB/s)}}$.
   - Örneğin H100 (`BF16`) için $I_{\text{kritik}} = \frac{989}{3.35} \approx \mathbf{295\text{ FLOP/Byte}}$'tır!
   - Eğer yazdığın katmanın aritmetik yoğunluğu $I < 295$ ise (tüm aktivasyonlar, `RMSNorm`, `Softmax`, `RoPE` ve `Batch=1` token üretimi böyledir!), **işlemin tamamen `Memory-Bound`'dur!** Onu hızlandırmanın tek yolu **`Kernel Fusion`** ile `HBM` bayt trafiğini azaltmaktır!

---

### 2. `SPMD` Programlama Modeli ve `Triton` Nasıl Çalışır?

Klasik `CUDA C++` ile çekirdek yazarken `Thread -> Warp -> Shared Memory Bank Conflict -> Synchronization Barrier` detaylarıyla boğuşursun. OpenAI tarafından geliştirilen **`Triton`**, **`SPMD` (`Single Program, Multiple Data` — Blok-Tabanlı Programlama)** paradigmasını kullanır:
- Sen tek bir thread'i değil, bir veri bloğunu (**`Tile / Block`**, örneğin matrisin tek bir satırını) işleyen bir program (`program_id`) yazarsın; `SRAM` yerleşimini ve `Warp` paralelliğini Triton derleyicisi otomatik halleder!

Şimdi saf Python ile hem `Roofline Model` analizini hem de bir GPU'nun `SPMD` blokları halinde paralel (`Fused`) çalışmasını simüle edelim:

```python
def roofline_durumu(flops, bayt_trafigi, tepe_tflops=989.0, bant_tb_sn=3.35):
    yogunluk = flops / bayt_trafigi
    kritik_esik = tepe_tflops / bant_tb_sn  # FLOP / Byte
    ulasilabilir_tflops = min(tepe_tflops, yogunluk * bant_tb_sn)
    rejim = "Compute-Bound" if yogunluk >= kritik_esik else "Memory-Bound"
    return round(yogunluk, 2), round(kritik_esik, 1), rejim, round(ulasilabilir_tflops, 2)

# Örnek 1: Eleman bazlı Fused RMSNorm (Her 2 baytlık BF16 eleman için ~5 FLOP, 2B oku + 2B yaz = 4 Byte)
print("RMSNorm :", roofline_durumu(flops=5, bayt_trafigi=4))
# Örnek 2: Büyük Matris Çarpımı (4096 x 4096 x 4096 BF16 GEMM -> 2*N^3 FLOP, 3*N^2*2 Byte)
n = 4096
print("Büyük GEMM:", roofline_durumu(flops=2 * (n ** 3), bayt_trafigi=3 * (n ** 2) * 2))
```

---

### 3. Gerçek Üretim Kodu: OpenAI `Triton` (`@triton.jit`) ile `Fused Softmax` Çekirdeği

Gerçek bir Frontier model eğitim çatısında (`Unsloth`, `Liger-Kernel`, `vLLM`, `FlashAttention`) kullanılan üretim kalitesinde **`@triton.jit` Fused Softmax** çekirdeğinin birebir kodu şöyledir:

```python norun
import torch
import triton
import triton.language as tl

@triton.jit
def fused_softmax_kernel(
    output_ptr, input_ptr,
    input_row_stride, output_row_stride,
    n_cols,
    BLOCK_SIZE: tl.constexpr,
):
    # 1. SPMD: Her Triton program örneği (SM üzerinde) matrisin TEK BİR SATIRINI üstlenir!
    row_idx = tl.program_id(axis=0)
    row_start_ptr = input_ptr + row_idx * input_row_stride

    # 2. Sütun ofsetlerini [0, 1, ..., BLOCK_SIZE-1] oluştur ve sınır dışı olanları maskele
    col_offsets = tl.arange(0, BLOCK_SIZE)
    input_ptrs = row_start_ptr + col_offsets
    mask = col_offsets < n_cols

    # 3. HBM'den SRAM'e TEK SEFERDE oku! (Maske dışı elemanlara -inf koy ki max ve exp'i etkilemesin)
    row = tl.load(input_ptrs, mask=mask, other=-float("inf"))

    # 4. Tüm işlemler GPU SRAM / Register içinde (HBM'e hiç dokunmadan!) gerçekleşir:
    row_minus_max = row - tl.max(row, axis=0)
    numerator = tl.exp(row_minus_max)
    denominator = tl.sum(numerator, axis=0)
    softmax_output = numerator / denominator

    # 5. Sonucu SRAM'den HBM'e TEK SEFERDE yaz!
    output_row_start_ptr = output_ptr + row_idx * output_row_stride
    output_ptrs = output_row_start_ptr + col_offsets
    tl.store(output_ptrs, softmax_output, mask=mask)

def triton_fused_softmax(x: torch.Tensor) -> torch.Tensor:
    n_rows, n_cols = x.shape
    # BLOCK_SIZE, n_cols'tan büyük veya eşit en küçük 2'nin kuvveti olmalıdır (Warp hizalaması)
    BLOCK_SIZE = triton.next_power_of_2(n_cols)
    y = torch.empty_like(x)
    # Grid = (n_rows,): Her satır için paralel bir Triton programı başlat!
    fused_softmax_kernel[(n_rows,)](
        y, x,
        x.stride(0), y.stride(0),
        n_cols,
        BLOCK_SIZE=BLOCK_SIZE,
    )
    return y
```

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [Triton fused softmax](https://triton-lang.org/main/getting-started/tutorials/02-fused-softmax.html). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: tahmin Kernel Fusion ile HBM Bellek Trafiği Kazancı
Boyutu $N$ eleman olan bir vektör üzerinde sırasıyla 4 ayrı PyTorch işlemi (`y = a + b`, `z = y * c`, `w = exp(z)`, `out = w / d`) çalıştırılıyor.
- **Unfused (Ayrık):** Her işlem girdilerini `HBM`'den okur ve çıktısını `HBM`'e yazar (toplam `9` tensör okuma/yazma geçişi).
- **Fused Triton Kernel:** `a, b, c, d` vektörlerini `HBM`'den birer kez okur (`4` okuma), ara değişkenler (`y, z, w`) yalnızca çip üstü `SRAM/Register`'da yaşar ve `out` `HBM`'e `1` kez yazılır (toplam `5` geçiş).
Aşağıdaki kod `BLOCK_SIZE = next_power_of_2(1000)` değerini ve `HBM` bant genişliği tasarruf oranını hesaplar. Çıktı nedir?

```python
def sonraki_ikinin_kuvveti(n):
    p = 1
    while p < n:
        p *= 2
    return p

blok = sonraki_ikinin_kuvveti(1000)
hizlanma_orani = round(9 / 5, 2)
print(f"Triton_BLOCK_SIZE={blok} | HBM_Hizlanma={hizlanma_orani}x")
```

???

```cikti
Triton_BLOCK_SIZE=1024 | HBM_Hizlanma=1.8x
```
$1000$ sütunlu bir satırı tek bir Triton bloğuna sığdırmak için $1000$'den büyük veya eşit en küçük 2'nin kuvveti olan `1024` (`2^10`) seçilir (`Triton_BLOCK_SIZE=1024`). Ara tensörlerin `HBM`'e yazılıp okunması elendiğinde bellek trafiği 9 geçişten 5 geçişe düşer ve `9 / 5 = 1.8x` doğrudan bant genişliği hızlanması sağlanır.
:::

::: gorev 1 · Roofline Modeli: Arithmetic Intensity ve Memory-Bound vs Compute-Bound Analizi
`roofline_analiz(toplam_flop, toplam_bayt, tepe_tflops, hbm_gb_sn)` işlevini yaz.

Bir GPU çekirdeğinin performans karakteristiğini **Roofline Model** ile analiz edeceksin:
- `toplam_flop`: Çekirdeğin yaptığı toplam kayan nokta işlemi sayısı (`float` veya `int`).
- `toplam_bayt`: Çekirdeğin `HBM` ana bellekten okuduğu + yazdığı toplam bayt miktarı (`float` veya `int`).
- `tepe_tflops`: GPU'nun teorik maksimum işlem gücü (`TeraFLOPS` = $10^{12}\text{ FLOP/sn}$, ör. `989.0`).
- `hbm_gb_sn`: GPU'nun `HBM` bellek bant genişliği (`Gigabyte/sn` = $10^9\text{ Byte/sn}$, ör. `3350.0` GB/s = `3.35` TB/s).

Hesaplanacak değerler:
1. **Aritmetik Yoğunluk (`aritmetik_yogunluk`):** $I = \frac{\text{toplam\_flop}}{\text{toplam\_bayt}}$ ($\text{FLOP/Byte}$).
2. **Kritik Sırt Noktası (`kritik_yogunluk`):**
   $$I_{\text{kritik}} = \frac{\text{tepe\_tflops} \times 10^{12}}{\text{hbm\_gb\_sn} \times 10^9} = \frac{\text{tepe\_tflops} \times 1000.0}{\text{hbm\_gb\_sn}} \quad \left[\frac{\text{FLOP}}{\text{Byte}}\right]$$
3. **Darboğaz Türü (`darbogaz`):** Eğer $I < I_{\text{kritik}}$ ise `"memory-bound"`, aksi halde ($I \ge I_{\text{kritik}}$) `"compute-bound"`.
4. **Ulaşılabilir Maksimum Performans (`etkin_tflops`):**
   $$\text{Etkin TFLOPS} = \min\!\left(\text{tepe\_tflops}, \; I \times \frac{\text{hbm\_gb\_sn}}{1000.0}\right)$$
5. Tüm kayan nokta değerlerini `round(val, 4)` ile yuvarlayarak sözlük döndür.

```starter
def roofline_analiz(toplam_flop, toplam_bayt, tepe_tflops, hbm_gb_sn):
    # KUSURLU BAŞLANGIÇ KODU: Roofline denklemlerini ve darboğaz analizini yapmıyor!
    return {
        "aritmetik_yogunluk": 0.0,
        "kritik_yogunluk": 0.0,
        "darbogaz": "unknown",
        "etkin_tflops": 0.0,
    }

print("Analiz:", roofline_analiz(10_000_000, 1_000_000, tepe_tflops=1000.0, hbm_gb_sn=2000.0))
```

```test
def sozlesme(fn):
    try:
        # Test 1: Memory-bound durum
        # I = 10M / 1M = 10.0 FLOP/Byte
        # I_kritik = 1000 * 1000 / 2000 = 500.0 FLOP/Byte
        # Etkin TFLOPS = min(1000.0, 10.0 * 2.0) = 20.0 TFLOPS
        r1 = fn(10_000_000, 1_000_000, 1000.0, 2000.0)
        if r1 != {
            "aritmetik_yogunluk": 10.0,
            "kritik_yogunluk": 500.0,
            "darbogaz": "memory-bound",
            "etkin_tflops": 20.0,
        }:
            return False

        # Kırılma noktası: I = 500 = I_kritik. Ders sözleşmesinde eşitlik compute-bound sayılır (yogunluk < kritik değil).
        r_esik = fn(500_000_000, 1_000_000, 1000.0, 2000.0)
        if r_esik != {
            "aritmetik_yogunluk": 500.0,
            "kritik_yogunluk": 500.0,
            "darbogaz": "compute-bound",
            "etkin_tflops": 1000.0,
        }:
            return False

        # Tam olmayan oran 4 basamağa yuvarlanır: I = 1/3, kritik = 1.0
        if fn(1_000_000, 3_000_000, 1.0, 1000.0) != {
            "aritmetik_yogunluk": 0.3333,
            "kritik_yogunluk": 1.0,
            "darbogaz": "memory-bound",
            "etkin_tflops": 0.3333,
        }:
            return False

        # Test 2: Compute-bound durum
        # I = 600M / 1M = 600.0 FLOP/Byte >= 500.0 -> compute-bound, etkin_tflops = 1000.0
        r2 = fn(600_000_000, 1_000_000, 1000.0, 2000.0)
        if r2 != {
            "aritmetik_yogunluk": 600.0,
            "kritik_yogunluk": 500.0,
            "darbogaz": "compute-bound",
            "etkin_tflops": 1000.0,
        }:
            return False

        return True
    except Exception:
        return False

ok(sozlesme(roofline_analiz), "Roofline aritmetik yoğunluğu, kritik eşik ve etkin TFLOPS hesabı doğru çalışmalı")

def m_ters_darbogaz(toplam_flop, toplam_bayt, tepe_tflops, hbm_gb_sn):
    r = roofline_analiz(toplam_flop, toplam_bayt, tepe_tflops, hbm_gb_sn)
    r["darbogaz"] = "compute-bound" if r["darbogaz"] == "memory-bound" else "memory-bound"
    return r

def m_tavan_asmasi(toplam_flop, toplam_bayt, tepe_tflops, hbm_gb_sn):
    r = roofline_analiz(toplam_flop, toplam_bayt, tepe_tflops, hbm_gb_sn)
    r["etkin_tflops"] = r["aritmetik_yogunluk"] * (hbm_gb_sn / 1000.0)  # min(tepe_tflops, ...) unutulmuş!
    return r

for ad, mutant in [("darboğaz etiketini ters veren", m_ters_darbogaz), ("tepe TFLOPS tavanını aşan", m_tavan_asmasi)]:
    ok(not sozlesme(mutant), "hatalı çözüm/mutant yakalanmalı: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def roofline_analiz(toplam_flop, toplam_bayt, tepe_tflops, hbm_gb_sn):\n    yogunluk = float(toplam_flop) / float(toplam_bayt)\n    bant_tb_sn = float(hbm_gb_sn) / 1000.0\n    kritik = float(tepe_tflops) / bant_tb_sn\n    darbogaz = 'memory-bound' if yogunluk < kritik else 'compute-bound'\n    etkin = min(float(tepe_tflops), yogunluk * bant_tb_sn)\n    return {'aritmetik_yogunluk': round(yogunluk, 4), 'kritik_yogunluk': round(kritik, 4), 'darbogaz': darbogaz, 'etkin_tflops': round(etkin, 4)}", 'referans', 'exec'), _REF)
_t, _g = _ff(roofline_analiz, _REF['roofline_analiz'], (10000000, 1000000, 1000.0, 2000.0), tohum=2652, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (roofline_analiz): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def roofline_analiz(toplam_flop, toplam_bayt, tepe_tflops, hbm_gb_sn):
    yogunluk = float(toplam_flop) / float(toplam_bayt)
    bant_tb_sn = float(hbm_gb_sn) / 1000.0
    kritik = float(tepe_tflops) / bant_tb_sn
    darbogaz = "memory-bound" if yogunluk < kritik else "compute-bound"
    etkin = min(float(tepe_tflops), yogunluk * bant_tb_sn)

    return {
        "aritmetik_yogunluk": round(yogunluk, 4),
        "kritik_yogunluk": round(kritik, 4),
        "darbogaz": darbogaz,
        "etkin_tflops": round(etkin, 4),
    }
```

```hint
`bant_tb_sn = hbm_gb_sn / 1000.0` dönüşümünü yaparsan `kritik = tepe_tflops / bant_tb_sn` ve `etkin = min(tepe_tflops, yogunluk * bant_tb_sn)` formülleri doğrudan aynı birimde (`TFLOPS` ve `TB/s`) çalışır.
```
:::

::: gorev 2 · Triton Tarzı Blok-Paralel (SPMD) Fused Row-Wise Softmax Simülatörü
`spmd_fused_softmax(matris)` işlevini yaz.

OpenAI `Triton` çekirdeğinin (`fused_softmax_kernel`) çalışma mekanizmasını birebir simüle edeceksin:
- `matris`: Boyutu `n_rows x n_cols` olan iki boyutlu liste (`list[list[float]]`).

Kurallar:
1. Girdi matrisini değiştirme. Sütun sayısı `n_cols` için Triton'un `BLOCK_SIZE = next_power_of_2(n_cols)` değerini bul ($n\_cols \le 1$ ise `1`, aksi halde $2^k \ge n\_cols$ olan en küçük 2'nin kuvveti).
2. Her satır (`program_id = 0 .. n_rows - 1`) için:
   - Uzunluğu `BLOCK_SIZE` olan bir `sram_tampon` oluştur: İlk `n_cols` elemanı satırdaki gerçek verilerdir (`mask = True`), geri kalan `BLOCK_SIZE - n_cols` dolgu (`padding`) elemanı ise **`float("-inf")`** (`mask = False`) olarak yüklenir!
   - Tampon üzerinde kararlı Softmax (`m = max(sram_tampon)`, `exp(v - m) / sum(exp)`) hesapla. (Dolgu elemanları `-inf` olduğu için `exp(-inf) == 0.0` olur ve toplamı hiç bozmaz!).
   - Sonuçtan yalnız maskesi `True` olan ilk `n_cols` elemanı (`round(val, 6)` ile yuvarlayarak) çıktı satırı olarak sakla.
3. Sonuçta şu sözlüğü döndür:
   - `"block_size"`: `int`
   - `"maskeli_dolgu_sayisi"`: Satır başına eklenen `-inf` dolgu sayısı (`BLOCK_SIZE - n_cols`)
   - `"hbm_okuma_yazma_gecisi"`: Fused çekirdek her satırı 1 kez okuyup 1 kez yazdığı için sabit `2` tam sayısı
   - `"cikti"`: `n_rows x n_cols` boyutundaki Softmax matrisi

```starter
def spmd_fused_softmax(matris):
    # KUSURLU BAŞLANGIÇ KODU: Power-of-2 blok hizalaması ve maskeli Fused Softmax yapmıyor!
    return {
        "block_size": 0,
        "maskeli_dolgu_sayisi": 0,
        "hbm_okuma_yazma_gecisi": 0,
        "cikti": [list(satir) for satir in matris],
    }

print("Triton Simülasyon:", spmd_fused_softmax([[1.0, 2.0, 3.0], [0.0, 0.0, 0.0]]))
```

```test
import copy
import math

def sozlesme(fn):
    try:
        m = [[1.0, 2.0, 3.0], [10.0, 10.0, 10.0]]  # 2 x 3 -> BLOCK_SIZE = 4, dolgu = 1
        mk = copy.deepcopy(m)
        r = fn(m)
        if m != mk or not isinstance(r, dict):
            return False
        if r.get("block_size") != 4 or r.get("maskeli_dolgu_sayisi") != 1:
            return False
        if r.get("hbm_okuma_yazma_gecisi") != 2:
            return False

        e1, e2, e3 = math.exp(-2.0), math.exp(-1.0), 1.0
        s = e1 + e2 + e3
        beklenen_0 = [round(e1 / s, 6), round(e2 / s, 6), round(e3 / s, 6)]
        beklenen_1 = [round(1.0 / 3.0, 6)] * 3
        if r.get("cikti") != [beklenen_0, beklenen_1]:
            return False

        # Sütun sayısı 5 olduğunda BLOCK_SIZE = 8, dolgu = 3 olmalı
        r2 = fn([[0.0] * 5])
        if r2.get("block_size") != 8 or r2.get("maskeli_dolgu_sayisi") != 3:
            return False
        if r2.get("cikti") != [[0.2] * 5]:
            return False

        # Sütun sayısı zaten 2'nin kuvveti: dolgu yok. Tek sütun: BLOCK_SIZE = 1.
        r3 = fn([[1.0, 2.0, 3.0, 4.0]])
        if r3.get("block_size") != 4 or r3.get("maskeli_dolgu_sayisi") != 0 or r3.get("cikti") != [[0.032059, 0.087144, 0.236883, 0.643914]]:
            return False
        r4 = fn([[5.0], [-7.0]])
        if r4.get("block_size") != 1 or r4.get("maskeli_dolgu_sayisi") != 0 or r4.get("cikti") != [[1.0], [1.0]]:
            return False

        # Sayısal kararlılık: maksimumu çıkarmak exp taşmasını önler; sonuç [0, 1, 2] ile aynıdır.
        r5 = fn([[1000.0, 1001.0, 1002.0]])
        if r5.get("cikti") != [[0.090031, 0.244728, 0.665241]]:
            return False

        return True
    except Exception:
        return False

ok(sozlesme(spmd_fused_softmax), "Triton BLOCK_SIZE (2'nin kuvveti), -inf maskeleme ve satır bazlı Softmax doğru çalışmalı")

def m_dolgu_sifir_koyan(matris):
    # Dolguya -inf yerine 0.0 koyan hatalı mutant (exp(0)=1 olduğu için paydayı bozar!)
    r = spmd_fused_softmax(matris)
    r["cikti"][0][0] = 0.99
    return r

def m_block_yanlis(matris):
    r = spmd_fused_softmax(matris)
    r["block_size"] = len(matris[0])
    return r

for ad, mutant in [("maske dışına -inf yerine 0 koyan", m_dolgu_sifir_koyan), ("BLOCK_SIZE değerini 2'nin kuvvetine yuvarlamayan", m_block_yanlis)]:
    ok(not sozlesme(mutant), "hatalı çözüm/mutant yakalanmalı: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef spmd_fused_softmax(matris):\n    n_cols = len(matris[0])\n    block_size = 1\n    while block_size < n_cols:\n        block_size *= 2\n    dolgu_sayisi = block_size - n_cols\n    cikti = []\n    for satir in matris:\n        sram_row = list(satir) + [float('-inf')] * dolgu_sayisi\n        m = max(sram_row)\n        exps = [math.exp(v - m) for v in sram_row]\n        payda = sum(exps)\n        softmax_row = [round(exps[i] / payda, 6) for i in range(n_cols)]\n        cikti.append(softmax_row)\n    return {'block_size': block_size, 'maskeli_dolgu_sayisi': dolgu_sayisi, 'hbm_okuma_yazma_gecisi': 2, 'cikti': cikti}", 'referans', 'exec'), _REF)
_t, _g = _ff(spmd_fused_softmax, _REF['spmd_fused_softmax'], ([[1.0, 2.0, 3.0], [0.0, 0.0, 0.0]],), tohum=2987, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (spmd_fused_softmax): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def spmd_fused_softmax(matris):
    n_cols = len(matris[0])
    block_size = 1
    while block_size < n_cols:
        block_size *= 2
    dolgu_sayisi = block_size - n_cols

    cikti = []
    for satir in matris:
        # HBM -> SRAM maskeli yükleme (maske dışı elemanlar -inf)
        sram_row = list(satir) + [float("-inf")] * dolgu_sayisi
        m = max(sram_row)
        exps = [math.exp(v - m) for v in sram_row]
        payda = sum(exps)
        softmax_row = [round(exps[i] / payda, 6) for i in range(n_cols)]
        cikti.append(softmax_row)

    return {
        "block_size": block_size,
        "maskeli_dolgu_sayisi": dolgu_sayisi,
        "hbm_okuma_yazma_gecisi": 2,
        "cikti": cikti,
    }
```

```hint
`block_size = 1` başlatıp `while block_size < n_cols: block_size *= 2` ile en yakın 2'nin kuvvetini bul. Her satırın sonuna `block_size - n_cols` adet `float("-inf")` ekleyip Softmax aldıktan sonra ilk `n_cols` elemanı kaydet.
```
:::

::: anlat Gerçek deney: Bu makinenin gerçek roofline'ı ve fused softmax'ın ölçülen kazancı
Final roofline'ı bu makinede **ölçer** (GPU varsa GPU'da, yoksa CPU'da):

- **Tavanlar:** büyük bir fp32 matris çarpımının süresinden ulaşılabilen tepe TFLOPS, büyük bir kopyadan bellek bant genişliği (GB/s) ölçülür. Üretici değeri değil, bu makinenin gerçekten verdiği değerlerdir.
- **Dört işlem:** vektör toplama, satır softmax, GEMV (matris × vektör) ve büyük matmul. Her birinin FLOP ve bayt sayısı ile ölçülen tavanlar senin `roofline_analiz` işlevine verilir. İşlev her işlem için darboğazı ve ulaşılabilir TFLOPS'u tahmin eder; aynı işlemlerin ölçülen süresinden gerçek TFLOPS hesaplanır ve tahminle karşılaştırılır.
- **Fused softmax:** SmolLM2'nin 2. katmanındaki gerçek dikkat skorları (sütun sayısı 2'nin kuvveti olmayacak şekilde) senin `spmd_fused_softmax` işlevine verilir, sonuç `torch.softmax` ile karşılaştırılır. Sonra büyük bir matriste tek çekirdekli `torch.softmax` ile max, çıkarma, exp, toplam ve bölmeden oluşan ayrık softmax'ın süresi ölçülür: ayrık sürüm ara sonuçları belleğe yazıp tekrar okur.

**Güvenlik yönü — başlatılmamış bellekten veri sızıntısı:** Bir çekirdek ya da kütüphane çıktısını sıfırlamadan ayırırsa önceki verinin kalıntısı okunabilir (LeftoverLocals ve benzeri açıklar). 16 MB'lık bir 'gizli' tampon cihazda yazılıp serbest bırakılır; ardından `torch.empty` ile aynı boyutta tampon alınır ve içindeki desen aranır. CUDA'nın önbellekli ayırıcısı aynı bloğu geri verir ve gizli verinin tamamı okunur; `torch.zeros` temizdir. CPU'da işletim sistemi büyük ayırmaları sıfırlanmış sayfalarla verir.

Kabul: iki işlevin farksal taramayı geçmesi; vektör toplama, softmax ve GEMV'nin memory-bound, matmul'ün compute-bound sınıflanması; memory-bound işlemlerde ölçülen/tahmin oranının 0.25–2 arasında olması; gerçek skorlarda softmax'ın torch ile aynı ve dolgu sayısının doğru olması. Ayrıca torch.zeros temiz olmalı; CUDA'da torch.empty serbest bırakılan tampondaki veriyi geri vermelidir.

**Kanıt dosyasını oku:** `tepe_tflops_olculen`, `bant_gb_sn_olculen`, `kritik_yogunluk`, `islemler`, `fused_hizlanma`. Soru 1: Kritik yoğunluk ~26 FLOP/bayt ise bir transformer'da hangi işlemler bunun altında kalır? Soru 2: GEMV neden memory-bound ve LLM'de tek kullanıcılı üretim (batch 1) bu yüzden neden yavaştır? Soru 3: Ayrık softmax'ın kaç kat yavaş olduğunu bellek geçişi sayısıyla açıklayabilir misin?
:::

::: gorev Gerçek deney · Bu makinede ölçülen roofline ve gerçek dikkat skorlarında fused softmax
Önceki görevlerdeki `roofline_analiz`, `spmd_fused_softmax` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 240
```
```starter
import ai_lab
def roofline_analiz(toplam_flop, toplam_bayt, tepe_tflops, hbm_gb_sn):
    return {'aritmetik_yogunluk': 0.0, 'kritik_yogunluk': 0.0, 'darbogaz': 'unknown', 'etkin_tflops': 0.0}

def spmd_fused_softmax(matris):
    return {'block_size': 0, 'maskeli_dolgu_sayisi': 0, 'hbm_okuma_yazma_gecisi': 0, 'cikti': [list(satir) for satir in matris]}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_15 as D
    D.goster(roofline_analiz, spmd_fused_softmax)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_sure', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
roofline_analiz = need("roofline_analiz")
spmd_fused_softmax = need("spmd_fused_softmax")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def roofline_analiz(toplam_flop, toplam_bayt, tepe_tflops, hbm_gb_sn):\n    yogunluk = float(toplam_flop) / float(toplam_bayt)\n    bant_tb_sn = float(hbm_gb_sn) / 1000.0\n    kritik = float(tepe_tflops) / bant_tb_sn\n    darbogaz = 'memory-bound' if yogunluk < kritik else 'compute-bound'\n    etkin = min(float(tepe_tflops), yogunluk * bant_tb_sn)\n    return {'aritmetik_yogunluk': round(yogunluk, 4), 'kritik_yogunluk': round(kritik, 4), 'darbogaz': darbogaz, 'etkin_tflops': round(etkin, 4)}\n\nimport math\n\ndef spmd_fused_softmax(matris):\n    n_cols = len(matris[0])\n    block_size = 1\n    while block_size < n_cols:\n        block_size *= 2\n    dolgu_sayisi = block_size - n_cols\n    cikti = []\n    for satir in matris:\n        sram_row = list(satir) + [float('-inf')] * dolgu_sayisi\n        m = max(sram_row)\n        exps = [math.exp(v - m) for v in sram_row]\n        payda = sum(exps)\n        softmax_row = [round(exps[i] / payda, 6) for i in range(n_cols)]\n        cikti.append(softmax_row)\n    return {'block_size': block_size, 'maskeli_dolgu_sayisi': dolgu_sayisi, 'hbm_okuma_yazma_gecisi': 2, 'cikti': cikti}", 'referans', 'exec'), _REF)
_t, _g = _ff(roofline_analiz, _REF['roofline_analiz'], (10000000, 1000000, 1000.0, 2000.0), tohum=2652, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (roofline_analiz): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(spmd_fused_softmax, _REF['spmd_fused_softmax'], ([[1.0, 2.0, 3.0], [0.0, 0.0, 0.0]],), tohum=2987, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (spmd_fused_softmax): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
kontrol(roofline_analiz(1, 3, 100.0, 777.7) == _REF['roofline_analiz'](1, 3, 100.0, 777.7), "roofline 4 basamak yuvarlama korunmalı")
kontrol(spmd_fused_softmax([[1.0]]) == _REF['spmd_fused_softmax']([[1.0]]), "tek sütun block_size=1 sınırı korunmalı")
kontrol(spmd_fused_softmax([[1000.0, 999.0]]) == _REF['spmd_fused_softmax']([[1000.0, 999.0]]), "büyük logit kararlılığı korunmalı")
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_15 as D
try: r = D.deney(roofline_analiz, spmd_fused_softmax)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['siniflama_dogru'], 'dört gerçek işlemin darboğazı doğru sınıflandı (3 memory-bound, matmul compute-bound)')
kontrol(r['tahmin_tutarli'], 'memory-bound işlemlerde ölçülen performans roofline tahmininin 0.25–2 katı arasında')
kontrol(r['softmax_ayni'], 'fused softmax gerçek dikkat skorlarında torch.softmax ile aynı, dolgu doğru')
kontrol(r['zeros_temiz'] and r['empty_sizdiriyor'] is not False, "torch.zeros temiz; CUDA'da torch.empty serbest bırakılan gizli veriyi geri verdi")
ai_lab.kanit_yaz("ai-uretim-15-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-15", "deney": r})
```
```solution
import ai_lab
def roofline_analiz(toplam_flop, toplam_bayt, tepe_tflops, hbm_gb_sn):
    yogunluk = float(toplam_flop) / float(toplam_bayt)
    bant_tb_sn = float(hbm_gb_sn) / 1000.0
    kritik = float(tepe_tflops) / bant_tb_sn
    darbogaz = 'memory-bound' if yogunluk < kritik else 'compute-bound'
    etkin = min(float(tepe_tflops), yogunluk * bant_tb_sn)
    return {'aritmetik_yogunluk': round(yogunluk, 4), 'kritik_yogunluk': round(kritik, 4), 'darbogaz': darbogaz, 'etkin_tflops': round(etkin, 4)}

import math

def spmd_fused_softmax(matris):
    n_cols = len(matris[0])
    block_size = 1
    while block_size < n_cols:
        block_size *= 2
    dolgu_sayisi = block_size - n_cols
    cikti = []
    for satir in matris:
        sram_row = list(satir) + [float('-inf')] * dolgu_sayisi
        m = max(sram_row)
        exps = [math.exp(v - m) for v in sram_row]
        payda = sum(exps)
        softmax_row = [round(exps[i] / payda, 6) for i in range(n_cols)]
        cikti.append(softmax_row)
    return {'block_size': block_size, 'maskeli_dolgu_sayisi': dolgu_sayisi, 'hbm_okuma_yazma_gecisi': 2, 'cikti': cikti}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_15 as D
    D.goster(roofline_analiz, spmd_fused_softmax)
```
```hint
İki görevin çözümlerini olduğu gibi buraya koy. Süreler makineye göre değişir; kabul kontrolleri mutlak değerlere değil oranlara bakar.
```
:::

::: anlat Sınır
Görevler roofline modeliyle memory-bound/compute-bound ayrımını ve Triton tarzı blok paralel softmax'ı Python'da simüle eder; final adım tavanları bu makinede ölçer ve tahmini gerçek sürelerle karşılaştırır (çekirdek yazılmaz). Görev 1 ve 2'de tavanlar girdi olarak verilen sayılardır. Son adımdaki tavanlar ise bu makinede ölçülen en iyi değerlerdir, üretici belgesindeki tepe değerler değildir: tepe TFLOPS fp32 matris çarpımıyla, TF32 kapalıyken (`torch.backends.cuda.matmul.allow_tf32 = False`) ölçülür; Tensor Core'ların TF32/fp16 yolları bu ölçüme girmez. Bu derste gerçek bir Triton çekirdeği yazılmaz ya da derlenmez; Triton'ın blok-paralel modeli Python'da taklit edilir. Gerçek çekirdekler önbellek, occupancy ve bellek erişim düzeni yüzünden ölçülen tavana da her zaman ulaşmaz. Fused softmax tek bir satır SRAM'e sığdığında hızlıdır; çok uzun satırlarda online birleştirme gerekir. Ölçüm yapılmadan varılan 'darboğaz' sonucu yalnız bir tahmindir; profiler (Nsight Compute) ile doğrulanmalıdır.

Kaynaklar: [Williams vd. 2009 - Roofline: an insightful visual performance model for multicore architectures](https://doi.org/10.1145/1498765.1498785), [Tillet vd. 2019 - Triton: an intermediate language and compiler for tiled neural network computations](https://doi.org/10.1145/3315508.3329973), [Triton - Fused Softmax öğreticisi](https://triton-lang.org/main/getting-started/tutorials/02-fused-softmax.html).
:::

::: dusun
Bir LLM'in son katmanında gizli durum boyutu $D = 4096$, sözlük boyutu ise $V = 128,256$'dır. Eğitim sırasında sekans uzunluğu $B \times S = 32,768$ token olduğunda, eğer tüm `logits = hidden @ W_vocab` matrisini ($32,768 \times 128,256$) `FP32` olarak oluşturup ardından `CrossEntropyLoss` çağırırsan **yalnızca bu tek `logits` tensörü GPU'da `16.8 GB VRAM` kaplar!**

**`Liger-Kernel` ve `Unsloth`** kütüphanelerinin kullandığı **`Fused Linear Cross-Entropy (Chunked / Tiled Triton Kernel)`** bu `16.8 GB`'lık bellek patlamasını nasıl `0 GB` ek belleğe indirir? `logits` matrisinin tamamını `HBM` bellekte hiç oluşturmadan, `hidden` parçaları üzerinde hem `MatMul` hem `LogSumExp` hem de backpropagation gradyanı $d(\text{logits})$ hesabını `SRAM` içinde birleştirmenin mimari mantığını açıkla.
:::

::: ozet
Roofline modelinde peak FLOP/s değerini byte/s değerine bölmek bir hız oranı değil, FLOP/byte biriminde arithmetic-intensity eşiği verir. Donanım değerleri ve precision varsayımı açıkça yazılmalıdır.
- Standart PyTorch'ta ardışık eleman bazlı işlemler (`RMSNorm`, `Softmax`, `SwiGLU`, `RoPE`) her adımda `HBM`'e yazılıp okunduğu için bellek veri yolunu boğar.
- **OpenAI `Triton` (`@triton.jit`)**, **`SPMD`** modeliyle veriyi 2'nin kuvveti boyutundaki bloklar (`BLOCK_SIZE`) halinde maskeli (`tl.load(..., mask=mask, other=-inf)`) olarak çip üstü **`SRAM`** belleğe çeker ve tüm ara işlemleri tek çekirdekte (**`Kernel Fusion`**) tamamlar. Kazancın büyüklüğü işleme ve donanıma bağlıdır; bu derste son adımda bu makinede ölçülür.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Hesap değil bellek duvarı (30 sn).** "Modern GPU'larda Tensor Core aritmetik hızı HBM bellek bant genişliğinden yüzlerce kat hızlıdır; `RMSNorm`, `Softmax` veya `SwiGLU` gibi noktasal işlemler FLOP değil HBM okuma-yazma trafiğine takılır (`Memory-Bound`)."
2. **Roofline aritmetik yoğunluğu (30 sn).** "İşlem başına düşen $\text{FLOP} / \text{Byte}$ oranı donanımın tepe sırt noktasının (`Ridge Point`) altındaysa daha hızlı çarpıcı eklemek süreyi kısaltmaz; tek çare HBM gidiş-geliş baytını düşürmektir."
3. **Kernel Fusion ve SRAM (35 sn).** "Triton tarzı birleştirilmiş çekirdekler (`Fused Kernels`) girdiyi HBM'den SM üstü hızlı SRAM'e bir kez çeker, ara tensörleri HBM'ye hiç yazmadan tüm adımları kütüklerde tamamlayıp yalnız son çıktıyı yazar."
4. **Soru (25 sn).** "Çok kiracılı bir GPU sunucusunda aynı donanım üzerinde paylaşımlı SRAM ve L2 önbellek kullanıldığında komşu kiracıya hangi yan kanal (`side-channel`) veya artık bellek riski doğabilir?"
:::
