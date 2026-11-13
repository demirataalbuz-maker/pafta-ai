---
id: kuantum-05
title: Post-Quantum Cryptography (PQC) · Lattice Matematiği ve Learning With Errors (LWE)
summary: Shor algoritmasının kıramadığı kriptografi nasıl kurulur? Çok boyutlu kafes (Lattice) geometrisi, Shortest Vector Problem (SVP), Oded Regev'in Learning With Errors (LWE) problemi ve NIST standartları (ML-KEM / Kyber, ML-DSA / Dilithium).
esleme: kuantum-04, kuantum-21
---

::: anlat 1. Büyük Yanlış Anlaşılma: Post-Quantum Cryptography (PQC) Kuantum Bilgisayar Gerektirir mi?
## Post-quantum cryptography ve LWE

Post-quantum cryptography, klasik sistemlerde uygulanıp bilinen quantum saldırılarına da dayanması hedeflenen algoritmaları kapsar. Bu derste lattice ve LWE fikrini küçük denklemlerle inceleyeceksin. Oyuncak parametreler veya bir zorluk benzetmesi, standart bir KEM/signature uygulaması ya da koşulsuz güvenlik kanıtı değildir.

Konferansta insanların %90'ının birbirine karıştırdığı iki terimi netleştirerek başlayalım:
1. **`Quantum Cryptography` / `Quantum Key Distribution (QKD - BB84)`:** Fiber optik kablodan gerçek fotonlar (`Qubit`) göndererek yapılan donanımsal anahtar dağıtımıdır. Özel kuantum optik cihazlar gerektirir.
2. **`Post-Quantum Cryptography (PQC)` (`Quantum-Resistant Cryptography`):** **Hiçbir kuantum donanımı GEREKTİRMEZ!** Bugün kullandığımız normal klasik bilgisayarlarda, cep telefonlarında ve sunucularda çalışan; **ancak karşısına `Shor's Algorithm` veya `Grover's Algorithm` çalıştıran dev bir kuantum bilgisayar çıksa bile kırılmayan** yeni nesil matematiksel algoritmalardır!

Peki `Shor's Algorithm` neden `RSA` ve `ECC`'yi tereyağından kıl çeker gibi kırarken `PQC` algoritmalarını kıramaz?
- Çünkü `RSA` ve `ECC` tek boyutlu döngüsel gruplardaki **gizli periyot (`Periodicity` / `Abelian Hidden Subgroup Problem`)** yapısına dayanır; `Quantum Fourier Transform (QFT)` ise periyot bulmak için biçilmiş kaftandır!
- Oysa `Post-Quantum Cryptography`, içinde hiçbir basit periyot barındırmayan, **500–1.000 boyutlu uzayda gürültülü geometrik kafeslere (`Lattice-Based Cryptography`)** dayanır! `QFT` bu gürültülü kafese baktığında hiçbir ritim bulamaz!

**Kaynak ve sınır:** [NIST FIPS 203: ML-KEM](https://csrc.nist.gov/pubs/fips/203/final). Sayısal örnekler eğitim ölçeğindedir; gerçek quantum hardware, standart PQC ürünü veya ağ üzerindeki bir hedef üzerinde kabul testi yapılmaz.
:::

::: anlat 2. Lattice (Kafes) Nedir? Shortest Vector Problem (SVP) ve Closest Vector Problem (CVP)
Bir **`Lattice` (Matematiksel Kafes)**, uzayda başlangıç noktası sıfır olan birkaç temel vektörün ($\mathbf{b}_1, \mathbf{b}_2, \dots, \mathbf{b}_n$ — **`Basis Vectors`**) tam sayı katlarıyla ($c_1 \mathbf{b}_1 + c_2 \mathbf{b}_2 + \dots$) ulaşabildiğin düzenli noktalar ızgarasıdır.

### 🗺️ Benzetme: Manhattan Sokaklarında İyi Harita vs Çarpık Harita
Diyelim ki Manhattan'da bir adres arıyorsun:
- **İyi Taban (`Good Basis` — Gizli Anahtar / `Private Key`):** Elinde birbirine dik ve kısa iki yön vektörü var: *"1 adım Doğuya git $(1, 0)$"* ve *"1 adım Kuzeye git $(0, 1)$"*. Sana $(53, 89)$ noktasına en yakın ızgara köşesini sorduğumda 1 saniyede bulursun!
- **Kötü Taban (`Bad Basis` — Açık Anahtar / `Public Key`):** Aynı noktalara ulaşan ama birbirine neredeyse paralel, çok uzun ve çarpık iki vektör: Örneğin $\mathbf{b}_1 = (999, 1000)$ ve $\mathbf{b}_2 = (998, 999)$.
- Lattice problemlerinin zorluğu boyutun yanında dağılıma, parametrelere ve saldırı modeline bağlıdır. Standartların dayandığı varsayım, seçilen parametrelerde bilinen saldırıların pahalı olmasıdır; bütün lattice örnekleri için matematiksel imkânsızlık teoremi ileri sürülmez.
:::

::: anlat 3. Oded Regev'in Başyapıtı: Learning With Errors (LWE, 2005 — Gödel Ödülü)
2005 yılında bilgisayar bilimci **Oded Regev**, kafes kriptografisini son derece zarif bir doğrusal cebir problemine dönüştürdü: **`Learning With Errors (LWE)` (Hatalarla Öğrenme)**.

### 🧮 Lise Denklemi Neden Kuantum Bilgisayarı Çaresiz Bırakır?
Önce hatasız (gürültüsüz) durumu düşün:
Gizli anahtarımız $s = [3, 5, 2]$ olsun (mod $17$ aritmetiğinde çalışalım). Sana rastgele katsayılardan oluşan 3 tane doğrusal denklem veriyorum:
$$\begin{aligned}
2s_1 + 4s_2 + 1s_3 &\equiv 11 \pmod{17} \\
1s_1 + 1s_2 + 3s_3 &\equiv 14 \pmod{17} \\
5s_1 + 2s_2 + 1s_3 &\equiv 10 \pmod{17}
\end{aligned}$$
Eğer denklemler böyle **tam (hatasız)** ise, lisede öğrendiğimiz **`Gaussian Elimination` (Gauss Yok Etme Yöntemi)** ile denklemleri birbirinden çıkarır ve gizli anahtar $s = [3, 5, 2]$'yi **milisaniyede** bulursun!

### 💥 Şimdi Sihirli Dokunuş: Her Denkleme Küçücük Bir Gürültü ($e \in \{-1, 0, +1\}$) Ekle!
Şimdi her denklemin sonucuna rastgele $+1$ veya $-1$ gibi küçücük bir hata (**`Error / Noise` $e$**) ekliyorum:

$$\mathbf{b} = \mathbf{A}\mathbf{s} + \mathbf{e} \pmod q$$

Ne oldu? **`Gaussian Elimination` bir anda tamamen çöktü!**
Neden? Çünkü Gauss yok etme yönteminde 1. satırı 10 ile çarpıp 2. satırdan çıkardığında, o küçücük $\pm 1$ hatası da 10 ile çarpılır; birkaç adım sonra hatalar çığ gibi büyür (**`Noise Amplification`**) ve tüm denklem sistemi tamamen anlamsız gürültüye dönüşür!

```python
# Learning With Errors (LWE) simetrik/açık-anahtar temel mekanizması (Mod q = 97)
q = 97
s = [12, 45, 7, 33]          # Gizli Anahtar (Private Key vektörü)
A = [3, 10, 5, 2]            # Herkese açık rastgele satır (Public Matrix A satırı)
e = 1                        # Küçük gürültü (Error: -1, 0 veya +1)

# Gürültülü açık çıktı: b = (A . s + e) mod q
ic_carpim = sum(a * x for a, x in zip(A, s))
b = (ic_carpim + e) % q

# 1 bitlik mesajı (mesaj_bit = 1) q//2 (yaklaşık 48) ölçeğinde şifreleme ve gizli anahtarla çözme
mesaj_bit = 1
sifreli = (b + mesaj_bit * (q // 2)) % q

# Alıcı gizli anahtar s'yi bildiği için A.s'yi çıkarır; geriye sadece (e + mesaj * 48) kalır!
fark = (sifreli - ic_carpim) % q
cozulen_bit = 1 if abs(fark - (q // 2)) < (q // 4) else 0
print(f"Gürültülü b={b} | Şifreli={sifreli} | Fark={fark} (48+1) -> Çözülen Bit: {cozulen_bit}")
```
Şu zarafete bak:
- Gizli anahtar $\mathbf{s}$'yi **bilmeyen** saldırgan (veya kuantum bilgisayar) için $b$ değeri rastgele bir sayıdan ayırt edilemez!
- Gizli anahtar $\mathbf{s}$'yi **bilen** meşru alıcı ise $\mathbf{A}\mathbf{s}$ çarpımını çıkarıp attığında elinde sadece `mesaj * 48 + 1` kalır; $\pm 1$ gürültüsünü yuvarlayarak mesajın $0$ mı ($0 \pm 1$) yoksa $1$ mi ($48 \pm 1$) olduğunu %100 doğru okur!
:::

::: anlat 4. NIST Post-Quantum Cryptography Standartları (FIPS 203, 204, 205)
ABD Ulusal Standartlar ve Teknoloji Enstitüsü (**`NIST`**), 8 yıl süren küresel kriptanaliz yarışmasının ardından 2024'te resmi Kuantum-Sonrası Kriptografi standartlarını yayınladı. Bir güvenlik uzmanı olarak bu 3 kodu ezbere bilmelisin:

| Eski Klasik Algoritma (Shor Kırar ❌) | Yeni NIST PQC Standardı (Kuantum-Güvenli ✅) | Matematiksel Temeli | Kullanım Alanı |
| :--- | :--- | :--- | :--- |
| **`RSA` / `ECDH`** *(Anahtar Değişimi)* | **`FIPS 203 · ML-KEM` (`CRYSTALS-Kyber`)** | **`Module-LWE`** *(Modül Kafeslerinde Hatalı Öğrenme)* | TLS 1.3, HTTPS, VPN, Signal/iMessage/Chrome anahtar kapsülleme (`Key Encapsulation`). |
| **`RSA` / `ECDSA`** *(Dijital İmza)* | **`FIPS 204 · ML-DSA` (`CRYSTALS-Dilithium`)** | **`Module-LWE` & `Module-SIS`** | Yazılım güncellemeleri, TLS sertifikaları ve kimlik doğrulama imzaları. |
| **`ECDSA` / `Ed25519`** *(Yedek İmza)* | **`FIPS 205 · SLH-DSA` (`SPHINCS+`)** | **`Stateless Hash-Based Signatures`** | Kafes matematiğine bile güvenmek istemeyen kritik sistemler için saf `Hash` tabanlı imza. |

### 🛡️ `Hybrid Mode` (Hibrit Geçiş Mimarisi): `X25519MLKEM768`
Bugün Chrome, Cloudflare, AWS ve OpenSSH kuantum-sonrası şifrelemeye geçerken eski `Elliptic Curve (X25519)` algoritmasını silip sadece `ML-KEM (Kyber)` koymuyor; **ikisini birleştiriyor (`Hybrid Key Exchange`)!**
Neden? Eğer gelecekte `ML-KEM` matematiğinde klasik bir kusur bulunursa `X25519` korur; eğer kuantum bilgisayar çıkarsa `ML-KEM` korur!
:::

::: tahmin LWE Şifre Çözmede Gürültü Toleransı (Decryption Noise Margin)
Mod $q = 100$ üzerinde çalışan bir `LWE` şifrelemesinde $0$ biti $0$'a, $1$ biti ise $\lfloor q/2 \rfloor = 50$'ye kodlanıyor. Alıcı $\mathbf{A}\mathbf{s}$ terimini çıkardığında sonuç $50$'ye $25$'ten ($q/4$) daha yakınsa $1$, değilse $0$ olarak çözülüyor. Hata terimi $e = -3$ olduğunda $1$ bitinin nasıl çözüldüğünü hesaplayan kodun çıktısı nedir?

```python
q = 100
kodlanan = 1 * (q // 2)  # 50
gurultulu_fark = kodlanan + (-3)  # 47
cozulen = 1 if abs(gurultulu_fark - 50) < 25 else 0
print(f"Fark: {gurultulu_fark} | Tolerans Siniri: <25 | Cozulen Bit: {cozulen}")
```

???

```cikti
Fark: 47 | Tolerans Siniri: <25 | Cozulen Bit: 1
```
$1$ biti $50$ olarak kodlandığında ve üzerine $e = -3$ gürültüsü bindiğinde fark $47$ olur. $47$ değeri $50$'ye sadece $3$ birim uzaklıktadır ($3 < 25$ eşiği içinde kaldığı için) gürültü başarıyla temizlenir ve bit `1` olarak çözülür.
:::

::: gorev 1 · Oyuncak LWE: Bir Biti Gürültülü Denklemlerle Şifrelemek
Regev'in LWE şifrelemesinin en küçük hâli. Gizli anahtar $s \in \mathbb{Z}_q^n$; açık anahtar $m$ tane gürültülü denklemdir: $b_i = \langle A_i, s \rangle + e_i \bmod q$. `lwe_bit_sifrele_coz(A, s, e, q, alt_kume, bit)` işlevini yaz.

**Adımlar:**
1. Açık anahtar: $b_i = (A_i \cdot s + e_i) \bmod q$ (Python `%` negatif gürültüyü de doğru sarar).
2. Şifreleme (seçilen `alt_kume` $S$ ile): $u = \sum_{i \in S} A_i \bmod q$ (vektör), $v = \left(\sum_{i \in S} b_i + \text{bit} \cdot \lfloor q/2 \rfloor\right) \bmod q$.
3. Çözme: $d = (v - \langle u, s \rangle) \bmod q$. $d$, $q/2$'ye 0'dan daha yakınsa bit 1: tam sayılarla `q < 4·d < 3·q` ise 1, değilse 0.
4. Çıktı: `{"b": [...], "u": [...], "v": int, "d": int, "cozulen_bit": 0|1, "dogru_mu": bool, "toplam_gurultu": sum(e_i, i ∈ S)}`.

**Doğrulama:** `A` boş olmayan, satırları `s` ile aynı uzunlukta tam sayı matrisi; `e` uzunluğu `A`'nınkiyle aynı tam sayı listesi; `q >= 5`; `alt_kume` boş olmayan, tekrarsız, geçerli indeks listesi; `bit` 0 ya da 1 olmalı (`bool` değil). Değilse `ValueError`.

Toplam gürültü $q/4$'ü aşınca çözme bozulur: LWE'nin güvenliği de, doğruluğu da bu gürültünün büyüklüğüne bağlıdır.

```starter
def lwe_bit_sifrele_coz(A, s, e, q, alt_kume, bit):
    # KUSURLU BAŞLANGIÇ: gürültüyü yok sayıp biti açıkça taşıyor
    return {"b": [], "u": [], "v": bit, "d": bit, "cozulen_bit": bit, "dogru_mu": True, "toplam_gurultu": 0}

print(lwe_bit_sifrele_coz([[1, 2], [5, 6], [10, 20], [3, 3]], [3, 7], [1, -1, 2, 0], 97, [0, 2], 1))
```

```test
fn = need("lwe_bit_sifrele_coz")
A = [[1, 2], [5, 6], [10, 20], [3, 3]]
r = fn(A, [3, 7], [1, -1, 2, 0], 97, [0, 2], 1)
eq(r["b"], [18, 56, 75, 30], "b0 = 3+14+1, b1 = 15+42-1, b2 = 172 mod 97, b3 = 9+21")
eq(r["u"], [11, 22], "A0 + A2")
eq(r["v"], 44, "18 + 75 + 48 = 141 ≡ 44 (mod 97)")
eq(r["d"], 51, "d = toplam gürültü 3 + 48")
eq(r["cozulen_bit"], 1, "51, q/2 = 48.5'e yakın")
eq(r["dogru_mu"], True, "doğru çözüldü")
r0 = fn(A, [3, 7], [1, -1, 2, 0], 97, [0, 2], 0)
eq(r0["d"], 3, "bit 0: d yalnız gürültü")
eq(r0["cozulen_bit"], 0, "3, 0'a yakın")
rb = fn(A, [3, 7], [30, 0, 30, 0], 97, [0, 2], 0)
eq(rb["toplam_gurultu"], 60, "büyük gürültü")
eq(rb["d"], 60, "d = 60 > q/4")
eq(rb["dogru_mu"], False, "gürültü q/4'ü aşınca 0, 1 diye çözülür")
eq(fn(A, [3, 7], [1, -1, 2, 0], 97, [1], 1)["d"], 47, "tek satır: gürültü -1 + 48")
raises(ValueError, fn, A, [3], [1, -1, 2, 0], 97, [0], 1)
raises(ValueError, fn, [[]], [], [0], 97, [0], 1)
raises(ValueError, fn, A, [3, 7], [1, -1, 2], 97, [0], 1)
raises(ValueError, fn, A, [3, 7], [1, -1, 2, 0], 4, [0], 1)
raises(ValueError, fn, A, [3, 7], [1, -1, 2, 0], 97, [0, 0], 1)
raises(ValueError, fn, A, [3, 7], [1, -1, 2, 0], 97, [4], 1)
raises(ValueError, fn, A, [3, 7], [1, -1, 2, 0], 97, [], 1)
raises(ValueError, fn, A, [3, 7], [1, -1, 2, 0], 97, [0], 2)
raises(ValueError, fn, A, [3, 7], [1, -1, 2, 0], 97, [0], True)
eq(fn([[1]], [1], [0], 5, [0], 1)["cozulen_bit"], 1, "q = 5 en küçük geçerli modül")
_sarilan = fn([[1]], [0], [-1], 8, [0], 0)
eq(_sarilan["toplam_gurultu"], -1, "Gürültü işaretli raporlanır")
eq(_sarilan["d"], 7, "Negatif fark mod 8 altında 7 olur")
eq(_sarilan["cozulen_bit"], 0, "7, modüler çemberde sıfırın komşusudur")
eq(fn([[1]], [0], [-1], 8, [0], 1)["cozulen_bit"], 1,
   "Aynı gürültüyle 1 için fark 3 olur ve orta bölgeye düşer")
eq(fn([[1]], [0], [2], 8, [0], 0)["cozulen_bit"], 0, "4d = q tam sınırda: kesin eşitsizlik, 0")
eq(fn([[1]], [0], [6], 8, [0], 0)["cozulen_bit"], 0, "4d = 3q tam sınırda: 0")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def _tam(v):\n    return isinstance(v, int) and (not isinstance(v, bool))\n\ndef lwe_bit_sifrele_coz(A, s, e, q, alt_kume, bit):\n    if not isinstance(s, list) or not s or (not all((_tam(x) for x in s))):\n        raise ValueError('s boş olmayan tam sayı listesi olmalı')\n    n = len(s)\n    if not isinstance(A, list) or not A or (not all((isinstance(r, list) and len(r) == n and all((_tam(x) for x in r)) for r in A))):\n        raise ValueError('A satırları s ile aynı uzunlukta tam sayı listeleri olmalı')\n    m = len(A)\n    if not isinstance(e, list) or len(e) != m or (not all((_tam(x) for x in e))):\n        raise ValueError('e, A ile aynı uzunlukta tam sayı listesi olmalı')\n    if not _tam(q) or q < 5:\n        raise ValueError('q >= 5 tam sayı olmalı')\n    if not isinstance(alt_kume, list) or not alt_kume or len(set(alt_kume)) != len(alt_kume) or (not all((_tam(i) and 0 <= i < m for i in alt_kume))):\n        raise ValueError('alt_kume boş olmayan, tekrarsız, geçerli indeks listesi olmalı')\n    if not _tam(bit) or bit not in (0, 1):\n        raise ValueError('bit 0 ya da 1 olmalı')\n    b = [(sum((a * x for a, x in zip(A[i], s))) + e[i]) % q for i in range(m)]\n    u = [sum((A[i][j] for i in alt_kume)) % q for j in range(n)]\n    v = (sum((b[i] for i in alt_kume)) + bit * (q // 2)) % q\n    d = (v - sum((x * y for x, y in zip(u, s)))) % q\n    coz = 1 if q < 4 * d < 3 * q else 0\n    return {'b': b, 'u': u, 'v': v, 'd': d, 'cozulen_bit': coz, 'dogru_mu': coz == bit, 'toplam_gurultu': sum((e[i] for i in alt_kume))}", 'referans', 'exec'), _REF)
_t, _g = _ff(lwe_bit_sifrele_coz, _REF['lwe_bit_sifrele_coz'], ([[1, 2], [5, 6], [10, 20], [3, 3]], [3, 7], [1, -1, 2, 0], 97, [0, 2], 1), tohum=2929, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (lwe_bit_sifrele_coz): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def _tam(v):
    return isinstance(v, int) and not isinstance(v, bool)

def lwe_bit_sifrele_coz(A, s, e, q, alt_kume, bit):
    if not isinstance(s, list) or not s or not all(_tam(x) for x in s):
        raise ValueError("s boş olmayan tam sayı listesi olmalı")
    n = len(s)
    if not isinstance(A, list) or not A or not all(isinstance(r, list) and len(r) == n and all(_tam(x) for x in r) for r in A):
        raise ValueError("A satırları s ile aynı uzunlukta tam sayı listeleri olmalı")
    m = len(A)
    if not isinstance(e, list) or len(e) != m or not all(_tam(x) for x in e):
        raise ValueError("e, A ile aynı uzunlukta tam sayı listesi olmalı")
    if not _tam(q) or q < 5:
        raise ValueError("q >= 5 tam sayı olmalı")
    if (not isinstance(alt_kume, list) or not alt_kume or len(set(alt_kume)) != len(alt_kume)
            or not all(_tam(i) and 0 <= i < m for i in alt_kume)):
        raise ValueError("alt_kume boş olmayan, tekrarsız, geçerli indeks listesi olmalı")
    if not _tam(bit) or bit not in (0, 1):
        raise ValueError("bit 0 ya da 1 olmalı")
    b = [(sum(a * x for a, x in zip(A[i], s)) + e[i]) % q for i in range(m)]
    u = [sum(A[i][j] for i in alt_kume) % q for j in range(n)]
    v = (sum(b[i] for i in alt_kume) + bit * (q // 2)) % q
    d = (v - sum(x * y for x, y in zip(u, s))) % q
    coz = 1 if q < 4 * d < 3 * q else 0
    return {"b": b, "u": u, "v": v, "d": d, "cozulen_bit": coz, "dogru_mu": coz == bit,
            "toplam_gurultu": sum(e[i] for i in alt_kume)}
```

```hint
Her toplamın sonunda `% q` al. Çözmede $d$ yaklaşık `bit·⌊q/2⌋ + toplam gürültü` olur; karar için `q < 4*d < 3*q` yeter.
```
:::

::: anlat Sınır
Ders kafesleri, LWE'yi, NIST PQC standartlarını ve hibrit X25519MLKEM768 geçişini anlatır; görev oyuncak bir Regev şifrelemesiyle tek bit şifreler, gerçek ML-KEM anahtar değişimi yapılmaz. LWE güvenliği boyut, modül ve gürültü dağılımı seçimine bağlıdır; derste gösterilen küçük örnekler kırılabilir oyuncaklardır. Kuantum bilgisayarların kafes problemlerini verimli çözmediği matematiksel bir kanıt değil, bugünkü en iyi bilgidir. Gerçek dünyadaki tehlike çoğu zaman algoritmadan değil, zamanlama/güç yan kanallarından ve hatalı gerçeklemeden gelir (örneğin Kyber gerçeklemelerindeki KyberSlash zamanlama açığı).

Kaynaklar: [Regev 2005 (arXiv sürümü 2024) - On Lattices, Learning with Errors, Random Linear Codes, and Cryptography](https://arxiv.org/abs/2401.03703), [NIST 2024 - FIPS 203: Module-Lattice-Based Key-Encapsulation Mechanism Standard](https://csrc.nist.gov/pubs/fips/203/final), [NIST 2024 - FIPS 204: Module-Lattice-Based Digital Signature Standard](https://csrc.nist.gov/pubs/fips/204/final).
:::

