---
id: ai-uretim-11
title: "Reasoning Model İnşası (Opus / o1 / R1): GRPO, RLVR Verifier ve Process Reward Model (PRM)"
summary: "Opus 4.6/5.5, OpenAI o1/o3 ve DeepSeek-R1 gibi düşünen (Reasoning) modellerin inşası: <think> biçimi, deterministik RLVR doğrulayıcıları, Critic ağsız GRPO (Group Relative Policy Optimization) ve Test-Time Compute için Process Reward Model (PRM) araması."
track: ai-uretim
order: 11
duration_minutes: 45
difficulty: ileri
xp: 340
prerequisites: [ai-uretim-10]
tags: [reasoning, grpo, rlvr, prm, test-time-compute, deepseek-r1]
esleme: ai-saldiri-64, ai-saldiri-42
---

::: anlat
## RLVR, GRPO ve PRM

Doğrulanabilir bir görevde reward, örneğin test sonucu veya matematiksel kontrol üzerinden üretilebilir. Bu derste verifier skorunu, grup içi GRPO avantajlarını ve PRM ile yol seçimini hesaplayacaksın. Örnek hesaplar belirli bir ticari reasoning modelinin eğitim reçetesi olarak sunulmaz.

R1-Zero raporunda incelenen açık çıktı şablonunda model, yanıt öncesi `<think> ... </think>` arasında uzun izler üretebilir. Raporda gözlenen davranışlar şunlardır:
- Problemi alt parçalara böler,
- Farklı hipotezleri dener,
- *"Dur, burada işaret hatası yaptım, geri dönüp tekrar hesaplayayım!"* (`Self-Correction / Backtracking / "Aha Moment"`) diyerek kendi hatasını yakalar ve ardından nihai cevabı üretir; bu iz doğru cevap veya güvenilir öz denetim garantisi değildir.

Peki insanlığın elinde milyarlarca satırlık "insanların iç sesini ve geri dönüşlerini (`Backtracking`)" anlatan hazır bir `SFT` veri kümesi yokken, bir modele **nasıl düşünmesi gerektiğini sıfırdan öğretiriz?**
Cevap: **`RLVR (Reinforcement Learning with Verifiable Rewards)`** ve **`GRPO (Group Relative Policy Optimization)`**!

| RLVR verifier | GRPO | Test-time compute / PRM search |
|---|---|---|
| Kural tabanlı reward; nöral ödül modeli gerekmez ama verifier hatası mümkündür | Ayrı critic gerekmez; bellek kazancı düzene bağlıdır | Çıkarımda birden çok düşünce dalı üret |
| Birim test/derleme, sembolik matematik ve format kontrolü | Aynı soruya G yanıt örnekle; grup ortalaması ve standart sapmasından avantaj çıkar | PRM ile her adımı puanla; min veya prod skoruyla dalları karşılaştır |
| Doğru/yanlış skoru kurala bağlıdır; testten geçmek tam doğruluk garantisi değildir | Clipped surrogate hedefi ve KL cezasını hesapla | Beam search ile düşük skorlu dalları buda; PRM hatalarını ayrıca ölç |


---

### 1. Neden Nöral Ödül Modeli Değil de `RLVR (Reinforcement Learning with Verifiable Rewards)`?

Nöral ödül modeli kullanan `RLHF` içinde politika, gerçek görev kalitesi yerine ödül modelinin hatalarını optimize edebilir (`Reward Hacking`). Uzun bir düşünce izi bu riski ortadan kaldırmaz; belirli bir token sayısında zorunlu olarak ortaya çıktığı da iddia edilmez.

**`RLVR`**, doğrulanabilen görevlerde kural tabanlı bir `Verifier` kullanabilir. Bu kural deterministik olsa bile eksik veya hatalı olabilir; kandırılamaz olduğu varsayılmaz. Aşağıdaki ödüller öğretici örnektir, bütün modellerin sabit reçetesi değildir:
1. **`Format Reward` ($r_{\text{format}}$):** Model düşüncesini tam olarak `<think>...</think>` etiketleri içine yazdı mı ve nihai cevabı `\boxed{...}` içine koydu mu? (Örn: Evet ise `+0.2`, hayır ise `0.0`).
2. **`Accuracy / Verification Reward` ($r_{\text{acc}}$):**
   - **Matematik / Mantık:** `\boxed{...}` içindeki cevap sembolik cebir çözücüsü (`SymPy`) ile gerçek cevaba eşit mi? (`+1.0` veya `0.0`).
   - **Yazılım / Kodlama:** Üretilen kod izole `Sandbox` içinde derlenip gizli birim testlerin (`Unit Tests`) tamamından geçti mi? (`+1.0` veya `0.0`).

Modelin `<think>` bloğu içinde *nasıl* düşündüğüne hiç karışmayız! Sadece doğru sonuca ulaşan düşünce zincirlerini ödüllendiririz. Binlerce RL adımından sonra model, **uzun düşünmenin, sağlamasını yapmanın (`Verification`) ve hatadan geri dönmenin (`Backtracking`) doğru sonuca ulaşma ihtimalini artırdığını kendiliğinden keşfeder (`Emergent Reasoning / Aha Moment`)**!

---

### 2. `GRPO (Group Relative Policy Optimization)`: Critic Ağını Tarihe Gömen Matematik

`PPO` uygulamalarında öğrenilmiş bir value baseline avantaj tahminine katkı verir. Bu ağın policy ile aynı boyutta olması veya toplam GPU belleğini tam ikiye katlaması zorunlu değildir. Büyük bir ayrı value modeli, parametre/optimizer/aktivasyon maliyeti ekler; baseline tahmin hatası da avantajın varyansını etkileyebilir.

**DeepSeekMath (Shao et al., 2024)** ve **DeepSeek-R1 (2025)** tarafından geliştirilen **`GRPO`**, `Critic` ağını tamamen ortadan kaldırır!

Nasıl?
1. Aynı soru $q$ için eski politikadan ($\pi_{\theta_{\text{old}}}$) bir grup ($G$ adet, örn. $G = 8$ veya $G = 64$) bağımsız çıktı $\{o_1, o_2, \dots, o_G\}$ örneklenir (`Group Rollout`).
2. Deterministik `RLVR` doğrulayıcısı bu $G$ çıktının her birine bir skaler ödül verir: $\mathbf{r} = \{r_1, r_2, \dots, r_G\}$.
3. `Critic` ağının tahmin ettiği baz değer (`Baseline`) yerine, **grubun kendi ödül ortalaması ($\mu_r$) ve standart sapması ($\sigma_r$)** kullanılarak **Grup İçi Bağıl Avantaj (`Group-Relative Advantage`)** hesaplanır:

$$\mu_r = \frac{1}{G} \sum_{i=1}^{G} r_i, \qquad \sigma_r = \sqrt{\frac{1}{G} \sum_{i=1}^{G} (r_i - \mu_r)^2}$$

$$A_i = \frac{r_i - \mu_r}{\sigma_r + \epsilon}$$

Bu formülün zarafetine bak:
- Eğer soru çok kolaysa ve gruptaki çoğu yanıt yüksek puan aldıysa $\mu_r$ yüksek olur; sadece ortalamanın üstüne çıkanlar pozitif avantaj ($A_i > 0$) alır.
- Eğer soru çok zorsa ve 8 yanıttan sadece 1 tanesi doğru cevabı bulduysa, o tek doğru yanıt devasa bir pozitif avantaj ($A_i \gg 0$) alarak modelin o düşünce yolunu hızla pekiştirmesini sağlar!

#### GRPO Sınırlandırılmış Vekil Hedefi (`Clipped Surrogate Objective`) ve Yansız KL Cezası (`Schulman K3 Estimator`)
Her örnek $i \in \{1, \dots, G\}$ için yeni politikanın eski politikaya olasılık oranı (`Probability Ratio`):

$$\rho_i(\theta) = \frac{\pi_\theta(o_i \mid q)}{\pi_{\theta_{\text{old}}}(o_i \mid q)}$$

Modelin tek bir adımda aşırı büyük güncelleme yapıp çökmesini (`Policy Collapse`) önlemek için oran $[1 - \epsilon_{\text{clip}}, 1 + \epsilon_{\text{clip}}]$ aralığına kırpılır (`Clipping`) ve **Schulman'ın her zaman pozitif olan yansız KL tahmincisi** ($\mathbb{D}_{\text{KL}} = \frac{\pi_{\text{ref}}}{\pi_\theta} - \log \frac{\pi_{\text{ref}}}{\pi_\theta} - 1$) cezası çıkarılır:

$$\mathcal{J}_{\text{GRPO}}(\theta) = \frac{1}{G} \sum_{i=1}^{G} \left[ \min \Big( \rho_i(\theta) A_i, \; \text{clip}(\rho_i(\theta), 1 - \epsilon_{\text{clip}}, 1 + \epsilon_{\text{clip}}) A_i \Big) - \beta_{\text{KL}} \, \mathbb{D}_{\text{KL}, i} \right]$$

(Otomatik türev motorlarında maksimize edilen $\mathcal{J}_{\text{GRPO}}(\theta)$ hedefinin negatifi alınarak $\mathcal{L}_{\text{GRPO}} = -\mathcal{J}_{\text{GRPO}}(\theta)$ minimize edilir).

```python
import math

# Bir soruya üretilen G=4 farklı <think> yanıtının GRPO Avantaj Hesabı
oduller = [1.2, 0.2, 0.2, 0.0]  # 1. yanıt hem format (+0.2) hem doğru cevap (+1.0) almış!
G = len(oduller)
mu = sum(oduller) / G
std = math.sqrt(sum((r - mu) ** 2 for r in oduller) / G)
avantajlar = [round((r - mu) / (std + 1e-8), 4) for r in oduller]

print(f"Grup Ortalamasi (mu)={mu:.2f} | Std={std:.4f}")
print(f"Grup Ici Avantajlar (A_i)={avantajlar}")
```

---

### 3. Çıkarım Anında Ölçekleme (`Test-Time Compute`) ve `Process Reward Model (PRM)`

Modelimizi `GRPO` ile eğittik. Peki canlıda (`Inference / Test-Time`) çok kritik bir olimpiyat sorusu veya mimari tasarım problemi çözerken başarıyı nasıl katlarız?

İki tür ödül modeli vardır (**Lightman et al., OpenAI — *"Let's Verify Step by Step"* / Math-Shepherd**):
1. **`ORM (Outcome Reward Model)`:** Düşünce zincirinin sadece en sonundaki nihai cevaba tek bir puan verir. Aradaki hatalı adımları göremez ("Yanlış yoldan gidip şans eseri doğru sonuca ulaşan" tehlikeli zincirleri ayırt edemez).
2. **`PRM (Process Reward Model)`:** `<think>` içindeki her bir mantık adımını ($s_1, s_2, \dots, s_K$) teker teker denetler ve her adıma "bu adım mantıksal olarak geçerli ve doğru yolda mı?" olasılığı $p_k \in [0, 1]$ verir!

Bir düşünce zincirinin (`Chain-of-Thought`) adım puanları $[p_1, p_2, \dots, p_K]$ olduğunda tüm zincirin güvenilirlik skoru 3 farklı stratejiyle (`Aggregation Mode`) birleştirilir:
- **`min` (En Zayıf Halka Kuralı — Endüstri Standardı):** Bir matematiksel kanıtın gücü, içindeki **en zayıf (en şüpheli) adımın** gücü kadardır! Eğer 10 adımdan 9'u `0.99` ama 4. adım hatalı (`0.10`) ise, o zincirin puanı `min = 0.10` olur ve anında elenir!
  $$S_{\text{min}} = \min_{1 \le k \le K} p_k$$
- **`prod` (Çarpımsal Ortak Olasılık):** Tüm adımların aynı anda doğru olma olasılığı:
  $$S_{\text{prod}} = \prod_{k=1}^{K} p_k$$
- **`mean` (Aritmetik Ortalama):** Adım uzunluğundan bağımsız ortalama adım kalitesi:
  $$S_{\text{mean}} = \frac{1}{K} \sum_{k=1}^{K} p_k$$

---

### 4. Gerçek PyTorch Üretim Kodu: `GRPO` Kayıp Hesaplayıcısı

Gerçek bir `DeepSeek-R1 / OpenRLHF / TRL GRPOTrainer` eğitim döngüsünde `GRPO` kaybı PyTorch tensörleriyle şu şekilde kodlanır:

```python norun
import torch

def grpo_loss_pytorch(
    logp_new: torch.Tensor,      # (G, SeqLen) - Yeni politikanın token log-olasılıkları
    logp_old: torch.Tensor,      # (G, SeqLen) - Eski politikanın token log-olasılıkları (detach)
    logp_ref: torch.Tensor,      # (G, SeqLen) - Referans modelin token log-olasılıkları (detach)
    rewards: torch.Tensor,       # (G,) - RLVR Verifier ödülleri
    completion_mask: torch.Tensor, # (G, SeqLen) - Yalnızca üretilen yanıt tokenları için 1, prompt için 0
    eps_clip: float = 0.2,
    beta_kl: float = 0.04,
) -> torch.Tensor:
    # 1. Grup içi bağıl avantaj (Group-Relative Advantage): (G, 1)
    mean_r = rewards.mean()
    std_r = rewards.std(unbiased=False)
    advantages = ((rewards - mean_r) / (std_r + 1e-8)).unsqueeze(-1)

    # 2. Olasılık oranı: rho = exp(logp_new - logp_old)
    ratio = torch.exp(logp_new - logp_old)
    clipped_ratio = torch.clamp(ratio, 1.0 - eps_clip, 1.0 + eps_clip)

    # 3. Clipped Surrogate Objective
    surr1 = ratio * advantages
    surr2 = clipped_ratio * advantages
    policy_obj = torch.minimum(surr1, surr2)

    # 4. Schulman K3 Unbiased KL Penalty: exp(logp_ref - logp_new) - (logp_ref - logp_new) - 1
    log_ratio_ref = logp_ref - logp_new
    kl_per_token = torch.exp(log_ratio_ref) - log_ratio_ref - 1.0

    # 5. Maskeli token ortalaması ve negatif hedef (Loss)
    per_token_loss = -(policy_obj - beta_kl * kl_per_token) * completion_mask
    seq_loss = per_token_loss.sum(dim=-1) / completion_mask.sum(dim=-1).clamp(min=1)
    return seq_loss.mean()
```

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [DeepSeek-R1 teknik raporu](https://arxiv.org/abs/2501.12948). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: tahmin PRM "En Zayıf Halka (Min)" vs "Ortalama (Mean)" Tuzağı
Bir model bir güvenlik açığı analizi için iki farklı `<think>` düşünce zinciri üretti:
- **Zincir A:** 4 adımın puanları `[0.95, 0.95, 0.12, 0.98]` (3. adımda ciddi bir mantık hatası var ama diğer adımlar çok parlak görünüyor!).
- **Zincir B:** 4 adımın puanları `[0.82, 0.80, 0.78, 0.84]` (Her adımı tutarlı ve sağlam).
Aşağıdaki kod `mean` ve `min` stratejilerine göre hangi zinciri seçer?

```python
zincir_A = [0.95, 0.95, 0.12, 0.98]
zincir_B = [0.82, 0.80, 0.78, 0.84]

mean_secim = "A" if (sum(zincir_A)/4) > (sum(zincir_B)/4) else "B"
min_secim = "A" if min(zincir_A) > min(zincir_B) else "B"

print(f"Ortalama_A={sum(zincir_A)/4:.3f}, Ortalama_B={sum(zincir_B)/4:.3f} -> MeanSecim={mean_secim}")
print(f"Min_A={min(zincir_A):.2f}, Min_B={min(zincir_B):.2f} -> MinSecim={min_secim}")
```

???

```cikti
Ortalama_A=0.750, Ortalama_B=0.810 -> MeanSecim=B
Min_A=0.12, Min_B=0.78 -> MinSecim=B
```
Zincir A'nın 3. adımında `0.12` gibi ölümcül bir mantık hatası vardır, ancak diğer adımları yüksek olduğu için aritmetik ortalaması (`0.750`) yüksek görünür (yine de B'nin `0.810` ortalamasının altındadır; A'nın diğer üç adımı `0.99` olsa bile ortalaması `0.7725` olur ve bu B'yi geçmez; buna karşılık bütün adımları `0.70` olan başka bir zinciri mean ile geçer, min ile geçemez!). `min` (En Zayıf Halka) stratejisi ise Zincir A'nın puanını doğrudan `0.12`'ye çekerek hatalı adımı anında yakalar ve sağlam olan `B` zincirini (`0.78`) seçer.
:::

::: gorev 1 · RLVR Doğrulayıcı Puanlama ve GRPO Clipped Policy Objective
Bir soru için örneklenen $G$ adet yanıtın **Grup İçi Bağıl Avantajlarını (`Group-Relative Advantages`)** ve **`GRPO Clipped Surrogate Objective`** değerini hesaplayan `grpo_hedef_hesapla(oduller, oranlar_ratio, kl_degerleri, eps_clip, beta_kl)` işlevini yaz.

**Girdi Kuralları ve Doğrulama:**
- `oduller`: Grup içindeki $G$ adet yanıtın ödülleri ($G \ge 2$, elemanları `bool` olmayan sonlu sayılar).
- `oranlar_ratio`: Her yanıtın olasılık oranı $\rho_i = \frac{\pi_\theta(o_i|q)}{\pi_{\theta_{\text{old}}}(o_i|q)}$ ($G$ elemanlı, tümü `> 0.0` sonlu sayılar).
- `kl_degerleri`: Her yanıtın KL sapması $\mathbb{D}_{\text{KL}, i}$ ($G$ elemanlı, tümü `>= 0.0` sonlu sayılar).
- `eps_clip`: Kırpma sınırı ($\epsilon_{\text{clip}} > 0$), `bool` olmayan sonlu pozitif sayı.
- `beta_kl`: KL ceza katsayısı ($\beta_{\text{KL}} \ge 0$), `bool` olmayan sonlu negatif olmayan sayı.

**Hesaplama Kuralları:**
1. Grup ödül ortalaması $\mu_r = \frac{1}{G} \sum_{i=0}^{G-1} r_i$ ve anakütle standart sapması $\sigma_r = \sqrt{\frac{1}{G} \sum_{i=0}^{G-1} (r_i - \mu_r)^2}$.
2. Grup içi avantajlar (`avantajlar`):
   - Eğer $\sigma_r < 10^{-12}$ ise (tüm ödüller birbirinin aynıysa), sıfıra bölmeyi önlemek için tüm avantajlar `0.0` olmalıdır: $A_i = 0.0$.
   - Aksi halde $A_i = \frac{r_i - \mu_r}{\sigma_r + 10^{-8}}$.
3. Her örnek $i$ için kırpılmış oran: $\tilde{\rho}_i = \min(\max(\rho_i, 1.0 - \epsilon_{\text{clip}}), 1.0 + \epsilon_{\text{clip}})$.
4. Her örnek $i$ için vekil hedef (`Surrogate`): $s_i = \min(\rho_i \cdot A_i, \; \tilde{\rho}_i \cdot A_i)$.
5. Her örnek $i$ için KL-düzenlenmiş net hedef: $j_i = s_i - \beta_{\text{KL}} \cdot \text{kl\_degerleri}[i]$.
6. Metrikler:
   - `avantajlar`: $[A_0, \dots, A_{G-1}]$ (`float` listesi)
   - `grpo_hedefi`: $\mathcal{J}_{\text{GRPO}} = \frac{1}{G} \sum_{i=0}^{G-1} j_i$ (`float`)
   - `grpo_kaybi`: $\mathcal{L}_{\text{GRPO}} = -\mathcal{J}_{\text{GRPO}}$ (`float`)
   - `kirpilan_orani`: $|\rho_i - 1.0| > \epsilon_{\text{clip}}$ olduğu için kırpma sınırına takılan örneklerin oranı ($\frac{\text{sayı}(|\rho_i - 1.0| > \epsilon_{\text{clip}})}{G}$, `float`).
7. İşlev şu sözlüğü döndürmelidir:
   `{"avantajlar": [...], "grpo_hedefi": float, "grpo_kaybi": float, "kirpilan_orani": float}`
- Geçersiz herhangi bir girdide veya uzunluk uyuşmazlığında `ValueError` yükseltilmelidir.

```starter
import math

# KUSURLU BAŞLANGIÇ KODU: Grup standart sapmasıyla bölmüyor, ratio kırpması (clipping) ve KL cezasını uygulamıyor!
def grpo_hedef_hesapla(oduller, oranlar_ratio, kl_degerleri, eps_clip, beta_kl):
     g = len(oduller)
     mu = sum(oduller) / g
     av = [r - mu for r in oduller]
     hedef = sum(oranlar_ratio[i] * av[i] for i in range(g)) / g
     return {
         "avantajlar": av,
         "grpo_hedefi": hedef,
         "grpo_kaybi": -hedef,
         "kirpilan_orani": 0.0,
     }

print(grpo_hedef_hesapla([1.0, 0.0, 0.0, 1.0], [1.3, 0.9, 1.0, 1.1], [0.05, 0.02, 0.01, 0.04], eps_clip=0.2, beta_kl=0.04))
```
```test
def sinama_grpo(f):
    import copy, math, random
    def _ref(od, ra, kl, eps, bkl):
        g = len(od)
        mu = sum(float(x) for x in od) / g
        std = math.sqrt(sum((float(x) - mu) ** 2 for x in od) / g)
        if std < 1e-12:
            av = [0.0] * g
        else:
            av = [(float(x) - mu) / (std + 1e-8) for x in od]
        j_list = []
        kirp = 0
        for i in range(g):
            r_i = float(ra[i])
            if abs(r_i - 1.0) > float(eps):
                kirp += 1
            c_i = min(max(r_i, 1.0 - float(eps)), 1.0 + float(eps))
            s_i = min(r_i * av[i], c_i * av[i])
            j_list.append(s_i - float(bkl) * float(kl[i]))
        hedef = sum(j_list) / g
        return {
            "avantajlar": av,
            "grpo_hedefi": hedef,
            "grpo_kaybi": -hedef,
            "kirpilan_orani": float(kirp) / g,
        }
    def _yakin(a, b):
        keys = {"avantajlar", "grpo_hedefi", "grpo_kaybi", "kirpilan_orani"}
        if not isinstance(a, dict) or set(a.keys()) != keys:
            return False
        if not isinstance(a["avantajlar"], list) or len(a["avantajlar"]) != len(b["avantajlar"]):
            return False
        for u, v in zip(a["avantajlar"], b["avantajlar"]):
            if abs(u - v) > 1e-9:
                return False
        for k in ("grpo_hedefi", "grpo_kaybi", "kirpilan_orani"):
            if isinstance(a[k], bool) or not isinstance(a[k], float) or abs(a[k] - b[k]) > 1e-10:
                return False
        return True
    try:
        od = [1.0, 0.0, 0.0, 1.0]
        ra = [1.3, 0.9, 1.0, 1.1]
        kl = [0.05, 0.02, 0.01, 0.04]
        old = (list(od), list(ra), list(kl))
        out = f(od, ra, kl, 0.2, 0.04)
        if (od, ra, kl) != old or not _yakin(out, _ref(od, ra, kl, 0.2, 0.04)):
            return False
        # 1.3 > 1.2 olduğu için 4 örnekten 1'i kırpıldı -> 0.25
        if abs(out["kirpilan_orani"] - 0.25) > 1e-12:
            return False

        # Tüm ödüller eşit olduğunda (std == 0) avantajlar 0.0 olmalı!
        out_esit = f([1.0, 1.0, 1.0], [1.5, 0.6, 1.0], [0.1, 0.1, 0.1], 0.2, 0.05)
        if not _yakin(out_esit, _ref([1.0, 1.0, 1.0], [1.5, 0.6, 1.0], [0.1, 0.1, 0.1], 0.2, 0.05)):
            return False
        if any(abs(a) > 1e-12 for a in out_esit["avantajlar"]):
            return False

        # std=1e-12 sınırının altı, eşiti ve üstü farklı dallardır.
        for olcek in (0.5e-12, 1e-12, 1.5e-12, 2e-12):
            od_sinir = [-olcek, olcek]
            if not _yakin(f(od_sinir, [1.0, 1.0], [0.0, 0.0], 0.25, 0.0), _ref(od_sinir, [1.0, 1.0], [0.0, 0.0], 0.25, 0.0)): return False
        rng = random.Random(1101)
        for _ in range(25):
            g = rng.randint(2, 10)
            oo = [rng.uniform(0.0, 2.0) for _ in range(g)]
            rr = [rng.uniform(0.5, 1.6) for _ in range(g)]
            kk = [rng.uniform(0.0, 0.3) for _ in range(g)]
            ep = rng.uniform(0.1, 0.3)
            bk = rng.uniform(0.0, 0.1)
            if not _yakin(f(oo, rr, kk, ep, bk), _ref(oo, rr, kk, ep, bk)):
                return False

        bad_cases = [
            ([1.0], [1.0], [0.1], 0.2, 0.04),  # G < 2
            ([1.0, 0.0], [1.0], [0.1, 0.1], 0.2, 0.04),
            ([1.0, 0.0], [0.0, 1.0], [0.1, 0.1], 0.2, 0.04),  # ratio <= 0
            ([1.0, 0.0], [1.0, 1.0], [-0.1, 0.1], 0.2, 0.04),  # kl < 0
            ([1.0, 0.0], [1.0, 1.0], [0.1, 0.1], 0.0, 0.04),  # eps_clip <= 0
            ([1.0, 0.0], [1.0, 1.0], [0.1, 0.1], 0.2, -0.01),  # beta_kl < 0
            ([True, 0.0], [1.0, 1.0], [0.1, 0.1], 0.2, 0.04),
            ([1.0, float("nan")], [1.0, 1.0], [0.1, 0.1], 0.2, 0.04),
        ]
        for bo, br, bk, bep, bkl in bad_cases:
            try:
                f(bo, br, bk, bep, bkl)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

grpo_hedef_hesapla = need("grpo_hedef_hesapla")
ok(sinama_grpo(grpo_hedef_hesapla), "GRPO grup avantaj normalizasyonu, PPO-clipping ve KL cezası")
for ad, mut in [
    ("clipping yapmayan", lambda o, r, k, e, b: grpo_hedef_hesapla(o, r, k, 100.0, b)),
    ("KL cezasını ekleyen (+beta*kl)", lambda o, r, k, e, b: dict(grpo_hedef_hesapla(o, r, k, e, b), grpo_hedefi=grpo_hedef_hesapla(o, r, [0.0]*len(k), e, b)["grpo_hedefi"])),
    ("kaybın işaretini ters bırakan", lambda o, r, k, e, b: dict(grpo_hedef_hesapla(o, r, k, e, b), grpo_kaybi=grpo_hedef_hesapla(o, r, k, e, b)["grpo_hedefi"])),
]:
    ok(not sinama_grpo(mut), "mutant reddedildi: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef grpo_hedef_hesapla(oduller, oranlar_ratio, kl_degerleri, eps_clip, beta_kl):\n    if not isinstance(oduller, list) or len(oduller) < 2:\n        raise ValueError('oduller en az 2 elemanlı liste olmalı')\n    g = len(oduller)\n    if not isinstance(oranlar_ratio, list) or len(oranlar_ratio) != g:\n        raise ValueError('oranlar_ratio uzunluğu uyuşmuyor')\n    if not isinstance(kl_degerleri, list) or len(kl_degerleri) != g:\n        raise ValueError('kl_degerleri uzunluğu uyuşmuyor')\n    if not _sayi_mi(eps_clip) or eps_clip <= 0.0:\n        raise ValueError('eps_clip > 0 olmalı')\n    if not _sayi_mi(beta_kl) or beta_kl < 0.0:\n        raise ValueError('beta_kl >= 0 olmalı')\n    for i in range(g):\n        if not _sayi_mi(oduller[i]) or not _sayi_mi(oranlar_ratio[i]) or (not _sayi_mi(kl_degerleri[i])):\n            raise ValueError('geçersiz liste elemanı')\n        if oranlar_ratio[i] <= 0.0 or kl_degerleri[i] < 0.0:\n            raise ValueError('oran > 0 ve kl >= 0 olmalı')\n    mu = sum((float(x) for x in oduller)) / g\n    std = math.sqrt(sum(((float(x) - mu) ** 2 for x in oduller)) / g)\n    if std < 1e-12:\n        avantajlar = [0.0] * g\n    else:\n        avantajlar = [(float(x) - mu) / (std + 1e-08) for x in oduller]\n    eps = float(eps_clip)\n    bkl = float(beta_kl)\n    hedefler = []\n    kirpilan = 0\n    for i in range(g):\n        rho = float(oranlar_ratio[i])\n        if abs(rho - 1.0) > eps:\n            kirpilan += 1\n        rho_clip = min(max(rho, 1.0 - eps), 1.0 + eps)\n        surr = min(rho * avantajlar[i], rho_clip * avantajlar[i])\n        hedefler.append(surr - bkl * float(kl_degerleri[i]))\n    grpo_hedef = sum(hedefler) / g\n    return {'avantajlar': avantajlar, 'grpo_hedefi': grpo_hedef, 'grpo_kaybi': -grpo_hedef, 'kirpilan_orani': float(kirpilan) / g}", 'referans', 'exec'), _REF)
_t, _g = _ff(grpo_hedef_hesapla, _REF['grpo_hedef_hesapla'], ([1.0, 0.0, 0.0, 1.0], [1.3, 0.9, 1.0, 1.1], [0.05, 0.02, 0.01, 0.04], 0.2, 0.04), tohum=2924, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (grpo_hedef_hesapla): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math

def _sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def grpo_hedef_hesapla(oduller, oranlar_ratio, kl_degerleri, eps_clip, beta_kl):
    if not isinstance(oduller, list) or len(oduller) < 2:
        raise ValueError("oduller en az 2 elemanlı liste olmalı")
    g = len(oduller)
    if not isinstance(oranlar_ratio, list) or len(oranlar_ratio) != g:
        raise ValueError("oranlar_ratio uzunluğu uyuşmuyor")
    if not isinstance(kl_degerleri, list) or len(kl_degerleri) != g:
        raise ValueError("kl_degerleri uzunluğu uyuşmuyor")
    if not _sayi_mi(eps_clip) or eps_clip <= 0.0:
        raise ValueError("eps_clip > 0 olmalı")
    if not _sayi_mi(beta_kl) or beta_kl < 0.0:
        raise ValueError("beta_kl >= 0 olmalı")

    for i in range(g):
        if not _sayi_mi(oduller[i]) or not _sayi_mi(oranlar_ratio[i]) or not _sayi_mi(kl_degerleri[i]):
            raise ValueError("geçersiz liste elemanı")
        if oranlar_ratio[i] <= 0.0 or kl_degerleri[i] < 0.0:
            raise ValueError("oran > 0 ve kl >= 0 olmalı")

    mu = sum(float(x) for x in oduller) / g
    std = math.sqrt(sum((float(x) - mu) ** 2 for x in oduller) / g)
    if std < 1e-12:
        avantajlar = [0.0] * g
    else:
        avantajlar = [(float(x) - mu) / (std + 1e-8) for x in oduller]

    eps = float(eps_clip)
    bkl = float(beta_kl)
    hedefler = []
    kirpilan = 0

    for i in range(g):
        rho = float(oranlar_ratio[i])
        if abs(rho - 1.0) > eps:
            kirpilan += 1
        rho_clip = min(max(rho, 1.0 - eps), 1.0 + eps)
        surr = min(rho * avantajlar[i], rho_clip * avantajlar[i])
        hedefler.append(surr - bkl * float(kl_degerleri[i]))

    grpo_hedef = sum(hedefler) / g
    return {
        "avantajlar": avantajlar,
        "grpo_hedefi": grpo_hedef,
        "grpo_kaybi": -grpo_hedef,
        "kirpilan_orani": float(kirpilan) / g,
    }

if __name__ == "__main__":
    print(grpo_hedef_hesapla([1.0, 0.0, 0.0, 1.0], [1.3, 0.9, 1.0, 1.1], [0.05, 0.02, 0.01, 0.04], eps_clip=0.2, beta_kl=0.04))
```
```hint
Önce `mu` ve anakütle `std` hesapla (`std < 1e-12` ise avantajların tamamı `0.0`, değilse `(r - mu) / (std + 1e-8)`). Sonra `min(rho * A_i, clip(rho, 1-eps, 1+eps) * A_i) - beta_kl * kl_i` ortalamasını bul.
```
:::

::: gorev 2 · Process Reward Model (PRM) ile Adım Adım Düşünce Ağacı Seçimi
Çıkarım anında (`Test-Time Compute`) üretilen $N$ adet aday düşünce zinciri (`Chain-of-Thought`) arasından **`Process Reward Model (PRM)`** adım puanlarını birleştirerek en güvenilir düşünce yolunu seçen `prm_en_iyi_zincir(dusunce_zincirleri, birlestirme_modu)` işlevini yaz.

**Girdi Kuralları ve Doğrulama:**
- `dusunce_zincirleri`: Boş olmayan bir `list`. Her elemanı `{"cevap": str, "adim_puanlari": list}` biçiminde bir `dict` olmalıdır:
  - `"cevap"`: Boş olmayan (`strip()` sonrası en az 1 karakter içeren) `str`.
  - `"adim_puanlari"`: Boş olmayan (`len >= 1`) bir `list`; her elemanı $[0.0, 1.0]$ aralığında `bool` olmayan sonlu sayı (`0.0 <= p <= 1.0`).
- `birlestirme_modu`: Yalnızca `"min"`, `"prod"` veya `"mean"` değerlerinden biri olabilir (`str`).

**Hesaplama Kuralları:**
1. Her düşünce zinciri $i \in \{0, \dots, N-1\}$ için `birlestirme_modu` kuralına göre birleşik PRM skorunu hesapla:
   - `"min"`: $\min_{k} p_{i, k}$ (En zayıf halka skoru)
   - `"prod"`: $\prod_{k} p_{i, k}$ (Adım olasılıklarının çarpımı)
   - `"mean"`: $\frac{1}{K_i} \sum_{k} p_{i, k}$ (Adım puanlarının aritmetik ortalaması)
2. `zincir_skorlari`: Her zincirin hesaplanan PRM skorunu sırasıyla tutan `float` listesi.
3. `secilen_indis`: En yüksek PRM skoruna sahip zincirin indisi (eşitlik durumunda daha küçük indis seçilir).
4. `secilen_cevap`: Seçilen zincirin `"cevap"` alanı (`str`).
5. `en_zayif_adim_skoru`: Seçilen (kazanan) zincirin kendi içindeki en düşük adım puanı ($\min_k p_{\text{secilen}, k}$, `float`).
6. İşlev şu sözlüğü döndürmelidir:
   `{"zincir_skorlari": [...], "secilen_indis": int, "secilen_cevap": str, "en_zayif_adim_skoru": float}`
- Geçersiz herhangi bir girdide `ValueError` yükseltilmelidir.

```starter
import math

# KUSURLU BAŞLANGIÇ KODU: birlestirme_modu parametresini yok sayıp her zaman ilk zinciri seçiyor!
def prm_en_iyi_zincir(dusunce_zincirleri, birlestirme_modu):
     skorlar = [sum(z["adim_puanlari"]) / len(z["adim_puanlari"]) for z in dusunce_zincirleri]
     return {
         "zincir_skorlari": skorlar,
         "secilen_indis": 0,
         "secilen_cevap": dusunce_zincirleri[0]["cevap"],
         "en_zayif_adim_skoru": min(dusunce_zincirleri[0]["adim_puanlari"]),
     }

adaylar = [
    {"cevap": "42", "adim_puanlari": [0.95, 0.90, 0.15, 0.92]},
    {"cevap": "24", "adim_puanlari": [0.85, 0.82, 0.80, 0.88]},
]
print(prm_en_iyi_zincir(adaylar, "min"))
```
```test
def sinama_prm(f):
    import copy, math, random
    def _skor(puanlar, mod):
        if mod == "min":
            return min(float(x) for x in puanlar)
        if mod == "prod":
            p = 1.0
            for x in puanlar:
                p *= float(x)
            return p
        return sum(float(x) for x in puanlar) / len(puanlar)
    def _ref(zincirler, mod):
        sk = [_skor(z["adim_puanlari"], mod) for z in zincirler]
        sec = max(range(len(zincirler)), key=lambda i: (sk[i], -i))
        return {
            "zincir_skorlari": sk,
            "secilen_indis": sec,
            "secilen_cevap": zincirler[sec]["cevap"],
            "en_zayif_adim_skoru": min(float(x) for x in zincirler[sec]["adim_puanlari"]),
        }
    def _yakin(a, b):
        keys = {"zincir_skorlari", "secilen_indis", "secilen_cevap", "en_zayif_adim_skoru"}
        if not isinstance(a, dict) or set(a.keys()) != keys:
            return False
        if type(a["secilen_indis"]) is not int or a["secilen_indis"] != b["secilen_indis"]:
            return False
        if a["secilen_cevap"] != b["secilen_cevap"] or abs(a["en_zayif_adim_skoru"] - b["en_zayif_adim_skoru"]) > 1e-11:
            return False
        if not isinstance(a["zincir_skorlari"], list) or len(a["zincir_skorlari"]) != len(b["zincir_skorlari"]):
            return False
        return all(abs(u - v) < 1e-11 for u, v in zip(a["zincir_skorlari"], b["zincir_skorlari"]))
    try:
        z1 = [
            {"cevap": "42", "adim_puanlari": [0.95, 0.90, 0.15, 0.92]},
            {"cevap": "24", "adim_puanlari": [0.85, 0.82, 0.80, 0.88]},
        ]
        old = copy.deepcopy(z1)
        r_min = f(z1, "min")
        if z1 != old or not _yakin(r_min, _ref(z1, "min")) or r_min["secilen_indis"] != 1 or r_min["secilen_cevap"] != "24":
            return False
        r_prod = f(z1, "prod")
        if not _yakin(r_prod, _ref(z1, "prod")) or r_prod["secilen_indis"] != 1:
            return False

        # Eşitlikte küçük indis kuralı
        z_esit = [
            {"cevap": "A", "adim_puanlari": [0.8, 0.7]},
            {"cevap": "B", "adim_puanlari": [0.7, 0.9]},
        ]
        if f(z_esit, "min")["secilen_indis"] != 0:
            return False

        # [0,1] uçları geçerlidir; tek zincir ve prod=0 da kabul edilir.
        z_uc = [{"cevap": "uç", "adim_puanlari": [0.0, 1.0]}]
        for mod in ("min", "prod", "mean"):
            if not _yakin(f(z_uc, mod), _ref(z_uc, mod)): return False
        for mod in ("min", "prod", "mean"):
            for puanlar in ([], ["0.5"]):
                try:
                    f([{"cevap": "ok", "adim_puanlari": puanlar}], mod)
                    return False
                except ValueError:
                    pass
        rng = random.Random(1102)
        for mod in ("min", "prod", "mean"):
            for _ in range(15):
                n = rng.randint(2, 6)
                zz = [
                    {"cevap": f"yanit_{i}", "adim_puanlari": [rng.uniform(0.05, 0.99) for _ in range(rng.randint(1, 6))]}
                    for i in range(n)
                ]
                if not _yakin(f(zz, mod), _ref(zz, mod)):
                    return False

        bad_cases = [
            ([], "min"),
            (z1, "sum"),
            (z1, ""),
            ([{"cevap": "  ", "adim_puanlari": [0.5]}], "min"),
            ([{"cevap": "ok", "adim_puanlari": []}], "min"),
            ([{"cevap": "ok", "adim_puanlari": [1.2]}], "min"),
            ([{"cevap": "ok", "adim_puanlari": [-0.1]}], "min"),
            ([{"cevap": "ok", "adim_puanlari": [True]}], "min"),
            ([{"adim_puanlari": [0.5]}], "min"),
        ]
        for bz, bm in bad_cases:
            try:
                f(bz, bm)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

prm_en_iyi_zincir = need("prm_en_iyi_zincir")
ok(sinama_prm(prm_en_iyi_zincir), "PRM adım birleştirme (min/prod/mean), en iyi zincir seçimi ve girdi doğrulaması")
for ad, mut in [
    ("hep mean kullanan", lambda z, m: prm_en_iyi_zincir(z, "mean")),
    ("hep min kullanan", lambda z, m: prm_en_iyi_zincir(z, "min")),
    ("eşitlikte büyük indis seçen", lambda z, m: dict(prm_en_iyi_zincir(z, m), secilen_indis=len(z)-1 if len(set(prm_en_iyi_zincir(z, m)["zincir_skorlari"])) == 1 else prm_en_iyi_zincir(z, m)["secilen_indis"])),
]:
    ok(not sinama_prm(mut), "mutant reddedildi: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef prm_en_iyi_zincir(dusunce_zincirleri, birlestirme_modu):\n    if not isinstance(dusunce_zincirleri, list) or not dusunce_zincirleri:\n        raise ValueError('boş olmayan zincir listesi gerekli')\n    if birlestirme_modu not in ('min', 'prod', 'mean'):\n        raise ValueError('geçersiz birlestirme_modu')\n    skorlar = []\n    for z in dusunce_zincirleri:\n        if not isinstance(z, dict) or 'cevap' not in z or 'adim_puanlari' not in z:\n            raise ValueError('geçersiz zincir sözlüğü')\n        cevap = z['cevap']\n        puanlar = z['adim_puanlari']\n        if not isinstance(cevap, str) or not cevap.strip():\n            raise ValueError('geçersiz cevap')\n        if not isinstance(puanlar, list) or not puanlar:\n            raise ValueError('boş adım puanları')\n        temiz_puanlar = []\n        for p in puanlar:\n            if isinstance(p, bool) or not isinstance(p, (int, float)) or (not math.isfinite(p)) or (not 0.0 <= p <= 1.0):\n                raise ValueError('adım puanı [0, 1] aralığında sayı olmalı')\n            temiz_puanlar.append(float(p))\n        if birlestirme_modu == 'min':\n            skor = min(temiz_puanlar)\n        elif birlestirme_modu == 'prod':\n            skor = 1.0\n            for val in temiz_puanlar:\n                skor *= val\n        else:\n            skor = sum(temiz_puanlar) / len(temiz_puanlar)\n        skorlar.append(skor)\n    secilen = max(range(len(dusunce_zincirleri)), key=lambda i: (skorlar[i], -i))\n    en_zayif = min((float(x) for x in dusunce_zincirleri[secilen]['adim_puanlari']))\n    return {'zincir_skorlari': skorlar, 'secilen_indis': secilen, 'secilen_cevap': dusunce_zincirleri[secilen]['cevap'], 'en_zayif_adim_skoru': en_zayif}", 'referans', 'exec'), _REF)
_t, _g = _ff(prm_en_iyi_zincir, _REF['prm_en_iyi_zincir'], ([{'cevap': '42', 'adim_puanlari': [0.95, 0.9, 0.15, 0.92]}, {'cevap': '24', 'adim_puanlari': [0.85, 0.82, 0.8, 0.88]}], 'min'), tohum=2869, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (prm_en_iyi_zincir): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math

def prm_en_iyi_zincir(dusunce_zincirleri, birlestirme_modu):
    if not isinstance(dusunce_zincirleri, list) or not dusunce_zincirleri:
        raise ValueError("boş olmayan zincir listesi gerekli")
    if birlestirme_modu not in ("min", "prod", "mean"):
        raise ValueError("geçersiz birlestirme_modu")

    skorlar = []
    for z in dusunce_zincirleri:
        if not isinstance(z, dict) or "cevap" not in z or "adim_puanlari" not in z:
            raise ValueError("geçersiz zincir sözlüğü")
        cevap = z["cevap"]
        puanlar = z["adim_puanlari"]
        if not isinstance(cevap, str) or not cevap.strip():
            raise ValueError("geçersiz cevap")
        if not isinstance(puanlar, list) or not puanlar:
            raise ValueError("boş adım puanları")
        temiz_puanlar = []
        for p in puanlar:
            if isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p) or not (0.0 <= p <= 1.0):
                raise ValueError("adım puanı [0, 1] aralığında sayı olmalı")
            temiz_puanlar.append(float(p))

        if birlestirme_modu == "min":
            skor = min(temiz_puanlar)
        elif birlestirme_modu == "prod":
            skor = 1.0
            for val in temiz_puanlar:
                skor *= val
        else:
            skor = sum(temiz_puanlar) / len(temiz_puanlar)
        skorlar.append(skor)

    secilen = max(range(len(dusunce_zincirleri)), key=lambda i: (skorlar[i], -i))
    en_zayif = min(float(x) for x in dusunce_zincirleri[secilen]["adim_puanlari"])

    return {
        "zincir_skorlari": skorlar,
        "secilen_indis": secilen,
        "secilen_cevap": dusunce_zincirleri[secilen]["cevap"],
        "en_zayif_adim_skoru": en_zayif,
    }

if __name__ == "__main__":
    adaylar = [
        {"cevap": "42", "adim_puanlari": [0.95, 0.90, 0.15, 0.92]},
        {"cevap": "24", "adim_puanlari": [0.85, 0.82, 0.80, 0.88]},
    ]
    print(prm_en_iyi_zincir(adaylar, "min"))
```
```hint
Her zincirin `adim_puanlari` listesini doğrula (`0.0 <= p <= 1.0`). Moda göre `min`, çarpım veya ortalama hesapla; `max(range(len(skorlar)), key=lambda i: (skorlar[i], -i))` ile en yüksek skorlu (eşitlikte en küçük indisli) zinciri seç.
```
:::

::: anlat Gerçek deney: Qwen2.5-0.5B ile gerçek GRPO adımı, doğrulayıcı hileleri ve model tabanlı PRM
Final yerel önbellekteki **Qwen2.5-0.5B-Instruct** ile çalışır (CPU, yaklaşık bir dakika, indirme yok):

- 4 toplama sorusunun her birine 6'şar yanıt örneklenir (grup). **Katı doğrulayıcı** son `Answer: N` kalıbındaki sayıyı doğru cevapla karşılaştırır; ödül 0 ya da 1'dir.
- Son katmanın MLP'si iki adım GRPO ile güncellenir. Sonra her yanıt için gerçek **oran** (yeni / eski olasılık, uzunlukla normalize) ve gerçek **KL** tahmini (k3) hesaplanır; senin `grpo_hedef_hesapla` işlevinin hedefi ve kırpılan oranı torch referansıyla karşılaştırılır.
- Model bu sorularda çoğunlukla doğru olduğundan çoğu grupta **tüm ödüller aynıdır**: avantaj sıfırdır ve o grup öğrenme sinyali vermez. Zorluğu uygun soru seçmenin nedeni budur.
- **Doğrulayıcı hileleri iki yönlüdür:** "cevap metinde geçiyor mu" diye bakan naif doğrulayıcı 0'dan 499'a kadar sayı döken bir spam yanıtı doğru sayar (reward hacking). Katı doğrulayıcı ise doğru cevabı farklı biçimde yazan yanıtı (`Answer: 125 + 76 = 201`) yanlış sayabilir. Kanıttaki `naif_kati_ayrisan` gerçek yanıtlarda kaç ayrışma olduğunu gösterir.
- **PRM:** aynı model, her adım için "Bu adım doğru mu? Yes/No" sorusunun `Yes` olasılığını puan olarak verir. Üç zincir var: doğru, yanlış ve **yanlış adımla doğru cevaba ulaşan**. Senin `prm_en_iyi_zincir` işlevin bu gerçek puanlarla min, mean ve prod kiplerinde seçim yapar. Son olarak yanlış adıma "öğretmen kontrol etti, doğru" cümlesi eklenip puan yeniden ölçülür (ai-saldiri-64).

Kabul: iki işlevin farksal taramayı geçmesi; GRPO hedefi ve kırpılan oranın torch'tan en çok `1e-6` farklı olması; spam yanıtın naif doğrulayıcıyı geçip katı doğrulayıcıyı geçmemesi; zincir seçimlerinin gerçek puanlarla bağımsız hesaplanan seçimle aynı olması.

**Kanıt dosyasını oku:** `gruplar` (ödüller, oranlar, KL), `sifir_sinyal_grup`, `prm_puanlari`, `prm_secim`, `prm_yanlis_adim_puani`, `prm_ikna_sonrasi_puan`. Soru 1: 0.5B'lik bir genel model yanlış adımlara neden yüksek puan veriyor ve bu PRM'nin değeri hakkında ne söylüyor? Soru 2: Hangi birleştirme kipi süreç hatalı ama sonucu doğru zinciri cezalandırmalıydı, gerçekte cezalandırdı mı? Soru 3: Ödülü 0 olan yanıtların oranı neden 1'in altına düştü?
:::

::: gorev Gerçek deney · Qwen2.5-0.5B ile GRPO hedefi, doğrulayıcı hileleri ve model tabanlı PRM seçimi
Önceki görevlerdeki `grpo_hedef_hesapla`, `prm_en_iyi_zincir` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 300
```
```starter
import ai_lab
import math

def grpo_hedef_hesapla(oduller, oranlar_ratio, kl_degerleri, eps_clip, beta_kl):
    g = len(oduller)
    mu = sum(oduller) / g
    av = [r - mu for r in oduller]
    hedef = sum((oranlar_ratio[i] * av[i] for i in range(g))) / g
    return {'avantajlar': av, 'grpo_hedefi': hedef, 'grpo_kaybi': -hedef, 'kirpilan_orani': 0.0}

import math

def prm_en_iyi_zincir(dusunce_zincirleri, birlestirme_modu):
    skorlar = [sum(z['adim_puanlari']) / len(z['adim_puanlari']) for z in dusunce_zincirleri]
    return {'zincir_skorlari': skorlar, 'secilen_indis': 0, 'secilen_cevap': dusunce_zincirleri[0]['cevap'], 'en_zayif_adim_skoru': min(dusunce_zincirleri[0]['adim_puanlari'])}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_11 as D
    D.goster(grpo_hedef_hesapla, prm_en_iyi_zincir)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_grpo_ref', '_yes_no', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
grpo_hedef_hesapla = need("grpo_hedef_hesapla")
prm_en_iyi_zincir = need("prm_en_iyi_zincir")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef grpo_hedef_hesapla(oduller, oranlar_ratio, kl_degerleri, eps_clip, beta_kl):\n    if not isinstance(oduller, list) or len(oduller) < 2:\n        raise ValueError('oduller en az 2 elemanlı liste olmalı')\n    g = len(oduller)\n    if not isinstance(oranlar_ratio, list) or len(oranlar_ratio) != g:\n        raise ValueError('oranlar_ratio uzunluğu uyuşmuyor')\n    if not isinstance(kl_degerleri, list) or len(kl_degerleri) != g:\n        raise ValueError('kl_degerleri uzunluğu uyuşmuyor')\n    if not _sayi_mi(eps_clip) or eps_clip <= 0.0:\n        raise ValueError('eps_clip > 0 olmalı')\n    if not _sayi_mi(beta_kl) or beta_kl < 0.0:\n        raise ValueError('beta_kl >= 0 olmalı')\n    for i in range(g):\n        if not _sayi_mi(oduller[i]) or not _sayi_mi(oranlar_ratio[i]) or (not _sayi_mi(kl_degerleri[i])):\n            raise ValueError('geçersiz liste elemanı')\n        if oranlar_ratio[i] <= 0.0 or kl_degerleri[i] < 0.0:\n            raise ValueError('oran > 0 ve kl >= 0 olmalı')\n    mu = sum((float(x) for x in oduller)) / g\n    std = math.sqrt(sum(((float(x) - mu) ** 2 for x in oduller)) / g)\n    if std < 1e-12:\n        avantajlar = [0.0] * g\n    else:\n        avantajlar = [(float(x) - mu) / (std + 1e-08) for x in oduller]\n    eps = float(eps_clip)\n    bkl = float(beta_kl)\n    hedefler = []\n    kirpilan = 0\n    for i in range(g):\n        rho = float(oranlar_ratio[i])\n        if abs(rho - 1.0) > eps:\n            kirpilan += 1\n        rho_clip = min(max(rho, 1.0 - eps), 1.0 + eps)\n        surr = min(rho * avantajlar[i], rho_clip * avantajlar[i])\n        hedefler.append(surr - bkl * float(kl_degerleri[i]))\n    grpo_hedef = sum(hedefler) / g\n    return {'avantajlar': avantajlar, 'grpo_hedefi': grpo_hedef, 'grpo_kaybi': -grpo_hedef, 'kirpilan_orani': float(kirpilan) / g}\n\nimport math\n\ndef prm_en_iyi_zincir(dusunce_zincirleri, birlestirme_modu):\n    if not isinstance(dusunce_zincirleri, list) or not dusunce_zincirleri:\n        raise ValueError('boş olmayan zincir listesi gerekli')\n    if birlestirme_modu not in ('min', 'prod', 'mean'):\n        raise ValueError('geçersiz birlestirme_modu')\n    skorlar = []\n    for z in dusunce_zincirleri:\n        if not isinstance(z, dict) or 'cevap' not in z or 'adim_puanlari' not in z:\n            raise ValueError('geçersiz zincir sözlüğü')\n        cevap = z['cevap']\n        puanlar = z['adim_puanlari']\n        if not isinstance(cevap, str) or not cevap.strip():\n            raise ValueError('geçersiz cevap')\n        if not isinstance(puanlar, list) or not puanlar:\n            raise ValueError('boş adım puanları')\n        temiz_puanlar = []\n        for p in puanlar:\n            if isinstance(p, bool) or not isinstance(p, (int, float)) or (not math.isfinite(p)) or (not 0.0 <= p <= 1.0):\n                raise ValueError('adım puanı [0, 1] aralığında sayı olmalı')\n            temiz_puanlar.append(float(p))\n        if birlestirme_modu == 'min':\n            skor = min(temiz_puanlar)\n        elif birlestirme_modu == 'prod':\n            skor = 1.0\n            for val in temiz_puanlar:\n                skor *= val\n        else:\n            skor = sum(temiz_puanlar) / len(temiz_puanlar)\n        skorlar.append(skor)\n    secilen = max(range(len(dusunce_zincirleri)), key=lambda i: (skorlar[i], -i))\n    en_zayif = min((float(x) for x in dusunce_zincirleri[secilen]['adim_puanlari']))\n    return {'zincir_skorlari': skorlar, 'secilen_indis': secilen, 'secilen_cevap': dusunce_zincirleri[secilen]['cevap'], 'en_zayif_adim_skoru': en_zayif}", 'referans', 'exec'), _REF)
_t, _g = _ff(grpo_hedef_hesapla, _REF['grpo_hedef_hesapla'], ([1.0, 0.0, 0.0, 1.0], [1.3, 0.9, 1.0, 1.1], [0.05, 0.02, 0.01, 0.04], 0.2, 0.04), tohum=2924, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (grpo_hedef_hesapla): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(prm_en_iyi_zincir, _REF['prm_en_iyi_zincir'], ([{'cevap': '42', 'adim_puanlari': [0.95, 0.9, 0.15, 0.92]}, {'cevap': '24', 'adim_puanlari': [0.85, 0.82, 0.8, 0.88]}], 'min'), tohum=2869, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (prm_en_iyi_zincir): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
def _birim_11():
    for _olcek in (0.0, 0.5e-12, 1e-12, 1.5e-12, 2e-12):
        _od = [1.0, 1.0] if _olcek == 0.0 else [-_olcek, _olcek]
        if grpo_hedef_hesapla(_od, [1.5, 0.6], [0.1, 0.1], 0.2, 0.05) != _REF['grpo_hedef_hesapla'](_od, [1.5, 0.6], [0.1, 0.1], 0.2, 0.05):
            return False
    for _bo in ([1.0], []):
        try:
            grpo_hedef_hesapla(_bo, [1.0] * len(_bo), [0.1] * len(_bo), 0.2, 0.04)
            return False
        except ValueError:
            pass
    _z = [{"cevap": "42", "adim_puanlari": [0.95, 0.9, 0.15, 0.92]}, {"cevap": "24", "adim_puanlari": [0.85, 0.82, 0.8, 0.88]}]
    _zuc = [{"cevap": "uc", "adim_puanlari": [0.0, 1.0]}]
    for _mod in ("min", "prod", "mean"):
        if prm_en_iyi_zincir(_z, _mod) != _REF['prm_en_iyi_zincir'](_z, _mod):
            return False
        if prm_en_iyi_zincir(_zuc, _mod) != _REF['prm_en_iyi_zincir'](_zuc, _mod):
            return False
    for _bz, _bm in (([], "min"), ([{"cevap": "ok", "adim_puanlari": [1.0]}, {"cevap": "bos", "adim_puanlari": []}], "prod"), ([{"cevap": "ok", "adim_puanlari": [True]}], "min"), ([{"cevap": "ok", "adim_puanlari": ["0.5"]}], "min"), ([{"cevap": "ok", "adim_puanlari": [-0.1]}], "min"), ([{"cevap": "ok", "adim_puanlari": [1.1]}], "min")):
        try:
            prm_en_iyi_zincir(_bz, _bm)
            return False
        except ValueError:
            pass
    return True
kontrol(_birim_11(), "GRPO std sınırı ve PRM birleştirme/doğrulama sözleşmesi")
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_11 as D
try: r = D.deney(grpo_hedef_hesapla, prm_en_iyi_zincir)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['grpo_ayni'], 'GRPO hedefi ve kırpılan oran gerçek oran/KL değerlerinde torch referansıyla aynı')
kontrol(r['spam_naif'] == 1 and r['spam_kati'] == 0, 'naif doğrulayıcı spam yanıtı kabul ediyor, katı doğrulayıcı reddediyor')
kontrol(r['prm_secim_dogru'], 'zincir seçimi gerçek PRM puanlarıyla min/mean/prod kiplerinde doğru')
ai_lab.kanit_yaz("ai-uretim-11-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-11", "deney": r})
```
```solution
import ai_lab
import math

def _sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def grpo_hedef_hesapla(oduller, oranlar_ratio, kl_degerleri, eps_clip, beta_kl):
    if not isinstance(oduller, list) or len(oduller) < 2:
        raise ValueError('oduller en az 2 elemanlı liste olmalı')
    g = len(oduller)
    if not isinstance(oranlar_ratio, list) or len(oranlar_ratio) != g:
        raise ValueError('oranlar_ratio uzunluğu uyuşmuyor')
    if not isinstance(kl_degerleri, list) or len(kl_degerleri) != g:
        raise ValueError('kl_degerleri uzunluğu uyuşmuyor')
    if not _sayi_mi(eps_clip) or eps_clip <= 0.0:
        raise ValueError('eps_clip > 0 olmalı')
    if not _sayi_mi(beta_kl) or beta_kl < 0.0:
        raise ValueError('beta_kl >= 0 olmalı')
    for i in range(g):
        if not _sayi_mi(oduller[i]) or not _sayi_mi(oranlar_ratio[i]) or (not _sayi_mi(kl_degerleri[i])):
            raise ValueError('geçersiz liste elemanı')
        if oranlar_ratio[i] <= 0.0 or kl_degerleri[i] < 0.0:
            raise ValueError('oran > 0 ve kl >= 0 olmalı')
    mu = sum((float(x) for x in oduller)) / g
    std = math.sqrt(sum(((float(x) - mu) ** 2 for x in oduller)) / g)
    if std < 1e-12:
        avantajlar = [0.0] * g
    else:
        avantajlar = [(float(x) - mu) / (std + 1e-08) for x in oduller]
    eps = float(eps_clip)
    bkl = float(beta_kl)
    hedefler = []
    kirpilan = 0
    for i in range(g):
        rho = float(oranlar_ratio[i])
        if abs(rho - 1.0) > eps:
            kirpilan += 1
        rho_clip = min(max(rho, 1.0 - eps), 1.0 + eps)
        surr = min(rho * avantajlar[i], rho_clip * avantajlar[i])
        hedefler.append(surr - bkl * float(kl_degerleri[i]))
    grpo_hedef = sum(hedefler) / g
    return {'avantajlar': avantajlar, 'grpo_hedefi': grpo_hedef, 'grpo_kaybi': -grpo_hedef, 'kirpilan_orani': float(kirpilan) / g}

import math

def prm_en_iyi_zincir(dusunce_zincirleri, birlestirme_modu):
    if not isinstance(dusunce_zincirleri, list) or not dusunce_zincirleri:
        raise ValueError('boş olmayan zincir listesi gerekli')
    if birlestirme_modu not in ('min', 'prod', 'mean'):
        raise ValueError('geçersiz birlestirme_modu')
    skorlar = []
    for z in dusunce_zincirleri:
        if not isinstance(z, dict) or 'cevap' not in z or 'adim_puanlari' not in z:
            raise ValueError('geçersiz zincir sözlüğü')
        cevap = z['cevap']
        puanlar = z['adim_puanlari']
        if not isinstance(cevap, str) or not cevap.strip():
            raise ValueError('geçersiz cevap')
        if not isinstance(puanlar, list) or not puanlar:
            raise ValueError('boş adım puanları')
        temiz_puanlar = []
        for p in puanlar:
            if isinstance(p, bool) or not isinstance(p, (int, float)) or (not math.isfinite(p)) or (not 0.0 <= p <= 1.0):
                raise ValueError('adım puanı [0, 1] aralığında sayı olmalı')
            temiz_puanlar.append(float(p))
        if birlestirme_modu == 'min':
            skor = min(temiz_puanlar)
        elif birlestirme_modu == 'prod':
            skor = 1.0
            for val in temiz_puanlar:
                skor *= val
        else:
            skor = sum(temiz_puanlar) / len(temiz_puanlar)
        skorlar.append(skor)
    secilen = max(range(len(dusunce_zincirleri)), key=lambda i: (skorlar[i], -i))
    en_zayif = min((float(x) for x in dusunce_zincirleri[secilen]['adim_puanlari']))
    return {'zincir_skorlari': skorlar, 'secilen_indis': secilen, 'secilen_cevap': dusunce_zincirleri[secilen]['cevap'], 'en_zayif_adim_skoru': en_zayif}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_11 as D
    D.goster(grpo_hedef_hesapla, prm_en_iyi_zincir)
```
```hint
İki görevin çözümlerini olduğu gibi buraya koy. Örnekleme sabit tohumla yapılır; farklı işlemcide yanıtlar biraz değişebilir, kabul kontrolleri buna bağlı değildir.
```
:::

::: anlat Sınır
Görevler RLVR doğrulayıcı puanlamasını, GRPO'nun kırpılmış hedefini ve PRM ile adım seçimini küçük sayılarla hesaplatır; final adım Qwen2.5-0.5B'nin son MLP'sini iki GRPO adımıyla günceller ve aynı modeli PRM olarak kullanır (tam RL eğitimi değildir). Gruptaki tüm yanıtlar aynı ödülü alırsa avantaj sıfır olur ve o soru öğrenme sinyali vermez; zorluğu uygun sorular seçilmelidir. Doğrulayıcı yalnız son cevabı kontrol ediyorsa model yanlış akıl yürütmeyle doğru cevaba ulaşmayı ya da biçim hilesini öğrenebilir (reward hacking). PRM etiketleri pahalıdır ve PRM'nin kendisi de kandırılabilir (ai-saldiri-64).

Kaynaklar: [Shao vd. 2024 - DeepSeekMath: Pushing the Limits of Mathematical Reasoning in Open Language Models](https://arxiv.org/abs/2402.03300), [Lightman vd. 2023 - Let's Verify Step by Step](https://arxiv.org/abs/2305.20050), [DeepSeek-AI 2025 - DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning](https://arxiv.org/abs/2501.12948).
:::

::: dusun
**DeepSeek-R1-Zero** deneyinde araştırmacılar hiç `SFT` yapmadan doğrudan `Base Model` üzerine `GRPO + RLVR` uyguladıklarında AIME 2024 pass@1 başarısı `%15.6`'dan `%71.0`'a çıktı; `%86.7` ise ayrı `cons@64` majority-voting ölçümüdür ([rapor, Tablo 2](https://arxiv.org/html/2501.12948v1#S2.T2)); ancak çok tuhaf bir yan etki (`Language Mixing / Readability Problem`) ortaya çıktı:
Model `<think>` bloğu içinde düşünürken bir cümleyi İngilizce başlatıp, ortasında Çinceye geçip, sonunu kod sembolleriyle bitirmeye başladı! Çünkü `RLVR` doğrulayıcısı yalnızca nihai cevabın (`\boxed{...}`) doğruluğuna puan veriyordu; dil tutarlılığı ayrıca ödüllendirilmiyordu. Doğruluğa ek olarak `<think>` biçim ödülü de kullanılıyordu; ödül yalnız nihai cevaptan ibaret değildi.

**Mimari Tasarım Sorusu:** Düşünce zincirinin hem insan tarafından okunabilir ve tek bir dilde tutarlı kalmasını sağlamak, hem de modelin özgürce muhakeme yürütme (`Exploration`) kapasitesini boğmamak için **DeepSeek-R1**'in 4 aşamalı boru hattında (`Cold-Start SFT` $\to$ `Reasoning GRPO` $\to$ `Rejection Sampling SFT` $\to$ `All-Scenario RL`) nasıl bir tasarım kullanılmıştır?
:::

::: ozet
- Bu ders, R1 tarzı açık `<think>...</think>` şablonuyla `Test-Time Compute` ve adım puanlamayı inceler. Bu görünür şablon bütün reasoning modellerinin iç işleyişini veya düşünce izini kullanıcıya açtığını göstermez.
- **`RLVR (Reinforcement Learning with Verifiable Rewards)`**, kandırılabilir nöral ödül modelleri yerine deterministik doğrulayıcılar (birim testler, sembolik matematik çözücüler, format kuralları) kullanarak `Reward Hacking` riskinin bir bölümünü azaltır. Eksik testler, hatalı doğrulayıcı veya yalnız formatı ödüllendiren bir kural yine sömürülebilir; geçen yanıtın gerçek görevi çözdüğü ayrıca sınanır.
- **`GRPO (Group Relative Policy Optimization)`**, aynı soruya üretilen $G$ adet yanıtın grup içi ortalama ve standart sapmasını ($A_i = \frac{r_i - \mu_r}{\sigma_r + \epsilon}$) baz alarak ayrı bir `Critic (Value)` ağı gereksinimini kaldırır. Toplam bellek kazancı model, optimizer, referans model ve aktivasyon maliyetine bağlıdır; koşulsuz yarı yarıya değildir.
- **`Process Reward Model (PRM)`**, çıkarım anında yalnızca son cevabı (`ORM`) değil, her bir düşünce adımını ayrı ayrı puanlayarak en zayıf halkası (`min`) veya çarpım skoru (`prod`) en sağlam olan düşünce zincirini seçer.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Aynı soruya dört yanıt çiz; ödüllerin grup içi ortalama ve standart sapmasından avantajı türet. Pozitif avantajda üst ratio kırpmasının, negatif avantajda alt ratio kırpmasının hangi güncellemeyi sınırladığını göster. KL cezasının referansa uzaklaşmayı ölçtüğünü, doğruluk ödülü olmadığını ayır. PRM'de mean, min ve prod aynı zinciri seçmek zorunda değildir; tek düşük adım puanı ile örnek ver. Son bölümde yerel birkaç adımlık GRPO deneyinin büyük ölçekli R1 eğitimi olmadığını ve verifier'dan geçen yanlış yanıtın hâlâ reward hacking olabileceğini belirt. Dinleyiciye sor: “Ödül doğrulanabiliyorsa doğrulayıcının kendisini kim sınar?”
:::
