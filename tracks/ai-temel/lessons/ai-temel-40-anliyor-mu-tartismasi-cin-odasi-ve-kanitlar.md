---
id: ai-temel-40
title: "Anlıyor mu, Taklit mi Ediyor? · Çin Odası, Stochastic Parrots ve Ölçülebilir Karşı Kanıtlar"
summary: Felsefi tartışmayı üç ölçüye indir: test verisi eğitime sızmış mı, yüzey değişince doğruluk düşüyor mu, görülmemiş birleşimler çözülüyor mu; her görüşün en güçlü hâlini ve sınırını anlat.
---

::: anlat 1. Soru: "Gerçekten anlıyor mu, yoksa taklit mi ediyor?"
Bu soru 1980'den beri soruluyor ve iki kampın da güçlü argümanları var. Önce argümanları en güçlü hâlleriyle tanı; sonra tartışmayı ölçülebilir hâle getir.

**Çin Odası (Searle, 1980).** Bir odada Çince bilmeyen biri oturuyor. Elinde, gelen Çince sembollere hangi sembollerle karşılık vereceğini söyleyen dev bir kural kitabı var. Dışarıdaki Çinli, odanın Çince anladığını düşünür. Searle'ün iddiası: içerideki kişi hiçbir şey anlamıyor; yalnız sembolleri biçimlerine göre işliyor. Sözdizimi (`syntax`) anlam (`semantics`) için yetmez.

**Stochastic Parrots (Bender ve Koller 2020; Bender vd. 2021).** Yalnız metinle eğitilen bir sistem, kelimelerin dünyadaki karşılığına hiç erişmez. Biçimden anlam öğrenilemez; model olası kelime dizilerini birleştirir.

**Karşı argümanlar:**

- **Sistem cevabı.** Odadaki kişi anlamıyor olabilir ama kişi + kitap + oda **sistemi** anlıyor olabilir. Tek bir nöron da Türkçe anlamaz.
- **Davranış cevabı.** "Anlama"yı içeriden göremiyoruz; insanlarda da yalnız davranışa bakıyoruz. Bir sistem görmediği problemleri tutarlı biçimde çözüyorsa, buna anlama demeyi reddetmek keyfî olur.
- **Deneysel cevap.** Bazı modellerin iç temsillerinde verinin arkasındaki yapı okunabiliyor (bkz. `ai-temel-38`, Othello-GPT).

> [!NOT]
> Bunların hepsi **görüştür**. Alan uzlaşmış değildir; Mitchell ve Krakauer (2023) iki kampı da ciddiye alan bir derleme yazmıştır. Bu derste hiçbir kampın haklı olduğu iddia edilmez.
:::

::: anlat 2. Tartışmayı ölçülebilir yapmak
"Anlıyor mu?" sorusunun kendisi ölçülemez, çünkü "anlamak" için üzerinde uzlaşılmış bir tanım yok. Ama her kampın **öngörüsü** ölçülebilir:

| Soru | "Yalnız taklit" öngörür | "Yapıyı öğrendi" öngörür | Görev |
|---|---|---|---|
| Test sorusu eğitimde geçti mi? | Başarı ezberden gelir | Ezber olmadan da başarır | 1 |
| Sorudaki isim ve sayılar değişince ne olur? | Doğruluk düşer | Doğruluk korunur | 2 |
| Parçalarını bildiği ama birleşimini görmediği durum? | Başarısız olur | Başarır | 3 |

Gerçek modellerde bulgular karışıktır:

- **Sızıntı gerçektir.** Yaygın benchmark'ların soruları internette durur ve eğitim verisine girer. Yüksek skor, kısmen ezber olabilir. Bu yüzden ciddi değerlendirmeler önce `contamination` denetler.
- **Yüzey değişimi doğruluğu düşürür.** Mirzadeh ve arkadaşları (2024), matematik sorularında yalnız isim ve sayıları değiştirdiklerinde modellerin doğruluğunun düştüğünü, soruya ilgisiz bir cümle eklendiğinde ise belirgin biçimde düştüğünü ölçtü. Düşüş modele göre değişir; en güçlü modellerde küçüktür ama sıfır değildir.
- **Birleşimsel genelleme kısmidir.** Lake ve Baroni (2018), dizi modellerinin görülmüş parçaların yeni birleşimlerinde zorlandığını gösterdi. Sonraki modeller bu testlerde çok daha iyidir, ama zorluk tümüyle kaybolmamıştır.

Yani dürüst cevap ikili değildir: modeller **ne yalnız ezberler ne de insan gibi genelleştirir**. Ne kadarının hangisi olduğu, soru başına ölçülür.
:::

::: tahmin Kural kitabı odası
Aşağıdaki "oda" yalnız kural kitabındaki soruları cevaplayabiliyor. Üç soru soruluyor; ne yazdırılır?

```python
kural_kitabi = {"2+3": "5", "4+1": "5", "2+2": "4"}

def oda(soru):
    return kural_kitabi.get(soru, "?")

for soru in ("2+3", "3+2", "2 + 3"):
    print(repr(soru), "->", oda(soru))
```

???

```cikti
'2+3' -> 5
'3+2' -> ?
'2 + 3' -> ?
```
Oda `2+3`'ü biliyor ama aynı toplamın yer değiştirmiş hâlini (`3+2`) ve boşluklu yazımını (`2 + 3`) bilmiyor. Toplamayı öğrenmiş bir sistem üçünü de çözerdi. "Görülmüş soruda başarı" ile "yapıyı öğrenme" arasındaki fark budur ve ancak **görülmemiş** girdiyle ölçülür. Görev 2 ve 3 bu ölçümü yapar.
:::

::: gorev 1 · Test verisi eğitime sızmış mı? (n-gram örtüşmesi)
`sizinti_orani(test_ornekleri, egitim_metni, n)` işlevini yaz. Her test örneğinin kelime n-gram'larından kaçının eğitim metninde aynen geçtiğini ölçer.

- `test_ornekleri`: boş olmayan `str` listesi. `egitim_metni`: `str`. `n`: pozitif `int`.
- Kelimeler `casefold().split()` ile ayrılır. Bir örneğin n-gram'ı, ardışık `n` kelimelik demettir.
- Her örnek için `oran = eğitimde geçen n-gram sayısı / örneğin n-gram sayısı` (yinelenen n-gram'lar ayrı ayrı sayılır). `n`'den kısa örneğin n-gram'ı yoktur; oranı `None` olur.
- Dönüş: `{'oranlar': [...], 'ortalama': None olmayan oranların ortalaması ya da None}`. Sayılar 6 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç n-gram yerine tek tek kelimelere bakıyor. "ve", "bir" gibi sık kelimeler her metinde geçtiği için her örnek sızmış görünür.

```starter
def sizinti_orani(test_ornekleri, egitim_metni, n):
    egitim = set(egitim_metni.casefold().split())
    oranlar = []
    for t in test_ornekleri:
        k = t.casefold().split()
        oranlar.append(round(sum(1 for w in k if w in egitim) / len(k), 6))
    return {'oranlar': oranlar, 'ortalama': round(sum(oranlar) / len(oranlar), 6)}
```

```solution
def sizinti_orani(test_ornekleri, egitim_metni, n):
    if not isinstance(test_ornekleri, list) or not test_ornekleri or any(not isinstance(t, str) for t in test_ornekleri):
        raise ValueError('test_ornekleri boş olmayan str listesi olmalı')
    if not isinstance(egitim_metni, str):
        raise ValueError('egitim_metni str olmalı')
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError('n pozitif int olmalı')

    def ngramlar(metin):
        k = metin.casefold().split()
        return [tuple(k[i:i + n]) for i in range(len(k) - n + 1)]

    egitim = set(ngramlar(egitim_metni))
    oranlar = []
    for t in test_ornekleri:
        g = ngramlar(t)
        oranlar.append(round(sum(1 for x in g if x in egitim) / len(g), 6) if g else None)
    dolu = [o for o in oranlar if o is not None]
    return {'oranlar': oranlar, 'ortalama': round(sum(dolu) / len(dolu), 6) if dolu else None}
```

```test
need('sizinti_orani')
import random

def _ref(tests, egitim, n):
    def ng(m):
        k = m.casefold().split()
        out = []
        for i in range(0, len(k) - n + 1):
            out.append(" ".join(k[i:i + n]))
        return out
    e = set(ng(egitim))
    oranlar = []
    for t in tests:
        g = ng(t)
        oranlar.append(None if not g else round(len([x for x in g if x in e]) / len(g), 6))
    d = [o for o in oranlar if o is not None]
    return {'oranlar': oranlar, 'ortalama': None if not d else round(sum(d) / len(d), 6)}

egitim = "Ali nin üç elması var ve iki elma daha aldı"
eq(sizinti_orani(["ali nin üç elması var"], egitim, 3), {'oranlar': [1.0], 'ortalama': 1.0}, 'aynen geçen örnek tam sızıntı')
eq(sizinti_orani(["var ve üç bir elma"], egitim, 3), {'oranlar': [0.0], 'ortalama': 0.0}, 'ortak kelime var ama ortak 3-gram yok')
eq(sizinti_orani(["Ali nin üç armudu var"], egitim, 2), {'oranlar': [0.5], 'ortalama': 0.5}, 'kısmi örtüşme: 4 2-gramdan 2si')
eq(sizinti_orani(["kısa", "ali nin üç"], egitim, 3), {'oranlar': [None, 1.0], 'ortalama': 1.0}, 'n den kısa örnek None, ortalamaya girmez')
eq(sizinti_orani(["a"], "a b", 2), {'oranlar': [None], 'ortalama': None}, 'hiç n-gram yoksa ortalama None')
eq(sizinti_orani(["a a a"], "a a", 2), {'oranlar': [1.0], 'ortalama': 1.0}, 'yinelenen n-gram ayrı sayılır')
eq(sizinti_orani(["x y"], "", 1), {'oranlar': [0.0], 'ortalama': 0.0}, 'boş eğitim metni')
rng = random.Random(4001)
for _ in range(25):
    soz = ["ve", "bir", "elma", "ali", "üç", "Var", "aldı", "iki"]
    egt = " ".join(rng.choice(soz) for _ in range(rng.randint(0, 30)))
    tests = [" ".join(rng.choice(soz) for _ in range(rng.randint(0, 8))) for _ in range(rng.randint(1, 5))]
    n = rng.randint(1, 4)
    eq(sizinti_orani(tests, egt, n), _ref(tests, egt, n), 'rastgele metinde bağımsız referansla aynı')
for a in ([None, "a", 1], [[], "a", 1], [["a"], None, 1], [["a"], "a", 0], [["a"], "a", 1.0], [["a"], "a", True], [[1], "a", 1], ["a b", "a", 1], [("a",), "a", 1]):
    raises(ValueError, sizinti_orani, *a, msg='bozuk girdi reddedilir')
```

```hint
n-gram'ı demet olarak üret: `tuple(k[i:i + n])`, `i` için `range(len(k) - n + 1)`. Eğitim n-gram'larını bir kümeye koy; her test n-gram'ı için üyelik sor.
```
:::

::: gorev 2 · Yüzey değişince doğruluk düşüyor mu?
Aynı sorunun iki hâli modele soruluyor: `ozgun` (benchmark'taki hâli) ve `degismis` (yalnız isimler ve sayılar değiştirilmiş, mantık aynı). `yuzey_dayanikliligi(sonuclar)` işlevi ikisi arasındaki farkı ölçer.

- `sonuclar`: boş olmayan liste; her öğe `{'soru': str, 'varyant': 'ozgun' | 'degismis', 'dogru': bool}` (tam bu üç anahtar).
- Bir soru için aynı varyanttan birden çok kayıt olabilir (farklı değişmiş sürümler). Önce **soru başına** her varyantın doğruluk oranı alınır.
- Yalnız iki varyantı da olan sorular hesaba katılır. `ozgun` ve `degismis`, bu soruların oranlarının ortalamasıdır.
- Dönüş: `{'soru_sayisi': ..., 'ozgun': ..., 'degismis': ..., 'dusus': ozgun - degismis}`. Eşleşen soru yoksa `soru_sayisi` 0, diğerleri `None`. Sayılar 6 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç eşleştirme yapmadan bütün kayıtları varyanta göre topluyor. Bir sorunun on değişmiş sürümü varsa o soru ortalamayı ele geçirir; tek varyantı olan sorular da hesaba girer.

```starter
def yuzey_dayanikliligi(sonuclar):
    o = [s['dogru'] for s in sonuclar if s['varyant'] == 'ozgun']
    d = [s['dogru'] for s in sonuclar if s['varyant'] == 'degismis']
    a, b = sum(o) / len(o), sum(d) / len(d)
    return {'soru_sayisi': len(o), 'ozgun': round(a, 6), 'degismis': round(b, 6), 'dusus': round(a - b, 6)}
```

```solution
def yuzey_dayanikliligi(sonuclar):
    if not isinstance(sonuclar, list) or not sonuclar:
        raise ValueError('sonuclar boş olmayan liste olmalı')
    tablo = {}
    for s in sonuclar:
        if not isinstance(s, dict) or set(s) != {'soru', 'varyant', 'dogru'}:
            raise ValueError('kayıt şeması')
        if not isinstance(s['soru'], str) or not s['soru'] or s['varyant'] not in ('ozgun', 'degismis') or not isinstance(s['dogru'], bool):
            raise ValueError('kayıt değeri')
        tablo.setdefault(s['soru'], {'ozgun': [], 'degismis': []})[s['varyant']].append(s['dogru'])
    cift = [v for v in tablo.values() if v['ozgun'] and v['degismis']]
    if not cift:
        return {'soru_sayisi': 0, 'ozgun': None, 'degismis': None, 'dusus': None}
    o = sum(sum(v['ozgun']) / len(v['ozgun']) for v in cift) / len(cift)
    d = sum(sum(v['degismis']) / len(v['degismis']) for v in cift) / len(cift)
    return {'soru_sayisi': len(cift), 'ozgun': round(o, 6), 'degismis': round(d, 6), 'dusus': round(o - d, 6)}
```

```test
need('yuzey_dayanikliligi')
import random

def K(soru, varyant, dogru):
    return {'soru': soru, 'varyant': varyant, 'dogru': dogru}

def _ref(sonuclar):
    sorular = sorted({s['soru'] for s in sonuclar})
    oo, dd = [], []
    for q in sorular:
        o = [s['dogru'] for s in sonuclar if s['soru'] == q and s['varyant'] == 'ozgun']
        d = [s['dogru'] for s in sonuclar if s['soru'] == q and s['varyant'] == 'degismis']
        if o and d:
            oo.append(o.count(True) / len(o))
            dd.append(d.count(True) / len(d))
    if not oo:
        return {'soru_sayisi': 0, 'ozgun': None, 'degismis': None, 'dusus': None}
    a, b = sum(oo) / len(oo), sum(dd) / len(dd)
    return {'soru_sayisi': len(oo), 'ozgun': round(a, 6), 'degismis': round(b, 6), 'dusus': round(a - b, 6)}

s = [K('q1', 'ozgun', True), K('q1', 'degismis', False), K('q2', 'ozgun', True), K('q2', 'degismis', True)]
eq(yuzey_dayanikliligi(s), {'soru_sayisi': 2, 'ozgun': 1.0, 'degismis': 0.5, 'dusus': 0.5}, 'iki soru, biri değişince bozuluyor')
s = [K('q1', 'ozgun', True)] + [K('q1', 'degismis', False)] * 9 + [K('q2', 'ozgun', True), K('q2', 'degismis', True)]
eq(yuzey_dayanikliligi(s), {'soru_sayisi': 2, 'ozgun': 1.0, 'degismis': 0.5, 'dusus': 0.5}, 'dokuz değişmiş sürüm tek sorunun ağırlığını artırmaz')
s = [K('q1', 'ozgun', True), K('q1', 'degismis', True), K('q3', 'ozgun', False), K('q4', 'degismis', False)]
eq(yuzey_dayanikliligi(s), {'soru_sayisi': 1, 'ozgun': 1.0, 'degismis': 1.0, 'dusus': 0.0}, 'tek varyantlı sorular hesaba girmez')
eq(yuzey_dayanikliligi([K('q1', 'ozgun', True)]), {'soru_sayisi': 0, 'ozgun': None, 'degismis': None, 'dusus': None}, 'eşleşen soru yok')
s = [K('q1', 'ozgun', False), K('q1', 'degismis', True)]
eq(yuzey_dayanikliligi(s)['dusus'], -1.0, 'negatif düşüş: değişmiş hâl daha iyi')
rng = random.Random(4002)
for _ in range(25):
    s = [K(f"q{rng.randint(0, 5)}", rng.choice(['ozgun', 'degismis']), rng.random() < 0.6) for _ in range(rng.randint(1, 30))]
    eq(yuzey_dayanikliligi(s), _ref(s), 'rastgele sonuçlarda bağımsız referansla aynı')
for kotu in (None, [], [1], [{'soru': 'q'}], [K('q', 'baska', True)], [K('q', 'ozgun', 1)], [K('', 'ozgun', True)], [K(1, 'ozgun', True)], [dict(K('q', 'ozgun', True), ek=1)], (K('q', 'ozgun', True),)):
    raises(ValueError, yuzey_dayanikliligi, kotu, msg='bozuk kayıt reddedilir')
```

```hint
Önce `{soru: {'ozgun': [...], 'degismis': [...]}}` tablosunu kur. Sonra iki listesi de dolu olan sorularda her varyantın oranını al ve bu oranların ortalamasını hesapla.
```
:::

::: gorev 3 · Birleşimsel genelleme: parçaları biliyor, birleşimi görmedi
Model `(eylem, nesne)` çiftleriyle eğitildi. Test sorularını üç sınıfa ayır ve her sınıfın doğruluğunu ölç: `bilesimsel_genelleme(egitim_ciftleri, test_sonuclari)`.

- `egitim_ciftleri`: boş olmayan liste; her öğe iki boş olmayan `str` içeren demet ya da liste.
- `test_sonuclari`: boş olmayan liste; her öğe `(eylem, nesne, dogru)`; `dogru` `bool`.
- Sınıflar: `gorulmus` (çift eğitimde aynen var), `yeni_bilesim` (eylem eğitimde bir çiftin eylemi, nesne bir çiftin nesnesi olarak geçmiş ama bu çift yok), `yeni_parca` (eylem ya da nesne eğitimde hiç geçmemiş).
- Dönüş: `{sınıf: {'adet': n, 'dogruluk': oran ya da None}}`; üç sınıf da her zaman bulunur. Oran 6 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç yalnız "eğitimde var mı, yok mu" diye ikiye ayırıyor. Asıl ilginç sınıf olan `yeni_bilesim`, hiç görülmemiş parçalarla aynı kefeye giriyor.

```starter
def bilesimsel_genelleme(egitim_ciftleri, test_sonuclari):
    gorulen = set(map(tuple, egitim_ciftleri))
    out = {'gorulmus': [], 'yeni_bilesim': [], 'yeni_parca': []}
    for e, n, d in test_sonuclari:
        out['gorulmus' if (e, n) in gorulen else 'yeni_parca'].append(d)
    return {k: {'adet': len(v), 'dogruluk': round(sum(v) / len(v), 6) if v else None} for k, v in out.items()}
```

```solution
def bilesimsel_genelleme(egitim_ciftleri, test_sonuclari):
    def cift_mi(c, uzunluk):
        return isinstance(c, (tuple, list)) and len(c) == uzunluk and all(isinstance(x, str) and x for x in c[:2])
    if not isinstance(egitim_ciftleri, list) or not egitim_ciftleri or any(not cift_mi(c, 2) for c in egitim_ciftleri):
        raise ValueError('egitim_ciftleri')
    if not isinstance(test_sonuclari, list) or not test_sonuclari or any(not cift_mi(t, 3) or not isinstance(t[2], bool) for t in test_sonuclari):
        raise ValueError('test_sonuclari')
    gorulen = {(e, n) for e, n in egitim_ciftleri}
    eylemler = {e for e, _ in gorulen}
    nesneler = {n for _, n in gorulen}
    kova = {'gorulmus': [], 'yeni_bilesim': [], 'yeni_parca': []}
    for e, n, d in test_sonuclari:
        if (e, n) in gorulen:
            kova['gorulmus'].append(d)
        elif e in eylemler and n in nesneler:
            kova['yeni_bilesim'].append(d)
        else:
            kova['yeni_parca'].append(d)
    return {k: {'adet': len(v), 'dogruluk': round(sum(1 for x in v if x) / len(v), 6) if v else None} for k, v in kova.items()}
```

```test
need('bilesimsel_genelleme')
import random

def _ref(egitim, test):
    g = [tuple(c) for c in egitim]
    E = [c[0] for c in g]
    N = [c[1] for c in g]
    kova = {'gorulmus': [], 'yeni_bilesim': [], 'yeni_parca': []}
    for e, n, d in test:
        if (e, n) in g:
            s = 'gorulmus'
        elif e not in E or n not in N:
            s = 'yeni_parca'
        else:
            s = 'yeni_bilesim'
        kova[s].append(d)
    return {k: {'adet': len(v), 'dogruluk': None if not v else round(v.count(True) / len(v), 6)} for k, v in kova.items()}

egitim = [("zıpla", "iki kez"), ("yürü", "iki kez"), ("yürü", "sola")]
test = [("yürü", "sola", True), ("zıpla", "sola", False), ("zıpla", "sola", True), ("koş", "sola", False), ("yürü", "geri", False)]
eq(bilesimsel_genelleme(egitim, test), {'gorulmus': {'adet': 1, 'dogruluk': 1.0}, 'yeni_bilesim': {'adet': 2, 'dogruluk': 0.5}, 'yeni_parca': {'adet': 2, 'dogruluk': 0.0}}, 'üç sınıf ayrı ölçülür')
eq(bilesimsel_genelleme([("a", "b")], [("a", "b", True)]), {'gorulmus': {'adet': 1, 'dogruluk': 1.0}, 'yeni_bilesim': {'adet': 0, 'dogruluk': None}, 'yeni_parca': {'adet': 0, 'dogruluk': None}}, 'boş sınıfın doğruluğu None')
eq(bilesimsel_genelleme([("a", "b"), ("c", "d")], [("b", "a", True)])['yeni_parca']['adet'], 1, 'eylem yerinde görülen kelime nesne olarak sayılmaz')
eq(bilesimsel_genelleme([["a", "b"], ["c", "d"]], [["a", "d", True]])['yeni_bilesim'], {'adet': 1, 'dogruluk': 1.0}, 'liste biçimli girdi kabul edilir')
rng = random.Random(4003)
for _ in range(25):
    ey = [f"e{i}" for i in range(4)]
    ne = [f"n{i}" for i in range(4)]
    egt = [(rng.choice(ey[:3]), rng.choice(ne[:3])) for _ in range(rng.randint(1, 6))]
    tst = [(rng.choice(ey), rng.choice(ne), rng.random() < 0.5) for _ in range(rng.randint(1, 20))]
    eq(bilesimsel_genelleme(egt, tst), _ref(egt, tst), 'rastgele veride bağımsız referansla aynı')
iyi_e, iyi_t = [("a", "b")], [("a", "b", True)]
for e, t in [(None, iyi_t), ([], iyi_t), (["ab"], iyi_t), ([("a",)], iyi_t), ([("a", 1)], iyi_t), ([("", "b")], iyi_t), (iyi_e, None), (iyi_e, []), (iyi_e, tuple(iyi_t)), (iyi_e, ["abc"]), (iyi_e, [("a", "b")]), (iyi_e, [("a", "b", 1)]), (iyi_e, [("a", "", True)]), (tuple(iyi_e), iyi_t)]:
    raises(ValueError, bilesimsel_genelleme, e, t, msg='bozuk girdi reddedilir')
```

```hint
Üç küme kur: görülen çiftler, görülen eylemler, görülen nesneler. Sıra önemli: önce çift görülmüş mü, sonra iki parça da ayrı ayrı görülmüş mü, değilse `yeni_parca`.
```
:::

::: anlat 3. Ölçümler tartışmayı nereye götürür?
Bu üç ölçü "anlıyor mu?" sorusunu cevaplamaz; soruyu **daha iyi bir soruyla** değiştirir:

- Sızıntı oranı yüksekse başarı hakkında hiçbir şey söyleyemezsin. Önce temiz veriyle ölç.
- Yüzey değişiminde düşüş büyükse model sorunun mantığına değil, biçimine tutunmuştur.
- `yeni_bilesim` doğruluğu `gorulmus`'a yakınsa model kuralı öğrenmiştir; `yeni_parca`'ya yakınsa ezberlemiştir.

Searle'ün argümanı bu ölçümlerle çürütülmez: bir sistem üç testi de geçse bile "yine de anlamıyor" denebilir. Bu, argümanın gücü mü yoksa zayıflığı mı? İki bakış var:

- **Savunanlar:** Davranış ne kadar iyi olursa olsun, anlam bilinçli deneyim gerektirir ve bu ölçülemez.
- **Eleştirenler:** Hiçbir gözlemle sınanamayan bir iddia bilimsel değildir; anlamayı davranışla tanımlamak zorundayız.

Güvenlik mühendisi için pratik sonuç felsefi olandan bağımsızdır: bir modelin bir işi "anladığına" güvenmek yerine, **o işteki genellemesini ölç**. Bir güvenlik sınıflandırıcısı benchmark'ta %99 alıp gerçek trafikte çöküyorsa, sebep çoğu zaman bu üç ölçüden biridir.
:::

::: anlat 4. Yaygın yanlışlar ve iki dakikalık anlatım
| Yanlış | Doğrusu |
|---|---|
| "Çin Odası LLM'lerin anlamadığını kanıtladı." | Bir düşünce deneyidir, kanıt değildir; güçlü karşı cevapları vardır. |
| "Sınavı geçti, demek anlıyor." | Sınav soruları eğitim verisine sızmış olabilir. Önce sızıntıyı ölç. |
| "Sadece ezberliyor." | Görülmemiş birleşimlerde de başarı var; ezber tek başına açıklamıyor. |
| "İnsan gibi genelleştiriyor." | Yüzey değişimlerinde insanın yapmayacağı düşüşler ölçüldü. |
| "Bu felsefi bir tartışma, ölçülemez." | "Anlama" ölçülemez, ama her kampın öngörüsü ölçülür. |

**İki dakikada anlatım iskeleti:**

1. **Çin Odası (30 sn).** Odayı anlat. "Dışarıdan Çince biliyor gibi görünüyor. İçeride kimse anlamıyor. Peki sistem anlıyor mu?"
2. **Soruyu değiştir (20 sn).** "Bu soruyu cevaplayamayız. Ama şunu ölçebiliriz: görmediği bir şeyde ne yapıyor?"
3. **Üç test (50 sn).** Soruyu daha önce gördü mü? İsimleri değiştirince bozuluyor mu? Bildiği parçaların yeni birleşimini çözüyor mu? Tahmin adımındaki `2+3` ve `3+2` örneğini kullan.
4. **Kapanış (20 sn).** "Bugünkü modeller ne papağan ne insan. Ortada bir yerdeler ve nerede olduklarını soru başına ölçüyoruz."
:::

::: anlat Sınır
Bu ders "anlama" tartışmasının iki kampını ve üç ölçüyü anlatır; hangi kampın haklı olduğu konusunda bir sonuca varmaz. Görevler sentetik veri üzerinde çalışır ve gerçek bir modeli değerlendirmez. n-gram örtüşmesi yalnız birebir sızıntıyı yakalar: başka kelimelerle yazılmış ya da çevrilmiş sızıntıyı kaçırır, sık kullanılan kalıplar yüzünden de yanlış alarm verebilir. Yüzey dayanıklılığı ölçüsü, değişmiş soruların özgünle aynı zorlukta olduğunu varsayar; bu varsayım elle doğrulanmalıdır. Birleşimsel genelleme görevi iki parçalı çiftlerle sınırlıdır; gerçek dilde birleşimler çok daha derindir. Mirzadeh ve arkadaşlarının bulguları belirli modeller ve bir matematik veri kümesi içindir; düşüşün büyüklüğü modele göre değişir. Bilinç ve öznel deneyim bu ölçülerin dışındadır.

Kaynaklar: [Searle 1980 - Minds, brains, and programs](https://doi.org/10.1017/S0140525X00005756), [Bender ve Koller 2020 - Climbing towards NLU](https://aclanthology.org/2020.acl-main.463/), [Mitchell ve Krakauer 2023 - The debate over understanding in AI's large language models](https://doi.org/10.1073/pnas.2215907120), [Mirzadeh vd. 2024 - GSM-Symbolic](https://arxiv.org/abs/2410.05229), [Lake ve Baroni 2018 - Generalization without Systematicity](https://arxiv.org/abs/1711.00350).
:::

::: dusun
Bir satıcı sana "modelimiz güvenlik sertifika sınavında %94 aldı" diyor. Bu derste öğrendiğin üç ölçüyü kullanarak ona soracağın üç soruyu yaz. Her soru için: hangi cevap seni ikna eder, hangi cevap şüphelendirir?
:::

::: ozet
- Çin Odası ve Stochastic Parrots, biçimden anlam çıkmayacağını savunur; sistem cevabı ve deneysel bulgular buna karşı çıkar. İkisi de görüştür.
- "Anlıyor mu?" ölçülemez; her kampın öngörüsü ölçülür: sızıntı, yüzey dayanıklılığı, birleşimsel genelleme.
- Benchmark başarısı, test verisi eğitime sızdıysa bir şey kanıtlamaz. Önce n-gram örtüşmesine bak.
- Yalnız isim ve sayı değişince doğruluk düşüyorsa model biçime tutunmuştur.
- `yeni_bilesim` doğruluğu, kuralın öğrenilip öğrenilmediğinin en doğrudan göstergesidir. Modeller bu ölçüde ne papağan ne insandır.
:::
