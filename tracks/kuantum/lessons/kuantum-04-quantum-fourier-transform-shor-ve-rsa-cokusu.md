---
id: kuantum-04
title: Quantum Fourier Transform (QFT), Shor's Algorithm ve RSA/ECC Çöküşü
summary: Peter Shor'un 1994'te internetin temelini sarsan keşfi: Çarpanlara ayırma problemini Period Finding (Periyot Bulma) problemine indirgemek, Quantum Fourier Transform (QFT) ve "Harvest Now, Decrypt Later" tehdidi.
esleme: kuantum-03, kuantum-05
---

::: anlat 1. İnternetin Kilidini Tutan Tek Matematiksel Varsayım: Integer Factorization
## QFT, period finding ve HNDL

Shor algoritmasında quantum period finding ile classical post-processing birlikte kullanılır. Bu derste QFT fikrini ve HNDL için zaman varsayımlarını inceleyeceksin. Quantum donanımın ne zaman yeterli olacağını bu küçük sayısal örnekler öngörmez.

- İki tane $1.024$ bitlik dev asal sayıyı ($p$ ve $q$) birbiriyle çarpmak ($N = p \times q$) dizüstü bilgisayarda **1 milisaniye** sürer.
- **AMA** sana sadece çarpım sonucu olan $2.048$ bitlik (617 basamaklı) $N$ sayısını verip *"Hangi iki asal sayıyı çarptım?"* (**`Integer Factorization`**) diye sorduğumda, dünyanın en hızlı klasik süperbilgisayarı (`General Number Field Sieve` algoritmasıyla) bunu bulmak için **milyonlarca yıl** çalışmak zorundadır!

Ta ki 1994 yılında o dönem AT&T Bell Labs'ta çalışan (bugün MIT'de olan) matematikçi **Peter Shor**, kuantum bilgisayarlar için **`Shor's Algorithm`**'ı yazana kadar!
- Klasik süperbilgisayarın **milyonlarca yılda** çözebileceği `RSA-2048` şifresini, hata düzeltmeli bir kuantum bilgisayar **`Shor's Algorithm` ile sadece birkaç saat içinde** kırabilir (**Üstel Hızlanma / `Exponential Speedup`**)!

**Kaynak ve sınır:** [IBM Quantum: quantum algorithms](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms). Sayısal örnekler eğitim ölçeğindedir; gerçek quantum hardware, standart PQC ürünü veya ağ üzerindeki bir hedef üzerinde kabul testi yapılmaz.
:::

::: anlat 2. Shor'un Dehası: Çarpanlara Ayırmayı "Müzik Notalarına (Periyot Bulmaya)" Dönüştürmek!
Şu soruyu düşün: *"Shor algoritması asal çarpanları nasıl buluyor? Tek tek bütün sayılara bölüyor mu?"*

Bir konferansta dinleyicilere *"Shor algoritması asal çarpanları nasıl buluyor? Tek tek bütün sayılara bölüyor mu?"* diye sor. Herkes *"Evet, süperpozisyonla hepsine aynı anda bölüyor"* diyecektir.
Oysa gerçek cevap çok daha zekicedir: **Shor algoritması bölme yapmaz; sayının içindeki gizli ritmi (`Period` / Periyot) dinler!**

### 🎵 Matematiksel Köprü: `Factoring` $\to$ `Period Finding` (Euler & Miller İndirgemesi)
Çarpanlarına ayırmak istediğimiz sayı $N = 15$ olsun ($3 \times 5$ olduğunu bilmiyoruz diyelim).
1. $N$ ile aralarında asal rastgele bir sayı seçelim: örneğin $a = 7$.
2. Şimdi şu modüler üs alma fonksiyonunun ($f(x) = a^x \bmod N$) sırasıyla $x = 0, 1, 2, 3, 4, 5, \dots$ için ürettiği kalanlara bakalım:
   - $x=0 \implies 7^0 \bmod 15 = \mathbf{1}$
   - $x=1 \implies 7^1 \bmod 15 = \mathbf{7}$
   - $x=2 \implies 7^2 \bmod 15 = 49 \bmod 15 = \mathbf{4}$
   - $x=3 \implies 7^3 \bmod 15 = 343 \bmod 15 = \mathbf{13}$
   - $x=4 \implies 7^4 \bmod 15 = \mathbf{1}$ *(BINGO! Başa döndü!)*
   - $x=5 \implies 7^5 \bmod 15 = \mathbf{7}$

Bak, dizi $[1, 7, 4, 13, \mathbf{1, 7, 4, 13}, 1, 7, 4, 13, \dots]$ şeklinde tam **$r = 4$** adımda bir kendini tekrar ediyor! Bu tekrar uzunluğuna **Periyot (`Period` $r = 4$)** denir.

### 🔓 Periyodu ($r$) Bulunca Şifre Nasıl Kırılır?
Eğer $a^r \equiv 1 \pmod N$ ise, $(a^r - 1)$ sayısı $N$'in tam katıdır. İki kare farkı özdeşliğinden:
$$(a^{r/2} - 1)(a^{r/2} + 1) \equiv 0 \pmod N$$
Yerine koyalım ($a=7, r=4 \implies a^{r/2} = 7^2 = 49$):
- $(49 - 1) = 48$ ile $15$'in En Büyük Ortak Böleni (`gcd(48, 15)`) = **$3$**!
- $(49 + 1) = 50$ ile $15$'in En Büyük Ortak Böleni (`gcd(50, 15)`) = **$5$**!
**Ve $15 = 3 \times 5$ şifresi tek hamlede kırıldı!**

```python
import math

def shor_periyottan_carpan_bul(N, a):
    # f(x) = a^x mod N dizisinin periyodunu (r) bulalım
    degerler = [pow(a, x, N) for x in range(1, N)]
    r = degerler.index(1) + 1
    # r çift sayıysa gcd(a^(r/2) - 1, N) ve gcd(a^(r/2) + 1, N) çarpanları verir!
    yarim = pow(a, r // 2, N)
    p = math.gcd(yarim - 1, N)
    q = math.gcd(yarim + 1, N)
    return {"N": N, "secilen_a": a, "periyot_r": r, "ilk_4_terim": [1] + degerler[:3], "carpanlar": sorted([p, q])}

print("N=15 (a=7) :", shor_periyottan_carpan_bul(15, 7))
print("N=77 (a=2) :", shor_periyottan_carpan_bul(77, 2))
```
:::

::: anlat 3. Quantum Fourier Transform (QFT): Samanlıktaki Ritmi Tek Seferde Yakalamak
Peki klasik bilgisayar neden $2.048$ bitlik bir sayı için bu $r$ periyodunu bulamıyor? Çünkü $2.048$ bitlik bir sayıda periyot $r \approx 10^{600}$ adım uzunluğunda olabilir; klasik bilgisayarın tekrar eden sayıyı görmesi için $10^{600}$ adım sayması gerekir!

Kuantum bilgisayar ise **`Quantum Fourier Transform (QFT)`** sayesinde bunu polinom sürede yapar (gerçekçi kaynak tahminleriyle `RSA-2048` için saatler–günler mertebesinde):
1. **Adım 1 (`Superposition` & `Modular Exponentiation`):** Birinci yazmaçtaki tüm $x$ değerlerini süperpozisyona sokar ve ikinci yazmaçta $f(x) = a^x \bmod N$ değerini kuantum paralelliğiyle hesaplar:
$$\frac{1}{\sqrt{Q}} \sum_{x=0}^{Q-1} |x\rangle |a^x \bmod N\rangle$$
2. **Adım 2 (`Periodic Collapse`):** İkinci yazmaç ölçüldüğünde (örneğin sonuç $4$ çıktığında), birinci yazmaçta sadece sonucu $4$ veren **periyodik $x$ noktaları ($x_0, x_0 + r, x_0 + 2r, x_0 + 3r, \dots$) ayakta kalır!**
3. **Adım 3 (`Quantum Fourier Transform - QFT`):** Tıpkı ses mühendisliğinde bir ses dalgasına **Fourier Dönüşümü (`FFT`)** uyguladığında zaman uzayındaki karmaşık dalganın **frekansına ($1/r$)** dönüşmesi gibi; `QFT` kapısı da bu periyodik süperpozisyonu girişime sokar:
   - $r$'nin katı olmayan tüm frekanslar **yıkıcı girişimle (`Destructive Interference`) birbirini sıfırlar**,
   - Sadece **$1/r$ frekansının tam katları yapıcı girişimle (`Constructive Interference`) zirve yapar!**
4. Sonuçta ölçüm yaptığında ekrandan doğrudan frekansın bir katını ($y \approx kQ/r$) okursun, **Sürekli Kesirler Algoritması (`Continued Fractions`)** ile periyot $r$'yi ve dolayısıyla asal çarpanları ($p, q$) çıkarırsın!
:::

::: anlat 4. "Harvest Now, Decrypt Later" (Şimdi Topla, Sonra Çöz) Tehdidi!
Şu soruyla hesap adımlarını ayır:

Konferansta dinleyicilerden biri mutlaka şunu soracaktır:
*"İyi de hocam, `RSA-2048`'i kıracak büyüklükte hata düzeltmeli bir kuantum bilgisayarın çıkmasına daha 5–10 yıl var deniyor. Neden bugünden telaş yapıyoruz?"*

İşte istihbarat servislerinin ve siber güvenlik dünyasının uykularını kaçıran kavram:
> **`Harvest Now, Decrypt Later (HNDL)` / `Store Now, Decrypt Later (SNDL)` — Şimdi Kaydet, Kuantum Çıkınca Çöz!**

1. Bugün internet üzerinden geçen şifreli devlet yazışmaları, askeri sırlar, biyometrik veriler ve ticari Ar-Ge trafiği (`TLS / VPN` paketleri), gelişmiş tehdit aktörleri (`APT` grupları) tarafından **bugün şifreli haliyle devasa veri merkezlerine kaydediliyor.**
2. Bu verilerin bugün çözülememesi önemli değil; eğer bir bilginin gizlilik ömrü **10–20 yıl** ise ve kuantum bilgisayar **8 yıl sonra** çalışmaya başlarsa, 2026 yılında gönderdiğin tüm "güvenli" mesajlar 2034 yılında geriye dönük olarak (`Retroactively`) açık metin gibi okunacaktır!

### 📐 Mosca Teoremi (`Mosca's Inequality`: $X + Y > Z$)
Kuantum güvenlik uzmanı Michele Mosca bunu basit bir eşitsizlikle özetler:
- **$X$ (Verinin Gizli Kalması Gereken Süre - Yıl):** Örneğin 15 yıl.
- **$Y$ (Altyapıyı Kuantum-Sonrası Kriptografiye Göç Ettirme Süresi - Yıl):** Örneğin 5 yıl.
- **$Z$ (Kriptanalitik Kuantum Bilgisayarın Çıkmasına Kalan Süre - Yıl):** Örneğin 12 yıl.
> **Eğer $X + Y > Z$ ise ($15 + 5 = 20 > 12$), GEÇ KALDINIZ DEMEKTİR!** Göç işlemine kuantum bilgisayar çıktığı gün değil, **bugün** başlamak zorundasınız!
:::

::: tahmin Mosca's Inequality (X + Y > Z) Risk Analizi
Bir bankanın müşteri sırlarının $X = 10$ yıl gizli kalması gerekiyor. Bankanın tüm sunucularını yeni nesil kuantum-dirençli şifrelemeye geçirmesi $Y = 4$ yıl sürecek. Büyük ölçekli bir kuantum bilgisayarın ($Z$) $11$ yıl içinde çıkacağı tahmin ediliyor. `Mosca's Inequality` ($X + Y > Z$) kontrolünün çıktısı nedir?

```python
X, Y, Z = 10, 4, 11
toplam_maruziyet = X + Y
risk = "ACIL RISK (HNDL Tehdidi!)" if toplam_maruziyet > Z else "GUVENDE"
print(f"X+Y={toplam_maruziyet} vs Z={Z} -> {risk}")
```

???

```cikti
X+Y=14 vs Z=11 -> ACIL RISK (HNDL Tehdidi!)
```
Göç tamamlanana kadar geçen $Y=4$ yılın sonunda kaydedilen veriler $X=10$ yıl daha gizli kalmak zorundadır ($X+Y=14$ yıl). Kuantum bilgisayar $Z=11$. yılda çıkarsa, son 3 yıllık gizlilik penceresi kırılacağı için `ACIL RISK (HNDL Tehdidi!)` oluşur.
:::

::: gorev 1 · Shor'un Klasik Çerçevesi: Periyottan Çarpanlara
Shor algoritmasında kuantum bilgisayar yalnız bir işi yapar: $a^x \bmod N$ fonksiyonunun **periyodunu** ($r$) bulur. Geri kalan her şey klasiktir. Bu görevde periyodu kaba kuvvetle (kuantum bilgisayarın yapacağı işi klasik olarak) bul ve Shor'un klasik adımlarını uygula. `shor_klasik(N, a)` işlevini yaz.

**Kurallar:**
1. `N` en az 3, `a` $1 < a < N$ olan tam sayılar olmalı (`bool` değil); değilse `ValueError`.
2. $g = \gcd(a, N) > 1$ ise şanslısın: `durum = "ortak_bolen"`, çarpanlar $[g, N/g]$ (küçükten büyüğe), `periyot = None`.
3. Değilse $a^r \equiv 1 \pmod N$ olan **en küçük** $r \ge 1$'i bul.
   - $r$ tekse `durum = "tek_periyot"`, çarpanlar `None`.
   - $a^{r/2} \equiv -1 \pmod N$ ise `durum = "eksi_bir"`, çarpanlar `None`.
   - Aksi halde $p = \gcd(a^{r/2} - 1, N)$, $q = \gcd(a^{r/2} + 1, N)$: `durum = "basarili"`, çarpanlar `sorted([p, q])`.
4. Çıktı: `{"periyot": r | None, "durum": str, "carpanlar": list | None}`.

```starter
def shor_klasik(N, a):
    # KUSURLU BAŞLANGIÇ: periyodu hep 2 sayıyor
    import math
    y = pow(a, 1, N)
    return {"periyot": 2, "durum": "basarili", "carpanlar": sorted([math.gcd(y - 1, N), math.gcd(y + 1, N)])}

print(shor_klasik(15, 7))
```

```test
fn = need("shor_klasik")
eq(fn(15, 7), {"periyot": 4, "durum": "basarili", "carpanlar": [3, 5]}, "7^4 ≡ 1 (mod 15); 7² = 49 ≡ 4 → gcd(3,15)=3, gcd(5,15)=5")
eq(fn(21, 2), {"periyot": 6, "durum": "basarili", "carpanlar": [3, 7]}, "2^6 ≡ 1 (mod 21); 2³ = 8 → gcd(7,21)=7, gcd(9,21)=3")
eq(fn(15, 14), {"periyot": 2, "durum": "eksi_bir", "carpanlar": None}, "14 ≡ -1 (mod 15): işe yaramaz, başka a dene")
eq(fn(21, 4), {"periyot": 3, "durum": "tek_periyot", "carpanlar": None}, "4³ = 64 ≡ 1 (mod 21): tek periyot")
eq(fn(15, 6), {"periyot": None, "durum": "ortak_bolen", "carpanlar": [3, 5]}, "gcd(6, 15) = 3: doğrudan çarpan")
eq(fn(35, 2)["carpanlar"], [5, 7], "2^12 ≡ 1 (mod 35), 2^6 = 64 ≡ 29 → gcd(28,35)=7, gcd(30,35)=5")
eq(fn(35, 2)["periyot"], 12, "2'nin mod 35'teki mertebesi 12")
raises(ValueError, fn, 15, 1)
raises(ValueError, fn, 15, 15)
raises(ValueError, fn, 2, 1)
raises(ValueError, fn, 15.0, 7)
raises(ValueError, fn, 15, True)
eq(fn(3, 2)["durum"], "eksi_bir", "N = 3 en küçük geçerli N: 2 ≡ -1 (mod 3)")
eq(fn(10, 4), {"periyot": None, "durum": "ortak_bolen", "carpanlar": [2, 5]}, "gcd = 2 de ortak bölendir (yoksa periyot döngüsü hiç bitmez)")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef shor_klasik(N, a):\n    for v in (N, a):\n        if isinstance(v, bool) or not isinstance(v, int):\n            raise ValueError('N ve a tam sayı olmalı')\n    if N < 3 or not 1 < a < N:\n        raise ValueError('N >= 3 ve 1 < a < N olmalı')\n    g = math.gcd(a, N)\n    if g > 1:\n        return {'periyot': None, 'durum': 'ortak_bolen', 'carpanlar': sorted([g, N // g])}\n    r, deger = (1, a % N)\n    while deger != 1:\n        deger = deger * a % N\n        r += 1\n    if r % 2:\n        return {'periyot': r, 'durum': 'tek_periyot', 'carpanlar': None}\n    yarim = pow(a, r // 2, N)\n    if yarim == N - 1:\n        return {'periyot': r, 'durum': 'eksi_bir', 'carpanlar': None}\n    return {'periyot': r, 'durum': 'basarili', 'carpanlar': sorted([math.gcd(yarim - 1, N), math.gcd(yarim + 1, N)])}", 'referans', 'exec'), _REF)
_t, _g = _ff(shor_klasik, _REF['shor_klasik'], (15, 7), tohum=2096, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (shor_klasik): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def shor_klasik(N, a):
    for v in (N, a):
        if isinstance(v, bool) or not isinstance(v, int):
            raise ValueError("N ve a tam sayı olmalı")
    if N < 3 or not (1 < a < N):
        raise ValueError("N >= 3 ve 1 < a < N olmalı")
    g = math.gcd(a, N)
    if g > 1:
        return {"periyot": None, "durum": "ortak_bolen", "carpanlar": sorted([g, N // g])}
    r, deger = 1, a % N
    while deger != 1:
        deger = deger * a % N
        r += 1
    if r % 2:
        return {"periyot": r, "durum": "tek_periyot", "carpanlar": None}
    yarim = pow(a, r // 2, N)
    if yarim == N - 1:
        return {"periyot": r, "durum": "eksi_bir", "carpanlar": None}
    return {"periyot": r, "durum": "basarili", "carpanlar": sorted([math.gcd(yarim - 1, N), math.gcd(yarim + 1, N)])}
```

```hint
Periyodu `deger = deger * a % N` döngüsüyle say (gcd 1 olduğu için döngü biter). −1 mod N, `N - 1` demektir.
```
:::

::: gorev 2 · İki qubit için QFT matrisini uygula
`qft_genlikleri(genlikler)` işlevi, hesaplama tabanı sırasıyla verilen dört genlikten dört karmaşık çıkış genliği üretsin. QFT matrisinin `k,j` öğesi `(1j ** ((k * j) % 4)) / 2` değeridir. Her satırın girdi vektörüyle çarpımını hesapla. Çıktı bir liste olsun.

Karmaşık genlikleri toplamadan önce karelerini almak girişimi kaybeder. Örneğin eşit işaretli ve dönüşümlü işaretli iki girdi aynı ölçüm olasılıklarına sahiptir. QFT sonrasında ilki 0, ikincisi 2 numaralı durumda yoğunlaşır.

```starter
def qft_genlikleri(genlikler):
    # Bu başlangıç genlikleri kopyalıyor ve faz çarpanını uygulamıyor.
    return list(genlikler)
```
```solution
def qft_genlikleri(genlikler):
    return [
        sum(a * 1j ** ((k * j) % 4) for j, a in enumerate(genlikler)) / 2
        for k in range(4)
    ]
```
```test
f = need("qft_genlikleri")
eq(f([1, 0, 0, 0]), [0.5, 0.5, 0.5, 0.5], "Sıfırıncı matris sütunu")
eq(f([0, 1, 0, 0]), [0.5, 0.5j, -0.5, -0.5j], "İşaret ve faz sırası")
eq(f([0.5, 0.5, 0.5, 0.5]), [1, 0, 0, 0], "Eşfazlı girişim")
eq(f([0.5, -0.5, 0.5, -0.5]), [0, 0, 1, 0], "Dönüşümlü faz")
a = [0.5j, 0.5, -0.5j, 0.5]
yedek = a[:]
eq(f(a), [0.5, 0.5j, -0.5, 0.5j], "Karmaşık girdide faz korunur")
eq(a, yedek, "Girdi değişmez")
```
:::

::: anlat Sınır
Ders Shor'un faktörlemeyi periyot bulmaya indirgemesini, QFT'yi ve HNDL/Mosca eşitsizliğini anlatır; görev periyodu klasik olarak (kaba kuvvetle) bulur, yani kuantum bilgisayarın yaptığı kısmı değil, Shor'un klasik çerçevesini gösterir; QFT devresi ve kaynak tahmini yoktur. 2019 tahmini RSA-2048 için 20 milyon gürültülü qubit ve yaklaşık 8 saatti; sonraki çalışmalar qubit sayısını düşürdü, ama bugünkü donanım bu ölçeğin çok gerisindedir. Periyot tek çıkarsa ya da a^(r/2) ≡ -1 (mod N) ise deneme başka bir a ile tekrarlanır. Mosca eşitsizliğindeki X, Y, Z süreleri kurumun kendi tahminleridir; sonuç bu tahminler kadar güvenilirdir. ECC anahtarları küçük olduğu için aynı güvenlik düzeyindeki RSA'dan daha az qubit'le kırılabilir.

Kaynaklar: [Shor 1995 - Polynomial-Time Algorithms for Prime Factorization and Discrete Logarithms on a Quantum Computer](https://arxiv.org/abs/quant-ph/9508027), [Gidney ve Ekerå 2019 - How to factor 2048 bit RSA integers in 8 hours using 20 million noisy qubits](https://arxiv.org/abs/1905.09749), [Roetteler vd. 2017 - Quantum resource estimates for computing elliptic curve discrete logarithms](https://arxiv.org/abs/1706.06752), [Gidney 2025 - How to factor 2048 bit RSA integers with less than a million noisy qubits](https://arxiv.org/abs/2505.15917).
:::

