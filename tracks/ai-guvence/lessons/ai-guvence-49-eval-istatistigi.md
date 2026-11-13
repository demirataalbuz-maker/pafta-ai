---
id: ai-guvence-49
title: "Eval İstatistiği · Eşli Karşılaştırma, Çoklu Test ve Küçük Örneklem"
summary: Aynı sorularla sınanan iki modeli McNemar testiyle karşılaştır, çok sayıda karşılaştırmada yanlış keşifleri Bonferroni ve Benjamini-Hochberg ile sınırla ve bir farkı görebilmek için kaç örnek gerektiğini hesapla.
esleme: ai-guvence-27, ai-matematik-06, ai-matematik-07
timeout: 30
---

::: anlat 1. Bir eval tablosunu ne zaman ciddiye alırsın?
`ai-matematik-06` ve `ai-matematik-07` bir oranın belirsizliğini ve iki oranın farkını verdi. Gerçek değerlendirmelerde üç durum o araçları yetersiz bırakır:

| Durum | Sorun | Araç | Görev |
|---|---|---|---|
| İki model **aynı** sorularla sınandı | Ölçümler bağımsız değil; bağımsız test gücü boşa harcar | `McNemar` testi | 1 |
| Yirmi model, on benchmark, iki yüz karşılaştırma | Şans eseri "anlamlı" çıkanlar | `Bonferroni`, `Benjamini-Hochberg` | 2 |
| Test kümesi küçük | Fark var ama görünmüyor; sıfır hata "hatasız" sanılıyor | Güç analizi, üç kuralı | 3 |

Bu üçü, bir eval sonucunun yanlış okunmasının en yaygın yollarıdır ve hepsi bir güvenlik değerlendirmesinde de geçerlidir: "yeni sürüm daha güvenli" iddiası ancak aynı test kümesinde, düzeltilmiş eşikle ve yeterli örnekle anlam taşır.

> [!NOT]
> Görevlerdeki sayımlar ve `p-value`'lar sentetiktir. Bu ders, gerçek bir modelin sonuçlarını değil, sonuçları okumak için gereken hesapları öğretir.
:::

::: anlat 2. Üç araç
**McNemar testi.** İki model aynı `n` soruyu cevapladıysa her soru dört kutudan birine düşer: ikisi de doğru, ikisi de yanlış, yalnız A doğru (`b`), yalnız B doğru (`c`). İki modelin de aynı cevabı verdiği sorular fark hakkında **hiçbir şey söylemez**; bilgi yalnız ayrıştıkları `b + c` sorudadır.

Sıfır hipotezi: modeller eşit; ayrıştıkları bir soruda hangisinin doğru olduğu yazı turadır. O hâlde `b`, `b + c` atışta yarı olasılıkla gelen tura sayısıdır ve kesin (`exact`) iki yönlü `p-value`:

$$p = \min\!\left(1,\; 2\sum_{k=0}^{\min(b, c)} \binom{b + c}{k}\left(\tfrac{1}{2}\right)^{b + c}\right)$$

Aynı veride bağımsız iki oran testi (bkz. `ai-matematik-07`) çok daha zayıftır, çünkü soruların zorluğundan gelen ortak oynaklığı gürültü sayar. 1.000 soruda %90 ve %92 alan iki model bağımsız testte ayrılamayabilir; ama ayrıştıkları 40 sorunun 30'unda B doğruysa fark açıktır.

**Çoklu karşılaştırma.** Her test %5 yanlış alarm olasılığı taşır. Hiçbir gerçek fark olmasa bile 20 testte en az bir "anlamlı" sonuç görme olasılığı $1 - 0{,}95^{20} \approx \%64$'tür. İki düzeltme vardır:

- **Bonferroni:** her testi $\alpha / m$ eşiğiyle değerlendir (`m` test sayısı). Tek bir yanlış alarm olasılığını bile $\alpha$'nın altında tutar; çok tutucudur.
- **Benjamini-Hochberg:** `p-value`'ları küçükten büyüğe sırala; $p_{(k)} \le \dfrac{k}{m}\alpha$ koşulunu sağlayan **en büyük** `k`'yı bul; ilk `k` testin hepsini kabul et. Yanlış alarm sayısını değil, kabul edilenler içindeki yanlış alarm **oranını** (`false discovery rate`) sınırlar; daha güçlüdür.

**Küçük örneklem.** İki ayrı tuzak vardır.

*Güç.* Gerçek bir farkı görebilme olasılığına `power` denir. İki grubu karşılaştırırken, taban oranı `p` olan ve aralarında $\delta$ fark bulunan iki oranı %5 anlamlılık ve %80 güçle ayırmak için grup başına yaklaşık şu kadar örnek gerekir:

$$n \approx \frac{(z_{\alpha/2} + z_\beta)^2 \cdot 2\,p(1 - p)}{\delta^2}, \qquad z_{\alpha/2} = 1{,}96,\; z_\beta = 0{,}84$$

%80 civarındaki bir doğrulukta 2 puanlık farkı görmek için grup başına yaklaşık 6.300 örnek gerekir. 200 soruluk bir testte "fark bulunamadı" demek, "fark yok" demek değildir.

*Üç kuralı.* `n` denemede hiç hata görmediysen gerçek hata oranı sıfır değildir; %95 güvenle en çok yaklaşık $3 / n$'dir. 100 denemede sıfır başarısızlık, oranın %3'e kadar olabileceğini söyler.
:::

::: tahmin Aynı sorular, iki farklı test
İki model aynı 1.000 soruda %90 ve %92 doğruluk aldı. Ayrıştıkları 40 sorunun 10'unda A, 30'unda B doğru. Eşli testin `p-value`'su ne yazdırılır?

```python
from math import comb

b, c = 10, 30
n = b + c
p = min(1.0, 2 * sum(comb(n, k) for k in range(min(b, c) + 1)) / 2 ** n)
print(n, round(p, 4))
```

???

```cikti
40 0.0022
```
Bin sorunun 960'ında iki model aynı cevabı verdi; o sorular karşılaştırmaya bilgi katmıyor. Ayrıştıkları 40 soruda B, A'yı 30'a 10 geçiyor ve bunun yazı turayla olma olasılığı binde ikidir. Aynı sayılarla bağımsız iki oran testi `p ≈ 0,12` verirdi ve "fark yok" derdin. Fark aynı; kullandığın test, verinin yapısına uymuyordu.
:::

::: gorev 1 · McNemar testi (kesin)
`mcnemar(yalniz_a, yalniz_b)` işlevini yaz.

- `yalniz_a`: yalnız A'nın doğru cevapladığı soru sayısı; `yalniz_b`: yalnız B'nin. İkisi de negatif olmayan `int`.
- `ayrisan`: ikisinin toplamı. `fark`: `yalniz_a - yalniz_b`.
- `p_degeri`: yukarıdaki kesin iki yönlü değer; `ayrisan == 0` ise `1.0`.
- Dönüş: `{'ayrisan': ..., 'fark': ..., 'p_degeri': ...}`; `p_degeri` 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç yalnız farkın sıfır olup olmadığına bakıyor: 1'e 0'lık bir ayrışmayı da 300'e 100'lük bir ayrışmayı da "fark var" diye raporluyor.

```starter
def mcnemar(yalniz_a, yalniz_b):
    return {'ayrisan': yalniz_a + yalniz_b, 'fark': yalniz_a - yalniz_b, 'p_degeri': 1.0 if yalniz_a == yalniz_b else 0.0}
```

```solution
def mcnemar(yalniz_a, yalniz_b):
    from math import comb
    for x in (yalniz_a, yalniz_b):
        if isinstance(x, bool) or not isinstance(x, int) or x < 0:
            raise ValueError('sayımlar negatif olmayan int olmalı')
    n = yalniz_a + yalniz_b
    if n == 0:
        p = 1.0
    else:
        p = min(1.0, 2 * sum(comb(n, k) for k in range(min(yalniz_a, yalniz_b) + 1)) / 2 ** n)
    return {'ayrisan': n, 'fark': yalniz_a - yalniz_b, 'p_degeri': round(p, 9)}
```

```test
need('mcnemar')
import random
from fractions import Fraction
from math import comb

r = mcnemar(10, 30)
eq((r['ayrisan'], r['fark']), (40, -20), 'ayrışan sayısı ve fark')
yakin(r['p_degeri'], 0.002221434, '10 a 30: binde iki', tol=1e-8)
eq(mcnemar(0, 0), {'ayrisan': 0, 'fark': 0, 'p_degeri': 1.0}, 'hiç ayrışma yok')
eq(mcnemar(1, 0)['p_degeri'], 1.0, 'tek ayrışma hiçbir şey kanıtlamaz')
eq(mcnemar(5, 5)['p_degeri'], 1.0, 'eşit ayrışma: p 1 e kırpılır')
eq(mcnemar(0, 5)['p_degeri'], 0.0625, '0 a 5: 2 · (1/32)')
eq(mcnemar(0, 6)['p_degeri'], 0.03125, '0 a 6: 0.05 in altına ilk iniş')
yakin(mcnemar(30, 10)['p_degeri'], mcnemar(10, 30)['p_degeri'], 'modellerin yerini değiştirmek p yi değiştirmez', tol=1e-12)
ok(mcnemar(100, 300)['p_degeri'] < 1e-20, 'büyük ve tutarlı ayrışma', got=mcnemar(100, 300))
rng = random.Random(4901)
for _ in range(30):
    b, c = rng.randint(0, 60), rng.randint(0, 60)
    n = b + c
    exp = Fraction(1) if n == 0 else min(Fraction(1), 2 * sum(Fraction(comb(n, k), 2 ** n) for k in range(min(b, c) + 1)))
    r = mcnemar(b, c)
    yakin(r['p_degeri'], float(exp), 'rastgele sayımlarda kesirli referansla aynı', tol=1e-9)
    ok(0.0 <= r['p_degeri'] <= 1.0, 'p bir olasılıktır')
for a in ([-1, 5], [5, -1], [5.0, 5], [5, True], [None, 5], ["5", 5]):
    raises(ValueError, mcnemar, *a, msg='bozuk girdi reddedilir')
```

```hint
`n = b + c`. Küçük olan sayıya kadar binom katsayılarını topla, `2ⁿ`'e böl, ikiyle çarp ve 1'e kırp.
```
:::

::: gorev 2 · Çoklu karşılaştırma düzeltmesi
`coklu_duzeltme(p_degerleri, alfa)` işlevini yaz.

- `p_degerleri`: boş olmayan liste; her öğe `[0, 1]` aralığında sayı. `alfa`: `(0, 1)` aralığında sayı. `m` test sayısıdır.
- `duzeltmesiz`: her test için `p <= alfa`.
- `bonferroni`: her test için `p <= alfa / m`.
- `bh` (Benjamini-Hochberg): `p-value`'ları küçükten büyüğe sırala; `p_(k) <= (k / m) · alfa` koşulunu sağlayan en büyük `k`'yı bul (`k` 1'den başlar); sıralamada ilk `k` test `True`, gerisi `False`. Böyle bir `k` yoksa hepsi `False`. Eşit `p-value`'larda girdi sırası korunur.
- Dönüş: `{'duzeltmesiz': [...], 'bonferroni': [...], 'bh': [...]}`; üç liste de girdiyle **aynı sırada** `bool` içerir.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç Benjamini-Hochberg'de koşulu sağlamayan **ilk** testte duruyor. Doğru yöntem koşulu sağlayan **son** testi arar: arada koşulu kaçıran bir test olsa bile ondan sonraki sağlayan test, öncekilerin hepsini kurtarır.

```starter
def coklu_duzeltme(p_degerleri, alfa):
    m = len(p_degerleri)
    sira = sorted(range(m), key=lambda i: p_degerleri[i])
    bh = [False] * m
    for k, i in enumerate(sira, 1):
        if p_degerleri[i] > k / m * alfa:
            break
        bh[i] = True
    return {'duzeltmesiz': [p <= alfa for p in p_degerleri], 'bonferroni': [p <= alfa / m for p in p_degerleri], 'bh': bh}
```

```solution
def coklu_duzeltme(p_degerleri, alfa):
    if not isinstance(p_degerleri, list) or not p_degerleri or any(isinstance(p, bool) or not isinstance(p, (int, float)) or not 0 <= p <= 1 for p in p_degerleri):
        raise ValueError('p_degerleri [0, 1] aralığında sayılardan oluşan boş olmayan liste olmalı')
    if isinstance(alfa, bool) or not isinstance(alfa, (int, float)) or not 0 < alfa < 1:
        raise ValueError('alfa (0, 1) aralığında olmalı')
    m = len(p_degerleri)
    sira = sorted(range(m), key=lambda i: p_degerleri[i])
    en_buyuk_k = 0
    for k, i in enumerate(sira, 1):
        if p_degerleri[i] <= k / m * alfa:
            en_buyuk_k = k
    bh = [False] * m
    for i in sira[:en_buyuk_k]:
        bh[i] = True
    return {
        'duzeltmesiz': [p <= alfa for p in p_degerleri],
        'bonferroni': [p <= alfa / m for p in p_degerleri],
        'bh': bh,
    }
```

```test
need('coklu_duzeltme')
import random

r = coklu_duzeltme([0.001, 0.04, 0.03, 0.2], 0.05)
eq(coklu_duzeltme([0.05, 0.5], 0.05)['duzeltmesiz'], [True, False], 'p tam alfa ya eşitse anlamlı sayılır (<=)')
eq(r['duzeltmesiz'], [True, True, True, False], 'düzeltmesiz: üç keşif')
eq(r['bonferroni'], [True, False, False, False], 'Bonferroni eşiği 0.0125: tek keşif')
eq(r['bh'], [True, False, False, False], 'BH eşikleri 0.0125, 0.025, 0.0375, 0.05: yalnız ilki')
r = coklu_duzeltme([0.01, 0.04, 0.03, 0.02], 0.05)
eq(r['bh'], [True, True, True, True], 'BH: sıralı p ler 0.01, 0.02, 0.03, 0.04 hepsi eşiklerinin altında')
eq(r['bonferroni'], [True, False, False, False], 'aynı veride Bonferroni yalnız birini kabul eder')
r = coklu_duzeltme([0.03, 0.001, 0.04], 0.05)
eq(r['bh'], [True, True, True], 'ikinci sıradaki (0.03) eşiğini (0.0333) geçiyor, üçüncü (0.04) kendi eşiğini (0.05) sağlıyor: hepsi kabul')
r = coklu_duzeltme([0.02, 0.03, 0.045], 0.05)
eq(r['bh'], [True, True, True], 'ilk ikisi kendi eşiğini kaçırıyor ama üçüncü sağlıyor: en büyük k = 3, hepsi kabul')
eq(coklu_duzeltme([0.04], 0.05), {'duzeltmesiz': [True], 'bonferroni': [True], 'bh': [True]}, 'tek test: düzeltme bir şey değiştirmez')
eq(coklu_duzeltme([0.5, 0.9], 0.05)['bh'], [False, False], 'koşulu sağlayan yok')
rng = random.Random(4902)
for _ in range(25):
    m = rng.randint(1, 15)
    ps = [round(rng.random() ** 3, 4) for _ in range(m)]
    a = rng.choice([0.01, 0.05, 0.1])
    r = coklu_duzeltme(ps, a)
    sirali = sorted(ps)
    k = max([i + 1 for i in range(m) if sirali[i] <= (i + 1) / m * a], default=0)
    esik = sirali[k - 1] if k else -1.0
    eq(sum(r['bh']), k, 'rastgele p lerde BH kabul sayısı')
    ok(all((p <= esik) == kabul or p == esik for p, kabul in zip(ps, r['bh'])), 'BH: eşik p sinin altındakiler kabul')
    eq(r['bonferroni'], [p <= a / m for p in ps], 'rastgele p lerde Bonferroni')
    ok(all(not b or h for b, h in zip(r['bonferroni'], r['bh'])), 'Bonferroni nin kabul ettiğini BH de kabul eder')
    ok(all(not h or d for h, d in zip(r['bh'], r['duzeltmesiz'])), 'BH nin kabul ettiği düzeltmesiz de anlamlıdır')
ps = [0.03, 0.01]
coklu_duzeltme(ps, 0.05)
eq(ps, [0.03, 0.01], 'girdi değişmez (sıralanmaz)')
for a in ([None, 0.05], [[], 0.05], [[1.2], 0.05], [[-0.1], 0.05], [[0.5, "0.1"], 0.05], [[True], 0.05], [[float('nan')], 0.05], [(0.01,), 0.05], [[0.01], 0], [[0.01], 1], [[0.01], None], [[0.01], True], [[0.01], float('nan')]):
    raises(ValueError, coklu_duzeltme, *a, msg='bozuk girdi reddedilir')
```

```hint
İndeksleri `p-value`'ya göre sırala. Döngüde koşulu sağlayan **her** `k`'da `en_buyuk_k`'yı güncelle (durma). Sonra sıralamanın ilk `en_buyuk_k` indeksini `True` yap.
```
:::

::: gorev 3 · Kaç örnek gerekir?
`ornek_plani(taban_oran, fark, z_alfa, z_guc)` işlevini yaz.

- `taban_oran`: `(0, 1)` aralığında sayı. `fark`: görmek istediğin en küçük fark; `(0, 1)` aralığında sayı. `z_alfa`, `z_guc`: pozitif sayılar (%5 anlamlılık için 1,96; %80 güç için 0,84).
- `grup_basina`: $\left\lceil \dfrac{(z_\alpha + z_\beta)^2 \cdot 2\,p(1 - p)}{\delta^2} \right\rceil$ (`int`).
- `sifir_hata_siniri`: bu kadar denemede hiç hata görülmezse gerçek hata oranının %95 üst sınırı, `3 / grup_basina`.
- Dönüş: `{'grup_basina': ..., 'sifir_hata_siniri': ...}`; sınır 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç örnek sayısını farkla **doğrusal** ölçekliyor: farkı yarıya indirince iki kat örnek yeter sanıyor; oysa dört kat gerekir.

```starter
def ornek_plani(taban_oran, fark, z_alfa, z_guc):
    n = int((z_alfa + z_guc) ** 2 * 2 * taban_oran * (1 - taban_oran) / fark) + 1
    return {'grup_basina': n, 'sifir_hata_siniri': round(3 / n, 9)}
```

```solution
def ornek_plani(taban_oran, fark, z_alfa, z_guc):
    import math
    def sayi(x):
        return not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x)
    if not sayi(taban_oran) or not 0 < taban_oran < 1 or not sayi(fark) or not 0 < fark < 1:
        raise ValueError('taban_oran ve fark (0, 1) aralığında olmalı')
    if not sayi(z_alfa) or not sayi(z_guc) or not z_alfa > 0 or not z_guc > 0:
        raise ValueError('z değerleri pozitif olmalı')
    ham = (z_alfa + z_guc) ** 2 * 2 * taban_oran * (1 - taban_oran) / fark ** 2
    n = max(1, math.ceil(round(ham, 9)))
    return {'grup_basina': n, 'sifir_hata_siniri': round(3 / n, 9)}
```

```test
need('ornek_plani')
import math, random

r = ornek_plani(0.8, 0.02, 1.96, 0.84)
eq(r['grup_basina'], 6272, 'yüzde 80 civarında 2 puanlık fark: grup başına 6272')
yakin(r['sifir_hata_siniri'], 3 / 6272, 'üç kuralı', tol=1e-9)
a = ornek_plani(0.8, 0.04, 1.96, 0.84)['grup_basina']
eq(a, 1568, '4 puanlık fark: 1568')
eq(r['grup_basina'], 4 * a, 'farkı yarıya indirmek dört kat örnek ister')
ok(ornek_plani(0.5, 0.02, 1.96, 0.84)['grup_basina'] > r['grup_basina'], 'yüzde 50 civarında aynı fark daha çok örnek ister')
ok(ornek_plani(0.8, 0.02, 2.58, 0.84)['grup_basina'] > r['grup_basina'], 'daha sıkı anlamlılık daha çok örnek ister')
ok(ornek_plani(0.8, 0.02, 1.96, 1.28)['grup_basina'] > r['grup_basina'], 'daha yüksek güç daha çok örnek ister')
r = ornek_plani(0.5, 0.9, 0.1, 0.1)
eq((r['grup_basina'], r['sifir_hata_siniri']), (1, 3.0), 'en az bir örnek; üç kuralı çok küçük n de anlamsız büyür')
ok(isinstance(r['grup_basina'], int) and not isinstance(r['grup_basina'], bool), 'grup_basina int')
rng = random.Random(4903)
for _ in range(25):
    p, d = round(rng.uniform(0.05, 0.95), 2), round(rng.uniform(0.01, 0.3), 3)
    za, zb = rng.choice([1.645, 1.96, 2.58]), rng.choice([0.84, 1.28])
    r = ornek_plani(p, d, za, zb)
    ham = (za + zb) ** 2 * 2 * p * (1 - p) / d ** 2
    ok(r['grup_basina'] >= ham - 1e-6 and r['grup_basina'] < ham + 1 + 1e-6 or r['grup_basina'] == 1, 'yukarı yuvarlanmış formül', got=(r['grup_basina'], ham))
    yakin(r['sifir_hata_siniri'], 3 / r['grup_basina'], 'üç kuralı', tol=1e-9)
for a in ([0, 0.02, 1.96, 0.84], [1, 0.02, 1.96, 0.84], [True, 0.02, 1.96, 0.84], [float('nan'), 0.02, 1.96, 0.84], [0.8, 0, 1.96, 0.84], [0.8, 1, 1.96, 0.84], [0.8, -0.02, 1.96, 0.84], [0.8, True, 1.96, 0.84], [0.8, float('nan'), 1.96, 0.84], [0.8, 0.02, 0, 0.84], [0.8, 0.02, float('inf'), 0.84], [0.8, 0.02, float('nan'), 0.84], [0.8, 0.02, 1.96, -1], [0.8, 0.02, 1.96, True], [0.8, 0.02, 1.96, float('inf')], [0.8, 0.02, 1.96, float('nan')], [None, 0.02, 1.96, 0.84], [0.8, "0.02", 1.96, 0.84], [0.8, 0.02, True, 0.84]):
    raises(ValueError, ornek_plani, *a, msg='bozuk girdi reddedilir')
```

```hint
Paydada farkın **karesi** var: `(z_alfa + z_guc)² · 2 · p · (1 − p) / fark²`. Yukarı yuvarla; sınır `3 / n`.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur; her adım bu derste hesapladığın bir sayıya ya da örneğe dayanır.

1. **Soru (15 sn).** "Yeni sürüm daha güvenli mi? Üç istatistik tuzağı bu soruyu bozar."
2. **Aynı sorular (30 sn).** "İki model aynı bin soruyu cevapladı; 960'ında aynı cevabı verdiler. Bilgi yalnız ayrıştıkları 40 sorudadır: orada 30'a 10."
3. **Çok test (30 sn).** "Yirmi karşılaştırma yaparsanız, hiçbir gerçek fark olmasa bile birinin 'anlamlı' çıkma olasılığı yüzde 64."
4. **Sıfır hata (25 sn).** "150 denemede hiç başarısızlık yok demek, oranın sıfır olduğunu değil, en çok yüzde 2 civarında olduğunu söyler. Günde bir milyon istekte bu yirmi bin olay olabilir."
5. **Kapanış (20 sn).** "Bir güvenlik iddiasını, ölçüldüğü test kadar ciddiye alın."
:::

::: anlat Sınır
Bu ders eval sonuçlarını okumak için üç istatistik aracı anlatır; görevlerdeki sayılar sentetiktir. McNemar testi yalnız ikili (doğru/yanlış) sonuçlar ve **tek** bir eşli karşılaştırma içindir; sürekli skorlarda eşli `t` testi ya da eşli bootstrap kullanılır. Test soruların bağımsız olduğunu varsayar; aynı belgeden türetilmiş ya da birbirinin varyantı olan sorular bağımsız değildir ve `p-value` olduğundan küçük çıkar. Bonferroni testlerin bağımlılığından etkilenmez ama çok tutucudur; Benjamini-Hochberg bağımsız ya da pozitif bağımlı testlerde geçerlidir ve keyfî bağımlılıkta daha tutucu bir sürümü (`Benjamini-Yekutieli`) gerekir. Hangi karşılaştırmaların "bir aile" sayılacağı bir yargıdır ve deneyden önce belirlenmelidir. Görev 3'teki örnek sayısı formülü **bağımsız** iki grup ve normal yaklaşım içindir; eşli tasarımda gereken sayı çok daha azdır ve ayrışma oranına bağlıdır. Üç kuralı yalnız sıfır gözlem için ve bağımsız denemelerde geçerlidir. İstatistiksel anlamlılık pratik önemi göstermez: yeterince büyük bir testte önemsiz bir fark da anlamlı çıkar; etki büyüklüğü ve güven aralığı her zaman birlikte verilmelidir. Bu araçların hiçbiri test kümesinin eğitime sızmasını, etiket hatalarını ya da testin ölçmek istediğin şeyi ölçüp ölçmediğini göstermez.

Kaynaklar: [McNemar 1947 - Note on the sampling error of the difference between correlated proportions or percentages](https://doi.org/10.1007/BF02295996), [Benjamini ve Hochberg 1995 - Controlling the False Discovery Rate](https://doi.org/10.1111/j.2517-6161.1995.tb02031.x), [Dror vd. 2018 - The Hitchhiker's Guide to Testing Statistical Significance in Natural Language Processing](https://aclanthology.org/P18-1128/), [Card vd. 2020 - With Little Power Comes Great Responsibility](https://arxiv.org/abs/2010.06595), [Miller 2024 - Adding Error Bars to Evals](https://arxiv.org/abs/2411.00640).
:::

::: dusun
Bir ekip 150 soruluk bir güvenlik testinde yeni modelin "hiç başarısız olmadığını" ve bu yüzden "bu risk sınıfına karşı güvenli olduğunu" bildiriyor. Üç kuralını kullanarak gerçek başarısızlık oranı için ne söyleyebilirsin? Model günde bir milyon istek alıyorsa bu üst sınır günde kaç başarısızlığa karşılık gelir? İddiayı savunulabilir hâle getirmek için cümleyi nasıl yeniden yazardın?
:::

::: ozet
- Aynı sorularla sınanan iki model eşli karşılaştırılır; bilgi yalnız ayrıştıkları sorulardadır (McNemar).
- Çok sayıda testte bazıları yalnız şansla anlamlı çıkar; Bonferroni tek bir yanlış alarmı, Benjamini-Hochberg yanlış keşif oranını sınırlar.
- Benjamini-Hochberg koşulu sağlayan **en büyük** sırayı arar; ilk başarısızlıkta durmak yanlıştır.
- Küçük bir farkı görmek için gereken örnek sayısı farkın karesiyle ters orantılıdır; "fark bulunamadı", "fark yok" demek değildir.
- `n` denemede sıfır hata, oranın sıfır olduğunu değil, en çok yaklaşık `3 / n` olduğunu söyler.
:::
