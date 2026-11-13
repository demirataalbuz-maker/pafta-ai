---
id: ai-temel-37
title: Sıfırdan Kendi Dil Modelini (Mini-LLM) Üretmek · Uçtan Uca Mimari ve Eğitim
summary: Hiçbir hazır model ağırlığı kullanmadan sıfırdan (From Scratch) kendi çalışan Dil Modelini (GPT/Transformer) inşa etmek: Tokenizer, Embedding, Causal Self-Attention, MLP, Pre-training Loop, SFT ve Autoregressive Generation.
esleme: ai-temel-05, ai-temel-06, ai-temel-09
---

::: anlat 1. "Ben Şu An Sıfırdan Kendi Yapay Zekamı Üretebilir miyim?" — Evet, İşte Tam Mimari!
Teoriyi öğrendik; peki gerçekten boş bir `.py` dosyası açıp, hiçbir hazır kütüphane ağırlığı indirmeden **sıfırdan (`From Scratch`) kendi çalışan dil modelini (`Mini-LLM / GPT`)** nasıl kodlarsın ve eğitirsin?

Bir `Frontier Model` ($1\text{ Trilyon}$ parametre) ile kendi bilgisayarında sıfırdan eğiteceğin bir `Mini-LLM` ($10\text{ Milyon} - 1\text{ Milyar}$ parametre) arasında **kod mimarisi açısından HİÇBİR FARK YOKTUR!** İkisi de tam olarak aynı **6 yapıtaşının** üst üste konmasıyla inşa edilir:

```text
[1. Tokenizer (Metin -> Tam Sayı Token ID'leri: [14, 82, 9, ...])]
        │
        ▼
[2. Token Embedding (W_te) + Positional Encoding (W_pe / RoPE) -> Vektör Uzayı (T x d_model)]
        │
        ▼
[3. N x Transformer Block (Beyin Katmanları)]
    ├── LayerNorm / RMSNorm
    ├── Causal Multi-Head Self-Attention (Q, K, V + Nedensel Maske + Residual Bağlantı)
    ├── LayerNorm / RMSNorm
    └── Feed-Forward Network / SwiGLU MLP (Bilgi İşleme + Residual Bağlantı)
        │
        ▼
[4. Language Modeling Head (LM Head: d_model -> Vocab Size Logits)]
        │
        ▼
[5. Pre-training Loop (Cross-Entropy Loss -> Backward Pass -> AdamW Weight Update)]
        │
        ▼
[6. Autoregressive Decoding (Softmax + Temperature/Top-p Sampling -> Yeni Token Üretimi!)]
```

Şimdi bu 6 parçanın her birini nasıl kodlayacağını ve kendi GPU'nda nasıl eğiteceğini adım adım kuralım.
:::

::: anlat 2. Adım 1 & 2: Tokenizer ve Embedding Tablosu (Kelimeleri Geometrik Vektörlere Çevirmek)
Bilgisayarın işlemcisi `"yapay zeka"` kelimesinden anlamaz; sadece sayılarla matris çarpımı yapabilir.
1. **`Byte-Pair Encoding (BPE) Tokenizer`:** Önce eğitim metnimizde en sık yan yana gelen harf/byte çiftlerini birleştirerek bir sözlük (**`Vocabulary`**, örn. $V = 32.000$ parça) oluştururuz. Her parçaya $0$ ile $V-1$ arasında bir kimlik numarası (**`Token ID`**) verilir.
2. **`Token Embedding Matrix` ($W_E \in \mathbb{R}^{V \times d_{\text{model}}}$):** Her `Token ID`, $d_{\text{model}}$ boyutlu (örn. $768$ veya $4096$ sayıdan oluşan) öğrenilebilir bir vektör satırına karşılık gelir.
3. **`Positional Information` ($W_P$ veya `RoPE`):** `Attention` mekanizması kelimelerin sırasını doğuştan bilmez (`"Ali köpeği ısırdı"` ile `"Köpek Ali'yi ısırdı"` aynı kelimelerdir!). Bu yüzden her kelimenin vektörüne, cümledeki sırasını ($t = 0, 1, 2, \dots$) kodlayan konumsal vektör eklenir:

$$h_t^{(0)} = W_E[\text{token}_t] + W_P[t]$$
:::

::: anlat 3. Adım 3: Transformer Bloğunun Kalbi (Causal Self-Attention + MLP + Residual Stream)
Giriş vektörlerimiz ($H^{(0)}$) hazır. Şimdi bunları üst üste dizilmiş $L$ adet özdeş **`Transformer Block`** katmanından geçiriyoruz. Her katman **iki ana iş** yapar:

### 1. `Causal Self-Attention` (Kelimeler Arası İletişim)
Her kelime vektörü ($x_t$), üç farklı matrisle çarpılarak üç role bürünür:
- **`Query` ($q_t = x_t W_Q$):** *"Ben şu an ne arıyorum?"* (Örn. `"onu"` zamiri: *"Ben hangi ismin yerine geçtim?"* diye sorar).
- **`Key` ($k_j = x_j W_K$):** *"Bende ne bilgisi var?"* (Örn. cümlenin başındaki `"kitap"` kelimesi: *"Ben cansız bir nesneyim"* etiketi taşır).
- **`Value` ($v_j = x_j W_V$):** *"Eğer beni seçersen sana hangi anlamı aktaracağım?"*

Dikkat skoru, `Query` ile önceki kelimelerin `Key` vektörlerinin iç çarpımıdır (`Dot Product`). Ancak modelin **gelecekteki kelimelere bakıp kopya çekmemesi** için $j > t$ olan tüm gelecek konumlara $-\infty$ konulur (**`Causal Mask`**):

$$\text{Attention}(Q, K, V) = \text{Softmax}\left(\frac{QK^\top}{\sqrt{d_k}} + M_{\text{causal}}\right) V$$

### 2. `Feed-Forward MLP` (Her Kelimenin Kendi İçinde Düşünmesi)
`Attention` kelimeler arasında bilgi toplar; hemen ardından gelen **`MLP` (`Feed-Forward Network` / `SwiGLU`)** ise toplanan bu bilgiyi doğrusal olmayan aktivasyonlarla (`GELU` / `SiLU`) işler. Araştırmalar, modelin **ansiklopedik bilgilerinin büyük kısmının `MLP` ağırlıklarında (`Key-Value Memory` olarak) depolandığını** göstermiştir!

### 3. `Residual Stream` ($x \leftarrow x + f(x)$)
Her alt katmanın çıktısı, girdi vektörünün üzerine **toplanarak (`Residual Connection`)** ilerler. Böylece geri yayılımda (`Backpropagation`) gradient akışı için doğrudan bir toplama yolu oluşur; bu, bütün derin ağlarda vanishing/exploding gradient riskini ortadan kaldırmaz.
:::

::: anlat 4. Adım 4 & 5: Sıfırdan Çalışan Bir Mini-LLM Eğitim Döngüsü (Canlı Simülasyon!)
**Model sınırı:** Aşağıdaki kod gerçekten ağırlık günceller; fakat Q/K/V attention, Transformer MLP ve residual block uygulamaz. Context embedding ortalaması, öğrenme döngüsünü küçük ölçekte göstermek için seçilmiştir. Yukarıdaki Transformer mimarisiyle aynı model sayılmamalıdır.

Şimdi "Yapay zeka nasıl öğreniyor?" sorusunu lafta bırakmayalım; aşağıda **hiçbir dış kütüphane kullanmadan, saf Python ile rastgele ağırlıklardan başlayıp (`Random Initialization`), `Cross-Entropy Loss` ve `Gradient Descent` ile cümle kurmayı öğrenen context embedding ortalaması ve linear output layer kullanan küçük bir dil modeli** görüyorsun.

Kodu incele: Model başlangıçta tamamen rastgele saçmalarken, eğitim adımları (`Epochs`) ilerledikçe `Loss` değerinin nasıl sıfıra yaklaştığını ve modelin cümleyi hatasız tamamlamayı nasıl öğrendiğini bizzat gözlemle!

```python
import math, random

random.seed(42)
# 1. Eğitim Verisi (Corpus) ve Tokenizer (Kelime Dağarcığı)
egitim_cumleleri = [
    ["kuantum", "bilgisayar", "superposition", "kullanir"],
    ["frontier", "model", "attention", "kullanir"],
    ["kuantum", "model", "entanglement", "uretir"],
]
vocab = sorted(list({k for c in egitim_cumleleri for k in c}))
kelime_to_id = {k: i for i, k in enumerate(vocab)}
id_to_kelime = {i: k for i, k in enumerate(vocab)}
V, d_model = len(vocab), 8

# 2. Rastgele Başlatılmış Model Ağırlıkları (Embedding E ve Çıkış Projeksiyonu W_out)
E = [[random.uniform(-0.5, 0.5) for _ in range(d_model)] for _ in range(V)]
W_out = [[random.uniform(-0.5, 0.5) for _ in range(V)] for _ in range(d_model)]

def softmax(logits):
    m = max(logits)
    exps = [math.exp(z - m) for z in logits]
    s = sum(exps)
    return [e / s for e in exps]

# 3. Pre-training Döngüsü (Forward Pass + Cross-Entropy Loss + Backprop)
lr = 0.25
for epoch in range(1, 121):
    toplam_loss = 0.0
    for cumle in egitim_cumleleri:
        for t in range(len(cumle) - 1):
            Baglam_idler = [kelime_to_id[k] for k in cumle[:t+1]]
            hedef_id = kelime_to_id[cumle[t+1]]
            # Bağlam temsilini (Causal Ortalama / Attention özeti) çıkar
            h = [sum(E[i][d] for i in Baglam_idler) / len(Baglam_idler) for d in range(d_model)]
            logits = [sum(h[d] * W_out[d][v] for d in range(d_model)) for v in range(V)]
            olasiliklar = softmax(logits)
            toplam_loss += -math.log(max(1e-12, olasiliklar[hedef_id]))
            # Geri Yayılım (Gradient: dL/dz = p - y)
            grad_z = [olasiliklar[v] - (1.0 if v == hedef_id else 0.0) for v in range(V)]
            grad_h = [sum(grad_z[v] * W_out[d][v] for v in range(V)) for d in range(d_model)]
            for d in range(d_model):
                for v in range(V):
                    W_out[d][v] -= lr * h[d] * grad_z[v]
                for i in Baglam_idler:
                    E[i][d] -= (lr / len(Baglam_idler)) * grad_h[d]
    if epoch in (1, 30, 120):
        print(f"Epoch {epoch:3d} | Cross-Entropy Loss: {toplam_loss:.4f}")

# 4. Autoregressive Generation (Eğitilen Modelden Canlı Üretim!)
baslangic = ["kuantum", "bilgisayar"]
for _ in range(2):
    ids = [kelime_to_id[k] for k in baslangic]
    h = [sum(E[i][d] for i in ids) / len(ids) for d in range(d_model)]
    logits = [sum(h[d] * W_out[d][v] for d in range(d_model)) for v in range(V)]
    secilen_id = max(range(V), key=lambda v: logits[v])
    baslangic.append(id_to_kelime[secilen_id])
print("Üretilen Cümle:", " ".join(baslangic))
```
:::

::: anlat 5. Kendi Bilgisayarında Gerçek PyTorch ile LLM Üretme Yol Haritası
Yukarıdaki 50 satırlık saf Python kodunda gördüğün döngünün (`Embedding` $\to$ `Context Mixing` $\to$ `Logits` $\to$ `Cross-Entropy Loss` $\to$ `Backpropagation`) **PyTorch ve GPU (`CUDA` / `ROCm`)** üzerindeki tam karşılığı şu şekildedir:

1. **Veri Hazırlığı:** `tiktoken` veya `SentencePiece` ile kendi metin arşivin üzerinde $16.000$ – $32.000$ kelimelik bir `BPE Tokenizer` eğitirsin (`token_ids.bin`).
2. **Model Sınıfı (`torch.nn.Module`):**
   - `nn.Embedding(vocab_size, d_model)`
   - `nn.ModuleList([TransformerBlock(d_model, n_heads) for _ in range(n_layers)])`
   - `nn.RMSNorm(d_model)` ve `nn.Linear(d_model, vocab_size, bias=False)`
3. **Senin Ekran Kartında (`16 GB` – `24 GB VRAM`) Ne Kadar Büyük Model Üretebilirsin?**
   - Tek bir modern tüketici GPU'sunda (`BF16 Mixed Precision` + `FlashAttention` + `Gradient Accumulation` kullanarak) **$125\text{ Milyon}$ ile $500\text{ Milyon}$ parametreli** tamamen kendine ait bir `GPT / Llama` mimarisini **sıfırdan (`From Scratch`)** birkaç gün içinde eğitebilirsin!
   - Açık ağırlıklı bir `7B` veya `14B` `Base Model` alıp kendi özel veri kümenle **`QLoRA` + `SFT` + `GRPO (RLVR)`** aşamalarını ise kendi ekran kartında **sadece birkaç saat içinde** tamamlayıp uzmanlaşmış bir asistana dönüştürebilirsin!
:::

::: tahmin Sıfırdan LLM Parametre Sayısı Hesabı
Kendi bilgisayarında sıfırdan küçük bir `Transformer` dil modeli (`d_model = 512`, `n_layers = 8`) tasarlıyorsun. Her bir `Transformer Block` katmanında:
- `Self-Attention` ($W_Q, W_K, W_V, W_O$): $4 \times d_{\text{model}}^2$ parametre,
- `Feed-Forward MLP` ($W_{\text{up}}, W_{\text{down}}$ — $4d_{\text{model}}$ genişlikli): $8 \times d_{\text{model}}^2$ parametre
bulunuyor. Sadece bu $8$ `Transformer` katmanındaki toplam parametre sayısı kaç milyondur?

```python
d = 512
katman_basi = (4 * (d ** 2)) + (8 * (d ** 2))  # 12 * d^2
toplam_8_katman = 8 * katman_basi
print(f"Katman Basi: {katman_basi:,} | 8 Katman Toplami: {toplam_8_katman / 1_000_000:.2f} Milyon")
```

???

```cikti
Katman Basi: 3,145,728 | 8 Katman Toplami: 25.17 Milyon
```
Her bir `Transformer` bloğunda $4d^2$ (`Attention`) + $8d^2$ (`MLP`) = $12d^2 = 12 \times 512^2 = 3.145.728$ parametre bulunur. $8$ katmanın toplamı $25.165.824$ ($\approx 25.17\text{ Milyon}$) parametre olarak hesaplanır; bu sayıdan training süresi çıkarılamaz.

Bu tahmin yalnız verilen katman parametre formülünü hesaplar. Gerçek training süresi veri, sequence length, donanım ve hedef kaliteye bağlıdır; parametre sayısından dakika garantisi çıkarılmaz.
:::

::: gorev 1 · Llama Tarzı Bir Dil Modelinin Parametrelerini Saymak
`parametre_say(V, d, L, ff, n_bas, n_kv_bas, bagli_gomme)` işlevini yaz. Mimari: token gömmesi, `L` adet blok (RMSNorm → GQA dikkat → RMSNorm → SwiGLU MLP), son RMSNorm ve çıktı katmanı; **hiçbir doğrusal katmanda bias yok**.

**Kurallar:**
1. `V`, `d`, `L`, `ff`, `n_bas`, `n_kv_bas` pozitif tam sayı (`bool` değil), `bagli_gomme` `bool` olmalı; `d`, `n_bas`'a ve `n_bas`, `n_kv_bas`'a tam bölünmeli. Değilse `ValueError`.
2. $h = d / n_{bas}$. Blok başına: dikkat $= d\cdot d$ (q) $+ 2\cdot d\cdot(n_{kv} h)$ (k, v) $+ d\cdot d$ (o); MLP $= 3\cdot d\cdot ff$ (gate, up, down); norm $= 2d$.
3. Gömme $= V d$; çıktı katmanı bağlıysa 0, değilse $V d$; son norm $d$.
4. Çıktı: `"dikkat"`, `"mlp"`, `"katman_basi"` (blok toplamı), `"gomme"`, `"cikti"`, `"toplam"`, `"gomme_orani"` (gömme + çıktı / toplam, `round(·, 6)`).

SmolLM2-135M'in yapılandırmasıyla ($V = 49152$, $d = 576$, $L = 30$, $ff = 1536$, 9 / 3 baş, bağlı gömme) sonuç modelin gerçek parametre sayısına eşit çıkmalıdır.

```starter
def parametre_say(V, d, L, ff, n_bas, n_kv_bas, bagli_gomme):
    # KUSURLU BAŞLANGIÇ: 12·d² kuralı; GQA, SwiGLU, norm ve gömmeyi yok sayıyor
    return {"dikkat": 4 * d * d, "mlp": 8 * d * d, "katman_basi": 12 * d * d, "gomme": 0, "cikti": 0,
            "toplam": 12 * d * d * L, "gomme_orani": 0.0}

print(parametre_say(49152, 576, 30, 1536, 9, 3, True))
```

```test
fn = need("parametre_say")
r = fn(49152, 576, 30, 1536, 9, 3, True)
eq(r["dikkat"], 884736, "q,o: 576², k,v: 576·192")
eq(r["mlp"], 2654208, "3·576·1536")
eq(r["katman_basi"], 3540096, "dikkat + MLP + 2 norm")
eq(r["gomme"], 28311552, "49152·576")
eq(r["cikti"], 0, "bağlı gömme")
eq(r["toplam"], 134515008, "SmolLM2-135M'in gerçek parametre sayısı")
eq(r["gomme_orani"], 0.210471, "gömme toplamın %21'i")
r2 = fn(1000, 64, 2, 128, 4, 4, False)
eq(r2["dikkat"], 16384, "MHA: 4·64²")
eq(r2["cikti"], 64000, "bağlı değil: ayrı çıktı katmanı")
eq(r2["toplam"], 64000 + 64000 + 2 * (16384 + 24576 + 128) + 64, "toplam")
raises(ValueError, fn, 1000, 64, 2, 128, 3, 3, True)
raises(ValueError, fn, 1000, 64, 2, 128, 4, 3, True)
raises(ValueError, fn, 1000, 64, 2, 128, 4, 4, 1)
raises(ValueError, fn, 0, 64, 2, 128, 4, 4, True)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile('def parametre_say(V, d, L, ff, n_bas, n_kv_bas, bagli_gomme):\n    for v in (V, d, L, ff, n_bas, n_kv_bas):\n        if isinstance(v, bool) or not isinstance(v, int) or v < 1:\n            raise ValueError(\'boyutlar pozitif tam sayı olmalı\')\n    if not isinstance(bagli_gomme, bool):\n        raise ValueError(\'bagli_gomme bool olmalı\')\n    if d % n_bas or n_bas % n_kv_bas:\n        raise ValueError("d, n_bas\'a; n_bas, n_kv_bas\'a bölünmeli")\n    h = d // n_bas\n    dikkat = 2 * d * d + 2 * d * n_kv_bas * h\n    mlp = 3 * d * ff\n    blok = dikkat + mlp + 2 * d\n    gomme = V * d\n    cikti = 0 if bagli_gomme else V * d\n    toplam = gomme + cikti + L * blok + d\n    return {\'dikkat\': dikkat, \'mlp\': mlp, \'katman_basi\': blok, \'gomme\': gomme, \'cikti\': cikti, \'toplam\': toplam, \'gomme_orani\': round((gomme + cikti) / toplam, 6)}', 'referans', 'exec'), _REF)
_t, _g = _ff(parametre_say, _REF['parametre_say'], (49152, 576, 30, 1536, 9, 3, True), tohum=2322, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (parametre_say): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def parametre_say(V, d, L, ff, n_bas, n_kv_bas, bagli_gomme):
    for v in (V, d, L, ff, n_bas, n_kv_bas):
        if isinstance(v, bool) or not isinstance(v, int) or v < 1:
            raise ValueError("boyutlar pozitif tam sayı olmalı")
    if not isinstance(bagli_gomme, bool):
        raise ValueError("bagli_gomme bool olmalı")
    if d % n_bas or n_bas % n_kv_bas:
        raise ValueError("d, n_bas'a; n_bas, n_kv_bas'a bölünmeli")
    h = d // n_bas
    dikkat = 2 * d * d + 2 * d * n_kv_bas * h
    mlp = 3 * d * ff
    blok = dikkat + mlp + 2 * d
    gomme = V * d
    cikti = 0 if bagli_gomme else V * d
    toplam = gomme + cikti + L * blok + d
    return {"dikkat": dikkat, "mlp": mlp, "katman_basi": blok, "gomme": gomme, "cikti": cikti, "toplam": toplam,
            "gomme_orani": round((gomme + cikti) / toplam, 6)}
```

```hint
GQA'da k ve v projeksiyonları d × (n_kv_bas · head_dim) boyutludur; q ve o ise d × d.
```
:::

::: gorev 2 · Karakter Bigram Dil Modeli ve Perplexity
`bigram_dil_modeli(egitim_metni, test_metni, alfa)` işlevini yaz. En basit dil modeli: bir sonraki karakterin olasılığı yalnız bir önceki karaktere bağlıdır.

**Kurallar:**
1. İki metin de en az 2 karakterli `str`, `alfa` pozitif sonlu sayı olmalı; değilse `ValueError`.
2. Sözlük $\mathcal{V}$: iki metindeki karakterlerin birleşimi (sıralı). Sayımlar yalnız eğitim metninden: $c(a, b)$ = `a` ardından `b` gelme sayısı, $c(a) = \sum_b c(a, b)$.
3. Add-α düzleştirme: $p(b \mid a) = \frac{c(a, b) + \alpha}{c(a) + \alpha |\mathcal{V}|}$.
4. Perplexity test metninin her ardışık çifti üzerinden: $\exp\big(-\frac{1}{n-1}\sum_{i=1}^{n-1} \ln p(t_i \mid t_{i-1})\big)$.
5. Çıktı: `"sozluk"` ($|\mathcal{V}|$), `"perplexity"` (`round(·, 6)`), `"en_sik_bigram"`: eğitimdeki en sık çift (iki karakterlik dizgi; eşitlikte sözlük sırasına göre ilk).

Tekdüze bir model $|\mathcal{V}|$ perplexity verir; bigram bundan iyi olmalıdır.

```starter
def bigram_dil_modeli(egitim_metni, test_metni, alfa):
    # KUSURLU BAŞLANGIÇ: tekdüze model
    V = sorted(set(egitim_metni) | set(test_metni))
    return {"sozluk": len(V), "perplexity": float(len(V)), "en_sik_bigram": egitim_metni[:2]}

print(bigram_dil_modeli("abababab", "abab", 0.5))
```

```test
fn = need("bigram_dil_modeli")
r = fn("abababab", "abab", 0.5)
eq(r["sozluk"], 2, "a ve b")
eq(r["perplexity"], 1.121594, "p(b|a) = 4.5/5, p(a|b) = 3.5/4 → exp(-(2 ln 0.9 + ln 0.875)/3)")
eq(r["en_sik_bigram"], "ab", "4 kez ab, 3 kez ba")
r2 = fn("aab", "ba", 1.0)
eq(r2["sozluk"], 2, "iki karakter")
eq(r2["perplexity"], 2.0, "b ardından hiçbir şey görülmedi: 1/2")
eq(r2["en_sik_bigram"], "aa", "aa ve ab birer kez: sözlük sırası")
r3 = fn("abc", "abd", 1.0)
eq(r3["sozluk"], 4, "test karakterleri de sözlükte")
ok(r3["perplexity"] > 1.0, "bilinmeyen karakter olasılığı küçük ama sıfır değil")
raises(ValueError, fn, "a", "ab", 1.0)
raises(ValueError, fn, "ab", "ab", 0.0)
raises(ValueError, fn, "ab", 5, 1.0)
raises(ValueError, fn, "ab", "ab", True)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef bigram_dil_modeli(egitim_metni, test_metni, alfa):\n    if not isinstance(egitim_metni, str) or not isinstance(test_metni, str) or len(egitim_metni) < 2 or (len(test_metni) < 2):\n        raise ValueError('metinler en az 2 karakterli str olmalı')\n    if isinstance(alfa, bool) or not isinstance(alfa, (int, float)) or (not math.isfinite(alfa)) or (alfa <= 0):\n        raise ValueError('alfa pozitif olmalı')\n    V = sorted(set(egitim_metni) | set(test_metni))\n    cift, tek = ({}, {})\n    for a, b in zip(egitim_metni, egitim_metni[1:]):\n        cift[a, b] = cift.get((a, b), 0) + 1\n        tek[a] = tek.get(a, 0) + 1\n    lp = 0.0\n    for a, b in zip(test_metni, test_metni[1:]):\n        lp += math.log((cift.get((a, b), 0) + alfa) / (tek.get(a, 0) + alfa * len(V)))\n    ppl = math.exp(-lp / (len(test_metni) - 1))\n    en = min(cift, key=lambda k: (-cift[k], k))\n    return {'sozluk': len(V), 'perplexity': round(ppl, 6), 'en_sik_bigram': en[0] + en[1]}", 'referans', 'exec'), _REF)
_t, _g = _ff(bigram_dil_modeli, _REF['bigram_dil_modeli'], ('abababab', 'abab', 0.5), tohum=2696, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (bigram_dil_modeli): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def bigram_dil_modeli(egitim_metni, test_metni, alfa):
    if not isinstance(egitim_metni, str) or not isinstance(test_metni, str) or len(egitim_metni) < 2 or len(test_metni) < 2:
        raise ValueError("metinler en az 2 karakterli str olmalı")
    if isinstance(alfa, bool) or not isinstance(alfa, (int, float)) or not math.isfinite(alfa) or alfa <= 0:
        raise ValueError("alfa pozitif olmalı")
    V = sorted(set(egitim_metni) | set(test_metni))
    cift, tek = {}, {}
    for a, b in zip(egitim_metni, egitim_metni[1:]):
        cift[(a, b)] = cift.get((a, b), 0) + 1
        tek[a] = tek.get(a, 0) + 1
    lp = 0.0
    for a, b in zip(test_metni, test_metni[1:]):
        lp += math.log((cift.get((a, b), 0) + alfa) / (tek.get(a, 0) + alfa * len(V)))
    ppl = math.exp(-lp / (len(test_metni) - 1))
    en = min(cift, key=lambda k: (-cift[k], k))
    return {"sozluk": len(V), "perplexity": round(ppl, 6), "en_sik_bigram": en[0] + en[1]}
```

```hint
Sayımları yalnız eğitimden al ama sözlüğü iki metnin birleşiminden kur; yoksa testte görülen yeni karakterin olasılığı tanımsız kalır.
```
:::

::: anlat Gerçek deney: Sıfırdan bir mini-LLM eğitmek ve parametre sayımını gerçek modellerle doğrulamak
Final dersin anlattığı mini-LLM'i gerçekten kurar ve eğitir (indirme yok; GPU varsa kullanılır):

- **Parametre sayımı:** senin `parametre_say` işlevin üç gerçek modelle karşılaştırılır. **SmolLM2-135M** birebir tutmalıdır (134 515 008). **Qwen2.5-0.5B** tutmaz: q/k/v projeksiyonlarında bias vardır ve fark tam olarak bias sayısıdır. Üçüncüsü az sonra eğitilecek mini modeldir.
- **Mini Llama:** 4 katman, genişlik 128, 4 sorgu / 2 KV başı, SwiGLU ara boyutu 344, bağlı gömme; ~750 bin parametre. Pafta ders metinlerinde karakter düzeyinde **sıfırdan** 1 500 adım eğitilir.
- **Karşılaştırma:** aynı doğrulama metninde tekdüze model (perplexity = sözlük boyutu), senin `bigram_dil_modeli` işlevin ve eğitilmiş mini model.
- **Üretim ve kopya:** mini model "Model " önekinden 240 karakter üretir. Üretilen metnin eğitim metninde birebir geçen en uzun parçası ölçülür: akıcı görünen metnin bir kısmı ezberdir.

**Güvenlik yönü — eğitim verisine gizlenmiş sırrın maruziyeti:** Eğitimden önce metne "gizli kod 48213" kanaryası 20 kez rastgele yerlere gizlenir (Carlini vd. 2019, Secret Sharer). Eğitimden sonra "gizli kod " önekinden sonra gelebilecek **bütün** 100 000 beş haneli kodun log-olasılığı basamak ağacıyla tam hesaplanır. Kanaryanın sırası maruziyeti verir: $\log_2(100\,000) - \log_2(\text{sıra})$. Gizlenen kod birinci sıradadır ve modelin en olası kodudur; hiç görülmemiş bir kontrol kodu rastgele bir sıradadır. Yaklaşık bir milyon parametrelik bir model bile eğitim verisindeki bir sırrı önek bilen herkese verir; eğitim verisinden sırlar temizlenmeli ya da diferansiyel gizlilikle eğitilmelidir.

Kabul: iki işlevin farksal taramayı geçmesi; parametre sayımının SmolLM2 ve mini modelde birebir tutması, Qwen'deki farkın bias sayısına eşit olması; perplexity sırasının mini model < bigram < tekdüze olması. Ayrıca kanaryanın maruziyeti en az 10 bit, görülmemiş kontrol kodununki en çok 6 bit olmalıdır.

**Kanıt dosyasını oku:** `smollm2`, `qwen2_5_0_5b`, `mini`, `ppl_tekduze`, `ppl_bigram`, `ppl_mini`, `uretilen`, `en_uzun_kopya_karakter`. Soru 1: SmolLM2'de gömme parametrelerin %21'i; mini modelde oran ne ve neden bu kadar farklı? Soru 2: Bigram ile mini model arasındaki farkı hangi mimari parça sağlıyor? Soru 3: Üretilen metin dilbilgisi olarak düzgünse model "Türkçe biliyor" mu?
:::

::: gorev Gerçek deney · Parametre sayımını SmolLM2/Qwen/mini modelle doğrulamak ve sıfırdan karakter düzeyinde mini Llama eğitmek
Önceki görevlerdeki `parametre_say`, `bigram_dil_modeli` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 300
```
```starter
import ai_lab
def parametre_say(V, d, L, ff, n_bas, n_kv_bas, bagli_gomme):
    return {'dikkat': 4 * d * d, 'mlp': 8 * d * d, 'katman_basi': 12 * d * d, 'gomme': 0, 'cikti': 0, 'toplam': 12 * d * d * L, 'gomme_orani': 0.0}

def bigram_dil_modeli(egitim_metni, test_metni, alfa):
    V = sorted(set(egitim_metni) | set(test_metni))
    return {'sozluk': len(V), 'perplexity': float(len(V)), 'en_sik_bigram': egitim_metni[:2]}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_37 as D
    D.goster(parametre_say, bigram_dil_modeli)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('mini_llama', 'karakter_verisi', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
parametre_say = need("parametre_say")
bigram_dil_modeli = need("bigram_dil_modeli")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile('def parametre_say(V, d, L, ff, n_bas, n_kv_bas, bagli_gomme):\n    for v in (V, d, L, ff, n_bas, n_kv_bas):\n        if isinstance(v, bool) or not isinstance(v, int) or v < 1:\n            raise ValueError(\'boyutlar pozitif tam sayı olmalı\')\n    if not isinstance(bagli_gomme, bool):\n        raise ValueError(\'bagli_gomme bool olmalı\')\n    if d % n_bas or n_bas % n_kv_bas:\n        raise ValueError("d, n_bas\'a; n_bas, n_kv_bas\'a bölünmeli")\n    h = d // n_bas\n    dikkat = 2 * d * d + 2 * d * n_kv_bas * h\n    mlp = 3 * d * ff\n    blok = dikkat + mlp + 2 * d\n    gomme = V * d\n    cikti = 0 if bagli_gomme else V * d\n    toplam = gomme + cikti + L * blok + d\n    return {\'dikkat\': dikkat, \'mlp\': mlp, \'katman_basi\': blok, \'gomme\': gomme, \'cikti\': cikti, \'toplam\': toplam, \'gomme_orani\': round((gomme + cikti) / toplam, 6)}\n\nimport math\n\ndef bigram_dil_modeli(egitim_metni, test_metni, alfa):\n    if not isinstance(egitim_metni, str) or not isinstance(test_metni, str) or len(egitim_metni) < 2 or (len(test_metni) < 2):\n        raise ValueError(\'metinler en az 2 karakterli str olmalı\')\n    if isinstance(alfa, bool) or not isinstance(alfa, (int, float)) or (not math.isfinite(alfa)) or (alfa <= 0):\n        raise ValueError(\'alfa pozitif olmalı\')\n    V = sorted(set(egitim_metni) | set(test_metni))\n    cift, tek = ({}, {})\n    for a, b in zip(egitim_metni, egitim_metni[1:]):\n        cift[a, b] = cift.get((a, b), 0) + 1\n        tek[a] = tek.get(a, 0) + 1\n    lp = 0.0\n    for a, b in zip(test_metni, test_metni[1:]):\n        lp += math.log((cift.get((a, b), 0) + alfa) / (tek.get(a, 0) + alfa * len(V)))\n    ppl = math.exp(-lp / (len(test_metni) - 1))\n    en = min(cift, key=lambda k: (-cift[k], k))\n    return {\'sozluk\': len(V), \'perplexity\': round(ppl, 6), \'en_sik_bigram\': en[0] + en[1]}', 'referans', 'exec'), _REF)
_t, _g = _ff(parametre_say, _REF['parametre_say'], (49152, 576, 30, 1536, 9, 3, True), tohum=2322, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (parametre_say): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(bigram_dil_modeli, _REF['bigram_dil_modeli'], ('abababab', 'abab', 0.5), tohum=2696, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (bigram_dil_modeli): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
if not all(checks): stop()
from sandbox import ai_gercek_ai_temel_37 as D
try: r = D.deney(parametre_say, bigram_dil_modeli)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['sayim_dogru'], "parametre sayımı SmolLM2 ve mini modelde birebir; Qwen'deki fark bias sayısına eşit")
kontrol(r['siralama_dogru'], "doğrulama perplexity'si: mini model < bigram < tekdüze")
kontrol(r['kanarya_ezberlendi'], 'eğitime gizlenen kanarya 100 000 aday içinde öne çıktı; görülmemiş kontrol kodu çıkmadı')
ai_lab.kanit_yaz("ai-temel-37-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-temel-37", "deney": r})
```
```solution
import ai_lab
import math

def parametre_say(V, d, L, ff, n_bas, n_kv_bas, bagli_gomme):
    for v in (V, d, L, ff, n_bas, n_kv_bas):
        if isinstance(v, bool) or not isinstance(v, int) or v < 1:
            raise ValueError('boyutlar pozitif tam sayı olmalı')
    if not isinstance(bagli_gomme, bool):
        raise ValueError('bagli_gomme bool olmalı')
    if d % n_bas or n_bas % n_kv_bas:
        raise ValueError("d, n_bas'a; n_bas, n_kv_bas'a bölünmeli")
    h = d // n_bas
    dikkat = 2 * d * d + 2 * d * n_kv_bas * h
    mlp = 3 * d * ff
    blok = dikkat + mlp + 2 * d
    gomme = V * d
    cikti = 0 if bagli_gomme else V * d
    toplam = gomme + cikti + L * blok + d
    return {'dikkat': dikkat, 'mlp': mlp, 'katman_basi': blok, 'gomme': gomme, 'cikti': cikti, 'toplam': toplam, 'gomme_orani': round((gomme + cikti) / toplam, 6)}

def bigram_dil_modeli(egitim_metni, test_metni, alfa):
    if not isinstance(egitim_metni, str) or not isinstance(test_metni, str) or len(egitim_metni) < 2 or (len(test_metni) < 2):
        raise ValueError('metinler en az 2 karakterli str olmalı')
    if isinstance(alfa, bool) or not isinstance(alfa, (int, float)) or (not math.isfinite(alfa)) or (alfa <= 0):
        raise ValueError('alfa pozitif olmalı')
    V = sorted(set(egitim_metni) | set(test_metni))
    cift, tek = ({}, {})
    for a, b in zip(egitim_metni, egitim_metni[1:]):
        cift[a, b] = cift.get((a, b), 0) + 1
        tek[a] = tek.get(a, 0) + 1
    lp = 0.0
    for a, b in zip(test_metni, test_metni[1:]):
        lp += math.log((cift.get((a, b), 0) + alfa) / (tek.get(a, 0) + alfa * len(V)))
    ppl = math.exp(-lp / (len(test_metni) - 1))
    en = min(cift, key=lambda k: (-cift[k], k))
    return {'sozluk': len(V), 'perplexity': round(ppl, 6), 'en_sik_bigram': en[0] + en[1]}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_37 as D
    D.goster(parametre_say, bigram_dil_modeli)
```
```hint
İki görevin çözümlerini olduğu gibi buraya koy.
```
:::

::: anlat Sınır
Ders mini-LLM'in parçalarını (tokenizer, embedding, causal attention, MLP, residual stream, eğitim döngüsü) anlatır ve katman başına parametre sayısını tahmin ettirir; görevler parametre sayımını ve bigram dil modelini yazdırır; final adım küçük bir Llama tarzı modeli sıfırdan gerçekten eğitir. 12d² formülü bias, normalizasyon ve embedding parametrelerini dışarıda bırakır; vocab büyükse embedding tablosu toplamın önemli bir kısmı olur. Küçük bir modelin akıcı metin üretmesi bilgi ya da muhakeme sahibi olduğunu göstermez; eğitim verisini ezberleyip tekrarlayabilir. Kendi bilgisayarında eğitimde GPU belleği, batch boyu ve bağlam uzunluğu birlikte sınırlar.

Kaynaklar: [Vaswani vd. 2017 - Attention Is All You Need](https://arxiv.org/abs/1706.03762), [Karpathy - nanoGPT](https://github.com/karpathy/nanoGPT).
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Altı parçalı uçtan uca `Mini-LLM` (30 sn).** "Dev modellerle sıfırdan kurulan küçük bir Llama modeli aynı iskeleti paylaşır: `Tokenizer` → `Embedding + RoPE` → `RMSNorm + GQA Causal Attention + SwiGLU MLP` blokları → `LM Head` → çapraz entropi eğitim döngüsü."
2. **Tam parametre muhasebesi ve `Perplexity` sırası (35 sn).** "`12d²` kuralı kaba bir yaklaşımdır; `GQA` KV baş sayısı, `SwiGLU` üçlü matrisi, norm ağırlıkları ve bağlı gömme (`weight tying`) sayıldığında gerçek model parametresi birebir tutar ve doğrulama `perplexity`'si `mini-LLM < bigram < tekdüze` sırasını izler."
3. **Kanarya maruziyeti (`Secret Sharer`) (30 sn).** "Yalnız ~750 bin parametreli küçük bir model bile eğitim verisinde tekrarlanan 5 haneli bir kanarya sırrını 100.000 aday içinde en olası kod yapacak kadar ezberler; eğitim öncesi sır temizliği şarttır."
4. **Soru (25 sn).** "SmolLM2-135M tam sayımla birebir tutarken Qwen2.5-0.5B'de formülün tam `q/k/v bias` sayısı kadar eksik çıkması mimari denetimde bize neyi kanıtlar?"
:::
