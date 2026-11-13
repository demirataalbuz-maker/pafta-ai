---
id: ai-uretim-29
title: "Gerçek Zamanlı Ses ve Konuşma AI (GPT-4o Voice / Moshi): RVQ Neural Audio Codec ve Full-Duplex"
summary: "Klasik STT-LLM-TTS boru hattını yıkan Native Speech-to-Speech mimarisi: ses dalgasını ayrık tokenlara nicelendiren Residual Vector Quantization (RVQ Neural Audio Codec), zaman hizalı Inner Monologue ve kesintisiz Full-Duplex (Barge-In) akışı."
track: ai-uretim
order: 29
duration_minutes: 40
difficulty: ileri
xp: 320
prerequisites: [ai-uretim-28]
tags: [audio-ai, speech-to-speech, rvq, neural-codec, full-duplex, moshi, gpt-4o-voice]
esleme: ai-uretim-28, ai-saldiri-55
---

::: anlat
## Ses tokenları ve full-duplex akış

Bir neural audio codec, sesi ayrık codebook kimlikleriyle temsil edebilir. Bu derste RVQ ile residual bilgisini katmanlara dağıtacak, ses/metin akışlarını ve interruption durumunu inceleyeceksin. Codec bit-rate hesabı, gerçek bir konuşma modelinin gecikmesini veya ses kalitesini ölçmez.

Bu klasik boru hattının iki ölümcül kusuru vardır:
- **Gecikme Duvarı (`2–3 Saniye Latency`):** Doğal insan sohbetinde tepki süresi $200\text{–}300\text{ ms}$'dir; 3 saniye bekleyen bir sistemle gerçek zamanlı sohbet edilemez ve sözü kesilemez!
- **Paralinguistik Körlük (`Acoustic Information Loss`):** `STT` sesi düz metne çevirdiği anda kullanıcının sesindeki **alaycılık, fısıltı, heyecan, öksürük veya kahkaha** tamamen silinir!

Yayımlanmış Moshi çalışması, speech-to-speech ve full-duplex tasarıma örnektir. Bütün sesli ürünlerin aynı codec, model gövdesi veya latency değerini kullandığı varsayılmaz.

```
┌────────────────────────────────────────────────────────────────────────────┐
│         NATIVE SPEECH-TO-SPEECH & FULL-DUPLEX MİMARİSİ (MOSHI / 4o)        │
├────────────────────────┬─────────────────────────┬─────────────────────────┤
│ 1. RVQ NEURAL AUDIO    │ 2. INNER MONOLOGUE      │ 3. FULL-DUPLEX STREAM   │
│    CODEC (EnCodec/Mimi)│    (Zaman Hizalı Metin) │    & BARGE-IN           │
│ ────────────────────── │ ─────────────────────── │ ─────────────────────── │
│ • 24 kHz ses dalgasını │ • Sadece ses tokenıyla  │ • Sıra bekleme (Turn-   │
│   saniyede 12.5 çerçe- │   eğitilen modelin      │   taking) YOK!          │
│   veye (80ms) sıkıştır │   zekası düşer.         │ • Model her 80ms'de     │
│ • K=8 kademeli kod     │ • Çözüm: Her ses çerçe- │   [Kullanıcı_Ses_t,     │
│   kitabı (RVQ):        │   vesinde ÖNCE 1 metin  │    Model_Metin_t,       │
│   - Codebook 1: Anlam  │   tokenı (iç ses),      │    Model_Ses_t]         │
│   - Codebook 2..K:     │   hemen ardından K adet │   kanallarını eşzamanlı │
│     Kalan hata (Tını!) │   RVQ ses tokenı üret!  │   işler; söz kesilebilir│
└────────────────────────┴─────────────────────────┴─────────────────────────┘
```

---

### 1. Sürekli Ses Dalgasını Tokenlara Çevirmek: `RVQ (Residual Vector Quantization)`

Ham ses dalgası saniyede $24,000$ örnekten ($24\text{ kHz}$) oluşur. Bir `Transformer`'a saniyede $24,000$ token verirsen 5 saniyelik konuşma $120,000$ token eder ve sistem kilitlenir!

**`SoundStream` (Zeghidour et al.)**, **`EnCodec` (Meta)** ve **`Mimi` (Kyutai Moshi)** gibi **Nöral Ses Kodekleri (`Neural Audio Codecs`)**, evrişimli bir kodlayıcıyla $24\text{ kHz}$ sesi saniyede yalnızca **$12.5$ çerçeveye ($80\text{ ms}$ adıma)** indirger. Her $80\text{ ms}$'lik çerçeve $D$ boyutlu sürekli bir gizli vektör $z \in \mathbb{R}^D$ ile temsil edilir.

Peki sürekli vektör $z$'yi, `Transformer`'ın `Cross-Entropy` ile tahmin edebileceği **ayrık tam sayı `Token ID`'lerine** nasıl çeviririz?
Eğer tek bir kod kitabı (`Single Codebook Vector Quantization - VQ`) kullanırsak, yüksek ses kalitesi için $2^{80}$ boyutunda imkansız bir sözlük gerekir!

**Çözüm: `RVQ (Residual Vector Quantization)` (Kademeli Kalıntı Vektör Niceleme)!**
Tek bir dev sözlük yerine, her biri küçük (ör. $M = 1024$ veya $2048$ vektörlü) **$K$ adet kademeli kod kitabı** ($\mathcal{C}^{(1)}, \mathcal{C}^{(2)}, \dots, \mathcal{C}^{(K)}$) kullanırız:
1. Başlangıçta 0. kalıntı (`Residual`), orijinal ses vektörünün kendisidir: $r^{(0)} = z$.
2. Her kademe $k = 1, \dots, K$ için:
   - Mevcut kalıntı vektörü $r^{(k-1)}$'e Öklid mesafesi (`L2 Distance`) en yakın olan kod kitabı vektörünü seç:
     $$idx_k = \arg\min_{j \in \{0, \dots, M-1\}} \left\| r^{(k-1)} - \mathcal{C}^{(k)}_j \right\|_2^2$$
   - Seçilen quantization vektörünü kalıntıdan çıkararak **geriye kalan hatayı (`New Residual`)** bir sonraki kod kitabına devret:
     $$r^{(k)} = r^{(k-1)} - \mathcal{C}^{(k)}_{idx_k}$$
3. **Yeniden İnşa (`Reconstruction`):** Seçilen $K$ adet vektörün toplamı orijinal ses vektörünü yüksek sadakatle geri verir:

$$\hat{z} = \sum_{k=1}^{K} \mathcal{C}^{(k)}_{idx_k}, \qquad \text{Kalan Son Hata: } r^{(K)} = z - \hat{z}$$

#### Neden İlk Kod Kitabı "Anlamı (`Semantic`)", Sonrakiler "Tınıyı (`Acoustic`)" Tutar?
Özellikle `Moshi / Mimi` mimarisinde **1. Kod Kitabı (`Codebook 1`)** bir `WavLM` modelinden damıtılarak (`Semantic Distillation`) kelimelerin fonetik ve anlamsal bilgisini tutmaya zorlanır; **2'den $K$'ya kadar olan kod kitapları (`Acoustic Codebooks`)** ise sesin tınısını, duygusunu, nefes alışını ve mikrofon akustiğini adım adım tamamlar!

```python
# 2 Kademeli (K=2) RVQ Niceleme ve Hata Azaltma Simülasyonu
z = [2.3, -1.4]  # Orijinal ses çerçevesi vektörü
codebook_1 = [[0.0, 0.0], [2.0, -1.0], [-2.0, 1.0]]      # Kaba anlamsal merkezler
codebook_2 = [[0.0, 0.0], [0.25, -0.35], [-0.25, 0.35]]  # İnce akustik düzeltmeler

# Kademe 1: z=[2.3, -1.4]'e en yakın vektör codebook_1[1] = [2.0, -1.0]
q1 = codebook_1[1]
r1 = [round(z[0] - q1[0], 4), round(z[1] - q1[1], 4)]   # Kalıntı 1: [0.3, -0.4]

# Kademe 2: r1=[0.3, -0.4]'e en yakın vektör codebook_2[1] = [0.25, -0.35]
q2 = codebook_2[1]
r2 = [round(r1[0] - q2[0], 4), round(r1[1] - q2[1], 4)] # Kalıntı 2: [0.05, -0.05]
z_hat = [round(q1[0] + q2[0], 4), round(q1[1] + q2[1], 4)]

print(f"Kademe 1 Kalinti={r1} | Kademe 2 Kalinti={r2}")
print(f"Orijinal z={z} -> RVQ Yeniden Insa z_hat={z_hat}")
```

---

### 2. `Inner Monologue` ve `Full-Duplex (Tam Çift Yönlü)` Söz Kesme (`Barge-In`)

#### A) `Inner Monologue` (İç Monolog)
Bir modeli sadece ses tokenlarıyla eğitirsen akustik olarak güzel konuşur ama mantıksal muhakeme yeteneği düşer. **Moshi** mimarisi bunu **`Inner Monologue`** ile çözer:
Her $80\text{ ms}$ zaman adımında model kendi içinde **önce 1 adet metin tokenı (`Text Token` — kendi söyleyeceği kelimenin iç sesi)** üretir, hemen mikrosaniyeler sonra bu metin tokenına koşullu olarak $K$ adet **`RVQ` ses tokenını** üretir! Böylece metin LLM'in zekası ile doğrudan ses üretiminin sıfır gecikmesi birleşir!

#### B) `Full-Duplex` ve `Barge-In` (Söz Kesme Yönetimi)
Klasik sistemler telsiz (`Half-Duplex / Walkie-Talkie`) gibidir: Ya sadece kullanıcı konuşur ya da sadece model konuşur. **`Full-Duplex`** mimaride ise model konuşurken bile mikrofon kanalı (`User Audio Stream`) açıktır!
- Kullanıcı sadece *"Hı-hı, evet"* gibi kısa bir onay (`Backchanneling` — örn. 1–2 çerçeve süren ses enerjisi) verdiğinde model konuşmasını **kesmez**, devam eder!
- Ancak kullanıcının ses enerjisi (`RMS Energy` / `VAD Probability`) belirlenen eşiği (`esik_enerji`) **en az $N_{\text{ardışık}}$ çerçeve boyunca kesintisiz aşarsa**, bu gerçek bir **Söz Kesme (`Barge-In / Interruption`)** demektir! Motor anında modelin ses çıkış tamponunu (`Output Audio Buffer`) susturur (sıfırlar) ve kullanıcının yeni sorusunu dinleme moduna geçer!

---

### 3. Gerçek PyTorch Üretim Kodu: `ResidualVectorQuantizer` (`Straight-Through Estimator`)

Vektör nicelemede $\arg\min$ işlemi türevlenemez (`Non-Differentiable`) olduğu için eğitim sırasında gradyanları kodlayıcıya geri taşımak adına **Bengio'nun `Straight-Through Estimator (STE)`** hilesi (`z_q = z + (z_q - z).detach()`) kullanılır:

```python norun
import torch
import torch.nn as nn

class ResidualVectorQuantizer(nn.Module):
    def __init__(self, num_quantizers: int = 8, codebook_size: int = 1024, dim: int = 256):
        super().__init__()
        self.codebooks = nn.ModuleList([
            nn.Embedding(codebook_size, dim) for _ in range(num_quantizers)
        ])

    def forward(self, z: torch.Tensor):
        # z: (Batch, SeqLen, Dim)
        residual = z
        quantized_out = torch.zeros_like(z)
        all_indices = []
        commitment_loss = 0.0

        for codebook in self.codebooks:
            # L2 mesafesi: ||r - e||^2 = ||r||^2 + ||e||^2 - 2 * (r @ e^T)
            emb = codebook.weight  # (CodebookSize, Dim)
            dist = (
                residual.pow(2).sum(dim=-1, keepdim=True)
                + emb.pow(2).sum(dim=-1).unsqueeze(0).unsqueeze(0)
                - 2.0 * torch.matmul(residual, emb.t())
            )
            indices = torch.argmin(dist, dim=-1)  # (Batch, SeqLen)
            z_q = codebook(indices)               # (Batch, SeqLen, Dim)

            # Kalıntıyı güncelle ve niceleme çıktısını topla
            commitment_loss = commitment_loss + (residual.detach() - z_q).pow(2).mean()
            residual = residual - z_q.detach()
            quantized_out = quantized_out + z_q
            all_indices.append(indices)

        # Straight-Through Estimator (STE): İleri geçişte quantized_out, geri yayılımda z gradyanı!
        quantized_ste = z + (quantized_out - z).detach()
        codes = torch.stack(all_indices, dim=1)  # (Batch, NumQuantizers, SeqLen)
        return quantized_ste, codes, commitment_loss
```

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [Moshi teknik raporu](https://arxiv.org/abs/2410.00037). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: tahmin RVQ Saniye Başına Bit Hızı (Bitrate) Hesabı
Bir `Neural Audio Codec` (ör. `Mimi / EnCodec`) sesi saniyede $f_{\text{frame}} = 12.5$ çerçeveye ($80\text{ ms}$) bölmekte ve her çerçevede her biri $M = 1024$ ($2^{10}$, yani `10 bit`) büyüklüğünde $K = 8$ adet `RVQ` kod kitabı kullanmaktadır.
Sıkıştırılmamış $24\text{ kHz}$ 16-bit PCM sesin bit hızı $24000 \times 16 = 384\text{ kbps}$ iken, bu `RVQ` kodeğinin saniye başına ürettiği toplam ayrık token sayısı ve bit hızı (`kbps`) nedir?

```python
cerceve_hizi = 12.5       # Hz (saniyedeki çerçeve sayısı)
kod_kitabi_sayisi = 8     # K = 8 RVQ katmanı
sozluk_boyutu = 1024      # 2^10 -> her token 10 bit

saniyede_token = int(cerceve_hizi * kod_kitabi_sayisi)
token_basina_bit = 10
bit_hizi_bps = saniyede_token * token_basina_bit
kbps = bit_hizi_bps / 1000.0

print(f"SaniyedeToken={saniyede_token} | BitHizi={kbps} kbps ({round(384 / kbps, 1)}x Sikistirma!)")
```

???

```cikti
SaniyedeToken=100 | BitHizi=1.0 kbps (384.0x Sikistirma!)
```
Saniyede $12.5$ çerçeve $\times 8$ kod kitabı = saniyede yalnızca `100` ayrık ses tokenı üretilir! Her token $\log_2(1024) = 10$ bit yer kapladığı için toplam bit hızı $100 \times 10 = 1000\text{ bps} = 1.0\text{ kbps}$ olur (ham $384\text{ kbps}$ PCM sese kıyasla **384 kat sıkıştırma**!).
:::

::: gorev 1 · K-Katmanlı Residual Vector Quantization (RVQ) Kodlama ve Yeniden İnşa
Verilen $D$ boyutlu bir sürekli ses çerçevesi vektörü (`ses_vektoru`) üzerinde $K$ katmanlı **`Residual Vector Quantization (RVQ)`** algoritmasını çalıştıran `rvq_nicele(ses_vektoru, kod_kitaplari)` işlevini yaz.

**Girdi Kuralları ve Doğrulama:**
- `ses_vektoru`: Uzunluğu $D \ge 1$ olan 1B sayı listesi (`bool` olmayan sonlu sayılar).
- `kod_kitaplari`: Uzunluğu $K \ge 1$ olan 3B liste (`list[list[list[float]]]`).
  - Her kod kitabı $k \in \{0, \dots, K-1\}$, en az 1 adet ($M_k \ge 1$) $D$ boyutlu kod vektörü içermelidir.

**Hesaplama Kuralları:**
1. Başlangıç kalıntısı $r = \text{list(ses\_vektoru)}$ ve yeniden inşa vektörü $\hat{z} = [0.0, \dots, 0.0]$.
2. Her kod kitabı $k = 0, \dots, K-1$ için:
   - Kod kitabındaki aday vektörler $c_j$ ($j \in \{0, \dots, M_k-1\}$) arasında mevcut kalıntı $r$'ye karesel Öklid mesafesi ($\sum_{i=0}^{D-1} (r[i] - c_j[i])^2$) **en küçük olan indisi** $j^*$ seç (eşitlik durumunda daha küçük indisi seç).
   - Seçilen indisi `token_indisleri` listesine ekle.
   - Yeniden inşa vektörünü güncelle: $\hat{z}[i] \leftarrow \hat{z}[i] + c_{j^*}[i]$.
   - Yeni kalıntıyı güncelle: $r[i] \leftarrow r[i] - c_{j^*}[i]$.
   - Bu kademe sonundaki kalıntının ortalama karesel hatasını ($\frac{1}{D} \sum_{i=0}^{D-1} r[i]^2$) `kademe_mse_listesi` listesine ekle.
3. İşlev şu sözlüğü döndürmelidir:
   `{"token_indisleri": [...], "yeniden_insa": [...], "son_kalinti": [...], "kademe_mse_listesi": [...]}`
- Geçersiz herhangi bir girdide veya boyut uyuşmazlığında `ValueError` yükseltilmelidir.

```starter
import math

# KUSURLU BAŞLANGIÇ KODU: Kalıntıyı (residual) bir sonraki kod kitabına aktarmıyor, hep orijinal vektörü niceliyor!
def rvq_nicele(ses_vektoru, kod_kitaplari):
     d = len(ses_vektoru)
     indisler = []
     insa = [0.0] * d
     mse_list = []
     for kitap in kod_kitaplari:
         en_yakin = 0
         indisler.append(en_yakin)
         for i in range(d):
             insa[i] += kitap[en_yakin][i]
         mse_list.append(0.0)
     return {
         "token_indisleri": indisler,
         "yeniden_insa": insa,
         "son_kalinti": [ses_vektoru[i] - insa[i] for i in range(d)],
         "kademe_mse_listesi": mse_list,
     }

z_orn = [2.3, -1.4]
kitaplar_orn = [
    [[0.0, 0.0], [2.0, -1.0], [-2.0, 1.0]],
    [[0.0, 0.0], [0.25, -0.35], [-0.25, 0.35]],
]
print(rvq_nicele(z_orn, kitaplar_orn))
```
```test
def sinama_rvq(f):
    import copy, math, random
    def _ref(z, kitaplar):
        d = len(z)
        r = [float(v) for v in z]
        insa = [0.0] * d
        indisler = []
        mseler = []
        for kitap in kitaplar:
            sec = min(range(len(kitap)), key=lambda j: (sum((r[i] - float(kitap[j][i])) ** 2 for i in range(d)), j))
            indisler.append(sec)
            for i in range(d):
                v = float(kitap[sec][i])
                insa[i] += v
                r[i] -= v
            mseler.append(sum(x * x for x in r) / d)
        return {
            "token_indisleri": indisler,
            "yeniden_insa": insa,
            "son_kalinti": r,
            "kademe_mse_listesi": mseler,
        }
    def _yakin(a, b):
        keys = {"token_indisleri", "yeniden_insa", "son_kalinti", "kademe_mse_listesi"}
        if not isinstance(a, dict) or set(a.keys()) != keys:
            return False
        if a["token_indisleri"] != b["token_indisleri"]:
            return False
        for k in ("yeniden_insa", "son_kalinti", "kademe_mse_listesi"):
            if not isinstance(a[k], list) or len(a[k]) != len(b[k]):
                return False
            if any(abs(u - v) > 1e-10 for u, v in zip(a[k], b[k])):
                return False
        return True
    try:
        z = [2.3, -1.4]
        kb = [
            [[0.0, 0.0], [2.0, -1.0], [-2.0, 1.0]],
            [[0.0, 0.0], [0.25, -0.35], [-0.25, 0.35]],
        ]
        oz, okb = list(z), copy.deepcopy(kb)
        out = f(z, kb)
        if z != oz or kb != okb or not _yakin(out, _ref(z, kb)):
            return False
        if out["token_indisleri"] != [1, 1] or out["kademe_mse_listesi"][1] >= out["kademe_mse_listesi"][0]:
            return False

        rng = random.Random(2901)
        for _ in range(25):
            d = rng.randint(2, 5)
            K = rng.randint(2, 4)
            M = rng.randint(3, 6)
            zz = [rng.uniform(-3.0, 3.0) for _ in range(d)]
            kk = [[[rng.uniform(-1.5, 1.5) for _ in range(d)] for _ in range(M)] for _ in range(K)]
            if not _yakin(f(zz, kk), _ref(zz, kk)):
                return False

        bad_cases = [
            ([], [[[]]]),
            ([], kb),
            (z, [[[1.0, True]]]),
            (z, [[[1.0, float("nan")]]]),
            (z, []),
            (z, [[]]),
            (z, [[[1.0]]]),  # D uyuşmazlığı
            ([1.0, True], kb),
            ([1.0, float("nan")], kb),
        ]
        for bz, bk in bad_cases:
            try:
                f(bz, bk)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

rvq_nicele = need("rvq_nicele")
ok(sinama_rvq(rvq_nicele), "K-katmanlı RVQ kalıntı niceleme, yeniden inşa ve MSE düşüşü")
for ad, mut in [
    ("kalıntı güncellemeyen", lambda z, k: dict(rvq_nicele(z, k), token_indisleri=[rvq_nicele(z, [kit])[ "token_indisleri"][0] for kit in k])),
    ("son kalıntıyı sıfır döndüren", lambda z, k: dict(rvq_nicele(z, k), son_kalinti=[0.0]*len(z))),
]:
    ok(not sinama_rvq(mut), "mutant reddedildi: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef rvq_nicele(ses_vektoru, kod_kitaplari):\n    if not isinstance(ses_vektoru, list) or not ses_vektoru or (not all((_sayi_mi(v) for v in ses_vektoru))):\n        raise ValueError('geçersiz ses_vektoru')\n    if not isinstance(kod_kitaplari, list) or not kod_kitaplari:\n        raise ValueError('boş olmayan kod_kitaplari gerekli')\n    d = len(ses_vektoru)\n    for kitap in kod_kitaplari:\n        if not isinstance(kitap, list) or not kitap:\n            raise ValueError('her kod kitabı boş olmayan bir liste olmalı')\n        for vec in kitap:\n            if not isinstance(vec, list) or len(vec) != d or (not all((_sayi_mi(v) for v in vec))):\n                raise ValueError('kod kitabı vektör boyutu ses_vektoru ile uyuşmuyor')\n    kalinti = [float(v) for v in ses_vektoru]\n    insa = [0.0] * d\n    indisler = []\n    mse_listesi = []\n    for kitap in kod_kitaplari:\n        en_yakin_indis = min(range(len(kitap)), key=lambda j: (sum(((kalinti[i] - float(kitap[j][i])) ** 2 for i in range(d))), j))\n        indisler.append(en_yakin_indis)\n        secilen_vec = kitap[en_yakin_indis]\n        for i in range(d):\n            val = float(secilen_vec[i])\n            insa[i] += val\n            kalinti[i] -= val\n        mse_listesi.append(sum((r * r for r in kalinti)) / d)\n    return {'token_indisleri': indisler, 'yeniden_insa': insa, 'son_kalinti': kalinti, 'kademe_mse_listesi': mse_listesi}", 'referans', 'exec'), _REF)
_t, _g = _ff(rvq_nicele, _REF['rvq_nicele'], ([2.3, -1.4], [[[0.0, 0.0], [2.0, -1.0], [-2.0, 1.0]], [[0.0, 0.0], [0.25, -0.35], [-0.25, 0.35]]]), tohum=2125, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (rvq_nicele): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math

def _rvq_sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def rvq_nicele(ses_vektoru, kod_kitaplari):
    if not isinstance(ses_vektoru, list) or not ses_vektoru or not all(_rvq_sayi_mi(v) for v in ses_vektoru):
        raise ValueError("geçersiz ses_vektoru")
    if not isinstance(kod_kitaplari, list) or not kod_kitaplari:
        raise ValueError("boş olmayan kod_kitaplari gerekli")

    d = len(ses_vektoru)
    for kitap in kod_kitaplari:
        if not isinstance(kitap, list) or not kitap:
            raise ValueError("her kod kitabı boş olmayan bir liste olmalı")
        for vec in kitap:
            if not isinstance(vec, list) or len(vec) != d or not all(_rvq_sayi_mi(v) for v in vec):
                raise ValueError("kod kitabı vektör boyutu ses_vektoru ile uyuşmuyor")

    kalinti = [float(v) for v in ses_vektoru]
    insa = [0.0] * d
    indisler = []
    mse_listesi = []

    for kitap in kod_kitaplari:
        en_yakin_indis = min(
            range(len(kitap)),
            key=lambda j: (sum((kalinti[i] - float(kitap[j][i])) ** 2 for i in range(d)), j),
        )
        indisler.append(en_yakin_indis)
        secilen_vec = kitap[en_yakin_indis]
        for i in range(d):
            val = float(secilen_vec[i])
            insa[i] += val
            kalinti[i] -= val
        mse_listesi.append(sum(r * r for r in kalinti) / d)

    return {
        "token_indisleri": indisler,
        "yeniden_insa": insa,
        "son_kalinti": kalinti,
        "kademe_mse_listesi": mse_listesi,
    }

if __name__ == "__main__":
    z_orn = [2.3, -1.4]
    kitaplar_orn = [
        [[0.0, 0.0], [2.0, -1.0], [-2.0, 1.0]],
        [[0.0, 0.0], [0.25, -0.35], [-0.25, 0.35]],
    ]
    print(rvq_nicele(z_orn, kitaplar_orn))
```
```hint
Her kod kitabında mevcut `kalinti` vektörüne L2 karesel uzaklığı en küçük olan indisi seç. Seçilen vektörü `insa` vektörüne ekle ve `kalinti` vektöründen çıkar (`kalinti[i] -= val`).
```
:::

::: gorev 2 · Full-Duplex Çok Kanallı Ses/Metin Akışı ve Söz Kesme (Barge-In) Algılayıcı
Bir **`Full-Duplex Speech-to-Speech`** çıkarım motorunda zaman adımları ($t = 0, \dots, T-1$) boyunca kullanıcının mikrofon ses enerjisini (`kullanici_enerji_dizisi`) ve modelin ürettiği ses genliklerini (`model_ses_dizisi`) eşzamanlı izleyerek **Kısa Onayları (`Backchannel`)** ve **Gerçek Söz Kesmeyi (`Barge-In / Interruption`)** yöneten `full_duplex_akis(kullanici_enerji_dizisi, model_ses_dizisi, esik_enerji, ardisik_cerceve)` işlevini yaz.

**Girdi Kuralları ve Doğrulama:**
- `kullanici_enerji_dizisi`: Uzunluğu $T \ge 1$ olan, elemanları $\ge 0.0$ sonlu sayılar (`bool` hariç) olan 1B liste.
- `model_ses_dizisi`: `kullanici_enerji_dizisi` ile aynı uzunlukta ($T$), elemanları sonlu sayılar (`bool` hariç) olan 1B liste.
- `esik_enerji`: Kullanıcının konuşuyor sayılması için gereken minimum enerji eşiği (`> 0.0` sonlu sayı, `bool` hariç).
- `ardisik_cerceve`: Söz kesmenin (`Barge-In`) tetiklenmesi için gereken kesintisiz aktif çerçeve sayısı $N_{\text{barge}}$ (`bool` olmayan tam sayı, $\ge 2$).

**Tam Çift Yönlü (`Full-Duplex`) Akış Kuralları:**
1. Zaman çerçevelerini $t = 0, 1, \dots, T-1$ sırasıyla işle ve bir `aktif_sayac = 0` tut:
   - Eğer `kullanici_enerji_dizisi[t] >= esik_enerji` ise `aktif_sayac += 1`, değilse `aktif_sayac = 0`.
2. **Söz Kesme (`Barge-In`) Tetiklenmesi:**
   - `aktif_sayac == ardisik_cerceve` olduğu **ilk çerçeve indisi** `kesme_cercevesi` olarak kaydedilir (tetiklendikten sonra model susturulur!).
   - Eğer hiçbir zaman `ardisik_cerceve` uzunluğuna ulaşılmazsa `kesme_cercevesi = None` ve `soz_kesildi_mi = False` olur.
3. **Çıkış Ses Dizisi (`etkin_model_sesi`):**
   - Eğer söz kesildiyse (`kesme_cercevesi` varsa), `t >= kesme_cercevesi` olan tüm çerçevelerde modelin çıkışı anında susturulur (`0.0` yapılır); önceki çerçeveler (`t < kesme_cercevesi`) kendi `float(model_ses_dizisi[t])` değerini korur.
   - Söz kesilmediyse tüm çerçeveler kendi `float(model_ses_dizisi[t])` değerini korur.
4. **Kısa Onay (`backchannel_sayisi`):**
   - Söz kesme gerçekleşmeden önce (veya hiç söz kesilmediyse tüm dizi boyunca) başlayan, `esik_enerji` üstünde kalan ancak uzunluğu `1 <= seri_uzunlugu < ardisik_cerceve` olup tekrar eşiğin altına düşen (veya söz kesilmeden dizinin sonuna ulaşan) kısa kullanıcı ses patlamalarının (`Backchannel`, örn. *"Hı-hı"*) toplam adedi (`int`).
5. İşlev şu sözlüğü döndürmelidir:
   `{"soz_kesildi_mi": bool, "kesme_cercevesi": int | None, "etkin_model_sesi": [...], "backchannel_sayisi": int}`
- Geçersiz herhangi bir girdide `ValueError` yükseltilmelidir.

```starter
import math

# KUSURLU BAŞLANGIÇ KODU: İlk eşik aşımında hemen söz kesiyor, Backchannel ile Barge-In ayrımı yapmıyor!
def full_duplex_akis(kullanici_enerji_dizisi, model_ses_dizisi, esik_enerji, ardisik_cerceve):
     etkin = [float(x) for x in model_ses_dizisi]
     kesme = None
     for t, e in enumerate(kullanici_enerji_dizisi):
         if e >= esik_enerji:
             kesme = t
             break
     return {
         "soz_kesildi_mi": kesme is not None,
         "kesme_cercevesi": kesme,
         "etkin_model_sesi": etkin,
         "backchannel_sayisi": 0,
     }

# t=1'de 1 çerçevelik kısa onay ("Hı-hı") var -> söz kesilmez!
# t=3,4,5'te 3 ardışık çerçeve eşiği aşıyor -> t=5'te Barge-In tetiklenir!
enerji = [0.1, 0.8, 0.1, 0.7, 0.9, 0.85, 0.2]
model_ses = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
print(full_duplex_akis(enerji, model_ses, esik_enerji=0.6, ardisik_cerceve=3))
```
```test
def sinama_duplex(f):
    import copy, math, random
    def _ref(ue, ms, esik, ardisik):
        T = len(ue)
        sayac = 0
        kesme = None
        backchannel = 0
        for t in range(T):
            if float(ue[t]) >= float(esik):
                sayac += 1
                if sayac == ardisik:
                    kesme = t
                    break
            else:
                if 0 < sayac < ardisik:
                    backchannel += 1
                sayac = 0
        if kesme is None and 0 < sayac < ardisik:
            backchannel += 1
        etkin = [
            0.0 if (kesme is not None and t >= kesme) else float(ms[t])
            for t in range(T)
        ]
        return {
            "soz_kesildi_mi": kesme is not None,
            "kesme_cercevesi": kesme,
            "etkin_model_sesi": etkin,
            "backchannel_sayisi": backchannel,
        }
    try:
        ue = [0.1, 0.8, 0.1, 0.7, 0.9, 0.85, 0.2]
        ms = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        oue, oms = list(ue), list(ms)
        out = f(ue, ms, 0.6, 3)
        if ue != oue or ms != oms or out != _ref(ue, ms, 0.6, 3):
            return False
        if out["soz_kesildi_mi"] is not True or out["kesme_cercevesi"] != 5 or out["backchannel_sayisi"] != 1:
            return False
        if out["etkin_model_sesi"] != [0.5, 0.5, 0.5, 0.5, 0.5, 0.0, 0.0]:
            return False

        # Hiç söz kesilmeyen, 2 adet backchannel içeren senaryo
        ue2 = [0.8, 0.8, 0.1, 0.2, 0.9, 0.1]
        ms2 = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        out2 = f(ue2, ms2, 0.5, 3)
        if out2 != _ref(ue2, ms2, 0.5, 3) or out2["soz_kesildi_mi"] is not False or out2["backchannel_sayisi"] != 2:
            return False

        sessiz_sonuc = f([0.0, 0.0], [0.3, 0.4], 0.5, 2)
        if sessiz_sonuc != {
            "soz_kesildi_mi": False, "kesme_cercevesi": None,
            "etkin_model_sesi": [0.3, 0.4], "backchannel_sayisi": 0,
        }:
            return False

        # Eşiğe eşit son çerçeve kısa seriye dahil edilir.
        kisa_sonuc = f([0.0, 0.5], [0.3, 0.4], 0.5, 2)
        if kisa_sonuc != {
            "soz_kesildi_mi": False, "kesme_cercevesi": None,
            "etkin_model_sesi": [0.3, 0.4], "backchannel_sayisi": 1,
        }:
            return False

        rng = random.Random(2902)
        for _ in range(25):
            T = rng.randint(4, 15)
            u_list = [rng.uniform(0.0, 1.0) for _ in range(T)]
            m_list = [rng.uniform(-1.0, 1.0) for _ in range(T)]
            es = rng.uniform(0.3, 0.7)
            ar = rng.randint(2, 4)
            if f(u_list, m_list, es, ar) != _ref(u_list, m_list, es, ar):
                return False

        bad_cases = [
            ([], [], 0.5, 2),
            ([0.1, 0.2], [0.5], 0.5, 2),
            ([-0.1, 0.2], [0.5, 0.5], 0.5, 2),  # negatif enerji
            ([0.1, 0.2], [0.5, 0.5], 0.0, 2),   # esik <= 0
            ([0.1, 0.2], [0.5, 0.5], 0.5, 1),   # ardisik < 2
            ([True, 0.2], [0.5, 0.5], 0.5, 2),
            ([0.1, 0.2], [0.5, 0.5], 0.5, True),
        ]
        for bu, bm, be, ba in bad_cases:
            try:
                f(bu, bm, be, ba)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

full_duplex_akis = need("full_duplex_akis")
ok(sinama_duplex(full_duplex_akis), "Full-Duplex Barge-In tespiti, model sesini susturma ve Backchannel sayımı")
for ad, mut in [
    ("model sesini susturmayan", lambda u, m, e, a: dict(full_duplex_akis(u, m, e, a), etkin_model_sesi=[float(x) for x in m])),
    ("backchannel saymayan", lambda u, m, e, a: dict(full_duplex_akis(u, m, e, a), backchannel_sayisi=0)),
]:
    ok(not sinama_duplex(mut), "mutant reddedildi: " + ad)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef full_duplex_akis(kullanici_enerji_dizisi, model_ses_dizisi, esik_enerji, ardisik_cerceve):\n    if not isinstance(kullanici_enerji_dizisi, list) or not kullanici_enerji_dizisi:\n        raise ValueError('boş olmayan kullanici_enerji_dizisi gerekli')\n    T = len(kullanici_enerji_dizisi)\n    if not isinstance(model_ses_dizisi, list) or len(model_ses_dizisi) != T:\n        raise ValueError('model_ses_dizisi uzunluğu uyuşmuyor')\n    for e, m in zip(kullanici_enerji_dizisi, model_ses_dizisi):\n        if not _sayi_mi(e) or e < 0.0 or (not _sayi_mi(m)):\n            raise ValueError('geçersiz enerji veya ses değeri')\n    if not _sayi_mi(esik_enerji) or esik_enerji <= 0.0:\n        raise ValueError('esik_enerji > 0 olmalı')\n    if isinstance(ardisik_cerceve, bool) or not isinstance(ardisik_cerceve, int) or ardisik_cerceve < 2:\n        raise ValueError('ardisik_cerceve >= 2 tam sayı olmalı')\n    sayac = 0\n    kesme_cercevesi = None\n    backchannel = 0\n    for t in range(T):\n        if float(kullanici_enerji_dizisi[t]) >= float(esik_enerji):\n            sayac += 1\n            if sayac == ardisik_cerceve:\n                kesme_cercevesi = t\n                break\n        else:\n            if 0 < sayac < ardisik_cerceve:\n                backchannel += 1\n            sayac = 0\n    if kesme_cercevesi is None and 0 < sayac < ardisik_cerceve:\n        backchannel += 1\n    etkin_ses = [0.0 if kesme_cercevesi is not None and t >= kesme_cercevesi else float(model_ses_dizisi[t]) for t in range(T)]\n    return {'soz_kesildi_mi': kesme_cercevesi is not None, 'kesme_cercevesi': kesme_cercevesi, 'etkin_model_sesi': etkin_ses, 'backchannel_sayisi': backchannel}", 'referans', 'exec'), _REF)
_t, _g = _ff(full_duplex_akis, _REF['full_duplex_akis'], ([0.1, 0.8, 0.1, 0.7, 0.9, 0.85, 0.2], [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5], 0.6, 3), tohum=2768, en_cok=600, mod='tam', butce='oto', ekler=[([0.1, 0.8, 0.1, 0.7, 0.9, 0.85, 0.2], [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5], 0.6, 3, ), ([0.1, 0.8, 0.1, 0.7, 0.9, 0.85, 0.2], [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5], 1, 3, )])
ok(_t, "farksal tarama (full_duplex_akis): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math

def _sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def full_duplex_akis(kullanici_enerji_dizisi, model_ses_dizisi, esik_enerji, ardisik_cerceve):
    if not isinstance(kullanici_enerji_dizisi, list) or not kullanici_enerji_dizisi:
        raise ValueError("boş olmayan kullanici_enerji_dizisi gerekli")
    T = len(kullanici_enerji_dizisi)
    if not isinstance(model_ses_dizisi, list) or len(model_ses_dizisi) != T:
        raise ValueError("model_ses_dizisi uzunluğu uyuşmuyor")
    for e, m in zip(kullanici_enerji_dizisi, model_ses_dizisi):
        if not _sayi_mi(e) or e < 0.0 or not _sayi_mi(m):
            raise ValueError("geçersiz enerji veya ses değeri")
    if not _sayi_mi(esik_enerji) or esik_enerji <= 0.0:
        raise ValueError("esik_enerji > 0 olmalı")
    if isinstance(ardisik_cerceve, bool) or not isinstance(ardisik_cerceve, int) or ardisik_cerceve < 2:
        raise ValueError("ardisik_cerceve >= 2 tam sayı olmalı")

    sayac = 0
    kesme_cercevesi = None
    backchannel = 0

    for t in range(T):
        if float(kullanici_enerji_dizisi[t]) >= float(esik_enerji):
            sayac += 1
            if sayac == ardisik_cerceve:
                kesme_cercevesi = t
                break
        else:
            if 0 < sayac < ardisik_cerceve:
                backchannel += 1
            sayac = 0

    if kesme_cercevesi is None and 0 < sayac < ardisik_cerceve:
        backchannel += 1

    etkin_ses = [
        0.0 if (kesme_cercevesi is not None and t >= kesme_cercevesi) else float(model_ses_dizisi[t])
        for t in range(T)
    ]

    return {
        "soz_kesildi_mi": kesme_cercevesi is not None,
        "kesme_cercevesi": kesme_cercevesi,
        "etkin_model_sesi": etkin_ses,
        "backchannel_sayisi": backchannel,
    }

if __name__ == "__main__":
    enerji = [0.1, 0.8, 0.1, 0.7, 0.9, 0.85, 0.2]
    model_ses = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
    print(full_duplex_akis(enerji, model_ses, esik_enerji=0.6, ardisik_cerceve=3))
```
```hint
Çerçeveleri sırayla gezerken `e >= esik_enerji` ise `sayac += 1` yap; `sayac == ardisik_cerceve` olduğu ilk anda `kesme_cercevesi = t` kaydedip döngüden çık. Eşiğin altına düştüğünde `0 < sayac < ardisik_cerceve` ise `backchannel += 1` artırıp sayacı sıfırla.
```
:::

::: anlat Gerçek deney: İşletim sisteminin gerçek seslerinde RVQ ve gerçek enerjiyle söz kesme
Final, bilgisayarındaki **gerçek ses dosyalarını** kullanır (Windows'ta `C:\Windows\Media\*.wav`, macOS'ta `/System/Library/Sounds`; indirme yok, PyAV ile 16 kHz mono'ya çevrilir):

- **RVQ kod kitapları:** eğitim dosyalarının 16 örneklik dalga biçimi çerçevelerinden (sessiz çerçeveler hariç, 40 000 çerçeve) **kademeli k-means** ile 8 kademe × 64 kodluk kitaplar öğrenilir: her kademe bir öncekinin kalıntısını kodlar.
- **Kodlama:** ayrılmış bir ses dosyasının 400 çerçevesi senin `rvq_nicele` işlevinle kodlanır; her kademede seçilen indis bağımsız bir referansla karşılaştırılır. Kademe sayısına göre SNR (dB) ve bit hızı (her kademe 6 bit / 16 örnek = 6 kbps) ölçülür. Kademe ekledikçe kalite artar, bit hızı doğrusal büyür.
- **Söz kesme:** başka bir gerçek sesin 20 ms'lik çerçeve enerjisi kullanıcı kanalı olur; senin `full_duplex_akis` işlevin modelin sesini nerede kestiğini bulur. Sonra 40 ms'lik tek bir tık/gürültü patlaması verilir: 2 çerçevelik eşik bunu "kullanıcı konuşuyor" sanıp sözü keser, 4 çerçevelik eşik kesmez. Gürültü enjeksiyonuyla bir sesli asistanı susturmak (DoS) bu kadar kolaydır.

**Güvenlik yönü — ses filigranı kodekten geçince:** Üretilmiş sesin kaynağını kanıtlamak için filigran kullanılır. Ayrılmış dosyanın tamamına düşük genlikli (SNR 26 dB) ±1'lik sözde rastgele bir dizi eklenir. Tespit, diziyle korelasyondan hesaplanan bir z skorudur: filigransız seste ~0, filigranlıda çok yüksektir. Sonra filigranlı ses bu dersin RVQ kodekinden 1, 2, 4 ve 8 kademeyle geçirilir. Düşük bit hızında kodek filigranı da gürültü gibi atar ve z tespit eşiğinin (4) altına iner. Kaynak doğrulaması, sesin geçeceği kodeklere karşı dayanıklı olmalıdır; aksi hâlde bir saldırgan filigranı yalnızca yeniden kodlayarak siler.

Kabul: iki işlevin farksal taramayı geçmesi; RVQ indislerinin gerçek seste referansla aynı olması; SNR'nin her kademede artması; söz kesme çerçevesinin bağımsız hesapla aynı olması; tık patlamasının 2 çerçevede söz kesip 4 çerçevede kesmemesi. Ayrıca filigran kodeksiz seste kolayca tespit edilmeli (z > 8), filigransız seste ve her kodekte z 3'ün altında kalmalı; 1 kademede z 4'ün altına inmeli, 8 kademede üstünde kalmalıdır.

**Kanıt dosyasını oku:** `kademe_snr_db`, `kademe_kbps`, `full_duplex`, `tik_yanlis_kesme`. Soru 1: Her kademe neden bir öncekinden daha az SNR kazandırıyor? Soru 2: Dalga biçimi yerine öğrenilmiş bir gizli uzayda çalışmak (EnCodec, Mimi) aynı bit hızında neden çok daha iyi ses verir? Soru 3: Eşiği büyütmek söz kesmeyi nasıl yavaşlatır, gerçek sistemler bu ödünleşimi nasıl çözer?
:::

::: gorev Gerçek deney · Gerçek sistem seslerinde RVQ kodek ve gerçek enerjiyle söz kesme
Önceki görevlerdeki `rvq_nicele`, `full_duplex_akis` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 180
```
```starter
import ai_lab
import math

def rvq_nicele(ses_vektoru, kod_kitaplari):
    d = len(ses_vektoru)
    indisler = []
    insa = [0.0] * d
    mse_list = []
    for kitap in kod_kitaplari:
        en_yakin = 0
        indisler.append(en_yakin)
        for i in range(d):
            insa[i] += kitap[en_yakin][i]
        mse_list.append(0.0)
    return {'token_indisleri': indisler, 'yeniden_insa': insa, 'son_kalinti': [ses_vektoru[i] - insa[i] for i in range(d)], 'kademe_mse_listesi': mse_list}

import math

def full_duplex_akis(kullanici_enerji_dizisi, model_ses_dizisi, esik_enerji, ardisik_cerceve):
    etkin = [float(x) for x in model_ses_dizisi]
    kesme = None
    for t, e in enumerate(kullanici_enerji_dizisi):
        if e >= esik_enerji:
            kesme = t
            break
    return {'soz_kesildi_mi': kesme is not None, 'kesme_cercevesi': kesme, 'etkin_model_sesi': etkin, 'backchannel_sayisi': 0}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_29 as D
    D.goster(rvq_nicele, full_duplex_akis)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('ses_dosyalari', 'oku', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
rvq_nicele = need("rvq_nicele")
full_duplex_akis = need("full_duplex_akis")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef rvq_nicele(ses_vektoru, kod_kitaplari):\n    if not isinstance(ses_vektoru, list) or not ses_vektoru or (not all((_sayi_mi(v) for v in ses_vektoru))):\n        raise ValueError('geçersiz ses_vektoru')\n    if not isinstance(kod_kitaplari, list) or not kod_kitaplari:\n        raise ValueError('boş olmayan kod_kitaplari gerekli')\n    d = len(ses_vektoru)\n    for kitap in kod_kitaplari:\n        if not isinstance(kitap, list) or not kitap:\n            raise ValueError('her kod kitabı boş olmayan bir liste olmalı')\n        for vec in kitap:\n            if not isinstance(vec, list) or len(vec) != d or (not all((_sayi_mi(v) for v in vec))):\n                raise ValueError('kod kitabı vektör boyutu ses_vektoru ile uyuşmuyor')\n    kalinti = [float(v) for v in ses_vektoru]\n    insa = [0.0] * d\n    indisler = []\n    mse_listesi = []\n    for kitap in kod_kitaplari:\n        en_yakin_indis = min(range(len(kitap)), key=lambda j: (sum(((kalinti[i] - float(kitap[j][i])) ** 2 for i in range(d))), j))\n        indisler.append(en_yakin_indis)\n        secilen_vec = kitap[en_yakin_indis]\n        for i in range(d):\n            val = float(secilen_vec[i])\n            insa[i] += val\n            kalinti[i] -= val\n        mse_listesi.append(sum((r * r for r in kalinti)) / d)\n    return {'token_indisleri': indisler, 'yeniden_insa': insa, 'son_kalinti': kalinti, 'kademe_mse_listesi': mse_listesi}\n\nimport math\n\ndef _sayi_mi(v):\n    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)\n\ndef full_duplex_akis(kullanici_enerji_dizisi, model_ses_dizisi, esik_enerji, ardisik_cerceve):\n    if not isinstance(kullanici_enerji_dizisi, list) or not kullanici_enerji_dizisi:\n        raise ValueError('boş olmayan kullanici_enerji_dizisi gerekli')\n    T = len(kullanici_enerji_dizisi)\n    if not isinstance(model_ses_dizisi, list) or len(model_ses_dizisi) != T:\n        raise ValueError('model_ses_dizisi uzunluğu uyuşmuyor')\n    for e, m in zip(kullanici_enerji_dizisi, model_ses_dizisi):\n        if not _sayi_mi(e) or e < 0.0 or (not _sayi_mi(m)):\n            raise ValueError('geçersiz enerji veya ses değeri')\n    if not _sayi_mi(esik_enerji) or esik_enerji <= 0.0:\n        raise ValueError('esik_enerji > 0 olmalı')\n    if isinstance(ardisik_cerceve, bool) or not isinstance(ardisik_cerceve, int) or ardisik_cerceve < 2:\n        raise ValueError('ardisik_cerceve >= 2 tam sayı olmalı')\n    sayac = 0\n    kesme_cercevesi = None\n    backchannel = 0\n    for t in range(T):\n        if float(kullanici_enerji_dizisi[t]) >= float(esik_enerji):\n            sayac += 1\n            if sayac == ardisik_cerceve:\n                kesme_cercevesi = t\n                break\n        else:\n            if 0 < sayac < ardisik_cerceve:\n                backchannel += 1\n            sayac = 0\n    if kesme_cercevesi is None and 0 < sayac < ardisik_cerceve:\n        backchannel += 1\n    etkin_ses = [0.0 if kesme_cercevesi is not None and t >= kesme_cercevesi else float(model_ses_dizisi[t]) for t in range(T)]\n    return {'soz_kesildi_mi': kesme_cercevesi is not None, 'kesme_cercevesi': kesme_cercevesi, 'etkin_model_sesi': etkin_ses, 'backchannel_sayisi': backchannel}", 'referans', 'exec'), _REF)
_t, _g = _ff(rvq_nicele, _REF['rvq_nicele'], ([2.3, -1.4], [[[0.0, 0.0], [2.0, -1.0], [-2.0, 1.0]], [[0.0, 0.0], [0.25, -0.35], [-0.25, 0.35]]]), tohum=2125, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (rvq_nicele): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(full_duplex_akis, _REF['full_duplex_akis'], ([0.1, 0.8, 0.1, 0.7, 0.9, 0.85, 0.2], [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5], 0.6, 3), tohum=2768, en_cok=600, mod='tam', butce='oto', ekler=[([0.1, 0.8, 0.1, 0.7, 0.9, 0.85, 0.2], [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5], 0.6, 3, ), ([0.1, 0.8, 0.1, 0.7, 0.9, 0.85, 0.2], [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5], 1, 3, )])
kontrol(_t, "farksal tarama (full_duplex_akis): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
def _birim_29():
    for _args in (([], [[[]]]), ([1.0], [[[True]]]), ([1.0], [[[float("nan")]]]), (["x"], [[[1.0]]])):
        try:
            rvq_nicele(*_args)
            return False
        except ValueError:
            pass
    if full_duplex_akis([0.0, 0.5], [0.3, 0.4], 0.5, 2) != {"soz_kesildi_mi": False, "kesme_cercevesi": None, "etkin_model_sesi": [0.3, 0.4], "backchannel_sayisi": 1}:
        return False
    if full_duplex_akis([0.0, 0.0], [0.3, 0.4], 0.5, 2) != {"soz_kesildi_mi": False, "kesme_cercevesi": None, "etkin_model_sesi": [0.3, 0.4], "backchannel_sayisi": 0}:
        return False
    for _args in (([], [], 0.5, 2), ([True, 0.2], [0.5, 0.5], 0.5, 2), ([0.1, 0.2], [0.5, 0.5], 0.5, True)):
        try:
            full_duplex_akis(*_args)
            return False
        except ValueError:
            pass
    return True
kontrol(_birim_29(), "RVQ doğrulama ve Full-Duplex sondaki backchannel sözleşmesi")
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_29 as D
try: r = D.deney(rvq_nicele, full_duplex_akis)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['rvq_ayni'] and r['snr_artiyor'], 'RVQ indisleri gerçek seste referansla aynı; SNR her kademede artıyor')
kontrol(r['kesme_dogru'], 'gerçek ses enerjisinde söz kesme çerçevesi bağımsız hesapla aynı')
kontrol(r['tik_korumasi'], "40 ms'lik tık 2 çerçeve eşiğinde söz kesiyor, 4 çerçeve eşiğinde kesmiyor")
kontrol(r['filigran_dusuk_bitte_kayboluyor'], 'filigran düşük bit hızlı RVQ kodekinde tespit eşiğinin altına indi, yüksek bit hızında korundu')
ai_lab.kanit_yaz("ai-uretim-29-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-29", "deney": r})
```
```solution
import ai_lab
import math

def _rvq_sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def rvq_nicele(ses_vektoru, kod_kitaplari):
    if not isinstance(ses_vektoru, list) or not ses_vektoru or (not all((_rvq_sayi_mi(v) for v in ses_vektoru))):
        raise ValueError('geçersiz ses_vektoru')
    if not isinstance(kod_kitaplari, list) or not kod_kitaplari:
        raise ValueError('boş olmayan kod_kitaplari gerekli')
    d = len(ses_vektoru)
    for kitap in kod_kitaplari:
        if not isinstance(kitap, list) or not kitap:
            raise ValueError('her kod kitabı boş olmayan bir liste olmalı')
        for vec in kitap:
            if not isinstance(vec, list) or len(vec) != d or (not all((_rvq_sayi_mi(v) for v in vec))):
                raise ValueError('kod kitabı vektör boyutu ses_vektoru ile uyuşmuyor')
    kalinti = [float(v) for v in ses_vektoru]
    insa = [0.0] * d
    indisler = []
    mse_listesi = []
    for kitap in kod_kitaplari:
        en_yakin_indis = min(range(len(kitap)), key=lambda j: (sum(((kalinti[i] - float(kitap[j][i])) ** 2 for i in range(d))), j))
        indisler.append(en_yakin_indis)
        secilen_vec = kitap[en_yakin_indis]
        for i in range(d):
            val = float(secilen_vec[i])
            insa[i] += val
            kalinti[i] -= val
        mse_listesi.append(sum((r * r for r in kalinti)) / d)
    return {'token_indisleri': indisler, 'yeniden_insa': insa, 'son_kalinti': kalinti, 'kademe_mse_listesi': mse_listesi}

import math

def _sayi_mi(v):
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)

def full_duplex_akis(kullanici_enerji_dizisi, model_ses_dizisi, esik_enerji, ardisik_cerceve):
    if not isinstance(kullanici_enerji_dizisi, list) or not kullanici_enerji_dizisi:
        raise ValueError('boş olmayan kullanici_enerji_dizisi gerekli')
    T = len(kullanici_enerji_dizisi)
    if not isinstance(model_ses_dizisi, list) or len(model_ses_dizisi) != T:
        raise ValueError('model_ses_dizisi uzunluğu uyuşmuyor')
    for e, m in zip(kullanici_enerji_dizisi, model_ses_dizisi):
        if not _sayi_mi(e) or e < 0.0 or (not _sayi_mi(m)):
            raise ValueError('geçersiz enerji veya ses değeri')
    if not _sayi_mi(esik_enerji) or esik_enerji <= 0.0:
        raise ValueError('esik_enerji > 0 olmalı')
    if isinstance(ardisik_cerceve, bool) or not isinstance(ardisik_cerceve, int) or ardisik_cerceve < 2:
        raise ValueError('ardisik_cerceve >= 2 tam sayı olmalı')
    sayac = 0
    kesme_cercevesi = None
    backchannel = 0
    for t in range(T):
        if float(kullanici_enerji_dizisi[t]) >= float(esik_enerji):
            sayac += 1
            if sayac == ardisik_cerceve:
                kesme_cercevesi = t
                break
        else:
            if 0 < sayac < ardisik_cerceve:
                backchannel += 1
            sayac = 0
    if kesme_cercevesi is None and 0 < sayac < ardisik_cerceve:
        backchannel += 1
    etkin_ses = [0.0 if kesme_cercevesi is not None and t >= kesme_cercevesi else float(model_ses_dizisi[t]) for t in range(T)]
    return {'soz_kesildi_mi': kesme_cercevesi is not None, 'kesme_cercevesi': kesme_cercevesi, 'etkin_model_sesi': etkin_ses, 'backchannel_sayisi': backchannel}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_29 as D
    D.goster(rvq_nicele, full_duplex_akis)
```
```hint
İki görevin çözümlerini olduğu gibi buraya koy.
```
:::

::: anlat Sınır
Görevler K katmanlı RVQ kodlamasını ve yeniden inşayı, full-duplex akışta barge-in algılamayı küçük vektörler ve enerji dizileriyle hesaplatır; final adım işletim sisteminin gerçek ses dosyalarında kod kitabı öğrenip kodlar (gerçek bir codec ya da konuşma modeli kullanılmaz). RVQ kod kitapları eğitimle öğrenilir; final adım bunu gerçek seslerde k-means ile yapar. Enerji eşiğine dayalı söz kesme algılayıcısı gürültüde, yankıda ve modelin kendi sesi mikrofona geri döndüğünde yanlış tetiklenir; gerçek sistemler yankı iptali ve öğrenilmiş bir VAD kullanır. Ses klonlama ve sahte ses (voice spoofing) riskleri bu derste ele alınmaz.

Kaynaklar: [Zeghidour vd. 2021 - SoundStream: An End-to-End Neural Audio Codec](https://arxiv.org/abs/2107.03312), [Défossez vd. 2022 - High Fidelity Neural Audio Compression](https://arxiv.org/abs/2210.13438), [Défossez vd. 2024 - Moshi: a speech-text foundation model for real-time dialogue](https://arxiv.org/abs/2410.00037).
:::

::: dusun
Bir `Native Speech-to-Speech` modelde her $80\text{ ms}$'lik çerçevede $K = 8$ adet `RVQ` ses tokenı üretilmesi gerekiyor. Eğer ana `7B` veya `70B Temporal Transformer` modelini her çerçevede 8 kez ardışık çalıştırırsan gecikme 8 katına çıkar ve gerçek zamanlı ($80\text{ ms}$) sınırı aşılır!

**Kyutai Moshi (`RQ-Transformer / Depth Transformer`) Mimari Sorusu:** Ana büyük `Temporal Transformer` her $80\text{ ms}$'de yalnızca **1 kez** çalışıp tek bir bağlam vektörü $h_t$ üretirken, o çerçeveye ait $K = 8$ `RVQ` kod kitabını çok küçük (ör. sadece `20M` parametreli) bir **`Depth Transformer`** ile milisaniyeler içinde nasıl otoregresif olarak ($c_{t,1} \to c_{t,2} \to \dots \to c_{t,8}$) çözeriz?
:::

::: ozet
- **`RVQ (Residual Vector Quantization)`**, sürekli ses çerçevelerini $K$ adet kademeli kod kitabıyla niceler; ilk kod kitabı fonetik/anlamsal yapıyı (`Semantic`), sonraki kod kitapları ise kalan hatayı (`Residual`) kodlayarak sesin tınısını ve duygusunu (`Acoustic`) yakalar.
- **`Inner Monologue`**, her ses çerçevesinden hemen önce zaman-hizalı bir metin tokenı üreterek `Speech-to-Speech` modelin dilbilgisel ve mantıksal muhakeme gücünü korur.
- **`Full-Duplex` Mimari**, kullanıcının ve modelin ses akışlarını paralel kanallarda eşzamanlı işleyerek kısa onayları (`Backchanneling`) gerçek söz kesmelerden (`Barge-In`) ayırır ve milisaniyelik doğal diyalog sağlar.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Kademeli kalıntı niceleme (`RVQ`) (30 sn).** "Tek bir dev kod kitabı yerine her kademe bir öncekinin bıraktığı hatayı (`kalıntı`) niceler; ilk kademeler kaba zarfı, sonraki kademeler ince akustik ayrıntıyı taşır ve her kademede SNR yükselir."
2. **Söz kesme (`barge-in`) vs `backchannel` (30 sn).** "`Full-duplex` akışta tek çerçevelik tık veya 'hı-hı' onayı modeli susturmamalıdır; yalnızca eşiği ardışık $N$ çerçeve aşan enerji gerçek söz kesme sayılır."
3. **Düşük bit hızında filigran kaybı (35 sn).** "Deneyde gördüğümüz gibi düşük bit hızlı RVQ sıkıştırması ince kalıntıyı attığı için akustik filigranı da silebilir; yüksek bit hızında ise kalıntı katmanları filigranı korur."
4. **Soru (25 sn).** "Enerji eşiğine dayalı basit söz kesme algılayıcısı hoparlör yankısında neden yanılır ve gerçek sistemler bunu hangi iki bileşenle çözer?"
:::
