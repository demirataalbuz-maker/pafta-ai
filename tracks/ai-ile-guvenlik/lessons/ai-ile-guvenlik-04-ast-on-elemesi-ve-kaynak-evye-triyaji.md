---
id: ai-ile-guvenlik-04
title: "AST Ön-Elemesi ve LLM ile source-to-sink Triyajı"
summary: Python ast modülüyle tehlikeli çağrı evyelerini (subprocess, eval, system, execute) çıkar, sabit argümanları dinamik girdilerden ayır ve LLM triyajındaki yanlış pozitif oranını ölç.
esleme: ai-savunma-11
timeout: 300
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et
Büyük bir kod tabanını doğrudan bir dil modelinin bağlam penceresine verip *"açıkları bul"* demek hem pahalıdır hem de yüksek yanlış alarm (`false positive`) üretir. Tersine, yalnız `grep` veya basit regex ile `subprocess.run` aramak da `subprocess.run("python --version")` gibi bu fixture’da sabit (`ast.Constant`) olduğu için düşük-risk etiketi verilen çağrıları alarm olarak işaretler (`pu02` ve `ai-savunma-11` derslerindeki araç/komut sınırlarını hatırla). Doğru mühendislik yaklaşımı **AST ön-elemesi + `source-to-sink` triyajıdır**: önce sözdizimi ağacı (`ast`) tehlikeli evyeleri (`sink`) ve argüman yapısını çıkarır, ardından model yalnız şüpheli akışları inceler.

| Gerçek araç / model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Python `ast.parse` ağacındaki `ast.Call` düğümlerini, argüman tiplerini (`ast.Constant` vs `ast.Name`/`ast.BinOp`) ve yerel Ollama modelinin (`qwen3`) triyaj yanıtını | İlk üç görevde `ornek_servis.py` ve `model_triyaj_kararlari.json` içindeki **sentetik** kod/karar verilerini; son görevde canlı `ai_lab.SohbetOturumu` ve gerçek `ast` ağacıyla hibrit triyaj deneyini | Tek fonksiyon içindeki `ast.Call` argüman kontrolünün, fonksiyonlar ve modüller arası çok adımlı veri akışı (`inter-procedural taint analysis`) analizinin yerini tamamen tutabileceğini söyleyemez |

> [!GÜVENLİK]
> **Kapsam ve dürüstlük sınırı:** İlk üç görevdeki örnek dosyalar **sentetik** eğitim verisidir ve her çalıştırmada (`setup`) çalışma klasörüne yeniden kopyalanır (kalıcılık yoktur). `ast.parse` kodu çalıştırmadan (`exec` etmeden) yalnızca sözdizimi ağacını okur.
:::

::: anlat Statik analiz aday üretir, argüman düğümü sabit ile dinamik girdiyi ayırır
`source-to-sink` triyaj hattı üç aşamada çalışır:

1. **AST Evye Adayı Çıkarma (`ast_evye_adaylari_cikar`):** Kaynak kod `ast.parse` ile ayrıştırılır ve `ast.walk` ile tüm `ast.Call` düğümleri taranır. Çağrı adı `("eval", "exec", "system", "run", "Popen", "execute")` kümesindeyse ve en az bir konumsal argümanı (`dugum.args`) varsa aday listesine alınır. İlk argüman `ast.Constant` ise `"sabit_deger"`, değilse (değişken, birleştirme, f-string vb.) `"dinamik_girdi"` olarak etiketlenir.
2. **Model Triyajı Değerlendirmesi (`kaynak_evye_triyaji`):** Modelin her satır için verdiği `"tehlikeli"` veya `"guvenli"` kararı AST gerçeğiyle karşılaştırılır:
   - `"dinamik_girdi"` + `"tehlikeli"` -> `gercek_acik_satirlari` (True Positive)
   - `"sabit_deger"` + `"tehlikeli"` -> `yanlis_alarm_satirlari` (False Positive)
   - `"dinamik_girdi"` + `"guvenli"` -> `kacirilan_satirlar` (False Negative)
3. **Hibrit Triyaj Kapısı (`hibrit_triyaj_kapisi`):** AST üzerinde `"sabit_deger"` olduğu kesinleşen çağrılar deterministik olarak elenir (`elenen_sabit_satirlar`), dinamik girdili evyeler ise model kaçırmış olsa bile güvenlik kapısında yakalanır (`onaylanan_evye_satirlari`).
:::

::: anlat Bulguyu sınırlı ve doğrulanabilir yaz: yanlış pozitif oranını tüm satırlara değil, verilen alarmlara böl
Modelin yanlış pozitif oranı (`yanlis_pozitif_orani` / False Discovery Rate among alarms) hesaplanırken payda toplam satır sayısı değil, modelin `"tehlikeli"` dediği toplam alarm sayısıdır (`len(gercek_acik_satirlari) + len(yanlis_alarm_satirlari)`). Model hiç `"tehlikeli"` kararı vermemişse oran `0.0` kabul edilir.
:::

::: tahmin AST üzerinde sabit dizge ile değişken argüman ayrımını tahmin et
Aşağıdaki Python kodunun çıktısını tahmin et:

```python
import ast

kod = """
os.system("whoami")
os.system(kullanici_girdisi)
"""
agac = ast.parse(kod)
sonuc = [
    (d.lineno, isinstance(d.args[0], ast.Constant))
    for d in ast.walk(agac)
    if isinstance(d, ast.Call)
]
print(sorted(sonuc))
```

???

```cikti
[(2, True), (3, False)]
```

2. satırdaki `"whoami"` bir sabit dizge (`ast.Constant` -> `True`) iken, 3. satırdaki `kullanici_girdisi` bir değişken adıdır (`ast.Name` -> `False`).
:::

::: gorev 1 · Python AST ağacından tehlikeli evye adaylarını ve argüman türünü çıkar
`ast_evye_adaylari_cikar(kaynak_kodu)` işlevini yaz.

Girdi kuralları:
- `kaynak_kodu`: boş olmayan (`strip()` sonrası dolu) ve geçerli Python sözdizimine sahip `str`. Boş metin, `str` dışı tip veya `SyntaxError` durumunda `ValueError` yükselt.

Çıkarma kuralları:
- Tehlikeli evye adları: `("eval", "exec", "system", "run", "Popen", "execute")`.
- `ast.walk(ast.parse(kaynak_kodu))` içindeki her `ast.Call` düğümünü incele:
  - Çağrı fonksiyonu `ast.Name` ise `func.id`, `ast.Attribute` ise `func.attr` adını al.
  - Eğer ad tehlikeli evye kümesindeyse ve `dugum.args` boş değilse:
    - `dugum.args[0]` bir `ast.Constant` örneğiyse `arguman_turu = "sabit_deger"`, aksi hâlde `"dinamik_girdi"`.
    - `{"satir_no": dugum.lineno, "evye_adi": ad, "arguman_turu": arguman_turu}` kaydını ekle.
- Sonuç listesini `(satir_no, evye_adi)` ikilisine göre artan sırada (`sorted`) döndür.

```starter
import ast
from ai_ile_guvenlik_veri import metin_yukle

kod = metin_yukle("ornek_servis.py")

def ast_evye_adaylari_cikar(kaynak_kodu):
    # HATA: Argümanın sabit mi dinamik mi olduğunu ayırt etmiyor ve Attribute çağrılarını kaçırıyor.
    agac = ast.parse(kaynak_kodu)
    adaylar = []
    for d in ast.walk(agac):
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Name):
            adaylar.append({
                "satir_no": d.lineno,
                "evye_adi": d.func.id,
                "arguman_turu": "dinamik_girdi",
            })
    return adaylar

print(ast_evye_adaylari_cikar(kod))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-04")
```

```test
need("ast_evye_adaylari_cikar")

def sozlesme(fn):
    try:
        kod = (
            "import os, subprocess\n"
            "def f(x):\n"
            "    subprocess.run('ls')\n"
            "    os.system(x)\n"
            "    eval('1+1')\n"
            "    cursor.execute('SELECT ' + x)\n"
            "    print(x)\n"
            "    eval()\n"
        )
        beklenen = [
            {"satir_no": 3, "evye_adi": "run", "arguman_turu": "sabit_deger"},
            {"satir_no": 4, "evye_adi": "system", "arguman_turu": "dinamik_girdi"},
            {"satir_no": 5, "evye_adi": "eval", "arguman_turu": "sabit_deger"},
            {"satir_no": 6, "evye_adi": "execute", "arguman_turu": "dinamik_girdi"},
        ]
        if fn(kod) != beklenen:
            return False

        ayni_satir = "eval('1'); exec(x, 'sabit')"
        if fn(ayni_satir) != [
            {"satir_no": 1, "evye_adi": "eval", "arguman_turu": "sabit_deger"},
            {"satir_no": 1, "evye_adi": "exec", "arguman_turu": "dinamik_girdi"},
        ]:
            return False

        if fn("x = 1 + 2") != []:
            return False
        if fn("(lambda a: a)(1)") != []:
            return False

        for h in (None, 123, "", "   \n ", "def bozuk(:"):
            try:
                fn(h)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(ast_evye_adaylari_cikar), "AST evye adayları ve argüman türleri doğru çıkarılmalı")
def m_hep_dinamik(k):
    return [dict(x, arguman_turu="dinamik_girdi") for x in ast_evye_adaylari_cikar(k)]
def m_ters(k):
    return list(reversed(ast_evye_adaylari_cikar(k)))
for ad, mutant in [("sabit argümanı dinamik sayan", m_hep_dinamik), ("sıralamayı bozan", m_ters)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
import ast

TEHLIKELI_EVYELER = ("eval", "exec", "system", "run", "Popen", "execute")

def _cagri_adi(func_node):
    if isinstance(func_node, ast.Name):
        return func_node.id
    if isinstance(func_node, ast.Attribute):
        return func_node.attr
    return None

def ast_evye_adaylari_cikar(kaynak_kodu):
    if not isinstance(kaynak_kodu, str) or not kaynak_kodu.strip():
        raise ValueError("kaynak kodu boş olmayan string olmalı")
    try:
        agac = ast.parse(kaynak_kodu)
    except SyntaxError as e:
        raise ValueError("geçersiz Python sözdizimi") from e

    adaylar = []
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.Call) and dugum.args:
            ad = _cagri_adi(dugum.func)
            if ad in TEHLIKELI_EVYELER:
                ilk = dugum.args[0]
                sabit_mi = isinstance(ilk, ast.Constant)
                adaylar.append({
                    "satir_no": dugum.lineno,
                    "evye_adi": ad,
                    "arguman_turu": "sabit_deger" if sabit_mi else "dinamik_girdi",
                })
    adaylar.sort(key=lambda x: (x["satir_no"], x["evye_adi"]))
    return adaylar
```

```hint
Hem `eval(...)` (`ast.Name`) hem de `subprocess.run(...)` (`ast.Attribute`) çağrılarını yakalamak için `dugum.func` tipini kontrol et ve ilk argümanın `isinstance(dugum.args[0], ast.Constant)` olup olmadığına bak.
```
:::

::: gorev 2 · Modelin source-to-sink triyaj kararlarını değerlendir ve yanlış pozitif oranını ölç
`kaynak_evye_triyaji(adaylar, model_kararlari)` işlevini yaz.

Girdi kuralları:
- `adaylar`: boş olmayan `list`; her öğesi tam olarak `{"satir_no", "evye_adi", "arguman_turu"}` anahtarlarını taşımalıdır (`satir_no` benzersiz pozitif `int`, `evye_adi` `TEHLIKELI_EVYELER` içinde, `arguman_turu` `("sabit_deger", "dinamik_girdi")` içinde).
- `model_kararlari`: `dict`; her adayın `str(satir_no)` anahtarı bu sözlükte bulunmalı ve değeri `"tehlikeli"` veya `"guvenli"` olmalıdır.
- Geçersiz girdi veya şemada `ValueError` yükselt.

Değerlendirme kuralları:
- `arguman_turu == "dinamik_girdi"` ve `karar == "tehlikeli"` -> `gercek_acik_satirlari` listesine `satir_no` ekle.
- `arguman_turu == "dinamik_girdi"` ve `karar == "guvenli"` -> `kacirilan_satirlar` listesine `satir_no` ekle.
- `arguman_turu == "sabit_deger"` ve `karar == "tehlikeli"` -> `yanlis_alarm_satirlari` listesine `satir_no` ekle.
- `alarm_sayisi = len(gercek_acik_satirlari) + len(yanlis_alarm_satirlari)`.
- `yanlis_pozitif_orani`: `alarm_sayisi > 0` ise `round(len(yanlis_alarm_satirlari) / alarm_sayisi, 4)`, aksi hâlde `0.0`.
- Tüm satır listelerini artan sırada (`sorted`) döndür.

```starter
from ai_ile_guvenlik_veri import json_yukle

kararlar = json_yukle("model_triyaj_kararlari.json")["model_kararlari"]
ornek_adaylar = [
    {"satir_no": 5, "evye_adi": "run", "arguman_turu": "sabit_deger"},
    {"satir_no": 6, "evye_adi": "system", "arguman_turu": "dinamik_girdi"},
    {"satir_no": 7, "evye_adi": "eval", "arguman_turu": "sabit_deger"},
    {"satir_no": 8, "evye_adi": "execute", "arguman_turu": "dinamik_girdi"},
]

def kaynak_evye_triyaji(adaylar, model_kararlari):
    # HATA: Sabit değerli çağrılara verilen "tehlikeli" kararlarını yanlış alarm saymıyor.
    aciklar = [a["satir_no"] for a in adaylar if model_kararlari.get(str(a["satir_no"])) == "tehlikeli"]
    return {
        "gercek_acik_satirlari": sorted(aciklar),
        "yanlis_alarm_satirlari": [],
        "kacirilan_satirlar": [],
        "yanlis_pozitif_orani": 0.0,
    }

print(kaynak_evye_triyaji(ornek_adaylar, kararlar))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-04")
```

```test
need("kaynak_evye_triyaji")

ADAYLAR = [
    {"satir_no": 10, "evye_adi": "system", "arguman_turu": "dinamik_girdi"},
    {"satir_no": 4, "evye_adi": "run", "arguman_turu": "sabit_deger"},
    {"satir_no": 7, "evye_adi": "eval", "arguman_turu": "sabit_deger"},
    {"satir_no": 15, "evye_adi": "execute", "arguman_turu": "dinamik_girdi"},
]

KARARLAR = {
    "4": "tehlikeli",
    "7": "guvenli",
    "10": "tehlikeli",
    "15": "guvenli",
}

def sozlesme(fn):
    try:
        r = fn(ADAYLAR, KARARLAR)
        if r != {
            "gercek_acik_satirlari": [10],
            "yanlis_alarm_satirlari": [4],
            "kacirilan_satirlar": [15],
            "yanlis_pozitif_orani": 0.5,
        }:
            return False

        r_uc = fn(ADAYLAR[:3], {"4": "tehlikeli", "7": "tehlikeli", "10": "tehlikeli"})
        if r_uc["yanlis_pozitif_orani"] != 0.6667:
            return False

        r_sifir_alarm = fn([ADAYLAR[1]], {"4": "guvenli"})
        if r_sifir_alarm["yanlis_pozitif_orani"] != 0.0:
            return False

        if fn([{"satir_no": 1, "evye_adi": "eval", "arguman_turu": "dinamik_girdi"}], {"1": "tehlikeli"})["gercek_acik_satirlari"] != [1]:
            return False

        a0 = ADAYLAR[0]
        hatalilar = [
            (None, KARARLAR),
            (tuple(ADAYLAR), KARARLAR),
            ([], KARARLAR),
            ("liste", KARARLAR),
            (["bozuk"], KARARLAR),
            ([{"satir_no": 1}], KARARLAR),
            ([a0, a0], {"10": "tehlikeli"}),
            ([dict(a0, satir_no=0)], {"0": "tehlikeli"}),
            ([dict(a0, satir_no=True)], {"True": "tehlikeli"}),
            ([dict(a0, satir_no="10")], {"10": "tehlikeli"}),
            ([dict(a0, evye_adi="print")], {"10": "tehlikeli"}),
            ([dict(a0, arguman_turu="bilinmeyen")], {"10": "tehlikeli"}),
            ([a0], None),
            ([a0], []),
            ([a0], {}),
            ([a0], {"10": "belirsiz"}),
        ]
        for a_in, k_in in hatalilar:
            try:
                fn(a_in, k_in)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(kaynak_evye_triyaji), "model triyaj kararları AST argüman türüyle doğru karşılaştırılmalı")
def m_fp_sifir(a, k):
    return dict(kaynak_evye_triyaji(a, k), yanlis_pozitif_orani=0.0)
def m_kacirilan_bos(a, k):
    return dict(kaynak_evye_triyaji(a, k), kacirilan_satirlar=[])
for ad, mutant in [("yanlış pozitif oranını sıfırlayan", m_fp_sifir), ("kaçırılan satırları gizleyen", m_kacirilan_bos)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
TEHLIKELI_EVYELER = ("eval", "exec", "system", "run", "Popen", "execute")

def kaynak_evye_triyaji(adaylar, model_kararlari):
    if not isinstance(adaylar, list) or not adaylar:
        raise ValueError("adaylar boş olamaz")
    if not isinstance(model_kararlari, dict):
        raise ValueError("model kararları sözlük olmalı")

    beklenen_a = {"satir_no", "evye_adi", "arguman_turu"}
    gorulen = set()
    gercek_acik_satirlari = []
    yanlis_alarm_satirlari = []
    kacirilan_satirlar = []

    for a in adaylar:
        if not isinstance(a, dict) or set(a.keys()) != beklenen_a:
            raise ValueError("aday şeması geçersiz")
        sno = a["satir_no"]
        if isinstance(sno, bool) or not isinstance(sno, int) or sno < 1 or sno in gorulen:
            raise ValueError("satır numarası geçersiz")
        gorulen.add(sno)
        if a["evye_adi"] not in TEHLIKELI_EVYELER:
            raise ValueError("evye adı geçersiz")
        atur = a["arguman_turu"]
        if atur not in ("sabit_deger", "dinamik_girdi"):
            raise ValueError("argüman türü geçersiz")
        anahtar = str(sno)
        if anahtar not in model_kararlari:
            raise ValueError("model kararı eksik")
        karar = model_kararlari[anahtar]
        if karar not in ("tehlikeli", "guvenli"):
            raise ValueError("model kararı geçersiz")

        if atur == "dinamik_girdi":
            if karar == "tehlikeli":
                gercek_acik_satirlari.append(sno)
            else:
                kacirilan_satirlar.append(sno)
        elif karar == "tehlikeli":
            yanlis_alarm_satirlari.append(sno)

    alarm_sayisi = len(gercek_acik_satirlari) + len(yanlis_alarm_satirlari)
    yanlis_pozitif_orani = round(len(yanlis_alarm_satirlari) / alarm_sayisi, 4) if alarm_sayisi else 0.0
    return {
        "gercek_acik_satirlari": sorted(gercek_acik_satirlari),
        "yanlis_alarm_satirlari": sorted(yanlis_alarm_satirlari),
        "kacirilan_satirlar": sorted(kacirilan_satirlar),
        "yanlis_pozitif_orani": yanlis_pozitif_orani,
    }
```

```hint
Paydayı hesaplarken yalnızca `karar == "tehlikeli"` verilen satırların toplamını (`len(gercek_acik_satirlari) + len(yanlis_alarm_satirlari)`) kullan.
```
:::

::: gorev 3 · Sabit çağrıları eleyen ve kaçırılan evyeleri yakalayan hibrit triyaj kapısı kur
`hibrit_triyaj_kapisi(kaynak_kodu, model_kararlari)` işlevini yaz.

Girdi kuralları:
- `kaynak_kodu`: 1. görevdeki kurallarla aynıdır; ayrıca kod içinde **en az bir** tehlikeli evye adayı bulunmalıdır (hiç aday yoksa `ValueError` yükselt).
- `model_kararlari`: 2. görevdeki kurallarla aynıdır.

Hibrit kapı kuralları:
1. `kaynak_kodu` içinden 1. görevdeki kurallarla AST evye adaylarını çıkar.
2. Adayları ve `model_kararlari` sözlüğünü 2. görevdeki kurallarla değerlendir.
3. `onaylanan_evye_satirlari`: AST üzerinde `"dinamik_girdi"` olan tüm evye satırları (`gercek_acik_satirlari` ile `kacirilan_satirlar` birleşimi, `sorted`).
4. `elenen_sabit_satirlar`: AST üzerinde `"sabit_deger"` olduğu için deterministik olarak elenen evye satırları (`sorted`).
5. `model_yanlis_pozitif_orani`: 2. görevde hesaplanan `yanlis_pozitif_orani`.
6. `hibrit_yanlis_pozitif_orani`: sabit çağrılar AST katmanında elendiği için `0.0`.

```starter
from ai_ile_guvenlik_veri import json_yukle, metin_yukle

kod = metin_yukle("ornek_servis.py")
kararlar = json_yukle("model_triyaj_kararlari.json")["model_kararlari"]

def hibrit_triyaj_kapisi(kaynak_kodu, model_kararlari):
    # HATA: AST sabit filtrelemesini uygulamıyor.
    return {
        "onaylanan_evye_satirlari": [],
        "elenen_sabit_satirlar": [],
        "model_yanlis_pozitif_orani": 0.0,
        "hibrit_yanlis_pozitif_orani": 0.0,
    }

print(hibrit_triyaj_kapisi(kod, kararlar))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-04")
```

```test
need("hibrit_triyaj_kapisi")

KOD = (
    "import os, subprocess\n"
    "def calistir(k, s):\n"
    "    subprocess.run('date')\n"
    "    os.system(k)\n"
    "    eval('2+2')\n"
    "    cursor.execute('SELECT ' + s)\n"
)

def sozlesme(fn):
    try:
        kararlar = {"3": "tehlikeli", "4": "tehlikeli", "5": "tehlikeli", "6": "guvenli"}
        r = fn(KOD, kararlar)
        if r != {
            "onaylanan_evye_satirlari": [4, 6],
            "elenen_sabit_satirlar": [3, 5],
            "model_yanlis_pozitif_orani": 0.6667,
            "hibrit_yanlis_pozitif_orani": 0.0,
        }:
            return False

        r_sifir = fn("os.system(x)", {"1": "guvenli"})
        if r_sifir != {
            "onaylanan_evye_satirlari": [1],
            "elenen_sabit_satirlar": [],
            "model_yanlis_pozitif_orani": 0.0,
            "hibrit_yanlis_pozitif_orani": 0.0,
        }:
            return False

        r_dinamik_guvenli = fn("eval('1')\nos.system(x)\nprint(x)\neval()\n(lambda a: a)(1)\nexec(x, 'sabit')", {"1": "tehlikeli", "2": "guvenli", "6": "tehlikeli"})
        if r_dinamik_guvenli != {
            "onaylanan_evye_satirlari": [2, 6],
            "elenen_sabit_satirlar": [1],
            "model_yanlis_pozitif_orani": 0.5,
            "hibrit_yanlis_pozitif_orani": 0.0,
        }:
            return False
        if fn("eval('1')\nos.system(x)", {"1": "guvenli", "2": "tehlikeli"})["model_yanlis_pozitif_orani"] != 0.0:
            return False
        if fn("eval('1')\nos.system(x)", {"1": "tehlikeli", "2": "tehlikeli"})["model_yanlis_pozitif_orani"] != 0.5:
            return False

        hatalilar = [
            (None, kararlar),
            (123, kararlar),
            ("", kararlar),
            ("   ", kararlar),
            ("def bozuk(:", kararlar),
            ("x = 1 + 2", {}),
            (KOD, None),
            (KOD, []),
            (KOD, {}),
            (KOD, {"3": "tehlikeli", "4": "tehlikeli", "5": "tehlikeli", "6": "yanlis"}),
        ]
        for k_in, m_in in hatalilar:
            try:
                fn(k_in, m_in)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(hibrit_triyaj_kapisi), "hibrit triyaj kapısı sabit çağrıları elemeli ve dinamik evyeleri eksiksiz onaylamalı")
def m_kacirani_eklemeyen(k, m):
    r = hibrit_triyaj_kapisi(k, m)
    return dict(r, onaylanan_evye_satirlari=[s for s in r["onaylanan_evye_satirlari"] if m.get(str(s)) == "tehlikeli"])
def m_sabit_elemeyen(k, m):
    return dict(hibrit_triyaj_kapisi(k, m), elenen_sabit_satirlar=[])
for ad, mutant in [("modelin kaçırdığı evyeyi onaylamayan", m_kacirani_eklemeyen), ("sabit çağrıları elemeyen", m_sabit_elemeyen)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
import ast

TEHLIKELI_EVYELER = ("eval", "exec", "system", "run", "Popen", "execute")

def _cagri_adi(func_node):
    if isinstance(func_node, ast.Name):
        return func_node.id
    if isinstance(func_node, ast.Attribute):
        return func_node.attr
    return None

def hibrit_triyaj_kapisi(kaynak_kodu, model_kararlari):
    if not isinstance(kaynak_kodu, str) or not kaynak_kodu.strip():
        raise ValueError("kaynak kodu boş olmayan string olmalı")
    if not isinstance(model_kararlari, dict):
        raise ValueError("model kararları sözlük olmalı")
    try:
        agac = ast.parse(kaynak_kodu)
    except SyntaxError as e:
        raise ValueError("geçersiz Python sözdizimi") from e

    adaylar = []
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.Call) and dugum.args:
            ad = _cagri_adi(dugum.func)
            if ad in TEHLIKELI_EVYELER:
                sabit_mi = isinstance(dugum.args[0], ast.Constant)
                adaylar.append({
                    "satir_no": dugum.lineno,
                    "arguman_turu": "sabit_deger" if sabit_mi else "dinamik_girdi",
                })
    if not adaylar:
        raise ValueError("en az bir evye adayı gerekli")

    onaylanan = []
    elenen = []
    dogru_alarm = 0
    yanlis_alarm = 0

    for a in adaylar:
        sno = a["satir_no"]
        anahtar = str(sno)
        if anahtar not in model_kararlari or model_kararlari[anahtar] not in ("tehlikeli", "guvenli"):
            raise ValueError("model kararı geçersiz veya eksik")
        karar = model_kararlari[anahtar]
        if a["arguman_turu"] == "dinamik_girdi":
            onaylanan.append(sno)
            if karar == "tehlikeli":
                dogru_alarm += 1
        else:
            elenen.append(sno)
            if karar == "tehlikeli":
                yanlis_alarm += 1

    toplam_alarm = dogru_alarm + yanlis_alarm
    fp_orani = round(yanlis_alarm / toplam_alarm, 4) if toplam_alarm else 0.0
    return {
        "onaylanan_evye_satirlari": sorted(onaylanan),
        "elenen_sabit_satirlar": sorted(elenen),
        "model_yanlis_pozitif_orani": fp_orani,
        "hibrit_yanlis_pozitif_orani": 0.0,
    }
```

```hint
AST üzerinde `"dinamik_girdi"` olan tüm satırları `onaylanan_evye_satirlari` listesine, `"sabit_deger"` olanları ise `elenen_sabit_satirlar` listesine ekle.
```
:::

::: gorev Gerçek deney · Python AST ön-elemesi ve yerel modelle source-to-sink triyajı
Önceki üç görevde yazdığın `ast_evye_adaylari_cikar`, `kaynak_evye_triyaji` ve `hibrit_triyaj_kapisi` işlevlerini bu adımda birleştir.

Canlı deneyde:
1. Sabit `subprocess.run`, sabit `eval` ve dinamik `os.system(kullanici_verisi)` içeren Python kodu `ast_evye_adaylari_cikar` ile ayrıştırılır.
2. Yerel Ollama modeli (`ai_lab.SohbetOturumu`) üzerinde kod analizi çalıştırılır.
3. `kaynak_evye_triyaji` ve `hibrit_triyaj_kapisi` ile sabit çağrıların elendiği ve gerçek dinamik evyenin onaylandığı doğrulanır.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def ast_evye_adaylari_cikar(kaynak_kodu):
    return []

def kaynak_evye_triyaji(adaylar, model_kararlari):
    return {}

def hibrit_triyaj_kapisi(kaynak_kodu, model_kararlari):
    return {}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_ile_guvenlik_04 as deney
    deney.goster(ast_evye_adaylari_cikar, kaynak_evye_triyaji, hibrit_triyaj_kapisi)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-04")
```

```test
import ai_lab
from sandbox import ai_gercek_ai_ile_guvenlik_04 as D

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for ad in ("ast_evye_adaylari_cikar", "kaynak_evye_triyaji", "hibrit_triyaj_kapisi"):
    need(ad)

sorun = ai_lab.kod_denetimi(
    src,
    ("ast_evye_adaylari_cikar_referans", "kaynak_evye_triyaji_referans", "hibrit_triyaj_kapisi_referans"),
)
ok(not sorun, "laboratuvar yamalanmamalı, referans işlevler çağrılmamalı")

KISA_KOD = "os.system(x)\neval('1')"
ok(ast_evye_adaylari_cikar(KISA_KOD) == D.ast_evye_adaylari_cikar_referans(KISA_KOD), "sentetik ön kontrol: AST evye çıkarma referansla uyumlu")

def _on_sozlesme():
    try:
        for h in (None, 123, "", "   ", "def bozuk(:"):
            try:
                ast_evye_adaylari_cikar(h)
                return False
            except ValueError:
                pass
        if ast_evye_adaylari_cikar("eval('1'); exec(x, 'sabit')\nprint(x)\neval()\n(lambda a: a)(1)") != [
            {"satir_no": 1, "evye_adi": "eval", "arguman_turu": "sabit_deger"},
            {"satir_no": 1, "evye_adi": "exec", "arguman_turu": "dinamik_girdi"},
        ]:
            return False
        a_uc = [
            {"satir_no": 1, "evye_adi": "run", "arguman_turu": "sabit_deger"},
            {"satir_no": 2, "evye_adi": "eval", "arguman_turu": "sabit_deger"},
            {"satir_no": 3, "evye_adi": "system", "arguman_turu": "dinamik_girdi"},
        ]
        if kaynak_evye_triyaji(a_uc, {"1": "tehlikeli", "2": "tehlikeli", "3": "tehlikeli"})["yanlis_pozitif_orani"] != 0.6667:
            return False
        if kaynak_evye_triyaji(a_uc, {"1": "tehlikeli", "2": "guvenli", "3": "guvenli"}) != {
            "gercek_acik_satirlari": [],
            "yanlis_alarm_satirlari": [1],
            "kacirilan_satirlar": [3],
            "yanlis_pozitif_orani": 1.0,
        }:
            return False
        if kaynak_evye_triyaji([a_uc[0]], {"1": "guvenli"})["yanlis_pozitif_orani"] != 0.0:
            return False
        for a_in, k_in in [
            (None, {"1": "tehlikeli"}),
            (tuple(a_uc), {"1": "tehlikeli", "2": "tehlikeli", "3": "tehlikeli"}),
            ([], {"1": "tehlikeli"}),
            ("x", {"1": "tehlikeli"}),
            (["x"], {"1": "tehlikeli"}),
            ([{"satir_no": 1}], {"1": "tehlikeli"}),
            ([dict(a_uc[0], satir_no=0)], {"0": "tehlikeli"}),
            ([dict(a_uc[0], satir_no=True)], {"True": "tehlikeli"}),
            ([dict(a_uc[0], satir_no="1")], {"1": "tehlikeli"}),
            ([dict(a_uc[0], evye_adi="print")], {"1": "tehlikeli"}),
            ([dict(a_uc[0], arguman_turu="bilinmeyen")], {"1": "tehlikeli"}),
            ([a_uc[0], a_uc[0]], {"1": "tehlikeli"}),
            ([a_uc[0]], None),
            ([a_uc[0]], []),
            ([a_uc[0]], {}),
            ([a_uc[0]], {"1": "belirsiz"}),
        ]:
            try:
                kaynak_evye_triyaji(a_in, k_in)
                return False
            except ValueError:
                pass
        if hibrit_triyaj_kapisi("subprocess.run('d')\nos.system(k)\neval('2')\ncursor.execute('S'+s)", {"1": "tehlikeli", "2": "tehlikeli", "3": "tehlikeli", "4": "guvenli"}) != {
            "onaylanan_evye_satirlari": [2, 4],
            "elenen_sabit_satirlar": [1, 3],
            "model_yanlis_pozitif_orani": 0.6667,
            "hibrit_yanlis_pozitif_orani": 0.0,
        }:
            return False
        try:
            hibrit_triyaj_kapisi("x = 1 + 2", {})
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
    r = D.deney(ast_evye_adaylari_cikar, kaynak_evye_triyaji, hibrit_triyaj_kapisi)
except Exception as e:
    ok(False, f"GERÇEK AST TRİYAJ DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

for ad, deger in r["kontroller"].items():
    ok(deger, "gerçek deney: " + ad)

ai_lab.kanit_yaz("ile-guvenlik-04-ast", {
    "kaynak": "gercek",
    "kabul": all(checks),
    "ders": "ai-ile-guvenlik-04",
    "ortam": r["ortam"],
    "ayarlar": r["ayarlar"],
    "deney": r,
    "ozet": r["ozet"],
})
o = r["ozet"]
ok(
    True,
    f"BULGU ({o['model']}): aday={o['aday_sayisi']}, onaylanan={o['onaylanan_satirlar']}, elenen_sabit={o['elenen_sabit_satirlar']}, model_fp={o['model_fp_orani']}.",
)
```

```solution
import ast
import ai_lab

TEHLIKELI_EVYELER = ("eval", "exec", "system", "run", "Popen", "execute")

def _cagri_adi(func_node):
    if isinstance(func_node, ast.Name):
        return func_node.id
    if isinstance(func_node, ast.Attribute):
        return func_node.attr
    return None

def ast_evye_adaylari_cikar(kaynak_kodu):
    if not isinstance(kaynak_kodu, str) or not kaynak_kodu.strip():
        raise ValueError("kaynak kodu boş olmayan string olmalı")
    try:
        agac = ast.parse(kaynak_kodu)
    except SyntaxError as e:
        raise ValueError("geçersiz Python sözdizimi") from e

    adaylar = []
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.Call) and dugum.args:
            ad = _cagri_adi(dugum.func)
            if ad in TEHLIKELI_EVYELER:
                ilk = dugum.args[0]
                sabit_mi = isinstance(ilk, ast.Constant)
                adaylar.append({
                    "satir_no": dugum.lineno,
                    "evye_adi": ad,
                    "arguman_turu": "sabit_deger" if sabit_mi else "dinamik_girdi",
                })
    adaylar.sort(key=lambda x: (x["satir_no"], x["evye_adi"]))
    return adaylar

def kaynak_evye_triyaji(adaylar, model_kararlari):
    if not isinstance(adaylar, list) or not adaylar:
        raise ValueError("adaylar boş olamaz")
    if not isinstance(model_kararlari, dict):
        raise ValueError("model kararları sözlük olmalı")

    beklenen_a = {"satir_no", "evye_adi", "arguman_turu"}
    gorulen = set()
    gercek_acik_satirlari = []
    yanlis_alarm_satirlari = []
    kacirilan_satirlar = []

    for a in adaylar:
        if not isinstance(a, dict) or set(a.keys()) != beklenen_a:
            raise ValueError("aday şeması geçersiz")
        sno = a["satir_no"]
        if isinstance(sno, bool) or not isinstance(sno, int) or sno < 1 or sno in gorulen:
            raise ValueError("satır numarası geçersiz")
        gorulen.add(sno)
        if a["evye_adi"] not in TEHLIKELI_EVYELER:
            raise ValueError("evye adı geçersiz")
        atur = a["arguman_turu"]
        if atur not in ("sabit_deger", "dinamik_girdi"):
            raise ValueError("argüman türü geçersiz")
        anahtar = str(sno)
        if anahtar not in model_kararlari:
            raise ValueError("model kararı eksik")
        karar = model_kararlari[anahtar]
        if karar not in ("tehlikeli", "guvenli"):
            raise ValueError("model kararı geçersiz")

        if atur == "dinamik_girdi":
            if karar == "tehlikeli":
                gercek_acik_satirlari.append(sno)
            else:
                kacirilan_satirlar.append(sno)
        elif karar == "tehlikeli":
            yanlis_alarm_satirlari.append(sno)

    alarm_sayisi = len(gercek_acik_satirlari) + len(yanlis_alarm_satirlari)
    yanlis_pozitif_orani = round(len(yanlis_alarm_satirlari) / alarm_sayisi, 4) if alarm_sayisi else 0.0
    return {
        "gercek_acik_satirlari": sorted(gercek_acik_satirlari),
        "yanlis_alarm_satirlari": sorted(yanlis_alarm_satirlari),
        "kacirilan_satirlar": sorted(kacirilan_satirlar),
        "yanlis_pozitif_orani": yanlis_pozitif_orani,
    }

def hibrit_triyaj_kapisi(kaynak_kodu, model_kararlari):
    adaylar = ast_evye_adaylari_cikar(kaynak_kodu)
    if not adaylar:
        raise ValueError("en az bir evye adayı gerekli")
    triyaj = kaynak_evye_triyaji(adaylar, model_kararlari)
    onaylanan = sorted(set(triyaj["gercek_acik_satirlari"]) | set(triyaj["kacirilan_satirlar"]))
    elenen = sorted(a["satir_no"] for a in adaylar if a["arguman_turu"] == "sabit_deger")
    return {
        "onaylanan_evye_satirlari": onaylanan,
        "elenen_sabit_satirlar": elenen,
        "model_yanlis_pozitif_orani": triyaj["yanlis_pozitif_orani"],
        "hibrit_yanlis_pozitif_orani": 0.0,
    }

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_ile_guvenlik_04 as deney
    deney.goster(ast_evye_adaylari_cikar, kaynak_evye_triyaji, hibrit_triyaj_kapisi)
```

```hint
Önceki üç görevdeki `ast_evye_adaylari_cikar`, `kaynak_evye_triyaji` ve `hibrit_triyaj_kapisi` çözümlerini birleştir.
```
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
AST önce çağrı ve ilk argümanın sözdizimini sınıflandırır; tam bir source-to-sink veri akışı çıkarmaz. Sabit argüman örneği dersin düşük-risk vekilidir, genel olarak güvenli program kanıtı değildir. Modelin alarm verdiği satırlar içindeki yanlışların payı FDR’dır; tüm negatifler içindeki FPR farklı payda kullanır. Hibrit sıfır oranı yalnız bu sentetik etiket kuralına göredir; gerçek vulnerability false positive değeri değildir.

Önkoşul ve yol köprüsü: ai-savunma-11 kod/araç sınırı.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| Dinamik argüman kesin açık, sabit argüman kesin güvenlidir | Sanitization, alias, veri akışı ve çağrı semantiği ayrıca gerekir |

Dinleyiciye sor: Bir model önerisini gerçek güvenlik kararı hâline getiren hangi uygulama denetimidir? Veri kökenini ve kalan sınırı koruyarak cevapla.
:::


::: anlat AST vekili gerçek data-flow kanıtı değildir
Bu dersin `gercek_acik_satirlari` alanı dinamik ilk argümanlı adayların eğitim etiketidir; doğrulanmış vulnerability listesi değildir. Sabit bir `eval`/`system` çağrısı da tehlikeli olabilir; dinamik fakat sanitize edilmiş bir sorgu güvenli olabilir. `hibrit_yanlis_pozitif_orani=0.0` yalnız bu açık fixture sözleşmesiyle hesaplanan vekil metriktir. Gerçek FPR/FDR için bağımsız etiketli vakalar ve source-to-sink incelemesi gerekir.
:::


::: anlat Ayrılma bağımlılığı
İlk anlatımdaki pu02 klasik yol karşılaştırması runtime bağımlılığı değildir. AI dışı yollar ayrılırken referans gözden geçirilmelidir; bu görevde klasik dosyalar değiştirilmez.
:::


### Birincil kaynak ve deneyin sınırı

[Python AST belgeleri](https://docs.python.org/3/library/ast.html). AST sözdizim ağacı sağlar; tek başına veri akışı veya istismar kanıtı sağlamaz.
