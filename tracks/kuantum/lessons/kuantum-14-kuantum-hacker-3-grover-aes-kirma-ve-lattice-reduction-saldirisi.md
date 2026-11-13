---
id: kuantum-14
title: "Kuantum Hacker 3: Grover ile Simetrik Şifre Kırma ve Zayıf Kafeslere (LWE) Lattice Reduction Saldırısı"
summary: "Grover algoritmasıyla simetrik anahtar aramada optimal iterasyonu ve Over-Rotation (Sufle Problemi) çöküşünü hesapla; zayıf seçilmiş Post-Quantum kafes bazlarını Lagrange/Gauss & LLL Lattice Reduction ve Babai CVP saldırısıyla kır."
track: kuantum
order: 14
duration_minutes: 40
difficulty: ileri
xp: 320
prerequisites: [kuantum-13]
tags: [grovers-algorithm, over-rotation, aes-cryptanalysis, lattice-reduction, lll-algorithm, babai-cvp, lwe-attack]
esleme: kuantum-04, kuantum-05
---

::: anlat 1. Grover ile Simetrik Şifre Kırma ve "Sufle Problemi" (Over-Rotation)
## Grover iterasyonu ve küçük lattice hesabı

Arama iterasyonu arttıkça başarı olasılığı her zaman artmaz; amplitude amplification için doğru durma noktası önemlidir. Bu derste iterasyon olasılığını ve iki boyutlu lattice reduction örneğini hesaplayacaksın. İki boyutlu örnek gerçek LWE parametrelerinin kırıldığı anlamına gelmez.

### 🔎 1. reversible quantum oracle (`Reversible Key-Search Oracle`):
Saldırgan tüm olası $N = 2^n$ anahtarı eşit süperpozisyona sokar: $\frac{1}{\sqrt{N}}\sum_{k=0}^{N-1} |k\rangle$.
Kuantum kehaneti ($U_\omega$), süperpozisyon içindeki her $k$ anahtarı için tersinir (`Toffoli` kapılarıyla kurulmuş) şifreleme devresini çalıştırır ve $E_k(P) == C$ koşulunu sağlayan doğru anahtarın genliğini eksiyle çarpar (`Phase Flip`):
$$U_\omega |k\rangle = \begin{cases} -|k\rangle & \text{eğer } E_k(P) = C \\ +|k\rangle & \text{diğer durumlarda} \end{cases}$$

### 📐 2. Tam Dönüş Açısı ve `Over-Rotation` (*The Soufflé Problem*):
Uzayda $N$ toplam durum ve $M$ doğru çözüm (anahtar) olduğunda, başlangıç durumunun doğru çözümler altuzayıyla yaptığı açı $\theta / 2$ şöyledir:
$$\sin\left(\frac{\theta}{2}\right) = \sqrt{\frac{M}{N}} \implies \frac{\theta}{2} = \arcsin\left(\sqrt{\frac{M}{N}}\right)$$
Her **Grover İterasyonu** (`Oracle` + `Diffusion`), durum vektörünü doğru çözüme doğru tam $\theta$ kadar döndürür. $k$ iterasyon sonunda açı $(2k + 1)\frac{\theta}{2}$ olur ve doğru anahtarı ölçme olasılığı:

$$P_{\text{başarı}}(k) = \sin^2\left((2k + 1) \cdot \arcsin\sqrt{\frac{M}{N}}\right)$$

Optimal iterasyon sayısı açıyı $\frac{\pi}{2}$ ($90^\circ$) değerine en çok yaklaştıran adımdır:
$$R_{\text{opt}} = \left\lfloor \frac{\pi}{4}\sqrt{\frac{N}{M}} \right\rfloor$$

> **⚠️ Kuantum Hacker Tuzağı — Sufle Problemi (`Over-Rotation`):**
> Klasik kaba kuvvet (`Brute-Force`) saldırısında bilgisayarı ne kadar uzun çalıştırırsan şifreyi bulma ihtimalin o kadar artar.
> **Grover algoritması ise fırındaki sufle gibidir!** Eğer $R_{\text{opt}}$ adımda ölçüm yapmayıp devreyi çalıştırmaya devam edersen (`Over-Rotation`), vektör $90^\circ$'yi geçip $180^\circ$'ye (yanlış cevaplara) geri döner ve başarı olasılığın **%100'den tekrar %0'a çakılır!**

```python
import math

# N = 64 elemanlı uzayda M = 1 gizli anahtar için Grover iterasyonlarına göre başarı olasılığı
N, M = 64, 1
yari_aci = math.asin(math.sqrt(M / N))
r_opt = int(math.floor((math.pi / 4) * math.sqrt(N / M)))

for k in (0, 2, r_opt, r_opt * 2):
    p = round(math.sin((2 * k + 1) * yari_aci) ** 2, 4)
    print(f"Iterasyon k={k:2d} (Optimal={r_opt}) -> Başarı Olasılığı: {p}")
```

**Kaynak ve sınır:** [IBM Quantum: quantum algorithms](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms). Sayısal örnekler eğitim ölçeğindedir; gerçek quantum hardware, standart PQC ürünü veya ağ üzerindeki bir hedef üzerinde kabul testi yapılmaz.
:::

::: anlat 2. Zayıf Post-Quantum Kafesleri Kırmak: Lattice Reduction (Gauss/LLL) ve Babai CVP Saldırısı!
Önceki derslerimizde **`Post-Quantum Cryptography (LWE / ML-KEM)`** algoritmalarının kafes (`Lattice`) matematiğine dayandığını öğrendik.
Peki bir yazılımcı kendi kafes şifrelemesini yazarken boyutu küçük seçerse veya açık anahtar olarak verdiği **"Kötü Taban (`Bad Basis`)"** vektörleri yeterince karmaşık değilse, bir kriptanalist bu şifreyi **kuantum bilgisayara bile ihtiyaç duymadan** nasıl kırar?

### 🗡️ Adım 1: `Lattice Basis Reduction` (`Lagrange/Gauss` & `LLL Algorithm`)
Saldırganın elinde birbirine neredeyse paralel ve çok uzun iki açık anahtar vektörü vardır:
Örneğin $\mathbf{b}_1 = (14, 19)$ ve $\mathbf{b}_2 = (11, 15)$.
Bu iki vektör çok uzun görünse de aslında aynı kafesi üreten **en kısa ve mümkün olduğunca dik baz vektörlerini** bulmak için Öklid algoritmasının vektör versiyonu olan **`Lagrange/Gauss Lattice Reduction`** (yüksek boyutta **`LLL — Lenstra-Lenstra-Lovász, 1982`**) çalıştırılır:

```
Kötü Açık Baz (Bad Basis):         Gauss / LLL İndirgeme Sonrası İyi Baz (Short Orthogonal Basis):
  b1 = (14, 19)  [Uzunluk: 23.6]     ──►   u1 = (1, 0)  [Uzunluk: 1.0]
  b2 = (11, 15)  [Uzunluk: 18.6]     ──►   u2 = (0, 1)  [Uzunluk: 1.0]
```

Algoritma her adımda uzun vektörün ($\mathbf{v}$) kısa vektör ($\mathbf{u}$) üzerindeki izdüşüm katsayısını tam sayıya yuvarlar:
$$\mu = \operatorname{round}\!\left(\frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|^2}\right), \qquad \mathbf{v} \leftarrow \mathbf{v} - \mu \mathbf{u}$$
ve $\|\mathbf{v}\| < \|\mathbf{u}\|$ oldukça rolleri değiştirir. Döngü durduğunda (2 boyutta) elimizde kafesin **en kısa baz vektörleri** kalır; bunlar mümkün olduğunca diktir!

### 🎯 Adım 2: `Babai's Rounding / Nearest Plane` ile Gürültüyü ($\mathbf{e}$) Soyup Atmak!
`LWE` şifrelemesinde açık hedef nokta $\mathbf{t} = \mathbf{x}_{\text{kafes}} + \mathbf{e}$ (bir kafes noktası artı küçük gürültü $\mathbf{e}$) biçimindedir.
Saldırgan indirgenmiş dik baz $(\mathbf{u}, \mathbf{v})$ matrisini bulduktan sonra, $\mathbf{t}$ hedefini bu kısa baza bölüp katsayıları en yakın tam sayıya yuvarlar (**`Babai's Algorithm`**):
$$c_1 = \operatorname{round}\!\left(\frac{t_x v_y - t_y v_x}{u_x v_y - u_y v_x}\right), \qquad c_2 = \operatorname{round}\!\left(\frac{u_x t_y - u_y t_x}{u_x v_y - u_y v_x}\right)$$
Böylece gerçek kafes noktasını $\mathbf{x}_{\text{kafes}} = c_1 \mathbf{u} + c_2 \mathbf{v}$ olarak tam isabetle bulur ve $\mathbf{e} = \mathbf{t} - \mathbf{x}_{\text{kafes}}$ çıkarmasıyla **gizli gürültüyü ve özel anahtarı anında ele geçirir!**

```python
# Kötü baz b1=(14, 19), b2=(11, 15) üzerinde Gauss Lattice Reduction
u, v = [14, 19], [11, 15]
while True:
    if u[0]**2 + u[1]**2 > v[0]**2 + v[1]**2:
        u, v = v, u
    mu = int(round((u[0]*v[0] + u[1]*v[1]) / (u[0]**2 + u[1]**2)))
    if mu == 0:
        break
    v = [v[0] - mu * u[0], v[1] - mu * u[1]]
print("Kötü bazdan kurtarılan kısa dik baz:", u, v)
```
:::

::: tahmin Grover Over-Rotation (Fazla Döndürme) Riski
$N = 100$ elemanlı bir arama uzayında $M = 1$ çözüm ararken optimal iterasyon sayısı $R_{\text{opt}} = \lfloor \frac{\pi}{4}\sqrt{100} \rfloor = 7$'dir. Eğer geliştirici devreyi $k = 7$ yerine iki katı olan $k = 15$ iterasyon çalıştırırsa başarı olasılığına ne olur?

```python
import math
yari_aci = math.asin(math.sqrt(1 / 100))
p_opt = round(math.sin((2 * 7 + 1) * yari_aci) ** 2, 4)
p_fazla = round(math.sin((2 * 15 + 1) * yari_aci) ** 2, 4)
print(f"k=7 (Optimal): {p_opt} | k=15 (Over-Rotation): {p_fazla}")
```

???

```cikti
k=7 (Optimal): 0.9953 | k=15 (Over-Rotation): 0.0013
```
Yarım açı $\theta = \arcsin(\sqrt{1/100}) \approx 0.1002$ radyandır. Optimal iterasyon $k=7$'de toplam açı $(2 \cdot 7 + 1)\theta \approx 1.503$ radyan ($\approx 86^\circ$) olduğu için başarı olasılığı $\sin^2 \approx \%99.53$ (`0.9953`) iken, devreyi $k=15$ adıma kadar fazla çalıştırdığımızda (`Over-Rotation`) açı $(2 \cdot 15 + 1)\theta \approx 3.105$ radyana ($\approx 178^\circ$) ulaşır; durum vektörü $180^\circ$'ye yaklaştığı için başarı olasılığı $\%0.13$ (`0.0013`) seviyesine çakılır!
:::

::: gorev 1 · Grover Optimal İterasyon Hesabı ve Over-Rotation (Sufle Problemi) Başarı Olasılığı
`grover_olasilik_analizi(uzay_boyutu_N, cozum_sayisi_M, iterasyon_k)` işlevini yaz:
1. `yari_aci = math.asin(math.sqrt(cozum_sayisi_M / uzay_boyutu_N))` değerini hesapla.
2. `optimal_iterasyon = int(math.floor((math.pi / 4.0) * math.sqrt(uzay_boyutu_N / cozum_sayisi_M)))` değerini bul.
3. `iterasyon_k` adımındaki tam başarı olasılığını `basari_olasiligi = round(math.sin((2 * iterasyon_k + 1) * yari_aci) ** 2, 6)` formülüyle hesapla.
4. `fazla_donus_var_mi = bool(iterasyon_k > optimal_iterasyon)` alanı ile birlikte `{"optimal_iterasyon": ..., "basari_olasiligi": ..., "fazla_donus_var_mi": ...}` sözlüğünü döndür.

```starter
import math
# KUSURLU BAŞLANGIÇ KODU: optimal iterasyonu ve sin^2((2k+1)*yari_aci) olasılığını hesapla.
def grover_olasilik_analizi(uzay_boyutu_N, cozum_sayisi_M, iterasyon_k):
    return {
        "optimal_iterasyon": 1,
        "basari_olasiligi": 0.0,
        "fazla_donus_var_mi": False
    }

print(grover_olasilik_analizi(64, 1, 6))
print(grover_olasilik_analizi(64, 1, 12))
```
```test
f = need("grover_olasilik_analizi")
# N=4, M=1 -> yari_aci = asin(0.5) = pi/6 = 30 derece. k=1 iken sin^2(3 * 30) = sin^2(90) = 1.0!
r4 = f(4, 1, 1)
ok(r4 == {"optimal_iterasyon": 1, "basari_olasiligi": 1.0, "fazla_donus_var_mi": False}, "N=4, M=1 için tek iterasyonda %100 (1.0) başarı olasılığı bulundu")

# N=64, M=1 -> optimal = 6
r64_opt = f(64, 1, 6)
r64_over = f(64, 1, 12)
ok(r64_opt["optimal_iterasyon"] == 6 and r64_opt["basari_olasiligi"] > 0.99 and r64_opt["fazla_donus_var_mi"] is False, "N=64, k=6 optimal iterasyonda >%99 başarı")
ok(r64_over["fazla_donus_var_mi"] is True and r64_over["basari_olasiligi"] < 0.05, "N=64, k=12 Over-Rotation durumunda başarı olasılığı <%5'e düştü")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef grover_olasilik_analizi(uzay_boyutu_N, cozum_sayisi_M, iterasyon_k):\n    yari_aci = math.asin(math.sqrt(cozum_sayisi_M / uzay_boyutu_N))\n    opt = int(math.floor(math.pi / 4.0 * math.sqrt(uzay_boyutu_N / cozum_sayisi_M)))\n    olas = round(math.sin((2 * iterasyon_k + 1) * yari_aci) ** 2, 6)\n    return {'optimal_iterasyon': opt, 'basari_olasiligi': olas, 'fazla_donus_var_mi': bool(iterasyon_k > opt)}", 'referans', 'exec'), _REF)
_t, _g = _ff(grover_olasilik_analizi, _REF['grover_olasilik_analizi'], (64, 1, 6), tohum=3370, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (grover_olasilik_analizi): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def grover_olasilik_analizi(uzay_boyutu_N, cozum_sayisi_M, iterasyon_k):
    yari_aci = math.asin(math.sqrt(cozum_sayisi_M / uzay_boyutu_N))
    opt = int(math.floor((math.pi / 4.0) * math.sqrt(uzay_boyutu_N / cozum_sayisi_M)))
    olas = round(math.sin((2 * iterasyon_k + 1) * yari_aci) ** 2, 6)
    return {
        "optimal_iterasyon": opt,
        "basari_olasiligi": olas,
        "fazla_donus_var_mi": bool(iterasyon_k > opt)
    }
```
```hint
`yari_aci = math.asin(math.sqrt(M / N))` ve `round(math.sin((2 * iterasyon_k + 1) * yari_aci) ** 2, 6)` formüllerini kullan.
```
:::

::: gorev 2 · 2D Lagrange/Gauss Lattice Basis Reduction ve Babai En Yakın Kafes Noktası (CVP) Saldırısı
`kafes_indirge_ve_kir(b1, b2, hedef_t)` işlevini yaz:
1. `u = [int(b1[0]), int(b1[1])]` ve `v = [int(b2[0]), int(b2[1])]` vektörlerine 2D Lagrange/Gauss kafes indirgemesi uygula:
   - Döngüde eğer `u[0]**2 + u[1]**2 > v[0]**2 + v[1]**2` ise `u, v = v, u` yap.
   - `mu = int(round((u[0]*v[0] + u[1]*v[1]) / (u[0]**2 + u[1]**2)))` hesapla; `mu == 0` ise döngüden çık, değilse `v = [v[0] - mu * u[0], v[1] - mu * u[1]]` güncelle.
2. İndirgenmiş `[u, v]` çiftini `(x**2 + y**2, x, y)` anahtarıyla küçükten büyüğe sırala (`indirgenmis_baz = [u, v]`).
3. Babai yuvarlamasıyla (`det = u[0]*v[1] - u[1]*v[0]`, `c1 = int(round((hedef_t[0]*v[1] - hedef_t[1]*v[0]) / det))`, `c2 = int(round((u[0]*hedef_t[1] - u[1]*hedef_t[0]) / det))`) en yakın kafes noktasını `kafes_noktasi = [c1*u[0] + c2*v[0], c1*u[1] + c2*v[1]]` ve hata vektörünü `hata = [hedef_t[0] - kafes_noktasi[0], hedef_t[1] - kafes_noktasi[1]]` bul.
4. `{"indirgenmis_baz": [u, v], "en_yakin_kafes_noktasi": kafes_noktasi, "kurtarilan_hata_e": hata}` döndür.

```starter
# KUSURLU BAŞLANGIÇ KODU: Gauss indirgeme döngüsünü ve Babai CVP çözümünü tamamla.
def kafes_indirge_ve_kir(b1, b2, hedef_t):
    return {
        "indirgenmis_baz": [list(b1), list(b2)],
        "en_yakin_kafes_noktasi": [0, 0],
        "kurtarilan_hata_e": list(hedef_t)
    }

print(kafes_indirge_ve_kir([40, 27], [15, 10], [101, 49]))
```
```test
f = need("kafes_indirge_ve_kir")
# b1=[40, 27], b2=[15, 10] -> indirgenmiş baz [5, 0] ve [0, 1] değil: det = 40*10 - 27*15 = 400 - 405 = -5!
# Gerçek kısa baz: [-5, -3] değil, bakalım: u=[0, 1], v=[5, 0]!
# Hedef t = [101, 49] = [100, 49] + [1, 0] -> en yakın kafes noktası [100, 49], hata [1, 0]!
r1 = f([40, 27], [15, 10], [101, 49])
ok(r1 == {"indirgenmis_baz": [[0, 1], [5, 0]], "en_yakin_kafes_noktasi": [100, 49], "kurtarilan_hata_e": [1, 0]}, "Kötü baz ([40,27],[15,10]) dik baza ([0,1],[5,0]) indirgendi ve LWE hatası [1,0] yakalandı")

# İkinci test: b1=[28, 38], b2=[22, 30] -> kısa baz [2, 0] ve [0, 2] değil, det = 28*30 - 38*22 = 840 - 836 = 4 -> [0, 2] ve [2, 0]
# Hedef [10, 14] + [0, 1] = [10, 15] -> kafes noktası [10, 14] veya bakalım:
# B1 = [19, 10], B2 = [38, 21] -> 38,21 - 2*(19,10) = [0, 1], ve [19, 10] - 10*[0, 1] = [19, 0]!
r2 = f([38, 21], [19, 10], [58, 8])
ok(r2 == {"indirgenmis_baz": [[0, 1], [19, 0]], "en_yakin_kafes_noktasi": [57, 8], "kurtarilan_hata_e": [1, 0]}, "İkinci çarpık kafes indirgendi ve Babai yuvarlamasıyla [57, 8] + [1, 0] ayrıştırıldı")
r3 = f([0, -1], [-1, 0], [3, -2])
ok(r3 == {"indirgenmis_baz": [[0, 1], [1, 0]], "en_yakin_kafes_noktasi": [3, -2], "kurtarilan_hata_e": [0, 0]}, "Negatif eksen vektörleri kanonik pozitif baza ([0, 1], [1, 0]) dönüştürüldü")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def kafes_indirge_ve_kir(b1, b2, hedef_t):\n    u = [int(b1[0]), int(b1[1])]\n    v = [int(b2[0]), int(b2[1])]\n    while True:\n        if u[0] ** 2 + u[1] ** 2 > v[0] ** 2 + v[1] ** 2:\n            u, v = (v, u)\n        payda = u[0] ** 2 + u[1] ** 2\n        mu = int(round((u[0] * v[0] + u[1] * v[1]) / payda))\n        if mu == 0:\n            break\n        v = [v[0] - mu * u[0], v[1] - mu * u[1]]\n    u = [-u[0], -u[1]] if u[0] < 0 or (u[0] == 0 and u[1] < 0) else u\n    v = [-v[0], -v[1]] if v[0] < 0 or (v[0] == 0 and v[1] < 0) else v\n    baz = sorted([u, v], key=lambda x: (x[0] ** 2 + x[1] ** 2, x[0], x[1]))\n    u, v = (baz[0], baz[1])\n    det = u[0] * v[1] - u[1] * v[0]\n    c1 = int(round((hedef_t[0] * v[1] - hedef_t[1] * v[0]) / det))\n    c2 = int(round((u[0] * hedef_t[1] - u[1] * hedef_t[0]) / det))\n    nokta = [c1 * u[0] + c2 * v[0], c1 * u[1] + c2 * v[1]]\n    hata = [hedef_t[0] - nokta[0], hedef_t[1] - nokta[1]]\n    return {'indirgenmis_baz': [u, v], 'en_yakin_kafes_noktasi': nokta, 'kurtarilan_hata_e': hata}", 'referans', 'exec'), _REF)
_t, _g = _ff(kafes_indirge_ve_kir, _REF['kafes_indirge_ve_kir'], ([40, 27], [15, 10], [101, 49]), tohum=3009, en_cok=600, mod='gecerli', butce='oto', ekler=[([40, 27], [15, 10], [101, 49], ), ([15, 27], [15, 10], [101, 49], )])
ok(_t, "farksal tarama (kafes_indirge_ve_kir): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
def kafes_indirge_ve_kir(b1, b2, hedef_t):
    u = [int(b1[0]), int(b1[1])]
    v = [int(b2[0]), int(b2[1])]
    while True:
        if u[0] ** 2 + u[1] ** 2 > v[0] ** 2 + v[1] ** 2:
            u, v = v, u
        payda = u[0] ** 2 + u[1] ** 2
        mu = int(round((u[0] * v[0] + u[1] * v[1]) / payda))
        if mu == 0:
            break
        v = [v[0] - mu * u[0], v[1] - mu * u[1]]
    u = [-u[0], -u[1]] if (u[0] < 0 or (u[0] == 0 and u[1] < 0)) else u
    v = [-v[0], -v[1]] if (v[0] < 0 or (v[0] == 0 and v[1] < 0)) else v
    baz = sorted([u, v], key=lambda x: (x[0] ** 2 + x[1] ** 2, x[0], x[1]))
    u, v = baz[0], baz[1]
    det = u[0] * v[1] - u[1] * v[0]
    c1 = int(round((hedef_t[0] * v[1] - hedef_t[1] * v[0]) / det))
    c2 = int(round((u[0] * hedef_t[1] - u[1] * hedef_t[0]) / det))
    nokta = [c1 * u[0] + c2 * v[0], c1 * u[1] + c2 * v[1]]
    hata = [hedef_t[0] - nokta[0], hedef_t[1] - nokta[1]]
    return {
        "indirgenmis_baz": [u, v],
        "en_yakin_kafes_noktasi": nokta,
        "kurtarilan_hata_e": hata
    }
```
```hint
Gauss indirgeme döngüsünden sonra `baz = sorted([u, v], key=lambda x: (x[0]**2 + x[1]**2, x[0], x[1]))` ile sırala ve Cramer kuralı + `round` ile `c1, c2` tam sayı katsayılarını bul.
```
:::

::: anlat Sınır
Görevler Grover'ın optimal iterasyonunu ve fazla döndürme olasılığını, 2 boyutlu Gauss kafes indirgemesini ve Babai ile en yakın kafes noktasını hesaplatır. 2 boyutta indirgeme her zaman en kısa vektörü bulur; gerçek LWE boyutlarında LLL/BKZ yalnız yaklaşık sonuç verir ve saldırı maliyeti boyutla üstel artar. 'Zayıf kafes' saldırısı ancak parametreler kötü seçildiğinde (çok küçük boyut ya da gürültü) çalışır; standart ML-KEM parametreleri bu dersteki yöntemle kırılmaz. Grover kısmında oracle maliyeti ve hata düzeltme hesaba katılmaz.

Kaynaklar: [Boyer vd. 1996 - Tight bounds on quantum searching](https://arxiv.org/abs/quant-ph/9605034), [Grassl vd. 2016 - Applying Grover's algorithm to AES: quantum resource estimates](https://arxiv.org/abs/1512.04965), [Albrecht vd. 2015 - On the concrete hardness of Learning with Errors](https://eprint.iacr.org/2015/046).
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Bu dersin iki mesajı var: Birincisi, Grover araması klasik kaba kuvveti karesel hızlandırır ($\sqrt{N/M}$ mertebesi), yani AES-128'i yaklaşık $2^{64}$ kuantum sorgusuna indirirken AES-256 hâlâ $2^{128}$ güvenlik payı bırakır; üstelik optimal iterasyon $\lfloor \frac{\pi}{4}\sqrt{N/M} \rfloor$ aşılırsa durum vektörü fazla döner (Over-Rotation) ve başarı olasılığı yeniden düşer.

İkincisi, "kuantum sonrası kafes kullandım" demek tek başına güvenlik sağlamaz: boyut küçük veya baz zayıf seçilirse klasik Gauss/LLL kafes indirgemesi ve Babai yuvarlaması kuantum bilgisayara bile gerek duymadan gürültü vektörünü soyup anahtarı kırar. Dolayısıyla simetrik tarafta 256-bit anahtar, kafes tarafında ise kendi kurgun yerine NIST onaylı ML-KEM/ML-DSA parametreleri şarttır.
:::

::: dusun
2 boyutlu veya 10 boyutlu bir kafeste **`Gauss / LLL Lattice Reduction`** algoritması milisaniyeler içinde en kısa dik vektörleri bulup şifreyi kırabiliyor. Peki **NIST FIPS 203 (`ML-KEM / Kyber`)** standardında kafes boyutu neden $n = 512$, $768$ veya $1024$ seçilmiştir? Boyut $n$ büyüdükçe **`LLL`** algoritmasının bulabildiği vektörün kısalık kalitesi ($2^{(n-1)/2}$ çarpanı — **Hermite Factor**) neden bozulur ve hem klasik hem kuantum bilgisayarları çaresiz bırakır?
:::

::: ozet
- **`Grover's Algorithm`**, simetrik şifreleri (`AES`) ve özet fonksiyonlarını (`SHA-256`) $R_{\text{opt}} = \lfloor \frac{\pi}{4}\sqrt{N/M} \rfloor$ iterasyonda karesel hızlanmayla kırar; ancak fazla döndürme (**`Over-Rotation / Soufflé Problem`**) yapılırsa başarı olasılığı tekrar sıfıra düşer.
- Zayıf parametreli veya düşük boyutlu **`Post-Quantum Lattice (LWE)`** şemaları, **`Lagrange/Gauss`** ve **`LLL (Lenstra-Lenstra-Lovász)`** kafes indirgeme algoritmalarıyla dik baza dönüştürülüp **`Babai's Nearest Plane (CVP)`** yuvarlamasıyla kuantum bilgisayara bile gerek kalmadan kırılır.
- Gerçek kuantum sonrası güvenlik için kafes boyutu ($n \ge 512$) ve gürültü dağılımı NIST standartlarına (`ML-KEM`, `ML-DSA`) uygun seçilmelidir.
:::
