---
id: kuantum-01
title: Klasik Bit'ten Qubit'e · Superposition, Complex Amplitudes ve Bloch Sphere
summary: Popüler bilimin "aynı anda hem 0 hem 1" klişesinin ötesinde gerçek Qubit matematiği: Dirac Bra-Ket notasyonu, Probability Amplitude, Born Rule, Relative Phase ve Bloch Sphere.
esleme: kuantum-02, kuantum-09
---

::: anlat 1. Popüler Bilim Yalanını Yıkarak Başlayalım: Qubit Nedir?
## Qubit ve probability amplitude

Bir qubit durumunu complex amplitude değerleriyle yazar, ölçüm olasılığını Born rule ile hesaplarız. Bu derste normalization ve phase farkını ayıracaksın. Bir state vectorun çok sayıda bileşen içermesi, ölçümde bütün bileşenlerin birlikte okunabileceği anlamına gelmez.

Bir konferansta kürsüye çıktığında salonu ilk 30 saniyede yakalayacağın cümle şudur:
> *"Gazetelerde ve popüler bilim videolarında kuantum bilgisayarlar için hep aynı cümleyi duyarsınız: 'Klasik bit ya 0 ya 1'dir, `Qubit` ise aynı anda hem 0 hem 1'dir, bu sayede bütün ihtimalleri aynı anda dener!' **Arkadaşlar, bu cümle yanlıştır.** Eğer `Qubit` sadece 'belirsiz bir 0 veya 1' olsaydı, onun adı kuantum bilgisayar değil, bozuk para atan olasılıksal bir klasik bilgisayar (`Probabilistic Classical Computer`) olurdu!"*

Peki gerçek fark nedir?

### 🪙 Benzetme: Havada Dönen Madeni Para vs Su Dalgası
- **Klasik Bit (`Classical Bit`):** Masanın üzerinde duran madeni paradır. Ya **Yazı ($0$)** ya da **Tura ($1$)** durumundadır.
- **Olasılıksal Klasik Bit (`Probabilistic Bit`):** Havaya atılıp elinin altında kapattığın paradır. Sen bakana kadar `%50` olasılıkla $0$, `%50` olasılıkla $1$'dir. Olasılıklar her zaman **$0$ ile $1$ arasında pozitif gerçek sayılardır ($p \in [0, 1]$)**. İki pozitif olasılığı topladığında birbirini asla sıfırlayamazlar!
- **Kuantum Bit (`Qubit`):** Bir su dalgası veya lazer ışını gibidir! Durumu olasılıklarla değil, **negatif ve karmaşık sayılar (`Complex Numbers`) alabilen `Probability Amplitude` (Olasılık Genliği)** değerleriyle tanımlanır. Dalgada tepe ($+$) ve çukur ($-$) üst üste geldiğinde nasıl birbirini yok ediyorsa (**`Destructive Interference` — Yıkıcı Girişim**), `Qubit` genlikleri de yanlış cevapları birbirine çarptırarak yok edebilir!

İşte kuantum bilgisayarın bütün gücü "her şeyi aynı anda denemek" değil, **genliklerin işaretlerini ($+$, $-$, $i$) kullanarak yanlış cevapları birbirine sildirmektir!**

**Kaynak ve sınır:** [IBM Quantum: temel quantum information](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information). Sayısal örnekler eğitim ölçeğindedir; gerçek quantum hardware, standart PQC ürünü veya ağ üzerindeki bir hedef üzerinde kabul testi yapılmaz.
:::

::: anlat 2. Dirac Bra-Ket Notasyonu ve Superposition Matematiği
Kuantum mekaniğinde durum vektörlerini göstermek için fizikçi Paul Dirac'ın icat ettiği **`Bra-Ket Notation` (`Dirac Notation`)** kullanılır:

- Klasik `"0"` durumu, iki boyutlu uzayda dikey bir birim vektör olan **$|0\rangle$ (`Ket 0`)** ile gösterilir:
$$|0\rangle = \begin{bmatrix} 1 \\ 0 \end{bmatrix}$$
- Klasik `"1"` durumu ise dikey birim vektör **$|1\rangle$ (`Ket 1`)** ile gösterilir:
$$|1\rangle = \begin{bmatrix} 0 \\ 1 \end{bmatrix}$$

Bir **`Qubit`**, bu iki temel durumun (`Computational Basis States`) karmaşık katsayılarla ($\alpha, \beta \in \mathbb{C}$) doğrusal birleşimi olan bir **`Superposition` (Süperpozisyon)** vektörüdür:

$$|\psi\rangle = \alpha |0\rangle + \beta |1\rangle = \begin{bmatrix} \alpha \\ \beta \end{bmatrix}$$

### 📏 `Born Rule` (Born Kuralı) ve `Wavefunction Collapse` (Ölçüm Çöküşü)
Doğa çok ilginç bir sansür uygular: Bir `Qubit` üzerinde işlem yaparken $\alpha$ ve $\beta$ genlikleri sürekli etkileşir; **fakat `Qubit`'i ölçtüğün (`Measurement`) anda `Superposition` anında çöker (`Wavefunction Collapse`)!** Ekranda asla $\alpha$ veya $\beta$ görmezsin; ekranda sadece klasik bir **$0$** veya **$1$** görürsün!

Peki ölçtüğümüzde hangi olasılıkla $0$, hangi olasılıkla $1$ çıkar? Max Born'un Nobel ödüllü **`Born Rule`** yasasına göre olasılık, genliğin mutlak değerinin karesidir:
- **$0$ ölçme olasılığı:** $P(0) = |\alpha|^2$
- **$1$ ölçme olasılığı:** $P(1) = |\beta|^2$
- Toplam olasılık her zaman %100 ($1$) olmak zorunda olduğundan (**`Normalization Condition`**):

$$|\alpha|^2 + |\beta|^2 = 1$$

```python
import cmath

def qubit_olc_olasiliklari(alpha, beta):
    p0 = round(abs(alpha) ** 2, 4)
    p1 = round(abs(beta) ** 2, 4)
    gecerli = abs((p0 + p1) - 1.0) < 1e-6
    return {"P(0)": p0, "P(1)": p1, "norm_gecerli_mi": gecerli}

# Örnek: |+⟩ durumu -> alpha = 1/√2, beta = 1/√2
s = 1 / (2 ** 0.5)
print("|+⟩ Durumu :", qubit_olc_olasiliklari(s, s))
# Örnek: Karmaşık fazlı durum -> alpha = 1/√2, beta = i/√2
print("|i⟩ Durumu :", qubit_olc_olasiliklari(s, 1j * s))
```
:::

::: anlat 3. Relative Phase (Bağıl Faz): |+⟩ ile |-⟩ Arasındaki Görünmez Fark
Şimdi kuantum bilgisayarları anlamak için en kritik soruya bakalım:
İki farklı `Qubit` hazırladığımızı düşün:
1. **Birinci `Qubit` ($|+\rangle$ durumu):**
$$|+\rangle = \frac{1}{\sqrt{2}}|0\rangle + \frac{1}{\sqrt{2}}|1\rangle$$
2. **İkinci `Qubit` ($|-\rangle$ durumu):**
$$|-\rangle = \frac{1}{\sqrt{2}}|0\rangle - \frac{1}{\sqrt{2}}|1\rangle$$

Bu iki `Qubit`'i hemen ölçersen ne görürsün?
- $|+\rangle$ durumunda: $P(0) = |1/\sqrt{2}|^2 = 0.50$, $P(1) = |1/\sqrt{2}|^2 = 0.50$.
- $|-\rangle$ durumunda: $P(0) = |1/\sqrt{2}|^2 = 0.50$, $P(1) = |-1/\sqrt{2}|^2 = 0.50$.

**Ölçüm olasılıkları birebir aynı (%50'ye %50)!** O halde aradaki **eksi işareti (`Relative Phase`)** ne işe yarıyor?
> **Cevap:** Tek başına ölçtüğünde eksi işaretini göremezsin; ama bu iki durumu bir sonraki kuantum kapısına (**`Hadamard Gate`**) soktuğunda $|+\rangle$ durumu **%100 kesinlikle $|0\rangle$** verirken, $|-\rangle$ durumu **%100 kesinlikle $|1\rangle$** verir!

Yani **`Relative Phase`**, `Qubit`'in dışarıdan bakınca görünmeyen ama bir sonraki kuantum kapısında dalgaların birbirini güçlendireceğini mi (`+`) yoksa yok edeceğini mi (`-`) belirleyen **gizli pusulasıdır!**
:::

::: anlat 4. Bloch Sphere (Bloch Küresi) ve n-Qubit Üstel Uzay Patlaması
Tek bir `Qubit`'in durumunu görselleştirmek için **`Bloch Sphere` (Bloch Küresi)** kullanılır:
- Kürenin **Kuzey Kutbu ($+Z$)** $|0\rangle$ durumudur.
- Kürenin **Güney Kutbu ($-Z$)** $|1\rangle$ durumudur.
- Klasik bir bit sadece Kuzey veya Güney kutbunda durabilir.
- Bir `Qubit` ise iki açı ($\theta$: enlem/olasılık oranı, $\phi$: boylam/`Relative Phase`) ile kürenin yüzeyindeki **sonsuz noktadan herhangi birinde** durabilir:

$$|\psi\rangle = \cos\left(\frac{\theta}{2}\right)|0\rangle + e^{i\phi}\sin\left(\frac{\theta}{2}\right)|1\rangle$$

### 🚀 Neden 300 Qubit Evrendeki Atom Sayısını Geçer? (`Hilbert Space Explosion`)
Tek bir `Qubit` 2 karmaşık sayı ($\alpha, \beta$) tutar. Peki $n$ tane `Qubit`'i bir araya getirdiğimizde sistemin durum uzayı (**`Hilbert Space`**) nasıl büyür?
- Klasik $n$ bitlik bir yazmaç (`Register`), her anda $2^n$ durumdan **yalnızca 1 tanesini** tutar ($n$ bit bilgi).
- Kuantum $n$ `Qubit`'lik bir sistem ise aynı anda **$2^n$ temel durumun tamamı için ayrı bir karmaşık genlik ($\alpha_0, \alpha_1, \dots, \alpha_{2^n-1}$)** taşır!

| Qubit Sayısı ($n$) | Durum Vektörü Boyutu ($2^n$) | Klasik Bilgisayarda Simüle Etmek İçin Gereken RAM (`Complex128`) |
| :---: | :---: | :--- |
| **$10\text{ Qubit}$** | $1.024$ genlik | $16\text{ Kilobyte}$ (Dizüstü bilgisayarda milisaniyede çalışır) |
| **$30\text{ Qubit}$** | $\approx 1\text{ Milyar}$ genlik | **$16\text{ Gigabyte RAM}$** |
| **$50\text{ Qubit}$** | $\approx 1.12 \times 10^{15}$ genlik | **$18\text{ Petabyte RAM}$** (Dünyanın en büyük süperbilgisayarının sınırı!) |
| **$300\text{ Qubit}$** | **$2^{300} \approx 10^{90}$ genlik** | **Gözlemlenebilir evrendeki toplam atom sayısından ($\approx 10^{80}$) daha fazla!** |

İşte ünlü fizikçi **Richard Feynman**'ın 1981'de kuantum bilgisayar fikrini ortaya atmasının sebebi budur: *"Doğa klasik değildir; eğer bir molekülün veya kuantum sisteminin davranışını simüle etmek istiyorsan, klasik bilgisayarın belleği üstel olarak ($2^n$) patlar. Doğayı ancak yine kuantum mekaniğiyle çalışan bir bilgisayarla simüle edebilirsin!"*
:::

::: tahmin Hilbert Space Boyutu ve Born Rule Hesabı
Bir kuantum sisteminde $n=10$ `Qubit` bulunuyor (durum uzayı boyutu $2^{10}$) ve tek bir `Qubit` $|\psi\rangle = 0.6|0\rangle - 0.8|1\rangle$ durumunda hazırlanmış. Bu `Qubit` ölçüldüğünde $1$ gelme olasılığı ($|-0.8|^2$) ve $10$ `Qubit`'lik uzayın toplam genlik sayısı nedir?

```python
genlik_sayisi = 2 ** 10
p1 = round(abs(-0.8) ** 2, 2)
print(f"Boyut: {genlik_sayisi} | P(1): {p1}")
```

???

```cikti
Boyut: 1024 | P(1): 0.64
```
$10$ `Qubit`'lik bir sistemin `Hilbert Space` boyutu $2^{10} = 1024$'tür. Genliği $-0.8$ olan $|1\rangle$ durumunun ölçülme olasılığı `Born Rule` gereği $|-0.8|^2 = 0.64$ (%64) olur (eksi işareti karesi alındığında pozitif olasılığa dönüşür).
:::

::: gorev 1 · Born Kuralı: Genliklerden Ölçüm Olasılıklarına
`born_olcum(genlikler)` işlevini yaz. `genlikler`, $n$ qubit'lik bir durumun $2^n$ genliğidir (sırası `|0…0⟩, |0…1⟩, …`); öğeler `int`, `float` ya da `complex` olabilir.

**Kurallar:**
1. Liste boş değilse, uzunluğu en az 2 olan bir 2 kuvvetiyse ve öğeler sonlu sayıysa (`bool` değil) devam et; aksi halde, ya da bütün genlikler 0 ise `ValueError`.
2. Toplam $\Sigma = \sum_i |\alpha_i|^2$. Born kuralına göre olasılık $p_i = |\alpha_i|^2 / \Sigma$ (durum normalize değilse önce normalize edilmiş sayılır).
3. Çıktı:
   - `"n_qubit"`: $n$;
   - `"toplam"`: $\Sigma$ (`round(·, 6)`);
   - `"normalize_mi"`: $|\Sigma - 1| \le 10^{-9}$;
   - `"olasiliklar"`: $p_i$ listesi (`round(·, 6)`);
   - `"en_olasi"`: en büyük olasılıklı durumun $n$ basamaklı ikili yazımı (eşitlikte **ilk** indeks), ör. `"01"`.

Bağıl faz olasılıkları değiştirmez: `[h, h]` ile `[h, -h]` aynı olasılıkları verir.

```starter
def born_olcum(genlikler):
    # KUSURLU BAŞLANGIÇ: genliğin karesini değil kendisini olasılık sayıyor (eksi ve karmaşık genlikte bozulur)
    return {"n_qubit": 1, "toplam": sum(genlikler), "normalize_mi": True, "olasiliklar": list(genlikler), "en_olasi": "0"}

print(born_olcum([0.6, -0.8]))
```

```test
import math
fn = need("born_olcum")
r = fn([0.6, -0.8])
eq(r["olasiliklar"], [0.36, 0.64], "eksi genliğin karesi pozitif olasılık verir")
eq(r["n_qubit"], 1, "2 genlik = 1 qubit")
eq(r["normalize_mi"], True, "0.36 + 0.64 = 1")
eq(r["en_olasi"], "1", "|1⟩ daha olası")
r2 = fn([0.5, 0.5j, -0.5, 0.5])
eq(r2["olasiliklar"], [0.25, 0.25, 0.25, 0.25], "karmaşık genlik |0.5i|² = 0.25")
eq(r2["n_qubit"], 2, "4 genlik = 2 qubit")
eq(r2["en_olasi"], "00", "eşitlikte ilk indeks, 2 basamakla")
r3 = fn([3, 4])
eq(r3["toplam"], 25.0, "normalize değil: 9 + 16")
eq(r3["normalize_mi"], False, "toplam 1 değil")
eq(r3["olasiliklar"], [0.36, 0.64], "olasılıklar normalize edilerek hesaplanır")
h = 1 / math.sqrt(2)
eq(fn([h, h])["olasiliklar"], fn([h, -h])["olasiliklar"], "bağıl faz ölçüm olasılığını değiştirmez")
eq(fn([0, 0, 0, 0, 0, 1, 0, 0])["en_olasi"], "101", "3 qubit: indeks 5 = 101")
raises(ValueError, fn, [1, 0, 0])
raises(ValueError, fn, [0, 0])
raises(ValueError, fn, [True, False])
raises(ValueError, fn, [1])
raises(ValueError, fn, [float("nan"), 1])
eq(fn([math.sqrt(1.0 + 7e-10), 0.0])["normalize_mi"], True, "1e-9 tolerans icinde normalize")
eq(fn([math.sqrt(1.0 + 1.5e-9), 0.0])["normalize_mi"], False, "1e-9 tolerans disinda normalize degil")
eq(fn([1.0, 1.0, 1.0, 0.0])["olasiliklar"][0], 0.333333, "6 basamak olasilik yuvarlamasi")
eq(fn([math.sqrt(1/3), math.sqrt(1/3)])["toplam"], 0.666667, "6 basamak toplam yuvarlamasi")

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import cmath\nimport math\n\ndef born_olcum(genlikler):\n    if not isinstance(genlikler, list) or len(genlikler) < 2 or len(genlikler) & len(genlikler) - 1:\n        raise ValueError('genlik sayısı en az 2 olan bir 2 kuvveti olmalı')\n    for a in genlikler:\n        if isinstance(a, bool) or not isinstance(a, (int, float, complex)) or (not cmath.isfinite(a)):\n            raise ValueError('genlikler sonlu sayı olmalı')\n    kareler = [float(abs(a)) ** 2 for a in genlikler]\n    toplam = sum(kareler)\n    if toplam == 0:\n        raise ValueError('bütün genlikler sıfır olamaz')\n    n = len(genlikler).bit_length() - 1\n    olas = [k / toplam for k in kareler]\n    en = max(range(len(olas)), key=lambda i: (olas[i], -i))\n    return {'n_qubit': n, 'toplam': round(toplam, 6), 'normalize_mi': abs(toplam - 1) <= 1e-09, 'olasiliklar': [round(p, 6) for p in olas], 'en_olasi': format(en, f'0{n}b')}", 'referans', 'exec'), _REF)
_t, _g = _ff(born_olcum, _REF['born_olcum'], ([0.6, -0.8],), tohum=1987, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (born_olcum): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import cmath
import math

def born_olcum(genlikler):
    if not isinstance(genlikler, list) or len(genlikler) < 2 or len(genlikler) & (len(genlikler) - 1):
        raise ValueError("genlik sayısı en az 2 olan bir 2 kuvveti olmalı")
    for a in genlikler:
        if isinstance(a, bool) or not isinstance(a, (int, float, complex)) or not cmath.isfinite(a):
            raise ValueError("genlikler sonlu sayı olmalı")
    kareler = [float(abs(a)) ** 2 for a in genlikler]
    toplam = sum(kareler)
    if toplam == 0:
        raise ValueError("bütün genlikler sıfır olamaz")
    n = len(genlikler).bit_length() - 1
    olas = [k / toplam for k in kareler]
    en = max(range(len(olas)), key=lambda i: (olas[i], -i))
    return {"n_qubit": n, "toplam": round(toplam, 6), "normalize_mi": abs(toplam - 1) <= 1e-9,
            "olasiliklar": [round(p, 6) for p in olas], "en_olasi": format(en, f"0{n}b")}
```

```hint
`abs(a) ** 2` gerçek, eksi ve karmaşık genlikte doğru çalışır. İkili yazım için `format(i, f"0{n}b")`.
```
:::

::: gorev 2 · Bağıl fazı Bloch koordinatlarında gör
`bloch_noktasi(alpha, beta)` işlevini yaz. Girdiler normalize bir saf qubit'in iki karmaşık genliğidir. Çıktı altı ondalık basamağa yuvarlanmış `(x, y, z)` demetidir. Kartezyen eksenler için `x = 2 * (alpha.conjugate() * beta).real`, `y = 2 * (alpha.conjugate() * beta).imag` ve `z = abs(alpha)**2 - abs(beta)**2` kullan. Başlangıç kodu yalnız ölçüm olasılığı farkını kullanır ve ekvatordaki durumları ayıramaz.

```starter
def bloch_noktasi(alpha, beta):
    return (0.0, 0.0, round(abs(alpha)**2 - abs(beta)**2, 6))
```
```solution
def bloch_noktasi(alpha, beta):
    carpit = alpha.conjugate() * beta
    return (
        round(2 * carpit.real, 6),
        round(2 * carpit.imag, 6),
        round(abs(alpha)**2 - abs(beta)**2, 6),
    )
```
```test
f = need("bloch_noktasi")
s = 2**-0.5
eq(f(1, 0), (0.0, 0.0, 1.0), "Kuzey kutbu")
eq(f(0, 1), (0.0, 0.0, -1.0), "Güney kutbu")
eq(f(s, s), (1.0, 0.0, 0.0), "Eşfazlı genlikler +X ekseninde")
eq(f(s, -s), (-1.0, 0.0, 0.0), "Ters faz -X ekseninde")
eq(f(s, 1j*s), (0.0, 1.0, 0.0), "Bağıl i fazı +Y ekseninde")
eq(f(1j*s, -s), (0.0, 1.0, 0.0), "Ortak i fazı noktayı değiştirmez")
eq(f(0.6, 0.8j), (0.0, 0.96, -0.28), "Farklı büyüklükler z bileşenini değiştirir")
eq(f(1/3, 2/3), (0.444444, 0.0, -0.333333), "x ve z 6 basamak yuvarlama")
eq(f(1/3, 2j/3), (0.0, 0.444444, -0.333333), "y ve z 6 basamak yuvarlama")
```
:::

::: anlat İki qubit ölçümünü karşılaştır
İlk görevdeki Born işlevine `[0.5, 0.5, 0.5, 0.5]` ve `[2**-0.5, 0, 0, 2**-0.5]` vektörlerini sırayla ver. Temel durum sırası `00, 01, 10, 11`. İlk durumda dört çıktı eşit olasılıklı, ikinci durumda yalnız `00` ve `11` eşit olasılıklı. İki durumda da ilk qubit için `0` olasılığı `1/2`. Ortak dağılımı karşılaştırmak, tek qubit ölçümünden görünmeyen korelasyonu ortaya çıkarır.
:::

::: anlat Sınır
Ders qubit'i, karmaşık genlikleri, Born kuralını, bağıl fazı ve Bloch küresini anlatır; görevler Born kuralını küçük durum vektörlerinde ve Bloch koordinatlarını tek qubit için hesaplatır, gerçek donanım ya da kuantum SDK'sı kullanılmaz. Bloch küresinin yüzeyi yalnız tek ve saf (pure) bir qubit'i gösterir; karışık durumlar kürenin içinde kalır, çok qubitli dolaşık durumlar küreyle gösterilemez. '300 qubit evrendeki atomlardan fazla bilgi tutar' cümlesi durum uzayının boyutunu anlatır; Holevo sınırı nedeniyle n qubit'ten ölçümle en fazla n klasik bit okunabilir. Gerçek qubit'ler decoherence ve kapı hatalarıyla çalışır; ders ideal, gürültüsüz durumları varsayar.

Kaynaklar: [Preskill 2018 - Quantum Computing in the NISQ era and beyond](https://arxiv.org/abs/1801.00862), [Rieffel ve Polak 2000 - An Introduction to Quantum Computing for Non-Physicists](https://arxiv.org/abs/quant-ph/9809016).
:::

