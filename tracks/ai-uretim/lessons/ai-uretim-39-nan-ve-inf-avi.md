---
id: ai-uretim-39
title: "NaN ve Inf Avı · Nerede Doğdu, Nasıl Yayıldı?"
summary: "Katman çıktılarını sırayla tarayıp ilk bozulan yeri bul, taşan bir log-sum-exp'i kararlı biçimde yeniden yaz ve bir hesap grafında tek bir NaN'in hangi düğümlere yayıldığını çıkar."
track: ai-uretim
order: 39
---

::: anlat 1. Kayıp `nan` oldu
Eğitimin en sinir bozucu hatası budur: kayıp `nan` yazıyor ve geri dönüş yok. `nan` bulaşıcıdır; bir kez doğduktan sonra dokunduğu her sayıyı `nan` yapar, geri geçişte bütün gradient'lere, oradan bütün ağırlıklara yayılır. Bir sonraki adımda modelin tamamı `nan`'dir.

Bu yüzden kayba bakmak işe yaramaz: orası zincirin **sonudur**. Aranan şey ilk doğduğu yerdir.

`nan` (not a number) ve `inf` (sonsuz) `IEEE 754` kayan nokta standardının özel değerleridir. Olağan doğum yerleri:

| İşlem | Sonuç | Eğitimde nerede çıkar |
|---|---|---|
| `exp(büyük sayı)` | `inf` | `softmax`, `logsumexp`, büyük `logit` |
| `log(0)` | `-inf` | Olasılığı sıfıra yuvarlanan sınıfın cross-entropy'si |
| `0 / 0`, `inf - inf`, `0 · inf` | `nan` | Sıfır varyansla normalleştirme, taşan iki terimin farkı |
| `sqrt(negatif)` | `nan` | Yuvarlama yüzünden hafif negatif çıkan bir varyans |
| `x / 0` | `inf` | Boş bir maskeyle ortalama almak |

Çoğu `nan`, önce bir `inf` olarak doğar ve bir sonraki işlemde `nan`'e döner.

| Soru | Araç | Görev |
|---|---|---|
| İlk bozulan katman hangisi? | Sıralı tarama | 1 |
| Taşan işlem nasıl kararlı yazılır? | `log-sum-exp` hilesi | 2 |
| Bozulma nerelere yayıldı, nerede durdu? | Hesap grafında yayılım | 3 |

> [!NOT]
> Görevlerdeki katman çıktıları ve hesap grafları sentetiktir; canlı bir eğitimden alınmamıştır. PyTorch'ta aynı işi yapan araçlar anlatımda gösterilir.
:::

::: anlat 2. İlk bozulan yer, kararlı yazım ve yayılım
**İlk bozulan yeri bulmak.** PyTorch'ta iki araç vardır:

```python norun
import torch

torch.autograd.set_detect_anomaly(True)   # geri geçişte nan üreten işlemi iz kaydıyla bildirir (yavaştır)

def denetle(ad):
    def kanca(modul, girdi, cikti):
        if not torch.isfinite(cikti).all():
            raise RuntimeError(f"sonlu olmayan çıktı: {ad}")
    return kanca

for ad, modul in model.named_modules():
    modul.register_forward_hook(denetle(ad))
```

`Forward hook`'lar katmanları **ileri geçiş sırasıyla** denetler; ilk hata veren katman, bozulmanın doğduğu yerdir. Görev 1 aynı taramayı kaydedilmiş çıktılar üzerinde yapar.

**Kararlı yazım: log-sum-exp.** $\log \sum_i e^{x_i}$ ifadesi `softmax`'in ve cross-entropy'nin çekirdeğidir. Doğrudan yazılırsa $x = 1000$ için $e^{1000}$ taşar ve sonuç `inf` olur; $x = -1000$ için $e^{-1000}$ sıfıra iner ve `log(0) = -inf` çıkar. Oysa doğru cevap sıradan bir sayıdır. Hile, en büyük değeri dışarı almaktır:

$$\log \sum_i e^{x_i} = m + \log \sum_i e^{x_i - m}, \qquad m = \max_i x_i$$

Artık en büyük üs $e^0 = 1$'dir: taşma olmaz. Toplamın içinde en az bir tane 1 vardır: sıfıra inme olmaz. Bu yüzden olasılık hesaplayıp sonra logaritma almak yerine her zaman birleşik işlev (`log_softmax`, `cross_entropy`, `logsumexp`) kullanılır.

Aynı aileden diğer çareler: bölmede ve karekökte paydaya küçük bir `eps` eklemek; `log(p)` yerine `log(p + eps)` ya da olasılığı kırpmak; `fp16` kullanırken `eps`'in o hassasiyette sıfıra yuvarlanmadığından emin olmak ($10^{-8}$, `fp16`'da sıfırdır).

**Yayılım.** `nan` girdi alan hemen her işlem `nan` verir. Bunu durduran az sayıda işlem vardır: `nan_to_num`, bir maskeyle seçim yapan `where` (ama yalnız ileri geçişte; geri geçişte `nan` gradient yine sızabilir) ve bozuk örneği tamamen atlamak. Bir hesap grafında bozulmanın kaynağını ve durdurucuları bilirsen hangi düğümlerin etkilendiğini çıkarabilirsin; bu, "kayıp temiz ama bir metrik `nan`" gibi kısmi bozulmaları açıklar.
:::

::: tahmin Özel değerlerin aritmetiği
Aşağıdaki işlemler ne yazdırılır?

```python
import math

inf, nan = float("inf"), float("nan")
print(inf - inf)
print(0.0 * inf)
print(nan == nan)
print(math.isnan(nan), max(1.0, nan), max(nan, 1.0))
```

???

```cikti
nan
nan
False
True 1.0 nan
```
`inf - inf` ve `0 · inf` belirsizdir: `nan`. `nan` hiçbir şeye, kendisine bile eşit değildir; bu yüzden `x == float("nan")` denetimi asla tutmaz, `math.isnan` kullanılır. Son satır tuzaktır: Python'un `max` işlevi karşılaştırmaya dayanır ve `nan` ile her karşılaştırma `False` verdiği için sonuç **argüman sırasına** bağlıdır. Bir listenin en büyüğünü alarak `nan` aramak güvenilmezdir; bozulma sessizce kaybolabilir.
:::

::: gorev 1 · İlk bozulan katmanı bul
`ilk_bozuk_katman(katmanlar)` işlevini yaz.

- `katmanlar`: boş olmayan liste, **ileri geçiş sırasıyla**; her öğe `(ad, degerler)`; `ad` boş olmayan `str`, `degerler` boş olmayan sayı listesi.
- Sonlu olmayan değer içeren **ilk** katmanı bul.
- Dönüş: bozulma yoksa `None`. Varsa `{'katman': ad, 'indeks': sırası, 'tur': 'nan' | 'inf' | 'ikisi', 'oran': bozuk değer oranı}`; `tur`, o katmanda yalnız `nan`, yalnız `inf` (artı ya da eksi) ya da ikisinin de bulunmasına göre belirlenir; `oran` 6 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç her katmanın en büyük değerine bakıyor: `nan` içeren bir listede `max` sıraya göre `nan`'i gizleyebiliyor ve `-inf` hiç yakalanmıyor.

```starter
def ilk_bozuk_katman(katmanlar):
    for i, (ad, d) in enumerate(katmanlar):
        if max(d) == float('inf'):
            return {'katman': ad, 'indeks': i, 'tur': 'inf', 'oran': 1.0}
    return None
```

```solution
def ilk_bozuk_katman(katmanlar):
    import math
    if not isinstance(katmanlar, list) or not katmanlar:
        raise ValueError('katmanlar boş olmayan liste olmalı')
    for k in katmanlar:
        if not isinstance(k, (tuple, list)) or len(k) != 2 or not isinstance(k[0], str) or not k[0]:
            raise ValueError('katman (ad, degerler) olmalı')
        if not isinstance(k[1], list) or not k[1] or any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in k[1]):
            raise ValueError('degerler boş olmayan sayı listesi olmalı')
    for i, (ad, d) in enumerate(katmanlar):
        nan_sayisi = sum(1 for x in d if math.isnan(x))
        inf_sayisi = sum(1 for x in d if math.isinf(x))
        if nan_sayisi or inf_sayisi:
            tur = 'ikisi' if nan_sayisi and inf_sayisi else ('nan' if nan_sayisi else 'inf')
            return {'katman': ad, 'indeks': i, 'tur': tur, 'oran': round((nan_sayisi + inf_sayisi) / len(d), 6)}
    return None
```

```test
need('ilk_bozuk_katman')
import math, random

nan, inf = float('nan'), float('inf')
K = [('embed', [0.1, 0.2]), ('attn', [1.0, inf, 3.0, 4.0]), ('mlp', [nan, nan]), ('loss', [nan])]
eq(ilk_bozuk_katman(K), {'katman': 'attn', 'indeks': 1, 'tur': 'inf', 'oran': 0.25}, 'kayıp nan ama ilk bozulan yer attention: inf olarak doğmuş')
eq(ilk_bozuk_katman([('a', [1.0, 2.0]), ('b', [3.0])]), None, 'bozulma yok')
eq(ilk_bozuk_katman([('a', [nan, 5.0, 1.0])])['tur'], 'nan', 'nan listenin başında: max ile gizlenirdi')
eq(ilk_bozuk_katman([('a', [5.0, nan])])['tur'], 'nan', 'nan listenin sonunda')
eq(ilk_bozuk_katman([('a', [1.0, -inf])]), {'katman': 'a', 'indeks': 0, 'tur': 'inf', 'oran': 0.5}, 'eksi sonsuz da inf sayılır')
eq(ilk_bozuk_katman([('a', [nan, inf, 1.0])])['tur'], 'ikisi', 'aynı katmanda ikisi birden')
eq(ilk_bozuk_katman([('a', [1e308, -1e308])]), None, 'çok büyük ama sonlu değer bozulma değildir')
rng = random.Random(3901)
for _ in range(25):
    kat = []
    for i in range(rng.randint(1, 8)):
        d = [round(rng.uniform(-5, 5), 2) for _ in range(rng.randint(1, 6))]
        if rng.random() < 0.25:
            d[rng.randrange(len(d))] = rng.choice([nan, inf, -inf])
        kat.append((f"k{i}", d))
    r = ilk_bozuk_katman(kat)
    ilk = next((i for i, (_, d) in enumerate(kat) if any(x != x or x in (inf, -inf) for x in d)), None)
    if ilk is None:
        eq(r, None, 'rastgele katmanlarda bozulma yok')
    else:
        d = kat[ilk][1]
        eq((r['indeks'], r['katman']), (ilk, kat[ilk][0]), 'rastgele katmanlarda ilk bozuk')
        yakin(r['oran'], sum(1 for x in d if x != x or x in (inf, -inf)) / len(d), 'bozuk oranı', tol=1e-6)
eq(ilk_bozuk_katman([('a', [nan, 1.0, 2.0])])['oran'], 0.333333, 'oran 6 basamağa yuvarlanır')
for kotu in (None, [], ['kotu'], [123], [('a',)], [('', [1.0])], [(1, [1.0])], [('a', [])], [('a', [1, "2"])], [('a', [True])], [('a', (1.0,))], (('a', [1.0]),)):
    raises(ValueError, ilk_bozuk_katman, kotu, msg='bozuk girdi reddedilir')
```

```hint
Her katmanda `math.isnan` ve `math.isinf` ile ayrı ayrı say. İlk sıfırdan farklı sayım gördüğün katmanda dur.
```
:::

::: gorev 2 · Kararlı log-sum-exp
`logsumexp(x)` işlevini yaz.

- `x`: boş olmayan, **sonlu** sayılardan oluşan liste.
- Dönüş: $\log \sum_i e^{x_i}$, `float`; 9 basamağa yuvarlanmış. Hesap `m + log(Σ exp(x_i − m))` biçiminde yapılır.
- Çok büyük (`1000`) ve çok küçük (`-1000`) girdilerde de sonlu ve doğru sonuç vermelidir.
- Bozuk ya da sonlu olmayan girdi `ValueError`.

KUSURLU başlangıç tanımı doğrudan yazıyor: büyük girdide `exp` taşıyor, küçük girdide toplam sıfıra inip `log(0)` hatası veriyor.

```starter
def logsumexp(x):
    import math
    return round(math.log(sum(math.exp(v) for v in x)), 9)
```

```solution
def logsumexp(x):
    import math
    if not isinstance(x, list) or not x or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in x):
        raise ValueError('x sonlu sayılardan oluşan boş olmayan liste olmalı')
    m = max(x)
    return round(m + math.log(sum(math.exp(v - m) for v in x)), 9)
```

```test
need('logsumexp')
import math, random

yakin(logsumexp([0.0, 0.0]), math.log(2), 'iki eşit terim: log 2', tol=1e-9)
yakin(logsumexp([1000.0, 1000.0]), 1000 + math.log(2), 'büyük girdi taşmaz', tol=1e-9)
yakin(logsumexp([-1000.0, -1000.0]), -1000 + math.log(2), 'küçük girdi sıfıra inmez', tol=1e-9)
yakin(logsumexp([1000.0, -1000.0]), 1000.0, 'baskın terim: sonuç en büyüğe çok yakın', tol=1e-9)
eq(logsumexp([5.0]), 5.0, 'tek terim: kendisi')
yakin(logsumexp([math.log(0.2), math.log(0.3), math.log(0.5)]), 0.0, 'olasılıkların logaritmaları: toplam 1, log u 0', tol=1e-9)
ok(isinstance(logsumexp([1, 2]), float), 'dönüş float')
rng = random.Random(3902)
for _ in range(25):
    x = [round(rng.uniform(-20, 20), 3) for _ in range(rng.randint(1, 10))]
    yakin(logsumexp(x), math.log(math.fsum(math.exp(v) for v in x)), 'orta büyüklükte girdide doğrudan tanımla aynı', tol=1e-8)
    ok(max(x) <= logsumexp(x) <= max(x) + math.log(len(x)) + 1e-9, 'max ile max + log n arasında')
    kaymis = logsumexp([v + 700 for v in x])
    yakin(kaymis - 700, logsumexp(x), 'bütün girdilere sabit eklemek sonucu aynı sabit kadar kaydırır', tol=1e-7)
x = [1.0, 2.0]
logsumexp(x)
eq(x, [1.0, 2.0], 'girdi değişmez')
for kotu in (None, [], [1, "2"], [True], (1.0, 2.0), [float('nan')], [1.0, float('inf')], [float('-inf')]):
    raises(ValueError, logsumexp, kotu, msg='bozuk ya da sonlu olmayan girdi reddedilir')
```

```hint
`m = max(x)`; sonuç `m + log(Σ exp(v − m))`. En büyük terim `exp(0) = 1` olur, bu yüzden ne taşar ne sıfıra iner.
```
:::

::: gorev 3 · Bozulma nerelere yayıldı?
`nan_yayilimi(graf, kaynaklar, durduranlar)` işlevini yaz.

- `graf`: boş olmayan `{düğüm: [girdi düğümleri]}` sözlüğü; adlar `str`. Her girdi `graf`'ın bir anahtarı olmalıdır. Girdisi olmayan düğüm (`[]`) bir yapraktır.
- `kaynaklar`: `nan` **üreten** düğümlerin listesi; `durduranlar`: girdisi `nan` olsa bile temiz çıktı veren düğümlerin listesi (`nan_to_num` gibi). İkisi de `graf`'ın anahtarlarından oluşur ve yinelenmez.
- Bir düğüm bozuktur, eğer kaynaksa; **ya da** durduran değilse ve girdilerinden en az biri bozuksa. Bir düğüm hem kaynak hem durduransa kaynak sayılır (kendi ürettiğini durduramaz).
- Graf döngü içeriyorsa `ValueError`.
- Dönüş: `{'bozuk': alfabetik sıralı liste, 'temiz': alfabetik sıralı liste}`.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç yalnız kaynağın **doğrudan** tüketicilerini işaretliyor: iki adım ötedeki kayıp temiz görünüyor.

```starter
def nan_yayilimi(graf, kaynaklar, durduranlar):
    bozuk = set(kaynaklar)
    for d, girdiler in graf.items():
        if any(g in kaynaklar for g in girdiler):
            bozuk.add(d)
    return {'bozuk': sorted(bozuk), 'temiz': sorted(set(graf) - bozuk)}
```

```solution
def nan_yayilimi(graf, kaynaklar, durduranlar):
    if not isinstance(graf, dict) or not graf:
        raise ValueError('graf boş olmayan dict olmalı')
    for d, girdiler in graf.items():
        if not isinstance(d, str) or not isinstance(girdiler, list) or any(g not in graf for g in girdiler):
            raise ValueError('düğüm str, girdiler graf içindeki düğümlerin listesi olmalı')
    for liste in (kaynaklar, durduranlar):
        if not isinstance(liste, list) or len(set(liste)) != len(liste) or any(x not in graf for x in liste):
            raise ValueError('kaynaklar ve durduranlar graf düğümlerinden oluşan yinelenmeyen liste olmalı')
    kaynak, durduran = set(kaynaklar), set(durduranlar)
    durum = {}

    def bozuk_mu(d, yol):
        if d in durum:
            return durum[d]
        if d in yol:
            raise ValueError('graf döngü içeriyor')
        yol.add(d)
        girdi_bozuk = False
        for g in graf[d]:
            if bozuk_mu(g, yol):
                girdi_bozuk = True
        yol.discard(d)
        durum[d] = d in kaynak or (d not in durduran and girdi_bozuk)
        return durum[d]

    for d in graf:
        bozuk_mu(d, set())
    return {'bozuk': sorted(d for d in graf if durum[d]), 'temiz': sorted(d for d in graf if not durum[d])}
```

```test
need('nan_yayilimi')
import random

G = {'x': [], 'w': [], 'logit': ['x', 'w'], 'olasilik': ['logit'], 'log': ['olasilik'], 'kayip': ['log'], 'metrik': ['logit']}
r = nan_yayilimi(G, ['log'], [])
eq(r['bozuk'], ['kayip', 'log'], 'log ta doğan nan yalnız aşağı akışa yayılır')
eq(r['temiz'], ['logit', 'metrik', 'olasilik', 'w', 'x'], 'yukarı akış ve yan dal temiz')
r = nan_yayilimi(G, ['logit'], [])
eq(r['bozuk'], ['kayip', 'log', 'logit', 'metrik', 'olasilik'], 'erken doğan nan her yere ulaşır (doğrudan tüketiciyle sınırlı değil)')
r = nan_yayilimi(G, ['logit'], ['olasilik'])
eq(r['bozuk'], ['logit', 'metrik'], 'durduran düğüm aşağı akışı kurtarır ama yan dalı kurtarmaz')
eq(nan_yayilimi(G, [], [])['bozuk'], [], 'kaynak yoksa hiçbir şey bozulmaz')
eq(nan_yayilimi(G, ['log'], ['log'])['bozuk'], ['kayip', 'log'], 'hem kaynak hem durduran: kaynak sayılır')
eq(nan_yayilimi({'a': [], 'b': ['a', 'a']}, ['a'], []), {'bozuk': ['a', 'b'], 'temiz': []}, 'aynı girdi iki kez')
raises(ValueError, nan_yayilimi, {'a': ['b'], 'b': ['a']}, [], [], msg='döngü reddedilir')
raises(ValueError, nan_yayilimi, {'a': ['a']}, [], [], msg='kendine bağlı düğüm reddedilir')
rng = random.Random(3903)
for _ in range(20):
    n = rng.randint(1, 10)
    ad = [f"d{i:02d}" for i in range(n)]
    g = {ad[i]: sorted(rng.sample(ad[:i], rng.randint(0, min(i, 3)))) for i in range(n)}
    kay = rng.sample(ad, rng.randint(0, min(n, 2)))
    dur = rng.sample(ad, rng.randint(0, min(n, 2)))
    boz = set()
    for d in ad:
        if d in kay or (d not in dur and any(x in boz for x in g[d])):
            boz.add(d)
    r = nan_yayilimi(g, kay, dur)
    eq(r['bozuk'], sorted(boz), 'rastgele grafta topolojik sırayla hesaplanan referansla aynı')
    eq(sorted(r['bozuk'] + r['temiz']), ad, 'her düğüm tam bir kümede')
    karisik = dict(reversed(list(g.items())))
    eq(nan_yayilimi(karisik, kay, dur)['bozuk'], r['bozuk'], 'sözlük sırası sonucu değiştirmez')
g_elmas = {'s0': []}
for _i in range(20):
    g_elmas[f'a{_i}'] = [f's{_i}']
    g_elmas[f'b{_i}'] = [f's{_i}']
    g_elmas[f's{_i + 1}'] = [f'a{_i}', f'b{_i}']
eq('s20' in nan_yayilimi(g_elmas, ['s0'], [])['bozuk'], True, '20 katmanlı elmas DAG memoization ile doğrusal zamanda çözülür')
iyi = {'a': []}
for a in ([None, [], []], [123, [], []], [{}, [], []], [{'a': ['yok']}, [], []], [{'a': 'b'}, [], []], [{'a': ('a',)}, [], []], [{1: []}, [], []], [iyi, None, []], [iyi, ['yok'], []], [iyi, ['a', 'a'], []], [iyi, [], ['yok']], [iyi, [], ['a', 'a']], [iyi, [], None], [iyi, ('a',), []], [iyi, [], ('a',)]):
    raises(ValueError, nan_yayilimi, *a, msg='bozuk girdi reddedilir')
```

```hint
Her düğümün durumunu özyinelemeyle hesapla ve sakla (`memoization`): düğüm bozuksa ya kaynaktır ya da durduran değildir ve bir girdisi bozuktur. O an ziyaret edilen yolu bir kümede tutarak döngüyü yakala.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur; her adım bu derste hesapladığın bir sayıya ya da örneğe dayanır.

1. **Çerçeve (15 sn).** "Kayıp NaN yazıyor. Kayba bakmak işe yaramaz; orası zincirin sonu."
2. **Bulaşıcı (30 sn).** "NaN kendisine bile eşit değildir ve dokunduğu her sayıyı NaN yapar. Bir adım sonra bütün model NaN'dir."
3. **Doğum yeri (30 sn).** "Çoğu NaN önce sonsuz olarak doğar: taşan bir üstel, sıfırın logaritması. İlk bozulan katmanı sırayla tararız."
4. **Çare (25 sn).** "Hesabı yeniden yazarız: en büyük terimi dışarı alınca ne taşma olur ne sıfıra inme."
5. **Kapanış (20 sn).** "Kayan nokta sayısı gerçek sayı değildir; sınırlarını bilmeyen model eğitemez."
:::

::: anlat Sınır
Bu ders `nan` ve `inf` değerlerinin nerede doğduğunu ve nasıl yayıldığını anlatır. Görevlerdeki katman çıktıları ve graflar sentetiktir; canlı bir model taranmaz. Görev 1 yalnız **ileri** geçişi tarar; bozulma geri geçişte doğabilir (ileri değerler sonluyken gradient `inf` olur, örneğin sıfırdaki `sqrt`'un türevi) ve o zaman `autograd` anomali tespiti gerekir. Bozulma her adımda değil, belirli bir batch'te ya da belirli bir adımdan sonra çıkabilir; yeniden üretmek için tohumun, veri sırasının ve o adımdaki ağırlıkların kaydedilmiş olması gerekir. Görev 3'teki yayılım kuralı basitleştirilmiştir: gerçekte bazı işlemler `nan`'i girdiye göre yutabilir (`nan`'in sıfırla maskelenmesi beklenenin tersine `nan` verir, ama bir karşılaştırma `False` verir ve `nan` sessizce kaybolur). `where` ileri geçişte bozuk dalı seçmese bile geri geçişte o daldan `nan` gradient gelebilir; bu yaygın bir tuzaktır ve burada modellenmez. `log-sum-exp` hilesi taşmayı önler ama hassasiyet kaybını (`catastrophic cancellation`) her durumda gidermez. Karışık hassasiyette eşikler çok daha düşüktür: `fp16`'da 65.504'ün üstü `inf`'tir.

Kaynaklar: [Goldberg 1991 - What Every Computer Scientist Should Know About Floating-Point Arithmetic](https://doi.org/10.1145/103162.103163), [PyTorch autograd anomaly detection belgesi](https://pytorch.org/docs/stable/autograd.html#anomaly-detection), [PyTorch torch.logsumexp belgesi](https://pytorch.org/docs/stable/generated/torch.logsumexp.html), [Goodfellow, Bengio ve Courville 2016 - Deep Learning, Bölüm 4: Numerical Computation](https://www.deeplearningbook.org/contents/numerical.html).
:::

::: dusun
Bir eğitim `fp32`'de sorunsuz çalışıyor; `fp16`'ya geçince 300. adımda kayıp `nan` oluyor. Kodda `x / (x.std() + 1e-8)` biçiminde bir normalleştirme var. Bu satır neden şüpheli? İlk giriş tablosundaki işlemlerden hangisi devreye giriyor ve düzeltme için iki farklı yol nedir?
:::

::: ozet
- `nan` bulaşıcıdır; kayıp zincirin sonudur, aranan şey bozulmanın ilk doğduğu katmandır.
- Çoğu `nan` önce `inf` olarak doğar: taşan `exp`, `log(0)`, sıfıra bölme; sonra `inf − inf` ya da `0 · inf` ile `nan`'e döner.
- `nan` kendisine bile eşit değildir; `max` ve `==` ile aranmaz, `isnan` / `isfinite` kullanılır.
- `log-sum-exp` en büyük terim dışarı alınarak yazılır; olasılık hesaplayıp logaritma almak yerine birleşik işlevler kullanılır.
- Bozulma aşağı akışa yayılır; hangi düğümlerin etkilendiği hesap grafından çıkarılır ve yalnız birkaç işlem onu durdurur.
:::
