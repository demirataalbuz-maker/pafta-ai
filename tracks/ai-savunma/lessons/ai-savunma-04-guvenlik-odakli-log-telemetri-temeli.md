---
id: ai-savunma-04
title: Güvenlik Odaklı Log ve Telemetri Temeli
summary: Hassas içeriği dışlayan olay şeması kur, trace zincirlerini ilişkilendir ve sayısal telemetri özeti üret.
timeout: 45
esleme: ai-saldiri-06, ai-saldiri-38
---

::: anlat İzlenebilirlik ham içeriği kaydetmek değildir

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Model çağrısı gerçek süre ve çıktı token sayısı üretir | İlk üç görev görünür sentetik JSON; final kurulu Ollama modeline üç gerçek istek | Sentetik olaylar servis kaydı değildir; token_in finalde ölçülmez |
| Güvenli telemetri ölçüm ve ilişkileri içerikten ayırır | Alan izin listesi, trace doğrulama, sayısal rapor ve gerçek olayların şema kontrolü | OpenTelemetry SDK, OTLP dışa aktarımı veya SigNoz servisi çalıştırıldığı anlamına gelmez |

> [!NOT]
> `veri/telemetri.json` elle hazırlanmış sentetik örnektir. İlk üç görev aynı dosyayı okur; ilk Çalıştır ham dosyayı gösterir. Setup her çalıştırmada yeni geçici veri/ kopyası kurar; değişiklikler sonraki çalıştırmaya taşınmaz. Kaynak dosyayı haricî editörde veya yüklenen sözlüğü kodda değiştirip Çalıştır deneyebilirsin. Gizli testler ayrıdır. Final gerçek yerel model çağırır. Laboratuvarın yalnız zararsız sentetik istem/yanıtları içeren deney kaydı güvenli telemetri akışından ayrıdır; gerçek kullanıcı içeriğini toplama izni değildir.

Bir AI isteğini izlemek için trace kimliği, olay kimliği, parent ilişkisi, olay türü, zaman ve süre yeterlidir. Prompt, model yanıtı, API anahtarı, Authorization başlığı veya kullanıcı e-postası güvenlik telemetrisine eklenmemelidir. Model adı, HTTP kodu, guardrail kararı ve token sayıları gibi dar alanlar ise ölçüm için kullanılabilir.

Bu derste alan izin listesi fail-closed çalışır: bilinmeyen alan sessizce loglanmaz, olay geçersiz sayılır. Böylece `prompt` veya `yanit` gibi yeni bir alanın şemaya yanlışlıkla eklenmesi engellenir. İlk üç görev OpenTelemetry ve SigNoz kavramlarını standart Python verileriyle temsil eder; final gerçek yerel modeli çağırır. OpenTelemetry SDK/OTLP veya SigNoz servisi bu derste çalıştırılmaz.
:::

::: tahmin İzin listesi bilinmeyen alanı görünür kılar
Üç çıktı satırını yaz:

```python
alanlar = {"model": "yerel", "prompt": "gizli"}
print("prompt" in alanlar)
print(sorted(alanlar))
print(len(alanlar) - 1)
```

???

```cikti
True
['model', 'prompt']
1
```

İzin verilen alan sayısını çıkarmak yerine bilinmeyen alanı reddetmek, ham içeriğin loglanmasını önler.
:::

::: gorev 1 · Hassas içeriği dışlayan telemetri olayını doğrula
`guvenli_telemetri_olayi(olay)` işlevini yaz. Olay tam olarak `iz_id`, `olay_id`, `parent_id`, `tur`, `zaman_ms`, `sure_ms`, `alanlar` alanlarını taşısın. İz ve olay kimlikleri baş/son boşluğu olmayan boş olmayan stringlerdir. Parent None veya aynı kurallara uyan ve olay kimliğinden farklı bir stringdir. Tür yalnız `http`, `model`, `guardrail`, `arac`; zaman ve süre bool olmayan, sonlu ve sıfır/pozitif sayılardır.

`alanlar` sözlüğü yalnız şu alanları içerebilir:

- her tür: `durum` (`ok` veya `hata`), `hata_kodu` (boş olmayan string)
- `http`: `http_kod` (bool olmayan 100–599 int), `yontem` (boş olmayan string)
- `model`: `model` (boş olmayan string), `token_in`, `token_out` (bool olmayan sıfır/pozitif int)
- `guardrail`: `karar` (`izin`, `reddet` veya `hata`)
- `arac`: `arac` (boş olmayan string)

Metin alanlarının baş/son boşluğu olamaz. Bilinmeyen alan veya geçersiz veride `ValueError` yükselt. Olayı ve alanlar sözlüğünü kopyalayarak döndür, girdiyi değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-04")
```

```starter
from ai_savunma_veri import json_yukle,metin_yukle

def guvenli_telemetri_olayi(olay):
    # KUSURLU BAŞLANGIÇ KODU: iç alanları paylaşır ve bilinmeyen alanları kabul eder.
    return dict(olay)

v=json_yukle("veri/telemetri.json")
print("Sentetik ham dosya:\n",metin_yukle("veri/telemetri.json"))
print("Model olayı:",guvenli_telemetri_olayi(v["olaylar"][v["model_indeksi"]]))
```

```test
import copy
O = {"iz_id": "iz-1", "olay_id": "model-1", "parent_id": "http-1", "tur": "model", "zaman_ms": 10, "sure_ms": 2.5, "alanlar": {"token_out": 3, "model": "yerel", "token_in": 5, "durum": "ok"}}
def sozlesme(fn):
    try:
        once = copy.deepcopy(O)
        if fn(O) != O or O != once or fn(O) is O or fn(O)["alanlar"] is O["alanlar"]:
            return False
        sifir = dict(O, zaman_ms=0, sure_ms=0, parent_id=None, alanlar={"token_in": 0, "token_out": 0})
        if fn(sifir)["sure_ms"] != 0:
            return False
        for olay in [
            None, [], dict(O, ek=1), dict(O, iz_id=""), dict(O, iz_id=" x"),
            dict(O, olay_id=None), dict(O, parent_id="model-1"), dict(O, parent_id=1),
            dict(O, parent_id=""), dict(O, parent_id=" x"),
            dict(O, tur="diger"), dict(O, zaman_ms=True), dict(O, sure_ms=-1),
            dict(O, zaman_ms=float("nan")), dict(O, sure_ms=float("inf")),
            dict(O, alanlar=None), dict(O, alanlar={"prompt": "gizli"}),
            dict(O, alanlar={"yanit": "gizli"}), dict(O, alanlar={"api_key": "x"}),
            dict(O, alanlar={"http_kod": 200}), dict(O, alanlar={"token_in": True}),
            dict(O, alanlar={"token_out": -1}), dict(O, alanlar={"model": " x"}),
            dict(O, alanlar={"durum": "bitti"}), dict(O, alanlar={"hata_kodu": ""}),
            dict(O, tur="http", alanlar={"http_kod": 99}),
            dict(O, tur="http", alanlar={"http_kod": 600}),
            dict(O, tur="http", alanlar={"http_kod": True}),
            dict(O, tur="guardrail", alanlar={"karar": "belirsiz"}),
        ]:
            try:
                fn(olay)
                return False
            except ValueError:
                pass
        for kod in (100, 599):
            if fn(dict(O, tur="http", alanlar={"http_kod": kod}))["alanlar"]["http_kod"] != kod:
                return False
        # Aynı olay sözleşmesi tüm bağımsız görevlerde korunur.
        temel={"iz_id":"t","olay_id":"e","parent_id":None,"tur":"model","zaman_ms":0,"sure_ms":0,"alanlar":{}}
        boz=[dict(temel,parent_id=True),dict(temel,parent_id=" e"),dict(temel,parent_id="e"),dict(temel,zaman_ms=-1)]
        for tur,alan in [("model","model"),("http","yontem"),("arac","arac"),("model","hata_kodu")]:
            for val in [None,True,""," x","x "]:
                boz.append(dict(temel,tur=tur,alanlar={alan:val}))
        for tur,alan,val in [("http","http_kod",True),("model","token_out",True),("model","token_in",-1),("guardrail","karar","x"),("model","durum","x"),("model","Authorization","sentetik"),("model","eposta","demo@example.invalid")]:
            boz.append(dict(temel,tur=tur,alanlar={alan:val}))
        for olay in boz:
            try:
                fn(olay)
                return False
            except ValueError:pass
        for tur,alan,val in [("arac","arac","yerel"),("http","yontem","POST"),("model","hata_kodu","E"),("guardrail","karar","izin"),("guardrail","karar","hata")]:
            olay=dict(temel,tur=tur,alanlar={alan:val})
            fn(olay)
        return True
    except Exception:
        return False
ok(sozlesme(guvenli_telemetri_olayi), "izin listesi, sayı sınırları ve kopyalama korunmalı")
def m_prompt(olay):
    sonuc = guvenli_telemetri_olayi(olay)
    sonuc["alanlar"]["prompt"] = "gizli"
    return sonuc
def m_sure(olay):
    sonuc = guvenli_telemetri_olayi(olay)
    sonuc["sure_ms"] += 1
    return sonuc
def m_token(olay):
    sonuc = guvenli_telemetri_olayi(olay)
    sonuc["alanlar"].pop("token_in", None)
    return sonuc
for ad, mutant in [("ham prompt ekleyen", m_prompt), ("süreyi değiştiren", m_sure), ("token kanıtını silen", m_token)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
# --- carbon-c8-ek-bas ---
raises(ValueError, guvenli_telemetri_olayi, dict(O, iz_id=123), msg="iz_id str olmalı")
raises(ValueError, guvenli_telemetri_olayi, dict(O, olay_id=123), msg="olay_id str olmalı")
raises(ValueError, guvenli_telemetri_olayi, dict(O, parent_id=123), msg="parent_id str veya None olmalı")
raises(ValueError, guvenli_telemetri_olayi, dict(O, alanlar={"model": 123}), msg="model alanı str olmalı")
raises(ValueError, guvenli_telemetri_olayi, dict(O, sure_ms="1.0"), msg="sure_ms str olamaz")
raises(ValueError, guvenli_telemetri_olayi, dict(O, tur="http", alanlar={"http_kod": 200.0}), msg="http_kod float olamaz")
# --- carbon-c8-ek-son ---
```

```solution
from ai_savunma_veri import json_yukle,metin_yukle

def guvenli_telemetri_olayi(olay):
    import math
    zorunlu = {"iz_id", "olay_id", "parent_id", "tur", "zaman_ms", "sure_ms", "alanlar"}
    if not isinstance(olay, dict):
        raise ValueError("olay geçersiz")
    if set(olay) != zorunlu:
        raise ValueError("olay şeması geçersiz")
    for alan in ("iz_id", "olay_id"):
        deger = olay[alan]
        if not isinstance(deger, str):
            raise ValueError("kimlik geçersiz")
        if not deger or deger != deger.strip():
            raise ValueError("kimlik geçersiz")
    parent = olay["parent_id"]
    if parent is not None:
        if not isinstance(parent, str):
            raise ValueError("parent geçersiz")
        if not parent or parent != parent.strip():
            raise ValueError("parent geçersiz")
        if parent == olay["olay_id"]:
            raise ValueError("olay kendi parentı olamaz")
    tur = olay["tur"]
    if tur not in ("http", "model", "guardrail", "arac"):
        raise ValueError("olay türü geçersiz")
    for alan in ("zaman_ms", "sure_ms"):
        deger = olay[alan]
        if isinstance(deger, bool) or not isinstance(deger, (int, float)):
            raise ValueError("süre geçersiz")
        if not math.isfinite(deger):
            raise ValueError("süre sonlu olmalı")
        if deger < 0:
            raise ValueError("süre negatif olamaz")
    alanlar = olay["alanlar"]
    if not isinstance(alanlar, dict):
        raise ValueError("alanlar geçersiz")
    izinli = {"durum", "hata_kodu"} | {
        "http": {"http_kod", "yontem"}, "model": {"model", "token_in", "token_out"},
        "guardrail": {"karar"}, "arac": {"arac"},
    }[tur]
    if any(alan not in izinli for alan in alanlar):
        raise ValueError("bilinmeyen veya hassas alan")
    for alan in ("hata_kodu", "yontem", "model", "arac"):
        if alan in alanlar:
            deger = alanlar[alan]
            if not isinstance(deger, str) or not deger or deger != deger.strip():
                raise ValueError("metin alanı geçersiz")
    if "durum" in alanlar and alanlar["durum"] not in ("ok", "hata"):
        raise ValueError("durum geçersiz")
    if "karar" in alanlar and alanlar["karar"] not in ("izin", "reddet", "hata"):
        raise ValueError("karar geçersiz")
    if "http_kod" in alanlar:
        kod = alanlar["http_kod"]
        if type(kod) is not int or kod < 100 or kod > 599:
            raise ValueError("HTTP kodu geçersiz")
    for alan in ("token_in", "token_out"):
        if alan in alanlar:
            deger = alanlar[alan]
            if type(deger) is not int or deger < 0:
                raise ValueError("token sayısı geçersiz")
    sonuc = dict(olay)
    sonuc["alanlar"] = {alan: alanlar[alan] for alan in sorted(alanlar)}
    return sonuc

v=json_yukle("veri/telemetri.json")
print("Sentetik ham dosya:\n",metin_yukle("veri/telemetri.json"))
print("Model olayı:",guvenli_telemetri_olayi(v["olaylar"][v["model_indeksi"]]))
```

```hint
Önce olayın tam alan kümesini doğrula. Sonra türe özel izin kümesi çıkar; izin dışındaki her anahtarı reddet ve sonuçta yeni bir alan sözlüğü oluştur.
```
:::

::: anlat Trace ilişkisi olayları tek istekte birleştirir

Önce telemetri.json dosyasındaki olaylar dizisini incele. Olay kimlikleri ve süreler elle seçilmiştir; bunları canlı sunucunun ölçümleri sanma. İlk görev model türündeki tek olayı doğrular, ikinci görev aynı diziden iz zincirleri çıkarır, üçüncü görev aynı olayların sayısal özetini hesaplar. Böylece sadece fonksiyon tarifine değil ham kayıt biçimine de bakarsın. veri sözlüğündeki bir süreyi veya parent kimliğini kod içinde değiştirip Çalıştır ile etkisini gözle. Geçici dosyanın her çalıştırmada yeniden kurulduğunu unutma; değişikliklerini korumak istiyorsan ders koduna veya haricî kaynak kopyana yaz.

İzin listesi yalnız alan adlarını sınırlar. model veya hata_kodu gibi izin verilen bir string alanına gizli bilgi yazılması hâlâ sızıntıdır. Bu ders boşluk ve tür sözleşmesini doğrular; izinli stringlerin anlamını okuyup tüm kişisel veriyi bulduğu iddia edilmez. Üretimde bu alanları kullanıcıdan gelen serbest metinle doldurmak yerine denetlenen değer kümeleriyle üretmek gerekir. Authorization veya prompt adındaki alanları sessizce atmak, veri üreticisindeki hatayı gizler; bu görev açık ValueError ister. İzin listesini geliştirirken her olay türünün ayrı alan kümesini koru. Örneğin model olayına http_kod koymak da yanlış şemadır.

Kimlik ve parent ilişkileri yalnız biçim bilgisi değildir. Aynı olay kimliği farklı trace'lerde kullanılabilir, aynı trace içinde iki kez kullanılamaz. Birinci ve üçüncü görev parent'ın biçimini ve olayın kendisine işaret etmemesini denetler. Parent'ın gerçekten aynı trace içinde bulunması, zaman sırası ve döngü kontrolü ikinci görevin ek sorumluluğudur. Böylece yalnız sayısal metrik üreten işlevle bütün iz grafiğini doğrulayan işlevin kapsamı karışmaz. Parent ve çocuk aynı anda başlayabilir; eşit zaman tek başına hata değildir. Eşit zamanda olay kimliğiyle sıralamak sonucu deterministik kılar, nedenselliğin tek kaynağı bu sıralama değildir.

İz süresi olay sürelerinin toplamından farklıdır. Paralel model ve araç işleri üst üste binebilir. Bu ders en erken başlangıç ile en geç bitiş arasındaki aralığı alır. Trace içindeki bir child kökten sonra bitebilir; dersin sözleşmesi çocuğun başlangıcını parent başlangıcından önce yasaklar, parent bitişi içinde kalmasını ayrıca istemez. Bir kayıt üreticisinin saatleri birbirinden kayıksa bu basit karşılaştırma yanlış alarm verebilir. Dağıtık saat eşleme veya eksik span onarımı bu küçük laboratuvarın kabulü değildir. Olayları sadece liste sırasına göre zincirlemek veya bütün parentları None yapmak gerçek ilişkiyi kaybettirir.

Üçüncü görevde hata sayısı ile guardrail reddi ayrı tutulur. Aynı olay hem durum=hata hem hata_kodu taşıyorsa tek hatadır. Guardrail'in reddet kararı teknik hata olmadan da gelebilir. İki sayacı eşitlemek savunmanın normal retlerini arıza gibi gösterebilir. Token alanı yoksa sıfır kabul edilir; bu, token tüketiminin gerçekten sıfır ölçüldüğü anlamına gelmez. Son gerçek deney yalnız çıktı token sayısını Ollama'nın eval_count alanından alır; giriş tokenını ölçmediği için rapordaki token_in sıfırının bu sınırı açıklanır. Üç ondalık süre ortalaması gösterim içindir; ham süreler kanıtta korunur.

Finalde yerel modele üç zararsız istem gönderilir. Cevabın belli bir kelime olması şart değildir; isteklerin gerçekten tamamlanması, model sürelerinin sonlu olması ve token sayısının gerçek yanıttan gelmesi denetlenir. Olay başlangıçları artık uydurulmuş aralıklar yerine monotonic saatten ölçülür. Olaylara ham istem ve yanıt eklenmez. Ayrı laboratuvar kanıtında yalnız bu açık, sentetik istemlerin ayarları ve gerçek çıktıları saklanır; öğrenci böylece ölçümün kaynağını inceleyebilir. Bu araştırma kaydı telemetriye gönderilen veri değildir ve kullanıcının özel konuşmalarının kaydedildiği anlamına gelmez.

Bir saldırgan aşırı uzun veya hassas alanlarla log hattını kirletmeyi, farklı trace parentlarıyla ilişkiyi bozmayı veya hataları normalmiş gibi göstermeyi deneyebilir. Buradaki şema ve grafik kontrolleri bazı biçim hatalarını yakalar; bütün sahtecilik, içerik sızıntısı veya kullanılabilirlik saldırıları için yeterli değildir. Kimlik doğrulama, erişim sınırı ve kayıtların saklama süresi ayrıca tasarlanmalıdır. Prompt dizgisinin olayda bulunmadığını aramak tek başına mahremiyet kanıtı olmaz: farklı bir sır da sızabilir. Bu yüzden final olayları da alan sözleşmesiyle tek tek denetlenir ve bu ölçümün kapsamı açık tutulur.

Çalıştır keşif kaydını kabulfalse üretir. Kontrol bütün koşullar sağlanınca kabul verir. Eksik model, başarısız çağrı veya tamamlanmamış üç istek PASS sayılmaz. Deney kendi açtığı sunucuyu kapatır; kullanıcının çalışan Ollama sunucusunu, önceden yüklü modelini, WSL veya Docker'ı kapatmaz. Yeni paket veya model indirilmez. Modelin adı, digest bilgisi, sürümler, ayarlar, cihaz, gerçek olaylar ve temizlik sonucu kanıtta saklanır. Bu ders yerel ölçüm hattını sınar; dış telemetri altyapısının kurulduğu veya denetlendiği iddia edilmez.

Her olay aynı trace içinde benzersiz bir olay kimliği taşır. Parent kimliği None ise olay köktür; aksi hâlde parent aynı trace içinde bulunmalı ve başlangıç zamanı çocuğun başlangıcından sonra olmamalıdır. Başka trace'e parent vermek veya döngü oluşturmak korelasyonu bozar.

Trace süresi olay sürelerinin toplamı değildir; paralel işlerde süreler çakışabilir. Bu ders `maksimum(zaman + süre) - minimum(zaman)` hesabını kullanır. Olaylar başlangıç zamanı ve kimlikle sıralanır.
:::

::: gorev 2 · Olayları doğrulanmış trace zincirlerine dönüştür
`iz_zinciri_raporu(olaylar)` işlevini yaz. Her olay ilk görevin kurallarını sağlasın. İlk görevin tam doğrulayıcısını bu bağımsız kod alanına da alabilirsin. `(iz_id, olay_id)` çifti benzersiz, parent aynı trace içinde kayıtlı ve parent başlangıcı çocuk başlangıcından büyük olmamalıdır. Parent zinciri döngü içeremez. Geçersiz veride `ValueError` yükselt.

Her trace için:

```text
{"iz_id":ID,"kokler":[OLAY_ID,...],"olaylar":[OLAY_ID,...],
 "baslangic_ms":B,"bitis_ms":T,"sure_ms":T-B}
```

Trace'leri iz kimliğine, kökleri ve olayları `(zaman_ms, olay_id)` sırasına göre sırala. Boş girdi için boş liste döndür ve girdiyi değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-04")
```

```starter
from ai_savunma_veri import json_yukle,metin_yukle

def iz_zinciri_raporu(olaylar):
    # KUSURLU BAŞLANGIÇ KODU: paralel süreleri toplar, parent grafiğini doğrulamaz.
    gruplar={}
    for o in olaylar:gruplar.setdefault(o["iz_id"],[]).append(o)
    sonuc=[]
    for k,vs in sorted(gruplar.items()):
        vs=sorted(vs,key=lambda x:(x["zaman_ms"],x["olay_id"]))
        b=min(o["zaman_ms"] for o in vs);t=max(o["zaman_ms"]+o["sure_ms"] for o in vs)
        sonuc.append({"iz_id":k,"kokler":[o["olay_id"] for o in vs if o["parent_id"] is None],"olaylar":[o["olay_id"] for o in vs],"baslangic_ms":b,"bitis_ms":t,"sure_ms":sum(o["sure_ms"] for o in vs)})
    return sonuc

v=json_yukle("veri/telemetri.json")
print("Sentetik iz zincirleri:",iz_zinciri_raporu(v["olaylar"]))
```

```test
import copy
O = [
    {"iz_id": "iz-b", "olay_id": "kok", "parent_id": None, "tur": "http", "zaman_ms": 20, "sure_ms": 8, "alanlar": {}},
    {"iz_id": "iz-a", "olay_id": "model", "parent_id": "http", "tur": "model", "zaman_ms": 3, "sure_ms": 5, "alanlar": {}},
    {"iz_id": "iz-a", "olay_id": "http", "parent_id": None, "tur": "http", "zaman_ms": 0, "sure_ms": 12, "alanlar": {}},
    {"iz_id": "iz-a", "olay_id": "arac", "parent_id": "model", "tur": "arac", "zaman_ms": 9, "sure_ms": 4, "alanlar": {}},
]
BEKLENEN = [
    {"iz_id": "iz-a", "kokler": ["http"], "olaylar": ["http", "model", "arac"], "baslangic_ms": 0, "bitis_ms": 13, "sure_ms": 13},
    {"iz_id": "iz-b", "kokler": ["kok"], "olaylar": ["kok"], "baslangic_ms": 20, "bitis_ms": 28, "sure_ms": 8},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(O)
        if fn(O) != BEKLENEN or O != once or fn(list(reversed(O))) != BEKLENEN or fn([]) != []:
            return False
        es_zamanli = [O[0], dict(O[0], olay_id="cocuk", parent_id="kok", tur="model")]
        if fn(es_zamanli)[0]["olaylar"] != ["cocuk", "kok"]:
            return False
        for olaylar in [
            None, {}, [None], O + [O[0]],
            [dict(O[0], parent_id="yok")],
            [dict(O[1], parent_id="kok")],
            [dict(O[1], zaman_ms=-1)], [dict(O[1], sure_ms=float("nan"))],
            [dict(O[1], zaman_ms=True)], [dict(O[1], sure_ms="x")],
            [dict(O[0], iz_id="")], [dict(O[0], iz_id=" x")], [dict(O[0], olay_id=None)],
            [dict(O[1], alanlar={"prompt": "x"})],
            [dict(O[0], parent_id="kok", olay_id="x")],
            [dict(O[1], parent_id="arac"), dict(O[2], zaman_ms=20)],
            [dict(O[1], parent_id="arac"), dict(O[3], parent_id="model")],
        ]:
            try:
                fn(olaylar)
                return False
            except ValueError:
                pass
        # Aynı olay sözleşmesi tüm bağımsız görevlerde korunur.
        temel={"iz_id":"t","olay_id":"e","parent_id":None,"tur":"model","zaman_ms":0,"sure_ms":0,"alanlar":{}}
        boz=[dict(temel,parent_id=True),dict(temel,parent_id=" e"),dict(temel,parent_id="e"),dict(temel,zaman_ms=-1)]
        for tur,alan in [("model","model"),("http","yontem"),("arac","arac"),("model","hata_kodu")]:
            for val in [None,True,""," x","x "]:
                boz.append(dict(temel,tur=tur,alanlar={alan:val}))
        for tur,alan,val in [("http","http_kod",True),("model","token_out",True),("model","token_in",-1),("guardrail","karar","x"),("model","durum","x"),("model","Authorization","sentetik"),("model","eposta","demo@example.invalid")]:
            boz.append(dict(temel,tur=tur,alanlar={alan:val}))
        for olay in boz:
            try:
                fn([olay])
                return False
            except ValueError:pass
        for tur,alan,val in [("arac","arac","yerel"),("http","yontem","POST"),("model","hata_kodu","E"),("guardrail","karar","izin"),("guardrail","karar","hata")]:
            olay=dict(temel,tur=tur,alanlar={alan:val})
            fn([olay])
        for kod in [100,599]:
            if fn([dict(temel,tur="http",alanlar={"http_kod":kod})])[0]["sure_ms"]!=0:return False
        fn([dict(temel,alanlar={"token_in":0,"token_out":0})])
        for kod in [99,600]:
            try:fn([dict(temel,tur="http",alanlar={"http_kod":kod})]);return False
            except ValueError:pass
        return True
    except Exception:
        return False
ok(sozlesme(iz_zinciri_raporu), "parent kapsamı, döngü, zaman sınırı ve trace süresi korunmalı")
def m_parent(olaylar):
    degisen = [dict(x, parent_id=None) for x in olaylar]
    return iz_zinciri_raporu(degisen)
def m_sure(olaylar):
    sonuc = iz_zinciri_raporu(olaylar)
    for x in sonuc:
        x["sure_ms"] = sum(o["sure_ms"] for o in olaylar if o["iz_id"] == x["iz_id"])
    return sonuc
def m_sira(olaylar):
    sonuc = iz_zinciri_raporu(olaylar)
    for x in sonuc:
        x["olaylar"].sort(reverse=True)
    return sonuc
for ad, mutant in [("parent ilişkisini silen", m_parent), ("süreleri toplayan", m_sure), ("olay sırasını bozan", m_sira)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
# --- carbon-c8-ek-bas ---
_kok04 = dict(O[0], parent_id=None, zaman_ms=10, sure_ms=1)
raises(ValueError, iz_zinciri_raporu, [dict(_kok04, iz_id=123)], msg="iz_id str olmalı")
raises(ValueError, iz_zinciri_raporu, [dict(_kok04, olay_id=123)], msg="olay_id str olmalı")
raises(ValueError, iz_zinciri_raporu, [dict(_kok04, parent_id=123)], msg="parent_id str/None olmalı")
raises(ValueError, iz_zinciri_raporu, [dict(_kok04, alanlar={"model": 123})], msg="alan str olmalı")
raises(ValueError, iz_zinciri_raporu, [dict(_kok04, tur="http", alanlar={"http_kod": True})], msg="http_kod bool ret")
raises(ValueError, iz_zinciri_raporu, [dict(_kok04, tur="http", alanlar={"http_kod": 99})], msg="http_kod 99 ret")
raises(ValueError, iz_zinciri_raporu, [dict(_kok04, tur="http", alanlar={"http_kod": 600})], msg="http_kod 600 ret")
raises(ValueError, iz_zinciri_raporu, [dict(_kok04, tur="model", alanlar={"token_in": True})], msg="token_in bool ret")
raises(ValueError, iz_zinciri_raporu, [dict(_kok04, tur="model", alanlar={"token_in": -1})], msg="token_in negatif ret")
raises(ValueError, iz_zinciri_raporu, [_kok04, dict(_kok04, olay_id="cocuk-1", parent_id=_kok04["olay_id"], zaman_ms=5)], msg="çocuk zamanı ebeveynden küçük olamaz")
raises(ValueError, iz_zinciri_raporu, [dict(_kok04, ek=1)], msg="olay fazla alan ret")
raises(ValueError, iz_zinciri_raporu, [dict(_kok04, tur="diger")], msg="geçersiz olay türü ret")
raises(ValueError, iz_zinciri_raporu, [dict(_kok04, sure_ms=True)], msg="sure_ms bool ret")
raises(ValueError, iz_zinciri_raporu, [dict(_kok04, sure_ms=float("nan"))], msg="sure_ms NaN ret")
raises(ValueError, iz_zinciri_raporu, [dict(_kok04, alanlar=[])], msg="alanlar list olamaz")
raises(ValueError, iz_zinciri_raporu, [dict(_kok04, tur="http", alanlar={"http_kod": 200.0})], msg="http_kod float ret")
raises(ValueError, iz_zinciri_raporu, [_kok04, dict(_kok04, olay_id="c-2", parent_id=[1])], msg="kök varken str olmayan parent_id ret")
# --- carbon-c8-ek-son ---
```

```solution
from ai_savunma_veri import json_yukle,metin_yukle

def guvenli_telemetri_olayi(olay):
    import math
    zorunlu = {"iz_id", "olay_id", "parent_id", "tur", "zaman_ms", "sure_ms", "alanlar"}
    if not isinstance(olay, dict):
        raise ValueError("olay geçersiz")
    if set(olay) != zorunlu:
        raise ValueError("olay şeması geçersiz")
    for alan in ("iz_id", "olay_id"):
        deger = olay[alan]
        if not isinstance(deger, str):
            raise ValueError("kimlik geçersiz")
        if not deger or deger != deger.strip():
            raise ValueError("kimlik geçersiz")
    # Parent türü, kapsamı ve döngüsü aşağıda aynı trace grafiğinde doğrulanır.
    tur = olay["tur"]
    if tur not in ("http", "model", "guardrail", "arac"):
        raise ValueError("olay türü geçersiz")
    for alan in ("zaman_ms", "sure_ms"):
        deger = olay[alan]
        if isinstance(deger, bool) or not isinstance(deger, (int, float)):
            raise ValueError("süre geçersiz")
        if not math.isfinite(deger):
            raise ValueError("süre sonlu olmalı")
        if deger < 0:
            raise ValueError("süre negatif olamaz")
    alanlar = olay["alanlar"]
    if not isinstance(alanlar, dict):
        raise ValueError("alanlar geçersiz")
    izinli = {"durum", "hata_kodu"} | {
        "http": {"http_kod", "yontem"}, "model": {"model", "token_in", "token_out"},
        "guardrail": {"karar"}, "arac": {"arac"},
    }[tur]
    if any(alan not in izinli for alan in alanlar):
        raise ValueError("bilinmeyen veya hassas alan")
    for alan in ("hata_kodu", "yontem", "model", "arac"):
        if alan in alanlar:
            deger = alanlar[alan]
            if not isinstance(deger, str) or not deger or deger != deger.strip():
                raise ValueError("metin alanı geçersiz")
    if "durum" in alanlar and alanlar["durum"] not in ("ok", "hata"):
        raise ValueError("durum geçersiz")
    if "karar" in alanlar and alanlar["karar"] not in ("izin", "reddet", "hata"):
        raise ValueError("karar geçersiz")
    if "http_kod" in alanlar:
        kod = alanlar["http_kod"]
        if type(kod) is not int or kod < 100 or kod > 599:
            raise ValueError("HTTP kodu geçersiz")
    for alan in ("token_in", "token_out"):
        if alan in alanlar:
            deger = alanlar[alan]
            if type(deger) is not int or deger < 0:
                raise ValueError("token sayısı geçersiz")
    sonuc = dict(olay)
    sonuc["alanlar"] = {alan: alanlar[alan] for alan in sorted(alanlar)}
    return sonuc

def iz_zinciri_raporu(olaylar):
    import math
    if not isinstance(olaylar, list):
        raise ValueError("olay listesi geçersiz")
    izler = {}
    kimlikler = set()
    for olay in olaylar:
        olay=guvenli_telemetri_olayi(olay)
        kimlik = (olay["iz_id"], olay["olay_id"])
        if kimlik in kimlikler:
            raise ValueError("olay kimliği yinelenemez")
        kimlikler.add(kimlik)
        izler.setdefault(olay["iz_id"], []).append(olay)
    sonuc = []
    for iz_id in sorted(izler):
        kayitlar = izler[iz_id]
        id_map = {x["olay_id"]: x for x in kayitlar}
        for olay in kayitlar:
            parent = olay["parent_id"]
            if parent is None:
                continue
            if not isinstance(parent, str):
                raise ValueError("parent kimliği geçersiz")
            if parent not in id_map:
                raise ValueError("parent aynı trace içinde olmalı")
            if id_map[parent]["zaman_ms"] > olay["zaman_ms"]:
                raise ValueError("parent zamanı geçersiz")
            gorulen = set()
            yuruyen = olay["olay_id"]
            while yuruyen is not None:
                if yuruyen in gorulen:
                    raise ValueError("parent döngüsü")
                gorulen.add(yuruyen)
                yuruyen = id_map[yuruyen]["parent_id"]
        sirali = sorted(kayitlar, key=lambda x: (x["zaman_ms"], x["olay_id"]))
        baslangic = min(x["zaman_ms"] for x in kayitlar)
        bitis = max(x["zaman_ms"] + x["sure_ms"] for x in kayitlar)
        sonuc.append({"iz_id": iz_id, "kokler": [x["olay_id"] for x in sirali if x["parent_id"] is None], "olaylar": [x["olay_id"] for x in sirali], "baslangic_ms": baslangic, "bitis_ms": bitis, "sure_ms": bitis - baslangic})
    return sonuc

v=json_yukle("veri/telemetri.json")
print("Sentetik iz zincirleri:",iz_zinciri_raporu(v["olaylar"]))
```

```hint
Trace'leri önce `iz_id` ile grupla. Her grup içinde olay kimliği haritası kur, parent ve döngüyü bu haritada denetle; süreyi minimum başlangıç ve maksimum bitişten hesapla.
```
:::

::: anlat Telemetri özeti içerik yerine ölçüm taşır
Sayısal özet; olay, trace, hata, ret ve token sayılarını toplar. Tür bazında ortalama süre, hangi aşamanın yavaşladığını gösterir. Hata, `durum = hata` veya `hata_kodu` bulunmasıyla belirlenir. Guardrail'in `reddet` kararı teknik hata değildir ve ayrı sayılır.

Ortalama süre üç ondalık basamağa yuvarlanır. Çıktı yalnız sabit ölçüm alanları ve olay türü anahtarları içerir; kullanıcı kimliği, model girdisi veya serbest metin taşımaz.
:::

::: gorev 3 · Tür bazında güvenli telemetri metrikleri hesapla
`telemetri_metrik_raporu(olaylar)` işlevini yaz. İlk görevin tam doğrulayıcısını bu bağımsız kod alanına da alabilirsin. Olaylar ilk görevdeki bütün şema, tür ve alan kurallarını sağlasın; olay kimliklerinin trace içinde yinelenmediğini de doğrula. Geçersiz veride `ValueError` yükselt.

Dönüş:

```text
{"toplam":N,"iz_sayisi":N,"hatali":N,"reddedildi":N,
 "token_in":N,"token_out":N,
 "turler":{TUR:{"sayi":N,"ortalama_sure_ms":ORT},...}}
```

`hatali`, durumu `hata` olan veya `hata_kodu` taşıyan olay sayısıdır; aynı olay iki koşulda da bir kez sayılır. `reddedildi`, `karar = reddet` olaylarıdır. Token alanları bulunmadığında sıfır kabul edilir. Türleri alfabetik sıralı sözlükte, her ortalama süreyi üç ondalığa yuvarlanmış şekilde döndür. Boş girdi için türler boş, sayaçlar sıfır olur. Girdiyi değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-04")
```

```starter
from ai_savunma_veri import json_yukle,metin_yukle

def telemetri_metrik_raporu(olaylar):
    # KUSURLU BAŞLANGIÇ KODU: hata kodunu saymaz ve guardrail reddini hataya eşitler.
    gruplar={}
    for o in olaylar:gruplar.setdefault(o["tur"],[]).append(o["sure_ms"])
    hata=sum(o["alanlar"].get("durum")=="hata" for o in olaylar)
    return {"toplam":len(olaylar),"iz_sayisi":len({o["iz_id"] for o in olaylar}),"hatali":hata,"reddedildi":hata,"token_in":sum(o["alanlar"].get("token_in",0) for o in olaylar),"token_out":sum(o["alanlar"].get("token_out",0) for o in olaylar),"turler":{t:{"sayi":len(v),"ortalama_sure_ms":round(sum(v)/len(v),3)} for t,v in sorted(gruplar.items())}}

v=json_yukle("veri/telemetri.json")
print("Sentetik metrikler:",telemetri_metrik_raporu(v["olaylar"]))
```

```test
import copy
O = [
    {"iz_id": "a", "olay_id": "h1", "parent_id": None, "tur": "http", "zaman_ms": 0, "sure_ms": 10, "alanlar": {"http_kod": 200}},
    {"iz_id": "a", "olay_id": "m1", "parent_id": "h1", "tur": "model", "zaman_ms": 1, "sure_ms": 1, "alanlar": {"token_in": 3, "token_out": 2, "durum": "hata"}},
    {"iz_id": "b", "olay_id": "m2", "parent_id": None, "tur": "model", "zaman_ms": 0, "sure_ms": 2, "alanlar": {"token_in": 4, "hata_kodu": "E1"}},
    {"iz_id": "b", "olay_id": "g1", "parent_id": "m2", "tur": "guardrail", "zaman_ms": 2, "sure_ms": 2, "alanlar": {"karar": "reddet", "durum": "hata", "hata_kodu": "E2"}},
]
BEKLENEN = {"toplam": 4, "iz_sayisi": 2, "hatali": 3, "reddedildi": 1, "token_in": 7, "token_out": 2, "turler": {"guardrail": {"sayi": 1, "ortalama_sure_ms": 2.0}, "http": {"sayi": 1, "ortalama_sure_ms": 10.0}, "model": {"sayi": 2, "ortalama_sure_ms": 1.5}}}
def sozlesme(fn):
    try:
        once = copy.deepcopy(O)
        if fn(O) != BEKLENEN or O != once or fn(list(reversed(O))) != BEKLENEN:
            return False
        if fn([]) != {"toplam": 0, "iz_sayisi": 0, "hatali": 0, "reddedildi": 0, "token_in": 0, "token_out": 0, "turler": {}}:
            return False
        uc = [dict(O[0], olay_id=str(i), sure_ms=x) for i, x in enumerate((1, 2, 2))]
        if fn(uc)["turler"]["http"]["ortalama_sure_ms"] != 1.667:
            return False
        if fn([dict(O[0], sure_ms=0)])["turler"]["http"]["ortalama_sure_ms"] != 0.0:
            return False
        for kod in (100, 599):
            if fn([dict(O[0], alanlar={"http_kod": kod})])["toplam"] != 1:
                return False
        sifir_token = fn([dict(O[1], alanlar={"token_in": 0, "token_out": 0})])
        if sifir_token["token_in"] != 0 or sifir_token["token_out"] != 0 or sifir_token["hatali"] != 0:
            return False
        for olaylar in [
            None, {}, [None], O + [O[0]], [dict(O[0], ek=1)],
            [dict(O[0], zaman_ms=True)], [dict(O[0], sure_ms=float("nan"))],
            [dict(O[0], iz_id="")], [dict(O[0], iz_id=" x")], [dict(O[0], olay_id=None)],
            [dict(O[0], alanlar={"prompt": "x"})],
            [dict(O[1], alanlar={"token_in": True})],
            [dict(O[0], alanlar={"http_kod": 99})],
            [dict(O[0], alanlar={"http_kod": 600})],
        ]:
            try:
                fn(olaylar)
                return False
            except ValueError:
                pass
        # Aynı olay sözleşmesi tüm bağımsız görevlerde korunur.
        temel={"iz_id":"t","olay_id":"e","parent_id":None,"tur":"model","zaman_ms":0,"sure_ms":0,"alanlar":{}}
        boz=[dict(temel,parent_id=True),dict(temel,parent_id=" e"),dict(temel,parent_id="e"),dict(temel,zaman_ms=-1)]
        for tur,alan in [("model","model"),("http","yontem"),("arac","arac"),("model","hata_kodu")]:
            for val in [None,True,""," x","x "]:
                boz.append(dict(temel,tur=tur,alanlar={alan:val}))
        for tur,alan,val in [("http","http_kod",True),("model","token_out",True),("model","token_in",-1),("guardrail","karar","x"),("model","durum","x"),("model","Authorization","sentetik"),("model","eposta","demo@example.invalid")]:
            boz.append(dict(temel,tur=tur,alanlar={alan:val}))
        for olay in boz:
            try:
                fn([olay])
                return False
            except ValueError:pass
        for tur,alan,val in [("arac","arac","yerel"),("http","yontem","POST"),("model","hata_kodu","E"),("guardrail","karar","izin"),("guardrail","karar","hata")]:
            olay=dict(temel,tur=tur,alanlar={alan:val})
            fn([olay])
        return True
    except Exception:
        return False
ok(sozlesme(telemetri_metrik_raporu), "hata ve ret ayrımı, token toplamları ve yuvarlanmış ortalamalar korunmalı")
def m_hata(olaylar):
    sonuc = telemetri_metrik_raporu(olaylar)
    sonuc["hatali"] = sum(1 for o in olaylar if o["alanlar"].get("durum") == "hata")
    return sonuc
def m_ret(olaylar):
    sonuc = telemetri_metrik_raporu(olaylar)
    sonuc["reddedildi"] = sonuc["hatali"]
    return sonuc
def m_ortalama(olaylar):
    sonuc = telemetri_metrik_raporu(olaylar)
    for x in sonuc["turler"].values():
        x["ortalama_sure_ms"] += 1
    return sonuc
for ad, mutant in [("hata kodunu saymayan", m_hata), ("ret sayısını hataya eşitleyen", m_ret), ("ortalama süreyi bozan", m_ortalama)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
# --- carbon-c8-ek-bas ---
_kok04m = dict(O[0], parent_id=None)
raises(ValueError, telemetri_metrik_raporu, [dict(_kok04m, iz_id=123)], msg="iz_id str olmalı")
raises(ValueError, telemetri_metrik_raporu, [dict(_kok04m, olay_id=123)], msg="olay_id str olmalı")
raises(ValueError, telemetri_metrik_raporu, [dict(_kok04m, parent_id=123)], msg="parent_id str/None olmalı")
raises(ValueError, telemetri_metrik_raporu, [dict(_kok04m, alanlar={"hata_kodu": 123})], msg="hata_kodu str olmalı")
raises(ValueError, telemetri_metrik_raporu, [dict(_kok04m, tur="model", alanlar={"token_out": -1})], msg="negatif token_out ret")
raises(ValueError, telemetri_metrik_raporu, [dict(_kok04m, tur="model", alanlar={"token_out": True})], msg="bool token_out ret")
raises(ValueError, telemetri_metrik_raporu, [_kok04m, dict(_kok04m, olay_id="c-2", parent_id="")], msg="boş parent_id ret")
raises(ValueError, telemetri_metrik_raporu, [dict(_kok04m, tur="diger")], msg="geçersiz tür ret")
raises(ValueError, telemetri_metrik_raporu, [dict(_kok04m, sure_ms="1.0")], msg="str sure_ms ret")
raises(ValueError, telemetri_metrik_raporu, [dict(_kok04m, alanlar=[])], msg="alanlar list olamaz")
raises(ValueError, telemetri_metrik_raporu, [dict(_kok04m, tur="http", alanlar={"http_kod": 200.0})], msg="float http_kod ret")
# --- carbon-c8-ek-son ---
```

```solution
from ai_savunma_veri import json_yukle,metin_yukle

def guvenli_telemetri_olayi(olay):
    import math
    zorunlu = {"iz_id", "olay_id", "parent_id", "tur", "zaman_ms", "sure_ms", "alanlar"}
    if not isinstance(olay, dict):
        raise ValueError("olay geçersiz")
    if set(olay) != zorunlu:
        raise ValueError("olay şeması geçersiz")
    for alan in ("iz_id", "olay_id"):
        deger = olay[alan]
        if not isinstance(deger, str):
            raise ValueError("kimlik geçersiz")
        if not deger or deger != deger.strip():
            raise ValueError("kimlik geçersiz")
    parent = olay["parent_id"]
    if parent is not None:
        if not isinstance(parent, str):
            raise ValueError("parent geçersiz")
        if not parent or parent != parent.strip():
            raise ValueError("parent geçersiz")
        if parent == olay["olay_id"]:
            raise ValueError("olay kendi parentı olamaz")
    tur = olay["tur"]
    if tur not in ("http", "model", "guardrail", "arac"):
        raise ValueError("olay türü geçersiz")
    for alan in ("zaman_ms", "sure_ms"):
        deger = olay[alan]
        if isinstance(deger, bool) or not isinstance(deger, (int, float)):
            raise ValueError("süre geçersiz")
        if not math.isfinite(deger):
            raise ValueError("süre sonlu olmalı")
        if deger < 0:
            raise ValueError("süre negatif olamaz")
    alanlar = olay["alanlar"]
    if not isinstance(alanlar, dict):
        raise ValueError("alanlar geçersiz")
    izinli = {"durum", "hata_kodu"} | {
        "http": {"http_kod", "yontem"}, "model": {"model", "token_in", "token_out"},
        "guardrail": {"karar"}, "arac": {"arac"},
    }[tur]
    if any(alan not in izinli for alan in alanlar):
        raise ValueError("bilinmeyen veya hassas alan")
    for alan in ("hata_kodu", "yontem", "model", "arac"):
        if alan in alanlar:
            deger = alanlar[alan]
            if not isinstance(deger, str) or not deger or deger != deger.strip():
                raise ValueError("metin alanı geçersiz")
    if "durum" in alanlar and alanlar["durum"] not in ("ok", "hata"):
        raise ValueError("durum geçersiz")
    if "karar" in alanlar and alanlar["karar"] not in ("izin", "reddet", "hata"):
        raise ValueError("karar geçersiz")
    if "http_kod" in alanlar:
        kod = alanlar["http_kod"]
        if type(kod) is not int or kod < 100 or kod > 599:
            raise ValueError("HTTP kodu geçersiz")
    for alan in ("token_in", "token_out"):
        if alan in alanlar:
            deger = alanlar[alan]
            if type(deger) is not int or deger < 0:
                raise ValueError("token sayısı geçersiz")
    sonuc = dict(olay)
    sonuc["alanlar"] = {alan: alanlar[alan] for alan in sorted(alanlar)}
    return sonuc

def telemetri_metrik_raporu(olaylar):
    if not isinstance(olaylar,list):raise ValueError("olay listesi geçersiz")
    kimlikler=set();gruplar={}
    hatali=reddedildi=token_in=token_out=0
    for olay in olaylar:
        olay=guvenli_telemetri_olayi(olay)
        anahtar=(olay["iz_id"],olay["olay_id"])
        if anahtar in kimlikler:raise ValueError("olay kimliği yinelenemez")
        kimlikler.add(anahtar)
        a=olay["alanlar"]
        if a.get("durum")=="hata" or "hata_kodu" in a:hatali+=1
        if a.get("karar")=="reddet":reddedildi+=1
        token_in+=a.get("token_in",0);token_out+=a.get("token_out",0)
        gruplar.setdefault(olay["tur"],[]).append(olay["sure_ms"])
    turler={t:{"sayi":len(v),"ortalama_sure_ms":round(sum(v)/len(v),3)} for t,v in sorted(gruplar.items())}
    return {"toplam":len(olaylar),"iz_sayisi":len({x["iz_id"] for x in olaylar}),"hatali":hatali,"reddedildi":reddedildi,"token_in":token_in,"token_out":token_out,"turler":turler}


v=json_yukle("veri/telemetri.json")
print("Sentetik metrikler:",telemetri_metrik_raporu(v["olaylar"]))
```

```hint
Her olayı doğrularken sayaçları ve türe göre süre listelerini biriktir. Hata için iki koşulu tek bir karar olarak ele al; aynı olayı iki kez artırma.
```
:::

::: anlat Telemetri gerçek trafikten üretilir, içerik taşımaz
Buraya kadar telemetri olayları sentetik fixture'dı. Gerçekte bu olaylar canlı trafikten üretilir: her model çağrısı bir gecikme (sure_ms) ve token sayısı (token_out) bırakır — ama güvenli telemetri bu ölçüleri alır, istem ve yanıt **metnini** almaz. Son görevde senin `telemetri_metrik_raporu` işlevin, yerel modele yapılan **gerçek isteklerden** üretilmiş telemetri olaylarını toplar: süreler ve tokenlar gerçektir, hiçbir olay ham istem içermez. Deney ayrıca olaylarda istem metninin sızmadığını doğrular — telemetrinin kendisi bir sızıntı yüzeyi olmamalıdır.
:::

::: gorev Gerçek deney · Gerçek trafikten güvenli telemetri metrikleri
`telemetri_metrik_raporu(olaylar)` işlevini yaz — kuralları ve çıktısı 3. görevdekiyle **aynıdır**. Deney yerel modele birkaç gerçek istek atar, her birinden gerçek süre ve çıktı token sayısı taşıyan (ham istem/yanıt taşımayan) bir model telemetri olayı kurar ve senin raporun bunları toplar.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def telemetri_metrik_raporu(olaylar):
    return {}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_04 as deney
    deney.goster(telemetri_metrik_raporu)
```

```test
import ai_lab
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
import ast
yasak=("referans","referans_rapor","getattr","kanit_yaz")
sorun=ai_lab.kod_denetimi(src,yasak)
try:
    for node in ast.walk(ast.parse(src)):
        if isinstance(node,ast.ImportFrom) and any(a.name in yasak or a.name=="*" for a in node.names):sorun.append("referans ithali")
except SyntaxError:sorun.append("sözdizimi")
kontrol(not sorun, "laboratuvar yamalanmamalı, referans kullanılmamalı " + ", ".join(sorun))
if sorun:stop()
fn = need("telemetri_metrik_raporu")
from sandbox import ai_gercek_ai_savunma_04 as D
ornek = [{"iz_id": "a", "olay_id": "m1", "parent_id": None, "tur": "model", "zaman_ms": 0, "sure_ms": 12.0, "alanlar": {"model": "yerel", "token_out": 5, "durum": "ok"}},
         {"iz_id": "a", "olay_id": "g1", "parent_id": "m1", "tur": "guardrail", "zaman_ms": 1, "sure_ms": 2, "alanlar": {"karar": "reddet"}}]
import copy
import copy
O = [
    {"iz_id": "a", "olay_id": "h1", "parent_id": None, "tur": "http", "zaman_ms": 0, "sure_ms": 10, "alanlar": {"http_kod": 200}},
    {"iz_id": "a", "olay_id": "m1", "parent_id": "h1", "tur": "model", "zaman_ms": 1, "sure_ms": 1, "alanlar": {"token_in": 3, "token_out": 2, "durum": "hata"}},
    {"iz_id": "b", "olay_id": "m2", "parent_id": None, "tur": "model", "zaman_ms": 0, "sure_ms": 2, "alanlar": {"token_in": 4, "hata_kodu": "E1"}},
    {"iz_id": "b", "olay_id": "g1", "parent_id": "m2", "tur": "guardrail", "zaman_ms": 2, "sure_ms": 2, "alanlar": {"karar": "reddet", "durum": "hata", "hata_kodu": "E2"}},
]
BEKLENEN = {"toplam": 4, "iz_sayisi": 2, "hatali": 3, "reddedildi": 1, "token_in": 7, "token_out": 2, "turler": {"guardrail": {"sayi": 1, "ortalama_sure_ms": 2.0}, "http": {"sayi": 1, "ortalama_sure_ms": 10.0}, "model": {"sayi": 2, "ortalama_sure_ms": 1.5}}}
def sozlesme(fn):
    try:
        once = copy.deepcopy(O)
        if fn(O) != BEKLENEN or O != once or fn(list(reversed(O))) != BEKLENEN:
            return False
        if fn([]) != {"toplam": 0, "iz_sayisi": 0, "hatali": 0, "reddedildi": 0, "token_in": 0, "token_out": 0, "turler": {}}:
            return False
        uc = [dict(O[0], olay_id=str(i), sure_ms=x) for i, x in enumerate((1, 2, 2))]
        if fn(uc)["turler"]["http"]["ortalama_sure_ms"] != 1.667:
            return False
        if fn([dict(O[0], sure_ms=0)])["turler"]["http"]["ortalama_sure_ms"] != 0.0:
            return False
        for kod in (100, 599):
            if fn([dict(O[0], alanlar={"http_kod": kod})])["toplam"] != 1:
                return False
        sifir_token = fn([dict(O[1], alanlar={"token_in": 0, "token_out": 0})])
        if sifir_token["token_in"] != 0 or sifir_token["token_out"] != 0 or sifir_token["hatali"] != 0:
            return False
        for olaylar in [
            None, {}, [None], O + [O[0]], [dict(O[0], ek=1)],
            [dict(O[0], zaman_ms=True)], [dict(O[0], sure_ms=float("nan"))],
            [dict(O[0], iz_id="")], [dict(O[0], iz_id=" x")], [dict(O[0], olay_id=None)],
            [dict(O[0], alanlar={"prompt": "x"})],
            [dict(O[1], alanlar={"token_in": True})],
            [dict(O[0], alanlar={"http_kod": 99})],
            [dict(O[0], alanlar={"http_kod": 600})],
        ]:
            try:
                fn(olaylar)
                return False
            except ValueError:
                pass
        # Aynı olay sözleşmesi tüm bağımsız görevlerde korunur.
        temel={"iz_id":"t","olay_id":"e","parent_id":None,"tur":"model","zaman_ms":0,"sure_ms":0,"alanlar":{}}
        boz=[dict(temel,parent_id=True),dict(temel,parent_id=" e"),dict(temel,parent_id="e"),dict(temel,zaman_ms=-1)]
        for tur,alan in [("model","model"),("http","yontem"),("arac","arac"),("model","hata_kodu")]:
            for val in [None,True,""," x","x "]:
                boz.append(dict(temel,tur=tur,alanlar={alan:val}))
        for tur,alan,val in [("http","http_kod",True),("model","token_out",True),("model","token_in",-1),("guardrail","karar","x"),("model","durum","x"),("model","Authorization","sentetik"),("model","eposta","demo@example.invalid")]:
            boz.append(dict(temel,tur=tur,alanlar={alan:val}))
        for olay in boz:
            try:
                fn([olay])
                return False
            except ValueError:pass
        for tur,alan,val in [("arac","arac","yerel"),("http","yontem","POST"),("model","hata_kodu","E"),("guardrail","karar","izin"),("guardrail","karar","hata")]:
            olay=dict(temel,tur=tur,alanlar={alan:val})
            fn([olay])
        return True
    except Exception:
        return False
for ad,mutant in [("boş",None),("sabit",lambda *a:{}),("hep boş metrik",lambda *a:D.referans_rapor([]))]:
    kontrol(not sozlesme(mutant),"hatalı çözüm reddedilmeli: "+ad)
kontrol(sozlesme(fn), "güvenli telemetri metrikleri doğru; hassas alan ve geçersiz girdi reddedilmeli")
def _olay_denetle(olay):
    import math
    zorunlu = {"iz_id", "olay_id", "parent_id", "tur", "zaman_ms", "sure_ms", "alanlar"}
    if not isinstance(olay, dict):
        raise ValueError("olay geçersiz")
    if set(olay) != zorunlu:
        raise ValueError("olay şeması geçersiz")
    for alan in ("iz_id", "olay_id"):
        deger = olay[alan]
        if not isinstance(deger, str):
            raise ValueError("kimlik geçersiz")
        if not deger or deger != deger.strip():
            raise ValueError("kimlik geçersiz")
    parent = olay["parent_id"]
    if parent is not None:
        if not isinstance(parent, str):
            raise ValueError("parent geçersiz")
        if not parent or parent != parent.strip():
            raise ValueError("parent geçersiz")
        if parent == olay["olay_id"]:
            raise ValueError("olay kendi parentı olamaz")
    tur = olay["tur"]
    if tur not in ("http", "model", "guardrail", "arac"):
        raise ValueError("olay türü geçersiz")
    for alan in ("zaman_ms", "sure_ms"):
        deger = olay[alan]
        if isinstance(deger, bool) or not isinstance(deger, (int, float)):
            raise ValueError("süre geçersiz")
        if not math.isfinite(deger):
            raise ValueError("süre sonlu olmalı")
        if deger < 0:
            raise ValueError("süre negatif olamaz")
    alanlar = olay["alanlar"]
    if not isinstance(alanlar, dict):
        raise ValueError("alanlar geçersiz")
    izinli = {"durum", "hata_kodu"} | {
        "http": {"http_kod", "yontem"}, "model": {"model", "token_in", "token_out"},
        "guardrail": {"karar"}, "arac": {"arac"},
    }[tur]
    if any(alan not in izinli for alan in alanlar):
        raise ValueError("bilinmeyen veya hassas alan")
    for alan in ("hata_kodu", "yontem", "model", "arac"):
        if alan in alanlar:
            deger = alanlar[alan]
            if not isinstance(deger, str) or not deger or deger != deger.strip():
                raise ValueError("metin alanı geçersiz")
    if "durum" in alanlar and alanlar["durum"] not in ("ok", "hata"):
        raise ValueError("durum geçersiz")
    if "karar" in alanlar and alanlar["karar"] not in ("izin", "reddet", "hata"):
        raise ValueError("karar geçersiz")
    if "http_kod" in alanlar:
        kod = alanlar["http_kod"]
        if type(kod) is not int or kod < 100 or kod > 599:
            raise ValueError("HTTP kodu geçersiz")
    for alan in ("token_in", "token_out"):
        if alan in alanlar:
            deger = alanlar[alan]
            if type(deger) is not int or deger < 0:
                raise ValueError("token sayısı geçersiz")
    sonuc = dict(olay)
    sonuc["alanlar"] = {alan: alanlar[alan] for alan in sorted(alanlar)}
    return sonuc

def sozlesme_olay(o):
    try:_olay_denetle(o);return True
    except ValueError:return False

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
    guvenli_telemetri_olayi = need('guvenli_telemetri_olayi')
    telemetri_metrik_raporu = need('telemetri_metrik_raporu')
    def _birim_adim_3():
        import copy
        O = [
            {"iz_id": "a", "olay_id": "h1", "parent_id": None, "tur": "http", "zaman_ms": 0, "sure_ms": 10, "alanlar": {"http_kod": 200}},
            {"iz_id": "a", "olay_id": "m1", "parent_id": "h1", "tur": "model", "zaman_ms": 1, "sure_ms": 1, "alanlar": {"token_in": 3, "token_out": 2, "durum": "hata"}},
            {"iz_id": "b", "olay_id": "m2", "parent_id": None, "tur": "model", "zaman_ms": 0, "sure_ms": 2, "alanlar": {"token_in": 4, "hata_kodu": "E1"}},
            {"iz_id": "b", "olay_id": "g1", "parent_id": "m2", "tur": "guardrail", "zaman_ms": 2, "sure_ms": 2, "alanlar": {"karar": "reddet", "durum": "hata", "hata_kodu": "E2"}},
        ]
        BEKLENEN = {"toplam": 4, "iz_sayisi": 2, "hatali": 3, "reddedildi": 1, "token_in": 7, "token_out": 2, "turler": {"guardrail": {"sayi": 1, "ortalama_sure_ms": 2.0}, "http": {"sayi": 1, "ortalama_sure_ms": 10.0}, "model": {"sayi": 2, "ortalama_sure_ms": 1.5}}}
        def sozlesme(fn):
            try:
                once = copy.deepcopy(O)
                if fn(O) != BEKLENEN or O != once or fn(list(reversed(O))) != BEKLENEN:
                    return False
                if fn([]) != {"toplam": 0, "iz_sayisi": 0, "hatali": 0, "reddedildi": 0, "token_in": 0, "token_out": 0, "turler": {}}:
                    return False
                uc = [dict(O[0], olay_id=str(i), sure_ms=x) for i, x in enumerate((1, 2, 2))]
                if fn(uc)["turler"]["http"]["ortalama_sure_ms"] != 1.667:
                    return False
                if fn([dict(O[0], sure_ms=0)])["turler"]["http"]["ortalama_sure_ms"] != 0.0:
                    return False
                for kod in (100, 599):
                    if fn([dict(O[0], alanlar={"http_kod": kod})])["toplam"] != 1:
                        return False
                sifir_token = fn([dict(O[1], alanlar={"token_in": 0, "token_out": 0})])
                if sifir_token["token_in"] != 0 or sifir_token["token_out"] != 0 or sifir_token["hatali"] != 0:
                    return False
                for olaylar in [
                    None, {}, [None], O + [O[0]], [dict(O[0], ek=1)],
                    [dict(O[0], zaman_ms=True)], [dict(O[0], sure_ms=float("nan"))],
                    [dict(O[0], iz_id="")], [dict(O[0], iz_id=" x")], [dict(O[0], olay_id=None)],
                    [dict(O[0], alanlar={"prompt": "x"})],
                    [dict(O[1], alanlar={"token_in": True})],
                    [dict(O[0], alanlar={"http_kod": 99})],
                    [dict(O[0], alanlar={"http_kod": 600})],
                ]:
                    try:
                        fn(olaylar)
                        return False
                    except ValueError:
                        pass
                # Aynı olay sözleşmesi tüm bağımsız görevlerde korunur.
                temel={"iz_id":"t","olay_id":"e","parent_id":None,"tur":"model","zaman_ms":0,"sure_ms":0,"alanlar":{}}
                boz=[dict(temel,parent_id=True),dict(temel,parent_id=" e"),dict(temel,parent_id="e"),dict(temel,zaman_ms=-1)]
                for tur,alan in [("model","model"),("http","yontem"),("arac","arac"),("model","hata_kodu")]:
                    for val in [None,True,""," x","x "]:
                        boz.append(dict(temel,tur=tur,alanlar={alan:val}))
                for tur,alan,val in [("http","http_kod",True),("model","token_out",True),("model","token_in",-1),("guardrail","karar","x"),("model","durum","x"),("model","Authorization","sentetik"),("model","eposta","demo@example.invalid")]:
                    boz.append(dict(temel,tur=tur,alanlar={alan:val}))
                for olay in boz:
                    try:
                        fn([olay])
                        return False
                    except ValueError:pass
                for tur,alan,val in [("arac","arac","yerel"),("http","yontem","POST"),("model","hata_kodu","E"),("guardrail","karar","izin"),("guardrail","karar","hata")]:
                    olay=dict(temel,tur=tur,alanlar={alan:val})
                    fn([olay])
                return True
            except Exception:
                return False
        ok(sozlesme(telemetri_metrik_raporu), "hata ve ret ayrımı, token toplamları ve yuvarlanmış ortalamalar korunmalı")
        def m_hata(olaylar):
            sonuc = telemetri_metrik_raporu(olaylar)
            sonuc["hatali"] = sum(1 for o in olaylar if o["alanlar"].get("durum") == "hata")
            return sonuc
        def m_ret(olaylar):
            sonuc = telemetri_metrik_raporu(olaylar)
            sonuc["reddedildi"] = sonuc["hatali"]
            return sonuc
        def m_ortalama(olaylar):
            sonuc = telemetri_metrik_raporu(olaylar)
            for x in sonuc["turler"].values():
                x["ortalama_sure_ms"] += 1
            return sonuc
        for ad, mutant in [("hata kodunu saymayan", m_hata), ("ret sayısını hataya eşitleyen", m_ret), ("ortalama süreyi bozan", m_ortalama)]:
            ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
        _kok04m = dict(O[0], parent_id=None)
        raises(ValueError, telemetri_metrik_raporu, [dict(_kok04m, iz_id=123)], msg="iz_id str olmalı")
        raises(ValueError, telemetri_metrik_raporu, [dict(_kok04m, olay_id=123)], msg="olay_id str olmalı")
        raises(ValueError, telemetri_metrik_raporu, [dict(_kok04m, parent_id=123)], msg="parent_id str/None olmalı")
        raises(ValueError, telemetri_metrik_raporu, [dict(_kok04m, alanlar={"hata_kodu": 123})], msg="hata_kodu str olmalı")
        raises(ValueError, telemetri_metrik_raporu, [dict(_kok04m, tur="model", alanlar={"token_out": -1})], msg="negatif token_out ret")
        raises(ValueError, telemetri_metrik_raporu, [dict(_kok04m, tur="model", alanlar={"token_out": True})], msg="bool token_out ret")
        raises(ValueError, telemetri_metrik_raporu, [_kok04m, dict(_kok04m, olay_id="c-2", parent_id="")], msg="boş parent_id ret")
        raises(ValueError, telemetri_metrik_raporu, [dict(_kok04m, tur="diger")], msg="geçersiz tür ret")
        raises(ValueError, telemetri_metrik_raporu, [dict(_kok04m, sure_ms="1.0")], msg="str sure_ms ret")
        raises(ValueError, telemetri_metrik_raporu, [dict(_kok04m, alanlar=[])], msg="alanlar list olamaz")
        raises(ValueError, telemetri_metrik_raporu, [dict(_kok04m, tur="http", alanlar={"http_kod": 200.0})], msg="float http_kod ret")
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
    kontrol(len(r["deney_kaydi"])==3 and not r["hatalar"] and all(x.get("basarili") for x in r["deney_kaydi"]),"üç gerçek istek tamamlandı; hata yok")
    kontrol(all(sozlesme_olay(o) for o in r["olaylar"]),"gerçek olaylar izinli şema ve içerik sınırını koruyor")
    kontrol(r["rapor"] == D.referans_rapor(r["olaylar"]), "gerçek telemetri metrikleri bağımsız hesapla aynı")
    kontrol(not r["sizan_istem"], f"telemetri olaylarında ham istem sızmadı (sızan: {r['sizan_istem'] or 'yok'})")
    oz = D.ozet(r)
    kontrol(oz["token_out"] > 0 and oz["olay"] > 0, f"gerçek token/süre ölçüldü: {oz['olay']} olay, token_out {oz['token_out']}, ort süre {oz['model_ort_sure_ms']} ms")
yol = ai_lab.kanit_yaz("savunma-telemetri", {"kaynak": "gercek" if r and r.get("deney_kaydi") else "fixture", "kabul": all(sonuclar), "ders": "ai-savunma-04",
                                             "ortam": (r or {}).get("ortam"), "ozet": oz, "olaylar":(r or {}).get("olaylar"), "rapor":(r or {}).get("rapor"), "laboratuvar_deney_kaydi":(r or {}).get("deney_kaydi"), "hatalar":(r or {}).get("hatalar"), "ayarlar":D.AYARLAR, "sinir":"Bu deney kaydı yalnız açık sentetik istemlerin kanıtıdır; güvenli telemetri içerik taşımaz; token_in ölçülmedi"})
if oz:
    ok(True, f"BULGU ({r['ortam']['model']['ad']}): {oz['olay']} gerçek istekten telemetri — token_out {oz['token_out']}, model ort süre {oz['model_ort_sure_ms']} ms; "
             f"sızan ham istem: {oz['sizan_istem']}. Telemetri gerçek ölçüleri taşır ama içerik taşımaz.")
```

```solution
import ai_lab

def guvenli_telemetri_olayi(olay):
    import math
    zorunlu = {"iz_id", "olay_id", "parent_id", "tur", "zaman_ms", "sure_ms", "alanlar"}
    if not isinstance(olay, dict):
        raise ValueError("olay geçersiz")
    if set(olay) != zorunlu:
        raise ValueError("olay şeması geçersiz")
    for alan in ("iz_id", "olay_id"):
        deger = olay[alan]
        if not isinstance(deger, str):
            raise ValueError("kimlik geçersiz")
        if not deger or deger != deger.strip():
            raise ValueError("kimlik geçersiz")
    parent = olay["parent_id"]
    if parent is not None:
        if not isinstance(parent, str):
            raise ValueError("parent geçersiz")
        if not parent or parent != parent.strip():
            raise ValueError("parent geçersiz")
        if parent == olay["olay_id"]:
            raise ValueError("olay kendi parentı olamaz")
    tur = olay["tur"]
    if tur not in ("http", "model", "guardrail", "arac"):
        raise ValueError("olay türü geçersiz")
    for alan in ("zaman_ms", "sure_ms"):
        deger = olay[alan]
        if isinstance(deger, bool) or not isinstance(deger, (int, float)):
            raise ValueError("süre geçersiz")
        if not math.isfinite(deger):
            raise ValueError("süre sonlu olmalı")
        if deger < 0:
            raise ValueError("süre negatif olamaz")
    alanlar = olay["alanlar"]
    if not isinstance(alanlar, dict):
        raise ValueError("alanlar geçersiz")
    izinli = {"durum", "hata_kodu"} | {
        "http": {"http_kod", "yontem"}, "model": {"model", "token_in", "token_out"},
        "guardrail": {"karar"}, "arac": {"arac"},
    }[tur]
    if any(alan not in izinli for alan in alanlar):
        raise ValueError("bilinmeyen veya hassas alan")
    for alan in ("hata_kodu", "yontem", "model", "arac"):
        if alan in alanlar:
            deger = alanlar[alan]
            if not isinstance(deger, str) or not deger or deger != deger.strip():
                raise ValueError("metin alanı geçersiz")
    if "durum" in alanlar and alanlar["durum"] not in ("ok", "hata"):
        raise ValueError("durum geçersiz")
    if "karar" in alanlar and alanlar["karar"] not in ("izin", "reddet", "hata"):
        raise ValueError("karar geçersiz")
    if "http_kod" in alanlar:
        kod = alanlar["http_kod"]
        if type(kod) is not int or kod < 100 or kod > 599:
            raise ValueError("HTTP kodu geçersiz")
    for alan in ("token_in", "token_out"):
        if alan in alanlar:
            deger = alanlar[alan]
            if type(deger) is not int or deger < 0:
                raise ValueError("token sayısı geçersiz")
    sonuc = dict(olay)
    sonuc["alanlar"] = {alan: alanlar[alan] for alan in sorted(alanlar)}
    return sonuc

def telemetri_metrik_raporu(olaylar):
    if not isinstance(olaylar,list):raise ValueError("olay listesi geçersiz")
    kimlikler=set();gruplar={}
    hatali=reddedildi=token_in=token_out=0
    for olay in olaylar:
        olay=guvenli_telemetri_olayi(olay)
        anahtar=(olay["iz_id"],olay["olay_id"])
        if anahtar in kimlikler:raise ValueError("olay kimliği yinelenemez")
        kimlikler.add(anahtar)
        a=olay["alanlar"]
        if a.get("durum")=="hata" or "hata_kodu" in a:hatali+=1
        if a.get("karar")=="reddet":reddedildi+=1
        token_in+=a.get("token_in",0);token_out+=a.get("token_out",0)
        gruplar.setdefault(olay["tur"],[]).append(olay["sure_ms"])
    turler={t:{"sayi":len(v),"ortalama_sure_ms":round(sum(v)/len(v),3)} for t,v in sorted(gruplar.items())}
    return {"toplam":len(olaylar),"iz_sayisi":len({x["iz_id"] for x in olaylar}),"hatali":hatali,"reddedildi":reddedildi,"token_in":token_in,"token_out":token_out,"turler":turler}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_04 as deney
    deney.goster(telemetri_metrik_raporu)
```

```hint
Bu işlev 3. görevdeki `telemetri_metrik_raporu` ile birebir aynıdır; tek fark, olayların gerçek model çağrılarından gelmesidir. Her olayı doğrula, hassas alanı reddet; türe göre süreleri biriktir ve ortalamayı 3 ondalığa yuvarla. Hata sayısında durum=hata ve hata_kodu'nu tek karar olarak ele al.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### İzlenebilirlik için ham sır gerekmez

Telemetri isteğin kimliğini, zamanını, türünü ve sonuç durumunu taşıyabilir; ham prompt veya credential taşımak zorunda değildir. Trace zinciri bu güvenli olaylardan kurulur. Tür bazlı metriklerde yanlış payda veya kopya olay sayımı sonucu şişirir. Kaydın az içerik taşıması otomatik yeterli denetim değildir; gerekli korelasyon alanları korunmalıdır.

| Yaygın yanlış | Mekanizmanın sınırı |
|---|---|
| Daha fazla ham log daha iyi güvenliktir | Gerekli iz ile hassas içerik ayrı tasarlanır. |

Saldırı–savunma bağlantısı: ai-saldiri-06.
:::

::: anlat Kaynak ile lab sonucunu ayır
[OpenTelemetry traces](https://opentelemetry.io/docs/concepts/signals/traces/). Trace ve span ilişkileri korelasyonu açıklar; bu derste OpenTelemetry SDK çalıştırıldığı iddia edilmez.
:::
