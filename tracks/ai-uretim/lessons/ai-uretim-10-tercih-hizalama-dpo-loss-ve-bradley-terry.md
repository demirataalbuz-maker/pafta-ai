---
id: ai-uretim-10
title: "Post-Training Aşama 2: Direct Preference Optimization (DPO), Bradley-Terry ve SimPO"
summary: "Klasik RLHF (PPO) karmaşıklığını aşan Direct Preference Optimization (DPO) matematiği, Bradley-Terry tercih modeli, örtük ödül marjı (Implicit Reward Margin) ve referans modelsiz SimPO kaybının sıfırdan inşası."
track: ai-uretim
order: 10
duration_minutes: 40
difficulty: ileri
xp: 300
prerequisites: [ai-uretim-09]
esleme: ai-temel-11, ai-uretim-09, ai-uretim-11
tags: [post-training, rlhf, dpo, bradley-terry, simpo, alignment]
---

::: anlat
## DPO ve tercih çiftleri

Bir tercih çifti aynı girdiye verilen iki yanıtı karşılaştırır. Bu derste policy ve reference log probability farklarından DPO loss hesabını, ardından uzunluk normalizasyonu kullanan SimPO yaklaşımını inceleyeceksin. Tercih etiketi, yanıtın olgusal doğruluğunu ayrıca kanıtlamaz.

Çünkü **üretmek (`Generation`) ile ayırt etmek (`Discrimination`) arasındaki asimetri** insan ve model doğasının temel bir gerçeğidir:
- `SFT`, modele yalnızca *"bu token dizisini taklit et (`Behavior Cloning`)"* der; modele **neyin kötü, neyin halüsinasyon, neyin güvensiz veya yüzeysel olduğunu** açıkça öğretmez.
- Aynı soruya (`Prompt` $x$) verilen iki yanıttan hangisinin daha doğru, daha zarif ve daha güvenli olduğunu seçmek (`Chosen` $y_w \succ$ `Rejected` $y_l$), sıfırdan kusursuz yanıt yazmaktan çok daha kolay ve ölçeklenebilirdir.

2022'de InstructGPT ve ChatGPT bu sorunu **İnsan Geri Bildirimiyle reinforcement learning (`RLHF - Reinforcement Learning from Human Feedback`)** ve **`PPO (Proximal Policy Optimization)`** ile çözdü. Ancak klasik `RLHF (PPO)` boru hattı, dağıtık sistem mühendisleri için tam bir VRAM ve kararlılık kâbusuydu!

```
┌────────────────────────────────────────────────────────────────────────────┐
│        KLASİK RLHF (PPO) BORU HATTI  vs  DPO (DIRECT PREFERENCE OPT.)      │
├──────────────────────────────────────┬─────────────────────────────────────┤
│ KLASİK RLHF + PPO (4 Ayrı Model!)    │ DPO (Rafailov et al., Stanford 2023)│
│ ──────────────────────────────────── │ ─────────────────────────────────── │
│ 1. Actor Model (pi_theta - Eğitilen) │ 1. Policy Model (pi_theta - Eğitilen│
│ 2. Reference Model (pi_ref - Donuk)  │ 2. Reference Model (pi_ref - Donuk, │
│ 3. Reward Model (r_phi - Donuk)      │    veya logp önceden önbellekli!)   │
│ 4. Critic / Value Model (V_psi -     │                                     │
│    Eğitilen)                         │ • Critic YOK, ayrı Reward Model YOK!│
│ • Canlı örnekleme (Rollout) darboğazı│ • Canlı Rollout YOK; doğrudan       │
│ • Hiperparametre hassasiyeti ve      │   Binary Cross-Entropy Loss ile     │
│   Reward Hacking (Ödül İstismarı)    │   kapalı formda (Closed-Form) çözüm!│
└──────────────────────────────────────┴─────────────────────────────────────┘
```

70B parametreli bir modeli klasik `PPO` ile hizalamak için bellekte **aynı anda 4 adet 70B model** (`Actor`, `Reference`, `Reward`, `Critic`) tutmak zorunda kalıyordun!

İşte Mayıs 2023'te **Rafailov et al. (Stanford)** tarafından yayınlanan **`Direct Preference Optimization (DPO)`** ("*Your Language Model is Secretly a Reward Model*") makalesi, bu 4 modelli RL döngüsünü tek bir analitik cebir hamlesiyle yıktı ve dil modelinin kendisinin zaten örtük bir ödül modeli (`Implicit Reward Model`) olduğunu kanıtladı!

---

### 1. `Bradley-Terry Preference Model` (1952) ve KL-Kısıtlı RL Hedefi

Önce insan tercihlerini nasıl olasılığa döktüğümüzü görelim. Elimizde bir istem $x$ ve iki yanıt var:
- **$y_w$ (`Chosen / Winner`):** Tercih edilen kaliteli yanıt.
- **$y_l$ (`Rejected / Loser`):** Reddedilen kusurlu yanıt.

**`Bradley-Terry Model`**'e göre, gizli bir ödül fonksiyonu $r^*(x, y)$ altında $y_w$'nin $y_l$'ye tercih edilme olasılığı, iki yanıtın ödül farkının `Sigmoid` ($\sigma(z) = \frac{1}{1 + e^{-z}}$) fonksiyonundan geçirilmiş halidir:

$$P(y_w \succ y_l \mid x) = \sigma\big(r^*(x, y_w) - r^*(x, y_l)\big) = \frac{1}{1 + \exp\big(-(r^*(x, y_w) - r^*(x, y_l))\big)}$$

Peki klasik `RLHF`'nin maksimize etmeye çalıştığı **KL-Kısıtlı Ödül Hedefi (`KL-Constrained Reward Maximization Objective`)** nedir?
Modelimiz $\pi_\theta(y \mid x)$ yüksek ödül alsın, ama ön-eğitimli/SFT referans modelinden ($\pi_{\text{ref}}$) çok fazla sapıp dilbilgisini bozmasın (`Mode Collapse / Reward Hacking` yapmasın) diye bir **`KL-Divergence`** cezası ($\beta > 0$) koyarız:

$$\max_{\pi_\theta} \mathbb{E}_{x \sim \mathcal{D}, y \sim \pi_\theta(y \mid x)} \Big[ r(x, y) \Big] - \beta \, \mathbb{D}_{\text{KL}}\Big( \pi_\theta(y \mid x) \,\Big\|\, \pi_{\text{ref}}(y \mid x) \Big)$$

---

### 2. DPO'nun Mucizevi Türetimi: Kapalı Form Çözüm ve `Implicit Reward`

Rafailov et al. yukarıdaki KL-kısıtlı maksimizasyon probleminin **analitik olarak tam (kapalı form) bir optimal çözümü ($\pi^*$)** olduğunu fark etti! Kalkülüste varyasyonlar hesabı (`Calculus of Variations` / Gibbs eşitsizliği) uygulandığında optimal politika $\pi^*(y \mid x)$ şudur:

$$\pi^*(y \mid x) = \frac{1}{Z(x)} \pi_{\text{ref}}(y \mid x) \exp\left(\frac{1}{\beta} r(x, y)\right)$$

Burada $Z(x) = \sum_y \pi_{\text{ref}}(y \mid x) \exp\left(\frac{1}{\beta} r(x, y)\right)$ hesaplanması imkansız olan (`Intractable`) bölüntü fonksiyonudur (`Partition Function`).

Şimdi nefesini tut ve yukarıdaki denklemde $r(x, y)$'yi yalnız bırak (iki tarafın logaritmasını al ve $\beta$ ile çarp):

$$r(x, y) = \beta \log \frac{\pi^*(y \mid x)}{\pi_{\text{ref}}(y \mid x)} + \beta \log Z(x)$$

İşte `DPO`'nun altın vuruşu burasıdır! Bu $r(x, y)$ ifadesini alıp **`Bradley-Terry`** tercih denklemindeki $r(x, y_w) - r(x, y_l)$ farkının içine koyduğumuzda:
- Yalnızca $x$'e bağlı olan hesaplanamaz $\beta \log Z(x)$ terimleri **birbirini sadeleştirir ve tamamen yok olur!**

$$r(x, y_w) - r(x, y_l) = \beta \log \frac{\pi_\theta(y_w \mid x)}{\pi_{\text{ref}}(y_w \mid x)} - \beta \log \frac{\pi_\theta(y_l \mid x)}{\pi_{\text{ref}}(y_l \mid x)}$$

Böylece her yanıt için **Örtük Ödül (`Implicit Reward`)** tanımını elde ederiz:
- **Kazananın Örtük Ödülü:** $\hat{r}_\theta(x, y_w) = \beta \left( \log \pi_\theta(y_w \mid x) - \log \pi_{\text{ref}}(y_w \mid x) \right)$
- **Kaybedenin Örtük Ödülü:** $\hat{r}_\theta(x, y_l) = \beta \left( \log \pi_\theta(y_l \mid x) - \log \pi_{\text{ref}}(y_l \mid x) \right)$
- **Örtük Ödül Marjı (`Implicit Reward Margin`):** $M_\theta = \hat{r}_\theta(x, y_w) - \hat{r}_\theta(x, y_l)$

Ve nihai **`DPO Loss` (Negatif Log-Olabilirlik Kaybı)**:

$$\mathcal{L}_{\text{DPO}}(\pi_\theta; \pi_{\text{ref}}) = -\mathbb{E}_{(x, y_w, y_l) \sim \mathcal{D}} \left[ \log \sigma \left( \beta \log \frac{\pi_\theta(y_w \mid x)}{\pi_{\text{ref}}(y_w \mid x)} - \beta \log \frac{\pi_\theta(y_l \mid x)}{\pi_{\text{ref}}(y_l \mid x)} \right) \right]$$

#### DPO Gradyanı Sezgisel Olarak Ne Yapar?
$\mathcal{L}_{\text{DPO}}$ kaybının $\theta$'ya göre türevini aldığımızda:

$$\nabla_\theta \mathcal{L}_{\text{DPO}} = -\beta \, \mathbb{E} \Big[ \underbrace{\sigma\big(\hat{r}_\theta(x, y_l) - \hat{r}_\theta(x, y_w)\big)}_{\text{Dinamik Ağırlık: Model yanılıyorsa BÜYÜK!}} \Big( \underbrace{\nabla_\theta \log \pi_\theta(y_w \mid x)}_{\text{Chosen olasılığını artır}} - \underbrace{\nabla_\theta \log \pi_\theta(y_l \mid x)}_{\text{Rejected olasılığını azalt}} \Big) \Big]$$

Bu denklemin güzelliğine bak:
1. $\nabla_\theta \log \pi_\theta(y_w \mid x) - \nabla_\theta \log \pi_\theta(y_l \mid x)$: Tercih edilen yanıtın olasılığını yukarı çekerken, reddedilen yanıtın olasılığını aşağı iter.
2. Başındaki $\sigma(\hat{r}_l - \hat{r}_w)$ çarpanı **otomatik bir zorluk ağırlıklandırıcısıdır**: Eğer model zaten $y_w$'yi $y_l$'den çok daha yüksek puanlıyorsa bu ağırlık $0$'a yaklaşır; ama model **yanlışlıkla kötü yanıtı ($y_l$) tercih ediyorsa** ağırlık $1$'e yaklaşır ve modele güçlü bir düzeltme gradyanı uygular!

```python
import math

def log_sigmoid(z):
    # Sayısal olarak kararlı (Numerically Stable) log(1 / (1 + exp(-z))) = -softplus(-z)
    if z >= 0:
        return -math.log1p(math.exp(-z))
    return z - math.log1p(math.exp(z))

# Örnek bir (x, y_w, y_l) çifti için DPO Hesabı (beta = 0.1)
beta = 0.1
pi_w, ref_w = -12.0, -15.0   # Model chosen yanıtın log-olasılığını -15'ten -12'ye çıkarmış (+3 artış)
pi_l, ref_l = -20.0, -16.0   # Model rejected yanıtın log-olasılığını -16'dan -20'ye düşürmüş (-4 düşüş)

r_chosen = beta * (pi_w - ref_w)      # 0.1 * (+3.0) = +0.3
r_rejected = beta * (pi_l - ref_l)    # 0.1 * (-4.0) = -0.4
margin = r_chosen - r_rejected        # 0.3 - (-0.4) = +0.7
tercih_olasiligi = 1.0 / (1.0 + math.exp(-margin))
dpo_loss = -log_sigmoid(margin)

print(f"r_chosen={r_chosen:.2f} | r_rejected={r_rejected:.2f} | Margin={margin:.2f}")
print(f"P(y_w > y_l)={tercih_olasiligi:.4f} | DPO Loss={dpo_loss:.4f}")
```

---

### 3. `DPO`'nun Gizli Kusuru (`Length Bias`) ve `SimPO (Simple Preference Optimization — NeurIPS 2024)`

`DPO` endüstride yaygın kullanıma girdi ancak büyük ölçekli üretimde iki önemli darboğaz ortaya çıktı:
1. **Bellek / Hesaplama Maliyeti:** `DPO` hâlâ bir referans modeline ($\pi_{\text{ref}}$) ihtiyaç duyar (ya bellekte dondurulmuş ikinci bir model tutulur ya da tüm veri kümesinin referans log-olasılıkları diskte önbelleğe alınır).
2. **Uzunluk Yanlılığı (`Length Exploitation / Verbosity Bias`) ve Eğitim-Çıkarım Uyuşmazlığı (`Train-Inference Discrepancy`):**
   - Bir dizinin toplam log-olasılığı, tokenların log-olasılıklarının toplamıdır: $\log \pi_\theta(y \mid x) = \sum_{t=1}^{|y|} \log \pi_\theta(y_t \mid x, y_{<t})$.
   - Uzun yanıtlar ($|y|$ büyük) daha fazla negatif sayı topladığı için ölçekleri kayar ve `DPO` bazen $\pi_{\text{ref}}$'e kıyasla gereksiz yere geveze (`Verbose`) yanıtları ödüllendirir. Üstelik çıkarım (`Inference`) anında $\pi_{\text{ref}}$ yoktur; çıkarım motoru yalnızca $\pi_\theta$'nın kendi uzunluk-normalize olasılığına göre üretim yapar!

**Meng et al. (2024 — `SimPO: Simple Preference Optimization with a Reference-Free Reward`)** bu iki sorunu tek darbede çözdü:
1. **Referans Modelini Tamamen Kaldır (`Reference-Free`):** $\pi_{\text{ref}}$ kullanma! VRAM tüketimi ve ileri geçiş süresi doğrudan yarıya iner.
2. **Uzunluk Normalizasyonu (`Length-Normalized Average Log-Probability`):** Toplam log-olasılık yerine **token başına ortalama log-olasılığı** kullan:
   $$s_\theta(x, y) = \frac{1}{|y|} \sum_{t=1}^{|y|} \log \pi_\theta(y_t \mid x, y_{<t})$$
3. **Hedef Ödül Marjı (`Target Reward Margin` $\gamma > 0$):** Kazanan yanıtın ortalama puanı kaybedenden sadece "birazcık" büyük olmasın; en az bir $\gamma$ marjı kadar önde olmaya zorlansın:

$$\mathcal{L}_{\text{SimPO}}(\pi_\theta) = -\mathbb{E}_{(x, y_w, y_l) \sim \mathcal{D}} \left[ \log \sigma \left( \frac{\beta}{|y_w|} \log \pi_\theta(y_w \mid x) - \frac{\beta}{|y_l|} \log \pi_\theta(y_l \mid x) - \gamma \right) \right]$$

---

### 4. Gerçek PyTorch Üretim Kodu: `DPO` ve `SimPO` Kayıp Fonksiyonları

Gerçek bir `Post-Training` kütüphanesinde (`TRL`, `torchtune`, `OpenRLHF`) maskelenmiş dizi log-olasılıkları ve `DPO / SimPO` kaybı PyTorch ile şu şekilde yazılır:

```python norun
import torch
import torch.nn.functional as F

def sequence_log_probs(logits: torch.Tensor, labels: torch.Tensor, ignore_index: int = -100):
    """
    logits: (Batch, SeqLen, VocabSize)
    labels: (Batch, SeqLen) -> Prompt tokenları -100 ile maskelenmiştir.
    Döndürür: (toplam_logp, ortalama_logp) -> Her ikisi de (Batch,) boyutunda.
    """
    # Causal LM kaydırması: t. adımdaki logit, (t+1). adımdaki etiketi tahmin eder
    shift_logits = logits[:, :-1, :]
    shift_labels = labels[:, 1:]

    loss_mask = (shift_labels != ignore_index)
    # -100 olan indeksleri gather hatası vermemesi için geçici olarak 0 yap
    safe_labels = shift_labels.masked_fill(~loss_mask, 0)

    log_probs = F.log_softmax(shift_logits, dim=-1)
    token_logp = torch.gather(log_probs, dim=-1, index=safe_labels.unsqueeze(-1)).squeeze(-1)
    masked_token_logp = token_logp * loss_mask.to(token_logp.dtype)

    sum_logp = masked_token_logp.sum(dim=-1)
    valid_lengths = loss_mask.sum(dim=-1).clamp(min=1)
    avg_logp = sum_logp / valid_lengths
    return sum_logp, avg_logp

def dpo_loss_pytorch(pi_yw_logp, pi_yl_logp, ref_yw_logp, ref_yl_logp, beta: float = 0.1):
    r_chosen = beta * (pi_yw_logp - ref_yw_logp)
    r_rejected = beta * (pi_yl_logp - ref_yl_logp)
    logits = r_chosen - r_rejected
    losses = -F.logsigmoid(logits)
    accuracy = (r_chosen > r_rejected).float().mean()
    return losses.mean(), r_chosen.detach(), r_rejected.detach(), accuracy
```

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [DPO makalesi](https://arxiv.org/abs/2305.18290). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: tahmin Uzunluk Tuzağı: Toplam Log-Olasılık vs SimPO Uzunluk Normalizasyonu
Aşağıdaki kodda kısa ve öz bir `Chosen` yanıtı (4 token: her biri `-0.8` log-olasılıklı) ile gereksiz uzatılmış ama her tokenı daha düşük kaliteli bir `Rejected` yanıtı (10 token: her biri `-0.5` değil `-0.9` log-olasılıklı, ya da tersine 2 tokenlık çok kısa bir yanıt) karşılaştırılıyor. Şimdi şu senaryoya bak:
- `Chosen` yanıtı: 8 token, her tokenın log-olasılığı `-0.6` (toplam `-4.8`, token başına ortalama `-0.60`).
- `Rejected` yanıtı: 4 token, her tokenın log-olasılığı `-1.0` (toplam `-4.0`, token başına ortalama `-1.00`).
Uzunluk normalizasyonu **yapılmazsa** (toplam log-olasılık) ve `SimPO` gibi uzunluk normalizasyonu **yapılırsa** (ortalama log-olasılık) hangi yanıt kazanır?

```python
chosen_tok = [-0.6] * 8    # 8 token, yüksek kalite (-0.6 / token)
rejected_tok = [-1.0] * 4  # 4 token, düşük kalite (-1.0 / token)

toplam_fark = round(sum(chosen_tok) - sum(rejected_tok), 2)
ort_chosen = sum(chosen_tok) / len(chosen_tok)
ort_rejected = sum(rejected_tok) / len(rejected_tok)
simpo_fark = round(ort_chosen - ort_rejected, 2)

print(f"ToplamFark={toplam_fark} (ChosenÖndeMi={toplam_fark > 0})")
print(f"SimPOFark={simpo_fark} (ChosenÖndeMi={simpo_fark > 0})")
```

???

```cikti
ToplamFark=-0.8 (ChosenÖndeMi=False)
SimPOFark=0.4 (ChosenÖndeMi=True)
```
Toplam log-olasılıkta `Chosen` 8 token olduğu için toplamı `-4.8` eder ve 4 tokenlık `Rejected` (`-4.0`) karşısında haksız yere geride kalır (`ToplamFark=-0.8`, `False`). Oysa `SimPO` token sayısına bölerek uzunluk normalizasyonu yaptığı için `Chosen` ortalaması `-0.6`, `Rejected` ortalaması `-1.0` olur ve kaliteli yanıt `+0.4` farkla hak ettiği şekilde öne geçer (`True`).
:::

::: gorev 1 · DPO Kaybı (Loss) ve Implicit Reward Margin Hesabı
Bir yığın (`Batch`) içindeki $(x, y_w, y_l)$ tercih örnekleri için **Rafailov et al. `Direct Preference Optimization (DPO)`** kaybını, örtük ödülleri ve tercih doğruluğunu (`Reward Accuracy`) hesaplayan `dpo_kayip_hesapla(pi_chosen_logp, pi_rejected_logp, ref_chosen_logp, ref_rejected_logp, beta)` işlevini yaz.

**Girdi Kuralları ve Doğrulama:**
- `pi_chosen_logp`, `pi_rejected_logp`, `ref_chosen_logp`, `ref_rejected_logp`: Aynı uzunlukta ($N \ge 1$), boş olmayan 1B sayı listeleri (`bool` olmayan sonlu `int` veya `float`).
- `beta`: KL-düzenleme sıcaklığı ($\beta > 0$), `bool` olmayan sonlu pozitif sayı.

**Hesaplama Kuralları:**
Her $i \in \{0, \dots, N-1\}$ örneği için:
1. Kazananın örtük ödülü: $r_{w, i} = \beta \cdot (\text{pi\_chosen\_logp}[i] - \text{ref\_chosen\_logp}[i])$
2. Kaybedenin örtük ödülü: $r_{l, i} = \beta \cdot (\text{pi\_rejected\_logp}[i] - \text{ref\_rejected\_logp}[i])$
3. Örtük ödül marjı (`Margin`): $m_i = r_{w, i} - r_{l, i}$
4. Örnek kaybı: $\ell_i = -\log \sigma(m_i) = \log(1 + e^{-m_i})$ (büyük $|m_i|$ değerlerinde `OverflowError` vermemesi için sayısal kararlı `log_sigmoid` kullan!).
5. Yığın (`Batch`) metrikleri:
   - `ortalama_kayip`: $\frac{1}{N} \sum_{i=0}^{N-1} \ell_i$
   - `chosen_odulleri`: $[r_{w, 0}, \dots, r_{w, N-1}]$ (`float` listesi)
   - `rejected_odulleri`: $[r_{l, 0}, \dots, r_{l, N-1}]$ (`float` listesi)
   - `ortalama_marj`: $\frac{1}{N} \sum_{i=0}^{N-1} m_i$
   - `tercih_dogrulugu`: $r_{w, i} > r_{l, i}$ koşulunu sağlayan örneklerin oranı ($\frac{\text{sayı}(r_{w, i} > r_{l, i})}{N}$, `float`).
6. İşlev şu sözlüğü döndürmelidir:
   `{"ortalama_kayip": float, "chosen_odulleri": [...], "rejected_odulleri": [...], "ortalama_marj": float, "tercih_dogrulugu": float}`
- Geçersiz herhangi bir girdide veya liste uzunluk uyuşmazlığında `ValueError` yükseltilmelidir.

```starter
import math

# KUSURLU BAŞLANGIÇ KODU: Referans model log-olasılıklarını ve beta çarpanını hesaba katmıyor!
def dpo_kayip_hesapla(pi_chosen_logp, pi_rejected_logp, ref_chosen_logp, ref_rejected_logp, beta):
     n = len(pi_chosen_logp)
     marjlar = [pi_chosen_logp[i] - pi_rejected_logp[i] for i in range(n)]
     kayiplar = [math.log(1.0 + math.exp(-m)) for m in marjlar]
     return {
         "ortalama_kayip": sum(kayiplar) / n,
         "chosen_odulleri": list(pi_chosen_logp),
         "rejected_odulleri": list(pi_rejected_logp),
         "ortalama_marj": sum(marjlar) / n,
         "tercih_dogrulugu": sum(1 for m in marjlar if m > 0) / n,
     }

if __name__ == "__main__":
    print(dpo_kayip_hesapla([-10.0, -14.0], [-15.0, -12.0], [-12.0, -13.0], [-14.0, -15.0], beta=0.1))
```
```test
def sinama_dpo(f):
    import copy, math, random
    def _logsig(z):
        return -math.log1p(math.exp(-z)) if z >= 0 else z - math.log1p(math.exp(z))
    def _ref(pw, pl, rw, rl, b):
        n = len(pw)
        b = float(b)
        cw = [b * (float(pw[i]) - float(rw[i])) for i in range(n)]
        cl = [b * (float(pl[i]) - float(rl[i])) for i in range(n)]
        mm = [cw[i] - cl[i] for i in range(n)]
        ll = [-_logsig(m) for m in mm]
        return {
            "ortalama_kayip": sum(ll) / n,
            "chosen_odulleri": cw,
            "rejected_odulleri": cl,
            "ortalama_marj": sum(mm) / n,
            "tercih_dogrulugu": sum(1 for m in mm if m > 0.0) / n,
        }
    def _yakin(a, b):
        keys = {"ortalama_kayip", "chosen_odulleri", "rejected_odulleri", "ortalama_marj", "tercih_dogrulugu"}
        if not isinstance(a, dict) or set(a.keys()) != keys:
            return False
        for k in ("ortalama_kayip", "ortalama_marj", "tercih_dogrulugu"):
            if isinstance(a[k], bool) or not isinstance(a[k], float) or abs(a[k] - b[k]) > 1e-11:
                return False
        for k in ("chosen_odulleri", "rejected_odulleri"):
            if not isinstance(a[k], list) or len(a[k]) != len(b[k]):
                return False
            for u, v in zip(a[k], b[k]):
                if abs(u - v) > 1e-11:
                    return False
        return True
    try:
        pw, pl = [-10.0, -14.0], [-15.0, -12.0]
        rw, rl = [-12.0, -13.0], [-14.0, -15.0]
        old = (list(pw), list(pl), list(rw), list(rl))
        out = f(pw, pl, rw, rl, 0.1)
        if (pw, pl, rw, rl) != old or not _yakin(out, _ref(pw, pl, rw, rl, 0.1)):
            return False
        # 1. örnek: r_w = 0.2, r_l = -0.1 -> m = 0.3 > 0
        # 2. örnek: r_w = -0.1, r_l = 0.3 -> m = -0.4 < 0 -> doğruluk 0.5
        if abs(out["tercih_dogrulugu"] - 0.5) > 1e-12:
            return False

        # Sayısal kararlılık testi (aşırı büyük/küçük logp farkları)
        out_extreme = f([-10.0, -5000.0], [-5000.0, -10.0], [-20.0, -20.0], [-20.0, -20.0], 1.0)
        if not _yakin(out_extreme, _ref([-10.0, -5000.0], [-5000.0, -10.0], [-20.0, -20.0], [-20.0, -20.0], 1.0)):
            return False

        rng = random.Random(1001)
        for _ in range(20):
            n = rng.randint(1, 8)
            b = rng.uniform(0.05, 0.5)
            p_w = [rng.uniform(-50.0, -1.0) for _ in range(n)]
            p_l = [rng.uniform(-50.0, -1.0) for _ in range(n)]
            r_w = [rng.uniform(-50.0, -1.0) for _ in range(n)]
            r_l = [rng.uniform(-50.0, -1.0) for _ in range(n)]
            if not _yakin(f(p_w, p_l, r_w, r_l, b), _ref(p_w, p_l, r_w, r_l, b)):
                return False

        bad_cases = [
            ([], [-1.0], [-1.0], [-1.0], 0.1),
            ([-1.0, -2.0], [-1.0], [-1.0, -2.0], [-1.0, -2.0], 0.1),
            ([-1.0], [-1.0], [-1.0], [-1.0], 0.0),
            ([-1.0], [-1.0], [-1.0], [-1.0], -0.2),
            ([-1.0], [-1.0], [-1.0], [-1.0], True),
            ([True], [-1.0], [-1.0], [-1.0], 0.1),
            ([float("nan")], [-1.0], [-1.0], [-1.0], 0.1),
            ("[-1.0]", [-1.0], [-1.0], [-1.0], 0.1),
        ]
        for bpw, bpl, brw, brl, bb in bad_cases:
            try:
                f(bpw, bpl, brw, brl, bb)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

dpo_kayip_hesapla = need("dpo_kayip_hesapla")
raises(ValueError, lambda: dpo_kayip_hesapla([], [], [], [], 0.1), msg="boş batch ValueError vermeli")
ok(sinama_dpo(dpo_kayip_hesapla), "DPO örtük ödül, marj, sayısal kararlı logsigmoid ve tercih doğruluğu")
for ad, mut in [
    ("referansı unutan", lambda pw, pl, rw, rl, b: dpo_kayip_hesapla(pw, pl, [0.0]*len(pw), [0.0]*len(pl), b)),
    ("beta=1 sabitleyen", lambda pw, pl, rw, rl, b: dpo_kayip_hesapla(pw, pl, rw, rl, 1.0)),
    ("işareti ters çeviren", lambda pw, pl, rw, rl, b: dpo_kayip_hesapla(pl, pw, rl, rw, b)),
]:
    ok(not sinama_dpo(mut), "mutant reddedildi: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _sayi_listesi_dogrula(lst, n=None):\n    if not isinstance(lst, list) or not lst:\n        raise ValueError('boş olmayan liste gerekli')\n    if n is not None and len(lst) != n:\n        raise ValueError('liste uzunlukları eşit olmalı')\n    for v in lst:\n        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):\n            raise ValueError('geçersiz sayı')\n\ndef _log_sigmoid(z):\n    if z >= 0.0:\n        return -math.log1p(math.exp(-z))\n    return z - math.log1p(math.exp(z))\n\ndef dpo_kayip_hesapla(pi_chosen_logp, pi_rejected_logp, ref_chosen_logp, ref_rejected_logp, beta):\n    _sayi_listesi_dogrula(pi_chosen_logp)\n    n = len(pi_chosen_logp)\n    _sayi_listesi_dogrula(pi_rejected_logp, n)\n    _sayi_listesi_dogrula(ref_chosen_logp, n)\n    _sayi_listesi_dogrula(ref_rejected_logp, n)\n    if isinstance(beta, bool) or not isinstance(beta, (int, float)) or (not math.isfinite(beta)) or (beta <= 0.0):\n        raise ValueError('beta > 0 olmalı')\n    b = float(beta)\n    chosen_odul = [b * (float(pi_chosen_logp[i]) - float(ref_chosen_logp[i])) for i in range(n)]\n    rejected_odul = [b * (float(pi_rejected_logp[i]) - float(ref_rejected_logp[i])) for i in range(n)]\n    marjlar = [chosen_odul[i] - rejected_odul[i] for i in range(n)]\n    kayiplar = [-_log_sigmoid(m) for m in marjlar]\n    return {'ortalama_kayip': sum(kayiplar) / n, 'chosen_odulleri': chosen_odul, 'rejected_odulleri': rejected_odul, 'ortalama_marj': sum(marjlar) / n, 'tercih_dogrulugu': float(sum((1 for m in marjlar if m > 0.0))) / n}", 'referans', 'exec'), _REF)
_t, _g = _ff(dpo_kayip_hesapla, _REF['dpo_kayip_hesapla'], ([-10.0, -14.0], [-15.0, -12.0], [-12.0, -13.0], [-14.0, -15.0], 0.1), tohum=2840, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (dpo_kayip_hesapla): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math

def _sayi_listesi_dogrula(lst, n=None):
    if not isinstance(lst, list) or not lst:
        raise ValueError("boş olmayan liste gerekli")
    if n is not None and len(lst) != n:
        raise ValueError("liste uzunlukları eşit olmalı")
    for v in lst:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError("geçersiz sayı")

def _log_sigmoid(z):
    if z >= 0.0:
        return -math.log1p(math.exp(-z))
    return z - math.log1p(math.exp(z))

def dpo_kayip_hesapla(pi_chosen_logp, pi_rejected_logp, ref_chosen_logp, ref_rejected_logp, beta):
    _sayi_listesi_dogrula(pi_chosen_logp)
    n = len(pi_chosen_logp)
    _sayi_listesi_dogrula(pi_rejected_logp, n)
    _sayi_listesi_dogrula(ref_chosen_logp, n)
    _sayi_listesi_dogrula(ref_rejected_logp, n)

    if isinstance(beta, bool) or not isinstance(beta, (int, float)) or not math.isfinite(beta) or beta <= 0.0:
        raise ValueError("beta > 0 olmalı")

    b = float(beta)
    chosen_odul = [b * (float(pi_chosen_logp[i]) - float(ref_chosen_logp[i])) for i in range(n)]
    rejected_odul = [b * (float(pi_rejected_logp[i]) - float(ref_rejected_logp[i])) for i in range(n)]
    marjlar = [chosen_odul[i] - rejected_odul[i] for i in range(n)]
    kayiplar = [-_log_sigmoid(m) for m in marjlar]

    return {
        "ortalama_kayip": sum(kayiplar) / n,
        "chosen_odulleri": chosen_odul,
        "rejected_odulleri": rejected_odul,
        "ortalama_marj": sum(marjlar) / n,
        "tercih_dogrulugu": float(sum(1 for m in marjlar if m > 0.0)) / n,
    }

if __name__ == "__main__":
    print(dpo_kayip_hesapla([-10.0, -14.0], [-15.0, -12.0], [-12.0, -13.0], [-14.0, -15.0], beta=0.1))
```
```hint
Her örnek için `r_w = beta * (pi_w - ref_w)` ve `r_l = beta * (pi_l - ref_l)` hesapla. `m = r_w - r_l` farkını kararlı `_log_sigmoid(m)` fonksiyonuna verip negatifini al.
```
:::

::: gorev 2 · Uzunluk Normalize Edilmiş SimPO (Reference-Free) Tercih Kaybı
Referans modelini ortadan kaldıran ve uzunluk yanlılığını (`Length Bias`) önleyen **`SimPO (Simple Preference Optimization)`** algoritmasını tek bir tercih çifti için hesaplayan `simpo_kayip_hesapla(chosen_token_logp, rejected_token_logp, beta, gamma_margin)` işlevini yaz.

**Girdi Kuralları ve Doğrulama:**
- `chosen_token_logp`: Kazanan yanıttaki her tokenın log-olasılığını tutan boş olmayan 1B liste (`len >= 1`, elemanları `bool` olmayan sonlu sayılar).
- `rejected_token_logp`: Kaybeden yanıttaki her tokenın log-olasılığını tutan boş olmayan 1B liste (`len >= 1`, elemanları `bool` olmayan sonlu sayılar; uzunluğu `chosen_token_logp`'tan farklı olabilir!).
- `beta`: Ölçekleme sıcaklığı ($\beta > 0$), `bool` olmayan sonlu pozitif sayı.
- `gamma_margin`: Hedef ödül marjı ($\gamma \ge 0$), `bool` olmayan sonlu negatif olmayan sayı.

**Hesaplama Kuralları:**
1. Uzunluk normalize ortalama log-olasılıklar:
   - $\bar{s}_w = \frac{1}{|y_w|} \sum_{t=1}^{|y_w|} \text{chosen\_token\_logp}[t]$
   - $\bar{s}_l = \frac{1}{|y_l|} \sum_{t=1}^{|y_l|} \text{rejected\_token\_logp}[t]$
2. `SimPO` marjı (hedef marj $\gamma$ düşülmüş ölçekli fark):
   - $z = \beta \cdot (\bar{s}_w - \bar{s}_l) - \gamma$
3. `simpo_kaybi`: $-\log \sigma(z)$ (sayısal kararlı `log_sigmoid` ile).
4. `marj_asildi_mi`: Ölçekli ödül farkı hedef marjı aştıysa ($\beta \cdot (\bar{s}_w - \bar{s}_l) > \gamma$, yani $z > 0$) `True`, değilse `False`.
5. İşlev şu sözlüğü döndürmelidir:
   `{"chosen_ort_logp": float, "rejected_ort_logp": float, "simpo_logit": float, "simpo_kaybi": float, "marj_asildi_mi": bool}`
- Geçersiz herhangi bir girdide `ValueError` yükseltilmelidir.

```starter
import math

# KUSURLU BAŞLANGIÇ KODU: Uzunluk normalizasyonu yapmıyor ve gamma_margin değerini çıkarmıyor!
def simpo_kayip_hesapla(chosen_token_logp, rejected_token_logp, beta, gamma_margin):
     sw = sum(chosen_token_logp)
     sl = sum(rejected_token_logp)
     z = beta * (sw - sl)
     return {
         "chosen_ort_logp": sw,
         "rejected_ort_logp": sl,
         "simpo_logit": z,
         "simpo_kaybi": math.log1p(math.exp(-z)),
         "marj_asildi_mi": z > 0,
     }

if __name__ == "__main__":
    print(simpo_kayip_hesapla([-0.6, -0.8, -0.7, -0.7], [-1.2, -1.4], beta=2.0, gamma_margin=0.5))
```
```test
def sinama_simpo(f):
    import copy, math, random
    def _logsig(z):
        return -math.log1p(math.exp(-z)) if z >= 0 else z - math.log1p(math.exp(z))
    def _ref(cw, cl, b, g):
        sw = sum(float(x) for x in cw) / len(cw)
        sl = sum(float(x) for x in cl) / len(cl)
        z = float(b) * (sw - sl) - float(g)
        return {
            "chosen_ort_logp": sw,
            "rejected_ort_logp": sl,
            "simpo_logit": z,
            "simpo_kaybi": -_logsig(z),
            "marj_asildi_mi": bool(z > 0.0),
        }
    def _yakin(a, b):
        keys = {"chosen_ort_logp", "rejected_ort_logp", "simpo_logit", "simpo_kaybi", "marj_asildi_mi"}
        if not isinstance(a, dict) or set(a.keys()) != keys:
            return False
        if type(a["marj_asildi_mi"]) is not bool or a["marj_asildi_mi"] != b["marj_asildi_mi"]:
            return False
        for k in ("chosen_ort_logp", "rejected_ort_logp", "simpo_logit", "simpo_kaybi"):
            if isinstance(a[k], bool) or not isinstance(a[k], float) or abs(a[k] - b[k]) > 1e-11:
                return False
        return True
    try:
        cw = [-0.6, -0.8, -0.7, -0.7]  # ort = -0.7
        cl = [-1.2, -1.4]              # ort = -1.3
        # beta=2.0 * (-0.7 - (-1.3)) - 0.5 = 2.0 * 0.6 - 0.5 = 0.7 > 0
        ocw, ocl = list(cw), list(cl)
        out = f(cw, cl, 2.0, 0.5)
        if cw != ocw or cl != ocl or not _yakin(out, _ref(cw, cl, 2.0, 0.5)):
            return False
        if abs(out["simpo_logit"] - 0.7) > 1e-12 or out["marj_asildi_mi"] is not True:
            return False

        # Marjın aşılamadığı durum: beta*(sw-sl) = 0.4, gamma = 0.5 -> z = -0.1 -> False
        out2 = f([-0.8, -0.8], [-1.0, -1.0, -1.0], 2.0, 0.5)
        if not _yakin(out2, _ref([-0.8, -0.8], [-1.0, -1.0, -1.0], 2.0, 0.5)) or out2["marj_asildi_mi"] is not False:
            return False

        rng = random.Random(1002)
        for _ in range(25):
            nw = rng.randint(1, 10)
            nl = rng.randint(1, 10)
            cc = [rng.uniform(-5.0, -0.05) for _ in range(nw)]
            rr = [rng.uniform(-5.0, -0.05) for _ in range(nl)]
            bb = rng.uniform(0.5, 5.0)
            gg = rng.uniform(0.0, 2.0)
            if not _yakin(f(cc, rr, bb, gg), _ref(cc, rr, bb, gg)):
                return False

        bad_cases = [
            ([], [-1.0], 2.0, 0.5),
            ([-1.0], [], 2.0, 0.5),
            ([-1.0], [-1.0], 0.0, 0.5),
            ([-1.0], [-1.0], -1.0, 0.5),
            ([-1.0], [-1.0], 2.0, -0.1),  # negatif gamma_margin
            ([-1.0], [-1.0], True, 0.5),
            ([-1.0], [-1.0], 2.0, False),
            ([True], [-1.0], 2.0, 0.5),
            ([float("inf")], [-1.0], 2.0, 0.5),
        ]
        for bc, br, bb, bg in bad_cases:
            try:
                f(bc, br, bb, bg)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

simpo_kayip_hesapla = need("simpo_kayip_hesapla")
ok(simpo_kayip_hesapla([0.0], [-1000.0], 1.0, 0.0)["simpo_kaybi"] == 0.0, "büyük pozitif marj taşmamalı")
ok(simpo_kayip_hesapla([-1000.0], [0.0], 1.0, 0.0)["simpo_kaybi"] == 1000.0, "büyük negatif marj taşmamalı")
ok(sinama_simpo(simpo_kayip_hesapla), "SimPO uzunluk normalizasyonu, gamma marjı ve kararlı kayıp")
for ad, mut in [
    ("uzunluğa bölmeyen", lambda cw, cl, b, g: dict(simpo_kayip_hesapla(cw, cl, b, g), chosen_ort_logp=float(sum(cw)))),
    ("gamma marjını çıkarmayan", lambda cw, cl, b, g: simpo_kayip_hesapla(cw, cl, b, 0.0)),
    ("marj_asildi_mi >= 0 yapan", lambda cw, cl, b, g: dict(simpo_kayip_hesapla(cw, cl, b, g), marj_asildi_mi=True)),
]:
    ok(not sinama_simpo(mut), "mutant reddedildi: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _tok_dogrula(lst):\n    if not isinstance(lst, list) or not lst:\n        raise ValueError('boş olmayan token listesi gerekli')\n    for v in lst:\n        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):\n            raise ValueError('geçersiz token logp')\n\ndef _log_sigmoid(z):\n    if z >= 0.0:\n        return -math.log1p(math.exp(-z))\n    return z - math.log1p(math.exp(z))\n\ndef simpo_kayip_hesapla(chosen_token_logp, rejected_token_logp, beta, gamma_margin):\n    _tok_dogrula(chosen_token_logp)\n    _tok_dogrula(rejected_token_logp)\n    for v in (beta, gamma_margin):\n        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):\n            raise ValueError('geçersiz parametre')\n    if beta <= 0.0 or gamma_margin < 0.0:\n        raise ValueError('beta > 0 ve gamma_margin >= 0 olmalı')\n    sw = sum((float(x) for x in chosen_token_logp)) / len(chosen_token_logp)\n    sl = sum((float(x) for x in rejected_token_logp)) / len(rejected_token_logp)\n    z = float(beta) * (sw - sl) - float(gamma_margin)\n    kayip = -_log_sigmoid(z)\n    return {'chosen_ort_logp': sw, 'rejected_ort_logp': sl, 'simpo_logit': z, 'simpo_kaybi': kayip, 'marj_asildi_mi': bool(z > 0.0)}", 'referans', 'exec'), _REF)
_t, _g = _ff(simpo_kayip_hesapla, _REF['simpo_kayip_hesapla'], ([-0.6, -0.8, -0.7, -0.7], [-1.2, -1.4], 2.0, 0.5), tohum=3069, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (simpo_kayip_hesapla): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math

def _tok_dogrula(lst):
    if not isinstance(lst, list) or not lst:
        raise ValueError("boş olmayan token listesi gerekli")
    for v in lst:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError("geçersiz token logp")

def _log_sigmoid(z):
    if z >= 0.0:
        return -math.log1p(math.exp(-z))
    return z - math.log1p(math.exp(z))

def simpo_kayip_hesapla(chosen_token_logp, rejected_token_logp, beta, gamma_margin):
    _tok_dogrula(chosen_token_logp)
    _tok_dogrula(rejected_token_logp)
    for v in (beta, gamma_margin):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError("geçersiz parametre")
    if beta <= 0.0 or gamma_margin < 0.0:
        raise ValueError("beta > 0 ve gamma_margin >= 0 olmalı")

    sw = sum(float(x) for x in chosen_token_logp) / len(chosen_token_logp)
    sl = sum(float(x) for x in rejected_token_logp) / len(rejected_token_logp)
    z = float(beta) * (sw - sl) - float(gamma_margin)
    kayip = -_log_sigmoid(z)

    return {
        "chosen_ort_logp": sw,
        "rejected_ort_logp": sl,
        "simpo_logit": z,
        "simpo_kaybi": kayip,
        "marj_asildi_mi": bool(z > 0.0),
    }

if __name__ == "__main__":
    print(simpo_kayip_hesapla([-0.6, -0.8, -0.7, -0.7], [-1.2, -1.4], beta=2.0, gamma_margin=0.5))
```
```hint
Önce `sw = sum(chosen_token_logp) / len(chosen_token_logp)` ve `sl = sum(rejected_token_logp) / len(rejected_token_logp)` ortalamalarını bul. Ardından `z = beta * (sw - sl) - gamma_margin` hesaplayıp `-_log_sigmoid(z)` ile kaybı döndür.
```
:::

::: anlat Gerçek deney: SmolLM2-Instruct'ı gerçek DPO ile eğitmek ve tercih zehirlemesi
Final gerçek bir tercih eğitimi yapar (CPU, yaklaşık bir buçuk dakika, indirme yok):

- 8 tercih çifti (güvenlik ve destek soruları; biri yararlı, biri kötü yanıt) gerçek **SmolLM2-135M-Instruct** sohbet şablonuyla hazırlanır. Referans model eğitim öncesi kopyadır.
- Model 8 adım tam DPO ile eğitilir ($\beta = 0.1$). Eğitimden sonra yanıt log-olasılıkları modelden alınır ve **senin** `dpo_kayip_hesapla` işlevinle değerlendirilir; sonuç torch'un `logsigmoid` referansıyla karşılaştırılır.
- **Zehirleme:** aynı eğitim, 8 çiftten 3'ünün etiketi ters çevrilerek baştan tekrarlanır. Değerlendirme gerçek tercihlere göre yapılır: model zehirli çiftlerde kötü yanıtı tercih etmeyi öğrenir. DPO kaybı bunu ayırt edemez; kayıp yalnız etikete göre düşer.
- **SimPO:** eğitim öncesi modelin gerçek token log-olasılıklarıyla senin `simpo_kayip_hesapla` işlevin çalıştırılır. Ayrıca toplam log-olasılığın ve uzunluğa bölünmüş ortalamanın kaç çiftte **ters** tercih verdiği sayılır: kısa yanıt toplamda hep avantajlıdır.

Kabul: iki işlevin farksal taramayı geçmesi; DPO kaybının torch'tan en çok `1e-6`, SimPO'nun `1e-9` farklı olması; temiz eğitimde kaybın düşüp tercih doğruluğunun en az 0.75 olması; zehirli eğitimin zehirli çiftlerdeki doğruluğu temiz eğitime göre düşürmesi.

**Kanıt dosyasını oku:** `temiz` ve `zehirli` (kayıp, doğruluk, marj, `chosen_logp_degisim`, `rejected_logp_degisim`, `zehirli_ciftlerde_dogru`) ile `toplam_ve_ortalama_ters_dusen`. Soru 1: Zehirli eğitimde chosen log-olasılığı neden düştü ve bu DPO hakkında ne söylüyor? Soru 2: Zehirli çiftleri eğitimden önce yakalamak için hangi ölçümü kullanırdın? Soru 3: Uzunluk etkisi değerlendirmede nasıl yanıltır?
:::

::: gorev Gerçek deney · SmolLM2-Instruct'ta gerçek DPO eğitimi, etiket zehirlemesi ve SimPO
Önceki görevlerdeki `dpo_kayip_hesapla`, `simpo_kayip_hesapla` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 300
```
```starter
import ai_lab
import math

def dpo_kayip_hesapla(pi_chosen_logp, pi_rejected_logp, ref_chosen_logp, ref_rejected_logp, beta):
    n = len(pi_chosen_logp)
    marjlar = [pi_chosen_logp[i] - pi_rejected_logp[i] for i in range(n)]
    kayiplar = [math.log(1.0 + math.exp(-m)) for m in marjlar]
    return {'ortalama_kayip': sum(kayiplar) / n, 'chosen_odulleri': list(pi_chosen_logp), 'rejected_odulleri': list(pi_rejected_logp), 'ortalama_marj': sum(marjlar) / n, 'tercih_dogrulugu': sum((1 for m in marjlar if m > 0)) / n}

import math

def simpo_kayip_hesapla(chosen_token_logp, rejected_token_logp, beta, gamma_margin):
    sw = sum(chosen_token_logp)
    sl = sum(rejected_token_logp)
    z = beta * (sw - sl)
    return {'chosen_ort_logp': sw, 'rejected_ort_logp': sl, 'simpo_logit': z, 'simpo_kaybi': math.log1p(math.exp(-z)), 'marj_asildi_mi': z > 0}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_10 as D
    D.goster(dpo_kayip_hesapla, simpo_kayip_hesapla)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_egit', '_token_logp', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
dpo_kayip_hesapla = need("dpo_kayip_hesapla")
simpo_kayip_hesapla = need("simpo_kayip_hesapla")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _sayi_listesi_dogrula(lst, n=None):\n    if not isinstance(lst, list) or not lst:\n        raise ValueError('boş olmayan liste gerekli')\n    if n is not None and len(lst) != n:\n        raise ValueError('liste uzunlukları eşit olmalı')\n    for v in lst:\n        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):\n            raise ValueError('geçersiz sayı')\n\ndef _log_sigmoid(z):\n    if z >= 0.0:\n        return -math.log1p(math.exp(-z))\n    return z - math.log1p(math.exp(z))\n\ndef dpo_kayip_hesapla(pi_chosen_logp, pi_rejected_logp, ref_chosen_logp, ref_rejected_logp, beta):\n    _sayi_listesi_dogrula(pi_chosen_logp)\n    n = len(pi_chosen_logp)\n    _sayi_listesi_dogrula(pi_rejected_logp, n)\n    _sayi_listesi_dogrula(ref_chosen_logp, n)\n    _sayi_listesi_dogrula(ref_rejected_logp, n)\n    if isinstance(beta, bool) or not isinstance(beta, (int, float)) or (not math.isfinite(beta)) or (beta <= 0.0):\n        raise ValueError('beta > 0 olmalı')\n    b = float(beta)\n    chosen_odul = [b * (float(pi_chosen_logp[i]) - float(ref_chosen_logp[i])) for i in range(n)]\n    rejected_odul = [b * (float(pi_rejected_logp[i]) - float(ref_rejected_logp[i])) for i in range(n)]\n    marjlar = [chosen_odul[i] - rejected_odul[i] for i in range(n)]\n    kayiplar = [-_log_sigmoid(m) for m in marjlar]\n    return {'ortalama_kayip': sum(kayiplar) / n, 'chosen_odulleri': chosen_odul, 'rejected_odulleri': rejected_odul, 'ortalama_marj': sum(marjlar) / n, 'tercih_dogrulugu': float(sum((1 for m in marjlar if m > 0.0))) / n}\n\nimport math\n\ndef _tok_dogrula(lst):\n    if not isinstance(lst, list) or not lst:\n        raise ValueError('boş olmayan token listesi gerekli')\n    for v in lst:\n        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):\n            raise ValueError('geçersiz token logp')\n\ndef _log_sigmoid(z):\n    if z >= 0.0:\n        return -math.log1p(math.exp(-z))\n    return z - math.log1p(math.exp(z))\n\ndef simpo_kayip_hesapla(chosen_token_logp, rejected_token_logp, beta, gamma_margin):\n    _tok_dogrula(chosen_token_logp)\n    _tok_dogrula(rejected_token_logp)\n    for v in (beta, gamma_margin):\n        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):\n            raise ValueError('geçersiz parametre')\n    if beta <= 0.0 or gamma_margin < 0.0:\n        raise ValueError('beta > 0 ve gamma_margin >= 0 olmalı')\n    sw = sum((float(x) for x in chosen_token_logp)) / len(chosen_token_logp)\n    sl = sum((float(x) for x in rejected_token_logp)) / len(rejected_token_logp)\n    z = float(beta) * (sw - sl) - float(gamma_margin)\n    kayip = -_log_sigmoid(z)\n    return {'chosen_ort_logp': sw, 'rejected_ort_logp': sl, 'simpo_logit': z, 'simpo_kaybi': kayip, 'marj_asildi_mi': bool(z > 0.0)}", 'referans', 'exec'), _REF)
_t, _g = _ff(dpo_kayip_hesapla, _REF['dpo_kayip_hesapla'], ([-10.0, -14.0], [-15.0, -12.0], [-12.0, -13.0], [-14.0, -15.0], 0.1), tohum=2840, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (dpo_kayip_hesapla): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(simpo_kayip_hesapla, _REF['simpo_kayip_hesapla'], ([-0.6, -0.8, -0.7, -0.7], [-1.2, -1.4], 2.0, 0.5), tohum=3069, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (simpo_kayip_hesapla): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
kontrol(dpo_kayip_hesapla([1000.0], [-1000.0], [0.0], [0.0], 1.0) == _REF['dpo_kayip_hesapla']([1000.0], [-1000.0], [0.0], [0.0], 1.0), "büyük pozitif marjda log-sigmoid kararlılığı")
kontrol(dpo_kayip_hesapla([-1000.0], [1000.0], [0.0], [0.0], 1.0) == _REF['dpo_kayip_hesapla']([-1000.0], [1000.0], [0.0], [0.0], 1.0), "büyük negatif marjda log-sigmoid kararlılığı")
for _kotu_fn, _kotu_args in [
    (dpo_kayip_hesapla, ([], [], [], [], 1.0)),
    (simpo_kayip_hesapla, ([], [-1.0], 2.0, 0.5)),
]:
    try:
        _kotu_fn(*_kotu_args)
        kontrol(False, "boş logprob listesi ValueError fırlatmalı")
    except ValueError:
        kontrol(True, "boş logprob listesi ValueError fırlattı")
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_10 as D
try: r = D.deney(dpo_kayip_hesapla, simpo_kayip_hesapla)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['dpo_ayni'] and r['simpo_ayni'], 'DPO ve SimPO gerçek log-olasılıklarda torch referansıyla aynı')
kontrol(r['egitim_ogrendi'], 'temiz DPO eğitimi kaybı düşürdü, tercih doğruluğu en az 0.75')
kontrol(r['zehir_bozdu'], '3 ters etiket zehirli çiftlerdeki gerçek tercih doğruluğunu düşürdü')
ai_lab.kanit_yaz("ai-uretim-10-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-10", "deney": r})
```
```solution
import ai_lab
import math

def _sayi_listesi_dogrula(lst, n=None):
    if not isinstance(lst, list) or not lst:
        raise ValueError('boş olmayan liste gerekli')
    if n is not None and len(lst) != n:
        raise ValueError('liste uzunlukları eşit olmalı')
    for v in lst:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):
            raise ValueError('geçersiz sayı')

def _log_sigmoid(z):
    if z >= 0.0:
        return -math.log1p(math.exp(-z))
    return z - math.log1p(math.exp(z))

def dpo_kayip_hesapla(pi_chosen_logp, pi_rejected_logp, ref_chosen_logp, ref_rejected_logp, beta):
    _sayi_listesi_dogrula(pi_chosen_logp)
    n = len(pi_chosen_logp)
    _sayi_listesi_dogrula(pi_rejected_logp, n)
    _sayi_listesi_dogrula(ref_chosen_logp, n)
    _sayi_listesi_dogrula(ref_rejected_logp, n)
    if isinstance(beta, bool) or not isinstance(beta, (int, float)) or (not math.isfinite(beta)) or (beta <= 0.0):
        raise ValueError('beta > 0 olmalı')
    b = float(beta)
    chosen_odul = [b * (float(pi_chosen_logp[i]) - float(ref_chosen_logp[i])) for i in range(n)]
    rejected_odul = [b * (float(pi_rejected_logp[i]) - float(ref_rejected_logp[i])) for i in range(n)]
    marjlar = [chosen_odul[i] - rejected_odul[i] for i in range(n)]
    kayiplar = [-_log_sigmoid(m) for m in marjlar]
    return {'ortalama_kayip': sum(kayiplar) / n, 'chosen_odulleri': chosen_odul, 'rejected_odulleri': rejected_odul, 'ortalama_marj': sum(marjlar) / n, 'tercih_dogrulugu': float(sum((1 for m in marjlar if m > 0.0))) / n}

def _tok_dogrula(lst):
    if not isinstance(lst, list) or not lst:
        raise ValueError('boş olmayan token listesi gerekli')
    for v in lst:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):
            raise ValueError('geçersiz token logp')

def simpo_kayip_hesapla(chosen_token_logp, rejected_token_logp, beta, gamma_margin):
    _tok_dogrula(chosen_token_logp)
    _tok_dogrula(rejected_token_logp)
    for v in (beta, gamma_margin):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):
            raise ValueError('geçersiz parametre')
    if beta <= 0.0 or gamma_margin < 0.0:
        raise ValueError('beta > 0 ve gamma_margin >= 0 olmalı')
    sw = sum((float(x) for x in chosen_token_logp)) / len(chosen_token_logp)
    sl = sum((float(x) for x in rejected_token_logp)) / len(rejected_token_logp)
    z = float(beta) * (sw - sl) - float(gamma_margin)
    kayip = -_log_sigmoid(z)
    return {'chosen_ort_logp': sw, 'rejected_ort_logp': sl, 'simpo_logit': z, 'simpo_kaybi': kayip, 'marj_asildi_mi': bool(z > 0.0)}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_10 as D
    D.goster(dpo_kayip_hesapla, simpo_kayip_hesapla)
```
```hint
İki görevin çözümlerini olduğu gibi buraya koy. Eğitim deneyin içinde yapılır; senin işlevlerin eğitim sonrası değerlendirmede kullanılır.
```
:::

::: anlat Sınır
Görevler DPO kaybını ve implicit reward margin'i, uzunluk normalize SimPO kaybını küçük log-olasılıklarla hesaplatır; final adım SmolLM2-Instruct'ı 8 çiftte gerçek DPO ile eğitir (küçük ölçek, genelleme ölçülmez). DPO referans modele göre göreli olasılığı artırır; seçilen yanıtın mutlak olasılığı eğitim sırasında yine de düşebilir. SimPO'nun hedef marjı (γ) ve β ayarı veri kümesine duyarlıdır. Tercih verisine az sayıda ters etiket karışırsa (zehirleme) model istenmeyen davranışı 'tercih edilen' olarak öğrenir; kayıp bunu ayırt edemez. Uzunluk yanlılığı yalnız kayıpta değil değerlendirmede de kontrol edilmelidir.

Kaynaklar: [Rafailov vd. 2023 - Direct Preference Optimization: Your Language Model is Secretly a Reward Model](https://arxiv.org/abs/2305.18290), [Meng vd. 2024 - SimPO: Simple Preference Optimization with a Reference-Free Reward](https://arxiv.org/abs/2405.14734).
:::

::: dusun
`DPO` eğitimi sırasında pratikte sıkça karşılaşılan çok ilginç bir olgu (`Likelihood Displacement`) vardır:
Eğitim ilerledikçe ödül marjı $r(x, y_w) - r(x, y_l)$ sürekli büyür ve `DPO Loss` sıfıra yaklaşır; ancak dikkatle baktığında **hem `Chosen` ($y_w$) yanıtının hem de `Rejected` ($y_l$) yanıtının mutlak log-olasılığının ($\log \pi_\theta(y_w \mid x)$ ve $\log \pi_\theta(y_l \mid x)$) aynı anda düştüğünü** (yalnızca $y_l$'nin daha hızlı düştüğünü!) görürsün.

**Mühendislik Sorusu:** Eğer `Chosen` yanıtının da olasılığı düşüyorsa, olasılık kütlesi sözlükteki hangi tokenlara kayıyor olabilir? Ve bunu önlemek için `DPO` kaybına küçük bir katsayıyla ($\lambda_{\text{NLL}} \approx 0.1$) `SFT Cross-Entropy` terimi eklemek ($\mathcal{L}_{\text{RPO / CPO}} = \mathcal{L}_{\text{DPO}} + \lambda \, \mathcal{L}_{\text{NLL}}(y_w \mid x)$) neden bu sorunu kökten çözer?
:::

::: ozet
- Klasik **`RLHF (PPO)`**, bellekte 4 ayrı model (`Actor`, `Reference`, `Reward`, `Critic`) tutmayı ve canlı örnekleme (`Rollout`) yapmayı gerektirirken; **`Direct Preference Optimization (DPO)`** KL-kısıtlı ödül maksimizasyonunu kapalı formda çözerek ayrı ödül modelini ve `PPO` döngüsünü ortadan kaldırır.
- **`Bradley-Terry Preference Model`** altında her yanıtın örtük ödülü $\hat{r}_\theta(x, y) = \beta \log \frac{\pi_\theta(y \mid x)}{\pi_{\text{ref}}(y \mid x)}$ olarak tanımlanır; hesaplanamaz bölüntü fonksiyonu $Z(x)$ kazanan ve kaybeden yanıtların farkında ($r_w - r_l$) birbirini götürür.
- **`SimPO (Simple Preference Optimization)`**, referans modelini ($\pi_{\text{ref}}$) tamamen kaldırır, dizi log-olasılığını yanıt uzunluğuna ($1 / |y|$) bölerek uzunluk yanlılığını (`Verbosity / Length Bias`) engeller ve bir hedef ödül marjı ($\gamma$) dayatır.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Ödül modelinden kapalı forma (`DPO`) (30 sn).** "KL kısıtlı ödül maksimizasyonunun optimal çözümü örtük ödülü $\beta \log(\pi_\theta / \pi_{\text{ref}})$ olarak yazar; `Bradley-Terry` farkında bölüntü sabiti $Z(x)$ sadeleştiği için ayrı ödül ve `PPO` kritik ağına gerek kalmaz."
2. **Uzunluk yanlılığı ve `SimPO` (30 sn).** "Toplam log-olasılık uzun yanıtlarda terim sayısıyla küçülür; `SimPO` log-olasılığı yanıt uzunluğuna ($1/|y|$) böler, referans model belleğini kaldırır ve $\gamma$ hedef marjı koyar."
3. **Tercih zehirlemesi riski (35 sn).** "Deneyde gördüğümüz gibi `DPO` kaybı etiketin doğruluğunu sorgulamaz: tercih çiftlerinin küçük bir kısmında kazanan/kaybeden etiketi ters çevrilirse model o konularda güvensiz yanıtı sistematik olarak öne çıkarır."
4. **Soru (25 sn).** "Yalnız `chosen - rejected` marjını büyütmek bazen her iki yanıtın mutlak olasılığını da düşürür; bunu engellemek için kayba hangi terim eklenir?"
:::
