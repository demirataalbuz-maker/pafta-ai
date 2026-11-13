---
id: kuantum-29
title: "Kuantum Bilgisayar Ne Yapar, Ne Yapamaz? · En Yaygın Beş Yanlış"
summary: "Ölçümün neden tek bir sonuç verdiğini, kuantum hızlanmanın hangi problemlerde ve ne kadar olduğunu ve bir kuantum durumundan ne kadar bilgi okunabildiğini hesapla; beş yaygın yanlışı sayılarla düzelt ve iki dakikada anlat."
track: kuantum
order: 29
---

::: anlat 1. Soru: "Kuantum bilgisayarın olayı ne?"
Bu soruya verilen popüler cevapların çoğu yanlıştır ve yanlışlar hep aynıdır. Bir salonda ya da bir yöneticiyle konuşurken karşına çıkacak beş tanesi:

| # | Yaygın yanlış | Doğrusu | Görev |
|---|---|---|---|
| 1 | "Bütün cevapları aynı anda dener ve doğrusunu söyler." | Ölçüm tek bir sonuç verir; hesaplama doğru cevabın olasılığını **girişimle** büyütür | 1 |
| 2 | "Her şeyi çok daha hızlı yapar." | Hızlanma probleme bağlıdır: bazılarında üstel, aramada yalnız karesel, çoğunda hiç | 2 |
| 3 | "`n` qubit `2ⁿ` veriyi saklar; devasa bir bellek." | `2ⁿ` genlik vardır ama ölçümle en çok `n` bit okunur | 3 |
| 4 | "Bütün şifreleri kırar." | Belirli açık anahtarlı sistemleri (`RSA`, eliptik eğri) kırar; simetrik şifreleri yalnız zayıflatır | Anlatım |
| 5 | "Yakında dizüstü bilgisayarın yerini alır." | Belirli problemler için özel bir hızlandırıcıdır; klasik bilgisayarın yerine geçmez | Anlatım |

> [!NOT]
> Görevler küçük durum vektörleri ve adım sayısı formülleriyle çalışır; bir kuantum donanımı ya da simülatörü çalıştırılmaz. Algoritmaların kendisi `kuantum-03` (Grover), `kuantum-04` (Shor) ve `kuantum-12` derslerindedir; bu ders onları **anlatmayı** öğretir.
:::

::: anlat 2. Üç yanlışın arkasındaki fizik
**Yanlış 1: "Hepsini aynı anda dener."** `n` qubit'lik bir kayıt, $2^n$ olası sonucun her biri için bir **genlik** (`amplitude`) taşır; genlik karmaşık bir sayıdır. Bu yüzden "hepsini aynı anda tutuyor" demek cazip gelir. Ama ölçtüğünde yalnız **bir** sonuç görürsün ve o sonucun olasılığı genliğinin mutlak değerinin karesidir (`Born` kuralı):

$$P(x) = \frac{\lvert a_x \rvert^2}{\sum_y \lvert a_y \rvert^2}$$

Bütün sonuçlar eşit genlikteyse ölçüm rastgele bir cevap verir; bu, zar atmaktan farksızdır. Kuantum algoritmasının hüneri, yanlış cevapların genliklerini birbirini **götürecek**, doğru cevabınkini güçlendirecek biçimde düzenlemektir (`interference`). Genlikler negatif ya da karmaşık olabildiği için birbirini yok edebilir; olasılıklar bunu yapamaz. Hesaplama "bütün cevaplara bakmak" değil, "yanlışları söndürmek"tir ve her problemde böyle bir düzen kurulamaz.

**Yanlış 2: "Her şeyi hızlandırır."** Bilinen hızlanmalar üç sınıftadır:

| Problem | Klasik | Kuantum | Hızlanma |
|---|---|---|---|
| Yapısız arama (`Grover`) | $\sim N/2$ deneme | $\sim \frac{\pi}{4}\sqrt{N}$ adım | Karesel |
| Çarpanlara ayırma (`Shor`) | Alt-üstel | Polinom | Üstele yakın |
| Kuantum sistemlerinin benzetimi | Üstel | Polinom | Üstel |
| Sıralama, e-posta, video, çoğu günlük iş | — | — | Bilinen bir hızlanma yok |

Karesel hızlanma büyük görünür ama üstel değildir: $2^{128}$ olasılığı aramak yine $2^{64}$ adım ister. Ayrıca her kuantum adımı klasik bir adımdan çok daha yavaş ve pahalıdır; küçük problemlerde klasik bilgisayar kazanır.

**Yanlış 3: "Devasa bir bellek."** 50 qubit'in durumunu klasik bir bilgisayarda saklamak için $2^{50}$ karmaşık sayı gerekir: yaklaşık 18 petabayt. Ama bu bilgiyi **okuyamazsın**. `Holevo` sınırı, `n` qubit'ten ölçümle en çok `n` klasik bit bilgi çıkarılabileceğini söyler. Kuantum durumu büyük bir veritabanı değil, hesaplama sırasında kullanılan ve sonunda tek bir kısa cevaba çöken bir ara kaynaktır.
:::

::: anlat 3. Diğer iki yanlış
**Yanlış 4: "Bütün şifreleri kırar."** Yeterince büyük ve hata düzeltmeli bir kuantum bilgisayar (`CRQC`), güvenliği çarpanlara ayırmaya ya da ayrık logaritmaya dayanan sistemleri kırar: `RSA`, `Diffie-Hellman`, eliptik eğri imzaları. Bunlar bugünkü internetin anahtar değişimi ve imza altyapısıdır; tehdit gerçektir.

Ama simetrik şifrelerde (`AES`) anahtar araması ve özet işlevlerinde (`SHA-2`, `SHA-3`) `preimage` araması için bilinen en iyi genel kuantum saldırısı Grover'dır ve yalnız karesel hızlanma verir: 256 bitlik bir anahtarın güvenliği kabaca 128 bite iner; bu hâlâ kırılamaz. Çare anahtarı uzatmaktır. Özet işlevlerinde `collision` bulmak ayrı bir problemdir: klasik doğum günü saldırısı $n$ bitlik çıktıda zaten $2^{n/2}$ deneme ister, Brassard–Høyer–Tapp algoritması bunu ideal sorgu modelinde $2^{n/3}$ sorguya indirir. Bu karesel değil, daha küçük bir kazançtır ve aynı büyüklükte kuantum belleği ister; bu yüzden pratikteki üstünlüğü tartışmalıdır. Görev 2 yalnız anahtar aramasını hesaplar. Açık anahtarlı sistemler içinse kuantum saldırısına dayanıklı olduğu düşünülen yenileri standartlaştırılmıştır (`ML-KEM`, `ML-DSA`, `SLH-DSA`; bkz. `kuantum-05`, `kuantum-21`, `kuantum-22`).

Bugün için asıl risk "şimdi topla, sonra çöz"dür: bugün kaydedilen şifreli trafik, yıllar sonra bir CRQC ile açılabilir. Uzun süre gizli kalması gereken veri için geçiş **şimdi** başlar.

**Yanlış 5: "Yakında her şeyin yerini alır."** Kuantum bilgisayar genel amaçlı bir makine değil, belirli problem sınıfları için bir hızlandırıcıdır; bir GPU'nun CPU'nun yerine geçmemesi gibi. Bugünkü cihazlar gürültülüdür: qubit'ler çok kısa sürede bozulur (`decoherence`) ve her işlem hata ekler. Yararlı büyük hesaplar hata düzeltme ister ve bir **mantıksal** qubit için yüzlerce ya da binlerce **fiziksel** qubit gerekir (bkz. `kuantum-06`). Ne zaman olacağı konusunda uzmanlar uzlaşmış değildir; kesin bir tarih veren her cümle bir tahmindir (bkz. `kuantum-30`).
:::

::: tahmin Eşit genlikte ölçüm ne verir?
İki qubit'lik bir kayıt dört sonucun hepsinde eşit genlik taşıyor. Sonra bir algoritma doğru cevabın (`10`) genliğini büyütüyor. Olasılıklar ne yazdırılır?

```python
def olasiliklar(genlikler):
    toplam = sum(abs(a) ** 2 for a in genlikler)
    return [round(abs(a) ** 2 / toplam, 3) for a in genlikler]

print(olasiliklar([0.5, 0.5, 0.5, 0.5]))
print(olasiliklar([0.1, 0.1, 0.98, 0.1]))
```

???

```cikti
[0.25, 0.25, 0.25, 0.25]
[0.01, 0.01, 0.97, 0.01]
```
İlk durumda kayıt "bütün cevapları tutuyor", ama ölçersen dörtte bir olasılıkla rastgele birini görürsün: hiçbir şey öğrenmedin. İkinci durumda algoritma yanlış cevapların genliklerini küçültmüş, doğru cevabınkini büyütmüştür; ölçüm %97 olasılıkla `10` verir. Kuantum hesaplamanın işi süperpozisyonu kurmak değil, ölçümden **önce** genlikleri doğru cevaba yığmaktır.
:::

::: gorev 1 · Ölçüm dağılımı (Born kuralı)
`olcum_dagilimi(genlikler)` işlevini yaz.

- `genlikler`: uzunluğu 2'nin kuvveti olan (1, 2, 4, 8, ...) boş olmayan liste; öğeler `int`, `float` ya da `complex` (`bool` kabul edilmez). Hepsi sıfır olamaz.
- Olasılık: `|a|² / Σ|a|²` (durum normalleştirilmemiş olabilir).
- Dönüş: `{'qubit': n, 'olasiliklar': {ikili etiket: olasılık}, 'en_olasi': etiket}`. Etiket, indeksin `n` basamaklı ikili yazımıdır (`n = 0` için boş dizgi yerine `'0'` kullanma; tek öğeli listede etiket `''` olur). Olasılıklar 9 basamağa yuvarlanır; `en_olasi`, eşitlikte küçük indekslidir.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç genliklerin kendisini olasılık sanıyor: kare almıyor ve negatif ya da karmaşık genlikte anlamsız sonuç veriyor.

```starter
def olcum_dagilimi(genlikler):
    n = len(genlikler).bit_length() - 1
    t = sum(genlikler)
    p = {format(i, f'0{n}b'): round(a / t, 9) for i, a in enumerate(genlikler)}
    return {'qubit': n, 'olasiliklar': p, 'en_olasi': max(p, key=p.get)}
```

```solution
def olcum_dagilimi(genlikler):
    if not isinstance(genlikler, list) or not genlikler:
        raise ValueError('genlikler boş olmayan liste olmalı')
    if any(isinstance(a, bool) or not isinstance(a, (int, float, complex)) for a in genlikler):
        raise ValueError('genlikler sayı olmalı')
    uzunluk = len(genlikler)
    if uzunluk & (uzunluk - 1):
        raise ValueError('uzunluk 2 nin kuvveti olmalı')
    n = uzunluk.bit_length() - 1
    kareler = [abs(a) ** 2 for a in genlikler]
    toplam = sum(kareler)
    if toplam == 0:
        raise ValueError('bütün genlikler sıfır olamaz')
    olas = [round(k / toplam, 9) for k in kareler]
    etiket = lambda i: format(i, f'0{n}b') if n else ''
    en = max(range(uzunluk), key=lambda i: (kareler[i], -i))
    return {'qubit': n, 'olasiliklar': {etiket(i): p for i, p in enumerate(olas)}, 'en_olasi': etiket(en)}
```

```test
need('olcum_dagilimi')
import cmath, math, random

r = olcum_dagilimi([0.5, 0.5, 0.5, 0.5])
eq(r, {'qubit': 2, 'olasiliklar': {'00': 0.25, '01': 0.25, '10': 0.25, '11': 0.25}, 'en_olasi': '00'}, 'eşit süperpozisyon: her sonuç dörtte bir')
r = olcum_dagilimi([1, -1])
eq(r['olasiliklar'], {'0': 0.5, '1': 0.5}, 'negatif genlik: olasılık yine yarı yarıya (kare alınır, normalleştirilir)')
r = olcum_dagilimi([1, 1j])
eq(r['olasiliklar'], {'0': 0.5, '1': 0.5}, 'karmaşık genlik: mutlak değerin karesi')
r = olcum_dagilimi([3, 4])
eq(r['olasiliklar'], {'0': 0.36, '1': 0.64}, 'normalleştirilmemiş durum: 9 / 25 ve 16 / 25')
eq(r['en_olasi'], '1', 'en olası sonuç')
eq(olcum_dagilimi([0, 0, 1, 0])['en_olasi'], '10', 'iki qubit, indeks 2: etiket 10')
eq(olcum_dagilimi([7]), {'qubit': 0, 'olasiliklar': {'': 1.0}, 'en_olasi': ''}, 'sıfır qubit: tek sonuç')
rng = random.Random(2901)
for _ in range(25):
    n = rng.randint(1, 4)
    g = [complex(rng.uniform(-1, 1), rng.uniform(-1, 1)) for _ in range(2 ** n)]
    r = olcum_dagilimi(g)
    eq((r['qubit'], len(r['olasiliklar'])), (n, 2 ** n), 'qubit ve sonuç sayısı')
    yakin(sum(r['olasiliklar'].values()), 1.0, 'olasılıklar 1 e toplanır', tol=1e-7)
    t = math.fsum(abs(a) ** 2 for a in g)
    for i, a in enumerate(g):
        yakin(r['olasiliklar'][format(i, f'0{n}b')], abs(a) ** 2 / t, 'Born kuralı', tol=1e-8)
    faz = cmath.exp(1j * rng.uniform(0, 6.28))
    r2 = olcum_dagilimi([a * faz * 3 for a in g])
    for k in r['olasiliklar']:
        yakin(r2['olasiliklar'][k], r['olasiliklar'][k], 'ortak faz ve ölçek ölçümü değiştirmez', tol=1e-8)
g = [1, 1]
olcum_dagilimi(g)
eq(g, [1, 1], 'girdi değişmez')
for kotu in (None, [], [1, 1, 1], [0, 0], [1, "1"], [True, False], (1, 1), [1, None]):
    raises(ValueError, olcum_dagilimi, kotu, msg='bozuk girdi reddedilir')
```

```hint
`abs(a) ** 2` karmaşık sayılarda da mutlak değerin karesini verir. Toplamına böl. Etiket için `format(i, f'0{n}b')`.
```
:::

::: gorev 2 · Aramada hızlanma ne kadar?
`arama_adimlari(bit)` işlevini yaz. `bit` bitlik bir anahtar uzayında (`N = 2^bit` olasılık) yapısız arama için adım sayılarını karşılaştırır.

- `bit`: 1 ile 512 arasında `int`.
- `klasik_log2`: klasik aramanın ortalama deneme sayısının (`N / 2`) 2 tabanında logaritması, yani `bit - 1`.
- `grover_log2`: Grover'ın adım sayısının ($\frac{\pi}{4}\sqrt{N}$) 2 tabanında logaritması, yani `bit / 2 + log2(π / 4)`.
- `hizlanma_log2`: ikisinin farkı.
- `etkin_guvenlik_bit`: Grover karşısında anahtarın etkin güvenliği, `bit / 2`.
- Dönüş: bu dört anahtar; 6 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç hızlanmayı üstel sanıyor: kuantum adım sayısını `bit` ile doğrusal ölçekliyor. Bu doğru olsaydı her simetrik şifre kırılırdı.

```starter
def arama_adimlari(bit):
    import math
    return {'klasik_log2': float(bit - 1), 'grover_log2': round(math.log2(bit), 6), 'hizlanma_log2': round(bit - 1 - math.log2(bit), 6), 'etkin_guvenlik_bit': round(math.log2(bit), 6)}
```

```solution
def arama_adimlari(bit):
    import math
    if isinstance(bit, bool) or not isinstance(bit, int) or not 1 <= bit <= 512:
        raise ValueError('bit 1 ile 512 arasında int olmalı')
    klasik = float(bit - 1)
    grover = bit / 2 + math.log2(math.pi / 4)
    return {
        'klasik_log2': round(klasik, 6),
        'grover_log2': round(grover, 6),
        'hizlanma_log2': round(klasik - grover, 6),
        'etkin_guvenlik_bit': round(bit / 2, 6),
    }
```

```test
need('arama_adimlari')
import math, random

r = arama_adimlari(128)
eq(r['klasik_log2'], 127.0, '128 bit: klasik ortalama 2 üzeri 127 deneme')
yakin(r['grover_log2'], 64 + math.log2(math.pi / 4), '128 bit: Grover yaklaşık 2 üzeri 63.65 adım', tol=1e-6)
eq(r['etkin_guvenlik_bit'], 64.0, '128 bitlik anahtarın Grover karşısında etkin güvenliği 64 bit')
r = arama_adimlari(256)
eq(r['etkin_guvenlik_bit'], 128.0, '256 bitlik anahtar: 128 bit etkin güvenlik (hâlâ kırılamaz)')
ok(r['grover_log2'] > 127, 'AES-256 için Grover bile 2 üzeri 127 den çok adım ister', got=r)
eq(arama_adimlari(1)['klasik_log2'], 0.0, '1 bit: tek deneme')
r = arama_adimlari(2)
yakin(2 ** r['grover_log2'], math.pi / 2, 'dört öğede Grover: pi / 2, yani yaklaşık 1.57 adım', tol=1e-5)
yakin(2 ** arama_adimlari(20)['grover_log2'], math.pi / 4 * 1024, 'bir milyon öğede yaklaşık 804 adım', tol=1e-2)
rng = random.Random(2902)
for _ in range(25):
    b = rng.randint(1, 512)
    r = arama_adimlari(b)
    yakin(r['klasik_log2'], b - 1, 'klasik: N / 2', tol=1e-6)
    yakin(r['grover_log2'], math.log2(math.pi / 4) + b / 2, 'Grover: (pi / 4) kök N', tol=1e-6)
    yakin(r['hizlanma_log2'], r['klasik_log2'] - r['grover_log2'], 'hızlanma iki adım sayısının oranı', tol=2e-6)
    ok(r['grover_log2'] > b / 2 - 1, 'karesel hızlanma: adım sayısının logaritması yaklaşık bit / 2, bit in logaritması değil')
a, c = arama_adimlari(100), arama_adimlari(200)
yakin(c['grover_log2'] - a['grover_log2'], 50.0, 'anahtarı iki katına çıkarmak Grover adımlarını 2 üzeri 50 kat artırır', tol=1e-5)
for kotu in (0, -8, 513, 128.0, True, None, "128"):
    raises(ValueError, arama_adimlari, kotu, msg='bozuk girdi reddedilir')
```

```hint
Logaritmayla çalış: `log2(N / 2) = bit − 1` ve `log2((π / 4)·√N) = bit / 2 + log2(π / 4)`.
```
:::

::: gorev 3 · Saklanan genlik, okunan bit
`durum_boyutu(qubit)` işlevini yaz.

- `qubit`: 1 ile 300 arasında `int`.
- `genlik_sayisi`: $2^{\text{qubit}}$ (`int`).
- `klasik_bayt`: durumu klasik bellekte saklamak için gereken bayt; her genlik 16 bayttır (iki tane 64 bitlik kayan nokta sayısı): `16 × 2^qubit` (`int`).
- `okunabilir_bit`: tek bir ölçümden çıkarılabilecek en çok klasik bilgi (`Holevo` sınırı): `qubit`.
- `oran_log2`: `genlik_sayisi / okunabilir_bit` oranının 2 tabanında logaritması; 6 basamağa yuvarlanır.
- Dönüş: bu dört anahtar.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç okunabilir bilgiyi genlik sayısına eşit sayıyor: "`n` qubit `2ⁿ` bit saklar" yanlışının kendisi.

```starter
def durum_boyutu(qubit):
    return {'genlik_sayisi': 2 ** qubit, 'klasik_bayt': 16 * 2 ** qubit, 'okunabilir_bit': 2 ** qubit, 'oran_log2': 0.0}
```

```solution
def durum_boyutu(qubit):
    import math
    if isinstance(qubit, bool) or not isinstance(qubit, int) or not 1 <= qubit <= 300:
        raise ValueError('qubit 1 ile 300 arasında int olmalı')
    return {
        'genlik_sayisi': 2 ** qubit,
        'klasik_bayt': 16 * 2 ** qubit,
        'okunabilir_bit': qubit,
        'oran_log2': round(qubit - math.log2(qubit), 6),
    }
```

```test
need('durum_boyutu')
import math, random

r = durum_boyutu(1)
eq(r, {'genlik_sayisi': 2, 'klasik_bayt': 32, 'okunabilir_bit': 1, 'oran_log2': 1.0}, 'tek qubit: iki genlik, bir bit')
r = durum_boyutu(10)
eq((r['genlik_sayisi'], r['klasik_bayt'], r['okunabilir_bit']), (1024, 16384, 10), '10 qubit: 1024 genlik, 16 kB, 10 bit')
r = durum_boyutu(50)
eq(r['klasik_bayt'], 16 * 2 ** 50, '50 qubit: 16 · 2 üzeri 50 bayt (yaklaşık 18 petabayt)')
ok(17e15 < r['klasik_bayt'] < 19e15, '50 qubit klasik bellekte petabayt mertebesinde', got=r['klasik_bayt'])
eq(r['okunabilir_bit'], 50, 'ama ölçümle en çok 50 bit okunur')
r = durum_boyutu(300)
ok(r['genlik_sayisi'] > 10 ** 90, '300 qubit: genlik sayısı gözlemlenebilir evrendeki atom sayısından fazla', got=len(str(r['genlik_sayisi'])))
eq(r['okunabilir_bit'], 300, '300 qubit ten yine 300 bit')
ok(isinstance(r['genlik_sayisi'], int), 'büyük sayılar int kalır (kayan noktaya taşmaz)')
rng = random.Random(2903)
for _ in range(25):
    q = rng.randint(1, 300)
    r = durum_boyutu(q)
    eq(r['genlik_sayisi'], 1 << q, 'genlik sayısı 2 üzeri n')
    eq(r['klasik_bayt'], 16 << q, 'her genlik 16 bayt')
    eq(r['okunabilir_bit'], q, 'Holevo: n qubit, n bit')
    yakin(r['oran_log2'], q - math.log2(q), 'oran: 2 üzeri n bölü n', tol=1e-6)
eq(durum_boyutu(11)['klasik_bayt'], 2 * durum_boyutu(10)['klasik_bayt'], 'her yeni qubit klasik belleği ikiye katlar')
for kotu in (0, -1, 301, 10.0, True, None, "10"):
    raises(ValueError, durum_boyutu, kotu, msg='bozuk girdi reddedilir')
```

```hint
Genlik sayısı `2 ** qubit` (Python tam sayıları taşmaz). Okunabilir bilgi yalnız `qubit` bittir. Oranın logaritması `qubit − log2(qubit)`.
```
:::

::: anlat 4. Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur. Her adım bu derste hesapladığın bir sayıya dayanır.

1. **Yanlışı söyle (15 sn).** "Kuantum bilgisayar bütün cevapları aynı anda dener, diye duymuşsunuzdur. Bu yanlış ve neden yanlış olduğu, makinenin gerçekte ne yaptığını anlatır."
2. **Ölçüm (30 sn).** "Evet, makine bütün olasılıkları bir arada tutar. Ama sorduğunuzda size yalnız birini söyler, o da rastgele. Tahmin adımındaki sayıyı ver: dört olasılık, her biri dörtte bir. Zar atmaktan farkı yok."
3. **Hüner (30 sn).** "Hüner şudur: yanlış cevapları birbirine çarptırıp söndürmek, doğru cevabı güçlendirmek. Dalgaların birbirini yok etmesi gibi. Bunu her problemde yapamıyoruz; yalnız birkaç problemde yapmayı biliyoruz."
4. **Ne kadar hızlı (25 sn).** "Bir şifreyi kırmak gibi bazı işlerde fark devasa. Aramada ise yalnız karekök kadar: bir milyon yerine bin adım. E-postanızı ya da videonuzu hızlandırmaz."
5. **Kapanış (20 sn).** "Yani bu, bilgisayarınızın yerini alacak daha hızlı bir bilgisayar değil; birkaç özel problem için çok güçlü, çok kırılgan bir alet. O birkaç problemden biri bugünkü internet şifrelemesi olduğu için ciddiye alıyoruz."

Salondan gelebilecek iki soru ve dürüst cevapları:

- *"Banka şifrem tehlikede mi?"* Bugün değil. Bugünkü makineler bunu yapmaktan çok uzak. Ama bugün kaydedilen şifreli veri ileride açılabilir; bu yüzden kurumlar yeni şifreleme yöntemlerine geçmeye şimdiden başlıyor.
- *"Ne zaman olacak?"* Bilmiyoruz. Tahminler birkaç yıl ile birkaç on yıl arasında değişiyor ve uzmanlar uzlaşmış değil. Tarih veren kişiye hangi varsayımla verdiğini sor.
:::

::: anlat Sınır
Bu ders kuantum hesaplama hakkındaki beş yaygın yanlışı ve onları düzelten üç hesabı anlatır; hiçbir kuantum devresi çalıştırılmaz. Görev 1 yalnız Born kuralını uygular; genliklerin bir algoritmayla nasıl düzenlendiği (kapılar, girişim) `kuantum-02`, `kuantum-03` ve `kuantum-09`'dadır. Görev 2'deki adım sayıları **sorgu** sayılarıdır ve ideal, hatasız bir makine varsayar: her Grover adımı binlerce temel kapı içerir, hata düzeltme büyük bir çarpan ekler ve Grover iyi paralelleşmez; pratikte karesel hızlanmanın büyük kısmı bu maliyetlere gider. Hızlanma tablosundaki "bilinen hızlanma yok" ifadesi bugünkü bilgidir; bir problem için hızlanma olmadığının kanıtı çoğu durumda yoktur. Kuantum bilgisayarların klasik bilgisayarlardan gerçekten daha güçlü olduğu (karmaşıklık sınıflarının ayrı olduğu) da kanıtlanmış değil, yaygın bir varsayımdır. Görev 3'teki Holevo sınırı tek bir ölçümden çıkarılabilecek klasik bilgiyi sınırlar; durumun birçok kopyası varsa daha çok şey öğrenilebilir, ama kopyalamak yasaktır (`no-cloning`) ve her kopya yeniden hazırlanmalıdır. Yeni açık anahtarlı sistemlerin kuantum saldırısına dayanıklılığı da kanıtlanmış değil, bugüne kadar kırılamamış olmalarına dayanan bir güvendir.

Kaynaklar: [Aaronson 2008 - The Limits of Quantum Computers (Scientific American)](https://www.scottaaronson.com/writings/limitsqc-draft.pdf), [Nielsen ve Chuang 2010 - Quantum Computation and Quantum Information](https://doi.org/10.1017/CBO9780511976667), [Grover 1996 - A fast quantum mechanical algorithm for database search](https://arxiv.org/abs/quant-ph/9605043), [Brassard, Høyer ve Tapp 1997 - Quantum Algorithm for the Collision Problem](https://arxiv.org/abs/quant-ph/9705002), [Bernstein 2009 - Cost analysis of hash collisions: Will quantum computers make SHARCS obsolete?](https://cr.yp.to/hash/collisioncost-20090517.pdf), [Holevo 1973 - Bounds for the quantity of information transmitted by a quantum communication channel](http://mi.mathnet.ru/eng/ppi903), [NIST Post-Quantum Cryptography standartları](https://csrc.nist.gov/projects/post-quantum-cryptography).
:::

::: dusun
Bir haber başlığı "1.000 qubit'lik yeni işlemci, 2 üzeri 1.000 hesabı aynı anda yapıyor" diyor. Bu cümlede bu dersteki beş yanlıştan hangileri var? Aynı haberi tek cümleyle, yanlış olmadan ve sıkıcı da olmadan nasıl yazardın?
:::

::: ozet
- Kuantum kaydı `2ⁿ` genlik taşır, ama ölçüm tek bir sonuç verir; olasılık genliğin mutlak değerinin karesidir.
- Hesaplamanın işi yanlış cevapların genliklerini girişimle söndürmek, doğru cevabınkini güçlendirmektir.
- Hızlanma probleme bağlıdır: çarpanlara ayırmada üstele yakın, aramada karesel, çoğu işte bilinen bir hızlanma yok.
- `n` qubit'ten ölçümle en çok `n` bit okunur; kuantum durumu bir veritabanı değildir.
- Kırılan şey belirli açık anahtarlı sistemlerdir; simetrik şifreler anahtar uzatılarak korunur ve makine genel amaçlı bilgisayarın yerini almaz.
:::
