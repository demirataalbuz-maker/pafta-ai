---
id: ai-temel-30
title: Mamba Durum Uzayı Modelleri ve State Collapse · Seçici Bellek Sönümü
summary: Seçici State Space Model (SSM) katmanında Δ_t ayrıklaştırmasını, durum yinelemesini (recurrence) ve büyük Δ_t sıçramalarının ürettiği state collapse etkisini GPU'da ölç.
esleme: ai-temel-05, ai-temel-07, ai-temel-08
timeout: 60
---

::: anlat Sabit boyutlu bellek uzun bağlamı nasıl taşır ve nasıl silinir?
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Mamba gibi seçici `State Space Model` (SSM) mimarileri, Transformer'ın $O(T^2)$ dikkat ve büyüyen KV-cache maliyetini girdi bağımlı $(\Delta_t, B_t, C_t)$ parametreleriyle sabit boyutlu $h_t$ durumunda $O(T)$ zamana indirir | İlk üç görev: `veri/mamba_ssm.json` içindeki **sentetik** diyagonal durum parametreleri ve sekanslar. Final: SmolLM2-135M'in gerçek token gömmeleriyle eğitilen seçici SSM'de bellek görevi, sözlük taramasıyla bulunan büyük Δ tokeniyle bellek silme/üzerine yazma saldırısı ve tutma oranı tanısı | Donanım duyarlı paralel tarama (parallel associative scan) çekirdeğinin SRAM hızlandırma oranını doğrudan ölçemez |
| Adım boyutu $\Delta_t$ büyüdüğünde $\bar{A}_t = \exp(\Delta_t A) \to 0$ olur ve geçmiş bellek durumu tek adımda silinir (`state collapse` / memory flush) | ZOH diyagonal ayrıklaştırma $\exp(\Delta A)$, doğrusal durum yinelemesi $h_t = \bar{A}_t h_{t-1} + \bar{B}_t x_t$ ve çökme tanısı | Hibrit (Transformer + Mamba, ör. Jamba) modellerin de aynı derecede bellek silinmesi yaşadığını kanıtlamaz |

> [!NOT]
> Görevler `veri/mamba_ssm.json` dosyasını okur; dosya sentetiktir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; değişiklikler taşınmaz, **kalıcılık yoktur**. Ekranda ayrı dosya görüntüleyici yoktur; içeriği görmek için `print` kullan. Gizli testler ayrıdır. Final yeni model indirmez ve GPU varsa onu kullanır.

ai-temel-05 ve ai-temel-07 Transformer mimarisinin her geçmiş token için bir anahtar-değer (KV) vektörü sakladığını inceler: sekans uzadıkça bellek doğrusal, dikkat hesabı karesel büyür. **Peki geçmişi büyüyen bir tabloda tutmak yerine, girdiyle seçici olarak güncellenen sabit boyutlu bir durum vektörü $h_t \in \mathbb{R}^N$ içinde sıkıştırabilir miyiz?**

**Sürekli zamandan ayrık zamana `State Space Model` (SSM).** Sürekli zamanlı doğrusal sistem $h'(t) = A h(t) + B x(t)$ diferansiyel denklemini izler. Kararlılık (Hurwitz koşulu) için diyagonal $A$ matrisinin tüm elemanları negatif seçilir ($A_i < 0$). Mamba (Gu ve Dao 2023), her token $x_t$ geldiğinde girdiye bağlı bir adım boyutu $\Delta_t = \text{softplus}(W_\Delta x_t) > 0$ üretir ve parametreleri ayrıklaştırır:
$$\bar{A}_{t, i} = \exp(\Delta_t \cdot A_i), \qquad \bar{B}_{t, i} = \Delta_t \cdot B_{t, i}$$
Burada iki farklı ayrıklaştırma kuralı birlikte kullanılır: $\bar A$ için tam üstel geçiş, $\bar B$ için $\Delta B$ ölçeklemesi. Tam ZOH, diyagonal $A_i<0$ için $\bar B_i=\frac{\exp(\Delta A_i)-1}{A_i}B_i$ verir ([Mamba, Denklem 4](https://arxiv.org/html/2312.00752v2#S2.E4)); küçük $|\Delta A_i|$ için $\exp(\Delta A_i)-1\approx\Delta A_i$ ile $\Delta B_i$ elde edilir. Örneğin $A=-1,B=1,\Delta=2$ için tam ZOH giriş katsayısı $1-e^{-2}\approx0.8647$, bu görevin katsayısı ise $2$'dir. Görev bu iki katsayıyı eşit saymaz; sözleşmedeki $\Delta B$ kuralını uygular. Böylece bellek geçişini koruyup giriş ölçeklemesinin yaklaşımını açıkça ayırır.

Ardından durum vektörü doğrusal yinelemeyle güncellenir:
$$h_t = \bar{A}_t \odot h_{t-1} + \bar{B}_t \cdot x_t$$

**Seçicilik (Selectivity) ve `state collapse` mekanizması.** Buradaki $\Delta_t$ klasik RNN'lerdeki unutma kapısının (forget gate) sürekli zamanlı karşılığıdır:
- $\Delta_t \to 0$ olduğunda $\bar{A}_t = \exp(0) = 1$ ve $\bar{B}_t = 0$ olur: model mevcut $x_t$ girdisini yok sayar ve geçmiş durumu $h_{t-1}$ **olduğu gibi korur**.
- $\Delta_t$ çok büyüdüğünde ($\Delta_t \gg 1$) ise $A_i < 0$ olduğundan $\bar{A}_{t, i} = \exp(\Delta_t A_i) \approx 0$ olur! Ortalama tutma oranı (`tutma_orani` $= \frac{1}{N}\sum_i \bar{A}_{t, i}$) sıfıra çakılır ve geçmiş bellek $h_{t-1}$ tek adımda silinir (`state collapse`).

**Saldırgan ne dener?** Uzun bağlamlı bir SSM modelinde sistem istemi (system prompt) veya güvenlik kısıtı sekansın başında verilmişse, saldırgan araya yüksek $\Delta_t$ üretecek ("belleği sıfırlayacak") şok token dizileri enjekte eder. Transformer'da eski tokenların KV önbelleği fiziksel olarak dururken, saf SSM'de küçük $\bar{A}_t$ önceki durumun o bileşendeki katkısını bastırır. Bu, tek başına sistem isteminin bütün katmanlardan silindiğini veya güvenlik kısıtının aşıldığını kanıtlamaz; sonraki deney yalnız eğitilen küçük SSM'nin bellek görevini ölçer.

**Savunma neden kırılır?** Yalnızca son çıktının doğruluğuna bakılıp ara adımlardaki `tutma_orani` ($\bar{A}_t$) ve durum normu $\|h_t\|_2$ izlenmezse, hangi token adımında geçmiş bağlamın çöktüğü tespit edilemez.

**Görev 1'de sık tuzaklar:** $\bar{A}_i = \exp(\Delta \cdot A_i)$ yerine birinci dereceden Euler ($1 + \Delta \cdot A_i$) kullanmak (büyük $\Delta$'da negatif olasılık/kararsızlık üretir!) veya $A_i \ge 0$ durumunu reddetmemek.

Kaynaklar: [Gu ve Dao 2023 - Mamba: Linear-Time Sequence Modeling with Selective State Spaces](https://arxiv.org/abs/2312.00752), [Jelassi vd. 2024 - Repeat After Me: Transformers are Better than State Space Models at Copying](https://arxiv.org/abs/2402.01032), [Waleffe vd. 2024 - An Empirical Study of Mamba-based Language Models](https://arxiv.org/abs/2406.07887). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Köprü: ai-temel-07 Transformer KV-cache maliyetini, ai-temel-08 uzun bağlamda ortada kaybolma (lost-in-the-middle) etkisini inceler; bu ders SSM'lerin sabit bellekli alternatifini ve durum çökmesi sınırını gösterir.
:::

::: tahmin Adım boyutu Δ büyüdüğünde geçmiş durum çarpanı ne olur?
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
import math
a_diag = [-1.0, -2.0, -4.0]
for delta in (0.05, 0.50, 3.50):
    a_bar = [round(math.exp(delta * a), 4) for a in a_diag]
    print("delta=%.2f -> a_bar=%s | tutma=%.4f" % (delta, a_bar, sum(a_bar) / len(a_bar)))
```
???
```cikti
delta=0.05 -> a_bar=[0.9512, 0.9048, 0.8187] | tutma=0.8916
delta=0.50 -> a_bar=[0.6065, 0.3679, 0.1353] | tutma=0.3699
delta=3.50 -> a_bar=[0.0302, 0.0009, 0.0] | tutma=0.0104
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: `delta=3.50` olduğunda geçmiş durum $h_{t-1}$ vektörünün yaklaşık yüzde kaçı hayatta kalır? Sonra üç kusurlu başlangıç kodunu çalıştır ve her birinin neyi kaçırdığını önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · Seçici SSM ayrıklaştırması (ZOH ve Euler)
`ssm_ayriklastir(delta, a_diag, b_vektor)`: `delta` bool olmayan sonlu sayı ve `delta > 0`; `a_diag` ve `b_vektor` aynı uzunlukta (`N >= 1`) boş olmayan `list`, elemanları bool olmayan sonlu sayı ve kararlılık için tüm `a_diag[i] < 0`. $\bar{A}_i = \exp(\text{delta} \cdot A_i)$, $\bar{B}_i = \text{delta} \cdot B_i$ ve `tutma_orani` $= \frac{1}{N}\sum \bar{A}_i$ hesaplayarak `{"a_bar": [...], "b_bar": [...], "tutma_orani": float}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-30")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def ssm_ayriklastir(delta, a_diag, b_vektor):
    a_bar = [1.0 + delta * a for a in a_diag]
    b_bar = [delta * b for b in b_vektor]
    return {"a_bar": a_bar, "b_bar": b_bar, "tutma_orani": sum(a_bar) / len(a_bar)}

from ai_temel_veri import json_yukle
v = json_yukle("veri/mamba_ssm.json")
for d in (0.10, 3.50):
    print("delta=%.2f ->" % d, ssm_ayriklastir(d, v["a_diag"], v["b_vektor"]))
```
```test
def sinama1(f):
    import math, random
    def _r(d, a, b):
        ab = [math.exp(d * x) for x in a]
        bb = [d * x for x in b]
        return {"a_bar": ab, "b_bar": bb, "tutma_orani": sum(ab) / len(ab)}
    def _y(x, y):
        return set(x) == {"a_bar", "b_bar", "tutma_orani"} and abs(x["tutma_orani"] - y["tutma_orani"]) < 1e-12 and len(x["a_bar"]) == len(y["a_bar"]) and all(abs(p - q) < 1e-12 for p, q in zip(x["a_bar"], y["a_bar"])) and all(abs(p - q) < 1e-12 for p, q in zip(x["b_bar"], y["b_bar"]))
    try:
        a = [-1.0, -2.0]; b = [0.5, -1.0]; old = (list(a), list(b))
        c = f(0.5, a, b)
        if not _y(c, _r(0.5, a, b)) or (a, b) != old: return False
        if any(v <= 0 or v >= 1 for v in f(5.0, [-1.0, -3.0], [1.0, 1.0])["a_bar"]): return False
        rng = random.Random(30)
        for _ in range(25):
            n = rng.randint(1, 7); d = rng.uniform(0.01, 4.0)
            av = [rng.uniform(-5.0, -0.05) for _ in range(n)]
            bv = [rng.uniform(-2.0, 2.0) for _ in range(n)]
            if not _y(f(d, list(av), list(bv)), _r(d, av, bv)): return False
        for bad in (
            (0.0, [-1.0], [1.0]), (-0.5, [-1.0], [1.0]), (True, [-1.0], [1.0]),
            (0.5, [], []), (0.5, [-1.0], [1.0, 2.0]), (0.5, [0.0], [1.0]),
            (0.5, [0.5], [1.0]), (0.5, [-1.0, True], [1.0, 1.0]),
            (float("nan"), [-1.0], [1.0]), (0.5, [-1.0], [float("inf")])
        ):
            try:
                f(*bad)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sinama1(ssm_ayriklastir), "üstel ZOH ayrıklaştırma, Hurwitz negatiflik kısıtı ve geçersiz girdi")
for ad, mut in [
    ("Euler 1 + d*A", lambda d, a, b: {"a_bar": [1.0 + d * x for x in a], "b_bar": [d * x for x in b], "tutma_orani": 0.5}),
    ("b_bar ölçeklenmemiş", lambda d, a, b: dict(ssm_ayriklastir(d, a, b), b_bar=list(b))),
    ("tutma oranı toplam", lambda d, a, b: dict(ssm_ayriklastir(d, a, b), tutma_orani=sum(ssm_ayriklastir(d, a, b)["a_bar"])))
]:
    ok(not sinama1(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(ssm_ayriklastir, _il.import_module('ai_gercek_ai_temel_30').referans_ssm_ayriklastir, (0.1, [-1.0, -2.0, -4.0], [0.5, -0.5, 1.0]), tohum=2559)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def ssm_ayriklastir(delta, a_diag, b_vektor):
    if isinstance(delta, bool) or not isinstance(delta, (int, float)) or not math.isfinite(delta) or delta <= 0.0:
        raise ValueError("delta")
    if not isinstance(a_diag, list) or not isinstance(b_vektor, list) or not a_diag or len(a_diag) != len(b_vektor):
        raise ValueError("boyut")
    for a, b in zip(a_diag, b_vektor):
        if isinstance(a, bool) or not isinstance(a, (int, float)) or not math.isfinite(a) or a >= 0.0:
            raise ValueError("a_diag")
        if isinstance(b, bool) or not isinstance(b, (int, float)) or not math.isfinite(b):
            raise ValueError("b_vektor")
    a_bar = [math.exp(delta * a) for a in a_diag]
    b_bar = [delta * b for b in b_vektor]
    return {
        "a_bar": a_bar,
        "b_bar": b_bar,
        "tutma_orani": sum(a_bar) / float(len(a_bar)),
    }

from ai_temel_veri import json_yukle
v = json_yukle("veri/mamba_ssm.json")
for d in (0.10, 3.50):
    print("delta=%.2f ->" % d, ssm_ayriklastir(d, v["a_diag"], v["b_vektor"]))
```
```hint
Her `a in a_diag` için `a < 0` kontrolü yap ve `math.exp(delta * a)` ile `a_bar` listesini oluştur.
```
:::

::: anlat Seçici durum uzayı yinelemesi (SSM Recurrence)
Başlangıç durumu $h_{-1} = [0.0, \dots, 0.0] \in \mathbb{R}^N$ olarak başlar. Her zaman adımı $t = 0, \dots, T-1$ için:
$$h_{t, i} = \bar{A}_{t, i} \cdot h_{t-1, i} + \bar{B}_{t, i} \cdot x_t$$
güncellemesi uygulanır ve o adımdaki durum vektörünün Öklidyen L2 normu $\|h_t\|_2 = \sqrt{\sum_{i=0}^{N-1} h_{t, i}^2}$ `norm_izleri` listesine kaydedilir.

**Görev 2'de sık tuzaklar:** Önceki durum $h_{t-1}$'i $\bar{A}_t$ ile çarpmadan doğrudan toplamak veya her adımda durumu sıfırlamak!
:::

::: gorev 2 · SSM durum yinelemesi ve norm izi
`ssm_adim_izle(a_bar_adimlar, b_bar_adimlar, x_adimlar)`: `a_bar_adimlar` ve `b_bar_adimlar` aynı uzunlukta ($T \ge 1$) `list`, her eleman aynı durum boyutunda ($N \ge 1$) sonlu sayı listesi ve `0 <= a_bar_adimlar[t][i] <= 1`; `x_adimlar` uzunluğu $T$ olan sonlu sayı listesi. $h_{-1} = 0$ başlangıcıyla her adımda $h_t = \bar{A}_t \odot h_{t-1} + \bar{B}_t x_t$ yinelemesini yürüt ve `{"son_durum": list[float], "norm_izleri": list[float]}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-30")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def ssm_adim_izle(a_bar_adimlar, b_bar_adimlar, x_adimlar):
    N = len(a_bar_adimlar[0])
    h = [0.0] * N
    normlar = []
    for ab, bb, x in zip(a_bar_adimlar, b_bar_adimlar, x_adimlar):
        h = [bb[i] * x for i in range(N)]
        normlar.append(math.sqrt(sum(v * v for v in h)))
    return {"son_durum": h, "norm_izleri": normlar}

from ai_temel_veri import json_yukle
v = json_yukle("veri/mamba_ssm.json")
for s in v["sekanslar"]:
    ab_l = [[math.exp(d * a) for a in v["a_diag"]] for d in s["deltalar"]]
    bb_l = [[d * b for b in v["b_vektor"]] for d in s["deltalar"]]
    print(s["ad"], ssm_adim_izle(ab_l, bb_l, s["x_adimlar"]))
```
```test
def sinama2(f):
    import copy, math, random
    def _r(ab, bb, xl):
        h = [0.0] * len(ab[0]); nl = []
        for a, b, x in zip(ab, bb, xl):
            h = [a[i] * h[i] + b[i] * x for i in range(len(h))]
            nl.append(math.sqrt(sum(v * v for v in h)))
        return {"son_durum": h, "norm_izleri": nl}
    def _y(a, b):
        return set(a) == {"son_durum", "norm_izleri"} and len(a["son_durum"]) == len(b["son_durum"]) and len(a["norm_izleri"]) == len(b["norm_izleri"]) and all(abs(p - q) < 1e-12 for p, q in zip(a["son_durum"], b["son_durum"])) and all(abs(p - q) < 1e-12 for p, q in zip(a["norm_izleri"], b["norm_izleri"]))
    try:
        ab = [[0.5, 0.5], [0.5, 0.5]]; bb = [[1.0, 0.0], [1.0, 0.0]]; xl = [2.0, 2.0]
        old = copy.deepcopy((ab, bb, xl))
        c = f(ab, bb, xl)
        if not _y(c, {"son_durum": [3.0, 0.0], "norm_izleri": [2.0, 3.0]}) or (ab, bb, xl) != old:
            return False
        try:
            f([[]], [[]], [1.0])
            return False
        except ValueError:
            pass
        rng = random.Random(3030)
        for _ in range(25):
            T = rng.randint(1, 6); N = rng.randint(1, 5)
            a_l = [[rng.uniform(0.0, 1.0) for _ in range(N)] for _ in range(T)]
            b_l = [[rng.uniform(-2.0, 2.0) for _ in range(N)] for _ in range(T)]
            x_l = [rng.uniform(-3.0, 3.0) for _ in range(T)]
            if not _y(f(copy.deepcopy(a_l), copy.deepcopy(b_l), list(x_l)), _r(a_l, b_l, x_l)):
                return False
        for bad in (
            ([], [], []), ([[0.5]], [[0.5]], [1.0, 2.0]),
            ([[0.5], [0.5, 0.5]], [[0.5], [0.5, 0.5]], [1.0, 1.0]),
            ([[-0.1]], [[0.5]], [1.0]), ([[1.2]], [[0.5]], [1.0]),
            ([[True]], [[0.5]], [1.0]), ([[0.5]], [[0.5]], [float("nan")])
        ):
            try:
                f(*bad)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sinama2(ssm_adim_izle), "durum birikimi, L2 norm izi ve geçersiz girdi")
for ad, mut in [
    ("geçmiş durum unutulur", lambda ab, bb, xl: {"son_durum": [bb[-1][i] * xl[-1] for i in range(len(ab[0]))], "norm_izleri": [0.0] * len(xl)}),
    ("a_bar çarpanı yok", lambda ab, bb, xl: dict(ssm_adim_izle([[1.0] * len(ab[0]) for _ in ab], bb, xl))),
    ("norm karesi", lambda ab, bb, xl: dict(ssm_adim_izle(ab, bb, xl), norm_izleri=[v * v for v in ssm_adim_izle(ab, bb, xl)["norm_izleri"]]))
]:
    ok(not sinama2(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(ssm_adim_izle, _il.import_module('ai_gercek_ai_temel_30').referans_ssm_izle, ([[0.9048374180359595, 0.8187307530779818, 0.6703200460356393], [0.8607079764250578, 0.7408182206817179, 0.5488116360940265], [0.8869204367171575, 0.7866278610665535, 0.6187833918061408], [0.9048374180359595, 0.8187307530779818, 0.6703200460356393]], [[0.05, -0.05, 0.1], [0.075, -0.075, 0.15], [0.06, -0.06, 0.12], [0.05, -0.05, 0.1]], [1.5, 0.8, -0.5, 1.0]), tohum=2302)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def ssm_adim_izle(a_bar_adimlar, b_bar_adimlar, x_adimlar):
    if not isinstance(a_bar_adimlar, list) or not isinstance(b_bar_adimlar, list) or not isinstance(x_adimlar, list):
        raise ValueError("liste")
    T = len(x_adimlar)
    if T < 1 or len(a_bar_adimlar) != T or len(b_bar_adimlar) != T:
        raise ValueError("zaman_boyut")
    N = None
    for t in range(T):
        ab, bb, x = a_bar_adimlar[t], b_bar_adimlar[t], x_adimlar[t]
        if not isinstance(ab, list) or not isinstance(bb, list) or not ab or len(ab) != len(bb):
            raise ValueError("durum_boyut")
        if N is not None and len(ab) != N:
            raise ValueError("n_farkli")
        N = len(ab)
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
            raise ValueError("x_sayi")
        for a, b in zip(ab, bb):
            if isinstance(a, bool) or not isinstance(a, (int, float)) or not math.isfinite(a) or not 0.0 <= a <= 1.0:
                raise ValueError("a_bar")
            if isinstance(b, bool) or not isinstance(b, (int, float)) or not math.isfinite(b):
                raise ValueError("b_bar")
    h = [0.0] * N
    normlar = []
    for t in range(T):
        ab, bb, x = a_bar_adimlar[t], b_bar_adimlar[t], x_adimlar[t]
        h = [ab[i] * h[i] + bb[i] * x for i in range(N)]
        normlar.append(math.sqrt(sum(v * v for v in h)))
    return {"son_durum": h, "norm_izleri": normlar}

if __name__ == "__main__":
    from ai_temel_veri import json_yukle
    v = json_yukle("veri/mamba_ssm.json")
    for s in v["sekanslar"]:
        ab_l = [[math.exp(d * a) for a in v["a_diag"]] for d in s["deltalar"]]
        bb_l = [[d * b for b in v["b_vektor"]] for d in s["deltalar"]]
        print(s["ad"], ssm_adim_izle(ab_l, bb_l, s["x_adimlar"]))
```
```hint
Her adımda `h = [ab[i] * h[i] + bb[i] * x for i in range(N)]` ile durumu güncelle ve L2 normunu `normlar` listesine ekle.
```
:::

::: anlat State collapse (durum çökmesi) tanısı
Bir sekans boyunca her zaman adımı $t \in \{0, \dots, T-1\}$ için durum normu `norm_izleri[t]` ve ortalama tutma oranı `tutma_orani_izleri[t]` incelenir.
- Eğer `norm_izleri[t] < min_norm` **veya** `tutma_orani_izleri[t] < max_oran` ise $t$ adımı `cokme_adimlari` listesine eklenir.
- `cokme_var`: `bool(len(cokme_adimlari) > 0)`.
- `en_dusuk_tutma`: `float(min(tutma_orani_izleri))`.

Düşük norm tek başına bilgi kaybını, yüksek ortalama tutma da her bileşenin korunduğunu kanıtlamaz. Bu eşikler görevde tanımlanan bir tanı kuralıdır.

**Görev 3'te sık tuzaklar:** İki çökme koşulunu `or` yerine `and` ile bağlamak (giriş $\bar{B}_t x_t$ büyükken $\bar{A}_t \approx 0$ olsa bile norm yüksek kalabilir ama önceki durumun katkısı çok küçülmüştür!).
:::

::: gorev 3 · State collapse tanı raporu
`durum_cokme_tanisi(norm_izleri, tutma_orani_izleri, min_norm, max_oran)`: `norm_izleri` ve `tutma_orani_izleri` aynı uzunlukta ($T \ge 1$) boş olmayan `list`; `norm_izleri` elemanları `>= 0`, `tutma_orani_izleri` elemanları `0 <= r <= 1` sonlu sayı; `min_norm > 0` ve `0 < max_oran <= 1` bool olmayan sonlu sayılar. `{"cokme_adimlari": list[int], "cokme_var": bool, "en_dusuk_tutma": float}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-30")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def durum_cokme_tanisi(norm_izleri, tutma_orani_izleri, min_norm, max_oran):
    return {
        "cokme_adimlari": [],
        "cokme_var": False,
        "en_dusuk_tutma": min(tutma_orani_izleri),
    }

from ai_temel_veri import json_yukle
v = json_yukle("veri/mamba_ssm.json")
for s in v["sekanslar"]:
    ab_l = [[math.exp(d * a) for a in v["a_diag"]] for d in s["deltalar"]]
    bb_l = [[d * b for b in v["b_vektor"]] for d in s["deltalar"]]
    tutma_l = [sum(r) / len(r) for r in ab_l]
    h = [0.0] * len(v["a_diag"])
    norm_l = []
    for ab, bb, x in zip(ab_l, bb_l, s["x_adimlar"]):
        h = [ab[i] * h[i] + bb[i] * x for i in range(len(h))]
        norm_l.append(math.sqrt(sum(u * u for u in h)))
    print(s["ad"], durum_cokme_tanisi(norm_l, tutma_l, v["min_norm"], v["max_oran"]))
```
```test
def sinama3(f):
    import random
    def _r(nl, tl, mn, mo):
        ad = [t for t in range(len(nl)) if nl[t] < mn or tl[t] < mo]
        return {"cokme_adimlari": ad, "cokme_var": bool(ad), "en_dusuk_tutma": float(min(tl))}
    try:
        nl = [0.5, 0.4, 0.05, 0.3]; tl = [0.8, 0.1, 0.7, 0.9]; old = (list(nl), list(tl))
        c = f(nl, tl, 0.1, 0.2)
        if c != {"cokme_adimlari": [1, 2], "cokme_var": True, "en_dusuk_tutma": 0.1} or (nl, tl) != old:
            return False
        if f([0.5, 0.6], [0.8, 0.9], 0.1, 0.2) != {"cokme_adimlari": [], "cokme_var": False, "en_dusuk_tutma": 0.8}:
            return False
        # Eşik eşitliği alarm değildir; yalnız kesin küçüklük alarmdır.
        if f([0.25, 0.249, 0.25], [0.3, 0.3, 0.299], 0.25, 0.3) != {"cokme_adimlari": [1, 2], "cokme_var": True, "en_dusuk_tutma": 0.299}: return False
        if f([0.25], [0.3], 0.25, 0.3) != {"cokme_adimlari": [], "cokme_var": False, "en_dusuk_tutma": 0.3}: return False
        rng = random.Random(3003)
        for _ in range(25):
            T = rng.randint(1, 8)
            n_v = [rng.uniform(0.0, 2.0) for _ in range(T)]
            t_v = [rng.uniform(0.0, 1.0) for _ in range(T)]
            if f(list(n_v), list(t_v), 0.25, 0.3) != _r(n_v, t_v, 0.25, 0.3):
                return False
        for bad in (
            ([], [], 0.1, 0.2), ([0.5], [0.5, 0.5], 0.1, 0.2),
            ([-0.1], [0.5], 0.1, 0.2), ([0.5], [-0.1], 0.1, 0.2), ([0.5], [1.2], 0.1, 0.2),
            ([0.5], [0.5], 0.0, 0.2), ([0.5], [0.5], 0.1, 0.0), ([0.5], [0.5], 0.1, 1.1),
            ([0.5], [0.5], True, 0.2), ([0.5], [0.5], 0.1, float("nan"))
        ):
            try:
                f(*bad)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sinama3(durum_cokme_tanisi), "norm veya tutma oranı çökmesi, en düşük tutma ve geçersiz girdi")
for ad, mut in [
    ("and bağlacı", lambda nl, tl, mn, mo: {"cokme_adimlari": [t for t in range(len(nl)) if nl[t] < mn and tl[t] < mo], "cokme_var": True, "en_dusuk_tutma": min(tl)}),
    ("hep temiz", lambda nl, tl, mn, mo: {"cokme_adimlari": [], "cokme_var": False, "en_dusuk_tutma": min(tl)}),
    ("en düşük yerine maksimum", lambda nl, tl, mn, mo: dict(durum_cokme_tanisi(nl, tl, mn, mo), en_dusuk_tutma=max(tl)))
]:
    ok(not sinama3(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(durum_cokme_tanisi, _il.import_module('ai_gercek_ai_temel_30').referans_cokme_tanisi, ([0.1837117307087384, 0.2642006668911607, 0.12014429883567816, 0.21378761926378415], [0.7979627390498601, 0.7167792777336007, 0.7641105631966173, 0.7979627390498601], 0.15, 0.2), tohum=2848)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def durum_cokme_tanisi(norm_izleri, tutma_orani_izleri, min_norm, max_oran):
    if not isinstance(norm_izleri, list) or not isinstance(tutma_orani_izleri, list) or not norm_izleri or len(norm_izleri) != len(tutma_orani_izleri):
        raise ValueError("iz_boyut")
    for n, r in zip(norm_izleri, tutma_orani_izleri):
        if isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n) or n < 0.0:
            raise ValueError("norm_deger")
        if isinstance(r, bool) or not isinstance(r, (int, float)) or not math.isfinite(r) or not 0.0 <= r <= 1.0:
            raise ValueError("oran_deger")
    for v in (min_norm, max_oran):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError("esik_sayi")
    if min_norm <= 0.0 or not 0.0 < max_oran <= 1.0:
        raise ValueError("esik_sinir")
    adimlar = [t for t in range(len(norm_izleri)) if norm_izleri[t] < min_norm or tutma_orani_izleri[t] < max_oran]
    return {
        "cokme_adimlari": adimlar,
        "cokme_var": bool(adimlar),
        "en_dusuk_tutma": float(min(tutma_orani_izleri)),
    }

if __name__ == "__main__":
    from ai_temel_veri import json_yukle
    v = json_yukle("veri/mamba_ssm.json")
    for s in v["sekanslar"]:
        ab_l = [[math.exp(d * a) for a in v["a_diag"]] for d in s["deltalar"]]
        bb_l = [[d * b for b in v["b_vektor"]] for d in s["deltalar"]]
        tutma_l = [sum(r) / len(r) for r in ab_l]
        h = [0.0] * len(v["a_diag"])
        norm_l = []
        for ab, bb, x in zip(ab_l, bb_l, s["x_adimlar"]):
            h = [ab[i] * h[i] + bb[i] * x for i in range(len(h))]
            norm_l.append(math.sqrt(sum(u * u for u in h)))
        print(s["ad"], durum_cokme_tanisi(norm_l, tutma_l, v["min_norm"], v["max_oran"]))
```
```hint
`norm_izleri[t] < min_norm or tutma_orani_izleri[t] < max_oran` koşulunu sağlayan tüm zaman adımlarını sıralı olarak döndür.
```
:::

::: anlat Hata vitrini · çalışmış yanlış rapor
Yazar, kusurlu başlangıç kodlarını görünür sentetik veriyle gerçekten çalıştırdı ve sonucu `outputs/yeni-ai-temel-30/gorunur-run-1.json` dosyasına kaydetti. `delta=3.50` adımında kusurlu kod birinci dereceden Euler (`1 + delta * a`) kullandığı için `a_bar=[-2.5, -6.0, -13.0]` gibi anlamsız negatif katsayılar üretirken; doğru ZOH kodu `[0.0302, 0.0009, 0.0000008]` üretir. Ayrıca `saldirgan_delta_patlamasi` sekansında kusurlu tanı `cokme_var=False` verirken doğru kod `[2, 3]` adımlarında bellek çökmesini yakalar.

Bu kaydedilmiş bir hesaplama çıktısıdır, model yanıtı değildir ve rapor sentetiktir. Büyük bir $\Delta_t$ adımında Euler yaklaşıklamasının negatif/patlayan durum üretmesi ile gerçek ZOH üstel sönümünün belleği sıfırlaması arasındaki farkı kendi cümlenle açıkla. Gerçek finaldeki ölçüm ayrıca üretilir; bu sayılar onun yerine konmaz.
:::

::: anlat Gerçek deney: SmolLM2 gömmeleriyle eğitilen seçici SSM'de bellek silme ve üzerine yazma
Eğitim ve metin üretimi kayıtlı `seed=30` ile tekrarlanır. Her üretilen belgenin ilk %70 tokenı eğitim, kalan %30 tokenı test içindir; pencereler bölüm sınırını aşmaz. Böylece konular iki tarafta temsil edilirken aynı token aralığı iki tarafta kullanılmaz. Eğitim en az 300, en çok 1200 adım sürer ve yalnız eğitim cross-entropy kaybı 0.02 altına indiğinde erken durur; ayrık test durdurma kararına girmez. Gerçek adım sayısı ve son kayıp kanıtta `egitim` alanındadır.

Final önce Mamba'nın çekirdek mekanizmasını (girdiye bağlı $\Delta_t$, $B_t$ ve köşegen $A$) gerçek verilerle küçük bir modelde eğitir ve saldırıyı orada kurar; sonra aynı saldırıyı ön eğitimli **mamba-130m**'de (yerel önbellek) dener.

**Kurulum:**
- **Girdi:** SmolLM2-135M'in gerçek token gömmeleri (576 boyut). $\Delta_t = \text{softplus}(w_\Delta \cdot e_t + b)$, $B_t = W_B\, e_t$, $x_t = w_x \cdot e_t$; durum boyutu $N = 8$; $A$ sabit S4D başlangıcıdır.
- **Görev:** Bir bellek sınavı. Dizi bir anahtar kelimeyle başlar (` red`, ` blue`, ` green`, ` black`). Ardından modelin kendi ürettiği 24 tokenlık gerçek İngilizce metin gelir. SSM son durumundan anahtarı söylemelidir (4 sınıf, şans 0.25).
- **Veri:** Eğitim 512 dizi; test 128 dizi, metnin eğitimde kullanılmayan bölümünden alınır.

Eğitilen SSM, ayrık testte yazarın üç GPU koşusunun üçünde de doğruluk **1.0** verdi. Model bunu seçicilikle başarıyor: anahtar tokenlere büyük $\Delta$ verip durumu yazıyor, dolgu tokenlerine küçük $\Delta$ (tutma oranı ~0.93) verip belleği koruyor.

**Saldırgan** SSM ağırlıklarını bilir. Sözlükteki 49 bin tokenin hepsi için $\Delta$'yı hesaplar ve en büyüğünü dizinin ortasına koyar. Üç koşunun üçünde de bulunan token ` red` oldu, yani anahtarlardan biri ($\Delta$ 5–8). Bu bir **silme** değil, **üzerine yazma** saldırısıdır. O adımda tutma oranı ~0.93'ten ~0.005'e düştü ve model her dizide "red" dedi. Doğruluk 0.20–0.27'ye indi; kalan doğrular zaten "red" olan dizilerdir.

Anahtarları hariç tutan saldırganın bulduğu token ` Red` ya da `blue` oldu (anahtarın büyük harfli/boşluksuz hâli). Gömme uzayında anahtara komşu olduğu için aynı yazma kapısını açar ve aynı hasarı verir. Seçicilik bir **yön** olarak öğrenilir; o yönde duran her token kapıyı açar.

**Savunmalar:**
- **Küresel $\Delta$ tavanı çalışmaz.** Eğitim dolgu tokenlerinin %99 yüzdeliğiyle tavan konulduğunda saldırının yanında normal doğruluk da 0.19–0.38'e düştü. Model anahtarı yazmak için tam o büyük $\Delta$'ya muhtaçtır; tavan yazma kapısını da kapatır.
- **Tanı çalışır, ama yalnız tespit eder.** Senin `durum_cokme_tanisi` işlevin anahtardan sonraki adımlarda tutma oranı < 0.18 ya da norm < (normal ortanca normun %5'i) arar. Saldırılı dizilerin 32/32'sini yakaladı. Normal dizilerde koşuya göre 0/32 ile 10/32 arasında yanlış alarm verdi. Tespit edilen girdi reddedilebilir ya da işaretlenebilir; bozulan durum geri gelmez.

Her iki akışta **senin `ssm_ayriklastir`, `ssm_adim_izle` ve `durum_cokme_tanisi` işlevlerin** eğitilmiş SSM'nin gerçek $\Delta_t$, $B_t$, $x_t$ izlerinde çalışır ve bağımsız referansla karşılaştırılır.

**Ön eğitimli mamba-130m'de aynı saldırı.** Sözlükten rastgele ~5 400 sözcük, sabit bir önekten sonra modelden geçirilir. Her biri için 24 katmanın hepsinde $\Delta$ hesaplanır ve ortalama durum tutma oranı $\overline{e^{\Delta A}}$ ölçülür. Senin `ssm_ayriklastir` işlevin de bir katmanın gerçek $\Delta$, $A$ ve $B$ değerleriyle beş kanalda sınanır. Yazarın koşusunda en düşük tutma oranlı tokenlar "Introduction", "Abbreviations", "Share", "Consider" gibi sözcüklerdi. Bunların belge sınırlarıyla ilişkili olması bir yorumdur; sabit önekteki bu tarama modelin neyi öğrenmiş olduğunu tek başına kanıtlamaz. Bu "silici" tokenlar bir parola hatırlama görevinde (ai-uretim-20'deki gibi) anahtarla soru arasına 60 kez konur ve 60 rastgele tokenla karşılaştırılır. Yazarın bu koşusundaki sonuç: küçük modelde çalışan saldırı gerçek modele **aktarılmadı**; anahtarın log-olasılığı rastgele tokenlarla neredeyse aynı kalır. Gerçek modelde bilgi 24 katmana ve 1 536 kanala dağılmıştır; tek tek sıfırlamalar kısa mesafedeki hatırlamayı bozmaz. Uzun dolgunun hatırlamayı nasıl değiştirdiği ayrıca ölçülür (ai-uretim-20, durum taşırma). Küçük bir modelde kurulan bir saldırının büyük modele aktarıldığı varsayılamaz; ölçülmelidir.

**Kanıt dosyasını oku:** Soru 1: Saldırı tokeninin bir anahtar ya da anahtarın komşusu çıkması, seçici SSM'nin "neyi yazacağına" nasıl karar verdiği hakkında ne söyler? Soru 2: Konuma bağlı bir kural ("yalnız ilk token yazabilir") bu görevde işe yarardı; gerçek bir dil modelinde neden yaramaz? Soru 3: Hibrit mimariler (her birkaç Mamba katmanına bir tam dikkat katmanı) bu üzerine yazma sorununu nasıl hafifletir? Cevabını tezgâhta yorum olarak yaz; otomatik test bu serbest açıklamayı puanlamaz.
:::

::: gorev Gerçek deney · GPU üzerinde seçici SSM yinelemesi ve state collapse denetimi
Önceki üç görevin `ssm_ayriklastir`, `ssm_adim_izle` ve `durum_cokme_tanisi` işlevlerini birleştir. Çalıştır gerçek tabloyu gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 180
```
```starter
import ai_lab
import math
def ssm_ayriklastir(delta, a_diag, b_vektor):
    a_bar = [1.0 + delta * a for a in a_diag]
    b_bar = [delta * b for b in b_vektor]
    return {"a_bar": a_bar, "b_bar": b_bar, "tutma_orani": sum(a_bar) / len(a_bar)}
def ssm_adim_izle(a_bar_adimlar, b_bar_adimlar, x_adimlar):
    N = len(a_bar_adimlar[0])
    return {"son_durum": [0.0] * N, "norm_izleri": [1.0] * len(x_adimlar)}
def durum_cokme_tanisi(norm_izleri, tutma_orani_izleri, min_norm, max_oran):
    return {"cokme_adimlari": [], "cokme_var": False, "en_dusuk_tutma": min(tutma_orani_izleri)}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_30 as D
    D.goster(ssm_ayriklastir, ssm_adim_izle, durum_cokme_tanisi)
```
```test
import ai_lab, math
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('referans_ssm_ayriklastir', 'referans_ssm_izle', 'referans_cokme_tanisi', 'kanit_yaz', '_yakin'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
ssm_ayriklastir = need("ssm_ayriklastir")
ssm_adim_izle = need("ssm_adim_izle")
durum_cokme_tanisi = need("durum_cokme_tanisi")
def sinama1(f):
    import math, random
    def _r(d, a, b):
        ab = [math.exp(d * x) for x in a]; bb = [d * x for x in b]
        return {"a_bar": ab, "b_bar": bb, "tutma_orani": sum(ab) / len(ab)}
    def _y(x, y): return set(x) == {"a_bar", "b_bar", "tutma_orani"} and abs(x["tutma_orani"] - y["tutma_orani"]) < 1e-12 and len(x["a_bar"]) == len(y["a_bar"]) and all(abs(p - q) < 1e-12 for p, q in zip(x["a_bar"], y["a_bar"])) and all(abs(p - q) < 1e-12 for p, q in zip(x["b_bar"], y["b_bar"]))
    try:
        a = [-1.0, -2.0]; b = [0.5, -1.0]; old = (list(a), list(b))
        if not _y(f(0.5, a, b), _r(0.5, a, b)) or (a, b) != old: return False
        rng = random.Random(30)
        for _ in range(25):
            n = rng.randint(1, 7); d = rng.uniform(0.01, 4.0); av = [rng.uniform(-5.0, -0.05) for _ in range(n)]; bv = [rng.uniform(-2.0, 2.0) for _ in range(n)]
            if not _y(f(d, list(av), list(bv)), _r(d, av, bv)): return False
        for bad in ((0.0, [-1.0], [1.0]), (-0.5, [-1.0], [1.0]), (True, [-1.0], [1.0]), (0.5, [], []), (0.5, [-1.0], [1.0, 2.0]), (0.5, [0.0], [1.0]), (0.5, [0.5], [1.0]), (0.5, [-1.0, True], [1.0, 1.0]), (float("nan"), [-1.0], [1.0]), (0.5, [-1.0], [float("inf")])):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama1(ssm_ayriklastir), "üstel ZOH ayrıklaştırma, Hurwitz negatiflik kısıtı ve geçersiz girdi")
for ad, mut in [("Euler 1 + d*A", lambda d, a, b: {"a_bar": [1.0 + d * x for x in a], "b_bar": [d * x for x in b], "tutma_orani": 0.5}), ("b_bar ölçeklenmemiş", lambda d, a, b: dict(ssm_ayriklastir(d, a, b), b_bar=list(b))), ("tutma oranı toplam", lambda d, a, b: dict(ssm_ayriklastir(d, a, b), tutma_orani=sum(ssm_ayriklastir(d, a, b)["a_bar"])))]:
    kontrol(not sinama1(mut), "mutant reddedildi: " + ad)
def sinama2(f):
    import copy, math, random
    def _r(ab, bb, xl):
        h = [0.0] * len(ab[0]); nl = []
        for a, b, x in zip(ab, bb, xl):
            h = [a[i] * h[i] + b[i] * x for i in range(len(h))]; nl.append(math.sqrt(sum(v * v for v in h)))
        return {"son_durum": h, "norm_izleri": nl}
    def _y(a, b): return set(a) == {"son_durum", "norm_izleri"} and len(a["son_durum"]) == len(b["son_durum"]) and len(a["norm_izleri"]) == len(b["norm_izleri"]) and all(abs(p - q) < 1e-12 for p, q in zip(a["son_durum"], b["son_durum"])) and all(abs(p - q) < 1e-12 for p, q in zip(a["norm_izleri"], b["norm_izleri"]))
    try:
        ab = [[0.5, 0.5], [0.5, 0.5]]; bb = [[1.0, 0.0], [1.0, 0.0]]; xl = [2.0, 2.0]; old = copy.deepcopy((ab, bb, xl))
        if not _y(f(ab, bb, xl), {"son_durum": [3.0, 0.0], "norm_izleri": [2.0, 3.0]}) or (ab, bb, xl) != old: return False
        try:
            f([[]], [[]], [1.0])
            return False
        except ValueError:
            pass
        rng = random.Random(3030)
        for _ in range(25):
            T = rng.randint(1, 6); N = rng.randint(1, 5); a_l = [[rng.uniform(0.0, 1.0) for _ in range(N)] for _ in range(T)]; b_l = [[rng.uniform(-2.0, 2.0) for _ in range(N)] for _ in range(T)]; x_l = [rng.uniform(-3.0, 3.0) for _ in range(T)]
            if not _y(f(copy.deepcopy(a_l), copy.deepcopy(b_l), list(x_l)), _r(a_l, b_l, x_l)): return False
        for bad in (([], [], []), ([[0.5]], [[0.5]], [1.0, 2.0]), ([[0.5], [0.5, 0.5]], [[0.5], [0.5, 0.5]], [1.0, 1.0]), ([[-0.1]], [[0.5]], [1.0]), ([[1.2]], [[0.5]], [1.0]), ([[True]], [[0.5]], [1.0]), ([[0.5]], [[0.5]], [float("nan")])):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama2(ssm_adim_izle), "durum birikimi, L2 norm izi ve geçersiz girdi")
for ad, mut in [("geçmiş durum unutulur", lambda ab, bb, xl: {"son_durum": [bb[-1][i] * xl[-1] for i in range(len(ab[0]))], "norm_izleri": [0.0] * len(xl)}), ("a_bar çarpanı yok", lambda ab, bb, xl: dict(ssm_adim_izle([[1.0] * len(ab[0]) for _ in ab], bb, xl))), ("norm karesi", lambda ab, bb, xl: dict(ssm_adim_izle(ab, bb, xl), norm_izleri=[v * v for v in ssm_adim_izle(ab, bb, xl)["norm_izleri"]]))]:
    kontrol(not sinama2(mut), "mutant reddedildi: " + ad)
def sinama3(f):
    import random
    def _r(nl, tl, mn, mo):
        ad = [t for t in range(len(nl)) if nl[t] < mn or tl[t] < mo]
        return {"cokme_adimlari": ad, "cokme_var": bool(ad), "en_dusuk_tutma": float(min(tl))}
    try:
        nl = [0.5, 0.4, 0.05, 0.3]; tl = [0.8, 0.1, 0.7, 0.9]; old = (list(nl), list(tl))
        if f(nl, tl, 0.1, 0.2) != {"cokme_adimlari": [1, 2], "cokme_var": True, "en_dusuk_tutma": 0.1} or (nl, tl) != old: return False
        # Eşik eşitliği alarm değildir; yalnız kesin küçüklük alarmdır.
        if f([0.25, 0.249, 0.25], [0.3, 0.3, 0.299], 0.25, 0.3) != {"cokme_adimlari": [1, 2], "cokme_var": True, "en_dusuk_tutma": 0.299}: return False
        if f([0.25], [0.3], 0.25, 0.3) != {"cokme_adimlari": [], "cokme_var": False, "en_dusuk_tutma": 0.3}: return False
        rng = random.Random(3003)
        for _ in range(25):
            T = rng.randint(1, 8); n_v = [rng.uniform(0.0, 2.0) for _ in range(T)]; t_v = [rng.uniform(0.0, 1.0) for _ in range(T)]
            if f(list(n_v), list(t_v), 0.25, 0.3) != _r(n_v, t_v, 0.25, 0.3): return False
        for bad in (([], [], 0.1, 0.2), ([0.5], [0.5, 0.5], 0.1, 0.2), ([-0.1], [0.5], 0.1, 0.2), ([0.5], [-0.1], 0.1, 0.2), ([0.5], [1.2], 0.1, 0.2), ([0.5], [0.5], 0.0, 0.2), ([0.5], [0.5], 0.1, 0.0), ([0.5], [0.5], 0.1, 1.1), ([0.5], [0.5], True, 0.2), ([0.5], [0.5], 0.1, float("nan"))):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama3(durum_cokme_tanisi), "norm veya tutma oranı çökmesi, en düşük tutma ve geçersiz girdi")
for ad, mut in [("and bağlacı", lambda nl, tl, mn, mo: {"cokme_adimlari": [t for t in range(len(nl)) if nl[t] < mn and tl[t] < mo], "cokme_var": True, "en_dusuk_tutma": min(tl)}), ("hep temiz", lambda nl, tl, mn, mo: {"cokme_adimlari": [], "cokme_var": False, "en_dusuk_tutma": min(tl)}), ("en düşük yerine maksimum", lambda nl, tl, mn, mo: dict(durum_cokme_tanisi(nl, tl, mn, mo), en_dusuk_tutma=max(tl)))]:
    kontrol(not sinama3(mut), "mutant reddedildi: " + ad)
# farksal tarama (final)
import importlib as _il
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_R = _il.import_module('sandbox.ai_gercek_ai_temel_30')
for _ad, _ref, _taban, _toh in (
    ('ssm_ayriklastir', 'referans_ssm_ayriklastir', (0.1, [-1.0, -2.0, -4.0], [0.5, -0.5, 1.0]), 3081),
    ('ssm_adim_izle', 'referans_ssm_izle', ([[0.9048374180359595, 0.8187307530779818, 0.6703200460356393], [0.8607079764250578, 0.7408182206817179, 0.5488116360940265], [0.8869204367171575, 0.7866278610665535, 0.6187833918061408], [0.9048374180359595, 0.8187307530779818, 0.6703200460356393]], [[0.05, -0.05, 0.1], [0.075, -0.075, 0.15], [0.06, -0.06, 0.12], [0.05, -0.05, 0.1]], [1.5, 0.8, -0.5, 1.0]), 2824),
    ('durum_cokme_tanisi', 'referans_cokme_tanisi', ([0.1837117307087384, 0.2642006668911607, 0.12014429883567816, 0.21378761926378415], [0.7979627390498601, 0.7167792777336007, 0.7641105631966173, 0.7979627390498601], 0.15, 0.2), 3370),
):
    _t, _g = _ff(need(_ad), getattr(_R, _ref), _taban, tohum=_toh)
    kontrol(_t, "farksal tarama (" + _ad + "): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
if not all(checks): stop()
from sandbox import ai_gercek_ai_temel_30 as D
try: r = D.deney(ssm_ayriklastir, ssm_adim_izle, durum_cokme_tanisi)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r["ayrik_ayni"], "eğitilmiş SSM'nin gerçek Δ_t/B_t izlerinde ayrıklaştırma bağımsız referansla aynı (32 normal + 32 saldırılı dizi)")
kontrol(r["izle_ayni"], "gerçek izlerde durum yinelemesi referansla aynı")
kontrol(r["tani_ayni"], "gerçek izlerde state collapse tanısı referansla aynı")
kontrol(r["dogruluk"]["normal"] >= 0.9, "SmolLM2 gömmeleriyle eğitilen seçici SSM anahtarı ayrık testte hatırladı: %.3f" % r["dogruluk"]["normal"])
kontrol(r["bellek_silindi"], "sözlükteki en büyük Δ tokeni belleği bozdu: doğruluk %.3f -> %.3f" % (r["dogruluk"]["normal"], r["dogruluk"]["saldiri"]))
kontrol(r["saldiri_cokme_orani"] >= 0.9, "tutma oranı tanısı saldırılı dizilerin en az %%90'ını yakaladı: %.3f (normal yanlış alarm %.3f)" % (r["saldiri_cokme_orani"], r["normal_cokme_orani"]))
kontrol(r["gercek_mamba_olculdu"], "ön eğitimli mamba-130m'nin gerçek Δ, A, B değerlerinde ayrıklaştırma referansla aynı; silici tokenların tutma oranı rastgele tokenlardan düşük")
ai_lab.kanit_yaz("ai-temel-30-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-temel-30", "deney": r})
```
```solution
import ai_lab
import math
def ssm_ayriklastir(delta, a_diag, b_vektor):
    if isinstance(delta, bool) or not isinstance(delta, (int, float)) or not math.isfinite(delta) or delta <= 0.0:
        raise ValueError("delta")
    if not isinstance(a_diag, list) or not isinstance(b_vektor, list) or not a_diag or len(a_diag) != len(b_vektor):
        raise ValueError("boyut")
    for a, b in zip(a_diag, b_vektor):
        if isinstance(a, bool) or not isinstance(a, (int, float)) or not math.isfinite(a) or a >= 0.0:
            raise ValueError("a_diag")
        if isinstance(b, bool) or not isinstance(b, (int, float)) or not math.isfinite(b):
            raise ValueError("b_vektor")
    a_bar = [math.exp(delta * a) for a in a_diag]
    b_bar = [delta * b for b in b_vektor]
    return {
        "a_bar": a_bar,
        "b_bar": b_bar,
        "tutma_orani": sum(a_bar) / float(len(a_bar)),
    }
def ssm_adim_izle(a_bar_adimlar, b_bar_adimlar, x_adimlar):
    if not isinstance(a_bar_adimlar, list) or not isinstance(b_bar_adimlar, list) or not isinstance(x_adimlar, list):
        raise ValueError("liste")
    T = len(x_adimlar)
    if T < 1 or len(a_bar_adimlar) != T or len(b_bar_adimlar) != T:
        raise ValueError("zaman_boyut")
    N = None
    for t in range(T):
        ab, bb, x = a_bar_adimlar[t], b_bar_adimlar[t], x_adimlar[t]
        if not isinstance(ab, list) or not isinstance(bb, list) or not ab or len(ab) != len(bb):
            raise ValueError("durum_boyut")
        if N is not None and len(ab) != N:
            raise ValueError("n_farkli")
        N = len(ab)
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
            raise ValueError("x_sayi")
        for a, b in zip(ab, bb):
            if isinstance(a, bool) or not isinstance(a, (int, float)) or not math.isfinite(a) or not 0.0 <= a <= 1.0:
                raise ValueError("a_bar")
            if isinstance(b, bool) or not isinstance(b, (int, float)) or not math.isfinite(b):
                raise ValueError("b_bar")
    h = [0.0] * N
    normlar = []
    for t in range(T):
        ab, bb, x = a_bar_adimlar[t], b_bar_adimlar[t], x_adimlar[t]
        h = [ab[i] * h[i] + bb[i] * x for i in range(N)]
        normlar.append(math.sqrt(sum(v * v for v in h)))
    return {"son_durum": h, "norm_izleri": normlar}
def durum_cokme_tanisi(norm_izleri, tutma_orani_izleri, min_norm, max_oran):
    if not isinstance(norm_izleri, list) or not isinstance(tutma_orani_izleri, list) or not norm_izleri or len(norm_izleri) != len(tutma_orani_izleri):
        raise ValueError("iz_boyut")
    for n, r in zip(norm_izleri, tutma_orani_izleri):
        if isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n) or n < 0.0:
            raise ValueError("norm_deger")
        if isinstance(r, bool) or not isinstance(r, (int, float)) or not math.isfinite(r) or not 0.0 <= r <= 1.0:
            raise ValueError("oran_deger")
    for v in (min_norm, max_oran):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError("esik_sayi")
    if min_norm <= 0.0 or not 0.0 < max_oran <= 1.0:
        raise ValueError("esik_sinir")
    adimlar = [t for t in range(len(norm_izleri)) if norm_izleri[t] < min_norm or tutma_orani_izleri[t] < max_oran]
    return {
        "cokme_adimlari": adimlar,
        "cokme_var": bool(adimlar),
        "en_dusuk_tutma": float(min(tutma_orani_izleri)),
    }
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_30 as D
    D.goster(ssm_ayriklastir, ssm_adim_izle, durum_cokme_tanisi)
```
```hint
Üç işlevi birleştir; ZOH ayrıklaştırmasında `math.exp(delta * a)` ve çökme tanısında `or` bağlacını kullan.
```
:::

::: anlat Sınır
Bu ders tek kanallı, tek katmanlı, köşegen bir seçici `State Space Model` üzerinde $\Delta_t$ ayrıklaştırmasını ve `state collapse` etkisini gösterir. Gerçek deneydeki SSM ön eğitimli bir Mamba değildir; girdisi SmolLM2'nin **statik** token gömmeleridir, bağlamsal gizli durumlar değildir. Görev dar bir bellek sınavıdır. Saldırgan SSM ağırlıklarını bilir (beyaz kutu). Tanı yalnız tespit eder; yanlış alarm oranı koşuya göre değişir. Mamba-2'nin durum uzayı ikililiği (State Space Duality - SSD), çok kanallı/çok katmanlı gerçek Mamba blokları ve hibrit dikkat-SSM mimarileri kapsanmaz.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
Önce belleği bir durum vektörü olarak çiz: her yeni token eski durumu exp(ΔA) ile çarpar, ardından ΔBx ekler. Küçük Δ geçmişi korur; büyük Δ, negatif A altında geçmiş katkısını bastırır. Tam ZOH giriş katsayısı ile görevdeki ΔB yaklaşımını ayır. Sonra aynı son normun farklı geçmiş katkılarıyla oluşabileceğini göster: güçlü yeni giriş, silinmiş geçmişi yüksek normun arkasında gizleyebilir. Bu yüzden norm ve tutma tanısı birlikte raporlanır. Son 30 saniyede küçük SSM'deki bellek sınavını ön eğitimli Mamba denemesinden ayır; saldırının aktarımı ve yanlış alarm oranı ölçülür, varsayılmaz. Dinleyiciye sor: “Norm yüksekse geçmiş bilgi mutlaka korunmuş mudur?”
:::
