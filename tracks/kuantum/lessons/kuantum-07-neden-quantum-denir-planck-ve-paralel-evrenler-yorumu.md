---
id: kuantum-07
title: "Neden 'Quantum' Denir? Planck'tan Paralel Evrenler Yorumuna (Many-Worlds vs Copenhagen)"
track: kuantum
order: 7
duration_minutes: 30
difficulty: orta
xp: 260
prerequisites: [kuantum-06]
tags: [kuantum-fizigi, planck, copenhagen-interpretation, many-worlds-interpretation, decoherence]
summary: "Planck kuantum hipotezini, Kopenhag ve Çoklu Dünyalar yorumlarının ortak Schrödinger matematiğini, iki yollu karmaşık genlik girişimini ve eşevresizlik (decoherence) kaybını incele."
esleme: kuantum-06, kuantum-09
---

::: anlat
## Sahnedeki En Merak Edilen Soru: "Neden Quantum Denir ve Gerçekten Başka Evrendeki Bilgisayarları mı Kullanıyor?"

Bir konferansta **Quantum Computing** anlattığında izleyicilerden mutlaka şu iki soru gelir:
1. *"Hocam, neden bu bilgisayarlara **Quantum** deniyor? Kelime anlamı ne?"*
2. *"Google Quantum AI'ın kurucusu Hartmut Neven ve bazı fizikçiler kuantum bilgisayarların paralel evrenlerdeki bilgisayarları kullandığını söylüyor; bu gerçek mi yoksa bilim kurgu mu?"*

Bu iki soruya kulaktan dolma değil, tarihsel ve matematiksel kesinlikle cevap verdiğin an salondaki herkesin saygısını kazanırsın. Gel ikisini de en derinden açalım.

---

### 1. Neden "Quantum" Denir? (Sürekli Dünyadan "Paketli" Dünyaya Geçiş)

Latincede **Quantum** (çoğulu: **Quanta**) *"ne kadar?"* demektir; fizikte ise *"en küçük bölünemez miktar / paketçik"* anlamında kullanılır.

1900 yılına kadar klasik fizik (**Classical Physics**), doğadaki her şeyin (enerjinin, ışığın, hızın) bir su hortumundan akan su gibi **sürekli (Continuous)** olduğunu sanıyordu. Yani enerjinin $1.0$, $1.0001$, $1.00000042$ gibi sonsuz küsuratlı her değeri alabileceğine inanılıyordu.

Ancak 1900 yılında **Max Planck**, sıcak cisimlerin yaydığı ışığı (**Black-Body Radiation**) hesaplarken klasik fiziğin formüllerinin yüksek frekanslarda sonsuza patladığını gördü (bu soruna 1911'de Ehrenfest **Ultraviolet Catastrophe** adını verdi; Planck'ın asıl derdi deneysel ölçümlere uyan bir formül bulmaktı). Denklemi kurtarmak için tarihin en cesur varsayımını yaptı:
> *"Ya enerji bir hortumdan akan su gibi sürekli (Continuous) değilse? Ya enerji, tıpkı merdiven basamakları veya madeni paralar gibi yalnızca belirli **bölünemez paketçikler (Quanta)** halinde alınıp verilebiliyorsa?"*

$$\Delta E = h \cdot \nu$$

Buradaki $h$, evrenin en küçük çözünürlük sınırı olan **Planck Sabiti (Planck's Constant)** idi. 1905'te **Albert Einstein**, ışığın kendisinin bile kesintisiz bir dalga değil, **Photon** adı verilen enerji paketçiklerinden (**Light Quanta**) oluştuğunu önerdi ve fotoelektrik olayını böyle açıkladı (deneysel doğrulama Millikan, 1916; *photon* adı 1926'da kondu).

Atom altı dünyaya indiğimizde şunları gördük:
- Bir elektron çekirdek etrafında "herhangi bir yörüngede" dönemez; yalnızca belirli, kesikli (**Discrete / Quantized**) enerji basamaklarında bulunabilir. Ara basamak diye bir yer yoktur!
- Bir elektronun kendi etrafındaki açısal momentumu (**Spin**), klasik bir top gibi her yöne rastgele büyüklükte olamaz; ölçüldüğünde yalnızca iki kesikli paket değerinden birini verir: **Spin-Up ($\uparrow$, yani $|0\rangle$)** veya **Spin-Down ($\downarrow$, yani $|1\rangle$)**.

İşte **Quantum Computer** denmesinin sebebi budur: Klasik bilgisayarlar milyarlarca elektronun oluşturduğu kaba elektrik voltajlarını kullanırken; kuantum bilgisayarlar doğanın en küçük, bölünemez **tekil kuantum paketçiklerinin (Single Quanta)** — tek bir elektronun **Spin**'inin, tek bir **Photon**'un **Polarization**'ının veya süperiletken bir devredeki tekil enerji seviyesinin — doğrudan kuantum mekaniği yasalarıyla (**Superposition**, **Entanglement**, **Wave Interference**) kontrol edilmesidir!

```python
# Klasik Sürekli (Continuous) Enerji vs Kuantize (Quantized) Enerji Basamakları
def enerji_seviyesi_kontrol(enerji_birimi):
    # Kuantum dünyasında enerji yalnızca tam sayı paketlerinin (n * h_f) katı olabilir
    en_kucuk_paket = 1.0  # 1 Quantum (h * f)
    kalan = round(enerji_birimi % en_kucuk_paket, 4)
    if kalan == 0:
        return f"E={enerji_birimi}: GEÇERLİ Kuantum Basamağı (Tam {int(enerji_birimi)} Quanta)"
    return f"E={enerji_birimi}: YASAKLI BÖLGE! İki basamak arasında durulamaz."

print(enerji_seviyesi_kontrol(3.0))
print(enerji_seviyesi_kontrol(3.4))
```

---

### 2. "Paralel Evrenlerdeki Bilgisayarları Kullanmak" Ne Demek?

Gelelim ikinci dev soruya! Aralık 2024'te Google, **Willow** adlı 105-qubit kuantum çipini tanıttığında, klasik süper bilgisayarların $10^{25}$ yılda (evrenin yaşından trilyonlarca kat uzun sürede) yapacağı hesabı 5 dakikada çözdüğünü açıkladı. Google Quantum AI lideri **Hartmut Neven**, resmi blog yazısında bu sonucun, kuantum hesaplamanın birçok paralel evrende gerçekleştiği ve bir **Multiverse** içinde yaşadığımız fikrine (ilk kez **David Deutsch**'un öne sürdüğü) destek verdiğini yazdı. Bu bir fizik sonucu değil, Neven'in yorum tercihidir; birçok fizikçi aynı deneyin tek evrenli yorumlarla da eksiksiz açıklandığını hemen belirtti.

Peki fizikçiler bu konuda ne diyor? Kuantum bilgisayarın o 5 dakikada $2^{105}$ durumu aynı anda işlemesini açıklayan **aynı matematiğin (Schrödinger Wave Equation) iki büyük felsefi yorumu (Interpretation)** vardır:

```
                   SCHRÖDINGER DENKLEMİ & 2^N SUPERPOSITION
                                      │
          ┌───────────────────────────┴───────────────────────────┐
          ▼                                                       ▼
  1. COPENHAGEN INTERPRETATION                        2. MANY-WORLDS INTERPRETATION
   (Niels Bohr & W. Heisenberg)                         (Hugh Everett III & David Deutsch)
  ────────────────────────────                        ────────────────────────────────────
  • Tek bir evren vardır.                             • Wave Function Collapse diye bir şey
  • Ölçümden önce Qubit'ler fiziksel                    yoktur; evren asla zar atmaz.
    olarak "Probability Wave" (Olasılık               • Her Superposition adımında evren
    Dalgası / Genliği) halindedir.                      dallanır (Branching Universes).
  • Kuantum kapıları bu dalgaları                     • 300 Qubit varsa, 2^300 paralel evren
    Constructive / Destructive                          dalında hesaplama eşzamanlı yürür
    Interference ile birbirine çarptırır.               ve dallar birbiriyle Interference
  • Ölçüm (Measurement) yapıldığı an                    (girişim) yaparak doğru cevabı üretir!
    dalga fonksiyonu çöker (Wave Function             • Kuantum bilgisayarın kurucu babası
    Collapse) ve tek sonuç görünür.                     David Deutsch bu yoruma inanır.
```

#### A) Copenhagen Interpretation (Niels Bohr & Werner Heisenberg — Standart Yorum)
Fizikçilerin çoğunluğunun kullandığı standart **Copenhagen Interpretation**'a göre paralel evrenlere gerek yoktur:
- Ölçüm yapılana kadar elektron ne sadece $|0\rangle$'dır ne de başka bir evrendedir; elektron bizim evrenimizde **Complex Probability Amplitude (Karmaşık Olasılık Dalgası)** olarak var olur.
- Kuantum bilgisayarın gücü "başka evrendeki bilgisayarlara iş göndermekten" değil, bu olasılık dalgalarını tıpkı su dalgaları gibi birbiriyle çarpıştırıp (**Quantum Interference**) yanlış cevapların dalgalarını söndürmekten (**Destructive Interference**), doğru cevabın dalgasını büyütmekten (**Constructive Interference**) gelir.
- En sonda **Measurement (Ölçüm)** yaptığında dalga fonksiyonu çöker (**Wave Function Collapse**) ve elinde doğru cevap kalır.

#### B) Many-Worlds Interpretation - MWI (Hugh Everett III, 1957 & David Deutsch, 1985)
Peki neden Kuantum Bilgisayarların kurucu babası sayılan Oxford'lu fizikçi **David Deutsch** (*Universal Quantum Computer* makalesinin yazarı, 1985) paralel evrenlerde ısrar ediyor?
- **Hugh Everett** 1957'de şunu sordu: *"Schrödinger denklemi tamamen pürüzsüz ve deterministik bir dalga denklemidir. Denklemin hiçbir yerinde 'ölçüm yapınca dalga aniden çöksün (Collapse)' diye bir kural yok! Eğer denklemi ciddiye alırsak, ölçüm yaptığımızda dalga çökmüyor; gözlemci de dalgayla **Entangled (Dolaşık)** hale geliyor ve gerçeklik dallara ayrılıyor!"*
- **David Deutsch** ise 1997'de *The Fabric of Reality* kitabında bir meydan okuma ortaya koydu. Aşağıdaki, argümanın **özetidir, doğrudan alıntı değildir** (Deutsch kitapta örnek olarak çok büyük bir sayıyı Shor algoritmasıyla çarpanlarına ayırmayı kullanır):
  - Görünür evrende yaklaşık $10^{80}$ atom vardır.
  - 300 qubit'lik bir kuantum bilgisayarın durum vektörü $2^{300} \approx 10^{90}$ genlik taşır ve hesap bu genliklerin girişimiyle ilerler.
  - Yalnız tek bir evren varsa, atom sayısından 10 milyar kat fazla bu "hesaplama durumu" **fiziksel olarak nerededir**?
  - Copenhagen tarafının cevabı: genlikler ayrı ayrı var olan hesaplar değildir; ölçümde yalnız bir sonuç okunabilir ve hızlanma girişim deseninden gelir. Bu yüzden argüman çoğu fizikçi için kesin bir kanıt değil, bir yorum tercihidir.
- Deutsch'a göre: Kuantum kapıları çalıştığı sırada birbirine çok yakın $2^N$ paralel evren dalı (**Branches of the Multiverse**) geçici olarak birbiriyle **Interference (Girişim)** yapar, yani kaynaklarını ortak kullanır ve ölçüm anında doğru sonucu bizim dalımıza bırakır.

#### C) Konferansta Vereceğin "Altın Vuruş" Cevabı:
Birisi sana *"Paralel evrendeki bilgisayarları mı kullanıyor?"* diye sorduğunda şu cevabı vereceksin:
> *"Matematiksel olarak her iki yorum da (**Copenhagen** ve **Many-Worlds Interpretation**) virgülden sonraki son basamağa kadar **birebir aynı denklemi** kullanır ve aynı sonucu verir.
> - Eğer **David Deutsch** ve **Hugh Everett**'in **Many-Worlds Interpretation** penceresinden bakarsanız: Evet, kuantum bilgisayarlar hesaplama sırasında paralel gerçeklik dalları arasındaki **Interference (Girişim)** etkisini kullanan ilk insan yapımı cihazlardır.
> - Eğer **Niels Bohr**'un **Copenhagen Interpretation** penceresinden bakarsanız: Başka bir evrene gitmeye gerek yoktur; doğa tek bir evrende **Hilbert Space** adını verdiğimiz $2^N$ boyutlu bir olasılık dalgası uzayında (**Probability Amplitude**) dalga girişimi yapmaktadır.
> Ancak her iki durumda da kesin olan tek bir şey var: Kuantum bilgisayar, klasik bilgisayarların teker teker geçtiği yolları **Wave Interference** sayesinde tek seferde tarayabilmektedir."*
:::

::: tahmin Hilbert Space ve İki Yorumun Matematiksel Eşdeğerliği
10 Qubit'lik bir kuantum sisteminin Hilbert Space boyutu ve iki yorumun (Copenhagen vs Many-Worlds) matematiksel sonucu hakkında aşağıdaki kod ne yazdırır?

```python
def yorum_karsilastir(qubit_sayisi):
    hilbert_boyutu = 2 ** qubit_sayisi
    copenhagen = "Wave Interference in Hilbert Space"
    many_worlds = "Interference Across Parallel Branches"
    matematiksel_sonuc_ayni_mi = True
    return hilbert_boyutu, matematiksel_sonuc_ayni_mi

boyut, ayni_mi = yorum_karsilastir(10)
print(f"Boyut={boyut} | SonucAyniMi={ayni_mi}")
```

???
```cikti
Boyut=1024 | SonucAyniMi=True
```
$10$ Qubit'lik bir sistemin **Hilbert Space** boyutu $2^{10} = 1024$'tür. Hem **Copenhagen Interpretation** hem de **Many-Worlds Interpretation** aynı **Schrödinger Denklemi**'ni kullandığı için matematiksel tahminleri birebir aynıdır (`True`).
:::

::: gorev 1 · İki Yollu Girişim: Olasılıklar Değil, Genlikler Toplanır
Yorumlar ne derse desin hesap aynıdır. Bir parçacık dedektöre iki yoldan ulaşabiliyorsa her yolun bir **karmaşık genliği** vardır: $a_1$, $a_2$. Hangi yoldan geçtiği bilinmiyorsa (girişim korunuyorsa) olasılık $|a_1 + a_2|^2$'dir. Yol bilgisi çevreye sızmışsa (decoherence) olasılıklar klasik gibi toplanır: $|a_1|^2 + |a_2|^2$. Aradaki fark **girişim terimidir**: $2\,\mathrm{Re}(a_1 \overline{a_2})$. `iki_yol_girisimi(a1, a2)` işlevini yaz.

**Girdi:** her genlik `[gerçek, sanal]` biçiminde 2 öğeli bir listedir.

**Çıktı:** `{"kuantum": |a1 + a2|², "klasik": |a1|² + |a2|², "girisim_terimi": 2·Re(a1·conj(a2)), "tur": ...}`. Sayıları `round(·, 6)` ile yuvarla. `"tur"`: terim `1e-9`'dan büyükse `"yapici"`, `-1e-9`'dan küçükse `"yikici"`, yoksa `"yok"`.

Genlik 2 öğeli liste değilse ya da bileşenlerden biri sonlu bir sayı değilse (`bool` dahil) `ValueError` ver.

```starter
def iki_yol_girisimi(a1, a2):
    # KUSURLU BAŞLANGIÇ: olasılıkları klasik gibi topluyor, girişimi yok sayıyor
    p = a1[0] ** 2 + a1[1] ** 2 + a2[0] ** 2 + a2[1] ** 2
    return {"kuantum": p, "klasik": p, "girisim_terimi": 0.0, "tur": "yok"}

print(iki_yol_girisimi([0.5, 0.0], [-0.5, 0.0]))
```

```test
fn = need("iki_yol_girisimi")
eq(fn([0.5, 0.0], [0.5, 0.0]), {"kuantum": 1.0, "klasik": 0.5, "girisim_terimi": 0.5, "tur": "yapici"}, "aynı fazlı iki yol: olasılık iki katına çıkar")
eq(fn([0.5, 0.0], [-0.5, 0.0]), {"kuantum": 0.0, "klasik": 0.5, "girisim_terimi": -0.5, "tur": "yikici"}, "zıt fazlı iki yol birbirini söndürür (H·H|0⟩'da |1⟩'in genliği)")
eq(fn([0.5, 0.0], [0.0, 0.5]), {"kuantum": 0.5, "klasik": 0.5, "girisim_terimi": 0.0, "tur": "yok"}, "90° faz farkında girişim terimi sıfır")
r = fn([0.3, 0.4], [0.1, -0.2])
eq(r["kuantum"], 0.2, "|(0.3+0.4i) + (0.1−0.2i)|² = |0.4+0.2i|² = 0.2")
eq(r["klasik"], 0.3, "0.25 + 0.05")
eq(r["girisim_terimi"], -0.1, "kuantum = klasik + girişim terimi")
eq(r["tur"], "yikici", "negatif terim yıkıcıdır")
eq(fn([0.0, 0.0], [0.6, 0.8])["tur"], "yok", "bir yol kapalıysa girişim yoktur")
eq(fn([1, 0], [0, 0])["kuantum"], 1.0, "tam sayı bileşen kabul edilir")
eq(fn([0.5, 0.0], [1e-9, 0.0])["tur"], "yok", "Tam pozitif tolerans sınırı")
eq(fn([0.5, 0.0], [-1e-9, 0.0])["tur"], "yok", "Tam negatif tolerans sınırı")
_kucuk = fn([0.5, 0.0], [2e-9, 0.0])
eq(_kucuk["girisim_terimi"], 0.0, "Gösterilen terim altı basamakta sıfıra yuvarlanır")
eq(_kucuk["tur"], "yapici", "Tür yuvarlanmamış terime göre belirlenir")
eq(fn([0.5, 0.0], [-2e-9, 0.0])["tur"], "yikici", "Negatif sınırın hemen dışı")
raises(ValueError, fn, [0.5], [0.5, 0.0])
raises(ValueError, fn, [0.5, 0.0, 0.0], [0.5, 0.0])
raises(ValueError, fn, [0.5, "0"], [0.5, 0.0])
raises(ValueError, fn, [True, 0.0], [0.5, 0.0])
raises(ValueError, fn, [0.5, 0.0], [float("nan"), 0.0])
raises(ValueError, fn, (0.5, 0.0), [0.5, 0.0])

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef iki_yol_girisimi(a1, a2):\n    for a in (a1, a2):\n        if not isinstance(a, list) or len(a) != 2:\n            raise ValueError('genlik [gerçek, sanal] biçiminde 2 öğeli liste olmalı')\n        for x in a:\n            if isinstance(x, bool) or not isinstance(x, (int, float)) or (not math.isfinite(x)):\n                raise ValueError('genlik bileşenleri sonlu sayı olmalı')\n    z1, z2 = (complex(a1[0], a1[1]), complex(a2[0], a2[1]))\n    kuantum = abs(z1 + z2) ** 2\n    klasik = abs(z1) ** 2 + abs(z2) ** 2\n    terim = 2 * (z1 * z2.conjugate()).real\n    tur = 'yapici' if terim > 1e-09 else 'yikici' if terim < -1e-09 else 'yok'\n    return {'kuantum': round(kuantum, 6), 'klasik': round(klasik, 6), 'girisim_terimi': round(terim, 6), 'tur': tur}", 'referans', 'exec'), _REF)
_t, _g = _ff(iki_yol_girisimi, _REF['iki_yol_girisimi'], ([0.5, 0.0], [-0.5, 0.0]), tohum=2629, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (iki_yol_girisimi): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def iki_yol_girisimi(a1, a2):
    for a in (a1, a2):
        if not isinstance(a, list) or len(a) != 2:
            raise ValueError("genlik [gerçek, sanal] biçiminde 2 öğeli liste olmalı")
        for x in a:
            if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
                raise ValueError("genlik bileşenleri sonlu sayı olmalı")
    z1, z2 = complex(a1[0], a1[1]), complex(a2[0], a2[1])
    kuantum = abs(z1 + z2) ** 2
    klasik = abs(z1) ** 2 + abs(z2) ** 2
    terim = 2 * (z1 * z2.conjugate()).real
    tur = "yapici" if terim > 1e-9 else ("yikici" if terim < -1e-9 else "yok")
    return {"kuantum": round(kuantum, 6), "klasik": round(klasik, 6), "girisim_terimi": round(terim, 6), "tur": tur}
```

```hint
Python'un `complex` türü işini kolaylaştırır: `complex(re, im)`, `.conjugate()`, `abs(z) ** 2`.
```
:::

::: gorev 2 · Decoherence Bütçesi: Kaç Kapı Sığar?
Basit bir saf faz kaybı (dephasing) modelinde süperpozisyonun faz bilgisi (yoğunluk matrisinin köşegen dışı öğesi) $e^{-t/T_2}$ ile söner. Bir algoritma, eşevrelilik bitmeden kaç kapı uygulayabileceğine göre sınırlanır. `koherans_butcesi(T2_us, kapi_ns, sure_us)` işlevini yaz.

**Çıktı:**
- `"kalan_koherans"`: $e^{-\text{sure}/T_2}$, `round(·, 6)`.
- `"kapi_sayisi"`: $T_2$ süresine sığan kapı sayısı, $\lfloor T_2 \cdot 1000 / \text{kapı} \rfloor$ (µs → ns).
- `"yuzde_99_icin_kapi"`: eşevrelilik 0.99'un altına düşmeden sığan kapı sayısı, $\lfloor -\ln(0.99) \cdot T_2 \cdot 1000 / \text{kapı} \rfloor$.

Kayan nokta hatası tam bölünen değerleri bir aşağı yuvarlamasın diye `floor`'dan önce değeri `round(·, 9)` ile yuvarla. Girdiler sonlu sayı olmalı (`bool` değil); `T2_us` ve `kapi_ns` pozitif, `sure_us` negatif olmamalı. Değilse `ValueError`.

```starter
import math

def koherans_butcesi(T2_us, kapi_ns, sure_us):
    # KUSURLU BAŞLANGIÇ: birimleri karıştırıyor (µs ile ns), %99 eşiğini hesaplamıyor
    return {"kalan_koherans": round(math.exp(-sure_us / T2_us), 6), "kapi_sayisi": int(T2_us / kapi_ns), "yuzde_99_icin_kapi": 0}

print(koherans_butcesi(100, 25, 50))
```

```test
fn = need("koherans_butcesi")
eq(fn(100, 25, 50), {"kalan_koherans": 0.606531, "kapi_sayisi": 4000, "yuzde_99_icin_kapi": 40}, "süperiletken qubit: T2 100 µs, kapı 25 ns, 50 µs sonra e^-0.5")
eq(fn(1e6, 1e5, 0), {"kalan_koherans": 1.0, "kapi_sayisi": 10000, "yuzde_99_icin_kapi": 100}, "iyon tuzağı: T2 1 s, kapı 100 µs; t = 0'da eşevrelilik tam")
eq(fn(0.3, 0.1, 0.3)["kapi_sayisi"], 3000, "0.3·1000/0.1 kayan noktada 2999.999…; round(·, 9) ile 3000")
eq(fn(0.3, 0.1, 0.3)["kalan_koherans"], 0.367879, "t = T2'de 1/e")
eq(fn(100, 25, 50)["yuzde_99_icin_kapi"] < fn(100, 25, 50)["kapi_sayisi"], True, "%99 eşiği çok daha az kapıya izin verir")
eq(fn(50, 30, 0)["kapi_sayisi"], 1666, "50 000 / 30 = 1666.67: aşağı yuvarlanır")
raises(ValueError, fn, 0, 25, 1)
raises(ValueError, fn, 100, 0, 1)
raises(ValueError, fn, 100, 25, -1)
raises(ValueError, fn, True, 25, 1)
raises(ValueError, fn, 100, float("inf"), 1)
raises(ValueError, fn, "100", 25, 1)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef koherans_butcesi(T2_us, kapi_ns, sure_us):\n    for v in (T2_us, kapi_ns, sure_us):\n        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):\n            raise ValueError('sonlu sayı gerekli')\n    if T2_us <= 0 or kapi_ns <= 0 or sure_us < 0:\n        raise ValueError('T2 ve kapı süresi pozitif, süre negatif olmayan olmalı')\n    oran = T2_us * 1000 / kapi_ns\n    return {'kalan_koherans': round(math.exp(-sure_us / T2_us), 6), 'kapi_sayisi': math.floor(round(oran, 9)), 'yuzde_99_icin_kapi': math.floor(round(-math.log(0.99) * oran, 9))}", 'referans', 'exec'), _REF)
_t, _g = _ff(koherans_butcesi, _REF['koherans_butcesi'], (100, 25, 50), tohum=2626, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (koherans_butcesi): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def koherans_butcesi(T2_us, kapi_ns, sure_us):
    for v in (T2_us, kapi_ns, sure_us):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError("sonlu sayı gerekli")
    if T2_us <= 0 or kapi_ns <= 0 or sure_us < 0:
        raise ValueError("T2 ve kapı süresi pozitif, süre negatif olmayan olmalı")
    oran = T2_us * 1000 / kapi_ns
    return {"kalan_koherans": round(math.exp(-sure_us / T2_us), 6),
            "kapi_sayisi": math.floor(round(oran, 9)),
            "yuzde_99_icin_kapi": math.floor(round(-math.log(0.99) * oran, 9))}
```

```hint
1 µs = 1000 ns. $-\ln(0.99) \approx 0.01005$: eşevreliliğin yalnız %1'ini harcamak için $T_2$'nin yaklaşık %1'i kadar süre vardır.
```
:::

::: gorev 3 · Yorum Değil Tehdit: Mosca Eşitsizliğiyle "Şimdi Topla, Sonra Çöz" Riski
Hangi yorum doğru olursa olsun güvenlik için önemli olan, şifreyi kıracak büyüklükte bir kuantum bilgisayarın (**CRQC**) ne zaman geleceğidir. Saldırgan şifreli trafiği bugün kaydedip yarın çözebilir (**Harvest Now, Decrypt Later**). **Mosca eşitsizliği:** verinin gizli kalması gereken süre $x$, post-kuantum kriptografiye geçiş süresi $y$ ve CRQC'ye kalan süre $z$ ise, $x + y > z$ olduğunda veri risk altındadır. `mosca_riski(saklama_yil, goc_yil, bugun_qubit, yillik_carpan, gereken_qubit)` işlevini yaz. $z$'yi kaba bir büyüme modeliyle tahmin et: qubit sayısı her yıl `yillik_carpan` katına çıkıyorsa $z = \log(\text{gereken} / \text{bugün}) / \log(\text{çarpan})$; bugün zaten yeterliyse $z = 0$.

**Çıktı:** `{"kalan_yil_z": z, "x_arti_y": x + y, "risk_var": x + y > z, "pay_yil": z - (x + y)}`; sayıları `round(·, 2)` ile yuvarla (`risk_var` yuvarlanmamış değerlerle karşılaştırılır).

Bütün girdiler sonlu sayı olmalı (`bool` değil); `saklama_yil` ve `goc_yil` negatif olmamalı, `bugun_qubit` ve `gereken_qubit` pozitif, `yillik_carpan` 1'den büyük olmalı. Değilse `ValueError`.

```starter
import math

def mosca_riski(saklama_yil, goc_yil, bugun_qubit, yillik_carpan, gereken_qubit):
    # KUSURLU BAŞLANGIÇ: göç süresini unutuyor, büyümeyi doğrusal sanıyor
    z = (gereken_qubit - bugun_qubit) / (bugun_qubit * (yillik_carpan - 1))
    return {"kalan_yil_z": round(z, 2), "x_arti_y": round(saklama_yil, 2), "risk_var": saklama_yil > z, "pay_yil": round(z - saklama_yil, 2)}

print(mosca_riski(10, 5, 105, 2, 1e6))
```

```test
fn = need("mosca_riski")
eq(fn(10, 5, 105, 2, 1e6), {"kalan_yil_z": 13.22, "x_arti_y": 15, "risk_var": True, "pay_yil": -1.78}, "105 qubit (Willow), her yıl ×2, ~1 milyon fiziksel qubit gerekir: 10 yıl gizli kalacak veri bugünden risk altında")
eq(fn(2, 1, 105, 2, 1e6)["risk_var"], False, "kısa ömürlü veri ve hızlı göç: risk yok")
eq(fn(2, 1, 105, 2, 1e6)["pay_yil"], 10.22, "10 yılı aşkın pay")
eq(fn(10, 5, 2e6, 2, 1e6)["kalan_yil_z"], 0.0, "bugün zaten yeterli qubit varsa z = 0")
eq(fn(25, 8, 105, 1.5, 1e6), {"kalan_yil_z": 22.6, "x_arti_y": 33, "risk_var": True, "pay_yil": -10.4}, "daha yavaş büyüme bile 25 yıllık sırları kurtarmaz")
eq(fn(0, 0, 105, 2, 1e6)["risk_var"], False, "saklanmayan veri için HNDL riski yok")
eq(fn(1, 1, 1000, 10, 100000), {"kalan_yil_z": 2.0, "x_arti_y": 2, "risk_var": False, "pay_yil": 0.0}, "x + y tam z'ye eşitse risk yok (eşitsizlik katı: >)")
raises(ValueError, fn, -1, 5, 105, 2, 1e6)
raises(ValueError, fn, 10, 5, 0, 2, 1e6)
raises(ValueError, fn, 10, 5, 105, 1, 1e6)
raises(ValueError, fn, 10, 5, 105, 2, 0)
raises(ValueError, fn, True, 5, 105, 2, 1e6)
raises(ValueError, fn, 10, float("nan"), 105, 2, 1e6)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile('import math\n\ndef mosca_riski(saklama_yil, goc_yil, bugun_qubit, yillik_carpan, gereken_qubit):\n    for v in (saklama_yil, goc_yil, bugun_qubit, yillik_carpan, gereken_qubit):\n        if isinstance(v, bool) or not isinstance(v, (int, float)) or (not math.isfinite(v)):\n            raise ValueError(\'sonlu sayı gerekli\')\n    if saklama_yil < 0 or goc_yil < 0 or bugun_qubit <= 0 or (gereken_qubit <= 0) or (yillik_carpan <= 1):\n        raise ValueError("süreler negatif olmamalı, qubit sayıları pozitif, çarpan 1\'den büyük olmalı")\n    z = 0.0 if bugun_qubit >= gereken_qubit else math.log(gereken_qubit / bugun_qubit) / math.log(yillik_carpan)\n    xy = saklama_yil + goc_yil\n    return {\'kalan_yil_z\': round(z, 2), \'x_arti_y\': round(xy, 2), \'risk_var\': xy > z, \'pay_yil\': round(z - xy, 2)}', 'referans', 'exec'), _REF)
_t, _g = _ff(mosca_riski, _REF['mosca_riski'], (10, 5, 105, 2, 1000000.0), tohum=2093, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (mosca_riski): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def mosca_riski(saklama_yil, goc_yil, bugun_qubit, yillik_carpan, gereken_qubit):
    for v in (saklama_yil, goc_yil, bugun_qubit, yillik_carpan, gereken_qubit):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError("sonlu sayı gerekli")
    if saklama_yil < 0 or goc_yil < 0 or bugun_qubit <= 0 or gereken_qubit <= 0 or yillik_carpan <= 1:
        raise ValueError("süreler negatif olmamalı, qubit sayıları pozitif, çarpan 1'den büyük olmalı")
    z = 0.0 if bugun_qubit >= gereken_qubit else math.log(gereken_qubit / bugun_qubit) / math.log(yillik_carpan)
    xy = saklama_yil + goc_yil
    return {"kalan_yil_z": round(z, 2), "x_arti_y": round(xy, 2), "risk_var": xy > z, "pay_yil": round(z - xy, 2)}
```

```hint
Üstel büyümede gereken yıl sayısı logaritmadır: $\text{bugün} \cdot c^z = \text{gereken}$. Gerçek tahminler qubit sayısının yanında hata oranlarını ve algoritmik iyileşmeleri de hesaba katar (kuantum-20).
```
:::

::: dusun
Sahnede bir dinleyici el kaldırdı: *"Hocam madem atomlar ve elektronlar aynı anda iki durumda (**Superposition**) olabiliyor, neden benim elimdeki kahve kupası veya masadaki laptop aynı anda hem masanın sağında hem solunda **Superposition** halinde durmuyor? Neden büyük cisimlerde kuantum etkilerini göremiyoruz?"*

Buna fizikte **Quantum Decoherence (Kuantum Eşevrelilik Kaybı)** denir. Kendi cümlelerinle **Decoherence** kavramını ve neden kuantum bilgisayarların $-273.135^\circ\text{C}$ ($15\text{ mK}$) sıcaklıkta, ışıktan ve manyetik alandan izole vakum tüplerinde saklandığını açıkla.
**İpucu:** "Ölçüm (**Measurement**)" yapmak için illa bir insanın gözüyle bakması gerekmez; havadaki tek bir hava molekülünün veya tek bir ısı fotonunun Qubit'e çarpması da çevre tarafından yapılan bir ölçümdür!
:::

::: anlat
### 3. Neden Kahve Kupası Superposition'da Durmaz? (Quantum Decoherence)

Az önce düşündüğün soru, kuantum fiziğinin en önemli köprüsüdür: **Quantum Decoherence**.
- Bir Qubit'in **Superposition** ($\alpha|0\rangle + \beta|1\rangle$) ve **Entanglement** özelliğini koruyabilmesi için çevreden **tamamen izole (Isolated)** olması gerekir. Bu saf kuantum haline **Coherence (Eşevrelilik)** denir.
- Kuantum mekaniğinde "Ölçüm (**Measurement**)", bilinçli bir insanın mikroskopla bakması demek değildir! Dış ortamdan gelen **tek bir ısı fotonunun**, **tek bir hava molekülünün** veya **kaçak bir elektromanyetik dalganın** Qubit'e çarpması, Qubit'in bilgisinin çevreye sızması demektir.
- Qubit çevreyle etkileştiği salisede, çevredeki trilyonlarca atomla **Entangled** olur ve kendi içindeki hassas faz ilişkisi (**Phase Coherence**) bozulur. Buna **Quantum Decoherence** denir!
- Masadaki kahve kupası saniyede katrilyonlarca hava molekülü ve ışık fotonuyla çarpıştığı için **Decoherence** süresi $10^{-40}$ saniyedir; yani kupa salisenin trilyonda birinde bile **Superposition**'da kalamaz, anında klasik dünyaya çöker.
- İşte Google, IBM gibi şirketlerin kuantum bilgisayarları altın avizeye benzeyen **Dilution Refrigerator** (Seyreltme Soğutucusu) içinde, uzay boşluğundan (2.7 K) yaklaşık 180 kat daha soğuk olan **15 Millikelvin ($-273.135^\circ\text{C}$)** sıcaklıkta tutmasının tek sebebi, ısı fotonlarını susturup süperiletken qubit'lerin uyum (**Coherence**) süresini yüzlerce mikrosaniye mertebesine çıkarabilmektir (iyon tuzaklarında saniyeler mümkündür)!
:::

::: anlat Sınır
Ders 'quantum' adının kökenini, kuantizasyonu, many-worlds ve Copenhagen yorumlarını ve decoherence'ı anlatır. Yorumlar arasındaki fark deneyle ayırt edilemez, çünkü hepsi aynı ölçüm olasılıklarını öngörür; hangisinin doğru olduğu fizikte açık bir sorudur. 'Paralel evrenlerdeki bilgisayarları kullanmak' bir benzetmedir: kuantum hızlanması genliklerin girişiminden (interference) gelir ve her dalın sonucu ayrı ayrı okunamaz. Decoherence klasik görünümün nedenini açıklar ama ölçüm probleminin tamamını çözdüğü konusunda uzlaşı yoktur. Görevler girişim terimini ve tek parametreli bir faz kaybı modelini hesaplatır: gerçek qubit'lerde enerji kaybı ($T_1$), faz kaybı ($T_2$) ve kapı hataları birlikte etkilidir; kaç kapı sığdığı yalnız $T_2$'ye değil, hata oranlarına ve hata düzeltmeye de bağlıdır (kuantum-06). Mosca görevi qubit sayısının sabit bir çarpanla üstel büyüdüğünü varsayan kaba bir modeldir; gerçek CRQC tahminleri hata oranlarına ve algoritmik iyileşmelere bağlıdır (ör. Gidney 2025, RSA-2048 için bir milyondan az gürültülü qubit) ve geniş belirsizlik taşır.

Kaynaklar: [Zurek 2003 - Decoherence, einselection, and the quantum origins of the classical](https://arxiv.org/abs/quant-ph/0105127), [Everett 1957 - "Relative State" Formulation of Quantum Mechanics](https://doi.org/10.1103/RevModPhys.29.454).
:::

::: ozet
- **Quantum (Quanta)**, Max Planck (1900) ve Albert Einstein (1905) tarafından keşfedilen, doğadaki enerji ve bilginin sürekli (**Continuous**) değil, bölünemez kesikli paketçikler (**Discrete Packets / Quanta**) halinde var olması gerçeğinden adını alır.
- Kuantum bilgisayarların $2^N$ durumu aynı anda işlemesi, **Copenhagen Interpretation**'a göre tek bir evrendeki **Hilbert Space** olasılık dalgalarının girişimi (**Wave Interference**); **Many-Worlds Interpretation**'a (Everett & David Deutsch) göre ise paralel evren dalları arasındaki girişim olarak yorumlanır.
- Makroskobik dünyada kuantum etkilerini görmememizin ve kuantum bilgisayarların mutlak sıfıra yakın soğutulmasının sebebi **Quantum Decoherence** (çevresel gürültünün Superposition'ı bozması) olgusudur.
:::
