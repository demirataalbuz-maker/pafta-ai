---
id: kuantum-02
title: Quantum Gates, Entanglement, No-Cloning ve Bell / CHSH Deneyi
summary: Unitary Quantum Gates (Hadamard, Pauli X/Z, CNOT), Einstein'ın "uzaktan hayaletimsi etki" dediği Quantum Entanglement (Bell States), No-Cloning Theorem ve klasik fiziği yıkan CHSH eşitsizliği.
esleme: kuantum-01, kuantum-03
---

::: anlat 1. Quantum Gates (Kuantum Kapıları) Neden Tersinir (Reversible) Olmak Zorundadır?
## Quantum gates ve entanglement

Quantum gate işlemleri, birden fazla qubitin ortak durumu ve CHSH örneği üzerinden classical correlation ile quantum correlation farkını inceleyeceksin. Uzak ölçümlerin correlation göstermesi, denetlenebilir bir mesajın ışıktan hızlı gönderilmesini sağlamaz.

Kuantum mekaniğinde ise Schrödinger denklemi gereği kapalı bir sistemde bilgi asla yok olmaz! Bu yüzden ölçüm yapmadığın sürece her **`Quantum Gate` (Kuantum Kapısı)**:
1. Toplam olasılığı ($|\alpha|^2 + |\beta|^2 = 1$) korumak zorundadır,
2. Geri sarılabilir (**`Reversible`**) olmak zorundadır,
3. Matematiksel olarak bir **`Unitary Matrix` ($U^\dagger U = I$)** olmak zorundadır! (Yani her kuantum kapısı aslında `Bloch Sphere` üzerinde yapılan kusursuz bir döndürme veya yansıtma işlemidir).

### 🎛️ En Temel 4 Kuantum Kapısı
| Kapı Adı | Matris Gösterimi | Ne Yapar? (Sezgisel Karşılığı) |
| :--- | :---: | :--- |
| **`Pauli-X Gate` (`Quantum NOT`)** | $X = \begin{bmatrix} 0 & 1 \\ 1 & 0 \end{bmatrix}$ | Klasik `NOT` kapısıdır: $|0\rangle \leftrightarrow |1\rangle$ yer değiştirir (Kuzey ve Güney kutbunu çevirir). |
| **`Pauli-Z Gate` (`Phase Flip`)** | $Z = \begin{bmatrix} 1 & 0 \\ 0 & -1 \end{bmatrix}$ | $|0\rangle$'a dokunmaz, $|1\rangle$'in önüne **eksi işareti (`Phase Flip`: $|1\rangle \to -|1\rangle$)** koyar! |
| **`Hadamard Gate` ($H$)** | $H = \frac{1}{\sqrt{2}}\begin{bmatrix} 1 & 1 \\ 1 & -1 \end{bmatrix}$ | **Süperpozisyon Makinesi:** Kesin olan $|0\rangle$ durumunu eşit süperpozisyon $|+\rangle = \frac{|0\rangle+|1\rangle}{\sqrt{2}}$ durumuna, $|1\rangle$ durumunu ise $|-\rangle = \frac{|0\rangle-|1\rangle}{\sqrt{2}}$ durumuna taşır. **Ve kendi kendisinin tersidir ($H \cdot H = I$)!** |
| **`CNOT Gate` (`Controlled-NOT`)** | $4 \times 4\text{ Matris}$ | İki `Qubit` alır (`Control` ve `Target`). Eğer `Control Qubit` $|1\rangle$ ise `Target Qubit`'e `NOT` ($X$) uygular; $|0\rangle$ ise dokunmaz. **entanglement (`Entanglement`) üreten anahtar kapıdır!** |

```python
import math

# Hadamard kapısının (H) kendi kendisinin tersi (H * H = I) olduğunu ve girişim yarattığını görelim
s = 1 / math.sqrt(2)
def hadamard_uygula(durum):
    a, b = durum
    return (round(s * (a + b), 6), round(s * (a - b), 6))

ket0 = (1.0, 0.0)
arti_durumu = hadamard_uygula(ket0)          # |0⟩ -> |+⟩
geri_donus = hadamard_uygula(arti_durumu)    # |+⟩ -> |0⟩ (Yapıcı ve yıkıcı girişim!)
print("|0⟩ -> H ->", arti_durumu, "-> H ->", geri_donus)
```

**Kaynak ve sınır:** [IBM Quantum: temel quantum information](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information). Sayısal örnekler eğitim ölçeğindedir; gerçek quantum hardware, standart PQC ürünü veya ağ üzerindeki bir hedef üzerinde kabul testi yapılmaz.
:::

::: anlat 2. Quantum Entanglement (Kuantum entanglement) ve Bell States
Şimdi kuantum fiziğinin en büyüleyici kavramına geliyoruz: **`Quantum Entanglement` (Kuantum entanglement)**.

İki `Qubit`'imiz olsun ve ikisi de başlangıçta $|00\rangle$ durumunda dursun. Çok basit **2 adımlı bir devre** kuruyoruz:
1. Birinci `Qubit`'e **`Hadamard ($H$)`** kapısı uygula $\to$ Durum: $\frac{1}{\sqrt{2}}(|00\rangle + |10\rangle)$.
2. Birinci `Qubit` kontrol, ikinci `Qubit` hedef olacak şekilde **`CNOT`** kapısı uygula!

İkinci `Qubit`, sadece birinci `Qubit` $1$ olduğunda ters döneceği için ($|10\rangle \to |11\rangle$), ortaya ünlü **`Bell State` ($|\Phi^+\rangle$)** çıkar:

$$|\Phi^+\rangle = \frac{1}{\sqrt{2}}|00\rangle + \frac{1}{\sqrt{2}}|11\rangle$$

### 🤯 Bu Denklem Neden İnanılmazdır?
Bu denkleme dikkatle bak: İçinde $|01\rangle$ yok, $|10\rangle$ yok! Sadece $|00\rangle$ (%50 olasılık) ve $|11\rangle$ (%50 olasılık) var.
- Şimdi bu iki `Qubit`'ten birini İstanbul'da bırak, diğerini **10 ışık yılı uzaktaki bir galaksiye** gönder.
- İstanbul'daki `Qubit` tek başına ölçüldüğünde %50 ihtimalle $0$, %50 ihtimalle $1$ verir (tamamen rastgele!).
- **AMA** İstanbul'daki `Qubit`'i ölçtüğün ve ekranda **$1$** gördüğün salisede, 10 ışık yılı uzaktaki diğer `Qubit`'in durumu da **anında %100 kesinlikle $1$** olur!

Albert Einstein buna itiraz etmişti: kuantum rastlantısına ("Tanrı zar atmaz", 1926) ve "uzaktan hayaletimsi etki"ye (*spooky action at a distance*, 1947) karşı çıkmış, parçacıkların ayrılırken içlerine önceden kararlaştırılmış gizli bir bilgi (`Local Hidden Variables`) konulduğunu düşünmüştü.
:::

::: anlat 3. Einstein Yanıldı mı? Bell Theorem ve CHSH Oyunu (2022 Nobel Fizik Ödülü)
Einstein'ın dediği doğru olabilir mi? Yani dolanık `Qubit`'ler ayrılırken bir çift ayakkabının sağ ve sol tekini iki kutuya koymuşuz gibi önceden belirlenmiş gizli bir bilgi (`Local Realism`) taşıyor olabilir mi?

1964'te fizikçi **John Stewart Bell** (ve ardından Clauser, Horne, Shimony, Holt — **`CHSH Inequality`**), Einstein'ın "gizli değişken" hipotezini matematiksel bir oyuna dönüştürdü:

### 🎮 `CHSH Game` (Klasik vs Kuantum İletişimsiz İşbirliği Oyunu)
- Alice ve Bob iki ayrı odadadır, oyun başladıktan sonra birbirleriyle **asla haberleşemezler**.
- Hakem Alice'e rastgele bir bit $x \in \{0, 1\}$, Bob'a rastgele bir bit $y \in \{0, 1\}$ gönderir.
- Alice bir bit $a \in \{0, 1\}$, Bob bir bit $b \in \{0, 1\}$ üretir.
- **Kazanma Kuralı:** Alice ve Bob'un çıktılarının `XOR` toplamı, hakemin girdilerinin `AND` çarpımına eşit olmalıdır:
$$a \oplus b = x \cdot y$$
(Yani yalnız $x=1$ ve $y=1$ olduğunda Alice ve Bob **farklı** bit vermeli, diğer 3 durumda **aynı** biti vermelidir!).

1. **Klasik Fizik Sınırı (`Bell Bound`):** Alice ve Bob önceden hangi gizli stratejiyi veya kopya kağıdını (`Hidden Variable`) anlaşırsa anlaşsın, 4 durumdan en fazla 3'ünü tutturabilirler. Klasik evrende maksimum kazanma olasılığı **kesinlikle $\le \%75$ ($0.75$)**'tir!
2. **Kuantum entanglement Sınırı (`Tsirelson's Bound`):** Eğer Alice ve Bob yanlarına bir çift dolanık `Qubit` ($|\Phi^+\rangle$) alıp ölçüm açılarını ($\theta_A, \theta_B$) döndürürlerse, oyunu **$\cos^2(\pi / 8) \approx \mathbf{\%85.36}$ ($0.8536$) olasılıkla kazanırlar!**

Alain Aspect, John Clauser ve Anton Zeilinger dolaşık fotonlarla Bell eşitsizliğinin ihlal edildiğini deneylerle göstererek **2022 Nobel Fizik Ödülü**'nü kazandılar (CHSH oyunundaki %85.36, bu ihlalin oyun diliyle karşılığıdır). Sonuç nettir: **Evren yerel-gerçekçi (`Locally Real`) değildir; `Qubit` ölçülene kadar içinde gizli bir değer taşımaz!**
:::

::: anlat 4. No-Cloning Theorem ve Işıktan Hızlı Haberleşme Neden İmkansızdır?
İki noktayı ayrı inceleyelim:

Konferansta hemen şu iki zeki soru gelecektir:

### Soru 1: *"Madem uzaktaki Qubit anında etkileniyor, bununla ışıktan hızlı Mors alfabesi gönderebilir miyiz?"*
**Hayır (`No-Communication Theorem`)!** Neden?
- Çünkü İstanbul'daki Alice kendi `Qubit`'ini ölçtüğünde ekranda $0$ mı yoksa $1$ mi çıkacağını **kontrol edemez**; sonuç %50-%50 tamamen rastgeledir!
- Uzaktaki Bob kendi `Qubit`'ini ölçtüğünde de sadece %50 $0$, %50 $1$ görür. Bob, elindeki sonucun Alice'in yaptığı ölçümden mi kaynaklandığını ancak Alice onu **klasik bir telefon/radyo kanalıyla (ışık hızıyla)** arayıp kendi sonuçlarıyla karşılaştırdığında anlayabilir!

### Soru 2: *"Klasik bilgisayarda bir dosyayı Kopyala-Yapıştır (`Ctrl+C / Ctrl+V`) yapabiliyoruz; bilinmeyen bir `Qubit` durumunu $|\psi\rangle$ kopyalayabilir miyiz?"*
**Kesinlikle Hayır (`No-Cloning Theorem` — Wootters & Zurek, 1982)!**
- Bilinmeyen bir $|\psi\rangle = \alpha|0\rangle + \beta|1\rangle$ durumunu bozmadan ikinci bir `Qubit`'e kopyalayacak ($|\psi\rangle|0\rangle \to |\psi\rangle|\psi\rangle$) hiçbir doğrusal `Unitary` kuantum kapısı **var olamaz** (çünkü kopyalama işlemi kareseldir: $\alpha^2, \beta^2$, oysa kuantum mekaniği tamamen doğrusaldır!).
- **Siber Güvenlik Yaklaşımı (`Quantum Key Distribution - BB84`):** İşte `No-Cloning Theorem` sayesinde kuantum iletişim hattını dinlemeye çalışan bir saldırgan (`Eavesdropper`), geçen `Qubit`'in kopyasını alamaz; okumaya çalıştığı anda `Superposition` çöker ve hat üzerindeki hata oranı (`QBER`) artarak saldırganı **fizik yasaları gereği anında ele verir!**
:::

::: tahmin CHSH Oyunu: Klasik Fizik Sınırı vs Kuantum entanglement Sınırı
Aşağıdaki kod, haberleşemeyen Alice ve Bob'un `CHSH` oyununda klasik gizli değişkenlerle alabileceği maksimum kazanma yüzdesi ile kuantum entanglement (`Tsirelson's Bound`: $\cos^2(\pi/8)$) kazanma yüzdesini hesaplar. Çıktı nedir?

```python
import math
klasik_max = round(3 / 4 * 100, 1)
kuantum_max = round((math.cos(math.pi / 8) ** 2) * 100, 1)
print(f"Klasik Sinir: %{klasik_max} | Kuantum Sinir: %{kuantum_max}")
```

???

```cikti
Klasik Sinir: %75.0 | Kuantum Sinir: %85.4
```
Klasik fizikte (`Local Hidden Variables`) 4 durumdan en çok 3'ü sağlandığı için tavan `%75.0`'tir; kuantum dolanıklığında ise genliklerin kosinüs girişimi sayesinde başarı $\cos^2(\pi/8) \approx \%85.4$'e ulaşır ve Bell eşitsizliği kırılır.
:::

::: gorev 1 · Bell Durumu ve CHSH Oyununda Kazanma Olasılığı
`bell_chsh(alice_acilari, bob_acilari)` işlevini yaz. İki parçası var:

**A) Bell durumu:** `|00⟩ = [1, 0, 0, 0]` vektörüne önce birinci qubit'e `H` (yani $H \otimes I$), sonra birinci qubit kontrol, ikinci hedef olacak şekilde `CNOT` uygula. Sonuç `"bell_durumu"` (genlikler `round(·, 6)`): $|\Phi^+\rangle = (|00\rangle + |11\rangle)/\sqrt{2}$ çıkmalı.

**B) CHSH oyunu:** Alice $x$ sorusunda $a_x$ açısıyla, Bob $y$ sorusunda $b_y$ açısıyla ölçer (açılar **radyan**). $|\Phi^+\rangle$ için iki sonucun **aynı** çıkma olasılığı $\cos^2(a_x - b_y)$'dir. Kazanma kuralı $a \oplus b = x \cdot y$: $x \cdot y = 0$ ise aynı sonuç, $x = y = 1$ ise farklı sonuç kazandırır. Yani
$$P_{\text{kazan}}(x, y) = \begin{cases}\cos^2(a_x - b_y) & x \cdot y = 0 \\ \sin^2(a_x - b_y) & x = y = 1\end{cases}$$

Çıktı: `"bell_durumu"`, `"kazanma"`: `{"00", "01", "10", "11"}` anahtarlı olasılıklar (`round(·, 6)`), `"toplam_kazanma"`: dördünün ortalaması (`round(·, 6)`), `"klasik_siniri_asti_mi"`: ortalama $> 0.75 + 10^{-12}$.

Her açı listesi 2 sonlu sayıdan oluşmalı (`bool` değil); değilse `ValueError`.

```starter
def bell_chsh(alice_acilari, bob_acilari):
    # KUSURLU BAŞLANGIÇ: dolaşıklığı yok sayıp klasik en iyi stratejinin sonucunu döndürüyor
    return {"bell_durumu": [1.0, 0.0, 0.0, 0.0], "kazanma": {"00": 1.0, "01": 1.0, "10": 1.0, "11": 0.0},
            "toplam_kazanma": 0.75, "klasik_siniri_asti_mi": False}

import math
print(bell_chsh([0.0, math.pi / 4], [math.pi / 8, -math.pi / 8]))
```

```test
import math
fn = need("bell_chsh")
r = fn([0.0, math.pi / 4], [math.pi / 8, -math.pi / 8])
eq(r["bell_durumu"], [0.707107, 0.0, 0.0, 0.707107], "H sonra CNOT: (|00⟩ + |11⟩)/√2")
c = round(math.cos(math.pi / 8) ** 2, 6)
eq(r["kazanma"], {"00": c, "01": c, "10": c, "11": c}, "optimal açılarda dört soru da cos²(π/8)")
eq(r["toplam_kazanma"], 0.853553, "Tsirelson sınırı cos²(π/8)")
eq(r["klasik_siniri_asti_mi"], True, "0.8536 > 0.75")
r2 = fn([0.0, 0.0], [0.0, 0.0])
eq(r2["kazanma"], {"00": 1.0, "01": 1.0, "10": 1.0, "11": 0.0}, "aynı açılar: (1,1) sorusunda hep kaybeder")
eq(r2["toplam_kazanma"], 0.75, "klasik sınıra eşit")
eq(r2["klasik_siniri_asti_mi"], False, "0.75 sınırı aşmak değildir")
r3 = fn([0.0, math.pi / 2], [0.0, math.pi / 4])
eq(r3["kazanma"]["11"], 0.5, "π/2 − π/4 farkında sin²(π/4) = 0.5")
eq(r3["kazanma"]["10"], 0.0, "π/2 farkında cos² = 0")
raises(ValueError, fn, [0.0], [0.0, 0.0])
raises(ValueError, fn, [0.0, True], [0.0, 0.0])
raises(ValueError, fn, [0.0, float("inf")], [0.0, 0.0])
eq(fn([0.0, 2e-6], [1e-6, -1e-6])["klasik_siniri_asti_mi"], True, "0.75 + 1.5e-12 > 0.75 + 1e-12")
eq(fn([0.0, 1e-6], [5e-7, -5e-7])["klasik_siniri_asti_mi"], False, "0.75 + 3.75e-13 <= 0.75 + 1e-12")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef bell_chsh(alice_acilari, bob_acilari):\n    for acilar in (alice_acilari, bob_acilari):\n        if not isinstance(acilar, list) or len(acilar) != 2:\n            raise ValueError('her açı listesi 2 öğeli olmalı')\n        for v in acilar:\n            if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):\n                raise ValueError('açılar sonlu sayı olmalı')\n    h = 1 / math.sqrt(2)\n    durum = [1.0, 0.0, 0.0, 0.0]\n    yeni = [0.0] * 4\n    for i in range(4):\n        q0, q1 = (i >> 1, i & 1)\n        for b in (0, 1):\n            isaret = -1.0 if q0 == 1 and b == 1 else 1.0\n            yeni[b << 1 | q1] += h * isaret * durum[i]\n    durum = [yeni[0], yeni[1], yeni[3], yeni[2]]\n    kazanma = {}\n    for x in (0, 1):\n        for y in (0, 1):\n            fark = alice_acilari[x] - bob_acilari[y]\n            p = math.sin(fark) ** 2 if x * y == 1 else math.cos(fark) ** 2\n            kazanma[f'{x}{y}'] = round(p, 6)\n    ort = sum((math.sin(alice_acilari[x] - bob_acilari[y]) ** 2 if x * y == 1 else math.cos(alice_acilari[x] - bob_acilari[y]) ** 2 for x in (0, 1) for y in (0, 1))) / 4\n    return {'bell_durumu': [round(a, 6) for a in durum], 'kazanma': kazanma, 'toplam_kazanma': round(ort, 6), 'klasik_siniri_asti_mi': ort > 0.75 + 1e-12}", 'referans', 'exec'), _REF)
_t, _g = _ff(bell_chsh, _REF['bell_chsh'], ([0.0, 0.7853981633974483], [0.39269908169872414, -0.39269908169872414]), tohum=1848, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (bell_chsh): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def bell_chsh(alice_acilari, bob_acilari):
    for acilar in (alice_acilari, bob_acilari):
        if not isinstance(acilar, list) or len(acilar) != 2:
            raise ValueError("her açı listesi 2 öğeli olmalı")
        for v in acilar:
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                raise ValueError("açılar sonlu sayı olmalı")
    h = 1 / math.sqrt(2)
    durum = [1.0, 0.0, 0.0, 0.0]
    # H ⊗ I: birinci qubit (yüksek bit) üzerinde Hadamard
    yeni = [0.0] * 4
    for i in range(4):
        q0, q1 = i >> 1, i & 1
        for b in (0, 1):
            isaret = -1.0 if (q0 == 1 and b == 1) else 1.0
            yeni[(b << 1) | q1] += h * isaret * durum[i]
    # CNOT: birinci kontrol, ikinci hedef → |10⟩ ↔ |11⟩
    durum = [yeni[0], yeni[1], yeni[3], yeni[2]]
    kazanma = {}
    for x in (0, 1):
        for y in (0, 1):
            fark = alice_acilari[x] - bob_acilari[y]
            p = math.sin(fark) ** 2 if x * y == 1 else math.cos(fark) ** 2
            kazanma[f"{x}{y}"] = round(p, 6)
    ort = sum(math.sin(alice_acilari[x] - bob_acilari[y]) ** 2 if x * y == 1 else math.cos(alice_acilari[x] - bob_acilari[y]) ** 2
              for x in (0, 1) for y in (0, 1)) / 4
    return {"bell_durumu": [round(a, 6) for a in durum], "kazanma": kazanma,
            "toplam_kazanma": round(ort, 6), "klasik_siniri_asti_mi": ort > 0.75 + 1e-12}
```

```hint
Durum indeksi `i = 2·q0 + q1`. CNOT yalnız `|10⟩` ile `|11⟩` genliklerini yer değiştirir. Ortalamayı yuvarlanmamış değerlerden al.
```
:::

::: gorev 2 · Hadamard ile bağıl fazı ölçümde görünür kıl
`hadamard_dizisi(durum, adet)` işlevi iki genlikli bir saf qubit'e arka arkaya `adet` kez Hadamard uygulasın. `adet` negatif olmayan tam sayıdır. Her uygulamada yeni genlikler `(a + b) / sqrt(2)` ve `(a - b) / sqrt(2)` olur. Çıkışı iki genlikli liste olarak ver. Genlikleri karmaşık sayı olarak işleyebil ve girdiyi koru.

Tek uygulama, aynı ölçüm dağılımıyla başlayan artı ve eksi durumlarını ayrı ölçüm sonuçlarına taşır. İkinci uygulama ilkini geri alır çünkü Hadamard matrisi kendi tersidir.

```starter
def hadamard_dizisi(durum, adet):
    # Girdiyi döndürür ve tek uygulamada bağıl fazın etkisini kaçırır.
    return list(durum)
```
```solution
import math

def hadamard_dizisi(durum, adet):
    a, b = durum
    olcek = math.sqrt(2)
    for _ in range(adet):
        a, b = (a + b) / olcek, (a - b) / olcek
    return [a, b]
```
```test
f = need("hadamard_dizisi")
s = 2**-0.5

def yakin_genlikler(gercek, beklenen):
    return isinstance(gercek, list) and len(gercek) == 2 and all(
        abs(a - b) < 1e-12 for a, b in zip(gercek, beklenen)
    )

ok(yakin_genlikler(f([0, 1], 1), [s, -s]), "İkinci matris sütunu")
ok(yakin_genlikler(f([s, s], 1), [1, 0]), "Artı durumundan sıfıra")
ok(yakin_genlikler(f([s, -s], 1), [0, 1]), "Eksi durumundan bire")
girdi = [0.6, 0.8j]
yedek = girdi[:]
ok(yakin_genlikler(f(girdi, 0), yedek), "Sıfır uygulama")
ok(yakin_genlikler(f(girdi, 2), yedek), "İki uygulamada karmaşık genlikler geri gelir")
ok(yakin_genlikler(f(girdi, 3), [s * (0.6 + 0.8j), s * (0.6 - 0.8j)]),
   "Üç uygulama bir uygulamaya eşdeğerdir")
eq(girdi, yedek, "Girdi korunur")
```
:::

::: anlat Sınır
Ders temel kapıları, dolaşıklığı, Bell/CHSH oyununu ve no-cloning'i anlatır; görev Bell durumunu kapılarla kurar ve CHSH kazanma olasılığını kapalı formülle hesaplar, sonlu sayıda ölçümün istatistiği simüle edilmez. CHSH ihlali (2√2 > 2) yerel gizli değişken kuramlarını dışlar, ama ölçüm boşlukları (detection, locality) kapatılmadan deneysel sonuç kesin sayılmaz; boşluksuz testler ancak 2015'te yapılabildi. Dolaşıklık bilgi iletmez (no-signaling); korelasyon ancak sonuçlar klasik kanalla karşılaştırılınca görünür. No-cloning bilinmeyen bir durumun kopyalanmasını yasaklar; bilinen bir durumu yeniden hazırlamak ya da ortogonal durumları ayırt etmek mümkündür.

Kaynaklar: [Clauser vd. 1969 - Proposed Experiment to Test Local Hidden-Variable Theories](https://doi.org/10.1103/PhysRevLett.23.880), [Wootters ve Zurek 1982 - A single quantum cannot be cloned](https://doi.org/10.1038/299802a0), [Hensen vd. 2015 - Experimental loophole-free violation of a Bell inequality using entangled electron spins separated by 1.3 km](https://arxiv.org/abs/1508.05949).
:::

