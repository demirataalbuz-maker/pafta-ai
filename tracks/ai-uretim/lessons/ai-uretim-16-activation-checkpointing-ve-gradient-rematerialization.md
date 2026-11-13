---
id: ai-uretim-16
title: "Activation Checkpointing (Gradient Rematerialization) ve Bellek-Hesaplama Optimizasyonu"
summary: "Derin Transformer eğitiminde VRAM'i dolduran ara aktivasyonları saklamak yerine geri yayılımda yeniden hesaplayan (Gradient Rematerialization) tam, blok-kökü ve seçici (Selective) Activation Checkpointing ödünleşimi."
esleme: ai-uretim-14, ai-uretim-15, ai-temel-09
track: ai-uretim
order: 16
duration_minutes: 35
difficulty: ileri
xp: 290
prerequisites: [ai-uretim-15]
tags: [activation-checkpointing, gradient-rematerialization, vram-optimization, selective-checkpointing, pytorch]
---

::: anlat
## Activation checkpointing

Training sırasında bazı ara activation değerlerini saklamayıp backward sırasında yeniden hesaplayabiliriz. Bu derste belleği azaltmanın ek hesap maliyetini ve checkpoint seçimini modelleyeceksin. Activation checkpointing, bir training koşusunu diske kaydedip yeniden başlatan checkpoint/resume işlemiyle aynı değildir.

Kalan **`52 GB`** belleği kim yedi?
1. derste (`Autograd`) kanıtladığımız denklemi hatırla: Bir doğrusal katmanda $Y = X \cdot W$ işleminin ağırlık gradyanı **$dW = X^T \cdot dY$**'dir!
Yani `Backward Pass` (backpropagation) sırasında $dW$'yi hesaplayabilmek için, `Forward Pass` sırasında üretilen **tüm katmanların ara çıktı tensörlerini (`Activations` $X_1, X_2, \dots, X_L$)** son katmana ulaşıp geri dönene kadar GPU `HBM` belleğinde canlı tutmak zorundasın!

---

### 1. `Activation Checkpointing` (`Gradient Rematerialization` — Chen et al., 2016)

Peki $L = 64$ katmanlı bir Transformer'da **tüm** ara aktivasyonları saklamak yerine, yalnızca belirli sınır taşlarını (**Checkpoints**) saklasak ve aradaki katmanların aktivasyonlarını `Forward Pass` sırasında **hemen silsek (`Drop / Free`)** ne olur?
- `Backward Pass` sırası o katmana geldiğinde, en yakın kayıtlı `Checkpoint` girdisinden başlayarak o katmanın ileri geçişini **anında yeniden hesaplarız (`Rematerialization / Recomputation`)**, $dW$ gradyanını alırız ve tekrar sileriz!

```
  1. STANDART BACKPROP (Bellek: O(L) = 64 Katman Aktivasyonu Saklanır, Ek Hesaplama: %0)
     [A1] ──► [A2] ──► [A3] ──► [A4] ──► ... ──► [A64]  (Hepsi HBM'de duruyor -> OOM!)

  2. √L SEGMENT CHECKPOINTING (Bellek: O(√L), Örneğin Her 8 Katmanda 1 Kayıt!)
     [A1*] ──► (sil) ──► (sil) ──► [A9*] ──► (sil) ──► ...  (Yalnız * olanlar HBM'de!)
       └─── Backward sırasında A1*'den A2..A8 anında yeniden hesaplanır (Rematerialize)!

  3. FULL LAYER CHECKPOINTING (Her Transformer Bloğu Girişi Kaydedilir, Blok İçi Silinir)
     Maliyet: Yalnızca +%33 FLOPs (1 ek Forward Pass) karşılığında %70-%85 VRAM Tasarrufu!
```

#### 📐 Neden Ekstra Maliyet Yalnızca `+%33 FLOPs` Kadardır?
Bir eğitim adımında:
- **Forward Pass:** `1 birim` hesaplama (`1x FLOPs`),
- **Backward Pass:** Hem $dX = dY \cdot W^T$ hem de $dW = X^T \cdot dY$ olmak üzere **2 matris çarpımı** yaptığı için `2 birim` hesaplama (`2x FLOPs`) harcar. Toplam = **`3 birim FLOPs`**.
- `Full Activation Checkpointing` yaptığımızda backpropagation sırasında `Forward Pass`'i bir kez daha çalıştırırız (`+1 birim FLOPs`). Böylece toplam maliyet `3` birimden `4` birime çıkar ($\frac{4 - 3}{3} = \mathbf{+33.3\%}$ ek işlem)! **`%33` ek süre karşılığında aktivasyon belleğini `5 ila 10 kat` küçültmek**, modern LLM eğitiminin en kârlı mühendislik takasıdır!

---

### 2. `Selective Activation Checkpointing` (Megatron-LM / Llama-3 Stratejisi)

Her katmanı körü körüne silip yeniden hesaplamak (`Full Checkpointing`) zorunda mıyız? **Hayır!**
NVIDIA **Megatron-LM** araştırmacıları (Korthikanti et al.) bir Transformer bloğunun içindeki işlemleri incelediğinde çarpıcı bir asimetri keşfetti:
1. **`MatMul` (`Linear Projections` $Q, K, V, O, W_{\text{gate}}, W_{\text{up}}, W_{\text{down}}$):**
   - Yeniden hesaplaması **çok pahalıdır** (tüm `FLOPs` bütçesinin `%80`'i buradadır!), ama çıktıları görece makul yer kaplar.
2. **`Non-MatMul` (`Softmax`, `Dropout`, `SwiGLU SiLU * Up`, `RoPE`):**
   - Yeniden hesaplaması **neredeyse bedavadır** (`FLOPs` bütçesinin yalnızca `%2`'si!), **AMA** devasa boyutlu ara aktivasyon belleği (`VRAM`'in `%60`'ından fazlası!) harcarlar!

> **Altın Mühendislik Kuralı (`Selective Checkpointing / Cost-per-Byte Optimization`):**
> **Birim bellek başına yeniden hesaplama maliyeti ($\frac{\text{FLOPs}}{\text{Bytes}}$) DÜŞÜK** olan işlemleri (yani çok yer kaplayıp çok ucuza yeniden hesaplanan `SwiGLU`, `Attention Softmax`, `RMSNorm` çıktılarını) **sil ve yeniden hesapla (`Recompute`)**; yeniden hesaplaması çok ağır olan `Linear MatMul` çıktılarını ise **bellekte sakla (`Save`)**! Böylece yalnızca `+%5` ek `FLOPs` ödeyerek belleğin `%60`'ını kurtarırsın!

Şimdi saf Python ile `Standard`, `Sqrt-L` ve `Full` Checkpointing bellek/hesaplama profillerini karşılaştıralım:

```python
import math

def checkpoint_profil_karsilastir(katman_sayisi, blok_ici_islem_sayisi, islem_bellek_mb):
    # Standart: L katmanın her birindeki K işlemin tamamı saklanır
    std_bellek = katman_sayisi * blok_ici_islem_sayisi * islem_bellek_mb
    # Full Blok Checkpointing: Yalnız her katmanın girişi (L adet) + aktif katmanın K işlemi
    full_bellek = (katman_sayisi + blok_ici_islem_sayisi) * islem_bellek_mb
    # Sqrt(L) Checkpointing: sqrt(L) adet ana sınır taşı + 1 segmentin iç katmanları
    seg = int(math.isqrt(katman_sayisi))
    sqrt_bellek = (seg + seg * blok_ici_islem_sayisi) * islem_bellek_mb
    return {"Standart_MB": std_bellek, "Full_Blok_MB": full_bellek, "Sqrt_Segment_MB": sqrt_bellek}

print("64 Katmanlı Model Aktivasyon Belleği:", checkpoint_profil_karsilastir(64, 6, 100))
```

---

### 3. Gerçek Üretim Kodu: PyTorch `torch.utils.checkpoint` ve `Selective Policy`

Modern PyTorch 2.x üretim kodunda hem standart blok bazlı `checkpoint(..., use_reentrant=False)` hem de `Selective Activation Checkpointing` (`create_selective_checkpoint_contexts`) şöyle uygulanır:

```python norun
import torch
import torch.nn as nn
from torch.utils.checkpoint import checkpoint, create_selective_checkpoint_contexts, CheckpointPolicy

# 1. Seçici Politika (Selective Policy): Pahalı MatMul (mm/addmm) işlemlerini HBM'de SAKLA,
#    ucuz ama çok yer kaplayan eleman bazlı (SwiGLU, RoPE, Norm) işlemleri YENİDEN HESAPLA!
def selective_matmul_save_policy(ctx, func, *args, **kwargs):
    if func in (torch.ops.aten.mm.default, torch.ops.aten.addmm.default, torch.ops.aten.bmm.default):
        return CheckpointPolicy.MUST_SAVE
    return CheckpointPolicy.PREFER_RECOMPUTE

class CheckpointedTransformerBlock(nn.Module):
    def __init__(self, layer_module: nn.Module, use_selective: bool = True):
        super().__init__()
        self.layer = layer_module
        self.use_selective = use_selective

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if not self.training:
            return self.layer(x)

        # Kritik Üretim Standardı: Modern PyTorch'ta her zaman use_reentrant=False kullanılır!
        if self.use_selective:
            return checkpoint(
                self.layer, x,
                use_reentrant=False,
                context_fn=lambda: create_selective_checkpoint_contexts(selective_matmul_save_policy),
            )
        return checkpoint(self.layer, x, use_reentrant=False)
```

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [PyTorch activation checkpointing](https://docs.pytorch.org/docs/stable/checkpoint.html). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: tahmin √L Segmentli Activation Checkpointing Bellek Kazancı
$L = 100$ katmanlı bir derin ağda her katmanın aktivasyonu `200 MB` yer kaplıyor.
- Standart eğitimde $100 \times 200 = 20,000\text{ MB}$ (`20 GB`) aktivasyon belleği gerekir.
- Chen et al. (2016) **`$\sqrt{L}$ Segment Checkpointing`** yönteminde ise ağ $\sqrt{100} = 10$ katmanlık $10$ segmente bölünür: İleri geçişte yalnız $10$ segment başı kaydedilir, geri geçişte ise aktif segmentin $10$ katmanı yeniden hesaplanır (tepe bellek: $(10 + 10 - 1) = 19$ katman veya yaklaşık $2\sqrt{L} = 20$ katman).
Aşağıdaki kod $2\sqrt{L}$ formülüyle tepe belleği ve küçülme oranını hesaplar. Çıktı nedir?

```python
import math
L = 100
katman_mb = 200
standart_mb = L * katman_mb
sqrt_mb = 2 * int(math.isqrt(L)) * katman_mb
oran = round(standart_mb / sqrt_mb, 1)
print(f"Standart={standart_mb}MB | SqrtCheckpointing={sqrt_mb}MB | Tasarruf={oran}x")
```

???

```cikti
Standart=20000MB | SqrtCheckpointing=4000MB | Tasarruf=5.0x
```
$L = 100$ katman için standart aktivasyon belleği `20,000 MB` iken, $2\sqrt{100} = 20$ katmanlık tepe bellekle çalışan $\sqrt{L}$ Checkpointing yalnızca `4,000 MB` harcar ve tam `5.0x` bellek tasarrufu sağlar.
:::

::: gorev 1 · Katmanlı Ağda Standart, Full-Block ve √L Activation Checkpointing Hesabı
`checkpoint_bellek_hesapla(katman_sayisi, alt_islem_sayisi, islem_bellek_mb)` işlevini yaz.

$L$ katmandan oluşan bir Transformer modelinde her katmanın içinde $K$ adet alt işlem (`alt_islem_sayisi`, örn. `RMSNorm`, `QKV`, `Softmax`, `SwiGLU` vb.) bulunmaktadır ve her alt işlemin çıktısı `islem_bellek_mb` kadar GPU belleği tüketmektedir.

Üç farklı mod için **Tepe Aktivasyon Belleği (`MB`)** ve **Toplam Forward İşi Çarpanı (`forward_carpani`)** hesaplayacaksın:
1. **`"standart"` (Checkpointing Yok):**
   - Bellek: Tüm $L$ katmanın tüm $K$ alt işlemi saklanır: $L \times K \times \text{islem\_bellek\_mb}$.
   - Forward Çarpanı: `1.0` (yalnızca normal ileri geçiş yapılır).
2. **`"full_block"` (Her Katmanın Girişi Kaydedilir, İç İşlemler Geri Yayılımda Yeniden Hesaplanır):**
   - Bellek: $L$ katmanın yalnız giriş sınır taşı ($L \times 1$) + backpropagation sırasında o an yeniden hesaplanan **tek bir aktif katmanın** kalan $(K - 1)$ iç işlemi: $(L + K - 1) \times \text{islem\_bellek\_mb}$.
   - Forward Çarpanı: `2.0` (her katman ileri geçişte 1 kez, geri geçişte 1 kez olmak üzere toplam 2 kez hesaplanır).
3. **`"sqrt_segment"` ($\sqrt{L}$ Katmanlık Segment Sınır Taşları):**
   - Segment boyutu $S = \lfloor \sqrt{L} \rfloor$ (`math.isqrt(katman_sayisi)`) ve sınır taşı sayısı $C = \lceil L / S \rceil$ (`math.ceil(katman_sayisi / S)`).
   - Bellek: $C$ adet segment giriş taşı ($C \times 1$) + geri yayılımda aktif olan tek bir segmentin tüm iç işlemleri ($S \times K$): $(C + S \times K) \times \text{islem\_bellek\_mb}$.
   - Forward Çarpanı: `2.0`.

Tüm bellek değerlerini `round(val, 4)` ile yuvarlayarak ve `"full_block_tasarruf_orani": round(standart_bellek / full_block_bellek, 4)` alanını ekleyerek sözlük döndür.

```starter
def checkpoint_bellek_hesapla(katman_sayisi, alt_islem_sayisi, islem_bellek_mb):
    # KUSURLU BAŞLANGIÇ KODU: Checkpointing bellek formüllerini hesaplamadan sıfır döndürüyor!
    return {
        "standart_mb": 0.0,
        "full_block_mb": 0.0,
        "sqrt_segment_mb": 0.0,
        "full_block_tasarruf_orani": 1.0,
    }

print("Bellek Analizi:", checkpoint_bellek_hesapla(36, 6, 50.0))
```

```test
def sozlesme(fn):
    try:
        # L = 36, K = 6, mb = 50.0
        # standart_mb = 36 * 6 * 50 = 10800.0
        # full_block_mb = (36 + 6 - 1) * 50 = 41 * 50 = 2050.0
        # S = isqrt(36) = 6, C = ceil(36/6) = 6 -> sqrt_segment_mb = (6 + 6*6) * 50 = 42 * 50 = 2100.0
        # tasarruf = round(10800.0 / 2050.0, 4) = 5.2683
        r1 = fn(36, 6, 50.0)
        if r1 != {
            "standart_mb": 10800.0,
            "full_block_mb": 2050.0,
            "sqrt_segment_mb": 2100.0,
            "full_block_tasarruf_orani": 5.2683,
        }:
            return False

        # L = 16, K = 4, mb = 10.0
        # standart = 640.0, full_block = (16+3)*10 = 190.0, S=4, C=4 -> sqrt = (4 + 16)*10 = 200.0
        r2 = fn(16, 4, 10.0)
        if r2 != {
            "standart_mb": 640.0,
            "full_block_mb": 190.0,
            "sqrt_segment_mb": 200.0,
            "full_block_tasarruf_orani": round(640.0 / 190.0, 4),
        }:
            return False

        return True
    except Exception:
        return False

ok(sozlesme(checkpoint_bellek_hesapla), "Standart, Full-Block ve Sqrt-Segment tepe aktivasyon bellekleri doğru hesaplanmalı")

def m_aktif_katman_unutan(katman_sayisi, alt_islem_sayisi, islem_bellek_mb):
    r = checkpoint_bellek_hesapla(katman_sayisi, alt_islem_sayisi, islem_bellek_mb)
    r["full_block_mb"] = katman_sayisi * islem_bellek_mb
    return r

def m_oran_bozuk(katman_sayisi, alt_islem_sayisi, islem_bellek_mb):
    r = checkpoint_bellek_hesapla(katman_sayisi, alt_islem_sayisi, islem_bellek_mb)
    r["full_block_tasarruf_orani"] = 1.0
    return r

for ad, mutant in [("aktif katmanın iç işlemlerini unutan", m_aktif_katman_unutan), ("tasarruf oranını yanlış hesaplayan", m_oran_bozuk)]:
    ok(not sozlesme(mutant), "hatalı çözüm/mutant yakalanmalı: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef checkpoint_bellek_hesapla(katman_sayisi, alt_islem_sayisi, islem_bellek_mb):\n    mb = float(islem_bellek_mb)\n    standart = katman_sayisi * alt_islem_sayisi * mb\n    full_block = (katman_sayisi + alt_islem_sayisi - 1) * mb\n    s = math.isqrt(katman_sayisi)\n    c = math.ceil(katman_sayisi / s)\n    sqrt_seg = (c + s * alt_islem_sayisi) * mb\n    oran = standart / full_block\n    return {'standart_mb': round(standart, 4), 'full_block_mb': round(full_block, 4), 'sqrt_segment_mb': round(sqrt_seg, 4), 'full_block_tasarruf_orani': round(oran, 4)}", 'referans', 'exec'), _REF)
_t, _g = _ff(checkpoint_bellek_hesapla, _REF['checkpoint_bellek_hesapla'], (36, 6, 50.0), tohum=3668, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (checkpoint_bellek_hesapla): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
ok(checkpoint_bellek_hesapla(4, 3, 0.123456) == _REF['checkpoint_bellek_hesapla'](4, 3, 0.123456), "4 basamak bellek yuvarlaması korunmalı")
```

```solution
import math

def checkpoint_bellek_hesapla(katman_sayisi, alt_islem_sayisi, islem_bellek_mb):
    mb = float(islem_bellek_mb)
    standart = katman_sayisi * alt_islem_sayisi * mb
    full_block = (katman_sayisi + alt_islem_sayisi - 1) * mb

    s = math.isqrt(katman_sayisi)
    c = math.ceil(katman_sayisi / s)
    sqrt_seg = (c + s * alt_islem_sayisi) * mb

    oran = standart / full_block

    return {
        "standart_mb": round(standart, 4),
        "full_block_mb": round(full_block, 4),
        "sqrt_segment_mb": round(sqrt_seg, 4),
        "full_block_tasarruf_orani": round(oran, 4),
    }
```

```hint
`full_block = (katman_sayisi + alt_islem_sayisi - 1) * mb` formülünü ve `s = math.isqrt(katman_sayisi)`, `c = math.ceil(katman_sayisi / s)` ile `(c + s * alt_islem_sayisi) * mb` formülünü uygula.
```
:::

::: gorev 2 · Selective Activation Checkpointing (İşlem Maliyet/Bellek Oranına Göre Seçim)
`secici_checkpoint_planla(islemler, bellek_butcesi_mb)` işlevini yaz.

Bir Transformer bloğundaki alt işlemler `islemler` listesiyle verilmektedir. Her öğe şu alanları taşıyan bir sözlüktür:
- `"ad"`: İşlemin adı (`str`, ör. `"qkv_matmul"`, `"softmax_attn"`, `"swiglu_gate"`).
- `"bellek_mb"`: Aktivasyonu bellekte tutmanın kapladığı alan (`float` > 0).
- `"ek_flop"`: Aktivasyonu silip geri yayılımda **yeniden hesaplamanın (`recompute`)** getireceği ek işlem maliyeti (`float` >= 0).

**Selective Activation Checkpointing** algoritması:
1. Girdi listesini değiştirme. Başlangıçta **tüm** işlemlerin bellekte tutulduğunu (`saklananlar`) varsay.
2. Eğer toplam bellek `bellek_butcesi_mb` sınırını aşıyorsa, birim bellek başına yeniden hesaplama maliyeti **EN DÜŞÜK** olan işlemlerden başlayarak (`verimlilik_skoru = ek_flop / bellek_mb` küçükten büyüğe; eşitlikte `"ad"` alfabetik küçükten büyüğe) işlemleri **yeniden hesaplanacaklar (`yeniden_hesaplananlar`)** listesine taşı (bellekten sil)!
3. Kalan saklanan işlemlerin toplam belleği `<= bellek_butcesi_mb` olduğu anda (veya tüm işlemler silindiğinde) dur!
4. Sonuç olarak şu sözlüğü döndür:
   - `"saklananlar"`: Bellekte tutulan işlemlerin `"ad"` listesi (orijinal `islemler` listesindeki sırasıyla!),
   - `"yeniden_hesaplananlar"`: Silinip geri yayılımda yeniden hesaplanan işlemlerin `"ad"` listesi (silinme sırasıyla!),
   - `"son_bellek_mb"`: Saklanan işlemlerin toplam belleği (`round(val, 4)`),
   - `"toplam_ek_flop"`: Yeniden hesaplanan işlemlerin toplam `ek_flop` maliyeti (`round(val, 4)`).

```starter
def secici_checkpoint_planla(islemler, bellek_butcesi_mb):
    # KUSURLU BAŞLANGIÇ KODU: Maliyet/bellek oranına göre seçici silme yapmıyor!
    return {
        "saklananlar": [islem["ad"] for islem in islemler],
        "yeniden_hesaplananlar": [],
        "son_bellek_mb": 0.0,
        "toplam_ek_flop": 0.0,
    }

ornek_islemler = [
    {"ad": "qkv_matmul", "bellek_mb": 100.0, "ek_flop": 800.0},   # oran: 8.0 (çok pahalı!)
    {"ad": "attn_softmax", "bellek_mb": 200.0, "ek_flop": 20.0},  # oran: 0.1 (çok ucuz ve şişkin!)
    {"ad": "swiglu_act", "bellek_mb": 150.0, "ek_flop": 30.0},    # oran: 0.2 (ucuz!)
]
print("Seçici Plan:", secici_checkpoint_planla(ornek_islemler, bellek_butcesi_mb=120.0))
```

```test
import copy

def sozlesme(fn):
    try:
        ops = [
            {"ad": "qkv_matmul", "bellek_mb": 100.0, "ek_flop": 800.0},   # 8.0
            {"ad": "attn_softmax", "bellek_mb": 200.0, "ek_flop": 20.0},  # 0.1 (1. silinir -> kalan 250 MB)
            {"ad": "swiglu_act", "bellek_mb": 150.0, "ek_flop": 30.0},    # 0.2 (2. silinir -> kalan 100 MB <= 120)
        ]
        op_k = copy.deepcopy(ops)
        r = fn(ops, 120.0)
        if ops != op_k or not isinstance(r, dict):
            return False
        if r != {
            "saklananlar": ["qkv_matmul"],
            "yeniden_hesaplananlar": ["attn_softmax", "swiglu_act"],
            "son_bellek_mb": 100.0,
            "toplam_ek_flop": 50.0,
        }:
            return False

        # Bütçe zaten yeterliyse hiçbir şey silinmemeli!
        r2 = fn(ops, 500.0)
        if r2 != {
            "saklananlar": ["qkv_matmul", "attn_softmax", "swiglu_act"],
            "yeniden_hesaplananlar": [],
            "son_bellek_mb": 450.0,
            "toplam_ek_flop": 0.0,
        }:
            return False

        return True
    except Exception:
        return False

ok(sozlesme(secici_checkpoint_planla), "ek_flop / bellek_mb oranı en düşük işlemlerden başlayarak bütçeye inene kadar seçici silme yapılmalı")

def m_ters_sira(islemler, bellek_butcesi_mb):
    # Pahalı işlemleri önce silen hatalı mutant
    r = secici_checkpoint_planla(islemler, bellek_butcesi_mb)
    r["toplam_ek_flop"] += 500.0
    return r

def m_hepsini_silen(islemler, bellek_butcesi_mb):
    r = secici_checkpoint_planla(islemler, bellek_butcesi_mb)
    r["saklananlar"] = []
    return r

for ad, mutant in [("pahalı MatMul işlemini önce silen", m_ters_sira), ("bütçeye ulaştığı halde silmeye devam eden", m_hepsini_silen)]:
    ok(not sozlesme(mutant), "hatalı çözüm/mutant yakalanmalı: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def secici_checkpoint_planla(islemler, bellek_butcesi_mb):\n    mevcut_bellek = sum((float(op['bellek_mb']) for op in islemler))\n    adaylar = sorted(islemler, key=lambda op: (float(op['ek_flop']) / float(op['bellek_mb']), op['ad']))\n    silinen_set = set()\n    yeniden_hesaplananlar = []\n    toplam_flop = 0.0\n    for op in adaylar:\n        if mevcut_bellek <= bellek_butcesi_mb:\n            break\n        ad = op['ad']\n        silinen_set.add(ad)\n        yeniden_hesaplananlar.append(ad)\n        mevcut_bellek -= float(op['bellek_mb'])\n        toplam_flop += float(op['ek_flop'])\n    saklananlar = [op['ad'] for op in islemler if op['ad'] not in silinen_set]\n    return {'saklananlar': saklananlar, 'yeniden_hesaplananlar': yeniden_hesaplananlar, 'son_bellek_mb': round(mevcut_bellek, 4), 'toplam_ek_flop': round(toplam_flop, 4)}", 'referans', 'exec'), _REF)
_t, _g = _ff(secici_checkpoint_planla, _REF['secici_checkpoint_planla'], ([{'ad': 'qkv_matmul', 'bellek_mb': 100.0, 'ek_flop': 800.0}, {'ad': 'attn_softmax', 'bellek_mb': 200.0, 'ek_flop': 20.0}, {'ad': 'swiglu_act', 'bellek_mb': 150.0, 'ek_flop': 30.0}], 120.0), tohum=3567, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (secici_checkpoint_planla): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
ok(secici_checkpoint_planla([{"ad": "a", "bellek_mb": 1.123456, "ek_flop": 0.234567}, {"ad": "b", "bellek_mb": 2.234567, "ek_flop": 9.0}], 2.5) == _REF['secici_checkpoint_planla']([{"ad": "a", "bellek_mb": 1.123456, "ek_flop": 0.234567}, {"ad": "b", "bellek_mb": 2.234567, "ek_flop": 9.0}], 2.5), "4 basamak bellek/flop yuvarlaması korunmalı")
```

```solution
def secici_checkpoint_planla(islemler, bellek_butcesi_mb):
    mevcut_bellek = sum(float(op["bellek_mb"]) for op in islemler)
    adaylar = sorted(
        islemler,
        key=lambda op: (float(op["ek_flop"]) / float(op["bellek_mb"]), op["ad"]),
    )

    silinen_set = set()
    yeniden_hesaplananlar = []
    toplam_flop = 0.0

    for op in adaylar:
        if mevcut_bellek <= bellek_butcesi_mb:
            break
        ad = op["ad"]
        silinen_set.add(ad)
        yeniden_hesaplananlar.append(ad)
        mevcut_bellek -= float(op["bellek_mb"])
        toplam_flop += float(op["ek_flop"])

    saklananlar = [op["ad"] for op in islemler if op["ad"] not in silinen_set]

    return {
        "saklananlar": saklananlar,
        "yeniden_hesaplananlar": yeniden_hesaplananlar,
        "son_bellek_mb": round(mevcut_bellek, 4),
        "toplam_ek_flop": round(toplam_flop, 4),
    }
```

```hint
İşlemleri `(op["ek_flop"] / op["bellek_mb"], op["ad"])` anahtarıyla sırala. `mevcut_bellek > bellek_butcesi_mb` olduğu sürece sıradaki işlemi `yeniden_hesaplananlar` listesine ekleyip belleğini `mevcut_bellek` değerinden düş.
```
:::

::: anlat Gerçek deney: SmolLM2'nin gerçek geri yayılımında checkpoint belleği
Final SmolLM2-135M'in 30 katmanını gerçek bir geri yayılımla çalıştırır (GPU varsa CUDA tepe belleği, yoksa CPU'da geri yayılım için saklanan tensörler ölçülür):

- **Üç kip:** checkpoint yok; her katman ayrı checkpoint (full-block); √L segment (30 katman için 5'li 6 segment). Üç kipte de girdi gradyanı aynı çıkmalıdır: checkpoint yalnız belleği ve süreyi değiştirir, sonucu değil.
- **Formül karşılaştırması:** katman sınırındaki gizli durum tensörünün boyutu `islem_bellek_mb`, checkpoint'siz ölçümden çıkan katman başına "alt işlem" sayısı `alt_islem_sayisi` olarak senin `checkpoint_bellek_hesapla` işlevine verilir. Formülün öngördüğü oranlar (full-block / standart, √L / standart) ölçülen oranlarla karşılaştırılır.
- **Seçici checkpoint:** tek bir katmanın autograd grafı dolaşılır ve her işlem türünün geri yayılım için **gerçekten sakladığı** tensörlerin baytı ile yeniden hesap maliyeti (FLOP) çıkarılır. Senin `secici_checkpoint_planla` işlevin bu gerçek tabloyla bir bellek bütçesine göre plan yapar. Tipik sonuç: ucuz eleman bazlı işlemler (çarpım, üs, SiLU) yeniden hesaplanır, pahalı matmul çıktıları saklanır; Megatron ve PyTorch'un seçici checkpoint politikası da budur.

**Güvenlik yönü — uzun girdiyle bellek tüketimi (DoS):** Tek bir isteğin uzunluğu 256'dan 2 048 tokena çıkarılır ve eğitim belleği ölçülür: checkpoint'siz bellek uzunlukla doğrusal büyür (2 kat uzunluk ≈ 2 kat bellek); 2K tokenda birkaç GB'a ulaşır. Uzunluk sınırı konmayan bir ince ayar ya da çıkarım servisi tek bir istekle doldurulabilir (OWASP LLM10 sınırsız tüketim). Katman başına checkpoint büyümeyi yaklaşık 10 kat keser ama ortadan kaldırmaz; asıl savunma istek başına token sınırıdır.

Kabul: iki işlevin farksal taramayı geçmesi; bellek sırasının full-block < √L < standart olması; üç kipte gradyanın aynı olması; ölçülen oranların formülden en çok %30 sapması; seçici planın bağımsız açgözlü referansla aynı olması. Ayrıca bellek uzunlukla artmalı ve en uzun girdide katman başına checkpoint belleği yarıdan fazla azaltmalıdır.

**Kanıt dosyasını oku:** `kipler` (MB ve süre), `formul`, `gercek_oran`, `tahmin_oran`, `secici_islemler`, `secici_plan`. Soru 1: Full-block neden √L'den daha az bellek kullanıyor, √L'nin avantajı ne olabilir? Soru 2: Bu ölçümde checkpoint süreyi neden belirgin artırmadı (ipucu: 135M küçük bir model ve GPU boşta)? Soru 3: Dikkat skorları saklansaydı (FlashAttention yok) seçici plan nasıl değişirdi?
:::

::: gorev Gerçek deney · SmolLM2'nin geri yayılımında full-block, √L ve seçici checkpoint ölçümü
Önceki görevlerdeki `checkpoint_bellek_hesapla`, `secici_checkpoint_planla` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 240
```
```starter
import ai_lab
def checkpoint_bellek_hesapla(katman_sayisi, alt_islem_sayisi, islem_bellek_mb):
    return {'standart_mb': 0.0, 'full_block_mb': 0.0, 'sqrt_segment_mb': 0.0, 'full_block_tasarruf_orani': 1.0}

def secici_checkpoint_planla(islemler, bellek_butcesi_mb):
    return {'saklananlar': [islem['ad'] for islem in islemler], 'yeniden_hesaplananlar': [], 'son_bellek_mb': 0.0, 'toplam_ek_flop': 0.0}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_16 as D
    D.goster(checkpoint_bellek_hesapla, secici_checkpoint_planla)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_islem_tablosu', '_saklanan_bayt', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
checkpoint_bellek_hesapla = need("checkpoint_bellek_hesapla")
secici_checkpoint_planla = need("secici_checkpoint_planla")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef checkpoint_bellek_hesapla(katman_sayisi, alt_islem_sayisi, islem_bellek_mb):\n    mb = float(islem_bellek_mb)\n    standart = katman_sayisi * alt_islem_sayisi * mb\n    full_block = (katman_sayisi + alt_islem_sayisi - 1) * mb\n    s = math.isqrt(katman_sayisi)\n    c = math.ceil(katman_sayisi / s)\n    sqrt_seg = (c + s * alt_islem_sayisi) * mb\n    oran = standart / full_block\n    return {'standart_mb': round(standart, 4), 'full_block_mb': round(full_block, 4), 'sqrt_segment_mb': round(sqrt_seg, 4), 'full_block_tasarruf_orani': round(oran, 4)}\n\ndef secici_checkpoint_planla(islemler, bellek_butcesi_mb):\n    mevcut_bellek = sum((float(op['bellek_mb']) for op in islemler))\n    adaylar = sorted(islemler, key=lambda op: (float(op['ek_flop']) / float(op['bellek_mb']), op['ad']))\n    silinen_set = set()\n    yeniden_hesaplananlar = []\n    toplam_flop = 0.0\n    for op in adaylar:\n        if mevcut_bellek <= bellek_butcesi_mb:\n            break\n        ad = op['ad']\n        silinen_set.add(ad)\n        yeniden_hesaplananlar.append(ad)\n        mevcut_bellek -= float(op['bellek_mb'])\n        toplam_flop += float(op['ek_flop'])\n    saklananlar = [op['ad'] for op in islemler if op['ad'] not in silinen_set]\n    return {'saklananlar': saklananlar, 'yeniden_hesaplananlar': yeniden_hesaplananlar, 'son_bellek_mb': round(mevcut_bellek, 4), 'toplam_ek_flop': round(toplam_flop, 4)}", 'referans', 'exec'), _REF)
_t, _g = _ff(checkpoint_bellek_hesapla, _REF['checkpoint_bellek_hesapla'], (36, 6, 50.0), tohum=3668, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (checkpoint_bellek_hesapla): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(secici_checkpoint_planla, _REF['secici_checkpoint_planla'], ([{'ad': 'qkv_matmul', 'bellek_mb': 100.0, 'ek_flop': 800.0}, {'ad': 'attn_softmax', 'bellek_mb': 200.0, 'ek_flop': 20.0}, {'ad': 'swiglu_act', 'bellek_mb': 150.0, 'ek_flop': 30.0}], 120.0), tohum=3567, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (secici_checkpoint_planla): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
kontrol(checkpoint_bellek_hesapla(4, 3, 0.123456) == _REF['checkpoint_bellek_hesapla'](4, 3, 0.123456), "4 basamak bellek yuvarlaması korunmalı")
kontrol(secici_checkpoint_planla([{"ad": "a", "bellek_mb": 1.123456, "ek_flop": 0.234567}, {"ad": "b", "bellek_mb": 2.234567, "ek_flop": 9.0}], 2.5) == _REF['secici_checkpoint_planla']([{"ad": "a", "bellek_mb": 1.123456, "ek_flop": 0.234567}, {"ad": "b", "bellek_mb": 2.234567, "ek_flop": 9.0}], 2.5), "4 basamak bellek/flop yuvarlaması korunmalı")
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_16 as D
try: r = D.deney(checkpoint_bellek_hesapla, secici_checkpoint_planla)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['sira_dogru'] and r['gradyan_ayni'], 'ölçülen bellek full-block < √L < standart; gradyan üç kipte aynı')
kontrol(r['oran_tutarli'], 'ölçülen bellek oranları formülün öngördüğünden en çok %30 sapıyor')
kontrol(r['secici_ayni'], 'seçici plan gerçek autograd tablosunda bağımsız referansla aynı')
kontrol(r['uzunlukla_buyuyor'] and r['checkpoint_buyumeyi_kesiyor'], 'aktivasyon belleği istek uzunluğuyla büyüdü; checkpoint büyümeyi yarıdan fazla kesti')
ai_lab.kanit_yaz("ai-uretim-16-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-16", "deney": r})
```
```solution
import ai_lab
import math

def checkpoint_bellek_hesapla(katman_sayisi, alt_islem_sayisi, islem_bellek_mb):
    mb = float(islem_bellek_mb)
    standart = katman_sayisi * alt_islem_sayisi * mb
    full_block = (katman_sayisi + alt_islem_sayisi - 1) * mb
    s = math.isqrt(katman_sayisi)
    c = math.ceil(katman_sayisi / s)
    sqrt_seg = (c + s * alt_islem_sayisi) * mb
    oran = standart / full_block
    return {'standart_mb': round(standart, 4), 'full_block_mb': round(full_block, 4), 'sqrt_segment_mb': round(sqrt_seg, 4), 'full_block_tasarruf_orani': round(oran, 4)}

def secici_checkpoint_planla(islemler, bellek_butcesi_mb):
    mevcut_bellek = sum((float(op['bellek_mb']) for op in islemler))
    adaylar = sorted(islemler, key=lambda op: (float(op['ek_flop']) / float(op['bellek_mb']), op['ad']))
    silinen_set = set()
    yeniden_hesaplananlar = []
    toplam_flop = 0.0
    for op in adaylar:
        if mevcut_bellek <= bellek_butcesi_mb:
            break
        ad = op['ad']
        silinen_set.add(ad)
        yeniden_hesaplananlar.append(ad)
        mevcut_bellek -= float(op['bellek_mb'])
        toplam_flop += float(op['ek_flop'])
    saklananlar = [op['ad'] for op in islemler if op['ad'] not in silinen_set]
    return {'saklananlar': saklananlar, 'yeniden_hesaplananlar': yeniden_hesaplananlar, 'son_bellek_mb': round(mevcut_bellek, 4), 'toplam_ek_flop': round(toplam_flop, 4)}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_16 as D
    D.goster(checkpoint_bellek_hesapla, secici_checkpoint_planla)
```
```hint
İki görevin çözümlerini olduğu gibi buraya koy.
```
:::

::: anlat Sınır
Görevler standart, tam blok ve √L activation checkpointing bellek hesabını ve maliyet/bellek oranına göre seçici checkpointing'i formülle hesaplatır; final adım belleği gerçek SmolLM2 geri yayılımında ölçer. Formüller katman başına aktivasyon boyutunu sabit varsayar; FlashAttention kullanılmayan dikkat katmanlarında bellek bağlam uzunluğunun karesiyle büyür ve seçimi değiştirir. Tam checkpointing ileri geçişi yeniden yaptığı için hesap süresini yaklaşık üçte bir artırır. Dropout gibi rastgele işlemler yeniden hesaplamada aynı RNG durumuyla üretilmezse gradyan yanlış olur.

Kaynaklar: [Chen vd. 2016 - Training Deep Nets with Sublinear Memory Cost](https://arxiv.org/abs/1604.06174), [Korthikanti vd. 2022 - Reducing Activation Recomputation in Large Transformer Models](https://arxiv.org/abs/2205.05198).
:::

::: dusun
`Activation Checkpointing` kullanırken çok sinsi bir determinizm tuzağı vardır:
Eğer katmanın içinde **Stokastik (Rastgele) bir işlem** — örneğin **`Dropout`** — varsa ve ileri geçişte (`Forward Pass`) rastgele sayı üretecinin (**`PRNG State / CUDA RNG Seed`**) durumu kaydedilmezse, backpropagation sırasında katman yeniden hesaplandığında (`Rematerialization`) `Dropout` **farklı** nöronları sıfırlar!

İleri geçişteki aktivasyon ile geri geçişte yeniden üretilen aktivasyon birbirinden farklı olursa $dW = X^T \cdot dY$ gradyanlarına ne olur? PyTorch'un `torch.utils.checkpoint` içinde neden **`preserve_rng_state=True`** mekanizmasıyla `torch.cuda.get_rng_state()` durumunu yedekleyip geri yüklediğini açıkla.
:::

::: ozet
- Derin ağların eğitiminde `VRAM` darboğazının ana sorumlusu ağırlıklar değil, $dW = X^T \cdot dY$ hesabı için `Forward Pass`'ten `Backward Pass`'e kadar saklanan **ara aktivasyonlardır (`Activations`)**.
- **`Activation Checkpointing` (`Gradient Rematerialization`)**, ara aktivasyonları ileri geçişte silip geri geçişte en yakın sınır taşından yeniden hesaplayarak yaklaşık `+%33` ek `FLOPs` karşılığında aktivasyon belleğini $O(L)$'den $O(\sqrt{L})$ seviyesine (`5x–10x` küçülme) indirir.
- **`Selective Activation Checkpointing`**, birim bellek başına yeniden hesaplama maliyeti ($\text{FLOPs/Byte}$) yüksek olan `MatMul` çıktılarını bellekte saklayıp, ucuz ama devasa yer kaplayan `Softmax / SwiGLU` aktivasyonlarını yeniden hesaplayarak neredeyse sıfır hız kaybıyla maksimum bellek tasarrufu sağlar.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Ağırlıklardan büyük aktivasyon belleği (30 sn).** "Uzun bağlamlı eğitimde VRAM'i asıl dolduran model parametreleri değil, geri yayılımda zincir kuralı için her katmanda tutulan ara aktivasyon tensörleridir ($O(L \cdot B \cdot S \cdot d)$)."
2. **Bellek için yeniden hesap takası (35 sn).** "`Activation Checkpointing`, katman içi ara aktivasyonları silip yalnız blok sınırlarını saklar; geri yayılımda o bloğun ileri geçişini yerelde bir kez daha çalıştırarak ~%25–33 ek FLOP karşılığında aktivasyon belleğini $O(\sqrt{L})$ düzeyine indirir."
3. **Seçici (`Selective`) Checkpointing (30 sn).** "Matris çarpımları hesapça pahalı, `Softmax`/`Dropout` çıktıları ise bellekçe devasa ama yeniden hesabı ucuz olduğu için yalnız ucuz ve şişkin aktivasyonları silmek en iyi hız-bellek dengesini verir."
4. **Soru (25 sn).** "Geri yayılımda blok yeniden çalıştırılırken `Dropout` maskesi ileri geçiştekiyle birebir aynı tohumdan (`RNG state`) üretilmezse gradyanlara ne olur?"
:::
