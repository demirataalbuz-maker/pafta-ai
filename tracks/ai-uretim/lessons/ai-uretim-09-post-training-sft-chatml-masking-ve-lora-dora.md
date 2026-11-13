---
id: ai-uretim-09
title: "Post-Training Aşama 1: Supervised Fine-Tuning (SFT), ChatML Loss Masking ve LoRA/DoRA"
summary: "Ham Base Model'in ChatML şablonu ve Assistant-Only Loss Masking (labels = -100) ile talimat izleyen bir asistana dönüştürülmesi; LoRA (Low-Rank Adaptation) ve DoRA (Weight-Decomposed Low-Rank Adaptation) mimarilerinin sıfırdan kodlanması."
track: ai-uretim
order: 9
duration_minutes: 35
difficulty: orta
xp: 280
prerequisites: [ai-uretim-08]
esleme: ai-temel-10, ai-uretim-02, ai-uretim-10
tags: [post-training, sft, chatml, loss-masking, lora, dora, peft]
---

::: anlat
## SFT, loss masking ve LoRA

SFT verisinde hangi tokenların loss hesabına katıldığı öğrenme hedefini belirler. Önce assistant-only maskeyi oluşturacak, sonra düşük ranklı LoRA güncellemesini ve DoRA katmanının ileri hesabını inceleyeceksin. Bu parçaların doğru olması, bütün fine-tuning koşusunun doğru veya güvenli olduğunu tek başına göstermez.

Ancak binlerce GPU ile haftalarca eğittiğin bu ham **`Base Model`**'e (`Pre-trained Foundation Model`) şu istemi (`Prompt`) verdiğinde şok edici bir çıktıyla karşılaşırsın:
- **Girdi:** `"Türkiye'nin başkenti neresidir?"`
- **Ham `Base Model` Çıktısı:** `"B) İstanbul C) İzmir D) Bursa. 2. Soru: Fransa'nın başkenti neresidir?..."`

Neden? Çünkü `Base Model` bir "asistan" değildir; internetteki milyarlarca web sayfasını, sınav kitapçığını ve forum yazısını tamamlamak üzere eğitilmiş devasa bir **Belge Tamamlayıcıdır (`Document Completer / Next-Token Predictor`)**! Senin yazdığın cümleyi bir çoktan seçmeli sınav sorusunun başlangıcı sanmış ve sınav kağıdını devam ettirmiştir.

Ham bir `Base Model`'in içindeki muazzam dünya bilgisini ("Knowledge") açığa çıkarmak ve onu kullanıcının talimatlarını izleyen bir asistana dönüştürmek için **Post-Training** boru hattının ilk aşamasına gireriz: **`Supervised Fine-Tuning (SFT)` (Gözetimli İnce Ayar / Instruction Tuning)**.

```
┌────────────────────────────────────────────────────────────────────────────┐
│                  FRONTIER LLM EĞİTİM BORU HATTI (PIPELINE)                 │
├────────────────────────┬─────────────────────────┬─────────────────────────┤
│ 1. PRE-TRAINING        │ 2. SFT (BU DERS)        │ 3. RLHF / DPO / GRPO    │
│ ────────────────────── │ ─────────────────────── │ ─────────────────────── │
│ • 10T+ Ham Web Tokenı  │ • 100K - 1M Yüksek      │ • Tercih Hizalama (DPO) │
│ • Next-Token Prediction│   Kaliteli Diyalog      │ • Doğrulanabilir Ödül   │
│ • Dünya bilgisini      │ • ChatML Özel Tokenları │   ve Düşünme (GRPO/RLVR)│
│   öğrenir ama format   │ • Assistant-Only Loss   │ • Halüsinasyonu azaltır,│
│   ve talimat bilmez.   │   Masking (labels=-100) │   muhakemeyi derinleş-  │
│ • Maliyet: %95 GPU     │ • LoRA / DoRA Adaptörü  │   tirir (Ders 10 & 11). │
└────────────────────────┴─────────────────────────┴─────────────────────────┘
```

---

### 1. Diyalog Protokolü: `ChatML` ve Özel Kontrol Tokenları (`Control Tokens`)

Bir `Transformer` modeli özünde tek boyutlu bir tam sayı (`Token ID`) dizisi alır ve bir sonraki tokenı tahmin eder. Modelin "kimin konuştuğunu", "kullanıcı mesajının nerede bittiğini" ve "asistanın nerede durması gerektiğini (`EOS / End-of-Turn`)" anlaması için sözlüğe (`Vocabulary`) özel kontrol tokenları (`Special Control Tokens`) eklenir.

Endüstride en yaygın kullanılan standart **`ChatML` (Chat Markup Language)** biçimidir:

```
<|im_start|>system
Sen dikkatli bir yapay zeka mühendisisin.<|im_end|>
<|im_start|>user
LoRA nedir?<|im_end|>
<|im_start|>assistant
LoRA, düşük ranklı matris ayrıştırmasıdır.<|im_end|>
```

Burada `<|im_start|>` ve `<|im_end|>` karakter dizisi olarak parçalanmaz; `Tokenizer` tablosunda tek birer atomik `Token ID` (ör. `151644` ve `151645`) olarak temsil edilir. Model `<|im_end|>` tokenını üretmeyi öğrendiği an çıkarım motoru (`Inference Engine`) üretimi durdurur; aksi takdirde model kendi kendine yeni bir `user` sorusu uydurup konuşmaya sonsuza kadar devam eder!

---

### 2. SFT'nin En Kritik Mühendislik Sırrı: `Assistant-Only Loss Masking` (`labels = -100`)

Çok turlu (`Multi-Turn`) bir diyaloğu `SFT` ile eğitirken yapılan en ölümcül acemi hatası, dizideki **bütün tokenlar üzerinden `Cross-Entropy Loss` hesaplamaktır!**

Neden?
- Eğer `system` talimatı ve `user` sorusu üzerindeki tokenlardan da kayıp (`Loss`) hesaplarsan, model kapasitesini **"kullanıcının nasıl soru sorduğunu ezberlemeye"** ve **"sistem komutlarını taklit etmeye"** harcar!
- Biz modelin kullanıcı sorusu üretmesini değil, **verilen `system + user` bağlamına koşullu olarak yalnızca `assistant` yanıtlarını ($\pi_\theta(y_{\text{assistant}} \mid x_{\text{system}}, x_{\text{user}})$) üretmesini** istiyoruz.

Bunun için **`Assistant-Only Loss Masking` (Yalnızca Asistan Kayıp Maskelemesi)** uygulanır:
1. Girdi dizisi `input_ids` modele tam olarak verilir (böylece `Causal Self-Attention` katmanları geçmişteki tüm `system` ve `user` tokenlarını görebilir ve `KV-Cache` bağlamını kurar).
2. Hedef dizisi `labels` oluşturulurken, `system` mesajı, `user` mesajı ve `<|im_start|>assistant\n` başlığına denk gelen tüm konumlara **`-100` (`IGNORE_INDEX`)** atanır!
3. Yalnızca asistanın ürettiği yanıt tokenları ve yanıtı bitiren `<|im_end|>` tokenı gerçek `Token ID` değerlerini korur.

$$\mathcal{L}_{\text{SFT}}(\theta) = -\frac{1}{\sum_{t=1}^{T} \mathbb{I}(y_t \neq -100)} \sum_{t=1}^{T} \mathbb{I}(y_t \neq -100) \cdot \log P_\theta(y_t \mid x_{<t})$$

PyTorch'un `nn.CrossEntropyLoss(ignore_index=-100)` fonksiyonu, hedef değeri `-100` olan konumların kaybını ve gradyanını donanım çekirdeğinde (`CUDA Kernel`) otomatik olarak sıfırlar!

```python
# Çok Turlu ChatML Diyaloğunda Assistant-Only Loss Masking Simülasyonu
diyalog = [
    ("system", ["<|im_start|>system\n", "Net", "cevap", "ver", "<|im_end|>\n"]),
    ("user", ["<|im_start|>user\n", "2+2", "kactir?", "<|im_end|>\n"]),
    ("assistant", ["<|im_start|>assistant\n", "2+2", "=", "4", "eder.", "<|im_end|>\n"]),
]

input_tokens = []
labels = []

for rol, tokenlar in diyalog:
    for i, tok in enumerate(tokenlar):
        input_tokens.append(tok)
        # Yalnızca assistant rolünün başlık (<|im_start|>assistant\n) sonrası yanıt tokenları eğitilir!
        if rol == "assistant" and i > 0:
            labels.append(tok)
        else:
            labels.append(-100)

egitilen = [t for t in labels if t != -100]
maskelenen_oran = round(labels.count(-100) / len(labels) * 100, 1)
print(f"Toplam Token: {len(input_tokens)} | Maskelenen (-100): %{maskelenen_oran}")
print(f"Egitilen Asistan Tokenlari: {egitilen}")
```

Dikkat et: `<|im_start|>assistant\n` başlığı da `-100` ile maskelenir çünkü o başlığı çıkarım anında koda biz ekleriz; ancak asistanın sonundaki `<|im_end|>` tokenı **kesinlikle maskelenmez** çünkü modelin konuşmayı nerede bitireceğini öğrenmesi şarttır!

---

### 3. `LoRA` (Low-Rank Adaptation): Milyarlarca Parametreyi Dondurup %0.1 Parametreyle İnce Ayar Yapmak

70 Milyar parametreli bir modeli **Tam İnce Ayar (`Full Fine-Tuning`)** ile eğitmek istediğinde, `BF16` ağırlıklar ($140\text{ GB}$), gradyanlar ($140\text{ GB}$) ve `FP32 AdamW` (`m` ve `v` momentleri + master ağırlıklar: $840\text{ GB}$) yüzünden **1.1 Terabayt VRAM** gerekir! Üstelik her müşteri veya görev için $140\text{ GB}$'lık ayrı bir model kopyası saklamak imkansızdır.

**Hu et al. (2021)** tarafından geliştirilen **`LoRA (Low-Rank Adaptation)`**, derin öğrenmedeki **`Intrinsic Rank` (İçsel Boyut)** hipotezine dayanır:
> *"Ön-eğitimli devasa bir ağırlık matrisi $W_0 \in \mathbb{R}^{d_{\text{out}} \times d_{\text{in}}}$ ince ayar sırasında güncellendiğinde, oluşan değişim matrisi $\Delta W$'nin bilgi yoğunluğu çok düşük bir rank (`Low-Rank`: $r \ll \min(d_{\text{in}}, d_{\text{out}})$) alt-uzayında toplanır!"*

Bu yüzden $W_0$ matrisini tamamen **dondururuz (`requires_grad = False`)** — yani $W_0$ için `AdamW` durumu tutmayız! Bunun yerine yanına iki ince uzun matris (`Low-Rank Adapter`) ekleriz:
- $A \in \mathbb{R}^{r \times d_{\text{in}}}$ (Aşağı projeksiyon: $d_{\text{in}} \to r$)
- $B \in \mathbb{R}^{d_{\text{out}} \times r}$ (Yukarı projeksiyon: $r \to d_{\text{out}}$)

forward pass (`Forward Pass`) denklemi:

$$h = W_{\text{eff}} x = \left( W_0 + \frac{\alpha}{r} B A \right) x = W_0 x + \frac{\alpha}{r} B(Ax)$$

```
                 h = W_0 x  +  (alpha / r) * B(A x)
                               ▲
               ┌───────────────┴───────────────┐
               │                               │
    ┌──────────┴──────────┐         ┌──────────┴──────────┐
    │   Dondurulmuş W_0   │         │  Eğitilebilir LoRA  │
    │   (d_out x d_in)    │         │  B (d_out x r) = 0  │
    │  4096 x 4096 = 16.7M│         │         ▲           │
    │  requires_grad=False│         │    r=8 darboğazı    │
    │  AdamW belleği: 0 MB│         │         ▲           │
    └──────────▲──────────┘         │  A (r x d_in) ~ N() │
               │                    └──────────▲──────────┘
               └───────────────┬───────────────┘
                               │
                           Girdi (x)
```

#### Neden $A$ Rastgele (`Kaiming/Gaussian`), $B$ İse Tamamen Sıfır (`Zero`) Başlatılır?
- Eğer hem $A$ hem $B$ sıfır başlatılsaydı, zincir kuralı (`Chain Rule`) gereği gradyanlar $\frac{\partial \mathcal{L}}{\partial A} \propto B^T = 0$ olurdu ve eğitim **hiç başlayamazdı (Sıfır Gradyan Kilitlenmesi / Saddle Point)**!
- Eğer hem $A$ hem $B$ rastgele başlatılsaydı, eğitimin ilk adımında (`step = 0`) $\Delta W = BA \neq 0$ olacağı için, trilyonlarca tokenla eğitilmiş `Base Model`'in hassas aktivasyonları rastgele gürültüyle bozulurdu!
- **Çözüm:** $A \sim \mathcal{N}(0, \sigma^2)$ ile rastgele, **$B = 0$** ile sıfır başlatılır. Böylece eğitimin 0. adımında $\Delta W = B A = 0$ olur (`Identity Initialization`: model tam olarak `Base Model` gibi davranır), fakat $A \neq 0$ olduğu için 1. adımda $\frac{\partial \mathcal{L}}{\partial B} = \frac{\partial \mathcal{L}}{\partial h} (Ax)^T \neq 0$ olur ve öğrenme pürüzsüzce başlar!

#### Neden $\frac{\alpha}{r}$ Ölçekleme Çarpanı (`Scaling Factor`) Vardır ve Çıkarım Gecikmesi Neden Sıfırdır (`Zero Inference Latency`)?
- $\alpha$ (`lora_alpha`), adaptörün öğrenme hızını ayarlayan sabittir. Rank $r$'yi $8$'den $32$'ye çıkardığımızda $BA$ çarpımının varyansı $r$ ile orantılı büyür; $\frac{\alpha}{r}$ çarpanı sayesinde yeni bir $r$ denediğimizde `Learning Rate` gibi hiperparametreleri baştan aramamız gerekmez!
- **Çıkarım Anında Sıfır Ek Maliyet (`Weight Merging`):** Eğitim bittiğinde $W_{\text{merged}} = W_0 + \frac{\alpha}{r} BA$ toplamını tek seferlik hesaplayıp doğrudan $W_0$'ın üzerine yazarız! Böylece canlı sunucuda (`Production`) ekstradan tek bir matris çarpımı bile yapılmaz; gecikme (`Latency`) **%0** artar!

---

### 4. `DoRA` (Weight-Decomposed Low-Rank Adaptation — ICML 2024 Oral)

`LoRA` harikadır ancak bazen karmaşık muhakeme görevlerinde `Full Fine-Tuning` performansının biraz gerisinde kalır. **Liu et al. (2024)** bunun nedenini araştırdığında çok derin bir geometrik gerçek keşfetti:
- Bir ağırlık matrisinin her satır (çıktı nöronu) vektörünü **Büyüklük (`Magnitude` $m$)** ve **Birim Yön (`Direction` $V / \|V\|_c$)** olarak ikiye ayırırsak:
  $$W = m \odot \frac{V}{\|V\|_c}$$
- `Full Fine-Tuning` sırasında ağırlıkların **Yönü (`Direction`)** ile **Büyüklüğü (`Magnitude`)** birbirinden bağımsız (hatta ters yönlü) güncellenirken; klasik `LoRA` her ikisini aynı anda değiştirmeye zorlandığı için alt-uzayda sıkışır!

**`DoRA` Çözümü:**
1. Ön-eğitimli $W_0$ matrisinin her satırının Öklid normunu (`L2 Norm`) başlangıç büyüklük vektörü $m \in \mathbb{R}^{d_{\text{out}}}$ olarak ayır ve **eğitilebilir bir vektör** yap ($m^{(0)}_i = \|W_{0, i}\|_2$).
2. Yön matrisini güncellemek için klasik `LoRA` ($\Delta V = \frac{\alpha}{r} BA$) kullan, ancak birleştirmeden önce güncellenmiş yön matrisinin her satırını kendi L2 normuna bölerek **birim yön vektörüne normalize et**:

$$W_{\text{DoRA}} = m \odot \frac{W_0 + \frac{\alpha}{r} B A}{\left\| W_0 + \frac{\alpha}{r} B A \right\|_2}$$

Bu küçük ayrıştırma, yalnızca $d_{\text{out}}$ adet skaler parametre (ör. $4096$ sayı, yani ihmal edilebilir düzeyde!) ekleyerek `LoRA`'nın öğrenme kapasitesini `Full Fine-Tuning` seviyesine çıkarır!

```python
import math

# Saf Python ile Parametre Tasarrufu ve LoRA vs DoRA Karsilastirmasi
d_in, d_out, r = 4096, 4096, 8
w0_param = d_in * d_out
lora_param = r * (d_in + d_out)
dora_param = lora_param + d_out  # + m (magnitude) vektoru

oran_lora = round(lora_param / w0_param * 100, 3)
oran_dora = round(dora_param / w0_param * 100, 3)
print(f"Full W0 Parametre: {w0_param:,}")
print(f"LoRA (r=8) Parametre: {lora_param:,} (%{oran_lora}) -> {w0_param // lora_param}x Tasarruf!")
print(f"DoRA (r=8) Parametre: {dora_param:,} (%{oran_dora})")
```

---

### 5. Gerçek PyTorch Üretim Kodu: `LoRALinear` ve `DoRALinear` Katmanı

Gerçek bir Frontier model eğitim çatısında (`torchtune`, `PEFT`) `LoRA` ve `DoRA` katmanları PyTorch ile şu şekilde inşa edilir:

```python norun
import math
import torch
import torch.nn as nn
import torch.nn.functional as F

class DoRALinear(nn.Module):
    def __init__(self, in_features: int, out_features: int, r: int = 8, alpha: float = 16.0):
        super().__init__()
        self.r = r
        self.scaling = alpha / r

        # 1. Dondurulmuş ön-eğitimli ağırlık matrisi W_0 (out_features x in_features)
        self.weight = nn.Parameter(torch.randn(out_features, in_features) * 0.02, requires_grad=False)

        # 2. LoRA düşük ranklı matrisler: A ~ Kaiming/Gaussian, B = 0
        self.lora_A = nn.Parameter(torch.empty(r, in_features))
        self.lora_B = nn.Parameter(torch.zeros(out_features, r))
        nn.init.kaiming_uniform_(self.lora_A, a=math.sqrt(5))

        # 3. DoRA Magnitude (Büyüklük) vektörü m: Başlangıçta ||W_0||_2 satır normlarına eşittir
        with torch.no_grad():
            init_mag = self.weight.norm(p=2, dim=1, keepdim=True)  # (out_features, 1)
        self.magnitude = nn.Parameter(init_mag, requires_grad=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Güncellenmiş yön matrisi: V' = W_0 + (alpha / r) * (B @ A)
        delta_w = (self.lora_B @ self.lora_A) * self.scaling
        v_prime = self.weight + delta_w

        # Her çıktı satırını L2 normuna bölerek birim yöne normalize et ve m ile ölçekle
        col_norm = v_prime.norm(p=2, dim=1, keepdim=True).clamp(min=1e-8)
        w_dora = self.magnitude * (v_prime / col_norm)
        return F.linear(x, w_dora)
```

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [LoRA makalesi](https://arxiv.org/abs/2106.09685). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: tahmin LoRA Sıfır Başlatma (Zero-Initialization) ve İlk Adım Çıktısı
Aşağıdaki kodda $W_0 = \begin{bmatrix} 2.0 & -1.0 \\ 0.5 & 3.0 \end{bmatrix}$ matrisine $r=1, \alpha=2.0$ ile bir `LoRA` adaptörü eklenmiştir. Standart `LoRA` başlatma kuralına göre $A = [[0.5, 1.5]]$ rastgele değerlerle, $B = [[0.0], [0.0]]$ ise sıfırlarla başlatılmıştır. $x = [2.0, 4.0]$ girdisi için eğitimin 0. adımındaki çıktı ve $B$'nin `[[1.0], [-0.5]]` olarak güncellendiği 1. adım çıktısı nedir?

```python
x = [2.0, 4.0]
W0 = [[2.0, -1.0], [0.5, 3.0]]
A = [[0.5, 1.5]]
B_adim0 = [[0.0], [0.0]]
B_adim1 = [[1.0], [-0.5]]
olcek = 2.0 / 1  # alpha / r

def ileri(B_mat):
     baz = [sum(W0[i][j] * x[j] for j in range(2)) for i in range(2)]
     ax = [sum(A[0][j] * x[j] for j in range(2))]  # 0.5*2 + 1.5*4 = 7.0
     bax = [B_mat[i][0] * ax[0] * olcek for i in range(2)]
     return [round(baz[i] + bax[i], 2) for i in range(2)]

print(f"Adim0={ileri(B_adim0)} | Adim1={ileri(B_adim1)}")
```

???

```cikti
Adim0=[0.0, 13.0] | Adim1=[14.0, 6.0]
```
Eğitimin 0. adımında $B = 0$ olduğu için $\frac{\alpha}{r} B(Ax) = [0.0, 0.0]$ olur ve katman tam olarak dondurulmuş $W_0 x = [2(2) + (-1)(4), 0.5(2) + 3(4)] = [0.0, 13.0]$ çıktısını üretir (`Identity Initialization`). 1. adımda $Ax = 7.0$ ve $\frac{\alpha}{r} = 2.0$ olduğundan $\Delta h = [1.0 \times 14.0, -0.5 \times 14.0] = [14.0, -7.0]$ eklenir ve çıktı `[14.0, 6.0]` olur.
:::

::: gorev 1 · Çok Turlu Diyalogda Assistant-Only Loss Masking ve SFT Kaybı
Bir `Supervised Fine-Tuning (SFT)` eğitim döngüsünde çok turlu diyalogların yalnızca `assistant` yanıtları üzerinden kayıp (`Cross-Entropy Loss`) hesaplayan `sft_maskeli_kayip(diyalog_turlari, token_kayiplari)` işlevini yaz.

**Girdi Kuralları ve Doğrulama:**
- `diyalog_turlari`: Boş olmayan bir `list`. Her elemanı `{"rol": str, "token_sayisi": int}` biçiminde bir `dict` olmalıdır.
  - `"rol"` yalnızca `"system"`, `"user"` veya `"assistant"` olabilir.
  - `"token_sayisi"` `bool` olmayan pozitif bir tam sayı (`>= 1`) olmalıdır.
- `token_kayiplari`: `bool` olmayan, sonlu (`math.isfinite`) ve negatif olmayan (`>= 0.0`) sayılardan (`int` veya `float`) oluşan bir `list`.
- Tüm turlardaki `"token_sayisi"` toplamı, `len(token_kayiplari)` uzunluğuna **tam olarak eşit** olmalıdır.
- Diyalogda en az bir adet `"assistant"` turu bulunmalıdır.

**Hesaplama Kuralları:**
1. Diyalog turlarını sırayla dolaşarak her token için bir maske oluştur:
   - `"system"` ve `"user"` turlarındaki tüm tokenlar maskelenir (`-100` etiketi alır, kayba dahil edilmez).
   - `"assistant"` turlarındaki tüm tokenlar aktiftir (`1` etiketi alır, kayba dahil edilir).
2. `maske`: Aktif tokenlar için `1`, maskelenenler için `-100` içeren tam sayı listesi (`len(token_kayiplari)` uzunluğunda).
3. `aktif_token_sayisi`: Maskede `1` olan (yani `assistant` rolüne ait) toplam token sayısı.
4. `maskeli_ortalama_kayip`: Yalnızca aktif (`assistant`) konumlarındaki `token_kayiplari` değerlerinin aritmetik ortalaması (`float`).
5. `maskesiz_ortalama_kayip`: Tüm dizideki `token_kayiplari` değerlerinin aritmetik ortalaması (`float` — karşılaştırma metriği).
6. İşlev şu sözlüğü döndürmelidir:
   `{"maske": [...], "aktif_token_sayisi": int, "maskeli_ortalama_kayip": float, "maskesiz_ortalama_kayip": float}`
- Geçersiz herhangi bir girdide `ValueError` yükseltilmelidir; girdi listeleri değiştirilmemelidir.

```starter
import math

# KUSURLU BAŞLANGIÇ KODU: Tüm rolleri hesaba katıyor ve maskeleme yapmıyor!
def sft_maskeli_kayip(diyalog_turlari, token_kayiplari):
     ort = sum(token_kayiplari) / len(token_kayiplari)
     return {
         "maske": [1] * len(token_kayiplari),
         "aktif_token_sayisi": len(token_kayiplari),
         "maskeli_ortalama_kayip": ort,
         "maskesiz_ortalama_kayip": ort,
     }

if __name__ == "__main__":
    turlar = [
        {"rol": "system", "token_sayisi": 2},
        {"rol": "user", "token_sayisi": 3},
        {"rol": "assistant", "token_sayisi": 2},
    ]
    kayiplar = [4.5, 3.5, 5.0, 4.0, 3.0, 1.2, 0.8]
    print(sft_maskeli_kayip(turlar, kayiplar))
```
```test
def sinama_sft(f):
    import copy, math, random
    def _ref(turlar, kayiplar):
        maske = []
        aktif_toplam = 0.0
        aktif_sayi = 0
        idx = 0
        for t in turlar:
            rol = t["rol"]
            n = t["token_sayisi"]
            for _ in range(n):
                if rol == "assistant":
                    maske.append(1)
                    aktif_toplam += float(kayiplar[idx])
                    aktif_sayi += 1
                else:
                    maske.append(-100)
                idx += 1
        return {
            "maske": maske,
            "aktif_token_sayisi": aktif_sayi,
            "maskeli_ortalama_kayip": aktif_toplam / aktif_sayi,
            "maskesiz_ortalama_kayip": sum(float(x) for x in kayiplar) / len(kayiplar),
        }
    def _yakin(a, b):
        if not isinstance(a, dict) or set(a.keys()) != {"maske", "aktif_token_sayisi", "maskeli_ortalama_kayip", "maskesiz_ortalama_kayip"}:
            return False
        if a["maske"] != b["maske"] or a["aktif_token_sayisi"] != b["aktif_token_sayisi"] or type(a["aktif_token_sayisi"]) is not int:
            return False
        return abs(a["maskeli_ortalama_kayip"] - b["maskeli_ortalama_kayip"]) < 1e-11 and abs(a["maskesiz_ortalama_kayip"] - b["maskesiz_ortalama_kayip"]) < 1e-11
    try:
        t1 = [{"rol": "system", "token_sayisi": 2}, {"rol": "user", "token_sayisi": 3}, {"rol": "assistant", "token_sayisi": 2}]
        k1 = [4.5, 3.5, 5.0, 4.0, 3.0, 1.2, 0.8]
        old_t, old_k = copy.deepcopy(t1), list(k1)
        r1 = f(t1, k1)
        if t1 != old_t or k1 != old_k or not _yakin(r1, _ref(t1, k1)):
            return False
        if r1["maske"] != [-100, -100, -100, -100, -100, 1, 1] or r1["aktif_token_sayisi"] != 2 or abs(r1["maskeli_ortalama_kayip"] - 1.0) > 1e-11:
            return False

        # Çok turlu diyalog (2 user + 2 assistant)
        t2 = [
            {"rol": "user", "token_sayisi": 2},
            {"rol": "assistant", "token_sayisi": 3},
            {"rol": "user", "token_sayisi": 1},
            {"rol": "assistant", "token_sayisi": 2},
        ]
        k2 = [9.0, 8.0, 1.0, 2.0, 3.0, 7.0, 0.5, 1.5]
        if not _yakin(f(t2, k2), _ref(t2, k2)):
            return False

        rng = random.Random(901)
        for _ in range(20):
            tur_sayisi = rng.randint(2, 6)
            tt = []
            roller = [rng.choice(["system", "user", "assistant"]) for _ in range(tur_sayisi)]
            if "assistant" not in roller:
                roller[-1] = "assistant"
            for r in roller:
                tt.append({"rol": r, "token_sayisi": rng.randint(1, 5)})
            toplam_n = sum(x["token_sayisi"] for x in tt)
            kk = [rng.uniform(0.0, 10.0) for _ in range(toplam_n)]
            if not _yakin(f(copy.deepcopy(tt), list(kk)), _ref(tt, kk)):
                return False

        bad_cases = [
            ([], [1.0]),
            (None, [1.0]),
            ([{"rol": "user", "token_sayisi": 2}], [1.0, 2.0]),  # assistant yok
            ([{"rol": "user", "token_sayisi": 0}, {"rol": "assistant", "token_sayisi": 1}], [1.0]),
            ([{"rol": "bot", "token_sayisi": 1}, {"rol": "assistant", "token_sayisi": 1}], [1.0, 2.0]),
            ([{"rol": "assistant", "token_sayisi": 0}], []),
            ([{"rol": "assistant", "token_sayisi": True}], [1.0]),
            ([{"rol": "assistant", "token_sayisi": 2}], [1.0]),  # uzunluk uyuşmazlığı
            ([{"rol": "assistant", "token_sayisi": 2}], [1.0, -0.5]),  # negatif kayıp
            ([{"rol": "assistant", "token_sayisi": 2}], [1.0, True]),
            ([{"rol": "assistant", "token_sayisi": 2}], [1.0, float("nan")]),
            (["assistant"], [1.0]),
        ]
        for bt, bk in bad_cases:
            try:
                f(bt, bk)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

sft_maskeli_kayip = need("sft_maskeli_kayip")
ok(sinama_sft(sft_maskeli_kayip), "Assistant-Only Loss Masking (-100), çok turlu SFT kaybı ve girdi doğrulaması")
for ad, mut in [
    ("maskesiz ortalama döndüren", lambda t, k: dict(sft_maskeli_kayip(t, k), maskeli_ortalama_kayip=sft_maskeli_kayip(t, k)["maskesiz_ortalama_kayip"])),
    ("tüm toplamtoka bölen", lambda t, k: dict(sft_maskeli_kayip(t, k), maskeli_ortalama_kayip=sum(k[i] for i, m in enumerate(sft_maskeli_kayip(t, k)["maske"]) if m == 1) / len(k))),
    ("0 ile maskeleyen", lambda t, k: dict(sft_maskeli_kayip(t, k), maske=[0 if m == -100 else 1 for m in sft_maskeli_kayip(t, k)["maske"]])),
]:
    ok(not sinama_sft(mut), "mutant reddedildi: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef sft_maskeli_kayip(diyalog_turlari, token_kayiplari):\n    if not isinstance(diyalog_turlari, list) or not diyalog_turlari:\n        raise ValueError('diyalog_turlari boş olmayan bir liste olmalı')\n    if not isinstance(token_kayiplari, list) or not token_kayiplari:\n        raise ValueError('token_kayiplari boş olmayan bir liste olmalı')\n    for k in token_kayiplari:\n        if isinstance(k, bool) or not isinstance(k, (int, float)) or (not math.isfinite(k)) or (k < 0.0):\n            raise ValueError('geçersiz token kaybı')\n    maske = []\n    aktif_toplam = 0.0\n    aktif_sayi = 0\n    idx = 0\n    for tur in diyalog_turlari:\n        if not isinstance(tur, dict) or 'rol' not in tur or 'token_sayisi' not in tur:\n            raise ValueError('geçersiz tur yapısı')\n        rol = tur['rol']\n        n = tur['token_sayisi']\n        if rol not in ('system', 'user', 'assistant'):\n            raise ValueError('geçersiz rol')\n        if isinstance(n, bool) or not isinstance(n, int) or n < 1:\n            raise ValueError('geçersiz token_sayisi')\n        if idx + n > len(token_kayiplari):\n            raise ValueError('token sayısı toplamı kayıp listesini aşıyor')\n        for _ in range(n):\n            if rol == 'assistant':\n                maske.append(1)\n                aktif_toplam += float(token_kayiplari[idx])\n                aktif_sayi += 1\n            else:\n                maske.append(-100)\n            idx += 1\n    if idx != len(token_kayiplari) or aktif_sayi == 0:\n        raise ValueError('uzunluk uyuşmazlığı veya assistant turu eksik')\n    return {'maske': maske, 'aktif_token_sayisi': aktif_sayi, 'maskeli_ortalama_kayip': aktif_toplam / aktif_sayi, 'maskesiz_ortalama_kayip': sum((float(x) for x in token_kayiplari)) / len(token_kayiplari)}", 'referans', 'exec'), _REF)
_t, _g = _ff(sft_maskeli_kayip, _REF['sft_maskeli_kayip'], ([{'rol': 'system', 'token_sayisi': 2}, {'rol': 'user', 'token_sayisi': 3}, {'rol': 'assistant', 'token_sayisi': 2}], [4.5, 3.5, 5.0, 4.0, 3.0, 1.2, 0.8]), tohum=2866, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (sft_maskeli_kayip): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math

def sft_maskeli_kayip(diyalog_turlari, token_kayiplari):
    if not isinstance(diyalog_turlari, list) or not diyalog_turlari:
        raise ValueError("diyalog_turlari boş olmayan bir liste olmalı")
    if not isinstance(token_kayiplari, list) or not token_kayiplari:
        raise ValueError("token_kayiplari boş olmayan bir liste olmalı")

    for k in token_kayiplari:
        if isinstance(k, bool) or not isinstance(k, (int, float)) or not math.isfinite(k) or k < 0.0:
            raise ValueError("geçersiz token kaybı")

    maske = []
    aktif_toplam = 0.0
    aktif_sayi = 0
    idx = 0

    for tur in diyalog_turlari:
        if not isinstance(tur, dict) or "rol" not in tur or "token_sayisi" not in tur:
            raise ValueError("geçersiz tur yapısı")
        rol = tur["rol"]
        n = tur["token_sayisi"]
        if rol not in ("system", "user", "assistant"):
            raise ValueError("geçersiz rol")
        if isinstance(n, bool) or not isinstance(n, int) or n < 1:
            raise ValueError("geçersiz token_sayisi")
        if idx + n > len(token_kayiplari):
            raise ValueError("token sayısı toplamı kayıp listesini aşıyor")
        for _ in range(n):
            if rol == "assistant":
                maske.append(1)
                aktif_toplam += float(token_kayiplari[idx])
                aktif_sayi += 1
            else:
                maske.append(-100)
            idx += 1

    if idx != len(token_kayiplari) or aktif_sayi == 0:
        raise ValueError("uzunluk uyuşmazlığı veya assistant turu eksik")

    return {
        "maske": maske,
        "aktif_token_sayisi": aktif_sayi,
        "maskeli_ortalama_kayip": aktif_toplam / aktif_sayi,
        "maskesiz_ortalama_kayip": sum(float(x) for x in token_kayiplari) / len(token_kayiplari),
    }

if __name__ == "__main__":
    turlar = [
        {"rol": "system", "token_sayisi": 2},
        {"rol": "user", "token_sayisi": 3},
        {"rol": "assistant", "token_sayisi": 2},
    ]
    kayiplar = [4.5, 3.5, 5.0, 4.0, 3.0, 1.2, 0.8]
    print(sft_maskeli_kayip(turlar, kayiplar))
```
```hint
Turları sırayla gezerken bir `idx` sayacı tut; `rol == "assistant"` ise maskeye `1` ekleyip `token_kayiplari[idx]` değerini `aktif_toplam` değişkenine ekle, değilse maskeye `-100` ekle. En sonda `aktif_toplam / aktif_sayi` ile maskeli ortalamayı hesapla.
```
:::

::: gorev 2 · LoRA ve DoRA forward pass Katmanı
Hem klasik `LoRA` birleşimini ($W_{\text{eff}} = W_0 + \frac{\alpha}{r} B A$) hem de `DoRA` satır bazlı birim yön ayrıştırmasını hesaplayan `lora_ileri(x, W0, A, B, alpha, r)` işlevini yaz.

**Girdi Kuralları ve Doğrulama:**
- `x`: Uzunluğu $d_{\text{in}} \ge 1$ olan 1B girdi vektörü (`list` of finite numbers, `bool` hariç).
- `W0`: Boyutu $d_{\text{out}} \times d_{\text{in}}$ ($d_{\text{out}} \ge 1$) olan 2B dondurulmuş temel ağırlık matrisi.
- `A`: Boyutu $r \times d_{\text{in}}$ olan 2B aşağı-projeksiyon matrisi.
- `B`: Boyutu $d_{\text{out}} \times r$ olan 2B yukarı-projeksiyon matrisi.
- `alpha`: `bool` olmayan sonlu pozitif sayı (`> 0`).
- `r`: `bool` olmayan pozitif tam sayı (`>= 1`), ve `len(A) == r` ile `B`'nin her satır uzunluğu `r` olmalıdır.

**Hesaplama Kuralları:**
1. Ölçekleme katsayısı $\text{scale} = \frac{\alpha}{r}$.
2. `temel_cikti`: $W_0 x$ vektörü ($d_{\text{out}}$ elemanlı `float` listesi).
3. `lora_delta_cikti`: $\frac{\alpha}{r} B(Ax)$ vektörü ($d_{\text{out}}$ elemanlı `float` listesi).
4. `lora_cikti`: `temel_cikti` + `lora_delta_cikti` vektörü ($h_{\text{LoRA}} = W_0 x + \frac{\alpha}{r} BAx$).
5. `dora_cikti`:
   - Önce başlangıç büyüklük vektörü $m_i = \|W_{0, i}\|_2 = \sqrt{\sum_{j} W_{0, i, j}^2}$ değerini her satır $i \in \{0, \dots, d_{\text{out}}-1\}$ için hesapla.
   - Güncellenmiş yön matrisi $V'_i = W_{0, i} + \frac{\alpha}{r} (BA)_i$ satırını oluştur ve L2 normunu $\|V'_i\|_2 = \sqrt{\sum_{j} (V'_{i,j})^2}$ bul (eğer $\|V'_i\|_2 == 0$ ise `ValueError` yükselt).
   - Her satır için `DoRA` ağırlığı $W_{\text{DoRA}, i, j} = m_i \cdot \frac{V'_{i, j}}{\|V'_i\|_2}$ ile $x$'in iç çarpımını alarak `dora_cikti` vektörünü ($d_{\text{out}}$ elemanlı `float` listesi) hesapla.
6. İşlev şu sözlüğü döndürmelidir:
   `{"temel_cikti": [...], "lora_delta_cikti": [...], "lora_cikti": [...], "dora_cikti": [...]}`
- Geçersiz herhangi bir girdide veya boyut uyuşmazlığında `ValueError` yükseltilmelidir.

```starter
import math

# KUSURLU BAŞLANGIÇ KODU: alpha/r ölçeklemesini ve DoRA yön normalizasyonunu atlıyor!
def lora_ileri(x, W0, A, B, alpha, r):
     d_out, d_in = len(W0), len(x)
     temel = [sum(W0[i][j] * x[j] for j in range(d_in)) for i in range(d_out)]
     ax = [sum(A[k][j] * x[j] for j in range(d_in)) for k in range(r)]
     delta = [sum(B[i][k] * ax[k] for k in range(r)) for i in range(d_out)]
     lora_c = [temel[i] + delta[i] for i in range(d_out)]
     return {
         "temel_cikti": temel,
         "lora_delta_cikti": delta,
         "lora_cikti": lora_c,
         "dora_cikti": lora_c,
     }

if __name__ == "__main__":
    x_ornek = [1.0, 2.0, -1.0]
    W0_ornek = [[3.0, 0.0, 4.0], [0.0, 2.0, 0.0]]
    A_ornek = [[0.5, -0.5, 1.0]]
    B_ornek = [[2.0], [-1.0]]
    print(lora_ileri(x_ornek, W0_ornek, A_ornek, B_ornek, alpha=2.0, r=1))
```
```test
def sinama_lora(f):
    import copy, math, random
    def _ref(x, W0, A, B, alpha, r):
        d_in = len(x)
        d_out = len(W0)
        sc = float(alpha) / r
        temel = [sum(float(W0[i][j]) * float(x[j]) for j in range(d_in)) for i in range(d_out)]
        ax = [sum(float(A[k][j]) * float(x[j]) for j in range(d_in)) for k in range(r)]
        delta = [sc * sum(float(B[i][k]) * ax[k] for k in range(r)) for i in range(d_out)]
        lora_c = [temel[i] + delta[i] for i in range(d_out)]
        dora_c = []
        for i in range(d_out):
            m_i = math.sqrt(sum(float(W0[i][j]) ** 2 for j in range(d_in)))
            v_satir = [float(W0[i][j]) + sc * sum(float(B[i][k]) * float(A[k][j]) for k in range(r)) for j in range(d_in)]
            v_norm = math.sqrt(sum(val ** 2 for val in v_satir))
            dora_c.append(sum((m_i * v_satir[j] / v_norm) * float(x[j]) for j in range(d_in)))
        return {
            "temel_cikti": temel,
            "lora_delta_cikti": delta,
            "lora_cikti": lora_c,
            "dora_cikti": dora_c,
        }
    def _yakin(a, b):
        keys = {"temel_cikti", "lora_delta_cikti", "lora_cikti", "dora_cikti"}
        if not isinstance(a, dict) or set(a.keys()) != keys:
            return False
        for k in keys:
            if not isinstance(a[k], list) or len(a[k]) != len(b[k]):
                return False
            for u, v in zip(a[k], b[k]):
                if abs(u - v) > 1e-10:
                    return False
        return True
    try:
        x = [1.0, 2.0, -1.0]
        W0 = [[3.0, 0.0, 4.0], [0.0, 2.0, 0.0]]
        A = [[0.5, -0.5, 1.0]]
        B = [[2.0], [-1.0]]
        ox, ow, oa, ob = list(x), copy.deepcopy(W0), copy.deepcopy(A), copy.deepcopy(B)
        res = f(x, W0, A, B, 2.0, 1)
        if x != ox or W0 != ow or A != oa or B != ob or not _yakin(res, _ref(x, W0, A, B, 2.0, 1)):
            return False

        # B = 0 iken LoRA ve DoRA çıktısı temel çıktıya birebir eşit olmalı!
        B_sifir = [[0.0, 0.0], [0.0, 0.0]]
        A_iki = [[1.0, 2.0, 3.0], [-1.0, 0.5, 0.2]]
        res0 = f(x, W0, A_iki, B_sifir, 16.0, 2)
        if not _yakin(res0, _ref(x, W0, A_iki, B_sifir, 16.0, 2)):
            return False
        for i in range(2):
            if abs(res0["lora_cikti"][i] - res0["temel_cikti"][i]) > 1e-12 or abs(res0["dora_cikti"][i] - res0["temel_cikti"][i]) > 1e-12:
                return False

        if f([2.0], [[1.0]], [[0.0]], [[0.0]], 1.0, 1)["dora_cikti"] != [2.0]:
            return False
        rng = random.Random(902)
        for _ in range(20):
            din = rng.randint(2, 5)
            dout = rng.randint(2, 4)
            rr = rng.randint(1, 3)
            alp = rng.uniform(1.0, 32.0)
            xx = [rng.uniform(-3.0, 3.0) for _ in range(din)]
            ww = [[rng.uniform(-2.0, 2.0) for _ in range(din)] for _ in range(dout)]
            aa = [[rng.uniform(-1.0, 1.0) for _ in range(din)] for _ in range(rr)]
            bb = [[rng.uniform(-1.0, 1.0) for _ in range(rr)] for _ in range(dout)]
            if not _yakin(f(xx, ww, aa, bb, alp, rr), _ref(xx, ww, aa, bb, alp, rr)):
                return False

        bad_cases = [
            ([], W0, A, B, 2.0, 1),
            ([1.0], [[1.0]], [[1.0]], [[-1.0]], 1.0, 1),
            ([1.0], [[1.0]], [], [[]], 1.0, 0),
            ([1.0, 2.0], W0, A, B, 2.0, 1),  # d_in uyuşmazlığı
            (x, [], A, B, 2.0, 1),
            (x, W0, [[1.0, 2.0, 3.0]], [[1.0], [2.0]], 2.0, 2),  # r uyuşmazlığı
            (x, W0, A, [[1.0]], 2.0, 1),  # B d_out uyuşmazlığı
            (x, W0, A, B, 0.0, 1),  # alpha <= 0
            (x, W0, A, B, -4.0, 1),
            (x, W0, A, B, True, 1),
            (x, W0, A, B, 2.0, True),
            ([1.0, True, 2.0], W0, A, B, 2.0, 1),
            ([1.0, float("nan"), 2.0], W0, A, B, 2.0, 1),
        ]
        for bx, bw, ba, bb, balp, br in bad_cases:
            try:
                f(bx, bw, ba, bb, balp, br)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

lora_ileri = need("lora_ileri")
ok(sinama_lora(lora_ileri), "LoRA (alpha/r) ölçeklemesi, DoRA satır normu ayrıştırması ve girdi doğrulaması")
for ad, mut in [
    ("alpha/r ölçeğini unutan", lambda x, W0, A, B, alpha, r: lora_ileri(x, W0, A, B, float(r), r)),
    ("DoRA yerine LoRA döndüren", lambda x, W0, A, B, alpha, r: dict(lora_ileri(x, W0, A, B, alpha, r), dora_cikti=lora_ileri(x, W0, A, B, alpha, r)["lora_cikti"])),
    ("m_i büyüklük çarpanını unutan", lambda x, W0, A, B, alpha, r: dict(lora_ileri(x, W0, A, B, alpha, r), dora_cikti=[v * 0.5 for v in lora_ileri(x, W0, A, B, alpha, r)["dora_cikti"]])),
]:
    ok(not sinama_lora(mut), "mutant reddedildi: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef _matris_dogrula(M, satir, sutun):\n    if not isinstance(M, list) or len(M) != satir or satir < 1 or (sutun < 1):\n        raise ValueError('matris boyutu')\n    for s in M:\n        if not isinstance(s, list) or len(s) != sutun:\n            raise ValueError('satır boyutu')\n        for v in s:\n            if not _sayi_mi(v):\n                raise ValueError('matris elemanı sayı değil')\n\ndef lora_ileri(x, W0, A, B, alpha, r):\n    if not isinstance(x, list) or not x or (not all((_sayi_mi(v) for v in x))):\n        raise ValueError('geçersiz x')\n    if isinstance(r, bool) or not isinstance(r, int) or r < 1:\n        raise ValueError('geçersiz r')\n    if not _sayi_mi(alpha) or alpha <= 0.0:\n        raise ValueError('geçersiz alpha')\n    if not isinstance(W0, list) or not W0:\n        raise ValueError('geçersiz W0')\n    d_in = len(x)\n    d_out = len(W0)\n    _matris_dogrula(W0, d_out, d_in)\n    _matris_dogrula(A, r, d_in)\n    _matris_dogrula(B, d_out, r)\n    sc = float(alpha) / r\n    temel = [sum((float(W0[i][j]) * float(x[j]) for j in range(d_in))) for i in range(d_out)]\n    ax = [sum((float(A[k][j]) * float(x[j]) for j in range(d_in))) for k in range(r)]\n    delta = [sc * sum((float(B[i][k]) * ax[k] for k in range(r))) for i in range(d_out)]\n    lora_c = [temel[i] + delta[i] for i in range(d_out)]\n    dora_c = []\n    for i in range(d_out):\n        m_i = math.sqrt(sum((float(W0[i][j]) ** 2 for j in range(d_in))))\n        v_satir = [float(W0[i][j]) + sc * sum((float(B[i][k]) * float(A[k][j]) for k in range(r))) for j in range(d_in)]\n        v_norm = math.sqrt(sum((val ** 2 for val in v_satir)))\n        if v_norm == 0.0:\n            raise ValueError('sıfır yön normu')\n        dora_c.append(sum((m_i * v_satir[j] / v_norm * float(x[j]) for j in range(d_in))))\n    return {'temel_cikti': temel, 'lora_delta_cikti': delta, 'lora_cikti': lora_c, 'dora_cikti': dora_c}", 'referans', 'exec'), _REF)
_t, _g = _ff(lora_ileri, _REF['lora_ileri'], ([1.0, 2.0, -1.0], [[3.0, 0.0, 4.0], [0.0, 2.0, 0.0]], [[0.5, -0.5, 1.0]], [[2.0], [-1.0]], 2.0, 1), tohum=2117, en_cok=600, mod='tam', butce='oto', ekler=[([1.0, 2.0, -1.0], [[3.0, 0.0, 4.0]], [[0.5, -0.5, 1.0]], [[2.0], [-1.0]], 2.0, 1, )])
ok(_t, "farksal tarama (lora_ileri): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math

def _sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def _matris_dogrula(M, satir, sutun):
    if not isinstance(M, list) or len(M) != satir or satir < 1 or sutun < 1:
        raise ValueError("matris boyutu")
    for s in M:
        if not isinstance(s, list) or len(s) != sutun:
            raise ValueError("satır boyutu")
        for v in s:
            if not _sayi_mi(v):
                raise ValueError("matris elemanı sayı değil")

def lora_ileri(x, W0, A, B, alpha, r):
    if not isinstance(x, list) or not x or not all(_sayi_mi(v) for v in x):
        raise ValueError("geçersiz x")
    if isinstance(r, bool) or not isinstance(r, int) or r < 1:
        raise ValueError("geçersiz r")
    if not _sayi_mi(alpha) or alpha <= 0.0:
        raise ValueError("geçersiz alpha")
    if not isinstance(W0, list) or not W0:
        raise ValueError("geçersiz W0")

    d_in = len(x)
    d_out = len(W0)
    _matris_dogrula(W0, d_out, d_in)
    _matris_dogrula(A, r, d_in)
    _matris_dogrula(B, d_out, r)

    sc = float(alpha) / r
    temel = [sum(float(W0[i][j]) * float(x[j]) for j in range(d_in)) for i in range(d_out)]
    ax = [sum(float(A[k][j]) * float(x[j]) for j in range(d_in)) for k in range(r)]
    delta = [sc * sum(float(B[i][k]) * ax[k] for k in range(r)) for i in range(d_out)]
    lora_c = [temel[i] + delta[i] for i in range(d_out)]

    dora_c = []
    for i in range(d_out):
        m_i = math.sqrt(sum(float(W0[i][j]) ** 2 for j in range(d_in)))
        v_satir = [
            float(W0[i][j]) + sc * sum(float(B[i][k]) * float(A[k][j]) for k in range(r))
            for j in range(d_in)
        ]
        v_norm = math.sqrt(sum(val ** 2 for val in v_satir))
        if v_norm == 0.0:
            raise ValueError("sıfır yön normu")
        dora_c.append(sum((m_i * v_satir[j] / v_norm) * float(x[j]) for j in range(d_in)))

    return {
        "temel_cikti": temel,
        "lora_delta_cikti": delta,
        "lora_cikti": lora_c,
        "dora_cikti": dora_c,
    }

if __name__ == "__main__":
    x_ornek = [1.0, 2.0, -1.0]
    W0_ornek = [[3.0, 0.0, 4.0], [0.0, 2.0, 0.0]]
    A_ornek = [[0.5, -0.5, 1.0]]
    B_ornek = [[2.0], [-1.0]]
    print(lora_ileri(x_ornek, W0_ornek, A_ornek, B_ornek, alpha=2.0, r=1))
```
```hint
`lora_delta_cikti` için önce $Ax$ ($r$ boyutlu vektör), ardından $\frac{\alpha}{r} B(Ax)$ hesapla. `DoRA` için her satır $i$'de başlangıç normu $m_i = \|W_{0,i}\|_2$ ve güncellenmiş satır $V'_i = W_{0,i} + \frac{\alpha}{r}(BA)_i$ üzerinden $m_i \frac{V'_i}{\|V'_i\|_2} \cdot x$ çarpımını uygula.
```
:::

::: anlat Gerçek deney: Gerçek ChatML şablonunda maske ve peft'e karşı LoRA/DoRA
Final iki ölçüm yapar (indirme yok):

- **Maske gerçek şablondan:** çok turlu bir destek diyaloğu gerçek **SmolLM2-135M-Instruct** ChatML şablonuyla (`apply_chat_template`) tokenlanır. Tur sınırları elle sayılmaz: şablon her önek için ayrı çalıştırılır ve aradaki fark o turun tokenlarıdır. `<|im_start|>assistant\n` başlığı ve turdan sonraki satır sonu kayıp dışıdır (işlevine `system` rolüyle verilir); asistan içeriği ve `<|im_end|>` eğitilir. Token başına kayıplar modelin kendi çıktısından hesaplanır ve senin maskeli ortalaman Hugging Face'in `labels=-100` kaybıyla karşılaştırılır.
- **Neden önemli:** kullanıcı turunda bir enjeksiyon cümlesi var. Maskesiz SFT bu tokenları da hedef yapar, yani modele kullanıcının yazdığı enjeksiyonu **üretmeyi** öğretir. `<|im_end|>` eğitilmezse model durmayı öğrenmez.
- **LoRA ve DoRA:** 5. katmanın gerçek `q_proj` ağırlığı (576×576) ve gerçek bir gizli durumla, rastgele r=4 `A`/`B` matrisleri hem senin `lora_ileri` işlevine hem de **peft**'in LoRA ve DoRA katmanlarına verilir. Son olarak q/v_proj üzerinde LoRA ile modelin eğitilebilir parametre oranı peft'ten okunur.

Kabul: iki işlevin farksal taramayı geçmesi; maskeli kaybın HF kaybıyla `1e-4` içinde aynı olması; `<|im_end|>` tokenlarının eğitilmesi; LoRA ve DoRA çıktısının peft'ten göreli `1e-6` altında farklı olması.

**Kanıt dosyasını oku:** `turlar`, `egitilen_metin`, `maskeli_kayip`, `maskesiz_kayip`, `lora_goreli_fark`, `dora_goreli_fark`, `egitilebilir_oran`. Soru 1: Maskesiz kayıp neden maskeliden düşük çıkıyor (ipucu: sistem istemi tekrar eden kalıplar içerir)? Soru 2: Tur sınırlarını içerik metnini ayrı tokenlayarak sayan bir kod nerede kayardı? Soru 3: DoRA büyüklüğü neden W0'ın satır normlarıyla başlatılır?
:::

::: gorev Gerçek deney · SmolLM2-Instruct ChatML maskesi ve peft LoRA/DoRA karşılaştırması
Önceki görevlerdeki `sft_maskeli_kayip`, `lora_ileri` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 180
```
```starter
import ai_lab
import math

def sft_maskeli_kayip(diyalog_turlari, token_kayiplari):
    ort = sum(token_kayiplari) / len(token_kayiplari)
    return {'maske': [1] * len(token_kayiplari), 'aktif_token_sayisi': len(token_kayiplari), 'maskeli_ortalama_kayip': ort, 'maskesiz_ortalama_kayip': ort}

import math

def lora_ileri(x, W0, A, B, alpha, r):
    d_out, d_in = (len(W0), len(x))
    temel = [sum((W0[i][j] * x[j] for j in range(d_in))) for i in range(d_out)]
    ax = [sum((A[k][j] * x[j] for j in range(d_in))) for k in range(r)]
    delta = [sum((B[i][k] * ax[k] for k in range(r))) for i in range(d_out)]
    lora_c = [temel[i] + delta[i] for i in range(d_out)]
    return {'temel_cikti': temel, 'lora_delta_cikti': delta, 'lora_cikti': lora_c, 'dora_cikti': lora_c}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_09 as D
    D.goster(sft_maskeli_kayip, lora_ileri)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_turlar', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
sft_maskeli_kayip = need("sft_maskeli_kayip")
lora_ileri = need("lora_ileri")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef sft_maskeli_kayip(diyalog_turlari, token_kayiplari):\n    if not isinstance(diyalog_turlari, list) or not diyalog_turlari:\n        raise ValueError('diyalog_turlari boş olmayan bir liste olmalı')\n    if not isinstance(token_kayiplari, list) or not token_kayiplari:\n        raise ValueError('token_kayiplari boş olmayan bir liste olmalı')\n    for k in token_kayiplari:\n        if isinstance(k, bool) or not isinstance(k, (int, float)) or (not math.isfinite(k)) or (k < 0.0):\n            raise ValueError('geçersiz token kaybı')\n    maske = []\n    aktif_toplam = 0.0\n    aktif_sayi = 0\n    idx = 0\n    for tur in diyalog_turlari:\n        if not isinstance(tur, dict) or 'rol' not in tur or 'token_sayisi' not in tur:\n            raise ValueError('geçersiz tur yapısı')\n        rol = tur['rol']\n        n = tur['token_sayisi']\n        if rol not in ('system', 'user', 'assistant'):\n            raise ValueError('geçersiz rol')\n        if isinstance(n, bool) or not isinstance(n, int) or n < 1:\n            raise ValueError('geçersiz token_sayisi')\n        if idx + n > len(token_kayiplari):\n            raise ValueError('token sayısı toplamı kayıp listesini aşıyor')\n        for _ in range(n):\n            if rol == 'assistant':\n                maske.append(1)\n                aktif_toplam += float(token_kayiplari[idx])\n                aktif_sayi += 1\n            else:\n                maske.append(-100)\n            idx += 1\n    if idx != len(token_kayiplari) or aktif_sayi == 0:\n        raise ValueError('uzunluk uyuşmazlığı veya assistant turu eksik')\n    return {'maske': maske, 'aktif_token_sayisi': aktif_sayi, 'maskeli_ortalama_kayip': aktif_toplam / aktif_sayi, 'maskesiz_ortalama_kayip': sum((float(x) for x in token_kayiplari)) / len(token_kayiplari)}\n\nimport math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef _matris_dogrula(M, satir, sutun):\n    if not isinstance(M, list) or len(M) != satir or satir < 1 or (sutun < 1):\n        raise ValueError('matris boyutu')\n    for s in M:\n        if not isinstance(s, list) or len(s) != sutun:\n            raise ValueError('satır boyutu')\n        for v in s:\n            if not _sayi_mi(v):\n                raise ValueError('matris elemanı sayı değil')\n\ndef lora_ileri(x, W0, A, B, alpha, r):\n    if not isinstance(x, list) or not x or (not all((_sayi_mi(v) for v in x))):\n        raise ValueError('geçersiz x')\n    if isinstance(r, bool) or not isinstance(r, int) or r < 1:\n        raise ValueError('geçersiz r')\n    if not _sayi_mi(alpha) or alpha <= 0.0:\n        raise ValueError('geçersiz alpha')\n    if not isinstance(W0, list) or not W0:\n        raise ValueError('geçersiz W0')\n    d_in = len(x)\n    d_out = len(W0)\n    _matris_dogrula(W0, d_out, d_in)\n    _matris_dogrula(A, r, d_in)\n    _matris_dogrula(B, d_out, r)\n    sc = float(alpha) / r\n    temel = [sum((float(W0[i][j]) * float(x[j]) for j in range(d_in))) for i in range(d_out)]\n    ax = [sum((float(A[k][j]) * float(x[j]) for j in range(d_in))) for k in range(r)]\n    delta = [sc * sum((float(B[i][k]) * ax[k] for k in range(r))) for i in range(d_out)]\n    lora_c = [temel[i] + delta[i] for i in range(d_out)]\n    dora_c = []\n    for i in range(d_out):\n        m_i = math.sqrt(sum((float(W0[i][j]) ** 2 for j in range(d_in))))\n        v_satir = [float(W0[i][j]) + sc * sum((float(B[i][k]) * float(A[k][j]) for k in range(r))) for j in range(d_in)]\n        v_norm = math.sqrt(sum((val ** 2 for val in v_satir)))\n        if v_norm == 0.0:\n            raise ValueError('sıfır yön normu')\n        dora_c.append(sum((m_i * v_satir[j] / v_norm * float(x[j]) for j in range(d_in))))\n    return {'temel_cikti': temel, 'lora_delta_cikti': delta, 'lora_cikti': lora_c, 'dora_cikti': dora_c}", 'referans', 'exec'), _REF)
_t, _g = _ff(sft_maskeli_kayip, _REF['sft_maskeli_kayip'], ([{'rol': 'system', 'token_sayisi': 2}, {'rol': 'user', 'token_sayisi': 3}, {'rol': 'assistant', 'token_sayisi': 2}], [4.5, 3.5, 5.0, 4.0, 3.0, 1.2, 0.8]), tohum=2866, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (sft_maskeli_kayip): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(lora_ileri, _REF['lora_ileri'], ([1.0, 2.0, -1.0], [[3.0, 0.0, 4.0], [0.0, 2.0, 0.0]], [[0.5, -0.5, 1.0]], [[2.0], [-1.0]], 2.0, 1), tohum=2117, en_cok=600, mod='tam', butce='oto', ekler=[([1.0, 2.0, -1.0], [[3.0, 0.0, 4.0]], [[0.5, -0.5, 1.0]], [[2.0], [-1.0]], 2.0, 1, )])
kontrol(_t, "farksal tarama (lora_ileri): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
kontrol(sft_maskeli_kayip([{"rol": "user", "token_sayisi": 1}, {"rol": "assistant", "token_sayisi": 1}], [2.0, 1.0]) == _REF['sft_maskeli_kayip']([{"rol": "user", "token_sayisi": 1}, {"rol": "assistant", "token_sayisi": 1}], [2.0, 1.0]), "token_sayisi=1 geçerli olmalı")
kontrol(lora_ileri([1.0, 2.0], [[1.0, 0.0], [0.0, 1.0]], [[0.5, 0.2], [0.1, 0.3]], [[0.4, 0.1], [0.2, 0.5]], 4.0, 2) == _REF['lora_ileri']([1.0, 2.0], [[1.0, 0.0], [0.0, 1.0]], [[0.5, 0.2], [0.1, 0.3]], [[0.4, 0.1], [0.2, 0.5]], 4.0, 2), "r=2 ölçekleme alpha/r korunmalı")
kontrol(lora_ileri([1.0], [[1.0]], [[0.0]], [[0.0]], 1.0, 1) == _REF['lora_ileri']([1.0], [[1.0]], [[0.0]], [[0.0]], 1.0, 1), "v_norm=1.0 geçerli olmalı")
for _kotu_fn, _kotu_args in [
    (sft_maskeli_kayip, ([{"rol": "assistant", "token_sayisi": True}], [1.0])),
    (sft_maskeli_kayip, ([{"rol": "assistant", "token_sayisi": 0}, {"rol": "assistant", "token_sayisi": 1}], [1.0])),
    (lora_ileri, ([1.0], [[1.0]], [[0.5]], [[0.5]], 1.0, True)),
    (lora_ileri, ([1.0], [[1.0]], [[1.0]], [[-1.0]], 1.0, 1)),
]:
    try:
        _kotu_fn(*_kotu_args)
        kontrol(False, "geçersiz girdi ValueError fırlatmalı")
    except ValueError:
        kontrol(True, "geçersiz girdi ValueError fırlattı")
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_09 as D
try: r = D.deney(sft_maskeli_kayip, lora_ileri)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['maske_ayni'], 'maskeli kayıp gerçek şablonda Hugging Face labels=-100 kaybıyla aynı')
kontrol(r['im_end_egitiliyor'], 'asistan turlarının <|im_end|> tokenı eğitiliyor')
kontrol(r['lora_ayni'] and r['dora_ayni'], "LoRA ve DoRA ileri geçişi gerçek q_proj'da peft ile aynı (göreli fark < 1e-6)")
ai_lab.kanit_yaz("ai-uretim-09-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-09", "deney": r})
```
```solution
import ai_lab
import math

def sft_maskeli_kayip(diyalog_turlari, token_kayiplari):
    if not isinstance(diyalog_turlari, list) or not diyalog_turlari:
        raise ValueError('diyalog_turlari boş olmayan bir liste olmalı')
    if not isinstance(token_kayiplari, list) or not token_kayiplari:
        raise ValueError('token_kayiplari boş olmayan bir liste olmalı')
    for k in token_kayiplari:
        if isinstance(k, bool) or not isinstance(k, (int, float)) or (not math.isfinite(k)) or (k < 0.0):
            raise ValueError('geçersiz token kaybı')
    maske = []
    aktif_toplam = 0.0
    aktif_sayi = 0
    idx = 0
    for tur in diyalog_turlari:
        if not isinstance(tur, dict) or 'rol' not in tur or 'token_sayisi' not in tur:
            raise ValueError('geçersiz tur yapısı')
        rol = tur['rol']
        n = tur['token_sayisi']
        if rol not in ('system', 'user', 'assistant'):
            raise ValueError('geçersiz rol')
        if isinstance(n, bool) or not isinstance(n, int) or n < 1:
            raise ValueError('geçersiz token_sayisi')
        if idx + n > len(token_kayiplari):
            raise ValueError('token sayısı toplamı kayıp listesini aşıyor')
        for _ in range(n):
            if rol == 'assistant':
                maske.append(1)
                aktif_toplam += float(token_kayiplari[idx])
                aktif_sayi += 1
            else:
                maske.append(-100)
            idx += 1
    if idx != len(token_kayiplari) or aktif_sayi == 0:
        raise ValueError('uzunluk uyuşmazlığı veya assistant turu eksik')
    return {'maske': maske, 'aktif_token_sayisi': aktif_sayi, 'maskeli_ortalama_kayip': aktif_toplam / aktif_sayi, 'maskesiz_ortalama_kayip': sum((float(x) for x in token_kayiplari)) / len(token_kayiplari)}

import math

def _sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def _matris_dogrula(M, satir, sutun):
    if not isinstance(M, list) or len(M) != satir or satir < 1 or (sutun < 1):
        raise ValueError('matris boyutu')
    for s in M:
        if not isinstance(s, list) or len(s) != sutun:
            raise ValueError('satır boyutu')
        for v in s:
            if not _sayi_mi(v):
                raise ValueError('matris elemanı sayı değil')

def lora_ileri(x, W0, A, B, alpha, r):
    if not isinstance(x, list) or not x or (not all((_sayi_mi(v) for v in x))):
        raise ValueError('geçersiz x')
    if isinstance(r, bool) or not isinstance(r, int) or r < 1:
        raise ValueError('geçersiz r')
    if not _sayi_mi(alpha) or alpha <= 0.0:
        raise ValueError('geçersiz alpha')
    if not isinstance(W0, list) or not W0:
        raise ValueError('geçersiz W0')
    d_in = len(x)
    d_out = len(W0)
    _matris_dogrula(W0, d_out, d_in)
    _matris_dogrula(A, r, d_in)
    _matris_dogrula(B, d_out, r)
    sc = float(alpha) / r
    temel = [sum((float(W0[i][j]) * float(x[j]) for j in range(d_in))) for i in range(d_out)]
    ax = [sum((float(A[k][j]) * float(x[j]) for j in range(d_in))) for k in range(r)]
    delta = [sc * sum((float(B[i][k]) * ax[k] for k in range(r))) for i in range(d_out)]
    lora_c = [temel[i] + delta[i] for i in range(d_out)]
    dora_c = []
    for i in range(d_out):
        m_i = math.sqrt(sum((float(W0[i][j]) ** 2 for j in range(d_in))))
        v_satir = [float(W0[i][j]) + sc * sum((float(B[i][k]) * float(A[k][j]) for k in range(r))) for j in range(d_in)]
        v_norm = math.sqrt(sum((val ** 2 for val in v_satir)))
        if v_norm == 0.0:
            raise ValueError('sıfır yön normu')
        dora_c.append(sum((m_i * v_satir[j] / v_norm * float(x[j]) for j in range(d_in))))
    return {'temel_cikti': temel, 'lora_delta_cikti': delta, 'lora_cikti': lora_c, 'dora_cikti': dora_c}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_09 as D
    D.goster(sft_maskeli_kayip, lora_ileri)
```
```hint
İki görevin çözümlerini olduğu gibi buraya koy. Deney tur listesini şablondan kendisi çıkarır.
```
:::

::: anlat Sınır
Görevler çok turlu diyalogda yalnız asistan tokenlarına kayıp maskelemeyi ve LoRA/DoRA ileri geçişini saf Python ile yazdırır; final adım maskeyi gerçek SmolLM2-Instruct ChatML şablonunda, LoRA/DoRA'yı peft'e karşı sınar; gerçek ince ayar yapılmaz. Şablonda tek bir token kayarsa maske yanlış yere düşer ve model kullanıcı ya da sistem metnini üretmeyi öğrenir; maske gerçek tokenizer çıktısında denetlenmelidir. LoRA rank'ı ve hedef modül seçimi kaliteyi belirler; düşük rank yeni bilgi öğretmekte zayıf kalır. Az sayıda örnekle yapılan ince ayar bile modelin önceden kazandığı güvenlik davranışını bozabilir.

Kaynaklar: [Hu vd. 2021 - LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685), [Liu vd. 2024 - DoRA: Weight-Decomposed Low-Rank Adaptation](https://arxiv.org/abs/2402.09353), [Ouyang vd. 2022 - Training language models to follow instructions with human feedback](https://arxiv.org/abs/2203.02155).
:::

::: dusun
Bir üretim ortamında **tek bir 70B `Base Model`** kullanarak aynı anda **50 farklı kurumsal müşteriye** (hukuk, tıp, finans, siber güvenlik vb.) kişiselleştirilmiş yapay zeka servisi vermek istiyorsun (`Multi-Tenant LoRA Serving / S-LoRA`).

Eğer `Full Fine-Tuning` yapsaydın $50 \times 140\text{ GB} = 7\text{ TB}$ GPU belleği gerekirdi! Oysa `LoRA` kullandığında GPU belleğinde ($140\text{ GB}$) yalnızca **1 adet dondurulmuş $W_0$** tutarsın ve 50 müşterinin her biri sadece $100\text{ MB}$'lık kendi $(A_k, B_k)$ adaptör çiftine sahip olur.
**Tasarım Sorusu:** Aynı GPU `Batch` içinde 1. istek Hukuk adaptörünü $(A_1, B_1)$, 2. istek Tıp adaptörünü $(A_2, B_2)$ kullanıyorsa, ağırlıkları $W_0$'ın içine kalıcı olarak birleştiremezsin (`Weight Merging` yapamazsın). Bu durumda `Batch` içindeki matris çarpımını $Y = X W_0^T + \text{BatchLoRA}(X, A_{\text{id}}, B_{\text{id}})$ şeklinde nasıl hesaplarsın?
:::

::: ozet
- Ham **`Base Model`** yalnızca belge tamamlayıcıdır (`Next-Token Predictor`); onu talimat izleyen bir asistana dönüştürmek için **`ChatML`** kontrol tokenları (`<|im_start|>`, `<|im_end|>`) ve **`Supervised Fine-Tuning (SFT)`** uygulanır.
- **`Assistant-Only Loss Masking` (`labels = -100`):** Çok turlu diyaloglarda modelin kullanıcı sorularını ezberlemesini önlemek için `system` ve `user` tokenları `-100` (`ignore_index`) ile maskelenir; yalnızca `assistant` yanıtları ve bitiş `<|im_end|>` tokenı üzerinden `Cross-Entropy Loss` hesaplanır.
- **`LoRA (Low-Rank Adaptation)`:** Dondurulmuş $W_0$ matrisinin yanına $\Delta W = \frac{\alpha}{r} B A$ düşük ranklı adaptör ekler. $A$ rastgele, $B = 0$ başlatılarak 0. adımda `Base Model` davranışı korunur ve eğitim sonunda ağırlıklar birleştirilerek (`Weight Merging`) çıkarım gecikmesi (`Inference Latency`) sıfıra indirilir.
- **`DoRA (Weight-Decomposed Low-Rank Adaptation)`:** Ağırlık matrisini büyüklük ($m = \|W_0\|_2$) ve birim yön ($V' / \|V'\|_2$) bileşenlerine ayırarak `LoRA`'nın öğrenme dinamiklerini `Full Fine-Tuning` seviyesine taşır.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Yalnız asistan kaybı (`labels = -100`) (30 sn).** "Çok turlu `ChatML` eğitiminde `system` ve `user` tokenları `-100` ile maskelenir; aksi hâlde model kullanıcının sorusunu ve içindeki olası enjeksiyon metnini üretmeyi öğrenir, `<|im_end|>` eğitilmezse de yanıtı nerede keseceğini bilemez."
2. **`LoRA` düşük ranklı güncelleme (30 sn).** "Dondurulmuş $W_0$'ın yanına $\frac{\alpha}{r}BA$ eklenir; $B=0$ başlatıldığı için ilk adımda taban model korunur, eğitim sonunda da $W_0 + \frac{\alpha}{r}BA$ tek matriste birleştirilerek ek çıkarım gecikmesi sıfırlanır."
3. **`DoRA` yön-büyüklük ayrımı (35 sn).** "Ağırlık satırlarını büyüklük $m_i$ ve birim yön $V'_i / \|V'_i\|_2$ olarak ayırmak, düşük ranklı güncellemenin tam ince ayardaki yön-büyüklük dengesini daha yakından izlemesini sağlar."
4. **Soru (25 sn).** "Paylaşılan tek bir taban model üstünde onlarca kiracıya ayrı `LoRA` adaptörü sunarken ağırlıkları kalıcı birleştirmek (`merge`) neden uygun değildir?"
:::
