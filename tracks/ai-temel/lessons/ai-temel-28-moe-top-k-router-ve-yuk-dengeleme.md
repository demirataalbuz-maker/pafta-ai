---
id: ai-temel-28
title: Mixture-of-Experts Top-K Router ve Yük Dengeleme · Uzman Çökmesini Önlemek
summary: Seyrek Mixture-of-Experts (MoE) katmanında Top-K router ağırlıklarını, yardımcı load balancing kaybını ve uzman kapasite aşımını (token dropping) GPU'da ölç.
esleme: ai-temel-06, ai-temel-10, ai-temel-18
timeout: 60
---

::: anlat Seyrek uzmanlar nasıl seçilir ve neden tek bir uzmana çöker?
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Mixtral 8x7B ve DeepSeek-V3 gibi `Mixture-of-Experts` modelleri her token için yalnızca Top-$K$ uzmanı etkinleştirerek toplam parametre sayısını büyütürken çıkarım FLOP maliyetini sabit tutar | İlk üç görev: `veri/moe_router.json` içindeki **sentetik** yönlendirici logitleri ve senaryolar. Final: yerel **SmolLM2-135M** 15. katman MLP bloğundan damıtılan 8 SwiGLU uzmanlı ve Top-2 `router` katmanlı MoE deneyi | Dağıtık GPU'lar arası All-to-All iletişim gecikmesinin ağ topolojisine göre nasıl değiştiğini söyleyemez |
| Yardımcı `load balancing` kaybı olmadan `router` erken aşamada birkaç uzmanı aşırı seçip diğerlerini köreltir (routing collapse) ve donanım kapasitesini aşan tokenlar düşürülür | Top-$K$ kararlı softmax, Switch/Mixtral yardımcı kaybı $E \sum f_e P_e$ ve kapasite faktörü (`kapasite_faktoru`) raporu | Yardımcı kaybın `1.0` olmasının uzmanların anlamsal olarak en iyi şekilde ayrıştığını kanıtlamaz |

> [!NOT]
> Görevler `veri/moe_router.json` dosyasını okur; dosya sentetiktir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; değişiklikler taşınmaz, **kalıcılık yoktur**. Ekranda ayrı dosya görüntüleyici yoktur; içeriği görmek için `print` kullan. Gizli testler ayrıdır. Final yeni model indirmez ve GPU varsa onu kullanır.

ai-temel-06 yoğun (dense) Transformer ileri besleme (FFN) katmanını inceler: her token aynı FFN ağırlıklarından geçer. **`Mixture-of-Experts` (`MoE`) mimarisi ise FFN katmanını $E$ adet bağımsız uzman (expert) ağına böler ve her token için öğrenilebilir bir `router` (gating network) ile yalnızca en yüksek puanlı $K$ uzmanı çalıştırır (Shazeer vd. 2017, Jiang vd. 2024).**

**Top-$K$ `router` ve kapılama (gating) ağırlıkları.** Bir tokenın yönlendirici logit vektörü $z \in \mathbb{R}^E$ olsun. En yüksek logitli $K$ uzmanın indis kümesi $S = \text{TopK}(z, K)$ seçilir. Seçilen bu $K$ uzman kendi aralarında kararlı softmax ile normalize edilir:
$$w_i = \frac{\exp(z_i - \max_{j \in S} z_j)}{\sum_{j \in S} \exp(z_j - \max_{m \in S} z_m)}, \quad i \in S$$

**Uzman çökmesi (expert collapse) ve `load balancing` kaybı.** Eğitim başında bir uzman şans eseri biraz daha iyi gradyan alırsa, `router` ona daha yüksek logit verir; daha çok token alan uzman daha hızlı gelişir ve sonunda neredeyse tüm tokenlar aynı 1-2 uzmana yığılır. Bunu önlemek için Fedus vd. (2022) yardımcı yük dengeleme kaybını tanımlar. $T$ tokenlık bir grupta her uzman $e \in \{0, \dots, E-1\}$ için:
- Atanma kesri: $f_e = \frac{\text{uzman } e\text{'nin seçilme sayısı}}{T \cdot K}$
- Ortalama yönlendirici olasılığı: $P_e = \frac{1}{T}\sum_{t=0}^{T-1} p_{t, e}$
$$\mathcal{L}_{\text{aux}} = E \sum_{e=0}^{E-1} f_e \cdot P_e$$
Kusursuz dengede her uzman için $f_e = 1/E$ ve $P_e = 1/E$ olduğundan $\mathcal{L}_{\text{aux}} = E \cdot E \cdot (1/E^2) = 1.0$ değerini alır. Bu, dengeli durumun referans değeridir; bütün geçerli yönlendirmeler için genel bir alt sınır değildir. Örneğin dokuz tokenın olasılığı `[0.51, 0.49]`, onuncunun `[0.0, 1.0]` ve seçimler Top-1 ise $f=(0.9,0.1)$, $P=(0.459,0.541)$ ve kayıp $2(0.9\cdot0.459+0.1\cdot0.541)=0.9344$ çıkar. Bu nedenle kaybı tek başına denge kanıtı sayma; uzman yüklerini ve düşürülen atamaları birlikte incele.

**Kapasite faktörü ve token düşürme (token dropping).** Donanımda statik tensör boyutları kullanıldığında her uzmanın işleyebileceği maksimum atama sayısı `uzman_kapasitesi` $= \lceil \frac{T \cdot K}{E} \cdot \text{CF} \rceil$ ile sınırlanır. Bir uzmana bu kapasiteden fazla atama gelirse, aşan atamalar (`dusurulen_atama`) işlenmeden atlanır (artık bağlantı üzerinden doğrudan geçer).

**Saldırgan ne dener?** Akustik/metinsel yönlendirme taşması (routing overflow / sponge) saldırısında, saldırgan tüm tokenlarını aynı uzmana yönlendirecek girdi örüntüleri oluşturur. Hedef uzmanın kapasitesi dolar ve aynı batch içindeki diğer kullanıcıların veya kritik talimatların tokenları düşürülerek modelin doğruluğu bozulur.

**Savunma neden kırılır?** Yardımcı kayıpta $E$ çarpanı unutulursa veya $f_e$ kesri $T \cdot K$ yerine yanlış paydaya bölünürse dengeleme sinyali zayıflar; kapasite raporu izlenmezse sessizce düşürülen tokenlar fark edilmez.

**Görev 1'de sık tuzaklar:** Eşit logit durumunda küçük indisi seçmemek veya softmax'ı seçilen $K$ uzman yerine tüm $E$ uzman üzerinden alıp ağırlık toplamını `1.0` altında bırakmak.

Kaynaklar: [Shazeer vd. 2017 - Outrageously Large Neural Networks: The Sparsely-Gated Mixture-of-Experts Layer](https://arxiv.org/abs/1701.06538), [Fedus vd. 2022 - Switch Transformers: Scaling to Trillion Parameter Models](https://arxiv.org/abs/2101.03961), [Jiang vd. 2024 - Mixtral of Experts](https://arxiv.org/abs/2401.04088). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Köprü: ai-temel-06 standart FFN bloğunu, ai-temel-18 çıkarım bütçesini inceler; bu ders seyrek uzman yönlendirmesini ve yük dengelemesini kurar.
:::

::: tahmin Dengeli ve çökmüş yönlendirmede yardımcı kayıp kaç çıkar?
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
E = 4
f_dengeli = [0.25, 0.25, 0.25, 0.25]
P_dengeli = [0.25, 0.25, 0.25, 0.25]
f_cokmus = [1.0, 0.0, 0.0, 0.0]
P_cokmus = [0.90, 0.05, 0.03, 0.02]
print("Dengeli aux_loss:", round(E * sum(a * b for a, b in zip(f_dengeli, P_dengeli)), 4))
print("Çökmüş aux_loss:", round(E * sum(a * b for a, b in zip(f_cokmus, P_cokmus)), 4))
```
???
```cikti
Dengeli aux_loss: 1.0
Çökmüş aux_loss: 3.6
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: `Dengeli aux_loss` neden uzman sayısından bağımsız olarak tam `1.0` çıktı? Çökmüş durumda kayıp neden $E=4$ değerine yaklaştı? Sonra üç kusurlu başlangıç kodunu çalıştır ve her birinin neyi kaçırdığını önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · Top-K uzman seçimi ve kapılama ağırlıkları
`topk_yonlendirme(logitler, k)`: `logitler` en az 2 elemanlı `list`, elemanları bool olmayan sonlu sayı; `k` bool olmayan `int` ve `1 <= k <= len(logitler)`. En yüksek logitli `k` uzmanın indisini (büyükten küçüğe, eşitlikte küçük indis önce) seç ve yalnızca bu `k` logit üzerinde kararlı softmax uygulayarak `{"uzmanlar": [...], "agirliklar": [...]}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-28")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def topk_yonlendirme(logitler, k):
    m = max(logitler)
    p = [math.exp(x - m) for x in logitler]
    t = sum(p)
    tum_ag = [v / t for v in p]
    sec = sorted(range(len(logitler)), key=lambda i: logitler[i], reverse=True)[:k]
    return {"uzmanlar": sec, "agirliklar": [tum_ag[i] for i in sec]}

from ai_temel_veri import json_yukle
v = json_yukle("veri/moe_router.json")
print("Top-K:", topk_yonlendirme(v["ornek_logit"], v["k"]))
```
```test
def sinama1(f):
    import math, random
    def _r(z, k):
        s = sorted(range(len(z)), key=lambda i: (-z[i], i))[:k]
        m = max(z[i] for i in s)
        e = [math.exp(z[i] - m) for i in s]; t = sum(e)
        return {"uzmanlar": s, "agirliklar": [v / t for v in e]}
    def _y(a, b):
        return set(a) == {"uzmanlar", "agirliklar"} and a["uzmanlar"] == b["uzmanlar"] and len(a["agirliklar"]) == len(b["agirliklar"]) and all(abs(p - q) < 1e-12 for p, q in zip(a["agirliklar"], b["agirliklar"]))
    try:
        z = [1.0, 3.0, 3.0, -5.0]; old = list(z)
        c = f(z, 2)
        if not _y(c, {"uzmanlar": [1, 2], "agirliklar": [0.5, 0.5]}) or z != old: return False
        if not _y(f([10.0, 0.0, 5.0], 1), {"uzmanlar": [0], "agirliklar": [1.0]}) or not _y(f([800.0, 801.0], 2), _r([800.0, 801.0], 2)): return False
        rng = random.Random(28)
        for _ in range(25):
            n = rng.randint(2, 8); zv = [rng.uniform(-30, 30) for _ in range(n)]; kv = rng.randint(1, n)
            if not _y(f(list(zv), kv), _r(zv, kv)): return False
        for bad in (
            (None, 1), ([], 1), ([1.0], 1), ((1.0, 2.0), 1),
            ([True, 1.0], 1), ([float("nan"), 1.0], 1), ([float("inf"), 1.0], 1),
            ([1.0, 2.0], 0), ([1.0, 2.0], 3), ([1.0, 2.0], -1),
            ([1.0, 2.0], True), ([1.0, 2.0], 1.5), ([1.0, 2.0], "1")
        ):
            try:
                f(*bad)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sinama1(topk_yonlendirme), "Top-K sıralama, eşitlik kırılımı, alt-küme softmax ve geçersiz girdi")
for ad, mut in [
    ("tüm uzmanlar üzerinden softmax", lambda z, k: {"uzmanlar": topk_yonlendirme(z, k)["uzmanlar"], "agirliklar": [math.exp(z[i] - max(z)) / sum(math.exp(v - max(z)) for v in z) for i in topk_yonlendirme(z, k)["uzmanlar"]]}),
    ("ters sıralama", lambda z, k: dict(topk_yonlendirme(z, k), uzmanlar=list(reversed(topk_yonlendirme(z, k)["uzmanlar"])))),
    ("eşit ağırlık", lambda z, k: dict(topk_yonlendirme(z, k), agirliklar=[1.0 / k] * k))
]:
    ok(not sinama1(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(topk_yonlendirme, _il.import_module('ai_gercek_ai_temel_28').referans_topk_yonlendirme, ([2.5, -0.5, 1.5, 0.2], 2), tohum=2664)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def topk_yonlendirme(logitler, k):
    if not isinstance(logitler, list) or len(logitler) < 2:
        raise ValueError("logitler")
    for x in logitler:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
            raise ValueError("sayi")
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= len(logitler):
        raise ValueError("k")
    secilen = sorted(range(len(logitler)), key=lambda i: (-logitler[i], i))[:k]
    m = max(logitler[i] for i in secilen)
    exps = [math.exp(logitler[i] - m) for i in secilen]
    top = sum(exps)
    return {"uzmanlar": secilen, "agirliklar": [v / top for v in exps]}

from ai_temel_veri import json_yukle
v = json_yukle("veri/moe_router.json")
print("Top-K:", topk_yonlendirme(v["ornek_logit"], v["k"]))
```
```hint
`sorted(range(len(logitler)), key=lambda i: (-logitler[i], i))[:k]` ile seçilen indisleri bul ve yalnız bu indislerin logitleri üzerinde softmax hesapla.
```
:::

::: anlat Yardımcı yük dengeleme kaybı (Auxiliary Load-Balancing Loss)
$T$ token ve $E$ uzman (`uzman_sayisi`) için:
- Her token $t$'de $k$ adet benzersiz uzman seçilmiştir (`secilen_uzmanlar[t]`).
- Uzman $e$'nin seçilme kesri:
  $$f_e = \frac{\text{uzman } e\text{'nin toplam seçilme sayısı}}{T \cdot k}$$
- Uzman $e$'nin ortalama yönlendirici olasılığı:
  $$P_e = \frac{1}{T} \sum_{t=0}^{T-1} \text{router\_olasilik}[t][e]$$
- Yardımcı kayıp:
  $$\mathcal{L}_{\text{aux}} = E \sum_{e=0}^{E-1} f_e \cdot P_e$$

**Görev 2'de sık tuzaklar:** Formüldeki $E$ (`uzman_sayisi`) çarpanını unutmak veya bir tokenın `secilen_uzmanlar[t]` listesinde aynı uzmanın birden fazla kez geçmesini (`len(set(s)) != len(s)`) geçerli kabul etmek.
:::

::: gorev 2 · Yardımcı yük dengeleme kaybı
`yuk_dengeleme_kaybi(router_olasilik, secilen_uzmanlar, uzman_sayisi)`: `uzman_sayisi` bool olmayan `int >= 2` ($E$); `router_olasilik` boş olmayan `list` ($T$ token), her eleman uzunluğu $E$ olan geçerli olasılık dağılımı (`0 <= p <= 1`, toplamı `1.0`); `secilen_uzmanlar` uzunluğu $T$ olan `list`, her eleman aynı uzunlukta ($1 \le k \le E$) benzersiz geçerli uzman indisi listesi. $E \sum_{e=0}^{E-1} f_e P_e$ değerini `float` olarak döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-28")
```
```starter
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def yuk_dengeleme_kaybi(router_olasilik, secilen_uzmanlar, uzman_sayisi):
    T = len(router_olasilik)
    k = len(secilen_uzmanlar[0])
    sayac = [0] * uzman_sayisi
    for s in secilen_uzmanlar:
        for idx in s:
            sayac[idx] += 1
    f = [c / (T * k) for c in sayac]
    P = [sum(router_olasilik[t][e] for t in range(T)) / T for e in range(uzman_sayisi)]
    return sum(f[e] * P[e] for e in range(uzman_sayisi))

from ai_temel_veri import json_yukle
v = json_yukle("veri/moe_router.json")
for s in v["senaryolar"]:
    print(s["ad"], round(yuk_dengeleme_kaybi(s["router_olasilik"], s["secilen_uzmanlar"], v["uzman_sayisi"]), 4))
```
```test
def sinama2(f):
    import copy, random
    def _r(ro, su, E):
        T = len(ro); k = len(su[0]); c = [0] * E
        for s in su:
            for i in s: c[i] += 1
        fv = [x / (T * k) for x in c]
        Pv = [sum(ro[t][e] for t in range(T)) / T for e in range(E)]
        return float(E * sum(fv[e] * Pv[e] for e in range(E)))
    try:
        ro = [[0.25, 0.25, 0.25, 0.25]] * 4
        su = [[0, 1], [2, 3], [0, 2], [1, 3]]
        old = copy.deepcopy((ro, su))
        if abs(f(ro, su, 4) - 1.0) > 1e-12 or (ro, su) != old: return False
        ro2 = [[0.9, 0.1], [0.9, 0.1]]
        su2 = [[0], [0]]
        if abs(f(ro2, su2, 2) - 1.8) > 1e-12: return False
        # Top-1 ile tutarlı dağılım: yardımcı kayıp 1'in altına inebilir.
        ro_alt = [[0.51, 0.49] for _ in range(9)] + [[0.0, 1.0]]
        su_alt = [[0] for _ in range(9)] + [[1]]
        if abs(f(ro_alt, su_alt, 2) - 0.9344) > 1e-12: return False
        rng = random.Random(2828)
        for _ in range(20):
            E = rng.randint(2, 6); T = rng.randint(2, 6); k = rng.randint(1, E)
            r_l, s_l = [], []
            for _ in range(T):
                w = [rng.uniform(0.1, 1.0) for _ in range(E)]; sw = sum(w)
                r_l.append([x / sw for x in w])
                s_l.append(rng.sample(range(E), k))
            if abs(f(copy.deepcopy(r_l), copy.deepcopy(s_l), E) - _r(r_l, s_l, E)) > 1e-12: return False
        for bad in (
            ([], [], 2), ([[1.0]], [[0]], 1), ([[-0.5, 0.75, 0.75]], [[0]], 3), ([[0.5, 0.5]], [[]], 2), ([[0.5, 0.5]], [[0]], 1), ([[0.5, 0.5]], [[0]], True),
            ([[0.5, 0.5]], [[0, 0]], 2), ([[0.5, 0.5]], [[2]], 2), ([[0.5, 0.5]], [[-1]], 2),
            ([[0.6, 0.6]], [[0]], 2), ([[0.5, 0.5], [0.5, 0.5]], [[0], [0, 1]], 2),
            ([[0.5, 0.5]], [[0], [1]], 2), ([[True, 0.0]], [[0]], 2)
        ):
            try:
                f(*bad)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sinama2(yuk_dengeleme_kaybi), "E çarpanı, atanma kesri f_e, olasılık ortalaması P_e ve geçersiz girdi")
for ad, mut in [
    ("E çarpanı yok", lambda ro, su, E: yuk_dengeleme_kaybi(ro, su, E) / E),
    ("sabit 1.0", lambda ro, su, E: 1.0),
    ("k bölmesi yok", lambda ro, su, E: yuk_dengeleme_kaybi(ro, su, E) * len(su[0]))
]:
    ok(not sinama2(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(yuk_dengeleme_kaybi, _il.import_module('ai_gercek_ai_temel_28').referans_yuk_kaybi, ([[0.45, 0.35, 0.1, 0.1], [0.1, 0.4, 0.4, 0.1], [0.1, 0.1, 0.45, 0.35], [0.35, 0.15, 0.1, 0.4]], [[0, 1], [1, 2], [2, 3], [3, 0]], 4), tohum=2930,
             ekler=(([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]], [[0, 1], [1, 2]], 4), ([[0.5, 0.5, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]], [[0], [3]], 4),
                    ([[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]], [[0], [1], [0]], 2)))
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def yuk_dengeleme_kaybi(router_olasilik, secilen_uzmanlar, uzman_sayisi):
    if isinstance(uzman_sayisi, bool) or not isinstance(uzman_sayisi, int) or uzman_sayisi < 2:
        raise ValueError("uzman_sayisi")
    if not isinstance(router_olasilik, list) or not isinstance(secilen_uzmanlar, list) or not router_olasilik or len(router_olasilik) != len(secilen_uzmanlar):
        raise ValueError("boyut")
    T = len(router_olasilik)
    k_boyut = None
    sayac = [0] * uzman_sayisi
    for p, s in zip(router_olasilik, secilen_uzmanlar):
        if not isinstance(p, list) or len(p) != uzman_sayisi:
            raise ValueError("olasilik_boyut")
        for x in p:
            if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or not 0.0 <= x <= 1.0:
                raise ValueError("olasilik_deger")
        if abs(sum(p) - 1.0) > 1e-6:
            raise ValueError("olasilik_toplam")
        if not isinstance(s, list) or not s or len(s) > uzman_sayisi:
            raise ValueError("secilen_liste")
        if k_boyut is not None and len(s) != k_boyut:
            raise ValueError("k_farkli")
        k_boyut = len(s)
        if len(set(s)) != len(s):
            raise ValueError("tekrarli_uzman")
        for idx in s:
            if isinstance(idx, bool) or not isinstance(idx, int) or not 0 <= idx < uzman_sayisi:
                raise ValueError("uzman_indis")
            sayac[idx] += 1
    toplam_atama = float(T * k_boyut)
    f = [c / toplam_atama for c in sayac]
    P = [sum(router_olasilik[t][e] for t in range(T)) / float(T) for e in range(uzman_sayisi)]
    return float(uzman_sayisi * sum(f[e] * P[e] for e in range(uzman_sayisi)))

from ai_temel_veri import json_yukle
v = json_yukle("veri/moe_router.json")
for s in v["senaryolar"]:
    print(s["ad"], round(yuk_dengeleme_kaybi(s["router_olasilik"], s["secilen_uzmanlar"], v["uzman_sayisi"]), 4))
```
```hint
Her token için seçilen uzman listesinde tekrar olmadığını (`len(set(s)) == len(s)`) doğrula ve en sonda toplamı `uzman_sayisi` ile çarp.
```
:::

::: anlat Uzman kapasitesi ve düşürülen atamalar
Toplam atama sayısı $M = T \cdot k$ iken uzman başına düşen ideal ortalama yük $M / E$ olur. `kapasite_faktoru` ($CF > 0$) ile her uzmanın kabul edebileceği tavan atama sayısı:
$$\text{uzman\_kapasitesi} = \max\left(1, \left\lceil \frac{T \cdot k}{E} \cdot CF \right\rceil\right)$$
Her uzman $e$ için gelen toplam atama sayısı `uzman_yukleri[e]` olarak sayılır. Kapasiteyi aşan atamaların toplamı `dusurulen_atama = sum(max(0, y - uzman_kapasitesi) for y in uzman_yukleri)` ve oranı `dusurulme_orani = dusurulen_atama / (T * k)` olur. Ayrıca tek bir uzman tokenların yarısından fazlasına atanmışsa (`max(uzman_yukleri) > 0.5 * T`), `uzman_cokmesi = True` işaretlenir.

Eşik neden $M/2$ değil de $T/2$? Bir token aynı uzmanı iki kez seçemez, bu yüzden bir uzmanın yükü en çok $T = M/k$ olabilir. $k = 2$ iken "toplam atamaların yarısı" eşiği $M/2 = T$ olur ve hiçbir yük onu **aşamaz**: tüm tokenları tek uzmana yığılmış, tamamen çökmüş bir yönlendirici bile "çökme yok" diye raporlanırdı. Token sayısına göre tanımlanan eşik her $k$ için anlamlıdır ve $k = 1$'de eski tanımla aynıdır.

**Görev 3'te sık tuzaklar:** Tavan yuvarlamada `math.ceil` yerine `int` kesmesi kullanmak, kapasiteyi `uzman_sayisi`'na bölmeden hesaplamak veya çökme eşiğini token sayısı yerine toplam atama sayısıyla kurmak.
:::

::: gorev 3 · Uzman kapasitesi ve düşürülme raporu
`kapasite_raporu(secilen_uzmanlar, uzman_sayisi, kapasite_faktoru)`: `secilen_uzmanlar` ve `uzman_sayisi` Görev 2 kurallarına uyar; `kapasite_faktoru` bool olmayan sonlu sayı ve `> 0`. Yukarıdaki kuralla `{"uzman_kapasitesi": int, "uzman_yukleri": list[int], "dusurulen_atama": int, "dusurulme_orani": float, "uzman_cokmesi": bool}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-28")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def kapasite_raporu(secilen_uzmanlar, uzman_sayisi, kapasite_faktoru):
    T = len(secilen_uzmanlar)
    k = len(secilen_uzmanlar[0])
    kapasite = int(T * k)
    yukler = [0] * uzman_sayisi
    for s in secilen_uzmanlar:
        for idx in s:
            yukler[idx] += 1
    return {
        "uzman_kapasitesi": kapasite,
        "uzman_yukleri": yukler,
        "dusurulen_atama": 0,
        "dusurulme_orani": 0.0,
        "uzman_cokmesi": False,
    }

from ai_temel_veri import json_yukle
v = json_yukle("veri/moe_router.json")
for s in v["senaryolar"]:
    print(s["ad"], kapasite_raporu(s["secilen_uzmanlar"], v["uzman_sayisi"], v["kapasite_faktoru"]))
```
```test
def sinama3(f):
    import copy, math, random
    def _r(su, E, cf):
        T = len(su); k = len(su[0]); M = T * k
        kap = max(1, int(math.ceil((M / E) * cf)))
        y = [0] * E
        for s in su:
            for i in s: y[i] += 1
        d = sum(max(0, v - kap) for v in y)
        return {"uzman_kapasitesi": kap, "uzman_yukleri": y, "dusurulen_atama": d, "dusurulme_orani": d / M, "uzman_cokmesi": bool(max(y) > 0.5 * T)}
    try:
        su = [[0], [0], [0], [1]]
        old = copy.deepcopy(su)
        c = f(su, 4, 1.0)
        if c != {"uzman_kapasitesi": 1, "uzman_yukleri": [3, 1, 0, 0], "dusurulen_atama": 2, "dusurulme_orani": 0.5, "uzman_cokmesi": True} or su != old:
            return False
        if f([[0, 1], [0, 2], [0, 3]], 4, 1.0) != {"uzman_kapasitesi": 2, "uzman_yukleri": [3, 1, 1, 1], "dusurulen_atama": 1, "dusurulme_orani": 1 / 6, "uzman_cokmesi": True}:
            return False
        c2 = f([[0, 1], [2, 3]], 4, 1.0)
        if c2 != {"uzman_kapasitesi": 1, "uzman_yukleri": [1, 1, 1, 1], "dusurulen_atama": 0, "dusurulme_orani": 0.0, "uzman_cokmesi": False}:
            return False
        rng = random.Random(2803)
        for _ in range(25):
            E = rng.randint(2, 6); T = rng.randint(2, 8); k = rng.randint(1, E); cf = rng.uniform(0.5, 2.0)
            s_l = [rng.sample(range(E), k) for _ in range(T)]
            if f(copy.deepcopy(s_l), E, cf) != _r(s_l, E, cf): return False
        for bad in (
            ([], 4, 1.0), ([[]], 4, 1.0), ([[0]], 1, 1.0), ([[0, 0]], 4, 1.0), ([[4]], 4, 1.0),
            ([[0], [0, 1]], 4, 1.0), ([[0]], 4, 0.0), ([[0]], 4, -0.5),
            ([[0]], 4, True), ([[0]], 4, float("nan")), ([[True]], 4, 1.0)
        ):
            try:
                f(*bad)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sinama3(kapasite_raporu), "tavan kapasite, düşürülen atama, uzman çökmesi bayrağı ve geçersiz girdi")
for ad, mut in [
    ("düşürülen hep 0", lambda su, E, cf: dict(kapasite_raporu(su, E, cf), dusurulen_atama=0, dusurulme_orani=0.0)),
    ("çökme hep yanlış", lambda su, E, cf: dict(kapasite_raporu(su, E, cf), uzman_cokmesi=False)),
    ("kapasite +1", lambda su, E, cf: dict(kapasite_raporu(su, E, cf), uzman_kapasitesi=kapasite_raporu(su, E, cf)["uzman_kapasitesi"] + 1))
]:
    ok(not sinama3(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(kapasite_raporu, _il.import_module('ai_gercek_ai_temel_28').referans_kapasite_raporu, ([[0, 1], [1, 2], [2, 3], [3, 0]], 4, 1.25), tohum=2543)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def kapasite_raporu(secilen_uzmanlar, uzman_sayisi, kapasite_faktoru):
    if isinstance(uzman_sayisi, bool) or not isinstance(uzman_sayisi, int) or uzman_sayisi < 2:
        raise ValueError("uzman_sayisi")
    if isinstance(kapasite_faktoru, bool) or not isinstance(kapasite_faktoru, (int, float)) or not math.isfinite(kapasite_faktoru) or kapasite_faktoru <= 0.0:
        raise ValueError("kapasite_faktoru")
    if not isinstance(secilen_uzmanlar, list) or not secilen_uzmanlar:
        raise ValueError("secilen_uzmanlar")
    T = len(secilen_uzmanlar)
    k_boyut = None
    yukler = [0] * uzman_sayisi
    for s in secilen_uzmanlar:
        if not isinstance(s, list) or not s or len(s) > uzman_sayisi:
            raise ValueError("secilen_liste")
        if k_boyut is not None and len(s) != k_boyut:
            raise ValueError("k_farkli")
        k_boyut = len(s)
        if len(set(s)) != len(s):
            raise ValueError("tekrarli_uzman")
        for idx in s:
            if isinstance(idx, bool) or not isinstance(idx, int) or not 0 <= idx < uzman_sayisi:
                raise ValueError("uzman_indis")
            yukler[idx] += 1
    toplam_atama = T * k_boyut
    kapasite = max(1, int(math.ceil((toplam_atama / float(uzman_sayisi)) * kapasite_faktoru)))
    dusurulen = sum(max(0, y - kapasite) for y in yukler)
    return {
        "uzman_kapasitesi": kapasite,
        "uzman_yukleri": yukler,
        "dusurulen_atama": dusurulen,
        "dusurulme_orani": dusurulen / float(toplam_atama),
        "uzman_cokmesi": bool(max(yukler) > 0.5 * T),
    }

from ai_temel_veri import json_yukle
v = json_yukle("veri/moe_router.json")
for s in v["senaryolar"]:
    print(s["ad"], kapasite_raporu(s["secilen_uzmanlar"], v["uzman_sayisi"], v["kapasite_faktoru"]))
```
```hint
`toplam_atama = T * k` değerini `uzman_sayisi`'na bölüp `kapasite_faktoru` ile çarp ve `math.ceil` uygula.
```
:::

::: anlat Hata vitrini · çalışmış yanlış rapor
Yazar, kusurlu başlangıç kodlarını görünür sentetik veriyle gerçekten çalıştırdı ve sonucu `outputs/yeni-ai-temel-28/gorunur-run-1.json` dosyasına kaydetti. `uzman_cokmesi_senaryosu` için kusurlu kod $E$ çarpanını unuttuğundan `0.47125` kayıp ve `dusurulen_atama=0` verirken; doğru kod `1.885` kayıp ve `uzman_kapasitesi=3` üzerinden `dusurulen_atama=2` (`dusurulme_orani=0.25`) döndürür.

Bu kaydedilmiş bir hesaplama çıktısıdır, model yanıtı değildir ve rapor sentetiktir. Uzmanların yarısı (`2` ve `3` numaralı uzmanlar) hiç token almazken `dusurulen_atama=0` raporlayan kusurlu kod hangi donanım darboğazını gizler? Kendi cümlenle açıkla. Gerçek finaldeki ölçüm ayrıca üretilir; bu sayılar onun yerine konmaz.
:::

::: anlat Gerçek deney: SmolLM2'nin MLP bloğundan damıtılan MoE'de uzman çökmesi
Elimizde ön eğitimli bir MoE modeli yok; bu yüzden final, literatürdeki **upcycling** fikrinin küçük bir sürümünü gerçek bir modelde kurar. SmolLM2-135M'in 15. katmanındaki yoğun (dense) MLP bloğu, modelin kendi ürettiği ~600 tokenlık metinde gözlenir: her token için bloğun gerçek girdisi ($x \in \mathbb{R}^{576}$) ve gerçek çıktısı kaydedilir. Sonra 8 küçük SwiGLU uzmanı (her biri 192 gizli birim; toplamda orijinal 1536'lık MLP ile aynı genişlik) ve top-2 yönlendiricisi bu çıktıyı taklit edecek şekilde eğitilir (damıtma: $\lVert \text{MoE}(x) - \text{MLP}(x) \rVert^2$).

Çökme mekanizmasını görünür kılmak için yönlendirici, 0. uzmana +3 logit yanlılığıyla başlatılır. Bu, gerçek eğitimin başındaki rastgele dengesizliğin abartılmış hâlidir: tokenları alan uzman gradyan alır ve gelişir, hiç token almayan uzmanın ağırlıklarına hiç gradyan ulaşmaz. Aynı başlangıçtan iki model eğitilir:
- `dengesiz`: yalnızca damıtma kaybı. 
- `dengeli`: damıtma kaybı + $0.3 \cdot E \sum_e f_e P_e$.

Eğitim bittikten sonra iki yönlendirici, eğitimde görülmemiş ~105 tokenlık ayrık bir metinde çalıştırılır. Gerçek logitlerde **senin `topk_yonlendirme`, `yuk_dengeleme_kaybi` ve `kapasite_raporu` işlevlerin** çalışır ve bağımsız referansla karşılaştırılır. Son olarak her MoE, modelin içine MLP'nin yerine takılır (kapasite aşan atamalar gerçekten düşürülerek) ve ayrık metindeki dil modeli kaybı ölçülür.

Yazarın GPU koşularında (iki koşu): `dengesiz` yönlendiricide 0. uzman 105 tokenın 101–105'ini aldı, iki uzman 0–2 token aldı. Aux kaybı 1.58–1.65, kapasite (33) aşımından düşen atama 74–82 idi. `dengeli` yönlendiricide aux 1.02–1.07, düşen 9–28 idi. LM kaybı temiz modelde 3.224, iki MoE'de de ~3.27–3.28 idi. Damıtma MLP'yi iyi taklit ediyor; bu kısa metinde dengesizliğin kalite maliyeti küçük, **donanım maliyeti** (düşen atamalar, boş duran uzmanlar) büyük.

**Güvenlik yönü — çöken MoE'de tek uzmanın etki alanı.** Her iki MoE'de en çok yük alan uzmanın çıkışı ters çevrilir: bozuk bir uzman ağırlık dosyasının, bir bit hatasının ya da tedarik zincirinde kurcalanmış tek bir uzmanın benzeri. Bu uzmanın dokunduğu token oranı ölçülür ve model yeniden çalıştırılır. Dengesiz (çökmüş) MoE'de bozuk uzman tokenların **hepsine** dokunur, dengeli MoE'de yarısı kadarına. Yük dengeleme yalnız donanım verimi değildir; tek bir bileşenin bozulmasının etki alanını da daraltır. Bozukluk 30 katmandan yalnız birinde olduğu için LM kaybındaki değişim küçüktür ve koşudan koşuya değişir; asıl ölçü etkilenen token oranıdır.

**Kanıt dosyasını oku:** Soru 1: `dengesiz.kapasite.uzman_yukleri` içinde sıfıra yakın uzmanlar neden eğitim boyunca kendini toparlayamadı? Soru 2: Düşen atama 80'den 10–25'e indiği hâlde LM kaybı neden neredeyse aynı kaldı? (İpucu: düşen atama artık bağlantı üzerinden geçer; top-2'nin ikinci uzmanı da çoğu zaman işler.) Cevabını tezgâhta yorum olarak yaz; otomatik test bu serbest açıklamayı puanlamaz.
:::

::: gorev Gerçek deney · PyTorch MoE katmanında Top-K yönlendirme ve yük dengeleme
Önceki üç görevin `topk_yonlendirme`, `yuk_dengeleme_kaybi` ve `kapasite_raporu` işlevlerini birleştir. Çalıştır gerçek tabloyu gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 180
```
```starter
import ai_lab
import math
def topk_yonlendirme(logitler, k):
    sec = sorted(range(len(logitler)), key=lambda i: logitler[i], reverse=True)[:k]
    return {"uzmanlar": sec, "agirliklar": [1.0 / k] * k}
def yuk_dengeleme_kaybi(router_olasilik, secilen_uzmanlar, uzman_sayisi):
    return 1.0
def kapasite_raporu(secilen_uzmanlar, uzman_sayisi, kapasite_faktoru):
    return {"uzman_kapasitesi": 64, "uzman_yukleri": [0] * uzman_sayisi, "dusurulen_atama": 0, "dusurulme_orani": 0.0, "uzman_cokmesi": False}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_28 as D
    D.goster(topk_yonlendirme, yuk_dengeleme_kaybi, kapasite_raporu)
```
```test
import ai_lab, math
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('referans_topk_yonlendirme', 'referans_yuk_kaybi', 'referans_kapasite_raporu', 'kanit_yaz', '_yakin'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
topk_yonlendirme = need("topk_yonlendirme")
yuk_dengeleme_kaybi = need("yuk_dengeleme_kaybi")
kapasite_raporu = need("kapasite_raporu")
def sinama1(f):
    import math, random
    def _r(z, k):
        s = sorted(range(len(z)), key=lambda i: (-z[i], i))[:k]; m = max(z[i] for i in s)
        e = [math.exp(z[i] - m) for i in s]; t = sum(e)
        return {"uzmanlar": s, "agirliklar": [v / t for v in e]}
    def _y(a, b): return set(a) == {"uzmanlar", "agirliklar"} and a["uzmanlar"] == b["uzmanlar"] and len(a["agirliklar"]) == len(b["agirliklar"]) and all(abs(p - q) < 1e-12 for p, q in zip(a["agirliklar"], b["agirliklar"]))
    try:
        z = [1.0, 3.0, 3.0, -5.0]; old = list(z)
        if not _y(f(z, 2), {"uzmanlar": [1, 2], "agirliklar": [0.5, 0.5]}) or z != old or not _y(f([800.0, 801.0], 2), _r([800.0, 801.0], 2)): return False
        rng = random.Random(28)
        for _ in range(25):
            n = rng.randint(2, 8); zv = [rng.uniform(-30, 30) for _ in range(n)]; kv = rng.randint(1, n)
            if not _y(f(list(zv), kv), _r(zv, kv)): return False
        for bad in ((None, 1), ([], 1), ([1.0], 1), ((1.0, 2.0), 1), ([True, 1.0], 1), ([float("nan"), 1.0], 1), ([float("inf"), 1.0], 1), ([1.0, 2.0], 0), ([1.0, 2.0], 3), ([1.0, 2.0], -1), ([1.0, 2.0], True), ([1.0, 2.0], 1.5), ([1.0, 2.0], "1")):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama1(topk_yonlendirme), "Top-K sıralama, eşitlik kırılımı, alt-küme softmax ve geçersiz girdi")
for ad, mut in [("tüm uzmanlar üzerinden softmax", lambda z, k: {"uzmanlar": topk_yonlendirme(z, k)["uzmanlar"], "agirliklar": [math.exp(z[i] - max(z)) / sum(math.exp(v - max(z)) for v in z) for i in topk_yonlendirme(z, k)["uzmanlar"]]}), ("ters sıralama", lambda z, k: dict(topk_yonlendirme(z, k), uzmanlar=list(reversed(topk_yonlendirme(z, k)["uzmanlar"])))), ("eşit ağırlık", lambda z, k: dict(topk_yonlendirme(z, k), agirliklar=[1.0 / k] * k))]:
    kontrol(not sinama1(mut), "mutant reddedildi: " + ad)
def sinama2(f):
    import copy, random
    def _r(ro, su, E):
        T = len(ro); k = len(su[0]); c = [0] * E
        for s in su:
            for i in s: c[i] += 1
        fv = [x / (T * k) for x in c]; Pv = [sum(ro[t][e] for t in range(T)) / T for e in range(E)]
        return float(E * sum(fv[e] * Pv[e] for e in range(E)))
    try:
        ro = [[0.25, 0.25, 0.25, 0.25]] * 4; su = [[0, 1], [2, 3], [0, 2], [1, 3]]; old = copy.deepcopy((ro, su))
        if abs(f(ro, su, 4) - 1.0) > 1e-12 or (ro, su) != old: return False
        # Top-1 ile tutarlı dağılım: yardımcı kayıp 1'in altına inebilir.
        ro_alt = [[0.51, 0.49] for _ in range(9)] + [[0.0, 1.0]]
        su_alt = [[0] for _ in range(9)] + [[1]]
        if abs(f(ro_alt, su_alt, 2) - 0.9344) > 1e-12: return False
        rng = random.Random(2828)
        for _ in range(20):
            E = rng.randint(2, 6); T = rng.randint(2, 6); k = rng.randint(1, E); r_l, s_l = [], []
            for _ in range(T):
                w = [rng.uniform(0.1, 1.0) for _ in range(E)]; sw = sum(w); r_l.append([x / sw for x in w]); s_l.append(rng.sample(range(E), k))
            if abs(f(copy.deepcopy(r_l), copy.deepcopy(s_l), E) - _r(r_l, s_l, E)) > 1e-12: return False
        for bad in (([], [], 2), ([[1.0]], [[0]], 1), ([[-0.5, 0.75, 0.75]], [[0]], 3), ([[0.5, 0.5]], [[]], 2), ([[0.5, 0.5]], [[0]], 1), ([[0.5, 0.5]], [[0]], True), ([[0.5, 0.5]], [[0, 0]], 2), ([[0.5, 0.5]], [[2]], 2), ([[0.5, 0.5]], [[-1]], 2), ([[0.6, 0.6]], [[0]], 2), ([[0.5, 0.5], [0.5, 0.5]], [[0], [0, 1]], 2), ([[0.5, 0.5]], [[0], [1]], 2), ([[True, 0.0]], [[0]], 2)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama2(yuk_dengeleme_kaybi), "E çarpanı, atanma kesri f_e, olasılık ortalaması P_e ve geçersiz girdi")
for ad, mut in [("E çarpanı yok", lambda ro, su, E: yuk_dengeleme_kaybi(ro, su, E) / E), ("sabit 1.0", lambda ro, su, E: 1.0), ("k bölmesi yok", lambda ro, su, E: yuk_dengeleme_kaybi(ro, su, E) * len(su[0]))]:
    kontrol(not sinama2(mut), "mutant reddedildi: " + ad)
def sinama3(f):
    import copy, math, random
    def _r(su, E, cf):
        T = len(su); k = len(su[0]); M = T * k; kap = max(1, int(math.ceil((M / E) * cf))); y = [0] * E
        for s in su:
            for i in s: y[i] += 1
        d = sum(max(0, v - kap) for v in y)
        return {"uzman_kapasitesi": kap, "uzman_yukleri": y, "dusurulen_atama": d, "dusurulme_orani": d / M, "uzman_cokmesi": bool(max(y) > 0.5 * T)}
    try:
        su = [[0], [0], [0], [1]]; old = copy.deepcopy(su)
        if f(su, 4, 1.0) != {"uzman_kapasitesi": 1, "uzman_yukleri": [3, 1, 0, 0], "dusurulen_atama": 2, "dusurulme_orani": 0.5, "uzman_cokmesi": True} or su != old: return False
        if f([[0, 1], [0, 2], [0, 3]], 4, 1.0) != {"uzman_kapasitesi": 2, "uzman_yukleri": [3, 1, 1, 1], "dusurulen_atama": 1, "dusurulme_orani": 1 / 6, "uzman_cokmesi": True}: return False
        rng = random.Random(2803)
        for _ in range(25):
            E = rng.randint(2, 6); T = rng.randint(2, 8); k = rng.randint(1, E); cf = rng.uniform(0.5, 2.0)
            s_l = [rng.sample(range(E), k) for _ in range(T)]
            if f(copy.deepcopy(s_l), E, cf) != _r(s_l, E, cf): return False
        for bad in (([], 4, 1.0), ([[]], 4, 1.0), ([[0]], 1, 1.0), ([[0, 0]], 4, 1.0), ([[4]], 4, 1.0), ([[0], [0, 1]], 4, 1.0), ([[0]], 4, 0.0), ([[0]], 4, -0.5), ([[0]], 4, True), ([[0]], 4, float("nan")), ([[True]], 4, 1.0)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama3(kapasite_raporu), "tavan kapasite, düşürülen atama, uzman çökmesi bayrağı ve geçersiz girdi")
for ad, mut in [("düşürülen hep 0", lambda su, E, cf: dict(kapasite_raporu(su, E, cf), dusurulen_atama=0, dusurulme_orani=0.0)), ("çökme hep yanlış", lambda su, E, cf: dict(kapasite_raporu(su, E, cf), uzman_cokmesi=False)), ("kapasite +1", lambda su, E, cf: dict(kapasite_raporu(su, E, cf), uzman_kapasitesi=kapasite_raporu(su, E, cf)["uzman_kapasitesi"] + 1))]:
    kontrol(not sinama3(mut), "mutant reddedildi: " + ad)
# farksal tarama (final)
import importlib as _il
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_R = _il.import_module('sandbox.ai_gercek_ai_temel_28')
for _ad, _ref, _taban, _toh in (
    ('topk_yonlendirme', 'referans_topk_yonlendirme', ([2.5, -0.5, 1.5, 0.2], 2), 3186),
    ('yuk_dengeleme_kaybi', 'referans_yuk_kaybi', ([[0.45, 0.35, 0.1, 0.1], [0.1, 0.4, 0.4, 0.1], [0.1, 0.1, 0.45, 0.35], [0.35, 0.15, 0.1, 0.4]], [[0, 1], [1, 2], [2, 3], [3, 0]], 4), 3452),
    ('kapasite_raporu', 'referans_kapasite_raporu', ([[0, 1], [1, 2], [2, 3], [3, 0]], 4, 1.25), 3065),
):
    _t, _g = _ff(need(_ad), getattr(_R, _ref), _taban, tohum=_toh)
    kontrol(_t, "farksal tarama (" + _ad + "): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
if not all(checks): stop()
from sandbox import ai_gercek_ai_temel_28 as D
try: r = D.deney(topk_yonlendirme, yuk_dengeleme_kaybi, kapasite_raporu)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r["topk_ayni"], "SmolLM2 MLP'sinden damıtılan MoE'nin gerçek router logitlerinde Top-K yönlendirme bağımsız referansla aynı")
kontrol(r["yuk_ayni"], "iki yönlendiricide yardımcı yük kaybı referansla aynı")
kontrol(r["kapasite_ayni"], "iki yönlendiricide kapasite raporu referansla aynı")
kontrol(r["dengesiz"]["kapasite"]["uzman_cokmesi"], "yardımcı kayıpsız eğitimde uzman çökmesi ölçüldü: " + str(r["dengesiz"]["kapasite"]["uzman_yukleri"]))
kontrol(r["kayip_azaldi"], "yardımcı yük dengeleme sonrası aux_loss düştü: %.3f -> %.3f" % (r["dengesiz"]["aux_kayip"], r["dengeli"]["aux_kayip"]))
kontrol(r["dusurulme_azaldi"], "yük dengeleme sonrası kapasite aşımından düşürülen atama azaldı: %d -> %d" % (r["dengesiz"]["kapasite"]["dusurulen_atama"], r["dengeli"]["kapasite"]["dusurulen_atama"]))
kontrol(r["cokme_etki_alanini_buyutur"], "kurcalanmış en yüklü uzman çökmüş MoE'de tokenların %%%.0f'ine, dengeli MoE'de %%%.0f'ine dokundu" % (100 * r["bozuk_uzman"]["dengesiz"]["etkilenen_token_orani"], 100 * r["bozuk_uzman"]["dengeli"]["etkilenen_token_orani"]))
kontrol(r["dengeli"]["takili_lm_kaybi"] < r["temiz_lm_kaybi"] + 0.5, "MoE modelin içine takıldığında dil modeli kaybı makul kaldı (damıtma gerçekten MLP'yi taklit ediyor)")
ai_lab.kanit_yaz("ai-temel-28-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-temel-28", "deney": r})
```
```solution
import ai_lab
import math
def topk_yonlendirme(logitler, k):
    if not isinstance(logitler, list) or len(logitler) < 2:
        raise ValueError("logitler")
    for x in logitler:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
            raise ValueError("sayi")
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= len(logitler):
        raise ValueError("k")
    secilen = sorted(range(len(logitler)), key=lambda i: (-logitler[i], i))[:k]
    m = max(logitler[i] for i in secilen)
    exps = [math.exp(logitler[i] - m) for i in secilen]
    top = sum(exps)
    return {"uzmanlar": secilen, "agirliklar": [v / top for v in exps]}
def yuk_dengeleme_kaybi(router_olasilik, secilen_uzmanlar, uzman_sayisi):
    if isinstance(uzman_sayisi, bool) or not isinstance(uzman_sayisi, int) or uzman_sayisi < 2:
        raise ValueError("uzman_sayisi")
    if not isinstance(router_olasilik, list) or not isinstance(secilen_uzmanlar, list) or not router_olasilik or len(router_olasilik) != len(secilen_uzmanlar):
        raise ValueError("boyut")
    T = len(router_olasilik)
    k_boyut = None
    sayac = [0] * uzman_sayisi
    for p, s in zip(router_olasilik, secilen_uzmanlar):
        if not isinstance(p, list) or len(p) != uzman_sayisi:
            raise ValueError("olasilik_boyut")
        for x in p:
            if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or not 0.0 <= x <= 1.0:
                raise ValueError("olasilik_deger")
        if abs(sum(p) - 1.0) > 1e-6:
            raise ValueError("olasilik_toplam")
        if not isinstance(s, list) or not s or len(s) > uzman_sayisi:
            raise ValueError("secilen_liste")
        if k_boyut is not None and len(s) != k_boyut:
            raise ValueError("k_farkli")
        k_boyut = len(s)
        if len(set(s)) != len(s):
            raise ValueError("tekrarli_uzman")
        for idx in s:
            if isinstance(idx, bool) or not isinstance(idx, int) or not 0 <= idx < uzman_sayisi:
                raise ValueError("uzman_indis")
            sayac[idx] += 1
    toplam_atama = float(T * k_boyut)
    f = [c / toplam_atama for c in sayac]
    P = [sum(router_olasilik[t][e] for t in range(T)) / float(T) for e in range(uzman_sayisi)]
    return float(uzman_sayisi * sum(f[e] * P[e] for e in range(uzman_sayisi)))
def kapasite_raporu(secilen_uzmanlar, uzman_sayisi, kapasite_faktoru):
    if isinstance(uzman_sayisi, bool) or not isinstance(uzman_sayisi, int) or uzman_sayisi < 2:
        raise ValueError("uzman_sayisi")
    if isinstance(kapasite_faktoru, bool) or not isinstance(kapasite_faktoru, (int, float)) or not math.isfinite(kapasite_faktoru) or kapasite_faktoru <= 0.0:
        raise ValueError("kapasite_faktoru")
    if not isinstance(secilen_uzmanlar, list) or not secilen_uzmanlar:
        raise ValueError("secilen_uzmanlar")
    T = len(secilen_uzmanlar)
    k_boyut = None
    yukler = [0] * uzman_sayisi
    for s in secilen_uzmanlar:
        if not isinstance(s, list) or not s or len(s) > uzman_sayisi:
            raise ValueError("secilen_liste")
        if k_boyut is not None and len(s) != k_boyut:
            raise ValueError("k_farkli")
        k_boyut = len(s)
        if len(set(s)) != len(s):
            raise ValueError("tekrarli_uzman")
        for idx in s:
            if isinstance(idx, bool) or not isinstance(idx, int) or not 0 <= idx < uzman_sayisi:
                raise ValueError("uzman_indis")
            yukler[idx] += 1
    toplam_atama = T * k_boyut
    kapasite = max(1, int(math.ceil((toplam_atama / float(uzman_sayisi)) * kapasite_faktoru)))
    dusurulen = sum(max(0, y - kapasite) for y in yukler)
    return {
        "uzman_kapasitesi": kapasite,
        "uzman_yukleri": yukler,
        "dusurulen_atama": dusurulen,
        "dusurulme_orani": dusurulen / float(toplam_atama),
        "uzman_cokmesi": bool(max(yukler) > 0.5 * T),
    }
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_28 as D
    D.goster(topk_yonlendirme, yuk_dengeleme_kaybi, kapasite_raporu)
```
```hint
Üç işlevi birleştir. Kapasite ve yük dengeleme işlevlerinin her ikisinde de `secilen_uzmanlar` içindeki indislerin benzersiz olduğunu denetle.
```
:::

::: anlat Sınır
Bu ders tek katmanlı Top-$K$ yönlendirmeyi ve yardımcı kayıp tabanlı `load balancing` mekanizmasını gösterir. Gerçek deneydeki MoE ön eğitimli bir MoE modeli değildir: SmolLM2'nin tek bir katmanındaki MLP, ~600 tokenlık küçük bir derlemde damıtılır. Çökme, yönlendiriciye kasıtlı bir başlangıç yanlılığı verilerek tetiklenir; nötr başlangıçta yazarın koşularında bu kısa eğitim yalnız hafif dengesizlik üretti (aux ~1.04) ve yardımcı kaybın etkisi koşudan koşuya değişti. Paylaşımlı uzmanlar (shared experts), yardımcı kayıpsız dinamik yanlılık güncellemesi (aux-loss-free load balancing, DeepSeek-V3), uzmanların anlamsal uzmanlaşması ve büyük ölçekli dağıtık uzman paralelliği ölçülmez.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Seyrek etkinleştirme (20 sn).** "Yoğun MLP'de her token bütün ağırlıklardan geçer; MoE katmanı ise $E$ uzman arasından yalnız Top-$K$ uzmanı seçip kendi aralarında normalize eder, böylece parametre sayısı büyürken token başı FLOP sabit kalır."
2. **Çökme döngüsü ve $E \sum f_e P_e$ (35 sn).** "Başta azıcık öne geçen uzman daha çok token ve gradyan alarak diğer uzmanları köreltir. Yardımcı kayıp, kesikli atanma kesri $f_e$ ile türevlenebilir olasılık ortalaması $P_e$'yi çarpar; tam dengede $1.0$'dır ama genel alt sınır değildir (`0.9344` karşı örneği)."
3. **Kapasite tavanı ve etki alanı (40 sn).** "Statik tensör şekilleri için uzman kapasitesi $\lceil (T\cdot k/E)\cdot CF\rceil$ ile sınırlanır; taşan atamalar artık bağlantıdan düşer. SmolLM2 MLP damıtmasında çökme hem düşürülen atamayı fırlatır hem de bozuk tek bir uzmanın etki alanını tüm tokenlara yayar."
4. **Soru (25 sn).** "Yardımcı kayıp `1.0` civarındayken bile tek bir uzmanın kapasite aşımı yaşayıp yaşamadığını neden ayrıca `uzman_yukleri` ve `dusurulen_atama` ile izlemek zorundayız?"
:::
