---
id: ai-uretim-14
title: "Sayısal Kararlılık ve Bit Mimarisi: FP32, TF32, BF16 ve FP8 (E4M3 / E5M2) Matematiği"
track: ai-uretim
order: 14
duration_minutes: 35
difficulty: ileri
xp: 290
prerequisites: [ai-uretim-13]
tags: [floating-point, bf16, fp16, fp8, e4m3, e5m2, logsumexp, numerical-stability]
summary: "FP32, BF16 ve OCP FP8 (E4M3) bit mimarilerini, blok ölçekli nicemlemeyi ve taşmaya dayanıklı LogSumExp çapraz entropisini gerçek SmolLM2 ağırlıkları üzerinde ölç."
esleme: ai-uretim-13, ai-temel-10
---

::: anlat
## Floating-point aralık ve sayısal kararlılık

Düşük precision bellek ve hesap maliyetini azaltabilir; fakat temsil aralığı ve yuvarlama hatası da değişir. Bu derste FP8 için sadeleştirilmiş bir hesabı ve overflow riskini azaltan LogSumExp yöntemini inceleyeceksin. Format seçimi tek başına kararlı veya hızlı training garantisi değildir.

Ancak 2018–2020 yıllarında büyük modelleri klasik **`FP16` (`IEEE 754 Half-Precision`)** ile eğitmeye çalışan mühendisler korkunç bir kâbus yaşadı: Eğitim ortasında loss function aniden **`NaN` (`Not a Number`)** oluyor ve milyonlarca dolarlık GPU süresi yanıyordu! Ardından Google Brain **`BF16` (`Brain Float 16`)** formatını, NVIDIA ve DeepSeek ise **`FP8` (`E4M3` & `E5M2`)** formatlarını devreye soktu ve sorun kökten çözüldü. Peki nasıl?

---

### 1. Kayan Nokta (`Floating-Point`) Bit Anatomisi: `Sign`, `Exponent` ve `Mantissa`

Bilgisayarda her kayan noktalı sayı üç bit alanından oluşan bilimsel gösterimle ($\pm 1.\text{Mantissa} \times 2^{\text{Exponent} - \text{Bias}}$) temsil edilir:

$$\text{Değer} = (-1)^{S} \times 2^{(E - \text{bias})} \times \left(1 + \frac{M}{2^{m}}\right)$$

1. **`Sign` ($S$ — 1 bit):** İşaret biti (`0` pozitif, `1` negatif).
2. **`Exponent` ($E$ — Üs bitleri):** Sayının **Dynamic Range (Dinamik Aralığını)**, yani ne kadar büyük (`Overflow` sınırı) ve sıfıra ne kadar yakın (`Underflow` sınırı) sayıları tutabileceğini belirler!
3. **`Mantissa / Fraction` ($M$ — Kesir bitleri):** Sayının **Precision (Hassasiyetini)**, yani virgülden sonra kaç basamak ayırt edebileceğini belirler!

```
  FORMAT          BİT DAĞILIMI (Sign | Exponent | Mantissa)      MAKSİMUM DEĞER (Dynamic Range)
 ───────────────────────────────────────────────────────────────────────────────────────────────
  FP32 (32-bit)   [ 1 ] [    8 bit E    ] [      23 bit M      ]   ~ 3.40 x 10^38  (Tam Hassasiyet)
  TF32 (19-bit)   [ 1 ] [    8 bit E    ] [   10 bit M   ]         ~ 3.40 x 10^38  (Ampere/Hopper MatMul)
  FP16 (16-bit)   [ 1 ] [ 5 bit E ] [   10 bit M   ]               65,504          (Çok Dar Aralık -> NaN!)
  BF16 (16-bit)   [ 1 ] [    8 bit E    ] [ 7 bit M ]              ~ 3.39 x 10^38  (FP32 ile Aynı Aralık!)
  FP8 E4M3 (8b)   [ 1 ] [4b E] [3b M]                              448             (Forward: Yüksek Hassasiyet)
  FP8 E5M2 (8b)   [ 1 ] [ 5b E ] [2b]                              57,344          (Backward: Geniş Gradyan Aralığı)
```

#### 💡 Neden `BF16` (`1-8-7`) Derin Öğrenmenin Kralı Oldu?
Yukarıdaki tabloya dikkatle bak:
- Klasik **`FP16` (`1-5-10`)** yalnızca **5 bit `Exponent`** kullanır; temsil edebileceği en büyük sayı **`65,504`**'tür! Bir Transformer'da dikkat skorları veya aktivasyon kareleri `65,505` olduğu salisede `FP16` **`+Inf` (`Overflow`)** verir; küçük gradyanlar ise $6 \times 10^{-8}$ altında sıfırlanır (**`Underflow`**). Bu yüzden `FP16` eğitimi karmaşık bir `Dynamic Loss Scaler` (`GradScaler`) olmadan çalışamaz.
- **`BF16` (`1-8-7`)** ise `Mantissa` bitlerinden 3 bit feda edip (`10 -> 7 bit`), **`FP32` ile birebir aynı olan 8 bit `Exponent`** kullanır! Sinir ağları gürültüye dayanıklı olduğu için virgülden sonraki küçük hassasiyet kaybını umursamaz, ama **dinamik aralığın ($10^{-38}$ ile $3.4 \times 10^{38}$) daralmasına asla tahammül edemez!**

---

### 2. DeepSeek-V3 ve H100 `FP8` Yaklaşımı: Neden İleri Geçişte `E4M3`, Geri Geçişte `E5M2`?

8 bite (`1 Byte`) indiğimizde elimizde `Sign` hariç yalnızca **7 bit** kalır. Endüstri burada **Hibrit `FP8`** standardını (Micikevicius et al.) geliştirdi:
1. **`FP8 E4M3` (4 bit Exponent, 3 bit Mantissa — Maks: `448.0`):**
   - **forward pass** ağırlıkları ($W$) ve aktivasyonları ($X$) `RMSNorm` sayesinde düzgün dağılımlıdır. Burada daha fazla hassasiyet (`3 bit Mantissa`) gerektiği için **`E4M3`** kullanılır!
2. **`FP8 E5M2` (5 bit Exponent, 2 bit Mantissa — Maks: `57,344.0`):**
   - **Backward Pass (backpropagation)** gradyanları ($dY$) katmanlar boyunca çok geniş bir dinamik aralıkta zıplar. Bu yüzden geri yayılımda `FP16` ile aynı üs genişliğine (`5 bit Exponent`) sahip olan **`E5M2`** kullanılır!

#### ⚖️ `Per-Tile / Per-Block FP8 Scaling` (DeepSeek-V3 Mimarisi)
`E4M3` formatının tavanı `448.0` olduğu için bir tensörü doğrudan `FP8`'e çevirirsen `448`'den büyük değerler kırpılır (`Clipping / Saturation`), küçük değerler sıfırlanır. Bunu önlemek için tensör $1 \times 128$ boyutlu bloklara (**Tiles**) bölünür, her bloğun mutlak maksimumu ($\text{amax} = \max_i |x_i|$) bulunur ve blok `[-448, +448]` aralığına ölçeklenir:

$$s = \frac{\text{amax}}{448.0}, \qquad x_{\text{fp8}} = \text{round\_to\_fp8}\!\left(\frac{x}{s}\right), \qquad \hat{x} = x_{\text{fp8}} \cdot s$$

Şimdi saf Python ile `FP16`, `BF16` ve `FP8 E4M3` bit sınırlarını ve blok ölçeklemeli (`Block-Scaled`) quantization işlemini canlı olarak test edelim:

```python
def ieee_formati_ozetle(exp_bits, mantissa_bits):
    bias = (2 ** (exp_bits - 1)) - 1
    # Standart IEEE 754 (en üst exponent NaN/Inf için ayrıldığında) maksimum normal sayı:
    max_exp = (2 ** exp_bits - 2) - bias
    max_mantissa = 2.0 - (2.0 ** (-mantissa_bits))
    max_deger = max_mantissa * (2.0 ** max_exp)
    min_normal = 1.0 * (2.0 ** (1 - bias))
    return max_deger, min_normal

fp16_max, fp16_min = ieee_formati_ozetle(5, 10)
bf16_max, bf16_min = ieee_formati_ozetle(8, 7)
print(f"FP16 (1-5-10) -> Max: {fp16_max:,.0f} | Min Normal: {fp16_min:.2e}")
print(f"BF16 (1-8-7)  -> Max: {bf16_max:.2e} | Min Normal: {bf16_min:.2e}")
```

---

### 3. `LogSumExp Trick`: Softmax ve Cross-Entropy'de `exp()` Taşmasını Önlemek

Bir dil modelinin son katmanında sözlük boyutu $V = 128,256$ için ham skorlar (**Logits** $z_i$) üretilir ve **Cross-Entropy Loss** hesaplanır:

$$\mathcal{L} = -\log P(y) = -\log\left(\frac{e^{z_y}}{\sum_{j=1}^V e^{z_j}}\right) = \log\left(\sum_{j=1}^V e^{z_j}\right) - z_y$$

Eğer $z_j = 100.0$ ise $e^{100} \approx 2.68 \times 10^{43}$ olur ve hem `FP16` hem `BF16` hem de `FP32` anında **`+Inf` (`Overflow`)** verir! $\log(\infty) - 100 = \infty$ olur ve eğitim çöker!
**Çözüm — `LogSumExp (LSE) Özdeşliği`:** Maksimum logit değerini ($m = \max_j z_j$) üs almadan önce dışarı çektiğimizde matematiksel sonuç **hiç değişmez** ama en büyük üs $e^{m - m} = e^0 = 1.0$ olduğu için **taşma (`Overflow`) fiziksel olarak imkansız hale gelir**:

$$\text{LSE}(z) = m + \log\left(\sum_{j=1}^V e^{z_j - m}\right), \qquad \mathcal{L} = \text{LSE}(z) - z_y$$

---

### 4. Gerçek Üretim Kodu: PyTorch `torch.amp.autocast(bfloat16)` ve `FP8` Çarpımı

Gerçek üretim sistemlerinde hangi işlemlerin `BF16 / FP8` (`Tensor Core MatMul`), hangi işlemlerin ise `FP32` (`Master Weights`, `RMSNorm`, `Softmax`, `Loss`) hassasiyetinde kalması gerektiğini gösteren mimari:

```python norun
import torch
import torch.nn as nn

def train_step_bf16_mixed_precision(model: nn.Module, optimizer: torch.optim.Optimizer, x: torch.Tensor, y: torch.Tensor):
    optimizer.zero_grad(set_to_none=True)

    # BF16 Autocast: Linear/Attention MatMul işlemlerini BF16'da yapar,
    # ancak Softmax, LayerNorm ve CrossEntropy kaybını otomatik FP32'de tutar!
    with torch.amp.autocast(device_type="cuda", dtype=torch.bfloat16):
        logits = model(x)
        # CrossEntropyLoss içeride kararlı LogSumExp (log_softmax) çalıştırır
        loss = nn.functional.cross_entropy(logits.view(-1, logits.size(-1)), y.view(-1))

    # BF16'nın 8-bit Exponent genişliği FP32 ile aynı olduğundan GradScaler GEREKMEZ!
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
    optimizer.step()  # Optimizer içindeki Master Weights ve m, v momentleri FP32'de güncellenir!
    return loss.item()
```

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [PyTorch AMP](https://docs.pytorch.org/docs/stable/amp.html). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: tahmin FP16 Taşması (Overflow) vs Kararlı LogSumExp
Bir modelin 3 sınıflı logit çıktısı `z = [90.0, 91.0, 92.0]` olsun. Klasik `FP16`'da `exp(92.0)` değeri $65,504$ sınırını milyarlarca kat aştığı için `Overflow` verir. Peki `LogSumExp Trick` ile $m = \max(z) = 92.0$ çıkarıldığında `exp(z_i - m)` terimlerinin alabileceği **en büyük** değer nedir ve `92.0` sınıfının negatif log-olasılık kaybı ($\mathcal{L} = \text{LSE}(z) - z_2$) kaç çıkar?

```python
import math
z = [90.0, 91.0, 92.0]
m = max(z)
kaydirilmis_exps = [math.exp(v - m) for v in z]
en_buyuk_exp = max(kaydirilmis_exps)
lse = m + math.log(sum(kaydirilmis_exps))
kayip = round(lse - z[2], 4)
print(f"MaxExp={en_buyuk_exp} | LSE={round(lse, 4)} | Kayip={kayip}")
```

???

```cikti
MaxExp=1.0 | LSE=92.4076 | Kayip=0.4076
```
En büyük logit $m = 92.0$ çıkarıldığında kaydırılmış logitler `[-2.0, -1.0, 0.0]` olur; dolayısıyla `exp(0.0) = 1.0` (`MaxExp=1.0`) değerini asla geçemez ve `Overflow` tamamen engellenir. Kayıp ise $\log(e^{-2} + e^{-1} + 1) \approx 0.4076$ olarak güvenle hesaplanır.
:::

::: gorev 1 · Kayan Nokta (Floating-Point) Dinamik Aralık ve Blok Bazlı FP8 E4M3 quantization
`fp8_blok_nicele(degerler, maks_temsil=448.0)` işlevini yaz.

DeepSeek-V3 ve NVIDIA H100 `FP8 (E4M3)` eğitiminde bir aktivasyon bloğu (`degerler`: `list[float]`) şu adımlarla 8-bit aralığına nicelenir (**Block-wise AbsMax Quantization**) ve geri açılır (**Dequantization**):
1. Girdi listesini değiştirme. Bloğun mutlak maksimum değerini bul: $\text{amax} = \max_{x \in \text{degerler}} |x|$.
2. Ölçekleme çarpanını (`olcek`) hesapla:
   - Eğer $\text{amax} == 0.0$ ise `olcek = 1.0` al; aksi halde $\text{olcek} = \frac{\text{amax}}{\text{maks\_temsil}}$ olarak hesapla.
3. Her $x$ değerini ölçeğe bölüp en yakın tam sayı/kuantum basamağına yuvarla (`round(x / olcek)`) ve `[-maks_temsil, +maks_temsil]` aralığına kırp (`q_degerler`).
4. Nicelenmiş her $q$ değerini tekrar `olcek` ile çarparak geri açılmış (`geri_acilmis`) listeyi oluştur ve orijinal değerlerle geri açılmış değerler arasındaki **Ortalama Mutlak Hatayı (`mae` = $\frac{1}{N}\sum |x_i - \hat{x}_i|$)** hesapla.
5. Tüm kayan nokta çıktılarını `round(val, 6)` ile yuvarlayarak şu sözlüğü döndür:
   - `"amax"`: `float`
   - `"olcek"`: `float`
   - `"nicelenmis"`: `list[float]` (yuvarlanmış kuantum değerleri)
   - `"geri_acilmis"`: `list[float]`
   - `"mae"`: `float`

```starter
def fp8_blok_nicele(degerler, maks_temsil=448.0):
    # KUSURLU BAŞLANGIÇ KODU: AbsMax ölçekleme ve niceleme yapmadan sıfır döndürüyor!
    n = len(degerler)
    return {
        "amax": 0.0,
        "olcek": 1.0,
        "nicelenmis": [0.0] * n,
        "geri_acilmis": [0.0] * n,
        "mae": 0.0,
    }

print("FP8 Niceleme:", fp8_blok_nicele([896.0, -448.0, 224.0, -10.5], maks_temsil=448.0))
```

```test
import copy

def sozlesme(fn):
    try:
        d = [896.0, -448.0, 225.0, -11.0]
        dk = copy.deepcopy(d)
        # amax = 896.0, maks_temsil = 448.0 -> olcek = 896.0 / 448.0 = 2.0
        # nicelenmis: [round(896/2)=448.0, round(-448/2)=-224.0, round(225/2)=112.0, round(-11/2)=-6.0]
        # geri_acilmis: [896.0, -448.0, 224.0, -12.0]
        # hatalar: [0.0, 0.0, 1.0, 1.0] -> mae = 2.0 / 4 = 0.5
        r = fn(d, 448.0)
        if d != dk or not isinstance(r, dict):
            return False
        if r.get("amax") != 896.0 or r.get("olcek") != 2.0:
            return False
        if r.get("nicelenmis") != [448.0, -224.0, 112.0, -6.0]:
            return False
        if r.get("geri_acilmis") != [896.0, -448.0, 224.0, -12.0]:
            return False
        if r.get("mae") != 0.5:
            return False

        # Tümü sıfır olan blok sınır testi (ZeroDivisionError vermemeli!)
        r0 = fn([0.0, 0.0], 448.0)
        if r0 != {"amax": 0.0, "olcek": 1.0, "nicelenmis": [0.0, 0.0], "geri_acilmis": [0.0, 0.0], "mae": 0.0}:
            return False

        return True
    except Exception:
        return False

eq(fp8_blok_nicele([]), {"amax": 0.0, "olcek": 1.0, "nicelenmis": [], "geri_acilmis": [], "mae": 0.0}, "boş blok sınır durumu")
eq(fp8_blok_nicele([448.0]), {"amax": 448.0, "olcek": 1.0, "nicelenmis": [448.0], "geri_acilmis": [448.0], "mae": 0.0}, "varsayılan maks_temsil=448.0")
eq(fp8_blok_nicele([0.5], 448.0)["olcek"], round(0.5 / 448.0, 6), "0 < amax <= 1.0 için ölçek hesaplanır")
eq(fp8_blok_nicele([0.1234567])["amax"], 0.123457, "amax 6 basamağa yuvarlanır")
eq(fp8_blok_nicele([10.0], 1.6234567)["nicelenmis"], [1.623457], "taşma kırpması ve 6 basamak yuvarlama")
ok(sozlesme(fp8_blok_nicele), "FP8 blok ölçekleme (amax / 448), niceleme, geri açma ve MAE hesabı doğru çalışmalı")

def m_olceksiz(degerler, maks_temsil=448.0):
    r = fp8_blok_nicele(degerler, maks_temsil)
    r["olcek"] = 1.0
    return r

def m_mae_sifir(degerler, maks_temsil=448.0):
    r = fp8_blok_nicele(degerler, maks_temsil)
    r["mae"] = 0.0
    return r

for ad, mutant in [("ölçek çarpanını hesaplamayan", m_olceksiz), ("niceleme hatasını (MAE) sıfır veren", m_mae_sifir)]:
    ok(not sozlesme(mutant), "hatalı çözüm/mutant yakalanmalı: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def fp8_blok_nicele(degerler, maks_temsil=448.0):\n    amax = max((abs(x) for x in degerler)) if degerler else 0.0\n    olcek = amax / maks_temsil if amax > 0.0 else 1.0\n    nicelenmis = []\n    geri_acilmis = []\n    for x in degerler:\n        q = float(round(x / olcek))\n        if q > maks_temsil:\n            q = float(maks_temsil)\n        elif q < -maks_temsil:\n            q = float(-maks_temsil)\n        nicelenmis.append(round(q, 6))\n        geri_acilmis.append(round(q * olcek, 6))\n    mae = sum((abs(x - x_hat) for x, x_hat in zip(degerler, geri_acilmis))) / len(degerler) if degerler else 0.0\n    return {'amax': round(amax, 6), 'olcek': round(olcek, 6), 'nicelenmis': nicelenmis, 'geri_acilmis': geri_acilmis, 'mae': round(mae, 6)}", 'referans', 'exec'), _REF)
_t, _g = _ff(fp8_blok_nicele, _REF['fp8_blok_nicele'], ([896.0, -448.0, 224.0, -10.5], 448.0), tohum=2563, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (fp8_blok_nicele): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def fp8_blok_nicele(degerler, maks_temsil=448.0):
    amax = max(abs(x) for x in degerler) if degerler else 0.0
    olcek = (amax / maks_temsil) if amax > 0.0 else 1.0

    nicelenmis = []
    geri_acilmis = []
    for x in degerler:
        q = float(round(x / olcek))
        if q > maks_temsil:
            q = float(maks_temsil)
        elif q < -maks_temsil:
            q = float(-maks_temsil)
        nicelenmis.append(round(q, 6))
        geri_acilmis.append(round(q * olcek, 6))

    mae = sum(abs(x - x_hat) for x, x_hat in zip(degerler, geri_acilmis)) / len(degerler) if degerler else 0.0

    return {
        "amax": round(amax, 6),
        "olcek": round(olcek, 6),
        "nicelenmis": nicelenmis,
        "geri_acilmis": geri_acilmis,
        "mae": round(mae, 6),
    }
```

```hint
`amax = max(abs(x) for x in degerler)` bulduktan sonra `olcek = (amax / maks_temsil) if amax > 0 else 1.0` hesapla. Her değeri `round(x / olcek)` ile tam basamağa yuvarlayıp `[-maks_temsil, maks_temsil]` aralığına sınırla.
```
:::

::: gorev 2 · Taşma Korumalı (Overflow-Safe) LogSumExp ve Cross-Entropy
`kararli_logsumexp_kayip(logitler, hedef_indeks)` işlevini yaz.

Aşırı büyük veya aşırı küçük logit değerlerinde (`[1000.0, 1001.0, 999.0]` veya `[-1000.0, -1002.0]`) bile `OverflowError` veya `ZeroDivisionError` vermeden çalışan kararlı bir **LogSumExp & Cross-Entropy** hesaplayıcısı yazacaksın:
1. Girdi listesi `logitler`'i değiştirme. Maksimum logit değerini bul: $m = \max_j z_j$.
2. Kararlı **LogSumExp** değerini hesapla:
   $$\text{lse} = m + \ln\!\left(\sum_{j=0}^{V-1} e^{z_j - m}\right)$$
3. Her sınıfın log-olasılığını $\log P_j = z_j - \text{lse}$ ve olasılığını $P_j = e^{z_j - \text{lse}}$ olarak hesapla.
4. `hedef_indeks` sınıfı için **Cross-Entropy Loss** değerini ($\mathcal{L} = -\log P_{\text{hedef}} = \text{lse} - z_{\text{hedef}}$) ve hedef sınıfın backpropagation logit gradyanını ($\frac{\partial \mathcal{L}}{\partial z_j} = P_j - \mathbb{1}_{j == \text{hedef}}$) hesapla!
5. Tüm sayıları `round(val, 6)` ile yuvarlayarak şu sözlüğü döndür:
   - `"lse"`: `float`
   - `"kayip"`: `float`
   - `"olasiliklar"`: `list[float]`
   - `"logit_gradyanlari"`: `list[float]` ($P_j - 1.0$ hedef indeks için, diğerleri için $P_j$)

```starter
def kararli_logsumexp_kayip(logitler, hedef_indeks):
    # KUSURLU BAŞLANGIÇ KODU: Maksimum kaydırma (LogSumExp trick) yapmadığı için büyük logitlerde çöker!
    n = len(logitler)
    return {
        "lse": 0.0,
        "kayip": 0.0,
        "olasiliklar": [0.0] * n,
        "logit_gradyanlari": [0.0] * n,
    }

print("Kararlı Kayıp:", kararli_logsumexp_kayip([1000.0, 1001.0, 1002.0], hedef_indeks=2))
```

```test
import copy
import math

def sozlesme(fn):
    try:
        # Standart math.exp(1000.0) OverflowError fırlatır! Fonksiyon taşmadan çalışmalı.
        z = [1000.0, 1001.0, 1002.0]
        zk = copy.deepcopy(z)
        r = fn(z, 2)
        if z != zk or not isinstance(r, dict):
            return False

        exps = [math.exp(-2.0), math.exp(-1.0), 1.0]
        toplam = sum(exps)
        b_lse = round(1002.0 + math.log(toplam), 6)
        b_kayip = round(b_lse - 1002.0, 6)
        b_olasilik = [round(e / toplam, 6) for e in exps]
        b_grad = [
            round(exps[0] / toplam, 6),
            round(exps[1] / toplam, 6),
            round(exps[2] / toplam - 1.0, 6),
        ]
        if r.get("lse") != b_lse or r.get("kayip") != b_kayip:
            return False
        if r.get("olasiliklar") != b_olasilik or r.get("logit_gradyanlari") != b_grad:
            return False

        # Çok negatif logit testi (Underflow koruması)
        r_neg = fn([-1000.0, -1000.0], 0)
        if r_neg.get("olasiliklar") != [0.5, 0.5] or r_neg.get("logit_gradyanlari") != [-0.5, 0.5]:
            return False

        return True
    except Exception:
        return False

eq(kararli_logsumexp_kayip([0.0, 0.1], 0)["lse"], 0.744397, "lse 6 basamağa yuvarlanır")
ok(sozlesme(kararli_logsumexp_kayip), "1000.0 ve -1000.0 gibi uç logitlerde taşmadan LSE, olasılık ve Cross-Entropy gradyanı hesaplanmalı")

def m_dogrudan_exp(logitler, hedef_indeks):
    # m çıkarmadan doğrudan math.exp çağıran mutant -> 1000.0'da OverflowError verir!
    exps = [math.exp(x) for x in logitler]
    return {"lse": math.log(sum(exps)), "kayip": 0.0, "olasiliklar": [], "logit_gradyanlari": []}

def m_grad_yanlis(logitler, hedef_indeks):
    r = kararli_logsumexp_kayip(logitler, hedef_indeks)
    r["logit_gradyanlari"][hedef_indeks] += 1.0
    return r

for ad, mutant in [("maksimum çıkarmadan doğrudan exp() alan", m_dogrudan_exp), ("hedef sınıf gradyanından 1 çıkarmayı unutan", m_grad_yanlis)]:
    ok(not sozlesme(mutant), "hatalı çözüm/mutant yakalanmalı: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef kararli_logsumexp_kayip(logitler, hedef_indeks):\n    m = max(logitler)\n    exps = [math.exp(z - m) for z in logitler]\n    toplam_exp = sum(exps)\n    lse = m + math.log(toplam_exp)\n    kayip = lse - logitler[hedef_indeks]\n    olasiliklar = [e / toplam_exp for e in exps]\n    gradyanlar = [p - 1.0 if i == hedef_indeks else p for i, p in enumerate(olasiliklar)]\n    return {'lse': round(lse, 6), 'kayip': round(kayip, 6), 'olasiliklar': [round(p, 6) for p in olasiliklar], 'logit_gradyanlari': [round(g, 6) for g in gradyanlar]}", 'referans', 'exec'), _REF)
_t, _g = _ff(kararli_logsumexp_kayip, _REF['kararli_logsumexp_kayip'], ([1000.0, 1001.0, 1002.0], 2), tohum=3525, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (kararli_logsumexp_kayip): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def kararli_logsumexp_kayip(logitler, hedef_indeks):
    m = max(logitler)
    exps = [math.exp(z - m) for z in logitler]
    toplam_exp = sum(exps)
    lse = m + math.log(toplam_exp)
    kayip = lse - logitler[hedef_indeks]

    olasiliklar = [e / toplam_exp for e in exps]
    gradyanlar = [
        (p - 1.0) if i == hedef_indeks else p
        for i, p in enumerate(olasiliklar)
    ]

    return {
        "lse": round(lse, 6),
        "kayip": round(kayip, 6),
        "olasiliklar": [round(p, 6) for p in olasiliklar],
        "logit_gradyanlari": [round(g, 6) for g in gradyanlar],
    }
```

```hint
Önce `m = max(logitler)` bulup `exps = [math.exp(z - m) for z in logitler]` hesapla. `lse = m + math.log(sum(exps))` ve `kayip = lse - logitler[hedef_indeks]` olur. Geri yayılım gradyanı `i == hedef_indeks` için `p - 1.0`, diğerleri için `p` değeridir.
```
:::

::: gorev 3 · Bit Düzeyinde BF16 ve Gerçek E4M3 Izgarasına Yuvarlama
Görev 1'deki nicemleme tam sayıya yuvarlıyordu; gerçek `FP8 E4M3` ise 3 bitlik mantissa yüzünden her ikili aralıkta yalnız 8 değer tutar. `bf16_ve_e4m3_yuvarla(x)` işlevini yaz.

**BF16 (bit düzeyinde, round-to-nearest-even):** `struct` ile `x`'in FP32 bitlerini al (`>I`). Alt 16 biti atarken en yakına, eşitlikte çifte yuvarla: `lsb = (bitler >> 16) & 1`, `bitler = (bitler + 0x7FFF + lsb) & 0xFFFF0000`, sonra bitleri tekrar `float`'a çevir.

**E4M3 (OCP FP8, satüre eden):** $a = |x|$. $a = 0$ ise 0. $a \ge 448$ ise 448. Değilse `m, ex = math.frexp(a)` ile $e = \max(ex - 1, -6)$, adım $= 2^{e-3}$, $q = \text{round}(a / \text{adım}) \cdot \text{adım}$ (Python `round` eşitlikte çifte yuvarlar), $q > 448$ ise 448. İşareti geri koy. ($e = -6$ alt sınırı alt-normal sayıların sabit $2^{-9}$ adımını verir.)

**Çıktı:** `"fp32"` (`x`'in FP32'ye çevrilmiş değeri), `"bf16"`, `"e4m3"`, `"bf16_goreli_hata"`, `"e4m3_goreli_hata"` (`|yaklaşık − x| / |x|`, `round(·, 6)`; `x = 0` ise 0.0).

`x` sonlu bir sayı değilse, `bool` ise ya da $|x| > 3 \times 10^{38}$ ise `ValueError`.

```starter
def bf16_ve_e4m3_yuvarla(x):
    # KUSURLU BAŞLANGIÇ: hiçbir yuvarlama yapmıyor
    return {"fp32": x, "bf16": x, "e4m3": x, "bf16_goreli_hata": 0.0, "e4m3_goreli_hata": 0.0}

print(bf16_ve_e4m3_yuvarla(0.1))
```

```test
fn = need("bf16_ve_e4m3_yuvarla")
r = fn(0.1)
eq(r["bf16"], 0.10009765625, "0x3DCCCCCD → 0x3DCD0000")
eq(r["e4m3"], 0.1015625, "0.1 / 2^-7 = 12.8 → 13 · 2^-7")
eq(r["fp32"], 0.10000000149011612, "0.1'in FP32 karşılığı")
eq(r["bf16_goreli_hata"], 0.000977, "0.0009765625")
eq(r["e4m3_goreli_hata"], 0.015625, "0.0015625 / 0.1")
eq(fn(1.00390625)["bf16"], 1.0, "alt yarı tam 0x8000, üst lsb 0: aşağı (çifte) yuvarlanır")
eq(fn(1.01171875)["bf16"], 1.015625, "alt yarı 0x8000, üst lsb 1: yukarı (çifte) yuvarlanır")
eq(fn(112.5)["e4m3"], 112.0, "64–128 aralığında adım 8: 14.0625 → 14")
eq(fn(232.0)["e4m3"], 224.0, "adım 16: 14.5 → 14 (çift)")
eq(fn(248.0)["e4m3"], 256.0, "15.5 → 16 (çift)")
eq(fn(431.75)["e4m3"], 416.0, "Üst iki seviyenin orta noktasının hemen altı")
eq(fn(432.0)["e4m3"], 448.0, "Tam ortada 13 yerine çift katsayı 14 seçilir")
eq(fn(448.0)["e4m3"], 448.0, "En büyük temsil edilebilir değer korunur")
eq(fn(-448.25)["e4m3"], -448.0, "Negatif satürasyonda işaret korunur")

eq(fn(1000.0)["e4m3"], 448.0, "satürasyon")
eq(fn(-0.001)["e4m3"], -0.001953125, "alt-normal adım 2^-9: 0.512 → 1 adım")
r0 = fn(0.0001)
eq(r0["e4m3"], 0.0, "en küçük alt-normalin yarısından küçük: sıfıra düşer")
eq(r0["e4m3_goreli_hata"], 1.0, "tam kayıp")
eq(fn(0.0)["bf16_goreli_hata"], 0.0, "x = 0")
eq(math.copysign(1.0, fn(-0.0)["e4m3"]), 1.0, "-0.0 için e4m3 +0.0 döner")
eq(fn(3e38)["e4m3"], 448.0, "üst sınır 3e38 geçerlidir")
eq(fn(2e38)["e4m3"], 448.0, "2e38 geçerlidir")
raises(ValueError, fn, 3.01e38)
raises(ValueError, fn, float("nan"))
raises(ValueError, fn, float("inf"))
raises(ValueError, fn, True)
raises(ValueError, fn, 1e39)
raises(ValueError, fn, "1.0")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\nimport struct\n\ndef bf16_ve_e4m3_yuvarla(x):\n    if isinstance(x, bool) or not isinstance(x, (int, float)) or (not math.isfinite(x)) or (abs(x) > 3e+38):\n        raise ValueError('x sonlu ve |x| <= 3e38 olmalı')\n    fp32 = struct.unpack('>f', struct.pack('>f', x))[0]\n    bitler = struct.unpack('>I', struct.pack('>f', x))[0]\n    lsb = bitler >> 16 & 1\n    bitler = bitler + 32767 + lsb & 4294901760\n    bf16 = struct.unpack('>f', struct.pack('>I', bitler))[0]\n    a = abs(x)\n    if a == 0:\n        q = 0.0\n    elif a >= 448.0:\n        q = 448.0\n    else:\n        _, ex = math.frexp(a)\n        e = max(ex - 1, -6)\n        adim = 2.0 ** (e - 3)\n        q = min(round(a / adim) * adim, 448.0)\n    e4m3 = math.copysign(q, x) if q else 0.0\n\n    def hata(y):\n        return round(abs(y - x) / abs(x), 6) if x else 0.0\n    return {'fp32': fp32, 'bf16': bf16, 'e4m3': e4m3, 'bf16_goreli_hata': hata(bf16), 'e4m3_goreli_hata': hata(e4m3)}", 'referans', 'exec'), _REF)
_t, _g = _ff(bf16_ve_e4m3_yuvarla, _REF['bf16_ve_e4m3_yuvarla'], (0.1,), tohum=2947, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (bf16_ve_e4m3_yuvarla): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math
import struct

def bf16_ve_e4m3_yuvarla(x):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or abs(x) > 3e38:
        raise ValueError("x sonlu ve |x| <= 3e38 olmalı")
    fp32 = struct.unpack(">f", struct.pack(">f", x))[0]
    bitler = struct.unpack(">I", struct.pack(">f", x))[0]
    lsb = (bitler >> 16) & 1
    bitler = (bitler + 0x7FFF + lsb) & 0xFFFF0000
    bf16 = struct.unpack(">f", struct.pack(">I", bitler))[0]
    a = abs(x)
    if a == 0:
        q = 0.0
    elif a >= 448.0:
        q = 448.0
    else:
        _, ex = math.frexp(a)
        e = max(ex - 1, -6)
        adim = 2.0 ** (e - 3)
        q = min(round(a / adim) * adim, 448.0)
    e4m3 = math.copysign(q, x) if q else 0.0

    def hata(y):
        return round(abs(y - x) / abs(x), 6) if x else 0.0

    return {"fp32": fp32, "bf16": bf16, "e4m3": e4m3, "bf16_goreli_hata": hata(bf16), "e4m3_goreli_hata": hata(e4m3)}
```

```hint
`math.frexp(a)` `a = m · 2^ex`, `0.5 <= m < 1` verir; yani `floor(log2(a)) = ex - 1`. Adım ikinin kuvveti olduğu için bölme kesindir.
```
:::

::: anlat Gerçek deney: Gerçek ağırlıklarda BF16/E4M3, gerçek logit'lerde LogSumExp ve FP8 modelin perplexity'si
Final, torch'un gerçek düşük hassasiyet türlerini (`torch.bfloat16`, `torch.float8_e4m3fn`) ve SmolLM2-135M'in gerçek ağırlıklarını kullanır (FP8 donanımı gerekmez):

- **Bit bit yuvarlama:** 7. katmanın `down_proj` ağırlığından 1 500 rastgele değer ve 128'lik bir bloğun ölçeklenmiş değerleri senin `bf16_ve_e4m3_yuvarla` işlevine verilir; her sonuç torch dönüşümüyle **tam eşitlik** için karşılaştırılır. Ham ağırlıklar (~0.02) E4M3'ün alt normal (subnormal) bölgesine düşer; ölçekleme onları normal bölgeye taşır.
- **Blok nicemleme:** görev 1'deki `fp8_blok_nicele` x/ölçek değerini **tam sayıya** yuvarlar: −448…448 arası 897 seviye, yani yaklaşık 10 bit. Gerçek E4M3 ise 8 bittir ve büyük değerlerde adımı 32'ye çıkar. Aynı blokta iki ızgaranın hatası yan yana ölçülür.
- **Kararlı LogSumExp:** 49 152 sözcüklük gerçek bir logit vektörü senin `kararli_logsumexp_kayip` işlevine verilir; LSE, kayıp ve logit gradyanları `torch.logsumexp`, `cross_entropy` ve autograd ile karşılaştırılır. Aynı logit'lerde naif `exp` fp16'da binlerce sonsuz üretir ve kayıp `NaN` olur.
- **FP8 model:** tüm doğrusal katmanların ağırlıkları E4M3'e (blok ölçekli ve tensör ölçekli) ve karşılaştırma için INT8'e nicemlenir; gerçek bir paragrafta perplexity ölçülür.

**Güvenlik yönü — nicemlenmiş model ayrı bir modeldir:** FP8 ve INT8'e nicemlenmiş SmolLM2'ler fp32 ile aynı paragrafta ve beş istemde (bazıları güvenlikle ilgili) karşılaştırılır. Sonraki token kararlarının bir kısmı ve açgözlü üretimlerin çoğu değişir. Bir modelin güvenlik değerlendirmesi, dağıtılan **nicemlenmiş** sürümünde tekrarlanmalıdır; yalnız nicemlenince ortaya çıkan davranışlar ve arka kapılar gösterilmiştir.

Kabul: üç işlevin farksal taramayı geçmesi; BF16 ve E4M3 sonuçlarının torch ile birebir aynı olması; blok nicemlemenin torch referansıyla aynı olması; LSE/kayıp/gradyanın torch ile aynı olması; FP8 blok ölçekli modelin perplexity'sinin fp32'nin en çok %10 üstünde kalması. Ayrıca nicemlenmiş modellerin en az birinin üretimi ve INT8'in token kararları fp32'den farklı olmalıdır.

**Kanıt dosyasını oku:** `ham_agirlik_e4m3_goreli_hata`, `olcekli_e4m3_goreli_hata`, `blok_tamsayi_mae`, `blok_e4m3_mae`, `naif_fp16_inf`, `ppl_fp32`, `ppl_fp8_blok`, `ppl_fp8_tensor`, `ppl_int8_tensor`. Soru 1: E4M3'te blok ölçek ile tensör ölçek neden neredeyse aynı perplexity veriyor da INT8'de tensör ölçek belirgin kötüleşiyor? Soru 2: Görev 1'in ızgarası neden gerçek FP8'den daha az hata veriyor ve bu bir avantaj mı? Soru 3: Naif softmax hangi logit büyüklüğünde fp16'da taşar?
:::

::: gorev Gerçek deney · Gerçek SmolLM2 ağırlık ve logit'lerinde BF16, E4M3, LogSumExp ve FP8 perplexity
Önceki görevlerdeki `fp8_blok_nicele`, `kararli_logsumexp_kayip`, `bf16_ve_e4m3_yuvarla` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 240
```
```starter
import ai_lab
def fp8_blok_nicele(degerler, maks_temsil=448.0):
    n = len(degerler)
    return {'amax': 0.0, 'olcek': 1.0, 'nicelenmis': [0.0] * n, 'geri_acilmis': [0.0] * n, 'mae': 0.0}

def kararli_logsumexp_kayip(logitler, hedef_indeks):
    n = len(logitler)
    return {'lse': 0.0, 'kayip': 0.0, 'olasiliklar': [0.0] * n, 'logit_gradyanlari': [0.0] * n}

def bf16_ve_e4m3_yuvarla(x):
    return {'fp32': x, 'bf16': x, 'e4m3': x, 'bf16_goreli_hata': 0.0, 'e4m3_goreli_hata': 0.0}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_14 as D
    D.goster(fp8_blok_nicele, kararli_logsumexp_kayip, bf16_ve_e4m3_yuvarla)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_fp8_model', '_ppl', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
fp8_blok_nicele = need("fp8_blok_nicele")
kararli_logsumexp_kayip = need("kararli_logsumexp_kayip")
bf16_ve_e4m3_yuvarla = need("bf16_ve_e4m3_yuvarla")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def fp8_blok_nicele(degerler, maks_temsil=448.0):\n    amax = max((abs(x) for x in degerler)) if degerler else 0.0\n    olcek = amax / maks_temsil if amax > 0.0 else 1.0\n    nicelenmis = []\n    geri_acilmis = []\n    for x in degerler:\n        q = float(round(x / olcek))\n        if q > maks_temsil:\n            q = float(maks_temsil)\n        elif q < -maks_temsil:\n            q = float(-maks_temsil)\n        nicelenmis.append(round(q, 6))\n        geri_acilmis.append(round(q * olcek, 6))\n    mae = sum((abs(x - x_hat) for x, x_hat in zip(degerler, geri_acilmis))) / len(degerler) if degerler else 0.0\n    return {'amax': round(amax, 6), 'olcek': round(olcek, 6), 'nicelenmis': nicelenmis, 'geri_acilmis': geri_acilmis, 'mae': round(mae, 6)}\n\nimport math\n\ndef kararli_logsumexp_kayip(logitler, hedef_indeks):\n    m = max(logitler)\n    exps = [math.exp(z - m) for z in logitler]\n    toplam_exp = sum(exps)\n    lse = m + math.log(toplam_exp)\n    kayip = lse - logitler[hedef_indeks]\n    olasiliklar = [e / toplam_exp for e in exps]\n    gradyanlar = [p - 1.0 if i == hedef_indeks else p for i, p in enumerate(olasiliklar)]\n    return {'lse': round(lse, 6), 'kayip': round(kayip, 6), 'olasiliklar': [round(p, 6) for p in olasiliklar], 'logit_gradyanlari': [round(g, 6) for g in gradyanlar]}\n\nimport math\nimport struct\n\ndef bf16_ve_e4m3_yuvarla(x):\n    if isinstance(x, bool) or not isinstance(x, (int, float)) or (not math.isfinite(x)) or (abs(x) > 3e+38):\n        raise ValueError('x sonlu ve |x| <= 3e38 olmalı')\n    fp32 = struct.unpack('>f', struct.pack('>f', x))[0]\n    bitler = struct.unpack('>I', struct.pack('>f', x))[0]\n    lsb = bitler >> 16 & 1\n    bitler = bitler + 32767 + lsb & 4294901760\n    bf16 = struct.unpack('>f', struct.pack('>I', bitler))[0]\n    a = abs(x)\n    if a == 0:\n        q = 0.0\n    elif a >= 448.0:\n        q = 448.0\n    else:\n        _, ex = math.frexp(a)\n        e = max(ex - 1, -6)\n        adim = 2.0 ** (e - 3)\n        q = min(round(a / adim) * adim, 448.0)\n    e4m3 = math.copysign(q, x) if q else 0.0\n\n    def hata(y):\n        return round(abs(y - x) / abs(x), 6) if x else 0.0\n    return {'fp32': fp32, 'bf16': bf16, 'e4m3': e4m3, 'bf16_goreli_hata': hata(bf16), 'e4m3_goreli_hata': hata(e4m3)}", 'referans', 'exec'), _REF)
_t, _g = _ff(fp8_blok_nicele, _REF['fp8_blok_nicele'], ([896.0, -448.0, 224.0, -10.5], 448.0), tohum=2563, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (fp8_blok_nicele): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(kararli_logsumexp_kayip, _REF['kararli_logsumexp_kayip'], ([1000.0, 1001.0, 1002.0], 2), tohum=3525, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (kararli_logsumexp_kayip): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(bf16_ve_e4m3_yuvarla, _REF['bf16_ve_e4m3_yuvarla'], (0.1,), tohum=2947, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (bf16_ve_e4m3_yuvarla): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
import math as _m14
def _birim_14():
    for _args in (([],), ([0.0, 0.0], 448.0), ([448.0],), ([0.5], 448.0), ([0.1234567],), ([10.0], 1.6234567)):
        if fp8_blok_nicele(*_args) != _REF['fp8_blok_nicele'](*_args):
            return False
    if kararli_logsumexp_kayip([0.0, 0.1], 0) != _REF['kararli_logsumexp_kayip']([0.0, 0.1], 0):
        return False
    for _x in (0.0, -0.0, 1.00390625, 1.01171875, 232.0, 248.0, 432.0, 448.0, -448.25, 1000.0, 2e38, 3e38):
        if bf16_ve_e4m3_yuvarla(_x) != _REF['bf16_ve_e4m3_yuvarla'](_x):
            return False
    if _m14.copysign(1.0, bf16_ve_e4m3_yuvarla(-0.0)["e4m3"]) != 1.0:
        return False
    for _bad in (float("nan"), float("inf"), 3.01e38, 1e39, True, "1.0"):
        try:
            bf16_ve_e4m3_yuvarla(_bad)
            return False
        except ValueError:
            pass
    return True
kontrol(_birim_14(), "FP8 boş/varsayılan blok, LSE yuvarlama ve BF16/E4M3 bit sınır sözleşmesi")
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_14 as D
try: r = D.deney(fp8_blok_nicele, kararli_logsumexp_kayip, bf16_ve_e4m3_yuvarla)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['yuvarlama_ayni'], 'BF16 ve E4M3 yuvarlaması gerçek ağırlıklarda torch dönüşümüyle birebir aynı')
kontrol(r['blok_ayni'], 'blok nicemleme gerçek blokta torch referansıyla aynı')
kontrol(r['lse_ayni'], "LogSumExp, kayıp ve logit gradyanları 49 152 gerçek logit'te torch ile aynı")
kontrol(r['fp8_kucuk_kayip'] and r['naif_fp16_inf'] > 0, "FP8 blok ölçekli model perplexity'yi en çok %10 artırıyor; naif fp16 exp taşıyor")
kontrol(r['nicemleme_davranisi_degistirir'], 'nicemleme gerçek modelin token kararlarını ve üretimlerini değiştirdi')
ai_lab.kanit_yaz("ai-uretim-14-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-14", "deney": r})
```
```solution
import ai_lab
def fp8_blok_nicele(degerler, maks_temsil=448.0):
    amax = max((abs(x) for x in degerler)) if degerler else 0.0
    olcek = amax / maks_temsil if amax > 0.0 else 1.0
    nicelenmis = []
    geri_acilmis = []
    for x in degerler:
        q = float(round(x / olcek))
        if q > maks_temsil:
            q = float(maks_temsil)
        elif q < -maks_temsil:
            q = float(-maks_temsil)
        nicelenmis.append(round(q, 6))
        geri_acilmis.append(round(q * olcek, 6))
    mae = sum((abs(x - x_hat) for x, x_hat in zip(degerler, geri_acilmis))) / len(degerler) if degerler else 0.0
    return {'amax': round(amax, 6), 'olcek': round(olcek, 6), 'nicelenmis': nicelenmis, 'geri_acilmis': geri_acilmis, 'mae': round(mae, 6)}

import math

def kararli_logsumexp_kayip(logitler, hedef_indeks):
    m = max(logitler)
    exps = [math.exp(z - m) for z in logitler]
    toplam_exp = sum(exps)
    lse = m + math.log(toplam_exp)
    kayip = lse - logitler[hedef_indeks]
    olasiliklar = [e / toplam_exp for e in exps]
    gradyanlar = [p - 1.0 if i == hedef_indeks else p for i, p in enumerate(olasiliklar)]
    return {'lse': round(lse, 6), 'kayip': round(kayip, 6), 'olasiliklar': [round(p, 6) for p in olasiliklar], 'logit_gradyanlari': [round(g, 6) for g in gradyanlar]}

import math
import struct

def bf16_ve_e4m3_yuvarla(x):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or (not math.isfinite(x)) or (abs(x) > 3e+38):
        raise ValueError('x sonlu ve |x| <= 3e38 olmalı')
    fp32 = struct.unpack('>f', struct.pack('>f', x))[0]
    bitler = struct.unpack('>I', struct.pack('>f', x))[0]
    lsb = bitler >> 16 & 1
    bitler = bitler + 32767 + lsb & 4294901760
    bf16 = struct.unpack('>f', struct.pack('>I', bitler))[0]
    a = abs(x)
    if a == 0:
        q = 0.0
    elif a >= 448.0:
        q = 448.0
    else:
        _, ex = math.frexp(a)
        e = max(ex - 1, -6)
        adim = 2.0 ** (e - 3)
        q = min(round(a / adim) * adim, 448.0)
    e4m3 = math.copysign(q, x) if q else 0.0

    def hata(y):
        return round(abs(y - x) / abs(x), 6) if x else 0.0
    return {'fp32': fp32, 'bf16': bf16, 'e4m3': e4m3, 'bf16_goreli_hata': hata(bf16), 'e4m3_goreli_hata': hata(e4m3)}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_14 as D
    D.goster(fp8_blok_nicele, kararli_logsumexp_kayip, bf16_ve_e4m3_yuvarla)
```
```hint
Üç görevin çözümlerini olduğu gibi buraya koy.
```
:::

::: anlat Sınır
Görevler blok bazlı FP8 E4M3 nicemlemesini ve taşmaya dayanıklı LogSumExp ile cross-entropy'yi saf Python ile hesaplatır; final adım sonuçları torch.float8_e4m3fn ve bfloat16 dönüşümleriyle karşılaştırır (FP8 donanımı kullanılmaz). Görevdeki nicemleme x/ölçek değerini tam sayıya yuvarlar; gerçek E4M3'te mantissa 3 bit olduğu için örneğin 64–128 aralığındaki temsil edilebilir değerler 8'er 8'er ilerler, yani gerçek nicemleme hatası görevdekinden çok daha büyüktür. E4M3 en fazla 448'e kadar temsil eder; aykırı değerler ölçeği bozar, bu yüzden blok başına ölçek gerekir. FP8 eğitimi gradyanlar için genelde E5M2 ve yüksek hassasiyetli birikim (FP32 accumulate) ister; birikim de düşük hassasiyette yapılırsa hata büyür. BF16 ve E4M3 görevi tek sayılar üzerinde çalışır; TF32 yalnız anlatımdadır.

Kaynaklar: [Micikevicius vd. 2022 - FP8 Formats for Deep Learning](https://arxiv.org/abs/2209.05433), [Kalamkar vd. 2019 - A Study of BFLOAT16 for Deep Learning Training](https://arxiv.org/abs/1905.12322), [DeepSeek-AI 2024 - DeepSeek-V3 Technical Report](https://arxiv.org/abs/2412.19437).
:::

::: dusun
Karma hassasiyetli (**Mixed-Precision `BF16 / FP8`**) eğitimde ileri ve backpropagation `16-bit` veya `8-bit` yapıldığı halde, neden **Optimizer içindeki `Master Weights` (Ana Ağırlıklar) ve AdamW momentleri (`m, v`) mutlaka `FP32` (32-bit) olarak saklanır?**

Şu matematiksel senaryoyu düşün: Bir ağırlığın değeri $w = 1.0$ (`BF16`'da 7 bit mantissa ile makine epsilonu $\epsilon_{\text{bf16}} = 2^{-7} \approx 0.0078$) olsun. learning rate $\eta = 10^{-4}$ ve gradyan $g = 1.0$ olduğunda ağırlık güncellemesi $\Delta w = -\eta \cdot g = -0.0001$'dir. Eğer ana ağırlığı `FP32` yerine `BF16` tutarsan $1.0 - 0.0001$ çıkarma işleminde ne olur (**`Swamping / Underflow of Small Updates`**) ve model neden öğrenmeyi tamamen durdurur?
:::

::: ozet
- Kayan nokta formatlarında **`Exponent`** bitleri sayının dinamik aralığını (**Dynamic Range**), **`Mantissa`** bitleri ise hassasiyetini (**Precision**) belirler; `FP16 (1-5-10)` dar üs aralığı yüzünden `65,504` üstünde taşarken, **`BF16 (1-8-7)`** `FP32` ile aynı 8-bit üs genişliğini koruyarak taşmaları önler.
- **Hibrit `FP8`** eğitiminde ileri yayılımda hassasiyet için **`E4M3`** (maks `448`), backpropagation gradyanlarında ise geniş dinamik aralık için **`E5M2`** (maks `57,344`) kullanılır ve her tensör bloğu kendi mutlak maksimumuyla (**Per-Block AbsMax Scaling**) ölçeklenir.
- **`LogSumExp Trick`** ($\text{LSE}(z) = m + \log\sum e^{z_j - m}$), üs almadan önce maksimum logiti çıkararak en büyük üssü $e^0 = 1$ değerine sabitler ve `Softmax / Cross-Entropy` hesaplarında `Overflow` tehlikesini matematiksel olarak ortadan kaldırır.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Aralık mı hassasiyet mi? (30 sn).** "`FP16` 5 üs bitiyle `65.504` üstünde taşarken, `BF16` `FP32`'nin 8 üs bitini koruyup mantissayı 7 bite indirir: taşmayı önler ama küçük güncellemeleri yutabilir (`swamping`)."
2. **Blok ölçekli `FP8` (`E4M3`) (30 sn).** "`E4M3` en fazla `448` temsil eder; tensörü bloklara bölüp her bloğu kendi `absmax / 448` çarpanıyla ölçeklemek tek bir aykırı değerin bütün tensörü sıfıra ezmesini engeller."
3. **`LogSumExp` kaydırması (35 sn).** "Büyük logitlerde doğrudan `exp(z)` sonsuza taşar; en büyük logiti çıkarmak ($z_j - m$) en büyük terimi $e^0 = 1$ yapar ve çapraz entropiyi bit düzeyinde kararlı tutar."
4. **Soru (25 sn).** "Ağırlıkları `E4M3` ızgarasına indirdiğimizde SmolLM2 `perplexity` artışı sınırlı kalırken, neden ana ağırlık kopyasını (`master weights`) eğitimde hâlâ `FP32` tutmak zorundayız?"
:::
