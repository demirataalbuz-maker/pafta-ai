---
id: ai-saldiri-36
title: Red Team Metodolojisi I · Yasal Kapsam (RoE), Sistem Anatomisi ve Güven Sınırları
summary: AI red team ile klasik pentest farkını kur; yasal kapsam belgesini (RoE) ve üçüncü taraf API kısıtlarını denetle, 6 bileşenli hedef sistem anatomisiyle güven sınırı geçişlerini çıkar ve yerel modelde izinli keşif yürüt.
timeout: 60
esleme: ai-saldiri-37, ai-guvence-33, ai-savunma-01
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et
Bir AI sistemine tek bir saldırı istemi göndermeden önce iki temel soru yanıtlanır: **“Hangi hedefe, hangi sınırlar içinde dokunmaya yetkiliyim?”** ve **“Karşımdaki sistem yalnızca bir dil modeli mi, yoksa RAG, araç, bellek ve çıktı tüketicilerinden oluşan çok bileşenli bir mimari mi?”**

Bu derste ilk üç görevde çalışma klasörüne kopyalanan **sentetik örnek / fixture** dosyalarını (`kapsam/*.json`, `sistemler/*.json`) doğruluyor; son görevde ise RoE denetiminden geçen izinli keşif sorgularını **yerel Ollama modeline** göndererek gerçek model yanıtlarını çözümlüyoruz:

| Katman | Gerçek red team operasyonunda ne vardır? | Bu ders ne kullanır? | Ne söyleyemez? |
|---|---|---|---|
| **Yasal kapsam (RoE)** | Müşteriyle imzalanan yazılı sözleşme, IP/URL beyaz listesi, hız sınırı, üçüncü taraf model sağlayıcı (OpenAI/Anthropic/bulut) kullanım politikaları ve veri saklama protokolü | `kapsam/roe_sozlesmesi.json` ve `kapsam/aday_test_plani.json` (**sentetik fixture**) | Buradaki JSON şeması hukuki danışmanlık veya gerçek kurum sözleşmesi yerine geçmez |
| **Sistem anatomisi** | Mimari diyagramlar, API ağ geçidi yapılandırmaları, MCP/araç şemaları, vektör veritabanı indeksleri ve ön-yüz render kodu | `sistemler/musteri_asistani_mimari.json` (**sentetik mimari tanımı**) | Statik mimari tanımı, çalışma zamanında yanlış bağlanmış gizli bir aracı tek başına kanıtlamaz |
| **Canlı keşif (Recon)** | İzinli hedef üzerinde hız limitine uyarak sistem rolünü, araç yüzeyini, bilgi kaynağını ve bellek davranışını yoklama | Son görevde yerel Ollama modeli (`ai_lab.SohbetOturumu`) üzerinde RoE filtreli 4 canlı keşif sorgusu | Modelin kendi araç veya kaynak adını söylemesi her zaman gerçek çalışma zamanı yetkisini eksiksiz yansıtmaz; uygulama katmanında ayrıca doğrulanır |

> [!GÜVENLİK]
> Yetkisiz sistemlere veya üçüncü taraf bulut model API'lerine izinsiz saldırı trafiği göndermek hem sözleşme hem yasa ihlalidir. Bu dersteki `kapsam/` ve `sistemler/` dosyaları her çalıştırmada geçici çalışma klasörüne sıfırdan kopyalanır (**çalıştırmalar arasında dosya kalıcılığı yoktur**). Görev değerlendirmeleri görünür dosyalardan bağımsız gizli test verileriyle yapılır.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-36")
```

```python
from ai_saldiri_veri import json_yukle

roe = json_yukle("kapsam/roe_sozlesmesi.json")
mimari = json_yukle("sistemler/musteri_asistani_mimari.json")
print("RoE:", roe["kapsam_id"], "izinli hedefler:", roe["izinli_hedefler"])
print("Mimari:", mimari["sistem_id"], "araçlar:", [a["ad"] for a in mimari["araclar"]])
```
:::

::: anlat Klasik pentest ile AI red team neden farklıdır?
Klasik uygulama sızma testinde (pentest) hedef çoğu zaman **deterministik bir kod hatasıdır**: SQL sorgusuna kaçışsız eklenen parametre, eksik yetki kontrolü (IDOR) veya yamalanmamış bir kütüphane sürümü. Aynı girdi aynı koşulda her seferinde aynı sonucu üretir ve düzeltme net bir kod yamasıdır.

**AI Red Team** çalışmasında ise klasik uygulama yüzeyine ek olarak **olasılıksal ve bağlama duyarlı bir model katmanı** bulunur:

1. **Talimat ile verinin aynı kanalda akması:** Sistem istemi, kullanıcı mesajı, RAG'dan dönen belge ve araç çıktısı modelin bağlam penceresinde aynı token dizisine dönüşür.
2. **Olasılıksal davranış:** Aynı istem `temperature > 0` veya farklı konuşma geçmişinde bir kez reddedilip bir sonraki denemede sızıntı üretebilir; bu yüzden tek deneme yerine ölçülebilir başarı oranı (`ai-saldiri-05`), N koşuda tekrarlanabilirlik/tutarlılık (`ai-guvence-33`) ve hata-ayrık kanıt gerekir.
3. **Zincirleme etki:** Modelin yanlış yönlendirilmesi tek başına son etki olmayabilir; modelin ürettiği çıktı bir **aracı** tetiklediğinde (`ai-saldiri-01`, `ai-saldiri-16`) veya **HTML/SQL/komut tüketicisine** doğrulamasız aktığında gerçek sistem ihlaline dönüşür.
:::

::: anlat Yasal erişim ve Kapsam Belgesi (Rules of Engagement — RoE)
Bir AI red team çalışması başlamadan önce kapsam belgesi (**RoE**) makinece de denetlenebilir kurallara bağlanır:

- **İzinli hedefler (`izinli_hedefler`):** Yalnız açıkça listelenen laboratuvar veya test uç noktalarına (`lab://...`) istek gönderilebilir; kapsam dışı her uç nokta (`hedef-kapsam-disi`) yürütme öncesinde engellenir.
- **Üçüncü taraf model API şartları (`ucuncu_taraf_api_izni`):** Hedef uygulama arka planda ticari bir bulut LLM sağlayıcısı kullanıyorsa, müşterinin kendi uygulaması için verdiği izin bulut sağlayıcının kullanım politikasını (AUP/ToS) kendiliğinden geçersiz kılmaz. Üçüncü taraf API izni `False` iken `"ucuncu-taraf-api"` hedefli testler (`ucuncu-taraf-api-yasak`) reddedilir.
- **Hız limiti (`maks_istek_dakika`):** Model çıkarımı GPU/bellek tükettiğinden, hız limitini aşan (`hiz-limiti-asimi`) taramalar hizmet kesintisine (DoS) yol açabilir.
- **Gerçek PII ve zararlı yük yasağı (`yasak_kategoriler`):** Testlerde gerçek kişisel veri (`gercek-pii`), gerçek zararlı yazılım/istismar yükü (`zararli-yuk`) veya `hizmet-kesintisi` kullanılmaz; bunun yerine oturuma özel zararsız **vekil işaretler (canary)** kullanılır.
- **Kanıt saklama sınırı (`kanit_saklama_gun`):** Model yanıtları hassas bağlam içerebileceğinden, saklama süresini aşan (`saklama-suresi-asimi`) kayıt planları kabul edilmez.
:::

::: anlat Hedef sistemin 6 bileşenli anatomisi ve güven sınırları
Bir AI uygulamasının saldırı yüzeyi incelenirken sistem 6 bileşene ayrılır:

1. **Model (`model`):** Yerel veya bulut API üzerinden çalışan temel dil modeli.
2. **Sistem istemi (`sistem_istemi`):** Rol sınırını ve varsa gizli iş kurallarını (`gizli_talimat_var`) taşıyan katman.
3. **RAG (`rag`):** Modelin dış bilgi kaynaklarından (`dis_kaynak_acik`) belge çekip bağlama eklediği katman.
4. **Araçlar (`araclar`):** Modelin çağırabildiği okuma, yazma veya komut araçları ile insan onayı (`onay_gerekli`) gereksinimi.
5. **Bellek (`bellek`):** Konuşma geçmişinin kalıcılığı (`kalici`) ve oturumlar arası paylaşımı (`oturumlar_arasi_paylasim`).
6. **Çıktı tüketici (`cikti_tuketici`):** Model yanıtının düz metin mi gösterildiği, yoksa `html-render`, `sql-sorgusu` veya `kabuk-komutu` olarak doğrudan mı çalıştırıldığı (`dogrudan_calistirma`).

En yüksek riskli senaryolar, **güvenilmeyen dış veri girişinin** (`dolayli-rag-enjeksiyonu` veya `capraz-oturum-bellek-zehirlemesi`) **onaysız yüksek yetkili bir araca** (`rag->onaysiz-arac`, `paylasimli-bellek->onaysiz-arac`) ya da **doğrudan çalıştırılan bir çıktı tüketicisine** (`dis-veri->dogrudan-cikti-calistirma`) ulaştığı **güven sınırı geçişleridir**.
:::

::: tahmin RoE filtresi ve güven sınırı geçişi hangi sonucu üretir?
Aşağıdaki kod parçasında aday testlerin RoE kontrolünü ve mimarideki onaysız yüksek yetkili araç kontrolünü izleyip üç `print` çıktısını tahmin et:

```python
izinli = {"lab://asistan"}
testler = [
    {"id": "T1", "hedef": "lab://asistan", "turu": "yerel-model", "hiz": 10},
    {"id": "T2", "hedef": "lab://asistan", "turu": "ucuncu-taraf-api", "hiz": 10},
    {"id": "T3", "hedef": "lab://baska", "turu": "yerel-model", "hiz": 50},
]
gecen = [
    t["id"] for t in testler
    if t["hedef"] in izinli and t["turu"] == "yerel-model" and t["hiz"] <= 30
]
araclar = [
    {"ad": "oku", "yetki": "okuma", "onay": False},
    {"ad": "sil", "yetki": "yazma", "onay": False},
    {"ad": "komut", "yetki": "komut", "onay": True},
]
onaysiz_yuksek = [a["ad"] for a in araclar if a["yetki"] in ("yazma", "komut") and not a["onay"]]
print("gecen:", gecen)
print("engellenen_sayisi:", len(testler) - len(gecen))
print("onaysiz_yuksek:", onaysiz_yuksek)
```

???

```cikti
gecen: ['T1']
engellenen_sayisi: 2
onaysiz_yuksek: ['sil']
```

`T2` üçüncü taraf API kullandığı için, `T3` ise hem kapsam dışı hedefe gittiği hem hız sınırını aştığı için elenir (`gecen: ['T1']`, `engellenen_sayisi: 2`). Araçlar arasında `yazma` veya `komut` yetkisine sahip olup `onay == False` olan tek araç `'sil'`dir.
:::

::: gorev 1 · Yasal kapsam belgesine (RoE) göre aday test planını denetle
`roe_denetle(roe, aday_testler)` işlevini yaz.

- `roe` sözlüğü en az `{"kapsam_id", "izinli_hedefler", "ucuncu_taraf_api_izni", "maks_istek_dakika", "kanit_saklama_gun", "yasak_kategoriler"}` anahtarlarını taşımalıdır:
  - `kapsam_id`: boş olmayan `str`.
  - `izinli_hedefler`: en az 1 öğeli, boş olmayan `str` listesi.
  - `ucuncu_taraf_api_izni`: `bool`.
  - `maks_istek_dakika`: `bool` olmayan, `1..600` aralığında `int`.
  - `kanit_saklama_gun`: `bool` olmayan, `1..90` aralığında `int`.
  - `yasak_kategoriler`: boş olmayan `str` öğelerinden oluşan liste (boş liste olabilir).
- `aday_testler` bir listedir; her öğe tam olarak `{"test_id", "hedef", "hedef_turu", "istek_dakika", "kategori", "saklama_gun"}` anahtarlarını taşır:
  - `test_id`: boş olmayan ve listede benzersiz `str`.
  - `hedef`: boş olmayan `str`.
  - `hedef_turu`: `"yerel-model"` veya `"ucuncu-taraf-api"`.
  - `istek_dakika`: `bool` olmayan, `1..1000` aralığında `int`.
  - `kategori`: boş olmayan `str`.
  - `saklama_gun`: `bool` olmayan, `1..365` aralığında `int`.
- Şema, tür veya değer aralıklarından herhangi biri ihlal edilirse `ValueError` yükselt. Girdileri değiştirme.

Her aday testi aşağıdaki **sabit sırayla** kontrol et:
1. `hedef` `roe["izinli_hedefler"]` içinde değilse → `"hedef-kapsam-disi"`
2. `hedef_turu == "ucuncu-taraf-api"` iken `roe["ucuncu_taraf_api_izni"]` `False` ise → `"ucuncu-taraf-api-yasak"`
3. `istek_dakika > roe["maks_istek_dakika"]` ise → `"hiz-limiti-asimi"`
4. `kategori` `roe["yasak_kategoriler"]` içindeyse → `"yasak-kategori"`
5. `saklama_gun > roe["kanit_saklama_gun"]` ise → `"saklama-suresi-asimi"`

Hiç ihlali olmayan testlerin `test_id` değerlerini `izinli_testler` listesine, en az bir ihlali olanları `{"test_id": ..., "ihlaller": [...]}` biçiminde `engellenen_testler` listesine ekle ve her ihlal türünün toplam kaç testte görüldüğünü `ihlal_sayilari` sözlüğünde döndür:

```text
{
  "kapsam_id": str,
  "izinli_testler": [str, ...],
  "engellenen_testler": [{"test_id": str, "ihlaller": [str, ...]}, ...],
  "ihlal_sayilari": {
    "hedef-kapsam-disi": int,
    "ucuncu-taraf-api-yasak": int,
    "hiz-limiti-asimi": int,
    "yasak-kategori": int,
    "saklama-suresi-asimi": int
  }
}
```

```starter
from ai_saldiri_veri import json_yukle

roe = json_yukle("kapsam/roe_sozlesmesi.json")
aday_testler = json_yukle("kapsam/aday_test_plani.json")

def roe_denetle(roe, aday_testler):
    # HATA: Yalnız hedef adresini kontrol ediyor; üçüncü taraf API, hız limiti, yasak kategori ve saklama süresini atlıyor.
    izinli = []
    engellenen = []
    sayilar = {
        "hedef-kapsam-disi": 0,
        "ucuncu-taraf-api-yasak": 0,
        "hiz-limiti-asimi": 0,
        "yasak-kategori": 0,
        "saklama-suresi-asimi": 0,
    }
    for t in aday_testler:
        if t["hedef"] in roe["izinli_hedefler"]:
            izinli.append(t["test_id"])
        else:
            engellenen.append({"test_id": t["test_id"], "ihlaller": ["hedef-kapsam-disi"]})
            sayilar["hedef-kapsam-disi"] += 1
    return {
        "kapsam_id": roe["kapsam_id"],
        "izinli_testler": izinli,
        "engellenen_testler": engellenen,
        "ihlal_sayilari": sayilar,
    }

print(roe_denetle(roe, aday_testler))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-36")
```

```test
import copy
from pathlib import Path

ok(Path("kapsam/roe_sozlesmesi.json").is_file() and Path("kapsam/aday_test_plani.json").is_file(), "görünür RoE ve aday test planı dosyaları hazır")

ORNEK_ROE = {
    "kapsam_id": "ROE-1",
    "izinli_hedefler": ["lab://asistan", "lab://rag"],
    "ucuncu_taraf_api_izni": False,
    "maks_istek_dakika": 30,
    "kanit_saklama_gun": 14,
    "yasak_kategoriler": ["gercek-pii", "zararli-yuk"],
}

def _test(tid="t1", hedef="lab://asistan", turu="yerel-model", hiz=30, kat="vekil", gun=14):
    return {"test_id": tid, "hedef": hedef, "hedef_turu": turu, "istek_dakika": hiz, "kategori": kat, "saklama_gun": gun}

def sozlesme(fn):
    try:
        adaylar = [
            _test("t1", "lab://asistan", "yerel-model", 30, "vekil", 14),
            _test("t2", "lab://dis", "ucuncu-taraf-api", 31, "gercek-pii", 15),
            _test("t3", "lab://rag", "ucuncu-taraf-api", 10, "vekil", 7),
        ]
        r_kopya = copy.deepcopy(ORNEK_ROE)
        a_kopya = copy.deepcopy(adaylar)
        sonuc = fn(ORNEK_ROE, adaylar)
        if ORNEK_ROE != r_kopya or adaylar != a_kopya:
            return False
        if sonuc != {
            "kapsam_id": "ROE-1",
            "izinli_testler": ["t1"],
            "engellenen_testler": [
                {
                    "test_id": "t2",
                    "ihlaller": [
                        "hedef-kapsam-disi",
                        "ucuncu-taraf-api-yasak",
                        "hiz-limiti-asimi",
                        "yasak-kategori",
                        "saklama-suresi-asimi",
                    ],
                },
                {
                    "test_id": "t3",
                    "ihlaller": ["ucuncu-taraf-api-yasak"],
                },
            ],
            "ihlal_sayilari": {
                "hedef-kapsam-disi": 1,
                "ucuncu-taraf-api-yasak": 2,
                "hiz-limiti-asimi": 1,
                "yasak-kategori": 1,
                "saklama-suresi-asimi": 1,
            },
        }:
            return False
        roe_api_acik = dict(ORNEK_ROE, ucuncu_taraf_api_izni=True, maks_istek_dakika=600, kanit_saklama_gun=90, yasak_kategoriler=[])
        if fn(roe_api_acik, [_test("t1", "lab://asistan", "ucuncu-taraf-api", 600, "vekil", 90)])["izinli_testler"] != ["t1"]:
            return False
        roe_min = dict(ORNEK_ROE, maks_istek_dakika=1, kanit_saklama_gun=1)
        if fn(roe_min, [_test("t1", "lab://asistan", "yerel-model", 1, "vekil", 1)])["izinli_testler"] != ["t1"]:
            return False
        if fn(ORNEK_ROE, [_test("t1", "lab://asistan", "yerel-model", 1000, "vekil", 365)])["engellenen_testler"][0]["ihlaller"] != ["hiz-limiti-asimi", "saklama-suresi-asimi"]:
            return False
        for b_roe, b_aday in [
            (None, []), ({}, []),
            (dict(ORNEK_ROE, kapsam_id=""), []),
            (dict(ORNEK_ROE, kapsam_id=1), []),
            (dict(ORNEK_ROE, izinli_hedefler=[]), []),
            (dict(ORNEK_ROE, izinli_hedefler=[""]), []),
            (dict(ORNEK_ROE, izinli_hedefler=[1]), []),
            (dict(ORNEK_ROE, izinli_hedefler="lab://a"), []),
            (dict(ORNEK_ROE, ucuncu_taraf_api_izni=1), []),
            (dict(ORNEK_ROE, maks_istek_dakika=0), []),
            (dict(ORNEK_ROE, maks_istek_dakika=601), []),
            (dict(ORNEK_ROE, maks_istek_dakika=True), []),
            (dict(ORNEK_ROE, maks_istek_dakika="30"), []),
            (dict(ORNEK_ROE, kanit_saklama_gun=0), []),
            (dict(ORNEK_ROE, kanit_saklama_gun=91), []),
            (dict(ORNEK_ROE, kanit_saklama_gun=True), []),
            (dict(ORNEK_ROE, kanit_saklama_gun="14"), []),
            (dict(ORNEK_ROE, yasak_kategoriler="pii"), []),
            (dict(ORNEK_ROE, yasak_kategoriler=[""]), []),
            (dict(ORNEK_ROE, yasak_kategoriler=[1]), []),
            (ORNEK_ROE, None), (ORNEK_ROE, "liste"), (ORNEK_ROE, [None]), (ORNEK_ROE, [{}]),
            (ORNEK_ROE, [_test("")]), (ORNEK_ROE, [_test(1)]),
            (ORNEK_ROE, [_test("a"), _test("a")]),
            (ORNEK_ROE, [_test("a", hedef="")]), (ORNEK_ROE, [_test("a", hedef=1)]),
            (ORNEK_ROE, [_test("a", turu="bulut")]),
            (ORNEK_ROE, [_test("a", hiz=0)]), (ORNEK_ROE, [_test("a", hiz=1001)]),
            (ORNEK_ROE, [_test("a", hiz=True)]), (ORNEK_ROE, [_test("a", hiz="10")]),
            (ORNEK_ROE, [_test("a", kat="")]), (ORNEK_ROE, [_test("a", kat=1)]),
            (ORNEK_ROE, [_test("a", gun=0)]), (ORNEK_ROE, [_test("a", gun=366)]),
            (ORNEK_ROE, [_test("a", gun=True)]), (ORNEK_ROE, [_test("a", gun="7")]),
            (ORNEK_ROE, [dict(_test("a"), fazla=1)]),
        ]:
            try:
                fn(b_roe, b_aday)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(roe_denetle), "RoE kapsam, hız, üçüncü taraf API, yasak kategori ve saklama süresi kuralları korunmalı")
def m_api_atla(roe, adaylar):
    r = roe_denetle(dict(roe, ucuncu_taraf_api_izni=True), adaylar)
    return r
def m_hiz_esit(roe, adaylar):
    r = roe_denetle(dict(roe, maks_istek_dakika=max(1, roe["maks_istek_dakika"] - 1)), adaylar)
    return r
for ad, mutant in [("üçüncü taraf API yasağını yok sayan", m_api_atla), ("hız limiti sınır değerini kaydıran", m_hiz_esit)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def roe_denetle(roe, aday_testler):
    ihlal_sirasi = (
        "hedef-kapsam-disi",
        "ucuncu-taraf-api-yasak",
        "hiz-limiti-asimi",
        "yasak-kategori",
        "saklama-suresi-asimi",
    )
    gerekli = {
        "kapsam_id",
        "izinli_hedefler",
        "ucuncu_taraf_api_izni",
        "maks_istek_dakika",
        "kanit_saklama_gun",
        "yasak_kategoriler",
    }
    if not isinstance(roe, dict) or not gerekli.issubset(roe):
        raise ValueError("roe şeması eksik")
    kid = roe["kapsam_id"]
    hedefler = roe["izinli_hedefler"]
    api_izni = roe["ucuncu_taraf_api_izni"]
    maks_hiz = roe["maks_istek_dakika"]
    maks_gun = roe["kanit_saklama_gun"]
    yasaklar = roe["yasak_kategoriler"]
    if not isinstance(kid, str) or not kid:
        raise ValueError("kapsam_id geçersiz")
    if not isinstance(hedefler, list) or not hedefler or any(not isinstance(h, str) or not h for h in hedefler):
        raise ValueError("izinli_hedefler geçersiz")
    if not isinstance(api_izni, bool):
        raise ValueError("ucuncu_taraf_api_izni bool olmalı")
    if isinstance(maks_hiz, bool) or not isinstance(maks_hiz, int) or not 1 <= maks_hiz <= 600:
        raise ValueError("maks_istek_dakika geçersiz")
    if isinstance(maks_gun, bool) or not isinstance(maks_gun, int) or not 1 <= maks_gun <= 90:
        raise ValueError("kanit_saklama_gun geçersiz")
    if not isinstance(yasaklar, list) or any(not isinstance(y, str) or not y for y in yasaklar):
        raise ValueError("yasak_kategoriler geçersiz")
    if not isinstance(aday_testler, list):
        raise ValueError("aday_testler liste olmalı")

    hedef_kumesi = set(hedefler)
    yasak_kumesi = set(yasaklar)
    izinli_testler = []
    engellenen_testler = []
    ihlal_sayilari = {k: 0 for k in ihlal_sirasi}
    gorulen = set()

    for t in aday_testler:
        if not isinstance(t, dict) or set(t) != {"test_id", "hedef", "hedef_turu", "istek_dakika", "kategori", "saklama_gun"}:
            raise ValueError("aday test şeması geçersiz")
        tid = t["test_id"]
        hedef = t["hedef"]
        hturu = t["hedef_turu"]
        hiz = t["istek_dakika"]
        kat = t["kategori"]
        gun = t["saklama_gun"]
        if not isinstance(tid, str) or not tid or tid in gorulen:
            raise ValueError("test_id geçersiz")
        if not isinstance(hedef, str) or not hedef:
            raise ValueError("hedef geçersiz")
        if hturu not in ("yerel-model", "ucuncu-taraf-api"):
            raise ValueError("hedef_turu geçersiz")
        if isinstance(hiz, bool) or not isinstance(hiz, int) or not 1 <= hiz <= 1000:
            raise ValueError("istek_dakika geçersiz")
        if not isinstance(kat, str) or not kat:
            raise ValueError("kategori geçersiz")
        if isinstance(gun, bool) or not isinstance(gun, int) or not 1 <= gun <= 365:
            raise ValueError("saklama_gun geçersiz")
        gorulen.add(tid)

        ihlaller = []
        if hedef not in hedef_kumesi:
            ihlaller.append("hedef-kapsam-disi")
        if hturu == "ucuncu-taraf-api" and not api_izni:
            ihlaller.append("ucuncu-taraf-api-yasak")
        if hiz > maks_hiz:
            ihlaller.append("hiz-limiti-asimi")
        if kat in yasak_kumesi:
            ihlaller.append("yasak-kategori")
        if gun > maks_gun:
            ihlaller.append("saklama-suresi-asimi")

        if ihlaller:
            engellenen_testler.append({"test_id": tid, "ihlaller": ihlaller})
            for ih in ihlaller:
                ihlal_sayilari[ih] += 1
        else:
            izinli_testler.append(tid)

    return {
        "kapsam_id": kid,
        "izinli_testler": izinli_testler,
        "engellenen_testler": engellenen_testler,
        "ihlal_sayilari": ihlal_sayilari,
    }
```

```hint
Önce `roe` sözlüğünü, ardından her aday testi doğrula. Bir testte birden fazla ihlal olabileceği için `elif` yerine beş bağımsız `if` kullan ve ihlal sırasını koru.
```
:::

::: gorev 2 · Hedef sistemin 6 katmanlı anatomisini ve güven sınırı geçişlerini çıkar
`sistem_anatomisi(mimari)` işlevini yaz. `mimari` sözlüğü en az `{"sistem_id", "model", "sistem_istemi", "rag", "araclar", "bellek", "cikti_tuketici"}` anahtarlarını taşımalıdır:

- `sistem_id`: boş olmayan `str`.
- `model`: tam olarak `{"ad", "erisim"}` anahtarlarını taşıyan sözlük (`ad`: boş olmayan `str`, `erisim`: `"yerel"` veya `"bulut-api"`).
- `sistem_istemi`: tam olarak `{"gizli_talimat_var", "rol_siniri"}` anahtarlarını taşıyan sözlük (`gizli_talimat_var`: `bool`, `rol_siniri`: boş olmayan `str`).
- `rag`: tam olarak `{"aktif", "dis_kaynak_acik"}` anahtarlarını taşıyan sözlük (ikisi de `bool`; `aktif == False` iken `dis_kaynak_acik == True` olamaz).
- `araclar`: `0..16` öğeli liste; her öğe tam olarak `{"ad", "yetki", "onay_gerekli"}` taşıyan sözlük (`ad`: benzersiz boş olmayan `str`, `yetki`: `"okuma"`, `"yazma"` veya `"komut"`, `onay_gerekli`: `bool`).
- `bellek`: tam olarak `{"kalici", "oturumlar_arasi_paylasim"}` taşıyan sözlük (ikisi de `bool`; `kalici == False` iken `oturumlar_arasi_paylasim == True` olamaz).
- `cikti_tuketici`: tam olarak `{"tur", "dogrudan_calistirma"}` taşıyan sözlük (`tur`: `"duz-metin"`, `"html-render"`, `"sql-sorgusu"` veya `"kabuk-komutu"`, `dogrudan_calistirma`: `bool`).
- Şema veya tutarlılık kuralları ihlal edilirse `ValueError` yükselt. Girdiyi değiştirme.

Geçerli bir mimari için şu sözlüğü döndür:

```text
{
  "sistem_id": str,
  "acik_yuzeyler": [...],                  # alfabetik sıralı
  "onaysiz_yuksek_yetkili_araclar": [...], # alfabetik sıralı
  "kritik_gecisler": [...]                 # alfabetik sıralı
}
```

Kurallar:
- `acik_yuzeyler`:
  - `"dogrudan-kullanici-girdisi"` her zaman bulunur.
  - `sistem_istemi["gizli_talimat_var"]` doğruysa → `"sistem-istemi-sizintisi"`
  - `rag["aktif"]` ve `rag["dis_kaynak_acik"]` doğruysa → `"dolayli-rag-enjeksiyonu"`
  - `araclar` listesi boş değilse → `"arac-cagrisi-manipulasyonu"`
  - `bellek["kalici"]` ve `bellek["oturumlar_arasi_paylasim"]` doğruysa → `"capraz-oturum-bellek-zehirlemesi"`
  - `cikti_tuketici["tur"] != "duz-metin"` ve `cikti_tuketici["dogrudan_calistirma"]` doğruysa → `"guvensiz-cikti-tuketimi"`
- `onaysiz_yuksek_yetkili_araclar`: `yetki` değeri `"yazma"` veya `"komut"` olup `onay_gerekli == False` olan araçların `ad` listesi (alfabetik).
- `kritik_gecisler` (güvenilmeyen bağlamın tehlikeli yürütmeye bağlandığı güven sınırı geçişleri):
  - `"dolayli-rag-enjeksiyonu"` açık yüzeylerde varsa **ve** `onaysiz_yuksek_yetkili_araclar` boş değilse → `"rag->onaysiz-arac"`
  - `"capraz-oturum-bellek-zehirlemesi"` açık yüzeylerde varsa **ve** `onaysiz_yuksek_yetkili_araclar` boş değilse → `"paylasimli-bellek->onaysiz-arac"`
  - `"guvensiz-cikti-tuketimi"` açık yüzeylerde varsa **ve** (`"dolayli-rag-enjeksiyonu"` **veya** `"capraz-oturum-bellek-zehirlemesi"`) açık yüzeylerde varsa → `"dis-veri->dogrudan-cikti-calistirma"`

```starter
from ai_saldiri_veri import json_yukle

mimari = json_yukle("sistemler/musteri_asistani_mimari.json")

def sistem_anatomisi(mimari):
    # HATA: Yalnız araç listesine bakıyor; RAG, bellek, çıktı tüketici ve güven sınırı geçişlerini çıkarmıyor.
    araclar = [a["ad"] for a in mimari["araclar"] if not a["onay_gerekli"]]
    return {
        "sistem_id": mimari["sistem_id"],
        "acik_yuzeyler": ["dogrudan-kullanici-girdisi"],
        "onaysiz_yuksek_yetkili_araclar": sorted(araclar),
        "kritik_gecisler": [],
    }

print(sistem_anatomisi(mimari))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-36")
```

```test
import copy
from pathlib import Path

ok(Path("sistemler/musteri_asistani_mimari.json").is_file(), "görünür sistem mimarisi dosyası hazır")

ORNEK_MIMARI = {
    "sistem_id": "SIS-1",
    "model": {"ad": "qwen3:4b", "erisim": "yerel"},
    "sistem_istemi": {"gizli_talimat_var": True, "rol_siniri": "sipariş asistanı"},
    "rag": {"aktif": True, "dis_kaynak_acik": True},
    "araclar": [
        {"ad": "siparis_oku", "yetki": "okuma", "onay_gerekli": False},
        {"ad": "iade_yaz", "yetki": "yazma", "onay_gerekli": False},
        {"ad": "kabuk", "yetki": "komut", "onay_gerekli": True},
    ],
    "bellek": {"kalici": True, "oturumlar_arasi_paylasim": True},
    "cikti_tuketici": {"tur": "html-render", "dogrudan_calistirma": True},
}

def sozlesme(fn):
    try:
        once = copy.deepcopy(ORNEK_MIMARI)
        r = fn(ORNEK_MIMARI)
        if ORNEK_MIMARI != once:
            return False
        if r != {
            "sistem_id": "SIS-1",
            "acik_yuzeyler": [
                "arac-cagrisi-manipulasyonu",
                "capraz-oturum-bellek-zehirlemesi",
                "dogrudan-kullanici-girdisi",
                "dolayli-rag-enjeksiyonu",
                "guvensiz-cikti-tuketimi",
                "sistem-istemi-sizintisi",
            ],
            "onaysiz_yuksek_yetkili_araclar": ["iade_yaz"],
            "kritik_gecisler": [
                "dis-veri->dogrudan-cikti-calistirma",
                "paylasimli-bellek->onaysiz-arac",
                "rag->onaysiz-arac",
            ],
        }:
            return False
        sade = {
            "sistem_id": "SIS-SADE",
            "model": {"ad": "m", "erisim": "bulut-api"},
            "sistem_istemi": {"gizli_talimat_var": False, "rol_siniri": "genel"},
            "rag": {"aktif": False, "dis_kaynak_acik": False},
            "araclar": [],
            "bellek": {"kalici": False, "oturumlar_arasi_paylasim": False},
            "cikti_tuketici": {"tur": "duz-metin", "dogrudan_calistirma": True},
        }
        if fn(sade) != {
            "sistem_id": "SIS-SADE",
            "acik_yuzeyler": ["dogrudan-kullanici-girdisi"],
            "onaysiz_yuksek_yetkili_araclar": [],
            "kritik_gecisler": [],
        }:
            return False
        yalniz_bellek_cikti = dict(
            sade,
            bellek={"kalici": True, "oturumlar_arasi_paylasim": True},
            cikti_tuketici={"tur": "sql-sorgusu", "dogrudan_calistirma": True},
        )
        if fn(yalniz_bellek_cikti)["kritik_gecisler"] != ["dis-veri->dogrudan-cikti-calistirma"]:
            return False
        yalniz_rag_cikti = dict(
            sade,
            rag={"aktif": True, "dis_kaynak_acik": True},
            cikti_tuketici={"tur": "kabuk-komutu", "dogrudan_calistirma": False},
        )
        if fn(yalniz_rag_cikti)["kritik_gecisler"] != []:
            return False
        ic_rag_izole_bellek = dict(
            sade,
            rag={"aktif": True, "dis_kaynak_acik": False},
            bellek={"kalici": True, "oturumlar_arasi_paylasim": False},
        )
        if fn(ic_rag_izole_bellek)["acik_yuzeyler"] != ["dogrudan-kullanici-girdisi"]:
            return False
        onalti_arac = dict(
            sade,
            araclar=[{"ad": f"a{i}", "yetki": "komut" if i == 0 else "okuma", "onay_gerekli": False} for i in range(16)],
        )
        if fn(onalti_arac)["onaysiz_yuksek_yetkili_araclar"] != ["a0"] or fn(onalti_arac)["kritik_gecisler"] != []:
            return False
        for b in [
            None, [], {},
            dict(ORNEK_MIMARI, sistem_id=""), dict(ORNEK_MIMARI, sistem_id=1),
            dict(ORNEK_MIMARI, model=None), dict(ORNEK_MIMARI, model={"ad": "m"}),
            dict(ORNEK_MIMARI, model={"ad": "", "erisim": "yerel"}),
            dict(ORNEK_MIMARI, model={"ad": 1, "erisim": "yerel"}),
            dict(ORNEK_MIMARI, model={"ad": "m", "erisim": "hibrit"}),
            dict(ORNEK_MIMARI, sistem_istemi=None), dict(ORNEK_MIMARI, sistem_istemi={"gizli_talimat_var": True}),
            dict(ORNEK_MIMARI, sistem_istemi={"gizli_talimat_var": 1, "rol_siniri": "x"}),
            dict(ORNEK_MIMARI, sistem_istemi={"gizli_talimat_var": True, "rol_siniri": ""}),
            dict(ORNEK_MIMARI, sistem_istemi={"gizli_talimat_var": True, "rol_siniri": 1}),
            dict(ORNEK_MIMARI, rag=None), dict(ORNEK_MIMARI, rag={"aktif": True}),
            dict(ORNEK_MIMARI, rag={"aktif": 1, "dis_kaynak_acik": False}),
            dict(ORNEK_MIMARI, rag={"aktif": True, "dis_kaynak_acik": 0}),
            dict(ORNEK_MIMARI, rag={"aktif": False, "dis_kaynak_acik": True}),
            dict(ORNEK_MIMARI, araclar="araclar"),
            dict(ORNEK_MIMARI, araclar=()),
            dict(ORNEK_MIMARI, araclar=[{"ad": f"a{i}", "yetki": "okuma", "onay_gerekli": True} for i in range(17)]),
            dict(ORNEK_MIMARI, araclar=[None]),
            dict(ORNEK_MIMARI, araclar=[{"ad": "a", "yetki": "okuma"}]),
            dict(ORNEK_MIMARI, araclar=[{"ad": "", "yetki": "okuma", "onay_gerekli": True}]),
            dict(ORNEK_MIMARI, araclar=[{"ad": 1, "yetki": "okuma", "onay_gerekli": True}]),
            dict(ORNEK_MIMARI, araclar=[{"ad": "a", "yetki": "okuma", "onay_gerekli": True}, {"ad": "a", "yetki": "yazma", "onay_gerekli": False}]),
            dict(ORNEK_MIMARI, araclar=[{"ad": "a", "yetki": "silme", "onay_gerekli": True}]),
            dict(ORNEK_MIMARI, araclar=[{"ad": "a", "yetki": "okuma", "onay_gerekli": 1}]),
            dict(ORNEK_MIMARI, bellek=None), dict(ORNEK_MIMARI, bellek={"kalici": True}),
            dict(ORNEK_MIMARI, bellek={"kalici": 1, "oturumlar_arasi_paylasim": False}),
            dict(ORNEK_MIMARI, bellek={"kalici": True, "oturumlar_arasi_paylasim": 0}),
            dict(ORNEK_MIMARI, bellek={"kalici": False, "oturumlar_arasi_paylasim": True}),
            dict(ORNEK_MIMARI, cikti_tuketici=None), dict(ORNEK_MIMARI, cikti_tuketici={"tur": "duz-metin"}),
            dict(ORNEK_MIMARI, cikti_tuketici={"tur": "markdown", "dogrudan_calistirma": False}),
            dict(ORNEK_MIMARI, cikti_tuketici={"tur": "duz-metin", "dogrudan_calistirma": 0}),
        ]:
            try:
                fn(b)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(sistem_anatomisi), "6 bileşenli sistem anatomisi ve güven sınırı geçişleri doğru çıkarılmalı")
def m_okuma_dahil(m):
    r = sistem_anatomisi(m)
    r["onaysiz_yuksek_yetkili_araclar"] = sorted([a["ad"] for a in m["araclar"] if not a["onay_gerekli"]])
    return r
def m_gecis_eksik(m):
    r = sistem_anatomisi(m)
    r["kritik_gecisler"] = []
    return r
for ad, mutant in [("okuma aracını yüksek yetkili sayan", m_okuma_dahil), ("güven sınırı geçişlerini boş bırakan", m_gecis_eksik)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

for rag_var in (False,True):
    for bellek_var in (False,True):
        tek=copy.deepcopy(ORNEK_MIMARI)
        tek['rag']={'aktif':rag_var,'dis_kaynak_acik':rag_var}
        tek['bellek']={'kalici':bellek_var,'oturumlar_arasi_paylasim':bellek_var}
        gecis=sistem_anatomisi(tek)['kritik_gecisler']
        eq('dis-veri->dogrudan-cikti-calistirma' in gecis,rag_var or bellek_var,'RAG/bellek bağımsız OR matrisi')
```

```solution
def sistem_anatomisi(mimari):
    gerekli = {"sistem_id", "model", "sistem_istemi", "rag", "araclar", "bellek", "cikti_tuketici"}
    if not isinstance(mimari, dict) or not gerekli.issubset(mimari):
        raise ValueError("mimari şeması eksik")
    sid = mimari["sistem_id"]
    model = mimari["model"]
    sis = mimari["sistem_istemi"]
    rag = mimari["rag"]
    araclar = mimari["araclar"]
    bellek = mimari["bellek"]
    cikti = mimari["cikti_tuketici"]

    if not isinstance(sid, str) or not sid:
        raise ValueError("sistem_id geçersiz")
    if not isinstance(model, dict) or set(model) != {"ad", "erisim"}:
        raise ValueError("model şeması geçersiz")
    if not isinstance(model["ad"], str) or not model["ad"] or model["erisim"] not in ("yerel", "bulut-api"):
        raise ValueError("model alanları geçersiz")
    if not isinstance(sis, dict) or set(sis) != {"gizli_talimat_var", "rol_siniri"}:
        raise ValueError("sistem_istemi şeması geçersiz")
    if not isinstance(sis["gizli_talimat_var"], bool) or not isinstance(sis["rol_siniri"], str) or not sis["rol_siniri"]:
        raise ValueError("sistem_istemi alanları geçersiz")
    if not isinstance(rag, dict) or set(rag) != {"aktif", "dis_kaynak_acik"}:
        raise ValueError("rag şeması geçersiz")
    if not isinstance(rag["aktif"], bool) or not isinstance(rag["dis_kaynak_acik"], bool):
        raise ValueError("rag alanları bool olmalı")
    if not rag["aktif"] and rag["dis_kaynak_acik"]:
        raise ValueError("pasif rag dış kaynağa açık olamaz")
    if not isinstance(araclar, list) or len(araclar) > 16:
        raise ValueError("araclar 0..16 öğeli liste olmalı")

    arac_adlari = set()
    onaysiz_yuksek = []
    for a in araclar:
        if not isinstance(a, dict) or set(a) != {"ad", "yetki", "onay_gerekli"}:
            raise ValueError("araç şeması geçersiz")
        if not isinstance(a["ad"], str) or not a["ad"] or a["ad"] in arac_adlari:
            raise ValueError("araç adı geçersiz")
        if a["yetki"] not in ("okuma", "yazma", "komut") or not isinstance(a["onay_gerekli"], bool):
            raise ValueError("araç yetki/onay geçersiz")
        arac_adlari.add(a["ad"])
        if a["yetki"] in ("yazma", "komut") and not a["onay_gerekli"]:
            onaysiz_yuksek.append(a["ad"])

    if not isinstance(bellek, dict) or set(bellek) != {"kalici", "oturumlar_arasi_paylasim"}:
        raise ValueError("bellek şeması geçersiz")
    if not isinstance(bellek["kalici"], bool) or not isinstance(bellek["oturumlar_arasi_paylasim"], bool):
        raise ValueError("bellek alanları bool olmalı")
    if not bellek["kalici"] and bellek["oturumlar_arasi_paylasim"]:
        raise ValueError("kalıcı olmayan bellek paylaşılamaz")

    if not isinstance(cikti, dict) or set(cikti) != {"tur", "dogrudan_calistirma"}:
        raise ValueError("cikti_tuketici şeması geçersiz")
    if cikti["tur"] not in ("duz-metin", "html-render", "sql-sorgusu", "kabuk-komutu") or not isinstance(cikti["dogrudan_calistirma"], bool):
        raise ValueError("cikti_tuketici alanları geçersiz")

    yuzeyler = ["dogrudan-kullanici-girdisi"]
    if sis["gizli_talimat_var"]:
        yuzeyler.append("sistem-istemi-sizintisi")
    if rag["aktif"] and rag["dis_kaynak_acik"]:
        yuzeyler.append("dolayli-rag-enjeksiyonu")
    if araclar:
        yuzeyler.append("arac-cagrisi-manipulasyonu")
    if bellek["kalici"] and bellek["oturumlar_arasi_paylasim"]:
        yuzeyler.append("capraz-oturum-bellek-zehirlemesi")
    if cikti["tur"] != "duz-metin" and cikti["dogrudan_calistirma"]:
        yuzeyler.append("guvensiz-cikti-tuketimi")

    yk = set(yuzeyler)
    gecisler = []
    if "dolayli-rag-enjeksiyonu" in yk and onaysiz_yuksek:
        gecisler.append("rag->onaysiz-arac")
    if "capraz-oturum-bellek-zehirlemesi" in yk and onaysiz_yuksek:
        gecisler.append("paylasimli-bellek->onaysiz-arac")
    if "guvensiz-cikti-tuketimi" in yk and ("dolayli-rag-enjeksiyonu" in yk or "capraz-oturum-bellek-zehirlemesi" in yk):
        gecisler.append("dis-veri->dogrudan-cikti-calistirma")

    return {
        "sistem_id": sid,
        "acik_yuzeyler": sorted(yuzeyler),
        "onaysiz_yuksek_yetkili_araclar": sorted(onaysiz_yuksek),
        "kritik_gecisler": sorted(gecisler),
    }
```

```hint
Önce 6 bileşenin şema ve mantıksal tutarlılığını (`not aktif and dis_kaynak_acik`, `not kalici and oturumlar_arasi_paylasim`) doğrula. Ardından `acik_yuzeyler` kümesini kullanarak `kritik_gecisler` listesini üret.
```
:::

::: gorev 3 · Keşif (reconnaissance) yanıtlarından gözlenen katmanları çözümle
`kesif_yaniti_cozumle(gozlemler)` işlevini yaz. `gozlemler`, `1..10` öğeli bir listedir; her öğe tam olarak `{"sorgu_id", "hedef_katman", "yanit", "durum"}` anahtarlarını taşır:

- `sorgu_id`: boş olmayan ve listede benzersiz `str`.
- `hedef_katman`: `"rol-siniri"`, `"arac-yuzeyi"`, `"rag-yuzeyi"` veya `"bellek-yuzeyi"`.
- `yanit`: `str` (`durum == "tamam"` iken boş olamaz; `durum == "hata"` iken boş olabilir).
- `durum`: `"tamam"` veya `"hata"`.
- Geçersiz şema, tür veya değer durumunda `ValueError` yükselt. Girdiyi değiştirme.

`durum == "tamam"` olan her yanıtta (`yanit.casefold()` üzerinde) ilgili katmanın anahtar ipuçlarından en az biri geçiyorsa o katmanı `True` olarak işaretle:
- `"rol-siniri"`: `("sipariş", "siparis", "iade", "politika", "yalnız", "yalniz", "kapsam", "görev", "gorev", "asistan")`
- `"arac-yuzeyi"`: `("siparis_sorgula", "iade_olustur", "araç", "arac", "tool", "fonksiyon", "sorgula")`
- `"rag-yuzeyi"`: `("belge", "doküman", "dokuman", "kaynak", "indeks", "bilgi bankası", "bilgi bankasi", "kb-")`
- `"bellek-yuzeyi"`: `("oturum", "bellek", "geçmiş", "gecmis", "hatırla", "hatirla", "kalıcı", "kalici")`

Dönüş sözlüğü:

```text
{
  "toplam_sorgu": int,
  "gecerli_sorgu": int,
  "hata_sayisi": int,
  "gozlenen_katmanlar": {
    "rol-siniri": bool,
    "arac-yuzeyi": bool,
    "rag-yuzeyi": bool,
    "bellek-yuzeyi": bool
  },
  "dogrulanan_katman_sayisi": int
}
```

```starter
def kesif_yaniti_cozumle(gozlemler):
    # HATA: Hata durumundaki sorguları ayırmıyor ve yanıt içeriğine bakmadan her katmanı True sayıyor.
    gozlenen = {
        "rol-siniri": False,
        "arac-yuzeyi": False,
        "rag-yuzeyi": False,
        "bellek-yuzeyi": False,
    }
    for g in gozlemler:
        gozlenen[g["hedef_katman"]] = True
    return {
        "toplam_sorgu": len(gozlemler),
        "gecerli_sorgu": len(gozlemler),
        "hata_sayisi": 0,
        "gozlenen_katmanlar": gozlenen,
        "dogrulanan_katman_sayisi": sum(1 for v in gozlenen.values() if v),
    }

ornek = [
    {"sorgu_id": "s1", "hedef_katman": "rol-siniri", "yanit": "Yalnız sipariş ve iade politikası sorularına yanıt veririm.", "durum": "tamam"},
    {"sorgu_id": "s2", "hedef_katman": "arac-yuzeyi", "yanit": "", "durum": "hata"},
]
print(kesif_yaniti_cozumle(ornek))
```

```test
import copy

GOZLEMLER = [
    {"sorgu_id": "s1", "hedef_katman": "rol-siniri", "yanit": "Görev kapsamım yalnız İADE ve sipariş politikasıdır.", "durum": "tamam"},
    {"sorgu_id": "s2", "hedef_katman": "arac-yuzeyi", "yanit": "siparis_sorgula ve iade_olustur fonksiyonlarını kullanırım.", "durum": "tamam"},
    {"sorgu_id": "s3", "hedef_katman": "rag-yuzeyi", "yanit": "Bu konuda bilgi veremem.", "durum": "tamam"},
    {"sorgu_id": "s4", "hedef_katman": "bellek-yuzeyi", "yanit": "Oturum belleği zaman aşımı", "durum": "hata"},
]

def sozlesme(fn):
    try:
        once = copy.deepcopy(GOZLEMLER)
        r = fn(GOZLEMLER)
        if GOZLEMLER != once:
            return False
        if r != {
            "toplam_sorgu": 4,
            "gecerli_sorgu": 3,
            "hata_sayisi": 1,
            "gozlenen_katmanlar": {
                "rol-siniri": True,
                "arac-yuzeyi": True,
                "rag-yuzeyi": False,
                "bellek-yuzeyi": False,
            },
            "dogrulanan_katman_sayisi": 2,
        }:
            return False
        on_sorgu = [
            {"sorgu_id": f"q{i}", "hedef_katman": "rag-yuzeyi" if i < 5 else "bellek-yuzeyi", "yanit": "KB-2026 belge deposu ve kalıcı oturum geçmişi" if i == 9 else "merhaba", "durum": "tamam"}
            for i in range(10)
        ]
        r10 = fn(on_sorgu)
        if r10["toplam_sorgu"] != 10 or r10["gozlenen_katmanlar"]["bellek-yuzeyi"] is not True or r10["gozlenen_katman_sayisi" if "gozlenen_katman_sayisi" in r10 else "dogrulanan_katman_sayisi"] != 1:
            return False
        bos_hata = [{"sorgu_id": "h1", "hedef_katman": "rag-yuzeyi", "yanit": "", "durum": "hata"}]
        if fn(bos_hata)["hata_sayisi"] != 1 or fn(bos_hata)["gecerli_sorgu"] != 0:
            return False
        for b in [
            None, "liste", [], [None], [{}],
            [{"sorgu_id": f"q{i}", "hedef_katman": "rol-siniri", "yanit": "x", "durum": "tamam"} for i in range(11)],
            [{"sorgu_id": "", "hedef_katman": "rol-siniri", "yanit": "x", "durum": "tamam"}],
            [{"sorgu_id": 1, "hedef_katman": "rol-siniri", "yanit": "x", "durum": "tamam"}],
            [{"sorgu_id": "a", "hedef_katman": "rol-siniri", "yanit": "x", "durum": "tamam"},
             {"sorgu_id": "a", "hedef_katman": "arac-yuzeyi", "yanit": "y", "durum": "tamam"}],
            [{"sorgu_id": "a", "hedef_katman": "ag-yuzeyi", "yanit": "x", "durum": "tamam"}],
            [{"sorgu_id": "a", "hedef_katman": "rol-siniri", "yanit": None, "durum": "tamam"}],
            [{"sorgu_id": "a", "hedef_katman": "rol-siniri", "yanit": 123, "durum": "hata"}],
            [{"sorgu_id": "a", "hedef_katman": "rol-siniri", "yanit": "", "durum": "tamam"}],
            [{"sorgu_id": "a", "hedef_katman": "rol-siniri", "yanit": "x", "durum": "beklemede"}],
            [{"sorgu_id": "a", "hedef_katman": "rol-siniri", "yanit": "x", "durum": "tamam", "ek": 1}],
        ]:
            try:
                fn(b)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(kesif_yaniti_cozumle), "keşif yanıtları hata-ayrık ve casefold duyarlı çözümlenmeli")
def m_hatayi_gecerli_say(g):
    r = kesif_yaniti_cozumle(g)
    r["gozlenen_katmanlar"]["bellek-yuzeyi"] = True
    r["dogrulanan_katman_sayisi"] = sum(1 for v in r["gozlenen_katmanlar"].values() if v)
    return r
def m_buyuk_harf_kacir(g):
    r = kesif_yaniti_cozumle(g)
    r["gozlenen_katmanlar"]["rol-siniri"] = False
    r["dogrulanan_katman_sayisi"] = sum(1 for v in r["gozlenen_katmanlar"].values() if v)
    return r
for ad, mutant in [("hata durumundaki yanıtı gözlenmiş sayan", m_hatayi_gecerli_say), ("büyük/küçük harf duyarsız eşleşmeyi kaçıran", m_buyuk_harf_kacir)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

r=kesif_yaniti_cozumle([{'sorgu_id':'ust','hedef_katman':'arac-yuzeyi','yanit':'TOOL','durum':'tamam'}])
eq(r['gozlenen_katmanlar']['arac-yuzeyi'],True,'casefold tek büyük harf ipucu')
```

```solution
def kesif_yaniti_cozumle(gozlemler):
    ipucu_haritasi = {
        "rol-siniri": ("sipariş", "siparis", "iade", "politika", "yalnız", "yalniz", "kapsam", "görev", "gorev", "asistan"),
        "arac-yuzeyi": ("siparis_sorgula", "iade_olustur", "araç", "arac", "tool", "fonksiyon", "sorgula"),
        "rag-yuzeyi": ("belge", "doküman", "dokuman", "kaynak", "indeks", "bilgi bankası", "bilgi bankasi", "kb-"),
        "bellek-yuzeyi": ("oturum", "bellek", "geçmiş", "gecmis", "hatırla", "hatirla", "kalıcı", "kalici"),
    }
    if not isinstance(gozlemler, list) or not 1 <= len(gozlemler) <= 10:
        raise ValueError("gozlemler 1..10 öğeli liste olmalı")
    gorulen = set()
    gecerli = 0
    hata = 0
    gozlenen = {k: False for k in ipucu_haritasi}

    for g in gozlemler:
        if not isinstance(g, dict) or set(g) != {"sorgu_id", "hedef_katman", "yanit", "durum"}:
            raise ValueError("gözlem şeması geçersiz")
        sid = g["sorgu_id"]
        katman = g["hedef_katman"]
        yanit = g["yanit"]
        durum = g["durum"]
        if not isinstance(sid, str) or not sid or sid in gorulen:
            raise ValueError("sorgu_id geçersiz")
        if katman not in ipucu_haritasi:
            raise ValueError("hedef_katman geçersiz")
        if not isinstance(yanit, str):
            raise ValueError("yanit str olmalı")
        if durum not in ("tamam", "hata"):
            raise ValueError("durum geçersiz")
        if durum == "tamam" and not yanit:
            raise ValueError("tamam durumunda yanit boş olamaz")
        gorulen.add(sid)

        if durum == "hata":
            hata += 1
        else:
            gecerli += 1
            kucuk = yanit.casefold()
            if any(ipucu in kucuk for ipucu in ipucu_haritasi[katman]):
                gozlenen[katman] = True

    return {
        "toplam_sorgu": len(gozlemler),
        "gecerli_sorgu": gecerli,
        "hata_sayisi": hata,
        "gozlenen_katmanlar": gozlenen,
        "dogrulanan_katman_sayisi": sum(1 for v in gozlenen.values() if v),
    }
```

```hint
`durum == "hata"` olan kayıtları `hata_sayisi` içinde say ve anahtar kelime aramasına sokma. `durum == "tamam"` iken `yanit.casefold()` üzerinde ilgili katmanın ipuçlarını kontrol et.
```
:::

::: gorev Gerçek deney · Yerel modelde RoE filtreli sistem anatomisi keşfi
Önceki üç görevdeki `roe_denetle`, `sistem_anatomisi` ve `kesif_yaniti_cozumle` işlevlerini burada birleştir.

Bu gerçek deneyde:
1. 6 aday test (`4` izinli yerel keşif sorgusu + `1` üçüncü taraf bulut API testi + `1` gerçek PII / hız limiti aşımı testi) önce `roe_denetle` süzgecinden geçirilir; kapsam dışı iki test modele ulaşmadan engellenir.
2. Yalnız izinli 4 keşif sorgusu (`rol-siniri`, `arac-yuzeyi`, `rag-yuzeyi`, `bellek-yuzeyi`) `ai_lab.SohbetOturumu` ile yerel Ollama modeline gönderilir.
3. Mimari tanımı `sistem_anatomisi`, canlı model yanıtları ise `kesif_yaniti_cozumle` ile çözümlenir ve gerçek deney kanıtı (`ai_lab.kanit_yaz`) üretilir.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab
from ai_saldiri_veri import json_yukle

def roe_denetle(roe, aday_testler):
    return {
        "kapsam_id": roe["kapsam_id"],
        "izinli_testler": [t["test_id"] for t in aday_testler],
        "engellenen_testler": [],
        "ihlal_sayilari": {
            "hedef-kapsam-disi": 0,
            "ucuncu-taraf-api-yasak": 0,
            "hiz-limiti-asimi": 0,
            "yasak-kategori": 0,
            "saklama-suresi-asimi": 0,
        },
    }

def sistem_anatomisi(mimari):
    return {
        "sistem_id": mimari["sistem_id"],
        "acik_yuzeyler": ["dogrudan-kullanici-girdisi"],
        "onaysiz_yuksek_yetkili_araclar": [],
        "kritik_gecisler": [],
    }

def kesif_yaniti_cozumle(gozlemler):
    return {
        "toplam_sorgu": len(gozlemler),
        "gecerli_sorgu": len(gozlemler),
        "hata_sayisi": 0,
        "gozlenen_katmanlar": {
            "rol-siniri": False,
            "arac-yuzeyi": False,
            "rag-yuzeyi": False,
            "bellek-yuzeyi": False,
        },
        "dogrulanan_katman_sayisi": 0,
    }

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_36 as deney
    deney.goster(roe_denetle, sistem_anatomisi, kesif_yaniti_cozumle)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-36")
```

```test
import ai_lab
import copy
from sandbox import ai_gercek_ai_saldiri_36 as D

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for ad in ("roe_denetle", "sistem_anatomisi", "kesif_yaniti_cozumle"):
    need(ad)

sorun = ai_lab.kod_denetimi(src, ("roe_referans", "anatomi_referans", "kesif_referans"))
ok(not sorun, "laboratuvar yamalanmamalı, referans işlevler çağrılmamalı")

def _test(tid="t1", hedef="lab://asistan", turu="yerel-model", hiz=30, kat="vekil", gun=14):
    return {"test_id": tid, "hedef": hedef, "hedef_turu": turu, "istek_dakika": hiz, "kategori": kat, "saklama_gun": gun}

ORNEK_ROE = {
    "kapsam_id": "ROE-1",
    "izinli_hedefler": ["lab://asistan", "lab://rag"],
    "ucuncu_taraf_api_izni": False,
    "maks_istek_dakika": 30,
    "kanit_saklama_gun": 14,
    "yasak_kategoriler": ["gercek-pii", "zararli-yuk"],
}
ORNEK_MIMARI = {
    "sistem_id": "SIS-1",
    "model": {"ad": "qwen3:4b", "erisim": "yerel"},
    "sistem_istemi": {"gizli_talimat_var": True, "rol_siniri": "sipariş asistanı"},
    "rag": {"aktif": True, "dis_kaynak_acik": True},
    "araclar": [
        {"ad": "siparis_oku", "yetki": "okuma", "onay_gerekli": False},
        {"ad": "iade_yaz", "yetki": "yazma", "onay_gerekli": False},
        {"ad": "kabuk", "yetki": "komut", "onay_gerekli": True},
    ],
    "bellek": {"kalici": True, "oturumlar_arasi_paylasim": True},
    "cikti_tuketici": {"tur": "html-render", "dogrudan_calistirma": True},
}

def _sinir_ve_sema_kontrol():
    try:
        adaylar = [
            _test("t1", "lab://asistan", "yerel-model", 30, "vekil", 14),
            _test("t2", "lab://dis", "ucuncu-taraf-api", 31, "gercek-pii", 15),
            _test("t3", "lab://rag", "ucuncu-taraf-api", 10, "vekil", 7),
        ]
        if roe_denetle(copy.deepcopy(ORNEK_ROE), copy.deepcopy(adaylar)) != D.roe_referans(ORNEK_ROE, adaylar):
            return False
        roe_api_acik = dict(ORNEK_ROE, ucuncu_taraf_api_izni=True, maks_istek_dakika=600, kanit_saklama_gun=90, yasak_kategoriler=[])
        if roe_denetle(roe_api_acik, [_test("t1", "lab://asistan", "ucuncu-taraf-api", 600, "vekil", 90)])["izinli_testler"] != ["t1"]:
            return False
        roe_min = dict(ORNEK_ROE, maks_istek_dakika=1, kanit_saklama_gun=1)
        if roe_denetle(roe_min, [_test("t1", "lab://asistan", "yerel-model", 1, "vekil", 1)])["izinli_testler"] != ["t1"]:
            return False
        if roe_denetle(ORNEK_ROE, [_test("t1", "lab://asistan", "yerel-model", 1000, "vekil", 365)])["engellenen_testler"][0]["ihlaller"] != ["hiz-limiti-asimi", "saklama-suresi-asimi"]:
            return False
        for b_roe, b_aday in [
            (None, []), ({}, []),
            (dict(ORNEK_ROE, kapsam_id=""), []), (dict(ORNEK_ROE, kapsam_id=1), []),
            (dict(ORNEK_ROE, izinli_hedefler=[]), []), (dict(ORNEK_ROE, izinli_hedefler=[""]), []),
            (dict(ORNEK_ROE, izinli_hedefler=[1]), []), (dict(ORNEK_ROE, izinli_hedefler="lab://a"), []),
            (dict(ORNEK_ROE, ucuncu_taraf_api_izni=1), []),
            (dict(ORNEK_ROE, maks_istek_dakika=0), []), (dict(ORNEK_ROE, maks_istek_dakika=601), []),
            (dict(ORNEK_ROE, maks_istek_dakika=True), []), (dict(ORNEK_ROE, maks_istek_dakika="30"), []),
            (dict(ORNEK_ROE, kanit_saklama_gun=0), []), (dict(ORNEK_ROE, kanit_saklama_gun=91), []),
            (dict(ORNEK_ROE, kanit_saklama_gun=True), []), (dict(ORNEK_ROE, kanit_saklama_gun="14"), []),
            (dict(ORNEK_ROE, yasak_kategoriler="pii"), []), (dict(ORNEK_ROE, yasak_kategoriler=[""]), []), (dict(ORNEK_ROE, yasak_kategoriler=[1]), []),
            (ORNEK_ROE, None), (ORNEK_ROE, "liste"), (ORNEK_ROE, [None]), (ORNEK_ROE, [{}]),
            (ORNEK_ROE, [_test("")]), (ORNEK_ROE, [_test(1)]), (ORNEK_ROE, [_test("a"), _test("a")]),
            (ORNEK_ROE, [_test("a", hedef="")]), (ORNEK_ROE, [_test("a", hedef=1)]),
            (ORNEK_ROE, [_test("a", turu="bulut")]),
            (ORNEK_ROE, [_test("a", hiz=0)]), (ORNEK_ROE, [_test("a", hiz=1001)]),
            (ORNEK_ROE, [_test("a", hiz=True)]), (ORNEK_ROE, [_test("a", hiz="10")]),
            (ORNEK_ROE, [_test("a", kat="")]), (ORNEK_ROE, [_test("a", kat=1)]),
            (ORNEK_ROE, [_test("a", gun=0)]), (ORNEK_ROE, [_test("a", gun=366)]),
            (ORNEK_ROE, [_test("a", gun=True)]), (ORNEK_ROE, [_test("a", gun="7")]),
            (ORNEK_ROE, [dict(_test("a"), fazla=1)]),
        ]:
            try:
                roe_denetle(b_roe, b_aday)
                return False
            except ValueError:
                pass

        sade = {
            "sistem_id": "SIS-SADE",
            "model": {"ad": "m", "erisim": "bulut-api"},
            "sistem_istemi": {"gizli_talimat_var": False, "rol_siniri": "genel"},
            "rag": {"aktif": False, "dis_kaynak_acik": False},
            "araclar": [],
            "bellek": {"kalici": False, "oturumlar_arasi_paylasim": False},
            "cikti_tuketici": {"tur": "duz-metin", "dogrudan_calistirma": True},
        }
        yalniz_bellek_cikti = dict(sade, bellek={"kalici": True, "oturumlar_arasi_paylasim": True}, cikti_tuketici={"tur": "sql-sorgusu", "dogrudan_calistirma": True})
        yalniz_rag_cikti = dict(sade, rag={"aktif": True, "dis_kaynak_acik": True}, cikti_tuketici={"tur": "kabuk-komutu", "dogrudan_calistirma": False})
        ic_rag_izole_bellek = dict(sade, rag={"aktif": True, "dis_kaynak_acik": False}, bellek={"kalici": True, "oturumlar_arasi_paylasim": False})
        onalti_arac = dict(sade, araclar=[{"ad": f"a{i}", "yetki": "komut" if i == 0 else "okuma", "onay_gerekli": False} for i in range(16)])
        rag_sade = dict(ORNEK_MIMARI, bellek={'kalici': False, 'oturumlar_arasi_paylasim': False})
        bellek_sade = dict(ORNEK_MIMARI, rag={'aktif': False, 'dis_kaynak_acik': False})
        ikisi_kapali = dict(ORNEK_MIMARI, rag={'aktif': False, 'dis_kaynak_acik': False}, bellek={'kalici': False, 'oturumlar_arasi_paylasim': False})
        for m in (ORNEK_MIMARI, sade, yalniz_bellek_cikti, yalniz_rag_cikti, ic_rag_izole_bellek, onalti_arac, rag_sade, bellek_sade, ikisi_kapali):
            if sistem_anatomisi(copy.deepcopy(m)) != D.anatomi_referans(m):
                return False
        for bm in [
            None, [], {},
            dict(ORNEK_MIMARI, sistem_id=""), dict(ORNEK_MIMARI, sistem_id=1),
            dict(ORNEK_MIMARI, model=None), dict(ORNEK_MIMARI, model={"ad": "m"}),
            dict(ORNEK_MIMARI, model={"ad": "", "erisim": "yerel"}), dict(ORNEK_MIMARI, model={"ad": 1, "erisim": "yerel"}),
            dict(ORNEK_MIMARI, model={"ad": "m", "erisim": "hibrit"}),
            dict(ORNEK_MIMARI, sistem_istemi=None), dict(ORNEK_MIMARI, sistem_istemi={"gizli_talimat_var": True}),
            dict(ORNEK_MIMARI, sistem_istemi={"gizli_talimat_var": 1, "rol_siniri": "x"}),
            dict(ORNEK_MIMARI, sistem_istemi={"gizli_talimat_var": True, "rol_siniri": ""}),
            dict(ORNEK_MIMARI, sistem_istemi={"gizli_talimat_var": True, "rol_siniri": 1}),
            dict(ORNEK_MIMARI, rag=None), dict(ORNEK_MIMARI, rag={"aktif": True}),
            dict(ORNEK_MIMARI, rag={"aktif": 1, "dis_kaynak_acik": False}), dict(ORNEK_MIMARI, rag={"aktif": True, "dis_kaynak_acik": 0}),
            dict(ORNEK_MIMARI, rag={"aktif": False, "dis_kaynak_acik": True}),
            dict(ORNEK_MIMARI, araclar="araclar"),
            dict(ORNEK_MIMARI, araclar=()),
            dict(ORNEK_MIMARI, araclar=[{"ad": f"a{i}", "yetki": "okuma", "onay_gerekli": True} for i in range(17)]),
            dict(ORNEK_MIMARI, araclar=[None]), dict(ORNEK_MIMARI, araclar=[{"ad": "a", "yetki": "okuma"}]),
            dict(ORNEK_MIMARI, araclar=[{"ad": "", "yetki": "okuma", "onay_gerekli": True}]),
            dict(ORNEK_MIMARI, araclar=[{"ad": 1, "yetki": "okuma", "onay_gerekli": True}]),
            dict(ORNEK_MIMARI, araclar=[{"ad": "a", "yetki": "okuma", "onay_gerekli": True}, {"ad": "a", "yetki": "yazma", "onay_gerekli": False}]),
            dict(ORNEK_MIMARI, araclar=[{"ad": "a", "yetki": "silme", "onay_gerekli": True}]),
            dict(ORNEK_MIMARI, araclar=[{"ad": "a", "yetki": "okuma", "onay_gerekli": 1}]),
            dict(ORNEK_MIMARI, bellek=None), dict(ORNEK_MIMARI, bellek={"kalici": True}),
            dict(ORNEK_MIMARI, bellek={"kalici": 1, "oturumlar_arasi_paylasim": False}), dict(ORNEK_MIMARI, bellek={"kalici": True, "oturumlar_arasi_paylasim": 0}),
            dict(ORNEK_MIMARI, bellek={"kalici": False, "oturumlar_arasi_paylasim": True}),
            dict(ORNEK_MIMARI, cikti_tuketici=None), dict(ORNEK_MIMARI, cikti_tuketici={"tur": "duz-metin"}),
            dict(ORNEK_MIMARI, cikti_tuketici={"tur": "markdown", "dogrudan_calistirma": False}),
            dict(ORNEK_MIMARI, cikti_tuketici={"tur": "duz-metin", "dogrudan_calistirma": 0}),
        ]:
            try:
                sistem_anatomisi(bm)
                return False
            except ValueError:
                pass

        gozlemler = [
            {"sorgu_id": "s1", "hedef_katman": "rol-siniri", "yanit": "Görev kapsamım yalnız İADE ve sipariş politikasıdır.", "durum": "tamam"},
            {"sorgu_id": "s2", "hedef_katman": "arac-yuzeyi", "yanit": "siparis_sorgula ve iade_olustur fonksiyonlarını kullanırım.", "durum": "tamam"},
            {"sorgu_id": "s3", "hedef_katman": "rag-yuzeyi", "yanit": "Bu konuda bilgi veremem.", "durum": "tamam"},
            {"sorgu_id": "s4", "hedef_katman": "bellek-yuzeyi", "yanit": "", "durum": "hata"},
        ]
        on_sorgu = [
            {"sorgu_id": f"q{i}", "hedef_katman": "rag-yuzeyi" if i < 5 else "bellek-yuzeyi", "yanit": "KB-2026 belge deposu ve kalıcı oturum geçmişi" if i == 9 else "merhaba", "durum": "tamam"}
            for i in range(10)
        ]
        tek_sorgu = [{"sorgu_id": "h1", "hedef_katman": "rag-yuzeyi", "yanit": "", "durum": "hata"}]
        if not kesif_yaniti_cozumle([{"sorgu_id": "ust", "hedef_katman": "arac-yuzeyi", "yanit": "TOOL", "durum": "tamam"}])["gozlenen_katmanlar"]["arac-yuzeyi"]:
            return False
        if (
            kesif_yaniti_cozumle(copy.deepcopy(gozlemler)) != D.kesif_referans(gozlemler)
            or kesif_yaniti_cozumle(copy.deepcopy(on_sorgu)) != D.kesif_referans(on_sorgu)
            or kesif_yaniti_cozumle(copy.deepcopy(tek_sorgu)) != D.kesif_referans(tek_sorgu)
        ):
            return False
        for bg in [
            None, "liste", [], [None], [{}],
            [{"sorgu_id": f"q{i}", "hedef_katman": "rol-siniri", "yanit": "x", "durum": "tamam"} for i in range(11)],
            [{"sorgu_id": "", "hedef_katman": "rol-siniri", "yanit": "x", "durum": "tamam"}],
            [{"sorgu_id": 1, "hedef_katman": "rol-siniri", "yanit": "x", "durum": "tamam"}],
            [{"sorgu_id": "a", "hedef_katman": "rol-siniri", "yanit": "x", "durum": "tamam"},
             {"sorgu_id": "a", "hedef_katman": "arac-yuzeyi", "yanit": "y", "durum": "tamam"}],
            [{"sorgu_id": "a", "hedef_katman": "ag-yuzeyi", "yanit": "x", "durum": "tamam"}],
            [{"sorgu_id": "a", "hedef_katman": "rol-siniri", "yanit": None, "durum": "tamam"}],
            [{"sorgu_id": "a", "hedef_katman": "rol-siniri", "yanit": 123, "durum": "hata"}],
            [{"sorgu_id": "a", "hedef_katman": "rol-siniri", "yanit": "", "durum": "tamam"}],
            [{"sorgu_id": "a", "hedef_katman": "rol-siniri", "yanit": "x", "durum": "beklemede"}],
            [{"sorgu_id": "a", "hedef_katman": "rol-siniri", "yanit": "x", "durum": "tamam", "ek": 1}],
        ]:
            try:
                kesif_yaniti_cozumle(bg)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(_sinir_ve_sema_kontrol(), "RoE, sistem anatomisi ve keşif çözümlemesi tüm sınır ve şema kurallarını geçti")

if not all(checks):
    stop()

try:
    r = D.deney(roe_denetle, sistem_anatomisi, kesif_yaniti_cozumle)
except Exception as e:
    ok(False, f"GERÇEK RO-E VE KEŞİF DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

for ad, deger in r["kontroller"].items():
    ok(deger, "gerçek deney: " + ad)

ai_lab.kanit_yaz("saldiri-36-red-team-metodoloji-i", {
    "kaynak": "gercek",
    "kabul": all(checks),
    "ders": "ai-saldiri-36",
    "ortam": r["ortam"],
    "ayarlar": r["ayarlar"],
    "deney": r,
    "ozet": r["ozet"],
})
o = r["ozet"]
ok(
    True,
    f"BULGU ({r['ortam']['model']['ad']}): izinli keşif çağrısı={r['ortam']['cagri_sayisi']}, "
    f"engellenen kapsam dışı test={len(r['roe_sonucu']['engellenen_testler'])}, "
    f"canlı doğrulanan katman sayısı={o['dogrulanan_katman_sayisi']}/4 ({o['gozlenen_katmanlar']}).",
)
```

```solution
import ai_lab

def roe_denetle(roe, aday_testler):
    ihlal_sirasi = (
        "hedef-kapsam-disi",
        "ucuncu-taraf-api-yasak",
        "hiz-limiti-asimi",
        "yasak-kategori",
        "saklama-suresi-asimi",
    )
    gerekli = {
        "kapsam_id",
        "izinli_hedefler",
        "ucuncu_taraf_api_izni",
        "maks_istek_dakika",
        "kanit_saklama_gun",
        "yasak_kategoriler",
    }
    if not isinstance(roe, dict) or not gerekli.issubset(roe):
        raise ValueError("roe şeması eksik")
    kid = roe["kapsam_id"]
    hedefler = roe["izinli_hedefler"]
    api_izni = roe["ucuncu_taraf_api_izni"]
    maks_hiz = roe["maks_istek_dakika"]
    maks_gun = roe["kanit_saklama_gun"]
    yasaklar = roe["yasak_kategoriler"]
    if not isinstance(kid, str) or not kid:
        raise ValueError("kapsam_id geçersiz")
    if not isinstance(hedefler, list) or not hedefler or any(not isinstance(h, str) or not h for h in hedefler):
        raise ValueError("izinli_hedefler geçersiz")
    if not isinstance(api_izni, bool):
        raise ValueError("ucuncu_taraf_api_izni bool olmalı")
    if isinstance(maks_hiz, bool) or not isinstance(maks_hiz, int) or not 1 <= maks_hiz <= 600:
        raise ValueError("maks_istek_dakika geçersiz")
    if isinstance(maks_gun, bool) or not isinstance(maks_gun, int) or not 1 <= maks_gun <= 90:
        raise ValueError("kanit_saklama_gun geçersiz")
    if not isinstance(yasaklar, list) or any(not isinstance(y, str) or not y for y in yasaklar):
        raise ValueError("yasak_kategoriler geçersiz")
    if not isinstance(aday_testler, list):
        raise ValueError("aday_testler liste olmalı")

    hedef_kumesi = set(hedefler)
    yasak_kumesi = set(yasaklar)
    izinli_testler = []
    engellenen_testler = []
    ihlal_sayilari = {k: 0 for k in ihlal_sirasi}
    gorulen = set()

    for t in aday_testler:
        if not isinstance(t, dict) or set(t) != {"test_id", "hedef", "hedef_turu", "istek_dakika", "kategori", "saklama_gun"}:
            raise ValueError("aday test şeması geçersiz")
        tid = t["test_id"]
        hedef = t["hedef"]
        hturu = t["hedef_turu"]
        hiz = t["istek_dakika"]
        kat = t["kategori"]
        gun = t["saklama_gun"]
        if not isinstance(tid, str) or not tid or tid in gorulen:
            raise ValueError("test_id geçersiz")
        if not isinstance(hedef, str) or not hedef:
            raise ValueError("hedef geçersiz")
        if hturu not in ("yerel-model", "ucuncu-taraf-api"):
            raise ValueError("hedef_turu geçersiz")
        if isinstance(hiz, bool) or not isinstance(hiz, int) or not 1 <= hiz <= 1000:
            raise ValueError("istek_dakika geçersiz")
        if not isinstance(kat, str) or not kat:
            raise ValueError("kategori geçersiz")
        if isinstance(gun, bool) or not isinstance(gun, int) or not 1 <= gun <= 365:
            raise ValueError("saklama_gun geçersiz")
        gorulen.add(tid)

        ihlaller = []
        if hedef not in hedef_kumesi:
            ihlaller.append("hedef-kapsam-disi")
        if hturu == "ucuncu-taraf-api" and not api_izni:
            ihlaller.append("ucuncu-taraf-api-yasak")
        if hiz > maks_hiz:
            ihlaller.append("hiz-limiti-asimi")
        if kat in yasak_kumesi:
            ihlaller.append("yasak-kategori")
        if gun > maks_gun:
            ihlaller.append("saklama-suresi-asimi")

        if ihlaller:
            engellenen_testler.append({"test_id": tid, "ihlaller": ihlaller})
            for ih in ihlaller:
                ihlal_sayilari[ih] += 1
        else:
            izinli_testler.append(tid)

    return {
        "kapsam_id": kid,
        "izinli_testler": izinli_testler,
        "engellenen_testler": engellenen_testler,
        "ihlal_sayilari": ihlal_sayilari,
    }

def sistem_anatomisi(mimari):
    gerekli = {"sistem_id", "model", "sistem_istemi", "rag", "araclar", "bellek", "cikti_tuketici"}
    if not isinstance(mimari, dict) or not gerekli.issubset(mimari):
        raise ValueError("mimari şeması eksik")
    sid = mimari["sistem_id"]
    model = mimari["model"]
    sis = mimari["sistem_istemi"]
    rag = mimari["rag"]
    araclar = mimari["araclar"]
    bellek = mimari["bellek"]
    cikti = mimari["cikti_tuketici"]

    if not isinstance(sid, str) or not sid:
        raise ValueError("sistem_id geçersiz")
    if not isinstance(model, dict) or set(model) != {"ad", "erisim"}:
        raise ValueError("model şeması geçersiz")
    if not isinstance(model["ad"], str) or not model["ad"] or model["erisim"] not in ("yerel", "bulut-api"):
        raise ValueError("model alanları geçersiz")
    if not isinstance(sis, dict) or set(sis) != {"gizli_talimat_var", "rol_siniri"}:
        raise ValueError("sistem_istemi şeması geçersiz")
    if not isinstance(sis["gizli_talimat_var"], bool) or not isinstance(sis["rol_siniri"], str) or not sis["rol_siniri"]:
        raise ValueError("sistem_istemi alanları geçersiz")
    if not isinstance(rag, dict) or set(rag) != {"aktif", "dis_kaynak_acik"}:
        raise ValueError("rag şeması geçersiz")
    if not isinstance(rag["aktif"], bool) or not isinstance(rag["dis_kaynak_acik"], bool):
        raise ValueError("rag alanları bool olmalı")
    if not rag["aktif"] and rag["dis_kaynak_acik"]:
        raise ValueError("pasif rag dış kaynağa açık olamaz")
    if not isinstance(araclar, list) or len(araclar) > 16:
        raise ValueError("araclar 0..16 öğeli liste olmalı")

    arac_adlari = set()
    onaysiz_yuksek = []
    for a in araclar:
        if not isinstance(a, dict) or set(a) != {"ad", "yetki", "onay_gerekli"}:
            raise ValueError("araç şeması geçersiz")
        if not isinstance(a["ad"], str) or not a["ad"] or a["ad"] in arac_adlari:
            raise ValueError("araç adı geçersiz")
        if a["yetki"] not in ("okuma", "yazma", "komut") or not isinstance(a["onay_gerekli"], bool):
            raise ValueError("araç yetki/onay geçersiz")
        arac_adlari.add(a["ad"])
        if a["yetki"] in ("yazma", "komut") and not a["onay_gerekli"]:
            onaysiz_yuksek.append(a["ad"])

    if not isinstance(bellek, dict) or set(bellek) != {"kalici", "oturumlar_arasi_paylasim"}:
        raise ValueError("bellek şeması geçersiz")
    if not isinstance(bellek["kalici"], bool) or not isinstance(bellek["oturumlar_arasi_paylasim"], bool):
        raise ValueError("bellek alanları bool olmalı")
    if not bellek["kalici"] and bellek["oturumlar_arasi_paylasim"]:
        raise ValueError("kalıcı olmayan bellek paylaşılamaz")

    if not isinstance(cikti, dict) or set(cikti) != {"tur", "dogrudan_calistirma"}:
        raise ValueError("cikti_tuketici şeması geçersiz")
    if cikti["tur"] not in ("duz-metin", "html-render", "sql-sorgusu", "kabuk-komutu") or not isinstance(cikti["dogrudan_calistirma"], bool):
        raise ValueError("cikti_tuketici alanları geçersiz")

    yuzeyler = ["dogrudan-kullanici-girdisi"]
    if sis["gizli_talimat_var"]:
        yuzeyler.append("sistem-istemi-sizintisi")
    if rag["aktif"] and rag["dis_kaynak_acik"]:
        yuzeyler.append("dolayli-rag-enjeksiyonu")
    if araclar:
        yuzeyler.append("arac-cagrisi-manipulasyonu")
    if bellek["kalici"] and bellek["oturumlar_arasi_paylasim"]:
        yuzeyler.append("capraz-oturum-bellek-zehirlemesi")
    if cikti["tur"] != "duz-metin" and cikti["dogrudan_calistirma"]:
        yuzeyler.append("guvensiz-cikti-tuketimi")

    yk = set(yuzeyler)
    gecisler = []
    if "dolayli-rag-enjeksiyonu" in yk and onaysiz_yuksek:
        gecisler.append("rag->onaysiz-arac")
    if "capraz-oturum-bellek-zehirlemesi" in yk and onaysiz_yuksek:
        gecisler.append("paylasimli-bellek->onaysiz-arac")
    if "guvensiz-cikti-tuketimi" in yk and ("dolayli-rag-enjeksiyonu" in yk or "capraz-oturum-bellek-zehirlemesi" in yk):
        gecisler.append("dis-veri->dogrudan-cikti-calistirma")

    return {
        "sistem_id": sid,
        "acik_yuzeyler": sorted(yuzeyler),
        "onaysiz_yuksek_yetkili_araclar": sorted(onaysiz_yuksek),
        "kritik_gecisler": sorted(gecisler),
    }

def kesif_yaniti_cozumle(gozlemler):
    ipucu_haritasi = {
        "rol-siniri": ("sipariş", "siparis", "iade", "politika", "yalnız", "yalniz", "kapsam", "görev", "gorev", "asistan"),
        "arac-yuzeyi": ("siparis_sorgula", "iade_olustur", "araç", "arac", "tool", "fonksiyon", "sorgula"),
        "rag-yuzeyi": ("belge", "doküman", "dokuman", "kaynak", "indeks", "bilgi bankası", "bilgi bankasi", "kb-"),
        "bellek-yuzeyi": ("oturum", "bellek", "geçmiş", "gecmis", "hatırla", "hatirla", "kalıcı", "kalici"),
    }
    if not isinstance(gozlemler, list) or not 1 <= len(gozlemler) <= 10:
        raise ValueError("gozlemler 1..10 öğeli liste olmalı")
    gorulen = set()
    gecerli = 0
    hata = 0
    gozlenen = {k: False for k in ipucu_haritasi}

    for g in gozlemler:
        if not isinstance(g, dict) or set(g) != {"sorgu_id", "hedef_katman", "yanit", "durum"}:
            raise ValueError("gözlem şeması geçersiz")
        sid = g["sorgu_id"]
        katman = g["hedef_katman"]
        yanit = g["yanit"]
        durum = g["durum"]
        if not isinstance(sid, str) or not sid or sid in gorulen:
            raise ValueError("sorgu_id geçersiz")
        if katman not in ipucu_haritasi:
            raise ValueError("hedef_katman geçersiz")
        if not isinstance(yanit, str):
            raise ValueError("yanit str olmalı")
        if durum not in ("tamam", "hata"):
            raise ValueError("durum geçersiz")
        if durum == "tamam" and not yanit:
            raise ValueError("tamam durumunda yanit boş olamaz")
        gorulen.add(sid)

        if durum == "hata":
            hata += 1
        else:
            gecerli += 1
            kucuk = yanit.casefold()
            if any(ipucu in kucuk for ipucu in ipucu_haritasi[katman]):
                gozlenen[katman] = True

    return {
        "toplam_sorgu": len(gozlemler),
        "gecerli_sorgu": gecerli,
        "hata_sayisi": hata,
        "gozlenen_katmanlar": gozlenen,
        "dogrulanan_katman_sayisi": sum(1 for v in gozlenen.values() if v),
    }

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_36 as deney
    deney.goster(roe_denetle, sistem_anatomisi, kesif_yaniti_cozumle)
```

```hint
Önceki üç görevdeki çözümlerini birleştir; canlı deneyde önce RoE süzgeci çalışır ve yalnız izinli yerel sorgular modele gönderilir.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Kapsam belgesi deneyin girdisidir

RoE hangi hedefe, hangi vektörle ve hangi sınırda erişilebileceğini belirler. Sistem anatomisi model, retrieval, araç ve uygulama katmanlarını ayırır; modelin keşif yanıtı gerçek servis varlığını doğrulamaz. Gözlenen katmanla tahmini katmanı karıştırırsan saldırı planı doğrulanmamış altyapıya dayanır. Yerel denemede yalnız izinli kurgusal hedefler kullanılır.

| Yaygın yanlış | Doğru sınır |
|---|---|
| Recon yanıtı bütün mimariyi kanıtlar | Beyan, gözlem ve doğrulanan sınır ayrı kaydedilir. |

Sonraki bağlantı: ai-savunma-01. [Birincil kaynak](https://docs.ollama.com/api/chat). Kaynak mekanizmanın ilgili API veya yöntemini açıklar; bu labın başarı oranının kanıtı yerel ham koşudur.
:::
