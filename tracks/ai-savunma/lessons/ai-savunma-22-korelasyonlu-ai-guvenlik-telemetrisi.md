---
id: ai-savunma-22
title: Korelasyonlu AI Güvenlik Telemetrisi
summary: Kullanıcı isteği, guardrail, model ve araç olaylarını iz kimliğiyle ilişkilendir; eksik, yinelenen, uzun ve sürüm değiştiren zincirleri önce görünür sentetik telemetriyle, sonra yerel Ollama modelinin gerçek araç çağrılı isteğiyle raporla.
timeout: 45
esleme: ai-saldiri-25, ai-savunma-18
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et: Tek olay değil, uçtan uca iz zinciri denetlenir

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| OpenTelemetry her işlemi bir *span* olarak kaydeder. Aynı isteğe ait span'ler ortak bir `trace_id` taşır ve başlangıç/bitiş zamanı, öznitelikler (ör. `gen_ai.request.model`) içerir. SigNoz veya Jaeger bu span'leri zaman çizelgesinde birleştirir. | Görev 1–3: `veri/telemetri_politikasi.json` ve `veri/otel_olaylari.json` içindeki **sentetik** olaylar; span'lerin ders şemasına indirgenmiş tek zamanlı hâli. Son adım: kurulu yerel Ollama modeline araç tanımıyla gerçek bir istek gönderilir, araç modelin verdiği argümanlarla gerçekten çalıştırılır ve olay zamanları gerçek saatle ölçülür. | Dört türlü sabit bir zincir, gerçek uygulamalardaki çok adımlı ajan döngülerini temsil etmez. Olayların "tam" çıkması, guardrail kararının doğru olduğunu göstermez; yalnız loglandığını gösterir. |

> [!NOT]
> Görev 1–3 sentetik veriyle çalışır. Bu görevlerde model, OpenTelemetry veya SigNoz çağrılmaz. Son adımdaki **Gerçek deney** görevi kurulu yerel Ollama modelini araç çağrısıyla gerçekten çalıştırır; yeni model veya araç indirmez. OpenTelemetry ve SigNoz bu derste çalıştırılmaz. `veri/` dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalanır; kopyada yaptığın değişiklik bir sonraki çalıştırmada sıfırlanır, **kalıcılık yoktur**. Kontrol bu dosyalardan ayrı, gizli verilerle sınar. `detay` alanı yapay bir olay etiketidir; gerçek prompt, parola veya gizli veri taşımaz.

OpenTelemetry ve SigNoz gibi araçlar kullanıcı isteği, guardrail kararı, model sürümü ve araç çağrısını aynı iz kimliği altında ilişkilendirebilir. Güvenlik incelemesinde olayların zamanı, türü ve model sürümü birlikte değerlendirilir.

**Neden korelasyon bir güvenlik kontrolüdür?** Bir LLM uygulamasında olaylar farklı bileşenlerden gelir: API ağ geçidi isteği, guardrail servisi kararı, model sunucusu yanıtı, araç yürütücüsü çağrıyı loglar. Bunlar ayrı ayrı bakıldığında her biri "normal" görünebilir. Bir olay müdahalesinde sorulan soru ise zincir sorusudur. "Bu araç çağrısından önce guardrail çalıştı mı?" "Bu yanıtı hangi model sürümü üretti?" Ortak iz kimliği yoksa ya da zincirde bir halka eksikse bu sorulara cevap verilemez. Cevaplanamayan soru da denetimde "kontrol yoktu" diye okunur.
:::

::: anlat Tam zincir dört zorunlu türü bir kez içerir
Bu dersin sözleşmesinde her izde `iste`, `guardrail`, `model`, `arac` türlerinin her biri tam olarak bir kez bulunur. Eksik tür `eksik`, yinelenen tür `yinelenen` nedenidir. Zincir süresi en geç ve en erken olay zamanının farkıdır.

Süre politika sınırını aşarsa `sure`, aynı izde birden çok model sürümü görülürse `surum` nedeni eklenir. Sıfır zaman damgası ve sıfır süre geçerlidir; bool zaman damgası değildir.

`veri/otel_olaylari.json` içindeki üç iz bu nedenlerin gerçek hayattaki karşılıklarını gösterir:

- **`iz-91bc`:** Guardrail zaman aşımına uğrayıp yeniden denenmiştir; iki guardrail olayı vardır (`yinelenen`). İstek 6,3 saniye sürer (`sure`). İstek ortasında model sürümü `q4`'ten `q8`'e geçmiştir (`surum`). Sürüm geçişi, kademeli dağıtım (canary) sırasında tek bir isteğin iki farklı modele yönlendirildiğini düşündürür. Bir güvenlik olayında "hangi model bu yanıtı verdi?" sorusunu belirsiz bırakır.
- **`iz-c044`:** Model yanıtı bir araç çağrısı yaptığını söyler, ama `arac` olayı hiç yoktur. Ya araç loglanmadan çalışmıştır ya da hiç çalışmamıştır. İkisi de araştırılmalıdır.

**Saldırgan bakışı:** Saldırgan iz bırakmamak ister. Guardrail'i atlatan bir yol bulursa, o yolda guardrail olayı hiç oluşmaz. Sayım temelli kontrol bu boşluğu yakalar. Log hattını tıkamak (çok uzun detay, kontrol karakteri, sahte iz kimliği) da bir tekniktir. Bu yüzden olay şeması sıkı doğrulanır ve bozuk olay sessizce düzeltilmez, reddedilir. `detay` alanına ham prompt yazmak ise başka bir risktir: telemetri deposu kişisel veri ve sır deposuna dönüşür. Bu ders detayı yapay etiketle sınırlar.

**Sık tuzaklar:**

- Olayları geliş sırasına göre işlemek. Dağıtık sistemlerde olaylar karışık gelir. Sıralama zaman damgasına, eşitlikte kimliğe göre yapılır.
- Eksik türü fark etmeden yalnız var olanları saymak.
- Boş izi "tam" saymak.
- Süreyi ilk ve son **gelen** olaydan hesaplamak. Doğrusu en erken ve en geç **zaman damgasıdır**.
:::

::: tahmin İz süresini ve kimliklerini tahmin et
Üç çıktı satırını yaz:

```python
olaylar = [{"iz_id": "z-1", "zaman_ms": 20}, {"iz_id": "z-1", "zaman_ms": 5}]
print(max(x["zaman_ms"] for x in olaylar) - min(x["zaman_ms"] for x in olaylar))
print(sorted({x["iz_id"] for x in olaylar}))
print(len(olaylar) == 2)
```

???

```cikti
15
['z-1']
True
```

Olay sayısı, zorunlu türlerin her birinin bulunduğunu tek başına kanıtlamaz; tür bazında sayım gerekir.
:::

::: gorev 1 · Telemetri politikasını doğrula
`telemetri_politikasi_dogrula(politika)` işlevini yaz. Politika tam olarak `max_olay`, `max_sure_ms`, `iz_zorunlu`, `surum_zorunlu` alanlarını taşısın. Olay sınırı bool olmayan 1–100 arası int, süre sınırı bool olmayan 1–60000 arası int olmalıdır.

İz ve sürüm zorunlulukları gerçek `True` olmalıdır. Geçersiz veride `ValueError` yükselt. Politikayı yeni sözlük olarak döndür.

Görünür veri: `veri/telemetri_politikasi.json`. Başlangıç kodu asıl politikayı ve dört bozuk politikayı doğrulamayı dener. Bozukların dördü de reddedilmelidir.

```starter
from ai_savunma_veri import json_yukle

def telemetri_politikasi_dogrula(politika):
    # KUSURLU BAŞLANGIÇ KODU: bool'u int sayıyor, aralıkları ve zorunluluk bayraklarını denetlemiyor, girdinin kendisini döndürüyor!
    if not isinstance(politika.get("max_olay"), int) or not isinstance(politika.get("max_sure_ms"), int):
        raise ValueError("sınırlar int olmalı")
    return politika

veri = json_yukle("veri/telemetri_politikasi.json")
for ad, p in [("asil", veri["politika"])] + [(b["ad"], b["politika"]) for b in veri["bozuk_politikalar"]]:
    try:
        telemetri_politikasi_dogrula(p)
        print(ad, "kabul")
    except ValueError as hata:
        print(ad, "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-22")
```

```test
P = {"max_olay": 20, "max_sure_ms": 1000, "iz_zorunlu": True, "surum_zorunlu": True}
def sozlesme(fn):
    try:
        sonuc = fn(P)
        if sonuc != P or sonuc is P:
            return False
        for alan, deger in [("max_olay", 1), ("max_olay", 100), ("max_sure_ms", 1), ("max_sure_ms", 60000)]:
            if fn(dict(P, **{alan: deger}))[alan] != deger:
                return False
        for politika in [
            None, [], dict(P, ek=1), dict(P, max_olay=0), dict(P, max_olay=101), dict(P, max_olay=True),
            dict(P, max_sure_ms=0), dict(P, max_sure_ms=60001), dict(P, max_sure_ms=False),
            dict(P, iz_zorunlu=False), dict(P, iz_zorunlu=1), dict(P, surum_zorunlu=False), dict(P, surum_zorunlu=1),
        ]:
            try:
                fn(politika)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(telemetri_politikasi_dogrula), "olay, süre, iz ve sürüm politikaları korunmalı")
def m_olay(politika):
    return telemetri_politikasi_dogrula(dict(politika, max_olay=100))
def m_sure(politika):
    return telemetri_politikasi_dogrula(dict(politika, max_sure_ms=60000))
def m_iz(politika):
    sonuc = telemetri_politikasi_dogrula(politika)
    sonuc["iz_zorunlu"] = False
    return sonuc
for ad, mutant in [("olayı büyüten", m_olay), ("süreyi büyüten", m_sure), ("izi kaldıran", m_iz)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
# --- carbon-c8-ek-bas ---
raises(ValueError, telemetri_politikasi_dogrula, dict(P, max_olay=True), msg="max_olay bool ret")
raises(ValueError, telemetri_politikasi_dogrula, dict(P, max_sure_ms=True), msg="max_sure_ms bool ret")
# --- carbon-c8-ek-son ---
```

```solution
def telemetri_politikasi_dogrula(politika):
    if not isinstance(politika, dict):
        raise ValueError("politika sözlük olmalı")
    if set(politika) != {"max_olay", "max_sure_ms", "iz_zorunlu", "surum_zorunlu"}:
        raise ValueError("politika şeması geçersiz")
    if type(politika["max_olay"]) is not int:
        raise ValueError("olay sınırı int olmalı")
    if politika["max_olay"] < 1:
        raise ValueError("olay sınırı pozitif olmalı")
    if politika["max_olay"] > 100:
        raise ValueError("olay sınırı çok büyük")
    if type(politika["max_sure_ms"]) is not int:
        raise ValueError("süre sınırı int olmalı")
    if politika["max_sure_ms"] < 1:
        raise ValueError("süre sınırı pozitif olmalı")
    if politika["max_sure_ms"] > 60000:
        raise ValueError("süre sınırı çok büyük")
    if politika["iz_zorunlu"] is not True:
        raise ValueError("iz kimliği zorunlu olmalı")
    if politika["surum_zorunlu"] is not True:
        raise ValueError("model sürümü zorunlu olmalı")
    return {"max_olay": politika["max_olay"], "max_sure_ms": politika["max_sure_ms"], "iz_zorunlu": True, "surum_zorunlu": True}
```

```hint
İki sayısal sınırı ayrı doğrula. İz ve sürüm bayraklarını `is not True` ile zorunlu tut.
```
:::

::: anlat Olay normalizasyonu sıralamayı deterministik yapar
Her olay benzersiz bir kimlik, ortak iz kimliği, tür, zaman damgası, model sürümü ve yapay detay etiketi taşır. Çıktı önce zaman damgasına, eşitlikte olay kimliğine göre sıralanır.

Kimlikler 1–64 karakterlik ASCII desenine uyar. Model sürümü 1–32 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, nokta, alt çizgi veya tire içeren stringdir. Detay başı/sonu boşluğu olmayan boş olmayan stringdir ve kontrol karakteri içermez.
:::

::: gorev 2 · Telemetri olaylarını doğrula ve sırala
`telemetri_olaylarini_normallestir(olaylar, politika)` işlevini yaz. Politika ilk görevdeki bütün kuralları sağlasın ve olay sayısı sınırını aşan girdi `ValueError` üretsin. Olaylar liste; her kayıt tam olarak `id`, `iz_id`, `tur`, `zaman_ms`, `model_surumu`, `detay` alanlarını taşısın.

Olay kimliği benzersizdir; olay ve iz kimlikleri yukarıdaki 64 karakter desenine uyar. Tür `iste`, `guardrail`, `model`, `arac`; zaman bool olmayan 0 veya pozitif int olmalıdır. Model sürümü ve detay anlatımdaki kurallara uysun. Geçersiz veride `ValueError` yükselt.

Alanları koruyan yeni kayıtları zaman ve kimlik sırasıyla döndür. Boş olayda boş liste döndür ve girdileri değiştirme.

Görünür veri: `veri/otel_olaylari.json`. Olaylar karışık sırada gelir. `t2-guard-a` ile `t2-guard-b` aynı zamandadır; dosyada `b` önce gelir, ama çıktıda kimliğe göre `a` önce olmalıdır. `bozuk_olaylar` reddedilmelidir.

```starter
from ai_savunma_veri import json_yukle

def telemetri_olaylarini_normallestir(olaylar, politika):
    # KUSURLU BAŞLANGIÇ KODU: yalnız zamana göre sıralıyor (eşitlikte giriş sırası kalıyor), olay şemasını ve sayı sınırını denetlemiyor!
    return sorted([dict(o) for o in olaylar], key=lambda o: o["zaman_ms"])

politika = json_yukle("veri/telemetri_politikasi.json")["politika"]
veri = json_yukle("veri/otel_olaylari.json")
for o in telemetri_olaylarini_normallestir(veri["olaylar"], politika):
    print(f"[{o['zaman_ms']:>5}] {o['iz_id']} {o['id']:<11} {o['tur']}")
for o in veri["bozuk_olaylar"]:
    try:
        telemetri_olaylarini_normallestir([o], politika)
        print(o["id"], "KABUL edildi (yanlış)")
    except ValueError as hata:
        print(o["id"], "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-22")
```

```test
import copy
P = {"max_olay": 5, "max_sure_ms": 1000, "iz_zorunlu": True, "surum_zorunlu": True}
O = [
    {"id": "o-2", "iz_id": "z-1", "tur": "model", "zaman_ms": 20, "model_surumu": "v1.2", "detay": "model"},
    {"id": "o-1", "iz_id": "z-1", "tur": "iste", "zaman_ms": 0, "model_surumu": "v1.2", "detay": "istek"},
    {"id": "o-3", "iz_id": "z-1", "tur": "arac", "zaman_ms": 20, "model_surumu": "v1.2", "detay": "araç"},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(O)
        ponce = copy.deepcopy(P)
        beklenen = [O[1], O[0], O[2]]
        if fn(O, P) != beklenen or O != once or P != ponce or fn(list(reversed(O)), P) != beklenen or fn([], P) != []:
            return False
        if fn([dict(O[0], id="a" * 64)], P)[0]["id"] != "a" * 64:
            return False
        if fn([dict(O[0], model_surumu="v" * 32)], P)[0]["model_surumu"] != "v" * 32:
            return False
        if fn(O, dict(P, max_olay=3)) != beklenen:
            return False
        if fn([dict(O[0], detay="model cagrisi")], P)[0]["detay"] != "model cagrisi":
            return False
        for alan, deger in [("max_olay", 1), ("max_olay", 100), ("max_sure_ms", 1), ("max_sure_ms", 60000)]:
            if fn([], dict(P, **{alan: deger})) != []:
                return False
        for olaylar, politika in [
            (None, P), ({}, P), ([None], P), (O, None), (O, dict(P, iz_zorunlu=False)),
            (O, dict(P, surum_zorunlu=False)), (O, dict(P, max_olay=0)), (O, dict(P, max_olay=101)),
            (O, dict(P, max_sure_ms=0)), (O, dict(P, max_olay=2)),
            ([dict(O[0], ek=1)], P), ([dict(O[0], id="a b")], P), ([dict(O[0], id="a" * 65)], P),
            ([O[0], O[0]], P), ([dict(O[0], iz_id="")], P), ([dict(O[0], iz_id="a" * 65)], P),
            ([dict(O[0], tur="diger")], P), ([dict(O[0], zaman_ms=-1)], P), ([dict(O[0], zaman_ms=True)], P),
            ([dict(O[0], model_surumu="")], P), ([dict(O[0], model_surumu="v" * 33)], P),
            ([dict(O[0], model_surumu="v 1")], P), ([dict(O[0], detay="")], P),
            ([dict(O[0], detay=" x")], P), ([dict(O[0], detay="a\0b")], P),
        ]:
            try:
                fn(olaylar, politika)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(telemetri_olaylarini_normallestir), "olay şeması, kimlik, zaman ve sıralama korunmalı")
def m_zaman(olaylar, politika):
    return telemetri_olaylarini_normallestir(sorted(olaylar, key=lambda x: x["id"]), politika)
def m_iz(olaylar, politika):
    return telemetri_olaylarini_normallestir([dict(x, iz_id="sabit") for x in olaylar], politika)
def m_surum(olaylar, politika):
    return telemetri_olaylarini_normallestir([dict(x, model_surumu="v1") for x in olaylar], politika)
for ad, mutant in [("zamanı bozan", m_zaman), ("izi değiştiren", m_iz), ("sürümü değiştiren", m_surum)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
raises(ValueError,telemetri_olaylarini_normallestir,[{'id': None, 'iz_id': 'z-1', 'tur': 'model', 'zaman_ms': 20, 'model_surumu': 'v1.2', 'detay': 'model'}, {'id': 'o-1', 'iz_id': 'z-1', 'tur': 'iste', 'zaman_ms': 0, 'model_surumu': 'v1.2', 'detay': 'istek'}, {'id': 'o-3', 'iz_id': 'z-1', 'tur': 'arac', 'zaman_ms': 20, 'model_surumu': 'v1.2', 'detay': 'araç'}],{'max_olay': 5, 'max_sure_ms': 1000, 'iz_zorunlu': True, 'surum_zorunlu': True},msg="hatalı alan istisna türü: mutant:424:33:Add->Sub")
# --- carbon-c8-ek-bas ---
raises(ValueError, telemetri_olaylarini_normallestir, O, dict(P, max_olay=True), msg="max_olay bool ret")
raises(ValueError, telemetri_olaylarini_normallestir, O, dict(P, max_sure_ms=True), msg="max_sure_ms bool ret")
raises(ValueError, telemetri_olaylarini_normallestir, [dict(O[0], id=123)], P, msg="id str olmalı")
raises(ValueError, telemetri_olaylarini_normallestir, [dict(O[0], iz_id=123)], P, msg="iz_id str olmalı")
raises(ValueError, telemetri_olaylarini_normallestir, [dict(O[0], zaman_ms=True)], P, msg="zaman_ms bool ret")
raises(ValueError, telemetri_olaylarini_normallestir, [dict(O[0], model_surumu=123)], P, msg="model_surumu str olmalı")
raises(ValueError, telemetri_olaylarini_normallestir, [dict(O[0], detay=123)], P, msg="detay str olmalı")
raises(ValueError, telemetri_olaylarini_normallestir, [dict(O[0], detay="a\x1fb")], P, msg="0x1f kontrol karakteri ret")
raises(ValueError, telemetri_olaylarini_normallestir, [dict(O[0], iz_id="")], dict(P, iz_zorunlu=False), msg="boş iz_id zorunlu değilken de ret")
raises(ValueError, telemetri_olaylarini_normallestir, [dict(O[0], model_surumu="")], dict(P, surum_zorunlu=False), msg="boş sürüm zorunlu değilken de ret")
raises(ValueError, telemetri_olaylarini_normallestir, O, dict(P, ek=1), msg="politika fazla alan ret")
raises(ValueError, telemetri_olaylarini_normallestir, O, dict(P, max_olay="5"), msg="max_olay str olamaz")
raises(ValueError, telemetri_olaylarini_normallestir, O, dict(P, max_olay=0), msg="max_olay 0 olamaz")
raises(ValueError, telemetri_olaylarini_normallestir, O, dict(P, max_sure_ms=60001), msg="max_sure_ms 60001 ret")
ok(isinstance(telemetri_olaylarini_normallestir(O[:1], dict(P, max_olay=1, max_sure_ms=60000)), list), "max_olay=1 ve max_sure_ms=60000 geçerli")
raises(ValueError, telemetri_olaylarini_normallestir, [], dict(P, max_olay=0), msg="boş listede max_olay=0 ret")
# --- carbon-c8-ek-son ---
```

```solution
def telemetri_olaylarini_normallestir(olaylar, politika):
    import re
    if not isinstance(politika, dict):
        raise ValueError("politika sözlük olmalı")
    if set(politika) != {"max_olay", "max_sure_ms", "iz_zorunlu", "surum_zorunlu"}:
        raise ValueError("politika şeması geçersiz")
    if type(politika["max_olay"]) is not int:
        raise ValueError("olay sınırı int olmalı")
    if politika["max_olay"] < 1:
        raise ValueError("olay sınırı pozitif olmalı")
    if politika["max_olay"] > 100:
        raise ValueError("olay sınırı çok büyük")
    if type(politika["max_sure_ms"]) is not int:
        raise ValueError("süre sınırı int olmalı")
    if politika["max_sure_ms"] < 1:
        raise ValueError("süre sınırı pozitif olmalı")
    if politika["max_sure_ms"] > 60000:
        raise ValueError("süre sınırı çok büyük")
    if politika["iz_zorunlu"] is not True:
        raise ValueError("iz kimliği zorunlu olmalı")
    if politika["surum_zorunlu"] is not True:
        raise ValueError("model sürümü zorunlu olmalı")
    if not isinstance(olaylar, list):
        raise ValueError("olaylar liste olmalı")
    if len(olaylar) > politika["max_olay"]:
        raise ValueError("olay sayısı sınırı aşıyor")
    kimlikler = set()
    sonuc = []
    for olay in olaylar:
        if not isinstance(olay, dict):
            raise ValueError("olay sözlük olmalı")
        if set(olay) != {"id", "iz_id", "tur", "zaman_ms", "model_surumu", "detay"}:
            raise ValueError("olay şeması geçersiz")
        for alan in ("id", "iz_id"):
            if not isinstance(olay[alan], str):
                raise ValueError(alan + " string olmalı")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", olay[alan]):
                raise ValueError(alan + " geçersiz")
        if olay["id"] in kimlikler:
            raise ValueError("olay kimliği yinelenemez")
        kimlikler.add(olay["id"])
        if olay["tur"] not in ("iste", "guardrail", "model", "arac"):
            raise ValueError("olay türü geçersiz")
        if type(olay["zaman_ms"]) is not int:
            raise ValueError("zaman int olmalı")
        if olay["zaman_ms"] < 0:
            raise ValueError("zaman negatif olamaz")
        if not isinstance(olay["model_surumu"], str):
            raise ValueError("model sürümü string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,31}", olay["model_surumu"]):
            raise ValueError("model sürümü geçersiz")
        detay = olay["detay"]
        if not isinstance(detay, str):
            raise ValueError("detay string olmalı")
        if not detay or detay != detay.strip():
            raise ValueError("detay boşluk biçimi geçersiz")
        if any(ord(karakter) < 32 for karakter in detay):
            raise ValueError("detay kontrol karakteri içeremez")
        sonuc.append({"id": olay["id"], "iz_id": olay["iz_id"], "tur": olay["tur"], "zaman_ms": olay["zaman_ms"], "model_surumu": olay["model_surumu"], "detay": detay})
    return sorted(sonuc, key=lambda x: (x["zaman_ms"], x["id"]))
```

```hint
Olayları yeni sözlüklerle oluştur. Zaman ve kimlik için `(zaman_ms, id)` sıralama anahtarı kullan.
```
:::

::: anlat Korelasyon raporu eksik ve tutarsız zinciri gizlemez
Her iz için tür sayımları, süre ve benzersiz model sürümleri hesaplanır. Neden sırası `eksik`, `yinelenen`, `sure`, `surum` şeklindedir. Dört türün her biri bir kez bulunuyor, süre sınırda veya altında ve tek model sürümü varsa zincir `tam` olur.

Rapordaki sürüm listesi alfabetik sıralıdır. Süre, izdeki mevcut olayların en erken ve en geç zamanından hesaplanır; eksik tür olması süre hesabını engellemez.
:::

::: gorev 3 · Korelasyonlu iz zinciri raporu üret
`korelasyonlu_iz_raporu(olaylar, politika)` işlevini yaz. Girdi ve politika ikinci görevdeki bütün kuralları sağlasın; geçersiz veride `ValueError` yükselt. Olayları `iz_id` alanına göre grupla ve her iz için dört zorunlu türü say.

Eksik veya yinelenen türleri, süre aşımını ve birden çok model sürümünü belirtilen neden sırasıyla raporla. Her kayıt `{"iz_id":IZ,"karar":"hatali" if nedenler else "tam","nedenler":[...],"sure_ms":SURE,"model_surumleri":[...]}` olsun.

İz kimliğine göre sırala, boş olayda boş liste döndür ve girdileri değiştirme.

Görünür veri: aynı iki dosya. Doğru raporda `iz-7f3a` `tam`, `iz-91bc` `["yinelenen","sure","surum"]`, `iz-c044` `["eksik"]` olur.

```starter
from ai_savunma_veri import json_yukle

def korelasyonlu_iz_raporu(olaylar, politika):
    # KUSURLU BAŞLANGIÇ KODU: yalnız var olan türleri sayıyor (eksik türü görmüyor), süreyi ilk ve son GELEN olaydan hesaplıyor ve sürüm değişimini denetlemiyor!
    izler = {}
    for o in olaylar:
        izler.setdefault(o["iz_id"], []).append(o)
    rapor = []
    for iz_id in sorted(izler):
        grup = izler[iz_id]
        sayim = {}
        for o in grup:
            sayim[o["tur"]] = sayim.get(o["tur"], 0) + 1
        sure = grup[-1]["zaman_ms"] - grup[0]["zaman_ms"]
        nedenler = []
        if any(v > 1 for v in sayim.values()):
            nedenler.append("yinelenen")
        if sure > politika["max_sure_ms"]:
            nedenler.append("sure")
        rapor.append({"iz_id": iz_id, "karar": "hatali" if nedenler else "tam", "nedenler": nedenler,
                      "sure_ms": sure, "model_surumleri": sorted({o["model_surumu"] for o in grup})})
    return rapor

politika = json_yukle("veri/telemetri_politikasi.json")["politika"]
veri = json_yukle("veri/otel_olaylari.json")
for r in korelasyonlu_iz_raporu(veri["olaylar"], politika):
    print(r["iz_id"], r["karar"], r["nedenler"], f"{r['sure_ms']} ms", r["model_surumleri"])
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-22")
```

```test
import copy
P = {"max_olay": 10, "max_sure_ms": 100, "iz_zorunlu": True, "surum_zorunlu": True}
O = [
    {"id": "a-1", "iz_id": "z-a", "tur": "iste", "zaman_ms": 0, "model_surumu": "v1", "detay": "istek"},
    {"id": "a-2", "iz_id": "z-a", "tur": "guardrail", "zaman_ms": 20, "model_surumu": "v1", "detay": "karar"},
    {"id": "a-3", "iz_id": "z-a", "tur": "model", "zaman_ms": 30, "model_surumu": "v1", "detay": "model"},
    {"id": "a-4", "iz_id": "z-a", "tur": "arac", "zaman_ms": 100, "model_surumu": "v1", "detay": "araç"},
    {"id": "b-1", "iz_id": "z-b", "tur": "iste", "zaman_ms": 0, "model_surumu": "v1", "detay": "istek"},
    {"id": "b-2", "iz_id": "z-b", "tur": "guardrail", "zaman_ms": 200, "model_surumu": "v1", "detay": "karar"},
    {"id": "b-3", "iz_id": "z-b", "tur": "guardrail", "zaman_ms": 250, "model_surumu": "v2", "detay": "tekrar"},
    {"id": "b-4", "iz_id": "z-b", "tur": "model", "zaman_ms": 300, "model_surumu": "v2", "detay": "model"},
]
BEKLENEN = [
    {"iz_id": "z-a", "karar": "tam", "nedenler": [], "sure_ms": 100, "model_surumleri": ["v1"]},
    {"iz_id": "z-b", "karar": "hatali", "nedenler": ["eksik", "yinelenen", "sure", "surum"], "sure_ms": 300, "model_surumleri": ["v1", "v2"]},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(O)
        ponce = copy.deepcopy(P)
        if fn(O, P) != BEKLENEN or O != once or P != ponce or fn(list(reversed(O)), P) != BEKLENEN or fn([], P) != []:
            return False
        if fn(O[:4], dict(P, max_sure_ms=99))[0]["nedenler"] != ["sure"]:
            return False
        if fn([dict(x, zaman_ms=0) for x in O[:4]], P)[0]["sure_ms"] != 0:
            return False
        if fn(O[:3], P)[0]["nedenler"] != ["eksik"]:
            return False
        if fn(O, dict(P, max_olay=8)) != BEKLENEN:
            return False
        if fn([dict(O[0], detay="istek kaydi")], P)[0]["iz_id"] != "z-a":
            return False
        for alan, deger in [("max_olay", 1), ("max_olay", 100), ("max_sure_ms", 1), ("max_sure_ms", 60000)]:
            if fn([], dict(P, **{alan: deger})) != []:
                return False
        for olaylar, politika in [
            (None, P), ({}, P), ([None], P), (O, None), (O, dict(P, iz_zorunlu=False)),
            (O, dict(P, surum_zorunlu=False)), (O, dict(P, max_olay=0)), (O, dict(P, max_olay=7)),
            (O, dict(P, max_olay=101)),
            (O, dict(P, max_sure_ms=0)), (O, dict(P, max_sure_ms=60001)),
            ([dict(O[0], ek=1)], P), ([dict(O[0], id="a" * 65)], P), ([O[0], O[0]], P),
            ([dict(O[0], iz_id="a b")], P), ([dict(O[0], tur="diger")], P),
            ([dict(O[0], zaman_ms=-1)], P), ([dict(O[0], zaman_ms=True)], P),
            ([dict(O[0], model_surumu="v" * 33)], P), ([dict(O[0], detay="")], P),
        ]:
            try:
                fn(olaylar, politika)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(korelasyonlu_iz_raporu), "tür sayımı, süre, sürüm ve iz gruplama korunmalı")
def m_tur(olaylar, politika):
    return korelasyonlu_iz_raporu([x for x in olaylar if x["tur"] != "arac"], politika)
def m_surum(olaylar, politika):
    return korelasyonlu_iz_raporu([dict(x, model_surumu="v1") for x in olaylar], politika)
def m_sure(olaylar, politika):
    return korelasyonlu_iz_raporu(olaylar, dict(politika, max_sure_ms=60000))
for ad, mutant in [("türü silen", m_tur), ("sürümü eşitleyen", m_surum), ("süreyi büyüten", m_sure)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

raises(ValueError,korelasyonlu_iz_raporu,[dict(O[0],detay=' istek ')]+O[1:],P,msg='detay baş/son boşluğu ret')
raises(ValueError,korelasyonlu_iz_raporu,[{'id': None, 'iz_id': 'z-a', 'tur': 'iste', 'zaman_ms': 0, 'model_surumu': 'v1', 'detay': 'istek'}, {'id': 'a-2', 'iz_id': 'z-a', 'tur': 'guardrail', 'zaman_ms': 20, 'model_surumu': 'v1', 'detay': 'karar'}, {'id': 'a-3', 'iz_id': 'z-a', 'tur': 'model', 'zaman_ms': 30, 'model_surumu': 'v1', 'detay': 'model'}, {'id': 'a-4', 'iz_id': 'z-a', 'tur': 'arac', 'zaman_ms': 100, 'model_surumu': 'v1', 'detay': 'araç'}, {'id': 'b-1', 'iz_id': 'z-b', 'tur': 'iste', 'zaman_ms': 0, 'model_surumu': 'v1', 'detay': 'istek'}, {'id': 'b-2', 'iz_id': 'z-b', 'tur': 'guardrail', 'zaman_ms': 200, 'model_surumu': 'v1', 'detay': 'karar'}, {'id': 'b-3', 'iz_id': 'z-b', 'tur': 'guardrail', 'zaman_ms': 250, 'model_surumu': 'v2', 'detay': 'tekrar'}, {'id': 'b-4', 'iz_id': 'z-b', 'tur': 'model', 'zaman_ms': 300, 'model_surumu': 'v2', 'detay': 'model'}],{'max_olay': 10, 'max_sure_ms': 100, 'iz_zorunlu': True, 'surum_zorunlu': True},msg="hatalı alan istisna türü: mutant:549:33:Add->Sub")
eq(korelasyonlu_iz_raporu([dict(x,zaman_ms=x["zaman_ms"]+1000) for x in O],P),korelasyonlu_iz_raporu(O,P),"iz süreleri başlangıç anından bağımsız")
# --- carbon-c8-ek-bas ---
raises(ValueError, korelasyonlu_iz_raporu, O, dict(P, max_olay=True), msg="max_olay bool ret")
raises(ValueError, korelasyonlu_iz_raporu, O, dict(P, max_sure_ms=True), msg="max_sure_ms bool ret")
raises(ValueError, korelasyonlu_iz_raporu, [dict(O[0], id=123)], P, msg="id str olmalı")
raises(ValueError, korelasyonlu_iz_raporu, [dict(O[0], iz_id=123)], P, msg="iz_id str olmalı")
raises(ValueError, korelasyonlu_iz_raporu, [dict(O[0], zaman_ms=True)], P, msg="zaman_ms bool ret")
raises(ValueError, korelasyonlu_iz_raporu, [dict(O[0], model_surumu=123)], P, msg="model_surumu str olmalı")
raises(ValueError, korelasyonlu_iz_raporu, [dict(O[0], detay=123)], P, msg="detay str olmalı")
raises(ValueError, korelasyonlu_iz_raporu, [dict(O[0], detay="a\x1fb")], P, msg="0x1f kontrol karakteri ret")
raises(ValueError, korelasyonlu_iz_raporu, [dict(O[0], iz_id="")], dict(P, iz_zorunlu=False), msg="boş iz_id ret")
raises(ValueError, korelasyonlu_iz_raporu, [dict(O[0], model_surumu="")], dict(P, surum_zorunlu=False), msg="boş sürüm ret")
raises(ValueError, korelasyonlu_iz_raporu, O, dict(P, ek=1), msg="politika fazla alan ret")
raises(ValueError, korelasyonlu_iz_raporu, O, dict(P, max_olay="5"), msg="max_olay str olamaz")
raises(ValueError, korelasyonlu_iz_raporu, O, dict(P, max_olay=0), msg="max_olay 0 olamaz")
ok(isinstance(korelasyonlu_iz_raporu(O[:1], dict(P, max_olay=1)), (list, dict)), "max_olay=1 geçerli")
raises(ValueError, korelasyonlu_iz_raporu, [], dict(P, max_olay=0), msg="boş listede max_olay=0 ret")
# --- carbon-c8-ek-son ---
```

```solution
def korelasyonlu_iz_raporu(olaylar, politika):
    import re
    if not isinstance(politika, dict):
        raise ValueError("politika sözlük olmalı")
    if set(politika) != {"max_olay", "max_sure_ms", "iz_zorunlu", "surum_zorunlu"}:
        raise ValueError("politika şeması geçersiz")
    if type(politika["max_olay"]) is not int:
        raise ValueError("olay sınırı int olmalı")
    if politika["max_olay"] < 1:
        raise ValueError("olay sınırı pozitif olmalı")
    if politika["max_olay"] > 100:
        raise ValueError("olay sınırı çok büyük")
    if type(politika["max_sure_ms"]) is not int:
        raise ValueError("süre sınırı int olmalı")
    if politika["max_sure_ms"] < 1:
        raise ValueError("süre sınırı pozitif olmalı")
    if politika["max_sure_ms"] > 60000:
        raise ValueError("süre sınırı çok büyük")
    if politika["iz_zorunlu"] is not True:
        raise ValueError("iz kimliği zorunlu olmalı")
    if politika["surum_zorunlu"] is not True:
        raise ValueError("model sürümü zorunlu olmalı")
    if not isinstance(olaylar, list):
        raise ValueError("olaylar liste olmalı")
    if len(olaylar) > politika["max_olay"]:
        raise ValueError("olay sayısı sınırı aşıyor")
    kimlikler = set()
    gruplar = {}
    for olay in olaylar:
        if not isinstance(olay, dict):
            raise ValueError("olay sözlük olmalı")
        if set(olay) != {"id", "iz_id", "tur", "zaman_ms", "model_surumu", "detay"}:
            raise ValueError("olay şeması geçersiz")
        for alan in ("id", "iz_id"):
            if not isinstance(olay[alan], str):
                raise ValueError(alan + " string olmalı")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", olay[alan]):
                raise ValueError(alan + " geçersiz")
        if olay["id"] in kimlikler:
            raise ValueError("olay kimliği yinelenemez")
        kimlikler.add(olay["id"])
        if olay["tur"] not in ("iste", "guardrail", "model", "arac"):
            raise ValueError("olay türü geçersiz")
        if type(olay["zaman_ms"]) is not int:
            raise ValueError("zaman int olmalı")
        if olay["zaman_ms"] < 0:
            raise ValueError("zaman negatif olamaz")
        if not isinstance(olay["model_surumu"], str):
            raise ValueError("model sürümü string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,31}", olay["model_surumu"]):
            raise ValueError("model sürümü geçersiz")
        detay = olay["detay"]
        if not isinstance(detay, str):
            raise ValueError("detay string olmalı")
        if not detay or detay != detay.strip():
            raise ValueError("detay boşluk biçimi geçersiz")
        if any(ord(karakter) < 32 for karakter in detay):
            raise ValueError("detay kontrol karakteri içeremez")
        gruplar.setdefault(olay["iz_id"], []).append(olay)
    sonuc = []
    for iz_id, kayitlar in gruplar.items():
        nedenler = []
        sayim = {tur: 0 for tur in ("iste", "guardrail", "model", "arac")}
        for kayit in kayitlar:
            sayim[kayit["tur"]] += 1
        if any(sayim[tur] == 0 for tur in sayim):
            nedenler.append("eksik")
        if any(sayim[tur] > 1 for tur in sayim):
            nedenler.append("yinelenen")
        zamanlar = [x["zaman_ms"] for x in kayitlar]
        sure = max(zamanlar) - min(zamanlar)
        if sure > politika["max_sure_ms"]:
            nedenler.append("sure")
        surumler = sorted({x["model_surumu"] for x in kayitlar})
        if len(surumler) > 1:
            nedenler.append("surum")
        sonuc.append({"iz_id": iz_id, "karar": "hatali" if nedenler else "tam", "nedenler": nedenler, "sure_ms": sure, "model_surumleri": surumler})
    return sorted(sonuc, key=lambda x: x["iz_id"])
```

```hint
Tür sayımlarını sözlükte tut. Eksik ve yinelenen kontrollerini ayrı yap; süre ve sürüm nedenlerini sonra ekle.
```
:::

::: anlat Korelasyon, gerçek bir istek zincirinde anlam kazanır
Görev 1–3'te olaylar elle yazılmış bir dosyadan geliyordu. Bu adımda olayları **gerçek bir istek** üretir. `sandbox/ai_gercek_ai_savunma_22.py` deneyi şunları yapar:

1. Kurulu yerel Ollama modellerinden araç çağrısını destekleyen ilk model seçilir. Model adı, sürüm etiketine çevrilerek her olaya yazılır.
2. **iste** olayı zaman 0'da oluşur. **guardrail** olayı, istek metninde bilinen iki injection kalıbını arayan küçük ama gerçek bir kontrolün bitiş zamanında yazılır.
3. Modele "5 ile 3'ü topla aracını kullanarak topla" isteği `topla` araç tanımıyla gönderilir (sıcaklık 0, tohum 7). **model** olayı modelin yanıt döndüğü gerçek zamanda yazılır; detayında gerçek süre ve token sayısı bulunur.
4. Model aracı çağırdıysa araç, modelin verdiği argümanlarla **gerçekten çalıştırılır** ve **arac** olayı sonucu taşır. Model aracı çağırmadıysa arac olayı yazılmaz. Model ne metin ne araç çağrısı döndürürse deney "tamamlanmadı" diye durur.
5. Karşılaştırma için aynı koşudan ikinci bir iz kurulur. Bu izde guardrail ve araç olayları loglanmamış gibi davranılır; zincirde yalnız iste ve model vardır.

Test önce işlevini gizli deterministik olaylarla sınar. Ardından gerçek olaylardan ürettiğin raporu bağımsız bir referans hesapla birebir karşılaştırır. Eksik iz `eksik` nedeni almak zorundadır. Modelin aracı çağırması kabul koşulu **değildir**. Çağırmazsa doğru rapor gerçek izi de `eksik` sayar ve bu da doğru bir ölçümdür. Ham araç çağrıları, model yanıtı ve bütün olaylar kanıta yazılır.

Ders yazılırken bu makinede `qwen3:4b-instruct-2507` modeli `topla(a=5, b=3)` çağrısını yaptı. Araç 8 sonucunu döndürdü, model yanıtı koşudan koşuya 6–9 saniye sürdü ve gerçek iz `tam` çıktı. Sınırları unutma: "tam" yalnız dört olayın loglandığını gösterir. Guardrail'in doğru karar verdiğini, aracın yetkili olduğunu ya da modelin sonucu doğru aktardığını göstermez. Bunlar ayrı kontrollerin işidir.

:::

::: gorev Gerçek deney · Gerçek istek zincirinden korelasyon
`korelasyonlu_iz_raporu(olaylar, politika)` işlevini yaz. Kuralları ve çıktısı 3. görevdekiyle **aynıdır**. Deney gerçek modeli bir araçla koşar ve tek iz kimliğiyle gerçek zaman damgalı olaylar üretir. Senin raporun her izi doğru nedenlerle işaretlemelidir; eksik zincir `eksik` nedeniyle `hatali` olur. `sandbox.ai_gercek_ai_savunma_22` içindeki `korelasyonlu_iz_raporu_referans` yalnız test içindir; onu import etmek veya kaynağını okuyup çalıştırmak Kontrol'de reddedilir.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def korelasyonlu_iz_raporu(olaylar, politika):
    # KUSURLU BAŞLANGIÇ KODU: yalnız var olan türleri sayıyor; guardrail ve araç olayı hiç loglanmamış izi "tam" sayıyor!
    izler = {}
    for o in olaylar:
        izler.setdefault(o["iz_id"], []).append(o)
    rapor = []
    for iz_id in sorted(izler):
        grup = izler[iz_id]
        turler = [o["tur"] for o in grup]
        zamanlar = [o["zaman_ms"] for o in grup]
        surumler = sorted({o["model_surumu"] for o in grup})
        nedenler = [n for n, k in (("yinelenen", len(turler) != len(set(turler))),
                                    ("sure", max(zamanlar) - min(zamanlar) > politika["max_sure_ms"]),
                                    ("surum", len(surumler) > 1)) if k]
        rapor.append({"iz_id": iz_id, "karar": "hatali" if nedenler else "tam", "nedenler": nedenler,
                      "sure_ms": max(zamanlar) - min(zamanlar), "model_surumleri": surumler})
    return rapor

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_22 as deney
    deney.goster(korelasyonlu_iz_raporu)
```

```test
import ast
import ai_lab
from sandbox import ai_gercek_ai_savunma_22 as D
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
_yasak = ("korelasyonlu_iz_raporu_referans", "kanit_yaz")
sorun = ai_lab.kod_denetimi(src, yasak=_yasak)
for n in ast.walk(ast.parse(src)):
    if isinstance(n, ast.ImportFrom) and any(a.name in _yasak or a.name == "*" for a in n.names):
        sorun.append("referans importu yasak")
    if isinstance(n, (ast.Import, ast.ImportFrom)):
        adlar = [a.name for a in n.names] + ([n.module] if isinstance(n, ast.ImportFrom) and n.module else [])
        if any(a and a.split(".")[0] in ("inspect", "importlib", "runpy") for a in adlar):
            sorun.append("kaynak okuma/dinamik import yasak")
    if isinstance(n, ast.Name) and n.id in ("exec", "eval", "compile", "__builtins__"):
        sorun.append("dinamik kod çalıştırma yasak: " + n.id)
if not kontrol(not sorun, "Kendi korelasyonlu_iz_raporu işlevini yaz; laboratuvar/referans kullanımı yasak: " + "; ".join(sorted(set(sorun)))):
    stop()
fn = need("korelasyonlu_iz_raporu")
P = {"max_olay": 10, "max_sure_ms": 60000, "iz_zorunlu": True, "surum_zorunlu": True}
O = [
    {"id": "a-1", "iz_id": "z-a", "tur": "iste", "zaman_ms": 0, "model_surumu": "v1", "detay": "istek"},
    {"id": "a-2", "iz_id": "z-a", "tur": "guardrail", "zaman_ms": 20, "model_surumu": "v1", "detay": "karar"},
    {"id": "a-3", "iz_id": "z-a", "tur": "model", "zaman_ms": 30, "model_surumu": "v1", "detay": "model"},
    {"id": "a-4", "iz_id": "z-a", "tur": "arac", "zaman_ms": 100, "model_surumu": "v1", "detay": "arac"},
    {"id": "b-1", "iz_id": "z-b", "tur": "iste", "zaman_ms": 0, "model_surumu": "v1", "detay": "istek"},
    {"id": "b-2", "iz_id": "z-b", "tur": "model", "zaman_ms": 30, "model_surumu": "v1", "detay": "model"},
]
BEKLENEN = [
    {"iz_id": "z-a", "karar": "tam", "nedenler": [], "sure_ms": 100, "model_surumleri": ["v1"]},
    {"iz_id": "z-b", "karar": "hatali", "nedenler": ["eksik"], "sure_ms": 30, "model_surumleri": ["v1"]},
]
def sozlesme(f):
    try:
        if f(O, P) != BEKLENEN or f([], P) != [] or f(list(reversed(O)), P) != BEKLENEN:
            return False
        karma = O[:4] + [dict(O[1], id="a-5", zaman_ms=60100, model_surumu="v2")]
        if f(karma, P) != [{"iz_id": "z-a", "karar": "hatali", "nedenler": ["yinelenen", "sure", "surum"], "sure_ms": 60100, "model_surumleri": ["v1", "v2"]}]:
            return False
        if f(O[:4], dict(P, max_sure_ms=100))[0]["karar"] != "tam":
            return False
        for bozuk in (None, [None], [dict(O[0], ek=1)], [dict(O[0], tur="diger")], [dict(O[0], model_surumu="v 1")],
                      [dict(O[0], zaman_ms=True)], [dict(O[0], detay=" istek")], [O[0], O[0]], O * 2):
            try:
                f(bozuk, P)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(fn), "tür sayımı, süre, sürüm ve iz gruplama korunmalı")
r, oz = None, None
# --- carbon-c8-g4-bas ---
def _c8_birim_denetimi():
    _u = []
    def _same(got, exp):
        try:
            if not bool(got == exp):
                return False
        except Exception:
            return False
        if isinstance(exp, bool) or isinstance(got, bool):
            return isinstance(got, bool) and isinstance(exp, bool)
        if isinstance(exp, (int, float)) and isinstance(got, (int, float)):
            return True
        return isinstance(got, type(exp))
    def ok(cond, msg=None, got=None):
        _u.append(bool(cond))
        return bool(cond)
    def eq(got, exp, msg=None):
        r = _same(got, exp)
        _u.append(r)
        return r
    def yakin(got, exp, msg=None, tol=1e-6):
        try:
            r = abs(got - exp) <= tol
        except Exception:
            r = False
        _u.append(bool(r))
        return bool(r)
    def raises(exc, fn_cagri, *a, msg=None, **kw):
        try:
            fn_cagri(*a, **kw)
        except exc:
            _u.append(True)
            return True
        except Exception:
            _u.append(False)
            return False
        _u.append(False)
        return False
    korelasyonlu_iz_raporu = need('korelasyonlu_iz_raporu')
    def _birim_adim_3():
        import copy
        P = {"max_olay": 10, "max_sure_ms": 100, "iz_zorunlu": True, "surum_zorunlu": True}
        O = [
            {"id": "a-1", "iz_id": "z-a", "tur": "iste", "zaman_ms": 0, "model_surumu": "v1", "detay": "istek"},
            {"id": "a-2", "iz_id": "z-a", "tur": "guardrail", "zaman_ms": 20, "model_surumu": "v1", "detay": "karar"},
            {"id": "a-3", "iz_id": "z-a", "tur": "model", "zaman_ms": 30, "model_surumu": "v1", "detay": "model"},
            {"id": "a-4", "iz_id": "z-a", "tur": "arac", "zaman_ms": 100, "model_surumu": "v1", "detay": "araç"},
            {"id": "b-1", "iz_id": "z-b", "tur": "iste", "zaman_ms": 0, "model_surumu": "v1", "detay": "istek"},
            {"id": "b-2", "iz_id": "z-b", "tur": "guardrail", "zaman_ms": 200, "model_surumu": "v1", "detay": "karar"},
            {"id": "b-3", "iz_id": "z-b", "tur": "guardrail", "zaman_ms": 250, "model_surumu": "v2", "detay": "tekrar"},
            {"id": "b-4", "iz_id": "z-b", "tur": "model", "zaman_ms": 300, "model_surumu": "v2", "detay": "model"},
        ]
        BEKLENEN = [
            {"iz_id": "z-a", "karar": "tam", "nedenler": [], "sure_ms": 100, "model_surumleri": ["v1"]},
            {"iz_id": "z-b", "karar": "hatali", "nedenler": ["eksik", "yinelenen", "sure", "surum"], "sure_ms": 300, "model_surumleri": ["v1", "v2"]},
        ]
        def sozlesme(fn):
            try:
                once = copy.deepcopy(O)
                ponce = copy.deepcopy(P)
                if fn(O, P) != BEKLENEN or O != once or P != ponce or fn(list(reversed(O)), P) != BEKLENEN or fn([], P) != []:
                    return False
                if fn(O[:4], dict(P, max_sure_ms=99))[0]["nedenler"] != ["sure"]:
                    return False
                if fn([dict(x, zaman_ms=0) for x in O[:4]], P)[0]["sure_ms"] != 0:
                    return False
                if fn(O[:3], P)[0]["nedenler"] != ["eksik"]:
                    return False
                if fn(O, dict(P, max_olay=8)) != BEKLENEN:
                    return False
                if fn([dict(O[0], detay="istek kaydi")], P)[0]["iz_id"] != "z-a":
                    return False
                for alan, deger in [("max_olay", 1), ("max_olay", 100), ("max_sure_ms", 1), ("max_sure_ms", 60000)]:
                    if fn([], dict(P, **{alan: deger})) != []:
                        return False
                for olaylar, politika in [
                    (None, P), ({}, P), ([None], P), (O, None), (O, dict(P, iz_zorunlu=False)),
                    (O, dict(P, surum_zorunlu=False)), (O, dict(P, max_olay=0)), (O, dict(P, max_olay=7)),
                    (O, dict(P, max_olay=101)),
                    (O, dict(P, max_sure_ms=0)), (O, dict(P, max_sure_ms=60001)),
                    ([dict(O[0], ek=1)], P), ([dict(O[0], id="a" * 65)], P), ([O[0], O[0]], P),
                    ([dict(O[0], iz_id="a b")], P), ([dict(O[0], tur="diger")], P),
                    ([dict(O[0], zaman_ms=-1)], P), ([dict(O[0], zaman_ms=True)], P),
                    ([dict(O[0], model_surumu="v" * 33)], P), ([dict(O[0], detay="")], P),
                ]:
                    try:
                        fn(olaylar, politika)
                        return False
                    except ValueError:
                        pass
                return True
            except Exception:
                return False
        ok(sozlesme(korelasyonlu_iz_raporu), "tür sayımı, süre, sürüm ve iz gruplama korunmalı")
        def m_tur(olaylar, politika):
            return korelasyonlu_iz_raporu([x for x in olaylar if x["tur"] != "arac"], politika)
        def m_surum(olaylar, politika):
            return korelasyonlu_iz_raporu([dict(x, model_surumu="v1") for x in olaylar], politika)
        def m_sure(olaylar, politika):
            return korelasyonlu_iz_raporu(olaylar, dict(politika, max_sure_ms=60000))
        for ad, mutant in [("türü silen", m_tur), ("sürümü eşitleyen", m_surum), ("süreyi büyüten", m_sure)]:
            ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

        raises(ValueError,korelasyonlu_iz_raporu,[dict(O[0],detay=' istek ')]+O[1:],P,msg='detay baş/son boşluğu ret')
        raises(ValueError,korelasyonlu_iz_raporu,[{'id': None, 'iz_id': 'z-a', 'tur': 'iste', 'zaman_ms': 0, 'model_surumu': 'v1', 'detay': 'istek'}, {'id': 'a-2', 'iz_id': 'z-a', 'tur': 'guardrail', 'zaman_ms': 20, 'model_surumu': 'v1', 'detay': 'karar'}, {'id': 'a-3', 'iz_id': 'z-a', 'tur': 'model', 'zaman_ms': 30, 'model_surumu': 'v1', 'detay': 'model'}, {'id': 'a-4', 'iz_id': 'z-a', 'tur': 'arac', 'zaman_ms': 100, 'model_surumu': 'v1', 'detay': 'araç'}, {'id': 'b-1', 'iz_id': 'z-b', 'tur': 'iste', 'zaman_ms': 0, 'model_surumu': 'v1', 'detay': 'istek'}, {'id': 'b-2', 'iz_id': 'z-b', 'tur': 'guardrail', 'zaman_ms': 200, 'model_surumu': 'v1', 'detay': 'karar'}, {'id': 'b-3', 'iz_id': 'z-b', 'tur': 'guardrail', 'zaman_ms': 250, 'model_surumu': 'v2', 'detay': 'tekrar'}, {'id': 'b-4', 'iz_id': 'z-b', 'tur': 'model', 'zaman_ms': 300, 'model_surumu': 'v2', 'detay': 'model'}],{'max_olay': 10, 'max_sure_ms': 100, 'iz_zorunlu': True, 'surum_zorunlu': True},msg="hatalı alan istisna türü: mutant:549:33:Add->Sub")
        eq(korelasyonlu_iz_raporu([dict(x,zaman_ms=x["zaman_ms"]+1000) for x in O],P),korelasyonlu_iz_raporu(O,P),"iz süreleri başlangıç anından bağımsız")
        raises(ValueError, korelasyonlu_iz_raporu, O, dict(P, max_olay=True), msg="max_olay bool ret")
        raises(ValueError, korelasyonlu_iz_raporu, O, dict(P, max_sure_ms=True), msg="max_sure_ms bool ret")
        raises(ValueError, korelasyonlu_iz_raporu, [dict(O[0], id=123)], P, msg="id str olmalı")
        raises(ValueError, korelasyonlu_iz_raporu, [dict(O[0], iz_id=123)], P, msg="iz_id str olmalı")
        raises(ValueError, korelasyonlu_iz_raporu, [dict(O[0], zaman_ms=True)], P, msg="zaman_ms bool ret")
        raises(ValueError, korelasyonlu_iz_raporu, [dict(O[0], model_surumu=123)], P, msg="model_surumu str olmalı")
        raises(ValueError, korelasyonlu_iz_raporu, [dict(O[0], detay=123)], P, msg="detay str olmalı")
        raises(ValueError, korelasyonlu_iz_raporu, [dict(O[0], detay="a\x1fb")], P, msg="0x1f kontrol karakteri ret")
        raises(ValueError, korelasyonlu_iz_raporu, [dict(O[0], iz_id="")], dict(P, iz_zorunlu=False), msg="boş iz_id ret")
        raises(ValueError, korelasyonlu_iz_raporu, [dict(O[0], model_surumu="")], dict(P, surum_zorunlu=False), msg="boş sürüm ret")
        raises(ValueError, korelasyonlu_iz_raporu, O, dict(P, ek=1), msg="politika fazla alan ret")
        raises(ValueError, korelasyonlu_iz_raporu, O, dict(P, max_olay="5"), msg="max_olay str olamaz")
        raises(ValueError, korelasyonlu_iz_raporu, O, dict(P, max_olay=0), msg="max_olay 0 olamaz")
        ok(isinstance(korelasyonlu_iz_raporu(O[:1], dict(P, max_olay=1)), (list, dict)), "max_olay=1 geçerli")
        raises(ValueError, korelasyonlu_iz_raporu, [], dict(P, max_olay=0), msg="boş listede max_olay=0 ret")
    try:
        _birim_adim_3()
    except Exception:
        _u.append(False)
    return bool(_u) and all(_u)
kontrol(_c8_birim_denetimi(), "deney öncesi tam birim sözleşmesi korunmalı")
# --- carbon-c8-g4-son ---
if all(sonuclar):
    try:
        r = D.deney(fn)
    except ai_lab.GercekLabYok as e:
        kontrol(False, f"GERÇEK MODEL YOK, deney yapılmadı: {e}")
        stop()
    kontrol(r["eksik_karar"] == "hatali" and "eksik" in (r["eksik_nedenler"] or []),
            "guardrail ve araç olayı loglanmamış zincir hatalı (eksik) olarak işaretlendi")
    if r["cagrilan"]:
        kontrol(r["arac"] and r["arac"]["hata"] is None, f"model aracı çağırdı ve araç gerçekten çalıştırıldı: {r['arac']}")
    bagimsiz = D.korelasyonlu_iz_raporu_referans([dict(o) for o in r["olaylar"]], dict(D.POLITIKA))
    kontrol(r["rapor"] == bagimsiz, f"gerçek olaylardaki rapor bağımsız hesapla aynı olmalı: senin {r['rapor']} · beklenen {bagimsiz}")
    oz = D.ozet(r)
yol = ai_lab.kanit_yaz("savunma-telemetri", {"kaynak": "gercek", "kabul": all(sonuclar), "ders": "ai-savunma-22",
                                             "ortam": (r or {}).get("ortam"), "ozet": oz, "ham": D.ham(r) if r else None})
if oz:
    ok(True, f"BULGU ({r['ortam']['model']['ad']}): gerçek istek zinciri — çağrılan araç {oz['cagrilan_arac']} ({oz['arac']}), model {oz['model_sure_ms']}ms/{oz['tokens']} token; "
             f"gerçek iz → {oz['tam_karar']} {oz['tam_nedenler']} (süre {oz['tam_sure_ms']}ms), loglanmamış iz → {oz['eksik_karar']} {oz['eksik_nedenler']}. "
             f"Modelin aracı çağırması kabul koşulu değildir; ham olaylar kanıtta.")
```

```solution
import ai_lab

def korelasyonlu_iz_raporu(olaylar, politika):
    import re
    if not isinstance(politika, dict):
        raise ValueError("politika sözlük olmalı")
    if set(politika) != {"max_olay", "max_sure_ms", "iz_zorunlu", "surum_zorunlu"}:
        raise ValueError("politika şeması geçersiz")
    if type(politika["max_olay"]) is not int:
        raise ValueError("olay sınırı int olmalı")
    if politika["max_olay"] < 1:
        raise ValueError("olay sınırı pozitif olmalı")
    if politika["max_olay"] > 100:
        raise ValueError("olay sınırı çok büyük")
    if type(politika["max_sure_ms"]) is not int:
        raise ValueError("süre sınırı int olmalı")
    if politika["max_sure_ms"] < 1:
        raise ValueError("süre sınırı pozitif olmalı")
    if politika["max_sure_ms"] > 60000:
        raise ValueError("süre sınırı çok büyük")
    if politika["iz_zorunlu"] is not True:
        raise ValueError("iz kimliği zorunlu olmalı")
    if politika["surum_zorunlu"] is not True:
        raise ValueError("model sürümü zorunlu olmalı")
    if not isinstance(olaylar, list):
        raise ValueError("olaylar liste olmalı")
    if len(olaylar) > politika["max_olay"]:
        raise ValueError("olay sayısı sınırı aşıyor")
    kimlikler = set()
    gruplar = {}
    for olay in olaylar:
        if not isinstance(olay, dict):
            raise ValueError("olay sözlük olmalı")
        if set(olay) != {"id", "iz_id", "tur", "zaman_ms", "model_surumu", "detay"}:
            raise ValueError("olay şeması geçersiz")
        for alan in ("id", "iz_id"):
            if not isinstance(olay[alan], str):
                raise ValueError(alan + " string olmalı")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", olay[alan]):
                raise ValueError(alan + " geçersiz")
        if olay["id"] in kimlikler:
            raise ValueError("olay kimliği yinelenemez")
        kimlikler.add(olay["id"])
        if olay["tur"] not in ("iste", "guardrail", "model", "arac"):
            raise ValueError("olay türü geçersiz")
        if type(olay["zaman_ms"]) is not int:
            raise ValueError("zaman int olmalı")
        if olay["zaman_ms"] < 0:
            raise ValueError("zaman negatif olamaz")
        if not isinstance(olay["model_surumu"], str):
            raise ValueError("model sürümü string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,31}", olay["model_surumu"]):
            raise ValueError("model sürümü geçersiz")
        detay = olay["detay"]
        if not isinstance(detay, str):
            raise ValueError("detay string olmalı")
        if not detay or detay != detay.strip():
            raise ValueError("detay boşluk biçimi geçersiz")
        if any(ord(karakter) < 32 for karakter in detay):
            raise ValueError("detay kontrol karakteri içeremez")
        gruplar.setdefault(olay["iz_id"], []).append(olay)
    sonuc = []
    for iz_id, kayitlar in gruplar.items():
        nedenler = []
        sayim = {tur: 0 for tur in ("iste", "guardrail", "model", "arac")}
        for kayit in kayitlar:
            sayim[kayit["tur"]] += 1
        if any(sayim[tur] == 0 for tur in sayim):
            nedenler.append("eksik")
        if any(sayim[tur] > 1 for tur in sayim):
            nedenler.append("yinelenen")
        zamanlar = [x["zaman_ms"] for x in kayitlar]
        sure = max(zamanlar) - min(zamanlar)
        if sure > politika["max_sure_ms"]:
            nedenler.append("sure")
        surumler = sorted({x["model_surumu"] for x in kayitlar})
        if len(surumler) > 1:
            nedenler.append("surum")
        sonuc.append({"iz_id": iz_id, "karar": "hatali" if nedenler else "tam", "nedenler": nedenler, "sure_ms": sure, "model_surumleri": surumler})
    return sorted(sonuc, key=lambda x: x["iz_id"])

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_22 as deney
    deney.goster(korelasyonlu_iz_raporu)
```

```hint
Bu işlev 3. görevdeki `korelasyonlu_iz_raporu` ile birebir aynıdır; tek fark, olayların gerçek bir model+araç koşusundan gelmesidir. Tür sayımlarını tut; eksik/yinelenen/süre/sürüm nedenlerini sırayla ekle.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Korelasyon kimliği kanıt zincirini kurar

Bir model isteği retrieval ve araç çağrılarıyla aynı trace içinde izlenir. Yanlış parent veya kayıp olay, başarı raporunun eksik zincire dayanmasına yol açar. Zaman ve kimlik tutarlılığı doğrulanırken ham sırların loga alınmaması gerekir. Korelasyon olayların ilişkisini gösterir; olay içeriğinin doğru veya saldırının engellendiğinin tek başına kanıtı değildir.

| Yaygın yanlış | Mekanizmanın sınırı |
|---|---|
| Aynı trace ID bütün adımları doğrular | Ebeveyn ilişkisi, durum ve kanıt alanları ayrıca kontrol edilir. |

Saldırı–savunma bağlantısı: ai-saldiri-25.
:::

::: anlat Kaynak ile lab sonucunu ayır
[OpenTelemetry traces](https://opentelemetry.io/docs/concepts/signals/traces/). Trace/span bağlamı olay ilişkisini açıklar; bu yerel JSON olay zinciri tam bir OpenTelemetry dağıtımı değildir.
:::
