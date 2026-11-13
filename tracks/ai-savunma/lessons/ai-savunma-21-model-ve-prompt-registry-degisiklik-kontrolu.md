---
id: ai-savunma-21
title: Model ve Prompt Registry Değişiklik Kontrolü
summary: Model, prompt ve guardrail değişikliklerinde bağımsız onay, içerik özeti, geri alma ve ileri sürüm koşullarını denetle; önce görünür sentetik registry kayıtlarıyla, sonra gerçek prompt özetleri ve yerel Ollama modeliyle sına.
timeout: 45
esleme: ai-saldiri-47, ai-savunma-36
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et: Registry kaydı onaylı değişikliğin kanıtıdır

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| MLflow Model Registry model sürümlerini, aşamalarını ve etiketlerini tutar. Git tabanlı bir prompt deposunda her değişiklik bir commit ve pull request ile gelir. Dal koruma kuralları (ör. "en az 2 onay, yazar sayılmaz") bağımsız onayı zorunlu kılar. | Görev 1–3: `veri/registry_politikasi.json` ve `veri/degisiklik_kayitlari.json` içindeki **sentetik** registry dışa aktarımı. Son adım: iki prompt sürümünün SHA-256 özeti gerçekten hesaplanır ve kurulu yerel Ollama modeli aynı belgeyi her iki sürümle gerçekten özetler. | Özet farkı yalnız baytların değiştiğini gösterir. Değişikliğin daha güvenli olduğunu ya da modelin davranışını iyileştirdiğini göstermez. Onaycı adları ve kayıtlar uydurmadır; gerçek bir kimlik doğrulama sistemi denetlenmez. |

> [!NOT]
> Görev 1–3 sentetik veriyle çalışır. Bu görevlerde MLflow, Git veya model çağrılmaz. Son adımdaki **Gerçek deney** görevi kurulu yerel Ollama modelini gerçekten çalıştırır; yeni model veya araç indirmez. MLflow ve Git bu derste çalıştırılmaz. `veri/` dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalanır; kopyada yaptığın değişiklik bir sonraki çalıştırmada sıfırlanır, **kalıcılık yoktur**. Kontrol bu dosyalardan ayrı, gizli verilerle sınar.

MLflow veya Git tabanlı bir registry, model, sistem promptu ve guardrail sürümlerini kayıt altına alabilir. Ancak bir kaydın bulunması, üretime alınmaya uygun olduğunu göstermez. Bağımsız onay, değişen içerik özeti ve çalışan bir geri alma hedefi birlikte aranır.

**Neden prompt da bir "sürüm"dür?** Bir LLM uygulamasında sistem promptu ve guardrail kuralları, model ağırlıkları kadar davranışı belirler. "Bu kodu asla yazma" cümlesini silen tek satırlık bir prompt değişikliği, bir model güncellemesinden daha büyük güvenlik etkisi yaratabilir. Buna rağmen promptlar çoğu zaman bir yapılandırma dosyasında ya da veritabanı satırında, onaysız ve izsiz değiştirilir. Registry denetimi bu değişiklikleri de modelle aynı kurala bağlar: kim değiştirdi, kim onayladı, içerik gerçekten ne oldu, sorun çıkarsa hangi sürüme dönülecek.
:::

::: anlat Sahip onayı bağımsız onay sayılmaz
Değişiklik sahibi `onaycilar` listesinde bulunsa bile bağımsız onay sayısına katılmaz. Yalnız sahip dışındaki benzersiz onaycılar sayılır. Onaycı listesindeki yineleme biçim hatasıdır; sayıyı yapay olarak büyütmez.

Yeni sürüm aktif sürümden büyük, geri alma sürümü ise yeni sürümden küçük olmalıdır. İlk sürüm için aktif sürüm sıfır olabilir. Önceki ve yeni SHA-256 özetleri aynıysa içerik değişikliği yoktur.

`veri/degisiklik_kayitlari.json` içindeki `prompt-v4-sahip` kaydında sahip `ayse`, onaycılar `["ayse", "mehmet"]`. Liste iki kişilik görünür, ama bağımsız onay sayısı birdir. Bu, "dört göz" ilkesinin en sık delindiği yerdir: değişikliği yapan kişi kendi değişikliğini onaylayamaz. `prompt-ilk` kaydı ise ilk sürümdür ve aktif sürümü 0'dır. Kuralın sonucu ilk bakışta şaşırtıcıdır: geri dönülecek daha eski bir sürüm olmadığı için `geri_alma` nedeniyle karantinaya girer. Gerçek hayatta ilk yayın için "geri alma = özelliği kapat" gibi ayrı bir plan yazılır. Bu ders o istisnayı modellemez ve fail-closed kalır.

**Saldırgan bakışı:** İçeriden bir saldırgan ya da ele geçirilmiş bir hesap, güvenlik kuralını gevşeten bir prompt değişikliğini şu yollarla gizlemeye çalışır:

- **Sahte sürüm:** Sürümü artırır ama içeriği aynı bırakır. Kayıt "bir şey güncellendi" der, oysa gerçek değişiklik başka bir yoldan, kayıtsız yapılmıştır.
- **Kendi kendine onay:** Onaycı listesine kendini ekler.
- **Aynı sürümü tekrar yayınlama:** Aktif sürümle aynı numarayı tekrar yayınlar ve içeriği sessizce değiştirir (`model-v6-tekrar`).
- **Geri alma hedefini bozma:** Geri alma sürümünü yeni sürüme eşit yazar. Sorun çıktığında "geri dönülen" sürüm aynı bozuk sürüm olur (`model-v7`).

**Özet anlamı değil baytı ölçer.** SHA-256 metne tek bir boşluk eklense bile tamamen değişir. Bu yüzden özet "içerik değişti mi?" sorusuna kesin cevap verir, ama "anlamlı ve güvenli bir değişiklik mi?" sorusuna cevap vermez. Gerçek deneyde bunu doğrudan göreceksin. Sık görülen tuzaklar şunlardır:

- Onaycı listesindeki yinelemeyi sessizce teke indirmek. Yineleme bir biçim hatasıdır, reddedilir.
- Büyük harfli özeti normalleştirip kabul etmek.
- Sürümleri string olarak karşılaştırmak (`"10" < "9"`).
- Geri almada `>` yerine `>=` kullanmamak, yani eşit sürümü kabul etmek.
:::

::: tahmin Bağımsız onay ve sürüm koşullarını tahmin et
Üç çıktı satırını yaz:

```python
sahip = "ayse"
onaycilar = ["ayse", "mehmet", "deniz"]
print([x for x in onaycilar if x != sahip])
print(3 > 0 and 2 < 3)
print("a" * 64 == "a" * 64)
```

???

```cikti
['mehmet', 'deniz']
True
True
```

Son satırdaki özet eşitliği, değişiklik yayını açısından bir ihlaldir.
:::

::: gorev 1 · Registry değişiklik politikasını doğrula
`registry_politikasi_dogrula(politika)` işlevini yaz. Politika tam olarak `izinli_turler`, `min_onay`, `geri_alma_zorunlu`, `ozet_degismeli` alanlarını taşısın. Türler `model`, `prompt`, `guardrail` değerlerinden oluşan boş olmayan ve yinelenmeyen listedir.

Minimum onay bool olmayan 1–5 arası int olmalıdır. Geri alma zorunluluğu ve özet değişim zorunluluğu gerçek `True` olmalıdır. Geçersiz veride `ValueError` yükselt. Politikayı yeni listeyle döndür; girdiyi değiştirme.

Görünür veri: `veri/registry_politikasi.json`. Başlangıç kodu asıl politikayı ve dört bozuk politikayı doğrulamayı dener. Bozukların dördü de reddedilmelidir.

```starter
from ai_savunma_veri import json_yukle

def registry_politikasi_dogrula(politika):
    # KUSURLU BAŞLANGIÇ KODU: geri alma ve özet bayraklarını hiç denetlemiyor, onay sınırında bool ve 0'ı kabul ediyor, tür değerlerini denetlemiyor ve girdinin kendisini döndürüyor!
    if not isinstance(politika.get("izinli_turler"), list) or not politika["izinli_turler"]:
        raise ValueError("tür listesi gerekli")
    if not isinstance(politika.get("min_onay"), int):
        raise ValueError("onay sınırı int olmalı")
    return politika

veri = json_yukle("veri/registry_politikasi.json")
for ad, p in [("asil", veri["politika"])] + [(b["ad"], b["politika"]) for b in veri["bozuk_politikalar"]]:
    try:
        registry_politikasi_dogrula(p)
        print(ad, "kabul")
    except ValueError as hata:
        print(ad, "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-21")
```

```test
import copy
P = {"izinli_turler": ["model", "prompt"], "min_onay": 2, "geri_alma_zorunlu": True, "ozet_degismeli": True}
def sozlesme(fn):
    try:
        once = copy.deepcopy(P)
        sonuc = fn(P)
        if sonuc != P or P != once or sonuc is P or sonuc["izinli_turler"] is P["izinli_turler"]:
            return False
        for sinir in (1, 5):
            if fn(dict(P, min_onay=sinir))["min_onay"] != sinir:
                return False
        for politika in [
            None, [], dict(P, ek=1), dict(P, izinli_turler=[]), dict(P, izinli_turler=None),
            dict(P, izinli_turler=["model", "model"]), dict(P, izinli_turler=["dosya"]),
            dict(P, min_onay=0), dict(P, min_onay=6), dict(P, min_onay=True),
            dict(P, geri_alma_zorunlu=False), dict(P, geri_alma_zorunlu=1),
            dict(P, ozet_degismeli=False), dict(P, ozet_degismeli=1),
        ]:
            try:
                fn(politika)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(registry_politikasi_dogrula), "tür, onay, geri alma ve özet politikaları korunmalı")
def m_tur(politika):
    sonuc = registry_politikasi_dogrula(politika)
    sonuc["izinli_turler"].append("guardrail")
    return sonuc
def m_onay(politika):
    return registry_politikasi_dogrula(dict(politika, min_onay=1))
def m_geri(politika):
    sonuc = registry_politikasi_dogrula(politika)
    sonuc["geri_alma_zorunlu"] = False
    return sonuc
for ad, mutant in [("türü açan", m_tur), ("onayı azaltan", m_onay), ("geri almayı kaldıran", m_geri)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
# --- carbon-c8-ek-bas ---
raises(ValueError, registry_politikasi_dogrula, dict(P, izinli_turler=[123]), msg="izinli tür str olmalı")
raises(ValueError, registry_politikasi_dogrula, dict(P, min_onay=True), msg="min_onay bool ret")
raises(ValueError, registry_politikasi_dogrula, dict(P, izinli_turler=tuple(P["izinli_turler"])), msg="izinli_turler tuple olamaz")
# --- carbon-c8-ek-son ---
```

```solution
def registry_politikasi_dogrula(politika):
    if not isinstance(politika, dict):
        raise ValueError("politika sözlük olmalı")
    if set(politika) != {"izinli_turler", "min_onay", "geri_alma_zorunlu", "ozet_degismeli"}:
        raise ValueError("politika şeması geçersiz")
    turler = politika["izinli_turler"]
    if not isinstance(turler, list):
        raise ValueError("türler liste olmalı")
    if not turler:
        raise ValueError("tür listesi boş olamaz")
    if len(set(turler)) != len(turler):
        raise ValueError("türler yinelenemez")
    if any(tur not in ("model", "prompt", "guardrail") for tur in turler):
        raise ValueError("tür geçersiz")
    if type(politika["min_onay"]) is not int:
        raise ValueError("onay sınırı int olmalı")
    if politika["min_onay"] < 1:
        raise ValueError("onay sınırı pozitif olmalı")
    if politika["min_onay"] > 5:
        raise ValueError("onay sınırı çok büyük")
    if politika["geri_alma_zorunlu"] is not True:
        raise ValueError("geri alma zorunlu olmalı")
    if politika["ozet_degismeli"] is not True:
        raise ValueError("özet değişimi zorunlu olmalı")
    return {"izinli_turler": list(turler), "min_onay": politika["min_onay"], "geri_alma_zorunlu": True, "ozet_degismeli": True}
```

```hint
Tür listesini ve sayısal onay sınırını ayrı doğrula. İki güvenlik bayrağını `is not True` ile fail-closed denetle.
```
:::

::: anlat Değişiklik raporu bağımsız onayı ve geri almayı denetler
Tür politika dışındaysa `tur`; sahip dışındaki onay sayısı yetersizse `onay`; geri alma sürümü yeni sürüme eşit veya büyükse `geri_alma`; iki özet aynıysa `ozet` nedeni üretilir. Nedenler bu sıradadır.

Geri alma sürümü pozitif, yeni sürüm en az birdir. Her onaycı ve sahip geçerli bir kimlik taşır; ancak kimliğin biçimsel olarak geçerli olması onay sayısını otomatik artırmaz.
:::

::: gorev 2 · Registry değişikliklerini denetle
`registry_degisiklikleri_denetle(kayitlar, politika)` işlevini yaz. Politika ilk görevdeki bütün kuralları sağlasın. Kayıtlar liste; her kayıt tam olarak `id`, `tur`, `surum`, `sahip`, `onaycilar`, `onceki_ozet`, `yeni_ozet`, `geri_alma_surumu` alanlarını taşısın.

Kimlik, sahip ve her onaycı 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren stringdir. Kayıt kimliği benzersizdir. Tür `model`, `prompt`, `guardrail`; sürüm ve geri alma sürümü bool olmayan pozitif int olmalıdır. Onaycılar yinelenmeyen listedir. İki özet de 64 küçük onaltılık karakterdir. Geçersiz veride `ValueError` yükselt.

Dört karar nedenini sırayla uygula. Her kayıt için `{"id":ID,"karar":"karantina" if nedenler else "aday","nedenler":[...]}` döndür. Kimliğe göre sırala, boş kayıtta boş liste döndür ve girdileri değiştirme.

Görünür veri: `veri/degisiklik_kayitlari.json` içindeki `denetim_kayitlari` ve `bozuk_kayitlar`. `prompt-v4-sahip` kaydında sahip kendi değişikliğini onaylamıştır. `model-v7` kaydında geri alma sürümü yeni sürüme eşittir.

```starter
from ai_savunma_veri import json_yukle

def registry_degisiklikleri_denetle(kayitlar, politika):
    # KUSURLU BAŞLANGIÇ KODU: sahibi de onay sayıyor, geri almada eşit sürümü kabul ediyor (>= olmalı) ve kayıt şemasını doğrulamıyor!
    sonuc = []
    for k in kayitlar:
        nedenler = []
        if k["tur"] not in politika["izinli_turler"]:
            nedenler.append("tur")
        if len(set(k["onaycilar"])) < politika["min_onay"]:
            nedenler.append("onay")
        if k["geri_alma_surumu"] > k["surum"]:
            nedenler.append("geri_alma")
        if k["onceki_ozet"] == k["yeni_ozet"]:
            nedenler.append("ozet")
        sonuc.append({"id": k["id"], "karar": "karantina" if nedenler else "aday", "nedenler": nedenler})
    return sorted(sonuc, key=lambda x: x["id"])

politika = json_yukle("veri/registry_politikasi.json")["politika"]
veri = json_yukle("veri/degisiklik_kayitlari.json")
for s in registry_degisiklikleri_denetle(veri["denetim_kayitlari"], politika):
    print(s["id"], s["karar"], s["nedenler"])
for k in veri["bozuk_kayitlar"]:
    try:
        registry_degisiklikleri_denetle([k], politika)
        print(k["id"], "KABUL edildi (yanlış)")
    except ValueError as hata:
        print(k["id"], "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-21")
```

```test
import copy
P = {"izinli_turler": ["model", "prompt"], "min_onay": 2, "geri_alma_zorunlu": True, "ozet_degismeli": True}
K = [
    {"id": "aday-1", "tur": "model", "surum": 3, "sahip": "ayse", "onaycilar": ["ayse", "mehmet", "deniz"], "onceki_ozet": "a" * 64, "yeni_ozet": "b" * 64, "geri_alma_surumu": 2},
    {"id": "onay-1", "tur": "prompt", "surum": 2, "sahip": "ayse", "onaycilar": ["ayse", "mehmet"], "onceki_ozet": "c" * 64, "yeni_ozet": "d" * 64, "geri_alma_surumu": 1},
    {"id": "ret-1", "tur": "guardrail", "surum": 4, "sahip": "ayse", "onaycilar": ["ayse"], "onceki_ozet": "e" * 64, "yeni_ozet": "e" * 64, "geri_alma_surumu": 4},
]
BEKLENEN = [
    {"id": "aday-1", "karar": "aday", "nedenler": []},
    {"id": "onay-1", "karar": "karantina", "nedenler": ["onay"]},
    {"id": "ret-1", "karar": "karantina", "nedenler": ["tur", "onay", "geri_alma", "ozet"]},
]
def sozlesme(fn):
    try:
        konce = copy.deepcopy(K)
        ponce = copy.deepcopy(P)
        if fn(K, P) != BEKLENEN or K != konce or P != ponce or fn(list(reversed(K)), P) != BEKLENEN or fn([], P) != []:
            return False
        if fn([dict(K[0], id="a" * 64)], P)[0]["id"] != "a" * 64:
            return False
        if fn([dict(K[0], onaycilar=["mehmet"])], dict(P, min_onay=1))[0]["karar"] != "aday":
            return False
        for sinir in (1, 5):
            if fn([], dict(P, min_onay=sinir)) != []:
                return False
        for kayitlar, politika in [
            (None, P), ({}, P), ([None], P), (K, None), (K, dict(P, geri_alma_zorunlu=False)),
            (K, dict(P, ozet_degismeli=False)), (K, dict(P, izinli_turler=[])),
            (K, dict(P, min_onay=0)), (K, dict(P, min_onay=6)),
            ([dict(K[0], ek=1)], P), ([dict(K[0], id="a b")], P), ([dict(K[0], id="a" * 65)], P),
            ([K[0], K[0]], P), ([dict(K[0], tur="dosya")], P), ([dict(K[0], surum=0)], P),
            ([dict(K[0], surum=True)], P), ([dict(K[0], geri_alma_surumu=0)], P),
            ([dict(K[0], sahip="")], P), ([dict(K[0], sahip="a" * 65)], P),
            ([dict(K[0], onaycilar=None)], P), ([dict(K[0], onaycilar=["mehmet", "mehmet"])], P),
            ([dict(K[0], onaycilar=["a b"])], P), ([dict(K[0], onaycilar=["a" * 65])], P),
            ([dict(K[0], onceki_ozet="a" * 63)], P),
            ([dict(K[0], yeni_ozet="A" * 64)], P),
        ]:
            try:
                fn(kayitlar, politika)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(registry_degisiklikleri_denetle), "bağımsız onay, geri alma ve özet kuralları korunmalı")
def m_onay(kayitlar, politika):
    return registry_degisiklikleri_denetle([dict(x, onaycilar=["mehmet", "deniz"]) for x in kayitlar], politika)
def m_geri(kayitlar, politika):
    return registry_degisiklikleri_denetle([dict(x, geri_alma_surumu=1) for x in kayitlar], politika)
def m_ozet(kayitlar, politika):
    return registry_degisiklikleri_denetle([dict(x, yeni_ozet=x["onceki_ozet"] + "0") for x in kayitlar], politika)
for ad, mutant in [("onayı düzelten", m_onay), ("geri almayı düzelten", m_geri), ("özeti silen", m_ozet)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
raises(ValueError,registry_degisiklikleri_denetle,[{'id': None, 'tur': 'model', 'surum': 3, 'sahip': 'ayse', 'onaycilar': ['ayse', 'mehmet', 'deniz'], 'onceki_ozet': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'yeni_ozet': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 'geri_alma_surumu': 2}, {'id': 'onay-1', 'tur': 'prompt', 'surum': 2, 'sahip': 'ayse', 'onaycilar': ['ayse', 'mehmet'], 'onceki_ozet': 'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc', 'yeni_ozet': 'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd', 'geri_alma_surumu': 1}, {'id': 'ret-1', 'tur': 'guardrail', 'surum': 4, 'sahip': 'ayse', 'onaycilar': ['ayse'], 'onceki_ozet': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee', 'yeni_ozet': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee', 'geri_alma_surumu': 4}],{'izinli_turler': ['model', 'prompt'], 'min_onay': 2, 'geri_alma_zorunlu': True, 'ozet_degismeli': True},msg="hatalı alan ValueError sözleşmesi: mutant:511:33:Add->Sub")
raises(ValueError,registry_degisiklikleri_denetle,[{'id': 'aday-1', 'tur': 'model', 'surum': 3, 'sahip': 'ayse', 'onaycilar': ['ayse', 'mehmet', 'deniz'], 'onceki_ozet': None, 'yeni_ozet': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 'geri_alma_surumu': 2}, {'id': 'onay-1', 'tur': 'prompt', 'surum': 2, 'sahip': 'ayse', 'onaycilar': ['ayse', 'mehmet'], 'onceki_ozet': 'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc', 'yeni_ozet': 'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd', 'geri_alma_surumu': 1}, {'id': 'ret-1', 'tur': 'guardrail', 'surum': 4, 'sahip': 'ayse', 'onaycilar': ['ayse'], 'onceki_ozet': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee', 'yeni_ozet': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee', 'geri_alma_surumu': 4}],{'izinli_turler': ['model', 'prompt'], 'min_onay': 2, 'geri_alma_zorunlu': True, 'ozet_degismeli': True},msg="hatalı alan ValueError sözleşmesi: mutant:557:33:Add->Sub")
# --- carbon-c8-ek-bas ---
raises(ValueError, registry_degisiklikleri_denetle, K, dict(P, izinli_turler=[123]), msg="izinli tür str olmalı")
raises(ValueError, registry_degisiklikleri_denetle, K, dict(P, min_onay=True), msg="min_onay bool ret")
raises(ValueError, registry_degisiklikleri_denetle, [dict(K[0], id=123)], P, msg="id str olmalı")
raises(ValueError, registry_degisiklikleri_denetle, [dict(K[0], tur=123)], P, msg="tür str olmalı")
raises(ValueError, registry_degisiklikleri_denetle, [dict(K[0], surum=True)], P, msg="sürüm bool ret")
raises(ValueError, registry_degisiklikleri_denetle, [dict(K[0], sahip=123)], P, msg="sahip str olmalı")
raises(ValueError, registry_degisiklikleri_denetle, [dict(K[0], onaycilar=[123])], P, msg="onaycı str olmalı")
raises(ValueError, registry_degisiklikleri_denetle, [dict(K[0], onceki_ozet=123)], P, msg="önceki özet str olmalı")
raises(ValueError, registry_degisiklikleri_denetle, [dict(K[0], yeni_ozet=123)], P, msg="yeni özet str olmalı")
raises(ValueError, registry_degisiklikleri_denetle, [dict(K[0], geri_alma_surumu=True)], P, msg="geri_alma_surumu bool ret")
raises(ValueError, registry_degisiklikleri_denetle, K, dict(P, ek=1), msg="politika fazla alan ret")
raises(ValueError, registry_degisiklikleri_denetle, K, dict(P, izinli_turler=tuple(P["izinli_turler"])), msg="izinli_turler tuple olamaz")
raises(ValueError, registry_degisiklikleri_denetle, K, dict(P, izinli_turler=P["izinli_turler"] + [P["izinli_turler"][0]]), msg="yinelenen izinli tür ret")
# --- carbon-c8-ek-son ---
```

```solution
def registry_degisiklikleri_denetle(kayitlar, politika):
    import re
    if not isinstance(politika, dict):
        raise ValueError("politika sözlük olmalı")
    if set(politika) != {"izinli_turler", "min_onay", "geri_alma_zorunlu", "ozet_degismeli"}:
        raise ValueError("politika şeması geçersiz")
    if not isinstance(politika["izinli_turler"], list):
        raise ValueError("türler liste olmalı")
    if not politika["izinli_turler"]:
        raise ValueError("tür listesi boş olamaz")
    if len(set(politika["izinli_turler"])) != len(politika["izinli_turler"]):
        raise ValueError("türler yinelenemez")
    if any(tur not in ("model", "prompt", "guardrail") for tur in politika["izinli_turler"]):
        raise ValueError("tür geçersiz")
    if type(politika["min_onay"]) is not int:
        raise ValueError("onay sınırı int olmalı")
    if politika["min_onay"] < 1:
        raise ValueError("onay sınırı pozitif olmalı")
    if politika["min_onay"] > 5:
        raise ValueError("onay sınırı çok büyük")
    if politika["geri_alma_zorunlu"] is not True:
        raise ValueError("geri alma zorunlu olmalı")
    if politika["ozet_degismeli"] is not True:
        raise ValueError("özet değişimi zorunlu olmalı")
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    kimlikler = set()
    sonuc = []
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"id", "tur", "surum", "sahip", "onaycilar", "onceki_ozet", "yeni_ozet", "geri_alma_surumu"}:
            raise ValueError("kayıt şeması geçersiz")
        for alan in ("id", "sahip"):
            if not isinstance(kayit[alan], str):
                raise ValueError(alan + " string olmalı")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit[alan]):
                raise ValueError(alan + " geçersiz")
        if kayit["id"] in kimlikler:
            raise ValueError("kimlik yinelenemez")
        kimlikler.add(kayit["id"])
        if kayit["tur"] not in ("model", "prompt", "guardrail"):
            raise ValueError("tür geçersiz")
        for alan in ("surum", "geri_alma_surumu"):
            if type(kayit[alan]) is not int:
                raise ValueError(alan + " int olmalı")
            if kayit[alan] < 1:
                raise ValueError(alan + " pozitif olmalı")
        onaycilar = kayit["onaycilar"]
        if not isinstance(onaycilar, list):
            raise ValueError("onaycılar liste olmalı")
        if len(set(onaycilar)) != len(onaycilar):
            raise ValueError("onaycılar yinelenemez")
        for onayci in onaycilar:
            if not isinstance(onayci, str):
                raise ValueError("onaycı string olmalı")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", onayci):
                raise ValueError("onaycı geçersiz")
        for alan in ("onceki_ozet", "yeni_ozet"):
            if not isinstance(kayit[alan], str):
                raise ValueError(alan + " string olmalı")
            if not re.fullmatch(r"[0-9a-f]{64}", kayit[alan]):
                raise ValueError(alan + " geçersiz")
        nedenler = []
        if kayit["tur"] not in politika["izinli_turler"]:
            nedenler.append("tur")
        bagimsiz = [x for x in onaycilar if x != kayit["sahip"]]
        if len(bagimsiz) < politika["min_onay"]:
            nedenler.append("onay")
        if kayit["geri_alma_surumu"] >= kayit["surum"]:
            nedenler.append("geri_alma")
        if kayit["onceki_ozet"] == kayit["yeni_ozet"]:
            nedenler.append("ozet")
        sonuc.append({"id": kayit["id"], "karar": "karantina" if nedenler else "aday", "nedenler": nedenler})
    return sorted(sonuc, key=lambda x: x["id"])
```

```hint
Bağımsız onaycıları sahip dışlayarak say. Geri alma için `>=`, özet değişmemesi için `==` koşulunu kullan.
```
:::

::: anlat Yayın paketi sürüm ilerlemesini de zorunlu kılar
Aday değişikliğin üretime alınması için yeni sürümün aktif sürümden büyük olması gerekir. Aksi hâlde `surum` nedeni eklenir. Yayın neden sırası `tur`, `surum`, `onay`, `geri_alma`, `ozet` şeklindedir.

Yalnız nedensiz kayıtlar yayın manifestosuna girer. Manifesto içerik özeti ve geri alma hedefini taşır; karantina kayıtları ise kimlikleri ve bütün nedenleriyle denetimde kalır.
:::

::: gorev 3 · Onaylı registry yayın paketi oluştur
`registry_yayin_paketi(kayitlar, politika)` işlevini yaz. Politika ilk görevdeki bütün kuralları sağlasın. Kayıtlar ikinci görevdeki alanlara ek olarak `aktif_surum` taşır ve tam olarak bu dokuz alanı içerir. Aktif sürüm bool olmayan 0 veya pozitif int olmalıdır; diğer bütün biçim kuralları ikinci görevle aynıdır. Geçersiz veride `ValueError` yükselt.

Beş yayın nedenini sırayla uygula. Nedensiz kayıtları `yayin` listesine `{"id":ID,"tur":TUR,"surum":SURUM,"yeni_ozet":OZET,"geri_alma_surumu":GERI}` olarak ekle; diğerlerini `karantina` listesine `{"id":ID,"nedenler":[...]}` olarak yaz.

İki listeyi de kimliğe göre sırala. Boş kayıtta iki boş liste döndür ve girdileri değiştirme.

Görünür veri: `veri/degisiklik_kayitlari.json` içindeki `yayin_kayitlari`. `prompt-v3` yayına girmelidir. `model-v6-tekrar` aktif sürümü tekrar yayınladığı için `surum`, `prompt-ilk` geri dönülecek sürümü olmadığı için `geri_alma` nedenini almalıdır.

```starter
from ai_savunma_veri import json_yukle

def registry_yayin_paketi(kayitlar, politika):
    # KUSURLU BAŞLANGIÇ KODU: sürüm ilerlemesini hiç denetlemiyor, karantina kayıtlarını nedensiz yazıyor ve yayına özet yerine eski özeti koyuyor!
    yayin, karantina = [], []
    for k in kayitlar:
        bagimsiz = [x for x in k["onaycilar"] if x != k["sahip"]]
        sorunlu = (k["tur"] not in politika["izinli_turler"] or len(bagimsiz) < politika["min_onay"]
                   or k["geri_alma_surumu"] >= k["surum"] or k["onceki_ozet"] == k["yeni_ozet"])
        if sorunlu:
            karantina.append({"id": k["id"], "nedenler": []})
        else:
            yayin.append({"id": k["id"], "tur": k["tur"], "surum": k["surum"], "yeni_ozet": k["onceki_ozet"], "geri_alma_surumu": k["geri_alma_surumu"]})
    return {"yayin": sorted(yayin, key=lambda x: x["id"]), "karantina": sorted(karantina, key=lambda x: x["id"])}

politika = json_yukle("veri/registry_politikasi.json")["politika"]
veri = json_yukle("veri/degisiklik_kayitlari.json")
paket = registry_yayin_paketi(veri["yayin_kayitlari"], politika)
for y in paket["yayin"]:
    print("yayın:", y["id"], "sürüm", y["surum"], "özet", y["yeni_ozet"][:12] + "…")
for k in paket["karantina"]:
    print("karantina:", k["id"], k["nedenler"])
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-21")
```

```test
import copy
P = {"izinli_turler": ["model", "prompt"], "min_onay": 2, "geri_alma_zorunlu": True, "ozet_degismeli": True}
K = [
    {"id": "yayin-1", "tur": "model", "surum": 3, "aktif_surum": 2, "sahip": "ayse", "onaycilar": ["mehmet", "deniz"], "onceki_ozet": "a" * 64, "yeni_ozet": "b" * 64, "geri_alma_surumu": 2},
    {"id": "surum-1", "tur": "prompt", "surum": 2, "aktif_surum": 2, "sahip": "ayse", "onaycilar": ["mehmet", "deniz"], "onceki_ozet": "c" * 64, "yeni_ozet": "d" * 64, "geri_alma_surumu": 1},
    {"id": "ret-1", "tur": "guardrail", "surum": 1, "aktif_surum": 1, "sahip": "ayse", "onaycilar": ["ayse"], "onceki_ozet": "e" * 64, "yeni_ozet": "e" * 64, "geri_alma_surumu": 1},
]
BEKLENEN = {
    "yayin": [{"id": "yayin-1", "tur": "model", "surum": 3, "yeni_ozet": "b" * 64, "geri_alma_surumu": 2}],
    "karantina": [{"id": "ret-1", "nedenler": ["tur", "surum", "onay", "geri_alma", "ozet"]}, {"id": "surum-1", "nedenler": ["surum"]}],
}
def sozlesme(fn):
    try:
        konce = copy.deepcopy(K)
        ponce = copy.deepcopy(P)
        if fn(K, P) != BEKLENEN or K != konce or P != ponce or fn(list(reversed(K)), P) != BEKLENEN:
            return False
        if fn([], P) != {"yayin": [], "karantina": []}:
            return False
        if fn([dict(K[0], aktif_surum=0)], P)["yayin"][0]["id"] != "yayin-1":
            return False
        if fn([dict(K[0], id="a" * 64)], P)["yayin"][0]["id"] != "a" * 64:
            return False
        for sinir in (1, 5):
            if fn([], dict(P, min_onay=sinir)) != {"yayin": [], "karantina": []}:
                return False
        for kayitlar, politika in [
            (None, P), ({}, P), ([None], P), (K, None), (K, dict(P, geri_alma_zorunlu=False)),
            (K, dict(P, ozet_degismeli=False)), (K, dict(P, min_onay=0)), (K, dict(P, min_onay=6)),
            ([dict(K[0], ek=1)], P), ([dict(K[0], id="a b")], P), ([dict(K[0], id="a" * 65)], P),
            ([K[0], K[0]], P), ([dict(K[0], tur="dosya")], P), ([dict(K[0], surum=0)], P),
            ([dict(K[0], aktif_surum=-1)], P), ([dict(K[0], aktif_surum=True)], P),
            ([dict(K[0], geri_alma_surumu=0)], P), ([dict(K[0], onaycilar=None)], P),
            ([dict(K[0], onaycilar=["mehmet", "mehmet"])], P), ([dict(K[0], sahip="a" * 65)], P),
            ([dict(K[0], onaycilar=["a" * 65])], P), ([dict(K[0], onceki_ozet="a" * 63)], P), ([dict(K[0], yeni_ozet="A" * 64)], P),
        ]:
            try:
                fn(kayitlar, politika)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(registry_yayin_paketi), "sürüm, onay, geri alma ve yayın ayrımı korunmalı")
def m_surum(kayitlar, politika):
    return registry_yayin_paketi([dict(x, aktif_surum=0) for x in kayitlar], politika)
def m_onay(kayitlar, politika):
    return registry_yayin_paketi([dict(x, onaycilar=["mehmet", "deniz"]) for x in kayitlar], politika)
def m_ozet(kayitlar, politika):
    return registry_yayin_paketi([dict(x, yeni_ozet="f" * 64) for x in kayitlar], politika)
for ad, mutant in [("sürümü düzelten", m_surum), ("onayı düzelten", m_onay), ("özeti değiştiren", m_ozet)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
raises(ValueError,registry_yayin_paketi,[{'id': None, 'tur': 'model', 'surum': 3, 'aktif_surum': 2, 'sahip': 'ayse', 'onaycilar': ['mehmet', 'deniz'], 'onceki_ozet': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'yeni_ozet': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 'geri_alma_surumu': 2}, {'id': 'surum-1', 'tur': 'prompt', 'surum': 2, 'aktif_surum': 2, 'sahip': 'ayse', 'onaycilar': ['mehmet', 'deniz'], 'onceki_ozet': 'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc', 'yeni_ozet': 'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd', 'geri_alma_surumu': 1}, {'id': 'ret-1', 'tur': 'guardrail', 'surum': 1, 'aktif_surum': 1, 'sahip': 'ayse', 'onaycilar': ['ayse'], 'onceki_ozet': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee', 'yeni_ozet': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee', 'geri_alma_surumu': 1}],{'izinli_turler': ['model', 'prompt'], 'min_onay': 2, 'geri_alma_zorunlu': True, 'ozet_degismeli': True},msg="hatalı alan ValueError sözleşmesi: mutant:563:33:Add->Sub")
raises(ValueError,registry_yayin_paketi,[{'id': 'yayin-1', 'tur': 'model', 'surum': None, 'aktif_surum': 2, 'sahip': 'ayse', 'onaycilar': ['mehmet', 'deniz'], 'onceki_ozet': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'yeni_ozet': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 'geri_alma_surumu': 2}, {'id': 'surum-1', 'tur': 'prompt', 'surum': 2, 'aktif_surum': 2, 'sahip': 'ayse', 'onaycilar': ['mehmet', 'deniz'], 'onceki_ozet': 'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc', 'yeni_ozet': 'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd', 'geri_alma_surumu': 1}, {'id': 'ret-1', 'tur': 'guardrail', 'surum': 1, 'aktif_surum': 1, 'sahip': 'ayse', 'onaycilar': ['ayse'], 'onceki_ozet': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee', 'yeni_ozet': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee', 'geri_alma_surumu': 1}],{'izinli_turler': ['model', 'prompt'], 'min_onay': 2, 'geri_alma_zorunlu': True, 'ozet_degismeli': True},msg="hatalı alan ValueError sözleşmesi: mutant:579:33:Add->Sub")
raises(ValueError,registry_yayin_paketi,[{'id': 'yayin-1', 'tur': 'model', 'surum': 3, 'aktif_surum': 2, 'sahip': 'ayse', 'onaycilar': ['mehmet', 'deniz'], 'onceki_ozet': None, 'yeni_ozet': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 'geri_alma_surumu': 2}, {'id': 'surum-1', 'tur': 'prompt', 'surum': 2, 'aktif_surum': 2, 'sahip': 'ayse', 'onaycilar': ['mehmet', 'deniz'], 'onceki_ozet': 'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc', 'yeni_ozet': 'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd', 'geri_alma_surumu': 1}, {'id': 'ret-1', 'tur': 'guardrail', 'surum': 1, 'aktif_surum': 1, 'sahip': 'ayse', 'onaycilar': ['ayse'], 'onceki_ozet': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee', 'yeni_ozet': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee', 'geri_alma_surumu': 1}],{'izinli_turler': ['model', 'prompt'], 'min_onay': 2, 'geri_alma_zorunlu': True, 'ozet_degismeli': True},msg="hatalı alan ValueError sözleşmesi: mutant:616:33:Add->Sub")
# --- carbon-c8-ek-bas ---
raises(ValueError, registry_yayin_paketi, K, dict(P, izinli_turler=[123]), msg="izinli tür str olmalı")
raises(ValueError, registry_yayin_paketi, K, dict(P, min_onay=True), msg="min_onay bool ret")
raises(ValueError, registry_yayin_paketi, [dict(K[0], id=123)], P, msg="id str olmalı")
raises(ValueError, registry_yayin_paketi, [dict(K[0], tur=123)], P, msg="tür str olmalı")
raises(ValueError, registry_yayin_paketi, [dict(K[0], surum=True)], P, msg="sürüm bool ret")
raises(ValueError, registry_yayin_paketi, [dict(K[0], aktif_surum=True)], P, msg="aktif_surum bool ret")
raises(ValueError, registry_yayin_paketi, [dict(K[0], sahip=123)], P, msg="sahip str olmalı")
raises(ValueError, registry_yayin_paketi, [dict(K[0], onaycilar=[123])], P, msg="onaycı str olmalı")
raises(ValueError, registry_yayin_paketi, [dict(K[0], onceki_ozet=123)], P, msg="önceki özet str olmalı")
raises(ValueError, registry_yayin_paketi, [dict(K[0], yeni_ozet=123)], P, msg="yeni özet str olmalı")
raises(ValueError, registry_yayin_paketi, [dict(K[0], geri_alma_surumu=True)], P, msg="geri_alma_surumu bool ret")
raises(ValueError, registry_yayin_paketi, K, dict(P, ek=1), msg="politika fazla alan ret")
raises(ValueError, registry_yayin_paketi, K, dict(P, izinli_turler=tuple(P["izinli_turler"])), msg="izinli_turler tuple olamaz")
raises(ValueError, registry_yayin_paketi, K, dict(P, izinli_turler=[]), msg="boş izinli tür listesi ret")
raises(ValueError, registry_yayin_paketi, K, dict(P, izinli_turler=P["izinli_turler"] + [P["izinli_turler"][0]]), msg="yinelenen izinli tür ret")
# --- carbon-c8-ek-son ---
```

```solution
def registry_yayin_paketi(kayitlar, politika):
    import re
    if not isinstance(politika, dict):
        raise ValueError("politika sözlük olmalı")
    if set(politika) != {"izinli_turler", "min_onay", "geri_alma_zorunlu", "ozet_degismeli"}:
        raise ValueError("politika şeması geçersiz")
    if not isinstance(politika["izinli_turler"], list):
        raise ValueError("türler liste olmalı")
    if not politika["izinli_turler"]:
        raise ValueError("tür listesi boş olamaz")
    if len(set(politika["izinli_turler"])) != len(politika["izinli_turler"]):
        raise ValueError("türler yinelenemez")
    if any(tur not in ("model", "prompt", "guardrail") for tur in politika["izinli_turler"]):
        raise ValueError("tür geçersiz")
    if type(politika["min_onay"]) is not int:
        raise ValueError("onay sınırı int olmalı")
    if politika["min_onay"] < 1:
        raise ValueError("onay sınırı pozitif olmalı")
    if politika["min_onay"] > 5:
        raise ValueError("onay sınırı çok büyük")
    if politika["geri_alma_zorunlu"] is not True:
        raise ValueError("geri alma zorunlu olmalı")
    if politika["ozet_degismeli"] is not True:
        raise ValueError("özet değişimi zorunlu olmalı")
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    kimlikler = set()
    yayin = []
    karantina = []
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"id", "tur", "surum", "aktif_surum", "sahip", "onaycilar", "onceki_ozet", "yeni_ozet", "geri_alma_surumu"}:
            raise ValueError("kayıt şeması geçersiz")
        for alan in ("id", "sahip"):
            if not isinstance(kayit[alan], str):
                raise ValueError(alan + " string olmalı")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit[alan]):
                raise ValueError(alan + " geçersiz")
        if kayit["id"] in kimlikler:
            raise ValueError("kimlik yinelenemez")
        kimlikler.add(kayit["id"])
        if kayit["tur"] not in ("model", "prompt", "guardrail"):
            raise ValueError("tür geçersiz")
        for alan in ("surum", "geri_alma_surumu"):
            if type(kayit[alan]) is not int:
                raise ValueError(alan + " int olmalı")
            if kayit[alan] < 1:
                raise ValueError(alan + " pozitif olmalı")
        if type(kayit["aktif_surum"]) is not int:
            raise ValueError("aktif sürüm int olmalı")
        if kayit["aktif_surum"] < 0:
            raise ValueError("aktif sürüm negatif olamaz")
        onaycilar = kayit["onaycilar"]
        if not isinstance(onaycilar, list):
            raise ValueError("onaycılar liste olmalı")
        if len(set(onaycilar)) != len(onaycilar):
            raise ValueError("onaycılar yinelenemez")
        for onayci in onaycilar:
            if not isinstance(onayci, str):
                raise ValueError("onaycı string olmalı")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", onayci):
                raise ValueError("onaycı geçersiz")
        for alan in ("onceki_ozet", "yeni_ozet"):
            if not isinstance(kayit[alan], str):
                raise ValueError(alan + " string olmalı")
            if not re.fullmatch(r"[0-9a-f]{64}", kayit[alan]):
                raise ValueError(alan + " geçersiz")
        nedenler = []
        if kayit["tur"] not in politika["izinli_turler"]:
            nedenler.append("tur")
        if kayit["surum"] <= kayit["aktif_surum"]:
            nedenler.append("surum")
        bagimsiz = [x for x in onaycilar if x != kayit["sahip"]]
        if len(bagimsiz) < politika["min_onay"]:
            nedenler.append("onay")
        if kayit["geri_alma_surumu"] >= kayit["surum"]:
            nedenler.append("geri_alma")
        if kayit["onceki_ozet"] == kayit["yeni_ozet"]:
            nedenler.append("ozet")
        if nedenler:
            karantina.append({"id": kayit["id"], "nedenler": nedenler})
        else:
            yayin.append({"id": kayit["id"], "tur": kayit["tur"], "surum": kayit["surum"], "yeni_ozet": kayit["yeni_ozet"], "geri_alma_surumu": kayit["geri_alma_surumu"]})
    return {"yayin": sorted(yayin, key=lambda x: x["id"]), "karantina": sorted(karantina, key=lambda x: x["id"])}
```

```hint
Yeni sürüm için `surum <= aktif_surum` ihlalini ekle. Nedensiz kayıtları manifestoya, nedenli kayıtları kimlik sıralı karantinaya ayır.
```
:::

::: anlat Değişiklik kontrolü, gerçek içerik özetiyle anlam kazanır
Görev 1–3'te özetler JSON dosyasında hazır yazılıydı. Bu adımda özetler **gerçek prompt metinlerinden** hesaplanır ve bu promptlar gerçek bir modelde çalıştırılır. `sandbox/ai_gercek_ai_savunma_21.py` deneyi şunları yapar:

1. İki guardrail prompt sürümü vardır. v1 temel kuraldır. v2, "gizli kod, anahtar veya token yazma" kuralını ekleyen sertleştirilmiş sürümdür. Her ikisinin UTF-8 baytlarının SHA-256 özeti hesaplanır. Ayrıca v1'in sonuna **yalnız bir boşluk** eklenmiş üçüncü bir metnin özeti de hesaplanır.
2. Kurulu yerel Ollama modeli aynı belgeyi önce v1, sonra v2 sistem promptuyla özetler (sıcaklık 0, tohum 5). Böylece kayıttaki her özetin arkasında modele gerçekten gönderilmiş bir metin ve onun gerçek yanıtı bulunur. Model boş yanıt verirse deney "tamamlanmadı" diye durur.
3. Üç registry kaydı kurulur ve senin `registry_degisiklikleri_denetle` işlevine verilir:
   - `r-gercek`: v1 → v2 geçişidir. Bağımsız onay yeterli, geri alma hedefi var. Beklenen karar `aday`.
   - `r-sahte`: sürüm artmış ama yeni özet eskisiyle aynı. Beklenen neden `ozet`.
   - `r-bosluk`: yalnız bir boşluk değişmiş. Özet farklı olduğu için kural açısından gerçek bir değişikliktir ve `aday` olur.

Test önce işlevini gizli deterministik kayıtlarla sınar. Ardından gerçek kayıtlardan ürettiğin raporu bağımsız bir referans hesapla birebir karşılaştırır. Modelin yanıtlarının içeriği kabul koşulu değildir; ham yanıtlar ve özetler kanıta yazılır.

`r-bosluk` kaydı dersin asıl uyarısıdır. Özet karşılaştırması bir boşluk farkını da "içerik değişti" diye sayar. Saldırgan, sahte sürüm kuralını atlatmak için içeriğe anlamsız bir karakter ekleyip sürümü artırabilir; özet kontrolü bunu geçirir. Bu yüzden registry kontrolü yalnız kapının ilk adımıdır. Fark (diff) insan tarafından okunur ve davranış değişikliği bir eval paketiyle ölçülür. Ders yazılırken bu makinede `qwen3:4b-instruct-2507` ile yapılan koşuda v1 ve v2 aynı belgeye farklı cümlelerle ama aynı anlamda iki özet verdi. Bu tek örnekten v2'nin daha güvenli olduğu sonucu çıkarılamaz.

:::

::: gorev Gerçek deney · Gerçek içerik özetiyle değişiklik kontrolü
`registry_degisiklikleri_denetle(kayitlar, politika)` işlevini yaz. Kuralları ve çıktısı 2. görevdekiyle **aynıdır**. Deney gerçek prompt sürümlerinin SHA-256 özetlerini hesaplar ve iki sürümü de gerçek modelde çalıştırır. Senin denetçin gerçek değişikliği `aday` bırakmalı, içerik özeti değişmeyen sahte sürümü `ozet` nedeniyle karantinaya almalıdır. `sandbox.ai_gercek_ai_savunma_21` içindeki `registry_degisiklikleri_denetle_referans` yalnız test içindir; onu import etmek veya kaynağını okuyup çalıştırmak Kontrol'de reddedilir.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def registry_degisiklikleri_denetle(kayitlar, politika):
    # KUSURLU BAŞLANGIÇ KODU: sürüm artınca içeriğin değiştiğini varsayıyor (özetleri hiç karşılaştırmıyor) ve sahibi de onay sayıyor!
    sonuc = []
    for k in kayitlar:
        nedenler = []
        if k["tur"] not in politika["izinli_turler"]:
            nedenler.append("tur")
        if len(k["onaycilar"]) < politika["min_onay"]:
            nedenler.append("onay")
        if k["geri_alma_surumu"] >= k["surum"]:
            nedenler.append("geri_alma")
        sonuc.append({"id": k["id"], "karar": "karantina" if nedenler else "aday", "nedenler": nedenler})
    return sorted(sonuc, key=lambda x: x["id"])

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_21 as deney
    deney.goster(registry_degisiklikleri_denetle)
```

```test
import ast
import ai_lab
from sandbox import ai_gercek_ai_savunma_21 as D
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
_yasak = ("registry_degisiklikleri_denetle_referans", "kanit_yaz")
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
if not kontrol(not sorun, "Kendi registry_degisiklikleri_denetle işlevini yaz; laboratuvar/referans kullanımı yasak: " + "; ".join(sorted(set(sorun)))):
    stop()
fn = need("registry_degisiklikleri_denetle")
P = {"izinli_turler": ["model", "prompt"], "min_onay": 2, "geri_alma_zorunlu": True, "ozet_degismeli": True}
K = [
    {"id": "aday-1", "tur": "prompt", "surum": 2, "sahip": "ayse", "onaycilar": ["ayse", "mehmet", "deniz"], "onceki_ozet": "a" * 64, "yeni_ozet": "b" * 64, "geri_alma_surumu": 1},
    {"id": "ozet-1", "tur": "prompt", "surum": 2, "sahip": "ayse", "onaycilar": ["ayse", "mehmet", "deniz"], "onceki_ozet": "c" * 64, "yeni_ozet": "c" * 64, "geri_alma_surumu": 1},
]
BEKLENEN = [
    {"id": "aday-1", "karar": "aday", "nedenler": []},
    {"id": "ozet-1", "karar": "karantina", "nedenler": ["ozet"]},
]
def sozlesme(f):
    try:
        if f(K, P) != BEKLENEN or f([], P) != []:
            return False
        zor = [dict(K[0], id="s-1", onaycilar=["ayse", "mehmet"]), dict(K[0], id="s-2", surum=3, geri_alma_surumu=3),
               dict(K[0], id="s-3", tur="guardrail", onaycilar=[], geri_alma_surumu=5, yeni_ozet="a" * 64)]
        if f(zor, P) != [{"id": "s-1", "karar": "karantina", "nedenler": ["onay"]},
                         {"id": "s-2", "karar": "karantina", "nedenler": ["geri_alma"]},
                         {"id": "s-3", "karar": "karantina", "nedenler": ["tur", "onay", "geri_alma", "ozet"]}]:
            return False
        for bozuk in (None, [None], [dict(K[0], ek=1)], [dict(K[0], onaycilar=["mehmet", "mehmet"])], [dict(K[0], yeni_ozet="A" * 64)],
                      [dict(K[0], surum=True)], [dict(K[0], sahip="ayşe")], [K[0], K[0]], [dict(K[0], geri_alma_surumu=0)]):
            try:
                f(bozuk, P)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(fn), "bağımsız onay, geri alma ve özet kuralları korunmalı")
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
    registry_degisiklikleri_denetle = need('registry_degisiklikleri_denetle')
    def _birim_adim_2():
        import copy
        P = {"izinli_turler": ["model", "prompt"], "min_onay": 2, "geri_alma_zorunlu": True, "ozet_degismeli": True}
        K = [
            {"id": "aday-1", "tur": "model", "surum": 3, "sahip": "ayse", "onaycilar": ["ayse", "mehmet", "deniz"], "onceki_ozet": "a" * 64, "yeni_ozet": "b" * 64, "geri_alma_surumu": 2},
            {"id": "onay-1", "tur": "prompt", "surum": 2, "sahip": "ayse", "onaycilar": ["ayse", "mehmet"], "onceki_ozet": "c" * 64, "yeni_ozet": "d" * 64, "geri_alma_surumu": 1},
            {"id": "ret-1", "tur": "guardrail", "surum": 4, "sahip": "ayse", "onaycilar": ["ayse"], "onceki_ozet": "e" * 64, "yeni_ozet": "e" * 64, "geri_alma_surumu": 4},
        ]
        BEKLENEN = [
            {"id": "aday-1", "karar": "aday", "nedenler": []},
            {"id": "onay-1", "karar": "karantina", "nedenler": ["onay"]},
            {"id": "ret-1", "karar": "karantina", "nedenler": ["tur", "onay", "geri_alma", "ozet"]},
        ]
        def sozlesme(fn):
            try:
                konce = copy.deepcopy(K)
                ponce = copy.deepcopy(P)
                if fn(K, P) != BEKLENEN or K != konce or P != ponce or fn(list(reversed(K)), P) != BEKLENEN or fn([], P) != []:
                    return False
                if fn([dict(K[0], id="a" * 64)], P)[0]["id"] != "a" * 64:
                    return False
                if fn([dict(K[0], onaycilar=["mehmet"])], dict(P, min_onay=1))[0]["karar"] != "aday":
                    return False
                for sinir in (1, 5):
                    if fn([], dict(P, min_onay=sinir)) != []:
                        return False
                for kayitlar, politika in [
                    (None, P), ({}, P), ([None], P), (K, None), (K, dict(P, geri_alma_zorunlu=False)),
                    (K, dict(P, ozet_degismeli=False)), (K, dict(P, izinli_turler=[])),
                    (K, dict(P, min_onay=0)), (K, dict(P, min_onay=6)),
                    ([dict(K[0], ek=1)], P), ([dict(K[0], id="a b")], P), ([dict(K[0], id="a" * 65)], P),
                    ([K[0], K[0]], P), ([dict(K[0], tur="dosya")], P), ([dict(K[0], surum=0)], P),
                    ([dict(K[0], surum=True)], P), ([dict(K[0], geri_alma_surumu=0)], P),
                    ([dict(K[0], sahip="")], P), ([dict(K[0], sahip="a" * 65)], P),
                    ([dict(K[0], onaycilar=None)], P), ([dict(K[0], onaycilar=["mehmet", "mehmet"])], P),
                    ([dict(K[0], onaycilar=["a b"])], P), ([dict(K[0], onaycilar=["a" * 65])], P),
                    ([dict(K[0], onceki_ozet="a" * 63)], P),
                    ([dict(K[0], yeni_ozet="A" * 64)], P),
                ]:
                    try:
                        fn(kayitlar, politika)
                        return False
                    except ValueError:
                        pass
                return True
            except Exception:
                return False
        ok(sozlesme(registry_degisiklikleri_denetle), "bağımsız onay, geri alma ve özet kuralları korunmalı")
        def m_onay(kayitlar, politika):
            return registry_degisiklikleri_denetle([dict(x, onaycilar=["mehmet", "deniz"]) for x in kayitlar], politika)
        def m_geri(kayitlar, politika):
            return registry_degisiklikleri_denetle([dict(x, geri_alma_surumu=1) for x in kayitlar], politika)
        def m_ozet(kayitlar, politika):
            return registry_degisiklikleri_denetle([dict(x, yeni_ozet=x["onceki_ozet"] + "0") for x in kayitlar], politika)
        for ad, mutant in [("onayı düzelten", m_onay), ("geri almayı düzelten", m_geri), ("özeti silen", m_ozet)]:
            ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
        raises(ValueError,registry_degisiklikleri_denetle,[{'id': None, 'tur': 'model', 'surum': 3, 'sahip': 'ayse', 'onaycilar': ['ayse', 'mehmet', 'deniz'], 'onceki_ozet': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'yeni_ozet': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 'geri_alma_surumu': 2}, {'id': 'onay-1', 'tur': 'prompt', 'surum': 2, 'sahip': 'ayse', 'onaycilar': ['ayse', 'mehmet'], 'onceki_ozet': 'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc', 'yeni_ozet': 'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd', 'geri_alma_surumu': 1}, {'id': 'ret-1', 'tur': 'guardrail', 'surum': 4, 'sahip': 'ayse', 'onaycilar': ['ayse'], 'onceki_ozet': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee', 'yeni_ozet': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee', 'geri_alma_surumu': 4}],{'izinli_turler': ['model', 'prompt'], 'min_onay': 2, 'geri_alma_zorunlu': True, 'ozet_degismeli': True},msg="hatalı alan ValueError sözleşmesi: mutant:511:33:Add->Sub")
        raises(ValueError,registry_degisiklikleri_denetle,[{'id': 'aday-1', 'tur': 'model', 'surum': 3, 'sahip': 'ayse', 'onaycilar': ['ayse', 'mehmet', 'deniz'], 'onceki_ozet': None, 'yeni_ozet': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 'geri_alma_surumu': 2}, {'id': 'onay-1', 'tur': 'prompt', 'surum': 2, 'sahip': 'ayse', 'onaycilar': ['ayse', 'mehmet'], 'onceki_ozet': 'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc', 'yeni_ozet': 'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd', 'geri_alma_surumu': 1}, {'id': 'ret-1', 'tur': 'guardrail', 'surum': 4, 'sahip': 'ayse', 'onaycilar': ['ayse'], 'onceki_ozet': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee', 'yeni_ozet': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee', 'geri_alma_surumu': 4}],{'izinli_turler': ['model', 'prompt'], 'min_onay': 2, 'geri_alma_zorunlu': True, 'ozet_degismeli': True},msg="hatalı alan ValueError sözleşmesi: mutant:557:33:Add->Sub")
        raises(ValueError, registry_degisiklikleri_denetle, K, dict(P, izinli_turler=[123]), msg="izinli tür str olmalı")
        raises(ValueError, registry_degisiklikleri_denetle, K, dict(P, min_onay=True), msg="min_onay bool ret")
        raises(ValueError, registry_degisiklikleri_denetle, [dict(K[0], id=123)], P, msg="id str olmalı")
        raises(ValueError, registry_degisiklikleri_denetle, [dict(K[0], tur=123)], P, msg="tür str olmalı")
        raises(ValueError, registry_degisiklikleri_denetle, [dict(K[0], surum=True)], P, msg="sürüm bool ret")
        raises(ValueError, registry_degisiklikleri_denetle, [dict(K[0], sahip=123)], P, msg="sahip str olmalı")
        raises(ValueError, registry_degisiklikleri_denetle, [dict(K[0], onaycilar=[123])], P, msg="onaycı str olmalı")
        raises(ValueError, registry_degisiklikleri_denetle, [dict(K[0], onceki_ozet=123)], P, msg="önceki özet str olmalı")
        raises(ValueError, registry_degisiklikleri_denetle, [dict(K[0], yeni_ozet=123)], P, msg="yeni özet str olmalı")
        raises(ValueError, registry_degisiklikleri_denetle, [dict(K[0], geri_alma_surumu=True)], P, msg="geri_alma_surumu bool ret")
        raises(ValueError, registry_degisiklikleri_denetle, K, dict(P, ek=1), msg="politika fazla alan ret")
        raises(ValueError, registry_degisiklikleri_denetle, K, dict(P, izinli_turler=tuple(P["izinli_turler"])), msg="izinli_turler tuple olamaz")
        raises(ValueError, registry_degisiklikleri_denetle, K, dict(P, izinli_turler=P["izinli_turler"] + [P["izinli_turler"][0]]), msg="yinelenen izinli tür ret")
    try:
        _birim_adim_2()
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
    kontrol(r["gercek_karar"] == "aday", "gerçek içerik değişimi (farklı hash) aday bırakıldı")
    kontrol(r["sahte_karar"] == "karantina" and "ozet" in (r["sahte_nedenler"] or []),
            "içerik-hash'i değişmeyen sahte sürüm bumpı ozet nedeniyle karantinaya alındı")
    bagimsiz = D.registry_degisiklikleri_denetle_referans([dict(k, onaycilar=list(k["onaycilar"])) for k in r["kayitlar"]], dict(D.POLITIKA))
    kontrol(r["rapor"] == bagimsiz, f"gerçek kayıtlardaki rapor bağımsız hesapla aynı olmalı: senin {r['rapor']} · beklenen {bagimsiz}")
    oz = D.ozet(r)
yol = ai_lab.kanit_yaz("savunma-registry", {"kaynak": "gercek", "kabul": all(sonuclar), "ders": "ai-savunma-21",
                                            "ortam": (r or {}).get("ortam"), "ozet": oz,
                                            "kayitlar": (r or {}).get("kayitlar"), "yanitlar": D.ham_yanitlar(r) if r else None})
if oz:
    ok(True, f"BULGU ({r['ortam']['model']['ad']}): gerçek prompt özetleri v1={oz['sha_v1_onek']} v2={oz['sha_v2_onek']}; "
             f"gerçek değişim → {oz['gercek_karar']}; içerik değişmeyen sahte sürüm → {oz['sahte_karar']} {oz['sahte_nedenler']}; "
             f"yalnız boşluk değişen sürüm → {oz['bosluk_karar']} (özet baytı ölçer, anlamı değil). Ham v1/v2 yanıtları kanıtta.")
```

```solution
import ai_lab

def registry_degisiklikleri_denetle(kayitlar, politika):
    import re
    if not isinstance(politika, dict):
        raise ValueError("politika sözlük olmalı")
    if set(politika) != {"izinli_turler", "min_onay", "geri_alma_zorunlu", "ozet_degismeli"}:
        raise ValueError("politika şeması geçersiz")
    if not isinstance(politika["izinli_turler"], list):
        raise ValueError("türler liste olmalı")
    if not politika["izinli_turler"]:
        raise ValueError("tür listesi boş olamaz")
    if len(set(politika["izinli_turler"])) != len(politika["izinli_turler"]):
        raise ValueError("türler yinelenemez")
    if any(tur not in ("model", "prompt", "guardrail") for tur in politika["izinli_turler"]):
        raise ValueError("tür geçersiz")
    if type(politika["min_onay"]) is not int:
        raise ValueError("onay sınırı int olmalı")
    if politika["min_onay"] < 1:
        raise ValueError("onay sınırı pozitif olmalı")
    if politika["min_onay"] > 5:
        raise ValueError("onay sınırı çok büyük")
    if politika["geri_alma_zorunlu"] is not True:
        raise ValueError("geri alma zorunlu olmalı")
    if politika["ozet_degismeli"] is not True:
        raise ValueError("özet değişimi zorunlu olmalı")
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    kimlikler = set()
    sonuc = []
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"id", "tur", "surum", "sahip", "onaycilar", "onceki_ozet", "yeni_ozet", "geri_alma_surumu"}:
            raise ValueError("kayıt şeması geçersiz")
        for alan in ("id", "sahip"):
            if not isinstance(kayit[alan], str):
                raise ValueError(alan + " string olmalı")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit[alan]):
                raise ValueError(alan + " geçersiz")
        if kayit["id"] in kimlikler:
            raise ValueError("kimlik yinelenemez")
        kimlikler.add(kayit["id"])
        if kayit["tur"] not in ("model", "prompt", "guardrail"):
            raise ValueError("tür geçersiz")
        for alan in ("surum", "geri_alma_surumu"):
            if type(kayit[alan]) is not int:
                raise ValueError(alan + " int olmalı")
            if kayit[alan] < 1:
                raise ValueError(alan + " pozitif olmalı")
        onaycilar = kayit["onaycilar"]
        if not isinstance(onaycilar, list):
            raise ValueError("onaycılar liste olmalı")
        if len(set(onaycilar)) != len(onaycilar):
            raise ValueError("onaycılar yinelenemez")
        for onayci in onaycilar:
            if not isinstance(onayci, str):
                raise ValueError("onaycı string olmalı")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", onayci):
                raise ValueError("onaycı geçersiz")
        for alan in ("onceki_ozet", "yeni_ozet"):
            if not isinstance(kayit[alan], str):
                raise ValueError(alan + " string olmalı")
            if not re.fullmatch(r"[0-9a-f]{64}", kayit[alan]):
                raise ValueError(alan + " geçersiz")
        nedenler = []
        if kayit["tur"] not in politika["izinli_turler"]:
            nedenler.append("tur")
        bagimsiz = [x for x in onaycilar if x != kayit["sahip"]]
        if len(bagimsiz) < politika["min_onay"]:
            nedenler.append("onay")
        if kayit["geri_alma_surumu"] >= kayit["surum"]:
            nedenler.append("geri_alma")
        if kayit["onceki_ozet"] == kayit["yeni_ozet"]:
            nedenler.append("ozet")
        sonuc.append({"id": kayit["id"], "karar": "karantina" if nedenler else "aday", "nedenler": nedenler})
    return sorted(sonuc, key=lambda x: x["id"])

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_21 as deney
    deney.goster(registry_degisiklikleri_denetle)
```

```hint
Bu işlev 2. görevdeki `registry_degisiklikleri_denetle` ile birebir aynıdır; tek fark, özetlerin gerçek prompt metinlerinden hesaplanması ve bu promptların gerçek modelde çalıştırılmasıdır. Bağımsız onaycıları sahip dışlayarak say; özet değişmemesini `==` ile yakala.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Registry değişikliğinde içerik ve onay bağlanır

Bir değişiklik kaydı hangi bileşenin hangi sürümden hangisine geçtiğini ve kimin kabul ettiğini bağlamalıdır. Sadece onaylayan adı yetmez; onayın incelenen içerik özetiyle ilişkisi korunmalıdır. Yayın paketi yalnız kabul edilen değişiklikleri içerir. Labın yerel değişiklik günlüğü uzaktaki registrynin tüm kimlik ve rol yönetimini temsil etmez.

| Yaygın yanlış | Mekanizmanın sınırı |
|---|---|
| Onay metni tüm sonraki içerikleri kapsar | Onay belirli değişiklik ve sürüm kimliğine bağlıdır. |

Saldırı–savunma bağlantısı: ai-saldiri-47.
:::

::: anlat Kaynak ile lab sonucunu ayır
[Python hashlib](https://docs.python.org/3/library/hashlib.html). Özet onayın belirli içeriğe bağlanmasını sağlar; onaylayan kimliğinin doğrulanması ayrı katmandır.
:::
