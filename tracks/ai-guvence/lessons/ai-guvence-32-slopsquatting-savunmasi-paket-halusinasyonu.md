---
id: ai-guvence-32
title: "Slopsquatting Savunması: Paket Halüsinasyonu"
summary: Modelin önerdiği paketleri çıkar, typosquat'ı Levenshtein ile yakala, allow-list ile doğrula; halüsine paketin körü körüne kurulmasını gerçek modelde engelle.
esleme: ai-guvence-21, ai-guvence-25, ai-uretim-10
timeout: 45
---

::: anlat Slopsquatting: modelin uydurduğu paket adı, saldırganın tuzağı olur
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Kod asistanları paket adları önerir; paket kayıt sistemleri dağıtım adı, sürüm ve kaynak bilgisi sağlar | İlk üç görevde `veri/paket_onerisi.txt` ve `veri/denetim.json` içindeki elle yazılmış sentetik örnekler; son görevde mevcut yerel Ollama modelinin canlı önerileri | Allow-list dışında olmak paketin hayalî veya zararlı olduğunu kanıtlamaz. Bu deney PyPI sorgulamaz, paket indirmez/kurmaz ve tam bir pip gereksinim ayrıştırıcısı değildir |

> [!NOT]
> İlk üç görevin dosyaları **sentetiktir**; canlı yanıt kaydı değildir. **Çalıştır** kodu aynı dosyaları okuyup sonuçları gösterir. Ham dosyayı koddan okuyup değiştirebilirsin; çalışma klasörü geçicidir, sonraki çalıştırmada örnek yeniden kopyalanır ve değişiklikler kalıcı değildir. Gizli testler bu örneklerden ayrıdır. Son **Gerçek deney** yerel modele canlı çağrı yapar ve gerçek yanıtları kaydeder; listede olmayan öneri insan incelemesine ayrılır.

Bir kod asistanına "bu görev için hangi paketleri kurayım" diye sorduğunda, model olasılıkçıdır ve bazen **var olmayan** bir paket adı uydurur (halüsinasyon). Saldırgan bu uydurma adları önceden tahmin edip PyPI/npm'e **kendi zararlı paketini** o adla kaydeder; model aynı adı tekrar önerdiğinde, otomatik kuran bir coding-agent doğrudan saldırganın kodunu `pip install` eder. Bu desene **slopsquatting** denir (LLM "slop" + typosquatting; Lanyado, 2024) ve klasik typosquatting'in (`reqeusts` gibi popüler bir ada bir harf yakın sahte paket) LLM çağındaki akrabasıdır. Tehlike, kurulumun **otomatik** ve adın **gerçekçi görünmesinden** gelir.

Savunma, modelin önerisine güvenmemek ve kurulumu bir **doğrulama kapısından** geçirmektir. Üç katman: önce modelin çıktısından paket adlarını **çıkar** (`pip install …`, `import …`); sonra her adı çok bilinen paketlere **Levenshtein uzaklığıyla** karşılaştır — ada çok yakın ama eşit olmayan bir ad typosquat şüphesidir; en önemlisi, her paketi önceden onaylı bir **allow-list** ile doğrula. Allow-list'te olmayan hiçbir paket körü körüne kurulmaz; gerçek-ama-yeni, yazım hatası ya da halüsinasyon olabilir, hepsi insan incelemesine gider. Böylece model bir paket adı uydursa bile zincir orada durur.
:::

::: anlat Savunma deterministiktir: allow-list modelin kararını beklemez
Bu savunmanın gücü, çoğunun **modelin davranışından bağımsız** çalışmasıdır. Allow-list bir küme üyeliği sorusudur: önerilen paket önceden onaylı mı, değil mi — model ne kadar ikna edici yazarsa yazsın cevap değişmez. Levenshtein uzaklığı iki ad arasındaki düzenleme sayısıdır; `1 ≤ uzaklık ≤ eşik` olan bir ad, bilinen bir paketin yazım-hatası/typosquat kuzeni olabilir, sıfır uzaklık ise adın gerçek paketin **kendisi** olduğunu söyler (şüphe değil). Paket çıkarımı da metin işlemesidir: sürüm belirteçleri (`==1.2`), ekstralar (`[async]`) ve bayraklar (`-U`) ayıklanır, adlar küçük harfe indirilir.

Bu derste önce bu üç adımı saf Python'la kurarsın. `veri/paket_onerisi.txt` ham öneriyi, `veri/denetim.json` onaylı adları ve sınanacak yazım hatasını içerir. Koddan `print(open("veri/paket_onerisi.txt", encoding="utf-8").read())` ile ham biçimi görebilirsin. İstersen aynı çalıştırmada kopyaya satır ekleyip çıktıyı karşılaştır; sonraki çalıştırma örneği yeniden hazırlar. Bu dersin basit çıkarıcısı import adı ile dağıtım adı arasındaki eşlemeyi çözmez (`bs4`/`beautifulsoup4` gibi); URL, gereksinim dosyası ve seçenek argümanları için üretim kurulum kapısı değildir. Son görevdeki denetim ise **canlı gerçek deneydir**: gerçek yerel modele bir kodlama görevi için paket önerisi sordurulur, önerilenler çıkarılıp allow-list ile doğrulanır ve kaç paketin incelemeye gittiği ölçülür — listede olmayan öneriler ölçülür; bunların varlığı veya zararlılığı bu deneyle karara bağlanmaz.
:::

::: tahmin Levenshtein, allow-list ve çıkarım çıktısını tahmin et
Üç çıktı satırını yaz:

```python
def lev(a, b):
    o = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        s = [i]
        for j, cb in enumerate(b, 1):
            s.append(min(o[j] + 1, s[j - 1] + 1, o[j - 1] + (ca != cb)))
        o = s
    return o[-1]
print(lev("reqeusts", "requests"), lev("requests", "requests"))
guvenilir = {"requests", "numpy", "flask"}
print([p for p in ["requests", "bilmiyorum", "csv"] if p not in guvenilir])
print("pip install numpy==1.26.0".split("pip install")[1].split()[0].split("==")[0].strip())
```

???

```cikti
2 0
['bilmiyorum', 'csv']
numpy
```

İlk satır Levenshtein uzaklığıdır: `reqeusts` → `requests` iki düzenleme (typosquat şüphesi), aynı adın kendine uzaklığı 0 (şüphe yok). İkinci satır allow-list denetimi: `bilmiyorum` (halüsinasyon) ve `csv` (aslında stdlib, pip paketi değil) güvenilir listede yok, incelemeye gider; `requests` geçer. Üçüncü satır paket çıkarımı: `pip install` sonrası ilk ad alınır, `==1.26.0` sürüm belirteci atılır.
:::

::: gorev 1 · Model çıktısından paket adlarını çıkar
`paket_ayikla(metin)` işlevini yaz. `metin` stringdir (değilse `ValueError`). Her satırda: satır `pip install` içeriyorsa, o ifadeden sonrasını boşlukla böl; `-` ile başlayan bayrakları atla; her belirteçten ekstraları (`[...]` ve sonrası) ve sürüm belirtecini (`<`, `>`, `=`, `!`, `~` ve sonrası) at, küçük harfe indir; baştaki/sondaki boşluk ve basit alıntı/noktalama işaretlerini temizle; sonuç `[a-z0-9][a-z0-9._-]*` kalıbına uyuyorsa paket say. Satır `pip install` içermiyor ama `import X` ya da `from X import` ile başlıyorsa `X`'i (küçük harf) paket say. Bulunan paket adlarını **alfabetik ve yinelenmesiz** liste döndür.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-32")
```

```starter
from ai_guvence_veri import metin_yukle

def paket_ayikla(metin):
    # KUSURLU BAŞLANGIÇ KODU: sürüm/ekstra/bayrak temizliği ve import satırları eksik.
    return sorted(set(tok for satir in metin.splitlines() if satir.startswith("pip install ") for tok in satir.split()[2:]))

ham = metin_yukle("veri/paket_onerisi.txt")
print("Sentetik ham öneri:\n" + ham)
print("Çıkan paketler:", paket_ayikla(ham))
```

```test
def sozlesme(fn):
    try:
        m = "pip install requests numpy==1.26.0\npip install flask[async] -U\nimport pandas\nfrom bs4 import BeautifulSoup\npip install scikit-learn"
        if fn(m) != ["bs4", "flask", "numpy", "pandas", "requests", "scikit-learn"]:
            return False
        if fn("pip install Django httpx>=0.27") != ["django", "httpx"]:
            return False
        if fn("hiç paket yok") != [] or fn("pip install requests\npip install requests") != ["requests"]:
            return False
        for kotu in [None, 5, b"x", ["pip install requests"]]:
            try:
                fn(kotu)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(paket_ayikla), "pip install + import çıkarımı, sürüm/ekstra/bayrak temizliği doğru")
import re
SUR = re.compile(r"[<>=!~].*$")
def _ay(metin, imports=True, surum=True, kucuk=True):
    pk = set()
    for ham in metin.splitlines():
        s = ham.strip(); d = s.lower()
        if "pip install" in d:
            for tok in s[d.index("pip install") + 11:].split():
                if tok.startswith("-"):
                    continue
                ad = tok.split("[")[0]
                if surum:
                    ad = SUR.sub("", ad)
                ad = ad.strip(" `'\"().,")
                if kucuk:
                    ad = ad.lower()
                if re.fullmatch(r"[a-z0-9][a-z0-9._-]*", ad.lower()):
                    pk.add(ad)
        elif imports:
            mo = re.match(r"(?:from|import)\s+([a-zA-Z0-9_]+)", s)
            if mo:
                pk.add(mo.group(1).lower() if kucuk else mo.group(1))
    return sorted(pk)
for ad, mut in [("import satırlarını atlayan", lambda m: _ay(m, imports=False)),
                ("sürüm belirtecini temizlemeyen", lambda m: _ay(m, surum=False)),
                ("küçük harfe indirmeyen", lambda m: _ay(m, kucuk=False))]:
    ok(not sozlesme(mut), "yanlış çözüm/mutant yakalanmalı: " + ad)
# Sessiz yanlış ayrıştırma yerine sınırdaki sözdizimini de denetle.
eq(paket_ayikla("  PIP INSTALL -U 'a1==2' z9[cli] a_b a.b a-b\nimport Z9\nfrom A1 import x"),["a-b","a.b","a1","a_b","z9"],"noktalama, harf/rakam ve yineleme")
eq(paket_ayikla("pip install -q @bad /x https://ornek.invalid/a\nimport json.tool\nfrom pathlib import Path"),["json","pathlib"],"geçersiz paket belirteçleri ve kök import")
eq(paket_ayikla(""),[],"boş metin")
```

```solution
from ai_guvence_veri import json_yukle, metin_yukle
import re

def paket_ayikla(metin):
    if not isinstance(metin, str):
        raise ValueError("metin string olmalı")
    surum = re.compile(r"[<>=!~].*$")
    paketler = set()
    for ham in metin.splitlines():
        s = ham.strip()
        d = s.lower()
        if "pip install" in d:
            for tok in s[d.index("pip install") + len("pip install"):].split():
                if tok.startswith("-"):
                    continue
                ad = surum.sub("", tok.split("[")[0]).strip(" `'\"().,").lower()
                if re.fullmatch(r"[a-z0-9][a-z0-9._-]*", ad):
                    paketler.add(ad)
        else:
            m = re.match(r"(?:from|import)\s+([a-zA-Z0-9_]+)", s)
            if m:
                paketler.add(m.group(1).lower())
    return sorted(paketler)

if __name__ == "__main__":
    ham = metin_yukle("veri/paket_onerisi.txt")
    print("Sentetik ham öneri:\n" + ham)
    print("Çıkan paketler:", paket_ayikla(ham))
```

```hint
Her satırda önce `pip install` geçip geçmediğine bak; geçiyorsa sonrasını boşlukla böl, bayrakları (`-`) atla, her belirteçten `[...]` ve sürüm son ekini temizle, küçült. Geçmiyorsa `import`/`from` ile modül adını al. Kümeyle yinelenmeyi önle, sonunda `sorted` döndür.
```
:::

::: gorev 2 · Typosquat'ı Levenshtein uzaklığıyla yakala
`benzer_typosquat(paket, populer, esik)` işlevini yaz. `paket` boş olmayan stringdir. `populer` 1–1000 öğeli, boş olmayan, yinelenmeyen string listesidir (çok bilinen paket adları). `esik` bool olmayan ≥1 tamsayıdır. Geçersiz veride `ValueError` yükselt.

`populer` içindeki her `p` için `paket` ile `p` arasındaki Levenshtein düzenleme uzaklığını hesapla. `1 ≤ uzaklık ≤ esik` olan `p`'leri topla (tam eşleşme — uzaklık 0 — typosquat değildir, dışarıda bırak) ve **alfabetik** liste döndür.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-32")
```

```starter
from ai_guvence_veri import json_yukle

def benzer_typosquat(paket, populer, esik):
    # KUSURLU BAŞLANGIÇ KODU: düzenleme uzaklığı yerine yalnız ad uzunluğunu karşılaştırıyor.
    return sorted(p for p in populer if abs(len(paket)-len(p)) <= esik)

v = json_yukle("veri/denetim.json")
print("Sentetik denetim:", v)
print("Yakın adlar:", benzer_typosquat(v["supheli"],v["populer"],v["esik"]))
```

```test
def sozlesme(fn):
    try:
        if fn("reqeusts", ["requests", "numpy", "pandas"], 2) != ["requests"]:
            return False
        if fn("requests", ["requests", "numpy"], 2) != [] or fn("numpyy", ["numpy", "numba"], 1) != ["numpy"]:
            return False
        if sorted(fn("panda", ["pandas", "panda3d", "numpy"], 1)) != ["pandas"]:
            return False
        if fn("xyz", ["requests", "numpy"], 2) != []:
            return False
        for kotu in [(None, ["a"], 1), ("", ["a"], 1), ("a", None, 1), ("a", [], 1), ("a", ["a", "a"], 1), ("a", ["", "b"], 1),
                     ("a", "b", 1), ("a", ["b"], 0), ("a", ["b"], True), ("a", ["b"], 1.0)]:
            try:
                fn(*kotu)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(benzer_typosquat), "Levenshtein typosquat eşiği ve tam eşleşmenin dışlanması doğru")
def lev(a, b):
    o = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        s = [i]
        for j, cb in enumerate(b, 1):
            s.append(min(o[j] + 1, s[j - 1] + 1, o[j - 1] + (ca != cb)))
        o = s
    return o[-1]
def m_tam(p, pop, e):
    return sorted(x for x in pop if lev(p, x) <= e)  # tam eşleşmeyi (0) de alır
def m_esik(p, pop, e):
    return sorted(x for x in pop if lev(p, x) >= 1)  # eşiği yok sayar
for ad, mut in [("tam eşleşmeyi de sayan", m_tam), ("eşiği yok sayan", m_esik)]:
    ok(not sozlesme(mut), "yanlış çözüm/mutant yakalanmalı: " + ad)
eq(benzer_typosquat("ab",["b"],1),["b"],"tek aday geçerli ve baştaki silme maliyeti bir")
eq(benzer_typosquat("a",["a","ab","b","cde"],1),["ab","b"],"sıfır dışarıda, eşik dahil ve alfabetik")
eq(benzer_typosquat("x",["p"+str(i) for i in range(1000)],1),[],"bin popüler ad üst sınır dahil")
for args in [("a",["p"+str(i) for i in range(1001)],1),("a",[2],1),("a",[True],1),(7,["b"],1),("a",["b"],-1)]:
    try:
        benzer_typosquat(*args)
        ok(False,"geçersiz ad/sınır reddedilmeli")
    except ValueError:
        ok(True,"geçersiz ad/sınır reddedildi")
```

```solution
from ai_guvence_veri import json_yukle, metin_yukle
def benzer_typosquat(paket, populer, esik):
    if not isinstance(paket, str) or not paket:
        raise ValueError("paket boş olmayan string olmalı")
    if not isinstance(populer, list) or not 1 <= len(populer) <= 1000 \
            or any(not isinstance(x, str) or not x for x in populer) or len(set(populer)) != len(populer):
        raise ValueError("populer yinelenmeyen, boş olmayan string listesi olmalı")
    if isinstance(esik, bool) or not isinstance(esik, int) or esik < 1:
        raise ValueError("esik pozitif tamsayı olmalı")
    def lev(a, b):
        onceki = [j for j, _ in enumerate(b)] + [len(b)]
        for i, ca in enumerate(a, 1):
            simdi = [i]
            for j, cb in enumerate(b, 1):
                simdi.append(min(onceki[j] + 1, simdi[j - 1] + 1, onceki[j - 1] + (ca != cb)))
            onceki = simdi
        return onceki[-1]
    return sorted(p for p in populer if 1 <= lev(paket, p) <= esik)

if __name__ == "__main__":
    v = json_yukle("veri/denetim.json")
    print("Sentetik denetim:", v)
    print("Yakın adlar:", benzer_typosquat(v["supheli"],v["populer"],v["esik"]))
```

```hint
Levenshtein uzaklığı iki satırlık bir dinamik programlamadır: her karakter için ekleme, silme ve değiştirme maliyetlerinin en küçüğünü al. `1 ≤ uzaklık ≤ esik` koşulu hem tam eşleşmeyi (0, gerçek paketin kendisi) hem de çok uzak adları eler.
```
:::

::: gorev 3 · Allow-list ile doğrula
`allowlist_dogrula(paketler, guvenilir)` işlevini yaz. `paketler` 0–1000 öğeli, boş olmayan string listesidir (önerilen paketler). `guvenilir` 0–10000 öğeli, boş olmayan string listesidir (önceden onaylı paketler). Geçersiz veride `ValueError` yükselt.

`{"izin": guvenilir'de olan paketler, "incele": guvenilir'de OLMAYAN paketler}` döndür; her liste **alfabetik ve yinelenmesiz** olsun.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-32")
```

```starter
from ai_guvence_veri import json_yukle

def allowlist_dogrula(paketler, guvenilir):
    # KUSURLU BAŞLANGIÇ KODU: güvenilir olmayanları da otomatik izin listesine alıyor.
    return {"izin": sorted(set(paketler)), "incele": []}

v = json_yukle("veri/denetim.json")
print("Sentetik denetim:",v)
print("Kapı sonucu:",allowlist_dogrula(v["paketler"],v["guvenilir"]))
```

```test
def sozlesme(fn):
    try:
        g = ["requests", "numpy", "flask"]
        if fn(["requests", "bilmiyorum", "csv", "numpy"], g) != {"izin": ["numpy", "requests"], "incele": ["bilmiyorum", "csv"]}:
            return False
        if fn([], g) != {"izin": [], "incele": []} or fn(["flask", "flask"], g) != {"izin": ["flask"], "incele": []}:
            return False
        if fn(["x"], []) != {"izin": [], "incele": ["x"]}:
            return False
        for kotu in [(None, g), ("x", g), ([1], g), ([""], g), (["a"], None), (["a"], [1]), (["a"], [""])]:
            try:
                fn(*kotu)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(allowlist_dogrula), "allow-list ayrımı (izin/incele) doğru; geçersiz girdi reddedilmeli")
def m_hepsi(p, g):
    return {"izin": sorted(set(p)), "incele": []}  # hepsini güvenli sayar
def m_ters(p, g):
    gs = set(g)
    return {"izin": sorted({x for x in p if x not in gs}), "incele": sorted({x for x in p if x in gs})}
for ad, mut in [("hepsini güvenli sayan", m_hepsi), ("izin/inceleyi ters çeviren", m_ters)]:
    ok(not sozlesme(mut), "yanlış çözüm/mutant yakalanmalı: " + ad)
eq(allowlist_dogrula(["x"]*1000,["x"]*10000),{"izin":["x"],"incele":[]},"üst sınırlar dahil, yineleme temizliği")
eq(allowlist_dogrula([],[]),{"izin":[],"incele":[]},"iki boş liste geçerli")
eq(allowlist_dogrula(["B","a","B","x"],["a","B"]),{"izin":["B","a"],"incele":["x"]},"eşleme harfe duyarlı, sıralı, yinelenmesiz")
for args in [(["x"]*1001,["x"]),(["x"],["x"]*10001),(["x"],"x"),([True],["x"]),(["x"],[{}])]:
    try:
        allowlist_dogrula(*args)
        ok(False,"kapı sınırı/türü reddedilmeli")
    except ValueError:
        ok(True,"kapı sınırı/türü reddedildi")
```

```solution
from ai_guvence_veri import json_yukle, metin_yukle
def allowlist_dogrula(paketler, guvenilir):
    if not isinstance(paketler, list) or len(paketler) > 1000 or any(not isinstance(x, str) or not x for x in paketler):
        raise ValueError("paketler boş olmayan stringlerden oluşmalı")
    if not isinstance(guvenilir, list) or len(guvenilir) > 10000 or any(not isinstance(x, str) or not x for x in guvenilir):
        raise ValueError("guvenilir boş olmayan stringlerden oluşmalı")
    gset = set(guvenilir)
    return {"izin": sorted({p for p in paketler if p in gset}),
            "incele": sorted({p for p in paketler if p not in gset})}

if __name__ == "__main__":
    v = json_yukle("veri/denetim.json")
    print("Sentetik denetim:",v)
    print("Kapı sonucu:",allowlist_dogrula(v["paketler"],v["guvenilir"]))
```

```hint
İki kümeye ayır: güvenilir listede olanlar `izin`, olmayanlar `incele`. İkisini de `sorted(set(...))` ile alfabetik ve yinelenmesiz döndür. Allow-list mantığı "kanıtlanana kadar güvenme"dir: listede yoksa — gerçek bile olsa — incelemeye gider.
```
:::

::: anlat Gerçek modelde slopsquatting denetimi
Bu deneyde gerçek yerel modele üç kodlama görevi için gereken pip paketleri sorulur ("her paketi ayrı satırda `pip install <ad>` yaz"). Senin `paket_denetle` işlevin modelin yanıtından paket adlarını çıkarır ve güvenilir allow-list ile doğrular: listede olanlar otomatik onaya, olmayanlar incelemeye gider. Deney, önerilen paketleri ve kaçının incelemeye gittiğini ölçer — model gerçekten var olmayan bir ad (halüsinasyon) ya da `csv` gibi pip paketi olmayan bir ad önerdiğinde allow-list bunu yakalar, körü körüne kurulmaz. Dış paket kaydına ağ çağrısı yoktur; yerel Ollama HTTP bağlantısı kullanılır, hiçbir paket kurulmaz; model bu deney tarafından yüklendiyse sonunda boşaltılır.

Kaynaklar: [Spracklen vd. 2024 — We Have a Package for You! A Comprehensive Analysis of Package Hallucinations by Code Generating LLMs (arXiv:2406.10279)](https://arxiv.org/abs/2406.10279), [OWASP Top 10 for LLM Applications — LLM03 Supply Chain](https://genai.owasp.org/llmrisk/llm032025-supply-chain/).
:::

::: gorev Gerçek deney · Önerilen paketleri çıkar ve allow-list ile denetle
`paket_denetle(metin, guvenilir)` işlevini yaz.

- `metin` string (model yanıtı), `guvenilir` boş olmayan stringlerden oluşan 0–10000 öğeli liste. Geçersiz veride `ValueError`.
- `metin`'den paket adlarını çıkar (görev 1'deki `pip install` + `import`/`from` kuralı; sürüm/ekstra/bayrak temizliği; küçük harf; alfabetik, yinelenmesiz). Çıkan paketleri allow-list ile ayır (görev 3). `{"paketler": çıkan tüm paketler, "izin": güvenilirde olanlar, "incele": olmayanlar}` döndür; her liste alfabetik, yinelenmesiz.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import re
import ai_lab

def paket_denetle(metin, guvenilir):
    return {"paketler": [], "izin": [], "incele": []}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_32 as deney
    deney.goster(paket_denetle)
```

```test
import ai_lab
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
import ast
YASAK=("referans", "referans_denetle", "_ayikla", "kanit_yaz", "getattr")
sorun=ai_lab.kod_denetimi(src,YASAK)
for node in ast.walk(ast.parse(src)):
    if isinstance(node,ast.ImportFrom) and any(a.name in YASAK or a.name=="*" for a in node.names):
        sorun.append("referans import edilemez")
kontrol(not sorun,"Kendi paket denetimini yaz; laboratuvar yamalanmamalı: "+", ".join(sorun))
if sorun:
    stop()
fn = need("paket_denetle")
from sandbox import ai_gercek_ai_guvence_32 as D
G = ["requests", "numpy", "flask", "pandas"]
metinler = ["pip install requests numpy==1.0\npip install bilmiyorum\nimport pandas",
            "pip install flask\npip install csv\nfrom lxml import etree", "hiç paket yok"]
def sozlesme(f):
    try:
        for m in metinler + ["  PIP INSTALL -U 'Requests[socks]>=2.0' `NumPy` -q @bad\n  Import Pandas\n  from Flask import app"]:
            if f(m, list(G)) != D.referans_denetle(m, list(G)):
                return False
        if f("pip install a0", [f"a{i}" for i in range(10000)])["izin"] != ["a0"]:
            return False
        for kotu in [(None, G), (5, G), ("x", None), ("x", [1]), ("x", [""]), ("x", ["a"] * 10001)]:
            try:
                f(*kotu)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(fn), "paket çıkarımı + allow-list denetimi doğru; geçersiz girdi reddedilmeli")
kontrol(not sozlesme(lambda m, g: D.referans_denetle(m, g, dogrula=False)), "hatalı çözüm reddedilmeli: allow-list doğrulamayı atlayan")
r, oz = None, None
if all(sonuclar):
    try:
        r = D.deney(fn)
    except ai_lab.GercekLabYok as e:
        kontrol(False, f"GERÇEK MODEL YOK, deney yapılmadı: {e}")
        stop()
    g = [k for k in r["kayitlar"] if k.get("hata") is None]
    kontrol(len(g) == len(r["kayitlar"]) == len(D.GOREVLER), f"bütün model çağrıları hatasız tamamlanmalı ({len(g)}/{len(r['kayitlar'])} görev hatasız)")
    kontrol(all(set(k["incele"]) == (set(k["paketler"]) - set(D.GUVENILIR)) for k in g), "allow-list ayrımı gerçek yanıtlarda tutarlı")
    kontrol(all({a:k[a] for a in ("paketler","izin","incele")} == D.referans_denetle(k["yanit"],list(D.GUVENILIR)) for k in g), "gerçek ham yanıtın bütün listeleri bağımsız denetimle aynı")
    oz = D.ozet(r)
    kontrol(oz["benzersiz_paket"] > 0, f"model {oz['benzersiz_paket']} benzersiz paket önerdi")
yol = ai_lab.kanit_yaz("guvence-slopsquat", {"kaynak": "gercek", "kabul": all(sonuclar), "ders": "ai-guvence-32",
                                             "ortam": (r or {}).get("ortam"), "ozet": oz, "deney": r})
if oz:
    ok(True, f"BULGU ({r['ortam']['model']['ad']}): {oz['benzersiz_paket']} benzersiz paket önerildi; {oz['izinli']} allow-list'te, "
             f"{oz['incelenecek']} İNCELE gerekli (slopsquatting riski): {oz['incele_ornegi']}. Allow-list dışı hiçbir paket körü körüne kurulmaz.")
```

```solution
import re
import ai_lab

def paket_denetle(metin, guvenilir):
    if not isinstance(metin, str):
        raise ValueError("metin string olmalı")
    if not isinstance(guvenilir, list) or len(guvenilir) > 10000 or any(not isinstance(x, str) or not x for x in guvenilir):
        raise ValueError("guvenilir boş olmayan stringlerden oluşmalı")
    surum = re.compile(r"[<>=!~].*$")
    paketler = set()
    for ham in metin.splitlines():
        s = ham.strip()
        d = s.lower()
        if "pip install" in d:
            for tok in s[d.index("pip install") + len("pip install"):].split():
                if tok.startswith("-"):
                    continue
                ad = surum.sub("", tok.split("[")[0]).strip(" `'\"().,").lower()
                if re.fullmatch(r"[a-z0-9][a-z0-9._-]*", ad):
                    paketler.add(ad)
        else:
            m = re.match(r"(?:from|import)\s+([a-zA-Z0-9_]+)", s)
            if m:
                paketler.add(m.group(1).lower())
    gset = set(guvenilir)
    return {"paketler": sorted(paketler), "izin": sorted(p for p in paketler if p in gset),
            "incele": sorted(p for p in paketler if p not in gset)}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_32 as deney
    deney.goster(paket_denetle)
```

```hint
Paket çıkarımı görev 1, allow-list ayrımı görev 3'tür; bu görev ikisini birleştirir. Çıkan her paketi güvenilir kümeyle karşılaştır: listede yoksa `incele`'ye koy. Model bir ad uydursa bile (`bilmiyorum`) ya da `csv` gibi pip paketi olmayan bir ad verse de, allow-list'te olmadığı için incelemeye düşer ve kurulmaz.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **`Slopsquatting` saldırı zinciri (35 sn).** "Kod üreten modeller bazen gerçekte var olmayan ama kulağa makul gelen paket adları uydurur ve aynı halüsinasyonu farklı kullanıcılarda tekrarlar; saldırgan bu boş paket adını açık kayıt defterinde tescilleyip zararlı kod yüklediğinde geliştirici veya ajan kendi eliyle tuzağı kurar."
2. **Komut ayrıştırma + `allow-list` kapısı (30 sn).** "Otomatik kod çalıştırma hattı `pip install` ve `import` satırlarından bayrakları, sürüm kısıtlarını ve `extras` köşeli parantezlerini soyup paket adını çıkarır; kurumsal izin listesinde (`allow-list`) olmayan her ad kurulum yerine `incele` kuyruğuna düşer."
3. **Yazım yakınlığı (`Levenshtein`) uyarısı (30 sn).** "`reqeusts` gibi popüler pakete 1–2 düzenleme uzaklığındaki adlar hem insan yazım hatası hem `typosquatting` için ek yüksek risk sinyali üretir."
4. **Soru (25 sn).** "Bir paketin PyPI'da gerçekten var olması ve binlerce kez indirilmiş görünmesi tek başına güvenli olduğunu neden kanıtlamaz?"
:::
