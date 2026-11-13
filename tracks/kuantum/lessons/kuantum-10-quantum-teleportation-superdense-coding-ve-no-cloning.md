---
id: kuantum-10
title: "Quantum Teleportation, Superdense Coding ve No-Cloning Güvenlik Kanıtı"
summary: "Bilinmeyen bir Qubit durumunu No-Cloning teoremini ihlal etmeden Bell Pair ve 2 klasik bitle ışınla (Quantum Teleportation); tersine tek bir dolaşık Qubit göndererek 2 klasik bit taşıyan Superdense Coding protokolünü kodla."
track: kuantum
order: 10
duration_minutes: 35
difficulty: orta
xp: 280
prerequisites: [kuantum-09]
tags: [quantum-teleportation, superdense-coding, no-cloning, bell-measurement, pauli-correction, quantum-internet]
esleme: kuantum-09, kuantum-11
---

::: anlat 1. Quantum Teleportation (Kuantum Işınlama, Bennett vd. 1993)
## Teleportation ve superdense coding

Quantum teleportation, önceden paylaşılan entanglement ve classical iletişimle bir quantum state aktarır. Madde ışınlama veya ışıktan hızlı mesajlaşma değildir. Bu derste ölçüm bitlerine bağlı Pauli correction işlemini ve superdense coding çözmesini hesaplayacaksın.

Konferanslarda en çok yanlış anlaşılan başlıklardan biri **"Kuantum Işınlama (`Quantum Teleportation`)"** kavramıdır:
> *"Bilim insanları bir fotonu laboratuvardan uyduya ışınladı!"* haberini duyanlar, *Star Trek*'teki gibi maddenin bir yerden yok olup başka yerde belirdiğini veya ışıktan hızlı (`Faster-Than-Light`) mesaj gönderildiğini sanır.

Gerçekte **`Quantum Teleportation`** nedir?
Alice'in elinde kendisinin bile $\alpha$ ve $\beta$ katsayılarını bilmediği çok kıymetli bir kuantum durumu vardır:
$$|\psi\rangle_Q = \alpha|0\rangle + \beta|1\rangle$$
Alice bu durumu uzaktaki Bob'a ulaştırmak istiyor, ancak önünde **3 imkansızlık duvarı** var:
1. Alice $|\psi\rangle_Q$'yu ölçüp $\alpha, \beta$'yı öğrenmeye kalkarsa **`Wavefunction Collapse`** yüzünden durum tek bir klasik bite ($0$ veya $1$) çöker ve bilgi yok olur!
2. Alice $|\psi\rangle_Q$'nun yedeğini alıp göndermeye kalkarsa **`No-Cloning Theorem`** buna izin vermez!
3. $\alpha$ ve $\beta$ sonsuz duyarlıklı karmaşık sayılar olduğu için klasik kanalla tam tarif etmek sonsuz bit gerektirir!

### 🌌 Çözüm: 1 `Bell Pair` + 2 Klasik Bit = Kusursuz Kuantum Işınlama!
Alice ve Bob daha önceden paylaşılmış bir dolaşık **`Bell Pair`** ($|\Phi^+\rangle_{AB} = \frac{|00\rangle + |11\rangle}{\sqrt{2}}$) tutsunlar ($A$ Qubit'i Alice'te, $B$ Qubit'i Bob'da).

```
Alice: |\psi⟩_Q ───●───[ H ]───(Ölç: m0)═══════════════╗ (2 Klasik Bit
                   │                                   ║  Işık Hızıyla)
Alice: |\Phi+⟩_A ──⊕───────────(Ölç: m1)═══════╗       ║
                                               ▼       ▼
Bob:   |\Phi+⟩_B ────────────────────────────[ X^m1 ][ Z^m0 ] ──► |\psi⟩ = \alpha|0⟩ + \beta|1⟩
```

Üç Qubit'in başlangıçtaki birleşik durumu $|\psi\rangle_Q \otimes |\Phi^+\rangle_{AB}$ üzerine Alice kendi elindeki iki Qubit'e ($\text{CNOT}_{Q\to A}$ ve ardından $H_Q$) uyguladığında, 3-Qubit denklemi cebirsel olarak tam 4 parçaya ayrılır:

$$|\Psi_{\text{son}}\rangle = \frac{1}{2}\Big[
  |00\rangle_{QA}(\alpha|0\rangle + \beta|1\rangle)_B
+ |01\rangle_{QA}(\alpha|1\rangle + \beta|0\rangle)_B
+ |10\rangle_{QA}(\alpha|0\rangle - \beta|1\rangle)_B
+ |11\rangle_{QA}(\alpha|1\rangle - \beta|0\rangle)_B
\Big]$$

Şu denklemin güzelliğine bak! Alice kendi iki Qubit'ini ölçtüğünde $(m_0, m_1) \in \{00, 01, 10, 11\}$ sonuçlarından birini alır ve Bob'un elindeki Qubit **anında** o satırdaki duruma çöker:

| Alice'in Ölçümü $(m_0, m_1)$ | Bob'un Qubit'inin Çöktüğü Durum ($|\psi_{\text{Bob}}\rangle$) | Bob'un Uygulayacağı Pauli Düzeltmesi ($Z^{m_0} X^{m_1}$) | Düzeltme Sonrası Bob'un Durumu |
| :---: | :---: | :---: | :---: |
| **`(0, 0)`** | $\alpha|0\rangle + \beta|1\rangle$ | $I$ *(Hiçbir şey yapma)* | $\alpha|0\rangle + \beta|1\rangle$ |
| **`(0, 1)`** | $\alpha|1\rangle + \beta|0\rangle$ *(Bit-Flip olmuş)* | **`X Gate`** *(0 ve 1'i yer değiştir)* | $\alpha|0\rangle + \beta|1\rangle$ |
| **`(1, 0)`** | $\alpha|0\rangle - \beta|1\rangle$ *(Phase-Flip olmuş)* | **`Z Gate`** *($|1\rangle$ işaretini çevir)* | $\alpha|0\rangle + \beta|1\rangle$ |
| **`(1, 1)`** | $\alpha|1\rangle - \beta|0\rangle$ *(İkisi de olmuş)* | **`Önce X, Sonra Z` ($Z \cdot X$)** | $\alpha|0\rangle + \beta|1\rangle$ |

### 🛡️ İki Kritik Güvenlik ve Fizik Kanıtı:
1. **`No-Cloning Theorem` İhlal Edildi mi?** Hayır! Alice $(m_0, m_1)$ ölçümünü yaptığı anda kendi elindeki $|\psi\rangle_Q$ durumu tamamen çökmüş ve yok olmuştur. Evrende aynı anda iki kopya asla var olmamıştır!
2. **Neden Işıktan Hızlı (`Faster-Than-Light`) Değildir?** Alice'in ölçüm sonucu $(m_0, m_1)$ %25-%25-%25-%25 tamamen rastgeledir. Alice telefon/fiber optik kabloyla (ışık hızıyla) bu **2 klasik biti** Bob'a gönderene kadar Bob elindeki Qubit'e hangi düzeltmeyi ($I, X, Z, ZX$) uygulayacağını bilemez; o 2 bit gelmeden Bob'un Qubit'i $\rho_B = \frac{1}{2}I$ (saf beyaz gürültü) halindedir!

```python
def teleport_simulasyonu(alpha, beta, m0, m1):
    # Alice'in (m0, m1) ölçümünden hemen sonra Bob'un Qubit'indeki çökmüş durum:
    if (m0, m1) == (0, 0):
        bob = [alpha, beta]
    elif (m0, m1) == (0, 1):
        bob = [beta, alpha]
    elif (m0, m1) == (1, 0):
        bob = [alpha, -beta]
    else:
        bob = [-beta, alpha]
    # Bob m1==1 ise X, m0==1 ise Z uygular:
    if m1 == 1:
        bob = [bob[1], bob[0]]
    if m0 == 1:
        bob = [bob[0], -bob[1]]
    return [round(v, 4) for v in bob]

for m0 in (0, 1):
    for m1 in (0, 1):
        print(f"Ölçüm=({m0},{m1}) -> Bob Düzeltme Sonrası:", teleport_simulasyonu(0.6, 0.8, m0, m1))
```

**Kaynak ve sınır:** [IBM Quantum: temel quantum information](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information). Sayısal örnekler eğitim ölçeğindedir; gerçek quantum hardware, standart PQC ürünü veya ağ üzerindeki bir hedef üzerinde kabul testi yapılmaz.
:::

::: anlat 2. Superdense Coding (Süperyoğun Kodlama, Bennett & Wiesner 1992)
Şimdi madalyonun tam tersini çevirelim!
- **`Quantum Teleportation`:** **2 klasik bit** göndererek **1 Qubit** durumu aktardık.
- **`Superdense Coding`:** Fiziksel olarak **yalnızca 1 Qubit** göndererek **2 klasik bit (`00`, `01`, `10`, `11`)** bilgi aktarabilir miyiz?

Klasik bilgi teorisine (ve **Holevo's Bound** teoremine) göre entanglement yoksa tek bir Qubit en fazla **1 klasik bit** bilgi taşıyabilir. Ancak Alice ve Bob önceden bir **`Bell Pair` ($|\Phi^+\rangle_{AB}$)** paylaşıyorsa, Alice **Bob'un Qubit'ine hiç dokunmadan**, sadece kendi elindeki tek Qubit'e 4 Pauli kapısından birini uygulayarak 4 dik (`Orthogonal`) Bell durumundan birini seçebilir:

| Alice'in Göndermek İstediği 2 Bit | Alice'in Kendi Qubit'ine Uyguladığı Kapı | Oluşan Dolaşık Bell Durumu | Bob'un `CNOT` + `H` Sonrası Ölçtüğü 2 Bit |
| :---: | :---: | :---: | :---: |
| **`"00"`** | **`I` (Birim)** | $|\Phi^+\rangle = \frac{\|00\rangle + \|11\rangle}{\sqrt{2}}$ | **`"00"`** |
| **`"01"`** | **`X` (`Bit-Flip`)** | $|\Psi^+\rangle = \frac{\|10\rangle + \|01\rangle}{\sqrt{2}}$ | **`"01"`** |
| **`"10"`** | **`Z` (`Phase-Flip`)** | $|\Phi^-\rangle = \frac{\|00\rangle - \|11\rangle}{\sqrt{2}}$ | **`"10"`** |
| **`"11"`** | **`Z · X` (Önce $X$, sonra $Z$)** | $|\Psi^-\rangle = \frac{\|01\rangle - \|10\rangle}{\sqrt{2}}$ | **`"11"`** |

Alice kendi Qubit'ini Bob'a gönderdiğinde Bob elindeki iki Qubit'e **Bell Çözücü (`CNOT` ardından `Hadamard`)** uygular ve deterministik (%100 kesinlikle) Alice'in 2 bitlik mesajını okur!
> **Kuantum Hacker Notu:** Eğer kuantum kanalda bir saldırgan (veya gürültü) Alice'in gönderdiği Qubit'e fazladan bir Pauli hatası ($X$ veya $Z$) uygularsa, gönderilen 2 bitlik mesaj tam olarak ilgili bitte (`Bit-Flip` $\to$ 2. bit, `Phase-Flip` $\to$ 1. bit) ters döner!
:::

::: tahmin Teleportasyon ve Superdense Coding Simetrisi
Alice `Superdense Coding` ile `"10"` mesajını göndermek için kendi Qubit'ine `Z` kapısı uyguluyor. Fakat fiber optik kabloda oluşan bir gürültü, yoldaki Qubit'e fazladan bir `X` kapısı (`Bit-Flip`) etkisi yapıyor. Bob `Bell Measurement` yaptığında ekranda hangi 2 biti okur?

```python
# "10" mesajı Z kapısıdır; yolda X gürültüsü eklenirse toplam etki X*Z (11 etkisi) olur
alice_mesaj = "10"
gurultu = "X"
# Z birinci biti (m0=1), X ikinci biti (m1=1) tetikler:
okunan = "11" if (alice_mesaj == "10" and gurultu == "X") else alice_mesaj
print("Alice Gönderdi:", alice_mesaj, "| Gürültü:", gurultu, "-> Bob Okudu:", okunan)
```

???

```cikti
Alice Gönderdi: 10 | Gürültü: X -> Bob Okudu: 11
```
`Superdense Coding`'de birinci bit ($b_0$) `Z` (`Phase-Flip`), ikinci bit ($b_1$) ise `X` (`Bit-Flip`) kanalında taşınır. Alice `"10"` için `Z` uyguladığında, yoldaki `X` gürültüsü ikinci biti de çevirir ve Bob `"11"` okur!
:::

::: gorev 1 · Quantum Teleportation Protokolü: Bell Ölçümü ve Bob'un Pauli (X/Z) Düzeltmesi
`teleportasyon_duzelt(alpha, beta, olcum_m0, olcum_m1)` işlevini yaz:
- Alice'in ışınlamak istediği $|\psi\rangle = \alpha|0\rangle + \beta|1\rangle$ durumu ve Alice'in Bell ölçümü sonuçları `olcum_m0`, `olcum_m1` ($\in \{0, 1\}$) veriliyor.
- Önce Alice'in ölçümü sonucunda Bob'un Qubit'inin çöktüğü düzeltme-öncesi durumu `cokmus_durum` olarak hesapla:
  - `(0, 0)` $\to [\alpha, \beta]$
  - `(0, 1)` $\to [\beta, \alpha]$
  - `(1, 0)` $\to [\alpha, -\beta]$
  - `(1, 1)` $\to [-\beta, \alpha]$
- Ardından Bob'un uygulaması gereken düzeltme kapısı adını (`"I"`, `"X"`, `"Z"` veya `"ZX"`), düzeltme sonrası `kurtarilan_durum` vektörünü (`[round(v, 6) ...]`) ve `basarili_mi` (`kurtarilan_durum` ile `[round(alpha, 6), round(beta, 6)]` eşleşiyor mu) alanlarını sözlükte döndür.

```starter
# KUSURLU BAŞLANGIÇ KODU: 4 ölçüm durumu için çökmüş durumu ve Bob'un düzeltmesini tamamla.
def teleportasyon_duzelt(alpha, beta, olcum_m0, olcum_m1):
    return {
        "cokmus_durum": [round(alpha, 6), round(beta, 6)],
        "duzeltme_kapisi": "I",
        "kurtarilan_durum": [round(alpha, 6), round(beta, 6)],
        "basarili_mi": False
    }

print(teleportasyon_duzelt(0.6, 0.8, 1, 1))
```
```test
f = need("teleportasyon_duzelt")
r00 = f(0.6, -0.8, 0, 0)
ok(r00["cokmus_durum"] == [0.6, -0.8] and r00["duzeltme_kapisi"] == "I" and r00["kurtarilan_durum"] == [0.6, -0.8] and r00["basarili_mi"] is True, "(0,0) ölçümünde birim kapı (I) ile durum korundu")

r01 = f(0.6, -0.8, 0, 1)
ok(r01["cokmus_durum"] == [-0.8, 0.6] and r01["duzeltme_kapisi"] == "X" and r01["kurtarilan_durum"] == [0.6, -0.8] and r01["basarili_mi"] is True, "(0,1) ölçümünde X kapısı ile Bit-Flip düzeltildi")

r10 = f(0.6, -0.8, 1, 0)
ok(r10["cokmus_durum"] == [0.6, 0.8] and r10["duzeltme_kapisi"] == "Z" and r10["kurtarilan_durum"] == [0.6, -0.8] and r10["basarili_mi"] is True, "(1,0) ölçümünde Z kapısı ile Phase-Flip düzeltildi")

r11 = f(0.6, -0.8, 1, 1)
ok(r11["cokmus_durum"] == [0.8, 0.6] and r11["duzeltme_kapisi"] == "ZX" and r11["kurtarilan_durum"] == [0.6, -0.8] and r11["basarili_mi"] is True, "(1,1) ölçümünde ZX kapısı ile hem Bit hem Phase Flip düzeltildi")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def teleportasyon_duzelt(alpha, beta, olcum_m0, olcum_m1):\n    if (olcum_m0, olcum_m1) == (0, 0):\n        cokmus = [alpha, beta]\n        kapi = 'I'\n    elif (olcum_m0, olcum_m1) == (0, 1):\n        cokmus = [beta, alpha]\n        kapi = 'X'\n    elif (olcum_m0, olcum_m1) == (1, 0):\n        cokmus = [alpha, -beta]\n        kapi = 'Z'\n    else:\n        cokmus = [-beta, alpha]\n        kapi = 'ZX'\n    kurt = list(cokmus)\n    if olcum_m1 == 1:\n        kurt = [kurt[1], kurt[0]]\n    if olcum_m0 == 1:\n        kurt = [kurt[0], -kurt[1]]\n    cokmus_r = [round(v, 6) for v in cokmus]\n    kurt_r = [round(v, 6) for v in kurt]\n    hedef_r = [round(alpha, 6), round(beta, 6)]\n    return {'cokmus_durum': cokmus_r, 'duzeltme_kapisi': kapi, 'kurtarilan_durum': kurt_r, 'basarili_mi': bool(kurt_r == hedef_r)}", 'referans', 'exec'), _REF)
_t, _g = _ff(teleportasyon_duzelt, _REF['teleportasyon_duzelt'], (0.6, 0.8, 1, 1), tohum=3107, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (teleportasyon_duzelt): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
def teleportasyon_duzelt(alpha, beta, olcum_m0, olcum_m1):
    if (olcum_m0, olcum_m1) == (0, 0):
        cokmus = [alpha, beta]
        kapi = "I"
    elif (olcum_m0, olcum_m1) == (0, 1):
        cokmus = [beta, alpha]
        kapi = "X"
    elif (olcum_m0, olcum_m1) == (1, 0):
        cokmus = [alpha, -beta]
        kapi = "Z"
    else:
        cokmus = [-beta, alpha]
        kapi = "ZX"
    kurt = list(cokmus)
    if olcum_m1 == 1:
        kurt = [kurt[1], kurt[0]]
    if olcum_m0 == 1:
        kurt = [kurt[0], -kurt[1]]
    cokmus_r = [round(v, 6) for v in cokmus]
    kurt_r = [round(v, 6) for v in kurt]
    hedef_r = [round(alpha, 6), round(beta, 6)]
    return {
        "cokmus_durum": cokmus_r,
        "duzeltme_kapisi": kapi,
        "kurtarilan_durum": kurt_r,
        "basarili_mi": bool(kurt_r == hedef_r)
    }

print(teleportasyon_duzelt(0.6, 0.8, 1, 1))
```
```hint
`olcum_m1 == 1` ise elemanların yerini değiştir (`X`), ardından `olcum_m0 == 1` ise ikinci elemanın işaretini ters çevir (`Z`).
```
:::

::: gorev 2 · Superdense Coding: 2 Klasik Biti 1 Qubit Kapısıyla Kodlama ve Bell Çözme
`superdense_kodla_coz(mesaj_bitleri, gurultu_kapi)` işlevini yaz:
- `mesaj_bitleri` (`"00"`, `"01"`, `"10"` veya `"11"`): Alice birinci biti `b0 = int(mesaj_bitleri[0])` (`Z` kapısı), ikinci biti `b1 = int(mesaj_bitleri[1])` (`X` kapısı) olarak kodlar (`kodlama_kapisi`: `"00"->"I"`, `"01"->"X"`, `"10"->"Z"`, `"11"->"ZX"`).
- Kanalda `gurultu_kapi` (`"I"`, `"X"`, `"Z"` veya `"ZX"`) uygulanır:
  - `"X"` gürültüsü ikinci biti (`b1 ^= 1`) çevirir,
  - `"Z"` gürültüsü birinci biti (`b0 ^= 1`) çevirir,
  - `"ZX"` gürültüsü her iki biti de çevirir.
- `{"kodlama_kapisi": ..., "cozulen_bitler": f"{b0}{b1}", "bozulma_var_mi": bool(cozulen_bitler != mesaj_bitleri)}` döndür.

```starter
# KUSURLU BAŞLANGIÇ KODU: kodlama kapısını ve gürültü etkisini hesapla.
def superdense_kodla_coz(mesaj_bitleri, gurultu_kapi):
    return {
        "kodlama_kapisi": "I",
        "cozulen_bitler": mesaj_bitleri,
        "bozulma_var_mi": False
    }

print(superdense_kodla_coz("11", "I"))
print(superdense_kodla_coz("10", "X"))
```
```test
f = need("superdense_kodla_coz")
# Her satırdaki çözülmüş bitler sırasıyla I, X, Z ve ZX gürültüsüne karşılık gelir.
for mesaj, kodlama, beklenenler in (
    ("00", "I",  ("00", "01", "10", "11")),
    ("01", "X",  ("01", "00", "11", "10")),
    ("10", "Z",  ("10", "11", "00", "01")),
    ("11", "ZX", ("11", "10", "01", "00")),
):
    for gurultu, cozulen in zip(("I", "X", "Z", "ZX"), beklenenler):
        eq(f(mesaj, gurultu), {
            "kodlama_kapisi": kodlama,
            "cozulen_bitler": cozulen,
            "bozulma_var_mi": mesaj != cozulen,
        }, f"Mesaj {mesaj}, gürültü {gurultu}")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def superdense_kodla_coz(mesaj_bitleri, gurultu_kapi):\n    kapi_tablosu = {'00': 'I', '01': 'X', '10': 'Z', '11': 'ZX'}\n    kodlama = kapi_tablosu[mesaj_bitleri]\n    b0 = int(mesaj_bitleri[0])\n    b1 = int(mesaj_bitleri[1])\n    if 'Z' in gurultu_kapi:\n        b0 ^= 1\n    if 'X' in gurultu_kapi:\n        b1 ^= 1\n    cozulen = f'{b0}{b1}'\n    return {'kodlama_kapisi': kodlama, 'cozulen_bitler': cozulen, 'bozulma_var_mi': bool(cozulen != mesaj_bitleri)}", 'referans', 'exec'), _REF)
_t, _g = _ff(superdense_kodla_coz, _REF['superdense_kodla_coz'], ('11', 'I'), tohum=3046, en_cok=600, mod='gecerli', butce='oto')
ok(_t, "farksal tarama (superdense_kodla_coz): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
def superdense_kodla_coz(mesaj_bitleri, gurultu_kapi):
    kapi_tablosu = {"00": "I", "01": "X", "10": "Z", "11": "ZX"}
    kodlama = kapi_tablosu[mesaj_bitleri]
    b0 = int(mesaj_bitleri[0])
    b1 = int(mesaj_bitleri[1])
    if "Z" in gurultu_kapi:
        b0 ^= 1
    if "X" in gurultu_kapi:
        b1 ^= 1
    cozulen = f"{b0}{b1}"
    return {
        "kodlama_kapisi": kodlama,
        "cozulen_bitler": cozulen,
        "bozulma_var_mi": bool(cozulen != mesaj_bitleri)
    }

print(superdense_kodla_coz("11", "I"))
print(superdense_kodla_coz("10", "X"))
```
```hint
`"00"->"I"`, `"01"->"X"`, `"10"->"Z"`, `"11"->"ZX"` tablosunu kullan; `gurultu_kapi` içinde `"Z"` varsa `b0 ^= 1`, `"X"` varsa `b1 ^= 1` uygula.
```
:::

::: gorev 3 · No-Cloning Kanıtı: CNOT Kopyalayıcının Süperpozisyonda Çöküşü
Bir saldırgan bilinmeyen bir qubit'i kopyalamak için en doğal devreyi dener: hedef qubit'i `|0⟩` hazırlar ve `CNOT` uygular. Bu devre `|0⟩` ve `|1⟩` için kusursuz kopya üretir; ama süperpozisyonda **dolaşık** bir durum üretir ve kopya bozulur. `klonlama_sadakati(alfa, beta)` işlevini yaz.

**Girdiler:** `alfa`, `beta`: $|\psi\rangle = \alpha|0\rangle + \beta|1\rangle$ durumunun **gerçek** genlikleri. `bool` ya da sayı olmayan değer veya $|\alpha^2 + \beta^2 - 1| > 10^{-9}$ ise `ValueError`.

**Hesap** (genlik sırası `|00⟩, |01⟩, |10⟩, |11⟩`):
1. `"kopyalanan"`: `CNOT` çıktısı $\alpha|00\rangle + \beta|11\rangle$ → `[alfa, 0.0, 0.0, beta]`.
2. `"ideal"`: istenen $|\psi\rangle \otimes |\psi\rangle$ → `[alfa², alfa·beta, alfa·beta, beta²]`.
3. `"sadakat"`: $F = |\langle \text{ideal} | \text{kopyalanan} \rangle|^2 = (\alpha^3 + \beta^3)^2$.
4. `"kusursuz_mu"`: $F > 1 - 10^{-9}$ ise `True`.

Sayısal çıktıları `round(v, 6)` ile yuvarla. `|+⟩` durumunda sadakat tam `0.5` çıkar: kopyalayıcı yalnız kendi tasarlandığı iki ortogonal durumda çalışır, bu da no-cloning teoreminin doğrusallıktan gelen özüdür.

```starter
def klonlama_sadakati(alfa, beta):
    # KUSURLU BAŞLANGIÇ: CNOT'un her durumu kusursuz kopyaladığını varsayıyor
    return {"kopyalanan": [alfa * alfa, alfa * beta, alfa * beta, beta * beta],
            "ideal": [alfa * alfa, alfa * beta, alfa * beta, beta * beta],
            "sadakat": 1.0, "kusursuz_mu": True}

print(klonlama_sadakati(0.6, 0.8))
```

```test
import math
fn = need("klonlama_sadakati")
r0 = fn(1.0, 0.0)
eq(r0["sadakat"], 1.0, "|0⟩ bir taban durumu: CNOT onu kusursuz kopyalar (F = 1)")
eq(r0["kusursuz_mu"], True, "|0⟩ için kopya kusursuz")
eq(fn(0.0, 1.0)["sadakat"], 1.0, "|1⟩ de kusursuz kopyalanır")
h = 1 / math.sqrt(2)
r = fn(h, h)
eq(r["kopyalanan"], [0.707107, 0.0, 0.0, 0.707107], "|+⟩ için CNOT çıktısı Bell durumu (|00⟩ + |11⟩)/√2")
eq(r["ideal"], [0.5, 0.5, 0.5, 0.5], "|+⟩⊗|+⟩ tüm genlikleri 0.5")
eq(r["sadakat"], 0.5, "|+⟩ için sadakat (α³+β³)² = 0.5")
eq(r["kusursuz_mu"], False, "süperpozisyon kusursuz kopyalanamaz")
r2 = fn(0.6, 0.8)
eq(r2["sadakat"], 0.529984, "(0.216 + 0.512)² = 0.529984")
eq(fn(-h, h)["sadakat"], 0.0, "|−⟩ için α³+β³ = 0: kopya ideal duruma tamamen dik")
raises(ValueError, fn, 0.6, 0.6)
raises(ValueError, fn, True, 0.0)
raises(ValueError, fn, "0.6", 0.8)
raises(ValueError, fn, float("nan"), 0.0)
raises(ValueError, fn, float("inf"), 0.0)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\ndef klonlama_sadakati(alfa, beta):\n    for v in (alfa, beta):\n        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):\n            raise ValueError('genlikler gerçek sayı olmalı')\n    if abs(alfa * alfa + beta * beta - 1.0) > 1e-09:\n        raise ValueError('durum normalize değil: alfa² + beta² = 1 olmalı')\n    kopya = [alfa, 0.0, 0.0, beta]\n    ideal = [alfa * alfa, alfa * beta, alfa * beta, beta * beta]\n    ic = sum((a * b for a, b in zip(ideal, kopya)))\n    f = ic * ic\n    return {'kopyalanan': [round(v, 6) for v in kopya], 'ideal': [round(v, 6) for v in ideal], 'sadakat': round(f, 6), 'kusursuz_mu': f > 1 - 1e-09}", 'referans', 'exec'), _REF)
_t, _g = _ff(klonlama_sadakati, _REF['klonlama_sadakati'], (0.6, 0.8), tohum=2691, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (klonlama_sadakati): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
def klonlama_sadakati(alfa, beta):
    import math
    for v in (alfa, beta):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError("genlikler gerçek sayı olmalı")
    if abs(alfa * alfa + beta * beta - 1.0) > 1e-9:
        raise ValueError("durum normalize değil: alfa² + beta² = 1 olmalı")
    kopya = [alfa, 0.0, 0.0, beta]
    ideal = [alfa * alfa, alfa * beta, alfa * beta, beta * beta]
    ic = sum(a * b for a, b in zip(ideal, kopya))
    f = ic * ic
    return {"kopyalanan": [round(v, 6) for v in kopya], "ideal": [round(v, 6) for v in ideal],
            "sadakat": round(f, 6), "kusursuz_mu": f > 1 - 1e-9}
```

```hint
İç çarpım yalnız `|00⟩` ve `|11⟩` bileşenlerinden gelir: `alfa·alfa² + beta·beta²`. Karesini al; doğrulamayı hesaptan önce yap.
```
:::

::: anlat Sınır
Görevler teleportation'da Bell ölçümü ile Bob'un Pauli düzeltmesini ve superdense coding'in kodlama/çözme adımlarını ideal durumlarla hesaplatır. Teleportation ışıktan hızlı iletişim sağlamaz: Bob iki klasik bit gelmeden durumu düzeltemez. Gerçek kanallarda Bell çiftinin sadakati (fidelity) düşer; entanglement purification yapılmazsa ışınlanan durum bozulur. Kanal gürültüsü ve ölçüm istatistiği modellenmez. No-cloning görevi yalnız CNOT kopyalayıcısının süperpozisyonda başarısız olduğunu gösterir; her birimsel kopyalayıcının doğrusallık nedeniyle başarısız olduğunun genel ispatı anlatımdadır.

Kaynaklar: [Bennett vd. 1993 - Teleporting an unknown quantum state via dual classical and Einstein-Podolsky-Rosen channels](https://doi.org/10.1103/PhysRevLett.70.1895), [Bennett ve Wiesner 1992 - Communication via one- and two-particle operators on Einstein-Podolsky-Rosen states](https://doi.org/10.1103/PhysRevLett.69.2881).
:::

::: dusun
Şu örneği incele:

Bir siber güvenlik konferansında dinleyici şunu sordu:
*"Hocam, `Quantum Teleportation` sırasında kuantum durumu aradaki fiber optik kablodan fiziksel olarak geçmiyor; sadece `m0` ve `m1` adlı 2 klasik bit geçiyor! O halde aradaki kabloyu dinleyen bir hacker (`Man-in-the-Middle`) bu `m0` ve `m1` bitlerini okuduğunda ışınlanan gizli $|\psi\rangle$ durumunu çalabilir mi?"*

Kendi cümlelerinle açıkla: Neden $(m_0, m_1)$ bitleri tek başına tamamen rastgele (%25 olasılıklı) gürültüdür ve Bob'un elindeki dolaşık eş (`Bell Pair` yarısı) olmadan saldırgana $|\psi\rangle$ hakkında **sıfır bit bilgi** verir?
:::

::: ozet
- **`Quantum Teleportation`**, önceden paylaşılmış 1 **`Bell Pair`** ve ışık hızıyla gönderilen **2 klasik ölçüm biti** $(m_0, m_1)$ kullanarak bilinmeyen $|\psi\rangle = \alpha|0\rangle + \beta|1\rangle$ durumunu aradaki kanaldan Qubit geçirmeden Bob'da yeniden oluşturur.
- Alice'in ölçümü orijinal durumu çökerttiği için **`No-Cloning Theorem`** korunur; Bob'un $Z^{m_0}X^{m_1}$ düzeltmesi için 2 klasik bitin ulaşması gerektiğinden **`No-Communication Theorem`** (ışıktan hızlı iletişim yasağı) ihlal edilmez.
- **`Superdense Coding`**, teleportasyonun tam ikizidir: paylaşılan bir `Bell Pair` yardımıyla 1 Qubit göndererek 2 klasik bit bilgi taşır.
:::
