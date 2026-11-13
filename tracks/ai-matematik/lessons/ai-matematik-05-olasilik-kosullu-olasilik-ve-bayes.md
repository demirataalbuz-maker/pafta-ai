---
id: ai-matematik-05
title: "Olasılık, Koşullu Olasılık ve Bayes · Kanıt Geldiğinde İnancı Güncellemek"
summary: Ortak dağılımdan marjinal ve koşullu olasılığı çıkar, Bayes kuralıyla bir testin pozitif çıkmasının gerçekte ne anlama geldiğini hesapla ve art arda gelen kanıtlarla inancı adım adım güncelle.
---

::: anlat 1. Model bir olasılık dağılımıdır
Bir dil modeli sıradaki token için bir olasılık dağılımı üretir. Bir sınıflandırıcı her sınıf için bir olasılık verir. Bir alarm sistemi "bu olay yüzde 92 şüpheli" der. Bu sayıları doğru okumak için üç işlemi bilmen gerekir:

| Soru | Araç | Görev |
|---|---|---|
| Test pozitif çıktı; gerçekten pozitif olma olasılığı ne? | Bayes kuralı | 1 |
| İki değişken birlikte nasıl davranıyor; biri diğeri hakkında bilgi veriyor mu? | Ortak, marjinal ve koşullu dağılım | 2 |
| Kanıtlar tek tek geldikçe inanç nasıl değişir? | Ardışık Bayes güncellemesi | 3 |

Temel tanımlar:

- **Ortak olasılık** $P(A, B)$: ikisinin birlikte olma olasılığı.
- **Marjinal olasılık** $P(A) = \sum_b P(A, b)$: diğer değişkeni toplayarak yok etmek.
- **Koşullu olasılık** $P(A \mid B) = \dfrac{P(A, B)}{P(B)}$: `B`'nin olduğunu bildiğinde `A`'nın olasılığı.
- **Bağımsızlık**: $P(A, B) = P(A)\,P(B)$ ise `B`'yi bilmek `A` hakkında hiçbir şey söylemez.
:::

::: anlat 2. Bayes kuralı ve taban oranı
Koşullu olasılığın tanımını iki yönde yazıp eşitlersen Bayes kuralı çıkar:

$$P(H \mid E) = \frac{P(E \mid H)\, P(H)}{P(E)}$$

- $P(H)$: **önsel** (`prior`); kanıttan önceki inanç.
- $P(E \mid H)$: **olabilirlik** (`likelihood`); hipotez doğruysa bu kanıtı görme olasılığı.
- $P(H \mid E)$: **sonsal** (`posterior`); kanıttan sonraki inanç.
- $P(E)$: kanıtın toplam olasılığı; bütün hipotezler üzerinden toplanır.

En sık yapılan hata, $P(E \mid H)$ ile $P(H \mid E)$'yi karıştırmaktır. "Test hastaların %99'unu yakalıyor" cümlesi $P(+ \mid \text{hasta})$'dır. Senin bilmek istediğin ise $P(\text{hasta} \mid +)$'dır ve bu, hastalığın ne kadar yaygın olduğuna (**taban oranı**, `base rate`) bağlıdır.

Nadir bir olayı arayan her sistem bu sorunla karşılaşır. Günde bir milyon olaydan yalnız onu gerçekten kötüyse, %1 yanlış alarm oranı olan çok iyi bir dedektör bile on bin yanlış alarm üretir; gerçek on olay bunların içinde kaybolur. Dedektörün doğruluğu değil, **alarm verdiğinde haklı olma olasılığı** (`precision`) işletmeyi belirler.
:::

::: tahmin Pozitif test ne kadar güvenilir?
Bir hastalık nüfusun %1'inde var. Test hastaların %99'unu yakalıyor, sağlıklıların %5'ine yanlışlıkla pozitif diyor. Pozitif çıkan birinin gerçekten hasta olma olasılığı ne yazdırılır?

```python
onsel = 0.01
duyarlilik = 0.99
yanlis_pozitif = 0.05

pozitif = duyarlilik * onsel + yanlis_pozitif * (1 - onsel)
sonsal = duyarlilik * onsel / pozitif
print(round(sonsal, 4))
```

???

```cikti
0.1667
```
Yalnız %16,7. 10.000 kişi düşün: 100'ü hasta, 99'u pozitif çıkar. 9.900 sağlıklının %5'i, yani 495 kişi de pozitif çıkar. Toplam 594 pozitifin yalnız 99'u gerçekten hastadır: $99 / 594 \approx 0{,}167$. Test kötü değil; hastalık nadir. Önsel küçükken, çok iyi bir test bile çoğunlukla yanlış alarm verir.
:::

::: gorev 1 · Bayes kuralı: pozitif sonucun anlamı
`sonsal_olasilik(onsel, duyarlilik, yanlis_pozitif)` işlevini yaz.

- `onsel`: $P(H)$. `duyarlilik`: $P(+ \mid H)$. `yanlis_pozitif`: $P(+ \mid \neg H)$. Üçü de `[0, 1]` aralığında sayı.
- Dönüş: $P(H \mid +)$, 9 basamağa yuvarlanmış.
- Pozitif sonucun toplam olasılığı sıfırsa (hiç pozitif çıkmaz) sonsal tanımsızdır: `ValueError`.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç taban oranını yok sayıp duyarlılığı döndürüyor: `P(+|H)` ile `P(H|+)`'yı karıştırma hatası.

```starter
def sonsal_olasilik(onsel, duyarlilik, yanlis_pozitif):
    return duyarlilik
```

```solution
def sonsal_olasilik(onsel, duyarlilik, yanlis_pozitif):
    for x in (onsel, duyarlilik, yanlis_pozitif):
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not 0 <= x <= 1:
            raise ValueError('olasılık [0, 1] aralığında sayı olmalı')
    pozitif = duyarlilik * onsel + yanlis_pozitif * (1 - onsel)
    if pozitif == 0:
        raise ValueError('pozitif sonuç olasılığı sıfır')
    return round(duyarlilik * onsel / pozitif, 9)
```

```test
need('sonsal_olasilik')
import random
from fractions import Fraction

yakin(sonsal_olasilik(0.01, 0.99, 0.05), 1 / 6, 'nadir hastalık: pozitif sonucun altıda biri gerçek', tol=1e-8)
eq(sonsal_olasilik(0.5, 0.9, 0.1), 0.9, 'önsel yarı yarıya ise sonsal duyarlılıkla aynı çıkar')
eq(sonsal_olasilik(0.2, 0.7, 0.7), 0.2, 'test bilgi vermiyorsa sonsal önsele eşit')
eq(sonsal_olasilik(1, 0.3, 0.9), 1.0, 'önsel kesinse kanıt değiştirmez')
eq(sonsal_olasilik(0, 0.99, 0.01), 0.0, 'önsel sıfırsa sonsal sıfır')
eq(sonsal_olasilik(0.001, 1, 0), 1.0, 'hiç yanlış pozitif yoksa pozitif kesindir')
ok(sonsal_olasilik(0.001, 0.99, 0.01) < 0.1, 'binde bir taban oranında yüzde 99 doğru test bile çoğunlukla yanılır')
ok(sonsal_olasilik(0.1, 0.9, 0.2) < 0.9, 'sonsal duyarlılık değildir')
rng = random.Random(501)
for _ in range(30):
    p, d, y = (Fraction(rng.randint(1, 99), 100) for _ in range(3))
    yakin(sonsal_olasilik(float(p), float(d), float(y)), float(d * p / (d * p + y * (1 - p))), 'rastgele değerlerde kesirli referansla aynı', tol=1e-8)
raises(ValueError, sonsal_olasilik, 0.5, 0, 0, msg='hiç pozitif çıkmıyorsa sonsal tanımsız')
raises(ValueError, sonsal_olasilik, 0, 0.9, 0, msg='hiç pozitif çıkmıyorsa sonsal tanımsız')
for a in ([1.1, 0.5, 0.5], [0.5, -0.1, 0.5], [0.5, 0.5, 2], [None, 0.5, 0.5], [0.5, "0.5", 0.5], [True, 0.5, 0.5], [0.5, 0.5, False], [float('nan'), 0.5, 0.5], [0.5, float('nan'), 0.5], [0.5, 0.5, float('nan')]):
    raises(ValueError, sonsal_olasilik, *a, msg='bozuk girdi reddedilir')
```

```hint
Önce pozitif çıkma olasılığını bul: `duyarlilik * onsel + yanlis_pozitif * (1 - onsel)`. Sonsal, bu toplamın içindeki "gerçek pozitif" payıdır.
```
:::

::: gorev 2 · Ortak dağılımdan marjinal, koşullu ve bağımsızlık
`dagilim_ozeti(ortak)` işlevini yaz.

- `ortak`: boş olmayan `dict`; anahtarlar `(x, y)` biçiminde iki öğeli demetler, değerler negatif olmayan sayılar. Değerlerin toplamı 1 olmalıdır (`1e-9` toleransla). `NaN` ve sonsuz değerler olasılık değildir, reddedilir.
- `marjinal_x`: `{x: P(x)}`. `marjinal_y`: `{y: P(y)}`.
- `kosullu_y_x`: `{x: {y: P(y | x)}}`; yalnız `P(x) > 0` olan `x` değerleri ve o `x` ile sözlükte geçen `y` değerleri için.
- `bagimsiz`: her `(x, y)` birleşimi için (sözlükte olmayan birleşimin olasılığı 0 sayılır) `|P(x, y) - P(x) P(y)| <= 1e-9` ise `True`.
- Olasılıklar 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç koşullu olasılığı normalleştirmiyor (ortak olasılığı aynen yazıyor) ve bağımsızlığı her zaman `True` sayıyor.

```starter
def dagilim_ozeti(ortak):
    mx, my, k = {}, {}, {}
    for (x, y), p in ortak.items():
        mx[x] = mx.get(x, 0) + p
        my[y] = my.get(y, 0) + p
        k.setdefault(x, {})[y] = p
    return {'marjinal_x': mx, 'marjinal_y': my, 'kosullu_y_x': k, 'bagimsiz': True}
```

```solution
def dagilim_ozeti(ortak):
    if not isinstance(ortak, dict) or not ortak:
        raise ValueError('ortak boş olmayan dict olmalı')
    for k, p in ortak.items():
        if not isinstance(k, tuple) or len(k) != 2:
            raise ValueError('anahtar (x, y) demeti olmalı')
        if isinstance(p, bool) or not isinstance(p, (int, float)) or not 0 <= p <= 1:
            raise ValueError('olasılık [0, 1] aralığında sonlu sayı olmalı')
    if abs(sum(ortak.values()) - 1) > 1e-9:
        raise ValueError('olasılıklar 1 e toplanmalı')
    mx, my = {}, {}
    for (x, y), p in ortak.items():
        mx[x] = mx.get(x, 0.0) + p
        my[y] = my.get(y, 0.0) + p
    kosullu = {}
    for (x, y), p in ortak.items():
        if mx[x] > 0:
            kosullu.setdefault(x, {})[y] = round(p / mx[x], 9)
    bagimsiz = all(abs(ortak.get((x, y), 0.0) - mx[x] * my[y]) <= 1e-9 for x in mx for y in my)
    return {
        'marjinal_x': {x: round(p, 9) for x, p in mx.items()},
        'marjinal_y': {y: round(p, 9) for y, p in my.items()},
        'kosullu_y_x': kosullu,
        'bagimsiz': bagimsiz,
    }
```

```test
need('dagilim_ozeti')
import random

r = dagilim_ozeti({('yagmur', 'gec'): 0.2, ('yagmur', 'vaktinde'): 0.1, ('gunes', 'gec'): 0.1, ('gunes', 'vaktinde'): 0.6})
yakin(r['marjinal_x']['yagmur'], 0.3, 'P(yağmur)', tol=1e-9)
yakin(r['marjinal_y']['gec'], 0.3, 'P(geç)', tol=1e-9)
yakin(r['kosullu_y_x']['yagmur']['gec'], 2 / 3, 'P(geç | yağmur)', tol=1e-8)
yakin(r['kosullu_y_x']['gunes']['gec'], 1 / 7, 'P(geç | güneş)', tol=1e-8)
eq(r['bagimsiz'], False, 'yağmur gecikmeyi etkiliyor')
r = dagilim_ozeti({('a', 0): 0.12, ('a', 1): 0.18, ('b', 0): 0.28, ('b', 1): 0.42})
eq(r['bagimsiz'], True, 'çarpım biçimindeki dağılım bağımsızdır')
yakin(r['kosullu_y_x']['a'][1], 0.6, 'bağımsızsa koşullu marjinale eşit', tol=1e-9)
yakin(r['kosullu_y_x']['b'][1], 0.6, 'bağımsızsa koşullu marjinale eşit', tol=1e-9)
r = dagilim_ozeti({('a', 0): 0.5, ('b', 1): 0.5})
eq(r['bagimsiz'], False, 'eksik birleşimler 0 sayılır: tam bağımlı dağılım')
eq(r['kosullu_y_x'], {'a': {0: 1.0}, 'b': {1: 1.0}}, 'x bilinince y kesin')
r = dagilim_ozeti({('a', 0): 1.0, ('b', 0): 0.0})
eq(sorted(r['kosullu_y_x']), ['a'], 'P(x) = 0 olan x için koşullu yok')
rng = random.Random(502)
for _ in range(25):
    xs, ys = range(rng.randint(1, 4)), range(rng.randint(1, 4))
    agirlik = {(x, y): rng.randint(0, 9) for x in xs for y in ys}
    t = sum(agirlik.values()) or 1
    if sum(agirlik.values()) == 0:
        agirlik[(0, 0)] = 1
    ortak = {k: w / t for k, w in agirlik.items()}
    r = dagilim_ozeti(ortak)
    yakin(sum(r['marjinal_x'].values()), 1.0, 'marjinal x toplamı 1', tol=1e-7)
    yakin(sum(r['marjinal_y'].values()), 1.0, 'marjinal y toplamı 1', tol=1e-7)
    for x, d in r['kosullu_y_x'].items():
        yakin(sum(d.values()), 1.0, 'her koşullu dağılımın toplamı 1', tol=1e-7)
        for y, p in d.items():
            yakin(p * r['marjinal_x'][x], ortak[(x, y)], 'P(y|x) P(x) = P(x, y)', tol=1e-7)
o = {('a', 0): 0.5, ('b', 1): 0.5}
dagilim_ozeti(o)
eq(o, {('a', 0): 0.5, ('b', 1): 0.5}, 'girdi değişmez')
for kotu in (None, {}, {('a', 0): 0.5}, {('a', 0): 0.7, ('b', 0): 0.7}, {'a': 1.0}, {'ab': 1.0}, {('a',): 1.0}, {('a', 0, 1): 1.0}, {('a', 0): -0.5, ('b', 0): 1.5}, {('a', 0): True}, {('a', 0): '1'}, [(('a', 0), 1.0)], {('x', 'y'): float('nan')}, {('a', 0): float('nan'), ('b', 0): 1.0}, {('a', 0): float('inf')}):
    raises(ValueError, dagilim_ozeti, kotu, msg='bozuk dağılım reddedilir')
```

```hint
İki sözlükte topla: `mx[x] += p`, `my[y] += p`. Koşullu için `p / mx[x]`. Bağımsızlıkta **bütün** `(x, y)` birleşimlerini gez; sözlükte olmayanı `0` say.
```
:::

::: gorev 3 · Ardışık Bayes güncellemesi
`ardisik_guncelle(onsel, kanitlar)` işlevini yaz. Birden çok hipotez ve art arda gelen kanıtlar var; her kanıttan sonra inanç yeniden dağıtılır.

- `onsel`: boş olmayan `dict`; `{hipotez: olasılık}`; değerler negatif olmayan sayılar ve toplamları 1 (`1e-9` toleransla). `NaN` ve sonsuz değerler olasılık değildir, reddedilir.
- `kanitlar`: liste (boş olabilir); her öğe `{hipotez: P(kanıt | hipotez)}` biçiminde, `onsel` ile **aynı anahtarlara** sahip bir `dict`; değerler `[0, 1]` aralığında.
- Her kanıt için: her hipotezin olasılığını olabilirliğiyle çarp, sonra toplam 1 olacak biçimde normalleştir. Toplam sıfırsa (kanıt bütün hipotezlerle çelişiyor) `ValueError`.
- Dönüş: her adımdan sonraki dağılımların listesi; ilk öğe `onsel`'in kendisidir (yani `len(kanitlar) + 1` öğe). Olasılıklar 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç çarpıyor ama normalleştirmiyor: sayılar olasılık olmaktan çıkar ve her adımda küçülür.

```starter
def ardisik_guncelle(onsel, kanitlar):
    out = [dict(onsel)]
    for k in kanitlar:
        out.append({h: out[-1][h] * k[h] for h in onsel})
    return out
```

```solution
def ardisik_guncelle(onsel, kanitlar):
    def sayi(x):
        return not isinstance(x, bool) and isinstance(x, (int, float))
    if not isinstance(onsel, dict) or not onsel or any(not sayi(p) or not 0 <= p <= 1 for p in onsel.values()):
        raise ValueError('onsel boş olmayan olasılık sözlüğü olmalı')
    if abs(sum(onsel.values()) - 1) > 1e-9:
        raise ValueError('önsel 1 e toplanmalı')
    if not isinstance(kanitlar, list):
        raise ValueError('kanitlar liste olmalı')
    simdi = {h: float(p) for h, p in onsel.items()}
    out = [{h: round(p, 9) for h, p in simdi.items()}]
    for k in kanitlar:
        if not isinstance(k, dict) or set(k) != set(onsel) or any(not sayi(p) or not 0 <= p <= 1 for p in k.values()):
            raise ValueError('kanıt önselle aynı anahtarlara ve [0, 1] değerlere sahip olmalı')
        carpim = {h: simdi[h] * k[h] for h in simdi}
        toplam = sum(carpim.values())
        if toplam == 0:
            raise ValueError('kanıt bütün hipotezlerle çelişiyor')
        simdi = {h: p / toplam for h, p in carpim.items()}
        out.append({h: round(p, 9) for h, p in simdi.items()})
    return out
```

```test
need('ardisik_guncelle')
import random
from fractions import Fraction

r = ardisik_guncelle({'adil': 0.5, 'hileli': 0.5}, [{'adil': 0.5, 'hileli': 0.9}])
eq(r[0], {'adil': 0.5, 'hileli': 0.5}, 'ilk öğe önsel')
yakin(r[1]['hileli'], 0.9 / 1.4, 'bir tura sonrası', tol=1e-8)
r = ardisik_guncelle({'adil': 0.5, 'hileli': 0.5}, [{'adil': 0.5, 'hileli': 0.9}] * 5)
eq(len(r), 6, 'kanıt sayısı + 1 dağılım')
yakin(r[5]['hileli'], 0.9 ** 5 / (0.9 ** 5 + 0.5 ** 5), 'beş tura sonrası', tol=1e-8)
ok(all(r[i + 1]['hileli'] > r[i]['hileli'] for i in range(5)), 'her tura hileli hipotezini güçlendirir')
eq(ardisik_guncelle({'a': 0.3, 'b': 0.7}, []), [{'a': 0.3, 'b': 0.7}], 'kanıt yoksa yalnız önsel')
r = ardisik_guncelle({'a': 0.2, 'b': 0.8}, [{'a': 1, 'b': 0}])
eq(r[1], {'a': 1.0, 'b': 0.0}, 'b ile çelişen kanıt b yi sıfırlar')
r = ardisik_guncelle({'a': 0.2, 'b': 0.8}, [{'a': 0.4, 'b': 0.4}])
eq(r[1], {'a': 0.2, 'b': 0.8}, 'bütün hipotezlerde eşit olabilirlik inancı değiştirmez')
rng = random.Random(503)
for _ in range(25):
    hs = [f"h{i}" for i in range(rng.randint(1, 4))]
    w = [rng.randint(1, 9) for _ in hs]
    onsel = {h: Fraction(x, sum(w)) for h, x in zip(hs, w)}
    kan = [{h: Fraction(rng.randint(1, 10), 10) for h in hs} for _ in range(rng.randint(0, 5))]
    ref = dict(onsel)
    for k in kan:
        c = {h: ref[h] * k[h] for h in hs}
        ref = {h: c[h] / sum(c.values()) for h in hs}
    got = ardisik_guncelle({h: float(p) for h, p in onsel.items()}, [{h: float(p) for h, p in k.items()} for k in kan])
    for h in hs:
        yakin(got[-1][h], float(ref[h]), 'rastgele kanıtlarda kesirli referansla aynı', tol=1e-7)
    for d in got:
        yakin(sum(d.values()), 1.0, 'her adımda toplam 1', tol=1e-7)
a = ardisik_guncelle({'a': 0.5, 'b': 0.5}, [{'a': 0.2, 'b': 0.6}, {'a': 0.9, 'b': 0.3}])[-1]
b = ardisik_guncelle({'a': 0.5, 'b': 0.5}, [{'a': 0.9, 'b': 0.3}, {'a': 0.2, 'b': 0.6}])[-1]
yakin(a['a'], b['a'], 'bağımsız kanıtların sırası sonucu değiştirmez', tol=1e-8)
o, k = {'a': 0.5, 'b': 0.5}, [{'a': 0.2, 'b': 0.6}]
ardisik_guncelle(o, k)
eq((o, k), ({'a': 0.5, 'b': 0.5}, [{'a': 0.2, 'b': 0.6}]), 'girdiler değişmez')
raises(ValueError, ardisik_guncelle, {'a': 0.5, 'b': 0.5}, [{'a': 0, 'b': 0}], msg='bütün hipotezlerle çelişen kanıt')
iyi = {'a': 0.5, 'b': 0.5}
for o, k in [(None, []), ([('a', 1.0)], []), ({}, []), ({'a': 0.5}, []), ({'a': 0.6, 'b': 0.6}, []), ({'a': -0.5, 'b': 1.5}, []), ({'a': True}, []), ({'a': '0.5', 'b': 0.5}, []), ({'a': float('nan')}, []), ({'a': float('nan'), 'b': 1.0}, []), (iyi, [{'a': float('nan'), 'b': 0.5}]), (iyi, [{'a': True, 'b': 0.5}]), (iyi, [['a', 'b']]), (iyi, None), (iyi, [{'a': 0.5}]), (iyi, [{'a': 0.5, 'b': 0.5, 'c': 0.5}]), (iyi, [{'a': 1.5, 'b': 0.5}]), (iyi, [[0.5, 0.5]]), (iyi, ({'a': 0.5, 'b': 0.5},))]:
    raises(ValueError, ardisik_guncelle, o, k, msg='bozuk girdi reddedilir')
```

```hint
Her adımda iki iş: çarp (`simdi[h] * kanit[h]`) ve toplamına böl. Bir adımın sonsalı, bir sonrakinin önselidir.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur; her adım bu derste hesapladığın bir sayıya ya da örneğe dayanır.

1. **Soru (15 sn).** "Test pozitif çıktı. Gerçekten hasta olma olasılığınız ne?"
2. **Sayılar (30 sn).** Hastalık yüzde 1, test hastaların yüzde 99'unu yakalıyor, sağlıklıların yüzde 5'ine yanlışlıkla pozitif diyor. Salona tahmin ettir.
3. **Cevap (30 sn).** "On bin kişi: yüz hasta, 99'u pozitif. Ama 9.900 sağlıklının 495'i de pozitif. 594 pozitifin yalnız 99'u hasta: yüzde 17."
4. **Güvenlik (25 sn).** "Günde bir milyon olaydan onu gerçekten saldırıysa, çok iyi bir alarm sistemi bile binlerce yanlış alarm üretir. Asıl soru: alarm çaldığında haklı olma olasılığı."
5. **Kapanış (20 sn).** "Nadir bir şeyi arıyorsanız, testin doğruluğundan önce taban oranını sorun."
:::

::: anlat Sınır
Bu ders ayrık olasılığı, koşullu olasılığı ve Bayes kuralını anlatır. Görevlerdeki dağılımlar küçük ve tam bilinen tablolardır; gerçek problemlerde ortak dağılım bilinmez, sınırlı sayıda örnekten tahmin edilir ve bu tahminin kendi belirsizliği vardır (bkz. `ai-matematik-06`). Bayes güncellemesi önselin ve olabilirliklerin doğru olduğunu varsayar; önsel yanlışsa sonsal da yanlıştır ve az kanıtla önselin etkisi büyüktür. Görev 3'teki ardışık güncelleme, kanıtların hipotez verildiğinde birbirinden bağımsız olduğunu varsayar; aynı kaynaktan gelen kanıtları ayrı ayrı saymak inancı olduğundan güçlü gösterir. Bağımsızlık denetimi kesin olasılıklar içindir; veriden tahmin edilen olasılıklarda örnekleme gürültüsü yüzünden bir istatistik testi gerekir (bkz. `ai-matematik-07`). Sürekli değişkenler ve olasılık yoğunlukları bu dersin kapsamı dışındadır.

Kaynaklar: [Goodfellow, Bengio ve Courville 2016 - Deep Learning, Bölüm 3: Probability and Information Theory](https://www.deeplearningbook.org/contents/prob.html), [Axelsson 2000 - The Base-Rate Fallacy and the Difficulty of Intrusion Detection](https://doi.org/10.1145/357830.357849), [Jaynes 2003 - Probability Theory: The Logic of Science](https://doi.org/10.1017/CBO9780511790423).
:::

::: dusun
Bir e-posta süzgeci istenmeyen postaların %98'ini yakalıyor ve normal postaların %1'ini yanlışlıkla işaretliyor. Gelen kutunun %20'si istenmeyen postaysa, işaretlenen bir postanın gerçekten istenmeyen olma olasılığı nedir? Aynı süzgeci, istenmeyen posta oranının binde bir olduğu bir kurumsal ağa koyarsan bu olasılık ne olur? Süzgeç değişmediği hâlde kullanıcı deneyimi neden değişir?
:::

::: ozet
- Marjinal olasılık toplayarak, koşullu olasılık bölerek bulunur: `P(A | B) = P(A, B) / P(B)`.
- Bayes kuralı kanıt geldiğinde önseli sonsala çevirir; `P(E | H)` ile `P(H | E)` aynı şey değildir.
- Nadir olaylarda taban oranı sonucu belirler: çok iyi bir test bile çoğunlukla yanlış alarm verebilir.
- Bağımsızlık, ortak olasılığın marjinallerin çarpımına eşit olmasıdır; her birleşim için denetlenir.
- Ardışık güncellemede bir adımın sonsalı sonrakinin önselidir; her adımda yeniden normalleştirilir.
:::
