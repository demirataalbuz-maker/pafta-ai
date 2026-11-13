---
id: ai-temel-39
title: "Halüsinasyon Neden Olur ve Neden Tümüyle Bitmez? · Good-Turing, Puanlama Kuralı ve Self-Consistency"
summary: Halüsinasyonun üç kaynağını ölç: eğitimde bir kez görülen olgular, tahmini ödüllendiren puanlama ve örnekleme tutarsızlığı; çekimserliğin ne zaman kazandırdığını hesapla ve iki dakikada anlat.
---

::: anlat 1. Soru: "Neden uyduruyor ve bu neden düzeltilemiyor?"
`Hallucination`, modelin akıcı ve kendinden emin biçimde **yanlış** bir şey üretmesidir: var olmayan bir makale, yanlış bir doğum tarihi, hiç yazılmamış bir fonksiyon. Salonda bu soru genellikle şöyle gelir: *"Madem bu kadar gelişti, neden hâlâ uyduruyor?"*

Kısa cevap: halüsinasyon bir yazılım hatası değil, üretken bir modelin **istatistiksel sonucudur**. Üç ayrı kaynağı vardır ve her birini bu derste ölçeceksin:

| Kaynak | Açıklama | Görev |
|---|---|---|
| Seyrek olgular | Eğitimde bir kez geçen bir olgu ile hiç geçmemiş makul bir uydurma, model için ayırt edilemez | 1 |
| Tahmini ödüllendiren puanlama | "Bilmiyorum" 0 puan, yanlış cevap da 0 puan ise tahmin etmek her zaman kazandırır | 2 |
| Örnekleme | Aynı soruya her seferinde farklı cevap gelebilir; tutarsızlık bir uyarı işaretidir | 3 |

> [!NOT]
> Görevlerdeki veriler sentetiktir: uydurma olgu listeleri ve elle yazılmış güven değerleri. Gerçek bir modelin halüsinasyon oranını ölçmezler; o oranı ölçmekte kullanılan hesapları öğretirler.
:::

::: anlat 2. Kaynak 1: bir kez görülen olgu
Model eğitimde "Ankara Türkiye'nin başkentidir" cümlesini binlerce kez görür; bu olgu sağlam öğrenilir. Ama az bilinen bir kişinin doğum günü tek bir sayfada bir kez geçer. Model için bu tek gözlem, hiç geçmemiş ama **kulağa makul gelen** başka bir tarihten istatistiksel olarak ayırt edilemez.

Bunu ölçmenin eski ve sağlam bir yolu vardır. Alan Turing ve I. J. Good, savaş sırasında şifre çözerken şu soruyu sordu: "Şimdiye kadar hiç görmediğim bir şeyle karşılaşma olasılığım ne?" Cevap (`Good-Turing estimate`):

$$P(\text{görülmemiş}) \approx \frac{N_1}{N}$$

Burada $N$ toplam gözlem sayısı, $N_1$ ise **tam bir kez** görülen farklı öğelerin sayısıdır. Bir kez görülenler çoksa, görmediklerin de çoktur.

Kalai ve Vempala (2024) bunu dil modellerine uyguladı: iyi kalibre edilmiş bir model, eğitim verisinde bir kez geçen türden olgularda yaklaşık bu oranda halüsinasyon üretmek **zorundadır**. Bu, mimariden ya da veri kalitesinden bağımsız bir alt sınırdır. "Daha fazla veri" bu oranı düşürür ama sıfırlamaz, çünkü dünyada her zaman bir kez yazılmış olgular olacaktır.

> [!NOT]
> Alt sınır "keyfî olgular" içindir (doğum günü, tez başlığı gibi bir örüntüsü olmayan bilgiler). Hesaplanabilir ya da kurallı bilgide (aritmetik, dil bilgisi) aynı sınır geçerli değildir.
:::

::: anlat 3. Kaynak 2: tahmini ödüllendiren puanlama
Çoktan seçmeli bir sınavda boş bırakmak 0, yanlış cevap da 0 puansa ne yaparsın? Bilmediğin soruyu sallarsın. Dil modelleri de böyle değerlendirilir: çoğu benchmark yalnız doğruluk oranına bakar, "bilmiyorum" cevabına puan vermez. Kalai ve arkadaşları (2025) bunun modelleri **tahmin etmeye** ittiğini savunur: çekimser kalan model sıralamada geriye düşer.

Hesap basittir. Model cevabının doğru olma olasılığını $p$ sanıyor; doğru cevap $+1$, yanlış cevap $-c$, çekimserlik $0$ puan:

$$\mathbb{E}[\text{puan} \mid \text{cevapla}] = p - c(1 - p)$$

Cevaplamak ancak bu değer pozitifse kazandırır:

$$p > \frac{c}{1 + c}$$

- $c = 0$ (yanlışa ceza yok): eşik $0$. Her zaman tahmin et. **Halüsinasyon ödüllendirilir.**
- $c = 1$: eşik $0.5$.
- $c = 3$: eşik $0.75$. Yalnız emin olduğunda cevapla.

Bu, halüsinasyonun bir kısmının modelin "yeteneksizliği" değil, **neyi ödüllendirdiğimizin** sonucu olduğunu gösterir. Bu bir görüştür ve tartışılır: karşı görüş, puanlamayı değiştirmenin tek başına yetmeyeceğini, çünkü modelin kendi güveninin de güvenilir olmadığını (`calibration`, bkz. `ai-temel-38`) söyler. İkisi de doğrudur; eşik ancak güven kalibre ise işe yarar.
:::

::: tahmin Sallamak mı, susmak mı?
Model bir sorunun cevabından %30 emin. İki farklı puanlama kuralında cevap vermenin beklenen puanı ne yazdırılır?

```python
p = 0.30
for ceza in (0, 1):
    beklenen = p * 1 - (1 - p) * ceza
    karar = "cevapla" if beklenen > 0 else "çekimser kal"
    print(f"ceza={ceza} beklenen={beklenen:+.2f} -> {karar}")
```

???

```cikti
ceza=0 beklenen=+0.30 -> cevapla
ceza=1 beklenen=-0.40 -> çekimser kal
```
Yanlışa ceza yokken %30'luk bir tahmin bile pozitif beklenen puan getirir; model için en iyi strateji sallamaktır. Yanlış cevap 1 puan götürdüğünde aynı tahmin zarar ettirir ve susmak kazandırır. Modelin bilgisi değişmedi; yalnız neyi ödüllendirdiğin değişti.
:::

::: gorev 1 · Görülmemiş kütleyi tahmin et (Good-Turing)
`tekil_orani(gozlemler)` işlevini yaz. Bir derlemde geçen olguların listesini alır ve "henüz görmediğim bir olguyla karşılaşma olasılığı"nı tahmin eder.

- `gozlemler`: boş olmayan `str` listesi (aynı olgu birden çok kez geçebilir).
- Dönüş: `{'toplam': N, 'farkli': K, 'tekil': N1, 'gorulmemis_kutle': N1 / N}`. `tekil`, **tam bir kez** geçen farklı olguların sayısıdır. Oran 6 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç farklı olgu sayısını toplam gözleme bölüyor. Bu, çok tekrarlanan olguları da "nadir" sayar ve görülmemiş kütleyi olduğundan büyük gösterir.

```starter
def tekil_orani(gozlemler):
    farkli = len(set(gozlemler))
    return {'toplam': len(gozlemler), 'farkli': farkli, 'tekil': farkli, 'gorulmemis_kutle': round(farkli / len(gozlemler), 6)}
```

```solution
def tekil_orani(gozlemler):
    if not isinstance(gozlemler, list) or not gozlemler or any(not isinstance(g, str) for g in gozlemler):
        raise ValueError('gozlemler boş olmayan str listesi olmalı')
    say = {}
    for g in gozlemler:
        say[g] = say.get(g, 0) + 1
    tekil = sum(1 for n in say.values() if n == 1)
    return {'toplam': len(gozlemler), 'farkli': len(say), 'tekil': tekil, 'gorulmemis_kutle': round(tekil / len(gozlemler), 6)}
```

```test
need('tekil_orani')
import random

def _ref(g):
    adet = {}
    for x in g:
        adet[x] = adet.get(x, 0) + 1
    n1 = len([k for k in adet if adet[k] == 1])
    return {'toplam': len(g), 'farkli': len(adet), 'tekil': n1, 'gorulmemis_kutle': round(n1 / len(g), 6)}

eq(tekil_orani(["ankara", "ankara", "ankara", "dogum-1", "dogum-2"]), {'toplam': 5, 'farkli': 3, 'tekil': 2, 'gorulmemis_kutle': 0.4}, 'iki tekil olgu, beş gözlem')
eq(tekil_orani(["a", "a", "b", "b"]), {'toplam': 4, 'farkli': 2, 'tekil': 0, 'gorulmemis_kutle': 0.0}, 'her olgu tekrar ediyorsa görülmemiş kütle 0')
eq(tekil_orani(["x"]), {'toplam': 1, 'farkli': 1, 'tekil': 1, 'gorulmemis_kutle': 1.0}, 'tek gözlem')
eq(tekil_orani(["a", "b", "c"])['gorulmemis_kutle'], 1.0, 'hepsi tekil')
rng = random.Random(3901)
for _ in range(25):
    havuz = [f"olgu-{i}" for i in range(rng.randint(1, 15))]
    g = [rng.choice(havuz) for _ in range(rng.randint(1, 40))]
    eq(tekil_orani(g), _ref(g), 'rastgele derlemde bağımsız referansla aynı')
g = ["a", "b", "a"]
tekil_orani(g)
eq(g, ["a", "b", "a"], 'girdi değişmez')
for kotu in (None, [], "abc", [1, 2], ["a", None], ("a", "b"), {"a"}):
    raises(ValueError, tekil_orani, kotu, msg='bozuk girdi reddedilir')
```

```hint
Önce her olgunun kaç kez geçtiğini say. `tekil`, sayımı tam 1 olanların adedidir; `farkli` ise sözlükteki anahtar sayısı.
```
:::

::: gorev 2 · Seçici cevaplama: eşik ve ceza
`secici_puan(guvenler, dogrular, esik, ceza)` işlevini yaz. Model yalnız güveni eşiğe ulaştığında cevap verir, yoksa çekimser kalır.

- `guvenler`: `[0, 1]` aralığında sayılardan boş olmayan liste. `dogrular`: aynı uzunlukta `bool` listesi (cevap verilseydi doğru olur muydu).
- `esik`: `[0, 1]` aralığında sayı. Güven `>= esik` ise cevaplanır.
- `ceza`: negatif olmayan sayı. Doğru cevap `+1`, yanlış cevap `-ceza`, çekimserlik `0`.
- Dönüş: `{'kapsama': cevaplanan / N, 'uydurma_orani': yanlış / cevaplanan, 'puan': (doğru - ceza · yanlış) / N}`. Hiç cevap verilmediyse `uydurma_orani` `None` olur. Sayılar 6 basamağa yuvarlanır.
- Bozuk girdi `ValueError` (`bool` bir sayı sayılmaz).

KUSURLU başlangıç cezayı yok sayıyor: yanlış cevap hiçbir şey götürmüyor. Bu puanlamada eşiği 0'a çekmek her zaman en iyisidir.

```starter
def secici_puan(guvenler, dogrular, esik, ceza):
    cevap = [d for g, d in zip(guvenler, dogrular) if g >= esik]
    n = len(guvenler)
    return {'kapsama': round(len(cevap) / n, 6), 'uydurma_orani': None, 'puan': round(sum(cevap) / n, 6)}
```

```solution
def secici_puan(guvenler, dogrular, esik, ceza):
    import math
    def sayi(x):
        return not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x)
    if not isinstance(guvenler, list) or not isinstance(dogrular, list) or not guvenler or len(guvenler) != len(dogrular):
        raise ValueError('listeler boş olmamalı ve aynı uzunlukta olmalı')
    if any(not sayi(g) or not 0 <= g <= 1 for g in guvenler):
        raise ValueError('güven [0, 1] aralığında sayı olmalı')
    if any(not isinstance(d, bool) for d in dogrular):
        raise ValueError('dogrular bool olmalı')
    if not sayi(esik) or not 0 <= esik <= 1:
        raise ValueError('esik [0, 1] aralığında sayı olmalı')
    if not sayi(ceza) or ceza < 0:
        raise ValueError('ceza negatif olmayan sayı olmalı')
    n = len(guvenler)
    cevap = [d for g, d in zip(guvenler, dogrular) if g >= esik]
    dogru = sum(1 for d in cevap if d)
    yanlis = len(cevap) - dogru
    return {
        'kapsama': round(len(cevap) / n, 6),
        'uydurma_orani': round(yanlis / len(cevap), 6) if cevap else None,
        'puan': round((dogru - ceza * yanlis) / n, 6),
    }
```

```test
need('secici_puan')
import random

def _ref(gs, ds, e, c):
    n = len(gs)
    d = y = 0
    for i in range(n):
        if gs[i] >= e:
            if ds[i]:
                d += 1
            else:
                y += 1
    return {'kapsama': round((d + y) / n, 6), 'uydurma_orani': None if d + y == 0 else round(y / (d + y), 6), 'puan': round((d - c * y) / n, 6)}

gs = [0.9, 0.8, 0.6, 0.3, 0.2]
ds = [True, True, False, True, False]
eq(secici_puan(gs, ds, 0.0, 0), {'kapsama': 1.0, 'uydurma_orani': 0.4, 'puan': 0.6}, 'ceza yokken hepsini cevaplamak')
eq(secici_puan(gs, ds, 0.0, 1), {'kapsama': 1.0, 'uydurma_orani': 0.4, 'puan': 0.2}, 'ceza 1: iki yanlış iki puan götürür')
eq(secici_puan(gs, ds, 0.7, 1), {'kapsama': 0.4, 'uydurma_orani': 0.0, 'puan': 0.4}, 'eşik 0.7: az cevap, sıfır uydurma, daha yüksek puan')
eq(secici_puan(gs, ds, 1.0, 3), {'kapsama': 0.0, 'uydurma_orani': None, 'puan': 0.0}, 'hiç cevap yoksa uydurma oranı tanımsız')
eq(secici_puan([0.5], [False], 0.5, 2.5), {'kapsama': 1.0, 'uydurma_orani': 1.0, 'puan': -2.5}, 'eşik dahil; kesirli ceza')
ok(secici_puan(gs, ds, 0.0, 0)['puan'] > secici_puan(gs, ds, 0.7, 0)['puan'], 'ceza yokken tahmin etmek kazandırır')
ok(secici_puan(gs, ds, 0.7, 1)['puan'] > secici_puan(gs, ds, 0.0, 1)['puan'], 'ceza varken çekimserlik kazandırır')
rng = random.Random(3902)
for _ in range(30):
    n = rng.randint(1, 25)
    g = [round(rng.random(), 2) for _ in range(n)]
    d = [rng.random() < x for x in g]
    e = round(rng.random(), 2)
    c = rng.choice([0, 0.5, 1, 2, 3])
    eq(secici_puan(g, d, e, c), _ref(g, d, e, c), 'rastgele veride bağımsız referansla aynı')
for a in ([[], [], 0.5, 1], [[0.5], (True,), 0.5, 1], [[0.5], [True, True], 0.5, 1], [[1.5], [True], 0.5, 1], [[-0.1], [True], 0.5, 1], [[float('nan')], [True], 0.5, 1], [[True], [True], 0.5, 1], [[0.5], [1], 0.5, 1], [[0.5], [True], 1.5, 1], [[0.5], [True], -0.1, 1], [[0.5], [True], float('nan'), 1], [[0.5], [True], True, 1], [[0.5], [True], 0.5, -1], [[0.5], [True], 0.5, True], [[0.5], [True], 0.5, float('nan')], [[0.5], [True], 0.5, float('inf')], [[0.5], [True], 0.5, None], [(0.5,), [True], 0.5, 1]):
    raises(ValueError, secici_puan, *a, msg='bozuk girdi reddedilir')
```

```hint
Önce cevaplananları ayır (`g >= esik`). Doğru ve yanlış sayılarını ayrı tut. Puan `(doğru − ceza · yanlış) / N`; payda cevaplanan değil, **bütün** sorulardır.
```
:::

::: gorev 3 · Self-consistency: aynı soruyu birkaç kez sor
Model bir olguyu gerçekten biliyorsa, aynı soruya tekrar tekrar aynı cevabı verme eğilimindedir. Uyduruyorsa cevaplar dağılır. `oz_tutarlilik(ornekler)` işlevi, aynı soruya alınan cevapların ne kadar uzlaştığını ölçer.

- `ornekler`: boş olmayan `str` listesi (aynı soruya alınan cevaplar).
- Karşılaştırmadan önce her cevabı normalleştir: baştaki ve sondaki boşlukları at, ardışık boşlukları teke indir, `casefold()` uygula.
- Dönüş: `{'cevap': en sık normalleştirilmiş cevap, 'oran': o cevabın payı, 'farkli': farklı cevap sayısı}`. Eşitlikte alfabetik olarak önce gelen seçilir. Oran 4 basamağa yuvarlanır.
- Normalleştirme sonrası boş kalan cevap ve bozuk girdi `ValueError`.

KUSURLU başlangıç normalleştirme yapmıyor: `"1923"` ile `" 1923 "` farklı cevap sayılıyor ve tutarlı bir model tutarsız görünüyor.

```starter
def oz_tutarlilik(ornekler):
    en_sik = max(set(ornekler), key=ornekler.count)
    return {'cevap': en_sik, 'oran': round(ornekler.count(en_sik) / len(ornekler), 4), 'farkli': len(set(ornekler))}
```

```solution
def oz_tutarlilik(ornekler):
    if not isinstance(ornekler, list) or not ornekler or any(not isinstance(o, str) for o in ornekler):
        raise ValueError('ornekler boş olmayan str listesi olmalı')
    say = {}
    for o in ornekler:
        n = " ".join(o.split()).casefold()
        if not n:
            raise ValueError('boş cevap')
        say[n] = say.get(n, 0) + 1
    cevap = sorted(say, key=lambda k: (-say[k], k))[0]
    return {'cevap': cevap, 'oran': round(say[cevap] / len(ornekler), 4), 'farkli': len(say)}
```

```test
need('oz_tutarlilik')
import random

def _ref(orn):
    adet = {}
    for o in orn:
        k = " ".join(o.strip().split()).casefold()
        adet[k] = adet.get(k, 0) + 1
    en = min(adet, key=lambda k: (-adet[k], k))
    return {'cevap': en, 'oran': round(adet[en] / len(orn), 4), 'farkli': len(adet)}

eq(oz_tutarlilik(["1923", " 1923 ", "1923", "1920"]), {'cevap': '1923', 'oran': 0.75, 'farkli': 2}, 'boşluk farkı aynı cevaptır')
eq(oz_tutarlilik(["Ankara", "ANKARA", "ankara"]), {'cevap': 'ankara', 'oran': 1.0, 'farkli': 1}, 'büyük-küçük harf farkı aynı cevaptır')
eq(oz_tutarlilik(["Kemal  Sunal", "kemal sunal"]), {'cevap': 'kemal sunal', 'oran': 1.0, 'farkli': 1}, 'ardışık boşluk teke iner')
eq(oz_tutarlilik(["b", "a"]), {'cevap': 'a', 'oran': 0.5, 'farkli': 2}, 'eşitlikte alfabetik')
eq(oz_tutarlilik(["1987", "1991", "1979", "2001"])['oran'], 0.25, 'dağılan cevaplar: uydurma işareti')
rng = random.Random(3903)
for _ in range(25):
    havuz = ["Mavi", "mavi ", " KIRMIZI", "kırmızı", "yeşil", "Sarı  renk", "sarı renk"]
    orn = [rng.choice(havuz) for _ in range(rng.randint(1, 20))]
    eq(oz_tutarlilik(orn), _ref(orn), 'rastgele örneklerde bağımsız referansla aynı')
o = [" A ", "a"]
oz_tutarlilik(o)
eq(o, [" A ", "a"], 'girdi değişmez')
for kotu in (None, [], "abc", [1], ["a", None], ("a",), ["  "], ["a", ""]):
    raises(ValueError, oz_tutarlilik, kotu, msg='bozuk ya da boş cevap reddedilir')
```

```hint
Normalleştirme: `" ".join(o.split()).casefold()`. Sayımı normalleştirilmiş anahtarla yap; en sık olanı `(-sayım, anahtar)` sırasıyla seç.
```
:::

::: anlat 4. Neden tümüyle bitmez ve ne azaltır?
Üç kaynağın her biri için bir önlem vardır; hiçbiri sıfıra indirmez.

| Önlem | Neyi azaltır | Neden yetmez |
|---|---|---|
| `Retrieval` (RAG): cevabı bir belgeye dayandırmak | Seyrek olgulardaki uydurmayı | Yanlış belge gelebilir; model belgeyi yanlış okuyabilir; belgede olmayanı yine uydurabilir |
| Çekimserliği ödüllendirmek (Görev 2) | Tahmin ederek cevaplamayı | Modelin güveni kalibre değilse eşik yanlış soruları eler |
| `Self-consistency` (Görev 3) | Tutarsız uydurmaları yakalar | Model **tutarlı biçimde** yanlış olabilir (eğitim verisindeki yaygın bir hata) |
| Kaynak gösterme zorunluluğu | Doğrulanabilirliği artırır | Model var olmayan kaynak da uydurabilir; kaynak ayrıca doğrulanmalıdır |

Temel neden değişmez: model **üretir**, aramaz. Her soruya akıcı bir cevap üretebilmesi ile bazı cevapların yanlış olması aynı mekanizmanın iki yüzüdür. Hiç uydurmayan bir model, emin olmadığı her soruda susan bir modeldir; bu da kullanışlılığı düşürür. Halüsinasyon oranı ile kapsama arasındaki bu ödünleşimi Görev 2'de sayılarla gördün.

Güvenlik açısından sonuç: model çıktısı **doğrulanmamış bir iddiadır**. Uydurulmuş bir paket adı (`slopsquatting`), var olmayan bir API ya da yanlış bir CVE numarası, onu doğrulamadan kullanan bir sistemde gerçek bir açığa dönüşür.
:::

::: anlat 5. Yaygın yanlışlar ve iki dakikalık anlatım
| Yanlış | Doğrusu |
|---|---|
| "Halüsinasyon bir bug, bir sonraki sürümde düzelir." | Üretken modelin istatistiksel sonucudur; oran düşer, sıfırlanmaz. |
| "Model yalan söylüyor." | Yalan, doğruyu bilip başka söylemektir. Model çoğu durumda doğruyu ayırt edemez. |
| "Temperature 0 yaparsam uydurmaz." | Örneklemeyi sabitler; en olası token yanlışsa her seferinde aynı yanlışı üretir. |
| "RAG kullanınca biter." | Azalır. Getirilen belge yanlış, eksik ya da zehirlenmiş olabilir. |
| "Kaynak gösterdiyse doğrudur." | Kaynak da uydurulabilir; bağlantıyı açıp okumadan doğrulanmış sayılmaz. |

**İki dakikada anlatım iskeleti:**

1. **Çerçeve (15 sn).** "Model bir arama motoru değil. Cevabı bulmuyor, üretiyor."
2. **Sınav benzetmesi (30 sn).** "Boş bırakmak 0, yanlış da 0 ise bilmediğin soruyu sallarsın. Modelleri de böyle puanlıyoruz." Tahmin adımındaki iki satırı söyle: ceza 0 iken +0.30, ceza 1 iken −0.40.
3. **Bir kez görülen olgu (30 sn).** "İnternette bir kez yazılmış bir doğum günü ile hiç yazılmamış ama makul bir tarih, model için aynıdır." Good-Turing: bir kez görülenler çoksa görülmeyenler de çoktur.
4. **Ne yapıyoruz (30 sn).** Belgeye dayandırma, çekimserliği ödüllendirme, aynı soruyu birkaç kez sorma. Hiçbiri sıfırlamıyor.
5. **Kapanış (15 sn).** "Model çıktısı bir iddiadır. Önemli bir karardan önce doğrula."
:::

::: anlat Sınır
Bu ders halüsinasyonun üç istatistiksel kaynağını ve üç ölçüyü anlatır. Görevler sentetik listeler üzerinde çalışır; gerçek bir modelin halüsinasyon oranını ölçmez. Good-Turing tahmini bağımsız örnekleme varsayar ve gerçek metin derlemlerinde yalnız yaklaşık geçerlidir. Kalai ve Vempala'nın alt sınırı kalibre modeller ve keyfî olgular içindir; kurallı ya da hesaplanabilir bilgiye uygulanmaz. Puanlama kuralının halüsinasyonu "ödüllendirdiği" savı bir görüştür ve tek neden olduğu iddia edilmez. Görev 3'teki `self-consistency` yalnız metin eşleşmesine bakar: aynı anlamı farklı kelimelerle söyleyen cevapları ayrı sayar. Farquhar ve arkadaşlarının `semantic entropy` yöntemi bu sınırı anlam kümeleriyle aşar ve bu derste uygulanmaz. Tutarlı biçimde yanlış olan cevaplar bu ölçüyle yakalanmaz.

Kaynaklar: [Kalai ve Vempala 2024 - Calibrated Language Models Must Hallucinate](https://arxiv.org/abs/2311.14648), [Kalai vd. 2025 - Why Language Models Hallucinate](https://arxiv.org/abs/2509.04664), [Manakul vd. 2023 - SelfCheckGPT](https://arxiv.org/abs/2303.08896), [Farquhar vd. 2024 - Detecting hallucinations using semantic entropy](https://doi.org/10.1038/s41586-024-07421-0), [Good 1953 - The population frequencies of species](https://doi.org/10.1093/biomet/40.3-4.237).
:::

::: dusun
Bir şirket, müşteri hizmetleri botunun "bilmiyorum" demesini istemiyor çünkü müşteri memnuniyeti düşüyor. Görev 2'deki sayıları kullanarak yöneticiye şunu açıkla: eşiği 0'a çekmek kapsamayı nasıl, uydurma oranını nasıl değiştirir? Yanlış bir cevabın şirkete maliyeti hangi `ceza` değerine karşılık gelir ve bu değer en iyi eşiği nereye taşır?
:::

::: ozet
- Halüsinasyon bir yazılım hatası değil, üretken modelin istatistiksel sonucudur: model cevabı aramaz, üretir.
- Eğitimde bir kez görülen olgu, makul bir uydurmadan ayırt edilemez. Good-Turing tahmini `N1 / N` bu görülmemiş kütleyi verir ve kalibre modeller için bir alt sınırdır.
- Yanlışa ceza vermeyen puanlama tahmini ödüllendirir. Cevaplamak ancak `p > c / (1 + c)` iken kazandırır.
- `Self-consistency` tutarsız uydurmaları yakalar; tutarlı biçimde yanlış olanı yakalamaz.
- RAG, çekimserlik ve tutarlılık denetimi oranı düşürür, sıfırlamaz. Model çıktısı doğrulanmamış bir iddiadır.
:::
