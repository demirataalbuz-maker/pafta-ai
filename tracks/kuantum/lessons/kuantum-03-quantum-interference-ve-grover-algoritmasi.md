---
id: kuantum-03
title: Quantum Interference ve Grover's Algorithm · Samanlıkta İğneyi √N Adımda Bulmak
summary: Kuantum algoritmalarının kalbi olan Constructive/Destructive Interference, Phase Kickback, Amplitude Amplification ve Grover's Algorithm'ın simetrik şifrelemeyi (AES/SHA) nasıl etkilediği.
esleme: kuantum-02, kuantum-04
---

::: anlat 1. Büyük Yanılgı: "Süperpozisyona Soktum, Hepsini Aynı Anda Hesapladım, Bitti!" Neden Çalışmaz?
## Grover amplitude amplification

Grover algoritması uygun bir oracle ile doğru adayların ölçülme olasılığını artırır. Bu derste oracle maliyetini arama iterasyonu sayısından ayıracak ve fazla iterasyonun başarı olasılığını neden düşürdüğünü inceleyeceksin. Asimptotik query hesabı, gerçek bir AES anahtarının bugün pratikte kırılabildiği anlamına gelmez.

Acemi bir kuantum meraklısı şöyle der:
> *"Çok kolay! $20\text{ Qubit}$ alırım ($2^{20} \approx 1.000.000$), hepsine `Hadamard ($H$)` kapısı uygularım. Artık $1.000.000$ şifrenin hepsi aynı anda `Superposition` içinde! Sonra şifre kontrol fonksiyonunu bir kez çalıştırırım, doğru cevabı alırım!"*

**Neden bu plan tamamen çöker?**
Çünkü $1.000.000$ durumun hepsi eşit süperpozisyondayken her birinin genliği $\frac{1}{\sqrt{1.000.000}} = \frac{1}{1000}$'dir. Sen devrenin sonunda ölçüm (`Measurement`) yaptığın anda `Superposition` çöker ve doğru şifreyi görme olasılığın:
$$P(x^*) = \left|\frac{1}{1000}\right|^2 = \frac{1}{1.000.000} \quad (\text{Yani milyon binde bir!})$$

Rastgele zar atmaktan **hiçbir farkı kalmadı!**

> **Temel Ders:** Bütün ihtimalleri süperpozisyona sokmak çok kolaydır; zor olan şey, ölçüm yapmadan önce **yanlış olan $999.999$ durumun genliğini $0$'a indirip (`Destructive Interference`), doğru olan tek durumun genliğini $1$'e yaklaştırmaktır (`Constructive Interference / Amplitude Amplification`)!**

**Kaynak ve sınır:** [IBM Quantum: quantum algorithms](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms). Sayısal örnekler eğitim ölçeğindedir; gerçek quantum hardware, standart PQC ürünü veya ağ üzerindeki bir hedef üzerinde kabul testi yapılmaz.
:::

::: anlat 2. Lov Grover'ın Dahi İcadı: Grover's Algorithm (1996)
1996 yılında Bell Labs araştırmacısı **Lov Grover**, sırasız bir veri tabanında (veya kriptografik bir `Hash` / `AES` anahtar uzayında) $N$ eleman arasından doğru olanı:
- Klasik bilgisayarların mecbur olduğu **$O(N)$** adım yerine,
- Sadece **$O(\sqrt{N})$** adımda bulan **`Grover's Algorithm`**'ı keşfetti!

$N = 1.000.000.000.000$ ($1\text{ Trilyon}$) şifre adayı varsa:
- **Klasik Bilgisayar (`Brute-Force`):** Ortalama **$500\text{ Milyar}$** deneme yapmak zorundadır.
- **Kuantum Bilgisayar (`Grover's Algorithm`):** Sadece **$\frac{\pi}{4}\sqrt{10^{12}} \approx \mathbf{785.398}$** adımda doğru şifreyi **%100'e yakın kesinlikle** ekrana çıkarır!

### 🌊 Benzetme: Gürültülü Odada Fısıltıyı Büyütmek (`Amplitude Amplification`)
Grover algoritması her adımda (**`Grover Iteration`**) iki basit ayna yansıması yapar:

1. **Adım A — `Phase Oracle` (Doğru Cevabın İşaretini Ters Çevir):**
   - `Oracle` (şifre kontrol devresi), doğru şifre $x^*$ hangisiyse onun olasılığına dokunmaz ama **genliğinin önüne bir eksi işareti koyar (`Phase Kickback`: $\alpha_{x^*} \to -\alpha_{x^*}$)**.
   - Sanki düz bir su yüzeyinde sadece doğru cevabın olduğu noktada aşağı doğru bir çukur açmışsındır!
2. **Adım B — `Diffusion Operator` (`Inversion About the Mean` — Ortalamaya Göre Yansıtma):**
   - Bütün genliklerin ortalaması ($\mu$) hesaplanır ve her genlik bu ortalamanın üzerinden ayna gibi simetrik yansıtılır:
   $$\alpha_i \leftarrow 2\mu - \alpha_i$$
   - Yanlış cevaplar ortalamanın biraz üstünde olduğu için yansıyınca **küçülür**; doğru cevap ise eksi işaretli (ortalamanın çok altında) olduğu için ortalamanın üstüne katlanarak **devasa biçimde büyür!**

```python
import math

# 16 elemanlı (4-Qubit) bir uzayda Grover Amplitude Amplification simülasyonu
N = 16
hedef = 7  # Aradığımız gizli anahtar indisi
genlikler = [1.0 / math.sqrt(N)] * N  # Başlangıç: Eşit Superposition (Her biri 0.25, olasılık %6.25)

for adim in range(1, 4):
    # 1. Phase Oracle: Hedef durumun fazını ters çevir (+ -> -)
    genlikler[hedef] = -genlikler[hedef]
    # 2. Diffusion (Inversion About the Mean): a_i = 2 * ortalama - a_i
    ort = sum(genlikler) / N
    genlikler = [2 * ort - a for a in genlikler]
    hedef_olasilik = round((genlikler[hedef] ** 2) * 100, 1)
    print(f"{adim}. Grover Adimi Sonrasi Dogru Anahtar Olasiligi: %{hedef_olasilik}")
```
Şu çıktının güzelliğine bak: Başlangıçta doğru cevabı bulma şansımız sadece `%6.25` iken, **1. adımda `%47.3`'e, 2. adımda `%90.8`'e, 3. adımda ise `%96.1`'e** fırlıyor!
:::

::: anlat 3. Fazla Döndürürsen Ne Olur? (Grover Over-Rotation / Soufflé Problem)
Grover iterasyonunu gereğinden fazla artırmak başarı probability değerini düşürebilir:

`Grover's Algorithm` hakkında konferansta söyleyebileceğin çok havalı bir teknik detay vardır: **Grover algoritmasını gereğinden fazla çalıştırırsan doğru cevap tekrar kaybolur!**

Buna **`The Soufflé Problem` (Sufle Problemi)** denir:
- Fırındaki sufleyi erken çıkarırsan pişmemiştir, tam vaktinde çıkarırsan kabarmıştır, ama fırında fazla tutarsan tekrar söner!
- Geometrik olarak her `Grover Iteration`, durum vektörünü doğru cevaba doğru sabit bir $\theta \approx \frac{2}{\sqrt{N}}$ açısı kadar döndürür.
- Tam **$\approx \frac{\pi}{4}\sqrt{N}$** adımda vektör $|x^*\rangle$ ekseninin tam üzerine ($\approx 90^\circ$) gelir ve olasılık `%100` olur. Eğer durmayıp döndürmeye devam edersen $90^\circ$'yi geçip tekrar yanlış cevaplara doğru uzaklaşmaya başlar!
:::

::: anlat 4. Siber Güvenlik Etkisi: Grover Algoritması AES ve SHA-256'yı Kırar mı?
Şimdi siber güvenlik dünyasındaki en önemli soruya gelelim:
*"Kuantum bilgisayarlar çıktığında `AES` şifrelemesi ve `SHA-256 / SHA-3` özet fonksiyonları çöp mü olacak?"*

**Hayır! Simetrik kriptografi çökmez, sadece anahtar boyutu yarıya iner:**
- Klasik dünyada **`AES-128`** kırmak için $2^{128}$ işlem gerekir (imkansızdır).
- Kuantum dünyada `Grover's Algorithm` bu karekök hızlanmasıyla `AES-128`'i $\sqrt{2^{128}} = \mathbf{2^{64}}$ kuantum adımına indirir (tehlikeli sınıra yaklaşır!).
- Peki çözüm nedir? Simetrik anahtarı iki katına çıkarmak: **`AES-256`**, Grover'a karşı da yaklaşık `2^128` adımlık bir arama ister. Özet işlevlerinde önimge araması için aynı hesap geçerlidir: `SHA-256`'nın önimgesi Grover'la yaklaşık `2^128` adım ister. Çıktısı daha uzun olan `SHA-384 / SHA-512` bu payı büyütür; çarpışma direnci gibi başka özellikler için ek pay isteyen sistemler bu yüzden onları seçebilir.
- Çünkü `Grover` algoritması `AES-256` karşısında $\sqrt{2^{256}} = \mathbf{2^{128}}$ adıma ihtiyaç duyar ki $2^{128}$ ardışık kuantum kapısını çalıştırmak evrenin yaşı kadar sürer!

> **Kısa Kural:** `Grover's Algorithm` yapısız arama (`Unstructured Search`) yaptığı için sadece **karesel ($\sqrt{N}$)** hızlanma sağlar; bu yüzden **`AES-256` ve `SHA-256` / `SHA-384` / `SHA-512` için önerilen düzeltme algoritmayı değiştirmek değil, yeterli uzunluk seçmektir** (Grover yaklaşık `2^(n/2)`). Asıl kıyamet bir sonraki derste göreceğimiz `RSA` ve `ECC` (Açık Anahtarlı Kriptografi) tarafında kopacaktır!
:::

::: tahmin Grover Algoritmasının AES-128 ve AES-256 Üzerindeki Etkisi
Bir şifreleme algoritmasının klasik güvenlik seviyesi $k$ bit ise ($2^k$ arama uzayı), `Grover's Algorithm` karşısındaki etkin kuantum güvenlik seviyesi $\log_2(\sqrt{2^k}) = k / 2$ bittir. Aşağıdaki kodun çıktısı nedir?

```python
aes128_kuantum_bit = 128 // 2
aes256_kuantum_bit = 256 // 2
print(f"AES-128 Kuantum Guvenligi: 2^{aes128_kuantum_bit} | AES-256 Kuantum Guvenligi: 2^{aes256_kuantum_bit}")
```

???

```cikti
AES-128 Kuantum Guvenligi: 2^64 | AES-256 Kuantum Guvenligi: 2^128
```
`Grover's Algorithm` arama uzayının karekökünü ($\sqrt{2^k} = 2^{k/2}$) aldığı için `AES-128`'in güvenliği $2^{64}$ seviyesine düşerken, `AES-256`'nın güvenliği kırılması imkansız olan $2^{128}$ seviyesinde kalır.
:::

::: gorev 1 · Grover İterasyonu: Oracle ve Ortalamaya Göre Yansıtma
`grover_iterasyonlari(n_qubit, hedef, adim)` işlevini yaz. $N = 2^n$ durumun hepsi eşit genlikle ($1/\sqrt{N}$) başlar. Her Grover iterasyonu:
1. **Oracle:** hedefin genliğinin işaretini çevir ($\alpha_{x^*} \to -\alpha_{x^*}$).
2. **Diffusion:** ortalama $\mu$'yü hesapla, her genliği $\alpha_i \leftarrow 2\mu - \alpha_i$ yap.

Her iterasyondan sonra hedefi ölçme olasılığını ($\alpha_{x^*}^2$) kaydet.

**Kurallar:** `n_qubit` 1–10 arası, `hedef` $0 \le x^* < N$, `adim` $\ge 0$ tam sayı olmalı (`bool` değil); değilse `ValueError`.

**Çıktı:** `"N"`, `"olasiliklar"` (her iterasyon sonrası, `round(·, 4)`), `"optimal_adim"` ($\lfloor \frac{\pi}{4}\sqrt{N} \rfloor$), `"son_genlikler"` (`round(·, 6)`).

Dersteki 16 elemanlı örnekte olasılık 3 iterasyonda %47.3 → %90.8 → %96.1 olur. $N = 4$'te ise tek iterasyon hedefi kesin bulur, ikinci iterasyon onu yeniden kaybettirir (fazla döndürme).

```starter
def grover_iterasyonlari(n_qubit, hedef, adim):
    # KUSURLU BAŞLANGIÇ: genlikleri hiç değiştirmiyor, olasılık hep 1/N kalıyor
    N = 2 ** n_qubit
    return {"N": N, "olasiliklar": [round(1 / N, 4)] * adim, "optimal_adim": 0, "son_genlikler": [round(N ** -0.5, 6)] * N}

print(grover_iterasyonlari(4, 5, 3))
```

```test
fn = need("grover_iterasyonlari")
r = fn(4, 5, 3)
eq(r["olasiliklar"], [0.4727, 0.9084, 0.9613], "N = 16: dersteki örnek")
eq(r["optimal_adim"], 3, "floor(π/4 · 4) = 3")
eq(r["N"], 16, "2^4")
r2 = fn(2, 3, 2)
eq(r2["olasiliklar"], [1.0, 0.25], "N = 4: bir adımda kesin, ikinci adımda fazla döndürme")
eq(fn(2, 3, 1)["son_genlikler"], [0.0, 0.0, 0.0, 1.0], "N = 4, 1 adım: yanlışlar tam sıfırlanır")
eq(fn(1, 0, 1)["olasiliklar"], [0.5], "N = 2: Grover yardımcı olmaz")
eq(fn(1, 0, 1)["optimal_adim"], 1, "floor(π/4 · √2) = 1")
eq(fn(3, 7, 0)["olasiliklar"], [], "0 adım")
eq(fn(3, 7, 0)["son_genlikler"], [0.353553] * 8, "başlangıç: 1/√8")
raises(ValueError, fn, 0, 0, 1)
raises(ValueError, fn, 11, 0, 1)
raises(ValueError, fn, 2, 4, 1)
raises(ValueError, fn, 2, 1, -1)
raises(ValueError, fn, 2, True, 1)

# farksal tarama (örnek çözümden derlenen referans)
import sys as _sys
from pathlib import Path as _Yol
_sys.path.insert(0, str(_Yol(ok.__func__.__code__.co_filename).resolve().parent))
from ai_fark_fuzz import fark_fuzz as _ff
_REF = {}
exec(compile("import math\n\ndef grover_iterasyonlari(n_qubit, hedef, adim):\n    for v in (n_qubit, hedef, adim):\n        if isinstance(v, bool) or not isinstance(v, int):\n            raise ValueError('n_qubit, hedef, adim tam sayı olmalı')\n    if not 1 <= n_qubit <= 10:\n        raise ValueError('n_qubit 1 ile 10 arasında olmalı')\n    N = 2 ** n_qubit\n    if not 0 <= hedef < N or adim < 0:\n        raise ValueError('0 <= hedef < N ve adim >= 0 olmalı')\n    a = [1 / math.sqrt(N)] * N\n    olas = []\n    for _ in range(adim):\n        a[hedef] = -a[hedef]\n        mu = sum(a) / N\n        a = [2 * mu - x for x in a]\n        olas.append(round(a[hedef] ** 2, 4))\n    return {'N': N, 'olasiliklar': olas, 'optimal_adim': math.floor(math.pi / 4 * math.sqrt(N)), 'son_genlikler': [round(x, 6) for x in a]}", 'referans', 'exec'), _REF)
_t, _g = _ff(grover_iterasyonlari, _REF['grover_iterasyonlari'], (4, 5, 3), tohum=3087, en_cok=600, mod='tam', butce='oto')
ok(_t, "farksal tarama (grover_iterasyonlari): örnek çözümden derlenen referansla aynı sonuç ve aynı ValueError" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```

```solution
import math

def grover_iterasyonlari(n_qubit, hedef, adim):
    for v in (n_qubit, hedef, adim):
        if isinstance(v, bool) or not isinstance(v, int):
            raise ValueError("n_qubit, hedef, adim tam sayı olmalı")
    if not (1 <= n_qubit <= 10):
        raise ValueError("n_qubit 1 ile 10 arasında olmalı")
    N = 2 ** n_qubit
    if not (0 <= hedef < N) or adim < 0:
        raise ValueError("0 <= hedef < N ve adim >= 0 olmalı")
    a = [1 / math.sqrt(N)] * N
    olas = []
    for _ in range(adim):
        a[hedef] = -a[hedef]
        mu = sum(a) / N
        a = [2 * mu - x for x in a]
        olas.append(round(a[hedef] ** 2, 4))
    return {"N": N, "olasiliklar": olas, "optimal_adim": math.floor(math.pi / 4 * math.sqrt(N)),
            "son_genlikler": [round(x, 6) for x in a]}
```

```hint
Oracle'dan sonra ortalamayı yeniden hesapla; yansıtma tüm genliklere aynı anda uygulanır (yeni liste oluştur).
```
:::

::: anlat Sınır
Ders Grover'ın genlik büyütmesini, fazla döndürme sorununu ve simetrik şifrelere etkisini anlatır; görev Grover iterasyonunu doğrudan genlik vektörü üzerinde hesaplatır, kapı düzeyinde bir devre ve tersinir oracle kurulmaz. √N hızlanması oracle çağrı sayısı içindir; AES için gerçek bir anahtar arama oracle'ı binlerce mantıksal qubit ve çok derin devre ister, hata düzeltme maliyeti kazancın büyük kısmını yer. Grover paralelleştirmeye kötü ölçeklenir: k makine yalnız √k kat hızlanma verir. Çözüm sayısı bilinmiyorsa optimal iterasyon sayısı da bilinmez; kuantum sayma ya da rastgele iterasyon sayısı gerekir. Bu nedenlerle AES-256 Grover'a karşı yeterli sayılır.

Kaynaklar: [Grover 1996 - A fast quantum mechanical algorithm for database search](https://arxiv.org/abs/quant-ph/9605043), [Boyer vd. 1996 - Tight bounds on quantum searching](https://arxiv.org/abs/quant-ph/9605034).
:::

