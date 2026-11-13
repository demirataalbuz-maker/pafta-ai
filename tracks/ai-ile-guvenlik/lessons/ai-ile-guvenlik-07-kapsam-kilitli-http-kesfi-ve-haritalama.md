---
id: ai-ile-guvenlik-07
title: "Kapsam Kilitli HTTP Keşfi ve Parametre Haritalama"
summary: urllib.parse ile aday URL'leri yerel geri-dönüş (127.0.0.1 / localhost) kapsam kilidinden geçir, uç nokta sorgu parametrelerini çıkar ve kapsam dışı hedefleri reddeden güvenli keşif planı üret.
timeout: 300
esleme: ai-saldiri-36, ai-savunma-11, ai-savunma-14
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et
Bir güvenlik ajanına hedef uygulamanın bağlantıları verildiğinde, sayfa içinde üçüncü taraf alan adlarına (`https://dis-hedef.ornek.com`), bulut üstveri servislerine (`http://169.254.169.254/latest/meta-data/`) veya `file://` şemasına işaret eden bağlantılar bulunabilir (`ai-saldiri-36` dersindeki yasal kapsam sınırlarını ve `ai-savunma-11` dersindeki araç izin listelerini hatırla). Modelin *"bu URL'yi de tarayayım"* demesine güvenmek yerine, ağ katmanından önce deterministik bir **kapsam kilidi (`scope lock`)** uygulanır.

| Gerçek araç / model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| `urllib.parse.urlparse` / `parse_qs` ayrıştırmasını, yerel `127.0.0.1` HTTP sunucusunu ve yerel Ollama modelinin (`qwen3`) uç nokta önceliklendirmesini | İlk üç görevde `aday_urller.json` ve `model_kesif_plani.json` içindeki **sentetik** URL verilerini; son görevde canlı `HTTPServer(("127.0.0.1", 0))` ve `ai_lab.SohbetOturumu` ile kapsam kilitli keşif deneyini | Tek başına URL ayrıştırmasının DNS yeniden bağlama (`DNS rebinding`) veya sunucu taraflı yönlendirme (`HTTP 302 redirect`) zincirlerini çalışma zamanı soket kontrolü olmadan engelleyebileceğini söyleyemez |

> [!GÜVENLİK]
> **Kapsam ve dürüstlük sınırı:** İlk üç görevdeki URL listeleri **sentetik** eğitim verisidir. Canlı deney yalnızca yerel geri-dönüş (`127.0.0.1`) üzerinde geçici olarak açılan test sunucusuna bağlanır; dış ağa hiçbir istek gönderilmez.
:::

::: anlat Kapsam kilidi URL bileşenlerini deterministik olarak doğrular
Kapsam kilitli HTTP keşif hattı üç aşamada çalışır:

1. **Kapsam Kilidi Doğrulaması (`kapsam_kilidi_dogrula`):** `urlparse(url.strip())` ile şema (`scheme`), sunucu adı (`hostname`), kullanıcı bilgisi (`username`/`password`) ve yol (`path`) ayrıştırılır. Yalnızca:
   - `sema in ("http", "https")`,
   - `host in ("127.0.0.1", "localhost")`,
   - URL içinde kullanıcı adı veya parola (`user:pass@host`) bulunmayan (`not p.username and not p.password`)
   hedefler `izinli = True` kabul edilir. Boş `path` değeri `"/"` olarak normalize edilir.
2. **Parametre Haritalama (`url_parametre_haritasi`):** Kapsam kilidinden geçen URL'nin sorgu dizgesi `parse_qs(p.query, keep_blank_values=True)` ile ayrıştırılır ve parametre adları alfabetik sırada (`sorted`) çıkarılır. Kapsam dışı URL verilirse `ValueError` yükseltilir.
3. **Güvenli Keşif Planı (`guvenli_kesif_plani`):** Aday URL listesindeki kapsam dışı adresler `engellenen_urller` listesine ayrılır; izinli uç noktalar ise tekilleştirilerek (`gorulen_yollar`) modelin atadığı öncelikle (`"yuksek"`, `"orta"`, `"dusuk"`) birleştirilir.
:::

::: anlat Bulguyu sınırlı ve doğrulanabilir yaz: kapsam dışı URL haritalama aşamasına geçemez
Bir keşif ajanında kapsam dışı URL'lerin yalnızca rapor sonunda filtrelenmesi yeterli değildir; `url_parametre_haritasi` işlevi kapsam dışı bir URL aldığında doğrudan `ValueError` yükselterek haritalama ve istek aşamalarını deterministik olarak durdurmalıdır.
:::

::: tahmin urlparse ve parse_qs ile sunucu adı ve parametre çıkarımını tahmin et
Aşağıdaki Python kodunun çıktısını tahmin et:

```python
from urllib.parse import urlparse, parse_qs

u = "http://127.0.0.1:8080/api/ara?q=test&sayfa=1&bos=#etiket"
p = urlparse(u)
sorgu = parse_qs(p.query, keep_blank_values=True)
print((p.hostname, p.path, sorted(sorgu.keys())))
```

???

```cikti
('127.0.0.1', '/api/ara', ['bos', 'q', 'sayfa'])
```

`p.hostname` port numarasını ayırarak `'127.0.0.1'` döndürür, `#etiket` (`fragment`) sorguya karışmaz ve `keep_blank_values=True` sayesinde boş değerli `'bos'` parametresi de korunur.
:::

::: gorev 1 · URL üzerinde yerel geri-dönüş kapsam kilidini doğrula
`kapsam_kilidi_dogrula(url)` işlevini yaz.

Girdi kuralları:
- `url`: boş olmayan (`strip()` sonrası dolu) `str`. Boş metin veya `str` dışı tipte `ValueError` yükselt.

Doğrulama kuralları:
- `p = urlparse(url.strip())` ile ayrıştır:
  - `sema = p.scheme.lower()`
  - `host = (p.hostname or "").lower()`
  - `yol = p.path if p.path else "/"`
- `izinli`: `sema in ("http", "https")` ve `host in ("127.0.0.1", "localhost")` ve `not p.username` ve `not p.password` ise `True`, aksi hâlde `False`.
- `{"izinli": izinli, "sema": sema, "host": host, "yol": yol}` sözlüğünü döndür.

```starter
from urllib.parse import urlparse
from ai_ile_guvenlik_veri import json_yukle

urller = json_yukle("aday_urller.json")

def kapsam_kilidi_dogrula(url):
    # HATA: Sunucu adını ve şemayı kontrol etmeden her URL'ye izin veriyor.
    p = urlparse(url)
    return {
        "izinli": True,
        "sema": p.scheme,
        "host": p.hostname or "",
        "yol": p.path or "/",
    }

for u in urller:
    print(u, kapsam_kilidi_dogrula(u))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-07")
```

```test
need("kapsam_kilidi_dogrula")

def sozlesme(fn):
    try:
        if fn("http://127.0.0.1:8080/api/kullanici?id=1") != {
            "izinli": True,
            "sema": "http",
            "host": "127.0.0.1",
            "yol": "/api/kullanici",
        }:
            return False

        if fn("HTTPS://LOCALHOST") != {
            "izinli": True,
            "sema": "https",
            "host": "localhost",
            "yol": "/",
        }:
            return False

        for dis in (
            "https://ornek.com/api",
            "http://169.254.169.254/latest/meta-data/",
            "ftp://127.0.0.1/dosya",
            "file:///etc/passwd",
            "http://admin:1234@127.0.0.1:8080/api",
            "http://admin@127.0.0.1:8080/api",
            "http://:parola@127.0.0.1:8080/api",
            "http:///yalniz-yol",
        ):
            if fn(dis)["izinli"] is not False:
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

ok(sozlesme(kapsam_kilidi_dogrula), "kapsam kilidi yalnız yerel http/https hedeflerine izin vermeli")
def m_hep_izinli(u):
    return dict(kapsam_kilidi_dogrula(u), izinli=True)
def m_hep_yasak(u):
    return dict(kapsam_kilidi_dogrula(u), izinli=False)
for ad, mutant in [("dış hedeflere izin veren", m_hep_izinli), ("yerel hedefleri engelleyen", m_hep_yasak)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

eq(kapsam_kilidi_dogrula('http://127.0.0.1/a   '),kapsam_kilidi_dogrula('http://127.0.0.1/a'),'URL son boşluğu kırpılır')
```

```solution
from urllib.parse import urlparse

IZINLI_ADRESLER = ("127.0.0.1", "localhost")

def kapsam_kilidi_dogrula(url):
    if not isinstance(url, str) or not url.strip():
        raise ValueError("url boş olmayan string olmalı")
    p = urlparse(url.strip())
    sema = p.scheme.lower()
    host = (p.hostname or "").lower()
    yol = p.path if p.path else "/"

    izinli = (
        sema in ("http", "https")
        and host in IZINLI_ADRESLER
        and not p.username
        and not p.password
    )
    return {
        "izinli": bool(izinli),
        "sema": sema,
        "host": host,
        "yol": yol,
    }
```

```hint
`urlparse(url.strip())` çıktısında `scheme.lower()`, `(hostname or "").lower()`, `username` ve `password` alanlarını birlikte kontrol et.
```
:::

::: gorev 2 · İzinli URL'nin uç nokta yolunu ve sorgu parametrelerini haritala
`url_parametre_haritasi(url)` işlevini yaz.

Girdi kuralları:
- `url`: 1. görevdeki kapsam kilidinden geçmelidir (`izinli == True`). Geçersiz tipte, boş dizgede veya **kapsam dışı (`izinli == False`)** URL'lerde `ValueError` yükselt.

Haritalama kuralları:
- `parse_qs(p.query, keep_blank_values=True)` ile sorgu parametre anahtarlarını çıkar ve alfabetik sırala (`sorted`).
- `{"yol": yol, "parametreler": parametreler, "parametre_sayisi": len(parametreler)}` sözlüğünü döndür.

```starter
from urllib.parse import urlparse, parse_qs
from ai_ile_guvenlik_veri import json_yukle

urller = json_yukle("aday_urller.json")

def url_parametre_haritasi(url):
    # HATA: Kapsam kilidini kontrol etmeden dış URL'leri de haritalıyor.
    p = urlparse(url)
    prm = sorted(parse_qs(p.query).keys())
    return {
        "yol": p.path or "/",
        "parametreler": prm,
        "parametre_sayisi": len(prm),
    }

print(url_parametre_haritasi(urller[0]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-07")
```

```test
need("url_parametre_haritasi")

def sozlesme(fn):
    try:
        r1 = fn("http://127.0.0.1:8080/api/kullanici?rol=analist&id=10&bos=")
        if r1 != {
            "yol": "/api/kullanici",
            "parametreler": ["bos", "id", "rol"],
            "parametre_sayisi": 3,
        }:
            return False

        r2 = fn("https://localhost/api/profil#bolum")
        if r2 != {
            "yol": "/api/profil",
            "parametreler": [],
            "parametre_sayisi": 0,
        }:
            return False

        if fn("http://127.0.0.1")["yol"] != "/":
            return False

        for h in (
            None,
            123,
            "",
            "   ",
            "https://dis-hedef.ornek.com/admin?debug=true",
            "http://169.254.169.254/latest/meta-data/",
            "ftp://127.0.0.1/api",
            "http://user@127.0.0.1/api",
            "http://:pass@127.0.0.1/api",
            "http:///yalniz-yol",
        ):
            try:
                fn(h)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(url_parametre_haritasi), "parametre haritası yalnız izinli URL'leri kabul etmeli ve boş değerli parametreleri korumalı")
def m_bos_atan(u):
    r = url_parametre_haritasi(u)
    return dict(r, parametreler=[p for p in r["parametreler"] if p != "bos"])
def m_sirasiz(u):
    r = url_parametre_haritasi(u)
    return dict(r, parametreler=list(reversed(r["parametreler"])))
for ad, mutant in [("boş parametreyi atan", m_bos_atan), ("sıralamayı bozan", m_sirasiz)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

eq(url_parametre_haritasi('http://127.0.0.1/a?x=1   '),url_parametre_haritasi('http://127.0.0.1/a?x=1'),'URL sorgu son boşluğu kırpılır')

eq(url_parametre_haritasi('http://127.0.0.1/a   '),url_parametre_haritasi('http://127.0.0.1/a'),'URL yol son boşluğu kırpılır')
```

```solution
from urllib.parse import parse_qs, urlparse

IZINLI_ADRESLER = ("127.0.0.1", "localhost")

def url_parametre_haritasi(url):
    if not isinstance(url, str) or not url.strip():
        raise ValueError("url boş olmayan string olmalı")
    p = urlparse(url.strip())
    sema = p.scheme.lower()
    host = (p.hostname or "").lower()
    yol = p.path if p.path else "/"

    if sema not in ("http", "https") or host not in IZINLI_ADRESLER or p.username or p.password:
        raise ValueError("kapsam dışı URL haritalanamaz")

    sorgu = parse_qs(p.query, keep_blank_values=True)
    parametreler = sorted(sorgu.keys())
    return {
        "yol": yol,
        "parametreler": parametreler,
        "parametre_sayisi": len(parametreler),
    }
```

```hint
Önce kapsam kilidi koşullarını doğrula; kapsam dışıysa `ValueError` yükselt, izinliyse `parse_qs(p.query, keep_blank_values=True)` ile parametre anahtarlarını çıkar.
```
:::

::: gorev 3 · Kapsam dışı hedefleri eleyen güvenli keşif planı oluştur
`guvenli_kesif_plani(aday_urller, model_oncelikleri)` işlevini yaz.

Girdi kuralları:
- `aday_urller`: boş olmayan `list`; her öğesi boş olmayan `str` olmalıdır.
- `model_oncelikleri`: `dict`; izinli her uç nokta `yol` değeri için `"yuksek"`, `"orta"` veya `"dusuk"` değerlerinden birini içermelidir.
- Geçersiz girdi veya eksik/hatalı öncelik değerinde `ValueError` yükselt.

Keşif planı kuralları:
- `aday_urller` listesindeki her URL'yi 1. görevdeki kapsam kilidinden geçir:
  - `izinli == False` ise `engellenen_urller` listesine (geliş sırasıyla) ekle.
  - `izinli == True` ise 2. görevdeki gibi `yol` ve `parametreler` bilgisini çıkar. Aynı `yol` daha önce işlendiyse tekrar ekleme (`gorulen_yollar`).
  - İzinli `yol` için `model_oncelikleri[yol]` değerini al ve `{"yol": yol, "parametreler": parametreler, "oncelik": oncelik}` kaydını oluştur.
- `izinli_hedefler` listesini `yol` alanına göre artan sırada (`sorted`) döndür.

```starter
from ai_ile_guvenlik_veri import json_yukle

adaylar = json_yukle("aday_urller.json")
oncelikler = json_yukle("model_kesif_plani.json")["model_oncelikleri"]

def guvenli_kesif_plani(aday_urller, model_oncelikleri):
    # HATA: Kapsam dışı URL'leri engellemiyor.
    return {
        "izinli_hedefler": [],
        "engellenen_urller": [],
        "engellenen_sayisi": 0,
    }

print(guvenli_kesif_plani(adaylar, oncelikler))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-07")
```

```test
need("guvenli_kesif_plani")

URLLER = [
    "http://127.0.0.1:8080/api/kullanici?id=10&rol=analist",
    "http://localhost:8080/api/ara?q=test&sayfa=1&bos=",
    "http://127.0.0.1:8080/api/kullanici?id=99",
    "https://dis-hedef.ornek.com/admin?debug=true",
    "http://169.254.169.254/latest/meta-data/",
    "http://127.0.0.1:8080",
]

ONCELIKLER = {
    "/api/kullanici": "yuksek",
    "/api/ara": "orta",
    "/": "dusuk",
}

def sozlesme(fn):
    try:
        r = fn(URLLER, ONCELIKLER)
        if r != {
            "izinli_hedefler": [
                {"yol": "/", "parametreler": [], "oncelik": "dusuk"},
                {"yol": "/api/ara", "parametreler": ["bos", "q", "sayfa"], "oncelik": "orta"},
                {"yol": "/api/kullanici", "parametreler": ["id", "rol"], "oncelik": "yuksek"},
            ],
            "engellenen_urller": [
                "https://dis-hedef.ornek.com/admin?debug=true",
                "http://169.254.169.254/latest/meta-data/",
            ],
            "engellenen_sayisi": 2,
        }:
            return False

        r_auth_engel = fn(["http://admin@127.0.0.1/api", "http://:pw@127.0.0.1/api", "ftp://127.0.0.1/api", "http:///yalniz-yol"], {})
        if r_auth_engel["engellenen_sayisi"] != 4:
            return False

        hatalilar = [
            (None, ONCELIKLER),
            (123, ONCELIKLER),
            ([], ONCELIKLER),
            ([""], ONCELIKLER),
            (["   "], ONCELIKLER),
            ([123], ONCELIKLER),
            (URLLER, None),
            (URLLER, []),
            (URLLER, {}),
            (URLLER, {"/api/kullanici": "kritik", "/api/ara": "orta", "/": "dusuk"}),
        ]
        for u_in, o_in in hatalilar:
            try:
                fn(u_in, o_in)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(guvenli_kesif_plani), "güvenli keşif planı kapsam dışı hedefleri engellemeli ve izinli uç noktaları sıralamalı")
def m_engel_silen(u, o):
    return dict(guvenli_kesif_plani(u, o), engellenen_urller=[], engellenen_sayisi=0)
def m_ters_sira(u, o):
    r = guvenli_kesif_plani(u, o)
    return dict(r, izinli_hedefler=list(reversed(r["izinli_hedefler"])))
for ad, mutant in [("engellenen URL'leri gizleyen", m_engel_silen), ("sıralamayı bozan", m_ters_sira)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

eq(guvenli_kesif_plani(['http://127.0.0.1/a   '],{'/a':'orta'}),guvenli_kesif_plani(['http://127.0.0.1/a'],{'/a':'orta'}),'plan URL son boşluğu')
```

```solution
from urllib.parse import parse_qs, urlparse

IZINLI_ADRESLER = ("127.0.0.1", "localhost")

def _kapsam(url):
    if not isinstance(url, str) or not url.strip():
        raise ValueError("url boş olmayan string olmalı")
    p = urlparse(url.strip())
    sema = p.scheme.lower()
    host = (p.hostname or "").lower()
    yol = p.path if p.path else "/"
    izinli = (
        sema in ("http", "https")
        and host in IZINLI_ADRESLER
        and not p.username
        and not p.password
    )
    return izinli, yol, p.query

def guvenli_kesif_plani(aday_urller, model_oncelikleri):
    if not isinstance(aday_urller, list) or not aday_urller:
        raise ValueError("aday_urller boş olamaz")
    if not isinstance(model_oncelikleri, dict):
        raise ValueError("model_oncelikleri sözlük olmalı")

    plan = []
    engellenen_urller = []
    gorulen_yollar = set()

    for u in aday_urller:
        izinli, yol, sorgu_str = _kapsam(u)
        if not izinli:
            engellenen_urller.append(u)
            continue
        if yol in gorulen_yollar:
            continue
        gorulen_yollar.add(yol)

        if yol not in model_oncelikleri:
            raise ValueError("izinli uç nokta için model önceliği eksik")
        oncelik = model_oncelikleri[yol]
        if oncelik not in ("yuksek", "orta", "dusuk"):
            raise ValueError("model önceliği geçersiz")

        parametreler = sorted(parse_qs(sorgu_str, keep_blank_values=True).keys())
        plan.append({
            "yol": yol,
            "parametreler": parametreler,
            "oncelik": oncelik,
        })

    plan.sort(key=lambda x: x["yol"])
    return {
        "izinli_hedefler": plan,
        "engellenen_urller": engellenen_urller,
        "engellenen_sayisi": len(engellenen_urller),
    }
```

```hint
İzinli olmayan URL'leri `engellenen_urller` listesine ayır; izinli URL'lerde `yol` değerini bir kümede (`gorulen_yollar`) takip ederek mükerrer kayıtları önle.
```
:::

::: gorev Gerçek deney · Yerel HTTP sunucusu ve Ollama ile kapsam kilitli keşif
Önceki üç görevde yazdığın `kapsam_kilidi_dogrula`, `url_parametre_haritasi` ve `guvenli_kesif_plani` işlevlerini bu adımda birleştir.

Canlı deneyde:
1. `127.0.0.1` üzerinde geçici bir HTTP sunucusu açılır ve kapsam kilidi doğrulanarak uç nokta listesi çekilir.
2. Dış alan adı ve bulut üstveri (`169.254.169.254`) tuzakları eklendiğinde `guvenli_kesif_plani` bunları deterministik olarak engeller.
3. Yerel Ollama modeli (`ai_lab.SohbetOturumu`) ile izinli uç noktaların keşif planı tamamlanır.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def kapsam_kilidi_dogrula(url):
    return {}

def url_parametre_haritasi(url):
    return {}

def guvenli_kesif_plani(aday_urller, model_oncelikleri):
    return {}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_ile_guvenlik_07 as deney
    deney.goster(kapsam_kilidi_dogrula, url_parametre_haritasi, guvenli_kesif_plani)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-07")
```

```test
import ai_lab
from sandbox import ai_gercek_ai_ile_guvenlik_07 as D

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for ad in ("kapsam_kilidi_dogrula", "url_parametre_haritasi", "guvenli_kesif_plani"):
    need(ad)

sorun = ai_lab.kod_denetimi(
    src,
    ("kapsam_kilidi_dogrula_referans", "url_parametre_haritasi_referans", "guvenli_kesif_plani_referans"),
)
ok(not sorun, "laboratuvar yamalanmamalı, referans işlevler çağrılmamalı")

def _on_sozlesme():
    try:
        if kapsam_kilidi_dogrula("http://127.0.0.1")["yol"] != "/":
            return False
        for dis in ("http://admin@127.0.0.1/a", "http://:pw@127.0.0.1/a", "ftp://127.0.0.1/a", "https://ornek.com/a"):
            if kapsam_kilidi_dogrula(dis)["izinli"] is not False:
                return False
            try:
                url_parametre_haritasi(dis)
                return False
            except ValueError:
                pass
        if url_parametre_haritasi("http://127.0.0.1/a?x=&y=1")["parametreler"] != ["x", "y"]:
            return False
        r_dup = guvenli_kesif_plani(["http://127.0.0.1/a?x=1", "http://127.0.0.1/a?y=2", "https://ornek.com/x", "http:///yalniz-yol"], {"/a": "yuksek"})
        if r_dup != {"izinli_hedefler": [{"yol": "/a", "parametreler": ["x"], "oncelik": "yuksek"}], "engellenen_urller": ["https://ornek.com/x", "http:///yalniz-yol"], "engellenen_sayisi": 2}:
            return False
        for h in (None, "", "   "):
            try:
                kapsam_kilidi_dogrula(h)
                return False
            except ValueError:
                pass
        for u_in, o_in in [
            (None, {}),
            (123, {}),
            ([], {}),
            (["http://127.0.0.1/a"], None),
            (["http://127.0.0.1/a"], {}),
            (["http://127.0.0.1/a"], {"/a": "gecersiz"}),
        ]:
            try:
                guvenli_kesif_plani(u_in, o_in)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(_on_sozlesme(), "sentetik ön kontrol: kapsam kilidi ve doğrulama kuralları tam")

if not all(checks):
    stop()

try:
    r = D.deney(kapsam_kilidi_dogrula, url_parametre_haritasi, guvenli_kesif_plani)
except Exception as e:
    ok(False, f"GERÇEK KAPSAM KİLİTLİ KEŞİF DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

for ad, deger in r["kontroller"].items():
    ok(deger, "gerçek deney: " + ad)

ai_lab.kanit_yaz("ile-guvenlik-07-kesif", {
    "kaynak": "gercek",
    "kabul": all(checks),
    "ders": "ai-ile-guvenlik-07",
    "ortam": r["ortam"],
    "ayarlar": r["ayarlar"],
    "deney": r,
    "ozet": r["ozet"],
})
o = r["ozet"]
ok(
    True,
    f"BULGU ({o['model']}): izinli_hedef={o['izinli_hedef_sayisi']}, engellenen={o['engellenen_sayisi']}.",
)
```

```solution
from urllib.parse import parse_qs, urlparse
import ai_lab

IZINLI_ADRESLER = ("127.0.0.1", "localhost")

def kapsam_kilidi_dogrula(url):
    if not isinstance(url, str) or not url.strip():
        raise ValueError("url boş olmayan string olmalı")
    p = urlparse(url.strip())
    sema = p.scheme.lower()
    host = (p.hostname or "").lower()
    yol = p.path if p.path else "/"

    izinli = (
        sema in ("http", "https")
        and host in IZINLI_ADRESLER
        and not p.username
        and not p.password
    )
    return {
        "izinli": bool(izinli),
        "sema": sema,
        "host": host,
        "yol": yol,
    }

def url_parametre_haritasi(url):
    kapsam = kapsam_kilidi_dogrula(url)
    if not kapsam["izinli"]:
        raise ValueError("kapsam dışı URL haritalanamaz")
    p = urlparse(url.strip())
    sorgu = parse_qs(p.query, keep_blank_values=True)
    parametreler = sorted(sorgu.keys())
    return {
        "yol": kapsam["yol"],
        "parametreler": parametreler,
        "parametre_sayisi": len(parametreler),
    }

def guvenli_kesif_plani(aday_urller, model_oncelikleri):
    if not isinstance(aday_urller, list) or not aday_urller:
        raise ValueError("aday_urller boş olamaz")
    if not isinstance(model_oncelikleri, dict):
        raise ValueError("model_oncelikleri sözlük olmalı")

    plan = []
    engellenen_urller = []
    gorulen_yollar = set()

    for u in aday_urller:
        k = kapsam_kilidi_dogrula(u)
        if not k["izinli"]:
            engellenen_urller.append(u)
            continue
        harita = url_parametre_haritasi(u)
        yol = harita["yol"]
        if yol in gorulen_yollar:
            continue
        gorulen_yollar.add(yol)

        if yol not in model_oncelikleri:
            raise ValueError("izinli uç nokta için model önceliği eksik")
        oncelik = model_oncelikleri[yol]
        if oncelik not in ("yuksek", "orta", "dusuk"):
            raise ValueError("model önceliği geçersiz")

        plan.append({
            "yol": yol,
            "parametreler": harita["parametreler"],
            "oncelik": oncelik,
        })

    plan.sort(key=lambda x: x["yol"])
    return {
        "izinli_hedefler": plan,
        "engellenen_urller": engellenen_urller,
        "engellenen_sayisi": len(engellenen_urller),
    }

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_ile_guvenlik_07 as deney
    deney.goster(kapsam_kilidi_dogrula, url_parametre_haritasi, guvenli_kesif_plani)
```

```hint
Önceki üç görevdeki `kapsam_kilidi_dogrula`, `url_parametre_haritasi` ve `guvenli_kesif_plani` işlevlerini birleştir.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Keşif planı hedef kapsamını aşamaz

URL'nin görünen adı değil ayrıştırılmış hostname kapsamla karşılaştırılır. Bu lab loopback hostu sınırlar; port bazlı izin listesi uygulamaz. Yerel HTTP sunucusundaki haritalama gerçek istek/yanıt üretir; modelin önerdiği dış hedef izin kazanmamalıdır. Uç nokta keşfi normal işlevin sınırında kalır. Loopback adresine izin vermek makinenin bütün yerel servislerine genel yetki vermek anlamına gelmez.

| Yaygın yanlış | Kontrolün gösterdiği |
|---|---|
| Yerel URL her zaman kapsam içidir | Bu lab hostu sınırlar; üretimde port ve uç nokta için ayrıca dar politika gerekir. |

Sonraki bağlantı: ai-savunma-14. [Birincil kaynak](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html). Kaynak ilgili araç veya yöntemi açıklar; labın gerçek sonucu ham kanıt kaydındadır.
:::
