---
id: ai-matematik-06
title: "Beklenti, Varyans ve Örnekleme Hatası · Bir Ölçüm Ne Kadar Oynar?"
summary: Bir dağılımın beklentisini ve varyansını hesapla, örneklemden ortalama ve standart hata çıkar ve bir doğruluk oranının kaç örnekle ne kadar güvenilir olduğunu ölç.
---

::: anlat 1. Bir skor tek başına bir şey söylemez
"Model A %91, model B %89 doğruluk aldı." Bu cümleden A'nın daha iyi olduğu sonucu çıkar mı? Test 100 soruluksa hayır: fark, hangi 100 sorunun seçildiğine bağlı şansla açıklanabilir. Test 100.000 soruluksa evet. Aradaki farkı söyleyen şey **örnekleme hatasıdır**.

| Soru | Araç | Görev |
|---|---|---|
| Bir dağılımın "ortası" ve "yayılımı" ne? | Beklenti $\mathbb{E}[X]$, varyans $\mathrm{Var}[X]$ | 1 |
| Elimdeki ölçümlerden ortalama ne kadar güvenilir? | Örneklem varyansı, standart hata | 2 |
| Bir doğruluk oranı kaç örnekle ne kadar oynar? | Oranın standart hatası | 3 |

Tanımlar (ayrık bir değişken için):

$$\mathbb{E}[X] = \sum_i x_i\, p_i \qquad \mathrm{Var}[X] = \sum_i (x_i - \mathbb{E}[X])^2\, p_i$$

Standart sapma varyansın kareköküdür ve verinin kendisiyle aynı birimdedir.
:::

::: anlat 2. Örneklem ve standart hata
Gerçek dağılımı bilmezsin; elinde `n` ölçüm vardır. Bunlardan iki şey hesaplarsın:

**Örneklem ortalaması** $\bar{x} = \frac{1}{n}\sum x_i$ ve **örneklem varyansı**:

$$s^2 = \frac{1}{n - 1}\sum_i (x_i - \bar{x})^2$$

Paydanın `n` değil `n - 1` olması (`Bessel's correction`) bir düzeltmedir: sapmaları gerçek ortalamadan değil, aynı veriden hesapladığın ortalamadan ölçtüğün için yayılımı biraz küçük görürsün; `n - 1` bunu giderir.

Asıl önemli sayı **standart hatadır**: ortalamanın kendisinin ne kadar oynadığı.

$$\mathrm{SE} = \frac{s}{\sqrt{n}}$$

Standart sapma tek bir ölçümün ne kadar oynadığını söyler ve örnek sayısıyla küçülmez. Standart hata ortalamanın ne kadar oynadığını söyler ve $\sqrt{n}$ ile küçülür. Hatayı yarıya indirmek için **dört kat** örnek gerekir; onda birine indirmek için yüz kat.

**Doğruluk gibi bir oran için** her örnek 0 ya da 1'dir ve standart hata kapalı biçimde yazılır:

$$\mathrm{SE}(\hat{p}) = \sqrt{\frac{\hat{p}(1 - \hat{p})}{n}}$$

Oran %50'ye yakınken en büyüktür; %0 ya da %100'e yaklaştıkça küçülür.
:::

::: tahmin Yüz soru mu, on bin soru mu?
Aynı %90 doğruluk iki farklı büyüklükte testle ölçülüyor. Standart hata ne yazdırılır?

```python
p = 0.9
for n in (100, 10000):
    se = (p * (1 - p) / n) ** 0.5
    print(n, round(se, 4))
```

???

```cikti
100 0.03
10000 0.003
```
100 soruluk testte standart hata 3 puandır: "%90" aslında kabaca %84 ile %96 arasında bir yerdir (iki standart hata). 10.000 soruluk testte 0,3 puandır. Örnek sayısı 100 kat arttı, hata 10 kat küçüldü: $\sqrt{100} = 10$. İki modelin 100 soruluk bir testteki 2 puanlık farkı, tek bir standart hatadan küçüktür.
:::

::: gorev 1 · Beklenti ve varyans
`beklenti_varyans(degerler, olasiliklar)` işlevini yaz.

- `degerler`: boş olmayan sayı listesi. `olasiliklar`: aynı uzunlukta, negatif olmayan sayılardan oluşan ve toplamı 1 olan (`1e-9` toleransla) liste. `NaN` ve sonsuz değerler olasılık değildir, reddedilir.
- Dönüş: `{'beklenti': E[X], 'varyans': Var[X], 'standart_sapma': √Var[X]}`; 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç olasılıkları yok sayıp değerlerin düz ortalamasını alıyor. Eşit olmayan olasılıklarda yanlıştır.

```starter
def beklenti_varyans(degerler, olasiliklar):
    e = sum(degerler) / len(degerler)
    v = sum((x - e) ** 2 for x in degerler) / len(degerler)
    return {'beklenti': round(e, 9), 'varyans': round(v, 9), 'standart_sapma': round(v ** 0.5, 9)}
```

```solution
def beklenti_varyans(degerler, olasiliklar):
    def sayilar(v):
        return isinstance(v, list) and v and not any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in v)
    if not sayilar(degerler) or not sayilar(olasiliklar) or len(degerler) != len(olasiliklar):
        raise ValueError('aynı uzunlukta, boş olmayan iki sayı listesi gerekli')
    if any(not 0 <= p <= 1 for p in olasiliklar) or abs(sum(olasiliklar) - 1) > 1e-9:
        raise ValueError('olasılıklar negatif olmamalı ve 1 e toplanmalı')
    e = sum(x * p for x, p in zip(degerler, olasiliklar))
    v = sum((x - e) ** 2 * p for x, p in zip(degerler, olasiliklar))
    return {'beklenti': round(e, 9), 'varyans': round(v, 9), 'standart_sapma': round(v ** 0.5, 9)}
```

```test
need('beklenti_varyans')
import math, random

eq(beklenti_varyans([0, 1], [0.5, 0.5]), {'beklenti': 0.5, 'varyans': 0.25, 'standart_sapma': 0.5}, 'adil yazı tura')
r = beklenti_varyans([0, 1], [0.1, 0.9])
yakin(r['beklenti'], 0.9, 'yüzde 90 başarı: beklenti', tol=1e-9)
yakin(r['varyans'], 0.09, 'yüzde 90 başarı: varyans p(1-p)', tol=1e-9)
r = beklenti_varyans([1, 2, 3, 4, 5, 6], [1 / 6] * 6)
yakin(r['beklenti'], 3.5, 'adil zar', tol=1e-9)
yakin(r['varyans'], 35 / 12, 'adil zarın varyansı', tol=1e-8)
eq(beklenti_varyans([7], [1]), {'beklenti': 7.0, 'varyans': 0.0, 'standart_sapma': 0.0}, 'kesin değerin varyansı sıfır')
r = beklenti_varyans([0, 100], [0.99, 0.01])
yakin(r['beklenti'], 1.0, 'nadir büyük değer: beklenti 1, düz ortalama 50 değil', tol=1e-9)
rng = random.Random(601)
for _ in range(25):
    n = rng.randint(1, 8)
    xs = [round(rng.uniform(-5, 5), 2) for _ in range(n)]
    w = [rng.randint(0, 9) for _ in range(n)]
    if sum(w) == 0:
        w[0] = 1
    ps = [x / sum(w) for x in w]
    e = math.fsum(x * p for x, p in zip(xs, ps))
    v = math.fsum(x * x * p for x, p in zip(xs, ps)) - e * e
    r = beklenti_varyans(xs, ps)
    yakin(r['beklenti'], e, 'rastgele dağılımda beklenti', tol=1e-7)
    yakin(r['varyans'], v, 'varyans = E[X²] - E[X]² ile aynı', tol=1e-6)
    yakin(r['standart_sapma'] ** 2, r['varyans'], 'standart sapma varyansın karekökü', tol=1e-6)
for a in ([[], []], [[1, 2], [1.0]], [[1, 2], [0.5, 0.6]], [[1, 2], [-0.5, 1.5]], [None, [1]], [[1], None], [[1, "2"], [0.5, 0.5]], [[True], [1]], [(1, 2), [0.5, 0.5]], [[1], [True]], [[1], [float('nan')]], [[1, 2], [float('nan'), 1.0]], [[1], [float('inf')]]):
    raises(ValueError, beklenti_varyans, *a, msg='bozuk girdi reddedilir')
```

```hint
Beklenti `Σ x·p`. Varyans `Σ (x − E)²·p`. Her iki toplamda da olasılıkla çarpmayı unutma.
```
:::

::: gorev 2 · Örneklem ortalaması, varyansı ve standart hata
`orneklem_ozeti(veri)` işlevini yaz.

- `veri`: en az **iki** sayıdan oluşan liste (tek ölçümden yayılım tahmin edilemez).
- `ortalama`: örneklem ortalaması. `varyans`: `n - 1`'e bölünmüş örneklem varyansı. `standart_sapma`: karekökü. `standart_hata`: `standart_sapma / √n`.
- Dönüş: bu dört anahtar ve `'n'`; kayan noktalı değerler 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç varyansı `n`'e bölüyor ve standart hata yerine standart sapmayı döndürüyor: ortalamanın belirsizliği örnek sayısıyla hiç küçülmüyor.

```starter
def orneklem_ozeti(veri):
    n = len(veri)
    m = sum(veri) / n
    v = sum((x - m) ** 2 for x in veri) / n
    return {'n': n, 'ortalama': round(m, 9), 'varyans': round(v, 9), 'standart_sapma': round(v ** 0.5, 9), 'standart_hata': round(v ** 0.5, 9)}
```

```solution
def orneklem_ozeti(veri):
    if not isinstance(veri, list) or len(veri) < 2 or any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in veri):
        raise ValueError('veri en az iki sayıdan oluşan liste olmalı')
    n = len(veri)
    m = sum(veri) / n
    v = sum((x - m) ** 2 for x in veri) / (n - 1)
    s = v ** 0.5
    return {'n': n, 'ortalama': round(m, 9), 'varyans': round(v, 9), 'standart_sapma': round(s, 9), 'standart_hata': round(s / n ** 0.5, 9)}
```

```test
need('orneklem_ozeti')
import random, statistics

r = orneklem_ozeti([2, 4, 4, 4, 5, 5, 7, 9])
eq((r['n'], r['ortalama']), (8, 5.0), 'ortalama')
yakin(r['varyans'], 32 / 7, 'n - 1 e bölünmüş varyans', tol=1e-8)
yakin(r['standart_hata'], (32 / 7) ** 0.5 / 8 ** 0.5, 'standart hata s / kök n', tol=1e-8)
eq(orneklem_ozeti([3, 3, 3]), {'n': 3, 'ortalama': 3.0, 'varyans': 0.0, 'standart_sapma': 0.0, 'standart_hata': 0.0}, 'sabit veri')
eq(orneklem_ozeti([0, 2])['varyans'], 2.0, 'iki ölçüm: n - 1 = 1')
kucuk = orneklem_ozeti([1, 2, 3, 4])
buyuk = orneklem_ozeti([1, 2, 3, 4] * 25)
ok(buyuk['standart_hata'] < kucuk['standart_hata'] / 4, '25 kat veri: standart hata yaklaşık 5 kat küçülür', got=(kucuk['standart_hata'], buyuk['standart_hata']))
ok(abs(buyuk['standart_sapma'] - kucuk['standart_sapma']) < 0.2, 'standart sapma örnek sayısıyla küçülmez')
rng = random.Random(602)
for _ in range(25):
    v = [round(rng.gauss(10, 3), 3) for _ in range(rng.randint(2, 40))]
    r = orneklem_ozeti(v)
    yakin(r['ortalama'], statistics.fmean(v), 'rastgele veride ortalama', tol=1e-7)
    yakin(r['varyans'], statistics.variance(v), 'rastgele veride varyans', tol=1e-6)
    yakin(r['standart_hata'], statistics.stdev(v) / len(v) ** 0.5, 'rastgele veride standart hata', tol=1e-7)
v = [1, 2, 3]
orneklem_ozeti(v)
eq(v, [1, 2, 3], 'girdi değişmez')
for kotu in (None, [], [5], [1, "2"], [True, False], (1, 2, 3), "123"):
    raises(ValueError, orneklem_ozeti, kotu, msg='bozuk ya da tek öğeli veri reddedilir')
```

```hint
Varyansın paydası `n - 1`. Standart hata, standart sapmanın `√n`'e bölünmüş hâlidir.
```
:::

::: gorev 3 · Bir doğruluk oranı ne kadar güvenilir?
`oran_belirsizligi(dogru, toplam, hedef_hata)` işlevini yaz.

- `dogru`: doğru cevap sayısı, `toplam`: soru sayısı; ikisi de `int`, `0 <= dogru <= toplam` ve `toplam >= 1`.
- `hedef_hata`: ulaşmak istediğin standart hata; `(0, 1)` aralığında sayı.
- `oran`: `dogru / toplam`. `standart_hata`: $\sqrt{\hat{p}(1 - \hat{p}) / n}$.
- `gereken_ornek`: aynı oranda standart hatanın `hedef_hata`'ya inmesi için gereken en küçük örnek sayısı: $\lceil \hat{p}(1 - \hat{p}) / \text{hedef}^2 \rceil$ (`int`).
- Dönüş: bu üç anahtar; kayan noktalı değerler 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç standart hatayı `1 / n` ile küçültüyor (karekök yok) ve gereken örnek sayısını doğrusal ölçekliyor: hatayı yarıya indirmek için iki kat örnek yeter sanıyor.

```starter
def oran_belirsizligi(dogru, toplam, hedef_hata):
    p = dogru / toplam
    se = p * (1 - p) / toplam
    return {'oran': round(p, 9), 'standart_hata': round(se, 9), 'gereken_ornek': int(toplam * se / hedef_hata) + 1}
```

```solution
def oran_belirsizligi(dogru, toplam, hedef_hata):
    import math
    for x in (dogru, toplam):
        if isinstance(x, bool) or not isinstance(x, int):
            raise ValueError('sayımlar int olmalı')
    if toplam < 1 or not 0 <= dogru <= toplam:
        raise ValueError('0 <= dogru <= toplam ve toplam >= 1 olmalı')
    if isinstance(hedef_hata, bool) or not isinstance(hedef_hata, (int, float)) or not 0 < hedef_hata < 1:
        raise ValueError('hedef_hata (0, 1) aralığında olmalı')
    p = dogru / toplam
    return {
        'oran': round(p, 9),
        'standart_hata': round((p * (1 - p) / toplam) ** 0.5, 9),
        'gereken_ornek': math.ceil(round(p * (1 - p) / hedef_hata ** 2, 9)),
    }
```

```test
need('oran_belirsizligi')
import math, random

eq(oran_belirsizligi(90, 100, 0.01), {'oran': 0.9, 'standart_hata': 0.03, 'gereken_ornek': 900}, '100 soruda yüzde 90: 3 puan hata; 1 puan için 900 soru')
eq(oran_belirsizligi(9000, 10000, 0.01)['standart_hata'], 0.003, '10.000 soruda aynı oran: 0.3 puan')
eq(oran_belirsizligi(50, 100, 0.05), {'oran': 0.5, 'standart_hata': 0.05, 'gereken_ornek': 100}, 'yüzde 50 de hata en büyük')
eq(oran_belirsizligi(100, 100, 0.01), {'oran': 1.0, 'standart_hata': 0.0, 'gereken_ornek': 0}, 'hepsi doğruysa formül sıfır verir (Sınır bölümüne bak)')
eq(oran_belirsizligi(0, 1, 0.1), {'oran': 0.0, 'standart_hata': 0.0, 'gereken_ornek': 0}, 'tek soruda sıfır doğru: uç sınırlar geçerlidir')
a = oran_belirsizligi(80, 100, 0.02)['gereken_ornek']
b = oran_belirsizligi(80, 100, 0.01)['gereken_ornek']
eq(b, 4 * a, 'hatayı yarıya indirmek dört kat örnek ister')
ok(isinstance(a, int) and not isinstance(a, bool), 'gereken_ornek int')
rng = random.Random(603)
for _ in range(30):
    n = rng.randint(1, 5000)
    d = rng.randint(0, n)
    h = rng.choice([0.005, 0.01, 0.02, 0.05])
    r = oran_belirsizligi(d, n, h)
    p = d / n
    yakin(r['standart_hata'], math.sqrt(p * (1 - p) / n), 'rastgele sayımda standart hata', tol=1e-8)
    g = r['gereken_ornek']
    ok(math.sqrt(p * (1 - p) / g) <= h + 1e-9 if g > 0 else p * (1 - p) < 1e-9, 'gereken örnek hedefi sağlar', got=(d, n, h, g))
    ok(g <= 1 or math.sqrt(p * (1 - p) / (g - 1)) > h - 1e-9, 'bir eksik örnek hedefi sağlamaz', got=(d, n, h, g))
for a in ([5, 0, 0.01], [-1, 10, 0.01], [11, 10, 0.01], [5.0, 10, 0.01], [5, 10.0, 0.01], [True, 10, 0.01], [5, 10, 0], [5, 10, 1], [5, 10, -0.1], [5, 10, None], [5, 10, True], [5, 10, float('nan')], [5, 10, float('inf')], ["5", 10, 0.01]):
    raises(ValueError, oran_belirsizligi, *a, msg='bozuk girdi reddedilir')
```

```hint
`standart_hata = (p * (1 - p) / n) ** 0.5`. Gereken örnek için formülü `n`'e göre çöz: `n = p * (1 - p) / hedef²`, sonra yukarı yuvarla.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur; her adım bu derste hesapladığın bir sayıya ya da örneğe dayanır.

1. **Soru (15 sn).** "Model A yüzde 91, model B yüzde 89 aldı. A daha mı iyi?"
2. **Cevap (30 sn).** "Test 100 soruluksa bilmiyoruz: her skor yaklaşık 3 puan oynar. 10.000 soruluksa evet: oynama 0,3 puana iner."
3. **Kural (30 sn).** "Belirsizliği yarıya indirmek için dört kat soru gerekir. Onda birine indirmek için yüz kat."
4. **Tuzak (25 sn).** "Tek bir modelin bir ölçümü ne kadar oynar, ortalamanın ne kadar oynar: ikisi farklı şeylerdir ve sık karıştırılır."
5. **Kapanış (20 sn).** "Bir skor bir sayı değil, bir aralıktır. Aralığı söylemeyen sonucu henüz söylememiştir."
:::

::: anlat Sınır
Bu ders beklentiyi, varyansı, örneklem istatistiklerini ve standart hatayı anlatır. Standart hata formülleri örneklerin birbirinden bağımsız seçildiğini varsayar; aynı belgeden alınmış sorular ya da birbirine çok benzeyen örnekler bağımsız değildir ve gerçek belirsizlik formülün verdiğinden büyüktür. Oranın standart hatası, oran 0 ya da 1'e çok yakınken ya da örnek azken yanıltıcıdır: 100 soruda 100 doğru, hatanın sıfır olduğu anlamına gelmez, yalnız formülün orada çalışmadığını gösterir (daha sağlam aralıklar için bkz. `ai-matematik-07`). Standart hata yalnız örnekleme gürültüsünü ölçer; testin yanlı seçilmesi, etiket hataları ya da test verisinin eğitime sızması gibi sistematik hataları göstermez. Bir modeli farklı rastgele tohumlarla eğitmekten gelen değişkenlik de ayrı bir kaynaktır ve burada hesaplanmaz.

Kaynaklar: [Goodfellow, Bengio ve Courville 2016 - Deep Learning, Bölüm 3: Probability and Information Theory](https://www.deeplearningbook.org/contents/prob.html), [Wasserman 2004 - All of Statistics](https://doi.org/10.1007/978-0-387-21736-9), [Miller 2024 - Adding Error Bars to Evals](https://arxiv.org/abs/2411.00640).
:::

::: dusun
Bir makale, yeni bir yöntemin 200 soruluk bir testte doğruluğu %78'den %81'e çıkardığını bildiriyor. Her iki oranın standart hatasını hesapla. Bu fark seni ikna eder mi? Aynı farkı güvenle söyleyebilmek için kabaca kaç soruluk bir test gerekirdi?
:::

::: ozet
- Beklenti olasılıkla ağırlıklı ortalamadır; varyans beklentiden sapmanın karesinin beklentisidir.
- Örneklem varyansı `n - 1`'e bölünür; standart sapma tek bir ölçümün, standart hata ortalamanın oynaklığıdır.
- Standart hata `√n` ile küçülür: hatayı yarıya indirmek dört kat örnek ister.
- Bir oranın standart hatası `√(p(1 − p) / n)`'dir ve %50 civarında en büyüktür.
- Standart hata yalnız örnekleme gürültüsünü ölçer; bağımlı örnekleri ve sistematik hataları görmez.
:::
