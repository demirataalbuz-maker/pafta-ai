---
id: ai-guvence-48
title: "Ablation Tasarımı · Etkiyi Hangi Bileşen Taşıyor?"
summary: Bir sistemin bileşenlerini tek tek çıkararak katkılarını ölç, iki bileşenin etkileşimini 2x2 tasarımla ayır ve iki varyant arasındaki farkın tohum gürültüsünden büyük olup olmadığını denetle.
esleme: ai-guvence-26, ai-guvence-27, ai-matematik-06, ai-matematik-07
timeout: 30
---

::: anlat 1. "Çalışıyor" yetmez; neden çalışıyor?
Bir makale yeni bir yöntem öneriyor: beş farklı bileşen eklenmiş ve sonuç 6 puan iyileşmiş. Hangi bileşen işe yaradı? Beşi de mi, yoksa biri mi? Diğer dördü yalnız karmaşıklık mı ekliyor?

`Ablation study` bu soruyu cevaplar: bileşenleri sistemli olarak çıkarır ve sonucun nasıl değiştiğine bakarsın. İyi bir ablation olmadan bir sonuç **yeniden üretilemez** ve üstüne bir şey kurulamaz, çünkü neyin önemli olduğu bilinmez. Bir savunmayı ya da bir değerlendirme yöntemini incelerken de aynı soru geçerlidir: koruma gerçekten iddia edilen bileşenden mi geliyor?

Bu derste örnek sistem bir soru-cevap hattıdır ve üç bileşeni vardır: sorguyu yeniden yazma, `reranker` ve alıntı denetimi. Ölçü, bir test kümesindeki doğruluktur.

| Soru | Araç | Görev |
|---|---|---|
| Her bileşenin katkısı ne? | Birer birer çıkarma (`leave-one-out`) | 1 |
| İki bileşen birlikte mi çalışıyor? | 2×2 `factorial` tasarım ve etkileşim | 2 |
| Fark gerçek mi, tohum gürültüsü mü? | Tohumlar üzerinden standart hata | 3 |

> [!NOT]
> Bu dersteki skorlar sentetiktir; gerçek bir sistem ölçülmez. Görevler bir ablation tablosunun nasıl kurulacağını ve okunacağını öğretir.
:::

::: anlat 2. Üç tasarım ve tuzakları
**Birer birer çıkarma.** Tam sistemin skorunu ölç; sonra her bileşeni tek başına çıkarıp yeniden ölç. Bileşenin katkısı aradaki farktır:

$$\text{katkı}_i = \text{skor}(\text{tam}) - \text{skor}(\text{tam} \setminus i)$$

Bu tasarım ucuzdur (`n + 1` koşu) ama bir kör noktası vardır: bileşenler birbirinin yerini tutabiliyorsa her birini tek tek çıkarmak hiçbir şey değiştirmez ve ikisi de "etkisiz" görünür; oysa ikisini birden çıkarınca sistem çöker. Tersi de olur: iki bileşen ancak birlikte çalışıyorsa her birinin katkısı toplam etkinin tamamı gibi görünür ve katkıların toplamı toplam etkiyi **aşar**.

**2×2 tasarım.** İki bileşen için dört koşulun hepsini ölçersin: ikisi de yok, yalnız A, yalnız B, ikisi de var. Buradan üç sayı çıkar:

- **A'nın ana etkisi:** A'yı eklemenin ortalama kazancı (B yokken ve B varken).
- **B'nin ana etkisi:** aynı şey B için.
- **Etkileşim:** A'nın kazancı B varken ve yokken ne kadar farklı? $(s_{11} - s_{01}) - (s_{10} - s_{00})$.

Etkileşim sıfırsa bileşenler bağımsızdır ve katkıları toplanır. Pozitifse birbirini güçlendirir (`synergy`); negatifse birbirinin yerini tutar (`redundancy`).

**Gürültü.** Aynı yapılandırmayı farklı rastgele tohumlarla koşarsan skor oynar. Tek koşuya dayalı 0,8 puanlık bir "katkı", tohum gürültüsü 1,5 puansa hiçbir şey söylemez. Her varyantı birkaç tohumla koşup ortalamayı ve standart hatayı verirsin (bkz. `ai-matematik-06`). İki varyantın farkının standart hatası:

$$\mathrm{SE} = \sqrt{\frac{s_a^2}{n_a} + \frac{s_b^2}{n_b}}$$

Fark, bu standart hatanın iki katından büyük değilse "fark var" denmez.

**Diğer tuzaklar.** Bir bileşeni çıkarınca hiperparametreler artık en iyi değerlerinde değildir; adil karşılaştırma için her varyant ayrıca ayarlanmalıdır. Bileşeni "çıkarmak" ile onu etkisiz bir sürümle (rastgele ya da sabit çıktılı) **değiştirmek** farklı şeylerdir: ikincisi hesap bütçesini ve parametre sayısını sabit tutar. Hangi karşılaştırmaların yapılacağı deneyden **önce** yazılmalıdır; sonuçlara bakıp anlamlı çıkanı seçmek çoklu karşılaştırma hatasıdır (bkz. `ai-matematik-07`).
:::

::: tahmin Tek tek çıkarınca görünmeyen etki
İki bileşen birbirinin yedeği: biri varsa sistem çalışıyor. Birer birer çıkarma ne gösterir?

```python
def skor(a, b):
    return 0.90 if (a or b) else 0.50

tam = skor(True, True)
print("A katkısı:", round(tam - skor(False, True), 2))
print("B katkısı:", round(tam - skor(True, False), 2))
print("ikisi birden:", round(tam - skor(False, False), 2))
```

???

```cikti
A katkısı: 0.0
B katkısı: 0.0
ikisi birden: 0.4
```
Birer birer çıkarma iki bileşeni de "etkisiz" gösteriyor: biri gidince öbürü işi devralıyor. İkisini birden çıkarınca skor 40 puan düşüyor. Yalnız birer birer tabloya bakan biri iki bileşeni de silerdi ve sistemi bozardı. Bu, negatif etkileşimin (`redundancy`) uç örneğidir ve ancak dört koşulun hepsini ölçünce görünür.
:::

::: gorev 1 · Birer birer çıkarma tablosu
`ablation_tablosu(tam_skor, cikarilmis, gurultu)` işlevini yaz.

- `tam_skor`: bütün bileşenler varken skor; sayı. `cikarilmis`: boş olmayan `{bileşen adı: o bileşen çıkarılınca skor}` sözlüğü; adlar boş olmayan `str`. `gurultu`: negatif olmayan sayı (ölçümün oynaklığı).
- Her bileşen için `katki = tam_skor - cikarilmis[ad]`.
- `karar`: `katki > gurultu` ise `'katkili'`; `katki < -gurultu` ise `'zararli'` (çıkarınca skor artıyor); değilse `'belirsiz'`.
- Dönüş: satır sözlüklerinin listesi `{'bilesen': ..., 'katki': ..., 'karar': ...}`; katkıya göre azalan, eşitlikte ada göre alfabetik sıralı; katkı 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç gürültüyü yok sayıyor ve her pozitif farkı katkı sayıyor: 0,1 puanlık bir oynama "katkılı bileşen" olarak raporlanıyor, skoru düşüren bileşen ise hiç işaretlenmiyor.

```starter
def ablation_tablosu(tam_skor, cikarilmis, gurultu):
    satirlar = [{'bilesen': ad, 'katki': round(tam_skor - s, 9), 'karar': 'katkili' if tam_skor - s > 0 else 'belirsiz'} for ad, s in cikarilmis.items()]
    return sorted(satirlar, key=lambda r: -r['katki'])
```

```solution
def ablation_tablosu(tam_skor, cikarilmis, gurultu):
    import math
    def sayi(x):
        return not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x)
    if not sayi(tam_skor) or not sayi(gurultu) or gurultu < 0:
        raise ValueError('tam_skor sayı, gurultu negatif olmayan sayı olmalı')
    if not isinstance(cikarilmis, dict) or not cikarilmis or any(not isinstance(a, str) or not a or not sayi(s) for a, s in cikarilmis.items()):
        raise ValueError('cikarilmis {ad: skor} sözlüğü olmalı')
    satirlar = []
    for ad, s in cikarilmis.items():
        katki = round(tam_skor - s, 9) + 0.0
        karar = 'katkili' if katki > gurultu else ('zararli' if katki < -gurultu else 'belirsiz')
        satirlar.append({'bilesen': ad, 'katki': katki, 'karar': karar})
    return sorted(satirlar, key=lambda r: (-r['katki'], r['bilesen']))
```

```test
need('ablation_tablosu')
import random

r = ablation_tablosu(0.80, {'yeniden_yazma': 0.79, 'reranker': 0.68, 'alinti_denetimi': 0.83}, 0.02)
eq([x['bilesen'] for x in r], ['reranker', 'yeniden_yazma', 'alinti_denetimi'], 'katkıya göre azalan sıra')
eq(r[0], {'bilesen': 'reranker', 'katki': 0.12, 'karar': 'katkili'}, 'gürültünün üstünde katkı')
eq(r[1], {'bilesen': 'yeniden_yazma', 'katki': 0.01, 'karar': 'belirsiz'}, 'gürültünün içinde kalan fark: belirsiz')
eq(r[2], {'bilesen': 'alinti_denetimi', 'katki': -0.03, 'karar': 'zararli'}, 'çıkarınca skor artıyor: zararlı')
r = ablation_tablosu(0.8, {'b': 0.7, 'a': 0.7}, 0.0)
eq([x['bilesen'] for x in r], ['a', 'b'], 'eşit katkıda alfabetik')
eq(ablation_tablosu(0.8, {'a': 0.8}, 0.0)[0]['karar'], 'belirsiz', 'sıfır fark, sıfır gürültü: belirsiz')
eq(ablation_tablosu(0.8, {'a': 0.78}, 0.02)[0]['karar'], 'belirsiz', 'tam gürültü kadar fark katkı sayılmaz')
rng = random.Random(4801)
for _ in range(25):
    tam = round(rng.uniform(0.3, 0.9), 3)
    c = {f"k{i}": round(tam + rng.uniform(-0.2, 0.2), 3) for i in range(rng.randint(1, 6))}
    g = rng.choice([0, 0.01, 0.05])
    r = ablation_tablosu(tam, c, g)
    eq(len(r), len(c), 'her bileşen için bir satır')
    for x in r:
        k = round(tam - c[x['bilesen']], 9)
        yakin(x['katki'], k, 'rastgele tabloda katkı', tol=1e-9)
        eq(x['karar'], 'katkili' if k > g else ('zararli' if k < -g else 'belirsiz'), 'rastgele tabloda karar')
    ok(all((r[i]['katki'], ) >= (r[i + 1]['katki'], ) for i in range(len(r) - 1)), 'katkıya göre azalan')
c = {'a': 0.5}
ablation_tablosu(0.8, c, 0.01)
eq(c, {'a': 0.5}, 'girdi değişmez')
for a in ([None, {'a': 0.5}, 0.01], [0.8, None, 0.01], [0.8, ['a'], 0.01], [0.8, {}, 0.01], [0.8, {'': 0.5}, 0.01], [0.8, {1: 0.5}, 0.01], [0.8, {'a': '0.5'}, 0.01], [0.8, {'a': True}, 0.01], [0.8, {'a': float('nan')}, 0.01], [0.8, {'a': float('inf')}, 0.01], [0.8, {'a': 0.5}, -0.01], [0.8, {'a': 0.5}, None], [0.8, {'a': 0.5}, True], [0.8, {'a': 0.5}, float('nan')], [0.8, {'a': 0.5}, float('inf')], [True, {'a': 0.5}, 0.01], [float('nan'), {'a': 0.5}, 0.01], [float('inf'), {'a': 0.5}, 0.01]):
    raises(ValueError, ablation_tablosu, *a, msg='bozuk girdi reddedilir')
```

```hint
Her bileşen için katkıyı hesapla; üç dallı bir karşılaştırmayla kararı ver; `(-katki, ad)` anahtarıyla sırala.
```
:::

::: gorev 2 · 2×2 tasarım: ana etkiler ve etkileşim
`iki_etken(s00, s10, s01, s11)` işlevini yaz. Dört argüman, iki bileşenin dört koşulundaki skorlardır: `s10` yalnız A varken, `s01` yalnız B varken.

- Hepsi sayı.
- `a_etkisi`: A'nın ana etkisi, `((s10 - s00) + (s11 - s01)) / 2`.
- `b_etkisi`: B'nin ana etkisi, `((s01 - s00) + (s11 - s10)) / 2`.
- `etkilesim`: `(s11 - s01) - (s10 - s00)`.
- `toplam_etki`: `s11 - s00`.
- `tur`: etkileşim `1e-9`'dan büyükse `'guclendirme'`, `-1e-9`'dan küçükse `'yedeklik'`, değilse `'bagimsiz'`.
- Dönüş: bu beş anahtar; sayılar 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç etkileri yalnız öbür bileşen **varken** ölçüyor (birer birer çıkarmanın yaptığı şey) ve etkileşimi hep sıfır sayıyor.

```starter
def iki_etken(s00, s10, s01, s11):
    return {'a_etkisi': round(s11 - s01, 9), 'b_etkisi': round(s11 - s10, 9), 'etkilesim': 0.0, 'toplam_etki': round(s11 - s00, 9), 'tur': 'bagimsiz'}
```

```solution
def iki_etken(s00, s10, s01, s11):
    import math
    for x in (s00, s10, s01, s11):
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
            raise ValueError('skorlar sayı olmalı')
    a = ((s10 - s00) + (s11 - s01)) / 2
    b = ((s01 - s00) + (s11 - s10)) / 2
    e = (s11 - s01) - (s10 - s00)
    tur = 'guclendirme' if e > 1e-9 else ('yedeklik' if e < -1e-9 else 'bagimsiz')
    return {'a_etkisi': round(a, 9) + 0.0, 'b_etkisi': round(b, 9) + 0.0, 'etkilesim': round(e, 9) + 0.0, 'toplam_etki': round(s11 - s00, 9) + 0.0, 'tur': tur}
```

```test
need('iki_etken')
import random

eq(iki_etken(0.5, 0.6, 0.7, 0.8), {'a_etkisi': 0.1, 'b_etkisi': 0.2, 'etkilesim': 0.0, 'toplam_etki': 0.3, 'tur': 'bagimsiz'}, 'bağımsız bileşenler: etkiler toplanır')
r = iki_etken(0.5, 0.9, 0.9, 0.9)
eq((r['a_etkisi'], r['b_etkisi'], r['etkilesim'], r['tur']), (0.2, 0.2, -0.4, 'yedeklik'), 'biri yetiyor: negatif etkileşim')
r = iki_etken(0.5, 0.5, 0.5, 0.9)
eq((r['a_etkisi'], r['b_etkisi'], r['etkilesim'], r['tur']), (0.2, 0.2, 0.4, 'guclendirme'), 'ancak birlikte çalışıyor: pozitif etkileşim')
eq(iki_etken(0.7, 0.7, 0.7, 0.7)['tur'], 'bagimsiz', 'hiç etki yok')
r = iki_etken(0.5, 0.4, 0.8, 0.7)
eq((r['a_etkisi'], r['tur']), (-0.1, 'bagimsiz'), 'zararlı ama bağımsız bileşen')
rng = random.Random(4802)
for _ in range(30):
    s = [round(rng.uniform(0, 1), 3) for _ in range(4)]
    r = iki_etken(*s)
    yakin(r['a_etkisi'] + r['b_etkisi'], r['toplam_etki'], 'ana etkilerin toplamı her zaman toplam etkiye eşit', tol=1e-8)
    yakin(s[0] + r['a_etkisi'] + r['b_etkisi'] + 0 * r['etkilesim'], s[3], 's11 = s00 + A + B', tol=1e-8)
    yakin(r['etkilesim'], s[3] - s[2] - s[1] + s[0], 'etkileşim: fark farkı', tol=1e-8)
    yakin((s[3] - s[2]) + (s[3] - s[1]), r['toplam_etki'] + r['etkilesim'], 'birer birer çıkarma katkılarının toplamı = toplam etki + etkileşim', tol=1e-8)
    ters = iki_etken(s[0], s[2], s[1], s[3])
    yakin(ters['a_etkisi'], r['b_etkisi'], 'A ve B nin yerini değiştirmek etkileri değiştirir', tol=1e-9)
    yakin(ters['etkilesim'], r['etkilesim'], 'etkileşim simetriktir', tol=1e-9)
eq(iki_etken(0.0, 1 / 3, 0.0, 0.0)['a_etkisi'], 0.166666667, '9 basamağa yuvarlanır')
for a in ([None, 1, 1, 1], [1, "1", 1, 1], [1, 1, True, 1], [1, 1, 1, [1]], [float('nan'), 1, 1, 1], [1, float('inf'), 1, 1], [1, 1, float('-inf'), 1], [1, 1, 1, float('nan')]):
    raises(ValueError, iki_etken, *a, msg='bozuk girdi reddedilir')
```

```hint
A'nın kazancını iki kez ölç: B yokken (`s10 − s00`) ve B varken (`s11 − s01`). Ana etki ikisinin ortalaması, etkileşim ikisinin farkıdır.
```
:::

::: gorev 3 · Fark tohum gürültüsünden büyük mü?
`fark_ozeti(a_skorlari, b_skorlari)` işlevini yaz. İki varyantın farklı tohumlarla alınmış skorlarını karşılaştırır.

- `a_skorlari`, `b_skorlari`: her biri en az **iki** sayıdan oluşan liste (uzunlukları farklı olabilir).
- `fark`: `ortalama(a) - ortalama(b)`.
- `standart_hata`: `√(s_a² / n_a + s_b² / n_b)`; `s²` örneklem varyansıdır (`n - 1` payda).
- `z`: `fark / standart_hata`; standart hata sıfırsa `fark` da sıfırken `0.0`, değilken `math.inf` (işareti farkın işaretiyle aynı).
- `guvenilir`: `|z| >= 2`.
- Dönüş: bu dört anahtar; sonlu sayılar 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç her varyantın **en iyi** tohumunu karşılaştırıyor: daha çok tohumla koşulan varyant, yalnız şansla, daha iyi görünüyor.

```starter
def fark_ozeti(a_skorlari, b_skorlari):
    fark = max(a_skorlari) - max(b_skorlari)
    return {'fark': round(fark, 9), 'standart_hata': 0.0, 'z': float('inf') if fark else 0.0, 'guvenilir': fark != 0}
```

```solution
def fark_ozeti(a_skorlari, b_skorlari):
    import math
    for v in (a_skorlari, b_skorlari):
        if not isinstance(v, list) or len(v) < 2 or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in v):
            raise ValueError('her varyant için en az iki sayı gerekli')

    def ozet(v):
        m = sum(v) / len(v)
        return m, sum((x - m) ** 2 for x in v) / (len(v) - 1)

    ma, va = ozet(a_skorlari)
    mb, vb = ozet(b_skorlari)
    fark = ma - mb
    se = math.sqrt(va / len(a_skorlari) + vb / len(b_skorlari))
    if se == 0:
        z = 0.0 if fark == 0 else math.copysign(math.inf, fark)
    else:
        z = fark / se
    return {
        'fark': round(fark, 9) + 0.0,
        'standart_hata': round(se, 9),
        'z': z if math.isinf(z) else round(z, 9) + 0.0,
        'guvenilir': abs(z) >= 2,
    }
```

```test
need('fark_ozeti')
import math, random, statistics

r = fark_ozeti([0.80, 0.82, 0.78], [0.79, 0.81, 0.77])
yakin(r['fark'], 0.01, '1 puanlık fark', tol=1e-9)
eq(r['guvenilir'], False, 'tohum oynaklığı 2 puan: 1 puanlık fark güvenilir değil')
r = fark_ozeti([0.80, 0.81, 0.80, 0.81], [0.70, 0.71, 0.70, 0.71])
eq(r['guvenilir'], True, '10 puanlık fark, küçük oynaklık: güvenilir')
ok(r['z'] > 10, 'z büyük', got=r)
r = fark_ozeti([0.5, 0.5], [0.5, 0.5])
s = fark_ozeti([5, 7], [-1, 2, 5])
eq((s['z'], s['guvenilir']), (2.0, True), 'z tam 2 ise güvenilir sayılır (>=)')
eq(r, {'fark': 0.0, 'standart_hata': 0.0, 'z': 0.0, 'guvenilir': False}, 'oynaklık yok, fark yok')
r = fark_ozeti([0.6, 0.6], [0.5, 0.5])
eq((r['z'], r['guvenilir']), (math.inf, True), 'oynaklık yok, fark var: z sonsuz')
eq(fark_ozeti([0.5, 0.5], [0.6, 0.6])['z'], -math.inf, 'fark negatifse z eksi sonsuz')
az = fark_ozeti([0.5, 0.9], [0.6, 0.6, 0.6])
ok(not az['guvenilir'], 'tek bir şanslı tohum (0.9) farkı güvenilir yapmaz', got=az)
rng = random.Random(4803)
for _ in range(25):
    a = [round(rng.gauss(0.7, 0.03), 4) for _ in range(rng.randint(2, 10))]
    b = [round(rng.gauss(0.68, 0.03), 4) for _ in range(rng.randint(2, 10))]
    r = fark_ozeti(a, b)
    f = statistics.fmean(a) - statistics.fmean(b)
    se = math.sqrt(statistics.variance(a) / len(a) + statistics.variance(b) / len(b))
    yakin(r['fark'], f, 'rastgele tohumlarda fark', tol=1e-8)
    yakin(r['standart_hata'], se, 'rastgele tohumlarda standart hata', tol=1e-8)
    if se > 0:
        yakin(r['z'], f / se, 'rastgele tohumlarda z', tol=1e-6)
        eq(r['guvenilir'], abs(f / se) >= 2, 'rastgele tohumlarda karar')
    ters = fark_ozeti(b, a)
    yakin(ters['fark'], -r['fark'], 'varyantların yerini değiştirmek farkın işaretini çevirir', tol=1e-9)
    eq(ters['guvenilir'], r['guvenilir'], 'karar simetriktir')
a, b = [0.5, 0.6], [0.4, 0.5]
fark_ozeti(a, b)
eq((a, b), ([0.5, 0.6], [0.4, 0.5]), 'girdiler değişmez')
eq(fark_ozeti([0.9, 0.8], [0.6, 0.5])['z'], 4.242640687, 'sonlu z 9 basamağa yuvarlanır')
for x, y in [(None, [1.0, 2.0]), ([1.0, 2.0], None), ([1.0], [1.0, 2.0]), ([1.0, 2.0], [1.0]), ([], []), ([1, "2"], [1, 2]), ([True, False], [1, 2]), ((1.0, 2.0), [1.0, 2.0]), ([float('nan'), 1.0], [1.0, 2.0]), ([1.0, 2.0], [1.0, float('inf')])]:
    raises(ValueError, fark_ozeti, x, y, msg='bozuk ya da tek tohumlu girdi reddedilir')
```

```hint
Her varyant için ortalama ve `n − 1` paydalı varyans. `se = √(va/na + vb/nb)`. Sıfır standart hatayı ayrı ele al.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur; her adım bu derste hesapladığın bir sayıya ya da örneğe dayanır.

1. **Soru (15 sn).** "Bir yöntem beş parça eklemiş ve 6 puan kazanmış. Hangi parça işe yaradı?"
2. **Tuzak (30 sn).** Tahmin adımı: iki yedek bileşenin her biri tek tek çıkarılınca hiçbir şey değişmiyor; ikisi birden çıkınca 40 puan düşüyor.
3. **Çare (30 sn).** "İki bileşenin dört birleşimini de ölçeriz: birlikte mi çalışıyorlar, birbirinin yerini mi tutuyorlar?"
4. **Gürültü (25 sn).** "Tek koşuluk 0,8 puanlık fark, tohumdan tohuma 1,5 puan oynayan bir skorda hiçbir şey söylemez."
5. **Kapanış (20 sn).** "'Çalışıyor' yetmez; neden çalıştığını gösteremeyen sonuç üstüne bir şey kurulamaz."
:::

::: anlat Sınır
Bu ders ablation'ın üç temel tasarımını sentetik skorlarla anlatır. Birer birer çıkarma yalnız bir bileşenin **tam sistemdeki** marjinal katkısını ölçer; etkileşim varsa bu sayı bileşenin "değeri" değildir ve katkıların toplamı toplam etkiye eşit olmak zorunda değildir. Bütün alt kümeleri ölçmek `2ⁿ` koşu ister; çok bileşenli sistemlerde bu imkânsızdır ve `Shapley` değerleri gibi ortalamalar ya da kesirli tasarımlar kullanılır; bu derste işlenmez. Görev 2 iki bileşen ve tek ölçüm içindir; her hücrenin kendi gürültüsü vardır ve küçük bir etkileşimi güvenle söylemek, ana etkileri söylemekten daha çok tekrar ister. Görev 3'teki `|z| >= 2` kuralı kaba bir eşiktir: az sayıda tohumda normal yaklaşım zayıftır (`t` dağılımı gerekir) ve aynı tohumlar iki varyantta da kullanıldıysa eşli bir karşılaştırma daha güçlüdür (bkz. `ai-matematik-07`). Tohum gürültüsü tek belirsizlik kaynağı değildir: test kümesinin örneklemesi, hiperparametre ayarı ve veri sırası da oynaklık ekler. Bir bileşeni çıkarıp sistemi yeniden ayarlamadan ölçmek, bileşenin katkısını olduğundan büyük gösterebilir. Ablation "bu bileşen olmadan skor düşüyor" der; **neden** düştüğünü söylemez.

Kaynaklar: [Lipton ve Steinhardt 2018 - Troubling Trends in Machine Learning Scholarship](https://arxiv.org/abs/1807.03341), [Melis, Dyer ve Blunsom 2018 - On the State of the Art of Evaluation in Neural Language Models](https://arxiv.org/abs/1707.05589), [Bouthillier vd. 2021 - Accounting for Variance in Machine Learning Benchmarks](https://arxiv.org/abs/2103.03098), [Meyes vd. 2019 - Ablation Studies in Artificial Neural Networks](https://arxiv.org/abs/1901.08644).
:::

::: dusun
Bir makalenin ablation tablosunda beş bileşen var; her biri tek tek çıkarıldığında skor 0,3 ile 0,6 puan arasında düşüyor ve yazarlar "her bileşen katkı sağlıyor" diyor. Tabloda tohum sayısı ve standart sapma yok. Bu sonuca güvenmek için yazarlardan hangi iki sayıyı istersin? Bileşenlerin beşi birden çıkarıldığında toplam düşüş 0,5 puansa bu tablo hakkında ne düşünürsün?
:::

::: ozet
- Ablation, bir sonucun hangi bileşenden geldiğini bileşenleri sistemli çıkararak ölçer.
- Birer birer çıkarma ucuzdur ama yedekli bileşenleri "etkisiz", birbirine bağımlı bileşenleri "her şey" gösterir.
- 2×2 tasarım ana etkileri ve etkileşimi ayırır: sıfır bağımsızlık, pozitif güçlendirme, negatif yedekliktir.
- Tek koşuluk fark kanıt değildir; her varyant birkaç tohumla koşulur ve fark standart hatasıyla birlikte verilir.
- Karşılaştırmalar deneyden önce belirlenir; en iyi tohumu ya da anlamlı çıkan karşılaştırmayı sonradan seçmek sonucu geçersiz kılar.
:::
