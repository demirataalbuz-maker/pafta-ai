---
id: ai-temel-27
title: Speculative Decoding ve Red Örneklemesi · Kayıpsız Hızlandırma Mekaniği
summary: Taslak (draft) ve hedef (target) dağılımlar arasında Leviathan rejection sampling kabul olasılığını, artık dağılımı ve spekülatif doğrulama turunu GPU'da doğrula.
esleme: ai-temel-03, ai-temel-07, ai-temel-18
timeout: 60
---

::: anlat Küçük bir taslak model büyük modelin dağılımını hiç bozmadan nasıl hızlandırır?
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| `speculative decoding` küçük bir taslak (draft) modelin ürettiği $\gamma$ tokenı büyük hedef (target) modelde tek ileri geçişte paralel doğrular ve `rejection sampling` ile hedef dağılımı kayıpsız korur | İlk üç görev: `veri/speculative.json` içindeki **sentetik** hedef/taslak dağılımları ve turlar. Final: yerel **SmolLM2-135M** üzerinde erken çıkış + damıtılmış doğrusal adaptör (taslak) ve tam 30 katmanlı model (hedef) ile spekülatif turlar | Donanım bellek bant genişliği (memory bandwidth) kazancının her batch boyutunda aynı kalacağını söyleyemez |
| İlk reddedilen adımda $\text{norm}(\max(0, p(x)-q(x)))$ artık dağılımından (residual distribution) kurtarma tokenı seçilerek hedef dağılım tam olarak dengelenir | Kabul oranı $\min(1, p(x)/q(x))$, normalize artık dağılım ve ardışık red/kabul özeti | Taslak modelin kabul oranının alan dışı (out-of-domain) girdilerde düşmeyeceğini kanıtlamaz |

> [!NOT]
> Görevler `veri/speculative.json` dosyasını okur; dosya sentetiktir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; değişiklikler taşınmaz, **kalıcılık yoktur**. Ekranda ayrı dosya görüntüleyici yoktur; içeriği görmek için `print` kullan. Gizli testler ayrıdır. Final yeni model indirmez ve GPU varsa onu kullanır.

ai-temel-07 KV-cache ile otoregresif üretimin neden bellek bant genişliği (memory-bound) darboğazına takıldığını gösterir: her yeni token için büyük modelin bütün ağırlıkları GPU belleğinden okunur. **Peki büyük modeli $\gamma$ kez ardışık çalıştırmak yerine, çok hızlı küçük bir taslak (draft) modele $\gamma$ token ürettirip büyük modeli yalnızca tek bir paralel doğrulama adımında çalıştırabilir miyiz?**

**Kayıpsız `speculative decoding` ve `rejection sampling`.** Leviathan vd. (2023) ve Chen vd. (2023), taslak dağılım $q(x)$ ile hedef dağılım $p(x)$ arasında değiştirilmiş bir `rejection sampling` şeması tanımlar:
1. Taslak modelden örneklenen $x \sim q(x)$ tokenı şu olasılıkla kabul edilir:
   $$\alpha(x) = \min\left(1, \frac{p(x)}{q(x)}\right)$$
2. Bir tekdüze rastgele sayı $u \in [0, 1)$ çekilir. Eğer $u < \alpha(x)$ ise token kabul edilir ve bir sonraki taslak adımına geçilir.
3. Eğer $u \ge \alpha(x)$ ise token **reddedilir**, sonraki taslak adımları iptal edilir ve o konum için doğrudan artık dağılımdan (residual distribution) yeni bir kurtarma tokenı seçilir:
   $$p'(x) = \frac{\max(0, p(x) - q(x))}{\sum_{y} \max(0, p(y) - q(y))}$$

**Matematiksel değişmezlik (invariance).** Bir $x$ tokenının kabul edilme olasılığı $q(x)\min(1, p(x)/q(x)) = \min(p(x), q(x))$ olur. Toplam red olasılığı $\beta = 1 - \sum_y \min(p(y), q(y)) = \sum_y \max(0, p(y) - q(y))$ değerine (yani toplam değişim uzaklığı $D_{\text{TV}}(p, q)$'ya) eşittir. Dolayısıyla kabul veya kurtarma sonucunda $x$ tokenının çıkma olasılığı:
$$\min(p(x), q(x)) + \beta \cdot \frac{\max(0, p(x) - q(x))}{\beta} = p(x)$$
Yani çıktı dağılımı yaklaşıklama değildir; **tam olarak büyük hedef modelin $p(x)$ dağılımıdır!**

**Saldırgan ne dener?** Hizmet reddi (DoS / latency sponge) saldırısında saldırgan, taslak modelin hedef modelle sürekli çelişeceği (yüksek $D_{\text{TV}}(p, q)$ üreten) nadir veya karmaşık önekler gönderir. Her adımda ilk taslak token reddedilirse (`kabul_sayisi = 0`), taslak modelin maliyeti boşa harcanır ve sistem normal otoregresif üretimden bile yavaş çalışır.

**Savunma neden kırılır?** İlk reddedilen adımdan sonraki taslak tokenları iptal etmeden doğrulamaya devam etmek zincirleme koşullu olasılığı bozar; ayrıca artık dağılım yerine doğrudan $p(x)$'ten yeniden örneklemek yüksek olasılıklı taslak tokenların iki kez seçilme şansını artırarak hedef dağılımı çarpıtır.

**Görev 1'de sık tuzaklar:** $p(x) > q(x)$ olduğunda oranı `1.0` ile üstten sınırlamayı unutmak veya $q(x) = 0$ durumunu denetlememek.

Kaynaklar: [Leviathan vd. 2023 - Fast Inference from Transformers via Speculative Decoding](https://arxiv.org/abs/2211.17192), [Chen vd. 2023 - Accelerating Large Language Model Decoding with Speculative Sampling](https://arxiv.org/abs/2302.01318). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Köprü: ai-temel-03 tek bir dağılımdan örneklemeyi, ai-temel-07 KV-cache maliyetini inceler; bu ders iki modeli `rejection sampling` ile kayıpsız birleştirir.
:::

::: tahmin Kabul artı artık dağılım neden tam olarak hedef dağılımı verir?
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
p = [0.10, 0.60, 0.30]
q = [0.40, 0.20, 0.40]
kabul_kutlesi = [min(pi, qi) for pi, qi in zip(p, q)]
fark = [max(0.0, pi - qi) for pi, qi in zip(p, q)]
red_olasiligi = 1.0 - sum(kabul_kutlesi)
artik = [d / sum(fark) for d in fark]
birlesik = [round(k + red_olasiligi * a, 4) for k, a in zip(kabul_kutlesi, artik)]
print("Kabul kütlesi:", kabul_kutlesi)
print("Artık dağılım:", [round(a, 4) for a in artik])
print("Birleşik olasılık:", birlesik)
```
???
```cikti
Kabul kütlesi: [0.1, 0.2, 0.3]
Artık dağılım: [0.0, 1.0, 0.0]
Birleşik olasılık: [0.1, 0.6, 0.3]
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: `Birleşik olasılık` satırı neden `p` listesiyle birebir aynı çıktı? Reddedildiğinde `artik` yerine doğrudan `p` kullanılsaydı 0. ve 2. indislerin olasılığı ne olurdu? Sonra üç kusurlu başlangıç kodunu çalıştır ve her birinin neyi kaçırdığını önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · Leviathan kabul olasılığı
`kabul_olasiligi(p_hedef, q_taslak)`: `p_hedef` bool olmayan sonlu sayı ve `0 <= p_hedef <= 1`; `q_taslak` bool olmayan sonlu sayı ve `0 < q_taslak <= 1` (taslak olasılığı sıfır olamaz). $\min(1.0, \text{p\_hedef} / \text{q\_taslak})$ değerini `float` olarak döndür. Geçersiz girdide `ValueError`.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-27")
```
```starter
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def kabul_olasiligi(p_hedef, q_taslak):
    return p_hedef / q_taslak

from ai_temel_veri import json_yukle
v = json_yukle("veri/speculative.json")
for p, q in zip(v["ornek_p"], v["ornek_q"]):
    print("p=%.2f q=%.2f -> kabul=" % (p, q), round(kabul_olasiligi(p, q), 4))
```
```test
def sinama1(f):
    import math, random
    try:
        if f(0.2, 0.4) != 0.5 or f(0.8, 0.4) != 1.0 or f(0.0, 0.5) != 0.0 or f(1.0, 1.0) != 1.0:
            return False
        rng = random.Random(27)
        for _ in range(25):
            p = rng.uniform(0.0, 1.0)
            q = rng.uniform(0.01, 1.0)
            if abs(f(p, q) - min(1.0, p / q)) > 1e-12:
                return False
        for bad in (
            (0.5, 0.0), (-0.1, 0.5), (1.1, 0.5), (0.5, -0.1), (0.5, 1.2),
            (True, 0.5), (0.5, False), (float("nan"), 0.5), (0.5, float("inf")),
            ("0.5", 0.5), (None, 0.5), (0.5, True), (0.5, "0.5"), (0.5, None), (0.5, float("nan"))
        ):
            try:
                f(*bad)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sinama1(kabul_olasiligi), "1.0 üst sınırı, oran hesabı ve sıfır/geçersiz taslak olasılığı")
for ad, mut in [
    ("üst sınır yok", lambda p, q: float(p / q)),
    ("ters oran", lambda p, q: min(1.0, q / max(p, 1e-9))),
    ("sabit 1.0", lambda p, q: 1.0)
]:
    ok(not sinama1(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(kabul_olasiligi, _il.import_module('ai_gercek_ai_temel_27').referans_kabul_olasiligi, (0.1, 0.4), tohum=2511)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def kabul_olasiligi(p_hedef, q_taslak):
    if isinstance(p_hedef, bool) or not isinstance(p_hedef, (int, float)) or not math.isfinite(p_hedef) or not 0.0 <= p_hedef <= 1.0:
        raise ValueError("p_hedef")
    if isinstance(q_taslak, bool) or not isinstance(q_taslak, (int, float)) or not math.isfinite(q_taslak) or not 0.0 < q_taslak <= 1.0:
        raise ValueError("q_taslak")
    return float(min(1.0, p_hedef / q_taslak))

if __name__ == "__main__":
    from ai_temel_veri import json_yukle
    v = json_yukle("veri/speculative.json")
    for p, q in zip(v["ornek_p"], v["ornek_q"]):
        print("p=%.2f q=%.2f -> kabul=" % (p, q), round(kabul_olasiligi(p, q), 4))
```
```hint
`p_hedef` için `0.0 <= p_hedef <= 1.0`, `q_taslak` için `0.0 < q_taslak <= 1.0` kontrolü yap ve `min(1.0, p_hedef / q_taslak)` döndür.
```
:::

::: anlat Red sonrası artık dağılım (Residual Distribution)
Taslak token reddedildiğinde, hedef modelin olasılığının taslak modelden **fazla** olduğu tokenları telafi etmek gerekir. Her indis için pozitif fark $\max(0.0, p_i - q_i)$ alınır ve bu farkların toplamına bölünerek normalize edilir:
$$p'_i = \frac{\max(0, p_i - q_i)}{\sum_j \max(0, p_j - q_j)}$$
Eğer iki dağılım aynıysa ($\sum_j \max(0, p_j - q_j) \le 10^{-12}$), artık dağılım tanımsızdır (çünkü kabul olasılığı zaten %100'dür ve red gerçekleşemez); bu durumda `ValueError` fırlatılmalıdır.

**Görev 2'de sık tuzaklar:** Negatif farkları sıfırlamadan (`max(0.0, ...)`) bırakmak veya girdi dağılımlarının toplamının `1.0` (`abs(sum(d) - 1.0) <= 1e-6`) olduğunu doğrulamamak.
:::

::: gorev 2 · Normalize artık dağılım
`artik_dagilim(p_dagilim, q_dagilim)`: `p_dagilim` ve `q_dagilim` aynı uzunlukta (`>= 2`) `list`; her eleman bool olmayan sonlu sayı (`0 <= v <= 1`) ve her iki listenin toplamı `1.0` (`abs(sum(d) - 1.0) <= 1e-6`). Pozitif farkların toplamı `> 1e-12` olmalıdır. $\max(0.0, p_i - q_i)$ değerlerini toplamlarına bölerek yeni bir `list` döndür. Geçersiz girdide veya sıfır fark toplamında `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-27")
```
```starter
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def artik_dagilim(p_dagilim, q_dagilim):
    return [p - q for p, q in zip(p_dagilim, q_dagilim)]

from ai_temel_veri import json_yukle
v = json_yukle("veri/speculative.json")
print("Artık dağılım:", artik_dagilim(v["ornek_p"], v["ornek_q"]))
```
```test
def sinama2(f):
    import math, random
    def _r(p, q):
        d = [max(0.0, a - b) for a, b in zip(p, q)]
        t = sum(d)
        return [v / t for v in d]
    def _y(a, b):
        return len(a) == len(b) and all(abs(x - y) < 1e-12 for x, y in zip(a, b))
    try:
        p = [0.1, 0.6, 0.2, 0.1]; q = [0.4, 0.25, 0.25, 0.1]; old = (list(p), list(q))
        c = f(p, q)
        if not _y(c, [0.0, 1.0, 0.0, 0.0]) or (p, q) != old: return False
        p2 = [0.5, 0.4, 0.1]; q2 = [0.2, 0.2, 0.6]
        if not _y(f(p2, q2), [0.6, 0.4, 0.0]): return False
        if not _y(f([1.0, 0.0], [0.5, 0.5]), [1.0, 0.0]) or not _y(f([0.5, 0.5], [0.0, 1.0]), [1.0, 0.0]): return False
        for k in ((["a", 0.5], [0.5, 0.5]), ([0.5, 0.5], [0.5, "a"]), ([float("inf"), 0.5], [0.5, 0.5]), ([0.5, 0.5], [True, 0.0]), ((0.6, 0.4), [0.5, 0.5]), ([0.6, 0.4], (0.5, 0.5))):
            try:
                f(*k)
                return False
            except ValueError:
                pass
        rng = random.Random(2727)
        for _ in range(25):
            n = rng.randint(2, 7)
            rp = [rng.uniform(0.1, 2.0) for _ in range(n)]; sp = sum(rp); vp = [x / sp for x in rp]
            rq = [rng.uniform(0.1, 2.0) for _ in range(n)]; sq = sum(rq); vq = [x / sq for x in rq]
            if sum(max(0.0, a - b) for a, b in zip(vp, vq)) > 1e-6:
                if not _y(f(list(vp), list(vq)), _r(vp, vq)): return False
        for bad in (
            (None, [0.5, 0.5]), ([0.5, 0.5], None), ([1.0], [1.0]), ([1.0], [0.9999995]),
            ([0.5, 0.5], [0.5, 0.3, 0.2]), ([0.5, 0.5], [0.5, 0.5]),
            ([0.6, 0.6], [0.5, 0.5]), ([0.5, 0.5], [0.2, 0.2]),
            ([-0.1, 1.1], [0.5, 0.5]), ([-0.5, 0.75, 0.75], [0.5, 0.25, 0.25]), ([True, 0.0], [0.5, 0.5]),
            ([float("nan"), 0.5], [0.5, 0.5])
        ):
            try:
                f(*bad)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sinama2(artik_dagilim), "pozitif fark kırpma, normalizasyon, özdeş dağılım reddi ve geçersiz girdi")
for ad, mut in [
    ("normalize edilmemiş", lambda p, q: [max(0.0, a - b) for a, b in zip(p, q)]),
    ("doğrudan p döndür", lambda p, q: list(p)),
    ("ters fark q-p", lambda p, q: artik_dagilim(q, p))
]:
    ok(not sinama2(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(artik_dagilim, _il.import_module('ai_gercek_ai_temel_27').referans_artik_dagilim, ([0.1, 0.6, 0.2, 0.1], [0.4, 0.25, 0.25, 0.1]), tohum=2293)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def artik_dagilim(p_dagilim, q_dagilim):
    if not isinstance(p_dagilim, list) or not isinstance(q_dagilim, list) or len(p_dagilim) < 2 or len(p_dagilim) != len(q_dagilim):
        raise ValueError("boyut")
    for d in (p_dagilim, q_dagilim):
        for x in d:
            if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or not 0.0 <= x <= 1.0:
                raise ValueError("deger")
        if abs(sum(d) - 1.0) > 1e-6:
            raise ValueError("toplam")
    fark = [max(0.0, p - q) for p, q in zip(p_dagilim, q_dagilim)]
    toplam = sum(fark)
    if toplam <= 1e-12:
        raise ValueError("sifir_artik")
    return [v / toplam for v in fark]

if __name__ == "__main__":
    from ai_temel_veri import json_yukle
    v = json_yukle("veri/speculative.json")
    print("Artık dağılım:", artik_dagilim(v["ornek_p"], v["ornek_q"]))
```
```hint
Her iki dağılımın toplamının `1.0` olduğunu kontrol et, `[max(0.0, p - q) ...]` farklarını topla ve toplam `<= 1e-12` ise `ValueError` fırlat.
```
:::

::: anlat Spekülatif doğrulama turu ve ilk redde durma kuralı
Bir spekülatif doğrulama turunda $\gamma$ adet taslak adımı (`t = 0, ..., gamma - 1`) sırayla incelenir:
- Adım $t$'de taslak token `tok = tokenlar[t]` için kabul olasılığı $\alpha_t = \min(1.0, p_t[\text{tok}] / q_t[\text{tok}])$ hesaplanır.
- Eğer `u_Ornekler[t] < alpha_t` ise token **kabul edilir** (`kabul_sayisi += 1`).
- Eğer `u_Ornekler[t] >= alpha_t` ise token **reddedilir**:
  - `red_adimi = t` olarak kaydedilir.
  - $t$ adımındaki `artik_dagilim(p_t, q_t)` üzerinden en yüksek olasılıklı kurtarma tokenı `kurtarma_token = max(range(V), key=lambda i: artik[i])` seçilir.
  - **Döngü derhâl sonlandırılır (`break`)**; sonraki taslak adımlarına bakılmaz!
- Eğer hiçbir adımda red olmazsa `red_adimi = None`, `kurtarma_token = None` olur ve hedef modelin son konumdan ürettiği bonus tokenla birlikte `uretilen_token = kabul_sayisi + 1` (yani $\gamma + 1$) olur. Her iki durumda da tek hedef model çağrısında üretilen geçerli token sayısı `kabul_sayisi + 1` değeridir.

**Görev 3'te sık tuzaklar:** Red gerçekleştiğinde `break` yapmayıp sonraki taslak tokenları da kabul etmeye devam etmek!
:::

::: gorev 3 · Spekülatif doğrulama turu özeti
`spekulatif_tur_ozeti(p_adimlar, q_adimlar, tokenlar, u_Ornekler)`: `p_adimlar` ve `q_adimlar` aynı uzunlukta ($\gamma \ge 1$) geçerli olasılık dağılımı listeleri (tüm adımlarda sözlük boyutu $V \ge 2$ aynı); `tokenlar` uzunluğu $\gamma$ olan geçerli indis listesi (`0 <= tok < V` ve `q_adimlar[t][tok] > 0`); `u_Ornekler` uzunluğu $\gamma$ olan `0 <= u < 1` sayı listesi. Yukarıdaki kuralla `{"kabul_sayisi": int, "red_adimi": int veya None, "kurtarma_token": int veya None, "uretilen_token": int, "hizlanma_carpani": float}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-27")
```
```starter
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def spekulatif_tur_ozeti(p_adimlar, q_adimlar, tokenlar, u_Ornekler):
    kabul = 0
    for p_t, q_t, tok, u in zip(p_adimlar, q_adimlar, tokenlar, u_Ornekler):
        if u < min(1.0, p_t[tok] / q_t[tok]):
            kabul += 1
    return {
        "kabul_sayisi": kabul,
        "red_adimi": None,
        "kurtarma_token": None,
        "uretilen_token": kabul,
        "hizlanma_carpani": float(kabul),
    }

from ai_temel_veri import json_yukle
v = json_yukle("veri/speculative.json")
for tur in v["turlar"]:
    print(tur["ad"], spekulatif_tur_ozeti(tur["p_adimlar"], tur["q_adimlar"], tur["tokenlar"], tur["u_Ornekler"]))
```
```test
def sinama3(f):
    import copy, random
    def _r(pa, qa, tk, uo):
        ks = 0; ra = None; kt = None; V = len(pa[0])
        for t in range(len(pa)):
            alfa = min(1.0, pa[t][tk[t]] / qa[t][tk[t]])
            if uo[t] < alfa:
                ks += 1
            else:
                ra = t
                d = [max(0.0, a - b) for a, b in zip(pa[t], qa[t])]
                s = sum(d); ar = [v / s for v in d]
                kt = max(range(V), key=lambda i: ar[i])
                break
        ur = ks + 1
        return {"kabul_sayisi": ks, "red_adimi": ra, "kurtarma_token": kt, "uretilen_token": ur, "hizlanma_carpani": float(ur)}
    try:
        pa = [[0.7, 0.2, 0.1], [0.1, 0.75, 0.15], [0.2, 0.3, 0.5]]
        qa = [[0.65, 0.25, 0.1], [0.6, 0.25, 0.15], [0.25, 0.25, 0.5]]
        tk = [0, 0, 2]; uo = [0.5, 0.4, 0.1]
        old = copy.deepcopy((pa, qa, tk, uo))
        c = f(pa, qa, tk, uo)
        if c != {"kabul_sayisi": 1, "red_adimi": 1, "kurtarma_token": 1, "uretilen_token": 2, "hizlanma_carpani": 2.0} or (pa, qa, tk, uo) != old:
            return False
        c2 = f([[0.8, 0.2], [0.3, 0.7]], [[0.7, 0.3], [0.4, 0.6]], [0, 1], [0.9, 0.9])
        if c2 != {"kabul_sayisi": 2, "red_adimi": None, "kurtarma_token": None, "uretilen_token": 3, "hizlanma_carpani": 3.0}:
            return False
        rng = random.Random(2703)
        for _ in range(20):
            g = rng.randint(1, 5); V = rng.randint(2, 5)
            p_l, q_l, t_l, u_l = [], [], [], []
            for _ in range(g):
                rp = [rng.uniform(0.1, 1.0) for _ in range(V)]; sp = sum(rp); vp = [x / sp for x in rp]
                rq = [rng.uniform(0.1, 1.0) for _ in range(V)]; sq = sum(rq); vq = [x / sq for x in rq]
                p_l.append(vp); q_l.append(vq); t_l.append(rng.randrange(V)); u_l.append(rng.uniform(0.0, 0.99))
            if f(copy.deepcopy(p_l), copy.deepcopy(q_l), list(t_l), list(u_l)) != _r(p_l, q_l, t_l, u_l):
                return False
        for args in (([[0.25, 0.75]], [[0.5, 0.5]], [0], [0.5]), ([[1.0, 0.0]], [[0.5, 0.5]], [0], [0.0]), ([[0.0, 1.0]], [[0.5, 0.5]], [0], [0.0])):
            if f(*copy.deepcopy(args)) != _r(*args): return False
        if f([[0.25, 0.75]], [[0.5, 0.5]], [0], [0.5])["red_adimi"] != 0: return False
        B = ([[0.6, 0.4], [0.5, 0.5]], [[0.5, 0.5], [0.4, 0.6]], [0, 1], [0.1, 0.1])
        def deg(i, v):
            x = list(copy.deepcopy(B)); x[i] = v; return tuple(x)
        kotu = [deg(i, tuple(B[i])) for i in range(4)] + [deg(i, None) for i in range(4)]
        kotu += [deg(1, B[1][:1]), deg(2, [0]), deg(3, [0.1]), deg(3, [0.1, 0.1, 0.1])]
        kotu += [deg(0, [(0.6, 0.4), [0.5, 0.5]]), deg(1, [(0.5, 0.5), [0.4, 0.6]]), deg(0, [[1.0], [0.5, 0.5]]), deg(1, [[0.5, 0.5], [0.4, 0.3, 0.3]])]
        for kt in (True, "a", float("nan"), float("inf"), -0.1, 1.1):
            kotu += [deg(0, [[kt, 0.4], [0.5, 0.5]]), deg(1, [[0.5, 0.5], [0.4, kt]])]
        kotu += [deg(3, [u, 0.1]) for u in (True, "a", float("nan"), 1.0, -0.1)] + [deg(2, [0.0, 1]), deg(2, ["0", 1]), deg(2, [-1, 1])]
        kotu += [([[0.6, 0.4]], [[0.5, 0.5]], [0], [1.0]), deg(0, [[1.1, -0.1], [0.5, 0.5]]), deg(1, [[0.5, 0.5], [1.1, -0.1]])]
        for bad in (
            *kotu,
            ([], [], [], []),
            ([[0.5, 0.5]], [[0.5, 0.5], [0.5, 0.5]], [0], [0.5]),
            ([[0.5, 0.5], [0.3, 0.3, 0.4]], [[0.5, 0.5], [0.3, 0.3, 0.4]], [0, 0], [0.1, 0.1]),
            ([[0.5, 0.5]], [[0.5, 0.5]], [2], [0.1]),
            ([[0.5, 0.5]], [[0.0, 1.0]], [0], [0.1]),
            ([[0.5, 0.5]], [[0.5, 0.5]], [0], [1.0]),
            ([[0.5, 0.5]], [[0.5, 0.5]], [0], [-0.1]),
            ([[0.5, 0.5]], [[0.5, 0.5]], [True], [0.1]), ([[1.0]], [[1.0]], [0], [0.1]), ([[False, 1.0]], [[0.5, 0.5]], [1], [0.1]), ([[0.4999996, 0.4999996]], [[0.5000004, 0.5000004]], [0], [0.999999]), ([[-0.5, 0.75, 0.75]], [[0.5, 0.25, 0.25]], [1], [0.1])
        ):
            try:
                f(*bad)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
_tur_esik = spekulatif_tur_ozeti(
    [[0.5, 0.25, 0.25], [0.25, 0.375, 0.375], [0.5, 0.25, 0.25]],
    [[0.5, 0.25, 0.25], [0.5, 0.25, 0.25], [0.5, 0.25, 0.25]],
    [0, 0, 0], [0.0, 0.5, 0.0],
)
eq(_tur_esik, {"kabul_sayisi": 1, "red_adimi": 1, "kurtarma_token": 1,
              "uretilen_token": 2, "hizlanma_carpani": 2.0},
   "İkinci adımda u kabul eşiğine eşit. Artık kütle eşitse küçük indeks seçilir.")
ok(sinama3(spekulatif_tur_ozeti), "ilk redde durma, kurtarma tokenı, bonus token ve geçersiz girdi")
for ad, mut in [
    ("redde durmaz", lambda pa, qa, tk, uo: dict(spekulatif_tur_ozeti(pa, qa, tk, uo), kabul_sayisi=sum(1 for p, q, t, u in zip(pa, qa, tk, uo) if u < min(1.0, p[t] / q[t])))),
    ("bonus token yok", lambda pa, qa, tk, uo: dict(spekulatif_tur_ozeti(pa, qa, tk, uo), uretilen_token=spekulatif_tur_ozeti(pa, qa, tk, uo)["kabul_sayisi"])),
    ("kurtarma hep 0", lambda pa, qa, tk, uo: dict(spekulatif_tur_ozeti(pa, qa, tk, uo), kurtarma_token=0))
]:
    ok(not sinama3(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(spekulatif_tur_ozeti, _il.import_module('ai_gercek_ai_temel_27').referans_spekulatif_ozet, ([[0.7, 0.2, 0.1], [0.1, 0.75, 0.15], [0.2, 0.3, 0.5]], [[0.65, 0.25, 0.1], [0.6, 0.25, 0.15], [0.25, 0.25, 0.5]], [0, 0, 2], [0.5, 0.4, 0.1]), tohum=3104)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def spekulatif_tur_ozeti(p_adimlar, q_adimlar, tokenlar, u_Ornekler):
    if not isinstance(p_adimlar, list) or not isinstance(q_adimlar, list) or not isinstance(tokenlar, list) or not isinstance(u_Ornekler, list):
        raise ValueError("liste")
    gamma = len(p_adimlar)
    if gamma < 1 or len(q_adimlar) != gamma or len(tokenlar) != gamma or len(u_Ornekler) != gamma:
        raise ValueError("gamma")
    sozluk = None
    for t in range(gamma):
        p_t, q_t = p_adimlar[t], q_adimlar[t]
        if not isinstance(p_t, list) or not isinstance(q_t, list) or len(p_t) < 2 or len(p_t) != len(q_t):
            raise ValueError("adim_boyut")
        if sozluk is not None and len(p_t) != sozluk:
            raise ValueError("sozluk_farkli")
        sozluk = len(p_t)
        for d in (p_t, q_t):
            for x in d:
                if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or not 0.0 <= x <= 1.0:
                    raise ValueError("olasilik")
            if abs(sum(d) - 1.0) > 1e-6:
                raise ValueError("toplam")
        tok = tokenlar[t]
        u = u_Ornekler[t]
        if isinstance(tok, bool) or not isinstance(tok, int) or not 0 <= tok < sozluk or q_t[tok] <= 0.0:
            raise ValueError("token")
        if isinstance(u, bool) or not isinstance(u, (int, float)) or not math.isfinite(u) or not 0.0 <= u < 1.0:
            raise ValueError("u_ornek")
    kabul_sayisi = 0
    red_adimi = None
    kurtarma_token = None
    for t in range(gamma):
        p_t, q_t = p_adimlar[t], q_adimlar[t]
        tok = tokenlar[t]
        alfa = min(1.0, p_t[tok] / q_t[tok])
        if u_Ornekler[t] < alfa:
            kabul_sayisi += 1
        else:
            red_adimi = t
            fark = [max(0.0, a - b) for a, b in zip(p_t, q_t)]
            top = sum(fark)
            if top <= 1e-12:
                raise ValueError("sifir_artik")
            artik = [v / top for v in fark]
            kurtarma_token = max(range(sozluk), key=lambda i: artik[i])
            break
    uretilen = kabul_sayisi + 1
    return {
        "kabul_sayisi": kabul_sayisi,
        "red_adimi": red_adimi,
        "kurtarma_token": kurtarma_token,
        "uretilen_token": uretilen,
        "hizlanma_carpani": float(uretilen),
    }

if __name__ == "__main__":
    from ai_temel_veri import json_yukle
    v = json_yukle("veri/speculative.json")
    for tur in v["turlar"]:
        print(tur["ad"], spekulatif_tur_ozeti(tur["p_adimlar"], tur["q_adimlar"], tur["tokenlar"], tur["u_Ornekler"]))
```
```hint
İlk `u_Ornekler[t] >= alfa` durumunda `red_adimi = t` ve `kurtarma_token` değerini hesaplayıp `break` ile döngüden çık.
```
:::

::: anlat Hata vitrini · çalışmış yanlış rapor
Yazar, kusurlu başlangıç kodlarını görünür sentetik veriyle gerçekten çalıştırdı ve sonucu `outputs/yeni-ai-temel-27/gorunur-run-1.json` dosyasına kaydetti. `ikinci_adimda_red` turunda 1. adımda (indis `1`) taslak token reddedildiği hâlde kusurlu kod `break` yapmadığı için 2. adımdaki taslak tokenı da kabul edip `kabul_sayisi=2`, `red_adimi=None` döndürür. Doğru kod ise 1. adımda durup `kabul_sayisi=1`, `red_adimi=1`, `kurtarma_token=1` döndürür.

Bu kaydedilmiş bir hesaplama çıktısıdır, model yanıtı değildir ve rapor sentetiktir. 1. adımdaki token reddedilmişken 2. adımdaki taslak tokenı kabul etmek neden geçersiz bir önek (prefix) üzerine üretim yapmak demektir? Kendi cümlenle açıkla. Gerçek finaldeki ölçüm ayrıca üretilir; bu sayılar onun yerine konmaz.
:::

::: anlat Gerçek deney: SmolLM2'de kendi kendine spekülatif çözme
Final, yerel önbellekteki gerçek **SmolLM2-135M** modelini (indirme yok) hem hedef hem taslak olarak kullanır. **Hedef** tam modeldir (30 katman). **Taslak** aynı modelin 12. katmanından erken çıkıştır: o katmanın gizli durumu son norm ve `lm_head`'den geçirilir (LayerSkip / Draft&Verify yaklaşımı). Her turda taslak $\gamma = 4$ token örnekler; hedef dört konumun dağılımını tek ileri geçişte hesaplar. Bütün dağılımlar gerçek 49.152 tokenlık sözlük üzerindedir ve **senin `kabul_olasiligi`, `artik_dagilim` ve `spekulatif_tur_ozeti` işlevlerinle** doğrulanır.

Deney üç şey ölçer:
1. **Kayıpsızlık:** ilk istemin ilk adımında "kabul + red sonrası artık dağılım" bileşiminin hedef dağılımı tam olarak (`1e-9`) yeniden ürettiği.
2. **Ayarsız erken çıkış:** ara katmanlar çıkış için eğitilmemiştir; ayarsız taslak hedefle çok az örtüşür ve hedef çağrısı başına token neredeyse 1'de kalır.
3. **Ayarlı taslak:** modelin kendi ürettiği metin üzerinde her çıkış katmanı (6, 12, 20) için doğrusal bir adaptör, son katmanın dağılımına KL ile damıtılır (Medusa başları ve tuned lens'in yaptığına benzer). Ayarlı taslak, hedef dağılımını değiştirmeden kabulü artırır.

Kabul: üç işlevin gerçek dağılımlarda bağımsız referansla aynı sonucu vermesi, artık dağılımların toplamının 1 olması, kayıpsızlık özdeşliği, hedef çağrısı başına ortalama tokenın 1'in üstünde olması ve derinliklerin ortalamasında ayarlı taslağın ayarsızdan daha çok token kazandırması.

**Kanıt dosyasını oku:** `derinlik_taramasi_ayarsiz`, `derinlik_taramasi` ve `kayipsizlik_max_sapma` alanlarına bak. Soru 1: Taslak berbat olsa bile (ayarsız erken çıkış) çıktı dağılımı neden değişmedi? Soru 2: Ayarsız 12. katman taslağı neden 6. katmandan bile iyi değil (çıkış için eğitilmemiş ara katmanlar)? Soru 3: Bu deney hızlanmayı "hedef çağrısı başına token" olarak ölçüyor; gerçek duvar saati hızlanması için taslağın maliyeti hakkında neyi bilmen gerekir? Cevabını tezgâhta yorum olarak yaz; otomatik test bu serbest açıklamayı puanlamaz.
:::

::: gorev Gerçek deney · SmolLM2-135M erken çıkış taslağı ve tam modelde spekülatif doğrulama
Önceki üç görevin `kabul_olasiligi`, `artik_dagilim` ve `spekulatif_tur_ozeti` işlevlerini birleştir. Çalıştır gerçek tabloyu gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 180
```
```starter
import ai_lab
def kabul_olasiligi(p_hedef, q_taslak):
    return p_hedef / q_taslak
def artik_dagilim(p_dagilim, q_dagilim):
    return [p - q for p, q in zip(p_dagilim, q_dagilim)]
def spekulatif_tur_ozeti(p_adimlar, q_adimlar, tokenlar, u_Ornekler):
    return {"kabul_sayisi": 0, "red_adimi": 0, "kurtarma_token": 0, "uretilen_token": 1, "hizlanma_carpani": 1.0}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_27 as D
    D.goster(kabul_olasiligi, artik_dagilim, spekulatif_tur_ozeti)
```
```test
import ai_lab, math
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('referans_kabul_olasiligi', 'referans_artik_dagilim', 'referans_spekulatif_ozet', 'kanit_yaz', '_yakin'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
kabul_olasiligi = need("kabul_olasiligi")
artik_dagilim = need("artik_dagilim")
spekulatif_tur_ozeti = need("spekulatif_tur_ozeti")
def sinama1(f):
    import random
    try:
        if f(0.2, 0.4) != 0.5 or f(0.8, 0.4) != 1.0 or f(0.0, 0.5) != 0.0 or f(1.0, 1.0) != 1.0: return False
        rng = random.Random(27)
        for _ in range(25):
            p = rng.uniform(0.0, 1.0); q = rng.uniform(0.01, 1.0)
            if abs(f(p, q) - min(1.0, p / q)) > 1e-12: return False
        for bad in ((0.5, 0.0), (-0.1, 0.5), (1.1, 0.5), (0.5, -0.1), (0.5, 1.2), (True, 0.5), (0.5, False), (float("nan"), 0.5), (0.5, float("inf")), ("0.5", 0.5), (None, 0.5)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama1(kabul_olasiligi), "1.0 üst sınırı, oran hesabı ve sıfır/geçersiz taslak olasılığı")
for ad, mut in [("üst sınır yok", lambda p, q: float(p / q)), ("ters oran", lambda p, q: min(1.0, q / max(p, 1e-9))), ("sabit 1.0", lambda p, q: 1.0)]:
    kontrol(not sinama1(mut), "mutant reddedildi: " + ad)
def sinama2(f):
    import random
    def _r(p, q):
        d = [max(0.0, a - b) for a, b in zip(p, q)]; t = sum(d)
        return [v / t for v in d]
    def _y(a, b): return len(a) == len(b) and all(abs(x - y) < 1e-12 for x, y in zip(a, b))
    try:
        p = [0.1, 0.6, 0.2, 0.1]; q = [0.4, 0.25, 0.25, 0.1]; old = (list(p), list(q))
        if not _y(f(p, q), [0.0, 1.0, 0.0, 0.0]) or (p, q) != old: return False
        if not _y(f([1.0, 0.0], [0.5, 0.5]), [1.0, 0.0]) or not _y(f([0.5, 0.5], [0.0, 1.0]), [1.0, 0.0]): return False
        rng = random.Random(2727)
        for _ in range(25):
            n = rng.randint(2, 7)
            rp = [rng.uniform(0.1, 2.0) for _ in range(n)]; sp = sum(rp); vp = [x / sp for x in rp]
            rq = [rng.uniform(0.1, 2.0) for _ in range(n)]; sq = sum(rq); vq = [x / sq for x in rq]
            if sum(max(0.0, a - b) for a, b in zip(vp, vq)) > 1e-6:
                if not _y(f(list(vp), list(vq)), _r(vp, vq)): return False
        for bad in ((None, [0.5, 0.5]), ([0.5, 0.5], None), ([1.0], [1.0]), ([1.0], [0.9999995]), ([0.5, 0.5], [0.5, 0.3, 0.2]), ([0.5, 0.5], [0.5, 0.5]), ([0.6, 0.6], [0.5, 0.5]), ([0.5, 0.5], [0.2, 0.2]), ([-0.1, 1.1], [0.5, 0.5]), ([-0.5, 0.75, 0.75], [0.5, 0.25, 0.25]), ([True, 0.0], [0.5, 0.5]), ([float("nan"), 0.5], [0.5, 0.5])):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama2(artik_dagilim), "pozitif fark kırpma, normalizasyon, özdeş dağılım reddi ve geçersiz girdi")
for ad, mut in [("normalize edilmemiş", lambda p, q: [max(0.0, a - b) for a, b in zip(p, q)]), ("doğrudan p döndür", lambda p, q: list(p)), ("ters fark q-p", lambda p, q: artik_dagilim(q, p))]:
    kontrol(not sinama2(mut), "mutant reddedildi: " + ad)
def sinama3(f):
    import copy, random
    def _r(pa, qa, tk, uo):
        ks = 0; ra = None; kt = None; V = len(pa[0])
        for t in range(len(pa)):
            alfa = min(1.0, pa[t][tk[t]] / qa[t][tk[t]])
            if uo[t] < alfa: ks += 1
            else:
                ra = t; d = [max(0.0, a - b) for a, b in zip(pa[t], qa[t])]; s = sum(d); ar = [v / s for v in d]
                kt = max(range(V), key=lambda i: ar[i]); break
        ur = ks + 1
        return {"kabul_sayisi": ks, "red_adimi": ra, "kurtarma_token": kt, "uretilen_token": ur, "hizlanma_carpani": float(ur)}
    try:
        pa = [[0.7, 0.2, 0.1], [0.1, 0.75, 0.15], [0.2, 0.3, 0.5]]
        qa = [[0.65, 0.25, 0.1], [0.6, 0.25, 0.15], [0.25, 0.25, 0.5]]
        tk = [0, 0, 2]; uo = [0.5, 0.4, 0.1]; old = copy.deepcopy((pa, qa, tk, uo))
        if f(pa, qa, tk, uo) != {"kabul_sayisi": 1, "red_adimi": 1, "kurtarma_token": 1, "uretilen_token": 2, "hizlanma_carpani": 2.0} or (pa, qa, tk, uo) != old: return False
        if f([[0.8, 0.2], [0.3, 0.7]], [[0.7, 0.3], [0.4, 0.6]], [0, 1], [0.9, 0.9]) != {"kabul_sayisi": 2, "red_adimi": None, "kurtarma_token": None, "uretilen_token": 3, "hizlanma_carpani": 3.0} or f([[0.25, 0.75]], [[0.5, 0.5]], [0], [0.5])["kabul_sayisi"] != 0 or f([[1.0, 0.0]], [[1.0, 0.0]], [0], [0.1])["kabul_sayisi"] != 1: return False
        rng = random.Random(2703)
        for _ in range(20):
            g = rng.randint(1, 5); V = rng.randint(2, 5); p_l, q_l, t_l, u_l = [], [], [], []
            for _ in range(g):
                rp = [rng.uniform(0.1, 1.0) for _ in range(V)]; sp = sum(rp); vp = [x / sp for x in rp]
                rq = [rng.uniform(0.1, 1.0) for _ in range(V)]; sq = sum(rq); vq = [x / sq for x in rq]
                p_l.append(vp); q_l.append(vq); t_l.append(rng.randrange(V)); u_l.append(rng.uniform(0.0, 0.99))
            if f(copy.deepcopy(p_l), copy.deepcopy(q_l), list(t_l), list(u_l)) != _r(p_l, q_l, t_l, u_l): return False
        for bad in (([], [], [], []), ([[1.0]], [[1.0]], [0], [0.1]), ([[0.5, 0.5]], [[0.5, 0.3, 0.2]], [0], [0.1]), ([[True, 0.0]], [[0.5, 0.5]], [0], [0.1]), ([[False, 1.0]], [[0.5, 0.5]], [1], [0.1]), ([[-0.5, 0.75, 0.75]], [[0.5, 0.25, 0.25]], [1], [0.1]), ([[0.2, 0.8], [0.5, 0.5]], [[0.8, 0.2], [0.0, 1.0]], [0, 0], [0.9, 0.1]), ([[0.5, 0.5]], [[0.5, 0.5], [0.5, 0.5]], [0], [0.5]), ([[0.5, 0.5], [0.3, 0.3, 0.4]], [[0.5, 0.5], [0.3, 0.3, 0.4]], [0, 0], [0.1, 0.1]), ([[0.5, 0.5]], [[0.5, 0.5]], [2], [0.1]), ([[0.5, 0.5]], [[0.0, 1.0]], [0], [0.1]), ([[0.5, 0.5]], [[0.5, 0.5]], [0], [1.0]), ([[0.5, 0.5]], [[0.5, 0.5]], [0], [-0.1]), ([[0.5, 0.5]], [[0.5, 0.5]], [True], [0.1]), ([[0.4999996, 0.4999996]], [[0.5000004, 0.5000004]], [0], [0.999999]), ([[-0.5, 0.75, 0.75]], [[0.5, 0.25, 0.25]], [0], [0.1])):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama3(spekulatif_tur_ozeti), "ilk redde durma, kurtarma tokenı, bonus token ve geçersiz girdi")
for ad, mut in [("redde durmaz", lambda pa, qa, tk, uo: dict(spekulatif_tur_ozeti(pa, qa, tk, uo), kabul_sayisi=sum(1 for p, q, t, u in zip(pa, qa, tk, uo) if u < min(1.0, p[t] / q[t])))), ("bonus token yok", lambda pa, qa, tk, uo: dict(spekulatif_tur_ozeti(pa, qa, tk, uo), uretilen_token=spekulatif_tur_ozeti(pa, qa, tk, uo)["kabul_sayisi"])), ("kurtarma hep 0", lambda pa, qa, tk, uo: dict(spekulatif_tur_ozeti(pa, qa, tk, uo), kurtarma_token=0))]:
    kontrol(not sinama3(mut), "mutant reddedildi: " + ad)
# farksal tarama (final)
import importlib as _il
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_R = _il.import_module('sandbox.ai_gercek_ai_temel_27')
for _ad, _ref, _taban, _toh in (
    ('kabul_olasiligi', 'referans_kabul_olasiligi', (0.1, 0.4), 3033),
    ('artik_dagilim', 'referans_artik_dagilim', ([0.1, 0.6, 0.2, 0.1], [0.4, 0.25, 0.25, 0.1]), 2815),
    ('spekulatif_tur_ozeti', 'referans_spekulatif_ozet', ([[0.7, 0.2, 0.1], [0.1, 0.75, 0.15], [0.2, 0.3, 0.5]], [[0.65, 0.25, 0.1], [0.6, 0.25, 0.15], [0.25, 0.25, 0.5]], [0, 0, 2], [0.5, 0.4, 0.1]), 3626),
):
    _t, _g = _ff(need(_ad), getattr(_R, _ref), _taban, tohum=_toh)
    kontrol(_t, "farksal tarama (" + _ad + "): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
if not all(checks): stop()
from sandbox import ai_gercek_ai_temel_27 as D
try: r = D.deney(kabul_olasiligi, artik_dagilim, spekulatif_tur_ozeti)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r["kabul_ayni"], "gerçek SmolLM2 turlarında kabul olasılıkları bağımsız referansla aynı")
kontrol(r["artik_ayni"], "gerçek dağılımlarda (49.152 token) artık dağılımlar referansla aynı")
kontrol(r["ozet_ayni"], "gerçek turlarda spekülatif tur özeti referansla aynı")
kontrol(r["artik_toplam_bir"], "bütün artık dağılımların toplamı 1.0")
kontrol(r["dagilim_degismez"], "kabul + artık dağılım birleşimi gerçek hedef dağılım p(x) ile özdeş (1e-9)")
kontrol(r["ortalama_hizlanma"] > 1.0, "spekülatif doğrulama hedef çağrısı başına 1'den fazla token üretti")
_ay, _ar = r["derinlik_taramasi_ayarsiz"], r["derinlik_taramasi"]
kontrol(sum(_ar.values()) > sum(_ay.values()), "derinliklerin ortalamasında kendi metninde damıtılmış taslak ayarsız erken çıkıştan daha çok token kazandırdı")
ai_lab.kanit_yaz("ai-temel-27-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-temel-27", "deney": r})
```
```solution
import ai_lab
import math
def kabul_olasiligi(p_hedef, q_taslak):
    if isinstance(p_hedef, bool) or not isinstance(p_hedef, (int, float)) or not math.isfinite(p_hedef) or not 0.0 <= p_hedef <= 1.0:
        raise ValueError("p_hedef")
    if isinstance(q_taslak, bool) or not isinstance(q_taslak, (int, float)) or not math.isfinite(q_taslak) or not 0.0 < q_taslak <= 1.0:
        raise ValueError("q_taslak")
    return float(min(1.0, p_hedef / q_taslak))
def artik_dagilim(p_dagilim, q_dagilim):
    if not isinstance(p_dagilim, list) or not isinstance(q_dagilim, list) or len(p_dagilim) < 2 or len(p_dagilim) != len(q_dagilim):
        raise ValueError("boyut")
    for d in (p_dagilim, q_dagilim):
        for x in d:
            if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or not 0.0 <= x <= 1.0:
                raise ValueError("deger")
        if abs(sum(d) - 1.0) > 1e-6:
            raise ValueError("toplam")
    fark = [max(0.0, p - q) for p, q in zip(p_dagilim, q_dagilim)]
    toplam = sum(fark)
    if toplam <= 1e-12:
        raise ValueError("sifir_artik")
    return [v / toplam for v in fark]
def spekulatif_tur_ozeti(p_adimlar, q_adimlar, tokenlar, u_Ornekler):
    if not isinstance(p_adimlar, list) or not isinstance(q_adimlar, list) or not isinstance(tokenlar, list) or not isinstance(u_Ornekler, list):
        raise ValueError("liste")
    gamma = len(p_adimlar)
    if gamma < 1 or len(q_adimlar) != gamma or len(tokenlar) != gamma or len(u_Ornekler) != gamma:
        raise ValueError("gamma")
    sozluk = None
    for t in range(gamma):
        p_t, q_t = p_adimlar[t], q_adimlar[t]
        if not isinstance(p_t, list) or not isinstance(q_t, list) or len(p_t) < 2 or len(p_t) != len(q_t):
            raise ValueError("adim_boyut")
        if sozluk is not None and len(p_t) != sozluk:
            raise ValueError("sozluk_farkli")
        sozluk = len(p_t)
        for d in (p_t, q_t):
            for x in d:
                if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or not 0.0 <= x <= 1.0:
                    raise ValueError("olasilik")
            if abs(sum(d) - 1.0) > 1e-6:
                raise ValueError("toplam")
        tok = tokenlar[t]
        u = u_Ornekler[t]
        if isinstance(tok, bool) or not isinstance(tok, int) or not 0 <= tok < sozluk or q_t[tok] <= 0.0:
            raise ValueError("token")
        if isinstance(u, bool) or not isinstance(u, (int, float)) or not math.isfinite(u) or not 0.0 <= u < 1.0:
            raise ValueError("u_ornek")
    kabul_sayisi = 0
    red_adimi = None
    kurtarma_token = None
    for t in range(gamma):
        p_t, q_t = p_adimlar[t], q_adimlar[t]
        tok = tokenlar[t]
        alfa = kabul_olasiligi(p_t[tok], q_t[tok])
        if u_Ornekler[t] < alfa:
            kabul_sayisi += 1
        else:
            red_adimi = t
            artik = artik_dagilim(p_t, q_t)
            kurtarma_token = max(range(sozluk), key=lambda i: artik[i])
            break
    uretilen = kabul_sayisi + 1
    return {
        "kabul_sayisi": kabul_sayisi,
        "red_adimi": red_adimi,
        "kurtarma_token": kurtarma_token,
        "uretilen_token": uretilen,
        "hizlanma_carpani": float(uretilen),
    }
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_27 as D
    D.goster(kabul_olasiligi, artik_dagilim, spekulatif_tur_ozeti)
```
```hint
Üç işlevi birleştir; `spekulatif_tur_ozeti` içinde `kabul_olasiligi` ve `artik_dagilim` işlevlerini çağırabilirsin.
```
:::

::: anlat Sınır
Bu ders gerçek SmolLM2-135M'de tek dal (chain) üzerinde standart `speculative decoding` doğrulamasını, erken çıkış taslağıyla ve kendi metninde damıtılmış adaptörle gösterir. Hızlanmayı hedef çağrısı başına token olarak ölçer, duvar saati süresini ölçmez (taslak burada aynı ileri geçişten hesaplanır); ağaç tabanlı doğrulama (Medusa, SpecInfer, EAGLE), KV önbelleği, ayrı küçük bir taslak model ve kayıplı yaklaşımları kapsamaz. Az sayıda tur kabul oranını gürültülü ölçer.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Bellek bant genişliği darboğazı ve taslak–doğrula (30 sn).** "Tek token üretirken bütün hedef ağırlıklarını bellekten okumak pahalıdır; ucuz bir taslak model $\gamma$ aday token önerir, büyük hedef model hepsini tek paralel ileri geçişte puanlar."
2. **Kayıpsız red örneklemesi (`exact target distribution`) (35 sn).** "Her aday $\min(1, p(x)/q(x))$ olasılığıyla kabul edilir; ilk reddedilen konumda artık dağılım $\text{norm}(\max(0, p - q))$ üzerinden yeni token çekildiği için çıktı dağılımı matematiksel olarak tek başına hedef modelle birebir aynı kalır."
3. **Kabul oranı ve yan kanal yüzeyi (30 sn).** "SmolLM2 erken çıkış taslağında damıtılmış adaptör kabul oranını ve hedef çağrısı başına üretilen token sayısını yükseltir; ancak tur başına kabul edilen token sayısı bağlama bağlı olduğu için ağ paket boyutundan içerik yan kanalı doğurabilir."
4. **Soru (25 sn).** "Taslak model ne kadar kötü olursa olsun spekülatif doğrulama neden hedef modelin doğruluk veya güvenlik dağılımını bozmaz, yalnız hız kazancını düşürür?"
:::
