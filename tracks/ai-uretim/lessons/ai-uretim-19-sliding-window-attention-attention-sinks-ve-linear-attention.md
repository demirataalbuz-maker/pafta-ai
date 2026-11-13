---
id: ai-uretim-19
title: "Sliding Window Attention (SWA), Attention Sinks (StreamingLLM) ve Linear Attention"
track: ai-uretim
order: 19
duration_minutes: 35
difficulty: ileri
xp: 290
prerequisites: [ai-uretim-18]
summary: "Sonsuz uzunlukta akış (Infinite Streaming) nasıl yapılır? Sliding Window Attention (SWA — Mistral/Gemma-2), ilk 4 token silindiğinde modelin neden çöktüğünü açıklayan Attention Sinks (StreamingLLM) keşfi ve O(N) Linear Attention."
esleme: ai-uretim-18, ai-uretim-20, ai-temel-07
tags: [sliding-window-attention, attention-sinks, streamingllm, linear-attention, kernel-feature-map]
---

::: anlat 1. Sonsuz Uzunlukta Akış (Infinite Streaming) Problemi ve Sliding Window Attention (SWA)
## Sınırlı cache ve linear attention

Uzun akışlarda saklanan KV miktarını sınırlamak ile attention işleminin biçimini değiştirmek farklı yaklaşımlardır. StreamingLLM için attention sink ve kayan pencereyi, linear attention için birikimli durum hesabını karşılaştıracaksın. İşlem sayısı oranı, ölçülmüş latency hızlanması olarak yorumlanmamalı.

Bir konferansta ya da teknik sunumda sahneye çıktığında izleyicilere şu soruyu sor:
> *"Arkadaşlar, 7/24 hiç kapanmadan çalışan bir sesli yapay zeka asistanı veya otonom bir kodlama ajanı düşünün. Sohbet 10 bin, 100 bin, 4 milyon `token` boyunca devam ediyor! Standart bir `Transformer` modelinde her yeni `token` geldiğinde `KV-Cache` belleği doğrusal olarak büyür, dikkat (`Self-Attention`) hesabı ise $O(T^2)$ karesel olarak patlar! Peki GPU belleğini (`VRAM`) hiç taşırmadan ve hızı hiç düşürmeden **sonsuz uzunlukta akışı (`Infinite Streaming`)** nasıl sağlarız?"*

### 🪟 İlk Çözüm: `Sliding Window Attention (SWA)` (`Mistral-7B` & `Gemma-2`)
Standart `Causal Self-Attention` katmanında $t$. konumdaki bir `token`, $0$'dan $t$'ye kadar olan tüm geçmişe bakar. **`Sliding Window Attention (SWA)`** ise her `token`'ın yalnızca son $W$ adet (`Window Size`, örn. $W = 4096$) komşusuna bakmasına izin verir ($t - W < j \le t$):

```text
  STANDART CAUSAL ATTENTION (O(T^2))          SLIDING WINDOW ATTENTION (O(T · W))
       j=0  1   2   3   4   5                      j=0  1   2   3   4   5   (W = 3)
    ┌─────────────────────────┐                 ┌─────────────────────────┐
  0 │   1   0   0   0   0   0 │               0 │   1   0   0   0   0   0 │
  1 │   1   1   0   0   0   0 │               1 │   1   1   0   0   0   0 │
  2 │   1   1   1   0   0   0 │               2 │   1   1   1   0   0   0 │
  3 │   1   1   1   1   0   0 │               3 │   0   1   1   1   0   0 │  <-- j=0 pencere dışı!
  4 │   1   1   1   1   1   0 │               4 │   0   0   1   1   1   0 │  <-- j=0,1 silindi!
  5 │   1   1   1   1   1   1 │               5 │   0   0   0   1   1   1 │  <-- Sabit W=3 KV-Cache!
    └─────────────────────────┘                 └─────────────────────────┘
```

### 🧱 Bilgi Pencerenin Dışından Nasıl Akar? (`Stacked Receptive Field`)
İlk bakışta *"Hocam, $W=4096$ ise model 5000. kelimedeyken 100. kelimeyi tamamen unutur mu?"* diye düşünebilirsin. **Hayır!**
- Tıpkı Evrişimli Sinir Ağlarındaki (`CNN`) üst üste binen filtreler gibi:
  - **Katman 1** son $W$ `token`'ın bilgisini özetler.
  - **Katman 2**, Katman 1'in özetlediği son $W$ temsil üzerinden tekrar $W$ geriye baktığı için dolaylı olarak **$2W$** uzaklıktaki bilgiye erişir!
  - $L$ katmanlı bir modelin etkin görüş alanı (**`Effective Receptive Field`**) $L \times W$ olur (örn. $L=32, W=4096 \implies 131.072\text{ token}$)!
- `Gemma-2` ve `GPT-OSS` gibi modern mimariler ise **hibrit (`Interleaved SWA + Global Attention`)** bir yapı kullanır: Örneğin 5 katman çok hızlı yerel `SWA` ($W=4096$) yaparken, her 6. katman tam `Global Attention` yaparak uzak geçmişle doğrudan köprü kurar!

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [StreamingLLM makalesi](https://arxiv.org/abs/2309.17453). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: anlat 2. Milyon Dolarlık Gizem: İlk 4 Token Silindiğinde Model Neden Anında Çöküyor? (Attention Sinks & StreamingLLM)
Şimdi MIT ve Meta araştırmacılarının (Xiao et al., ICLR 2024 — **`StreamingLLM`**) keşfettiği, derin öğrenme dünyasını sarsan o ünlü olaya geliyoruz!

Araştırmacılar, $W=4096$ penceresiyle çalışan bir modeli sonsuz akışta çalıştırmak istediler. $4096$. `token` geçildiğinde, bellek dolmasın diye en eski `token` olan **0. ve 1. `token`'ı `KV-Cache`'ten sildiler (`Eviction`)**.
- **Beklenen:** Modelin sadece ilk birkaç kelimeyi unutması ama düzgün konuşmaya devam etmesi.
- **Gerçekleşen Felaket:** İlk `token`lar `KV-Cache`'ten silindiği salisede modelin `Perplexity` (şaşkınlık) skoru $5.0$'dan **$10.000+$ seviyesine fırladı** ve model tamamen anlamsız harfler (`"aaaa###..."`) kusarak çöktü!

### 🤯 Neden Cümlenin En Başındaki Anlamsız Bir Kelime Silinince Tüm Beyin Çöker?
Cevap **`Softmax` fonksiyonunun doğasında** gizlidir:

$$\text{Softmax}(z)_j = \frac{e^{z_j}}{\sum_{m} e^{z_m}}, \qquad \sum_{j} \text{Softmax}(z)_j = \mathbf{1.0}$$

1. `Self-Attention` içindeki her bir `Attention Head`, her adımda elindeki `%100` (`1.0`) dikkat enerjisini geçmişteki `token`lara **dağıtmak ZORUNDADIR** (`Softmax` toplamı asla $0.0$ olamaz!).
2. Ancak birçok adımda o anki `Attention Head`, geçmişte dikkat etmeye değer hiçbir anlamlı kelime bulamaz ("şu an kimseye bakmak istemiyorum / `No-Op`" durumu).
3. Peki `Softmax` toplamı $1.0$ olmak zorundaysa, model bu **fazladan, istenmeyen dikkat enerjisini nereye boşaltır (`Dump`)?**
4. Nedensel maske (`Causal Mask` $j \le i$) nedeniyle dizideki **bütün `token`ların %100'ü tarafından ortaklaşa görülebilen tek yer en baştaki ilk birkaç `token`'dır ($j = 0, 1, 2, 3$)!**
5. Bu yüzden model, ön-eğitim (`Pre-Training`) sırasında en baştaki ilk 1 ila 4 `token`'ı bir **"Dikkat Çöp Kutusu / Lavabo Deliği (`Attention Sink`)"** olarak kullanmayı öğrenir! Sen o ilk 4 `token`'ı (`Attention Sinks`) sildiğin anda, `Softmax` paydasındaki devasa $e^{z_{\text{sink}}}$ terimi yok olur ve dikkat dağılımı tamamen patlar!

### 🚀 Çözüm: `StreamingLLM` (`Attention Sinks` + `Rolling KV-Cache`)
Çözüm inanılmaz derecede zariftir:
- `KV-Cache` belleğini iki parçaya ayırırız:
  1. **`Attention Sinks` ($S$ adet, örn. ilk $S = 4$ `token`):** Dizinin en başındaki ilk $4$ `token` **ASLA SİLİNMEZ**, her zaman önbelleğin başında sabit tutulur!
  2. **`Rolling Sliding Window` ($W$ adet, örn. son $W = 1020$ `token`):** Sadece en son gelen $W$ adet `token` dairesel olarak güncellenir; aradaki eski `token`lar silinir!
- **Konumsal Kodlama (`RoPE`) Püf Noktası:** Önbellekteki `token`ların orijinal mutlak indeksleri (`[0, 1, 2, 3, 9500, 9501, ...]`) yerine, önbellek içindeki ardışık konumları (`[0, 1, 2, 3, 4, 5, ...]`) üzerinden `RoPE` döndürmesi uygulanır! Bu sayede model $4\text{ Milyon token}$ boyunca tek bir `OutOfMemory` almadan ve hiç çökmeden akıcı şekilde konuşur!

```text
  STREAMING-LLM KV-CACHE BELLEK DÜZENİ (Sabit Kapasite = S + W):
  ┌─────────────────────────┬───────────────────────────┬──────────────────────────────────┐
  │ [0] [1] [2] [3]         │  ... (Silinen Geçmiş) ... │ [T-W] [T-W+1] ...     [T-1] [T]  │
  │  ATTENTION SINKS (S=4)  │   (Bellekte Tutulmaz!)    │   ROLLING SLIDING WINDOW (Son W) │
  │  (Asla Silinmez!)       │                           │   (Yeni geldikçe kayar)          │
  └─────────────────────────┴───────────────────────────┴──────────────────────────────────┘
     RoPE Konumları: 0..3                                  RoPE Konumları: 4 .. (S+W-1)
```
:::

::: anlat 3. Matris Çarpım Sırasını Değiştirerek $O(N^2)$'den $O(N)$'e İnmek: Linear Attention
`Sliding Window` ve `StreamingLLM` pencere dışındaki orta geçmişi siler. Peki **hiçbir `token`'ı silmeden**, tüm geçmişi sabit boyutlu bir durum matrisinde ($S_t \in \mathbb{R}^{d \times d}$) tutarak **$O(N)$ doğrusal zamanda** dikkat hesaplayabilir miyiz?

Standart `Attention` neden $O(N^2)$ zaman alır? Çünkü $\text{Softmax}(Q K^\top)$ fonksiyonu $Q$ ve $K^\top$ matrislerini birbirine kilitler:
$$\text{Standart: } \underbrace{(Q K^\top)}_{N \times N \text{ Matris!}} V \quad \longrightarrow \quad \text{Maliyet: } O(N^2 d)$$

Katharopoulos et al. (2020 — *"Transformers are RNNs: Fast Autoregressive Transformers with Linear Attention"*) şu soruyu sordu:
> *"Ya `Softmax` üstel fonksiyonu yerine, $Q$ ve $K$ vektörlerine ayrı ayrı uygulanabilen pozitif bir çekirdek özellik haritası (**`Kernel Feature Map` $\phi(\cdot) \ge 0$**, örn. $\phi(x) = \text{elu}(x) + 1$) uygularsak?"*

Matris çarpımının birleşme özelliğini (`Associative Property`: $(AB)C = A(BC)$) kullandığımız anda mucize gerçekleşir:

$$\text{Linear Attention: } \phi(Q) \big(\phi(K)^\top V\big) = \phi(Q) \cdot \underbrace{\big(\phi(K)^\top V\big)}_{d \times d \text{ Matris!}} \quad \longrightarrow \quad \text{Maliyet: } \mathbf{O(N d^2)}$$

### 🔄 Nedensel (`Causal / Autoregressive`) Formda `Linear Attention` = `RNN`!
Nedensel üretimde her $t$ adımında:
1. $d \times d$ boyutlu **Durum Matrisi (`KV State` $S_t$)** ve $d$ boyutlu **Normalleştirici Vektör ($Z_t$)** yalnızca yeni gelen $\phi(k_t)$ ve $v_t$ ile $O(d^2)$ sürede güncellenir:
   $$S_t = S_{t-1} + \phi(k_t) v_t^\top, \qquad Z_t = Z_{t-1} + \phi(k_t)$$
2. Çıktı vektörü $y_t$, bu sabit boyutlu özet durumla $\phi(q_t)$ vektörünün çarpımıdır:
   $$y_t = \frac{\phi(q_t)^\top S_t}{\phi(q_t)^\top Z_t + \epsilon}$$

Bu denklem modern **`Lightning Attention` (`MiniMax-01`)**, **`GLA` (`Gated Linear Attention`)**, **`DeltaNet` (`Qwen3-Next`)** ve **`Mamba-2`** mimarilerinin temel yapıtaşıdır!

```python norun
import torch
import torch.nn.functional as F

def causal_linear_attention_pytorch(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, eps: float = 1e-6):
    # Q, K, V: [Batch, SeqLen, d_head]
    # Pozitif çekirdek dönüşümü: phi(x) = ELU(x) + 1
    phi_Q = F.elu(Q) + 1.0
    phi_K = F.elu(K) + 1.0

    # Dış çarpımların (k_t @ v_t^T) kümülatif toplamı -> O(N * d^2) bellek ve hız!
    kv_outer = torch.einsum("btd,bte->btde", phi_K, V)
    S_cum = torch.cumsum(kv_outer, dim=1)          # [B, T, d, d]
    Z_cum = torch.cumsum(phi_K, dim=1)             # [B, T, d]

    pay   = torch.einsum("btd,btde->bte", phi_Q, S_cum)
    payda = torch.einsum("btd,btd->bt", phi_Q, Z_cum).unsqueeze(-1) + eps
    return pay / payda
```
:::

::: tahmin Standart Attention vs Linear Attention İşlem (FLOPs) Karşılaştırması
Uzunluğu $N = 100.000$ `token` olan bir belgede kafa boyutu $d = 64$ olan tek bir `Attention Head` çalıştırıyoruz.
- Standart `Attention` $(QK^\top)V$ adımında yaklaşık $N^2 \cdot d$ mertebesinde işlem yapar.
- `Linear Attention` $\phi(Q)(\phi(K)^\top V)$ adımında ise $N \cdot d^2$ mertebesinde işlem yapar.
Bu belgede `Linear Attention`, standart `Attention`'a göre kaç kat daha az işlem yapar?

```python
N = 100_000
d = 64

standart_islem = (N ** 2) * d
linear_islem = N * (d ** 2)
hizlanma_katsayisi = round(standart_islem / linear_islem, 2)
print(f"Standart: {standart_islem:,} | Linear: {linear_islem:,} | Hizlanma: {hizlanma_katsayisi}x")
```

???

```cikti
Standart: 640,000,000,000 | Linear: 409,600,000 | Hizlanma: 1562.5x
```
$N = 100.000$ ve $d = 64$ için standart dikkat $\approx 6.4 \times 10^{11}$ işlem yaparken, `Linear Attention` yalnızca $\approx 4.096 \times 10^8$ işlem yapar. Oran $\frac{N^2 d}{N d^2} = \frac{N}{d} = \frac{100.000}{64} = 1562.5\text{ kat}$ hızlanmadır!

Kodda Hizlanma diye yazılan değer, seçilen formüllerin işlem sayısı oranıdır; ölçülmüş latency veya throughput katsayısı değildir.
:::

::: gorev 1 · StreamingLLM (Attention Sinks + Rolling KV-Cache Penceresi)
Sonsuz bir `token` akışında `StreamingLLM` önbellek yönetimini simüle eden `streaming_kv_guncelle(tum_tokenlar, sink_sayisi, pencere_boyutu)` işlevini yaz:

1. **Girdiler:**
   - `tum_tokenlar`: Şimdiye kadar akıştan gelen tüm `token ID` tam sayılarının listesi.
   - `sink_sayisi`: Önbelleğin en başında her zaman sabit tutulacak `Attention Sink` sayısı $S$ (`int >= 0`).
   - `pencere_boyutu`: En sonda tutulacak kayan pencere (`Rolling Window`) boyutu $W$ (`int > 0`).
2. **Kurallar:**
   - Toplam önbellek kapasitesi `kapasite = sink_sayisi + pencere_boyutu` değeridir.
   - Eğer `len(tum_tokenlar) <= kapasite` ise:
     - Hiçbir `token` silinmez (`silinen_token_sayisi = 0`).
     - `aktif_kv_tokenlari = list(tum_tokenlar)` olur.
   - Eğer `len(tum_tokenlar) > kapasite` ise:
     - İlk `sink_sayisi` adet `token` (`tum_tokenlar[:sink_sayisi]`) ve en son `pencere_boyutu` adet `token` (`tum_tokenlar[-pencere_boyutu:]`) birleştirilerek `aktif_kv_tokenlari` oluşturulur.
     - Arada kalan `len(tum_tokenlar) - kapasite` adet `token` silinmiştir (`silinen_token_sayisi`).
   - **`rope_konumlari`:** `StreamingLLM` kuralı gereği, önbellekte tutulan `aktif_kv_tokenlari` listesindeki elemanlara orijinal indeksleri değil, **`0`'dan başlayıp `len(aktif_kv_tokenlari) - 1`'e kadar giden ardışık (`contiguous`) tam sayı konumları** (`[0, 1, 2, ...]`) atanır!
3. **Dönüş Değeri:**
   `{"aktif_kv_tokenlari": [int, ...], "rope_konumlari": [int, ...], "silinen_token_sayisi": int, "kapasite": int}` sözlüğü döndür. Girdi listesini değiştirme.

```starter
def streaming_kv_guncelle(tum_tokenlar, sink_sayisi, pencere_boyutu):
    # KUSURLU BAŞLANGIÇ KODU: Attention Sink tokenlarını korumadan sadece son pencereyi alıyor!
    kapasite = sink_sayisi + pencere_boyutu
    aktif = list(tum_tokenlar[-pencere_boyutu:])
    return {
        "aktif_kv_tokenlari": aktif,
        "rope_konumlari": list(range(len(aktif))),
        "silinen_token_sayisi": 0,
        "kapasite": kapasite,
    }

print(streaming_kv_guncelle([10, 20, 30, 40, 50, 60, 70, 80], sink_sayisi=2, pencere_boyutu=3))
```

```test
import copy

def _ref_stream(toks, s, w):
    kap = s + w
    if len(toks) <= kap:
        aktif = list(toks)
        silinen = 0
    else:
        aktif = (list(toks[:s]) if s > 0 else []) + list(toks[-w:])
        silinen = len(toks) - kap
    return {
        "aktif_kv_tokenlari": aktif,
        "rope_konumlari": list(range(len(aktif))),
        "silinen_token_sayisi": silinen,
        "kapasite": kap,
    }

def sozlesme(fn):
    try:
        vakalar = [
            ([10, 20, 30, 40, 50, 60, 70, 80], 2, 3),
            ([1, 2, 3, 4], 2, 4),
            ([100, 101, 102, 103, 104, 105, 106, 107, 108, 109], 4, 4),
            ([5, 6, 7, 8, 9], 0, 3),
        ]
        for toks, s, w in vakalar:
            t_kopya = copy.deepcopy(toks)
            sonuc = fn(toks, s, w)
            bek = _ref_stream(toks, s, w)
            if sonuc != bek or toks != t_kopya:
                return False
        return True
    except Exception:
        return False

ok(sozlesme(streaming_kv_guncelle), "streaming_kv_guncelle ilk S adet Attention Sink ile son W adet pencereyi birleştirmeli ve ardışık RoPE konumları atamalı")

def m_sinksiz(toks, s, w):
    r = copy.deepcopy(_ref_stream(toks, s, w))
    r["aktif_kv_tokenlari"] = list(toks[-(s + w):])
    return r

def m_eski_rope(toks, s, w):
    r = copy.deepcopy(_ref_stream(toks, s, w))
    if len(toks) > s + w:
        r["rope_konumlari"] = list(range(s)) + list(range(len(toks) - w, len(toks)))
    return r

for ad, m in [("Attention Sink tokenlarını silip sadece son tokenları tutan", m_sinksiz), ("Ardışık RoPE yerine orijinal kopuk konumları kullanan", m_eski_rope)]:
    ok(not sozlesme(m), f"Yanlış çözüm/mutant yakalanmalı: {ad}")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def streaming_kv_guncelle(tum_tokenlar, sink_sayisi, pencere_boyutu):\n    kapasite = sink_sayisi + pencere_boyutu\n    if len(tum_tokenlar) <= kapasite:\n        aktif = list(tum_tokenlar)\n        silinen = 0\n    else:\n        sink_kismi = list(tum_tokenlar[:sink_sayisi]) if sink_sayisi > 0 else []\n        pencere_kismi = list(tum_tokenlar[-pencere_boyutu:])\n        aktif = sink_kismi + pencere_kismi\n        silinen = len(tum_tokenlar) - kapasite\n    return {'aktif_kv_tokenlari': aktif, 'rope_konumlari': list(range(len(aktif))), 'silinen_token_sayisi': silinen, 'kapasite': kapasite}", 'referans', 'exec'), _REF)
_t, _g = _ff(streaming_kv_guncelle, _REF['streaming_kv_guncelle'], ([10, 20, 30, 40, 50, 60, 70, 80], 2, 3), tohum=3292, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (streaming_kv_guncelle): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def streaming_kv_guncelle(tum_tokenlar, sink_sayisi, pencere_boyutu):
    kapasite = sink_sayisi + pencere_boyutu
    if len(tum_tokenlar) <= kapasite:
        aktif = list(tum_tokenlar)
        silinen = 0
    else:
        sink_kismi = list(tum_tokenlar[:sink_sayisi]) if sink_sayisi > 0 else []
        pencere_kismi = list(tum_tokenlar[-pencere_boyutu:])
        aktif = sink_kismi + pencere_kismi
        silinen = len(tum_tokenlar) - kapasite

    return {
        "aktif_kv_tokenlari": aktif,
        "rope_konumlari": list(range(len(aktif))),
        "silinen_token_sayisi": silinen,
        "kapasite": kapasite,
    }
```

```hint
`kapasite = sink_sayisi + pencere_boyutu` değerini bul. Dizi uzunluğu kapasiteden büyükse `tum_tokenlar[:sink_sayisi] + tum_tokenlar[-pencere_boyutu:]` ile önbelleği oluştur (`sink_sayisi == 0` durumuna dikkat et). `rope_konumlari` her zaman `list(range(len(aktif)))` olmalıdır.
```
:::

::: gorev 2 · O(N) Linear Attention (ELU+1 Kernel Feature Map ile Tek Geçişli Durum Özeti)
$N \times N$ dikkat matrisi oluşturmadan, $\phi(x) = \text{elu}(x) + 1$ çekirdek özellik haritası ve tekrarlamalı durum özeti ($S_t, Z_t$) kullanarak $O(N d^2)$ sürede nedensel doğrusal dikkat hesaplayan `linear_attention_ileri(Q, K, V, eps)` işlevini yaz:

1. **Girdiler:**
   - `Q`, `K`, `V`: Boyutu $T \times d$ olan matrisler (`T` adet `token`, her biri `d` boyutlu `float` listesi).
   - `eps`: Sıfıra bölmeyi önleyen küçük sabit ($\epsilon > 0$, örn. `1e-6`).
2. **Matematiksel Kurallar:**
   - **Özellik Haritası ($\phi$):** Skaler bir $x$ sayısı için $\text{elu}(x) + 1$ fonksiyonu:
     $$\phi(x) = \begin{cases} x + 1.0, & \text{eğer } x \ge 0 \\ e^x, & \text{eğer } x < 0 \end{cases}$$
     Bu fonksiyonu `Q` ve `K` matrislerinin tüm elemanlarına uygula ($\tilde{q}_t = \phi(Q_t)$, $\tilde{k}_t = \phi(K_t)$).
   - **Tek Geçişli Nedensel Durum Güncellemesi ($t = 0, 1, \dots, T-1$):**
     - Başlangıçta $d \times d$ boyutlu durum matrisi $S$ tamamen `0.0` ve $d$ boyutlu normalleştirici vektör $Z$ tamamen `0.0`'dır.
     - Her $t$ adımında önce durumu güncelle:
       $$S_{i, j} \leftarrow S_{i, j} + \tilde{k}_{t, i} \cdot V_{t, j} \quad (\forall i, j \in \{0, \dots, d-1\})$$
       $$Z_i \leftarrow Z_i + \tilde{k}_{t, i} \quad (\forall i \in \{0, \dots, d-1\})$$
     - Ardından $t$. adımın çıktı vektörü $y_t$'yi hesapla:
       $$\text{pay}_j = \sum_{i=0}^{d-1} \tilde{q}_{t, i} \cdot S_{i, j}, \qquad \text{payda} = \left(\sum_{i=0}^{d-1} \tilde{q}_{t, i} \cdot Z_i\right) + \text{eps}$$
       $$y_{t, j} = \frac{\text{pay}_j}{\text{payda}}$$
   - Tüm çıktı ve son durum elemanlarını `round(val, 6)` ile yuvarla.
3. **Dönüş Değeri:**
   `{"cikti": [[float, ...], ...], "son_durum_S": [[float, ...], ...], "son_norm_Z": [float, ...]}` sözlüğü döndür.

```starter
def linear_attention_ileri(Q, K, V, eps=1e-6):
    # KUSURLU BAŞLANGIÇ KODU: ELU+1 dönüşümü ve S_t durum birikimini yapmadan V matrisini döndürüyor!
    T, d = len(Q), len(Q[0])
    return {
        "cikti": [[round(float(x), 6) for x in satir] for satir in V],
        "son_durum_S": [[0.0] * d for _ in range(d)],
        "son_norm_Z": [0.0] * d,
    }

ornek_Q = [[0.5, -0.5], [1.0, 0.0]]
ornek_K = [[0.2, 0.8], [-0.4, 0.6]]
ornek_V = [[1.0, 2.0], [3.0, 4.0]]
print(linear_attention_ileri(ornek_Q, ornek_K, ornek_V))
```

```test
import copy, math

def _phi(x):
    return (x + 1.0) if x >= 0 else math.exp(x)

def _ref_lin(Q, K, V, eps=1e-6):
    T, d = len(Q), len(Q[0])
    S = [[0.0] * d for _ in range(d)]
    Z = [0.0] * d
    cikti = []
    for t in range(T):
        qt = [_phi(x) for x in Q[t]]
        kt = [_phi(x) for x in K[t]]
        vt = V[t]
        for i in range(d):
            Z[i] += kt[i]
            for j in range(d):
                S[i][j] += kt[i] * vt[j]
        payda = sum(qt[i] * Z[i] for i in range(d)) + eps
        yt = [round(sum(qt[i] * S[i][j] for i in range(d)) / payda, 6) for j in range(d)]
        cikti.append(yt)
    return {
        "cikti": cikti,
        "son_durum_S": [[round(S[i][j], 6) for j in range(d)] for i in range(d)],
        "son_norm_Z": [round(Z[i], 6) for i in range(d)],
    }

def sozlesme(fn):
    try:
        vakalar = [
            ([[0.5, -0.5], [1.0, 0.0]], [[0.2, 0.8], [-0.4, 0.6]], [[1.0, 2.0], [3.0, 4.0]], 1e-6),
            ([[0.0, 1.0], [-1.0, 0.5], [0.2, -0.3]], [[0.5, -0.2], [0.1, 0.4], [-0.5, 0.8]], [[2.0, -1.0], [0.5, 3.0], [1.5, 0.0]], 1e-5),
        ]
        for q, k, v, eps in vakalar:
            q_c = copy.deepcopy(q)
            sonuc = fn(q, k, v, eps)
            bek = _ref_lin(q, k, v, eps)
            if not isinstance(sonuc, dict) or set(sonuc.keys()) != {"cikti", "son_durum_S", "son_norm_Z"}:
                return False
            if sonuc != bek or q != q_c:
                return False
        return True
    except Exception:
        return False

ok(sozlesme(linear_attention_ileri), "linear_attention_ileri ELU+1 çekirdeği ve (S_t, Z_t) durum güncellemesiyle O(N) nedensel çıktıyı doğru hesaplamalı")

def m_phisiz(Q, K, V, eps=1e-6):
    r = copy.deepcopy(_ref_lin(Q, K, V, eps))
    r["son_norm_Z"] = [0.0] * len(Q[0])
    return r

def m_normsüz(Q, K, V, eps=1e-6):
    r = copy.deepcopy(_ref_lin(Q, K, V, eps))
    r["cikti"] = [[round(x * 2.0, 6) for x in s] for s in r["cikti"]]
    return r

for ad, m in [("Normalleştirici Z vektörünü güncellemeyen", m_phisiz), ("Payda normalleştirmesini yanlış yapan", m_normsüz)]:
    ok(not sozlesme(m), f"Yanlış çözüm/mutant yakalanmalı: {ad}")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef linear_attention_ileri(Q, K, V, eps=1e-06):\n    T = len(Q)\n    d = len(Q[0])\n    S = [[0.0] * d for _ in range(d)]\n    Z = [0.0] * d\n    cikti = []\n\n    def phi(x):\n        return x + 1.0 if x >= 0 else math.exp(x)\n    for t in range(T):\n        qt = [phi(x) for x in Q[t]]\n        kt = [phi(x) for x in K[t]]\n        vt = V[t]\n        for i in range(d):\n            Z[i] += kt[i]\n            for j in range(d):\n                S[i][j] += kt[i] * vt[j]\n        payda = sum((qt[i] * Z[i] for i in range(d))) + eps\n        yt = [round(sum((qt[i] * S[i][j] for i in range(d))) / payda, 6) for j in range(d)]\n        cikti.append(yt)\n    return {'cikti': cikti, 'son_durum_S': [[round(S[i][j], 6) for j in range(d)] for i in range(d)], 'son_norm_Z': [round(Z[i], 6) for i in range(d)]}", 'referans', 'exec'), _REF)
_t, _g = _ff(linear_attention_ileri, _REF['linear_attention_ileri'], ([[0.5, -0.5], [1.0, 0.0]], [[0.2, 0.8], [-0.4, 0.6]], [[1.0, 2.0], [3.0, 4.0]], 1e-06), tohum=3400, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (linear_attention_ileri): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
ok(linear_attention_ileri([[-7.0, -7.0]], [[-7.0, -7.0]], [[1000.0, 500.0]]) == _REF['linear_attention_ileri']([[-7.0, -7.0]], [[-7.0, -7.0]], [[1000.0, 500.0]]), "varsayılan eps=1e-6 payda kararlılığı korunmalı")
```

```solution
import math

def linear_attention_ileri(Q, K, V, eps=1e-6):
    T = len(Q)
    d = len(Q[0])
    S = [[0.0] * d for _ in range(d)]
    Z = [0.0] * d
    cikti = []

    def phi(x):
        return (x + 1.0) if x >= 0 else math.exp(x)

    for t in range(T):
        qt = [phi(x) for x in Q[t]]
        kt = [phi(x) for x in K[t]]
        vt = V[t]
        for i in range(d):
            Z[i] += kt[i]
            for j in range(d):
                S[i][j] += kt[i] * vt[j]

        payda = sum(qt[i] * Z[i] for i in range(d)) + eps
        yt = [
            round(sum(qt[i] * S[i][j] for i in range(d)) / payda, 6)
            for j in range(d)
        ]
        cikti.append(yt)

    return {
        "cikti": cikti,
        "son_durum_S": [[round(S[i][j], 6) for j in range(d)] for i in range(d)],
        "son_norm_Z": [round(Z[i], 6) for i in range(d)],
    }
```

```hint
Her `t` adımında önce `qt` ve `kt` vektörlerini `x + 1.0 if x >= 0 else math.exp(x)` ile dönüştür. Ardından `Z[i] += kt[i]` ve `S[i][j] += kt[i] * vt[j]` güncellemelerini yapıp `sum(qt[i] * S[i][j]) / (sum(qt[i] * Z[i]) + eps)` ile çıktıyı hesapla.
```
:::

::: anlat Gerçek deney: SmolLM2'de attention sink: önbellekli pencerenin çöküşü ve sink'lerin kurtarması
Final StreamingLLM makalesinin temel deneyini gerçek bir modelde yeniden üretir (indirme yok):

- Pafta ders metinlerinden ~2 000 tokenlık gerçek bir dizide, 1 024–1 976 arasındaki 120 konumda sonraki token tahmin edilir. Önbellek 128 tokendır.
- **Önbellekli pencere:** her tokenın KV'si üretildiği anda, o andaki önbellekle hesaplanır; eski tokenlar atılır. Bu, tüm diziyi tek geçişte, her satırın yalnız son 128 tokenı gördüğü bir 4B dikkat maskesiyle çalıştırmaya denktir.
- **StreamingLLM:** aynı kurulum, ama önbellekte hangi tokenların kalacağına senin `streaming_kv_guncelle` işlevin karar verir: ilk 4 token (sink) + son 124 token.
- **Yeniden hesaplamalı pencere:** her konumda son 128 token baştan, önbellek içi konumlarla (`rope_konumlari`) modelden geçirilir. Pahalı ama iyi bir üst sınırdır: pencerenin ilk tokenı sink rolünü üstlenir.
- Ayrıca son tokenın dikkatinin ne kadarının ilk 4 tokena gittiği ölçülür (eager dikkat ile).
- **Doğrusal dikkat:** 2. katmanın gerçek Q/K/V değerleri (head 0) senin `linear_attention_ileri` işlevine verilir; sonuç torch'taki kümülatif toplam referansıyla karşılaştırılır ve aynı Q/K/V ile softmax dikkatinden ne kadar uzak olduğu ölçülür.

**Güvenlik yönü — sistem istemi pencereden düşünce:** SmolLM2-Instruct'a kod adı içeren bir sistem istemi, ardından 14 tur alakasız sohbet ve "proje kod adı ne?" sorusu verilir (~730 token). Doğru cevabın log-olasılığı üç kipte ölçülür: tam bağlam, 192 tokenlık önbellek + 4 sink (sistem istemi atılır) ve senin `streaming_kv_guncelle` işlevinle **sistem istemi sabitlenmiş** önbellek (sink sayısı = sistem istemi token sayısı). Sistem istemi düşünce model kod adını bilemez; aynı mekanizma güvenlik talimatlarını da sessizce siler. Sabitleme cevabı tam bağlam düzeyine geri getirir. Sink sayısı yalnız perplexity için değil, korunması gereken talimatlar için de seçilmelidir.

Kabul: iki işlevin farksal taramayı geçmesi; senin işlevinin her konumda doğru tokenları ve konumları seçmesi; önbellekli kipte sink'lerin perplexity'yi düşürmesi; doğrusal dikkatin torch referansıyla aynı olması. Ayrıca sistem istemi atılınca cevabın log-olasılığı en az 3 nat düşmeli, sabitlenince en az 3 nat geri gelmelidir.

**Kanıt dosyasını oku:** `ppl` (beş kip), `sink_dikkat_payi`, `linear_softmax_goreli_fark`. Soru 1: Önbellekli pencerede ilk tokenlar atılınca perplexity neden yüzlerce kat bozuluyor? Soru 2: Yeniden hesaplamalı pencere neden sink olmadan da iyi? Soru 3: Sistem istemi pencereden düşerse ne olur ve sink sayısını bu açıdan nasıl seçersin?
:::

::: gorev Gerçek deney · SmolLM2'de önbellekli pencere, attention sink'ler ve doğrusal dikkat
Önceki görevlerdeki `streaming_kv_guncelle`, `linear_attention_ileri` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 240
```
```starter
import ai_lab
def streaming_kv_guncelle(tum_tokenlar, sink_sayisi, pencere_boyutu):
    kapasite = sink_sayisi + pencere_boyutu
    aktif = list(tum_tokenlar[-pencere_boyutu:])
    return {'aktif_kv_tokenlari': aktif, 'rope_konumlari': list(range(len(aktif))), 'silinen_token_sayisi': 0, 'kapasite': kapasite}

def linear_attention_ileri(Q, K, V, eps=1e-06):
    T, d = (len(Q), len(Q[0]))
    return {'cikti': [[round(float(x), 6) for x in satir] for satir in V], 'son_durum_S': [[0.0] * d for _ in range(d)], 'son_norm_Z': [0.0] * d}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_19 as D
    D.goster(streaming_kv_guncelle, linear_attention_ileri)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_nll', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
streaming_kv_guncelle = need("streaming_kv_guncelle")
linear_attention_ileri = need("linear_attention_ileri")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def streaming_kv_guncelle(tum_tokenlar, sink_sayisi, pencere_boyutu):\n    kapasite = sink_sayisi + pencere_boyutu\n    if len(tum_tokenlar) <= kapasite:\n        aktif = list(tum_tokenlar)\n        silinen = 0\n    else:\n        sink_kismi = list(tum_tokenlar[:sink_sayisi]) if sink_sayisi > 0 else []\n        pencere_kismi = list(tum_tokenlar[-pencere_boyutu:])\n        aktif = sink_kismi + pencere_kismi\n        silinen = len(tum_tokenlar) - kapasite\n    return {'aktif_kv_tokenlari': aktif, 'rope_konumlari': list(range(len(aktif))), 'silinen_token_sayisi': silinen, 'kapasite': kapasite}\n\nimport math\n\ndef linear_attention_ileri(Q, K, V, eps=1e-06):\n    T = len(Q)\n    d = len(Q[0])\n    S = [[0.0] * d for _ in range(d)]\n    Z = [0.0] * d\n    cikti = []\n\n    def phi(x):\n        return x + 1.0 if x >= 0 else math.exp(x)\n    for t in range(T):\n        qt = [phi(x) for x in Q[t]]\n        kt = [phi(x) for x in K[t]]\n        vt = V[t]\n        for i in range(d):\n            Z[i] += kt[i]\n            for j in range(d):\n                S[i][j] += kt[i] * vt[j]\n        payda = sum((qt[i] * Z[i] for i in range(d))) + eps\n        yt = [round(sum((qt[i] * S[i][j] for i in range(d))) / payda, 6) for j in range(d)]\n        cikti.append(yt)\n    return {'cikti': cikti, 'son_durum_S': [[round(S[i][j], 6) for j in range(d)] for i in range(d)], 'son_norm_Z': [round(Z[i], 6) for i in range(d)]}", 'referans', 'exec'), _REF)
_t, _g = _ff(streaming_kv_guncelle, _REF['streaming_kv_guncelle'], ([10, 20, 30, 40, 50, 60, 70, 80], 2, 3), tohum=3292, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (streaming_kv_guncelle): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(linear_attention_ileri, _REF['linear_attention_ileri'], ([[0.5, -0.5], [1.0, 0.0]], [[0.2, 0.8], [-0.4, 0.6]], [[1.0, 2.0], [3.0, 4.0]], 1e-06), tohum=3400, en_cok=600, mod='gecerli', butce='oto')
kontrol(_t, "farksal tarama (linear_attention_ileri): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
kontrol(linear_attention_ileri([[-7.0, -7.0]], [[-7.0, -7.0]], [[1000.0, 500.0]]) == _REF['linear_attention_ileri']([[-7.0, -7.0]], [[-7.0, -7.0]], [[1000.0, 500.0]]), "varsayılan eps=1e-6 payda kararlılığı korunmalı")
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_19 as D
try: r = D.deney(streaming_kv_guncelle, linear_attention_ileri)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['secim_dogru'], 'her konumda sink + pencere tokenları ve önbellek içi konumlar doğru')
kontrol(r['sink_kurtariyor'], "önbellekli kipte sink'ler perplexity'yi yalnız pencereye göre düşürüyor")
kontrol(r['linear_ayni'], "doğrusal dikkat gerçek Q/K/V'de torch referansıyla aynı")
kontrol(r['sistem_dusuyor_sabitleme_koruyor'], 'sistem istemi pencereden düşünce cevap kayboldu, öğrencinin işleviyle sabitlenince geri geldi')
ai_lab.kanit_yaz("ai-uretim-19-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-19", "deney": r})
```
```solution
import ai_lab
def streaming_kv_guncelle(tum_tokenlar, sink_sayisi, pencere_boyutu):
    kapasite = sink_sayisi + pencere_boyutu
    if len(tum_tokenlar) <= kapasite:
        aktif = list(tum_tokenlar)
        silinen = 0
    else:
        sink_kismi = list(tum_tokenlar[:sink_sayisi]) if sink_sayisi > 0 else []
        pencere_kismi = list(tum_tokenlar[-pencere_boyutu:])
        aktif = sink_kismi + pencere_kismi
        silinen = len(tum_tokenlar) - kapasite
    return {'aktif_kv_tokenlari': aktif, 'rope_konumlari': list(range(len(aktif))), 'silinen_token_sayisi': silinen, 'kapasite': kapasite}

import math

def linear_attention_ileri(Q, K, V, eps=1e-06):
    T = len(Q)
    d = len(Q[0])
    S = [[0.0] * d for _ in range(d)]
    Z = [0.0] * d
    cikti = []

    def phi(x):
        return x + 1.0 if x >= 0 else math.exp(x)
    for t in range(T):
        qt = [phi(x) for x in Q[t]]
        kt = [phi(x) for x in K[t]]
        vt = V[t]
        for i in range(d):
            Z[i] += kt[i]
            for j in range(d):
                S[i][j] += kt[i] * vt[j]
        payda = sum((qt[i] * Z[i] for i in range(d))) + eps
        yt = [round(sum((qt[i] * S[i][j] for i in range(d))) / payda, 6) for j in range(d)]
        cikti.append(yt)
    return {'cikti': cikti, 'son_durum_S': [[round(S[i][j], 6) for j in range(d)] for i in range(d)], 'son_norm_Z': [round(Z[i], 6) for i in range(d)]}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_19 as D
    D.goster(streaming_kv_guncelle, linear_attention_ileri)
```
```hint
İki görevin çözümlerini olduğu gibi buraya koy.
```
:::

::: anlat Sınır
Görevler StreamingLLM'in sink token ve kayan KV penceresini, ELU+1 kernel'li linear attention'ı saf Python ile hesaplatır; final adım sink etkisini gerçek SmolLM2'de perplexity ile ölçer. StreamingLLM akışı kararlı tutar ama pencereden düşen bilgiyi hatırlamaz; uzun bağlam belleği sağlamaz. Özel bir sink token ile eğitilmemiş modellerde bu rolü ilk birkaç token üstlenir. Linear attention softmax dikkatinin yerini kayıpsız tutmaz; geri çağırma (recall) görevlerinde belirgin kalite kaybı vardır. Sistem istemi pencereden düşerse güvenlik talimatları da düşer; sink'ler ve sabit tutulan önek bu yüzden bilinçli seçilmelidir.

Kaynaklar: [Xiao vd. 2023 - Efficient Streaming Language Models with Attention Sinks](https://arxiv.org/abs/2309.17453), [Beltagy vd. 2020 - Longformer: The Long-Document Transformer](https://arxiv.org/abs/2004.05150), [Katharopoulos vd. 2020 - Transformers are RNNs: Fast Autoregressive Transformers with Linear Attention](https://arxiv.org/abs/2006.16236).
:::

::: dusun
Sahnede bir araştırmacı el kaldırdı:
*"Hocam, `StreamingLLM` (`Attention Sinks` + `Sliding Window`) sayesinde modelin 4 milyon `token` boyunca hiç çökmeden akıcı şekilde konuşabildiğini gördük. Peki kullanıcı sohbetin 10. kelimesinde `'Benim gizli şifrem 4815162342'` dediyse ve biz 100.000. kelimedeyken `'Benim gizli şifrem neydi?'` diye sorarsa, `StreamingLLM` bu şifreyi hatırlayabilir mi?"*

Bu soruya **`Infinite Fluent Generation` (Çökmeden Akıcı Üretim) vs `Long-Term Exact Memory Retrieval` (Uzun Vadeli Kesin Hatırlama)** farkı ve neden üretim sistemlerinde `StreamingLLM` penceresinin yanında bir **`External Vector RAG / Episodic KV-Memory`** veya **hibrit `Global Attention` katmanı** gerektiği üzerinden nasıl cevap verirsin?
:::

::: ozet
- **`Sliding Window Attention (SWA)`**, her `token`'ın yalnızca son $W$ komşusuna dikkat etmesini sağlayarak adım başına dikkat maliyetini $O(T^2)$'den $O(T \cdot W)$'ye ve `KV-Cache` boyutunu sabit $W$ sınırına indirir; üst üste binen $L$ katman sayesinde etkin görüş alanı $L \times W$ olarak büyür.
- **`Attention Sinks (StreamingLLM)`**, `Softmax` toplamının $1.0$ olma zorunluluğu nedeniyle modelin fazladan dikkat enerjisini dizinin en başındaki ilk 4 `token`'a boşalttığını kanıtlamıştır; bu ilk $S$ `token` önbellekte sabit tutulup son $W$ `token` kaydırıldığında sonsuz uzunlukta akış (`Infinite Streaming`) sıfır çökme ile sağlanır.
- **`Linear Attention`**, $\phi(x) = \text{elu}(x) + 1$ gibi pozitif bir çekirdek özellik haritasıyla matris çarpım sırasını $\phi(Q)(\phi(K)^\top V)$ şeklinde değiştirerek $O(N d^2)$ karmaşıklıkta ve sabit boyutlu $S_t \in \mathbb{R}^{d \times d}$ durum özetiyle doğrusal zamanda çalışır.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Kayan pencere ve çöküş bilmecesi (30 sn).** "Yalnız son $W$ tokenı tutan `Sliding Window Attention` sabit bellek kullanır; ancak ilk birkaç başlangıç tokenı pencereden düştüğü anda `Softmax` paydası çöker ve perplexity patlar."
2. **`Attention Sinks` (`StreamingLLM`) (35 sn).** "`Softmax` toplamı her zaman 1 olmak zorunda olduğu için model 'hiçbir yere bakmak istemediği' fazla olasılık kütlesini hep ilk 1–4 tokena boşaltır; bu lavabo tokenları sabit tutup yanına kayan pencere eklemek akışı kararlı tutar."
3. **`Linear Attention` birleşme özelliği (30 sn).** "$\exp(q k^T)$ yerine pozitif çekirdek dönüşümü $\phi(q)(\phi(k)^T v)$ kullanıldığında çarpım sırası değiştirilerek maliyet $O(N^2)$'den sabit durumlu $O(N)$ yinelemeye iner."
4. **Soru (25 sn).** "`StreamingLLM` ilk 4 lavabo tokenı ve son $W$ tokenı tutarak akışı sürdürdüğünde, ortada elenen binlerce tokendaki kesin olguları hatırlayabilir mi?"
:::
