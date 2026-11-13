---
id: kuantum-17
title: "Kripto Hacker 1: ECDSA Nonce Reuse (k Tekrarı) ile Private Key Çalma ve %51 / Selfish Mining"
track: kuantum
order: 17
duration_minutes: 45
difficulty: ileri
xp: 330
prerequisites: [kuantum-16]
tags: [ecdsa, nonce-reuse, ps3-hack, rfc-6979, 51-percent-attack, chain-reorg, selfish-mining, double-spend]
summary: "ECDSA imzalarında aynı geçici sayı (nonce k) tekrarlandığında iki imzadan özel anahtar d'yi cebirsel olarak kurtar; %51 zincir yeniden düzenleme (reorg) ve Eyal–Sirer bencil madencilik (selfish mining) gelir eşiğini hesapla."
esleme: kuantum-13, kuantum-16
---

::: anlat
## ECDSA nonce reuse

ECDSA için aynı nonce değerinin uygun koşullarda iki farklı mesajda tekrar kullanılması private key hakkında cebirsel bilgi açığa çıkarabilir. Bu derste küçük sayılarla nonce reuse hesabını ve sadeleştirilmiş chain reorg senaryosunu inceleyeceksin. Bu çalışma gerçek bir cüzdana veya ağa işlem göndermez.

**Peki ya sana, kuantum bilgisayara hiç ihtiyaç duymadan, sadece 5 satırlık modüler aritmetikle Sony PlayStation 3'ün ana imzalama anahtarının (`Master Signing Private Key`) nasıl kırıldığını ve yüzlerce Bitcoin/Ethereum cüzdanının saniyeler içinde nasıl boşaltıldığını söylesem?**

Bu derste kriptografi ve blokzincir dünyasının en yıkıcı iki gerçek dünya saldırısını (**`ECDSA Nonce Reuse Attack`** ve **`51% Chain Reorganization / Selfish Mining`**) matematiksel ve algoritmik olarak sıfırdan kodluyoruz.

---

### 1. `ECDSA (Elliptic Curve Digital Signature Algorithm)` İmza Denklemi

Bitcoin, Ethereum ve TLS sertifikalarında kullanılan **`ECDSA`** algoritmasında:
- Eğrinin mertebesi (**`Curve Order`**) $n$ asal bir sayıdır, $G$ üreteç noktasıdır (**`Generator Point`**).
- Kullanıcının gizli anahtarı (**`Private Key`**) $d \in [1, n-1]$ tam sayısıdır; açık anahtarı (**`Public Key`**) ise $Q = d \cdot G$ noktasıdır.

Kullanıcı özeti $z = \text{SHA256}(m)$ olan bir mesajı imzalarken şu 3 adımı uygular:
1. Her imza için **tamamen rastgele ve tek kullanımlık bir gizli sayı (`Ephemeral Nonce`)** $k \in [1, n-1]$ seçer!
2. Eğri üzerinde $R = k \cdot G = (x_R, y_R)$ noktasını hesaplar ve imzanın ilk yarısını $r = x_R \bmod n$ olarak alır.
3. İmzanın ikinci yarısı olan $s$ değerini şu modüler denklemle hesaplar:

$$s \equiv k^{-1} (z + r \cdot d) \pmod n$$

Dünyaya yayınlanan açık imza $(r, s)$ ikilisidir. Normal şartlarda dışarıdan bakan bir saldırgan $z, r, s$ ve $n$ değerlerini bilir ama denklemin içinde **iki adet bilinmeyen** vardır: geçici $k$ (`Nonce`) ve kalıcı özel anahtar $d$ (`Private Key`). Tek bir denklemde iki bilinmeyen olduğu için denklem çözülemez!

---

### 2. Felaket Senaryosu: `ECDSA Nonce Reuse Attack` ($k$ Tekrarı İstismarı)

Şimdi cüzdan yazılımcısının veya donanım üreticisinin rastgele sayı üretecinde (**`CSPRNG — Cryptographically Secure Pseudo-Random Number Generator`**) bir hata yaptığını ve **iki farklı mesajı ($z_1 \neq z_2$) imzalarken yanlışlıkla aynı $k$ (`Nonce`) sayısını kullandığını** düşün!

1. İki imzada da aynı $k$ kullanıldığı için $R = k \cdot G$ noktası aynı çıkar; yani blokzincirde yayınlanan iki imzanın da **$r$ değerleri birebir aynıdır**: $(r, s_1)$ ve $(r, s_2)$! (Blokzinciri tarayan bir hacker, aynı adresten çıkan iki işlemde aynı $r$ değerini gördüğü salisede alarm zillerini çalar!).
2. Şimdi elimizde **iki denklem ve iki bilinmeyen ($k$ ve $d$)** vardır:
   $$s_1 \equiv k^{-1}(z_1 + r \cdot d) \pmod n \quad \Longrightarrow \quad k \cdot s_1 \equiv z_1 + r \cdot d \pmod n$$
   $$s_2 \equiv k^{-1}(z_2 + r \cdot d) \pmod n \quad \Longrightarrow \quad k \cdot s_2 \equiv z_2 + r \cdot d \pmod n$$
3. İki denklemi birbirinden çıkardığımızda $r \cdot d$ terimleri birbirini götürür!
   $$k \cdot (s_1 - s_2) \equiv (z_1 - z_2) \pmod n$$
4. Buradan gizli $k$ (`Nonce`) değerini modüler ters (`pow(s1 - s2, -1, n)`) ile anında çekeriz:
   $$k \equiv (z_1 - z_2) \cdot (s_1 - s_2)^{-1} \pmod n$$
5. Ve $k$'yı bildiğimiz an birinci denklemde yerine koyup **kurbanın `Private Key` ($d$) anahtarını 1 milisaniyede ele geçiririz:**

$$d \equiv r^{-1} \cdot (s_1 \cdot k - z_1) \pmod n$$

```
┌────────────────────────────────────────────────────────────────────────────┐
│            GERÇEK DÜNYA VAKALARI: NONCE REUSE (k TEKRARI) FELAKETLERİ      │
├──────────────────────────────────────┬─────────────────────────────────────┤
│ 🎮 SONY PLAYSTATION 3 HACK (2010)    │ 🪙 ANDROID BITCOIN WALLET HACK (2013)│
│ • `fail0verflow` ekibi, Sony'nin     │ • Android `SecureRandom` PRNG       │
│   PS3 oyunlarını imzalarken `k`      │   hatası yüzünden binlerce cüzdan   │
│   değerini rastgele üretmek yerine   │   aynı `r` değeriyle işlem          │
│   SABİT (statik) bir sayı olarak     │   imzaladı; botlar blokzinciri      │
│   kodladığını fark etti!             │   tarayıp özel anahtarları saniyeler│
│ • Sadece iki yazılım güncelleme      │   içinde çözerek tüm BTC'leri çaldı!│
│   imzasını birbirinden çıkararak     │                                     │
│   Sony'nin Master Private Key'ini    │ 🛡️ KESİN SAVUNMA: RFC 6979          │
│   kağıt-kalemle buldular!            │ • `k = HMAC_DRBG(Private_Key, z)`   │
└──────────────────────────────────────┴─────────────────────────────────────┘
```

#### 🛡️ Kesin Mühendislik Savunması: `RFC 6979 Deterministic ECDSA`
Donanım gürültüsüne (`Entropy Source`) güvenmek tehlikelidir. **Thomas Pornin** tarafından yazılan **`RFC 6979`** standardı, $k$ sayısını rastgele zar atarak değil, **özel anahtar $d$ ve mesaj özeti $z$'nin deterministik `HMAC-SHA256` özeti olarak** üretir:
- Aynı mesaj imzalanırsa aynı $k$ ve aynı imza çıkar (zararsızdır, çünkü $z_1 = z_2$ olduğunda $z_1 - z_2 = 0$ olur ve denklem bilgi sızdırmaz).
- Deterministic nonce üretimi uygun secret/message girdileriyle RNG kaynaklı tekrar riskini azaltır. Hash/PRF ve implementation varsayımları sürer; farklı bütün mesajlarda çakışmanın matematiksel olarak imkânsız olduğu söylenmez.

```python
# ECDSA Nonce Reuse (k Tekrari) Saldirisi: Iki Acik Imzadan Private Key (d) Calma!
n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141  # secp256k1 order
gizli_d = 98765432101234567890987654321  # Kurbanin Private Key'i (Saldirgan bunu bilmiyor!)
tekrarlanan_k = 111222333444555666777    # Hatali CSPRNG yuzunden iki kez kullanilan k!
r = 555666777888999000111222333444       # (k * G).x mod n

# Kurban iki farkli islem (z1 ve z2) imzalayip blokzincire gonderiyor:
z1, z2 = 4000001, 9000002
k_ters = pow(tekrarlanan_k, -1, n)
s1 = (k_ters * (z1 + r * gizli_d)) % n
s2 = (k_ters * (z2 + r * gizli_d)) % n

# --- HACKER SAHNEDE: Sadece acik (z1, s1, z2, s2, r, n) degerlerine bakiyor! ---
kurtarilan_k = ((z1 - z2) * pow(s1 - s2, -1, n)) % n
calinan_d = (pow(r, -1, n) * (s1 * kurtarilan_k - z1)) % n
print(f"k Bulundu mu?: {kurtarilan_k == tekrarlanan_k} | Private Key Calindi mi?: {calinan_d == gizli_d}")
```

---

### 3. `%51 Saldırısı (Majority Hash Rate Attack)` ve `Chain Reorganization`

Şu teknik ayrımı inceleyelim:

Şimdi bir kripto konferansında en çok sorulan ikinci hacker sorusuna gelelim:
> *"Hocam, bir devlet veya devasa bir madenci havuzu Bitcoin ağındaki toplam işlem gücünün (`Hash Rate`) %51'ini ele geçirirse ne yapabilir? Satoshi'nin cüzdanındaki paraları çalabilir mi?"*

**Çok Kritik Ayrım:** `%51 Saldırısı` yapan birisi **başkasının `Private Key`'ini kıramaz**, başkasının cüzdanından imzasız para transfer edemez veya yoktan 21 milyon sınırını aşan Bitcoin üretemez! (Çünkü dürüst `Full Node`'lar kriptografik imzası geçersiz olan veya kural dışı blokları ne kadar uzun olursa olsun reddeder!).

#### 🎯 Peki `%51 Saldırganı` Ne Yapabilir? — `Double-Spend via Chain Reorganization (Reorg)`
**`Nakamoto Consensus`** kuralına göre düğümler her zaman **en fazla kümülatif `Proof-of-Work` içeren en uzun geçerli zinciri (`Longest / Heaviest Valid Chain`)** gerçek kabul eder:
1. Saldırgan borsaya **1.000 BTC** gönderir (`TX_Borsa`) ve bu işlem dürüst madencilerin kazdığı **Açık Zincire (`Public Honest Chain`)** girer.
2. Borsa işlemin üzerine $k = 6$ blok onay (**`6 Confirmations`**) gelmesini bekler. Dürüst zincir 6 blok ilerlediğinde borsa saldırgana karşılığında **70 Milyon USDT** verir ve saldırgan parayı başka ağa çekip kaçar.
3. Oysa saldırgan bu 6 blok süresince, elindeki **%51+ `Hash Rate`** gücüyle aynı 1.000 BTC'yi **kendi başka bir cüzdanına geri gönderen (`TX_Kendine`)** alternatif bir **Gizli Zinciri (`Secret Fork Chain`)** dış dünyaya duyurmadan paralel olarak kazmıştır!
4. Saldırganın gizli zinciri dürüst zinciri **1 blok geçtiği an** (örneğin dürüst zincir 6 blokken gizli zincir 7 blok olduğunda), saldırgan gizli zincirini tüm ağa yayınlar.
5. Tüm düğümler *"Aaa, burada 7 blokluk daha uzun ve geçerli bir zincir var!"* diyerek 6 blokluk eski dürüst zinciri çöpe atar (**`Chain Reorganization / Orphaned Blocks`**)! Böylece borsaya giden `TX_Borsa` işlemi tarihten silinir; saldırgan hem 70 Milyon Doları hem de 1.000 BTC'sini cebinde tutar!

#### 🕵️ `Selfish Mining` (Eyal & Sirer, 2014): %51 Bile Gerekmeden %33 İle Saldırmak!
Cornell Üniversitesi'nden **Ittay Eyal** ve **Emin Gün Sirer**, bir madencinin ağa hükmetmek için %51'e bile ihtiyacı olmadığını kanıtladı:
- **`Selfish Mining` (Bencil Madencilik):** Ağın sadece **$\ge \%33.3$ (`1/3`)** gücüne sahip (yarışta dürüst madencilerin havuzun bloğunu hiç seçmediği $\gamma = 0$ varsayımıyla; $\gamma$ büyüdükçe eşik düşer) bir madenci, bulduğu bloğu hemen yayınlamak yerine **gizli tutar (`Block Withholding`)**.
- Dürüst madenciler boşuna eski blok üzerinde elektrik harcarken bencil madenci 2 blok öne geçer; dürüstler 1 blok bulduğu an bencil madenci elindeki 2 gizli bloğu peş peşe yayınlayarak dürüstlerin bloğunu yetim (**`Orphan Block`**) bırakır ve dürüst madencilerin emeğinin bir kısmını boşa çıkararak gelirdeki payını hash gücü payının üstüne çıkarır!

**Kaynak ve sınır:** [RFC 6979: deterministic ECDSA](https://datatracker.ietf.org/doc/html/rfc6979). Sayısal örnekler eğitim ölçeğindedir; gerçek cüzdanlar, imzalama donanımı veya ağ üzerindeki bir blokzincir hedefi üzerinde kabul testi yapılmaz.
:::

::: tahmin ECDSA Nonce Reuse Saldırısında (s1 - s2) Farkı
Küçük bir sonlu cisim modeli ($\bmod\; 23$) üzerinde `ECDSA` imzası test ediliyor ($n = 23$, ortak $r = 7$). Aynı $k$ (`Nonce`) değeriyle imzalanmış iki farklı mesajın özetleri $z_1 = 10, z_2 = 4$ ve imzaları $s_1 = 9, s_2 = 6$ olarak yakalanmıştır. Saldırganın $k \equiv (z_1 - z_2)(s_1 - s_2)^{-1} \pmod{23}$ formülüyle bulacağı gizli $k$ değeri nedir?

```python
n = 23
z1, s1 = 10, 9
z2, s2 = 4, 6

k = ((z1 - z2) * pow(s1 - s2, -1, n)) % n
print(f"Kurtarilan Nonce k = {k}")
```

???

```cikti
Kurtarilan Nonce k = 2
```
$z_1 - z_2 = 10 - 4 = 6$ ve $s_1 - s_2 = 9 - 6 = 3$ olur. Bu durumda $k \equiv 6 \cdot 3^{-1} \equiv 2 \pmod{23}$ olarak doğrudan ortaya çıkar!
:::

::: gorev 1 · ECDSA Nonce Reuse (k Tekrarı) İstismarıyla İki İmzadan Private Key (d) Kurtarma
Blokzincirde aynı $r$ değerini paylaşan iki imzayı yakalayıp kurbanın özel anahtarını ($d$) çıkaran `ecdsa_nonce_reuse_kir(z1, s1, z2, s2, r, grup_n)` fonksiyonunu yaz.

**Matematiksel Denklemler ($\pmod{\text{grup\_n}}$):**
1. Eğer `s1 == s2` veya `r % grup_n == 0` ise modüler ters alınamaz; fonksiyon `{"basarili": False, "nonce_k": None, "ozel_anahtar_d": None}` döndürmelidir.
2. Geçici anahtar (`Nonce`):
   $$k = (z_1 - z_2) \cdot (s_1 - s_2)^{-1} \bmod \text{grup\_n}$$
3. Özel anahtar (`Private Key`):
   $$d = r^{-1} \cdot (s_1 \cdot k - z_1) \bmod \text{grup\_n}$$
4. Doğrulama kontrolü ve dönüş sözlüğü:
   `{"basarili": True, "nonce_k": k, "ozel_anahtar_d": d}`

```starter
def ecdsa_nonce_reuse_kir(z1, s1, z2, s2, r, grup_n):
    # TODO: Iki ECDSA imzasindan (z1, s1) ve (z2, s2) once k nonce degerini, sonra d ozel anahtarini coz
    return {
        "basarili": False,
        "nonce_k": None,
        "ozel_anahtar_d": None,
    }
```

```test
fn = need("ecdsa_nonce_reuse_kir")

# Test 1: secp256k1 mertebesinde gercek 256-bit sayilarla ozel anahtar kurtarma
N_SECP = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
gercek_d = 0x4A9B8C7D6E5F4A3B2C1D0E9F8A7B6C5D4E3F2A1B0C9D8E7F6A5B4C3D2E1F0A9B
gercek_k = 0x123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0
ortak_r  = 0x7F8E9D0C1B2A394857667584930211203F4E5D6C7B8A99081726354453627180
z_a = 0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
z_b = 0x5555555555555555555555555555555555555555555555555555555555555555

s_a = (pow(gercek_k, -1, N_SECP) * (z_a + ortak_r * gercek_d)) % N_SECP
s_b = (pow(gercek_k, -1, N_SECP) * (z_b + ortak_r * gercek_d)) % N_SECP

sonuc1 = fn(z_a, s_a, z_b, s_b, ortak_r, N_SECP)
eq(sonuc1["basarili"], True, "Farkli iki imzada saldiri basarili olmali")
eq(sonuc1["nonce_k"], gercek_k, "Gizli nonce k tam olarak kurtarilmali")
eq(sonuc1["ozel_anahtar_d"], gercek_d, "256-bitlik Private Key d tam olarak kurtarilmali")

# Test 2: Kucuk asal modda kontrol
n2 = 101
d2, k2, r2 = 73, 41, 19
z2_1, z2_2 = 15, 88
s2_1 = (pow(k2, -1, n2) * (z2_1 + r2 * d2)) % n2
s2_2 = (pow(k2, -1, n2) * (z2_2 + r2 * d2)) % n2
sonuc2 = fn(z2_1, s2_1, z2_2, s2_2, r2, n2)
eq(sonuc2["nonce_k"], k2, "Mod 101 uzerinde k=41 bulunmali")
eq(sonuc2["ozel_anahtar_d"], d2, "Mod 101 uzerinde d=73 bulunmali")

# Test 3: Ayni mesaj imzalanmissa (s1 == s2) bilgi sizmaz, basarili=False donmeli
sonuc3 = fn(z2_1, s2_1, z2_1, s2_1, r2, n2)
eq(sonuc3["basarili"], False, "s1 == s2 oldugunda moduler ters alinamaz, basarili=False olmali")
eq(sonuc3["ozel_anahtar_d"], None, "Basarisiz durumda ozel_anahtar_d None olmali")
eq(fn(z2_1, s2_1, z2_2, s2_2, 0, n2), {"basarili": False, "nonce_k": None, "ozel_anahtar_d": None}, "r % grup_n == 0 oldugunda moduler ters alinamaz, basarili=False donmeli")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def ecdsa_nonce_reuse_kir(z1, s1, z2, s2, r, grup_n):\n    fark_s = (s1 - s2) % grup_n\n    if fark_s == 0 or r % grup_n == 0:\n        return {'basarili': False, 'nonce_k': None, 'ozel_anahtar_d': None}\n    nonce_k = (z1 - z2) * pow(fark_s, -1, grup_n) % grup_n\n    ozel_d = pow(r, -1, grup_n) * (s1 * nonce_k - z1) % grup_n\n    return {'basarili': True, 'nonce_k': nonce_k, 'ozel_anahtar_d': ozel_d}", 'referans', 'exec'), _REF)
_t, _g = _ff(ecdsa_nonce_reuse_kir, _REF['ecdsa_nonce_reuse_kir'], (77194726158210796949047323339125271902179989777093709359638389338608753093290, 26738435603415978225737294942624297377257010461268171821008204775287752981487, 38597363079105398474523661669562635951089994888546854679819194669304376546645, 106095338848152565851325652809351962403106426509846520503356127204466523339979, 57695707953829969745001113217119817096828108920660621711567829750348012220800, 115792089237316195423570985008687907852837564279074904382605163141518161494337), tohum=3124, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (ecdsa_nonce_reuse_kir): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def ecdsa_nonce_reuse_kir(z1, s1, z2, s2, r, grup_n):
    fark_s = (s1 - s2) % grup_n
    if fark_s == 0 or (r % grup_n) == 0:
        return {
            "basarili": False,
            "nonce_k": None,
            "ozel_anahtar_d": None,
        }

    nonce_k = ((z1 - z2) * pow(fark_s, -1, grup_n)) % grup_n
    ozel_d = (pow(r, -1, grup_n) * (s1 * nonce_k - z1)) % grup_n

    return {
        "basarili": True,
        "nonce_k": nonce_k,
        "ozel_anahtar_d": ozel_d,
    }
```

```hint
Önce `fark_s = (s1 - s2) % grup_n` değerini hesapla; `0` ise `basarili: False` döndür. Değilse `pow(fark_s, -1, grup_n)` ile modüler tersini alıp `(z1 - z2)` ile çarparak `nonce_k` değerini bul, ardından `pow(r, -1, grup_n) * (s1 * nonce_k - z1) % grup_n` ile `ozel_d` değerini çıkar.
```
:::

::: gorev 2 · %51 Çifte Harcama (Chain Reorg) ve En Uzun Zincir (Nakamoto Consensus) Simülatörü
Bir kripto borsasının maruz kaldığı gizli zincir (**`Secret Fork / 51% Attack`**) saldırısında **`Chain Reorganization (Reorg)`** ve **`Double-Spend`** gerçekleşip gerçekleşmeyeceğini analiz eden `zincir_reorg_analiz(durust_zincir_uzunlugu, gizli_saldirgan_zinciri, onay_bekleme_k)` fonksiyonunu yaz.

**Girdiler:**
- `durust_zincir_uzunlugu`: İşlem bloğa girdikten sonra dürüst madencilerin açık zincirde ürettiği blok sayısı (`int`).
- `gizli_saldirgan_zinciri`: Saldırganın aynı sürede gizlice kazdığı alternatif dalın blok sayısı (`int`).
- `onay_bekleme_k`: Borsanın parayı serbest bırakmak için beklediği minimum onay (`Confirmation`) sayısı (`int`).

**Kurallar ve Çıktı Sözlüğü (`dict`):**
1. `"borsa_odeme_yapti_mi"`: Dürüst zincir uzunluğu borsanın beklediği onay sayısına ulaştıysa (`durust_zincir_uzunlugu >= onay_bekleme_k`) `True`, aksi halde `False`.
2. `"reorg_gerceklesti_mi"`: `Nakamoto Consensus` gereği gizli zincir dürüst zincirden **kesinlikle daha uzunsa** (`gizli_saldirgan_zinciri > durust_zincir_uzunlugu`) `True`, aksi halde `False`.
3. `"cifte_harcama_basarili"`: Hem borsa ödemeyi yaptıysa (`borsa_odeme_yapti_mi == True`) hem de gizli zincir dürüst zinciri geçip `Reorg` yarattıysa (`reorg_gerceklesti_mi == True`) `True`, aksi halde `False`.
4. `"yetim_kalan_blok_sayisi"`: Eğer `reorg_gerceklesti_mi == True` ise dürüst zincirdeki tüm bloklar yetim (`Orphaned`) kalacağı için `durust_zincir_uzunlugu`, aksi halde `0`.

```starter
def zincir_reorg_analiz(durust_zincir_uzunlugu, gizli_saldirgan_zinciri, onay_bekleme_k):
    # TODO: Nakamoto Consensus en uzun zincir kuralina gore Reorg ve Double-Spend durumunu hesapla
    return {
        "borsa_odeme_yapti_mi": False,
        "reorg_gerceklesti_mi": False,
        "cifte_harcama_basarili": False,
        "yetim_kalan_blok_sayisi": 0,
    }
```

```test
fn = need("zincir_reorg_analiz")

# 1) Klasik basarili %51 Double-Spend: Borsa 6 onay bekliyor, durust 6 blok kazdi, saldirgan gizlice 7 blok kazdi!
r1 = fn(6, 7, 6)
eq(r1["borsa_odeme_yapti_mi"], True, "6 >= 6 oldugu icin borsa odemeyi serbest birakmali")
eq(r1["reorg_gerceklesti_mi"], True, "7 > 6 oldugu icin gizli zincir Reorg yaratmali")
eq(r1["cifte_harcama_basarili"], True, "Hem odeme alindi hem Reorg oldu -> Double-Spend basarili")
eq(r1["yetim_kalan_blok_sayisi"], 6, "6 durust blok yetim (orphan) kalmali")

# 2) Esit uzunluk durumu (6 vs 6): Kesin ustunluk yok, Reorg gerceklesmez
r2 = fn(6, 6, 6)
eq(r2["reorg_gerceklesti_mi"], False, "Esit blok sayisinda (6 == 6) kesin Reorg gerceklesmez")
eq(r2["cifte_harcama_basarili"], False, "Reorg olmayinca cifte harcama basarisiz olmali")
eq(r2["yetim_kalan_blok_sayisi"], 0, "Reorg olmadiginda yetim blok sayisi 0 olmali")

# 3) Saldirgan gizli zinciri erken yayinladi (Borsa 6 onay bekliyor ama durust zincir henuz 4 blokta)
r3 = fn(4, 5, 6)
eq(r3["borsa_odeme_yapti_mi"], False, "4 < 6 oldugu icin borsa henuz odeme yapmadi")
eq(r3["reorg_gerceklesti_mi"], True, "5 > 4 oldugu icin zincir degisir")
eq(r3["cifte_harcama_basarili"], False, "Borsa odeme yapmadigi icin Double-Spend vurgunu gerceklesmedi")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def zincir_reorg_analiz(durust_zincir_uzunlugu, gizli_saldirgan_zinciri, onay_bekleme_k):\n    odeme = durust_zincir_uzunlugu >= onay_bekleme_k\n    reorg = gizli_saldirgan_zinciri > durust_zincir_uzunlugu\n    cifte_harcama = odeme and reorg\n    yetim = durust_zincir_uzunlugu if reorg else 0\n    return {'borsa_odeme_yapti_mi': odeme, 'reorg_gerceklesti_mi': reorg, 'cifte_harcama_basarili': cifte_harcama, 'yetim_kalan_blok_sayisi': yetim}", 'referans', 'exec'), _REF)
_t, _g = _ff(zincir_reorg_analiz, _REF['zincir_reorg_analiz'], (6, 7, 6), tohum=2949, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (zincir_reorg_analiz): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def zincir_reorg_analiz(durust_zincir_uzunlugu, gizli_saldirgan_zinciri, onay_bekleme_k):
    odeme = durust_zincir_uzunlugu >= onay_bekleme_k
    reorg = gizli_saldirgan_zinciri > durust_zincir_uzunlugu
    cifte_harcama = odeme and reorg
    yetim = durust_zincir_uzunlugu if reorg else 0

    return {
        "borsa_odeme_yapti_mi": odeme,
        "reorg_gerceklesti_mi": reorg,
        "cifte_harcama_basarili": cifte_harcama,
        "yetim_kalan_blok_sayisi": yetim,
    }
```

```hint
`odeme = durust_zincir_uzunlugu >= onay_bekleme_k` ve `reorg = gizli_saldirgan_zinciri > durust_zincir_uzunlugu` koşullarını ayrı ayrı hesapla. Çifte harcamanın başarılı olması için ikisinin de `True` olması gerekir.
```
:::

::: gorev 3 · Selfish Mining: Eyal–Sirer Gelir Oranı ve Kârlılık Eşiği
Eyal ve Sirer (2014), bulduğu blokları saklayıp stratejik yayınlayan bir madenci havuzunun **%51'in çok altında** bile payından fazla kazanabileceğini gösterdi. `selfish_mining_gelir(alfa, gama)` işlevini yaz.

**Girdiler:** `alfa`: havuzun hash gücü payı, $0 \le \alpha < 0.5$; `gama`: yarış anında dürüst madencilerin havuzun bloğu üzerine kazma oranı, $0 \le \gamma \le 1$. Sayı olmayan, `bool` ya da aralık dışı değerde `ValueError`.

**Formüller:**
$$R = \frac{\alpha(1-\alpha)^2\big(4\alpha + \gamma(1-2\alpha)\big) - \alpha^3}{1 - \alpha\big(1 + (2-\alpha)\alpha\big)}, \qquad \alpha_{\text{eşik}} = \frac{1-\gamma}{3-2\gamma}$$

**Çıktı:** `"goreli_gelir"` ($R$), `"durust_gelir"` ($\alpha$), `"esik_alfa"` (sayılar `round(·, 6)`), `"karli_mi"`: $R > \alpha + 10^{-12}$.

```starter
def selfish_mining_gelir(alfa, gama):
    # KUSURLU BAŞLANGIÇ: saklama stratejisinin dürüst kazmayla aynı kazandırdığını varsayıyor
    return {"goreli_gelir": round(alfa, 6), "durust_gelir": round(alfa, 6), "esik_alfa": 0.5, "karli_mi": False}

print(selfish_mining_gelir(0.4, 0.0))
```

```test
fn = need("selfish_mining_gelir")
r = fn(1 / 3, 0.0)
eq(r["goreli_gelir"], 0.333333, "γ = 0'da eşik α = 1/3: gelir tam payına eşit")
eq(r["durust_gelir"], 0.333333, "dürüst gelir 6 basamağa yuvarlanmalı")
eq(r["esik_alfa"], 0.333333, "eşik (1 - 0) / (3 - 0) = 1/3")
eq(r["karli_mi"], False, "eşikte kâr yok")
r2 = fn(0.4, 0.0)
eq(r2["goreli_gelir"], 0.483721, "α = 0.4: 0.1664 / 0.344")
eq(r2["karli_mi"], True, "eşiğin üstünde payından fazla kazanır")
r3 = fn(0.25, 0.5)
eq(r3["esik_alfa"], 0.25, "γ = 0.5'te eşik 0.25")
eq(r3["goreli_gelir"], 0.25, "eşikte gelir payına eşit")
r4 = fn(0.1, 1.0)
eq(r4["esik_alfa"], 0.0, "γ = 1: her havuz kârlı")
eq(r4["goreli_gelir"], 0.109194, "α = 0.1, γ = 1: 0.0962 / 0.881")
eq(r4["karli_mi"], True, "γ = 1'de %10 bile kârlı")
eq(fn(0.0, 0.5)["goreli_gelir"], 0.0, "α = 0 gelir 0")
raises(ValueError, fn, 0.5, 0.0)
raises(ValueError, fn, 0.3, 1.5)
raises(ValueError, fn, True, 0.0)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef selfish_mining_gelir(alfa, gama):\n    for v in (alfa, gama):\n        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):\n            raise ValueError('alfa ve gama sonlu sayı olmalı')\n    if not 0.0 <= alfa < 0.5 or not 0.0 <= gama <= 1.0:\n        raise ValueError('0 <= alfa < 0.5 ve 0 <= gama <= 1 olmalı')\n    pay = alfa * (1 - alfa) ** 2 * (4 * alfa + gama * (1 - 2 * alfa)) - alfa ** 3\n    payda = 1 - alfa * (1 + (2 - alfa) * alfa)\n    r = pay / payda\n    esik = (1 - gama) / (3 - 2 * gama)\n    return {'goreli_gelir': round(r, 6), 'durust_gelir': round(alfa, 6), 'esik_alfa': round(esik, 6), 'karli_mi': r > alfa + 1e-12}", 'referans', 'exec'), _REF)
_t, _g = _ff(selfish_mining_gelir, _REF['selfish_mining_gelir'], (0.4, 0.0), tohum=3035, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (selfish_mining_gelir): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def selfish_mining_gelir(alfa, gama):
    for v in (alfa, gama):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError("alfa ve gama sonlu sayı olmalı")
    if not (0.0 <= alfa < 0.5) or not (0.0 <= gama <= 1.0):
        raise ValueError("0 <= alfa < 0.5 ve 0 <= gama <= 1 olmalı")
    pay = alfa * (1 - alfa) ** 2 * (4 * alfa + gama * (1 - 2 * alfa)) - alfa ** 3
    payda = 1 - alfa * (1 + (2 - alfa) * alfa)
    r = pay / payda
    esik = (1 - gama) / (3 - 2 * gama)
    return {"goreli_gelir": round(r, 6), "durust_gelir": round(alfa, 6),
            "esik_alfa": round(esik, 6), "karli_mi": r > alfa + 1e-12}
```

```hint
Payı ve paydayı ayrı değişkenlerde hesapla; kârlılığı yuvarlanmamış R ile karşılaştır.
```
:::

::: anlat Sınır
Görevler aynı nonce (k) ile atılmış iki imzadan özel anahtarı kurtarmayı ve %51 reorg simülasyonunu yazdırır. Görev imza denklemini yalnız modüler aritmetikle kurar: testte secp256k1'in gerçek grup mertebesi n kullanılsa da r değeri bir eğri noktasından (k·G) hesaplanmaz ve imzalar gerçek bir kütüphaneyle doğrulanmaz. Pratikte tam k tekrarı nadirdir, ama k'nın birkaç biti bile sızarsa ya da k yanlı üretilirse kafes saldırısıyla anahtar kurtarılabilir; RFC 6979 deterministik nonce bu sınıfı kapatır. Selfish mining görevi Eyal–Sirer'in kapalı form gelirini hesaplar, ağ gecikmesini ve birden çok havuzun dengesini modellemez; %51 simülasyonu ağ gecikmesini ve madenci davranışını modellemez.

Kaynaklar: [Breitner ve Heninger 2019 - Biased Nonce Sense: Lattice Attacks against Weak ECDSA Signatures in Cryptocurrencies](https://eprint.iacr.org/2019/023), [Eyal ve Sirer 2014 - Majority is not Enough: Bitcoin Mining is Vulnerable](https://arxiv.org/abs/1311.0243), [SECG 2010 - SEC 2: Recommended Elliptic Curve Domain Parameters](https://www.secg.org/sec2-v2.pdf).
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Kriptografik sistemler çoğu zaman kuramsal eğri kırıldığı için değil, uygulama ve mutabakat varsayımları ihlal edildiği için çöker. ECDSA'da iki farklı mesaj yanlışlıkla aynı geçici $k$ (nonce) ile imzalanırsa iki imzanın $r$ bileşeni aynı çıkar; saldırgan iki doğrusal denklemi birbirinden çıkararak önce $k$'yı, ardından kalıcı özel anahtar $d$'yi milisaniyede hesaplar — RFC 6979 deterministik nonce bu RNG hatasını kökünden kapatır.

Zincir katmanında ise %51 gücü başkasının imzasını taklit edemez ama gizli dal kazıp daha uzun zincir yayınlayarak onaylanmış ödemeleri geri sarabilir (chain reorg / çifte harcama); Eyal–Sirer bencil madencilik analizi ise blok saklama stratejisiyle %33,3 eşiğinden itibaren bile dürüst madencilerin payının aşındırılabildiğini gösterir.
:::

::: dusun
2018-2020 yıllarında `Ethereum Classic (ETC)` ve `Bitcoin Gold (BTG)` gibi daha küçük `Proof-of-Work` ağları defalarca **`%51 Double-Spend`** saldırısına uğrayıp borsalardan milyonlarca dolar çalınırken, neden **Bitcoin** ana ağında bu saldırı hiç başarılı olamadı? Ayrıca borsalar küçük PoW ağlarında kendilerini korumak için `onay_bekleme_k` sayısını neden `6`'dan `500` hatta `3.000` bloğa çıkardı?
:::

::: ozet
- **`ECDSA`** imzalama denkleminde ($s \equiv k^{-1}(z + r \cdot d) \pmod n$) iki farklı mesaj ($z_1 \neq z_2$) aynı geçici **`Nonce` ($k$)** ile imzalanırsa iki imzanın $r$ değeri aynı olur; saldırgan $k \equiv (z_1 - z_2)(s_1 - s_2)^{-1} \pmod n$ ve ardından $d \equiv r^{-1}(s_1 k - z_1) \pmod n$ formülüyle **Private Key ($d$)** anahtarını anında ele geçirir.
- **`Nonce Reuse`** zafiyetine karşı endüstri standardı savunma **`RFC 6979 Deterministic ECDSA`** protokolüdür; $k$ değeri rastgele üreteç yerine özel anahtar ve mesaj özetinin `HMAC` çıktısı olarak deterministik üretilir.
- **`%51 Saldırısı`** başkasının özel anahtarını kıramaz ancak gizlice daha uzun bir alternatif dal kazıp yayınlayarak **`Chain Reorganization (Reorg)`** ve **`Double-Spend`** yaratabilir; **`Selfish Mining`** ise blokları gizleyerek (`Block Withholding`) %33.3 güçle bile dürüst madencilerin bloklarını yetim (`Orphan`) bırakabilir.
:::
