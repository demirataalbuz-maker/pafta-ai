---
id: ai-saldiri-59
title: Speculative Decoding Yan Kanalı · Kabul Oranı Sızıntısı ve Sabit Hız Dolgusu
summary: Speculative decoding çıkarımında paket başına kabul edilen token sayısını ve üretim hızını ölç; paylaşımlı taslak/önbellek kabul oranından gizli öneki kurtar ve sabit boyutlu paket dolgusunun boyut sızıntısına etkisini ve kalan paket sayısı izini GPU'da ölç.
esleme: ai-saldiri-38, ai-saldiri-07, ai-savunma-31
timeout: 60
---

::: anlat Hızlandırma mekanizması gizli bağlamı nasıl sızdırır?
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| `speculative decoding` (taslak model + hedef model doğrulaması) her ileri geçişte $1$ ile $\gamma+1$ arasında değişen sayıda token üretir; paket boyutu ve zamanlama izi (`side-channel`) tahmin edilen metnin hedef dağılımla veya önbellekle ne kadar örtüştüğünü sızdırır | İlk üç görev: `veri/spec_sidechannel.json` içindeki **sentetik** paket token sayıları ve kabul oranları. Final: GPU'da $\gamma=5$ taslak adımlı doğrulama döngüsünde gizli önekin kurtarılması | WAN üzerindeki TCP/TLS parçalama ve yönlendirici kuyruk gecikmesi (jitter) gürültüsünün tam ağ izini tek başına temsil etmez |
| Sabit boyutlu paket dolgusu her paketin boyutunu eşitleyerek boyut gözlemini gizler; tek başına paket sayısını veya zamanlamayı eşitlemez | Paket kabul hızı, normalize önek kazanç puanı ve sabit boyutlu dolgu ek yükü (`overhead`) | Sabit dolgunun GPU içi güç/elektromanyetik yan kanallarını da kapattığını kanıtlamaz |

> [!NOT]
> Görevler `veri/spec_sidechannel.json` dosyasını okur; dosya sentetiktir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; değişiklikler taşınmaz, **kalıcılık yoktur**. Ekranda ayrı dosya görüntüleyici yoktur; içeriği görmek için `print` kullan. Gizli testler ayrıdır. Final yeni model indirmez ve GPU varsa onu kullanır.

Büyük dil modellerinde bellek bant genişliği darboğazını aşmak için **speculative decoding** (Leviathan vd. 2023) yaygın kullanılır: küçük bir taslak model (`draft model`) veya paylaşımlı önek arama tablosu (`prompt lookup` / `ngram cache`) $\gamma$ adet aday token önerir; büyük hedef model tek bir ileri geçişte bu $\gamma$ tokeni paralel doğrular.

**Yan kanal (`side-channel`) nasıl oluşur?** Eğer taslak modelin önerdiği ilk $k$ token hedef modelle uyuşursa, sunucu tek bir SSE/WebSocket paketinde $k+1$ token birden gönderir ($1 \le \text{paket\_token} \le \gamma+1$). Paylaşımlı bir çıkarım sunucusunda veya şifreli akışın paket boyutlarını izleyen bir saldırgan:
1. Her pakette kaç token üretildiğini ve paketler arası süreyi (`sure_ms`) gözlemler.
2. Kurbanın gizli sistem istemi veya önbellekteki tıbbi/finansal kaydıyla örtüşen aday önekleri dener; kabul oranı (`acceptance rate`) sıçrayan aday gizli metni ele verir.

**Saldırgan ne dener?** Aday önekler kümesi oluşturup her birinin `spekulatif_oran` veya kabul oranını taban oranla (`taban_oran`) karşılaştırır:
$$\text{kazanç}(c) = \max\left(0, \frac{r_c - r_{\text{taban}}}{1 - r_{\text{taban}}}\right)$$

**Savunma neden kırılır?** Yalnız TLS şifrelemesi paketlerin **ne zaman** ve **kaç bayt** olarak çıktığını gizlemez. Savunma, her doğrulama adımında üretilen gerçek token sayısını sabit bir çerçeve boyutuna (`hedef_sabit_boyut`) tamamlayan sabit hızlı dolgu (`constant-rate padding`) veya paket tamponlama uygulamaktır.

**Görev 1'de sık tuzaklar:** `saniyede_token` hesaplarken süreyi milisaniyeden saniyeye (`sum(sure_ms_listesi) / 1000.0`) çevirmeyi unutmak hızı 1000 kat küçük çıkarır.

Kaynaklar: [Leviathan vd. 2023 - Fast Inference from Transformers via Speculative Decoding](https://arxiv.org/abs/2211.17192), [Wei vd. - When Speculation Spills Secrets: Side Channels via Speculative Decoding In LLMs (ilk sürüm 2024)](https://arxiv.org/abs/2411.01076). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Köprü: ai-saldiri-38 önbellek zamanlama yan kanalını inceler; bu ders doğrudan `speculative decoding` kabul oranı ve paket çoklama sızıntısını modeller.
:::

::: tahmin Milisaniye paketlerinden saniyede token hızı
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
paketler = [4, 5, 3, 4]
sureler_ms = [25.0, 25.0, 25.0, 25.0]
ort_paket = sum(paketler) / len(paketler)
tok_sn = sum(paketler) / (sum(sureler_ms) / 1000.0)
spek_oran = sum(1 for k in paketler if k > 1) / len(paketler)
print("Ortalama paket:", ort_paket, "Token/sn:", tok_sn, "Spekülatif oran:", spek_oran)
```
???
```cikti
Ortalama paket: 4.0 Token/sn: 160.0 Spekülatif oran: 1.0
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: 4 adım toplam 100 ms sürdüğünde 16 token neden `160.0` token/sn hızına karşılık gelir? Sonra üç kusurlu başlangıç kodunu çalıştır ve her birinin neyi kaçırdığını önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · Paket kabul hızı ve spekülatif oran
`paket_kabul_hizi(paket_token_sayilari, sure_ms_listesi)`: iki girdi de eşit uzunlukta boş olmayan liste; `paket_token_sayilari` elemanları bool olmayan `int` ve `>= 1`; `sure_ms_listesi` elemanları bool olmayan sonlu sayı ve `> 0`. `{"ortalama_paket_token": ..., "saniyede_token": ..., "spekulatif_oran": ...}` döndür (`spekulatif_oran`: `k > 1` olan paketlerin toplam paket sayısına oranı). Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-59")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def paket_kabul_hizi(paket_token_sayilari, sure_ms_listesi):
    n = len(paket_token_sayilari)
    t = sum(paket_token_sayilari)
    return {"ortalama_paket_token": t / n, "saniyede_token": t / sum(sure_ms_listesi), "spekulatif_oran": sum(1 for k in paket_token_sayilari if k >= 1) / n}

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/spec_sidechannel.json")
for g in v["gozlemler"]:
    print(g["ad"], paket_kabul_hizi(g["paket_token_sayilari"], g["sure_ms_listesi"]))
```
```test
def sinama1(f):
    import copy, math, random
    def _y(a, b):
        return isinstance(a, dict) and set(a) == set(b) and all(abs(a[k] - b[k]) < 1e-11 for k in b)
    try:
        p = [4, 1, 3, 2]; s = [20.0, 30.0, 25.0, 25.0]; old = (list(p), list(s))
        r = f(p, s)
        if (p, s) != old or not _y(r, {"ortalama_paket_token": 2.5, "saniyede_token": 100.0, "spekulatif_oran": 0.75}):
            return False
        if not _y(f([1, 1], [50.0, 50.0]), {"ortalama_paket_token": 1.0, "saniyede_token": 20.0, "spekulatif_oran": 0.0}):
            return False
        rng = random.Random(59)
        for _ in range(25):
            n = rng.randint(2, 8); pp = [rng.randint(1, 6) for _ in range(n)]; ss = [rng.uniform(5.0, 50.0) for _ in range(n)]
            bek = {"ortalama_paket_token": sum(pp) / n, "saniyede_token": sum(pp) / (sum(ss) / 1000.0), "spekulatif_oran": sum(1 for k in pp if k > 1) / n}
            if not _y(f(list(pp), list(ss)), bek):
                return False
        for bad in ((None, [10.0]), ([], []), ([1, 2], [10.0]), ([0], [10.0]), ([True], [10.0]), ([1.5], [10.0]), ([2], [0.0]), ([2], [-5.0]), ([2], [True]), ([2], [float("nan")])):
            try:
                f(*bad); return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sinama1(paket_kabul_hizi), "ortalama paket, saniyede token, spekülatif oran ve geçersiz girdi")
for ad, mut in [("ms/sn dönüşümü yok", lambda p, s: dict(paket_kabul_hizi(p, s), saniyede_token=paket_kabul_hizi(p, s)["saniyede_token"] / 1000.0)), ("spekülatif oran >= 1", lambda p, s: dict(paket_kabul_hizi(p, s), spekulatif_oran=1.0)), ("ortalama yerine toplam", lambda p, s: dict(paket_kabul_hizi(p, s), ortalama_paket_token= float(sum(p))))]:
    ok(not sinama1(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(paket_kabul_hizi, _il.import_module('ai_gercek_ai_saldiri_59').referans_hiz, ([5, 4, 5, 3, 5, 4], [25.0, 24.0, 26.0, 25.0, 25.0, 25.0]), tohum=2832)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def paket_kabul_hizi(paket_token_sayilari, sure_ms_listesi):
    if not isinstance(paket_token_sayilari, list) or not isinstance(sure_ms_listesi, list):
        raise ValueError("liste")
    if not paket_token_sayilari or len(paket_token_sayilari) != len(sure_ms_listesi):
        raise ValueError("boyut")
    for k in paket_token_sayilari:
        if isinstance(k, bool) or not isinstance(k, int) or k < 1:
            raise ValueError("token")
    for s in sure_ms_listesi:
        if isinstance(s, bool) or not isinstance(s, (int, float)) or not math.isfinite(s) or s <= 0:
            raise ValueError("süre")
    n = len(paket_token_sayilari)
    t = sum(paket_token_sayilari)
    return {
        "ortalama_paket_token": t / n,
        "saniyede_token": t / (sum(sure_ms_listesi) / 1000.0),
        "spekulatif_oran": sum(1 for k in paket_token_sayilari if k > 1) / n,
    }

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/spec_sidechannel.json")
for g in v["gozlemler"]:
    print(g["ad"], paket_kabul_hizi(g["paket_token_sayilari"], g["sure_ms_listesi"]))
```
```hint
Toplam süreyi saniyeye çevirmek için `sum(sure_ms_listesi) / 1000.0` kullan; spekülatif oranda yalnız `k > 1` olanları say.
```
:::

::: anlat Aday öneklerin kabul oranı nasıl puanlanır?
Saldırgan her aday önek için gözlemlediği kabul oranını (`aday_kabul_oranlari` sözlüğü) beklenen `taban_oran` ($0 \le r_{\text{taban}} < 1$) ile karşılaştırır:
- En yüksek kabul oranına sahip anahtar `en_olasi_onek` olarak seçilir (eşitlikte alfabetik olarak en küçük anahtar).
- `sizinti_guveni = max(0.0, (en_yuksek_oran - taban_oran) / (1.0 - taban_oran))`
- `anomali = (en_yuksek_oran - taban_oran) >= 0.25`

**Görev 2'de sık tuzaklar:** En yüksek kabul oranı `taban_oran` değerinin altındaysa `sizinti_guveni` negatif olmamalı, `0.0`'a kırpılmalıdır.
:::

::: gorev 2 · Aday öneki puanlama ve yan kanal anomalisi
`aday_oneki_puanla(aday_kabul_oranlari, taban_oran)`: `aday_kabul_oranlari` boş olmayan `dict`, anahtarlar dolu `str`, değerler `[0, 1]` içinde bool olmayan sonlu sayı; `taban_oran` `[0, 1)` içinde bool olmayan sonlu sayı. `{"en_olasi_onek": ..., "sizinti_guveni": ..., "anomali": bool}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-59")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def aday_oneki_puanla(aday_kabul_oranlari, taban_oran):
    en = max(aday_kabul_oranlari, key=aday_kabul_oranlari.get)
    fark = aday_kabul_oranlari[en] - taban_oran
    return {"en_olasi_onek": en, "sizinti_guveni": fark, "anomali": False}

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/spec_sidechannel.json")
print(aday_oneki_puanla(v["aday_kabul_oranlari"], v["taban_oran"]))
```
```test
def sinama2(f):
    import copy
    def _y(a, b):
        return isinstance(a, dict) and set(a) == set(b) and a["en_olasi_onek"] == b["en_olasi_onek"] and type(a["anomali"]) is bool and a["anomali"] == b["anomali"] and abs(a["sizinti_guveni"] - b["sizinti_guveni"]) < 1e-12
    try:
        d = {"b_onek": 0.75, "a_onek": 0.25}; old = dict(d)
        r = f(d, 0.25)
        if d != old or not _y(r, {"en_olasi_onek": "b_onek", "sizinti_guveni": 0.5 / 0.75, "anomali": True}):
            return False
        if not _y(f({"z": 0.5, "a": 0.5}, 0.3), {"en_olasi_onek": "a", "sizinti_guveni": 0.2 / 0.7, "anomali": False}):
            return False
        if not _y(f({"x": 0.1}, 0.25), {"en_olasi_onek": "x", "sizinti_guveni": 0.0, "anomali": False}):
            return False
        for bad in ((None, 0.2), ({}, 0.2), ({"": 0.5}, 0.2), ({"a": 1.2}, 0.2), ({"a": -0.1}, 0.2), ({"a": True}, 0.2), ({"a": 0.5}, 1.0), ({"a": 0.5}, -0.1), ({"a": 0.5}, True), ({"a": 0.5}, float("nan"))):
            try:
                f(*bad); return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sinama2(aday_oneki_puanla), "normalize sızıntı güveni, eşitlik kuralı, anomali ve geçersiz girdi")
for ad, mut in [("normalize edilmemiş güven", lambda d, t: dict(aday_oneki_puanla(d, t), sizinti_guveni=max(d.values()) - t)), ("anomali hep False", lambda d, t: dict(aday_oneki_puanla(d, t), anomali=False)), ("eşitlikte ters sıra", lambda d, t: dict(aday_oneki_puanla(d, t), en_olasi_onek=max(d, key=lambda k: (d[k], k))))]:
    ok(not sinama2(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(aday_oneki_puanla, _il.import_module('ai_gercek_ai_saldiri_59').referans_puanla, ({'hasta_tani: diyabet': 0.82, 'hasta_tani: hipertansiyon': 0.31, 'hasta_tani: astim': 0.28}, 0.25), tohum=2926)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def aday_oneki_puanla(aday_kabul_oranlari, taban_oran):
    if not isinstance(aday_kabul_oranlari, dict) or not aday_kabul_oranlari:
        raise ValueError("adaylar")
    if isinstance(taban_oran, bool) or not isinstance(taban_oran, (int, float)) or not math.isfinite(taban_oran) or not 0 <= taban_oran < 1:
        raise ValueError("taban")
    for k, v in aday_kabul_oranlari.items():
        if not isinstance(k, str) or not k or isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1:
            raise ValueError("eleman")
    en = min(aday_kabul_oranlari, key=lambda k: (-aday_kabul_oranlari[k], k))
    val = aday_kabul_oranlari[en]
    guven = max(0.0, (val - taban_oran) / (1.0 - taban_oran))
    return {"en_olasi_onek": en, "sizinti_guveni": guven, "anomali": (val - taban_oran) >= 0.25}

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/spec_sidechannel.json")
print(aday_oneki_puanla(v["aday_kabul_oranlari"], v["taban_oran"]))
```
```hint
`min(aday_kabul_oranlari, key=lambda k: (-aday_kabul_oranlari[k], k))` ile en yüksek oranlı (eşitlikte alfabetik ilk) adayı seç.
```
:::

::: anlat Sabit boyutlu paket dolgusu yan kanalı nasıl kapatır?
Her doğrulama adımında ağa çıkan paketin tam olarak `hedef_sabit_boyut` ($M \ge \max(\text{paket\_token\_sayilari})$) token taşıması sağlanırsa, dış gözlemci tüm paketleri eşit boyutta görür:
- `dolgu_listesi = [hedef_sabit_boyut - k for k in paket_token_sayilari]`
- `toplam_dolgu = sum(dolgu_listesi)`
- `ek_yuk_orani = toplam_dolgu / (sum(paket_token_sayilari) + toplam_dolgu)`

**Görev 3'te sık tuzaklar:** `ek_yuk_orani` paydasına yalnız gerçek token toplamını yazmak oranı 1'in üzerine çıkarabilir; payda toplam iletilen (`gercek + dolgu`, yani `len(paket) * hedef_sabit_boyut`) token sayısıdır.
:::

::: gorev 3 · Sabit hız ve boyut dolgusu
`sabit_hiz_dolgusu(paket_token_sayilari, hedef_sabit_boyut)`: `paket_token_sayilari` boş olmayan liste, elemanları bool olmayan `int` ve `>= 1`; `hedef_sabit_boyut` bool olmayan `int` ve `>= max(paket_token_sayilari)`. `{"dolgu_listesi": [...], "toplam_dolgu": int, "ek_yuk_orani": float}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-59")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def sabit_hiz_dolgusu(paket_token_sayilari, hedef_sabit_boyut):
    d = [hedef_sabit_boyut - k for k in paket_token_sayilari]
    return {"dolgu_listesi": d, "toplam_dolgu": sum(d), "ek_yuk_orani": sum(d) / sum(paket_token_sayilari)}

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/spec_sidechannel.json")
for g in v["gozlemler"]:
    print(g["ad"], sabit_hiz_dolgusu(g["paket_token_sayilari"], v["hedef_sabit_boyut"]))
```
```test
def sinama3(f):
    import copy
    try:
        p = [5, 3, 1, 3]; old = list(p)
        r = f(p, 5)
        if p != old or r != {"dolgu_listesi": [0, 2, 4, 2], "toplam_dolgu": 8, "ek_yuk_orani": 8 / 20}:
            return False
        if f([4, 4], 4) != {"dolgu_listesi": [0, 0], "toplam_dolgu": 0, "ek_yuk_orani": 0.0}:
            return False
        for bad in ((None, 5), ([], 5), ([0, 2], 5), ([True, 2], 5), ([3, 5], 4), ([3, 5], True), ([1], True), ([3, 5], 5.0)):
            try:
                f(*bad); return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sinama3(sabit_hiz_dolgusu), "dolgu listesi, toplam dolgu, ek yük oranı ve geçersiz girdi")
for ad, mut in [("payda yalnız gerçek token", lambda p, h: dict(sabit_hiz_dolgusu(p, h), ek_yuk_orani=sabit_hiz_dolgusu(p, h)["toplam_dolgu"] / sum(p))), ("dolgu sıfır", lambda p, h: {"dolgu_listesi": [0]*len(p), "toplam_dolgu": 0, "ek_yuk_orani": 0.0}), ("toplam_dolgu 1 eksik", lambda p, h: dict(sabit_hiz_dolgusu(p, h), toplam_dolgu=sabit_hiz_dolgusu(p, h)["toplam_dolgu"] - 1))]:
    ok(not sinama3(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(sabit_hiz_dolgusu, _il.import_module('ai_gercek_ai_saldiri_59').referans_dolgu, ([5, 4, 5, 3, 5, 4], 5), tohum=2969)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def sabit_hiz_dolgusu(paket_token_sayilari, hedef_sabit_boyut):
    if not isinstance(paket_token_sayilari, list) or not paket_token_sayilari:
        raise ValueError("liste")
    for k in paket_token_sayilari:
        if isinstance(k, bool) or not isinstance(k, int) or k < 1:
            raise ValueError("token")
    if isinstance(hedef_sabit_boyut, bool) or not isinstance(hedef_sabit_boyut, int) or hedef_sabit_boyut < max(paket_token_sayilari):
        raise ValueError("hedef_sabit_boyut")
    d = [hedef_sabit_boyut - k for k in paket_token_sayilari]
    td = sum(d)
    tg = sum(paket_token_sayilari)
    return {"dolgu_listesi": d, "toplam_dolgu": td, "ek_yuk_orani": td / (tg + td)}

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/spec_sidechannel.json")
for g in v["gozlemler"]:
    print(g["ad"], sabit_hiz_dolgusu(g["paket_token_sayilari"], v["hedef_sabit_boyut"]))
```
```hint
`ek_yuk_orani` için `toplam_dolgu / (sum(paket_token_sayilari) + toplam_dolgu)` oranını hesapla.
```
:::

::: anlat Hata vitrini · çalışmış yanlış rapor
Yazar, kusurlu başlangıç kodlarını görünür sentetik veriyle çalıştırdı ve sonucu `outputs/yeni-ai-saldiri-59/gorunur-run-1.json` dosyasına kaydetti. Kusurlu kod milisaniyeyi saniyeye çevirmediği için hızı `173.33` yerine `0.1733` tok/sn bulur ve `hasta_tani: diyabet` adayındaki `%82` kabul oranına rağmen `anomali=false` döndürür. Doğru kod ise `sizinti_guveni=0.76` ve `anomali=true` ile gizli öneki işaretler.

Bu kaydedilmiş bir hesaplama çıktısıdır, canlı model yanıtı değildir ve rapor sentetiktir. Paylaşımlı bir önek önbelleğinde (`prefix/prompt lookup`) spekülatif kabul hızını izleyen bir saldırgan neden şifreli içerikleri tahmin edebilir? Kendi cümlenle açıkla.
:::

::: anlat Gerçek deney: SmolLM2 sunucusunun paketlerinden gizli bağlamı bulmak
Final, yerel önbellekteki gerçek **SmolLM2-135M** modelini (indirme yok) bir akış sunucusu gibi çalıştırır. Sunucu açgözlü (sıcaklık 0) **kendi kendine spekülatif çözme** kullanır: taslak, modelin 20. katmanından erken çıkıştır (ai-temel-27); her turda kabul edilen tokenlar tek pakette gönderilir ve turun gerçek GPU süresi ölçülür. Kurbanın isteği, dört aday gizli notun (`Credit risk: low / medium / high / unknown`) rastgele biriyle başlar ve 40 tokenlık bir yanıt istenir.

Saldırgan yalnız paket boyutlarını ve zamanlarını görür. Model açık olduğu için her adayı kendi makinesinde aynı şekilde yeniden koşar ve paket boyutu dizilerini gözlenenle karşılaştırır. Açgözlü çözmede dizi deterministiktir: doğru aday birebir eşleşir. Eşleşme oranları senin `aday_oneki_puanla` işlevine, gözlenen paketler `paket_kabul_hizi` işlevine verilir. Savunma olarak her paket `sabit_hiz_dolgusu` ile $\gamma + 1$ tokena doldurulur ve saldırı yeniden koşar.

Kabul: üç işlevin bağımsız referansla aynı sonucu vermesi, saldırının gizli bağlamı doğru bulması ve en az 0.1 ayırt edicilikle (en iyi ile ikinci aday arasındaki fark) bulması, dolgunun ayırt ediciliği azaltması.

**Neden sızar?** Bir turda kaç taslak tokenın kabul edileceği, devamın **ne kadar tahmin edilebilir** olduğuna bağlıdır. Erken çıkış taslağı, kolay (kalıplaşmış) tokenlarda tam modelle aynı fikirdedir, zor tokenlarda ayrılır. "Credit risk: high … court case" gibi bir gizli not, yanıtın hangi kısımlarının kalıplaşmış olacağını değiştirir. Bu yüzden paket boyutu dizisi (1, 1, 3, 1, 5, …) içeriğin bir **parmak izidir**. Açgözlü çözmede bu iz deterministiktir: aynı bağlam her seferinde aynı diziyi üretir. Saldırgan açık ağırlıklı modeli bildiği için adayları kendi makinesinde yeniden üretip karşılaştırabilir.

**Yazarın GPU koşusunda** gizli not doğru tahmin edildi ve ayırt edicilik 0.265 çıktı. Paketlerin çoğu tek tokendı, ama birkaç çok tokenlı paketin yeri adayları ayırmaya yetti. Sabit boyut dolgusundan sonra ayırt edicilik 0.059'a indi, sıfıra değil: dolgu her paketi aynı boyuta getirir ama **paket sayısını** değiştirmez, kabul oranı da paket sayısını belirler. Dolgunun bant genişliği bedeli %76'dır (ek yük oranı 0.76).

**Gerçek dünyadaki karşılığı:** Akış (streaming) yanıtlarında token başına paket boyutunun içeriği sızdırdığı ve verimli çıkarım tekniklerinin (spekülatif çözme, önbellek) zamanlama yan kanalı açtığı yakın tarihli çalışmalarda gösterildi. Tam savunma, boyut dolgusuna ek olarak tokenları **sabit aralıklarla ve sabit sayıda** göndermeyi (sabit hızlı akış) ya da yanıtı tümüyle tamponlayıp tek seferde göndermeyi gerektirir. İkisi de gecikme ve bant genişliği bedeli getirir.

**Kanıt dosyasını oku:** `gozlenen_paketler`, `simule_paketler`, `aday_oranlari` ve `dolgu` alanlarına bak. Soru 1: Paketlerin çoğu tek token olduğu hâlde (taslak zayıf) birkaç çok tokenlı paket neden bağlamı ele vermeye yetti? Soru 2: Dolgudan sonra ayırt edicilik neden tam sıfıra inmedi (paket sayısı ne söylüyor)? Soru 3: Sunucu örneklemeli üretim (sıcaklık > 0) kullansaydı saldırgan ne yapmak zorunda kalırdı; zaman yan kanalını kapatmak için dolguya ne eklemek gerekir?
:::

::: gorev Gerçek deney · GPU speculative decoding yan kanalı ve sabit dolgu
Önceki üç görevin `paket_kabul_hizi`, `aday_oneki_puanla` ve `sabit_hiz_dolgusu` işlevlerini birleştir. Çalıştır gerçek tabloyu gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
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
def paket_kabul_hizi(paket_token_sayilari, sure_ms_listesi):
    n = len(paket_token_sayilari); t = sum(paket_token_sayilari)
    return {"ortalama_paket_token": t / n, "saniyede_token": t / sum(sure_ms_listesi), "spekulatif_oran": 1.0}

def aday_oneki_puanla(aday_kabul_oranlari, taban_oran):
    en = max(aday_kabul_oranlari, key=aday_kabul_oranlari.get)
    return {"en_olasi_onek": en, "sizinti_guveni": aday_kabul_oranlari[en] - taban_oran, "anomali": False}

def sabit_hiz_dolgusu(paket_token_sayilari, hedef_sabit_boyut):
    d = [hedef_sabit_boyut - k for k in paket_token_sayilari]
    return {"dolgu_listesi": d, "toplam_dolgu": sum(d), "ek_yuk_orani": sum(d) / sum(paket_token_sayilari)}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_59 as D
    D.goster(paket_kabul_hizi, aday_oneki_puanla, sabit_hiz_dolgusu)
```
```test
import ai_lab, math
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('referans_hiz', 'referans_puanla', 'referans_dolgu', 'kanit_yaz', '_yakin'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
paket_kabul_hizi = need("paket_kabul_hizi")
aday_oneki_puanla = need("aday_oneki_puanla")
sabit_hiz_dolgusu = need("sabit_hiz_dolgusu")
def sinama1(f):
    import copy, math, random
    def _y(a, b):
        return isinstance(a, dict) and set(a) == set(b) and all(abs(a[k] - b[k]) < 1e-11 for k in b)
    try:
        p = [4, 1, 3, 2]; s = [20.0, 30.0, 25.0, 25.0]; old = (list(p), list(s))
        r = f(p, s)
        if (p, s) != old or not _y(r, {"ortalama_paket_token": 2.5, "saniyede_token": 100.0, "spekulatif_oran": 0.75}):
            return False
        if not _y(f([1, 1], [50.0, 50.0]), {"ortalama_paket_token": 1.0, "saniyede_token": 20.0, "spekulatif_oran": 0.0}):
            return False
        for bad in ((None, [10.0]), ([], []), ([1, 2], [10.0]), ([0], [10.0]), ([True], [10.0]), ([2], [0.0]), ([2], [True])):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama1(paket_kabul_hizi), "ortalama paket, saniyede token ve spekülatif oran")
for ad, mut in [("ms/sn dönüşümü yok", lambda p, s: dict(paket_kabul_hizi(p, s), saniyede_token=paket_kabul_hizi(p, s)["saniyede_token"] / 1000.0)), ("spekülatif oran >= 1", lambda p, s: dict(paket_kabul_hizi(p, s), spekulatif_oran=1.0)), ("ortalama yerine toplam", lambda p, s: dict(paket_kabul_hizi(p, s), ortalama_paket_token=float(sum(p))))]:
    kontrol(not sinama1(mut), "mutant reddedildi: " + ad)
def sinama2(f):
    def _y(a, b):
        return isinstance(a, dict) and set(a) == set(b) and a["en_olasi_onek"] == b["en_olasi_onek"] and type(a["anomali"]) is bool and a["anomali"] == b["anomali"] and abs(a["sizinti_guveni"] - b["sizinti_guveni"]) < 1e-12
    try:
        d = {"b_onek": 0.75, "a_onek": 0.25}; old = dict(d)
        if not _y(f(d, 0.25), {"en_olasi_onek": "b_onek", "sizinti_guveni": 0.5 / 0.75, "anomali": True}) or d != old: return False
        if not _y(f({"z": 0.5, "a": 0.5}, 0.3), {"en_olasi_onek": "a", "sizinti_guveni": 0.2 / 0.7, "anomali": False}): return False
        if not _y(f({"x": 0.1}, 0.25), {"en_olasi_onek": "x", "sizinti_guveni": 0.0, "anomali": False}): return False
        for bad in ((None, 0.2), ({}, 0.2), ({"": 0.5}, 0.2), ({"a": 1.2}, 0.2), ({"a": 0.5}, 1.0), ({"a": 0.5}, True)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama2(aday_oneki_puanla), "normalize sızıntı güveni ve anomali")
for ad, mut in [("normalize edilmemiş güven", lambda d, t: dict(aday_oneki_puanla(d, t), sizinti_guveni=max(d.values()) - t)), ("anomali hep False", lambda d, t: dict(aday_oneki_puanla(d, t), anomali=False)), ("eşitlikte ters sıra", lambda d, t: dict(aday_oneki_puanla(d, t), en_olasi_onek=max(d, key=lambda k: (d[k], k))))]:
    kontrol(not sinama2(mut), "mutant reddedildi: " + ad)
def sinama3(f):
    try:
        p = [5, 3, 1, 3]; old = list(p)
        if f(p, 5) != {"dolgu_listesi": [0, 2, 4, 2], "toplam_dolgu": 8, "ek_yuk_orani": 8 / 20} or p != old: return False
        if f([4, 4], 4) != {"dolgu_listesi": [0, 0], "toplam_dolgu": 0, "ek_yuk_orani": 0.0}: return False
        for bad in ((None, 5), ([], 5), ([0, 2], 5), ([3, 5], 4), ([3, 5], True), ([1], True)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama3(sabit_hiz_dolgusu), "dolgu listesi, toplam dolgu ve ek yük oranı")
for ad, mut in [("payda yalnız gerçek token", lambda p, h: dict(sabit_hiz_dolgusu(p, h), ek_yuk_orani=sabit_hiz_dolgusu(p, h)["toplam_dolgu"] / sum(p))), ("dolgu sıfır", lambda p, h: {"dolgu_listesi": [0]*len(p), "toplam_dolgu": 0, "ek_yuk_orani": 0.0}), ("toplam_dolgu 1 eksik", lambda p, h: dict(sabit_hiz_dolgusu(p, h), toplam_dolgu=sabit_hiz_dolgusu(p, h)["toplam_dolgu"] - 1))]:
    kontrol(not sinama3(mut), "mutant reddedildi: " + ad)
# farksal tarama (final)
import importlib as _il
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_R = _il.import_module('sandbox.ai_gercek_ai_saldiri_59')
for _ad, _ref, _taban, _toh in (
    ('paket_kabul_hizi', 'referans_hiz', ([5, 4, 5, 3, 5, 4], [25.0, 24.0, 26.0, 25.0, 25.0, 25.0]), 3354),
    ('aday_oneki_puanla', 'referans_puanla', ({'hasta_tani: diyabet': 0.82, 'hasta_tani: hipertansiyon': 0.31, 'hasta_tani: astim': 0.28}, 0.25), 3448),
    ('sabit_hiz_dolgusu', 'referans_dolgu', ([5, 4, 5, 3, 5, 4], 5), 3491),
):
    _t, _g = _ff(need(_ad), getattr(_R, _ref), _taban, tohum=_toh)
    kontrol(_t, "farksal tarama (" + _ad + "): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
if not all(checks): stop()
from sandbox import ai_gercek_ai_saldiri_59 as D
try: r = D.deney(paket_kabul_hizi, aday_oneki_puanla, sabit_hiz_dolgusu)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r["hiz_ayni"], "gerçek paket dizilerinde kabul hızı bağımsız hesapla aynı")
kontrol(r["puan_ayni"], "gerçek aday oranlarında önek puanlama bağımsız hesapla aynı")
kontrol(r["dolgu_ayni"], "gerçek paket dizilerinde sabit dolgu hesabı bağımsız hesapla aynı")
kontrol(r["dogru_tahmin"] and r["ayirt_edicilik"] >= 0.1, "gerçek SmolLM2 paket boyutu dizisinden gizli bağlam doğru ve ayırt edici biçimde bulundu")
kontrol(r["dolgu"]["ayirt_edicilik"] < r["ayirt_edicilik"], "sabit boyutlu dolgu ayırt ediciliği azalttı")
ai_lab.kanit_yaz("ai-saldiri-59-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-saldiri-59", "deney": r})
```
```solution
import ai_lab
import math
def paket_kabul_hizi(paket_token_sayilari, sure_ms_listesi):
    if not isinstance(paket_token_sayilari, list) or not isinstance(sure_ms_listesi, list):
        raise ValueError("liste")
    if not paket_token_sayilari or len(paket_token_sayilari) != len(sure_ms_listesi):
        raise ValueError("boyut")
    for k in paket_token_sayilari:
        if isinstance(k, bool) or not isinstance(k, int) or k < 1:
            raise ValueError("token")
    for s in sure_ms_listesi:
        if isinstance(s, bool) or not isinstance(s, (int, float)) or not math.isfinite(s) or s <= 0:
            raise ValueError("süre")
    n = len(paket_token_sayilari)
    t = sum(paket_token_sayilari)
    return {
        "ortalama_paket_token": t / n,
        "saniyede_token": t / (sum(sure_ms_listesi) / 1000.0),
        "spekulatif_oran": sum(1 for k in paket_token_sayilari if k > 1) / n,
    }

def aday_oneki_puanla(aday_kabul_oranlari, taban_oran):
    if not isinstance(aday_kabul_oranlari, dict) or not aday_kabul_oranlari:
        raise ValueError("adaylar")
    if isinstance(taban_oran, bool) or not isinstance(taban_oran, (int, float)) or not math.isfinite(taban_oran) or not 0 <= taban_oran < 1:
        raise ValueError("taban")
    for k, v in aday_kabul_oranlari.items():
        if not isinstance(k, str) or not k or isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1:
            raise ValueError("eleman")
    en = min(aday_kabul_oranlari, key=lambda k: (-aday_kabul_oranlari[k], k))
    val = aday_kabul_oranlari[en]
    guven = max(0.0, (val - taban_oran) / (1.0 - taban_oran))
    return {"en_olasi_onek": en, "sizinti_guveni": guven, "anomali": (val - taban_oran) >= 0.25}

def sabit_hiz_dolgusu(paket_token_sayilari, hedef_sabit_boyut):
    if not isinstance(paket_token_sayilari, list) or not paket_token_sayilari:
        raise ValueError("liste")
    for k in paket_token_sayilari:
        if isinstance(k, bool) or not isinstance(k, int) or k < 1:
            raise ValueError("token")
    if isinstance(hedef_sabit_boyut, bool) or not isinstance(hedef_sabit_boyut, int) or hedef_sabit_boyut < max(paket_token_sayilari):
        raise ValueError("hedef_sabit_boyut")
    d = [hedef_sabit_boyut - k for k in paket_token_sayilari]
    td = sum(d)
    tg = sum(paket_token_sayilari)
    return {"dolgu_listesi": d, "toplam_dolgu": td, "ek_yuk_orani": td / (tg + td)}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_59 as D
    D.goster(paket_kabul_hizi, aday_oneki_puanla, sabit_hiz_dolgusu)
```
```hint
Üç işlevi birleştir; `saniyede_token` için ms→sn dönüşümünü ve `ek_yuk_orani` için toplam paydasını koru.
```
:::

::: anlat Sınır
Bu ders gerçek SmolLM2-135M'de açgözlü `speculative decoding` sunucusunun paket boyutu yan kanalını ve sabit boyut dolgusunu ölçer; dolgunun paket sayısını gizlemediğini gösterir. Örneklemeli üretimi, saldırganın modeli bilmediği durumu, çok sayıda aday, TLS kayıt birleştirme, Nagle ve ağ gürültüsünü, donanım önbellek (L3/PCIe) zamanlama izlerini kapsamaz.
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
Speculative decoding içinde taslak tokenlar hedef modelle doğrulanır; kabul edilen ardışık token sayısı bir paketin boyutunu değiştirebilir. Ortak ön ek kabul oranını etkiliyorsa saldırgan adaylarını bu gözlemle sıralar. Sabit boyut dolgusunun paket boyutunu gizlerken paket sayısını ve zamanlamayı gizlemediğini vurgula. Yerel açık ağırlıklı, greedy oracle varsayımından gürültülü uzak ağa doğrudan başarı oranı taşınamaz.

Önkoşul ve yol köprüsü: ai-saldiri-33 KV-cache maliyetini; ai-savunma-31 tüketim sınırını gösterir.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| Tüm paketler eşitse bütün yan kanal kapandı | Paket sayısı, süre ve yön hâlâ gözlemdir |

Dinleyiciye sor: Bu dersin kanıtı hangi gözlemi gösterir; hangi daha güçlü iddia için ek deney gerekir? Kanıtın model, ayar, veri kökeni ve hata alanlarını açarak cevabını gerekçelendir.
:::
