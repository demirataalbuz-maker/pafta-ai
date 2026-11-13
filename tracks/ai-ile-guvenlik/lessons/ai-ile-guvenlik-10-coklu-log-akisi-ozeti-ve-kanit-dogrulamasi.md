---
id: ai-ile-guvenlik-10
title: "Çoklu Log Akışı Özeti ve Kanıt Satırı Doğrulaması"
summary: JSONL log akışlarını kaynak IP bazında kümele, LLM SOC özetindeki olay kimliği ve IP iddialarını ham log indeksiyle karşılaştırarak halüsinasyonlu iddiaları ele.
timeout: 300
esleme: ai-ile-guvenlik-02, ai-ile-guvenlik-19
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et
Güvenlik Operasyon Merkezlerinde (`SOC`) yüzlerce satırlık `JSONL` log akışını bir dil modeline özetletirken iki kritik hata türü görülür: model ya ham logda hiç bulunmayan bir olay kimliği (`log-999`) uydurur ya da gerçek bir olay kimliğini (`log-101`) yanlış bir kaynak IP adresine (`10.10.8.55`) bağlar (`ai-ile-guvenlik-02` dersindeki kanıt eşleştirme ilkesini hatırla). Güvenilir bir SOC özetleme hattı, modelin her iddiasını ham log indeksiyle deterministik olarak çapraz doğrular.

| Gerçek araç / model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| `JSONL` log ayrıştırıcısını, kaynak IP kümelemesini ve yerel Ollama modelinin (`qwen3`) ürettiği SOC özetini | İlk üç görevde `ham_loglar.jsonl` ve `model_ozet_iddialari.json` içindeki **sentetik** log/iddia verilerini; son görevde canlı `ai_lab.SohbetOturumu` ile SOC log doğrulama deneyini | Yalnızca log kimliği ve IP eşleşmesinin, log kaydının kaynağında saat kayması (`clock skew`) veya IP sahteciliği (`IP spoofing`) olmadığını tek başına kanıtlayabileceğini söyleyemez |

> [!GÜVENLİK]
> **Kapsam ve dürüstlük sınırı:** İlk üç görevdeki `ham_loglar.jsonl` ve `model_ozet_iddialari.json` dosyaları **sentetik** eğitim verisidir; özel ağ (`RFC 1918`) adresleri kullanır ve her çalıştırmada (`setup`) yeniden yüklenir.
:::

::: anlat Log indeksleme ve kanıt doğrulaması üç aşamada çalışır
Doğrulanabilir SOC log özetleme hattı şöyle kurulur:

1. **JSONL Log Kümeleme (`jsonl_log_kumele`):** Her satır `json.loads` ile ayrıştırılır ve `{"olay_id", "kaynak_ip", "olay_turu", "kullanici"}` şeması doğrulanır. Kayıtlar `olay_indeksi[olay_id]` sözlüğüne alınır ve her `kaynak_ip` için sıralı `olay_id` listesi (`ip_kumeleri`) oluşturulur.
2. **Özet İddia Doğrulaması (`ozet_iddia_dogrula`):** Modelin ürettiği bir iddia (`{"iddia_id", "kaynak_ip", "kanit_olay_idleri"}`) iki kontrolden geçer:
   - Kanıt listesindeki herhangi bir `olay_id` `olay_indeksi` içinde yoksa `"uydurma_olay_id"` nedeniyle reddedilir.
   - Kanıt listesindeki tüm `olay_id` kayıtları mevcut olmasına rağmen herhangi birinin `kaynak_ip` değeri iddiadaki `kaynak_ip` ile uyuşmuyorsa `"ip_uyumsuzlugu"` nedeniyle reddedilir.
3. **Doğrulanmış SOC Özeti (`dogrulanmis_soc_ozeti`):** Ham `JSONL` log metnini ve model iddialarını birleştirerek yalnızca kanıtı doğrulanmış iddiaları `onaylanan_iddialar` listesine alır.
:::

::: anlat Bulguyu sınırlı ve doğrulanabilir yaz: kısmi kanıt uyuşmazlığı da reddedilir
Bir model iddiası üç kanıt olay kimliği (`["log-101", "log-102", "log-999"]`) sunmuşsa, ilk ikisinin gerçek olması üçüncü uydurma kanıtı meşrulaştırmaz. Kanıt dizisindeki **her** öğe hem varlık hem de IP aidiyeti bakımından doğrulanmalıdır.
:::

::: tahmin JSONL ayrıştırma ve IP bazlı olay kümelemesini tahmin et
Aşağıdaki Python kodunun çıktısını tahmin et:

```python
import json

metin = (
    '{"olay_id": "e2", "kaynak_ip": "10.0.0.1"}\n'
    '{"olay_id": "e1", "kaynak_ip": "10.0.0.1"}\n'
    '{"olay_id": "e3", "kaynak_ip": "10.0.0.2"}\n'
)
kumeler = {}
for s in metin.splitlines():
    k = json.loads(s)
    kumeler.setdefault(k["kaynak_ip"], []).append(k["olay_id"])
print({ip: sorted(v) for ip, v in sorted(kumeler.items())})
```

???

```cikti
{'10.0.0.1': ['e1', 'e2'], '10.0.0.2': ['e3']}
```

Aynı kaynak IP adresine (`'10.0.0.1'`) ait olaylar tek listede toplanır ve alfabetik sıralandığında `['e1', 'e2']` elde edilir.
:::

::: gorev 1 · JSONL log akışını ayrıştır ve kaynak IP bazında kümele
`jsonl_log_kumele(jsonl_metni)` işlevini yaz.

Girdi kuralları:
- `jsonl_metni`: boş olmayan (`strip()` sonrası dolu) `str`.
- Boş olmayan her satır geçerli bir JSON nesnesi (`dict`) olmalı ve tam olarak `{"olay_id", "kaynak_ip", "olay_turu", "kullanici"}` anahtarlarını taşımalıdır.
- Dört alanın tamamı boş olmayan (`strip()` sonrası dolu) `str` olmalı ve `olay_id` değerleri benzersiz olmalıdır.
- Kurallara uymayan girdilerde `ValueError` yükselt.

Kümeleme kuralları:
- `olay_indeksi`: `{olay_id: kayit_sozlugu}` eşlemesi.
- `ip_kumeleri`: `{kaynak_ip: sorted(olay_id_listesi)}` eşlemesi.
- `{"olay_indeksi": olay_indeksi, "ip_kumeleri": ip_kumeleri, "toplam_olay": len(olay_indeksi)}` sözlüğünü döndür.

```starter
import json
from ai_ile_guvenlik_veri import metin_yukle

metin = metin_yukle("ham_loglar.jsonl")

def jsonl_log_kumele(jsonl_metni):
    # HATA: IP kümelerini ve şema doğrulamasını oluşturmuyor.
    return {
        "olay_indeksi": {},
        "ip_kumeleri": {},
        "toplam_olay": 0,
    }

print(jsonl_log_kumele(metin))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-10")
```

```test
need("jsonl_log_kumele")

ORNEK_JSONL = (
    '{"olay_id": "log-2", "kaynak_ip": "10.0.0.1", "olay_turu": "giris", "kullanici": "root"}\n\n'
    '{"olay_id": "log-1", "kaynak_ip": "10.0.0.1", "olay_turu": "giris", "kullanici": "admin"}\n'
    '{"olay_id": "log-3", "kaynak_ip": "10.0.0.2", "olay_turu": "okuma", "kullanici": "analist"}\n'
)

def sozlesme(fn):
    try:
        r = fn(ORNEK_JSONL)
        if r["ip_kumeleri"] != {"10.0.0.1": ["log-1", "log-2"], "10.0.0.2": ["log-3"]}:
            return False
        if r["toplam_olay"] != 3 or set(r["olay_indeksi"].keys()) != {"log-1", "log-2", "log-3"}:
            return False

        hatalilar = [
            None,
            123,
            "",
            "   \n ",
            "{bozuk",
            "[1, 2]",
            '{"olay_id": "log-1"}',
            '{"olay_id": "", "kaynak_ip": "10.0.0.1", "olay_turu": "g", "kullanici": "u"}',
            '{"olay_id": "log-1", "kaynak_ip": "  ", "olay_turu": "g", "kullanici": "u"}',
            '{"olay_id": "log-1", "kaynak_ip": 123, "olay_turu": "g", "kullanici": "u"}',
            (
                '{"olay_id": "log-1", "kaynak_ip": "10.0.0.1", "olay_turu": "g", "kullanici": "u"}\n'
                '{"olay_id": "log-1", "kaynak_ip": "10.0.0.2", "olay_turu": "g", "kullanici": "u"}'
            ),
        ]
        for h in hatalilar:
            try:
                fn(h)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(jsonl_log_kumele), "JSONL log akışı doğru indekslenmeli ve kaynak IP bazında kümelenmeli")
def m_sirasiz(m):
    r = jsonl_log_kumele(m)
    return dict(r, ip_kumeleri={k: list(reversed(v)) for k, v in r["ip_kumeleri"].items()})
def m_sifir(m):
    return dict(jsonl_log_kumele(m), toplam_olay=0)
for ad, mutant in [("IP küme sırasını bozan", m_sirasiz), ("toplam olayı sıfırlayan", m_sifir)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

eq(jsonl_log_kumele('   \n'+ORNEK_JSONL+'\n\t'),jsonl_log_kumele(ORNEK_JSONL),'JSONL whitespace satırı')
```

```solution
import json

def jsonl_log_kumele(jsonl_metni):
    if not isinstance(jsonl_metni, str) or not jsonl_metni.strip():
        raise ValueError("jsonl_metni boş olmayan string olmalı")

    olay_indeksi = {}
    ip_kumeleri = {}
    beklenen = {"olay_id", "kaynak_ip", "olay_turu", "kullanici"}

    for satir in jsonl_metni.splitlines():
        s = satir.strip()
        if not s:
            continue
        try:
            kayit = json.loads(s)
        except Exception as e:
            raise ValueError("geçersiz JSON satırı") from e
        if not isinstance(kayit, dict) or set(kayit.keys()) != beklenen:
            raise ValueError("log kaydı şeması geçersiz")
        if not all(isinstance(kayit[k], str) and bool(kayit[k].strip()) for k in beklenen):
            raise ValueError("log alanları boş olmayan string olmalı")

        oid = kayit["olay_id"]
        if oid in olay_indeksi:
            raise ValueError("tekrarlanan olay_id")
        olay_indeksi[oid] = kayit
        ip_kumeleri.setdefault(kayit["kaynak_ip"], []).append(oid)

    for ip in ip_kumeleri:
        ip_kumeleri[ip].sort()

    return {
        "olay_indeksi": olay_indeksi,
        "ip_kumeleri": ip_kumeleri,
        "toplam_olay": len(olay_indeksi),
    }
```

```hint
Boş satırları `if not s: continue` ile atla; her kaydı `olay_indeksi[oid]` içine koy ve `ip_kumeleri.setdefault(ip, []).append(oid)` sonrası listeleri sırala.
```
:::

::: gorev 2 · Modelin özet iddiasındaki olay kimliklerini ve kaynak IP eşleşmesini doğrula
`ozet_iddia_dogrula(iddia, olay_indeksi)` işlevini yaz.

Girdi kuralları:
- `iddia`: tam olarak `{"iddia_id", "kaynak_ip", "kanit_olay_idleri"}` anahtarlarına sahip `dict`.
- `iddia_id` ve `kaynak_ip`: boş olmayan (`strip()` sonrası dolu) `str`.
- `kanit_olay_idleri`: boş olmayan `list`; her öğesi boş olmayan (`strip()` sonrası dolu) `str` olmalıdır.
- `olay_indeksi`: boş olmayan `dict`.
- Kurallara uymayan girdilerde `ValueError` yükselt.

Doğrulama kuralları (sırasıyla):
1. `kanit_olay_idleri` içindeki herhangi bir kimlik `olay_indeksi` içinde yoksa `{"iddia_id": iddia_id, "gecerli": False, "neden": "uydurma_olay_id"}` döndür.
2. Herhangi bir kanıt olayının `olay_indeksi[oid].get("kaynak_ip")` değeri `iddia["kaynak_ip"]` ile aynı değilse `{"iddia_id": iddia_id, "gecerli": False, "neden": "ip_uyumsuzlugu"}` döndür.
3. Tümü eşleşiyorsa `{"iddia_id": iddia_id, "gecerli": True, "neden": "dogrulandi"}` döndür.

```starter
from ai_ile_guvenlik_veri import json_yukle

iddialar = json_yukle("model_ozet_iddialari.json")["iddialar"]

def ozet_iddia_dogrula(iddia, olay_indeksi):
    # HATA: Olay kimliğinin varlığını ve IP eşleşmesini kontrol etmiyor.
    return {"iddia_id": iddia["iddia_id"], "gecerli": True, "neden": "dogrulandi"}

print(ozet_iddia_dogrula(iddialar[0], {"log-101": {"kaynak_ip": "10.10.4.21"}}))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-10")
```

```test
need("ozet_iddia_dogrula")

INDEKS = {
    "log-1": {"olay_id": "log-1", "kaynak_ip": "10.0.0.1"},
    "log-2": {"olay_id": "log-2", "kaynak_ip": "10.0.0.1"},
    "log-3": {"olay_id": "log-3", "kaynak_ip": "10.0.0.2"},
}

def sozlesme(fn):
    try:
        if fn({"iddia_id": "i1", "kaynak_ip": "10.0.0.1", "kanit_olay_idleri": ["log-1", "log-2"]}, INDEKS) != {
            "iddia_id": "i1",
            "gecerli": True,
            "neden": "dogrulandi",
        }:
            return False

        if fn({"iddia_id": "i2", "kaynak_ip": "10.0.0.1", "kanit_olay_idleri": ["log-1", "log-99"]}, INDEKS) != {
            "iddia_id": "i2",
            "gecerli": False,
            "neden": "uydurma_olay_id",
        }:
            return False

        if fn({"iddia_id": "i3", "kaynak_ip": "10.0.0.1", "kanit_olay_idleri": ["log-1", "log-3"]}, INDEKS) != {
            "iddia_id": "i3",
            "gecerli": False,
            "neden": "ip_uyumsuzlugu",
        }:
            return False

        hatalilar = [
            (None, INDEKS),
            ({}, INDEKS),
            ({"iddia_id": "i1"}, INDEKS),
            ({"iddia_id": "", "kaynak_ip": "10.0.0.1", "kanit_olay_idleri": ["log-1"]}, INDEKS),
            ({"iddia_id": "i1", "kaynak_ip": "   ", "kanit_olay_idleri": ["log-1"]}, INDEKS),
            ({"iddia_id": 123, "kaynak_ip": "10.0.0.1", "kanit_olay_idleri": ["log-1"]}, INDEKS),
            ({"iddia_id": "i1", "kaynak_ip": None, "kanit_olay_idleri": ["log-1"]}, INDEKS),
            ({"iddia_id": "i1", "kaynak_ip": "10.0.0.1", "kanit_olay_idleri": []}, INDEKS),
            ({"iddia_id": "i1", "kaynak_ip": "10.0.0.1", "kanit_olay_idleri": "log-1"}, INDEKS),
            ({"iddia_id": "i1", "kaynak_ip": "10.0.0.1", "kanit_olay_idleri": [""]}, INDEKS),
            ({"iddia_id": "i1", "kaynak_ip": "10.0.0.1", "kanit_olay_idleri": [123]}, INDEKS),
            ({"iddia_id": "i1", "kaynak_ip": "10.0.0.1", "kanit_olay_idleri": ["log-1"]}, None),
            ({"iddia_id": "i1", "kaynak_ip": "10.0.0.1", "kanit_olay_idleri": ["log-1"]}, 123),
            ({"iddia_id": "i1", "kaynak_ip": "10.0.0.1", "kanit_olay_idleri": ["log-1"]}, {}),
        ]
        for idd_in, ind_in in hatalilar:
            try:
                fn(idd_in, ind_in)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(ozet_iddia_dogrula), "özet iddia doğrulaması uydurma olay kimliklerini ve IP uyumsuzluklarını yakalamalı")
def m_hep_gecerli(i, ind):
    return dict(ozet_iddia_dogrula(i, ind), gecerli=True, neden="dogrulandi")
def m_ip_atlayan(i, ind):
    r = ozet_iddia_dogrula(i, ind)
    return {"iddia_id": i["iddia_id"], "gecerli": True, "neden": "dogrulandi"} if r["neden"] == "ip_uyumsuzlugu" else r
for ad, mutant in [("hep geçerli sayan", m_hep_gecerli), ("IP uyumsuzluğunu atlayan", m_ip_atlayan)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

raises(ValueError,ozet_iddia_dogrula,{'iddia_id':'x','kaynak_ip':'10.0.0.1','kanit_olay_idleri':['   ']},INDEKS,msg='whitespace kanıt kimliği')
```

```solution
def ozet_iddia_dogrula(iddia, olay_indeksi):
    if not isinstance(iddia, dict) or set(iddia.keys()) != {"iddia_id", "kaynak_ip", "kanit_olay_idleri"}:
        raise ValueError("iddia şeması geçersiz")
    if not isinstance(olay_indeksi, dict) or not olay_indeksi:
        raise ValueError("olay_indeksi boş olmayan sözlük olmalı")

    iid = iddia["iddia_id"]
    ip = iddia["kaynak_ip"]
    kanitlar = iddia["kanit_olay_idleri"]

    if not all(isinstance(x, str) and bool(x.strip()) for x in (iid, ip)):
        raise ValueError("iddia_id ve kaynak_ip boş olamaz")
    if not isinstance(kanitlar, list) or not kanitlar or not all(isinstance(x, str) and bool(x.strip()) for x in kanitlar):
        raise ValueError("kanit_olay_idleri boş olmayan string listesi olmalı")

    if any(oid not in olay_indeksi for oid in kanitlar):
        return {"iddia_id": iid, "gecerli": False, "neden": "uydurma_olay_id"}

    if any(olay_indeksi[oid].get("kaynak_ip") != ip for oid in kanitlar):
        return {"iddia_id": iid, "gecerli": False, "neden": "ip_uyumsuzlugu"}

    return {"iddia_id": iid, "gecerli": True, "neden": "dogrulandi"}
```

```hint
Önce `any(oid not in olay_indeksi for oid in kanitlar)` ile uydurma olay kimliklerini, ardından `any(olay_indeksi[oid].get("kaynak_ip") != ip for oid in kanitlar)` ile IP uyumsuzluğunu kontrol et.
```
:::

::: gorev 3 · Ham log akışı ve model iddialarından doğrulanmış SOC özeti üret
`dogrulanmis_soc_ozeti(jsonl_metni, iddialar)` işlevini yaz.

Girdi kuralları:
- `jsonl_metni`: 1. görevdeki kurallarla aynıdır.
- `iddialar`: boş olmayan `list`; her öğesi 2. görevdeki iddia şemasına uymalı ve `iddia_id` değerleri benzersiz olmalıdır.
- Kurallara uymayan girdilerde `ValueError` yükselt.

Özetleme kuralları:
1. `jsonl_metni` girdisini 1. görevdeki kurallarla indeksle.
2. `iddialar` listesindeki her iddiayı 2. görevdeki kurallarla doğrula:
   - `gecerli == True` ise `onaylanan_iddialar` listesine `iddia_id` ekle.
   - `gecerli == False` ise `reddedilen_iddialar[iddia_id] = neden` olarak kaydet.
3. `{"onaylanan_iddialar": sorted(...), "reddedilen_iddialar": ..., "toplam_olay": ...}` sözlüğünü döndür.

```starter
from ai_ile_guvenlik_veri import json_yukle, metin_yukle

metin = metin_yukle("ham_loglar.jsonl")
iddialar = json_yukle("model_ozet_iddialari.json")["iddialar"]

def dogrulanmis_soc_ozeti(jsonl_metni, iddialar):
    # HATA: İddiaları doğrulamadan hepsini onaylıyor.
    return {
        "onaylanan_iddialar": [i["iddia_id"] for i in iddialar],
        "reddedilen_iddialar": {},
        "toplam_olay": 0,
    }

print(dogrulanmis_soc_ozeti(metin, iddialar))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-10")
```

```test
need("dogrulanmis_soc_ozeti")

JSONL = (
    '{"olay_id": "log-101", "kaynak_ip": "10.10.4.21", "olay_turu": "basarisiz_giris", "kullanici": "admin"}\n'
    '{"olay_id": "log-102", "kaynak_ip": "10.10.4.21", "olay_turu": "basarili_giris", "kullanici": "admin"}\n'
    '{"olay_id": "log-104", "kaynak_ip": "10.10.8.55", "olay_turu": "dosya_okuma", "kullanici": "analist"}\n'
)

IDDIALAR = [
    {"iddia_id": "id-1", "kaynak_ip": "10.10.4.21", "kanit_olay_idleri": ["log-101", "log-102"]},
    {"iddia_id": "id-2", "kaynak_ip": "192.168.99.99", "kanit_olay_idleri": ["log-999"]},
    {"iddia_id": "id-3", "kaynak_ip": "10.10.8.55", "kanit_olay_idleri": ["log-101"]},
]

def sozlesme(fn):
    try:
        r = fn(JSONL, IDDIALAR)
        if r != {
            "onaylanan_iddialar": ["id-1"],
            "reddedilen_iddialar": {
                "id-2": "uydurma_olay_id",
                "id-3": "ip_uyumsuzlugu",
            },
            "toplam_olay": 3,
        }:
            return False

        if fn(JSONL + "\n", [IDDIALAR[0]])["onaylanan_iddialar"] != ["id-1"]:
            return False

        hatalilar = [
            (None, IDDIALAR),
            ("", IDDIALAR),
            ("{bozuk", IDDIALAR),
            ("[1, 2]", IDDIALAR),
            ('{"olay_id": 1, "kaynak_ip": "1.1.1.1", "olay_turu": "a", "kullanici": "b"}', IDDIALAR),
            ('{"olay_id": "1"}', IDDIALAR),
            ('{"olay_id": "", "kaynak_ip": "1.1.1.1", "olay_turu": "a", "kullanici": "b"}', IDDIALAR),
            (
                '{"olay_id": "1", "kaynak_ip": "1.1.1.1", "olay_turu": "a", "kullanici": "b"}\n'
                '{"olay_id": "1", "kaynak_ip": "1.1.1.1", "olay_turu": "a", "kullanici": "b"}',
                IDDIALAR,
            ),
            (JSONL, None),
            (JSONL, 123),
            (JSONL, []),
            (JSONL, [123]),
            (JSONL, [{}]),
            (JSONL, [{"iddia_id": 1, "kaynak_ip": "10.10.4.21", "kanit_olay_idleri": ["log-101"]}]),
            (JSONL, [{"iddia_id": "id-1", "kaynak_ip": "10.10.4.21", "kanit_olay_idleri": 123}]),
            (JSONL, [{"iddia_id": "id-1", "kaynak_ip": "10.10.4.21", "kanit_olay_idleri": [123]}]),
            (JSONL, [{"iddia_id": "", "kaynak_ip": "10.10.4.21", "kanit_olay_idleri": ["log-101"]}]),
            (JSONL, [{"iddia_id": "id-1", "kaynak_ip": "10.10.4.21", "kanit_olay_idleri": []}]),
            (JSONL, [{"iddia_id": "id-1", "kaynak_ip": "10.10.4.21", "kanit_olay_idleri": [""]}]),
            (JSONL, [IDDIALAR[0], IDDIALAR[0]]),
        ]
        for j_in, i_in in hatalilar:
            try:
                fn(j_in, i_in)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(dogrulanmis_soc_ozeti), "doğrulanmış SOC özeti halüsinasyonlu ve uyumsuz iddiaları reddetmeli")
def m_red_silen(j, i):
    return dict(dogrulanmis_soc_ozeti(j, i), reddedilen_iddialar={})
def m_onay_silen(j, i):
    return dict(dogrulanmis_soc_ozeti(j, i), onaylanan_iddialar=[])
for ad, mutant in [("reddedilenleri silen", m_red_silen), ("onaylananları silen", m_onay_silen)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

import json
_idd={'iddia_id':'x','kaynak_ip':'10.10.4.21','kanit_olay_idleri':['log-101']}
eq(dogrulanmis_soc_ozeti('   \n'+JSONL+'\n\t',[_idd]),dogrulanmis_soc_ozeti(JSONL,[_idd]),'JSONL whitespace satırı')
raises(ValueError,dogrulanmis_soc_ozeti,JSONL,[dict(_idd,iddia_id='   ')],msg='whitespace iddia kimliği')
raises(ValueError,dogrulanmis_soc_ozeti,JSONL,[dict(_idd,kanit_olay_idleri=['   '])],msg='whitespace kanıt kimliği')
_tek=json.loads(JSONL.splitlines()[0]);_tek['kullanici']='   '
raises(ValueError,dogrulanmis_soc_ozeti,json.dumps(_tek),[_idd],msg='whitespace log alanı')
```

```solution
import json

def _kumele(jsonl_metni):
    if not isinstance(jsonl_metni, str) or not jsonl_metni.strip():
        raise ValueError("jsonl_metni boş olmayan string olmalı")
    olay_indeksi = {}
    beklenen = {"olay_id", "kaynak_ip", "olay_turu", "kullanici"}
    for satir in jsonl_metni.splitlines():
        s = satir.strip()
        if not s:
            continue
        try:
            kayit = json.loads(s)
        except Exception as e:
            raise ValueError("geçersiz JSON satırı") from e
        if not isinstance(kayit, dict) or set(kayit.keys()) != beklenen:
            raise ValueError("log kaydı şeması geçersiz")
        if not all(isinstance(kayit[k], str) and bool(kayit[k].strip()) for k in beklenen):
            raise ValueError("log alanları boş olmayan string olmalı")
        oid = kayit["olay_id"]
        if oid in olay_indeksi:
            raise ValueError("tekrarlanan olay_id")
        olay_indeksi[oid] = kayit
    return olay_indeksi

def _iddia_kontrol(iddia, olay_indeksi):
    if not isinstance(iddia, dict) or set(iddia.keys()) != {"iddia_id", "kaynak_ip", "kanit_olay_idleri"}:
        raise ValueError("iddia şeması geçersiz")
    iid = iddia["iddia_id"]
    ip = iddia["kaynak_ip"]
    kanitlar = iddia["kanit_olay_idleri"]
    if not all(isinstance(x, str) and bool(x.strip()) for x in (iid, ip)):
        raise ValueError("iddia_id ve kaynak_ip boş olamaz")
    if not isinstance(kanitlar, list) or not kanitlar or not all(isinstance(x, str) and bool(x.strip()) for x in kanitlar):
        raise ValueError("kanit_olay_idleri boş olmayan string listesi olmalı")
    if any(oid not in olay_indeksi for oid in kanitlar):
        return iid, False, "uydurma_olay_id"
    if any(olay_indeksi[oid].get("kaynak_ip") != ip for oid in kanitlar):
        return iid, False, "ip_uyumsuzlugu"
    return iid, True, "dogrulandi"

def dogrulanmis_soc_ozeti(jsonl_metni, iddialar):
    if not isinstance(iddialar, list) or not iddialar:
        raise ValueError("iddialar boş olamaz")
    indeks = _kumele(jsonl_metni)

    onaylanan = []
    reddedilen = {}
    gorulen = set()

    for idd in iddialar:
        iid, gecerli, neden = _iddia_kontrol(idd, indeks)
        if iid in gorulen:
            raise ValueError("tekrarlanan iddia_id")
        gorulen.add(iid)
        if gecerli:
            onaylanan.append(iid)
        else:
            reddedilen[iid] = neden

    return {
        "onaylanan_iddialar": sorted(onaylanan),
        "reddedilen_iddialar": reddedilen,
        "toplam_olay": len(indeks),
    }
```

```hint
Önce JSONL loglarını indeksle; ardından her iddiayı indeksle karşılaştırarak geçerli olanları `onaylanan_iddialar` listesine, geçersiz olanları `reddedilen_iddialar` sözlüğüne yaz.
```
:::

::: gorev Gerçek deney · Yerel modelle SOC log özeti ve kanıt satırı doğrulaması
Önceki üç görevde yazdığın `jsonl_log_kumele`, `ozet_iddia_dogrula` ve `dogrulanmis_soc_ozeti` işlevlerini bu adımda birleştir.

Canlı deneyde:
1. Ham `JSONL` log akışı `jsonl_log_kumele` ile indekslenir ve yerel Ollama modeline (`ai_lab.SohbetOturumu`) özetletilir.
2. Doğru kanıtlı iddia (`id-1`), uydurma olay kimlikli iddia (`id-2`) ve yanlış IP eşleştirmeli iddia (`id-3`) `dogrulanmis_soc_ozeti` süzgecinden geçirilir.
3. Yalnız ham logda kanıtı bulunan iddianın onaylandığı doğrulanır.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def jsonl_log_kumele(jsonl_metni):
    return {}

def ozet_iddia_dogrula(iddia, olay_indeksi):
    return {}

def dogrulanmis_soc_ozeti(jsonl_metni, iddialar):
    return {}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_ile_guvenlik_10 as deney
    deney.goster(jsonl_log_kumele, ozet_iddia_dogrula, dogrulanmis_soc_ozeti)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-10")
```

```test
import ai_lab
from sandbox import ai_gercek_ai_ile_guvenlik_10 as D

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for ad in ("jsonl_log_kumele", "ozet_iddia_dogrula", "dogrulanmis_soc_ozeti"):
    need(ad)

sorun = ai_lab.kod_denetimi(
    src,
    ("jsonl_log_kumele_referans", "ozet_iddia_dogrula_referans", "dogrulanmis_soc_ozeti_referans"),
)
ok(not sorun, "laboratuvar yamalanmamalı, referans işlevler çağrılmamalı")

def _on_sozlesme():
    try:
        ornek_jl = (
            '{"olay_id": "log-2", "kaynak_ip": "10.0.0.1", "olay_turu": "giris", "kullanici": "root"}\n\n'
            '{"olay_id": "log-1", "kaynak_ip": "10.0.0.1", "olay_turu": "giris", "kullanici": "admin"}\n'
            '{"olay_id": "log-3", "kaynak_ip": "10.0.0.2", "olay_turu": "okuma", "kullanici": "analist"}\n'
        )
        kume = jsonl_log_kumele(ornek_jl)
        if kume["ip_kumeleri"] != {"10.0.0.1": ["log-1", "log-2"], "10.0.0.2": ["log-3"]} or kume["toplam_olay"] != 3: return False
        ind = kume["olay_indeksi"]
        if ozet_iddia_dogrula({"iddia_id": "i1", "kaynak_ip": "10.0.0.1", "kanit_olay_idleri": ["log-1", "log-2"]}, ind) != {"iddia_id": "i1", "gecerli": True, "neden": "dogrulandi"}: return False
        if ozet_iddia_dogrula({"iddia_id": "i2", "kaynak_ip": "10.0.0.1", "kanit_olay_idleri": ["log-99"]}, ind) != {"iddia_id": "i2", "gecerli": False, "neden": "uydurma_olay_id"}: return False
        if ozet_iddia_dogrula({"iddia_id": "i3", "kaynak_ip": "10.0.0.1", "kanit_olay_idleri": ["log-3"]}, ind) != {"iddia_id": "i3", "gecerli": False, "neden": "ip_uyumsuzlugu"}: return False
        soc = dogrulanmis_soc_ozeti(ornek_jl, [
            {"iddia_id": "i1", "kaynak_ip": "10.0.0.1", "kanit_olay_idleri": ["log-1"]},
            {"iddia_id": "i2", "kaynak_ip": "10.0.0.1", "kanit_olay_idleri": ["log-99"]},
            {"iddia_id": "i3", "kaynak_ip": "10.0.0.1", "kanit_olay_idleri": ["log-3"]},
        ])
        if soc != {"onaylanan_iddialar": ["i1"], "reddedilen_iddialar": {"i2": "uydurma_olay_id", "i3": "ip_uyumsuzlugu"}, "toplam_olay": 3}: return False
        for h in (
            None, 123, "", "   ", "{bozuk", "[1, 2]",
            '{"olay_id": "1"}',
            '{"olay_id": 1, "kaynak_ip": "1.1.1.1", "olay_turu": "a", "kullanici": "b"}',
            '{"olay_id": "", "kaynak_ip": "1.1.1.1", "olay_turu": "a", "kullanici": "b"}',
            '{"olay_id": "1", "kaynak_ip": "1.1.1.1", "olay_turu": "a", "kullanici": "b"}\n{"olay_id": "1", "kaynak_ip": "1.1.1.1", "olay_turu": "a", "kullanici": "b"}',
        ):
            try:
                jsonl_log_kumele(h)
                return False
            except ValueError:
                pass
        for idd_in, ind_in in [
            (None, ind), (123, ind), ({}, ind),
            ({"iddia_id": 1, "kaynak_ip": "10.0.0.1", "kanit_olay_idleri": ["log-1"]}, ind),
            ({"iddia_id": "", "kaynak_ip": "10.0.0.1", "kanit_olay_idleri": ["log-1"]}, ind),
            ({"iddia_id": "i1", "kaynak_ip": "10.0.0.1", "kanit_olay_idleri": 123}, ind),
            ({"iddia_id": "i1", "kaynak_ip": "10.0.0.1", "kanit_olay_idleri": []}, ind),
            ({"iddia_id": "i1", "kaynak_ip": "10.0.0.1", "kanit_olay_idleri": [""]}, ind),
            ({"iddia_id": "i1", "kaynak_ip": "10.0.0.1", "kanit_olay_idleri": [123]}, ind),
            ({"iddia_id": "i1", "kaynak_ip": "10.0.0.1", "kanit_olay_idleri": ["log-1"]}, None),
            ({"iddia_id": "i1", "kaynak_ip": "10.0.0.1", "kanit_olay_idleri": ["log-1"]}, 123),
            ({"iddia_id": "i1", "kaynak_ip": "10.0.0.1", "kanit_olay_idleri": ["log-1"]}, {}),
        ]:
            try:
                ozet_iddia_dogrula(idd_in, ind_in)
                return False
            except ValueError:
                pass
        for i_list in (None, 123, [], [D.ADAY_IDDIALAR[0], D.ADAY_IDDIALAR[0]]):
            try:
                dogrulanmis_soc_ozeti(D.HAM_LOG_METNI, i_list)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(_on_sozlesme(), "sentetik ön kontrol: log kümeleme ve iddia doğrulama kuralları tam")

if not all(checks):
    stop()

try:
    r = D.deney(jsonl_log_kumele, ozet_iddia_dogrula, dogrulanmis_soc_ozeti)
except Exception as e:
    ok(False, f"GERÇEK SOC LOG ÖZETİ DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

for ad, deger in r["kontroller"].items():
    ok(deger, "gerçek deney: " + ad)

ai_lab.kanit_yaz("ile-guvenlik-10-log", {
    "kaynak": "gercek",
    "kabul": all(checks),
    "ders": "ai-ile-guvenlik-10",
    "ortam": r["ortam"],
    "ayarlar": r["ayarlar"],
    "deney": r,
    "ozet": r["ozet"],
})
o = r["ozet"]
ok(
    True,
    f"BULGU ({o['model']}): onaylanan={o['onaylanan']}, reddedilen={o['reddedilen']}.",
)
```

```solution
import json
import ai_lab

def jsonl_log_kumele(jsonl_metni):
    if not isinstance(jsonl_metni, str) or not jsonl_metni.strip():
        raise ValueError("jsonl_metni boş olmayan string olmalı")

    olay_indeksi = {}
    ip_kumeleri = {}
    beklenen = {"olay_id", "kaynak_ip", "olay_turu", "kullanici"}

    for satir in jsonl_metni.splitlines():
        s = satir.strip()
        if not s:
            continue
        try:
            kayit = json.loads(s)
        except Exception as e:
            raise ValueError("geçersiz JSON satırı") from e
        if not isinstance(kayit, dict) or set(kayit.keys()) != beklenen:
            raise ValueError("log kaydı şeması geçersiz")
        if not all(isinstance(kayit[k], str) and bool(kayit[k].strip()) for k in beklenen):
            raise ValueError("log alanları boş olmayan string olmalı")

        oid = kayit["olay_id"]
        if oid in olay_indeksi:
            raise ValueError("tekrarlanan olay_id")
        olay_indeksi[oid] = kayit
        ip_kumeleri.setdefault(kayit["kaynak_ip"], []).append(oid)

    for ip in ip_kumeleri:
        ip_kumeleri[ip].sort()

    return {
        "olay_indeksi": olay_indeksi,
        "ip_kumeleri": ip_kumeleri,
        "toplam_olay": len(olay_indeksi),
    }

def ozet_iddia_dogrula(iddia, olay_indeksi):
    if not isinstance(iddia, dict) or set(iddia.keys()) != {"iddia_id", "kaynak_ip", "kanit_olay_idleri"}:
        raise ValueError("iddia şeması geçersiz")
    if not isinstance(olay_indeksi, dict) or not olay_indeksi:
        raise ValueError("olay_indeksi boş olmayan sözlük olmalı")

    iid = iddia["iddia_id"]
    ip = iddia["kaynak_ip"]
    kanitlar = iddia["kanit_olay_idleri"]

    if not all(isinstance(x, str) and bool(x.strip()) for x in (iid, ip)):
        raise ValueError("iddia_id ve kaynak_ip boş olamaz")
    if not isinstance(kanitlar, list) or not kanitlar or not all(isinstance(x, str) and bool(x.strip()) for x in kanitlar):
        raise ValueError("kanit_olay_idleri boş olmayan string listesi olmalı")

    if any(oid not in olay_indeksi for oid in kanitlar):
        return {"iddia_id": iid, "gecerli": False, "neden": "uydurma_olay_id"}

    if any(olay_indeksi[oid].get("kaynak_ip") != ip for oid in kanitlar):
        return {"iddia_id": iid, "gecerli": False, "neden": "ip_uyumsuzlugu"}

    return {"iddia_id": iid, "gecerli": True, "neden": "dogrulandi"}

def dogrulanmis_soc_ozeti(jsonl_metni, iddialar):
    if not isinstance(iddialar, list) or not iddialar:
        raise ValueError("iddialar boş olamaz")
    kume = jsonl_log_kumele(jsonl_metni)
    indeks = kume["olay_indeksi"]

    onaylanan = []
    reddedilen = {}
    gorulen = set()

    for idd in iddialar:
        sonuc = ozet_iddia_dogrula(idd, indeks)
        iid = sonuc["iddia_id"]
        if iid in gorulen:
            raise ValueError("tekrarlanan iddia_id")
        gorulen.add(iid)

        if sonuc["gecerli"]:
            onaylanan.append(iid)
        else:
            reddedilen[iid] = sonuc["neden"]

    return {
        "onaylanan_iddialar": sorted(onaylanan),
        "reddedilen_iddialar": reddedilen,
        "toplam_olay": kume["toplam_olay"],
    }

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_ile_guvenlik_10 as deney
    deney.goster(jsonl_log_kumele, ozet_iddia_dogrula, dogrulanmis_soc_ozeti)
```

```hint
Önceki üç görevdeki `jsonl_log_kumele`, `ozet_iddia_dogrula` ve `dogrulanmis_soc_ozeti` işlevlerini birleştir.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### SOC özeti olay kimliğini kanıt satırına bağlar

Modelin kaynak IP ve olay kimliği hakkındaki iddiası ham JSONL kaydıyla çaprazlanır. Doğru IPyi yanlış olayla eşlemek kanıt değildir. Yinelenen kimlik veya bozuk satır sessizce atılırsa özetin dayanağı değişir. Kabul edilen özet yalnız doğrulanan iddiaları taşır; logun kendisinin gerçek dünyadan ve dürüst bir kaynaktan geldiği ayrıca varsayılır.

| Yaygın yanlış | Kontrolün gösterdiği |
|---|---|
| İkna edici özet kanıtlı özettir | Her iddia doğru satır ve kaynakla eşleşmelidir. |

Sonraki bağlantı: ai-ile-guvenlik-19. [Birincil kaynak](https://opentelemetry.io/docs/concepts/signals/traces/). Kaynak ilgili araç veya yöntemi açıklar; labın gerçek sonucu ham kanıt kaydındadır.
:::
