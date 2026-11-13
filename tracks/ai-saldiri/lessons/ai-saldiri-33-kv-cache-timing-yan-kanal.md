---
id: ai-saldiri-33
title: KV-Cache Timing ve Prompt-Stealing Yan Kanalları
summary: Sentetik hit/miss sürelerinde medyan farkı, sınıflandırma hataları ve aday etki büyüklüğü ölç; sonda yerel Ollama üzerinde ortak önek önbelleği (KV-cache) zamanlama deneyini yürüt.
timeout: 300
esleme: ai-savunma-25, ai-temel-08
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et: Hız farkı bir sinyaldir, prompt dökümü değildir

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| vLLM, SGLang ve llama.cpp gibi sunucular ortak önek (prefix) önbelleği tutar. Aynı sistem promptunu paylaşan istekler, önbellek isabetinde daha hızlı yanıt verir. Araştırmalarda çok kiracılı servislerde bu farkla başka kullanıcının prompt önekinin tahmin edilebildiği gösterilmiştir. Gerçek değerlendirme yüzlerce tekrar, kontrol grubu ve istatistiksel test ister. | Görev 1–3: `veri/grup_olcumleri.json`, `veri/esik_olcumleri.json` ve `veri/aday_olcumleri.json` içindeki **sentetik** milisaniye ölçümleri. Son adım: kurulu yerel Ollama modelinde 3 soğuk önek ve 3 ısıtılmış ortak önek isteğinin gerçek duvar saati süreleri. | Tek kullanıcılı yerel Ollama, çok kiracılı bir servisin önbellek paylaşımını temsil etmez. 3+3 ölçüm istatistiksel bir kanıt değildir. Ölçülen süre isteğin tamamıdır (en fazla 8 token üretimi dahil), saf ilk-token süresi (TTFT) değildir. Hiçbir prompt çalınmaz. |

> [!NOT]
> Görev 1–3 sentetik veriyle çalışır. Bu görevlerde model ve ağ yoktur. Son adımdaki **Gerçek deney** görevi yalnız kurulu yerel Ollama modelini ve deneyin kendi ürettiği yapay önek metinlerini kullanır. Başka bir kullanıcının ya da uygulamanın promptuna erişilmez. `veri/` dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalanır; kopyada yaptığın değişiklik bir sonraki çalıştırmada sıfırlanır, **kalıcılık yoktur**. Kontrol bu dosyalardan ayrı, gizli verilerle sınar.

Paylaşılan bir inference sisteminde önbellek isabeti yanıt süresini kısaltabilir. Saldırgan aday prompt ön eklerini deneyerek bu farktan bilgi çıkarmaya çalışabilir. Ancak gürültü, kuyruk, donanım ve scheduler da aynı farkı üretebilir. Bu nedenle tek ölçüm yerine tekrarlar, medyan, hata oranları ve önceden belirlenmiş etki eşiği gerekir.

İlk üç görevde süreler sentetik milisaniye fixture'larıdır; son görevde ise yerel Ollama (`ai_lab.SohbetOturumu`) üzerinde ortak önek (`hit`) ve soğuk önek (`miss`) istekleriyle gerçek yanıt sürelerini ölçüyoruz. Amaç prompt çalmak değil, yan kanal iddiasını ve yanlış pozitifleri istatistiksel olarak sınamaktır.

**Altta ne olur?** Bir dil modeli yanıt üretmeden önce bütün girdiyi (sistem promptu ve kullanıcı mesajı) işler. Bu "prefill" aşamasında her token için anahtar/değer (KV) tensörleri hesaplanır. Sunucu aynı öneki daha önce işlediyse bu tensörleri önbellekten okuyabilir ve prefill süresini kısaltır. Uzun bir ortak sistem promptu, önbellek isabetinde onlarca milisaniye kazandırabilir.

**Saldırgan ne dener?** Çok kiracılı bir serviste saldırgan, başka bir müşterinin sistem promptunun nasıl başladığını tahmin etmek ister. Aday önekler gönderir ve her birinin süresini ölçer. Hızlı dönen aday, "bu önek başka biri tarafından yakın zamanda işlendi" sinyali olabilir. Önek parça parça uzatılarak prompt token token tahmin edilmeye çalışılır.

**Savunma ve yanlış alarm neden kırılır?** Tek bir ölçüm bu soruyu yanıtlayamaz. GPU frekans değişimi, işletim sistemi zamanlayıcısı, başka isteklerin kuyrukta beklemesi ya da çöp toplayıcı birkaç yüz milisaniyelik aykırı değer üretebilir. Ortalama böyle tek bir değerle bütünüyle kayar, medyan ise kaymaz (`veri/grup_olcumleri.json` içindeki 950 ms'lik hit). Savunma tarafında da durum aynıdır: "Bu servis sızdırıyor" demek için önceden belirlenmiş eşik, tekrar sayısı ve hata oranları gerekir.
:::

::: tahmin Medyan fark kaç millisaniyedir?
Hit ve miss gruplarının medyanları hesaplanıyor. Üç çıktı satırını yaz:

```python
import statistics
hit = [10, 12, 14]
miss = [20, 22, 24, 26]
print(statistics.median(hit))
print(statistics.median(miss))
print(statistics.median(miss) - statistics.median(hit))
```

???

```cikti
12
23.0
11.0
```

Bu fark yalnız fixture'daki iki grubun merkezidir. Prompt içeriğinin bilindiğini veya gerçek önbellek isabetini tek başına kanıtlamaz.
:::

::: gorev 1 · Hit ve miss gruplarının medyan farkını hesapla
`grup_ozeti(olcumler)` işlevini yaz. Girdi boş olmayan liste; her ölçüm tam olarak `grup`, `sure_ms` alanlarını taşısın. Grup `hit` veya `miss`; süre bool olmayan, sonlu ve pozitif int/float olmalıdır. Her grupta en az bir ölçüm bulunmalıdır. Geçersiz veride `ValueError` yükselt.

Dönüş:

```text
{"hit":{"n":H,"medyan":HM},
 "miss":{"n":M,"medyan":MM},"fark":MM-HM}
```

Medyanlar ve fark float olmalıdır. Girdi sırası sonucu etkilememeli ve kayıtlar değiştirilmemelidir. Ortalama yerine medyan kullan.

Görünür veri: `veri/grup_olcumleri.json`. Doğru özette hit medyanı 42,1 ms, miss medyanı 88,1 ms ve fark yaklaşık 46 ms olur. 950 ms'lik aykırı hit medyanı bozmaz. Beş bozuk liste reddedilmelidir.

```starter
from ai_saldiri_veri import json_yukle

def grup_ozeti(olcumler):
    # KUSURLU BAŞLANGIÇ KODU: medyan yerine aritmetik ortalama alıyor (tek aykırı ölçüm hit grubunu bozar), farkı ters işaretli hesaplıyor ve ölçümleri doğrulamıyor!
    gruplar = {"hit": [], "miss": []}
    for olcum in olcumler:
        gruplar.setdefault(olcum["grup"], []).append(float(olcum["sure_ms"]))
    hit = sum(gruplar["hit"]) / len(gruplar["hit"])
    miss = sum(gruplar["miss"]) / len(gruplar["miss"])
    return {"hit": {"n": len(gruplar["hit"]), "medyan": hit}, "miss": {"n": len(gruplar["miss"]), "medyan": miss}, "fark": float(hit - miss)}

veri = json_yukle("veri/grup_olcumleri.json")
print(grup_ozeti(veri["olcumler"]))
for b in veri["bozuk_listeler"]:
    try:
        grup_ozeti(b["olcumler"])
        print(b["id"], "KABUL edildi (yanlış)")
    except ValueError as hata:
        print(b["id"], "reddedildi:", hata)
    except Exception as hata:
        print(b["id"], "ValueError yerine çöktü:", type(hata).__name__)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-33")
```

```test
import copy
OLCUMLER = [{"grup": "hit", "sure_ms": 10}, {"grup": "miss", "sure_ms": 20}, {"grup": "hit", "sure_ms": 12}, {"grup": "miss", "sure_ms": 22}, {"grup": "hit", "sure_ms": 14}, {"grup": "miss", "sure_ms": 24}, {"grup": "miss", "sure_ms": 26}]
BEKLENEN = {"hit": {"n": 3, "medyan": 12.0}, "miss": {"n": 4, "medyan": 23.0}, "fark": 11.0}
def sozlesme(fn):
    try:
        once = copy.deepcopy(OLCUMLER)
        if fn(OLCUMLER) != BEKLENEN or OLCUMLER != once or fn(list(reversed(OLCUMLER))) != BEKLENEN:
            return False
        tek = [{"grup": "hit", "sure_ms": 0.1}, {"grup": "miss", "sure_ms": 1}]
        if fn(tek) != {"hit": {"n": 1, "medyan": 0.1}, "miss": {"n": 1, "medyan": 1.0}, "fark": 0.9}:
            return False
        aykiri = [{"grup": "hit", "sure_ms": 10}, {"grup": "hit", "sure_ms": 12}, {"grup": "hit", "sure_ms": 100}, {"grup": "miss", "sure_ms": 20}, {"grup": "miss", "sure_ms": 22}, {"grup": "miss", "sure_ms": 24}]
        if fn(aykiri) != {"hit": {"n": 3, "medyan": 12.0}, "miss": {"n": 3, "medyan": 22.0}, "fark": 10.0}:
            return False
        for olcumler in [
            None, tuple(OLCUMLER), [], [OLCUMLER[0]], [OLCUMLER[1]], [None], [{"grup": "hit"}, OLCUMLER[1]], [dict(OLCUMLER[0], ek=1)],
            [dict(OLCUMLER[0], grup="diger"), OLCUMLER[1]],
            [dict(OLCUMLER[0], sure_ms=True), OLCUMLER[1]],
            [dict(OLCUMLER[0], sure_ms=0), OLCUMLER[1]],
            [dict(OLCUMLER[0], sure_ms=-1), OLCUMLER[1]],
            [dict(OLCUMLER[0], sure_ms=float("nan")), OLCUMLER[1]],
            [dict(OLCUMLER[0], sure_ms=float("inf")), OLCUMLER[1]],
            [dict(OLCUMLER[0], sure_ms="10"), OLCUMLER[1]],
        ]:
            try:
                fn(olcumler)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(grup_ozeti), "grup zorunluluğu, sonlu pozitif süre ve medyan farkı korunmalı")
def m_ortalama(olcumler):
    sonuc = grup_ozeti(olcumler)
    hit = [x["sure_ms"] for x in olcumler if x["grup"] == "hit"]
    miss = [x["sure_ms"] for x in olcumler if x["grup"] == "miss"]
    sonuc["hit"]["medyan"] = sum(hit) / len(hit)
    sonuc["miss"]["medyan"] = sum(miss) / len(miss)
    sonuc["fark"] = sonuc["miss"]["medyan"] - sonuc["hit"]["medyan"]
    return sonuc
def m_fark(olcumler):
    sonuc = grup_ozeti(olcumler)
    sonuc["fark"] = -sonuc["fark"]
    return sonuc
def m_grup(olcumler):
    return grup_ozeti(olcumler + [{"grup": "miss" if all(x["grup"] == "hit" for x in olcumler) else "hit", "sure_ms": 1}])
for ad, mutant in [("medyan yerine ortalama kullanan", m_ortalama), ("farkın işaretini ters çeviren", m_fark), ("eksik grubu uydurma ölçümle kapatan", m_grup)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def grup_ozeti(olcumler):
    import math
    if not isinstance(olcumler, list) or not olcumler:
        raise ValueError("ölçüm listesi geçersiz")
    gruplar = {"hit": [], "miss": []}
    for olcum in olcumler:
        if not isinstance(olcum, dict) or set(olcum) != {"grup", "sure_ms"}:
            raise ValueError("ölçüm şeması geçersiz")
        if olcum["grup"] not in gruplar:
            raise ValueError("grup geçersiz")
        sure = olcum["sure_ms"]
        if isinstance(sure, bool) or not isinstance(sure, (int, float)) or not math.isfinite(sure) or sure <= 0:
            raise ValueError("süre geçersiz")
        gruplar[olcum["grup"]].append(float(sure))
    if not gruplar["hit"] or not gruplar["miss"]:
        raise ValueError("iki grup da gerekli")
    def medyan(degerler):
        sirali = sorted(degerler)
        orta = len(sirali) // 2
        if len(sirali) % 2:
            return float(sirali[orta])
        return float((sirali[orta - 1] + sirali[orta]) / 2)
    hit = medyan(gruplar["hit"])
    miss = medyan(gruplar["miss"])
    return {"hit": {"n": len(gruplar["hit"]), "medyan": hit}, "miss": {"n": len(gruplar["miss"]), "medyan": miss}, "fark": float(miss - hit)}
```

```hint
Süreleri gruplara float olarak topla. Her grubu sıralayıp tek orta değer veya iki orta değerin ortalamasını al; farkı `miss - hit` sırasıyla hesapla.
```
:::

::: anlat Eşik kararı dört sonuç üretir
Süre eşik altındaysa `hit` tahmin etmek basit bir sınıflandırıcıdır. Gerçek etiketle karşılaştırıldığında TP, FP, TN ve FN oluşur. Doğruluk tek başına yeterli değildir; hitleri yakalama oranı `TP/(TP+FN)` ve missleri doğru reddetme oranı `TN/(TN+FP)` ayrıca görülmelidir.

Eşiğe eşit süre bu fixture'da hit tahminidir. Bir sınıf hiç yoksa ilgili oran tanımsızdır ve `None` döner; sıfır kabul edilmez.

**Sık tuzaklar:**

- **Sınırda kayma:** `<` ile `<=` arasındaki fark, eşiğe tam denk gelen ölçümü öteki sınıfa iter (`veri/esik_olcumleri.json` içinde 60 ms'lik hit).
- **Tanımsızı sıfır yapmak:** Hiç gerçek hit yoksa "hitlerin %0'ını yakaladık" demek yanlıştır; ölçülecek bir şey yoktur. `None`, raporu okuyanı bu boşluk konusunda uyarır (`yalniz_miss`).
- **Yalnız doğruluğa bakmak:** Dengesiz veride, örneğin 95 miss ve 5 hit varken, her şeye "miss" diyen sınıflandırıcı %95 doğruluk alır ama hiçbir hiti yakalamaz. TPR ve TNR'yi ayrı raporlamak bu yüzden gereklidir.
:::

::: gorev 2 · Timing eşiğinin hata türlerini ve oranlarını çıkar
`esik_regresyonu(olcumler, esik)` işlevini yaz. Girdi boş olmayan liste; her ölçüm tam olarak `gercek`, `sure_ms` alanlarını taşısın. Gerçek `hit` veya `miss`; süre ve eşik bool olmayan, sonlu, pozitif sayı olmalıdır. Geçersiz veride `ValueError` yükselt. `sure_ms <= esik` ise tahmin hit, aksi halde miss olur.

Dönüş tam olarak:

```text
{"tp":TP,"fp":FP,"tn":TN,"fn":FN,"dogruluk":D,"tpr":TPR,"tnr":TNR}
```

`dogruluk=(TP+TN)/N`, `tpr=TP/(TP+FN)`, `tnr=TN/(TN+FP)` hesaplanır. Payda sıfırsa ilgili oran `None` olur. Girdi sırası sonucu etkilememeli ve kayıtlar değiştirilmemelidir.

Görünür veri: `veri/esik_olcumleri.json`. 60 ms eşikte doğru sonuç TP=2, FP=1, TN=2 ve FN=1'dir. `yalniz_miss` verisinde TPR `None` olmalıdır. Üç bozuk liste reddedilmelidir.

```starter
from ai_saldiri_veri import json_yukle

def esik_regresyonu(olcumler, esik):
    # KUSURLU BAŞLANGIÇ KODU: eşiğe eşit süreyi miss sayıyor (< kullanıyor), tanımsız oranı 0.0 yapıyor ve ölçümleri/eşiği doğrulamıyor!
    sonuc = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    for olcum in olcumler:
        tahmin = "hit" if olcum["sure_ms"] < esik else "miss"
        if tahmin == "hit":
            sonuc["tp" if olcum["gercek"] == "hit" else "fp"] += 1
        else:
            sonuc["tn" if olcum["gercek"] == "miss" else "fn"] += 1
    n = len(olcumler)
    sonuc["dogruluk"] = (sonuc["tp"] + sonuc["tn"]) / n if n else 0.0
    sonuc["tpr"] = sonuc["tp"] / (sonuc["tp"] + sonuc["fn"]) if sonuc["tp"] + sonuc["fn"] else 0.0
    sonuc["tnr"] = sonuc["tn"] / (sonuc["tn"] + sonuc["fp"]) if sonuc["tn"] + sonuc["fp"] else 0.0
    return sonuc

veri = json_yukle("veri/esik_olcumleri.json")
print("tüm ölçümler:", esik_regresyonu(veri["olcumler"], veri["esik"]))
print("yalnız miss:", esik_regresyonu(veri["yalniz_miss"], veri["esik"]))
for b in veri["bozuk_listeler"]:
    try:
        esik_regresyonu(b["olcumler"], veri["esik"])
        print(b["id"], "KABUL edildi (yanlış)")
    except ValueError as hata:
        print(b["id"], "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-33")
```

```test
import copy
OLCUMLER = [{"gercek": "hit", "sure_ms": 10}, {"gercek": "hit", "sure_ms": 20}, {"gercek": "miss", "sure_ms": 10}, {"gercek": "miss", "sure_ms": 20}]
BEKLENEN = {"tp": 1, "fp": 1, "tn": 1, "fn": 1, "dogruluk": 0.5, "tpr": 0.5, "tnr": 0.5}
def sozlesme(fn):
    try:
        once = copy.deepcopy(OLCUMLER)
        if fn(OLCUMLER, 15) != BEKLENEN or OLCUMLER != once or fn(list(reversed(OLCUMLER)), 15) != BEKLENEN:
            return False
        esit = fn([{"gercek": "hit", "sure_ms": 15}], 15)
        if esit != {"tp": 1, "fp": 0, "tn": 0, "fn": 0, "dogruluk": 1.0, "tpr": 1.0, "tnr": None}:
            return False
        miss = fn([{"gercek": "miss", "sure_ms": 20}], 15)
        if miss["tnr"] != 1.0 or miss["tpr"] is not None or miss["fp"] != 0:
            return False
        if fn([{"gercek": "hit", "sure_ms": 0.4}], 0.5)["tp"] != 1:
            return False
        for olcumler, esik in [
            (None, 15), (tuple(OLCUMLER), 15), ([], 15), ([None], 15), ([{"gercek": "hit"}], 15), ([dict(OLCUMLER[0], ek=1)], 15),
            ([dict(OLCUMLER[0], sure_ms="10")], 15), ([dict(OLCUMLER[0], sure_ms=-0.5)], 15), ([dict(OLCUMLER[0], sure_ms=float("nan"))], 15),
            ([dict(OLCUMLER[0], gercek="diger")], 15), ([dict(OLCUMLER[0], sure_ms=0)], 15),
            ([dict(OLCUMLER[0], sure_ms=True)], 15), ([dict(OLCUMLER[0], sure_ms=float("inf"))], 15),
            (OLCUMLER, 0), (OLCUMLER, -1), (OLCUMLER, True), (OLCUMLER, float("nan")),
            (OLCUMLER, float("inf")), (OLCUMLER, "15"),
        ]:
            try:
                fn(olcumler, esik)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(esik_regresyonu), "eşik eşitliği, dört hata sayısı ve tanımsız oranlar korunmalı")
def m_esik(olcumler, esik):
    degisen = [dict(x, sure_ms=x["sure_ms"] + 0.001 if x["sure_ms"] == esik else x["sure_ms"]) for x in olcumler]
    return esik_regresyonu(degisen, esik)
def m_oran(olcumler, esik):
    sonuc = esik_regresyonu(olcumler, esik)
    sonuc["tpr"] = sonuc["dogruluk"]
    sonuc["tnr"] = sonuc["dogruluk"]
    return sonuc
def m_sinif(olcumler, esik):
    degisen = [dict(x, gercek="miss" if x["gercek"] == "hit" else "hit") for x in olcumler]
    return esik_regresyonu(degisen, esik)
for ad, mutant in [("eşik eşitliğini hit dışı bırakan", m_esik), ("sınıf oranları yerine doğruluk yazan", m_oran), ("hit ve miss etiketlerini değiştiren", m_sinif)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def esik_regresyonu(olcumler, esik):
    import math
    if not isinstance(olcumler, list) or not olcumler:
        raise ValueError("ölçüm listesi geçersiz")
    if isinstance(esik, bool) or not isinstance(esik, (int, float)) or not math.isfinite(esik) or esik <= 0:
        raise ValueError("eşik geçersiz")
    sonuc = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    for olcum in olcumler:
        if not isinstance(olcum, dict) or set(olcum) != {"gercek", "sure_ms"}:
            raise ValueError("ölçüm şeması geçersiz")
        if olcum["gercek"] not in ("hit", "miss"):
            raise ValueError("gerçek sınıf geçersiz")
        sure = olcum["sure_ms"]
        if isinstance(sure, bool) or not isinstance(sure, (int, float)) or not math.isfinite(sure) or sure <= 0:
            raise ValueError("süre geçersiz")
        tahmin = "hit" if sure <= esik else "miss"
        if tahmin == "hit" and olcum["gercek"] == "hit":
            sonuc["tp"] += 1
        elif tahmin == "hit":
            sonuc["fp"] += 1
        elif olcum["gercek"] == "miss":
            sonuc["tn"] += 1
        else:
            sonuc["fn"] += 1
    n = len(olcumler)
    sonuc["dogruluk"] = (sonuc["tp"] + sonuc["tn"]) / n
    sonuc["tpr"] = sonuc["tp"] / (sonuc["tp"] + sonuc["fn"]) if sonuc["tp"] + sonuc["fn"] else None
    sonuc["tnr"] = sonuc["tn"] / (sonuc["tn"] + sonuc["fp"]) if sonuc["tn"] + sonuc["fp"] else None
    return sonuc
```

```hint
Her kayıt için önce tahmini belirle, sonra gerçek sınıfla dört sayaçtan birini artır. Oranları sayaçlardan türet; payda kontrolünü bölmeden önce yap.
```
:::

::: anlat Aday karşılaştırması önceden belirlenmiş kurallar ister
Birçok prompt adayı denenirse en hızlı görünen aday rastlantıyla öne çıkabilir. Her aday için aynı minimum örnek sayısı ve aynı minimum medyan farkı uygulanmalıdır. Sonuçlar etki büyüklüğüne göre azalan, eşitlikte ada göre artan sıralanır; böylece girdi sırası kararı değiştirmez.

`guclu_sinyal` yalnız fixture politikasını geçen adayları listeler. Bu etiket promptun gerçekten bulunduğunu veya saldırının başarılı olduğunu kanıtlamaz; kontrollü deney ve bağımsız tekrar gerekir.

Raporu okurken `aday-gurultu` satırına bak. Bu aday, hit ve miss listesi aynı olan bir kontroldür ve farkı 0 olmalıdır. Kontrol aday sinyal veriyorsa ölçüm hattında bir sorun vardır. `aday-tek-sansli` adayında tek bir 10 ms'lik ölçüm, ortalamaya göre 26 ms'lik sahte bir fark yaratır; medyan ise yalnız 1 ms fark gösterir. `aday-esik-sinirinda` adayının farkı tam 5,0 ms'dir ve politika gereği sinyal sayılır. `aday-a` ile `aday-b` aynı farka sahiptir; ada göre sıralama, raporun girdi sırasından bağımsız olmasını sağlar.
:::

::: gorev 3 · Adayların örnek yeterliliğini ve medyan etkisini karşılaştır
`aday_kanit_raporu(adaylar, min_ornek=3, min_fark_ms=5.0)` işlevini yaz. `min_ornek` bool olmayan pozitif int, `min_fark_ms` bool olmayan sonlu ve sıfır/pozitif sayı olmalıdır. Her aday tam olarak `aday`, `hit_sureleri`, `miss_sureleri` alanlarını taşısın. Aday adı boş olmayan ve benzersiz string; iki süre listesi de en az `min_ornek` uzunluğunda, sonlu ve pozitif sayılardan oluşmalıdır. Geçersiz veride `ValueError` yükselt.

Her aday için `fark = medyan(miss) - medyan(hit)` hesapla. `sinyal`, fark `min_fark_ms` değerine eşit veya büyükse true olur. Dönüş:

```text
{"adaylar":[{"aday":AD,"fark":F,"sinyal":BOOL},...],
 "guclu_sinyal":[AD,...]}
```

Adaylar farka göre azalan, eşitlikte ada göre artan sıralıdır; `guclu_sinyal` aynı sırayı izler. Boş liste için iki alan da boş döner. Girdi değiştirilmemelidir.

Görünür veri: `veri/aday_olcumleri.json`. Doğru raporun sırası şöyledir: `aday-ortak-onek` (50), `aday-a` (6), `aday-b` (6), `aday-esik-sinirinda` (5, sinyal), `aday-tek-sansli` (1) ve `aday-gurultu` (0). Üç bozuk liste reddedilmelidir.

```starter
from ai_saldiri_veri import json_yukle

def aday_kanit_raporu(adaylar, min_ornek=3, min_fark_ms=5.0):
    # KUSURLU BAŞLANGIÇ KODU: medyan yerine ortalama kullanıyor (tek şanslı hızlı ölçüm sinyal üretir), eşiğe eşit farkı sinyal saymıyor, eşitlikte ada göre sıralamıyor ve örnek sayısını/adları doğrulamıyor!
    sonuc = []
    for aday in adaylar:
        hit = sum(aday["hit_sureleri"]) / len(aday["hit_sureleri"])
        miss = sum(aday["miss_sureleri"]) / len(aday["miss_sureleri"])
        fark = float(miss - hit)
        sonuc.append({"aday": aday["aday"], "fark": fark, "sinyal": fark > min_fark_ms})
    sonuc.sort(key=lambda x: -x["fark"])
    return {"adaylar": sonuc, "guclu_sinyal": [x["aday"] for x in sonuc if x["sinyal"]]}

veri = json_yukle("veri/aday_olcumleri.json")
r = aday_kanit_raporu(veri["adaylar"])
for a in r["adaylar"]:
    print(a["aday"], round(a["fark"], 2), "sinyal" if a["sinyal"] else "-")
print("güçlü sinyal:", r["guclu_sinyal"])
for b in veri["bozuk_listeler"]:
    try:
        aday_kanit_raporu(b["adaylar"])
        print(b["id"], "KABUL edildi (yanlış)")
    except ValueError as hata:
        print(b["id"], "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-33")
```

```test
import copy
ADAYLAR = [
    {"aday": "b", "hit_sureleri": [10, 12, 14], "miss_sureleri": [20, 22, 24]},
    {"aday": "a", "hit_sureleri": [10, 11, 12], "miss_sureleri": [20, 21, 22]},
    {"aday": "c", "hit_sureleri": [10, 10, 10], "miss_sureleri": [14, 14, 14]},
]
BEKLENEN = {"adaylar": [{"aday": "a", "fark": 10.0, "sinyal": True}, {"aday": "b", "fark": 10.0, "sinyal": True}, {"aday": "c", "fark": 4.0, "sinyal": False}], "guclu_sinyal": ["a", "b"]}
def sozlesme(fn):
    try:
        once = copy.deepcopy(ADAYLAR)
        if fn(ADAYLAR, 3, 10) != BEKLENEN or ADAYLAR != once or fn(list(reversed(ADAYLAR)), 3, 10) != BEKLENEN:
            return False
        if fn(ADAYLAR) != BEKLENEN:
            return False
        if fn([{"aday": "z", "hit_sureleri": [10, 10, 10], "miss_sureleri": [16, 16, 16]}])["guclu_sinyal"] != ["z"]:
            return False
        if (fn([{"aday": "t", "hit_sureleri": [1, 10, 10], "miss_sureleri": [20, 20, 30]}], 3, 5)["adaylar"][0]["fark"] != 10.0 or fn([{"aday": "e", "hit_sureleri": [1, 3, 5, 100], "miss_sureleri": [10, 20, 30, 100]}], 3, 5)["adaylar"][0]["fark"] != 21.0):
            return False
        if fn([{"aday": "t", "hit_sureleri": [0.2, 0.3, 0.4], "miss_sureleri": [0.8, 0.9, 1.0]}], 3, 0.5)["guclu_sinyal"] != ["t"]:
            return False
        if fn([], 1, 0) != {"adaylar": [], "guclu_sinyal": []}:
            return False
        tek = [{"aday": "x", "hit_sureleri": [1], "miss_sureleri": [1]}]
        if fn(tek, 1, 0) != {"adaylar": [{"aday": "x", "fark": 0.0, "sinyal": True}], "guclu_sinyal": ["x"]}:
            return False
        cift = [{"aday": "c", "hit_sureleri": [10, 14], "miss_sureleri": [20, 24]}]
        if fn(cift, 2, 5) != {"adaylar": [{"aday": "c", "fark": 10.0, "sinyal": True}], "guclu_sinyal": ["c"]}:
            return False
        dort = [{"aday": "d", "hit_sureleri": [1, 2, 3, 100], "miss_sureleri": [10, 20, 30, 40]}]
        if fn(dort, 4, 5) != {"adaylar": [{"aday": "d", "fark": 22.5, "sinyal": True}], "guclu_sinyal": ["d"]}:
            return False
        for adaylar, minimum, fark in [
            (None, 3, 5), (tuple(ADAYLAR), 3, 5), (ADAYLAR, 0, 5), (ADAYLAR, True, 5), (ADAYLAR, 1.5, 5),
            (ADAYLAR, 3, "5"), (ADAYLAR, 3, float("inf")),
            ([{"aday": "a"}], 3, 5), ([dict(ADAYLAR[0], aday=123)], 3, 5),
            ([dict(ADAYLAR[0], hit_sureleri=(10, 12, 14))], 3, 5), ([dict(ADAYLAR[0], miss_sureleri=(20, 22, 24))], 3, 5),
            ([dict(ADAYLAR[0], hit_sureleri=[1, "2", 3])], 3, 5), ([dict(ADAYLAR[0], hit_sureleri=[1, -1, 3])], 3, 5), ([dict(ADAYLAR[0], hit_sureleri=[1, float("nan"), 3])], 3, 5),
            (ADAYLAR, 3, -1), (ADAYLAR, 3, True), (ADAYLAR, 3, float("nan")),
            ([None], 3, 5), (ADAYLAR + [ADAYLAR[0]], 3, 5), ([dict(ADAYLAR[0], ek=1)], 3, 5),
            ([dict(ADAYLAR[0], aday="")], 3, 5), ([dict(ADAYLAR[0], hit_sureleri=[1, 2])], 3, 5),
            ([dict(ADAYLAR[0], miss_sureleri="20,21,22")], 3, 5),
            ([dict(ADAYLAR[0], hit_sureleri=[1, True, 3])], 3, 5),
            ([dict(ADAYLAR[0], miss_sureleri=[1, 0, 3])], 3, 5),
            ([dict(ADAYLAR[0], miss_sureleri=[1, float("inf"), 3])], 3, 5),
        ]:
            try:
                fn(adaylar, minimum, fark)
                return False
            except ValueError:
                pass
        try:
            fn([{"aday": "z", "hit_sureleri": [1, 2], "miss_sureleri": [10, 11]}])
            return False
        except ValueError:
            pass
        return True
    except Exception:
        return False
ok(sozlesme(aday_kanit_raporu), "örnek yeterliliği, eşik eşitliği, medyan fark ve sıralama korunmalı")
def m_esik(adaylar, min_ornek=3, min_fark_ms=5.0):
    return aday_kanit_raporu(adaylar, min_ornek, min_fark_ms + 0.001)
def m_sira(adaylar, min_ornek=3, min_fark_ms=5.0):
    sonuc = aday_kanit_raporu(adaylar, min_ornek, min_fark_ms)
    sonuc["adaylar"].reverse()
    sonuc["guclu_sinyal"].reverse()
    return sonuc
def m_ornek(adaylar, min_ornek=3, min_fark_ms=5.0):
    return aday_kanit_raporu(adaylar, max(1, min_ornek - 1), min_fark_ms)
for ad, mutant in [("eşit farkı sinyal dışı bırakan", m_esik), ("aday sırasını bozan", m_sira), ("yetersiz örneği kabul eden", m_ornek)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def aday_kanit_raporu(adaylar, min_ornek=3, min_fark_ms=5.0):
    import math
    if not isinstance(adaylar, list) or type(min_ornek) is not int or min_ornek < 1:
        raise ValueError("aday listesi veya örnek sınırı geçersiz")
    if isinstance(min_fark_ms, bool) or not isinstance(min_fark_ms, (int, float)) or not math.isfinite(min_fark_ms) or min_fark_ms < 0:
        raise ValueError("fark eşiği geçersiz")
    def medyan(degerler):
        if not isinstance(degerler, list) or len(degerler) < min_ornek:
            raise ValueError("süre listesi yetersiz")
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or x <= 0 for x in degerler):
            raise ValueError("süre geçersiz")
        sirali = sorted(float(x) for x in degerler)
        orta = len(sirali) // 2
        if len(sirali) % 2:
            return float(sirali[orta])
        return float((sirali[orta - 1] + sirali[orta]) / 2)
    sonuc = []
    adlar = set()
    for aday in adaylar:
        if not isinstance(aday, dict) or set(aday) != {"aday", "hit_sureleri", "miss_sureleri"}:
            raise ValueError("aday şeması geçersiz")
        if not isinstance(aday["aday"], str) or not aday["aday"] or aday["aday"] in adlar:
            raise ValueError("aday kimliği geçersiz")
        adlar.add(aday["aday"])
        hit = medyan(aday["hit_sureleri"])
        miss = medyan(aday["miss_sureleri"])
        fark = float(miss - hit)
        sonuc.append({"aday": aday["aday"], "fark": fark, "sinyal": fark >= min_fark_ms})
    sonuc.sort(key=lambda x: (-x["fark"], x["aday"]))
    return {"adaylar": sonuc, "guclu_sinyal": [x["aday"] for x in sonuc if x["sinyal"]]}
```

```hint
Aynı medyan yardımcısını iki süre listesine uygula. Aday sonuçlarını ürettikten sonra `(-fark, ad)` anahtarıyla sırala ve güçlü sinyal adlarını bu sıralı listeden çıkar.
```
:::

::: anlat Canlı Ollama üzerinde ortak önek (KV-cache) ve soğuk önek zamanlama deneyi
İlk üç görevde medyan farkı, eşik regresyonu ve aday kanıt raporunu sentetik milisaniye listeleri üzerinde doğruladın. Şimdi aynı üç işlevi **gerçek yerel Ollama sunucusu** (`ai_lab.SohbetOturumu`, GPU kilidiyle) üzerinde koşuyoruz:

1. Her turda önce daha önce görülmemiş uzun bir **soğuk önek (`miss`)** gönderilir. Yanıt en fazla 8 token ile sınırlıdır, böylece süreye büyük ölçüde prefill yükü yansır. Ölçülen değer isteğin duvar saati süresidir, saf ilk-token süresi (TTFT) değildir.
2. Ardından **ortak sistem öneki (`hit`)** ısıtılır ve hemen aynı ortak önekle sıcak istek gönderilerek önbellek isabet süresi kaydedilir.
3. Elde edilen 6 canlı ölçüm (`3 hit`, `3 miss`) doğrudan senin `grup_ozeti`, `esik_regresyonu` ve `aday_kanit_raporu` işlevlerine verilir.

> [!NOTE]
> İşletim sistemi zamanlayıcısı ve GPU frekans geçişleri tekil ölçümlerde gürültü yaratabilir; bu yüzden kabul testi ham milisaniyenin sabit bir sayıya eşit olmasını değil, 6 canlı model çağrısının hatasız tamamlanmasını, zamanlama istatistiklerinin doğru hesaplanmasını ve gerçek kanıt kaydını denetler.

**Kanıtı okumak:** `ham_kayitlar` listesinde her turun `hit` ve `miss` süresi yan yana durur. Önce `aday-gurultu-kontrol` satırının farkının 0 olduğuna bak: deney bu adayı bilerek miss listesiyle eşleştirir. Sonra `aday-ortak-onek` farkına bak. Pozitif ve 5 ms'den büyükse, bu makinede ortak önek ısıtmasının ölçülebilir bir etkisi var demektir. Fark küçük ya da negatif çıkabilir; bu da gerçek bir gözlemdir ve kabul şartı değildir. Ollama modeli yeniden yüklerse ya da GPU başka bir iş yaparsa sonuç değişir. Üç tekrar, yalnız yöntemin çalıştığını gösterir.
:::

::: gorev Gerçek deney · Yerel Ollama üzerinde KV-cache ortak önek zamanlama ölçümü
Önceki üç görevde yazdığın `grup_ozeti(olcumler)`, `esik_regresyonu(olcumler, esik)` ve `aday_kanit_raporu(adaylar, min_ornek=3, min_fark_ms=5.0)` işlevlerini burada birleştir.

- **Çalıştır** düğmesi yerel Ollama üzerinde 3 soğuk (`miss`) ve 3 sıcak (`hit`) ortak önek çağrısı yapar ve medyan farkını ekrana döker.
- **Kontrol** düğmesi önce üç işlevini deterministik sınır ve mutant testlerinden geçirir, ardından canlı Ollama zamanlama deneyini koşup kanıt üretir.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import math
import ai_lab
from sandbox import ai_gercek_ai_saldiri_33 as L

def grup_ozeti(olcumler):
    # KUSURLU BAŞLANGIÇ KODU: medyan yerine aritmetik ortalama alıyor (tek aykırı ölçüm hit grubunu bozar), farkı ters işaretli hesaplıyor ve ölçümleri doğrulamıyor!
    gruplar = {"hit": [], "miss": []}
    for olcum in olcumler:
        gruplar.setdefault(olcum["grup"], []).append(float(olcum["sure_ms"]))
    hit = sum(gruplar["hit"]) / len(gruplar["hit"])
    miss = sum(gruplar["miss"]) / len(gruplar["miss"])
    return {"hit": {"n": len(gruplar["hit"]), "medyan": hit}, "miss": {"n": len(gruplar["miss"]), "medyan": miss}, "fark": float(hit - miss)}

def esik_regresyonu(olcumler, esik):
    # KUSURLU BAŞLANGIÇ KODU: eşiğe eşit süreyi miss sayıyor (< kullanıyor), tanımsız oranı 0.0 yapıyor ve ölçümleri/eşiği doğrulamıyor!
    sonuc = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    for olcum in olcumler:
        tahmin = "hit" if olcum["sure_ms"] < esik else "miss"
        if tahmin == "hit":
            sonuc["tp" if olcum["gercek"] == "hit" else "fp"] += 1
        else:
            sonuc["tn" if olcum["gercek"] == "miss" else "fn"] += 1
    n = len(olcumler)
    sonuc["dogruluk"] = (sonuc["tp"] + sonuc["tn"]) / n if n else 0.0
    sonuc["tpr"] = sonuc["tp"] / (sonuc["tp"] + sonuc["fn"]) if sonuc["tp"] + sonuc["fn"] else 0.0
    sonuc["tnr"] = sonuc["tn"] / (sonuc["tn"] + sonuc["fp"]) if sonuc["tn"] + sonuc["fp"] else 0.0
    return sonuc

def aday_kanit_raporu(adaylar, min_ornek=3, min_fark_ms=5.0):
    # KUSURLU BAŞLANGIÇ KODU: medyan yerine ortalama kullanıyor (tek şanslı hızlı ölçüm sinyal üretir), eşiğe eşit farkı sinyal saymıyor, eşitlikte ada göre sıralamıyor ve örnek sayısını/adları doğrulamıyor!
    sonuc = []
    for aday in adaylar:
        hit = sum(aday["hit_sureleri"]) / len(aday["hit_sureleri"])
        miss = sum(aday["miss_sureleri"]) / len(aday["miss_sureleri"])
        fark = float(miss - hit)
        sonuc.append({"aday": aday["aday"], "fark": fark, "sinyal": fark > min_fark_ms})
    sonuc.sort(key=lambda x: -x["fark"])
    return {"adaylar": sonuc, "guclu_sinyal": [x["aday"] for x in sonuc if x["sinyal"]]}

if ai_lab.CALISTIR:
    L.goster(grup_ozeti, esik_regresyonu, aday_kanit_raporu)
```

```test
import copy
import ai_lab
from sandbox import ai_gercek_ai_saldiri_33 as L
checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

import ast
_yasak = ("grup_ozeti_referans", "esik_regresyonu_referans", "aday_kanit_raporu_referans", "kanit_yaz")
for s in ai_lab.kod_denetimi(src, yasak=_yasak):
    ok(False, f"Güvenlik/kopya denetimi: {s}")
for _n in ast.walk(ast.parse(src)):
    if isinstance(_n, ast.ImportFrom) and any(a.name in _yasak or a.name == "*" for a in _n.names): ok(False, "Güvenlik/kopya denetimi: referans importu yasak")
    if isinstance(_n, (ast.Import, ast.ImportFrom)) and any(x and x.split(".")[0] in ("inspect", "importlib", "runpy") for x in [a.name for a in _n.names] + ([_n.module] if isinstance(_n, ast.ImportFrom) else [])): ok(False, "Güvenlik/kopya denetimi: kaynak okuma/dinamik import yasak")
    if isinstance(_n, ast.Name) and _n.id in ("exec", "eval", "compile", "__builtins__"): ok(False, "Güvenlik/kopya denetimi: dinamik kod çalıştırma yasak: " + _n.id)
if not all(checks):
    stop()

def _sozlesme_kontrol():
    try:
        olc = [{"grup": "hit", "sure_ms": 10}, {"grup": "miss", "sure_ms": 20}, {"grup": "hit", "sure_ms": 12}, {"grup": "miss", "sure_ms": 22}, {"grup": "hit", "sure_ms": 14}, {"grup": "miss", "sure_ms": 24}, {"grup": "miss", "sure_ms": 26}]
        bek_g = {"hit": {"n": 3, "medyan": 12.0}, "miss": {"n": 4, "medyan": 23.0}, "fark": 11.0}
        once = copy.deepcopy(olc)
        if grup_ozeti(olc) != bek_g or olc != once or grup_ozeti(list(reversed(olc))) != bek_g:
            return False
        if grup_ozeti([{"grup": "hit", "sure_ms": 10}, {"grup": "hit", "sure_ms": 12}, {"grup": "hit", "sure_ms": 100}, {"grup": "miss", "sure_ms": 20}, {"grup": "miss", "sure_ms": 22}, {"grup": "miss", "sure_ms": 24}])["hit"]["medyan"] != 12.0:
            return False
        for bozuk in [None, [], [olc[0]], [dict(olc[0], grup="x"), olc[1]], [dict(olc[0], sure_ms=0), olc[1]], [dict(olc[0], sure_ms=True), olc[1]]]:
            try:
                grup_ozeti(bozuk)
                return False
            except ValueError:
                pass

        olc_e = [{"gercek": "hit", "sure_ms": 10}, {"gercek": "hit", "sure_ms": 20}, {"gercek": "miss", "sure_ms": 10}, {"gercek": "miss", "sure_ms": 20}]
        if esik_regresyonu(olc_e, 15) != {"tp": 1, "fp": 1, "tn": 1, "fn": 1, "dogruluk": 0.5, "tpr": 0.5, "tnr": 0.5}:
            return False
        if esik_regresyonu([{"gercek": "hit", "sure_ms": 15}], 15) != {"tp": 1, "fp": 0, "tn": 0, "fn": 0, "dogruluk": 1.0, "tpr": 1.0, "tnr": None}:
            return False
        for bozuk_e, es in [(None, 15), ([], 15), (olc_e, 0), (olc_e, True), ([dict(olc_e[0], gercek="x")], 15), ([dict(olc_e[0], sure_ms=0)], 15)]:
            try:
                esik_regresyonu(bozuk_e, es)
                return False
            except ValueError:
                pass

        adaylar = [
            {"aday": "b", "hit_sureleri": [10, 12, 14], "miss_sureleri": [20, 22, 24]},
            {"aday": "a", "hit_sureleri": [10, 11, 12], "miss_sureleri": [20, 21, 22]},
            {"aday": "c", "hit_sureleri": [10, 10, 10], "miss_sureleri": [14, 14, 14]},
        ]
        bek_a = {"adaylar": [{"aday": "a", "fark": 10.0, "sinyal": True}, {"aday": "b", "fark": 10.0, "sinyal": True}, {"aday": "c", "fark": 4.0, "sinyal": False}], "guclu_sinyal": ["a", "b"]}
        if aday_kanit_raporu(adaylar, 3, 10) != bek_a or aday_kanit_raporu([], 1, 0) != {"adaylar": [], "guclu_sinyal": []}:
            return False
        for bozuk_a, mo, mf in [(None, 3, 5), (adaylar, 0, 5), (adaylar, True, 5), (adaylar, 3, -1), (adaylar + [adaylar[0]], 3, 5), ([dict(adaylar[0], hit_sureleri=[1, 2])], 3, 5)]:
            try:
                aday_kanit_raporu(bozuk_a, mo, mf)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(_sozlesme_kontrol(), "grup_ozeti, esik_regresyonu ve aday_kanit_raporu sözleşme ve sınır kontrollerini geçmeli")
def _k33_g1():
    import copy
    OLCUMLER = [{"grup": "hit", "sure_ms": 10}, {"grup": "miss", "sure_ms": 20}, {"grup": "hit", "sure_ms": 12}, {"grup": "miss", "sure_ms": 22}, {"grup": "hit", "sure_ms": 14}, {"grup": "miss", "sure_ms": 24}, {"grup": "miss", "sure_ms": 26}]
    BEKLENEN = {"hit": {"n": 3, "medyan": 12.0}, "miss": {"n": 4, "medyan": 23.0}, "fark": 11.0}
    def sozlesme(fn):
        try:
            once = copy.deepcopy(OLCUMLER)
            if fn(OLCUMLER) != BEKLENEN or OLCUMLER != once or fn(list(reversed(OLCUMLER))) != BEKLENEN:
                return False
            tek = [{"grup": "hit", "sure_ms": 0.1}, {"grup": "miss", "sure_ms": 1}]
            if fn(tek) != {"hit": {"n": 1, "medyan": 0.1}, "miss": {"n": 1, "medyan": 1.0}, "fark": 0.9}:
                return False
            aykiri = [{"grup": "hit", "sure_ms": 10}, {"grup": "hit", "sure_ms": 12}, {"grup": "hit", "sure_ms": 100}, {"grup": "miss", "sure_ms": 20}, {"grup": "miss", "sure_ms": 22}, {"grup": "miss", "sure_ms": 24}]
            if fn(aykiri) != {"hit": {"n": 3, "medyan": 12.0}, "miss": {"n": 3, "medyan": 22.0}, "fark": 10.0}:
                return False
            for olcumler in [
                None, tuple(OLCUMLER), [], [OLCUMLER[0]], [OLCUMLER[1]], [None], [{"grup": "hit"}, OLCUMLER[1]], [dict(OLCUMLER[0], ek=1)],
                [dict(OLCUMLER[0], grup="diger"), OLCUMLER[1]],
                [dict(OLCUMLER[0], sure_ms=True), OLCUMLER[1]],
                [dict(OLCUMLER[0], sure_ms=0), OLCUMLER[1]],
                [dict(OLCUMLER[0], sure_ms=-1), OLCUMLER[1]],
                [dict(OLCUMLER[0], sure_ms=float("nan")), OLCUMLER[1]],
                [dict(OLCUMLER[0], sure_ms=float("inf")), OLCUMLER[1]],
                [dict(OLCUMLER[0], sure_ms="10"), OLCUMLER[1]],
            ]:
                try:
                    fn(olcumler)
                    return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False
    return bool(sozlesme(grup_ozeti))
def _k33_g2():
    import copy
    OLCUMLER = [{"gercek": "hit", "sure_ms": 10}, {"gercek": "hit", "sure_ms": 20}, {"gercek": "miss", "sure_ms": 10}, {"gercek": "miss", "sure_ms": 20}]
    BEKLENEN = {"tp": 1, "fp": 1, "tn": 1, "fn": 1, "dogruluk": 0.5, "tpr": 0.5, "tnr": 0.5}
    def sozlesme(fn):
        try:
            once = copy.deepcopy(OLCUMLER)
            if fn(OLCUMLER, 15) != BEKLENEN or OLCUMLER != once or fn(list(reversed(OLCUMLER)), 15) != BEKLENEN:
                return False
            esit = fn([{"gercek": "hit", "sure_ms": 15}], 15)
            if esit != {"tp": 1, "fp": 0, "tn": 0, "fn": 0, "dogruluk": 1.0, "tpr": 1.0, "tnr": None}:
                return False
            miss = fn([{"gercek": "miss", "sure_ms": 20}], 15)
            if miss["tnr"] != 1.0 or miss["tpr"] is not None or miss["fp"] != 0:
                return False
            if fn([{"gercek": "hit", "sure_ms": 0.4}], 0.5)["tp"] != 1:
                return False
            for olcumler, esik in [
                (None, 15), (tuple(OLCUMLER), 15), ([], 15), ([None], 15), ([{"gercek": "hit"}], 15), ([dict(OLCUMLER[0], ek=1)], 15),
                ([dict(OLCUMLER[0], sure_ms="10")], 15), ([dict(OLCUMLER[0], sure_ms=-0.5)], 15), ([dict(OLCUMLER[0], sure_ms=float("nan"))], 15),
                ([dict(OLCUMLER[0], gercek="diger")], 15), ([dict(OLCUMLER[0], sure_ms=0)], 15),
                ([dict(OLCUMLER[0], sure_ms=True)], 15), ([dict(OLCUMLER[0], sure_ms=float("inf"))], 15),
                (OLCUMLER, 0), (OLCUMLER, -1), (OLCUMLER, True), (OLCUMLER, float("nan")),
                (OLCUMLER, float("inf")), (OLCUMLER, "15"),
            ]:
                try:
                    fn(olcumler, esik)
                    return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False
    return bool(sozlesme(esik_regresyonu))
def _k33_g3():
    import copy
    ADAYLAR = [
        {"aday": "b", "hit_sureleri": [10, 12, 14], "miss_sureleri": [20, 22, 24]},
        {"aday": "a", "hit_sureleri": [10, 11, 12], "miss_sureleri": [20, 21, 22]},
        {"aday": "c", "hit_sureleri": [10, 10, 10], "miss_sureleri": [14, 14, 14]},
    ]
    BEKLENEN = {"adaylar": [{"aday": "a", "fark": 10.0, "sinyal": True}, {"aday": "b", "fark": 10.0, "sinyal": True}, {"aday": "c", "fark": 4.0, "sinyal": False}], "guclu_sinyal": ["a", "b"]}
    def sozlesme(fn):
        try:
            once = copy.deepcopy(ADAYLAR)
            if fn(ADAYLAR, 3, 10) != BEKLENEN or ADAYLAR != once or fn(list(reversed(ADAYLAR)), 3, 10) != BEKLENEN:
                return False
            if fn(ADAYLAR) != BEKLENEN:
                return False
            if fn([{"aday": "z", "hit_sureleri": [10, 10, 10], "miss_sureleri": [16, 16, 16]}])["guclu_sinyal"] != ["z"]:
                return False
            if (fn([{"aday": "t", "hit_sureleri": [1, 10, 10], "miss_sureleri": [20, 20, 30]}], 3, 5)["adaylar"][0]["fark"] != 10.0 or fn([{"aday": "e", "hit_sureleri": [1, 3, 5, 100], "miss_sureleri": [10, 20, 30, 100]}], 3, 5)["adaylar"][0]["fark"] != 21.0):
                return False
            if fn([{"aday": "t", "hit_sureleri": [0.2, 0.3, 0.4], "miss_sureleri": [0.8, 0.9, 1.0]}], 3, 0.5)["guclu_sinyal"] != ["t"]:
                return False
            if fn([], 1, 0) != {"adaylar": [], "guclu_sinyal": []}:
                return False
            tek = [{"aday": "x", "hit_sureleri": [1], "miss_sureleri": [1]}]
            if fn(tek, 1, 0) != {"adaylar": [{"aday": "x", "fark": 0.0, "sinyal": True}], "guclu_sinyal": ["x"]}:
                return False
            cift = [{"aday": "c", "hit_sureleri": [10, 14], "miss_sureleri": [20, 24]}]
            if fn(cift, 2, 5) != {"adaylar": [{"aday": "c", "fark": 10.0, "sinyal": True}], "guclu_sinyal": ["c"]}:
                return False
            dort = [{"aday": "d", "hit_sureleri": [1, 2, 3, 100], "miss_sureleri": [10, 20, 30, 40]}]
            if fn(dort, 4, 5) != {"adaylar": [{"aday": "d", "fark": 22.5, "sinyal": True}], "guclu_sinyal": ["d"]}:
                return False
            for adaylar, minimum, fark in [
                (None, 3, 5), (tuple(ADAYLAR), 3, 5), (ADAYLAR, 0, 5), (ADAYLAR, True, 5), (ADAYLAR, 1.5, 5),
                (ADAYLAR, 3, "5"), (ADAYLAR, 3, float("inf")),
                ([{"aday": "a"}], 3, 5), ([dict(ADAYLAR[0], aday=123)], 3, 5),
                ([dict(ADAYLAR[0], hit_sureleri=(10, 12, 14))], 3, 5), ([dict(ADAYLAR[0], miss_sureleri=(20, 22, 24))], 3, 5),
                ([dict(ADAYLAR[0], hit_sureleri=[1, "2", 3])], 3, 5), ([dict(ADAYLAR[0], hit_sureleri=[1, -1, 3])], 3, 5), ([dict(ADAYLAR[0], hit_sureleri=[1, float("nan"), 3])], 3, 5),
                (ADAYLAR, 3, -1), (ADAYLAR, 3, True), (ADAYLAR, 3, float("nan")),
                ([None], 3, 5), (ADAYLAR + [ADAYLAR[0]], 3, 5), ([dict(ADAYLAR[0], ek=1)], 3, 5),
                ([dict(ADAYLAR[0], aday="")], 3, 5), ([dict(ADAYLAR[0], hit_sureleri=[1, 2])], 3, 5),
                ([dict(ADAYLAR[0], miss_sureleri="20,21,22")], 3, 5),
                ([dict(ADAYLAR[0], hit_sureleri=[1, True, 3])], 3, 5),
                ([dict(ADAYLAR[0], miss_sureleri=[1, 0, 3])], 3, 5),
                ([dict(ADAYLAR[0], miss_sureleri=[1, float("inf"), 3])], 3, 5),
            ]:
                try:
                    fn(adaylar, minimum, fark)
                    return False
                except ValueError:
                    pass
            try:
                fn([{"aday": "z", "hit_sureleri": [1, 2], "miss_sureleri": [10, 11]}])
                return False
            except ValueError:
                pass
            return True
        except Exception:
            return False
    return bool(sozlesme(aday_kanit_raporu))
ok(_k33_g1() and _k33_g2() and _k33_g3(), "ön sözleşme: tüm grup özeti, eşik regresyonu ve aday kanıt raporu sınırları doğrulandı")
if not all(checks):
    stop()

try:
    rapor = L.deney(grup_ozeti, esik_regresyonu, aday_kanit_raporu)
except ai_lab.GercekLabYok as e:
    ok(False, str(e))
    stop()
except Exception as e:
    ok(False, f"GERÇEK KV-CACHE DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

k = rapor["kontroller"]
ok(k["grup_ozeti_uyumu"], f"grup_ozeti canlı ölçümlerde referansla uyuşmalı: {rapor['grup_ozeti']}")
ok(k["esik_regresyonu_uyumu"], f"esik_regresyonu canlı ölçümlerde referansla uyuşmalı: {rapor['esik_regresyonu']}")
ok(k["aday_raporu_uyumu"], f"aday_kanit_raporu canlı ölçümlerde referansla uyuşmalı: {rapor['aday_raporu']}")
ok(k["alti_canli_olcum_alindi"], f"3 hit ve 3 miss olmak üzere 6 canlı Ollama ölçümü alınmalı: {rapor['ozet']}")
ok(k["cihaz_dogrulandi"], f"cihaz doğrulaması geçmeli: {rapor['ortam'].get('bellek')}")
ok(k["kaynak_temizlendi"], f"kaynak temizliği geçmeli: {rapor['ortam'].get('temizlik')}")

kabul = all(checks)
kanit_yolu = ai_lab.kanit_yaz("saldiri-33-kv-cache-timing", dict(rapor, kaynak="gercek", kabul=kabul))
o = rapor["ozet"]
print(f"GERÇEK KV-CACHE DENEYİ: model={o['model']} hit_medyan={o['hit_medyan_ms']}ms miss_medyan={o['miss_medyan_ms']}ms fark={o['medyan_fark_ms']}ms kanıt={kanit_yolu}")
```

```solution
import math
import ai_lab
from sandbox import ai_gercek_ai_saldiri_33 as L

def grup_ozeti(olcumler):
    if not isinstance(olcumler, list) or not olcumler:
        raise ValueError("ölçüm listesi geçersiz")
    gruplar = {"hit": [], "miss": []}
    for olcum in olcumler:
        if not isinstance(olcum, dict) or set(olcum) != {"grup", "sure_ms"}:
            raise ValueError("ölçüm şeması geçersiz")
        if olcum["grup"] not in gruplar:
            raise ValueError("grup geçersiz")
        sure = olcum["sure_ms"]
        if isinstance(sure, bool) or not isinstance(sure, (int, float)) or not math.isfinite(sure) or sure <= 0:
            raise ValueError("süre geçersiz")
        gruplar[olcum["grup"]].append(float(sure))
    if not gruplar["hit"] or not gruplar["miss"]:
        raise ValueError("iki grup da gerekli")
    def medyan(degerler):
        sirali = sorted(degerler)
        orta = len(sirali) // 2
        if len(sirali) % 2:
            return float(sirali[orta])
        return float((sirali[orta - 1] + sirali[orta]) / 2)
    hit = medyan(gruplar["hit"])
    miss = medyan(gruplar["miss"])
    return {"hit": {"n": len(gruplar["hit"]), "medyan": hit}, "miss": {"n": len(gruplar["miss"]), "medyan": miss}, "fark": float(miss - hit)}

def esik_regresyonu(olcumler, esik):
    if not isinstance(olcumler, list) or not olcumler:
        raise ValueError("ölçüm listesi geçersiz")
    if isinstance(esik, bool) or not isinstance(esik, (int, float)) or not math.isfinite(esik) or esik <= 0:
        raise ValueError("eşik geçersiz")
    sonuc = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    for olcum in olcumler:
        if not isinstance(olcum, dict) or set(olcum) != {"gercek", "sure_ms"}:
            raise ValueError("ölçüm şeması geçersiz")
        if olcum["gercek"] not in ("hit", "miss"):
            raise ValueError("gerçek sınıf geçersiz")
        sure = olcum["sure_ms"]
        if isinstance(sure, bool) or not isinstance(sure, (int, float)) or not math.isfinite(sure) or sure <= 0:
            raise ValueError("süre geçersiz")
        tahmin = "hit" if sure <= esik else "miss"
        if tahmin == "hit" and olcum["gercek"] == "hit":
            sonuc["tp"] += 1
        elif tahmin == "hit":
            sonuc["fp"] += 1
        elif olcum["gercek"] == "miss":
            sonuc["tn"] += 1
        else:
            sonuc["fn"] += 1
    n = len(olcumler)
    sonuc["dogruluk"] = (sonuc["tp"] + sonuc["tn"]) / n
    sonuc["tpr"] = sonuc["tp"] / (sonuc["tp"] + sonuc["fn"]) if sonuc["tp"] + sonuc["fn"] else None
    sonuc["tnr"] = sonuc["tn"] / (sonuc["tn"] + sonuc["fp"]) if sonuc["tn"] + sonuc["fp"] else None
    return sonuc

def aday_kanit_raporu(adaylar, min_ornek=3, min_fark_ms=5.0):
    if not isinstance(adaylar, list) or type(min_ornek) is not int or min_ornek < 1:
        raise ValueError("aday listesi veya örnek sınırı geçersiz")
    if isinstance(min_fark_ms, bool) or not isinstance(min_fark_ms, (int, float)) or not math.isfinite(min_fark_ms) or min_fark_ms < 0:
        raise ValueError("fark eşiği geçersiz")
    def medyan(degerler):
        if not isinstance(degerler, list) or len(degerler) < min_ornek:
            raise ValueError("süre listesi yetersiz")
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or x <= 0 for x in degerler):
            raise ValueError("süre geçersiz")
        sirali = sorted(float(x) for x in degerler)
        orta = len(sirali) // 2
        if len(sirali) % 2:
            return float(sirali[orta])
        return float((sirali[orta - 1] + sirali[orta]) / 2)
    sonuc = []
    adlar = set()
    for aday in adaylar:
        if not isinstance(aday, dict) or set(aday) != {"aday", "hit_sureleri", "miss_sureleri"}:
            raise ValueError("aday şeması geçersiz")
        if not isinstance(aday["aday"], str) or not aday["aday"] or aday["aday"] in adlar:
            raise ValueError("aday kimliği geçersiz")
        adlar.add(aday["aday"])
        hit = medyan(aday["hit_sureleri"])
        miss = medyan(aday["miss_sureleri"])
        fark = float(miss - hit)
        sonuc.append({"aday": aday["aday"], "fark": fark, "sinyal": fark >= min_fark_ms})
    sonuc.sort(key=lambda x: (-x["fark"], x["aday"]))
    return {"adaylar": sonuc, "guclu_sinyal": [x["aday"] for x in sonuc if x["sinyal"]]}

if ai_lab.CALISTIR:
    L.goster(grup_ozeti, esik_regresyonu, aday_kanit_raporu)
```

```hint
Önceki üç görevde yazdığın `grup_ozeti`, `esik_regresyonu` ve `aday_kanit_raporu` işlevlerini eksiksiz taşı; `if ai_lab.CALISTIR:` bloğu canlı Ollama KV-cache deneyini çalıştırır.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Timing farkı tek ölçümle sır kanıtı olmaz

Önbelleğe denk gelen ortak önek hesap yükünü azaltabilir; GPU sıralaması, model yüklenmesi ve ısınma da süreyi değiştirir. Medyan farkı, eşik hataları ve aday başına örnek sayısı bu yüzden ayrı ölçülür. Deneyin kendi cache durumu ile gerçek çok kiracılı sistemin izolasyonu aynı değildir. Sayaç ve süreler gizli metnin doğrudan okunması olarak yorumlanamaz.

| Yaygın yanlış | Doğru sınır |
|---|---|
| Hızlı yanıt kesin üyelik kanıtıdır | Karar eşiğinin yanlış pozitif ve yanlış negatifleri vardır. |

Sonraki bağlantı: ai-savunma-25. [Birincil kaynak](https://docs.ollama.com/api/generate). Kaynak mekanizmanın ilgili API veya yöntemini açıklar; bu labın başarı oranının kanıtı yerel ham koşudur.
:::
