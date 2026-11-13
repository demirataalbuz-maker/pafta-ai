---
id: ai-uretim-07
title: "Pre-Training Loop Mühendisliği: AdamW, WSD Learning Rate Scheduler ve Mixed Precision"
track: ai-uretim
order: 7
duration_minutes: 40
difficulty: ileri
xp: 300
prerequisites: [ai-uretim-06]
esleme: ai-temel-09, ai-uretim-01, ai-uretim-14
summary: "Trilyon tokenlik Pre-Training döngüsü nasıl yazılır? Autoregressive Shifted Cross-Entropy Loss, Decoupled Weight Decay AdamW, Warmup-Stable-Decay (WSD) takvimi, Gradient Accumulation, Global Gradient Norm Clipping ve BF16/FP8 Mixed Precision."
tags: [pre-training, adamw, wsd-scheduler, gradient-clipping, mixed-precision, gradient-accumulation]
---

::: anlat 1. 15 Trilyon Token Boyunca Çökmeden Çalışan Pre-Training Döngüsünün Anatomisi
## Pre-training loop bileşenleri

Bir training loop; loss hesabı, gradient biriktirme, optimizer adımı ve learning-rate planının birlikte yürütülmesidir. Bu derste AdamW güncellemesini, global gradient norm clipping işlemini ve WSD planını hesaplayacaksın. Modelin eğitilmesi ile bu güncellemelerin küçük sayısal örneklerle doğru hesaplanması farklı kabul koşullarıdır.

Bir konferansta `Frontier LLM` ön-eğitimini (`Pre-Training`) anlatırken dinleyicilere şu gerçeği göster:
> *"Milyonlarca dolarlık GPU kümesinde 3 ay boyunca kesintisiz süren bir `Pre-Training` koşusu, otoyolda saatte 300 km hızla giden bir Formula 1 aracı gibidir. Tek bir katmanda oluşan sayısal taşma (`FP16 Overflow`), yanlış ayarlanmış bir öğrenme oranı (`Learning Rate Spike`) veya patlayan bir gradyan (`Gradient Explosion`) tüm ağırlıkları saniyeler içinde `NaN` (`Not-a-Number`) yapar ve haftalık emeği çöpe atar!"*

Bir `Pre-Training` motorunun sarsılmaz kalbi şu **5 mühendislik dişlisinin** kusursuz uyumuyla döner:

```text
  [1. AUTOREGRESSIVE SHIFTED CROSS-ENTROPY LOSS]
      • Girdi: x = tokens[:-1], Hedef: y = tokens[1:] -> -log P(y_t | x_<=t)
                                    │
                                    ▼
  [2. GRADIENT ACCUMULATION & MIXED PRECISION (BF16 / FP8 + FP32 Master Weights)]
      • K mikro-batch boyunca gradyanları biriktir (g_acc += g_micro / K)
                                    │
                                    ▼
  [3. GLOBAL GRADIENT NORM CLIPPING (clip_grad_norm_ <= 1.0)]
      • ||G||_2 > max_norm ise tüm gradyanları (max_norm / ||G||_2) ile küçült!
                                    │
                                    ▼
  [4. WARMUP-STABLE-DECAY (WSD) LEARNING RATE SCHEDULER]
      • Doğrusal ısınma (Warmup) -> Uzun sabit plato (Stable) -> Hızlı sönümleme (Decay)
                                    │
                                    ▼
  [5. DECOUPLED WEIGHT DECAY ADAMW OPTIMIZER ADIMI]
      • 1. Moment (m_t), 2. Moment (v_t), Bias Correction ve Ayrık Ağırlık Çürümesi!
```

### 🎯 Adım 1: `Autoregressive Shifted Cross-Entropy Loss` ve `Perplexity`
Dil modelinin tek bir görevi vardır: **Bir sonraki `token`'ı tahmin etmek (`Next-Token Prediction`)!**
Uzunluğu $T+1$ olan bir `token` dizisi $[w_0, w_1, w_2, \dots, w_T]$ geldiğinde:
- Modele **Girdi (`inputs`)** olarak ilk $T$ eleman verilir: $X = [w_0, w_1, \dots, w_{T-1}]$
- Modelden beklenen **Hedef (`targets`)** ise bir sağa kaydırılmış (`Shifted`) dizidir: $Y = [w_1, w_2, \dots, w_T]$

Her $t$ adımında modelin doğru hedef `token` $y_t$'ye verdiği olasılık $p_{t, y_t}$ ise ortalama **`Cross-Entropy Loss`** ($\mathcal{L}$) ve modelin şaşkınlık ölçütü olan **`Perplexity` ($\text{PPL}$)**:

$$\mathcal{L} = -\frac{1}{T}\sum_{t=0}^{T-1} \ln P(y_t \mid w_{\le t}), \qquad \text{Perplexity (PPL)} = e^{\mathcal{L}}$$

Eğer modelin sözlük boyutu $V = 100.000$ ise, eğitimin ilk saniyesinde rastgele tahmin yapan bir modelin kaybı $\mathcal{L} \approx \ln(100.000) \approx 11.51$ (`PPL = 100.000`), iyi eğitilmiş bir `Frontier` modelin kaybı ise $\mathcal{L} \approx 1.80$ (`PPL ≈ 6.0`) civarındadır!

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [PyTorch AdamW](https://docs.pytorch.org/docs/stable/generated/torch.optim.AdamW.html). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: anlat 2. Standart Adam Neden Kusurludur ve AdamW (Decoupled Weight Decay) Nasıl Çalışır?
Derin öğrenmede yıllarca kullanılan standart `Adam` optimizer'da büyük bir matematiksel hata vardı (Loshchilov & Hutter, 2019 — **`AdamW`** makalesi):
- Standart `L2 Regularization`, ağırlık cezasını ($\lambda \theta_t$) doğrudan gradyanın içine ekliyordu: $g_t \leftarrow g_t + \lambda \theta_t$.
- Ancak `Adam`, gradyanları ikinci momentin kareköküne ($\sqrt{\hat{v}_t}$) böldüğü için, **büyük gradyan alan ağırlıklarda ağırlık çürümesi (`Weight Decay`) etkisi tamamen eziliyor ve yok oluyordu!**

**`AdamW` (`Adam with Decoupled Weight Decay`)**, ağırlık çürümesini gradyan hesabından tamamen **ayırır (`Decouple`)** ve doğrudan parametre güncellemesine uygular! Her $t \ge 1$ adımında bir $\theta_{t-1}$ parametresi ve $g_t$ gradyanı için **4 aşamalı `AdamW` denklemi** şöyledir:

1. **Birinci Moment (`Momentum` — Gradyanların Üstel Hareketli Ortalaması):**
   $$m_t = \beta_1 m_{t-1} + (1 - \beta_1) g_t$$
2. **İkinci Moment (`Uncentered Variance` — Gradyan Karelerinin Ortalaması):**
   $$v_t = \beta_2 v_{t-1} + (1 - \beta_2) g_t^2$$
3. **Sıfır Başlangıç Önyargı Düzeltmesi (`Bias Correction`):** ($m_0 = 0, v_0 = 0$ başladığı için ilk adımlarda sıfıra yakın kalmalarını düzeltir):
   $$\hat{m}_t = \frac{m_t}{1 - \beta_1^t}, \qquad \hat{v}_t = \frac{v_t}{1 - \beta_2^t}$$
4. **Ayrık Ağırlık Çürümesi (`Decoupled Weight Decay`) + Adaptif Adım:**
   $$\theta_t = \theta_{t-1} - \eta_t \left( \frac{\hat{m}_t}{\sqrt{\hat{v}_t} + \epsilon} + \lambda \theta_{t-1} \right)$$

> **Frontier Hiperparametre Sırrı:** `Llama-3`, `DeepSeek-V3` ve `Qwen` modellerinde standart $(\beta_1=0.9, \beta_2=0.999)$ yerine **`(\beta_1 = 0.9, \beta_2 = 0.95)`** ve `weight_decay` $\lambda = 0.1$ kullanılır! Çünkü $\beta_2 = 0.999$ olduğunda ikinci moment geçmişteki bir gradyan sıçramasını binlerce adım boyunca unutmaz ve eğitimi kilitler; $\beta_2 = 0.95$ ise çok daha çeviktir! (`Embedding` ve `RMSNorm` katmanlarına ise `weight_decay = 0.0` uygulanır).
:::

::: anlat 3. Cosine Schedule'dan Warmup-Stable-Decay (WSD) Yaklaşımına ve Gradient Clipping'e
### 📈 Neden `Cosine Annealing` Yerine `Warmup-Stable-Decay (WSD)` Kullanılıyor?
Eskiden modeller `Cosine Learning Rate Schedule` ile eğitilirdi. Ancak `Cosine` takviminde çok büyük bir sorun vardır: **Eğitimin kaç trilyon `token` süreceğini (`T_max`) en baştan kesin olarak bilmek zorundasındır!** Eğer $10\text{T token}$ planlayıp bütçen arttığında modeli $15\text{T token}$'a uzatmak istersen, learning rate çoktan sıfıra indiği için devam edemezsin!

Modern `Frontier` modellerin (`MiniCPM`, `DeepSeek-V3`, `Llama-3` türevleri) kullandığı **`Warmup-Stable-Decay (WSD)`** takvimi eğitimi **3 esnek evreye** ayırır:
1. **`Warmup Phase` ($0 \le t \le T_{\text{warmup}}$):** learning rate $0$'dan $\eta_{\max}$ değerine doğrusal olarak çıkar ($\eta_t = \eta_{\max} \cdot \frac{t}{T_{\text{warmup}}}$). İlk adımlarda rastgele ağırlıkların dağılmasını önler.
2. **`Stable Phase` ($T_{\text{warmup}} < t \le T_{\text{warmup}} + T_{\text{stable}}$):** learning rate trilyonlarca `token` boyunca **sabit $\eta_{\max}$** değerinde tutulur! İstediğin kadar yeni veri ekleyip eğitimi sonsuza dek sürdürebilirsin!
3. **`Decay / Cool-down Phase` ($t > T_{\text{warmup}} + T_{\text{stable}}$):** Eğitimi bitirmeye karar verdiğin son `%10-%15`'lik dilimde learning rate hızla $\eta_{\min}$ değerine düşürülür (doğrusal veya kosinüs sönümleme ile) ve yüksek kaliteli veriyle modelin `Loss` değeri bir anda keskin biçimde aşağı çekilir!

### 🛡️ `Gradient Accumulation` ve `Global Gradient Norm Clipping`
- **`Gradient Accumulation`:** Modeli kararlı eğitmek için adım başına $4\text{ Milyon token}$ (`Global Batch Size`) gerekir ama GPU belleğine tek seferde sadece $8\text{ dizi}$ (`Micro-Batch`) sığar. Çözüm: $K$ adet `Micro-Batch` boyunca ileri ve backpropagation yapıp gradyanları $(1/K)$ ile ölçekleyerek üst üste toplamak (`Accumulate`) ve `optimizer.step()` adımını sadece $K$ adımda bir atmaktır!
- **`Global Gradient Norm Clipping` (`max_norm = 1.0`):** backpropagation bittiğinde modeldeki tüm parametrelerin gradyanlarının birleşik Öklid normu (**`Global L2 Norm`** $\|G\|_2 = \sqrt{\sum_i g_i^2}$) hesaplanır. Eğer $\|G\|_2 > \text{max\_norm}$ ise, **gradyanların yönünü hiç bozmadan** tüm gradyanlar aynı katsayıyla küçültülür:

$$\text{Eğer } \|G\|_2 > C \quad \Longrightarrow \quad g_i \leftarrow g_i \cdot \frac{C}{\|G\|_2}$$

### ⚡ `Mixed Precision`: Neden `FP16` Yerine `BF16` (`Brain Float 16`) ve `FP8`?
- **`FP16` (`1 işaret, 5 üs, 10 kesir biti`):** Maksimum $65.504$ sayısını temsil edebilir! Aktivasyon veya gradyan $65.505$ olduğu anda **`Overflow` (`Inf / NaN`)** olur, bu yüzden karmaşık bir `Dynamic Loss Scaler` (`GradScaler`) gerektirir.
- **`BF16` (`1 işaret, 8 üs, 7 kesir biti`):** Tıpkı `FP32` gibi **8 bit üs (`Exponent`)** kullanır! Yani `FP32` ile birebir aynı devasa sayı aralığına ($\sim 3.4 \times 10^{38}$) sahiptir; **asla kolayca `Overflow` olmaz**, `Loss Scaler` gerektirmeden yarı bellek (`2 Byte`) ve 2 kat `Tensor Core` hızı sağlar! (Ağırlık güncellemelerinde hassasiyet kaybı olmaması için `Master Weights` ve `AdamW` momentleri ise `FP32` olarak tutulur).
:::

::: anlat 4. Gerçek PyTorch Pre-Training Döngüsü (Üretim Kodu)
Aşağıda `BF16 Automatic Mixed Precision`, `Gradient Accumulation`, `Global Gradient Clipping` ve `WSD Scheduler` içeren gerçek bir `PyTorch` ön-eğitim döngüsünü (`Training Loop`) inceleyebilirsin:

```python norun
import torch
import torch.nn.functional as F

def train_step_frontier(model, optimizer, data_iter, grad_accum_steps: int, max_norm: float = 1.0):
    optimizer.zero_grad(set_to_none=True)
    total_loss = 0.0

    for micro_step in range(grad_accum_steps):
        batch_tokens = next(data_iter)           # [B, T + 1]
        inputs  = batch_tokens[:, :-1].cuda()    # [B, T]
        targets = batch_tokens[:, 1:].cuda()     # [B, T] (1 sağa kaydırılmış hedef!)

        # BF16 Mixed Precision ile hızlı ve taşmasız ileri yayılım
        with torch.amp.autocast(device_type="cuda", dtype=torch.bfloat16):
            logits = model(inputs)               # [B, T, Vocab]
            loss = F.cross_entropy(logits.view(-1, logits.size(-1)), targets.view(-1))
            scaled_loss = loss / grad_accum_steps

        scaled_loss.backward()
        total_loss += loss.item() / grad_accum_steps

    # Global Gradient Norm Clipping (Patlayan gradyanlara karşı emniyet sübabı)
    grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=max_norm)
    optimizer.step()
    return total_loss, grad_norm.item()
```
:::

::: tahmin Global Gradient Norm Clipping ve Perplexity Hesabı
Bir eğitim adımında modelin `Cross-Entropy Loss` değeri $\mathcal{L} = 2.0$ olarak ölçülmüş ve iki parametreli bir katmanın gradyan vektörü $G = [6.0, 8.0]$ çıkmıştır. `max_norm = 5.0` sınırı uygulandığında kırpılmış (`clipped`) gradyan vektörü ve modelin `Perplexity` ($e^{\mathcal{L}}$) değeri ne olur?

```python
import math

loss = 2.0
g = [6.0, 8.0]
max_norm = 5.0

norm = math.sqrt(sum(x * x for x in g))
olcek = (max_norm / norm) if norm > max_norm else 1.0
g_clipped = [round(x * olcek, 2) for x in g]
ppl = round(math.exp(loss), 2)
print(f"Norm: {norm:.1f} -> Clipped: {g_clipped} | PPL: {ppl}")
```

???

```cikti
Norm: 10.0 -> Clipped: [3.0, 4.0] | PPL: 7.39
```
Gradyan vektörünün Öklid normu $\|G\|_2 = \sqrt{6^2 + 8^2} = \sqrt{100} = 10.0$'dır. Bu değer `max_norm = 5.0` sınırını aştığı için tüm gradyanlar $5.0 / 10.0 = 0.5$ katsayısıyla çarpılarak `[3.0, 4.0]` vektörüne küçültülür (yönü korunur, yeni normu tam $5.0$ olur). `Perplexity` ise $e^{2.0} \approx 7.39$'dur.
:::

::: gorev 1 · Decoupled Weight Decay AdamW Optimizer Adımı
Tek bir `AdamW` (`Decoupled Weight Decay`) güncelleme adımını gerçekleştiren `adamw_adimi(parametreler, gradyanlar, m, v, adim_t, lr, beta1, beta2, eps, weight_decay)` işlevini yaz:

1. **Girdiler:**
   - `parametreler`: Model ağırlıkları listesi ($\theta_{t-1}$).
   - `gradyanlar`: Her ağırlığa ait gradyan listesi ($g_t$).
   - `m`: Birinci moment (`Momentum`) geçmişi listesi ($m_{t-1}$).
   - `v`: İkinci moment (`Variance`) geçmişi listesi ($v_{t-1}$).
   - `adim_t`: Zaman adımı $t \ge 1$ (`int`).
   - `lr` ($\eta$), `beta1` ($\beta_1$), `beta2` ($\beta_2$), `eps` ($\epsilon$), `weight_decay` ($\lambda$): Optimizer hiperparametreleri (`float`).
2. **Matematiksel Kurallar (Her indeks $i$ için):**
   - **Birinci Moment:** $m_{t,i} = \beta_1 m_{t-1,i} + (1 - \beta_1) g_{t,i}$
   - **İkinci Moment:** $v_{t,i} = \beta_2 v_{t-1,i} + (1 - \beta_2) g_{t,i}^2$
   - **Bias Correction:**
     $$\hat{m}_{t,i} = \frac{m_{t,i}}{1 - \beta_1^t}, \qquad \hat{v}_{t,i} = \frac{v_{t,i}}{1 - \beta_2^t}$$
   - **Decoupled Weight Decay + Parametre Güncellemesi:**
     $$\theta_{t,i} = \theta_{t-1,i} - \text{lr} \cdot \left( \frac{\hat{m}_{t,i}}{\sqrt{\hat{v}_{t,i}} + \text{eps}} + \text{weight\_decay} \cdot \theta_{t-1,i} \right)$$
   - Döndürülecek tüm liste elemanlarını `round(deger, 6)` ile yuvarla.
3. **Dönüş Değeri:**
   `{"parametreler": [float, ...], "m": [float, ...], "v": [float, ...]}` sözlüğü döndür. Girdi listelerini değiştirme.

```starter
def adamw_adimi(parametreler, gradyanlar, m, v, adim_t, lr, beta1, beta2, eps, weight_decay):
    # KUSURLU BAŞLANGIÇ KODU: momentleri, bias düzeltmesini ve weight decay'i hesaplamadan basit SGD yapıyor!
    return {
        "parametreler": [round(p - lr * g, 6) for p, g in zip(parametreler, gradyanlar)],
        "m": [round(float(x), 6) for x in m],
        "v": [round(float(x), 6) for x in v],
    }

print(adamw_adimi([1.0, -0.5], [0.2, -0.1], [0.0, 0.0], [0.0, 0.0], 1, 0.01, 0.9, 0.95, 1e-8, 0.1))
```

```test
import copy, math

def _ref_adamw(parametreler, gradyanlar, m, v, t, lr, b1, b2, eps, wd):
    yeni_p, yeni_m, yeni_v = [], [], []
    for p, g, mi, vi in zip(parametreler, gradyanlar, m, v):
        mt = b1 * mi + (1.0 - b1) * g
        vt = b2 * vi + (1.0 - b2) * (g * g)
        m_hat = mt / (1.0 - (b1 ** t))
        v_hat = vt / (1.0 - (b2 ** t))
        pt = p - lr * ((m_hat / (math.sqrt(v_hat) + eps)) + wd * p)
        yeni_p.append(round(pt, 6))
        yeni_m.append(round(mt, 6))
        yeni_v.append(round(vt, 6))
    return {"parametreler": yeni_p, "m": yeni_m, "v": yeni_v}

def sozlesme(fn):
    try:
        vakalar = [
            ([1.0, -0.5], [0.2, -0.1], [0.0, 0.0], [0.0, 0.0], 1, 0.01, 0.9, 0.95, 1e-8, 0.1),
            ([2.5, -1.2, 0.8], [0.5, 0.0, -0.4], [0.1, -0.05, 0.02], [0.04, 0.01, 0.09], 3, 0.005, 0.9, 0.95, 1e-8, 0.05),
            ([0.5], [-0.3], [0.02], [0.005], 10, 0.02, 0.9, 0.99, 1e-6, 0.2),
        ]
        for args in vakalar:
            p_k = copy.deepcopy(args[0])
            m_k = copy.deepcopy(args[2])
            sonuc = fn(*args)
            bek = _ref_adamw(*args)
            if not isinstance(sonuc, dict) or set(sonuc.keys()) != {"parametreler", "m", "v"}:
                return False
            for k in ("parametreler", "m", "v"):
                if any(abs(a - b) > 1e-5 for a, b in zip(sonuc[k], bek[k])):
                    return False
            if args[0] != p_k or args[2] != m_k:
                return False
        return True
    except Exception:
        return False

ok(sozlesme(adamw_adimi), "adamw_adimi momentleri, bias correction'ı ve decoupled weight decay'i doğru hesaplamalı")

def m_wd_unut(p, g, m, v, t, lr, b1, b2, eps, wd):
    return adamw_adimi(p, g, m, v, t, lr, b1, b2, eps, 0.0)

def m_bias_unut(p, g, m, v, t, lr, b1, b2, eps, wd):
    return adamw_adimi(p, g, m, v, 100000, lr, b1, b2, eps, wd)

def m_klasik_l2(p, g, m, v, t, lr, b1, b2, eps, wd):
    g_l2 = [gi + wd * pi for pi, gi in zip(p, g)]
    return adamw_adimi(p, g_l2, m, v, t, lr, b1, b2, eps, 0.0)

for ad, m in [("Weight decay'i unutan", m_wd_unut), ("Bias correction adımını atlayan", m_bias_unut), ("Decoupled yerine klasik L2 uygulayan", m_klasik_l2)]:
    ok(not sozlesme(m), f"Yanlış çözüm/mutant yakalanmalı: {ad}")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef adamw_adimi(parametreler, gradyanlar, m, v, adim_t, lr, beta1, beta2, eps, weight_decay):\n    yeni_p = []\n    yeni_m = []\n    yeni_v = []\n    for p, g, mi, vi in zip(parametreler, gradyanlar, m, v):\n        mt = beta1 * mi + (1.0 - beta1) * g\n        vt = beta2 * vi + (1.0 - beta2) * (g * g)\n        m_hat = mt / (1.0 - beta1 ** adim_t)\n        v_hat = vt / (1.0 - beta2 ** adim_t)\n        p_yeni = p - lr * (m_hat / (math.sqrt(v_hat) + eps) + weight_decay * p)\n        yeni_p.append(round(p_yeni, 6))\n        yeni_m.append(round(mt, 6))\n        yeni_v.append(round(vt, 6))\n    return {'parametreler': yeni_p, 'm': yeni_m, 'v': yeni_v}", 'referans', 'exec'), _REF)
_t, _g = _ff(adamw_adimi, _REF['adamw_adimi'], ([1.0, -0.5], [0.2, -0.1], [0.0, 0.0], [0.0, 0.0], 1, 0.01, 0.9, 0.95, 1e-08, 0.1), tohum=2190, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (adamw_adimi): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
ok(adamw_adimi([1.0], [0.1234567], [0.0], [0.0], 1, 0.01, 0.9, 0.99, 1e-8, 0.1) == _REF['adamw_adimi']([1.0], [0.1234567], [0.0], [0.0], 1, 0.01, 0.9, 0.99, 1e-8, 0.1), "yeni_m 6 basamak yuvarlama korunmalı")
```

```solution
import math

def adamw_adimi(parametreler, gradyanlar, m, v, adim_t, lr, beta1, beta2, eps, weight_decay):
    yeni_p = []
    yeni_m = []
    yeni_v = []
    for p, g, mi, vi in zip(parametreler, gradyanlar, m, v):
        mt = beta1 * mi + (1.0 - beta1) * g
        vt = beta2 * vi + (1.0 - beta2) * (g * g)
        m_hat = mt / (1.0 - (beta1 ** adim_t))
        v_hat = vt / (1.0 - (beta2 ** adim_t))
        p_yeni = p - lr * ((m_hat / (math.sqrt(v_hat) + eps)) + weight_decay * p)
        yeni_p.append(round(p_yeni, 6))
        yeni_m.append(round(mt, 6))
        yeni_v.append(round(vt, 6))
    return {
        "parametreler": yeni_p,
        "m": yeni_m,
        "v": yeni_v,
    }
```

```hint
Her parametre için önce `mt = beta1 * mi + (1 - beta1) * g` ve `vt = beta2 * vi + (1 - beta2) * (g ** 2)` hesapla. Ardından `m_hat = mt / (1 - beta1 ** adim_t)` ve `v_hat = vt / (1 - beta2 ** adim_t)` ile önyargıyı düzeltip `p - lr * (m_hat / (math.sqrt(v_hat) + eps) + weight_decay * p)` güncellemesini uygula.
```
:::

::: gorev 2 · Global Gradient Norm Clipping ve WSD Learning Rate Hesabı
Aynı eğitim adımında hem **`Global Gradient Norm Clipping`** hem de **`Warmup-Stable-Decay (WSD)`** learning rate hesabını gerçekleştiren `grad_kirp_ve_wsd_lr(gradyanlar, max_norm, adim, warmup_adim, stable_adim, toplam_adim, max_lr, min_lr)` işlevini yaz:

1. **Global Gradient Norm Clipping:**
   - `gradyanlar` listesinin küresel L2 normunu hesapla: $\text{norm} = \sqrt{\sum_i g_i^2}$.
   - Eğer $\text{norm} > \text{max\_norm}$ ise her gradyanı `max_norm / norm` ile çarp (`kirpildi_mi = True`); değilse gradyanları olduğu gibi koru (`kirpildi_mi = False`).
2. **WSD (`Warmup-Stable-Decay`) learning rate Takvimi:**
   - **Evre 1 (`warmup`):** Eğer `adim <= warmup_adim` ise (ve `warmup_adim > 0`):
     $$\text{lr} = \text{max\_lr} \cdot \frac{\text{adim}}{\text{warmup\_adim}}, \qquad \text{evre} = \text{"warmup"}$$
   - **Evre 2 (`stable`):** Eğer `warmup_adim < adim <= warmup_adim + stable_adim` ise:
     $$\text{lr} = \text{max\_lr}, \qquad \text{evre} = \text{"stable"}$$
   - **Evre 3 (`decay`):** Eğer `adim > warmup_adim + stable_adim` ise:
     - Sönümleme süresi `decay_suresi = toplam_adim - (warmup_adim + stable_adim)` ve geçen sönümleme adımı `gecen = adim - (warmup_adim + stable_adim)`.
     - İlerleme oranı `oran = min(1.0, gecen / decay_suresi)`.
     - Doğrusal sönümleme (`Linear Decay`):
       $$\text{lr} = \text{max\_lr} - \text{oran} \cdot (\text{max\_lr} - \text{min\_lr}), \qquad \text{evre} = \text{"decay"}$$
3. **Dönüş Değeri:**
   Tüm sayısal değerleri `round(val, 6)` ile yuvarlayarak `{"grad_norm": float, "kirpildi_mi": bool, "kirpilmis_gradyanlar": [float, ...], "lr": float, "evre": str}` sözlüğü döndür.

```starter
def grad_kirp_ve_wsd_lr(gradyanlar, max_norm, adim, warmup_adim, stable_adim, toplam_adim, max_lr, min_lr):
    # KUSURLU BAŞLANGIÇ KODU: gradyanları kırpmıyor ve WSD evrelerini hesaplamadan sabit max_lr döndürüyor!
    return {
        "grad_norm": 0.0,
        "kirpildi_mi": False,
        "kirpilmis_gradyanlar": [round(float(g), 6) for g in gradyanlar],
        "lr": round(float(max_lr), 6),
        "evre": "stable",
    }

print(grad_kirp_ve_wsd_lr([3.0, 4.0], 2.5, adim=850, warmup_adim=100, stable_adim=700, toplam_adim=1000, max_lr=0.001, min_lr=0.0001))
```

```test
import copy, math

def _ref_wsd(gradyanlar, max_norm, adim, w_adim, s_adim, t_adim, max_lr, min_lr):
    norm = math.sqrt(sum(g * g for g in gradyanlar))
    kirpildi = norm > max_norm
    olcek = (max_norm / norm) if kirpildi else 1.0
    yeni_g = [round(g * olcek, 6) for g in gradyanlar]
    if adim <= w_adim:
        lr = max_lr * (adim / w_adim) if w_adim > 0 else max_lr
        evre = "warmup"
    elif adim <= w_adim + s_adim:
        lr = max_lr
        evre = "stable"
    else:
        decay_suresi = t_adim - (w_adim + s_adim)
        oran = min(1.0, (adim - (w_adim + s_adim)) / decay_suresi) if decay_suresi > 0 else 1.0
        lr = max_lr - oran * (max_lr - min_lr)
        evre = "decay"
    return {
        "grad_norm": round(norm, 6),
        "kirpildi_mi": kirpildi,
        "kirpilmis_gradyanlar": yeni_g,
        "lr": round(lr, 6),
        "evre": evre,
    }

def sozlesme(fn):
    try:
        vakalar = [
            ([3.0, 4.0], 2.5, 50, 100, 700, 1000, 0.001, 0.0001),
            ([0.3, 0.4], 1.0, 400, 100, 700, 1000, 0.001, 0.0001),
            ([6.0, 8.0], 5.0, 900, 100, 700, 1000, 0.001, 0.0001),
            ([0.0, 0.0], 1.0, 1000, 100, 700, 1000, 0.002, 0.0002),
            ([3.0, 4.0], 2.5, 0, 1, 5, 10, 0.001, 0.0001),
            ([3.0, 4.0], 2.5, 800, 100, 700, 1000, 0.001, 0.0001),
        ]
        for args in vakalar:
            g_kopya = copy.deepcopy(args[0])
            sonuc = fn(*args)
            bek = _ref_wsd(*args)
            if sonuc != bek or args[0] != g_kopya:
                return False
        return True
    except Exception:
        return False

ok(sozlesme(grad_kirp_ve_wsd_lr), "grad_kirp_ve_wsd_lr hem L2 norm kırpmasını hem de WSD (warmup/stable/decay) takvimini doğru hesaplamalı")

def m_eleman_kirp(g, mn, a, w, s, t, max_l, min_l):
    r = copy.deepcopy(grad_kirp_ve_wsd_lr(g, mn, a, w, s, t, max_l, min_l))
    r["kirpilmis_gradyanlar"] = [round(max(-mn, min(mn, x)), 6) for x in g]
    return r

def m_decay_sifir(g, mn, a, w, s, t, max_l, min_l):
    return grad_kirp_ve_wsd_lr(g, mn, a, w, s, t, max_l, 0.0)

for ad, m in [("Küresel L2 norm yerine eleman bazlı kırpan", m_eleman_kirp), ("Decay evresinde min_lr sınırını unutan", m_decay_sifir)]:
    ok(not sozlesme(m), f"Yanlış çözüm/mutant yakalanmalı: {ad}")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef grad_kirp_ve_wsd_lr(gradyanlar, max_norm, adim, warmup_adim, stable_adim, toplam_adim, max_lr, min_lr):\n    norm = math.sqrt(sum((g * g for g in gradyanlar)))\n    kirpildi = norm > max_norm\n    olcek = max_norm / norm if kirpildi else 1.0\n    kirpilmis = [round(g * olcek, 6) for g in gradyanlar]\n    if adim <= warmup_adim:\n        lr = max_lr * (adim / warmup_adim) if warmup_adim > 0 else max_lr\n        evre = 'warmup'\n    elif adim <= warmup_adim + stable_adim:\n        lr = max_lr\n        evre = 'stable'\n    else:\n        decay_suresi = toplam_adim - (warmup_adim + stable_adim)\n        oran = min(1.0, (adim - (warmup_adim + stable_adim)) / decay_suresi) if decay_suresi > 0 else 1.0\n        lr = max_lr - oran * (max_lr - min_lr)\n        evre = 'decay'\n    return {'grad_norm': round(norm, 6), 'kirpildi_mi': kirpildi, 'kirpilmis_gradyanlar': kirpilmis, 'lr': round(lr, 6), 'evre': evre}", 'referans', 'exec'), _REF)
_t, _g = _ff(grad_kirp_ve_wsd_lr, _REF['grad_kirp_ve_wsd_lr'], ([3.0, 4.0], 2.5, 850, 100, 700, 1000, 0.001, 0.0001), tohum=3064, en_cok=600, mod='gecerli', butce='oto', ekler=[([3.0, 4.0], 2.5, 0, 0, 700, 1000, 0.001, 0.0001, ), ([3.0, 4.0], 2.5, 900, 100, 700, 800, 0.001, 0.0001, )])
ok(_t, "farksal tarama (grad_kirp_ve_wsd_lr): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def grad_kirp_ve_wsd_lr(gradyanlar, max_norm, adim, warmup_adim, stable_adim, toplam_adim, max_lr, min_lr):
    norm = math.sqrt(sum(g * g for g in gradyanlar))
    kirpildi = norm > max_norm
    olcek = (max_norm / norm) if kirpildi else 1.0
    kirpilmis = [round(g * olcek, 6) for g in gradyanlar]

    if adim <= warmup_adim:
        lr = max_lr * (adim / warmup_adim) if warmup_adim > 0 else max_lr
        evre = "warmup"
    elif adim <= warmup_adim + stable_adim:
        lr = max_lr
        evre = "stable"
    else:
        decay_suresi = toplam_adim - (warmup_adim + stable_adim)
        oran = min(1.0, (adim - (warmup_adim + stable_adim)) / decay_suresi) if decay_suresi > 0 else 1.0
        lr = max_lr - oran * (max_lr - min_lr)
        evre = "decay"

    return {
        "grad_norm": round(norm, 6),
        "kirpildi_mi": kirpildi,
        "kirpilmis_gradyanlar": kirpilmis,
        "lr": round(lr, 6),
        "evre": evre,
    }
```

```hint
Önce `norm = math.sqrt(sum(g * g for g in gradyanlar))` hesapla ve `norm > max_norm` ise her elemanı `max_norm / norm` ile çarp. Ardından `adim <= warmup_adim`, `adim <= warmup_adim + stable_adim` ve sonrası için `warmup`, `stable`, `decay` formüllerini uygula.
```
:::

::: gorev 3 · Mixed Precision: FP16 Dinamik Loss Scaling (GradScaler Mantığı)
FP16 eğitiminde küçük gradyanlar sıfıra düşmesin diye kayıp bir **ölçek** ile çarpılır; gradyanlarda `inf/NaN` (taşma) görülürse adım atlanır ve ölçek küçültülür, uzun süre taşma olmazsa ölçek büyütülür. PyTorch `GradScaler` bu kuralı uygular. `dinamik_loss_scaler(tasma_dizisi, baslangic_olcek=65536.0, buyume_carpani=2.0, geri_cekilme=0.5, buyume_araligi=2000)` işlevini yaz.

**Kurallar:**
1. `tasma_dizisi` yalnız `bool` içeren liste olmalı; `baslangic_olcek > 0`, `buyume_carpani > 1`, `0 < geri_cekilme < 1`, `buyume_araligi >= 1` tam sayı (`bool` değil) olmalı. Değilse `ValueError`.
2. Bir sayaç 0'dan başlar. Her adımda:
   - Taşma varsa (`True`): adım **atlanır**, ölçek `geri_cekilme` ile çarpılır, sayaç 0 olur.
   - Yoksa: adım uygulanır, sayaç 1 artar; sayaç `buyume_araligi`'na ulaşınca ölçek `buyume_carpani` ile çarpılır ve sayaç 0 olur.
   - Adımdan **sonraki** ölçek geçmişe yazılır.
3. Çıktı: `{"olcek_gecmisi": [...], "atlanan_adimlar": [indeksler], "uygulanan_adim_sayisi": int, "son_olcek": float}`.

```starter
def dinamik_loss_scaler(tasma_dizisi, baslangic_olcek=65536.0, buyume_carpani=2.0, geri_cekilme=0.5, buyume_araligi=2000):
    # KUSURLU BAŞLANGIÇ: ölçek hiç değişmiyor, taşan adımlar da uygulanıyor
    return {"olcek_gecmisi": [baslangic_olcek] * len(tasma_dizisi), "atlanan_adimlar": [],
            "uygulanan_adim_sayisi": len(tasma_dizisi), "son_olcek": baslangic_olcek}

print(dinamik_loss_scaler([False, False, True, False], baslangic_olcek=1024.0, buyume_araligi=2))
```

```test
fn = need("dinamik_loss_scaler")
r = fn([False, False, True, False], baslangic_olcek=1024.0, buyume_araligi=2)
eq(r["olcek_gecmisi"], [1024.0, 2048.0, 1024.0, 1024.0], "2 temiz adımda büyür, taşmada yarıya iner, sayaç sıfırlanır")
eq(r["atlanan_adimlar"], [2], "taşan adım atlanır")
eq(r["uygulanan_adim_sayisi"], 3, "4 adımdan 3'ü uygulanır")
eq(r["son_olcek"], 1024.0, "son ölçek")
r2 = fn([True, True, True])
eq(r2["olcek_gecmisi"], [32768.0, 16384.0, 8192.0], "art arda taşmalar ölçeği yarıya indirir")
eq(r2["uygulanan_adim_sayisi"], 0, "hiçbir adım uygulanmaz")
r3 = fn([False] * 2000)
eq(r3["son_olcek"], 131072.0, "2000 temiz adımdan sonra ölçek iki katına çıkar")
eq(r3["olcek_gecmisi"][1998], 65536.0, "1999. adıma kadar büyüme yok")
eq(fn([], baslangic_olcek=8.0)["son_olcek"], 8.0, "adım yoksa ölçek değişmez")
r4 = fn([False, True, False, False, False], baslangic_olcek=4.0, buyume_araligi=3)
eq(r4["olcek_gecmisi"], [4.0, 2.0, 2.0, 2.0, 4.0], "taşma sayacı sıfırlar: büyüme taşmadan sonraki 3. temiz adımda")
raises(ValueError, fn, [0, 1])
raises(ValueError, fn, [False], 65536.0, 1.0)
raises(ValueError, fn, [False], 65536.0, 2.0, 1.0)
raises(ValueError, fn, [False], 65536.0, 2.0, 0.5, 0)
raises(ValueError, fn, [False], -1.0)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def dinamik_loss_scaler(tasma_dizisi, baslangic_olcek=65536.0, buyume_carpani=2.0, geri_cekilme=0.5, buyume_araligi=2000):\n    if not isinstance(tasma_dizisi, list) or not all((isinstance(t, bool) for t in tasma_dizisi)):\n        raise ValueError('tasma_dizisi bool listesi olmalı')\n    for v in (baslangic_olcek, buyume_carpani, geri_cekilme):\n        if isinstance(v, bool) or not isinstance(v, (int, float)):\n            raise ValueError('ölçek parametreleri sayı olmalı')\n    if not (baslangic_olcek > 0 and buyume_carpani > 1 and (0 < geri_cekilme < 1)):\n        raise ValueError('baslangic_olcek > 0, buyume_carpani > 1, 0 < geri_cekilme < 1 olmalı')\n    if isinstance(buyume_araligi, bool) or not isinstance(buyume_araligi, int) or buyume_araligi < 1:\n        raise ValueError('buyume_araligi >= 1 tam sayı olmalı')\n    olcek = float(baslangic_olcek)\n    sayac, uygulanan = (0, 0)\n    gecmis, atlanan = ([], [])\n    for i, tasma in enumerate(tasma_dizisi):\n        if tasma:\n            atlanan.append(i)\n            olcek *= geri_cekilme\n            sayac = 0\n        else:\n            uygulanan += 1\n            sayac += 1\n            if sayac == buyume_araligi:\n                olcek *= buyume_carpani\n                sayac = 0\n        gecmis.append(olcek)\n    return {'olcek_gecmisi': gecmis, 'atlanan_adimlar': atlanan, 'uygulanan_adim_sayisi': uygulanan, 'son_olcek': olcek}", 'referans', 'exec'), _REF)
_t, _g = _ff(dinamik_loss_scaler, _REF['dinamik_loss_scaler'], ([False, False, True, False], 1024.0, 2.0, 0.5, 2), tohum=3063, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (dinamik_loss_scaler): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def dinamik_loss_scaler(tasma_dizisi, baslangic_olcek=65536.0, buyume_carpani=2.0, geri_cekilme=0.5, buyume_araligi=2000):
    if not isinstance(tasma_dizisi, list) or not all(isinstance(t, bool) for t in tasma_dizisi):
        raise ValueError("tasma_dizisi bool listesi olmalı")
    for v in (baslangic_olcek, buyume_carpani, geri_cekilme):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError("ölçek parametreleri sayı olmalı")
    if not (baslangic_olcek > 0 and buyume_carpani > 1 and 0 < geri_cekilme < 1):
        raise ValueError("baslangic_olcek > 0, buyume_carpani > 1, 0 < geri_cekilme < 1 olmalı")
    if isinstance(buyume_araligi, bool) or not isinstance(buyume_araligi, int) or buyume_araligi < 1:
        raise ValueError("buyume_araligi >= 1 tam sayı olmalı")
    olcek = float(baslangic_olcek)
    sayac, uygulanan = 0, 0
    gecmis, atlanan = [], []
    for i, tasma in enumerate(tasma_dizisi):
        if tasma:
            atlanan.append(i)
            olcek *= geri_cekilme
            sayac = 0
        else:
            uygulanan += 1
            sayac += 1
            if sayac == buyume_araligi:
                olcek *= buyume_carpani
                sayac = 0
        gecmis.append(olcek)
    return {"olcek_gecmisi": gecmis, "atlanan_adimlar": atlanan, "uygulanan_adim_sayisi": uygulanan, "son_olcek": olcek}
```

```hint
Tek bir sayaç yeter: taşmada sıfırla, temiz adımda artır ve `buyume_araligi`'na eşitlenince büyütüp sıfırla. Ölçeği her adımın sonunda geçmişe ekle.
```
:::

::: anlat Gerçek deney: Gerçek SmolLM2 ağırlığında 10 adımlık eğitim ve gerçek fp16 taşmaları
Final senin üç işlevinle gerçek bir eğitim döngüsü kurar (indirme yok). SmolLM2-135M'in son katmanındaki gerçek `q_proj` ağırlığı (576×576 = 331 776 eleman) bir metinde 10 adım eğitilir: 2 adım warmup, 5 adım stable, 3 adım decay.

- Her adımda modelden **gerçek gradyan** alınır, senin `grad_kirp_ve_wsd_lr` işlevinle kırpılır ve o adımın `lr` değeri belirlenir; sonra senin `adamw_adimi` işlevin ağırlığı günceller.
- Aynı gradyan `torch.nn.utils.clip_grad_norm_`'a, aynı durum (p, m, v, adım) `torch.optim.AdamW`'ye verilir ve her adım ayrı ayrı karşılaştırılır.
- Gradyanlar sabit bir katsayıyla büyütülür. Bu hile değil, AdamW'nin bir özelliğidir: güncelleme $\hat m / \sqrt{\hat v}$ oranına bağlı olduğu için gradyanı (ya da kaybı) bir sabitle çarpmak adımı değiştirmez (yalnız `eps` etkilenir). Senin işlevin 6 basamağa yuvarladığı için küçük gradyanlar bu yolla görünür mertebeye taşınır.
- **Zehirli batch:** aynı girdi rastgele etiketlerle verilir. Kayıp yaklaşık dört kat büyür ama gradyan normu yalnız biraz artar; softmax gradyanı sınırlı olduğu için norm kırpma zehirli veriyi ayırt eden bir savunma değildir, yalnız kararlılık aracıdır.
- **Loss scaling:** gerçek gradyanlar her adımda senin `dinamik_loss_scaler` işlevinin verdiği ölçekle çarpılıp `float16`'ya çevrilir; sonsuz çıkan adım taşmadır. Taşma dizisi torch'un `GradScaler` içinde kullandığı çekirdeğe (`torch._amp_update_scale_`) de verilir. Aynı değerler `bfloat16`'ya çevrilince taşma olmaz: bf16'nın üs aralığı fp32 ile aynıdır, bu yüzden bf16 eğitiminde loss scaling gerekmez.

Kabul: üç işlevin farksal taramayı geçmesi; kırpmanın torch'tan göreli `1e-5`, AdamW adımının en çok `1e-6` (6 basamak yuvarlama sınırı) farklı olması; WSD öğrenme oranlarının doğru olması; eğitim kaybının düşmesi; ölçek geçmişinin torch çekirdeğiyle aynı olması ve bf16'da taşma olmaması.

**Kanıt dosyasını oku:** `gecmis` (adım adım lr, evre, kırpma ve iki kayıp), `kayip_rastgele_etiket`, `aykiri_kat`, `tasma_dizisi`, `olcek_gecmisi`. Soru 1: Eğitim kaybı düşerken doğrulama kaybı neden yerinde sayıyor ya da artıyor? Soru 2: Ölçek neden taşma ile büyüme arasında salınıyor ve `buyume_araligi` büyürse ne olur? Soru 3: Zehirli batch'i yakalamak için gradyan normu yerine neye bakardın?
:::

::: gorev Gerçek deney · Gerçek SmolLM2 q_proj ağırlığında AdamW, kırpma, WSD ve loss scaling
Önceki görevlerdeki `adamw_adimi`, `grad_kirp_ve_wsd_lr`, `dinamik_loss_scaler` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 240
```
```starter
import ai_lab
def adamw_adimi(parametreler, gradyanlar, m, v, adim_t, lr, beta1, beta2, eps, weight_decay):
    return {'parametreler': [round(p - lr * g, 6) for p, g in zip(parametreler, gradyanlar)], 'm': [round(float(x), 6) for x in m], 'v': [round(float(x), 6) for x in v]}

def grad_kirp_ve_wsd_lr(gradyanlar, max_norm, adim, warmup_adim, stable_adim, toplam_adim, max_lr, min_lr):
    return {'grad_norm': 0.0, 'kirpildi_mi': False, 'kirpilmis_gradyanlar': [round(float(g), 6) for g in gradyanlar], 'lr': round(float(max_lr), 6), 'evre': 'stable'}

def dinamik_loss_scaler(tasma_dizisi, baslangic_olcek=65536.0, buyume_carpani=2.0, geri_cekilme=0.5, buyume_araligi=2000):
    return {'olcek_gecmisi': [baslangic_olcek] * len(tasma_dizisi), 'atlanan_adimlar': [], 'uygulanan_adim_sayisi': len(tasma_dizisi), 'son_olcek': baslangic_olcek}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_07 as D
    D.goster(adamw_adimi, grad_kirp_ve_wsd_lr, dinamik_loss_scaler)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('dil_modeli', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
adamw_adimi = need("adamw_adimi")
grad_kirp_ve_wsd_lr = need("grad_kirp_ve_wsd_lr")
dinamik_loss_scaler = need("dinamik_loss_scaler")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef adamw_adimi(parametreler, gradyanlar, m, v, adim_t, lr, beta1, beta2, eps, weight_decay):\n    yeni_p = []\n    yeni_m = []\n    yeni_v = []\n    for p, g, mi, vi in zip(parametreler, gradyanlar, m, v):\n        mt = beta1 * mi + (1.0 - beta1) * g\n        vt = beta2 * vi + (1.0 - beta2) * (g * g)\n        m_hat = mt / (1.0 - beta1 ** adim_t)\n        v_hat = vt / (1.0 - beta2 ** adim_t)\n        p_yeni = p - lr * (m_hat / (math.sqrt(v_hat) + eps) + weight_decay * p)\n        yeni_p.append(round(p_yeni, 6))\n        yeni_m.append(round(mt, 6))\n        yeni_v.append(round(vt, 6))\n    return {'parametreler': yeni_p, 'm': yeni_m, 'v': yeni_v}\n\nimport math\n\ndef grad_kirp_ve_wsd_lr(gradyanlar, max_norm, adim, warmup_adim, stable_adim, toplam_adim, max_lr, min_lr):\n    norm = math.sqrt(sum((g * g for g in gradyanlar)))\n    kirpildi = norm > max_norm\n    olcek = max_norm / norm if kirpildi else 1.0\n    kirpilmis = [round(g * olcek, 6) for g in gradyanlar]\n    if adim <= warmup_adim:\n        lr = max_lr * (adim / warmup_adim) if warmup_adim > 0 else max_lr\n        evre = 'warmup'\n    elif adim <= warmup_adim + stable_adim:\n        lr = max_lr\n        evre = 'stable'\n    else:\n        decay_suresi = toplam_adim - (warmup_adim + stable_adim)\n        oran = min(1.0, (adim - (warmup_adim + stable_adim)) / decay_suresi) if decay_suresi > 0 else 1.0\n        lr = max_lr - oran * (max_lr - min_lr)\n        evre = 'decay'\n    return {'grad_norm': round(norm, 6), 'kirpildi_mi': kirpildi, 'kirpilmis_gradyanlar': kirpilmis, 'lr': round(lr, 6), 'evre': evre}\n\ndef dinamik_loss_scaler(tasma_dizisi, baslangic_olcek=65536.0, buyume_carpani=2.0, geri_cekilme=0.5, buyume_araligi=2000):\n    if not isinstance(tasma_dizisi, list) or not all((isinstance(t, bool) for t in tasma_dizisi)):\n        raise ValueError('tasma_dizisi bool listesi olmalı')\n    for v in (baslangic_olcek, buyume_carpani, geri_cekilme):\n        if isinstance(v, bool) or not isinstance(v, (int, float)):\n            raise ValueError('ölçek parametreleri sayı olmalı')\n    if not (baslangic_olcek > 0 and buyume_carpani > 1 and (0 < geri_cekilme < 1)):\n        raise ValueError('baslangic_olcek > 0, buyume_carpani > 1, 0 < geri_cekilme < 1 olmalı')\n    if isinstance(buyume_araligi, bool) or not isinstance(buyume_araligi, int) or buyume_araligi < 1:\n        raise ValueError('buyume_araligi >= 1 tam sayı olmalı')\n    olcek = float(baslangic_olcek)\n    sayac, uygulanan = (0, 0)\n    gecmis, atlanan = ([], [])\n    for i, tasma in enumerate(tasma_dizisi):\n        if tasma:\n            atlanan.append(i)\n            olcek *= geri_cekilme\n            sayac = 0\n        else:\n            uygulanan += 1\n            sayac += 1\n            if sayac == buyume_araligi:\n                olcek *= buyume_carpani\n                sayac = 0\n        gecmis.append(olcek)\n    return {'olcek_gecmisi': gecmis, 'atlanan_adimlar': atlanan, 'uygulanan_adim_sayisi': uygulanan, 'son_olcek': olcek}", 'referans', 'exec'), _REF)
_t, _g = _ff(adamw_adimi, _REF['adamw_adimi'], ([1.0, -0.5], [0.2, -0.1], [0.0, 0.0], [0.0, 0.0], 1, 0.01, 0.9, 0.95, 1e-08, 0.1), tohum=2190, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (adamw_adimi): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(grad_kirp_ve_wsd_lr, _REF['grad_kirp_ve_wsd_lr'], ([3.0, 4.0], 2.5, 850, 100, 700, 1000, 0.001, 0.0001), tohum=3064, en_cok=600, mod='gecerli', butce='oto', ekler=[([3.0, 4.0], 2.5, 0, 0, 700, 1000, 0.001, 0.0001, ), ([3.0, 4.0], 2.5, 900, 100, 700, 800, 0.001, 0.0001, )])
kontrol(_t, "farksal tarama (grad_kirp_ve_wsd_lr): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(dinamik_loss_scaler, _REF['dinamik_loss_scaler'], ([False, False, True, False], 1024.0, 2.0, 0.5, 2), tohum=3063, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (dinamik_loss_scaler): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
kontrol(adamw_adimi([1.0], [0.1234567], [0.5], [0.2], 3, 0.01, 0.9, 0.95, 1e-8, 0.1) == _REF['adamw_adimi']([1.0], [0.1234567], [0.5], [0.2], 3, 0.01, 0.9, 0.95, 1e-8, 0.1), "adamw vt/v_hat ve 6 basamak yuvarlama korunmalı")
kontrol(grad_kirp_ve_wsd_lr([3.0, 4.0], 2.5, 0, 1, 5, 10, 0.001, 0.0001) == _REF['grad_kirp_ve_wsd_lr']([3.0, 4.0], 2.5, 0, 1, 5, 10, 0.001, 0.0001), "warmup_adim=1 sınırı korunmalı")
kontrol(grad_kirp_ve_wsd_lr([3.0, 4.0], 2.5, 800, 100, 700, 1000, 0.001, 0.0001) == _REF['grad_kirp_ve_wsd_lr']([3.0, 4.0], 2.5, 800, 100, 700, 1000, 0.001, 0.0001), "stable evre üst sınırı korunmalı")
kontrol(dinamik_loss_scaler([False] * 2000 + [True, False]) == _REF['dinamik_loss_scaler']([False] * 2000 + [True, False]), "dinamik_loss_scaler varsayılan parametreleri korunmalı")
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_07 as D
try: r = D.deney(adamw_adimi, grad_kirp_ve_wsd_lr, dinamik_loss_scaler)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['kirpma_ayni'] and r['wsd_dogru'], 'gerçek gradyanlarda kırpma torch.clip_grad_norm_ ile aynı, WSD öğrenme oranları doğru')
kontrol(r['adamw_ayni'], 'AdamW adımı her adımda torch.optim.AdamW ile aynı (en çok 1e-6, yuvarlama sınırı)')
kontrol(r['egitim_dustu'], '10 adımlık gerçek eğitimde eğitim kaybı düştü')
kontrol(r['olcek_ayni'] and r['fp16_tasma'] > 0 and r['bf16_tasma'] == 0, 'loss scaling ölçek geçmişi torch GradScaler çekirdeğiyle aynı; fp16 taşıyor, bf16 taşmıyor')
ai_lab.kanit_yaz("ai-uretim-07-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-07", "deney": r})
```
```solution
import ai_lab
import math

def adamw_adimi(parametreler, gradyanlar, m, v, adim_t, lr, beta1, beta2, eps, weight_decay):
    yeni_p = []
    yeni_m = []
    yeni_v = []
    for p, g, mi, vi in zip(parametreler, gradyanlar, m, v):
        mt = beta1 * mi + (1.0 - beta1) * g
        vt = beta2 * vi + (1.0 - beta2) * (g * g)
        m_hat = mt / (1.0 - beta1 ** adim_t)
        v_hat = vt / (1.0 - beta2 ** adim_t)
        p_yeni = p - lr * (m_hat / (math.sqrt(v_hat) + eps) + weight_decay * p)
        yeni_p.append(round(p_yeni, 6))
        yeni_m.append(round(mt, 6))
        yeni_v.append(round(vt, 6))
    return {'parametreler': yeni_p, 'm': yeni_m, 'v': yeni_v}

import math

def grad_kirp_ve_wsd_lr(gradyanlar, max_norm, adim, warmup_adim, stable_adim, toplam_adim, max_lr, min_lr):
    norm = math.sqrt(sum((g * g for g in gradyanlar)))
    kirpildi = norm > max_norm
    olcek = max_norm / norm if kirpildi else 1.0
    kirpilmis = [round(g * olcek, 6) for g in gradyanlar]
    if adim <= warmup_adim:
        lr = max_lr * (adim / warmup_adim) if warmup_adim > 0 else max_lr
        evre = 'warmup'
    elif adim <= warmup_adim + stable_adim:
        lr = max_lr
        evre = 'stable'
    else:
        decay_suresi = toplam_adim - (warmup_adim + stable_adim)
        oran = min(1.0, (adim - (warmup_adim + stable_adim)) / decay_suresi) if decay_suresi > 0 else 1.0
        lr = max_lr - oran * (max_lr - min_lr)
        evre = 'decay'
    return {'grad_norm': round(norm, 6), 'kirpildi_mi': kirpildi, 'kirpilmis_gradyanlar': kirpilmis, 'lr': round(lr, 6), 'evre': evre}

def dinamik_loss_scaler(tasma_dizisi, baslangic_olcek=65536.0, buyume_carpani=2.0, geri_cekilme=0.5, buyume_araligi=2000):
    if not isinstance(tasma_dizisi, list) or not all((isinstance(t, bool) for t in tasma_dizisi)):
        raise ValueError('tasma_dizisi bool listesi olmalı')
    for v in (baslangic_olcek, buyume_carpani, geri_cekilme):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError('ölçek parametreleri sayı olmalı')
    if not (baslangic_olcek > 0 and buyume_carpani > 1 and (0 < geri_cekilme < 1)):
        raise ValueError('baslangic_olcek > 0, buyume_carpani > 1, 0 < geri_cekilme < 1 olmalı')
    if isinstance(buyume_araligi, bool) or not isinstance(buyume_araligi, int) or buyume_araligi < 1:
        raise ValueError('buyume_araligi >= 1 tam sayı olmalı')
    olcek = float(baslangic_olcek)
    sayac, uygulanan = (0, 0)
    gecmis, atlanan = ([], [])
    for i, tasma in enumerate(tasma_dizisi):
        if tasma:
            atlanan.append(i)
            olcek *= geri_cekilme
            sayac = 0
        else:
            uygulanan += 1
            sayac += 1
            if sayac == buyume_araligi:
                olcek *= buyume_carpani
                sayac = 0
        gecmis.append(olcek)
    return {'olcek_gecmisi': gecmis, 'atlanan_adimlar': atlanan, 'uygulanan_adim_sayisi': uygulanan, 'son_olcek': olcek}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_07 as D
    D.goster(adamw_adimi, grad_kirp_ve_wsd_lr, dinamik_loss_scaler)
```
```hint
Üç görevin çözümlerini olduğu gibi buraya koy. Deney adım sayacını 1'den başlatır ve m, v listelerini her adımda senin döndürdüğün değerlerle sürdürür.
```
:::

::: anlat Sınır
Görevler decoupled weight decay ile AdamW adımını, global norm clipping'i ve WSD öğrenme oranını saf Python ile hesaplatır; final adım gerçek bir SmolLM2 ağırlığını 10 adım eğitip her adımı torch.optim.AdamW ile karşılaştırır (tek matris, tek metin). Weight decay genelde normalizasyon ve bias parametrelerine uygulanmaz; hepsine uygulamak küçük modellerde sonucu kötüleştirebilir. Clipping normu tüm parametreler üzerinden, dağıtık eğitimde de tüm GPU'lar üzerinden hesaplanmalıdır. FP16 loss scaling görevi yalnız ölçek güncelleme kuralını simüle eder; final adım taşmayı gerçek gradyanların fp16'ya çevrilmesiyle belirler; ileri/geri geçiş fp16 ya da BF16 autocast ile yapılmaz. WSD'nin decay fazının uzunluğu ve şekli sonucu belirgin değiştirir; tek bir doğru oran yoktur.

Kaynaklar: [Loshchilov ve Hutter 2019 - Decoupled Weight Decay Regularization](https://arxiv.org/abs/1711.05101), [Micikevicius vd. 2018 - Mixed Precision Training](https://arxiv.org/abs/1710.03740), [Hu vd. 2024 - MiniCPM: Unveiling the Potential of Small Language Models with Scalable Training Strategies](https://arxiv.org/abs/2404.06395).
:::

::: dusun
Sahnede bir katılımcı sordu:
*"Hocam, madem `BF16` (`2 Byte`) veya `FP8` (`1 Byte`) ile ileri ve geri yayılım (`backpropagation`) yapabiliyoruz, neden `AdamW` optimizer içindeki ana ağırlık kopyasını (`Master Weights`) ve momentleri ($m_t, v_t$) hâlâ `FP32` (`4 Byte`) hassasiyetinde tutmak zorunda kalıyoruz? Neden her şeyi doğrudan `BF16` içinde güncellemiyoruz?"*

Bu soruya **`Underflow / Swamping in Floating-Point Addition` ($w_{\text{BF16}} - \eta \cdot \Delta w$ işleminde çok küçük olan $\eta \approx 10^{-4}$ güncellemesinin `BF16`'nın 7 bitlik kesir (`Mantissa`) alanında tamamen yuvarlanıp sıfırlanması / ağırlığın hiç güncellenememesi)** gerçeğini kullanarak nasıl cevap verirsin?
:::

::: ozet
- **`Autoregressive Pre-Training`**, girdi dizisini bir adım sağa kaydırarak (`Shifted Targets`) her konumda bir sonraki `token`'ın **`Cross-Entropy Loss`** değerini minimize eder.
- **`AdamW` (`Decoupled Weight Decay`)**, birinci ($m_t$) ve ikinci ($v_t$) momentlerin önyargı düzeltmesini (`Bias Correction`) yaptıktan sonra ağırlık çürümesini ($\lambda \theta_{t-1}$) gradyandan bağımsız olarak doğrudan parametreye uygular.
- **`Warmup-Stable-Decay (WSD)`** takvimi, eğitimin toplam süresini önceden sabitleme zorunluluğunu ortadan kaldırarak uzun bir sabit plato (`Stable`) ve son aşamada keskin bir soğuma (`Decay / Cool-down`) sunar.
- **`Global Gradient Norm Clipping`** ($\|G\|_2 \le 1.0$) gradyanların yönünü bozmadan patlamaları önlerken, **`BF16 / FP8 Mixed Precision`** (`FP32 Master Weights` ile birlikte) sayısal taşma olmadan eğitimi hızlandırır.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Ayrık ağırlık çürümesi (`AdamW`) (30 sn).** "Klasik $L_2$ cezasını gradyana eklemek ikinci moment $\sqrt{\hat{v}_t}$ yüzünden büyük gradyanlı ağırlıklarda düzenlileştirmeyi zayıflatır; `AdamW` çürümeyi ($-\eta\lambda\theta$) adaptif adımdan ayırıp doğrudan ağırlığa uygular."
2. **`WSD` takvimi ve küresel kırpma (30 sn).** "`Warmup-Stable-Decay` toplam token hedefini baştan kilitlemeden uzun bir sabit öğrenme oranı platosu ve sonunda keskin bir soğuma (`decay`) sağlar; küresel L2 norm kırpması ise yönü bozmadan gradyan sıçramalarını sınırlar."
3. **Karma duyarlık ve `Master Weights` (35 sn).** "İleri/geri geçiş hız için `BF16`/`FP8` koşarken, $10^{-4}$ mertebesindeki küçük ağırlık güncellemelerinin 7 bitlik `BF16` mantissasında sıfıra yuvarlanmaması için ana ağırlık ve momentler `FP32` tutulur."
4. **Soru (25 sn).** "`RMSNorm` ölçek parametrelerine ve gömme tablosuna neden çoğunlukla diğer matrislerle aynı `weight decay` uygulanmaz?"
:::
