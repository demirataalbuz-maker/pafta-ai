---
id: kuantum-06
title: Decoherence, Quantum Error Correction (Surface Codes) ve Quantum AI
summary: Neden bugün 1.000 Qubit'lik bilgisayarlar RSA-2048'i kıramıyor? Decoherence (eşevresizlik), Surface Code hata düzeltme, Physical Qubit vs Logical Qubit ayrımı, donanım mimarileri ve Quantum Machine Learning sınırları.
esleme: kuantum-15, kuantum-07
---

::: anlat 1. Büyük Paradoks: "Madem 300 Qubit Evrendeki Atom Sayısını Geçiyor, Bugün 1.000 Qubit'lik Çipler Neden RSA'yı Kıramıyor?"
## Decoherence ve error correction

Physical qubit hataları, mantıksal bir hesabın güvenilir yürütülmesini zorlaştırır. Bu derste decoherence, syndrome ölçümü ve logical/physical qubit ayrımını inceleyeceksin. Verilen cihaz ve kaynak büyüklükleri güncel ürün kataloğu değil; sayısal örnekler varsayım olarak okunmalıdır.

Bir konferansta dinleyicilerin aklını en çok karıştıran çelişki şudur:
1. Bir yandan haberlerde *"IBM 1.121 Qubit'lik çip üretti"*, *"Google Willow çipini tanıttı"* başlıklarını okuyorlar.
2. Diğer yandan *"RSA-2048'i kırmak için 4.000 ideal `Qubit` yeterlidir"* deniyor.
3. Dinleyici haklı olarak soruyor: *"1.000'den 4.000'e ne kaldı ki? O zaman yarın sabah bütün şifreler kırılıyor mu?"*

**Cevap: HAYIR!** Çünkü haberlerde duyduğun `1.000 Qubit`, gürültülü ve kusurlu **`Physical Qubit` (Fiziksel Qubit)** sayısıdır; oysa `Shor's Algorithm` çalıştırmak için gereken `4.000 Qubit`, hatasız **`Logical Qubit` (Mantıksal Qubit)** sayısıdır!

Ve **1 adet hatasız `Logical Qubit`** üretmek için yaklaşık **$500$ ile $1.000$ adet `Physical Qubit`**'i birbirine bağlamak gerekir!
Yani `RSA-2048`'i gerçekten kırmak için $4.000$ değil, **$4.000 \times 1.000 \approx \mathbf{4.000.000}$ (4 Milyon) `Physical Qubit`** gerekir! (Bu kaba hesap, T-kapısı üreten *magic state* fabrikalarını saymaz: Gidney ve Ekerå'nın 2019 tahmini yaklaşık 20 milyon, Gidney'in 2025 tahmini ise bir milyonun altında fiziksel qubit'tir; kuantum-15'teki düşün sorusu bu farkı tartışır.)

### 🎻 Benzetme: Kasırganın Ortasında Sabun Köpüğü Taşımak (`Decoherence`)
Neden fiziksel bir `Qubit` bu kadar çok hata yapar?
- Klasik bir transistörde $0$ demek $0\text{ Volt}$, $1$ demek $5\text{ Volt}$ demektir; voltaj $4.8\text{ V}$'a düşse bile devre onu hala $1$ olarak okur (doğal gürültü bağışıklığı vardır).
- Bir `Qubit` ise mikroskobik bir süperpozisyondur (`Sabun Köpüğü`). Çevredeki tek bir ısı fotonu, manyetik alan dalgalanması veya titreşim `Qubit`'e çarptığı anda çevre `Qubit`'i "ölçmüş" gibi davranır ve süperpozisyon mikrosaniyeler içinde bozulur!
- Bu olguya **`Decoherence` (Eşevresizlik / Kuantum Durumunun Çevreye Sızması)** denir. Bu yüzden süperiletken kuantum işlemciler dış uzaydan bile daha soğuk olan **$15\text{ Millikelvin}$ ($-273.135^\circ\text{C}$ — Mutlak Sıfırın hemen üstü)** sıcaklığındaki altın avizeye benzeyen **`Dilution Refrigerator`** soğutucularında çalıştırılır!

**Kaynak ve sınır:** [IBM Quantum: error correction](https://quantum.cloud.ibm.com/learning/en/courses/foundations-of-quantum-error-correction). Sayısal örnekler eğitim ölçeğindedir; gerçek quantum hardware, standart PQC ürünü veya ağ üzerindeki bir hedef üzerinde kabul testi yapılmaz.
:::

::: anlat 2. Quantum Error Correction (QEC) ve Surface Codes: Bakmadan Hata Nasıl Düzeltilir?
Şimdi bir mühendislik bilmecesi düşün:
Klasik bilgisayarda bir bitin bozulmasına karşı $0 \to 000$ şeklinde 3 kopya alırız (**`Repetition Code`**); biri bozulup $010$ olursa çoğunluk oylamasıyla (`Majority Vote`) hatayı düzeltiriz.

**Ama kuantum bilgisayarda `QEC` yaparken karşımıza iki imkansızlık duvarı çıkar:**
1. **`No-Cloning Theorem`:** Bilinmeyen $|\psi\rangle$ durumunu 3 kez kopyalayamayız!
2. **`Wavefunction Collapse`:** Hata var mı diye `Qubit`'e bakarsak (ölçersek), süperpozisyonu kendi elimizle çökertiriz!

### 🧩 Çözüm: `Syndrome Measurement` ve `Surface Code`
Fizikçi Peter Shor ve Alexei Kitaev bu imkansız görünen sorunu dahi bir yöntemle çözdü:
- Veri `Qubit`'lerinin (**`Data Qubits`**) arasına yardımcı bekçi `Qubit`'ler (**`Ancilla / Syndrome Qubits`**) yerleştirilir.
- Bekçi `Qubit`, veri `Qubit`'lerinin kendisini ($|0\rangle$ mı $|1\rangle$ mi olduğunu) **ASLA ölçmez**; sadece komşu iki veri `Qubit`'inin **birbiriyle aynı mı yoksa ters mi olduğunu (`Parity Check`: $Z_1 Z_2$ ve $X_1 X_2$)** ölçer!
- Tıpkı bir zarfın içindeki gizli mektubu okumadan, sadece zarfın ağırlığını tartarak içine yabancı bir cisim girip girmediğini anlamak gibi!
- **`Threshold Theorem` (Eşik Teoremi):** Eğer tek bir fiziksel kapının hata oranı yaklaşık **%1'in (`Fault-Tolerance Threshold` $p_{\text{th}} \approx 10^{-2}$) altına** indirilebilirse, **`Surface Code`** ızgarasını büyüttükçe mantıksal hata oranı üstel olarak sıfıra yaklaşır! (Google'ın 2024 sonunda **Willow** çipiyle kanıtladığı *"Below Threshold"* dönüm noktası tam olarak budur).

```python
# Surface Code mantıksal hata bastırma yasası: p_logical ~ (p_physical / p_threshold) ^ ((d + 1) / 2)
def mantiksal_hata_orani(p_fiziksel, kod_mesafesi_d, p_esik=0.01):
    ust = (kod_mesafesi_d + 1) // 2
    p_mantiksal = 0.1 * ((p_fiziksel / p_esik) ** ust)
    gereken_fiziksel_qubit = 2 * (kod_mesafesi_d ** 2)
    return {"kod_mesafesi_d": kod_mesafesi_d, "fiziksel_qubit": gereken_fiziksel_qubit, "mantiksal_hata": f"{p_mantiksal:.2e}"}

print("Mesafe d=3  (Küçük Izgara):", mantiksal_hata_orani(0.001, 3))
print("Mesafe d=11 (Orta Izgara) :", mantiksal_hata_orani(0.001, 11))
print("Mesafe d=27 (Kripto-Kırıcı):", mantiksal_hata_orani(0.001, 27))
```
:::

::: anlat 3. NISQ Çağrı vs Fault-Tolerant Çağ ve 4 Donanım Yarışı
Bugün kuantum bilgisayar dünyasında iki çağ ve birbiriyle yarışan **4 farklı fiziksel qubit teknolojisi** vardır:

1. **`NISQ Era` (`Noisy Intermediate-Scale Quantum` — Bugün):** $50 - 1.500$ fiziksel `Qubit` içeren, hata düzeltmesi tam olmayan, sadece kısa devreleri çalıştırabilen dönem.
2. **`FTQC Era` (`Fault-Tolerant Quantum Computing` — Hedef):** Milyonlarca fiziksel `Qubit` üzerinde binlerce kusursuz `Logical Qubit` koşturan hata-toleranslı dönem.

### 🏎️ Qubit Üretmenin 4 Rakip Teknolojisi
| Donanım Mimarisi | Qubit Olarak Ne Kullanılır? | Avantajı | Dezavantajı | Öncü Şirketler |
| :--- | :--- | :--- | :--- | :--- |
| **`Superconducting Qubits`** *(Süperiletken)* | `Josephson Junction` devrelerinde akan makroskopik kuantum akımı | Çok hızlı kapı süresi ($\sim 20\text{ ns}$), mikroçip fabrikalarında üretilebilir | $15\text{ mK}$ aşırı soğutma ister, `Coherence` süresi kısadır ($\sim 100\ \mu\text{s}$) | Google, IBM, Rigetti |
| **`Trapped Ions`** *(İyon Tuzakları)* | Elektromanyetik alanda havada asılı tutulan tekil atomlar ($^{171}\text{Yb}^+$) | Çok uzun `Coherence` süresi (saniyeler/dakikalar) ve %99.9+ kapı doğruluğu | Kapı işlemleri yavaştır ($\mu\text{s} - \text{ms}$), milyon iyonu tek çipte ölçeklemek zordur | IonQ, Quantinuum |
| **`Neutral Atoms`** *(Nötr Atomlar)* | Lazer cımbızlarla (`Optical Tweezers`) tutulan Rubidyum/Stronsiyum atomları | Binlerce atomu 2D/3D dizilerde kolayca ölçekleme ve esnek taşıma | Lazer kontrol ve okuma hızı darboğazları | QuEra, Pasqal, Atom Computing |
| **`Photonic / Topological`** *(Fotonik & Topolojik)* | Işık fotonları veya `Majorana Zero Modes` yarı-parçacıkları | Oda sıcaklığında ağ kurabilme (Fotonik) / Donanım seviyesinde doğal hata koruması (Topolojik) | Fotonları birbiriyle etkileştirmek veya Majorana durumunu üretmek çok zordur | PsiQuantum, Xanadu, Microsoft |
:::

::: anlat 4. Quantum AI (Quantum Machine Learning - QML): Gerçekler ve Efsaneler
Şu teknik ayrımı inceleyelim:

Konferansın son ve en çarpıcı sorusu:
*"Kuantum bilgisayarlar ile Yapay Zeka birleştiğinde (`Quantum AI`) ne olacak? Kuantum bilgisayarlar ChatGPT/Opus gibi Büyük Dil Modellerini (`LLM`) milyon kat hızlandıracak mı?"*

İşte entelektüel dürüstlüğün ve derin uzmanlığın parlayacağı yer burasıdır:

### 1. Büyük Klasik Veriyi Kuantum Bilgisayara Yükleme Darboğazı (`The QRAM Input Bottleneck`)
- Bir `LLM` eğitmek için $15\text{ Trilyon Token}$ klasik metni çipe okutman gerekir.
- Klasik terabaytlarca veriyi kuantum süperpozisyonuna (`Amplitude Encoding`) dönüştürüp yüklemek için varsayımsal **`QRAM` (`Quantum RAM`)** gerekir ve bu yükleme işlemi zaten $O(N)$ sürer — yani kuantum algoritmanın sağlayacağı hızlanmayı daha veriyi yüklerken kaybedersin!
- Bu yüzden **metin, görüntü ve ses gibi devasa klasik veriler üzerinde çalışan `LLM`'ler için klasik GPU/TPU kümeleri ana motor olmaya devam edecektir.**

### 2. Peki `Quantum AI` Asıl Yaklaşımı Nerede Yapacak? (`Quantum Data & Chemistry`)
Kuantum bilgisayarların yapay zekayı uçuracağı yer "sohbet botları" değil, **verinin kendisinin kuantum mekaniksel olduğu (`Quantum-Native Problems`)** alanlardır:
1. **`VQE (Variational Quantum Eigensolver)` & İlaç/Malzeme Keşfi:** Klasik yapay zeka (`AlphaFold` vb.) moleküllerin şeklini tahmin eder ama ağır geçiş metallerinin elektron korelasyonlarını (örneğin gübre üretiminde dünyanın enerjisinin %2'sini harcayan Haber-Bosch sürecini oda sıcaklığında yapan **`Nitrogenase / FeMo-co`** enzimini veya yeni nesil pil/süperiletken kimyasını) tam simüle edemez.
2. **Kuantum Bilgisayar + Klasik AI Hibrit Döngüsü (`Quantum-Centric Supercomputing`):**
   - **Kuantum İşlemci (`QPU`):** Molekülün veya malzemenin gerçek kuantum temel enerji durumunu (`Ground State`) simüle edip kesin eğitim verisi üretir.
   - **Klasik `Frontier AI` (`GPU`):** Kuantum işlemciden gelen bu kusursuz fiziksel verileri öğrenerek milyarlarca yeni ilaç ve süperiletken malzemeyi saniyeler içinde tasarlar (ve ayrıca kuantum bilgisayarın `Surface Code` hata düzeltme sendromlarını gerçek zamanlı çözer — Google DeepMind **`AlphaQubit`**!).

Şu soruyu düşün: *"Kuantum bilgisayarlar klasik yapay zekanın yerini almayacak; klasik yapay zeka insan dilinin ve mantığının motoru olurken, kuantum bilgisayarlar doğanın en derin atomik yasalarının simülatörü olacak. İkisi birleştiğinde (`AI + Quantum`), insanlık maddeyi ve zekayı atom seviyesinden itibaren programlayabilir hale gelecek."*

> **Konferans Kapanış Cümlesi:** *"Kuantum bilgisayarlar klasik yapay zekanın yerini almayacak; klasik yapay zeka insan dilinin ve mantığının motoru olurken, kuantum bilgisayarlar doğanın en derin atomik yasalarının simülatörü olacak. İkisi birleştiğinde (`AI + Quantum`), insanlık maddeyi ve zekayı atom seviyesinden itibaren programlayabilir hale gelecek."*
:::

::: tahmin Physical Qubit vs Logical Qubit Hesabı
Bir kuantum algoritması (`Shor's Algorithm`) $2.048$ bitlik bir anahtarı kırmak için $4.000$ hatasız `Logical Qubit` gerektiriyor. Kullanılan `Surface Code` mimarisinde her $1$ `Logical Qubit` için $1.250$ gürültülü `Physical Qubit` gerekiyorsa, toplam kaç milyon fiziksel `Qubit` gerekir?

```python
logical_qubits = 4000
oran = 1250
toplam_physical = logical_qubits * oran
print(f"Gereken Fiziksel Qubit: {toplam_physical / 1_000_000:.1f} Milyon")
```

???

```cikti
Gereken Fiziksel Qubit: 5.0 Milyon
```
Her bir hatasız `Logical Qubit`'i `Decoherence` gürültüsünden korumak için $1.250$ fiziksel `Qubit` (`Surface Code` ızgarası) gerektiğinden, $4.000 \times 1.250 = 5.000.000$ ($5.0\text{ Milyon}$) `Physical Qubit` gerekir.
:::

::: gorev 1 · 3 Qubit'lik Bit-Flip Kodu: Sendromla Hata Bulma
En basit kuantum hata düzeltme kodu bir mantıksal qubit'i üç fiziksel qubit'e yayar: $\alpha|0\rangle + \beta|1\rangle \to \alpha|000\rangle + \beta|111\rangle$. İki **parite ölçümü** ($Z_0Z_1$ ve $Z_1Z_2$) hangi qubit'in çevrildiğini söyler ama $\alpha$, $\beta$ hakkında hiçbir şey öğrenmez, bu yüzden süperpozisyon bozulmaz. `bit_flip_kodu(alfa, beta, hata_qubit)` işlevini yaz.

**Gösterim:** 8 genlik, indeks $= 4q_0 + 2q_1 + q_2$ (qubit 0 en soldaki). Qubit $k$'ye `X` uygulamak indeksin $2^{2-k}$ bitini çevirir.

**Adımlar:**
1. `"kodlanmis"`: indeks 0'da $\alpha$, indeks 7'de $\beta$, diğerleri 0.
2. `"hatali"`: `hata_qubit` `None` değilse o qubit'e `X` uygula.
3. `"sendrom"`: genliği sıfır olmayan herhangi bir taban durumundan $[q_0 \oplus q_1,\ q_1 \oplus q_2]$ (iki bileşenin paritesi her zaman aynıdır).
4. Çözümleme: `[0,0]` → hata yok (`None`), `[1,0]` → qubit 0, `[1,1]` → qubit 1, `[0,1]` → qubit 2. `"duzeltilen_qubit"` ve `"duzeltilmis"` (o qubit'e yeniden `X`).
5. `"kurtarildi_mi"`: düzeltilmiş vektör kodlanmış vektöre eşit mi.

Vektörleri `round(·, 6)` ile yuvarla. `alfa`, `beta` gerçek sayı olmalı, $|\alpha^2 + \beta^2 - 1| \le 10^{-9}$ sağlanmalı; `hata_qubit` `None` ya da 0–2 arası `int` olmalı (`bool` değil). Değilse `ValueError`.

```starter
def bit_flip_kodu(alfa, beta, hata_qubit):
    # KUSURLU BAŞLANGIÇ: kodlamıyor, sendromu ölçmüyor
    v = [alfa, beta, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    return {"kodlanmis": v, "hatali": v, "sendrom": [0, 0], "duzeltilen_qubit": None, "duzeltilmis": v, "kurtarildi_mi": True}

print(bit_flip_kodu(0.6, 0.8, 1))
```

```test
fn = need("bit_flip_kodu")
r = fn(0.6, 0.8, 1)
eq(r["kodlanmis"], [0.6, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.8], "α|000⟩ + β|111⟩")
eq(r["hatali"], [0.0, 0.0, 0.6, 0.0, 0.0, 0.8, 0.0, 0.0], "qubit 1 çevrilince 000→010 (2), 111→101 (5)")
eq(r["sendrom"], [1, 1], "q0⊕q1 = 1, q1⊕q2 = 1")
eq(r["duzeltilen_qubit"], 1, "sendrom [1,1] → qubit 1")
eq(r["kurtarildi_mi"], True, "tek hata düzeltilir")
r0 = fn(0.6, 0.8, 0)
eq(r0["hatali"], [0.0, 0.0, 0.0, 0.8, 0.6, 0.0, 0.0, 0.0], "qubit 0: 000→100 (4), 111→011 (3)")
eq(r0["sendrom"], [1, 0], "yalnız ilk parite bozulur")
r2 = fn(0.6, 0.8, 2)
eq(r2["sendrom"], [0, 1], "qubit 2: yalnız ikinci parite")
eq(r2["duzeltilen_qubit"], 2, "sendrom [0,1] → qubit 2")
rn = fn(0.6, 0.8, None)
eq(rn["sendrom"], [0, 0], "hata yoksa sendrom sıfır")
eq(rn["duzeltilen_qubit"], None, "düzeltme yok")
eq(fn(0.0, 1.0, 0)["sendrom"], [1, 0], "α = 0: yalnız |111⟩ bileşeninden okunur")
eq(fn(1.0, 0.0, 2)["duzeltilmis"], [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], "|000⟩'a geri döner")
raises(ValueError, fn, 0.6, 0.6, 0)
raises(ValueError, fn, 0.6, 0.8, 3)
raises(ValueError, fn, 0.6, 0.8, True)
raises(ValueError, fn, "0.6", 0.8, 0)
eq(fn(1.0, 0.0, 0)["sendrom"], [1, 0], "β = 0: yalnız |100⟩ bileşeni okunur")
eq(fn(0.0, 1.0, 1)["sendrom"], [1, 1], "|101⟩")
eq(fn(0.0, 1.0, 2)["sendrom"], [0, 1], "|110⟩")
eq(fn(0.0, 1.0, None)["sendrom"], [0, 0], "|111⟩ hatasız durumda indeks 7 okunur")
eq(fn(1/3, (8**0.5)/3, None)["kodlanmis"][0], 0.333333, "6 basamak yuvarlama")
eq(fn((1.0 + 6e-10)**0.5, 0.0, None)["kurtarildi_mi"], True, "1e-9 norm toleransı içi")
raises(ValueError, fn, (1.0 + 1.6e-9)**0.5, 0.0, None)
raises(ValueError, fn, True, 0.0, 0)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef bit_flip_kodu(alfa, beta, hata_qubit):\n    for v in (alfa, beta):\n        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):\n            raise ValueError('alfa ve beta gerçek sayı olmalı')\n    if abs(alfa * alfa + beta * beta - 1.0) > 1e-09:\n        raise ValueError('durum normalize olmalı')\n    if hata_qubit is not None and (isinstance(hata_qubit, bool) or not isinstance(hata_qubit, int) or (not 0 <= hata_qubit <= 2)):\n        raise ValueError('hata_qubit None ya da 0-2 arası tam sayı olmalı')\n\n    def x_uygula(v, k):\n        maske = 1 << 2 - k\n        return [v[i ^ maske] for i in range(8)]\n    kod = [0.0] * 8\n    kod[0], kod[7] = (float(alfa), float(beta))\n    hatali = x_uygula(kod, hata_qubit) if hata_qubit is not None else list(kod)\n    i = next((j for j in range(8) if abs(hatali[j]) > 1e-12))\n    q0, q1, q2 = (i >> 2 & 1, i >> 1 & 1, i & 1)\n    sendrom = [q0 ^ q1, q1 ^ q2]\n    duzeltilen = {(0, 0): None, (1, 0): 0, (1, 1): 1, (0, 1): 2}[tuple(sendrom)]\n    duz = x_uygula(hatali, duzeltilen) if duzeltilen is not None else list(hatali)\n    yuv = lambda v: [round(x, 6) for x in v]\n    return {'kodlanmis': yuv(kod), 'hatali': yuv(hatali), 'sendrom': sendrom, 'duzeltilen_qubit': duzeltilen, 'duzeltilmis': yuv(duz), 'kurtarildi_mi': yuv(duz) == yuv(kod)}", 'referans', 'exec'), _REF)
_t, _g = _ff(bit_flip_kodu, _REF['bit_flip_kodu'], (0.6, 0.8, 1), tohum=2291, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (bit_flip_kodu): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def bit_flip_kodu(alfa, beta, hata_qubit):
    for v in (alfa, beta):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError("alfa ve beta gerçek sayı olmalı")
    if abs(alfa * alfa + beta * beta - 1.0) > 1e-9:
        raise ValueError("durum normalize olmalı")
    if hata_qubit is not None and (isinstance(hata_qubit, bool) or not isinstance(hata_qubit, int) or not 0 <= hata_qubit <= 2):
        raise ValueError("hata_qubit None ya da 0-2 arası tam sayı olmalı")

    def x_uygula(v, k):
        maske = 1 << (2 - k)
        return [v[i ^ maske] for i in range(8)]

    kod = [0.0] * 8
    kod[0], kod[7] = float(alfa), float(beta)
    hatali = x_uygula(kod, hata_qubit) if hata_qubit is not None else list(kod)
    i = next(j for j in range(8) if abs(hatali[j]) > 1e-12)
    q0, q1, q2 = (i >> 2) & 1, (i >> 1) & 1, i & 1
    sendrom = [q0 ^ q1, q1 ^ q2]
    duzeltilen = {(0, 0): None, (1, 0): 0, (1, 1): 1, (0, 1): 2}[tuple(sendrom)]
    duz = x_uygula(hatali, duzeltilen) if duzeltilen is not None else list(hatali)
    yuv = lambda v: [round(x, 6) for x in v]  # noqa: E731
    return {"kodlanmis": yuv(kod), "hatali": yuv(hatali), "sendrom": sendrom, "duzeltilen_qubit": duzeltilen,
            "duzeltilmis": yuv(duz), "kurtarildi_mi": yuv(duz) == yuv(kod)}
```

```hint
`X` permütasyondur: yeni vektörün i. öğesi eski vektörün `i ^ maske` öğesidir. Sendromu ilk sıfır olmayan genliğin indeksinden oku.
```
:::

::: gorev 2 · Üç qubit kodunun mantıksal hata olasılığını hesapla
Her fiziksel qubit bağımsız olarak `p` olasılıkla çevrilsin. Kusursuz sendrom ölçümü ve çoğunluk kararı varsay. Mantıksal bit, en az iki fiziksel bit çevrildiğinde hatalı okunur. `tekrar_kodu_hatasi(p)` işlevi tam iki çevrilmenin üç konum seçimini ve üç çevrilme durumunu toplayıp altı ondalık basamağa yuvarlasın. `p` 0 ile 1 arasında sonlu bir `int` veya `float` olmalı. `bool` ve geçersiz girdilerde `ValueError` üret.

```starter
def tekrar_kodu_hatasi(p):
    # Yalnız üç qubit birden çevrilirse hata olacağını varsayıyor.
    return round(p**3, 6)
```
```solution
def tekrar_kodu_hatasi(p):
    if type(p) not in (int, float) or not 0 <= p <= 1:
        raise ValueError("p 0 ile 1 arasında sayısal olmalı")
    return round(3 * p**2 * (1 - p) + p**3, 6)
```
```test
f = need("tekrar_kodu_hatasi")
eq(f(0), 0.0, "Çevrilme yok")
eq(f(1), 1.0, "Her qubit çevrilir")
eq(f(0.1), 0.028, "Tam iki çevrilme 0.027 ve tam üç çevrilme 0.001")
eq(f(0.5), 0.5, "Sekiz desenin dördü hatalı çoğunluk verir")
eq(f(0.9), 0.972, "Yüksek fiziksel hata oranında çoğunluk kodu hatayı artırır")
eq(f(0.123), 0.041665, "Sonuç altı basamakla raporlanır")
for p in (-0.01, 1.01, True, "0.1", float("nan"), float("inf")):
    raises(ValueError, f, p)
```
:::

::: anlat Sınır
Ders decoherence'ı, sendrom ölçümünü ve surface code'u, NISQ ile fault-tolerant ayrımını ve quantum AI'daki veri yükleme darboğazını anlatır; görev 3 qubit'lik bit-flip kodunu tek bir X hatası için simüle eder; faz hataları, birden çok hata (iki çevrilmiş qubit yanlış düzeltilir) ve gerçek gürültü modeli yoktur. Surface code yalnız fiziksel hata oranı eşiğin altındaysa mantıksal hatayı düşürür; tek bir mantıksal qubit için yüzlerce ile binlerce fiziksel qubit gerekir. Eşik altı çalışma 2024'te küçük kod mesafelerinde gösterildi; büyük ölçekli fault-tolerant hesaplama henüz yoktur. Quantum ML hızlanma iddialarının çoğu QRAM gibi henüz olmayan veri yükleme donanımını varsayar; bazı hızlanmalar klasik 'dequantization' algoritmalarıyla ortadan kalkmıştır.

Kaynaklar: [Fowler vd. 2012 - Surface codes: Towards practical large-scale quantum computation](https://arxiv.org/abs/1208.0928), [Google Quantum AI 2024 - Quantum error correction below the surface code threshold](https://arxiv.org/abs/2408.13687), [Biamonte vd. 2017 - Quantum Machine Learning](https://arxiv.org/abs/1611.09347), [Aaronson 2015 - Read the fine print](https://doi.org/10.1038/nphys3272).
:::

