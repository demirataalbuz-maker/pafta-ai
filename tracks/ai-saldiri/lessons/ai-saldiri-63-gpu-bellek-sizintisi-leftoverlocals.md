---
id: ai-saldiri-63
title: Paylaşımlı GPU Bellek Sızıntısı (LeftoverLocals) · Kalıntı Vektör Kurtarma ve Tensör Temizleme
summary: Sıfırlanmamış yerel GPU tamponlarındaki artık enerjiyi ölç; kalıntı aktivasyon vektöründen kurbanın token gömmelerini kosinüs eşleşmesiyle kurtar ve tensör temizleme (scrubbing) ile sızıntıyı GPU'da sıfırla.
esleme: ai-saldiri-51, ai-saldiri-57, ai-savunma-40
timeout: 60
---

::: anlat Çok kiracılı GPU çıkarımında önceki oturumun verisi bellekte neden kalır?
**Deneyin tam sınırı:** Finalde aynı süreç içinde bilerek oluşturulan bir PyTorch tensor tamponu okunur ve temizlenir. Gerçek tensor hesabı yapılır; başka bir sürecin GPU local memory verisini yetkisiz okumaya veya CVE-2023-4969 replikasyonuna gidilmez. Gerçek LeftoverLocals için kaynak: [Trail of Bits](https://blog.trailofbits.com/2024/01/16/leftoverlocals-listening-to-llm-responses-through-leaked-gpu-local-memory/).

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| `LeftoverLocals` (CVE-2023-4969), paylaşımlı GPU/VRAM üzerinde bir çekirdek (`kernel`) sonlandığında yerel belleğin (`local memory / LDS`) sıfırlanmaması yüzünden sonraki kiracının kurbanın matris çarpımı veya embedding çıktılarını doğrudan okumasıdır (Trail of Bits, 2024) | İlk üç görev: `veri/leftover.json` içindeki **sentetik** tampon ve gömmeler. Final: gerçek SmolLM2-135M gömme aktivasyonları; tek süreçli çok kiracılı bir sunucuda PyTorch'un önbellekli GPU ayırıcısının serbest bıraktığı bloğu saldırganın `torch.empty` ile alması | Süreçler arası LDS sızıntısını (AMD/Apple/Qualcomm sürücüleri) ölçmez; aynı mekanizmanın yazılım katmanındaki karşılığını gerçek bellekte ölçer |
| Güvenli bellek sıfırlama (`tensor scrubbing / zero-initialization`) tahsis edilen her tensörü `0.0` ile doldurarak artık enerjiyi tamamen yok eder | Tensör enerjisi, sözlük embedding kosinüs hizalaması ve bellek temizliği sözleşmesi | Güvenilmeyen bir sürücünün sıfırlama talimatını atladığı donanım kusurlarını yakalayamaz |

> [!NOT]
> Görevler `veri/leftover.json` dosyasını okur; dosya sentetiktir. Setup her Çalıştır/Kontrol Et adımında geçici kopya kurar; değişiklikler taşınmaz, **kalıcılık yoktur**. Ekranda ayrı dosya görüntüleyici yoktur; içeriği görmek için `print` kullan. Gizli testler ayrıdır. Final yeni model indirmez ve GPU varsa onu kullanır.

GPU'lar yüksek verim elde etmek için matris çarpımlarını yerel paylaşımlı belleğe (`LDS / Shared Memory`) yükler. Bir kiracının LLM çıkarımı bittiğinde bellek tahsisi serbest bırakılır; ancak GPU bellek denetleyicisi performans kaygısıyla bu alanı sıfırlamazsa (`uninitialized memory`), aynı donanımı paylaşan ikinci bir kiracı bu adresten eski oturumun aktivasyon vektörlerini okuyabilir (`LeftoverLocals`, Trail of Bits, 2024).

**Saldırgan ne dener?** Saldırgan rastgele veya sıfırlanmamış bellek ayırır (`torch.empty` gibi) ve içindeki değerlerin ortalama enerjisini ($\frac{1}{N} \sum x_i^2$) ölçer. Eğer enerji sıfırdan belirgin şekilde büyükse, bu kalıntı vektörleri bilinen kelime gömmeleriyle (`embedding dictionary`) kosinüs benzerliği üzerinden karşılaştırarak kurbanın az önce ürettiği gizli token dizisini kurtarır.

**Aynı sorun yazılımda da var.** PyTorch, CUDA/ROCm'da her `cudaMalloc` çağrısının maliyetinden kaçınmak için **önbellekli ayırıcı** (`caching allocator`) kullanır: `del tensor` belleği sürücüye geri vermez, havuzda tutar ve aynı boyuttaki bir sonraki isteğe **sıfırlamadan** verir. 1 MB'tan büyük istekler "büyük blok" havuzundan karşılanır; aynı boyutta ardışık bir istek çoğu zaman tam aynı segmenti alır. Birden çok kullanıcının isteğini **tek bir süreçte** sırayla işleyen bir çıkarım sunucusunda bir önceki kullanıcının aktivasyonları, sonraki isteğin `torch.empty` ile aldığı tensörün içinde durur. `torch.empty` "boş" demek değildir; "başlatılmamış" demektir.

**Savunma neden kırılır?** Güvenlik duvarları ve yetkilendirme katmanları API seviyesinde çalışır; ancak sızıntı donanım/sürücü ya da ayırıcı düzeyindeki bellek paylaşımından kaynaklanır. Çözüm, işlem bittiğinde tamponu serbest bırakmadan önce sıfırlamak (`tensor scrubbing`) ya da yeni tahsiste `torch.zeros` kullanmaktır. İnce nokta: yalnız son tamponu sıfırlamak yetmeyebilir. Aynı veriyi taşıyan **ara tensörler** (ör. `E[ids] * 1.0` gibi bir işlemin ara kopyası) da havuza sıfırlanmadan döner; savunma bütün geçici kopyaları kapsamalıdır. `torch.cuda.empty_cache()` blokları sürücüye geri verir ama sürücü de belleği sıfırlamak zorunda değildir; kriptografik anlamda silme sayılmaz.

**Görev 1'de sık tuzaklar:** Mutlak değer toleransını (`beklenen_sifir_tol`) unutarak `x != 0` kontrolü yapmak, kayan nokta gürültüsünü sızıntı sanabilir; ortalama enerjide vektör uzunluğuna bölmeyi atlamamak gerekir.

Kaynaklar: [Khlaaf ve Sorensen, 2024 - LeftoverLocals: Listening to LLM responses through leaked GPU local memory](https://blog.trailofbits.com/2024/01/16/leftoverlocals-listening-to-llm-responses-through-leaked-gpu-local-memory/). Bu dersteki bütün sayılar yalnız yerel kanıttan gelir.

Köprü: ai-saldiri-57 logit çıktılarından model çalmayı inceler; bu ders doğrudan GPU belleğindeki kalıntı aktivasyonlardan girdi sızdırmayı modeller.
:::

::: tahmin Kalıntı vektörden en yakın tokeni bulmak
Çıktıyı tahmin et, sonra Çalıştır ile karşılaştır.
```python
import math
kalinti = [0.8, -0.6]
sozluk = {"onay": [0.8, -0.6], "red": [-0.8, 0.6]}
nk = math.sqrt(sum(x*x for x in kalinti))
for k, v in sozluk.items():
    nv = math.sqrt(sum(x*x for x in v))
    kos = sum(a*b for a, b in zip(kalinti, v)) / (nk * nv)
    print(f"{k}: kosinus={round(kos, 2)}")
```
???
```cikti
onay: kosinus=1.0
red: kosinus=-1.0
```
Tahmininle gerçek çıktı arasındaki farkı tezgâhta yorum satırı olarak yaz: kalıntı vektör gürültülü olduğunda (örneğin `[0.78, -0.62]`) kosinüs benzerliği 1.0'a ne kadar yakın kalır? Sonra üç kusurlu başlangıç kodunu çalıştır ve her birinin neyi kaçırdığını önce kendin teşhis et; açıklama çözümün ardından gelir.
:::

::: gorev 1 · Kalıntı enerji oranı
`kalinti_enerji_orani(tampon, beklenen_sifir_tol)`: `tampon` en az bir elemanlı, bool olmayan sonlu sayılardan oluşan liste; `beklenen_sifir_tol` bool olmayan, `>= 0` sonlu sayı. `dolu = abs(x) > beklenen_sifir_tol` olan eleman sayısı; `enerji = sum(x*x for x in tampon) / len(tampon)`. `{"doluluk_orani": float(dolu/n), "ortalama_enerji": float(enerji), "sizinti_var": dolu > 0}` döndür. Geçersiz girdide `ValueError`.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-63")
```
```starter
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def kalinti_enerji_orani(tampon, beklenen_sifir_tol):
    return {"doluluk_orani": 0.0, "ortalama_enerji": 0.0, "sizinti_var": False}

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/leftover.json")
print(kalinti_enerji_orani(v["kalinti_tampon"], v["beklenen_sifir_tol"]))
```
```test
def sinama1(f):
    try:
        t = [0.8, -0.6, 1e-8, 0.5]; old = list(t)
        r = f(t, 1e-6)
        if r["doluluk_orani"] != 0.75 or abs(r["ortalama_enerji"] - 0.3125) > 1e-6 or r["sizinti_var"] is not True or t != old:
            return False
        if f([0.0, 0.0], 1e-6) != {"doluluk_orani": 0.0, "ortalama_enerji": 0.0, "sizinti_var": False}:
            return False
        for bad in ((None, 1e-6), ([], 1e-6), (t, -0.1), (t, True), ([True], 1e-6), (t, float("nan"))):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
ok(sinama1(kalinti_enerji_orani), "enerji ve doluluk hesabı, tolerans ve geçersiz girdi")
for ad, mut in [
    ("hep sıfır", lambda t, s: {"doluluk_orani": 0.0, "ortalama_enerji": 0.0, "sizinti_var": False}),
    ("tolerans yok", lambda t, s: dict(kalinti_enerji_orani(t, 0.0))),
    ("enerji kare yerine mutlak", lambda t, s: dict(kalinti_enerji_orani(t, s), ortalama_enerji=sum(abs(x) for x in t)/len(t)))
]:
    ok(not sinama1(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(kalinti_enerji_orani, _il.import_module('ai_gercek_ai_saldiri_63').referans_enerji, ([0.8, -0.6, 0.0, 0.5], 1e-06), tohum=3253)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def kalinti_enerji_orani(tampon, beklenen_sifir_tol):
    if not isinstance(tampon, list) or not tampon: raise ValueError("tampon")
    for x in tampon:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x): raise ValueError("sayı")
    if isinstance(beklenen_sifir_tol, bool) or not isinstance(beklenen_sifir_tol, (int, float)) or not math.isfinite(beklenen_sifir_tol) or beklenen_sifir_tol < 0:
        raise ValueError("tol")
    n = len(tampon)
    dolu = sum(1 for x in tampon if abs(x) > beklenen_sifir_tol)
    enerji = sum(x * x for x in tampon) / n
    return {"doluluk_orani": float(dolu / n), "ortalama_enerji": float(enerji), "sizinti_var": dolu > 0}

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/leftover.json")
print(kalinti_enerji_orani(v["kalinti_tampon"], v["beklenen_sifir_tol"]))
```
```hint
Her elemanın mutlak değerini `beklenen_sifir_tol` ile karşılaştır; kareler toplamını eleman sayısına böl.
```
:::

::: anlat Kalıntı vektörden token kurtarma
Kalıntı aktivasyon vektörü $\mathbf{v}$ ile sözlükteki her adayın embedding vektörü $\mathbf{e}_i$ arasındaki kosinüs benzerliği:
$$\cos(\mathbf{v}, \mathbf{e}_i) = \frac{\mathbf{v} \cdot \mathbf{e}_i}{\|\mathbf{v}\|_2 \|\mathbf{e}_i\|_2}$$
En yüksek benzerliğe sahip token seçilir. Eşitlik durumunda alfabetik sıralama (`min(..., key=lambda k: (-skor[k], k))`) uygulanır.
:::

::: gorev 2 · Gömme kurtarma eşleşmesi
`gomme_kurtarma_eslesmesi(kalinti_vektor, sozluk_gommeleri)`: `kalinti_vektor` sıfırdan farklı uzunlukta ve sıfır olmayan normda bool olmayan sonlu sayı listesi; `sozluk_gommeleri` string anahtarlı ve aynı boyutta sıfır olmayan vektör değerlerine sahip sözlük. En yüksek kosinüs benzerliğini veren tokeni bul. `{"kurtarilan_token": str, "kosinus_benzerligi": float, "guvenli_eslesme": bool(en_kos >= 0.85)}` döndür. Geçersiz girdide `ValueError`.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-63")
```
```starter
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def gomme_kurtarma_eslesmesi(kalinti_vektor, sozluk_gommeleri):
    return {"kurtarilan_token": "yok", "kosinus_benzerligi": 0.0, "guvenli_eslesme": False}

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/leftover.json")
print(gomme_kurtarma_eslesmesi(v["kalinti_tampon"], v["sozluk_gommeleri"]))
```
```test
def sinama2(f):
    import copy
    try:
        v = [0.8, -0.6, 0.0, 0.5]; s = {"red": [-0.7, 0.5, 0.2, -0.1], "onay": [0.8, -0.6, 0.0, 0.5]}; old = (list(v), copy.deepcopy(s))
        r = f(v, s)
        if r["kurtarilan_token"] != "onay" or abs(r["kosinus_benzerligi"] - 1.0) > 1e-9 or r["guvenli_eslesme"] is not True or (v, s) != old:
            return False
        if f(v, {"a": [0.0, 0.0, 1.0, 0.0]})["guvenli_eslesme"] is not False:
            return False
        for bad in ((None, s), ([], s), ([0.0, 0.0], {"a": [1.0, 0.0]}), (v, None), (v, {}), (v, {"a": [1.0]}), (v, {"a": [0.0, 0.0, 0.0, 0.0]})):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
ok(sinama2(gomme_kurtarma_eslesmesi), "kosinus benzerligi, en iyi token secimi ve gecersiz girdi")
for ad, mut in [
    ("hep ilk token", lambda v, s: {"kurtarilan_token": next(iter(s)), "kosinus_benzerligi": 1.0, "guvenli_eslesme": True}),
    ("normsuz iç çarpım", lambda v, s: {"kurtarilan_token": max(s, key=lambda k: sum(a*b for a,b in zip(v, s[k]))), "kosinus_benzerligi": 0.9, "guvenli_eslesme": True}),
    ("güvenli eşleşme hep False", lambda v, s: dict(gomme_kurtarma_eslesmesi(v, s), guvenli_eslesme=False))
]:
    ok(not sinama2(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(gomme_kurtarma_eslesmesi, _il.import_module('ai_gercek_ai_saldiri_63').referans_kurtarma, ([0.8, -0.6, 0.0, 0.5], {'onay': [0.8, -0.6, 0.0, 0.5], 'red': [-0.7, 0.5, 0.2, -0.1], 'bekle': [0.1, 0.2, 0.9, -0.3]}), tohum=3705)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
# Birim normlu vektörle 0.85 eşik eşitliği ve iki yanı.
for _c in (0.849, 0.85, 0.851):
    _r = gomme_kurtarma_eslesmesi([1.0, 0.0], {"tek": [_c, math.sqrt(1.0 - _c * _c)]})
    ok(_r["guvenli_eslesme"] is (_c >= 0.85), "kosinüs eşik sınırı: " + str(_c))
```
```solution
import math
def gomme_kurtarma_eslesmesi(kalinti_vektor, sozluk_gommeleri):
    if not isinstance(kalinti_vektor, list) or not kalinti_vektor: raise ValueError("vektor")
    for x in kalinti_vektor:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x): raise ValueError("sayı")
    nk = math.sqrt(sum(x * x for x in kalinti_vektor))
    if nk == 0: raise ValueError("sıfır norm")
    if not isinstance(sozluk_gommeleri, dict) or not sozluk_gommeleri: raise ValueError("sozluk")
    d = len(kalinti_vektor)
    skorlar = {}
    for tok, emb in sozluk_gommeleri.items():
        if not isinstance(tok, str) or not tok or not isinstance(emb, list) or len(emb) != d: raise ValueError("eleman")
        for x in emb:
            if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x): raise ValueError("sayı")
        ne = math.sqrt(sum(x * x for x in emb))
        if ne == 0: raise ValueError("sıfır gömme")
        skorlar[tok] = sum(a * b for a, b in zip(kalinti_vektor, emb)) / (nk * ne)
    en_iyi = min(skorlar, key=lambda k: (-skorlar[k], k))
    en_kos = float(skorlar[en_iyi])
    return {"kurtarilan_token": en_iyi, "kosinus_benzerligi": en_kos, "guvenli_eslesme": en_kos >= 0.85}

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/leftover.json")
print(gomme_kurtarma_eslesmesi(v["kalinti_tampon"], v["sozluk_gommeleri"]))
```
```hint
Her adayın kosinüs benzerliğini hesapla; `(-skor, token)` anahtarıyla en yüksek skora sahip olanı seç.
```
:::

::: anlat Güvenli bellek sıfırlama (Tensor Scrubbing)
Bir tensör havuzu boşaltıldığında, elemanların sıfırlarla ezilmesi gerekir. Böylece sonraki kiracı belleği okuduğunda artık enerji tam olarak `0.0` çıkar.
:::

::: gorev 3 · Güvenli bellek temizle
`guvenli_bellek_temizle(tampon_listesi)`: `tampon_listesi` sayılardan oluşan listelerin boş olmayan listesi. Her tamponu aynı boyutta `0.0` değerleriyle sıfırla; sıfırdan farklı silinen eleman sayısını ve kalan toplam enerjiyi hesapla. `{"temiz_tamponlar": [[0.0, ...], ...], "temizlenen_eleman_sayisi": int, "kalan_enerji": float(0.0)}` döndür. Geçersiz girdide `ValueError`.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-63")
```
```starter
# KUSURLU BAŞLANGIÇ KODU: teşhis et; kusuru çözümü açmadan önce tahmin et.
def guvenli_bellek_temizle(tampon_listesi):
    return {"temiz_tamponlar": tampon_listesi, "temizlenen_eleman_sayisi": 0, "kalan_enerji": 1.0}

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/leftover.json")
print(guvenli_bellek_temizle(v["tampon_listesi"]))
```
```test
def sinama3(f):
    import copy
    try:
        t = [[0.8, -0.6, 0.0, 0.5], [0.0, 1.2, -0.4]]; old = copy.deepcopy(t)
        r = f(t)
        if r["temiz_tamponlar"] != [[0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0]] or r["temizlenen_eleman_sayisi"] != 5 or r["kalan_enerji"] != 0.0 or t != old:
            return False
        for bad in (None, [], [[]], [None], [[True]], [[float("nan")]]):
            try: f(bad); return False
            except (ValueError, TypeError): pass
        return True
    except Exception: return False
ok(sinama3(guvenli_bellek_temizle), "tampon sıfırlama, silinen eleman sayısı ve geçersiz girdi")
for ad, mut in [
    ("sıfırlama yok", lambda t: {"temiz_tamponlar": list(t), "temizlenen_eleman_sayisi": 0, "kalan_enerji": 1.0}),
    ("kalan enerji sıfır değil", lambda t: dict(guvenli_bellek_temizle(t), kalan_enerji=0.5)),
    ("silinen sayısı yanlış", lambda t: dict(guvenli_bellek_temizle(t), temizlenen_eleman_sayisi=0))
]:
    ok(not sinama3(mut), "mutant reddedildi: " + ad)
import importlib as _il, sys as _sys
_sys.modules.setdefault("ai_lab", _il.import_module("ai_gercek_lab"))
from ai_fark_fuzz import fark_fuzz as _ff
_t, _g = _ff(guvenli_bellek_temizle, _il.import_module('ai_gercek_ai_saldiri_63').referans_temizle, ([[0.8, -0.6, 0.0, 0.5], [0.0, 1.2, -0.4]],), tohum=3478)
ok(_t, "farksal tarama: bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
```
```solution
import math
def guvenli_bellek_temizle(tampon_listesi):
    if not isinstance(tampon_listesi, list) or not tampon_listesi: raise ValueError("liste")
    for t in tampon_listesi:
        if not isinstance(t, list) or not t: raise ValueError("tampon")
        for x in t:
            if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x): raise ValueError("sayı")
    temiz = [[0.0 for _ in t] for t in tampon_listesi]
    silinen = sum(1 for t in tampon_listesi for x in t if x != 0)
    kalan = sum(x * x for t in temiz for x in t)
    return {"temiz_tamponlar": temiz, "temizlenen_eleman_sayisi": silinen, "kalan_enerji": float(kalan)}

from ai_saldiri_veri import json_yukle
v = json_yukle("veri/leftover.json")
print(guvenli_bellek_temizle(v["tampon_listesi"]))
```
```hint
Her tampon için sıfır listesi oluştur; eski tamponlardaki sıfır olmayan elemanları say.
```
:::

::: anlat Hata vitrini · çalışmış yanlış rapor
Yazar, kusurlu başlangıç kodlarını görünür sentetik veriyle gerçekten çalıştırdı ve sonucu `outputs/yeni-ai-saldiri-63/gorunur-run-1.json` dosyasına kaydetti. Kusurlu kod sıfırlanmamış tamponu `sizinti_var=False` ve `doluluk_orani=0.0` olarak gösterir. Doğru kod ise `%75` doluluk oranını yakalar ve kurbanın tokenini `%100` kosinüs benzerliğiyle kurtarır.
:::

::: anlat Gerçek deney: önbellekli GPU ayırıcısından kurbanın sır cümlesini okumak
Final, yerel önbellekteki gerçek **SmolLM2-135M** modelini yükler (indirme yok) ve aynı süreçte iki kiracı canlandırır:

1. **Kurban** isteği, içinde sentetik bir sır cümlesi (`The vault PIN is 4831 and the backup phrase is copper lantern.`) bulunan 512 tokenlık bir batch'in gerçek gömme aktivasyonlarını GPU'da bir tampona yazar (~1,2 MB), işi bitince tamponu `del` ile serbest bırakır.
2. **Saldırgan** isteği hemen ardından aynı boyutta `torch.empty` tensörü ister ve içini okur. Deney, saldırganın gerçekten kurbanın bloğunu (aynı adres) alıp almadığını kaydeder. Senin `kalinti_enerji_orani` işlevin kalıntı satırlarının enerjisini ölçer; `gomme_kurtarma_eslesmesi` her satırı 1.000 tokenlık bir aday sözlükte (gizli tokenlar dahil), modelin gerçek gömme tablosuna kosinüsle eşler. Deney ayrıca tam sözlükte (49.152 token) GPU üzerinde aynı eşlemeyi yapıp kurtarılan metni yazar.
3. Aynı akış ikinci kez koşar; bu kez kurban tamponu serbest bırakmadan önce senin `guvenli_bellek_temizle` çıktısını tampona yazar. Saldırgan aynı bloğu alsa bile sıfır okumalıdır.

Kabul: üç işlevin bağımsız referansla aynı sonucu vermesi, saldırganın temizlemesiz akışta kurbanın bloğunu alması, sır cümlesinin tüm tokenlarının hem aday sözlükte hem tam sözlükte birebir kurtarılması ve temizlemeden sonra kalıntıda sızıntı kalmaması.

**Neden çalışıyor?** PyTorch'un CUDA önbellekli ayırıcısı, serbest bırakılan blokları sürücüye geri vermez. Blokları kendi havuzunda tutar ve aynı boyut sınıfındaki bir sonraki isteğe **içeriğini silmeden** verir. Bu bir hız tasarımıdır; `cudaMalloc` pahalıdır ve sıfırlamak bellek bant genişliği harcar. `torch.empty` "başlatılmamış bellek" demektir: içinde ne varsa onu görürsünüz. Küçük tamponlar ayrı bir havuzdan ve parçalanarak dağıtıldığı için bu deneyde kurbanın tamponu bilerek ~1,2 MB (512 token) seçildi. Daha küçük tamponlarla aynı bloğun geri gelmesi garanti değildir.

**Yazarın GPU koşusunda** saldırganın `torch.empty` tensörü kurbanın bloğuyla aynı adrese düştü. Sır cümlesinin bütün tokenları hem 1.000 tokenlık aday sözlükte hem 49.152 tokenlık tam sözlükte birebir kurtarıldı. Kurban tamponunu serbest bırakmadan önce senin `guvenli_bellek_temizle` çıktısını yazınca kalıntıda sızıntı kalmadı.

**Gerçek tehdit nerede?** LeftoverLocals (CVE-2023-4969) süreçler arası bir GPU yerel bellek açığıydı ve NVIDIA'yı etkilemedi. Bu deney farklı bir yüzeyi gösterir: **tek bir sunucu sürecinin içi**. vLLM, TGI gibi çıkarım motorları birçok kullanıcının isteğini aynı süreçte, aynı ayırıcı havuzuyla gruplar. Bir istekteki kod ya da hata, başlatılmamış bir tamponu yanıta sızdırırsa başka bir kullanıcının aktivasyonları açığa çıkar.

**Savunmalar ve bedelleri:**
- **Serbest bırakmadan önce sıfırlama:** Bellek bant genişliği harcar.
- **Ara kopyaların da temizlenmesi:** Soru 2'deki tuzak.
- **Önbelleği kapatmak (`PYTORCH_NO_CUDA_MEMORY_CACHING=1`):** Ciddi hız kaybı getirir.
- **Kiracıları ayrı süreçlere, MIG bölümlerine ya da gizli hesaplama ortamlarına ayırmak:** Kaynak verimliliğini düşürür.

**Kanıt dosyasını oku:** `ayni_blok_temizlemesiz`, `tam_sozlukte_kurtarilan_metin` ve `temizlik_sonrasi_sizinti` alanlarına bak. Soru 1: Saldırgan hiçbir API'yi kandırmadan yalnız `torch.empty` ile sırrı nasıl okudu? Soru 2: Kurban tamponunu sıfırlasaydı ama gömmeyi `E[ids] * 1.0` gibi ara kopyası olan bir işlemle hesaplasaydı sızıntı neden sürebilirdi? Soru 3: Bu deney süreçler arası LeftoverLocals'tan neyle ayrılır; NVIDIA GPU'lar CVE-2023-4969'dan etkilenmediği hâlde bu deney neden bu makinede çalıştı?
:::

::: gorev Gerçek deney · GPU bellek kalıntısından token kurtarma ve tensör sıfırlama
Önceki üç görevin işlevlerini birleştir.
```meta
motor: ai-gercek
gereksinim: torch
ortam: gpu
timeout: 180
```
```starter
import ai_lab
import math
def kalinti_enerji_orani(tampon, beklenen_sifir_tol):
    return {"doluluk_orani": 0.0, "ortalama_enerji": 0.0, "sizinti_var": False}
def gomme_kurtarma_eslesmesi(kalinti_vektor, sozluk_gommeleri):
    return {"kurtarilan_token": "yok", "kosinus_benzerligi": 0.0, "guvenli_eslesme": False}
def guvenli_bellek_temizle(tampon_listesi):
    return {"temiz_tamponlar": tampon_listesi, "temizlenen_eleman_sayisi": 0, "kalan_enerji": 1.0}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_63 as D
    D.goster(kalinti_enerji_orani, gomme_kurtarma_eslesmesi, guvenli_bellek_temizle)
```
```test
import ai_lab, math, copy
checks = []
def kontrol(x, m): checks.append(bool(x)); ok(x, m)
issues = ai_lab.kod_denetimi(src, ('referans_enerji', 'referans_kurtarma', 'referans_temizle'), izin=())
kontrol(not issues, "kopya/yama/dinamik kod yok: " + str(issues))
if issues: stop()
kalinti_enerji_orani = need("kalinti_enerji_orani")
gomme_kurtarma_eslesmesi = need("gomme_kurtarma_eslesmesi")
guvenli_bellek_temizle = need("guvenli_bellek_temizle")

def sinama1(f):
    try:
        t = [0.8, -0.6, 1e-8, 0.5]; old = list(t)
        r = f(t, 1e-6)
        return r["doluluk_orani"] == 0.75 and abs(r["ortalama_enerji"] - 0.3125) < 1e-6 and r["sizinti_var"] is True and t == old
    except Exception: return False
kontrol(sinama1(kalinti_enerji_orani), "enerji ve doluluk hesabı")
for ad, mut in [("hep sıfır", lambda t, s: {"doluluk_orani": 0.0, "ortalama_enerji": 0.0, "sizinti_var": False}), ("tolerans yok", lambda t, s: dict(kalinti_enerji_orani(t, 0.0))), ("kare yok", lambda t, s: dict(kalinti_enerji_orani(t, s), ortalama_enerji=sum(abs(x) for x in t)/len(t)))]:
    kontrol(not sinama1(mut), "mutant reddedildi: " + ad)

def sinama2(f):
    try:
        v = [0.8, -0.6, 0.0, 0.5]; s = {"red": [-0.7, 0.5, 0.2, -0.1], "onay": [0.8, -0.6, 0.0, 0.5]}
        r = f(v, s)
        if not (r["kurtarilan_token"] == "onay" and abs(r["kosinus_benzerligi"] - 1.0) < 1e-9 and r["guvenli_eslesme"] is True): return False
        if f([1.0, 0.0], {"z": [1.0, 0.0], "a": [1.0, 0.0]})["kurtarilan_token"] != "a": return False
        if f([1.0, 0.0], {"a": [0.85, math.sqrt(1.0 - 0.85 * 0.85)]})["guvenli_eslesme"] is not True or f([1.0, 0.0], {"a": [0.84, math.sqrt(1.0 - 0.84 * 0.84)]})["guvenli_eslesme"] is not False: return False
        for bad in (([0.0, 0.0], {"a": [1.0, 0.0]}), ([1.0, 0.0], {"a": [0.0, 0.0]})):
            try: f(*bad); return False
            except ValueError: pass
        return True
    except Exception: return False
kontrol(sinama2(gomme_kurtarma_eslesmesi), "kurtarma kosinüs eşleşmesi")
for ad, mut in [("hep ilk", lambda v, s: {"kurtarilan_token": next(iter(s)), "kosinus_benzerligi": 1.0, "guvenli_eslesme": True}), ("güvenli False", lambda v, s: dict(gomme_kurtarma_eslesmesi(v, s), guvenli_eslesme=False)), ("normsuz", lambda v, s: {"kurtarilan_token": max(s, key=lambda k: sum(a*b for a,b in zip(v, s[k]))), "kosinus_benzerligi": 0.9, "guvenli_eslesme": True})]:
    kontrol(not sinama2(mut), "mutant reddedildi: " + ad)

def sinama3(f):
    try:
        t = [[0.8, -0.6, 0.0, 0.5], [0.0, 1.2, -0.4]]
        r = f(t)
        return r["temiz_tamponlar"] == [[0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0]] and r["temizlenen_eleman_sayisi"] == 5 and r["kalan_enerji"] == 0.0
    except Exception: return False
kontrol(sinama3(guvenli_bellek_temizle), "tampon sıfırlama")
for ad, mut in [("sıfırlama yok", lambda t: {"temiz_tamponlar": list(t), "temizlenen_eleman_sayisi": 0, "kalan_enerji": 1.0}), ("enerji sıfır değil", lambda t: dict(guvenli_bellek_temizle(t), kalan_enerji=0.5)), ("sayı sıfır", lambda t: dict(guvenli_bellek_temizle(t), temizlenen_eleman_sayisi=0))]:
    kontrol(not sinama3(mut), "mutant reddedildi: " + ad)

# farksal tarama (final)
import importlib as _il
from sandbox.ai_fark_fuzz import fark_fuzz as _ff
_R = _il.import_module('sandbox.ai_gercek_ai_saldiri_63')
for _ad, _ref, _taban, _toh in (
    ('kalinti_enerji_orani', 'referans_enerji', ([0.8, -0.6, 0.0, 0.5], 1e-06), 3775),
    ('gomme_kurtarma_eslesmesi', 'referans_kurtarma', ([0.8, -0.6, 0.0, 0.5], {'onay': [0.8, -0.6, 0.0, 0.5], 'red': [-0.7, 0.5, 0.2, -0.1], 'bekle': [0.1, 0.2, 0.9, -0.3]}), 4227),
    ('guvenli_bellek_temizle', 'referans_temizle', ([[0.8, -0.6, 0.0, 0.5], [0.0, 1.2, -0.4]],), 4000),
):
    _t, _g = _ff(need(_ad), getattr(_R, _ref), _taban, tohum=_toh)
    kontrol(_t, "farksal tarama (" + _ad + "): bozulmuş ve sınır girdilerde bağımsız referansla aynı ValueError/sonuç" + ("" if _t else " · ayrılan girdi: " + repr(_g)[:200]))
if not all(checks): stop()
from sandbox import ai_gercek_ai_saldiri_63 as D
try: r = D.deney(kalinti_enerji_orani, gomme_kurtarma_eslesmesi, guvenli_bellek_temizle)
except ai_lab.GercekLabYok as e:
    kontrol(False, "gerçek deney yok: " + str(e)); stop()
kontrol(r["enerji_ayni"], "gerçek GPU tamponunda artık enerji hesabı bağımsız referansla aynı")
kontrol(r["kurtarma_ayni"], "gerçek gömme aktivasyonlarında kurtarma bağımsız referansla aynı")
kontrol(r["temizle_ayni"], "gerçek GPU tamponlarında temizleme bağımsız referansla aynı")
kontrol(r["ayni_blok_temizlemesiz"], "saldırganın torch.empty isteği kurbanın serbest bıraktığı GPU bloğunu aldı (aynı adres)")
kontrol(r["tam_kurtarma_basarili"], f"sır cümlesinin {r['gizli_token_sayisi']} tokenının tamamı aday sözlükte kalıntıdan kurtarıldı")
kontrol(r["tam_sozlukte_tam_kurtarma"], "tam sözlükte (49.152 token) kalıntıdan sır cümlesi birebir kurtarıldı")
kontrol(not r["temizlik_sonrasi_sizinti"] and r["temizlik_sonrasi_kurtarilan_metin"] == "", "temizleme sonrası GPU kalıntısında sızıntı yok, hiçbir token kurtarılamadı")
ai_lab.kanit_yaz("ai-saldiri-63-kabul", {"kaynak": "gercek", "kabul": all(checks), "ders": "ai-saldiri-63", "deney": r})
```
```solution
import ai_lab
import math
def kalinti_enerji_orani(tampon, beklenen_sifir_tol):
    if not isinstance(tampon, list) or not tampon: raise ValueError("tampon")
    for x in tampon:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x): raise ValueError("sayı")
    if isinstance(beklenen_sifir_tol, bool) or not isinstance(beklenen_sifir_tol, (int, float)) or not math.isfinite(beklenen_sifir_tol) or beklenen_sifir_tol < 0:
        raise ValueError("tol")
    n = len(tampon)
    dolu = sum(1 for x in tampon if abs(x) > beklenen_sifir_tol)
    enerji = sum(x * x for x in tampon) / n
    return {"doluluk_orani": float(dolu / n), "ortalama_enerji": float(enerji), "sizinti_var": dolu > 0}

def gomme_kurtarma_eslesmesi(kalinti_vektor, sozluk_gommeleri):
    if not isinstance(kalinti_vektor, list) or not kalinti_vektor: raise ValueError("vektor")
    for x in kalinti_vektor:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x): raise ValueError("sayı")
    nk = math.sqrt(sum(x * x for x in kalinti_vektor))
    if nk == 0: raise ValueError("sıfır norm")
    if not isinstance(sozluk_gommeleri, dict) or not sozluk_gommeleri: raise ValueError("sozluk")
    d = len(kalinti_vektor)
    skorlar = {}
    for tok, emb in sozluk_gommeleri.items():
        if not isinstance(tok, str) or not tok or not isinstance(emb, list) or len(emb) != d: raise ValueError("eleman")
        for x in emb:
            if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x): raise ValueError("sayı")
        ne = math.sqrt(sum(x * x for x in emb))
        if ne == 0: raise ValueError("sıfır gömme")
        skorlar[tok] = sum(a * b for a, b in zip(kalinti_vektor, emb)) / (nk * ne)
    en_iyi = min(skorlar, key=lambda k: (-skorlar[k], k))
    en_kos = float(skorlar[en_iyi])
    return {"kurtarilan_token": en_iyi, "kosinus_benzerligi": en_kos, "guvenli_eslesme": en_kos >= 0.85}

def guvenli_bellek_temizle(tampon_listesi):
    if not isinstance(tampon_listesi, list) or not tampon_listesi: raise ValueError("liste")
    for t in tampon_listesi:
        if not isinstance(t, list) or not t: raise ValueError("tampon")
        for x in t:
            if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x): raise ValueError("sayı")
    temiz = [[0.0 for _ in t] for t in tampon_listesi]
    silinen = sum(1 for t in tampon_listesi for x in t if x != 0)
    kalan = sum(x * x for t in temiz for x in t)
    return {"temiz_tamponlar": temiz, "temizlenen_eleman_sayisi": silinen, "kalan_enerji": float(kalan)}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_63 as D
    D.goster(kalinti_enerji_orani, gomme_kurtarma_eslesmesi, guvenli_bellek_temizle)
```
```hint
Üç işlevi birleştir; `kalinti_enerji_orani` toleransını, `gomme_kurtarma_eslesmesi` kosinüs normunu ve `guvenli_bellek_temizle` sıfırlamasını uygula.
```
:::

::: anlat Sınır
Bu ders tek süreçli bir sunucuda PyTorch önbellekli GPU ayırıcısının sıfırlamadan yeniden kullandığı bloktan gerçek SmolLM2 gömme aktivasyonlarının okunmasını ve tampon sıfırlamanın bunu kesmesini ölçer. Süreçler arası GPU yerel bellek (LDS) sızıntısını (LeftoverLocals, CVE-2023-4969: AMD/Apple/Qualcomm; NVIDIA etkilenmedi), sürücü düzeyinde sayfa eşlemesini, ara tensör kopyalarının sızıntısını ve gömme dışındaki derin katman aktivasyonlarından girdi kurtarmayı kapsamaz.
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
torch.empty başlatılmamış tampon döndürür; içeriği sıfır veya önceki kiracının verisi olarak garanti etmez. Aynı süreçte ayırıcının bloğu yeniden kullanmasını adres ve kalan enerjiyle ölç. Kosinüs sözlük eşleşmesiyle aktivasyonların hangi sentetik tokena benzediğini göster; özgün veri her durumda geri gelir deme. Serbest bırakmadan önce bütün kopyaları temizleme ihtiyacını anlat. Bu CUDA allocator deneyi süreçler arası LDS kusuru LeftoverLocals replikasyonu değildir.

Önkoşul ve yol köprüsü: ai-saldiri-57 çıkış sızıntısını; bu ders aynı süreçte tampon yaşam döngüsünü karşılaştırır.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| Belleği serbest bırakmak veya empty_cache güvenli silmedir | Yeniden kullanım ve sürücü davranışı silme garantisi vermez |

Dinleyiciye sor: Bu dersin kanıtı hangi gözlemi gösterir; hangi daha güçlü iddia için ek deney gerekir? Kanıtın model, ayar, veri kökeni ve hata alanlarını açarak cevabını gerekçelendir.
:::
