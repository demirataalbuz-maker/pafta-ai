---
id: ai-saldiri-57
title: Carlini Logit Model Extraction · Merkezleme ve SVD ile Gizli Boyut Keşfi
summary: Softmax kaydırma değişmezliğini gideren çift yönlü logit merkezlemesini uygula; SVD tekil değer spektrumundaki uçurumdan modelin gizli boyutunu (hidden dimension) ve son katman parametre uzayını GPU'da kurtar.
esleme: ai-saldiri-07, ai-saldiri-08, ai-guvence-38
timeout: 60
---

::: anlat API yalnızca olasılık döndürürken gizli katman boyutu nasıl çalınır?
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Ticari LLM API'lerinde `logit_bias` ve `logprobs` sorgularıyla oluşturulan $N \times V$ logit matrisinin `SVD` analizi, modelin gizli katman boyutunu ($d$) ve son projeksiyon matrisini ($W$) ortaya çıkarır (Carlini vd. 2024) | İlk üç görev: `veri/logit_svd.json` içindeki **sentetik** logit matrisi ve tekil değer spektrumları. Final: GPU'da gerçek `torch.linalg.svdvals` ile kaydırılmış logit matrisinden gizli boyutun ($d=12$) kurtarılması | Tam üretim modellerinde top-$k$ kısıtını aşmak için gereken kupon toplayıcı (`coupon collector`) sorgu planlamasını tek matrisle kapsamaz |
| Softmax her sorguda keyfi bir sabit kaydırma ($c_i$) içerdiği için ham matrisin rankı $d+1$ görünür | Çift yönlü (satır ve sütun) merkezleme, normalize tekil değer eşiği, spektral uçurum ve sızıntı raporu | Yalnız son doğrusal katmanı ($W$) kurtarır; iç transformer bloklarının ağırlıklarını doğrudan vermez |

> [!NOT]
> Görevler `veri/logit_svd.json` dosyasını okur; dosya sentetiktir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; değişiklikler taşınmaz, **kalıcılık yoktur**. Ekranda ayrı dosya görüntüleyici yoktur; içeriği görmek için `print` kullan. Gizli testler ayrıdır. Final yeni model indirmez ve GPU varsa onu kullanır.

Bir dil modelinin son katmanı, $d$ boyutlu gizli durum vektörünü ($h_i \in \mathbb{R}^d$) sözlük boyutundaki ($V \gg d$) `logit` vektörüne dönüştürür:
$$z_i = h_i W + c_i \mathbf{1}$$
Burada $W \in \mathbb{R}^{d \times V}$ embedding/projeksiyon matrisidir ve $c_i$ softmax'ın kaydırma değişmezliğinden (`shift invariance`) gelen sorguya özgü keyfi sabittir.

**Neden SVD gizli boyutu ele verir?** Sözlük boyutu $V = 100.000$ olsa bile, eğer modelin gizli boyutu $d = 4096$ ise, üretilebilecek tüm merkezlenmiş `logit` vektörleri en fazla $d$ boyutlu bir doğrusal altuzayda (`subspace`) yaşar. Carlini vd. (2024), $N > d$ adet rastgele istem gönderip dönen logitleri bir matriste topladığımızda, $d$'inci tekil değerden ($\sigma_d$) hemen sonra $\sigma_{d+1} \approx 0$ şeklinde devasa bir **spektral uçurum** (`spectral gap`) oluştuğunu göstermiştir.

**Merkezleme neden şarttır?** Her sorguda $c_i \mathbf{1}$ kayması farklıysa, ham logit matrisine doğrudan `SVD` uygulamak rankı 1 şişirir ve büyük kaymalarda sayısal gürültü üretir. Önce her satırın ortalamasını çıkararak $c_i$ kaymasını silmek, ardından her sütunun ortalamasını çıkararak sorgu kümesini orijine taşımak gerekir.

**Saldırgan ne dener?** `logit_bias` parametresiyle belirli tokenlerin logitlerini yukarı çekip top-1/top-5 `logprobs` farklarından tam `logit` vektörlerini yeniden inşa eder (`model extraction`); ardından `SVD` ile $d$'yi ve $W$ altuzayını kurtarır.

**Savunma neden kırılır?** API'nin yalnız top-5 olasılık döndürmesi savunma sanılır; oysa saldırgan `logit_bias` kullanımına sahipse istediği tokeni top-1'e taşıyarak göreceli logit farkını okuyabilir. Gerçek savunma, `logit_bias` ile `logprobs` kombinasyonunu kısıtlamak veya çıktılara kontrollü quantization/gürültü eklemektir.

**Görev 1'de sık tuzaklar:** Yalnız satır ortalamasını çıkarıp sütun ortalamasını unutmamak veya girdi matrisini yerinde (`in-place`) değiştirmek testi kırar.

Kaynaklar: [Carlini vd. 2024 - Stealing Part of a Production Language Model](https://arxiv.org/abs/2403.06634), [Tramèr vd. 2016 - Stealing Machine Learning Models via Prediction APIs](https://arxiv.org/abs/1609.02943), [Jagielski vd. 2020 - High Accuracy and High Fidelity Extraction of Neural Networks](https://arxiv.org/abs/1909.01838). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Köprü: ai-saldiri-07 ve ai-saldiri-08 olasılık sızıntısını inceler; ai-guvence-38 gömme uzayında PCA uygular; bu ders `SVD` spektrumuyla gizli mimari parametrelerin çalınmasını (`model extraction`) gösterir.
:::

::: tahmin Sabit kaydırma matris rankını nasıl şişirir?
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
matris = [
    [1.0 + 10.0, 2.0 + 10.0, 3.0 + 10.0],
    [2.0 - 5.0,  4.0 - 5.0,  6.0 - 5.0],
]
satir_m = [[v - sum(s) / len(s) for v in s] for s in matris]
print("Satır merkezli 0:", [round(x, 2) for x in satir_m[0]])
print("Satır merkezli 1:", [round(x, 2) for x in satir_m[1]])
print("Oran (satır 1 / satır 0):", [satir_m[1][j] / satir_m[0][j] for j in (0, 2)])
```
???
```cikti
Satır merkezli 0: [-1.0, 0.0, 1.0]
Satır merkezli 1: [-2.0, 0.0, 2.0]
Oran (satır 1 / satır 0): [2.0, 2.0]
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: başlangıçta birbirinin katı görünmeyen iki satır, satır ortalaması çıkarılınca neden tam olarak `2.0` katı (rank 1) hâline geldi? Sonra üç kusurlu başlangıç kodunu çalıştır ve her birinin neyi kaçırdığını önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · Çift yönlü logit merkezleme
`logit_merkezle(logit_matrisi)`: `logit_matrisi` en az 2 satırlı liste; her satır en az 2 elemanlı ve eşit uzunlukta liste; tüm değerler bool olmayan sonlu sayı. Önce her satırın kendi aritmetik ortalamasını o satırın elemanlarından çıkar; ardından elde edilen matrisin her sütununun aritmetik ortalamasını o sütundaki elemanlardan çıkar ve yeni matrisi döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-57")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def logit_merkezle(logit_matrisi):
    return [[v - sum(s) / len(s) for v in s] for s in logit_matrisi]

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/logit_svd.json")
print("Merkezli:", logit_merkezle(v["logit_matrisi"]))
```
```test
def sinama1(f):
    import copy, math, random
    def _r(M):
        n, m = len(M), len(M[0])
        a = [[v - sum(s) / m for v in s] for s in M]
        c = [sum(a[i][j] for i in range(n)) / n for j in range(m)]
        return [[a[i][j] - c[j] for j in range(m)] for i in range(n)]
    def _y(A, B):
        return isinstance(A, list) and len(A) == len(B) and all(isinstance(r, list) and len(r) == len(s) and all(abs(x - y) < 1e-11 for x, y in zip(r, s)) for r, s in zip(A, B))
    try:
        M = [[12.0, 14.0, 10.0], [2.0, 6.0, -2.0]]; old = copy.deepcopy(M)
        out = f(M)
        if M != old or not _y(out, _r(M)):
            return False
        if any(abs(sum(s)) > 1e-11 for s in out) or any(abs(sum(out[i][j] for i in range(len(out)))) > 1e-11 for j in range(len(out[0]))):
            return False
        rng = random.Random(57)
        for _ in range(25):
            r = rng.randint(2, 6); c = rng.randint(2, 6)
            X = [[rng.uniform(-50, 50) for _ in range(c)] for _ in range(r)]
            if not _y(f(copy.deepcopy(X)), _r(X)):
                return False
        for bad in (None, [], [[1.0, 2.0]], [[1.0], [2.0]], [[1.0, 2.0], [1.0]], [[1.0, True], [2.0, 3.0]], [[1.0, float("nan")], [2.0, 3.0]], [[1.0, float("inf")], [2.0, 3.0]], ([1.0, 2.0], [3.0, 4.0]), [[1.0, "2"], [3.0, 4.0]]):
            try:
                f(bad); return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sinama1(logit_merkezle), "satır ve sütun merkezleme, değişmezlik ve geçersiz girdi")
for ad, mut in [("yalnız satır merkezli", lambda M: [[v - sum(s) / len(s) for v in s] for s in M]), ("yalnız sütun merkezli", lambda M: [[M[i][j] - sum(M[k][j] for k in range(len(M))) / len(M) for j in range(len(M[0]))] for i in range(len(M))]), ("işaret ters", lambda M: [[-x for x in s] for s in logit_merkezle(M)])]:
    ok(not sinama1(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(logit_merkezle, _il.import_module('ai_gercek_ai_saldiri_57').referans_merkezle, ([[12.0, 14.0, 10.0, 16.0], [2.0, 6.0, -2.0, 10.0], [7.0, 8.0, 6.0, 9.0], [-3.0, 1.0, -7.0, 5.0]],), tohum=2645)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def logit_merkezle(logit_matrisi):
    if not isinstance(logit_matrisi, list) or len(logit_matrisi) < 2:
        raise ValueError("matris")
    if not all(isinstance(s, list) and len(s) >= 2 for s in logit_matrisi):
        raise ValueError("satır")
    m = len(logit_matrisi[0])
    if any(len(s) != m for s in logit_matrisi):
        raise ValueError("boyut")
    for s in logit_matrisi:
        for v in s:
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                raise ValueError("sayı")
    n = len(logit_matrisi)
    a = [[v - sum(s) / m for v in s] for s in logit_matrisi]
    c = [sum(a[i][j] for i in range(n)) / n for j in range(m)]
    return [[a[i][j] - c[j] for j in range(m)] for i in range(n)]

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/logit_svd.json")
print("Merkezli:", logit_merkezle(v["logit_matrisi"]))
```
```hint
Önce her satırdan kendi ortalamasını çıkarıp ara matris `a` oluştur; sonra `a`'nın her sütununun ortalamasını çıkar.
```
:::

::: anlat Tekil değer spektrumundan etkin boyut nasıl okunur?
Azalan sıradaki tekil değerler $\sigma_1 \ge \sigma_2 \ge \dots \ge \sigma_k \ge 0$ verildiğinde:
- Bağıl eşik: $\tau = \sigma_1 \cdot \text{tol}$.
- `etkin_boyut` ($d$): $\sigma_i > \tau$ şartını sağlayan tekil değerlerin sayısı.
- `enerji_orani`: İlk $d$ tekil değerin kareleri toplamının tüm tekil değerlerin kareleri toplamına oranı ($\sum_{i=1}^d \sigma_i^2 / \sum_{j=1}^k \sigma_j^2$).
- `spektral_ucurum`: Eğer $d < k$ ise $\sigma_d / \max(\sigma_{d+1}, 10^{-12})$, eğer $d == k$ ise `None`.

**Görev 2'de sık tuzaklar:** Eşiği $\sigma_1 \cdot \text{tol}$ yerine doğrudan mutlak `tol` almak ölçekten etkilenir; enerjide $\sigma_i$ yerine $\sigma_i^2$ (Frobenius normu karesi) toplanmalıdır.
:::

::: gorev 2 · SVD tekil değerlerinden etkin boyut tahmini
`etkin_boyut_tahmini(tekil_degerler, tol)`: `tekil_degerler` boş olmayan liste, tümü bool olmayan sonlu sayı ve `>= 0`, ilk eleman `> 0` ve liste artmayan sırada (`s[i] >= s[i+1]`). `tol` bool olmayan sonlu sayı ve `0 < tol < 1`. Yukarıdaki tanıma göre `{"etkin_boyut": ..., "enerji_orani": ..., "spektral_ucurum": ...}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-57")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def etkin_boyut_tahmini(tekil_degerler, tol):
    d = sum(1 for s in tekil_degerler if s > tol)
    return {"etkin_boyut": d, "enerji_orani": 1.0, "spektral_ucurum": None}

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/logit_svd.json")
for ad, s in v["spektrumlar"].items():
    print(ad, etkin_boyut_tahmini(s["tekil_degerler"], v["tol"]))
```
```test
def sinama2(f):
    import copy, math
    def _y(a, b):
        if not isinstance(a, dict) or set(a) != set(b) or a["etkin_boyut"] != b["etkin_boyut"]:
            return False
        if (a["spektral_ucurum"] is None) != (b["spektral_ucurum"] is None):
            return False
        if a["spektral_ucurum"] is not None and abs(a["spektral_ucurum"] - b["spektral_ucurum"]) > 1e-9 * max(1.0, abs(b["spektral_ucurum"])):
            return False
        return abs(a["enerji_orani"] - b["enerji_orani"]) < 1e-12
    try:
        s = [100.0, 50.0, 0.5, 0.0]; old = list(s)
        r = f(s, 0.01)
        if s != old or not _y(r, {"etkin_boyut": 2, "enerji_orani": 12500.0 / 12500.25, "spektral_ucurum": 100.0}):
            return False
        if not _y(f([10.0, 5.0], 0.1), {"etkin_boyut": 2, "enerji_orani": 1.0, "spektral_ucurum": None}):
            return False
        if not _y(f([10.0, 0.0], 0.01), {"etkin_boyut": 1, "enerji_orani": 1.0, "spektral_ucurum": 10.0 / 1e-12}):
            return False
        if not _y(f([0.5, 0.1], 0.5), {"etkin_boyut": 1, "enerji_orani": 0.25 / 0.26, "spektral_ucurum": 5.0}):
            return False
        for bad in ((None, 0.1), ([], 0.1), ([0.0, 0.0], 0.1), ([5.0, 10.0], 0.1), ([10.0, -1.0], 0.1), ([True, 1.0], 0.1), ([float("nan")], 0.1), ([10.0], 0.0), ([10.0], 1.0), ([10.0], -0.1), ([10.0], True), ([10.0], float("nan"))):
            try:
                f(*bad); return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sinama2(etkin_boyut_tahmini), "bağıl eşik, kare enerji oranı, spektral uçurum ve geçersiz girdi")
for ad, mut in [("mutlak eşik", lambda s, t: dict(etkin_boyut_tahmini(s, t), etkin_boyut=sum(1 for x in s if x > t))), ("doğrusal enerji", lambda s, t: dict(etkin_boyut_tahmini(s, t), enerji_orani=sum(s[:etkin_boyut_tahmini(s, t)["etkin_boyut"]]) / sum(s))), ("uçurum hep None", lambda s, t: dict(etkin_boyut_tahmini(s, t), spektral_ucurum=None))]:
    ok(not sinama2(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(etkin_boyut_tahmini, _il.import_module('ai_gercek_ai_saldiri_57').referans_boyut, ([42.0, 35.0, 28.0, 21.0, 14.0, 9.0, 6.0, 4.0, 0.002, 0.001, 0.0005, 0.0], 0.01), tohum=3182)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def etkin_boyut_tahmini(tekil_degerler, tol):
    if not isinstance(tekil_degerler, list) or not tekil_degerler:
        raise ValueError("liste")
    for v in tekil_degerler:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
            raise ValueError("sayı")
    if tekil_degerler[0] <= 0 or any(tekil_degerler[i] < tekil_degerler[i + 1] for i in range(len(tekil_degerler) - 1)):
        raise ValueError("sıra")
    if isinstance(tol, bool) or not isinstance(tol, (int, float)) or not math.isfinite(tol) or not 0 < tol < 1:
        raise ValueError("tol")
    esik = tekil_degerler[0] * tol
    d = sum(1 for s in tekil_degerler if s > esik)
    top = sum(s * s for s in tekil_degerler)
    enerji = sum(s * s for s in tekil_degerler[:d]) / top
    ucurum = tekil_degerler[d - 1] / max(tekil_degerler[d], 1e-12) if d < len(tekil_degerler) else None
    return {"etkin_boyut": d, "enerji_orani": enerji, "spektral_ucurum": ucurum}

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/logit_svd.json")
for ad, s in v["spektrumlar"].items():
    print(ad, etkin_boyut_tahmini(s["tekil_degerler"], v["tol"]))
```
```hint
Eşiği `tekil_degerler[0] * tol` olarak kur; enerji oranında `s * s` toplamlarını kullan.
```
:::

::: anlat Model extraction sızıntı raporu nasıl yorumlanır?
Saldırgan $N$ sorgu (`sorgu_sayisi`) ve $V$ sözlük boyutu (`sozluk_boyutu`) ile yaptığı ölçümde etkin boyutu $d$ bulduğunda:
- `sikistirma_orani = d / min(sorgu_sayisi, sozluk_boyutu)`
- `tahmini_parametre = d * sozluk_boyutu` (kurtarılan son katman matrisinin eleman sayısı)
- `sizinti_durumu`: Eğer `sorgu_sayisi > d` **ve** `d < min(sorgu_sayisi, sozluk_boyutu)` **ve** `enerji_orani >= 0.99` ise `"tam_altuzay"`, aksi hâlde `"kismi_iz"`.

**Görev 3'te sık tuzaklar:** Sorgu sayısı henüz gizli boyutu aşmadıysa (`sorgu_sayisi == d`), tüm tekil değerler büyük kalır; buna `"tam_altuzay"` demek yanlıştır çünkü altuzay henüz doygunluğa ulaşmamıştır (`"kismi_iz"`).
:::

::: gorev 3 · Extraction sızıntı raporu
`extraction_sizinti_raporu(tekil_degerler, sorgu_sayisi, sozluk_boyutu, tol)`: `tekil_degerler` ve `tol` Görev 2 kurallarına uymalı; `sorgu_sayisi` ve `sozluk_boyutu` bool olmayan `int` ve `>= len(tekil_degerler)` olmalı. `{"etkin_boyut": d, "sikistirma_orani": ..., "tahmini_parametre": ..., "sizinti_durumu": "tam_altuzay"|"kismi_iz"}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-57")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def extraction_sizinti_raporu(tekil_degerler, sorgu_sayisi, sozluk_boyutu, tol):
    d = len(tekil_degerler)
    return {"etkin_boyut": d, "sikistirma_orani": 1.0, "tahmini_parametre": d * sozluk_boyutu, "sizinti_durumu": "kismi_iz"}

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/logit_svd.json")
for ad, s in v["spektrumlar"].items():
    print(ad, extraction_sizinti_raporu(s["tekil_degerler"], s["sorgu_sayisi"], s["sozluk_boyutu"], v["tol"]))
```
```test
def sinama3(f):
    import copy, math
    try:
        s = [40.0, 30.0, 20.0, 0.001, 0.0]; old = list(s)
        r = f(s, 10, 100, 0.01)
        if s != old or r != {"etkin_boyut": 3, "sikistirma_orani": 0.3, "tahmini_parametre": 300, "sizinti_durumu": "tam_altuzay"}:
            return False
        if f([20.0, 15.0, 10.0], 3, 50, 0.01) != {"etkin_boyut": 3, "sikistirma_orani": 1.0, "tahmini_parametre": 150, "sizinti_durumu": "kismi_iz"}:
            return False
        if f([10.0, 5.0, 5.0], 6, 50, 0.6)["sizinti_durumu"] != "kismi_iz":
            return False
        # N=d ve V=d sınırları tam altuzay kanıtı değildir.
        for n, v in ((3, 50), (50, 3), (3, 3)):
            r = f([20.0, 15.0, 10.0], n, v, 0.01)
            if r != {"etkin_boyut": 3, "sikistirma_orani": 1.0, "tahmini_parametre": 3 * v, "sizinti_durumu": "kismi_iz"}:
                return False
        # Enerji oranı tam 0.99: >= ile > ayrışır.
        if f([math.sqrt(99.0), 1.0], 3, 3, 0.11)["sizinti_durumu"] != "tam_altuzay":
            return False
        try:
            f([0.0, 0.0], 3, 3, 0.1)
            return False
        except ValueError:
            pass
        # Her iki boyutta da bir fazla gözlem bulununca tam altuzay olur.
        if f([20.0, 15.0, 10.0, 0.0], 4, 4, 0.01)["sizinti_durumu"] != "tam_altuzay":
            return False
        if f([0.5, 0.1], 5, 10, 0.5)["etkin_boyut"] != 1:
            return False
        for bad in (([], 5, 10, 0.1), ([True, 0.5], 5, 10, 0.1), ([2.0, -0.1], 5, 10, 0.1), ([3.0, 2.0, 2.5], 5, 10, 0.1), ([1.0], True, 10, 0.1), ([10.0, 5.0], 1, 10, 0.1), ([10.0, 5.0], 10, 1, 0.1), ([10.0, 5.0], True, 10, 0.1), ([10.0, 5.0], 5, False, 0.1), ([10.0, 5.0], 5.5, 10, 0.1), ([10.0, 5.0], 5, 10, 0.0)):
            try:
                f(*bad); return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sinama3(extraction_sizinti_raporu), "etkin boyut, sıkıştırma oranı, parametre tahmini ve sızıntı durumu")
for ad, mut in [("hep kismi_iz", lambda s, n, v, t: dict(extraction_sizinti_raporu(s, n, v, t), sizinti_durumu="kismi_iz")), ("hep tam_altuzay", lambda s, n, v, t: dict(extraction_sizinti_raporu(s, n, v, t), sizinti_durumu="tam_altuzay")), ("parametre sorguyla çarpıldı", lambda s, n, v, t: dict(extraction_sizinti_raporu(s, n, v, t), tahmini_parametre=extraction_sizinti_raporu(s, n, v, t)["etkin_boyut"] * n))]:
    ok(not sinama3(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(extraction_sizinti_raporu, _il.import_module('ai_gercek_ai_saldiri_57').referans_rapor, ([42.0, 35.0, 28.0, 21.0, 14.0, 9.0, 6.0, 4.0, 0.002, 0.001, 0.0005, 0.0], 32, 128, 0.01), tohum=3866)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(etkin_boyut_tahmini, _il.import_module('ai_gercek_ai_saldiri_57').referans_boyut, ([42.0, 35.0, 28.0, 21.0, 14.0, 9.0, 6.0, 4.0, 0.002, 0.001, 0.0005, 0.0], 0.01), tohum=3182, ekler=(([10.0, 0.0], 0.01),))
ok(_t, "farksal tarama (etkin_boyut_tahmini): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def etkin_boyut_tahmini(tekil_degerler, tol):
    if not isinstance(tekil_degerler, list) or not tekil_degerler:
        raise ValueError("liste")
    for v in tekil_degerler:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
            raise ValueError("sayı")
    if tekil_degerler[0] <= 0 or any(tekil_degerler[i] < tekil_degerler[i + 1] for i in range(len(tekil_degerler) - 1)):
        raise ValueError("sıra")
    if isinstance(tol, bool) or not isinstance(tol, (int, float)) or not math.isfinite(tol) or not 0 < tol < 1:
        raise ValueError("tol")
    esik = tekil_degerler[0] * tol
    d = sum(1 for s in tekil_degerler if s > esik)
    top = sum(s * s for s in tekil_degerler)
    enerji = sum(s * s for s in tekil_degerler[:d]) / top
    ucurum = tekil_degerler[d - 1] / max(tekil_degerler[d], 1e-12) if d < len(tekil_degerler) else None
    return {"etkin_boyut": d, "enerji_orani": enerji, "spektral_ucurum": ucurum}

def extraction_sizinti_raporu(tekil_degerler, sorgu_sayisi, sozluk_boyutu, tol):
    b = etkin_boyut_tahmini(tekil_degerler, tol)
    for k in (sorgu_sayisi, sozluk_boyutu):
        if isinstance(k, bool) or not isinstance(k, int) or k < len(tekil_degerler):
            raise ValueError("boyut")
    d = b["etkin_boyut"]
    ust = min(sorgu_sayisi, sozluk_boyutu)
    durum = "tam_altuzay" if (sorgu_sayisi > d and d < ust and b["enerji_orani"] >= 0.99) else "kismi_iz"
    return {"etkin_boyut": d, "sikistirma_orani": d / ust, "tahmini_parametre": d * sozluk_boyutu, "sizinti_durumu": durum}

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/logit_svd.json")
for ad, s in v["spektrumlar"].items():
    print(ad, extraction_sizinti_raporu(s["tekil_degerler"], s["sorgu_sayisi"], s["sozluk_boyutu"], v["tol"]))
```
```hint
`etkin_boyut_tahmini` çıktısını kullan; `ust = min(sorgu_sayisi, sozluk_boyutu)` üzerinden sıkıştırma oranını ve üçlü `"tam_altuzay"` şartını hesapla.
```
:::

::: anlat Hata vitrini · çalışmış yanlış rapor
Yazar, kusurlu başlangıç kodlarını görünür sentetik veriyle çalıştırdı ve sonucu `outputs/yeni-ai-saldiri-57/gorunur-run-1.json` dosyasına kaydetti. `dusuk_rank_gizli_8` spektrumunda kusurlu kod mutlak eşik kullandığı için `0.002` gibi gürültü tekil değerlerini bile gerçek boyut sayıp `etkin_boyut=11` ve `sizinti_durumu="kismi_iz"` döndürür. Doğru kod ise bağıl eşikle tam olarak `etkin_boyut=8`, `spektral_ucurum=2000.0` ve `sizinti_durumu="tam_altuzay"` bulur.

Bu kaydedilmiş bir hesaplama çıktısıdır, canlı model yanıtı değildir ve rapor sentetiktir. Merkezleme veya bağıl eşik yapmadan SVD spektrumuna bakan bir analist neden modelin gizli boyutunu yanlış tahmin eder? Kendi cümlenle açıkla.
:::

::: anlat Gerçek deney: SmolLM2'nin API log-olasılıklarından gizli boyutu ve son katmanı çalmak
Final, yerel önbellekteki gerçek **SmolLM2-135M** modelini (sabit revizyon, indirme yok) bir "API" gibi kullanır. Modele $N = 640$ rastgele kısa istem gönderir ve her yanıtta, gerçek bir API'nin döndürdüğü gibi **log-olasılıkları** (`log_softmax`) alır; bu dönüşüm her satıra sorguya özgü bir sabit ekler. Saldırgan 49.152 sözcüklük sözlüğün rastgele 2.048 sütununu görür. Ham matriste SVD bu satır kayması yüzünden bir fazla boyut gösterir; senin `logit_merkezle` işlevinle çift yönlü merkezlenen matriste spektrum tam olarak modelin `hidden_size` değerinde ($d = 576$) uçuruma düşer.

Deney bir adım daha atar: üst $d$ sağ tekil vektörün gerdiği altuzayı, modelin gerçek `lm_head` ağırlıklarının aynı sütunlarla gerdiği altuzayla karşılaştırır (temel açılar). Kosinüslerin hepsi 1'e çok yakınsa saldırgan son katmanı **bir dönüşüme kadar** ele geçirmiştir; Carlini vd. (2024), üretim API'lerinde projeksiyon katmanı kurtarmayı gösterdi; yerel deneyin maliyeti veya başarısı bu hizmetlere genellenmez.

Kabul; üç işlevin bağımsız referansla aynı sonucu vermesine, merkezleme sonrası etkin boyutun modelin `hidden_size` değerine (576) eşit çıkmasına, ham matrisin bir fazla boyut göstermesine ve kurtarılan altuzayın gerçek son katmanla örtüşmesine (en küçük açı kosinüsü > 0.999) bağlıdır.

**Kanıt dosyasını oku:** `ucurum_kati` ve `uçurum_cevresi_bagil` alanlarına bak. Soru 1: 576. ve 577. tekil değer arasındaki uçurum kaç kat; bu oran float32 logitlerin sayısal gürültüsü hakkında ne söyler? Soru 2: `ham_tahmini_boyut` neden 577; hangi tek satırlık ön işlem bu fazlalığı sildi? Soru 3: Savunmacı yalnız ilk 5 log-olasılığı döndürseydi bu deneyin hangi adımı imkânsız hâle gelirdi (bkz. ai-savunma-40)?
:::

::: gorev Gerçek deney · GPU SVD ile logit matrisinden gizli boyut keşfi
Önceki üç görevin `logit_merkezle`, `etkin_boyut_tahmini` ve `extraction_sizinti_raporu` işlevlerini birleştir. Çalıştır gerçek tabloyu gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 180
```
```starter
import ai_lab
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def logit_merkezle(logit_matrisi):
    return [[v - sum(s) / len(s) for v in s] for s in logit_matrisi]

def etkin_boyut_tahmini(tekil_degerler, tol):
    d = sum(1 for s in tekil_degerler if s > tol)
    return {"etkin_boyut": d, "enerji_orani": 1.0, "spektral_ucurum": None}

def extraction_sizinti_raporu(tekil_degerler, sorgu_sayisi, sozluk_boyutu, tol):
    d = len(tekil_degerler)
    return {"etkin_boyut": d, "sikistirma_orani": 1.0, "tahmini_parametre": d * sozluk_boyutu, "sizinti_durumu": "kismi_iz"}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_57 as D
    D.goster(logit_merkezle, etkin_boyut_tahmini, extraction_sizinti_raporu)
```
```test
import ai_lab, math
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('referans_merkezle', 'referans_boyut', 'referans_rapor', 'kanit_yaz', '_yakin'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
logit_merkezle = need("logit_merkezle")
etkin_boyut_tahmini = need("etkin_boyut_tahmini")
extraction_sizinti_raporu = need("extraction_sizinti_raporu")
def sinama1(f):
    import copy, math, random
    def _r(M):
        n, m = len(M), len(M[0])
        a = [[v - sum(s) / m for v in s] for s in M]
        c = [sum(a[i][j] for i in range(n)) / n for j in range(m)]
        return [[a[i][j] - c[j] for j in range(m)] for i in range(n)]
    def _y(A, B):
        return isinstance(A, list) and len(A) == len(B) and all(isinstance(r, list) and len(r) == len(s) and all(abs(x - y) < 1e-11 for x, y in zip(r, s)) for r, s in zip(A, B))
    try:
        M = [[12.0, 14.0, 10.0], [2.0, 6.0, -2.0]]; old = copy.deepcopy(M)
        out = f(M)
        if M != old or not _y(out, _r(M)) or not _y(f([[1.0, 3.0], [5.0, 7.0]]), _r([[1.0, 3.0], [5.0, 7.0]])): return False
        for bad in (None, [], [[1.0, 2.0]], [[1.0], [2.0]], [[1.0, 2.0], [1.0]], [[1.0, True], [2.0, 3.0]], [[1.0, float("nan")], [2.0, 3.0]]):
            try: f(bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama1(logit_merkezle), "satır ve sütun merkezleme ve geçersiz girdi")
for ad, mut in [("yalnız satır merkezli", lambda M: [[v - sum(s) / len(s) for v in s] for s in M]), ("yalnız sütun merkezli", lambda M: [[M[i][j] - sum(M[k][j] for k in range(len(M))) / len(M) for j in range(len(M[0]))] for i in range(len(M))]), ("işaret ters", lambda M: [[-x for x in s] for s in logit_merkezle(M)])]:
    kontrol(not sinama1(mut), "mutant reddedildi: " + ad)
def sinama2(f):
    def _y(a, b):
        if not isinstance(a, dict) or set(a) != set(b) or a["etkin_boyut"] != b["etkin_boyut"]: return False
        if (a["spektral_ucurum"] is None) != (b["spektral_ucurum"] is None): return False
        if a["spektral_ucurum"] is not None and abs(a["spektral_ucurum"] - b["spektral_ucurum"]) > 1e-9 * max(1.0, abs(b["spektral_ucurum"])): return False
        return abs(a["enerji_orani"] - b["enerji_orani"]) < 1e-12
    try:
        s = [100.0, 50.0, 0.5, 0.0]; old = list(s)
        if not _y(f(s, 0.01), {"etkin_boyut": 2, "enerji_orani": 12500.0 / 12500.25, "spektral_ucurum": 100.0}) or s != old: return False
        if not _y(f([10.0, 5.0], 0.1), {"etkin_boyut": 2, "enerji_orani": 1.0, "spektral_ucurum": None}): return False
        if not _y(f([1.0, 0.0], 0.1), {"etkin_boyut": 1, "enerji_orani": 1.0, "spektral_ucurum": 1.0 / 1e-12}): return False
        if not _y(f([0.5, 0.1], 0.5), {"etkin_boyut": 1, "enerji_orani": 0.25 / 0.26, "spektral_ucurum": 5.0}): return False
        for bad in ((None, 0.1), ([], 0.1), ([0.0, 0.0], 0.1), ([5.0, 10.0], 0.1), ([10.0, -1.0], 0.1), ([True, 0.5], 0.1), ([10.0], 0.0), ([10.0], 1.0), ([10.0], True)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama2(etkin_boyut_tahmini), "bağıl eşik, kare enerji oranı ve spektral uçurum")
for ad, mut in [("mutlak eşik", lambda s, t: dict(etkin_boyut_tahmini(s, t), etkin_boyut=sum(1 for x in s if x > t))), ("doğrusal enerji", lambda s, t: dict(etkin_boyut_tahmini(s, t), enerji_orani=sum(s[:etkin_boyut_tahmini(s, t)["etkin_boyut"]]) / sum(s))), ("uçurum hep None", lambda s, t: dict(etkin_boyut_tahmini(s, t), spektral_ucurum=None))]:
    kontrol(not sinama2(mut), "mutant reddedildi: " + ad)
def sinama3(f):
    try:
        s = [40.0, 30.0, 20.0, 0.001, 0.0]; old = list(s)
        if f(s, 10, 100, 0.01) != {"etkin_boyut": 3, "sikistirma_orani": 0.3, "tahmini_parametre": 300, "sizinti_durumu": "tam_altuzay"} or s != old: return False
        if f([20.0, 15.0, 10.0], 3, 50, 0.01)["sizinti_durumu"] != "kismi_iz" or f([20.0, 15.0, 10.0], 50, 3, 0.01)["sizinti_durumu"] != "kismi_iz": return False
        if f([math.sqrt(99.0), 1.0], 3, 3, 0.11)["sizinti_durumu"] != "tam_altuzay" or f([0.5, 0.1], 5, 10, 0.5)["etkin_boyut"] != 1: return False
        for bad in (([], 5, 10, 0.1), ([True, 0.5], 5, 10, 0.1), ([2.0, -0.1], 5, 10, 0.1), ([3.0, 2.0, 2.5], 5, 10, 0.1), ([1.0], True, 10, 0.1), ([10.0, 5.0], 1, 10, 0.1), ([10.0, 5.0], True, 10, 0.1), ([10.0, 5.0], 5, 10, 0.0)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama3(extraction_sizinti_raporu), "etkin boyut, sıkıştırma oranı ve sızıntı durumu")
for ad, mut in [("hep kismi_iz", lambda s, n, v, t: dict(extraction_sizinti_raporu(s, n, v, t), sizinti_durumu="kismi_iz")), ("hep tam_altuzay", lambda s, n, v, t: dict(extraction_sizinti_raporu(s, n, v, t), sizinti_durumu="tam_altuzay")), ("parametre sorguyla çarpıldı", lambda s, n, v, t: dict(extraction_sizinti_raporu(s, n, v, t), tahmini_parametre=extraction_sizinti_raporu(s, n, v, t)["etkin_boyut"] * n))]:
    kontrol(not sinama3(mut), "mutant reddedildi: " + ad)
# farksal tarama (final)
import importlib as _il
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_R = _il.import_module('sandbox.ai_gercek_ai_saldiri_57')
for _ad, _ref, _taban, _toh in (
    ('logit_merkezle', 'referans_merkezle', ([[12.0, 14.0, 10.0, 16.0], [2.0, 6.0, -2.0, 10.0], [7.0, 8.0, 6.0, 9.0], [-3.0, 1.0, -7.0, 5.0]],), 3167),
    ('etkin_boyut_tahmini', 'referans_boyut', ([42.0, 35.0, 28.0, 21.0, 14.0, 9.0, 6.0, 4.0, 0.002, 0.001, 0.0005, 0.0], 0.01), 3704),
    ('extraction_sizinti_raporu', 'referans_rapor', ([42.0, 35.0, 28.0, 21.0, 14.0, 9.0, 6.0, 4.0, 0.002, 0.001, 0.0005, 0.0], 32, 128, 0.01), 4388),
):
    _t, _g = _ff(need(_ad), getattr(_R, _ref), _taban, tohum=_toh)
    kontrol(_t, "farksal tarama (" + _ad + "): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
if not all(checks): stop()
from sandbox import ai_gercek_ai_saldiri_57 as D
try: r = D.deney(logit_merkezle, etkin_boyut_tahmini, extraction_sizinti_raporu)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r["merkezle_ayni"], "gerçek logit matrisinde çift yönlü merkezleme bağımsız hesapla aynı")
kontrol(r["boyut_ayni"], "gerçek SVD spektrumunda etkin boyut analizi bağımsız hesapla aynı")
kontrol(r["rapor_ayni"], "gerçek SVD spektrumunda sızıntı raporu bağımsız hesapla aynı")
kontrol(r["merkezli_boyut_analizi"]["etkin_boyut"] == r["gercek_gizli_boyut"], f"merkezleme sonrası SVD SmolLM2'nin gizli boyutunu ({r['gercek_gizli_boyut']}) tam kurtardı")
kontrol(r["ham_tahmini_boyut"] == r["gercek_gizli_boyut"] + 1, "ham API log-olasılıklarında satır kayması bir fazla boyut gösterdi")
kontrol(r["altuzay_kosinus_min"] > 0.999, "kurtarılan altuzay gerçek lm_head altuzayıyla örtüşüyor (en küçük açı kosinüsü > 0.999)")
kontrol(r["sizinti_raporu"]["sizinti_durumu"] == "tam_altuzay", "altuzay sızıntısı tam_altuzay olarak doğrulandı")
ai_lab.kanit_yaz("ai-saldiri-57-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-saldiri-57", "deney": r})
```
```solution
import ai_lab
import math
def logit_merkezle(logit_matrisi):
    if not isinstance(logit_matrisi, list) or len(logit_matrisi) < 2:
        raise ValueError("matris")
    if not all(isinstance(s, list) and len(s) >= 2 for s in logit_matrisi):
        raise ValueError("satır")
    m = len(logit_matrisi[0])
    if any(len(s) != m for s in logit_matrisi):
        raise ValueError("boyut")
    for s in logit_matrisi:
        for v in s:
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                raise ValueError("sayı")
    n = len(logit_matrisi)
    a = [[v - sum(s) / m for v in s] for s in logit_matrisi]
    c = [sum(a[i][j] for i in range(n)) / n for j in range(m)]
    return [[a[i][j] - c[j] for j in range(m)] for i in range(n)]

def etkin_boyut_tahmini(tekil_degerler, tol):
    if not isinstance(tekil_degerler, list) or not tekil_degerler:
        raise ValueError("liste")
    for v in tekil_degerler:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
            raise ValueError("sayı")
    if tekil_degerler[0] <= 0 or any(tekil_degerler[i] < tekil_degerler[i + 1] for i in range(len(tekil_degerler) - 1)):
        raise ValueError("sıra")
    if isinstance(tol, bool) or not isinstance(tol, (int, float)) or not math.isfinite(tol) or not 0 < tol < 1:
        raise ValueError("tol")
    esik = tekil_degerler[0] * tol
    d = sum(1 for s in tekil_degerler if s > esik)
    top = sum(s * s for s in tekil_degerler)
    enerji = sum(s * s for s in tekil_degerler[:d]) / top
    ucurum = tekil_degerler[d - 1] / max(tekil_degerler[d], 1e-12) if d < len(tekil_degerler) else None
    return {"etkin_boyut": d, "enerji_orani": enerji, "spektral_ucurum": ucurum}

def extraction_sizinti_raporu(tekil_degerler, sorgu_sayisi, sozluk_boyutu, tol):
    b = etkin_boyut_tahmini(tekil_degerler, tol)
    for k in (sorgu_sayisi, sozluk_boyutu):
        if isinstance(k, bool) or not isinstance(k, int) or k < len(tekil_degerler):
            raise ValueError("boyut")
    d = b["etkin_boyut"]
    ust = min(sorgu_sayisi, sozluk_boyutu)
    durum = "tam_altuzay" if (sorgu_sayisi > d and d < ust and b["enerji_orani"] >= 0.99) else "kismi_iz"
    return {"etkin_boyut": d, "sikistirma_orani": d / ust, "tahmini_parametre": d * sozluk_boyutu, "sizinti_durumu": durum}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_57 as D
    D.goster(logit_merkezle, etkin_boyut_tahmini, extraction_sizinti_raporu)
```
```hint
Üç işlevi birleştir; çift yönlü merkezlemenin hem satır hem sütun ortalamasını çıkardığından emin ol.
```
:::

::: anlat Sınır
Bu ders gerçek SmolLM2-135M'de, tam log-olasılık erişimi altında gizli boyutun ve son katman altuzayının (bir dönüşüme kadar) SVD ile kurtarılmasını gösterir; ağırlık matrisinin kendisini (dönüşüm belirsizliği çözülmeden), top-$k$ logprob kısıtlı API'lerde gereken `logit_bias` tarama maliyetini ve iç katman ağırlıklarını kapsamaz. Bulgular tek model ve tek sorgu dağılımı içindir.
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
z= hW+c1 denkleminden başla. Satır merkezlemenin c1 kaymasını, sütun merkezlemenin örnek ortalamasını kaldırdığını; H yeterince çeşitli değilse rankın d değerinin altında kalabileceğini açıkla. SVD rankı son katmanın koordinatlarını tek başına benzersiz belirlemez: invertible A için HA ile A⁻¹W aynı çarpımı verir. Son katmanın altuzayını kurtarmak ile tüm transformer ağırlıklarını kurtarmak farklı iddialardır.

Önkoşul ve yol köprüsü: ai-saldiri-07/08 olasılık erişimi önkoşulunu; ai-savunma-40 çıktı yüzeyinin daraltılmasını tartışır.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| Eşik değişince model mimarisi değişti | Eşik sayısal rank tahminidir; gürültü ve örnek çeşitliliği hesaba katılır |

Dinleyiciye sor: Bu dersin kanıtı hangi gözlemi gösterir; hangi daha güçlü iddia için ek deney gerekir? Kanıtın model, ayar, veri kökeni ve hata alanlarını açarak cevabını gerekçelendir.
:::
