---
id: ai-uretim-26
title: "Görsel Anlama (VLM) İnşası: CLIP/SigLIP Contrastive Pre-Training ve AnyRes Dynamic Tiling"
summary: "Görüntü ve metin uzaylarını hizalayan CLIP (Symmetric InfoNCE) ve SigLIP (Sigmoid Pairwise Contrastive Loss) matematiği; yüksek çözünürlüklü belge/ekran görüntülerini bulanıklaştırmadan işleyen AnyRes Dynamic Tiling ve Pixel Unshuffle sıkıştırması."
esleme: ai-uretim-28, ai-temel-02, ai-saldiri-13
track: ai-uretim
order: 26
duration_minutes: 40
difficulty: ileri
xp: 310
prerequisites: [ai-uretim-25]
tags: [vlm, clip, siglip, contrastive-learning, anyres, pixel-unshuffle]
---

::: anlat
## Görsel ve metin temsillerini eşleştirme

CLIP/SigLIP türü hedefler görsel ve metin temsilini eşleştirmeyi öğretir. Bu derste loss hesabını ve görselleri tile/patch biçiminde yerleştirmenin token maliyetini hesaplayacaksın. Küçük bir loss uygulaması, eğitilmiş bir VLM veya genel görsel anlama kabulü değildir.

```
┌────────────────────────────────────────────────────────────────────────────┐
│              MODERN VLM GÖRSEL KODLAYICI VE ANYRES MİMARİSİ                │
├────────────────────────┬─────────────────────────┬─────────────────────────┤
│ 1. CLIP vs SigLIP      │ 2. ANYRES DYNAMIC       │ 3. 2D PIXEL UNSHUFFLE   │
│    CONTRASTIVE LOSS    │    TILING (LLaVA-NeXT)  │    (Token Sıkıştırma)   │
│ ────────────────────── │ ─────────────────────── │ ─────────────────────── │
│ • CLIP: NxN matrisin   │ • Görüntünün en-boy     │ • 5 karo x 576 yama =   │
│   satır ve sütunlarında│   oranına en uygun      │   2880 görsel token!    │
│   Softmax (InfoNCE)    │   ızgarayı (ör. 2x2,    │ • 2x2 komşu yamaları    │
│   -> Tüm GPU'lar arası │   1x3) dinamik seçer.   │   kanal boyutunda       │
│   All-Gather şart!     │ • Net yerel karolar     │   birleştirip (4xd)     │
│ • SigLIP: Her (i, j)   │   (Local Crops) +       │   MLP ile d_model'e     │
│   çiftini bağımsız     │   1 adet Global         │   indirger -> Token     │
│   Sigmoid ikili sınıfl.│   Thumbnail üretir!     │   sayısı 4 kat azalır!  │
└────────────────────────┴─────────────────────────┴─────────────────────────┘
```

---

### 1. `CLIP` (Symmetric InfoNCE) vs `SigLIP` (Sigmoid Pairwise Contrastive Loss)

Elbette milyarlarca görüntüyü tek tek elle etiketleyemeyiz. Bunun yerine bir yığın (`Batch`) içinde $N$ adet `(Görüntü, Metin)` çifti $\{(I_1, T_1), \dots, (I_N, T_N)\}$ alırız.
- Görüntü kodlayıcı her görüntüyü L2-normalize edilmiş bir birim vektöre dönüştürür: $\hat{u}_i = \frac{f(I_i)}{\|f(I_i)\|_2}$.
- Metin kodlayıcı her metni L2-normalize edilmiş bir birim vektöre dönüştürür: $\hat{v}_j = \frac{g(T_j)}{\|g(T_j)\|_2}$.
- Böylece $N \times N$ boyutlu **Kosinüs Benzerlik Matrisi (`Cosine Similarity Matrix`)** $S_{i,j} = \hat{u}_i \cdot \hat{v}_j \in [-1, 1]$ oluşur! Köşegen elemanları ($i = j$) **gerçek eşleşmeler (Pozitif Çiftler)**, köşegen dışı tüm elemanlar ($i \neq j$, toplam $N^2 - N$ adet) ise **sahte eşleşmelerdir (Negatif Çiftler)**.

#### A) `CLIP` (Radford et al., 2021 — Symmetric InfoNCE / Softmax Loss)
`CLIP`, her satırı (Görüntü $\to$ Metin) ve her sütunu (Metin $\to$ Görüntü) $N$ sınıflı bir `Softmax Cross-Entropy` problemi olarak çözer:

$$\mathcal{L}_{\text{CLIP}} = -\frac{1}{2N} \sum_{i=1}^{N} \left( \log \frac{\exp(t \cdot S_{i,i})}{\sum_{j=1}^{N} \exp(t \cdot S_{i,j})} + \log \frac{\exp(t \cdot S_{i,i})}{\sum_{j=1}^{N} \exp(t \cdot S_{j,i})} \right)$$

**CLIP'in Dağıtık Sistem Darboğazı:** Paydadaki $\sum_{j=1}^N \exp(t \cdot S_{i,j})$ toplamını hesaplamak için $32,768$ boyutlu global yığındaki tüm vektörlerin tüm GPU'lar arasında senkronize edilmesi (`All-Gather`) ve devasa $32768 \times 32768$ matrisin bellekte tutulması gerekir!

#### B) `SigLIP` (Zhai et al., ICCV 2023 — Sigmoid Loss for Language Image Pre-Training)
Google DeepMind araştırmacıları şunu sordu: *"Neden satır/sütun boyunca global `Softmax` normalizasyonu yapmak zorundayız? Her $(i, j)$ çiftini bağımsız bir **İkili Lojistik Regresyon (`Binary Sigmoid Classification`)** olarak çözsek ne olur?"*

Etiket matrisi $y_{i,j}$: köşegen üzerinde ($i = j$) **$+1$**, köşegen dışında ($i \neq j$) **$-1$** olarak tanımlanır. Öğrenilebilir bir sıcaklık $t > 0$ ve başlangıçta negatif çiftlerin baskınlığını dengeleyen bir önyargı (`bias` $b$, örn. $b = -10.0$) ile **`SigLIP Loss`**:

$$z_{i,j} = y_{i,j} \cdot \left( t \cdot (\hat{u}_i \cdot \hat{v}_j) + b \right)$$

$$\mathcal{L}_{\text{SigLIP}} = -\frac{1}{N^2} \sum_{i=1}^{N} \sum_{j=1}^{N} \log \sigma(z_{i,j}) = \frac{1}{N^2} \sum_{i=1}^{N} \sum_{j=1}^{N} \log \left( 1 + \exp(-z_{i,j}) \right)$$

**Neden `SigLIP` Önemlidir?**
1. Hiçbir satır veya sütun toplamına (`Global Normalization`) ihtiyaç duymaz! Her $(i, j)$ çifti bağımsızdır; GPU'lar arası bellek trafiği parçalanabilir (`Chunked Ring Communication`).
2. Negatif çift sayısı $N(N-1)$ pozitif çift sayısından ($N$) çok daha fazla olduğu için, eğitimin ilk adımında modelin devasa bir gradyan patlaması yaşamaması adına $b \approx -10.0$ başlatılır (böylece başlangıçta model her çifte "negatif" der ve hızla dengelenir).

```python
import math

# 2x2 Yığın (N=2) için SigLIP ve CLIP Kaybı Karşılaştırması
# İki mükemmel hizalı birim vektör çifti: u0=[1, 0], v0=[1, 0] ve u1=[0, 1], v1=[0, 1]
S = [[1.0, 0.0], [0.0, 1.0]]
t, b = 10.0, -5.0

# SigLIP: i==j için y=+1, i!=j için y=-1
siglip_toplam = 0.0
for i in range(2):
    for j in range(2):
        y_ij = 1.0 if i == j else -1.0
        z_ij = y_ij * (t * S[i][j] + b)
        siglip_toplam += math.log1p(math.exp(-z_ij))
siglip_loss = round(siglip_toplam / 4.0, 4)

# CLIP: Satır bazlı Softmax Cross-Entropy
clip_satir0 = -math.log(math.exp(t * 1.0) / (math.exp(t * 1.0) + math.exp(t * 0.0)))
print(f"SigLIP Loss={siglip_loss} | CLIP Loss={round(clip_satir0, 6)}")
```

---

### 2. `AnyRes (Dynamic High-Resolution Tiling)` ve `2D Pixel Unshuffle`

Ön-eğitimli bir `SigLIP / CLIP ViT` modeli genellikle sabit $336 \times 336$ (veya $384 \times 384$) çözünürlükte çalışır. Eğer kullanıcı modele $1344 \times 672$ boyutunda geniş bir ekran görüntüsü verirse ve sen bunu doğrudan $336 \times 336$ kareye sıkıştırırsan:
- En-boy oranı (`Aspect Ratio`) ezilir,
- Ekrandaki küçük harfler 1 pikselin altına düşüp okunaksız hale gelir (**`OCR Hallucination`**)!

**`AnyRes (Dynamic High-Resolution Tiling — LLaVA-NeXT / InternVL / Qwen2-VL)`** bu sorunu 3 adımda çözer:
1. **En Uygun Izgara Seçimi (`Optimal Grid Selection`):**
   - Her bir karonun (`Tile`) boyutu $T \times T$ (ör. $T = 336$) olsun. Aday ızgaralar kümesi $\mathcal{G} = \{(r, c)\}$ (örn. `(1,1), (1,2), (2,1), (2,2), (1,3), (3,1)`).
   - Orijinal görüntüyü ($W \times H$) en-boy oranını bozmadan (`Aspect-Ratio Preserving Scale`) $(r, c)$ ızgarasının çözünürlüğüne ($W_{\text{grid}} = c \cdot T, \; H_{\text{grid}} = r \cdot T$) sığdırdığımızda oluşacak:
     - **Etkin Görüntü Alanı (`Effective Resolution Area`):** $\text{scale} = \min(W_{\text{grid}} / W, \; H_{\text{grid}} / H)$, etkin alan $A_{\text{eff}} = \min(\text{scale}, 1.0)^2 \cdot W \cdot H$ (veya ölçeklenmiş piksel alanı $\lfloor W \cdot \text{scale}\rfloor \times \lfloor H \cdot \text{scale}\rfloor$).
     - **Boş Dolgu İsrafı (`Wasted Padding Area`):** $A_{\text{pad}} = (W_{\text{grid}} \cdot H_{\text{grid}}) - A_{\text{scaled}}$.
   - Orijinal görüntüyü en çok kapsayan (maksimum etkin çözünürlük) ve en az boş dolgu (`Padding`) bırakan $(r^*, c^*)$ ızgarası seçilir!
2. **Yerel Karolar + Global Önizleme (`Local Tiles + Global Thumbnail`):**
   - Görüntü $r^* \times c^*$ adet yüksek çözünürlüklü karoya bölünür (`Local Crops` — küçük yazıları net okumak için).
   - Ayrıca tüm görüntünün $T \times T$ boyutuna küçültülmüş **1 adet `Global Thumbnail`** kopyası eklenir (modelin sahnenin genel bütünü ve karolar arası ilişkileri kaybetmemesi için!). Toplam işlenen görüntü sayısı: $(r^* \cdot c^* + 1)$!
3. **`2D Pixel Unshuffle` (Uzamsal Token Sıkıştırma):**
   - Her $336 \times 336$ karo, $14 \times 14$ yama boyutuyla $(336/14)^2 = 24 \times 24 = 576$ görsel token üretir. 5 karo $\times 576 = 2880$ token çok fazladır!
   - **`Pixel Unshuffle` ($2 \times 2 \to 1$):** Yan yana duran $2 \times 2 = 4$ yamanın öznitelik vektörleri ($d$) kanal boyutunda uç uca eklenir ($4d$) ve doğrusal bir katmanla tekrar $d_{\text{model}}$ boyutuna indirilir. Böylece uzamsal bilgi kaybolmadan **görsel token sayısı tam 4 kat (%75) azaltılır** ($576 \to 144$ token/karo)!

---

### 3. Gerçek PyTorch Üretim Kodu: `SigLIPLoss` ve `PixelUnshuffleProjector`

Gerçek bir `VLM` eğitim çatısında `SigLIP` kaybı ve `2D Pixel Unshuffle` sıkıştırma modülü PyTorch ile şu şekilde inşa edilir:

```python norun
import torch
import torch.nn as nn
import torch.nn.functional as F

class SigLIPContrastiveLoss(nn.Module):
    def __init__(self, init_temp: float = 10.0, init_bias: float = -10.0):
        super().__init__()
        self.log_temp = nn.Parameter(torch.tensor(init_temp).log())
        self.bias = nn.Parameter(torch.tensor(init_bias))

    def forward(self, img_embeds: torch.Tensor, txt_embeds: torch.Tensor) -> torch.Tensor:
        # 1. Birim küreye L2 normalizasyonu: (B, D)
        img_norm = F.normalize(img_embeds, p=2, dim=-1)
        txt_norm = F.normalize(txt_embeds, p=2, dim=-1)

        # 2. Kosinüs benzerlik logitleri: t * (U @ V^T) + b -> (B, B)
        logits = (img_norm @ txt_norm.T) * self.log_temp.exp() + self.bias

        # 3. Köşegen +1, köşegen dışı -1 etiket matrisi
        b_size = img_embeds.size(0)
        labels = 2.0 * torch.eye(b_size, device=img_embeds.device) - 1.0

        # 4. Pairwise Sigmoid Loss: -mean(log_sigmoid(labels * logits))
        return -F.logsigmoid(labels * logits).mean()

class PixelUnshuffleConnector(nn.Module):
    def __init__(self, d_vision: int = 1024, d_model: int = 4096, scale_factor: int = 2):
        super().__init__()
        self.scale = scale_factor
        self.mlp = nn.Sequential(
            nn.Linear(d_vision * (scale_factor ** 2), d_model),
            nn.GELU(),
            nn.Linear(d_model, d_model),
        )

    def forward(self, x: torch.Tensor, h_patches: int, w_patches: int) -> torch.Tensor:
        # x: (Batch, H * W, D) -> 2x2 komşu yamaları kanal boyutunda birleştir: (Batch, H/2 * W/2, 4*D)
        b, _, d = x.shape
        s = self.scale
        x = x.view(b, h_patches // s, s, w_patches // s, s, d)
        x = x.permute(0, 1, 3, 2, 4, 5).contiguous()
        x = x.view(b, (h_patches // s) * (w_patches // s), d * (s ** 2))
        return self.mlp(x)
```

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [CLIP makalesi](https://arxiv.org/abs/2103.00020). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: tahmin AnyRes Tiling + Global Thumbnail + Pixel Unshuffle Token Hesabı
Bir VLM'de karo boyutu $T = 336$, yama boyutu $P = 14$'tür (yani her karo $(336/14)^2 = 576$ ham yama üretir). Yüksek çözünürlüklü bir görüntü için `2x2` ızgarası seçilmiş ve buna **1 adet `Global Thumbnail`** eklenmiştir. Ardından $2 \times 2$ **`Pixel Unshuffle`** sıkıştırması (token sayısını 4'e bölen) uygulanmıştır. LLM'e gönderilen nihai toplam görsel token sayısı kaçtır?

```python
karo_boyutu = 336
yama_boyutu = 14
izgara_satir, izgara_sutun = 2, 2

karo_basina_ham_yama = (karo_boyutu // yama_boyutu) ** 2  # 24 * 24 = 576
toplam_karo = (izgara_satir * izgara_sutun) + 1           # 4 yerel karo + 1 Global Thumbnail = 5
ham_toplam_token = toplam_karo * karo_basina_ham_yama
sikistirilmis_token = ham_toplam_token // 4               # 2x2 Pixel Unshuffle (4x sıkıştırma)

print(f"HamToken={ham_toplam_token} | PixelUnshuffleSonrasi={sikistirilmis_token}")
```

???

```cikti
HamToken=2880 | PixelUnshuffleSonrasi=720
```
Her $336 \times 336$ karo $(336/14)^2 = 576$ yama üretir. `2x2` yerel ızgara (`4` karo) + `1` `Global Thumbnail` ile toplam `5` karo oluşur ve ham yama sayısı $5 \times 576 = 2880$ olur. $2 \times 2$ `Pixel Unshuffle` her 4 komşu yamayı 1 tokenda birleştirdiği için nihai görsel token sayısı $2880 / 4 = 720$'ye düşer.
:::

::: gorev 1 · CLIP (InfoNCE) ve SigLIP (Sigmoid) Karşılaştırmalı Görüntü-Metin Kaybı
Bir yığın (`Batch`, boyut $N \ge 2$) içindeki görüntü ve metin embedding vektörlerini L2-normalize ederek hem **`SigLIP` (Pairwise Sigmoid Loss)** hem de **`CLIP` (Symmetric InfoNCE Softmax Loss)** kaybını hesaplayan `siglip_kayip_hesapla(goruntu_vektorleri, metin_vektorleri, sicaklik_t, bias_b)` işlevini yaz.

**Girdi Kuralları ve Doğrulama:**
- `goruntu_vektorleri` ve `metin_vektorleri`: Boyutu $N \times D$ ($N \ge 2, D \ge 1$) olan 2B sayı matrisleri (elemanları `bool` olmayan sonlu sayılar).
- Her bir vektörün L2 normu sıfırdan büyük olmalıdır ($\|u_i\|_2 > 0$ ve $\|v_j\|_2 > 0$; sıfır vektörü varsa `ValueError` yükselt).
- `sicaklik_t`: Sıcaklık çarpanı $t > 0$ (`bool` olmayan sonlu pozitif sayı).
- `bias_b`: `SigLIP` önyargı terimi $b$ (`bool` olmayan sonlu sayı).

**Hesaplama Kuralları:**
1. Her görüntü vektörü $u_i$ ve metin vektörü $v_j$'yi kendi L2 normuna bölerek birim vektörlere ($\hat{u}_i, \hat{v}_j$) dönüştür.
2. $N \times N$ **Kosinüs Benzerlik Matrisi** `kosinus_matrisi` oluştur: $S_{i,j} = \sum_{k=0}^{D-1} \hat{u}_{i,k} \cdot \hat{v}_{j,k}$.
3. **`siglip_kaybi`:**
   - Her $(i, j) \in \{0, \dots, N-1\}^2$ çifti için $y_{i,j} = +1.0$ (eğer $i == j$) veya $-1.0$ (eğer $i \neq j$).
   - $z_{i,j} = y_{i,j} \cdot (t \cdot S_{i,j} + b)$
   - $\mathcal{L}_{\text{SigLIP}} = \frac{1}{N^2} \sum_{i=0}^{N-1} \sum_{j=0}^{N-1} -\log \sigma(z_{i,j})$ (sayısal kararlı `log_sigmoid` ile).
4. **`clip_kaybi`:**
   - Ölçekli logit matrisi $L_{i,j} = t \cdot S_{i,j}$.
   - Satır bazlı (Görüntü $\to$ Metin) ortalama `Cross-Entropy` kaybı $\mathcal{L}_{I \to T}$ ve sütun bazlı (Metin $\to$ Görüntü) ortalama `Cross-Entropy` kaybı $\mathcal{L}_{T \to I}$'nın aritmetik ortalaması: $\mathcal{L}_{\text{CLIP}} = \frac{1}{2}(\mathcal{L}_{I \to T} + \mathcal{L}_{T \to I})$.
5. **`top1_dogruluk`:** Her görüntü satırı $i$ için en yüksek kosinüs benzerliğine sahip metin sütunu $\arg\max_j S_{i,j}$ (eşitlikte en küçük indis) doğru eşleşme ($j == i$) ise `1`, değilse `0` sayılarak elde edilen oran (`float`).
6. İşlev şu sözlüğü döndürmelidir:
   `{"kosinus_matrisi": [[...], ...], "siglip_kaybi": float, "clip_kaybi": float, "top1_dogruluk": float}`
- Geçersiz herhangi bir girdide `ValueError` yükseltilmelidir.

```starter
import math

# KUSURLU BAŞLANGIÇ KODU: L2 normalizasyonu yapmıyor ve SigLIP/CLIP kayıplarını yanlış hesaplıyor!
def siglip_kayip_hesapla(goruntu_vektorleri, metin_vektorleri, sicaklik_t, bias_b):
     n = len(goruntu_vektorleri)
     d = len(goruntu_vektorleri[0])
     S = [[sum(goruntu_vektorleri[i][k] * metin_vektorleri[j][k] for k in range(d)) for j in range(n)] for i in range(n)]
     return {
         "kosinus_matrisi": S,
         "siglip_kaybi": 1.0,
         "clip_kaybi": 1.0,
         "top1_dogruluk": 1.0,
     }

img_v = [[3.0, 0.0], [0.0, 4.0]]
txt_v = [[5.0, 0.0], [0.0, 2.0]]
print(siglip_kayip_hesapla(img_v, txt_v, sicaklik_t=10.0, bias_b=-5.0))
```
```test
def sinama_siglip(f):
    import copy, math, random
    def _logsig(z):
        return -math.log1p(math.exp(-z)) if z >= 0 else z - math.log1p(math.exp(z))
    def _ce(logits, target):
        m = max(logits)
        lse = m + math.log(sum(math.exp(v - m) for v in logits))
        return lse - logits[target]
    def _ref(U, V, t, b):
        n, d = len(U), len(U[0])
        u_n = []
        v_n = []
        for i in range(n):
            nu = math.sqrt(sum(float(x)**2 for x in U[i]))
            nv = math.sqrt(sum(float(x)**2 for x in V[i]))
            u_n.append([float(x)/nu for x in U[i]])
            v_n.append([float(x)/nv for x in V[i]])
        S = [[sum(u_n[i][k]*v_n[j][k] for k in range(d)) for j in range(n)] for i in range(n)]
        sig_top = 0.0
        for i in range(n):
            for j in range(n):
                y = 1.0 if i == j else -1.0
                z = y * (float(t) * S[i][j] + float(b))
                sig_top += -_logsig(z)
        i2t = sum(_ce([float(t)*S[i][j] for j in range(n)], i) for i in range(n)) / n
        t2i = sum(_ce([float(t)*S[j][i] for j in range(n)], i) for i in range(n)) / n
        dogru = sum(1 for i in range(n) if max(range(n), key=lambda j: (S[i][j], -j)) == i)
        return {
            "kosinus_matrisi": S,
            "siglip_kaybi": sig_top / (n * n),
            "clip_kaybi": 0.5 * (i2t + t2i),
            "top1_dogruluk": float(dogru) / n,
        }
    def _yakin(a, b):
        keys = {"kosinus_matrisi", "siglip_kaybi", "clip_kaybi", "top1_dogruluk"}
        if not isinstance(a, dict) or set(a.keys()) != keys:
            return False
        for k in ("siglip_kaybi", "clip_kaybi", "top1_dogruluk"):
            if isinstance(a[k], bool) or not isinstance(a[k], float) or abs(a[k] - b[k]) > 1e-10:
                return False
        if not isinstance(a["kosinus_matrisi"], list) or len(a["kosinus_matrisi"]) != len(b["kosinus_matrisi"]):
            return False
        for sa, sb in zip(a["kosinus_matrisi"], b["kosinus_matrisi"]):
            if not isinstance(sa, list) or len(sa) != len(sb):
                return False
            if any(abs(u - v) > 1e-10 for u, v in zip(sa, sb)):
                return False
        return True
    try:
        u1 = [[3.0, 0.0], [0.0, 4.0]]
        v1 = [[5.0, 0.0], [0.0, 2.0]]
        ou, ov = copy.deepcopy(u1), copy.deepcopy(v1)
        out = f(u1, v1, 10.0, -5.0)
        if u1 != ou or v1 != ov or not _yakin(out, _ref(u1, v1, 10.0, -5.0)):
            return False
        if abs(out["kosinus_matrisi"][0][0] - 1.0) > 1e-12 or abs(out["top1_dogruluk"] - 1.0) > 1e-12:
            return False

        rng = random.Random(2601)
        for _ in range(20):
            n = rng.randint(2, 5)
            d = rng.randint(2, 6)
            uu = [[rng.uniform(-3.0, 3.0) for _ in range(d)] for _ in range(n)]
            vv = [[rng.uniform(-3.0, 3.0) for _ in range(d)] for _ in range(n)]
            tt = rng.uniform(1.0, 15.0)
            bb = rng.uniform(-10.0, 2.0)
            if not _yakin(f(uu, vv, tt, bb), _ref(uu, vv, tt, bb)):
                return False

        bad_cases = [
            ([[1.0, 0.0]], [[1.0, 0.0]], 10.0, -5.0),  # N < 2
            ([[0.0, 0.0], [1.0, 0.0]], [[1.0, 0.0], [0.0, 1.0]], 10.0, -5.0),  # sıfır vektörü!
            ([[1.0, 0.0], [0.0, 1.0]], [[1.0], [0.0]], 10.0, -5.0),  # boyut uyuşmazlığı
            ([[1.0, 0.0], [0.0, 1.0]], [[1.0, 0.0], [0.0, 1.0]], 0.0, -5.0),  # t <= 0
            ([[1.0, 0.0], [0.0, 1.0]], [[1.0, 0.0], [0.0, 1.0]], True, -5.0),
            ([[1.0, True], [0.0, 1.0]], [[1.0, 0.0], [0.0, 1.0]], 10.0, -5.0),
        ]
        for bu, bv, bt, bb in bad_cases:
            try:
                f(bu, bv, bt, bb)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

siglip_kayip_hesapla = need("siglip_kayip_hesapla")
ok(sinama_siglip(siglip_kayip_hesapla), "L2 normalizasyonu, SigLIP ikili sigmoid kaybı ve simetrik CLIP InfoNCE kaybı")
for ad, mut in [
    ("bias_b yok sayan", lambda u, v, t, b: siglip_kayip_hesapla(u, v, t, 0.0)),
    ("yalnız I->T CLIP hesaplayan", lambda u, v, t, b: dict(siglip_kayip_hesapla(u, v, t, b), clip_kaybi=siglip_kayip_hesapla(u, v, t, b)["siglip_kaybi"])),
    ("N yerine N^2 bölmeyen", lambda u, v, t, b: dict(siglip_kayip_hesapla(u, v, t, b), siglip_kaybi=siglip_kayip_hesapla(u, v, t, b)["siglip_kaybi"] * len(u))),
]:
    ok(not sinama_siglip(mut), "mutant reddedildi: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef _norm_matris(M):\n    if not isinstance(M, list) or len(M) < 2 or (not isinstance(M[0], list)) or (not M[0]):\n        raise ValueError('en az 2x1 boyutlu 2B matris gerekli')\n    d = len(M[0])\n    out = []\n    for s in M:\n        if not isinstance(s, list) or len(s) != d or (not all((_sayi_mi(v) for v in s))):\n            raise ValueError('geçersiz vektör')\n        norm = math.sqrt(sum((float(v) ** 2 for v in s)))\n        if norm == 0.0:\n            raise ValueError('sıfır normlu vektör normalize edilemez')\n        out.append([float(v) / norm for v in s])\n    return out\n\ndef _log_sigmoid(z):\n    if z >= 0.0:\n        return -math.log1p(math.exp(-z))\n    return z - math.log1p(math.exp(z))\n\ndef _cross_entropy(logits, hedef):\n    m = max(logits)\n    lse = m + math.log(sum((math.exp(v - m) for v in logits)))\n    return lse - logits[hedef]\n\ndef siglip_kayip_hesapla(goruntu_vektorleri, metin_vektorleri, sicaklik_t, bias_b):\n    u_norm = _norm_matris(goruntu_vektorleri)\n    v_norm = _norm_matris(metin_vektorleri)\n    if len(u_norm) != len(v_norm) or len(u_norm[0]) != len(v_norm[0]):\n        raise ValueError('görüntü ve metin matris boyutları eşit olmalı')\n    if not _sayi_mi(sicaklik_t) or sicaklik_t <= 0.0 or (not _sayi_mi(bias_b)):\n        raise ValueError('geçersiz sicaklik_t veya bias_b')\n    n = len(u_norm)\n    d = len(u_norm[0])\n    t = float(sicaklik_t)\n    b = float(bias_b)\n    S = [[sum((u_norm[i][k] * v_norm[j][k] for k in range(d))) for j in range(n)] for i in range(n)]\n    sig_toplam = 0.0\n    for i in range(n):\n        for j in range(n):\n            y_ij = 1.0 if i == j else -1.0\n            z_ij = y_ij * (t * S[i][j] + b)\n            sig_toplam += -_log_sigmoid(z_ij)\n    siglip_kaybi = sig_toplam / (n * n)\n    loss_i2t = sum((_cross_entropy([t * S[i][j] for j in range(n)], i) for i in range(n))) / n\n    loss_t2i = sum((_cross_entropy([t * S[j][i] for j in range(n)], i) for i in range(n))) / n\n    clip_kaybi = 0.5 * (loss_i2t + loss_t2i)\n    dogru = sum((1 for i in range(n) if max(range(n), key=lambda j: (S[i][j], -j)) == i))\n    return {'kosinus_matrisi': S, 'siglip_kaybi': siglip_kaybi, 'clip_kaybi': clip_kaybi, 'top1_dogruluk': float(dogru) / n}", 'referans', 'exec'), _REF)
_t, _g = _ff(siglip_kayip_hesapla, _REF['siglip_kayip_hesapla'], ([[3.0, 0.0], [0.0, 4.0]], [[5.0, 0.0], [0.0, 2.0]], 10.0, -5.0), tohum=3172, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (siglip_kayip_hesapla): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
ok(siglip_kayip_hesapla([[1.0, 0.0], [1.0, 0.0]], [[1.0, 0.0], [1.0, 0.0]], 1000.0, 0.0) == _REF['siglip_kayip_hesapla']([[1.0, 0.0], [1.0, 0.0]], [[1.0, 0.0], [1.0, 0.0]], 1000.0, 0.0), "büyük sicaklik_t ±1000 log-sigmoid kararlılığı korunmalı")
try:
    siglip_kayip_hesapla([[1.0], [1.0]], [[1.0, 0.0], [0.0, 1.0]], 10.0, -5.0)
    ok(False, "farklı sütun boyutlu matrisler ValueError fırlatmalı")
except ValueError:
    ok(True, "farklı sütun boyutlu matrisler ValueError fırlattı")
```
```solution
import math

def _sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def _norm_matris(M):
    if not isinstance(M, list) or len(M) < 2 or not isinstance(M[0], list) or not M[0]:
        raise ValueError("en az 2x1 boyutlu 2B matris gerekli")
    d = len(M[0])
    out = []
    for s in M:
        if not isinstance(s, list) or len(s) != d or not all(_sayi_mi(v) for v in s):
            raise ValueError("geçersiz vektör")
        norm = math.sqrt(sum(float(v) ** 2 for v in s))
        if norm == 0.0:
            raise ValueError("sıfır normlu vektör normalize edilemez")
        out.append([float(v) / norm for v in s])
    return out

def _log_sigmoid(z):
    if z >= 0.0:
        return -math.log1p(math.exp(-z))
    return z - math.log1p(math.exp(z))

def _cross_entropy(logits, hedef):
    m = max(logits)
    lse = m + math.log(sum(math.exp(v - m) for v in logits))
    return lse - logits[hedef]

def siglip_kayip_hesapla(goruntu_vektorleri, metin_vektorleri, sicaklik_t, bias_b):
    u_norm = _norm_matris(goruntu_vektorleri)
    v_norm = _norm_matris(metin_vektorleri)
    if len(u_norm) != len(v_norm) or len(u_norm[0]) != len(v_norm[0]):
        raise ValueError("görüntü ve metin matris boyutları eşit olmalı")
    if not _sayi_mi(sicaklik_t) or sicaklik_t <= 0.0 or not _sayi_mi(bias_b):
        raise ValueError("geçersiz sicaklik_t veya bias_b")

    n = len(u_norm)
    d = len(u_norm[0])
    t = float(sicaklik_t)
    b = float(bias_b)

    S = [[sum(u_norm[i][k] * v_norm[j][k] for k in range(d)) for j in range(n)] for i in range(n)]

    sig_toplam = 0.0
    for i in range(n):
        for j in range(n):
            y_ij = 1.0 if i == j else -1.0
            z_ij = y_ij * (t * S[i][j] + b)
            sig_toplam += -_log_sigmoid(z_ij)
    siglip_kaybi = sig_toplam / (n * n)

    loss_i2t = sum(_cross_entropy([t * S[i][j] for j in range(n)], i) for i in range(n)) / n
    loss_t2i = sum(_cross_entropy([t * S[j][i] for j in range(n)], i) for i in range(n)) / n
    clip_kaybi = 0.5 * (loss_i2t + loss_t2i)

    dogru = sum(1 for i in range(n) if max(range(n), key=lambda j: (S[i][j], -j)) == i)
    return {
        "kosinus_matrisi": S,
        "siglip_kaybi": siglip_kaybi,
        "clip_kaybi": clip_kaybi,
        "top1_dogruluk": float(dogru) / n,
    }

if __name__ == "__main__":
    img_v = [[3.0, 0.0], [0.0, 4.0]]
    txt_v = [[5.0, 0.0], [0.0, 2.0]]
    print(siglip_kayip_hesapla(img_v, txt_v, sicaklik_t=10.0, bias_b=-5.0))
```
```hint
Önce her görüntü ve metin satırını kendi L2 normuna bölerek birim vektör yap. $S_{i,j} = \hat{u}_i \cdot \hat{v}_j$ üzerinden `SigLIP` için $\frac{1}{N^2}\sum -\log\sigma(y_{i,j}(t S_{i,j} + b))$, `CLIP` için satır ve sütun `Cross-Entropy` ortalamasını hesapla.
```
:::

::: gorev 2 · AnyRes Dinamik Çözünürlük Izgara (Grid) Seçimi ve Token Sayısı Hesabı
Bir **`AnyRes (Dynamic High-Resolution)`** VLM ön-işlemcisinde, verilen $(W, H)$ boyutundaki bir görüntü için aday ızgaralar (`aday_izgaralar`) arasından en uygun $(r, c)$ karo ızgarasını seçen ve `Global Thumbnail` + `2x2 Pixel Unshuffle` sonrası toplam görsel token sayısını hesaplayan `anyres_izgara_sec(genislik, yukseklik, karo_boyutu, aday_izgaralar, yama_boyutu)` işlevini yaz.

**Girdi Kuralları ve Doğrulama:**
- `genislik` ($W$) ve `yukseklik` ($H$): `bool` olmayan pozitif tam sayılar ($\ge 1$).
- `karo_boyutu` ($T$) ve `yama_boyutu` ($P$): `bool` olmayan pozitif tam sayılar ($\ge 1$).
  - `karo_boyutu` değeri `yama_boyutu`'na tam bölünmelidir (`T % P == 0`) ve bir karodaki tek eksenli yama sayısı (`T // P`) `2x2 Pixel Unshuffle` için çift sayı (`(T // P) % 2 == 0`) olmalıdır; aksi halde `ValueError` yükselt!
- `aday_izgaralar`: Boş olmayan bir `list`. Her elemanı `(satir_sayisi, sutun_sayisi)` yani `(r, c)` biçiminde 2 elemanlı `tuple` veya `list` (`r >= 1, c >= 1` pozitif tam sayılar) olmalıdır.

**Hesaplama Kuralları:**
1. Her aday ızgara $(r, c)$ için:
   - Izgara piksel genişliği $W_g = c \cdot T$, ızgara piksel yüksekliği $H_g = r \cdot T$.
   - Görüntüyü en-boy oranını bozmadan ızgaraya sığdıran ölçek katsayısı (görüntüyü orijinal boyutundan daha fazla büyütmeden, yani `1.0` ile sınırlandırarak):
     $$s = \min\left(\frac{W_g}{W}, \; \frac{H_g}{H}, \; 1.0\right)$$
   - **Etkin Kapsanan Alan (`etkin_alan`):** $A_{\text{eff}} = (W \cdot s) \cdot (H \cdot s) = W \cdot H \cdot s^2$.
   - **Boş Dolgu Alanı (`dolgu_alani`):** Izgara içine en-boy oranını koruyarak tam sığdırıldığında ($s_{\text{fit}} = \min(W_g / W, H_g / H)$) boş kalan alan:
     $$A_{\text{pad}} = (W_g \cdot H_g) - (W \cdot s_{\text{fit}}) \cdot (H \cdot s_{\text{fit}})$$
2. **En İyi Izgara Seçimi:**
   - Önce **`etkin_alan` ($A_{\text{eff}}$) değerini maksimize eden** ızgarayı seç (`round(A_eff, 9)` ile karşılaştır).
   - Eğer birden fazla ızgara aynı maksimum `etkin_alan` değerini veriyorsa, aralarından **`dolgu_alani` ($A_{\text{pad}}$) en küçük olanı** (`round(A_pad, 9)`) seç (onda da eşitlik varsa `aday_izgaralar` listesindeki ilk ızgarayı seç).
3. **Token Hesapları (Seçilen $(r^*, c^*)$ ızgarası için):**
   - `secilen_izgara`: `(r*, c*)` (`tuple` olarak).
   - `toplam_karo_sayisi`: $r^* \cdot c^* + 1$ (`+1` `Global Thumbnail` karosu!).
   - `ham_gorsel_token`: $\text{toplam\_karo\_sayisi} \times (T // P)^2$ (`int`).
   - `unshuffle_gorsel_token`: `ham_gorsel_token // 4` ($2 \times 2$ `Pixel Unshuffle` sonrası token sayısı, `int`).
4. İşlev şu sözlüğü döndürmelidir:
   `{"secilen_izgara": (int, int), "toplam_karo_sayisi": int, "ham_gorsel_token": int, "unshuffle_gorsel_token": int}`
- Geçersiz herhangi bir girdide `ValueError` yükseltilmelidir.

```starter
# KUSURLU BAŞLANGIÇ KODU: Görüntü boyutuna bakmadan hep ilk ızgarayı seçiyor ve Global Thumbnail (+1) eklemiyor!
def anyres_izgara_sec(genislik, yukseklik, karo_boyutu, aday_izgaralar, yama_boyutu):
     r, c = tuple(aday_izgaralar[0])
     n_karo = r * c
     ham = n_karo * ((karo_boyutu // yama_boyutu) ** 2)
     return {
         "secilen_izgara": (r, c),
         "toplam_karo_sayisi": n_karo,
         "ham_gorsel_token": ham,
         "unshuffle_gorsel_token": ham // 4,
     }

adaylar = [(1, 1), (1, 2), (2, 1), (2, 2)]
# 672x336 yatay görüntü (2:1 oran) -> (1, 2) ızgarası (672x336) sıfır dolguyla tam oturur!
print(anyres_izgara_sec(672, 336, 336, adaylar, 14))
```
```test
def sinama_anyres(f):
    import copy, random
    def _ref(W, H, T, adaylar, P):
        en_iyi = None
        en_iyi_anahtar = None
        for idx, (r, c) in enumerate(adaylar):
            wg, hg = c * T, r * T
            s = min(wg / W, hg / H, 1.0)
            a_eff = W * H * (s ** 2)
            s_fit = min(wg / W, hg / H)
            a_pad = (wg * hg) - (W * H * (s_fit ** 2))
            anahtar = (round(a_eff, 9), -round(a_pad, 9), -idx)
            if en_iyi_anahtar is None or anahtar > en_iyi_anahtar:
                en_iyi_anahtar = anahtar
                en_iyi = (int(r), int(c))
        n_karo = en_iyi[0] * en_iyi[1] + 1
        ham = n_karo * ((T // P) ** 2)
        return {
            "secilen_izgara": en_iyi,
            "toplam_karo_sayisi": n_karo,
            "ham_gorsel_token": ham,
            "unshuffle_gorsel_token": ham // 4,
        }
    try:
        adaylar = [(1, 1), (1, 2), (2, 1), (2, 2), (1, 3), (3, 1)]
        old = list(adaylar)
        # 1) 672x336 yatay görüntü -> (1, 2) seçilmeli (2 yerel + 1 global = 3 karo)
        out1 = f(672, 336, 336, adaylar, 14)
        if adaylar != old or out1 != _ref(672, 336, 336, adaylar, 14):
            return False
        if out1["secilen_izgara"] != (1, 2) or out1["toplam_karo_sayisi"] != 3 or out1["ham_gorsel_token"] != 1728 or out1["unshuffle_gorsel_token"] != 432:
            return False

        # 2) 336x1008 dikey fatura görüntüsü -> (3, 1) seçilmeli (3 yerel + 1 global = 4 karo)
        out2 = f(336, 1008, 336, adaylar, 14)
        if out2 != _ref(336, 1008, 336, adaylar, 14) or out2["secilen_izgara"] != (3, 1):
            return False

        # 3) Küçük 200x200 kare görüntü -> (1, 1) ve (2, 2) aynı etkin alanı (40000) verir ama (1, 1) daha az dolgu bırakır!
        out3 = f(200, 200, 336, adaylar, 14)
        if out3 != _ref(200, 200, 336, adaylar, 14) or out3["secilen_izgara"] != (1, 1):
            return False

        rng = random.Random(2602)
        for _ in range(25):
            w = rng.randint(100, 1500)
            h = rng.randint(100, 1500)
            if f(w, h, 336, adaylar, 14) != _ref(w, h, 336, adaylar, 14):
                return False

        bad_cases = [
            (0, 336, 336, adaylar, 14),
            (336, -10, 336, adaylar, 14),
            (336, 336, 336, [], 14),
            (336, 336, 336, [(1, 0)], 14),
            (336, 336, 336, [(1, 2, 3)], 14),
            (336, 336, 335, adaylar, 14),  # T % P != 0
            (336, 336, 42, adaylar, 14),   # T // P = 3 (tek sayı, 2x2 unshuffle yapılamaz!)
            (True, 336, 336, adaylar, 14),
        ]
        for bw, bh, bt, ba, bp in bad_cases:
            try:
                f(bw, bh, bt, ba, bp)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

anyres_izgara_sec = need("anyres_izgara_sec")
ok(sinama_anyres(anyres_izgara_sec), "AnyRes dinamik ızgara seçimi, Global Thumbnail (+1) ve 2x2 Pixel Unshuffle")
for ad, mut in [
    ("Global Thumbnail (+1) unutan", lambda w, h, t, a, p: dict(anyres_izgara_sec(w, h, t, a, p), toplam_karo_sayisi=anyres_izgara_sec(w, h, t, a, p)["toplam_karo_sayisi"] - 1)),
    ("Pixel Unshuffle 4'e bölmeyen", lambda w, h, t, a, p: dict(anyres_izgara_sec(w, h, t, a, p), unshuffle_gorsel_token=anyres_izgara_sec(w, h, t, a, p)["ham_gorsel_token"])),
    ("hep (2,2) seçen", lambda w, h, t, a, p: dict(anyres_izgara_sec(w, h, t, a, p), secilen_izgara=(2, 2))),
]:
    ok(not sinama_anyres(mut), "mutant reddedildi: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def _pozitif_int_mi(v):\n    return not isinstance(v, bool) and isinstance(v, int) and (v >= 1)\n\ndef anyres_izgara_sec(genislik, yukseklik, karo_boyutu, aday_izgaralar, yama_boyutu):\n    for v in (genislik, yukseklik, karo_boyutu, yama_boyutu):\n        if not _pozitif_int_mi(v):\n            raise ValueError('boyutlar pozitif tam sayı olmalı')\n    if karo_boyutu % yama_boyutu != 0:\n        raise ValueError('karo_boyutu, yama_boyutu değerine tam bölünmeli')\n    yama_eksen = karo_boyutu // yama_boyutu\n    if yama_eksen % 2 != 0:\n        raise ValueError('2x2 Pixel Unshuffle için eksen başına yama sayısı çift olmalı')\n    if not isinstance(aday_izgaralar, list) or not aday_izgaralar:\n        raise ValueError('boş olmayan aday_izgaralar gerekli')\n    temiz_adaylar = []\n    for item in aday_izgaralar:\n        if not isinstance(item, (tuple, list)) or len(item) != 2:\n            raise ValueError('her ızgara (r, c) çifti olmalı')\n        r, c = (item[0], item[1])\n        if not _pozitif_int_mi(r) or not _pozitif_int_mi(c):\n            raise ValueError('ızgara satır ve sütunu pozitif tam sayı olmalı')\n        temiz_adaylar.append((r, c))\n    en_iyi_izgara = None\n    en_iyi_anahtar = None\n    for idx, (r, c) in enumerate(temiz_adaylar):\n        wg = c * karo_boyutu\n        hg = r * karo_boyutu\n        s = min(wg / genislik, hg / yukseklik, 1.0)\n        a_eff = genislik * yukseklik * s ** 2\n        s_fit = min(wg / genislik, hg / yukseklik)\n        a_pad = wg * hg - genislik * yukseklik * s_fit ** 2\n        anahtar = (round(a_eff, 9), -round(a_pad, 9), -idx)\n        if en_iyi_anahtar is None or anahtar > en_iyi_anahtar:\n            en_iyi_anahtar = anahtar\n            en_iyi_izgara = (r, c)\n    toplam_karo = en_iyi_izgara[0] * en_iyi_izgara[1] + 1\n    ham_token = toplam_karo * yama_eksen ** 2\n    return {'secilen_izgara': en_iyi_izgara, 'toplam_karo_sayisi': toplam_karo, 'ham_gorsel_token': ham_token, 'unshuffle_gorsel_token': ham_token // 4}", 'referans', 'exec'), _REF)
_t, _g = _ff(anyres_izgara_sec, _REF['anyres_izgara_sec'], (672, 336, 336, [(1, 1), (1, 2), (2, 1), (2, 2)], 14), tohum=2859, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (anyres_izgara_sec): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
ok(all(anyres_izgara_sec(*_a) == _REF['anyres_izgara_sec'](*_a) for _a in [(10**6, 10**6, 4, [(1, 1), (2, 2)], 2), (20000000000, 10000000001, 4, [(2, 2), (1, 2)], 2), (50000000001, 50000000000, 4, [(2, 1), (1, 2)], 2)]), "AnyRes etkin alan formülü ve 9 basamak yuvarlama korunmalı")
try:
    anyres_izgara_sec(336, 336, 336, [(0, 1)], 14)
    ok(False, "r=0 ızgara satırı ValueError fırlatmalı")
except ValueError:
    ok(True, "r=0 ızgara satırı ValueError fırlattı")
```
```solution
def _pozitif_int_mi(v):
    return not isinstance(v, bool) and isinstance(v, int) and v >= 1

def anyres_izgara_sec(genislik, yukseklik, karo_boyutu, aday_izgaralar, yama_boyutu):
    for v in (genislik, yukseklik, karo_boyutu, yama_boyutu):
        if not _pozitif_int_mi(v):
            raise ValueError("boyutlar pozitif tam sayı olmalı")
    if karo_boyutu % yama_boyutu != 0:
        raise ValueError("karo_boyutu, yama_boyutu değerine tam bölünmeli")
    yama_eksen = karo_boyutu // yama_boyutu
    if yama_eksen % 2 != 0:
        raise ValueError("2x2 Pixel Unshuffle için eksen başına yama sayısı çift olmalı")
    if not isinstance(aday_izgaralar, list) or not aday_izgaralar:
        raise ValueError("boş olmayan aday_izgaralar gerekli")

    temiz_adaylar = []
    for item in aday_izgaralar:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise ValueError("her ızgara (r, c) çifti olmalı")
        r, c = item[0], item[1]
        if not _pozitif_int_mi(r) or not _pozitif_int_mi(c):
            raise ValueError("ızgara satır ve sütunu pozitif tam sayı olmalı")
        temiz_adaylar.append((r, c))

    en_iyi_izgara = None
    en_iyi_anahtar = None

    for idx, (r, c) in enumerate(temiz_adaylar):
        wg = c * karo_boyutu
        hg = r * karo_boyutu
        s = min(wg / genislik, hg / yukseklik, 1.0)
        a_eff = genislik * yukseklik * (s ** 2)

        s_fit = min(wg / genislik, hg / yukseklik)
        a_pad = (wg * hg) - (genislik * yukseklik * (s_fit ** 2))

        anahtar = (round(a_eff, 9), -round(a_pad, 9), -idx)
        if en_iyi_anahtar is None or anahtar > en_iyi_anahtar:
            en_iyi_anahtar = anahtar
            en_iyi_izgara = (r, c)

    toplam_karo = en_iyi_izgara[0] * en_iyi_izgara[1] + 1
    ham_token = toplam_karo * (yama_eksen ** 2)

    return {
        "secilen_izgara": en_iyi_izgara,
        "toplam_karo_sayisi": toplam_karo,
        "ham_gorsel_token": ham_token,
        "unshuffle_gorsel_token": ham_token // 4,
    }

if __name__ == "__main__":
    adaylar = [(1, 1), (1, 2), (2, 1), (2, 2)]
    print(anyres_izgara_sec(672, 336, 336, adaylar, 14))
```
```hint
Her `(r, c)` ızgarası için `s = min(c*T / W, r*T / H, 1.0)` ile `a_eff = W * H * s**2` ve `s_fit = min(c*T / W, r*T / H)` ile `a_pad = (c*T*r*T) - W*H*(s_fit**2)` hesapla. `(round(a_eff, 9), -round(a_pad, 9), -idx)` anahtarını maksimize eden ızgarayı seçip `r*c + 1` karo üzerinden token sayılarını döndür.
```
:::

::: anlat Gerçek deney: Gerçek rakam görüntülerinde CLIP ve SigLIP eğitimi, LLaVA-NeXT'e karşı AnyRes
Final küçük ama gerçek bir çift kodlayıcı eğitir (indirme yok):

- **Veri:** scikit-learn'ün gerçek el yazısı rakam görüntüleri (1 797 adet, 8×8), 1 400 eğitim / 397 test. Metin tarafı "a photo of the handwritten digit seven" gibi 10 cümlenin **donmuş** SmolLM2 temsilleridir (son gizli durumların ortalaması).
- **Eğitim:** küçük bir görüntü MLP'si ve doğrusal metin projeksiyonu, 1 200 adım CLIP (InfoNCE) ya da SigLIP (sigmoid) kaybıyla, 16 ve 128'lik batch'lerle eğitilir. Aynı batch'te aynı sınıftan birden çok görüntü olabildiği için aynı sınıf çiftleri pozitif sayılır. Test görüntüleri, en yakın sınıf cümlesine göre sıfır atışla sınıflandırılır. SigLIP makaledeki başlatmayla ($t = 10$, $b = -10$) başlar.
- **Öğrencinin kaybı:** SigLIP'le eğitilmiş kodlayıcılardan, 8 farklı sınıfın gerçek görüntü ve metin temsilleri senin `siglip_kayip_hesapla` işlevine verilir; kosinüs matrisi, iki kayıp ve top-1 torch ile karşılaştırılır.
- **AnyRes:** 10 gerçek fotoğraf boyutunda (12 MP telefon, 1080p, dikey, küçük ikon …) senin `anyres_izgara_sec` seçimin `transformers`'ın LLaVA-NeXT gerçeklemesi `select_best_resolution` ile karşılaştırılır. Tek karodan küçük bir görüntüde iki kural ayrışır: senin kuralın küçük görüntüyü büyütüp üç karoyu doldurmayı seçer (576 token), LLaVA-NeXT boşa harcanan alanı daha sıkı saydığı için tek karo seçer.

**Güvenlik yönü — çekişmeli görüntüyle hedefli eşleştirme:** Eğitilmiş SigLIP (b=128) kodlayıcısına karşı beyaz kutu saldırısı yapılır: her test rakamına, onu **bir sonraki** rakamın metniyle eşleştiren L∞ sınırlı bir pertürbasyon eklenir (tek adımlı FGSM ve 10 adımlı PGD; eps 0.05, 0.1, 0.2). Sıfır atış doğruluğu ve hedefe yönlendirme oranı ölçülür. Pertürbasyon büyüdükçe doğruluk çöker ve PGD görüntüleri seçilen metne yönlendirir. Çift kodlayıcılar görsel arama, içerik filtresi ve VLM'lerin görüntü kodlayıcısı olarak kullanılır; aynı saldırı onları kandırır.

Kabul: iki işlevin farksal taramayı geçmesi; tüm kipler için sıfır atış doğruluğunun en az 0.5 olması; öğrencinin kaybının gerçek batch'te torch ile aynı olması; en az bir karo boyutundaki tüm görüntülerde AnyRes seçiminin LLaVA-NeXT ile aynı olması. Ayrıca en büyük eps'te PGD hedefe yönlendirmesi 0.5'i aşmalı ve doğruluğu temiz doğruluğun yarısının altına indirmeli; PGD en küçük eps'te FGSM'den zayıf olmamalı ve pertürbasyon eps sınırını aşmamalıdır.

**Kanıt dosyasını oku:** `egitim` (dört kipin doğruluğu, öğrenilen sıcaklık ve bias), `batch_ogrenci`, `anyres`, `anyres_kucuk_fark`. Soru 1: SigLIP 16'lık batch'te neden yavaş öğrendi ve $b = -10$ başlatmasının bununla ilgisi ne? Soru 2: Küçük görüntüde hangi kural daha iyi, neden? Soru 3: 12 MP bir fotoğraf kaç görsel token ediyor ve bu bağlam bütçesini nasıl etkiler?
:::

::: gorev Gerçek deney · Gerçek rakam görüntülerinde CLIP/SigLIP çift kodlayıcı ve LLaVA-NeXT'e karşı AnyRes
Önceki görevlerdeki `siglip_kayip_hesapla`, `anyres_izgara_sec` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 240
```
```starter
import ai_lab
import math

def siglip_kayip_hesapla(goruntu_vektorleri, metin_vektorleri, sicaklik_t, bias_b):
    n = len(goruntu_vektorleri)
    d = len(goruntu_vektorleri[0])
    S = [[sum((goruntu_vektorleri[i][k] * metin_vektorleri[j][k] for k in range(d))) for j in range(n)] for i in range(n)]
    return {'kosinus_matrisi': S, 'siglip_kaybi': 1.0, 'clip_kaybi': 1.0, 'top1_dogruluk': 1.0}

def anyres_izgara_sec(genislik, yukseklik, karo_boyutu, aday_izgaralar, yama_boyutu):
    r, c = tuple(aday_izgaralar[0])
    n_karo = r * c
    ham = n_karo * (karo_boyutu // yama_boyutu) ** 2
    return {'secilen_izgara': (r, c), 'toplam_karo_sayisi': n_karo, 'ham_gorsel_token': ham, 'unshuffle_gorsel_token': ham // 4}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_26 as D
    D.goster(siglip_kayip_hesapla, anyres_izgara_sec)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_egit', '_metin_temsilleri', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
siglip_kayip_hesapla = need("siglip_kayip_hesapla")
anyres_izgara_sec = need("anyres_izgara_sec")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef _norm_matris(M):\n    if not isinstance(M, list) or len(M) < 2 or (not isinstance(M[0], list)) or (not M[0]):\n        raise ValueError('en az 2x1 boyutlu 2B matris gerekli')\n    d = len(M[0])\n    out = []\n    for s in M:\n        if not isinstance(s, list) or len(s) != d or (not all((_sayi_mi(v) for v in s))):\n            raise ValueError('geçersiz vektör')\n        norm = math.sqrt(sum((float(v) ** 2 for v in s)))\n        if norm == 0.0:\n            raise ValueError('sıfır normlu vektör normalize edilemez')\n        out.append([float(v) / norm for v in s])\n    return out\n\ndef _log_sigmoid(z):\n    if z >= 0.0:\n        return -math.log1p(math.exp(-z))\n    return z - math.log1p(math.exp(z))\n\ndef _cross_entropy(logits, hedef):\n    m = max(logits)\n    lse = m + math.log(sum((math.exp(v - m) for v in logits)))\n    return lse - logits[hedef]\n\ndef siglip_kayip_hesapla(goruntu_vektorleri, metin_vektorleri, sicaklik_t, bias_b):\n    u_norm = _norm_matris(goruntu_vektorleri)\n    v_norm = _norm_matris(metin_vektorleri)\n    if len(u_norm) != len(v_norm) or len(u_norm[0]) != len(v_norm[0]):\n        raise ValueError('görüntü ve metin matris boyutları eşit olmalı')\n    if not _sayi_mi(sicaklik_t) or sicaklik_t <= 0.0 or (not _sayi_mi(bias_b)):\n        raise ValueError('geçersiz sicaklik_t veya bias_b')\n    n = len(u_norm)\n    d = len(u_norm[0])\n    t = float(sicaklik_t)\n    b = float(bias_b)\n    S = [[sum((u_norm[i][k] * v_norm[j][k] for k in range(d))) for j in range(n)] for i in range(n)]\n    sig_toplam = 0.0\n    for i in range(n):\n        for j in range(n):\n            y_ij = 1.0 if i == j else -1.0\n            z_ij = y_ij * (t * S[i][j] + b)\n            sig_toplam += -_log_sigmoid(z_ij)\n    siglip_kaybi = sig_toplam / (n * n)\n    loss_i2t = sum((_cross_entropy([t * S[i][j] for j in range(n)], i) for i in range(n))) / n\n    loss_t2i = sum((_cross_entropy([t * S[j][i] for j in range(n)], i) for i in range(n))) / n\n    clip_kaybi = 0.5 * (loss_i2t + loss_t2i)\n    dogru = sum((1 for i in range(n) if max(range(n), key=lambda j: (S[i][j], -j)) == i))\n    return {'kosinus_matrisi': S, 'siglip_kaybi': siglip_kaybi, 'clip_kaybi': clip_kaybi, 'top1_dogruluk': float(dogru) / n}\n\ndef _pozitif_int_mi(v):\n    return not isinstance(v, bool) and isinstance(v, int) and (v >= 1)\n\ndef anyres_izgara_sec(genislik, yukseklik, karo_boyutu, aday_izgaralar, yama_boyutu):\n    for v in (genislik, yukseklik, karo_boyutu, yama_boyutu):\n        if not _pozitif_int_mi(v):\n            raise ValueError('boyutlar pozitif tam sayı olmalı')\n    if karo_boyutu % yama_boyutu != 0:\n        raise ValueError('karo_boyutu, yama_boyutu değerine tam bölünmeli')\n    yama_eksen = karo_boyutu // yama_boyutu\n    if yama_eksen % 2 != 0:\n        raise ValueError('2x2 Pixel Unshuffle için eksen başına yama sayısı çift olmalı')\n    if not isinstance(aday_izgaralar, list) or not aday_izgaralar:\n        raise ValueError('boş olmayan aday_izgaralar gerekli')\n    temiz_adaylar = []\n    for item in aday_izgaralar:\n        if not isinstance(item, (tuple, list)) or len(item) != 2:\n            raise ValueError('her ızgara (r, c) çifti olmalı')\n        r, c = (item[0], item[1])\n        if not _pozitif_int_mi(r) or not _pozitif_int_mi(c):\n            raise ValueError('ızgara satır ve sütunu pozitif tam sayı olmalı')\n        temiz_adaylar.append((r, c))\n    en_iyi_izgara = None\n    en_iyi_anahtar = None\n    for idx, (r, c) in enumerate(temiz_adaylar):\n        wg = c * karo_boyutu\n        hg = r * karo_boyutu\n        s = min(wg / genislik, hg / yukseklik, 1.0)\n        a_eff = genislik * yukseklik * s ** 2\n        s_fit = min(wg / genislik, hg / yukseklik)\n        a_pad = wg * hg - genislik * yukseklik * s_fit ** 2\n        anahtar = (round(a_eff, 9), -round(a_pad, 9), -idx)\n        if en_iyi_anahtar is None or anahtar > en_iyi_anahtar:\n            en_iyi_anahtar = anahtar\n            en_iyi_izgara = (r, c)\n    toplam_karo = en_iyi_izgara[0] * en_iyi_izgara[1] + 1\n    ham_token = toplam_karo * yama_eksen ** 2\n    return {'secilen_izgara': en_iyi_izgara, 'toplam_karo_sayisi': toplam_karo, 'ham_gorsel_token': ham_token, 'unshuffle_gorsel_token': ham_token // 4}", 'referans', 'exec'), _REF)
_t, _g = _ff(siglip_kayip_hesapla, _REF['siglip_kayip_hesapla'], ([[3.0, 0.0], [0.0, 4.0]], [[5.0, 0.0], [0.0, 2.0]], 10.0, -5.0), tohum=3172, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (siglip_kayip_hesapla): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(anyres_izgara_sec, _REF['anyres_izgara_sec'], (672, 336, 336, [(1, 1), (1, 2), (2, 1), (2, 2)], 14), tohum=2859, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (anyres_izgara_sec): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
kontrol(siglip_kayip_hesapla([[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]], [[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]], 1000.0, 0.0) == _REF['siglip_kayip_hesapla']([[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]], [[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]], 1000.0, 0.0), "3x2 büyük sicaklik_t ±1000 ve n^2 paydası korunmalı")
kontrol(all(anyres_izgara_sec(*_a) == _REF['anyres_izgara_sec'](*_a) for _a in [(10**6, 10**6, 4, [(1, 1), (2, 2)], 2), (20000000000, 10000000001, 4, [(2, 2), (1, 2)], 2), (50000000001, 50000000000, 4, [(2, 1), (1, 2)], 2)]), "AnyRes etkin alan formülü ve 9 basamak yuvarlama korunmalı")
for _fn, _args in [
    (siglip_kayip_hesapla, ([[1.0, 0.0]], [[1.0, 0.0]], 10.0, -5.0)),
    (siglip_kayip_hesapla, ([[1.0], [1.0]], [[1.0, 0.0], [0.0, 1.0]], 10.0, -5.0)),
    (anyres_izgara_sec, (336, 336, 336, [(0, 1)], 14)),
    (anyres_izgara_sec, (336, 336, 336, [(1, 0)], 14)),
]:
    try:
        _fn(*_args)
        kontrol(False, "geçersiz girdi ValueError fırlatmalı")
    except ValueError:
        kontrol(True, "geçersiz girdi ValueError fırlattı")
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_26 as D
try: r = D.deney(siglip_kayip_hesapla, anyres_izgara_sec)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['egitim_ogrendi'], 'dört eğitim kipinde de sıfır atış doğruluğu en az 0.5')
kontrol(r['kayip_ayni'], "SigLIP/CLIP kaybı ve top-1 eğitilmiş kodlayıcıların gerçek batch'inde torch ile aynı")
kontrol(r['anyres_buyukte_ayni'], 'en az bir karo boyutundaki gerçek görüntülerde AnyRes seçimi LLaVA-NeXT ile aynı')
kontrol(r['cekismeli_basarili'], 'L∞ sınırlı PGD gerçek kodlayıcıda test rakamlarını seçilen metne yönlendirdi ve doğruluğu çökertti')
ai_lab.kanit_yaz("ai-uretim-26-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-26", "deney": r})
```
```solution
import ai_lab
import math

def _sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def _norm_matris(M):
    if not isinstance(M, list) or len(M) < 2 or (not isinstance(M[0], list)) or (not M[0]):
        raise ValueError('en az 2x1 boyutlu 2B matris gerekli')
    d = len(M[0])
    out = []
    for s in M:
        if not isinstance(s, list) or len(s) != d or (not all((_sayi_mi(v) for v in s))):
            raise ValueError('geçersiz vektör')
        norm = math.sqrt(sum((float(v) ** 2 for v in s)))
        if norm == 0.0:
            raise ValueError('sıfır normlu vektör normalize edilemez')
        out.append([float(v) / norm for v in s])
    return out

def _log_sigmoid(z):
    if z >= 0.0:
        return -math.log1p(math.exp(-z))
    return z - math.log1p(math.exp(z))

def _cross_entropy(logits, hedef):
    m = max(logits)
    lse = m + math.log(sum((math.exp(v - m) for v in logits)))
    return lse - logits[hedef]

def siglip_kayip_hesapla(goruntu_vektorleri, metin_vektorleri, sicaklik_t, bias_b):
    u_norm = _norm_matris(goruntu_vektorleri)
    v_norm = _norm_matris(metin_vektorleri)
    if len(u_norm) != len(v_norm) or len(u_norm[0]) != len(v_norm[0]):
        raise ValueError('görüntü ve metin matris boyutları eşit olmalı')
    if not _sayi_mi(sicaklik_t) or sicaklik_t <= 0.0 or (not _sayi_mi(bias_b)):
        raise ValueError('geçersiz sicaklik_t veya bias_b')
    n = len(u_norm)
    d = len(u_norm[0])
    t = float(sicaklik_t)
    b = float(bias_b)
    S = [[sum((u_norm[i][k] * v_norm[j][k] for k in range(d))) for j in range(n)] for i in range(n)]
    sig_toplam = 0.0
    for i in range(n):
        for j in range(n):
            y_ij = 1.0 if i == j else -1.0
            z_ij = y_ij * (t * S[i][j] + b)
            sig_toplam += -_log_sigmoid(z_ij)
    siglip_kaybi = sig_toplam / (n * n)
    loss_i2t = sum((_cross_entropy([t * S[i][j] for j in range(n)], i) for i in range(n))) / n
    loss_t2i = sum((_cross_entropy([t * S[j][i] for j in range(n)], i) for i in range(n))) / n
    clip_kaybi = 0.5 * (loss_i2t + loss_t2i)
    dogru = sum((1 for i in range(n) if max(range(n), key=lambda j: (S[i][j], -j)) == i))
    return {'kosinus_matrisi': S, 'siglip_kaybi': siglip_kaybi, 'clip_kaybi': clip_kaybi, 'top1_dogruluk': float(dogru) / n}

def _pozitif_int_mi(v):
    return not isinstance(v, bool) and isinstance(v, int) and (v >= 1)

def anyres_izgara_sec(genislik, yukseklik, karo_boyutu, aday_izgaralar, yama_boyutu):
    for v in (genislik, yukseklik, karo_boyutu, yama_boyutu):
        if not _pozitif_int_mi(v):
            raise ValueError('boyutlar pozitif tam sayı olmalı')
    if karo_boyutu % yama_boyutu != 0:
        raise ValueError('karo_boyutu, yama_boyutu değerine tam bölünmeli')
    yama_eksen = karo_boyutu // yama_boyutu
    if yama_eksen % 2 != 0:
        raise ValueError('2x2 Pixel Unshuffle için eksen başına yama sayısı çift olmalı')
    if not isinstance(aday_izgaralar, list) or not aday_izgaralar:
        raise ValueError('boş olmayan aday_izgaralar gerekli')
    temiz_adaylar = []
    for item in aday_izgaralar:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise ValueError('her ızgara (r, c) çifti olmalı')
        r, c = (item[0], item[1])
        if not _pozitif_int_mi(r) or not _pozitif_int_mi(c):
            raise ValueError('ızgara satır ve sütunu pozitif tam sayı olmalı')
        temiz_adaylar.append((r, c))
    en_iyi_izgara = None
    en_iyi_anahtar = None
    for idx, (r, c) in enumerate(temiz_adaylar):
        wg = c * karo_boyutu
        hg = r * karo_boyutu
        s = min(wg / genislik, hg / yukseklik, 1.0)
        a_eff = genislik * yukseklik * s ** 2
        s_fit = min(wg / genislik, hg / yukseklik)
        a_pad = wg * hg - genislik * yukseklik * s_fit ** 2
        anahtar = (round(a_eff, 9), -round(a_pad, 9), -idx)
        if en_iyi_anahtar is None or anahtar > en_iyi_anahtar:
            en_iyi_anahtar = anahtar
            en_iyi_izgara = (r, c)
    toplam_karo = en_iyi_izgara[0] * en_iyi_izgara[1] + 1
    ham_token = toplam_karo * yama_eksen ** 2
    return {'secilen_izgara': en_iyi_izgara, 'toplam_karo_sayisi': toplam_karo, 'ham_gorsel_token': ham_token, 'unshuffle_gorsel_token': ham_token // 4}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_26 as D
    D.goster(siglip_kayip_hesapla, anyres_izgara_sec)
```
```hint
İki görevin çözümlerini olduğu gibi buraya koy.
```
:::

::: anlat Sınır
Görevler CLIP (InfoNCE) ve SigLIP (sigmoid) kayıplarını küçük benzerlik matrislerinde, AnyRes ızgara seçimini ve token sayısını formülle hesaplatır; final adım gerçek rakam görüntülerinde küçük bir çift kodlayıcı eğitir ve AnyRes'i LLaVA-NeXT gerçeklemesiyle karşılaştırır (büyük bir VLM kullanılmaz). Kontrastif kayıp batch boyutuna ve sıcaklığa duyarlıdır; SigLIP'in avantajı özellikle küçük batch'lerde görülür. AnyRes çözünürlük arttıkça görsel token sayısını hızla büyütür ve bağlamı doldurur. Görüntüdeki yazı modele metin gibi okunur; görsel prompt injection ve tipografik saldırılar ai-uretim-12'nin finalinde gerçek bir VLM ile gösterilir.

Kaynaklar: [Radford vd. 2021 - Learning Transferable Visual Models From Natural Language Supervision](https://arxiv.org/abs/2103.00020), [Zhai vd. 2023 - Sigmoid Loss for Language Image Pre-Training](https://arxiv.org/abs/2303.15343), [Liu vd. 2023 - Improved Baselines with Visual Instruction Tuning](https://arxiv.org/abs/2310.03744).
:::

::: dusun
**Qwen2-VL** ve **Pixtral** gibi en yeni nesil VLM mimarileri, görüntüyü sabit $336 \times 336$ karolara (`AnyRes Tiling`) bölmek yerine **Doğal Çözünürlüklü ViT (`Naive Dynamic Resolution + 2D-RoPE`)** yaklaşımına geçmiştir:
Görüntüyü karolara kesmez; doğrudan kendi doğal çözünürlüğünde $14 \times 14$ yamalara böler ve her yamaya 1B token indisi yerine **2 Boyutlu Döner Konum Gömmesi (`2D Rotary Position Embedding`: `(satır_y, sütun_x)`)** verir!

**Mimari Karşılaştırma Sorusu:** Bir tablonun ortasından geçen uzun bir çizgiyi veya diyagramı okurken, görüntüyü `2x2` karolara kesen `AnyRes Tiling` yaklaşımında karo sınırlarında (`Seam / Boundary Artifact`) nasıl bir sorun yaşanabilir ve `2D-RoPE` kullanan doğal çözünürlüklü bir `ViT` bu sorunu nasıl aşar? Buna karşılık `AnyRes Tiling`'in GPU `FlashAttention` önbelleklemesi açısından avantajı nedir?
:::

::: ozet
- **`CLIP`**, görüntü ve metin gömmelerini $N \times N$ benzerlik matrisinin satır ve sütunları üzerinde simetrik `InfoNCE Softmax` kaybıyla hizalarken; **`SigLIP`** her $(i, j)$ çiftini bağımsız bir ikili `Sigmoid` sınıflandırma problemine dönüştürerek global normalizasyon darboğazını ortadan kaldırır.
- **`AnyRes (Dynamic High-Resolution Tiling)`**, yüksek çözünürlüklü görüntüleri en-boy oranını bozmadan optimal $(r, c)$ karo ızgarasına böler ve genel bağlamı korumak için 1 adet **`Global Thumbnail`** ekler.
- **`2D Pixel Unshuffle`**, $2 \times 2$ komşu görüntü yamalarını kanal boyutunda birleştirerek LLM'e gönderilen görsel token sayısını uzamsal bilgiyi kaybetmeden 4 kat azaltır.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **`CLIP InfoNCE` vs `SigLIP` ikili kayıp (35 sn).** "`CLIP` tüm yığın (`batch`) boyunca küresel `Softmax` kurduğu için dev yığın boyutu ister; `SigLIP` her görüntü-metin çiftini bağımsız ikili `Sigmoid` lojistik kayıpla değerlendirerek küçük yığınlarda da kararlı hizalama sağlar."
2. **`AnyRes` dinamik karolama (`Dynamic Tiling`) (30 sn).** "Yüksek çözünürlüklü bir belgeyi zorla `336x336` kareye ezmek küçük yazıları okunmaz yapar; `AnyRes` en-boy oranına en uygun ızgarayı seçip yerel karolarla birlikte bir de küresel küçük önizleme karosu üretir."
3. **`Pixel Unshuffle` token sıkıştırma (30 sn).** "Uzamsal $2\times 2$ komşu yama vektörlerini kanal boyutunda birleştirmek görsel token sayısını 4 kat azaltıp LLM bağlam bütçesini korur."
4. **Soru (25 sn).** "Yüksek çözünürlüklü bir görüntü karosunun içine insan gözünün zor seçtiği düşük kontrastlı metin gömüldüğünde (`Typographic / Visual Prompt Injection`) VLM neden bunu talimat sanabilir?"
:::
