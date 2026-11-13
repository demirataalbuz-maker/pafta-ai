---
id: ai-matematik-16
title: "Q-Learning · Modeli Bilmeden, Deneyerek Öğrenmek"
summary: Tek bir temporal-difference güncellemesini, epsilon-greedy eylem seçimini ve tablo tabanlı Q-learning döngüsünü yaz; ajanın geçiş kurallarını hiç görmeden en iyi politikayı nasıl bulduğunu ölç.
---

::: anlat 1. Harita yokken
`ai-matematik-15`'teki yöntemler MDP'nin tamamını biliyordu: hangi eylem nereye götürür, kaç ödül verir. Gerçek bir ajan bunu bilmez; yalnız dener ve sonucu görür. Her denemeden elinde dört şey kalır: bulunduğu durum `s`, yaptığı eylem `a`, aldığı ödül `r` ve vardığı durum `s'`.

`Q-learning` bu dörtlülerden öğrenir. Durumların değerini değil, **durum-eylem çiftlerinin** değerini tutar: $Q(s, a)$, "`s` durumunda `a`'yı yapıp sonra en iyi biçimde devam edersem beklenen getirim". Bu tablo varsa politika bedavadır: her durumda `Q`'su en büyük eylemi seç. Geçiş modeline gerek kalmaz.

| Soru | Araç | Görev |
|---|---|---|
| Tek bir deneyimden tablo nasıl güncellenir? | `Temporal-difference` güncellemesi | 1 |
| Bilineni mi kullanmalı, yeniyi mi denemeli? | `Epsilon-greedy` | 2 |
| Bunlar birleşince ajan nasıl öğrenir? | Q-learning döngüsü | 3 |
:::

::: anlat 2. TD hatası, keşif ve döngü
**Güncelleme.** Bir `(s, a, r, s')` deneyiminden sonra:

$$Q(s, a) \leftarrow Q(s, a) + \alpha\,\Big[\underbrace{r + \gamma \max_{a'} Q(s', a')}_{\text{hedef}} - Q(s, a)\Big]$$

Köşeli parantezin içi **TD hatasıdır**: gözlenen bir adımlık kanıt ile eski tahmin arasındaki fark. $\alpha$ öğrenme oranıdır: hatanın ne kadarının düzeltileceği. `s'` terminal durumsa gelecekte ödül yoktur ve hedef yalnız `r`'dir.

İki önemli özellik:

- **Bootstrapping.** Hedefin içinde tablonun kendi tahmini ($\max Q(s', \cdot)$) vardır. Ajan bölümün sonunu beklemeden, her adımda öğrenir; ama tahminini başka bir tahmine dayandırır.
- **Off-policy.** Hedef, ajanın gerçekte seçeceği eylemi değil, **en iyi** eylemi (`max`) kullanır. Ajan rastgele dolaşırken bile en iyi politikanın değerlerini öğrenir.

**Keşif.** Ajan hep en iyi bildiği eylemi seçerse, ilk başta şans eseri iyi görünen eyleme saplanır ve daha iyisini hiç denemez. `Epsilon-greedy` basit bir çözümdür: $\epsilon$ olasılıkla rastgele bir eylem seç (`exploration`), yoksa en iyi bilineni (`exploitation`). $\epsilon$ genellikle eğitim boyunca azaltılır.

**Ödül geriye yayılır.** Ödül yalnız hedefe varınca alınıyorsa, ilk bölümde yalnız hedefe komşu durumun `Q`'su güncellenir. İkinci bölümde ondan bir önceki. Bilgi her bölümde bir adım geri gider. Uzun görevlerde ve seyrek ödülde Q-learning'in yavaş olmasının sebebi budur.

Bu derste ortam şu biçimde verilir: `ortam[durum][eylem] = (sonraki_durum, ödül, terminal_mi)`. Ajan bu sözlüğü **okumaz**; yalnız adım atmak için kullanılır.
:::

::: tahmin Tek bir güncelleme
Tablo sıfırlarla başlıyor. Ajan `B` durumunda `sağ` eylemini yapıp 10 ödül alıyor ve bölüm bitiyor. Sonra `A`'da `sağ` yapıp 0 ödülle `B`'ye geçiyor. `alpha = 0.5`, `gamma = 0.9`. Ne yazdırılır?

```python
alpha, gamma = 0.5, 0.9
Q = {("A", "sağ"): 0.0, ("B", "sağ"): 0.0}

Q[("B", "sağ")] += alpha * (10 - Q[("B", "sağ")])
Q[("A", "sağ")] += alpha * (0 + gamma * Q[("B", "sağ")] - Q[("A", "sağ")])
print(Q[("B", "sağ")], Q[("A", "sağ")])
```

???

```cikti
5.0 2.25
```
`B`'deki güncelleme terminal bir geçiştir: hedef 10, eski değer 0, hatanın yarısı düzeltilir: 5. `A`'daki geçişte ödül 0'dır ama hedef $0 + 0{,}9 \times 5 = 4{,}5$'tir; yarısı 2,25. `A` hiç ödül almadı; değerini `B`'nin tahmininden **devraldı**. Bootstrapping budur. Sırayı ters çevirseydin (`A` önce) `A`'nın değeri 0 kalırdı: bilgi geriye doğru, bölüm bölüm yayılır.
:::

::: gorev 1 · TD güncellemesi
`q_guncelle(Q, s, a, r, s2, alpha, gamma, terminal)` işlevini yaz.

- `Q`: `{durum: {eylem: değer}}` biçiminde boş olmayan `dict`; `s` ve `s2` anahtarları, `a` da `Q[s]`'nin anahtarı olmalıdır.
- `r`: sayı. `alpha`, `gamma`: `[0, 1]` aralığında sayı. `terminal`: `bool`.
- Hedef: `terminal` ise `r`; değilse `r + gamma · max(Q[s2].values())`. `Q[s2]` boşsa ve `terminal` değilse `ValueError`.
- Dönüş: güncellenmiş tablonun **derin kopyası**; yalnız `Q[s][a]` değişir ve 9 basamağa yuvarlanır. Girdi tablo değişmemelidir.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç hedefte `max` yerine `Q[s2]`'nin **ortalamasını** kullanıyor ve terminal bayrağını yok sayıyor: en iyi eylemin değil, rastgele bir eylemin değerini öğreniyor.

```starter
def q_guncelle(Q, s, a, r, s2, alpha, gamma, terminal):
    import copy
    yeni = copy.deepcopy(Q)
    gelecek = sum(Q[s2].values()) / len(Q[s2]) if Q[s2] else 0.0
    yeni[s][a] = round(Q[s][a] + alpha * (r + gamma * gelecek - Q[s][a]), 9)
    return yeni
```

```solution
def q_guncelle(Q, s, a, r, s2, alpha, gamma, terminal):
    import copy, math
    def sayi(x):
        return not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x)
    if not isinstance(Q, dict) or not Q or any(not isinstance(v, dict) or any(not sayi(x) for x in v.values()) for v in Q.values()):
        raise ValueError('Q {durum: {eylem: değer}} biçiminde olmalı')
    if s not in Q or s2 not in Q or a not in Q[s]:
        raise ValueError('durum ya da eylem tabloda yok')
    if not sayi(r) or not sayi(alpha) or not sayi(gamma) or not 0 <= alpha <= 1 or not 0 <= gamma <= 1:
        raise ValueError('r sayı; alpha ve gamma [0, 1] aralığında olmalı')
    if not isinstance(terminal, bool):
        raise ValueError('terminal bool olmalı')
    if terminal:
        hedef = r
    else:
        if not Q[s2]:
            raise ValueError('terminal olmayan durumun eylemi olmalı')
        hedef = r + gamma * max(Q[s2].values())
    yeni = copy.deepcopy(Q)
    yeni[s][a] = round(Q[s][a] + alpha * (hedef - Q[s][a]), 9)
    return yeni
```

```test
need('q_guncelle')
import copy, random

Q = {'A': {'sol': 0.0, 'sag': 0.0}, 'B': {'sol': 1.0, 'sag': 5.0}, 'son': {}}
r = q_guncelle(Q, 'B', 'sag', 10, 'son', 0.5, 0.9, True)
eq(r['B']['sag'], 7.5, 'terminal geçiş: hedef yalnız ödül')
r = q_guncelle(Q, 'A', 'sag', 0, 'B', 0.5, 0.9, False)
eq(r['A']['sag'], 2.25, 'hedef en iyi eylemin değeri (5), ortalama (3) değil')
eq(r['A']['sol'], 0.0, 'yalnız seçilen eylem güncellenir')
eq(q_guncelle(Q, 'A', 'sag', 3, 'B', 0, 0.9, False)['A']['sag'], 0.0, 'alpha 0: hiç öğrenmez')
eq(q_guncelle(Q, 'A', 'sag', 3, 'B', 1, 0.9, False)['A']['sag'], 7.5, 'alpha 1: hedefin kendisi')
eq(q_guncelle(Q, 'A', 'sag', 3, 'B', 1, 0, False)['A']['sag'], 3.0, 'gamma 0: yalnız anlık ödül')
eq(q_guncelle(Q, 'B', 'sag', 2, 'B', 0.5, 1, True)['B']['sag'], 3.5, 'terminal bayrağı varsa sonraki durumun değeri kullanılmaz')
eski = copy.deepcopy(Q)
r = q_guncelle(Q, 'A', 'sag', 1, 'B', 0.5, 0.9, False)
eq(Q, eski, 'girdi tablo değişmez')
r['B']['sol'] = 99
eq(Q['B']['sol'], 1.0, 'dönüş derin kopyadır')
rng = random.Random(1601)
for _ in range(25):
    ds = [f"s{i}" for i in range(rng.randint(1, 4))]
    T = {d: {e: round(rng.uniform(-5, 5), 2) for e in ['x', 'y', 'z'][:rng.randint(1, 3)]} for d in ds}
    s, s2 = rng.choice(ds), rng.choice(ds)
    a = rng.choice(sorted(T[s]))
    od, al, ga, term = round(rng.uniform(-3, 3), 2), rng.choice([0, 0.1, 0.5, 1]), rng.choice([0, 0.9, 1]), rng.random() < 0.3
    hedef = od if term else od + ga * max(T[s2].values())
    r = q_guncelle(T, s, a, od, s2, al, ga, term)
    yakin(r[s][a], (1 - al) * T[s][a] + al * hedef, 'rastgele tabloda: eski ve hedefin ağırlıklı ortalaması', tol=1e-8)
    for d in ds:
        for e in T[d]:
            if (d, e) != (s, a):
                eq(r[d][e], T[d][e], 'diğer hücreler aynı')
raises(ValueError, q_guncelle, Q, 'A', 'sag', 0, 'son', 0.5, 0.9, False, msg='eylemsiz duruma terminal olmayan geçiş')
for a in ([None, 'A', 'sag', 0, 'B', 0.5, 0.9, False], [['kotu'], 'A', 'sag', 0, 'B', 0.5, 0.9, False], [{}, 'A', 'sag', 0, 'B', 0.5, 0.9, False], [{'A': []}, 'A', 'sag', 0, 'A', 0.5, 0.9, False], [{'A': {'x': True}}, 'A', 'x', 0, 'A', 0.5, 0.9, False], [{'A': {'x': float('nan')}}, 'A', 'x', 0, 'A', 0.5, 0.9, False], [Q, 'yok', 'sag', 0, 'B', 0.5, 0.9, False], [Q, 'A', 'yok', 0, 'B', 0.5, 0.9, False], [Q, 'A', 'sag', 0, 'yok', 0.5, 0.9, False], [Q, 'A', 'sag', None, 'B', 0.5, 0.9, False], [Q, 'A', 'sag', True, 'B', 0.5, 0.9, False], [Q, 'A', 'sag', float('inf'), 'B', 0.5, 0.9, False], [Q, 'A', 'sag', 0, 'B', 1.5, 0.9, False], [Q, 'A', 'sag', 0, 'B', -0.1, 0.9, False], [Q, 'A', 'sag', 0, 'B', True, 0.9, False], [Q, 'A', 'sag', 0, 'B', float('nan'), 0.9, False], [Q, 'A', 'sag', 0, 'B', 0.5, -0.1, False], [Q, 'A', 'sag', 0, 'B', 0.5, 1.5, False], [Q, 'A', 'sag', 0, 'B', 0.5, True, False], [Q, 'A', 'sag', 0, 'B', 0.5, float('nan'), False], [Q, 'A', 'sag', 0, 'B', 0.5, 0.9, 1], [Q, 'A', 'sag', 0, 'B', 0.5, 0.9, None], [{'A': {'x': 'bir'}}, 'A', 'x', 0, 'A', 0.5, 0.9, False]):
    raises(ValueError, q_guncelle, *a, msg='bozuk girdi reddedilir')
```

```hint
Önce hedefi bul: terminalse `r`, değilse `r + gamma * max(Q[s2].values())`. Sonra `Q[s][a] + alpha * (hedef - Q[s][a])`. Tabloyu `copy.deepcopy` ile kopyala.
```
:::

::: gorev 2 · Epsilon-greedy eylem seçimi
`eylem_sec(degerler, epsilon, u, v)` işlevini yaz. Rastgelelik dışarıdan iki sayı olarak verilir; böylece işlev belirlenimci ve sınanabilir olur.

- `degerler`: boş olmayan `{eylem: değer}` sözlüğü; eylem adları `str`. `epsilon`: `[0, 1]` aralığında sayı. `u`, `v`: `[0, 1)` aralığında sayılar.
- `u < epsilon` ise **keşif**: eylemleri alfabetik sırala ve `int(v * eylem_sayısı)` indeksli eylemi seç.
- Değilse **sömürü**: değeri en büyük eylem; eşitlikte alfabetik olarak önce gelen.
- Dönüş: `{'eylem': ..., 'kesif': bool}`.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç her zaman en iyi eylemi seçiyor; `epsilon`'u yok sayıyor. Ajan hiç keşfetmez.

```starter
def eylem_sec(degerler, epsilon, u, v):
    return {'eylem': max(sorted(degerler), key=lambda a: degerler[a]), 'kesif': False}
```

```solution
def eylem_sec(degerler, epsilon, u, v):
    import math
    def sayi(x):
        return not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x)
    if not isinstance(degerler, dict) or not degerler or any(not isinstance(a, str) or not sayi(d) for a, d in degerler.items()):
        raise ValueError('degerler boş olmayan {eylem: değer} sözlüğü olmalı')
    if not sayi(epsilon) or not 0 <= epsilon <= 1:
        raise ValueError('epsilon [0, 1] aralığında olmalı')
    if not sayi(u) or not sayi(v) or not 0 <= u < 1 or not 0 <= v < 1:
        raise ValueError('u ve v [0, 1) aralığında olmalı')
    eylemler = sorted(degerler)
    if u < epsilon:
        return {'eylem': eylemler[int(v * len(eylemler))], 'kesif': True}
    en = eylemler[0]
    for a in eylemler[1:]:
        if degerler[a] > degerler[en]:
            en = a
    return {'eylem': en, 'kesif': False}
```

```test
need('eylem_sec')
import random

D = {'sol': 1.0, 'sag': 5.0, 'bekle': 2.0}
eq(eylem_sec(D, 0.1, 0.5, 0.0), {'eylem': 'sag', 'kesif': False}, 'u >= epsilon: en iyi eylem')
eq(eylem_sec(D, 0.1, 0.05, 0.0), {'eylem': 'bekle', 'kesif': True}, 'u < epsilon: keşif, alfabetik ilk')
eq(eylem_sec(D, 0.1, 0.05, 0.99), {'eylem': 'sol', 'kesif': True}, 'keşif: v büyükse alfabetik son')
eq(eylem_sec(D, 0.1, 0.05, 0.5), {'eylem': 'sag', 'kesif': True}, 'keşif en iyi eylemi de seçebilir')
eq(eylem_sec(D, 0, 0.0, 0.0), {'eylem': 'sag', 'kesif': False}, 'epsilon 0: hiç keşif yok')
eq(eylem_sec(D, 1, 0.999, 0.0)['kesif'], True, 'epsilon 1: hep keşif')
eq(eylem_sec({'b': 2.0, 'a': 2.0}, 0, 0.5, 0.5), {'eylem': 'a', 'kesif': False}, 'eşit değerde alfabetik ilk')
eq(eylem_sec({'tek': -3.0}, 0.5, 0.1, 0.9), {'eylem': 'tek', 'kesif': True}, 'tek eylem')
rng = random.Random(1602)
sayim = {'sol': 0, 'sag': 0, 'bekle': 0}
kesif = 0
for _ in range(4000):
    r = eylem_sec(D, 0.3, rng.random(), rng.random())
    sayim[r['eylem']] += 1
    kesif += r['kesif']
ok(0.27 < kesif / 4000 < 0.33, 'keşif oranı epsilon a yakın', got=kesif / 4000)
ok(0.76 < sayim['sag'] / 4000 < 0.84, 'en iyi eylem: 0.7 + 0.3 / 3 = 0.8 oranında seçilir', got=sayim)
for _ in range(25):
    d = {e: round(rng.uniform(-3, 3), 1) for e in ['a', 'b', 'c', 'd'][:rng.randint(1, 4)]}
    eps, u, v = rng.choice([0, 0.2, 1]), rng.random(), rng.random()
    r = eylem_sec(d, eps, u, v)
    s = sorted(d)
    if u < eps:
        eq(r, {'eylem': s[int(v * len(s))], 'kesif': True}, 'rastgele durumda keşif')
    else:
        eq(r, {'eylem': min(s, key=lambda a: (-d[a], a)), 'kesif': False}, 'rastgele durumda sömürü')
for a in ([None, 0.1, 0.5, 0.5], [['kotu'], 0.1, 0.5, 0.5], [{}, 0.1, 0.5, 0.5], [{'a': '1'}, 0.1, 0.5, 0.5], [{'a': True}, 0.1, 0.5, 0.5], [{'a': float('nan')}, 0.1, 0.5, 0.5], [{'a': float('inf')}, 0.1, 0.5, 0.5], [{1: 1.0}, 0.1, 0.5, 0.5], [D, 1.5, 0.5, 0.5], [D, -0.1, 0.5, 0.5], [D, None, 0.5, 0.5], [D, True, 0.5, 0.5], [D, float('nan'), 0.5, 0.5], [D, 0.1, 1.0, 0.5], [D, 0.1, 0.5, 1.0], [D, 0.1, -0.1, 0.5], [D, 0.1, 0.5, -0.1], [D, 0.1, True, 0.5], [D, 0.1, 0.5, True], [D, 0.1, float('nan'), 0.5], [D, 0.1, 0.5, float('nan')]):
    raises(ValueError, eylem_sec, *a, msg='bozuk girdi reddedilir')
```

```hint
Eylemleri alfabetik sırala. `u < epsilon` ise `eylemler[int(v * n)]`. Değilse sıralı listede gez ve yalnız **kesin büyük** değerde değiştir.
```
:::

::: gorev 3 · Q-learning döngüsü
`q_ogren(ortam, baslangic, bolum, alpha, gamma, epsilon, tohum, maks_adim)` işlevini yaz.

- `ortam`: `{durum: {eylem: (sonraki, ödül, terminal_mi)}}`; boş olmayan; her durumun en az bir eylemi vardır; `sonraki` `ortam`'ın bir anahtarı ya da terminal bir geçişte herhangi bir `str` olabilir.
- `baslangic`: `ortam`'ın bir anahtarı. `bolum`, `maks_adim`: pozitif `int` (`bolum` 0 da olabilir). `tohum`: `int`.
- `Q`, `ortam`'daki her `(durum, eylem)` için 0 ile başlar. `rng = random.Random(tohum)`.
- Her bölüm `baslangic`'tan başlar ve en çok `maks_adim` adım sürer. Her adımda:
  1. `u = rng.random()`, `v = rng.random()` çek (ikisi de **her zaman** çekilir).
  2. Eylemi Görev 2'deki kuralla seç.
  3. `(s2, r, terminal) = ortam[s][a]`; hedef terminalse `r`, değilse `r + gamma · max(Q[s2].values())`.
  4. `Q[s][a] += alpha · (hedef - Q[s][a])`; terminalse bölüm biter, değilse `s = s2`.
- Dönüş: `{'Q': {durum: {eylem: değer}}, 'politika': {durum: en iyi eylem}}`; değerler 6 basamağa yuvarlanır; politikada eşitlikte alfabetik ilk.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç hiç keşfetmiyor (`epsilon` yok sayılıyor): ilk denediği eylem ödül verirse başka yol aramıyor.

```starter
def q_ogren(ortam, baslangic, bolum, alpha, gamma, epsilon, tohum, maks_adim):
    Q = {s: {a: 0.0 for a in e} for s, e in ortam.items()}
    for _ in range(bolum):
        s = baslangic
        for _ in range(maks_adim):
            a = max(sorted(Q[s]), key=lambda x: Q[s][x])
            s2, r, term = ortam[s][a]
            hedef = r if term else r + gamma * max(Q[s2].values())
            Q[s][a] += alpha * (hedef - Q[s][a])
            if term:
                break
            s = s2
    return {'Q': {s: {a: round(v, 6) for a, v in e.items()} for s, e in Q.items()}, 'politika': {s: max(sorted(e), key=lambda x: e[x]) for s, e in Q.items()}}
```

```solution
def q_ogren(ortam, baslangic, bolum, alpha, gamma, epsilon, tohum, maks_adim):
    import math, random
    def sayi(x):
        return not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x)
    if not isinstance(ortam, dict) or not ortam:
        raise ValueError('ortam boş olmayan dict olmalı')
    for s, eylemler in ortam.items():
        if not isinstance(s, str) or not isinstance(eylemler, dict) or not eylemler:
            raise ValueError('her durumun en az bir eylemi olmalı')
        for a, x in eylemler.items():
            if not isinstance(a, str) or not isinstance(x, (tuple, list)) or len(x) != 3 or not isinstance(x[0], str) or not sayi(x[1]) or not isinstance(x[2], bool):
                raise ValueError('geçiş (sonraki, ödül, terminal) olmalı')
            if not x[2] and x[0] not in ortam:
                raise ValueError('terminal olmayan geçiş bilinen bir duruma gitmeli')
    if baslangic not in ortam:
        raise ValueError('baslangic ortamda yok')
    if isinstance(bolum, bool) or not isinstance(bolum, int) or bolum < 0 or isinstance(maks_adim, bool) or not isinstance(maks_adim, int) or maks_adim < 1:
        raise ValueError('bolum >= 0 ve maks_adim >= 1 int olmalı')
    if isinstance(tohum, bool) or not isinstance(tohum, int):
        raise ValueError('tohum int olmalı')
    for x in (alpha, gamma, epsilon):
        if not sayi(x) or not 0 <= x <= 1:
            raise ValueError('alpha, gamma ve epsilon [0, 1] aralığında olmalı')
    rng = random.Random(tohum)
    Q = {s: {a: 0.0 for a in e} for s, e in ortam.items()}

    def en_iyi(s):
        eylemler = sorted(Q[s])
        en = eylemler[0]
        for a in eylemler[1:]:
            if Q[s][a] > Q[s][en]:
                en = a
        return en

    for _ in range(bolum):
        s = baslangic
        for _ in range(maks_adim):
            u, v = rng.random(), rng.random()
            eylemler = sorted(Q[s])
            a = eylemler[int(v * len(eylemler))] if u < epsilon else en_iyi(s)
            s2, r, term = ortam[s][a]
            hedef = r if term else r + gamma * max(Q[s2].values())
            Q[s][a] += alpha * (hedef - Q[s][a])
            if term:
                break
            s = s2
    return {'Q': {s: {a: round(v, 6) for a, v in e.items()} for s, e in Q.items()}, 'politika': {s: en_iyi(s) for s in Q}}
```

```test
need('q_ogren')
import random

ortam = {
    'A': {'hemen': ('son', 1, True), 'sabret': ('B', 0, False)},
    'B': {'geri': ('A', 0, False), 'ileri': ('son', 10, True)},
}
r0 = q_ogren(ortam, 'A', 0, 0.5, 0.9, 0.2, 1, 20)
eq(r0['Q'], {'A': {'hemen': 0.0, 'sabret': 0.0}, 'B': {'geri': 0.0, 'ileri': 0.0}}, 'sıfır bölüm: tablo sıfır')
acgozlu = q_ogren(ortam, 'A', 300, 0.5, 0.9, 0.0, 1, 20)
eq(acgozlu['politika']['A'], 'hemen', 'keşifsiz ajan ilk bulduğu küçük ödüle saplanır')
eq(acgozlu['Q']['B']['ileri'], 0.0, 'büyük ödüllü geçişi hiç denememiştir')
kasif = q_ogren(ortam, 'A', 300, 0.5, 0.9, 0.3, 1, 20)
eq(kasif['politika'], {'A': 'sabret', 'B': 'ileri'}, 'keşfeden ajan büyük ödüle giden yolu bulur')
yakin(kasif['Q']['B']['ileri'], 10.0, 'Q(B, ileri) 10 a yakınsar', tol=1e-3)
yakin(kasif['Q']['A']['sabret'], 9.0, 'Q(A, sabret) gamma · 10 = 9 a yakınsar', tol=1e-2)
yakin(kasif['Q']['A']['hemen'], 1.0, 'Q(A, hemen) 1 e yakınsar', tol=1e-3)
eq(q_ogren(ortam, 'A', 300, 0.5, 0.9, 0.3, 1, 20), kasif, 'aynı tohum aynı sonucu verir')
def _ref(ortam, bas, bolum, alpha, gamma, eps, tohum, maks):
    g = random.Random(tohum)
    Q = {s: dict.fromkeys(e, 0.0) for s, e in ortam.items()}
    for _ in range(bolum):
        s = bas
        for _ in range(maks):
            u = g.random()
            v = g.random()
            es = sorted(Q[s])
            a = es[int(v * len(es))] if u < eps else min(es, key=lambda x: (-Q[s][x], x))
            s2, r, t = ortam[s][a]
            Q[s][a] = Q[s][a] + alpha * ((r if t else r + gamma * max(Q[s2].values())) - Q[s][a])
            if t:
                break
            s = s2
    return Q
rng = random.Random(1603)
for _ in range(12):
    ds = [f"s{i}" for i in range(rng.randint(1, 4))]
    o = {}
    for s in ds:
        o[s] = {}
        for a in ['x', 'y', 'z'][:rng.randint(1, 3)]:
            term = rng.random() < 0.3
            o[s][a] = ('bitis' if term else rng.choice(ds), rng.randint(-2, 5), term)
    args = (o, ds[0], rng.randint(0, 25), rng.choice([0.1, 0.5, 1]), rng.choice([0, 0.9]), rng.choice([0, 0.3, 1]), rng.randint(0, 999), rng.randint(1, 12))
    got, exp = q_ogren(*args), _ref(*args)
    for s in ds:
        for a in o[s]:
            yakin(got['Q'][s][a], exp[s][a], 'rastgele ortamda bağımsız referansla aynı', tol=2e-6)
        eq(got['politika'][s], min(sorted(exp[s]), key=lambda x: (-round(exp[s][x], 6), x)) if len({round(v, 6) for v in exp[s].values()}) == len(exp[s]) else got['politika'][s], 'politika en büyük Q değerli eylem')
iyi = {'A': {'x': ('son', 1, True)}}
eq(q_ogren(ortam, 'A', 1, 0.5, 0.9, 0.0, 1, 1)['Q']['A']['hemen'], 0.5, 'maks_adim = 1 sınırı')
for a in ([None, 'A', 1, 0.5, 0.9, 0.1, 0, 5], [['A'], 'A', 1, 0.5, 0.9, 0.1, 0, 5], [{}, 'A', 1, 0.5, 0.9, 0.1, 0, 5], [{1: {'x': ('son', 1, True)}}, 1, 1, 0.5, 0.9, 0.1, 0, 5], [{'A': []}, 'A', 1, 0.5, 0.9, 0.1, 0, 5], [{'A': {1: ('son', 1, True)}}, 'A', 1, 0.5, 0.9, 0.1, 0, 5], [{'A': {'x': 'kotu'}}, 'A', 1, 0.5, 0.9, 0.1, 0, 5], [{'A': {'x': {1, 2, 3}}}, 'A', 1, 0.5, 0.9, 0.1, 0, 5], [{'A': {'x': (1, 1, True)}}, 'A', 1, 0.5, 0.9, 0.1, 0, 5], [{'A': {'x': ('son', True, True)}}, 'A', 1, 0.5, 0.9, 0.1, 0, 5], [{'A': {'x': ('son', float('nan'), True)}}, 'A', 1, 0.5, 0.9, 0.1, 0, 5], [{'A': {'x': ('son', float('inf'), True)}}, 'A', 1, 0.5, 0.9, 0.1, 0, 5], [iyi, 'yok', 1, 0.5, 0.9, 0.1, 0, 5], [iyi, 'A', -1, 0.5, 0.9, 0.1, 0, 5], [iyi, 'A', 1.0, 0.5, 0.9, 0.1, 0, 5], [iyi, 'A', True, 0.5, 0.9, 0.1, 0, 5], [iyi, 'A', 1, 1.5, 0.9, 0.1, 0, 5], [iyi, 'A', 1, -0.1, 0.9, 0.1, 0, 5], [iyi, 'A', 1, True, 0.9, 0.1, 0, 5], [iyi, 'A', 1, float('nan'), 0.9, 0.1, 0, 5], [iyi, 'A', 1, 0.5, None, 0.1, 0, 5], [iyi, 'A', 1, 0.5, 0.9, 2, 0, 5], [iyi, 'A', 1, 0.5, 0.9, 0.1, 1.5, 5], [iyi, 'A', 1, 0.5, 0.9, 0.1, True, 5], [iyi, 'A', 1, 0.5, 0.9, 0.1, 0, 0], [iyi, 'A', 1, 0.5, 0.9, 0.1, 0, True], [iyi, 'A', 1, 0.5, 0.9, 0.1, 0, 1.5], [{'A': {}}, 'A', 1, 0.5, 0.9, 0.1, 0, 5], [{'A': {'x': ('yok', 1, False)}}, 'A', 1, 0.5, 0.9, 0.1, 0, 5], [{'A': {'x': ('son', 1)}}, 'A', 1, 0.5, 0.9, 0.1, 0, 5], [{'A': {'x': ('son', 1, 1)}}, 'A', 1, 0.5, 0.9, 0.1, 0, 5]):
    raises(ValueError, q_ogren, *a, msg='bozuk girdi reddedilir')
```

```hint
Dış döngü bölümler, iç döngü adımlar. Her adımda önce `u` ve `v`'yi çek, eylemi seç, ortamdan sonucu al, hedefi hesapla, hücreyi güncelle. Terminalse `break`.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur; her adım bu derste hesapladığın bir sayıya ya da örneğe dayanır.

1. **Çerçeve (15 sn).** "Harita yok; ajan yalnız dener ve sonucu görür."
2. **Devralma (30 sn).** Tahmin adımı: A hiç ödül almadı ama değeri 2,25 oldu; B'nin tahmininden devraldı. "Ödül geriye, bölüm bölüm yayılır."
3. **Keşif (30 sn).** "Hep bildiği en iyi şeyi yapan ajan, ilk bulduğu küçük ödüle saplanır ve büyüğünü hiç görmez. Biraz rastgelelik şarttır."
4. **Sınır (25 sn).** "Her durum için bir tablo satırı gerekir; bir satranç tahtası ya da bir sohbet geçmişi için tablo tutulamaz."
5. **Kapanış (20 sn).** "Deneyerek öğrenmenin bedeli, kötü denemelerdir. Gerçek dünyada bu bedel kimin cebinden çıkıyor, sorun."
:::

::: anlat Sınır
Bu ders tablo tabanlı Q-learning'i belirlenimci, küçük ortamlarda anlatır. Tablo, her durum-eylem çifti için bir hücre ister; durum sayısı büyüdüğünde ya da durumlar sürekli olduğunda tablo tutulamaz ve yerini bir sinir ağı alır (bkz. `ai-matematik-17`). Q-learning'in en iyi değerlere yakınsaması, her durum-eylem çiftinin sonsuz kez denenmesini ve öğrenme oranının uygun biçimde azaltılmasını gerektirir; sabit `alpha` ve sonlu bölümle değerler yalnız yaklaşıktır. Hedefteki `max`, gürültülü tahminlerde değerleri sistemli olarak **büyütür** (`maximization bias`); `Double Q-learning` bunu azaltır. Epsilon-greedy kör bir keşiftir: hiç denenmemiş eylem ile kötü olduğu bilinen eylemi ayırt etmez; seyrek ödüllü, uzun görevlerde yetersiz kalır. Görevlerdeki ortamlar belirlenimcidir; rastgele geçişlerde `alpha = 1` öğrenmeyi bozar. Ajan yalnız verilen ödülü büyütür: ödül kastedilen amacı tam yansıtmıyorsa ajan ödülü toplayan ama amacı gerçekleştirmeyen bir davranış öğrenebilir (`specification gaming`, bkz. `ai-guvence-42`).

Kaynaklar: [Watkins ve Dayan 1992 - Q-learning](https://doi.org/10.1007/BF00992698), [Sutton ve Barto 2018 - Reinforcement Learning: An Introduction, Bölüm 6](http://incompleteideas.net/book/the-book-2nd.html), [van Hasselt 2010 - Double Q-learning](https://papers.nips.cc/paper/2010/hash/091d584fced301b442654dd8c23b3fc9-Abstract.html).
:::

::: dusun
Görev 3'te keşifsiz ajan `A`'da `hemen` eylemine saplandı ve `Q(B, ileri)` sıfır kaldı. Tabloyu sıfır yerine bütün hücrelerde 20 ile başlatsaydın (`optimistic initialization`), keşifsiz ajan ne yapardı? Neden? Bu hile hangi tür ortamda işe yaramaz?
:::

::: ozet
- Q-learning geçiş modelini bilmeden, `(s, a, r, s')` deneyimlerinden durum-eylem değerlerini öğrenir.
- Güncelleme TD hatasının `alpha` kadarını düzeltir; hedef `r + γ max Q(s', ·)`, terminal geçişte yalnız `r`'dir.
- Hedefteki `max` yöntemi off-policy yapar: ajan rastgele dolaşırken en iyi politikanın değerlerini öğrenir.
- Keşif olmadan ajan ilk bulduğu ödüle saplanır; `epsilon-greedy` en basit çözümdür.
- Ödül geriye bölüm bölüm yayılır; tablo büyük durum uzaylarına ölçeklenmez.
:::
