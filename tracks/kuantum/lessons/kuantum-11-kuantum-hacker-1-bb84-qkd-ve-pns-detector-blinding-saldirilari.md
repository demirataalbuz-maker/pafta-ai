---
id: kuantum-11
title: "Kuantum Hacker 1: BB84/E91 QKD Protokolü ve Fiziksel Kuantum Hackleme (PNS & Detector Blinding)"
summary: "BB84 kuantum anahtar dağıtımını (Sifting ve %25 QBER dinleme tespiti) simüle et; gerçek dünyadaki ticari QKD cihazlarını kıran Photon Number Splitting (PNS) ve Detector Blinding saldırılarını ve Decoy-State savunmasını kodla."
track: kuantum
order: 11
duration_minutes: 40
difficulty: ileri
xp: 310
prerequisites: [kuantum-10]
tags: [quantum-hacking, bb84, qkd, qber, photon-number-splitting, decoy-state, detector-blinding]
esleme: kuantum-10, kuantum-25
---

::: anlat 1. BB84 Protokolü ve Neden Araya Giren Hacker %25 QBER İzi Bırakır?
## QKD, QBER ve cihaz varsayımları

QKD protokol analizi ile gerçek optik cihaz güvenliği aynı şey değildir. Bu derste BB84 sifting ve QBER hesabını, ardından PNS/decoy-state örneğini inceleyeceksin. Anahtarın güvenliği authentication, cihaz ve istatistik varsayımlarına bağlıdır; düşük QBER tek başına yeterli kabul değildir.

### 🔑 BB84 Adım Adım Çalışma Mekanizması:
1. Alice rastgele bitler ($0$ veya $1$) seçer ve her biti rastgele iki bazdan (`Basis`) biriyle foton polarizasyonuna kodlar:
   - **Artı Bazı (`+` / `Rectilinear Basis`):** $0 \to |0\rangle$ ($\uparrow$), $1 \to |1\rangle$ ($\rightarrow$)
   - **Çarpı Bazı (`x` / `Diagonal / Hadamard Basis`):** $0 \to |+\rangle = \frac{|0\rangle+|1\rangle}{\sqrt{2}}$ ($\nearrow$), $1 \to |-\rangle = \frac{|0\rangle-|1\rangle}{\sqrt{2}}$ ($\searrow$)
2. Bob gelen her fotonu ölçmek için kendi başına rastgele `+` veya `x` bazı seçer:
   - Eğer Bob, Alice ile **aynı bazı** seçmişse (%50 ihtimal), biti **%100 doğru** okur!
   - Eğer Bob **farklı bazı** seçmişse (%50 ihtimal), süperpozisyon çöker ve sonuç %50-%50 tamamen rastgele çıkar.
3. **Eleme (`Key Sifting`):** Gönderim bittikten sonra Alice ve Bob açık kanaldan **yalnızca hangi bazları kullandıklarını** (bit değerlerini değil!) söylerler. Bazların uyuşmadığı konumları çöpe atarlar; geriye **`Sifted Key`** kalır.

### 🕵️‍♂️ Eve'in `Intercept-Resend` Saldırısı ve %25 `QBER` Kanıtı:
Peki hattı dinleyen **Eve**, geçen her fotonu ölçüp Bob'a yeniden gönderirse (`Intercept-Resend Attack`) ne olur?
- Eve, Alice'in hangi bazı (`+` mı `x` mi) seçtiğini bilmiyor!
- Eve **%50 olasılıkla doğru bazı** seçer $\to$ Bob'a doğru durumu gönderir ($0$ hata).
- Eve **%50 olasılıkla yanlış bazı** seçer $\to$ Fotonun durumunu bozar ve Bob doğru bazı seçse bile **%50 olasılıkla yanlış bit** ölçer!
- Toplam hata olasılığı (**`QBER — Quantum Bit Error Rate`**):

$$\text{QBER}_{\text{Eve}} = 0.50 \times 0.50 = 0.25 \quad (\mathbf{\%25\text{ Hata Oranı!}})$$

Alice ve Bob, `Sifted Key` içinden küçük bir örneklem kümesini açıkça karşılaştırır. Eğer $QBER > \%11$ (**Shor-Preskill Güvenlik Eşiği**) çıkarsa hattın dinlendiğini anında anlarlar ve anahtarı imha ederler!

```python
# BB84 Intercept-Resend saldırısında teorik vs pratik QBER hesabı
def intercept_resend_qber_hesapla(dogru_baz_olasiligi=0.5, yanlis_bazda_hata_olasiligi=0.5):
    return round((1.0 - dogru_baz_olasiligi) * yanlis_bazda_hata_olasiligi, 4)

print("Eve tüm fotonları dinlerse oluşan QBER:", intercept_resend_qber_hesapla())
```

**Kaynak ve sınır:** [IBM Quantum: temel quantum information](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information). Sayısal örnekler eğitim ölçeğindedir; gerçek quantum hardware, standart PQC ürünü veya ağ üzerindeki bir hedef üzerinde kabul testi yapılmaz.
:::

::: anlat 2. Kuantum Hacker Saldırısı #1: Photon Number Splitting (PNS) Attack!
Buraya kadar her şey kağıt üzerinde kusursuz görünüyordu. Cihaz üreticileri bankalara ve devletlere milyon dolarlık `QKD` kutuları satıp *"Fizik yasalarıyla %100 kırılmaz!"* dediler.
Ancak gerçek dünyadaki **Kuantum Hacker'lar** (kriptanalistler ve optik donanım araştırmacıları) şu soruyu sordu:
> *"Kağıt üzerindeki teorem Alice'in her seferinde **tam 1 adet foton (`Single Photon`)** gönderdiğini varsayıyor. Peki gerçek dünyadaki lazerler tek foton üretebiliyor mu?"*

**Hayır!** Gerçek ticari QKD cihazları zayıflatılmış lazer darbeleri (**`Weak Coherent Pulses - WCP`**) kullanır. Bir lazer darbesinin içindeki foton sayısı $k$, ortalama foton sayısı $\mu$ olan **Poisson Dağılımı** izler:
$$P(k \text{ foton}) = \frac{e^{-\mu} \mu^k}{k!}$$
Yani bazı darbelerde $0$ foton, çoğunda $1$ foton, **ama bazı darbelerde aynı polarizasyona sahip $2$ veya $3$ foton** aynı anda gider!

```
Alice (WCP Lazer) ──► [ 2 Fotonlu Darbe: |ψ⟩|ψ⟩ ] ──► EVE (Kuantum Hacker)
                                                        ├── 1. Fotonu Quantum Memory'ye saklar!
                                                        └── 2. Fotonu hiç bozmadan Bob'a yollar!
                                                                 (QBER = %0.00! Hayalet Saldırı!)
```

### 💥 `Photon Number Splitting (PNS)` Nasıl Çalışır?
1. Eve, fiber kabloya **`Quantum Nondemolition (QND)`** foton-sayısı ölçer yerleştirir (polarizasyonu bozmadan sadece darbede kaç foton olduğunu sayar).
2. Eğer darbede **$1$ foton** varsa: Eve bu fotonu **bloklar (yok eder)**! Bob bunu neden fark etmez? Çünkü 50 km'lik fiber optik kabloda fotonların %90'ı zaten doğal hat kaybı (`Channel Attenuation`) yüzünden kaybolmaktadır! Eve ise kendi düşük kayıplı süper-kanalıyla kaybı taklit eder.
3. Eğer darbede **$2$ veya daha fazla foton** varsa: Eve fotonlardan birini ayırıp kendi **`Quantum Memory`** (Kuantum Belleği) ünitesine koyar, diğer fotonu hiç dokunmadan Bob'a gönderir!
4. Alice ve Bob gönderimi bitirip açık kanaldan bazları (`+` veya `x`) ilan ettikleri anda, Eve kendi belleğindeki fotonları **%100 doğru bazda** ölçer!
5. **Sonuç:** **`QBER = %0.00`**! Alice ve Bob hattın tertemiz olduğunu sanırken Eve, varsayılan çok-fotonlu darbelerden gelen bitleri öğrenebilir. Kazanım; kaynak, kayıp ve decoy-state ayarlarına bağlıdır.

### 🛡️ PNS Saldırısına Karşı Savunma: `Decoy-State Protocol` (Hwang 2003, Lo-Ma-Chen 2005)
Bu korkunç saldırıyı nasıl durdururuz? **`Decoy-State (Sahte/Yem Durum) Protokolü`** ile!
- Alice sadece tek bir lazer şiddeti ($\mu_{\text{signal}} \approx 0.5$) kullanmak yerine, rastgele anlarda araya çok düşük şiddetli **Yem Darbeleri (`Decoy Pulses`, $\mu_{\text{decoy}} \approx 0.1$)** karıştırır.
- Eve hattaki tek fotonluk bir darbenin `Signal` lazerinden mi yoksa `Decoy` lazerinden mi çıktığını **fiziksel olarak ayırt edemez!**
- Eve `PNS` saldırısı yapıp tek fotonlu darbeleri blokladığında, neredeyse tamamı tek fotondan oluşan `Decoy` darbelerinin Bob'a ulaşma verimi (**`Decoy Yield`**) çakılır!
- Gönderim sonunda Alice hangi darbelerin `Decoy` olduğunu açıklar; `decoy_verimi / sinyal_verimi` oranı normal Poisson beklentisinin altına düşmüşse **`PNS_SALDIRISI_TESPIT_EDILDI`** alarmı çalar!
:::

::: anlat 3. Kuantum Hacker Saldırısı #2: Detector Blinding Attack (Vadim Makarov)
Ünlü kuantum hacker **Vadim Makarov** ve ekibi, *Nature Photonics* (2010) makalesinde ticari QKD sistemlerini tek bir foton bile saymadan tamamen kör eden ikinci bir fiziksel saldırı gösterdi: **`Detector Blinding (Dedektör Körleştirme)`**.

- Bob'un QKD kutusunda tek bir fotonu yakalamak için çığ fotodiyotları (**`Avalanche Photodiodes - APD`**) **"Geiger Modunda"** (kuantum tek-foton modunda) çalışır.
- Makarov, fiber kablodan Bob'un dedektörlerine **parlak sürekli lazer ışığı (`Continuous-Wave Bright Laser`)** tuttuğunda APD dedektörlerinin kuantum Geiger modundan çıkıp **klasik doğrusal fotodiyot moduna ("kör" moda)** geçtiğini keşfetti!
- Kör moddaki dedektör artık tek fotonlara tepki vermez; yalnızca Eve'in gönderdiği klasik yüksek güçlü lazer darbesi $I_{\text{th}}$ eşiğini aştığında "tık" (`Click`) üretir!
- Eve önce sinyali ölçer, sonra Bob'a kendi seçtiği bazda parlak bir darbe gönderir:
  - Eğer Bob, Eve ile **aynı bazı** seçmişse tüm güç tek dedektöre düşer ve Bob **Eve'in istediği biti** ölçer!
  - Eğer Bob **farklı bazı** seçmişse güç ikiye bölünür ($I/2 < I_{\text{th}}$), hiçbir dedektör ötmez (`No-Click`) ve o adım `Sifting` sırasında çöpe atılır!
- **Sonuç:** Eve yine **%0 QBER** ile Bob'un dedektörünü uzaktan kukla gibi yönetir! (Savunması: Dedektör girişine optik güç izleyicisi `Watchdog Photodiode` koymak veya dedektörleri tamamen aradan çıkaran **`Measurement-Device-Independent QKD (MDI-QKD)`** kullanmaktır).
:::

::: tahmin Decoy-State ile PNS Saldırısını Yakalamak
Normal bir fiber optik kanalda `decoy_verimi / sinyal_verimi` oranının $[0.18, 0.25]$ aralığında olması bekleniyor. Eve `PNS` saldırısı yapıp tek fotonlu paketleri blokladığında `sinyal_verimi = 0.040`, `decoy_verimi = 0.002` olarak ölçülüyor. Aşağıdaki kodun çıktısı nedir?

```python
sinyal_verimi = 0.040
decoy_verimi = 0.002
oran = round(decoy_verimi / sinyal_verimi, 4)
alarm = oran < 0.18 or oran > 0.25
print(f"VerimOrani={oran} | PNS_Alarm={alarm}")
```

???

```cikti
VerimOrani=0.05 | PNS_Alarm=True
```
Eve tek fotonları blokladığında `Decoy` darbeleri neredeyse tamamen yok olduğu için oran $0.002 / 0.040 = 0.05$'e düşer (`0.05 < 0.18`). Böylece **QBER %0 olsa bile** `Decoy-State` dedektörü `PNS` saldırısını (`PNS_Alarm=True`) anında yakalar!
:::

::: gorev 1 · BB84 Anahtar Eleme (Sifting), QBER Hesabı ve Dinleme (Eavesdropping) Tespiti
`bb84_analiz_et(alice_bitler, alice_bazlar, bob_bazlar, bob_olcumler, kontrol_indeksleri)` işlevini yaz:
1. `alice_bazlar[i] == bob_bazlar[i]` olan indisleri (`elenmis_indeksler`) bul.
2. Bu elenmiş indisler içinde:
   - `i in kontrol_indeksleri` olanlarda `alice_bitler[i] != bob_olcumler[i]` sayısını elenmiş kontrol sayısına bölerek `qber` (`round(hata / kontrol_say, 4)`, kontrol sayısı 0 ise `0.0`) hesapla.
   - `i not in kontrol_indeksleri` olanlarda `bob_olcumler[i]` bitlerini aday anahtar listesine sırayla ekle.
3. Eğer `qber > 0.11` ise `dinleme_tespit_edildi = True` ve `guvenli_anahtar = []` (anahtar iptal edilir!), değilse `dinleme_tespit_edildi = False` ve `guvenli_anahtar = aday_anahtar` döndür.
4. Sözlük formatı: `{"elenmis_uzunluk": ..., "qber": ..., "dinleme_tespit_edildi": ..., "guvenli_anahtar": ...}`.

```starter
# KUSURLU BAŞLANGIÇ KODU: baz eşleşmesini (sifting) ve QBER kontrolünü tamamla.
def bb84_analiz_et(alice_bitler, alice_bazlar, bob_bazlar, bob_olcumler, kontrol_indeksleri):
    return {
        "elenmis_uzunluk": len(alice_bitler),
        "qber": 0.0,
        "dinleme_tespit_edildi": False,
        "guvenli_anahtar": list(bob_olcumler)
    }

print(bb84_analiz_et([1,0,1,1,0,1], ["+","+","x","+","x","+"], ["+","x","x","+","+","+"], [1,0,1,1,0,1], [0,2]))
```
```test
f = need("bb84_analiz_et")
# Temiz kanal (QBER = 0.0 <= 0.11)
r_temiz = f(
    [1, 0, 1, 1, 0, 1, 0, 0],
    ["+", "+", "x", "+", "x", "+", "x", "+"],
    ["+", "x", "x", "+", "+", "+", "x", "+"],
    [1, 1, 1, 1, 0, 1, 0, 0],
    [0, 2]
)
# Elenmiş indisler: 0, 2, 3, 5, 6, 7 (6 adet). Kontrol: 0, 2 (0 hata). Kalan anahtar indisleri: 3, 5, 6, 7 -> [1, 1, 0, 0]
ok(r_temiz == {"elenmis_uzunluk": 6, "qber": 0.0, "dinleme_tespit_edildi": False, "guvenli_anahtar": [1, 1, 0, 0]}, "Temiz BB84 kanalında sifting ve güvenli anahtar üretimi doğru")

# Dinlenen kanal (Eve %25+ QBER bıraktı -> anahtar imha edilmeli!)
r_eve = f(
    [1, 0, 1, 1, 0, 1, 0, 1],
    ["+", "x", "+", "x", "+", "x", "+", "x"],
    ["+", "x", "+", "x", "+", "x", "+", "x"],
    [1, 1, 1, 0, 0, 1, 0, 1],
    [0, 1, 2, 3]
)
# Kontrol: 0,1,2,3 içinde indis 1 ve 3 hatalı -> 2/4 = 0.5 QBER > 0.11
ok(r_eve == {"elenmis_uzunluk": 8, "qber": 0.5, "dinleme_tespit_edildi": True, "guvenli_anahtar": []}, "Yüksek QBER durumunda dinleme tespit edildi ve anahtar sıfırlandı")
r_bos_k = f([1, 0], ["+", "x"], ["+", "+"], [1, 0], [1])
ok(r_bos_k == {"elenmis_uzunluk": 1, "qber": 0.0, "dinleme_tespit_edildi": False, "guvenli_anahtar": [1]}, "Elenmis kontrol biti bosken QBER 0.0 olmali")
r_sinir = f([1]*9, ["+"]*9, ["+"]*9, [0] + [1]*8, list(range(9)))
ok(r_sinir == {"elenmis_uzunluk": 9, "qber": 0.1111, "dinleme_tespit_edildi": True, "guvenli_anahtar": []}, "QBER=1/9=0.1111 > 0.11 dinleme yakalar ve 4 basamak yuvarlar")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def bb84_analiz_et(alice_bitler, alice_bazlar, bob_bazlar, bob_olcumler, kontrol_indeksleri):\n    kontrol_kumesi = set(kontrol_indeksleri)\n    elenmis = [i for i in range(len(alice_bitler)) if alice_bazlar[i] == bob_bazlar[i]]\n    kontrol_elenmis = [i for i in elenmis if i in kontrol_kumesi]\n    hatalar = sum((1 for i in kontrol_elenmis if alice_bitler[i] != bob_olcumler[i]))\n    qber = round(hatalar / len(kontrol_elenmis), 4) if kontrol_elenmis else 0.0\n    aday = [bob_olcumler[i] for i in elenmis if i not in kontrol_kumesi]\n    dinleme = bool(qber > 0.11)\n    return {'elenmis_uzunluk': len(elenmis), 'qber': qber, 'dinleme_tespit_edildi': dinleme, 'guvenli_anahtar': [] if dinleme else aday}", 'referans', 'exec'), _REF)
_t, _g = _ff(bb84_analiz_et, _REF['bb84_analiz_et'], ([1, 0, 1, 1, 0, 1], ['+', '+', 'x', '+', 'x', '+'], ['+', 'x', 'x', '+', '+', '+'], [1, 0, 1, 1, 0, 1], [0, 2]), tohum=2266, en_cok=600, mod='gecerli', butce='oto', ekler=[([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], ['+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+'], ['+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+', '+'], [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99], )])
ok(_t, "farksal tarama (bb84_analiz_et): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
def bb84_analiz_et(alice_bitler, alice_bazlar, bob_bazlar, bob_olcumler, kontrol_indeksleri):
    kontrol_kumesi = set(kontrol_indeksleri)
    elenmis = [i for i in range(len(alice_bitler)) if alice_bazlar[i] == bob_bazlar[i]]
    kontrol_elenmis = [i for i in elenmis if i in kontrol_kumesi]
    hatalar = sum(1 for i in kontrol_elenmis if alice_bitler[i] != bob_olcumler[i])
    qber = round(hatalar / len(kontrol_elenmis), 4) if kontrol_elenmis else 0.0
    aday = [bob_olcumler[i] for i in elenmis if i not in kontrol_kumesi]
    dinleme = bool(qber > 0.11)
    return {
        "elenmis_uzunluk": len(elenmis),
        "qber": qber,
        "dinleme_tespit_edildi": dinleme,
        "guvenli_anahtar": [] if dinleme else aday
    }

print(bb84_analiz_et([1,0,1,1,0,1], ["+","+","x","+","x","+"], ["+","x","x","+","+","+"], [1,0,1,1,0,1], [0,2]))
```
```hint
Önce `alice_bazlar[i] == bob_bazlar[i]` olan indisleri süz; `kontrol_indeksleri` içindekilerden `qber` hesapla, dışındakilerden anahtarı oluştur ve `qber > 0.11` ise anahtarı `[]` yap.
```
:::

::: gorev 2 · Photon Number Splitting (PNS) Saldırısı vs Decoy-State (Sahte Yoğunluk) Savunma Dedektörü
`pns_saldiri_tespit(sinyal_verimi, decoy_verimi, beklenen_oran_alt, beklenen_oran_ust)` işlevini yaz:
- `verim_orani = round(decoy_verimi / sinyal_verimi, 4)` değerini hesapla.
- Eğer `verim_orani < beklenen_oran_alt` veya `verim_orani > beklenen_oran_ust` ise `pns_saldirisi_var = True` ve `durum = "PNS_SALDIRISI_TESPIT_EDILDI"`, aksi halde `pns_saldirisi_var = False` ve `durum = "KANAL_TEMIZ"` döndür.

```starter
# KUSURLU BAŞLANGIÇ KODU: Decoy/Signal verim oranını ve sınır kontrolünü yaz.
def pns_saldiri_tespit(sinyal_verimi, decoy_verimi, beklenen_oran_alt, beklenen_oran_ust):
    return {
        "verim_orani": 0.0,
        "pns_saldirisi_var": False,
        "durum": "KANAL_TEMIZ"
    }

print(pns_saldiri_tespit(0.04, 0.002, 0.18, 0.25))
```
```test
f = need("pns_saldiri_tespit")
ok(f(0.04, 0.008, 0.18, 0.25) == {"verim_orani": 0.2, "pns_saldirisi_var": False, "durum": "KANAL_TEMIZ"}, "Normal Poisson verim oranında kanal temiz bulundu")
ok(f(0.04, 0.002, 0.18, 0.25) == {"verim_orani": 0.05, "pns_saldirisi_var": True, "durum": "PNS_SALDIRISI_TESPIT_EDILDI"}, "Tek fotonların bloklandığı PNS saldırısı Decoy-State ile yakalandı")
ok(f(0.04, 0.015, 0.18, 0.25) == {"verim_orani": 0.375, "pns_saldirisi_var": True, "durum": "PNS_SALDIRISI_TESPIT_EDILDI"}, "Üst sınır dışı anormal verim oranı yakalandı")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("def pns_saldiri_tespit(sinyal_verimi, decoy_verimi, beklenen_oran_alt, beklenen_oran_ust):\n    oran = round(decoy_verimi / sinyal_verimi, 4)\n    saldiri = bool(oran < beklenen_oran_alt or oran > beklenen_oran_ust)\n    return {'verim_orani': oran, 'pns_saldirisi_var': saldiri, 'durum': 'PNS_SALDIRISI_TESPIT_EDILDI' if saldiri else 'KANAL_TEMIZ'}", 'referans', 'exec'), _REF)
_t, _g = _ff(pns_saldiri_tespit, _REF['pns_saldiri_tespit'], (0.04, 0.002, 0.18, 0.25), tohum=2852, en_cok=600, mod='gecerli', butce='oto', ekler=[(0.04, 0.01, 0.18, 0.25, )])
ok(_t, "farksal tarama (pns_saldiri_tespit): örnek çözümden derlenen referansla aynı sonuç (geçerli girdi varyantları)" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
def pns_saldiri_tespit(sinyal_verimi, decoy_verimi, beklenen_oran_alt, beklenen_oran_ust):
    oran = round(decoy_verimi / sinyal_verimi, 4)
    saldiri = bool(oran < beklenen_oran_alt or oran > beklenen_oran_ust)
    return {
        "verim_orani": oran,
        "pns_saldirisi_var": saldiri,
        "durum": "PNS_SALDIRISI_TESPIT_EDILDI" if saldiri else "KANAL_TEMIZ"
    }

print(pns_saldiri_tespit(0.04, 0.002, 0.18, 0.25))
```
```hint
`round(decoy_verimi / sinyal_verimi, 4)` değerinin `[beklenen_oran_alt, beklenen_oran_ust]` aralığı dışında olup olmadığını kontrol et.
```
:::

::: gorev 3 · E91: CHSH Değeriyle Dinleme Tespiti
`E91` protokolünde Alice ve Bob dolaşık foton çiftlerini rastgele açılarda ölçer; anahtar dışındaki ölçümlerden **CHSH** değeri $S$ hesaplanır. Gürültüsüz bir singlet durumda $|S| = 2\sqrt{2}$ olur; ölç-yeniden-gönder yapan bir dinleyici dolaşıklığı bozar ve $|S| \le 2$'ye düşürür. `e91_chsh_analiz(gorunurluk, a1, a2, b1, b2)` işlevini yaz.

**Girdiler:** `gorunurluk` $V \in [0, 1]$ (dolaşıklığın kalitesi); `a1, a2` Alice'in, `b1, b2` Bob'un polarizör açıları (**derece**). Sayı olmayan ya da `bool` değer veya $V \notin [0,1]$ ise `ValueError`.

**Hesap:** Polarizasyon singlet'i için korelasyon $E(a, b) = -V \cos(2(a - b))$ (açılar radyana çevrilerek).
$$S = E(a_1, b_1) - E(a_1, b_2) + E(a_2, b_1) + E(a_2, b_2)$$
Çıktı: `"S"` (`round(S, 6)`), `"S_mutlak"` (`round(abs(S), 6)`), `"bell_ihlali"`: `round(abs(S), 9) > 2.0`, `"dinleme_supheli"`: `bell_ihlali` değilse `True`. Bu alan dersin inceleme bayrağıdır. Düşük görünürlük veya kötü ölçüm açıları da ihlali ortadan kaldırabilir. Üretimde anahtar kabulü, protokolün güvenlik varsayımlarını ve sonlu örneklem analizini gerektirir.

```starter
def e91_chsh_analiz(gorunurluk, a1, a2, b1, b2):
    # KUSURLU BAŞLANGIÇ: korelasyonu hesaplamadan her kanalı güvenli sayıyor
    return {"S": 2.828427, "S_mutlak": 2.828427, "bell_ihlali": True, "dinleme_supheli": False}

print(e91_chsh_analiz(1.0, 0.0, 45.0, 22.5, 67.5))
```

```test
import math
fn = need("e91_chsh_analiz")
r = fn(1.0, 0.0, 45.0, 22.5, 67.5)
eq(r["S_mutlak"], round(2 * math.sqrt(2), 6), "optimal açılarda gürültüsüz singlet |S| = 2√2")
eq(r["S"], -2.828427, "işaretli S değeri: dört korelasyonun toplamı negatif")
eq(r["bell_ihlali"], True, "2√2 > 2: Bell eşitsizliği ihlal ediliyor")
eq(r["dinleme_supheli"], False, "Bu ideal modelde klasik sınır aşıldığında inceleme bayrağı kapanır")
r2 = fn(1 / math.sqrt(2), 0.0, 45.0, 22.5, 67.5)
eq(r2["S_mutlak"], 2.0, "V = 1/√2'de |S| tam 2 (klasik sınır)")
eq(r2["bell_ihlali"], False, "|S| = 2 ihlal değildir (kesinlikle büyük olmalı)")
eq(r2["dinleme_supheli"], True, "Klasik sınıra düşen korelasyon inceleme bayrağını açar")
eq(fn(0.0, 0.0, 45.0, 22.5, 67.5), {
    "S": 0.0, "S_mutlak": 0.0, "bell_ihlali": False, "dinleme_supheli": True,
}, "Sıfır görünürlük korelasyonu siler ve inceleme bayrağını açar")
eq(fn(0.5, 0.0, 45.0, 22.5, 67.5)["S_mutlak"], 1.414214, "V = 0.5 → |S| = √2")
eq(fn(1.0, 0.0, 0.0, 0.0, 0.0)["S"], -2.0, "aynı açılarda E = -1: S = -1 + 1 - 1 - 1 = -2")
raises(ValueError, fn, 1.2, 0.0, 45.0, 22.5, 67.5)
raises(ValueError, fn, True, 0.0, 45.0, 22.5, 67.5)
raises(ValueError, fn, 1.0, "0", 45.0, 22.5, 67.5)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef e91_chsh_analiz(gorunurluk, a1, a2, b1, b2):\n    for v in (gorunurluk, a1, a2, b1, b2):\n        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):\n            raise ValueError('girdiler sonlu sayı olmalı')\n    if not 0.0 <= gorunurluk <= 1.0:\n        raise ValueError('görünürlük 0 ile 1 arasında olmalı')\n\n    def E(a, b):\n        return -gorunurluk * math.cos(2 * math.radians(a - b))\n    s = E(a1, b1) - E(a1, b2) + E(a2, b1) + E(a2, b2)\n    ihlal = round(abs(s), 9) > 2.0\n    return {'S': round(s, 6), 'S_mutlak': round(abs(s), 6), 'bell_ihlali': ihlal, 'dinleme_supheli': not ihlal}", 'referans', 'exec'), _REF)
_t, _g = _ff(e91_chsh_analiz, _REF['e91_chsh_analiz'], (1.0, 0.0, 45.0, 22.5, 67.5), tohum=2374, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (e91_chsh_analiz): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def e91_chsh_analiz(gorunurluk, a1, a2, b1, b2):
    for v in (gorunurluk, a1, a2, b1, b2):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError("girdiler sonlu sayı olmalı")
    if not (0.0 <= gorunurluk <= 1.0):
        raise ValueError("görünürlük 0 ile 1 arasında olmalı")

    def E(a, b):
        return -gorunurluk * math.cos(2 * math.radians(a - b))

    s = E(a1, b1) - E(a1, b2) + E(a2, b1) + E(a2, b2)
    ihlal = round(abs(s), 9) > 2.0
    return {"S": round(s, 6), "S_mutlak": round(abs(s), 6), "bell_ihlali": ihlal, "dinleme_supheli": not ihlal}
```

```hint
`E(a, b) = -V * math.cos(2 * math.radians(a - b))` yardımcı işlevini yaz; S'deki tek eksi işareti `E(a1, b2)` teriminde.
```
:::

::: anlat Sınır
Görevler BB84 elemesini, QBER ile dinleme tespitini ve PNS saldırısına karşı decoy-state dedektörünü hesaplatır. Yaklaşık %11'lik QBER eşiği BB84'ün belirli güvenlik ispatlarına dayanır; sonlu anahtar uzunluğunda istatistiksel dalgalanma eşiği değiştirir. QKD anahtarı fiziksel kanal üzerinden korur, ama tarafların kimliğini doğrulamak için yine kimlik doğrulamalı bir klasik kanal gerekir; o olmadan ortadaki adam saldırısı mümkündür. E91 görevi ideal korelasyon modeli E = −V·cos 2(a−b) ile hesaplanır, sonlu örnek istatistiği yoktur; detector blinding yalnız anlatımdadır; donanım saldırıları matematik modelde değil cihaz kusurlarında yaşar ve buradaki hesap bunları göstermez.

Kaynaklar: [Bennett ve Brassard 1984 - Quantum cryptography: Public key distribution and coin tossing](https://arxiv.org/abs/2003.06557), [Ekert 1991 - Quantum cryptography based on Bell's theorem](https://doi.org/10.1103/PhysRevLett.67.661), [Lo vd. 2005 - Decoy State Quantum Key Distribution](https://arxiv.org/abs/quant-ph/0411004), [Lydersen vd. 2010 - Hacking commercial quantum cryptography systems by tailored bright illumination](https://arxiv.org/abs/1008.4593).
:::

::: dusun
ABD Ulusal Güvenlik Ajansı (**NSA**) ve İngiltere **NCSC**, kuantum sonrası güvenlik rehberlerinde donanımsal **`QKD`** yerine yazılımsal **`Post-Quantum Cryptography (PQC — ML-KEM / ML-DSA)`** önermektedir. Bu derste öğrendiğin **`Photon Number Splitting (PNS)`**, **`Detector Blinding`** fiziksel yan-kanal (`Side-Channel`) saldırılarını ve fiber optik mesafe/röle (`Trusted Node`) sınırlarını kullanarak bu stratejik tercihin nedenlerini bir siber güvenlik mimarı gözüyle açıkla.
:::

::: ozet
- **`BB84 QKD`** protokolünde araya girip ölçüm yapan (`Intercept-Resend`) bir saldırgan, bazların yarısını yanlış tahmin ettiği için elenmiş anahtarda **%25 `QBER`** bırakır ($>\%11$ eşiğinde iletişim kesilir).
- Gerçek dünyadaki lazerler çoklu foton (`Weak Coherent Pulse`) ürettiği için bir Kuantum Hacker **`Photon Number Splitting (PNS)`** saldırısıyla 1 fotonlu darbeleri bloklayıp 2+ fotonlu darbelerden birini çalabilir ve **%0 QBER** ile anahtarı ele geçirebilir; bu saldırı **`Decoy-State Protocol`** ile tespit edilir.
- **`Detector Blinding Attack`** (Makarov), Bob'un `APD` dedektörlerini parlak lazerle doğrusal moda sokarak uzaktan kontrol eder; fiziksel donanım kusurları teorik kuantum güvenlik kanıtlarını deldiği için donanım sertleştirmesi (`MDI-QKD` ve güç izleyicileri) şarttır.
:::
