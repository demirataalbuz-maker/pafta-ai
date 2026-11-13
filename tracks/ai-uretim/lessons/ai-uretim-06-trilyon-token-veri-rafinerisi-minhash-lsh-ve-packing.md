---
id: ai-uretim-06
title: "Trilyon-Token Veri Rafinerisi: MinHash LSH Deduplication, Kalite Süzgeci ve Document Packing"
track: ai-uretim
order: 6
duration_minutes: 35
difficulty: orta
xp: 280
prerequisites: [ai-uretim-05]
summary: "CommonCrawl ham verisinden FineWeb-Edu ve Frontier eğitim seti nasıl üretilir? N-gram Shingling, MinHash Signature, Locality-Sensitive Hashing (LSH) Banding ile aday bulma, FastText/Perplexity süzgeci ve Cross-Document Attention Mask ile Sequence Packing."
tags: [data-refinery, minhash-lsh, deduplication, sequence-packing, cross-document-mask, fineweb]
esleme: ai-saldiri-13, ai-savunma-18
---

::: anlat 1. "Garbage In, Garbage Out": Ham CommonCrawl Çöplüğünden 15 Trilyon Token'lık Altın Madeni Çıkarmak
## Training verisini hazırlama

Aynı metnin tekrarları ve belge sınırlarının yanlış işlenmesi eğitimden elde edilen bilgiyi etkileyebilir. Bu derste shingle, MinHash ve LSH ile benzerlik adaylarını bulacak; belgeleri sabit uzunluklu dizilere yerleştirirken belge içi attention maskesini koruyacaksın. Filtre kararının hangi bilgiyi kaybettiğini de değerlendir.

Bir konferansta ya da `Frontier AI` laboratuvarında şu gerçekle yüzleşirsin:
> *"Dünyanın en gelişmiş `DeepSeekMoE` veya `Transformer` mimarisini kodlasanız bile, modeli ham internet verisiyle (`Raw CommonCrawl`) doğrudan eğitirseniz elinize sadece spam reklamlar, kopyala-yapıştır haber siteleri, çerez (`cookie`) uyarıları ve bozuk HTML etiketleri kusan aptal bir model geçer!"*

Bugün `Llama-3`, `DeepSeek-V3` veya HuggingFace'in açık kaynak şaheseri **`FineWeb-Edu`** veri kümeleri, farklı veri seçme, kalite süzme ve tekilleştirme reçeteleri kullanır. Elenen veri oranı, başlangıç derlemi ve her aşamanın tanımına bağlıdır; bu modeller için tek bir ortak yüzde varsayılmaz. Aşağıdaki şema bileşenlerin öğretici bir birleşimidir, hepsinin aynı reçetesi değildir:

```text
  [1. HAM COMMONCRAWL ARŞİVİ (WARC/HTML; boyut seçilen snapshotlara bağlı)]
                                    │
                                    ▼
  [2. URL & METİN ÇIKARIMI (trafilatura / jusText: Menü, Reklam ve HTML Temizliği)]
                                    │
                                    ▼
  [3. MINHASH LSH FUZZY DEDUPLICATION (N-gram Shingling -> MinHash -> LSH Banding)]
      • Shingle imzalarıyla yakın kopya adaylarını bulma; bant isabeti kesin benzerlik eşiği değildir
                                    │
                                    ▼
  [4. HEURISTIC & MODEL-BASED QUALITY FILTERING (C4 / Gopher Kuralları + FastText / KenLM)]
      • Perplexity (KenLM) ve eğitici değer sınıflandırıcısı (FineWeb-Edu Classifier)
                                    │
                                    ▼
  [5. PII REDACTION & DECONTAMINATION (Kişisel Veri Maskeleme + Benchmark Test Sızıntısı Silme)]
                                    │
                                    ▼
  [6. SEQUENCE PACKING & CROSS-DOCUMENT MASKING (<|eos|> ile Paketleme + doc_ids Maskesi)]
```

### 🚨 Neden Tekilleştirme (`Deduplication`) Yapmazsak Model Çöker?
Ham internette aynı basın bülteni, aynı yemek tarifi veya `"Bu site çerezleri kullanmaktadır"` metni **milyonlarca kez** kopyalanmıştır. Eğer veri kümesini tekilleştirmezsen (`Deduplication`):
1. **`Memorization & Regurgitation` (Ezberleme):** Model genel dil mantığını öğrenmek yerine o metni harfi harfine ezberler ve kullanıcıya papağan gibi aynı metni kusar.
2. **Hesap ve örnek ağırlığı:** Tekrarlar bazı metinlerin eğitimde daha sık örneklenmesine ve yeni içerik için ayrılan hesap payının azalmasına yol açar. Bu, tek başına double descent veya grokking için bir sonuç kanıtlamaz; genelleme ve ezberleme ayrı ölçülür.

**Uygulama sınırı:** Görevler Python ile küçük, denetlenebilir hesaplar yapar. `python norun` blokları PyTorch/GPU tarafını incelemek içindir; bu tezgâhta otomatik çalıştırılıp gerçek training/serving kabulü yapılmaz.

**Birincil kaynak:** [FineWeb veri çalışması](https://arxiv.org/abs/2406.17557). Kaynak, yöntemin ayrıntıları içindir; dersteki küçük örnek ölçülmüş üretim benchmarkı değildir.
:::

::: anlat 2. Milyarlarca Belgeyi $O(N^2)$ Yerine $O(N)$ Sürede Tekilleştirmek: Shingling, MinHash ve LSH Banding
Sorun şudur: Birebir aynı (`Exact Match`) belgeleri `SHA-256` özetiyle bulmak kolaydır; ama iki haber sitesi aynı yazının sadece başlığını ve son cümlesini değiştirdiyse (`Near-Duplicate / Fuzzy Match`), `SHA-256` tamamen farklı çıkar!

İki belgenin ($A$ ve $B$) ne kadar benzediğini ölçen altın standart, $n$-gram parçalarının (**`Shingles`**) kesişiminin birleşimine oranı olan **`Jaccard Similarity`** değeridir:

$$J(A, B) = \frac{|S_A \cap S_B|}{|S_A \cup S_B|}$$

**Felaket:** Elinde $N = 5\text{ Milyar}$ web sayfası varsa, her belgeyi diğer her belgeyle karşılaştırmak $\binom{N}{2} \approx \mathbf{1.25 \times 10^{19}}$ çift demektir. Gerçek karşılaştırma süresi belge uzunluğu, donanım ve paralelliğe bağlıdır; burada süre tahmini yapılmaz.

Bütün çiftleri karşılaştırmadan aday bulmak için ne yapabiliriz? **3 Adımlı `MinHash LSH` Algoritması:**

### Adım 1: `N-Gram Shingling` (Metni Kiremit Parçalarına Bölmek)
Belgeyi kelimelere (veya karakterlere) ayırıp kayan bir pencereyle $n$-uzunluklu alt diziler (**`$n$-shingles`**, örn. 5-gram) kümesine dönüştürürüz ve her `shingle`'ı hızlı bir tam sayı özetine (`Hash Integer`) çeviririz.

### Adım 2: `MinHash Signature` (Kümeyi Sabit Boyutlu Parmak İzine Sıkıştırmak)
Binlerce elemanlı `shingle` kümesi üzerinde $M$ adet (örn. $M = 128$) farklı doğrusal özet fonksiyonu ($h_k(x) = (a_k x + b_k) \bmod P$) çalıştırırız. Her $h_k$ fonksiyonu için kümedeki elemanların aldığı **en küçük özet değerini (`Minimum Hash`)** seçeriz:

$$\text{Sig}_k(A) = \min_{s \in S_A} h_k(s)$$

**İdeal MinHash:** Birleşim kümesi üzerinde eşit olasılıklı rastgele permütasyon seçilirse, en küçük eleman kesişimde olduğunda ve ancak o zaman iki minimum eşleşir. Birleşimin her elemanı aynı olasılıkla minimum olduğundan eşleşme olasılığı kesişim/birleşim oranıdır. Görevdeki sabit doğrusal hash ailesi ve basit karakter özeti tam rastgele permütasyon değildir; aşağıdaki eşitlik onun için kesin garanti olarak kullanılmaz.

$$P\big(\text{Sig}_k(A) = \text{Sig}_k(B)\big) = J(A, B)$$

### Adım 3: `Locality-Sensitive Hashing (LSH) Banding` ve Aday Bulma Maliyeti
$M = b \times r$ uzunluğundaki `MinHash` imzasını, her biri $r$ satırdan (`rows per band`) oluşan **$b$ adet banda (`bands`)** böleriz (örn. $M = 128 \to b = 16\text{ bant} \times r = 8\text{ satır}$).
- Her belge için bu $b$ bandın her birini ayrı bir `Hash Bucket` (kova) tablosuna atarız.
- **Kural:** İki belge, **$b$ banttan EN AZ BİRİNDE (`at least one band`) birebir aynı $r$ satırlık alt-imzaya sahipse** aynı kovaya düşer (`Candidate Pair` — Aday Çift)! Hiçbir bantta çakışmayan milyarlarca belgeye hiç bakılmaz bile!

İdeal MinHash satırlarının bağımsız olduğu varsayımıyla, iki belgenin benzerliği $s=J(A,B)$ için:
- Tek bir bantta $r$ satırın tamamının eşleşme olasılığı: $s^r$
- Tek bir bantta eşleşmeme olasılığı: $1 - s^r$
- **$b$ bandın hiçbirinde eşleşmeme olasılığı:** $(1 - s^r)^b$
- **En az 1 bantta çakışıp yakalanma olasılığı (`S-Curve`):**

$$P_{\text{aday}}(s) = 1 - (1 - s^r)^b$$

Bu olasılık modeli görevdeki sabit hash ailesinde yaklaşık bir sezgidir. Genel aday üretiminde büyük kovalar çok sayıda çift doğurabilir; tüm işin en kötü durumu O(N) değildir. İmza hesabı toplam shingle sayısı S ve imza boyu M için O(SM), sabit bant sayısıyla kova eklemeleri beklenen O(Nb), adayları tek tek doğrulama ise aday sayısına bağlıdır. Görev yalnız korunan belgelerin bantlarını set içinde tutar ve bir isabette belgeyi eler; aday çiftlerini tek tek çıkarıp Jaccard doğrulamaz. Bu nedenle yanlış elemeler mümkündür.

Bu fonksiyon keskin bir **S-Eğrisi (`S-Curve`)** oluşturur ve eşik değeri yaklaşık $\tau \approx (1/b)^{1/r}$ noktasında sıçrama yapar!

```python
def lsh_yakalanma_olasiligi(jaccard_s, b_bant, r_satir):
    return round(1.0 - ((1.0 - (jaccard_s ** r_satir)) ** b_bant), 4)

# b=16 bant, r=8 satır (Toplam 128 MinHash fonksiyonu)
for s in [0.2, 0.5, 0.7, 0.85, 0.95]:
    print(f"Jaccard Benzerligi s={s:.2f} -> LSH Kovasinda Yakalanma Olasiligi: {lsh_yakalanma_olasiligi(s, 16, 8):.4f}")
```
:::

::: anlat 3. Kalite Süzgeci (Quality Filtering): Heuristic Kurallar, KenLM Perplexity ve FineWeb-Edu
Kopyaları `MinHash LSH` ile temizledikten sonra kalan tekil sayfaların kalitesini nasıl ölçeriz? Üç katmanlı bir elek kullanılır:

1. **`Heuristic Rule Filters` (`Gopher / C4 / FineWeb` Kuralları):**
   - Kelime sayısı çok az ($< 50$) veya aşırı uzun belgeleri at.
   - Ortalama kelime uzunluğu $[3, 10]$ karakter aralığında olmayanları (bozuk base64/hex dökümlerini) at.
   - Satırlarının `%30`'undan fazlası `"..."` (üç nokta) ile biten veya `"{", "}"` sembol yoğunluğu yüksek (kırpılmış menü/JavaScript) sayfaları at.
   - Tekrarlayan $n$-gram oranı (`Duplicate Line / N-gram Fraction`) eşiği aşan spam metinleri at.
2. **`KenLM Perplexity Filtering` (`CCNet` Yöntemi):**
   - CCNet yaklaşımında Wikipedia üzerinde bir $n$-gram dil modeli (`KenLM`) eğitilir.
   - Ham web sayfası bu modele okutulur; perplexity değeri bu referans dağılımında yüksekse filtre politikası onu eleyebilir. Bu, metnin kesin anlamsız olduğunu göstermez; farklı dil veya uzmanlık alanı da yüksek perplexity üretebilir.
3. **`Model-Based Educational Classifier` (`FineWeb-Edu` & `DeepSeek` Sırrı):**
   - `Llama-3-70B` gibi güçlü bir modele yüz binlerce web sayfası okutulup *"Bu metnin bir öğrenci veya bilim insanı için eğitici değeri 0 ile 5 arasında kaçtır?"* diye puanlatılır (`Synthetic Annotations`).
   - FineWeb-Edu çalışmasında `Snowflake-arctic-embed-m` üzerinde dondurulmuş encoder ve embedding'lerle doğrusal bir regresyon başı eğitilir. Tahminler 0–5 tamsayı skorlarına yuvarlanır ve en az 3 seçilir ([FineWeb, Bölüm 4](https://arxiv.org/html/2406.17557v1#S4)). Bu sınıflandırıcı kararıdır, her seçilen belgenin doğruluğu veya ders kitabı kalitesi garantisi değildir. Bu derste baş eğitimi yapılmaz; mekanizması anlatılır.
:::

::: anlat 4. Sequence Packing ve Cross-Document Attention Masking (Belge İçi Dikkat Yalıtımı)
Rafineriden çıkan tertemiz belgelerimiz hazır! Ancak bir belge $300\text{ token}$, diğeri $1.200\text{ token}$ uzunluğunda; oysa bizim `Transformer` modelimizin eğitim context window sabit (**`Context Length` $L = 4096$ veya $8192$**).

### ❌ Eski Yöntem: `Padding` (Dolgu Token'ları) Neden GPU Katilidir?
Eğer $300\text{ token}$'lık bir belgeyi $4096$'ya tamamlamak için sonuna $3796$ tane `<|pad|>` eklersen, slotların yaklaşık %92.7'si dolgu olur. Slot oranı, kernel verimi veya toplam GPU zamanıyla aynı ölçü değildir.

### 🚀 Modern Çözüm: `Concat-and-Chunk Sequence Packing` + `Document-Level Causal Mask`
Bütün belgelerin sonuna bir **`<|eos|>` (`End-of-Sequence` / Belge Sonu)** `token`'ı eklenir, hepsi uç uca dev bir şerit halinde birleştirilir ve tam $L$ boyutunda bloklara (`Chunks`) kesilir! Tam dolu pencerelerde dolgu slotu kalmaz; son eksik pencere ve sınır politikası hâlâ dolgu üretebilir. Bu, GPU kullanımının %100 olacağı anlamına gelmez.

**AMA ÇOK ÖNEMLİ BİR TUZAK VAR (`Cross-Document Contamination`):**
Aynı $L$ penceresinin içine paketlenen **Belge 1** ("Kuantum fiziği...") ile hemen arkasından gelen **Belge 2** ("Mercimek çorbası tarifi...") aynı diziyi paylaşır. Eğer standart alt-üçgen `Causal Mask` ($j \le i$) kullanırsan, **Belge 2'nin kelimeleri `Self-Attention` sırasında Belge 1'in kelimelerine dikkat (`Attend`) eder!** Mercimek çorbası cümlesi, kuantum fiziği cümlesinden bağlam çalar!

Bunu önlemek için her `token`'ın hangi belgeye ait olduğunu tutan bir **`doc_ids`** vektörü üretilir ve **`Cross-Document Causal Attention Mask`** şu iki kuralın kesişimi (`AND`) olarak kurulur:
1. **Nedensellik (`Causality`):** Bakılan konum $j$, mevcut konum $i$'den büyük olamaz ($j \le i$).
2. **Belge Yalıtımı (`Document Isolation`):** Konum $i$ ve konum $j$ **aynı belgeye ait olmalıdır** ($\text{doc\_id}[i] == \text{doc\_id}[j]$).

$$M_{i, j} = \begin{cases} 1 \text{ (İzin Ver)}, & \text{eğer } j \le i \text{ ve } \text{doc\_id}[i] = \text{doc\_id}[j] \\ 0 \text{ (Maskele / } -\infty\text{)}, & \text{aksi halde} \end{cases}$$

Bu sayede dikkat matrisi **Blok-Alt-Üçgen (`Block-Lower-Triangular`)** bir yapıya kavuşur ve `FlashAttention varlen (cu_seqlens)` çekirdekleriyle sıfır bellek israfıyla çalıştırılır!

```text
Token Dizisi : [T1, T2, <eos>, T3, T4, T5, <eos>]
doc_ids      : [ 0,  0,   0  ,  1,  1,  1,   1  ]

Cross-Document Causal Mask (M_ij):
       0  0  0 | 1  1  1  1
    ┌──────────┼───────────┐
  0 │  1  0  0 │ 0  0  0  0 │  <-- Belge 0 (Yalnızca kendine ve geçmişine bakar)
  0 │  1  1  0 │ 0  0  0  0 │
  0 │  1  1  1 │ 0  0  0  0 │
    ├──────────┼───────────┤
  1 │  0  0  0 │ 1  0  0  0 │  <-- Belge 1 (Belge 0'a ASLA bakamaz! Sıfırlanır!)
  1 │  0  0  0 │ 1  1  0  0 │
  1 │  0  0  0 │ 1  1  1  0 │
  1 │  0  0  0 │ 1  1  1  1 │
    └──────────┴───────────┘
```
:::

::: tahmin MinHash Benzerliği ve Paketlenmiş Belge Maskesi
İki belgenin $10$ elemanlı `MinHash` imzaları `sig_A` ve `sig_B` olarak verilmiştir. Ayrıca iki küçük belgenin paketlenmesiyle oluşan `doc_ids = [0, 0, 1, 1]` dizisi için `4x4` boyutundaki `Cross-Document Causal Mask` matrisinde toplam kaç adet `1` (aktif dikkat bağlantısı) bulunur?

```python
sig_A = [12, 45, 7, 89, 23, 56, 11, 90, 34, 67]
sig_B = [12, 99, 7, 89, 23, 10, 11, 90, 34, 67]

minhash_tahmini = sum(a == b for a, b in zip(sig_A, sig_B)) / len(sig_A)
doc_ids = [0, 0, 1, 1]
aktif_baglanti = sum(
    1 for i in range(4) for j in range(4)
    if j <= i and doc_ids[i] == doc_ids[j]
)
print(f"MinHash Jaccard Tahmini: {minhash_tahmini:.2f} | Aktif Dikkat Hucresi: {aktif_baglanti}")
```

???

```cikti
MinHash Jaccard Tahmini: 0.80 | Aktif Dikkat Hucresi: 6
```
$10$ imza konumundan $8$'i birebir eşleştiği için `MinHash` Jaccard benzerlik tahmini $8/10 = 0.80$'dir. `doc_ids = [0, 0, 1, 1]` için standart `Causal Mask` olsaydı $1+2+3+4 = 10$ aktif hücre olurdu; ancak `Belge 1` (`indeks 2, 3`), `Belge 0` (`indeks 0, 1`) konumlarına bakamadığı için her iki belgede $1+2 = 3$'er hücreden toplam $3 + 3 = 6$ aktif dikkat bağlantısı kalır.
:::

::: gorev 1 · Shingle, MinHash İmzası ve LSH Bant Çakışmasıyla Tekilleştirme
Verilen belgeleri `MinHash` ve `LSH Banding` kullanarak $O(N)$ kova mantığıyla tekilleştiren `lsh_tekillestir(belgeler, bant_sayisi, satir_sayisi)` işlevini yaz:

1. **Girdiler:**
   - `belgeler`: Metin dizelerinden (`str`) oluşan liste.
   - `bant_sayisi`: LSH bant sayısı $b$ (`int > 0`).
   - `satir_sayisi`: Bant başına satır sayısı $r$ (`int > 0`). Toplam imza uzunluğu $M = b \times r$'dir.
2. **Algoritma Adımları:**
   - **Adım 1 (Kelime 2-gram Shingling):** Her belgeyi küçük harfe çevirip (`lower()`) boşluklardan kelimelere (`split()`) ayır. Ardışık kelime çiftlerinden (`"kelime1 kelime2"`) oluşan 2-gram kümesini çıkar. (Eğer belgede 2'den az kelime varsa tek kelimeyi küme olarak al; tamamen boşsa `{""}` al).
   - **Adım 2 (Deterministik MinHash İmzası):** Her `shingle` dizesi $s$ için temel tam sayı değerini karakter kodlarından şu deterministik polinomla hesapla:
     $$x(s) = \sum_{idx, ch \in \text{enumerate}(s)} (idx + 1) \cdot \text{ord}(ch)$$
     Ardından $k = 0, 1, \dots, M-1$ için $k$. özet fonksiyonu:
     $$h_k(s) = \big((2k + 3) \cdot x(s) + (5k + 7)\big) \bmod 10007$$
     Belgenin $k$. `MinHash` imza değeri, belgedeki tüm $s$ `shingle`'ları üzerinden $\min_{s} h_k(s)$ değeridir.
   - **Adım 3 (LSH Banding & Tekilleştirme):** Belgenin $M$ elemanlı imzasını $b$ adet banda böl ($i$. bant: `imza[i * r : (i + 1) * r]` demeti / `tuple`).
     - Belgeleri sırayla (`0`'dan `len(belgeler) - 1`'e) tara:
     - Eğer mevcut belgenin $b$ bandından **herhangi biri**, daha önce **kabul edilmiş (`korunan`)** bir belgenin aynı indeksli bandıyla birebir eşleşiyorsa (aynı LSH kovasına düşmüşse), bu belge **kopya (`Duplicate`)** kabul edilir ve `elenen_indeksler` listesine eklenir (**korunanların kovalarına eklenmez!**).
     - Hiçbir bantta çakışma yoksa belge `korunan_indeksler` listesine eklenir ve $b$ adet bandı LSH kovalarına kaydedilir.
3. **Dönüş Değeri:**
   `{"korunan_indeksler": [int, ...], "elenen_indeksler": [int, ...], "korunan_belgeler": [str, ...]}` sözlüğü döndür.

```starter
def lsh_tekillestir(belgeler, bant_sayisi, satir_sayisi):
    # KUSURLU BAŞLANGIÇ KODU: hiçbir belgeyi elemeden hepsini koruyor!
    return {
        "korunan_indeksler": list(range(len(belgeler))),
        "elenen_indeksler": [],
        "korunan_belgeler": list(belgeler),
    }

ornek_belgeler = [
    "derin ogrenme modellerinde dikkat mekanizmasi cok onemlidir",
    "derin ogrenme modellerinde dikkat mekanizmasi cok faydalidir",
    "kuantum bilgisayarlar superpozisyon ve dolaniklik kullanir",
]
print(lsh_tekillestir(ornek_belgeler, bant_sayisi=4, satir_sayisi=2))
```

```test
import copy

def _ref_lsh(belgeler, b, r):
    m = b * r
    kovalar = [set() for _ in range(b)]
    korunan_idx, elenen_idx, korunan_txt = [], [], []
    for idx, doc in enumerate(belgeler):
        kelimeler = doc.lower().split()
        if len(kelimeler) >= 2:
            shingles = {" ".join(kelimeler[i:i+2]) for i in range(len(kelimeler) - 1)}
        elif len(kelimeler) == 1:
            shingles = {kelimeler[0]}
        else:
            shingles = {""}
        x_vals = [sum((i + 1) * ord(ch) for i, ch in enumerate(s)) for s in shingles]
        imza = [min(((2 * k + 3) * x + (5 * k + 7)) % 10007 for x in x_vals) for k in range(m)]
        bantlar = [tuple(imza[bi * r : (bi + 1) * r]) for bi in range(b)]
        if any(bantlar[bi] in kovalar[bi] for bi in range(b)):
            elenen_idx.append(idx)
        else:
            korunan_idx.append(idx)
            korunan_txt.append(doc)
            for bi in range(b):
                kovalar[bi].add(bantlar[bi])
    return {
        "korunan_indeksler": korunan_idx,
        "elenen_indeksler": elenen_idx,
        "korunan_belgeler": korunan_txt,
    }

def sozlesme(fn):
    try:
        v1 = [
            "derin ogrenme modellerinde dikkat mekanizmasi cok onemlidir",
            "derin ogrenme modellerinde dikkat mekanizmasi cok faydalidir",
            "kuantum bilgisayarlar superpozisyon ve dolaniklik kullanir",
            "kuantum bilgisayarlar superpozisyon ve dolaniklik kullanir",
        ]
        v2 = [
            "frontier dil modelleri trilyonlarca token veri ile egitilir",
            "dagitik gpu kumelerinde ring allreduce ile gradyan senkronize edilir",
            "frontier dil modelleri trilyonlarca token veri ile dikkatlice egitilir",
        ]
        for docs, b, r in [(v1, 4, 2), (v2, 5, 2), (["tek", "tek", "farkli"], 2, 2)]:
            d_kopya = copy.deepcopy(docs)
            sonuc = fn(docs, b, r)
            bek = _ref_lsh(docs, b, r)
            if sonuc != bek or docs != d_kopya:
                return False
        # Deterministik hash katsayıları için çalıştırılarak üretilmiş karşı örnekler.
        for args, bek in [([['', ' ', 'word'], 1, 1], {'korunan_indeksler': [0, 2], 'elenen_indeksler': [1], 'korunan_belgeler': ['', 'word']}), ([['am baioa kaeüekfmnşingi ahcoemebllamek fibkkfe', 'am baioa jjomi iogimşcjdcübmjm', 'kaeüekfmnşingi ahcoemebllamek fibkkfe jjomi iogimşcjdcübmjm'], 2, 2], {'korunan_indeksler': [0, 1, 2], 'elenen_indeksler': [], 'korunan_belgeler': ['am baioa kaeüekfmnşingi ahcoemebllamek fibkkfe', 'am baioa jjomi iogimşcjdcübmjm', 'kaeüekfmnşingi ahcoemebllamek fibkkfe jjomi iogimşcjdcübmjm']}), ([['hdkgngnkcdgünh od odilşankbaüid jlbcjflfghmşüj nkblmboookeş', 'hdkgngnkcdgünh od odilşankbaüid jlbcjflfghmşüj fnhjhügojogükü edciilfdedifaşüfehel', 'odilşankbaüid jlbcjflfghmşüj nkblmboookeş fnhjhügojogükü edciilfdedifaşüfehel'], 1, 1], {'korunan_indeksler': [0, 2], 'elenen_indeksler': [1], 'korunan_belgeler': ['hdkgngnkcdgünh od odilşankbaüid jlbcjflfghmşüj nkblmboookeş', 'odilşankbaüid jlbcjflfghmşüj nkblmboookeş fnhjhügojogükü edciilfdedifaşüfehel']}), ([['doiamkcalünküeehjm igdlgjiimijflnjcme şmahcomjjnkşiblmik ln güşübbmhjnmdş', 'doiamkcalünküeehjm igdlgjiimijflnjcme kşşdikdjicjc şüghgjkbg', 'şmahcomjjnkşiblmik ln güşübbmhjnmdş kşşdikdjicjc şüghgjkbg'], 4, 3], {'korunan_indeksler': [0, 1], 'elenen_indeksler': [2], 'korunan_belgeler': ['doiamkcalünküeehjm igdlgjiimijflnjcme şmahcomjjnkşiblmik ln güşübbmhjnmdş', 'doiamkcalünküeehjm igdlgjiimijflnjcme kşşdikdjicjc şüghgjkbg']}), ([['ejclüügfjfooc hbhim koknd doocmjoüboeljaül iaecfllkjobmgijgjişe', 'ejclüügfjfooc hbhim hi übimalnofakükaüjş', 'koknd doocmjoüboeljaül iaecfllkjobmgijgjişe hi übimalnofakükaüjş'], 2, 1], {'korunan_indeksler': [0, 1, 2], 'elenen_indeksler': [], 'korunan_belgeler': ['ejclüügfjfooc hbhim koknd doocmjoüboeljaül iaecfllkjobmgijgjişe', 'ejclüügfjfooc hbhim hi übimalnofakükaüjş', 'koknd doocmjoüboeljaül iaecfllkjobmgijgjişe hi übimalnofakükaüjş']}), ([['cdbmlcadinje fncfşennblnb oüdojüücninfükcd md jjlmişnşüffdnkiaoüa', 'cdbmlcadinje fncfşennblnb oüdojüücninfükcd md fşeükeşşdhdeffbfşoü combückceji', 'oüdojüücninfükcd md jjlmişnşüffdnkiaoüa fşeükeşşdhdeffbfşoü combückceji'], 4, 3], {'korunan_indeksler': [0, 1], 'elenen_indeksler': [2], 'korunan_belgeler': ['cdbmlcadinje fncfşennblnb oüdojüücninfükcd md jjlmişnşüffdnkiaoüa', 'cdbmlcadinje fncfşennblnb oüdojüücninfükcd md fşeükeşşdhdeffbfşoü combückceji']}), ([['oşocllbülmijeojünjü gkhmghdü nib adhiükohcajşfge hcnjohankbncükoüngm', 'oşocllbülmijeojünjü gkhmghdü nib leaeeaüehd iiobincnoghüeüi', 'nib adhiükohcajşfge hcnjohankbncükoüngm leaeeaüehd iiobincnoghüeüi'], 2, 3], {'korunan_indeksler': [0, 1, 2], 'elenen_indeksler': [], 'korunan_belgeler': ['oşocllbülmijeojünjü gkhmghdü nib adhiükohcajşfge hcnjohankbncükoüngm', 'oşocllbülmijeojünjü gkhmghdü nib leaeeaüehd iiobincnoghüeüi', 'nib adhiükohcajşfge hcnjohankbncükoüngm leaeeaüehd iiobincnoghüeüi']}), ([['ehinoülemf jmkjüooügş dhljblbchmeşşfa d nüfclkmdelkj', 'ehinoülemf jmkjüooügş dhljblbchmeşşfa n kkedşfaekişjo', 'dhljblbchmeşşfa d nüfclkmdelkj n kkedşfaekişjo'], 4, 3], {'korunan_indeksler': [0, 1], 'elenen_indeksler': [2], 'korunan_belgeler': ['ehinoülemf jmkjüooügş dhljblbchmeşşfa d nüfclkmdelkj', 'ehinoülemf jmkjüooügş dhljblbchmeşşfa n kkedşfaekişjo']}), ([['şbgmg şn boicebhdg daşld üşijkjfeeb', 'şbgmg şn boicebhdg şjneoüjgfohfodeüjkş bokjadekgeccokn', 'boicebhdg daşld üşijkjfeeb şjneoüjgfohfodeüjkş bokjadekgeccokn'], 2, 1], {'korunan_indeksler': [0, 1], 'elenen_indeksler': [2], 'korunan_belgeler': ['şbgmg şn boicebhdg daşld üşijkjfeeb', 'şbgmg şn boicebhdg şjneoüjgfohfodeüjkş bokjadekgeccokn']}), ([['liişşeşmicahüedbelhh n ddci aehdnkdndşa mooniko', 'liişşeşmicahüedbelhh n ddci aehdnkdndşa bdecjggdşgdkohfhigjo obbbemeoüeüg', 'ddci aehdnkdndşa mooniko bdecjggdşgdkohfhigjo obbbemeoüeüg'], 4, 3], {'korunan_indeksler': [0, 2], 'elenen_indeksler': [1], 'korunan_belgeler': ['liişşeşmicahüedbelhh n ddci aehdnkdndşa mooniko', 'ddci aehdnkdndşa mooniko bdecjggdşgdkohfhigjo obbbemeoüeüg']})]:
            docs = copy.deepcopy(args[0])
            if fn(docs, args[1], args[2]) != bek or docs != args[0]: return False
        return True
    except Exception:
        return False

ok(sozlesme(lsh_tekillestir), "lsh_tekillestir 2-gram Shingle, MinHash ve LSH bant çakışmasıyla kopyaları elemeli")

def m_sadece_birebir(belgeler, b, r):
    gorulen = set()
    k_i, e_i, k_t = [], [], []
    for i, d in enumerate(belgeler):
        if d in gorulen:
            e_i.append(i)
        else:
            gorulen.add(d)
            k_i.append(i)
            k_t.append(d)
    return {"korunan_indeksler": k_i, "elenen_indeksler": e_i, "korunan_belgeler": k_t}

def m_hepsini_ele(belgeler, b, r):
    return {"korunan_indeksler": [0], "elenen_indeksler": list(range(1, len(belgeler))), "korunan_belgeler": belgeler[:1]}

for ad, m in [("Sadece birebir aynı metinleri eleyen (Fuzzy kaçıran)", m_sadece_birebir), ("İlk belge hariç hepsini eleyen", m_hepsini_ele)]:
    ok(not sozlesme(m), f"Yanlış çözüm/mutant yakalanmalı: {ad}")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def lsh_tekillestir(belgeler, bant_sayisi, satir_sayisi):\n    m = bant_sayisi * satir_sayisi\n    kovalar = [set() for _ in range(bant_sayisi)]\n    korunan_indeksler = []\n    elenen_indeksler = []\n    korunan_belgeler = []\n    for idx, belge in enumerate(belgeler):\n        kelimeler = belge.lower().split()\n        if len(kelimeler) >= 2:\n            shingles = {' '.join(kelimeler[i:i + 2]) for i in range(len(kelimeler) - 1)}\n        elif len(kelimeler) == 1:\n            shingles = {kelimeler[0]}\n        else:\n            shingles = {''}\n        x_degerleri = [sum(((i + 1) * ord(ch) for i, ch in enumerate(s))) for s in shingles]\n        imza = [min((((2 * k + 3) * x + (5 * k + 7)) % 10007 for x in x_degerleri)) for k in range(m)]\n        bantlar = [tuple(imza[bi * satir_sayisi:(bi + 1) * satir_sayisi]) for bi in range(bant_sayisi)]\n        if any((bantlar[bi] in kovalar[bi] for bi in range(bant_sayisi))):\n            elenen_indeksler.append(idx)\n        else:\n            korunan_indeksler.append(idx)\n            korunan_belgeler.append(belge)\n            for bi in range(bant_sayisi):\n                kovalar[bi].add(bantlar[bi])\n    return {'korunan_indeksler': korunan_indeksler, 'elenen_indeksler': elenen_indeksler, 'korunan_belgeler': korunan_belgeler}", 'referans', 'exec'), _REF)
_t, _g = _ff(lsh_tekillestir, _REF['lsh_tekillestir'], (['derin ogrenme modellerinde dikkat mekanizmasi cok onemlidir', 'derin ogrenme modellerinde dikkat mekanizmasi cok faydalidir', 'kuantum bilgisayarlar superpozisyon ve dolaniklik kullanir'], 4, 2), tohum=2674, en_cok=600, mod='gecerli', butce='oto', ekler=[(['derin ogrenme', 'derin ogrenme', 'kuantum bilgisayar'], 4, 2, )])
ok(_t, "farksal tarama (lsh_tekillestir): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def lsh_tekillestir(belgeler, bant_sayisi, satir_sayisi):
    m = bant_sayisi * satir_sayisi
    kovalar = [set() for _ in range(bant_sayisi)]
    korunan_indeksler = []
    elenen_indeksler = []
    korunan_belgeler = []

    for idx, belge in enumerate(belgeler):
        kelimeler = belge.lower().split()
        if len(kelimeler) >= 2:
            shingles = {" ".join(kelimeler[i:i + 2]) for i in range(len(kelimeler) - 1)}
        elif len(kelimeler) == 1:
            shingles = {kelimeler[0]}
        else:
            shingles = {""}

        x_degerleri = [sum((i + 1) * ord(ch) for i, ch in enumerate(s)) for s in shingles]
        imza = [
            min(((2 * k + 3) * x + (5 * k + 7)) % 10007 for x in x_degerleri)
            for k in range(m)
        ]
        bantlar = [tuple(imza[bi * satir_sayisi : (bi + 1) * satir_sayisi]) for bi in range(bant_sayisi)]

        if any(bantlar[bi] in kovalar[bi] for bi in range(bant_sayisi)):
            elenen_indeksler.append(idx)
        else:
            korunan_indeksler.append(idx)
            korunan_belgeler.append(belge)
            for bi in range(bant_sayisi):
                kovalar[bi].add(bantlar[bi])

    return {
        "korunan_indeksler": korunan_indeksler,
        "elenen_indeksler": elenen_indeksler,
        "korunan_belgeler": korunan_belgeler,
    }
```

```hint
Her belge için 2-gram kümesini çıkar, her shingle'ın `x(s)` değerini bul ve `m = bant_sayisi * satir_sayisi` adet hash fonksiyonu için minimumları alarak imzayı oluştur. İmzayı `bant_sayisi` adet tuple parçasına bölüp `kovalar[bi]` kümelerinde arat.
```
:::

::: gorev 2 · Sabit Bağlam Uzunluğuna Document Packing ve Belge İçi Attention Maskesi
Farklı uzunluktaki tokenize edilmiş belgeleri `<|eos|>` ile birleştirip ilk `baglam_boyutu` ($L$) penceresini ve `Cross-Document Causal Attention Mask` matrisini üreten `belge_paketle(token_dizileri, baglam_boyutu, eos_id)` işlevini yaz:

1. **Girdiler:**
   - `token_dizileri`: Her biri bir belgenin `token ID` listesi olan liste (örn. `[[10, 11], [20, 21, 22]]`).
   - `baglam_boyutu`: Paketlenecek pencere boyutu $L$ (`int > 0`).
   - `eos_id`: Her belgenin sonuna eklenecek `<|eos|>` kimlik numarası (`int`).
2. **Kurallar:**
   - Boş olmayan her belgenin (`len(dizi) > 0`) sonuna `eos_id` ekle ve bu belgeye ait tüm `token`lara (eklenen `eos_id` dahil!) sırasıyla `0, 1, 2, ...` şeklinde artan bir belge kimliği (`doc_id`) ata.
   - Bütün belgelerin `token`larını ve `doc_id`lerini tek bir akışta uç uca birleştir.
   - Eğer toplam uzunluk `baglam_boyutu` ($L$) değerinden küçükse, `L` uzunluğuna ulaşana kadar sona `eos_id` ve `doc_id = -1` (dolgu / `padding`) ekle; büyük veya eşitse ilk `L` elemanı (`[:baglam_boyutu]`) kesip al.
   - Bu `L` elemanlı pencere için $L \times L$ boyutunda ikili (`0` veya `1`) **`Cross-Document Causal Mask`** matrisi (`maske`) oluştur:
     - $i$. satır ve $j$. sütun için `maske[i][j] = 1` olması için:
       1. $j \le i$ (nedensellik / geçmişe bakma),
       2. `doc_ids[i] == doc_ids[j]` (aynı belge içinde olma),
       3. `doc_ids[i] != -1` (dolgu `token`ı olmama)
       şartlarının **üçü birden** sağlanmalıdır; aksi halde `0` olmalıdır!
3. **Dönüş Değeri:**
   `{"paketlenmis_tokenlar": [int, ...], "doc_ids": [int, ...], "maske": [[int, ...], ...], "aktif_dikkat_sayisi": int}` sözlüğü döndür (`aktif_dikkat_sayisi`, maske içindeki toplam `1` sayısıdır). Girdileri değiştirme.

```starter
def belge_paketle(token_dizileri, baglam_boyutu, eos_id):
    # KUSURLU BAŞLANGIÇ KODU: belge sınırlarını (doc_ids) dikkate almadan standart alt-üçgen maske üretiyor!
    paket = [eos_id] * baglam_boyutu
    doc_ids = [0] * baglam_boyutu
    maske = [[1 if j <= i else 0 for j in range(baglam_boyutu)] for i in range(baglam_boyutu)]
    return {
        "paketlenmis_tokenlar": paket,
        "doc_ids": doc_ids,
        "maske": maske,
        "aktif_dikkat_sayisi": sum(sum(satir) for satir in maske),
    }

print(belge_paketle([[101, 102], [201]], baglam_boyutu=5, eos_id=999))
```

```test
import copy

def _ref_paketle(diziler, L, eos_id):
    toks, dids = [], []
    doc_no = 0
    for d in diziler:
        if not d:
            continue
        for t in d:
            toks.append(t)
            dids.append(doc_no)
        toks.append(eos_id)
        dids.append(doc_no)
        doc_no += 1
    while len(toks) < L:
        toks.append(eos_id)
        dids.append(-1)
    toks = toks[:L]
    dids = dids[:L]
    maske = [
        [1 if (j <= i and dids[i] == dids[j] and dids[i] != -1) else 0 for j in range(L)]
        for i in range(L)
    ]
    return {
        "paketlenmis_tokenlar": toks,
        "doc_ids": dids,
        "maske": maske,
        "aktif_dikkat_sayisi": sum(sum(r) for r in maske),
    }

def sozlesme(fn):
    try:
        vakalar = [
            ([[101, 102], [201]], 5, 999),
            ([[10, 20], [30, 40, 50], [60]], 6, 0),
            ([[1, 2], [], [3]], 7, 99),
        ]
        for diziler, L, eos in vakalar:
            d_kopya = copy.deepcopy(diziler)
            sonuc = fn(diziler, L, eos)
            bek = _ref_paketle(diziler, L, eos)
            if sonuc != bek or diziler != d_kopya:
                return False
        return True
    except Exception:
        return False

ok(sozlesme(belge_paketle), "belge_paketle <|eos|> eklemeli, doc_ids üretmeli ve belgeler arası dikkati maskelemeli")

def m_capraz_belge_acik(diziler, L, eos):
    r = copy.deepcopy(_ref_paketle(diziler, L, eos))
    dids = r["doc_ids"]
    r["maske"] = [[1 if (j <= i and dids[i] != -1) else 0 for j in range(L)] for i in range(L)]
    r["aktif_dikkat_sayisi"] = sum(sum(s) for s in r["maske"])
    return r

def m_eos_unut(diziler, L, eos):
    r = copy.deepcopy(_ref_paketle(diziler, L, eos))
    r["paketlenmis_tokenlar"] = [0] * L
    return r

for ad, m in [("Belgeler arası dikkati kapatmayan (standart causal mask)", m_capraz_belge_acik), ("Token dizisini yanlış paketleyen", m_eos_unut)]:
    ok(not sozlesme(m), f"Yanlış çözüm/mutant yakalanmalı: {ad}")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def belge_paketle(token_dizileri, baglam_boyutu, eos_id):\n    toks = []\n    dids = []\n    doc_no = 0\n    for dizi in token_dizileri:\n        if not dizi:\n            continue\n        for t in dizi:\n            toks.append(t)\n            dids.append(doc_no)\n        toks.append(eos_id)\n        dids.append(doc_no)\n        doc_no += 1\n    while len(toks) < baglam_boyutu:\n        toks.append(eos_id)\n        dids.append(-1)\n    toks = toks[:baglam_boyutu]\n    dids = dids[:baglam_boyutu]\n    maske = [[1 if j <= i and dids[i] == dids[j] and (dids[i] != -1) else 0 for j in range(baglam_boyutu)] for i in range(baglam_boyutu)]\n    aktif = sum((sum(satir) for satir in maske))\n    return {'paketlenmis_tokenlar': toks, 'doc_ids': dids, 'maske': maske, 'aktif_dikkat_sayisi': aktif}", 'referans', 'exec'), _REF)
_t, _g = _ff(belge_paketle, _REF['belge_paketle'], ([[101, 102], [201]], 5, 999), tohum=2404, en_cok=600, mod='gecerli', butce='oto', ekler=[([[101, 102], [201]], 6, 999, ), ([[1]], 4, 0, )])
ok(_t, "farksal tarama (belge_paketle): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def belge_paketle(token_dizileri, baglam_boyutu, eos_id):
    toks = []
    dids = []
    doc_no = 0
    for dizi in token_dizileri:
        if not dizi:
            continue
        for t in dizi:
            toks.append(t)
            dids.append(doc_no)
        toks.append(eos_id)
        dids.append(doc_no)
        doc_no += 1

    while len(toks) < baglam_boyutu:
        toks.append(eos_id)
        dids.append(-1)

    toks = toks[:baglam_boyutu]
    dids = dids[:baglam_boyutu]

    maske = [
        [
            1 if (j <= i and dids[i] == dids[j] and dids[i] != -1) else 0
            for j in range(baglam_boyutu)
        ]
        for i in range(baglam_boyutu)
    ]
    aktif = sum(sum(satir) for satir in maske)
    return {
        "paketlenmis_tokenlar": toks,
        "doc_ids": dids,
        "maske": maske,
        "aktif_dikkat_sayisi": aktif,
    }
```

```hint
Boş olmayan her belgenin elemanlarını ve ardından `eos_id` değerini `toks` listesine eklerken aynı `doc_no` değerini `dids` listesine ekle. Eksik kalan kısmı `eos_id` ve `-1` ile doldurup `[:baglam_boyutu]` dilimini al. Maskede `j <= i and dids[i] == dids[j] and dids[i] != -1` koşulunu kontrol et.
```
:::

::: gorev 3 · Gopher Tarzı Kural Tabanlı Kalite Süzgeci
Tekilleştirmeden sonra ikinci süzgeç **kalite**dir. DeepMind'ın Gopher veri hattı (Rae vd., 2021) basit, açıklanabilir kurallar kullanır. `kalite_suzgeci(metin, min_kelime=50, maks_kelime=100000, durak_kelimeleri=("the", "be", "to", "of", "and", "that", "have", "with"))` işlevini yaz.

**Ölçümler** (`kelimeler = metin.split()`, `satirlar` = boş olmayan satırlar):
- `kelime_sayisi`; `ortalama_kelime_uzunlugu` (kelime yoksa 0);
- `hash_orani` = `#` sayısı / kelime sayısı; `uc_nokta_orani` = (`"..."` + `"…"` sayısı) / kelime sayısı;
- `madde_satir_orani` = baştaki boşluk atıldığında `•`, `-` ya da `*` ile başlayan satır oranı; `uc_nokta_satir_orani` = sondaki boşluk atıldığında `...` ya da `…` ile biten satır oranı;
- `alfabetik_orani` = en az bir harf içeren kelime oranı;
- `durak_kelime_sayisi` = metinde geçen **farklı** durak kelimesi sayısı (kelime küçük harfe çevrilip baş/sondaki `.,;:!?"'()` atılarak karşılaştırılır).

Kelime ya da satır yoksa ilgili oran 0 sayılır. Oranları ve ortalamayı `round(·, 4)` ile yuvarla.

**Kurallar** (ihlal adları bu sırayla listelenir): `kelime_sayisi` (`min_kelime`–`maks_kelime` dışı), `ortalama_kelime_uzunlugu` (3–10 dışı), `sembol_orani` (hash ya da üç nokta oranı > 0.1), `madde_isareti` (> 0.9), `uc_nokta_satir` (> 0.3), `alfabetik` (< 0.8), `durak_kelime` (< 2).

Çıktı: `{"gecti": bool, "ihlaller": [...], "olcumler": {...}}` (ölçüm adları yukarıdaki gibi). `metin` `str` değilse, sınırlar negatif olmayan tam sayı değilse (`bool` dahil) ya da `min_kelime > maks_kelime` ise `ValueError`.

```starter
def kalite_suzgeci(metin, min_kelime=50, maks_kelime=100000, durak_kelimeleri=("the", "be", "to", "of", "and", "that", "have", "with")):
    # KUSURLU BAŞLANGIÇ: yalnız kelime sayısına bakıyor
    n = len(metin.split())
    ihlal = [] if min_kelime <= n <= maks_kelime else ["kelime_sayisi"]
    return {"gecti": not ihlal, "ihlaller": ihlal, "olcumler": {"kelime_sayisi": n}}

print(kalite_suzgeci("- the a\n- to b\n* and c", min_kelime=1))
```

```test
fn = need("kalite_suzgeci")
iyi = "The model learns to predict the next token and that skill transfers to many tasks with careful data."
r = fn(iyi, min_kelime=5)
eq(r["gecti"], True, "düzgün İngilizce cümle tüm kuralları geçer")
eq(r["olcumler"]["kelime_sayisi"], 18, "18 kelime")
eq(r["olcumler"]["ortalama_kelime_uzunlugu"], 4.6111, "toplam 83 karakter / 18 kelime")
eq(r["olcumler"]["durak_kelime_sayisi"], 5, "the, to, and, that, with (tekrarlar bir kez)")
eq(fn(iyi)["ihlaller"], ["kelime_sayisi"], "varsayılan en az 50 kelime: 18 kelime düşer")
r2 = fn("- the a\n- to b\n* and c", min_kelime=1)
eq(r2["ihlaller"], ["ortalama_kelime_uzunlugu", "madde_isareti", "alfabetik"], "9 kelime, ort 14/9, 3/3 madde satırı, 6/9 harfli")
eq(r2["olcumler"]["alfabetik_orani"], 0.6667, "6 / 9")
r3 = fn("the cat waits...\nand that dog...\nwith a bird", min_kelime=1)
eq(r3["ihlaller"], ["sembol_orani", "uc_nokta_satir"], "2 üç nokta / 9 kelime = 0.2222; 2/3 satır üç noktayla biter")
eq(r3["olcumler"]["uc_nokta_orani"], 0.2222, "2 / 9")
eq(r3["olcumler"]["uc_nokta_satir_orani"], 0.6667, "2 / 3")
eq(fn("#ai #ml the and", min_kelime=1)["ihlaller"], ["sembol_orani"], "2 hash / 4 kelime = 0.5")
eq(fn("kediler ve köpekler oynuyor", min_kelime=1)["ihlaller"], ["durak_kelime"], "İngilizce durak kelimesi yok")
eq(fn("", min_kelime=0)["ihlaller"], ["ortalama_kelime_uzunlugu", "alfabetik", "durak_kelime"], "boş metin: oranlar 0")
raises(ValueError, fn, 123)
raises(ValueError, fn, "x", 10, 5)
raises(ValueError, fn, "x", -1)
raises(ValueError, fn, "x", True)
for n, ihlal in ((100000, False), (100001, True)):
    metin = " ".join(["the", "and"] + ["cat"] * (n - 2))
    eq("kelime_sayisi" in fn(metin)["ihlaller"], ihlal, "varsayılan 100000 kelime üst sınırı")
eq(fn("#the and cat cat cat cat cat", 0)["olcumler"]["hash_orani"], 0.1429, "1/7 dört basamakta yuvarlanır")
eq(fn("- the and\nthe and\nthe and", 0)["olcumler"]["madde_satir_orani"], 0.3333, "1/3 madde satırı dört basamakta yuvarlanır")

# Eşiklerin kararları yuvarlanmamış oranlarla verilir.
for n, beklenen in ((49, False), (50, True), (51, True)):
    metin = " ".join(["the", "and"] + ["cat"] * (n - 2))
    eq(fn(metin)["gecti"], beklenen, "varsayılan 50 kelime alt sınırı: " + str(n))
for metin, durak, ihlal in (
    ("aaa bbb", ("aaa", "bbb"), False),
    ("aa bbb", ("aa", "bbb"), True),
    ("abcdefghij klmnopqrst", ("abcdefghij", "klmnopqrst"), False),
    ("abcdefghijk klmnopqrst", ("abcdefghijk", "klmnopqrst"), True),
):
    eq("ortalama_kelime_uzunlugu" in fn(metin, 0, 100, durak)["ihlaller"], ihlal, "ortalama 3/10 sınırları")
for isaret in ("#", "...", "…"):
    for n, ihlal in ((10, False), (9, True), (11, False)):
        # Üç nokta satır sonunda değildir; yalnız sembol oranını ölçer.
        metin = " ".join(["the" + isaret + "x", "and"] + ["cat"] * (n - 2))
        eq("sembol_orani" in fn(metin, 0)["ihlaller"], ihlal, "sembol 0.1 eşiği: " + repr((isaret, n)))
for sayi, ihlal in ((9, False), (10, True), (8, False)):
    metin = "\n".join(["- the and cat"] * sayi + ["the and cat"] * (10 - sayi))
    eq("madde_isareti" in fn(metin, 0)["ihlaller"], ihlal, "madde 0.9 eşiği")
for sayi, ihlal in ((3, False), (4, True), (2, False)):
    metin = "\n".join(["the and cat..."] * sayi + ["the and cat"] * (10 - sayi))
    eq("uc_nokta_satir" in fn(metin, 0)["ihlaller"], ihlal, "üç noktalı satır 0.3 eşiği")
for sayi, ihlal in ((8, False), (7, True), (9, False)):
    metin = " ".join(["the", "and"] + ["cat"] * (sayi - 2) + ["123"] * (10 - sayi))
    eq("alfabetik" in fn(metin, 0)["ihlaller"], ihlal, "alfabetik 0.8 eşiği")
for n, ihlal in ((50, False), (51, True)):
    metin = " ".join(["the", "and"] + ["cat"] * (n - 2))
    eq("kelime_sayisi" in fn(metin, 0, 50)["ihlaller"], ihlal, "özelleştirilmiş maksimum kelime sınırı")


# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile('def kalite_suzgeci(metin, min_kelime=50, maks_kelime=100000, durak_kelimeleri=(\'the\', \'be\', \'to\', \'of\', \'and\', \'that\', \'have\', \'with\')):\n    if not isinstance(metin, str):\n        raise ValueError(\'metin str olmalı\')\n    for v in (min_kelime, maks_kelime):\n        if isinstance(v, bool) or not isinstance(v, int) or v < 0:\n            raise ValueError(\'kelime sınırları negatif olmayan tam sayı olmalı\')\n    if min_kelime > maks_kelime:\n        raise ValueError(\'min_kelime <= maks_kelime olmalı\')\n    kelimeler = metin.split()\n    n = len(kelimeler)\n    satirlar = [s for s in metin.splitlines() if s.strip()]\n    ns = len(satirlar)\n    ort = sum((len(w) for w in kelimeler)) / n if n else 0.0\n    hash_o = metin.count(\'#\') / n if n else 0.0\n    uc_o = (metin.count(\'...\') + metin.count(\'…\')) / n if n else 0.0\n    madde = sum((1 for s in satirlar if s.lstrip().startswith((\'•\', \'-\', \'*\')))) / ns if ns else 0.0\n    uc_satir = sum((1 for s in satirlar if s.rstrip().endswith((\'...\', \'…\')))) / ns if ns else 0.0\n    alfa = sum((1 for w in kelimeler if any((ch.isalpha() for ch in w)))) / n if n else 0.0\n    durak = len({w.lower().strip(\'.,;:!?"\\\'()\') for w in kelimeler} & set(durak_kelimeleri))\n    ihlal = []\n    if not min_kelime <= n <= maks_kelime:\n        ihlal.append(\'kelime_sayisi\')\n    if not 3 <= ort <= 10:\n        ihlal.append(\'ortalama_kelime_uzunlugu\')\n    if hash_o > 0.1 or uc_o > 0.1:\n        ihlal.append(\'sembol_orani\')\n    if madde > 0.9:\n        ihlal.append(\'madde_isareti\')\n    if uc_satir > 0.3:\n        ihlal.append(\'uc_nokta_satir\')\n    if alfa < 0.8:\n        ihlal.append(\'alfabetik\')\n    if durak < 2:\n        ihlal.append(\'durak_kelime\')\n    return {\'gecti\': not ihlal, \'ihlaller\': ihlal, \'olcumler\': {\'kelime_sayisi\': n, \'ortalama_kelime_uzunlugu\': round(ort, 4), \'hash_orani\': round(hash_o, 4), \'uc_nokta_orani\': round(uc_o, 4), \'madde_satir_orani\': round(madde, 4), \'uc_nokta_satir_orani\': round(uc_satir, 4), \'alfabetik_orani\': round(alfa, 4), \'durak_kelime_sayisi\': durak}}', 'referans', 'exec'), _REF)
_t, _g = _ff(kalite_suzgeci, _REF['kalite_suzgeci'], ('- the a\n- to b\n* and c', 1, 100000, ('the', 'be', 'to', 'of', 'and', 'that', 'have', 'with')), tohum=2547, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (kalite_suzgeci): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def kalite_suzgeci(metin, min_kelime=50, maks_kelime=100000, durak_kelimeleri=("the", "be", "to", "of", "and", "that", "have", "with")):
    if not isinstance(metin, str):
        raise ValueError("metin str olmalı")
    for v in (min_kelime, maks_kelime):
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            raise ValueError("kelime sınırları negatif olmayan tam sayı olmalı")
    if min_kelime > maks_kelime:
        raise ValueError("min_kelime <= maks_kelime olmalı")
    kelimeler = metin.split()
    n = len(kelimeler)
    satirlar = [s for s in metin.splitlines() if s.strip()]
    ns = len(satirlar)
    ort = sum(len(w) for w in kelimeler) / n if n else 0.0
    hash_o = metin.count("#") / n if n else 0.0
    uc_o = (metin.count("...") + metin.count("…")) / n if n else 0.0
    madde = sum(1 for s in satirlar if s.lstrip().startswith(("•", "-", "*"))) / ns if ns else 0.0
    uc_satir = sum(1 for s in satirlar if s.rstrip().endswith(("...", "…"))) / ns if ns else 0.0
    alfa = sum(1 for w in kelimeler if any(ch.isalpha() for ch in w)) / n if n else 0.0
    durak = len({w.lower().strip(".,;:!?\"'()") for w in kelimeler} & set(durak_kelimeleri))
    ihlal = []
    if not (min_kelime <= n <= maks_kelime):
        ihlal.append("kelime_sayisi")
    if not (3 <= ort <= 10):
        ihlal.append("ortalama_kelime_uzunlugu")
    if hash_o > 0.1 or uc_o > 0.1:
        ihlal.append("sembol_orani")
    if madde > 0.9:
        ihlal.append("madde_isareti")
    if uc_satir > 0.3:
        ihlal.append("uc_nokta_satir")
    if alfa < 0.8:
        ihlal.append("alfabetik")
    if durak < 2:
        ihlal.append("durak_kelime")
    return {"gecti": not ihlal, "ihlaller": ihlal,
            "olcumler": {"kelime_sayisi": n, "ortalama_kelime_uzunlugu": round(ort, 4), "hash_orani": round(hash_o, 4),
                         "uc_nokta_orani": round(uc_o, 4), "madde_satir_orani": round(madde, 4),
                         "uc_nokta_satir_orani": round(uc_satir, 4), "alfabetik_orani": round(alfa, 4),
                         "durak_kelime_sayisi": durak}}
```

```hint
Önce bütün ölçümleri hesapla, sonra kuralları açıklamadaki sırayla `ihlal` listesine ekle. Kelime ya da satır yoksa bölme yapma, 0 kullan.
```
:::

::: anlat Gerçek deney: Gerçek paragraflar, gerçek model ve gerçek enjeksiyon verisiyle veri rafinerisi
Final üç işlevi de gerçek veriyle çalıştırır (indirme yok):

- **Tekilleştirme:** Pafta AI ders metinlerinden 60 gerçek paragraf seçilir. 20'sinin **yakın kopyası** (tek kelime değişmiş) ve 10'unun **kaçış kopyası** (saldırgan her üç kelimede bir dolgu kelimesi eklemiş) eklenir. Senin `lsh_tekillestir` işlevin (16 bant × 4 satır) bu 90 belgeyi işler; gerçek Jaccard benzerliği ve LSH'nin teorik yakalama olasılığı $1 - (1 - s^r)^b$ ile karşılaştırılır.
- **Packing:** dört gerçek belge (İngilizce, Türkçe, kod) SmolLM2 tokenizer'ıyla kodlanır ve senin `belge_paketle` işlevinle 96 tokenlık tek bağlama yerleşir. Senin maskeni modele **4B dikkat maskesi** olarak, belge başına sıfırlanan konumlarla birlikte veririz; paketli logit'ler her belge tek başına çalıştırıldığında çıkan logit'lerle karşılaştırılır. Aynı paket yalnız nedensel maskeyle de çalıştırılır: belgeler birbirini görür.
- **Kalite süzgeci:** gerçek `deepset/prompt-injections` test kümesindeki 116 metin (60 enjeksiyon, 56 zararsız) senin Gopher süzgecinden geçer.

Üçüncü ölçüm dersin güvenlik dersidir: kalite süzgeci bir **güvenlik** süzgeci değildir. Akıcı İngilizceyle yazılmış bir enjeksiyon tüm Gopher kurallarını geçer; ön eğitim verisine zehir sokmak isteyen biri tam da bunu yapar.

Kabul: üç işlevin farksal taramayı geçmesi; yakın kopyaların en az %90'ının elenmesi; paketli logit'lerin tek başına çalıştırmadan en çok `1e-3` farklı, maskesiz paketlemenin ise 0.1'den fazla farklı olması; süzgeçten en az bir enjeksiyonun geçmesi.

**Kanıt dosyasını oku:** `lsh` (yakın ve kaçış Jaccard'ı, teorik olasılıklar), `paket` (`paketli_tek_logit_fark`, `maskesiz_tek_logit_fark`), `suzgec`. Soru 1: Kaçış kopyalarının Jaccard'ı neden 0.43'e düşüyor ve bant/satır ayarını nasıl değiştirirsen yakalarsın, bunun bedeli ne olur? Soru 2: Maskesiz paketlemede 2. belgenin ilk tokenı neyi görüyor? Soru 3: Enjeksiyonlar neden zararsızlardan daha sık süzgeci geçiyor?
:::

::: gorev Gerçek deney · Gerçek paragraflarda LSH, SmolLM2'de packing maskesi ve enjeksiyon verisinde kalite süzgeci
Önceki görevlerdeki `lsh_tekillestir`, `belge_paketle`, `kalite_suzgeci` işlevlerini buraya birleştir (çözümlerini kopyalayabilirsin). Çalıştır gerçek ölçüm tablosunu gösterir; Kontrol Et önce işlevlerini gizli verilerle ve farksal taramayla sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
timeout: 240
```
```starter
import ai_lab
def lsh_tekillestir(belgeler, bant_sayisi, satir_sayisi):
    return {'korunan_indeksler': list(range(len(belgeler))), 'elenen_indeksler': [], 'korunan_belgeler': list(belgeler)}

def belge_paketle(token_dizileri, baglam_boyutu, eos_id):
    paket = [eos_id] * baglam_boyutu
    doc_ids = [0] * baglam_boyutu
    maske = [[1 if j <= i else 0 for j in range(baglam_boyutu)] for i in range(baglam_boyutu)]
    return {'paketlenmis_tokenlar': paket, 'doc_ids': doc_ids, 'maske': maske, 'aktif_dikkat_sayisi': sum((sum(satir) for satir in maske))}

def kalite_suzgeci(metin, min_kelime=50, maks_kelime=100000, durak_kelimeleri=('the', 'be', 'to', 'of', 'and', 'that', 'have', 'with')):
    n = len(metin.split())
    ihlal = [] if min_kelime <= n <= maks_kelime else ['kelime_sayisi']
    return {'gecti': not ihlal, 'ihlaller': ihlal, 'olcumler': {'kelime_sayisi': n}}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_06 as D
    D.goster(lsh_tekillestir, belge_paketle, kalite_suzgeci)
```
```test
import ai_lab
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('_jaccard', 'dil_modeli', 'kanit_yaz'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
lsh_tekillestir = need("lsh_tekillestir")
belge_paketle = need("belge_paketle")
kalite_suzgeci = need("kalite_suzgeci")
# farksal tarama (görev çözümlerinden derlenen referans)
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile('def lsh_tekillestir(belgeler, bant_sayisi, satir_sayisi):\n    m = bant_sayisi * satir_sayisi\n    kovalar = [set() for _ in range(bant_sayisi)]\n    korunan_indeksler = []\n    elenen_indeksler = []\n    korunan_belgeler = []\n    for idx, belge in enumerate(belgeler):\n        kelimeler = belge.lower().split()\n        if len(kelimeler) >= 2:\n            shingles = {\' \'.join(kelimeler[i:i + 2]) for i in range(len(kelimeler) - 1)}\n        elif len(kelimeler) == 1:\n            shingles = {kelimeler[0]}\n        else:\n            shingles = {\'\'}\n        x_degerleri = [sum(((i + 1) * ord(ch) for i, ch in enumerate(s))) for s in shingles]\n        imza = [min((((2 * k + 3) * x + (5 * k + 7)) % 10007 for x in x_degerleri)) for k in range(m)]\n        bantlar = [tuple(imza[bi * satir_sayisi:(bi + 1) * satir_sayisi]) for bi in range(bant_sayisi)]\n        if any((bantlar[bi] in kovalar[bi] for bi in range(bant_sayisi))):\n            elenen_indeksler.append(idx)\n        else:\n            korunan_indeksler.append(idx)\n            korunan_belgeler.append(belge)\n            for bi in range(bant_sayisi):\n                kovalar[bi].add(bantlar[bi])\n    return {\'korunan_indeksler\': korunan_indeksler, \'elenen_indeksler\': elenen_indeksler, \'korunan_belgeler\': korunan_belgeler}\n\ndef belge_paketle(token_dizileri, baglam_boyutu, eos_id):\n    toks = []\n    dids = []\n    doc_no = 0\n    for dizi in token_dizileri:\n        if not dizi:\n            continue\n        for t in dizi:\n            toks.append(t)\n            dids.append(doc_no)\n        toks.append(eos_id)\n        dids.append(doc_no)\n        doc_no += 1\n    while len(toks) < baglam_boyutu:\n        toks.append(eos_id)\n        dids.append(-1)\n    toks = toks[:baglam_boyutu]\n    dids = dids[:baglam_boyutu]\n    maske = [[1 if j <= i and dids[i] == dids[j] and (dids[i] != -1) else 0 for j in range(baglam_boyutu)] for i in range(baglam_boyutu)]\n    aktif = sum((sum(satir) for satir in maske))\n    return {\'paketlenmis_tokenlar\': toks, \'doc_ids\': dids, \'maske\': maske, \'aktif_dikkat_sayisi\': aktif}\n\ndef kalite_suzgeci(metin, min_kelime=50, maks_kelime=100000, durak_kelimeleri=(\'the\', \'be\', \'to\', \'of\', \'and\', \'that\', \'have\', \'with\')):\n    if not isinstance(metin, str):\n        raise ValueError(\'metin str olmalı\')\n    for v in (min_kelime, maks_kelime):\n        if isinstance(v, bool) or not isinstance(v, int) or v < 0:\n            raise ValueError(\'kelime sınırları negatif olmayan tam sayı olmalı\')\n    if min_kelime > maks_kelime:\n        raise ValueError(\'min_kelime <= maks_kelime olmalı\')\n    kelimeler = metin.split()\n    n = len(kelimeler)\n    satirlar = [s for s in metin.splitlines() if s.strip()]\n    ns = len(satirlar)\n    ort = sum((len(w) for w in kelimeler)) / n if n else 0.0\n    hash_o = metin.count(\'#\') / n if n else 0.0\n    uc_o = (metin.count(\'...\') + metin.count(\'…\')) / n if n else 0.0\n    madde = sum((1 for s in satirlar if s.lstrip().startswith((\'•\', \'-\', \'*\')))) / ns if ns else 0.0\n    uc_satir = sum((1 for s in satirlar if s.rstrip().endswith((\'...\', \'…\')))) / ns if ns else 0.0\n    alfa = sum((1 for w in kelimeler if any((ch.isalpha() for ch in w)))) / n if n else 0.0\n    durak = len({w.lower().strip(\'.,;:!?"\\\'()\') for w in kelimeler} & set(durak_kelimeleri))\n    ihlal = []\n    if not min_kelime <= n <= maks_kelime:\n        ihlal.append(\'kelime_sayisi\')\n    if not 3 <= ort <= 10:\n        ihlal.append(\'ortalama_kelime_uzunlugu\')\n    if hash_o > 0.1 or uc_o > 0.1:\n        ihlal.append(\'sembol_orani\')\n    if madde > 0.9:\n        ihlal.append(\'madde_isareti\')\n    if uc_satir > 0.3:\n        ihlal.append(\'uc_nokta_satir\')\n    if alfa < 0.8:\n        ihlal.append(\'alfabetik\')\n    if durak < 2:\n        ihlal.append(\'durak_kelime\')\n    return {\'gecti\': not ihlal, \'ihlaller\': ihlal, \'olcumler\': {\'kelime_sayisi\': n, \'ortalama_kelime_uzunlugu\': round(ort, 4), \'hash_orani\': round(hash_o, 4), \'uc_nokta_orani\': round(uc_o, 4), \'madde_satir_orani\': round(madde, 4), \'uc_nokta_satir_orani\': round(uc_satir, 4), \'alfabetik_orani\': round(alfa, 4), \'durak_kelime_sayisi\': durak}}', 'referans', 'exec'), _REF)
_t, _g = _ff(lsh_tekillestir, _REF['lsh_tekillestir'], (['derin ogrenme modellerinde dikkat mekanizmasi cok onemlidir', 'derin ogrenme modellerinde dikkat mekanizmasi cok faydalidir', 'kuantum bilgisayarlar superpozisyon ve dolaniklik kullanir'], 4, 2), tohum=2674, en_cok=600, mod='gecerli', butce='oto', ekler=[(['derin ogrenme', 'derin ogrenme', 'kuantum bilgisayar'], 4, 2, )])
kontrol(_t, "farksal tarama (lsh_tekillestir): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(belge_paketle, _REF['belge_paketle'], ([[101, 102], [201]], 5, 999), tohum=2404, en_cok=600, mod='gecerli', butce='oto', ekler=[([[101, 102], [201]], 6, 999, ), ([[1]], 4, 0, )])
kontrol(_t, "farksal tarama (belge_paketle): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(kalite_suzgeci, _REF['kalite_suzgeci'], ('- the a\n- to b\n* and c', 1, 100000, ('the', 'be', 'to', 'of', 'and', 'that', 'have', 'with')), tohum=2547, en_cok=600, mod='tam', butce='oto')
kontrol(_t, "farksal tarama (kalite_suzgeci): görev çözümüyle aynı sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
for _args, _bek in [
    ([['tek', 'tek', 'farkli'], 2, 2], _REF['lsh_tekillestir'](['tek', 'tek', 'farkli'], 2, 2)),
    ([['', ' ', 'word'], 1, 1], {'korunan_indeksler': [0, 2], 'elenen_indeksler': [1], 'korunan_belgeler': ['', 'word']}),
    ([['am baioa kaeüekfmnşingi ahcoemebllamek fibkkfe', 'am baioa jjomi iogimşcjdcübmjm', 'kaeüekfmnşingi ahcoemebllamek fibkkfe jjomi iogimşcjdcübmjm'], 2, 2], {'korunan_indeksler': [0, 1, 2], 'elenen_indeksler': [], 'korunan_belgeler': ['am baioa kaeüekfmnşingi ahcoemebllamek fibkkfe', 'am baioa jjomi iogimşcjdcübmjm', 'kaeüekfmnşingi ahcoemebllamek fibkkfe jjomi iogimşcjdcübmjm']}),
    ([['hdkgngnkcdgünh od odilşankbaüid jlbcjflfghmşüj nkblmboookeş', 'hdkgngnkcdgünh od odilşankbaüid jlbcjflfghmşüj fnhjhügojogükü edciilfdedifaşüfehel', 'odilşankbaüid jlbcjflfghmşüj nkblmboookeş fnhjhügojogükü edciilfdedifaşüfehel'], 1, 1], {'korunan_indeksler': [0, 2], 'elenen_indeksler': [1], 'korunan_belgeler': ['hdkgngnkcdgünh od odilşankbaüid jlbcjflfghmşüj nkblmboookeş', 'odilşankbaüid jlbcjflfghmşüj nkblmboookeş fnhjhügojogükü edciilfdedifaşüfehel']}),
    ([['doiamkcalünküeehjm igdlgjiimijflnjcme şmahcomjjnkşiblmik ln güşübbmhjnmdş', 'doiamkcalünküeehjm igdlgjiimijflnjcme kşşdikdjicjc şüghgjkbg', 'şmahcomjjnkşiblmik ln güşübbmhjnmdş kşşdikdjicjc şüghgjkbg'], 4, 3], {'korunan_indeksler': [0, 1], 'elenen_indeksler': [2], 'korunan_belgeler': ['doiamkcalünküeehjm igdlgjiimijflnjcme şmahcomjjnkşiblmik ln güşübbmhjnmdş', 'doiamkcalünküeehjm igdlgjiimijflnjcme kşşdikdjicjc şüghgjkbg']}),
    ([['ejclüügfjfooc hbhim koknd doocmjoüboeljaül iaecfllkjobmgijgjişe', 'ejclüügfjfooc hbhim hi übimalnofakükaüjş', 'koknd doocmjoüboeljaül iaecfllkjobmgijgjişe hi übimalnofakükaüjş'], 2, 1], {'korunan_indeksler': [0, 1, 2], 'elenen_indeksler': [], 'korunan_belgeler': ['ejclüügfjfooc hbhim koknd doocmjoüboeljaül iaecfllkjobmgijgjişe', 'ejclüügfjfooc hbhim hi übimalnofakükaüjş', 'koknd doocmjoüboeljaül iaecfllkjobmgijgjişe hi übimalnofakükaüjş']}),
    ([['cdbmlcadinje fncfşennblnb oüdojüücninfükcd md jjlmişnşüffdnkiaoüa', 'cdbmlcadinje fncfşennblnb oüdojüücninfükcd md fşeükeşşdhdeffbfşoü combückceji', 'oüdojüücninfükcd md jjlmişnşüffdnkiaoüa fşeükeşşdhdeffbfşoü combückceji'], 4, 3], {'korunan_indeksler': [0, 1], 'elenen_indeksler': [2], 'korunan_belgeler': ['cdbmlcadinje fncfşennblnb oüdojüücninfükcd md jjlmişnşüffdnkiaoüa', 'cdbmlcadinje fncfşennblnb oüdojüücninfükcd md fşeükeşşdhdeffbfşoü combückceji']}),
    ([['oşocllbülmijeojünjü gkhmghdü nib adhiükohcajşfge hcnjohankbncükoüngm', 'oşocllbülmijeojünjü gkhmghdü nib leaeeaüehd iiobincnoghüeüi', 'nib adhiükohcajşfge hcnjohankbncükoüngm leaeeaüehd iiobincnoghüeüi'], 2, 3], {'korunan_indeksler': [0, 1, 2], 'elenen_indeksler': [], 'korunan_belgeler': ['oşocllbülmijeojünjü gkhmghdü nib adhiükohcajşfge hcnjohankbncükoüngm', 'oşocllbülmijeojünjü gkhmghdü nib leaeeaüehd iiobincnoghüeüi', 'nib adhiükohcajşfge hcnjohankbncükoüngm leaeeaüehd iiobincnoghüeüi']}),
    ([['ehinoülemf jmkjüooügş dhljblbchmeşşfa d nüfclkmdelkj', 'ehinoülemf jmkjüooügş dhljblbchmeşşfa n kkedşfaekişjo', 'dhljblbchmeşşfa d nüfclkmdelkj n kkedşfaekişjo'], 4, 3], {'korunan_indeksler': [0, 1], 'elenen_indeksler': [2], 'korunan_belgeler': ['ehinoülemf jmkjüooügş dhljblbchmeşşfa d nüfclkmdelkj', 'ehinoülemf jmkjüooügş dhljblbchmeşşfa n kkedşfaekişjo']}),
    ([['şbgmg şn boicebhdg daşld üşijkjfeeb', 'şbgmg şn boicebhdg şjneoüjgfohfodeüjkş bokjadekgeccokn', 'boicebhdg daşld üşijkjfeeb şjneoüjgfohfodeüjkş bokjadekgeccokn'], 2, 1], {'korunan_indeksler': [0, 1], 'elenen_indeksler': [2], 'korunan_belgeler': ['şbgmg şn boicebhdg daşld üşijkjfeeb', 'şbgmg şn boicebhdg şjneoüjgfohfodeüjkş bokjadekgeccokn']}),
    ([['liişşeşmicahüedbelhh n ddci aehdnkdndşa mooniko', 'liişşeşmicahüedbelhh n ddci aehdnkdndşa bdecjggdşgdkohfhigjo obbbemeoüeüg', 'ddci aehdnkdndşa mooniko bdecjggdşgdkohfhigjo obbbemeoüeüg'], 4, 3], {'korunan_indeksler': [0, 2], 'elenen_indeksler': [1], 'korunan_belgeler': ['liişşeşmicahüedbelhh n ddci aehdnkdndşa mooniko', 'ddci aehdnkdndşa mooniko bdecjggdşgdkohfhigjo obbbemeoüeüg']}),
]:
    kontrol(lsh_tekillestir(_args[0], _args[1], _args[2]) == _bek, "LSH shingle ve hash katsayısı sözleşmesi")
kontrol(belge_paketle([[1, 2], [], [3]], 7, 99) == _REF['belge_paketle']([[1, 2], [], [3]], 7, 99), "boş dizi atlama ve paketleme sözleşmesi")
def _ks_birim():
    if kalite_suzgeci("", min_kelime=0)["ihlaller"] != ["ortalama_kelime_uzunlugu", "alfabetik", "durak_kelime"]:
        return False
    if kalite_suzgeci("the cat waits...\nand that dog…\nwith a bird", min_kelime=1) != _REF['kalite_suzgeci']("the cat waits...\nand that dog…\nwith a bird", min_kelime=1):
        return False
    if kalite_suzgeci("#the and cat cat cat cat cat", 0)["olcumler"]["hash_orani"] != 0.1429:
        return False
    if kalite_suzgeci("- the and\nthe and\nthe and", 0)["olcumler"]["madde_satir_orani"] != 0.3333:
        return False
    for _n, _bek in ((49, False), (50, True), (51, True), (100000, True), (100001, False)):
        if kalite_suzgeci(" ".join(["the", "and"] + ["cat"] * (_n - 2)))["gecti"] != _bek:
            return False
    for _m, _d, _ih in (("aaa bbb", ("aaa", "bbb"), False), ("aa bbb", ("aa", "bbb"), True), ("abcdefghij klmnopqrst", ("abcdefghij", "klmnopqrst"), False), ("abcdefghijk klmnopqrst", ("abcdefghijk", "klmnopqrst"), True)):
        if ("ortalama_kelime_uzunlugu" in kalite_suzgeci(_m, 0, 100, _d)["ihlaller"]) != _ih:
            return False
    for _is in ("#", "...", "…"):
        for _n, _ih in ((10, False), (9, True), (11, False)):
            if ("sembol_orani" in kalite_suzgeci(" ".join(["the" + _is + "x", "and"] + ["cat"] * (_n - 2)), 0)["ihlaller"]) != _ih:
                return False
    for _s, _ih in ((9, False), (10, True)):
        if ("madde_isareti" in kalite_suzgeci("\n".join(["- the and cat"] * _s + ["the and cat"] * (10 - _s)), 0)["ihlaller"]) != _ih:
            return False
    for _s, _ih in ((3, False), (4, True)):
        if ("uc_nokta_satir" in kalite_suzgeci("\n".join(["the and cat..."] * _s + ["the and cat"] * (10 - _s)), 0)["ihlaller"]) != _ih:
            return False
    for _s, _ih in ((8, False), (7, True)):
        if ("alfabetik" in kalite_suzgeci(" ".join(["the", "and"] + ["cat"] * (_s - 2) + ["123"] * (10 - _s)), 0)["ihlaller"]) != _ih:
            return False
    if ("durak_kelime" in kalite_suzgeci("the cat cat", 0)["ihlaller"]) is not True or ("durak_kelime" in kalite_suzgeci("the and cat", 0)["ihlaller"]) is not False:
        return False
    return True
kontrol(_ks_birim(), "kalite_suzgeci Gopher eşik ve yuvarlama sözleşmesi")
if not all(checks): stop()
from sandbox import ai_gercek_ai_uretim_06 as D
try: r = D.deney(lsh_tekillestir, belge_paketle, kalite_suzgeci)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r['lsh_yakin_orani'] >= 0.9, "gerçek paragrafların tek kelimelik yakın kopyalarının en az %90'ı elendi")
kontrol(r['paket']['maske_dogru'] and r['paket_izole'], "senin maskenle paketlenen belgeler SmolLM2'de tek başına çalıştırılmış gibi (logit farkı < 1e-3)")
kontrol(r['maskesiz_sizar'], 'maskesiz packing belgeler arası sızıntı üretiyor (logit farkı > 0.1)')
kontrol(r['suzgec']['enjeksiyon_gecen'] > 0, 'kalite süzgeci gerçek enjeksiyon metinlerini ayıklamıyor (en az biri geçti)')
ai_lab.kanit_yaz("ai-uretim-06-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-uretim-06", "deney": r})
```
```solution
import ai_lab
def lsh_tekillestir(belgeler, bant_sayisi, satir_sayisi):
    m = bant_sayisi * satir_sayisi
    kovalar = [set() for _ in range(bant_sayisi)]
    korunan_indeksler = []
    elenen_indeksler = []
    korunan_belgeler = []
    for idx, belge in enumerate(belgeler):
        kelimeler = belge.lower().split()
        if len(kelimeler) >= 2:
            shingles = {' '.join(kelimeler[i:i + 2]) for i in range(len(kelimeler) - 1)}
        elif len(kelimeler) == 1:
            shingles = {kelimeler[0]}
        else:
            shingles = {''}
        x_degerleri = [sum(((i + 1) * ord(ch) for i, ch in enumerate(s))) for s in shingles]
        imza = [min((((2 * k + 3) * x + (5 * k + 7)) % 10007 for x in x_degerleri)) for k in range(m)]
        bantlar = [tuple(imza[bi * satir_sayisi:(bi + 1) * satir_sayisi]) for bi in range(bant_sayisi)]
        if any((bantlar[bi] in kovalar[bi] for bi in range(bant_sayisi))):
            elenen_indeksler.append(idx)
        else:
            korunan_indeksler.append(idx)
            korunan_belgeler.append(belge)
            for bi in range(bant_sayisi):
                kovalar[bi].add(bantlar[bi])
    return {'korunan_indeksler': korunan_indeksler, 'elenen_indeksler': elenen_indeksler, 'korunan_belgeler': korunan_belgeler}

def belge_paketle(token_dizileri, baglam_boyutu, eos_id):
    toks = []
    dids = []
    doc_no = 0
    for dizi in token_dizileri:
        if not dizi:
            continue
        for t in dizi:
            toks.append(t)
            dids.append(doc_no)
        toks.append(eos_id)
        dids.append(doc_no)
        doc_no += 1
    while len(toks) < baglam_boyutu:
        toks.append(eos_id)
        dids.append(-1)
    toks = toks[:baglam_boyutu]
    dids = dids[:baglam_boyutu]
    maske = [[1 if j <= i and dids[i] == dids[j] and (dids[i] != -1) else 0 for j in range(baglam_boyutu)] for i in range(baglam_boyutu)]
    aktif = sum((sum(satir) for satir in maske))
    return {'paketlenmis_tokenlar': toks, 'doc_ids': dids, 'maske': maske, 'aktif_dikkat_sayisi': aktif}

def kalite_suzgeci(metin, min_kelime=50, maks_kelime=100000, durak_kelimeleri=('the', 'be', 'to', 'of', 'and', 'that', 'have', 'with')):
    if not isinstance(metin, str):
        raise ValueError('metin str olmalı')
    for v in (min_kelime, maks_kelime):
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            raise ValueError('kelime sınırları negatif olmayan tam sayı olmalı')
    if min_kelime > maks_kelime:
        raise ValueError('min_kelime <= maks_kelime olmalı')
    kelimeler = metin.split()
    n = len(kelimeler)
    satirlar = [s for s in metin.splitlines() if s.strip()]
    ns = len(satirlar)
    ort = sum((len(w) for w in kelimeler)) / n if n else 0.0
    hash_o = metin.count('#') / n if n else 0.0
    uc_o = (metin.count('...') + metin.count('…')) / n if n else 0.0
    madde = sum((1 for s in satirlar if s.lstrip().startswith(('•', '-', '*')))) / ns if ns else 0.0
    uc_satir = sum((1 for s in satirlar if s.rstrip().endswith(('...', '…')))) / ns if ns else 0.0
    alfa = sum((1 for w in kelimeler if any((ch.isalpha() for ch in w)))) / n if n else 0.0
    durak = len({w.lower().strip('.,;:!?"\'()') for w in kelimeler} & set(durak_kelimeleri))
    ihlal = []
    if not min_kelime <= n <= maks_kelime:
        ihlal.append('kelime_sayisi')
    if not 3 <= ort <= 10:
        ihlal.append('ortalama_kelime_uzunlugu')
    if hash_o > 0.1 or uc_o > 0.1:
        ihlal.append('sembol_orani')
    if madde > 0.9:
        ihlal.append('madde_isareti')
    if uc_satir > 0.3:
        ihlal.append('uc_nokta_satir')
    if alfa < 0.8:
        ihlal.append('alfabetik')
    if durak < 2:
        ihlal.append('durak_kelime')
    return {'gecti': not ihlal, 'ihlaller': ihlal, 'olcumler': {'kelime_sayisi': n, 'ortalama_kelime_uzunlugu': round(ort, 4), 'hash_orani': round(hash_o, 4), 'uc_nokta_orani': round(uc_o, 4), 'madde_satir_orani': round(madde, 4), 'uc_nokta_satir_orani': round(uc_satir, 4), 'alfabetik_orani': round(alfa, 4), 'durak_kelime_sayisi': durak}}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_uretim_06 as D
    D.goster(lsh_tekillestir, belge_paketle, kalite_suzgeci)
```
```hint
Üç görevin çözümlerini olduğu gibi buraya koy. Deney paragrafları, tokenizer'ı ve veri kümesini kendisi hazırlar.
```
:::

::: anlat Sınır
Görevler shingle, MinHash ve LSH bantlamasıyla tekilleştirmeyi, document packing'i ve belge içi attention maskesini saf Python ile yazdırır; final adım bunları gerçek ders paragraflarında, SmolLM2'de ve deepset/prompt-injections verisinde ölçer. MinHash'in Jaccard tahmini imza uzunluğuna bağlı olarak gürültülüdür; LSH bant/satır seçimi yanlış pozitif ile yanlış negatif dengesini belirler ve eşiğin hemen altındaki yakın kopyalar kaçar. Tekilleştirme kalite filtresi değildir (kalite süzgeci ayrı bir kural tabanlı görevdir ve durak kelimeleri İngilizce varsayılanla tanımlıdır; model tabanlı kalite sınıflandırıcısı yoktur) ve küçük değişikliklerle hazırlanmış zehirli belgeleri yakalamaz. Belge içi maske olmadan packing, bir belgenin diğerinin bağlamına sızmasına yol açar.

Kaynaklar: [Lee vd. 2021 - Deduplicating Training Data Makes Language Models Better](https://arxiv.org/abs/2107.06499), [Krell vd. 2021 - Efficient Sequence Packing without Cross-contamination](https://arxiv.org/abs/2107.02027), [Penedo vd. 2024 - The FineWeb Datasets: Decanting the Web for the Finest Text Data at Scale](https://arxiv.org/abs/2406.17557).
:::

::: dusun
Sahnede bir veri bilimcisi sana şunu sordu:
*"Hocam, modelimizi eğittikten sonra `MMLU`, `GSM8K` ve `HumanEval` gibi uluslararası sınavlarda (`Benchmarks`) `%95` başarı aldığını gördük ve çok sevindik. Ama gerçek kullanıcılar modele yeni bir soru sorduğunda model çuvallıyor! Veri rafinerisinde hangi kritik adımı atlamış olabiliriz?"*

Bu soruya **`Benchmark Contamination / Data Leakage` (Sınav Sorularının Eğitim Verisine Sızması)**, **`N-gram Decontamination` (13-gram / MinHash ile sınav sorularını eğitim verisinden kazıma)** ve **`Goodhart's Law`** kavramlarını kullanarak nasıl yanıt verirsin?
:::

::: ozet
- **`Trillion-Token Data Refinery`**, ham `CommonCrawl` verisine seçme, tekilleştirme ve kalite kuralları uygulayarak `FineWeb-Edu` gibi yüksek yoğunluklu eğitim kümeleri üretir.
- **`MinHash LSH Deduplication`**, metinleri $n$-gram **`Shingle`** kümelerine ayırır, $M$ adet özet fonksiyonunun minimumlarıyla **`MinHash Signature`** üretir ($P(\text{Sig}_k(A)=\text{Sig}_k(B)) = J(A,B)$) ve **`LSH Banding`** ($1 - (1 - s^r)^b$) ile bütün belge çiftlerini taramadan aday bulur. Olasılık formülleri ideal bağımsız hash varsayımına dayanır; aday doğrulama maliyeti kova yoğunluğuyla büyüyebilir.
- **`Sequence Packing`**, farklı uzunluktaki belgeleri `<|eos|>` ile birleştirip sabit bağlam pencerelerine ($L$) keserek tam dolu pencerelerde dolgu (`Padding`) israfını azaltır; **`Cross-Document Attention Mask`** (`j <= i` ve `doc_id[i] == doc_id[j]`) ise aynı paketteki farklı belgelerin birbirinden bağlam çalmasını (`Cross-Document Contamination`) engeller.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
İki belgeyi 2-gram kümelerine çevir ve Jaccard kesişim/birleşimini göster. İdeal rastgele permütasyonda minimumun kesişime düşme olasılığından MinHash bağıntısını türet; görevdeki sabit hash ailesinin ideal model olmadığını belirt. Bant eşleşmesini kesin kopya kararı sanma: aday doğrulama ve yanlış eleme ayrı konudur. Sonra iki belgeyi EOS ile paketle; aynı belge ve j<=i şartlarının kesişiminden attention maskesini çiz. Kalite süzgecinde eşit eşiklerin hangi tarafta olduğunu ve oranların karardan sonra yuvarlandığını göster. Son soru: “Akıcı bir prompt injection metni kalite kurallarını geçerse neden yine güvenli sayılmaz?”
:::
