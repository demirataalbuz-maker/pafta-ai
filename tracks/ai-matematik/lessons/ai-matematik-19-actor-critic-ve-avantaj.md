---
id: ai-matematik-19
title: "Actor-Critic ve Avantaj · Eleştirmen Oyuncuya Ne Söyler?"
summary: Tek adımlı TD avantajını, Generalized Advantage Estimation'ı ve bir actor-critic güncellemesini yaz; bias ile varyans arasındaki ödünleşimin lambda ile nasıl ayarlandığını ölç.
---

::: anlat 1. İki rol
`ai-matematik-18`'deki REINFORCE iki sorunla kaldı: tahmin çok gürültülüydü ve güncelleme için bölümün bitmesini beklemek gerekiyordu. `Actor-critic` yöntemleri ikisini de çözer; politika gradient'i ile değer öğrenmeyi birleştirir.

- **Actor** (oyuncu): politika $\pi_\theta(a \mid s)$. Eylemi seçer.
- **Critic** (eleştirmen): değer fonksiyonu $V(s)$. Durumun ne kadar iyi olduğunu tahmin eder ve oyuncuya "beklediğimden iyi miydi, kötü müydü?" der.

Eleştirmenin söylediği şey **avantajdır**: $A(s, a) = Q(s, a) - V(s)$. Eylemin, o durumdaki ortalama eylemden ne kadar iyi olduğu. Pozitifse eylemin olasılığı artırılır, negatifse azaltılır. Bu, REINFORCE'taki sabit baseline'ın **duruma bağlı** hâlidir.

| Soru | Araç | Görev |
|---|---|---|
| Tek bir adımdan avantaj nasıl tahmin edilir? | TD hatası $\delta$ | 1 |
| Bir adım mı, bütün bölüm mü; arası var mı? | `GAE` ($\lambda$) | 2 |
| Oyuncu ve eleştirmen birlikte nasıl güncellenir? | Actor-critic adımı | 3 |
:::

::: anlat 2. TD avantajı, GAE ve güncelleme
**Tek adımlı avantaj.** $Q(s, a)$ bilinmez; ama bir adım atıp sonucu görürsen onu tahmin edebilirsin: $Q(s, a) \approx r + \gamma V(s')$. Buradan avantaj tahmini TD hatasının kendisidir:

$$\delta = r + \gamma V(s') - V(s)$$

Bölüm bittiyse $V(s') = 0$ alınır. Bu tahmin **düşük varyanslıdır** (tek bir adımın rastgeleliğini taşır) ama **yanlıdır**: eleştirmenin $V$ tahmini yanlışsa avantaj da yanlıştır.

Öbür uçta Monte Carlo tahmini vardır: bölümün sonuna kadarki gerçek getiriden $V(s)$'yi çıkarmak. Yansızdır ama bütün bölümün rastgeleliğini taşır: yüksek varyans.

**GAE** (Generalized Advantage Estimation) ikisinin arasını bir düğmeyle ayarlar. TD hatalarının üstel ağırlıklı toplamıdır:

$$\hat{A}_t = \sum_{k=0}^{T-t-1} (\gamma\lambda)^k\, \delta_{t+k}$$

- $\lambda = 0$: yalnız $\delta_t$; tek adımlı TD (düşük varyans, yüksek bias).
- $\lambda = 1$: bütün TD hatalarının toplamı; Monte Carlo avantajına eşittir (yansız, yüksek varyans).
- Pratikte $\lambda \approx 0{,}95$ kullanılır.

Özyinelemeli hesaplanır, sondan başa: $\hat{A}_t = \delta_t + \gamma\lambda\, \hat{A}_{t+1}$. Eleştirmenin hedefi de buradan çıkar: $\text{getiri}_t = \hat{A}_t + V(s_t)$.

**Güncelleme.** Her adımda iki şey olur:

$$V(s) \leftarrow V(s) + \alpha_c\, \delta \qquad \theta \leftarrow \theta + \alpha_a\, \delta\, \nabla_\theta \log \pi_\theta(a \mid s)$$

Eleştirmen kendi tahminini TD hatası yönünde düzeltir (bkz. `ai-matematik-16`); oyuncu aynı hatayı avantaj olarak kullanır (bkz. `ai-matematik-18`). Bölümün bitmesi beklenmez.
:::

::: tahmin Beklenenden iyi mi, kötü mü?
Eleştirmen bulunulan durumun değerini 5, varılan durumunkini 4 sanıyor. Ajan 3 ödül aldı; `gamma = 0.9`. TD avantajı ne yazdırılır? Aynı adımda ödül 1 olsaydı?

```python
gamma, v_s, v_s2 = 0.9, 5.0, 4.0
for r in (3.0, 1.0):
    delta = r + gamma * v_s2 - v_s
    print(r, round(delta, 2))
```

???

```cikti
3.0 1.6
1.0 -0.4
```
Ödül 3 iken bir adımlık kanıt $3 + 0{,}9 \times 4 = 6{,}6$ diyor; eleştirmen 5 bekliyordu. Avantaj $+1{,}6$: eylem beklenenden iyiydi, olasılığı artırılır ve eleştirmen `V(s)`'yi yukarı çeker. Ödül 1 iken kanıt $4{,}6$'dır; avantaj $-0{,}4$: eylem beklenenden kötüydü. Ödül iki durumda da pozitifti; önemli olan ödülün işareti değil, **beklentiye göre** nerede durduğudur.
:::

::: gorev 1 · Tek adımlı TD avantajı
`td_avantaji(r, v_s, v_s2, gamma, bitti)` işlevini yaz.

- `r`, `v_s`, `v_s2`: sayı. `gamma`: `[0, 1]` aralığında sayı. `bitti`: `bool`.
- `bitti` ise `delta = r - v_s`; değilse `delta = r + gamma · v_s2 - v_s`.
- Dönüş: `float`, 9 basamağa yuvarlanmış.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç `V(s)`'yi çıkarmıyor: TD **hedefini** avantaj diye döndürüyor. Bütün eylemler "iyi" görünür.

```starter
def td_avantaji(r, v_s, v_s2, gamma, bitti):
    return round(r + gamma * v_s2, 9)
```

```solution
def td_avantaji(r, v_s, v_s2, gamma, bitti):
    import math
    for x in (r, v_s, v_s2, gamma):
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
            raise ValueError('sayı bekleniyor')
    if not 0 <= gamma <= 1:
        raise ValueError('gamma [0, 1] aralığında olmalı')
    if not isinstance(bitti, bool):
        raise ValueError('bitti bool olmalı')
    hedef = r if bitti else r + gamma * v_s2
    return round(float(hedef - v_s), 9)
```

```test
need('td_avantaji')
import random

eq(td_avantaji(3.0, 5.0, 4.0, 0.9, False), 1.6, 'beklenenden iyi: pozitif avantaj')
eq(td_avantaji(1.0, 5.0, 4.0, 0.9, False), -0.4, 'beklenenden kötü: ödül pozitif olsa da negatif avantaj')
eq(td_avantaji(3.0, 5.0, 4.0, 0.9, True), -2.0, 'bölüm bittiyse sonraki durumun değeri sayılmaz')
eq(td_avantaji(2.0, 2.0, 0.0, 0.9, False), 0.0, 'tam beklendiği gibi: avantaj sıfır')
eq(td_avantaji(0, 0, 10, 0, False), 0.0, 'gamma 0: gelecek sayılmaz')
ok(isinstance(td_avantaji(1, 0, 0, 1, True), float), 'dönüş float')
rng = random.Random(1901)
for _ in range(30):
    r, v, v2 = (round(rng.uniform(-5, 5), 2) for _ in range(3))
    g, b = rng.choice([0, 0.5, 0.99, 1]), rng.random() < 0.3
    yakin(td_avantaji(r, v, v2, g, b), (r - v) if b else (r + g * v2 - v), 'rastgele değerlerde bağımsız hesapla aynı', tol=1e-8)
eq(td_avantaji(1 / 3, 0, 0, 1, True), 0.333333333, '9 basamağa yuvarlanır')
for a in ([None, 1, 1, 0.9, False], [1, "1", 1, 0.9, False], [1, 1, True, 0.9, False], [float('nan'), 1, 1, 0.9, False], [1, float('inf'), 1, 0.9, False], [1, 1, float('nan'), 0.9, False], [1, 1, 1, float('nan'), False], [1, 1, 1, 1.5, False], [1, 1, 1, -0.1, False], [1, 1, 1, None, False], [1, 1, 1, 0.9, 0], [1, 1, 1, 0.9, None]):
    raises(ValueError, td_avantaji, *a, msg='bozuk girdi reddedilir')
```

```hint
Önce hedefi bul: bittiyse `r`, değilse `r + gamma * v_s2`. Avantaj hedef eksi `v_s`'dir.
```
:::

::: gorev 2 · Generalized Advantage Estimation
`gae(oduller, degerler, son_deger, gamma, lam)` işlevini yaz.

- `oduller`: `T` uzunlukta boş olmayan sayı listesi. `degerler`: aynı uzunlukta; `degerler[t]`, `t` anındaki durumun eleştirmen tahmini $V(s_t)$.
- `son_deger`: son adımdan sonra varılan durumun değeri; bölüm bittiyse `0` verilir.
- `gamma`, `lam`: `[0, 1]` aralığında sayı.
- `delta_t = oduller[t] + gamma · V(s_{t+1}) - degerler[t]`; son adımda `V(s_{t+1}) = son_deger`.
- Sondan başa: `A_t = delta_t + gamma · lam · A_{t+1}` (`A_T = 0`).
- Dönüş: `{'avantajlar': [...], 'getiriler': [A_t + degerler[t]]}`; 9 basamağa yuvarlanır (yuvarlama yalnız çıktıda).
- Bozuk girdi `ValueError`.

KUSURLU başlangıç yalnız tek adımlı TD hatalarını döndürüyor; `lam`'ı yok sayıyor. Sonraki adımlardaki sürprizler önceki eylemlere hiç yansımıyor.

```starter
def gae(oduller, degerler, son_deger, gamma, lam):
    sonraki = degerler[1:] + [son_deger]
    adv = [round(r + gamma * v2 - v, 9) for r, v, v2 in zip(oduller, degerler, sonraki)]
    return {'avantajlar': adv, 'getiriler': [round(a + v, 9) for a, v in zip(adv, degerler)]}
```

```solution
def gae(oduller, degerler, son_deger, gamma, lam):
    import math
    def sayi(x):
        return not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x)
    for v in (oduller, degerler):
        if not isinstance(v, list) or not v or not all(sayi(x) for x in v):
            raise ValueError('boş olmayan sayı listesi gerekli')
    if len(oduller) != len(degerler):
        raise ValueError('oduller ve degerler aynı uzunlukta olmalı')
    if not sayi(son_deger) or not sayi(gamma) or not sayi(lam) or not 0 <= gamma <= 1 or not 0 <= lam <= 1:
        raise ValueError('son_deger sayı; gamma ve lam [0, 1] aralığında olmalı')
    T = len(oduller)
    adv = [0.0] * T
    birikim = 0.0
    for t in range(T - 1, -1, -1):
        sonraki = son_deger if t == T - 1 else degerler[t + 1]
        delta = oduller[t] + gamma * sonraki - degerler[t]
        birikim = delta + gamma * lam * birikim
        adv[t] = birikim
    return {'avantajlar': [round(a, 9) for a in adv], 'getiriler': [round(a + v, 9) for a, v in zip(adv, degerler)]}
```

```test
need('gae')
import math, random

r = gae([1.0, 1.0, 1.0], [0.0, 0.0, 0.0], 0.0, 1.0, 1.0)
eq(r['avantajlar'], [3.0, 2.0, 1.0], 'lam 1, değerler 0: avantaj kalan getiridir (Monte Carlo)')
eq(r['getiriler'], [3.0, 2.0, 1.0], 'getiri = avantaj + değer')
r = gae([1.0, 1.0, 1.0], [0.0, 0.0, 0.0], 0.0, 1.0, 0.0)
eq(r['avantajlar'], [1.0, 1.0, 1.0], 'lam 0: yalnız tek adımlı TD hatası')
r = gae([0.0, 0.0, 10.0], [0.0, 0.0, 0.0], 0.0, 1.0, 0.5)
eq(r['avantajlar'], [2.5, 5.0, 10.0], 'sondaki sürpriz geriye lam ile yarılanarak yayılır')
r = gae([1.0, 1.0], [2.0, 1.0], 0.0, 1.0, 1.0)
eq(r['avantajlar'], [0.0, 0.0], 'eleştirmen kusursuzsa avantaj sıfır')
r = gae([1.0], [0.0], 5.0, 0.9, 0.95)
eq(r['avantajlar'], [5.5], 'bölüm bitmediyse son değer bootstrap edilir: 1 + 0.9 · 5')
rng = random.Random(1902)
for _ in range(25):
    T = rng.randint(1, 12)
    od = [round(rng.uniform(-2, 2), 2) for _ in range(T)]
    V = [round(rng.uniform(-2, 2), 2) for _ in range(T)]
    son, g, l = round(rng.uniform(-2, 2), 2), rng.choice([0.5, 0.9, 0.99, 1]), rng.choice([0, 0.5, 0.95, 1])
    got = gae(od, V, son, g, l)
    Vn = V[1:] + [son]
    d = [od[t] + g * Vn[t] - V[t] for t in range(T)]
    for t in range(T):
        yakin(got['avantajlar'][t], math.fsum((g * l) ** k * d[t + k] for k in range(T - t)), 'doğrudan toplamla aynı', tol=1e-7)
        yakin(got['getiriler'][t], got['avantajlar'][t] + V[t], 'getiri = avantaj + değer', tol=1e-8)
    mc = gae(od, V, son, g, 1)
    for t in range(T):
        G = math.fsum(g ** k * od[t + k] for k in range(T - t)) + g ** (T - t) * son
        yakin(mc['avantajlar'][t], G - V[t], 'lam 1: getiri eksi değer', tol=1e-7)
    td = gae(od, V, son, g, 0)
    for t in range(T):
        yakin(td['avantajlar'][t], d[t], 'lam 0: tek adımlı TD hatası', tol=1e-8)
eq(gae([1.0, 2.0], [0.5, 0.5], 0.0, 0, 0.5), {'avantajlar': [0.5, 1.5], 'getiriler': [1.0, 2.0]}, 'gamma 0 geçerlidir: avantaj anlık ödül eksi değerdir')
od, V = [1.0, 2.0], [0.5, 0.5]
gae(od, V, 0.0, 0.9, 0.9)
eq((od, V), ([1.0, 2.0], [0.5, 0.5]), 'girdiler değişmez')
for a in ([None, [1.0], 0, 0.9, 0.9], [[1.0], None, 0, 0.9, 0.9], [[], [1.0], 0, 0.9, 0.9], [[1.0], [], 0, 0.9, 0.9], [[], [], 0, 0.9, 0.9], [[1.0, 2.0], [1.0], 0, 0.9, 0.9], [[1, "2"], [1, 2], 0, 0.9, 0.9], [[True], [1.0], 0, 0.9, 0.9], [[float('nan')], [1.0], 0, 0.9, 0.9], [[1.0], [float('inf')], 0, 0.9, 0.9], [[1.0], [1.0], None, 0.9, 0.9], [[1.0], [1.0], True, 0.9, 0.9], [[1.0], [1.0], float('nan'), 0.9, 0.9], [[1.0], [1.0], 0, 1.5, 0.9], [[1.0], [1.0], 0, -0.1, 0.9], [[1.0], [1.0], 0, True, 0.9], [[1.0], [1.0], 0, float('nan'), 0.9], [[1.0], [1.0], 0, 0.9, -0.1], [[1.0], [1.0], 0, 0.9, 1.5], [[1.0], [1.0], 0, 0.9, True], [[1.0], [1.0], 0, 0.9, float('nan')], [[1.0], [1.0], 0, 0.9, None], [(1.0,), [1.0], 0, 0.9, 0.9]):
    raises(ValueError, gae, *a, msg='bozuk girdi reddedilir')
```

```hint
Sondan başa tek döngü. Her adımda `delta`'yı hesapla, sonra `birikim = delta + gamma * lam * birikim`. Son adımda sonraki değer `son_deger`'dir.
```
:::

::: gorev 3 · Actor-critic güncelleme adımı
`actor_critic_adimi(logitler, V, gecis, lr_actor, lr_critic, gamma)` işlevini yaz. Durumlar ve eylemler tabloludur.

- `logitler`: `{durum: [eylem logit'leri]}`; her liste boş olmayan sayı listesi. `V`: `{durum: değer}`; `logitler` ile **aynı** durum anahtarlarına sahip.
- `gecis`: `(s, a, r, s2, bitti)`; `s` tabloda bir durum, `a` o durumda geçerli eylem indeksi, `r` sayı, `bitti` `bool`. `bitti` değilse `s2` de tabloda olmalıdır.
- `lr_actor`, `lr_critic`: pozitif sayı. `gamma`: `[0, 1]`.
- `delta`: Görev 1'deki TD avantajı (güncellemeden önceki `V` ile).
- Eleştirmen: `V[s] += lr_critic · delta`.
- Oyuncu: `logitler[s][k] += lr_actor · delta · ((k == a) - pi[k])`; `pi`, `logitler[s]`'nin softmax'idir (güncellemeden önce).
- Dönüş: `{'logitler': ..., 'V': ..., 'delta': ...}`; derin kopyalar; değişen değerler 9 basamağa yuvarlanır. Girdiler değişmemelidir.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç oyuncuyu avantajla değil **ham ödülle** güncelliyor: eleştirmen öğreniyor ama söyledikleri oyuncuya ulaşmıyor.

```starter
def actor_critic_adimi(logitler, V, gecis, lr_actor, lr_critic, gamma):
    import copy, math
    s, a, r, s2, bitti = gecis
    delta = r - V[s] if bitti else r + gamma * V[s2] - V[s]
    L, W = copy.deepcopy(logitler), dict(V)
    en = max(L[s])
    u = [math.exp(x - en) for x in L[s]]
    pi = [x / sum(u) for x in u]
    W[s] = round(V[s] + lr_critic * delta, 9)
    L[s] = [round(x + lr_actor * r * ((1.0 if k == a else 0.0) - pi[k]), 9) for k, x in enumerate(L[s])]
    return {'logitler': L, 'V': W, 'delta': round(delta, 9)}
```

```solution
def actor_critic_adimi(logitler, V, gecis, lr_actor, lr_critic, gamma):
    import copy, math
    def sayi(x):
        return not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x)
    if not isinstance(logitler, dict) or not logitler or not isinstance(V, dict) or set(logitler) != set(V):
        raise ValueError('logitler ve V aynı durumlara sahip dict olmalı')
    for s0, l in logitler.items():
        if not isinstance(l, list) or not l or not all(sayi(x) for x in l) or not sayi(V[s0]):
            raise ValueError('logit listeleri ve değerler sayı olmalı')
    if not isinstance(gecis, (tuple, list)) or len(gecis) != 5:
        raise ValueError('gecis (s, a, r, s2, bitti) olmalı')
    s, a, r, s2, bitti = gecis
    if not isinstance(bitti, bool) or s not in logitler or (not bitti and s2 not in logitler):
        raise ValueError('durum tabloda yok ya da bitti bool değil')
    if isinstance(a, bool) or not isinstance(a, int) or not 0 <= a < len(logitler[s]) or not sayi(r):
        raise ValueError('eylem ya da ödül geçersiz')
    if not sayi(lr_actor) or not sayi(lr_critic) or not lr_actor > 0 or not lr_critic > 0 or not sayi(gamma) or not 0 <= gamma <= 1:
        raise ValueError('öğrenme oranları pozitif, gamma [0, 1] aralığında olmalı')
    delta = (r if bitti else r + gamma * V[s2]) - V[s]
    en = max(logitler[s])
    ustel = [math.exp(x - en) for x in logitler[s]]
    z = sum(ustel)
    pi = [u / z for u in ustel]
    yeni_l, yeni_v = copy.deepcopy(logitler), dict(V)
    yeni_v[s] = round(V[s] + lr_critic * delta, 9)
    yeni_l[s] = [round(x + lr_actor * delta * ((1.0 if k == a else 0.0) - pi[k]), 9) for k, x in enumerate(logitler[s])]
    return {'logitler': yeni_l, 'V': yeni_v, 'delta': round(float(delta), 9)}
```

```test
need('actor_critic_adimi')
import copy, math, random

L = {'A': [0.0, 0.0], 'B': [0.0, 0.0]}
V = {'A': 5.0, 'B': 4.0}
r = actor_critic_adimi(L, V, ('A', 0, 3.0, 'B', False), 1.0, 0.5, 0.9)
eq(r['delta'], 1.6, 'TD avantajı')
eq(r['V'], {'A': 5.8, 'B': 4.0}, 'eleştirmen yalnız bulunulan durumu düzeltir')
eq(r['logitler'], {'A': [0.8, -0.8], 'B': [0.0, 0.0]}, 'oyuncu avantajla güncellenir: 1.6 · 0.5')
r = actor_critic_adimi(L, V, ('A', 0, 1.0, 'B', False), 1.0, 0.5, 0.9)
eq(r['logitler']['A'], [-0.2, 0.2], 'ödül pozitif ama avantaj negatif: seçilen eylemin olasılığı düşer')
r = actor_critic_adimi(L, V, ('A', 1, 3.0, 'yok', True), 1.0, 1.0, 0.9)
eq((r['delta'], r['V']['A']), (-2.0, 3.0), 'bölüm bittiyse s2 kullanılmaz ve tabloda olması gerekmez')
r = actor_critic_adimi({'A': [0.0, 0.0]}, {'A': 2.0}, ('A', 0, 2.0, 'A', True), 1.0, 1.0, 0.9)
eq(r, {'logitler': {'A': [0.0, 0.0]}, 'V': {'A': 2.0}, 'delta': 0.0}, 'eleştirmen haklıysa hiçbir şey değişmez')
eskiL, eskiV = copy.deepcopy(L), dict(V)
r = actor_critic_adimi(L, V, ('A', 0, 3.0, 'B', False), 1.0, 0.5, 0.9)
eq((L, V), (eskiL, eskiV), 'girdiler değişmez')
r['logitler']['B'][0] = 99
eq(L['B'][0], 0.0, 'dönüş derin kopyadır')
rng = random.Random(1903)
for _ in range(20):
    ds = [f"s{i}" for i in range(rng.randint(1, 4))]
    Lr = {d: [round(rng.uniform(-2, 2), 2) for _ in range(rng.randint(1, 4))] for d in ds}
    Vr = {d: round(rng.uniform(-3, 3), 2) for d in ds}
    s, s2 = rng.choice(ds), rng.choice(ds)
    a = rng.randrange(len(Lr[s]))
    od, b = round(rng.uniform(-3, 3), 2), rng.random() < 0.3
    la, lc, g = rng.choice([0.01, 0.1, 1.0]), rng.choice([0.01, 0.1, 1.0]), rng.choice([0, 0.9, 1])
    got = actor_critic_adimi(Lr, Vr, (s, a, od, s2, b), la, lc, g)
    delta = (od - Vr[s]) if b else (od + g * Vr[s2] - Vr[s])
    m = max(Lr[s])
    u = [math.exp(x - m) for x in Lr[s]]
    pi = [x / sum(u) for x in u]
    yakin(got['delta'], delta, 'rastgele tabloda delta', tol=1e-8)
    yakin(got['V'][s], Vr[s] + lc * delta, 'rastgele tabloda eleştirmen', tol=1e-8)
    for k in range(len(pi)):
        yakin(got['logitler'][s][k], Lr[s][k] + la * delta * ((1 if k == a else 0) - pi[k]), 'rastgele tabloda oyuncu', tol=1e-8)
    for d in ds:
        if d != s:
            eq((got['logitler'][d], got['V'][d]), (Lr[d], Vr[d]), 'diğer durumlar aynı')
eq(actor_critic_adimi({'A': [1000.0, 1000.0]}, {'A': 0.0}, ('A', 0, 2.0, 'A', True), 1.0, 0.5, 0.9), {'logitler': {'A': [1001.0, 999.0]}, 'V': {'A': 1.0}, 'delta': 2.0}, 'büyük logit lerde kararlı softmax')
iyiL, iyiV, iyiG = {'A': [0.0]}, {'A': 0.0}, ('A', 0, 1.0, 'A', False)
for a in ([None, iyiV, iyiG, 0.1, 0.1, 0.9], [['A'], iyiV, iyiG, 0.1, 0.1, 0.9], [{}, {}, iyiG, 0.1, 0.1, 0.9], [iyiL, None, iyiG, 0.1, 0.1, 0.9], [iyiL, {'B': 0.0}, iyiG, 0.1, 0.1, 0.9], [{'A': []}, iyiV, iyiG, 0.1, 0.1, 0.9], [{'A': (0.0,)}, iyiV, iyiG, 0.1, 0.1, 0.9], [{'A': [True]}, iyiV, iyiG, 0.1, 0.1, 0.9], [{'A': [float('nan')]}, iyiV, iyiG, 0.1, 0.1, 0.9], [iyiL, {'A': '0'}, iyiG, 0.1, 0.1, 0.9], [iyiL, {'A': True}, iyiG, 0.1, 0.1, 0.9], [iyiL, {'A': float('inf')}, iyiG, 0.1, 0.1, 0.9], [iyiL, iyiV, 'kotu', 0.1, 0.1, 0.9], [iyiL, iyiV, 123, 0.1, 0.1, 0.9], [iyiL, iyiV, ('A', 0, 1.0, 'A'), 0.1, 0.1, 0.9], [iyiL, iyiV, ('yok', 0, 1.0, 'A', False), 0.1, 0.1, 0.9], [iyiL, iyiV, ('A', 0, 1.0, 'yok', False), 0.1, 0.1, 0.9], [iyiL, iyiV, ('A', 1, 1.0, 'A', False), 0.1, 0.1, 0.9], [iyiL, iyiV, ('A', -1, 1.0, 'A', False), 0.1, 0.1, 0.9], [iyiL, iyiV, ('A', True, 1.0, 'A', False), 0.1, 0.1, 0.9], [iyiL, iyiV, ('A', False, 1.0, 'A', False), 0.1, 0.1, 0.9], [iyiL, iyiV, ('A', 0.0, 1.0, 'A', False), 0.1, 0.1, 0.9], [iyiL, iyiV, ('A', 0, None, 'A', False), 0.1, 0.1, 0.9], [iyiL, iyiV, ('A', 0, True, 'A', False), 0.1, 0.1, 0.9], [iyiL, iyiV, ('A', 0, float('nan'), 'A', False), 0.1, 0.1, 0.9], [iyiL, iyiV, ('A', 0, 1.0, 'A', 0), 0.1, 0.1, 0.9], [iyiL, iyiV, iyiG, 0, 0.1, 0.9], [iyiL, iyiV, iyiG, True, 0.1, 0.9], [iyiL, iyiV, iyiG, float('inf'), 0.1, 0.9], [iyiL, iyiV, iyiG, 0.1, 0, 0.9], [iyiL, iyiV, iyiG, 0.1, True, 0.9], [iyiL, iyiV, iyiG, 0.1, float('nan'), 0.9], [iyiL, iyiV, iyiG, 0.1, None, 0.9], [iyiL, iyiV, iyiG, 0.1, 0.1, 1.5], [iyiL, iyiV, iyiG, 0.1, 0.1, -0.1], [iyiL, iyiV, iyiG, 0.1, 0.1, True], [iyiL, iyiV, iyiG, 0.1, 0.1, float('nan')]):
    raises(ValueError, actor_critic_adimi, *a, msg='bozuk girdi reddedilir')
```

```hint
Üç adım: `delta`'yı eski `V` ile hesapla; `V[s]`'yi `lr_critic · delta` kadar düzelt; `logitler[s]`'yi `lr_actor · delta · ((k == a) − pi[k])` kadar düzelt. Kopyalar üzerinde çalış.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur; her adım bu derste hesapladığın bir sayıya ya da örneğe dayanır.

1. **Çerçeve (15 sn).** "İki rol var: oyuncu eylemi seçer, eleştirmen 'beklediğimden iyi miydi' der."
2. **Örnek (30 sn).** Tahmin adımı: ödül 3 iken avantaj +1,6; ödül 1 iken -0,4. "Ödül iki durumda da pozitif; ama ikincisi beklentinin altında."
3. **Fayda (30 sn).** "Bölümün bitmesini beklemeden her adımda öğrenilir ve gürültü azalır."
4. **Bedel (25 sn).** "Eleştirmen yanılıyorsa oyuncu yanlış yöne itilir. Bir adım mı, bütün bölüm mü: arası tek bir düğmeyle ayarlanır."
5. **Kapanış (20 sn).** "Önemli olan ödülün işareti değil, beklentiye göre farkıdır; insanlar için de öyle."
:::

::: anlat Sınır
Bu ders avantajı, GAE'yi ve tek adımlı actor-critic güncellemesini tablolu durumlarla anlatır. Gerçek sistemlerde oyuncu ve eleştirmen sinir ağlarıdır, çoğu zaman gövdeyi paylaşır ve güncellemeler paralel ortamlardan toplanan `minibatch`'lerle yapılır (`A2C`, `A3C`). Avantaj tahmini eleştirmenin doğruluğuna bağlıdır: eleştirmen yanlışsa oyuncu yanlış yöne itilir ve eğitimin başında eleştirmen her zaman yanlıştır. $\lambda$ bu bias ile varyans arasında bir ödünleşimdir; doğru değeri probleme göre değişir ve ayarlanması gerekir. GAE bir bölüm parçası (`rollout`) üzerinde hesaplanır; parça bölüm bitmeden kesilirse son değerin bootstrap edilmesi şarttır, yoksa kesilen yer "bölüm bitti" gibi yorumlanır ve değerler sistemli olarak düşük çıkar. Görev 3'teki güncelleme `on-policy`'dir: geçiş güncel politikadan gelmelidir. Pratikte avantajlar bir batch içinde normalleştirilir ve politikanın erken çökmesini önlemek için bir `entropy` terimi eklenir; bunlar burada uygulanmaz. Tek bir büyük güncelleme politikayı bozabilir; bunu sınırlamak bir sonraki dersin konusudur (bkz. `ai-matematik-20`).

Kaynaklar: [Schulman vd. 2016 - High-Dimensional Continuous Control Using Generalized Advantage Estimation](https://arxiv.org/abs/1506.02438), [Mnih vd. 2016 - Asynchronous Methods for Deep Reinforcement Learning](https://arxiv.org/abs/1602.01783), [Sutton ve Barto 2018 - Reinforcement Learning: An Introduction, Bölüm 13.5](http://incompleteideas.net/book/the-book-2nd.html).
:::

::: dusun
Bir rollout 128 adımda kesiliyor ama bölüm 1.000 adım sürüyor. Geliştirici `son_deger` olarak yanlışlıkla hep `0` veriyor. Ajan hangi tür davranışı öğrenmeye yatkın olur: uzun vadeli mi, kısa vadeli mi? Görev 2'nin son örneğindeki sayıları kullanarak hatanın büyüklüğünü göster.
:::

::: ozet
- Actor politikayı, critic değer fonksiyonunu öğrenir; critic'in oyuncuya verdiği sinyal avantajdır.
- Tek adımlı TD hatası `δ = r + γV(s') − V(s)` düşük varyanslı ama yanlı bir avantaj tahminidir.
- GAE TD hatalarını `(γλ)^k` ile ağırlıklandırır: `λ = 0` tek adım, `λ = 1` Monte Carlo.
- Güncellemede critic `δ` yönünde düzeltilir, actor `δ · ∇ log π` yönünde itilir; bölümün bitmesi beklenmez.
- Pozitif ödül pozitif avantaj demek değildir; önemli olan beklentiye göre farktır.
:::
