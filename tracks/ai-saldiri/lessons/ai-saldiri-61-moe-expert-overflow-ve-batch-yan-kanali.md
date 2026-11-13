---
id: ai-saldiri-61
title: Mixture-of-Experts (MoE) Expert Overflow · Çapraz Kiracı Batch Yan Kanalı
summary: Sabit kapasiteli Mixture-of-Experts (MoE) katmanlarında uzman doyurma ve taşan token hesabını yap; aynı batch içindeki kurban tokenlerinin düşürülme oranını ölç ve kiracı kotasıyla (per-tenant quota) izolasyonu GPU'da doğrula.
esleme: ai-saldiri-38, ai-saldiri-59, ai-savunma-31
timeout: 60
---

::: anlat Aynı batch içindeki başka bir kullanıcı modelinin uzmanlarını nasıl körleştirir?
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Sabit kapasiteli `Mixture-of-Experts` (MoE) mimarilerinde bir batch içindeki tüm tokenler aynı uzman (`expert`) tamponlarını paylaşır; saldırgan belirli bir uzmanı doyurduğunda (`expert overflow`) kurbanın o uzmana giden tokenleri düşürülür veya yan kanal oluşturur (Hayes vd. 2024, Yona vd. 2024) | İlk üç görev: `veri/moe_overflow.json` içindeki **sentetik** uzman yönlendirme listeleri. Final: SmolLM2-135M'in gerçek MLP bloğundan damıtılan top-1 MoE katmanında açgözlü saldırı dizisiyle uzman doyurma, kiracı kotası ve sıralama yan kanalı | Dinamik kapasiteli (`dropless MoE` / MegaBlocks) çekirdeklerdeki zamanlama farklarını token düşürme modeliyle göstermez |
| Kiracı başına uzman kotası (`per-tenant expert quota`) tek bir kullanıcının uzman tamponunu tekelleştirmesini önler | Uzman yük tablosu, taşan token sayısı, kurban düşürme oranı ve kotalı batch izolasyonu | Kotanın meşru tekil uzun bağlamlı isteklerde yaratabileceği performans kaybını ortadan kaldırmaz |

> [!NOT]
> Görevler `veri/moe_overflow.json` dosyasını okur; dosya sentetiktir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; değişiklikler taşınmaz, **kalıcılık yoktur**. Ekranda ayrı dosya görüntüleyici yoktur; içeriği görmek için `print` kullan. Gizli testler ayrıdır. Final yeni model indirmez ve GPU varsa onu kullanır.

`Mixture-of-Experts` (MoE) modelleri, her katmanda $E$ adet uzman ağ (`expert FFN`) bulundurur ve bir yönlendirici (`router`) her tokeni en uygun 1 veya $k$ uzmana gönderir. Donanım verimliliği ve statik tensör boyutları için her uzmanın tek bir batch'te işleyebileceği maksimum token sayısı **kapasite** ($C$) ile sınırlandırılır.

**Expert Overflow Saldırısı:** Çok kiracılı (`multi-tenant`) bir çıkarım sunucusu, saldırganın ve kurbanın isteklerini aynı batch içinde birleştirdiğinde:
1. Saldırgan, yönlendiriciyi belirli bir $e^*$ uzmanına yönlendirecek token dizileri gönderir ve $e^*$ uzmanının yükünü $L(e^*) > C$ yapar.
2. Kapasiteyi aşan $\max(0, L(e^*) - C)$ token işlenmeden düşürülür (`token dropping`, yalnız artık bağlantıdan geçer).
3. Kurbanın güvenlik denetimi veya kritik akıl yürütme tokenleri $e^*$ uzmanına düştüğünde model kalitesi çöker ya da saldırgan hangi uzmanların taştığını gözlemleyerek kurbanın istem içeriğini çıkarır (`batch side-channel`).

**Saldırgan ne dener?** Hedef uzmanın yönlendirici ağırlığı $w_{e^*}$ ile yüksek iç çarpım veren tokenleri tekrarlayarak tek bir uzmana kapasitenin üzerinde yük bindirir.

**Savunma neden kırılır?** Toplam istek uzunluğunu sınırlamak yetmez; saldırgan az sayıda tokenin **tamamını** tek bir uzmana odaklayabilir. Savunma, bir batch içinde her kiracının tek bir uzmanda en fazla `kiraci_kota` kadar slot kullanmasına izin vermek veya kiracıları ayrı uzman tamponlarında izole etmektir.

**Görev 1'de sık tuzaklar:** Taşan token sayısını hesaplarken taşan uzmandaki **tüm** tokenleri değil, yalnız kapasiteyi aşan kısmı (`yuk - kapasite`) toplamalısın.

Kaynaklar: [Hayes vd. 2024 - Buffer Overflow in Mixture of Experts](https://arxiv.org/abs/2402.05526), [Yona vd. 2024 - Stealing User Prompts via Mixture of Experts](https://arxiv.org/abs/2410.22884), [Fedus vd. 2022 - Switch Transformers](https://arxiv.org/abs/2101.03961). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Köprü: ai-saldiri-59 spekülatif çözme yan kanalını inceler; bu ders `Mixture-of-Experts` yönlendirme kapasitesindeki çapraz kiracı (`cross-tenant`) taşma ve yan kanal mekanizmasını modeller.
:::

::: tahmin Uzman kapasitesi aşıldığında kaç token taşar?
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
saldirgan = [2, 2, 2, 2, 0]
kurban = [2, 1, 2]
kapasite = 4
birlesik = saldirgan + kurban
yuk = {u: birlesik.count(u) for u in sorted(set(birlesik))}
tasan = [u for u, s in yuk.items() if s > kapasite]
tasan_tok = sum(s - kapasite for s in yuk.values() if s > kapasite)
print("Yük:", yuk, "Taşan uzmanlar:", tasan, "Taşan token:", tasan_tok)
```
???
```cikti
Yük: {0: 1, 1: 1, 2: 6} Taşan uzmanlar: [2] Taşan token: 2
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: 2 numaralı uzmana toplam 6 token geldiğinde ve kapasite 4 olduğunda neden 6 değil de `2` token taşmış sayılır? Sonra üç kusurlu başlangıç kodunu çalıştır ve her birinin neyi kaçırdığını önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · Uzman doyurma ve taşan token hesabı
`uzman_doyurma_hesabi(saldirgan_istekleri, kurban_istekleri, kapasite)`: `saldirgan_istekleri` ve `kurban_istekleri` bool olmayan negatif olmayan `int` listeleri (ikisi birden boş olamaz); `kapasite` bool olmayan `int` ve `>= 1`. İki listedeki uzman indislerinin toplam sıklığını `yuk_tablosu` (anahtarlar artan sırada) olarak çıkar; `yuk > kapasite` olan uzmanları `tasan_uzmanlar` (artan sırada) ve kapasiteyi aşan fazlalıkların toplamını `toplam_tasan_token` olarak hesapla. `{"yuk_tablosu": {...}, "tasan_uzmanlar": [...], "toplam_tasan_token": int}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-61")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def uzman_doyurma_hesabi(saldirgan_istekleri, kurban_istekleri, kapasite):
    top = saldirgan_istekleri + kurban_istekleri
    yuk = {u: top.count(u) for u in sorted(set(top))}
    tasan = [u for u, s in yuk.items() if s > kapasite]
    return {"yuk_tablosu": yuk, "tasan_uzmanlar": tasan, "toplam_tasan_token": sum(yuk[u] for u in tasan)}

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/moe_overflow.json")
print(uzman_doyurma_hesabi(v["saldirgan_istekleri"], v["kurban_istekleri"], v["kapasite"]))
```
```test
def sinama1(f):
    import copy
    try:
        s = [2, 2, 2, 0]; k = [2, 2, 1]; old = (list(s), list(k))
        r = f(s, k, 3)
        if (s, k) != old or r != {"yuk_tablosu": {0: 1, 1: 1, 2: 5}, "tasan_uzmanlar": [2], "toplam_tasan_token": 2} or list(r["yuk_tablosu"]) != [0, 1, 2]:
            return False
        if f([], [1, 1], 2) != {"yuk_tablosu": {1: 2}, "tasan_uzmanlar": [], "toplam_tasan_token": 0}:
            return False
        for bad in ((None, [1], 2), ([1], None, 2), ([], [], 2), ([-1], [1], 2), ([True], [1], 2), ([1], [1], 0), ([1], [1], True), ([1], [1], 1.5)):
            try:
                f(*bad); return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sinama1(uzman_doyurma_hesabi), "uzman yük tablosu, taşan uzmanlar, taşan token toplamı ve geçersiz girdi")
for ad, mut in [("kapasite çıkarılmadı", lambda s, k, c: dict(uzman_doyurma_hesabi(s, k, c), toplam_tasan_token=sum(v for v in uzman_doyurma_hesabi(s, k, c)["yuk_tablosu"].values() if v > c))), ("taşan >= kapasite", lambda s, k, c: dict(uzman_doyurma_hesabi(s, k, c), tasan_uzmanlar=[u for u, v in uzman_doyurma_hesabi(s, k, c)["yuk_tablosu"].items() if v >= c])), ("yalnız saldırgan sayıldı", lambda s, k, c: uzman_doyurma_hesabi(s, [], c) if s else uzman_doyurma_hesabi(s, k, c))]:
    ok(not sinama1(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(uzman_doyurma_hesabi, _il.import_module('ai_gercek_ai_saldiri_61').referans_doyurma, ([2, 2, 2, 2, 2, 0, 2, 1], [2, 2, 1, 3, 2, 0], 4), tohum=3273)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
def _liste(lst):
    if not isinstance(lst, list):
        raise ValueError("liste")
    for u in lst:
        if isinstance(u, bool) or not isinstance(u, int) or u < 0:
            raise ValueError("uzman")

def uzman_doyurma_hesabi(saldirgan_istekleri, kurban_istekleri, kapasite):
    _liste(saldirgan_istekleri); _liste(kurban_istekleri)
    if not saldirgan_istekleri and not kurban_istekleri:
        raise ValueError("boş")
    if isinstance(kapasite, bool) or not isinstance(kapasite, int) or kapasite < 1:
        raise ValueError("kapasite")
    say = {}
    for u in saldirgan_istekleri + kurban_istekleri:
        say[u] = say.get(u, 0) + 1
    yuk = {u: say[u] for u in sorted(say)}
    tasan = [u for u, s in yuk.items() if s > kapasite]
    top_t = sum(s - kapasite for s in yuk.values() if s > kapasite)
    return {"yuk_tablosu": yuk, "tasan_uzmanlar": tasan, "toplam_tasan_token": top_t}

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/moe_overflow.json")
print(uzman_doyurma_hesabi(v["saldirgan_istekleri"], v["kurban_istekleri"], v["kapasite"]))
```
```hint
Her uzman için toplam sayımı bul; `s > kapasite` olanlarda `s - kapasite` farklarını topla.
```
:::

::: anlat Kurbanın düşürülen token oranı nasıl ölçülür?
Taşan uzmanlar kümesi `tasan_uzmanlar` bilindiğinde, kurbanın uzman istekleri (`kurban_uzmanlari`) içinde bu taşan uzmanlara yönlendirilen her token taşma bölgesine girer:
- `etkilenen_token_sayisi`: `kurban_uzmanlari` içinde `tasan_uzmanlar` kümesinde yer alan eleman sayısı (tekrarlar dahil).
- `dusurme_orani = etkilenen_token_sayisi / len(kurban_uzmanlari)`.
- `etkilenen_uzmanlar`: Kurbanın taşan uzmanlarla kesişen tekrarsız, sıralı uzman listesi.

**Görev 2'de sık tuzaklar:** `etkilenen_token_sayisi` hesaplarken `set(kurban_uzmanlari)` üzerinden saymak kurbanın aynı uzmana giden birden çok tokenini tek sayar; liste üzerinden sayılmalıdır.
:::

::: gorev 2 · Kurbanın düşürülen token oranı
`dusurulen_token_orani(kurban_uzmanlari, tasan_uzmanlar)`: `kurban_uzmanlari` boş olmayan liste (bool olmayan negatif olmayan `int`); `tasan_uzmanlar` `list` veya `set` (bool olmayan negatif olmayan `int`, boş olabilir). `{"etkilenen_token_sayisi": int, "dusurme_orani": float, "etkilenen_uzmanlar": [...]}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-61")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def dusurulen_token_orani(kurban_uzmanlari, tasan_uzmanlar):
    ortak = sorted(set(kurban_uzmanlari) & set(tasan_uzmanlar))
    return {"etkilenen_token_sayisi": len(ortak), "dusurme_orani": len(ortak) / len(kurban_uzmanlari), "etkilenen_uzmanlar": ortak}

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/moe_overflow.json")
print(dusurulen_token_orani(v["kurban_istekleri"], [2]))
```
```test
def sinama2(f):
    import copy
    try:
        k = [2, 2, 1, 3, 2, 0]; t = [2, 5]; old = (list(k), list(t))
        r = f(k, t)
        if (k, t) != old or r != {"etkilenen_token_sayisi": 3, "dusurme_orani": 0.5, "etkilenen_uzmanlar": [2]}:
            return False
        if f([1, 2], []) != {"etkilenen_token_sayisi": 0, "dusurme_orani": 0.0, "etkilenen_uzmanlar": []}:
            return False
        for bad in (([], [1]), (None, [1]), ([1], None), ([-1], [1]), ([True], [1]), ([1], [-1]), ([1], [True])):
            try:
                f(*bad); return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sinama2(dusurulen_token_orani), "tekrarlı kurban token sayımı, düşürme oranı ve geçersiz girdi")
for ad, mut in [("küme boyutu sayıldı", lambda k, t: dict(dusurulen_token_orani(k, t), etkilenen_token_sayisi=len(set(k) & set(t)), dusurme_orani=len(set(k) & set(t)) / len(k))), ("oran hep 0", lambda k, t: dict(dusurulen_token_orani(k, t), dusurme_orani=0.0)), ("tüm taşanları döndür", lambda k, t: dict(dusurulen_token_orani(k, t), etkilenen_uzmanlar=sorted(set(t))))]:
    ok(not sinama2(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(dusurulen_token_orani, _il.import_module('ai_gercek_ai_saldiri_61').referans_dusurme, ([2, 2, 1, 3, 2, 0], [2]), tohum=3410)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
def dusurulen_token_orani(kurban_uzmanlari, tasan_uzmanlar):
    if not isinstance(kurban_uzmanlari, list) or not kurban_uzmanlari:
        raise ValueError("kurban")
    for u in kurban_uzmanlari:
        if isinstance(u, bool) or not isinstance(u, int) or u < 0:
            raise ValueError("uzman")
    if not isinstance(tasan_uzmanlar, (list, set, frozenset)):
        raise ValueError("tasan")
    tk = set()
    for u in tasan_uzmanlar:
        if isinstance(u, bool) or not isinstance(u, int) or u < 0:
            raise ValueError("tasan eleman")
        tk.add(u)
    etk = sum(1 for u in kurban_uzmanlari if u in tk)
    return {"etkilenen_token_sayisi": etk, "dusurme_orani": etk / len(kurban_uzmanlari), "etkilenen_uzmanlar": sorted({u for u in kurban_uzmanlari if u in tk})}

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/moe_overflow.json")
print(dusurulen_token_orani(v["kurban_istekleri"], [2]))
```
```hint
`sum(1 for u in kurban_uzmanlari if u in tk)` ile kurbanın etkilenen tüm tokenlerini say.
```
:::

::: anlat Kiracı kotasıyla izole batch nasıl çalışır?
Her kiracıya uzman başına en fazla `kiraci_kota` ($1 \le \text{kota} \le C$) token gönderme hakkı tanındığında:
1. Korumasız durumda `saldirgan_istekleri` ve `kurban_istekleri` doğrudan birleştirilip `korumasiz_dusurme_orani` hesaplanır.
2. Korumalı durumda saldırganın her uzmana gönderdiği token sayısı `kiraci_kota` ile kırpılır (`kabul_saldirgan`), ardından `kurban_istekleri` ile birleştirilerek `korumali_dusurme_orani` hesaplanır.
3. `engellenen_saldirgan_token = len(saldirgan_istekleri) - len(kabul_saldirgan)`.
4. `koruma_basarili = (korumali_dusurme_orani < korumasiz_dusurme_orani) or (korumasiz_dusurme_orani == 0.0)`.

**Görev 3'te sık tuzaklar:** Kota yalnız saldırganın uzman başına sayacına uygulanır; saldırganın toplam token sayısını değil, **her uzman için ayrı ayrı** en fazla `kiraci_kota` geçişini sınırlar.
:::

::: gorev 3 · Kiracı kotalı izole batch raporu
`izole_batch_raporu(saldirgan_istekleri, kurban_istekleri, kapasite, kiraci_kota)`: `saldirgan_istekleri` (boş olabilir) ve `kurban_istekleri` (boş olamaz) geçerli uzman listeleri; `kapasite >= 1` ve `1 <= kiraci_kota <= kapasite` bool olmayan `int`. `{"korumasiz_dusurme_orani": float, "korumali_dusurme_orani": float, "engellenen_saldirgan_token": int, "koruma_basarili": bool}` döndür. Geçersiz girdide `ValueError`; girdi değişmez.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-61")
```
```starter
import math
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def izole_batch_raporu(saldirgan_istekleri, kurban_istekleri, kapasite, kiraci_kota):
    return {"korumasiz_dusurme_orani": 0.5, "korumali_dusurme_orani": 0.5, "engellenen_saldirgan_token": 0, "koruma_basarili": False}

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/moe_overflow.json")
print(izole_batch_raporu(v["saldirgan_istekleri"], v["kurban_istekleri"], v["kapasite"], v["kiraci_kota"]))
```
```test
def sinama3(f):
    import copy
    try:
        s = [2, 2, 2, 2, 0]; k = [2, 2, 1, 3]; old = (list(s), list(k))
        r = f(s, k, 4, 2)
        if (s, k) != old or r != {"korumasiz_dusurme_orani": 0.5, "korumali_dusurme_orani": 0.0, "engellenen_saldirgan_token": 2, "koruma_basarili": True}:
            return False
        if f([1], [2, 3], 4, 2) != {"korumasiz_dusurme_orani": 0.0, "korumali_dusurme_orani": 0.0, "engellenen_saldirgan_token": 0, "koruma_basarili": True}:
            return False
        if f([0, 0], [0], 2, 1)["engellenen_saldirgan_token"] != 1 or f([], [0], 1, 1)["engellenen_saldirgan_token"] != 0:
            return False
        for bad in ((None, [1], 4, 2), ([1], [], 4, 2), ([1], [1], 0, 1), ([1], [1], 4, 0), ([1], [1], 4, 5), ([1], [1], True, 1), ([1], [1], 4, True)):
            try:
                f(*bad); return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sinama3(izole_batch_raporu), "korumasız/korumalı düşürme oranı, engellenen token ve geçersiz girdi")
for ad, mut in [("kota uygulanmadı", lambda s, k, c, q: dict(izole_batch_raporu(s, k, c, q), korumali_dusurme_orani=izole_batch_raporu(s, k, c, q)["korumasiz_dusurme_orani"], engellenen_saldirgan_token=0)), ("koruma hep False", lambda s, k, c, q: dict(izole_batch_raporu(s, k, c, q), koruma_basarili=False)), ("engellenen 0", lambda s, k, c, q: dict(izole_batch_raporu(s, k, c, q), engellenen_saldirgan_token=0))]:
    ok(not sinama3(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(izole_batch_raporu, _il.import_module('ai_gercek_ai_saldiri_61').referans_izole, ([2, 2, 2, 2, 2, 0, 2, 1], [2, 2, 1, 3, 2, 0], 4, 2), tohum=3055)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(uzman_doyurma_hesabi, _il.import_module('ai_gercek_ai_saldiri_61').referans_doyurma, ([2, 2, 2, 2, 2, 0, 2, 1], [2, 2, 1, 3, 2, 0], 4), tohum=3273, ekler=(([], [], 2),))
ok(_t, "farksal tarama (uzman_doyurma_hesabi): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
_t, _g = _ff(dusurulen_token_orani, _il.import_module('ai_gercek_ai_saldiri_61').referans_dusurme, ([2, 2, 1, 3, 2, 0], [2]), tohum=3410)
ok(_t, "farksal tarama (dusurulen_token_orani): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
# Kapasitenin alt geçerli sınırı 1'dir; sıfırla karıştırılmamalı.
ok(izole_batch_raporu([], [0], 1, 1) == {"korumasiz_dusurme_orani": 0.0, "korumali_dusurme_orani": 0.0, "engellenen_saldirgan_token": 0, "koruma_basarili": True}, "kapasite=1 ve kota=1 geçerli")
```
```solution
def _liste(lst, bos_izin=True):
    if not isinstance(lst, list) or (not bos_izin and not lst):
        raise ValueError("liste")
    for u in lst:
        if isinstance(u, bool) or not isinstance(u, int) or u < 0:
            raise ValueError("uzman")

def uzman_doyurma_hesabi(saldirgan_istekleri, kurban_istekleri, kapasite):
    _liste(saldirgan_istekleri, True); _liste(kurban_istekleri, True)
    if not saldirgan_istekleri and not kurban_istekleri:
        raise ValueError("boş")
    if isinstance(kapasite, bool) or not isinstance(kapasite, int) or kapasite < 1:
        raise ValueError("kapasite")
    say = {}
    for u in saldirgan_istekleri + kurban_istekleri:
        say[u] = say.get(u, 0) + 1
    yuk = {u: say[u] for u in sorted(say)}
    tasan = [u for u, s in yuk.items() if s > kapasite]
    top_t = sum(s - kapasite for s in yuk.values() if s > kapasite)
    return {"yuk_tablosu": yuk, "tasan_uzmanlar": tasan, "toplam_tasan_token": top_t}

def dusurulen_token_orani(kurban_uzmanlari, tasan_uzmanlar):
    _liste(kurban_uzmanlari, False)
    if not isinstance(tasan_uzmanlar, (list, set, frozenset)):
        raise ValueError("tasan")
    tk = set()
    for u in tasan_uzmanlar:
        if isinstance(u, bool) or not isinstance(u, int) or u < 0:
            raise ValueError("tasan eleman")
        tk.add(u)
    etk = sum(1 for u in kurban_uzmanlari if u in tk)
    return {"etkilenen_token_sayisi": etk, "dusurme_orani": etk / len(kurban_uzmanlari), "etkilenen_uzmanlar": sorted({u for u in kurban_uzmanlari if u in tk})}

def izole_batch_raporu(saldirgan_istekleri, kurban_istekleri, kapasite, kiraci_kota):
    _liste(saldirgan_istekleri, True); _liste(kurban_istekleri, False)
    if isinstance(kapasite, bool) or not isinstance(kapasite, int) or kapasite < 1:
        raise ValueError("kapasite")
    if isinstance(kiraci_kota, bool) or not isinstance(kiraci_kota, int) or not 1 <= kiraci_kota <= kapasite:
        raise ValueError("kota")
    ham = uzman_doyurma_hesabi(saldirgan_istekleri, kurban_istekleri, kapasite)
    korumasiz = dusurulen_token_orani(kurban_istekleri, ham["tasan_uzmanlar"])["dusurme_orani"]
    sayac = {}; kabul = []
    for u in saldirgan_istekleri:
        if sayac.get(u, 0) < kiraci_kota:
            sayac[u] = sayac.get(u, 0) + 1
            kabul.append(u)
    kor = uzman_doyurma_hesabi(kabul, kurban_istekleri, kapasite)
    korumali = dusurulen_token_orani(kurban_istekleri, kor["tasan_uzmanlar"])["dusurme_orani"]
    return {
        "korumasiz_dusurme_orani": korumasiz,
        "korumali_dusurme_orani": korumali,
        "engellenen_saldirgan_token": len(saldirgan_istekleri) - len(kabul),
        "koruma_basarili": korumali < korumasiz or korumasiz == 0.0,
    }

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/moe_overflow.json")
print(izole_batch_raporu(v["saldirgan_istekleri"], v["kurban_istekleri"], v["kapasite"], v["kiraci_kota"]))
```
```hint
Saldırgan isteklerini uzman başına `kiraci_kota` ile sınırla, sonra `uzman_doyurma_hesabi` ve `dusurulen_token_orani` işlevlerini yeniden çağır.
```
:::

::: anlat Hata vitrini · çalışmış yanlış rapor
Yazar, kusurlu başlangıç kodlarını görünür sentetik veriyle çalıştırdı ve sonucu `outputs/yeni-ai-saldiri-61/gorunur-run-1.json` dosyasına kaydetti. Kusurlu kod taşan uzmandaki tüm tokenleri (`9`) taşmış sayar ve kiracı kotasında `engellenen_saldirgan_token=0` döndürür. Doğru kod ise kapasite 4 düşüldüğünde `5` tokenin taştığını ve kota=2 altında saldırganın `4` fazla tokeninin engellendiğini gösterir.

Bu kaydedilmiş bir hesaplama çıktısıdır, canlı model yanıtı değildir ve rapor sentetiktir. Görünür veride kota=2 uygulanmasına rağmen `korumali_dusurme_orani` neden hâlâ `0.5` kaldı (ipucu: kurbanın kendisi uzman 2'ye kaç token gönderdi)? Kendi cümlenle açıkla.
:::

::: anlat Gerçek deney: SmolLM2'den damıtılan MoE katmanında uzman doyurma, kota ve sıralama yan kanalı
Elimizde ön eğitimli bir MoE modeli yok. Final, ai-temel-28'deki yöntemle SmolLM2-135M'in 15. katmanındaki gerçek MLP bloğunu 8 uzmanlı, **top-1 (Switch)** bir MoE'ye damıtır ve yardımcı yük dengeleme kaybıyla eğitir. Modelin geri kalanı gerçek SmolLM2'dir; bu katmanda MLP yerine MoE çalışır. Batch'i sunucu kurar: önce bir kiracının tokenleri, sonra kurbanınkiler. Kapasite batch'in boyutuna göre belirlenir: $C = \lceil 2.5 \cdot T_{batch} / E \rceil$.

**Saldırgan kurbanı görmez.** Ağırlıklar açık olduğu için modeli yerelde koşar ve şu adımları izler:
1. Hizmetin bir yardım masası olduğunu bilir. Kendi yazdığı örnek bir destek isteğinde (kurbanın metni değil) en kalabalık uzmanı hedef seçer.
2. Diziyi token token **açgözlü** kurar. Her adımda 1024 aday tokenin her birini dene, o konumun gizli durumu hedef uzmana en yüksek olasılıkla yönlenen tokeni ekle.

Yazarın ilk denemesinde saldırgan 2048 aday tokenin her birini tekrarlayan diziler denedi. Taramadaki en iyi aday bile hedef uzmana hiç token gönderemedi. Seçilen dizinin 48 tokeninin hepsi başka bir uzmana gitti: tekrar eden tokenlerin gizli durumları birbirine benzer ve tek yere yığılır. Açgözlü arama ise anlamsız görünen metinlerle (örneğin `' engters around there in the pub in Chiffernach…'`) tokenlerin büyük çoğunluğunu hedefe gönderdi.

Senin üç işlevin gerçek uzman listelerinde çalışır ve bağımsız referansla karşılaştırılır. Ayrıca sunucunun **gerçek** düşürmesi batch sırasıyla uygulanır ve üç durum ölçülür:
- **Komşu:** Saldırgan yerine aynı uzunlukta zararsız bir kullanıcı var.
- **Saldırı:** Saldırganın tokenleri batch'in başında.
- **Kota:** Kiracı başına uzman kotası 2.

Her durumda kurbanın düşen token sayısı, o katmandaki göreli çıktı hatası ve dil modeli kaybı raporlanır.

Yazarın dört GPU koşusunda (batch 95 token, $C = 30$; 48 tokenlık saldırı dizisi) saldırgan tokenlerinin %87.5–94'ü hedefe gitti. Kurbanın 47 tokeninden gerçekten düşen sayılar:
- **Saldırı:** 4–22. Kurbanın hedef uzmana gönderdiği tokenlerin **hepsi** düştü.
- **Kota:** Her koşuda 0.
- **Zararsız komşu:** 0–3.

Kurbanın o katmandaki göreli çıktı hatası saldırıda 0.06–0.45, kotayla 0 idi. Hangi uzmanın hedef olduğu ve kurbanın ona kaç token gönderdiği, damıtılan MoE'ye göre koşudan koşuya değişir.

Bu koşularda saldırgan hedefi tek başına doldurduğu için gerçek düşen sayı sözleşmenin "etkilenen" sayısına eşit çıktı. Bu her zaman böyle değildir. Görev 2'nin oranı, taşan uzmana giden **bütün** kurban tokenlerini sayan bir **risk üst sınırıdır**. Saldırgan kapasiteyi tek başına dolduramazsa ya da batch sırası değişirse, gerçekte yalnız bir kısmı düşer.

**Kapasite faktörü neden 2.5?** Yazar önce değerlendirmede yaygın olan 2.0'ı kullandı ($C = 20$). Bazı koşularda kurbanın metni tek bir uzmana 22–24 token gönderdi ve kapasiteyi **kendi başına** aştı. O zaman kota bile kurbanın düşüşünü sıfırlayamadı ve yan kanal kapasitede doydu. Bir koşuda zararsız komşu, saldırgandan daha çok düşüşe yol açtı (19'a 14). Yardımcı kayıpla dengeli eğitilmiş bir MoE bile alan kayması olan bir metinde dengesiz yönlenebilir.

**Yan kanal:** Sunucu kurbanı önce sıraladığında saldırganın kendi düşen token sayısı $d = L_s - (C - n)$ olur. Buradan kurbanın hedef uzmandaki yükü $n = d - L_s + C$ çıkar. Dört koşuda da birebir doğru çıktı (4, 18, 22). Bu formül yalnız $n \le C$ iken çalışır; $n > C$ ise sonuç $C$'de doyar. Yona vd. (2024) benzer bir sıralama/eşitlik etkisini kullanarak kurban isteminin tamamını token token çıkarır.

**Komşunun girdisini tahmin etmek:** Saldırgan yardım masasına gelebilecek 8 olası isteği bilir (şifre sıfırlama, çift ödeme, kargo, adres, abonelik iptali, fatura, arızalı ürün, veri silme). Açık ağırlıklarla her uzman için o uzmana giden tek tokenlık bir **yoklama dizisi** arar (bazı uzmanlar için bulunamaz). Kurbanın isteğinden sonra her yoklamayı gönderir; kendi düşen token sayısı kurbanın o uzmandaki yükünü verir. Böylece kurbanın uzman yük dağılımının yoklanabilen kısmını çıkarır ve bunu 8 isteğin yerelde hesapladığı dağılımlarıyla karşılaştırır. Yazarın koşusunda yalnız 2 uzman yoklanabildi; bu, 8 isteğin 8'ini doğru tanımaya yetti (şans 1/8). Kiracı kotası açıkken saldırganın yoklaması kapasiteyi tüketemez, düşen sayısı kurban hakkında bilgi taşımaz ve tahmin şans düzeyine iner. Bu hesap sunucu kuralının bir modelidir: gerçek motorlarda sıralama ve gecikme gürültüsü yan kanalı zayıflatır, ama tek bir uzmanın yükü bile kısa isteklerin kimliğini ele verebilir.

**Kalite etkisi küçük, mekanizma gerçek:** Saldırı kurbanın o katmandaki çıktısını belirgin şekilde bozar. Ancak tek bir katmanda MLP'nin düşmesi artık bağlantı tarafından büyük ölçüde telafi edilir: LM kaybı en çok ~0.01 nat arttı (2.580 → 2.589). Gerçek MoE modellerinde her katman MoE'dir ve aynı saldırı her katmanda tekrar eder; bu ders o birikimi ölçmez.

**Kanıt dosyasını oku:** Soru 1: Saldırgan 48 yerine 16 token gönderseydi sözleşmenin "etkilenen" sayısı ile gerçek düşen sayı neden ayrışırdı? Batch sırası tersine dönseydi hangisi değişirdi? Soru 2: Kapasite faktörü 2.0'da kota kurbanın kendi taşmasını neden durduramadı; bunun için hangi sunucu ayarı değişmeli ve bedeli ne? Soru 3: Top-2 yönlendirmede düşen tokenin ikinci uzmanı yedek olarak nasıl davranırdı?
:::

::: gorev Gerçek deney · GPU MoE yönlendiricisinde expert overflow ve izolasyon
Önceki üç görevin `uzman_doyurma_hesabi`, `dusurulen_token_orani` ve `izole_batch_raporu` işlevlerini birleştir. Çalıştır gerçek tabloyu gösterir; Kontrol Et önce üç sözleşmeyi gizli verilerle sınar, sonra gerçek deneyi yürütür.
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
def uzman_doyurma_hesabi(saldirgan_istekleri, kurban_istekleri, kapasite):
    top = saldirgan_istekleri + kurban_istekleri
    yuk = {u: top.count(u) for u in sorted(set(top))}
    tasan = [u for u, s in yuk.items() if s > kapasite]
    return {"yuk_tablosu": yuk, "tasan_uzmanlar": tasan, "toplam_tasan_token": sum(yuk[u] for u in tasan)}

def dusurulen_token_orani(kurban_uzmanlari, tasan_uzmanlar):
    ortak = sorted(set(kurban_uzmanlari) & set(tasan_uzmanlar))
    return {"etkilenen_token_sayisi": len(ortak), "dusurme_orani": len(ortak) / len(kurban_uzmanlari), "etkilenen_uzmanlar": ortak}

def izole_batch_raporu(saldirgan_istekleri, kurban_istekleri, kapasite, kiraci_kota):
    return {"korumasiz_dusurme_orani": 0.5, "korumali_dusurme_orani": 0.5, "engellenen_saldirgan_token": 0, "koruma_basarili": False}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_61 as D
    D.goster(uzman_doyurma_hesabi, dusurulen_token_orani, izole_batch_raporu)
```
```test
import ai_lab, math
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('referans_doyurma', 'referans_dusurme', 'referans_izole', 'kanit_yaz', '_yakin'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
uzman_doyurma_hesabi = need("uzman_doyurma_hesabi")
dusurulen_token_orani = need("dusurulen_token_orani")
izole_batch_raporu = need("izole_batch_raporu")
def sinama1(f):
    try:
        s = [2, 2, 2, 0]; k = [2, 2, 1]; old = (list(s), list(k))
        r = f(s, k, 3)
        if (s, k) != old or r != {"yuk_tablosu": {0: 1, 1: 1, 2: 5}, "tasan_uzmanlar": [2], "toplam_tasan_token": 2}: return False
        if f([], [1, 1], 2) != {"yuk_tablosu": {1: 2}, "tasan_uzmanlar": [], "toplam_tasan_token": 0}: return False
        for bad in ((None, [1], 2), ([], [], 2), ([-1], [1], 2), ([True], [1], 2), ([1], [1], 0)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama1(uzman_doyurma_hesabi), "uzman yük tablosu ve taşan token toplamı")
for ad, mut in [("kapasite çıkarılmadı", lambda s, k, c: dict(uzman_doyurma_hesabi(s, k, c), toplam_tasan_token=sum(v for v in uzman_doyurma_hesabi(s, k, c)["yuk_tablosu"].values() if v > c))), ("taşan >= kapasite", lambda s, k, c: dict(uzman_doyurma_hesabi(s, k, c), tasan_uzmanlar=[u for u, v in uzman_doyurma_hesabi(s, k, c)["yuk_tablosu"].items() if v >= c])), ("yalnız saldırgan sayıldı", lambda s, k, c: uzman_doyurma_hesabi(s, [], c) if s else uzman_doyurma_hesabi(s, k, c))]:
    kontrol(not sinama1(mut), "mutant reddedildi: " + ad)
def sinama2(f):
    try:
        k = [2, 2, 1, 3, 2, 0]; t = [2, 5]; old = (list(k), list(t))
        if f(k, t) != {"etkilenen_token_sayisi": 3, "dusurme_orani": 0.5, "etkilenen_uzmanlar": [2]} or (k, t) != old: return False
        if f([1, 2], []) != {"etkilenen_token_sayisi": 0, "dusurme_orani": 0.0, "etkilenen_uzmanlar": []}: return False
        for bad in (([], [1]), (None, [1]), ([True], [1]), ([1], [-1])):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama2(dusurulen_token_orani), "tekrarlı kurban token sayımı ve düşürme oranı")
for ad, mut in [("küme boyutu sayıldı", lambda k, t: dict(dusurulen_token_orani(k, t), etkilenen_token_sayisi=len(set(k) & set(t)), dusurme_orani=len(set(k) & set(t)) / len(k))), ("oran hep 0", lambda k, t: dict(dusurulen_token_orani(k, t), dusurme_orani=0.0)), ("tüm taşanları döndür", lambda k, t: dict(dusurulen_token_orani(k, t), etkilenen_uzmanlar=sorted(set(t))))]:
    kontrol(not sinama2(mut), "mutant reddedildi: " + ad)
def sinama3(f):
    try:
        s = [2, 2, 2, 2, 0]; k = [2, 2, 1, 3]; old = (list(s), list(k))
        if f(s, k, 4, 2) != {"korumasiz_dusurme_orani": 0.5, "korumali_dusurme_orani": 0.0, "engellenen_saldirgan_token": 2, "koruma_basarili": True} or (s, k) != old: return False
        if f([1], [2, 3], 4, 2) != {"korumasiz_dusurme_orani": 0.0, "korumali_dusurme_orani": 0.0, "engellenen_saldirgan_token": 0, "koruma_basarili": True}: return False
        if f([0, 0], [0], 2, 1)["engellenen_saldirgan_token"] != 1 or f([], [0], 1, 1)["engellenen_saldirgan_token"] != 0: return False
        for bad in ((None, [1], 4, 2), ([1], [], 4, 2), ([1], [1], 0, 1), ([1], [1], True, 1), ([1], [1], 4, 0), ([1], [1], 4, 5), ([1], [1], 4, True)):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama3(izole_batch_raporu), "korumasız/korumalı düşürme oranı ve kiracı kotası")
for ad, mut in [("kota uygulanmadı", lambda s, k, c, q: dict(izole_batch_raporu(s, k, c, q), korumali_dusurme_orani=izole_batch_raporu(s, k, c, q)["korumasiz_dusurme_orani"], engellenen_saldirgan_token=0)), ("koruma hep False", lambda s, k, c, q: dict(izole_batch_raporu(s, k, c, q), koruma_basarili=False)), ("engellenen 0", lambda s, k, c, q: dict(izole_batch_raporu(s, k, c, q), engellenen_saldirgan_token=0))]:
    kontrol(not sinama3(mut), "mutant reddedildi: " + ad)
# farksal tarama (final)
import importlib as _il
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_R = _il.import_module('sandbox.ai_gercek_ai_saldiri_61')
for _ad, _ref, _taban, _toh in (
    ('uzman_doyurma_hesabi', 'referans_doyurma', ([2, 2, 2, 2, 2, 0, 2, 1], [2, 2, 1, 3, 2, 0], 4), 3795),
    ('dusurulen_token_orani', 'referans_dusurme', ([2, 2, 1, 3, 2, 0], [2]), 3932),
    ('izole_batch_raporu', 'referans_izole', ([2, 2, 2, 2, 2, 0, 2, 1], [2, 2, 1, 3, 2, 0], 4, 2), 3577),
):
    _t, _g = _ff(need(_ad), getattr(_R, _ref), _taban, tohum=_toh)
    kontrol(_t, "farksal tarama (" + _ad + "): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
if not all(checks): stop()
from sandbox import ai_gercek_ai_saldiri_61 as D
try: r = D.deney(uzman_doyurma_hesabi, dusurulen_token_orani, izole_batch_raporu)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r["doyurma_ayni"], "SmolLM2'den damıtılan MoE'nin gerçek yönlendirmesinde uzman doyurma hesabı bağımsız referansla aynı")
kontrol(r["dusurme_ayni"], "gerçek yönlendirmede düşürülen token oranı bağımsız referansla aynı")
kontrol(r["izole_ayni"], "gerçek yönlendirmede izole batch raporu bağımsız referansla aynı")
# Rastgele model davranışına başarı tabanı dayatılmaz. Gerçek rotalar bağımsız
# dispatch modeliyle yeniden hesaplanır; yanlış öğrenci hesapları yukarıda reddedilir.
_s, _k, _n = r["saldirgan_uzmanlari"], r["kurban_uzmanlari"], r["komsu_uzmanlari"]
_C, _q, _hedef = r["kapasite"], r["ayarlar"]["kiraci_kota"], r["hedef_uzman"]
def _dispatch(sira, kota=None):
    global_yuk, kiraci_yuk, dusen = {}, {}, []
    for tenant, expert in sira:
        key = (tenant, expert)
        kota_doldu = kota is not None and tenant == "saldirgan" and kiraci_yuk.get(key, 0) >= kota
        if kota_doldu:
            dusen.append(True)
            continue
        kiraci_yuk[key] = kiraci_yuk.get(key, 0) + 1
        dolu = global_yuk.get(expert, 0) >= _C
        dusen.append(dolu)
        if not dolu:
            global_yuk[expert] = global_yuk.get(expert, 0) + 1
    return dusen
_kurban = [("kurban", u) for u in _k]
for _ad, _rota, _kota in (("komsu", _n, None), ("saldiri", _s, None), ("kota", _s, _q)):
    _sira = [("saldirgan", u) for u in _rota] + _kurban
    _bek = sum(_dispatch(_sira, _kota)[-len(_k):])
    kontrol(r["gercek_dusen"][_ad] == _bek, "gerçek rota bağımsız dispatch hesabıyla aynı: " + _ad)
kontrol(abs(r["saldirgan_hedef_orani"] - _s.count(_hedef) / len(_s)) < 1e-12, "hedef yönlendirme oranı gerçek tokenlardan hesaplandı")
# Kurban önce sıralandığında saldırganın kendi düşen token sayısı bağımsız hesaplanır.
_mask = _dispatch(_kurban + [("saldirgan",u) for u in _s])[len(_k):]
_dusen = sum(int(d) for u,d in zip(_s,_mask) if u == _hedef)
_cikarilan = _dusen - _s.count(_hedef) + _C if _dusen > 0 else None
kontrol(r["yan_kanal"]["saldirganin_gordugu_dusen"] == _dusen and r["yan_kanal"]["cikarilan_kurban_yuku"] == _cikarilan, "yan kanal yük tahmini gözlenen düşürmeden yeniden üretildi")
_gc = r["girdi_cikarimi"]
kontrol(all(type(_gc[k]) is int and 0 <= _gc[k] <= _gc["aday"] for k in ("dogru_kotasiz", "dogru_kotali")) and _gc["aday"] > 0, "girdi çıkarımı başarı/başarısızlık sayıları ve payda kaydedildi")
kontrol(all(math.isfinite(v) for v in r["kurban_lm_kaybi"].values()), "gerçek model kayıpları sonlu ve kayıtlı")
ai_lab.kanit_yaz("ai-saldiri-61-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-saldiri-61", "deney": r})
```
```solution
import ai_lab
import math
def _liste(lst, bos_izin=True):
    if not isinstance(lst, list) or (not bos_izin and not lst):
        raise ValueError("liste")
    for u in lst:
        if isinstance(u, bool) or not isinstance(u, int) or u < 0:
            raise ValueError("uzman")

def uzman_doyurma_hesabi(saldirgan_istekleri, kurban_istekleri, kapasite):
    _liste(saldirgan_istekleri, True); _liste(kurban_istekleri, True)
    if not saldirgan_istekleri and not kurban_istekleri:
        raise ValueError("boş")
    if isinstance(kapasite, bool) or not isinstance(kapasite, int) or kapasite < 1:
        raise ValueError("kapasite")
    say = {}
    for u in saldirgan_istekleri + kurban_istekleri:
        say[u] = say.get(u, 0) + 1
    yuk = {u: say[u] for u in sorted(say)}
    tasan = [u for u, s in yuk.items() if s > kapasite]
    top_t = sum(s - kapasite for s in yuk.values() if s > kapasite)
    return {"yuk_tablosu": yuk, "tasan_uzmanlar": tasan, "toplam_tasan_token": top_t}

def dusurulen_token_orani(kurban_uzmanlari, tasan_uzmanlar):
    _liste(kurban_uzmanlari, False)
    if not isinstance(tasan_uzmanlar, (list, set, frozenset)):
        raise ValueError("tasan")
    tk = set()
    for u in tasan_uzmanlar:
        if isinstance(u, bool) or not isinstance(u, int) or u < 0:
            raise ValueError("tasan eleman")
        tk.add(u)
    etk = sum(1 for u in kurban_uzmanlari if u in tk)
    return {"etkilenen_token_sayisi": etk, "dusurme_orani": etk / len(kurban_uzmanlari), "etkilenen_uzmanlar": sorted({u for u in kurban_uzmanlari if u in tk})}

def izole_batch_raporu(saldirgan_istekleri, kurban_istekleri, kapasite, kiraci_kota):
    _liste(saldirgan_istekleri, True); _liste(kurban_istekleri, False)
    if isinstance(kapasite, bool) or not isinstance(kapasite, int) or kapasite < 1:
        raise ValueError("kapasite")
    if isinstance(kiraci_kota, bool) or not isinstance(kiraci_kota, int) or not 1 <= kiraci_kota <= kapasite:
        raise ValueError("kota")
    ham = uzman_doyurma_hesabi(saldirgan_istekleri, kurban_istekleri, kapasite)
    korumasiz = dusurulen_token_orani(kurban_istekleri, ham["tasan_uzmanlar"])["dusurme_orani"]
    sayac = {}; kabul = []
    for u in saldirgan_istekleri:
        if sayac.get(u, 0) < kiraci_kota:
            sayac[u] = sayac.get(u, 0) + 1
            kabul.append(u)
    kor = uzman_doyurma_hesabi(kabul, kurban_istekleri, kapasite)
    korumali = dusurulen_token_orani(kurban_istekleri, kor["tasan_uzmanlar"])["dusurme_orani"]
    return {
        "korumasiz_dusurme_orani": korumasiz,
        "korumali_dusurme_orani": korumali,
        "engellenen_saldirgan_token": len(saldirgan_istekleri) - len(kabul),
        "koruma_basarili": korumali < korumasiz or korumasiz == 0.0,
    }

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_61 as D
    D.goster(uzman_doyurma_hesabi, dusurulen_token_orani, izole_batch_raporu)
```
```hint
Üç işlevi birleştir; `izole_batch_raporu` içinde her uzman için saldırgan sayacını `kiraci_kota` ile sınırla.
```
:::

::: anlat Sınır
Bu ders top-1 yönlendirmeli ve sabit kapasite faktörlü `Mixture-of-Experts` katmanlarında uzman taşmasını inceler. Gerçek deneydeki MoE ön eğitimli değildir: SmolLM2'nin yalnız 15. katmanındaki MLP, küçük bir derlemde damıtılmıştır ve modelin diğer katmanları yoğundur. Bu yüzden kalite etkisi tek katmanla sınırlıdır. Sunucu kuralı (batch sırası, $C = \lceil 2.5\, T/E \rceil$, kiracı kotası) yazarın modelidir; gerçek çıkarım motorları sıralamayı, kapasiteyi ve düşen tokenleri farklı yönetebilir. Saldırgan beyaz kutudur (açık ağırlıklar); kapalı bir modelde aynı uzmanı bulmak çok daha fazla sorgu ister. Yan kanal, saldırganın kendi düşen token sayısını gözlediğini varsayar. Token düşürmeyen (`dropless`, MegaBlocks) çekirdeklerdeki gecikme yan kanalları kapsanmaz.
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
Expert kapasitesi C, yük L ise taşan sayı max(0,L−C) olur. Kurbanın her tokenının taştığını söylemek için batch sırası ve dispatch kuralı gerekir; yalnız taşan expert listesinden türetilen oran bir etkilenme vekilidir. Saldırgan kotası kurbana yer bırakabilir ama C kurbanın kendi yükünden küçükse sıfır kayıp garanti etmez. Damıtılmış tek MoE katmanı gerçek öğrenilmiş hesap yapar; ön eğitimli çok katmanlı MoE sonucu değildir.

Önkoşul ve yol köprüsü: ai-saldiri-59 paylaşılan çıkarım gözlemini; ai-savunma-31 kiracı kotasının maliyetini bağlar.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| Taşan experte giden her token kesin düşer | Hangi tokenın düştüğünü dispatch sırası belirler |

Dinleyiciye sor: Bu dersin kanıtı hangi gözlemi gösterir; hangi daha güçlü iddia için ek deney gerekir? Kanıtın model, ayar, veri kökeni ve hata alanlarını açarak cevabını gerekçelendir.
:::
