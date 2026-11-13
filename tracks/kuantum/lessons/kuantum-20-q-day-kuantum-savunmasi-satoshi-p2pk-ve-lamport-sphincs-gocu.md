---
id: kuantum-20
title: "Q-Day Kuantum Savunması: Satoshi P2PK Cüzdan Riski, Lamport/SPHINCS+ İmzaları ve Crypto-Agility"
track: kuantum
order: 20
duration_minutes: 40
difficulty: ileri
xp: 340
prerequisites: [kuantum-19]
tags: [q-day, satoshi-p2pk, p2pkh, lamport-signatures, sphincs-plus, fips-205, crypto-agility, post-quantum-blockchain]
summary: "Q-Day kuantum tehdidi altında P2PK ve yeniden kullanılmış adres maruziyetini ölç; SHA-256 tabanlı Lamport tek kullanımlık imza üretimi ve doğrulamasını uygula."
esleme: kuantum-08, kuantum-22
---

::: anlat
## Büyük Final (`Q-Day`): Kuantum Bilgisayarlar Devreye Girdiğinde Satoshi'nin 1.1 Milyon Bitcoin'ine Ne Olacak?

Yolculuğumuzun zirvesine, hem kuantum fiziği hem siber güvenlik hem de blokzincir konferanslarının en çarpıcı final sorusuna geldik:
> *"Hocam, kriptografik olarak anlamlı büyük bir kuantum bilgisayarın (**`CRQC — Cryptographically Relevant Quantum Computer`**) çalıştığı gün (**`Q-Day`**), Bitcoin ve Ethereum ağı anında çökecek mi? Satoshi Nakamoto'nun 2009'da kazdığı ~1.1 Milyon Bitcoin (~100 Milyar Dolar) gerçekten kuantum hacker'ların açık hedefi mi? Ve tüm dünyayı kurtaracak **`Hash-Based Signatures` (`Lamport` / `SPHINCS+`)** ile **`Crypto-Agility`** göçü nasıl çalışır?"*

Bu derste hem mevcut blokzincir cüzdanlarının **`Q-Day`** maruziyet haritasını çıkarıyor hem de kafes matematiği bile bir gün kırılırsa ayakta kalacak olan **hash tabanlı `Lamport / SPHINCS+` (`NIST FIPS 205`, SLH-DSA)** imzalarını sıfırdan kodluyoruz!

---

### 1. Bitcoin Cüzdanlarının `Q-Day` Kuantum Risk Analizi: `P2PK` vs `P2PKH`

Bir kuantum bilgisayarın **`Shor's Algorithm`** ile `ECDSA (secp256k1)` özel anahtarını ($d$) bulabilmesi için, kurbanın **Eliptik Eğri Açık Anahtarını (`Public Key` $Q = d \cdot G$)** bilmesi **şarttır**! Sadece `SHA-256` veya `RIPEMD-160` özetine bakarak `Shor` algoritmasını **çalıştıramazsın** (çünkü özet fonksiyonları tek yönlüdür ve `Grover` algoritması $2^{160}$ uzayını sadece $2^{80}$'e indirebilir, bu da kuantum bilgisayarlar için bile pratikte imkansızdır).

İşte bu ayrım, blokzincirdeki adresleri **3 farklı kuantum risk seviyesine** ayırır:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│          BLOKZİNCİR ADRESLERİNİN Q-DAY KUANTUM MARUZİYET HARİTASI            │
├────────────────────────┬─────────────────────────┬───────────────────────────┤
│ 1. 🔴 KRİTİK RİSK      │ 2. 🟠 YÜKSEK RİSK       │ 3. 🟢 DÜŞÜK RİSK (GEÇİCİ)│
│    P2PK & Taproot      │    ADRES TEKRARI        │    TEMİZ P2PKH / P2WPKH   │
│    (Pay-to-Public-Key) │    (Reused P2PKH)       │    (Hiç Harcama Yapmamış) │
├────────────────────────┼─────────────────────────┼───────────────────────────┤
│ • Satoshi'nin 2009-2010│ • Adres `HASH160(PubKey)`│ • Cüzdana sadece para     │
│   yıllarında kazdığı   │   olarak başlar ama     │   yatırılmış, bu adresten │
│   ~1.1 Milyon BTC!     │   kullanıcı o adresten  │   HİÇ ÇIKIŞ (Harcama)     │
│ • Blokzincirde özet    │   1 KEZ BİLE dışarı     │   yapılmamıştır!          │
│   değil, HAM 65-baytlık│   para gönderdiği an    │ • Ham `Public Key` zincir │
│   `secp256k1 PublicKey`│   imzayı doğrulamak     │   üzerinde HİÇBİR YERDE   │
│   doğrudan yazılıdır!  │   için ham `Public Key` │   yazmaz; `SHA256` +      │
│ • Q-Day geldiği an     │   zincire kazınır!      │   `RIPEMD160` zırhı       │
│   Shor algoritmasına   │ • Eğer kalan para aynı  │   arkasında gizlidir!     │
│   %100 AÇIK HEDEFTİR!  │   adreste tutulursa     │ • Yalnızca harcama anında │
│   (~4 Milyon BTC bu    │   Shor ile çalınabilir! │   Mempool'da kısa süreli  │
│   kategoridedir!)      │                         │   ifşa riski vardır!      │
└────────────────────────┴─────────────────────────┴───────────────────────────┘
```

#### ⚡ Kuantum Hacker Senaryosu: `In-Transit Quantum Mempool Hijacking`
Diyelim ki "Temiz `P2PKH`" (`3.` kategori) bir cüzdanın var ve içine hiç dokunmadığın 50 BTC koydun. `Q-Day` geldiğinde paran durduğu yerde güvendedir çünkü açık anahtarın (`Public Key`) özetin arkasında gizlidir.
- **Ama dikkat!** O 50 BTC'yi güvenli bir `Post-Quantum` adrese taşımak için işlemi imzalayıp **`Mempool`**'a yayınladığın saniyede, işleminin içinde **ham `Public Key`'in tüm dünyaya görünür olur!**
- Eğer kuantum saldırganın **`Shor's Algorithm`** çalışma süresi, Bitcoin'in blok süresi olan **10 dakikadan (veya Ethereum'un 12 saniyesinden) daha kısa** hale gelirse:
  1. Kuantum botu senin işlemini `Mempool`'da havada yakalar,
  2. Açık anahtarından özel anahtarını ($d$) birkaç dakikada çözer,
  3. Aynı 50 BTC'yi kendi adresine gönderen ve madenciye **10 kat daha yüksek komisyon (`Replace-By-Fee / Front-run`)** ödeyen yeni bir işlem imzalayıp senin işleminin önüne geçerek parayı havada kapar!
- İşte bu yüzden ağlar, kuantum bilgisayarlar dakikalar seviyesine inmeden **önce** **`Post-Quantum Hard Fork`** yapmak ve uzun süredir hareketsiz olan `P2PK` fonlarını korumak (veya dondurmak) üzerine aktif `BIP` (`Bitcoin Improvement Proposal`) tasarıları hazırlamaktadır.

---

### 2. Cebirsel Varsayıma Dayanmayan Son Kale: `Lamport One-Time Signature (OTS)` ve `SPHINCS+`

Önceki derslerimizde `NIST FIPS 204 (ML-DSA / Dilithium)` gibi kafes (**`Lattice-Based`**) imzalarını öğrenmiştik. Peki ya 30 yıl sonra bir matematikçi kafes problemlerini (`LWE`) çözen yeni bir cebirsel algoritma bulursa?

Kriptografide **hiçbir sayı teorisi veya cebirsel varsayıma (Asal çarpanlara ayırma, Eliptik eğri, Kafes) dayanmayan**, yalnızca **`SHA-256` / `SHA-3` gibi tek yönlü özet fonksiyonlarının (`One-Way Hash Functions`) tersinmezliğine dayanan** bir imza ailesi vardır (güvenliği seçilen hash fonksiyonuna, parametrelere ve doğru uygulamaya bağlıdır; koşulsuz kırılamazlık vaadi değildir): **`Hash-Based Signatures`**!

#### 🔑 `Lamport Signature` (Leslie Lamport, 1979) Nasıl Çalışır?
Diyelim ki $k$ bitlik bir mesaj özetini ($m = b_0 b_1 \dots b_{k-1}$) imzalayacağız:
1. **Özel Anahtar (`Private Key`):** Her bit pozisyonu $i \in \{0, \dots, k-1\}$ için rastgele **iki adet** gizli sayı (biri `0` biti için, biri `1` biti için) üretiriz:
   $$sk_i = (x_{i, 0}, \; x_{i, 1})$$
2. **Açık Anahtar (`Public Key`):** Bu gizli sayıların her birinin kriptografik özetini (`SHA-256`) alıp dünyaya yayınlarız:
   $$pk_i = \big(\text{Hash}(x_{i, 0}), \; \text{Hash}(x_{i, 1})\big)$$
3. **İmzalama (`Sign`):** Mesajın $i$-inci biti $b_i = 0$ ise kutudan $x_{i, 0}$'ı, eğer $b_i = 1$ ise $x_{i, 1}$'i çıkarıp imzaya koyarız:
   $$\sigma = (x_{0, b_0}, \; x_{1, b_1}, \; \dots, \; x_{k-1, b_{k-1}})$$
4. **Doğrulama (`Verify`):** Doğrulayıcı elindeki $\sigma_i$ değerlerinin özetini alır ve açık anahtardaki $\text{Hash}(x_{i, b_i})$ ile eşit olup olmadığına bakar!

```python
import hashlib

def h(x):
    return hashlib.sha256(x.encode("utf-8")).hexdigest()[:16]

# 4-bitlik mesaj ("1011") icin Lamport Tek Kullanimlik Imza (OTS) Ornegi
ozel_anahtar = [(f"gizli_{i}_bit0", f"gizli_{i}_bit1") for i in range(4)]
acik_anahtar = [(h(k0), h(k1)) for k0, k1 in ozel_anahtar]

mesaj_bitleri = "1011"
imza = [ozel_anahtar[i][int(bit)] for i, bit in enumerate(mesaj_bitleri)]
dogrulama = all(h(imza[i]) == acik_anahtar[i][int(bit)] for i, bit in enumerate(mesaj_bitleri))
print(f"Mesaj: {mesaj_bitleri} | Imza Ilk Eleman: {imza[0]} | Dogrulandi mi?: {dogrulama}")
```

#### ⚠️ Neden "Tek Kullanımlık (`One-Time Signature`)" ve `SPHINCS+` (`FIPS 205`) Bunu Nasıl Çözdü?
- Tek bir `Lamport` anahtarıyla 1 mesaj imzaladığında gizli anahtar parçalarının **%50'sini** dünyaya açıklamış olursun! Aynı anahtarla ikinci bir mesaj imzalarsan %75'i, üçüncüde %87.5'i ifşa olur ve saldırgan açıklanan parçaları birleştirerek sahte mesaj imzalayabilir!
- **Ralph Merkle** ve modern kriptograflar bunu çözmek için binlerce tek kullanımlık imzayı (`WOTS+ — Winternitz One-Time Signature` ve `FORS`) devasa bir **hiyerarşik `Merkle Tree` (`Hypertree`)** altında birleştirdi!
- İşte **Ağustos 2024'te `NIST FIPS 205` (`SLH-DSA`)** adıyla resmileşen **`SPHINCS+`** standardı budur: Durum bilgisi tutmayan (**`Stateless Hash-Based Signature`**), yalnızca özet fonksiyonlarına dayanan ve **Kuantum Bilgisayarlara karşı matematiksel olarak en muhafazakar, en sarsılmaz savunma kalesi!**

---

### 3. Kurumsal `Crypto-Agility` (Kriptografik Çeviklik) Mimarisi

Bir yazılım sistemini veya blokzinciri geleceğe hazırlamanın altın kuralı **`Crypto-Agility`** ilkesidir:
1. **Algoritmayı Koda Çivileme (`No Hardcoded Primitives`):** Kodun içine sabit `ECDSA` veya `RSA` yazmak yerine her imzayı ve anahtarı bir **`Algorithm Identifier (AlgID)`** başlığıyla soyutla.
2. **Hibrit Geçiş (`Hybrid Mode`):** Klasik ve Post-Quantum algoritmaları `AND` mantığıyla birleştir (`ECDSA + ML-DSA` veya `X25519 + ML-KEM-768`). Böylece iki algoritmadan biri sağlam kaldığı sürece birleşik şema da güvenli kalır (birleştirme doğru uygulandıysa).
:::

::: tahmin Lamport Tek Kullanımlık İmza (OTS) Anahtar İfşa Oranı
256-bitlik bir mesaj özetini imzalamak için kullanılan bir `Lamport One-Time Signature` özel anahtarı toplam $256 \times 2 = 512$ adet gizli rastgele sayıdan oluşmaktadır. Kullanıcı bu anahtarla **ilk mesajını** imzalayıp yayınladığında, 512 gizli sayıdan kaç tanesi dünyaya ifşa olur? Eğer **tamamen zıt bitlere sahip** ikinci bir mesajı da (`~m`) yanlışlıkla aynı anahtarla imzalarsa toplam yüzde kaçı ifşa olmuş olur?

```python
toplam_gizli_parca = 512
ilk_imzada_aciklanan = 256
zit_ikinci_imzada_toplam = 256 + 256
oran_1 = int(ilk_imzada_aciklanan / toplam_gizli_parca * 100)
oran_2 = int(zit_ikinci_imzada_toplam / toplam_gizli_parca * 100)
print(f"1. Imza Ifsa: {ilk_imzada_aciklanan} (%{oran_1}) | Zit 2. Imza Ifsa: %{oran_2}")
```

???
```cikti
1. Imza Ifsa: 256 (%50) | Zit 2. Imza Ifsa: %100
```
İlk imzada her bit pozisyonu için iki kutudan biri açıldığı için $512$ gizli değerin tam $256$ tanesi (`%50`) açığa çıkar. Eğer zıt bitlere sahip ikinci bir mesaj da aynı `Lamport` anahtarıyla imzalanırsa diğer $256$ kutu da açılır (`%100` ifşa!) ve saldırgan artık istediği herhangi bir mesajı imzalayabilir!
:::

::: gorev 1 · Lamport Hash Tabanlı Tek Kullanımlık İmza (OTS) Üretimi ve Doğrulaması
Yalnızca **`SHA-256`** özet fonksiyonuna dayanan kuantuma dirençli **`Lamport One-Time Signature`** şemasını gerçekleyen `lamport_imzala_ve_dogrula(ozel_anahtar_ciftleri, mesaj_bitleri, aday_imza)` fonksiyonunu yaz.

**Girdiler:**
- `ozel_anahtar_ciftleri`: Her bit pozisyonu `i` için `(gizli_0, gizli_1)` metin çiftlerinden oluşan liste (`list[tuple[str, str]]`).
- `mesaj_bitleri`: `"0"` ve `"1"` karakterlerinden oluşan mesaj dizisi (`str`, uzunluğu `len(ozel_anahtar_ciftleri)` kadardır).
- `aday_imza`: Doğrulanmak üzere dışarıdan gelen aday imza listesi (`list[str]`).

**Kurallar ve Çıktı Sözlüğü (`dict`):**
Özet fonksiyonu olarak `hashlib.sha256(metin.encode("utf-8")).hexdigest()` kullanılır.
1. `"acik_anahtar"`: Her `(gizli_0, gizli_1)` çifti için `(sha256(gizli_0), sha256(gizli_1))` demetlerinden oluşan liste (`list[tuple[str, str]]`).
2. `"uretilen_imza"`: `mesaj_bitleri` içindeki her `i, bit` için `bit == "0"` ise `ozel_anahtar_ciftleri[i][0]`, `"1"` ise `ozel_anahtar_ciftleri[i][1]` seçilerek oluşturulan liste (`list[str]`).
3. `"aday_gecerli_mi"`: `aday_imza` uzunluğu mesaj uzunluğuna eşitse ve her `i` pozisyonu için `sha256(aday_imza[i]) == acik_anahtar[i][int(mesaj_bitleri[i])]` koşulu sağlanıyorsa `True`, aksi halde `False` (`bool`).

```starter
import hashlib

def lamport_imzala_ve_dogrula(ozel_anahtar_ciftleri, mesaj_bitleri, aday_imza):
    # TODO: SHA-256 tabanli Lamport acik anahtarini, imzasini uret ve aday_imza'yi dogrula
    return {
        "acik_anahtar": [],
        "uretilen_imza": [],
        "aday_gecerli_mi": False,
    }
```

```test
import hashlib
fn = need("lamport_imzala_ve_dogrula")

def _h(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

sk = [
    ("sk0_ sıfır", "sk0_bir"),
    ("sk1_sıfır", "sk1_bir"),
    ("sk2_sıfır", "sk2_bir"),
    ("sk3_sıfır", "sk3_bir"),
]
mesaj = "1010"
dogru_aday = ["sk0_bir", "sk1_sıfır", "sk2_bir", "sk3_sıfır"]

# 1) Gecerli imza uretimi ve dogrulamasi
r1 = fn(sk, mesaj, dogru_aday)
eq(len(r1["acik_anahtar"]), 4, "Acik anahtar 4 ciftten olusmali")
eq(r1["acik_anahtar"][0], (_h("sk0_ sıfır"), _h("sk0_bir")), "Acik anahtar SHA-256 ozetlerinden olusmali")
eq(r1["uretilen_imza"], dogru_aday, "1010 mesaji icin dogru gizli anahtar parcalari secilmeli")
eq(r1["aday_gecerli_mi"], True, "Dogru aday imza dogrulamadan gecmeli")

# 2) Tek bitlik sahte imza denemesi
sahte_aday = ["sk0_bir", "sk1_bir", "sk2_bir", "sk3_sıfır"]  # 1. bit icin yanlis parca!
r2 = fn(sk, mesaj, sahte_aday)
eq(r2["aday_gecerli_mi"], False, "Yanlis gizli parca iceren imza reddedilmeli")

# 3) Eksik uzunlukta imza denemesi
r3 = fn(sk, mesaj, ["sk0_bir"])
eq(r3["aday_gecerli_mi"], False, "Eksik uzunluktaki aday imza False donmeli")

eq(fn(sk, mesaj, dogru_aday + ["ek"])["aday_gecerli_mi"], False,
   "Artık imza öğesi reddedilir")
for i in range(len(dogru_aday)):
    degisik = dogru_aday[:]
    degisik[i] = "geçersiz"
    eq(fn(sk, mesaj, degisik)["aday_gecerli_mi"], False,
       f"Doğrulama {i}. imza konumunu da denetler")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import hashlib\n\ndef lamport_imzala_ve_dogrula(ozel_anahtar_ciftleri, mesaj_bitleri, aday_imza):\n\n    def ozetle(metin):\n        return hashlib.sha256(metin.encode('utf-8')).hexdigest()\n    acik_anahtar = [(ozetle(k0), ozetle(k1)) for k0, k1 in ozel_anahtar_ciftleri]\n    uretilen_imza = [ozel_anahtar_ciftleri[i][int(bit)] for i, bit in enumerate(mesaj_bitleri)]\n    if len(aday_imza) != len(mesaj_bitleri):\n        gecerli = False\n    else:\n        gecerli = all((ozetle(aday_imza[i]) == acik_anahtar[i][int(mesaj_bitleri[i])] for i in range(len(mesaj_bitleri))))\n    return {'acik_anahtar': acik_anahtar, 'uretilen_imza': uretilen_imza, 'aday_gecerli_mi': gecerli}", 'referans', 'exec'), _REF)
_t, _g = _ff(lamport_imzala_ve_dogrula, _REF['lamport_imzala_ve_dogrula'], ([('sk0_ sıfır', 'sk0_bir'), ('sk1_sıfır', 'sk1_bir'), ('sk2_sıfır', 'sk2_bir'), ('sk3_sıfır', 'sk3_bir')], '1010', ['sk0_bir', 'sk1_sıfır', 'sk2_bir', 'sk3_sıfır']), tohum=3575, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (lamport_imzala_ve_dogrula): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import hashlib

def lamport_imzala_ve_dogrula(ozel_anahtar_ciftleri, mesaj_bitleri, aday_imza):
    def ozetle(metin):
        return hashlib.sha256(metin.encode("utf-8")).hexdigest()

    acik_anahtar = [(ozetle(k0), ozetle(k1)) for k0, k1 in ozel_anahtar_ciftleri]
    uretilen_imza = [
        ozel_anahtar_ciftleri[i][int(bit)]
        for i, bit in enumerate(mesaj_bitleri)
    ]

    if len(aday_imza) != len(mesaj_bitleri):
        gecerli = False
    else:
        gecerli = all(
            ozetle(aday_imza[i]) == acik_anahtar[i][int(mesaj_bitleri[i])]
            for i in range(len(mesaj_bitleri))
        )

    return {
        "acik_anahtar": acik_anahtar,
        "uretilen_imza": uretilen_imza,
        "aday_gecerli_mi": gecerli,
    }
```

```hint
`acik_anahtar` için her `(k0, k1)` çiftinin `sha256` özetini al. `uretilen_imza` için `int(bit)` (`0` veya `1`) indisini seç. Doğrulamada ise `ozetle(aday_imza[i]) == acik_anahtar[i][int(mesaj_bitleri[i])]` eşitliğini tüm bitler için kontrol et.
```
:::

::: gorev 2 · Blokzincir Cüzdanlarının Q-Day Kuantum Maruziyet (P2PK / Reused Address / Clean P2PKH) Denetçisi
Bir kurumsal saklama kuruluşunun (`Custody`) cüzdan portföyünü tarayıp **`Q-Day` (`Shor's Algorithm`)** karşısındaki risk sınıflarını ve acil göç (`Migration`) gerektiren toplam bakiyeyi hesaplayan `qday_cuzdan_risk_analizi(cuzdanlar)` fonksiyonunu yaz.

**Girdi (`cuzdanlar`):**
Her elemanı şu anahtarlara sahip bir sözlük olan liste:
- `"adres_id"`: Cüzdan kimliği (`str`)
- `"tip"`: `"P2PK"`, `"P2PKH"`, `"P2WPKH"` veya `"PQC_SPHINCS"` (`str`)
- `"cikis_islem_sayisi"`: Bu adresten daha önce dışarıya gönderilen harcama işlemi sayısı (`int`)
- `"bakiye"`: Cüzdandaki miktar (`float`)

**Sınıflandırma Kuralları:**
1. **`"PQC_GUVENLI"`:** `"tip" == "PQC_SPHINCS"` olan cüzdanlar (Kuantuma tam dirençli).
2. **`"KRITIK_ACIK_ANAHTAR"` (Acil Göç Gerekli!):**
   - `"tip" == "P2PK"` olan cüzdanlar (harcama yapmamış olsa bile açık anahtarı blokzincirde çıplaktır!), **VEYA**
   - `"tip"` değeri `"P2PKH"` ya da `"P2WPKH"` olup `"cikis_islem_sayisi" > 0` olan cüzdanlar (daha önce harcama yaptığı için açık anahtarı zincirde ifşa olmuştur — `Address Reuse`!).
3. **`"OZET_KORUMALI"`:** `"tip"` değeri `"P2PKH"` veya `"P2WPKH"` olup `"cikis_islem_sayisi" == 0` olan cüzdanlar (açık anahtar henüz `HASH160` arkasında gizlidir).

**Çıktı Sözlüğü (`dict`):**
- `"kritik_adresler"`: `"KRITIK_ACIK_ANAHTAR"` sınıfına giren cüzdanların `"adres_id"` listesi (girdi sırasıyla)
- `"kritik_toplam_bakiye"`: Kritik sınıftaki cüzdanların `"bakiye"` toplamı (`round(..., 4)`)
- `"ozet_korumali_bakiye"`: `"OZET_KORUMALI"` sınıfındaki cüzdanların `"bakiye"` toplamı (`round(..., 4)`)
- `"pqc_guvenli_bakiye"`: `"PQC_GUVENLI"` sınıfındaki cüzdanların `"bakiye"` toplamı (`round(..., 4)`)

```starter
def qday_cuzdan_risk_analizi(cuzdanlar):
    # TODO: P2PK, Reused P2PKH/P2WPKH, Temiz P2PKH ve PQC_SPHINCS cuzdanlarini siniflandir
    return {
        "kritik_adresler": [],
        "kritik_toplam_bakiye": 0.0,
        "ozet_korumali_bakiye": 0.0,
        "pqc_guvenli_bakiye": 0.0,
    }
```

```test
fn = need("qday_cuzdan_risk_analizi")

portfoy = [
    {"adres_id": "satoshi_2009", "tip": "P2PK", "cikis_islem_sayisi": 0, "bakiye": 50.0},
    {"adres_id": "sicak_cuzdan", "tip": "P2PKH", "cikis_islem_sayisi": 12, "bakiye": 15.5},
    {"adres_id": "soguk_depo_1", "tip": "P2WPKH", "cikis_islem_sayisi": 0, "bakiye": 120.0},
    {"adres_id": "soguk_depo_2", "tip": "P2PKH", "cikis_islem_sayisi": 0, "bakiye": 80.25},
    {"adres_id": "gelecek_kasa", "tip": "PQC_SPHINCS", "cikis_islem_sayisi": 5, "bakiye": 300.0},
]

r1 = fn(portfoy)
eq(r1["kritik_adresler"], ["satoshi_2009", "sicak_cuzdan"], "P2PK ve harcama yapmis P2PKH kritik listeye girmeli")
eq(r1["kritik_toplam_bakiye"], 65.5, "Kritik bakiye 50.0 + 15.5 = 65.5 olmali")
eq(r1["ozet_korumali_bakiye"], 200.25, "Hic harcama yapmamis P2WPKH ve P2PKH toplami 200.25 olmali")
eq(r1["pqc_guvenli_bakiye"], 300.0, "PQC_SPHINCS bakiyesi harcama yapsa bile 300.0 olarak guvende kalmali")

# Reused P2WPKH testi
r2 = fn([{"adres_id": "tekrar_w", "tip": "P2WPKH", "cikis_islem_sayisi": 1, "bakiye": 10.0}])
eq(r2["kritik_adresler"], ["tekrar_w"], "1 kez bile cikis yapmis P2WPKH adresi kritik sayilmali")
eq(r2["kritik_toplam_bakiye"], 10.0, "Kritik bakiye 10.0 olmali")
r3 = fn([
    {"adres_id": "k", "tip": "P2PK", "cikis_islem_sayisi": 0, "bakiye": 1/3},
    {"adres_id": "o", "tip": "P2WPKH", "cikis_islem_sayisi": 0, "bakiye": 1/3},
    {"adres_id": "p", "tip": "PQC_SPHINCS", "cikis_islem_sayisi": 0, "bakiye": 1/3},
])
eq(r3["kritik_toplam_bakiye"], 0.3333, "4 basamak kritik yuvarlama")
eq(r3["ozet_korumali_bakiye"], 0.3333, "4 basamak ozet yuvarlama")
eq(r3["pqc_guvenli_bakiye"], 0.3333, "4 basamak pqc yuvarlama")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def qday_cuzdan_risk_analizi(cuzdanlar):\n    kritik_adresler = []\n    kritik_bakiye = 0.0\n    ozet_bakiye = 0.0\n    pqc_bakiye = 0.0\n    for c in cuzdanlar:\n        tip = c['tip']\n        cikis = c['cikis_islem_sayisi']\n        bakiye = c['bakiye']\n        if tip == 'PQC_SPHINCS':\n            pqc_bakiye += bakiye\n        elif tip == 'P2PK' or (tip in ('P2PKH', 'P2WPKH') and cikis > 0):\n            kritik_adresler.append(c['adres_id'])\n            kritik_bakiye += bakiye\n        else:\n            ozet_bakiye += bakiye\n    return {'kritik_adresler': kritik_adresler, 'kritik_toplam_bakiye': round(kritik_bakiye, 4), 'ozet_korumali_bakiye': round(ozet_bakiye, 4), 'pqc_guvenli_bakiye': round(pqc_bakiye, 4)}", 'referans', 'exec'), _REF)
_t, _g = _ff(qday_cuzdan_risk_analizi, _REF['qday_cuzdan_risk_analizi'], ([{'adres_id': 'satoshi_2009', 'tip': 'P2PK', 'cikis_islem_sayisi': 0, 'bakiye': 50.0}, {'adres_id': 'sicak_cuzdan', 'tip': 'P2PKH', 'cikis_islem_sayisi': 12, 'bakiye': 15.5}, {'adres_id': 'soguk_depo_1', 'tip': 'P2WPKH', 'cikis_islem_sayisi': 0, 'bakiye': 120.0}, {'adres_id': 'soguk_depo_2', 'tip': 'P2PKH', 'cikis_islem_sayisi': 0, 'bakiye': 80.25}, {'adres_id': 'gelecek_kasa', 'tip': 'PQC_SPHINCS', 'cikis_islem_sayisi': 5, 'bakiye': 300.0}],), tohum=3462, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (qday_cuzdan_risk_analizi): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def qday_cuzdan_risk_analizi(cuzdanlar):
    kritik_adresler = []
    kritik_bakiye = 0.0
    ozet_bakiye = 0.0
    pqc_bakiye = 0.0

    for c in cuzdanlar:
        tip = c["tip"]
        cikis = c["cikis_islem_sayisi"]
        bakiye = c["bakiye"]

        if tip == "PQC_SPHINCS":
            pqc_bakiye += bakiye
        elif tip == "P2PK" or (tip in ("P2PKH", "P2WPKH") and cikis > 0):
            kritik_adresler.append(c["adres_id"])
            kritik_bakiye += bakiye
        else:
            ozet_bakiye += bakiye

    return {
        "kritik_adresler": kritik_adresler,
        "kritik_toplam_bakiye": round(kritik_bakiye, 4),
        "ozet_korumali_bakiye": round(ozet_bakiye, 4),
        "pqc_guvenli_bakiye": round(pqc_bakiye, 4),
    }
```

```hint
Her cüzdan için `tip == "PQC_SPHINCS"` ise `pqc_bakiye`'ye ekle. Değilse ve `tip == "P2PK"` veya `cikis_islem_sayisi > 0` ise açık anahtar zincirde görünür olduğu için `kritik_adresler` ve `kritik_bakiye` içine dahil et; aksi halde `ozet_bakiye`'ye ekle.
```
:::

::: anlat Sınır
Görevler SHA-256 tabanlı Lamport tek kullanımlık imzasını ve cüzdanların Q-Day maruziyet denetçisini yazdırır. Lamport anahtarı yalnız bir kez kullanılabilir; ikinci imza gizli değerlerin bir kısmını daha açar. Pratik sistemler bu yüzden SLH-DSA (SPHINCS+) ya da XMSS/LMS gibi çok imzalı şemalar kullanır; SLH-DSA imzaları yaklaşık 8–50 KB'dır ve blokzincir için ciddi bir maliyettir. Maruziyet denetçisi adres türünden ve yeniden kullanımdan tahmin yapar; mempool'da açıklanan açık anahtarların kısa süreli riskini ve gerçek zincir verisini modellemez. SPHINCS+ yalnız anlatımdadır.

Kaynaklar: [Bernstein vd. 2015 - SPHINCS: practical stateless hash-based signatures](https://eprint.iacr.org/2014/795), [NIST 2024 - FIPS 205: Stateless Hash-Based Digital Signature Standard](https://csrc.nist.gov/pubs/fips/205/final), [NIST 2024 - FIPS 204: Module-Lattice-Based Digital Signature Standard](https://csrc.nist.gov/pubs/fips/204/final).
:::

::: dusun
Satoshi Nakamoto'nun 2009-2010 yıllarında kazdığı ve o günden beri tek bir satoshi bile kıpırdamayan **~1.1 Milyon BTC (`P2PK`)** hakkında Bitcoin topluluğu **`Q-Day`** yaklaşırken tarihi bir etik ve ekonomik ikilemle karşı karşıyadır:
1. Eğer hiçbir şey yapılmazsa, ilk büyük kuantum bilgisayarı üreten güç bu 1.1 Milyon BTC'yi `Shor` algoritmasıyla çalıp piyasayı çökertebilir.
2. Eğer topluluk bir **`Hard Fork / Soft Fork`** ile *"Belirli bir tarihe kadar `Post-Quantum` adreslere taşınmayan tüm eski `P2PK` coin'ler dondurulsun (yakılsın)"* kararı alırsa, bu durum Bitcoin'in **"Kimsenin mülkiyetine dokunulamaz (`Immutability`)"** ilkesini bozar mı? Sen bir protokol mimarı olsan hangi çözümü savunurdun?
:::

::: ozet
- **`Q-Day`** geldiğinde **`Shor's Algorithm`** yalnızca açık anahtarı (`Public Key`) bilinen adresleri kırabilir: Satoshi döneminden kalan **`P2PK`** adresleri ve daha önce harcama yaparak açık anahtarını ifşa etmiş (**`Address Reuse`**) cüzdanlar anında savunmasızdır; hiç harcama yapmamış **`P2PKH / P2WPKH`** adresleri ise harcama anındaki **`Mempool`** penceresine kadar `SHA-256 + RIPEMD-160` özetiyle korunur.
- **`Lamport One-Time Signature (OTS)`** ve onun `Merkle Hypertree` ile çoklu kullanıma genişletilmiş standardı olan **`NIST FIPS 205 (SLH-DSA / SPHINCS+)`**, eliptik eğri veya kafes matematiğine değil yalnızca tek yönlü özet fonksiyonlarına (`Hash`) dayandığı için kuantum bilgisayarlara karşı matematiksel olarak en sağlam imza mimarisidir.
- Kurumlar ve blokzincir ağları, kriptografik algoritmaları soyutlayan **`Crypto-Agility`** tasarımı ve klasik + PQC algoritmalarını birleştiren **hibrit geçiş (`Hybrid Mode`)** ile kuantum çağına kesintisiz hazırlanmaktadır.
:::
