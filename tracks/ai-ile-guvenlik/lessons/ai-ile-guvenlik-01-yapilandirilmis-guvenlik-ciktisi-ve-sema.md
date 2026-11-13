---
id: ai-ile-guvenlik-01
title: "Yapılandırılmış Güvenlik Çıktısı ve Şema Zorlama"
summary: Güvenlik analizinde yerel modelin serbest metin yanıtlarından JSON nesnesini ayıkla, katı şema/tip doğrulaması uygula ve yeniden deneme bütçesiyle deterministik çıktı kapısı kur.
timeout: 300
esleme: ai-ile-guvenlik-02, ai-saldiri-10
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et
Bir dil modelini zafiyet triyajı, kod denetimi veya SOC alarm analizi hattına bağladığında en büyük mühendislik sorunu **serbest metin karmaşasıdır**. Model bazen yanıtın başına açıklama ekler (`"Analiz tamamlandı: ```json ..."`), bazen `"satir_no": "42"` diyerek tam sayı yerine dizge döndürür, bazen de şemada olmayan fazladan alanlar uydurur (`ai-temel-14` ve `ai-saldiri-10` derslerindeki yapısal çıktı sınamalarını hatırla). Güvenlik otomasyonunda şemaya uymayan hiçbir model çıktısı doğrudan aşağı akış (downstream) araçlarına iletilemez.

| Gerçek araç / model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Yerel Ollama modelinin (`qwen3`) güvenlik istemine verdiği ham yanıtı, kod çitlerini (` ```json `) ve alan/tip sapmalarını | İlk üç görevde `model_yanit_adaylari.jsonl`, `sema_kurallari.json` ve `yeniden_deneme_kuyrugu.json` içindeki **sentetik** yanıt adaylarını; son görevde canlı `ai_lab.SohbetOturumu` ile JSON şema doğrulama deneyini | Şemaya tam uyan (`gecerli=True`) bir JSON çıktısının içerik olarak da doğru bir zafiyet tespiti olduğunu söyleyemez (halüsinasyon doğrulaması bir sonraki dersin konusudur) |

> [!GÜVENLİK]
> **Kapsam ve dürüstlük sınırı:** İlk üç görevdeki örnek dosyalar **sentetik** eğitim verisidir ve her çalıştırmada (`setup`) çalışma klasörüne yeniden kopyalanır (kalıcılık yoktur). Şema doğrulaması yalnızca yapısal bütünlüğü garanti eder; bulgunun doğruluğunu kanıtlamaz.
:::

::: anlat Güvenlik otomasyonunda gevşek ayrıştırma aşağı akış araçlarını kırar
Yapılandırılmış güvenlik çıktısı (structured output) hattı üç savunma halkasından oluşur:

1. **JSON Bloğu Ayıklama (`json_blogu_ayikla`):** Model yanıtı açıklama metni veya Markdown kod çiti içerse bile ilk `{` ile son `}` arasındaki bölge çıkarılır ve `json.loads` ile ayrıştırılır. Yüklenen değer bir `dict` değilse (`list`, `int` vb.) `"sozluk_degil"` hatasıyla reddedilir.
2. **Katı Şema ve Tip Doğrulama (`guvenlik_semasi_dogrula`):** Zorunlu alanların (`bulgu_id`, `kategori`, `ciddiyet`, `satir_no`, `kanit_var`) eksiksiz olduğu, fazladan alan (`fazla_alanlar`) bulunmadığı ve her alanın tipinin/kümesinin (`bool` ile `int` ayrımı dahil) doğru olduğu denetlenir.
3. **Yeniden Deneme Bütçesi (`sema_zorlama_kapisi`):** Model ilk denemede bozuk çıktı üretirse sonsuz döngüye girilmez; en fazla `max_deneme` kadar yanıt incelenir ve bütçe aşılırsa `"butce_asildi"` durumuyla güvenli şekilde durulur.
:::

::: anlat Bulguyu sınırlı ve doğrulanabilir yaz: şema geçerliliğini kanıt geçerliliğiyle karıştırma
Yapılandırılmış çıktı doğrulayıcısı raporlanırken iki sınır açıkça belirtilmelidir:

- **Tip katılığı (`isinstance(x, bool)` tuzağı):** Python'da `bool` sınıfı `int`'in alt sınıfıdır (`isinstance(True, int) == True`). Bu yüzden `satir_no` gibi tam sayı alanlarında `not isinstance(s, bool) and isinstance(s, int)` kontrolü zorunludur.
- **Şema ≠ Gerçeklik:** `guvenlik_semasi_dogrula` işlevinin `"gecerli": True` döndürmesi, yalnızca model çıktısının makine tarafından güvenle okunabileceğini gösterir; `satir_no` değerinin kaynak dosyada gerçekten var olduğunu doğrulamaz.
:::

::: tahmin Python'da bool ve int kalıtım tuzağını tahmin et
Aşağıdaki Python kodunun çıktısını tahmin et:

```python
adaylar = [12, "12", True, 0]
gecerli_satirlar = [
    x for x in adaylar
    if not isinstance(x, bool) and isinstance(x, int) and x >= 1
]
print(gecerli_satirlar)
```

???

```cikti
[12]
```

`"12"` dizge olduğu için, `True` ise `not isinstance(x, bool)` filtresine takıldığı için, `0` ise `x >= 1` koşulunu sağlamadığı için elenir; geriye yalnızca `[12]` kalır.
:::

::: gorev 1 · Modelin serbest metin yanıtından JSON sözlüğünü ayıkla
`json_blogu_ayikla(ham_yanit)` işlevini yaz.

Girdi kuralları:
- `ham_yanit`: boş olmayan (`strip()` sonrası dolu) `str`. Aksi hâlde `ValueError` yükselt.

Ayıklama kuralları:
- `metin = ham_yanit.strip()` içinde ilk `"{"` konumunu (`bas`) ve son `"}"` konumunu (`son`) bul.
- Eğer `"{"` veya `"}"` yoksa ya da `son < bas` ise:
  `{"ayiklandi": False, "veri": None, "hata": "json_bulunamadi"}` döndür.
- `metin[bas : son + 1]` dilimini `json.loads` ile ayrıştırmayı dene:
  - Ayrıştırma hata verirse: `{"ayiklandi": False, "veri": None, "hata": "gecersiz_json"}`
  - Ayrıştırılan değer bir `dict` değilse: `{"ayiklandi": False, "veri": None, "hata": "sozluk_degil"}`
  - Geçerli bir `dict` ise: `{"ayiklandi": True, "veri": yuklenen, "hata": None}` döndür.

```starter
import json
from ai_ile_guvenlik_veri import metin_yukle

ham_satirlar = metin_yukle("model_yanit_adaylari.jsonl").splitlines()

def json_blogu_ayikla(ham_yanit):
    # HATA: Yanıtın başındaki/sonundaki serbest metni ve kod çitlerini ayıklayamıyor.
    try:
        veri = json.loads(ham_yanit)
        return {"ayiklandi": True, "veri": veri, "hata": None}
    except Exception:
        return {"ayiklandi": False, "veri": None, "hata": "gecersiz_json"}

for s in ham_satirlar:
    if s.strip():
        kayit = json.loads(s)
        print(kayit["aday_id"], json_blogu_ayikla(kayit["ham_yanit"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-01")
```

```test
need("json_blogu_ayikla")

def sozlesme(fn):
    try:
        r1 = fn('Açıklama:\n```json\n{"bulgu_id": "B1", "satir_no": 5}\n```\nBitti.')
        if r1 != {"ayiklandi": True, "veri": {"bulgu_id": "B1", "satir_no": 5}, "hata": None}:
            return False
        r2 = fn("Hiç süslü parantez yok.")
        if r2 != {"ayiklandi": False, "veri": None, "hata": "json_bulunamadi"}:
            return False
        r3 = fn("Ters parantez } önce { sonra.")
        if r3 != {"ayiklandi": False, "veri": None, "hata": "json_bulunamadi"}:
            return False
        r4 = fn("Başlangıç {bozuk: json} son")
        if r4 != {"ayiklandi": False, "veri": None, "hata": "gecersiz_json"}:
            return False
        r5 = fn('{"ic": [1, 2]} değil ama dıştaki: ')
        if r5 != {"ayiklandi": True, "veri": {"ic": [1, 2]}, "hata": None}:
            return False
        if fn("Tek açılış { var")["hata"] != "json_bulunamadi":
            return False
        if fn("Tek kapanış } var")["hata"] != "json_bulunamadi":
            return False
        if fn("Boş küme: {}") != {"ayiklandi": True, "veri": {}, "hata": None}:
            return False
        for h in (None, 123, "", "   \n "):
            try:
                fn(h)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(json_blogu_ayikla), "JSON bloğu serbest metinden doğru ayıklanmalı ve hatalar sınıflandırılmalı")
def m_dogrudan_loads(m):
    import json
    try:
        return {"ayiklandi": True, "veri": json.loads(m), "hata": None}
    except Exception:
        return {"ayiklandi": False, "veri": None, "hata": "gecersiz_json"}
def m_hata_sabit(m):
    r = json_blogu_ayikla(m)
    return dict(r, hata="gecersiz_json" if not r["ayiklandi"] else None)
for ad, mutant in [("serbest metni ayıklamayan", m_dogrudan_loads), ("hata türünü sabit döndüren", m_hata_sabit)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
import json

def json_blogu_ayikla(ham_yanit):
    if not isinstance(ham_yanit, str) or not ham_yanit.strip():
        raise ValueError("ham yanıt boş olmayan string olmalı")
    metin = ham_yanit.strip()
    _, acilis, kalan = metin.partition("{")
    ic_metin, kapanis, _ = kalan.rpartition("}")
    if not acilis or not kapanis:
        return {"ayiklandi": False, "veri": None, "hata": "json_bulunamadi"}
    aday = "{" + ic_metin + "}"
    try:
        yuklenen = json.loads(aday)
    except Exception:
        return {"ayiklandi": False, "veri": None, "hata": "gecersiz_json"}
    if not isinstance(yuklenen, dict):
        return {"ayiklandi": False, "veri": None, "hata": "sozluk_degil"}
    return {"ayiklandi": True, "veri": yuklenen, "hata": None}
```

```hint
`metin.find("{")` ve `metin.rfind("}")` kullanarak ilk açılış ve son kapanış süslü parantezlerini bul; `bas == -1` veya `son == -1` veya `son < bas` durumunda `"json_bulunamadi"` döndür.
```
:::

::: gorev 2 · Güvenlik bulgusu şemasını ve alan tiplerini doğrula
`guvenlik_semasi_dogrula(aday_sozluk)` işlevini yaz.

Girdi kuralları:
- `aday_sozluk`: `dict` olmalıdır (değilse `ValueError` yükselt).

Şema kuralları:
- Zorunlu alanlar: `{"bulgu_id", "kategori", "ciddiyet", "satir_no", "kanit_var"}`
- `eksik_alanlar`: zorunlu olup `aday_sozluk` içinde bulunmayan anahtarlar (`sorted`).
- `fazla_alanlar`: `aday_sozluk` içinde olup zorunlu kümede bulunmayan anahtarlar (`sorted`).
- `tip_hatalari` (`sorted` liste; yalnızca sözlükte mevcut olan zorunlu alanlar için kontrol edilir):
  - `"bulgu_id"`: `str` değilse veya `strip()` sonrası boşsa `"bulgu_id"` ekle.
  - `"kategori"`: `("enjeksiyon", "yetki_atlama", "sir_sizintisi", "yapilandirma")` içinde değilse `"kategori"` ekle.
  - `"ciddiyet"`: `("dusuk", "orta", "yuksek", "kritik")` içinde değilse `"ciddiyet"` ekle.
  - `"satir_no"`: `bool` ise veya `int` değilse ya da `1`'den küçükse `"satir_no"` ekle.
  - `"kanit_var"`: `bool` değilse `"kanit_var"` ekle.
- `gecerli`: `eksik_alanlar`, `fazla_alanlar` ve `tip_hatalari` listelerinin üçü de boşsa `True`, aksi hâlde `False`.

```starter
from ai_ile_guvenlik_veri import json_yukle

kurallar = json_yukle("sema_kurallari.json")

def guvenlik_semasi_dogrula(aday_sozluk):
    # HATA: Fazla alanları ve bool/int tip kaymalarını kontrol etmiyor.
    eksik = sorted(set(kurallar["zorunlu_alanlar"]) - set(aday_sozluk.keys()))
    return {
        "gecerli": len(eksik) == 0,
        "eksik_alanlar": eksik,
        "fazla_alanlar": [],
        "tip_hatalari": [],
    }

print(guvenlik_semasi_dogrula({"bulgu_id": "BLG-1", "kategori": "enjeksiyon", "ciddiyet": "yuksek", "satir_no": "10", "kanit_var": True, "ek": 1}))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-01")
```

```test
need("guvenlik_semasi_dogrula")

TAM_ADAY = {
    "bulgu_id": "BLG-101",
    "kategori": "enjeksiyon",
    "ciddiyet": "yuksek",
    "satir_no": 1,
    "kanit_var": False,
}

def sozlesme(fn):
    try:
        if fn(dict(TAM_ADAY)) != {
            "gecerli": True,
            "eksik_alanlar": [],
            "fazla_alanlar": [],
            "tip_hatalari": [],
        }:
            return False

        r_eksik_fazla = fn({"bulgu_id": "B1", "kategori": "enjeksiyon", "fazla": 1, "z_ek": 2})
        if r_eksik_fazla != {
            "gecerli": False,
            "eksik_alanlar": ["ciddiyet", "kanit_var", "satir_no"],
            "fazla_alanlar": ["fazla", "z_ek"],
            "tip_hatalari": [],
        }:
            return False

        r_tipler = fn({
            "bulgu_id": "  ",
            "kategori": "bilinmeyen",
            "ciddiyet": "acil",
            "satir_no": 0,
            "kanit_var": 1,
        })
        if r_tipler != {
            "gecerli": False,
            "eksik_alanlar": [],
            "fazla_alanlar": [],
            "tip_hatalari": ["bulgu_id", "ciddiyet", "kanit_var", "kategori", "satir_no"],
        }:
            return False

        if fn(dict(TAM_ADAY, satir_no=True))["tip_hatalari"] != ["satir_no"]:
            return False
        if fn(dict(TAM_ADAY, satir_no="10"))["tip_hatalari"] != ["satir_no"]:
            return False
        if fn(dict(TAM_ADAY, bulgu_id=10))["tip_hatalari"] != ["bulgu_id"]:
            return False
        if fn({}) != {"gecerli": False, "eksik_alanlar": ["bulgu_id", "ciddiyet", "kanit_var", "kategori", "satir_no"], "fazla_alanlar": [], "tip_hatalari": []}:
            return False
        if fn(dict(TAM_ADAY, ek=1)) != {"gecerli": False, "eksik_alanlar": [], "fazla_alanlar": ["ek"], "tip_hatalari": []}:
            return False

        for h in (None, [], "sozluk", 12):
            try:
                fn(h)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(guvenlik_semasi_dogrula), "zorunlu/fazla alanlar ve tip kuralları eksiksiz doğrulanmalı")
def m_fazla_izin(s):
    r = guvenlik_semasi_dogrula(s)
    return dict(r, fazla_alanlar=[], gecerli=not r["eksik_alanlar"] and not r["tip_hatalari"])
def m_bool_satir(s):
    r = guvenlik_semasi_dogrula(s)
    if s.get("satir_no") is True:
        return dict(r, tip_hatalari=[], gecerli=True)
    return r
for ad, mutant in [("fazla alanları yok sayan", m_fazla_izin), ("satir_no için bool kabul eden", m_bool_satir)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
ZORUNLU_ALANLAR = ("bulgu_id", "kategori", "ciddiyet", "satir_no", "kanit_var")
GECERLI_KATEGORILER = ("enjeksiyon", "yetki_atlama", "sir_sizintisi", "yapilandirma")
GECERLI_CIDDIYETLER = ("dusuk", "orta", "yuksek", "kritik")

def guvenlik_semasi_dogrula(aday_sozluk):
    if not isinstance(aday_sozluk, dict):
        raise ValueError("aday sözlük dict olmalı")
    beklenen = set(ZORUNLU_ALANLAR)
    mevcut = set(aday_sozluk.keys())
    eksik_alanlar = sorted(beklenen - mevcut)
    fazla_alanlar = sorted(mevcut - beklenen)
    tip_hatalari = []

    if "bulgu_id" in aday_sozluk:
        b = aday_sozluk["bulgu_id"]
        if not isinstance(b, str) or not b.strip():
            tip_hatalari.append("bulgu_id")
    if "kategori" in aday_sozluk:
        if aday_sozluk["kategori"] not in GECERLI_KATEGORILER:
            tip_hatalari.append("kategori")
    if "ciddiyet" in aday_sozluk:
        if aday_sozluk["ciddiyet"] not in GECERLI_CIDDIYETLER:
            tip_hatalari.append("ciddiyet")
    if "satir_no" in aday_sozluk:
        s = aday_sozluk["satir_no"]
        if isinstance(s, bool) or not isinstance(s, int) or s < 1:
            tip_hatalari.append("satir_no")
    if "kanit_var" in aday_sozluk:
        if not isinstance(aday_sozluk["kanit_var"], bool):
            tip_hatalari.append("kanit_var")

    tip_hatalari.sort()
    gecerli = not eksik_alanlar and not fazla_alanlar and not tip_hatalari
    return {
        "gecerli": gecerli,
        "eksik_alanlar": eksik_alanlar,
        "fazla_alanlar": fazla_alanlar,
        "tip_hatalari": tip_hatalari,
    }
```

```hint
`satir_no` kontrolünde `isinstance(s, bool) or not isinstance(s, int) or s < 1` koşulunu kullan.
```
:::

::: gorev 3 · Yeniden deneme bütçeli şema zorlama kapısı kur
`sema_zorlama_kapisi(deneme_yanitlari, max_deneme=3)` işlevini yaz.

Girdi kuralları:
- `deneme_yanitlari`: her öğesi boş olmayan `str` olan boş olmayan `list`.
- `max_deneme`: `bool` olmayan pozitif (`1` veya daha büyük) `int`.
- Geçersiz girdi veya şemada `ValueError` yükselt.

İşleyiş kuralları:
- `deneme_yanitlari[:max_deneme]` dilimindeki yanıtları sırayla (`1`'den başlayarak) incele:
  1. Yanıtı `json_blogu_ayikla` mantığıyla ayıkla. Ayıklanamazsa `son_hata = ayiklama["hata"]` ata ve sonraki denemeye geç.
  2. Ayıklanan sözlüğü `guvenlik_semasi_dogrula` mantığıyla doğrula.
  3. Eğer `gecerli == True` ise döngüyü hemen durdur ve şu sözlüğü döndür:
     `{"durum": "kabul", "kullanilan_deneme": idx, "cikti": ayiklama["veri"], "son_hata": None}`
  4. Eğer `gecerli == False` ise `son_hata = "sema_ihlali"` ata ve sonraki denemeye geç.
- İncelenen `len(deneme_yanitlari[:max_deneme])` denemenin hiçbirinde geçerli çıktı bulunamazsa:
  `{"durum": "butce_asildi", "kullanilan_deneme": len(deneme_yanitlari[:max_deneme]), "cikti": None, "son_hata": son_hata}` döndür.

```starter
from ai_ile_guvenlik_veri import json_yukle

kuyruk = json_yukle("yeniden_deneme_kuyrugu.json")

def sema_zorlama_kapisi(deneme_yanitlari, max_deneme=3):
    # HATA: max_deneme sınırını uygulamıyor ve şema doğrulaması yapmadan ilk yanıtı kabul ediyor.
    return {
        "durum": "kabul",
        "kullanilan_deneme": 1,
        "cikti": None,
        "son_hata": None,
    }

for g in kuyruk["gorevler"]:
    print(g["gorev_id"], sema_zorlama_kapisi(g["deneme_yanitlari"], kuyruk["max_deneme"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-01")
```

```test
import json

need("sema_zorlama_kapisi")

GECERLI_JSON = json.dumps({
    "bulgu_id": "BLG-9",
    "kategori": "yetki_atlama",
    "ciddiyet": "kritik",
    "satir_no": 8,
    "kanit_var": True,
})

BOZUK_SEMA = json.dumps({
    "bulgu_id": "BLG-9",
    "kategori": "yanlis_kat",
    "ciddiyet": "kritik",
    "satir_no": 8,
    "kanit_var": True,
})

def sozlesme(fn):
    try:
        r_kabul = fn(["Açıklama var JSON yok", BOZUK_SEMA, GECERLI_JSON], 3)
        if r_kabul != {
            "durum": "kabul",
            "kullanilan_deneme": 3,
            "cikti": json.loads(GECERLI_JSON),
            "son_hata": None,
        }:
            return False

        r_butce = fn(["JSON yok", BOZUK_SEMA, GECERLI_JSON], 2)
        if r_butce != {
            "durum": "butce_asildi",
            "kullanilan_deneme": 2,
            "cikti": None,
            "son_hata": "sema_ihlali",
        }:
            return False

        r_json_yok = fn(["Bozuk {json", "Parantez yok"], 3)
        if r_json_yok != {
            "durum": "butce_asildi",
            "kullanilan_deneme": 2,
            "cikti": None,
            "son_hata": "json_bulunamadi",
        }:
            return False

        r_gecersiz = fn(["{bozuk json}"], 1)
        if r_gecersiz["son_hata"] != "gecersiz_json" or r_gecersiz["durum"] != "butce_asildi":
            return False

        r_varsayilan = fn(["JSON yok", "Yine yok", "Üçüncü yok", GECERLI_JSON])
        if r_varsayilan["durum"] != "butce_asildi" or r_varsayilan["kullanilan_deneme"] != 3:
            return False

        if fn([json.dumps(dict(json.loads(GECERLI_JSON), satir_no=1))], 1)["durum"] != "kabul":
            return False
        for kotu_alan in (
            dict(json.loads(GECERLI_JSON), bulgu_id=" "),
            dict(json.loads(GECERLI_JSON), bulgu_id=12),
            dict(json.loads(GECERLI_JSON), ciddiyet="yanlis"),
            dict(json.loads(GECERLI_JSON), satir_no=0),
            dict(json.loads(GECERLI_JSON), satir_no=True),
            dict(json.loads(GECERLI_JSON), satir_no="8"),
            dict(json.loads(GECERLI_JSON), kanit_var=1),
        ):
            if fn([json.dumps(kotu_alan)], 1)["durum"] != "butce_asildi":
                return False

        if fn(["Tek { parantez"], 1)["son_hata"] != "json_bulunamadi":
            return False
        if fn(["Tek } parantez"], 1)["son_hata"] != "json_bulunamadi":
            return False
        if fn(["Ters } ve {"], 1)["son_hata"] != "json_bulunamadi":
            return False
        if fn([json.dumps({"bulgu_id": "BLG-9"})], 1) != {"durum": "butce_asildi", "kullanilan_deneme": 1, "cikti": None, "son_hata": "sema_ihlali"}:
            return False
        if fn([json.dumps(dict(json.loads(GECERLI_JSON), ek=1))], 1) != {"durum": "butce_asildi", "kullanilan_deneme": 1, "cikti": None, "son_hata": "sema_ihlali"}:
            return False

        hatalilar = [
            (None, 3),
            ([], 3),
            ("liste_degil", 3),
            ([""], 3),
            (["   "], 3),
            ([123], 3),
            ([GECERLI_JSON], 0),
            ([GECERLI_JSON], -1),
            ([GECERLI_JSON], True),
            ([GECERLI_JSON], "3"),
        ]
        for d_in, m_in in hatalilar:
            try:
                fn(d_in, m_in)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(sema_zorlama_kapisi), "şema zorlama kapısı yeniden deneme bütçesini ve hata nedenlerini doğru yönetmeli")
def m_sinirsiz(d, m=3):
    return sema_zorlama_kapisi(d, 99)
def m_hata_atlayan(d, m=3):
    r = sema_zorlama_kapisi(d, m)
    return dict(r, son_hata=None)
for ad, mutant in [("bütçe sınırını aşan", m_sinirsiz), ("son hatayı silen", m_hata_atlayan)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
import json

ZORUNLU_ALANLAR = ("bulgu_id", "kategori", "ciddiyet", "satir_no", "kanit_var")
GECERLI_KATEGORILER = ("enjeksiyon", "yetki_atlama", "sir_sizintisi", "yapilandirma")
GECERLI_CIDDIYETLER = ("dusuk", "orta", "yuksek", "kritik")

def _ayikla(ham_yanit):
    metin = ham_yanit.strip()
    _, acilis, kalan = metin.partition("{")
    ic_metin, kapanis, _ = kalan.rpartition("}")
    if not acilis or not kapanis:
        return {"ayiklandi": False, "veri": None, "hata": "json_bulunamadi"}
    try:
        yuklenen = json.loads("{" + ic_metin + "}")
    except Exception:
        return {"ayiklandi": False, "veri": None, "hata": "gecersiz_json"}
    if not isinstance(yuklenen, dict):
        return {"ayiklandi": False, "veri": None, "hata": "sozluk_degil"}
    return {"ayiklandi": True, "veri": yuklenen, "hata": None}

def _dogrula(aday_sozluk):
    beklenen = set(ZORUNLU_ALANLAR)
    mevcut = set(aday_sozluk.keys())
    if beklenen != mevcut:
        return False
    b = aday_sozluk["bulgu_id"]
    if not isinstance(b, str) or not b.strip():
        return False
    if aday_sozluk["kategori"] not in GECERLI_KATEGORILER:
        return False
    if aday_sozluk["ciddiyet"] not in GECERLI_CIDDIYETLER:
        return False
    s = aday_sozluk["satir_no"]
    if isinstance(s, bool) or not isinstance(s, int) or s < 1:
        return False
    if not isinstance(aday_sozluk["kanit_var"], bool):
        return False
    return True

def sema_zorlama_kapisi(deneme_yanitlari, max_deneme=3):
    if not isinstance(deneme_yanitlari, list) or not deneme_yanitlari:
        raise ValueError("deneme yanıtları boş olmayan liste olmalı")
    if isinstance(max_deneme, bool) or not isinstance(max_deneme, int) or max_deneme < 1:
        raise ValueError("azami deneme pozitif tam sayı olmalı")
    for y in deneme_yanitlari:
        if not isinstance(y, str) or not y.strip():
            raise ValueError("her deneme yanıtı boş olmayan string olmalı")

    incelenen = deneme_yanitlari[:max_deneme]
    son_hata = "belirsiz"
    for idx, ham in enumerate(incelenen, start=1):
        ayiklama = _ayikla(ham)
        if not ayiklama["ayiklandi"]:
            son_hata = ayiklama["hata"]
            continue
        if _dogrula(ayiklama["veri"]):
            return {
                "durum": "kabul",
                "kullanilan_deneme": idx,
                "cikti": ayiklama["veri"],
                "son_hata": None,
            }
        son_hata = "sema_ihlali"

    return {
        "durum": "butce_asildi",
        "kullanilan_deneme": len(incelenen),
        "cikti": None,
        "son_hata": son_hata,
    }
```

```hint
`deneme_yanitlari[:max_deneme]` üzerinde dönerken ilk geçerli şemada `durum="kabul"` ile çık; döngü biterse `kullanilan_deneme=len(incelenen)` ve `durum="butce_asildi"` döndür.
```
:::

::: gorev Gerçek deney · Yerel modelden güvenlik bulgusu JSON şeması üretme ve doğrulama kapısı
Önceki üç görevde yazdığın `json_blogu_ayikla`, `guvenlik_semasi_dogrula` ve `sema_zorlama_kapisi` işlevlerini bu adımda birleştir.

Canlı deneyde:
1. Yerel Ollama modelinden (`ai_lab.SohbetOturumu`) örnek bir SQL birleştirme satırı için yapılandırılmış JSON bulgusu istenir.
2. Modelin canlı yanıtı `json_blogu_ayikla` ile ayrıştırılır.
3. Bozuk ilk deneme ve canlı yanıt `sema_zorlama_kapisi` üzerinden geçirilerek şema doğrulaması ve yeniden deneme bütçesi doğrulanır.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def json_blogu_ayikla(ham_yanit):
    return {}

def guvenlik_semasi_dogrula(aday_sozluk):
    return {}

def sema_zorlama_kapisi(deneme_yanitlari, max_deneme=3):
    return {}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_ile_guvenlik_01 as deney
    deney.goster(json_blogu_ayikla, guvenlik_semasi_dogrula, sema_zorlama_kapisi)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-01")
```

```test
import ai_lab
from sandbox import ai_gercek_ai_ile_guvenlik_01 as D

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for ad in ("json_blogu_ayikla", "guvenlik_semasi_dogrula", "sema_zorlama_kapisi"):
    need(ad)

sorun = ai_lab.kod_denetimi(
    src,
    ("json_blogu_ayikla_referans", "guvenlik_semasi_dogrula_referans", "sema_zorlama_kapisi_referans"),
)
ok(not sorun, "laboratuvar yamalanmamalı, referans işlevler çağrılmamalı")

SENTETIK = 'Yanıt: {"bulgu_id": "B1", "kategori": "enjeksiyon", "ciddiyet": "yuksek", "satir_no": 1, "kanit_var": true}'
ok(json_blogu_ayikla(SENTETIK) == D.json_blogu_ayikla_referans(SENTETIK), "sentetik ön kontrol: JSON ayıklama referansla uyumlu")
def _on_sozlesme():
    try:
        for h in ("", "   ", None, 5):
            try: json_blogu_ayikla(h); return False
            except ValueError: pass
        if json_blogu_ayikla("yok") != {"ayiklandi": False, "veri": None, "hata": "json_bulunamadi"}: return False
        if json_blogu_ayikla("Tek { var") != {"ayiklandi": False, "veri": None, "hata": "json_bulunamadi"}: return False
        if json_blogu_ayikla("Ters } ve {") != {"ayiklandi": False, "veri": None, "hata": "json_bulunamadi"}: return False
        if json_blogu_ayikla("{bozuk}") != {"ayiklandi": False, "veri": None, "hata": "gecersiz_json"}: return False
        if json_blogu_ayikla("{1:2}" )["ayiklandi"] is not False: return False
        tam = {"bulgu_id": "B1", "kategori": "enjeksiyon", "ciddiyet": "yuksek", "satir_no": 1, "kanit_var": True}
        if guvenlik_semasi_dogrula(tam) != {"gecerli": True, "eksik_alanlar": [], "fazla_alanlar": [], "tip_hatalari": []}: return False
        if guvenlik_semasi_dogrula({"bulgu_id": " ", "kategori": "x", "ciddiyet": "y", "satir_no": 0, "kanit_var": 1, "ek": 2}) != {"gecerli": False, "eksik_alanlar": [], "fazla_alanlar": ["ek"], "tip_hatalari": ["bulgu_id", "ciddiyet", "kanit_var", "kategori", "satir_no"]}: return False
        if guvenlik_semasi_dogrula(dict(tam, satir_no=True)) != {"gecerli": False, "eksik_alanlar": [], "fazla_alanlar": [], "tip_hatalari": ["satir_no"]}: return False
        if guvenlik_semasi_dogrula(dict(tam, satir_no="1")) != {"gecerli": False, "eksik_alanlar": [], "fazla_alanlar": [], "tip_hatalari": ["satir_no"]}: return False
        if guvenlik_semasi_dogrula(dict(tam, bulgu_id=12)) != {"gecerli": False, "eksik_alanlar": [], "fazla_alanlar": [], "tip_hatalari": ["bulgu_id"]}: return False
        if guvenlik_semasi_dogrula(dict(tam, ek=1)) != {"gecerli": False, "eksik_alanlar": [], "fazla_alanlar": ["ek"], "tip_hatalari": []}: return False
        if guvenlik_semasi_dogrula({}) != {"gecerli": False, "eksik_alanlar": ["bulgu_id", "ciddiyet", "kanit_var", "kategori", "satir_no"], "fazla_alanlar": [], "tip_hatalari": []}: return False
        try: guvenlik_semasi_dogrula([]); return False
        except ValueError: pass
        import json as _j
        g_str = _j.dumps(tam)
        if sema_zorlama_kapisi(["yok", "{bozuk}", g_str]) != {"durum": "kabul", "kullanilan_deneme": 3, "cikti": tam, "son_hata": None}: return False
        if sema_zorlama_kapisi(["yok", "yok", "yok", g_str]) != {"durum": "butce_asildi", "kullanilan_deneme": 3, "cikti": None, "son_hata": "json_bulunamadi"}: return False
        if sema_zorlama_kapisi(["yok", g_str], 1) != {"durum": "butce_asildi", "kullanilan_deneme": 1, "cikti": None, "son_hata": "json_bulunamadi"}: return False
        if sema_zorlama_kapisi(["{\"a\":1}"], 1) != {"durum": "butce_asildi", "kullanilan_deneme": 1, "cikti": None, "son_hata": "sema_ihlali"}: return False
        for a, m in [([], 1), (None, 1), ("metin", 1), (123, 1), ([""], 1), (["   "], 1), ([1], 1), ([g_str, "   "], 1), ([g_str, 1], 1), ([g_str], 0), ([g_str], -1), ([g_str], True), ([g_str], "1")]:
            try: sema_zorlama_kapisi(a, m); return False
            except ValueError: pass
        return True
    except Exception:
        return False
ok(_on_sozlesme(), "sentetik ön kontrol: şema doğrulama ve bütçe kapısı sınırları tam")

if not all(checks):
    stop()

try:
    r = D.deney(json_blogu_ayikla, guvenlik_semasi_dogrula, sema_zorlama_kapisi)
except Exception as e:
    ok(False, f"GERÇEK ŞEMA ZORLAMA DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

for ad, deger in r["kontroller"].items():
    ok(deger, "gerçek deney: " + ad)

ai_lab.kanit_yaz("ile-guvenlik-01-sema", {
    "kaynak": "gercek",
    "kabul": all(checks),
    "ders": "ai-ile-guvenlik-01",
    "ortam": r["ortam"],
    "ayarlar": r["ayarlar"],
    "deney": r,
    "ozet": r["ozet"],
})
o = r["ozet"]
ok(
    True,
    f"BULGU ({o['model']}): ayıklandı={o['canli_json_ayiklandi']}, durum={o['kapi_durumu']}, deneme={o['kullanilan_deneme']}, kategori={o['kategori']}.",
)
```

```solution
import json
import ai_lab

ZORUNLU_ALANLAR = ("bulgu_id", "kategori", "ciddiyet", "satir_no", "kanit_var")
GECERLI_KATEGORILER = ("enjeksiyon", "yetki_atlama", "sir_sizintisi", "yapilandirma")
GECERLI_CIDDIYETLER = ("dusuk", "orta", "yuksek", "kritik")

def json_blogu_ayikla(ham_yanit):
    if not isinstance(ham_yanit, str) or not ham_yanit.strip():
        raise ValueError("ham yanıt boş olmayan string olmalı")
    metin = ham_yanit.strip()
    _, acilis, kalan = metin.partition("{")
    ic_metin, kapanis, _ = kalan.rpartition("}")
    if not acilis or not kapanis:
        return {"ayiklandi": False, "veri": None, "hata": "json_bulunamadi"}
    aday = "{" + ic_metin + "}"
    try:
        yuklenen = json.loads(aday)
    except Exception:
        return {"ayiklandi": False, "veri": None, "hata": "gecersiz_json"}
    if not isinstance(yuklenen, dict):
        return {"ayiklandi": False, "veri": None, "hata": "sozluk_degil"}
    return {"ayiklandi": True, "veri": yuklenen, "hata": None}

def guvenlik_semasi_dogrula(aday_sozluk):
    if not isinstance(aday_sozluk, dict):
        raise ValueError("aday sözlük dict olmalı")
    beklenen = set(ZORUNLU_ALANLAR)
    mevcut = set(aday_sozluk.keys())
    eksik_alanlar = sorted(beklenen - mevcut)
    fazla_alanlar = sorted(mevcut - beklenen)
    tip_hatalari = []

    if "bulgu_id" in aday_sozluk:
        b = aday_sozluk["bulgu_id"]
        if not isinstance(b, str) or not b.strip():
            tip_hatalari.append("bulgu_id")
    if "kategori" in aday_sozluk:
        if aday_sozluk["kategori"] not in GECERLI_KATEGORILER:
            tip_hatalari.append("kategori")
    if "ciddiyet" in aday_sozluk:
        if aday_sozluk["ciddiyet"] not in GECERLI_CIDDIYETLER:
            tip_hatalari.append("ciddiyet")
    if "satir_no" in aday_sozluk:
        s = aday_sozluk["satir_no"]
        if isinstance(s, bool) or not isinstance(s, int) or s < 1:
            tip_hatalari.append("satir_no")
    if "kanit_var" in aday_sozluk:
        if not isinstance(aday_sozluk["kanit_var"], bool):
            tip_hatalari.append("kanit_var")

    tip_hatalari.sort()
    gecerli = not eksik_alanlar and not fazla_alanlar and not tip_hatalari
    return {
        "gecerli": gecerli,
        "eksik_alanlar": eksik_alanlar,
        "fazla_alanlar": fazla_alanlar,
        "tip_hatalari": tip_hatalari,
    }

def sema_zorlama_kapisi(deneme_yanitlari, max_deneme=3):
    if not isinstance(deneme_yanitlari, list) or not deneme_yanitlari:
        raise ValueError("deneme yanıtları boş olmayan liste olmalı")
    if isinstance(max_deneme, bool) or not isinstance(max_deneme, int) or max_deneme < 1:
        raise ValueError("azami deneme pozitif tam sayı olmalı")
    for y in deneme_yanitlari:
        if not isinstance(y, str) or not y.strip():
            raise ValueError("her deneme yanıtı boş olmayan string olmalı")

    incelenen = deneme_yanitlari[:max_deneme]
    son_hata = "belirsiz"
    for idx, ham in enumerate(incelenen, start=1):
        ayiklama = json_blogu_ayikla(ham)
        if not ayiklama["ayiklandi"]:
            son_hata = ayiklama["hata"]
            continue
        dogrulama = guvenlik_semasi_dogrula(ayiklama["veri"])
        if dogrulama["gecerli"]:
            return {
                "durum": "kabul",
                "kullanilan_deneme": idx,
                "cikti": ayiklama["veri"],
                "son_hata": None,
            }
        son_hata = "sema_ihlali"

    return {
        "durum": "butce_asildi",
        "kullanilan_deneme": len(incelenen),
        "cikti": None,
        "son_hata": son_hata,
    }

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_ile_guvenlik_01 as deney
    deney.goster(json_blogu_ayikla, guvenlik_semasi_dogrula, sema_zorlama_kapisi)
```

```hint
Önceki üç görevdeki `json_blogu_ayikla`, `guvenlik_semasi_dogrula` ve `sema_zorlama_kapisi` çözümlerini birleştir.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Şema üretimi ile şema doğrulaması ayrıdır

Modelin JSON görünümünde metin döndürmesi katı şemaya uyduğu anlamına gelmez. Önce serbest metinden aday nesne ayrıştırılır, sonra gerekli alanlar ve türler hostta doğrulanır. Yeniden deneme bütçesi tükenirse şema uydurulmaz; başarısızlık görünür kalır. Geçerli şema bulgunun gerçekliğini kanıtlamaz; kanıt eşleme sonraki katmandır.

| Yaygın yanlış | Kontrolün gösterdiği |
|---|---|
| JSON parse edildiğinde bulgu doğrudur | Yapı, tür ve kaynak kanıtı ayrı denetlenir. |

Sonraki bağlantı: ai-ile-guvenlik-02. [Birincil kaynak](https://docs.ollama.com/api/chat). Kaynak ilgili araç veya yöntemi açıklar; labın gerçek sonucu ham kanıt kaydındadır.
:::
