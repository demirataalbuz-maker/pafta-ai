---
id: kuantum-16
title: "Blokzincir Çekirdeği: Sıfırdan Merkle Tree, Merkle Proof ve UTXO vs Account State Motoru"
track: kuantum
order: 16
duration_minutes: 35
difficulty: orta
xp: 290
prerequisites: [kuantum-15]
tags: [merkle-tree, merkle-proof, spv-light-client, utxo, account-model, replay-attack, state-machine]
summary: "SHA-256 tabanlı ikili Merkle ağacı, SPV üyelik kanıtı doğrulaması ve UTXO ile hesap tabanlı durum motorlarını karşılaştırmalı olarak kodla."
esleme: kuantum-08, kuantum-20
---

::: anlat
## Merkle proof ve UTXO

Merkle proof, bir kaydın belirli bir root altında bulunmasıyla ilgili kanıt verir. Root'un hangi zincire ait olduğuna ve zincirin güvenine ayrıca karar vermek gerekir. Bu derste küçük Merkle/UTXO hesaplarıyla bu katmanları ayıracaksın; proof doğrulamak işlemin bütün consensus kurallarını tek başına doğrulamaz.

Ve ikinci temel mimari soru: Neden **Bitcoin** bakiye tutmak yerine kağıt banknotlara benzeyen **`UTXO (Unspent Transaction Output)`** modelini kullanırken, **Ethereum** banka veritabanına benzeyen **`Account-Based State Machine`** modelini seçmiştir? Bu derste blokzincir çekirdeğinin bu iki motorunu sıfırdan inşa ediyoruz.

---

### 1. `Merkle Tree` ve $O(\log_2 N)$ `Merkle Inclusion Proof` (`Audit Path`)

1979 yılında **Ralph Merkle** tarafından icat edilen **`Merkle Tree` (Binary Hash Tree)**, bir blok içindeki binlerce işlemi ($TX_0, TX_1, \dots, TX_{N-1}$) tek bir 32-baytlık (256-bit) parmak izine — **`Merkle Root`** — sıkıştıran ikili özet ağacıdır.

```
                         [ Merkle Root: H_0123 ]
                            /               \
                           /                 \
                 [ H_01 = H(H_0 ‖ H_1) ]   [ H_23 = H(H_2 ‖ H_3) ]  <-- Kanıt #2 (SAĞ kardeş)
                    /             \             /             \
              [ H_0 ]          [ H_1 ]       [ H_2 ]         [ H_3 ]
                 ▲                ▲
        Kanıt #1 (SOL kardeş)   Hedef İşlem (TX_1): Telefonun doğrulamak istediği işlem!
```

#### 🔍 `SPV Light Client` Nasıl Çalışır?
Bir blok başlığı (**`Block Header`**) yalnızca **80 bayt** büyüklüğündedir ve içinde şu alanları barındırır: `Version`, `Previous Block Hash`, `Merkle Root`, `Timestamp`, `Difficulty Target` ve `Nonce`.
- Telefonundaki cüzdan tüm blok gövdelerini (`Transactions`) indirmez; sadece 80 baytlık **`Block Header`** zincirini indirir.
- Diyelim ki bir blokta $N = 4.096$ adet işlem var ve sen **$TX_1$** işleminin bu blokta gerçekten yer aldığını doğrulamak istiyorsun.
- Tam düğümden (`Full Node`) 4.096 işlemin tamamını istemek yerine sadece **`Merkle Proof` (`Audit Path` / Kardeş Özet Yolu)** istersin!
- Yukarıdaki şemada $TX_1$'i doğrulamak için bütün ağaca değil, yalnızca yol üzerindeki kardeş düğümlere (**`Sibling Hashes`**) ihtiyacın vardır:
  1. $H_1 = \text{Hash}(TX_1)$ değerini solundaki kardeş **`(SOL, H_0)`** ile birleştirip özetle: $H_{01} = \text{Hash}(H_0 \parallel H_1)$.
  2. Bulduğun $H_{01}$ değerini sağındaki kardeş **`(SAĞ, H_23)`** ile birleştirip özetle: $H_{0123} = \text{Hash}(H_{01} \parallel H_{23})$.
  3. Elde ettiğin $H_{0123}$ değeri, telefonundaki 80 baytlık `Block Header` içinde yazan **`Merkle Root`** ile birebir aynıysa, işlemin o blokta olduğu **matematiksel olarak kanıtlanmıştır!**

| Bloktaki İşlem Sayısı ($N$) | Tüm Bloğu İndirme Maliyeti ($O(N)$) | `Merkle Proof` Kardeş Özet Sayısı ($\lceil \log_2 N \rceil$) | Kanıt Boyutu (`SHA-256`) |
| :---: | :---: | :---: | :---: |
| **$4\text{ İşlem}$** | $4\text{ işlem}$ | **$2\text{ adım}$** | $64\text{ Bayt}$ |
| **$4.096\text{ İşlem}$** | $4.096\text{ işlem}$ | **$12\text{ adım}$** | **$384\text{ Bayt}$** |
| **$1.048.576\text{ İşlem}$** | $1\text{ Milyon işlem}$ | **$20\text{ adım}$** | **$640\text{ Bayt}$** |

> **Kuantum & Kripto Hacker Notu (`CVE-2012-2459` — Bitcoin Tek Yaprak Kopyalama Zafiyeti):** Bir Merkle seviyesinde düğüm sayısı tek ise (örneğin 3 yaprak: `[A, B, C]`), Bitcoin son yaprağı kopyalayarak çiftler (`[A, B, C, C]`). 2012'de keşfedilen meşhur **`CVE-2012-2459`** zafiyetinde, bir saldırgan bloğun son işlemini kopyalayıp gönderdiğinde aynı **Merkle Root**'a ve aynı **Block Hash**'e sahip ama geçersiz bir blok üreterek düğümleri kilitleyebiliyordu! Modern ağaçlarda yapraklara `0x00`, iç düğümlere `0x01` ön-eki (**`Domain Separation`**) konularak **`Second-Preimage Attack`** tamamen engellenir.

```python
import hashlib

def h256(veri):
    return hashlib.sha256(veri.encode("utf-8")).hexdigest()[:16]

# 4 İslemli [TX0, TX1, TX2, TX3] Merkle Agaci ve TX1 icin Merkle Inclusion Proof
yapraklar = [h256(f"TX{i}") for i in range(4)]
h01 = h256(yapraklar[0] + yapraklar[1])
h23 = h256(yapraklar[2] + yapraklar[3])
merkle_root = h256(h01 + h23)

# TX1 (yapraklar[1]) icin Kanit Yolu: Once SOL kardes yapraklar[0], sonra SAG kardes h23
kanit = [("SOL", yapraklar[0]), ("SAG", h23)]
adim1 = h256(kanit[0][1] + yapraklar[1])   # SOL kardes + hedef
adim2 = h256(adim1 + kanit[1][1])          # mevcut + SAG kardes
print(f"Kok: {merkle_root} | Kanit Hesabi: {adim2} | Dogrulandi: {merkle_root == adim2}")
```

---

### 2. İki Büyük Blokzincir Mimarisi: `Bitcoin UTXO` vs `Ethereum Account Model`

Blokzincir tasarımında durumun (**`Global State`**) nasıl temsil edileceği konusunda iki temel ekol vardır:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│        BITCOIN: UTXO MODELİ            vs       ETHEREUM: ACCOUNT MODELİ     │
│  (Kağıt Banknot / Dijital Küp Altın)          (Banka Hesabı / Durum Tablosu) │
├────────────────────────────────────────┬─────────────────────────────────────┤
│ • Sistemde "Alice'in Bakiyesi" diye    │ • Her adresin küresel durum ağacında│
│   bir tablo sütunu YOKTUR!             │   (State Trie) doğrudan bir satırı  │
│ • Sadece harcanmamış işlem çıktıları   │   vardır:                           │
│   (UTXO kümesi) vardır.                │   {balance, nonce, codeHash,        │
│ • 10 BTC'lik bir UTXO'nun 3 BTC'sini   │    storageRoot}                     │
│   göndermek için 10 BTC'lik UTXO'yu    │ • 10 ETH'den 3 ETH gönderildiğinde  │
│   TAMAMEN İMHA EDER (tüketir), yerine  │   Alice'ten 3 düşülür, Bob'a 3      │
│   2 yeni UTXO yaratırsın:              │   eklenir (Para üstü kavramı yok).  │
│   1) Alıcıya: 3 BTC                    │ • Çifte harcamayı ve tekrar         │
│   2) Kendine Para Üstü (Change): 6.99  │   saldırısını (Replay Attack)       │
│   (Aradaki 0.01 BTC = Miner Fee!)      │   her işlemde +1 artan `nonce`      │
│ • Paralel doğrulamaya (Parallelism)    │   sayacı engeller!                  │
│   ve gizliliğe çok uygundur.           │ • Smart Contract'lar için idealdir. │
└────────────────────────────────────────┴─────────────────────────────────────┘
```

#### 🪙 1. Bitcoin `UTXO (Unspent Transaction Output)` Kuralları
Cebinde **50 TL'lik tek bir kağıt banknot** varken bakkaldan **15 TL'lik** su aldığında banknotu makasla kesemezsin! Bakkal 50 TL'lik banknotunu alır (eski `UTXO` tüketilir / **`Spent`**), sana 15 TL'lik suyu ve **35 TL para üstünü (`Change Output`)** verir.
- **Kural 1 (`Atomicity`):** Bir `UTXO` bölünemez; bir işlemde girdi (`Input`) olarak kullanıldığı an **tamamı tüketilir** ve `UTXO` kümesinden silinir.
- **Kural 2 (`Conservation & Implicit Fee`):** Girdilerin toplam tutarı, çıktıların toplam tutarına eşit veya büyük olmalıdır ($\sum \text{Inputs} \ge \sum \text{Outputs}$). Eğer kullanıcı kendine para üstü (`Change`) çıkışı yazmayı unutursa, aradaki farkın **tamamı otomatik olarak madenciye işlem ücreti (`Miner Fee = Inputs - Outputs`) olarak gider!** (Tarihte yanlışlıkla çok yüksek komisyon ödenen hatalı ham işlemler bu yüzden yaşanmıştır!).
- **Kural 3 (`No Replay via Unique UTXO ID`):** Her `UTXO`'nun benzersiz bir kimliği (`txid:vout`) vardır ve bir kez harcandığında kümeden silindiği için aynı işlem ikinci kez ağa gönderilirse "bu `UTXO` zaten harcandı" denilerek anında reddedilir.

#### ⚙️ 2. Ethereum `Account-Based State Machine`, `Nonce` ve `Replay Attack`
Ethereum'da bir işlem "Alice'ten Bob'a 3 ETH gönder" şeklindedir. Peki kötü niyetli birisi (veya Bob!), Alice'in imzaladığı bu geçerli işlemi kopyalayıp ağa 5 kez daha gönderirse (**`Replay Attack`**), Alice'in hesabından 5 kez 3 ETH çekilir mi?
- **Hayır!** Çünkü Ethereum'da her hesabın **`Account Nonce`** adında bir işlem sayacı vardır (`0, 1, 2, ...`).
- Alice'in imzaladığı işlem `nonce: 42` içerir. İşlem onaylandığı an Alice'in durumdaki sayacı `43` olur. Aynı imzalı paket tekrar gönderildiğinde düğümler `islem.nonce (42) != hesap.nonce (43)` kontrolüyle **`Replay Attack`** girişimini anında çöpe atar!

**Kaynak ve sınır:** [Bitcoin: özgün protocol açıklaması](https://bitcoin.org/bitcoin.pdf). Sayısal örnekler eğitim ölçeğindedir; gerçek quantum hardware, standart PQC ürünü veya ağ üzerindeki bir hedef üzerinde kabul testi yapılmaz.
:::

::: tahmin UTXO Tüketiminde Unutulan Para Üstü (Change Output) Tuzağı
Alice'in cüzdanında `8.5 BTC` değerinde tek bir `UTXO` (`utxo_A`) bulunmaktadır. Alice kendi yazdığı ham işlem (`Raw Transaction`) betiğiyle Bob'a `2.0 BTC`lik tek bir çıktı (`Output`) oluşturur ancak kendisine **para üstü (`Change Output`)** eklemeyi unutur! Bu işlem bloğa girdiğinde madenci ücreti (`Miner Fee`) ve Alice'in kalan `UTXO` bakiyesi ne olur?

```python
girdi_utxo = 8.5
cikislar = [2.0]  # Yalnizca Bob'a giden cikis yazilmis, Change unutulmus!

madenci_ucreti = round(girdi_utxo - sum(cikislar), 2)
alice_yeni_bakiye = 0.0  # utxo_A tamamen tuketildigi ve Alice'e yeni cikis yazilmadigi icin!
print(f"Madenciye Giden Fee: {madenci_ucreti} BTC | Alice Kalan: {alice_yeni_bakiye} BTC")
```

???

```cikti
Madenciye Giden Fee: 6.5 BTC | Alice Kalan: 0.0 BTC
```
`UTXO` modelinde girdi olarak verilen `8.5 BTC`lik `utxo_A` tamamen imha edilir (`Spent`). Protokol kuralı gereği $\text{Fee} = \sum \text{Inputs} - \sum \text{Outputs}$ olduğundan, çıktı olarak yazılmayan `8.5 - 2.0 = 6.5 BTC`nin tamamı madenciye işlem ücreti (`Miner Fee`) olarak gider ve Alice'in elinde `0.0 BTC` kalır!
:::

::: gorev 1 · Merkle Root Hesaplama ve O(log N) Merkle Inclusion Proof Doğrulayıcısı
Bir **`SPV Light Client`** cüzdanının $O(\log_2 N)$ adımda işlem doğrulamasını gerçekleştiren `merkle_kanit_dogrula(yaprak_ozeti, kanit_yolu, beklenen_kok)` fonksiyonunu yaz.

**Özetleme Kuralı (`SHA-256`):**
İki düğüm özeti (`sol` ve `sag` metinleri) birleştirilirken aralarına `":"` konularak `hashlib.sha256(f"{sol}:{sag}".encode("utf-8")).hexdigest()` hesaplanır.

**Girdiler:**
- `yaprak_ozeti`: Doğrulanmak istenen işlemin başlangıç özet metni (`str`).
- `kanit_yolu`: Aşağıdan yukarıya doğru `(yon, kardes_ozeti)` çiftlerinden oluşan liste (`list[tuple[str, str]]`).
  - Eğer `yon == "SOL"` ise kardeş düğüm soldadır: yeni özet `sha256(f"{kardes_ozeti}:{mevcut_ozet}")` olur.
  - Eğer `yon == "SAG"` ise kardeş düğüm sağdadır: yeni özet `sha256(f"{mevcut_ozet}:{kardes_ozeti}")` olur.
- `beklenen_kok`: Blok başlığındaki (`Block Header`) `Merkle Root` özeti (`str`).

**Çıktı Sözlüğü (`dict`):**
- `"hesaplanan_kok"`: Kanıt yolu tamamlandığında ulaşılan kök özet (`str`).
- `"adim_sayisi"`: `kanit_yolu` içindeki adım sayısı (`int`).
- `"gecerli_mi"`: `hesaplanan_kok == beklenen_kok` ise `True`, değilse `False` (`bool`).

```starter
import hashlib

def merkle_kanit_dogrula(yaprak_ozeti, kanit_yolu, beklenen_kok):
    # TODO: Kanit yolundaki SOL / SAG kardes ozetlerini birlestirerek Merkle Root dogrulamasi yap
    return {
        "hesaplanan_kok": "",
        "adim_sayisi": 0,
        "gecerli_mi": False,
    }
```

```test
import hashlib
fn = need("merkle_kanit_dogrula")

def _birlestir(a, b):
    return hashlib.sha256(f"{a}:{b}".encode("utf-8")).hexdigest()

# 4 yaprakli agac: L0, L1, L2, L3
L = [hashlib.sha256(f"tx_{i}".encode("utf-8")).hexdigest() for i in range(4)]
H01 = _birlestir(L[0], L[1])
H23 = _birlestir(L[2], L[3])
KOK = _birlestir(H01, H23)

# L[2] icin kanit: 1) SAG kardes L[3] -> H23, 2) SOL kardes H01 -> KOK
kanit_L2 = [("SAG", L[3]), ("SOL", H01)]
sonuc1 = fn(L[2], kanit_L2, KOK)
eq(sonuc1["hesaplanan_kok"], KOK, "Dogru kanit yolunda hesaplanan kok Merkle Root ile ayni olmali")
eq(sonuc1["adim_sayisi"], 2, "4 yaprakli agacta kanit adim sayisi log2(4)=2 olmali")
eq(sonuc1["gecerli_mi"], True, "Dogru kanit gecerli_mi=True donmeli")

# Yon karistirildiginda (Second-preimage / sira kontrolu) gecersiz olmali
yanlis_yon = [("SOL", L[3]), ("SOL", H01)]
sonuc2 = fn(L[2], yanlis_yon, KOK)
eq(sonuc2["gecerli_mi"], False, "SOL ve SAG sirasi bozuldugunda kanit gecersiz olmali")

# Sahte islem ozeti testi
sonuc3 = fn("sahte_tx_ozeti", kanit_L2, KOK)
eq(sonuc3["gecerli_mi"], False, "Sahte yaprak ozeti Merkle kanitindan gecmemeli")

eq(fn(L[0], [], L[0]), {
    "hesaplanan_kok": L[0], "adim_sayisi": 0, "gecerli_mi": True,
}, "Tek yaprak kendi köküdür")
eq(fn(L[0], [], KOK), {
    "hesaplanan_kok": L[0], "adim_sayisi": 0, "gecerli_mi": False,
}, "Boş yol farklı bir kökü doğrulamaz")
_yol = kanit_L2[:]
_yedek = _yol[:]
eq(fn(L[2], _yol, KOK)["gecerli_mi"], True, "Yol aşağıdan yukarıya izlenir")
eq(_yol, _yedek, "Doğrulama girdi yolunu değiştirmez")
eq(fn(L[2], _yol[::-1], KOK)["gecerli_mi"], False, "Ters seviyeli yol reddedilir")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import hashlib\n\ndef merkle_kanit_dogrula(yaprak_ozeti, kanit_yolu, beklenen_kok):\n    mevcut = yaprak_ozeti\n    for yon, kardes in kanit_yolu:\n        if yon == 'SOL':\n            birlesik = f'{kardes}:{mevcut}'\n        else:\n            birlesik = f'{mevcut}:{kardes}'\n        mevcut = hashlib.sha256(birlesik.encode('utf-8')).hexdigest()\n    return {'hesaplanan_kok': mevcut, 'adim_sayisi': len(kanit_yolu), 'gecerli_mi': mevcut == beklenen_kok}", 'referans', 'exec'), _REF)
_t, _g = _ff(merkle_kanit_dogrula, _REF['merkle_kanit_dogrula'], ('06c989aa3b666ebd9fcc2446005349b772fcb72157a73cbf48ce24e1b353ace9', [('SAG', '4ca65520b9f48c97e02862739ba84215de70389cf8a63bf52fcd729adf96ec25'), ('SOL', 'f1ba9cd33800613774363fe625cbada23ea717122cb5caa4a6fef201f681c783')], 'e9692d6d969209488c39a5f421c72805ca91073e54d7bbe10c8caf49205bfdc2'), tohum=3036, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (merkle_kanit_dogrula): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import hashlib

def merkle_kanit_dogrula(yaprak_ozeti, kanit_yolu, beklenen_kok):
    mevcut = yaprak_ozeti
    for yon, kardes in kanit_yolu:
        if yon == "SOL":
            birlesik = f"{kardes}:{mevcut}"
        else:
            birlesik = f"{mevcut}:{kardes}"
        mevcut = hashlib.sha256(birlesik.encode("utf-8")).hexdigest()

    return {
        "hesaplanan_kok": mevcut,
        "adim_sayisi": len(kanit_yolu),
        "gecerli_mi": mevcut == beklenen_kok,
    }
```

```hint
`mevcut = yaprak_ozeti` ile başla. `for yon, kardes in kanit_yolu:` döngüsünde `yon == "SOL"` ise `f"{kardes}:{mevcut}"`, `"SAG"` ise `f"{mevcut}:{kardes}"` metninin `sha256` özetini alıp `mevcut` değişkenini güncelle.
```
:::

::: gorev 2 · Bitcoin UTXO Giriş/Çıkış Tüketimi, Para Üstü (Change) ve Madenci Ücreti (Fee) Motoru
Bir Bitcoin düğümünün **`UTXO`** kümesini güncelleyen ve çifte harcama (**`Double-Spend`**) ile karşılıksız para üretimi (**`Inflation Bug`**) girişimlerini engelleyen `utxo_islem_yurut(mevcut_utxolar, harcanan_id_listesi, cikislar)` fonksiyonunu yaz.

**Girdiler:**
- `mevcut_utxolar`: Harcanmamış çıktıları tutan sözlük: `{"utxo_id": {"sahip": str, "miktar": float}}`.
- `harcanan_id_listesi`: İşlemin girdi (`Input`) olarak tüketmek istediği `utxo_id` listesi (`list[str]`).
- `cikislar`: İşlemin yaratmak istediği yeni çıktılar listesi: `[{"yeni_id": str, "sahip": str, "miktar": float}]`.

**Doğrulama Kuralları (Sırasıyla):**
1. `harcanan_id_listesi` boşsa, içinde **tekrarlayan (`Duplicate`) aynı `utxo_id`** varsa (aynı işlem içinde çifte harcama!) veya `mevcut_utxolar` içinde **bulunmayan** bir `utxo_id` varsa işlem reddedilir:
   `{"onay": False, "hata": "GECERSIZ_UTXO_GIRDISI", "madenci_ucreti": 0.0, "yeni_utxo_sayisi": len(mevcut_utxolar)}` döndür.
2. `cikislar` içindeki herhangi bir çıktının `"miktar"` değeri `<= 0` ise veya toplam çıktı miktarı toplam girdi miktarından büyükse (`toplam_cikis > toplam_girdi`), işlem reddedilir:
   `{"onay": False, "hata": "YETERSIZ_GIRIS_VEYA_GECERSIZ_MIKTAR", "madenci_ucreti": 0.0, "yeni_utxo_sayisi": len(mevcut_utxolar)}` döndür.
3. İşlem geçerliyse:
   - `mevcut_utxolar` sözlüğünün bir kopyası üzerinden `harcanan_id_listesi` içindeki tüm `UTXO`'lar silinir ve `cikislar` içindeki yeni `UTXO`'lar eklenir.
   - `"madenci_ucreti"`: `round(toplam_girdi - toplam_cikis, 8)`
   - `{"onay": True, "hata": None, "madenci_ucreti": madenci_ucreti, "yeni_utxo_sayisi": len(guncel_utxolar), "guncel_utxolar": guncel_utxolar}` döndür.

```starter
def utxo_islem_yurut(mevcut_utxolar, harcanan_id_listesi, cikislar):
    # TODO: UTXO girislerini dogrula, tuket, yeni cikislari ekle ve madenci ucretini (fee) hesapla
    return {
        "onay": False,
        "hata": "GECERSIZ_UTXO_GIRDISI",
        "madenci_ucreti": 0.0,
        "yeni_utxo_sayisi": len(mevcut_utxolar),
    }
```

```test
fn = need("utxo_islem_yurut")

baslangic = {
    "u1": {"sahip": "Alice", "miktar": 5.0},
    "u2": {"sahip": "Alice", "miktar": 3.0},
    "u3": {"sahip": "Bob", "miktar": 10.0},
}

# 1) Gecerli islem: Alice u1 (5.0) ve u2 (3.0) harciyor (toplam 8.0),
#    Bob'a 6.5 gonderiyor, kendine 1.48 para ustu (change) aliyor -> Fee = 0.02
cikis1 = [
    {"yeni_id": "u4", "sahip": "Bob", "miktar": 6.5},
    {"yeni_id": "u5", "sahip": "Alice", "miktar": 1.48},
]
r1 = fn(baslangic, ["u1", "u2"], cikis1)
eq(r1["onay"], True, "Gecerli UTXO islemi onaylanmali")
eq(r1["hata"], None, "Gecerli islemde hata None olmali")
eq(r1["madenci_ucreti"], 0.02, "Madenci ucreti 8.0 - 7.98 = 0.02 olmali")
eq(r1["yeni_utxo_sayisi"], 3, "2 UTXO silinip 2 yeni UTXO eklendiginde toplam 3 UTXO kalmali")
ok("u1" not in r1["guncel_utxolar"] and "u4" in r1["guncel_utxolar"], "Harcanan u1 silinmeli, yeni u4 eklenmeli")

# 2) Ayni islem icinde ayni UTXO'yu iki kez kullanma (Double-Spend Input)
r2 = fn(baslangic, ["u1", "u1"], cikis1)
eq(r2["onay"], False, "Ayni UTXO iki kez girdi olarak verilirse reddedilmeli")
eq(r2["hata"], "GECERSIZ_UTXO_GIRDISI", "Tekrarlayan UTXO girdisi hatasi donmeli")

# 3) Olmayan UTXO harcama girisimi
r3 = fn(baslangic, ["u99"], cikis1)
eq(r3["onay"], False, "Var olmayan UTXO harcanamaz")
eq(r3["hata"], "GECERSIZ_UTXO_GIRDISI", "Olmayan UTXO icin GECERSIZ_UTXO_GIRDISI donmeli")

# 4) Girdiden fazla cikis uretme (Inflation Bug saldirisi)
r4 = fn(baslangic, ["u2"], [{"yeni_id": "u6", "sahip": "Saldirgan", "miktar": 3.5}])
eq(r4["onay"], False, "3.0 BTC girdiden 3.5 BTC cikis uretilemez")
eq(r4["hata"], "YETERSIZ_GIRIS_VEYA_GECERSIZ_MIKTAR", "Fazla cikista YETERSIZ_GIRIS_VEYA_GECERSIZ_MIKTAR donmeli")
r5 = fn(baslangic, [], cikis1)
eq(r5["onay"], False, "Bos harcanan UTXO listesi reddedilmeli")
eq(r5["hata"], "GECERSIZ_UTXO_GIRDISI", "Bos girdi GECERSIZ_UTXO_GIRDISI donmeli")
r6 = fn({"u1": {"sahip": "A", "miktar": 1.0}}, ["u1"], [{"yeni_id": "u2", "sahip": "B", "miktar": 1/3}])
eq(r6["madenci_ucreti"], 0.66666667, "Madenci ucreti 8 basamak satoshi hassasiyetiyle yuvarlanmali")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def utxo_islem_yurut(mevcut_utxolar, harcanan_id_listesi, cikislar):\n    if not harcanan_id_listesi or len(set(harcanan_id_listesi)) != len(harcanan_id_listesi) or any((uid not in mevcut_utxolar for uid in harcanan_id_listesi)):\n        return {'onay': False, 'hata': 'GECERSIZ_UTXO_GIRDISI', 'madenci_ucreti': 0.0, 'yeni_utxo_sayisi': len(mevcut_utxolar)}\n    toplam_girdi = sum((mevcut_utxolar[uid]['miktar'] for uid in harcanan_id_listesi))\n    if any((c['miktar'] <= 0 for c in cikislar)):\n        return {'onay': False, 'hata': 'YETERSIZ_GIRIS_VEYA_GECERSIZ_MIKTAR', 'madenci_ucreti': 0.0, 'yeni_utxo_sayisi': len(mevcut_utxolar)}\n    toplam_cikis = sum((c['miktar'] for c in cikislar))\n    if toplam_cikis > toplam_girdi:\n        return {'onay': False, 'hata': 'YETERSIZ_GIRIS_VEYA_GECERSIZ_MIKTAR', 'madenci_ucreti': 0.0, 'yeni_utxo_sayisi': len(mevcut_utxolar)}\n    guncel = {k: dict(v) for k, v in mevcut_utxolar.items() if k not in harcanan_id_listesi}\n    for c in cikislar:\n        guncel[c['yeni_id']] = {'sahip': c['sahip'], 'miktar': c['miktar']}\n    ucret = round(toplam_girdi - toplam_cikis, 8)\n    return {'onay': True, 'hata': None, 'madenci_ucreti': ucret, 'yeni_utxo_sayisi': len(guncel), 'guncel_utxolar': guncel}", 'referans', 'exec'), _REF)
_t, _g = _ff(utxo_islem_yurut, _REF['utxo_islem_yurut'], ({'u1': {'sahip': 'Alice', 'miktar': 5.0}, 'u2': {'sahip': 'Alice', 'miktar': 3.0}, 'u3': {'sahip': 'Bob', 'miktar': 10.0}}, ['u1', 'u2'], [{'yeni_id': 'u4', 'sahip': 'Bob', 'miktar': 6.5}, {'yeni_id': 'u5', 'sahip': 'Alice', 'miktar': 1.48}]), tohum=2698, en_cok=600, mod='gecerli', butce='oto', ekler=[({'u1': {'sahip': 'Alice', 'miktar': 5.0}, 'u2': {'sahip': 'Alice', 'miktar': 3.0}, 'u3': {'sahip': 'Bob', 'miktar': 10.0}}, ['u1', 'u2'], [{'yeni_id': 'u4', 'sahip': 'Bob', 'miktar': 6.5}, {'yeni_id': 'u5', 'sahip': 'Alice', 'miktar': 1.5}], )])
ok(_t, "farksal tarama (utxo_islem_yurut): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def utxo_islem_yurut(mevcut_utxolar, harcanan_id_listesi, cikislar):
    if (
        not harcanan_id_listesi
        or len(set(harcanan_id_listesi)) != len(harcanan_id_listesi)
        or any(uid not in mevcut_utxolar for uid in harcanan_id_listesi)
    ):
        return {
            "onay": False,
            "hata": "GECERSIZ_UTXO_GIRDISI",
            "madenci_ucreti": 0.0,
            "yeni_utxo_sayisi": len(mevcut_utxolar),
        }

    toplam_girdi = sum(mevcut_utxolar[uid]["miktar"] for uid in harcanan_id_listesi)
    if any(c["miktar"] <= 0 for c in cikislar):
        return {
            "onay": False,
            "hata": "YETERSIZ_GIRIS_VEYA_GECERSIZ_MIKTAR",
            "madenci_ucreti": 0.0,
            "yeni_utxo_sayisi": len(mevcut_utxolar),
        }

    toplam_cikis = sum(c["miktar"] for c in cikislar)
    if toplam_cikis > toplam_girdi:
        return {
            "onay": False,
            "hata": "YETERSIZ_GIRIS_VEYA_GECERSIZ_MIKTAR",
            "madenci_ucreti": 0.0,
            "yeni_utxo_sayisi": len(mevcut_utxolar),
        }

    guncel = {k: dict(v) for k, v in mevcut_utxolar.items() if k not in harcanan_id_listesi}
    for c in cikislar:
        guncel[c["yeni_id"]] = {"sahip": c["sahip"], "miktar": c["miktar"]}

    ucret = round(toplam_girdi - toplam_cikis, 8)
    return {
        "onay": True,
        "hata": None,
        "madenci_ucreti": ucret,
        "yeni_utxo_sayisi": len(guncel),
        "guncel_utxolar": guncel,
    }
```

```hint
Önce `len(set(harcanan_id_listesi)) != len(harcanan_id_listesi)` ile tekrarlayan girdi olup olmadığını ve tüm kimliklerin `mevcut_utxolar` içinde yer aldığını kontrol et. Ardından `toplam_girdi` ve `toplam_cikis` değerlerini karşılaştırıp harcananları sil, yeni çıktıları ekle.
```
:::

::: gorev 3 · Ethereum Account-State Modeli: Nonce ile Replay Koruması
Ethereum UTXO yerine **hesap durumu** tutar: her adresin bakiyesi ve **nonce**'u vardır. Bir işlem yalnız gönderenin güncel nonce'unu taşıyorsa geçerlidir; bu, aynı imzalı işlemin tekrar yayınlanmasını (**replay**) engeller. `hesap_durumu_uygula(durum, islemler)` işlevini yaz.

**Girdiler:** `durum`: `{adres: {"bakiye": int, "nonce": int}}`; `islemler`: `{"gonderen", "alici", "miktar", "ucret", "nonce"}` sözlüklerinin listesi. Girdileri değiştirme.

**Her işlem sırayla:**
1. `gonderen` durumda yoksa → red, sebep `"hesap_yok"`.
2. `miktar < 0` ya da `ucret < 0` → red, `"gecersiz_miktar"`.
3. İşlem nonce'u gönderenin nonce'una eşit değilse → red, `"nonce"`.
4. Bakiye `miktar + ucret`'ten azsa → red, `"bakiye"`.
5. Geçerliyse: gönderenden `miktar + ucret` düş, nonce'u 1 artır; alıcıya `miktar` ekle (alıcı yoksa `{"bakiye": 0, "nonce": 0}` ile oluştur); `ucret` toplam ücrete eklenir.

**Çıktı:** `{"durum": yeni_durum, "kabul": [işlem indeksleri], "red": [[indeks, sebep], ...], "toplam_ucret": int}`.

```starter
def hesap_durumu_uygula(durum, islemler):
    # KUSURLU BAŞLANGIÇ: nonce ve bakiye denetimi yok, her işlemi kabul ediyor
    return {"durum": durum, "kabul": list(range(len(islemler))), "red": [], "toplam_ucret": 0}

print(hesap_durumu_uygula({"A": {"bakiye": 100, "nonce": 0}}, [{"gonderen": "A", "alici": "B", "miktar": 10, "ucret": 1, "nonce": 0}]))
```

```test
import copy
fn = need("hesap_durumu_uygula")
d = {"A": {"bakiye": 100, "nonce": 0}, "B": {"bakiye": 5, "nonce": 3}}
tx = {"gonderen": "A", "alici": "B", "miktar": 30, "ucret": 2, "nonce": 0}
d0, t0 = copy.deepcopy(d), copy.deepcopy([tx, tx])
r = fn(d, [tx, tx])
eq(d, d0, "durum girdisi değiştirilmemeli")
eq(r["kabul"], [0], "ilk işlem geçerli")
eq(r["red"], [[1, "nonce"]], "aynı işlemin tekrarı (replay) nonce yüzünden reddedilir")
eq(r["durum"]["A"], {"bakiye": 68, "nonce": 1}, "A: 100 - 30 - 2, nonce 1")
eq(r["durum"]["B"], {"bakiye": 35, "nonce": 3}, "B yalnız miktarı alır, nonce'u değişmez")
eq(r["toplam_ucret"], 2, "yalnız kabul edilen işlemin ücreti sayılır")
r2 = fn(d, [{"gonderen": "A", "alici": "C", "miktar": 99, "ucret": 2, "nonce": 0},
             {"gonderen": "A", "alici": "C", "miktar": 98, "ucret": 2, "nonce": 0},
             {"gonderen": "Z", "alici": "C", "miktar": 1, "ucret": 0, "nonce": 0},
             {"gonderen": "B", "alici": "A", "miktar": -1, "ucret": 0, "nonce": 3}])
eq(r2["red"], [[0, "bakiye"], [2, "hesap_yok"], [3, "gecersiz_miktar"]], "red sebepleri sırayla")
eq(r2["kabul"], [1], "98 + 2 = 100: tam bakiye yeter")
eq(r2["durum"]["C"], {"bakiye": 98, "nonce": 0}, "yeni alıcı hesabı oluşturulur")
eq(r2["durum"]["A"]["bakiye"], 0, "A'nın bakiyesi sıfırlanır")
r3 = fn({"A": {"bakiye": 10, "nonce": 0}}, [
    {"gonderen": "A", "alici": "B", "miktar": 1, "ucret": -1, "nonce": 0},
    {"gonderen": "A", "alici": "B", "miktar": 0, "ucret": 1, "nonce": 0},
    {"gonderen": "A", "alici": "B", "miktar": 2, "ucret": 0, "nonce": 1},
])
eq(r3["red"], [[0, "gecersiz_miktar"]], "Negatif ucret gecersiz_miktar ile reddedilmeli")
eq(r3["kabul"], [1, 2], "Sifir miktar veya sifir ucret gecerli kabul edilmeli")
eq(r3["durum"]["A"], {"bakiye": 7, "nonce": 2}, "Bakiye ve nonce sifir sinir islemlerinden sonra dogru")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import copy\n\ndef hesap_durumu_uygula(durum, islemler):\n    yeni = copy.deepcopy(durum)\n    kabul, red, toplam = ([], [], 0)\n    for i, tx in enumerate(islemler):\n        g, a = (tx['gonderen'], tx['alici'])\n        miktar, ucret = (tx['miktar'], tx['ucret'])\n        if g not in yeni:\n            red.append([i, 'hesap_yok'])\n        elif miktar < 0 or ucret < 0:\n            red.append([i, 'gecersiz_miktar'])\n        elif tx['nonce'] != yeni[g]['nonce']:\n            red.append([i, 'nonce'])\n        elif yeni[g]['bakiye'] < miktar + ucret:\n            red.append([i, 'bakiye'])\n        else:\n            yeni[g]['bakiye'] -= miktar + ucret\n            yeni[g]['nonce'] += 1\n            yeni.setdefault(a, {'bakiye': 0, 'nonce': 0})\n            yeni[a]['bakiye'] += miktar\n            toplam += ucret\n            kabul.append(i)\n    return {'durum': yeni, 'kabul': kabul, 'red': red, 'toplam_ucret': toplam}", 'referans', 'exec'), _REF)
_t, _g = _ff(hesap_durumu_uygula, _REF['hesap_durumu_uygula'], ({'A': {'bakiye': 100, 'nonce': 0}}, [{'gonderen': 'A', 'alici': 'B', 'miktar': 10, 'ucret': 1, 'nonce': 0}]), tohum=2977, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (hesap_durumu_uygula): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import copy

def hesap_durumu_uygula(durum, islemler):
    yeni = copy.deepcopy(durum)
    kabul, red, toplam = [], [], 0
    for i, tx in enumerate(islemler):
        g, a = tx["gonderen"], tx["alici"]
        miktar, ucret = tx["miktar"], tx["ucret"]
        if g not in yeni:
            red.append([i, "hesap_yok"])
        elif miktar < 0 or ucret < 0:
            red.append([i, "gecersiz_miktar"])
        elif tx["nonce"] != yeni[g]["nonce"]:
            red.append([i, "nonce"])
        elif yeni[g]["bakiye"] < miktar + ucret:
            red.append([i, "bakiye"])
        else:
            yeni[g]["bakiye"] -= miktar + ucret
            yeni[g]["nonce"] += 1
            yeni.setdefault(a, {"bakiye": 0, "nonce": 0})
            yeni[a]["bakiye"] += miktar
            toplam += ucret
            kabul.append(i)
    return {"durum": yeni, "kabul": kabul, "red": red, "toplam_ucret": toplam}
```

```hint
`copy.deepcopy(durum)` üzerinde çalış; denetimleri açıklamadaki sırayla `if/elif` zinciriyle yap.
```
:::

::: anlat Sınır
Görevler SHA-256 ile Merkle kökünü ve O(log N) inclusion proof'u, UTXO tüketimini, para üstünü ve fee hesabını yazdırır. Görevdeki ağaç özetleri ':' ayraçlı metin olarak birleştirip tek SHA-256 alır; gerçek Bitcoin ağacı ham baytları birleştirip çift SHA-256 kullanır ve tek sayıdaki son yaprağı kopyalar; bu kopyalama kuralı CVE-2012-2459 zayıflığına yol açmıştır. SPV doğrulaması bir işlemin blokta olduğunu gösterir, geçerli olduğunu göstermez; en uzun zincire güvenmek gerekir. Account-state görevi imzayı, gas'ı ve sözleşme yürütmesini modellemez; imza doğrulaması ve script yürütmesi UTXO motorunda modellenmez.

Kaynaklar: [Nakamoto 2008 - Bitcoin: A Peer-to-Peer Electronic Cash System](https://bitcoin.org/bitcoin.pdf), [Wood - Ethereum: A Secure Decentralised Generalised Transaction Ledger (Yellow Paper)](https://ethereum.github.io/yellowpaper/paper.pdf).
:::

::: dusun
Solana ve Sui gibi yüksek hızlı modern blokzincirler saniyede on binlerce işlemi (**`High TPS`**) paralel çekirdeklerde çalıştırabilmek için neden Ethereum'un klasik `Account` modelinden uzaklaşıp `UTXO` benzeri nesne (`Object-Centric State`) veya açık erişim listesi (`State Access Lists`) modellerine yöneldi? İki farklı işlem aynı anda çalışırken `UTXO` modelinde neden kilitlenme (**`State Contention / Race Condition`**) yaşanmaz?
:::

::: ozet
- **`Merkle Tree`**, bloktaki $N$ adet işlemi ikili özetleme ile tek bir 32 baytlık **`Merkle Root`** değerine indirger; **`SPV Light Client`** cüzdanlar tüm bloğu indirmeden sadece $\lceil \log_2 N \rceil$ kardeş özetten oluşan **`Merkle Inclusion Proof` (`Audit Path`)** ile işlemi doğrular.
- **Bitcoin `UTXO (Unspent Transaction Output)`** modelinde hesap bakiyesi sütunu yoktur; harcanmamış çıktılar atomik olarak tamamen tüketilir, alıcıya ve göndericinin kendisine (**`Change Output`**) yeni çıktılar üretilir; $\sum \text{Inputs} - \sum \text{Outputs}$ farkı doğrudan **`Miner Fee`** olur.
- **Ethereum `Account-Based State Machine`** modelinde küresel durum ağacında (`World State Trie`) her adresin `balance` ve `nonce` alanı tutulur; her işlemde artan **`Account Nonce`** sayacı imzalı işlemlerin tekrar oynatılmasını (**`Replay Attack`**) engeller.
:::
