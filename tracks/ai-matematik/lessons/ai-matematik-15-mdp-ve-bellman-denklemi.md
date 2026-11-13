---
id: ai-matematik-15
title: "MDP ve Bellman Denklemi · Gelecekteki Ödülün Bugünkü Değeri"
summary: İndirimli getiriyi hesapla, verilen bir politikanın değer fonksiyonunu Bellman denklemiyle yinele ve value iteration ile en iyi politikayı bul.
---

::: anlat 1. Karar veren model
Şimdiye kadarki modeller tahmin etti. `Reinforcement learning` (RL) farklıdır: model **eylem seçer**, eylem dünyayı değiştirir ve sonuç hemen değil sonra görülür. `RLHF`, `GRPO` ve ajanların eğitimi bu çerçeveye dayanır (bkz. `ai-uretim-10`, `ai-uretim-11`).

Çerçevenin adı `Markov Decision Process` (MDP):

| Parça | Anlamı |
|---|---|
| Durum `s` | Ajanın bulunduğu yer |
| Eylem `a` | Ajanın seçebildiği hamle |
| Geçiş $P(s' \mid s, a)$ | Eylemden sonra hangi duruma, hangi olasılıkla geçilir |
| Ödül `r` | Geçişte alınan sayı |
| İndirim $\gamma \in [0, 1]$ | Gelecekteki ödülün bugünkü değeri |
| Politika $\pi$ | Her durumda hangi eylemin seçileceği |

`Markov` özelliği: gelecek yalnız şimdiki duruma bağlıdır; oraya nasıl gelindiği önemli değildir.

| Soru | Araç | Görev |
|---|---|---|
| Bir ödül dizisi toplamda ne eder? | İndirimli getiri (`return`) | 1 |
| Bu politika ne kadar iyi? | `Policy evaluation` | 2 |
| En iyi politika ne? | `Value iteration` | 3 |

Bu derste bütün görevlerde MDP şu biçimde verilir: `gecis[durum][eylem] = [(olasılık, sonraki_durum, ödül), ...]`. Hiç eylemi olmayan durum (`{}`) **terminal** durumdur; oradan ödül gelmez ve değeri 0'dır.
:::

::: anlat 2. Getiri, değer ve Bellman denklemi
**Getiri.** Ajanın amacı tek bir ödülü değil, ödüllerin indirimli toplamını büyütmektir:

$$G_t = r_{t+1} + \gamma r_{t+2} + \gamma^2 r_{t+3} + \dots$$

$\gamma = 0$ yalnız bir sonraki ödüle bakar; $\gamma$ 1'e yaklaştıkça ajan daha ileriyi düşünür. Getiri özyinelemelidir: $G_t = r_{t+1} + \gamma G_{t+1}$. Sondan başa tek geçişte hesaplanır.

**Değer fonksiyonu.** $V^\pi(s)$, `s` durumundan başlayıp $\pi$ politikasını izlediğinde beklenen getiridir. Aynı özyineleme beklenti altında da geçerlidir; buna **Bellman denklemi** denir:

$$V^\pi(s) = \sum_{s'} P(s' \mid s, \pi(s))\,\big[r + \gamma V^\pi(s')\big]$$

Bir durumun değeri, bir adım sonraki ödül artı varılan durumun indirimli değeridir. `Policy evaluation` bu denklemi bir güncelleme kuralı olarak kullanır: bütün değerleri 0'dan başlat, her turda sağ tarafı eski değerlerle hesapla, sol tarafa yaz. $\gamma < 1$ iken her tur hatayı $\gamma$ ile çarpar ve değerler yakınsar.

**En iyi değer.** En iyi politikanın değeri, her durumda en iyi eylemi seçmekle bulunur (`Bellman optimality`):

$$V^*(s) = \max_a \sum_{s'} P(s' \mid s, a)\,\big[r + \gamma V^*(s')\big]$$

`Value iteration` aynı yinelemeyi `max` ile yapar. Değerler yakınsayınca en iyi politika, her durumda bu toplamı en büyük yapan eylemdir.

Bu iki yöntem `dynamic programming`'dir ve MDP'nin tam bilindiğini varsayar. Geçişler bilinmediğinde ajan deneyerek öğrenir (bkz. `ai-matematik-16`).
:::

::: tahmin İndirim geleceği ne kadar küçültür?
Her adımda 1 ödül alınıyor. Farklı indirimlerle 50 adımlık toplam ne yazdırılır?

```python
for gamma in (0.5, 0.9, 0.99):
    toplam = sum(gamma ** t for t in range(50))
    print(gamma, round(toplam, 2))
```

???

```cikti
0.5 2.0
0.9 9.95
0.99 39.5
```
Sonsuz toplam $\dfrac{1}{1 - \gamma}$'dır: 2, 10 ve 100. $\gamma = 0{,}5$ ile 50 adım fazlasıyla yeter; toplam 2'ye ulaşmıştır. $\gamma = 0{,}99$ ile 50 adımda toplamın yalnız %40'ı birikmiştir. $\dfrac{1}{1 - \gamma}$'ya ajanın **etkin ufku** denir: $\gamma = 0{,}9$ kabaca 10 adım, $\gamma = 0{,}99$ kabaca 100 adım ileriyi önemser.
:::

::: gorev 1 · İndirimli getiri
`getiriler(oduller, gamma)` işlevini yaz.

- `oduller`: boş olmayan sayı listesi; `oduller[t]`, `t` anındaki eylemden sonra alınan ödüldür. `gamma`: `[0, 1]` aralığında sayı.
- Dönüş: aynı uzunlukta liste; `t`. öğe $G_t = \sum_{k \ge 0} \gamma^k\, \text{oduller}[t + k]$; 9 basamağa yuvarlanır.
- Hesap sondan başa tek geçişte yapılmalıdır; yuvarlama yalnız çıktıda uygulanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç her zaman adımına aynı toplamı (bölümün baştan sona getirisini) yazıyor: geçmişte alınmış ödülleri de sonraki adımlara mal ediyor.

```starter
def getiriler(oduller, gamma):
    g = sum(r * gamma ** t for t, r in enumerate(oduller))
    return [round(g, 9) for _ in oduller]
```

```solution
def getiriler(oduller, gamma):
    import math
    if not isinstance(oduller, list) or not oduller or any(isinstance(r, bool) or not isinstance(r, (int, float)) or not math.isfinite(r) for r in oduller):
        raise ValueError('oduller boş olmayan sayı listesi olmalı')
    if isinstance(gamma, bool) or not isinstance(gamma, (int, float)) or not 0 <= gamma <= 1:
        raise ValueError('gamma [0, 1] aralığında olmalı')
    out = [0.0] * len(oduller)
    g = 0.0
    for t in range(len(oduller) - 1, -1, -1):
        g = oduller[t] + gamma * g
        out[t] = g
    return [round(x, 9) for x in out]
```

```test
need('getiriler')
import math, random

eq(getiriler([1, 1, 1], 1), [3.0, 2.0, 1.0], 'indirimsiz: kalan ödüllerin toplamı')
eq(getiriler([1, 1, 1], 0), [1.0, 1.0, 1.0], 'gamma 0: yalnız bir sonraki ödül')
eq(getiriler([0, 0, 10], 0.5), [2.5, 5.0, 10.0], 'uzaktaki ödül her adımda yarıya iner')
eq(getiriler([5], 0.9), [5.0], 'tek adım')
eq(getiriler([1, -1, 2], 0.5), [1.0, 0.0, 2.0], 'negatif ödül')
r = getiriler([1] * 200, 0.9)
yakin(r[0], 10.0, 'uzun bölümde ilk getiri 1 / (1 - gamma) ya yaklaşır', tol=1e-6)
rng = random.Random(1501)
for _ in range(25):
    od = [round(rng.uniform(-3, 3), 2) for _ in range(rng.randint(1, 20))]
    g = rng.choice([0, 0.3, 0.9, 0.99, 1])
    got = getiriler(od, g)
    for t in range(len(od)):
        yakin(got[t], math.fsum(od[t + k] * g ** k for k in range(len(od) - t)), 'rastgele ödüllerde doğrudan toplamla aynı', tol=1e-7)
    for t in range(len(od) - 1):
        yakin(got[t], od[t] + g * got[t + 1], 'özyineleme: G_t = r + gamma G_(t+1)', tol=1e-7)
od = [1, 2]
getiriler(od, 0.5)
eq(od, [1, 2], 'girdi değişmez')
for a, g in [(None, 0.9), ([], 0.9), ([1, "2"], 0.9), ([True], 0.9), ((1, 2), 0.9), ([float('nan')], 0.9), ([float('inf')], 0.9), ([1], -0.1), ([1], 1.1), ([1], None), ([1], True), ([1], float('nan'))]:
    raises(ValueError, getiriler, a, g, msg='bozuk girdi reddedilir')
```

```hint
Sondan başla: `g = oduller[t] + gamma * g`. Her adımda `g`'yi o indekse yaz.
```
:::

::: gorev 2 · Policy evaluation
`politika_degeri(gecis, politika, gamma, tur)` işlevini yaz.

- `gecis`: boş olmayan `dict`; `gecis[s][a]` boş olmayan bir `(olasılık, sonraki, ödül)` listesidir. Olasılıklar `[0, 1]` aralığında ve her eylem için toplamı 1 (`1e-9` toleransla); `sonraki` `gecis`'in bir anahtarı olmalıdır. Durum ve eylem adları `str`. `gecis[s] == {}` terminal durumdur.
- `politika`: terminal olmayan her durum için o durumda geçerli bir eylem veren `dict`.
- `gamma`: `[0, 1]` aralığında sayı. `tur`: negatif olmayan `int`.
- Bütün değerler 0'dan başlar. Her turda **eşzamanlı** güncelle: yeni değerlerin hepsi bir önceki turun değerlerinden hesaplanır.
- Dönüş: `{durum: değer}`; 6 basamağa yuvarlanır; terminal durumların değeri 0.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç yalnız anlık ödülün beklentisini yazıyor: Bellman denklemindeki `gamma · V(s')` terimi yok.

```starter
def politika_degeri(gecis, politika, gamma, tur):
    V = {s: 0.0 for s in gecis}
    for _ in range(tur):
        V = {s: (sum(p * r for p, _, r in gecis[s][politika[s]]) if gecis[s] else 0.0) for s in gecis}
    return {s: round(v, 6) for s, v in V.items()}
```

```solution
def politika_degeri(gecis, politika, gamma, tur):
    import math
    def sayi(x):
        return not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x)
    if not isinstance(gecis, dict) or not gecis:
        raise ValueError('gecis boş olmayan dict olmalı')
    for s, eylemler in gecis.items():
        if not isinstance(s, str) or not isinstance(eylemler, dict):
            raise ValueError('durum str, eylemler dict olmalı')
        for a, sonuclar in eylemler.items():
            if not isinstance(a, str) or not isinstance(sonuclar, list) or not sonuclar:
                raise ValueError('eylem str, sonuçlar boş olmayan liste olmalı')
            for x in sonuclar:
                if not isinstance(x, (tuple, list)) or len(x) != 3 or not sayi(x[0]) or not 0 <= x[0] <= 1 or x[1] not in gecis or not sayi(x[2]):
                    raise ValueError('sonuç (olasılık, sonraki, ödül) olmalı')
            if abs(sum(x[0] for x in sonuclar) - 1) > 1e-9:
                raise ValueError('olasılıklar 1 e toplanmalı')
    if not isinstance(politika, dict) or any(gecis[s] and politika.get(s) not in gecis[s] for s in gecis):
        raise ValueError('politika her durum için geçerli bir eylem vermeli')
    if not sayi(gamma) or not 0 <= gamma <= 1:
        raise ValueError('gamma [0, 1] aralığında olmalı')
    if isinstance(tur, bool) or not isinstance(tur, int) or tur < 0:
        raise ValueError('tur negatif olmayan int olmalı')
    V = {s: 0.0 for s in gecis}
    for _ in range(tur):
        V = {s: (sum(p * (r + gamma * V[n]) for p, n, r in gecis[s][politika[s]]) if gecis[s] else 0.0) for s in gecis}
    return {s: round(v, 6) for s, v in V.items()}
```

```test
need('politika_degeri')
import random

zincir = {'A': {'ileri': [(1.0, 'B', 0)]}, 'B': {'ileri': [(1.0, 'C', 0)]}, 'C': {'ileri': [(1.0, 'son', 10)]}, 'son': {}}
pol = {'A': 'ileri', 'B': 'ileri', 'C': 'ileri'}
eq(politika_degeri(zincir, pol, 0.5, 0), {'A': 0.0, 'B': 0.0, 'C': 0.0, 'son': 0.0}, 'sıfır tur: bütün değerler 0')
eq(politika_degeri(zincir, pol, 0.5, 1), {'A': 0.0, 'B': 0.0, 'C': 10.0, 'son': 0.0}, 'bir tur: ödül yalnız bir adım geri yayılır (eşzamanlı güncelleme)')
eq(politika_degeri(zincir, pol, 0.5, 3), {'A': 2.5, 'B': 5.0, 'C': 10.0, 'son': 0.0}, 'üç tur: ödül her adımda yarılanarak başa ulaşır')
eq(politika_degeri(zincir, pol, 0.5, 30), {'A': 2.5, 'B': 5.0, 'C': 10.0, 'son': 0.0}, 'yakınsadıktan sonra değişmez')
dongu = {'s': {'kal': [(1.0, 's', 1)]}}
yakin(politika_degeri(dongu, {'s': 'kal'}, 0.9, 400)['s'], 10.0, 'sonsuz döngüde değer 1 / (1 - gamma)', tol=1e-5)
yazitura = {'s': {'at': [(0.5, 'k', 4), (0.5, 'y', -2)]}, 'k': {}, 'y': {}}
eq(politika_degeri(yazitura, {'s': 'at'}, 1, 5)['s'], 1.0, 'rastgele geçişte beklenen ödül')
def _ref(gecis, pol, gamma, tur):
    V = dict.fromkeys(gecis, 0.0)
    for _ in range(tur):
        yeni = {}
        for s in gecis:
            t = 0.0
            if gecis[s]:
                for p, n, r in gecis[s][pol[s]]:
                    t += p * r + p * gamma * V[n]
            yeni[s] = t
        V = yeni
    return V
rng = random.Random(1502)
for _ in range(15):
    ds = [f"s{i}" for i in range(rng.randint(1, 5))]
    gecis = {}
    for s in ds:
        if rng.random() < 0.2 and len(ds) > 1:
            gecis[s] = {}
            continue
        gecis[s] = {}
        for a in ['x', 'y'][:rng.randint(1, 2)]:
            k = rng.randint(1, 3)
            w = [rng.randint(1, 5) for _ in range(k)]
            gecis[s][a] = [(x / sum(w), rng.choice(ds), rng.randint(-3, 3)) for x in w]
    pol = {s: rng.choice(sorted(gecis[s])) for s in ds if gecis[s]}
    g, tur = rng.choice([0, 0.5, 0.9]), rng.randint(0, 12)
    got, exp = politika_degeri(gecis, pol, g, tur), _ref(gecis, pol, g, tur)
    for s in ds:
        yakin(got[s], exp[s], 'rastgele MDP de bağımsız referansla aynı', tol=2e-6)
iyi = {'s': {'a': [(1.0, 's', 1)]}}
for a in ([None, {'s': 'a'}, 0.9, 1], [['kotu'], {'s': 'a'}, 0.9, 1], [{}, {}, 0.9, 1], [{1: {}}, {}, 0.9, 1], [{'s': {1: [(1.0, 's', 1)]}}, {'s': 1}, 0.9, 1], [{'s': {'a': 'kotu'}}, {'s': 'a'}, 0.9, 1], [{'s': {'a': ((1.0, 's', 1),)}}, {'s': 'a'}, 0.9, 1], [{'s': {'a': ['kotu']}}, {'s': 'a'}, 0.9, 1], [{'s': {'a': [{1, 2, 3}]}}, {'s': 'a'}, 0.9, 1], [{'s': {'a': [(True, 's', 1)]}}, {'s': 'a'}, 0.9, 1], [{'s': {'a': [(1.0, 's', True)]}}, {'s': 'a'}, 0.9, 1], [{'s': {'a': [(float('nan'), 's', 1)]}}, {'s': 'a'}, 0.9, 1], [{'s': {'a': [(1.0, 's', float('inf'))]}}, {'s': 'a'}, 0.9, 1], [{'s': {'a': [(-0.5, 's', 1), (1.5, 's', 1)]}}, {'s': 'a'}, 0.9, 1], [iyi, {'s': 'yok'}, 0.9, 1], [iyi, {}, 0.9, 1], [iyi, None, 0.9, 1], [iyi, {'s': 'a'}, 1.5, 1], [iyi, {'s': 'a'}, -0.1, 1], [iyi, {'s': 'a'}, None, 1], [iyi, {'s': 'a'}, True, 1], [iyi, {'s': 'a'}, float('nan'), 1], [iyi, {'s': 'a'}, 0.9, -1], [iyi, {'s': 'a'}, 0.9, 1.0], [iyi, {'s': 'a'}, 0.9, True], [{'s': {'a': [(0.5, 's', 1)]}}, {'s': 'a'}, 0.9, 1], [{'s': {'a': [(1.0, 'yok', 1)]}}, {'s': 'a'}, 0.9, 1], [{'s': {'a': []}}, {'s': 'a'}, 0.9, 1], [{'s': {'a': [(1.0, 's')]}}, {'s': 'a'}, 0.9, 1], [{'s': [('a', 1)]}, {'s': 'a'}, 0.9, 1]):
    raises(ValueError, politika_degeri, *a, msg='bozuk MDP ya da politika reddedilir')
```

```hint
Her turda **yeni** bir sözlük kur; eski `V`'yi okurken üstüne yazma. Bir durumun yeni değeri: `Σ p · (r + gamma · V[sonraki])`.
```
:::

::: gorev 3 · Value iteration
`deger_yinelemesi(gecis, gamma, tur)` işlevini yaz.

- `gecis`, `gamma`, `tur`: Görev 2'deki gibi.
- Bütün değerler 0'dan başlar. Her turda eşzamanlı güncelle: `V(s) = max_a Σ p · (r + gamma · V(s'))`; terminal durum 0.
- Turlar bittikten sonra politikayı **son** değerlerden çıkar: her terminal olmayan durumda toplamı en büyük yapan eylem; eşitlikte (`1e-9` toleransla) alfabetik olarak önce gelen.
- Dönüş: `{'V': {durum: değer}, 'politika': {durum: eylem}}`; değerler 6 basamağa yuvarlanır; terminal durumlar politikada yer almaz.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç her durumda **anlık** ödülü en büyük olan eylemi seçiyor: küçük bir ödülü hemen alıp büyük ödüle giden yolu kaçırıyor.

```starter
def deger_yinelemesi(gecis, gamma, tur):
    V, pol = {}, {}
    for s in gecis:
        if not gecis[s]:
            V[s] = 0.0
            continue
        anlik = {a: sum(p * r for p, _, r in sonuc) for a, sonuc in gecis[s].items()}
        pol[s] = max(sorted(anlik), key=lambda a: anlik[a])
        V[s] = round(anlik[pol[s]], 6)
    return {'V': V, 'politika': pol}
```

```solution
def deger_yinelemesi(gecis, gamma, tur):
    import math
    def sayi(x):
        return not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x)
    if not isinstance(gecis, dict) or not gecis:
        raise ValueError('gecis boş olmayan dict olmalı')
    for s, eylemler in gecis.items():
        if not isinstance(s, str) or not isinstance(eylemler, dict):
            raise ValueError('durum str, eylemler dict olmalı')
        for a, sonuclar in eylemler.items():
            if not isinstance(a, str) or not isinstance(sonuclar, list) or not sonuclar:
                raise ValueError('eylem str, sonuçlar boş olmayan liste olmalı')
            for x in sonuclar:
                if not isinstance(x, (tuple, list)) or len(x) != 3 or not sayi(x[0]) or not 0 <= x[0] <= 1 or x[1] not in gecis or not sayi(x[2]):
                    raise ValueError('sonuç (olasılık, sonraki, ödül) olmalı')
            if abs(sum(x[0] for x in sonuclar) - 1) > 1e-9:
                raise ValueError('olasılıklar 1 e toplanmalı')
    if not sayi(gamma) or not 0 <= gamma <= 1:
        raise ValueError('gamma [0, 1] aralığında olmalı')
    if isinstance(tur, bool) or not isinstance(tur, int) or tur < 0:
        raise ValueError('tur negatif olmayan int olmalı')

    def q(s, a, V):
        return sum(p * (r + gamma * V[n]) for p, n, r in gecis[s][a])

    V = {s: 0.0 for s in gecis}
    for _ in range(tur):
        V = {s: (max(q(s, a, V) for a in gecis[s]) if gecis[s] else 0.0) for s in gecis}
    politika = {}
    for s in gecis:
        if not gecis[s]:
            continue
        en, en_a = None, None
        for a in sorted(gecis[s]):
            deger = q(s, a, V)
            if en is None or deger > en + 1e-9:
                en, en_a = deger, a
        politika[s] = en_a
    return {'V': {s: round(v, 6) for s, v in V.items()}, 'politika': politika}
```

```test
need('deger_yinelemesi')
import random

mdp = {
    'A': {'hemen': [(1.0, 'son', 1)], 'sabret': [(1.0, 'B', 0)]},
    'B': {'ileri': [(1.0, 'son', 10)]},
    'son': {},
}
r = deger_yinelemesi(mdp, 0.9, 20)
eq(r['politika'], {'A': 'sabret', 'B': 'ileri'}, 'büyük ödüle giden yol: anlık ödülü küçük eylem seçilir')
eq(r['V'], {'A': 9.0, 'B': 10.0, 'son': 0.0}, 'en iyi değerler')
r = deger_yinelemesi(mdp, 0.05, 20)
eq(r['politika']['A'], 'hemen', 'indirim çok küçükse hemen alınan ödül kazanır')
r = deger_yinelemesi(mdp, 0.9, 0)
eq(r['V'], {'A': 0.0, 'B': 0.0, 'son': 0.0}, 'sıfır tur: değerler 0')
eq(r['politika']['A'], 'hemen', 'sıfır turda politika anlık ödüle bakar')
esit = {'s': {'b': [(1.0, 'son', 1)], 'a': [(1.0, 'son', 1)]}, 'son': {}}
eq(deger_yinelemesi(esit, 0.9, 3)['politika'], {'s': 'a'}, 'eşit değerde alfabetik olarak önce gelen eylem')
riskli = {'s': {'guvenli': [(1.0, 'son', 2)], 'kumar': [(0.9, 'son', 0), (0.1, 'son', 30)]}, 'son': {}}
r = deger_yinelemesi(riskli, 1, 2)
eq((r['politika']['s'], r['V']['s']), ('kumar', 3.0), 'beklenen değeri yüksek olan eylem seçilir')
def _ref(gecis, gamma, tur):
    V = dict.fromkeys(gecis, 0.0)
    def Q(s, a, V):
        return sum(p * r + p * gamma * V[n] for p, n, r in gecis[s][a])
    for _ in range(tur):
        V = {s: (max(Q(s, a, V) for a in gecis[s]) if gecis[s] else 0.0) for s in gecis}
    return V, Q
rng = random.Random(1503)
for _ in range(15):
    ds = [f"s{i}" for i in range(rng.randint(1, 5))]
    gecis = {}
    for s in ds:
        if rng.random() < 0.2 and len(ds) > 1:
            gecis[s] = {}
            continue
        gecis[s] = {}
        for a in ['x', 'y', 'z'][:rng.randint(1, 3)]:
            w = [rng.randint(1, 5) for _ in range(rng.randint(1, 3))]
            gecis[s][a] = [(x / sum(w), rng.choice(ds), rng.randint(-3, 3)) for x in w]
    g, tur = rng.choice([0, 0.5, 0.9]), rng.randint(0, 15)
    got = deger_yinelemesi(gecis, g, tur)
    V, Q = _ref(gecis, g, tur)
    for s in ds:
        yakin(got['V'][s], V[s], 'rastgele MDP de değerler bağımsız referansla aynı', tol=2e-6)
        if gecis[s]:
            ok(Q(s, got['politika'][s], V) >= max(Q(s, a, V) for a in gecis[s]) - 1e-7, 'politika her durumda en iyi eylemi seçer')
        else:
            ok(s not in got['politika'], 'terminal durum politikada yok')
iyi = {'s': {'a': [(1.0, 's', 1)]}}
for a in ([None, 0.9, 1], [['kotu'], 0.9, 1], [{}, 0.9, 1], [{'s': []}, 0.9, 1], [{'s': {1: [(1.0, 's', 1)]}}, 0.9, 1], [{'s': {'a': 'kotu'}}, 0.9, 1], [{'s': {'a': ((1.0, 's', 1),)}}, 0.9, 1], [{'s': {'a': ['kotu']}}, 0.9, 1], [{'s': {'a': [{1, 2, 3}]}}, 0.9, 1], [{'s': {'a': [(1.0, 's')]}}, 0.9, 1], [{'s': {'a': [(True, 's', 1)]}}, 0.9, 1], [{'s': {'a': [(1.0, 's', True)]}}, 0.9, 1], [{'s': {'a': [(float('nan'), 's', 1)]}}, 0.9, 1], [{'s': {'a': [(1.0, 's', float('inf'))]}}, 0.9, 1], [{'s': {'a': [(-0.5, 's', 1), (1.5, 's', 1)]}}, 0.9, 1], [iyi, 1.5, 1], [iyi, -0.1, 1], [iyi, None, 1], [iyi, True, 1], [iyi, float('nan'), 1], [iyi, 0.9, -1], [iyi, 0.9, 1.0], [iyi, 0.9, True], [{'s': {'a': [(0.5, 's', 1)]}}, 0.9, 1], [{'s': {'a': [(1.0, 'yok', 1)]}}, 0.9, 1], [{'s': {'a': []}}, 0.9, 1], [{1: {'a': [(1.0, 1, 1)]}}, 0.9, 1]):
    raises(ValueError, deger_yinelemesi, *a, msg='bozuk MDP reddedilir')
```

```hint
Yardımcı bir `q(s, a, V)` yaz: `Σ p · (r + gamma · V[sonraki])`. Yinelemede `max` al; sonda eylemleri alfabetik gez ve yalnız kesin daha iyi olanı seç.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur; her adım bu derste hesapladığın bir sayıya ya da örneğe dayanır.

1. **Çerçeve (15 sn).** "Bir modelin tahmin etmesiyle karar vermesi farklıdır: karar dünyayı değiştirir ve sonuç sonra gelir."
2. **İndirim (30 sn).** "Ajan geleceğe ne kadar değer verir? İndirim 0,9 ise kabaca on adım ileriyi, 0,99 ise yüz adım ileriyi önemser."
3. **Bellman (30 sn).** "Bir durumun değeri, şimdi aldığınız ödül artı vardığınız yerin değeridir. Bu basit cümle bütün pekiştirmeli öğrenmenin çekirdeği."
4. **Seçim (25 sn).** "Aynı ajan, indirim değiştiğinde küçük ödülü hemen alır ya da büyük ödülü bekler. Kısa görüşlülük bazen bir ayardır."
5. **Kapanış (20 sn).** "Ajan ödülü büyütür, niyetinizi değil. Ödülü yazan sizsiniz."
:::

::: anlat Sınır
Bu ders MDP'yi, indirimli getiriyi ve iki `dynamic programming` yöntemini anlatır. Her iki yöntem de geçiş olasılıklarının ve ödüllerin **tam bilindiğini** ve durumların tek tek sayılabildiğini varsayar. Gerçek problemlerde geçişler bilinmez (ajan deneyerek öğrenir) ve durum uzayı sayılamayacak kadar büyüktür (bir satranç tahtası, bir metin geçmişi); o zaman değerler bir tabloda değil bir sinir ağında tutulur. Markov varsayımı gözlemin bütün ilgili bilgiyi taşıdığını söyler; ajan dünyanın yalnız bir kısmını görüyorsa (`partial observability`) bu varsayım bozulur. Görevlerde tur sayısı sabittir; pratikte değerler arası en büyük değişim bir eşiğin altına inene kadar yinelenir. $\gamma = 1$ ve hiç terminale varmayan döngüler varken değerler ıraksar. Ödül fonksiyonu burada verilidir; gerçek sistemlerde ödülü doğru tanımlamak işin en zor kısmıdır, çünkü ajan ödülü büyütür, senin kastettiğin amacı değil.

Kaynaklar: [Sutton ve Barto 2018 - Reinforcement Learning: An Introduction, Bölüm 3 ve 4](http://incompleteideas.net/book/the-book-2nd.html), [Bellman 1957 - Dynamic Programming](https://press.princeton.edu/books/paperback/9780691146683/dynamic-programming), [Puterman 1994 - Markov Decision Processes](https://doi.org/10.1002/9780470316887).
:::

::: dusun
Görev 3'teki ilk MDP'de `gamma = 0.9` iken ajan sabrediyor, `gamma = 0.05` iken hemen ödülü alıyor. İki eylemin değerinin eşitlendiği `gamma` değeri nedir? Bir ajanın "kısa görüşlü" davranmasının sebebi her zaman kötü bir politika mıdır, yoksa indirim seçimi de olabilir mi?
:::

::: ozet
- MDP durumlar, eylemler, geçiş olasılıkları, ödüller ve bir indirimden oluşur; gelecek yalnız şimdiki duruma bağlıdır.
- Getiri indirimli ödül toplamıdır ve `G_t = r + γ G_(t+1)` özyinelemesiyle sondan başa hesaplanır.
- Bellman denklemi bir durumun değerini bir adım sonraki ödül ve varılan durumun indirimli değeri olarak yazar.
- `Policy evaluation` verilen politikanın, `value iteration` en iyi politikanın değerlerini yineleyerek bulur.
- İndirim etkin ufku belirler (`1 / (1 − γ)`); ikisi de MDP'nin tam bilindiğini varsayar.
:::
