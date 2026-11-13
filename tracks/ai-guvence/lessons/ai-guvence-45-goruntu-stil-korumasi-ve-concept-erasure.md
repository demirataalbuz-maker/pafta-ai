---
id: ai-guvence-45
title: Görüntü Stil Koruması ve Concept Erasure · Temsil Uzayında Müdahale
summary: Dik izdüşümle doğrusal kavram silmeyi (concept erasure) kodla, özellik uzayında stil gizleme (style cloaking) kaymasını ölç ve kalıntı kavram izini GPU'da doğrula.
esleme: ai-guvence-06, ai-guvence-14, ai-guvence-37
timeout: 60
---

::: anlat Görüntü aynı görünürken özellik uzayında nasıl başka bir stile dönüşür?
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Küçük bir $L_\infty$ piksel pertürbasyonu görüntünün özellik temsilini hedef bir stil yönüne kaydırarak izinsiz stil taklidini bozar (`style cloaking`) | İlk üç görev: `veri/concept_erasure.json` içindeki **sentetik** özellik vektörleri. Final: GPU'da gerçek MLP kodlayıcısında $L_\infty$ bütçeli `style cloaking` ve dik izdüşümle `concept erasure` | Görüntü sıkıştırma veya yeniden boyutlandırma sonrasında `style cloaking` etkisinin her difüzyon modelinde korunacağını kanıtlamaz |
| Bir temsil vektöründen kavram yönü dik izdüşümle çıkarıldığında (`concept erasure`), o doğrusal yöndeki iç çarpım tam sıfır olur | Dik altuzay projeksiyonu ($v - \frac{v \cdot c}{c \cdot c} c$), kosinüs stil kayması ve artık iz denetimi | Doğrusal kavram silmenin doğrusal olmayan üst katmanlarda kavramın yeniden çıkarılmasını (`nonlinear recovery`) engellediğini garanti etmez |

> [!NOT]
> Görevler `veri/concept_erasure.json` dosyasını okur; dosya sentetiktir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; değişiklikler taşınmaz, **kalıcılık yoktur**. Ekranda ayrı dosya görüntüleyici yoktur; içeriği görmek için `print` kullan. Gizli testler ayrıdır. Final yeni model indirmez ve GPU varsa onu kullanır.

Üretken modellerde fikrî mülkiyet ve içerik güvenliği iki tamamlayıcı temsil uzayı müdahalesine dayanır: **veri sahibinin kendi eserini özellik uzayında gizlemesi (`style cloaking`)** ve **model sahibinin istenmeyen bir kavramı temsil uzayından silmesi (`concept erasure`)**.

**1. Doğrusal `concept erasure` (Dik İzdüşüm / Nullspace Projection):** Temsil vektörü $v \in \mathbb{R}^d$ ve silinmek istenen kavram yönü $c \in \mathbb{R}^d$ ($\|c\|_2 > 0$) verildiğinde, $v$'nin $c$ üzerindeki izdüşümü çıkarılır (Ravfogel vd. 2020; Belrose vd. 2023 `LEACE`; Gandikota vd. 2023):
$$v_{\text{sil}} = v - \frac{v \cdot c}{c \cdot c}\, c$$
Bu işlemden sonra birim kavram yönü $\hat{c} = c / \|c\|_2$ ile iç çarpım $|v_{\text{sil}} \cdot \hat{c}| = 0$ olur; kavram yönüne dik olan tüm özellik bileşenleri ise olduğu gibi korunur.

**2. Özellik uzayında `style cloaking` (Glaze / Nightshade):** Sanatçılar eserlerinin ince ayarda (`fine-tuning`) izinsiz kopyalanmasını önlemek için görüntüye insan gözünün fark edemeyeceği ($\|\delta\|_\infty \le \epsilon$) bir pertürbasyon ekler; öyle ki kodlayıcı (`encoder`) çıktısı $\phi(x + \delta)$ orijinal stilden uzaklaşıp bambaşka bir **hedef stil yönüne** ($s_{\text{hedef}}$) yaklaşsın (Shan vd. 2023 `Glaze`; Shan vd. 2024 `Nightshade`). Başarı, hedef stil yönüyle olan kosinüs benzerliğindeki artışla (`kayma_miktari = sonraki_kosinus - onceki_kosinus`) ölçülür.

**Saldırgan ne dener?** `Style cloaking` piksellerini temizlemek için görüntüye Gauss bulanıklaştırma, JPEG sıkıştırma veya difüzyon tabanlı arındırma (`purification`) uygular; `concept erasure` uygulanan bir modelde ise eşanlamlı istemlerle kavramı dik altuzaydan tekrar uyandırmaya çalışır.

**Savunma neden kırılır?** Kavram yönü $c$ birim vektör sanılıp $c \cdot c$ yerine yalnız $v \cdot c$ ile çıkarma yapılırsa, $\|c\|_2 \ne 1$ olduğunda kavram silinmez; hatta ters yönde aşırı büyütülür.

**Görev 1'de sık tuzaklar:** Paydada `sum(c * c for c in kavram_yonu)` yerine `math.sqrt(...)` kullanmak (birim vektöre bölerken iki kez norm gerekir).

Kaynaklar: [Shan vd. 2023 (Glaze)](https://arxiv.org/abs/2302.04222), [Shan vd. 2024 (Nightshade)](https://arxiv.org/abs/2310.13828), [Belrose vd. 2023 (LEACE)](https://arxiv.org/abs/2306.03819), [Gandikota vd. 2023 (ESD)](https://arxiv.org/abs/2303.07345). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Köprü: ai-guvence-06 $L_p$ pertürbasyon bütçesini, ai-guvence-37 temsil uzayında doğrusal yönleri inceler; bu ders aynı matematiği telif ve kavram koruma amacıyla kullanır.
:::

::: tahmin Dik izdüşüm kavram yönündeki bileşeni nasıl sıfırlar?
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
v = [1.2, 1.6, 0.5, 0.2]
c = [0.6, 0.8, 0.0, 0.0]
alfa = sum(a * b for a, b in zip(v, c)) / sum(b * b for b in c)
v_sil = [round(a - alfa * b, 6) for a, b in zip(v, c)]
print("Katsayı alfa:", alfa)
print("Silinmiş vektör:", v_sil)
print("Kalan iç çarpım:", round(sum(a * b for a, b in zip(v_sil, c)), 6))
```
???
```cikti
Katsayı alfa: 2.0
Silinmiş vektör: [0.0, 0.0, 0.5, 0.2]
Kalan iç çarpım: 0.0
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: son iki koordinat (`0.5, 0.2`) neden hiç değişmedi? Sonra üç kusurlu başlangıç kodunu çalıştır ve her birinin neyi kaçırdığını önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · Dik izdüşümle doğrusal kavram silme
`kavram_projeksiyonu_sil(vektor, kavram_yonu)`: Aynı uzunlukta ($d \ge 1$) iki dolu liste, elemanları bool olmayan sonlu sayı ve `kavram_yonu` L2 normu $> 0$. $\alpha = \frac{v \cdot c}{c \cdot c}$ olmak üzere $v - \alpha c$ vektörünü yeni `float` listesi olarak döndür. Geçersiz girdide veya sıfır normlu `kavram_yonu`nda `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-45")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def kavram_projeksiyonu_sil(vektor, kavram_yonu):
    return [v - c for v, c in zip(vektor, kavram_yonu)]

from ai_guvence_veri import json_yukle
v = json_yukle("veri/concept_erasure.json")
print(kavram_projeksiyonu_sil(v["onceki_vektorler"][0], v["kavram_yonu"]))
```
```test
def sinama1(f):
    import copy, math, random
    def _r(v, c):
        cc = sum(x * x for x in c); a = sum(x * y for x, y in zip(v, c)) / cc
        return [float(x - a * y) for x, y in zip(v, c)]
    def _y(a, b): return isinstance(a, list) and len(a) == len(b) and all(abs(p - q) < 1e-12 for p, q in zip(a, b))
    try:
        v = [1.2, 1.6, 0.5]; c = [0.6, 0.8, 0.0]; old = (list(v), list(c))
        if not _y(f(v, c), [0.0, 0.0, 0.5]) or (v, c) != old: return False
        # Birim olmayan kavram yönü
        if not _y(f([3.0, 4.0], [6.0, 0.0]), [0.0, 4.0]): return False
        # Sıfır vektör girdisi geçerlidir (kavram_yonu sıfır değilse)
        if not _y(f([0.0, 0.0], [1.0, 2.0]), [0.0, 0.0]): return False
        rng = random.Random(45)
        for _ in range(25):
            d = rng.randint(2, 7)
            rv = [rng.uniform(-3, 3) for _ in range(d)]; rc = [rng.uniform(-3, 3) for _ in range(d)]
            out = f(list(rv), list(rc))
            if not _y(out, _r(rv, rc)) or abs(sum(x * y for x, y in zip(out, rc))) > 1e-10: return False
        for bad in ((None, c), (v, None), ([], []), ([1.0, 2.0], [0.0, 0.0]), ([1.0], c), ([True, 1.0, 1.0], c), (v, [float("nan"), 1.0, 0.0])):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
ok(sinama1(kavram_projeksiyonu_sil), "dik izdüşüm, birim olmayan kavram yönü, diklik ve geçersiz girdi")
for ad, mut in [
    ("doğrudan çıkarma", lambda v, c: [a - b for a, b in zip(v, c)]),
    ("paydada norm", lambda v, c: [a - (sum(x * y for x, y in zip(v, c)) / math.sqrt(sum(x * x for x in c))) * b for a, b in zip(v, c)]),
    ("değiştirme", lambda v, c: list(v))
]:
    ok(not sinama1(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(kavram_projeksiyonu_sil, _il.import_module('ai_gercek_ai_guvence_45').referans_kavram_sil, ([1.2, 1.6, 0.5, 0.2], [0.6, 0.8, 0.0, 0.0]), tohum=3636)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def kavram_projeksiyonu_sil(vektor, kavram_yonu):
    if not isinstance(vektor, list) or not isinstance(kavram_yonu, list) or not vektor or len(vektor) != len(kavram_yonu):
        raise ValueError("vektör")
    for x in vektor + kavram_yonu:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x): raise ValueError("sayı")
    cc = sum(c * c for c in kavram_yonu)
    if cc <= 0: raise ValueError("sıfır norm")
    alfa = sum(v * c for v, c in zip(vektor, kavram_yonu)) / cc
    return [float(v - alfa * c) for v, c in zip(vektor, kavram_yonu)]

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v = json_yukle("veri/concept_erasure.json")
    print(kavram_projeksiyonu_sil(v["onceki_vektorler"][0], v["kavram_yonu"]))
```
```hint
`cc = sum(c * c for c in kavram_yonu)` ve `alfa = sum(v * c for v, c in zip(vektor, kavram_yonu)) / cc` hesaplayıp her koordinattan `alfa * c` çıkar.
```
:::

::: anlat Özellik uzayında stil kaydırma (Style Cloaking) ölçümü
Orijinal özellik $h_{\text{önce}}$, gizlenmiş (`cloaked`) özellik $h_{\text{sonra}}$ ve hedef stil yönü $s_{\text{hedef}}$ için:
- `onceki_kosinus`: $\cos(h_{\text{önce}}, s_{\text{hedef}})$
- `sonraki_kosinus`: $\cos(h_{\text{sonra}}, s_{\text{hedef}})$
- `kayma_miktari`: `sonraki_kosinus - onceki_kosinus`
- `ozellik_l2`: $\|h_{\text{sonra}} - h_{\text{önce}}\|_2$

**Görev 2'de sık tuzaklar:** `kayma_miktari` işaretini `onceki - sonraki` olarak ters yazmak.
:::

::: gorev 2 · Stil kaydırma başarısı
`stil_kaydirma_basarisi(orijinal_ozellik, gizlenmis_ozellik, hedef_stil_yonu)`: Üçü de aynı uzunlukta ($d \ge 1$) dolu liste, elemanları bool olmayan sonlu sayı ve üçünün de L2 normu $> 0$. `{"onceki_kosinus": float, "sonraki_kosinus": float, "kayma_miktari": float, "ozellik_l2": float}` döndür. Geçersiz girdide veya sıfır normda `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-45")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def stil_kaydirma_basarisi(orijinal_ozellik, gizlenmis_ozellik, hedef_stil_yonu):
    no = math.sqrt(sum(v * v for v in orijinal_ozellik))
    ng = math.sqrt(sum(v * v for v in gizlenmis_ozellik))
    nh = math.sqrt(sum(v * v for v in hedef_stil_yonu))
    ko = sum(a * b for a, b in zip(orijinal_ozellik, hedef_stil_yonu)) / (no * nh)
    ks = sum(a * b for a, b in zip(gizlenmis_ozellik, hedef_stil_yonu)) / (ng * nh)
    l2 = math.sqrt(sum((a - b) ** 2 for a, b in zip(orijinal_ozellik, gizlenmis_ozellik)))
    return {"onceki_kosinus": ko, "sonraki_kosinus": ks, "kayma_miktari": ko - ks, "ozellik_l2": l2}

from ai_guvence_veri import json_yukle
v = json_yukle("veri/concept_erasure.json")
print(stil_kaydirma_basarisi(v["onceki_vektorler"][0], v["gizlenmis_ornek"], v["hedef_stil_yonu"]))
```
```test
def sinama2(f):
    import copy, math, random
    def _r(o, g, h):
        no = math.sqrt(sum(x * x for x in o)); ng = math.sqrt(sum(x * x for x in g)); nh = math.sqrt(sum(x * x for x in h))
        ko = sum(a * b for a, b in zip(o, h)) / (no * nh); ks = sum(a * b for a, b in zip(g, h)) / (ng * nh)
        l2 = math.sqrt(sum((a - b) ** 2 for a, b in zip(o, g)))
        return {"onceki_kosinus": float(ko), "sonraki_kosinus": float(ks), "kayma_miktari": float(ks - ko), "ozellik_l2": float(l2)}
    def _y(a, b): return isinstance(a, dict) and set(a) == set(b) and all(abs(a[k] - b[k]) < 1e-12 for k in b)
    try:
        o = [1.0, 0.0]; g = [0.0, 2.0]; h = [0.0, 1.0]; old = (list(o), list(g), list(h))
        if not _y(f(o, g, h), {"onceki_kosinus": 0.0, "sonraki_kosinus": 1.0, "kayma_miktari": 1.0, "ozellik_l2": math.sqrt(5.0)}) or (o, g, h) != old:
            return False
        rng = random.Random(4545)
        for _ in range(25):
            d = rng.randint(2, 6)
            ro = [rng.uniform(-2, 2) for _ in range(d)]; rg = [rng.uniform(-2, 2) for _ in range(d)]; rh = [rng.uniform(-2, 2) for _ in range(d)]
            if not _y(f(list(ro), list(rg), list(rh)), _r(ro, rg, rh)): return False
        for bad in ((None, g, h), (o, None, h), (o, g, None), ([], [], []), ([0.0, 0.0], g, h), (o, [0.0, 0.0], h), (o, g, [0.0, 0.0]), ([1.0], g, h), ([True, 1.0], g, h)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
ok(sinama2(stil_kaydirma_basarisi), "önceki/sonraki kosinüs, kayma yönü, L2 mesafe ve geçersiz girdi")
for ad, mut in [
    ("kayma işaret ters", lambda o, g, h: dict(stil_kaydirma_basarisi(o, g, h), kayma_miktari=-stil_kaydirma_basarisi(o, g, h)["kayma_miktari"])),
    ("L2 karesi", lambda o, g, h: dict(stil_kaydirma_basarisi(o, g, h), ozellik_l2=stil_kaydirma_basarisi(o, g, h)["ozellik_l2"] ** 2 + 0.1)),
    ("kosinüs sıfır", lambda o, g, h: dict(stil_kaydirma_basarisi(o, g, h), sonraki_kosinus=0.0))
]:
    ok(not sinama2(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(stil_kaydirma_basarisi, _il.import_module('ai_gercek_ai_guvence_45').referans_stil_kaydirma, ([1.2, 1.6, 0.5, 0.2], [0.2, 0.1, 1.5, 1.1], [0.0, 0.0, 0.8, 0.6]), tohum=3476)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def stil_kaydirma_basarisi(orijinal_ozellik, gizlenmis_ozellik, hedef_stil_yonu):
    if not isinstance(orijinal_ozellik, list) or not isinstance(gizlenmis_ozellik, list) or not isinstance(hedef_stil_yonu, list):
        raise ValueError("liste")
    if not orijinal_ozellik or len(orijinal_ozellik) != len(gizlenmis_ozellik) or len(orijinal_ozellik) != len(hedef_stil_yonu):
        raise ValueError("boyut")
    for v in orijinal_ozellik + gizlenmis_ozellik + hedef_stil_yonu:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise ValueError("sayı")
    no = math.sqrt(sum(v * v for v in orijinal_ozellik))
    ng = math.sqrt(sum(v * v for v in gizlenmis_ozellik))
    nh = math.sqrt(sum(v * v for v in hedef_stil_yonu))
    if no <= 0 or ng <= 0 or nh <= 0: raise ValueError("sıfır norm")
    ko = sum(a * b for a, b in zip(orijinal_ozellik, hedef_stil_yonu)) / (no * nh)
    ks = sum(a * b for a, b in zip(gizlenmis_ozellik, hedef_stil_yonu)) / (ng * nh)
    l2 = math.sqrt(sum((a - b) ** 2 for a, b in zip(orijinal_ozellik, gizlenmis_ozellik)))
    return {"onceki_kosinus": float(ko), "sonraki_kosinus": float(ks), "kayma_miktari": float(ks - ko), "ozellik_l2": float(l2)}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v = json_yukle("veri/concept_erasure.json")
    print(stil_kaydirma_basarisi(v["onceki_vektorler"][0], v["gizlenmis_ornek"], v["hedef_stil_yonu"]))
```
```hint
`kayma_miktari = sonraki_kosinus - onceki_kosinus` olarak hesapla ve üç vektörün de normunun sıfırdan büyük olduğunu doğrula.
```
:::

::: anlat Kavram silme ve koruma denetim raporu
Silme işleminin ne kadar iz bıraktığı ve geri kalan özellikleri ne kadar değiştirdiği birim kavram yönü $\hat{c} = c / \|c\|_2$ üzerinden ölçülür:
- Her vektör $v$ için kavram izi büyüklüğü $|v \cdot \hat{c}|$'dir.
- `onceki_ort_iz` ve `sonraki_ort_iz`: Önceki ve sonraki vektörlerin ortalama kavram izi.
- `max_artik_iz`: Sonraki vektörler içindeki en büyük $|w \cdot \hat{c}|$ değeri.
- `ort_koruma_l2`: Eşleşen $(v_i, w_i)$ çiftleri arasındaki Öklidyen uzaklıkların $\|v_i - w_i\|_2$ ortalaması.
- `tam_silindi`: `max_artik_iz <= artik_esik` ise `True`, değilse `False`.

**Görev 3'te sık tuzaklar:** Kavram izini hesaplarken $c$'yi birim vektöre bölmemek veya mutlak değer `abs(...)` almamak.
:::

::: gorev 3 · Kavram silme ve koruma raporu
`silme_koruma_raporu(onceki_vektorler, sonraki_vektorler, kavram_yonu, artik_esik)`: `onceki_vektorler` ve `sonraki_vektorler` aynı sayıda ($m \ge 1$) ve `kavram_yonu` ile aynı boyutta ($d \ge 1$) vektör listeleri; `kavram_yonu` L2 normu $> 0$; `artik_esik >= 0`; tüm sayılar bool olmayan sonlu sayı. `{"onceki_ort_iz": float, "sonraki_ort_iz": float, "max_artik_iz": float, "ort_koruma_l2": float, "tam_silindi": bool}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-45")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def silme_koruma_raporu(onceki_vektorler, sonraki_vektorler, kavram_yonu, artik_esik):
    iz = [abs(sum(v * c for v, c in zip(vec, kavram_yonu))) for vec in onceki_vektorler]
    return {"onceki_ort_iz": sum(iz) / len(iz), "sonraki_ort_iz": 1.0, "max_artik_iz": 1.0, "ort_koruma_l2": 0.0, "tam_silindi": True}

from ai_guvence_veri import json_yukle
v = json_yukle("veri/concept_erasure.json")
print(silme_koruma_raporu(v["onceki_vektorler"], v["onceki_vektorler"], v["kavram_yonu"], v["artik_esik"]))
```
```test
def sinama3(f):
    import copy, math, random
    def _r(ov, sv, c, ae):
        nc = math.sqrt(sum(x * x for x in c)); u = [x / nc for x in c]
        io = [abs(sum(a * b for a, b in zip(v, u))) for v in ov]
        is_ = [abs(sum(a * b for a, b in zip(w, u))) for w in sv]
        l2 = [math.sqrt(sum((a - b) ** 2 for a, b in zip(v, w))) for v, w in zip(ov, sv)]
        ma = float(max(is_))
        return {"onceki_ort_iz": float(sum(io) / len(io)), "sonraki_ort_iz": float(sum(is_) / len(is_)), "max_artik_iz": ma, "ort_koruma_l2": float(sum(l2) / len(l2)), "tam_silindi": bool(ma <= ae)}
    def _y(a, b):
        if not isinstance(a, dict) or set(a) != set(b) or a["tam_silindi"] is not b["tam_silindi"]: return False
        return all(abs(a[k] - b[k]) < 1e-12 for k in ("onceki_ort_iz", "sonraki_ort_iz", "max_artik_iz", "ort_koruma_l2"))
    try:
        ov = [[3.0, 4.0], [-6.0, -8.0]]; sv = [[0.0, 0.0], [0.0, 0.0]]; c = [3.0, 4.0]; old = (copy.deepcopy(ov), copy.deepcopy(sv), list(c))
        if not _y(f(ov, sv, c, 1e-6), {"onceki_ort_iz": 7.5, "sonraki_ort_iz": 0.0, "max_artik_iz": 0.0, "ort_koruma_l2": 7.5, "tam_silindi": True}) or (ov, sv, c) != old:
            return False
        if f(ov, ov, c, 1.0)["tam_silindi"] is not False: return False
        for esik, silindi in ((0.499, False), (0.5, True), (0.501, True)):
            if f([[1.0, 2.0]], [[0.5, 2.0]], [1.0, 0.0], esik)["tam_silindi"] is not silindi:
                return False
        rng = random.Random(4546)
        for _ in range(25):
            m, d = rng.randint(1, 5), rng.randint(2, 6)
            rov = [[rng.uniform(-2, 2) for _ in range(d)] for _ in range(m)]
            rsv = [[rng.uniform(-2, 2) for _ in range(d)] for _ in range(m)]
            rc = [rng.uniform(-2, 2) for _ in range(d)]; rae = rng.uniform(0.1, 2.0)
            if not _y(f([list(x) for x in rov], [list(x) for x in rsv], list(rc), rae), _r(rov, rsv, rc, rae)): return False
        for bad in ((None, sv, c, 0.1), (ov, None, c, 0.1), ([], [], c, 0.1), (ov, [sv[0]], c, 0.1), (ov, sv, [0.0, 0.0], 0.1), (ov, sv, c, -0.1), (ov, sv, c, True), ([[1.0]], [[1.0]], c, 0.1)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
ok(sinama3(silme_koruma_raporu), "birim kavram izi, maksimum artık iz, tam silindi kararı ve geçersiz girdi")
for ad, mut in [
    ("hep silindi", lambda o, s, c, a: dict(silme_koruma_raporu(o, s, c, a), tam_silindi=True)),
    ("artık iz sıfır", lambda o, s, c, a: dict(silme_koruma_raporu(o, s, c, a), max_artik_iz=0.0)),
    ("L2 unutuldu", lambda o, s, c, a: dict(silme_koruma_raporu(o, s, c, a), ort_koruma_l2=0.0))
]:
    ok(not sinama3(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(silme_koruma_raporu, _il.import_module('ai_gercek_ai_guvence_45').referans_silme_raporu, ([[1.2, 1.6, 0.5, 0.2], [0.9, 1.2, -0.3, 0.4], [-0.6, -0.8, 0.7, 0.1]], [[0.0, 0.0, 0.5, 0.2], [0.0, 0.0, -0.3, 0.4], [0.0, 0.0, 0.7, 0.1]], [0.6, 0.8, 0.0, 0.0], 1e-06), tohum=3194)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def silme_koruma_raporu(onceki_vektorler, sonraki_vektorler, kavram_yonu, artik_esik):
    if not isinstance(onceki_vektorler, list) or not isinstance(sonraki_vektorler, list) or not isinstance(kavram_yonu, list):
        raise ValueError("liste")
    if not onceki_vektorler or len(onceki_vektorler) != len(sonraki_vektorler) or not kavram_yonu:
        raise ValueError("boyut")
    if isinstance(artik_esik, bool) or not isinstance(artik_esik, (int, float)) or not math.isfinite(artik_esik) or artik_esik < 0:
        raise ValueError("eşik")
    for x in kavram_yonu:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x): raise ValueError("sayı")
    nc = math.sqrt(sum(c * c for c in kavram_yonu))
    if nc <= 0: raise ValueError("sıfır norm")
    d = len(kavram_yonu)
    for v, w in zip(onceki_vektorler, sonraki_vektorler):
        if not isinstance(v, list) or not isinstance(w, list) or len(v) != d or len(w) != d: raise ValueError("vektör")
        for x in v + w:
            if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x): raise ValueError("sayı")
    u = [c / nc for c in kavram_yonu]
    io = [abs(sum(a * b for a, b in zip(v, u))) for v in onceki_vektorler]
    is_ = [abs(sum(a * b for a, b in zip(w, u))) for w in sonraki_vektorler]
    l2 = [math.sqrt(sum((a - b) ** 2 for a, b in zip(v, w))) for v, w in zip(onceki_vektorler, sonraki_vektorler)]
    ma = float(max(is_))
    return {
        "onceki_ort_iz": float(sum(io) / len(io)),
        "sonraki_ort_iz": float(sum(is_) / len(is_)),
        "max_artik_iz": ma,
        "ort_koruma_l2": float(sum(l2) / len(l2)),
        "tam_silindi": bool(ma <= artik_esik)
    }

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v = json_yukle("veri/concept_erasure.json")
    sonraki = [ [0.0, 0.0, x[2], x[3]] for x in v["onceki_vektorler"] ]
    print(silme_koruma_raporu(v["onceki_vektorler"], sonraki, v["kavram_yonu"], v["artik_esik"]))
```
```hint
Önce `u = [c / nc for c in kavram_yonu]` ile birim kavram vektörünü oluştur; her vektörün izini `abs(sum(a * b for a, b in zip(vec, u)))` ile hesapla.
```
:::

::: anlat Artık izin anlamı
Örneğin kavram yönü [1, 0] ve işlem sonrası vektör [0.5, 2] ise artık iz 0.5 olur. Eşik 0.5 olduğunda rapor kabul verir, eşik 0.499 olduğunda reddeder. Bu karar yalnız verilen vektörlerde seçilen doğrusal yönü ölçer. Başka yönler veya doğrusal olmayan bir sınıflandırıcı aynı kavramla ilgili bilgi taşıyabilir.
:::

::: anlat Hata vitrini · çalışmış yanlış rapor
Yazar, kusurlu başlangıç kodlarını görünür sentetik veriyle gerçekten çalıştırdı ve sonucu `outputs/yeni-ai-guvence-45/gorunur-run-1.json` dosyasına kaydetti. Kusurlu kod `[1.2, 1.6, 0.5, 0.2]` vektöründen kavram yönünü doğrudan çıkardığı için `[0.6, 0.8, 0.5, 0.2]` bırakır (kavramın yarısı hâlâ durmaktadır), stil kaymasını `-0.7419` ile ters işaretli hesaplar ve `max_artik_iz=1.0` iken bile `tam_silindi=True` döndürür. Doğru kod ise kavram bileşenini `[0.0, 0.0, 0.5, 0.2]` olarak tam sıfırlar ve stil kaymasını `+0.7419` olarak raporlar.

Bu kaydedilmiş bir hesaplama çıktısıdır, model yanıtı değildir ve rapor sentetiktir. `max_artik_iz=1.0` olduğu hâlde `tam_silindi=True` raporuna güvenen bir içerik filtresi neyi kaçırmış olur? Kendi cümlenle açıkla. Gerçek finaldeki ölçüm ayrıca üretilir; bu sayılar onun yerine konmaz.
:::

::: anlat Gerçek deney: Görüntü kodlayıcısında style cloaking ve concept erasure
Final, `load_digits` üzerinde eğitilen bir MLP kodlayıcısında 48 gerçek test görüntüsünü alır:
1. **`Style Cloaking`:** Görüntülere $\|\delta\|_\infty \le 0.15$ bütçesi içinde gradyan tabanlı bir stil pelerini uygulanarak gizli katman özelliklerinin hedef stil merkezine doğru nasıl kaydığı **senin `stil_kaydirma_basarisi` işlevinle** ölçülür.
2. **`Concept Erasure`:** Gizli katman vektörlerinden sınıf farkı kavram yönü **senin `kavram_projeksiyonu_sil` işlevinle** dik izdüşümle silinir ve kalıntı iz **senin `silme_koruma_raporu` işlevinle** doğrulanır.

Kalıntı izin sıfır çıkması silmenin **işe yaradığını** göstermez; yalnız izdüşümün doğru hesaplandığını gösterir. Bu yüzden final üç **davranış** ölçümü de yapar:
- **Gizleme davranışı:** Orijinal sınıflandırıcı, gizlenmiş görüntülerden 1 olmayanları ne sıklıkta "1" görüyor? Doğruluğu ne kadar düşüyor?
- **Silmeden sonra kavram geri okunabiliyor mu?** 0 ile 1 görüntülerinin gizli temsilleri silinir. Ardından **sıfırdan iki yeni sonda** eğitilip 0/1 ayrımı ölçülür: biri doğrusal, biri tek gizli katmanlı MLP. Saldırgan da silinmiş temsiller üzerinde kendi sondasını eğitebilir.
- **Ağırlık projeksiyonuyla silme:** Silme, temsillere değil sınıflandırıcının kendisine uygulanır. Başlık ağırlıkları kavram yönüne dik hâle getirilir: $W \leftarrow W(I - uu^\top)$. Ardından 0/1 doğruluğu ve diğer rakamların doğruluğu ölçülür.

Yazarın dört GPU koşusunda (her biri birkaç saniye) şu sonuçlar alındı:
- **Gizleme:** Sınıf-1 stil yönüne kosinüs kayması +0.07–0.09. Orijinal sınıflandırıcı 1 olmayan görüntülerin %2–5'i yerine %3–23'ünü "1" gördü; doğruluk ~0.1 düştü. Etki koşudan koşuya çok değişir. L∞ = 0.15 bu 8×8 görüntülerde gözle görülür bir pertürbasyondur; gerçek Glaze/Nightshade çok daha küçük bütçelerle ve büyük görüntülerde çalışır.
- **Doğrusal silme doğrusal sondayı durdurdu, MLP sondayı durdurmadı.** Doğrusal sondanın 0/1 doğruluğu 0.98–0.99'dan 0.27–0.53'e indi (şans 0.5). Silinmiş temsiller üzerinde eğitilen MLP sonda ise 0/1'i hâlâ **0.96–0.99** doğrulukla ayırdı. Tek bir doğrusal yönü kaldırmak, kavramı doğrusal olmayan bir okuyucudan gizlemez (LEACE ve benzeri yöntemlerin bilinen sınırı).
- **Ağırlık projeksiyonu hedefli çalıştı.** Başlık ağırlıkları kavram yönüne dik hâle getirilince 0/1 doğruluğu 0.90–0.92'den **0.05–0.22**'ye düştü; diğer rakamların doğruluğu 0.92–0.94'te kaldı. Model artık 0 ile 1'i birbirinden ayıramaz, ama başka hiçbir yeteneğini kaybetmez. Bu, "kavram silme"nin davranışta ölçülebilir hâlidir.

**Güvenlik yönü — taklitçi gizlemeyi arındırabilir mi?** Stil koruması ancak taklitçinin onu kaldıramadığı ölçüde koruma sağlar. Gizlenmiş görüntüler, gizlemeyi bilmeyen üç basit işlemden geçirilir: 3×3 bulanıklaştırma, 1/16 düzeyine nicemleme ve 4×4'e küçültüp geri büyütme. Her işlem temiz görüntülere de uygulanır ve gizlemenin özellik uzayındaki kaymasının ne kadarının kaldığı ölçülür. Küçültüp büyütme kaymanın yaklaşık üçte ikisini siler, ama 8×8 görüntüde rakamın kendisini de bozar (temiz doğruluk ~0.94'ten 0.5–0.7'ye iner). Bulanıklaştırma kaymanın yarısını silerken doğruluğu ~0.8'e indirir. Nicemleme gizlemeye neredeyse dokunmaz. Bu çözünürlükte koruma ile içerik birbirinden ayrılamaz. Yüksek çözünürlüklü gerçek eserlerde ise gürültü ekleyip yeniden üretmek içeriği koruyarak korumayı büyük ölçüde kaldırır (Hönig vd. 2024): stil koruması bir garanti değil, saldırganın maliyetini artıran bir önlemdir.

**Kanıt dosyasını oku:** Soru 1: `silme_raporu.tam_silindi` doğruyken `silme_sondalari.mlp_sonra` neden hâlâ yüksek? Soru 2: `silme_raporu` içinde `onceki_ort_iz` ile `ort_koruma_l2` neden birbirine eşit çıktı (Pisagor teoremini düşün)? Soru 3: Ağırlık projeksiyonu sonrası 0/1 doğruluğunun şansın (0.5) çok altına inmesi, modelin 0 ve 1 görüntülerini hangi sınıflara gönderdiğine dair ne söyler? Cevabını tezgâhta yorum olarak yaz; otomatik test bu serbest açıklamayı puanlamaz.
:::

::: gorev Gerçek deney · Özellik uzayında style cloaking ve dik izdüşümle kavram silme
Önceki üç görevin `kavram_projeksiyonu_sil`, `stil_kaydirma_basarisi` ve `silme_koruma_raporu` işlevlerini birleştir. Çalıştır gerçek tabloyu gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 180
```
```starter
import ai_lab
import math
def kavram_projeksiyonu_sil(vektor, kavram_yonu):
    return [v - c for v, c in zip(vektor, kavram_yonu)]
def stil_kaydirma_basarisi(orijinal_ozellik, gizlenmis_ozellik, hedef_stil_yonu):
    no = math.sqrt(sum(v * v for v in orijinal_ozellik))
    ng = math.sqrt(sum(v * v for v in gizlenmis_ozellik))
    nh = math.sqrt(sum(v * v for v in hedef_stil_yonu))
    ko = sum(a * b for a, b in zip(orijinal_ozellik, hedef_stil_yonu)) / (no * nh)
    ks = sum(a * b for a, b in zip(gizlenmis_ozellik, hedef_stil_yonu)) / (ng * nh)
    l2 = math.sqrt(sum((a - b) ** 2 for a, b in zip(orijinal_ozellik, gizlenmis_ozellik)))
    return {"onceki_kosinus": ko, "sonraki_kosinus": ks, "kayma_miktari": ko - ks, "ozellik_l2": l2}
def silme_koruma_raporu(onceki_vektorler, sonraki_vektorler, kavram_yonu, artik_esik):
    iz = [abs(sum(v * c for v, c in zip(vec, kavram_yonu))) for vec in onceki_vektorler]
    return {"onceki_ort_iz": sum(iz) / len(iz), "sonraki_ort_iz": 1.0, "max_artik_iz": 1.0, "ort_koruma_l2": 0.0, "tam_silindi": True}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_45 as D
    D.goster(kavram_projeksiyonu_sil, stil_kaydirma_basarisi, silme_koruma_raporu)
```
```test
import ai_lab, math
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('referans_kavram_sil', 'referans_stil_kaydirma', 'referans_silme_raporu', 'kanit_yaz', '_yakin'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
kavram_projeksiyonu_sil = need("kavram_projeksiyonu_sil")
stil_kaydirma_basarisi = need("stil_kaydirma_basarisi")
silme_koruma_raporu = need("silme_koruma_raporu")
def sinama1(f):
    import copy, math, random
    def _r(v, c):
        cc = sum(x * x for x in c); a = sum(x * y for x, y in zip(v, c)) / cc
        return [float(x - a * y) for x, y in zip(v, c)]
    def _y(a, b): return isinstance(a, list) and len(a) == len(b) and all(abs(p - q) < 1e-12 for p, q in zip(a, b))
    try:
        v = [1.2, 1.6, 0.5]; c = [0.6, 0.8, 0.0]; old = (list(v), list(c))
        if not _y(f(v, c), [0.0, 0.0, 0.5]) or (v, c) != old: return False
        if not _y(f([3.0, 4.0], [6.0, 0.0]), [0.0, 4.0]): return False
        rng = random.Random(45)
        for _ in range(25):
            d = rng.randint(2, 7)
            rv = [rng.uniform(-3, 3) for _ in range(d)]; rc = [rng.uniform(-3, 3) for _ in range(d)]
            out = f(list(rv), list(rc))
            if not _y(out, _r(rv, rc)) or abs(sum(x * y for x, y in zip(out, rc))) > 1e-10: return False
        for bad in ((None, c), ([1.0, 2.0], [0.0, 0.0]), ([1.0], c), ([True, 1.0, 1.0], c)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama1(kavram_projeksiyonu_sil), "dik izdüşüm, birim olmayan kavram yönü, diklik ve geçersiz girdi")
for ad, mut in [
    ("doğrudan çıkarma", lambda v, c: [a - b for a, b in zip(v, c)]),
    ("paydada norm", lambda v, c: [a - (sum(x * y for x, y in zip(v, c)) / math.sqrt(sum(x * x for x in c))) * b for a, b in zip(v, c)]),
    ("değiştirme", lambda v, c: list(v))
]:
    kontrol(not sinama1(mut), "mutant reddedildi: " + ad)
def sinama2(f):
    import copy, math, random
    def _r(o, g, h):
        no = math.sqrt(sum(x * x for x in o)); ng = math.sqrt(sum(x * x for x in g)); nh = math.sqrt(sum(x * x for x in h))
        ko = sum(a * b for a, b in zip(o, h)) / (no * nh); ks = sum(a * b for a, b in zip(g, h)) / (ng * nh)
        l2 = math.sqrt(sum((a - b) ** 2 for a, b in zip(o, g)))
        return {"onceki_kosinus": float(ko), "sonraki_kosinus": float(ks), "kayma_miktari": float(ks - ko), "ozellik_l2": float(l2)}
    def _y(a, b): return isinstance(a, dict) and set(a) == set(b) and all(abs(a[k] - b[k]) < 1e-12 for k in b)
    try:
        o = [1.0, 0.0]; g = [0.0, 2.0]; h = [0.0, 1.0]; old = (list(o), list(g), list(h))
        if not _y(f(o, g, h), {"onceki_kosinus": 0.0, "sonraki_kosinus": 1.0, "kayma_miktari": 1.0, "ozellik_l2": math.sqrt(5.0)}) or (o, g, h) != old:
            return False
        rng = random.Random(4545)
        for _ in range(25):
            d = rng.randint(2, 6)
            ro = [rng.uniform(-2, 2) for _ in range(d)]; rg = [rng.uniform(-2, 2) for _ in range(d)]; rh = [rng.uniform(-2, 2) for _ in range(d)]
            if not _y(f(list(ro), list(rg), list(rh)), _r(ro, rg, rh)): return False
        for bad in ((None, g, h), ([0.0, 0.0], g, h), (o, [0.0, 0.0], h), (o, g, [0.0, 0.0]), ([True, 1.0], g, h)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama2(stil_kaydirma_basarisi), "önceki/sonraki kosinüs, kayma yönü, L2 mesafe ve geçersiz girdi")
for ad, mut in [
    ("kayma işaret ters", lambda o, g, h: dict(stil_kaydirma_basarisi(o, g, h), kayma_miktari=-stil_kaydirma_basarisi(o, g, h)["kayma_miktari"])),
    ("L2 karesi", lambda o, g, h: dict(stil_kaydirma_basarisi(o, g, h), ozellik_l2=stil_kaydirma_basarisi(o, g, h)["ozellik_l2"] ** 2 + 0.1)),
    ("kosinüs sıfır", lambda o, g, h: dict(stil_kaydirma_basarisi(o, g, h), sonraki_kosinus=0.0))
]:
    kontrol(not sinama2(mut), "mutant reddedildi: " + ad)
def sinama3(f):
    import copy, math, random
    def _r(ov, sv, c, ae):
        nc = math.sqrt(sum(x * x for x in c)); u = [x / nc for x in c]
        io = [abs(sum(a * b for a, b in zip(v, u))) for v in ov]
        is_ = [abs(sum(a * b for a, b in zip(w, u))) for w in sv]
        l2 = [math.sqrt(sum((a - b) ** 2 for a, b in zip(v, w))) for v, w in zip(ov, sv)]
        ma = float(max(is_))
        return {"onceki_ort_iz": float(sum(io) / len(io)), "sonraki_ort_iz": float(sum(is_) / len(is_)), "max_artik_iz": ma, "ort_koruma_l2": float(sum(l2) / len(l2)), "tam_silindi": bool(ma <= ae)}
    def _y(a, b):
        if not isinstance(a, dict) or set(a) != set(b) or a["tam_silindi"] is not b["tam_silindi"]: return False
        return all(abs(a[k] - b[k]) < 1e-12 for k in ("onceki_ort_iz", "sonraki_ort_iz", "max_artik_iz", "ort_koruma_l2"))
    try:
        ov = [[3.0, 4.0], [-6.0, -8.0]]; sv = [[0.0, 0.0], [0.0, 0.0]]; c = [3.0, 4.0]; old = (copy.deepcopy(ov), copy.deepcopy(sv), list(c))
        if not _y(f(ov, sv, c, 1e-6), {"onceki_ort_iz": 7.5, "sonraki_ort_iz": 0.0, "max_artik_iz": 0.0, "ort_koruma_l2": 7.5, "tam_silindi": True}) or (ov, sv, c) != old:
            return False
        if f(ov, ov, c, 1.0)["tam_silindi"] is not False: return False
        for esik, silindi in ((0.499, False), (0.5, True), (0.501, True)):
            if f([[1.0, 2.0]], [[0.5, 2.0]], [1.0, 0.0], esik)["tam_silindi"] is not silindi:
                return False
        rng = random.Random(4546)
        for _ in range(25):
            m, d = rng.randint(1, 5), rng.randint(2, 6)
            rov = [[rng.uniform(-2, 2) for _ in range(d)] for _ in range(m)]
            rsv = [[rng.uniform(-2, 2) for _ in range(d)] for _ in range(m)]
            rc = [rng.uniform(-2, 2) for _ in range(d)]; rae = rng.uniform(0.1, 2.0)
            if not _y(f([list(x) for x in rov], [list(x) for x in rsv], list(rc), rae), _r(rov, rsv, rc, rae)): return False
        for bad in ((None, sv, c, 0.1), (ov, [sv[0]], c, 0.1), (ov, sv, [0.0, 0.0], 0.1), (ov, sv, c, -0.1), (ov, sv, c, True)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama3(silme_koruma_raporu), "birim kavram izi, maksimum artık iz, tam silindi kararı ve geçersiz girdi")
for ad, mut in [
    ("hep silindi", lambda o, s, c, a: dict(silme_koruma_raporu(o, s, c, a), tam_silindi=True)),
    ("artık iz sıfır", lambda o, s, c, a: dict(silme_koruma_raporu(o, s, c, a), max_artik_iz=0.0)),
    ("L2 unutuldu", lambda o, s, c, a: dict(silme_koruma_raporu(o, s, c, a), ort_koruma_l2=0.0))
]:
    kontrol(not sinama3(mut), "mutant reddedildi: " + ad)
# farksal tarama (final)
import importlib as _il
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_R = _il.import_module('sandbox.ai_gercek_ai_guvence_45')
for _ad, _ref, _taban, _toh in (
    ('kavram_projeksiyonu_sil', 'referans_kavram_sil', ([1.2, 1.6, 0.5, 0.2], [0.6, 0.8, 0.0, 0.0]), 4158),
    ('stil_kaydirma_basarisi', 'referans_stil_kaydirma', ([1.2, 1.6, 0.5, 0.2], [0.2, 0.1, 1.5, 1.1], [0.0, 0.0, 0.8, 0.6]), 3998),
    ('silme_koruma_raporu', 'referans_silme_raporu', ([[1.2, 1.6, 0.5, 0.2], [0.9, 1.2, -0.3, 0.4], [-0.6, -0.8, 0.7, 0.1]], [[0.0, 0.0, 0.5, 0.2], [0.0, 0.0, -0.3, 0.4], [0.0, 0.0, 0.7, 0.1]], [0.6, 0.8, 0.0, 0.0], 1e-06), 3716),
):
    _t, _g = _ff(need(_ad), getattr(_R, _ref), _taban, tohum=_toh)
    kontrol(_t, "farksal tarama (" + _ad + "): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
if not all(checks): stop()
from sandbox import ai_gercek_ai_guvence_45 as D
try: r = D.deney(kavram_projeksiyonu_sil, stil_kaydirma_basarisi, silme_koruma_raporu)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r["sil_ayni"], "gerçek aktivasyonlarda dik kavram silme bağımsız hesapla aynı")
kontrol(r["stil_ayni"], "gerçek aktivasyonlarda stil kaydırma ölçümü bağımsız hesapla aynı")
kontrol(r["rapor_ayni"], "gerçek aktivasyonlarda silme koruma raporu bağımsız hesapla aynı")
kontrol(r["ort_stil_kaymasi"] > 0, "style cloaking özellikleri hedef stil yönüne kaydırdı")
kontrol(r["silme_raporu"]["tam_silindi"] is True, "dik izdüşüm sonrası kavram izi eşik altına indi")
kontrol(r["linf_max"] <= r["ayarlar"]["eps"] + 1e-5, "style cloaking L∞ bütçesi aşılmadı")
kontrol(r["arindirma_odunlesimi"], "en etkili arındırma gizleme kaymasının yarısından fazlasını sildi ama temiz doğruluğu da düşürdü; nicemleme gizlemeye dokunmadı: " + str({a: round(v["kalan_kayma_orani"], 2) for a, v in r["arindirma"].items()}))
s = r["silme_sondalari"]
kontrol(s["dogrusal_sonra"] < 0.7 and s["dogrusal_once"] > 0.9, "doğrusal silme yeni bir doğrusal sondanın 0/1 ayrımını bozdu: %.3f -> %.3f" % (s["dogrusal_once"], s["dogrusal_sonra"]))
kontrol(s["mlp_sonra"] > 0.85, "doğrusal olmayan MLP sonda silinmiş temsillerden kavramı yine okudu: %.3f (doğrusal silmenin sınırı)" % s["mlp_sonra"])
a = r["agirlik_projeksiyonu"]
kontrol(a["sonra"]["0_1_dogrulugu"] < 0.5 and a["sonra"]["diger_rakamlar"] >= a["once"]["diger_rakamlar"] - 0.05,
        "ağırlık projeksiyonu 0/1 ayrımını sildi (%.3f -> %.3f), diğer rakamları korudu (%.3f -> %.3f)" % (
            a["once"]["0_1_dogrulugu"], a["sonra"]["0_1_dogrulugu"], a["once"]["diger_rakamlar"], a["sonra"]["diger_rakamlar"]))
ai_lab.kanit_yaz("ai-guvence-45-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-guvence-45", "deney": r})
```
```solution
import ai_lab
import math
def kavram_projeksiyonu_sil(vektor, kavram_yonu):
    if not isinstance(vektor, list) or not isinstance(kavram_yonu, list) or not vektor or len(vektor) != len(kavram_yonu):
        raise ValueError("vektör")
    for x in vektor + kavram_yonu:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x): raise ValueError("sayı")
    cc = sum(c * c for c in kavram_yonu)
    if cc <= 0: raise ValueError("sıfır norm")
    alfa = sum(v * c for v, c in zip(vektor, kavram_yonu)) / cc
    return [float(v - alfa * c) for v, c in zip(vektor, kavram_yonu)]
def stil_kaydirma_basarisi(orijinal_ozellik, gizlenmis_ozellik, hedef_stil_yonu):
    if not isinstance(orijinal_ozellik, list) or not isinstance(gizlenmis_ozellik, list) or not isinstance(hedef_stil_yonu, list):
        raise ValueError("liste")
    if not orijinal_ozellik or len(orijinal_ozellik) != len(gizlenmis_ozellik) or len(orijinal_ozellik) != len(hedef_stil_yonu):
        raise ValueError("boyut")
    for v in orijinal_ozellik + gizlenmis_ozellik + hedef_stil_yonu:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise ValueError("sayı")
    no = math.sqrt(sum(v * v for v in orijinal_ozellik))
    ng = math.sqrt(sum(v * v for v in gizlenmis_ozellik))
    nh = math.sqrt(sum(v * v for v in hedef_stil_yonu))
    if no <= 0 or ng <= 0 or nh <= 0: raise ValueError("sıfır norm")
    ko = sum(a * b for a, b in zip(orijinal_ozellik, hedef_stil_yonu)) / (no * nh)
    ks = sum(a * b for a, b in zip(gizlenmis_ozellik, hedef_stil_yonu)) / (ng * nh)
    l2 = math.sqrt(sum((a - b) ** 2 for a, b in zip(orijinal_ozellik, gizlenmis_ozellik)))
    return {"onceki_kosinus": float(ko), "sonraki_kosinus": float(ks), "kayma_miktari": float(ks - ko), "ozellik_l2": float(l2)}
def silme_koruma_raporu(onceki_vektorler, sonraki_vektorler, kavram_yonu, artik_esik):
    if not isinstance(onceki_vektorler, list) or not isinstance(sonraki_vektorler, list) or not isinstance(kavram_yonu, list):
        raise ValueError("liste")
    if not onceki_vektorler or len(onceki_vektorler) != len(sonraki_vektorler) or not kavram_yonu:
        raise ValueError("boyut")
    if isinstance(artik_esik, bool) or not isinstance(artik_esik, (int, float)) or not math.isfinite(artik_esik) or artik_esik < 0:
        raise ValueError("eşik")
    for x in kavram_yonu:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x): raise ValueError("sayı")
    nc = math.sqrt(sum(c * c for c in kavram_yonu))
    if nc <= 0: raise ValueError("sıfır norm")
    d = len(kavram_yonu)
    for v, w in zip(onceki_vektorler, sonraki_vektorler):
        if not isinstance(v, list) or not isinstance(w, list) or len(v) != d or len(w) != d: raise ValueError("vektör")
        for x in v + w:
            if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x): raise ValueError("sayı")
    u = [c / nc for c in kavram_yonu]
    io = [abs(sum(a * b for a, b in zip(v, u))) for v in onceki_vektorler]
    is_ = [abs(sum(a * b for a, b in zip(w, u))) for w in sonraki_vektorler]
    l2 = [math.sqrt(sum((a - b) ** 2 for a, b in zip(v, w))) for v, w in zip(onceki_vektorler, sonraki_vektorler)]
    ma = float(max(is_))
    return {
        "onceki_ort_iz": float(sum(io) / len(io)),
        "sonraki_ort_iz": float(sum(is_) / len(is_)),
        "max_artik_iz": ma,
        "ort_koruma_l2": float(sum(l2) / len(l2)),
        "tam_silindi": bool(ma <= artik_esik)
    }
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_45 as D
    D.goster(kavram_projeksiyonu_sil, stil_kaydirma_basarisi, silme_koruma_raporu)
```
```hint
Üç işlevi aynen birleştir. Style cloaking kaymasını ve dik izdüşüm sonrası kalan kavram izini incele.
```
:::

::: anlat Sınır
Bu ders tek katmanlı özellik uzayında doğrusal kavram silmeyi (`concept erasure`), sınıflandırıcı başlığında ağırlık projeksiyonunu ve $L_\infty$ bütçeli `style cloaking` kaymasını gösterir. Gerçek deney 8×8 rakamlar ve küçük bir MLP kullanır; difüzyon modeli ve gerçek sanat stili yoktur. Gizleme bütçesi gerçek Glaze/Nightshade bütçelerinden büyüktür. Ölçümler, doğrusal silmenin doğrusal olmayan okuyuculara karşı korumadığını gösterir; çok katmanlı difüzyon modellerinde kavram yeniden üretimini engellediğini kanıtlamaz.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Veri tarafında `style cloaking` (30 sn).** "Görüntüye $L_\infty$ bütçeli küçük bir pertürbasyon ekleyip özellik uzayında hedef stil yönüne kosinüs kayması yarattığımızda, insan gözü aynı rakamı görürken kodlayıcı başka bir stil temsiline kayar."
2. **Model tarafında doğrusal `concept erasure` (35 sn).** "Özellik vektöründen kavram yönü $u$'daki dik izdüşümü $v - (v\cdot u)u$ çıkardığımızda doğrusal kavram izi sıfırlanır ve dik bileşenlerdeki görev doğruluğu büyük ölçüde korunur."
3. **Doğrusal olmayan geri kazanım sınırı (30 sn).** "Tek bir doğrusal yönü silmek kavram bilgisinin tamamını yok etmez; deneydeki doğrusal olmayan MLP okuyucu kalan özelliklerden kavramı yeniden çıkarabilir."
4. **Soru (25 sn).** "Bir modelde kavramın gerçekten silindiğini iddia etmek için yalnız doğrusal sonda (`linear probe`) sıfırlanması neden yetmez?"
:::
