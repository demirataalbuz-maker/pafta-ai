---
id: ai-ile-guvenlik-06
title: "Yama Önerisi Üretimi ve Regresyon Doğrulaması"
summary: LLM tarafından önerilen güvenlik yamalarını AST sözdizimi kontrolü, işlevsel regresyon testi ve güvenlik istismar testi üçlü kapısından geçirerek doğrula.
timeout: 300
esleme: ai-ile-guvenlik-04, ai-savunma-16
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et
Bir dil modelinden zafiyetli bir fonksiyon için *"güvenli yama üret"* istediğimizde model üç farklı biçimde başarısız olabilir: (1) sözdizimi bozuk kod üretebilir (`SyntaxError`), (2) zafiyeti kapatayım derken fonksiyonu tamamen bozup her girdide `None` döndürerek **işlevsel regresyon** yaratabilir (`ai-savunma-16` dersindeki güvenlik/kullanılabilirlik dengesini hatırla) veya (3) `+` birleştirmesini `f-string` ile değiştirip SQL enjeksiyonu zafiyetini olduğu gibi bırakabilir. Bu yüzden hiçbir LLM yaması **sözdizimi + regresyon + güvenlik** doğrulama kapısından geçmeden kabul edilmez.

| Gerçek araç / model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Python `ast.parse` ağacını, birim test koşucusunu ve yerel Ollama modelinin (`qwen3`) ürettiği yama önerisini | İlk üç görevde `zafiyetli_fonksiyon.py` ve `aday_yamalar.json` içindeki **sentetik** yama adaylarını; son görevde canlı `ai_lab.SohbetOturumu` ile yama doğrulama deneyini | Birim testlerinden geçen bir yamanın tüm üretim veritabanı motorlarında (`PostgreSQL`, `SQLite`, `MySQL`) performans veya kilitlenme (`deadlock`) sorunu yaratmayacağını garanti edemez |

> [!GÜVENLİK]
> **Kapsam ve dürüstlük sınırı:** İlk üç görevdeki aday yamalar ve `SahteVeritabani` sınıfı **sentetik** eğitim verisidir; her çalıştırmada (`setup`) yeniden yüklenir ve kalıcılık bırakmaz.
:::

::: anlat Yama doğrulama kapısı üç bağımsız kanıt arar
Güvenli yama doğrulama hattı (`patch verification pipeline`) aday kodu üç aşamada sınar:

1. **AST Yapısal Kontrolü (`yama_ast_kontrolu`):**
   - Kod `ast.parse` ile ayrıştırılır; `SyntaxError` oluşursa `sozdizimi_gecerli = False` döner.
   - Ağaç içinde `ast.BinOp` (`+`, `%`) veya `ast.JoinedStr` (`f"..."`) varsa `dinamik_birlestirme_var = True` işaretlenir.
   - `sorgula` metoduna yapılan çağrıda (`dugum.func.attr == "sorgula"`) 2 konumsal argüman (`len(dugum.args) == 2`) varsa ve ilk argüman sabit dizge (`isinstance(dugum.args[0], ast.Constant)`) ise `parametrik_cagri = True` işaretlenir.
2. **Çalışma Zamanı Regresyon ve Güvenlik Testi (`yama_test_kosumu`):**
   - **Regresyon testi:** Normal kullanıcı (`"ayse"` -> `{"id": 1, "rol": "analist"}`) ve boş girdi (`""` -> `None`) beklendiği gibi çalışıyor mu?
   - **Güvenlik testi:** Enjeksiyon yükü (`"' OR 'a'='a'"`) verildiğinde sızıntı engelleniyor (`None`), parametre demet olarak (`("' OR 'a'='a'",)`) iletiliyor ve AST üzerinde dinamik birleştirme bulunmuyor mu?
3. **Aday Yama Seçimi (`aday_yamalari_denetle`):** Her aday yama sırasıyla `"sozdizimi_hatasi"`, `"regresyon_hatasi"` veya `"guvenlik_hatasi"` nedenlerinden biriyle elenir ya da tüm kapıları geçerse `kabul_edilen_yamalar` listesine alınır.
:::

::: anlat Bulguyu sınırlı ve doğrulanabilir yaz: işlevi bozan yama güvenli değildir
Her girdiye `return None` döndüren bir yama tüm enjeksiyon yüklerini engeller (`r_saldiri is None`), fakat normal kullanıcı sorgularını da kırdığı için **regresyon hatası** (`regresyon_hatasi`) olarak reddedilmelidir. Güvenlik kapısı her zaman işlevsel regresyon kapısından sonra değerlendirilir.
:::

::: tahmin AST üzerinde f-string ile parametrik çağrı farkını tahmin et
Aşağıdaki Python kodunun çıktısını tahmin et:

```python
import ast

kod1 = "db.sorgula(f'SELECT * FROM t WHERE a = {x}')"
kod2 = "db.sorgula('SELECT * FROM t WHERE a = ?', (x,))"

def incele(k):
    agac = ast.parse(k)
    fstr = any(isinstance(d, ast.JoinedStr) for d in ast.walk(agac))
    cagri = next(d for d in ast.walk(agac) if isinstance(d, ast.Call))
    return (fstr, len(cagri.args))

print(incele(kod1), incele(kod2))
```

???

```cikti
(True, 1) (False, 2)
```

`kod1` içinde `f-string` (`ast.JoinedStr` -> `True`) ve tek argüman (`1`) varken, `kod2` içinde `f-string` yoktur (`False`) ve sorgu metni ile parametre demeti ayrı argümanlar (`2`) olarak geçilmiştir.
:::

::: gorev 1 · Aday yamanın AST sözdizimi ve parametrik sorgu yapısını kontrol et
`yama_ast_kontrolu(yama_kodu)` işlevini yaz.

Girdi kuralları:
- `yama_kodu`: boş olmayan (`strip()` sonrası dolu) `str`. Boş metin veya `str` dışı tipte `ValueError` yükselt.

AST kontrol kuralları:
- `ast.parse(yama_kodu)` sırasında `SyntaxError` oluşursa `{"sozdizimi_gecerli": False, "parametrik_cagri": False, "dinamik_birlestirme_var": False}` döndür.
- Sözdizimi geçerliyse `ast.walk` ile tüm düğümleri tara:
  - Herhangi bir düğüm `ast.BinOp` veya `ast.JoinedStr` ise `dinamik_birlestirme_var = True`.
  - Herhangi bir `ast.Call` düğümünde `isinstance(dugum.func, ast.Attribute)` ve `dugum.func.attr == "sorgula"` ve `len(dugum.args) == 2` ve `isinstance(dugum.args[0], ast.Constant)` ise `parametrik_cagri = True`.
- Sonucu `{"sozdizimi_gecerli": True, "parametrik_cagri": ..., "dinamik_birlestirme_var": ...}` olarak döndür.

```starter
import ast
from ai_ile_guvenlik_veri import json_yukle

yamalar = json_yukle("aday_yamalar.json")

def yama_ast_kontrolu(yama_kodu):
    # HATA: Sözdizimi hatasını yakalamıyor ve dinamik birleştirmeyi kontrol etmiyor.
    agac = ast.parse(yama_kodu)
    return {
        "sozdizimi_gecerli": True,
        "parametrik_cagri": True,
        "dinamik_birlestirme_var": False,
    }

print(yama_ast_kontrolu(yamalar[3]["kod"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-06")
```

```test
need("yama_ast_kontrolu")

def sozlesme(fn):
    try:
        k_gecerli = "def f(vt, u):\n    return vt.sorgula('SELECT * WHERE a = ?', (u,))\n"
        if fn(k_gecerli) != {
            "sozdizimi_gecerli": True,
            "parametrik_cagri": True,
            "dinamik_birlestirme_var": False,
        }:
            return False

        k_binop = "def f(vt, u):\n    return vt.sorgula('SELECT ' + u)\n"
        if fn(k_binop) != {
            "sozdizimi_gecerli": True,
            "parametrik_cagri": False,
            "dinamik_birlestirme_var": True,
        }:
            return False

        k_fstr = "def f(vt, u):\n    return vt.sorgula(f'SELECT {u}', (u,))\n"
        if fn(k_fstr) != {
            "sozdizimi_gecerli": True,
            "parametrik_cagri": False,
            "dinamik_birlestirme_var": True,
        }:
            return False

        k_uc_arg = "def f(vt, u):\n    return vt.sorgula('SELECT ?', (u,), True)\n"
        if fn(k_uc_arg)["parametrik_cagri"] is not False:
            return False

        k_baska = "def f(vt, u):\n    return vt.calistir('SELECT ?', (u,))\n"
        if fn(k_baska)["parametrik_cagri"] is not False:
            return False
        k_isim_cagri = "def f(vt, u):\n    len(u)\n    return vt.sorgula('SELECT ?', (u,))\n"
        if fn(k_isim_cagri)["parametrik_cagri"] is not True:
            return False

        if fn("def bozuk(:") != {
            "sozdizimi_gecerli": False,
            "parametrik_cagri": False,
            "dinamik_birlestirme_var": False,
        }:
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

ok(sozlesme(yama_ast_kontrolu), "AST kontrolü sözdizimi, parametrik çağrı ve dinamik birleştirmeyi doğru tespit etmeli")
def m_hep_parametrik(k):
    return dict(yama_ast_kontrolu(k), parametrik_cagri=True)
def m_birlestirme_gizleyen(k):
    return dict(yama_ast_kontrolu(k), dinamik_birlestirme_var=False)
for ad, mutant in [("hep parametrik sayan", m_hep_parametrik), ("dinamik birleştirmeyi gizleyen", m_birlestirme_gizleyen)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
import ast

def yama_ast_kontrolu(yama_kodu):
    if not isinstance(yama_kodu, str) or not yama_kodu.strip():
        raise ValueError("yama_kodu boş olmayan string olmalı")
    try:
        agac = ast.parse(yama_kodu)
    except SyntaxError:
        return {
            "sozdizimi_gecerli": False,
            "parametrik_cagri": False,
            "dinamik_birlestirme_var": False,
        }

    parametrik_cagri = False
    dinamik_birlestirme_var = False

    for dugum in ast.walk(agac):
        if isinstance(dugum, (ast.BinOp, ast.JoinedStr)):
            dinamik_birlestirme_var = True
        if isinstance(dugum, ast.Call) and isinstance(dugum.func, ast.Attribute):
            if dugum.func.attr == "sorgula":
                if len(dugum.args) == 2 and isinstance(dugum.args[0], ast.Constant):
                    parametrik_cagri = True

    return {
        "sozdizimi_gecerli": True,
        "parametrik_cagri": parametrik_cagri,
        "dinamik_birlestirme_var": dinamik_birlestirme_var,
    }
```

```hint
`ast.BinOp` ve `ast.JoinedStr` düğümlerini kontrol ederek dinamik metin birleştirmeyi yakala; `sorgula` çağrısında `len(dugum.args) == 2` ve ilk argümanın `ast.Constant` olup olmadığına bak.
```
:::

::: gorev 2 · Aday yamayı işlevsel regresyon ve SQL enjeksiyonu testlerinden geçir
`yama_test_kosumu(yama_kodu)` işlevini yaz.

Girdi kuralları:
- `yama_kodu`: 1. görevdeki kurallarla aynıdır.

Test koşumu kuralları:
1. Önce 1. görevdeki kurallarla AST kontrolünü çalıştır; `sozdizimi_gecerli` `False` ise `{"sozdizimi_gecerli": False, "regresyon_gecti": False, "guvenlik_gecti": False}` döndür.
2. Kodu yalıtılmış bir sözlükte (`alan = {}`; `exec(yama_kodu, {}, alan)`) çalıştır ve `kullanici_getir` işlevini al (`callable` değilse veya `exec`/çağrı sırasında istisna çıkarsa `regresyon_gecti=False, guvenlik_gecti=False` döndür).
3. Testlerde `ai_gercek_ai_ile_guvenlik_06.SahteVeritabani` sınıfını kullan:
   - **Regresyon testi:** `vt1 = SahteVeritabani()` oluştur. `fn(vt1, "ayse") == {"id": 1, "rol": "analist"}` ve `fn(vt1, "") is None` ise `regresyon_gecti = True`.
   - **Güvenlik testi:** `vt2 = SahteVeritabani()` oluştur ve `saldiri = "' OR 'a'='a'"` ile `r_saldiri = fn(vt2, saldiri)` çağır. Eğer `parametrik_cagri` `True`, `dinamik_birlestirme_var` `False`, `r_saldiri is None` ve `vt2.son_parametreler == (saldiri,)` ise `guvenlik_gecti = True`.

```starter
from ai_ile_guvenlik_veri import json_yukle
from ai_gercek_ai_ile_guvenlik_06 import SahteVeritabani

yamalar = json_yukle("aday_yamalar.json")

def yama_test_kosumu(yama_kodu):
    # HATA: Regresyon ve güvenlik testlerini gerçekten koşmuyor.
    return {
        "sozdizimi_gecerli": True,
        "regresyon_gecti": True,
        "guvenlik_gecti": True,
    }

for y in yamalar:
    print(y["yama_id"], yama_test_kosumu(y["kod"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-06")
```

```test
need("yama_test_kosumu")

K_BOZUK = "def kullanici_getir(vt, u):\n    return vt.sorgula(\n"
K_REGRESYON = "def kullanici_getir(vt, u):\n    return None\n"
K_BOS_HATALI = "def kullanici_getir(vt, u):\n    return vt.sorgula('SELECT id, rol FROM kullanicilar WHERE ad = ?', ('ayse',))\n"
K_ZAFIYETLI = (
    "def kullanici_getir(vt, u):\n"
    "    if not u:\n"
    "        return None\n"
    "    return vt.sorgula(f\"SELECT id, rol FROM kullanicilar WHERE ad = '{u}'\")\n"
)
K_BINA_YAMA = (
    "def kullanici_getir(vt, u):\n"
    "    if not u:\n"
    "        return None\n"
    "    x = 'a' + 'b'\n"
    "    return vt.sorgula('SELECT id, rol FROM kullanicilar WHERE ad = ?', (u,))\n"
)
K_DEGISKEN_SORGU = (
    "def kullanici_getir(vt, u):\n"
    "    if not u:\n"
    "        return None\n"
    "    s = 'SELECT id, rol FROM kullanicilar WHERE ad = ?'\n"
    "    return vt.sorgula(s, (u,))\n"
)
K_GECERLI = (
    "def kullanici_getir(vt, u):\n"
    "    if not u:\n"
    "        return None\n"
    "    return vt.sorgula('SELECT id, rol FROM kullanicilar WHERE ad = ?', (u,))\n"
)

def sozlesme(fn):
    try:
        if fn(K_BOZUK) != {"sozdizimi_gecerli": False, "regresyon_gecti": False, "guvenlik_gecti": False}:
            return False
        if fn(K_REGRESYON) != {"sozdizimi_gecerli": True, "regresyon_gecti": False, "guvenlik_gecti": False}:
            return False
        if fn(K_BOS_HATALI) != {"sozdizimi_gecerli": True, "regresyon_gecti": False, "guvenlik_gecti": False}:
            return False
        if fn(K_ZAFIYETLI) != {"sozdizimi_gecerli": True, "regresyon_gecti": True, "guvenlik_gecti": False}:
            return False
        if fn(K_BINA_YAMA) != {"sozdizimi_gecerli": True, "regresyon_gecti": True, "guvenlik_gecti": False}:
            return False
        if fn(K_DEGISKEN_SORGU) != {"sozdizimi_gecerli": True, "regresyon_gecti": True, "guvenlik_gecti": False}:
            return False
        if fn("x = 1") != {"sozdizimi_gecerli": True, "regresyon_gecti": False, "guvenlik_gecti": False}:
            return False
        if fn("def kullanici_getir(vt, u):\n    raise RuntimeError('hata')\n") != {"sozdizimi_gecerli": True, "regresyon_gecti": False, "guvenlik_gecti": False}:
            return False
        if fn(K_GECERLI) != {"sozdizimi_gecerli": True, "regresyon_gecti": True, "guvenlik_gecti": True}:
            return False
        if fn("def kullanici_getir(vt, u):\n    if not u: return None\n    len(u)\n    return vt.sorgula('SELECT id, rol FROM kullanicilar WHERE ad = ?', (u,))\n") != {"sozdizimi_gecerli": True, "regresyon_gecti": True, "guvenlik_gecti": True}:
            return False
        if fn("def kullanici_getir(vt, u):\n    if not u: return None\n    'x'.replace('a', 'b')\n    s = 'SELECT id, rol FROM kullanicilar WHERE ad = ?'\n    return vt.sorgula(s, (u,))\n") != {"sozdizimi_gecerli": True, "regresyon_gecti": True, "guvenlik_gecti": False}:
            return False
        if fn("def kullanici_getir(vt, u):\n    if not u: return None\n    if False: vt.sorgula('SELECT ?')\n    s = 'SELECT id, rol FROM kullanicilar WHERE ad = ?'\n    return vt.sorgula(s, (u,))\n") != {"sozdizimi_gecerli": True, "regresyon_gecti": True, "guvenlik_gecti": False}:
            return False
        if fn("def kullanici_getir(vt, u):\n    if not u: return None\n    vt.sorgula('SELECT id, rol FROM kullanicilar WHERE ad = ?', (u,))\n    return {'id': 1, 'rol': 'analist'}\n") != {"sozdizimi_gecerli": True, "regresyon_gecti": True, "guvenlik_gecti": False}:
            return False
        if fn("def kullanici_getir(vt, u):\n    if not u: return None\n    p = (u,) if u == 'ayse' else ('sabit',)\n    return vt.sorgula('SELECT id, rol FROM kullanicilar WHERE ad = ?', p)\n") != {"sozdizimi_gecerli": True, "regresyon_gecti": True, "guvenlik_gecti": False}:
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

ok(sozlesme(yama_test_kosumu), "yama test koşumu regresyon ve güvenlik kapılarını doğru değerlendirmeli")
def m_regresyon_atlayan(k):
    return dict(yama_test_kosumu(k), regresyon_gecti=True)
def m_guvenlik_atlayan(k):
    return dict(yama_test_kosumu(k), guvenlik_gecti=True)
for ad, mutant in [("regresyonu hep geçiren", m_regresyon_atlayan), ("güvenliği hep geçiren", m_guvenlik_atlayan)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
import ast
from ai_gercek_ai_ile_guvenlik_06 import SahteVeritabani

def _ast_kontrol(yama_kodu):
    if not isinstance(yama_kodu, str) or not yama_kodu.strip():
        raise ValueError("yama_kodu boş olmayan string olmalı")
    try:
        agac = ast.parse(yama_kodu)
    except SyntaxError:
        return {
            "sozdizimi_gecerli": False,
            "parametrik_cagri": False,
            "dinamik_birlestirme_var": False,
        }

    parametrik_cagri = False
    dinamik_birlestirme_var = False

    for dugum in ast.walk(agac):
        if isinstance(dugum, (ast.BinOp, ast.JoinedStr)):
            dinamik_birlestirme_var = True
        if isinstance(dugum, ast.Call) and isinstance(dugum.func, ast.Attribute):
            if dugum.func.attr == "sorgula":
                if len(dugum.args) == 2 and isinstance(dugum.args[0], ast.Constant):
                    parametrik_cagri = True

    return {
        "sozdizimi_gecerli": True,
        "parametrik_cagri": parametrik_cagri,
        "dinamik_birlestirme_var": dinamik_birlestirme_var,
    }

def yama_test_kosumu(yama_kodu):
    ast_sonuc = _ast_kontrol(yama_kodu)
    if not ast_sonuc["sozdizimi_gecerli"]:
        return {
            "sozdizimi_gecerli": False,
            "regresyon_gecti": False,
            "guvenlik_gecti": False,
        }

    alan = {}
    try:
        exec(yama_kodu, {}, alan)
        fn = alan.get("kullanici_getir")
        if not callable(fn):
            return {
                "sozdizimi_gecerli": True,
                "regresyon_gecti": False,
                "guvenlik_gecti": False,
            }
        vt1 = SahteVeritabani()
        r_ayse = fn(vt1, "ayse")
        r_bos = fn(vt1, "")
        regresyon_gecti = (r_ayse == {"id": 1, "rol": "analist"}) and (r_bos is None)

        vt2 = SahteVeritabani()
        saldiri = "' OR 'a'='a'"
        r_saldiri = fn(vt2, saldiri)
        guvenlik_gecti = (
            ast_sonuc["parametrik_cagri"]
            and not ast_sonuc["dinamik_birlestirme_var"]
            and r_saldiri is None
            and vt2.son_parametreler == (saldiri,)
        )
    except Exception:
        return {
            "sozdizimi_gecerli": True,
            "regresyon_gecti": False,
            "guvenlik_gecti": False,
        }

    return {
        "sozdizimi_gecerli": True,
        "regresyon_gecti": bool(regresyon_gecti),
        "guvenlik_gecti": bool(guvenlik_gecti),
    }
```

```hint
`exec(yama_kodu, {}, alan)` ile fonksiyonu yükledikten sonra `SahteVeritabani` üzerinde hem `"ayse"` ve `""` (regresyon) hem de `"' OR '1'='1'"` (güvenlik) senaryolarını çalıştır.
```
:::

::: gorev 3 · Aday yamaları üçlü doğrulama kapısından geçir ve red nedenlerini sınıflandır
`aday_yamalari_denetle(adaylar)` işlevini yaz.

Girdi kuralları:
- `adaylar`: boş olmayan `list`; her öğe tam olarak `{"yama_id", "kod"}` anahtarlarına sahip `dict` olmalı, `yama_id` boş olmayan benzersiz `str` ve `kod` boş olmayan `str` olmalıdır.
- Geçersiz girdi veya şemada `ValueError` yükselt.

Denetim kuralları:
- Her aday için 2. görevdeki test koşumunu çalıştır ve sırasıyla kontrol et:
  1. `not sonuc["sozdizimi_gecerli"]` -> `reddedilen_yamalar[yama_id] = "sozdizimi_hatasi"`
  2. `not sonuc["regresyon_gecti"]` -> `reddedilen_yamalar[yama_id] = "regresyon_hatasi"`
  3. `not sonuc["guvenlik_gecti"]` -> `reddedilen_yamalar[yama_id] = "guvenlik_hatasi"`
  4. Üçü de `True` ise `kabul_edilen_yamalar` listesine `yama_id` ekle.
- Sonucu `{"kabul_edilen_yamalar": sorted(...), "reddedilen_yamalar": ..., "kabul_sayisi": ...}` olarak döndür.

```starter
from ai_ile_guvenlik_veri import json_yukle

yamalar = json_yukle("aday_yamalar.json")

def aday_yamalari_denetle(adaylar):
    # HATA: Tüm aday yamaları doğrulamadan kabul ediyor.
    ids = [a["yama_id"] for a in adaylar]
    return {
        "kabul_edilen_yamalar": sorted(ids),
        "reddedilen_yamalar": {},
        "kabul_sayisi": len(ids),
    }

print(aday_yamalari_denetle(yamalar))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-06")
```

```test
need("aday_yamalari_denetle")

ADAYLAR = [
    {
        "yama_id": "y1",
        "kod": "def kullanici_getir(vt, u):\n    return vt.sorgula(\n",
    },
    {
        "yama_id": "y2",
        "kod": "def kullanici_getir(vt, u):\n    return None\n",
    },
    {
        "yama_id": "y3",
        "kod": "def kullanici_getir(vt, u):\n    if not u:\n        return None\n    return vt.sorgula(f\"SELECT id, rol FROM kullanicilar WHERE ad = '{u}'\")\n",
    },
    {
        "yama_id": "y4",
        "kod": "def kullanici_getir(vt, u):\n    if not u:\n        return None\n    return vt.sorgula('SELECT id, rol FROM kullanicilar WHERE ad = ?', (u,))\n",
    },
]

def sozlesme(fn):
    try:
        r = fn(ADAYLAR)
        if r != {
            "kabul_edilen_yamalar": ["y4"],
            "reddedilen_yamalar": {
                "y1": "sozdizimi_hatasi",
                "y2": "regresyon_hatasi",
                "y3": "guvenlik_hatasi",
            },
            "kabul_sayisi": 1,
        }:
            return False

        a_bos_hatali = [{"yama_id": "yb", "kod": "def kullanici_getir(vt, u):\n    return vt.sorgula('SELECT ?', ('ayse',))\n"}]
        if fn(a_bos_hatali)["reddedilen_yamalar"] != {"yb": "regresyon_hatasi"}:
            return False

        a_binop = [{"yama_id": "ybin", "kod": "def kullanici_getir(vt, u):\n    if not u: return None\n    x = 'a' + 'b'\n    return vt.sorgula('SELECT ?', (u,))\n"}]
        if fn(a_binop)["reddedilen_yamalar"] != {"ybin": "guvenlik_hatasi"}:
            return False

        a_degisken = [{"yama_id": "ydeg", "kod": "def kullanici_getir(vt, u):\n    if not u: return None\n    s = 'SELECT ?'\n    return vt.sorgula(s, (u,))\n"}]
        if fn(a_degisken)["reddedilen_yamalar"] != {"ydeg": "guvenlik_hatasi"}:
            return False

        a_uc_arg = [{"yama_id": "yuc", "kod": "def kullanici_getir(vt, u):\n    if not u: return None\n    return vt.sorgula('SELECT ?', (u,), 1)\n"}]
        if fn(a_uc_arg)["reddedilen_yamalar"] != {"yuc": "regresyon_hatasi"}:
            return False

        a_callable_degil = [{"yama_id": "yc", "kod": "kullanici_getir = 123\n"}]
        if fn(a_callable_degil)["reddedilen_yamalar"] != {"yc": "regresyon_hatasi"}:
            return False
        if fn([{"yama_id": "ylen", "kod": "def kullanici_getir(vt, u):\n    if not u: return None\n    len(u)\n    return vt.sorgula('SELECT id, rol FROM kullanicilar WHERE ad = ?', (u,))\n"}])["kabul_edilen_yamalar"] != ["ylen"]:
            return False
        for idx_k, kod_k in enumerate([
            "def kullanici_getir(vt, u):\n    if not u: return None\n    'x'.replace('a', 'b')\n    s = 'SELECT ?'\n    return vt.sorgula(s, (u,))\n",
            "def kullanici_getir(vt, u):\n    if not u: return None\n    if False: vt.sorgula('SELECT ?')\n    s = 'SELECT ?'\n    return vt.sorgula(s, (u,))\n",
            "def kullanici_getir(vt, u):\n    if not u: return None\n    vt.sorgula('SELECT ?', (u,))\n    return {'id': 1, 'rol': 'analist'}\n",
            "def kullanici_getir(vt, u):\n    if not u: return None\n    p = (u,) if u == 'ayse' else ('sabit',)\n    return vt.sorgula('SELECT ?', p)\n",
        ]):
            if fn([{"yama_id": f"yk{idx_k}", "kod": kod_k}])["reddedilen_yamalar"] != {f"yk{idx_k}": "guvenlik_hatasi"}:
                return False

        hatalilar = [
            None,
            123,
            [],
            "liste",
            ["bozuk"],
            [{"yama_id": "y1"}],
            [{"yama_id": "", "kod": "x=1"}],
            [{"yama_id": "   ", "kod": "x=1"}],
            [{"yama_id": 123, "kod": "x=1"}],
            [{"yama_id": "y1", "kod": ""}],
            [{"yama_id": "y1", "kod": "   "}],
            [{"yama_id": "y1", "kod": None}],
            [ADAYLAR[3], ADAYLAR[3]],
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

ok(sozlesme(aday_yamalari_denetle), "aday yamalar doğru sınıflandırılmalı ve yalnız güvenli+çalışan yama kabul edilmeli")
def m_hepsini_kabul(a):
    return dict(aday_yamalari_denetle(a), reddedilen_yamalar={})
def m_hic_kabul_etmeyen(a):
    return dict(aday_yamalari_denetle(a), kabul_edilen_yamalar=[], kabul_sayisi=0)
for ad, mutant in [("reddedilenleri silen", m_hepsini_kabul), ("geçerli yamayı reddeden", m_hic_kabul_etmeyen)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
import ast
from ai_gercek_ai_ile_guvenlik_06 import SahteVeritabani

def _yama_test(yama_kodu):
    if not isinstance(yama_kodu, str) or not yama_kodu.strip():
        raise ValueError("yama_kodu boş olmayan string olmalı")
    try:
        agac = ast.parse(yama_kodu)
    except SyntaxError:
        return {
            "sozdizimi_gecerli": False,
            "regresyon_gecti": False,
            "guvenlik_gecti": False,
        }

    parametrik_cagri = False
    dinamik_birlestirme_var = False

    for dugum in ast.walk(agac):
        if isinstance(dugum, (ast.BinOp, ast.JoinedStr)):
            dinamik_birlestirme_var = True
        if isinstance(dugum, ast.Call) and isinstance(dugum.func, ast.Attribute):
            if dugum.func.attr == "sorgula":
                if len(dugum.args) == 2 and isinstance(dugum.args[0], ast.Constant):
                    parametrik_cagri = True

    alan = {}
    try:
        exec(yama_kodu, {}, alan)
        fn = alan.get("kullanici_getir")
        if not callable(fn):
            return {
                "sozdizimi_gecerli": True,
                "regresyon_gecti": False,
                "guvenlik_gecti": False,
            }
        vt1 = SahteVeritabani()
        r_ayse = fn(vt1, "ayse")
        r_bos = fn(vt1, "")
        regresyon_gecti = (r_ayse == {"id": 1, "rol": "analist"}) and (r_bos is None)

        vt2 = SahteVeritabani()
        saldiri = "' OR 'a'='a'"
        r_saldiri = fn(vt2, saldiri)
        guvenlik_gecti = (
            parametrik_cagri
            and not dinamik_birlestirme_var
            and r_saldiri is None
            and vt2.son_parametreler == (saldiri,)
        )
    except Exception:
        return {
            "sozdizimi_gecerli": True,
            "regresyon_gecti": False,
            "guvenlik_gecti": False,
        }

    return {
        "sozdizimi_gecerli": True,
        "regresyon_gecti": bool(regresyon_gecti),
        "guvenlik_gecti": bool(guvenlik_gecti),
    }

def aday_yamalari_denetle(adaylar):
    if not isinstance(adaylar, list) or not adaylar:
        raise ValueError("adaylar boş olamaz")

    gorulen = set()
    kabul_edilenler = []
    reddedilenler = {}

    for aday in adaylar:
        if not isinstance(aday, dict) or set(aday.keys()) != {"yama_id", "kod"}:
            raise ValueError("aday şeması geçersiz")
        yid = aday["yama_id"]
        kod = aday["kod"]
        if not isinstance(yid, str) or not yid.strip() or yid in gorulen:
            raise ValueError("yama_id geçersiz veya tekrarlı")
        gorulen.add(yid)

        sonuc = _yama_test(kod)
        if not sonuc["sozdizimi_gecerli"]:
            reddedilenler[yid] = "sozdizimi_hatasi"
        elif not sonuc["regresyon_gecti"]:
            reddedilenler[yid] = "regresyon_hatasi"
        elif not sonuc["guvenlik_gecti"]:
            reddedilenler[yid] = "guvenlik_hatasi"
        else:
            kabul_edilenler.append(yid)

    return {
        "kabul_edilen_yamalar": sorted(kabul_edilenler),
        "reddedilen_yamalar": reddedilenler,
        "kabul_sayisi": len(kabul_edilenler),
    }
```

```hint
Önce `sozdizimi_gecerli`, sonra `regresyon_gecti`, en son `guvenlik_gecti` durumunu kontrol ederek hata sınıfını ata.
```
:::

::: gorev Gerçek deney · Yerel modelle güvenlik yaması üretimi ve regresyon doğrulama kapısı
Önceki üç görevde yazdığın `yama_ast_kontrolu`, `yama_test_kosumu` ve `aday_yamalari_denetle` işlevlerini bu adımda birleştir.

Canlı deneyde:
1. Zafiyetli fonksiyon yerel Ollama modeline (`ai_lab.SohbetOturumu`) gönderilerek parametrik sorgu yaması istenir.
2. Bozuk sözdizimli, regresyon yaratan, hâlâ zafiyetli olan ve tam parametrik olan aday yamalar `aday_yamalari_denetle` kapısından geçirilir.
3. Yalnız hem regresyon hem de güvenlik testini geçen yamanın kabul edildiği doğrulanır.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def yama_ast_kontrolu(yama_kodu):
    return {}

def yama_test_kosumu(yama_kodu):
    return {}

def aday_yamalari_denetle(adaylar):
    return {}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_ile_guvenlik_06 as deney
    deney.goster(yama_ast_kontrolu, yama_test_kosumu, aday_yamalari_denetle)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-06")
```

```test
import ai_lab
from sandbox import ai_gercek_ai_ile_guvenlik_06 as D

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for ad in ("yama_ast_kontrolu", "yama_test_kosumu", "aday_yamalari_denetle"):
    need(ad)

# Yamayı exec ile yüklemek bu dersin konusu; bu yüzden exec serbest, dosya okuma yasak.
sorun = ai_lab.kod_denetimi(
    src,
    ("yama_ast_kontrolu_referans", "yama_test_kosumu_referans", "aday_yamalari_denetle_referans",
     "open", "read_text", "read_bytes", "io", "kanit_yaz"),
    izin=("exec",),
)
ok(not sorun, "laboratuvar yamalanmamalı, referans işlevler çağrılmamalı")

def _on_sozlesme():
    try:
        k_tam = "def kullanici_getir(vt, u):\n    if not u: return None\n    len(u)\n    return vt.sorgula('SELECT id, rol FROM kullanicilar WHERE ad = ?', (u,))\n"
        if yama_ast_kontrolu(k_tam) != {"sozdizimi_gecerli": True, "parametrik_cagri": True, "dinamik_birlestirme_var": False}: return False
        if yama_ast_kontrolu("def bozuk(:") != {"sozdizimi_gecerli": False, "parametrik_cagri": False, "dinamik_birlestirme_var": False}: return False
        if yama_ast_kontrolu("def f(vt, u):\n    return vt.sorgula('SELECT ' + u)\n") != {"sozdizimi_gecerli": True, "parametrik_cagri": False, "dinamik_birlestirme_var": True}: return False
        if yama_ast_kontrolu("def f(vt, u):\n    return vt.sorgula('SELECT ?', (u,), 1)\n")["parametrik_cagri"] is not False: return False
        if yama_ast_kontrolu("def f(vt, u):\n    return vt.calistir('SELECT ?', (u,))\n")["parametrik_cagri"] is not False: return False
        if yama_test_kosumu("def bozuk(:") != {"sozdizimi_gecerli": False, "regresyon_gecti": False, "guvenlik_gecti": False}: return False
        if yama_test_kosumu("kullanici_getir = 123\n") != {"sozdizimi_gecerli": True, "regresyon_gecti": False, "guvenlik_gecti": False}: return False
        if yama_test_kosumu("def kullanici_getir(vt, u):\n    raise RuntimeError('x')\n") != {"sozdizimi_gecerli": True, "regresyon_gecti": False, "guvenlik_gecti": False}: return False
        if yama_test_kosumu("def kullanici_getir(vt, u):\n    return None\n") != {"sozdizimi_gecerli": True, "regresyon_gecti": False, "guvenlik_gecti": False}: return False
        if yama_test_kosumu("def kullanici_getir(vt, u):\n    return vt.sorgula('SELECT ?', ('ayse',))\n") != {"sozdizimi_gecerli": True, "regresyon_gecti": False, "guvenlik_gecti": False}: return False
        if yama_test_kosumu(k_tam) != {"sozdizimi_gecerli": True, "regresyon_gecti": True, "guvenlik_gecti": True}: return False
        for kod_g in [
            "def kullanici_getir(vt, u):\n    if not u: return None\n    x = 'a' + 'b'\n    return vt.sorgula('SELECT ?', (u,))\n",
            "def kullanici_getir(vt, u):\n    if not u: return None\n    'x'.replace('a', 'b')\n    s = 'SELECT ?'\n    return vt.sorgula(s, (u,))\n",
            "def kullanici_getir(vt, u):\n    if not u: return None\n    if False: vt.sorgula('SELECT ?')\n    s = 'SELECT ?'\n    return vt.sorgula(s, (u,))\n",
            "def kullanici_getir(vt, u):\n    if not u: return None\n    vt.sorgula('SELECT ?', (u,))\n    return {'id': 1, 'rol': 'analist'}\n",
            "def kullanici_getir(vt, u):\n    if not u: return None\n    p = (u,) if u == 'ayse' else ('sabit',)\n    return vt.sorgula('SELECT ?', p)\n",
        ]:
            if yama_test_kosumu(kod_g) != {"sozdizimi_gecerli": True, "regresyon_gecti": True, "guvenlik_gecti": False}: return False
        denetim = aday_yamalari_denetle([
            {"yama_id": "y1", "kod": "def bozuk(:"},
            {"yama_id": "y2", "kod": "def kullanici_getir(vt, u):\n    return None\n"},
            {"yama_id": "y3", "kod": "def kullanici_getir(vt, u):\n    if not u: return None\n    s = 'SELECT ?'\n    return vt.sorgula(s, (u,))\n"},
            {"yama_id": "y4", "kod": k_tam},
        ])
        if denetim != {"kabul_edilen_yamalar": ["y4"], "reddedilen_yamalar": {"y1": "sozdizimi_hatasi", "y2": "regresyon_hatasi", "y3": "guvenlik_hatasi"}, "kabul_sayisi": 1}: return False
        for h in (None, 123, "", "   "):
            try:
                yama_ast_kontrolu(h)
                return False
            except ValueError:
                pass
        for a_in in (
            None,
            123,
            [],
            [123],
            [{}],
            [{"yama_id": "", "kod": "x=1"}],
            [{"yama_id": 123, "kod": "x=1"}],
            [{"yama_id": "a", "kod": ""}],
            [D.ADAY_YAMALAR[0], D.ADAY_YAMALAR[0]],
        ):
            try:
                aday_yamalari_denetle(a_in)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(_on_sozlesme(), "sentetik ön kontrol: sınır ve doğrulama kuralları tam")

if not all(checks):
    stop()

try:
    r = D.deney(yama_ast_kontrolu, yama_test_kosumu, aday_yamalari_denetle)
except Exception as e:
    ok(False, f"GERÇEK YAMA DOĞRULAMA DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

for ad, deger in r["kontroller"].items():
    ok(deger, "gerçek deney: " + ad)

ai_lab.kanit_yaz("ile-guvenlik-06-yama", {
    "kaynak": "gercek",
    "kabul": all(checks),
    "ders": "ai-ile-guvenlik-06",
    "ortam": r["ortam"],
    "ayarlar": r["ayarlar"],
    "deney": r,
    "ozet": r["ozet"],
})
o = r["ozet"]
ok(
    True,
    f"BULGU ({o['model']}): kabul_edilen={o['kabul_edilen']}, reddedilen={o['reddedilen']}.",
)
```

```solution
import ast
import ai_lab
from ai_gercek_ai_ile_guvenlik_06 import SahteVeritabani

def yama_ast_kontrolu(yama_kodu):
    if not isinstance(yama_kodu, str) or not yama_kodu.strip():
        raise ValueError("yama_kodu boş olmayan string olmalı")
    try:
        agac = ast.parse(yama_kodu)
    except SyntaxError:
        return {
            "sozdizimi_gecerli": False,
            "parametrik_cagri": False,
            "dinamik_birlestirme_var": False,
        }

    parametrik_cagri = False
    dinamik_birlestirme_var = False

    for dugum in ast.walk(agac):
        if isinstance(dugum, (ast.BinOp, ast.JoinedStr)):
            dinamik_birlestirme_var = True
        if isinstance(dugum, ast.Call) and isinstance(dugum.func, ast.Attribute):
            if dugum.func.attr == "sorgula":
                if len(dugum.args) == 2 and isinstance(dugum.args[0], ast.Constant):
                    parametrik_cagri = True

    return {
        "sozdizimi_gecerli": True,
        "parametrik_cagri": parametrik_cagri,
        "dinamik_birlestirme_var": dinamik_birlestirme_var,
    }

def yama_test_kosumu(yama_kodu):
    ast_sonuc = yama_ast_kontrolu(yama_kodu)
    if not ast_sonuc["sozdizimi_gecerli"]:
        return {
            "sozdizimi_gecerli": False,
            "regresyon_gecti": False,
            "guvenlik_gecti": False,
        }

    alan = {}
    try:
        exec(yama_kodu, {}, alan)
        fn = alan.get("kullanici_getir")
        if not callable(fn):
            return {
                "sozdizimi_gecerli": True,
                "regresyon_gecti": False,
                "guvenlik_gecti": False,
            }
        vt1 = SahteVeritabani()
        r_ayse = fn(vt1, "ayse")
        r_bos = fn(vt1, "")
        regresyon_gecti = (r_ayse == {"id": 1, "rol": "analist"}) and (r_bos is None)

        vt2 = SahteVeritabani()
        saldiri = "' OR 'a'='a'"
        r_saldiri = fn(vt2, saldiri)
        guvenlik_gecti = (
            ast_sonuc["parametrik_cagri"]
            and not ast_sonuc["dinamik_birlestirme_var"]
            and r_saldiri is None
            and vt2.son_parametreler == (saldiri,)
        )
    except Exception:
        return {
            "sozdizimi_gecerli": True,
            "regresyon_gecti": False,
            "guvenlik_gecti": False,
        }

    return {
        "sozdizimi_gecerli": True,
        "regresyon_gecti": bool(regresyon_gecti),
        "guvenlik_gecti": bool(guvenlik_gecti),
    }

def aday_yamalari_denetle(adaylar):
    if not isinstance(adaylar, list) or not adaylar:
        raise ValueError("adaylar boş olamaz")

    gorulen = set()
    kabul_edilenler = []
    reddedilenler = {}

    for aday in adaylar:
        if not isinstance(aday, dict) or set(aday.keys()) != {"yama_id", "kod"}:
            raise ValueError("aday şeması geçersiz")
        yid = aday["yama_id"]
        kod = aday["kod"]
        if not isinstance(yid, str) or not yid.strip() or yid in gorulen:
            raise ValueError("yama_id geçersiz veya tekrarlı")
        gorulen.add(yid)

        sonuc = yama_test_kosumu(kod)
        if not sonuc["sozdizimi_gecerli"]:
            reddedilenler[yid] = "sozdizimi_hatasi"
        elif not sonuc["regresyon_gecti"]:
            reddedilenler[yid] = "regresyon_hatasi"
        elif not sonuc["guvenlik_gecti"]:
            reddedilenler[yid] = "guvenlik_hatasi"
        else:
            kabul_edilenler.append(yid)

    return {
        "kabul_edilen_yamalar": sorted(kabul_edilenler),
        "reddedilen_yamalar": reddedilenler,
        "kabul_sayisi": len(kabul_edilenler),
    }

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_ile_guvenlik_06 as deney
    deney.goster(yama_ast_kontrolu, yama_test_kosumu, aday_yamalari_denetle)
```

```hint
Önceki üç görevdeki `yama_ast_kontrolu`, `yama_test_kosumu` ve `aday_yamalari_denetle` işlevlerini birleştir.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Yamanın üç kapısı farklı hataları yakalar

AST sözdizimi ve parametrik sorgu biçimi adayın yapısını denetler; işlevsel regresyon normal sorgunun hâlâ çalıştığını, enjeksiyon sınaması ise seçilen saldırıların veri olarak kaldığını kontrol eder. Sadece syntax düzeltmek güvenlik yaması değildir. Dar SQLite labında geçen aday bütün veri tabanı sürücüleri ve sorgu bağlamları için ispat sayılmaz.

| Yaygın yanlış | Kontrolün gösterdiği |
|---|---|
| AST parse başarılıysa SQLi kapalıdır | Yapı, normal işlev ve saldırı sonucu birlikte sınanır. |

Sonraki bağlantı: ai-ile-guvenlik-04. [Birincil kaynak](https://docs.python.org/3/library/ast.html). Kaynak ilgili araç veya yöntemi açıklar; labın gerçek sonucu ham kanıt kaydındadır.
:::
