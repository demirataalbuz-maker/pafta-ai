---
id: ai-uretim-05
title: "DeepSeekMoE Mimarisi: Shared/Routed Experts ve Auxiliary-Loss-Free Load Balancing"
track: ai-uretim
order: 5
duration_minutes: 40
difficulty: ileri
xp: 300
prerequisites: [ai-uretim-04]
esleme: ai-uretim-03, ai-uretim-04, ai-uretim-08
summary: "671B parametreli DeepSeek-V3/R1 veya Frontier MoE modeller nasıl token başına sadece 37B parametre çalıştırır? Fine-Grained Routed Experts, Always-On Shared Experts, Top-K Softmax Gating, Routing Collapse ve Auxiliary-Loss-Free Load Balancing."
tags: [deepseekmoe, mixture-of-experts, shared-experts, routed-experts, load-balancing, router-bias]
---

::: anlat 1. 671 Milyar Parametreli Bir Model Nasıl Token Başına Yalnızca 37 Milyar Parametre Çalıştırır?
## MoE ve load balancing

Bir MoE katmanında bütün expert parametreleri her token için kullanılmaz. Router, token için sınırlı sayıda expert seçer; shared expert bileşenleri ayrıca çalışabilir. Bu derste toplam ve aktif parametre maliyetini ayıracak, expert seçimini ve yük dengesini sağlayan bias güncellemesini uygulayacaksın.

Bir konferansta ya da teknik mülakatta kürsüye çıktığında izleyicilere şu soruyu sorarak başla:
> *"Önünüzde `671 Milyar` (`671B`) parametreli devasa bir **DeepSeek-V3 / DeepSeek-R1** modeli var. Normal bir yoğun (`Dense`) `Transformer` modelinde (`Llama-3.1-405B` gibi), ürettiğiniz **her bir kelime parçası (`Token`)** için o `405 Milyar` parametrenin tamamını GPU belleğinden (`HBM`) okuyup matris çarpımına sokmak zorundasınızdır. Peki nasıl oluyor da `671B` büyüklüğündeki bir **Sparse Mixture-of-Experts (`MoE`)** modeli, her bir `token` için yalnızca **`37 Milyar` (`37B`)** parametre çalıştırarak hem bir trilyonluk dev model kadar bilgili olabiliyor hem de küçük bir model kadar hızlı ve ucuza çalışabiliyor?"*

### 🧠 Yoğun (`Dense`) Beyin vs Uzmanlaşmış (`Sparse MoE`) Hastane
- **`Dense Transformer` (`Yoğun Model`):** Bir hastaneye girdiğinde başın ağrısa bile ortopedi, kardiyoloji, göz, nöroloji ve cildiye dahil **hastanedeki 100 doktorun tamamının** aynı anda seni muayene etmesidir! Her `token`, dev bir `SwiGLU Feed-Forward Network (FFN)` bloğunun tüm nöronlarından geçer. Bilgi kapasitesini (`Model Capacity`) 10 kat artırmak istediğinde, `token` başına gereken işlem yükü (`FLOPs/token`) de 10 kat artar!
- **`Sparse Mixture-of-Experts (MoE)` (`Seyrek Uzmanlar Karışımı`):** `Attention` katmanı tüm `token`lar için ortaktır; ancak ansiklopedik bilginin depolandığı `FFN / MLP` katmanı tek bir dev blok yerine **$N$ adet bağımsız küçük uzman ağa (`Experts`)** bölünür. Ön kapıda duran çok hafif bir yönlendirici (**`Router / Gating Network`**), gelen `token`'ın vektörüne ($x \in \mathbb{R}^d$) bakar ve:
  - *"Bu `token` bir Python kodu parçası; bunu **Uzman #4 (Yazılım)** ve **Uzman #19 (Mantık)** doktorlarına gönderin, diğer 254 uzman uyusun!"* der.

Böylece toplam parametre sayısını (`Total Parameters` — bilgi hafızasını) devasa boyutlara (`671B`) çıkarırken, `token` başına aktif işlem maliyetini (`Active Parameters / FLOPs` — `37B`) sabit ve düşük tutarsın!

```text
                       GİRDİ TOKEN TEMSİLİ: x ∈ R^d
                                    │
         ┌──────────────────────────┴──────────────────────────┐
         ▼                                                     ▼
 [ALWAYS-ON SHARED EXPERTS]                         [ROUTER / GATING NETWORK]
  (Her Token İçin Kesin Çalışır)                     s_i = Softmax / Sigmoid(x · W_g)
  ┌────────────┐  ┌────────────┐                               │
  │ Shared #1  │  │ Shared #2  │                     Top-K Seçimi (s_i + b_i)
  └─────┬──────┘  └─────┬──────┘                               │
        └───────┬───────┘               ┌──────────────┬───────┴──────┬──────────────┐
                │                       ▼              ▼              ▼              ▼
                │                 [Expert #1]    [Expert #2]    [Expert #3]    [Expert #N]
                │                   (Uyuyor)      (AKTİF w_2)    (AKTİF w_3)     (Uyuyor)
                │                                      │              │
                ▼                                      └──────┬───────┘
         y_shared = Σ E_s(x)                           y_routed = Σ w_i · E_i(x)
                │                                             │
                └──────────────────────┬──────────────────────┘
                                       ▼
                        ÇIKTI: y = x + y_shared + y_routed
```

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [DeepSeek-V3 teknik raporu](https://arxiv.org/abs/2412.19437). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: anlat 2. Klasik MoE'dan DeepSeekMoE'ya: Fine-Grained Routed Experts + Always-On Shared Experts
İlk nesil `MoE` modelleri (`GShard`, `Switch Transformer`, `Mixtral 8x7B`) sadece 8 veya 16 adet büyük uzmana sahipti ve her `token` için `Top-1` veya `Top-2` uzman seçiyordu. Ancak klasik `MoE` mimarisinde **iki büyük yapısal darboğaz** ortaya çıktı:
1. **`Knowledge Redundancy` (Bilgi Tekrarı):** Dilbilgisi kuralları, bağlaçlar ve temel dünya bilgisi *her* `token` için gereklidir. Klasik `MoE`'da 8 uzmanın 8'i de kendi içinde Türkçe/İngilizce dilbilgisini tekrar tekrar öğrenmek zorunda kalıyor, uzman kapasitesi ortak bilgilerle israf ediliyordu!
2. **`Knowledge Hybridity` (Kaba Uzmanlık):** Sadece 8 uzman olduğunda tek bir uzman hem tıp, hem hukuk, hem de kimyayı aynı anda sırtlamak zorunda kalıyordu.

**`DeepSeekMoE`** mimarisi bu iki sorunu iki radikal mühendislik darbesiyle çözdü:

### 1. `Always-On Shared Experts` (Her Zaman Açık Ortak Uzmanlar)
Uzmanların küçük bir grubu ($N_s$ adet, örn. `DeepSeek-V3`'te $N_s = 1$) **`Shared Expert` (Ortak Uzman)** olarak ayrılır. Hiçbir `Router` kapısına sorulmadan **her `token` %100 kesinlikle bu ortak uzmanlardan geçer.**
- **Sonuç:** Dilbilgisi, genel kültür ve ortak örüntüler `Shared Experts` içinde toplanır; diğer yönlendirilen uzmanlar (`Routed Experts`) ortak bilgileri tekrar ezberlemekten kurtulup saf niş alanlara odaklanır!

### 2. `Fine-Grained Routed Experts` (İnce Taneli Yönlendirilen Uzmanlar)
Uzmanların ara katman boyutu ($d_{\text{ff}}$) küçültülerek uzman sayısı büyütülür (örn. 8 dev uzman yerine $N_r = 256$ ince uzman) ve her `token` için daha fazla uzman (örn. $K = 8$ uzman) aktif edilir.
- $8$ uzmandan $2$'sini seçtiğinde $\binom{8}{2} = 28$ farklı uzman kombinasyonu vardır.
- $256$ ince uzmandan $8$'ini seçtiğinde ise $\binom{256}{8} \approx 4.02 \times 10^{14}$ (**402 Trilyon!**) farklı uzman kombinasyonu oluşur!

### 📐 DeepSeekMoE Katmanının Matematiksel Denklemi
Girdi vektörü $x \in \mathbb{R}^d$ için `Router` ağırlık matrisi $W_g \in \mathbb{R}^{d \times N_r}$ ile önce ham uzman yatkınlık skorları (`Affinity Scores` $s_i$) hesaplanır ve en yüksek $K$ uzman seçilerek (`Top-K Softmax Gating`) çıktı üretilir:

$$y = x + \sum_{j=1}^{N_s} \text{FFN}_j^{(\text{shared})}(x) + \sum_{i \in \text{TopK}(s)} g_i \cdot \text{FFN}_i^{(\text{routed})}(x)$$

```python
import math

def kombinasyon_karsilastir(n, k):
    return math.comb(n, k)

mixtral_kombinasyon = kombinasyon_karsilastir(8, 2)
deepseek_kombinasyon = kombinasyon_karsilastir(64, 6)
print(f"Klasik MoE (8'den 2)     : {mixtral_kombinasyon:,} kombinasyon")
print(f"Fine-Grained (64'ten 6)  : {deepseek_kombinasyon:,} kombinasyon")
```
:::

::: anlat 3. Routing Collapse Felaketi ve Auxiliary-Loss-Free Load Balancing Yaklaşımı
Bir `MoE` modelini sıfırdan (`From Scratch`) eğitmeye başladığında ilk 100 adımda başına gelecek en korkunç felaket **`Routing Collapse` (Yönlendirme Çöküşü)** olgusudur:
- Başlangıçta rastgele şans eseri `Uzman #3` birazcık daha iyi gradyan alır ve güçlenir.
- `Router`, `Loss` değerini düşürmek için bir sonraki adımda daha çok `token`'ı `Uzman #3`'e gönderir.
- `Uzman #3` daha çok veri gördükçe daha da güçlenir ve birkaç bin adım sonra **`Router` bütün `token`ların %99'unu tek bir uzmana gönderirken diğer 255 uzman tamamen ölür (`Dead Experts`)!**
- Ayrıca dağıtık eğitimde (`Expert Parallelism` — her uzmanın farklı bir GPU'da durması) tüm `token`lar tek bir GPU'ya yığılırken diğer 255 GPU boşta bekler!

### ❌ Eski Çözüm: `Auxiliary Load Balancing Loss` Neden Kusurluydu?
Yıllarca mühendisler bu sorunu çözmek için ana eğitim kaybına (`Cross-Entropy Loss`) yapay bir ceza terimi (**`Auxiliary Loss`** $\mathcal{L}_{\text{aux}} = \alpha \sum f_i P_i$) eklediler. Ancak burada ölümcül bir ikilem (`Interference Dilemma`) vardı:
- Eğer ceza katsayısı $\alpha$ çok küçükse $\to$ **`Routing Collapse`** yaşanır, GPU'lar dengesiz yüklenir.
- Eğer ceza katsayısı $\alpha$ büyükse $\to$ Model dil öğrenmeyi bırakıp sırf cezadan kaçmak için **anlamsız `token`ları yanlış uzmanlara zorla dağıtmaya başlar** ve modelin zekası (`Perplexity`) düşer! (Çünkü $\mathcal{L}_{\text{aux}}$ üzerinden akan parazit gradyanlar ana dil modelleme gradyanlarını bozar).

### 🚀 Yeni Çağ: `Auxiliary-Loss-Free Load Balancing` (`Dynamic Router Bias` $b_i$)
`DeepSeek-V3` ekibi tarihin en zarif mühendislik çözümlerinden birini geliştirdi: **Hiçbir `Auxiliary Loss` (yardımcı ceza kaybı ve parazit gradyan) kullanmadan %100 dengeli yük dağılımı!**

Nasıl çalışır?
1. Her yönlendirilen uzman ($i = 1, \dots, N_r$) için **gradyan almayan** dinamik bir önyargı skoru (**`Dynamic Router Bias` $b_i$**, başlangıçta $0.0$) tanımlanır.
2. **Hangi `Top-K` uzmanın seçileceğine** karar verirken ham yatkınlık skoruna bu `bias` eklenir:
   $$\text{Seçim Skoru}_i = s_i + b_i \quad \longrightarrow \quad \text{Top-K İndeksleri } \mathcal{T} = \text{ argtop}_K(s_i + b_i)$$
3. **ÇOK KRİTİK NOKTA:** Uzmanlar seçildikten sonra, uzmanların çıktılarını çarpan **kapı ağırlıkları (`Gating Weights` $g_i$)** hesaplanırken `bias` ($b_i$) **KULLANILMAZ**, yalnızca orijinal temiz $s_i$ skorları kullanılır! Böylece modelin ileri/backpropagation matematiği hiçbir yapay gürültüyle kirlenmez!
4. Her eğitim adımının (`Batch`) sonunda her uzmanın kaç `token` aldığı ($c_i$) sayılır ve ortalama hedef yük ($\bar{c} = \frac{1}{N_r}\sum c_i$) ile karşılaştırılır:
   - Eğer $i$. uzman ortalamanın **üzerinde** yük aldıysa ($c_i > \bar{c}$), çok popülerdir $\to$ Bias değeri $\gamma$ (`Bias Update Speed`) kadar **düşürülür**: $b_i \leftarrow b_i - \gamma$
   - Eğer $i$. uzman ortalamanın **altında** yük aldıysa ($c_i < \bar{c}$), aç kalmıştır $\to$ Bias değeri $\gamma$ kadar **artırılır**: $b_i \leftarrow b_i + \gamma$
   - Tam ortalamadaysa ($c_i = \bar{c}$) $\to$ Değiştirilmez!

### 🛡️ `Capacity Factor` ($CF$) ve `Token Dropping`
Donanım seviyesinde statik bellek ayırırken bir uzmana tek adımda gelebilecek maksimum `token` sınırına **`Expert Capacity`** denir:
$$\text{Capacity} = \left\lfloor CF \times \frac{T \times K}{N_r} \right\rfloor$$
Eğer `Capacity Factor` ($CF$, örn. $1.25$) sınırını aşan fazla `token` olursa o `token` uzmanda işlenmez ve doğrudan `Residual Connection` üzerinden bir sonraki katmana atlar (**`Token Dropping`**). `Auxiliary-Loss-Free Load Balancing` sayesinde yükler o kadar dengeli dağılır ki neredeyse sıfır `Token Dropping` ile eğitim tamamlanır!
:::

::: anlat 4. Gerçek PyTorch DeepSeekMoE Katmanı Mimarisi (Üretim Kodu)
Aşağıda gerçek bir `Frontier LLM` üretim çatısında (`PyTorch`) `Shared Experts`, `Fine-Grained Routed Experts` ve `Auxiliary-Loss-Free Dynamic Bias` mekanizmasının `nn.Module` olarak nasıl kodlandığını görebilirsin:

```python norun
import torch
import torch.nn as nn
import torch.nn.functional as F

class SwiGLUExpert(nn.Module):
    def __init__(self, d_model: int, d_ff: int):
        super().__init__()
        self.w_gate = nn.Linear(d_model, d_ff, bias=False)
        self.w_up   = nn.Linear(d_model, d_ff, bias=False)
        self.w_down = nn.Linear(d_ff, d_model, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.w_down(F.silu(self.w_gate(x)) * self.w_up(x))

class DeepSeekMoELayer(nn.Module):
    def __init__(self, d_model: int, d_ff: int, n_shared: int = 1, n_routed: int = 64, top_k: int = 6, gamma: float = 0.001):
        super().__init__()
        self.n_routed = n_routed
        self.top_k = top_k
        self.gamma = gamma
        self.shared_experts = nn.ModuleList([SwiGLUExpert(d_model, d_ff) for _ in range(n_shared)])
        self.routed_experts = nn.ModuleList([SwiGLUExpert(d_model, d_ff) for _ in range(n_routed)])
        self.router_weight = nn.Linear(d_model, n_routed, bias=False)
        # Auxiliary-Loss-Free Dynamic Bias (gradyan almaz, buffer olarak tutulur!)
        self.register_buffer("expert_bias", torch.zeros(n_routed))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [batch * seq_len, d_model]
        shared_out = sum(exp(x) for exp in self.shared_experts)
        # 1. Ham yatkınlık skorları (Affinity Scores)
        scores = torch.sigmoid(self.router_weight(x))  # [T, n_routed]
        # 2. Top-K seçimi (scores + expert_bias ile yapılır, gradyan bozulmaz!)
        _, topk_idx = torch.topk(scores + self.expert_bias.unsqueeze(0), k=self.top_k, dim=-1)
        # 3. Gating ağırlıkları ise SADECE orijinal scores üzerinden normalize edilir!
        topk_scores = torch.gather(scores, dim=-1, index=topk_idx)
        gates = topk_scores / (topk_scores.sum(dim=-1, keepdim=True) + 1e-9)
        
        routed_out = torch.zeros_like(x)
        expert_counts = torch.zeros(self.n_routed, device=x.device)
        for k_pos in range(self.top_k):
            idx_k = topk_idx[:, k_pos]
            gate_k = gates[:, k_pos].unsqueeze(-1)
            for exp_id in range(self.n_routed):
                mask = (idx_k == exp_id)
                if mask.any():
                    expert_counts[exp_id] += mask.sum()
                    routed_out[mask] += gate_k[mask] * self.routed_experts[exp_id](x[mask])
        
        # 4. Eğitim sırasında Auxiliary-Loss-Free Dynamic Bias güncellemesi
        if self.training:
            with torch.no_grad():
                avg_load = expert_counts.mean()
                self.expert_bias += self.gamma * torch.sign(avg_load - expert_counts)
        return x + shared_out + routed_out
```
:::

::: tahmin MoE Aktif Parametre ve Kapasite Hesabı
Bir `DeepSeekMoE` katmanında $N_s = 2$ adet `Shared Expert` ve $N_r = 64$ adet `Routed Expert` bulunuyor. Her bir uzman (hem `Shared` hem `Routed`) tam $10\text{ Milyon}$ parametreye sahip ve `Router` her `token` için $K = 6$ adet `Routed Expert` seçiyor.
Bu katmandaki **toplam uzman parametresi** ve tek bir `token` işlenirken **aktif olan uzman parametresi** kaç milyondur?

```python
n_shared, n_routed, top_k = 2, 64, 6
uzman_param_milyon = 10

toplam_param = (n_shared + n_routed) * uzman_param_milyon
aktif_param = (n_shared + top_k) * uzman_param_milyon
oran = round(aktif_param / toplam_param * 100, 1)
print(f"Toplam: {toplam_param}M | Aktif: {aktif_param}M (%{oran})")
```

???

```cikti
Toplam: 660M | Aktif: 80M (%12.1)
```
Katmanda toplam $2 + 64 = 66$ uzman olduğu için toplam kapasite $66 \times 10\text{M} = 660\text{ Milyon}$ parametredir. Ancak her `token` yalnızca $2$ `Shared Expert` ve seçilen $6$ `Routed Expert` olmak üzere toplam $8$ uzmandan geçer; yani `token` başına yalnızca $80\text{ Milyon}$ parametre (`%12.1`) aktif olarak çalıştırılır.
:::

::: gorev 1 · Shared + Top-K Routed MoE Katmanı İleri Yayılımı
Bir `DeepSeekMoE` katmanının ileri yayılımını (`Forward Pass`) gerçekleştiren `moe_ileri(x, ortak_uzmanlar, yonlendirilen_uzmanlar, router_agirliklari, k)` işlevini yaz:

1. **Girdiler:**
   - `x`: Boyutu $d$ olan girdi vektörü (`float`/`int` listesi, örn. `[1.0, -0.5]`).
   - `ortak_uzmanlar`: Her biri $d$ uzunluğunda ölçekleme vektörü olan `Always-On Shared Experts` listesi (her uzman $e$, girdiyle eleman bazlı çarpım $e \odot x = [e_j \cdot x_j]$ üretir).
   - `yonlendirilen_uzmanlar`: $N_r$ adet `Routed Expert` listesi (her uzman $e^{(i)}$, $d$ uzunluğunda vektördür ve $e^{(i)} \odot x$ üretir).
   - `router_agirliklari`: Boyutu $N_r \times d$ olan yönlendirici matris (`list of lists`). $i$. uzmanın ham `logit` skoru, $i$. satır ile `x` vektörünün iç çarpımıdır (`Dot Product`: $z_i = \sum_{j} W_{i,j} x_j$).
   - `k`: Seçilecek aktif `Routed Expert` sayısı (`1 <= k <= N_r` tam sayı).
2. **Adımlar:**
   - Tüm `yonlendirilen_uzmanlar` için ham `logit` skorlarını ($z_0, z_1, \dots, z_{N_r-1}$) hesapla.
   - En yüksek `logit` skoruna sahip **`k` adet uzmanı (`Top-K`)** seç (eşitlik durumunda küçük indeksli uzmana öncelik ver).
   - Sadece seçilen `k` uzmanın `logit` skorları üzerinden sayısal kararlı **`Top-K Softmax`** kapı ağırlıklarını ($g_{i_1}, \dots, g_{i_k}$, toplamları $1.0$) hesapla:
     $$g_m = \frac{\exp(z_m - \max z_{\text{topK}})}{\sum_{r \in \text{topK}} \exp(z_r - \max z_{\text{topK}})}$$
   - **Çıktı Vektörü (`cikti`):** Girdi `x` (`Residual`) + tüm `ortak_uzmanlar`ın çıktılarının toplamı + seçilen `k` yönlendirilen uzmanın kapı ağırlıklı (`g_m`) çıktılarının toplamı:
     $$y_j = x_j + \sum_{s} E_{s,j}^{\text{shared}} x_j + \sum_{m \in \text{topK}} g_m \cdot (E_{m,j}^{\text{routed}} x_j)$$
   - Çıktı vektöründeki her elemanı ve kapı ağırlıklarını `round(val, 6)` ile yuvarla.
3. **Dönüş Değeri:**
   `{"secilen_uzmanlar": [indeksler...], "kapi_agirliklari": [g_1, ...], "cikti": [y_0, ...]}` sözlüğü döndür (`secilen_uzmanlar` en yüksek skordan düşüğe sıralı olmalıdır). Girdileri değiştirme.

```starter
def moe_ileri(x, ortak_uzmanlar, yonlendirilen_uzmanlar, router_agirliklari, k):
    # KUSURLU BAŞLANGIÇ KODU: Top-K yönlendirme ve uzman çarpımlarını yapmadan sadece x döndürüyor!
    return {
        "secilen_uzmanlar": list(range(k)),
        "kapi_agirliklari": [round(1.0 / k, 6) for _ in range(k)],
        "cikti": [round(float(v), 6) for v in x],
    }

ornek_x = [1.0, 2.0]
ornek_shared = [[0.5, 0.5]]
ornek_routed = [[1.0, 0.0], [0.0, 1.0], [2.0, 2.0]]
ornek_router = [[1.0, 0.0], [0.0, 2.0], [1.0, 1.0]]
print(moe_ileri(ornek_x, ornek_shared, ornek_routed, ornek_router, 2))
```

```test
import copy, math

def _ref_moe(x, ortak, yon, router, k):
    d = len(x)
    logits = [sum(router[i][j] * x[j] for j in range(d)) for i in range(len(yon))]
    sirali = sorted(range(len(yon)), key=lambda i: (-logits[i], i))[:k]
    topk_l = [logits[i] for i in sirali]
    m = max(topk_l)
    exps = [math.exp(z - m) for z in topk_l]
    s = sum(exps)
    gates = [e / s for e in exps]
    cikti = []
    for j in range(d):
        val = x[j]
        for sh in ortak:
            val += sh[j] * x[j]
        for idx, g in zip(sirali, gates):
            val += g * (yon[idx][j] * x[j])
        cikti.append(round(val, 6))
    return {
        "secilen_uzmanlar": sirali,
        "kapi_agirliklari": [round(g, 6) for g in gates],
        "cikti": cikti,
    }

def sozlesme(fn):
    try:
        vakalar = [
            ([1.0, 2.0], [[0.5, 0.5]], [[1.0, 0.0], [0.0, 1.0], [2.0, 2.0]], [[1.0, 0.0], [0.0, 2.0], [1.0, 1.0]], 2),
            ([2.0, -1.0, 0.5], [[0.2, 0.3, 0.4], [0.1, 0.1, 0.1]], [[1.5, 0.5, 2.0], [0.0, 3.0, 1.0], [2.0, 1.0, 0.0], [-1.0, 2.0, 0.5]], [[0.5, -1.0, 2.0], [1.0, 2.0, 0.0], [2.0, 0.5, 1.0], [-0.5, 1.0, 1.0]], 2),
            ([1.0, 1.0], [], [[2.0, 3.0], [4.0, 1.0]], [[0.5, 0.5], [0.5, 0.5]], 1),
        ]
        for x, sh, ro, rw, k in vakalar:
            x_c, sh_c, ro_c = copy.deepcopy(x), copy.deepcopy(sh), copy.deepcopy(ro)
            sonuc = fn(x, sh, ro, rw, k)
            beklenen = _ref_moe(x, sh, ro, rw, k)
            if not isinstance(sonuc, dict) or set(sonuc.keys()) != {"secilen_uzmanlar", "kapi_agirliklari", "cikti"}:
                return False
            if sonuc["secilen_uzmanlar"] != beklenen["secilen_uzmanlar"]:
                return False
            if any(abs(a - b) > 1e-5 for a, b in zip(sonuc["kapi_agirliklari"], beklenen["kapi_agirliklari"])):
                return False
            if any(abs(a - b) > 1e-5 for a, b in zip(sonuc["cikti"], beklenen["cikti"])):
                return False
            if x != x_c or sh != sh_c or ro != ro_c:
                return False
        return True
    except Exception:
        return False

buyuk_logit = moe_ileri([1.0], [], [[1.0], [1.0]], [[1000.0], [999.0]], 2)
ok(buyuk_logit == {"secilen_uzmanlar": [0, 1], "kapi_agirliklari": [0.731059, 0.268941], "cikti": [2.0]}, "büyük sonlu logitlerde softmax taşmamalı")
ok(sozlesme(moe_ileri), "moe_ileri Shared Experts, Top-K Softmax Gating ve Residual toplamını doğru hesaplamalı")

def m_shared_unut(x, sh, ro, rw, k):
    return moe_ileri(x, [], ro, rw, k)

def m_residual_unut(x, sh, ro, rw, k):
    r = copy.deepcopy(moe_ileri(x, sh, ro, rw, k))
    r["cikti"] = [round(r["cikti"][j] - x[j], 6) for j in range(len(x))]
    return r

def m_esit_kapi(x, sh, ro, rw, k):
    r = copy.deepcopy(moe_ileri(x, sh, ro, rw, k))
    r["kapi_agirliklari"] = [round(1.0 / k, 6) for _ in range(k)]
    return r

for ad, m in [("Shared uzmanları unutan", m_shared_unut), ("Residual bağlantıyı unutan", m_residual_unut), ("Softmax yerine eşit ağırlık veren", m_esit_kapi)]:
    ok(not sozlesme(m), f"Yanlış çözüm/mutant yakalanmalı: {ad}")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef moe_ileri(x, ortak_uzmanlar, yonlendirilen_uzmanlar, router_agirliklari, k):\n    d = len(x)\n    n_routed = len(yonlendirilen_uzmanlar)\n    logits = [sum((router_agirliklari[i][j] * x[j] for j in range(d))) for i in range(n_routed)]\n    secilenler = sorted(range(n_routed), key=lambda i: (-logits[i], i))[:k]\n    topk_logits = [logits[i] for i in secilenler]\n    max_l = max(topk_logits)\n    exps = [math.exp(z - max_l) for z in topk_logits]\n    toplam_exp = sum(exps)\n    kapi_agirliklari = [e / toplam_exp for e in exps]\n    cikti = []\n    for j in range(d):\n        deger = float(x[j])\n        for ortak in ortak_uzmanlar:\n            deger += ortak[j] * x[j]\n        for idx, g in zip(secilenler, kapi_agirliklari):\n            deger += g * (yonlendirilen_uzmanlar[idx][j] * x[j])\n        cikti.append(round(deger, 6))\n    return {'secilen_uzmanlar': secilenler, 'kapi_agirliklari': [round(g, 6) for g in kapi_agirliklari], 'cikti': cikti}", 'referans', 'exec'), _REF)
_t, _g = _ff(moe_ileri, _REF['moe_ileri'], ([1.0, 2.0], [[0.5, 0.5]], [[1.0, 0.0], [0.0, 1.0], [2.0, 2.0]], [[1.0, 0.0], [0.0, 2.0], [1.0, 1.0]], 2), tohum=2004, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (moe_ileri): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def moe_ileri(x, ortak_uzmanlar, yonlendirilen_uzmanlar, router_agirliklari, k):
    d = len(x)
    n_routed = len(yonlendirilen_uzmanlar)
    logits = [sum(router_agirliklari[i][j] * x[j] for j in range(d)) for i in range(n_routed)]
    secilenler = sorted(range(n_routed), key=lambda i: (-logits[i], i))[:k]
    topk_logits = [logits[i] for i in secilenler]
    max_l = max(topk_logits)
    exps = [math.exp(z - max_l) for z in topk_logits]
    toplam_exp = sum(exps)
    kapi_agirliklari = [e / toplam_exp for e in exps]

    cikti = []
    for j in range(d):
        deger = float(x[j])
        for ortak in ortak_uzmanlar:
            deger += ortak[j] * x[j]
        for idx, g in zip(secilenler, kapi_agirliklari):
            deger += g * (yonlendirilen_uzmanlar[idx][j] * x[j])
        cikti.append(round(deger, 6))

    return {
        "secilen_uzmanlar": secilenler,
        "kapi_agirliklari": [round(g, 6) for g in kapi_agirliklari],
        "cikti": cikti,
    }
```

```hint
Önce her yönlendirilen uzman için `sum(router_agirliklari[i][j] * x[j] for j in range(d))` ile logit skorlarını hesapla. `sorted(range(n_routed), key=lambda i: (-logits[i], i))[:k]` ile Top-K uzmanları seçip yalnızca bu k adet logit üzerinde Softmax uygula.
```
:::

::: gorev 2 · Auxiliary-Loss-Free Dynamic Bias Güncellemesi (Yük Dengeleme)
`DeepSeek-V3` mimarisindeki `Auxiliary-Loss-Free Load Balancing` mekanizmasını gerçekleştiren `bias_guncelle(mevcut_biaslar, uzman_yukleri, gama_adimi)` işlevini yaz:

1. **Girdiler:**
   - `mevcut_biaslar`: $N_r$ adet uzmanın mevcut `Router Bias` ($b_i$) değerlerini tutan `float` listesi.
   - `uzman_yukleri`: Son eğitim adımında her uzmana yönlendirilen `token` sayılarını ($c_i$) tutan $N_r$ elemanlı liste.
   - `gama_adimi`: Bias güncelleme adım büyüklüğü ($\gamma > 0$).
2. **Kurallar:**
   - Uzman başına düşen **hedef ortalama yükü** ($\bar{c} = \frac{1}{N_r}\sum_{i=0}^{N_r-1} c_i$) hesapla.
   - Her uzman $i$ için:
     - Eğer $c_i > \bar{c}$ (ortalamanın üstünde yük almışsa, aşırı yüklü / `Overloaded`): $b_i^{\text{yeni}} = b_i - \gamma$
     - Eğer $c_i < \bar{c}$ (ortalamanın altında yük almışsa, az yüklü / `Underloaded`): $b_i^{\text{yeni}} = b_i + \gamma$
     - Eğer $|c_i - \bar{c}| \le 10^{-9}$ (tam ortalamadaysa): $b_i^{\text{yeni}} = b_i$
   - Ayrıca yük dengesizliğini ölçen **`Max Load Violation Ratio`** değerini hesapla (`ortalama > 0` ise $\max(c_i) / \bar{c}$, tüm yükler `0` ise `1.0`).
   - Tüm yeni `bias` değerlerini ve oranları `round(val, 6)` ile yuvarla.
3. **Dönüş Değeri:**
   `{"ortalama_yuk": float, "maks_ihlal_orani": float, "yeni_biaslar": [float, ...]}` sözlüğü döndür. Girdi listelerini değiştirme.

```starter
def bias_guncelle(mevcut_biaslar, uzman_yukleri, gama_adimi):
    # KUSURLU BAŞLANGIÇ KODU: bias değerlerini güncellemeden olduğu gibi döndürüyor!
    return {
        "ortalama_yuk": 0.0,
        "maks_ihlal_orani": 1.0,
        "yeni_biaslar": [round(float(b), 6) for b in mevcut_biaslar],
    }

print(bias_guncelle([0.0, 0.0, 0.0, 0.0], [100, 20, 40, 0], 0.01))
```

```test
import copy

def _ref_bias(biaslar, yukler, gama):
    ort = sum(yukler) / len(yukler)
    ihlal = (max(yukler) / ort) if ort > 0 else 1.0
    yeni = []
    for b, c in zip(biaslar, yukler):
        if c > ort + 1e-9:
            yeni.append(round(b - gama, 6))
        elif c < ort - 1e-9:
            yeni.append(round(b + gama, 6))
        else:
            yeni.append(round(float(b), 6))
    return {
        "ortalama_yuk": round(ort, 6),
        "maks_ihlal_orani": round(ihlal, 6),
        "yeni_biaslar": yeni,
    }

def sozlesme(fn):
    try:
        vakalar = [
            ([0.0, 0.0, 0.0, 0.0], [100, 20, 40, 0], 0.01),
            ([0.05, -0.02, 0.01], [30, 30, 30], 0.005),
            ([-0.1, 0.2, 0.0, 0.05], [10, 50, 20, 20], 0.02),
            ([0.0, 0.0], [0, 0], 0.01),
            ([0.12345678] * 3, [1, 0, 0], 0.01),
            ([0.12345678] * 2, [1, 1], 0.01),
        ]
        for b, y, g in vakalar:
            b_kopya, y_kopya = copy.deepcopy(b), copy.deepcopy(y)
            sonuc = fn(b, y, g)
            bek = _ref_bias(b, y, g)
            if sonuc != bek or b != b_kopya or y != y_kopya:
                return False
        return True
    except Exception:
        return False

ok(sozlesme(bias_guncelle), "bias_guncelle aşırı yüklü uzmanların bias'ını düşürüp az yüklü olanları artırmalı")

def m_ters_yon(b, y, g):
    return bias_guncelle(b, y, -g)

def m_ihlal_sabit(b, y, g):
    r = copy.deepcopy(bias_guncelle(b, y, g))
    r["maks_ihlal_orani"] = 1.0
    return r

for ad, m in [("Bias yönünü ters uygulayan", m_ters_yon), ("İhlal oranını hesaplamayan", m_ihlal_sabit)]:
    ok(not sozlesme(m), f"Yanlış çözüm/mutant yakalanmalı: {ad}")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def bias_guncelle(mevcut_biaslar, uzman_yukleri, gama_adimi):\n    ort = sum(uzman_yukleri) / len(uzman_yukleri)\n    ihlal = max(uzman_yukleri) / ort if ort > 0 else 1.0\n    yeni_biaslar = []\n    for b, c in zip(mevcut_biaslar, uzman_yukleri):\n        if c > ort + 1e-09:\n            yeni_biaslar.append(round(b - gama_adimi, 6))\n        elif c < ort - 1e-09:\n            yeni_biaslar.append(round(b + gama_adimi, 6))\n        else:\n            yeni_biaslar.append(round(float(b), 6))\n    return {'ortalama_yuk': round(ort, 6), 'maks_ihlal_orani': round(ihlal, 6), 'yeni_biaslar': yeni_biaslar}", 'referans', 'exec'), _REF)
_t, _g = _ff(bias_guncelle, _REF['bias_guncelle'], ([0.0, 0.0, 0.0, 0.0], [100, 20, 40, 0], 0.01), tohum=2412, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (bias_guncelle): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def bias_guncelle(mevcut_biaslar, uzman_yukleri, gama_adimi):
    ort = sum(uzman_yukleri) / len(uzman_yukleri)
    ihlal = (max(uzman_yukleri) / ort) if ort > 0 else 1.0
    yeni_biaslar = []
    for b, c in zip(mevcut_biaslar, uzman_yukleri):
        if c > ort + 1e-9:
            yeni_biaslar.append(round(b - gama_adimi, 6))
        elif c < ort - 1e-9:
            yeni_biaslar.append(round(b + gama_adimi, 6))
        else:
            yeni_biaslar.append(round(float(b), 6))
    return {
        "ortalama_yuk": round(ort, 6),
        "maks_ihlal_orani": round(ihlal, 6),
        "yeni_biaslar": yeni_biaslar,
    }
```

```hint
Önce `ort = sum(uzman_yukleri) / len(uzman_yukleri)` ile ortalama yükü bul. Her uzmanın yükü `c > ort + 1e-9` ise `b - gama_adimi`, `c < ort - 1e-9` ise `b + gama_adimi`, eşitse `b` olarak yeni listeye ekle.
```
:::

::: anlat Gerçek deney: Gerçek gizli durumlarla yönlendirme, dengeleme ve uzman doyurma
Elimizde ön eğitimli bir MoE modeli yok; bu yüzden final yönlendirmenin **girdisini** gerçek yapar: altı farklı türden metin (bütçe haberi, Python kodu, Fransızca, ilaç talimatı, güvenlik günlüğü, masal) SmolLM2-135M'den geçirilir ve 6. katmanın 97 gerçek gizli durumu alınır. Bu durumlar 32 temel bileşene indirilir, birim normlu yapılır ve **k-means** ile 8 merkeze ayrılır; yönlendirici bu merkezlerdir. Böylece yönlendirme istatistiği gerçek bir modelin temsil uzayından gelir.

- **İleri geçiş:** her token senin `moe_ileri` işlevinle top-2 uzmana gider; seçimler ve çıktı torch referansıyla karşılaştırılır.
- **Dengeleme:** gerçek veri dengesiz dağılır (en yüklü uzman / ortalama). Bias yalnız **seçimde** kullanılır: yönlendiriciye sabit 1 özelliği eklenir ve bias o sütuna yazılır, kapı ağırlığı değişmez. 60 tur boyunca senin `bias_guncelle` işlevin yüke göre bias'ı iter.
- **Uzman doyurma:** saldırgan aynı tokenı (`" admin"`) 24 kez tekrarlar. Yönlendirme girdiye bağlı olduğundan bu tokenlar aynı iki uzmana yığılır; kapasite sınırlı bir sistemde aynı batch'teki başka kullanıcıların tokenları düşer (ai-saldiri-61).

**Güvenlik yönü — kapasite sınırında token düşürme:** Gerçek MoE sistemlerinde her uzmanın bir batch'te kabul edebileceği token sayısı sınırlıdır (kapasite çarpanı 1.25). Kurbanın 97 tokenı tek başına yönlendirildiğinde birkaç ataması düşer. Aynı batch'e saldırganın tekrarlı ' admin' tokenları önce girince aynı uzmanlar dolar ve kurbanın çok daha fazla ataması düşer. Bir kullanıcının girdisi başka bir kullanıcının çıktı kalitesini bozar.

Kabul: iki işlevin farksal taramayı geçmesi; MoE çıktısının torch'tan göreli `1e-5` altında farklı ve seçimlerin aynı olması; dengesizliğin bias güncellemesiyle azalıp 1.5'in altına inmesi; tekrarlı girdide en yüklü uzman payının normal metindekinden büyük olması. Ayrıca kurbanın düşen atama sayısı saldırganın tokenlarıyla artmalıdır.

**Kanıt dosyasını oku:** `yuk_once`, `yuk_sonra`, `son_bias`, `saldiri_yuk`. Soru 1: Bias'ı kapı ağırlığına da ekleseydin çıktı neden bozulurdu? Soru 2: `gama` çok büyük olsaydı yük neden salınırdı? Soru 3: Uzman doyurmaya karşı sunucu tarafında hangi iki önlem alınabilir?
:::

::: gorev Gerçek deney · SmolLM2 gizli durumlarıyla MoE yönlendirme, bias dengeleme ve uzman doyurma
Önceki görevlerdeki `moe_ileri`, `bias_guncelle` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 180
```
```starter
import ai_lab
def moe_ileri(x, ortak_uzmanlar, yonlendirilen_uzmanlar, router_agirliklari, k):
    return {'secilen_uzmanlar': list(range(k)), 'kapi_agirliklari': [round(1.0 / k, 6) for _ in range(k)], 'cikti': [round(float(v), 6) for v in x]}

def bias_guncelle(mevcut_biaslar, uzman_yukleri, gama_adimi):
    return {'ortalama_yuk': 0.0, 'maks_ihlal_orani': 1.0, 'yeni_biaslar': [round(float(b), 6) for b in mevcut_biaslar]}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_05 as D
    D.goster(moe_ileri, bias_guncelle)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('dil_modeli', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
moe_ileri = need("moe_ileri")
bias_guncelle = need("bias_guncelle")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef moe_ileri(x, ortak_uzmanlar, yonlendirilen_uzmanlar, router_agirliklari, k):\n    d = len(x)\n    n_routed = len(yonlendirilen_uzmanlar)\n    logits = [sum((router_agirliklari[i][j] * x[j] for j in range(d))) for i in range(n_routed)]\n    secilenler = sorted(range(n_routed), key=lambda i: (-logits[i], i))[:k]\n    topk_logits = [logits[i] for i in secilenler]\n    max_l = max(topk_logits)\n    exps = [math.exp(z - max_l) for z in topk_logits]\n    toplam_exp = sum(exps)\n    kapi_agirliklari = [e / toplam_exp for e in exps]\n    cikti = []\n    for j in range(d):\n        deger = float(x[j])\n        for ortak in ortak_uzmanlar:\n            deger += ortak[j] * x[j]\n        for idx, g in zip(secilenler, kapi_agirliklari):\n            deger += g * (yonlendirilen_uzmanlar[idx][j] * x[j])\n        cikti.append(round(deger, 6))\n    return {'secilen_uzmanlar': secilenler, 'kapi_agirliklari': [round(g, 6) for g in kapi_agirliklari], 'cikti': cikti}\n\ndef bias_guncelle(mevcut_biaslar, uzman_yukleri, gama_adimi):\n    ort = sum(uzman_yukleri) / len(uzman_yukleri)\n    ihlal = max(uzman_yukleri) / ort if ort > 0 else 1.0\n    yeni_biaslar = []\n    for b, c in zip(mevcut_biaslar, uzman_yukleri):\n        if c > ort + 1e-09:\n            yeni_biaslar.append(round(b - gama_adimi, 6))\n        elif c < ort - 1e-09:\n            yeni_biaslar.append(round(b + gama_adimi, 6))\n        else:\n            yeni_biaslar.append(round(float(b), 6))\n    return {'ortalama_yuk': round(ort, 6), 'maks_ihlal_orani': round(ihlal, 6), 'yeni_biaslar': yeni_biaslar}", 'referans', 'exec'), _REF)
_t, _g = _ff(moe_ileri, _REF['moe_ileri'], ([1.0, 2.0], [[0.5, 0.5]], [[1.0, 0.0], [0.0, 1.0], [2.0, 2.0]], [[1.0, 0.0], [0.0, 2.0], [1.0, 1.0]], 2), tohum=2004, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (moe_ileri): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(bias_guncelle, _REF['bias_guncelle'], ([0.0, 0.0, 0.0, 0.0], [100, 20, 40, 0], 0.01), tohum=2412, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (bias_guncelle): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
kontrol(moe_ileri([1000.0, 0.0], [[0.5, 0.5]], [[1.0, 0.0], [0.0, 1.0], [2.0, 0.0]], [[1.0, 0.0], [0.5, 0.0], [0.2, 0.0]], 2) == _REF['moe_ileri']([1000.0, 0.0], [[0.5, 0.5]], [[1.0, 0.0], [0.0, 1.0], [2.0, 0.0]], [[1.0, 0.0], [0.5, 0.0], [0.2, 0.0]], 2), "MoE top-k büyük logit kararlılığı")
kontrol(bias_guncelle([0.1234567, -0.1234567, 0.2345678], [0, 0, 0], 0.0012345) == _REF['bias_guncelle']([0.1234567, -0.1234567, 0.2345678], [0, 0, 0], 0.0012345), "sıfır toplam yükte ihlal=1.0 ve yuvarlama")
kontrol(bias_guncelle([0.1234567, -0.1234567, 0.2345678], [1, 0, 0], 0.0012344) == _REF['bias_guncelle']([0.1234567, -0.1234567, 0.2345678], [1, 0, 0], 0.0012344), "ortalama yük ve yeni_biaslar 6 basamak yuvarlama")
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_05 as D
try: r = D.deney(moe_ileri, bias_guncelle)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['moe_ayni'], 'MoE ileri geçişi gerçek gizli durumlarda torch referansıyla aynı (seçim ve çıktı)')
kontrol(r['dengeleme_iyilesti'], "bias güncellemesi gerçek yük dengesizliğini azaltıp 1.5'in altına indiriyor")
kontrol(r['saldiri_en_yuklu_pay'] > r['normal_en_yuklu_pay'], 'tekrarlı saldırgan girdisi yükü birkaç uzmana yığıyor')
kontrol(r['saldiri_kurbani_dusurur'], 'kapasite sınırında saldırganın tokenları kurbanın uzman atamalarını düşürdü')
ai_lab.kanit_yaz("ai-uretim-05-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-05", "deney": r})
```
```solution
import ai_lab
import math

def moe_ileri(x, ortak_uzmanlar, yonlendirilen_uzmanlar, router_agirliklari, k):
    d = len(x)
    n_routed = len(yonlendirilen_uzmanlar)
    logits = [sum((router_agirliklari[i][j] * x[j] for j in range(d))) for i in range(n_routed)]
    secilenler = sorted(range(n_routed), key=lambda i: (-logits[i], i))[:k]
    topk_logits = [logits[i] for i in secilenler]
    max_l = max(topk_logits)
    exps = [math.exp(z - max_l) for z in topk_logits]
    toplam_exp = sum(exps)
    kapi_agirliklari = [e / toplam_exp for e in exps]
    cikti = []
    for j in range(d):
        deger = float(x[j])
        for ortak in ortak_uzmanlar:
            deger += ortak[j] * x[j]
        for idx, g in zip(secilenler, kapi_agirliklari):
            deger += g * (yonlendirilen_uzmanlar[idx][j] * x[j])
        cikti.append(round(deger, 6))
    return {'secilen_uzmanlar': secilenler, 'kapi_agirliklari': [round(g, 6) for g in kapi_agirliklari], 'cikti': cikti}

def bias_guncelle(mevcut_biaslar, uzman_yukleri, gama_adimi):
    ort = sum(uzman_yukleri) / len(uzman_yukleri)
    ihlal = max(uzman_yukleri) / ort if ort > 0 else 1.0
    yeni_biaslar = []
    for b, c in zip(mevcut_biaslar, uzman_yukleri):
        if c > ort + 1e-09:
            yeni_biaslar.append(round(b - gama_adimi, 6))
        elif c < ort - 1e-09:
            yeni_biaslar.append(round(b + gama_adimi, 6))
        else:
            yeni_biaslar.append(round(float(b), 6))
    return {'ortalama_yuk': round(ort, 6), 'maks_ihlal_orani': round(ihlal, 6), 'yeni_biaslar': yeni_biaslar}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_05 as D
    D.goster(moe_ileri, bias_guncelle)
```
```hint
Görev 1 ve görev 2 çözümlerini olduğu gibi buraya koy. Deney bias'ı her turda senin bias_guncelle çıktısıyla günceller.
```
:::

::: anlat Sınır
Görevler shared ve top-K routed MoE ileri geçişini ve auxiliary-loss-free bias güncellemesini küçük sayılarla saf Python'da yazdırır; final adım yönlendirmeyi gerçek SmolLM2 gizli durumlarıyla yapar (ön eğitimli bir MoE modeli yoktur; uzmanlar sabit kazançlardır). Dengeleme bias'ı yalnız uzman seçiminde kullanılır, kapı ağırlığına girmez; bu ayrım kaçırılırsa yük dengelenirken çıktı bozulur. Kapasite sınırı ve token düşürme, dağıtık eğitimde expert parallelism iletişimiyle birlikte düşünülmelidir. Yönlendirme girdiye bağlı olduğu için saldırgan kontrollü girdilerle belirli uzmanlar doyurulabilir ve aynı batch'teki başka kullanıcıların tokenları düşebilir (ai-saldiri-61).

Kaynaklar: [Dai vd. 2024 - DeepSeekMoE: Towards Ultimate Expert Specialization in Mixture-of-Experts Language Models](https://arxiv.org/abs/2401.06066), [Wang vd. 2024 - Auxiliary-Loss-Free Load Balancing Strategy for Mixture-of-Experts](https://arxiv.org/abs/2408.15664), [DeepSeek-AI 2024 - DeepSeek-V3 Technical Report](https://arxiv.org/abs/2412.19437).
:::

::: dusun
Sahnede bir sistem mühendisi el kaldırdı:
*"Hocam, `671B` parametreli bir `DeepSeekMoE` modelinde `token` başına sadece `37B` parametre çalıştığı için işlem (`FLOPs`) açısından çok ucuz olduğunu söylediniz. Peki ben bu modeli kendi şirketimin sunucusunda tek bir kullanıcı için (`Batch Size = 1`) çalıştırmak istediğimde neden hala `671B` parametrenin tamamını sığdıracak kadar devasa bir GPU belleğine (`VRAM`) ihtiyaç duyuyorum?"*

Bu soruya **`Compute Cost (FLOPs)` vs `Memory Footprint & Memory Bandwidth (HBM)`**, **tek bir `token` ile `Batch = 128` arasındaki fark** ve **`Expert Offloading / Expert Parallelism`** kavramlarını kullanarak nasıl net bir mühendislik yanıtı verirsin?
:::

::: ozet
- **`Sparse Mixture-of-Experts (MoE)`**, `Transformer` bloklarındaki tek parça yoğun `FFN` katmanını $N$ adet uzman ağa bölerek toplam model kapasitesini (`Total Parameters`) devasa boyutlara taşırken, `token` başına aktif işlem yükünü (`Active Parameters / FLOPs`) düşük tutar.
- **`DeepSeekMoE`**, her `token` için çalışan **`Always-On Shared Experts`** ile ortak bilgi tekrarını (`Knowledge Redundancy`) önler; **`Fine-Grained Routed Experts`** ile uzmanları küçültüp sayısını artırarak kombinatoryal uzmanlaşma gücünü trilyonlarca kombinasyona çıkarır.
- **`Routing Collapse`** (tüm yükün birkaç uzmana yığılıp diğer uzmanların ölmesi) sorununu çözmek için kullanılan eski `Auxiliary Loss` yöntemi ana dil modelleme gradyanlarını bozarken; **`Auxiliary-Loss-Free Load Balancing`** yalnızca `Top-K` seçiminde kullanılan ve gradyan üretmeyen dinamik bir **`Router Bias` ($b_i \leftarrow b_i \pm \gamma$)** güncelleyerek model kalitesinden ödün vermeden kusursuz yük dengesi sağlar.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Toplam kapasite vs aktif maliyet (25 sn).** "Seyrek `MoE`, yoğun `FFN` katmanını çok sayıda uzmana böler; modelin bilgi kapasitesi toplam parametreyle büyürken her token yalnızca seçilen `Top-K` uzmanı çalıştırdığı için işlem yükü düşük kalır."
2. **Paylaşılan ve ince taneli uzmanlar (35 sn).** "`DeepSeekMoE` ortak dilbilgisi ve temel örüntüleri her zaman açık `shared experts` üzerinde toplar; yönlendirilen uzmanları ise daha küçük parçalara bölerek (`fine-grained`) uzman kombinasyonu çeşitliliğini büyütür."
3. **Yardımcı kayıpsız yük dengeleme (35 sn).** "`Routing collapse`'ı önlemek için ana kayba ceza terimi eklemek dil modelleme gradyanlarını bozar; bunun yerine yalnızca seçim adımında kullanılan ve gradyan almayan `router bias` ($b_i \leftarrow b_i \pm \gamma$) fazla yüklü uzmanı frenler."
4. **Soru (25 sn).** "Tek kullanıcılı `batch=1` çıkarımında aktif `FLOPs` düşük olsa bile bütün uzman ağırlıkları neden hâlâ `VRAM` kapasitesini zorlar?"
:::
