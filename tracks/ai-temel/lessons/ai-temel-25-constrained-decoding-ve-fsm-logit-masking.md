---
id: ai-temel-25
title: Constrained Decoding ve FSM Logit Masking · Dilbilgisi Kısıtlı Üretim
summary: Sonlu durum makinesi (FSM) geçişlerinden izinli token kümesini çıkar, sayısal kararlı logit masking uygula ve kısıtlı üretimde zorlama kütlesini GPU'da ölç.
esleme: ai-temel-03, ai-temel-14, ai-savunma-05
timeout: 60
---

::: anlat Dilbilgisi kısıtı modeli nasıl yönlendirir ve neyi gizler?
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| `constrained decoding` (Outlines, Guidance, XGrammar) her adımda bir `FSM` veya PDA üzerinden geçersiz tokenlara $-\infty$ maskesi uygulayarak %100 geçerli JSON/şema üretir | İlk üç görev: `veri/fsm_logit.json` içindeki **sentetik** geçiş tablosu ve logitler. Final: yerel **SmolLM2-135M** (49.152 token) üzerinde sıfır örnekli ve iki örnekli JSON önek ağacı (trie FSM) kısıtlı üretimi | Şemaya %100 uyan çıktının anlamsal olarak doğru veya güvenli olduğunu söyleyemez |
| Modelin ham dağılımında izinli tokenların toplam olasılığı (`izinli_kutle`) çok düşükse, `logit masking` modeli düşük olasılıklı bir yola zorlar | Maskesiz olasılık kütlesi hesabı, kararlı maskeli softmax ve `zorlama_uyarisi` bayrağı | Tek bir eşik değerinin her görev ve sıcaklıkta optimal olduğunu kanıtlamaz |

> [!NOT]
> Görevler `veri/fsm_logit.json` dosyasını okur; dosya sentetiktir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; değişiklikler taşınmaz, **kalıcılık yoktur**. Ekranda ayrı dosya görüntüleyici yoktur; içeriği görmek için `print` kullan. Gizli testler ayrıdır. Final yeni model indirmez ve GPU varsa onu kullanır.

ai-temel-03 softmax ve sıcaklık örneklemesini, ai-temel-14 ise çıktı sonrası şema doğrulamasını inceler. Bu ders şu soruyu sorar: **Üretim sonrasında bozuk JSON'u reddetmek yerine, üretim anında geçersiz tokenları `FSM` ve `logit masking` ile sıfırlarsak ne kazanırız ve neyi gözden kaçırabiliriz?**

**`constrained decoding` bir sonlu durum makinesi (`FSM`) ile sözlük (vocabulary) kesişimidir.** Düzenli bir ifade (regex) veya JSON şeması deterministik bir `FSM` olarak derlenir (Willard ve Louf 2023). Her üretim adımında model bir `durum` içindedir; `FSM` bu durumdan yalnızca belirli `token` indislerine geçişe izin verir.

**`logit masking` softmax öncesinde uygulanır.** İzinli küme $V_{\text{izinli}} \subseteq V$ dışındaki her token için logit $-\infty$ kabul edilir, yani olasılığı tam `0.0` olur. Sayısal kararlılık burada kritik bir tuzak barındırır: standart softmax'ta taşmayı önlemek için tüm vektörün maksimumu çıkarılır. Ancak yasaklı bir tokenın logiti `900.0`, izinli tek tokenın logiti `2.0` ise, tüm vektörün maksimumunu çıkarmak $\exp(2.0 - 900.0) = 0.0$ alt taşmasına (underflow) ve `0.0 / 0.0` hatasına yol açar! Doğru `logit masking`, maksimumu **yalnızca izinli indisler üzerinden** alır: $m = \max_{i \in V_{\text{izinli}}} z_i$.

**Sözdizimsel garanti, anlamsal bozulmayı gizleyebilir.** Modelin ham dağılımında izinli tokenlara düşen toplam olasılık kütlesi $\sum_{i \in V_{\text{izinli}}} p_{\text{ham}}(i)$ çok küçükse (ör. `0.001`), model aslında başka bir şey söylemeye çalışırken `FSM` tarafından zorla şemaya sokulmuştur (Tam vd. 2024). Çıktı `json.loads` testini geçer ama içerik uydurma (hallucination) veya bozulmuş akıl yürütme olabilir.

**Saldırgan ne dener?** Katı bir JSON/araç şeması zorlandığında, şemanın zorunlu tuttuğu alanları (ör. `"komut"` veya `"arguman"`) kendi enjeksiyon yükünü taşıyacak şekilde yönlendirir; şema kısıtı modelin "Bunu yapamam" gibi serbest metin redlerini maskelediği için modeli zararlı argüman üretmeye zorlayabilir.

**Savunma neden kırılır?** Yalnızca çıktının şemaya uyup uymadığına bakılırsa, `FSM` her zaman %100 başarı raporlar. Oysa `mudahale` (ham argmax ile maskeli argmax farkı) ve `izinli_kutle` izlenmezse, modelin şema baskısı altında ne kadar zorlandığı görünmez kalır.

**Görev 1'de sık tuzaklar:** Geçiş tablosunda hedef durumun `gecisler` sözlüğünde tanımlı olup olmadığını denetlememek veya aynı durumdan aynı tokena birden fazla geçiş olduğunda tekrarlı/sırasız liste döndürmek.

Kaynaklar: [Willard ve Louf 2023 - Efficient Guided Generation for LLMs (Outlines)](https://arxiv.org/abs/2307.09702), [Tam vd. 2024 - Let Me Speak Freely? A Study on the Impact of Format Restrictions on Performance of LLMs](https://arxiv.org/abs/2408.02442), [Dong vd. 2024 - XGrammar](https://arxiv.org/abs/2411.15100). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Köprü: ai-temel-03 ham logitlerden olasılık dağılımı üretir; ai-temel-14 şema doğrulamasını üretim sonrasında yapar; bu ders kısıtı doğrudan logit katmanına indirir.
:::

::: tahmin Yasaklı token çok büyük logite sahipse ne olur?
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
import math
logitler = [900.0, 2.0, 1.0]
izinli = [1, 2]
m_tum = max(logitler)
print("Tüm max ile:", [math.exp(logitler[i] - m_tum) for i in izinli])
m_izinli = max(logitler[i] for i in izinli)
print("İzinli max ile:", [round(math.exp(logitler[i] - m_izinli), 4) for i in izinli])
```
???
```cikti
Tüm max ile: [0.0, 0.0]
İzinli max ile: [1.0, 0.3679]
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: ilk satırdaki `[0.0, 0.0]` normalize edilmeye çalışılırsa hangi hata oluşur? İkinci satır neden kararlı kaldı? Sonra üç kusurlu başlangıç kodunu çalıştır ve her birinin neyi kaçırdığını önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · FSM durumundan geçerli token indislerini çıkarma
`fsm_gecerli_tokenlar(gecisler, durum)`: `gecisler` boş olmayan `dict`; her anahtar boş olmayan `str` durum adı, her değer geçiş sözlüklerinden oluşan `list`. Her geçiş sözlüğü tam olarak `"token"` (bool olmayan `int >= 0`) ve `"hedef"` (`gecisler` içinde yer alan geçerli durum `str`) alanlarını taşır. `durum`, `gecisler` içinde bulunan ve en az bir geçişe sahip olan `str` olmalıdır. Bu durumdan tek adımda çıkabilen benzersiz token indislerini küçükten büyüğe sıralı yeni bir `list` olarak döndür. Geçersiz girdide veya çıkışsız durumda `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-25")
```
```starter
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def fsm_gecerli_tokenlar(gecisler, durum):
    return [oge["token"] for oge in gecisler[durum]]

from ai_temel_veri import json_yukle
v = json_yukle("veri/fsm_logit.json")
print("Geçerli tokenlar:", fsm_gecerli_tokenlar(v["gecisler"], v["ornek_durum"]))
```
```test
def sinama1(f):
    import copy, random
    def _r(g, d):
        return sorted({x["token"] for x in g[d]})
    try:
        g = {"A": [{"token": 4, "hedef": "B"}, {"token": 1, "hedef": "A"}, {"token": 4, "hedef": "A"}], "B": [{"token": 0, "hedef": "A"}], "SON": []}
        old = copy.deepcopy(g)
        if f(g, "A") != [1, 4] or g != old: return False
        if f(g, "B") != [0]: return False
        rng = random.Random(25)
        for _ in range(20):
            adlar = [f"S{i}" for i in range(rng.randint(2, 5))]
            tablo = {}
            for a in adlar:
                tablo[a] = [{"token": rng.randint(0, 12), "hedef": rng.choice(adlar)} for _ in range(rng.randint(1, 5))]
            sec = rng.choice(adlar)
            if f(copy.deepcopy(tablo), sec) != _r(tablo, sec): return False
        for bad in (
            (None, "A"), ({}, "A"), ("A", "A"), ([("A", [])], "A"), ({"": [{"token": 1, "hedef": ""}]}, ""),
            ({"A": "yanlis"}, "A"), ({"A": [1]}, "A"), ({"A": [{"token": 1}]}, "A"),
            ({"A": [{"token": 1, "hedef": "A", "ek": 2}]}, "A"),
            ({"A": [{"token": -1, "hedef": "A"}]}, "A"),
            ({"A": [{"token": True, "hedef": "A"}]}, "A"),
            ({"A": [{"token": 1.5, "hedef": "A"}]}, "A"),
            ({"A": [{"token": 1, "hedef": "YOK"}]}, "A"),
            ({"A": [{"token": 1, "hedef": 2}]}, "A"),
            (g, "YOK"), (g, "SON"), (g, None), (g, 123)
        ):
            try:
                f(*bad)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sinama1(fsm_gecerli_tokenlar), "FSM geçiş doğrulaması, tekilleştirme, sıralama ve geçersiz girdi")
for ad, mut in [
    ("sırasız/tekrarlı", lambda g, d: [x["token"] for x in g[d]]),
    ("sabit liste", lambda g, d: [0, 1]),
    ("ters sıra", lambda g, d: list(reversed(fsm_gecerli_tokenlar(g, d))))
]:
    ok(not sinama1(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(fsm_gecerli_tokenlar, _il.import_module('ai_gercek_ai_temel_25').referans_fsm_gecerli, ({'S_AC': [{'token': 1, 'hedef': 'S_ANAHTAR'}, {'token': 5, 'hedef': 'S_KAPAT'}], 'S_ANAHTAR': [{'token': 2, 'hedef': 'S_IKI_NOKTA'}], 'S_IKI_NOKTA': [{'token': 3, 'hedef': 'S_DEGER'}, {'token': 4, 'hedef': 'S_DEGER'}], 'S_DEGER': [{'token': 5, 'hedef': 'S_KAPAT'}, {'token': 1, 'hedef': 'S_ANAHTAR'}], 'S_KAPAT': []}, 'S_IKI_NOKTA'), tohum=3041)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
def fsm_gecerli_tokenlar(gecisler, durum):
    if not isinstance(gecisler, dict) or not gecisler:
        raise ValueError("gecisler")
    for k, v in gecisler.items():
        if not isinstance(k, str) or not k or not isinstance(v, list):
            raise ValueError("durum_sema")
        for oge in v:
            if not isinstance(oge, dict) or set(oge) != {"token", "hedef"}:
                raise ValueError("gecis_sema")
            tok = oge["token"]
            if isinstance(tok, bool) or not isinstance(tok, int) or tok < 0:
                raise ValueError("token")
            if not isinstance(oge["hedef"], str) or oge["hedef"] not in gecisler:
                raise ValueError("hedef")
    if not isinstance(durum, str) or durum not in gecisler or not gecisler[durum]:
        raise ValueError("durum")
    return sorted({oge["token"] for oge in gecisler[durum]})

from ai_temel_veri import json_yukle
v = json_yukle("veri/fsm_logit.json")
print("Geçerli tokenlar:", fsm_gecerli_tokenlar(v["gecisler"], v["ornek_durum"]))
```
```hint
Önce bütün durum ve geçiş şemasını doğrula (`hedef` anahtarının `gecisler` içinde yer aldığından emin ol). Sonra `durum` içindeki token indislerini küme (`set`) ile tekilleştirip `sorted(...)` ile döndür.
```
:::

::: anlat Sayısal kararlı logit masking
`logit_maskele_olasilik(logitler, izinli_indisler)` işlevi, `izinli_indisler` dışındaki tüm konumlara `0.0` olasılık verirken, izinli konumlar arasında kararlı softmax hesaplar.

Bunun için maksimum logit $m = \max_{i \in \text{izinli}} \text{logitler}[i]$ yalnızca izinli indisler üzerinden alınmalıdır. Ardından izinli konumlarda $e^{z_i - m}$, yasaklı konumlarda `0.0` hesaplanır ve toplamlarına bölünür.

**Görev 2'de sık tuzaklar:** Maksimumu tüm `logitler` üzerinden almak (yasaklı tokenda büyük logit varken `ZeroDivisionError` üretir) veya `izinli_indisler` sınırlarını (`0 <= i < len(logitler)`) denetlememek.
:::

::: gorev 2 · Kararlı FSM logit masking ve olasılık dağılımı
`logit_maskele_olasilik(logitler, izinli_indisler)`: `logitler` boş olmayan `list`, elemanları bool olmayan sonlu sayı (`int` veya `float`); `izinli_indisler` boş olmayan `list`, elemanları bool olmayan `int` ve `0 <= idx < len(logitler)`. İzinli olmayan indislerin olasılığı tam `0.0`, izinli indislerin olasılığı ise kendi aralarında kararlı softmax (`exp(z_i - max_izinli)`) ile normalize edilmiş yeni bir `list` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-25")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def logit_maskele_olasilik(logitler, izinli_indisler):
    m = max(logitler)
    exps = [math.exp(x - m) if i in izinli_indisler else 0.0 for i, x in enumerate(logitler)]
    t = sum(exps)
    return [v / t for v in exps]

from ai_temel_veri import json_yukle
v = json_yukle("veri/fsm_logit.json")
adim = v["adimlar"][0]
izinli = [1, 5]
print(adim["ad"], logit_maskele_olasilik(adim["logitler"], izinli))
```
```test
def sinama2(f):
    import math, random
    def _r(z, iz):
        s = set(iz)
        m = max(z[i] for i in s)
        e = [math.exp(z[i] - m) if i in s else 0.0 for i in range(len(z))]
        t = sum(e)
        return [v / t for v in e]
    def _y(a, b):
        return len(a) == len(b) and all(abs(p - q) < 1e-12 for p, q in zip(a, b))
    try:
        z = [1000.0, 2.0, 2.0, -500.0]; iz = [1, 2, 1]; old = (list(z), list(iz))
        c = f(z, iz)
        if not _y(c, [0.0, 0.5, 0.5, 0.0]) or (z, iz) != old: return False
        if c[0] != 0.0 or c[3] != 0.0: return False
        if f([950.0, -20.0], [1]) != [0.0, 1.0] or not _y(f([800.0, 801.0], [0, 1]), _r([800.0, 801.0], [0, 1])): return False
        rng = random.Random(2525)
        for _ in range(25):
            n = rng.randint(2, 8)
            zv = [rng.uniform(-40, 40) for _ in range(n)]
            izv = rng.sample(range(n), rng.randint(1, n))
            if not _y(f(list(zv), list(izv)), _r(zv, izv)): return False
        for bad in (
            (None, [0]), ([], [0]), ([1.0, 2.0], []), ([1.0, 2.0], None),
            ((1.0, 2.0), [0]), ([1.0, 2.0], (0,)), ([True, 1.0], [0]),
            ([float("nan"), 1.0], [0]), ([float("inf"), 1.0], [0]),
            ([1.0, 2.0], [2]), ([1.0, 2.0], [-1]), ([1.0, 2.0], [True]),
            ([1.0, 2.0], [0.0]), ([1.0, 2.0], ["0"])
        ):
            try:
                f(*bad)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
_maske_taban = logit_maskele_olasilik([2.0, 1.0, 0.0], [2, 0])
ok(abs(_maske_taban[0] - 0.8807970779778823) < 1e-12,
   "İzinli iki logit arasındaki fark 2 olduğunda ilk olasılık sigmoid(2)")
eq(_maske_taban[1], 0.0, "Yasaklı konum sıfır kalır")
eq(logit_maskele_olasilik([1002.0, -9000.0, 1000.0], [0, 2, 0]), _maske_taban,
   "Ortak kaydırma, yasaklı logit ve izinli indis sırası dağılımı değiştirmez")
ok(sinama2(logit_maskele_olasilik), "yasaklı büyük logit kararlılığı, sıfır maske ve geçersiz girdi")
for ad, mut in [
    ("tüm max kullanımı", lambda z, iz: [math.exp(z[i] - max(z)) if i in set(iz) else 0.0 for i in range(len(z))]),
    ("maskesiz softmax", lambda z, iz: [math.exp(x - max(z)) / sum(math.exp(v - max(z)) for v in z) for x in z]),
    ("eşit dağılım", lambda z, iz: [1.0 / len(set(iz)) if i in set(iz) else 0.0 for i in range(len(z))])
]:
    ok(not sinama2(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(logit_maskele_olasilik, _il.import_module('ai_gercek_ai_temel_25').referans_logit_maskele, ([-1.0, 4.2, 0.5, -0.3, 0.1, 1.8], [1, 5]), tohum=3257)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def logit_maskele_olasilik(logitler, izinli_indisler):
    if not isinstance(logitler, list) or not logitler:
        raise ValueError("logitler")
    for x in logitler:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
            raise ValueError("sayi")
    if not isinstance(izinli_indisler, list) or not izinli_indisler:
        raise ValueError("izinli")
    n = len(logitler)
    for idx in izinli_indisler:
        if isinstance(idx, bool) or not isinstance(idx, int) or not 0 <= idx < n:
            raise ValueError("indis")
    izinli = set(izinli_indisler)
    m = max(logitler[i] for i in izinli)
    exps = [math.exp(logitler[i] - m) if i in izinli else 0.0 for i in range(n)]
    toplam = sum(exps)
    return [v / toplam for v in exps]

if __name__ == "__main__":
    from ai_temel_veri import json_yukle
    v = json_yukle("veri/fsm_logit.json")
    for adim in v["adimlar"]:
        iz = [oge["token"] for oge in v["gecisler"][adim["durum"]]]
        print(adim["ad"], [round(p, 4) for p in logit_maskele_olasilik(adim["logitler"], iz)])
```
```hint
`izinli = set(izinli_indisler)` kümesini oluştur ve `m = max(logitler[i] for i in izinli)` değerini yalnız bu kümeden hesapla.
```
:::

::: anlat Zorlama kütlesi ve müdahale tanısı
Bir üretim adımında `FSM` maskesi uygulandığında şu iki soruyu sormalıyız:
1. **Müdahale (`mudahale`):** Maskesiz (ham) logitlerin en yüksek değerli tokenı (`ham_secilen`) ile maskeli olasılıkların seçtiği token (`secilen_token`) farklı mı? Eşitlik durumunda her ikisi de en küçük indisi seçer.
2. **Zorlama uyarısı (`zorlama_uyarisi`):** Modelin **ham** (maskesiz) softmax dağılımında izinli tokenların toplam olasılığı (`izinli_kutle`), verilen `esik` değerinin kesin altında mı (`izinli_kutle < esik`)?

Eğer `izinli_kutle` çok küçükse, maskeli dağılımda `secilen_olasilik` `1.0` görünse bile model aslında şema tarafından düşük olasılıklı bir yola zorlanmıştır.

**Görev 3'te sık tuzaklar:** `izinli_kutle` değerini maskeli olasılıklardan toplamak (her zaman `1.0` çıkar ve zorlamayı gizler!) veya `esik` sınırlarını (`0 < esik <= 1`) kontrol etmemek.
:::

::: gorev 3 · Kısıtlı adım ve zorlama raporu
`kisitli_adim_raporu(logitler, izinli_indisler, esik)`: `logitler` ve `izinli_indisler` Görev 2 kurallarına uyar; `esik` bool olmayan sonlu sayı ve `0 < esik <= 1`. Ham (maskesiz) kararlı softmax'ta izinli kümenin toplam olasılığını (`izinli_kutle`) ve maskeli dağılımda seçilen tokenı (`secilen_token`, eşitlikte küçük indis) hesapla. `{"secilen_token": int, "secilen_olasilik": float, "izinli_kutle": float, "mudahale": bool(secilen_token != ham_secilen), "zorlama_uyarisi": bool(izinli_kutle < esik)}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-25")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def kisitli_adim_raporu(logitler, izinli_indisler, esik):
    izinli = set(izinli_indisler)
    m = max(logitler[i] for i in izinli)
    exps = [math.exp(logitler[i] - m) if i in izinli else 0.0 for i in range(len(logitler))]
    t = sum(exps)
    p_mask = [v / t for v in exps]
    secilen = max(range(len(p_mask)), key=lambda i: p_mask[i])
    kutle = sum(p_mask[i] for i in izinli)
    return {
        "secilen_token": secilen,
        "secilen_olasilik": p_mask[secilen],
        "izinli_kutle": kutle,
        "mudahale": False,
        "zorlama_uyarisi": kutle < esik,
    }

from ai_temel_veri import json_yukle
v = json_yukle("veri/fsm_logit.json")
for adim in v["adimlar"]:
    iz = [oge["token"] for oge in v["gecisler"][adim["durum"]]]
    print(adim["ad"], kisitli_adim_raporu(adim["logitler"], iz, v["esik"]))
```
```test
def sinama3(f):
    import math, random
    def _r(z, iz, e):
        s = set(iz)
        m = max(z[i] for i in s)
        em = [math.exp(z[i] - m) if i in s else 0.0 for i in range(len(z))]
        tm = sum(em)
        pm = [v / tm for v in em]
        mh = max(z)
        eh = [math.exp(x - mh) for x in z]
        th = sum(eh)
        ph = [v / th for v in eh]
        kutle = sum(ph[i] for i in s)
        sec = max(range(len(pm)), key=lambda i: pm[i])
        hsec = max(range(len(z)), key=lambda i: z[i])
        return {"secilen_token": sec, "secilen_olasilik": pm[sec], "izinli_kutle": kutle, "mudahale": sec != hsec, "zorlama_uyarisi": kutle < e}
    def _y(a, b):
        return set(a) == set(b) and a["secilen_token"] == b["secilen_token"] and a["mudahale"] is b["mudahale"] and a["zorlama_uyarisi"] is b["zorlama_uyarisi"] and abs(a["secilen_olasilik"] - b["secilen_olasilik"]) < 1e-12 and abs(a["izinli_kutle"] - b["izinli_kutle"]) < 1e-12
    try:
        z = [10.0, 0.0, 0.0]; iz = [1, 2]; old = (list(z), list(iz))
        r1 = f(z, iz, 0.1)
        if not _y(r1, _r(z, iz, 0.1)) or (z, iz) != old: return False
        if not r1["mudahale"] or not r1["zorlama_uyarisi"] or r1["secilen_token"] != 1: return False
        r2 = f([5.0, 1.0, 0.0], [0, 1], 0.5)
        if r2["mudahale"] is not False or r2["zorlama_uyarisi"] is not False or r2["secilen_token"] != 0: return False
        r3 = f([0.0, 0.0], [0], 0.5)
        if r3["zorlama_uyarisi"] is not False: return False
        r4 = f([0.0, 0.0], [0], 0.6)
        if r4["zorlama_uyarisi"] is not True: return False
        r5 = f([0.0, 0.0], [0], 1)
        if r5["zorlama_uyarisi"] is not True or not _y(r5, _r([0.0, 0.0], [0], 1)): return False
        if not _y(f([800.0, 801.0], [0, 1], 0.5), _r([800.0, 801.0], [0, 1], 0.5)): return False
        rng = random.Random(2503)
        for _ in range(25):
            n = rng.randint(2, 7)
            zv = [rng.uniform(-20, 20) for _ in range(n)]
            izv = rng.sample(range(n), rng.randint(1, n))
            ev = rng.uniform(0.05, 0.95)
            if not _y(f(list(zv), list(izv), ev), _r(zv, izv, ev)): return False
        for bad in (
            (None, [0], 0.5), ([], [0], 0.5), ([1.0], [], 0.5), ([1.0], [1], 0.5),
            ([1.0, 2.0], [0], 0.0), ([1.0, 2.0], [0], -0.1), ([1.0, 2.0], [0], 1.1),
            ([1.0, 2.0], [0], True), ([1.0, 2.0], [0], float("nan")), ([1.0, 2.0], [0], "0.5"),
            ((1.0, 2.0), [0], 0.5), ([True, 1.0], [0], 0.5), (["a", 1.0], [0], 0.5), ([float("inf"), 1.0], [0], 0.5),
            ([1.0, 2.0], (0,), 0.5), ([1.0, 2.0], [True], 0.5), ([1.0, 2.0], [0.0], 0.5), ([1.0, 2.0], [-1], 0.5)
        ):
            try:
                f(*bad)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sinama3(kisitli_adim_raporu), "ham izinli kütle, müdahale, zorlama uyarısı ve geçersiz girdi")
for ad, mut in [
    ("kütle hep 1", lambda z, iz, e: dict(kisitli_adim_raporu(z, iz, e), izinli_kutle=1.0, zorlama_uyarisi=False)),
    ("müdahale hep yanlış", lambda z, iz, e: dict(kisitli_adim_raporu(z, iz, e), mudahale=False)),
    ("uyarı ters", lambda z, iz, e: dict(kisitli_adim_raporu(z, iz, e), zorlama_uyarisi=not kisitli_adim_raporu(z, iz, e)["zorlama_uyarisi"]))
]:
    ok(not sinama3(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(kisitli_adim_raporu, _il.import_module('ai_gercek_ai_temel_25').referans_kisitli_rapor, ([-1.0, 4.2, 0.5, -0.3, 0.1, 1.8], [1, 5], 0.15), tohum=2957)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def kisitli_adim_raporu(logitler, izinli_indisler, esik):
    if not isinstance(logitler, list) or not logitler:
        raise ValueError("logitler")
    for x in logitler:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
            raise ValueError("sayi")
    if not isinstance(izinli_indisler, list) or not izinli_indisler:
        raise ValueError("izinli")
    n = len(logitler)
    for idx in izinli_indisler:
        if isinstance(idx, bool) or not isinstance(idx, int) or not 0 <= idx < n:
            raise ValueError("indis")
    if isinstance(esik, bool) or not isinstance(esik, (int, float)) or not math.isfinite(esik) or not 0 < esik <= 1:
        raise ValueError("esik")
    izinli = set(izinli_indisler)
    m_iz = max(logitler[i] for i in izinli)
    exp_iz = [math.exp(logitler[i] - m_iz) if i in izinli else 0.0 for i in range(n)]
    top_iz = sum(exp_iz)
    p_mask = [v / top_iz for v in exp_iz]
    m_ham = max(logitler)
    exp_ham = [math.exp(x - m_ham) for x in logitler]
    top_ham = sum(exp_ham)
    p_ham = [v / top_ham for v in exp_ham]
    izinli_kutle = sum(p_ham[i] for i in izinli)
    secilen = max(range(n), key=lambda i: p_mask[i])
    ham_secilen = max(range(n), key=lambda i: logitler[i])
    return {
        "secilen_token": secilen,
        "secilen_olasilik": p_mask[secilen],
        "izinli_kutle": izinli_kutle,
        "mudahale": bool(secilen != ham_secilen),
        "zorlama_uyarisi": bool(izinli_kutle < esik),
    }

from ai_temel_veri import json_yukle
v = json_yukle("veri/fsm_logit.json")
for adim in v["adimlar"]:
    iz = [oge["token"] for oge in v["gecisler"][adim["durum"]]]
    print(adim["ad"], kisitli_adim_raporu(adim["logitler"], iz, v["esik"]))
```
```hint
`izinli_kutle` için ham (maskesiz) softmax olasılıklarını hesaplayıp yalnızca `izinli` kümesindeki indislerin olasılıklarını topla.
```
:::

::: anlat Hata vitrini · çalışmış yanlış rapor
Yazar, kusurlu başlangıç kodlarını görünür sentetik veriyle gerçekten çalıştırdı ve sonucu `outputs/yeni-ai-temel-25/gorunur-run-1.json` dosyasına kaydetti. `yasak_baskin_adim` örneği için kusurlu kod `izinli_kutle=1.0`, `mudahale=False`, `zorlama_uyarisi=False` verir. Doğru kod ise `izinli_kutle=0.000991`, `mudahale=True`, `zorlama_uyarisi=True` verir. Ayrıca `asiri_logit_adimi` örneğinde kusurlu kod `ZeroDivisionError` ile çökerken doğru kod `[0.0, 0.0, 1.0, 0.0, 0.0, 0.0]` döndürür.

Bu kaydedilmiş bir hesaplama çıktısıdır, model yanıtı değildir ve rapor sentetiktir. Kusurlu çıktıyı görüp "Model şemaya %100 güvenle uydu, hiç zorlanmadı" diyen biri neyi kaçırır? Hangi alan onu uyarabilirdi? Kendi cümlenle açıkla. Gerçek finaldeki ölçüm ayrıca üretilir; bu sayılar onun yerine konmaz.
:::

::: anlat Gerçek deney: SmolLM2'yi gerçek bir JSON şemasına zorlamak
Final, yerel önbellekteki gerçek **SmolLM2-135M** modelini (indirme yok) kullanır. Şema `{"risk": "low" | "medium" | "high"}` değerlerinden birini zorunlu kılar. Geçerli üç çıktının **modelin tokenizer'ındaki kanonik token dizileri** bir önek ağacına (trie) dökülür; bu ağaç gerçek token kimlikleriyle bir FSM'dir (Outlines gibi kütüphanelerin yaptığı da budur). 6 güvenlik alarmı iki istem kipinde işlenir: **sıfır örnekli** (yalnız alarm ve `Answer:`) ve **iki örnekli** (önce iki çözülmüş JSON örneği). Her alarmda iki üretim yapılır:
- **Serbest açgözlü üretim:** çıktı şemaya uyuyor mu?
- **Kısıtlı üretim:** her adımda gerçek 49.152 boyutlu logitler senin `fsm_gecerli_tokenlar`, `logit_maskele_olasilik` ve `kisitli_adim_raporu` işlevlerinden geçer. Her adımda modelin izinli tokenlara **kendi** verdiği olasılık (`izinli_kutle`) ve maskenin kararı değiştirip değiştirmediği (`mudahale`) kaydedilir.

İki kip arasındaki fark, kısıtlı çözmenin asıl ölçüsüdür. Model şemayı zaten izlemeye hazırsa (iki örnekli istem) maske neredeyse hiç müdahale etmez. Hazır değilse (sıfır örnekli istem) maske her adımda modelin dağılımının çok küçük bir kısmını seçmeye zorlar: çıktı sözdizimsel olarak geçerlidir ama model "kendi isteğiyle" söylemiş değildir. İki durumda da şema **anlamı** düzeltmez; küçük model gece 3'teki yönetici girişine "low" diyebilir.

**Token sınırı tuzağı.** Şemanın ilk tokenı ` {"` boşlukla başlar, çünkü SmolLM2'nin BPE'sinde boşluk sonraki tokenın parçasıdır (`Ġ{"`). Yazar ilk denemede istemi `Answer: ` ile (sonda boşlukla) bitirip şemayı `{"` ile başlatmıştı; iki örnekli istemde bile ilk adım kütlesi 0.985'ten 0.002'ye düştü. Kanonik olmayan bir sınır, modeli eğitimde neredeyse hiç görmediği bir token dizisine iter; token iyileştirme (`token healing`) bu yüzden vardır.

Kabul: üç işlevin bütün gerçek adımlarda bağımsız referansla aynı sonucu vermesi, yasaklı tokenların olasılığının tam `0.0` ve izinli olasılıkların toplamının `1.0` olması, kısıtlı çıktıların %100 geçerli olması, sıfır örnekli serbest üretimin kısıtlıdan daha az geçerli olması ve iki örnekli istemde ilk adım kütlesinin sıfır örneklidekinden en az 100 kat yüksek olması.

**Kanıt dosyasını oku:** `sifir_ornek` ve `iki_ornek` özetlerini, `kayitlar` içindeki `serbest`, `kisitli`, `ilk_adim_kutle` ve `mudahale_sayisi` alanlarını karşılaştır. Soru 1: Sıfır örnekli kipte kısıtlı çıktı %100 geçerli olduğu hâlde neden "modelin cevabı" sayılmamalı? Soru 2: İki kipte de doğruluk aynı kaldı; şema ve maske hangi sorunu çözer, hangisini çözmez? Soru 3: `zorlama_uyarisi` eşiği bir üretim sisteminde nasıl kullanılabilir (ör. düşük kütlede cevabı reddetmek ya da insana yönlendirmek)? Cevabını tezgâhta yorum olarak yaz; otomatik test bu serbest açıklamayı puanlamaz.
:::

::: gorev Gerçek deney · SmolLM2-135M logitlerinde FSM kısıtlı üretim ve zorlama analizi
Önceki üç görevin `fsm_gecerli_tokenlar`, `logit_maskele_olasilik` ve `kisitli_adim_raporu` işlevlerini birleştir. Çalıştır gerçek tabloyu gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 180
```
```starter
import ai_lab
import math
def fsm_gecerli_tokenlar(gecisler, durum):
    return [oge["token"] for oge in gecisler[durum]]
def logit_maskele_olasilik(logitler, izinli_indisler):
    m = max(logitler)
    exps = [math.exp(x - m) if i in izinli_indisler else 0.0 for i, x in enumerate(logitler)]
    t = sum(exps)
    return [v / t for v in exps]
def kisitli_adim_raporu(logitler, izinli_indisler, esik):
    p_mask = logit_maskele_olasilik(logitler, izinli_indisler)
    secilen = max(range(len(p_mask)), key=lambda i: p_mask[i])
    return {"secilen_token": secilen, "secilen_olasilik": p_mask[secilen], "izinli_kutle": 1.0, "mudahale": False, "zorlama_uyarisi": False}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_25 as D
    D.goster(fsm_gecerli_tokenlar, logit_maskele_olasilik, kisitli_adim_raporu)
```
```test
import ai_lab, math
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('referans_fsm_gecerli', 'referans_logit_maskele', 'referans_kisitli_rapor', 'kanit_yaz', '_yakin'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
fsm_gecerli_tokenlar = need("fsm_gecerli_tokenlar")
logit_maskele_olasilik = need("logit_maskele_olasilik")
kisitli_adim_raporu = need("kisitli_adim_raporu")
def sinama1(f):
    import copy, random
    def _r(g, d): return sorted({x["token"] for x in g[d]})
    try:
        g = {"A": [{"token": 4, "hedef": "B"}, {"token": 1, "hedef": "A"}, {"token": 4, "hedef": "A"}], "B": [{"token": 0, "hedef": "A"}], "SON": []}
        old = copy.deepcopy(g)
        if f(g, "A") != [1, 4] or g != old: return False
        if f(g, "B") != [0]: return False
        rng = random.Random(25)
        for _ in range(20):
            adlar = [f"S{i}" for i in range(rng.randint(2, 5))]
            tablo = {a: [{"token": rng.randint(0, 12), "hedef": rng.choice(adlar)} for _ in range(rng.randint(1, 5))] for a in adlar}
            sec = rng.choice(adlar)
            if f(copy.deepcopy(tablo), sec) != _r(tablo, sec): return False
        for bad in ((None, "A"), ({}, "A"), ({"": [{"token": 1, "hedef": ""}]}, ""), ({"A": "yanlis"}, "A"), ({"A": [1]}, "A"), ({"A": [{"token": 1}]}, "A"), ({"A": [{"token": 1, "hedef": "A", "ek": 2}]}, "A"), ({"A": [{"token": -1, "hedef": "A"}]}, "A"), ({"A": [{"token": True, "hedef": "A"}]}, "A"), ({"A": [{"token": 1.5, "hedef": "A"}]}, "A"), ({"A": [{"token": 1, "hedef": "YOK"}]}, "A"), ({"A": [{"token": 1, "hedef": 2}]}, "A"), (g, "YOK"), (g, "SON"), (g, None), (g, 123)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama1(fsm_gecerli_tokenlar), "FSM geçiş doğrulaması, tekilleştirme, sıralama ve geçersiz girdi")
for ad, mut in [("sırasız/tekrarlı", lambda g, d: [x["token"] for x in g[d]]), ("sabit liste", lambda g, d: [0, 1]), ("ters sıra", lambda g, d: list(reversed(fsm_gecerli_tokenlar(g, d))))]:
    kontrol(not sinama1(mut), "mutant reddedildi: " + ad)
def sinama2(f):
    import math, random
    def _r(z, iz):
        s = set(iz); m = max(z[i] for i in s)
        e = [math.exp(z[i] - m) if i in s else 0.0 for i in range(len(z))]; t = sum(e)
        return [v / t for v in e]
    def _y(a, b): return len(a) == len(b) and all(abs(p - q) < 1e-12 for p, q in zip(a, b))
    try:
        z = [1000.0, 2.0, 2.0, -500.0]; iz = [1, 2, 1]; old = (list(z), list(iz))
        c = f(z, iz)
        if not _y(c, [0.0, 0.5, 0.5, 0.0]) or (z, iz) != old: return False
        if f([950.0, -20.0], [1]) != [0.0, 1.0] or not _y(f([800.0, 801.0], [0, 1]), _r([800.0, 801.0], [0, 1])): return False
        rng = random.Random(2525)
        for _ in range(25):
            n = rng.randint(2, 8); zv = [rng.uniform(-40, 40) for _ in range(n)]; izv = rng.sample(range(n), rng.randint(1, n))
            if not _y(f(list(zv), list(izv)), _r(zv, izv)): return False
        for bad in ((None, [0]), ([], [0]), ([1.0, 2.0], []), ([1.0, 2.0], None), ((1.0, 2.0), [0]), ([1.0, 2.0], (0,)), ([True, 1.0], [0]), ([float("nan"), 1.0], [0]), ([float("inf"), 1.0], [0]), ([1.0, 2.0], [2]), ([1.0, 2.0], [-1]), ([1.0, 2.0], [True]), ([1.0, 2.0], [0.0]), ([1.0, 2.0], ["0"])):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama2(logit_maskele_olasilik), "yasaklı büyük logit kararlılığı, sıfır maske ve geçersiz girdi")
for ad, mut in [("tüm max kullanımı", lambda z, iz: [math.exp(z[i] - max(z)) if i in set(iz) else 0.0 for i in range(len(z))]), ("maskesiz softmax", lambda z, iz: [math.exp(x - max(z)) / sum(math.exp(v - max(z)) for v in z) for x in z]), ("eşit dağılım", lambda z, iz: [1.0 / len(set(iz)) if i in set(iz) else 0.0 for i in range(len(z))])]:
    kontrol(not sinama2(mut), "mutant reddedildi: " + ad)
def sinama3(f):
    import math, random
    def _r(z, iz, e):
        s = set(iz); m = max(z[i] for i in s); em = [math.exp(z[i] - m) if i in s else 0.0 for i in range(len(z))]; tm = sum(em); pm = [v / tm for v in em]
        mh = max(z); eh = [math.exp(x - mh) for x in z]; th = sum(eh); ph = [v / th for v in eh]
        kutle = sum(ph[i] for i in s); sec = max(range(len(pm)), key=lambda i: pm[i]); hsec = max(range(len(z)), key=lambda i: z[i])
        return {"secilen_token": sec, "secilen_olasilik": pm[sec], "izinli_kutle": kutle, "mudahale": sec != hsec, "zorlama_uyarisi": kutle < e}
    def _y(a, b): return set(a) == set(b) and a["secilen_token"] == b["secilen_token"] and a["mudahale"] is b["mudahale"] and a["zorlama_uyarisi"] is b["zorlama_uyarisi"] and abs(a["secilen_olasilik"] - b["secilen_olasilik"]) < 1e-12 and abs(a["izinli_kutle"] - b["izinli_kutle"]) < 1e-12
    try:
        z = [10.0, 0.0, 0.0]; iz = [1, 2]; old = (list(z), list(iz))
        r1 = f(z, iz, 0.1)
        if not _y(r1, _r(z, iz, 0.1)) or (z, iz) != old: return False
        if not r1["mudahale"] or not r1["zorlama_uyarisi"] or r1["secilen_token"] != 1: return False
        r2 = f([5.0, 1.0, 0.0], [0, 1], 0.5)
        if r2["mudahale"] is not False or r2["zorlama_uyarisi"] is not False or r2["secilen_token"] != 0: return False
        if f([0.0, 0.0], [0], 0.5)["zorlama_uyarisi"] is not False or f([0.0, 0.0], [0], 0.6)["zorlama_uyarisi"] is not True or not _y(f([800.0, 801.0], [0, 1], 0.5), _r([800.0, 801.0], [0, 1], 0.5)): return False
        rng = random.Random(2503)
        for _ in range(25):
            n = rng.randint(2, 7); zv = [rng.uniform(-20, 20) for _ in range(n)]; izv = rng.sample(range(n), rng.randint(1, n)); ev = rng.uniform(0.05, 0.95)
            if not _y(f(list(zv), list(izv), ev), _r(zv, izv, ev)): return False
        for bad in ((None, [0], 0.5), ([], [0], 0.5), ([1.0], [], 0.5), ([1.0], [1], 0.5), ([1.0, 2.0], [0], 0.0), ([1.0, 2.0], [0], -0.1), ([1.0, 2.0], [0], 1.1), ([1.0, 2.0], [0], True), ([1.0, 2.0], [0], float("nan")), ([1.0, 2.0], [0], "0.5")):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama3(kisitli_adim_raporu), "ham izinli kütle, müdahale, zorlama uyarısı ve geçersiz girdi")
for ad, mut in [("kütle hep 1", lambda z, iz, e: dict(kisitli_adim_raporu(z, iz, e), izinli_kutle=1.0, zorlama_uyarisi=False)), ("müdahale hep yanlış", lambda z, iz, e: dict(kisitli_adim_raporu(z, iz, e), mudahale=False)), ("uyarı ters", lambda z, iz, e: dict(kisitli_adim_raporu(z, iz, e), zorlama_uyarisi=not kisitli_adim_raporu(z, iz, e)["zorlama_uyarisi"]))]:
    kontrol(not sinama3(mut), "mutant reddedildi: " + ad)
# farksal tarama (final)
import importlib as _il
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_R = _il.import_module('sandbox.ai_gercek_ai_temel_25')
for _ad, _ref, _taban, _toh in (
    ('fsm_gecerli_tokenlar', 'referans_fsm_gecerli', ({'S_AC': [{'token': 1, 'hedef': 'S_ANAHTAR'}, {'token': 5, 'hedef': 'S_KAPAT'}], 'S_ANAHTAR': [{'token': 2, 'hedef': 'S_IKI_NOKTA'}], 'S_IKI_NOKTA': [{'token': 3, 'hedef': 'S_DEGER'}, {'token': 4, 'hedef': 'S_DEGER'}], 'S_DEGER': [{'token': 5, 'hedef': 'S_KAPAT'}, {'token': 1, 'hedef': 'S_ANAHTAR'}], 'S_KAPAT': []}, 'S_IKI_NOKTA'), 3563),
    ('logit_maskele_olasilik', 'referans_logit_maskele', ([-1.0, 4.2, 0.5, -0.3, 0.1, 1.8], [1, 5]), 3779),
    ('kisitli_adim_raporu', 'referans_kisitli_rapor', ([-1.0, 4.2, 0.5, -0.3, 0.1, 1.8], [1, 5], 0.15), 3479),
):
    _t, _g = _ff(need(_ad), getattr(_R, _ref), _taban, tohum=_toh)
    kontrol(_t, "farksal tarama (" + _ad + "): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
if not all(checks): stop()
from sandbox import ai_gercek_ai_temel_25 as D
try: r = D.deney(fsm_gecerli_tokenlar, logit_maskele_olasilik, kisitli_adim_raporu)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r["fsm_ayni"], "gerçek token kimlikli FSM'de geçerli token kümeleri bağımsız referansla aynı")
kontrol(r["maske_ayni"], "gerçek SmolLM2 logitlerinde (49.152 token) maskeli olasılıklar referansla aynı")
kontrol(r["rapor_ayni"], "gerçek üretim adımlarında kısıtlı adım raporu referansla aynı")
kontrol(r["yasak_olasilik_sifir"], "yasaklı tüm tokenların olasılığı tam 0.0")
kontrol(r["olasilik_toplami_bir"], "maskeli olasılık dağılımlarının toplamı 1.0")
kontrol(r["sifir_ornek"]["kisitli_gecerlilik"] == 1.0 and r["iki_ornek"]["kisitli_gecerlilik"] == 1.0, "kısıtlı çıktıların %100'ü şemaya uyuyor")
kontrol(r["sifir_ornek"]["serbest_gecerlilik"] < r["sifir_ornek"]["kisitli_gecerlilik"], "sıfır örnekli istemde serbest üretim kısıtlıdan daha az geçerli")
kontrol(r["iki_ornek"]["ilk_adim_kutle"] >= 100 * max(r["sifir_ornek"]["ilk_adim_kutle"], 1e-12), "iki örnekli istemde modelin şemaya kendi kütlesi sıfır örneklinin en az 100 katı")
ai_lab.kanit_yaz("ai-temel-25-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-temel-25", "deney": r})
```
```solution
import ai_lab
import math
def fsm_gecerli_tokenlar(gecisler, durum):
    if not isinstance(gecisler, dict) or not gecisler:
        raise ValueError("gecisler")
    for k, v in gecisler.items():
        if not isinstance(k, str) or not k or not isinstance(v, list):
            raise ValueError("durum_sema")
        for oge in v:
            if not isinstance(oge, dict) or set(oge) != {"token", "hedef"}:
                raise ValueError("gecis_sema")
            tok = oge["token"]
            if isinstance(tok, bool) or not isinstance(tok, int) or tok < 0:
                raise ValueError("token")
            if not isinstance(oge["hedef"], str) or oge["hedef"] not in gecisler:
                raise ValueError("hedef")
    if not isinstance(durum, str) or durum not in gecisler or not gecisler[durum]:
        raise ValueError("durum")
    return sorted({oge["token"] for oge in gecisler[durum]})
def logit_maskele_olasilik(logitler, izinli_indisler):
    if not isinstance(logitler, list) or not logitler:
        raise ValueError("logitler")
    for x in logitler:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
            raise ValueError("sayi")
    if not isinstance(izinli_indisler, list) or not izinli_indisler:
        raise ValueError("izinli")
    n = len(logitler)
    for idx in izinli_indisler:
        if isinstance(idx, bool) or not isinstance(idx, int) or not 0 <= idx < n:
            raise ValueError("indis")
    izinli = set(izinli_indisler)
    m = max(logitler[i] for i in izinli)
    exps = [math.exp(logitler[i] - m) if i in izinli else 0.0 for i in range(n)]
    toplam = sum(exps)
    return [v / toplam for v in exps]
def kisitli_adim_raporu(logitler, izinli_indisler, esik):
    p_mask = logit_maskele_olasilik(logitler, izinli_indisler)
    if isinstance(esik, bool) or not isinstance(esik, (int, float)) or not math.isfinite(esik) or not 0 < esik <= 1:
        raise ValueError("esik")
    n = len(logitler)
    izinli = set(izinli_indisler)
    m_ham = max(logitler)
    exp_ham = [math.exp(x - m_ham) for x in logitler]
    top_ham = sum(exp_ham)
    p_ham = [v / top_ham for v in exp_ham]
    izinli_kutle = sum(p_ham[i] for i in izinli)
    secilen = max(range(n), key=lambda i: p_mask[i])
    ham_secilen = max(range(n), key=lambda i: logitler[i])
    return {
        "secilen_token": secilen,
        "secilen_olasilik": p_mask[secilen],
        "izinli_kutle": izinli_kutle,
        "mudahale": bool(secilen != ham_secilen),
        "zorlama_uyarisi": bool(izinli_kutle < esik),
    }
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_25 as D
    D.goster(fsm_gecerli_tokenlar, logit_maskele_olasilik, kisitli_adim_raporu)
```
```hint
Üç işlevi birleştir. `logit_maskele_olasilik` işlevini `kisitli_adim_raporu` içinde doğrudan çağırabilirsin.
```
:::

::: anlat Sınır
Bu ders gerçek SmolLM2-135M'de, kanonik token dizilerinden kurulan küçük bir önek ağacı FSM'siyle `logit masking` uygular; zorlama kütlesini ve token sınırı tuzağını ölçer. Düzenli ifade/JSON Schema'dan otomatik FSM derlemeyi, token iyileştirme (token healing) uygulamasını, bağlamdan bağımsız gramerlerin (CFG/PDA) yığın maliyetini ve büyük şemalarda maskeleme gecikmesini kapsamaz; 6 alarm ve tek model genelleme için yetmez.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Üretim sonrası ayrıştırma yerine `FSM logit masking` (30 sn).** "Modelin bozuk JSON üretmesini bekleyip `json.loads` hatası almak yerine, her adımda sonlu durum makinesinin (`FSM`) izin vermediği tokenların logitini $-\infty$ yaparak olasılık kütlesini yalnızca geçerli geçişlere yeniden normalize ederiz."
2. **Biçimsel geçerlilik vs anlamsal doğruluk (`zorlama kütlesi`) (35 sn).** "SmolLM2 sıfır örnekli istemde geçerli tokenlara çok düşük kütle ayırırken maske yine de geçerli JSON çıkarır; yani düşük izinli kütle (`yüksek zorlama`) modelin şemaya uyduğunu ama içerikte zorlandığını haber verir."
3. **Token sınırı tuzağı (30 sn).** "Alt-kelime (`BPE`) sınırları gramer sınırlarıyla her zaman çakışmaz; çok karakterli tek bir token ara durumları atlayabileceği için önek ağacı (`trie`) tüm kanonik token dizilerini kapsamalıdır."
4. **Soru (25 sn).** "Yapılandırılmış çıktı (`structured output`) şema hatasını sıfırladığı hâlde neden araç çağrısı güvenliğinde parametre doğrulamasının yerini tutmaz?"
:::
