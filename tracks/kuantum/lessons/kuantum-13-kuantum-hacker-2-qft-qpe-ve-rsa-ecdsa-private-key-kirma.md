---
id: kuantum-13
title: "Kuantum Hacker 2: QFT, Phase Estimation ve RSA/ECDSA Private Key Kırma (HNDL & Continued Fractions)"
summary: "QFT/QPE ölçüm çıktısından Continued Fractions (Sürekli Kesirler) algoritmasıyla gizli periyot r'yi çıkar; RSA modülünü çarpanlarına ayırıp özel anahtar d'yi kurtar ve ECDSA açık anahtarlarının 2D QFT ile nasıl kırıldığını analiz et."
track: kuantum
order: 13
duration_minutes: 45
difficulty: ileri
xp: 330
prerequisites: [kuantum-12]
tags: [shors-algorithm, qft, quantum-phase-estimation, continued-fractions, rsa-cracking, ecdsa-cracking, hndl]
esleme: kuantum-12, kuantum-17
---

::: anlat 1. Kuantum Bilgisayar Ekrana Doğrudan "Periyot r = 4" Yazmaz! (QFT ve Continued Fractions)
Popüler anlatımlarda **Shor's Algorithm** anlatılırken hep *"Kuantum bilgisayar `QFT` uygular ve periyot $r$'yi verir"* denir ve geçilir.
Oysa gerçek bir **Kuantum Hacker** devreyi çalıştırdığında ekranda $r$ sayısını **görmez**! Peki ekranda ne görür ve oradan $r$'yi nasıl çıkarır?

### 📐 Adım Adım QFT Ölçümü ve `Continued Fractions` (Sürekli Kesirler) Motoru:
1. Çarpanlarına ayırmak istediğimiz RSA modülü $N$ için, büyüklüğü $Q = 2^m > N^2$ olan bir kuantum üst yazmacı kurarız.
2. Örneğin $N = 15$ ve $a = 7$ için gerçek gizli periyot $r = 4$'tür; üst yazmaç boyutumuz $Q = 2^{11} = 2048$ (veya $N=21, a=2, r=6$ için $Q = 512$) olsun.
3. **`Quantum Fourier Transform (QFT)`** uygulandıktan sonra üst yazmaç ölçüldüğünde, olasılık dalgaları yalnızca $\frac{k}{r}$ kesrinin $Q$ katına en yakın tam sayılarda zirve (`Peak`) yapar:
   $$y \approx k \cdot \frac{Q}{r} \implies \frac{y}{Q} \approx \frac{k}{r}$$
4. Örneğin $N = 21$, $a = 2$ (gerçek periyot $r = 6$) ve $Q = 512$ iken kuantum bilgisayarı ölçtüğümüzde ekranda **$y = 85$** tam sayısı çıkar!
   - Biz yalnız $y = 85$ ve $Q = 512$ sayılarını biliyoruz: $\frac{85}{512} = 0.166015625$.
   - Peki $0.166015625$ ondalık sayısına en yakın, paydası $N=21$'den küçük olan gerçek kesir ($\frac{k}{r}$) hangisidir?

İşte burada klasik sayı teorisinin şaheseri olan **`Continued Fractions Algorithm` (Sürekli Kesirler Algoritması)** devreye girer! Her rasyonel sayı ardışık bölme (`Euclidean Algorithm`) adımlarıyla şu merdiven kesir biçiminde açılır:

$$\frac{y}{Q} = a_0 + \cfrac{1}{a_1 + \cfrac{1}{a_2 + \cfrac{1}{a_3 + \dots}}}$$

$\frac{85}{512}$ için bölmeleri yapalım:
- $85 / 512 = 0 + 1 / (512 / 85)$
- $512 = \mathbf{6} \times 85 + 2 \implies \frac{85}{512} = \cfrac{1}{\mathbf{6} + \cfrac{1}{42 + \cfrac{1}{2}}}$

Bu merdiveni her basamakta kestiğimizde elde ettiğimiz yakınsak kesirlere (**`Convergents` $p_i / q_i$**) bakarız:
- 1. Yakınsak kesir: **$\frac{1}{6}$** $\implies$ Payda adayı **$r = 6$**!
- Hemen kontrol ederiz: $2^6 \bmod 21 = 64 \bmod 21 = \mathbf{1}$! **Periyot $r = 6$ milisaniyede yakalandı!**

```python
# QFT ölçümü y=85, Q=512 değerinden Continued Fractions ile r=6 periyodunu yakalama
def yakinsak_paydalari_bul(y, Q, maks_N):
    pay, payda = y, Q
    q_onceki, q_simdi = 1, 0
    adaylar = []
    while payda != 0:
        tam = pay // payda
        pay, payda = payda, pay % payda
        q_onceki, q_simdi = q_simdi, tam * q_simdi + q_onceki
        if 1 <= q_simdi < maks_N and q_simdi not in adaylar:
            adaylar.append(q_simdi)
    return adaylar

print("y=85, Q=512 için yakınsak paydalar (r adayları):", yakinsak_paydalari_bul(85, 512, 21))
```
:::

::: anlat 2. Periyot r'den RSA Özel Anahtarına (d) ve ECDSA Kırmaya Tam Saldırı Zinciri
Periyot $r$ (çift sayı ve $a^{r/2} \not\equiv -1 \pmod N$) bulunduktan sonra bir **Kuantum Hacker** için `RSA` şifresini tamamen ele geçirmek 4 satırlık modüler aritmetiktir:

```
[QFT Ölçümü: y] ──► [Continued Fractions: r] ──► [gcd(a^(r/2)±1, N) -> p, q]
                                                            │
[HNDL Şifreli Trafik Çözüldü: M = C^d mod N] ◄── [d = e^(-1) mod (p-1)(q-1)]
```

1. **Asal Çarpanları Ayır:** $p = \gcd(a^{r/2} - 1, N)$ ve $q = \gcd(a^{r/2} + 1, N)$.
2. **Euler Totient ($\phi(N)$) Hesapla:** $\phi(N) = (p - 1)(q - 1)$.
3. **Özel Anahtarı (`Private Key` $d$) Çıkar:** Genişletilmiş Öklid Algoritması (`Extended Euclidean Algorithm` / `pow(e, -1, phi_N)`) ile $e \cdot d \equiv 1 \pmod{\phi(N)}$ denklemini çöz!
4. **Yıllar Önce Kaydedilen (`HNDL`) Şifreli Veriyi Çöz:** $M = C^d \pmod N$.

---

### 🪙 Peki Bitcoin, Ethereum ve TLS'de Kullanılan `ECDSA` (Eliptik Eğri) Nasıl Kırılır?
Birçok yazılımcı *"Shor algoritması çarpanlara ayırma yapıyor, o yüzden sadece RSA'yı kırar; Bitcoin `secp256k1` eliptik eğrisini (`ECDSA`) kullanıyor!"* diye düşünür. **Bu ölümcül bir yanılgıdır!**
- `ECDSA` güvenliği **`Elliptic Curve Discrete Logarithm Problem (ECDLP)`** üzerine kuruludur: Eğri üzerindeki üreteç noktası $G$ ve açık anahtar noktası $Q = d \cdot G$ biliniyorken, skaler çarpan (özel anahtar) $d$'yi bulmak klasik bilgisayarda imkansızdır ($2^{128}$ işlem).
- **Kuantum Hacker Saldırısı (2 Boyutlu Shor / QPE):**
  Saldırgan iki kuantum yazmacı ($|u\rangle$ ve $|v\rangle$) hazırlar ve süperpozisyonda şu eliptik eğri nokta toplamasını hesaplar:
  $$f(u, v) = u \cdot G + v \cdot Q = (u + v \cdot d) \cdot G$$
  Eğrinin mertebesi $n$ olduğunda, bu iki değişkenli fonksiyon $u + v \cdot d \equiv 0 \pmod n$ doğrusu boyunca periyodiktir!
  Her iki yazmaca **`Quantum Fourier Transform (QFT)`** uygulayıp ölçtüğümüzde $(k_1, k_2)$ çiftini alırız. QFT yalnız bu periyot doğrusuna "dik" olan, yani her periyot $(u, v)$ için $k_1 u + k_2 v \equiv 0 \pmod n$ sağlayan çiftleri verir; doğru $(-d, 1)$ yönünde olduğundan:
  $$k_2 \equiv d \cdot k_1 \pmod n \implies \mathbf{d \equiv k_2 \cdot k_1^{-1} \pmod n}$$
- Hatta 256-bitlik `ECDSA` anahtarını kırmak (~2.330 mantıksal Qubit), 2048-bitlik `RSA` anahtarını kırmaktan (~4.098 mantıksal Qubit) **daha az Qubit** gerektirir! Yani Q-Day geldiğinde `ECDSA` (`secp256k1` / `P-256`), `RSA-2048`'den bile **daha önce** düşecektir!
:::

::: tahmin Shor Algoritmasıyla RSA-15 Özel Anahtarını (d) Kırmak
Açık anahtarı $(N = 15, e = 3)$ olan küçük bir RSA sisteminde $a = 7$ tabanı için Shor devresinden periyot $r = 4$ bulunmuştur. (Aynı yöntem $N = 33$, $a = 2$ için işe yaramaz: periyot $r = 10$ çıkar ama $2^5 = 32 \equiv -1 \pmod{33}$ olduğundan başka bir $a$ denenmelidir.) Aşağıdaki kodun kurtardığı özel anahtar $d$ nedir?

```python
import math
N, e, a, r = 15, 3, 7, 4
yarim = pow(a, r // 2, N)
p = math.gcd(yarim - 1, N)
q = math.gcd(yarim + 1, N)
phi = (p - 1) * (q - 1)
d = pow(e, -1, phi)
print(f"p={p}, q={q} | phi={phi} | Kurtarilan Private Key d={d}")
```

???
```cikti
p=3, q=5 | phi=8 | Kurtarilan Private Key d=3
```
$7^{4/2} \bmod 15 = 49 \bmod 15 = 4$ olur. $\gcd(4-1, 15) = 3$ ve $\gcd(4+1, 15) = 5$ ile çarpanlar bulunur. $\phi(15) = 2 \times 4 = 8$ üzerinden $3^{-1} \bmod 8 = \mathbf{3}$ olarak özel anahtar $d=3$ ele geçirilir!
:::

::: gorev 1 · Shor Son-İşleme Motoru: Continued Fractions (Sürekli Kesirler) ile Ölçümden Periyot r Çıkarma
`surekli_kesir_periyot_bul(olcum_y, q_boyutu, maks_N, taban_a, mod_N)` işlevini yaz:
1. `olcum_y / q_boyutu` kesrinin sürekli kesir yakınsak paydalarını (`q_onceki, q_simdi = 1, 0` başlangıcıyla `while payda != 0:` döngüsünde `tam = pay // payda`, `pay, payda = payda, pay % payda`, `q_onceki, q_simdi = q_simdi, tam * q_simdi + q_onceki`) hesapla.
2. `1 <= q_simdi < maks_N` koşulunu sağlayan paydaları sırasıyla ve tekrarsız olarak `payda_adaylari` listesine ekle.
3. `payda_adaylari` içinde `pow(taban_a, r, mod_N) == 1` eşitliğini sağlayan **ilk** `r` değerini `bulunan_periyot_r` olarak seç (hiçbiri sağlamazsa `None`).
4. `{"payda_adaylari": payda_adaylari, "bulunan_periyot_r": bulunan_r, "dogrulandi_mi": bool(bulunan_r is not None)}` döndür.

```starter
# KUSURLU BAŞLANGIÇ KODU: Sürekli kesirler (Continued Fractions) yakınsak payda döngüsünü yaz.
def surekli_kesir_periyot_bul(olcum_y, q_boyutu, maks_N, taban_a, mod_N):
    return {
        "payda_adaylari": [],
        "bulunan_periyot_r": None,
        "dogrulandi_mi": False
    }

print(surekli_kesir_periyot_bul(85, 512, 21, 2, 21))
```
```test
f = need("surekli_kesir_periyot_bul")
# N=21, a=2 -> gerçek periyot r=6. Q=512 iken y=85 ölçümü (85/512 ≈ 1/6)
r1 = f(85, 512, 21, 2, 21)
ok(r1["bulunan_periyot_r"] == 6 and r1["dogrulandi_mi"] is True and 6 in r1["payda_adaylari"], "y=85/512 ölçümünden N=21 için r=6 periyodu çıkarıldı")

# N=15, a=7 -> gerçek periyot r=4. Q=256 iken y=192 ölçümü (192/256 = 3/4)
r2 = f(192, 256, 15, 7, 15)
ok(r2 == {"payda_adaylari": [1, 4], "bulunan_periyot_r": 4, "dogrulandi_mi": True}, "y=192/256 ölçümünden N=15 için r=4 periyodu çıkarıldı")

# N=35, a=2 -> gerçek periyot r=12. Q=2048 iken y=171 ölçümü (171/2048 ≈ 1/12)
r3 = f(171, 2048, 35, 2, 35)
ok(r3["bulunan_periyot_r"] == 12 and r3["dogrulandi_mi"] is True, "y=171/2048 ölçümünden N=35 için r=12 periyodu çıkarıldı")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def surekli_kesir_periyot_bul(olcum_y, q_boyutu, maks_N, taban_a, mod_N):\n    pay, payda = (olcum_y, q_boyutu)\n    q_onceki, q_simdi = (1, 0)\n    adaylar = []\n    while payda != 0:\n        tam = pay // payda\n        pay, payda = (payda, pay % payda)\n        q_yeni = tam * q_simdi + q_onceki\n        q_onceki, q_simdi = (q_simdi, q_yeni)\n        if 1 <= q_simdi < maks_N and q_simdi not in adaylar:\n            adaylar.append(q_simdi)\n    bulunan = None\n    for r in adaylar:\n        if pow(taban_a, r, mod_N) == 1:\n            bulunan = r\n            break\n    return {'payda_adaylari': adaylar, 'bulunan_periyot_r': bulunan, 'dogrulandi_mi': bool(bulunan is not None)}", 'referans', 'exec'), _REF)
_t, _g = _ff(surekli_kesir_periyot_bul, _REF['surekli_kesir_periyot_bul'], (85, 512, 21, 2, 21), tohum=3615, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (surekli_kesir_periyot_bul): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
def surekli_kesir_periyot_bul(olcum_y, q_boyutu, maks_N, taban_a, mod_N):
    pay, payda = olcum_y, q_boyutu
    q_onceki, q_simdi = 1, 0
    adaylar = []
    while payda != 0:
        tam = pay // payda
        pay, payda = payda, pay % payda
        q_yeni = tam * q_simdi + q_onceki
        q_onceki, q_simdi = q_simdi, q_yeni
        if 1 <= q_simdi < maks_N and q_simdi not in adaylar:
            adaylar.append(q_simdi)
    bulunan = None
    for r in adaylar:
        if pow(taban_a, r, mod_N) == 1:
            bulunan = r
            break
    return {
        "payda_adaylari": adaylar,
        "bulunan_periyot_r": bulunan,
        "dogrulandi_mi": bool(bulunan is not None)
    }
```
```hint
`while payda != 0:` döngüsünde `tam = pay // payda`, `pay, payda = payda, pay % payda` ve `q_onceki, q_simdi = q_simdi, tam * q_simdi + q_onceki` adımlarını uygula; `pow(taban_a, r, mod_N) == 1` veren ilk `r`'yi seç.
```
:::

::: gorev 2 · Bulunan Periyot r ile RSA Modülünü Çarpanlarına Ayırma ve Private Key (d) Kurtarma
`rsa_ozel_anahtar_kir(N, e, taban_a, periyot_r)` işlevini yaz:
1. `yarim = pow(taban_a, periyot_r // 2, N)` değerini hesapla.
2. `p = math.gcd(yarim - 1, N)` ve `q = math.gcd(yarim + 1, N)` asal çarpanlarını bulup küçükten büyüğe sıralı `carpanlar = sorted([p, q])` listesini oluştur.
3. $\phi(N) = (p - 1)(q - 1)$ ve özel anahtar `ozel_anahtar_d = pow(e, -1, phi_N)` değerlerini hesapla.
4. `{"carpanlar": carpanlar, "phi_N": phi_N, "ozel_anahtar_d": ozel_anahtar_d, "anahtar_kirildi_mi": bool(p * q == N and p > 1 and q > 1 and (e * ozel_anahtar_d) % phi_N == 1)}` döndür.

```starter
import math
# KUSURLU BAŞLANGIÇ KODU: gcd ile çarpanları ve pow(e, -1, phi_N) ile d özel anahtarını bul.
def rsa_ozel_anahtar_kir(N, e, taban_a, periyot_r):
    return {
        "carpanlar": [1, N],
        "phi_N": N - 1,
        "ozel_anahtar_d": 1,
        "anahtar_kirildi_mi": False
    }

print(rsa_ozel_anahtar_kir(15, 3, 7, 4))
```
```test
f = need("rsa_ozel_anahtar_kir")
ok(f(15, 3, 7, 4) == {"carpanlar": [3, 5], "phi_N": 8, "ozel_anahtar_d": 3, "anahtar_kirildi_mi": True}, "RSA-15 (3x5) özel anahtarı d=3 başarıyla kurtarıldı")
ok(f(21, 5, 2, 6) == {"carpanlar": [3, 7], "phi_N": 12, "ozel_anahtar_d": 5, "anahtar_kirildi_mi": True}, "RSA-21 (3x7) özel anahtarı d=5 başarıyla kurtarıldı")
ok(f(77, 7, 2, 30) == {"carpanlar": [7, 11], "phi_N": 60, "ozel_anahtar_d": 43, "anahtar_kirildi_mi": True}, "RSA-77 (7x11) özel anahtarı d=43 başarıyla kurtarıldı")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef rsa_ozel_anahtar_kir(N, e, taban_a, periyot_r):\n    yarim = pow(taban_a, periyot_r // 2, N)\n    p = math.gcd(yarim - 1, N)\n    q = math.gcd(yarim + 1, N)\n    carpanlar = sorted([p, q])\n    phi_N = (carpanlar[0] - 1) * (carpanlar[1] - 1)\n    d = pow(e, -1, phi_N)\n    ok_mu = carpanlar[0] * carpanlar[1] == N and carpanlar[0] > 1 and (e * d % phi_N == 1)\n    return {'carpanlar': carpanlar, 'phi_N': phi_N, 'ozel_anahtar_d': d, 'anahtar_kirildi_mi': bool(ok_mu)}", 'referans', 'exec'), _REF)
_t, _g = _ff(rsa_ozel_anahtar_kir, _REF['rsa_ozel_anahtar_kir'], (15, 3, 7, 4), tohum=3032, en_cok=600, mod='gecerli', butce='oto', ekler=[(15, 3, 7, 4, )])
ok(_t, "farksal tarama (rsa_ozel_anahtar_kir): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def rsa_ozel_anahtar_kir(N, e, taban_a, periyot_r):
    yarim = pow(taban_a, periyot_r // 2, N)
    p = math.gcd(yarim - 1, N)
    q = math.gcd(yarim + 1, N)
    carpanlar = sorted([p, q])
    phi_N = (carpanlar[0] - 1) * (carpanlar[1] - 1)
    d = pow(e, -1, phi_N)
    ok_mu = (carpanlar[0] * carpanlar[1] == N and carpanlar[0] > 1 and (e * d) % phi_N == 1)
    return {
        "carpanlar": carpanlar,
        "phi_N": phi_N,
        "ozel_anahtar_d": d,
        "anahtar_kirildi_mi": bool(ok_mu)
    }
```
```hint
`yarim = pow(taban_a, periyot_r // 2, N)` üzerinden `math.gcd(yarim - 1, N)` ve `math.gcd(yarim + 1, N)` ile çarpanları al; `pow(e, -1, phi_N)` ile `d`'yi hesapla.
```
:::

::: gorev 3 · Shor'un Kırdığı Problem: Küçük Grupta Ayrık Logaritma (Baby-Step Giant-Step)
ECDSA'nın güvenliği **ayrık logaritma** problemine dayanır: açık anahtar $h = g^x$ verildiğinde gizli $x$'i bulmak. Shor'un algoritması bunu polinom zamanda çözer; en iyi genel klasik algoritmalar ise $O(\sqrt{n})$ adım ister. Bu görevde problemi çarpımsal grup $\mathbb{Z}_p^*$ üzerinde klasik **Baby-Step Giant-Step** ile çöz (eliptik eğri grubunda da aynı fikir çalışır). `ayrik_log_bsgs(g, h, p)` işlevini yaz.

**Kurallar:**
1. `p` 2'den büyük bir asal, `g` ve `h` $1 \le g, h < p$ tam sayılar olmalı (`bool` değil); değilse `ValueError`.
2. $m = \lceil \sqrt{p - 1} \rceil$ (`math.isqrt` ile tam sayı karekök kullan).
3. **Baby steps:** $j = 0..m-1$ için $g^j \bmod p$ değerlerini bir sözlüğe yaz (aynı değer tekrar ederse **en küçük** $j$ kalsın).
4. **Giant steps:** $c = g^{-m} \bmod p$; $\gamma = h$ ile başla, $i = 0..m-1$ için $\gamma$ sözlükteyse $x = i \cdot m + j$; değilse $\gamma \leftarrow \gamma \cdot c$.
5. Bulunamazsa `ValueError("çözüm yok")`.
6. Çıktı: `{"x": x, "m": m, "dogrulandi": pow(g, x, p) == h, "dev_adim": i + 1}`.

```starter
def ayrik_log_bsgs(g, h, p):
    # KUSURLU BAŞLANGIÇ: aramadan x = 0 döndürüyor
    return {"x": 0, "m": 1, "dogrulandi": False, "dev_adim": 0}

print(ayrik_log_bsgs(5, 8, 23))
```

```test
fn = need("ayrik_log_bsgs")
r = fn(5, 8, 23)
eq(r["x"], 6, "5^6 = 15625 ≡ 8 (mod 23)")
eq(r["m"], 5, "m = ceil(sqrt(22)) = 5")
eq(r["dogrulandi"], True, "bulunan x doğrulanmalı")
eq(r["dev_adim"], 2, "x = 1·5 + 1: ikinci dev adımda bulunur")
eq(fn(5, 1, 23)["x"], 0, "h = 1 için x = 0")
r2 = fn(2, pow(2, 77, 101), 101)
eq(r2["x"], 77, "2 mod 101'in üreteci; 2^77 → x = 77")
eq(r2["m"], 10, "m = ceil(sqrt(100)) = 10")
eq(fn(4, 2, 23)["x"], 6, "4^6 = 2^12 ≡ 2 (mod 23); en küçük çözüm")
raises(ValueError, fn, 2, 3, 7)
raises(ValueError, fn, 2, 3, 21)
raises(ValueError, fn, 0, 3, 23)
raises(ValueError, fn, True, 3, 23)
eq(fn(2, 2, 3)["x"], 1, "p = 3 en küçük geçerli asal: 2^1 = 2")
eq(fn(1, 1, 23)["x"], 0, "g = 1 geçerli taban")
r11 = fn(2, 3, 11)
eq(r11["x"], 8, "2^8 = 256 ≡ 3 (mod 11)")
eq(r11["m"], 4, "m = ceil(sqrt(10)) = 4 (p - 1 kullanılır, p - 2 değil)")
raises(ValueError, fn, 23, 3, 23)
raises(ValueError, fn, 5, 0, 23)
raises(ValueError, fn, 5, 23, 23)
raises(ValueError, fn, 1, 1, 2)
raises(ValueError, fn, 3, 1, 8)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile('import math\n\ndef _asal_mi(p):\n    if p < 3:\n        return False\n    k = 2\n    while k * k <= p:\n        if p % k == 0:\n            return False\n        k += 1\n    return True\n\ndef ayrik_log_bsgs(g, h, p):\n    for v in (g, h, p):\n        if isinstance(v, bool) or not isinstance(v, int):\n            raise ValueError(\'g, h, p tam sayı olmalı\')\n    if not _asal_mi(p):\n        raise ValueError("p 2\'den büyük asal olmalı")\n    if not (1 <= g < p and 1 <= h < p):\n        raise ValueError(\'1 <= g, h < p olmalı\')\n    n = p - 1\n    m = math.isqrt(n)\n    if m * m < n:\n        m += 1\n    tablo = {}\n    deger = 1\n    for j in range(m):\n        tablo.setdefault(deger, j)\n        deger = deger * g % p\n    c = pow(g, -m, p)\n    gamma = h\n    for i in range(m):\n        if gamma in tablo:\n            x = i * m + tablo[gamma]\n            return {\'x\': x, \'m\': m, \'dogrulandi\': pow(g, x, p) == h, \'dev_adim\': i + 1}\n        gamma = gamma * c % p\n    raise ValueError(\'çözüm yok\')', 'referans', 'exec'), _REF)
_t, _g = _ff(ayrik_log_bsgs, _REF['ayrik_log_bsgs'], (5, 8, 23), tohum=2405, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (ayrik_log_bsgs): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def _asal_mi(p):
    if p < 3:
        return False
    k = 2
    while k * k <= p:
        if p % k == 0:
            return False
        k += 1
    return True

def ayrik_log_bsgs(g, h, p):
    for v in (g, h, p):
        if isinstance(v, bool) or not isinstance(v, int):
            raise ValueError("g, h, p tam sayı olmalı")
    if not _asal_mi(p):
        raise ValueError("p 2'den büyük asal olmalı")
    if not (1 <= g < p and 1 <= h < p):
        raise ValueError("1 <= g, h < p olmalı")
    n = p - 1
    m = math.isqrt(n)
    if m * m < n:
        m += 1
    tablo = {}
    deger = 1
    for j in range(m):
        tablo.setdefault(deger, j)
        deger = deger * g % p
    c = pow(g, -m, p)
    gamma = h
    for i in range(m):
        if gamma in tablo:
            x = i * m + tablo[gamma]
            return {"x": x, "m": m, "dogrulandi": pow(g, x, p) == h, "dev_adim": i + 1}
        gamma = gamma * c % p
    raise ValueError("çözüm yok")
```

```hint
`m = math.isqrt(p - 1)`, gerekiyorsa bir artır. Sözlükte `setdefault` en küçük j'yi korur; `pow(g, -m, p)` modüler tersin kuvvetidir.
```
:::

::: anlat Sınır
Görevler Shor'un klasik son işlemesini (sürekli kesirlerle periyot çıkarma), periyottan RSA çarpanlarını ve özel anahtar d'yi bulmayı yazdırır; QFT ve phase estimation simüle edilmez, ölçüm sonucu hazır verilir. Gerçek ölçümden yanlış periyot ya da periyodun bir böleni çıkabilir; uygulama birkaç ölçüm ve doğrulama ister. Örnek modüller küçüktür ve klasik olarak anında çarpanlarına ayrılabilir. Ayrık logaritma görevi Shor'u değil, klasik baby-step giant-step yöntemini küçük bir çarpımsal grupta uygular; eliptik eğri grubu ve kuantum devre yoktur. HNDL tehdidinde kaydedilmiş trafiğin anahtar değişimi kırılır; forward secrecy bu tehdide karşı koruma sağlamaz.

Kaynaklar: [Shor 1995 - Polynomial-Time Algorithms for Prime Factorization and Discrete Logarithms on a Quantum Computer](https://arxiv.org/abs/quant-ph/9508027), [Kitaev 1995 - Quantum measurements and the Abelian Stabilizer Problem](https://arxiv.org/abs/quant-ph/9511026), [Roetteler vd. 2017 - Quantum resource estimates for computing elliptic curve discrete logarithms](https://arxiv.org/abs/1706.06752), [Gidney ve Ekerå 2019 - How to factor 2048 bit RSA integers in 8 hours using 20 million noisy qubits](https://arxiv.org/abs/1905.09749).
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Shor algoritmasını anlatırken "kuantum devre periyot $r$'yi ekrana basar" yanılgısını düzelt: QFT ölçümü sana doğrudan $r$'yi değil, $y/Q \approx k/r$ oranına yakın bir $y$ tam sayısını verir. Klasik bilgisayar bu kesri sürekli kesirlerle (Continued Fractions) açıp payda adaylarını dener ve $a^r \equiv 1 \pmod N$ doğrulamasıyla gerçek periyodu yakalar; oradan $\gcd(a^{r/2} \pm 1, N)$ ile RSA çarpanlarına, iki boyutlu QFT ile de ECDSA ayrık logaritmasına ulaşılır.

Bu yüzden "şimdi kaydet, sonra çöz" (HNDL) tehdidi bugünün şifreli trafiğini ve açık anahtarı zincire düşmüş cüzdanları doğrudan ilgilendirir. Savunma yalnızca anahtar boyutu büyütmek değil, ML-KEM ve ML-DSA gibi kuantum sonrası standartlara kriptografik çeviklikle geçmektir.
:::

::: dusun
Bitcoin ve Ethereum'da bir cüzdan adresi oluşturulduğunda, adres aslında `ECDSA Public Key`'in `SHA-256 / RIPEMD-160` veya `Keccak-256` özetidir (`Hash`). Cüzdan sahibi o adresten **hiç dışarıya para transferi yapmadığı sürece** açık anahtarı (`Public Key`) blokzincirde görünmez; yalnızca ilk para gönderme işlemini imzaladığı anda `Public Key` zincire yazılır.
Bir **Kuantum Hacker** gözüyle düşün: Neden bir adresten dışarıya işlem yapıp kalan bakiyeyi **aynı adreste bırakmak (`Address Reuse`)** kuantum çağında cüzdanın soyulmasına yol açar?
:::

::: ozet
- **`Quantum Fourier Transform (QFT)`** ve **`Quantum Phase Estimation (QPE)`**, periyodu $r$ olan modüler üs alma durumunu $y \approx k \cdot (Q / r)$ frekans tepelerine dönüştürür.
- Kuantum bilgisayardan okunan $y/Q$ kesrinden gerçek periyot $r$'yi kurtarmak için **`Continued Fractions (Sürekli Kesirler)`** yakınsak paydaları ($p_i / q_i$) kullanılır.
- Periyot $r$ bulunduğunda $\gcd(a^{r/2} \pm 1, N)$ ile `RSA` çarpanları ve $d \equiv e^{-1} \pmod{\phi(N)}$ özel anahtarı kırılır; 2 boyutlu `QFT` ise **`ECDSA` (`ECDLP`)** açık anahtarlarından özel anahtarı doğrudan çıkarır.
:::
