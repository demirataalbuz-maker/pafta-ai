---
id: ai-ile-guvenlik-05
title: "Kimlik Bilgisi ve Sır Sızıntısı Avında Bağlamsal Triyaj"
summary: Shannon entropisiyle düşük rastgelelikteki dizgeleri ele, aday sırları LLM istemine göndermeden önce maskele ve bağlamsal triyajla gerçek sırları test verisinden ayır.
timeout: 300
esleme: ai-savunma-15, ai-ile-guvenlik-01
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et
Kod tabanlarında unutulmuş API anahtarlarını ve parolaları ararken yalnız düzenli ifade (`regex`) veya karakter uzunluğu kullanmak, `EXAMPLE_ONLY_DO_NOT_USE_1234567890` gibi test sabitlerini veya `aaaaaaaaaaaa` gibi düşük entropili varsayılan değerleri de alarm olarak üretir. Öte yandan, şüpheli bir satırı **maskelemeden** doğrudan bir dil modeline göndermek, gerçek bir üretim sırrını model günlüklerine (`prompt logs`) sızdırmak demektir (`ai-savunma-15` dersindeki hassas veri sızıntısı önleme ilkesini hatırla). Güvenli tasarım; **Shannon entropisi ön-elemesi**, **zorunlu sır maskeleme** ve **bağlamsal LLM triyajını** birleştirir.

| Gerçek araç / model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Shannon bit entropisi hesabını, maskelenmiş bağlam satırlarını ve yerel Ollama modelinin (`qwen3`) bağlamsal sınıflandırmasını | İlk üç görevde `aday_sirlar.json` ve `model_sir_triyaji.json` içindeki **sentetik** sır adaylarını; son görevde canlı `ai_lab.SohbetOturumu` ile maskeli sır triyajı deneyini | Bir anahtarın yalnız metin bağlamına bakarak hedef serviste hâlâ aktif (`live/valid`) olup olmadığını doğrulayamaz |

> [!GÜVENLİK]
> **Kapsam ve dürüstlük sınırı:** İlk üç görevdeki anahtar ve parola dizgeleri **sentetik** eğitim verisidir; hiçbir gerçek servise ait değildir ve her çalıştırmada (`setup`) yeniden oluşturulur. Gerçek veya şüpheli sırlar LLM istemine girmeden önce mutlaka maskelenmelidir.
:::

::: anlat Entropi rastgeleliği ölçer, maskeleme ise sızıntıyı önler
Üç aşamalı güvenli sır triyaj hattı şöyle işler:

1. **Shannon Entropisi (`shannon_entropi`):** Bir dizgedeki karakter dağılımının bit cinsinden belirsizliğini ölçer:
   $$H(X) = -\sum_{c} p(c) \log_2 p(c)$$
   Tekrarlayan karakterlerden oluşan `"aaaaaaaaaaaa"` dizgesinin entropisi `0.0` iken, karmaşık bir API anahtarının entropisi genellikle `3.5` bitin üzerindedir.
2. **Sır Maskeleme (`maskeli_baglam_hazirla`):** Aday sır `deger` metni, bağlam satırı içinde `"***[MASKELENDI:{uzunluk}]***"` biçiminde maskelenir. Böylece model değişken adını, dosya yolunu ve yorum satırını görür ama ham sırrı asla görmez.
3. **Bağlamsal Triyaj (`baglamsal_sir_triyaji`):** Düşük entropili adaylar modele hiç sorulmadan elenir (`elenen_dusuk_entropi`). Kalan yüksek entropili adaylarda model kararı ve deterministik test bağlamı (`tests/`, `test_`, `dummy`, `fixture`) birlikte değerlendirilerek gerçek sırlar (`gercek_sir_kimlikleri`) ile test verileri (`elenen_test_kimlikleri`) ayrılır.
:::

::: anlat Bulguyu sınırlı ve doğrulanabilir yaz: istemde ham sır sızıntısı sıfır olmalıdır
Bir sır triyaj hattının başarısı yalnız doğru alarmları yakalamasıyla değil, model istemine gönderilen `maskeli_baglam` metinlerinin hiçbirinde ham `deger` dizgesinin yer almamasıyla (`sizinti_var_mi == False`) doğrulanır.
:::

::: tahmin Shannon entropisinin iki ve dört sembollü dizgelerdeki değerini tahmin et
Aşağıdaki Python kodunun çıktısını tahmin et:

```python
import math
from collections import Counter

def entropi(s):
    n = len(s)
    return round(-sum((c / n) * math.log2(c / n) for c in Counter(s).values()), 2)

print(entropi("abababab"), entropi("abcdabcd"))
```

???

```cikti
1.0 2.0
```

`"abababab"` içinde 2 karakter eşit olasılıkla (`1/2`) dağıldığı için entropi $\log_2(2) = 1.0$ bittir; `"abcdabcd"` içinde 4 karakter eşit olasılıkla (`1/4`) dağıldığı için entropi $\log_2(4) = 2.0$ bittir.
:::

::: gorev 1 · Karakter dağılımından Shannon entropisini hesapla
`shannon_entropi(dizge)` işlevini yaz.

Girdi kuralları:
- `dizge`: boş olmayan (`len(dizge) >= 1`) `str`. Boş dizge veya `str` dışı tipte `ValueError` yükselt.

Hesaplama kuralları:
- Her karakterin olasılığını `adet / len(dizge)` olarak hesapla.
- $-\sum p \log_2(p)$ toplamını `round(..., 4)` ile 4 ondalık basamağa yuvarlayarak `float` olarak döndür.

```starter
import math
from collections import Counter
from ai_ile_guvenlik_veri import json_yukle

adaylar = json_yukle("aday_sirlar.json")

def shannon_entropi(dizge):
    # HATA: Gerçek Shannon entropisi yerine farklı karakter oranını döndürüyor.
    return round(len(set(dizge)) / len(dizge), 4)

for a in adaylar:
    print(a["anahtar_adi"], shannon_entropi(a["deger"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-05")
```

```test
need("shannon_entropi")

def sozlesme(fn):
    try:
        if fn("aaaaaaaaaaaa") != 0.0:
            return False
        if fn("abababab") != 1.0:
            return False
        if fn("abcdabcd") != 2.0:
            return False
        if fn("aab") != 0.9183 or fn("aaab") != 0.8113:
            return False
        for h in (None, 123, "", [], {}):
            try:
                fn(h)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(shannon_entropi), "Shannon entropisi doğru hesaplanmalı ve geçersiz girdileri reddetmeli")
def m_sabit(s):
    return 1.0
def m_yuvarlamasiz(s):
    return round(shannon_entropi(s), 1)
for ad, mutant in [("sabit döndüren", m_sabit), ("yuvarlama hassasiyetini bozan", m_yuvarlamasiz)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
import math
from collections import Counter

def shannon_entropi(dizge):
    if not isinstance(dizge, str) or not dizge:
        raise ValueError("dizge boş olmayan string olmalı")
    uzunluk = len(dizge)
    sayim = Counter(dizge)
    entropi = -sum((adet / uzunluk) * math.log2(adet / uzunluk) for adet in sayim.values())
    return round(entropi, 4)
```

```hint
`Counter(dizge).values()` ile her karakterin frekansını alıp `math.log2` ile $-\sum p \log_2(p)$ formülünü uygula.
```
:::

::: gorev 2 · Aday sırrı modele göndermeden önce bağlam satırında maskele
`maskeli_baglam_hazirla(aday)` işlevini yaz.

Girdi kuralları:
- `aday`: tam olarak `{"dosya", "satir_no", "anahtar_adi", "deger", "baglam_satiri"}` anahtarlarına sahip `dict`.
- `dosya` ve `anahtar_adi`: boş olmayan (`strip()` sonrası dolu) `str`.
- `satir_no`: `bool` olmayan, `>= 1` `int`.
- `deger`: boş olmayan (`len(deger) >= 1`) `str`.
- `baglam_satiri`: içinde `deger` alt dizgesini barındıran `str`.
- Kurallara uymayan girdilerde `ValueError` yükselt.

Maskeleme kuralları:
- `maske = f"***[MASKELENDI:{len(deger)}]***"`
- `maskeli_baglam = baglam_satiri.replace(deger, maske)`
- Döndürülecek sözlük:
  - `"kimlik"`: `f"{dosya}:{satir_no}"`
  - `"dosya"`: `dosya`
  - `"satir_no"`: `satir_no`
  - `"anahtar_adi"`: `anahtar_adi`
  - `"entropi"`: `deger` dizgesinin 1. görevdeki kurallarla hesaplanan Shannon entropisi
  - `"maskeli_baglam"`: maskelenmiş bağlam satırı
  - `"ham_deger_sizdi_mi"`: `deger in maskeli_baglam` (`False` olmalı)

```starter
from ai_ile_guvenlik_veri import json_yukle

adaylar = json_yukle("aday_sirlar.json")

def maskeli_baglam_hazirla(aday):
    # HATA: Ham sırrı bağlam satırında maskelemeden bırakıyor!
    return {
        "kimlik": f"{aday['dosya']}:{aday['satir_no']}",
        "dosya": aday["dosya"],
        "satir_no": aday["satir_no"],
        "anahtar_adi": aday["anahtar_adi"],
        "entropi": 4.0,
        "maskeli_baglam": aday["baglam_satiri"],
        "ham_deger_sizdi_mi": True,
    }

print(maskeli_baglam_hazirla(adaylar[0]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-05")
```

```test
need("maskeli_baglam_hazirla")

ORNEK = {
    "dosya": "config/prod.env",
    "satir_no": 1,
    "anahtar_adi": "API_TOKEN",
    "deger": "aabbaabb",
    "baglam_satiri": "API_TOKEN=aabbaabb",
}

def sozlesme(fn):
    try:
        r = fn(ORNEK)
        if r != {
            "kimlik": "config/prod.env:1",
            "dosya": "config/prod.env",
            "satir_no": 1,
            "anahtar_adi": "API_TOKEN",
            "entropi": 1.0,
            "maskeli_baglam": "API_TOKEN=***[MASKELENDI:8]***",
            "ham_deger_sizdi_mi": False,
        }:
            return False

        if fn(dict(ORNEK, deger="aabbaabb", baglam_satiri="API_TOKEN=aabbaabb ve ***[MASKELENDI:8]***"))["ham_deger_sizdi_mi"] is not False:
            return False

        r_kesirli = fn(dict(ORNEK, deger="aaaaabbb", baglam_satiri="API_TOKEN=aaaaabbb"))
        if r_kesirli["entropi"] != 0.9544:
            return False
        if fn(dict(ORNEK, deger="aaaaaabbb", baglam_satiri="API_TOKEN=aaaaaabbb"))["entropi"] != 0.9183:
            return False

        hatalilar = [
            None,
            [],
            {},
            {"dosya": "a.py"},
            dict(ORNEK, dosya=""),
            dict(ORNEK, dosya="   "),
            dict(ORNEK, dosya=123),
            dict(ORNEK, satir_no=0),
            dict(ORNEK, satir_no=True),
            dict(ORNEK, satir_no="12"),
            dict(ORNEK, anahtar_adi=""),
            dict(ORNEK, anahtar_adi="  "),
            dict(ORNEK, anahtar_adi=None),
            dict(ORNEK, deger=""),
            dict(ORNEK, deger=12345678),
            dict(ORNEK, baglam_satiri="API_TOKEN=baska_deger"),
            dict(ORNEK, baglam_satiri=None),
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

ok(sozlesme(maskeli_baglam_hazirla), "aday sır bağlam satırında eksiksiz maskelenmeli ve entropisi hesaplanmalı")
def m_maskesiz(a):
    r = maskeli_baglam_hazirla(a)
    return dict(r, maskeli_baglam=a["baglam_satiri"])
def m_yanlis_entropi(a):
    return dict(maskeli_baglam_hazirla(a), entropi=0.0)
for ad, mutant in [("ham sırrı sızdıran", m_maskesiz), ("entropiyi sıfırlayan", m_yanlis_entropi)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
import math
from collections import Counter

def _entropi(dizge):
    uzunluk = len(dizge)
    sayim = Counter(dizge)
    deger = -sum((adet / uzunluk) * math.log2(adet / uzunluk) for adet in sayim.values())
    return round(deger, 4)

def maskeli_baglam_hazirla(aday):
    if not isinstance(aday, dict):
        raise ValueError("aday sözlük olmalı")
    beklenen = {"dosya", "satir_no", "anahtar_adi", "deger", "baglam_satiri"}
    if set(aday.keys()) != beklenen:
        raise ValueError("aday şeması geçersiz")

    dosya = aday["dosya"]
    satir_no = aday["satir_no"]
    anahtar_adi = aday["anahtar_adi"]
    deger = aday["deger"]
    baglam = aday["baglam_satiri"]

    if not isinstance(dosya, str) or not dosya.strip():
        raise ValueError("dosya geçersiz")
    if isinstance(satir_no, bool) or not isinstance(satir_no, int) or satir_no < 1:
        raise ValueError("satir_no geçersiz")
    if not isinstance(anahtar_adi, str) or not anahtar_adi.strip():
        raise ValueError("anahtar_adi geçersiz")
    if not isinstance(deger, str) or not deger:
        raise ValueError("deger boş olmayan string olmalı")
    if not isinstance(baglam, str) or deger not in baglam:
        raise ValueError("baglam_satiri ham degeri içermeli")

    maske = f"***[MASKELENDI:{len(deger)}]***"
    maskeli_satir = baglam.replace(deger, maske)
    return {
        "kimlik": f"{dosya}:{satir_no}",
        "dosya": dosya,
        "satir_no": satir_no,
        "anahtar_adi": anahtar_adi,
        "entropi": _entropi(deger),
        "maskeli_baglam": maskeli_satir,
        "ham_deger_sizdi_mi": deger in maskeli_satir,
    }
```

```hint
`baglam.replace(deger, maske)` ile ham sırrı maskele ve `deger in maskeli_satir` kontrolüyle sızıntı olmadığını doğrula.
```
:::

::: gorev 3 · Entropi ön-elemesi ve bağlamsal kurallarla sır triyajı yap
`baglamsal_sir_triyaji(adaylar, model_kararlari, min_entropi=3.5)` işlevini yaz.

Girdi kuralları:
- `adaylar`: boş olmayan `list`; her öğe 2. görevdeki aday şemasına uymalı ve `kimlik` (`dosya:satir_no`) benzersiz olmalıdır.
- `model_kararlari`: `dict`; `entropi >= min_entropi` olan her adayın `kimlik` anahtarı bu sözlükte bulunmalı ve değeri `"gercek_sir"` veya `"test_verisi"` olmalıdır.
- `min_entropi`: `bool` olmayan, `>= 0.5` `int` veya `float`.
- Kurallara uymayan girdilerde `ValueError` yükselt.

Triyaj kuralları:
1. Her adayı 2. görevdeki gibi maskele ve entropisini ölç:
   - `entropi < min_entropi` ise `elenen_dusuk_entropi` listesine `kimlik` ekle (modele gönderilmez).
   - `entropi >= min_entropi` ise maskelenmiş istem listesine dahil et.
2. Yüksek entropili adaylarda deterministik test bağlamı kontrolü yap:
   - Eğer `dosya.lower()` `"tests/"` ile başlıyorsa veya içinde `"test_"` geçiyorsa, ya da `anahtar_adi.lower()` içinde `"dummy"` geçiyorsa, ya da `maskeli_baglam.lower()` içinde `"fixture"` geçiyorsa aday kesin test verisidir (`kesin_test = True`).
   - `karar == "gercek_sir"` ve `not kesin_test` ise `gercek_sir_kimlikleri` listesine ekle; aksi hâlde `elenen_test_kimlikleri` listesine ekle.
3. Tüm kimlik listelerini `sorted` olarak, `maskeli_istem_sayisi` ve `sizinti_var_mi` alanlarıyla birlikte döndür.

```starter
from ai_ile_guvenlik_veri import json_yukle

adaylar = json_yukle("aday_sirlar.json")
kararlar = json_yukle("model_sir_triyaji.json")["model_kararlari"]

def baglamsal_sir_triyaji(adaylar, model_kararlari, min_entropi=3.5):
    # HATA: Entropi ön-elemesi ve test bağlamı kontrolü yapmıyor.
    return {
        "gercek_sir_kimlikleri": [],
        "elenen_test_kimlikleri": [],
        "elenen_dusuk_entropi": [],
        "maskeli_istem_sayisi": 0,
        "sizinti_var_mi": False,
    }

print(baglamsal_sir_triyaji(adaylar, kararlar))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-05")
```

```test
need("baglamsal_sir_triyaji")

ADAYLAR = [
    {
        "dosya": "config/prod.env",
        "satir_no": 1,
        "anahtar_adi": "API_TOKEN",
        "deger": "sk-8f92xK7mQ3pL9vR4wZ1nB6tY5cJ2hD0s",
        "baglam_satiri": "API_TOKEN=sk-8f92xK7mQ3pL9vR4wZ1nB6tY5cJ2hD0s",
    },
    {
        "dosya": "tests/test_auth.py",
        "satir_no": 44,
        "anahtar_adi": "API_KEY",
        "deger": "EXAMPLE_ONLY_DO_NOT_USE_1234567890",
        "baglam_satiri": "API_KEY = 'EXAMPLE_ONLY_DO_NOT_USE_1234567890'",
    },
    {
        "dosya": "app/settings.py",
        "satir_no": 8,
        "anahtar_adi": "DEFAULT_USER",
        "deger": "aaaaaaaaaaaa",
        "baglam_satiri": "DEFAULT_USER = 'aaaaaaaaaaaa'",
    },
]

KARARLAR = {
    "config/prod.env:1": "gercek_sir",
    "tests/test_auth.py:44": "gercek_sir",
}

def sozlesme(fn):
    try:
        r = fn(ADAYLAR, KARARLAR, 3.5)
        if r != {
            "gercek_sir_kimlikleri": ["config/prod.env:1"],
            "elenen_test_kimlikleri": ["tests/test_auth.py:44"],
            "elenen_dusuk_entropi": ["app/settings.py:8"],
            "maskeli_istem_sayisi": 2,
            "sizinti_var_mi": False,
        }:
            return False

        a_esik = {
            "dosya": "config/esik.env",
            "satir_no": 1,
            "anahtar_adi": "KEY",
            "deger": "abcdabcd",
            "baglam_satiri": "KEY=abcdabcd",
        }
        if fn([a_esik], {"config/esik.env:1": "gercek_sir"}, 2.0)["gercek_sir_kimlikleri"] != ["config/esik.env:1"]:
            return False

        a_kesir = {
            "dosya": "config/kesir.env",
            "satir_no": 1,
            "anahtar_adi": "KEY",
            "deger": "aaaaabbb",
            "baglam_satiri": "KEY=aaaaabbb",
        }
        if fn([a_kesir], {}, 0.95442)["elenen_dusuk_entropi"] != ["config/kesir.env:1"]:
            return False
        if fn([a_kesir], {"config/kesir.env:1": "gercek_sir"}, 0.9542)["gercek_sir_kimlikleri"] != ["config/kesir.env:1"]:
            return False
        a_tdir = dict(ADAYLAR[0], dosya="tests/yardimci.py")
        if fn([a_tdir], {"tests/yardimci.py:1": "gercek_sir"}, 3.5)["elenen_test_kimlikleri"] != ["tests/yardimci.py:1"]:
            return False
        a_dy = dict(ADAYLAR[0], dosya="config/d1.env", deger="0123456789abcdef", baglam_satiri="API_TOKEN=0123456789abcdef")
        a_dd = dict(ADAYLAR[0], dosya="config/d2.env", deger="abcdefabcdef", baglam_satiri="API_TOKEN=abcdefabcdef")
        r_def = fn([a_dy, a_dd], {"config/d1.env:1": "gercek_sir"})
        if r_def["gercek_sir_kimlikleri"] != ["config/d1.env:1"] or r_def["elenen_dusuk_entropi"] != ["config/d2.env:1"]:
            return False

        a_dokuz = {
            "dosya": "config/dokuz.env",
            "satir_no": 1,
            "anahtar_adi": "KEY",
            "deger": "aaaaaabbb",
            "baglam_satiri": "KEY=aaaaaabbb",
        }
        if fn([a_dokuz], {"config/dokuz.env:1": "gercek_sir"}, 0.5)["gercek_sir_kimlikleri"] != ["config/dokuz.env:1"]:
            return False

        a_sekiz_kisa = {
            "dosya": "config/sekiz.env",
            "satir_no": 1,
            "anahtar_adi": "KEY",
            "deger": "abcd1234",
            "baglam_satiri": "KEY=abcd1234",
        }
        if fn([a_sekiz_kisa], {"config/sekiz.env:1": "gercek_sir"}, 1.0)["gercek_sir_kimlikleri"] != ["config/sekiz.env:1"]:
            return False
        if fn([dict(a_sekiz_kisa, deger="abcd12345", baglam_satiri="KEY=abcd12345")], {"config/sekiz.env:1": "gercek_sir"}, 1.0)["gercek_sir_kimlikleri"] != ["config/sekiz.env:1"]:
            return False

        a_sizinti = {
            "dosya": "config/s.env",
            "satir_no": 1,
            "anahtar_adi": "KEY",
            "deger": "abcd123456",
            "baglam_satiri": "KEY=abcd123456 ve ***[MASKELENDI:10]***",
        }
        if fn([a_sizinti], {"config/s.env:1": "gercek_sir"}, 1.0)["sizinti_var_mi"] is not False:
            return False

        r_model_test = fn([ADAYLAR[0]], {"config/prod.env:1": "test_verisi"}, 3.5)
        if r_model_test["elenen_test_kimlikleri"] != ["config/prod.env:1"]:
            return False

        a_dummy = dict(ADAYLAR[0], dosya="app/cfg.py", anahtar_adi="DUMMY_KEY")
        if fn([a_dummy], {"app/cfg.py:1": "gercek_sir"}, 3.5)["elenen_test_kimlikleri"] != ["app/cfg.py:1"]:
            return False

        a_fixture = dict(ADAYLAR[0], dosya="app/cfg.py", baglam_satiri="# fixture: API_TOKEN=sk-8f92xK7mQ3pL9vR4wZ1nB6tY5cJ2hD0s")
        if fn([a_fixture], {"app/cfg.py:1": "gercek_sir"}, 3.5)["elenen_test_kimlikleri"] != ["app/cfg.py:1"]:
            return False

        a_test_dosya = dict(ADAYLAR[0], dosya="src/test_helper.py")
        if fn([a_test_dosya], {"src/test_helper.py:1": "gercek_sir"}, 3.5)["elenen_test_kimlikleri"] != ["src/test_helper.py:1"]:
            return False

        hatalilar = [
            (None, KARARLAR, 3.5),
            (123, KARARLAR, 3.5),
            ([], KARARLAR, 3.5),
            ([dict(ADAYLAR[2], satir_no=0)], {}, 3.5),
            ([dict(ADAYLAR[2], satir_no=-1)], {}, 3.5),
            ([dict(ADAYLAR[2], satir_no=True)], {}, 3.5),
            (["bozuk"], KARARLAR, 3.5),
            ([{"dosya": "a.py"}], KARARLAR, 3.5),
            ([dict(ADAYLAR[0], dosya="")], KARARLAR, 3.5),
            ([dict(ADAYLAR[0], dosya=123)], KARARLAR, 3.5),
            ([dict(ADAYLAR[0], satir_no=0)], KARARLAR, 3.5),
            ([dict(ADAYLAR[0], satir_no=True)], KARARLAR, 3.5),
            ([dict(ADAYLAR[0], satir_no="1")], KARARLAR, 3.5),
            ([dict(ADAYLAR[0], anahtar_adi="")], KARARLAR, 3.5),
            ([dict(ADAYLAR[0], anahtar_adi=None)], KARARLAR, 3.5),
            ([dict(ADAYLAR[0], deger="")], KARARLAR, 3.5),
            ([dict(ADAYLAR[0], deger=12345678)], KARARLAR, 3.5),
            ([dict(ADAYLAR[0], baglam_satiri="yok")], KARARLAR, 3.5),
            ([dict(ADAYLAR[0], baglam_satiri=None)], KARARLAR, 3.5),
            ([ADAYLAR[0], ADAYLAR[0]], KARARLAR, 3.5),
            (ADAYLAR, None, 3.5),
            (ADAYLAR, {}, 3.5),
            (ADAYLAR, {"config/prod.env:1": "belirsiz", "tests/test_auth.py:44": "test_verisi"}, 3.5),
            (ADAYLAR, KARARLAR, float("nan")),
            (ADAYLAR, KARARLAR, float("inf")),
            (ADAYLAR, KARARLAR, 0.4),
            (ADAYLAR, KARARLAR, 0),
            (ADAYLAR, KARARLAR, -1.0),
            (ADAYLAR, KARARLAR, True),
            (ADAYLAR, KARARLAR, "3.5"),
        ]
        for a_in, k_in, e_in in hatalilar:
            try:
                fn(a_in, k_in, e_in)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(baglamsal_sir_triyaji), "bağlamsal sır triyajı düşük entropiyi ve test verilerini doğru elemeli")
def m_testi_kaciran(a, k, e=3.5):
    r = baglamsal_sir_triyaji(a, k, e)
    return dict(r, gercek_sir_kimlikleri=sorted(r["gercek_sir_kimlikleri"] + r["elenen_test_kimlikleri"]), elenen_test_kimlikleri=[])
def m_entropi_elemeyen(a, k, e=3.5):
    return dict(baglamsal_sir_triyaji(a, k, e), elenen_dusuk_entropi=[])
for ad, mutant in [("test verisini gerçek sır sayan", m_testi_kaciran), ("düşük entropiyi elemeyen", m_entropi_elemeyen)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

for alan in ('dosya','anahtar_adi'):
    raises(ValueError,baglamsal_sir_triyaji,[dict(ADAYLAR[0],**{alan:'   '})],{},99,msg='whitespace aday alanı')
```

```solution
import math
from collections import Counter

def _entropi(dizge):
    uzunluk = len(dizge)
    sayim = Counter(dizge)
    deger = -sum((adet / uzunluk) * math.log2(adet / uzunluk) for adet in sayim.values())
    return round(deger, 4)

def _maskele(aday):
    if not isinstance(aday, dict):
        raise ValueError("aday sözlük olmalı")
    beklenen = {"dosya", "satir_no", "anahtar_adi", "deger", "baglam_satiri"}
    if set(aday.keys()) != beklenen:
        raise ValueError("aday şeması geçersiz")
    dosya = aday["dosya"]
    satir_no = aday["satir_no"]
    anahtar_adi = aday["anahtar_adi"]
    deger = aday["deger"]
    baglam = aday["baglam_satiri"]
    if not isinstance(dosya, str) or not dosya.strip():
        raise ValueError("dosya geçersiz")
    if isinstance(satir_no, bool) or not isinstance(satir_no, int) or satir_no < 1:
        raise ValueError("satir_no geçersiz")
    if not isinstance(anahtar_adi, str) or not anahtar_adi.strip():
        raise ValueError("anahtar_adi geçersiz")
    if not isinstance(deger, str) or not deger:
        raise ValueError("deger boş olmayan string olmalı")
    if not isinstance(baglam, str) or deger not in baglam:
        raise ValueError("baglam_satiri ham degeri içermeli")
    maske = f"***[MASKELENDI:{len(deger)}]***"
    maskeli_satir = baglam.replace(deger, maske)
    return {
        "kimlik": f"{dosya}:{satir_no}",
        "dosya": dosya,
        "anahtar_adi": anahtar_adi,
        "entropi": _entropi(deger),
        "maskeli_baglam": maskeli_satir,
        "ham_deger_sizdi_mi": deger in maskeli_satir,
    }

def baglamsal_sir_triyaji(adaylar, model_kararlari, min_entropi=3.5):
    if not isinstance(adaylar, list) or not adaylar:
        raise ValueError("adaylar boş olamaz")
    if not isinstance(model_kararlari, dict):
        raise ValueError("model_kararlari sözlük olmalı")
    if isinstance(min_entropi, bool) or not isinstance(min_entropi, (int, float)) or not math.isfinite(min_entropi) or min_entropi < 0.5:
        raise ValueError("min_entropi en az 0.5 olmalı")

    gorulen = set()
    elenen_dusuk_entropi = []
    gercek_sir_kimlikleri = []
    elenen_test_kimlikleri = []
    maskeli_istem_listesi = []

    for aday in adaylar:
        m = _maskele(aday)
        kimlik = m["kimlik"]
        if kimlik in gorulen:
            raise ValueError("tekrarlanan aday kimliği")
        gorulen.add(kimlik)

        if m["entropi"] < float(min_entropi):
            elenen_dusuk_entropi.append(kimlik)
            continue

        maskeli_istem_listesi.append(m)
        if kimlik not in model_kararlari:
            raise ValueError("yüksek entropili aday için model kararı eksik")
        karar = model_kararlari[kimlik]
        if karar not in ("gercek_sir", "test_verisi"):
            raise ValueError("model kararı geçersiz")

        dosya_kucuk = m["dosya"].lower()
        baglam_kucuk = m["maskeli_baglam"].lower()
        kesin_test = (
            dosya_kucuk.startswith("tests/")
            or "test_" in dosya_kucuk
            or "dummy" in m["anahtar_adi"].lower()
            or "fixture" in baglam_kucuk
        )

        if karar == "gercek_sir" and not kesin_test:
            gercek_sir_kimlikleri.append(kimlik)
        else:
            elenen_test_kimlikleri.append(kimlik)

    return {
        "gercek_sir_kimlikleri": sorted(gercek_sir_kimlikleri),
        "elenen_test_kimlikleri": sorted(elenen_test_kimlikleri),
        "elenen_dusuk_entropi": sorted(elenen_dusuk_entropi),
        "maskeli_istem_sayisi": len(maskeli_istem_listesi),
        "sizinti_var_mi": any(x["ham_deger_sizdi_mi"] for x in maskeli_istem_listesi),
    }
```

```hint
Önce `m["entropi"] < float(min_entropi)` olanları `elenen_dusuk_entropi` listesine ayır; kalan adaylarda hem model kararını hem de test dosya/anahtar/bağlam göstergelerini kontrol et.
```
:::

::: gorev Gerçek deney · Maskelenmiş sır adaylarıyla yerel model üzerinde bağlamsal triyaj
Önceki üç görevde yazdığın `shannon_entropi`, `maskeli_baglam_hazirla` ve `baglamsal_sir_triyaji` işlevlerini bu adımda birleştir.

Canlı deneyde:
1. Düşük entropili varsayılan değerler `shannon_entropi` ile elenir.
2. Yüksek entropili adaylar `maskeli_baglam_hazirla` ile maskelenerek yerel Ollama modeline (`ai_lab.SohbetOturumu`) gönderilir; model isteminde ham sırların bulunmadığı doğrulanır.
3. `baglamsal_sir_triyaji` ile test sabitleri elenir ve üretim sırları raporlanır.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def shannon_entropi(dizge):
    return 0.0

def maskeli_baglam_hazirla(aday):
    return {}

def baglamsal_sir_triyaji(adaylar, model_kararlari, min_entropi=3.5):
    return {}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_ile_guvenlik_05 as deney
    deney.goster(shannon_entropi, maskeli_baglam_hazirla, baglamsal_sir_triyaji)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-05")
```

```test
import ai_lab
from sandbox import ai_gercek_ai_ile_guvenlik_05 as D

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for ad in ("shannon_entropi", "maskeli_baglam_hazirla", "baglamsal_sir_triyaji"):
    need(ad)

sorun = ai_lab.kod_denetimi(
    src,
    ("shannon_entropi_referans", "maskeli_baglam_hazirla_referans", "baglamsal_sir_triyaji_referans"),
)
ok(not sorun, "laboratuvar yamalanmamalı, referans işlevler çağrılmamalı")

ok(shannon_entropi("aab") == 0.9183 and shannon_entropi("aaab") == 0.8113, "sentetik ön kontrol: Shannon entropisi doğru")

def _on_sozlesme():
    try:
        for h in ("", None, 123):
            try:
                shannon_entropi(h)
                return False
            except ValueError:
                pass
        ornek = {
            "dosya": "config/prod.env",
            "satir_no": 1,
            "anahtar_adi": "API_TOKEN",
            "deger": "aabbaabb",
            "baglam_satiri": "API_TOKEN=aabbaabb",
        }
        if maskeli_baglam_hazirla(ornek)["maskeli_baglam"] != "API_TOKEN=***[MASKELENDI:8]***":
            return False
        if maskeli_baglam_hazirla(dict(ornek, deger="1234567890", baglam_satiri="API_TOKEN=1234567890 ve ***[MASKELENDI:10]***"))["ham_deger_sizdi_mi"] is not False:
            return False
        if baglamsal_sir_triyaji([ornek], {"config/prod.env:1": "gercek_sir"}, 1.0)["gercek_sir_kimlikleri"] != ["config/prod.env:1"]:
            return False
        if baglamsal_sir_triyaji([ornek], {"config/prod.env:1": "gercek_sir"}, 0.5)["gercek_sir_kimlikleri"] != ["config/prod.env:1"]:
            return False
        if baglamsal_sir_triyaji([dict(ornek, deger="aaaaabbb", baglam_satiri="API_TOKEN=aaaaabbb")], {}, 0.95442)["elenen_dusuk_entropi"] != ["config/prod.env:1"]:
            return False
        if baglamsal_sir_triyaji([dict(ornek, anahtar_adi="DUMMY_KEY")], {"config/prod.env:1": "gercek_sir"}, 1.0)["elenen_test_kimlikleri"] != ["config/prod.env:1"]:
            return False
        if baglamsal_sir_triyaji([dict(ornek, baglam_satiri="# fixture API_TOKEN=aabbaabb")], {"config/prod.env:1": "gercek_sir"}, 1.0)["elenen_test_kimlikleri"] != ["config/prod.env:1"]:
            return False
        if baglamsal_sir_triyaji([dict(ornek, dosya="src/test_x.py")], {"src/test_x.py:1": "gercek_sir"}, 1.0)["elenen_test_kimlikleri"] != ["src/test_x.py:1"]:
            return False
        if baglamsal_sir_triyaji([dict(ornek, dosya="tests/yardimci.py")], {"tests/yardimci.py:1": "gercek_sir"}, 1.0)["elenen_test_kimlikleri"] != ["tests/yardimci.py:1"]:
            return False
        if baglamsal_sir_triyaji([ornek], {"config/prod.env:1": "test_verisi"}, 1.0)["elenen_test_kimlikleri"] != ["config/prod.env:1"]:
            return False
        a_dy = dict(ornek, dosya="config/d1.env", deger="0123456789abcdef", baglam_satiri="API_TOKEN=0123456789abcdef")
        a_dd = dict(ornek, dosya="config/d2.env", deger="abcdefabcdef", baglam_satiri="API_TOKEN=abcdefabcdef")
        r_def = baglamsal_sir_triyaji([a_dy, a_dd], {"config/d1.env:1": "gercek_sir"})
        if r_def["gercek_sir_kimlikleri"] != ["config/d1.env:1"] or r_def["elenen_dusuk_entropi"] != ["config/d2.env:1"]:
            return False
        for bozuk in (
            None,
            {},
            dict(ornek, dosya=""),
            dict(ornek, dosya=123),
            dict(ornek, satir_no=0),
            dict(ornek, satir_no=True),
            dict(ornek, satir_no="1"),
            dict(ornek, anahtar_adi=""),
            dict(ornek, anahtar_adi=None),
            dict(ornek, deger=""),
            dict(ornek, deger=12345678, baglam_satiri="API_TOKEN=aabbaabb"),
            dict(ornek, baglam_satiri="yok"),
            dict(ornek, baglam_satiri=None),
        ):
            try:
                maskeli_baglam_hazirla(bozuk)
                return False
            except ValueError:
                pass
        for a_in, k_in, e_in in [
            (None, {}, 1.0),
            (123, {}, 1.0),
            ([], {}, 1.0),
            ([ornek, ornek], {"config/prod.env:1": "gercek_sir"}, 1.0),
            ([ornek], None, 1.0),
            ([ornek], {}, 1.0),
            ([ornek], {"config/prod.env:1": "yanlis"}, 1.0),
            ([ornek], {"config/prod.env:1": "gercek_sir"}, float("nan")),
            ([ornek], {"config/prod.env:1": "gercek_sir"}, float("inf")),
            ([ornek], {"config/prod.env:1": "gercek_sir"}, 0.4),
            ([ornek], {"config/prod.env:1": "gercek_sir"}, 0),
            ([ornek], {"config/prod.env:1": "gercek_sir"}, True),
            ([ornek], {"config/prod.env:1": "gercek_sir"}, "1.0"),
        ]:
            try:
                baglamsal_sir_triyaji(a_in, k_in, e_in)
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
    r = D.deney(shannon_entropi, maskeli_baglam_hazirla, baglamsal_sir_triyaji)
except Exception as e:
    ok(False, f"GERÇEK SIR TRİYAJI DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

for ad, deger in r["kontroller"].items():
    ok(deger, "gerçek deney: " + ad)

ai_lab.kanit_yaz("ile-guvenlik-05-sir", {
    "kaynak": "gercek",
    "kabul": all(checks),
    "ders": "ai-ile-guvenlik-05",
    "ortam": r["ortam"],
    "ayarlar": r["ayarlar"],
    "deney": r,
    "ozet": r["ozet"],
})
o = r["ozet"]
ok(
    True,
    f"BULGU ({o['model']}): gercek_sirlar={o['gercek_sirlar']}, elenen_test={o['elenen_test']}, elenen_dusuk_entropi={o['elenen_dusuk_entropi']}, sizinti={o['sizinti_var_mi']}.",
)
```

```solution
import math
from collections import Counter
import ai_lab

def shannon_entropi(dizge):
    if not isinstance(dizge, str) or not dizge:
        raise ValueError("dizge boş olmayan string olmalı")
    uzunluk = len(dizge)
    sayim = Counter(dizge)
    entropi = -sum((adet / uzunluk) * math.log2(adet / uzunluk) for adet in sayim.values())
    return round(entropi, 4)

def maskeli_baglam_hazirla(aday):
    if not isinstance(aday, dict):
        raise ValueError("aday sözlük olmalı")
    beklenen = {"dosya", "satir_no", "anahtar_adi", "deger", "baglam_satiri"}
    if set(aday.keys()) != beklenen:
        raise ValueError("aday şeması geçersiz")
    dosya = aday["dosya"]
    satir_no = aday["satir_no"]
    anahtar_adi = aday["anahtar_adi"]
    deger = aday["deger"]
    baglam = aday["baglam_satiri"]
    if not isinstance(dosya, str) or not dosya.strip():
        raise ValueError("dosya geçersiz")
    if isinstance(satir_no, bool) or not isinstance(satir_no, int) or satir_no < 1:
        raise ValueError("satir_no geçersiz")
    if not isinstance(anahtar_adi, str) or not anahtar_adi.strip():
        raise ValueError("anahtar_adi geçersiz")
    if not isinstance(deger, str) or not deger:
        raise ValueError("deger boş olmayan string olmalı")
    if not isinstance(baglam, str) or deger not in baglam:
        raise ValueError("baglam_satiri ham degeri içermeli")

    maske = f"***[MASKELENDI:{len(deger)}]***"
    maskeli_satir = baglam.replace(deger, maske)
    return {
        "kimlik": f"{dosya}:{satir_no}",
        "dosya": dosya,
        "satir_no": satir_no,
        "anahtar_adi": anahtar_adi,
        "entropi": shannon_entropi(deger),
        "maskeli_baglam": maskeli_satir,
        "ham_deger_sizdi_mi": deger in maskeli_satir,
    }

def baglamsal_sir_triyaji(adaylar, model_kararlari, min_entropi=3.5):
    if not isinstance(adaylar, list) or not adaylar:
        raise ValueError("adaylar boş olamaz")
    if not isinstance(model_kararlari, dict):
        raise ValueError("model_kararlari sözlük olmalı")
    if isinstance(min_entropi, bool) or not isinstance(min_entropi, (int, float)) or not math.isfinite(min_entropi) or min_entropi < 0.5:
        raise ValueError("min_entropi en az 0.5 olmalı")

    gorulen = set()
    elenen_dusuk_entropi = []
    gercek_sir_kimlikleri = []
    elenen_test_kimlikleri = []
    maskeli_istem_listesi = []

    for aday in adaylar:
        m = maskeli_baglam_hazirla(aday)
        kimlik = m["kimlik"]
        if kimlik in gorulen:
            raise ValueError("tekrarlanan aday kimliği")
        gorulen.add(kimlik)

        if m["entropi"] < float(min_entropi):
            elenen_dusuk_entropi.append(kimlik)
            continue

        maskeli_istem_listesi.append(m)
        if kimlik not in model_kararlari:
            raise ValueError("yüksek entropili aday için model kararı eksik")
        karar = model_kararlari[kimlik]
        if karar not in ("gercek_sir", "test_verisi"):
            raise ValueError("model kararı geçersiz")

        dosya_kucuk = m["dosya"].lower()
        baglam_kucuk = m["maskeli_baglam"].lower()
        kesin_test = (
            dosya_kucuk.startswith("tests/")
            or "test_" in dosya_kucuk
            or "dummy" in m["anahtar_adi"].lower()
            or "fixture" in baglam_kucuk
        )

        if karar == "gercek_sir" and not kesin_test:
            gercek_sir_kimlikleri.append(kimlik)
        else:
            elenen_test_kimlikleri.append(kimlik)

    return {
        "gercek_sir_kimlikleri": sorted(gercek_sir_kimlikleri),
        "elenen_test_kimlikleri": sorted(elenen_test_kimlikleri),
        "elenen_dusuk_entropi": sorted(elenen_dusuk_entropi),
        "maskeli_istem_sayisi": len(maskeli_istem_listesi),
        "sizinti_var_mi": any(x["ham_deger_sizdi_mi"] for x in maskeli_istem_listesi),
    }

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_ile_guvenlik_05 as deney
    deney.goster(shannon_entropi, maskeli_baglam_hazirla, baglamsal_sir_triyaji)
```

```hint
Önceki üç görevdeki `shannon_entropi`, `maskeli_baglam_hazirla` ve `baglamsal_sir_triyaji` işlevlerini birleştir.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Entropi sır olduğunun ispatı değildir

Shannon entropisi karakter dağılımının belirsizliğini ölçer. Rastgele görünen test kimliği yüksek, gerçek ama düzenli parola düşük entropili olabilir. Adayı modele göndermeden bağlam satırında maskelemek gerçek değer sızıntısını azaltır. Son triyaj biçim, çevre ve yerel kuralları birlikte inceler; modelin emin görünmesi sır deposu doğrulaması değildir.

| Yaygın yanlış | Kontrolün gösterdiği |
|---|---|
| Yüksek entropi kesin secrettır | Entropi ön elemedir; bağlam ve güvenli işleme gerekir. |

Sonraki bağlantı: ai-savunma-15. [Birincil kaynak](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html). Kaynak ilgili araç veya yöntemi açıklar; labın gerçek sonucu ham kanıt kaydındadır.
:::
