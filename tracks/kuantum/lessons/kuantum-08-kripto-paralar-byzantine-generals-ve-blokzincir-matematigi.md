---
id: kuantum-08
title: "Kripto Paralar ve Blockchain Matematiği: Neden Kaybolmaz, Değerini Nereden Alır?"
track: kuantum
order: 8
duration_minutes: 35
difficulty: ileri
xp: 300
prerequisites: [kuantum-07]
tags: [cryptocurrency, blockchain, byzantine-generals, proof-of-work, digital-scarcity, smart-contracts]
summary: "Bizans Generalleri problemini, çift harcama önlemini, satoshi tam sayılarıyla yarılanma arzını ve iş kanıtı (Proof-of-Work) zorluk-enerji dengesini hesapla."
esleme: kuantum-16, kuantum-20
---

::: anlat
## Konferans Sorusu: "İnternetteki Bir Sayı Nasıl Milyarlarca Dolar Eder ve Neden Kaybolmaz?"

Sahnede teknoloji, kriptografi ve geleceğin sistemlerini anlatırken dinleyicilerden mutlaka şu şüpheci soru gelir:
> *"Hocam, Bitcoin veya kripto paralar dediğiniz şey nihayetinde internetteki bir bilgisayar dosyası, ekrandaki bir sayı değil mi? Arkasında devlet yok, altın yok, fabrika yok. Nasıl bu kadar değerli olabiliyor? Madenciler nasıl kâra geçiyor? Ve neden bunun bir balon olup tamamen yok olmayacağını söylüyorlar?"*

Bu soruyu "çünkü insanlar alıyor" gibi yüzeysel bir cümleyle geçiştiremezsin. Bu sorunun cevabı **Para Felsefesi (Monetary Theory)**, **Dağıtık Sistemler Bilimi (Distributed Systems)**, **Termodinamik Yasaları** ve **Kriptografi**'nin kesişim noktasında yatar. Gel, herkesi hayran bırakacak netlikte parçalara ayıralım.

---

### 1. "Sadece İnternetteki Bir Sayı Değil mi?" — Paranın Evrimi ve Digital Scarcity

Önce karşındaki kişiye şu karşı soruyu sor:
> *"Cebinizdeki 200 TL veya 100 Dolar kağıdının kendisi mi değerli? Ya da banka mobil uygulamanıza girdiğinizde ekranda gördüğünüz `50.000 TL` yazısı, bankanın SQL veritabanındaki bir sayıdan başka nedir?"*

**Aristoteles** paranın dayanıklı, taşınabilir, bölünebilir ve kendi başına değerli olması gerektiğini yazmıştı. İktisat ders kitapları paranın üç **işlevini** sayar (değişim aracı, hesap birimi, değer saklama) ve iyi bir paranın şu özelliklerini tartışır; ilk beşi yaygın kabul görür, altıncısını özellikle kripto savunucuları ekler:
1. **Scarcity (Kıtlık / Arz Sınırı):** Kolayca kopyalanamamalı veya sınırsız üretilememeli.
2. **Durability (Dayanıklılık):** Çürümemeli, yok olmamalı.
3. **Portability (Taşınabilirlik):** Dünyanın öbür ucuna kolayca gönderilebilmeli.
4. **Divisibility (Bölünebilirlik):** Küçük kuruşlara bölünebilmeli.
5. **Verifiability (Doğrulanabilirlik):** Sahte olup olmadığı kolayca anlaşılmalı.
6. **Censorship Resistance (Sansür Direnci / Egemenlik):** Kimse keyfi olarak el koyamamalı.

Binlerce yıl boyunca **Altın (Gold)** 1. ve 2. maddede (Kıtlık ve Dayanıklılık) mükemmeldi çünkü kimyada altın atomunu (Atom numarası 79) laboratuvarda ucuza üretemezsin; doğadan çıkarmak için devasa enerji harcaman gerekir. Ama altını internetten 5 saniyede Japonya'ya gönderemezsin (**Portability** zayıf).

Devletlerin bastığı **Fiat Money (İtibari Para — Dolar, TL, Euro)** dijital olarak kolay taşınır ve arzı **sabit değil, yönetilir**: merkez bankaları para arzını genişletip daraltabilir. Burada iki görüş vardır:
- **Kripto savunucuları:** arzın esnekliği bir zayıflıktır; aşırı para basımı (**Money Printing / Inflation**) biriktirilen emeğin satın alma gücünü eritir (yüksek enflasyon dönemleri örnek gösterilir).
- **Ana akım iktisat:** esneklik bilinçli bir tasarımdır; kriz anında likidite sağlamak, durgunlukta faizi düşürmek ve ılımlı bir enflasyon hedeflemek için gerekir. Arzı sabit bir para, ekonomi büyüdükçe deflasyon baskısı yaratır ve bu da borçluları ve yatırımı zorlar. Fiat paranın değeri de boşlukta durmaz: vergilerin o parayla ödenmesi zorunluluğu ve kurumlara güven onu destekler.

#### Dijital Dünyanın En Büyük Problemi: Double-Spending Problem (Çifte Harcama)
2008 yılına kadar bilgisayar bilimlerinde çözülemeyen temel bir imkansızlık vardı:
- Dijital dünyadaki her şey (bir `.mp3` şarkısı, bir `.jpg` fotoğrafı, bir `.pdf` dosyası) `Ctrl+C` ve `Ctrl+V` ile **sıfır maliyetle kopyalanabilir**.
- Sana dijital ortamda `1 Dijital Altın` dosyasını gönderdiğimde, aynı dosyayı kopyalayıp aynı anda 10 kişiye daha göndermemi (**Double-Spending Problem**) bir **merkezi hakem (Banka / PayPal / Devlet)** olmadan nasıl engelleyebiliriz?

---

### 2. Byzantine Generals Problem ve Satoshi Nakamoto'nun Dehası (2008)

Bilgisayar bilimlerinde 1982'de **Leslie Lamport** tarafından tanımlanan meşhur **Byzantine Generals Problem (Bizans Generalleri Problemi)** şunu sorar:
> *"Birbirine güvenmeyen, aralarında hainlerin ve sahtekarların olabileceği binlerce bilgisayar düğümü (**Node**), başlarında bir kral veya merkez bankası olmadan, **tek bir ortak gerçek (Single Source of Truth / Ledger)** üzerinde nasıl %100 uzlaşabilir (**Consensus**)?"*

2008'de **Satoshi Nakamoto** takma adlı kişi (veya grup), **Bitcoin Whitepaper**'ı yayınlayarak tarihte ilk kez **merkezi bir otorite olmadan Digital Scarcity (Dijital Kıtlık)** yaratmayı başardı. Bunu 3 matematiksel direk üzerine kurdu:

```
┌────────────────────────────────────────────────────────────────────────────┐
│           NEDEN "SADECE BİR İNTERNET SAYISI" DEĞİLDİR? (3 DİREK)           │
├────────────────────────┬─────────────────────────┬─────────────────────────┤
│ 1. CRYPTOGRAPHIC       │ 2. THERMODYNAMIC        │ 3. MATHEMATICAL         │
│    OWNERSHIP           │    PROOF-OF-WORK (PoW)  │    ABSOLUTE SCARCITY    │
│ ────────────────────── │ ─────────────────────── │ ─────────────────────── │
│ • Digital Signature    │ • SHA-256 Hash Puzzle   │ • 21,000,000 Hard Cap   │
│   (ECDSA / secp256k1)  │ • Gerçek dünyadaki      │ • Her 210,000 blokta    │
│ • Private Key kimdeyse │   elektrik enerjisini   │   (~4 yılda bir)        │
│   mülkiyet ondadır;    │   dijital mühre         │   Halving (Yarılanma)   │
│   dünyadaki hiçbir     │   dönüştürür.           │ • Hiçbir başkan veya    │
│   devlet veya ordu     │ • Geçmişteki bir bloğu  │   merkez bankası        │
│   Private Key olmadan  │   değiştirmek için tüm  │   21.000.001'inci       │
│   o parayı harcayamaz. │   dünyadan daha fazla   │   Bitcoin'i basamaz!    │
│                        │   elektrik yakman şart! │                         │
└────────────────────────┴─────────────────────────┴─────────────────────────┘
```

#### Direk 1: Termodinamik Kanıt — Proof-of-Work (PoW)
Satoshi dedi ki: *"Eğer dijital bir kaydı değiştirmek bedava olursa herkes sahtekarlık yapar. Öyleyse dijital deftere (**Blockchain**) yeni bir sayfa (**Block**) eklemeyi, gerçek dünyadaki **Fizik ve Termodinamik Yasalarına (Elektrik Enerjisine)** bağlayalım!"*
- **Proof-of-Work (İş Kanıtı):** Madenci (**Miner**) dediğimiz özel işlemciler (**ASIC**), son 10 dakikadaki para transferlerini bir bloğa toplar, bir önceki bloğun **SHA-256 Hash** özetini ekler ve sonuna **Nonce** adı verilen rastgele bir sayı koyup özetini alır.
- Kural şudur: Üretilen 256-bitlik **SHA-256** çıktısının başında örneğin **en az 75 tane sıfır (`0000000...`)** olmak zorundadır!
- **SHA-256** tek yönlü (**One-Way Cryptographic Hash Function**) olduğu için, başında 75 sıfır olan çıktıyı bulmanın hiçbir kestirme formülü yoktur; saniyede trilyonlarca kez zar atıp (**Brute-Force Hash Rate**) elektrik harcamak zorundasındır!
- Teknik olarak kesin olan şudur: geçmiş bir bloğu değiştirmek, o bloktan sonra eklenen bütün işi yeniden yapmayı gerektirir; bu yüzden kaydı değiştirmenin maliyeti gerçek enerjiyle ölçülür. Savunucular bundan "Bitcoin enerjinin dijital mühre dönüşmüş hâlidir" (**Thermodynamic Sound Money**) sonucunu çıkarır. Eleştirmenler ise harcanan enerjinin kendiliğinden **değer** yaratmadığını (bir şeyi üretmek pahalı diye değerli olmaz), yalnız ağın **güvenlik bütçesi** olduğunu ve büyük bir çevresel maliyeti olduğunu söyler.

#### Direk 2: Mathematical Scarcity (21 Milyon Sınırı ve Halving)
Altının bile uzaydaki asteroitlerde milyarlarca ton karşılığı vardır. Bitcoin'in arz kuralı ise protokolün içine yazılmıştır (bir kural değişikliği ancak düğümlerin büyük çoğunluğu yeni yazılımı kabul ederse olur; topluluk bunu bugüne kadar reddetmiştir):
- İlk başladığında (2009) her 10 dakikada bir bulunan blok için sistem **50 BTC** ödül veriyordu.
- Kodun içine yazılmış değiştirilemez kurala göre her **210.000 blokta bir (yaklaşık 4 yılda bir)** bu üretim ödülü yarıya düşer (**Halving**): $50 \rightarrow 25 \rightarrow 12.5 \rightarrow 6.25 \rightarrow 3.125 \text{ BTC}$ (Nisan 2024 itibarıyla).
- Geometrik seri toplamı alındığında toplam arz **21.000.000 adedi geçemez**. Gerçek protokol ödülü kayan noktayla değil, en küçük birim olan **satoshi** ($10^{-8}$ BTC) cinsinden tam sayıyla hesaplar ve her yarılanmada aşağı yuvarlar (bit kaydırma). Bu yüzden toplam 21 milyonun biraz altında kalır:

$$\sum_{k=0}^{32} 210000 \times \left\lfloor \frac{50 \cdot 10^8}{2^k} \right\rfloor \text{ satoshi} = 2\,099\,999\,997\,690\,000 \text{ satoshi} = 20\,999\,999.9769 \text{ BTC}$$

Yuvarlamasız sürekli toplam $21\,000\,000 \times (1 - 2^{-33}) \approx 20\,999\,999.9976$ olurdu. 33. dönemden sonra ödül 0 satoshi'dir.

```python
# Bitcoin Halving (Yarılanma): kayan nokta yaklaşımı ile tam sayı satoshi hesabı
def toplam_arz_kayan(halving_sayisi=33):
    toplam, odul = 0.0, 50.0
    for _ in range(halving_sayisi):
        toplam += 210_000 * odul
        odul /= 2.0
    return toplam

def toplam_arz_satoshi(halving_sayisi=33):
    return sum(210_000 * ((50 * 10**8) >> k) for k in range(halving_sayisi))

print(f"Kayan nokta: {toplam_arz_kayan():,.4f} BTC | Satoshi: {toplam_arz_satoshi() / 10**8:,.4f} BTC")
```

---

### 3. "Sistem Nasıl Kâra Geçiyor? Madenciler Neden Bedavaya Çalışmıyor?"

Birisi *"Bu sistemi kim ayakta tutuyor ve nasıl para kazanıyorlar?"* diye sorduğunda **Incentive Mechanism (Oyun Teorisi ve Teşvik Mekanizması)** devreye girer:

1. **Madencilerin / Doğrulayıcıların Geliri (Miners & Validators):**
   - Ağı koruyan ve işlemleri onaylayan düğümler iki yerden gelir elde eder:
     1. **Block Subsidy (Blok Ödülü):** Protokolün her 10 dakikada bir sıfırdan ürettiği yeni coin'ler (şu an blok başına $3.125\text{ BTC}$).
     2. **Transaction Fees (İşlem Ücretleri):** Ağa para transferi gönderen kullanıcıların, işlemlerinin bloğa dahil edilmesi için ödediği küçük komisyonlar. 2140 yılında 21 milyon BTC'nin tamamı üretildiğinde madenciler tamamen bu **Transaction Fee** gelirleriyle çalışmaya devam edecektir.
2. **Difficulty Adjustment (Zorluk Ayarlaması — Sistemin Kendi Kendini Dengesi):**
   - Diyelim ki fiyat düştü ve madencilerin yarısı zarar ettiği için fişi çekti; sistem çöker mi? **Hayır!**
   - Protokol her **2016 blokta bir (~2 haftada bir)** blokların bulunma süresini ölçer. Eğer bloklar 10 dakikadan geç çıkıyorsa, bulmacanın zorluğunu (**Difficulty Target**) otomatik olarak düşürür; kalan madencilerin maliyeti azalır ve tekrar **kâra geçerler**! Eğer çok fazla madenci girerse zorluğu artırır. Bu otonom geri besleme döngüsü (**Homeostasis**) sayesinde ağ 2009'dan beri, 2010'daki taşma hatası (*value overflow incident*) ve 2013'teki kısa zincir ayrılması gibi birkaç olay dışında kesintisiz çalışmaktadır.

---

### 4. "Neden Hiçbir Zaman Kaybolmayacak ve Geleceğin Parası Olacak?"

Konferansta birisi *"Peki neden kripto paralar ve Blockchain yok olmayacak?"* dediğinde savunucuların öne sürdüğü şu **4 yapısal gerekçeyi** masaya koyabilirsin (bunlar kanıtlanmış sonuçlar değil, tartışmalı tezlerdir; karşı görüşleri de bilmen gerekir):

1. **Kapatma Düğmesi Yoktur (Decentralization & Anti-Fragility):**
   - Bir şirketi (örneğin Lehman Brothers'ı) iflas ettirebilirsin, bir web sitesinin sunucusunu kapatabilirsin. Ama Bitcoin ve Ethereum'un bir "Merkez Ofisi", bir "CEO'su" veya "Ana Sunucusu" yoktur!
   - Dünyanın 150 ülkesine yayılmış on binlerce bağımsız **Full Node** aynı defterin tam kopyasını tutar (Blockstream uyduları blokları uzaydan bile yayınlar). İnternetin tamamı dünyada yok olmadığı sürece tek bir bilgisayarda bile o **Ledger** kalsa ağ yaşamaya devam eder.
2. **Smart Contracts ve Programmable Money (Ethereum & DeFi Devrimi):**
   - **Vitalik Buterin**'in 2015'te başlattığı **Ethereum** ile Blockchain sadece "dijital altın" olmaktan çıkıp **Dünya Bilgisayarı (World Computer)** oldu.
   - **Smart Contract (Akıllı Sözleşme):** Notere, bankaya, avukata veya aracı kuruma ihtiyaç duymadan, *"Eğer X şartı gerçekleşirse Y parasını Z'ye otomatik öde"* kuralının koda yazılıp değiştirilemez şekilde çalışmasıdır.
   - Bugün **BlackRock**, **JPMorgan** ve merkez bankaları; hisse senetlerini, gayrimenkulleri ve tahvilleri **Real-World Asset Tokenization (RWA)** ile Blockchain üzerine taşımayı deniyor. Savunuculara göre Cuma akşamı kapanan, uluslararası havalesi (**SWIFT**) günler süren eski bankacılık mimarisi, 7/24 çalışan bir **Blockchain Settlement** katmanıyla rekabet edemeyecek (bu projelerin çoğunun izinli defterlerde yürüdüğünü aşağıda göreceksin).
3. **AI Agents (Yapay Zeka Ajanları) Ekonomisinin Doğal Parasıdır:**
   - Çok kritik bir vizyon: Gelecekte milyarlarca otonom **AI Agent**, başka bir **AI Agent**'tan API hizmeti, veri veya GPU gücü satın alacak.
   - Bir **AI Agent** bankada kendi adına hesap açamaz; ama bir anahtar çifti üretip bir kripto cüzdanıyla küçük ödemeler (**Micropayment**) yapabilir. Savunucular buradan kriptonun **AI ekonomisinin yerel parası** olacağı sonucunu çıkarır. Karşı görüş: ajanlar zaten sahiplerinin ödeme hesaplarına bağlı API anahtarları, ön ödemeli krediler ya da kartlar üzerinden ödeme yapıyor; kripto kullanılsa bile bunun büyük ihtimalle fiyatı dolara sabitlenmiş **stablecoin**'ler olacağı, yani "yerel para"nın yine itibari para olacağı söylenir.
4. **Kuantum Bilgisayarlar Kriptoyu Bitirecek mi? (Hard Fork & PQC Geçişi):**
   - Bir önceki derslerimizde öğrendiğin gibi: Büyük bir kuantum bilgisayar (**CRQC**), **Shor's Algorithm** ile mevcut **ECDSA (`secp256k1`)** imzalarını kırabilir ama **SHA-256 (Proof-of-Work)** yapısını **Grover's Algorithm** karşısında sadece zorluğu artırarak koruyabilir.
   - Peki imzalar ne olacak? Blockchain protokolleri **Hard Fork / Soft Fork** adı verilen yazılım güncellemeleriyle imza şemalarını **NIST Post-Quantum Cryptography (ML-DSA / Dilithium veya Lamport/SPHINCS+ Hash-Based Signatures)** algoritmalarına yükselttiğinde kuantum saldırılarına karşı dayanıklı hale gelir; ancak açık anahtarı zaten görünen ve sahibi tarafından taşınamayan coin'ler (kayıp anahtarlar, eski `P2PK` çıktıları) risk altında kalır (kuantum-20).

#### Karşı görüşler: neden "kesin kalıcı" denemez?
Yukarıdaki dört gerekçe savunucuların tezleridir. Konferansta dürüst olmak için şunları da söylemelisin:
- **Değer:** Bitcoin'in nakit akışı ya da kullanım değeri yoktur; fiyatı tamamen talebe bağlıdır ve tarihsel olarak birkaç kez %70–80 düşmüştür. Değer saklama tezi henüz kısa (15 yıllık) bir geçmişe dayanır.
- **Ölçeklenme ve kullanım:** Bitcoin ana zinciri saniyede yalnız birkaç işlem işler; günlük ödemelerin çoğu ikinci katmanlara, borsalara ya da stablecoin'lere kayar ve bunlar yeniden aracı ve güven gerektirir.
- **Gerçek kayıplar:** 2022'de Terra/Luna'nın çöküşü ve FTX'in iflası milyarlarca dolarlık kayba yol açtı; akıllı sözleşme hataları ve köprü saldırıları düzenli olarak fon kaybettiriyor. Çıkarılan kripto varlıkların büyük çoğunluğu değersizleşti.
- **Enerji ve düzenleme:** Proof-of-work'ün enerji tüketimi küçük bir ülkeninkiyle karşılaştırılır; birçok ülke madenciliği ya da kripto ödemeleri kısıtladı. Ethereum 2022'de proof-of-stake'e geçerek enerji tüketimini büyük ölçüde azalttı.
- **Tokenizasyon:** Bankaların varlık tokenizasyon projelerinin çoğu, herkese açık zincirlerde değil, izinli (permissioned) defterlerde yürüyor; bu, Bitcoin gibi açık bir paranın kalıcılığını tek başına kanıtlamaz.
:::

::: tahmin Double-Spending Problem ve Consensus Doğrulaması
Aşağıdaki kodda aynı bakiyeyi iki kez harcamaya çalışan (`Double-Spending`) bir işlemin düğümler tarafından nasıl denetlendiği modellenmiştir. Çıktısı nedir?

```python
def cift_harcama_kontrol(cuzdan_bakiye, harcama_1, harcama_2):
    # Blockchain Consensus: İki transfer aynı anda gelirse yalnızca ilk onaylanan geçerlidir
    kalan = cuzdan_bakiye - harcama_1
    ikinci_islem_onay = kalan >= harcama_2
    return kalan, ikinci_islem_onay

bakiye_son, onay = cift_harcama_kontrol(10, 8, 5)
print(f"Kalan={bakiye_son} | IkinciIslem={onay}")
```

???
```cikti
Kalan=2 | IkinciIslem=False
```
Cüzdanda `10` birim varken ilk işlem `8` birimi harcadığında `Kalan=2` olur. Aynı parayı ikinci kez harcamaya çalışan (`5` birimlik) işlem, dağıtık düğümlerin (**Consensus Nodes**) bakiye doğrulamasından dönerek reddedilir (`False`), böylece **Double-Spending Problem** engellenir.
:::

::: gorev 1 · Satoshi Tam Sayılarıyla Bitcoin Arzı ve Yarılanma
Bitcoin Core blok ödülünü kayan noktayla değil **satoshi** ($10^{-8}$ BTC) cinsinden tam sayıyla hesaplar: yükseklik $y$'deki bloğun ödülü `(50 * 10**8) >> (y // 210000)`'dir; yarılanma sayısı 64 ya da daha fazlaysa ödül 0'dır. `bitcoin_arzi(blok_sayisi)` işlevini yaz: yüksekliği 0'dan `blok_sayisi - 1`'e kadar olan blokların toplam ödülünü hesaplar.

**Çıktı:**
- `"son_blok_odulu_satoshi"`: son bloğun (yükseklik `blok_sayisi - 1`) ödülü; hiç blok yoksa 0.
- `"toplam_satoshi"`: toplam ödül (tam sayı).
- `"toplam_btc"`: `toplam_satoshi / 10**8`.
- `"yarilanma"`: son bloğa kadar gerçekleşen yarılanma sayısı, `min(64, (blok_sayisi - 1) // 210000)`; hiç blok yoksa 0.

Milyarlarca bloğu tek tek toplamak yerine dönem dönem topla (her dönemde ödül sabittir). `blok_sayisi` negatif olmayan bir tam sayı değilse (`bool` dahil) `ValueError` ver.

```starter
def bitcoin_arzi(blok_sayisi):
    # KUSURLU BAŞLANGIÇ: kayan nokta kullanıyor; satoshi yuvarlamasını, son bloğun yüksekliğini ve 64 yarılanma sınırını yok sayıyor
    donem = min(blok_sayisi // 210000, 64)
    toplam = sum(210000 * 50.0 / 2 ** k for k in range(donem)) + (blok_sayisi % 210000) * 50.0 / 2 ** donem
    return {"son_blok_odulu_satoshi": int(50 * 10**8 / 2 ** donem), "toplam_satoshi": int(toplam * 10**8), "toplam_btc": toplam, "yarilanma": donem}

print(bitcoin_arzi(840001))
```

```test
fn = need("bitcoin_arzi")
eq(fn(0), {"son_blok_odulu_satoshi": 0, "toplam_satoshi": 0, "toplam_btc": 0.0, "yarilanma": 0}, "hiç blok yok")
eq(fn(1)["toplam_satoshi"], 5000000000, "genesis bloğu: 50 BTC")
eq(fn(210000)["toplam_satoshi"], 1050000000000000, "ilk dönem: 210 000 × 50 BTC")
eq(fn(210000)["yarilanma"], 0, "yükseklik 209 999 hâlâ ilk dönemde")
eq(fn(210001)["son_blok_odulu_satoshi"], 2500000000, "yükseklik 210 000: ilk yarılanma, 25 BTC")
eq(fn(210001)["yarilanma"], 1, "yükseklik 210 000'de bir yarılanma olmuş")
eq(fn(840001)["son_blok_odulu_satoshi"], 312500000, "Nisan 2024 yarılanması: 3.125 BTC")
eq(fn(840001)["toplam_satoshi"], 1968750312500000, "dört dönem + bir blok")
eq(fn(6930000)["son_blok_odulu_satoshi"], 1, "33. dönem: ödül 1 satoshi")
eq(fn(6930000)["toplam_satoshi"], 2099999997690000, "bütün arz: 2 099 999 997 690 000 satoshi")
eq(fn(6930000)["toplam_btc"], 20999999.9769, "21 milyonun 0.0231 BTC altında")
eq(fn(6_929_999)["toplam_satoshi"], 2_099_999_997_689_999, "Son ödüllü bloktan önce bir satoshi eksik")
eq(fn(6_930_001), {
    "son_blok_odulu_satoshi": 0,
    "toplam_satoshi": 2_099_999_997_690_000,
    "toplam_btc": 20_999_999.9769,
    "yarilanma": 33,
}, "İlk sıfır ödüllü blokta arz sabit kalır ve dönem ilerler")
eq(fn(10 ** 9)["toplam_satoshi"], 2099999997690000, "ödül 0'a indikten sonra arz artmaz")
eq(fn(10 ** 9)["yarilanma"], 64, "yarılanma sayısı 64'te durur")
eq(fn(10 ** 9)["son_blok_odulu_satoshi"], 0, "64 yarılanmadan sonra ödül 0")
raises(ValueError, fn, -1)
raises(ValueError, fn, 1.5)
raises(ValueError, fn, True)
raises(ValueError, fn, "10")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def bitcoin_arzi(blok_sayisi):\n    if isinstance(blok_sayisi, bool) or not isinstance(blok_sayisi, int) or blok_sayisi < 0:\n        raise ValueError('blok_sayisi negatif olmayan tam sayı olmalı')\n    ODUL, ARALIK = (50 * 10 ** 8, 210000)\n\n    def odul(y):\n        k = y // ARALIK\n        return 0 if k >= 64 else ODUL >> k\n    toplam, y = (0, 0)\n    while y < blok_sayisi:\n        donem_sonu = min(blok_sayisi, (y // ARALIK + 1) * ARALIK)\n        toplam += (donem_sonu - y) * odul(y)\n        y = donem_sonu\n        if odul(y) == 0:\n            break\n    if blok_sayisi == 0:\n        return {'son_blok_odulu_satoshi': 0, 'toplam_satoshi': 0, 'toplam_btc': 0.0, 'yarilanma': 0}\n    son = blok_sayisi - 1\n    return {'son_blok_odulu_satoshi': odul(son), 'toplam_satoshi': toplam, 'toplam_btc': toplam / 10 ** 8, 'yarilanma': min(64, son // ARALIK)}", 'referans', 'exec'), _REF)
_t, _g = _ff(bitcoin_arzi, _REF['bitcoin_arzi'], (840001,), tohum=2199, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (bitcoin_arzi): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def bitcoin_arzi(blok_sayisi):
    if isinstance(blok_sayisi, bool) or not isinstance(blok_sayisi, int) or blok_sayisi < 0:
        raise ValueError("blok_sayisi negatif olmayan tam sayı olmalı")
    ODUL, ARALIK = 50 * 10 ** 8, 210_000

    def odul(y):
        k = y // ARALIK
        return 0 if k >= 64 else ODUL >> k

    toplam, y = 0, 0
    while y < blok_sayisi:
        donem_sonu = min(blok_sayisi, (y // ARALIK + 1) * ARALIK)
        toplam += (donem_sonu - y) * odul(y)
        y = donem_sonu
        if odul(y) == 0:
            break
    if blok_sayisi == 0:
        return {"son_blok_odulu_satoshi": 0, "toplam_satoshi": 0, "toplam_btc": 0.0, "yarilanma": 0}
    son = blok_sayisi - 1
    return {"son_blok_odulu_satoshi": odul(son), "toplam_satoshi": toplam, "toplam_btc": toplam / 10 ** 8,
            "yarilanma": min(64, son // ARALIK)}
```

```hint
Bir dönemin bitiş yüksekliği `(y // 210000 + 1) * 210000`'dir; o dönemdeki blok sayısını ödülle çarp. Ödül 0 olunca döngüden çık.
```
:::

::: gorev 2 · Saldırgan Zinciri Ne Zaman Yetişir? (Nakamoto 2008, Bölüm 11)
Çifte harcama için saldırgan, satıcının gördüğü işlemi içermeyen gizli bir zincir kazar. Satıcı işlemden sonra $z$ blok (onay) bekler. Hash gücünün $q$ kadarı saldırganda, $p = 1 - q$ kadarı dürüst düğümlerdedir. Nakamoto'nun hesabı: dürüst zincir $z$ blok ilerlerken saldırganın ilerlemesi ortalaması $\lambda = z\,q/p$ olan Poisson dağılımıdır; $k$ blok ilerleyen saldırganın aradaki farkı kapatma olasılığı $(q/p)^{z-k}$'dir ($k > z$ ise 1). Toplam:

$$P = 1 - \sum_{k=0}^{z} \frac{\lambda^k e^{-\lambda}}{k!}\left(1 - (q/p)^{z-k}\right)$$

`saldirgan_yetisme(q, z)` işlevini yaz: `{"olasilik": P (round(·, 7)), "lambda": λ (round(·, 6)), "cogunluk_saldirgan": q >= p}`. Saldırgan çoğunluktaysa ($q \ge p$) olasılık 1'dir. `q` 0 ile 1 arasında sonlu bir sayı olmalı (1 hariç), `z` negatif olmayan bir tam sayı olmalı (`bool` değil). Değilse `ValueError`.

```starter
import math

def saldirgan_yetisme(q, z):
    # KUSURLU BAŞLANGIÇ: saldırganın bloklarını rastgele değil, ortalamasıyla sabit sanıyor
    p = 1 - q
    return {"olasilik": round((q / p) ** z, 7), "lambda": round(z * q / p, 6), "cogunluk_saldirgan": q >= p}

print(saldirgan_yetisme(0.1, 5))
```

```test
fn = need("saldirgan_yetisme")
eq(fn(0.1, 0)["olasilik"], 1.0, "hiç beklemeyen satıcı her zaman kandırılabilir")
eq(fn(0.1, 1)["olasilik"], 0.2045873, "makaledeki tablo: q=0.1, z=1")
eq(fn(0.1, 2)["olasilik"], 0.0509779, "q=0.1, z=2")
eq(fn(0.1, 5)["olasilik"], 0.0009137, "q=0.1, z=5")
eq(fn(0.1, 10)["olasilik"], 1.2e-06, "q=0.1, z=10")
eq(fn(0.3, 5)["olasilik"], 0.1773523, "q=0.3, z=5")
eq(fn(0.3, 10)["olasilik"], 0.0416605, "q=0.3, z=10")
eq(fn(0.3, 24)["olasilik"] < 0.001 <= fn(0.3, 23)["olasilik"], True, "q=0.3 için P < 0.001 olması 24 onay ister")
eq(fn(0.1, 5)["lambda"], 0.555556, "λ = z·q/p")
eq(fn(0.5, 3), {"olasilik": 1.0, "lambda": 3.0, "cogunluk_saldirgan": True}, "%50 saldırısı: yetişme kesin")
eq(fn(0.0, 3)["olasilik"], 0.0, "hash gücü olmayan saldırgan yetişemez")
raises(ValueError, fn, 1.0, 3)
raises(ValueError, fn, -0.1, 3)
raises(ValueError, fn, 0.1, -1)
raises(ValueError, fn, 0.1, 2.0)
raises(ValueError, fn, 0.1, True)
raises(ValueError, fn, float("nan"), 3)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef saldirgan_yetisme(q, z):\n    if isinstance(q, bool) or not isinstance(q, (int, float)) or (not math.isfinite(q)) or (not 0 <= q < 1):\n        raise ValueError('q 0 ile 1 arasında olmalı (1 hariç)')\n    if isinstance(z, bool) or not isinstance(z, int) or z < 0:\n        raise ValueError('z negatif olmayan tam sayı olmalı')\n    p = 1.0 - q\n    if q >= p:\n        return {'olasilik': 1.0, 'lambda': round(z * q / p, 6), 'cogunluk_saldirgan': True}\n    lam = z * (q / p)\n    s = 1.0\n    for k in range(z + 1):\n        poisson = math.exp(-lam)\n        for i in range(1, k + 1):\n            poisson *= lam / i\n        s -= poisson * (1 - (q / p) ** (z - k))\n    return {'olasilik': round(s, 7), 'lambda': round(lam, 6), 'cogunluk_saldirgan': False}", 'referans', 'exec'), _REF)
_t, _g = _ff(saldirgan_yetisme, _REF['saldirgan_yetisme'], (0.1, 5), tohum=2734, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (saldirgan_yetisme): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def saldirgan_yetisme(q, z):
    if isinstance(q, bool) or not isinstance(q, (int, float)) or not math.isfinite(q) or not 0 <= q < 1:
        raise ValueError("q 0 ile 1 arasında olmalı (1 hariç)")
    if isinstance(z, bool) or not isinstance(z, int) or z < 0:
        raise ValueError("z negatif olmayan tam sayı olmalı")
    p = 1.0 - q
    if q >= p:
        return {"olasilik": 1.0, "lambda": round(z * q / p, 6), "cogunluk_saldirgan": True}
    lam = z * (q / p)
    s = 1.0
    for k in range(z + 1):
        poisson = math.exp(-lam)
        for i in range(1, k + 1):
            poisson *= lam / i
        s -= poisson * (1 - (q / p) ** (z - k))
    return {"olasilik": round(s, 7), "lambda": round(lam, 6), "cogunluk_saldirgan": False}
```

```hint
Poisson olasılığını faktöriyelle değil, çarpımla biriktir: $e^{-\lambda}$'dan başla, her adımda $\lambda / i$ ile çarp.
```
:::

::: anlat Sınır
Ders paranın evrimini, Bizans generalleri problemini, proof-of-work teşvikini ve Bitcoin'in değer önerisini anlatır. Değer ve 'hiç kaybolmaz' tezleri kanıtlanmış teknik sonuçlar değil, görüş ve varsayımdır. Protokol güvenliği dürüst çoğunluk hash gücüne, sağlam anahtar yönetimine ve doğru istemci yazılımına bağlıdır; kaybolan özel anahtar, borsa iflası ve akıllı sözleşme hataları gerçek kayıplardır. Ödül yarılanmalarından sonra işlem ücretlerinin ağ güvenliğini karşılayıp karşılamayacağı açık bir sorudur. Görevler arz kuralını ve Nakamoto'nun saldırgan modelini hesaplatır; bu model saldırganın hash payının sabit olduğunu ve blok sürelerinin Poisson dağıldığını varsayar, selfish mining ve ağ gecikmesi gibi saldırıları içermez. Ders gerçek blok verisi kullanmaz.

Kaynaklar: [Nakamoto 2008 - Bitcoin: A Peer-to-Peer Electronic Cash System](https://bitcoin.org/bitcoin.pdf), [Lamport vd. 1982 - The Byzantine Generals Problem](https://doi.org/10.1145/357172.357176).
:::

::: dusun
Sahnede bir ekonomist sana şunu sordu:
*"Hocam, devletlerin bastığı paranın arkasında devletin vergi toplama gücü ve ordusu var. Altının arkasında kuyumculuk ve sanayi kullanımı var. Peki Bitcoin veya kripto paraların arkasında ne var?"*

Bu soruya **Trust (Güven) Maliyeti**, **Proof-of-Work**, **21 milyon arz kuralı** ve **Censorship Resistance** kavramlarını kullanarak 1 dakikalık bir cevap ver. Cevabında hangi cümlenin teknik bir gerçek, hangisinin bir görüş olduğunu ayır ve ekonomistin haklı olabileceği en güçlü karşı görüşü de söyle.
:::

::: ozet
- Dijital dünyadaki kopyalanabilirlik sorununu (**Double-Spending Problem**) ve merkezi hakem olmadan uzlaşma sorununu (**Byzantine Generals Problem**), **Satoshi Nakamoto** 2008'de **Proof-of-Work (PoW)** ve **Blockchain** mimarisiyle çözmüştür.
- **Proof-of-Work**, geçmiş kayıtları değiştirmenin maliyetini gerçek enerjiye bağlar; **21 milyon / Halving** kuralı arzı protokolde sabitler (satoshi yuvarlamasıyla toplam 20 999 999.9769 BTC). Bunlar teknik gerçeklerdir; "enerji değer yaratır" ve "mutlak kıtlık değer garantisidir" ise tartışmalı yorumlardır.
- Madenciler ve doğrulayıcılar (**Miners / Validators**), oyun teorisine dayalı **Block Reward + Transaction Fees** ve otonom **Difficulty Adjustment** mekanizmasıyla kâra geçerek ağı korur; yarılanmalardan sonra işlem ücretlerinin bunu karşılayıp karşılamayacağı açık bir sorudur.
- Güvenlik olasılıksaldır: hash gücünün $q$ kadarına sahip bir saldırganın $z$ blok gerideyken yetişme olasılığı $z$ ile üstel olarak düşer ama $q \ge 0.5$ ise 1'dir (Nakamoto 2008, 11. bölüm).
- Kalıcılık tezleri (kapatma düğmesinin olmaması, akıllı sözleşmeler, AI ajan ödemeleri, PQC'ye geçiş) savunucuların görüşüdür; oynaklık, ölçeklenme, borsa çöküşleri, enerji ve düzenleme ise karşı görüşlerin dayanaklarıdır.
:::
