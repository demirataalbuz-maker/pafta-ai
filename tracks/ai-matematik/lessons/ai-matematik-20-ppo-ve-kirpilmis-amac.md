---
id: ai-matematik-20
title: "PPO ve Kırpılmış Amaç · Politikayı Bozmadan Güncellemek"
summary: Olasılık oranını ve PPO'nun kırpılmış amacını hesapla, bir batch için kaybı ve tanı ölçülerini çıkar ve aynı veriyle birden çok güncelleme adımı atıldığında kırpmanın politikayı nasıl yerinde tuttuğunu ölç.
---

::: anlat 1. Tek bir kötü adım her şeyi bozar
Policy gradient yöntemlerinde veri politikanın kendisinden gelir. Bir güncelleme politikayı fazla değiştirirse ajan kötü eylemler seçmeye başlar, topladığı veri kötüleşir ve bir sonraki güncelleme daha da kötü olur: eğitim çöker ve çoğu zaman geri dönmez. Gözetimli öğrenmede kötü bir adım bir sonraki batch'te düzelir; burada düzelmez.

İkinci sorun verimliliktir: REINFORCE ve actor-critic topladığı her veriyi **bir kez** kullanıp atar.

`Proximal Policy Optimization` (PPO) ikisini birlikte çözer: aynı veriyle birkaç güncelleme adımı atar, ama politikanın veriyi toplayan eski politikadan fazla uzaklaşmasına izin vermez. `RLHF` ile dil modeli hizalamasının ve çoğu modern ajan eğitiminin standart yöntemidir (bkz. `ai-uretim-10`, `ai-uretim-11`).

| Soru | Araç | Görev |
|---|---|---|
| Yeni politika eskisinden ne kadar farklı? | Olasılık oranı $r$ ve kırpılmış amaç | 1 |
| Bir batch'te neler oluyor? | Kayıp, kırpılan pay, yaklaşık KL | 2 |
| Aynı veriyle çok adım atınca ne olur? | PPO güncelleme döngüsü | 3 |
:::

::: anlat 2. Oran, kırpma ve tanı ölçüleri
**Olasılık oranı.** Veri eski politika $\pi_{\text{eski}}$ ile toplandı; güncellenen politika $\pi_\theta$. Her örnek için:

$$r = \frac{\pi_\theta(a \mid s)}{\pi_{\text{eski}}(a \mid s)} = \exp\big(\log \pi_\theta(a \mid s) - \log \pi_{\text{eski}}(a \mid s)\big)$$

Güncellemeden önce $r = 1$'dir. $r > 1$, eylemin artık daha olası olduğunu gösterir.

**Kırpılmamış amaç** $r \cdot A$'dır (`A` avantaj, bkz. `ai-matematik-19`): avantajı pozitif eylemlerin oranını büyüt, negatif olanlarınkini küçült. Sınırı yoktur: optimizer `r`'yi istediği kadar büyütebilir.

**Kırpılmış amaç** buna bir tavan koyar:

$$L^{\text{CLIP}} = \min\big(r \cdot A,\; \operatorname{clip}(r,\, 1 - \epsilon,\, 1 + \epsilon) \cdot A\big)$$

$\epsilon$ genellikle 0,1 ile 0,2 arasıdır. `min`, amacı **kötümser** yapar:

| Durum | Ne olur |
|---|---|
| $A > 0$ ve $r > 1 + \epsilon$ | Kazanç $(1 + \epsilon)A$'da sabitlenir; daha fazla itmenin ödülü yok, gradient sıfır |
| $A < 0$ ve $r < 1 - \epsilon$ | Kazanç $(1 - \epsilon)A$'da sabitlenir; daha fazla bastırmanın ödülü yok |
| $A > 0$ ve $r < 1 - \epsilon$ | Kırpılmaz: iyi eylemi yanlışlıkla bastırdıysan tam ceza alırsın ve geri düzeltilir |
| $A < 0$ ve $r > 1 + \epsilon$ | Kırpılmaz: kötü eylemi yanlışlıkla güçlendirdiysen tam ceza alırsın |

Yani kırpma yalnız **kazanç yönünde** çalışır; hata yönünde düzeltme serbesttir. Politikanın eski politikadan uzaklaşmasının teşviki böylece ortadan kalkar.

**Tanı ölçüleri.** Bir PPO eğitimini izlerken iki sayıya bakılır:

- **Kırpılan pay** (`clip fraction`): $\lvert r - 1 \rvert > \epsilon$ olan örneklerin oranı. Sürekli yüksekse adımlar fazla büyüktür.
- **Yaklaşık KL**: $\text{ortalama}(\log \pi_{\text{eski}} - \log \pi_\theta)$. Politikanın ne kadar değiştiğinin ucuz bir ölçüsü; çoğu uygulama bu bir eşiği aşınca o veriyle güncellemeyi keser.

PPO en büyütülen bir **amaç** tanımlar; `gradient ascent` ile çıkılır (kitaplıklarda eksi işaretle kayıp olarak yazılır).
:::

::: tahmin Kırpma hangi yönde çalışır?
`epsilon = 0.2`. Avantajı pozitif bir eylem için üç farklı oranda kırpılmış amaç ne yazdırılır?

```python
eps, A = 0.2, 2.0

for r in (0.5, 1.0, 1.5):
    kirpik = min(max(r, 1 - eps), 1 + eps)
    print(r, round(min(r * A, kirpik * A), 2))
```

???

```cikti
0.5 1.0
1.0 2.0
1.5 2.4
```
$r = 1{,}5$ iken kırpılmamış değer 3 olurdu; amaç $1{,}2 \times 2 = 2{,}4$'te tavana vuruyor. Oranı 1,5'ten 5'e çıkarsan da değer 2,4 kalır: daha fazla itmenin ödülü yok. $r = 0{,}5$ iken ise değer kırpılmıyor: $0{,}5 \times 2 = 1$; kırpılmış hâli $0{,}8 \times 2 = 1{,}6$ olurdu ama `min` küçük olanı seçer. İyi bir eylemin olasılığını düşürdüysen cezayı tam alırsın.
:::

::: gorev 1 · Kırpılmış amaç (tek örnek)
`kirpilmis_amac(eski_logp, yeni_logp, avantaj, eps)` işlevini yaz.

- `eski_logp`, `yeni_logp`: log-olasılıklar; sıfırdan büyük olmayan sayılar. `avantaj`: sayı. `eps`: `(0, 1)` aralığında sayı.
- `oran = exp(yeni_logp - eski_logp)`. Fark 700'ü aşarsa oran `float`'ta temsil edilemez: `ValueError` (belgeli hata). `kirpik_oran`: oranın `[1 - eps, 1 + eps]` aralığına kırpılmış hâli.
- `amac = min(oran · avantaj, kirpik_oran · avantaj)`.
- `aktif`: gradient akıyor mu? `oran · avantaj <= kirpik_oran · avantaj + 1e-12` ise `True` (kırpılmamış terim `min`'i belirliyor).
- Dönüş: `{'oran': ..., 'amac': ..., 'aktif': bool}`; sayılar 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç oranı kırpıp doğrudan avantajla çarpıyor; `min` yok. Hata yönündeki tam cezayı da kırpıyor: iyi bir eylemi bastıran güncelleme düzeltilmez.

```starter
def kirpilmis_amac(eski_logp, yeni_logp, avantaj, eps):
    import math
    r = math.exp(yeni_logp - eski_logp)
    k = min(max(r, 1 - eps), 1 + eps)
    return {'oran': round(r, 9), 'amac': round(k * avantaj, 9), 'aktif': k == r}
```

```solution
def kirpilmis_amac(eski_logp, yeni_logp, avantaj, eps):
    import math
    def sayi(x):
        return not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x)
    if not sayi(eski_logp) or not sayi(yeni_logp) or eski_logp > 0 or yeni_logp > 0:
        raise ValueError('log-olasılıklar sıfırdan büyük olmayan sayı olmalı')
    if not sayi(avantaj) or not sayi(eps) or not 0 < eps < 1:
        raise ValueError('avantaj sayı, eps (0, 1) aralığında olmalı')
    if yeni_logp - eski_logp > 700:
        raise ValueError('log-olasılık farkı 700 ü aşıyor: oran float ta temsil edilemez')
    r = math.exp(yeni_logp - eski_logp)
    kirpik = min(max(r, 1 - eps), 1 + eps)
    ham, sinirli = r * avantaj, kirpik * avantaj
    return {'oran': round(r, 9), 'amac': round(min(ham, sinirli), 9) + 0.0, 'aktif': ham <= sinirli + 1e-12}
```

```test
need('kirpilmis_amac')
import math, random

L = math.log
eq(kirpilmis_amac(L(0.5), L(0.5), 2.0, 0.2), {'oran': 1.0, 'amac': 2.0, 'aktif': True}, 'güncellemeden önce oran 1')
r = kirpilmis_amac(L(0.4), L(0.6), 2.0, 0.2)
eq((r['oran'], r['amac'], r['aktif']), (1.5, 2.4, False), 'pozitif avantaj, oran tavanın üstünde: kazanç sabitlenir, gradient yok')
r = kirpilmis_amac(L(0.4), L(0.2), 2.0, 0.2)
eq((r['oran'], r['amac'], r['aktif']), (0.5, 1.0, True), 'pozitif avantaj, oran tabanın altında: kırpılmaz, tam ceza')
r = kirpilmis_amac(L(0.4), L(0.2), -2.0, 0.2)
eq((r['amac'], r['aktif']), (-1.6, False), 'negatif avantaj, oran tabanın altında: kazanç sabitlenir')
r = kirpilmis_amac(L(0.4), L(0.6), -2.0, 0.2)
eq((r['amac'], r['aktif']), (-3.0, True), 'negatif avantaj, oran tavanın üstünde: kırpılmaz, tam ceza')
eq(kirpilmis_amac(L(0.5), L(0.55), 1.0, 0.2)['aktif'], True, 'aralık içinde her zaman aktif')
eq(kirpilmis_amac(L(0.3), L(0.9), 0.0, 0.2)['amac'], 0.0, 'avantaj sıfırsa amaç sıfır')
rng = random.Random(2001)
for _ in range(30):
    po, pn = rng.uniform(0.05, 1.0), rng.uniform(0.05, 1.0)
    A, e = round(rng.uniform(-3, 3), 2), rng.choice([0.1, 0.2, 0.3])
    got = kirpilmis_amac(L(po), L(pn), A, e)
    oran = pn / po
    yakin(got['oran'], oran, 'oran olasılıkların bölümü', tol=1e-7)
    yakin(got['amac'], min(oran * A, max(1 - e, min(1 + e, oran)) * A), 'amaç tanımla aynı', tol=1e-7)
    ok(got['amac'] <= oran * A + 1e-7, 'kırpılmış amaç kırpılmamış amaçtan büyük olmaz (kötümser sınır)')
    if abs(oran - 1) <= e - 1e-6:
        eq(got['aktif'], True, 'aralık içinde aktif')
raises(ValueError, kirpilmis_amac, -1000, -1, 1, 0.2, msg='temsil edilemeyen oran belgeli hatayla reddedilir')
raises(ValueError, kirpilmis_amac, -700.5, 0, 1, 0.2, msg='700 üstü log-olasılık farkı reddedilir')
ok(kirpilmis_amac(-700.0, 0.0, 1.0, 0.2)['oran'] > 1e300, 'tam 700 farkta taşma yok')
yakin(kirpilmis_amac(-1000, -999.5, 1, 0.2)['oran'], math.exp(0.5), 'aşırı ama yakın log-olasılıklar sorunsuz', tol=1e-8)
for a in ([None, -1, 1, 0.2], [-1, "x", 1, 0.2], [0.5, -1, 1, 0.2], [-1, 0.5, 1, 0.2], [True, -1, 1, 0.2], [-1, True, 1, 0.2], [float('nan'), -1, 1, 0.2], [float('-inf'), -1, 1, 0.2], [-1, float('nan'), 1, 0.2], [-1, -1, None, 0.2], [-1, -1, True, 0.2], [-1, -1, float('nan'), 0.2], [-1, -1, float('inf'), 0.2], [-1, -1, 1, 0], [-1, -1, 1, 1], [-1, -1, 1, None], [-1, -1, 1, True], [-1, -1, 1, float('nan')]):
    raises(ValueError, kirpilmis_amac, *a, msg='bozuk girdi reddedilir')
```

```hint
`oran = exp(yeni − eski)`; `kirpik = min(max(oran, 1 − eps), 1 + eps)`; `amac = min(oran · A, kirpik · A)`. Gradient yalnız kırpılmamış terim küçük ya da eşitken akar.
```
:::

::: gorev 2 · Bir batch için kayıp ve tanı ölçüleri
`ppo_ozeti(eski_logp, yeni_logp, avantajlar, eps)` işlevini yaz.

- `eski_logp`, `yeni_logp`, `avantajlar`: aynı uzunlukta, boş olmayan sayı listeleri; log-olasılıklar sıfırdan büyük olamaz. `eps`: `(0, 1)`.
- `amac`: Görev 1'deki kırpılmış amacın örnekler üzerindeki ortalaması.
- `kirpilan_pay`: `|oran - 1| > eps` olan örneklerin oranı.
- `yaklasik_kl`: `eski_logp - yeni_logp` farklarının ortalaması.
- `en_buyuk_oran`: örneklerdeki en büyük oran.
- Dönüş: bu dört anahtar; 9 basamağa yuvarlanır.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç kırpılmamış amacı raporluyor ve kırpılan payı hep sıfır veriyor: politika uçup gitse bile tanı ölçüleri hiçbir şey göstermiyor.

```starter
def ppo_ozeti(eski_logp, yeni_logp, avantajlar, eps):
    import math
    oran = [math.exp(n - e) for e, n in zip(eski_logp, yeni_logp)]
    n = len(oran)
    return {'amac': round(sum(r * a for r, a in zip(oran, avantajlar)) / n, 9), 'kirpilan_pay': 0.0, 'yaklasik_kl': round(sum(e - y for e, y in zip(eski_logp, yeni_logp)) / n, 9), 'en_buyuk_oran': round(max(oran), 9)}
```

```solution
def ppo_ozeti(eski_logp, yeni_logp, avantajlar, eps):
    import math
    def sayilar(v):
        return isinstance(v, list) and v and not any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in v)
    if not sayilar(eski_logp) or not sayilar(yeni_logp) or not sayilar(avantajlar):
        raise ValueError('boş olmayan sayı listeleri gerekli')
    if not len(eski_logp) == len(yeni_logp) == len(avantajlar):
        raise ValueError('listeler aynı uzunlukta olmalı')
    if any(x > 0 for x in eski_logp) or any(x > 0 for x in yeni_logp):
        raise ValueError('log-olasılıklar sıfırdan büyük olamaz')
    if isinstance(eps, bool) or not isinstance(eps, (int, float)) or not 0 < eps < 1:
        raise ValueError('eps (0, 1) aralığında olmalı')
    n = len(eski_logp)
    if any(y - e > 700 for e, y in zip(eski_logp, yeni_logp)):
        raise ValueError('log-olasılık farkı 700 ü aşıyor: oran float ta temsil edilemez')
    oranlar = [math.exp(y - e) for e, y in zip(eski_logp, yeni_logp)]
    amac = sum(min(r * a, min(max(r, 1 - eps), 1 + eps) * a) for r, a in zip(oranlar, avantajlar)) / n
    return {
        'amac': round(amac, 9) + 0.0,
        'kirpilan_pay': round(sum(1 for r in oranlar if abs(r - 1) > eps) / n, 9),
        'yaklasik_kl': round(sum(e - y for e, y in zip(eski_logp, yeni_logp)) / n, 9) + 0.0,
        'en_buyuk_oran': round(max(oranlar), 9),
    }
```

```test
need('ppo_ozeti')
import math, random

L = math.log
r = ppo_ozeti([L(0.5), L(0.5)], [L(0.5), L(0.5)], [1.0, -1.0], 0.2)
eq(r, {'amac': 0.0, 'kirpilan_pay': 0.0, 'yaklasik_kl': 0.0, 'en_buyuk_oran': 1.0}, 'güncellemeden önce: oran 1, KL 0')
r = ppo_ozeti([L(0.4), L(0.4)], [L(0.6), L(0.44)], [2.0, 2.0], 0.2)
yakin(r['amac'], (2.4 + 2.2) / 2, 'biri tavanda (2.4), biri aralıkta (2.2)', tol=1e-8)
eq(r['kirpilan_pay'], 0.5, 'iki örnekten biri aralığın dışında')
yakin(r['en_buyuk_oran'], 1.5, 'en büyük oran', tol=1e-8)
ok(r['yaklasik_kl'] < 0, 'örneklenen eylemlerin olasılığı arttıysa bu tahmin negatif çıkabilir', got=r)
r = ppo_ozeti([L(0.5)], [L(0.1)], [1.0], 0.2)
yakin(r['yaklasik_kl'], L(5), 'olasılık beşte bire indi: log 5', tol=1e-8)
eq(r['kirpilan_pay'], 1.0, 'tek örnek, aralığın dışında')
rng = random.Random(2002)
for _ in range(25):
    n = rng.randint(1, 12)
    po = [rng.uniform(0.05, 1.0) for _ in range(n)]
    pn = [rng.uniform(0.05, 1.0) for _ in range(n)]
    A = [round(rng.uniform(-3, 3), 2) for _ in range(n)]
    e = rng.choice([0.1, 0.2, 0.3])
    got = ppo_ozeti([L(x) for x in po], [L(x) for x in pn], A, e)
    oran = [b / a for a, b in zip(po, pn)]
    yakin(got['amac'], sum(min(r * a, max(1 - e, min(1 + e, r)) * a) for r, a in zip(oran, A)) / n, 'rastgele batch te amaç', tol=1e-7)
    yakin(got['kirpilan_pay'], sum(1 for r in oran if abs(r - 1) > e) / n, 'rastgele batch te kırpılan pay', tol=1e-9)
    yakin(got['yaklasik_kl'], sum(L(a) - L(b) for a, b in zip(po, pn)) / n, 'rastgele batch te yaklaşık KL', tol=1e-7)
    yakin(got['en_buyuk_oran'], max(oran), 'rastgele batch te en büyük oran', tol=1e-7)
    ok(got['amac'] <= sum(r * a for r, a in zip(oran, A)) / n + 1e-7, 'kırpılmış amaç kırpılmamıştan büyük olmaz')
raises(ValueError, ppo_ozeti, [-1000.0], [-1.0], [1.0], 0.2, msg='700 üstü log-oran farkı reddedilir')
raises(ValueError, ppo_ozeti, [-700.5], [0.0], [1.0], 0.2, msg='700 sınırı üstü log-oran farkı reddedilir')
ok(ppo_ozeti([-700.0], [0.0], [1.0], 0.2)['en_buyuk_oran'] > 1e300, 'tam 700 farkta taşma yok')
yakin(ppo_ozeti([-500.0], [-499.5], [1.0], 0.2)['en_buyuk_oran'], math.exp(0.5), 'yakın aşırı log-olasılıklar sorunsuz', tol=1e-8)
for a in ([None, [-1.0], [1.0], 0.2], [[-1.0], None, [1.0], 0.2], [[-1.0], [-1.0], None, 0.2], [[], [-1.0], [1.0], 0.2], [[-1.0], [], [1.0], 0.2], [[-1.0], [-1.0], [], 0.2], [[], [], [], 0.2], [(-1.0,), [-1.0], [1.0], 0.2], [[-1.0, -1.0], [-1.0], [1.0], 0.2], [[-1.0], [-1.0], [1.0, 2.0], 0.2], [[0.5], [-1.0], [1.0], 0.2], [[-1.0], [0.5], [1.0], 0.2], [[-1.0], [-1.0], ["1"], 0.2], [[True], [-1.0], [1.0], 0.2], [[float('nan')], [-1.0], [1.0], 0.2], [[float('-inf')], [-1.0], [1.0], 0.2], [[-1.0], [-1.0], [float('inf')], 0.2], [[-1.0], [-1.0], [1.0], 0], [[-1.0], [-1.0], [1.0], 1.0], [[-1.0], [-1.0], [1.0], None], [[-1.0], [-1.0], [1.0], True], [[-1.0], [-1.0], [1.0], float('nan')]):
    raises(ValueError, ppo_ozeti, *a, msg='bozuk girdi reddedilir')
```

```hint
Önce bütün oranları hesapla. Amaç her örnek için `min(r·A, clip(r)·A)`'nın ortalaması; kırpılan pay `abs(r − 1) > eps` sayımının `n`'e oranı; KL `eski − yeni` ortalaması.
```
:::

::: gorev 3 · PPO güncelleme döngüsü
`ppo_guncelle(logitler, ornekler, eps, lr, epoch)` işlevini yaz. Tek durumlu, softmax politikalı bir problemde aynı veriyle birden çok güncelleme adımı atar.

- `logitler`: veriyi toplayan **eski** politikanın logit'leri; boş olmayan sayı listesi. `ornekler`: boş olmayan liste; her öğe `(eylem, avantaj)`. `eps`: `(0, 1)`. `lr`: pozitif sayı. `epoch`: negatif olmayan `int`.
- Eski log-olasılıklar `logitler`'in `log-softmax`'inden hesaplanır ve **sabit** kalır. Oran olasılıkların bölümüyle değil, `exp(yeni_logp - eski_logp)` ile hesaplanır: çok küçük bir eski olasılık `float`'ta sıfıra iner ve bölüm sıfıra bölmeye dönüşür.
- Her epoch'ta, o anki `theta` ile:
  1. Güncel politikayı (softmax) ve her örnek için `oran = pi[a] / pi_eski[a]` hesapla.
  2. Örnek **aktifse** (Görev 1'deki koşul) gradient'e `avantaj · oran · ((k == a) - pi[k])` katkısı yapar; aktif değilse katkısı sıfırdır.
  3. Gradient örnek sayısına bölünür ve `theta ← theta + lr · gradient` uygulanır.
- Dönüş: `{'logitler': [...], 'oranlar': her örnek için son oran, 'kirpilan_pay': son oranlarda |oran - 1| > eps payı}`; 9 basamağa yuvarlanır. Girdi değişmemelidir.
- Bozuk girdi `ValueError`.

KUSURLU başlangıç kırpmayı hiç uygulamıyor: bütün örnekler her epoch'ta aktif. Aynı veriyle çok adım atıldığında oranlar sınırsız büyüyor.

```starter
def ppo_guncelle(logitler, ornekler, eps, lr, epoch):
    import math
    def soft(t):
        m = max(t)
        u = [math.exp(x - m) for x in t]
        return [x / sum(u) for x in u]
    eski = soft(logitler)
    th = [float(x) for x in logitler]
    n = len(ornekler)
    for _ in range(epoch):
        pi = soft(th)
        g = [sum(A * (pi[a] / eski[a]) * ((1.0 if k == a else 0.0) - pi[k]) for a, A in ornekler) / n for k in range(len(th))]
        th = [t + lr * gk for t, gk in zip(th, g)]
    pi = soft(th)
    oran = [pi[a] / eski[a] for a, _ in ornekler]
    return {'logitler': [round(t, 9) for t in th], 'oranlar': [round(r, 9) for r in oran], 'kirpilan_pay': round(sum(1 for r in oran if abs(r - 1) > eps) / n, 9)}
```

```solution
def ppo_guncelle(logitler, ornekler, eps, lr, epoch):
    import math
    def sayi(x):
        return not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x)
    if not isinstance(logitler, list) or not logitler or not all(sayi(x) for x in logitler):
        raise ValueError('logitler boş olmayan sayı listesi olmalı')
    if not isinstance(ornekler, list) or not ornekler:
        raise ValueError('ornekler boş olmayan liste olmalı')
    for o in ornekler:
        if not isinstance(o, (tuple, list)) or len(o) != 2 or isinstance(o[0], bool) or not isinstance(o[0], int) or not 0 <= o[0] < len(logitler) or not sayi(o[1]):
            raise ValueError('örnek (eylem, avantaj) olmalı')
    if not sayi(eps) or not 0 < eps < 1 or not sayi(lr) or not lr > 0:
        raise ValueError('eps (0, 1) aralığında, lr pozitif olmalı')
    if isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 0:
        raise ValueError('epoch negatif olmayan int olmalı')

    def soft(t):
        m = max(t)
        u = [math.exp(x - m) for x in t]
        z = sum(u)
        return [x / z for x in u]

    def log_soft(t):
        m = max(t)
        z = m + math.log(sum(math.exp(x - m) for x in t))
        return [x - z for x in t]

    def oran(lp_yeni, a):
        fark = lp_yeni[a] - eski_lp[a]
        if fark > 700:
            raise ValueError('oran float ta temsil edilemez')
        return math.exp(fark)

    eski_lp = log_soft(logitler)
    th = [float(x) for x in logitler]
    n, d = len(ornekler), len(th)
    for _ in range(epoch):
        pi = soft(th)
        lp = log_soft(th)
        g = [0.0] * d
        for a, A in ornekler:
            r = oran(lp, a)
            kirpik = min(max(r, 1 - eps), 1 + eps)
            if r * A <= kirpik * A + 1e-12:
                for k in range(d):
                    g[k] += A * r * ((1.0 if k == a else 0.0) - pi[k]) / n
        th = [t + lr * gk for t, gk in zip(th, g)]
    lp = log_soft(th)
    oranlar = [oran(lp, a) for a, _ in ornekler]
    return {
        'logitler': [round(t, 9) for t in th],
        'oranlar': [round(r, 9) for r in oranlar],
        'kirpilan_pay': round(sum(1 for r in oranlar if abs(r - 1) > eps) / n, 9),
    }
```

```test
need('ppo_guncelle')
import math, random

def soft(t):
    m = max(t)
    u = [math.exp(x - m) for x in t]
    return [x / sum(u) for x in u]

orn = [(0, 1.0), (1, -1.0)]
r0 = ppo_guncelle([0.0, 0.0], orn, 0.2, 0.5, 0)
eq(r0, {'logitler': [0.0, 0.0], 'oranlar': [1.0, 1.0], 'kirpilan_pay': 0.0}, 'sıfır epoch: politika değişmez')
r1 = ppo_guncelle([0.0, 0.0], orn, 0.2, 0.5, 1)
eq(r1['logitler'], [0.25, -0.25], 'ilk adım: oran 1, bütün örnekler aktif (REINFORCE ile aynı)')
uzun = ppo_guncelle([0.0, 0.0], orn, 0.2, 0.5, 300)
ok(uzun['oranlar'][0] < 1.35, 'çok epoch ta bile iyi eylemin oranı tavanın biraz üstünde durur', got=uzun['oranlar'])
ok(uzun['oranlar'][1] > 0.65, 'kötü eylemin oranı tabanın biraz altında durur', got=uzun['oranlar'])
bir_daha = ppo_guncelle([0.0, 0.0], orn, 0.2, 0.5, 600)
eq(bir_daha['logitler'], uzun['logitler'], 'bütün örnekler kırpılınca güncelleme durur: fazladan epoch bir şey değiştirmez')
dar = ppo_guncelle([0.0, 0.0], orn, 0.05, 0.05, 300)
genis = ppo_guncelle([0.0, 0.0], orn, 0.2, 0.05, 300)
ok(abs(dar['oranlar'][0] - 1) < abs(genis['oranlar'][0] - 1), 'eps küçüldükçe politika eskisine daha yakın kalır', got=(dar['oranlar'], genis['oranlar']))
ok(1.2 < genis['oranlar'][0] < 1.23 and 1.05 < dar['oranlar'][0] < 1.09, 'küçük adımlarla oran tavanı yalnız son adım kadar aşar', got=(dar['oranlar'], genis['oranlar']))
def _ref(logitler, ornekler, eps, lr, epoch):
    eski = soft(logitler)
    th = list(map(float, logitler))
    n = len(ornekler)
    for _ in range(epoch):
        pi = soft(th)
        g = [0.0 for _ in th]
        for a, A in ornekler:
            oran = pi[a] / eski[a]
            sinirli = max(1 - eps, min(1 + eps, oran))
            if oran * A > sinirli * A + 1e-12:
                continue
            for k in range(len(th)):
                g[k] += A * oran * ((k == a) - pi[k]) / n
        th = [th[k] + lr * g[k] for k in range(len(th))]
    return th
rng = random.Random(2003)
for _ in range(15):
    d = rng.randint(1, 4)
    th = [round(rng.uniform(-1, 1), 2) for _ in range(d)]
    orn2 = [(rng.randrange(d), round(rng.uniform(-2, 2), 2)) for _ in range(rng.randint(1, 8))]
    e, lr, ep = rng.choice([0.1, 0.2, 0.3]), rng.choice([0.05, 0.3]), rng.randint(0, 25)
    got = ppo_guncelle(th, orn2, e, lr, ep)
    exp = _ref(th, orn2, e, lr, ep)
    for x, y in zip(got['logitler'], exp):
        yakin(x, y, 'rastgele veride logit ler bağımsız referansla aynı', tol=1e-7)
    eski, yeni = soft(th), soft(exp)
    for o, (a, _) in zip(got['oranlar'], orn2):
        yakin(o, yeni[a] / eski[a], 'oranlar son politikadan', tol=1e-7)
r = ppo_guncelle([-1000.0, 0.0], [(0, 1.0)], 0.2, 0.1, 1)
yakin(r['oranlar'][0], math.exp(0.2), 'eski olasılığı sıfıra inen eylem: iki logit 0.1 er oynar, log-oran 0.2; sıfıra bölme olmaz', tol=1e-6)
eq(ppo_guncelle([1000.0, -1000.0], [(0, 1.0)], 0.2, 0.1, 3), {'logitler': [1000.0, -1000.0], 'oranlar': [1.0], 'kirpilan_pay': 0.0}, 'büyük logit lerde kararlı softmax: taşma yok')
th = [0.5, -0.5]
ppo_guncelle(th, orn, 0.2, 0.1, 3)
eq(th, [0.5, -0.5], 'girdi değişmez')
eq(ppo_guncelle([0.0, 0.0, 0.0], [(0, 3.0), (1, -3.0), (2, 0.0)], 0.3, 1.0, 1)['kirpilan_pay'], 0.666666667, 'üç örnekten ikisi kırpılır: 2 / 3 (9 basamak)')
raises(ValueError, ppo_guncelle, [-1000.0, 0.0], [(0, 1000.0)], 0.2, 2.0, 2, msg='aşırı güncellemede oran taşması yakalanır')
raises(ValueError, ppo_guncelle, [-700.5, 0.0], [(0, 1000.0)], 0.2, 2.0, 1, msg='700 sınırı üstü log-oran farkı yakalanır')
iyi = [(0, 1.0)]
for a in ([None, iyi, 0.2, 0.1, 1], [[], iyi, 0.2, 0.1, 1], [(0.0,), iyi, 0.2, 0.1, 1], [[True], iyi, 0.2, 0.1, 1], [[float('nan')], iyi, 0.2, 0.1, 1], [[float('inf')], iyi, 0.2, 0.1, 1], [[0.0], None, 0.2, 0.1, 1], [[0.0], [], 0.2, 0.1, 1], [[0.0], (iyi[0],), 0.2, 0.1, 1], [[0.0], ['kotu'], 0.2, 0.1, 1], [[0.0], [123], 0.2, 0.1, 1], [[0.0], [(1, 1.0)], 0.2, 0.1, 1], [[0.0], [(-1, 1.0)], 0.2, 0.1, 1], [[0.0], [(True, 1.0)], 0.2, 0.1, 1], [[0.0], [(False, 1.0)], 0.2, 0.1, 1], [[0.0], [(0.0, 1.0)], 0.2, 0.1, 1], [[0.0], [(0,)], 0.2, 0.1, 1], [[0.0], [(0, None)], 0.2, 0.1, 1], [[0.0], [(0, True)], 0.2, 0.1, 1], [[0.0], [(0, float('nan'))], 0.2, 0.1, 1], [[0.0], iyi, 0, 0.1, 1], [[0.0], iyi, 1, 0.1, 1], [[0.0], iyi, True, 0.1, 1], [[0.0], iyi, float('nan'), 0.1, 1], [[0.0], iyi, 0.2, 0, 1], [[0.0], iyi, 0.2, True, 1], [[0.0], iyi, 0.2, float('nan'), 1], [[0.0], iyi, 0.2, float('inf'), 1], [[0.0], iyi, 0.2, 0.1, -1], [[0.0], iyi, 0.2, 0.1, 1.0], [[0.0], iyi, 0.2, 0.1, True]):
    raises(ValueError, ppo_guncelle, *a, msg='bozuk girdi reddedilir')
```

```hint
Eski olasılıkları döngüden önce bir kez hesapla. Her epoch'ta güncel politikayı yeniden hesapla; her örnek için oranı ve aktifliği bul; yalnız aktif örneklerin katkısını topla.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Aşağıdaki iskeleti kendi cümlelerinle doldur; her adım bu derste hesapladığın bir sayıya ya da örneğe dayanır.

1. **Çerçeve (15 sn).** "Bu yöntemde veri modelin kendisinden gelir. Tek bir kötü güncelleme kötü veri üretir ve eğitim çöker."
2. **Oran (30 sn).** "Yeni politika bir eylemi eskisinden kaç kat daha olası buluyor? Bu oranı izleriz."
3. **Tavan (30 sn).** Tahmin adımı: oran 1,5 olunca kazanç 2,4'te sabitleniyor. "Daha fazla itmenin ödülü yok; ama hata yönünde ceza tam."
4. **İzleme (25 sn).** "Eğitimi izlerken iki sayıya bakılır: kaç örnek kırpıldı ve politika ne kadar değişti."
5. **Kapanış (20 sn).** "Sohbet botlarının insan tercihlerine göre ince ayarı yıllarca bu yöntemle yapıldı."
:::

::: anlat Sınır
Bu ders PPO'nun kırpılmış amacını tek durumlu, logit'leri doğrudan parametre alan bir politikayla anlatır. Gerçek PPO'da politika ve değer fonksiyonu sinir ağlarıdır; amaç üç terimden oluşur (kırpılmış politika amacı, değer kaybı ve bir `entropy` ödülü) ve güncellemeler karıştırılmış `minibatch`'lerle yapılır. Kırpma, politikanın eski politikadan uzaklaşmasını **garanti etmez**; yalnız uzaklaşmanın teşvikini kaldırır. Görev 3'te gördüğün gibi oran tavanı bir miktar aşabilir, çünkü son aktif adım sınırı geçirebilir; paylaşılan ağırlıklarda bir örnek için atılan adım başka örneklerin oranını da değiştirir. Bu yüzden uygulamalar yaklaşık KL'yi izler ve eşik aşılınca erken durur. Yaklaşık KL yalnız örneklenen eylemlerden hesaplanır ve negatif çıkabilir; gerçek KL negatif olmaz. PPO'nun başarısı büyük ölçüde uygulama ayrıntılarına bağlıdır (avantaj normalleştirme, öğrenme oranı takvimi, gradient kırpma, gözlem ölçekleme); aynı algoritmanın iki uygulaması çok farklı sonuç verebilir. `On-policy`'dir: veri birkaç epoch kullanılır ama sonra atılır, bu yüzden off-policy yöntemlerden daha çok etkileşim ister. Bir dil modelinin hizalanmasında ödül bir insan tercih modelinden gelir; o modelin hataları politikaya aynen aktarılır.

Kaynaklar: [Schulman vd. 2017 - Proximal Policy Optimization Algorithms](https://arxiv.org/abs/1707.06347), [Schulman vd. 2015 - Trust Region Policy Optimization](https://arxiv.org/abs/1502.05477), [Engstrom vd. 2020 - Implementation Matters in Deep Policy Gradients](https://arxiv.org/abs/2005.12729), [Huang vd. 2022 - The 37 Implementation Details of Proximal Policy Optimization](https://iclr-blog-track.github.io/2022/03/25/ppo-implementation-details/).
:::

::: dusun
Bir PPO eğitiminde kırpılan pay ilk yüz güncellemede 0,05 civarında, sonra 0,6'ya çıkıyor ve ortalama getiri düşmeye başlıyor. Bu derste gördüğün düğmelerden (öğrenme oranı, epoch sayısı, `eps`) hangisini, hangi yönde değiştirirdin? Hangisinin soruna yol açtığını ayırt etmek için hangi ölçüme bakardın?
:::

::: ozet
- Policy gradient'te kötü bir güncelleme kötü veri üretir ve eğitim çökebilir; PPO adımın büyüklüğünü sınırlar.
- Olasılık oranı `r = π_yeni(a) / π_eski(a)`, politikanın bir örnekte ne kadar değiştiğini ölçer.
- Kırpılmış amaç `min(r·A, clip(r, 1 − ε, 1 + ε)·A)` kötümser bir sınırdır: kazanç yönünde tavan koyar, hata yönünde tam ceza verir.
- Kırpılan örneklerin gradient'i sıfırdır; aynı veriyle çok epoch atıldığında güncelleme kendiliğinden durur.
- Kırpılan pay ve yaklaşık KL eğitimin tanı ölçüleridir; kırpma bir garanti değil, bir teşvik düzenidir.
:::
