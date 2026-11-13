---
id: ai-ile-guvenlik-09
title: "Başsız Tarayıcı (Playwright) ile DOM Güvenlik Denetimi"
summary: Ağ erişimi kapatılmış başsız tarayıcı (Playwright Chromium) üzerinde DOM form hedeflerini, gizli girdi alanlarını ve javascript:/dış sızıntı bağlantılarını denetle.
timeout: 300
esleme: ai-saldiri-31, ai-savunma-17
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et
Tek sayfa uygulamalarında (`SPA`) veya karmaşık istemci arayüzlerinde ham HTML kaynağını yalnız metin olarak okumak, tarayıcının oluşturduğu gerçek DOM ağacındaki (`Document Object Model`) form hedeflerini (`action`), gizli girdi alanlarını (`input[type="hidden"]`) ve tehlikeli bağlantı şemalarını (`javascript:`, `data:`) gözden kaçırabilir (`ai-saldiri-31` dersindeki DOM katman farklarını hatırla). Güvenli bir DOM denetim aracı, sayfayı **ağ erişimi tamamen kapatılmış (`route.abort()`)** bir başsız tarayıcıda (`Playwright Chromium headless`) yükler ve DOM yüzeyini deterministik kurallarla denetler.

| Gerçek araç / model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| `html.parser.HTMLParser` ile DOM yüzeyi çıkarımını ve canlı `Playwright Chromium (headless)` üzerinde ağ yalıtımlı (`route.abort()`) DOM ağacını | İlk üç görevde `ornek_sayfa.html` ve `beklenen_dom_raporu.json` içindeki **sentetik** HTML verilerini; son görevde gerçek `Playwright Chromium` ile canlı DOM güvenlik denetimini | Yalnız statik DOM anlık görüntüsüne bakarak kullanıcı etkileşimi (tıklama/zamanlayıcı) sonrasında dinamik olarak eklenecek tüm betik davranışlarının tüketildiğini söyleyemez |

> [!GÜVENLİK]
> **Kapsam ve dürüstlük sınırı:** İlk üç görevdeki HTML dosyası **sentetik** eğitim verisidir. Canlı deneyde `Playwright Chromium` üzerinde `sayfa.route("**/*", lambda route: route.abort())` uygulanarak her türlü dış ağ isteği deterministik olarak engellenir.
:::

::: anlat DOM yüzeyi form, bağlantı ve gizli girdi envanterinden oluşur
Üç aşamalı DOM güvenlik denetimi şöyle çalışır:

1. **DOM Yüzeyi Çıkarma (`dom_yuzeyi_cikar`):** HTML içindeki `<form id="..." action="...">`, `<a id="..." href="...">` ve `<input type="hidden" name="...">` düğümleri ayrıştırılır.
2. **Bağlantı ve Form Güvenlik Denetimi (`baglanti_ve_form_denetle`):**
   - Bir formun `action` URL'si `http`/`https` şemasında değilse veya sunucu adı (`hostname`) `("127.0.0.1", "localhost")` dışında bir hedefse `dis_form_idleri` listesine eklenir (dış veri sızıntısı riski).
   - Bir bağlantının `href` şeması `javascript` veya `data` ise ya da `http`/`https` olup `("127.0.0.1", "localhost")` dışına çıkıyorsa `tehlikeli_baglanti_idleri` listesine eklenir.
3. **Birleşik DOM Güvenlik Raporu (`dom_guvenlik_raporu`):** Yüzey çıkarımı ve güvenlik denetimini birleştirerek `risk_var_mi` bayrağıyla birlikte doğrulanabilir bir rapor üretir.
:::

::: anlat Bulguyu sınırlı ve doğrulanabilir yaz: başsız tarayıcıda ağ yalıtımı şarttır
Güvenilmeyen bir HTML sayfasını gerçek bir tarayıcı motorunda (`Chromium`) açarken dış kaynakların (`<img src="https://...">`, `<script src="...">`) yüklenmesine izin vermek hem bilgi sızdırır hem de dış ağa istek üretir. Bu nedenle denetim sırasında tüm ağ rotaları `route.abort()` ile kapatılmalıdır.
:::

::: tahmin HTMLParser ile form action ve gizli input çıkarımını tahmin et
Aşağıdaki Python kodunun çıktısını tahmin et:

```python
from html.parser import HTMLParser

class MiniDOM(HTMLParser):
    def __init__(self):
        super().__init__()
        self.bulunan = []
    def handle_starttag(self, tag, attrs):
        oz = dict(attrs)
        if tag == "form":
            self.bulunan.append(("form", oz.get("id")))
        elif tag == "input" and oz.get("type") == "hidden":
            self.bulunan.append(("hidden", oz.get("name")))

p = MiniDOM()
p.feed('<form id="f1"><input type="text" name="u"><input type="hidden" name="token"></form>')
print(p.bulunan)
```

???

```cikti
[('form', 'f1'), ('hidden', 'token')]
```

`HTMLParser` başlangıç etiketlerini sırasıyla gezer; `<form id="f1">` düğümünü ve yalnızca `type="hidden"` olan `token` girdisini listeye ekler.
:::

::: gorev 1 · HTML metninden form, bağlantı ve gizli girdi yüzeyini çıkar
`dom_yuzeyi_cikar(html_metni)` işlevini yaz.

Girdi kuralları:
- `html_metni`: boş olmayan (`strip()` sonrası dolu) `str`. Boş metin veya `str` dışı tipte `ValueError` yükselt.

Çıkarma kuralları:
- `HTMLParser` kullanarak başlangıç etiketlerini (`handle_starttag`) tara:
  - `tag == "form"`: `id` ve `action` öznitelikleri (`strip()` sonrası) boş değilse `formlar` listesine `{"id": fid, "action": action}` ekle.
  - `tag == "a"`: `id` ve `href` öznitelikleri (`strip()` sonrası) boş değilse `baglantilar` listesine `{"id": aid, "href": href}` ekle.
  - `tag == "input"`: `type` özniteliği (`strip().lower()`) `"hidden"` ise ve `name` özniteliği (`strip()` sonrası) boş değilse `gizli_girdiler` kümesine ekle.
- `{"formlar": formlar, "baglantilar": baglantilar, "gizli_girdiler": sorted(set(gizli_girdiler))}` sözlüğünü döndür.

```starter
from html.parser import HTMLParser
from ai_ile_guvenlik_veri import metin_yukle

html = metin_yukle("ornek_sayfa.html")

def dom_yuzeyi_cikar(html_metni):
    # HATA: Etiketleri ayrıştırmadan boş yüzey döndürüyor.
    return {
        "formlar": [],
        "baglantilar": [],
        "gizli_girdiler": [],
    }

print(dom_yuzeyi_cikar(html))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-09")
```

```test
need("dom_yuzeyi_cikar")

ORNEK = (
    '<form id="f1" action="http://127.0.0.1/giris">'
    '<input type="hidden" name="csrf">'
    '<input type="text" name="kullanici">'
    '<input type="HIDDEN" name="oturum">'
    '<input type="hidden" name="csrf">'
    '</form>'
    '<form id="" action="http://127.0.0.1/bos"></form>'
    '<a id="a1" href="javascript:alert(1)">Tıkla</a>'
    '<a id="a2" href="">Boş</a>'
)

def sozlesme(fn):
    try:
        r = fn(ORNEK)
        if r != {
            "formlar": [{"id": "f1", "action": "http://127.0.0.1/giris"}],
            "baglantilar": [{"id": "a1", "href": "javascript:alert(1)"}],
            "gizli_girdiler": ["csrf", "oturum"],
        }:
            return False
        if fn('<div id="d1" type="hidden" name="n1"></div><form id="f_eksik"></form><a href="http://127.0.0.1/x">X</a><input name="n2"><input type="hidden">') != {"formlar": [], "baglantilar": [], "gizli_girdiler": []}:
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

ok(sozlesme(dom_yuzeyi_cikar), "DOM yüzeyi form, bağlantı ve gizli girdi alanlarını doğru çıkarmalı")
def m_formsiz(h):
    return dict(dom_yuzeyi_cikar(h), formlar=[])
def m_gizlisiz(h):
    return dict(dom_yuzeyi_cikar(h), gizli_girdiler=[])
for ad, mutant in [("formları silen", m_formsiz), ("gizli girdileri silen", m_gizlisiz)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

_normal='<form id="f" action="http://127.0.0.1/a"><input type="hidden" name="csrf"></form><a id="a" href="javascript:x">X</a>'
_bosluk='<form id=" f " action=" http://127.0.0.1/a "><input type=" HIDDEN " name=" csrf "></form><a id=" a " href=" javascript:x ">X</a>'
eq(dom_yuzeyi_cikar(_bosluk),dom_yuzeyi_cikar(_normal),'tüm DOM özniteliklerinde trim')
```

```solution
from html.parser import HTMLParser

class _DOMYuzeyAyristirici(HTMLParser):
    def __init__(self):
        super().__init__()
        self.formlar = []
        self.baglantilar = []
        self.gizli_girdiler = []

    def handle_starttag(self, tag, attrs):
        oz = dict(attrs)
        if tag == "form":
            fid = (oz.get("id") or "").strip()
            action = (oz.get("action") or "").strip()
            if fid and action:
                self.formlar.append({"id": fid, "action": action})
        elif tag == "a":
            aid = (oz.get("id") or "").strip()
            href = (oz.get("href") or "").strip()
            if aid and href:
                self.baglantilar.append({"id": aid, "href": href})
        elif tag == "input":
            tur = (oz.get("type") or "").strip().lower()
            ad = (oz.get("name") or "").strip()
            if tur == "hidden" and ad:
                self.gizli_girdiler.append(ad)

def dom_yuzeyi_cikar(html_metni):
    if not isinstance(html_metni, str) or not html_metni.strip():
        raise ValueError("html_metni boş olmayan string olmalı")
    p = _DOMYuzeyAyristirici()
    p.feed(html_metni)
    p.close()
    return {
        "formlar": p.formlar,
        "baglantilar": p.baglantilar,
        "gizli_girdiler": sorted(set(p.gizli_girdiler)),
    }
```

```hint
`HTMLParser` alt sınıfında `handle_starttag(self, tag, attrs)` metodunu tanımlayarak `form`, `a` ve `input` etiketlerinin özniteliklerini topla.
```
:::

::: gorev 2 · Çıkarılan DOM yüzeyindeki dış form hedeflerini ve tehlikeli bağlantıları denetle
`baglanti_ve_form_denetle(yuzey)` işlevini yaz.

Girdi kuralları:
- `yuzey`: tam olarak `{"formlar", "baglantilar", "gizli_girdiler"}` anahtarlarına sahip `dict`; üç değer de `list` olmalıdır.
- `formlar` içindeki her öğe `{"id", "action"}` anahtarlarına sahip, boş olmayan `str` değerler taşıyan `dict` olmalıdır.
- `baglantilar` içindeki her öğe `{"id", "href"}` anahtarlarına sahip, boş olmayan `str` değerler taşıyan `dict` olmalıdır.
- Geçersiz girdi veya şemada `ValueError` yükselt.

Denetim kuralları:
- İzinli yerel sunucu adları: `("127.0.0.1", "localhost")`.
- Her formun `action` URL'sini `urlparse` ile incele: `sema = u.scheme.lower()`, `host = (u.hostname or "").lower()`. Eğer `sema not in ("http", "https")` veya `host not in ("127.0.0.1", "localhost")` ise formun `id` değerini `dis_form_idleri` listesine ekle.
- Her bağlantının `href` değerini `urlparse` ile incele: eğer `sema in ("javascript", "data")` ise veya `(sema in ("http", "https") and host not in ("127.0.0.1", "localhost"))` ise bağlantının `id` değerini `tehlikeli_baglanti_idleri` listesine ekle.
- Tüm listeleri `sorted` olarak `{"dis_form_idleri": ..., "tehlikeli_baglanti_idleri": ..., "gizli_girdi_adlari": sorted(yuzey["gizli_girdiler"])}` biçiminde döndür.

```starter
def baglanti_ve_form_denetle(yuzey):
    # HATA: Dış formları ve javascript: bağlantılarını tespit etmiyor.
    return {
        "dis_form_idleri": [],
        "tehlikeli_baglanti_idleri": [],
        "gizli_girdi_adlari": [],
    }

print(baglanti_ve_form_denetle({"formlar": [], "baglantilar": [], "gizli_girdiler": ["token"]}))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-09")
```

```test
need("baglanti_ve_form_denetle")

YUZEY = {
    "formlar": [
        {"id": "f-ic", "action": "http://127.0.0.1:8080/giris"},
        {"id": "f-dis", "action": "https://sizinti.ornek.com/topla"},
        {"id": "f-js", "action": "javascript:void(0)"},
    ],
    "baglantilar": [
        {"id": "a-ic", "href": "http://localhost/yardim"},
        {"id": "a-js", "href": "javascript:alert(1)"},
        {"id": "a-data", "href": "data:text/html,<script>alert(1)</script>"},
        {"id": "a-dis", "href": "https://dis.ornek.com/p"},
    ],
    "gizli_girdiler": ["z_token", "a_token"],
}

def sozlesme(fn):
    try:
        r = fn(YUZEY)
        if r != {
            "dis_form_idleri": ["f-dis", "f-js"],
            "tehlikeli_baglanti_idleri": ["a-data", "a-dis", "a-js"],
            "gizli_girdi_adlari": ["a_token", "z_token"],
        }:
            return False
        if fn({"formlar": [{"id": "f-ftp", "action": "ftp://127.0.0.1/x"}], "baglantilar": [{"id": "a-jsh", "href": "javascript://127.0.0.1/x"}, {"id": "a-rel", "href": "/yerel"}], "gizli_girdiler": []}) != {
            "dis_form_idleri": ["f-ftp"],
            "tehlikeli_baglanti_idleri": ["a-jsh", "a-rel"],
            "gizli_girdi_adlari": [],
        }:
            return False

        hatalilar = [
            None,
            [],
            {},
            {"formlar": [], "baglantilar": []},
            {"formlar": "bozuk", "baglantilar": [], "gizli_girdiler": []},
            {"formlar": [], "baglantilar": "bozuk", "gizli_girdiler": []},
            {"formlar": [], "baglantilar": [], "gizli_girdiler": "bozuk"},
            {"formlar": [], "baglantilar": [], "gizli_girdiler": 123},
            {"formlar": ["bozuk"], "baglantilar": [], "gizli_girdiler": []},
            {"formlar": [], "baglantilar": ["bozuk"], "gizli_girdiler": []},
            {"formlar": [{}], "baglantilar": [], "gizli_girdiler": []},
            {"formlar": [{"id": "f1"}], "baglantilar": [], "gizli_girdiler": []},
            {"formlar": [{"id": "", "action": "http://127.0.0.1"}], "baglantilar": [], "gizli_girdiler": []},
            {"formlar": [{"id": "   ", "action": "http://127.0.0.1"}], "baglantilar": [], "gizli_girdiler": []},
            {"formlar": [{"id": "f1", "action": ""}], "baglantilar": [], "gizli_girdiler": []},
            {"formlar": [{"id": "f1", "action": "   "}], "baglantilar": [], "gizli_girdiler": []},
            {"formlar": [{"id": 123, "action": "http://127.0.0.1"}], "baglantilar": [], "gizli_girdiler": []},
            {"formlar": [{"id": "f1", "action": None}], "baglantilar": [], "gizli_girdiler": []},
            {"formlar": [], "baglantilar": [{}], "gizli_girdiler": []},
            {"formlar": [], "baglantilar": [{"id": "a1"}], "gizli_girdiler": []},
            {"formlar": [], "baglantilar": [{"id": "", "href": "http://127.0.0.1"}], "gizli_girdiler": []},
            {"formlar": [], "baglantilar": [{"id": "   ", "href": "http://127.0.0.1"}], "gizli_girdiler": []},
            {"formlar": [], "baglantilar": [{"id": "a1", "href": ""}], "gizli_girdiler": []},
            {"formlar": [], "baglantilar": [{"id": "a1", "href": "   "}], "gizli_girdiler": []},
            {"formlar": [], "baglantilar": [{"id": None, "href": "http://127.0.0.1"}], "gizli_girdiler": []},
            {"formlar": [], "baglantilar": [{"id": "a1", "href": 123}], "gizli_girdiler": []},
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

ok(sozlesme(baglanti_ve_form_denetle), "form ve bağlantı denetimi dış hedefleri ve tehlikeli şemaları doğru yakalamalı")
def m_form_atlayan(y):
    return dict(baglanti_ve_form_denetle(y), dis_form_idleri=[])
def m_bag_atlayan(y):
    return dict(baglanti_ve_form_denetle(y), tehlikeli_baglanti_idleri=[])
for ad, mutant in [("dış formları gizleyen", m_form_atlayan), ("tehlikeli bağlantıları gizleyen", m_bag_atlayan)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from urllib.parse import urlparse

IZINLI_ADRESLER = ("127.0.0.1", "localhost")

def baglanti_ve_form_denetle(yuzey):
    if not isinstance(yuzey, dict) or set(yuzey.keys()) != {"formlar", "baglantilar", "gizli_girdiler"}:
        raise ValueError("yuzey şeması geçersiz")
    if not all(isinstance(yuzey[k], list) for k in ("formlar", "baglantilar", "gizli_girdiler")):
        raise ValueError("yuzey alanları liste olmalı")

    dis_form_idleri = []
    tehlikeli_baglanti_idleri = []

    for f in yuzey["formlar"]:
        if not isinstance(f, dict) or set(f.keys()) != {"id", "action"}:
            raise ValueError("form kaydı geçersiz")
        fid = f["id"]
        action = f["action"]
        if not isinstance(fid, str) or not fid.strip() or not isinstance(action, str) or not action.strip():
            raise ValueError("form alanları boş olamaz")
        u = urlparse(action)
        sema = u.scheme.lower()
        host = (u.hostname or "").lower()
        if sema not in ("http", "https") or host not in IZINLI_ADRESLER:
            dis_form_idleri.append(fid)

    for b in yuzey["baglantilar"]:
        if not isinstance(b, dict) or set(b.keys()) != {"id", "href"}:
            raise ValueError("bağlantı kaydı geçersiz")
        bid = b["id"]
        href = b["href"]
        if not isinstance(bid, str) or not bid.strip() or not isinstance(href, str) or not href.strip():
            raise ValueError("bağlantı alanları boş olamaz")
        u = urlparse(href)
        sema = u.scheme.lower()
        host = (u.hostname or "").lower()
        if sema in ("javascript", "data") or host not in IZINLI_ADRESLER:
            tehlikeli_baglanti_idleri.append(bid)

    return {
        "dis_form_idleri": sorted(dis_form_idleri),
        "tehlikeli_baglanti_idleri": sorted(tehlikeli_baglanti_idleri),
        "gizli_girdi_adlari": sorted(yuzey["gizli_girdiler"]),
    }
```

```hint
`urlparse` ile `scheme.lower()` ve `(hostname or "").lower()` değerlerini kontrol ederek yerel olmayan form hedeflerini ve `javascript:`/`data:`/dış bağlantıları ayır.
```
:::

::: gorev 3 · HTML sayfasından birleşik DOM güvenlik raporu üret
`dom_guvenlik_raporu(html_metni)` işlevini yaz.

Girdi kuralları:
- `html_metni`: 1. görevdeki kurallarla aynıdır.

Raporlama kuralları:
1. 1. görevdeki kurallarla DOM yüzeyini çıkar.
2. 2. görevdeki kurallarla form ve bağlantı denetimini çalıştır.
3. `risk_var_mi = bool(dis_form_idleri or tehlikeli_baglanti_idleri)` olarak hesapla.
4. `{"form_sayisi": len(yuzey["formlar"]), "dis_form_idleri": ..., "tehlikeli_baglanti_idleri": ..., "gizli_girdi_adlari": ..., "risk_var_mi": ...}` sözlüğünü döndür.

```starter
from ai_ile_guvenlik_veri import metin_yukle

html = metin_yukle("ornek_sayfa.html")

def dom_guvenlik_raporu(html_metni):
    # HATA: Gerçek analiz yapmadan risksiz rapor döndürüyor.
    return {
        "form_sayisi": 0,
        "dis_form_idleri": [],
        "tehlikeli_baglanti_idleri": [],
        "gizli_girdi_adlari": [],
        "risk_var_mi": False,
    }

print(dom_guvenlik_raporu(html))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-09")
```

```test
need("dom_guvenlik_raporu")

HTML_RISKLI = (
    '<form id="f1" action="http://127.0.0.1/ok"><input type="hidden" name="t1"></form>'
    '<form id="f2" action="https://dis.ornek.com/al"></form>'
    '<a id="a1" href="javascript:alert(1)">X</a>'
)

HTML_TEMIZ = (
    '<form id="f1" action="http://127.0.0.1/ok"><input type="hidden" name="t1"></form>'
    '<a id="a1" href="http://localhost/yardim">Y</a>'
)

def sozlesme(fn):
    try:
        if fn(HTML_RISKLI) != {
            "form_sayisi": 2,
            "dis_form_idleri": ["f2"],
            "tehlikeli_baglanti_idleri": ["a1"],
            "gizli_girdi_adlari": ["t1"],
            "risk_var_mi": True,
        }:
            return False

        if fn(HTML_TEMIZ) != {
            "form_sayisi": 1,
            "dis_form_idleri": [],
            "tehlikeli_baglanti_idleri": [],
            "gizli_girdi_adlari": ["t1"],
            "risk_var_mi": False,
        }:
            return False

        if fn('<a id="a2" href="https://dis.ornek.com/x">D</a>')["risk_var_mi"] is not True:
            return False
        if fn('<form id="fftp" action="ftp://127.0.0.1/x"></form><form id="fbos" action="http:///yalniz"></form>') != {"form_sayisi": 2, "dis_form_idleri": ["fbos", "fftp"], "tehlikeli_baglanti_idleri": [], "gizli_girdi_adlari": [], "risk_var_mi": True}:
            return False
        if fn('<a id="ajsh" href="javascript://127.0.0.1/x">J</a><a id="arel" href="/yerel">R</a>')["tehlikeli_baglanti_idleri"] != ["ajsh", "arel"]:
            return False
        if fn('<div id="d1" type="hidden" name="n1"></div><form id="fe"></form><a href="javascript:alert(1)">B</a><a id="abos">B</a><input name="n2"><input type="hidden">') != {"form_sayisi": 0, "dis_form_idleri": [], "tehlikeli_baglanti_idleri": [], "gizli_girdi_adlari": [], "risk_var_mi": False}:
            return False

        r_eksik = fn(
            '<form id="" action="http://127.0.0.1/a"></form>'
            '<form id="f1" action=""></form>'
            '<a id="" href="http://127.0.0.1/b">B</a>'
            '<a id="a1" href="">B</a>'
            '<input type="hidden" name="">'
            '<input type="text" name="acik">'
        )
        if r_eksik != {
            "form_sayisi": 0,
            "dis_form_idleri": [],
            "tehlikeli_baglanti_idleri": [],
            "gizli_girdi_adlari": [],
            "risk_var_mi": False,
        }:
            return False

        for h in (None, 123, "", "   "):
            try:
                fn(h)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(dom_guvenlik_raporu), "birleşik DOM güvenlik raporu risk durumunu ve envanteri doğru hesaplamalı")
def m_risk_gizleyen(h):
    return dict(dom_guvenlik_raporu(h), risk_var_mi=False)
def m_form_sifir(h):
    return dict(dom_guvenlik_raporu(h), form_sayisi=0)
for ad, mutant in [("riski gizleyen", m_risk_gizleyen), ("form sayısını sıfırlayan", m_form_sifir)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

_normal='<form id="f" action="http://127.0.0.1/a"><input type="hidden" name="csrf"></form><a id="a" href="javascript:x">X</a>'
_bosluk='<form id=" f " action=" http://127.0.0.1/a "><input type=" HIDDEN " name=" csrf "></form><a id=" a " href=" javascript:x ">X</a>'
eq(dom_guvenlik_raporu(_bosluk),dom_guvenlik_raporu(_normal),'rapor DOM özniteliklerinde trim')

eq(dom_guvenlik_raporu('<form id=" f " action="http://evil.test"></form>'),dom_guvenlik_raporu('<form id="f" action="http://evil.test"></form>'),'riskli form kimliği trim')
eq(dom_guvenlik_raporu('<form id="f" action="http://localhost "></form>'),dom_guvenlik_raporu('<form id="f" action="http://localhost"></form>'),'form action host son boşluğu')
eq(dom_guvenlik_raporu('<a id="x" href="   ">X</a>'),dom_guvenlik_raporu('<a id="x" href="">X</a>'),'yalnız boşluk href yok sayılır')
```

```solution
from html.parser import HTMLParser
from urllib.parse import urlparse

IZINLI_ADRESLER = ("127.0.0.1", "localhost")

class _DOMYuzeyAyristirici(HTMLParser):
    def __init__(self):
        super().__init__()
        self.formlar = []
        self.baglantilar = []
        self.gizli_girdiler = []

    def handle_starttag(self, tag, attrs):
        oz = dict(attrs)
        if tag == "form":
            fid = (oz.get("id") or "").strip()
            action = (oz.get("action") or "").strip()
            if fid and action:
                self.formlar.append({"id": fid, "action": action})
        elif tag == "a":
            aid = (oz.get("id") or "").strip()
            href = (oz.get("href") or "").strip()
            if aid and href:
                self.baglantilar.append({"id": aid, "href": href})
        elif tag == "input":
            tur = (oz.get("type") or "").strip().lower()
            ad = (oz.get("name") or "").strip()
            if tur == "hidden" and ad:
                self.gizli_girdiler.append(ad)

def dom_guvenlik_raporu(html_metni):
    if not isinstance(html_metni, str) or not html_metni.strip():
        raise ValueError("html_metni boş olmayan string olmalı")
    p = _DOMYuzeyAyristirici()
    p.feed(html_metni)
    p.close()

    dis_form_idleri = []
    tehlikeli_baglanti_idleri = []

    for f in p.formlar:
        u = urlparse(f["action"])
        if u.scheme.lower() not in ("http", "https") or (u.hostname or "").lower() not in IZINLI_ADRESLER:
            dis_form_idleri.append(f["id"])

    for b in p.baglantilar:
        u = urlparse(b["href"])
        sema = u.scheme.lower()
        host = (u.hostname or "").lower()
        if sema in ("javascript", "data") or host not in IZINLI_ADRESLER:
            tehlikeli_baglanti_idleri.append(b["id"])

    dis_form_idleri.sort()
    tehlikeli_baglanti_idleri.sort()
    return {
        "form_sayisi": len(p.formlar),
        "dis_form_idleri": dis_form_idleri,
        "tehlikeli_baglanti_idleri": tehlikeli_baglanti_idleri,
        "gizli_girdi_adlari": sorted(set(p.gizli_girdiler)),
        "risk_var_mi": bool(dis_form_idleri or tehlikeli_baglanti_idleri),
    }
```

```hint
Önceki iki görevdeki ayrıştırma ve denetim mantığını birleştirerek `bool(dis_form_idleri or tehlikeli_baglanti_idleri)` ile `risk_var_mi` değerini üret.
```
:::

::: gorev Gerçek deney · Playwright başsız Chromium üzerinde ağ yalıtımlı DOM güvenlik denetimi
Önceki üç görevde yazdığın `dom_yuzeyi_cikar`, `baglanti_ve_form_denetle` ve `dom_guvenlik_raporu` işlevlerini bu adımda birleştir.

Canlı deneyde:
1. `Playwright Chromium (headless=True)` başlatılır ve `route.abort()` ile dış ağ erişimi kapatılır.
2. Sayfa gerçek tarayıcı DOM ağacına yüklenir (`set_content`) ve oluşan DOM metni çekilir.
3. Yazdığın işlevlerle dış sızıntı formu (`sizinti-formu`), `javascript:` tuzağı (`js-tuzak`) ve gizli oturum girdisi (`oturum_anahtari`) tespit edilir.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 300
```

```starter
import ai_lab

def dom_yuzeyi_cikar(html_metni):
    return {}

def baglanti_ve_form_denetle(yuzey):
    return {}

def dom_guvenlik_raporu(html_metni):
    return {}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_ile_guvenlik_09 as deney
    deney.goster(dom_yuzeyi_cikar, baglanti_ve_form_denetle, dom_guvenlik_raporu)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-09")
```

```test
import ai_lab
from sandbox import ai_gercek_ai_ile_guvenlik_09 as D

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for ad in ("dom_yuzeyi_cikar", "baglanti_ve_form_denetle", "dom_guvenlik_raporu"):
    need(ad)

sorun = ai_lab.kod_denetimi(
    src,
    ("dom_yuzeyi_cikar_referans", "baglanti_ve_form_denetle_referans", "dom_guvenlik_raporu_referans"),
)
ok(not sorun, "laboratuvar yamalanmamalı, referans işlevler çağrılmamalı")

def _on_sozlesme():
    try:
        if dom_yuzeyi_cikar('<div id="d1" type="hidden" name="n1"></div><form id="fe"></form><a href="javascript:alert(1)">X</a><a id="abos">X</a><input name="n2"><input type="hidden">') != {"formlar": [], "baglantilar": [], "gizli_girdiler": []}:
            return False
        if dom_yuzeyi_cikar('<form id="f1" action="http://127.0.0.1/ok"><input type="HIDDEN" name="csrf"><input type="text" name="u"></form><a id="a1" href="http://localhost/y">Y</a>') != {
            "formlar": [{"id": "f1", "action": "http://127.0.0.1/ok"}],
            "baglantilar": [{"id": "a1", "href": "http://localhost/y"}],
            "gizli_girdiler": ["csrf"],
        }:
            return False
        if dom_guvenlik_raporu('<form id="f1" action="http://127.0.0.1/ok"><input type="hidden" name="t1"></form><a id="a1" href="http://localhost/y">Y</a>') != {
            "form_sayisi": 1, "dis_form_idleri": [], "tehlikeli_baglanti_idleri": [], "gizli_girdi_adlari": ["t1"], "risk_var_mi": False
        }:
            return False
        if dom_guvenlik_raporu('<a id="a1" href="https://dis.ornek.com/x">X</a>')["risk_var_mi"] is not True:
            return False
        if dom_guvenlik_raporu('<form id="f1" action="ftp://127.0.0.1/x"></form><form id="f2" action="https://dis.ornek.com/x"></form><form id="f3" action="http:///yalniz"></form>') != {"form_sayisi": 3, "dis_form_idleri": ["f1", "f2", "f3"], "tehlikeli_baglanti_idleri": [], "gizli_girdi_adlari": [], "risk_var_mi": True}:
            return False
        if dom_guvenlik_raporu('<a id="ajsh" href="javascript://127.0.0.1/x">J</a><a id="arel" href="/yerel">R</a>')["tehlikeli_baglanti_idleri"] != ["ajsh", "arel"]:
            return False
        if dom_guvenlik_raporu('<form id="" action="http://127.0.0.1/a"></form><a id="" href="http://127.0.0.1/b">B</a><input type="hidden" name="">') != {
            "form_sayisi": 0,
            "dis_form_idleri": [],
            "tehlikeli_baglanti_idleri": [],
            "gizli_girdi_adlari": [],
            "risk_var_mi": False,
        }:
            return False
        for h in (None, "", "   "):
            try:
                dom_yuzeyi_cikar(h)
                return False
            except ValueError:
                pass
        for y_in in (
            None,
            {},
            {"formlar": "x", "baglantilar": [], "gizli_girdiler": []},
            {"formlar": [], "baglantilar": "x", "gizli_girdiler": []},
            {"formlar": [], "baglantilar": [], "gizli_girdiler": "x"},
            {"formlar": [], "baglantilar": [], "gizli_girdiler": 123},
            {"formlar": ["x"], "baglantilar": [], "gizli_girdiler": []},
            {"formlar": [], "baglantilar": ["x"], "gizli_girdiler": []},
            {"formlar": [{}], "baglantilar": [], "gizli_girdiler": []},
            {"formlar": [{"id": "", "action": "http://127.0.0.1"}], "baglantilar": [], "gizli_girdiler": []},
            {"formlar": [{"id": 1, "action": "http://127.0.0.1"}], "baglantilar": [], "gizli_girdiler": []},
            {"formlar": [{"id": "f", "action": ""}], "baglantilar": [], "gizli_girdiler": []},
            {"formlar": [{"id": "f", "action": 1}], "baglantilar": [], "gizli_girdiler": []},
            {"formlar": [], "baglantilar": [{}], "gizli_girdiler": []},
            {"formlar": [], "baglantilar": [{"id": "", "href": "http://127.0.0.1"}], "gizli_girdiler": []},
            {"formlar": [], "baglantilar": [{"id": 1, "href": "http://127.0.0.1"}], "gizli_girdiler": []},
            {"formlar": [], "baglantilar": [{"id": "a", "href": ""}], "gizli_girdiler": []},
            {"formlar": [], "baglantilar": [{"id": "a", "href": 1}], "gizli_girdiler": []},
        ):
            try:
                baglanti_ve_form_denetle(y_in)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(_on_sozlesme(), "sentetik ön kontrol: DOM yüzeyi ve denetim kuralları tam")

if not all(checks):
    stop()

try:
    r = D.deney(dom_yuzeyi_cikar, baglanti_ve_form_denetle, dom_guvenlik_raporu)
except Exception as e:
    ok(False, f"GERÇEK PLAYWRIGHT DOM DENETİMİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

for ad, deger in r["kontroller"].items():
    ok(deger, "gerçek deney: " + ad)

ai_lab.kanit_yaz("ile-guvenlik-09-dom", {
    "kaynak": "gercek",
    "kabul": all(checks),
    "ders": "ai-ile-guvenlik-09",
    "ortam": r["ortam"],
    "ayarlar": r["ayarlar"],
    "deney": r,
    "ozet": r["ozet"],
})
o = r["ozet"]
ok(
    True,
    f"BULGU (Chromium {o['chromium_surumu']}): dis_formlar={o['dis_formlar']}, tehlikeli_baglantilar={o['tehlikeli_baglantilar']}, gizli_girdiler={o['gizli_girdiler']}.",
)
```

```solution
from html.parser import HTMLParser
from urllib.parse import urlparse
import ai_lab

IZINLI_ADRESLER = ("127.0.0.1", "localhost")

class _DOMYuzeyAyristirici(HTMLParser):
    def __init__(self):
        super().__init__()
        self.formlar = []
        self.baglantilar = []
        self.gizli_girdiler = []

    def handle_starttag(self, tag, attrs):
        oz = dict(attrs)
        if tag == "form":
            fid = (oz.get("id") or "").strip()
            action = (oz.get("action") or "").strip()
            if fid and action:
                self.formlar.append({"id": fid, "action": action})
        elif tag == "a":
            aid = (oz.get("id") or "").strip()
            href = (oz.get("href") or "").strip()
            if aid and href:
                self.baglantilar.append({"id": aid, "href": href})
        elif tag == "input":
            tur = (oz.get("type") or "").strip().lower()
            ad = (oz.get("name") or "").strip()
            if tur == "hidden" and ad:
                self.gizli_girdiler.append(ad)

def dom_yuzeyi_cikar(html_metni):
    if not isinstance(html_metni, str) or not html_metni.strip():
        raise ValueError("html_metni boş olmayan string olmalı")
    p = _DOMYuzeyAyristirici()
    p.feed(html_metni)
    p.close()
    return {
        "formlar": p.formlar,
        "baglantilar": p.baglantilar,
        "gizli_girdiler": sorted(set(p.gizli_girdiler)),
    }

def baglanti_ve_form_denetle(yuzey):
    if not isinstance(yuzey, dict) or set(yuzey.keys()) != {"formlar", "baglantilar", "gizli_girdiler"}:
        raise ValueError("yuzey şeması geçersiz")
    if not all(isinstance(yuzey[k], list) for k in ("formlar", "baglantilar", "gizli_girdiler")):
        raise ValueError("yuzey alanları liste olmalı")

    dis_form_idleri = []
    tehlikeli_baglanti_idleri = []

    for f in yuzey["formlar"]:
        if not isinstance(f, dict) or set(f.keys()) != {"id", "action"}:
            raise ValueError("form kaydı geçersiz")
        fid = f["id"]
        action = f["action"]
        if not isinstance(fid, str) or not fid.strip() or not isinstance(action, str) or not action.strip():
            raise ValueError("form alanları boş olamaz")
        u = urlparse(action)
        sema = u.scheme.lower()
        host = (u.hostname or "").lower()
        if sema not in ("http", "https") or host not in IZINLI_ADRESLER:
            dis_form_idleri.append(fid)

    for b in yuzey["baglantilar"]:
        if not isinstance(b, dict) or set(b.keys()) != {"id", "href"}:
            raise ValueError("bağlantı kaydı geçersiz")
        bid = b["id"]
        href = b["href"]
        if not isinstance(bid, str) or not bid.strip() or not isinstance(href, str) or not href.strip():
            raise ValueError("bağlantı alanları boş olamaz")
        u = urlparse(href)
        sema = u.scheme.lower()
        host = (u.hostname or "").lower()
        if sema in ("javascript", "data") or host not in IZINLI_ADRESLER:
            tehlikeli_baglanti_idleri.append(bid)

    return {
        "dis_form_idleri": sorted(dis_form_idleri),
        "tehlikeli_baglanti_idleri": sorted(tehlikeli_baglanti_idleri),
        "gizli_girdi_adlari": sorted(yuzey["gizli_girdiler"]),
    }

def dom_guvenlik_raporu(html_metni):
    yuzey = dom_yuzeyi_cikar(html_metni)
    denetim = baglanti_ve_form_denetle(yuzey)
    risk_var = bool(denetim["dis_form_idleri"] or denetim["tehlikeli_baglanti_idleri"])
    return {
        "form_sayisi": len(yuzey["formlar"]),
        "dis_form_idleri": denetim["dis_form_idleri"],
        "tehlikeli_baglanti_idleri": denetim["tehlikeli_baglanti_idleri"],
        "gizli_girdi_adlari": denetim["gizli_girdi_adlari"],
        "risk_var_mi": risk_var,
    }

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_ile_guvenlik_09 as deney
    deney.goster(dom_yuzeyi_cikar, baglanti_ve_form_denetle, dom_guvenlik_raporu)
```

```hint
Önceki üç görevdeki `dom_yuzeyi_cikar`, `baglanti_ve_form_denetle` ve `dom_guvenlik_raporu` işlevlerini birleştir.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### DOM bulgusu browser davranışıyla karşılaştırılır

HTML parser form, action ve bağlantıları çıkarır; URL denetimi hedef origin ve tehlikeli şemaları ayırır. Gerçek Chromium farklı çözülmüş URL veya DOM davranışı gösterebilir. Ağ yalıtımı sayesinde incelenen HTMLnin dış hedeflerine istek yapılmaz. Bir formun dış origin taşıması otomatik istismar kanıtı değil, bağlama göre incelenecek bulgudur.

| Yaygın yanlış | Kontrolün gösterdiği |
|---|---|
| HTMLdeki metin gerçek yönlendirme hedefidir | Base URL, ayrıştırma ve tarayıcının çözdüğü hedef ayrı okunur. |

Sonraki bağlantı: ai-saldiri-31. [Birincil kaynak](https://docs.python.org/3/library/html.parser.html). Kaynak ilgili araç veya yöntemi açıklar; labın gerçek sonucu ham kanıt kaydındadır.
:::
