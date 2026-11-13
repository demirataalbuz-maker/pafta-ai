---
id: ai-guvence-41
title: Sparse Autoencoders ve Activation Steering · Monosemantic Özellik Bastırma
summary: Top-K Sparse Autoencoder (SAE) kodlayıcısını yaz, hedef gizli özelliği feature clamping ile üstten sınırla ve yeniden üretim kaybı ile L0 seyrekliğini SmolLM2-135M artık akımı üzerinde doğrula.
esleme: ai-guvence-05, ai-guvence-37, ai-savunma-33
timeout: 60
---

::: anlat Süperpozisyondaki nöronu tek başına neden susturamazsın?
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Bir nöron birden çok alakasız kavramı üst üste (`superposition`) taşıdığı için nöronu sıfırlamak yan etki doğurur; `Sparse Autoencoder` (`SAE`) aktivasyonu daha geniş ve seyrek (`monosemanticity`) bir sözlüğe açar | İlk üç görev: `veri/sae.json` içindeki **sentetik** aktivasyon ve ağırlık matrisleri. Final: gerçek SmolLM2-135M'in artık akımında Top-K `SAE`; "kod" ve "dalkavukluk" latentlerinin keşfi, `feature clamping` ile seçici bastırma ve latentin neyi izlediğinin sorgulanması | 135M parametreli modelin tek katmanındaki `SAE` latentinin, milyar parametreli bir modeldeki güvenlik kavramını saf ve nedensel olarak izole ettiğini kanıtlamaz |
| Seçilen bir `SAE` özelliğini tavan değere (`feature clamping`) çekmek, yeniden üretilen artık akım aktivasyonunu ve hedef metin türündeki dil modeli kaybını kontrollü biçimde kaydırır | Top-K ReLU kodlama, doğrusal kod çözme (`decoder`), MSE + L1 kaybı ve L0 seyreklik oranı | Tek bir özelliğin bastırılmasının tüm zararlı davranışları yan etkisiz sildiğini garanti etmez |

> [!NOT]
> Görevler `veri/sae.json` dosyasını okur; dosya sentetiktir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; değişiklikler taşınmaz, **kalıcılık yoktur**. Ekranda ayrı dosya görüntüleyici yoktur; içeriği görmek için `print` kullan. Gizli testler ayrıdır. Final yeni model indirmez ve GPU varsa onu kullanır.

Mekanistik yorumlanabilirlik (`mechanistic interpretability`) şu temel engelle başlar: bir katmanda $d_{\text{model}}$ nöron varken model bundan çok daha fazla kavramı temsil etmek zorundadır. Bunu kavramları neredeyse dik yönler olarak üst üste bindirerek (`superposition`) yapar (Elhage vd. 2022). Sonuçta tek bir nöron hem kod sözdizimini hem de alakasız bir doğal dil kalıbını aynı anda ateşleyebilir (`polysemanticity`).

**`Sparse Autoencoder` (`SAE`) süperpozisyonu çözmeye çalışır.** Gizli aktivasyon $x \in \mathbb{R}^{d_{\text{model}}}$ alınır, daha geniş bir özellik uzayına ($d_{\text{sae}} > d_{\text{model}}$) doğrusal dönüşüm ve ReLU ile çıkarılır:
$$z_i = \max\left(0,\; \sum_{j} W_{\text{enc}}[i, j]\, x_j + b_{\text{enc}}[i]\right)$$
Top-K `SAE` (Gao vd. 2024) bu ön-aktivasyonlardan yalnızca en büyük $k$ tanesini korur, geri kalanını tam `0.0` yapar. Eşitlik durumunda küçük indisli özellik öncelik alır. Böylece her örnekte en fazla $k$ özellik aktif kalır ve özellikler tekil kavramlara (`monosemanticity`) yaklaşır (Bricken vd. 2023).

**`Feature clamping` ve `activation steering` ne yapar?** Kod vektörü $c \in \mathbb{R}^{d_{\text{sae}}}$ elde edildikten sonra, riskli veya hedef bir özelliğin (`hedef_indis`) aşırı ateşlenmesini önlemek için değeri $\min(c_{\text{hedef}}, \text{tavan})$ ile üstten sınırlanır (`feature clamping`, Templeton vd. 2024). Ardından kod çözücü (`decoder`) yeniden üretilen aktivasyonu hesaplar:
$$\hat{x}_j = \sum_{i} W_{\text{dec}}[j, i]\, c'_i + b_{\text{dec}}[j]$$

**Kalite ve seyreklik dengesi:** `SAE` hiçbir bilgiyi kaybetmeden her şeyi sıfırlayamaz. Yeniden üretim hatası $\text{MSE} = \frac{1}{d_{\text{model}}} \sum_j (x_j - \hat{x}_j)^2$ ile ölçülürken, seyreklik cezası $\text{L1} = \sum_i |c_i|$ ve aktif özellik oranı $\text{L0 oranı} = \frac{1}{d_{\text{sae}}} \sum_i \mathbb{I}(c_i > 10^{-9})$ ile izlenir.

**Saldırgan ne dener?** Tek bir güvenlik özelliğine yapılan `feature clamping` savunmasını aşmak için aynı kavramı farklı kelimelerle ifade ederek özelliği komşu `SAE` koordinatlarına (`feature splitting`) dağıtmaya çalışır.

**Savunma neden kırılır?** Eğer `SAE` yeterince seyrek değilse (`L0` yüksekse) özellikler hâlâ karışık (`polysemantic`) kalır ve bastırma modelin normal yeteneklerini bozar; eğer aşırı seyrekse (`MSE` yüksekse) yeniden üretilen aktivasyon modelin asıl hesabını temsil etmez.

**Görev 1'de sık tuzaklar:** ReLU (`max(0.0, ...)`) uygulanmadan önce Top-K seçmek veya negatif değerleri kod vektöründe bırakmak. `k` dışındaki indisleri sıfırlamak yerine listeyi kısaltıp boyutunu $d_{\text{sae}}$'den $k$'ya düşürmek.

Kaynaklar: [Elhage vd. 2022](https://arxiv.org/abs/2209.10652), [Bricken vd. 2023](https://transformer-circuits.pub/2023/monosemantic-features), [Templeton vd. 2024](https://transformer-circuits.pub/2024/scaling-monosemanticity/), [Gao vd. 2024](https://arxiv.org/abs/2406.04093). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Köprü: ai-guvence-37 temsil uzayında doğrusal ayrımı inceler; bu ders temsili seyrek özelliklere ayırıp müdahale (`feature clamping`) uygular.
:::

::: tahmin Top-K ve ReLU sırası neyi değiştirir?
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
ham = [-3.0, 1.5, -0.2, 4.0]
relu = [max(0.0, v) for v in ham]
k = 2
secilen = set(sorted(range(len(relu)), key=lambda i: (-relu[i], i))[:k])
kod = [relu[i] if i in secilen else 0.0 for i in range(len(relu))]
print("ReLU:", relu)
print("Top-2 kod:", kod)
print("Aktif oran:", sum(1 for v in kod if v > 0) / len(kod))
```
???
```cikti
ReLU: [0.0, 1.5, 0.0, 4.0]
Top-2 kod: [0.0, 1.5, 0.0, 4.0]
Aktif oran: 0.5
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: mutlak değere göre Top-2 seçilseydi `-3.0` hangi hataya yol açardı? Sonra üç kusurlu başlangıç kodunu çalıştır ve her birinin neyi kaçırdığını önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · Top-K Sparse Autoencoder kodlayıcısı
`sae_topk_kodla(aktivasyon, w_enc, b_enc, k)`: `aktivasyon` dolu liste ($d_{\text{model}}$); `w_enc` $d_{\text{sae}} \times d_{\text{model}}$ boyutunda dolu matris (liste listesi); `b_enc` $d_{\text{sae}}$ uzunluğunda liste; tüm elemanlar bool olmayan sonlu sayı. `k` bool olmayan `int` ve $1 \le k \le d_{\text{sae}}$. Her özellik için $z_i = \max(0.0, \sum_j W_{\text{enc}}[i][j]\cdot x_j + b_{\text{enc}}[i])$ hesapla. En büyük $k$ değeri (`(-z[i], i)` sırasıyla) koru, diğerlerini `0.0` yap ve $d_{\text{sae}}$ uzunluğunda yeni `float` listesi döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-41")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def sae_topk_kodla(aktivasyon, w_enc, b_enc, k):
    return [sum(w * a for w, a in zip(r, aktivasyon)) + b for r, b in zip(w_enc, b_enc)]

from ai_guvence_veri import json_yukle
v = json_yukle("veri/sae.json")["ornek"]
print("Kod:", sae_topk_kodla(v["aktivasyon"], v["w_enc"], v["b_enc"], v["k"]))
```
```test
def sinama1(f):
    import copy, math, random
    def _r(x, we, be, k):
        z = [max(0.0, sum(w * a for w, a in zip(r, x)) + b) for r, b in zip(we, be)]
        s = set(sorted(range(len(z)), key=lambda i: (-z[i], i))[:k])
        return [float(z[i]) if i in s else 0.0 for i in range(len(z))]
    def _y(a, b): return isinstance(a, list) and len(a) == len(b) and all(abs(p - q) < 1e-12 for p, q in zip(a, b))
    try:
        x = [1.0, 2.0]; we = [[1.0, 0.0], [0.0, 2.0], [-1.0, -1.0]]; be = [0.5, -0.5, 0.0]
        old = (copy.deepcopy(x), copy.deepcopy(we), copy.deepcopy(be))
        if not _y(f(x, we, be, 1), [0.0, 3.5, 0.0]) or (x, we, be) != old: return False
        if not _y(f(x, we, be, 2), [1.5, 3.5, 0.0]): return False
        if not _y(f(x, we, be, 3), [1.5, 3.5, 0.0]): return False
        # Eşitlik durumunda küçük indis seçilmeli
        if not _y(f([1.0], [[2.0], [2.0], [1.0]], [0.0, 0.0, 0.0], 1), [2.0, 0.0, 0.0]): return False
        # Negatif ön-aktivasyonlar 0.0 olmalı
        if not _y(f([1.0], [[-5.0], [-2.0]], [0.0, 0.0], 1), [0.0, 0.0]): return False
        rng = random.Random(41)
        for _ in range(25):
            din, dsae = rng.randint(2, 5), rng.randint(2, 6)
            rx = [rng.uniform(-2, 2) for _ in range(din)]
            rwe = [[rng.uniform(-1, 1) for _ in range(din)] for _ in range(dsae)]
            rbe = [rng.uniform(-0.5, 0.5) for _ in range(dsae)]
            rk = rng.randint(1, dsae)
            if not _y(f(list(rx), [list(r) for r in rwe], list(rbe), rk), _r(rx, rwe, rbe, rk)): return False
        for bad in (
            (None, we, be, 1), ([], we, be, 1), ([], [[]], [0.0], 1), ([True, 1.0], we, be, 1), ([float("nan"), 1.0], we, be, 1),
            (x, None, be, 1), (x, [], [], 1), (x, [[1.0]], be, 1), (x, we, [0.1], 1),
            (x, we, be, 0), (x, we, be, 4), (x, we, be, True), (x, we, be, 1.5),
            (x, [[1.0, float("inf")], [0.0, 1.0], [0.0, 0.0]], be, 1), (x, we, [True, 0.0, 0.0], 1)
        ):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
ok(sinama1(sae_topk_kodla), "ReLU, Top-K seçimi, eşitlik kuralı ve geçersiz girdi")
for ad, mut in [
    ("Top-K yok", lambda x, we, be, k: [max(0.0, sum(w * a for w, a in zip(r, x)) + b) for r, b in zip(we, be)]),
    ("ReLU yok", lambda x, we, be, k: [sum(w * a for w, a in zip(r, x)) + b for r, b in zip(we, be)]),
    ("hep sıfır", lambda x, we, be, k: [0.0 for _ in we])
]:
    ok(not sinama1(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(sae_topk_kodla, _il.import_module('ai_gercek_ai_guvence_41').referans_sae_topk_kodla, ([1.2, -0.5, 0.8, 0.3], [[1.0, 0.0, 0.5, 0.0], [-0.5, 1.0, 0.2, 0.1], [0.8, -0.4, 1.0, 0.2], [0.2, 0.1, -0.3, 0.9], [0.5, -0.2, 0.4, 0.1]], [0.1, -0.1, 0.0, 0.05, -0.05], 2), tohum=2614)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def sae_topk_kodla(aktivasyon, w_enc, b_enc, k):
    if not isinstance(aktivasyon, list) or not aktivasyon: raise ValueError("aktivasyon")
    for v in aktivasyon:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise ValueError("sayı")
    d_in = len(aktivasyon)
    if not isinstance(w_enc, list) or not w_enc or not isinstance(b_enc, list) or len(w_enc) != len(b_enc):
        raise ValueError("boyut")
    for r in w_enc:
        if not isinstance(r, list) or len(r) != d_in: raise ValueError("w_enc")
        for v in r:
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise ValueError("sayı")
    for v in b_enc:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise ValueError("b_enc")
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= len(w_enc): raise ValueError("k")
    z = [max(0.0, sum(w * a for w, a in zip(r, aktivasyon)) + b) for r, b in zip(w_enc, b_enc)]
    secilen = set(sorted(range(len(z)), key=lambda i: (-z[i], i))[:k])
    return [float(z[i]) if i in secilen else 0.0 for i in range(len(z))]

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v = json_yukle("veri/sae.json")["ornek"]
    print("Kod:", sae_topk_kodla(v["aktivasyon"], v["w_enc"], v["b_enc"], v["k"]))
```
```hint
Önce her satır için iç çarpım + bias değerine `max(0.0, ...)` uygula; sonra `sorted(range(len(z)), key=lambda i: (-z[i], i))[:k]` kümesindeki indisleri koruyup diğerlerini `0.0` yap.
```
:::

::: anlat Feature clamping ve doğrusal kod çözme
Bir `SAE` özelliği belirli bir davranışla eşleştiğinde, o özelliğin aktivasyonunu üstten sınırlamak (`feature clamping`) modelin iç temsilini kontrollü biçimde yönlendirir (`activation steering`).

`hedef_indis` konumundaki kod değeri $c_{\text{hedef}}$ için yeni değer $c'_{\text{hedef}} = \min(c_{\text{hedef}}, \text{tavan\_deger})$ olur. Böylece özellik zaten tavandan küçükse dokunulmaz, büyükse tavana indirilir; bastırılan miktar $c_{\text{hedef}} - c'_{\text{hedef}}$ olarak kaydedilir.

**Görev 2'de sık tuzaklar:** Orijinal `kod` listesini yerinde (`in-place`) değiştirmek. `min` yerine doğrudan `tavan_deger` atamak (özellik zaten `0.0` iken pozitif tavana yükseltmek).
:::

::: gorev 2 · Feature clamping ve yeniden üretim
`ozellik_clamping_uygula(kod, w_dec, b_dec, hedef_indis, tavan_deger)`: `kod` dolu liste ($d_{\text{sae}}$), elemanları $\ge 0$ olan bool olmayan sonlu sayı; `w_dec` $d_{\text{model}} \times d_{\text{sae}}$ matris; `b_dec` $d_{\text{model}}$ uzunluğunda liste; `hedef_indis` geçerli `int` indis; `tavan_deger` $\ge 0$ sonlu sayı. `kod` kopyasında `hedef_indis` elemanını `min(kod[hedef_indis], float(tavan_deger))` yap, $\hat{x}_j = \sum_i W_{\text{dec}}[j][i]\cdot c'_i + b_{\text{dec}}[j]$ hesapla ve `{"yeniden_uretilen": [...], "onceki_deger": float, "yeni_deger": float, "bastirilan": float}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-41")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def ozellik_clamping_uygula(kod, w_dec, b_dec, hedef_indis, tavan_deger):
    yeniden = [sum(w * c for w, c in zip(r, kod)) + b for r, b in zip(w_dec, b_dec)]
    return {"yeniden_uretilen": yeniden, "onceki_deger": kod[hedef_indis], "yeni_deger": kod[hedef_indis], "bastirilan": 0.0}

from ai_guvence_veri import json_yukle
v = json_yukle("veri/sae.json")["ornek"]
kod = [1.7, 0.0, 2.02, 0.0, 0.0]
print(ozellik_clamping_uygula(kod, v["w_dec"], v["b_dec"], v["hedef_indis"], v["tavan_deger"]))
```
```test
def sinama2(f):
    import copy, math, random
    def _r(c, wd, bd, idx, tav):
        cc = [float(v) for v in c]
        o = cc[idx]; y = min(o, float(tav)); cc[idx] = y
        u = [float(sum(w * q for w, q in zip(r, cc)) + b) for r, b in zip(wd, bd)]
        return {"yeniden_uretilen": u, "onceki_deger": o, "yeni_deger": y, "bastirilan": o - y}
    def _y(a, b):
        if not isinstance(a, dict) or set(a) != set(b): return False
        if len(a["yeniden_uretilen"]) != len(b["yeniden_uretilen"]): return False
        if not all(abs(p - q) < 1e-12 for p, q in zip(a["yeniden_uretilen"], b["yeniden_uretilen"])): return False
        return all(abs(a[k] - b[k]) < 1e-12 for k in ("onceki_deger", "yeni_deger", "bastirilan"))
    try:
        c = [2.0, 0.5, 0.0]; wd = [[1.0, 2.0, 3.0], [0.5, -1.0, 0.0]]; bd = [0.1, -0.2]
        old = (copy.deepcopy(c), copy.deepcopy(wd), copy.deepcopy(bd))
        if not _y(f(c, wd, bd, 0, 0.5), _r(c, wd, bd, 0, 0.5)) or (c, wd, bd) != old: return False
        if not _y(f(c, wd, bd, 1, 5.0), _r(c, wd, bd, 1, 5.0)): return False
        if f(c, wd, bd, 1, 5.0)["bastirilan"] != 0.0: return False
        if not _y(f(c, wd, bd, 0, 0.0), _r(c, wd, bd, 0, 0.0)): return False
        rng = random.Random(4141)
        for _ in range(25):
            dsae, dm = rng.randint(2, 6), rng.randint(2, 5)
            rc = [rng.uniform(0, 3) for _ in range(dsae)]
            rwd = [[rng.uniform(-1, 1) for _ in range(dsae)] for _ in range(dm)]
            rbd = [rng.uniform(-0.5, 0.5) for _ in range(dm)]
            ridx = rng.randrange(dsae); rtav = rng.uniform(0, 2)
            if not _y(f(list(rc), [list(r) for r in rwd], list(rbd), ridx, rtav), _r(rc, rwd, rbd, ridx, rtav)): return False
        for bad in (
            (None, wd, bd, 0, 0.5), ([], wd, bd, 0, 0.5), ([-0.1, 0.5, 0.0], wd, bd, 0, 0.5),
            ([True, 0.5, 0.0], wd, bd, 0, 0.5), (c, None, bd, 0, 0.5), (c, [], [], 0, 0.5), (c, [[1.0]], bd, 0, 0.5),
            (c, wd, [0.1], 0, 0.5), (c, wd, bd, -1, 0.5), (c, wd, bd, 3, 0.5), (c, wd, bd, True, 0.5),
            (c, wd, bd, 0, -0.1), (c, wd, bd, 0, True), (c, wd, bd, 0, float("nan"))
        ):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
ok(sinama2(ozellik_clamping_uygula), "feature clamping, doğrusal kod çözme, sınırlar ve geçersiz girdi")
for ad, mut in [
    ("clamping yok", lambda c, wd, bd, i, t: ozellik_clamping_uygula(c, wd, bd, i, 1e9)),
    ("min yerine tavan", lambda c, wd, bd, i, t: dict(ozellik_clamping_uygula(c, wd, bd, i, t), yeni_deger=float(t))),
    ("bias unutuldu", lambda c, wd, bd, i, t: ozellik_clamping_uygula(c, wd, [0.0 for _ in bd], i, t))
]:
    ok(not sinama2(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(ozellik_clamping_uygula, _il.import_module('ai_gercek_ai_guvence_41').referans_ozellik_clamping, ([1.7, 0.0, 2.02, 0.0, 0.0], [[0.6, -0.2, 0.5, 0.1, 0.3], [0.0, 0.7, -0.3, 0.1, -0.1], [0.3, 0.1, 0.6, -0.2, 0.2], [0.0, 0.1, 0.1, 0.8, 0.1]], [0.05, -0.05, 0.02, 0.01], 2, 0.2), tohum=3600)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def ozellik_clamping_uygula(kod, w_dec, b_dec, hedef_indis, tavan_deger):
    if not isinstance(kod, list) or not kod: raise ValueError("kod")
    for v in kod:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0: raise ValueError("kod")
    d_sae = len(kod)
    if not isinstance(w_dec, list) or not w_dec or not isinstance(b_dec, list) or len(w_dec) != len(b_dec):
        raise ValueError("boyut")
    for r in w_dec:
        if not isinstance(r, list) or len(r) != d_sae: raise ValueError("w_dec")
        for v in r:
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise ValueError("sayı")
    for v in b_dec:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise ValueError("b_dec")
    if isinstance(hedef_indis, bool) or not isinstance(hedef_indis, int) or not 0 <= hedef_indis < d_sae:
        raise ValueError("hedef_indis")
    if isinstance(tavan_deger, bool) or not isinstance(tavan_deger, (int, float)) or not math.isfinite(tavan_deger) or tavan_deger < 0:
        raise ValueError("tavan_deger")
    kod_c = [float(v) for v in kod]
    onceki = float(kod_c[hedef_indis])
    yeni = min(onceki, float(tavan_deger))
    kod_c[hedef_indis] = yeni
    yeniden = [float(sum(w * c for w, c in zip(r, kod_c)) + b) for r, b in zip(w_dec, b_dec)]
    return {"yeniden_uretilen": yeniden, "onceki_deger": onceki, "yeni_deger": yeni, "bastirilan": onceki - yeni}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v = json_yukle("veri/sae.json")["ornek"]
    kod = [1.7, 0.0, 2.02, 0.0, 0.0]
    print(ozellik_clamping_uygula(kod, v["w_dec"], v["b_dec"], v["hedef_indis"], v["tavan_deger"]))
```
```hint
`kod` listesini kopyala, yalnız `hedef_indis` elemanını `min(onceki, float(tavan_deger))` ile güncelle ve `w_dec` satırlarıyla iç çarpıp `b_dec` ekle.
```
:::

::: anlat Yeniden üretim kaybı ve L0 seyreklik ölçümü
Bir `SAE` raporunda iki sayı birlikte okunur:
- **MSE:** $\frac{1}{d_{\text{model}}} \sum_{j=1}^{d_{\text{model}}} (x_j - \hat{x}_j)^2$
- **L1 ve Toplam Kayıp:** $\text{L1} = \sum_{i=1}^{d_{\text{sae}}} |c_i|$ ve $\text{toplam\_kayip} = \text{MSE} + \lambda_{\text{L1}} \cdot \text{L1}$
- **L0 Oranı:** `c > 1e-9` koşulunu sağlayan aktif özellik sayısının $d_{\text{sae}}$'ye oranı.

**Görev 3'te sık tuzaklar:** MSE'yi uzunluğa bölmeden toplam kare fark olarak bırakmak veya `l0_orani` hesabında sıfır olan koordinatları da aktif saymak.
:::

::: gorev 3 · SAE kayıp ve seyreklik raporu
`sae_kayip_ve_seyreklik(aktivasyon, yeniden_uretilen, kod, l1_katsayi)`: `aktivasyon` ve `yeniden_uretilen` aynı uzunlukta dolu liste; `kod` elemanları $\ge 0$ olan dolu liste; `l1_katsayi` $\ge 0$ sonlu sayı; tüm sayılar bool olmayan sonlu sayı. `{"mse": float, "l1": float, "toplam_kayip": float, "l0_orani": float}` döndür (`l0_orani` için aktiflik eşiği `c > 1e-9`). Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-41")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def sae_kayip_ve_seyreklik(aktivasyon, yeniden_uretilen, kod, l1_katsayi):
    mse = sum((a - y) ** 2 for a, y in zip(aktivasyon, yeniden_uretilen))
    l1 = sum(kod)
    return {"mse": mse, "l1": l1, "toplam_kayip": mse, "l0_orani": 1.0}

from ai_guvence_veri import json_yukle
v = json_yukle("veri/sae.json")["ornek"]
kod = [1.7, 0.0, 2.02, 0.0, 0.0]
yeniden = [2.08, -0.656, 1.742, 0.212]
print(sae_kayip_ve_seyreklik(v["aktivasyon"], yeniden, kod, v["l1_katsayi"]))
```
```test
def sinama3(f):
    import copy, math, random
    def _r(a, y, c, l1k):
        mse = sum((p - q) ** 2 for p, q in zip(a, y)) / len(a)
        l1 = sum(abs(v) for v in c)
        akt = sum(1 for v in c if v > 1e-9) / len(c)
        return {"mse": float(mse), "l1": float(l1), "toplam_kayip": float(mse + l1k * l1), "l0_orani": float(akt)}
    def _y(p, q): return isinstance(p, dict) and set(p) == set(q) and all(abs(p[k] - q[k]) < 1e-12 for k in q)
    try:
        a = [1.0, 2.0]; y = [1.0, 4.0]; c = [0.0, 2.5, 0.0, 1.5]; old = (list(a), list(y), list(c))
        if not _y(f(a, y, c, 0.1), {"mse": 2.0, "l1": 4.0, "toplam_kayip": 2.4, "l0_orani": 0.5}) or (a, y, c) != old:
            return False
        if not _y(f([0.0], [0.0], [0.0, 0.0], 0.5), {"mse": 0.0, "l1": 0.0, "toplam_kayip": 0.0, "l0_orani": 0.0}):
            return False
        for deger, oran in ((0.75e-9, 0.0), (1e-9, 0.0), (1.5e-9, 1.0)):
            if f([0.0], [0.0], [deger], 0.0)["l0_orani"] != oran:
                return False
        rng = random.Random(4142)
        for _ in range(25):
            n, m = rng.randint(1, 6), rng.randint(2, 8)
            ra = [rng.uniform(-2, 2) for _ in range(n)]
            ry = [rng.uniform(-2, 2) for _ in range(n)]
            rc = [0.0 if rng.random() < 0.5 else rng.uniform(0.01, 3.0) for _ in range(m)]
            rl = rng.uniform(0.0, 0.5)
            if not _y(f(list(ra), list(ry), list(rc), rl), _r(ra, ry, rc, rl)): return False
        for bad in (
            (None, y, c, 0.1), (a, None, c, 0.1), ([], [], c, 0.1), ([1.0], y, c, 0.1),
            (a, y, [], 0.1), (a, y, [-0.1, 1.0], 0.1), (a, y, c, -0.1), (a, y, c, True),
            ([True, 1.0], y, c, 0.1), (a, [float("nan"), 1.0], c, 0.1), (a, y, [float("inf"), 1.0], 0.1)
        ):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
ok(sinama3(sae_kayip_ve_seyreklik), "MSE ortalaması, L1 cezası, L0 oranı ve geçersiz girdi")
for ad, mut in [
    ("MSE bölünmedi", lambda a, y, c, l: dict(sae_kayip_ve_seyreklik(a, y, c, l), mse=sae_kayip_ve_seyreklik(a, y, c, l)["mse"] * 2 + 1)),
    ("L1 eklenmedi", lambda a, y, c, l: dict(sae_kayip_ve_seyreklik(a, y, c, l), toplam_kayip=sae_kayip_ve_seyreklik(a, y, c, l)["mse"])),
    ("L0 sabit 1", lambda a, y, c, l: dict(sae_kayip_ve_seyreklik(a, y, c, l), l0_orani=1.0))
]:
    ok(not sinama3(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(sae_kayip_ve_seyreklik, _il.import_module('ai_gercek_ai_guvence_41').referans_sae_kayip, ([1.2, -0.5, 0.8, 0.3], [2.08, -0.656, 1.742, 0.212], [1.7, 0.0, 2.02, 0.0, 0.0], 0.05), tohum=3480)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def sae_kayip_ve_seyreklik(aktivasyon, yeniden_uretilen, kod, l1_katsayi):
    if not isinstance(aktivasyon, list) or not isinstance(yeniden_uretilen, list) or not aktivasyon or len(aktivasyon) != len(yeniden_uretilen):
        raise ValueError("aktivasyon")
    for v in aktivasyon + yeniden_uretilen:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise ValueError("sayı")
    if not isinstance(kod, list) or not kod: raise ValueError("kod")
    for v in kod:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0: raise ValueError("kod")
    if isinstance(l1_katsayi, bool) or not isinstance(l1_katsayi, (int, float)) or not math.isfinite(l1_katsayi) or l1_katsayi < 0:
        raise ValueError("l1_katsayi")
    mse = sum((a - y) ** 2 for a, y in zip(aktivasyon, yeniden_uretilen)) / len(aktivasyon)
    l1 = sum(abs(c) for c in kod)
    aktif = sum(1 for c in kod if c > 1e-9)
    return {"mse": float(mse), "l1": float(l1), "toplam_kayip": float(mse + l1_katsayi * l1), "l0_orani": float(aktif / len(kod))}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    v = json_yukle("veri/sae.json")["ornek"]
    kod = [1.7, 0.0, 2.02, 0.0, 0.0]
    yeniden = [2.08, -0.656, 1.742, 0.212]
    print(sae_kayip_ve_seyreklik(v["aktivasyon"], yeniden, kod, v["l1_katsayi"]))
```
```hint
MSE için kare farklar toplamını `len(aktivasyon)` değerine böl. `l0_orani` için `c > 1e-9` olan eleman sayısını `len(kod)` değerine böl.
```
:::

::: anlat Hata vitrini · çalışmış yanlış rapor
Yazar, kusurlu başlangıç kodlarını görünür sentetik veriyle gerçekten çalıştırdı ve sonucu `outputs/yeni-ai-guvence-41/gorunur-run-1.json` dosyasına kaydetti. Kusurlu kod Top-K ve ReLU uygulamadığı için negatif aktivasyonları (`-0.51`) korur, `feature clamping` adımında `bastirilan=0.0` döndürür ve `l0_orani=1.0` ile seyrekliği tamamen yanlış raporlar. Doğru kod ise yalnızca en güçlü 2 özelliği (`[1.7, 0.0, 2.02, 0.0, 0.0]`, `l0_orani=0.4`) bırakır ve 2. özelliği `0.2` tavanına çekerek `1.82` birim aktivasyon bastırır.

Bu kaydedilmiş bir hesaplama çıktısıdır, model yanıtı değildir ve rapor sentetiktir. Kusurlu çıktıyı görüp "`feature clamping` hiçbir şeyi değiştirmedi" diyen biri hangi satırdaki eksikliği kaçırmıştır? Kendi cümlenle açıkla. Gerçek finaldeki ölçüm ayrıca üretilir; bu sayılar onun yerine konmaz.
:::

::: anlat Gerçek deney: SmolLM2'nin artık akımında "kod" özelliğini bulmak ve kıstırmak
Final, yerel önbellekteki gerçek **SmolLM2-135M** modelini (indirme yok) iki küçük derlemden geçirir: 16 kısa Python kod parçası ve 16 İngilizce düzyazı cümlesi. 15. katmanın çıktısındaki 576 boyutlu artık akım (`residual stream`) aktivasyonları, ortalama norma bölünerek ölçeklenir. İlk 12'şer metnin aktivasyonları üzerinde GPU'da bir Top-K SAE ($d_{\text{sae}} = 512$, $k = 16$) eğitilir; son 4'er metin ayrık değerlendirme için ayrılır.

Kodda en sık, düzyazıda en seyrek ateşleyen latent "kod özelliği" seçilir. Ardından iki şey ölçülür:
1. **Senin işlevlerin:** ayrık tokenlardan seçilen örneklerde `sae_topk_kodla`, `ozellik_clamping_uygula` ve `sae_kayip_ve_seyreklik` bağımsız referansla karşılaştırılır.
2. **Davranış etkisi (activation steering):** modelin 15. katman çıktısı ileri geçişte SAE yeniden üretimiyle değiştirilir; bir kez özellik serbestken, bir kez `0.0` tavanına kıstırılmışken. Ayrık kod ve düzyazı metinlerinde dil modeli kaybı ölçülür. Seçici bir özellik kodun kaybını belirgin artırmalı, düzyazıya neredeyse dokunmamalıdır.

Deney ayrıca SAE'nin araya girme maliyetini de yazar: küçük bir derlemde eğitilen SAE yeni metni kusursuz yeniden üretemez ve kayıp yükselir. Bu yüzden steering etkisi "SAE serbest" ile "SAE kıstırılmış" arasındaki farka göre ölçülür, ham modele göre değil.

Kabul: üç işlevin bağımsız referansla aynı sonucu vermesi, Top-K seyreklik sınırının aşılmaması, seçilen latentin ayrık metinde kodda düzyazıdan sık ateşlemesi ve kıstırmanın ayrık kod kaybını en az 0.05 nat ve düzyazıdakinin en az 5 katı artırması.

**İkinci kavram: dalkavukluk (sycophancy).** Plan, kod gibi bir konu değil, "aldatma / dalkavukluk / arka kapı" gibi bir **davranış** özelliği istiyordu. Final aynı yöntemi ikinci kez uygular: 16 dalkavukça asistan yanıtı ("What a brilliant question! You are absolutely right…") ve 16 nötr yanıt ("The function returns the wrong value when the list is empty…"). Ayrı bir SAE eğitilir, dalkavukçada sık ateşleyen latent seçilir ve aynı steering ölçümü yapılır. Yazarın koşularında (sabit tohum):
- Latent ayrık dalkavukça yanıt tokenlarının **%64**'ünde, nötr yanıtların **%6**'sında ateşledi.
- Kıstırmak dalkavukça metinlerin kaybını **+0.377 nat** artırdı; nötr metinlerde değişim −0.010 nat oldu. Kod latentinden çok daha güçlü ve seçici bir etki.
- **Ama latenti en çok tetikleyen tokenler ` You`, ` your`, ` are` oldu.** Latent büyük olasılıkla "ikinci şahısla övgü hitabını" izliyor, modelin içsel bir "dalkavukluk eğilimini" değil. Derlemdeki dalkavukça cümlelerin hepsi "you" ile başlayan övgüler, nötr cümlelerin çoğu değil.

Bu, yorumlanabilirlik araştırmasının temel tuzağıdır: bir latentin bir kavramla **ilişkili** ateşlemesi, o kavramı **temsil ettiğini** göstermez. Gerçek bir test için, aynı hitap kalıbını kullanan dalkavuk olmayan cümleler ("You need to restart the service") gibi karşı örnekler gerekir.

**Kanıt dosyasını oku:** `ateslenme_ayrik`, `kayiplar` ve `steering_kod_artis` / `steering_duzyazi_artis` alanlarına bak. Soru 1: `ort_l0_orani` neden $k / d_{\text{sae}} = 16 / 512$ değerini aşamaz? Soru 2: Latent eğitim metninde %45, ayrık metinde %37 ateşledi; düzyazıda da bir miktar ateşlemesi monosemantiklik iddiası için ne anlama gelir? Soru 3: SAE'nin araya girme maliyeti (`temiz` → `sae` kaybı) neden bu kadar büyük; daha büyük bir derlem ya da daha büyük $d_{\text{sae}}$ bunu nasıl etkilerdi? Soru 4: `dalkavukluk.ornek_tetikleyen_tokenler`'e bakarak, latentin gerçekten dalkavukluğu mu yoksa "you" hitabını mı izlediğini ayırmak için hangi 4 karşı örnek cümleyi derleme eklerdin? Cevabını tezgâhta yorum olarak yaz; otomatik test bu serbest açıklamayı puanlamaz.
:::

::: gorev Gerçek deney · SmolLM2-135M artık akımında SAE kodlama ve feature clamping
Önceki üç görevin `sae_topk_kodla`, `ozellik_clamping_uygula` ve `sae_kayip_ve_seyreklik` işlevlerini birleştir. Çalıştır gerçek tabloyu gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 180
```
```starter
import ai_lab
import math
def sae_topk_kodla(aktivasyon, w_enc, b_enc, k):
    return [sum(w * a for w, a in zip(r, aktivasyon)) + b for r, b in zip(w_enc, b_enc)]
def ozellik_clamping_uygula(kod, w_dec, b_dec, hedef_indis, tavan_deger):
    yeniden = [sum(w * c for w, c in zip(r, kod)) + b for r, b in zip(w_dec, b_dec)]
    return {"yeniden_uretilen": yeniden, "onceki_deger": kod[hedef_indis], "yeni_deger": kod[hedef_indis], "bastirilan": 0.0}
def sae_kayip_ve_seyreklik(aktivasyon, yeniden_uretilen, kod, l1_katsayi):
    mse = sum((a - y) ** 2 for a, y in zip(aktivasyon, yeniden_uretilen))
    l1 = sum(kod)
    return {"mse": mse, "l1": l1, "toplam_kayip": mse, "l0_orani": 1.0}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_41 as D
    D.goster(sae_topk_kodla, ozellik_clamping_uygula, sae_kayip_ve_seyreklik)
```
```test
import ai_lab, math
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('referans_sae_topk_kodla', 'referans_ozellik_clamping', 'referans_sae_kayip', 'kanit_yaz', '_yakin'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
sae_topk_kodla = need("sae_topk_kodla")
ozellik_clamping_uygula = need("ozellik_clamping_uygula")
sae_kayip_ve_seyreklik = need("sae_kayip_ve_seyreklik")
def sinama1(f):
    import copy, math, random
    def _r(x, we, be, k):
        z = [max(0.0, sum(w * a for w, a in zip(r, x)) + b) for r, b in zip(we, be)]
        s = set(sorted(range(len(z)), key=lambda i: (-z[i], i))[:k])
        return [float(z[i]) if i in s else 0.0 for i in range(len(z))]
    def _y(a, b): return isinstance(a, list) and len(a) == len(b) and all(abs(p - q) < 1e-12 for p, q in zip(a, b))
    try:
        x = [1.0, 2.0]; we = [[1.0, 0.0], [0.0, 2.0], [-1.0, -1.0]]; be = [0.5, -0.5, 0.0]
        old = (copy.deepcopy(x), copy.deepcopy(we), copy.deepcopy(be))
        if not _y(f(x, we, be, 1), [0.0, 3.5, 0.0]) or (x, we, be) != old: return False
        if not _y(f(x, we, be, 2), [1.5, 3.5, 0.0]): return False
        if not _y(f([1.0], [[2.0], [2.0], [1.0]], [0.0, 0.0, 0.0], 1), [2.0, 0.0, 0.0]): return False
        rng = random.Random(41)
        for _ in range(25):
            din, dsae = rng.randint(2, 5), rng.randint(2, 6)
            rx = [rng.uniform(-2, 2) for _ in range(din)]
            rwe = [[rng.uniform(-1, 1) for _ in range(din)] for _ in range(dsae)]
            rbe = [rng.uniform(-0.5, 0.5) for _ in range(dsae)]
            rk = rng.randint(1, dsae)
            if not _y(f(list(rx), [list(r) for r in rwe], list(rbe), rk), _r(rx, rwe, rbe, rk)): return False
        for bad in ((None, we, be, 1), ([], we, be, 1), ([], [[]], [0.0], 1), ([True, 1.0], we, be, 1), (x, we, be, 0), (x, we, be, 4), (x, we, be, True)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama1(sae_topk_kodla), "ReLU, Top-K seçimi, eşitlik kuralı ve geçersiz girdi")
for ad, mut in [
    ("Top-K yok", lambda x, we, be, k: [max(0.0, sum(w * a for w, a in zip(r, x)) + b) for r, b in zip(we, be)]),
    ("ReLU yok", lambda x, we, be, k: [sum(w * a for w, a in zip(r, x)) + b for r, b in zip(we, be)]),
    ("hep sıfır", lambda x, we, be, k: [0.0 for _ in we])
]:
    kontrol(not sinama1(mut), "mutant reddedildi: " + ad)
def sinama2(f):
    import copy, math, random
    def _r(c, wd, bd, idx, tav):
        cc = [float(v) for v in c]
        o = cc[idx]; y = min(o, float(tav)); cc[idx] = y
        u = [float(sum(w * q for w, q in zip(r, cc)) + b) for r, b in zip(wd, bd)]
        return {"yeniden_uretilen": u, "onceki_deger": o, "yeni_deger": y, "bastirilan": o - y}
    def _y(a, b):
        if not isinstance(a, dict) or set(a) != set(b): return False
        return all(abs(p - q) < 1e-12 for p, q in zip(a["yeniden_uretilen"], b["yeniden_uretilen"])) and all(abs(a[k] - b[k]) < 1e-12 for k in ("onceki_deger", "yeni_deger", "bastirilan"))
    try:
        c = [2.0, 0.5, 0.0]; wd = [[1.0, 2.0, 3.0], [0.5, -1.0, 0.0]]; bd = [0.1, -0.2]
        old = (copy.deepcopy(c), copy.deepcopy(wd), copy.deepcopy(bd))
        if not _y(f(c, wd, bd, 0, 0.5), _r(c, wd, bd, 0, 0.5)) or (c, wd, bd) != old: return False
        if not _y(f(c, wd, bd, 1, 5.0), _r(c, wd, bd, 1, 5.0)): return False
        rng = random.Random(4141)
        for _ in range(25):
            dsae, dm = rng.randint(2, 6), rng.randint(2, 5)
            rc = [rng.uniform(0, 3) for _ in range(dsae)]
            rwd = [[rng.uniform(-1, 1) for _ in range(dsae)] for _ in range(dm)]
            rbd = [rng.uniform(-0.5, 0.5) for _ in range(dm)]
            ridx = rng.randrange(dsae); rtav = rng.uniform(0, 2)
            if not _y(f(list(rc), [list(r) for r in rwd], list(rbd), ridx, rtav), _r(rc, rwd, rbd, ridx, rtav)): return False
        for bad in ((None, wd, bd, 0, 0.5), ([], wd, bd, 0, 0.5), ([-0.1, 0.5, 0.0], wd, bd, 0, 0.5), (c, [], [], 0, 0.5), (c, wd, bd, -1, 0.5), (c, wd, bd, 3, 0.5), (c, wd, bd, 0, -0.1), (c, wd, bd, 0, True)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama2(ozellik_clamping_uygula), "feature clamping, doğrusal kod çözme, sınırlar ve geçersiz girdi")
for ad, mut in [
    ("clamping yok", lambda c, wd, bd, i, t: ozellik_clamping_uygula(c, wd, bd, i, 1e9)),
    ("min yerine tavan", lambda c, wd, bd, i, t: dict(ozellik_clamping_uygula(c, wd, bd, i, t), yeni_deger=float(t))),
    ("bias unutuldu", lambda c, wd, bd, i, t: ozellik_clamping_uygula(c, wd, [0.0 for _ in bd], i, t))
]:
    kontrol(not sinama2(mut), "mutant reddedildi: " + ad)
def sinama3(f):
    import copy, math, random
    def _r(a, y, c, l1k):
        mse = sum((p - q) ** 2 for p, q in zip(a, y)) / len(a)
        l1 = sum(abs(v) for v in c)
        akt = sum(1 for v in c if v > 1e-9) / len(c)
        return {"mse": float(mse), "l1": float(l1), "toplam_kayip": float(mse + l1k * l1), "l0_orani": float(akt)}
    def _y(p, q): return isinstance(p, dict) and set(p) == set(q) and all(abs(p[k] - q[k]) < 1e-12 for k in q)
    try:
        a = [1.0, 2.0]; y = [1.0, 4.0]; c = [0.0, 2.5, 0.0, 1.5]; old = (list(a), list(y), list(c))
        if not _y(f(a, y, c, 0.1), {"mse": 2.0, "l1": 4.0, "toplam_kayip": 2.4, "l0_orani": 0.5}) or (a, y, c) != old:
            return False
        for deger, oran in ((0.75e-9, 0.0), (1e-9, 0.0), (1.5e-9, 1.0)):
            if f([0.0], [0.0], [deger], 0.0)["l0_orani"] != oran:
                return False
        rng = random.Random(4142)
        for _ in range(25):
            n, m = rng.randint(1, 6), rng.randint(2, 8)
            ra = [rng.uniform(-2, 2) for _ in range(n)]; ry = [rng.uniform(-2, 2) for _ in range(n)]
            rc = [0.0 if rng.random() < 0.5 else rng.uniform(0.01, 3.0) for _ in range(m)]
            rl = rng.uniform(0.0, 0.5)
            if not _y(f(list(ra), list(ry), list(rc), rl), _r(ra, ry, rc, rl)): return False
        for bad in ((None, y, c, 0.1), ([], [], c, 0.1), ([1.0], y, c, 0.1), (a, y, [-0.1, 1.0], 0.1), (a, y, c, -0.1), (a, y, c, True)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama3(sae_kayip_ve_seyreklik), "MSE ortalaması, L1 cezası, L0 oranı ve geçersiz girdi")
for ad, mut in [
    ("MSE bölünmedi", lambda a, y, c, l: dict(sae_kayip_ve_seyreklik(a, y, c, l), mse=sae_kayip_ve_seyreklik(a, y, c, l)["mse"] * 2 + 1)),
    ("L1 eklenmedi", lambda a, y, c, l: dict(sae_kayip_ve_seyreklik(a, y, c, l), toplam_kayip=sae_kayip_ve_seyreklik(a, y, c, l)["mse"])),
    ("L0 sabit 1", lambda a, y, c, l: dict(sae_kayip_ve_seyreklik(a, y, c, l), l0_orani=1.0))
]:
    kontrol(not sinama3(mut), "mutant reddedildi: " + ad)
# farksal tarama (final)
import importlib as _il
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_R = _il.import_module('sandbox.ai_gercek_ai_guvence_41')
for _ad, _ref, _taban, _toh in (
    ('sae_topk_kodla', 'referans_sae_topk_kodla', ([1.2, -0.5, 0.8, 0.3], [[1.0, 0.0, 0.5, 0.0], [-0.5, 1.0, 0.2, 0.1], [0.8, -0.4, 1.0, 0.2], [0.2, 0.1, -0.3, 0.9], [0.5, -0.2, 0.4, 0.1]], [0.1, -0.1, 0.0, 0.05, -0.05], 2), 3136),
    ('ozellik_clamping_uygula', 'referans_ozellik_clamping', ([1.7, 0.0, 2.02, 0.0, 0.0], [[0.6, -0.2, 0.5, 0.1, 0.3], [0.0, 0.7, -0.3, 0.1, -0.1], [0.3, 0.1, 0.6, -0.2, 0.2], [0.0, 0.1, 0.1, 0.8, 0.1]], [0.05, -0.05, 0.02, 0.01], 2, 0.2), 4122),
    ('sae_kayip_ve_seyreklik', 'referans_sae_kayip', ([1.2, -0.5, 0.8, 0.3], [2.08, -0.656, 1.742, 0.212], [1.7, 0.0, 2.02, 0.0, 0.0], 0.05), 4002),
):
    _t, _g = _ff(need(_ad), getattr(_R, _ref), _taban, tohum=_toh)
    kontrol(_t, "farksal tarama (" + _ad + "): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
if not all(checks): stop()
from sandbox import ai_gercek_ai_guvence_41 as D
try: r = D.deney(sae_topk_kodla, ozellik_clamping_uygula, sae_kayip_ve_seyreklik)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r["kod_ayni"], "gerçek aktivasyonlarda Top-K SAE kodlama bağımsız hesapla aynı")
kontrol(r["clamp_ayni"], "gerçek kodlarda feature clamping bağımsız hesapla aynı")
kontrol(r["kayip_ayni"], "gerçek aktivasyonlarda SAE kayıp ve seyreklik raporu bağımsız hesapla aynı")
kontrol(r["max_l0_orani"] <= r["ayarlar"]["k"] / r["ayarlar"]["d_sae"] + 1e-9, "Top-K seyreklik sınırı aşılmadı")
kontrol(r["ateslenme_ayrik"]["kod"] > r["ateslenme_ayrik"]["duzyazi"], "seçilen SAE latenti ayrık metinlerde kodda düzyazıdan sık ateşledi")
kontrol(r["steering_kod_artis"] >= 0.05 and r["steering_kod_artis"] >= 5 * max(r["steering_duzyazi_artis"], 0.0), "latenti kıstırmak ayrık kod kaybını seçici biçimde artırdı (≥ 0.05 nat ve düzyazının ≥ 5 katı)")
dk = r["dalkavukluk"]
kontrol(dk["ateslenme_ayrik"]["dalkavuk"] > dk["ateslenme_ayrik"]["notr"] + 0.3 and dk["steering"]["dalkavuk"] >= 0.05 and dk["steering"]["dalkavuk"] >= 5 * max(dk["steering"]["notr"], 0.0),
        "dalkavukluk latenti ayrık yanıtlarda seçici ateşledi (%.2f / %.2f) ve kıstırılması seçici etki yaptı (+%.3f / %+.3f nat)" % (
            dk["ateslenme_ayrik"]["dalkavuk"], dk["ateslenme_ayrik"]["notr"], dk["steering"]["dalkavuk"], dk["steering"]["notr"]))
ai_lab.kanit_yaz("ai-guvence-41-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-guvence-41", "deney": r})
```
```solution
import ai_lab
import math
def sae_topk_kodla(aktivasyon, w_enc, b_enc, k):
    if not isinstance(aktivasyon, list) or not aktivasyon: raise ValueError("aktivasyon")
    for v in aktivasyon:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise ValueError("sayı")
    d_in = len(aktivasyon)
    if not isinstance(w_enc, list) or not w_enc or not isinstance(b_enc, list) or len(w_enc) != len(b_enc):
        raise ValueError("boyut")
    for r in w_enc:
        if not isinstance(r, list) or len(r) != d_in: raise ValueError("w_enc")
        for v in r:
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise ValueError("sayı")
    for v in b_enc:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise ValueError("b_enc")
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= len(w_enc): raise ValueError("k")
    z = [max(0.0, sum(w * a for w, a in zip(r, aktivasyon)) + b) for r, b in zip(w_enc, b_enc)]
    secilen = set(sorted(range(len(z)), key=lambda i: (-z[i], i))[:k])
    return [float(z[i]) if i in secilen else 0.0 for i in range(len(z))]
def ozellik_clamping_uygula(kod, w_dec, b_dec, hedef_indis, tavan_deger):
    if not isinstance(kod, list) or not kod: raise ValueError("kod")
    for v in kod:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0: raise ValueError("kod")
    d_sae = len(kod)
    if not isinstance(w_dec, list) or not w_dec or not isinstance(b_dec, list) or len(w_dec) != len(b_dec):
        raise ValueError("boyut")
    for r in w_dec:
        if not isinstance(r, list) or len(r) != d_sae: raise ValueError("w_dec")
        for v in r:
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise ValueError("sayı")
    for v in b_dec:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise ValueError("b_dec")
    if isinstance(hedef_indis, bool) or not isinstance(hedef_indis, int) or not 0 <= hedef_indis < d_sae:
        raise ValueError("hedef_indis")
    if isinstance(tavan_deger, bool) or not isinstance(tavan_deger, (int, float)) or not math.isfinite(tavan_deger) or tavan_deger < 0:
        raise ValueError("tavan_deger")
    kod_c = [float(v) for v in kod]
    onceki = float(kod_c[hedef_indis])
    yeni = min(onceki, float(tavan_deger))
    kod_c[hedef_indis] = yeni
    yeniden = [float(sum(w * c for w, c in zip(r, kod_c)) + b) for r, b in zip(w_dec, b_dec)]
    return {"yeniden_uretilen": yeniden, "onceki_deger": onceki, "yeni_deger": yeni, "bastirilan": onceki - yeni}
def sae_kayip_ve_seyreklik(aktivasyon, yeniden_uretilen, kod, l1_katsayi):
    if not isinstance(aktivasyon, list) or not isinstance(yeniden_uretilen, list) or not aktivasyon or len(aktivasyon) != len(yeniden_uretilen):
        raise ValueError("aktivasyon")
    for v in aktivasyon + yeniden_uretilen:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v): raise ValueError("sayı")
    if not isinstance(kod, list) or not kod: raise ValueError("kod")
    for v in kod:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0: raise ValueError("kod")
    if isinstance(l1_katsayi, bool) or not isinstance(l1_katsayi, (int, float)) or not math.isfinite(l1_katsayi) or l1_katsayi < 0:
        raise ValueError("l1_katsayi")
    mse = sum((a - y) ** 2 for a, y in zip(aktivasyon, yeniden_uretilen)) / len(aktivasyon)
    l1 = sum(abs(c) for c in kod)
    aktif = sum(1 for c in kod if c > 1e-9)
    return {"mse": float(mse), "l1": float(l1), "toplam_kayip": float(mse + l1_katsayi * l1), "l0_orani": float(aktif / len(kod))}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_41 as D
    D.goster(sae_topk_kodla, ozellik_clamping_uygula, sae_kayip_ve_seyreklik)
```
```hint
Üç işlevi aynen birleştir. Top-K seyrekliği ile `feature clamping` sonrası dil modeli kaybı (nat) değişimini ve tetikleyen tokenleri birlikte incele.
```
:::

::: anlat Sınır
Bu ders gerçek SmolLM2-135M'in 15. katman artık akımında, küçük el yazımı derlemlerle eğitilen iki Top-K `Sparse Autoencoder` ile hem "Python kodu" hem de "dalkavukça yanıt (`sycophancy`)" korpuslarında seçici ateşlenen latentleri bulur ve `feature clamping` etkisini ölçer. Ancak dalkavukluk latentini en çok tetikleyen tokenlerin (`You`, `your`, `are`) gösterdiği gibi korelasyonel seçicilik içsel davranış temsili kanıtı değildir; aldatma veya arka kapı tetikleyicileri ölçülmez, küçük derlemde SAE araya girme maliyeti yüksektir ve tek bir latentin bastırılması zararlı davranışı yan etkisiz sildiğini kanıtlamaz.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Süperpozisyon engeli (25 sn).** "Bir katmandaki tek bir nöron birden çok kavramı üst üste (`polysemanticity`) taşıdığı için nöronu sıfırlamak alakasız yetenekleri de bozar; Top-K `SAE` artık akımı daha geniş ve en fazla $k$ aktif bileşenli seyrek bir sözlüğe açar."
2. **`Feature clamping` ve seçici etki (35 sn).** "Kodlayıcıdan çıkan hedef latent $c_i \leftarrow \min(c_i, \text{tavan})$ ile üstten sınırlandığında, SmolLM2 artık akımında ayrık kod metinlerinin kaybı düzyazının en az 5 katı kadar yükselir."
3. **Yorumlanabilirlik tuzağı (35 sn).** "Dalkavukluk korpusunda eğitilen ikinci SAE latenti ayrık yanıtlarda güçlü seçici kayıp artışı üretse de en çok `You / your` hitap tokenlerinde ateşler; yani korelasyon tek başına içsel davranış kavramını kanıtlamaz."
4. **Soru (25 sn).** "Bir SAE latentinin gerçekten dalkavukluğu mu yoksa ikinci şahıs övgü kalıbını mı izlediğini ayırmak için derleme hangi karşı örnekleri eklersin?"
:::
