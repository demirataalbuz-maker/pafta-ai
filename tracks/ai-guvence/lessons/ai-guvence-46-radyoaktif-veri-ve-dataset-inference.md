---
id: ai-guvence-46
title: Radyoaktif Veri ve Dataset Inference · Eğitim Kümesi Hırsızlığını Kanıtlamak
summary: Radyoaktif kanarya yönüyle ağırlık/özellik hizalanmasını ölç, Welch t-istatistiği ve Cohen's d etki boyutunu hesapla; yerel deneyde kanarya sinyalini istatistiksel olarak değerlendir.
esleme: ai-guvence-17, ai-guvence-20, ai-guvence-39
timeout: 60
---

::: anlat Model ağırlıklarına bakmadan "benim verimle eğitilmiş" iddiası nasıl kanıtlanır?
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Eğitim verisine gömülen gizli bir yön (`radioactive data`), o veriyle eğitilen herhangi bir modelin ağırlıklarında ve logit duyarlılığında istatistiksel iz bırakır | İlk üç görev: `veri/radioactive.json` içindeki **sentetik** kanarya yönü ve skor listeleri. Final: GPU'da radyoaktif işaretli ve temiz veri kümeleriyle eğitilen iki gerçek MLP üzerinde `dataset inference` testi | Tek bir örneğin ezberlendiğini (`membership inference`) değil, **veri kümesinin** eğitimde kullanıldığını olasılıksal olarak gösterir |
| Şüpheli ve referans modellerin kanarya tepkileri arasındaki fark Welch $t$-testi ve `Cohen's d` etki boyutu ile ölçülür | Birim kanarya iç çarpımı, enerji oranı, Welch $t$-istatistiği ve çift eşikli hırsızlık kararı | İstatistiksel anlamlılığın ($t \ge t_{\text{eşik}}$) tek başına hukuki kesinlik olduğunu iddia etmez; yanlış pozitif oranı eşik seçimine bağlıdır |

> [!NOT]
> Görevler `veri/radioactive.json` dosyasını okur; dosya sentetiktir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; değişiklikler taşınmaz, **kalıcılık yoktur**. Ekranda ayrı dosya görüntüleyici yoktur; içeriği görmek için `print` kullan. Gizli testler ayrıdır. Final yeni model indirmez ve GPU varsa onu kullanır.

Tekil üyelik çıkarımı (`membership inference`, ai-guvence-17) tek bir kaydın eğitimde kullanılıp kullanılmadığını sorar ve çoğunlukla yüksek gürültüye takılır. Oysa veri kümesi sahipleri daha güçlü bir soru sorar: **"Bu model benim özel veri kümemin üzerinde mi eğitildi?"** Bu soruya iki yöntem yanıt verir: **`radioactive data`** (Sablayrolles vd. 2020) ve **`dataset inference`** (Maini vd. 2021).

**1. `Radioactive data` ve kanarya hizalanması:** Veri sahibi, yayınladığı veri kümesindeki belirli bir sınıfın örneklerine insan gözünün seçemeyeceği birim uzunlukta gizli bir taşıyıcı yön $\hat{u} = u / \|u\|_2$ ekler ($x \leftarrow x + \gamma \hat{u}$). Bu veriyle eğitilen bir modelin ağırlık veya temsil farkı vektörü $\Delta \in \mathbb{R}^d$, kanarya yönüyle hizalanır:
$$\text{ic\_carpim} = \Delta \cdot \hat{u} = \frac{\Delta \cdot u}{\|u\|_2}, \qquad \text{kosinus} = \frac{\Delta \cdot u}{\|\Delta\|_2 \|u\|_2}, \qquad \text{enerji\_orani} = \cos^2(\Delta, u)$$

**2. `Dataset inference` için Welch $t$-testi ve `Cohen's d`:** Şüpheli modelden alınan $n_1$ adet kanarya duyarlılık skoru ($X_1$) ile temiz referans modelden alınan $n_2$ adet skor ($X_2$) karşılaştırılır. Örneklem ortalamaları $\bar{x}_1, \bar{x}_2$ ve yansız örneklem varyansları ($n-1$ paydalı) $s_1^2, s_2^2$ olmak üzere:
$$SE = \sqrt{\frac{s_1^2}{n_1} + \frac{s_2^2}{n_2}}, \qquad t = \frac{\bar{x}_1 - \bar{x}_2}{SE}, \qquad s_{\text{pool}} = \sqrt{\frac{(n_1-1)s_1^2 + (n_2-1)s_2^2}{n_1+n_2-2}}, \qquad d_{\text{Cohen}} = \frac{\bar{x}_1 - \bar{x}_2}{s_{\text{pool}}}$$

**Neden hem $t$ hem `Cohen's d` gerekir?** Çok büyük örneklemde ($n \to \infty$) önemsiz derecede küçük bir fark bile büyük $t$ üretir; çok küçük örneklemde ise gürültülü bir sıçrama yanıltıcı olabilir. Bu yüzden `calinti_kanitlandi` kararı hem istatistiksel anlamlılık ($t \ge t_{\text{eşik}}$) hem de pratik etki boyutu ($d_{\text{Cohen}} \ge d_{\text{min}}$) şartını birlikte arar; yalnız biri sağlanırsa `belirsiz`, ikisi de sağlanmazsa `kanit_yok` döner.

**Saldırgan ne dener?** Çalıntı veri kümesini kullanırken spektral aykırı değer temizliği veya güçlü veri artırma (`data augmentation`) uygulayarak radyoaktif taşıyıcı yönün enerjisini zayıflatmaya çalışır.

**Savunma (denetçi) neden kırılır?** Yalnız ortalama farka ($\bar{x}_1 - \bar{x}_2$) bakıp varyansı ($SE$) hesaba katmayan bir denetçi, yüksek varyanslı temiz modelleri yanlışlıkla "çalıntı" diye suçlar (`false positive`).

**Görev 1 ve 2'de sık tuzaklar:** Yansız varyansta $n - 1$ yerine $n$ böleni kullanmak. `enerji_orani` hesabında kosinüsün karesini almayı unutmak.

Kaynaklar: [Sablayrolles vd. 2020 (Radioactive Data)](https://arxiv.org/abs/2002.00937), [Maini vd. 2021 (Dataset Inference)](https://arxiv.org/abs/2104.10706), [Carlini vd. 2022](https://arxiv.org/abs/2112.03570). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Köprü: ai-guvence-17 tekil üyelik çıkarımını, ai-guvence-20 filigranlamayı inceler; bu ders küme düzeyinde radyoaktif iz ve hipotez testini birleştirir.
:::

::: tahmin Ortalama fark aynıyken varyans t-değerini nasıl değiştirir?
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
import math
temiz = [0.0, 0.0, 0.0, 0.0]
dusuk_var = [1.0, 1.02, 0.98, 1.0]
yuksek_var = [4.0, -2.0, 3.0, -1.0]
for ad, s in [("Düşük varyans", dusuk_var), ("Yüksek varyans", yuksek_var)]:
    m = sum(s) / len(s)
    v = sum((x - m) ** 2 for x in s) / (len(s) - 1)
    se = math.sqrt(v / len(s))
    print(ad, "-> ortalama:", round(m, 2), "| t-değeri:", round(m / se, 2))
```
???
```cikti
Düşük varyans -> ortalama: 1.0 | t-değeri: 122.47
Yüksek varyans -> ortalama: 1.0 | t-değeri: 0.68
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: iki grubun da ortalaması `1.0` olduğu hâlde ikinci grupta neden hırsızlık kanıtı yoktur? Sonra üç kusurlu başlangıç kodunu çalıştır ve her birinin neyi kaçırdığını önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · Radyoaktif kanarya hizalanma skoru
`kanarya_hizalanma_skoru(fark_vektoru, kanarya_yonu)`: Aynı uzunlukta ($d \ge 1$) iki dolu liste, elemanları bool olmayan sonlu sayı ve her iki vektörün L2 normu $> 0$. Birim kanarya yönü $\hat{u} = u / \|u\|_2$ ile `ic_carpim` ($\Delta \cdot \hat{u}$), `kosinus` ($\frac{\Delta \cdot \hat{u}}{\|\Delta\|_2}$) ve `enerji_orani` ($\text{kosinus}^2$) alanlarını içeren sözlük döndür. Geçersiz girdide veya sıfır normda `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-46")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def kanarya_hizalanma_skoru(fark_vektoru, kanarya_yonu):
    ic = sum(a * b for a, b in zip(fark_vektoru, kanarya_yonu))
    return {"ic_carpim": ic, "kosinus": ic, "enerji_orani": ic}

from ai_guvence_veri import json_yukle
v = json_yukle("veri/radioactive.json")
print("Radyoaktif:", kanarya_hizalanma_skoru(v["fark_radyoaktif"], v["kanarya_yonu"]))
print("Temiz:", kanarya_hizalanma_skoru(v["fark_temiz"], v["kanarya_yonu"]))
```
```test
def sinama1(f):
    import copy, math, random
    def _r(d, u):
        nd = math.sqrt(sum(x * x for x in d)); nu = math.sqrt(sum(x * x for x in u))
        ic = sum(a * b for a, b in zip(d, u)) / nu; kos = ic / nd
        return {"ic_carpim": float(ic), "kosinus": float(kos), "enerji_orani": float(kos * kos)}
    def _y(a, b): return isinstance(a, dict) and set(a) == set(b) and all(abs(a[k] - b[k]) < 1e-12 for k in b)
    try:
        d = [3.0, 4.0]; u = [6.0, 0.0]; old = (list(d), list(u))
        if not _y(f(d, u), {"ic_carpim": 3.0, "kosinus": 0.6, "enerji_orani": 0.36}) or (d, u) != old:
            return False
        if not _y(f([-3.0, -4.0], [3.0, 4.0]), {"ic_carpim": -5.0, "kosinus": -1.0, "enerji_orani": 1.0}):
            return False
        rng = random.Random(46)
        for _ in range(25):
            n = rng.randint(2, 7)
            rd = [rng.uniform(-3, 3) for _ in range(n)]; ru = [rng.uniform(-3, 3) for _ in range(n)]
            if not _y(f(list(rd), list(ru)), _r(rd, ru)): return False
        for bad in ((None, u), (d, None), ([], []), ([0.0, 0.0], u), (d, [0.0, 0.0]), ([1.0], u), ([True, 1.0], u), (d, [float("nan"), 1.0])):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
ok(sinama1(kanarya_hizalanma_skoru), "birim kanarya iç çarpımı, kosinüs, enerji oranı ve geçersiz girdi")
for ad, mut in [
    ("kanarya normu yok", lambda d, u: dict(kanarya_hizalanma_skoru(d, u), ic_carpim=sum(a * b for a, b in zip(d, u)) + 0.1)),
    ("enerji kare değil", lambda d, u: dict(kanarya_hizalanma_skoru(d, u), enerji_orani=kanarya_hizalanma_skoru(d, u)["kosinus"])),
    ("kosinüs sıfır", lambda d, u: dict(kanarya_hizalanma_skoru(d, u), kosinus=0.0))
]:
    ok(not sinama1(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(kanarya_hizalanma_skoru, _il.import_module('ai_gercek_ai_guvence_46').referans_kanarya_hizalanma, ([1.2, -1.6, 0.3, -0.4], [0.6, -0.8, 0.0, 0.0]), tohum=3593)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def kanarya_hizalanma_skoru(fark_vektoru, kanarya_yonu):
    if not isinstance(fark_vektoru, list) or not isinstance(kanarya_yonu, list) or not fark_vektoru or len(fark_vektoru) != len(kanarya_yonu):
        raise ValueError("vektör")
    for v in fark_vektoru + kanarya_yonu:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise ValueError("sayı")
    nf = math.sqrt(sum(x * x for x in fark_vektoru))
    nk = math.sqrt(sum(x * x for x in kanarya_yonu))
    if nf <= 0 or nk <= 0: raise ValueError("sıfır norm")
    ic = sum(a * b for a, b in zip(fark_vektoru, kanarya_yonu)) / nk
    kos = ic / nf
    return {"ic_carpim": float(ic), "kosinus": float(kos), "enerji_orani": float(kos * kos)}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v = json_yukle("veri/radioactive.json")
    print("Radyoaktif:", kanarya_hizalanma_skoru(v["fark_radyoaktif"], v["kanarya_yonu"]))
    print("Temiz:", kanarya_hizalanma_skoru(v["fark_temiz"], v["kanarya_yonu"]))
```
```hint
İç çarpımı `kanarya_yonu` normuna (`nk`) bölerek birim yön izdüşümünü bul; `kosinus = ic / nf` ve `enerji_orani = kos * kos` döndür.
```
:::

::: anlat Welch t-istatistiği ve Cohen's d etki boyutu
İki bağımsız örneklem $X_1$ ($n_1 \ge 2$) ve $X_2$ ($n_2 \ge 2$) için:
- Yansız örneklem varyansları: $s_1^2 = \frac{1}{n_1 - 1}\sum (x - \bar{x}_1)^2$ ve $s_2^2 = \frac{1}{n_2 - 1}\sum (y - \bar{x}_2)^2$.
- Standart hata: $SE = \sqrt{\frac{s_1^2}{n_1} + \frac{s_2^2}{n_2}}$ ve birleşik standart sapma: $s_{\text{pool}} = \sqrt{\frac{(n_1-1)s_1^2 + (n_2-1)s_2^2}{n_1+n_2-2}}$.
- $SE \le 0$ ise (her iki örneklem de sabit sayıysa) `ValueError` yükseltilir.

Eşit büyüklükteki örneklemlerde havuzlanmış varyans iki varyansın ortalamasına iner. Cohen d için bkz. [Lakens, denklem 1](https://pmc.ncbi.nlm.nih.gov/articles/PMC3840331/).

**Görev 2'de sık tuzaklar:** Varyansı $n - 1$ yerine $n$'ye bölmek. `cohen_d` hesabında $s_{\text{pool}}$ yerine $SE$ kullanmak.
:::

::: gorev 2 · Welch t-istatistiği ve Cohen's d
`welch_t_istatistigi(supheli_skorlar, temiz_skorlar)`: İkisi de en az 2 elemanlı liste, elemanları bool olmayan sonlu sayı ve $SE > 0$. `{"ort_fark": float, "standart_hata": float, "t_degeri": float, "cohen_d": float}` döndür. Geçersiz girdide veya sıfır varyansta `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-46")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def welch_t_istatistigi(supheli_skorlar, temiz_skorlar):
    fark = sum(supheli_skorlar) / len(supheli_skorlar) - sum(temiz_skorlar) / len(temiz_skorlar)
    return {"ort_fark": fark, "standart_hata": 1.0, "t_degeri": fark, "cohen_d": fark}

from ai_guvence_veri import json_yukle
v = json_yukle("veri/radioactive.json")
print("Şüpheli:", welch_t_istatistigi(v["supheli_skorlar"], v["temiz_skorlar"]))
print("Yüksek varyanslı:", welch_t_istatistigi(v["yuksek_varyansli_supheli"], v["temiz_skorlar"]))
```
```test
def sinama2(f):
    import copy, math, random
    def _r(s1, s2):
        n1, n2 = len(s1), len(s2); m1 = sum(s1) / n1; m2 = sum(s2) / n2
        v1 = sum((x - m1) ** 2 for x in s1) / (n1 - 1); v2 = sum((y - m2) ** 2 for y in s2) / (n2 - 1)
        se = math.sqrt(v1 / n1 + v2 / n2); sp = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2)); d = m1 - m2
        return {"ort_fark": float(d), "standart_hata": float(se), "t_degeri": float(d / se), "cohen_d": float(d / sp)}
    def _y(a, b): return isinstance(a, dict) and set(a) == set(b) and all(abs(a[k] - b[k]) < 1e-11 for k in b)
    try:
        s1 = [2.0, 4.0, 3.0]; s2 = [0.0, 2.0, 1.0]; old = (list(s1), list(s2))
        if not _y(f(s1, s2), _r(s1, s2)) or (s1, s2) != old: return False
        if not math.isclose(f([0.0, 4.0], [0.0, 0.0, 0.0, 0.0])["cohen_d"], math.sqrt(2.0), abs_tol=1e-12):
            return False
        for cok_kucuk in (([0.0, 1e-162], [0.0, 0.0, 0.0, 4e-162]), ([0.0, 4e-162], [0.0, 0.0, 0.0, 1e-162])):
            try:
                f(*cok_kucuk)
                return False
            except ValueError:
                pass
        rng = random.Random(4646)
        for _ in range(25):
            rs1 = [rng.uniform(0, 5) for _ in range(rng.randint(2, 8))]
            rs2 = [rng.uniform(-2, 3) for _ in range(rng.randint(2, 8))]
            if not _y(f(list(rs1), list(rs2)), _r(rs1, rs2)): return False
        for bad in ((None, s2), (s1, None), ([1.0], s2), (s1, [1.0]), ([1.0, 1.0], [2.0, 2.0]), ([True, 2.0], s2), (s1, [float("nan"), 1.0])):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
ok(sinama2(welch_t_istatistigi), "yansız varyans, standart hata, Welch t, Cohen's d ve geçersiz girdi")
for ad, mut in [
    ("n böleni", lambda a, b: dict(welch_t_istatistigi(a, b), standart_hata=welch_t_istatistigi(a, b)["standart_hata"] * 0.8)),
    ("cohen_d yerine t", lambda a, b: dict(welch_t_istatistigi(a, b), cohen_d=welch_t_istatistigi(a, b)["t_degeri"])),
    ("işaret ters", lambda a, b: dict(welch_t_istatistigi(a, b), t_degeri=-welch_t_istatistigi(a, b)["t_degeri"]))
]:
    ok(not sinama2(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(welch_t_istatistigi, _il.import_module('ai_gercek_ai_guvence_46').referans_welch_t, ([1.82, 1.95, 1.76, 2.04, 1.89, 1.91], [0.05, -0.12, 0.14, -0.04, 0.08, -0.07]), tohum=3182,
             ekler=(([1.0, 1.0, 1.0], [0.05, -0.12, 0.14]), ([1.82, 1.95, 1.76], [0.0, 0.0, 0.0]), ([2.0, 2.0], [2.0, 2.0]), ([0.5, 0.5, 0.5, 0.5], [0.1, 0.2])))
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def welch_t_istatistigi(supheli_skorlar, temiz_skorlar):
    if not isinstance(supheli_skorlar, list) or not isinstance(temiz_skorlar, list) or len(supheli_skorlar) < 2 or len(temiz_skorlar) < 2:
        raise ValueError("liste")
    for v in supheli_skorlar + temiz_skorlar:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise ValueError("sayı")
    n1, n2 = len(supheli_skorlar), len(temiz_skorlar)
    m1 = sum(supheli_skorlar) / n1
    m2 = sum(temiz_skorlar) / n2
    v1 = sum((x - m1) ** 2 for x in supheli_skorlar) / (n1 - 1)
    v2 = sum((y - m2) ** 2 for y in temiz_skorlar) / (n2 - 1)
    se = math.sqrt(v1 / n1 + v2 / n2)
    sp = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2))
    if se <= 0 or sp <= 0: raise ValueError("sıfır varyans")
    fark = m1 - m2
    return {"ort_fark": float(fark), "standart_hata": float(se), "t_degeri": float(fark / se), "cohen_d": float(fark / sp)}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v = json_yukle("veri/radioactive.json")
    print("Şüpheli:", welch_t_istatistigi(v["supheli_skorlar"], v["temiz_skorlar"]))
    print("Yüksek varyanslı:", welch_t_istatistigi(v["yuksek_varyansli_supheli"], v["temiz_skorlar"]))
```
```hint
Her iki liste için örneklem varyansını `len - 1` ile böl; `se = math.sqrt(v1 / n1 + v2 / n2)` ve `sp = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2))` kullan.
```
:::

::: anlat Çift eşikli veri hırsızlığı kararı
`welch_t_istatistigi` çıktısı üzerinden karar üç duruma ayrılır:
- `t_degeri >= t_esik` **ve** `cohen_d >= min_etki_boyutu` ise: `karar="calinti_kanitlandi"`, `kanitlandi=True`
- İki koşuldan yalnız biri sağlanırsa: `karar="belirsiz"`, `kanitlandi=False`
- İkisi de sağlanmazsa: `karar="kanit_yok"`, `kanitlandi=False`

**Görev 3'te sık tuzaklar:** Yalnız `t_degeri >= t_esik` kontrolü yapıp `min_etki_boyutu` koşulunu atlamak.
:::

::: gorev 3 · Veri hırsızlığı denetim kararı
`veri_hirsizligi_karari(supheli_skorlar, temiz_skorlar, t_esik, min_etki_boyutu)`: Geçerli iki skor listesi; `t_esik > 0`, `min_etki_boyutu > 0` bool olmayan sonlu sayı. `{"karar": str, "kanitlandi": bool, "t_degeri": float, "cohen_d": float, "ort_fark": float}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-46")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def veri_hirsizligi_karari(supheli_skorlar, temiz_skorlar, t_esik, min_etki_boyutu):
    fark = sum(supheli_skorlar) / len(supheli_skorlar) - sum(temiz_skorlar) / len(temiz_skorlar)
    kanit = fark > 0.5
    return {"karar": "calinti_kanitlandi" if kanit else "kanit_yok", "kanitlandi": kanit, "t_degeri": fark, "cohen_d": fark, "ort_fark": fark}

from ai_guvence_veri import json_yukle
v = json_yukle("veri/radioactive.json")
print("Şüpheli:", veri_hirsizligi_karari(v["supheli_skorlar"], v["temiz_skorlar"], v["t_esik"], v["min_etki_boyutu"]))
print("Yüksek varyanslı:", veri_hirsizligi_karari(v["yuksek_varyansli_supheli"], v["temiz_skorlar"], v["t_esik"], v["min_etki_boyutu"]))
```
```test
def sinama3(f):
    import copy, math
    try:
        s1 = [1.82, 1.95, 1.76, 2.04]; s2 = [0.05, -0.12, 0.14, -0.04]; old = (list(s1), list(s2))
        r1 = f(s1, s2, 3.0, 1.2)
        if r1["karar"] != "calinti_kanitlandi" or r1["kanitlandi"] is not True or (s1, s2) != old: return False
        # Her ikisi de eşik altı
        r2 = f([2.5, -1.8, 3.1, -1.2], s2, 3.0, 1.2)
        if r2["karar"] != "kanit_yok" or r2["kanitlandi"] is not False: return False
        # Yalnız t_degeri eşik üstü, cohen_d eşik altı -> belirsiz
        r3 = f(s1, s2, 3.0, 100.0)
        if r3["karar"] != "belirsiz" or r3["kanitlandi"] is not False: return False
        # Yalnız cohen_d eşik üstü, t_degeri eşik altı -> belirsiz
        r4 = f(s1, s2, 1000.0, 1.2)
        if r4["karar"] != "belirsiz" or r4["kanitlandi"] is not False: return False
        for bad in ((None, s2, 3.0, 1.0), ([0.0, 1e-162], [0.0, 0.0, 0.0, 4e-162], 3.0, 1.0), ([0.0, 4e-162], [0.0, 0.0, 0.0, 1e-162], 3.0, 1.0), ([1.0], s2, 3.0, 1.0), ([1.0, 1.0], [2.0, 2.0], 3.0, 1.0), (s1, s2, 0.0, 1.0), (s1, s2, 3.0, 0.0), (s1, s2, True, 1.0), (s1, s2, 3.0, True)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
ok(sinama3(veri_hirsizligi_karari), "üç karar durumu (kanıtlandı/belirsiz/yok), çift eşik ve geçersiz girdi")
for ad, mut in [
    ("belirsiz yok", lambda a, b, te, me: dict(veri_hirsizligi_karari(a, b, te, me), karar="calinti_kanitlandi" if veri_hirsizligi_karari(a, b, te, me)["t_degeri"] >= te else "kanit_yok")),
    ("hep kanıtlandı", lambda a, b, te, me: dict(veri_hirsizligi_karari(a, b, te, me), karar="calinti_kanitlandi", kanitlandi=True)),
    ("t eşiği unutuldu", lambda a, b, te, me: veri_hirsizligi_karari(a, b, 1e-9, me))
]:
    ok(not sinama3(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(veri_hirsizligi_karari, _il.import_module('ai_gercek_ai_guvence_46').referans_veri_hirsizligi, ([1.82, 1.95, 1.76, 2.04, 1.89, 1.91], [0.05, -0.12, 0.14, -0.04, 0.08, -0.07], 3.0, 1.2), tohum=3495,
             ekler=(([1.0, 1.0, 1.0], [0.05, -0.12, 0.14], 3.0, 1.2), ([1.82, 1.95, 1.76], [0.0, 0.0, 0.0], 3.0, 1.2), ([2.0, 2.0], [2.0, 2.0], 3.0, 1.2)))
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def veri_hirsizligi_karari(supheli_skorlar, temiz_skorlar, t_esik, min_etki_boyutu):
    if not isinstance(supheli_skorlar, list) or not isinstance(temiz_skorlar, list) or len(supheli_skorlar) < 2 or len(temiz_skorlar) < 2:
        raise ValueError("liste")
    for v in supheli_skorlar + temiz_skorlar + [t_esik, min_etki_boyutu]:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise ValueError("sayı")
    if t_esik <= 0 or min_etki_boyutu <= 0: raise ValueError("eşik")
    n1, n2 = len(supheli_skorlar), len(temiz_skorlar)
    m1 = sum(supheli_skorlar) / n1
    m2 = sum(temiz_skorlar) / n2
    v1 = sum((x - m1) ** 2 for x in supheli_skorlar) / (n1 - 1)
    v2 = sum((y - m2) ** 2 for y in temiz_skorlar) / (n2 - 1)
    se = math.sqrt(v1 / n1 + v2 / n2)
    sp = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2))
    if se <= 0 or sp <= 0: raise ValueError("sıfır varyans")
    fark = float(m1 - m2)
    t_deg = float(fark / se)
    cd = float(fark / sp)
    t_ok = t_deg >= t_esik
    d_ok = cd >= min_etki_boyutu
    if t_ok and d_ok: karar = "calinti_kanitlandi"
    elif t_ok or d_ok: karar = "belirsiz"
    else: karar = "kanit_yok"
    return {"karar": karar, "kanitlandi": bool(t_ok and d_ok), "t_degeri": t_deg, "cohen_d": cd, "ort_fark": fark}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v = json_yukle("veri/radioactive.json")
    print("Şüpheli:", veri_hirsizligi_karari(v["supheli_skorlar"], v["temiz_skorlar"], v["t_esik"], v["min_etki_boyutu"]))
    print("Yüksek varyanslı:", veri_hirsizligi_karari(v["yuksek_varyansli_supheli"], v["temiz_skorlar"], v["t_esik"], v["min_etki_boyutu"]))
```
```hint
`t_ok = (t_degeri >= t_esik)` ve `d_ok = (cohen_d >= min_etki_boyutu)` koşullarına göre üç durumdan (`calinti_kanitlandi`, `belirsiz`, `kanit_yok`) birini döndür.
```
:::

::: anlat Hata vitrini · çalışmış yanlış rapor
Yazar, kusurlu başlangıç kodlarını görünür sentetik veriyle gerçekten çalıştırdı ve sonucu `outputs/yeni-ai-guvence-46/gorunur-run-1.json` dosyasına kaydetti. `yuksek_varyansli_supheli` örneğinde skorlar `[-1.8, 3.1]` arasında savrulduğu için gerçek $t$-değeri `0.684` ve `Cohen's d` `0.395`'tir (`kanit_yok`). Ancak varyansı hesaba katmayan kusurlu kod yalnız ortalama farka (`0.66 > 0.5`) bakarak `calinti_kanitlandi` döndürür ve masum/gürültülü bir modeli suçlar.

Bu kaydedilmiş bir hesaplama çıktısıdır, model yanıtı değildir ve rapor sentetiktir. Varyans ve standart hatayı ölçmeden yalnız ortalama farkla veri hırsızlığı iddiasında bulunmanın neden tehlikeli olduğunu kendi cümlenle açıkla. Gerçek finaldeki ölçüm ayrıca üretilir; bu sayılar onun yerine konmaz.
:::

::: anlat Gerçek deney: Radyoaktif veriyle eğitilen modelde dataset inference
Final, `load_digits` üzerinde gizli bir birim kanarya yönü $\hat{u}$ üretir ve eğitim kümesindeki `0` sınıfı görüntülerine bu radyoaktif yönü gömer. Ardından GPU'da iki ayrı MLP eğitilir:
1. **Şüpheli model:** Radyoaktif işaretli eğitim kümesi üzerinde eğitilir.
2. **Temiz model:** Radyoaktif işaret taşımayan ayrık eğitim kümesi üzerinde eğitilir.

3. **Kontrol model:** Şüpheliyle **aynı** eğitim kümesinde, ama işaretsiz olarak eğitilir. "Çalıntı" sayılırsa test yanlış pozitif veriyor demektir.

Bir modelin "kanarya tepkisi", sınama görüntüleri kanarya yönünde biraz kaydırıldığında sınıf-0 logitinin ne kadar arttığıdır. Sorulması gereken soru şudur: bu model **gizli yöne**, herhangi bir rastgele yöne verdiğinden daha güçlü mü tepki veriyor?

**Bu dersin yazarı bu soruyu önce yanlış kurdu; ölçüm hatayı gösterdi.**
- **Eski yöntem:** Şüpheli modelin 32 örnekteki kanarya tepkisi, farklı veriyle eğitilmiş temiz modelinkiyle örnek başına Welch $t$-testiyle karşılaştırılır. Bu yöntem işaretsiz kontrol modelini de sık sık "çalıntı" ilan etti: yazarın zayıf ayardaki (60 adım, güç 0.45) 20 koşusunun 7'sinde. İki farklı model, işaret olmasa da, aynı yöne farklı tepki verir. 32 örneği bağımsız gözlem saymak da güveni şişirir.
- **Doğru yöntem (`Sablayrolles vd. 2020` fikri), yön düzeyinde null:** Aynı modelin 64 rastgele yöne verdiği ortalama tepkiler null dağılımını oluşturur. Kanarya yönünün tepkisi, örneklerin 4 ayrık alt kümesinde ölçülür ve bu dağılımla karşılaştırılır. Cohen $d$, havuzlanmış standart sapmayla ölçeklenen ortalama farkıdır. Deney $d \ge 3$ eşiğini kullanır. Bu eşikten tek başına bir p-değeri çıkarılamaz.

Senin **`welch_t_istatistigi`** ve **`veri_hirsizligi_karari`** işlevlerin bu doğru düzende çalışır. **`kanarya_hizalanma_skoru`** ise şüpheli ile kontrol modelin ilk katman ağırlık farkını kanarya yönüyle karşılaştırır.

Yazarın sekiz GPU koşusunda (işaret gücü 0.6, 300 eğitim adımı):
- **Şüpheli model:** 6 koşuda "çalıntı kanıtlandı", 2'sinde "belirsiz"; hiç "kanıt yok" değil. Etki büyüklüğü $d$ = 2.1–4.1.
- **Kontrol ve temiz model:** 16 denemenin hiçbirinde "çalıntı" değil (en fazla "belirsiz").
- **İşaretin görev maliyeti:** Yok; test doğruluğu üç modelde de 0.88–0.89.
- **Ağırlık uzayı hizalanması kör:** Ağırlık farkının kanarya yönüne kosinüsü −0.09 ile 0.09 arasında. İz, ağırlıklarda tek bir yönde değil, **davranışta** görünür.

Daha zayıf ayarda (60 adım, güç 0.45) şüpheli model 8 koşunun yalnız 2'sinde yakalandı. Eski yöntemin o ayardaki "kesin" yakalamalarının çoğu sahteydi.

**Kara kutu ve $p < 10^{-6}$: çoklu kanarya.** Tek bir kanaryayla $d \approx 3$ ancak $p \approx 10^{-3}$ düzeyinde kanıt verir. Gerçek bir hukuki iddia için çok daha güçlü kanıt gerekir. Veri sahibi bu yüzden **4 sınıfa 4 ayrı gizli yön** koyar. Test yalnız bir log-olasılık API'si kullanır (`log_softmax`, model iç yapısına erişim yok). Her kanarya $c$ için sınıf-$c$ log-olasılığının kanarya yönüne tepkisi, aynı sınıfın 64 rastgele yöne tepki dağılımına göre bir $z_c$'ye çevrilir. Kanaryalar birbirinden bağımsız olduğu için Stouffer yöntemiyle birleştirilir: $Z = \sum_c z_c / \sqrt{4}$, $p = \Phi(-Z)$. İşaretsiz bir modelde her $z_c$ yaklaşık standart normaldir, dolayısıyla $Z$ de öyledir. İşaretli modelde kanıt $\sqrt{4}$ kat büyür.

Yazarın sekiz koşusunda:
- **Şüpheli model:** $Z$ = 5.2–8.1, $p$ = $10^{-7}$–$10^{-16}$; **8/8 koşuda $p < 10^{-6}$**.
- **Kontrol ve temiz model:** $Z$ −1.2 ile 2.0 arasında; hiçbiri anlamlı değil.
- **Bedel:** 4 işaret şüpheli modelin görev doğruluğunu ~0.89'dan ~0.82'ye düşürdü. Tek işaret bedelsizdi. Çok kanarya daha güçlü kanıt verir, ama veriyi daha çok bozar.
- **Tek kanaryalı testin gücü düştü:** Dört işaret modelin kapasitesini paylaştığı için sınıf-0 kanaryası tek başına bazen zayıf kaldı ("kanıt yok"). Kanıt tek testten değil, birleşik testten gelir.

**Kanıt dosyasını oku:** Soru 1: `yontem_a.kontrol` ile `kontrol_karar` neden farklı karar verebiliyor? Hangisinin gözlem birimi doğru? Soru 2: `null_yon` 64 yerine 8 olsaydı z-skoru eşiği neden daha güvenilmez olurdu? Soru 3: `agirlik_hizalanma.kosinus` sıfıra yakınken davranış testi neden yine de işareti buluyor? Cevabını tezgâhta yorum olarak yaz; otomatik test bu serbest açıklamayı puanlamaz.
:::

::: gorev Gerçek deney · Radyoaktif kanarya izi ve Welch t-testi ile dataset inference
Önceki üç görevin `kanarya_hizalanma_skoru`, `welch_t_istatistigi` ve `veri_hirsizligi_karari` işlevlerini birleştir. Çalıştır gerçek tabloyu gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 180
```
```starter
import ai_lab
import math
def kanarya_hizalanma_skoru(fark_vektoru, kanarya_yonu):
    ic = sum(a * b for a, b in zip(fark_vektoru, kanarya_yonu))
    return {"ic_carpim": ic, "kosinus": ic, "enerji_orani": ic}
def welch_t_istatistigi(supheli_skorlar, temiz_skorlar):
    fark = sum(supheli_skorlar) / len(supheli_skorlar) - sum(temiz_skorlar) / len(temiz_skorlar)
    return {"ort_fark": fark, "standart_hata": 1.0, "t_degeri": fark, "cohen_d": fark}
def veri_hirsizligi_karari(supheli_skorlar, temiz_skorlar, t_esik, min_etki_boyutu):
    fark = sum(supheli_skorlar) / len(supheli_skorlar) - sum(temiz_skorlar) / len(temiz_skorlar)
    kanit = fark > 0.5
    return {"karar": "calinti_kanitlandi" if kanit else "kanit_yok", "kanitlandi": kanit, "t_degeri": fark, "cohen_d": fark, "ort_fark": fark}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_46 as D
    D.goster(kanarya_hizalanma_skoru, welch_t_istatistigi, veri_hirsizligi_karari)
```
```test
import ai_lab, math
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('referans_kanarya_hizalanma', 'referans_welch_t', 'referans_veri_hirsizligi', 'kanit_yaz', '_yakin'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
kanarya_hizalanma_skoru = need("kanarya_hizalanma_skoru")
welch_t_istatistigi = need("welch_t_istatistigi")
veri_hirsizligi_karari = need("veri_hirsizligi_karari")
def sinama1(f):
    import copy, math, random
    def _r(d, u):
        nd = math.sqrt(sum(x * x for x in d)); nu = math.sqrt(sum(x * x for x in u))
        ic = sum(a * b for a, b in zip(d, u)) / nu; kos = ic / nd
        return {"ic_carpim": float(ic), "kosinus": float(kos), "enerji_orani": float(kos * kos)}
    def _y(a, b): return isinstance(a, dict) and set(a) == set(b) and all(abs(a[k] - b[k]) < 1e-12 for k in b)
    try:
        d = [3.0, 4.0]; u = [6.0, 0.0]; old = (list(d), list(u))
        if not _y(f(d, u), {"ic_carpim": 3.0, "kosinus": 0.6, "enerji_orani": 0.36}) or (d, u) != old:
            return False
        rng = random.Random(46)
        for _ in range(25):
            n = rng.randint(2, 7)
            rd = [rng.uniform(-3, 3) for _ in range(n)]; ru = [rng.uniform(-3, 3) for _ in range(n)]
            if not _y(f(list(rd), list(ru)), _r(rd, ru)): return False
        for bad in ((None, u), ([0.0, 0.0], u), (d, [0.0, 0.0]), ([True, 1.0], u)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama1(kanarya_hizalanma_skoru), "birim kanarya iç çarpımı, kosinüs, enerji oranı ve geçersiz girdi")
for ad, mut in [
    ("kanarya normu yok", lambda d, u: dict(kanarya_hizalanma_skoru(d, u), ic_carpim=sum(a * b for a, b in zip(d, u)) + 0.1)),
    ("enerji kare değil", lambda d, u: dict(kanarya_hizalanma_skoru(d, u), enerji_orani=kanarya_hizalanma_skoru(d, u)["kosinus"])),
    ("kosinüs sıfır", lambda d, u: dict(kanarya_hizalanma_skoru(d, u), kosinus=0.0))
]:
    kontrol(not sinama1(mut), "mutant reddedildi: " + ad)
def sinama2(f):
    import copy, math, random
    def _r(s1, s2):
        n1, n2 = len(s1), len(s2); m1 = sum(s1) / n1; m2 = sum(s2) / n2
        v1 = sum((x - m1) ** 2 for x in s1) / (n1 - 1); v2 = sum((y - m2) ** 2 for y in s2) / (n2 - 1)
        se = math.sqrt(v1 / n1 + v2 / n2); sp = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2)); d = m1 - m2
        return {"ort_fark": float(d), "standart_hata": float(se), "t_degeri": float(d / se), "cohen_d": float(d / sp)}
    def _y(a, b): return isinstance(a, dict) and set(a) == set(b) and all(abs(a[k] - b[k]) < 1e-11 for k in b)
    try:
        s1 = [2.0, 4.0, 3.0]; s2 = [0.0, 2.0, 1.0]; old = (list(s1), list(s2))
        if not _y(f(s1, s2), _r(s1, s2)) or (s1, s2) != old: return False
        if not math.isclose(f([0.0, 4.0], [0.0, 0.0, 0.0, 0.0])["cohen_d"], math.sqrt(2.0), abs_tol=1e-12):
            return False
        for cok_kucuk in (([0.0, 1e-162], [0.0, 0.0, 0.0, 4e-162]), ([0.0, 4e-162], [0.0, 0.0, 0.0, 1e-162])):
            try:
                f(*cok_kucuk)
                return False
            except ValueError:
                pass
        rng = random.Random(4646)
        for _ in range(25):
            rs1 = [rng.uniform(0, 5) for _ in range(rng.randint(2, 8))]
            rs2 = [rng.uniform(-2, 3) for _ in range(rng.randint(2, 8))]
            if not _y(f(list(rs1), list(rs2)), _r(rs1, rs2)): return False
        for bad in ((None, s2), ([1.0], s2), ([1.0, 1.0], [2.0, 2.0]), ([True, 2.0], s2)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama2(welch_t_istatistigi), "yansız varyans, standart hata, Welch t, Cohen's d ve geçersiz girdi")
for ad, mut in [
    ("n böleni", lambda a, b: dict(welch_t_istatistigi(a, b), standart_hata=welch_t_istatistigi(a, b)["standart_hata"] * 0.8)),
    ("cohen_d yerine t", lambda a, b: dict(welch_t_istatistigi(a, b), cohen_d=welch_t_istatistigi(a, b)["t_degeri"])),
    ("işaret ters", lambda a, b: dict(welch_t_istatistigi(a, b), t_degeri=-welch_t_istatistigi(a, b)["t_degeri"]))
]:
    kontrol(not sinama2(mut), "mutant reddedildi: " + ad)
def sinama3(f):
    import copy, math
    try:
        s1 = [1.82, 1.95, 1.76, 2.04]; s2 = [0.05, -0.12, 0.14, -0.04]; old = (list(s1), list(s2))
        if f(s1, s2, 3.0, 1.2)["karar"] != "calinti_kanitlandi" or (s1, s2) != old: return False
        if f([2.5, -1.8, 3.1, -1.2], s2, 3.0, 1.2)["karar"] != "kanit_yok": return False
        if f(s1, s2, 3.0, 100.0)["karar"] != "belirsiz" or f(s1, s2, 1000.0, 1.2)["karar"] != "belirsiz": return False
        for bad in ((None, s2, 3.0, 1.0), ([0.0, 1e-162], [0.0, 0.0, 0.0, 4e-162], 3.0, 1.0), ([0.0, 4e-162], [0.0, 0.0, 0.0, 1e-162], 3.0, 1.0), ([1.0], s2, 3.0, 1.0), (s1, s2, 0.0, 1.0), (s1, s2, 3.0, 0.0), (s1, s2, True, 1.0)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama3(veri_hirsizligi_karari), "üç karar durumu (kanıtlandı/belirsiz/yok), çift eşik ve geçersiz girdi")
for ad, mut in [
    ("belirsiz yok", lambda a, b, te, me: dict(veri_hirsizligi_karari(a, b, te, me), karar="calinti_kanitlandi" if veri_hirsizligi_karari(a, b, te, me)["t_degeri"] >= te else "kanit_yok")),
    ("hep kanıtlandı", lambda a, b, te, me: dict(veri_hirsizligi_karari(a, b, te, me), karar="calinti_kanitlandi", kanitlandi=True)),
    ("t eşiği unutuldu", lambda a, b, te, me: veri_hirsizligi_karari(a, b, 1e-9, me))
]:
    kontrol(not sinama3(mut), "mutant reddedildi: " + ad)
# farksal tarama (final)
import importlib as _il
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_R = _il.import_module('sandbox.ai_gercek_ai_guvence_46')
for _ad, _ref, _taban, _toh in (
    ('kanarya_hizalanma_skoru', 'referans_kanarya_hizalanma', ([1.2, -1.6, 0.3, -0.4], [0.6, -0.8, 0.0, 0.0]), 4115),
    ('welch_t_istatistigi', 'referans_welch_t', ([1.82, 1.95, 1.76, 2.04, 1.89, 1.91], [0.05, -0.12, 0.14, -0.04, 0.08, -0.07]), 3704),
    ('veri_hirsizligi_karari', 'referans_veri_hirsizligi', ([1.82, 1.95, 1.76, 2.04, 1.89, 1.91], [0.05, -0.12, 0.14, -0.04, 0.08, -0.07], 3.0, 1.2), 4017),
):
    _t, _g = _ff(need(_ad), getattr(_R, _ref), _taban, tohum=_toh)
    kontrol(_t, "farksal tarama (" + _ad + "): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
if not all(checks): stop()
from sandbox import ai_gercek_ai_guvence_46 as D
try: r = D.deney(kanarya_hizalanma_skoru, welch_t_istatistigi, veri_hirsizligi_karari)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r["hiz_ayni"], "gerçek ağırlık farkında kanarya hizalanması bağımsız hesapla aynı")
kontrol(r["welch_ayni"], "gerçek logit tepkilerinde Welch t-istatistiği bağımsız hesapla aynı")
kontrol(r["karar_ayni"], "gerçek skorlarda veri hırsızlığı kararı bağımsız hesapla aynı")
kontrol(r["kontrol_karar"]["karar"] != "calinti_kanitlandi" and r["temiz_karar"]["karar"] != "calinti_kanitlandi", "tek kanaryalı testte işaretsiz kontrol ve temiz model çalıntı sayılmadı (yanlış pozitif yok): %s / %s" % (r["kontrol_karar"]["karar"], r["temiz_karar"]["karar"]))
kk = r["kara_kutu"]
kontrol(kk["supheli"]["p_degeri"] < 1e-6, "kara kutu çoklu kanarya testi şüpheli modeli p < 1e-6 ile yakaladı: Z=%.2f, p=%.1e" % (kk["supheli"]["Z_birlesik"], kk["supheli"]["p_degeri"]))
kontrol(kk["kontrol"]["p_degeri"] > 1e-3 and kk["temiz"]["p_degeri"] > 1e-3, "aynı veriyle işaretsiz kontrol ve temiz model kara kutu testte anlamlı çıkmadı: Z=%.2f / %.2f" % (kk["kontrol"]["Z_birlesik"], kk["temiz"]["Z_birlesik"]))
ai_lab.kanit_yaz("ai-guvence-46-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-guvence-46", "deney": r})
```
```solution
import ai_lab
import math
def kanarya_hizalanma_skoru(fark_vektoru, kanarya_yonu):
    if not isinstance(fark_vektoru, list) or not isinstance(kanarya_yonu, list) or not fark_vektoru or len(fark_vektoru) != len(kanarya_yonu):
        raise ValueError("vektör")
    for v in fark_vektoru + kanarya_yonu:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise ValueError("sayı")
    nf = math.sqrt(sum(x * x for x in fark_vektoru))
    nk = math.sqrt(sum(x * x for x in kanarya_yonu))
    if nf <= 0 or nk <= 0: raise ValueError("sıfır norm")
    ic = sum(a * b for a, b in zip(fark_vektoru, kanarya_yonu)) / nk
    kos = ic / nf
    return {"ic_carpim": float(ic), "kosinus": float(kos), "enerji_orani": float(kos * kos)}
def welch_t_istatistigi(supheli_skorlar, temiz_skorlar):
    if not isinstance(supheli_skorlar, list) or not isinstance(temiz_skorlar, list) or len(supheli_skorlar) < 2 or len(temiz_skorlar) < 2:
        raise ValueError("liste")
    for v in supheli_skorlar + temiz_skorlar:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise ValueError("sayı")
    n1, n2 = len(supheli_skorlar), len(temiz_skorlar)
    m1 = sum(supheli_skorlar) / n1
    m2 = sum(temiz_skorlar) / n2
    v1 = sum((x - m1) ** 2 for x in supheli_skorlar) / (n1 - 1)
    v2 = sum((y - m2) ** 2 for y in temiz_skorlar) / (n2 - 1)
    se = math.sqrt(v1 / n1 + v2 / n2)
    sp = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2))
    if se <= 0 or sp <= 0: raise ValueError("sıfır varyans")
    fark = m1 - m2
    return {"ort_fark": float(fark), "standart_hata": float(se), "t_degeri": float(fark / se), "cohen_d": float(fark / sp)}
def veri_hirsizligi_karari(supheli_skorlar, temiz_skorlar, t_esik, min_etki_boyutu):
    if not isinstance(t_esik, (int, float)) or isinstance(t_esik, bool) or not math.isfinite(t_esik) or t_esik <= 0:
        raise ValueError("t_esik")
    if not isinstance(min_etki_boyutu, (int, float)) or isinstance(min_etki_boyutu, bool) or not math.isfinite(min_etki_boyutu) or min_etki_boyutu <= 0:
        raise ValueError("min_etki")
    m = welch_t_istatistigi(supheli_skorlar, temiz_skorlar)
    t_ok = m["t_degeri"] >= t_esik
    d_ok = m["cohen_d"] >= min_etki_boyutu
    if t_ok and d_ok: karar = "calinti_kanitlandi"
    elif t_ok or d_ok: karar = "belirsiz"
    else: karar = "kanit_yok"
    return {"karar": karar, "kanitlandi": bool(t_ok and d_ok), "t_degeri": m["t_degeri"], "cohen_d": m["cohen_d"], "ort_fark": m["ort_fark"]}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_46 as D
    D.goster(kanarya_hizalanma_skoru, welch_t_istatistigi, veri_hirsizligi_karari)
```
```hint
Üç işlevi aynen birleştir. Radyoaktif kanarya yönünün hem ağırlık farkında hem de Welch t-testinde nasıl iz bıraktığını incele.
```
:::

::: anlat Sınır
Bu ders kontrollü bir radyoaktif yön ve yön düzeyinde bir null testiyle eğitim kümesi kullanımını (`dataset inference`) gösterir. Gerçek deney 8×8 rakamlar ve küçük bir MLP kullanır. İşaret gücü büyüktür ve tek bir sınıfa uygulanır. Kara kutu test log-olasılık API'si varsayar; yalnız en olası etiketi döndüren bir API'de ve büyük modellerde güç çok daha düşüktür. Yakalama gücü işaret gücüne, kanarya sayısına ve eğitim süresine bağlıdır; tek kanaryalı test zayıf ayarda çoğu zaman "belirsiz" der. Kanarya yönü önceden gömülmemiş ham verilerde aynı kesinlik elde edilemez.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Örnek ezberlemeden küme izine (`radioactive data`) (30 sn).** "Model tekil örnekleri birebir ezberlemese bile, eğitim verisine gömülen birim yönlü küçük bir `kanarya` işareti modelin karar sınırını ve log-olasılık farklarını o yöne doğru hizalar."
2. **Welch $t$-testi + Cohen $d$ çift kapısı (35 sn).** "Tek bir kanarya skoru şans eseri yüksek çıkabilir; bu yüzden şüpheli modelin kanarya hizalanma skorlarını temiz referans dağılımıyla karşılaştırırken hem istatistiksel anlamlılık (`Welch t`) hem pratik etki boyutu (`Cohen d`) birlikte aranır."
3. **Yanlış suçlama riski (30 sn).** "Yalnız $p$-değerine bakmak örneklem büyüdüğünde önemsiz farkları 'veri hırsızlığı' sanabilir; çift eşik ve `belirsiz` bölgesi yanlış pozitif suçlamayı frenler."
4. **Soru (25 sn).** "Şüpheli model log-olasılık yerine yalnız en üst sınıf etiketini (`top-1 label`) döndürüyorsa radyoaktif iz testi neden çok daha fazla sorgu ve kanarya gerektirir?"
:::
