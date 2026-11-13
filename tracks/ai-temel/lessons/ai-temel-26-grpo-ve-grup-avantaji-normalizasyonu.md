---
id: ai-temel-26
title: GRPO ve Grup Avantajı Normalizasyonu · Critic Ağsız Politika Optimizasyonu
summary: Grup içi bağıl avantajı (advantage) hesapla, negatif olmayan Schulman KL divergence tahmincisini kur ve kırpılmış GRPO kaybını GPU üzerinde doğrula.
esleme: ai-temel-10, ai-temel-11, ai-temel-12
timeout: 60
---

::: anlat Critic ağı olmadan politika nasıl güncellenir?
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| DeepSeekMath ve DeepSeek-R1 gibi akıl yürütme modelleri, PPO'daki ağır değer (critic) ağını kaldırıp `GRPO` ile aynı soruya üretilen $G$ çıktının grup içi ortalamasını taban çizgisi (baseline) yapar | İlk üç görev: `veri/grpo.json` içindeki **sentetik** grup ödülleri ve log-olasılıklar. Final: SmolLM2-135M'de doğrulanabilir ödüllü görevde (aritmetik dizi) 16 soru × $G=8$ rollout ile gerçek GRPO eğitimi ve görülmemiş sorularda ölçüm | Tek adımlı grup güncellemesinin uzun zincirli (CoT) ödül oyunlarını (reward hacking) tek başına engellediğini söyleyemez |
| Yansız negatif olmayan `KL divergence` cezası ($\exp(\Delta) - \Delta - 1$) politikanın referans modelden kopmasını sınırlar | Schulman yaklaşıklaması, PPO/GRPO oran kırpması (`clip_eps`) ve ödül çökmesi (`ifade_cokmesi`) tespiti | Sabit bir `beta` katsayısının her eğitim aşamasında optimal kaldığını kanıtlamaz |

> [!NOT]
> Görevler `veri/grpo.json` dosyasını okur; dosya sentetiktir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; değişiklikler taşınmaz, **kalıcılık yoktur**. Ekranda ayrı dosya görüntüleyici yoktur; içeriği görmek için `print` kullan. Gizli testler ayrıdır. Final yeni model indirmez ve GPU varsa onu kullanır.

ai-temel-11 tercih çiftleriyle DPO hizalamasını inceler. Peki doğrulanabilir matematik veya kod görevlerinde ikili tercih yerine bir ödül işlevi $r(q, o)$ varsa ve PPO'daki ikinci bir dev model olan değer ağını (value/critic network) bellekte tutmak istemiyorsak ne yaparız? **Group Relative Policy Optimization (`GRPO`) bu soruya yanıt verir (Shao vd. 2024).**

**Grup içi `advantage` normalizasyonu.** Aynı soru $q$ için eski politikadan $\pi_{\theta_{\text{old}}}$ toplam $G$ adet çıktı $\{o_1, \dots, o_G\}$ örneklenir ve ödülleri $\{r_1, \dots, r_G\}$ ölçülür. Grup ortalaması $\mu = \frac{1}{G}\sum_{i=1}^G r_i$ ve popülasyon standart sapması $\sigma = \sqrt{\frac{1}{G}\sum_{i=1}^G (r_i - \mu)^2}$ kullanılarak her çıktının bağıl avantajı hesaplanır:
$$A_i = \frac{r_i - \mu}{\sigma + \epsilon}$$

**Negatif olmayan `KL divergence` tahmincisi.** Standart log-oran farkı $\log \pi_\theta(o_i|q) - \log \pi_{\text{ref}}(o_i|q)$ tek bir örnekte negatif değer alabilir ve ceza terimi olarak kullanıldığında kararsızlık üretir. `GRPO`, Schulman'ın her örnekte $\ge 0$ olan yansız tahmincisini doğrudan kayba ekler ($\Delta_i = \log \pi_{\text{ref}}(o_i|q) - \log \pi_\theta(o_i|q)$):
$$D_{\text{KL}, i} = \exp(\Delta_i) - \Delta_i - 1 \ge 0$$

**Kırpılmış vekil hedef ve ifade çökmesi.** Oran $\rho_i = \exp(\log \pi_\theta - \log \pi_{\theta_{\text{old}}})$ hesaplanır ve $\tilde{\rho}_i = \text{clip}(\rho_i, 1-\epsilon_{\text{clip}}, 1+\epsilon_{\text{clip}})$ ile kırpılır. Vekil hedef $s_i = \min(\rho_i A_i, \tilde{\rho}_i A_i)$ olur. Ancak gruptaki $G$ çıktının tamamı aynı ödülü alırsa (ör. çok zor bir soruda hepsi `0.0` veya çok kolay soruda hepsi `1.0`), $\sigma = 0$ ve tüm $A_i = 0$ olur! Buna grup içi **ifade çökmesi** denir; o gruptan gelen politika gradyanı tamamen sıfırlanır.

**Saldırgan ne dener?** Doğrulayıcı (verifier) ödül fonksiyonundaki biçimsel bir açığı (ör. sonucu doğru hesaplamadan sadece son satıra beklenen şablonu yazmayı) keşfederse, grup içindeki o örnek yüksek pozitif `advantage` alır ve politika hızla bu kısayola yakınsar.

**Savunma neden kırılır?** `KL divergence` naif $\log \pi_\theta - \log \pi_{\text{ref}}$ olarak yazılırsa model negatif KL bölgesini ödül gibi sömürür; ayrıca `ifade_cokmesi` oranı izlenmezse eğitim adımlarının büyük kısmı sıfır avantajla boşa döner.

**Görev 1'de sık tuzaklar:** Popülasyon standart sapması ($\frac{1}{G}$) yerine örneklem standart sapması ($\frac{1}{G-1}$) kullanmak veya tüm ödüller eşitken `eps` eklemeden sıfıra bölmek.

Kaynaklar: [Shao vd. 2024 - DeepSeekMath: Pushing the Limits of Mathematical Reasoning in Open Language Models](https://arxiv.org/abs/2402.03300), [DeepSeek-AI 2025 - DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning](https://arxiv.org/abs/2501.12948), [Schulman vd. 2017 - Proximal Policy Optimization Algorithms](https://arxiv.org/abs/1707.06347). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Köprü: ai-temel-11 referans log-olasılık oranlarını DPO içinde kullanır; bu ders aynı log-oran mekaniğini grup içi `advantage` ve `KL divergence` düzenlemesiyle birleştirir.
:::

::: tahmin Gruptaki tüm ödüller aynı olduğunda ne olur?
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
import math
oduller = [1.0, 1.0, 1.0, 1.0]
ort = sum(oduller) / len(oduller)
std = math.sqrt(sum((x - ort) ** 2 for x in oduller) / len(oduller))
avantaj = [(x - ort) / (std + 1e-8) for x in oduller]
fark = -1.8 - (-1.2)
print("Avantajlar:", avantaj)
print("Naif log farkı:", round(-fark, 4), "| Schulman KL:", round(math.expm1(fark) - fark, 4))
```
???
```cikti
Avantajlar: [0.0, 0.0, 0.0, 0.0]
Naif log farkı: 0.6 | Schulman KL: 0.1488
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: tüm ödüller `1.0` (tam başarı) olsa bile avantajların `[0.0, 0.0, 0.0, 0.0]` çıkması gradyan güncellemesi için ne anlama gelir? Sonra üç kusurlu başlangıç kodunu çalıştır ve her birinin neyi kaçırdığını önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · Grup içi bağıl avantaj normalizasyonu
`grup_avantaji(oduller, eps)`: `oduller` en az 2 elemanlı `list`, elemanları bool olmayan sonlu sayı (`int` veya `float`); `eps` bool olmayan sonlu sayı ve `eps > 0`. Grup ortalaması $\mu = \frac{1}{G}\sum r_i$ ve popülasyon standart sapması $\sigma = \sqrt{\frac{1}{G}\sum (r_i - \mu)^2}$ ile her eleman için $(r_i - \mu) / (\sigma + \text{eps})$ değerini içeren yeni bir `list` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-26")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def grup_avantaji(oduller, eps):
    ort = sum(oduller) / len(oduller)
    return [x - ort for x in oduller]

from ai_temel_veri import json_yukle
v = json_yukle("veri/grpo.json")
for g in v["gruplar"]:
    print(g["ad"], [round(a, 4) for a in grup_avantaji(g["oduller"], v["eps"])])
```
```test
def sinama1(f):
    import math, random
    def _r(od, e):
        n = len(od); m = sum(od) / n
        s = math.sqrt(sum((x - m) ** 2 for x in od) / n)
        return [(x - m) / (s + e) for x in od]
    def _y(a, b):
        return len(a) == len(b) and all(abs(p - q) < 1e-12 for p, q in zip(a, b))
    try:
        od = [1.0, -1.0, 1.0, -1.0]; old = list(od)
        c = f(od, 1e-8)
        if not _y(c, _r(od, 1e-8)) or od != old: return False
        if f([5.0, 5.0, 5.0], 1e-6) != [0.0, 0.0, 0.0]: return False
        if not _y(f([0.0, 10.0], 0.5), [-5.0 / 5.5, 5.0 / 5.5]): return False
        rng = random.Random(26)
        for _ in range(25):
            k = [rng.uniform(-10, 10) for _ in range(rng.randint(2, 9))]
            ep = rng.uniform(1e-8, 0.1)
            if not _y(f(list(k), ep), _r(k, ep)): return False
        for bad in (
            (None, 1e-8), ([], 1e-8), ([1.0], 1e-8), ((1.0, 2.0), 1e-8),
            ([True, 1.0], 1e-8), ([float("nan"), 1.0], 1e-8), ([float("inf"), 1.0], 1e-8),
            ([1.0, 2.0], 0.0), ([1.0, 2.0], -1e-5), ([1.0, 2.0], True),
            ([1.0, 2.0], float("nan")), ([1.0, 2.0], "1e-8")
        ):
            try:
                f(*bad)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sinama1(grup_avantaji), "grup ortalaması, popülasyon std normalizasyonu ve geçersiz girdi")
for ad, mut in [
    ("std bölmesi yok", lambda od, e: [x - sum(od) / len(od) for x in od]),
    ("örneklem std (n-1)", lambda od, e: [(x - sum(od) / len(od)) / (math.sqrt(sum((v - sum(od) / len(od)) ** 2 for v in od) / (len(od) - 1)) + e) for x in od]),
    ("işaret ters", lambda od, e: [-v for v in grup_avantaji(od, e)])
]:
    ok(not sinama1(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(grup_avantaji, _il.import_module('ai_gercek_ai_temel_26').referans_grup_avantaji, ([1.0, 0.0, 1.0, 0.2, -0.5, 0.8], 1e-08), tohum=2318)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def grup_avantaji(oduller, eps):
    if not isinstance(oduller, list) or len(oduller) < 2:
        raise ValueError("oduller")
    for x in oduller:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
            raise ValueError("sayi")
    if isinstance(eps, bool) or not isinstance(eps, (int, float)) or not math.isfinite(eps) or eps <= 0:
        raise ValueError("eps")
    n = len(oduller)
    ort = sum(oduller) / n
    std = math.sqrt(sum((x - ort) ** 2 for x in oduller) / n)
    payda = std + eps
    return [(x - ort) / payda for x in oduller]

from ai_temel_veri import json_yukle
v = json_yukle("veri/grpo.json")
for g in v["gruplar"]:
    print(g["ad"], [round(a, 4) for a in grup_avantaji(g["oduller"], v["eps"])])
```
```hint
Popülasyon standart sapmasında kareler toplamını `len(oduller)` değerine böl, karekökünü al ve bölme öncesinde `eps` ekle.
```
:::

::: anlat Negatif olmayan KL sapma cezası
Her örnek için yeni politikanın log-olasılığı `logp_yeni[i]` ve referans modelin log-olasılığı `logp_ref[i]` verilir (`<= 0`).
Schulman `KL divergence` tahmincisi:
$$\Delta_i = \text{logp\_ref}[i] - \text{logp\_yeni}[i]$$
$$d_i = \exp(\Delta_i) - \Delta_i - 1$$
$\exp(x) \ge 1 + x$ eşitsizliği gereği her gerçek $\Delta_i$ için $d_i \ge 0$ olur ve yalnızca `logp_yeni[i] == logp_ref[i]` olduğunda tam `0.0` değerini alır.

**Görev 2'de sık tuzaklar:** Farkın yönünü ters almak (`logp_yeni - logp_ref`) veya pozitif log-olasılıkları (`> 0`) geçerli kabul etmek.
:::

::: gorev 2 · Schulman KL sapma cezası
`kl_sapma_cezasi(logp_yeni, logp_ref)`: `logp_yeni` ve `logp_ref` aynı uzunlukta, boş olmayan `list`; her eleman bool olmayan sonlu sayı ve `<= 0` (geçerli log-olasılık). Her konum için $\Delta_i = \text{logp\_ref}[i] - \text{logp\_yeni}[i]$ üzerinden $\exp(\Delta_i) - \Delta_i - 1$ değerini içeren yeni bir `list` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-26")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def kl_sapma_cezasi(logp_yeni, logp_ref):
    return [yn - rf for yn, rf in zip(logp_yeni, logp_ref)]

from ai_temel_veri import json_yukle
v = json_yukle("veri/grpo.json")
for g in v["gruplar"]:
    print(g["ad"], [round(k, 4) for k in kl_sapma_cezasi(g["logp_yeni"], g["logp_ref"])])
```
```test
def sinama2(f):
    import math, random
    def _r(yn, rf):
        return [math.exp(b - a) - (b - a) - 1.0 for a, b in zip(yn, rf)]
    def _y(a, b):
        return len(a) == len(b) and all(abs(p - q) < 1e-12 for p, q in zip(a, b))
    try:
        yn = [-1.0, -2.0, -0.5]; rf = [-1.0, -1.0, -1.5]; old = (list(yn), list(rf))
        c = f(yn, rf)
        if not _y(c, _r(yn, rf)) or (yn, rf) != old: return False
        if c[0] != 0.0 or any(v < 0 for v in c): return False
        if not _y(f([0.0], [0.0]), [0.0]): return False
        rng = random.Random(2626)
        for _ in range(25):
            n = rng.randint(1, 8)
            a = [rng.uniform(-10, 0) for _ in range(n)]
            b = [rng.uniform(-10, 0) for _ in range(n)]
            if not _y(f(list(a), list(b)), _r(a, b)): return False
        for bad in (
            (None, [-1.0]), ([-1.0], None), ([], []), ([-1.0], [-1.0, -2.0]),
            ((-1.0,), [-1.0]), ([-1.0], (-1.0,)), ([0.1], [-1.0]), ([-1.0], [0.01]),
            ([True], [-1.0]), ([-1.0], [float("nan")]), ([float("-inf")], [-1.0]),
            *[(k, [-1.0]) for k in ([False], ["a"], [float("nan")], [float("inf")], [0.5])],
            *[([-1.0], k) for k in ([True], ["a"], [float("-inf")], [float("inf")], [0.5])]
        ):
            try:
                f(*bad)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
_kl_yakin = kl_sapma_cezasi([-1e-8, 0.0], [0.0, -1e-8])
ok(all(4.99999e-17 < v < 5.00001e-17 for v in _kl_yakin),
   "Sıfıra yakın farklarda ikinci dereceden pozitif ceza korunur")
ok(sinama2(kl_sapma_cezasi), "negatif olmayan KL tahmincisi, yön duyarlılığı ve geçersiz girdi")
for ad, mut in [
    ("ters fark yönü", lambda yn, rf: [math.exp(a - b) - (a - b) - 1.0 for a, b in zip(yn, rf)]),
    ("naif fark", lambda yn, rf: [a - b for a, b in zip(yn, rf)]),
    ("sabit sıfır", lambda yn, rf: [0.0 for _ in yn])
]:
    ok(not sinama2(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(kl_sapma_cezasi, _il.import_module('ai_gercek_ai_temel_26').referans_kl_sapma, ([-1.0, -2.3, -1.1, -1.7, -2.6, -1.2], [-1.3, -1.9, -1.6, -1.8, -2.2, -1.4]), tohum=2505)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def kl_sapma_cezasi(logp_yeni, logp_ref):
    if not isinstance(logp_yeni, list) or not isinstance(logp_ref, list) or not logp_yeni or len(logp_yeni) != len(logp_ref):
        raise ValueError("boyut")
    for a, b in zip(logp_yeni, logp_ref):
        if isinstance(a, bool) or not isinstance(a, (int, float)) or not math.isfinite(a) or a > 0:
            raise ValueError("logp_yeni")
        if isinstance(b, bool) or not isinstance(b, (int, float)) or not math.isfinite(b) or b > 0:
            raise ValueError("logp_ref")
    sonuc = []
    for yn, rf in zip(logp_yeni, logp_ref):
        fark = rf - yn
        sonuc.append(math.expm1(fark) - fark)
    return sonuc

from ai_temel_veri import json_yukle
v = json_yukle("veri/grpo.json")
for g in v["gruplar"]:
    print(g["ad"], [round(k, 4) for k in kl_sapma_cezasi(g["logp_yeni"], g["logp_ref"])])
```
```hint
Her iki listede de elemanların `<= 0` olduğunu denetle ve `fark = rf - yn` üzerinden `math.expm1(fark) - fark` hesapla.
```
:::

::: anlat Kırpılmış GRPO kaybı ve ifade çökmesi
Grup içindeki her örnek $i$ için:
- Olasılık oranı $\rho_i = \exp(\text{logp\_yeni}[i] - \text{logp\_eski}[i])$
- Kırpılmış oran $\tilde{\rho}_i = \min(\max(\rho_i, 1 - \text{clip\_eps}), 1 + \text{clip\_eps})$
- Vekil terim $s_i = \min(\rho_i A_i, \tilde{\rho}_i A_i)$
- Eğer $|\rho_i - \tilde{\rho}_i| > 10^{-12}$ ise bu örnek kırpılmış sayılır.

Grup özeti:
- `vekil_hedef`: $\frac{1}{G}\sum s_i$
- `ortalama_kl`: $\frac{1}{G}\sum d_i$
- `kayip`: $-(\text{vekil\_hedef} - \text{beta} \cdot \text{ortalama\_kl})$
- `kirpilma_orani`: kırpılan örnek sayısının $G$'ye oranı
- `ifade_cokmesi`: `max(oduller) - min(oduller) <= 1e-12` ise `True`, değilse `False`.

**Görev 3'te sık tuzaklar:** Negatif avantajlı ($A_i < 0$) örneklerde $\min(\rho_i A_i, \tilde{\rho}_i A_i)$ yerine doğrudan kırpılmış oranı çarpmak (negatif avantajda $\rho_i > 1 + \text{clip\_eps}$ iken $\rho_i A_i < \tilde{\rho}_i A_i$ olur; `min` karamsar alt sınırı seçer!).
:::

::: gorev 3 · GRPO kayıp ve tanı raporu
`grpo_kayip_raporu(logp_yeni, logp_eski, logp_ref, oduller, clip_eps, beta, eps)`: `logp_yeni`, `logp_eski`, `logp_ref` aynı uzunlukta (`G >= 2`) ve `<= 0` sonlu sayı listeleri; `oduller` aynı uzunlukta (`G >= 2`) sonlu sayı listesi; `clip_eps > 0`, `beta >= 0`, `eps > 0` bool olmayan sonlu sayılar. Yukarıdaki formülle `{"kayip": float, "vekil_hedef": float, "ortalama_kl": float, "kirpilma_orani": float, "ifade_cokmesi": bool}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-26")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def grpo_kayip_raporu(logp_yeni, logp_eski, logp_ref, oduller, clip_eps, beta, eps):
    n = len(oduller)
    ort = sum(oduller) / n
    std = math.sqrt(sum((x - ort) ** 2 for x in oduller) / n)
    av = [(x - ort) / (std + eps) for x in oduller]
    vekil = sum(math.exp(yn - es) * a for yn, es, a in zip(logp_yeni, logp_eski, av)) / n
    ort_kl = sum(yn - rf for yn, rf in zip(logp_yeni, logp_ref)) / n
    return {
        "kayip": -(vekil - beta * ort_kl),
        "vekil_hedef": vekil,
        "ortalama_kl": ort_kl,
        "kirpilma_orani": 0.0,
        "ifade_cokmesi": False,
    }

from ai_temel_veri import json_yukle
v = json_yukle("veri/grpo.json")
for g in v["gruplar"]:
    print(g["ad"], grpo_kayip_raporu(g["logp_yeni"], g["logp_eski"], g["logp_ref"], g["oduller"], v["clip_eps"], v["beta"], v["eps"]))
```
```test
def sinama3(f):
    import math, random
    def _r(yn, es, rf, od, ce, bt, ep):
        n = len(od); m = sum(od) / n; s = math.sqrt(sum((x - m) ** 2 for x in od) / n)
        av = [(x - m) / (s + ep) for x in od]
        kl = [math.exp(b - a) - (b - a) - 1.0 for a, b in zip(yn, rf)]
        vt = 0.0; kr = 0
        for a, b, v in zip(yn, es, av):
            o = math.exp(a - b); ko = min(max(o, 1.0 - ce), 1.0 + ce)
            if abs(o - ko) > 1e-12: kr += 1
            vt += min(o * v, ko * v)
        vh = vt / n; ok_kl = sum(kl) / n
        return {"kayip": -(vh - bt * ok_kl), "vekil_hedef": vh, "ortalama_kl": ok_kl, "kirpilma_orani": kr / n, "ifade_cokmesi": bool(max(od) - min(od) <= 1e-12)}
    def _y(a, b):
        return set(a) == set(b) and a["ifade_cokmesi"] is b["ifade_cokmesi"] and all(abs(a[k] - b[k]) < 1e-12 for k in ("kayip", "vekil_hedef", "ortalama_kl", "kirpilma_orani"))
    try:
        yn = [-1.0, -3.0]; es = [-2.0, -2.0]; rf = [-1.5, -2.5]; od = [1.0, 0.0]
        old = (list(yn), list(es), list(rf), list(od))
        c = f(yn, es, rf, od, 0.2, 0.05, 1e-8)
        if not _y(c, _r(yn, es, rf, od, 0.2, 0.05, 1e-8)) or (yn, es, rf, od) != old: return False
        if c["kirpilma_orani"] != 1.0 or c["ifade_cokmesi"] is not False: return False
        c2 = f([-1.0, -0.5], [-1.0, -2.0], [-1.0, -1.0], [1.0, 0.0], 0.2, 0.1, 1e-8)
        if not _y(c2, _r([-1.0, -0.5], [-1.0, -2.0], [-1.0, -1.0], [1.0, 0.0], 0.2, 0.1, 1e-8)): return False
        c3 = f([-1.0, -2.0], [-1.0, -2.0], [-1.0, -2.0], [2.0, 2.0], 0.2, 0.05, 1e-8)
        if c3["ifade_cokmesi"] is not True or c3["vekil_hedef"] != 0.0: return False
        rng = random.Random(2603)
        for _ in range(25):
            n = rng.randint(2, 7)
            y_v = [rng.uniform(-5, 0) for _ in range(n)]
            e_v = [rng.uniform(-5, 0) for _ in range(n)]
            r_v = [rng.uniform(-5, 0) for _ in range(n)]
            o_v = [rng.uniform(-2, 2) for _ in range(n)]
            if not _y(f(list(y_v), list(e_v), list(r_v), list(o_v), 0.2, 0.04, 1e-8), _r(y_v, e_v, r_v, o_v, 0.2, 0.04, 1e-8)): return False
        B = ([-1.0, -1.0], [-1.0, -1.0], [-1.0, -1.0], [1.0, 0.0], 0.2, 0.04, 1e-8)
        def deg(i, v):
            x = list(B); x[i] = v; return tuple(x)
        for b0 in (deg(5, 0.0), ([0.0, -1.0], [0.0, -1.0], [0.0, -1.0], [1.0, 0.0], 0.2, 0.04, 1e-8), deg(3, [0.0, 1e-12])):
            if not _y(f(*b0), _r(*b0)): return False
        if f(*deg(3, [0.0, 1e-12]))["ifade_cokmesi"] is not True: return False
        kotu = [([-1.0], [-1.0], [-1.0], [1.0], 0.2, 0.04, 1e-8), deg(3, [1.0]), deg(3, (1.0, 0.0)), deg(3, None), deg(3, [True, 0.0]), deg(3, ["a", 0.0]), deg(3, [float("nan"), 0.0]), deg(3, [float("inf"), 0.0])]
        for i in range(3):
            kotu += [deg(i, (-1.0, -1.0)), deg(i, None), deg(i, [-1.0]), deg(i, [True, -1.0]), deg(i, ["a", -1.0]), deg(i, [float("nan"), -1.0]), deg(i, [float("-inf"), -1.0]), deg(i, [0.5, -1.0])]
        for i, vs in ((4, (0.0, -0.1, True, float("nan"), "0.2")), (5, (-0.01, True, float("inf"), "0")), (6, (0.0, -1e-8, True, float("nan")))):
            kotu += [deg(i, v) for v in vs]
        for bad in kotu:
            try:
                f(*bad)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sinama3(grpo_kayip_raporu), "PPO/GRPO kırpma, negatif avantaj min, KL cezası ve ifade çökmesi")
for ad, mut in [
    ("kırpma yok", lambda yn, es, rf, od, ce, bt, ep: dict(grpo_kayip_raporu(yn, es, rf, od, ce, bt, ep), kirpilma_orani=0.0)),
    ("kayıp işaret ters", lambda yn, es, rf, od, ce, bt, ep: dict(grpo_kayip_raporu(yn, es, rf, od, ce, bt, ep), kayip=-grpo_kayip_raporu(yn, es, rf, od, ce, bt, ep)["kayip"])),
    ("çökme hep yanlış", lambda yn, es, rf, od, ce, bt, ep: dict(grpo_kayip_raporu(yn, es, rf, od, ce, bt, ep), ifade_cokmesi=False))
]:
    ok(not sinama3(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(grpo_kayip_raporu, _il.import_module('ai_gercek_ai_temel_26').referans_grpo_rapor, ([-1.0, -2.3, -1.1, -1.7, -2.6, -1.2], [-1.2, -2.0, -1.5, -1.8, -2.4, -1.3], [-1.3, -1.9, -1.6, -1.8, -2.2, -1.4], [1.0, 0.0, 1.0, 0.2, -0.5, 0.8], 0.2, 0.04, 1e-08), tohum=2768)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def grpo_kayip_raporu(logp_yeni, logp_eski, logp_ref, oduller, clip_eps, beta, eps):
    if not isinstance(oduller, list) or len(oduller) < 2:
        raise ValueError("oduller")
    n = len(oduller)
    if not isinstance(logp_yeni, list) or not isinstance(logp_eski, list) or not isinstance(logp_ref, list):
        raise ValueError("liste")
    if len(logp_yeni) != n or len(logp_eski) != n or len(logp_ref) != n:
        raise ValueError("boyut")
    for x in oduller:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
            raise ValueError("odul_sayi")
    for lst in (logp_yeni, logp_eski, logp_ref):
        for x in lst:
            if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or x > 0:
                raise ValueError("logp_sayi")
    for v in (clip_eps, beta, eps):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError("ayar_sayi")
    if clip_eps <= 0 or beta < 0 or eps <= 0:
        raise ValueError("ayar_sinir")
    ort = sum(oduller) / n
    std = math.sqrt(sum((x - ort) ** 2 for x in oduller) / n)
    avantajlar = [(x - ort) / (std + eps) for x in oduller]
    kl_liste = [math.exp(rf - yn) - (rf - yn) - 1.0 for yn, rf in zip(logp_yeni, logp_ref)]
    vekil_top = 0.0
    kirpilan = 0
    for yn, es, av in zip(logp_yeni, logp_eski, avantajlar):
        oran = math.exp(yn - es)
        k_oran = min(max(oran, 1.0 - clip_eps), 1.0 + clip_eps)
        if abs(oran - k_oran) > 1e-12:
            kirpilan += 1
        vekil_top += min(oran * av, k_oran * av)
    vekil_hedef = vekil_top / n
    ort_kl = sum(kl_liste) / n
    kayip = -(vekil_hedef - beta * ort_kl)
    cokme = bool(max(oduller) - min(oduller) <= 1e-12)
    return {
        "kayip": kayip,
        "vekil_hedef": vekil_hedef,
        "ortalama_kl": ort_kl,
        "kirpilma_orani": kirpilan / n,
        "ifade_cokmesi": cokme,
    }

from ai_temel_veri import json_yukle
v = json_yukle("veri/grpo.json")
for g in v["gruplar"]:
    print(g["ad"], grpo_kayip_raporu(g["logp_yeni"], g["logp_eski"], g["logp_ref"], g["oduller"], v["clip_eps"], v["beta"], v["eps"]))
```
```hint
Her örnekte `min(oran * av, k_oran * av)` ifadesini topla ve ortalamasını al. `kayip` değeri `-(vekil_hedef - beta * ort_kl)` olmalıdır.
```
:::

::: anlat Hata vitrini · çalışmış yanlış rapor
Yazar, kusurlu başlangıç kodlarını görünür sentetik veriyle gerçekten çalıştırdı ve sonucu `outputs/yeni-ai-temel-26/gorunur-run-1.json` dosyasına kaydetti. `asiri_adim_grubu` için kusurlu kod `ortalama_kl=-0.025`, `kirpilma_orani=0.0`, `vekil_hedef=0.5835` verirken; doğru kod `ortalama_kl=0.2315`, `kirpilma_orani=1.0`, `vekil_hedef=-0.0056` verir.

Bu kaydedilmiş bir hesaplama çıktısıdır, model yanıtı değildir ve rapor sentetiktir. Kusurlu çıktıda `ortalama_kl` değerinin negatif çıkması ve kırpılmamış büyük oranların `vekil_hedef`'i şişirmesi politikayı nasıl bozar? Kendi cümlenle açıkla. Gerçek finaldeki ölçüm ayrıca üretilir; bu sayılar onun yerine konmaz.
:::

::: anlat Gerçek deney: SmolLM2-135M'de doğrulanabilir ödülle GRPO
Final gerçek bir dil modelini GRPO ile eğitir. Görev, ödülü kandırılamayan (verifiable reward) küçük bir sınavdır: `3, 7, 11, 15,` gibi bir aritmetik dizinin sonraki terimini yazmak. Ödül, modelin ürettiği ilk sayı doğruysa `1.0`, değilse `0.0`'dır. 45 olası sorudan 16'sı eğitim, 12'si hiç görülmeyen ayrık test sorusudur.

Her turda politika, her eğitim sorusu için sıcaklık 1.0 ile $G = 8$ tamamlama (3'er token) örnekler. Her tamamlamanın **dizi düzeyindeki** log-olasılığı üç modelde hesaplanır:
- güncel politika (`logp_eski`, örnekleme anındaki politika),
- donmuş referans model (`logp_ref`, eğitim başındaki SmolLM2),
- güncellenen politika (`logp_yeni`).

Grup içi avantaj, kırpılmış oran ve $k_3$ KL cezasıyla 2 Adam adımı atılır. Toplam 4 tur, 8 adım yapılır; tam ince ayar, lr $2 \cdot 10^{-5}$. Son turun 16 grubunda **senin `grup_avantaji`, `kl_sapma_cezasi` ve `grpo_kayip_raporu` işlevlerin** gerçek ödül ve log-olasılıklarla çalışır ve bağımsız referansla karşılaştırılır.

Yazarın bir GPU koşusunda (yaklaşık 35 sn) şu sonuçlar alındı:
- **Eğitim ödülü:** Tur başına ortalama 0.26 → 0.48 → 0.75 → 0.81.
- **Ayrık test:** Doğru cevabın ortalama olasılığı 0.16 → 0.62, açgözlü doğruluk 0.42 → 0.75. Bu, değer ağı (critic) olmadan, yalnız grup içi karşılaştırmayla elde edildi.

**İfade çökmesi gerçek veride kendiliğinden görüldü.** Ödülü tamamen eşit (hepsi 0 ya da hepsi 1) grup sayısı turlarda 3 → 2 → 7 → 8 oldu. Model iyileştikçe kolay soruların bütün grubu doğru cevap verir. Avantajlar sıfırlanır ve o sorular artık hiçbir şey öğretmez. DAPO'nun "dinamik örnekleme" (eşit ödüllü grupları atıp yeniden örnekleme) önerisi tam bu soruna yöneliktir.

Dizi düzeyindeki KL değerleri de büyüktür (bir grupta ortalama ~5.9 nat). 8 adımlık tam ince ayar, referanstan ciddi ölçüde uzaklaşır; $\beta = 0.04$ bu hızda zayıf bir frendir.

**Kanıt dosyasını oku:** Soru 1: `tur_cokmus_grup` artarken etkili eğitim verisi neden küçülüyor? Bu durumda grup boyutunu büyütmek mi, soruları zorlaştırmak mı daha iyi? Soru 2: Bir grupta `kirpilma_orani > 0` iken `vekil_hedef` neden kırpılmamış hâlinden küçük kalır? Cevabını tezgâhta yorum olarak yaz; otomatik test bu serbest açıklamayı puanlamaz.
:::

::: gorev Gerçek deney · GPU üzerinde grup rollout'larıyla GRPO politika optimizasyonu
Önceki üç görevin `grup_avantaji`, `kl_sapma_cezasi` ve `grpo_kayip_raporu` işlevlerini birleştir. Çalıştır gerçek tabloyu gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 180
```
```starter
import ai_lab
import math
def grup_avantaji(oduller, eps):
    ort = sum(oduller) / len(oduller)
    return [x - ort for x in oduller]
def kl_sapma_cezasi(logp_yeni, logp_ref):
    return [yn - rf for yn, rf in zip(logp_yeni, logp_ref)]
def grpo_kayip_raporu(logp_yeni, logp_eski, logp_ref, oduller, clip_eps, beta, eps):
    av = grup_avantaji(oduller, eps)
    n = len(oduller)
    vekil = sum(math.exp(yn - es) * a for yn, es, a in zip(logp_yeni, logp_eski, av)) / n
    ort_kl = sum(kl_sapma_cezasi(logp_yeni, logp_ref)) / n
    return {"kayip": -(vekil - beta * ort_kl), "vekil_hedef": vekil, "ortalama_kl": ort_kl, "kirpilma_orani": 0.0, "ifade_cokmesi": False}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_26 as D
    D.goster(grup_avantaji, kl_sapma_cezasi, grpo_kayip_raporu)
```
```test
import ai_lab, math
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('referans_grup_avantaji', 'referans_kl_sapma', 'referans_grpo_rapor', 'kanit_yaz', '_yakin'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
grup_avantaji = need("grup_avantaji")
kl_sapma_cezasi = need("kl_sapma_cezasi")
grpo_kayip_raporu = need("grpo_kayip_raporu")
def sinama1(f):
    import math, random
    def _r(od, e):
        n = len(od); m = sum(od) / n; s = math.sqrt(sum((x - m) ** 2 for x in od) / n)
        return [(x - m) / (s + e) for x in od]
    def _y(a, b): return len(a) == len(b) and all(abs(p - q) < 1e-12 for p, q in zip(a, b))
    try:
        od = [1.0, -1.0, 1.0, -1.0]; old = list(od)
        if not _y(f(od, 1e-8), _r(od, 1e-8)) or od != old: return False
        if f([5.0, 5.0, 5.0], 1e-6) != [0.0, 0.0, 0.0]: return False
        rng = random.Random(26)
        for _ in range(25):
            k = [rng.uniform(-10, 10) for _ in range(rng.randint(2, 9))]; ep = rng.uniform(1e-8, 0.1)
            if not _y(f(list(k), ep), _r(k, ep)): return False
        for bad in ((None, 1e-8), ([], 1e-8), ([1.0], 1e-8), ((1.0, 2.0), 1e-8), ([True, 1.0], 1e-8), ([float("nan"), 1.0], 1e-8), ([float("inf"), 1.0], 1e-8), ([1.0, 2.0], 0.0), ([1.0, 2.0], -1e-5), ([1.0, 2.0], True), ([1.0, 2.0], float("nan")), ([1.0, 2.0], "1e-8")):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama1(grup_avantaji), "grup ortalaması, popülasyon std normalizasyonu ve geçersiz girdi")
for ad, mut in [("std bölmesi yok", lambda od, e: [x - sum(od) / len(od) for x in od]), ("örneklem std (n-1)", lambda od, e: [(x - sum(od) / len(od)) / (math.sqrt(sum((v - sum(od) / len(od)) ** 2 for v in od) / (len(od) - 1)) + e) for x in od]), ("işaret ters", lambda od, e: [-v for v in grup_avantaji(od, e)])]:
    kontrol(not sinama1(mut), "mutant reddedildi: " + ad)
def sinama2(f):
    import math, random
    def _r(yn, rf): return [math.exp(b - a) - (b - a) - 1.0 for a, b in zip(yn, rf)]
    def _y(a, b): return len(a) == len(b) and all(abs(p - q) < 1e-12 for p, q in zip(a, b))
    try:
        yn = [-1.0, -2.0, -0.5]; rf = [-1.0, -1.0, -1.5]; old = (list(yn), list(rf))
        c = f(yn, rf)
        if not _y(c, _r(yn, rf)) or (yn, rf) != old or c[0] != 0.0 or any(v < 0 for v in c): return False
        rng = random.Random(2626)
        for _ in range(25):
            n = rng.randint(1, 8); a = [rng.uniform(-10, 0) for _ in range(n)]; b = [rng.uniform(-10, 0) for _ in range(n)]
            if not _y(f(list(a), list(b)), _r(a, b)): return False
        for bad in ((None, [-1.0]), ([-1.0], None), ([], []), ([-1.0], [-1.0, -2.0]), ((-1.0,), [-1.0]), ([-1.0], (-1.0,)), ([0.1], [-1.0]), ([-1.0], [0.01]), ([True], [-1.0]), ([-1.0], [float("nan")]), ([float("-inf")], [-1.0])):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama2(kl_sapma_cezasi), "negatif olmayan KL tahmincisi, yön duyarlılığı ve geçersiz girdi")
for ad, mut in [("ters fark yönü", lambda yn, rf: [math.exp(a - b) - (a - b) - 1.0 for a, b in zip(yn, rf)]), ("naif fark", lambda yn, rf: [a - b for a, b in zip(yn, rf)]), ("sabit sıfır", lambda yn, rf: [0.0 for _ in yn])]:
    kontrol(not sinama2(mut), "mutant reddedildi: " + ad)
def sinama3(f):
    import math, random
    def _r(yn, es, rf, od, ce, bt, ep):
        n = len(od); m = sum(od) / n; s = math.sqrt(sum((x - m) ** 2 for x in od) / n); av = [(x - m) / (s + ep) for x in od]
        kl = [math.exp(b - a) - (b - a) - 1.0 for a, b in zip(yn, rf)]; vt = 0.0; kr = 0
        for a, b, v in zip(yn, es, av):
            o = math.exp(a - b); ko = min(max(o, 1.0 - ce), 1.0 + ce)
            if abs(o - ko) > 1e-12: kr += 1
            vt += min(o * v, ko * v)
        vh = vt / n; ok_kl = sum(kl) / n
        return {"kayip": -(vh - bt * ok_kl), "vekil_hedef": vh, "ortalama_kl": ok_kl, "kirpilma_orani": kr / n, "ifade_cokmesi": bool(max(od) - min(od) <= 1e-12)}
    def _y(a, b): return set(a) == set(b) and a["ifade_cokmesi"] is b["ifade_cokmesi"] and all(abs(a[k] - b[k]) < 1e-12 for k in ("kayip", "vekil_hedef", "ortalama_kl", "kirpilma_orani"))
    try:
        yn = [-1.0, -3.0]; es = [-2.0, -2.0]; rf = [-1.5, -2.5]; od = [1.0, 0.0]; old = (list(yn), list(es), list(rf), list(od))
        c = f(yn, es, rf, od, 0.2, 0.05, 1e-8)
        if not _y(c, _r(yn, es, rf, od, 0.2, 0.05, 1e-8)) or (yn, es, rf, od) != old: return False
        c3 = f([-1.0, -2.0], [-1.0, -2.0], [-1.0, -2.0], [2.0, 2.0], 0.2, 0.05, 1e-8)
        if c3["ifade_cokmesi"] is not True or c3["vekil_hedef"] != 0.0: return False
        rng = random.Random(2603)
        for _ in range(25):
            n = rng.randint(2, 7); y_v = [rng.uniform(-5, 0) for _ in range(n)]; e_v = [rng.uniform(-5, 0) for _ in range(n)]; r_v = [rng.uniform(-5, 0) for _ in range(n)]; o_v = [rng.uniform(-2, 2) for _ in range(n)]
            if not _y(f(list(y_v), list(e_v), list(r_v), list(o_v), 0.2, 0.04, 1e-8), _r(y_v, e_v, r_v, o_v, 0.2, 0.04, 1e-8)): return False
        for bad in (([-1.0], [-1.0], [-1.0], [1.0], 0.2, 0.04, 1e-8), ([-1.0, -1.0, -1.0], [-1.0, -1.0], [-1.0, -1.0, -1.0], [1.0, 0.0], 0.2, 0.04, 1e-8), ([-1.0, -1.0], [-1.0], [-1.0, -1.0], [1.0, 0.0], 0.2, 0.04, 1e-8), ([-1.0, 0.5], [-1.0, -1.0], [-1.0, -1.0], [1.0, 0.0], 0.2, 0.04, 1e-8), ([-1.0, -1.0], [-1.0, 0.2], [-1.0, -1.0], [1.0, 0.0], 0.2, 0.04, 1e-8), ([-1.0, -1.0], [-1.0, -1.0], [-1.0, -1.0], [1.0, 0.0], 0.0, 0.04, 1e-8), ([-1.0, -1.0], [-1.0, -1.0], [-1.0, -1.0], [1.0, 0.0], 0.2, -0.01, 1e-8), ([-1.0, -1.0], [-1.0, -1.0], [-1.0, -1.0], [1.0, 0.0], True, 0.04, 1e-8)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama3(grpo_kayip_raporu), "PPO/GRPO kırpma, negatif avantaj min, KL cezası ve ifade çökmesi")
for ad, mut in [("kırpma yok", lambda yn, es, rf, od, ce, bt, ep: dict(grpo_kayip_raporu(yn, es, rf, od, ce, bt, ep), kirpilma_orani=0.0)), ("kayıp işaret ters", lambda yn, es, rf, od, ce, bt, ep: dict(grpo_kayip_raporu(yn, es, rf, od, ce, bt, ep), kayip=-grpo_kayip_raporu(yn, es, rf, od, ce, bt, ep)["kayip"])), ("çökme hep yanlış", lambda yn, es, rf, od, ce, bt, ep: dict(grpo_kayip_raporu(yn, es, rf, od, ce, bt, ep), ifade_cokmesi=False))]:
    kontrol(not sinama3(mut), "mutant reddedildi: " + ad)
# farksal tarama (final)
import importlib as _il
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_R = _il.import_module('sandbox.ai_gercek_ai_temel_26')
for _ad, _ref, _taban, _toh in (
    ('grup_avantaji', 'referans_grup_avantaji', ([1.0, 0.0, 1.0, 0.2, -0.5, 0.8], 1e-08), 2840),
    ('kl_sapma_cezasi', 'referans_kl_sapma', ([-1.0, -2.3, -1.1, -1.7, -2.6, -1.2], [-1.3, -1.9, -1.6, -1.8, -2.2, -1.4]), 3027),
    ('grpo_kayip_raporu', 'referans_grpo_rapor', ([-1.0, -2.3, -1.1, -1.7, -2.6, -1.2], [-1.2, -2.0, -1.5, -1.8, -2.4, -1.3], [-1.3, -1.9, -1.6, -1.8, -2.2, -1.4], [1.0, 0.0, 1.0, 0.2, -0.5, 0.8], 0.2, 0.04, 1e-08), 3290),
):
    _t, _g = _ff(need(_ad), getattr(_R, _ref), _taban, tohum=_toh)
    kontrol(_t, "farksal tarama (" + _ad + "): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
if not all(checks): stop()
from sandbox import ai_gercek_ai_temel_26 as D
try: r = D.deney(grup_avantaji, kl_sapma_cezasi, grpo_kayip_raporu)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r["avantaj_ayni"], "SmolLM2 rollout'larının 16 grubunda avantaj normalizasyonu bağımsız referansla aynı")
kontrol(r["kl_ayni"], "16 grupta gerçek log-olasılıklarla Schulman KL cezası referansla aynı")
kontrol(r["rapor_ayni"], "16 grupta GRPO kayıp raporu referansla aynı")
kontrol(r["kl_negatif_yok"], "bütün örneklerde KL sapma cezası >= 0")
kontrol(r["avantaj_sifir_ort"], "bütün gruplarda avantajların toplamı 0.0")
kontrol(r["tur_ortalama_odul"][-1] > r["tur_ortalama_odul"][0], "eğitim rollout'larının ortalama ödülü arttı: " + str([round(x, 3) for x in r["tur_ortalama_odul"]]))
kontrol(r["politika_iyilesti"], "görülmemiş sorularda doğru cevabın olasılığı arttı: %.3f -> %.3f" % (r["once_hedef_olasilik"], r["sonra_hedef_olasilik"]))
kontrol(sum(r["tur_cokmus_grup"]) > 0, "gerçek rollout'larda ödülü tamamen eşit (sinyalsiz) gruplar ölçüldü: " + str(r["tur_cokmus_grup"]))
ai_lab.kanit_yaz("ai-temel-26-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-temel-26", "deney": r})
```
```solution
import ai_lab
import math
def grup_avantaji(oduller, eps):
    if not isinstance(oduller, list) or len(oduller) < 2:
        raise ValueError("oduller")
    for x in oduller:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
            raise ValueError("sayi")
    if isinstance(eps, bool) or not isinstance(eps, (int, float)) or not math.isfinite(eps) or eps <= 0:
        raise ValueError("eps")
    n = len(oduller)
    ort = sum(oduller) / n
    std = math.sqrt(sum((x - ort) ** 2 for x in oduller) / n)
    payda = std + eps
    return [(x - ort) / payda for x in oduller]
def kl_sapma_cezasi(logp_yeni, logp_ref):
    if not isinstance(logp_yeni, list) or not isinstance(logp_ref, list) or not logp_yeni or len(logp_yeni) != len(logp_ref):
        raise ValueError("boyut")
    for a, b in zip(logp_yeni, logp_ref):
        if isinstance(a, bool) or not isinstance(a, (int, float)) or not math.isfinite(a) or a > 0:
            raise ValueError("logp_yeni")
        if isinstance(b, bool) or not isinstance(b, (int, float)) or not math.isfinite(b) or b > 0:
            raise ValueError("logp_ref")
    sonuc = []
    for yn, rf in zip(logp_yeni, logp_ref):
        fark = rf - yn
        sonuc.append(math.expm1(fark) - fark)
    return sonuc
def grpo_kayip_raporu(logp_yeni, logp_eski, logp_ref, oduller, clip_eps, beta, eps):
    avantajlar = grup_avantaji(oduller, eps)
    kl_liste = kl_sapma_cezasi(logp_yeni, logp_ref)
    n = len(oduller)
    if not isinstance(logp_eski, list) or len(logp_eski) != n or len(logp_yeni) != n:
        raise ValueError("boyut")
    for x in logp_eski:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or x > 0:
            raise ValueError("logp_eski")
    for v in (clip_eps, beta):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError("ayar_sayi")
    if clip_eps <= 0 or beta < 0:
        raise ValueError("ayar_sinir")
    vekil_top = 0.0
    kirpilan = 0
    for yn, es, av in zip(logp_yeni, logp_eski, avantajlar):
        oran = math.exp(yn - es)
        k_oran = min(max(oran, 1.0 - clip_eps), 1.0 + clip_eps)
        if abs(oran - k_oran) > 1e-12:
            kirpilan += 1
        vekil_top += min(oran * av, k_oran * av)
    vekil_hedef = vekil_top / n
    ort_kl = sum(kl_liste) / n
    kayip = -(vekil_hedef - beta * ort_kl)
    cokme = bool(max(oduller) - min(oduller) <= 1e-12)
    return {
        "kayip": kayip,
        "vekil_hedef": vekil_hedef,
        "ortalama_kl": ort_kl,
        "kirpilma_orani": kirpilan / n,
        "ifade_cokmesi": cokme,
    }
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_26 as D
    D.goster(grup_avantaji, kl_sapma_cezasi, grpo_kayip_raporu)
```
```hint
`grpo_kayip_raporu` içinde `grup_avantaji` ve `kl_sapma_cezasi` işlevlerini çağırıp oran kırpma ve `ifade_cokmesi` kontrolünü ekle.
```
:::

::: anlat Sınır
Gerçek deney küçük bir modelde (135M) birkaç adımlık GRPO'dur ve tek tip, kısa cevaplı bir görev kullanır. Oran DeepSeekMath'teki gibi token düzeyinde değil, 3 tokenlık tamamlamanın dizi düzeyindeki log-olasılığıyla kurulur. Bu, GSPO'ya yakındır ve kısa cevapta fark küçüktür. Ayrık testteki iyileşme aynı dizi kalıbının yeni sayılarına genellemedir; genel akıl yürütme yeteneği ölçülmez. Çok adımlı uzun düşünce zincirlerinde (CoT) uzunluk yanlılığı (length bias, Dr. GRPO), ödül kandırma (reward hacking), süreç ödül modelleri (PRM) ve büyük ölçekli eğitim dinamikleri kapsanmaz.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Eleştirmen (`critic`) olmadan RL (`GRPO`) (30 sn).** "PPO'daki ikinci büyük değer ağını (`value network`) bellekten atıp aynı istem için üretilen $G$ tamamlamanın grup içi ortalama ve standart sapmasıyla bağıl avantaj $A_i = (r_i - \mu)/\sigma$ hesaplarız."
2. **Kırpılmış oran ve `expm1` KL cezası (35 sn).** "$\pi_\theta / \pi_{\text{eski}}$ oranını $[1-\epsilon, 1+\epsilon]$ aralığında kırpmak tek adımda aşırı güncellemeyi, $\text{expm1}(\Delta) - \Delta$ biçimindeki pozitif KL tahmincisi ise küçük farklarda kayan nokta sönümlenmesini önleyerek referanstan kopmayı engeller."
3. **Ödül korsanlığı (`reward hacking`) riski (30 sn).** "Doğrulanabilir kural ödülü eksik tanımlanırsa grup içi normalizasyon kısayol bulan hileli çıktılara da pozitif avantaj verir; SmolLM2 deneyinde kural açığı kapatılmadan yanlış biçimli yanıtlar ödül toplayabilir."
4. **Soru (25 sn).** "Gruptaki tüm tamamlamalar aynı ödülü aldığında ($\sigma = 0$) avantajların sıfırlanması eğitim adımında ne anlama gelir?"
:::
