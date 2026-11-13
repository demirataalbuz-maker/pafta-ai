---
id: ai-temel-41
title: "AI Nasıl Daha İyi Yapılır? · Compute, Veri, Algoritma ve İlerlemenin Ayrıştırılması"
summary: Bir modelin iyileşmesini donanım, harcama ve algoritma verimliliğine ayır; örnek verimliliğini ve azalan getiriyi ölç; "sadece daha büyük yapıyorlar" iddiasını sayılarla sına ve iki dakikada anlat.
---

::: anlat 1. Soru: "Daha iyi AI nasıl yapılıyor? Sadece büyütüyorlar mı?"
Salondan gelen sorunun iki yaygın cevabı vardır: "Daha çok GPU alıyorlar" ve "Yeni bir mimari buldular". İkisi de eksiktir. Bir modelin iyileşmesi üç kaynaktan gelir ve bunlar **çarpılır**:

| Kaynak | Ne demek | Örnek |
|---|---|---|
| `Compute` | Eğitimde harcanan toplam hesap: donanımın verimi × harcanan para | Daha iyi GPU, daha büyük küme, daha uzun eğitim |
| Veri | Miktar, kalite, çeşitlilik ve nasıl hazırlandığı | Tekilleştirme, filtreleme, sentetik veri, insan geri bildirimi |
| Algoritma | Aynı compute ve veriyle daha iyi sonuç | Mimari, optimizer, eğitim reçetesi, `distillation` |

`ai-temel-31` dersi kaybın compute ile nasıl düştüğünü (`scaling laws`) işledi. Bu ders farklı bir soru sorar: **gözlenen bir iyileşmenin ne kadarı hangi kaynaktan geldi** ve bunu nasıl okursun?

| Ölçü | Soru | Görev |
|---|---|---|
| Ayrıştırma | Toplam büyümede her kaynağın payı ne? | 1 |
| Örnek verimliliği | Aynı sonuca kaç kat az veriyle ulaşılıyor? | 2 |
| Azalan getiri | Skor yavaşlıyor mu, yoksa ölçek mi yanıltıyor? | 3 |

> [!NOT]
> Görevlerdeki sayılar öğretim amaçlı seçilmiştir; gerçek bir laboratuvarın bütçesi ya da ölçümü değildir. Yayımlanmış ölçümler anlatımda kaynaklarıyla verilir.
:::

::: anlat 2. Üç kaynak ve "bitter lesson"
**Compute.** Bir eğitimin toplam hesabı kabaca `donanım verimi × harcama` çarpımıdır. Donanım her yıl aynı paraya daha çok işlem verir; laboratuvarlar da her yıl daha çok harcar. İkisi çarpıldığı için büyüme, tek tek bakıldığında göründüğünden hızlıdır.

**Algoritma verimliliği.** Hernandez ve Brown (2020), ImageNet'te AlexNet düzeyine ulaşmak için gereken compute'un 2012 ile 2019 arasında yaklaşık 44 kat azaldığını ölçtü: yaklaşık her 16 ayda bir yarılanma. Bu, aynı dönemde donanımdaki iyileşmeden daha hızlıdır. Yani "yalnız daha çok GPU" açıklaması, ölçülen ilerlemenin önemli bir kısmını kaçırır.

**Veri.** Daha fazla veri her zaman daha iyi değildir. Yinelenen, düşük kaliteli ya da yanlış etiketli veri compute'u boşa harcar. Modern eğitim hatlarının büyük kısmı veriyi büyütmekten çok **seçmekle** uğraşır (bkz. `ai-uretim-06`).

**Bitter lesson (Sutton, 2019).** Rich Sutton'ın gözlemi şudur: 70 yıllık AI tarihinde, araştırmacıların insan bilgisini elle kodladığı yöntemler kısa vadede kazandı, ama uzun vadede hep **compute ile ölçeklenen genel yöntemler** (arama ve öğrenme) kazandı. Satrançta, Go'da, konuşma tanımada ve görüde böyle oldu.

Bu bir **görüştür** ve iki itirazı vardır:

- Ölçeklenen yöntemlerin kendisi algoritmik buluşlardır (`Transformer`, `attention`, `backpropagation`). "Yalnız compute" demek bunları yok sayar.
- Geçmişte geçerli olan bir eğilim gelecekte sürmek zorunda değildir: veri, enerji ve çip üretimi sınırlıdır.
:::

::: tahmin Üç çarpan birlikte
Bir yılda donanım aynı paraya 1.4 kat, harcama 2.5 kat, algoritma verimliliği 2 kat iyileşiyor. Toplam etkili compute kaç kat artar ve bu kaç ayda bir ikiye katlanma demektir?

```python
import math

donanim, harcama, algoritma = 1.4, 2.5, 2.0
toplam = donanim * harcama * algoritma
ay = 12 * math.log(2) / math.log(toplam)
print(f"toplam={toplam:.1f}x ikiye_katlanma={ay:.1f} ay")
```

???

```cikti
toplam=7.0x ikiye_katlanma=4.3 ay
```
Çarpanlar toplanmaz, çarpılır: `1.4 × 2.5 × 2.0 = 7`. Tek başına donanım (1.4 kat) yılda yüzde 40'lık bir iyileşmedir; üçü birlikte yedi kattır. İkiye katlanma süresi `12 · ln 2 / ln 7 ≈ 4.3` aydır. "Moore yasası yavaşladı, AI de yavaşlar" çıkarımının neden eksik olduğunu bu hesap gösterir: donanım üç çarpandan yalnız biridir.
:::

::: gorev 1 · İlerlemeyi kaynaklarına ayır
`ilerleme_ayristir(carpanlar)` işlevini yaz. Yıllık büyüme çarpanlarını alır, toplamı ve her kaynağın payını döndürür.

- `carpanlar`: boş olmayan `dict`; anahtarlar boş olmayan `str`, değerler pozitif sayı (yıllık çarpan; `1.0` değişim yok demektir).
- `toplam_carpan`: bütün çarpanların çarpımı. `1`'den büyük olmak zorundadır; değilse `ValueError` (payda sıfır ya da negatif olur).
- `paylar`: her kaynak için `ln(çarpan) / ln(toplam)`. Paylar toplamı 1'dir; 1'den küçük bir çarpanın payı negatiftir.
- `ikiye_katlanma_ay`: `12 · ln 2 / ln(toplam)`.
- Dönüş: `{'toplam_carpan': ..., 'paylar': {...}, 'ikiye_katlanma_ay': ...}`. Çarpan ve paylar 6, ay 4 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç çarpanları topluyor ve payı aritmetik oranla hesaplıyor. Çarpımsal bir büyümede bu hem toplamı hem payları yanlış verir.

```starter
def ilerleme_ayristir(carpanlar):
    toplam = sum(carpanlar.values())
    return {'toplam_carpan': round(toplam, 6), 'paylar': {k: round(v / toplam, 6) for k, v in carpanlar.items()}, 'ikiye_katlanma_ay': round(12 / toplam, 4)}
```

```solution
def ilerleme_ayristir(carpanlar):
    import math
    if not isinstance(carpanlar, dict) or not carpanlar:
        raise ValueError('carpanlar boş olmayan dict olmalı')
    for k, v in carpanlar.items():
        if not isinstance(k, str) or not k:
            raise ValueError('kaynak adı boş olmayan str olmalı')
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not v > 0 or v == float('inf'):
            raise ValueError('çarpan pozitif sonlu sayı olmalı')
    toplam = 1.0
    for v in carpanlar.values():
        toplam *= v
    if not toplam > 1:
        raise ValueError('toplam çarpan 1 den büyük olmalı')
    lt = math.log(toplam)
    return {
        'toplam_carpan': round(toplam, 6),
        'paylar': {k: round(math.log(v) / lt, 6) for k, v in carpanlar.items()},
        'ikiye_katlanma_ay': round(12 * math.log(2) / lt, 4),
    }
```

```test
need('ilerleme_ayristir')
import math, random

def _ref(c):
    t = math.prod(c.values())
    return {'toplam_carpan': round(t, 6), 'paylar': {k: round(math.log(c[k]) / math.log(t), 6) for k in c}, 'ikiye_katlanma_ay': round(12 * math.log(2) / math.log(t), 4)}

r = ilerleme_ayristir({'donanim': 2.0, 'harcama': 2.0, 'algoritma': 4.0})
eq(r, {'toplam_carpan': 16.0, 'paylar': {'donanim': 0.25, 'harcama': 0.25, 'algoritma': 0.5}, 'ikiye_katlanma_ay': 3.0}, 'çarpımsal toplam ve logaritmik paylar')
eq(ilerleme_ayristir({'tek': 2.0}), {'toplam_carpan': 2.0, 'paylar': {'tek': 1.0}, 'ikiye_katlanma_ay': 12.0}, 'tek kaynak: yılda ikiye katlanma')
r = ilerleme_ayristir({'donanim': 4.0, 'veri': 0.5})
eq(r, {'toplam_carpan': 2.0, 'paylar': {'donanim': 2.0, 'veri': -1.0}, 'ikiye_katlanma_ay': 12.0}, '1 den küçük çarpanın payı negatiftir')
eq(ilerleme_ayristir({'a': 3.0, 'b': 1.0})['paylar'], {'a': 1.0, 'b': 0.0}, 'değişmeyen kaynağın payı 0')
rng = random.Random(4101)
for _ in range(25):
    c = {f"k{i}": round(rng.uniform(1.05, 5.0), 3) for i in range(rng.randint(1, 5))}
    eq(ilerleme_ayristir(c), _ref(c), 'rastgele çarpanlarda bağımsız referansla aynı')
    yakin(sum(ilerleme_ayristir(c)['paylar'].values()), 1.0, 'paylar toplamı 1', tol=1e-5)
c = {'a': 2.0, 'b': 3.0}
ilerleme_ayristir(c)
eq(c, {'a': 2.0, 'b': 3.0}, 'girdi değişmez')
for kotu in (None, {}, [2.0], {'a': 0}, {'a': -2.0}, {'a': True}, {'a': '2'}, {'': 2.0}, {1: 2.0}, {'a': 1.0}, {'a': 0.5}, {'a': 2.0, 'b': 0.5}, {'a': float('inf')}, {'a': float('nan')}):
    raises(ValueError, ilerleme_ayristir, kotu, msg='bozuk girdi ya da büyümeyen toplam reddedilir')
```

```hint
Toplam çarpımı bul, logaritmasını al. Pay `ln(çarpan) / ln(toplam)`. Logaritma çarpımı toplama çevirdiği için paylar 1'e toplanır.
```
:::

::: gorev 2 · Örnek verimliliği: hedefe kaç örnekle ulaşılır?
İki eğitim yöntemini karşılaştırmanın adil yolu "aynı veride kim daha iyi?" değil, **"aynı skora kim daha az veriyle ulaşıyor?"** sorusudur. `hedefe_ulasma(egri, hedef)` işlevi bir öğrenme eğrisinden bunu okur.

- `egri`: boş olmayan liste; her öğe `(ornek_sayisi, skor)`. Örnek sayıları pozitif ve **kesin artan**, skorlar sayıdır.
- `hedef`: sayı.
- İlk noktanın skoru zaten `>= hedef` ise o noktanın örnek sayısını döndür.
- Değilse hedefi ilk aşan ardışık iki nokta arasında **log ölçekte** doğrusal ara değer bul: `log10(n) = log10(n0) + (hedef - s0) / (s1 - s0) · (log10(n1) - log10(n0))`.
- Hedefe hiç ulaşılmıyorsa `None` döndür.
- Dönüş: `float`, 2 basamağa yuvarlanmış; ya da `None`.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç hedefi geçen ilk **ölçülmüş** noktayı döndürüyor. Ölçüm noktaları seyrekse yöntemlerin gerçek farkını gizler: 10 bin ile 100 bin arasında bir yerde hedefe ulaşan iki yöntem aynı görünür.

```starter
def hedefe_ulasma(egri, hedef):
    for n, s in egri:
        if s >= hedef:
            return float(n)
    return None
```

```solution
def hedefe_ulasma(egri, hedef):
    import math
    def sayi(x):
        return not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x)
    if not isinstance(egri, list) or not egri or not sayi(hedef):
        raise ValueError('egri boş olmayan liste, hedef sayı olmalı')
    onceki = 0
    for nokta in egri:
        if not isinstance(nokta, (tuple, list)) or len(nokta) != 2 or not sayi(nokta[0]) or not sayi(nokta[1]):
            raise ValueError('nokta (ornek_sayisi, skor) olmalı')
        if not nokta[0] > onceki:
            raise ValueError('örnek sayıları pozitif ve kesin artan olmalı')
        onceki = nokta[0]
    if egri[0][1] >= hedef:
        return round(float(egri[0][0]), 2)
    for (n0, s0), (n1, s1) in zip(egri, egri[1:]):
        if s0 < hedef <= s1:
            oran = (hedef - s0) / (s1 - s0)
            return round(10 ** (math.log10(n0) + oran * (math.log10(n1) - math.log10(n0))), 2)
    return None
```

```test
need('hedefe_ulasma')
import math, random

def _ref(egri, hedef):
    if egri[0][1] >= hedef:
        return round(float(egri[0][0]), 2)
    for i in range(1, len(egri)):
        n0, s0 = egri[i - 1]
        n1, s1 = egri[i]
        if s0 < hedef and s1 >= hedef:
            t = (hedef - s0) / (s1 - s0)
            return round(math.exp(math.log(n0) * (1 - t) + math.log(n1) * t), 2)
    return None

egri = [(1000, 0.5), (10000, 0.7), (100000, 0.9)]
eq(hedefe_ulasma(egri, 0.8), 31622.78, 'log ölçekte ara değer: 10^4.5')
eq(hedefe_ulasma(egri, 0.7), 10000.0, 'tam ölçüm noktasında hedef')
eq(hedefe_ulasma(egri, 0.4), 1000.0, 'ilk nokta zaten hedefin üstünde')
eq(hedefe_ulasma(egri, 0.95), None, 'hedefe ulaşılmıyor')
eq(hedefe_ulasma([(100, 0.2), (1000, 0.2), (10000, 0.6)], 0.4), 3162.28, 'düz bölge atlanır, sonraki aralıkta ara değer')
eq(hedefe_ulasma([(50, 0.3)], 0.3), 50.0, 'tek noktalı eğri')
a = hedefe_ulasma([(1000, 0.5), (10000, 0.9)], 0.8)
b = hedefe_ulasma([(1000, 0.5), (10000, 0.81)], 0.8)
ok(a < b, 'aynı ölçüm noktalarında hızlı yöntem daha az örnekle ulaşır', got=(a, b))
rng = random.Random(4102)
for _ in range(30):
    n, s, e = 10, 0.1, []
    for _ in range(rng.randint(1, 7)):
        n = n * rng.choice([2, 3, 10]) + rng.randint(0, 5)
        s = round(s + rng.choice([0.0, 0.05, 0.1, 0.2]), 3)
        e.append((n, s))
    h = round(rng.uniform(0.05, 1.2), 3)
    got, exp = hedefe_ulasma(e, h), _ref(e, h)
    if exp is None:
        eq(got, None, 'rastgele eğride ulaşılmayan hedef')
    else:
        ok(isinstance(got, float) and abs(got - exp) <= 0.011 + 1e-9 * abs(exp), 'rastgele eğride bağımsız referansla aynı', got=(got, exp))
eq(hedefe_ulasma([(1, 0.2), (100, 0.6)], 0.4), 10.0, 'n0 = 1 sınırı')
iyi = [(10, 0.1), (20, 0.2)]
for e, h in [(None, 0.5), ([], 0.5), (["ab"], 0.5), ([123], 0.5), (iyi, None), (iyi, True), (iyi, float('nan')), (iyi, float('inf')), ([(10,)], 0.5), ([(10, 0.1), (10, 0.2)], 0.5), ([(20, 0.1), (10, 0.2)], 0.5), ([(0, 0.1)], 0.5), ([(-5, 0.1)], 0.5), ([(True, 0.1)], 0.5), ([(10, True)], 0.5), ([(float('nan'), 0.1)], 0.5), ([(10, float('inf'))], 0.5), ([("10", 0.1)], 0.5), ([(10, "0.1")], 0.5), (tuple(iyi), 0.5)]:
    raises(ValueError, hedefe_ulasma, e, h, msg='bozuk eğri reddedilir')
```

```hint
Ardışık nokta çiftlerini gez. `s0 < hedef <= s1` olan ilk aralıkta oranı bul ve `log10` değerleri arasında ara değer al; sonucu `10 **` ile geri çevir.
```
:::

::: gorev 3 · Azalan getiri mi, tavan etkisi mi?
Bir benchmark'ta doğruluk %90'dan %95'e, sonra %95'ten %97.5'e çıkıyor. Kazanç 5 puandan 2.5 puana düştü: ilerleme yavaşladı mı? Hata oranına bakarsan ikisinde de hata **yarıya** indi. `getiri_tablosu(olcumler)` işlevi iki okumayı yan yana verir.

- `olcumler`: en az iki öğeli liste; her öğe `(compute, dogruluk)`. Compute pozitif ve kesin artan; doğruluk `[0, 1)` aralığında (1.0 kabul edilmez: hata oranı 0 olur).
- Her ardışık çift için bir satır üret:
  - `kat`: `c1 / c0`
  - `puan_kazanci`: `d1 - d0`
  - `hata_carpani`: `(1 - d1) / (1 - d0)`
  - `on_kat_hata_carpani`: `hata_carpani ** (1 / log10(kat))`; aralıklar farklı genişlikte olsa da karşılaştırılabilsin diye 10 kat compute'a normalleştirilmiş hata çarpanı.
- Dönüş: satır sözlüklerinin listesi; değerler 6 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç hata çarpanını normalleştirmiyor: 2 kat ve 100 kat compute artışını aynı terazide tartıyor.

```starter
def getiri_tablosu(olcumler):
    out = []
    for (c0, d0), (c1, d1) in zip(olcumler, olcumler[1:]):
        h = (1 - d1) / (1 - d0)
        out.append({'kat': round(c1 / c0, 6), 'puan_kazanci': round(d1 - d0, 6), 'hata_carpani': round(h, 6), 'on_kat_hata_carpani': round(h, 6)})
    return out
```

```solution
def getiri_tablosu(olcumler):
    import math
    def sayi(x):
        return not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x)
    if not isinstance(olcumler, list) or len(olcumler) < 2:
        raise ValueError('en az iki ölçüm gerekli')
    onceki = 0
    for o in olcumler:
        if not isinstance(o, (tuple, list)) or len(o) != 2 or not sayi(o[0]) or not sayi(o[1]):
            raise ValueError('ölçüm (compute, dogruluk) olmalı')
        if not o[0] > onceki:
            raise ValueError('compute pozitif ve kesin artan olmalı')
        if not 0 <= o[1] < 1:
            raise ValueError('doğruluk [0, 1) aralığında olmalı')
        onceki = o[0]
    out = []
    for (c0, d0), (c1, d1) in zip(olcumler, olcumler[1:]):
        kat = c1 / c0
        h = (1 - d1) / (1 - d0)
        out.append({
            'kat': round(kat, 6),
            'puan_kazanci': round(d1 - d0, 6),
            'hata_carpani': round(h, 6),
            'on_kat_hata_carpani': round(h ** (1 / math.log10(kat)), 6),
        })
    return out
```

```test
need('getiri_tablosu')
import math, random

def _ref(o):
    out = []
    for i in range(len(o) - 1):
        c0, d0 = o[i]
        c1, d1 = o[i + 1]
        k = c1 / c0
        h = (1 - d1) / (1 - d0)
        out.append({'kat': round(k, 6), 'puan_kazanci': round(d1 - d0, 6), 'hata_carpani': round(h, 6), 'on_kat_hata_carpani': round(math.exp(math.log(h) / math.log10(k)) if h > 0 else 0.0, 6)})
    return out

r = getiri_tablosu([(1, 0.9), (10, 0.95), (100, 0.975)])
eq([x['puan_kazanci'] for x in r], [0.05, 0.025], 'puan kazancı yarıya düşüyor')
eq([x['on_kat_hata_carpani'] for x in r], [0.5, 0.5], 'ama her 10 katta hata yine yarılanıyor')
r = getiri_tablosu([(1, 0.5), (100, 0.875)])
eq(r, [{'kat': 100.0, 'puan_kazanci': 0.375, 'hata_carpani': 0.25, 'on_kat_hata_carpani': 0.5}], '100 katta 0.25, 10 kat başına 0.5')
r = getiri_tablosu([(10, 0.8), (20, 0.8)])
eq(r[0]['on_kat_hata_carpani'], 1.0, 'iyileşme yoksa çarpan 1')
r = getiri_tablosu([(1, 0.9), (10, 0.85)])
eq((r[0]['puan_kazanci'], r[0]['hata_carpani']), (-0.05, 1.5), 'gerileme: hata çarpanı 1 den büyük')
rng = random.Random(4103)
for _ in range(25):
    c, o = 1.0, []
    for _ in range(rng.randint(2, 7)):
        c = c * rng.choice([2, 3, 10, 30])
        o.append((c, round(rng.uniform(0.05, 0.98), 3)))
    got, exp = getiri_tablosu(o), _ref(o)
    eq(len(got), len(exp), 'satır sayısı')
    for g, e in zip(got, exp):
        for k in ('kat', 'puan_kazanci', 'hata_carpani', 'on_kat_hata_carpani'):
            yakin(g[k], e[k], f'rastgele ölçümde {k}', tol=2e-6)
eq(getiri_tablosu([(0.1, 0.5), (1.0, 0.75)])[0]['kat'], 10.0, 'birden küçük pozitif compute')
for kotu in (None, [], [(1, 0.5)], ["ab", (2, 0.6)], [123, (2, 0.6)], [(1, 0.5), (1, 0.6)], [(2, 0.5), (1, 0.6)], [(0, 0.5), (1, 0.6)], [(1, 0.5), (2, 1.0)], [(1, -0.1), (2, 0.5)], [(1, 0.5), (2,)], [(True, 0.5), (2, 0.6)], [(1, True), (2, 0.5)], [(1, False), (2, 0.5)], [(float('nan'), 0.5), (2, 0.6)], [(1, 0.5), (float('inf'), 0.6)], [(1, float('nan')), (2, 0.6)], [("1", 0.5), (2, 0.6)], ((1, 0.5), (2, 0.6))):
    raises(ValueError, getiri_tablosu, kotu, msg='bozuk ölçüm reddedilir')
```

```hint
`on_kat_hata_carpani = hata_carpani ** (1 / log10(kat))`. 100 katlık bir aralıkta `log10(kat) = 2`'dir; yani karekök alırsın.
```
:::

::: anlat 3. Ölçümleri okumak
Üç görev aynı dersi verir: **hangi ölçeğe baktığın, vardığın sonucu değiştirir.**

- Çarpımsal bir büyümeyi toplamayla okursan en büyük çarpanı küçümsersin (Görev 1).
- Seyrek ölçüm noktalarına bakarsan yöntemler arasındaki verimlilik farkını kaçırırsın (Görev 2).
- Doğruluğa bakarsan tavana yaklaşan her benchmark "yavaşlıyor" görünür; hata oranına bakarsan ilerleme sürüyor olabilir (Görev 3). Tersi de doğrudur: hata oranı yarılanması etkileyici görünür ama %99'dan %99.5'e çıkmak kullanıcı için fark yaratmayabilir.

İlerlemeyi sınırlayan şeyler de vardır ve bunlar da ölçülür:

| Sınır | Neden |
|---|---|
| Veri | Kaliteli insan metni sonludur; sentetik veri yardımcı olur ama kendi hatalarını çoğaltabilir |
| Enerji ve çip | Büyük eğitimler yüzlerce megavat ve sınırlı üretim kapasitesi ister |
| Değerlendirme | Benchmark doyduğunda ilerlemeyi ölçemezsin; ölçemediğini iyileştiremezsin |
| Getiri | Aynı hata çarpanı için her seferinde 10 kat compute gerekir; maliyet üstel büyür |
:::

::: anlat 4. Yaygın yanlışlar ve iki dakikalık anlatım
| Yanlış | Doğrusu |
|---|---|
| "Sadece daha büyük yapıyorlar." | Algoritma verimliliği ölçülmüş ve donanımdan hızlı iyileşmiştir. |
| "Daha çok veri her zaman daha iyi." | Kalitesiz ve yinelenen veri compute'u boşa harcar; seçim miktardan önemli olabilir. |
| "Moore yasası bitti, AI de yavaşlar." | Donanım üç çarpandan biridir. |
| "Skor artışı yavaşladı, tavan geldi." | Önce hata oranına bak; tavana yakın benchmark her zaman yavaş görünür. |
| "Yeni mimari her şeyi çözer." | Bitter lesson: uzun vadede ölçeklenen genel yöntemler kazandı. Ama bu bir görüştür, yasa değil. |

**İki dakikada anlatım iskeleti:**

1. **Üç kaynak (20 sn).** "Daha iyi AI üç şeyden gelir: daha çok hesap, daha iyi veri, daha akıllı algoritma. Bunlar toplanmaz, çarpılır."
2. **Çarpım (30 sn).** Tahmin adımındaki sayıları söyle: 1.4 × 2.5 × 2 = 7 kat. "Donanım tek başına yüzde 40; üçü birlikte yedi kat."
3. **Algoritma sürprizi (30 sn).** "Aynı görüntü tanıma başarısı için gereken hesap yedi yılda 44 kat azaldı. Bu, çip iyileşmesinden hızlı."
4. **Sınırlar (25 sn).** Veri sonlu, enerji sınırlı, her aynı adım için on kat hesap gerekiyor.
5. **Kapanış (15 sn).** "Soru 'büyütmek yeter mi' değil; 'bir sonraki on katı kim, neyle ödeyecek'."
:::

::: anlat Sınır
Bu ders iyileşmenin üç kaynağını ve üç okuma yöntemini anlatır. Görevlerdeki çarpanlar ve eğriler öğretim amaçlı seçilmiştir; hiçbir laboratuvarın ölçümü değildir. Logaritmik ayrıştırma, kaynakların bağımsız ve çarpımsal olduğunu varsayar; gerçekte etkileşirler (daha büyük model daha çok veriden yararlanır) ve paylar bu varsayıma bağlıdır. Hernandez ve Brown'ın 44 kat bulgusu tek bir görev ve tek bir hedef düzey içindir; dil modellerine doğrudan aktarılamaz. Log ölçekte ara değer bulma, eğrinin iki ölçüm arasında log-doğrusal olduğunu varsayar. Hata çarpanının 10 kata normalleştirilmesi güç yasası biçiminde bir eğri varsayar ve tavana çok yakın ölçümlerde gürültüye duyarlıdır. Bitter lesson tarihsel bir gözlemdir; geleceğe dair bir garanti değildir. Bu ders bir modelin "zekâ"sını ölçmez; yalnız seçilen bir ölçüdeki iyileşmeyi ayrıştırır.

Kaynaklar: [Sutton 2019 - The Bitter Lesson](http://www.incompleteideas.net/IncIdeas/BitterLesson.html), [Hernandez ve Brown 2020 - Measuring the Algorithmic Efficiency of Neural Networks](https://arxiv.org/abs/2005.04305), [Kaplan vd. 2020 - Scaling Laws for Neural Language Models](https://arxiv.org/abs/2001.08361), [Hoffmann vd. 2022 - Training Compute-Optimal Large Language Models](https://arxiv.org/abs/2203.15556).
:::

::: dusun
Bir haber başlığı "Yeni model yalnızca 2 puan daha iyi: yapay zekâda ilerleme durdu" diyor. Önceki model %96, yenisi %98 almış ve yenisi 10 kat compute ile eğitilmiş. Görev 3'teki iki okumayı kullanarak başlığı yeniden yaz. Sonra karşı tarafı da savun: hata yarılanmış olsa bile bu ilerleme hangi durumda gerçekten önemsizdir?
:::

::: ozet
- İyileşme üç kaynaktan gelir: compute (donanım × harcama), veri ve algoritma. Bunlar çarpılır; paylar logaritmayla ayrıştırılır.
- Algoritma verimliliği ölçülmüş bir büyüklüktür ve bazı görevlerde donanımdan hızlı iyileşmiştir.
- Yöntemleri "aynı skora kaç örnekle ulaşıyor" sorusuyla, log ölçekte ara değer bularak karşılaştır.
- Tavana yakın bir benchmark'ta puan kazancı küçülür; hata oranı çarpanı ilerlemenin sürüp sürmediğini gösterir. İki okumayı birlikte ver.
- Bitter lesson bir görüştür: ölçeklenen genel yöntemler tarihsel olarak kazandı; veri, enerji ve maliyet sınırları ise gerçektir.
:::
