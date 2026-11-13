---
id: ai-guvence-43
title: Model Merging (TIES / DARE) ve Hizalama Analizi · Görev Vektörü Çatışması
summary: TIES kırpma ve işaret seçimi (elect sign) adımlarını kodla, güvenlik görev vektörü ile birleşik vektör arasındaki işaret çatışmasını ölç ve hizalama kaybını yerel model deneyinde ölç.
esleme: ai-guvence-21, ai-guvence-25, ai-guvence-38
timeout: 60
---

::: anlat İki "iyi" modeli birleştirince güvenlik neden silinir?
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Ağırlık uzayında birleştirilen (`model merging`) modellerin görev vektörleri (`task vector`) zıt işaretli olduğunda, çoğunluk oyu güvenlik yönünü tersine çevirebilir | İlk üç görev: `veri/merging.json` içindeki **sentetik** görev vektörleri. Final: gerçek el yazısı rakamlarda (`load_digits`) ortak tabandan dört gerçek ince ayar; görev vektörlerinin `TIES` birleştirmesinde saldırganın vektörünün güvenlik davranışını iptal etmesi, ağırlık uzayı denetimi ve davranış testi | Her model birleştirme işleminin güvenliği bozacağını kanıtlamaz; sonuç vektörlerin açısal ve işaretsel uyumuna bağlıdır |
| `TIES` kırpma (`trim`) ve işaret seçimi (`elect sign`) gürültüyü azaltır ama baskın zıt vektörlere karşı güvenlik yönünü koruyamaz | Top-K büyüklük kırpması, kütle toplamıyla işaret seçimi, kosinüs benzerliği ve çatışma oranı | Ağırlık uzayında yüksek kosinüs benzerliğinin tüm davranışsal güvenlik testlerini geçeceğini garanti etmez |

> [!NOT]
> Görevler `veri/merging.json` dosyasını okur; dosya sentetiktir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; değişiklikler taşınmaz, **kalıcılık yoktur**. Ekranda ayrı dosya görüntüleyici yoktur; içeriği görmek için `print` kullan. Gizli testler ayrıdır. Final yeni model indirmez ve GPU varsa onu kullanır.

Açık ağırlıklı ekosistemde yeniden eğitim yapmadan birden fazla ince ayarlı (`fine-tuned`) modeli tek modelde toplamak için **`model merging`** yaygınlaşmıştır. Taban model ağırlıkları $\theta_{\text{taban}}$ ve ince ayarlı ağırlıklar $\theta_m$ olduğunda fark vektörüne **`task vector`** denir (Ilharco vd. 2023):
$$\tau_m = \theta_m - \theta_{\text{taban}}$$

**`TIES` (`Trim, Elect Sign, Merge`) nasıl çalışır?** Doğrudan ortalama almak iki soruna yol açar: küçük gürültülü ağırlıklar birikir ve zıt işaretli parametreler birbirini sıfırlar. Yadav vd. (2023) TIES için üç adım tanımlar. Aşağıdaki bağ bozma ve sıfır toplamı kuralları bu dersin uygulamasına aittir.
1. **Kırpma (`Trim`):** Her görev vektörü $\tau_m \in \mathbb{R}^d$ içinde mutlak değeri en büyük $k = \max(1, \lfloor d \cdot \text{yoğunluk} \rfloor)$ koordinat tutulur (eşitlikte küçük indis önceliklidir), kalan koordinatlar `0.0` yapılır.
2. **İşaret Seçimi (`Elect Sign`):** Her koordinat $j$ için kırpılmış değerlerin toplamı $S_j = \sum_m \tilde{\tau}_m[j]$ hesaplanır. Seçilen işaret $\text{sgn}(S_j) \in \{-1, 0, +1\}$ olur.
3. **Ayrık Birleştirme (`Disjoint Merge`):** Koordinat $j$ için yalnızca seçilen işaretle **aynı işaretli** ($\tilde{\tau}_m[j] \cdot \text{sgn}(S_j) > 0$) değerlerin aritmetik ortalaması alınır; seçilen işaret `0` ise sonuç `0.0` olur.

**DARE nasıl ayrılır?** Yu vd. (2024) her fark parametresini bağımsız olarak p olasılıkla sıfırlar ve kalanları 1/(1−p) ile ölçekler. Örneğin p=0.5 ve fark 0.2 için sonuç eşit olasılıkla 0 veya 0.4 olur. Beklenen değer 0.2 olsa da tek bir maske bu değeri korumaz. DARE, birleştirmeden önce uygulanabilen bir seyreltme adımıdır. Bu dersin kodu ve gerçek deneyi TIES üzerinedir.

**Güvenlik açığı nerededir?** Tedarik zincirinde bir güvenlik vektörü $\tau_{\text{güv}}$ ile dışarıdan alınan yardımcı görev vektörleri birleştirildiğinde, yardımcı vektörler güvenlik koordinatlarında ters işaret ve daha büyük kütle taşıyorsa `Elect Sign` adımı güvenlik ağırlıklarını **tamamen dışlar** (Hammoud vd. 2024).

**Çatışma ve silinme ölçütleri:** Güvenlik vektörü $g$ ve karşılaştırılan vektör $v$ için:
- `kosinus`: $\frac{g \cdot v}{\|g\|_2 \|v\|_2}$
- `catisma_orani`: $g_j \cdot v_j < 0$ olan koordinatların tüm boyuta ($d$) oranı.
- `silinen_guvenlik_orani`: Aktif güvenlik koordinatları ($|g_j| > 10^{-9}$) içinde hem zıt işaretli ($g_j \cdot v_j < 0$) hem de $|v_j| \ge |g_j|$ olanların aktif güvenlik koordinat sayısına oranı.

**Saldırgan ne dener?** Masum görünen bir yetenek adaptörü (ör. kodlama veya çeviri LoRA'sı) içine güvenlik vektörünün kritik koordinatlarını ters işaretle bastıracak büyük genlikli ağırlıklar gömer (`task vector poisoning`).

**Savunma neden kırılır?** Birleştirme öncesi ağırlık uzayında işaret çatışması ve kosinüs uyumu denetlenmezse, birleşik model yetenek testlerini geçerken güvenlik hizalamasını sessizce kaybeder.

**Görev 1'de sık tuzaklar:** İşaret seçiminde yalnız seçilen işaretle uyumlu olanların ortalamasını almak yerine tüm vektörlerin sayısına bölmek.

Kaynaklar: [Ilharco vd. 2023](https://arxiv.org/abs/2212.04089), [Yadav vd. 2023](https://arxiv.org/abs/2306.01708), [Yu vd. 2024](https://arxiv.org/abs/2311.03099), [Hammoud vd. 2024](https://arxiv.org/abs/2406.16363). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Köprü: ai-guvence-21 ve ai-guvence-25 model tedarik zincirini inceler; bu ders ağırlık birleştirme (`model merging`) aşamasındaki hizalama silinmesini ölçer.
:::

::: tahmin İşaret seçimi (Elect Sign) azınlık vektörünü nasıl dışlar?
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
guvenlik = 0.8
gorev1 = -1.2
gorev2 = -1.0
adaylar = [guvenlik, gorev1, gorev2]
toplam = sum(adaylar)
isaret = 1 if toplam > 0 else -1
uyumlu = [x for x in adaylar if x * isaret > 0]
print("Düz ortalama:", round(sum(adaylar) / len(adaylar), 3))
print("Seçilen işaret:", isaret)
print("TIES birleşik değer:", round(sum(uyumlu) / len(uyumlu), 3))
```
???
```cikti
Düz ortalama: -0.467
Seçilen işaret: -1
TIES birleşik değer: -1.1
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: `TIES` neden düz ortalamadan (`-0.467`) bile daha sert biçimde güvenlik yönünün tersine (`-1.1`) gitti? Sonra üç kusurlu başlangıç kodunu çalıştır ve her birinin neyi kaçırdığını önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · TIES kırpma, işaret seçimi ve birleştirme
`ties_kirp_ve_sec(gorev_vektorleri, yogunluk_orani)`: `gorev_vektorleri` en az bir vektör içeren liste listesi, her vektör aynı uzunlukta ($d \ge 1$) ve elemanları bool olmayan sonlu sayı; `0 < yogunluk_orani <= 1.0`. Her vektörde mutlak değeri en büyük $k = \max(1, \text{int}(d \cdot \text{yogunluk\_orani}))$ koordinatı (`(-abs(v[j]), j)` sırasıyla) koru, diğerlerini `0.0` yap. Her koordinatta kırpılmış toplamın işaretini seç ve yalnız o işaretle uyumlu (`t[j] * isaret > 0`) değerlerin ortalamasını döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-43")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def ties_kirp_ve_sec(gorev_vektorleri, yogunluk_orani):
    d = len(gorev_vektorleri[0])
    return [sum(v[j] for v in gorev_vektorleri) / len(gorev_vektorleri) for j in range(d)]

from ai_guvence_veri import json_yukle
v = json_yukle("veri/merging.json")
print("Uyumlu:", ties_kirp_ve_sec(v["uyumlu_gorevler"], v["yogunluk_orani"]))
print("Saldırgan:", ties_kirp_ve_sec(v["saldirgan_gorevler"], v["yogunluk_orani"]))
```
```test
def sinama1(f):
    import copy, math, random
    def _r(gv, yo):
        d = len(gv[0]); k = max(1, int(d * yo)); kr = []
        for v in gv:
            s = set(sorted(range(d), key=lambda j: (-abs(v[j]), j))[:k])
            kr.append([float(v[j]) if j in s else 0.0 for j in range(d)])
        out = []
        for j in range(d):
            top = sum(t[j] for t in kr)
            isaret = 1 if top > 0 else (-1 if top < 0 else 0)
            if isaret == 0: out.append(0.0)
            else:
                u = [t[j] for t in kr if t[j] * isaret > 0]
                out.append(float(sum(u) / len(u)) if u else 0.0)
        return out
    def _y(a, b): return isinstance(a, list) and len(a) == len(b) and all(abs(p - q) < 1e-12 for p, q in zip(a, b))
    try:
        gv = [[1.0, -0.2, 0.8], [-2.0, 0.5, 0.4], [-1.0, 0.1, -0.1]]; old = copy.deepcopy(gv)
        if not _y(f(gv, 0.7), [-1.5, 0.3, 0.8]) or gv != old: return False
        if not _y(f([[1.0, -1.0], [-1.0, 1.0]], 1.0), [0.0, 0.0]): return False
        rng = random.Random(43)
        for _ in range(25):
            m, d = rng.randint(2, 5), rng.randint(2, 7)
            rgv = [[rng.uniform(-2, 2) for _ in range(d)] for _ in range(m)]
            ryo = rng.uniform(0.2, 1.0)
            if not _y(f([list(x) for x in rgv], ryo), _r(rgv, ryo)): return False
        for bad in ((None, 0.5), ([], 0.5), ([[]], 0.5), ([[1.0], [1.0, 2.0]], 0.5), ([[True]], 0.5), ([[float("nan")]], 0.5), (gv, 0.0), (gv, -0.2), (gv, 1.2), (gv, True)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
ok(sinama1(ties_kirp_ve_sec), "büyüklük kırpması, işaret seçimi, ayrık ortalama ve geçersiz girdi")
for ad, mut in [
    ("düz ortalama", lambda gv, yo: [sum(v[j] for v in gv) / len(gv) for j in range(len(gv[0]))]),
    ("kırpma yok", lambda gv, yo: ties_kirp_ve_sec(gv, 1.0)),
    ("işaret ters", lambda gv, yo: [-x for x in ties_kirp_ve_sec(gv, yo)])
]:
    ok(not sinama1(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(ties_kirp_ve_sec, _il.import_module('ai_gercek_ai_guvence_43').referans_ties_kirp_ve_sec, ([[0.7, -0.5, 0.4, -0.3, 0.6, -0.4], [0.5, -0.4, 0.6, -0.2, 0.5, -0.6]], 0.67), tohum=2838)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def ties_kirp_ve_sec(gorev_vektorleri, yogunluk_orani):
    if not isinstance(gorev_vektorleri, list) or not gorev_vektorleri: raise ValueError("liste")
    if not isinstance(gorev_vektorleri[0], list) or not gorev_vektorleri[0]: raise ValueError("vektör")
    d = len(gorev_vektorleri[0])
    for v in gorev_vektorleri:
        if not isinstance(v, list) or len(v) != d: raise ValueError("boyut")
        for x in v:
            if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x): raise ValueError("sayı")
    if isinstance(yogunluk_orani, bool) or not isinstance(yogunluk_orani, (int, float)) or not math.isfinite(yogunluk_orani) or not 0 < yogunluk_orani <= 1.0:
        raise ValueError("yoğunluk")
    k = max(1, int(d * yogunluk_orani))
    kirpilmis = []
    for v in gorev_vektorleri:
        sec = set(sorted(range(d), key=lambda j: (-abs(v[j]), j))[:k])
        kirpilmis.append([float(v[j]) if j in sec else 0.0 for j in range(d)])
    birlesik = []
    for j in range(d):
        toplam = sum(t[j] for t in kirpilmis)
        isaret = 1 if toplam > 0 else (-1 if toplam < 0 else 0)
        if isaret == 0:
            birlesik.append(0.0)
        else:
            uyumlu = [t[j] for t in kirpilmis if t[j] * isaret > 0]
            birlesik.append(float(sum(uyumlu) / len(uyumlu)) if uyumlu else 0.0)
    return birlesik

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v = json_yukle("veri/merging.json")
    print("Uyumlu:", ties_kirp_ve_sec(v["uyumlu_gorevler"], v["yogunluk_orani"]))
    print("Saldırgan:", ties_kirp_ve_sec(v["saldirgan_gorevler"], v["yogunluk_orani"]))
```
```hint
Her vektörü `sorted(range(d), key=lambda j: (-abs(v[j]), j))[:k]` ile kırp; sonra her koordinat için toplamın işaretini bulup yalnız `t[j] * isaret > 0` olanların ortalamasını al.
```
:::

::: anlat İşaret çatışması ve kritik güvenlik silinmesi
Güvenlik vektörü $g$ ile birleşik/görev vektörü $v$ karşılaştırılırken üç nicelik hesaplanır:
- `kosinus`: İki vektör arasındaki kosinüs benzerliği.
- `catisma_orani`: $g_j \cdot v_j < 0$ olan koordinat sayısının $d$'ye oranı.
- `silinen_guvenlik_orani`: Aktif güvenlik koordinatları ($|g_j| > 10^{-9}$) içinde $g_j \cdot v_j < 0$ **ve** $|v_j| \ge |g_j|$ olanların aktif güvenlik koordinat sayısına oranı.

**Görev 2'de sık tuzaklar:** Sıfır normlu vektörlerde `ValueError` yükseltmeyi unutmak. `silinen_guvenlik_orani` paydasında aktif güvenlik koordinatları yerine tüm $d$ boyutunu kullanmak.
:::

::: gorev 2 · İşaret çatışma ve silinme oranı
`isaret_catisma_orani(guvenlik_vektoru, gorev_vektoru)`: Aynı uzunlukta ($d \ge 1$) iki dolu liste, elemanları bool olmayan sonlu sayı ve her iki vektörün L2 normu $> 0$. `{"kosinus": float, "catisma_orani": float, "silinen_guvenlik_orani": float}` döndür. Etkin güvenlik koordinatı yoksa silinme oranı 0.0 kabul edilir. Geçersiz girdide veya sıfır normda `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-43")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def isaret_catisma_orani(guvenlik_vektoru, gorev_vektoru):
    na = math.sqrt(sum(a * a for a in guvenlik_vektoru))
    nb = math.sqrt(sum(b * b for b in gorev_vektoru))
    kos = sum(a * b for a, b in zip(guvenlik_vektoru, gorev_vektoru)) / (na * nb)
    return {"kosinus": kos, "catisma_orani": 0.0, "silinen_guvenlik_orani": 0.0}

from ai_guvence_veri import json_yukle
v = json_yukle("veri/merging.json")
print(isaret_catisma_orani(v["guvenlik_vektoru"], v["saldirgan_gorevler"][1]))
```
```test
def sinama2(f):
    import copy, math, random
    def _r(g, v):
        na = math.sqrt(sum(a * a for a in g)); nb = math.sqrt(sum(b * b for b in v))
        kos = sum(a * b for a, b in zip(g, v)) / (na * nb)
        cat = sum(1 for a, b in zip(g, v) if a * b < 0) / len(g)
        akt = [j for j, a in enumerate(g) if abs(a) > 1e-9]
        sil = sum(1 for j in akt if g[j] * v[j] < 0 and abs(v[j]) >= abs(g[j])) / len(akt) if akt else 0.0
        return {"kosinus": float(kos), "catisma_orani": float(cat), "silinen_guvenlik_orani": float(sil)}
    def _y(a, b): return isinstance(a, dict) and set(a) == set(b) and all(abs(a[k] - b[k]) < 1e-12 for k in b)
    try:
        g = [1.0, -2.0, 0.0, 1.0]; v = [-1.5, 1.0, 3.0, 1.0]; old = (list(g), list(v))
        if not _y(f(g, v), _r(g, v)) or (g, v) != old: return False
        if f(g, v)["catisma_orani"] != 0.5 or abs(f(g, v)["silinen_guvenlik_orani"] - 1.0 / 3.0) > 1e-12: return False
        for deger, oran in ((0.75e-9, 0.0), (1e-9, 0.0), (1.5e-9, 0.5)):
            if f([1.0, deger], [1.0, -deger])["silinen_guvenlik_orani"] != oran:
                return False
        if f([1e-10], [-1e-10])["silinen_guvenlik_orani"] != 0.0:
            return False
        rng = random.Random(4343)
        for _ in range(25):
            d = rng.randint(2, 8)
            rg = [rng.uniform(-2, 2) for _ in range(d)]; rv = [rng.uniform(-2, 2) for _ in range(d)]
            if not _y(f(list(rg), list(rv)), _r(rg, rv)): return False
        for bad in ((None, v), (g, None), ([], []), ([0.0, 0.0], [1.0, 2.0]), ([1.0, 2.0], [0.0, 0.0]), ([1.0], v), ([True, 1.0, 1.0, 1.0], v), (g, [float("nan"), 1.0, 1.0, 1.0])):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
ok(sinama2(isaret_catisma_orani), "kosinüs, işaret çatışması, aktif güvenlik silinmesi ve geçersiz girdi")
for ad, mut in [
    ("çatışma sıfır", lambda g, v: dict(isaret_catisma_orani(g, v), catisma_orani=0.0)),
    ("silinen yerine çatışma", lambda g, v: dict(isaret_catisma_orani(g, v), silinen_guvenlik_orani=isaret_catisma_orani(g, v)["catisma_orani"])),
    ("kosinüs ters", lambda g, v: dict(isaret_catisma_orani(g, v), kosinus=-isaret_catisma_orani(g, v)["kosinus"]))
]:
    ok(not sinama2(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(isaret_catisma_orani, _il.import_module('ai_gercek_ai_guvence_43').referans_isaret_catisma, ([0.8, -0.6, 0.5, -0.4, 0.7, -0.5], [-1.2, 0.9, -0.8, 0.7, -1.1, 0.8]), tohum=3257)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
# hedefli tablo: sıfır bileşenler çatışma sayılmaz
_R43 = _il.import_module("ai_gercek_ai_guvence_43")
_ek = (([1.0, 0.0, -1.0, 0.5], [1.0, 1.0, 0.0, -0.5]), ([0.0, 1.0], [1.0, 0.0]), ([1.0, -1.0, 0.0], [-1.0, 1.0, 0.0]), ([2.0, -2.0], [-2.0, 1.0]))
_t, _g = _ff(isaret_catisma_orani, _R43.referans_isaret_catisma, _ek[0], en_cok=0, ekler=_ek)
ok(_t, "sıfır bileşenli vektörlerde çatışma ve silinme oranı referansla aynı" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def isaret_catisma_orani(guvenlik_vektoru, gorev_vektoru):
    if not isinstance(guvenlik_vektoru, list) or not isinstance(gorev_vektoru, list) or not guvenlik_vektoru or len(guvenlik_vektoru) != len(gorev_vektoru):
        raise ValueError("vektör")
    for x in guvenlik_vektoru + gorev_vektoru:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x): raise ValueError("sayı")
    na = math.sqrt(sum(a * a for a in guvenlik_vektoru))
    nb = math.sqrt(sum(b * b for b in gorev_vektoru))
    if na <= 0 or nb <= 0: raise ValueError("sıfır norm")
    kosinus = sum(a * b for a, b in zip(guvenlik_vektoru, gorev_vektoru)) / (na * nb)
    catisma = sum(1 for a, b in zip(guvenlik_vektoru, gorev_vektoru) if a * b < 0) / len(guvenlik_vektoru)
    aktif = [j for j, a in enumerate(guvenlik_vektoru) if abs(a) > 1e-9]
    silinen = sum(1 for j in aktif if guvenlik_vektoru[j] * gorev_vektoru[j] < 0 and abs(gorev_vektoru[j]) >= abs(guvenlik_vektoru[j])) / len(aktif) if aktif else 0.0
    return {"kosinus": float(kosinus), "catisma_orani": float(catisma), "silinen_guvenlik_orani": float(silinen)}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v = json_yukle("veri/merging.json")
    print(isaret_catisma_orani(v["guvenlik_vektoru"], v["saldirgan_gorevler"][1]))
```
```hint
Aktif güvenlik indislerini `abs(a) > 1e-9` ile filtrele; bunların içinde `a * b < 0` ve `abs(b) >= abs(a)` olanların sayısını aktif güvenlik sayısına böl.
```
:::

::: anlat Birleştirme güvence raporu
Birleşik vektörün yayına alınmadan önce denetlenmesi üç bayrakla yapılır (alfabetik sıra):
- `hizalama_kaybi`: `kosinus < min_kosinus`
- `isaret_catismasi`: `catisma_orani > max_catisma`
- `kritik_silinme`: `silinen_guvenlik_orani > max_catisma`

Hiçbir bayrak tetiklenmezse `guvenli=True`, aksi hâlde `False` döner.

**Görev 3'te sık tuzaklar:** `min_kosinus` aralığını `[-1, 1]` ve `max_catisma` aralığını `[0, 1]` olarak doğrulamamak.
:::

::: gorev 3 · Birleştirme güvence raporu
`birlestirme_guvence_raporu(guvenlik_vektoru, birlesik_vektor, min_kosinus, max_catisma)`: İki vektör geçerli ve sıfır olmayan normda; `-1.0 <= min_kosinus <= 1.0`, `0.0 <= max_catisma <= 1.0`. `{"bayraklar": [...], "guvenli": bool, "kosinus": float, "catisma_orani": float, "silinen_guvenlik_orani": float}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-43")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def birlestirme_guvence_raporu(guvenlik_vektoru, birlesik_vektor, min_kosinus, max_catisma):
    na = math.sqrt(sum(a * a for a in guvenlik_vektoru))
    nb = math.sqrt(sum(b * b for b in birlesik_vektor))
    kos = sum(a * b for a, b in zip(guvenlik_vektoru, birlesik_vektor)) / (na * nb)
    return {"bayraklar": [], "guvenli": True, "kosinus": kos, "catisma_orani": 0.0, "silinen_guvenlik_orani": 0.0}

from ai_guvence_veri import json_yukle
v = json_yukle("veri/merging.json")
print(birlestirme_guvence_raporu(v["guvenlik_vektoru"], v["saldirgan_gorevler"][1], v["min_kosinus"], v["max_catisma"]))
```
```test
def sinama3(f):
    import copy, math
    try:
        if f([1e-10], [-1e-10], -1.0, 1.0)["silinen_guvenlik_orani"] != 0.0:
            return False
        if f([1.0], [1.0], 1.0, 0.0)["bayraklar"] != []:
            return False
        for deger, oran in ((0.75e-9, 0.0), (1e-9, 0.0), (1.5e-9, 0.5)):
            if f([1.0, deger], [1.0, -deger], 0.0, 1.0)["silinen_guvenlik_orani"] != oran:
                return False
        g = [1.0, -1.0, 1.0, -1.0]; u = [0.9, -0.8, 1.1, -0.9]; s = [-1.2, 1.1, -1.5, 0.5]
        old = (list(g), list(u))
        r1 = f(g, u, 0.8, 0.25)
        if r1["bayraklar"] != [] or r1["guvenli"] is not True or (g, u) != old: return False
        r2 = f(g, s, 0.5, 0.3)
        if r2["bayraklar"] != ["hizalama_kaybi", "isaret_catismasi", "kritik_silinme"] or r2["guvenli"] is not False:
            return False
        # Yalnız isaret_catismasi (büyüklük küçük olduğu için kritik_silinme yok, kosinüs yüksek)
        r3 = f([2.0, 2.0, 1.0], [2.0, 2.0, -0.1], 0.5, 0.2)
        if r3["bayraklar"] != ["isaret_catismasi"] or r3["guvenli"] is not False: return False
        for bad in ((None, u, 0.5, 0.3), ([0.0, 0.0], [1.0, 1.0], 0.5, 0.3), ([1.0, 1.0], [0.0, 0.0], 0.5, 0.3), (g, u, -1.5, 0.3), (g, u, 1.5, 0.3), (g, u, 0.5, -0.1), (g, u, 0.5, 1.2), (g, u, True, 0.3), (g, u, 0.5, True)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
ok(sinama3(birlestirme_guvence_raporu), "üç bayrak, güvenli kararı, sınırlar ve geçersiz girdi")
for ad, mut in [
    ("hep güvenli", lambda g, b, mk, mc: dict(birlestirme_guvence_raporu(g, b, mk, mc), bayraklar=[], guvenli=True)),
    ("guvenli ters", lambda g, b, mk, mc: dict(birlestirme_guvence_raporu(g, b, mk, mc), guvenli=not birlestirme_guvence_raporu(g, b, mk, mc)["guvenli"])),
    ("kritik silinme yok", lambda g, b, mk, mc: dict(birlestirme_guvence_raporu(g, b, mk, mc), bayraklar=[x for x in birlestirme_guvence_raporu(g, b, mk, mc)["bayraklar"] if x != "kritik_silinme"]))
]:
    ok(not sinama3(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(birlestirme_guvence_raporu, _il.import_module('ai_gercek_ai_guvence_43').referans_birlestirme_raporu, ([0.8, -0.6, 0.5, -0.4, 0.7, -0.5], [-1.2, 0.9, -0.8, 0.7, -1.1, 0.8], 0.5, 0.35), tohum=3934)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def birlestirme_guvence_raporu(guvenlik_vektoru, birlesik_vektor, min_kosinus, max_catisma):
    if not isinstance(guvenlik_vektoru, list) or not isinstance(birlesik_vektor, list) or not guvenlik_vektoru or len(guvenlik_vektoru) != len(birlesik_vektor):
        raise ValueError("vektör")
    for x in guvenlik_vektoru + birlesik_vektor + [min_kosinus, max_catisma]:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x): raise ValueError("sayı")
    if not -1.0 <= min_kosinus <= 1.0 or not 0.0 <= max_catisma <= 1.0: raise ValueError("eşik")
    na = math.sqrt(sum(a * a for a in guvenlik_vektoru))
    nb = math.sqrt(sum(b * b for b in birlesik_vektor))
    if na <= 0 or nb <= 0: raise ValueError("sıfır norm")
    kosinus = float(sum(a * b for a, b in zip(guvenlik_vektoru, birlesik_vektor)) / (na * nb))
    catisma = float(sum(1 for a, b in zip(guvenlik_vektoru, birlesik_vektor) if a * b < 0) / len(guvenlik_vektoru))
    aktif = [j for j, a in enumerate(guvenlik_vektoru) if abs(a) > 1e-9]
    silinen = float(sum(1 for j in aktif if guvenlik_vektoru[j] * birlesik_vektor[j] < 0 and abs(birlesik_vektor[j]) >= abs(guvenlik_vektoru[j])) / len(aktif)) if aktif else 0.0
    bayraklar = []
    if kosinus < min_kosinus: bayraklar.append("hizalama_kaybi")
    if catisma > max_catisma: bayraklar.append("isaret_catismasi")
    if silinen > max_catisma: bayraklar.append("kritik_silinme")
    return {"bayraklar": bayraklar, "guvenli": not bool(bayraklar), "kosinus": kosinus, "catisma_orani": catisma, "silinen_guvenlik_orani": silinen}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v = json_yukle("veri/merging.json")
    print(birlestirme_guvence_raporu(v["guvenlik_vektoru"], v["saldirgan_gorevler"][1], v["min_kosinus"], v["max_catisma"]))
```
```hint
Kosinüs, çatışma ve silinen güvenlik oranlarını hesapladıktan sonra üç bayrağı alfabetik sırayla kontrol et; `guvenli` alanı `not bool(bayraklar)` olmalı.
```
:::

::: anlat Hata vitrini · çalışmış yanlış rapor
Yazar, kusurlu başlangıç kodlarını görünür sentetik veriyle gerçekten çalıştırdı ve sonucu `outputs/yeni-ai-guvence-43/gorunur-run-1.json` dosyasına kaydetti. `saldirgan_gorevler` birleştirildiğinde kusurlu kod `kosinus=-0.998` hesaplamasına rağmen `bayraklar=[]` ve `guvenli=True` döndürür. Doğru kod ise `TIES` birleştirmesi sonucunda güvenlik koordinatlarının `%83.3` oranında ters işaretle bastırıldığını (`bayraklar=['hizalama_kaybi', 'isaret_catismasi', 'kritik_silinme']`, `guvenli=False`) açıkça işaretler.

Bu kaydedilmiş bir hesaplama çıktısıdır, model yanıtı değildir ve rapor sentetiktir. Kosinüs benzerliği `-0.95` iken `guvenli=True` raporuna güvenen bir tedarik zinciri otomasyonu ne tür bir modeli yayına almış olur? Kendi cümlenle açıkla. Gerçek finaldeki ölçüm ayrıca üretilir; bu sayılar onun yerine konmaz.
:::

::: anlat Gerçek deney: gerçek ince ayarlardan görev vektörleri, TIES birleştirme ve güvenlik iptali
Final gerçek ince ayarlardan gerçek görev vektörleri çıkarır. Önceki sürümde diğer vektörler güvenlik vektörünün ölçeklenmiş kopyalarıydı; bu sürüm ağırlık uzayının gerçek davranışını gösterir.

**Veri ve görevler.** Veri, `sklearn` `load_digits`'tir: 1797 gerçek el yazısı rakam, 8×8 piksel. Karıştırılır ve iki eğitim bölümüne (A, B) ve ayrık bir teste ayrılır. Oyuncak bir "güvenlik" görevi tanımlanır: rakam ≥ 5 "zararlı istek" sayılır ve reddedilmelidir. Zararsız yardımcı görev paritedir (çift/tek).

**İnce ayarlar.** Önce ortak bir taban model ön eğitilir (rakam 3'e bölünüyor mu). Aynı tabandan dört ayrı ince ayar yapılır ve her biri $\tau = \theta_{\text{ince ayar}} - \theta_0$ olarak (bütün parametreler, 1610 boyut) çıkarılır:
- $\tau_{\text{güv}}$: güvenlik ekibinin ince ayarı (bölüm A).
- $\tau_{\text{güv,B}}$: aynı görev, bağımsız ikinci ince ayar (bölüm B).
- $\tau_{\text{parite}}$: zararsız yetenek.
- $\tau_{\text{ters}}$: saldırganın "yardımcı model" diye yayımladığı ince ayar. Güvenlik etiketlerini **ters çevirerek** eğitilmiştir ve 1.5 kat uzun sürmüştür.

**Birleştirmeler.** İki `TIES` birleştirmesi yapılır (yoğunluk 0.75, λ = 1):
- **Uyumlu:** $\tau_{\text{güv}} + \tau_{\text{güv,B}} + \tau_{\text{parite}}$
- **Saldırı:** $\tau_{\text{güv}} + \tau_{\text{ters}} + \tau_{\text{parite}}$

Senin işlevlerin bu gerçek vektörlerde çalışır. Birleştirilmiş ağırlıklar modele geri yüklenip ayrık testte güvenlik ve parite doğruluğu ölçülür.

Yazarın sekiz GPU koşusunda (her biri birkaç saniye) şu sonuçlar alındı:
- **Ağırlık uzayı sezgiyi bozar.** Aynı güvenlik görevinin iki bağımsız ince ayarı arasındaki kosinüs yalnız **0.52–0.75**. Saldırganın ters etiketli vektörü güvenlik vektörüne **neredeyse dik** (−0.06 ile −0.33), "ters işaretli" değil. Bağımsız ince ayarlar aynı davranışı farklı ağırlık yollarıyla kurar.
- **Davranış yine de çöker.** Yalnız güvenlik ince ayarı ayrık testte 0.91–0.96 doğruluk verir. Uyumlu birleştirme koşuya göre 0.59–0.88'e iner; bu, görevler arası girişimin bedelidir. Saldırı birleştirmesi ise **0.25–0.54**'e, yani taban modelin (~0.46–0.54) seviyesine ya da altına iner. Aynı model paritede 0.60–0.89 ile "faydalı" görünür. Basit ortalama da benzer şekilde çöker.
- **Ağırlık uzayı denetimi kaçırır.** Senin `birlestirme_guvence_raporu`'n (kosinüs < 0.45, işaret çatışması > 0.35, kritik silinme) saldırı birleştirmesini üç koşudan yalnız **birinde** işaretledi. Kosinüs koşuya göre 0.25–0.66 çıktı.
- **DARE ve SLERP de ölçülür.**
  - **DARE** (Yu vd. 2024): her görev vektöründe girdilerin %90'ı rastgele atılır, kalanlar 10 ile ölçeklenir, sonra toplanır. Bu küçük ağda uyumlu birleştirmeyi bile taban seviyesine indirdi (güvenlik 0.43–0.59). DARE, büyük dil modellerinin fazlalık taşıyan ince ayar farkları için tasarlanmıştır; 1610 parametrelik bir ağda her girdi önemlidir.
  - **SLERP** (iki model arasında küresel ara değerleme, t = 0.5): güvenlik+parite iki görevi de yarı yarıya korudu (güvenlik ~0.58–0.60, parite ~0.67–0.72). Güvenlik+saldırgan ise güvenliği 0.49–0.59'a indirdi.
- **SVD ile tespit de saldırganı ayırmadı.** Güvenlik ince ayarının ilk katman ağırlık farkının (24 × 64) en büyük 4 sağ tekil yönü, güvenlik görevinin kullandığı piksel özelliklerinin alt uzayıdır. Başka bir görev vektörünün enerjisinin bu alt uzaya düşen payı ölçüldü:
  - aynı görevin ikinci ince ayarı: 0.31–0.45,
  - zararsız parite: 0.09–0.27,
  - saldırgan: **0.08–0.28** (rastgele taban 0.06).

  Saldırgan zararsız görevden ayrılmıyor. **Ağırlık uzayındaki üç denetimin üçü de** (kosinüs, işaret çatışması, SVD alt uzayı) başarısız oldu. Güvenliğin gittiğini güvenilir biçimde gösteren tek ölçüm, birleştirmeden sonra koşulan **davranış testiydi** (güvenlik test kümesi).

**Kanıt dosyasını oku:** Soru 1: `gorev_kosinuslari.ters` neredeyse sıfırken güvenlik davranışı neden yok oldu? (İpucu: davranışı yalnız son katman değil, ilk katmanın öğrendiği özellikler de belirler; ters ince ayar başka özellikler üzerinden zıt kararı kurabilir.) Soru 2: Bir model merkezine (hub) yüklenen birleştirme adaylarını kabul etmeden önce hangi davranış testlerini koşardın? Soru 3: `TIES` içinde `Elect Sign` adımı, dik vektörlerin çatışmasında neden pek bir şey değiştirmez? Cevabını tezgâhta yorum olarak yaz; otomatik test bu serbest açıklamayı puanlamaz.
:::

::: gorev Gerçek deney · Görev vektörü birleştirmede TIES ve hizalama denetimi
Önceki üç görevin `ties_kirp_ve_sec`, `isaret_catisma_orani` ve `birlestirme_guvence_raporu` işlevlerini birleştir. Çalıştır gerçek tabloyu gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 180
```
```starter
import ai_lab
import math
def ties_kirp_ve_sec(gorev_vektorleri, yogunluk_orani):
    d = len(gorev_vektorleri[0])
    return [sum(v[j] for v in gorev_vektorleri) / len(gorev_vektorleri) for j in range(d)]
def isaret_catisma_orani(guvenlik_vektoru, gorev_vektoru):
    na = math.sqrt(sum(a * a for a in guvenlik_vektoru))
    nb = math.sqrt(sum(b * b for b in gorev_vektoru))
    kos = sum(a * b for a, b in zip(guvenlik_vektoru, gorev_vektoru)) / (na * nb)
    return {"kosinus": kos, "catisma_orani": 0.0, "silinen_guvenlik_orani": 0.0}
def birlestirme_guvence_raporu(guvenlik_vektoru, birlesik_vektor, min_kosinus, max_catisma):
    na = math.sqrt(sum(a * a for a in guvenlik_vektoru))
    nb = math.sqrt(sum(b * b for b in birlesik_vektor))
    kos = sum(a * b for a, b in zip(guvenlik_vektoru, birlesik_vektor)) / (na * nb)
    return {"bayraklar": [], "guvenli": True, "kosinus": kos, "catisma_orani": 0.0, "silinen_guvenlik_orani": 0.0}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_43 as D
    D.goster(ties_kirp_ve_sec, isaret_catisma_orani, birlestirme_guvence_raporu)
```
```test
import ai_lab, math
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('referans_ties_kirp_ve_sec', 'referans_isaret_catisma', 'referans_birlestirme_raporu', 'kanit_yaz', '_yakin'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
ties_kirp_ve_sec = need("ties_kirp_ve_sec")
isaret_catisma_orani = need("isaret_catisma_orani")
birlestirme_guvence_raporu = need("birlestirme_guvence_raporu")
def sinama1(f):
    import copy, math, random
    def _r(gv, yo):
        d = len(gv[0]); k = max(1, int(d * yo)); kr = []
        for v in gv:
            s = set(sorted(range(d), key=lambda j: (-abs(v[j]), j))[:k])
            kr.append([float(v[j]) if j in s else 0.0 for j in range(d)])
        out = []
        for j in range(d):
            top = sum(t[j] for t in kr)
            isaret = 1 if top > 0 else (-1 if top < 0 else 0)
            if isaret == 0: out.append(0.0)
            else:
                u = [t[j] for t in kr if t[j] * isaret > 0]
                out.append(float(sum(u) / len(u)) if u else 0.0)
        return out
    def _y(a, b): return isinstance(a, list) and len(a) == len(b) and all(abs(p - q) < 1e-12 for p, q in zip(a, b))
    try:
        gv = [[1.0, -0.2, 0.8], [-2.0, 0.5, 0.4], [-1.0, 0.1, -0.1]]; old = copy.deepcopy(gv)
        if not _y(f(gv, 0.7), [-1.5, 0.3, 0.8]) or gv != old: return False
        rng = random.Random(43)
        for _ in range(25):
            m, d = rng.randint(2, 5), rng.randint(2, 7)
            rgv = [[rng.uniform(-2, 2) for _ in range(d)] for _ in range(m)]
            ryo = rng.uniform(0.2, 1.0)
            if not _y(f([list(x) for x in rgv], ryo), _r(rgv, ryo)): return False
        for bad in ((None, 0.5), ([], 0.5), ([[]], 0.5), ([[1.0], [1.0, 2.0]], 0.5), (gv, 0.0), (gv, 1.2), (gv, True)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama1(ties_kirp_ve_sec), "büyüklük kırpması, işaret seçimi, ayrık ortalama ve geçersiz girdi")
for ad, mut in [
    ("düz ortalama", lambda gv, yo: [sum(v[j] for v in gv) / len(gv) for j in range(len(gv[0]))]),
    ("kırpma yok", lambda gv, yo: ties_kirp_ve_sec(gv, 1.0)),
    ("işaret ters", lambda gv, yo: [-x for x in ties_kirp_ve_sec(gv, yo)])
]:
    kontrol(not sinama1(mut), "mutant reddedildi: " + ad)
def sinama2(f):
    import copy, math, random
    def _r(g, v):
        na = math.sqrt(sum(a * a for a in g)); nb = math.sqrt(sum(b * b for b in v))
        kos = sum(a * b for a, b in zip(g, v)) / (na * nb)
        cat = sum(1 for a, b in zip(g, v) if a * b < 0) / len(g)
        akt = [j for j, a in enumerate(g) if abs(a) > 1e-9]
        sil = sum(1 for j in akt if g[j] * v[j] < 0 and abs(v[j]) >= abs(g[j])) / len(akt) if akt else 0.0
        return {"kosinus": float(kos), "catisma_orani": float(cat), "silinen_guvenlik_orani": float(sil)}
    def _y(a, b): return isinstance(a, dict) and set(a) == set(b) and all(abs(a[k] - b[k]) < 1e-12 for k in b)
    try:
        g = [1.0, -2.0, 0.0, 1.0]; v = [-1.5, 1.0, 3.0, 1.0]; old = (list(g), list(v))
        if not _y(f(g, v), _r(g, v)) or (g, v) != old: return False
        for deger, oran in ((0.75e-9, 0.0), (1e-9, 0.0), (1.5e-9, 0.5)):
            if f([1.0, deger], [1.0, -deger])["silinen_guvenlik_orani"] != oran:
                return False
        if f([1e-10], [-1e-10])["silinen_guvenlik_orani"] != 0.0:
            return False
        rng = random.Random(4343)
        for _ in range(25):
            d = rng.randint(2, 8)
            rg = [rng.uniform(-2, 2) for _ in range(d)]; rv = [rng.uniform(-2, 2) for _ in range(d)]
            if not _y(f(list(rg), list(rv)), _r(rg, rv)): return False
        for bad in ((None, v), ([0.0, 0.0], [1.0, 2.0]), ([1.0], v), ([True, 1.0, 1.0, 1.0], v)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama2(isaret_catisma_orani), "kosinüs, işaret çatışması, aktif güvenlik silinmesi ve geçersiz girdi")
for ad, mut in [
    ("çatışma sıfır", lambda g, v: dict(isaret_catisma_orani(g, v), catisma_orani=0.0)),
    ("silinen yerine çatışma", lambda g, v: dict(isaret_catisma_orani(g, v), silinen_guvenlik_orani=isaret_catisma_orani(g, v)["catisma_orani"])),
    ("kosinüs ters", lambda g, v: dict(isaret_catisma_orani(g, v), kosinus=-isaret_catisma_orani(g, v)["kosinus"]))
]:
    kontrol(not sinama2(mut), "mutant reddedildi: " + ad)
def sinama3(f):
    import copy, math
    try:
        if f([1e-10], [-1e-10], -1.0, 1.0)["silinen_guvenlik_orani"] != 0.0:
            return False
        if f([1.0], [1.0], 1.0, 0.0)["bayraklar"] != []:
            return False
        for deger, oran in ((0.75e-9, 0.0), (1e-9, 0.0), (1.5e-9, 0.5)):
            if f([1.0, deger], [1.0, -deger], 0.0, 1.0)["silinen_guvenlik_orani"] != oran:
                return False
        g = [1.0, -1.0, 1.0, -1.0]; u = [0.9, -0.8, 1.1, -0.9]; s = [-1.2, 1.1, -1.5, 0.5]
        old = (list(g), list(u))
        if f(g, u, 0.8, 0.25)["guvenli"] is not True or (g, u) != old: return False
        r2 = f(g, s, 0.5, 0.3)
        if r2["bayraklar"] != ["hizalama_kaybi", "isaret_catismasi", "kritik_silinme"] or r2["guvenli"] is not False: return False
        if f([2.0, 2.0, 1.0], [2.0, 2.0, -0.1], 0.5, 0.2)["bayraklar"] != ["isaret_catismasi"]: return False
        for bad in ((None, u, 0.5, 0.3), ([1.0], u, 0.5, 0.3), ([0.0, 0.0], [1.0, 1.0], 0.5, 0.3), ([1.0, 1.0], [0.0, 0.0], 0.5, 0.3), (g, u, -1.5, 0.3), (g, u, 0.5, 1.2), (g, u, True, 0.3)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama3(birlestirme_guvence_raporu), "üç bayrak, güvenli kararı, sınırlar ve geçersiz girdi")
for ad, mut in [
    ("hep güvenli", lambda g, b, mk, mc: dict(birlestirme_guvence_raporu(g, b, mk, mc), bayraklar=[], guvenli=True)),
    ("guvenli ters", lambda g, b, mk, mc: dict(birlestirme_guvence_raporu(g, b, mk, mc), guvenli=not birlestirme_guvence_raporu(g, b, mk, mc)["guvenli"])),
    ("kritik silinme yok", lambda g, b, mk, mc: dict(birlestirme_guvence_raporu(g, b, mk, mc), bayraklar=[x for x in birlestirme_guvence_raporu(g, b, mk, mc)["bayraklar"] if x != "kritik_silinme"]))
]:
    kontrol(not sinama3(mut), "mutant reddedildi: " + ad)
# farksal tarama (final)
import importlib as _il
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_R = _il.import_module('sandbox.ai_gercek_ai_guvence_43')
for _ad, _ref, _taban, _toh in (
    ('ties_kirp_ve_sec', 'referans_ties_kirp_ve_sec', ([[0.7, -0.5, 0.4, -0.3, 0.6, -0.4], [0.5, -0.4, 0.6, -0.2, 0.5, -0.6]], 0.67), 3360),
    ('isaret_catisma_orani', 'referans_isaret_catisma', ([0.8, -0.6, 0.5, -0.4, 0.7, -0.5], [-1.2, 0.9, -0.8, 0.7, -1.1, 0.8]), 3779),
    ('birlestirme_guvence_raporu', 'referans_birlestirme_raporu', ([0.8, -0.6, 0.5, -0.4, 0.7, -0.5], [-1.2, 0.9, -0.8, 0.7, -1.1, 0.8], 0.5, 0.35), 4456),
):
    _t, _g = _ff(need(_ad), getattr(_R, _ref), _taban, tohum=_toh)
    kontrol(_t, "farksal tarama (" + _ad + "): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
if not all(checks): stop()
from sandbox import ai_gercek_ai_guvence_43 as D
try: r = D.deney(ties_kirp_ve_sec, isaret_catisma_orani, birlestirme_guvence_raporu)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
d = r["dogruluklar"]
kontrol(r["ties_ayni"], "gerçek ince ayarlardan çıkan görev vektörlerinde TIES birleştirme bağımsız hesapla aynı")
kontrol(r["catisma_ayni"], "gerçek görev vektörlerinde çatışma analizi bağımsız hesapla aynı")
kontrol(r["rapor_ayni"], "gerçek görev vektörlerinde güvence raporu bağımsız hesapla aynı")
kontrol(d["yalniz_guvenlik"]["guvenlik"] >= 0.85, "güvenlik ince ayarı ayrık testte işe yaradı: %.3f" % d["yalniz_guvenlik"]["guvenlik"])
kontrol(d["saldiri_birlesim"]["guvenlik"] < d["yalniz_guvenlik"]["guvenlik"] - 0.3 and d["saldiri_birlesim"]["guvenlik"] <= d["taban"]["guvenlik"] + 0.15,
        "saldırganın görev vektörü birleştirmede güvenlik davranışını taban seviyesine indirdi: %.3f (güvenlik ince ayarı %.3f, taban %.3f, uyumlu birleşim %.3f)" % (
            d["saldiri_birlesim"]["guvenlik"], d["yalniz_guvenlik"]["guvenlik"], d["taban"]["guvenlik"], d["uyumlu_birlesim"]["guvenlik"]))
kontrol(d["saldiri_birlesim"]["parite"] > d["taban"]["parite"], "saldırı birleşimi zararsız görevde faydalı görünmeye devam etti: parite %.3f" % d["saldiri_birlesim"]["parite"])
ai_lab.kanit_yaz("ai-guvence-43-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-guvence-43", "deney": r})
```
```solution
import ai_lab
import math
def ties_kirp_ve_sec(gorev_vektorleri, yogunluk_orani):
    if not isinstance(gorev_vektorleri, list) or not gorev_vektorleri: raise ValueError("liste")
    if not isinstance(gorev_vektorleri[0], list) or not gorev_vektorleri[0]: raise ValueError("vektör")
    d = len(gorev_vektorleri[0])
    for v in gorev_vektorleri:
        if not isinstance(v, list) or len(v) != d: raise ValueError("boyut")
        for x in v:
            if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x): raise ValueError("sayı")
    if isinstance(yogunluk_orani, bool) or not isinstance(yogunluk_orani, (int, float)) or not math.isfinite(yogunluk_orani) or not 0 < yogunluk_orani <= 1.0:
        raise ValueError("yoğunluk")
    k = max(1, int(d * yogunluk_orani))
    kirpilmis = []
    for v in gorev_vektorleri:
        sec = set(sorted(range(d), key=lambda j: (-abs(v[j]), j))[:k])
        kirpilmis.append([float(v[j]) if j in sec else 0.0 for j in range(d)])
    birlesik = []
    for j in range(d):
        toplam = sum(t[j] for t in kirpilmis)
        isaret = 1 if toplam > 0 else (-1 if toplam < 0 else 0)
        if isaret == 0:
            birlesik.append(0.0)
        else:
            uyumlu = [t[j] for t in kirpilmis if t[j] * isaret > 0]
            birlesik.append(float(sum(uyumlu) / len(uyumlu)) if uyumlu else 0.0)
    return birlesik
def isaret_catisma_orani(guvenlik_vektoru, gorev_vektoru):
    if not isinstance(guvenlik_vektoru, list) or not isinstance(gorev_vektoru, list) or not guvenlik_vektoru or len(guvenlik_vektoru) != len(gorev_vektoru):
        raise ValueError("vektör")
    for x in guvenlik_vektoru + gorev_vektoru:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x): raise ValueError("sayı")
    na = math.sqrt(sum(a * a for a in guvenlik_vektoru))
    nb = math.sqrt(sum(b * b for b in gorev_vektoru))
    if na <= 0 or nb <= 0: raise ValueError("sıfır norm")
    kosinus = sum(a * b for a, b in zip(guvenlik_vektoru, gorev_vektoru)) / (na * nb)
    catisma = sum(1 for a, b in zip(guvenlik_vektoru, gorev_vektoru) if a * b < 0) / len(guvenlik_vektoru)
    aktif = [j for j, a in enumerate(guvenlik_vektoru) if abs(a) > 1e-9]
    silinen = sum(1 for j in aktif if guvenlik_vektoru[j] * gorev_vektoru[j] < 0 and abs(gorev_vektoru[j]) >= abs(guvenlik_vektoru[j])) / len(aktif) if aktif else 0.0
    return {"kosinus": float(kosinus), "catisma_orani": float(catisma), "silinen_guvenlik_orani": float(silinen)}
def birlestirme_guvence_raporu(guvenlik_vektoru, birlesik_vektor, min_kosinus, max_catisma):
    if not isinstance(guvenlik_vektoru, list) or not isinstance(birlesik_vektor, list) or not guvenlik_vektoru or len(guvenlik_vektoru) != len(birlesik_vektor):
        raise ValueError("vektör")
    for x in guvenlik_vektoru + birlesik_vektor + [min_kosinus, max_catisma]:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x): raise ValueError("sayı")
    if not -1.0 <= min_kosinus <= 1.0 or not 0.0 <= max_catisma <= 1.0: raise ValueError("eşik")
    m = isaret_catisma_orani(guvenlik_vektoru, birlesik_vektor)
    bayraklar = []
    if m["kosinus"] < min_kosinus: bayraklar.append("hizalama_kaybi")
    if m["catisma_orani"] > max_catisma: bayraklar.append("isaret_catismasi")
    if m["silinen_guvenlik_orani"] > max_catisma: bayraklar.append("kritik_silinme")
    return {"bayraklar": bayraklar, "guvenli": not bool(bayraklar), "kosinus": m["kosinus"], "catisma_orani": m["catisma_orani"], "silinen_guvenlik_orani": m["silinen_guvenlik_orani"]}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_43 as D
    D.goster(ties_kirp_ve_sec, isaret_catisma_orani, birlestirme_guvence_raporu)
```
```hint
Üç işlevi aynen birleştir. Uyumlu ve çatışan görev vektörlerinin gerçek model doğruluğunu nasıl değiştirdiğini karşılaştır.
```
:::

::: anlat Sınır
Bu ders küçük bir MLP'nin (tek gizli katman) görev vektörlerinde `TIES` birleştirmesini ve işaret çatışmasını gösterir. "Güvenlik" görevi rakam görüntüleri üzerinde oyuncak bir red kuralıdır, LLM güvenlik hizalaması değildir. Saldırganın ince ayarı ters etiketle ve daha uzun eğitimle kurulmuştur; gerçek saldırılar daha gizli olabilir. Çok katmanlı transformatörlerdeki doğrusal olmayan katman etkileşimleri ölçülmez. DARE ve SLERP küçük bir ağda tek ayarla (p = 0.9, t = 0.5) denenir; büyük modellerdeki davranışları farklı olabilir. SVD tespiti yalnız ilk katmanda ve tek bir k ile yapılır. Ağırlık uzayı denetimlerinin başarısı koşudan koşuya değişir.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Görev vektörü aritmetiği (25 sn).** "İnce ayarlı modelden taban ağırlıkları çıkardığımızda elde edilen $\tau = \theta_{\text{ft}} - \theta_0$ görev vektörü, ağırlık uzayında yeteneğin veya güvenlik hizalamasının yönünü taşır."
2. **`TIES` üçlüsü ve işaret çatışması (35 sn).** "`TIES` küçük değişimleri kırpar (`trim`), her koordinatta baskın işareti seçer (`elect sign`) ve yalnız o işaretle uyuşanları ortalar (`disjoint merge`); ancak daha büyük genlikli ters işaretli bir görev vektörü baskın işareti ele geçirip güvenlik koordinatlarını silebilir."
3. **Ağırlık uzayı güvence kapısı (35 sn).** "Birleştirilmiş modeli yayına almadan önce güvenlik vektörüyle kosinüs benzerliği, işaret çatışma oranı ve baskılanan güvenlik koordinatı oranı (`silinen_guvenlik_orani`) eşiklerle denetlenmelidir."
4. **Soru (25 sn).** "Ağırlık uzayında kosinüs ve işaret çatışması temiz görünen iki adaptör birleştirildiğinde bile neden davranışsal güvenlik testini atlayamayız?"
:::
