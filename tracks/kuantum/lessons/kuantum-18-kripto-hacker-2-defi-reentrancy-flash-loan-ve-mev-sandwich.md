---
id: kuantum-18
title: "Kripto Hacker 2 (DeFi Exploits): Smart Contract Reentrancy, Flash Loan Oracle ve MEV Sandwich"
track: kuantum
order: 18
duration_minutes: 45
difficulty: ileri
xp: 340
prerequisites: [kuantum-17]
tags: [defi-security, reentrancy, checks-effects-interactions, amm, flash-loan, oracle-manipulation, mev-sandwich]
summary: "Sabit çarpımlı AMM (x·y=k) üzerinde MEV sandwich kârını, akıllı sözleşme reentrancy istismarına karşı Checks-Effects-Interactions (CEI) savunmasını ve flash loan spot fiyat oracle manipülasyonuna karşı TWAP etkisini modelle."
esleme: kuantum-16, kuantum-17
---

::: anlat
## DeFi işlem sırası ve state güncellemesi

AMM rezerv değişimi ile reentrancy, farklı güven sınırlarından kaynaklanır. Bu derste işlem sırasının takas sonucunu nasıl değiştirdiğini ve state güncellemesini external call öncesine almanın etkisini küçük modellerle hesaplayacaksın. Python modeli gerçek EVM execution, gas veya bütün DeFi risklerini kapsamaz.

Bu derste DeFi tarihinin en meşhur 3 saldırı mekaniğini ve savunma mimarilerini sıfırdan modelliyoruz:
1. **`Reentrancy Attack` (Yeniden Giriş Saldırısı — *The DAO Hack*):** Bakiye sıfırlanmadan önce dış çağrı yapıldığında kasanın özyinelemeli (`Recursive`) olarak boşaltılması ve **`Checks-Effects-Interactions (CEI)`** savunması,
2. **`Constant Product AMM` ($x \cdot y = k$) & `Flash Loan Price Oracle Manipulation`:** Sıfır teminatla 100 milyon dolar borç alıp havuz fiyatını bükerek protokol soymak ve **`TWAP / Chainlink`** savunması,
3. **`MEV (Maximal Extractable Value) Sandwich Attack`:** `Mempool`'da bekleyen kurbanın işlemini **`Front-run`** ve **`Back-run`** arasına sıkıştırarak risksiz kâr çekmek!

---

### 1. `Reentrancy Attack` (Yeniden Giriş Saldırısı) ve *The DAO Hack* (2016)

2016 yılında Ethereum üzerindeki **The DAO** fonunda 150 Milyon Dolar değerinde ETH toplanmıştı (o dönem tüm Ethereum arzının %14'ü!). Bir saldırgan, sözleşmenin `withdraw()` (para çekme) fonksiyonundaki **2 satırın sırasının yanlış olmasını** kullanarak 3.6 Milyon ETH çaldı ve bu olay Ethereum'un `ETH` ve `ETC (Ethereum Classic)` olarak ikiye bölünmesine (**`Hard Fork`**) yol açtı!

```
┌──────────────────────────────────────────────────────────────────────────────┐
│   ❌ ZAFİYETLİ KOD (EXTERNAL CALL ÖNCE)    │  ✅ GÜVENLİ KOD (CEI PATTERN)    │
├───────────────────────────────────────────┼──────────────────────────────────┤
│ function withdraw() {                     │ function withdraw() {            │
│   uint bal = balances[msg.sender];        │   // 1. CHECKS (Kontrol)         │
│   require(bal > 0);                       │   uint bal = balances[msg.sender]│
│                                           │   require(bal > 0);              │
│   // 💀 FELAKET: Bakiye sıfırlanmadan     │                                  │
│   // önce dış sözleşmeye ETH gönderiliyor!│   // 2. EFFECTS (Durum Güncelle!)│
│   msg.sender.call{value: bal}("");        │   balances[msg.sender] = 0;      │
│                                           │                                  │
│   // Buraya gelmeden saldırganın          │   // 3. INTERACTIONS (Dış Çağrı) │
│   // receive() fonksiyonu tekrar          │   msg.sender.call{value: bal}("")│
│   // withdraw() çağırır!                  │ }                                │
│   balances[msg.sender] = 0;               │ // + OpenZeppelin nonReentrant   │
│ }                                         │ //   Mutex kilidi!               │
└───────────────────────────────────────────┴──────────────────────────────────┘
```

#### 🔄 Saldırı Adım Adım Nasıl Çalışır?
1. Kasada (`Vault`) diğer kullanıcılara ait **100 ETH** vardır. Saldırgan kasaya sadece **10 ETH** yatırır (`balances[Attacker] = 10`).
2. Saldırgan bir akıllı sözleşme üzerinden `withdraw()` çağırır. Kasa `balances[Attacker] > 0` kontrolünü yapar (Doğru: `10 > 0`) ve saldırganın sözleşmesine `10 ETH` gönderir.
3. Ethereum'da bir akıllı sözleşmeye ETH gönderildiğinde, alıcı sözleşmenin **`receive()` / `fallback()`** fonksiyonu otomatik olarak tetiklenir!
4. Kasa henüz `balances[Attacker] = 0` satırına **gelemeden**, saldırganın `receive()` fonksiyonu kasanın `withdraw()` fonksiyonunu **tekrar çağırır (`Re-enter`)!**
5. Kasa tekrar `balances[Attacker]` değerine bakar: hâlâ `10` yazmaktadır! Bir `10 ETH` daha gönderir, `receive()` tekrar çağrılır... Kasadaki **100 ETH tamamen bitene kadar** bu döngü devam eder!

#### 🛡️ Kesin Savunma: `Checks-Effects-Interactions (CEI)` ve `ReentrancyGuard`
1. **`CEI Pattern`:** Önce tüm şartları kontrol et (**`Checks`**), ardından sözleşmenin kendi iç durumunu/bakiyesini güncelle (**`Effects`**: `balances[msg.sender] = 0`), **en son** dış dünyaya para gönder veya dış sözleşme çağır (**`Interactions`**)!
2. **`ReentrancyGuard` (`nonReentrant` Mutex):** Fonksiyon başladığında `locked = true` yapan, fonksiyon bitmeden tekrar girilirse işlemi anında iptal eden (`Revert`) kilit değişkeni kullan.

---

### 2. `AMM (x * y = k)` Matematiği ve `Flash Loan Oracle Manipulation`

Merkeziyetsiz borsalarda (**`Uniswap`, `Curve`, `PancakeSwap`**) alıcı ve satıcı emir defteri (`Order Book`) yoktur; onun yerine **`Automated Market Maker (AMM)`** adı verilen likidite havuzları vardır. En temel formül **Sabit Çarpım Kuralı (`Constant Product Invariant`)**'dır:

$$x \cdot y = k \quad (\text{Sabit})$$

Burada $x$ havuzdaki birinci token (`Token X`) rezervi, $y$ ikinci token (`Token Y`) rezervidir.
- Bir kullanıcı havuza $\Delta x$ miktarında `Token X` koyup karşılığında $\Delta y$ miktarında `Token Y` almak istediğinde, çarpım $k = x \cdot y$ sabit kalmak zorunda olduğundan yeni rezervler $(x + \Delta x) \cdot (y - \Delta y) = x \cdot y$ denklemini sağlar:

$$\Delta y = y - \frac{x \cdot y}{x + \Delta x} = \frac{y \cdot \Delta x}{x + \Delta x}$$

#### ⚡ `Flash Loan` (Yıldırım Kredi) Nedir ve `Price Oracle` Nasıl Hacklenir?
Blokzincirde bir işlem (**`Transaction`**) **atomiktir (`Atomic`)**: İşlemin içindeki 10 adımdan sonuncusu başarısız olursa, ilk 9 adım hiç yaşanmamış gibi geri sarılır (**`Revert`**)!
- **`Flash Loan` (`Aave`, `Balancer`):** Bu atomiklik sayesinde bir protokolden **hiçbir teminat göstermeden 500 Milyon Dolar borç alabilirsin!** Tek şart: **Aynı işlemin (aynı bloğun) sonunda** borcu küçük komisyonuyla birlikte geri ödemendir; ödeyemezsen işlem `Revert` olur ve borç hiç verilmemiş sayılır!
- **Saldırı (`Spot Price Oracle Manipulation`):** Acemi bir kredi protokolü (`Lending Protocol`), teminat değerini hesaplarken doğrudan bir `Uniswap` havuzunun anlık oranına ($\text{Spot Price} = y / x$) bakıyorsa:
  1. Saldırgan `Aave`'den 100 Milyon Dolarlık `Flash Loan` çeker.
  2. Bu devasa parayla `Uniswap` havuzuna girip `Token X` satın alır; havuzdaki $x$ tükenir, $y$ şişer ve `Token X`'in anlık fiyatı **1 saniyeliğine $100\times$ fırlar!**
  3. Saldırgan elindeki azıcık `Token X`'i acemi kredi protokolüne "100 kat değerli teminat" olarak yatırıp protokolün tüm kasasını borç olarak çeker.
  4. `Uniswap` havuzuna token'ları geri satar, `Flash Loan` borcunu kapatır ve milyonlarca dolar net kârla işlemi tamamlar!
- **Savunma:** Asla tek bir bloktaki anlık havuz oranını (`Spot Price`) fiyat kaynağı (`Oracle`) olarak kullanma! Zaman ağırlıklı ortalama fiyat (**`TWAP — Time-Weighted Average Price`**) veya **`Chainlink`** gibi merkeziyetsiz çoklu borsa fiyat ağlarını kullan.

---

### 3. `MEV (Maximal Extractable Value)` ve `Sandwich Attack`

Ethereum veya Solana'da bir takas işlemi gönderdiğinde, işlemin bloğa girmeden önce herkesin görebildiği bekleme salonuna (**`Public Mempool`**) düşer. **`MEV Searcher`** botları `Mempool`'u milisaniyede bir tarar ve büyük bir alım işlemi gördüklerinde onu **Sandviç (`Sandwich Attack`)** içine alırlar:

```
┌────────────────────────────────────────────────────────────────────────────┐
│                   🥪 MEV SANDWICH ATTACK ADIMLARI (AYNI BLOKTA)            │
├────────────────────────────────────────────────────────────────────────────┤
│ 1. 🏃 FRONT-RUN (Öne Geçme — Yüksek Gas / Priority Fee Ödeyerek):          │
│    Bot, kurbanın işlemini Mempool'da görür ve kurbandan HEMEN ÖNCE         │
│    havuzdan Token Y satın alır -> Token Y'nin fiyatı yapay olarak yükselir!│
│                                                                            │
│ 2. 😱 VICTIM TRADE (Kurbanın İşlemi):                                      │
│    Kurbanın alım işlemi şişmiş fiyattan gerçekleşir! Kurban belirlediği    │
│    Slippage (Kayma) sınırına kadar çok daha AZ Token Y alır ve fiyatı      │
│    daha da yukarı iter!                                                    │
│                                                                            │
│ 3. 💰 BACK-RUN (Arkadan Satış):                                            │
│    Kurbanın işleminden HEMEN SONRA bot, 1. adımda ucuza aldığı             │
│    Token Y'leri kurbanın şişirdiği tepeden havuza geri satar ve            │
│    aradaki farkı risksiz kâr (MEV Profit) olarak cebine indirir!           │
└────────────────────────────────────────────────────────────────────────────┘
```

```python
# Sabit Carpimli AMM (x * y = k) uzerinde MEV Sandwich Saldirisi Simulasyonu
def amm_takas_x_ver_y_al(x, y, dx):
    k = x * y
    yeni_x = x + dx
    yeni_y = k / yeni_x
    alinan_dy = y - yeni_y
    return yeni_x, yeni_y, alinan_dy

def amm_takas_y_ver_x_al(x, y, dy):
    k = x * y
    yeni_y = y + dy
    yeni_x = k / yeni_y
    alinan_dx = x - yeni_x
    return yeni_x, yeni_y, alinan_dx

# Havuz: 1000 ETH (X) ve 1000 Token (Y). Kurban 200 ETH ile alim yapacak, Saldirgan 100 ETH ile Front-run yapiyor
x0, y0 = 1000.0, 1000.0
_, _, kurban_normal = amm_takas_x_ver_y_al(x0, y0, 200.0)

# Sandwich: 1) Front-run (100 ETH) -> 2) Kurban (200 ETH) -> 3) Back-run (Aldigi Y'yi geri satar)
x1, y1, bot_alinan_y = amm_takas_x_ver_y_al(x0, y0, 100.0)
x2, y2, kurban_sandwich = amm_takas_x_ver_y_al(x1, y1, 200.0)
x3, y3, bot_geri_alinan_x = amm_takas_y_ver_x_al(x2, y2, bot_alinan_y)
print(f"Kurban Normal: {kurban_normal:.2f} | Sandvicte: {kurban_sandwich:.2f} | Bot Kar: {bot_geri_alinan_x - 100:.2f} ETH")
```

**Kaynak ve sınır:** [Solidity security considerations](https://docs.soliditylang.org/en/latest/security-considerations.html). Sayısal örnekler eğitim ölçeğindedir; gerçek EVM/Solidity sözleşmeleri, mempool veya ağ üzerindeki bir DeFi protokolü üzerinde kabul testi yapılmaz.
:::

::: tahmin Sabit Çarpımlı AMM (x * y = k) Fiyat Kayması (Price Impact / Slippage)
Bir `Uniswap` likidite havuzunda $x = 100$ adet `ETH` ve $y = 400.000$ adet `USDC` bulunmaktadır ($k = 100 \times 400.000 = 40.000.000$, yani başlangıç anlık fiyatı $1\text{ ETH} = 4.000\text{ USDC}$). Bir balina tek seferde havuza $\Delta x = 100\text{ ETH}$ satıp karşılığında `USDC` çekerse, havuzdan kaç `USDC` alır ve aldığı ortalama `ETH` fiyatı kaça düşer?

```python
x, y = 100, 400_000
k = x * y
dx = 100

yeni_x = x + dx
yeni_y = k // yeni_x
alinan_usdc = y - yeni_y
ortalama_fiyat = alinan_usdc // dx
print(f"Alinan: {alinan_usdc} USDC | Ortalama Fiyat: {ortalama_fiyat} USDC/ETH")
```

???

```cikti
Alinan: 200000 USDC | Ortalama Fiyat: 2000 USDC/ETH
```
Havuzdaki `ETH` miktarı $100 + 100 = 200$'e çıktığında, $x \cdot y = 40.000.000$ çarpımının sabit kalması için yeni `USDC` rezervi $40.000.000 / 200 = 200.000$'e iner. Balina $400.000 - 200.000 = 200.000\text{ USDC}$ alır; yani havuz büyüklüğünde işlem yaptığı için %50 fiyat kayması (`Price Impact`) yaşar ve ortalama fiyatı `2000 USDC/ETH` olur!
:::

::: gorev 1 · Sabit Çarpımlı AMM (x * y = k) Takas Motoru ve MEV Sandwich Saldırısı Kâr Hesabı
Komisyonsuz sabit çarpımlı ($x \cdot y = k$) bir **`AMM`** havuzunda **`MEV Sandwich Attack`** etkisini hesaplayan `mev_sandwich_simulasyonu(rezerv_x, rezerv_y, kurban_dx, saldirgan_dx)` fonksiyonunu yaz.

**Hesaplanacak Adımlar:**
1. **Normal Durum (Saldırı Yokken):** Başlangıç $(x_0, y_0) = (\text{rezerv\_x}, \text{rezerv\_y})$ havuzunda kurban tek başına `kurban_dx` kadar `Token X` verdiğinde alacağı `Token Y` miktarı:
   $$\text{kurban\_normal\_dy} = y_0 - \frac{x_0 \cdot y_0}{x_0 + \text{kurban\_dx}}$$
2. **Sandwich Adım 1 (`Front-Run`):** Saldırgan $(x_0, y_0)$ havuzuna `saldirgan_dx` kadar `Token X` verir, karşılığında `bot_dy` kadar `Token Y` alır ve havuz rezervleri $(x_1, y_1)$ olur.
3. **Sandwich Adım 2 (`Victim Trade`):** Kurban $(x_1, y_1)$ havuzuna `kurban_dx` kadar `Token X` verir, karşılığında `kurban_dy` kadar `Token Y` alır ve havuz rezervleri $(x_2, y_2)$ olur.
4. **Sandwich Adım 3 (`Back-Run`):** Saldırgan 1. adımda aldığı `bot_dy` miktarının tamamını $(x_2, y_2)$ havuzuna geri verir (`y_3 = y_2 + bot_dy`) ve karşılığında `bot_son_dx = x_2 - (x_2 * y_2) / y_3` kadar `Token X` geri alır.
5. **Çıktı Sözlüğü (`dict`, tüm değerler `round(..., 4)` ile yuvarlanmış):**
   - `"kurban_normal_dy"`: Saldırı olmasaydı kurbanın alacağı `Y` miktarı
   - `"kurban_sandwich_dy"`: Sandviç saldırısı altında kurbanın alabildiği `Y` miktarı
   - `"kurban_kaybi_dy"`: `round(kurban_normal_dy - kurban_sandwich_dy, 4)`
   - `"saldirgan_net_kar_x"`: `round(bot_son_dx - saldirgan_dx, 4)`

```starter
def mev_sandwich_simulasyonu(rezerv_x, rezerv_y, kurban_dx, saldirgan_dx):
    # TODO: Normal takas ile 3 adimli MEV Sandwich (Front-run -> Kurban -> Back-run) sonuclarini hesapla
    return {
        "kurban_normal_dy": 0.0,
        "kurban_sandwich_dy": 0.0,
        "kurban_kaybi_dy": 0.0,
        "saldirgan_net_kar_x": 0.0,
    }
```

```test
fn = need("mev_sandwich_simulasyonu")

# Test 1: 1000 X, 1000 Y havuzu; kurban_dx=200, saldirgan_dx=100
s1 = fn(1000.0, 1000.0, 200.0, 100.0)
# Normalde: 1000 - 1_000_000 / 1200 = 166.6667
eq(s1["kurban_normal_dy"], 166.6667, "Saldiri yokken kurban 166.6667 Y almali")
# Front-run: x1=1100, y1=909.0909, bot_dy=90.90909...
# Kurban: x2=1300, y2=1_000_000/1300=769.230769..., kurban_dy = 909.090909 - 769.230769 = 139.8601
eq(s1["kurban_sandwich_dy"], 139.8601, "Sandvic altinda kurban 139.8601 Y alabilmeli")
eq(s1["kurban_kaybi_dy"], round(166.6666667 - 139.8601399, 4), "Kurbanin kaybi dogru hesaplanmali")
ok(s1["saldirgan_net_kar_x"] > 15.0, "Saldirgan pozitif MEV kari elde etmeli")
eq(s1["saldirgan_net_kar_x"], 37.3984, "Saldirganin net kari 37.3984 X olmali")

# Test 2: Saldirgan 0 girerse (saldiri yoksa) kayip ve kar 0 olmali
s2 = fn(500.0, 2000.0, 50.0, 0.0)
eq(s2["kurban_kaybi_dy"], 0.0, "Saldirgan_dx=0 iken kurban kaybi 0 olmali")
eq(s2["saldirgan_net_kar_x"], 0.0, "Saldirgan_dx=0 iken saldirgan kari 0 olmali")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def mev_sandwich_simulasyonu(rezerv_x, rezerv_y, kurban_dx, saldirgan_dx):\n    x0, y0 = (float(rezerv_x), float(rezerv_y))\n    k0 = x0 * y0\n    kurban_normal_dy = y0 - k0 / (x0 + kurban_dx)\n    x1 = x0 + saldirgan_dx\n    y1 = k0 / x1\n    bot_dy = y0 - y1\n    k1 = x1 * y1\n    x2 = x1 + kurban_dx\n    y2 = k1 / x2\n    kurban_sandwich_dy = y1 - y2\n    k2 = x2 * y2\n    y3 = y2 + bot_dy\n    x3 = k2 / y3\n    bot_son_dx = x2 - x3\n    kayip = kurban_normal_dy - kurban_sandwich_dy\n    net_kar = bot_son_dx - saldirgan_dx\n    return {'kurban_normal_dy': round(kurban_normal_dy, 4), 'kurban_sandwich_dy': round(kurban_sandwich_dy, 4), 'kurban_kaybi_dy': round(kayip, 4), 'saldirgan_net_kar_x': round(net_kar, 4)}", 'referans', 'exec'), _REF)
_t, _g = _ff(mev_sandwich_simulasyonu, _REF['mev_sandwich_simulasyonu'], (1000.0, 1000.0, 200.0, 100.0), tohum=3515, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (mev_sandwich_simulasyonu): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def mev_sandwich_simulasyonu(rezerv_x, rezerv_y, kurban_dx, saldirgan_dx):
    x0, y0 = float(rezerv_x), float(rezerv_y)
    k0 = x0 * y0
    kurban_normal_dy = y0 - (k0 / (x0 + kurban_dx))

    # 1. Front-run: Saldirgan X verir, Y alir
    x1 = x0 + saldirgan_dx
    y1 = k0 / x1
    bot_dy = y0 - y1

    # 2. Victim trade: Kurban X verir, Y alir
    k1 = x1 * y1
    x2 = x1 + kurban_dx
    y2 = k1 / x2
    kurban_sandwich_dy = y1 - y2

    # 3. Back-run: Saldirgan aldigi bot_dy'yi havuza geri satar, X alir
    k2 = x2 * y2
    y3 = y2 + bot_dy
    x3 = k2 / y3
    bot_son_dx = x2 - x3

    kayip = kurban_normal_dy - kurban_sandwich_dy
    net_kar = bot_son_dx - saldirgan_dx

    return {
        "kurban_normal_dy": round(kurban_normal_dy, 4),
        "kurban_sandwich_dy": round(kurban_sandwich_dy, 4),
        "kurban_kaybi_dy": round(kayip, 4),
        "saldirgan_net_kar_x": round(net_kar, 4),
    }
```

```hint
Her takasta $k = x \cdot y$ çarpımını koru: `yeni_y = (x * y) / (x + dx)` ve `alinan_dy = y - yeni_y`. Back-run adımında ise `y3 = y2 + bot_dy`, `x3 = (x2 * y2) / y3` ve `bot_son_dx = x2 - x3` formülünü uygula.
```
:::

::: gorev 2 · Smart Contract Reentrancy İstismarı vs Checks-Effects-Interactions (CEI) Savunması
Bir akıllı sözleşme kasasının (`Vault`) **`Reentrancy`** saldırısı altındaki davranışını hem zafiyetli modda (`cei_aktif_mi=False`) hem de **`Checks-Effects-Interactions (CEI)`** savunma modunda (`cei_aktif_mi=True`) simüle eden `reentrancy_denetle(kasa_bakiye, kullanici_bakiye, cagri_derinligi, cei_aktif_mi)` fonksiyonunu yaz.

**Simülasyon Kuralları:**
Saldırganın sözleşmesi toplam `cagri_derinligi` ($\ge 1$) kez iç içe `withdraw()` çağrısı yapmayı dener:
1. **`cei_aktif_mi == True` (Güvenli `CEI` Modu):**
   - İlk çağrıda önce kullanıcının bakiyesi kontrol edilir (`kullanici_bakiye > 0` ve `kasa_bakiye >= kullanici_bakiye`), hemen ardından bakiye sıfırlanır (`Effects: bakiye = 0`) ve ödeme yapılır.
   - İç içe gelen 2., 3., ... çağrılarda kullanıcının bakiyesi artık `0` olduğu için yeniden giriş denemeleri reddedilir! Böylece saldırgan **yalnızca kendi hakkı olan 1 kez `kullanici_bakiye`** kadar çekim yapabilir.
2. **`cei_aktif_mi == False` (Zafiyetli Mod — *The DAO*):**
   - Bakiye sıfırlama işlemi en sona bırakıldığı için, iç içe yapılan her çağrıda (`range(cagri_derinligi)`) sözleşme kullanıcının bakiyesini hâlâ `kullanici_bakiye` olarak görür!
   - Her adımda eğer `kasa_bakiye >= kullanici_bakiye` ise kasadan bir `kullanici_bakiye` daha düşülür ve saldırganın çektiği toplama eklenir (kasada yeterli para kalmadığında çekim durur).

**Çıktı Sözlüğü (`dict`):**
- `"cekilen_toplam"`: Saldırganın kasadan çekmeyi başardığı toplam miktar
- `"kalan_kasa"`: İşlem sonunda kasada kalan bakiye
- `"calinan_fazla_miktar"`: `max(0, cekilen_toplam - kullanici_bakiye)` (Saldırganın kendi parasının üzerinde fazladan çaldığı tutar)
- `"istismar_basarili"`: `calinan_fazla_miktar > 0` ise `True`, değilse `False`

```starter
def reentrancy_denetle(kasa_bakiye, kullanici_bakiye, cagri_derinligi, cei_aktif_mi):
    # TODO: Zafiyetli (cei_aktif_mi=False) ve Guvenli CEI (cei_aktif_mi=True) modlarinda cekimi simule et
    return {
        "cekilen_toplam": 0,
        "kalan_kasa": kasa_bakiye,
        "calinan_fazla_miktar": 0,
        "istismar_basarili": False,
    }
```

```test
fn = need("reentrancy_denetle")

# 1) Zafiyetli sozlesme (cei_aktif_mi=False): Kasada 100 ETH var, saldirganin 10 ETH'si var, 8 kez re-enter yapiyor
r1 = fn(100, 10, 8, False)
eq(r1["cekilen_toplam"], 80, "Zafiyetli modda 8 cagri derinliginde 8 * 10 = 80 ETH cekilmeli")
eq(r1["kalan_kasa"], 20, "Kasada 100 - 80 = 20 ETH kalmali")
eq(r1["calinan_fazla_miktar"], 70, "Saldirgan kendi 10 ETH'si disinda 70 ETH calmis olmali")
eq(r1["istismar_basarili"], True, "Fazladan para cekildiginde istismar_basarili=True olmali")

# 2) Zafiyetli sozlesmede kasa siniri: Kasada 35 ETH var, saldirgan 10 ETH ile 10 kez cagri yapiyor (en fazla 3 kez 10 cekebilir)
r2 = fn(35, 10, 10, False)
eq(r2["cekilen_toplam"], 30, "Kasada 35 ETH varken 10'arlik en fazla 30 ETH cekilebilir")
eq(r2["kalan_kasa"], 5, "Kasada 5 ETH kalmali")
eq(r2["calinan_fazla_miktar"], 20, "Calinan fazla miktar 20 ETH olmali")

# 3) CEI Savunmasi Aktif (cei_aktif_mi=True): Saldirgan 8 kez cagri yapsa bile bakiye ilk adimda sifirlandigi icin 10 ETH alabilir
r3 = fn(100, 10, 8, True)
eq(r3["cekilen_toplam"], 10, "CEI aktifken 8 kez re-enter denense bile yalnizca 10 ETH cekilebilir")
eq(r3["kalan_kasa"], 90, "CEI aktifken kasada 90 ETH kalmali")
eq(r3["calinan_fazla_miktar"], 0, "CEI aktifken calinan fazla miktar 0 olmali")
eq(r3["istismar_basarili"], False, "CEI aktifken istismar_basarili=False olmali")
eq(fn(2, 1, 2, False), {"cekilen_toplam": 2, "kalan_kasa": 0, "calinan_fazla_miktar": 1, "istismar_basarili": True}, "1 birim fazla cekimde de istismar_basarili=True olmali")
eq(fn(10, 0, 3, False), {"cekilen_toplam": 0, "kalan_kasa": 10, "calinan_fazla_miktar": 0, "istismar_basarili": False}, "Sifir kullanici bakiyesinde cekim yapilmamali")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def reentrancy_denetle(kasa_bakiye, kullanici_bakiye, cagri_derinligi, cei_aktif_mi):\n    kasa = kasa_bakiye\n    bakiye = kullanici_bakiye\n    cekilen = 0\n    for _ in range(cagri_derinligi):\n        if bakiye > 0 and kasa >= bakiye:\n            odeme = bakiye\n            if cei_aktif_mi:\n                bakiye = 0\n            kasa -= odeme\n            cekilen += odeme\n    if not cei_aktif_mi:\n        bakiye = 0\n    fazla = max(0, cekilen - kullanici_bakiye)\n    return {'cekilen_toplam': cekilen, 'kalan_kasa': kasa, 'calinan_fazla_miktar': fazla, 'istismar_basarili': fazla > 0}", 'referans', 'exec'), _REF)
_t, _g = _ff(reentrancy_denetle, _REF['reentrancy_denetle'], (100, 10, 8, False), tohum=2838, en_cok=600, mod='gecerli', butce='oto', ekler=[(10, 10, 3, False, ), (10, 10, 3, True, )])
ok(_t, "farksal tarama (reentrancy_denetle): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def reentrancy_denetle(kasa_bakiye, kullanici_bakiye, cagri_derinligi, cei_aktif_mi):
    kasa = kasa_bakiye
    bakiye = kullanici_bakiye
    cekilen = 0

    for _ in range(cagri_derinligi):
        if bakiye > 0 and kasa >= bakiye:
            odeme = bakiye
            if cei_aktif_mi:
                bakiye = 0
            kasa -= odeme
            cekilen += odeme

    fazla = max(0, cekilen - kullanici_bakiye)
    return {
        "cekilen_toplam": cekilen,
        "kalan_kasa": kasa,
        "calinan_fazla_miktar": fazla,
        "istismar_basarili": fazla > 0,
    }
```

```hint
Döngü içinde `bakiye > 0 and kasa >= bakiye` kontrolü yap. Eğer `cei_aktif_mi` doğruysa (`True`), hemen ilk çekimde `bakiye = 0` yap ki sonraki döngü adımlarında koşul sağlanamasın; `False` ise `bakiye` döngü boyunca sabit kalır ve kasa yettikçe çekim tekrarlanır.
```
:::

::: gorev 3 · Flash Loan ile Spot Fiyat Oracle Manipülasyonu ve TWAP Savunması
Bir borç verme protokolü X token'ının teminat değerini bir AMM havuzunun **anlık (spot) fiyatından** okuyor. Saldırgan bir flash loan ile çok miktarda Y borçlanıp havuzda X satın alır; X'in spot fiyatı şişer, aynı işlem içinde şişmiş teminatla fazla borç çeker. `oracle_manipulasyonu(rezerv_x, rezerv_y, flash_y, teminat_x, ltv, twap_gecmis)` işlevini yaz.

**Kurallar** (ücretsiz $x \cdot y = k$ havuzu):
1. Rezervler, `teminat_x` pozitif; `flash_y` negatif değil; $0 < \text{ltv} \le 1$; `twap_gecmis` boş olmayan pozitif sayı listesi olmalı (`bool` değil). Değilse `ValueError`.
2. Spot fiyat (X başına Y): $p = r_y / r_x$. Takastan sonra $r_y' = r_y + \text{flash\_y}$, $r_x' = k / r_y'$, $p' = r_y'/r_x'$.
3. TWAP: `twap_gecmis` ile $p'$'nin aritmetik ortalaması (manipüle edilen blok tek gözlem).
4. Çıktı (sayılar `round(·, 6)`): `"spot_once"`, `"spot_sonra"`, `"artis_orani"` ($p'/p$), `"borc_limiti_spot"` ($\text{teminat\_x} \cdot p' \cdot \text{ltv}$), `"borc_limiti_twap"`, `"fazla_borc_spot"` (dürüst limitin üstündeki borç: $\text{teminat\_x}\cdot(p' - p)\cdot\text{ltv}$).

```starter
def oracle_manipulasyonu(rezerv_x, rezerv_y, flash_y, teminat_x, ltv, twap_gecmis):
    # KUSURLU BAŞLANGIÇ: takasın fiyata etkisini yok sayıyor
    p = rezerv_y / rezerv_x
    return {"spot_once": p, "spot_sonra": p, "artis_orani": 1.0, "borc_limiti_spot": teminat_x * p * ltv,
            "borc_limiti_twap": teminat_x * p * ltv, "fazla_borc_spot": 0.0}

print(oracle_manipulasyonu(1000.0, 1000.0, 1000.0, 100.0, 0.8, [1.0, 1.0, 1.0]))
```

```test
fn = need("oracle_manipulasyonu")
r = fn(1000.0, 1000.0, 1000.0, 100.0, 0.8, [1.0, 1.0, 1.0])
eq(r["spot_once"], 1.0, "1000/1000 = 1")
eq(r["spot_sonra"], 4.0, "r_y' = 2000, r_x' = 500: fiyat 4 katına çıkar")
eq(r["artis_orani"], 4.0, "artış oranı 4")
eq(r["borc_limiti_spot"], 320.0, "100 X × 4 × 0.8")
eq(r["fazla_borc_spot"], 240.0, "dürüst limit 80; 240 fazladan borç")
eq(r["borc_limiti_twap"], 140.0, "TWAP (1+1+1+4)/4 = 1.75 → 100 × 1.75 × 0.8")
r2 = fn(500.0, 2000.0, 0.0, 10.0, 0.5, [4.0])
eq(r2["spot_sonra"], 4.0, "flash 0: fiyat değişmez")
eq(r2["fazla_borc_spot"], 0.0, "manipülasyon yoksa fazla borç yok")
raises(ValueError, fn, 0.0, 1000.0, 1.0, 1.0, 0.5, [1.0])
raises(ValueError, fn, 1000.0, 1000.0, 1.0, 1.0, 1.5, [1.0])
raises(ValueError, fn, 1000.0, 1000.0, 1.0, 1.0, 0.5, [])
raises(ValueError, fn, 1000.0, 1000.0, -1.0, 1.0, 0.5, [1.0])

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef _pozitif(v, sifir_olur=False):\n    if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):\n        return False\n    return v >= 0 if sifir_olur else v > 0\n\ndef oracle_manipulasyonu(rezerv_x, rezerv_y, flash_y, teminat_x, ltv, twap_gecmis):\n    if not (_pozitif(rezerv_x) and _pozitif(rezerv_y) and _pozitif(teminat_x) and _pozitif(flash_y, True)):\n        raise ValueError('rezervler ve teminat pozitif, flash_y negatif olmayan sayı olmalı')\n    if not _pozitif(ltv) or ltv > 1:\n        raise ValueError('0 < ltv <= 1 olmalı')\n    if not isinstance(twap_gecmis, list) or not twap_gecmis or (not all((_pozitif(v) for v in twap_gecmis))):\n        raise ValueError('twap_gecmis boş olmayan pozitif sayı listesi olmalı')\n    k = rezerv_x * rezerv_y\n    p = rezerv_y / rezerv_x\n    ry2 = rezerv_y + flash_y\n    rx2 = k / ry2\n    p2 = ry2 / rx2\n    twap = (sum(twap_gecmis) + p2) / (len(twap_gecmis) + 1)\n    return {'spot_once': round(p, 6), 'spot_sonra': round(p2, 6), 'artis_orani': round(p2 / p, 6), 'borc_limiti_spot': round(teminat_x * p2 * ltv, 6), 'borc_limiti_twap': round(teminat_x * twap * ltv, 6), 'fazla_borc_spot': round(teminat_x * (p2 - p) * ltv, 6)}", 'referans', 'exec'), _REF)
_t, _g = _ff(oracle_manipulasyonu, _REF['oracle_manipulasyonu'], (1000.0, 1000.0, 1000.0, 100.0, 0.8, [1.0, 1.0, 1.0]), tohum=3077, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (oracle_manipulasyonu): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def _pozitif(v, sifir_olur=False):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return False
    return v >= 0 if sifir_olur else v > 0

def oracle_manipulasyonu(rezerv_x, rezerv_y, flash_y, teminat_x, ltv, twap_gecmis):
    if not (_pozitif(rezerv_x) and _pozitif(rezerv_y) and _pozitif(teminat_x) and _pozitif(flash_y, True)):
        raise ValueError("rezervler ve teminat pozitif, flash_y negatif olmayan sayı olmalı")
    if not _pozitif(ltv) or ltv > 1:
        raise ValueError("0 < ltv <= 1 olmalı")
    if not isinstance(twap_gecmis, list) or not twap_gecmis or not all(_pozitif(v) for v in twap_gecmis):
        raise ValueError("twap_gecmis boş olmayan pozitif sayı listesi olmalı")
    k = rezerv_x * rezerv_y
    p = rezerv_y / rezerv_x
    ry2 = rezerv_y + flash_y
    rx2 = k / ry2
    p2 = ry2 / rx2
    twap = (sum(twap_gecmis) + p2) / (len(twap_gecmis) + 1)
    return {"spot_once": round(p, 6), "spot_sonra": round(p2, 6), "artis_orani": round(p2 / p, 6),
            "borc_limiti_spot": round(teminat_x * p2 * ltv, 6), "borc_limiti_twap": round(teminat_x * twap * ltv, 6),
            "fazla_borc_spot": round(teminat_x * (p2 - p) * ltv, 6)}
```

```hint
Takastan sonra k sabit kalır: `rx2 = k / (rezerv_y + flash_y)`. TWAP paydası `len(twap_gecmis) + 1`.
```
:::

::: anlat Sınır
Görevler x·y=k AMM takasını ve sandwich kârını, reentrancy istismarını ve CEI savunmasını Python ile modeller; gerçek EVM, Solidity ya da zincir verisi kullanılmaz. Gerçek AMM'lerde işlem ücreti, slippage sınırı ve blok içi sıralama kârı değiştirir; MEV kârından gas ve builder'a ödenen pay düşülmelidir. CEI tek başına çapraz fonksiyon ve read-only reentrancy'yi her zaman engellemez; reentrancy guard ve kod denetimi gerekir. Oracle manipülasyonu görevi ücretsiz bir havuz ve tek gözlemli bir TWAP varsayar; gerçek TWAP pencereleri çok sayıda bloğu kapsar ve manipülasyonu pahalılaştırır.

Kaynaklar: [Daian vd. 2020 - Flash Boys 2.0: Frontrunning, Transaction Reordering, and Consensus Instability in Decentralized Exchanges](https://arxiv.org/abs/1904.05234), [Qin vd. 2021 - Attacking the DeFi Ecosystem with Flash Loans for Fun and Profit](https://arxiv.org/abs/2003.03810), [Zhou vd. 2021 - High-Frequency Trading on Decentralized On-Chain Exchanges](https://arxiv.org/abs/2009.14021).
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
DeFi istismarları çoğunlukla kriptografiyi değil, durum güncelleme sırasını ve tek blokluk fiyat varsayımlarını hedef alır: Reentrancy saldırısında sözleşme bakiyeyi sıfırlamadan dış çağrı yaptığı için saldırgan aynı bakiyeyi döngüsel olarak çeker; çözüm önce kontrol ve durum güncellemesini yapıp dış çağrıyı en sona bırakan Checks-Effects-Interactions (CEI) kalıbı ve yeniden giriş kilididir.

Sabit çarpımlı AMM ($x \cdot y = k$) tarafında ise iki ayrı risk vardır: açık mempool'daki yüksek kayma toleranslı takaslar front-run ve back-run arasına sıkıştırılarak (MEV sandwich) sömürülür; teminatsız atomik flash loan ile tek blokta bükülen anlık havuz oranı (spot price) ise oracle sanılırsa kredi kasası boşaltılır — bu yüzden özel işlem kanalları, sıkı slippage sınırı ve TWAP/çoklu kaynak oracle mimarisi zorunludur.
:::

::: dusun
Bir kullanıcı `Uniswap` üzerinde büyük bir takas yaparken **`MEV Sandwich Attack`** kurbanı olmamak için:
1. Neden `Slippage Tolerance` (Kayma Toleransı) ayarını `%5` yerine `%0.1` gibi sıkı bir değerde tutmalıdır?
2. İşlemini herkese açık `Public Mempool` yerine neden **`Flashbots Protect` (Private RPC)** üzerinden doğrudan blok üreticisine (`Block Builder`) gizlice göndermelidir?
:::

::: ozet
- **`Reentrancy Attack`**, akıllı sözleşmenin kullanıcı bakiyesini sıfırlamadan önce dış çağrı (`External Call`) yapmasını istismar ederek `receive() / fallback()` üzerinden özyinelemeli çekim yapar; kesin çözümü **`Checks-Effects-Interactions (CEI)`** sıralaması ve **`ReentrancyGuard` (`nonReentrant`)** kilididir.
- **`Constant Product AMM`** ($x \cdot y = k$) havuzlarının anlık oranı (**`Spot Price`**) tek bir blokta **`Flash Loan`** (teminatsız atomik kredi) ile kolayca manipüle edilebilir; bu yüzden DeFi protokolleri fiyat kaynağı olarak **`TWAP`** veya **`Chainlink`** merkeziyetsiz oracle ağlarını kullanmalıdır.
- **`MEV Sandwich Attack`**, açık `Mempool`'da görülen bir alım işleminin hemen önüne alım (**`Front-run`**), hemen arkasına satım (**`Back-run`**) yerleştirerek kullanıcının `Slippage` toleransını sömürür.
:::
