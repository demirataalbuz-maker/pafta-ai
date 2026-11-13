---
id: ai-savunma-01
title: Yerel LLM Saldırı Yüzeyi ve Güven Sınırları
summary: Bileşenleri güven bölgelerine ayır, bağlantılardaki sınır geçişlerini çıkar ve her geçişin kontrol kapsamını raporla.
esleme: ai-saldiri-18
timeout: 45
---

::: anlat Yerel çalışmak tek başına güven sınırı oluşturmaz

| Gerçek araç / model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| STRIDE / MITRE ATLAS gibi çerçevelerle uygulama yazarı akışları ve tehditleri modeller; diyagram uygulamanın envanterinden çıkarılır | İlk 3 görev bileşen envanteri, yönlü akış geçişleri ve kontrol kapsam matrisi | Dağıtık mikroservis ağ güvenliği, mTLS tünelleme veya kernel düzeyinde IPC izolasyon kanıtı değildir |
| Ollama yerel LLM ve araç çağırma motoru canlı model->araç yürütme akışları üretir | Gerçek deney model, geçit ve araç arasındaki canlı çalışma zamanı sınır geçişlerini denetler | Çok ajanlı karmaşık sistem mimarilerinde sıfır güven (zero-trust) garantisi veya zararlı kod bağışıklığı kanıtı değildir |

> [!NOT]
> `veri/mimari.json` dosyası sentetik bileşen, bağlantı ve güvenlik kontrolü kayıtlarını içerir; canlı telemetri veya gerçek servis yapılandırması değildir. İlk 3 görev bu yerel fixture verisini okur. Her Run/Check işleminde `hazirla("ai-savunma-01")` geçici kopya oluşturur; kalıcı değişiklik saklanmaz. Kodunuzu veya verinizi editörde inceleyebilirsiniz. Gizli değerlendirme testleri ayrı doğrulamalar koşturur. Gerçek deney adımı kurulu Ollama ve yerel modeli doğrudan çağırır; yeni paket veya model indirilmez.

Yerel bir yapay zekâ kurulumunda en sık düşülen yanılgı, tüm bileşenlerin aynı makinede (`localhost`) çalışmasının doğal bir güvenlik kalkanı sağladığı varsayımıdır. Geliştiriciler FastAPI servisinin, yerel Ollama motorunun, yerel SQLite/Chroma veritabanının ve işletim sisteminde çalışan yardımcı komut araçlarının "güvenli bir iç ağda" olduğunu varsayar. Ancak çağdaş siber güvenlik mimarisinde temel kural şudur: "Fiziksel veya mantıksal yakınlık bir güven sınırı oluşturmaz" (Sıfır Güven / Zero Trust prensibi). Bellek adres alanları izole edilmiş olsa bile, süreçler arasındaki her veri ve komut transferi potansiyel bir saldırı yüzeyidir. Bir kullanıcının web arayüzünden gönderdiği girdi ile bir arka plan aracının dosya sistemine yazdığı veri aynı güven düzeyine sahip olamaz.

Güven bölgesi (Trust Zone), aynı doğrulama, kimlik denetimi ve yetki varsayımlarını paylaşan bileşenlerin oluşturduğu mantıksal sınırdır. Bu derste savunma mimarisini beş temel bölgeye ayırıyoruz:
1. `dis` Bölgesi: Sistemin doğrudan denetimi altında olmayan, saldırgan kontrolüne açık veya filtrelenmemiş tüm dış varlıklar (`kullanici`, `istemci`, `ag`). Dış dünyadan gelen her bayt potansiyel olarak zehirlidir.
2. `uygulama` Bölgesi: Dış istekleri karşılayan, kimlik doğrulayan, istekleri yönlendiren ve iş mantığını koşturan API geçidi katmanı (`api`).
3. `model` Bölgesi: Olasılıksal token tamamlama yapan, deterministik olmayan ve prompt enjeksiyonuna (jailbreak, indirect injection) açık dil modeli süreçleri (`model`). Model girdiyi "anlamaz", sadece istatistiksel ağırlıklarla dönüştürür; bu nedenle modelin kendisi asla güvenilir bir karar verici kabul edilemez.
4. `arac` Bölgesi: İşletim sistemiyle, dosya sistemiyle, dış komutlarla veya harici API'lerle etkileşime girerek yan etki (side-effect) üreten yürütücüler (`arac`). Modelin bu araçları tetiklemesi kritik bir yetki sınırıdır.
5. `veri` Bölgesi: Kalıcı durum saklayan ilişkisel veritabanları, vektör indeksleri, yapılandırma dosyaları ve model ağırlıkları (`depo`).

Bir mimaride güvenlik zafiyetleri bileşenlerin kendisinden çok, bileşenler arasındaki **yönlü bağlantılarda (flows)** ortaya çıkar. Her akış bir `(kaynak, hedef, kanal)` üçlüsü olarak tanımlanır. Eğer kaynağın güven bölgesi ile hedefin güven bölgesi birbirinden farklıysa (`bolgeler[kaynak] != bolgeler[hedef]`), bu bağlantı kesin olarak bir **Güven Sınırı Geçişi (Trust Boundary Crossing)** barındırır. Örneğin:
- `kullanici -> api` (http): `dis` bölgesinden `uygulama` bölgesine geçiştir; kimlik doğrulama, şema denetimi ve boyut sınırlaması zorunludur.
- `model -> arac` (ipc): `model` bölgesinden `arac` bölgesine geçiştir; model çıktısının güvenilmezliği nedeniyle bu geçiş en tehlikeli saldırı vektörüdür.

Saldırganlar yerel LLM mimarilerinde başlıca şu zafiyetleri istismar eder:
- **`confused deputy` ve Dolaylı Enjeksiyon:** Dış bir kaynaktan (`dis`) gelen kötü niyetli komut modeli (`model`) manipüle eder. Model, kendi yetkilerini kullanarak araç katmanında (`arac`) saldırganın istediği yıkıcı bir eylemi (dosya silme, dış sunucuya veri sızdırma) tetikler. Model yetkilidir fakat niyeti saldırgan tarafından gasp edilmiştir.
- **Bölge Atlama (Zone Hopping):** Geliştiricinin "yerel IPC güvenlidir" zannıyla API ile veritabanı arasına şema veya yetki kontrolü koymaması sonucu, araya sızan bir model çıktısının doğrudan veri deposunu kirletmesi.
- **Parametre ve Şema Manipülasyonu:** Modelin araç çağrısı argümanlarında tip kontrolü yapılmadığında oluşan komut enjeksiyonları veya yol aşma (path traversal) açıkları.

Savunmanın kırılma nedenleri ve geliştiricilerin sık yaptığı hatalar:
- **Yönü Yok Saymak:** Akışın yönünü ihmal etmek; örneğin `api -> model` çağrısı ile `model -> api` yanıtını aynı kabul etmek. Yanıt kanalı, modelin ürettiği kontrolsüz yükleri taşır.
- **Aynı Bölge Akışlarına Kontrol Atamak:** Aynı güven bölgesindeki bileşenler (örneğin iki yardımcı API servisi) arasındaki akışları sınır geçişi sanmak, güvenlik ekiplerinin kaynaklarını tüketir ve gerçek sınır geçişlerinin gözden kaçmasına yol açar.
- **Kontrolsüz Geçişleri Toleransla Karşılamak:** `kontrolsuz=0`, raporlanan her geçişe en az bir kontrol atandığını gösterir. Örneğin bir araç çağrısında boyut sınırı bulunabilir ama çağrının yetkisi denetlenmeyebilir. Kontrolün uygunluğu ve uygulamada çalışması ayrıca sınanır.
- **Veri Yapılarını Yerinde Değiştirmek:** Girdi listelerini veya sözlüklerini doğrudan mutasyona uğratarak test sözleşmelerini ve saf fonksiyon ilkelerini ihlal etmek.
:::

::: tahmin Bileşen türü güven bölgesini belirler
Aynı sözlükteki üç türün bölge eşlemesini izle. Üç çıktı satırını yaz:

```python
sinir = {"kullanici": "dis", "model": "model", "arac": "arac"}
print(sinir["kullanici"])
print(sinir["model"] == sinir["arac"])
print(len(set(sinir.values())))
```

???

```cikti
dis
False
3
```

Model ve araç birlikte çağrılsa bile farklı bölgelerdedir; aralarındaki çağrı ayrıca denetlenmelidir.
:::

::: gorev 1 · Bileşen envanterini güven bölgeleriyle normalize et
`guven_bolgesi_envanteri(bilesenler)` işlevini yaz. Girdi liste olmalı; her bileşen tam olarak `id`, `tur` alanlarını taşımalıdır. Kimlik, küçük harfle başlayan ve yalnız küçük ASCII harf, rakam veya tire içeren 1–40 karakterli benzersiz bir string olmalıdır. Tür yalnız `kullanici`, `istemci`, `api`, `model`, `arac`, `depo` veya `ag` olabilir. Geçersiz veride `ValueError` yükselt.

Bölgeleri şöyle ata: `kullanici`, `istemci`, `ag` → `dis`; `api` → `uygulama`; `model` → `model`; `arac` → `arac`; `depo` → `veri`.

Her bileşen için `{"id":ID,"tur":TUR,"sinir":BOLGE}` döndür. Listeyi kimliğe göre artan sırala, boş liste için boş liste döndür ve girdiyi değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-01")
```

```starter
from ai_savunma_veri import json_yukle

def guven_bolgesi_envanteri(bilesenler):
    # KUSURLU BAŞLANGIÇ KODU: tüm bileşenleri ayrım gözetmeksizin uygulama bölgesine atar ve sıralama yapmaz.
    return [{"id": b["id"], "tur": b["tur"], "sinir": "uygulama"} for b in bilesenler]

v = json_yukle("veri/mimari.json")["bilesenler"]
print("Normalize envanter örneği:", guven_bolgesi_envanteri(v))
```

```test
import copy
BILESENLER = [
    {"id": "vektor", "tur": "depo"},
    {"id": "kullanici", "tur": "kullanici"},
    {"id": "llm", "tur": "model"},
    {"id": "dosya-araci", "tur": "arac"},
    {"id": "api", "tur": "api"},
    {"id": "internet", "tur": "ag"},
    {"id": "tarayici", "tur": "istemci"},
]
BEKLENEN = [
    {"id": "api", "tur": "api", "sinir": "uygulama"},
    {"id": "dosya-araci", "tur": "arac", "sinir": "arac"},
    {"id": "internet", "tur": "ag", "sinir": "dis"},
    {"id": "kullanici", "tur": "kullanici", "sinir": "dis"},
    {"id": "llm", "tur": "model", "sinir": "model"},
    {"id": "tarayici", "tur": "istemci", "sinir": "dis"},
    {"id": "vektor", "tur": "depo", "sinir": "veri"},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(BILESENLER)
        if fn(BILESENLER) != BEKLENEN or BILESENLER != once or fn(list(reversed(BILESENLER))) != BEKLENEN:
            return False
        if fn([]) != []:
            return False
        if fn([{"id": "a" * 40, "tur": "api"}])[0]["sinir"] != "uygulama":
            return False
        for kayitlar in [
            None, {}, [None], [{"id": "api", "tur": "api", "ek": 1}],
            [{"id": "", "tur": "api"}], [{"id": "1api", "tur": "api"}],
            [{"id": "Api", "tur": "api"}], [{"id": "a" * 41, "tur": "api"}],
            [{"id": None, "tur": "api"}], [{"id": True, "tur": "api"}],
            [{"id": "api", "tur": "servis"}], [{"id": "api", "tur": None}], [{"id": "api", "tur": []}],
            [{"id": "api", "tur": "api"}, {"id": "api", "tur": "model"}],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(guven_bolgesi_envanteri), "tür-bölge eşlemesi, kimlik sözleşmesi ve deterministik sıra korunmalı")
def m_bolge(bilesenler):
    sonuc = guven_bolgesi_envanteri(bilesenler)
    for x in sonuc:
        if x["tur"] == "arac":
            x["sinir"] = "model"
    return sonuc
def m_sira(bilesenler):
    return list(reversed(guven_bolgesi_envanteri(bilesenler)))
def m_tur(bilesenler):
    return guven_bolgesi_envanteri([dict(x, tur="api") for x in bilesenler])
for ad, mutant in [("aracı model bölgesine koyan", m_bolge), ("kimlik sırasını bozan", m_sira), ("bütün türleri API yapan", m_tur)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def guven_bolgesi_envanteri(bilesenler):
    import re
    esleme = {
        "kullanici": "dis", "istemci": "dis", "ag": "dis",
        "api": "uygulama", "model": "model", "arac": "arac", "depo": "veri",
    }
    if not isinstance(bilesenler, list):
        raise ValueError("bileşen listesi geçersiz")
    sonuc = []
    kimlikler = set()
    for bilesen in bilesenler:
        if not isinstance(bilesen, dict) or set(bilesen) != {"id", "tur"}:
            raise ValueError("bileşen şeması geçersiz")
        kimlik = bilesen["id"]
        tur = bilesen["tur"]
        if not isinstance(kimlik, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", kimlik) or kimlik in kimlikler:
            raise ValueError("bileşen kimliği geçersiz")
        if not isinstance(tur, str) or tur not in esleme:
            raise ValueError("bileşen türü geçersiz")
        kimlikler.add(kimlik)
        sonuc.append({"id": kimlik, "tur": tur, "sinir": esleme[tur]})
    return sorted(sonuc, key=lambda x: x["id"])
```

```hint
Türden bölgeye sabit bir sözlük kullan. Kimlikleri kümede izle, her çıktıyı yeni bir sözlük olarak oluştur ve en son kimliğe göre sırala.
```
:::

::: anlat Saldırı yüzeyi bağlantılarda görünür hâle gelir
Envanterdeki iki bileşen arasındaki bağlantı, veri veya talimat akışını temsil eder. Kaynak ve hedef aynı bölgedeyse bu fixture'da sınır geçişi yoktur; bölgeler farklıysa geçiş vardır. Örneğin kullanıcıdan API'ye istek, modelden araca çağrı ve API'den depoya sorgu ayrı güven kararları gerektirir.

Bağlantı yönü önemlidir. `api → model` ile `model → api` aynı kayıt değildir. Kanal da kimlikle birlikte korunur; aynı iki bileşen arasındaki HTTP ve IPC akışları farklı denetim noktaları olabilir.
:::

::: gorev 2 · Yönlü bağlantılardan güven sınırı geçişlerini çıkar
`sinir_gecisleri_raporu(bilesenler, baglantilar)` işlevini yaz. `bilesenler`, ilk görevin normalize edilmiş çıktısı biçiminde bir liste olmalı; her kayıt tam olarak `id`, `tur`, `sinir` alanlarını taşımalı ve ilk görevdeki bütün kuralları sağlamalıdır. Her bağlantı tam olarak `kaynak`, `hedef`, `kanal` alanlarını taşısın. Kaynak ve hedef kayıtlı, birbirinden farklı kimlikler; kanal yalnız `http`, `ipc`, `dosya`, `sql` veya `vektor` olmalıdır. Aynı `(kaynak, hedef, kanal)` üçlüsü yinelenemez. Geçersiz veride `ValueError` yükselt.

Her bağlantı için aynı üç alana ek olarak `sinir_gecisi` boolean alanı döndür; kaynak ve hedef bölgeleri farklıysa true olsun. Raporu `(kaynak, hedef, kanal)` anahtarıyla artan sırala. Girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-01")
```

```starter
from ai_savunma_veri import json_yukle

def sinir_gecisleri_raporu(bilesenler, baglantilar):
    # KUSURLU BAŞLANGIÇ KODU: bölge kontrolü yapmadan tüm bağlantıları sınır geçişi yok (False) olarak işaretler.
    return [{"kaynak": a["kaynak"], "hedef": a["hedef"], "kanal": a["kanal"], "sinir_gecisi": False} for a in baglantilar]

m = json_yukle("veri/mimari.json")
print("Sınır geçişleri örneği:", sinir_gecisleri_raporu(m["bilesenler"], m["baglantilar"]))
```

```test
import copy
B = [
    {"id": "api", "tur": "api", "sinir": "uygulama"},
    {"id": "kullanici", "tur": "kullanici", "sinir": "dis"},
    {"id": "llm", "tur": "model", "sinir": "model"},
    {"id": "yardimci", "tur": "api", "sinir": "uygulama"},
]
A = [
    {"kaynak": "llm", "hedef": "api", "kanal": "ipc"},
    {"kaynak": "kullanici", "hedef": "api", "kanal": "http"},
    {"kaynak": "api", "hedef": "yardimci", "kanal": "ipc"},
]
BEKLENEN = [
    {"kaynak": "api", "hedef": "yardimci", "kanal": "ipc", "sinir_gecisi": False},
    {"kaynak": "kullanici", "hedef": "api", "kanal": "http", "sinir_gecisi": True},
    {"kaynak": "llm", "hedef": "api", "kanal": "ipc", "sinir_gecisi": True},
]
def sozlesme(fn):
    try:
        once_b, once_a = copy.deepcopy(B), copy.deepcopy(A)
        if fn(B, A) != BEKLENEN or B != once_b or A != once_a or fn(B, list(reversed(A))) != BEKLENEN:
            return False
        if fn(B, []) != []:
            return False
        yonlu = fn(B, [{"kaynak": "api", "hedef": "kullanici", "kanal": "http"}])
        if yonlu[0]["kaynak"] != "api" or yonlu[0]["hedef"] != "kullanici":
            return False
        for bilesenler, baglantilar in [
            (None, []), (B, None), ([None], []),
            ([dict(B[0], ek=1)], []), ([dict(B[0], sinir="dis")], []),
            ([dict(B[0], id=123)], []), ([dict(B[0], tur="diger")], []), ([dict(B[0], tur=[])], []), (B, [dict(A[0], kaynak=[])]),
            ([dict(B[0], id="a" * 41)], []), ([B[0], B[0]], []),
            (B, [None]), (B, [dict(A[0], ek=1)]),
            (B, [{"kaynak": "yok", "hedef": "api", "kanal": "http"}]),
            (B, [{"kaynak": "api", "hedef": "yok", "kanal": "http"}]),
            (B, [{"kaynak": "api", "hedef": "api", "kanal": "http"}]),
            (B, [{"kaynak": "api", "hedef": "llm", "kanal": "tcp"}]),
            (B, [{"kaynak": None, "hedef": "api", "kanal": "http"}]),
            (B, [A[0], A[0]]),
        ]:
            try:
                fn(bilesenler, baglantilar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(sinir_gecisleri_raporu), "bağlantı yönü, bölge karşılaştırması ve kayıtlı uçlar korunmalı")
def m_gecis(bilesenler, baglantilar):
    sonuc = sinir_gecisleri_raporu(bilesenler, baglantilar)
    for x in sonuc:
        x["sinir_gecisi"] = not x["sinir_gecisi"]
    return sonuc
def m_yon(bilesenler, baglantilar):
    ters = [dict(x, kaynak=x["hedef"], hedef=x["kaynak"]) for x in baglantilar]
    return sinir_gecisleri_raporu(bilesenler, ters)
def m_kanal(bilesenler, baglantilar):
    sonuc = sinir_gecisleri_raporu(bilesenler, baglantilar)
    for x in sonuc:
        x["kanal"] = "http"
    return sonuc
for ad, mutant in [("sınır geçişini tersleyen", m_gecis), ("bağlantı yönünü değiştiren", m_yon), ("kanal kanıtını silen", m_kanal)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def sinir_gecisleri_raporu(bilesenler, baglantilar):
    import re
    esleme = {
        "kullanici": "dis", "istemci": "dis", "ag": "dis",
        "api": "uygulama", "model": "model", "arac": "arac", "depo": "veri",
    }
    if not isinstance(bilesenler, list):
        raise ValueError("envanter geçersiz")
    if not isinstance(baglantilar, list):
        raise ValueError("bağlantı listesi geçersiz")
    bolgeler = {}
    for b in bilesenler:
        if not isinstance(b, dict):
            raise ValueError("bileşen kaydı geçersiz")
        if set(b) != {"id", "tur", "sinir"}:
            raise ValueError("bileşen şeması geçersiz")
        if not isinstance(b["id"], str):
            raise ValueError("bileşen kimliği geçersiz")
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", b["id"]):
            raise ValueError("bileşen kimliği geçersiz")
        if b["id"] in bolgeler:
            raise ValueError("bileşen kimliği yinelenemez")
        if not isinstance(b["tur"], str) or b["tur"] not in esleme:
            raise ValueError("bileşen türü geçersiz")
        if b["sinir"] != esleme[b["tur"]]:
            raise ValueError("bileşen bölgesi geçersiz")
        bolgeler[b["id"]] = b["sinir"]
    sonuc = []
    akislar = set()
    for a in baglantilar:
        if not isinstance(a, dict):
            raise ValueError("bağlantı kaydı geçersiz")
        if set(a) != {"kaynak", "hedef", "kanal"}:
            raise ValueError("bağlantı şeması geçersiz")
        kaynak, hedef, kanal = a["kaynak"], a["hedef"], a["kanal"]
        if not all(isinstance(x, str) for x in (kaynak, hedef, kanal)):
            raise ValueError("bağlantı alanları metin olmalı")
        anahtar = (kaynak, hedef, kanal)
        if kaynak not in bolgeler:
            raise ValueError("kaynak geçersiz")
        if hedef not in bolgeler:
            raise ValueError("hedef geçersiz")
        if kaynak == hedef:
            raise ValueError("bağlantı kendine olamaz")
        if kanal not in ("http", "ipc", "dosya", "sql", "vektor"):
            raise ValueError("kanal geçersiz")
        if anahtar in akislar:
            raise ValueError("bağlantı yinelenemez")
        akislar.add(anahtar)
        sonuc.append({"kaynak": kaynak, "hedef": hedef, "kanal": kanal, "sinir_gecisi": bolgeler[kaynak] != bolgeler[hedef]})
    return sorted(sonuc, key=lambda x: (x["kaynak"], x["hedef"], x["kanal"]))
```

```hint
Önce kimlikten bölgeye bir sözlük kur. Her bağlantının iki ucunu bu sözlükte ara; `bolgeler[kaynak] != bolgeler[hedef]` ile geçişi hesapla.
```
:::

::: anlat Her sınır geçişi açık bir kontrolle eşleştirilmeli
Kontrol envanteri, sınır geçişini otomatik olarak güvenli yapmaz; yalnız hangi korumanın hangi akışa atandığını gösterir. Kimlik doğrulama, yetki, şema doğrulama, boyut sınırı ve insan onayı farklı riskleri karşılar. Bu derste kontrol adlarının etkisini ölçmüyor, eksik eşlemeyi görünür kılıyoruz.

Rapor yalnız gerçek sınır geçişlerini içerir. Aynı bölgedeki akışa sınır kontrolü eklemek bu fixture'da geçersizdir. Kontrolsüz geçiş sayısı sıfır olana kadar mimari inceleme tamamlanmış sayılmamalıdır; sonraki derslerde her kontrolün gerçekten çalıştığını ayrıca test edeceğiz.
:::

::: gorev 3 · Sınır geçişlerinin kontrol kapsamını hesapla
`kontrol_kapsam_raporu(bilesenler, baglantilar, kontroller)` işlevini yaz. Bileşenler ve bağlantılar ikinci görevdeki bütün kuralları sağlasın. `kontroller` liste olmalı; her kayıt tam olarak `kaynak`, `hedef`, `kanal`, `ad` alanlarını taşımalıdır. Kontrol yalnız mevcut bir sınır geçişine ait olabilir. Ad yalnız `kimlik`, `yetki`, `sema`, `boyut` veya `insan_onayi` olabilir; aynı akış ve ada sahip kayıt yinelenemez. Geçersiz veride `ValueError` yükselt.

Dönüş:

```text
{"gecisler":[{"kaynak":K,"hedef":H,"kanal":C,"kontroller":[AD,...]},...],
 "kontrolsuz":N}
```

Yalnız sınır geçişlerini raporla. Geçişleri `(kaynak, hedef, kanal)` ile, kontrol adlarını alfabetik artan sırala. Kontrol atanmayan geçiş boş liste taşır. `kontrolsuz`, boş kontrol listesi olan geçiş sayısıdır. Girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-01")
```

```starter
from ai_savunma_veri import json_yukle

def kontrol_kapsam_raporu(bilesenler, baglantilar, kontroller):
    # KUSURLU BAŞLANGIÇ KODU: kontrolleri geçişlerle eşleştirmeden sabit sıfır kontrolsüz geçiş raporlar.
    return {"gecisler": [{"kaynak": a["kaynak"], "hedef": a["hedef"], "kanal": a["kanal"], "kontroller": []} for a in baglantilar], "kontrolsuz": 0}

m = json_yukle("veri/mimari.json")
print("Kontrol kapsam örneği:", kontrol_kapsam_raporu(m["bilesenler"], m["baglantilar"], m["kontroller"]))
```

```test
import copy
B = [
    {"id": "api", "tur": "api", "sinir": "uygulama"},
    {"id": "kullanici", "tur": "kullanici", "sinir": "dis"},
    {"id": "llm", "tur": "model", "sinir": "model"},
    {"id": "yardimci", "tur": "api", "sinir": "uygulama"},
]
A = [
    {"kaynak": "kullanici", "hedef": "api", "kanal": "http"},
    {"kaynak": "api", "hedef": "yardimci", "kanal": "ipc"},
    {"kaynak": "api", "hedef": "llm", "kanal": "ipc"},
]
K = [
    {"kaynak": "api", "hedef": "llm", "kanal": "ipc", "ad": "sema"},
    {"kaynak": "kullanici", "hedef": "api", "kanal": "http", "ad": "boyut"},
    {"kaynak": "kullanici", "hedef": "api", "kanal": "http", "ad": "kimlik"},
]
BEKLENEN = {"gecisler": [
    {"kaynak": "api", "hedef": "llm", "kanal": "ipc", "kontroller": ["sema"]},
    {"kaynak": "kullanici", "hedef": "api", "kanal": "http", "kontroller": ["boyut", "kimlik"]},
], "kontrolsuz": 0}
def sozlesme(fn):
    try:
        once = copy.deepcopy((B, A, K))
        if fn(B, A, K) != BEKLENEN or (B, A, K) != once:
            return False
        ters = fn(B, list(reversed(A)), list(reversed(K)))
        if ters != BEKLENEN:
            return False
        bos = fn(B, A, [])
        if bos["kontrolsuz"] != 2 or any(x["kontroller"] for x in bos["gecisler"]):
            return False
        tek = fn(B, A, K[:1])
        if tek["kontrolsuz"] != 1 or tek["gecisler"][1]["kontroller"] != []:
            return False
        for bilesenler, baglantilar, kontroller in [
            (B, A, None), (B, A, [None]), (B, A, [dict(K[0], ek=1)]),
            (B, A, [dict(K[0], ad="fiziksel")]), (B, A, [dict(K[0], ad=None)]),
            (B, A, [dict(K[0], hedef="yok")]), (B, A, [dict(K[0], hedef=[])]),
            (B, A, [{"kaynak": "api", "hedef": "yardimci", "kanal": "ipc", "ad": "kimlik"}]),
            (B, A, [K[0], K[0]]), (None, A, K), (B, None, K),
            ([dict(B[0], sinir="dis")], [], []), ([None], [], []), ([dict(B[0], ek=1)], [], []), ([{"id": "api", "tur": "api"}], [], []),
            ([dict(B[0], id=123)], [], []), ([B[0], B[0]], [], []), ([dict(B[0], tur="diger")], [], []), ([dict(B[0], tur=[])], [], []), (B, [dict(A[0], kaynak=[])], []),
            ([dict(B[0], id="a" * 41)], [], []),
            (B, [None], []), (B, [dict(A[0], ek=1)], []), (B, [{"kaynak": "api", "hedef": "llm"}], []),
            (B, [{"kaynak": "yok", "hedef": "api", "kanal": "http"}], []),
            (B, [{"kaynak": "api", "hedef": "yok", "kanal": "http"}], []),
            (B, [{"kaynak": "api", "hedef": "llm", "kanal": "tcp"}], []),
            (B, [{"kaynak": "api", "hedef": "api", "kanal": "http"}], []),
        ]:
            try:
                fn(bilesenler, baglantilar, kontroller)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(kontrol_kapsam_raporu), "yalnız gerçek geçişlere kontrol atanmalı ve kontrolsüz sayısı korunmalı")
def m_ayni(bilesenler, baglantilar, kontroller):
    ek = baglantilar + [{"kaynak": "yardimci", "hedef": "api", "kanal": "http"}]
    return kontrol_kapsam_raporu(bilesenler, ek, kontroller)
def m_sayac(bilesenler, baglantilar, kontroller):
    sonuc = kontrol_kapsam_raporu(bilesenler, baglantilar, kontroller)
    sonuc["kontrolsuz"] += 1
    return sonuc
def m_kontrol(bilesenler, baglantilar, kontroller):
    sonuc = kontrol_kapsam_raporu(bilesenler, baglantilar, kontroller)
    for x in sonuc["gecisler"]:
        x["kontroller"] = []
    sonuc["kontrolsuz"] = len(sonuc["gecisler"])
    return sonuc
for ad, mutant in [("aynı bölge akışını geçiş sanan", m_ayni), ("kontrolsüz sayacını bozan", m_sayac), ("atanan kontrolleri kaybeden", m_kontrol)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
# İç bölgede kalan yinelenen akış da geçersizdir; rapordan düşmesi tekilliği kaldırmaz.
raises(ValueError, lambda: kontrol_kapsam_raporu([{"id":"api","tur":"api","sinir":"uygulama"},{"id":"yardimci","tur":"api","sinir":"uygulama"}], [{"kaynak":"api","hedef":"yardimci","kanal":"ipc"}]*2, []), msg="aynı bölge içindeki akış tekilliği")
```

```solution
def kontrol_kapsam_raporu(bilesenler, baglantilar, kontroller):
    import re
    esleme = {
        "kullanici": "dis", "istemci": "dis", "ag": "dis",
        "api": "uygulama", "model": "model", "arac": "arac", "depo": "veri",
    }
    if not isinstance(bilesenler, list):
        raise ValueError("envanter geçersiz")
    if not isinstance(baglantilar, list):
        raise ValueError("bağlantı listesi geçersiz")
    if not isinstance(kontroller, list):
        raise ValueError("kontrol listesi geçersiz")
    bolgeler = {}
    for b in bilesenler:
        if not isinstance(b, dict):
            raise ValueError("bileşen kaydı geçersiz")
        if set(b) != {"id", "tur", "sinir"}:
            raise ValueError("bileşen şeması geçersiz")
        if not isinstance(b["id"], str):
            raise ValueError("bileşen kimliği geçersiz")
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", b["id"]):
            raise ValueError("bileşen kimliği geçersiz")
        if b["id"] in bolgeler:
            raise ValueError("bileşen kimliği yinelenemez")
        if not isinstance(b["tur"], str) or b["tur"] not in esleme:
            raise ValueError("bileşen türü geçersiz")
        if b["sinir"] != esleme[b["tur"]]:
            raise ValueError("bileşen bölgesi geçersiz")
        bolgeler[b["id"]] = b["sinir"]
    gecisler = {}
    akislar = set()
    for a in baglantilar:
        if not isinstance(a, dict):
            raise ValueError("bağlantı kaydı geçersiz")
        if set(a) != {"kaynak", "hedef", "kanal"}:
            raise ValueError("bağlantı şeması geçersiz")
        kaynak, hedef, kanal = a["kaynak"], a["hedef"], a["kanal"]
        if not all(isinstance(x, str) for x in (kaynak, hedef, kanal)):
            raise ValueError("bağlantı alanları metin olmalı")
        anahtar = (kaynak, hedef, kanal)
        if kaynak not in bolgeler:
            raise ValueError("kaynak geçersiz")
        if hedef not in bolgeler:
            raise ValueError("hedef geçersiz")
        if kaynak == hedef:
            raise ValueError("bağlantı kendine olamaz")
        if kanal not in ("http", "ipc", "dosya", "sql", "vektor"):
            raise ValueError("kanal geçersiz")
        if anahtar in akislar:
            raise ValueError("bağlantı yinelenemez")
        akislar.add(anahtar)
        if bolgeler[kaynak] != bolgeler[hedef]:
            gecisler[anahtar] = []
    atanan = set()
    for k in kontroller:
        if not isinstance(k, dict):
            raise ValueError("kontrol kaydı geçersiz")
        if set(k) != {"kaynak", "hedef", "kanal", "ad"}:
            raise ValueError("kontrol şeması geçersiz")
        anahtar = (k["kaynak"], k["hedef"], k["kanal"]) if all(isinstance(k[x], str) for x in ("kaynak", "hedef", "kanal")) else None
        if anahtar not in gecisler:
            raise ValueError("kontrol geçişi geçersiz")
        if k["ad"] not in ("kimlik", "yetki", "sema", "boyut", "insan_onayi"):
            raise ValueError("kontrol adı geçersiz")
        tekil = (anahtar, k["ad"])
        if tekil in atanan:
            raise ValueError("kontrol yinelenemez")
        atanan.add(tekil)
        gecisler[anahtar].append(k["ad"])
    rapor = []
    for kaynak, hedef, kanal in sorted(gecisler):
        rapor.append({"kaynak": kaynak, "hedef": hedef, "kanal": kanal, "kontroller": sorted(gecisler[(kaynak, hedef, kanal)])})
    return {"gecisler": rapor, "kontrolsuz": sum(1 for x in rapor if not x["kontroller"])}
```

```hint
Önce gerçek geçişleri anahtarları boş kontrol listeleri olan bir sözlükte topla. Kontrolleri bu anahtarlara ekle; son raporu ve kontrolsüz sayacını bu sözlükten üret.
```
:::

::: anlat Güven sınırı soyut değil: gerçek etkileşimde oluşur
Şimdiye kadarki görevler mimariyi sentetik fixture üstünde modelledi. Ama bir güven sınırı geçişi gerçekten *olur*: yerel modele bir araç verildiğinde, model çıktısı bir araç çağrısı üretirse `model` bölgesinden `arac` bölgesine canlı bir geçiş gerçekleşir — ve model çıktısı güvenilmezdir, bu geçiş mutlaka denetlenmelidir. Son görevde senin sınır raporun, **gerçek bir ajan etkileşiminden** çıkarılan akışlara uygulanır: gerçek model aritmetik araçlarını çağırır, deney gerçekleşen akışları (kullanıcı→geçit, geçit→model, model→araç, araç→model) toplar ve senin raporun bu akışlardaki güven sınırı geçişlerini doğru işaretler mi ölçer.
:::

::: gorev Gerçek deney · Canlı ajan etkileşiminde güven sınırı geçişleri
`canli_gecis_raporu(bilesenler, baglantilar)` işlevini yaz — kuralları ve çıktısı 2. görevdeki `sinir_gecisleri_raporu` ile **aynıdır**: `bilesenler` normalize envanter (tam `id`, `tur`, `sinir`; 1. görev kuralları), `baglantilar` her biri tam `kaynak`, `hedef` (kayıtlı, farklı kimlikler), `kanal` (`http`/`ipc`/`dosya`/`sql`/`vektor`) olan, `(kaynak, hedef, kanal)` üçlüsü yinelenmeyen liste. Geçersiz veride `ValueError`. Her bağlantı için `sinir_gecisi` (kaynak ve hedef bölgeleri farklıysa True) ekleyip `(kaynak, hedef, kanal)` ile sıralı döndür.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def canli_gecis_raporu(bilesenler, baglantilar):
    # KUSURLU BAŞLANGIÇ KODU: bölgeleri karşılaştırmadan tüm canlı bağlantıları sınır geçişi yok (False) sayar.
    return [{"kaynak": a["kaynak"], "hedef": a["hedef"], "kanal": a["kanal"], "sinir_gecisi": False} for a in baglantilar]

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_01 as deney
    deney.goster(canli_gecis_raporu)
```

```test
import ast
import ai_lab
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
sorun = ai_lab.kod_denetimi(src, ("referans", "referans_rapor", "getattr"))
kontrol(not sorun, "laboratuvar yamalanmamalı, referans kullanılmamalı " + ", ".join(sorun))
def ast_denetle(kaynak):
    try:
        agac = ast.parse(kaynak)
    except Exception:
        return False
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.ImportFrom):
            if any(a.name == "*" for a in dugum.names):
                return False
            if dugum.module and any(x in dugum.module for x in ("referans", "ai_gercek")):
                return False
        if isinstance(dugum, ast.Import):
            if any(any(x in a.name for x in ("referans", "ai_gercek")) for a in dugum.names):
                return False
        if isinstance(dugum, ast.Name) and "referans" in dugum.id.lower():
            return False
        if isinstance(dugum, ast.Attribute) and "referans" in dugum.attr.lower():
            return False
        if isinstance(dugum, ast.Call):
            if isinstance(dugum.func, ast.Name) and dugum.func.id in ("getattr", "eval", "exec"):
                return False
    return True
kontrol(ast_denetle(src), "kod referans çözüme doğrudan veya dolaylı erişmemeli")
fn = need("canli_gecis_raporu")
from sandbox import ai_gercek_ai_savunma_01 as D
B = [{"id": "gecit", "tur": "api", "sinir": "uygulama"}, {"id": "kullanici", "tur": "kullanici", "sinir": "dis"},
     {"id": "model", "tur": "model", "sinir": "model"}, {"id": "topla", "tur": "arac", "sinir": "arac"}]
A = [{"kaynak": "model", "hedef": "topla", "kanal": "ipc"}, {"kaynak": "kullanici", "hedef": "gecit", "kanal": "http"},
     {"kaynak": "gecit", "hedef": "model", "kanal": "ipc"}]
def sozlesme(f):
    try:
        if f([dict(b) for b in B], [dict(a) for a in A]) != D.referans_rapor(B, A):
            return False
        if f(B, []) != [] or f([dict(B[0], id="a" * 40)] + B[1:], []) != []:
            return False
        for bil, bag in [(None, A), (B, None), ([None], []), ([dict(B[0], ek=1)], []), ([dict(B[0], sinir="dis")], []),
                         ([dict(B[0], id=123)], []), ([dict(B[0], id="a" * 41)], []), ([dict(B[0], id="A")], []), ([B[0], B[0]], []), ([dict(B[0], tur="diger")], []), ([dict(B[0], tur=[])], []), (B, [dict(A[0], kaynak=[])]),
                         (B, [None]), (B, [dict(A[0], ek=1)]), (B, [{"kaynak": "yok", "hedef": "model", "kanal": "ipc"}]),
                         (B, [{"kaynak": "model", "hedef": "yok", "kanal": "ipc"}]), (B, [{"kaynak": 123, "hedef": "model", "kanal": "ipc"}]),
                         (B, [{"kaynak": "model", "hedef": "model", "kanal": "ipc"}]), (B, [{"kaynak": "model", "hedef": "topla", "kanal": "tcp"}]),
                         (B, [A[0], A[0]])]:
            try:
                f(bil, bag)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(fn), "canlı sınır raporu (bölge karşılaştırması, yön, kanal) doğru; geçersiz girdi reddedilmeli")
def m_gecis(bil, bag):
    r = D.referans_rapor(bil, bag)
    return [dict(x, sinir_gecisi=not x["sinir_gecisi"]) for x in r]
kontrol(not sozlesme(m_gecis), "hatalı çözüm reddedilmeli: sınır geçişini tersleyen")
r, oz = None, None
if all(sonuclar):
    try:
        r = D.deney(fn)
    except ai_lab.GercekLabYok as e:
        kontrol(False, f"GERÇEK MODEL YOK, deney yapılmadı: {e}")
        stop()
    kontrol(r["rapor"] == D.referans_rapor(r["bilesenler"], r["baglantilar"]), "canlı akışlarda sınır raporu bağımsız hesapla aynı")
    oz = D.ozet(r)
    kontrol(oz["model_arac_gecisi"] > 0, f"gerçek model model→araç güven sınırını geçti (araç çağırdı): {r['cagrilan_arac']}")
    kontrol(all(x["sinir_gecisi"] for x in r["rapor"] if x["kaynak"] == "model" and x["hedef"] in ("topla", "carp")),
            "model→araç akışları güven sınırı geçişi olarak işaretlendi")
yol = ai_lab.kanit_yaz("savunma-sinir", {"kaynak": "gercek", "kabul": all(sonuclar), "ders": "ai-savunma-01",
                                         "ortam": (r or {}).get("ortam"), "ozet": oz})
if oz:
    ok(True, f"BULGU ({r['ortam']['model']['ad']}): canlı etkileşimde {oz['sinir_gecisi']}/{oz['baglanti']} akış güven sınırı geçti; "
             f"gerçek model {oz['cagrilan_arac']} araçlarını çağırarak model→araç sınırını {oz['model_arac_gecisi']} kez geçti. "
             f"Güvenilmez model çıktısının aracı tetiklemesi gerçek bir sınır geçişidir; her biri kontrol ister.")
```

```solution
import re
import ai_lab

def canli_gecis_raporu(bilesenler, baglantilar):
    esleme = {"kullanici": "dis", "istemci": "dis", "ag": "dis",
              "api": "uygulama", "model": "model", "arac": "arac", "depo": "veri"}
    if not isinstance(bilesenler, list) or not isinstance(baglantilar, list):
        raise ValueError("envanter ve bağlantı listesi olmalı")
    bolge = {}
    for b in bilesenler:
        if not isinstance(b, dict) or set(b) != {"id", "tur", "sinir"} or not isinstance(b["id"], str) \
                or not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", b["id"]) or b["id"] in bolge \
                or not isinstance(b["tur"], str) or b["tur"] not in esleme or b["sinir"] != esleme[b["tur"]]:
            raise ValueError("bileşen geçersiz")
        bolge[b["id"]] = b["sinir"]
    sonuc, akislar = [], set()
    for a in baglantilar:
        if not isinstance(a, dict) or set(a) != {"kaynak", "hedef", "kanal"}:
            raise ValueError("bağlantı şeması geçersiz")
        kaynak, hedef, kanal = a["kaynak"], a["hedef"], a["kanal"]
        if not all(isinstance(x, str) for x in (kaynak, hedef, kanal)):
            raise ValueError("bağlantı alanları metin olmalı")
        anahtar = (kaynak, hedef, kanal)
        if kaynak not in bolge or hedef not in bolge:
            raise ValueError("uç kayıtlı değil")
        if kaynak == hedef:
            raise ValueError("bağlantı kendine olamaz")
        if kanal not in ("http", "ipc", "dosya", "sql", "vektor"):
            raise ValueError("kanal geçersiz")
        if anahtar in akislar:
            raise ValueError("bağlantı yinelenemez")
        akislar.add(anahtar)
        sonuc.append({"kaynak": kaynak, "hedef": hedef, "kanal": kanal, "sinir_gecisi": bolge[kaynak] != bolge[hedef]})
    return sorted(sonuc, key=lambda x: (x["kaynak"], x["hedef"], x["kanal"]))

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_01 as deney
    deney.goster(canli_gecis_raporu)
```

```hint
Bu işlev 2. görevdeki `sinir_gecisleri_raporu` ile aynıdır; tek fark, `baglantilar`'ın gerçek bir ajan etkileşiminden gelmesidir. Kimlikten bölgeye sözlük kur, her akışın iki ucunu karşılaştır; model→araç akışları farklı bölgeler olduğundan güven sınırı geçişi olarak işaretlenir.
```
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
Yerel sistemin bileşenlerini güven bölgelerine ayır; yönlü bağlantı her veri/otorite geçişini temsil eder. Aynı makinede bulunmak aynı güven alanında olmak değildir. Bir kaynak–hedef çiftinin kanalı da kimliğinin parçasıdır. Kontrol kapsam matrisi hangi geçişin hangi kontrolle izlendiğini gösterir, kontrolün gerçek yan etkisini tek başına kanıtlamaz. Canlı ajan deneyinde model önerisiyle yürütücü etkisini ayrı kaydet.

Önkoşul ve yol köprüsü: ai-saldiri-18 confused deputy.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| Localhost olmak bütün bileşenlere güven verir | Model, API ve araç farklı yetkiler taşır |

Dinleyiciye sor: Savunma güvenlik metriğini iyileştirirken meşru kullanıma ne kaybettirebilir? Ham çıktı ve ölçüm paydalarıyla cevapla.
:::


::: anlat Birincil kaynak ve deney sınırı
[OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/): Talimat/veri sınırı için risk referansı. Bileşen/güven bölgesi envanteri dersin yazdığı tehdit modelidir. Çalışan sürüm ve gerçek sonuç kanıtta kayıtlıdır.
:::
