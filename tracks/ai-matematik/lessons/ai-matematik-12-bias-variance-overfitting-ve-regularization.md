---
id: ai-matematik-12
title: "Bias-Variance, Overfitting ve Regularization · Ezber mi, Öğrenme mi?"
summary: Veriyi tekrarlanabilir biçimde eğitim ve test olarak böl, L2 cezasının ağırlığı nasıl küçülttüğünü hesapla ve eğitim eğrilerinden overfitting'in başladığı adımı bul.
---

::: anlat 1. Eğitim hatası yanıltır
Bir modelin eğitim verisinde iyi olması kolaydır: yeterince büyükse veriyi ezberler. Asıl soru, **görmediği** veride ne yaptığıdır (`generalization`). Bu dersin üç aracı bu soruyu ölçülebilir kılar:

| Soru | Araç | Görev |
|---|---|---|
| Görmediği veriyi nereden bulurum? | Eğitim / test ayrımı | 1 |
| Modelin ezberlemesini nasıl zorlaştırırım? | `Regularization` (L2 cezası) | 2 |
| Ezber ne zaman başladı? | Eğitim ve doğrulama eğrileri, `early stopping` | 3 |

Test hatası üç parçaya ayrılır:

- **Bias**: model fazla basit; verinin yapısını yakalayamıyor (`underfitting`). Hem eğitim hem test hatası yüksektir.
- **Variance**: model fazla esnek; eğitim verisindeki gürültüyü de öğreniyor (`overfitting`). Eğitim hatası düşük, test hatası yüksektir.
- **İndirgenemez gürültü**: verinin kendisindeki rastgelelik; hiçbir model gideremez.

Karmaşıklık arttıkça bias düşer, variance yükselir. İyi model ikisinin toplamının en küçük olduğu yerdedir.
:::

::: anlat 2. Üç araç
**Eğitim / test ayrımı.** Veriyi rastgele ikiye bölersin; model yalnız eğitim kısmını görür, test kısmı son ölçüm için saklanır. İki kural vardır. Birincisi, bölme **tekrarlanabilir** olmalıdır (sabit bir tohum): yoksa iki koşunun farkı modelden mi bölmeden mi geldi bilinmez. İkincisi, test verisine bakarak hiçbir karar verilmez; hiperparametre seçimi için üçüncü bir parça (`validation`) ayrılır. Test verisine göre ayar yapmak, onu dolaylı olarak eğitime katmaktır.

**L2 regularization.** Kayba ağırlıkların karesiyle orantılı bir ceza eklersin: $L + \lambda \sum w^2$. Model artık yalnız veriye uymaya değil, ağırlıkları küçük tutmaya da çalışır. Kesişimsiz tek değişkenli doğrusal regresyonda çözüm kapalıdır:

$$w = \frac{\sum x_i y_i}{\sum x_i^2 + \lambda}$$

$\lambda = 0$ cezasız çözümdür. $\lambda$ büyüdükçe payda büyür ve `w` sıfıra doğru **küçülür** (`shrinkage`). Az veri varken ($\sum x^2$ küçük) ceza baskındır; veri arttıkça etkisi kaybolur. Bu, cezanın bir önsel inanç gibi davrandığını gösterir: "kanıt yoksa ağırlık küçüktür". Derin öğrenmedeki `weight decay` aynı fikirdir.

**Eğitim eğrileri.** Eğitim boyunca iki hatayı izlersin: eğitim hatası ve doğrulama hatası. Tipik seyir: ikisi birlikte düşer; bir noktadan sonra eğitim hatası düşmeye devam ederken doğrulama hatası **yükselmeye** başlar. O nokta overfitting'in başladığı yerdir. `Early stopping`, doğrulama hatasının en düşük olduğu adımdaki modeli tutar. İki eğri arasındaki fark `generalization gap`'tir.
:::

::: tahmin Ezberleyen model
Bir "model" eğitim örneklerini aynen saklıyor; görmediği girdide en sık etiketi söylüyor. Eğitim ve test doğruluğu ne yazdırılır?

```python
egitim = {"a": 1, "b": 0, "c": 1, "d": 1}
test = {"e": 0, "f": 1, "g": 0, "h": 0}

en_sik = max(set(egitim.values()), key=list(egitim.values()).count)

def tahmin(x):
    return egitim.get(x, en_sik)

for ad, veri in (("eğitim", egitim), ("test", test)):
    dogru = sum(tahmin(x) == y for x, y in veri.items())
    print(ad, dogru / len(veri))
```

???

```cikti
eğitim 1.0
test 0.25
```
Model eğitim verisinde kusursuz: her örneği saklamış. Test verisinde ise hiçbir örneği tanımıyor ve hep `1` diyor; dört örnekten yalnız biri `1`. Eğitim doğruluğu %100, test doğruluğu %25. Eğitim hatasına bakarak bu modelin iyi olduğunu sanırdın. Fark 75 puanlık bir `generalization gap`'tir.
:::

::: gorev 1 · Tekrarlanabilir eğitim / test ayrımı
`egitim_test_bol(veri, test_orani, tohum)` işlevini yaz.

- `veri`: en az iki öğeli liste (öğeler herhangi bir türde olabilir). `test_orani`: `(0, 1)` aralığında sayı. `tohum`: `int`.
- `0, 1, ..., n-1` indekslerini `random.Random(tohum).shuffle` ile karıştır.
- Test boyutu `round(n * test_orani)`'dir, ama en az 1 ve en çok `n - 1` olacak biçimde sınırlanır (iki parça da boş kalmaz).
- Karıştırılmış indekslerin **ilk** `test boyutu` kadarı test, gerisi eğitimdir; öğeler karıştırılmış sırayla döner.
- Dönüş: `{'egitim': [...], 'test': [...]}`.
- `veri` değişmemelidir. Bozuk girdi `ValueError`.

KUSURLU başlangıç karıştırmadan son parçayı test yapıyor. Veri sıralıysa (örneğin tarihe ya da sınıfa göre) test kısmı eğitimden sistematik olarak farklı olur.

```starter
def egitim_test_bol(veri, test_orani, tohum):
    k = round(len(veri) * test_orani)
    return {'egitim': veri[:len(veri) - k], 'test': veri[len(veri) - k:]}
```

```solution
def egitim_test_bol(veri, test_orani, tohum):
    import random
    if not isinstance(veri, list) or len(veri) < 2:
        raise ValueError('veri en az iki öğeli liste olmalı')
    if isinstance(test_orani, bool) or not isinstance(test_orani, (int, float)) or not 0 < test_orani < 1:
        raise ValueError('test_orani (0, 1) aralığında olmalı')
    if isinstance(tohum, bool) or not isinstance(tohum, int):
        raise ValueError('tohum int olmalı')
    n = len(veri)
    sira = list(range(n))
    random.Random(tohum).shuffle(sira)
    k = min(max(round(n * test_orani), 1), n - 1)
    return {'egitim': [veri[i] for i in sira[k:]], 'test': [veri[i] for i in sira[:k]]}
```

```test
need('egitim_test_bol')
import random

veri = list(range(10))
r = egitim_test_bol(veri, 0.3, 42)
eq((len(r['egitim']), len(r['test'])), (7, 3), '10 öğede yüzde 30: 7 ve 3')
eq(sorted(r['egitim'] + r['test']), veri, 'hiçbir öğe kaybolmaz ya da yinelenmez')
eq(egitim_test_bol(veri, 0.3, 42), r, 'aynı tohum aynı bölmeyi verir')
ok(egitim_test_bol(veri, 0.3, 43) != r, 'farklı tohum farklı bölme verir')
ok(r['test'] != [7, 8, 9], 'test kısmı verinin sonu değildir (karıştırılmış)', got=r['test'])
sira = list(range(10))
random.Random(42).shuffle(sira)
eq(r['test'], sira[:3], 'test, karıştırılmış indekslerin ilk kısmıdır')
eq(r['egitim'], sira[3:], 'eğitim, karıştırılmış indekslerin kalanıdır')
r = egitim_test_bol(['a', 'b'], 0.01, 0)
eq((len(r['egitim']), len(r['test'])), (1, 1), 'çok küçük oranda bile test boş kalmaz')
r = egitim_test_bol(['a', 'b', 'c'], 0.99, 0)
eq((len(r['egitim']), len(r['test'])), (1, 2), 'çok büyük oranda bile eğitim boş kalmaz')
rng = random.Random(1201)
for _ in range(25):
    n = rng.randint(2, 60)
    v = [(i, rng.random()) for i in range(n)]
    oran, t = round(rng.uniform(0.05, 0.95), 2), rng.randint(0, 9999)
    r = egitim_test_bol(v, oran, t)
    s = list(range(n))
    random.Random(t).shuffle(s)
    k = min(max(round(n * oran), 1), n - 1)
    eq(r['test'], [v[i] for i in s[:k]], 'rastgele veride test bağımsız referansla aynı')
    eq(r['egitim'], [v[i] for i in s[k:]], 'rastgele veride eğitim bağımsız referansla aynı')
    eq(len(set(r['egitim']) & set(r['test'])), 0, 'eğitim ve test kesişmez')
v = [3, 1, 2]
egitim_test_bol(v, 0.5, 1)
eq(v, [3, 1, 2], 'veri değişmez')
for a in ([None, 0.2, 0], [[], 0.2, 0], [[1], 0.2, 0], [(1, 2), 0.2, 0], [[1, 2], 0, 0], [[1, 2], 1, 0], [[1, 2], -0.1, 0], [[1, 2], None, 0], [[1, 2], True, 0], [[1, 2], float('nan'), 0], [[1, 2], 0.2, 1.5], [[1, 2], 0.2, True], [[1, 2], 0.2, None]):
    raises(ValueError, egitim_test_bol, *a, msg='bozuk girdi reddedilir')
```

```hint
Veriyi değil, indeks listesini karıştır: `sira = list(range(n)); random.Random(tohum).shuffle(sira)`. Sonra `sira[:k]` test, `sira[k:]` eğitim.
```
:::

::: gorev 2 · L2 cezası ağırlığı nasıl küçültür?
`ridge_agirlik(x, y, lam)` işlevini yaz. Model kesişimsiz doğrudur: $\hat{y} = wx$.

- `x`, `y`: aynı uzunlukta, boş olmayan sayı listeleri. `lam`: negatif olmayan sayı.
- `w`: $\dfrac{\sum x_i y_i}{\sum x_i^2 + \lambda}$. Payda sıfırsa (`lam = 0` ve bütün `x` sıfır) `ValueError`.
- `egitim_hatasi`: bu `w` ile ortalama kare hata $\frac{1}{n}\sum (y_i - w x_i)^2$ (ceza terimi **dahil değil**).
- `kuculme`: `w / w0`; `w0` cezasız (`lam = 0`) çözümdür. `w0` tanımsızsa ya da sıfırsa `None`.
- Dönüş: `{'w': ..., 'egitim_hatasi': ..., 'kuculme': ...}`; 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç cezayı paydaya değil paya ekliyor: ceza büyüdükçe ağırlık küçüleceğine büyüyor.

```starter
def ridge_agirlik(x, y, lam):
    sxy = sum(a * b for a, b in zip(x, y))
    sxx = sum(a * a for a in x)
    w = (sxy + lam) / sxx
    hata = sum((b - w * a) ** 2 for a, b in zip(x, y)) / len(x)
    return {'w': round(w, 9), 'egitim_hatasi': round(hata, 9), 'kuculme': None}
```

```solution
def ridge_agirlik(x, y, lam):
    import math
    for v in (x, y):
        if not isinstance(v, list) or not v or any(isinstance(a, bool) or not isinstance(a, (int, float)) or not math.isfinite(a) for a in v):
            raise ValueError('boş olmayan sayı listesi gerekli')
    if len(x) != len(y):
        raise ValueError('x ve y aynı uzunlukta olmalı')
    if isinstance(lam, bool) or not isinstance(lam, (int, float)) or not math.isfinite(lam) or lam < 0:
        raise ValueError('lam negatif olmayan sayı olmalı')
    sxy = sum(a * b for a, b in zip(x, y))
    sxx = sum(a * a for a in x)
    if sxx + lam == 0:
        raise ValueError('payda sıfır')
    w = sxy / (sxx + lam)
    hata = sum((b - w * a) ** 2 for a, b in zip(x, y)) / len(x)
    w0 = sxy / sxx if sxx else None
    return {'w': round(w, 9), 'egitim_hatasi': round(hata, 9), 'kuculme': round(w / w0, 9) if w0 else None}
```

```test
need('ridge_agirlik')
import random

eq(ridge_agirlik([1, 2, 3], [2, 4, 6], 0), {'w': 2.0, 'egitim_hatasi': 0.0, 'kuculme': 1.0}, 'cezasız: tam uyum')
r = ridge_agirlik([1, 2, 3], [2, 4, 6], 14)
eq(r['w'], 1.0, 'lam = Σx² iken ağırlık yarıya iner')
eq(r['kuculme'], 0.5, 'küçülme oranı Σx² / (Σx² + lam)')
ok(r['egitim_hatasi'] > 0, 'ceza eğitim hatasını artırır', got=r)
ws = [ridge_agirlik([1, 2, 3], [2, 4, 6], lam)['w'] for lam in (0, 1, 10, 100, 1000)]
ok(all(ws[i] > ws[i + 1] > 0 for i in range(4)), 'ceza arttıkça ağırlık sıfıra doğru tekdüze küçülür', got=ws)
az = ridge_agirlik([1, 2], [2, 4], 5)['kuculme']
cok = ridge_agirlik([1, 2] * 50, [2, 4] * 50, 5)['kuculme']
ok(az < cok and cok > 0.95, 'veri arttıkça aynı cezanın etkisi kaybolur', got=(az, cok))
eq(ridge_agirlik([0, 0], [1, 2], 3), {'w': 0.0, 'egitim_hatasi': 2.5, 'kuculme': None}, 'x bilgi taşımıyorsa ceza ağırlığı sıfırda tutar')
eq(ridge_agirlik([1, -1], [1, 1], 2)['kuculme'], None, 'cezasız ağırlık sıfırsa küçülme tanımsız')
rng = random.Random(1202)
for _ in range(25):
    n = rng.randint(1, 20)
    x = [round(rng.uniform(-3, 3), 2) or 0.5 for _ in range(n)]
    y = [round(1.7 * a + rng.gauss(0, 1), 3) for a in x]
    lam = rng.choice([0, 0.1, 1, 5, 50])
    r = ridge_agirlik(x, y, lam)
    sxx = sum(a * a for a in x)
    w = sum(a * b for a, b in zip(x, y)) / (sxx + lam)
    yakin(r['w'], w, 'rastgele veride ağırlık', tol=1e-8)
    yakin(sum((w * a - b) * a for a, b in zip(x, y)) + lam * w, 0.0, 'cezalı kaybın türevi çözümde sıfır', tol=1e-6)
    for d in (-0.01, 0.01):
        def amac(v):
            return sum((b - v * a) ** 2 for a, b in zip(x, y)) + lam * v * v
        ok(amac(r['w']) <= amac(r['w'] + d) + 1e-9, 'çözüm cezalı kaybı en küçük yapar')
eq(ridge_agirlik([1], [1], 2), {'w': 0.333333333, 'egitim_hatasi': 0.444444444, 'kuculme': 0.333333333}, '9 basamağa yuvarlanır')
for a in ([None, [1], 1], [[1], None, 1], [[], [], 1], [[1, 2], [1], 1], [[0, 0], [1, 2], 0], [[1, 2], [2, 4], -0.5], [[1], [1], -1], [[1], [1], None], [[1], [1], True], [[1, "2"], [1, 2], 1], [[True], [1], 1], [(1,), [1], 1], [[float('nan')], [1], 1], [[1], [float('inf')], 1], [[1], [1], float('nan')], [[1], [1], float('inf')]):
    raises(ValueError, ridge_agirlik, *a, msg='bozuk girdi reddedilir')
```

```hint
`w = Σxy / (Σx² + lam)`. Eğitim hatası ceza terimini içermez: yalnız `(y − w·x)²` ortalaması.
```
:::

::: gorev 3 · Overfitting ne zaman başladı?
`egri_ozeti(egitim, dogrulama)` işlevini yaz. Eğitim boyunca her adımda ölçülen iki hata serisini alır.

- `egitim`, `dogrulama`: aynı uzunlukta, boş olmayan, negatif olmayan sayı listeleri (adım 0, 1, 2, ...).
- `en_iyi_adim`: doğrulama hatasının en küçük olduğu **ilk** adımın indeksi (`early stopping` noktası).
- `bosluk`: her adım için `dogrulama - egitim` (`generalization gap`); 9 basamağa yuvarlanır.
- `asiri_ogrenme`: `en_iyi_adim`'dan sonraki adımlardan, doğrulama hatası en iyi değerden büyük **ve** eğitim hatası `en_iyi_adim`'daki eğitim hatasından küçük olanların indeks listesi.
- Dönüş: `{'en_iyi_adim': ..., 'en_iyi_dogrulama': ..., 'bosluk': [...], 'asiri_ogrenme': [...]}`.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç en iyi adımı **eğitim** hatasına göre seçiyor: ezberin en ileri olduğu son adımı en iyi sanıyor.

```starter
def egri_ozeti(egitim, dogrulama):
    i = egitim.index(min(egitim))
    return {'en_iyi_adim': i, 'en_iyi_dogrulama': dogrulama[i], 'bosluk': [round(d - e, 9) for e, d in zip(egitim, dogrulama)], 'asiri_ogrenme': []}
```

```solution
def egri_ozeti(egitim, dogrulama):
    import math
    for v in (egitim, dogrulama):
        if not isinstance(v, list) or not v or any(isinstance(a, bool) or not isinstance(a, (int, float)) or not math.isfinite(a) or a < 0 for a in v):
            raise ValueError('negatif olmayan sayılardan oluşan boş olmayan liste gerekli')
    if len(egitim) != len(dogrulama):
        raise ValueError('seriler aynı uzunlukta olmalı')
    en_iyi = min(dogrulama)
    i = dogrulama.index(en_iyi)
    asiri = [j for j in range(i + 1, len(egitim)) if dogrulama[j] > en_iyi and egitim[j] < egitim[i]]
    return {
        'en_iyi_adim': i,
        'en_iyi_dogrulama': en_iyi,
        'bosluk': [round(d - e, 9) for e, d in zip(egitim, dogrulama)],
        'asiri_ogrenme': asiri,
    }
```

```test
need('egri_ozeti')
import random

e = [1.0, 0.6, 0.4, 0.25, 0.15, 0.08]
d = [1.1, 0.7, 0.55, 0.5, 0.58, 0.7]
r = egri_ozeti(e, d)
eq(r['en_iyi_adim'], 3, 'doğrulama hatasının en düşük olduğu adım, eğitimin değil')
eq(r['en_iyi_dogrulama'], 0.5, 'en iyi doğrulama hatası')
eq(r['asiri_ogrenme'], [4, 5], 'sonraki adımlarda eğitim düşerken doğrulama yükseliyor')
eq(r['bosluk'], [0.1, 0.1, 0.15, 0.25, 0.43, 0.62], 'boşluk giderek açılıyor')
r = egri_ozeti([0.9, 0.5, 0.3], [1.0, 0.6, 0.4])
eq((r['en_iyi_adim'], r['asiri_ogrenme']), (2, []), 'ikisi birlikte düşüyorsa overfitting yok')
r = egri_ozeti([0.5, 0.4, 0.3], [0.6, 0.6, 0.7])
eq(r['en_iyi_adim'], 0, 'eşit en küçük değerlerde ilk adım')
eq(r['asiri_ogrenme'], [2], 'adım 1 de doğrulama en iyiden büyük değil; adım 2 de büyük')
r = egri_ozeti([0.5, 0.6, 0.7], [0.4, 0.5, 0.6])
eq(r['asiri_ogrenme'], [], 'eğitim hatası da yükseliyorsa bu overfitting değil, ıraksama')
eq(egri_ozeti([0.3], [0.4]), {'en_iyi_adim': 0, 'en_iyi_dogrulama': 0.4, 'bosluk': [0.1], 'asiri_ogrenme': []}, 'tek adım')
rng = random.Random(1203)
for _ in range(25):
    n = rng.randint(1, 20)
    e = [round(rng.uniform(0, 2), 2) for _ in range(n)]
    d = [round(rng.uniform(0, 2), 2) for _ in range(n)]
    r = egri_ozeti(e, d)
    i = 0
    for j in range(n):
        if d[j] < d[i]:
            i = j
    eq(r['en_iyi_adim'], i, 'rastgele eğride en iyi adım')
    eq(r['asiri_ogrenme'], [j for j in range(n) if j > i and d[j] > d[i] and e[j] < e[i]], 'rastgele eğride overfitting adımları')
    for b, a, c in zip(r['bosluk'], e, d):
        yakin(b, c - a, 'boşluk = doğrulama - eğitim', tol=1e-9)
e, d = [0.5, 0.4], [0.6, 0.7]
egri_ozeti(e, d)
eq((e, d), ([0.5, 0.4], [0.6, 0.7]), 'girdiler değişmez')
for a, b in [(None, [1.0]), ([1.0], None), ([], []), ([1.0], []), ([1.0, 2.0], [1.0]), ([-0.1], [1.0]), ([1.0], [-1.0]), ([1, "2"], [1, 2]), ([True], [1.0]), ((1.0,), [1.0]), ([float('nan')], [1.0]), ([1.0], [float('inf')])]:
    raises(ValueError, egri_ozeti, a, b, msg='bozuk girdi reddedilir')
```

```hint
`en_iyi = min(dogrulama)`; `i = dogrulama.index(en_iyi)` ilk indeksi verir. Overfitting adımları: `j > i`, `dogrulama[j] > en_iyi` ve `egitim[j] < egitim[i]`.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur; her adım bu derste hesapladığın bir sayıya ya da örneğe dayanır.

1. **Soru (15 sn).** "Sınavın cevap anahtarını ezberleyen öğrenci konuyu biliyor mu?"
2. **Örnek (30 sn).** Tahmin adımı: ezberleyen model eğitimde yüzde 100, görmediği veride yüzde 25. "Eğitim skoru bize hiçbir şey söylemedi."
3. **Çare (30 sn).** "Modeli büyük ağırlıklar için cezalandırırız ve doğrulama hatası yükselmeye başladığı an eğitimi durdururuz."
4. **Kural (25 sn).** "Test verisine bakıp karar veren, test verisini eğitime katmış olur. Ayar için ayrı bir parça ayrılır."
5. **Kapanış (20 sn).** "Bir modelin değeri, görmediği veride ne yaptığıdır."
:::

::: anlat Sınır
Bu ders eğitim/test ayrımını, tek değişkenli L2 cezasını ve eğitim eğrilerini anlatır. Rastgele bölme, örneklerin bağımsız olduğunu varsayar: zaman serilerinde, aynı kullanıcıdan gelen kayıtlarda ya da birbirinin kopyası olan örneklerde rastgele bölme bilgiyi teste sızdırır ve ölçümü iyimser yapar; orada zamana ya da gruba göre bölmek gerekir. Tek bir bölme gürültülüdür; küçük veride `cross-validation` daha güvenilirdir. Görev 2'deki kapalı çözüm kesişimsiz tek değişken içindir; çok değişkende ceza her ağırlığı farklı oranda küçültür ve özelliklerin ölçeğine duyarlıdır. `L1` cezası ağırlıkları tam sıfıra indirir (seyreklik) ve burada işlenmez. Klasik bias-variance tablosu çok büyük ağlarda tam tutmaz: model veriyi ezberleyecek büyüklüğü geçtikten sonra test hatası yeniden düşebilir (`double descent`). Görev 3'teki overfitting ölçütü basit bir kuraldır; gürültülü eğrilerde tek bir adımın yükselmesi overfitting sayılmaz, pratikte bir sabır (`patience`) penceresi kullanılır.

Kaynaklar: [Hastie, Tibshirani ve Friedman 2009 - The Elements of Statistical Learning, Bölüm 7](https://hastie.su.domains/ElemStatLearn/), [Goodfellow, Bengio ve Courville 2016 - Deep Learning, Bölüm 7: Regularization](https://www.deeplearningbook.org/contents/regularization.html), [Belkin vd. 2019 - Reconciling modern machine-learning practice and the classical bias-variance trade-off](https://doi.org/10.1073/pnas.1903070116), [Nakkiran vd. 2019 - Deep Double Descent](https://arxiv.org/abs/1912.02292).
:::

::: dusun
Bir ekip modelinin hiperparametrelerini test doğruluğuna bakarak 200 kez ayarlıyor ve en iyi sonucu %94 olarak raporluyor. Bu sayı neden iyimserdir? Aynı veriyle dürüst bir ölçüm yapmak için bölmeyi nasıl değiştirirdin ve %94'ün yerine hangi sayıyı raporlardın?
:::

::: ozet
- Eğitim hatası genellemeyi ölçmez; model yalnız görmediği veride sınanır.
- Bölme tekrarlanabilir olmalı ve test verisine bakarak karar verilmemelidir; ayar için ayrı bir doğrulama parçası kullanılır.
- L2 cezası ağırlığı `Σx² / (Σx² + λ)` oranında küçültür; veri azken baskındır, veri arttıkça etkisi kaybolur.
- Overfitting, eğitim hatası düşerken doğrulama hatasının yükseldiği noktada başlar; `early stopping` en düşük doğrulama hatasındaki modeli tutar.
- Bias fazla basit modelin, variance fazla esnek modelin hatasıdır; büyük ağlarda bu tablo `double descent` ile karmaşıklaşır.
:::
