---
id: ai-matematik-18
title: "REINFORCE ve Varyans · Politikayı Doğrudan Öğrenmek"
summary: Softmax politikasının log-olasılık gradient'ini türet, REINFORCE güncellemesini yaz ve bir baseline'ın gradient tahmininin varyansını ne kadar düşürdüğünü ölç.
---

::: anlat 1. Değeri değil, politikayı öğren
Q-learning ve DQN önce değerleri öğrenir, politikayı değerlerden çıkarır. Eylem sayısı çok büyükse (bir dil modelinin 100.000 token'lık sözlüğü) ya da eylemler sürekliyse bu yol tıkanır. `Policy gradient` yöntemleri politikayı **doğrudan** parametreler ve getiriyi artıracak yönde iter. `RLHF`, `GRPO` ve `PPO` bu aileden gelir (bkz. `ai-uretim-10`, `ai-uretim-11`).

Politika parametreli bir olasılık dağılımıdır: $\pi_\theta(a \mid s)$. En yaygın biçim `softmax`'tir: her eylemin bir tercih puanı (`logit`) vardır ve olasılık $\pi(a) = \dfrac{e^{\theta_a}}{\sum_b e^{\theta_b}}$ olur.

| Soru | Araç | Görev |
|---|---|---|
| Bir eylemin olasılığını artırmak için parametreler hangi yöne itilir? | $\nabla_\theta \log \pi_\theta(a)$ | 1 |
| Getiri bu itmeyi nasıl ölçekler? | `REINFORCE` güncellemesi | 2 |
| Tahmin neden gürültülü ve nasıl sakinleşir? | `Baseline` ve varyans | 3 |

Bu derste durum yoktur (tek durumlu bir problem, `bandit`); politika yalnız eylemler üzerinde bir dağılımdır. Fikir çok durumlu hâlde de aynıdır.
:::

::: anlat 2. Policy gradient teoremi, REINFORCE ve baseline
**Amaç.** Beklenen getiriyi büyütmek: $J(\theta) = \mathbb{E}_{a \sim \pi_\theta}[R(a)]$. Sorun şu: örnekleme işleminin içinden türev alınamaz. `Log-derivative trick` bunu çözer:

$$\nabla_\theta J = \mathbb{E}_{a \sim \pi_\theta}\big[R(a)\, \nabla_\theta \log \pi_\theta(a)\big]$$

Yani gradient, "seçilen eylemin log-olasılığının gradient'i çarpı alınan getiri"nin beklentisidir. Ödül fonksiyonunun türevine gerek yoktur; ödül bir kara kutu olabilir (bir insanın beğenisi, bir testin geçip geçmemesi).

**Softmax için** log-olasılığın gradient'i çok yalındır:

$$\frac{\partial \log \pi(a)}{\partial \theta_k} = \mathbb{1}[k = a] - \pi(k)$$

Seçilen eylemin logit'i $(1 - \pi(a))$ kadar artar, diğerlerininki $\pi(k)$ kadar azalır. Bileşenlerin toplamı sıfırdır: olasılık bir eylemden alınıp diğerine verilir.

**REINFORCE.** Bir eylem örnekle, getiriyi gör, güncelle:

$$\theta \leftarrow \theta + \alpha\, R\, \nabla_\theta \log \pi_\theta(a)$$

İyi getiri veren eylemin olasılığı artar, kötü getiri verenin azalır. Güncelleme **beklentide** doğru yöndedir, ama tek bir örnek çok gürültülüdür.

**Varyans ve baseline.** Bütün getiriler pozitifse (örneğin 100 ile 110 arası) her örnek, seçtiği eylemin olasılığını artırır; iyi eylem yalnız **biraz daha fazla** artar. Sinyal, büyük bir ortak sayının içinde kaybolur. Çözüm: getiriden bir `baseline` çıkarmak.

$$\theta \leftarrow \theta + \alpha\,(R - b)\, \nabla_\theta \log \pi_\theta(a)$$

`b` eyleme bağlı olmadığı sürece gradient'in beklentisi **değişmez** (çünkü $\mathbb{E}[\nabla \log \pi] = 0$), ama varyansı çok düşebilir. Doğal seçim ortalama getiridir: artık "ortalamadan iyi mi, kötü mü" sorusu sorulur. $R - b$ farkına `advantage` denir ve bir sonraki dersin konusudur.
:::

::: tahmin Seçilen eylem yukarı, diğerleri aşağı
Üç eylemli bir softmax politikasında birinci eylem seçildi. Log-olasılığın logit'lere göre gradient'i ne yazdırılır?

```python
import math

logit = [0.0, 0.0, math.log(2)]
z = sum(math.exp(x) for x in logit)
pi = [math.exp(x) / z for x in logit]
secilen = 0
grad = [(1.0 if k == secilen else 0.0) - pi[k] for k in range(3)]
print([round(p, 2) for p in pi])
print([round(g, 2) for g in grad])
```

???

```cikti
[0.25, 0.25, 0.5]
[0.75, -0.25, -0.5]
```
Olasılıklar 0,25, 0,25 ve 0,5'tir. Seçilen eylemin gradient'i $1 - 0{,}25 = 0{,}75$'tir; diğerlerininki eksi olasılıklarıdır. Toplam sıfırdır: $0{,}75 - 0{,}25 - 0{,}5 = 0$. Olasılığı zaten yüksek olan üçüncü eylem en çok geri itilir. Getiri pozitifse bu vektör yönünde, negatifse ters yönde adım atılır.
:::

::: gorev 1 · Softmax politikası ve log-olasılık gradient'i
`log_olasilik_gradient(logitler, eylem)` işlevini yaz.

- `logitler`: boş olmayan sayı listesi. `eylem`: geçerli bir indeks (`int`).
- `olasiliklar`: softmax; taşmayı önlemek için üstel almadan önce en büyük logit çıkarılır.
- `gradient`: her `k` için `(1 if k == eylem else 0) - olasiliklar[k]`.
- Dönüş: `{'olasiliklar': [...], 'gradient': [...]}`; 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç yalnız seçilen eylemin bileşenini dolduruyor; diğer eylemlerin logit'lerini geri itmiyor. Gradient'in toplamı sıfır olmuyor.

```starter
def log_olasilik_gradient(logitler, eylem):
    import math
    z = sum(math.exp(x) for x in logitler)
    pi = [math.exp(x) / z for x in logitler]
    return {'olasiliklar': [round(p, 9) for p in pi], 'gradient': [round(1 - pi[k], 9) if k == eylem else 0.0 for k in range(len(pi))]}
```

```solution
def log_olasilik_gradient(logitler, eylem):
    import math
    if not isinstance(logitler, list) or not logitler or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in logitler):
        raise ValueError('logitler boş olmayan sayı listesi olmalı')
    if isinstance(eylem, bool) or not isinstance(eylem, int) or not 0 <= eylem < len(logitler):
        raise ValueError('eylem geçerli bir indeks olmalı')
    en = max(logitler)
    ustel = [math.exp(x - en) for x in logitler]
    z = sum(ustel)
    pi = [u / z for u in ustel]
    return {
        'olasiliklar': [round(p, 9) for p in pi],
        'gradient': [round((1.0 if k == eylem else 0.0) - pi[k], 9) for k in range(len(pi))],
    }
```

```test
need('log_olasilik_gradient')
import math, random

r = log_olasilik_gradient([0.0, 0.0, math.log(2)], 0)
eq(r['olasiliklar'], [0.25, 0.25, 0.5], 'softmax olasılıkları')
eq(r['gradient'], [0.75, -0.25, -0.5], 'seçilen yukarı, diğerleri olasılıkları kadar aşağı')
eq(log_olasilik_gradient([5.0], 0), {'olasiliklar': [1.0], 'gradient': [0.0]}, 'tek eylem: değişecek bir şey yok')
r = log_olasilik_gradient([1000.0, 0.0], 1)
eq(r['olasiliklar'], [1.0, 0.0], 'çok büyük logit taşmaz')
eq(r['gradient'], [-1.0, 1.0], 'neredeyse imkânsız eylem seçilirse gradient en büyüktür')
r = log_olasilik_gradient([3.0, 3.0], 0)
eq(r['gradient'], [0.5, -0.5], 'eşit logit: yarı yarıya')
def logp(th, a):
    m = max(th)
    return th[a] - m - math.log(sum(math.exp(x - m) for x in th))
rng = random.Random(1801)
for _ in range(25):
    n = rng.randint(1, 6)
    th = [round(rng.uniform(-3, 3), 2) for _ in range(n)]
    a = rng.randrange(n)
    r = log_olasilik_gradient(th, a)
    yakin(sum(r['olasiliklar']), 1.0, 'olasılıklar 1 e toplanır', tol=1e-7)
    yakin(sum(r['gradient']), 0.0, 'gradient bileşenlerinin toplamı sıfır', tol=1e-7)
    h = 1e-6
    for k in range(n):
        tp, tm = list(th), list(th)
        tp[k] += h
        tm[k] -= h
        yakin(r['gradient'][k], (logp(tp, a) - logp(tm, a)) / (2 * h), 'gradient sayısal türevle aynı', tol=1e-5)
    kaymis = log_olasilik_gradient([x + 7.5 for x in th], a)
    for p, q in zip(r['olasiliklar'], kaymis['olasiliklar']):
        yakin(p, q, 'bütün logit lere sabit eklemek olasılıkları değiştirmez', tol=1e-8)
th = [1.0, 2.0]
log_olasilik_gradient(th, 0)
eq(th, [1.0, 2.0], 'girdi değişmez')
eq(log_olasilik_gradient([0.0, 0.0, 0.0], 0)['olasiliklar'][0], 0.333333333, '9 basamağa yuvarlanır')
for a, e in [(None, 0), ([], 0), ([1, "2"], 0), ([True], 0), ((1.0, 2.0), 0), ([float('nan')], 0), ([float('inf')], 0), ([1.0], 1), ([1.0], -1), ([1.0], 0.0), ([1.0], True), ([1.0], None)]:
    raises(ValueError, log_olasilik_gradient, a, e, msg='bozuk girdi reddedilir')
```

```hint
Kararlı softmax: önce en büyük logit'i çıkar, sonra üstel al ve toplama böl. Gradient: `(k == eylem) − pi[k]`.
```
:::

::: gorev 2 · REINFORCE güncellemesi
`reinforce_adimi(logitler, ornekler, lr, baseline)` işlevini yaz.

- `logitler`: boş olmayan sayı listesi. `ornekler`: boş olmayan liste; her öğe `(eylem, getiri)`; eylem geçerli indeks, getiri sayı. `lr`: pozitif sayı. `baseline`: sayı.
- Bütün örnekler **aynı** (güncellemeden önceki) politikadan gelmiştir. Gradient tahmini örneklerin ortalamasıdır:
  $g = \frac{1}{n}\sum_i (R_i - b)\,\nabla \log \pi(a_i)$.
- Güncelleme: `logit ← logit + lr · g`.
- Dönüş: `{'logitler': [...], 'gradient': [...]}`; 9 basamağa yuvarlanır. Girdi değişmemelidir.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç gradient **inişi** yapıyor (`−lr · g`): getirisi yüksek eylemlerin olasılığını düşürüyor.

```starter
def reinforce_adimi(logitler, ornekler, lr, baseline):
    import math
    en = max(logitler)
    u = [math.exp(x - en) for x in logitler]
    pi = [x / sum(u) for x in u]
    n = len(ornekler)
    g = [sum((r - baseline) * ((1.0 if k == a else 0.0) - pi[k]) for a, r in ornekler) / n for k in range(len(pi))]
    return {'logitler': [round(t - lr * gk, 9) for t, gk in zip(logitler, g)], 'gradient': [round(gk, 9) for gk in g]}
```

```solution
def reinforce_adimi(logitler, ornekler, lr, baseline):
    import math
    def sayi(x):
        return not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x)
    if not isinstance(logitler, list) or not logitler or not all(sayi(x) for x in logitler):
        raise ValueError('logitler boş olmayan sayı listesi olmalı')
    if not isinstance(ornekler, list) or not ornekler:
        raise ValueError('ornekler boş olmayan liste olmalı')
    for o in ornekler:
        if not isinstance(o, (tuple, list)) or len(o) != 2 or isinstance(o[0], bool) or not isinstance(o[0], int) or not 0 <= o[0] < len(logitler) or not sayi(o[1]):
            raise ValueError('örnek (eylem, getiri) olmalı')
    if not sayi(lr) or not lr > 0 or not sayi(baseline):
        raise ValueError('lr pozitif sayı, baseline sayı olmalı')
    en = max(logitler)
    ustel = [math.exp(x - en) for x in logitler]
    z = sum(ustel)
    pi = [u / z for u in ustel]
    n = len(ornekler)
    g = [sum((r - baseline) * ((1.0 if k == a else 0.0) - pi[k]) for a, r in ornekler) / n for k in range(len(pi))]
    return {'logitler': [round(t + lr * gk, 9) for t, gk in zip(logitler, g)], 'gradient': [round(gk, 9) for gk in g]}
```

```test
need('reinforce_adimi')
import math, random

r = reinforce_adimi([0.0, 0.0], [(0, 1.0)], 1.0, 0.0)
eq(r, {'logitler': [0.5, -0.5], 'gradient': [0.5, -0.5]}, 'pozitif getiri: seçilen eylemin logit i artar')
r = reinforce_adimi([0.0, 0.0], [(0, -1.0)], 1.0, 0.0)
eq(r['logitler'], [-0.5, 0.5], 'negatif getiri: seçilen eylemin logit i azalır')
r = reinforce_adimi([0.0, 0.0], [(0, 1.0)], 1.0, 1.0)
eq(r['logitler'], [0.0, 0.0], 'getiri baseline a eşitse güncelleme yok')
r = reinforce_adimi([0.0, 0.0], [(0, 101.0), (1, 100.0)], 0.1, 0.0)
yakin(r['gradient'][0], 0.25, 'baseline sız: (101 · 0.5 - 100 · 0.5) / 2', tol=1e-9)
r = reinforce_adimi([0.0, 0.0], [(0, 101.0), (1, 100.0)], 0.1, 100.5)
yakin(r['gradient'][0], 0.25, 'her eylem birer kez örneklendiyse baseline bu tahmini değiştirmez', tol=1e-9)
def soft(th):
    m = max(th)
    u = [math.exp(x - m) for x in th]
    return [x / sum(u) for x in u]
rng = random.Random(1802)
for _ in range(20):
    n = rng.randint(1, 5)
    th = [round(rng.uniform(-2, 2), 2) for _ in range(n)]
    orn = [(rng.randrange(n), round(rng.uniform(-3, 3), 2)) for _ in range(rng.randint(1, 10))]
    lr, b = rng.choice([0.01, 0.1, 1.0]), round(rng.uniform(-2, 2), 2)
    r = reinforce_adimi(th, orn, lr, b)
    pi = soft(th)
    for k in range(n):
        g = sum((ri - b) * ((1 if a == k else 0) - pi[k]) for a, ri in orn) / len(orn)
        yakin(r['gradient'][k], g, 'rastgele örneklerde gradient', tol=1e-8)
        yakin(r['logitler'][k], th[k] + lr * g, 'rastgele örneklerde yeni logit', tol=1e-8)
    yakin(sum(r['gradient']), 0.0, 'gradient toplamı sıfır', tol=1e-7)
th = [0.0, 0.0, 0.0]
odul = [1.0, 2.0, 5.0]
g2 = random.Random(7)
for _ in range(400):
    pi = soft(th)
    orn = []
    for _ in range(8):
        u, a, t = g2.random(), 0, pi[0]
        while u > t and a < 2:
            a += 1
            t += pi[a]
        orn.append((a, odul[a]))
    th = reinforce_adimi(th, orn, 0.1, 2.5)['logitler']
ok(soft(th)[2] > 0.9, 'tekrarlanan güncellemeler olasılığı en yüksek ödüllü eyleme yığar', got=soft(th))
eq(reinforce_adimi([1000.0, -1000.0], [(1, 1.0)], 0.1, 0.0), {'logitler': [999.9, -999.9], 'gradient': [-1.0, 1.0]}, 'büyük logit lerde kararlı softmax: taşma yok')
th = [1.0, 2.0]
reinforce_adimi(th, [(0, 1.0)], 0.1, 0.0)
eq(th, [1.0, 2.0], 'girdi değişmez')
iyi = [(0, 1.0)]
for a in ([None, iyi, 0.1, 0], [[], iyi, 0.1, 0], [(0.0,), iyi, 0.1, 0], [[True], iyi, 0.1, 0], [[float('nan')], iyi, 0.1, 0], [[float('inf')], iyi, 0.1, 0], [[0.0], None, 0.1, 0], [[0.0], [], 0.1, 0], [[0.0], (iyi[0],), 0.1, 0], [[0.0], ['kotu'], 0.1, 0], [[0.0], [123], 0.1, 0], [[0.0], [(1, 1.0)], 0.1, 0], [[0.0], [(-1, 1.0)], 0.1, 0], [[0.0], [(True, 1.0)], 0.1, 0], [[0.0], [(False, 1.0)], 0.1, 0], [[0.0], [(0,)], 0.1, 0], [[0.0], [(0.0, 1.0)], 0.1, 0], [[0.0], [(0, "1")], 0.1, 0], [[0.0], [(0, True)], 0.1, 0], [[0.0], [(0, float('nan'))], 0.1, 0], [[0.0], [(0, float('inf'))], 0.1, 0], [[0.0], iyi, 0, 0], [[0.0], iyi, True, 0], [[0.0], iyi, float('nan'), 0], [[0.0], iyi, float('inf'), 0], [[0.0], iyi, None, 0], [[0.0], iyi, 0.1, None], [[0.0], iyi, 0.1, True], [[0.0], iyi, 0.1, float('nan')], [[0.0], iyi, 0.1, float('inf')]):
    raises(ValueError, reinforce_adimi, *a, msg='bozuk girdi reddedilir')
```

```hint
Önce politikayı (softmax) bir kez hesapla. Her örnek `(R − b) · ((k == a) − pi[k])` katkısı yapar; ortalamasını al ve `lr` ile çarpıp **ekle**.
```
:::

::: gorev 3 · Baseline varyansı ne kadar düşürür?
`gradient_varyansi(logitler, getiriler, baseline)` işlevini yaz. Tek örnekli REINFORCE tahmininin beklentisini ve varyansını **tam** olarak (örneklemeden, bütün eylemler üzerinden toplayarak) hesaplar.

- `logitler`: boş olmayan sayı listesi. `getiriler`: aynı uzunlukta sayı listesi; `getiriler[a]`, `a` eyleminin (belirlenimci) getirisidir. `baseline`: sayı.
- Tek örnekli tahmin: `a` eylemi $\pi(a)$ olasılıkla seçilir ve tahmin vektörü $(R_a - b)\,\nabla \log \pi(a)$ olur.
- `beklenti`: bu vektörün beklentisi, $\sum_a \pi(a)\,(R_a - b)\,\nabla \log \pi(a)$.
- `varyans`: bileşenlerin varyanslarının toplamı, $\sum_k \big(\mathbb{E}[g_k^2] - \mathbb{E}[g_k]^2\big)$.
- Dönüş: `{'beklenti': [...], 'varyans': ...}`; 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç baseline'ı beklentiden de çıkarıyor gibi davranıp varyansı yalnız getirilerin varyansı olarak döndürüyor: gradient'in yönünü hiç hesaba katmıyor.

```starter
def gradient_varyansi(logitler, getiriler, baseline):
    import math
    en = max(logitler)
    u = [math.exp(x - en) for x in logitler]
    pi = [x / sum(u) for x in u]
    ort = sum(p * (r - baseline) for p, r in zip(pi, getiriler))
    var = sum(p * (r - baseline - ort) ** 2 for p, r in zip(pi, getiriler))
    return {'beklenti': [round(ort, 9) for _ in pi], 'varyans': round(var, 9)}
```

```solution
def gradient_varyansi(logitler, getiriler, baseline):
    import math
    def sayilar(v):
        return isinstance(v, list) and v and not any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in v)
    if not sayilar(logitler) or not sayilar(getiriler) or len(logitler) != len(getiriler):
        raise ValueError('aynı uzunlukta, boş olmayan iki sayı listesi gerekli')
    if isinstance(baseline, bool) or not isinstance(baseline, (int, float)) or not math.isfinite(baseline):
        raise ValueError('baseline sayı olmalı')
    en = max(logitler)
    ustel = [math.exp(x - en) for x in logitler]
    z = sum(ustel)
    pi = [u / z for u in ustel]
    n = len(pi)
    bek = [0.0] * n
    kare = [0.0] * n
    for a in range(n):
        for k in range(n):
            g = (getiriler[a] - baseline) * ((1.0 if k == a else 0.0) - pi[k])
            bek[k] += pi[a] * g
            kare[k] += pi[a] * g * g
    varyans = sum(kare[k] - bek[k] ** 2 for k in range(n))
    return {'beklenti': [round(x, 9) for x in bek], 'varyans': round(max(0.0, varyans), 9)}
```

```test
need('gradient_varyansi')
import math, random

a = gradient_varyansi([0.0, 0.0], [101.0, 100.0], 0.0)
b = gradient_varyansi([0.0, 0.0], [101.0, 100.0], 100.5)
eq(a['beklenti'], [0.25, -0.25], 'beklenen gradient: iyi eylem yönünde')
eq(b['beklenti'], [0.25, -0.25], 'baseline beklentiyi değiştirmez')
eq(a['varyans'], 5050.125, 'baseline sız: varyans getirilerin büyüklüğüyle şişer')
eq(b['varyans'], 0.0, 'ortalama getiri baseline olunca bu problemde varyans sıfır')
ok(a['varyans'] > 10000 * max(b['varyans'], 1e-9) or b['varyans'] == 0.0, 'baseline varyansı çok düşürür')
r = gradient_varyansi([0.0, 0.0, 0.0], [5.0, 5.0, 5.0], 0.0)
eq(r['beklenti'], [0.0, 0.0, 0.0], 'bütün eylemler eşit getirili: öğrenilecek yön yok')
ok(r['varyans'] > 1.0, 'ama baseline sız tahmin yine de gürültülü', got=r)
eq(gradient_varyansi([0.0, 0.0, 0.0], [5.0, 5.0, 5.0], 5.0)['varyans'], 0.0, 'baseline gürültüyü tamamen siler')
eq(gradient_varyansi([2.0], [3.0], 0.0), {'beklenti': [0.0], 'varyans': 0.0}, 'tek eylem')
def soft(th):
    m = max(th)
    u = [math.exp(x - m) for x in th]
    return [x / sum(u) for x in u]
rng = random.Random(1803)
for _ in range(20):
    n = rng.randint(1, 5)
    th = [round(rng.uniform(-2, 2), 2) for _ in range(n)]
    R = [round(rng.uniform(-5, 5), 2) for _ in range(n)]
    b0, b1 = round(rng.uniform(-3, 3), 2), round(rng.uniform(-3, 3), 2)
    r0, r1 = gradient_varyansi(th, R, b0), gradient_varyansi(th, R, b1)
    pi = soft(th)
    J = sum(p * x for p, x in zip(pi, R))
    for k in range(n):
        yakin(r0['beklenti'][k], pi[k] * (R[k] - J), 'beklenti gerçek gradient e eşit: pi_k (R_k - J)', tol=1e-7)
        yakin(r0['beklenti'][k], r1['beklenti'][k], 'beklenti baseline dan bağımsız', tol=1e-7)
    ok(r0['varyans'] >= 0.0 and r1['varyans'] >= 0.0, 'varyans negatif olmaz')
    ornek_var = 0.0
    for k in range(n):
        m2 = sum(pi[a] * ((R[a] - b0) * ((1 if a == k else 0) - pi[k])) ** 2 for a in range(n))
        ornek_var += m2 - r0['beklenti'][k] ** 2
    yakin(r0['varyans'], ornek_var, 'varyans tanımıyla aynı', tol=1e-6)
eq(gradient_varyansi([1000.0, -1000.0], [1.0, 0.0], 0.0), {'beklenti': [0.0, 0.0], 'varyans': 0.0}, 'büyük logit lerde kararlı softmax: taşma yok')
th, R = [0.0, 1.0], [1.0, 2.0]
gradient_varyansi(th, R, 0.5)
eq((th, R), ([0.0, 1.0], [1.0, 2.0]), 'girdiler değişmez')
for a in ([None, [1.0], 0], [[1.0], None, 0], [[], [1.0], 0], [[1.0], [], 0], [[], [], 0], [[1.0, 2.0], [1.0], 0], [[1, "2"], [1, 2], 0], [[True], [1.0], 0], [(1.0,), [1.0], 0], [[float('nan')], [1.0], 0], [[1.0], [float('inf')], 0], [[1.0], [1.0], None], [[1.0], [1.0], True], [[1.0], [1.0], float('nan')], [[1.0], [1.0], float('inf')]):
    raises(ValueError, gradient_varyansi, *a, msg='bozuk girdi reddedilir')
```

```hint
İki iç içe döngü: dıştaki seçilen eylem `a` (olasılığı `pi[a]`), içteki gradient bileşeni `k`. Her `k` için `E[g_k]` ve `E[g_k²]` biriktir; varyans `Σ (E[g_k²] − E[g_k]²)`.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur; her adım bu derste hesapladığın bir sayıya ya da örneğe dayanır.

1. **Çerçeve (15 sn).** "Değerleri öğrenmek yerine politikayı doğrudan iteriz: iyi giden eylemi daha olası, kötü gideni daha az olası yaparız."
2. **Yön (30 sn).** "Seçilen eylem yukarı, diğerleri olasılıkları kadar aşağı. Olasılık bir eylemden alınıp diğerine verilir."
3. **Gürültü (30 sn).** "Bütün ödüller 100 civarındaysa her deneme 'iyiydi' der; sinyal büyük bir ortak sayının içinde kaybolur. Görev 3'te varyans 5.050."
4. **Çare (25 sn).** "Ortalamayı çıkarın: soru 'iyi miydi' değil, 'ortalamadan iyi miydi' olsun. Varyans 5.050'den sıfıra iniyor."
5. **Kapanış (20 sn).** "Dil modellerinin insan geri bildirimiyle eğitilmesi bu ailenin torunudur."
:::

::: anlat Sınır
Bu ders policy gradient'i tek durumlu bir problemde (`bandit`), logit'leri doğrudan parametre alan bir softmax politikasıyla anlatır. Çok adımlı bölümlerde her eylemin log-olasılık gradient'i, o adımdan **sonraki** getiriyle çarpılır (bkz. `ai-matematik-15`) ve kredi ataması sorunu ortaya çıkar: hangi eylem sonuçtan sorumluydu? Gerçek politikalarda logit'ler bir sinir ağının çıktısıdır ve gradient `backpropagation` ile ağırlıklara taşınır. REINFORCE `on-policy`'dir: örnekler güncellenen politikadan gelmelidir; bir güncellemeden sonra eski örnekler geçersizdir, bu yüzden örnek açısından verimsizdir. Baseline varyansı düşürür ama tek bir sabit sayı çok durumlu problemde yetmez; duruma bağlı bir baseline (değer fonksiyonu) gerekir (bkz. `ai-matematik-19`). Görev 3'teki varyans, getirilerin belirlenimci olduğunu varsayar; gürültülü ödüllerde varyans daha da büyüktür. Yöntem yalnız ödülü büyütür: ödül fonksiyonu kastedilen amacı tam yansıtmıyorsa politika ödülü toplayan ama amaca hizmet etmeyen davranışı öğrenir.

Kaynaklar: [Williams 1992 - Simple statistical gradient-following algorithms for connectionist reinforcement learning](https://doi.org/10.1007/BF00992696), [Sutton vd. 1999 - Policy Gradient Methods for Reinforcement Learning with Function Approximation](https://papers.nips.cc/paper/1999/hash/464d828b85b0bed98e80ade0a5c43b0f-Abstract.html), [Sutton ve Barto 2018 - Reinforcement Learning: An Introduction, Bölüm 13](http://incompleteideas.net/book/the-book-2nd.html).
:::

::: dusun
Görev 3'te getirileri 101 ve 100 olan iki eylem için baseline'sız varyans 5.050, ortalama baseline ile 0 çıktı. İki eylemin getirisi 1 ve 0 olsaydı (fark aynı, ortak sayı yok) baseline'sız varyans ne olurdu? Bu, ödülleri bir sabitle kaydırmanın öğrenme hızını neden etkilediğini nasıl açıklar?
:::

::: ozet
- Policy gradient yöntemleri politikayı doğrudan parametreler ve beklenen getiriyi artıracak yönde iter.
- Gradient, `R · ∇ log π(a)` beklentisidir; ödülün türevine gerek yoktur.
- Softmax'te `∂ log π(a) / ∂θ_k = 1[k = a] − π(k)`'dır ve bileşenlerin toplamı sıfırdır.
- REINFORCE beklentide doğru, tek örnekte çok gürültülüdür.
- Eyleme bağlı olmayan bir baseline gradient'in beklentisini değiştirmez, varyansını düşürür.
:::
