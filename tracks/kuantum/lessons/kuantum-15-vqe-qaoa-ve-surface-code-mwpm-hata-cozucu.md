---
id: kuantum-15
title: "VQE, QAOA Optimizasyonu ve Surface Code Sendrom Çözücü (Fault-Tolerant Quantum)"
track: kuantum
order: 15
duration_minutes: 40
difficulty: ileri
xp: 310
prerequisites: [kuantum-14]
tags: [vqe, qaoa, maxcut, surface-code, stabilizer-codes, mwpm, fault-tolerant-quantum, nisq]
summary: "NISQ varyasyonel algoritmaları (VQE ve MaxCut QAOA) ile hata toleranslı Surface Code sendrom ve minimum ağırlıklı eşleştirme (MWPM) hesabını uygula."
esleme: kuantum-06, kuantum-16
---

::: anlat
## Variational algoritmalar ve syndrome ölçümü

VQE/QAOA türü yöntemler parameterized circuit ile classical optimization döngüsünü birleştirir. Error correction ise farklı bir problemi, hatanın syndrome üzerinden belirlenmesini ele alır. Bu derste küçük enerji ve syndrome hesapları yapacaksın; tam surface-code decoder veya donanım threshold ölçümü çalıştırılmayacak.

Bu derste kuantum mühendisliğinin en kritik iki cephesini kodlayarak birleştiriyoruz:
1. **NISQ Cephesi — `VQE (Variational Quantum Eigensolver)` ve `QAOA (Quantum Approximate Optimization Algorithm)`:** Sığ kuantum devrelerini (`Parameterized Ansatz`) klasik bir optimizasyon döngüsüyle birleştirerek moleküler taban enerjilerini ve NP-Hard kombinatorik çizge kesme (**`MaxCut`**) problemlerini çözmek.
2. **Fault-Tolerant Cephesi — `Surface Code` ve `MWPM (Minimum Weight Perfect Matching)`:** Veri `Qubit`'lerini doğrudan ölçüp **`Superposition`** durumunu çökertmeden, komşu **`Ancilla (Syndrom) Qubit`**'leri üzerinden **`X-Stabilizer`** ve **`Z-Stabilizer`** paritelerini okuyarak hem **`Bit-Flip` ($X$)** hem **`Phase-Flip` ($Z$)** hem de birleşik **$Y = iXZ$** hatalarını yakalayıp düzeltmek!

---

### 1. `VQE (Variational Quantum Eigensolver)` ve Rayleigh-Ritz Varyasyonel İlkesi

Kuantum kimyasında bir molekülün (örneğin lityum hidrür $\text{LiH}$ veya gübre üretimindeki azot bağlayıcı $\text{FeMo-co}$ katalizörü) kararlı yapısını ve reaksiyon hızını belirleyen şey, sistemin **Hamiltonyen operatörünün ($H$) en küçük özdeğeri**, yani **Taban Durumu Enerjisi (`Ground State Energy` $E_0$)**'dır.

Kuantum mekaniğinin **`Variational Principle` (Rayleigh-Ritz İlkesi)** bize sarsılmaz bir matematiksel garanti verir: Parametreli herhangi bir deneme dalga fonksiyonu $|\psi(\vec{\theta})\rangle$ (**`Parameterized Quantum Circuit / Ansatz`**) seçtiğimizde, ölçtüğümüz beklenen enerji (**`Expectation Value`**) asla gerçek taban enerjisi $E_0$'dan küçük olamaz:

$$E(\vec{\theta}) = \langle \psi(\vec{\theta}) \,|\, H \,|\, \psi(\vec{\theta}) \rangle \ge E_0$$

#### 🔄 Hibrit Kuantum-Klasik Döngü (`Hybrid Quantum-Classical Loop`)
1. **Pauli Ayrıştırması (`Pauli Decomposition`):** Moleküler Hamiltonyen $H$, ağırlıklı **`Pauli String`** tensör çarpımlarının toplamı olarak yazılır:
   $$H = \sum_{k} c_k P_k, \quad P_k \in \{I, X, Y, Z\}^{\otimes n}$$
2. **QPU (Kuantum İşlemci) Adımı:** Sığ bir kuantum devresi $U(\vec{\theta})|0\rangle^{\otimes n}$ çalıştırılır ve her bir Pauli teriminin beklenen değeri $\langle P_k \rangle$ ölçülerek toplanır. Devre çok sığ olduğu için **`Decoherence`** süresi dolmadan ölçüm tamamlanır!
3. **CPU (Klasik Optimize Edici) Adımı:** Klasik bilgisayar (`COBYLA`, `SPSA` veya **`Parameter-Shift Rule`** gradyanı: $\frac{\partial E}{\partial \theta_i} = \frac{1}{2}\left[E(\theta_i + \frac{\pi}{2}) - E(\theta_i - \frac{\pi}{2})\right]$) enerjiyi küçültecek yeni $\vec{\theta}_{t+1}$ açılarını hesaplar ve QPU'ya geri gönderir.

---

### 2. `QAOA (Quantum Approximate Optimization Algorithm)` ve `MaxCut`

2014'te **Edward Farhi** ve arkadaşları tarafından geliştirilen **`QAOA`**, lojistik rotalama, finansal portföy optimizasyonu, VLSI çip tasarımı ve kriptografik **`SAT`** problemleri gibi **NP-Hard kombinatorik optimizasyon** problemlerini **`Ising Hamiltonian`** taban durumuna dönüştürür.

#### ✂️ `MaxCut` Probleminin Kuantum `Cost Hamiltonian` ($H_C$) Haritalaması
Bir $G = (V, E)$ çizgesinde düğümleri iki kümeye ($z_i \in \{+1, -1\}$ veya bit olarak $x_i \in \{0, 1\}$) öyle ayırmak istiyoruz ki, iki küme arasında kesilen kenarların sayısı (veya ağırlıkları toplamı $w_{ij}$) **maksimum** olsun.

- Bir $(i, j) \in E$ kenarının uçlarındaki düğümler **farklı** kümelerdeyse ($z_i \neq z_j$), çarpımları $z_i z_j = -1$ olur ve $\frac{1 - z_i z_j}{2} = 1$ (kesildi!) verir.
- Aynı kümedelerse ($z_i = z_j$), çarpımları $z_i z_j = +1$ olur ve $\frac{1 - z_i z_j}{2} = 0$ (kesilmedi) verir.

Bunu doğrudan **`Pauli-Z`** operatörlerine ($Z|0\rangle = +|0\rangle$, $Z|1\rangle = -|1\rangle$) çevirdiğimizde **`QAOA Cost Hamiltonian` ($H_C$)** ortaya çıkar:

$$H_C = \sum_{(i,j) \in E} \frac{w_{ij}}{2} \left( I - Z_i Z_j \right)$$

`QAOA` devresi başlangıçta tüm `Qubit`'leri eşit süperpozisyona ($|+\rangle^{\otimes n}$) alır ve $p$ katman boyunca sırayla iki üniter operatörü uygular:
1. **`Phase Separator Unitary` ($U_C(\gamma) = e^{-i \gamma H_C}$):** Kesim değeri yüksek olan bit dizilerine ekstra bağıl faz (**`Relative Phase`**) yükler.
2. **`Mixer Unitary` ($U_B(\beta) = e^{-i \beta H_B}$, burada $H_B = \sum_i X_i$):** Farklı bit dizilerinin genliklerini birbirine karıştırarak (**`Quantum Interference`**) yüksek kesimli durumlarda yapıcı girişim (`Constructive Interference`) yaratır!

```python
# 4 Düğümlü Halka Çizgede (C4) QAOA MaxCut Beklenen Kesim (Expectation Value) Hesabı
kenarlar = [(0, 1, 1.0), (1, 2, 1.0), (2, 3, 1.0), (3, 0, 1.0)]

def kesim_degeri(bit_dizisi, kenar_listesi):
    toplam = 0.0
    for u, v, agirlik in kenar_listesi:
        if bit_dizisi[u] != bit_dizisi[v]:
            toplam += agirlik
    return toplam

# QAOA devresinin "0101" ve "1010" (maksimum kesim = 4) durumlarını yükselttiği dağılım:
olasiliklar = {"0101": 0.42, "1010": 0.42, "0011": 0.08, "1100": 0.08}
beklenen_kesim = sum(p * kesim_degeri(durum, kenarlar) for durum, p in olasiliklar.items())
print(f"0101 Kesimi: {kesim_degeri('0101', kenarlar)} | QAOA Beklenen Kesim <C>: {beklenen_kesim:.2f}")
```

---

### 3. `Surface Code` Topolojik Hata Düzeltme ve `Stabilizer Formalism`

Klasik bilgisayarda `1` bitini korumak için onu `111` diye kopyalarsın (**`Repetition Code`**) ve çoğunluk oylaması yaparsın. Kuantumda ise iki ölümcül engel vardır:
1. **`No-Cloning Theorem`:** Bilinmeyen $|\psi\rangle = \alpha|0\rangle + \beta|1\rangle$ durumunu kopyalayamazsın!
2. **Ölçüm Çöküşü (`Wavefunction Collapse`):** Veri `Qubit`'ini "bozuldu mu?" diye doğrudan ölçtüğün an $\alpha$ ve $\beta$ süperpozisyonu çöker, kuantum hesaplama yok olur!
3. **Sürekli ve Çift Yönlü Hatalar:** Sadece **`Bit-Flip` ($X$)** değil, klasik dünyada hiç var olmayan **`Phase-Flip` ($Z$: $\alpha|0\rangle + \beta|1\rangle \to \alpha|0\rangle - \beta|1\rangle$)** ve ikisinin çarpımı **`Bit+Phase Flip` ($Y = iXZ$)** hataları da oluşur.

#### 🛡️ Çözüm: Veriyi Ölçme, Komşuların Paritesini (`Ancilla Stabilizers`) Ölç!
**Alexei Kitaev** tarafından önerilen ve bugün Google Quantum AI (**Willow** çipi) ile IBM'in ana yol haritası olan **`Surface Code`**, `Qubit`'leri 2 boyutlu bir satranç tahtası (`2D Lattice`) üzerine yerleştirir:

```
      [D0] ─────── (Z0) ─────── [D1]
       │            │            │
     (X0) ─────── [D2] ─────── (X1)
       │            │            │
      [D3] ─────── (Z1) ─────── [D4]

  [Di] : Data Qubit (Kuantum bilgisini taşıyan, ASLA doğrudan ölçülmeyen qubitler)
  (Zk) : Z-Stabilizer Ancilla (Komşu veri qubitlerinin Z⊗Z⊗Z⊗Z paritesini ölçer -> X hatalarını yakalar!)
  (Xk) : X-Stabilizer Ancilla (Komşu veri qubitlerinin X⊗X⊗X⊗X paritesini ölçer -> Z hatalarını yakalar!)
```

#### Neden `Z-Stabilizer` Ölçümü `X` Hatasını Yakalar (`Anti-Commutation`)?
Pauli matrislerinin en temel cebirsel özelliği **ters-değişme (`Anti-Commutation`)** kuralıdır:

$$X \cdot Z = -Z \cdot X$$

- Bir **`Z-Stabilizer`** ($S_Z = Z_a Z_b Z_c Z_d$), etrafındaki 4 veri `Qubit`'inden `Ancilla` üzerine `CNOT` kapılarıyla parite aktarır. Hatasız (**`Code Space`**) durumda tüm stabilizer'lar **$+1$ özdeğeri (`Sendrom biti = 0`)** verir.
- Eğer $b$ veri `Qubit`'ine çevreden bir **`Bit-Flip` ($X_b$)** gürültüsü çarparsa, $X_b$ ile $Z_b$ ters değiştiği için ($X_b Z_b = -Z_b X_b$), $b$'ye komşu olan **`Z-Stabilizer`**'ların özdeğeri **$-1$'e (`Sendrom biti = 1` / `Defect / Anyon`)** döner!
- Tam tersine, veri `Qubit`'ine bir **`Phase-Flip` ($Z_b$)** çarparsa, $Z_b$ ile $X_b$ ters değiştiği için komşu **`X-Stabilizer`**'lar **`1` (alarm!)** verir.
- Eğer **`Y` hatası ($Y = iXZ$)** oluşursa, **hem `X-Stabilizer` hem `Z-Stabilizer` aynı anda alarm verir!**

---

### 4. `MWPM (Minimum Weight Perfect Matching)` ve `Threshold Theorem`

Bir `Surface Code` ızgarasında veri `Qubit`'leri üzerinde oluşan hataların bir zinciri ($E$), yalnızca zincirin **iki uç noktasındaki (`Boundary / Endpoint`)** `Ancilla` dedektörlerini `1` olarak yakar (çünkü ortadaki `Ancilla`'lar iki hatalı `Qubit`'e birden dokunduğu için $(-1) \times (-1) = +1$ olur ve sönük kalır!).

İşte **`MWPM (Minimum Weight Perfect Matching)`** kod çözücüsü (`Decoder` — örneğin **Blossom** veya **PyMatching** algoritması):
1. Izgarada `1` yanan tüm sendrom dedektörlerini (`Defects`) alır,
2. Bu dedektörleri ikişerli eşleştirirken aralarındaki **Manhattan uzaklığı (`Graph Distance / Weight`)** toplamını en küçük yapan eşleştirmeyi bulur,
3. En olası hata zincirini tespit edip, ilgili veri `Qubit`'lerine ters Pauli kapısını uygulayarak (**veya yazılımda `Pauli Frame` kaydını güncelleyerek**) hatayı süperpozisyona hiç dokunmadan sıfırlar!

#### 🏆 `Quantum Threshold Theorem` (koşullara bağlı hata eşiği)
`Surface Code`'un hata eşiği (**`Fault-Tolerance Threshold`**) $p_{th} \approx \%1$ ($0.01$)'dir. Eğer fiziksel kapıların hata oranı $p < p_{th}$ altına indirilirse, kod uzaklığı $d$ (ızgara boyutu $d \times d$) büyütüldükçe mantıksal hata oranı $P_L \propto (p / p_{th})^{(d+1)/2}$ şeklinde **üstel olarak sıfıra gider!** (Google 2024 sonunda **Willow** işlemcisinde $d=3 \to 5 \to 7$ geçişinde bu üstel bastırmayı deneysel olarak kanıtlamıştır).

```python
# 3 Veri Qubitli Bit-Flip Stabilizer Kodu: Z0Z1 ve Z1Z2 Parite Matrisi ile Sendrom Çözümü
# H_z matrisi: Satırlar Z-Stabilizer'ları, sütunlar [D0, D1, D2] veri qubitlerini temsil eder
H_z = [
    [1, 1, 0],  # S0 = Z0 * Z1
    [0, 1, 1],  # S1 = Z1 * Z2
]

def sendrom_hesapla(H, hata_vektoru):
    return [sum(h * e for h, e in zip(satir, hata_vektoru)) % 2 for satir in H]

for q in range(3):
    hata = [1 if i == q else 0 for i in range(3)]
    print(f"D{q} uzerinde X hatasi {hata} -> Olculen Sendrom (S0, S1): {sendrom_hesapla(H_z, hata)}")
```

**Kaynak ve sınır:** [IBM Quantum: error correction](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction). Sayısal örnekler eğitim ölçeğindedir; gerçek quantum hardware, standart PQC ürünü veya ağ üzerindeki bir hedef üzerinde kabul testi yapılmaz.
:::

::: tahmin Surface Code Anti-Commutation ve Y Hatası Sendrom İmzası
Bir kuantum hata düzeltme kodunda tek bir veri `Qubit`'i ($D_1$) hem bir `X-Stabilizer` ($S_X$) hem de bir `Z-Stabilizer` ($S_Z$) tarafından izlenmektedir. Eğer $D_1$ üzerinde çevre gürültüsü nedeniyle bir **`Pauli-Y` hatası ($Y = iXZ$)** meydana gelirse, $(S_X, S_Z)$ sendrom ölçüm bitleri ne olur?

```python
# Pauli ters-degisme (Anti-commutation) kurallari:
# X-Stabilizer Z bilesenini yakalar, Z-Stabilizer X bilesenini yakalar.
def y_hatasi_sendromu(hata_tipi):
    x_bileseni_var = hata_tipi in ("X", "Y")
    z_bileseni_var = hata_tipi in ("Z", "Y")
    s_x = 1 if z_bileseni_var else 0   # X-Stabilizer Z hatasi ile anti-commute eder
    s_z = 1 if x_bileseni_var else 0   # Z-Stabilizer X hatasi ile anti-commute eder
    return (s_x, s_z)

print(f"X:{y_hatasi_sendromu('X')} | Z:{y_hatasi_sendromu('Z')} | Y:{y_hatasi_sendromu('Y')}")
```

???

```cikti
X:(0, 1) | Z:(1, 0) | Y:(1, 1)
```
`Pauli-Y` operatörü $Y = iXZ$ olduğundan hem `Bit-Flip` ($X$) hem de `Phase-Flip` ($Z$) bileşeni içerir. `Z-Stabilizer` $X$ bileşeniyle, `X-Stabilizer` ise $Z$ bileşeniyle ters-değiştiği (`Anti-Commute`) için her iki sendrom dedektörü de aynı anda tetiklenir ve `Y:(1, 1)` çıktısını üretir.
:::

::: gorev 1 · QAOA MaxCut Kesim Değeri ve Beklenen Enerji (Expectation Value) Hesabı
Bir kombinatorik optimizasyon probleminde **`QAOA`** devresinin kalitesini ölçmek için `qaoa_maxcut_beklenti(kenarlar, durum_olasiliklari)` fonksiyonunu yaz.

**Girdiler:**
- `kenarlar`: `(u, v, agirlik)` demetlerinden oluşan liste (ör. `[(0, 1, 2.0), (1, 2, 1.5)]`). Düğüm indisleri bit dizisindeki karakter konumlarıdır (`0`, `1`, ...).
- `durum_olasiliklari`: Ölçülen bit dizilerini (`str`, ör. `"010"`) olasılıklarına (`float`, ör. `0.35`) eşleyen sözlük.

**Hesaplanacak Çıktı Sözlüğü (`dict`):**
1. `"beklenen_kesim"`: Tüm olası durumlar üzerinden ağırlıklı ortalama kesim değeri $\langle C \rangle = \sum_{x} P(x) \cdot C(x)$ (`round(..., 4)` ile yuvarlanmış `float`). Bir $(u, v, w)$ kenarı yalnızca `x[u] != x[v]` olduğunda $C(x)$ toplamına $w$ kadar katkı yapar.
2. `"en_iyi_durum"`: `durum_olasiliklari` içindeki bit dizileri arasında **en yüksek $C(x)$ kesim değerini** üreten bit dizisi (`str`). Eşitlik durumunda olasılığı (`P(x)`) daha yüksek olanı, o da eşitse alfabetik (leksikografik) olarak küçük olanı seç.
3. `"en_iyi_kesim"`: `"en_iyi_durum"` durumunun kesim değeri (`round(..., 4)` ile `float`).
4. `"yaklasim_orani"`: `"en_iyi_kesim"` sıfırdan büyükse `round(beklenen_kesim / en_iyi_kesim, 4)`, sıfırsa `0.0`.

```starter
def qaoa_maxcut_beklenti(kenarlar, durum_olasiliklari):
    # TODO: QAOA MaxCut beklenen kesim <C>, en iyi durum ve yaklasim oranini (approximation ratio) hesapla
    return {
        "beklenen_kesim": 0.0,
        "en_iyi_durum": "",
        "en_iyi_kesim": 0.0,
        "yaklasim_orani": 0.0,
    }
```

```test
fn = need("qaoa_maxcut_beklenti")

kenarlar1 = [(0, 1, 1.0), (1, 2, 1.0), (2, 3, 1.0), (3, 0, 1.0)]
olas1 = {"0101": 0.45, "1010": 0.35, "0011": 0.15, "0000": 0.05}
# C(0101)=4, C(1010)=4, C(0011)=2, C(0000)=0
# <C> = 0.45*4 + 0.35*4 + 0.15*2 + 0.05*0 = 1.8 + 1.4 + 0.3 = 3.5
s1 = fn(kenarlar1, olas1)
eq(s1["beklenen_kesim"], 3.5, "C4 halkasinda beklenen kesim <C> 3.5 olmali")
eq(s1["en_iyi_durum"], "0101", "Esit maksimum kesimde olasiligi daha yuksek olan 0101 secilmeli")
eq(s1["en_iyi_kesim"], 4.0, "Maksimum kesim 4.0 olmali")
eq(s1["yaklasim_orani"], 0.875, "Yaklasim orani 3.5 / 4.0 = 0.875 olmali")

# Agirlikli cizge testi
kenarlar2 = [(0, 1, 2.5), (1, 2, 1.5), (0, 2, 3.0)]
olas2 = {"101": 0.6, "011": 0.4}
# C(101): (0,1)=2.5 + (1,2)=1.5 + (0,2)=0 -> 4.0
# C(011): (0,1)=2.5 + (1,2)=0 + (0,2)=3.0 -> 5.5
# <C> = 0.6*4.0 + 0.4*5.5 = 2.4 + 2.2 = 4.6
s2 = fn(kenarlar2, olas2)
eq(s2["beklenen_kesim"], 4.6, "Agirlikli ucgen cizgede beklenen kesim 4.6 olmali")
eq(s2["en_iyi_durum"], "011", "En yuksek agirlikli kesimi veren durum 011 olmali")
eq(s2["en_iyi_kesim"], 5.5, "En iyi kesim 5.5 olmali")
eq(s2["yaklasim_orani"], round(4.6 / 5.5, 4), "Agirlikli yaklasim orani dogru hesaplanmali")
s3 = fn([(0, 1, 1.0)], {"01": 0.5, "00": 0.5})
eq(s3["yaklasim_orani"], 0.5, "en_iyi_kesim=1.0 iken yaklasim orani 0.5 hesaplanmali")
s4 = fn([(0, 1, 1/3)], {"01": 1.0})
eq(s4["en_iyi_kesim"], 0.3333, "en_iyi_kesim 4 basamak yuvarlanmali")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def qaoa_maxcut_beklenti(kenarlar, durum_olasiliklari):\n    beklenen = 0.0\n    en_iyi_durum = ''\n    en_iyi_kesim = -1.0\n    en_iyi_olasilik = -1.0\n    for durum in sorted(durum_olasiliklari.keys()):\n        olasilik = durum_olasiliklari[durum]\n        kesim = 0.0\n        for u, v, agirlik in kenarlar:\n            if durum[u] != durum[v]:\n                kesim += agirlik\n        beklenen += olasilik * kesim\n        if kesim > en_iyi_kesim or (kesim == en_iyi_kesim and olasilik > en_iyi_olasilik):\n            en_iyi_kesim = kesim\n            en_iyi_durum = durum\n            en_iyi_olasilik = olasilik\n    en_iyi_kesim = max(0.0, en_iyi_kesim)\n    oran = round(beklenen / en_iyi_kesim, 4) if en_iyi_kesim > 0 else 0.0\n    return {'beklenen_kesim': round(beklenen, 4), 'en_iyi_durum': en_iyi_durum, 'en_iyi_kesim': round(en_iyi_kesim, 4), 'yaklasim_orani': oran}", 'referans', 'exec'), _REF)
_t, _g = _ff(qaoa_maxcut_beklenti, _REF['qaoa_maxcut_beklenti'], ([(0, 1, 1.0), (1, 2, 1.0), (2, 3, 1.0), (3, 0, 1.0)], {'0101': 0.45, '1010': 0.35, '0011': 0.15, '0000': 0.05}), tohum=3032, en_cok=600, mod='gecerli', butce='oto', ekler=[([(0, 1, 1.0, )], {'00': 1.0}, )])
ok(_t, "farksal tarama (qaoa_maxcut_beklenti): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def qaoa_maxcut_beklenti(kenarlar, durum_olasiliklari):
    beklenen = 0.0
    en_iyi_durum = ""
    en_iyi_kesim = -1.0
    en_iyi_olasilik = -1.0

    for durum in sorted(durum_olasiliklari.keys()):
        olasilik = durum_olasiliklari[durum]
        kesim = 0.0
        for u, v, agirlik in kenarlar:
            if durum[u] != durum[v]:
                kesim += agirlik
        beklenen += olasilik * kesim
        if (kesim > en_iyi_kesim) or (kesim == en_iyi_kesim and olasilik > en_iyi_olasilik):
            en_iyi_kesim = kesim
            en_iyi_durum = durum
            en_iyi_olasilik = olasilik

    en_iyi_kesim = max(0.0, en_iyi_kesim)
    oran = round(beklenen / en_iyi_kesim, 4) if en_iyi_kesim > 0 else 0.0
    return {
        "beklenen_kesim": round(beklenen, 4),
        "en_iyi_durum": en_iyi_durum,
        "en_iyi_kesim": round(en_iyi_kesim, 4),
        "yaklasim_orani": oran,
    }
```

```hint
Her bit dizisi `durum` için `kenarlar` listesindeki `(u, v, agirlik)` üçlülerini dolaş; `durum[u] != durum[v]` ise o kenar kesilmiştir ve `agirlik` kadar puan eklenir. Beklenen kesim için her durumun kesimini olasılığıyla çarpıp topla.
```
:::

::: gorev 2 · Stabilizer Sendrom Tablosundan Tekil Pauli (X/Z/Y) Hatası Konumlandırma ve Düzeltme
Bir kuantum hata düzeltme kodunda **`Z-Stabilizer`** parite matrisi $H$ ($m \times n$) kullanılarak veri `Qubit`'lerindeki tekil **`Bit-Flip` ($X$)** hatalarını tespit edip düzelten `sendrom_hata_coz(stabilizer_matrisi, olculen_sendrom, veri_durumu)` fonksiyonunu yaz.

**Girdiler:**
- `stabilizer_matrisi`: $m$ satır (her satır bir `Stabilizer` ölçümü) ve $n$ sütundan (her sütun bir veri `Qubit`'i) oluşan `0/1` matrisi (`list[list[int]]`).
- `olculen_sendrom`: `Ancilla` ölçümlerinden gelen $m$ elemanlı `0/1` listesi (`list[int]`).
- `veri_durumu`: Gürültüye maruz kalmış $n$ elemanlı mevcut bit listesi (`list[int]`).

**Kurallar ve Çıktı Sözlüğü (`dict`):**
1. Eğer `olculen_sendrom` içindeki tüm elemanlar `0` ise hata yoktur:
   - `"hatali_qubit"`: `None`
   - `"duzeltilmis_veri"`: `veri_durumu` listesinin kopyası
   - `"durum"`: `"TEMIZ"`
2. Eğer `olculen_sendrom`, `stabilizer_matrisi`'nin $j$-inci sütunu (`[stabilizer_matrisi[r][j] for r in range(m)]`) ile birebir eşleşiyorsa, tekil $X$ hatası $j$ indisli `Qubit` üzerindedir:
   - `"hatali_qubit"`: `j` (`int`)
   - `"duzeltilmis_veri"`: `veri_durumu`'nun $j$-inci biti ters çevrilmiş (`1 - bit`) yeni liste
   - `"durum"`: `"DUZELTILDI"`
3. Eğer sendrom sıfırdan farklıysa ama hiçbir tekil sütunla eşleşmiyorsa (çoklu qubit hatası):
   - `"hatali_qubit"`: `-1`
   - `"duzeltilmis_veri"`: `veri_durumu` listesinin kopyası
   - `"durum"`: `"COKLU_HATA"`

```starter
def sendrom_hata_coz(stabilizer_matrisi, olculen_sendrom, veri_durumu):
    # TODO: Stabilizer parite matrisi sutunlariyla sendromu eslestirip hatali qubiti duzelt
    return {
        "hatali_qubit": None,
        "duzeltilmis_veri": list(veri_durumu),
        "durum": "TEMIZ",
    }
```

```test
fn = need("sendrom_hata_coz")

# Hamming(7,4) / Steane Code benzeri parite matrisi (3 stabilizer, 7 qubit)
H = [
    [1, 0, 1, 0, 1, 0, 1],
    [0, 1, 1, 0, 0, 1, 1],
    [0, 0, 0, 1, 1, 1, 1],
]

# 1) Hatasiz durum
r1 = fn(H, [0, 0, 0], [1, 0, 1, 1, 0, 1, 0])
eq(r1["durum"], "TEMIZ", "Sifir sendromda durum TEMIZ olmali")
eq(r1["hatali_qubit"], None, "Sifir sendromda hatali_qubit None olmali")
eq(r1["duzeltilmis_veri"], [1, 0, 1, 1, 0, 1, 0], "Temiz durumda veri degismemeli")

# 2) Qubit 5 (sutun [0, 1, 1]) uzerinde bit-flip hatasi
bozuk = [1, 0, 1, 1, 0, 0, 0]  # 5. indis 1'den 0'a dusmus
r2 = fn(H, [0, 1, 1], bozuk)
eq(r2["durum"], "DUZELTILDI", "Sutun eslestiginde durum DUZELTILDI olmali")
eq(r2["hatali_qubit"], 5, "Sendrom [0, 1, 1] 5. sutuna karsilik gelmeli")
eq(r2["duzeltilmis_veri"], [1, 0, 1, 1, 0, 1, 0], "5. indiste bit-flip geri cevrilmeli")
ok(bozuk[5] == 0, "Girdi listesi yerinde (in-place) bozulmamali")

# 3) Coklu hata (hicbir sutunda [1, 1, 0] yokken 3 qubitli H_3 matrisi)
H3 = [
    [1, 1, 0],
    [0, 0, 1],
]
r3 = fn(H3, [1, 1], [0, 1, 0])
eq(r3["durum"], "COKLU_HATA", "Hicbir sutunla eslesmeyen sendrom COKLU_HATA donmeli")
eq(r3["hatali_qubit"], -1, "Coklu hatada hatali_qubit -1 olmali")
r4 = fn([[1, 0, 1]], [1], [0, 1, 0])
eq(r4["durum"], "DUZELTILDI", "Tek satirlik stabilizer matrisinde (m=1) hata cozulmeli")
eq(r4["hatali_qubit"], 0, "m=1 ilk sutun eslesmesi")
eq(fn([], [1], [0])["durum"], "COKLU_HATA", "Bos stabilizer matrisinde sifir olmayan sendrom COKLU_HATA donmeli")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def sendrom_hata_coz(stabilizer_matrisi, olculen_sendrom, veri_durumu):\n    kopya = list(veri_durumu)\n    if all((s == 0 for s in olculen_sendrom)):\n        return {'hatali_qubit': None, 'duzeltilmis_veri': kopya, 'durum': 'TEMIZ'}\n    m = len(stabilizer_matrisi)\n    n = len(stabilizer_matrisi[0]) if m > 0 else 0\n    for j in range(n):\n        sutun = [stabilizer_matrisi[r][j] for r in range(m)]\n        if sutun == list(olculen_sendrom):\n            kopya[j] = 1 - kopya[j]\n            return {'hatali_qubit': j, 'duzeltilmis_veri': kopya, 'durum': 'DUZELTILDI'}\n    return {'hatali_qubit': -1, 'duzeltilmis_veri': kopya, 'durum': 'COKLU_HATA'}", 'referans', 'exec'), _REF)
_t, _g = _ff(sendrom_hata_coz, _REF['sendrom_hata_coz'], ([[1, 0, 1, 0, 1, 0, 1], [0, 1, 1, 0, 0, 1, 1], [0, 0, 0, 1, 1, 1, 1]], [0, 0, 0], [1, 0, 1, 1, 0, 1, 0]), tohum=2616, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (sendrom_hata_coz): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def sendrom_hata_coz(stabilizer_matrisi, olculen_sendrom, veri_durumu):
    kopya = list(veri_durumu)
    if all(s == 0 for s in olculen_sendrom):
        return {
            "hatali_qubit": None,
            "duzeltilmis_veri": kopya,
            "durum": "TEMIZ",
        }

    m = len(stabilizer_matrisi)
    n = len(stabilizer_matrisi[0]) if m > 0 else 0

    for j in range(n):
        sutun = [stabilizer_matrisi[r][j] for r in range(m)]
        if sutun == list(olculen_sendrom):
            kopya[j] = 1 - kopya[j]
            return {
                "hatali_qubit": j,
                "duzeltilmis_veri": kopya,
                "durum": "DUZELTILDI",
            }

    return {
        "hatali_qubit": -1,
        "duzeltilmis_veri": kopya,
        "durum": "COKLU_HATA",
    }
```

```hint
Önce `all(s == 0 for s in olculen_sendrom)` ile hatasız durumu kontrol et. Değilse `j` sütunlarını (`[stabilizer_matrisi[r][j] for r in range(m)]`) tek tek `olculen_sendrom` ile karşılaştır; eşleşen `j` indisinde `kopya[j] = 1 - kopya[j]` yaparak düzelt.
```
:::

::: gorev 3 · VQE: Tek Qubit Hamiltoniyeninde Varyasyonel Minimum
**VQE**, parametreli bir devrenin (ansatz) enerjisini klasik bir optimizasyonla küçültür; Rayleigh-Ritz ilkesi gereği bulunan enerji gerçek taban enerjisinden asla küçük olamaz. `vqe_tek_qubit(a, b, adim_sayisi)` işlevini yaz.

**Model:** $H = a Z + b X$; ansatz $|\psi(\theta)\rangle = R_y(\theta)|0\rangle = [\cos(\theta/2), \sin(\theta/2)]$; enerji $E(\theta) = \langle\psi|H|\psi\rangle = a\cos\theta + b\sin\theta$.

**Kurallar:**
1. `a`, `b` sonlu sayı, `adim_sayisi` en az 4 olan `int` olmalı (`bool` değil); değilse `ValueError`.
2. Izgara: $\theta_k = 2\pi k / \text{adim\_sayisi}$, $k = 0..\text{adim\_sayisi}-1$. En küçük $E$'yi veren **ilk** $\theta_k$'yı seç.
3. Tam taban enerjisi $E_0 = -\sqrt{a^2 + b^2}$.
4. Çıktı (hepsi `round(·, 6)`): `"en_iyi_teta"`, `"en_iyi_enerji"`, `"tam_enerji"`, `"hata"` ($E_{\min} - E_0$, hiçbir zaman negatif değil).

```starter
def vqe_tek_qubit(a, b, adim_sayisi):
    # KUSURLU BAŞLANGIÇ: yalnız θ = 0'ı deniyor
    return {"en_iyi_teta": 0.0, "en_iyi_enerji": float(a), "tam_enerji": -abs(a), "hata": 0.0}

print(vqe_tek_qubit(1.0, 1.0, 8))
```

```test
import math
fn = need("vqe_tek_qubit")
r = fn(1.0, 0.0, 8)
eq(r["en_iyi_teta"], round(math.pi, 6), "H = Z: minimum θ = π'de (|1⟩)")
eq(r["en_iyi_enerji"], -1.0, "E(π) = -1")
eq(r["hata"], 0.0, "ızgara π'yi içerdiği için hata 0")
r2 = fn(1.0, 1.0, 8)
eq(r2["tam_enerji"], -1.414214, "E0 = -√2")
eq(r2["en_iyi_teta"], round(5 * math.pi / 4, 6), "minimum 5π/4'te")
eq(r2["hata"], 0.0, "5π/4 ızgarada: tam enerji bulunur")
r3 = fn(1.0, 1.0, 6)
eq(r3["en_iyi_enerji"], -1.366025, "60°'lik ızgarada en iyi nokta 240°: cos + sin = -1.366025")
eq(r3["hata"], 0.048188, "kaba ızgara taban enerjisinin üstünde kalır (Rayleigh-Ritz): √2 − (1+√3)/2")
eq(fn(0.0, 0.0, 4)["en_iyi_teta"], 0.0, "H = 0: tüm θ eşit, ilk θ seçilir")
raises(ValueError, fn, 1.0, 1.0, 3)
raises(ValueError, fn, 1.0, 1.0, 8.0)
raises(ValueError, fn, "1", 1.0, 8)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef vqe_tek_qubit(a, b, adim_sayisi):\n    for v in (a, b):\n        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):\n            raise ValueError('a ve b sonlu sayı olmalı')\n    if isinstance(adim_sayisi, bool) or not isinstance(adim_sayisi, int) or adim_sayisi < 4:\n        raise ValueError('adim_sayisi en az 4 olan tam sayı olmalı')\n    en_iyi_t, en_iyi_e = (None, None)\n    for k in range(adim_sayisi):\n        t = 2 * math.pi * k / adim_sayisi\n        e = a * math.cos(t) + b * math.sin(t)\n        if en_iyi_e is None or e < en_iyi_e - 1e-12:\n            en_iyi_t, en_iyi_e = (t, e)\n    e0 = -math.sqrt(a * a + b * b)\n    return {'en_iyi_teta': round(en_iyi_t, 6), 'en_iyi_enerji': round(en_iyi_e, 6), 'tam_enerji': round(e0, 6), 'hata': round(max(0.0, en_iyi_e - e0), 6)}", 'referans', 'exec'), _REF)
_t, _g = _ff(vqe_tek_qubit, _REF['vqe_tek_qubit'], (1.0, 1.0, 8), tohum=2315, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (vqe_tek_qubit): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def vqe_tek_qubit(a, b, adim_sayisi):
    for v in (a, b):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError("a ve b sonlu sayı olmalı")
    if isinstance(adim_sayisi, bool) or not isinstance(adim_sayisi, int) or adim_sayisi < 4:
        raise ValueError("adim_sayisi en az 4 olan tam sayı olmalı")
    en_iyi_t, en_iyi_e = None, None
    for k in range(adim_sayisi):
        t = 2 * math.pi * k / adim_sayisi
        e = a * math.cos(t) + b * math.sin(t)
        if en_iyi_e is None or e < en_iyi_e - 1e-12:
            en_iyi_t, en_iyi_e = t, e
    e0 = -math.sqrt(a * a + b * b)
    return {"en_iyi_teta": round(en_iyi_t, 6), "en_iyi_enerji": round(en_iyi_e, 6),
            "tam_enerji": round(e0, 6), "hata": round(max(0.0, en_iyi_e - e0), 6)}
```

```hint
Izgarada dolaşırken yalnız kesinlikle daha küçük enerji bulunca güncelle (eşitlikte ilk θ kalır).
```
:::

::: gorev 4 · Dört sendrom olayını en düşük toplam ağırlıkla eşleştir
Dört olayın numarası 0, 1, 2 ve 3. Simetrik `agirliklar` matrisi, her olay çifti arasındaki yolun önceden hesaplanmış negatif olmayan maliyetini verir. Her olay tam bir çifte girsin. `sendrom_esle(agirliklar)` işlevi en düşük toplam maliyeti ve seçilen iki çifti `{"maliyet": toplam, "ciftler": [(a, b), (c, d)]}` biçiminde döndürsün. Her çiftte küçük numara önce gelsin ve çiftler sözlük sırasıyla listelensin. Maliyetler eşitse çift listesi sözlük sırasına göre en küçük olan çözümü seç.

Dört olayda yalnız üç tam eşleştirme vardır. Olay 0'ın eşini seçtiğinde diğer çift de belirlenir. Her seçimin **iki** kenarının maliyetini topla. En ucuz tek kenarı seçmek toplamı en aza indirmeyebilir.

```starter
def sendrom_esle(agirliklar):
    # Sabit eşleştirme, diğer iki olasılığın maliyetine bakmıyor.
    return {"maliyet": agirliklar[0][1] + agirliklar[2][3],
            "ciftler": [(0, 1), (2, 3)]}
```
```solution
def sendrom_esle(agirliklar):
    adaylar = []
    for es in (1, 2, 3):
        sol, sag = [i for i in (1, 2, 3) if i != es]
        maliyet = agirliklar[0][es] + agirliklar[sol][sag]
        adaylar.append((maliyet, [(0, es), (sol, sag)]))
    maliyet, ciftler = min(adaylar)
    return {"maliyet": maliyet, "ciftler": ciftler}
```
```test
f = need("sendrom_esle")
a = [[0, 1, 3, 4], [1, 0, 4, 3], [3, 4, 0, 7], [4, 3, 7, 0]]
eq(f(a), {"maliyet": 6, "ciftler": [(0, 2), (1, 3)]},
   "En ucuz tek kenarla başlayan eşleştirme 8 tutar")
b = [[0, 4, 4, 1], [4, 0, 1, 4], [4, 1, 0, 4], [1, 4, 4, 0]]
eq(f(b), {"maliyet": 2, "ciftler": [(0, 3), (1, 2)]}, "Üçüncü eşleştirme de değerlendirilir")
c = [[0, 2, 2, 2], [2, 0, 2, 2], [2, 2, 0, 2], [2, 2, 2, 0]]
eq(f(c), {"maliyet": 4, "ciftler": [(0, 1), (2, 3)]}, "Eşit maliyette sözlük sırası")
```
:::

::: anlat Sınır
Görevler QAOA ile MaxCut beklenen enerjisini ve stabilizer sendrom tablosundan tek Pauli hatasını bulmayı hesaplatır; VQE görevi tek qubit'li bir Hamiltoniyende ızgara aramasıyla sınırlıdır; gerçek VQE'deki ölçüm gürültüsü ve çok parametreli optimizasyon yoktur. Tek katmanlı (p=1) QAOA küçük graflarda klasik yaklaşık algoritmaları geçemez; varyasyonel yöntemlerde barren plateau ve ölçüm gürültüsü optimizasyonu zorlaştırır. Sendrom tablosu tek hata varsayar. Dördüncü görev, önceden hesaplanmış ağırlıklarla dört olayı tam eşleştirir. Surface code kod çözücüsünde sınırlarla eşleşme, ardışık ölçüm turları ve düzeltme yollarının çıkarılması da gerekir. Simülasyon gürültüsüzdür.

Kaynaklar: [Peruzzo vd. 2014 - A variational eigenvalue solver on a quantum processor](https://arxiv.org/abs/1304.3061), [Farhi vd. 2014 - A Quantum Approximate Optimization Algorithm](https://arxiv.org/abs/1411.4028), [Fowler vd. 2012 - Surface codes: Towards practical large-scale quantum computation](https://arxiv.org/abs/1208.0928).
:::

::: dusun
`RSA-2048` şifresini `Shor` algoritmasıyla kırmak için yaklaşık **4.000 kusursuz `Logical Qubit`** gerekirken, neden güvenlik raporlarında bunun için **4.000 değil de ~20 Milyon fiziksel `Qubit`** gerektiği söyleniyor? **`Surface Code` mesafesi ($d \approx 27$)** ve **`Magic State Distillation` ($T$-kapısı fabrikaları)** maliyeti açısından bu $5.000\times$ fiziksel ek yükü (`Overhead`) nasıl açıklarsın?
:::

::: ozet
- **`NISQ (Noisy Intermediate-Scale Quantum)`** işlemcilerde derin devreler çalıştırılamadığı için **`VQE`** (moleküler taban enerjisi $\langle \psi(\theta)|H|\psi(\theta)\rangle \ge E_0$) ve **`QAOA`** (**`MaxCut`** gibi kombinatorik `Ising` problemleri) sığ parametreli devreleri klasik optimizasyon döngüsüyle birleştirir.
- **`Surface Code`**, veri `Qubit`'lerini doğrudan ölçüp süperpozisyonu çökertmek yerine, komşu **`X-Stabilizer`** ve **`Z-Stabilizer`** (`Ancilla`) paritelerini ölçer; Pauli ters-değişme (**`Anti-Commutation`**: $XZ = -ZX$) kuralı sayesinde hem `Bit-Flip` ($X$) hem de `Phase-Flip` ($Z$) hatalarını yakalar.
- **`MWPM (Minimum Weight Perfect Matching)`** algoritması, 2 boyutlu ızgarada yanan sendrom dedektörlerini (`Defects`) en kısa yol ağırlığıyla eşleştirerek en olası hata zincirini bulur; fiziksel kapı hatası **`Threshold` ($\approx \%1$)** altında kaldığı sürece kod boyutu büyüdükçe mantıksal hata oranı üstel olarak sıfırlanır.
:::
