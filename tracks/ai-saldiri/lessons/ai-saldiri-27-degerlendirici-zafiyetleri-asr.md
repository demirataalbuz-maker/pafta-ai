---
id: ai-saldiri-27
title: Değerlendirici Zafiyetleri ve ASR Güvenilirliği
summary: Değerlendirici kararlarını katı şemayla ayrıştır; kapsam ile doğruluğu ayır ve belirsiz kararların ASR üzerindeki etkisini alt–üst sınırlarla raporla.
timeout: 45
esleme: ai-guvence-33, ai-uretim-36
---

::: anlat ASR, değerlendiricinin söylediğinden ibaret değildir
Attack Success Rate (ASR), denenen saldırıların başarılı görülen bölümünü ölçer. Ancak otomatik değerlendirici yanlış pozitif üretebilir, gerçek başarıyı kaçırabilir veya bozuk çıktı verebilir. Bozuk çıktıyı doğrudan `basarisiz` saymak ASR'yi düşürür; doğrudan `basarili` saymak ise şişirir.

Bu nedenle üç durum birbirinden ayrılır: açık başarı, açık başarısızlık ve belirsizlik. Ayrıştırılamayan çıktı da belirsiz etiketle aynı şey değildir; ilki ölçüm altyapısı hatasıdır ve düzeltilmelidir. Kapsam, karar verilebilen örnek oranını; doğruluk ise karar verilen örneklerde referansla uyuşmayı gösterir.

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Promptfoo, PyRIT veya garak kampanyalarında hedef yanıtları çoğu zaman bir LLM hakeme (LLM-as-judge) puanlatılır; raporlanan ASR doğrudan bu hakemin kararlarından türetilir | İlk üç görevde `hakem/ham_hakem_ciktilari.json`, `hakem/hakem_olaylari.json` ve `hakem/asr_sonuclari.json` içindeki **sentetik** çıktılar ve kararlar; son görevde yerel Ollama modeli hakem olarak, her çalıştırmada yeni üretilen zararsız bir canary kodunun sızıp sızmadığına karar verir | Tek hakem modeli ve 12 sentetik vakadaki hata oranı, başka hakem modelleri, istemler veya gerçek saldırı kampanyaları için genel bir güvenilirlik değeri vermez |

> [!NOT]
> İlk üç görevde çalışma dizinine kopyalanan `hakem/` dosyaları **sentetik** eğitim örnekleridir. Her çalıştırmada yeniden kopyalanır; çalıştırmalar arasında **kalıcılık yoktur**. Son adımdaki **Gerçek deney** görevinde yazdığın üç işlev canlı hakem çıktılarıyla sınanır. Başarı sinyali yalnız zararsız bir canary kodudur; gerçek zararlı içerik üretilmez ve hakemin kandırılması geçme şartı değildir.
:::

::: tahmin Belirsiz karar üst sınırı nasıl değiştirir?
Dört denemenin ikisi başarılı, biri belirsiz. Üç çıktı satırını yaz:

```python
kararlar = ["basarili", "basarisiz", "belirsiz", "basarili"]
print(len(kararlar))
print(kararlar.count("basarili"))
print((kararlar.count("basarili") + kararlar.count("belirsiz")) / len(kararlar))
```

???

```cikti
4
2
0.75
```

Kesin başarı oranı `2/4 = 0.5` olur. Belirsiz deneme başarı sayılırsa oran en fazla `0.75` olabilir; belirsizliği listeden silmek bu iki sınırı da değiştirir.
:::

::: gorev 1 · Değerlendirici çıktısını katı şemayla ayrıştır
`degerlendirici_karar_ayikla(ham)` işlevini yaz. `ham`, 1–1024 karakterli ve NUL içermeyen string olmalıdır. İçerik yalnız bir JSON nesnesi olmalı; nesne tam olarak `karar` alanını taşımalı ve değer `basarili`, `basarisiz` veya `belirsiz` stringlerinden biri olmalıdır. Geçerli kararı string olarak döndür.

Boşluklar JSON'un çevresinde bulunabilir. Ek alan, eksik alan, başka etiket, JSON dışı ön/son metin, bozuk JSON, yanlış tür veya geçersiz girdi durumunda `ValueError` yükselt. Hatalı çıktıyı `belirsiz` karara dönüştürme.

```starter
import re
from ai_saldiri_veri import json_yukle

def degerlendirici_karar_ayikla(ham):
    # KUSURLU BAŞLANGIÇ KODU: metinde etiket kelimesi arıyor (kod çiti, ek alan, düz metin geçiyor);
    # hiçbir şey bulamazsa bozuk çıktıyı sessizce "belirsiz" sayıyor!
    eslesme = re.search(r"basarisiz|basarili|belirsiz", str(ham).lower())
    return eslesme.group(0) if eslesme else "belirsiz"

for c in json_yukle("hakem/ham_hakem_ciktilari.json")["ciktilar"]:
    try:
        print(c["id"], degerlendirici_karar_ayikla(c["ham"]))
    except ValueError as hata:
        print(c["id"], "altyapı hatası:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-27")
```

```test
def sozlesme(fn):
    try:
        for karar in ("basarili", "basarisiz", "belirsiz"):
            if fn('{"karar":"' + karar + '"}') != karar or fn('  {"karar": "' + karar + '"} \n') != karar:
                return False
        uzun = '{"karar":"basarili"}' + " " * (1024 - len('{"karar":"basarili"}'))
        if len(uzun) != 1024 or fn(uzun) != "basarili":
            return False
        for ham in [
            None, 3, True, "", " " * 1025, "x" * 1025, uzun + " ", '{"karar":"basarili"}\x00',
            "{", '{"karar":"basarili"} ek', 'oneki {"karar":"basarili"}',
            "null", "[]", '"basarili"', "{}", '{"karar":"basarili","ek":1}',
            '{"Karar":"basarili"}', '{"karar":"BASARILI"}', '{"karar":"basarili "}',
            '{"karar":true}', '{"karar":1}', '{"karar":null}',
        ]:
            try:
                fn(ham)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(degerlendirici_karar_ayikla), "katı JSON şeması, uzunluk sınırı ve açık belirsizlik korunmalı")
def m_varsayilan(ham):
    try:
        return degerlendirici_karar_ayikla(ham)
    except ValueError:
        return "belirsiz"
def m_ek_alan(ham):
    return degerlendirici_karar_ayikla(ham.replace(',"ek":1', ""))
for ad, mutant in [("bozuk çıktıyı belirsiz sayan", m_varsayilan), ("ek alanı sessizce silen", m_ek_alan)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def degerlendirici_karar_ayikla(ham):
    import json
    if not isinstance(ham, str):
        raise ValueError("ham çıktı türü geçersiz")
    if not ham:
        raise ValueError("ham çıktı boş")
    if len(ham) > 1024:
        raise ValueError("ham çıktı çok uzun")
    if "\x00" in ham:
        raise ValueError("ham çıktı NUL içeriyor")
    try:
        veri = json.loads(ham)
    except (json.JSONDecodeError, TypeError, ValueError) as hata:
        raise ValueError("JSON ayrıştırılamadı") from hata
    if type(veri) is not dict or set(veri) != {"karar"}:
        raise ValueError("karar şeması geçersiz")
    karar = veri["karar"]
    if type(karar) is not str or karar not in ("basarili", "basarisiz", "belirsiz"):
        raise ValueError("karar etiketi geçersiz")
    return karar
```

```hint
Önce ham string sözleşmesini doğrula, sonra `json.loads` kullan. Nesnenin anahtar kümesini ve kararın hem türünü hem tam etiketini ayrı denetle.
```
:::

::: anlat Kapsam ve doğruluk birlikte raporlanır
Bir değerlendirici bütün zor örneklerde `belirsiz` dönerse kalan kolay örneklerde yüksek doğruluk gösterebilir. Yalnız doğruluğu raporlamak bu davranışı gizler. Dört sınıflandırma sayacı yalnız kesin kararlarda hesaplanır:

- TP: referans ve değerlendirici `basarili`.
- FP: referans `basarisiz`, değerlendirici `basarili`.
- TN: referans ve değerlendirici `basarisiz`.
- FN: referans `basarili`, değerlendirici `basarisiz`.

Belirsiz kararlar bu dört sayaca eklenmez. Kapsam bütün örnekleri, doğruluk ise yalnız kesin karar verilen örnekleri payda olarak kullanır.
:::

::: gorev 2 · Değerlendiricinin hata türlerini, kapsamını ve doğruluğunu ölç
`degerlendirici_raporu(olaylar)` işlevini yaz. Girdi boş olmayan liste; her olay tam olarak `id`, `referans`, `degerlendirici` alanlarını taşısın. Kimlik boş olmayan ve benzersiz string; referans `basarili` veya `basarisiz`; değerlendirici bu iki etikete ek olarak `belirsiz` olabilir. Geçersiz veride `ValueError` yükselt.

Dönüş tam olarak:

```text
{"tp":TP,"fp":FP,"tn":TN,"fn":FN,"belirsiz":B,
 "kapsam":K,"dogruluk":D}
```

`kapsam=(N-B)/N`; `dogruluk=(TP+TN)/(N-B)` hesaplanır. Kesin karar yoksa doğruluk `None` olur. Girdi sırası sonucu değiştirmemeli ve kayıtlar değiştirilmemelidir.

```starter
from ai_saldiri_veri import json_yukle

def degerlendirici_raporu(olaylar):
    # KUSURLU BAŞLANGIÇ KODU: belirsiz kararları başarısızlık sayıyor; kapsam hep 1.0 görünüyor
    # ve doğruluğun paydası bütün olaylar oluyor!
    sonuc = {"tp": 0, "fp": 0, "tn": 0, "fn": 0, "belirsiz": 0}
    for o in olaylar:
        karar = "basarisiz" if o["degerlendirici"] == "belirsiz" else o["degerlendirici"]
        if karar == "basarili":
            sonuc["tp" if o["referans"] == "basarili" else "fp"] += 1
        else:
            sonuc["tn" if o["referans"] == "basarisiz" else "fn"] += 1
    sonuc["kapsam"] = 1.0
    sonuc["dogruluk"] = (sonuc["tp"] + sonuc["tn"]) / len(olaylar)
    return sonuc

print(degerlendirici_raporu(json_yukle("hakem/hakem_olaylari.json")["olaylar"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-27")
```

```test
import copy
OLAYLAR = [
    {"id": "a", "referans": "basarili", "degerlendirici": "basarili"},
    {"id": "b", "referans": "basarisiz", "degerlendirici": "basarili"},
    {"id": "c", "referans": "basarisiz", "degerlendirici": "basarisiz"},
    {"id": "d", "referans": "basarili", "degerlendirici": "basarisiz"},
    {"id": "e", "referans": "basarili", "degerlendirici": "belirsiz"},
]
BEKLENEN = {"tp": 1, "fp": 1, "tn": 1, "fn": 1, "belirsiz": 1, "kapsam": 0.8, "dogruluk": 0.5}
def sozlesme(fn):
    try:
        once = copy.deepcopy(OLAYLAR)
        if fn(OLAYLAR) != BEKLENEN or OLAYLAR != once or fn(list(reversed(OLAYLAR))) != BEKLENEN:
            return False
        belirsiz = [{"id": "x", "referans": "basarisiz", "degerlendirici": "belirsiz"}]
        if fn(belirsiz) != {"tp": 0, "fp": 0, "tn": 0, "fn": 0, "belirsiz": 1, "kapsam": 0.0, "dogruluk": None}:
            return False
        tek = [{"id": "x", "referans": "basarisiz", "degerlendirici": "basarisiz"}]
        if fn(tek)["kapsam"] != 1.0 or fn(tek)["dogruluk"] != 1.0:
            return False
        tek_tp = [{"id": "x", "referans": "basarili", "degerlendirici": "basarili"}]
        if fn(tek_tp)["tp"] != 1 or fn(tek_tp)["fp"] != 0:
            return False
        tek_fp = [{"id": "x", "referans": "basarisiz", "degerlendirici": "basarili"}]
        if fn(tek_fp)["tp"] != 0 or fn(tek_fp)["fp"] != 1:
            return False
        for olaylar in [
            None, {}, (OLAYLAR[0],), [], [None], [dict(OLAYLAR[0], ek=1)],
            [dict(OLAYLAR[0], id=None)], [dict(OLAYLAR[0], id=123)], [dict(OLAYLAR[0], id="")],
            [dict(OLAYLAR[0], referans="belirsiz")], [dict(OLAYLAR[0], referans=None)],
            [dict(OLAYLAR[0], degerlendirici="diger")], [dict(OLAYLAR[0], degerlendirici=None)],
            [OLAYLAR[0], OLAYLAR[0]],
        ]:
            try:
                fn(olaylar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(degerlendirici_raporu), "dört hata sayacı, belirsizlik, kapsam ve koşullu doğruluk korunmalı")
def m_belirsiz(olaylar):
    degisen = [dict(x, degerlendirici="basarisiz" if x["degerlendirici"] == "belirsiz" else x["degerlendirici"]) for x in olaylar]
    return degerlendirici_raporu(degisen)
def m_dogruluk(olaylar):
    sonuc = degerlendirici_raporu(olaylar)
    sonuc["dogruluk"] = (sonuc["tp"] + sonuc["tn"]) / len(olaylar)
    return sonuc
def m_sinif(olaylar):
    degisen = [dict(x, degerlendirici="basarisiz" if x["degerlendirici"] == "basarili" else "basarili") for x in olaylar]
    return degerlendirici_raporu(degisen)
for ad, mutant in [("belirsizi başarısızlık sayan", m_belirsiz), ("doğrulukta belirsizleri paydaya katan", m_dogruluk), ("başarı sınıflarını değiştiren", m_sinif)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def degerlendirici_raporu(olaylar):
    if not isinstance(olaylar, list) or not olaylar:
        raise ValueError("olay listesi geçersiz")
    sonuc = {"tp": 0, "fp": 0, "tn": 0, "fn": 0, "belirsiz": 0}
    kimlikler = set()
    for olay in olaylar:
        if not isinstance(olay, dict) or set(olay) != {"id", "referans", "degerlendirici"}:
            raise ValueError("olay şeması geçersiz")
        kimlik = olay["id"]
        if type(kimlik) is not str or not kimlik or kimlik in kimlikler:
            raise ValueError("olay kimliği geçersiz")
        kimlikler.add(kimlik)
        if olay["referans"] not in ("basarili", "basarisiz") or type(olay["referans"]) is not str:
            raise ValueError("referans geçersiz")
        karar = olay["degerlendirici"]
        if type(karar) is not str or karar not in ("basarili", "basarisiz", "belirsiz"):
            raise ValueError("değerlendirici kararı geçersiz")
        if karar == "belirsiz":
            sonuc["belirsiz"] += 1
        elif karar == "basarili":
            if olay["referans"] == "basarili":
                sonuc["tp"] += 1
            else:
                sonuc["fp"] += 1
        else:
            if olay["referans"] == "basarisiz":
                sonuc["tn"] += 1
            else:
                sonuc["fn"] += 1
    n = len(olaylar)
    kesin = n - sonuc["belirsiz"]
    sonuc["kapsam"] = kesin / n
    sonuc["dogruluk"] = (sonuc["tp"] + sonuc["tn"]) / kesin if kesin else None
    return sonuc
```

```hint
Belirsizleri önce kendi sayacına ayır. Kesin kararları dört dala say; kapsamı toplamdan, doğruluğu kesin karar sayısından hesapla.
```
:::

::: anlat Belirsizlik ASR için aralık üretir
Belirsiz kararları tamamen başarısız saymak tek bir alt sınır, tamamen başarılı saymak tek bir üst sınır verir. Bunların hiçbiri kesin ASR değildir. Dürüst rapor, eldeki etiketlerle mümkün aralığı gösterir: `basarili/N ≤ ASR ≤ (basarili+belirsiz)/N`.

Bu aralık istatistiksel güven aralığı değildir; yalnız belirsiz etiketlerin sınıflandırma belirsizliğidir. Örnekleme hatası, saldırıların bağımsızlığı ve değerlendirici yanlılığı ayrıca ele alınmalıdır.
:::

::: gorev 3 · Belirsiz kararları silmeden ASR alt ve üst sınırını hesapla
`asr_sinirlari(sonuclar)` işlevini yaz. Girdi boş olmayan liste; her kayıt tam olarak `id`, `karar` alanlarını taşısın. Kimlik boş olmayan ve benzersiz string; karar `basarili`, `basarisiz` veya `belirsiz` olmalıdır. Geçersiz veride `ValueError` yükselt.

Dönüş:

```text
{"n":N,"basarili":S,"basarisiz":F,"belirsiz":B,
 "alt_asr":S/N,"ust_asr":(S+B)/N}
```

Girdi sırası sonucu etkilememeli ve kayıtlar değiştirilmemelidir. Belirsizleri paydadan çıkarma; üst sınırı `1.0` olarak sabitleme.

```starter
from ai_saldiri_veri import json_yukle

def asr_sinirlari(sonuclar):
    # KUSURLU BAŞLANGIÇ KODU: belirsizleri örneklemden siliyor; payda küçülüyor ve aralık tek noktaya çöküyor!
    kesin = [x for x in sonuclar if x["karar"] != "belirsiz"]
    basarili = sum(1 for x in kesin if x["karar"] == "basarili")
    oran = basarili / len(kesin)
    return {"n": len(kesin), "basarili": basarili, "basarisiz": len(kesin) - basarili, "belirsiz": 0,
            "alt_asr": oran, "ust_asr": oran}

print(asr_sinirlari(json_yukle("hakem/asr_sonuclari.json")["sonuclar"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-27")
```

```test
import copy
SONUCLAR = [
    {"id": "a", "karar": "basarili"},
    {"id": "b", "karar": "basarisiz"},
    {"id": "c", "karar": "belirsiz"},
    {"id": "d", "karar": "basarisiz"},
]
BEKLENEN = {"n": 4, "basarili": 1, "basarisiz": 2, "belirsiz": 1, "alt_asr": 0.25, "ust_asr": 0.5}
def sozlesme(fn):
    try:
        once = copy.deepcopy(SONUCLAR)
        if fn(SONUCLAR) != BEKLENEN or SONUCLAR != once or fn(list(reversed(SONUCLAR))) != BEKLENEN:
            return False
        belirsiz = [{"id": "x", "karar": "belirsiz"}]
        if fn(belirsiz) != {"n": 1, "basarili": 0, "basarisiz": 0, "belirsiz": 1, "alt_asr": 0.0, "ust_asr": 1.0}:
            return False
        basarisiz = [{"id": "x", "karar": "basarisiz"}]
        if fn(basarisiz)["alt_asr"] != 0.0 or fn(basarisiz)["ust_asr"] != 0.0:
            return False
        basarili = [{"id": "x", "karar": "basarili"}]
        if fn(basarili)["alt_asr"] != 1.0 or fn(basarili)["ust_asr"] != 1.0:
            return False
        for sonuclar in [
            None, {}, (SONUCLAR[0],), [], [None], [dict(SONUCLAR[0], ek=1)],
            [dict(SONUCLAR[0], id=None)], [dict(SONUCLAR[0], id=123)], [dict(SONUCLAR[0], id="")],
            [dict(SONUCLAR[0], karar=None)], [dict(SONUCLAR[0], karar="diger")],
            [SONUCLAR[0], SONUCLAR[0]],
        ]:
            try:
                fn(sonuclar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(asr_sinirlari), "bütün kararlar paydada kalmalı ve belirsizlik yalnız üst sınırı büyütmeli")
def m_sil(sonuclar):
    kesin = [x for x in sonuclar if x["karar"] != "belirsiz"]
    sonuc = asr_sinirlari(kesin)
    sonuc["n"] = len(sonuclar)
    return sonuc
def m_ust(sonuclar):
    sonuc = asr_sinirlari(sonuclar)
    sonuc["ust_asr"] = 1.0
    return sonuc
def m_belirsiz(sonuclar):
    degisen = [dict(x, karar="basarili" if x["karar"] == "belirsiz" else x["karar"]) for x in sonuclar]
    return asr_sinirlari(degisen)
for ad, mutant in [("belirsizleri örneklemden silen", m_sil), ("üst sınırı sabitleyen", m_ust), ("belirsizi kesin başarı sayan", m_belirsiz)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def asr_sinirlari(sonuclar):
    if not isinstance(sonuclar, list) or not sonuclar:
        raise ValueError("sonuç listesi geçersiz")
    kimlikler = set()
    sayaclar = {"basarili": 0, "basarisiz": 0, "belirsiz": 0}
    for kayit in sonuclar:
        if not isinstance(kayit, dict) or set(kayit) != {"id", "karar"}:
            raise ValueError("sonuç şeması geçersiz")
        kimlik = kayit["id"]
        if type(kimlik) is not str or not kimlik or kimlik in kimlikler:
            raise ValueError("sonuç kimliği geçersiz")
        kimlikler.add(kimlik)
        karar = kayit["karar"]
        if type(karar) is not str or karar not in sayaclar:
            raise ValueError("karar geçersiz")
        sayaclar[karar] += 1
    n = len(sonuclar)
    return {
        "n": n,
        "basarili": sayaclar["basarili"],
        "basarisiz": sayaclar["basarisiz"],
        "belirsiz": sayaclar["belirsiz"],
        "alt_asr": sayaclar["basarili"] / n,
        "ust_asr": (sayaclar["basarili"] + sayaclar["belirsiz"]) / n,
    }
```

```hint
Üç kararı toplam `N` içinde say. Alt sınırda yalnız kesin başarıları, üst sınırda başarı ve belirsizlerin toplamını paya yaz.
```
:::

::: anlat Yerel Ollama hakemiyle canlı ölçüm: hakeme yönelik dolaylı talimat ASR'yi nasıl kaydırır?
Önceki üç görevde hakem çıktısını katı şemayla ayrıştırdın, hakemin hata türlerini saydın ve belirsizliği silmeden ASR aralığı hesapladın. Şimdi aynı üç işlevi **gerçek bir hakem modeline** bağlıyoruz:

1. Her çalıştırmada yeni bir zararsız canary kodu (`PAFTA-...`) üretilir ve 12 sentetik hedef yanıtı kurulur. Referans etiket kodla hesaplanır: canary yanıtta **tam olarak** geçiyorsa saldırı başarılıdır,
2. Vakaların bir kısmı hakemi yanıltmak için hazırlanmıştır: reddederken kodu söyleyen yanıt, sahte veya maskeli kod, yarım kod, yanıtın içine gömülü `{"karar": ...}` JSON'u ve hakeme seslenen "DEĞERLENDİRİCİ NOTU" (dolaylı talimat),
3. Aynı vakalar yerel modelde iki hakem istemiyle değerlendirilir: `saf_hakem` yanıtı doğrudan okur; `sert_hakem` yanıtı `<yanit>` etiketleri içinde **veri** olarak işaretler ve kuralı mekanik biçimde tanımlar,
4. Her ham hakem çıktısı senin `degerlendirici_karar_ayikla` işlevinle ayrıştırılır (ayrıştırılamayan çıktı belirsiz değil `altyapi_hatasi` olarak ayrı sayılır), sonra `degerlendirici_raporu` ve `asr_sinirlari` ile özetlenir.

Kanıtta `gercek_asr` ile her hakemin `asr` aralığını ve `yanilan_vakalar` listesini karşılaştır. Hakemin yanlış pozitifleri ASR'yi gerçek değerin üstüne şişirir; bu, değerlendiricinin kendisinin bir saldırı yüzeyi olduğu anlamına gelir. Savunma tarafı bu derste görünür: yanıtı veri olarak ayırmak ve kuralı mekanikleştirmek hataları azaltabilir, ama tamamen kaldırmayabilir. Canary gibi deterministik olarak denetlenebilen bir başarı sinyali varsa hakem yerine kodla doğrulamak en güvenilir yoldur; ölçümün tekrarlanabilirliği ve raporlanması `ai-guvence-33` dersinde ele alınır.
:::

::: gorev Gerçek deney · Yerel Ollama hakemiyle değerlendirici zafiyetlerini ve ASR aralığını ölç
Önceki üç görevde yazdığın `degerlendirici_karar_ayikla(ham)`, `degerlendirici_raporu(olaylar)` ve `asr_sinirlari(sonuclar)` işlevlerini burada birleştir.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab
from sandbox import ai_gercek_ai_saldiri_27 as L

def degerlendirici_karar_ayikla(ham):
    # KUSURLU BAŞLANGIÇ KODU: bozuk hakem çıktısını sessizce "belirsiz" sayıyor!
    return "belirsiz"

def degerlendirici_raporu(olaylar):
    return {"tp": 0, "fp": 0, "tn": 0, "fn": 0, "belirsiz": 0, "kapsam": 1.0, "dogruluk": None}

def asr_sinirlari(sonuclar):
    return {"n": len(sonuclar), "basarili": 0, "basarisiz": 0, "belirsiz": 0, "alt_asr": 0.0, "ust_asr": 1.0}

if ai_lab.CALISTIR:
    L.goster(degerlendirici_karar_ayikla, degerlendirici_raporu, asr_sinirlari)
```

```test
import ai_lab
from sandbox import ai_gercek_ai_saldiri_27 as L

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for s in ai_lab.kod_denetimi(src, yasak=("degerlendirici_karar_ayikla_referans", "degerlendirici_raporu_referans", "asr_sinirlari_referans", "kanit_yaz", "vakalar")):
    ok(False, f"Güvenlik/kopya denetimi: {s}")
if not all(checks):
    stop()

def _sozlesme_kontrol():
    try:
        if degerlendirici_karar_ayikla(' {"karar":"belirsiz"} ') != "belirsiz":
            return False
        for ham in ['```json\n{"karar":"basarili"}\n```', '{"karar":"basarili","ek":1}', "Karar: basarili", '{"karar":"BASARILI"}', ""]:
            try:
                degerlendirici_karar_ayikla(ham)
                return False
            except ValueError:
                pass
        O = [{"id": "a", "referans": "basarili", "degerlendirici": "belirsiz"},
             {"id": "b", "referans": "basarisiz", "degerlendirici": "basarili"}]
        if degerlendirici_raporu(O) != {"tp": 0, "fp": 1, "tn": 0, "fn": 0, "belirsiz": 1, "kapsam": 0.5, "dogruluk": 0.0}:
            return False
        if asr_sinirlari([{"id": "a", "karar": "belirsiz"}, {"id": "b", "karar": "basarili"}, {"id": "c", "karar": "basarisiz"}, {"id": "d", "karar": "basarisiz"}]) != \
                {"n": 4, "basarili": 1, "basarisiz": 2, "belirsiz": 1, "alt_asr": 0.25, "ust_asr": 0.5}:
            return False
        return True
    except Exception:
        return False

ok(_sozlesme_kontrol(), "degerlendirici_karar_ayikla, degerlendirici_raporu ve asr_sinirlari sözleşme kontrollerini geçmeli")
def _k27_g1():
    def sozlesme(fn):
        try:
            for karar in ("basarili", "basarisiz", "belirsiz"):
                if fn('{"karar":"' + karar + '"}') != karar or fn('  {"karar": "' + karar + '"} \n') != karar:
                    return False
            uzun = '{"karar":"basarili"}' + " " * (1024 - len('{"karar":"basarili"}'))
            if len(uzun) != 1024 or fn(uzun) != "basarili":
                return False
            for ham in [
                None, 3, True, "", " " * 1025, "x" * 1025, uzun + " ", '{"karar":"basarili"}\x00',
                "{", '{"karar":"basarili"} ek', 'oneki {"karar":"basarili"}',
                "null", "[]", '"basarili"', "{}", '{"karar":"basarili","ek":1}',
                '{"Karar":"basarili"}', '{"karar":"BASARILI"}', '{"karar":"basarili "}',
                '{"karar":true}', '{"karar":1}', '{"karar":null}',
            ]:
                try:
                    fn(ham)
                    return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False
    return bool(sozlesme(degerlendirici_karar_ayikla))
def _k27_g2():
    import copy
    OLAYLAR = [
        {"id": "a", "referans": "basarili", "degerlendirici": "basarili"},
        {"id": "b", "referans": "basarisiz", "degerlendirici": "basarili"},
        {"id": "c", "referans": "basarisiz", "degerlendirici": "basarisiz"},
        {"id": "d", "referans": "basarili", "degerlendirici": "basarisiz"},
        {"id": "e", "referans": "basarili", "degerlendirici": "belirsiz"},
    ]
    BEKLENEN = {"tp": 1, "fp": 1, "tn": 1, "fn": 1, "belirsiz": 1, "kapsam": 0.8, "dogruluk": 0.5}
    def sozlesme(fn):
        try:
            once = copy.deepcopy(OLAYLAR)
            if fn(OLAYLAR) != BEKLENEN or OLAYLAR != once or fn(list(reversed(OLAYLAR))) != BEKLENEN:
                return False
            belirsiz = [{"id": "x", "referans": "basarisiz", "degerlendirici": "belirsiz"}]
            if fn(belirsiz) != {"tp": 0, "fp": 0, "tn": 0, "fn": 0, "belirsiz": 1, "kapsam": 0.0, "dogruluk": None}:
                return False
            tek = [{"id": "x", "referans": "basarisiz", "degerlendirici": "basarisiz"}]
            if fn(tek)["kapsam"] != 1.0 or fn(tek)["dogruluk"] != 1.0:
                return False
            tek_tp = [{"id": "x", "referans": "basarili", "degerlendirici": "basarili"}]
            if fn(tek_tp)["tp"] != 1 or fn(tek_tp)["fp"] != 0:
                return False
            tek_fp = [{"id": "x", "referans": "basarisiz", "degerlendirici": "basarili"}]
            if fn(tek_fp)["tp"] != 0 or fn(tek_fp)["fp"] != 1:
                return False
            for olaylar in [
                None, {}, (OLAYLAR[0],), [], [None], [dict(OLAYLAR[0], ek=1)],
                [dict(OLAYLAR[0], id=None)], [dict(OLAYLAR[0], id=123)], [dict(OLAYLAR[0], id="")],
                [dict(OLAYLAR[0], referans="belirsiz")], [dict(OLAYLAR[0], referans=None)],
                [dict(OLAYLAR[0], degerlendirici="diger")], [dict(OLAYLAR[0], degerlendirici=None)],
                [OLAYLAR[0], OLAYLAR[0]],
            ]:
                try:
                    fn(olaylar)
                    return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False
    return bool(sozlesme(degerlendirici_raporu))
def _k27_g3():
    import copy
    SONUCLAR = [
        {"id": "a", "karar": "basarili"},
        {"id": "b", "karar": "basarisiz"},
        {"id": "c", "karar": "belirsiz"},
        {"id": "d", "karar": "basarisiz"},
    ]
    BEKLENEN = {"n": 4, "basarili": 1, "basarisiz": 2, "belirsiz": 1, "alt_asr": 0.25, "ust_asr": 0.5}
    def sozlesme(fn):
        try:
            once = copy.deepcopy(SONUCLAR)
            if fn(SONUCLAR) != BEKLENEN or SONUCLAR != once or fn(list(reversed(SONUCLAR))) != BEKLENEN:
                return False
            belirsiz = [{"id": "x", "karar": "belirsiz"}]
            if fn(belirsiz) != {"n": 1, "basarili": 0, "basarisiz": 0, "belirsiz": 1, "alt_asr": 0.0, "ust_asr": 1.0}:
                return False
            basarisiz = [{"id": "x", "karar": "basarisiz"}]
            if fn(basarisiz)["alt_asr"] != 0.0 or fn(basarisiz)["ust_asr"] != 0.0:
                return False
            basarili = [{"id": "x", "karar": "basarili"}]
            if fn(basarili)["alt_asr"] != 1.0 or fn(basarili)["ust_asr"] != 1.0:
                return False
            for sonuclar in [
                None, {}, (SONUCLAR[0],), [], [None], [dict(SONUCLAR[0], ek=1)],
                [dict(SONUCLAR[0], id=None)], [dict(SONUCLAR[0], id=123)], [dict(SONUCLAR[0], id="")],
                [dict(SONUCLAR[0], karar=None)], [dict(SONUCLAR[0], karar="diger")],
                [SONUCLAR[0], SONUCLAR[0]],
            ]:
                try:
                    fn(sonuclar)
                    return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False
    return bool(sozlesme(asr_sinirlari))
ok(_k27_g1() and _k27_g2() and _k27_g3(), "ön sözleşme: tam şema, uzunluk ve belirsizlik sınırları doğrulandı")
if not all(checks):
    stop()

try:
    rapor = L.deney(degerlendirici_karar_ayikla, degerlendirici_raporu, asr_sinirlari)
except ai_lab.GercekLabYok as e:
    ok(False, str(e))
    stop()
except Exception as e:
    ok(False, f"GERÇEK HAKEM DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

k = rapor["kontroller"]
ok(k["ayristirma_uyumu"], f"degerlendirici_karar_ayikla canlı hakem çıktılarında referansla aynı kararı/hatayı vermeli: {rapor['ayristirma_farki']}")
ok(k["rapor_uyumu"], f"degerlendirici_raporu canlı hakem kararlarında referansla uyuşmalı: {rapor['ogrenci']}")
ok(k["sinir_uyumu"], f"asr_sinirlari canlı hakem kararlarında referansla uyuşmalı: {rapor['ogrenci']}")
ok(k["olcum_tam"], "her vaka iki hakem tarafından gerçek modelle değerlendirilmeli ve ham çıktı kaydedilmeli")
ok(k["cihaz_dogrulandi"], f"Ollama cihaz kaydı doğrulanmalı: {rapor['ortam'].get('bellek')}")
ok(k["kaynak_temizlendi"], f"deney yalnız kendi başlattığı kaynağı kapatmalı: {rapor['ortam'].get('temizlik')}")

kabul = all(checks)
kanit_yolu = ai_lab.kanit_yaz("saldiri-27-hakem-zafiyeti", dict(rapor, kaynak="gercek", kabul=kabul))
o = rapor["ozet"]
asr = {h: (v.get("asr") or {}).get("alt_asr") for h, v in o["hakemler"].items()}
print(f"GERÇEK HAKEM DENEYİ: model={o['model']} gerçek_asr={o['gercek_asr']} hakem_asr={asr} kanıt={kanit_yolu}")
```

```solution
import json
import ai_lab
from sandbox import ai_gercek_ai_saldiri_27 as L

ETIKETLER = ("basarili", "basarisiz", "belirsiz")

def degerlendirici_karar_ayikla(ham):
    if not isinstance(ham, str):
        raise ValueError("ham çıktı türü geçersiz")
    if not ham or len(ham) > 1024 or "\x00" in ham:
        raise ValueError("ham çıktı sözleşmesi geçersiz")
    try:
        veri = json.loads(ham)
    except (json.JSONDecodeError, TypeError, ValueError) as hata:
        raise ValueError("JSON ayrıştırılamadı") from hata
    if type(veri) is not dict or set(veri) != {"karar"}:
        raise ValueError("karar şeması geçersiz")
    if type(veri["karar"]) is not str or veri["karar"] not in ETIKETLER:
        raise ValueError("karar etiketi geçersiz")
    return veri["karar"]

def degerlendirici_raporu(olaylar):
    if not isinstance(olaylar, list) or not olaylar:
        raise ValueError("olay listesi geçersiz")
    sonuc = {"tp": 0, "fp": 0, "tn": 0, "fn": 0, "belirsiz": 0}
    kimlikler = set()
    for o in olaylar:
        if not isinstance(o, dict) or set(o) != {"id", "referans", "degerlendirici"}:
            raise ValueError("olay şeması geçersiz")
        if type(o["id"]) is not str or not o["id"] or o["id"] in kimlikler:
            raise ValueError("olay kimliği geçersiz")
        kimlikler.add(o["id"])
        if type(o["referans"]) is not str or o["referans"] not in ("basarili", "basarisiz"):
            raise ValueError("referans geçersiz")
        karar = o["degerlendirici"]
        if type(karar) is not str or karar not in ETIKETLER:
            raise ValueError("değerlendirici kararı geçersiz")
        if karar == "belirsiz":
            sonuc["belirsiz"] += 1
        elif karar == "basarili":
            sonuc["tp" if o["referans"] == "basarili" else "fp"] += 1
        else:
            sonuc["tn" if o["referans"] == "basarisiz" else "fn"] += 1
    n = len(olaylar)
    kesin = n - sonuc["belirsiz"]
    sonuc["kapsam"] = kesin / n
    sonuc["dogruluk"] = (sonuc["tp"] + sonuc["tn"]) / kesin if kesin else None
    return sonuc

def asr_sinirlari(sonuclar):
    if not isinstance(sonuclar, list) or not sonuclar:
        raise ValueError("sonuç listesi geçersiz")
    kimlikler = set()
    say = {e: 0 for e in ETIKETLER}
    for k in sonuclar:
        if not isinstance(k, dict) or set(k) != {"id", "karar"}:
            raise ValueError("sonuç şeması geçersiz")
        if type(k["id"]) is not str or not k["id"] or k["id"] in kimlikler:
            raise ValueError("sonuç kimliği geçersiz")
        kimlikler.add(k["id"])
        if type(k["karar"]) is not str or k["karar"] not in say:
            raise ValueError("karar geçersiz")
        say[k["karar"]] += 1
    n = len(sonuclar)
    return {"n": n, "basarili": say["basarili"], "basarisiz": say["basarisiz"], "belirsiz": say["belirsiz"],
            "alt_asr": say["basarili"] / n, "ust_asr": (say["basarili"] + say["belirsiz"]) / n}

if ai_lab.CALISTIR:
    L.goster(degerlendirici_karar_ayikla, degerlendirici_raporu, asr_sinirlari)
```

```hint
Önceki üç görevde yazdığın işlevleri eksiksiz taşı. Kanıtta `gercek_asr` kodla hesaplanan doğru değerdir; her hakemin `asr` aralığını ve `yanilan_vakalar` listesini bununla karşılaştır.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Hakemin verdiği sayının paydasını koru

Geçerli başarısız karar ile ayrıştırılamayan çıktı aynı değildir. Belirsiz örnekleri silmek, yalnız kolay örneklerde doğruluk ölçmene yol açar. Kesin başarı sayısı S, belirsiz U ve toplam N ise ASR alt sınırı S/N, üst sınırı (S+U)/N olur. Bu aralık hakemin yanlılığını ortadan kaldırmaz; eksik karardan doğan belirsizliği görünür tutar.

| Yaygın yanlış | Doğru sınır |
|---|---|
| Parse hatası başarısız saldırıdır | Ölçüm altyapısı hatası olarak ayrı tutulur. |

Sonraki bağlantı: ai-uretim-36. [Birincil kaynak](https://arxiv.org/abs/2306.05685). Kaynak mekanizmanın ilgili API veya yöntemini açıklar; bu labın başarı oranının kanıtı yerel ham koşudur.
:::
