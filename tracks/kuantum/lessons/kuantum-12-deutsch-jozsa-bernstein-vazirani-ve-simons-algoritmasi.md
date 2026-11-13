---
id: kuantum-12
title: "Kuantum Sorgu Algoritmaları: Deutsch-Jozsa, Bernstein-Vazirani ve Simon's Algorithm"
summary: "Phase Kickback (Faz Geri Tepmesi) mekanizmasını kur, Deutsch-Jozsa ve Bernstein-Vazirani ile black-box fonksiyonları tek sorguda çöz; Simon's Algorithm ile GF(2) üzerinde gizli XOR periyodunu bularak Even-Mansour simetrik şifresini kır."
track: kuantum
order: 12
duration_minutes: 40
difficulty: ileri
xp: 300
prerequisites: [kuantum-11]
tags: [phase-kickback, deutsch-jozsa, bernstein-vazirani, simons-algorithm, walsh-hadamard, even-mansour, quantum-cryptanalysis]
esleme: kuantum-02, kuantum-03
---

::: anlat 1. Phase Kickback (Faz Geri Tepmesi) ve Deutsch-Jozsa Algoritması
## Quantum oracle ve phase kickback

Bir quantum oracle, girdiye bağlı bilgiyi yardımcı qubit veya phase ilişkisi üzerinden hesaba taşır. Bu derste Bernstein–Vazirani ve Simon örneklerinin classical post-processing parçalarını inceleyeceksin. Küçük bir XOR denklemi çözmek bütün oracle devresini fiziksel olarak gerçekleştirmek değildir.

Elimizde $n$-bit girdi alıp $1$-bit çıktı veren bir black-box fonksiyon (**`Quantum Oracle`** $U_f$) olsun:
$$U_f |x\rangle |y\rangle = |x\rangle |y \oplus f(x)\rangle$$
Normalde bu kapı üstteki $|x\rangle$ yazmacına hiç dokunmaz, sonucu alttaki $|y\rangle$ hedef Qubit'ine `XOR` ($\oplus$) ile yazar.
**Fakat** alttaki hedef Qubit'i $|0\rangle$ yerine **`|-⟩ = (|0⟩ - |1⟩)/√2`** durumunda hazırlarsak ne olur?
- Eğer $f(x) = 0$ ise: $|x\rangle \frac{|0\rangle - |1\rangle}{\sqrt{2}} \to |x\rangle |-\rangle$ *(Hiçbir şey değişmedi)*
- Eğer $f(x) = 1$ ise: $0$ ve $1$ yer değiştirir $\to |x\rangle \frac{|1\rangle - |0\rangle}{\sqrt{2}} = \mathbf{-1} \cdot |x\rangle |-\rangle$!

$$U_f |x\rangle |-\rangle = (-1)^{f(x)} |x\rangle |-\rangle$$

**BINGO!** Hedef Qubit'i $|-\rangle$ hiç değişmeden kalırken, $f(x)$'in cevabı $(-1)^{f(x)}$ işareti olarak **üstteki $|x\rangle$ yazmacının fazına geri tepti (`Phase Kickback`)!**

### ⚡ `Deutsch-Jozsa Algorithm` (1992): $2^{n-1}+1$ Sorgu Yerine Tek Sorgu!
Sana $2^n$ olası girdisi olan bir $f(x)$ kara kutusu verildi ve şu söz verildi:
- Fonksiyon ya **Sabittir (`Constant`):** Her girdide hep $0$ (veya hep $1$) verir.
- Ya da **Dengelidir (`Balanced`):** Girdilerin tam yarısında $0$, diğer yarısında $1$ verir.

1. **Klasik Bilgisayar:** En kötü durumda emin olmak için girdilerin yarısından bir fazlasını ($\mathbf{2^{n-1} + 1}$ sorgu) tek tek denemek zorundadır!
2. **Kuantum Bilgisayar (`H⊗n -> U_f -> H⊗n`):**
   - Üstteki $n$ Qubit'e `Hadamard`, `Oracle` ve tekrar `Hadamard` (**`Walsh-Hadamard Transform`**) uyguladığımızda, $|00\dots 0\rangle$ durumunun genliği tam olarak tüm $(-1)^{f(x)}$ işaretlerinin ortalaması olur:
   $$A(0^n) = \frac{1}{2^n} \sum_{x=0}^{2^n-1} (-1)^{f(x)}$$
   - Eğer $f$ **Sabit (`Constant`)** ise tüm işaretler aynıdır $\implies |A(0^n)| = 1.0$ (%100 olasılıkla `00...0` ölçülür!).
   - Eğer $f$ **Dengeli (`Balanced`)** ise $+1$ ve $-1$'ler birbirini **yıkıcı girişimle (`Destructive Interference`) tam sıfırlar** $\implies A(0^n) = 0.0$ (`00...0` gelme olasılığı **sıfırdır**!).
   - Sonuç: Klasik bilgisayarın trilyonlarca sorguda çözdüğü problem **yalnızca 1 kuantum sorgusunda** kesin olarak çözülür! (Bu üstünlük **kesin, deterministik** bir klasik algoritmaya karşıdır; rastgele girdiler sorgulayan olasılıksal bir klasik algoritma $k$ sorguda yaklaşık $2^{-k}$ yanılma olasılığıyla doğru cevaba ulaşır.)

**Kaynak ve sınır:** [IBM Quantum: quantum algorithms](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms). Sayısal örnekler eğitim ölçeğindedir; gerçek quantum hardware, standart PQC ürünü veya ağ üzerindeki bir hedef üzerinde kabul testi yapılmaz.
:::

::: anlat 2. Bernstein-Vazirani: Gizli Anahtarı Tek Sorguda Okumak
1993'te **Ethan Bernstein** ve **Umesh Vazirani**, kara kutunun içine gizli bir $n$-bitlik anahtar dizisi $s \in \{0,1\}^n$ sakladı:
$$f(x) = s \cdot x \pmod 2 = (s_0 x_0 \oplus s_1 x_1 \oplus \dots \oplus s_{n-1} x_{n-1})$$

- **Klasik Bilgisayar:** Her sorguda en fazla $1$ bit bilgi alabilir ($x = 100\dots0$, $x = 010\dots0$, ... göndererek tam **$n$ sorgu** yapmak zorundadır).
- **Kuantum Bilgisayar (`Bernstein-Vazirani`):** Deutsch-Jozsa ile **birebir aynı devreyi** çalıştırır! İkinci `Hadamard` katmanı her $z \in \{0,1\}^n$ baz durumu için şu **Walsh-Hadamard** toplamını hesaplar:

$$A(z) = \frac{1}{2^n} \sum_{x \in \{0,1\}^n} (-1)^{(s \cdot x) \oplus (z \cdot x)} = \frac{1}{2^n} \sum_{x \in \{0,1\}^n} (-1)^{(s \oplus z) \cdot x}$$

Bu toplamda eğer $z = s$ ise üst kısım hep $0$ olur ve $A(s) = 1.0$ çıkar; $z \neq s$ olan diğer tüm durumlarda ise $+1$ ve $-1$'ler birbirini yok eder ($A(z) = 0$)!
Yani $n$ Qubit'lik yazmacı ölçtüğünde ekranda **tek sorguda (%100 olasılıkla) doğrudan gizli anahtar $s$ yazar!**

```python
# 3-bitlik gizli anahtar s = "101" (5) için Bernstein-Vazirani Walsh-Hadamard simülasyonu
s_gizli = 0b101
f_ciktilari = [bin(x & s_gizli).count("1") % 2 for x in range(8)]

for z in range(8):
    genlik = sum((-1) ** (f_ciktilari[x] ^ (bin(x & z).count("1") % 2)) for x in range(8)) / 8.0
    if abs(genlik) > 0.99:
        print(f"Tek sorguda yakalanan gizli anahtar z = {format(z, '03b')} (Genlik={genlik})")
```
:::

::: anlat 3. Kuantum Kriptanalizde Simon's Algorithm: Even-Mansour ve Feistel Şifrelerini Kırmak!
1994'te **Daniel Simon**, hem **Peter Shor**'a ilham veren hem de modern simetrik kriptografiyi sarsan **`Simon's Algorithm`**'ı yayınladı.

### 🧩 Simon Problemi (Gizli XOR Periyodu $s$):
black-box fonksiyonumuz $f: \{0,1\}^n \to \{0,1\}^n$, sıfırdan farklı gizli bir **$s \in \{0,1\}^n$ XOR periyoduna** sahiptir:
$$f(x) = f(y) \iff y = x \oplus s$$
- **Klasik Bilgisayar:** Aynı çıktıyı veren iki girdi ($f(x) = f(x \oplus s)$ çarpışması) bulmak için **Birthday Paradox** gereği $\mathbf{\Omega(2^{n/2})}$ sorgu yapmak zorundadır (üstel süre!).
- **Kuantum Bilgisayar (`Simon's Algorithm`):**
  1. $|\psi\rangle = \frac{1}{\sqrt{2^n}}\sum_x |x\rangle |f(x)\rangle$ durumunu hazırlar ve ikinci yazmacı ölçer.
  2. Birinci yazmaçta sadece birbirinin $s$ eşi olan iki durumun süperpozisyonu kalır: $\frac{|x_0\rangle + |x_0 \oplus s\rangle}{\sqrt{2}}$.
  3. Birinci yazmaca $H^{\otimes n}$ uygulayıp ölçtüğümüzde, yalnızca gizli $s$ vektörüne **$GF(2)$ uzayında dik (`Orthogonal`)** olan $z$ vektörleri gelebilir:
  $$z \cdot s \equiv 0 \pmod 2$$
  4. Bu devreyi $O(n)$ kez çalıştırıp $n-1$ tane doğrusal bağımsız $z_1, z_2, \dots, z_{n-1}$ denklemi toplarız ve $GF(2)$ Gauss yok etme yöntemiyle **gizli $s$ periyodunu polinom sürede ($O(n^3)$)** çözeriz!

### 💀 Kuantum Hacker Etkisi: `Even-Mansour` Şifresi Neden Anında Çöker?
Blok şifre tasarımının temel taşı olan **`Even-Mansour Cipher`** şu formülle çalışır:
$$E_{k_1, k_2}(x) = P(x \oplus k_1) \oplus k_2$$
(Burada $P$ herkese açık bir permütasyon, $k_1, k_2$ ise gizli anahtarlardır).
Klasik dünyada bu şifre son derece güvenlidir. **Ancak Kuwakado ve Morii (2012)** şunu gösterdi: Eğer saldırgan şifreleme kutusuna kuantum süperpozisyon sorgusu (**`Q2 Model`**) gönderebiliyorsa, şu yardımcı fonksiyonu tanımlar:
$$f(x) = E_{k_1, k_2}(x) \oplus P(x) = P(x \oplus k_1) \oplus k_2 \oplus P(x)$$
Dikkat et! $x$ yerine $x \oplus k_1$ koyduğunda ne olur?
$$f(x \oplus k_1) = P(x) \oplus k_2 \oplus P(x \oplus k_1) = f(x)$$
Yani $f(x)$ fonksiyonunun **Simon XOR periyodu tam olarak gizli anahtar $s = k_1$'dir!** Bir Kuantum Hacker, `Simon's Algorithm` ile $128$-bitlik `Even-Mansour` (ve `3-Round Feistel` / `CBC-MAC`) şifresini $2^{64}$ yerine **sadece ~128 sorguda** tamamen kırar!
:::

::: tahmin GF(2) Diklik Denklemi (z · s ≡ 0 mod 2)
3-bitlik bir `Simon` devresinden iki farklı ölçüm sonucu olarak $z_1 = \text{"101"}$ ve $z_2 = \text{"011"}$ elde edilmiştir. Sıfırdan farklı gizli periyot $s$, her iki vektöre de $GF(2)$'de dik ($z \cdot s \equiv 0 \pmod 2$) olmak zorundadır. Aşağıdaki kod hangi gizli $s$ periyodunu bulur?

```python
z_list = ["101", "011"]
for s in range(1, 8):
    dik_mi = all(bin(int(z, 2) & s).count("1") % 2 == 0 for z in z_list)
    if dik_mi:
        print("Bulunan Gizli Periyot s =", format(s, "03b"))
```

???

```cikti
Bulunan Gizli Periyot s = 111
```
$s = \text{"111"}$ için: $z_1 \cdot s = (1\cdot 1) \oplus (0\cdot 1) \oplus (1\cdot 1) = 1 \oplus 0 \oplus 1 = 0$ ve $z_2 \cdot s = (0\cdot 1) \oplus (1\cdot 1) \oplus (1\cdot 1) = 0 \oplus 1 \oplus 1 = 0$ sağlanır. İki bağımsız denklem 3-bitlik uzayda sıfır-dışı tek çözümü (`"111"`) kesin olarak belirler!
:::

::: gorev 1 · Bernstein-Vazirani black-box (Oracle) Faz Geri Tepmesiyle Gizli Anahtar Çıkarma
`bv_gizli_anahtar_coz(oracle_ciktilari, bit_uzunlugu)` işlevini yaz:
- `oracle_ciktilari`: uzunluğu $N = 2^{\text{bit\_uzunlugu}}$ olan ve her $x \in \{0, \dots, N-1\}$ için $f(x) \in \{0, 1\}$ değerini tutan listedir.
- Her aday $z \in \{0, \dots, N-1\}$ için Walsh-Hadamard genliğini hesapla:
  $$A(z) = \frac{1}{N} \sum_{x=0}^{N-1} (-1)^{f(x) \oplus (\text{popcount}(x \ \& \ z) \bmod 2)}$$
- $|A(z)| > 0.99$ olan $z$ değerini `bit_uzunlugu` haneli ikili dizge (`format(z, f"0{bit_uzunlugu}b")`) olarak `gizli_anahtar_s` alanına yaz.
- Ayrıca $z=0$ için $|A(0)| > 0.99$ ise fonksiyon sabittir (`sabit_mi = True`), değilse dengelidir (`sabit_mi = False`).
- `{"gizli_anahtar_s": ..., "sabit_mi": ..., "klasik_sorgu_sayisi": bit_uzunlugu, "kuantum_sorgu_sayisi": 1}` döndür.

```starter
# KUSURLU BAŞLANGIÇ KODU: Walsh-Hadamard toplamıyla gizli s dizgesini bul.
def bv_gizli_anahtar_coz(oracle_ciktilari, bit_uzunlugu):
    return {
        "gizli_anahtar_s": "0" * bit_uzunlugu,
        "sabit_mi": True,
        "klasik_sorgu_sayisi": bit_uzunlugu,
        "kuantum_sorgu_sayisi": 1
    }

# s = "101" (5) için oracle çıktıları:
print(bv_gizli_anahtar_coz([0, 1, 0, 1, 1, 0, 1, 0], 3))
```
```test
f = need("bv_gizli_anahtar_coz")
# s = "101" (3 bit)
r1 = f([0, 1, 0, 1, 1, 0, 1, 0], 3)
ok(r1 == {"gizli_anahtar_s": "101", "sabit_mi": False, "klasik_sorgu_sayisi": 3, "kuantum_sorgu_sayisi": 1}, "3-bitlik gizli anahtar '101' tek kuantum sorgusuyla çözüldü")

# s = "1101" (4 bit = 13)
s4 = 0b1101
orc4 = [bin(x & s4).count("1") % 2 for x in range(16)]
r2 = f(orc4, 4)
ok(r2 == {"gizli_anahtar_s": "1101", "sabit_mi": False, "klasik_sorgu_sayisi": 4, "kuantum_sorgu_sayisi": 1}, "4-bitlik gizli anahtar '1101' Walsh-Hadamard girişimiyle çözüldü")

# s = "000" (sabit fonksiyon f(x) = 1)
r3 = f([1] * 8, 3)
ok(r3 == {"gizli_anahtar_s": "000", "sabit_mi": True, "klasik_sorgu_sayisi": 3, "kuantum_sorgu_sayisi": 1}, "Sabit fonksiyon (s='000') Deutsch-Jozsa kriteriyle tespit edildi")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def bv_gizli_anahtar_coz(oracle_ciktilari, bit_uzunlugu):\n    n_boyut = 1 << bit_uzunlugu\n    bulunan_z = 0\n    sabit = False\n    for z in range(n_boyut):\n        toplam = 0\n        for x in range(n_boyut):\n            ic = bin(x & z).count('1') & 1\n            ust = oracle_ciktilari[x] ^ ic\n            toplam += -1 if ust else 1\n        genlik = toplam / n_boyut\n        if z == 0 and abs(genlik) > 0.99:\n            sabit = True\n        if abs(genlik) > 0.99:\n            bulunan_z = z\n    return {'gizli_anahtar_s': format(bulunan_z, f'0{bit_uzunlugu}b'), 'sabit_mi': bool(sabit), 'klasik_sorgu_sayisi': bit_uzunlugu, 'kuantum_sorgu_sayisi': 1}", 'referans', 'exec'), _REF)
_t, _g = _ff(bv_gizli_anahtar_coz, _REF['bv_gizli_anahtar_coz'], ([0, 1, 0, 1, 1, 0, 1, 0], 3), tohum=3028, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (bv_gizli_anahtar_coz): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
def bv_gizli_anahtar_coz(oracle_ciktilari, bit_uzunlugu):
    n_boyut = 1 << bit_uzunlugu
    bulunan_z = 0
    sabit = False
    for z in range(n_boyut):
        toplam = 0
        for x in range(n_boyut):
            ic = bin(x & z).count("1") & 1
            ust = oracle_ciktilari[x] ^ ic
            toplam += -1 if ust else 1
        genlik = toplam / n_boyut
        if z == 0 and abs(genlik) > 0.99:
            sabit = True
        if abs(genlik) > 0.99:
            bulunan_z = z
    return {
        "gizli_anahtar_s": format(bulunan_z, f"0{bit_uzunlugu}b"),
        "sabit_mi": bool(sabit),
        "klasik_sorgu_sayisi": bit_uzunlugu,
        "kuantum_sorgu_sayisi": 1
    }

print(bv_gizli_anahtar_coz([0, 1, 0, 1, 1, 0, 1, 0], 3))
```
```hint
Her `z in range(1 << bit_uzunlugu)` için `sum((-1)**(oracle_ciktilari[x] ^ (bin(x & z).count("1") % 2)) for x in range(N)) / N` genliğini hesapla; mutlak değeri `> 0.99` olan `z` gizli anahtardır.
```
:::

::: gorev 2 · Simon Algoritması: GF(2) Üzerinde Dik (Orthogonal) Denklemlerden Gizli XOR Periyodu s'yi Bulma
`simon_periyot_bul(olculen_z_vektorleri, n_bit)` işlevini yaz:
- `olculen_z_vektorleri`: Simon devresinden ölçülen `n_bit` uzunluklu ikili dizgelerin listesidir.
- Sıfırdan farklı her aday $s \in \{1, \dots, 2^{\text{n\_bit}} - 1\}$ için tüm $z \in \text{olculen\_z\_vektorleri}$ vektörleriyle $GF(2)$ iç çarpımının sıfır olup olmadığını (`bin(int(z, 2) & s).count("1") % 2 == 0`) kontrol et.
- Koşulu sağlayan tüm adayları `format(s, f"0{n_bit}b")` biçiminde `cozum_adaylari` listesine ekle.
- `{"gizli_periyot_s": cozum_adaylari[0] if cozum_adaylari else "0"*n_bit, "cozum_adaylari": cozum_adaylari, "tam_cozuldu_mu": bool(len(cozum_adaylari) == 1)}` döndür.

```starter
# KUSURLU BAŞLANGIÇ KODU: GF(2) diklik koşulunu sağlayan sıfır-dışı s adaylarını bul.
def simon_periyot_bul(olculen_z_vektorleri, n_bit):
    return {
        "gizli_periyot_s": "0" * n_bit,
        "cozum_adaylari": [],
        "tam_cozuldu_mu": False
    }

print(simon_periyot_bul(["101", "011"], 3))
```
```test
f = need("simon_periyot_bul")
r1 = f(["101", "011"], 3)
ok(r1 == {"gizli_periyot_s": "111", "cozum_adaylari": ["111"], "tam_cozuldu_mu": True}, "3-bit Simon sisteminde tekil gizli periyot '111' bulundu")

# 4-bit Even-Mansour anahtarı k1 = "1010" (10) -> dik vektörler: "0100" (4), "0001" (1), "1010" (10 -> 1^1=0)
r2 = f(["0100", "0001", "1010"], 4)
ok(r2 == {"gizli_periyot_s": "1010", "cozum_adaylari": ["1010"], "tam_cozuldu_mu": True}, "4-bit Even-Mansour gizli anahtarı '1010' Simon denklemleriyle kırıldı")

# Eksik denklem durumu (2 aday kalmalı -> tam_cozuldu_mu = False)
r3 = f(["100"], 3)
ok(r3["cozum_adaylari"] == ["001", "010", "011"] and r3["tam_cozuldu_mu"] is False, "Yetersiz sayıda ölçümde birden fazla aday raporlandı ve tam_cozuldu_mu=False döndü")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def simon_periyot_bul(olculen_z_vektorleri, n_bit):\n    z_int = [int(z, 2) for z in olculen_z_vektorleri]\n    adaylar = []\n    for s in range(1, 1 << n_bit):\n        if all((bin(z & s).count('1') & 1 == 0 for z in z_int)):\n            adaylar.append(format(s, f'0{n_bit}b'))\n    return {'gizli_periyot_s': adaylar[0] if adaylar else '0' * n_bit, 'cozum_adaylari': adaylar, 'tam_cozuldu_mu': bool(len(adaylar) == 1)}", 'referans', 'exec'), _REF)
_t, _g = _ff(simon_periyot_bul, _REF['simon_periyot_bul'], (['101', '011'], 3), tohum=2760, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (simon_periyot_bul): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
def simon_periyot_bul(olculen_z_vektorleri, n_bit):
    z_int = [int(z, 2) for z in olculen_z_vektorleri]
    adaylar = []
    for s in range(1, 1 << n_bit):
        if all((bin(z & s).count("1") & 1) == 0 for z in z_int):
            adaylar.append(format(s, f"0{n_bit}b"))
    return {
        "gizli_periyot_s": adaylar[0] if adaylar else "0" * n_bit,
        "cozum_adaylari": adaylar,
        "tam_cozuldu_mu": bool(len(adaylar) == 1)
    }

print(simon_periyot_bul(["101", "011"], 3))
```
```hint
`range(1, 1 << n_bit)` içindeki her `s` için `all((bin(int(z, 2) & s).count("1") % 2) == 0 for z in olculen_z_vektorleri)` şartını kontrol et.
```
:::

::: gorev 3 · Deutsch-Jozsa: Tek Sorguda Sabit mi Dengeli mi?
`deutsch_jozsa(f_tablosu)` işlevini yaz. `f_tablosu`, $f: \{0,1\}^n \to \{0,1\}$ fonksiyonunun doğruluk tablosudur (`f_tablosu[x]`, $x$'in ikili gösteriminin değeri). Deutsch-Jozsa devresi ($H^{\otimes n} \cdot U_f \cdot H^{\otimes n}$, faz geri tepmesiyle) sonunda `|0…0⟩` genliği
$$a_0 = \frac{1}{2^n} \sum_{x} (-1)^{f(x)}$$
olur. $f$ sabitse $|a_0| = 1$, dengeliyse $a_0 = 0$.

**Kurallar:**
1. Tablo uzunluğu $2^n$ ($n \ge 1$) olmalı, öğeler `int` 0 ya da 1 olmalı (`bool` kabul edilmez); değilse `ValueError`.
2. Algoritmanın **vaadi**: $f$ ya sabit ya dengeli. İkisi de değilse `ValueError("vaat bozuk")`.
3. Çıktı: `"n"`, `"genlik_sifir"` ($a_0$, `round(·, 6)`), `"p_sifir"` ($a_0^2$, `round(·, 6)`), `"karar"` (`"sabit"` ya da `"dengeli"`), `"kuantum_sorgu": 1`, `"klasik_en_kotu_sorgu"`: $2^{n-1} + 1$.

```starter
def deutsch_jozsa(f_tablosu):
    # KUSURLU BAŞLANGIÇ: yalnız ilk iki değere bakıp karar veriyor
    karar = "sabit" if f_tablosu[0] == f_tablosu[1] else "dengeli"
    return {"n": 1, "genlik_sifir": 1.0, "p_sifir": 1.0, "karar": karar, "kuantum_sorgu": 1, "klasik_en_kotu_sorgu": 2}

print(deutsch_jozsa([0, 0, 1, 1]))
```

```test
fn = need("deutsch_jozsa")
r = fn([0, 0, 0, 0])
eq(r["karar"], "sabit", "hep 0 olan f sabittir")
eq(r["genlik_sifir"], 1.0, "sabit 0 için tüm (-1)^0 = 1: genlik 1")
eq(r["n"], 2, "4 girişlik tablo n = 2 qubit")
eq(r["klasik_en_kotu_sorgu"], 3, "klasik deterministik algoritma en kötü 2^(n-1)+1 = 3 sorgu ister")
r1 = fn([1, 1])
eq(r1["genlik_sifir"], -1.0, "sabit 1: genlik -1 (global faz), olasılık yine 1")
eq(r1["p_sifir"], 1.0, "sabit fonksiyonda |0⟩ ölçme olasılığı 1")
eq(r1["karar"], "sabit", "hep 1 de sabit")
r2 = fn([0, 1, 1, 0])
eq(r2["p_sifir"], 0.0, "dengeli fonksiyonda katkılar birbirini götürür")
eq(r2["karar"], "dengeli", "XOR tablosu dengeli")
eq(fn([0, 0, 1, 1, 1, 1, 0, 0])["karar"], "dengeli", "n = 3 dengeli tablo")
eq(fn([1] * 8)["klasik_en_kotu_sorgu"], 5, "n = 3 için 2^2 + 1 = 5")
eq(fn([1] * 8)["kuantum_sorgu"], 1, "kuantum devre tek sorgu yapar")
# İki qubit için altı dengeli tablonun tüm yerleşimleri.
dengeli_tablolar = ([0, 0, 1, 1], [0, 1, 0, 1], [0, 1, 1, 0],
                    [1, 0, 0, 1], [1, 0, 1, 0], [1, 1, 0, 0])
for tablo in dengeli_tablolar:
    once = tablo[:]
    eq(fn(tablo), {
        "n": 2, "genlik_sifir": 0.0, "p_sifir": 0.0,
        "karar": "dengeli", "kuantum_sorgu": 1, "klasik_en_kotu_sorgu": 3,
    }, f"Dengeli tablo {tablo}")
    eq(tablo, once, "Girdi sırası korunur")
eq(fn([0, 1])["klasik_en_kotu_sorgu"], 2, "Tek qubit için en küçük geçerli tablo")
raises(ValueError, fn, [1, 1, 1, 0])
raises(ValueError, fn, [0.0, 1.0])
raises(ValueError, fn, [0, 0, 0, 1])
raises(ValueError, fn, [0, 1, 0])
raises(ValueError, fn, [0, 2])
raises(ValueError, fn, [True, False])
raises(ValueError, fn, [0])

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile('def deutsch_jozsa(f_tablosu):\n    if not isinstance(f_tablosu, list) or len(f_tablosu) < 2:\n        raise ValueError(\'tablo en az 2 öğeli liste olmalı\')\n    N = len(f_tablosu)\n    if N & N - 1:\n        raise ValueError("tablo uzunluğu 2\'nin kuvveti olmalı")\n    for v in f_tablosu:\n        if isinstance(v, bool) or v not in (0, 1) or (not isinstance(v, int)):\n            raise ValueError(\'tablo öğeleri 0 ya da 1 olmalı\')\n    n = N.bit_length() - 1\n    birler = sum(f_tablosu)\n    if birler not in (0, N, N // 2):\n        raise ValueError(\'vaat bozuk\')\n    a0 = sum(((-1) ** f for f in f_tablosu)) / N\n    p0 = a0 * a0\n    return {\'n\': n, \'genlik_sifir\': round(a0, 6), \'p_sifir\': round(p0, 6), \'karar\': \'sabit\' if p0 > 0.5 else \'dengeli\', \'kuantum_sorgu\': 1, \'klasik_en_kotu_sorgu\': 2 ** (n - 1) + 1}', 'referans', 'exec'), _REF)
_t, _g = _ff(deutsch_jozsa, _REF['deutsch_jozsa'], ([0, 0, 1, 1],), tohum=2315, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (deutsch_jozsa): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def deutsch_jozsa(f_tablosu):
    if not isinstance(f_tablosu, list) or len(f_tablosu) < 2:
        raise ValueError("tablo en az 2 öğeli liste olmalı")
    N = len(f_tablosu)
    if N & (N - 1):
        raise ValueError("tablo uzunluğu 2'nin kuvveti olmalı")
    for v in f_tablosu:
        if isinstance(v, bool) or v not in (0, 1) or not isinstance(v, int):
            raise ValueError("tablo öğeleri 0 ya da 1 olmalı")
    n = N.bit_length() - 1
    birler = sum(f_tablosu)
    if birler not in (0, N, N // 2):
        raise ValueError("vaat bozuk")
    a0 = sum((-1) ** f for f in f_tablosu) / N
    p0 = a0 * a0
    return {"n": n, "genlik_sifir": round(a0, 6), "p_sifir": round(p0, 6),
            "karar": "sabit" if p0 > 0.5 else "dengeli", "kuantum_sorgu": 1,
            "klasik_en_kotu_sorgu": 2 ** (n - 1) + 1}
```

```hint
Sabit: birlerin sayısı 0 ya da N; dengeli: tam N/2. Genlik `sum((-1)**f) / N`.
```
:::

::: anlat Sınır
Görevler Bernstein-Vazirani'deki faz geri tepmesini ve Simon algoritmasında GF(2) denklemlerinden gizli periyodu çıkarmayı yazdırır; Deutsch-Jozsa görevi genliği doğruluk tablosundan hesaplar, tersinir oracle devresi kurmaz. Bu algoritmaların üstel hızlanması oracle (kara kutu) modelinde geçerlidir; gerçek bir fonksiyonu tersinir oracle olarak kurmanın maliyeti hızlanmayı silebilir. Simon tabanlı Even-Mansour ve CBC-MAC saldırıları, saldırganın şifreleme oracle'ını kuantum süperpozisyonda sorgulayabildiği modeli varsayar; yalnız klasik sorgu yapılabiliyorsa bu saldırılar çalışmaz. Simülasyon gürültüsüzdür.

Kaynaklar: [Cleve vd. 1998 - Quantum algorithms revisited](https://arxiv.org/abs/quant-ph/9708016), [Kaplan vd. 2016 - Breaking Symmetric Cryptosystems using Quantum Period Finding](https://arxiv.org/abs/1602.05973).
:::

::: dusun
Kriptografide iki farklı kuantum saldırı modeli tanımlanır:
- **`Q1 Model` (Klasik Sorgu + Kuantum Hesaplama):** Saldırgan şifreli paketleri klasik internetten toplar, sonra kendi kuantum bilgisayarında (`Shor` veya `Grover` ile) çevrimdışı analiz eder.
- **`Q2 Model` (Kuantum Süperpozisyon Sorgusu):** Saldırgan hedef şifreleme donanımına doğrudan süperpozisyon halinde $\sum |x\rangle$ gönderip şifreli süperpozisyon yanıtı alabilir (`Simon's Algorithm` ile `Even-Mansour` ve `CBC-MAC` kırma).

Neden gerçek dünyada **`Q1 Model`** çok daha acil bir tehdit iken, açık kaynaklı bir hash/şifre algoritması kodunun saldırganın kendi kuantum bilgisayarına yüklenebildiği durumlarda `Q2` devre teknikleri de önem kazanır? Açıkla.
:::

::: ozet
- **`Phase Kickback`**, hedef Qubit'i $|-\rangle$ durumunda hazırlayarak bir kara kutunun ($U_f$) çıktısını $(-1)^{f(x)}$ faz işaretine dönüştürür.
- **`Deutsch-Jozsa`** bir fonksiyonun sabit mi dengeli mi olduğunu **1 sorguda**, **`Bernstein-Vazirani`** ise $f(x) = s \cdot x \pmod 2$ gizli $n$-bit anahtarını klasikte $n$ sorgu yerine kuantumda **1 sorguda** çıkarır.
- **`Simon's Algorithm`**, $f(x) = f(x \oplus s)$ gizli XOR periyodunu $GF(2)$ diklik denklemleriyle ($z \cdot s \equiv 0 \pmod 2$) $\Omega(2^{n/2})$ yerine $O(n)$ sorguda bulur; hem **Shor Algoritması**'nın temelini atmıştır hem de kuantum süperpozisyon modeli altında **`Even-Mansour`** ve **`3-Round Feistel`** şifrelerini polinom sürede kırar.
:::
