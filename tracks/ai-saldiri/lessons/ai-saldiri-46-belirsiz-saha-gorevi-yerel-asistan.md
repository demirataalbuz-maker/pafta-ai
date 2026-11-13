---
id: ai-saldiri-46
title: "Belirsiz Saha Görevi: Açıklı Yerel Asistanı Keşfet, Kanıtla ve Yamala"
summary: Açık sınıfı önceden söylenmeyen çok bileşenli yerel asistanda oturum izlerinden kanıtlı zayıflıkları keşfet, yapılandırma riskini derecelendir ve normal işlevi bozmadan güvenlik yaması doğrula.
timeout: 300
esleme: ai-savunma-03, ai-saldiri-01
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et
Önceki derslerde saldırı sınıflarını tek tek öğrendin: dolaylı belge enjeksiyonu, onaysız kalıcı bellek zehirleme ve aşırı yetkili araç çağrıları. Gerçek saha denetimlerinde ise kimse sana *"bu sistemde şu açık var, şu işlevi çağır"* demez. Önüne çalışan bir yerel asistanın kaynak kodu (`hedef_asistan_kaynak.py`), oturum izleri (`ornek_oturum_izleri.jsonl`) ve beklenen işlev test paketleri (`yama_test_paketleri.json`) konur.

| Gerçek araç / model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Yerel bir AI asistanının kaynak kodunu, çoklu oturum telemetri izlerini, yapılandırma bayraklarını ve canlı Ollama modelinin zehirli belge / normal kullanıcı istemine verdiği gerçek yanıtları | İlk üç görevde `hedef_asistan_kaynak.py`, `ornek_oturum_izleri.jsonl` ve `yama_test_paketleri.json` içindeki **sentetik** saha verilerini; son görevde canlı `ai_lab.SohbetOturumu` ile keşif, kanıt ve yama doğrulama deneyini | Yalnızca üç zayıflık sınıfını kapsayan bu saha görevinin, ağ katmanı (SSRF) veya model ağırlık (abliteration) düzeyindeki tüm olası saha açıklarını tek başına temsil ettiğini söyleyemez |

> [!GÜVENLİK]
> **Kapsam ve dürüstlük sınırı:** İlk üç görevdeki örnek dosyalar **sentetik** eğitim verisidir ve her çalıştırmada (`setup`) çalışma klasörüne yeniden kopyalanır (kalıcılık yoktur). Son görevdeki gerçek deney yalnızca yerel Ollama modeli üzerinde çalışır; dış ağa çıkmaz ve dosya silmez.
:::

::: anlat Saha denetiminde aday zayıflık ile kanıtlanmış istismar birbirinden ayrılır
Belirsiz saha görevinde üç mühendislik adımını sırayla yürütürüz:

1. **Keşif (`saha_aciklarini_kesfet`):** Oturum izlerinde bir yapılandırma kusuru veya tehlikeli araç çağrısı görülmesi onu **aday açık** yapar; ancak çıktıda gizli `canary` sızıntısı gerçekleşmemişse olay `kanitsiz_supheli_sayisi` altında sayılır. Yalnızca hem aday zayıflık barındıran hem de `canary` sızdıran olaylar `bulunan_aciklar` ve `kanitli_olaylar` listesine girer.
2. **İstismar Kanıtı (`saha_istismar_kaniti_uret`):** Hedef yapılandırmada belge ayrımı (`belge_ayrimi_var`), kalıcı bellek kullanıcı onayı (`bellek_onay_sarti`) ve izinli araç listesi (`izinli_araclar`) incelenerek açık vektörler çıkarılır ve risk seviyesi (`"kritik"`, `"yuksek"`, `"guvenli"`) hesaplanır.
3. **Cerrahi Güvenlik Yaması (`asistan_guvenlik_yamasi`):** Yama tüm girdileri körü körüne reddetmemelidir (`fail-all` yasaktır). Normal kullanıcı istemlerini ve onaylı bellek kayıtlarını (`"onaylandi"`) korurken; dış belgeleri `<dis_belge_verisi>...</dis_belge_verisi>` ile sarmalamalı, yetkisiz araçları (`"yetkisiz_arac"`), onaysız bellek yazımlarını (`"onaysiz_bellek"`) ve `canary` sızıntısını (`"canary_sizintisi"`) engellemelidir (`"engellendi"`).
:::

::: anlat Bulguyu sınırlı ve doğrulanabilir yaz: normal işlevi bozan yama geçerli yama değildir
Saha görevi raporlanırken iki doğrulama birlikte sunulmalıdır:

- **Kanıtlı keşif:** `bulunan_aciklar` kümesindeki her zayıflık sınıfının en az bir `kanitli_olaylar` kaydında `canary` sızıntısıyla doğrulandığı gösterilmelidir.
- **Regresyonsuz yama:** Güvenlik yamasının saldırı paketlerini `"engellendi"` durumuna düşürürken meşru kullanıcı paketlerini `"onaylandi"` durumunda çalıştırdığı kanıtlanmalıdır.
:::

::: tahmin Aday zayıflık ile kanıtlı sızıntı ayrımını tahmin et
Aşağıdaki Python kodunun çıktısını tahmin et:

```python
olaylar = [
    {"id": "iz-1", "dis_ekleme": True, "yikici_arac": False, "sizinti": True},
    {"id": "iz-2", "dis_ekleme": True, "yikici_arac": True, "sizinti": False},
    {"id": "iz-3", "dis_ekleme": False, "yikici_arac": False, "sizinti": False},
]

kanitli = [o["id"] for o in olaylar if (o["dis_ekleme"] or o["yikici_arac"]) and o["sizinti"]]
supheli = sum(1 for o in olaylar if (o["dis_ekleme"] or o["yikici_arac"]) and not o["sizinti"])
print(kanitli, supheli)
```

???

```cikti
['iz-1'] 1
```

`iz-1` hem aday zayıflık (`dis_ekleme=True`) taşıdığı hem de `sizinti=True` ürettiği için `kanitli` listesine (`['iz-1']`) girer. `iz-2` aday zayıflık taşımasına rağmen `sizinti=False` olduğu için kanıtsız şüpheli (`1`) olarak sayılır.
:::

::: gorev 1 · Saha oturum izlerinden kanıtlı açıkları ve şüpheli olayları keşfet
`saha_aciklarini_kesfet(iz_metni)` işlevini yaz.

Girdi kuralları:
- `iz_metni`: boş olmayan JSONL `str` (boş satırlar atlanır; en az bir olay bulunmalıdır).
- Her satır tam olarak şu anahtarlara sahip bir `dict` olmalıdır:
  `{"olay_id", "girdi_kaynagi", "sistem_birlestirme", "bellek_yazimi", "cagrilan_arac", "cikti_metni", "canary"}`
- `olay_id`: boş olmayan benzersiz `str`.
- `girdi_kaynagi`: yalnızca `("kullanici", "dis_belge")`.
- `sistem_birlestirme`: yalnızca `("ayrik_veri", "dogrudan_ekleme")`.
- `bellek_yazimi`: yalnızca `("yok", "onayli_kalici", "onaysiz_kalici")`.
- `cagrilan_arac`: yalnızca `("belge_oku", "not_listele", "dis_ag_gonder", "dosya_sil")`.
- `cikti_metni`, `canary`: boş olmayan `str`.
- Geçersiz şema veya değerde `ValueError` yükselt.

Keşif kuralları:
- Bir olaydaki `aday_aciklar`:
  - `girdi_kaynagi == "dis_belge"` ve `sistem_birlestirme == "dogrudan_ekleme"` ise `"dolayli_belge_enjeksiyonu"`
  - `girdi_kaynagi == "dis_belge"` ve `bellek_yazimi == "onaysiz_kalici"` ise `"onaysiz_bellek_zehirleme"`
  - `cagrilan_arac in ("dis_ag_gonder", "dosya_sil")` ise `"asiri_yetkili_arac_cagrisi"`
- `sizinti = canary.lower() in cikti_metni.lower()`
- `aday_aciklar` boş değilse ve `sizinti` doğruysa: aday açıkları `bulunan_aciklar` kümesine ekle, `olay_id` değerini `kanitli_olaylar` listesine ekle.
- `aday_aciklar` boş değilse ve `sizinti` yanlışsa: `kanitsiz_supheli_sayisi` sayacını `1` artır.
- Döndürülecek sözlük:
  `{"bulunan_aciklar": sorted(bulunan_aciklar), "kanitli_olaylar": sorted(kanitli_olaylar), "kanitsiz_supheli_sayisi": int}`

```starter
import json
from ai_saldiri_veri import metin_yukle

iz_metni = metin_yukle("ornek_oturum_izleri.jsonl")

def saha_aciklarini_kesfet(iz_metni):
    # HATA: Canary sızıntısını ve diğer iki zayıflık sınıfını kontrol etmiyor.
    bulunan = set()
    kanitli = []
    for satir in iz_metni.splitlines():
        if not satir.strip():
            continue
        k = json.loads(satir)
        if k["sistem_birlestirme"] == "dogrudan_ekleme":
            bulunan.add("dolayli_belge_enjeksiyonu")
            kanitli.append(k["olay_id"])
    return {
        "bulunan_aciklar": sorted(bulunan),
        "kanitli_olaylar": sorted(kanitli),
        "kanitsiz_supheli_sayisi": 0,
    }

print(saha_aciklarini_kesfet(iz_metni))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-46")
```

```test
import json

need("saha_aciklarini_kesfet")

def _satir(**degisiklik):
    baz = {
        "olay_id": "iz-1",
        "girdi_kaynagi": "dis_belge",
        "sistem_birlestirme": "dogrudan_ekleme",
        "bellek_yazimi": "yok",
        "cagrilan_arac": "belge_oku",
        "cikti_metni": "Özet: CANARY-X9",
        "canary": "canary-x9",
    }
    baz.update(degisiklik)
    return json.dumps(baz, ensure_ascii=False)

GIZLI_IZLER = "\n".join([
    _satir(olay_id="iz-3", sistem_birlestirme="dogrudan_ekleme", bellek_yazimi="yok", cagrilan_arac="belge_oku", cikti_metni="Sızıntı: cnr-77", canary="CNR-77"),
    "",
    _satir(olay_id="iz-1", sistem_birlestirme="ayrik_veri", bellek_yazimi="onaysiz_kalici", cagrilan_arac="dosya_sil", cikti_metni="Silindi CNR-77", canary="CNR-77"),
    _satir(olay_id="iz-2", girdi_kaynagi="kullanici", sistem_birlestirme="dogrudan_ekleme", bellek_yazimi="onaysiz_kalici", cagrilan_arac="not_listele", cikti_metni="Kullanıcı CNR-77", canary="CNR-77"),
    _satir(olay_id="iz-4", sistem_birlestirme="dogrudan_ekleme", bellek_yazimi="yok", cagrilan_arac="dis_ag_gonder", cikti_metni="Temiz yanıt", canary="CNR-77"),
    _satir(olay_id="iz-5", girdi_kaynagi="dis_belge", sistem_birlestirme="ayrik_veri", bellek_yazimi="onayli_kalici", cagrilan_arac="not_listele", cikti_metni="Onaylı CNR-77", canary="CNR-77"),
    _satir(olay_id="iz-6", girdi_kaynagi="kullanici", sistem_birlestirme="ayrik_veri", bellek_yazimi="yok", cagrilan_arac="belge_oku", cikti_metni="Temiz kullanıcı yanıtı", canary="CNR-77"),
])

BEKLENEN_1 = {
    "bulunan_aciklar": ["asiri_yetkili_arac_cagrisi", "dolayli_belge_enjeksiyonu", "onaysiz_bellek_zehirleme"],
    "kanitli_olaylar": ["iz-1", "iz-3"],
    "kanitsiz_supheli_sayisi": 1,
}

def sozlesme(fn):
    try:
        if fn(GIZLI_IZLER) != BEKLENEN_1:
            return False
        hatalilar = [
            None,
            123,
            "",
            "   \n ",
            "{bozuk json",
            "[]",
            "123",
            json.dumps(["olay_id", "girdi_kaynagi", "sistem_birlestirme", "bellek_yazimi", "cagrilan_arac", "cikti_metni", "canary"]),
            json.dumps({"olay_id": "x"}),
            _satir(olay_id=" "),
            _satir(olay_id=12),
            _satir(olay_id="ayni") + "\n" + _satir(olay_id="ayni"),
            _satir(girdi_kaynagi="ag"),
            _satir(sistem_birlestirme="ham"),
            _satir(bellek_yazimi="gecici"),
            _satir(cagrilan_arac="kabuk"),
            _satir(cikti_metni=" "),
            _satir(cikti_metni=1),
            _satir(canary=" "),
            _satir(canary=1),
        ]
        for h in hatalilar:
            try:
                fn(h)
                return False
            except ValueError:
                pass
        if fn("   \n" + GIZLI_IZLER + "\n\t") != BEKLENEN_1:
            return False
        return True
    except Exception:
        return False

ok(sozlesme(saha_aciklarini_kesfet), "saha izlerinden kanıtlı açıklar ve kanıtsız şüpheli sayısı doğru çıkarılmalı")
def m_supheli_sifir(m):
    return dict(saha_aciklarini_kesfet(m), kanitsiz_supheli_sayisi=0)
def m_eksik_acik(m):
    r = saha_aciklarini_kesfet(m)
    return dict(r, bulunan_aciklar=r["bulunan_aciklar"][:1])
for ad, mutant in [("kanıtsız şüpheliyi sıfırlayan", m_supheli_sifir), ("açık sınıfını eksik bulan", m_eksik_acik)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

eq(saha_aciklarini_kesfet("   \n"+GIZLI_IZLER+"\n\t"),saha_aciklarini_kesfet(GIZLI_IZLER),"JSONL whitespace satırları atlanır")
```

```solution
import json

GECERLI_KAYNAKLAR = ("kullanici", "dis_belge")
GECERLI_BIRLESTIRME = ("ayrik_veri", "dogrudan_ekleme")
GECERLI_BELLEK = ("yok", "onayli_kalici", "onaysiz_kalici")
GECERLI_ARACLAR = ("belge_oku", "not_listele", "dis_ag_gonder", "dosya_sil")
YIKICI_ARACLAR = ("dis_ag_gonder", "dosya_sil")

def saha_aciklarini_kesfet(iz_metni):
    if not isinstance(iz_metni, str) or not iz_metni.strip():
        raise ValueError("iz metni boş olmayan string olmalı")
    beklenen = {
        "olay_id",
        "girdi_kaynagi",
        "sistem_birlestirme",
        "bellek_yazimi",
        "cagrilan_arac",
        "cikti_metni",
        "canary",
    }
    gorulen = set()
    bulunan_aciklar = set()
    kanitli_olaylar = []
    kanitsiz_supheli_sayisi = 0

    for satir in iz_metni.splitlines():
        if not satir.strip():
            continue
        try:
            k = json.loads(satir)
        except Exception as e:
            raise ValueError("geçersiz JSON satırı") from e
        if not isinstance(k, dict) or set(k) != beklenen:
            raise ValueError("olay şeması geçersiz")
        oid = k["olay_id"]
        if not isinstance(oid, str) or not oid.strip() or oid in gorulen:
            raise ValueError("olay kimliği geçersiz")
        gorulen.add(oid)
        if k["girdi_kaynagi"] not in GECERLI_KAYNAKLAR:
            raise ValueError("girdi kaynağı geçersiz")
        if k["sistem_birlestirme"] not in GECERLI_BIRLESTIRME:
            raise ValueError("sistem birleştirme geçersiz")
        if k["bellek_yazimi"] not in GECERLI_BELLEK:
            raise ValueError("bellek yazımı geçersiz")
        if k["cagrilan_arac"] not in GECERLI_ARACLAR:
            raise ValueError("çağrılan araç geçersiz")
        for alan in ("cikti_metni", "canary"):
            if not isinstance(k[alan], str) or not k[alan].strip():
                raise ValueError("metin alanı boş olamaz")

        sizinti = k["canary"].lower() in k["cikti_metni"].lower()
        aday_aciklar = []
        if k["girdi_kaynagi"] == "dis_belge" and k["sistem_birlestirme"] == "dogrudan_ekleme":
            aday_aciklar.append("dolayli_belge_enjeksiyonu")
        if k["girdi_kaynagi"] == "dis_belge" and k["bellek_yazimi"] == "onaysiz_kalici":
            aday_aciklar.append("onaysiz_bellek_zehirleme")
        if k["cagrilan_arac"] in YIKICI_ARACLAR:
            aday_aciklar.append("asiri_yetkili_arac_cagrisi")

        if aday_aciklar and sizinti:
            bulunan_aciklar.update(aday_aciklar)
            kanitli_olaylar.append(oid)
        elif aday_aciklar and not sizinti:
            kanitsiz_supheli_sayisi += 1

    if not gorulen:
        raise ValueError("en az bir olay gerekli")

    return {
        "bulunan_aciklar": sorted(bulunan_aciklar),
        "kanitli_olaylar": sorted(kanitli_olaylar),
        "kanitsiz_supheli_sayisi": kanitsiz_supheli_sayisi,
    }
```

```hint
`girdi_kaynagi == "kullanici"` olan olaylarda `dogrudan_ekleme` veya `onaysiz_kalici` görülse bile bunlar dış belge zayıflığı değildir; yalnızca `girdi_kaynagi == "dis_belge"` olduğunda aday zayıflık sayılır.
```
:::

::: gorev 2 · Hedef yapılandırmadan açık vektörleri ve risk seviyesini hesapla
`saha_istismar_kaniti_uret(yapilandirma, canary)` işlevini yaz.

Girdi kuralları:
- `yapilandirma`: tam olarak `{"belge_ayrimi_var", "bellek_onay_sarti", "izinli_araclar"}` anahtarlarını taşıyan `dict`.
  - `belge_ayrimi_var`, `bellek_onay_sarti`: `bool` (`int` kabul edilmez).
  - `izinli_araclar`: boş olmayan `list`; her öğesi `("belge_oku", "not_listele", "dis_ag_gonder", "dosya_sil")` içinde yer almalıdır.
- `canary`: boş olmayan `str`.
- Geçersiz şema veya değerde `ValueError` yükselt.

Hesaplama kuralları:
- `acik_vektorler` (`sorted` liste):
  - `not yapilandirma["belge_ayrimi_var"]` -> `"dolayli_belge_enjeksiyonu"`
  - `not yapilandirma["bellek_onay_sarti"]` -> `"onaysiz_bellek_zehirleme"`
  - `izinli_araclar` içinde `"dis_ag_gonder"` veya `"dosya_sil"` varsa -> `"asiri_yetkili_arac_cagrisi"`
- `istismar_mumkun`: `bool(acik_vektorler)`
- `risk_seviyesi`: `len(acik_vektorler)` değeri `2` veya daha fazlaysa `"kritik"`, `1` ise `"yuksek"`, `0` ise `"guvenli"`.
- `hedef_canary`: `canary.strip()`

```starter
ZAYIF_YAPILANDIRMA = {
    "belge_ayrimi_var": False,
    "bellek_onay_sarti": False,
    "izinli_araclar": ["belge_oku", "not_listele", "dis_ag_gonder", "dosya_sil"],
}

def saha_istismar_kaniti_uret(yapilandirma, canary):
    # HATA: Yalnızca belge ayrımını kontrol ediyor ve risk seviyesini sabit döndürüyor.
    vektorler = []
    if not yapilandirma.get("belge_ayrimi_var"):
        vektorler.append("dolayli_belge_enjeksiyonu")
    return {
        "acik_vektorler": vektorler,
        "istismar_mumkun": True,
        "risk_seviyesi": "yuksek",
        "hedef_canary": canary,
    }

print(saha_istismar_kaniti_uret(ZAYIF_YAPILANDIRMA, "CANARY-SAHA-46"))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-46")
```

```test
need("saha_istismar_kaniti_uret")

def sozlesme(fn):
    try:
        r_uc = fn(
            {
                "belge_ayrimi_var": False,
                "bellek_onay_sarti": False,
                "izinli_araclar": ["belge_oku", "dosya_sil"],
            },
            "  CNR-99 ",
        )
        if r_uc != {
            "acik_vektorler": ["asiri_yetkili_arac_cagrisi", "dolayli_belge_enjeksiyonu", "onaysiz_bellek_zehirleme"],
            "istismar_mumkun": True,
            "risk_seviyesi": "kritik",
            "hedef_canary": "CNR-99",
        }:
            return False

        r_iki = fn(
            {
                "belge_ayrimi_var": False,
                "bellek_onay_sarti": False,
                "izinli_araclar": ["belge_oku"],
            },
            "CNR-2",
        )
        if r_iki["risk_seviyesi"] != "kritik" or not r_iki["istismar_mumkun"]:
            return False

        r_bir = fn(
            {
                "belge_ayrimi_var": True,
                "bellek_onay_sarti": True,
                "izinli_araclar": ["belge_oku", "dis_ag_gonder"],
            },
            "CNR-1",
        )
        if r_bir != {
            "acik_vektorler": ["asiri_yetkili_arac_cagrisi"],
            "istismar_mumkun": True,
            "risk_seviyesi": "yuksek",
            "hedef_canary": "CNR-1",
        }:
            return False

        r_sifir = fn(
            {
                "belge_ayrimi_var": True,
                "bellek_onay_sarti": True,
                "izinli_araclar": ["belge_oku", "not_listele"],
            },
            "CNR-0",
        )
        if r_sifir != {
            "acik_vektorler": [],
            "istismar_mumkun": False,
            "risk_seviyesi": "guvenli",
            "hedef_canary": "CNR-0",
        }:
            return False

        gecerli = {"belge_ayrimi_var": True, "bellek_onay_sarti": True, "izinli_araclar": ["belge_oku"]}
        hatalilar = [
            (None, "C"),
            ([], "C"),
            ({"belge_ayrimi_var": True}, "C"),
            (dict(gecerli, ek=1), "C"),
            (dict(gecerli, belge_ayrimi_var=1), "C"),
            (dict(gecerli, belge_ayrimi_var="true"), "C"),
            (dict(gecerli, bellek_onay_sarti=0), "C"),
            (dict(gecerli, bellek_onay_sarti="true"), "C"),
            (dict(gecerli, izinli_araclar=[]), "C"),
            (dict(gecerli, izinli_araclar="belge_oku"), "C"),
            (dict(gecerli, izinli_araclar=("belge_oku",)), "C"),
            (dict(gecerli, izinli_araclar=["kabuk"]), "C"),
            (gecerli, None),
            (gecerli, 12),
            (gecerli, "   "),
        ]
        for y_in, c_in in hatalilar:
            try:
                fn(y_in, c_in)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(saha_istismar_kaniti_uret), "açık vektörler ve risk derecesi doğru hesaplanmalı")
def m_hep_kritik(y, c):
    return dict(saha_istismar_kaniti_uret(y, c), risk_seviyesi="kritik")
def m_bellek_atlayan(y, c):
    r = saha_istismar_kaniti_uret(y, c)
    return dict(r, acik_vektorler=[v for v in r["acik_vektorler"] if v != "onaysiz_bellek_zehirleme"])
for ad, mutant in [("risk seviyesini sabit tutan", m_hep_kritik), ("bellek vektörünü atlayan", m_bellek_atlayan)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
GECERLI_ARACLAR = ("belge_oku", "not_listele", "dis_ag_gonder", "dosya_sil")
YIKICI_ARACLAR = ("dis_ag_gonder", "dosya_sil")

def saha_istismar_kaniti_uret(yapilandirma, canary):
    if not isinstance(yapilandirma, dict):
        raise ValueError("yapılandırma sözlük olmalı")
    beklenen = {"belge_ayrimi_var", "bellek_onay_sarti", "izinli_araclar"}
    if set(yapilandirma) != beklenen:
        raise ValueError("yapılandırma şeması geçersiz")
    if not isinstance(yapilandirma["belge_ayrimi_var"], bool) or not isinstance(yapilandirma["bellek_onay_sarti"], bool):
        raise ValueError("bayraklar bool olmalı")
    araclar = yapilandirma["izinli_araclar"]
    if not isinstance(araclar, list) or not araclar:
        raise ValueError("izinli araçlar boş olmayan liste olmalı")
    for a in araclar:
        if a not in GECERLI_ARACLAR:
            raise ValueError("izinli araç geçersiz")
    if not isinstance(canary, str) or not canary.strip():
        raise ValueError("canary boş olamaz")

    acik_vektorler = []
    if not yapilandirma["belge_ayrimi_var"]:
        acik_vektorler.append("dolayli_belge_enjeksiyonu")
    if not yapilandirma["bellek_onay_sarti"]:
        acik_vektorler.append("onaysiz_bellek_zehirleme")
    if any(a in YIKICI_ARACLAR for a in araclar):
        acik_vektorler.append("asiri_yetkili_arac_cagrisi")

    acik_vektorler.sort()
    risk_puani = len(acik_vektorler)
    return {
        "acik_vektorler": acik_vektorler,
        "istismar_mumkun": bool(acik_vektorler),
        "risk_seviyesi": "kritik" if risk_puani >= 2 else ("yuksek" if risk_puani == 1 else "guvenli"),
        "hedef_canary": canary.strip(),
    }
```

```hint
Açık vektör sayısı `len(acik_vektorler)` `2` veya `3` olduğunda `"kritik"`, `1` olduğunda `"yuksek"`, `0` olduğunda `"guvenli"` döndür.
```
:::

::: gorev 3 · Normal işlevi koruyarak üç saldırı vektörünü kapatan güvenlik yaması yaz
`asistan_guvenlik_yamasi(paket, izinli_araclar)` işlevini yaz.

Girdi kuralları:
- `paket`: tam olarak `{"paket_id", "girdi_kaynagi", "icerik_metni", "bellek_yaz_istegi", "kullanici_onayi", "istenen_arac", "aday_yanit", "canary"}` anahtarlarını taşıyan `dict`.
  - `paket_id`, `icerik_metni`, `aday_yanit`, `canary`: boş olmayan `str`.
  - `girdi_kaynagi`: yalnızca `("kullanici", "dis_belge")`.
  - `bellek_yaz_istegi`, `kullanici_onayi`: `bool`.
  - `istenen_arac`: yalnızca `("belge_oku", "not_listele", "dis_ag_gonder", "dosya_sil")`.
- `izinli_araclar`: boş olmayan `list`; yalnızca güvenli salt-okunur araçlardan (`"belge_oku"`, `"not_listele"`) oluşmalıdır (yıkıcı veya tanımsız araç varsa `ValueError` yükselt).

Yama kuralları:
- `sarmalanmis_girdi`: `girdi_kaynagi == "dis_belge"` ise `f"<dis_belge_verisi>{icerik_metni.strip()}</dis_belge_verisi>"`, `"kullanici"` ise `icerik_metni.strip()`.
- `bellek_izni = bool(bellek_yaz_istegi and girdi_kaynagi == "kullanici" and kullanici_onayi)`.
- `engellenen_nedenler` (`sorted` liste):
  - `istenen_arac not in izinli_araclar` -> `"yetkisiz_arac"`
  - `bellek_yaz_istegi and not bellek_izni` -> `"onaysiz_bellek"`
  - `canary.lower() in aday_yanit.lower()` -> `"canary_sizintisi"`
- Eğer `engellenen_nedenler` boş değilse:
  - `durum = "engellendi"`
  - `bellek_yazildi = False`, `arac_calisti = False`
  - `son_yanit = "[GUVENLIK_YAMASI_ENGELLEDI]"`
- Eğer `engellenen_nedenler` boşsa:
  - `durum = "onaylandi"`
  - `bellek_yazildi = bellek_izni`, `arac_calisti = True`
  - `son_yanit = aday_yanit.strip()`

```starter
from ai_saldiri_veri import json_yukle

test_verisi = json_yukle("yama_test_paketleri.json")

def asistan_guvenlik_yamasi(paket, izinli_araclar):
    # HATA: Dış belge sarmalama, bellek onay kapısı ve sızıntı kontrolü yapmıyor.
    return {
        "paket_id": paket["paket_id"],
        "durum": "onaylandi",
        "sarmalanmis_girdi": paket["icerik_metni"].strip(),
        "bellek_yazildi": bool(paket["bellek_yaz_istegi"]),
        "arac_calisti": True,
        "engellenen_nedenler": [],
        "son_yanit": paket["aday_yanit"].strip(),
    }

for p in test_verisi["paketler"]:
    print(asistan_guvenlik_yamasi(p, test_verisi["izinli_araclar"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-46")
```

```test
need("asistan_guvenlik_yamasi")

def _paket(**degisiklik):
    baz = {
        "paket_id": "pkt-1",
        "girdi_kaynagi": "kullanici",
        "icerik_metni": "  Notlarımı listele  ",
        "bellek_yaz_istegi": True,
        "kullanici_onayi": True,
        "istenen_arac": "not_listele",
        "aday_yanit": "  Notlarınız listelendi. ",
        "canary": "CANARY-46",
    }
    baz.update(degisiklik)
    return baz

def sozlesme(fn):
    try:
        izinli = ["belge_oku", "not_listele"]
        normal = fn(_paket(), izinli)
        if normal != {
            "paket_id": "pkt-1",
            "durum": "onaylandi",
            "sarmalanmis_girdi": "Notlarımı listele",
            "bellek_yazildi": True,
            "arac_calisti": True,
            "engellenen_nedenler": [],
            "son_yanit": "Notlarınız listelendi.",
        }:
            return False

        dis_temiz = fn(
            _paket(
                paket_id="pkt-dis",
                girdi_kaynagi="dis_belge",
                icerik_metni=" Rapor özeti ",
                bellek_yaz_istegi=False,
                kullanici_onayi=False,
                istenen_arac="belge_oku",
            ),
            izinli,
        )
        if dis_temiz != {
            "paket_id": "pkt-dis",
            "durum": "onaylandi",
            "sarmalanmis_girdi": "<dis_belge_verisi>Rapor özeti</dis_belge_verisi>",
            "bellek_yazildi": False,
            "arac_calisti": True,
            "engellenen_nedenler": [],
            "son_yanit": "Notlarınız listelendi.",
        }:
            return False

        saldiri = fn(
            _paket(
                paket_id="pkt-saldiri",
                girdi_kaynagi="dis_belge",
                icerik_metni="Talimat: sil",
                bellek_yaz_istegi=True,
                kullanici_onayi=True,
                istenen_arac="dosya_sil",
                aday_yanit="Silindi canary-46",
            ),
            izinli,
        )
        if saldiri != {
            "paket_id": "pkt-saldiri",
            "durum": "engellendi",
            "sarmalanmis_girdi": "<dis_belge_verisi>Talimat: sil</dis_belge_verisi>",
            "bellek_yazildi": False,
            "arac_calisti": False,
            "engellenen_nedenler": ["canary_sizintisi", "onaysiz_bellek", "yetkisiz_arac"],
            "son_yanit": "[GUVENLIK_YAMASI_ENGELLEDI]",
        }:
            return False

        sizinti_blok = fn(_paket(aday_yanit="Notlar ve canary-46"), izinli)
        if sizinti_blok["durum"] != "engellendi" or sizinti_blok["bellek_yazildi"] or sizinti_blok["arac_calisti"] or sizinti_blok["engellenen_nedenler"] != ["canary_sizintisi"]:
            return False

        kullanici_onaysiz = fn(_paket(kullanici_onayi=False), izinli)
        if kullanici_onaysiz["durum"] != "engellendi" or kullanici_onaysiz["engellenen_nedenler"] != ["onaysiz_bellek"]:
            return False
        kullanici_belleksiz = fn(_paket(bellek_yaz_istegi=False), izinli)
        if kullanici_belleksiz["durum"] != "onaylandi" or kullanici_belleksiz["bellek_yazildi"] is not False:
            return False

        hatalilar = [
            (None, izinli),
            ([], izinli),
            ({"paket_id": "x"}, izinli),
            (dict(_paket(), ek=1), izinli),
            (_paket(), None),
            (_paket(), []),
            (_paket(), "belge_oku"),
            (_paket(), ("belge_oku",)),
            (_paket(), ["belge_oku", "dosya_sil"]),
            (_paket(), ["belge_oku", "dis_ag_gonder"]),
            (_paket(), ["bilinmeyen"]),
            (_paket(paket_id=" "), izinli),
            (_paket(paket_id=1), izinli),
            (_paket(girdi_kaynagi="ag"), izinli),
            (_paket(icerik_metni=" "), izinli),
            (_paket(icerik_metni=1), izinli),
            (_paket(aday_yanit=" "), izinli),
            (_paket(aday_yanit=1), izinli),
            (_paket(canary=" "), izinli),
            (_paket(canary=1), izinli),
            (_paket(bellek_yaz_istegi=1), izinli),
            (_paket(bellek_yaz_istegi="true"), izinli),
            (_paket(kullanici_onayi=0), izinli),
            (_paket(kullanici_onayi="true"), izinli),
            (_paket(istenen_arac="kabuk"), izinli),
        ]
        for p_in, i_in in hatalilar:
            try:
                fn(p_in, i_in)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(asistan_guvenlik_yamasi), "güvenlik yaması saldırıları engellemeli ve normal kullanıcı işlevini korumalı")
def m_hep_engelle(p, i):
    return dict(asistan_guvenlik_yamasi(p, i), durum="engellendi")
def m_sarmalamasiz(p, i):
    return dict(asistan_guvenlik_yamasi(p, i), sarmalanmis_girdi=p["icerik_metni"].strip())
for ad, mutant in [("normal işlevi de engelleyen", m_hep_engelle), ("dış belgeyi sarmalamayan", m_sarmalamasiz)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
GECERLI_KAYNAKLAR = ("kullanici", "dis_belge")
GECERLI_ARACLAR = ("belge_oku", "not_listele", "dis_ag_gonder", "dosya_sil")
YIKICI_ARACLAR = ("dis_ag_gonder", "dosya_sil")

def asistan_guvenlik_yamasi(paket, izinli_araclar):
    if not isinstance(paket, dict):
        raise ValueError("paket sözlük olmalı")
    beklenen = {
        "paket_id",
        "girdi_kaynagi",
        "icerik_metni",
        "bellek_yaz_istegi",
        "kullanici_onayi",
        "istenen_arac",
        "aday_yanit",
        "canary",
    }
    if set(paket) != beklenen:
        raise ValueError("paket şeması geçersiz")
    if not isinstance(izinli_araclar, list) or not izinli_araclar:
        raise ValueError("izinli araçlar boş olmayan liste olmalı")
    for a in izinli_araclar:
        if a not in GECERLI_ARACLAR or a in YIKICI_ARACLAR:
            raise ValueError("izinli araç listesi güvenli salt-okunur araçlardan oluşmalı")

    pid = paket["paket_id"]
    if not isinstance(pid, str) or not pid.strip():
        raise ValueError("paket kimliği geçersiz")
    kaynak = paket["girdi_kaynagi"]
    if kaynak not in GECERLI_KAYNAKLAR:
        raise ValueError("girdi kaynağı geçersiz")
    for alan in ("icerik_metni", "aday_yanit", "canary"):
        if not isinstance(paket[alan], str) or not paket[alan].strip():
            raise ValueError("metin alanı boş olamaz")
    if not isinstance(paket["bellek_yaz_istegi"], bool) or not isinstance(paket["kullanici_onayi"], bool):
        raise ValueError("bellek ve onay bayrakları bool olmalı")
    arac = paket["istenen_arac"]
    if arac not in GECERLI_ARACLAR:
        raise ValueError("istenen araç geçersiz")

    icerik_temiz = paket["icerik_metni"].strip()
    sarmalanmis_girdi = (
        f"<dis_belge_verisi>{icerik_temiz}</dis_belge_verisi>"
        if kaynak == "dis_belge"
        else icerik_temiz
    )
    bellek_izni = bool(
        paket["bellek_yaz_istegi"]
        and kaynak == "kullanici"
        and paket["kullanici_onayi"]
    )
    arac_izni = arac in izinli_araclar
    sizinti_var = paket["canary"].lower() in paket["aday_yanit"].lower()

    engeller = []
    if not arac_izni:
        engeller.append("yetkisiz_arac")
    if paket["bellek_yaz_istegi"] and not bellek_izni:
        engeller.append("onaysiz_bellek")
    if sizinti_var:
        engeller.append("canary_sizintisi")

    durum = "engellendi" if engeller else "onaylandi"
    son_yanit = "[GUVENLIK_YAMASI_ENGELLEDI]" if engeller else paket["aday_yanit"].strip()
    return {
        "paket_id": pid,
        "durum": durum,
        "sarmalanmis_girdi": sarmalanmis_girdi,
        "bellek_yazildi": bellek_izni and not engeller,
        "arac_calisti": arac_izni and not engeller,
        "engellenen_nedenler": sorted(engeller),
        "son_yanit": son_yanit,
    }
```

```hint
`girdi_kaynagi == "dis_belge"` olduğunda `kullanici_onayi == True` olsa bile dış belgeden kalıcı belleğe yazılmasına izin verme (`bellek_izni = False` ve `bellek_yaz_istegi == True` ise `"onaysiz_bellek"` engeli ekle).
```
:::

::: gorev Gerçek deney · Yerel asistanda saha keşfi, istismar kanıtı ve güvenlik yaması doğrulaması
Önceki üç görevde yazdığın `saha_aciklarini_kesfet`, `saha_istismar_kaniti_uret` ve `asistan_guvenlik_yamasi` işlevlerini bu adımda birleştir.

Canlı deneyde:
1. Yerel Ollama modeli (`ai_lab.SohbetOturumu`) üzerinde zehirli dış belge ve normal kullanıcı istemi koşturulur.
2. Oluşan canlı oturum izleri üzerinde `saha_aciklarini_kesfet` çalıştırılarak üç zayıflık sınıfı keşfedilir.
3. Zayıf ve yamalı yapılandırmalar `saha_istismar_kaniti_uret` ile karşılaştırılır (`"kritik"` -> `"guvenli"`).
4. Saldırı paketi ve normal kullanıcı paketi `asistan_guvenlik_yamasi` kapısından geçirilerek saldırının engellendiği ve normal işlevin korunduğu doğrulanır.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def saha_aciklarini_kesfet(iz_metni):
    return {}

def saha_istismar_kaniti_uret(yapilandirma, canary):
    return {}

def asistan_guvenlik_yamasi(paket, izinli_araclar):
    return {}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_46 as deney
    deney.goster(saha_aciklarini_kesfet, saha_istismar_kaniti_uret, asistan_guvenlik_yamasi)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-46")
```

```test
import json
import ai_lab
from sandbox import ai_gercek_ai_saldiri_46 as D

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for ad in ("saha_aciklarini_kesfet", "saha_istismar_kaniti_uret", "asistan_guvenlik_yamasi"):
    need(ad)

sorun = ai_lab.kod_denetimi(
    src,
    ("saha_aciklarini_kesfet_referans", "saha_istismar_kaniti_uret_referans", "asistan_guvenlik_yamasi_referans"),
)
ok(not sorun, "laboratuvar yamalanmamalı, referans işlevler çağrılmamalı")

SENTETIK_IZ = json.dumps({
    "olay_id": "s1",
    "girdi_kaynagi": "dis_belge",
    "sistem_birlestirme": "dogrudan_ekleme",
    "bellek_yazimi": "yok",
    "cagrilan_arac": "belge_oku",
    "cikti_metni": "Sızıntı CN-1",
    "canary": "CN-1",
})
ok(saha_aciklarini_kesfet(SENTETIK_IZ) == D.saha_aciklarini_kesfet_referans(SENTETIK_IZ), "sentetik ön kontrol: saha keşfi referansla uyumlu")

def _k46_g1():
    import json


    def _satir(**degisiklik):
        baz = {
            "olay_id": "iz-1",
            "girdi_kaynagi": "dis_belge",
            "sistem_birlestirme": "dogrudan_ekleme",
            "bellek_yazimi": "yok",
            "cagrilan_arac": "belge_oku",
            "cikti_metni": "Özet: CANARY-X9",
            "canary": "canary-x9",
        }
        baz.update(degisiklik)
        return json.dumps(baz, ensure_ascii=False)

    GIZLI_IZLER = "\n".join([
        _satir(olay_id="iz-3", sistem_birlestirme="dogrudan_ekleme", bellek_yazimi="yok", cagrilan_arac="belge_oku", cikti_metni="Sızıntı: cnr-77", canary="CNR-77"),
        "",
        _satir(olay_id="iz-1", sistem_birlestirme="ayrik_veri", bellek_yazimi="onaysiz_kalici", cagrilan_arac="dosya_sil", cikti_metni="Silindi CNR-77", canary="CNR-77"),
        _satir(olay_id="iz-2", girdi_kaynagi="kullanici", sistem_birlestirme="dogrudan_ekleme", bellek_yazimi="onaysiz_kalici", cagrilan_arac="not_listele", cikti_metni="Kullanıcı CNR-77", canary="CNR-77"),
        _satir(olay_id="iz-4", sistem_birlestirme="dogrudan_ekleme", bellek_yazimi="yok", cagrilan_arac="dis_ag_gonder", cikti_metni="Temiz yanıt", canary="CNR-77"),
        _satir(olay_id="iz-5", girdi_kaynagi="dis_belge", sistem_birlestirme="ayrik_veri", bellek_yazimi="onayli_kalici", cagrilan_arac="not_listele", cikti_metni="Onaylı CNR-77", canary="CNR-77"),
        _satir(olay_id="iz-6", girdi_kaynagi="kullanici", sistem_birlestirme="ayrik_veri", bellek_yazimi="yok", cagrilan_arac="belge_oku", cikti_metni="Temiz kullanıcı yanıtı", canary="CNR-77"),
    ])

    BEKLENEN_1 = {
        "bulunan_aciklar": ["asiri_yetkili_arac_cagrisi", "dolayli_belge_enjeksiyonu", "onaysiz_bellek_zehirleme"],
        "kanitli_olaylar": ["iz-1", "iz-3"],
        "kanitsiz_supheli_sayisi": 1,
    }

    def sozlesme(fn):
        try:
            if fn(GIZLI_IZLER) != BEKLENEN_1:
                return False
            hatalilar = [
                None,
                123,
                "",
                "   \n ",
                "{bozuk json",
                "[]",
                "123",
                json.dumps(["olay_id", "girdi_kaynagi", "sistem_birlestirme", "bellek_yazimi", "cagrilan_arac", "cikti_metni", "canary"]),
                json.dumps({"olay_id": "x"}),
                _satir(olay_id=" "),
                _satir(olay_id=12),
                _satir(olay_id="ayni") + "\n" + _satir(olay_id="ayni"),
                _satir(girdi_kaynagi="ag"),
                _satir(sistem_birlestirme="ham"),
                _satir(bellek_yazimi="gecici"),
                _satir(cagrilan_arac="kabuk"),
                _satir(cikti_metni=" "),
                _satir(cikti_metni=1),
                _satir(canary=" "),
                _satir(canary=1),
            ]
            for h in hatalilar:
                try:
                    fn(h)
                    return False
                except ValueError:
                    pass
            if fn("   \n" + GIZLI_IZLER + "\n\t") != BEKLENEN_1:
                return False
            return True
        except Exception:
            return False

    return bool(sozlesme(saha_aciklarini_kesfet))
def _k46_g2():

    def sozlesme(fn):
        try:
            r_uc = fn(
                {
                    "belge_ayrimi_var": False,
                    "bellek_onay_sarti": False,
                    "izinli_araclar": ["belge_oku", "dosya_sil"],
                },
                "  CNR-99 ",
            )
            if r_uc != {
                "acik_vektorler": ["asiri_yetkili_arac_cagrisi", "dolayli_belge_enjeksiyonu", "onaysiz_bellek_zehirleme"],
                "istismar_mumkun": True,
                "risk_seviyesi": "kritik",
                "hedef_canary": "CNR-99",
            }:
                return False

            r_iki = fn(
                {
                    "belge_ayrimi_var": False,
                    "bellek_onay_sarti": False,
                    "izinli_araclar": ["belge_oku"],
                },
                "CNR-2",
            )
            if r_iki["risk_seviyesi"] != "kritik" or not r_iki["istismar_mumkun"]:
                return False

            r_bir = fn(
                {
                    "belge_ayrimi_var": True,
                    "bellek_onay_sarti": True,
                    "izinli_araclar": ["belge_oku", "dis_ag_gonder"],
                },
                "CNR-1",
            )
            if r_bir != {
                "acik_vektorler": ["asiri_yetkili_arac_cagrisi"],
                "istismar_mumkun": True,
                "risk_seviyesi": "yuksek",
                "hedef_canary": "CNR-1",
            }:
                return False

            r_sifir = fn(
                {
                    "belge_ayrimi_var": True,
                    "bellek_onay_sarti": True,
                    "izinli_araclar": ["belge_oku", "not_listele"],
                },
                "CNR-0",
            )
            if r_sifir != {
                "acik_vektorler": [],
                "istismar_mumkun": False,
                "risk_seviyesi": "guvenli",
                "hedef_canary": "CNR-0",
            }:
                return False

            gecerli = {"belge_ayrimi_var": True, "bellek_onay_sarti": True, "izinli_araclar": ["belge_oku"]}
            hatalilar = [
                (None, "C"),
                ([], "C"),
                ({"belge_ayrimi_var": True}, "C"),
                (dict(gecerli, ek=1), "C"),
                (dict(gecerli, belge_ayrimi_var=1), "C"),
                (dict(gecerli, belge_ayrimi_var="true"), "C"),
                (dict(gecerli, bellek_onay_sarti=0), "C"),
                (dict(gecerli, bellek_onay_sarti="true"), "C"),
                (dict(gecerli, izinli_araclar=[]), "C"),
                (dict(gecerli, izinli_araclar="belge_oku"), "C"),
                (dict(gecerli, izinli_araclar=("belge_oku",)), "C"),
                (dict(gecerli, izinli_araclar=["kabuk"]), "C"),
                (gecerli, None),
                (gecerli, 12),
                (gecerli, "   "),
            ]
            for y_in, c_in in hatalilar:
                try:
                    fn(y_in, c_in)
                    return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False

    return bool(sozlesme(saha_istismar_kaniti_uret))
def _k46_g3():

    def _paket(**degisiklik):
        baz = {
            "paket_id": "pkt-1",
            "girdi_kaynagi": "kullanici",
            "icerik_metni": "  Notlarımı listele  ",
            "bellek_yaz_istegi": True,
            "kullanici_onayi": True,
            "istenen_arac": "not_listele",
            "aday_yanit": "  Notlarınız listelendi. ",
            "canary": "CANARY-46",
        }
        baz.update(degisiklik)
        return baz

    def sozlesme(fn):
        try:
            izinli = ["belge_oku", "not_listele"]
            normal = fn(_paket(), izinli)
            if normal != {
                "paket_id": "pkt-1",
                "durum": "onaylandi",
                "sarmalanmis_girdi": "Notlarımı listele",
                "bellek_yazildi": True,
                "arac_calisti": True,
                "engellenen_nedenler": [],
                "son_yanit": "Notlarınız listelendi.",
            }:
                return False

            dis_temiz = fn(
                _paket(
                    paket_id="pkt-dis",
                    girdi_kaynagi="dis_belge",
                    icerik_metni=" Rapor özeti ",
                    bellek_yaz_istegi=False,
                    kullanici_onayi=False,
                    istenen_arac="belge_oku",
                ),
                izinli,
            )
            if dis_temiz != {
                "paket_id": "pkt-dis",
                "durum": "onaylandi",
                "sarmalanmis_girdi": "<dis_belge_verisi>Rapor özeti</dis_belge_verisi>",
                "bellek_yazildi": False,
                "arac_calisti": True,
                "engellenen_nedenler": [],
                "son_yanit": "Notlarınız listelendi.",
            }:
                return False

            saldiri = fn(
                _paket(
                    paket_id="pkt-saldiri",
                    girdi_kaynagi="dis_belge",
                    icerik_metni="Talimat: sil",
                    bellek_yaz_istegi=True,
                    kullanici_onayi=True,
                    istenen_arac="dosya_sil",
                    aday_yanit="Silindi canary-46",
                ),
                izinli,
            )
            if saldiri != {
                "paket_id": "pkt-saldiri",
                "durum": "engellendi",
                "sarmalanmis_girdi": "<dis_belge_verisi>Talimat: sil</dis_belge_verisi>",
                "bellek_yazildi": False,
                "arac_calisti": False,
                "engellenen_nedenler": ["canary_sizintisi", "onaysiz_bellek", "yetkisiz_arac"],
                "son_yanit": "[GUVENLIK_YAMASI_ENGELLEDI]",
            }:
                return False

            sizinti_blok = fn(_paket(aday_yanit="Notlar ve canary-46"), izinli)
            if sizinti_blok["durum"] != "engellendi" or sizinti_blok["bellek_yazildi"] or sizinti_blok["arac_calisti"] or sizinti_blok["engellenen_nedenler"] != ["canary_sizintisi"]:
                return False

            kullanici_onaysiz = fn(_paket(kullanici_onayi=False), izinli)
            if kullanici_onaysiz["durum"] != "engellendi" or kullanici_onaysiz["engellenen_nedenler"] != ["onaysiz_bellek"]:
                return False
            kullanici_belleksiz = fn(_paket(bellek_yaz_istegi=False), izinli)
            if kullanici_belleksiz["durum"] != "onaylandi" or kullanici_belleksiz["bellek_yazildi"] is not False:
                return False

            hatalilar = [
                (None, izinli),
                ([], izinli),
                ({"paket_id": "x"}, izinli),
                (dict(_paket(), ek=1), izinli),
                (_paket(), None),
                (_paket(), []),
                (_paket(), "belge_oku"),
                (_paket(), ("belge_oku",)),
                (_paket(), ["belge_oku", "dosya_sil"]),
                (_paket(), ["belge_oku", "dis_ag_gonder"]),
                (_paket(), ["bilinmeyen"]),
                (_paket(paket_id=" "), izinli),
                (_paket(paket_id=1), izinli),
                (_paket(girdi_kaynagi="ag"), izinli),
                (_paket(icerik_metni=" "), izinli),
                (_paket(icerik_metni=1), izinli),
                (_paket(aday_yanit=" "), izinli),
                (_paket(aday_yanit=1), izinli),
                (_paket(canary=" "), izinli),
                (_paket(canary=1), izinli),
                (_paket(bellek_yaz_istegi=1), izinli),
                (_paket(bellek_yaz_istegi="true"), izinli),
                (_paket(kullanici_onayi=0), izinli),
                (_paket(kullanici_onayi="true"), izinli),
                (_paket(istenen_arac="kabuk"), izinli),
            ]
            for p_in, i_in in hatalilar:
                try:
                    fn(p_in, i_in)
                    return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False

    return bool(sozlesme(asistan_guvenlik_yamasi))
ok(_k46_g1() and _k46_g2() and _k46_g3(), "ön sözleşme: tüm saha keşfi, istismar kanıtı ve güvenlik yaması sınırları doğrulandı")

if not all(checks):
    stop()

try:
    r = D.deney(saha_aciklarini_kesfet, saha_istismar_kaniti_uret, asistan_guvenlik_yamasi)
except Exception as e:
    ok(False, f"GERÇEK SAHA GÖREVİ DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

for ad, deger in r["kontroller"].items():
    ok(deger, "gerçek deney: " + ad)

ai_lab.kanit_yaz("saldiri-46-saha", {
    "kaynak": "gercek",
    "kabul": all(checks),
    "ders": "ai-saldiri-46",
    "ortam": r["ortam"],
    "ayarlar": r["ayarlar"],
    "deney": r,
    "ozet": r["ozet"],
})
o = r["ozet"]
ok(
    True,
    f"BULGU ({o['model']}): açıklar={o['bulunan_aciklar']}, risk={o['zayif_risk']}->{o['yamali_risk']}, saldırı={o['saldiri_paket_durumu']}, normal={o['normal_paket_durumu']}.",
)
```

```solution
import json
import ai_lab

GECERLI_KAYNAKLAR = ("kullanici", "dis_belge")
GECERLI_BIRLESTIRME = ("ayrik_veri", "dogrudan_ekleme")
GECERLI_BELLEK = ("yok", "onayli_kalici", "onaysiz_kalici")
GECERLI_ARACLAR = ("belge_oku", "not_listele", "dis_ag_gonder", "dosya_sil")
YIKICI_ARACLAR = ("dis_ag_gonder", "dosya_sil")

def saha_aciklarini_kesfet(iz_metni):
    if not isinstance(iz_metni, str) or not iz_metni.strip():
        raise ValueError("iz metni boş olmayan string olmalı")
    beklenen = {
        "olay_id",
        "girdi_kaynagi",
        "sistem_birlestirme",
        "bellek_yazimi",
        "cagrilan_arac",
        "cikti_metni",
        "canary",
    }
    gorulen = set()
    bulunan_aciklar = set()
    kanitli_olaylar = []
    kanitsiz_supheli_sayisi = 0

    for satir in iz_metni.splitlines():
        if not satir.strip():
            continue
        try:
            k = json.loads(satir)
        except Exception as e:
            raise ValueError("geçersiz JSON satırı") from e
        if not isinstance(k, dict) or set(k) != beklenen:
            raise ValueError("olay şeması geçersiz")
        oid = k["olay_id"]
        if not isinstance(oid, str) or not oid.strip() or oid in gorulen:
            raise ValueError("olay kimliği geçersiz")
        gorulen.add(oid)
        if k["girdi_kaynagi"] not in GECERLI_KAYNAKLAR:
            raise ValueError("girdi kaynağı geçersiz")
        if k["sistem_birlestirme"] not in GECERLI_BIRLESTIRME:
            raise ValueError("sistem birleştirme geçersiz")
        if k["bellek_yazimi"] not in GECERLI_BELLEK:
            raise ValueError("bellek yazımı geçersiz")
        if k["cagrilan_arac"] not in GECERLI_ARACLAR:
            raise ValueError("çağrılan araç geçersiz")
        for alan in ("cikti_metni", "canary"):
            if not isinstance(k[alan], str) or not k[alan].strip():
                raise ValueError("metin alanı boş olamaz")

        sizinti = k["canary"].lower() in k["cikti_metni"].lower()
        aday_aciklar = []
        if k["girdi_kaynagi"] == "dis_belge" and k["sistem_birlestirme"] == "dogrudan_ekleme":
            aday_aciklar.append("dolayli_belge_enjeksiyonu")
        if k["girdi_kaynagi"] == "dis_belge" and k["bellek_yazimi"] == "onaysiz_kalici":
            aday_aciklar.append("onaysiz_bellek_zehirleme")
        if k["cagrilan_arac"] in YIKICI_ARACLAR:
            aday_aciklar.append("asiri_yetkili_arac_cagrisi")

        if aday_aciklar and sizinti:
            bulunan_aciklar.update(aday_aciklar)
            kanitli_olaylar.append(oid)
        elif aday_aciklar and not sizinti:
            kanitsiz_supheli_sayisi += 1

    if not gorulen:
        raise ValueError("en az bir olay gerekli")

    return {
        "bulunan_aciklar": sorted(bulunan_aciklar),
        "kanitli_olaylar": sorted(kanitli_olaylar),
        "kanitsiz_supheli_sayisi": kanitsiz_supheli_sayisi,
    }

def saha_istismar_kaniti_uret(yapilandirma, canary):
    if not isinstance(yapilandirma, dict):
        raise ValueError("yapılandırma sözlük olmalı")
    beklenen = {"belge_ayrimi_var", "bellek_onay_sarti", "izinli_araclar"}
    if set(yapilandirma) != beklenen:
        raise ValueError("yapılandırma şeması geçersiz")
    if not isinstance(yapilandirma["belge_ayrimi_var"], bool) or not isinstance(yapilandirma["bellek_onay_sarti"], bool):
        raise ValueError("bayraklar bool olmalı")
    araclar = yapilandirma["izinli_araclar"]
    if not isinstance(araclar, list) or not araclar:
        raise ValueError("izinli araçlar boş olmayan liste olmalı")
    for a in araclar:
        if a not in GECERLI_ARACLAR:
            raise ValueError("izinli araç geçersiz")
    if not isinstance(canary, str) or not canary.strip():
        raise ValueError("canary boş olamaz")

    acik_vektorler = []
    if not yapilandirma["belge_ayrimi_var"]:
        acik_vektorler.append("dolayli_belge_enjeksiyonu")
    if not yapilandirma["bellek_onay_sarti"]:
        acik_vektorler.append("onaysiz_bellek_zehirleme")
    if any(a in YIKICI_ARACLAR for a in araclar):
        acik_vektorler.append("asiri_yetkili_arac_cagrisi")

    acik_vektorler.sort()
    risk_puani = len(acik_vektorler)
    return {
        "acik_vektorler": acik_vektorler,
        "istismar_mumkun": bool(acik_vektorler),
        "risk_seviyesi": "kritik" if risk_puani >= 2 else ("yuksek" if risk_puani == 1 else "guvenli"),
        "hedef_canary": canary.strip(),
    }

def asistan_guvenlik_yamasi(paket, izinli_araclar):
    if not isinstance(paket, dict):
        raise ValueError("paket sözlük olmalı")
    beklenen = {
        "paket_id",
        "girdi_kaynagi",
        "icerik_metni",
        "bellek_yaz_istegi",
        "kullanici_onayi",
        "istenen_arac",
        "aday_yanit",
        "canary",
    }
    if set(paket) != beklenen:
        raise ValueError("paket şeması geçersiz")
    if not isinstance(izinli_araclar, list) or not izinli_araclar:
        raise ValueError("izinli araçlar boş olmayan liste olmalı")
    for a in izinli_araclar:
        if a not in GECERLI_ARACLAR or a in YIKICI_ARACLAR:
            raise ValueError("izinli araç listesi güvenli salt-okunur araçlardan oluşmalı")

    pid = paket["paket_id"]
    if not isinstance(pid, str) or not pid.strip():
        raise ValueError("paket kimliği geçersiz")
    kaynak = paket["girdi_kaynagi"]
    if kaynak not in GECERLI_KAYNAKLAR:
        raise ValueError("girdi kaynağı geçersiz")
    for alan in ("icerik_metni", "aday_yanit", "canary"):
        if not isinstance(paket[alan], str) or not paket[alan].strip():
            raise ValueError("metin alanı boş olamaz")
    if not isinstance(paket["bellek_yaz_istegi"], bool) or not isinstance(paket["kullanici_onayi"], bool):
        raise ValueError("bellek ve onay bayrakları bool olmalı")
    arac = paket["istenen_arac"]
    if arac not in GECERLI_ARACLAR:
        raise ValueError("istenen araç geçersiz")

    icerik_temiz = paket["icerik_metni"].strip()
    sarmalanmis_girdi = (
        f"<dis_belge_verisi>{icerik_temiz}</dis_belge_verisi>"
        if kaynak == "dis_belge"
        else icerik_temiz
    )
    bellek_izni = bool(
        paket["bellek_yaz_istegi"]
        and kaynak == "kullanici"
        and paket["kullanici_onayi"]
    )
    arac_izni = arac in izinli_araclar
    sizinti_var = paket["canary"].lower() in paket["aday_yanit"].lower()

    engeller = []
    if not arac_izni:
        engeller.append("yetkisiz_arac")
    if paket["bellek_yaz_istegi"] and not bellek_izni:
        engeller.append("onaysiz_bellek")
    if sizinti_var:
        engeller.append("canary_sizintisi")

    durum = "engellendi" if engeller else "onaylandi"
    son_yanit = "[GUVENLIK_YAMASI_ENGELLEDI]" if engeller else paket["aday_yanit"].strip()
    return {
        "paket_id": pid,
        "durum": durum,
        "sarmalanmis_girdi": sarmalanmis_girdi,
        "bellek_yazildi": bellek_izni and not engeller,
        "arac_calisti": arac_izni and not engeller,
        "engellenen_nedenler": sorted(engeller),
        "son_yanit": son_yanit,
    }

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_46 as deney
    deney.goster(saha_aciklarini_kesfet, saha_istismar_kaniti_uret, asistan_guvenlik_yamasi)
```

```hint
Önceki üç görevdeki `saha_aciklarini_kesfet`, `saha_istismar_kaniti_uret` ve `asistan_guvenlik_yamasi` çözümlerini birleştir.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Saha bulgusunu çalışan sınırla doğrula

Telemetride şüpheli belge, gerçekleşmiş canary sızıntısı ve yalnız riskli yapılandırma farklı kanıtlardır. Bir bayrak kapatıldığında ilgili saldırı vektörünün gerçekten kapanması ve normal sorunun çalışması birlikte sınanır. Üç vektörü kapatmak bütün asistanın güvenli olduğunu kanıtlamaz; negatif sonuç, sorgulanan sınır ve deneme kümesiyle sınırlıdır.

| Yaygın yanlış | Doğru sınır |
|---|---|
| Yama bayrağı güvenlik kanıtıdır | Bayrak ile gerçek yanıt/yan etki eşleştirilmelidir. |

Sonraki bağlantı: ai-savunma-03. [Birincil kaynak](https://docs.ollama.com/api/chat). Kaynak mekanizmanın ilgili API veya yöntemini açıklar; bu labın başarı oranının kanıtı yerel ham koşudur.
:::
