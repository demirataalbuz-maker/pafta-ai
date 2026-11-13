---
id: ai-matematik-10
title: "Entropi, Çapraz Entropi ve KL · Bir Modelin Kaybı Neyi Ölçer?"
summary: Entropiyi, cross-entropy'yi ve KL divergence'ı kitaplıksız yaz; aralarındaki bağı sayılarla doğrula ve bir dil modelinin kaybından perplexity ile token başına bit değerini çıkar.
---

::: anlat 1. Kayıp fonksiyonu bir bilgi ölçüsüdür
Dil modelleri `cross-entropy` kaybıyla eğitilir, `distillation` bir `KL divergence` küçültür, modeller `perplexity` ile karşılaştırılır. Üçü de aynı fikirden gelir: **bir olay ne kadar şaşırtıcı?**

Olasılığı `p` olan bir olayın **şaşırtıcılığı** (`surprisal`) $-\log p$'dir. Kesin bir olay (`p = 1`) hiç şaşırtmaz; nadir bir olay çok şaşırtır. Logaritma 2 tabanındaysa birim **bit**, doğal logaritmaysa **nat**'tir.

| Ölçü | Formül | Anlamı | Görev |
|---|---|---|---|
| Entropi | $H(p) = -\sum_i p_i \log p_i$ | Dağılımın kendi ortalama şaşırtıcılığı; belirsizliği | 1 |
| Cross-entropy | $H(p, q) = -\sum_i p_i \log q_i$ | Gerçek `p` iken `q`'ya inanmanın ortalama şaşırtıcılığı | 2 |
| KL divergence | $D_{KL}(p \,\|\, q) = \sum_i p_i \log \dfrac{p_i}{q_i}$ | `q`'ya inanmanın **fazladan** bedeli | 2 |
| Perplexity | $\exp(\text{ortalama } {-\ln q})$ | Modelin "kaç seçenek arasında kaldığı" | 3 |
:::

::: anlat 2. Üçünü bağlayan eşitlik
Üç ölçü tek bir eşitlikle bağlıdır:

$$H(p, q) = H(p) + D_{KL}(p \,\|\, q)$$

Cross-entropy iki parçadan oluşur: verinin kendi belirsizliği $H(p)$ (modelin elinde olmayan, indirgenemez kısım) ve modelin yanlış inancının bedeli $D_{KL}$. Eğitimde `p` sabittir; cross-entropy'yi küçültmek ile KL'yi küçültmek **aynı şeydir**. Kayıp hiçbir zaman $H(p)$'nin altına inemez.

KL'nin üç özelliği:

- **Negatif olmaz** ve yalnız `p = q` iken sıfırdır.
- **Simetrik değildir:** $D_{KL}(p \,\|\, q) \ne D_{KL}(q \,\|\, p)$. Bir uzaklık değildir.
- **Sonsuz olabilir:** `p`'nin olası gördüğü bir olaya `q` sıfır olasılık verirse KL sonsuzdur. Model "imkânsız" dediği bir şey gerçekleşince sonsuz şaşırır. Modellerin hiçbir token'a tam sıfır olasılık vermemesinin sebebi budur.

Tanım gereği $0 \log 0 = 0$ alınır: hiç gerçekleşmeyen bir olay ortalamaya katkı yapmaz.

**Dil modelinde.** Her konumda gerçek dağılım `p` tek bir token'a 1 verir (`one-hot`). O zaman cross-entropy yalnız modelin doğru token'a verdiği olasılığın eksi logaritmasıdır: $-\ln q_{\text{doğru}}$. Kayıp, bunun bütün konumlardaki ortalamasıdır. **Perplexity** bu ortalamanın üstelidir: 50.000 token'lık bir sözlükte rastgele tahmin eden modelin perplexity'si 50.000'dir; perplexity'si 20 olan model, her adımda eşit olasılıklı 20 seçenek arasında kalmış gibidir.
:::

::: tahmin Hangi para daha belirsiz?
Adil bir para ile %90 tura gelen bir paranın entropisi (bit olarak) ne yazdırılır?

```python
import math

def entropi(p):
    return -sum(x * math.log2(x) for x in p if x > 0) + 0.0

print(round(entropi([0.5, 0.5]), 4))
print(round(entropi([0.9, 0.1]), 4))
print(round(entropi([1.0, 0.0]), 4))
```

???

```cikti
1.0
0.469
0.0
```
Adil para tam 1 bit belirsizlik taşır: sonucu öğrenmek için bir evet-hayır sorusu gerekir. %90 turalı para 0,469 bittir: sonucu çoğunlukla zaten biliyorsun. Hep tura gelen paranın entropisi sıfırdır. Entropi, dağılım düzgünken en büyük, tek bir sonuca yığılmışken en küçüktür.
:::

::: gorev 1 · Entropi
`entropi(p)` işlevini yaz.

- `p`: boş olmayan liste; negatif olmayan sayılar, toplamı 1 (`1e-9` toleransla). `NaN` ve sonsuz değerler olasılık değildir, reddedilir.
- Dönüş: $-\sum p_i \log_2 p_i$ (bit), 9 basamağa yuvarlanmış. `p_i = 0` olan terimler katkı yapmaz.
- Sonuç `-0.0` çıkmamalıdır; sıfır entropi `0.0` olarak döner.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç sıfır olasılıkta `log2(0)` hesaplamaya çalışıyor ve eksi işaretini unutuyor.

```starter
def entropi(p):
    import math
    return round(sum(x * math.log2(x) for x in p), 9)
```

```solution
def entropi(p):
    import math
    if not isinstance(p, list) or not p or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not 0 <= x <= 1 for x in p):
        raise ValueError('p negatif olmayan sayılardan oluşan boş olmayan liste olmalı')
    if abs(sum(p) - 1) > 1e-9:
        raise ValueError('olasılıklar 1 e toplanmalı')
    h = -sum(x * math.log2(x) for x in p if x > 0)
    return round(h, 9) + 0.0
```

```test
need('entropi')
import math, random

eq(entropi([0.5, 0.5]), 1.0, 'adil para 1 bit')
eq(entropi([0.25] * 4), 2.0, 'dört eşit seçenek 2 bit')
eq(entropi([1.0, 0.0]), 0.0, 'kesin sonuç 0 bit; log 0 hata vermez')
eq(str(entropi([1.0])), '0.0', 'eksi sıfır dönmez')
yakin(entropi([0.9, 0.1]), 0.468995594, 'yüzde 90 turalı para', tol=1e-8)
yakin(entropi([1 / 8] * 8), 3.0, 'sekiz eşit seçenek 3 bit', tol=1e-9)
rng = random.Random(1001)
for _ in range(25):
    n = rng.randint(1, 8)
    w = [rng.randint(0, 9) for _ in range(n)]
    if sum(w) == 0:
        w[0] = 1
    p = [x / sum(w) for x in w]
    h = entropi(p)
    yakin(h, math.fsum(-x * math.log(x) for x in p if x > 0) / math.log(2), 'rastgele dağılımda bağımsız hesapla aynı', tol=1e-8)
    ok(-1e-9 <= h <= math.log2(n) + 1e-9, 'entropi 0 ile log2(n) arasında')
p = [0.5, 0.5]
entropi(p)
eq(p, [0.5, 0.5], 'girdi değişmez')
for kotu in (None, [], [0.5], [0.6, 0.6], [-0.5, 1.5], [1, "0"], [True], (0.5, 0.5), [float('nan')], [float('nan'), 1.0], [float('inf')]):
    raises(ValueError, entropi, kotu, msg='bozuk dağılım reddedilir')
```

```hint
Toplamı yalnız `x > 0` olan terimler üzerinden al ve başına eksi koy. `-0.0`'dan kaçınmak için sonuca `0.0` ekle.
```
:::

::: gorev 2 · Cross-entropy ve KL divergence
`kl_ozeti(p, q)` işlevini yaz.

- `p`, `q`: aynı uzunlukta, boş olmayan iki dağılım (negatif olmayan sayılar, toplamları 1; `NaN` ve sonsuz reddedilir).
- `entropi`: $H(p)$. `capraz_entropi`: $H(p, q) = -\sum p_i \log_2 q_i$. `kl`: $D_{KL}(p \,\|\, q) = \sum p_i \log_2 (p_i / q_i)$. Hepsi bit.
- `p_i = 0` olan terimler katkı yapmaz. `p_i > 0` ve `q_i = 0` olan bir terim varsa `capraz_entropi` ve `kl` `math.inf` olur.
- Dönüş: bu üç anahtar; sonlu değerler 9 basamağa yuvarlanır. `kl` küçük negatif bir kayan nokta hatasıyla çıkarsa `0.0`'a kırpılır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç `p` ile `q`'nun yerini karıştırıyor: $D_{KL}(q \,\|\, p)$ hesaplıyor. KL simetrik olmadığı için sonuç farklıdır.

```starter
def kl_ozeti(p, q):
    import math
    h = -sum(x * math.log2(x) for x in p if x > 0)
    ce = -sum(y * math.log2(x) for x, y in zip(p, q) if y > 0)
    kl = sum(y * math.log2(y / x) for x, y in zip(p, q) if y > 0)
    return {'entropi': round(h, 9), 'capraz_entropi': round(ce, 9), 'kl': round(kl, 9)}
```

```solution
def kl_ozeti(p, q):
    import math
    for d in (p, q):
        if not isinstance(d, list) or not d or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not 0 <= x <= 1 for x in d):
            raise ValueError('dağılım negatif olmayan sayılardan oluşan boş olmayan liste olmalı')
        if abs(sum(d) - 1) > 1e-9:
            raise ValueError('olasılıklar 1 e toplanmalı')
    if len(p) != len(q):
        raise ValueError('dağılımlar aynı uzunlukta olmalı')
    h = -sum(x * math.log2(x) for x in p if x > 0)
    if any(x > 0 and y == 0 for x, y in zip(p, q)):
        return {'entropi': round(h, 9) + 0.0, 'capraz_entropi': math.inf, 'kl': math.inf}
    ce = -sum(x * math.log2(y) for x, y in zip(p, q) if x > 0)
    kl = sum(x * math.log2(x / y) for x, y in zip(p, q) if x > 0)
    return {'entropi': round(h, 9) + 0.0, 'capraz_entropi': round(ce, 9) + 0.0, 'kl': max(0.0, round(kl, 9))}
```

```test
need('kl_ozeti')
import math, random

eq(kl_ozeti([0.5, 0.5], [0.5, 0.5]), {'entropi': 1.0, 'capraz_entropi': 1.0, 'kl': 0.0}, 'p = q iken KL sıfır, cross-entropy entropiye eşit')
r = kl_ozeti([1.0, 0.0], [0.5, 0.5])
eq(r, {'entropi': 0.0, 'capraz_entropi': 1.0, 'kl': 1.0}, 'kesin gerçeğe yarı yarıya inanmak: 1 bit bedel')
r = kl_ozeti([0.5, 0.5], [1.0, 0.0])
eq((r['capraz_entropi'], r['kl']), (math.inf, math.inf), 'modelin imkânsız dediği şey gerçekleşirse sonsuz')
eq(kl_ozeti([1.0, 0.0], [1.0, 0.0])['kl'], 0.0, 'p nin sıfır olduğu yerde q nun sıfır olması sorun değil')
a = kl_ozeti([0.9, 0.1], [0.5, 0.5])['kl']
b = kl_ozeti([0.5, 0.5], [0.9, 0.1])['kl']
yakin(a, 0.531004406, 'KL(p || q)', tol=1e-8)
yakin(b, 0.736965594, 'KL(q || p)', tol=1e-8)
ok(abs(a - b) > 0.1, 'KL simetrik değildir')
rng = random.Random(1002)
for _ in range(25):
    n = rng.randint(1, 7)
    wp = [rng.randint(0, 9) for _ in range(n)]
    wq = [rng.randint(1, 9) for _ in range(n)]
    if sum(wp) == 0:
        wp[0] = 1
    p, q = [x / sum(wp) for x in wp], [x / sum(wq) for x in wq]
    r = kl_ozeti(p, q)
    yakin(r['capraz_entropi'], math.fsum(-x * math.log(y) for x, y in zip(p, q) if x > 0) / math.log(2), 'rastgele dağılımda cross-entropy', tol=1e-8)
    yakin(r['capraz_entropi'], r['entropi'] + r['kl'], 'H(p, q) = H(p) + KL(p || q)', tol=1e-7)
    ok(r['kl'] >= 0.0, 'KL negatif olmaz')
    ok(r['capraz_entropi'] >= r['entropi'] - 1e-8, 'cross-entropy entropinin altına inmez')
p, q = [0.5, 0.5], [0.25, 0.75]
kl_ozeti(p, q)
eq((p, q), ([0.5, 0.5], [0.25, 0.75]), 'girdiler değişmez')
iyi = [0.5, 0.5]
for a, b in [(None, iyi), (iyi, None), ([], []), (iyi, [1.0]), (iyi, [0.6, 0.6]), ([0.6, 0.6], iyi), ([-0.5, 1.5], iyi), (iyi, [1, "0"]), ([True], [1.0]), ((0.5, 0.5), iyi), ([float('nan')], [1.0]), ([1.0], [float('nan')]), ([float('nan'), 1.0], iyi), (iyi, [float('nan'), 1.0])]:
    raises(ValueError, kl_ozeti, a, b, msg='bozuk dağılım reddedilir')
```

```hint
Ağırlık her zaman `p`'dir; logaritmanın içi cross-entropy'de `q`, KL'de `p / q`. Önce sonsuz durumunu ayrı ele al: `p_i > 0` ve `q_i == 0`.
```
:::

::: gorev 3 · Kayıptan perplexity'ye
`perplexity_ozeti(dogru_olasiliklar)` işlevini yaz. Bir dil modelinin her konumda **doğru token'a** verdiği olasılıkları alır.

- `dogru_olasiliklar`: boş olmayan liste; her öğe `(0, 1]` aralığında sayı (sıfır kabul edilmez: kayıp sonsuz olur).
- `kayip`: ortalama $-\ln q$ (nat). `bit_token`: `kayip / ln 2`. `perplexity`: $e^{\text{kayip}}$.
- Dönüş: bu üç anahtar; 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç olasılıkların ortalamasını alıp tersini döndürüyor. Tek bir çok düşük olasılık (modelin tamamen yanıldığı bir konum) ortalamada kaybolur; oysa logaritmik kayıpta ağır cezalandırılır.

```starter
def perplexity_ozeti(dogru_olasiliklar):
    import math
    ort = sum(dogru_olasiliklar) / len(dogru_olasiliklar)
    return {'kayip': round(-math.log(ort), 9), 'bit_token': round(-math.log2(ort), 9), 'perplexity': round(1 / ort, 9)}
```

```solution
def perplexity_ozeti(dogru_olasiliklar):
    import math
    q = dogru_olasiliklar
    if not isinstance(q, list) or not q or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not 0 < x <= 1 for x in q):
        raise ValueError('olasılıklar (0, 1] aralığında sayılardan oluşan boş olmayan liste olmalı')
    kayip = -sum(math.log(x) for x in q) / len(q)
    return {'kayip': round(kayip, 9) + 0.0, 'bit_token': round(kayip / math.log(2), 9) + 0.0, 'perplexity': round(math.exp(kayip), 9)}
```

```test
need('perplexity_ozeti')
import math, random

eq(perplexity_ozeti([1.0, 1.0]), {'kayip': 0.0, 'bit_token': 0.0, 'perplexity': 1.0}, 'kusursuz model: perplexity 1')
r = perplexity_ozeti([0.25] * 10)
yakin(r['perplexity'], 4.0, 'her adımda dörtte bir: dört seçenek arasında kalmış', tol=1e-8)
yakin(r['bit_token'], 2.0, 'token başına 2 bit', tol=1e-8)
r = perplexity_ozeti([1 / 50000] * 3)
yakin(r['perplexity'], 50000.0, '50.000 lik sözlükte rastgele tahmin', tol=1e-4)
r = perplexity_ozeti([0.5, 0.125])
yakin(r['perplexity'], 4.0, 'geometrik ortalama: kök(0.5 x 0.125) = 0.25', tol=1e-8)
iyi = perplexity_ozeti([0.9] * 9 + [0.9])['perplexity']
kotu = perplexity_ozeti([0.9] * 9 + [0.0001])['perplexity']
ok(kotu > 2 * iyi, 'tek bir büyük hata perplexity yi belirgin biçimde yükseltir', got=(iyi, kotu))
rng = random.Random(1003)
for _ in range(25):
    q = [round(rng.uniform(0.001, 1.0), 4) for _ in range(rng.randint(1, 30))]
    r = perplexity_ozeti(q)
    nll = math.fsum(-math.log(x) for x in q) / len(q)
    yakin(r['kayip'], nll, 'rastgele olasılıklarda kayıp', tol=1e-8)
    yakin(r['bit_token'], nll / math.log(2), 'token başına bit', tol=1e-8)
    yakin(r['perplexity'], math.prod(q) ** (-1 / len(q)), 'perplexity geometrik ortalamanın tersidir', tol=1e-5 * max(1.0, math.exp(nll)))
    ok(r['perplexity'] >= 1.0 - 1e-9, 'perplexity 1 den küçük olmaz')
q = [0.5, 0.25]
perplexity_ozeti(q)
eq(q, [0.5, 0.25], 'girdi değişmez')
for kotu in (None, [], [0.0], [0.5, 0], [1.5], [-0.1], [0.5, "0.5"], [True], (0.5, 0.5), [float('nan')], [0.5, float('nan')]):
    raises(ValueError, perplexity_ozeti, kotu, msg='bozuk ya da sıfır olasılık reddedilir')
```

```hint
Önce logaritma, sonra ortalama: `kayip = -Σ ln(q) / n`. Perplexity `math.exp(kayip)`; bit değeri `kayip / math.log(2)`.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur; her adım bu derste hesapladığın bir sayıya ya da örneğe dayanır.

1. **Çerçeve (15 sn).** "Bir dil modelinin tek ölçüsü şudur: bir sonraki kelime ne kadar sürpriz oldu?"
2. **Bit (30 sn).** "Adil bir yazı tura 1 bit belirsizliktir; yüzde 90 tura gelen para yarım bit; hep tura gelen sıfır."
3. **Perplexity (30 sn).** "Perplexity'si 20 olan bir model, her kelimede eşit olasılıklı 20 seçenek arasında kalmış gibidir. 50.000 kelimelik sözlükte rastgele tahmin 50.000'dir."
4. **İmkânsız (25 sn).** "Model bir şeye sıfır olasılık verir ve o şey olursa kaybı sonsuzdur. Modellerin hiçbir şeye tam sıfır demediği bu yüzden."
5. **Kapanış (20 sn).** "Düşük perplexity, modelin metni iyi tahmin ettiğini söyler; doğru ya da güvenli konuştuğunu değil."
:::

::: anlat Sınır
Bu ders ayrık dağılımlar için entropiyi, cross-entropy'yi, KL divergence'ı ve perplexity'yi anlatır. Görevlerde gerçek dağılım `p` tam bilinir; pratikte `p` bilinmez ve cross-entropy sonlu bir örneklem üzerinden tahmin edilir, dolayısıyla kendi örnekleme hatası vardır (bkz. `ai-matematik-06`). Perplexity yalnız aynı `tokenizer` ve aynı test metniyle karşılaştırılabilir: farklı token'lara bölen iki modelin perplexity'leri yan yana konamaz; bu durumda karakter ya da bayt başına bit kullanılır. Düşük perplexity, modelin metni iyi tahmin ettiğini söyler; üretilen metnin doğru, yararlı ya da güvenli olduğunu söylemez. KL divergence simetrik olmadığından hangi yönde küçültüldüğü sonucu değiştirir: `KL(p || q)` küçültmek `q`'yu `p`'nin bütün kütlesini örtmeye, `KL(q || p)` küçültmek tek bir tepeye yığılmaya iter. Simetrik bir seçenek olan `Jensen-Shannon divergence` ve sürekli dağılımlar için diferansiyel entropi bu dersin kapsamı dışındadır.

Kaynaklar: [Shannon 1948 - A Mathematical Theory of Communication](https://doi.org/10.1002/j.1538-7305.1948.tb01338.x), [Kullback ve Leibler 1951 - On Information and Sufficiency](https://doi.org/10.1214/aoms/1177729694), [Goodfellow, Bengio ve Courville 2016 - Deep Learning, Bölüm 3.13: Information Theory](https://www.deeplearningbook.org/contents/prob.html), [Cover ve Thomas 2006 - Elements of Information Theory](https://doi.org/10.1002/047174882X).
:::

::: dusun
İki modelin test kaybı 2,30 ve 2,08 nat. Fark küçük görünüyor. İkisinin perplexity'sini hesapla. Sonra şunu düşün: birinci model sözlüğü 32.000, ikincisi 100.000 token olan bir `tokenizer` kullanıyorsa bu karşılaştırma neden geçersizdir ve neyle değiştirilmelidir?
:::

::: ozet
- Şaşırtıcılık `−log p`'dir; entropi bir dağılımın ortalama şaşırtıcılığı, yani belirsizliğidir.
- Cross-entropy, gerçek `p` iken `q`'ya inanmanın ortalama bedelidir ve `H(p, q) = H(p) + KL(p || q)` olur.
- KL negatif olmaz, simetrik değildir ve modelin sıfır olasılık verdiği bir olay gerçekleşirse sonsuzdur.
- Dil modelinde kayıp, doğru token'a verilen olasılığın eksi logaritmasının ortalamasıdır; perplexity bunun üstelidir.
- Perplexity yalnız aynı `tokenizer` ve aynı veriyle karşılaştırılabilir.
:::
