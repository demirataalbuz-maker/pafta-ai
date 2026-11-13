---
id: ai-saldiri-41
title: "Slopsquatting Saldırısı: Paket Halüsinasyonu Hasadı ve Kayıt Yüzeyi Analizi"
summary: Farklı istem ve tohumlarda modelin tekrarlayarak uydurduğu paket adlarını topla, yerel sentetik dizinde sahipsiz adların ele geçirilme riskini ölç ve otomatik kurulum zincirini gerçek modelle analiz et.
timeout: 300
esleme: ai-guvence-32, ai-savunma-20
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et
Kodlama ajanları ve geliştirici asistanları bir görevi çözerken `pip install <paket>` veya `npm install <paket>` önerdiğinde, bazen gerçekte var olmayan ama kulağa son derece mantıklı gelen paket adları uydurur. Saldırganın modelin **tekrarlayarak uydurduğu** bu sahipsiz adları tespit edip paket deposuna kaydettirmesiyle oluşan tedarik zinciri saldırısına **Slopsquatting** denir.

| Gerçek araç / model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Kodlama ajanlarının (`pip install`, `poetry add`, `requirements.txt`) ürettiği ham önerileri, çoklu tohum (`seed`) örnekleme dağılımını ve paket dizini sahiplik durumlarını | İlk üç görevde `slop/*.json` altındaki **sentetik** model önerisi, yerel dizin ve ajan kurulum izlerini; son görevde `ai_lab.SohbetOturumu` ile yerel Ollama modelinde canlı halüsinasyon hasadını | Yerel sentetik dizinde `"sahipsiz"` görünen bir adın gerçek PyPI/npm üzerinde boş olduğunu veya canlı modelin tek bir niş istemdeki halüsinasyon oranının tüm dillere genellenebileceğini söyleyemez |

> [!GÜVENLİK]
> **Kapsam ve dürüstlük sınırı:** Slopsquatting araştırmalarında **gerçek paket depolarına (PyPI, npm, crates.io vb.) hiçbir koşulda sahte veya test paketi yüklenmez**; tüm sahiplik ve kayıt yüzeyi analizleri yalnızca **yerel/sentetik dizin** üzerinde yürütülür. İlk üç görevdeki `slop/model_onerileri.json`, `slop/yerel_paket_dizini.json` ve `slop/ajan_kurulum_izleri.json` dosyaları **sentetik** eğitim verisidir ve her çalıştırmada (`setup`) yeniden kopyalanır (kalıcılık yoktur).
:::

::: anlat Rastgele halüsinasyon değil, tohumlar arası tekrarlayan halüsinasyon silahlaşır
Saldırı perspektifinden her paket halüsinasyonu eşit değerde değildir:

1. **Tekrarlanabilirlik (Repeatability Harvesting):** Modelin yüksek sıcaklıkta bir kez uydurup bir daha asla önermediği bir paket adı (`tek-seferlik-uydurma`), başka bir geliştiricinin veya ajanın karşısına çıkmayacağı için saldırgan açısından değersizdir. Saldırgan, ön-eğitim verisindeki token birlikteliklerinden (`fastapi` + `jwt` + `guard` → `fastapi-jwt-guard`) doğan ve farklı istem/tohumlarda (`toplam_gecis >= 2`) tekrar tekrar önerilen **kalıcı halüsinasyonları** hasat eder.
2. **Yerel dizin kayıt yüzeyi:** Önerilen ad resmi bir paketse (`"resmi"`) veya depo tarafından kara listeye/rezerveye alınmışsa (`"rezerve-yasakli"`), saldırgan bu adı kaydedemez (`kayit_acik == False`). Yalnız `"sahipsiz"` adlar özellikle `ci-cd` veya `gelistirici-yerel` ortamlarında yüksek risk üretir.
3. **Kurulum vs Import tetikleme evresi:** Otomatik çalışan (`kurulum_onayi == "otomatik"`) ve ağ erişimi olan (`ag_erisim == True`) bir kodlama ajanında, `pip install` sırasında `--only-binary=:all:` bayrağı **yoksa** kaynak paketin `setup.py` betiği daha kurulum anında (`"kurulum-setup-py"`) kod çalıştırır; yalnızca tekerlek (wheel) zorlanıyorsa zararlı yük paket ilk `import` edildiğinde (`"import-ani"`) tetiklenir.

> **Savunma köprüsü:** Model çıktısından paket ayıklama, Levenshtein uzaklığıyla typosquat yakalama ve deterministik allow-list doğrulaması `ai-guvence-32` (*Slopsquatting Savunması: Paket Halüsinasyonu*) dersinde kurulur.
:::

::: anlat Bulguyu sınırlı ve doğrulanabilir yaz: tekrar sıklığını, dizin durumunu ve tetik evresini ayır
Bir slopsquatting bulgusu *"Model olmayan paket önerdi"* diye raporlanmaz; saldırı zincirinin üç halkası ayrı ayrı kanıtlanır:

- **Hasat kanıtı:** Paketin kaç farklı denemede (`toplam_gecis`) ve kaç farklı istem şablonunda (`farkli_istem_sayisi`) üretildiği.
- **Kayıt yüzeyi kanıtı:** Adın yerel dizinde `"sahipsiz"` olup olmadığı ve hedef çalışma ortamının (`ci-cd`, `gelistirici-yerel`, `izole-kum-havuzu`) etkisi.
- **Yürütme kanıtı:** Kodlama ajanının insan onayı olmadan (`"otomatik"`) ve hangi `pip` bayraklarıyla (`"kurulum-setup-py"` vs `"import-ani"`) paketi kurduğu.
:::

::: tahmin Tek seferlik uydurma ile kalıcı halüsinasyon adayını ayırt et
Üç farklı denemede modelin önerdiği paketlerden kayıtlı dizinde olmayanların geçiş sayısını hesaplayan kodu incele:

```python
kayitli = {"requests", "fastapi"}
denemeler = [
    ["fastapi", "fastapi-jwt-guard"],
    ["requests", "fastapi-jwt-guard", "tek-uydurma"],
    ["fastapi", "fastapi-jwt-guard"],
]
sayac = {}
for d in denemeler:
    for p in set(d) - kayitli:
        sayac[p] = sayac.get(p, 0) + 1

kalici = sorted(p for p, n in sayac.items() if n >= 2)
print( len(sayac), kalici )
```

???

```cikti
2 ['fastapi-jwt-guard']
```

Kayıtlı dizinde olmayan toplam `2` uydurma paket (`fastapi-jwt-guard` ve `tek-uydurma`) vardır; ancak en az iki denemede tekrar eden tek kalıcı slopsquatting adayı `['fastapi-jwt-guard']` olur.
:::

::: gorev 1 · Çoklu tohum ve istem denemelerinde kalıcı paket halüsinasyonlarını hasat et
`halusinasyon_tekrar_analizi(denemeler, kayitli_dizin)` işlevini yaz:

- `kayitli_dizin`: `1..50` öğeli, her öğesi boş olmayan `str` olan ve küçük harfe (`lower()`) indirgendiğinde benzersiz olan paket listesi.
- `denemeler`: `1..20` öğeli liste; her öğe tam olarak `{"istem_id", "seed", "onerilen_paketler"}` anahtarlarını taşır:
  - `istem_id`: boş olmayan `str`.
  - `seed`: `bool` olmayan ve `>= 0` olan `int`. Listede `(istem_id, seed)` çifti benzersiz olmalıdır.
  - `onerilen_paketler`: `1..20` öğeli, her öğesi boş olmayan `str` olan liste (aynı deneme içindeki mükerrer paket adları küçük harfe indirgenip tek sayılır).
- Geçersiz şema, tür veya değer durumunda `ValueError` yükselt. Girdiyi değiştirme.

Kurallar:
- Tüm paket adlarını küçük harfe (`lower()`) indirgeyerek karşılaştır.
- `kayitli_dizin` içinde **olmayan** her paket bir uydurma (halüsinasyon) adayıdır; `uydurma_sayisi` benzersiz uydurma paket sayısıdır.
- Her uydurma paket için kaç denemede geçtiğini (`toplam_gecis`) ve kaç farklı `istem_id` altında görüldüğünü (`farkli_istem_sayisi`) hesapla.
- `kalici_adaylar`: `toplam_gecis >= 2` olan uydurma paketlerin `{"paket": str, "toplam_gecis": int, "farkli_istem_sayisi": int}` sözlükleri olup `(-toplam_gecis, -farkli_istem_sayisi, paket)` sırasıyla dizilir.
- `en_kalici_paket`: `kalici_adaylar` boş değilse ilk öğenin `"paket"` değeri, boşsa `None`.

Dönüş sözlüğü:

```text
{
  "uydurma_sayisi": int,
  "kalici_adaylar": [{"paket": str, "toplam_gecis": int, "farkli_istem_sayisi": int}, ...],
  "en_kalici_paket": str | None
}
```

```starter
from ai_saldiri_veri import json_yukle

veri = json_yukle("slop/model_onerileri.json")

def halusinasyon_tekrar_analizi(denemeler, kayitli_dizin):
    # HATA: Tek seferlik halüsinasyonları elemek yerine tüm önerileri kalıcı sayıyor.
    uydurmalar = sorted({p.lower() for d in denemeler for p in d["onerilen_paketler"]} - {k.lower() for k in kayitli_dizin})
    return {
        "uydurma_sayisi": len(uydurmalar),
        "kalici_adaylar": [{"paket": p, "toplam_gecis": 1, "farkli_istem_sayisi": 1} for p in uydurmalar],
        "en_kalici_paket": uydurmalar[0] if uydurmalar else None,
    }

print(halusinasyon_tekrar_analizi(veri["denemeler"], veri["kayitli_dizin"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-41")
```

```test
import copy
from pathlib import Path

ok(Path("slop/model_onerileri.json").is_file(), "görünür model önerileri dosyası hazır")

ORNEK_DIZIN = ["Requests", "FastAPI", "Pydantic"]
ORNEK_DENEMELER = [
    {"istem_id": "i1", "seed": 0, "onerilen_paketler": ["FastAPI", "FastAPI-JWT-Guard", "FastAPI-JWT-Guard"]},
    {"istem_id": "i1", "seed": 1, "onerilen_paketler": ["Requests", "py-graphql-shield", "z-ortak"]},
    {"istem_id": "i2", "seed": 0, "onerilen_paketler": ["Pydantic", "py-graphql-shield", "fastapi-jwt-guard", "tek-paket"]},
    {"istem_id": "i1", "seed": 2, "onerilen_paketler": ["z-ortak"]},
]

def sozlesme(fn):
    try:
        d_once = copy.deepcopy(ORNEK_DENEMELER)
        k_once = copy.deepcopy(ORNEK_DIZIN)
        r = fn(ORNEK_DENEMELER, ORNEK_DIZIN)
        if ORNEK_DENEMELER != d_once or ORNEK_DIZIN != k_once:
            return False
        if r != {
            "uydurma_sayisi": 4,
            "kalici_adaylar": [
                {"paket": "fastapi-jwt-guard", "toplam_gecis": 2, "farkli_istem_sayisi": 2},
                {"paket": "py-graphql-shield", "toplam_gecis": 2, "farkli_istem_sayisi": 2},
                {"paket": "z-ortak", "toplam_gecis": 2, "farkli_istem_sayisi": 1},
            ],
            "en_kalici_paket": "fastapi-jwt-guard",
        }:
            return False
        temiz = [{"istem_id": f"x{i}", "seed": i, "onerilen_paketler": ["requests"] * 20} for i in range(20)]
        elli_dizin = [f"pk{i}" for i in range(49)] + ["requests"]
        rt = fn(temiz, elli_dizin)
        if rt != {"uydurma_sayisi": 0, "kalici_adaylar": [], "en_kalici_paket": None}:
            return False
        if fn([temiz[0]], ["requests"])["en_kalici_paket"] is not None:
            return False
        if fn([{"istem_id": "i1", "seed": 0, "onerilen_paketler": ["cok-gecen", "az-gecen"]}, {"istem_id": "i1", "seed": 1, "onerilen_paketler": ["cok-gecen"]}, {"istem_id": "i2", "seed": 0, "onerilen_paketler": ["cok-gecen", "az-gecen"]}], ["requests"])["en_kalici_paket"] != "cok-gecen":
            return False
        for b_den, b_diz in [
            (None, ORNEK_DIZIN), ([], ORNEK_DIZIN), ("den", ORNEK_DIZIN), ([None], ORNEK_DIZIN), ([{}], ORNEK_DIZIN),
            (ORNEK_DENEMELER, None), (ORNEK_DENEMELER, []), (ORNEK_DENEMELER, "dizin"),
            (ORNEK_DENEMELER, [f"p{i}" for i in range(51)]),
            (ORNEK_DENEMELER, [""]), (ORNEK_DENEMELER, [1]), (ORNEK_DENEMELER, ["a", "A"]),
            ([{"istem_id": f"x{i}", "seed": 1, "onerilen_paketler": ["a"]} for i in range(21)], ORNEK_DIZIN),
            ([{"istem_id": "", "seed": 1, "onerilen_paketler": ["a"]}], ORNEK_DIZIN),
            ([{"istem_id": 1, "seed": 1, "onerilen_paketler": ["a"]}], ORNEK_DIZIN),
            ([{"istem_id": "a", "seed": -1, "onerilen_paketler": ["a"]}], ORNEK_DIZIN),
            ([{"istem_id": "a", "seed": True, "onerilen_paketler": ["a"]}], ORNEK_DIZIN),
            ([{"istem_id": "a", "seed": 1.5, "onerilen_paketler": ["a"]}], ORNEK_DIZIN),
            ([{"istem_id": "a", "seed": 1, "onerilen_paketler": ["a"]},
              {"istem_id": "a", "seed": 1, "onerilen_paketler": ["b"]}], ORNEK_DIZIN),
            ([{"istem_id": "a", "seed": 1, "onerilen_paketler": []}], ORNEK_DIZIN),
            ([{"istem_id": "a", "seed": 1, "onerilen_paketler": [f"p{i}" for i in range(21)]}], ORNEK_DIZIN),
            ([{"istem_id": "a", "seed": 1, "onerilen_paketler": "a"}], ORNEK_DIZIN),
            ([{"istem_id": "a", "seed": 1, "onerilen_paketler": [""]}], ORNEK_DIZIN),
            ([{"istem_id": "a", "seed": 1, "onerilen_paketler": [1]}], ORNEK_DIZIN),
            ([{"istem_id": "a", "seed": 1, "onerilen_paketler": ["a"], "ek": 1}], ORNEK_DIZIN),
        ]:
            try:
                fn(b_den, b_diz)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(halusinasyon_tekrar_analizi), "tekrarlayan paket halüsinasyonları ve farklı istem sayıları doğru hesaplanmalı")
def m_tek_dahil(d, k):
    r = halusinasyon_tekrar_analizi(d, k)
    r["uydurma_sayisi"] = 0
    return r
def m_siralama_bozuk(d, k):
    r = halusinasyon_tekrar_analizi(d, k)
    r["kalici_adaylar"] = list(reversed(r["kalici_adaylar"]))
    return r
for ad, mutant in [("uydurma sayısını sıfırlayan", m_tek_dahil), ("kalıcılık sıralamasını bozan", m_siralama_bozuk)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def halusinasyon_tekrar_analizi(denemeler, kayitli_dizin):
    if not isinstance(kayitli_dizin, list) or not 1 <= len(kayitli_dizin) <= 50:
        raise ValueError("kayitli_dizin geçersiz")
    kayitli_kume = set()
    for p in kayitli_dizin:
        if not isinstance(p, str) or not p:
            raise ValueError("dizin öğesi geçersiz")
        kl = p.lower()
        if kl in kayitli_kume:
            raise ValueError("yinelenen dizin öğesi")
        kayitli_kume.add(kl)

    if not isinstance(denemeler, list) or not 1 <= len(denemeler) <= 20:
        raise ValueError("denemeler geçersiz")
    gorulen_anahtar = set()
    gecis_sayisi = {}
    istem_kumeleri = {}

    for d in denemeler:
        if not isinstance(d, dict) or set(d) != {"istem_id", "seed", "onerilen_paketler"}:
            raise ValueError("deneme şeması geçersiz")
        iid = d["istem_id"]
        seed = d["seed"]
        paketler = d["onerilen_paketler"]
        if not isinstance(iid, str) or not iid:
            raise ValueError("istem_id geçersiz")
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise ValueError("seed geçersiz")
        if (iid, seed) in gorulen_anahtar:
            raise ValueError("yinelenen deneme anahtarı")
        if not isinstance(paketler, list) or not 1 <= len(paketler) <= 20:
            raise ValueError("onerilen_paketler geçersiz")
        gorulen_anahtar.add((iid, seed))

        bu_deneme = set()
        for pk in paketler:
            if not isinstance(pk, str) or not pk:
                raise ValueError("paket adı geçersiz")
            bu_deneme.add(pk.lower())

        for pk in bu_deneme:
            if pk not in kayitli_kume:
                gecis_sayisi[pk] = gecis_sayisi.get(pk, 0) + 1
                istem_kumeleri.setdefault(pk, set()).add(iid)

    kalici = []
    for pk, adet in gecis_sayisi.items():
        if adet >= 2:
            kalici.append({
                "paket": pk,
                "toplam_gecis": adet,
                "farkli_istem_sayisi": len(istem_kumeleri[pk]),
            })
    kalici.sort(key=lambda r: (-r["toplam_gecis"], -r["farkli_istem_sayisi"], r["paket"]))
    return {
        "uydurma_sayisi": len(gecis_sayisi),
        "kalici_adaylar": kalici,
        "en_kalici_paket": kalici[0]["paket"] if kalici else None,
    }
```

```hint
Her denemedeki paketleri önce `set(pk.lower() ...)` ile tekilleştir; ardından `kayitli_kume` içinde olmayanları sayıp `adet >= 2` olanları `(-toplam_gecis, -farkli_istem_sayisi, paket)` anahtarıyla sırala.
```
:::

::: gorev 2 · Yerel sentetik paket dizininde kayıt açıklığını ve ele geçirme riskini ölç
`yerel_dizin_ele_gecirme_riski(adaylar, yerel_dizin)` işlevini yaz:

- `yerel_dizin`: `1..50` öğeli sözlük; anahtarlar boş olmayan `str`, değerler `"resmi"`, `"rezerve-yasakli"` veya `"sahipsiz"`.
- `adaylar`: `1..20` öğeli liste; her öğe tam olarak `{"paket", "tekrar_orani", "hedef_ortam"}` anahtarlarını taşır:
  - `paket`: boş olmayan ve listede benzersiz `str`.
  - `tekrar_orani`: `bool` olmayan ve `0.0 <= tekrar_orani <= 1.0` aralığında `int` veya `float`.
  - `hedef_ortam`: `"ci-cd"`, `"gelistirici-yerel"` veya `"izole-kum-havuzu"`.
- Geçersiz şema, tür veya değer durumunda `ValueError` yükselt. Girdiyi değiştirme.

Her aday için:
- `yerel_dizin.get(paket, "sahipsiz")` değeri `"sahipsiz"` ise `kayit_acik = True`, aksi hâlde (`"resmi"` veya `"rezerve-yasakli"`) `kayit_acik = False`.
- `kayit_acik == False` ise `oncelik_puani = 0` ve `risk_sinifi = "kayit-kapali"`.
- `kayit_acik == True` ise:
  - Ortam ağırlığı: `"ci-cd"` için `40`, `"gelistirici-yerel"` için `25`, `"izole-kum-havuzu"` için `10`.
  - `oncelik_puani = round(float(tekrar_orani) * 60) + agirlik`.
  - `risk_sinifi`: `oncelik_puani >= 75` ise `"kritik-slopsquat"`, `45 <= oncelik_puani < 75` ise `"orta-slopsquat"`, `< 45` ise `"dusuk-slopsquat"`.

Girdi sırasıyla `{"paket": str, "kayit_acik": bool, "oncelik_puani": int, "risk_sinifi": str}` listesi döndür.

```starter
from ai_saldiri_veri import json_yukle

veri = json_yukle("slop/yerel_paket_dizini.json")

def yerel_dizin_ele_gecirme_riski(adaylar, yerel_dizin):
    # HATA: Rezerve/resmi paketlerin kayıt kapalı olduğunu kontrol etmiyor.
    return [
        {
            "paket": a["paket"],
            "kayit_acik": True,
            "oncelik_puani": round(float(a["tekrar_orani"]) * 60),
            "risk_sinifi": "orta-slopsquat",
        }
        for a in adaylar
    ]

print(yerel_dizin_ele_gecirme_riski(veri["adaylar"], veri["yerel_dizin"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-41")
```

```test
import copy
from pathlib import Path

ok(Path("slop/yerel_paket_dizini.json").is_file(), "görünür yerel paket dizini dosyası hazır")

ORNEK_YEREL = {
    "fastapi": "resmi",
    "ic-paket": "rezerve-yasakli",
    "acik-1": "sahipsiz",
}
ORNEK_ADAYLAR = [
    {"paket": "acik-1", "tekrar_orani": 0.75, "hedef_ortam": "ci-cd"},
    {"paket": "acik-2", "tekrar_orani": 0.5, "hedef_ortam": "gelistirici-yerel"},
    {"paket": "acik-3", "tekrar_orani": 0.5, "hedef_ortam": "izole-kum-havuzu"},
    {"paket": "ic-paket", "tekrar_orani": 1.0, "hedef_ortam": "ci-cd"},
    {"paket": "fastapi", "tekrar_orani": 1.0, "hedef_ortam": "ci-cd"},
]

def sozlesme(fn):
    try:
        a_once = copy.deepcopy(ORNEK_ADAYLAR)
        y_once = copy.deepcopy(ORNEK_YEREL)
        r = fn(ORNEK_ADAYLAR, ORNEK_YEREL)
        if ORNEK_ADAYLAR != a_once or ORNEK_YEREL != y_once:
            return False
        if r != [
            {"paket": "acik-1", "kayit_acik": True, "oncelik_puani": 85, "risk_sinifi": "kritik-slopsquat"},
            {"paket": "acik-2", "kayit_acik": True, "oncelik_puani": 55, "risk_sinifi": "orta-slopsquat"},
            {"paket": "acik-3", "kayit_acik": True, "oncelik_puani": 40, "risk_sinifi": "dusuk-slopsquat"},
            {"paket": "ic-paket", "kayit_acik": False, "oncelik_puani": 0, "risk_sinifi": "kayit-kapali"},
            {"paket": "fastapi", "kayit_acik": False, "oncelik_puani": 0, "risk_sinifi": "kayit-kapali"},
        ]:
            return False
        sinir_adaylar = [
            {"paket": "s75", "tekrar_orani": 5 / 6, "hedef_ortam": "gelistirici-yerel"},
            {"paket": "s74", "tekrar_orani": 34 / 60, "hedef_ortam": "ci-cd"},
            {"paket": "s45", "tekrar_orani": 7 / 12, "hedef_ortam": "izole-kum-havuzu"},
            {"paket": "s44", "tekrar_orani": 34 / 60, "hedef_ortam": "izole-kum-havuzu"},
            {"paket": "s0", "tekrar_orani": 0.0, "hedef_ortam": "izole-kum-havuzu"},
        ]
        rs = fn(sinir_adaylar, {"a": "resmi"})
        if [x["risk_sinifi"] for x in rs] != ["kritik-slopsquat", "orta-slopsquat", "orta-slopsquat", "dusuk-slopsquat", "dusuk-slopsquat"]:
            return False
        yirmi_a = [{"paket": f"p{i}", "tekrar_orani": 0.1, "hedef_ortam": "ci-cd"} for i in range(20)]
        elli_y = {f"d{i}": "sahipsiz" for i in range(50)}
        if len(fn(yirmi_a, elli_y)) != 20 or len(fn([yirmi_a[0]], {"d0": "sahipsiz"})) != 1:
            return False
        for ba, by in [
            (None, ORNEK_YEREL), ([], ORNEK_YEREL), ("aday", ORNEK_YEREL), ([None], ORNEK_YEREL), ([{}], ORNEK_YEREL),
            (ORNEK_ADAYLAR, None), (ORNEK_ADAYLAR, {}), (ORNEK_ADAYLAR, "dizin"),
            (ORNEK_ADAYLAR, {f"d{i}": "sahipsiz" for i in range(51)}),
            (ORNEK_ADAYLAR, {"": "sahipsiz"}), (ORNEK_ADAYLAR, {1: "sahipsiz"}), (ORNEK_ADAYLAR, {"a": "bilinmeyen"}),
            ([{"paket": f"p{i}", "tekrar_orani": 0.5, "hedef_ortam": "ci-cd"} for i in range(21)], ORNEK_YEREL),
            ([{"paket": "", "tekrar_orani": 0.5, "hedef_ortam": "ci-cd"}], ORNEK_YEREL),
            ([{"paket": 1, "tekrar_orani": 0.5, "hedef_ortam": "ci-cd"}], ORNEK_YEREL),
            ([{"paket": "a", "tekrar_orani": 0.5, "hedef_ortam": "ci-cd"},
              {"paket": "a", "tekrar_orani": 0.5, "hedef_ortam": "ci-cd"}], ORNEK_YEREL),
            ([{"paket": "a", "tekrar_orani": -0.1, "hedef_ortam": "ci-cd"}], ORNEK_YEREL),
            ([{"paket": "a", "tekrar_orani": 1.1, "hedef_ortam": "ci-cd"}], ORNEK_YEREL),
            ([{"paket": "a", "tekrar_orani": float("nan"), "hedef_ortam": "ci-cd"}], {"a": "resmi"}),
            ([{"paket": "a", "tekrar_orani": True, "hedef_ortam": "ci-cd"}], ORNEK_YEREL),
            ([{"paket": "a", "tekrar_orani": "0.5", "hedef_ortam": "ci-cd"}], ORNEK_YEREL),
            ([{"paket": "a", "tekrar_orani": 0.5, "hedef_ortam": "bulut"}], ORNEK_YEREL),
            ([{"paket": "a", "tekrar_orani": 0.5, "hedef_ortam": "ci-cd", "ek": 1}], ORNEK_YEREL),
        ]:
            try:
                fn(ba, by)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(yerel_dizin_ele_gecirme_riski), "yerel dizin sahiplik durumu ve slopsquatting öncelik puanı doğru hesaplanmalı")
def m_rezerve_acik(a, y):
    return yerel_dizin_ele_gecirme_riski(a, {"x": "sahipsiz"})
def m_ortamsiz(a, y):
    r = yerel_dizin_ele_gecirme_riski(a, y)
    for k in r:
        if k["kayit_acik"]:
            k["oncelik_puani"] = 50
    return r
for ad, mutant in [("rezerve paketi açık sayan", m_rezerve_acik), ("ortam ağırlığını katmayan", m_ortamsiz)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def yerel_dizin_ele_gecirme_riski(adaylar, yerel_dizin):
    durumlar = ("resmi", "rezerve-yasakli", "sahipsiz")
    ortamlar = ("ci-cd", "gelistirici-yerel", "izole-kum-havuzu")
    if not isinstance(yerel_dizin, dict) or not 1 <= len(yerel_dizin) <= 50:
        raise ValueError("yerel_dizin geçersiz")
    for k, v in yerel_dizin.items():
        if not isinstance(k, str) or not k or v not in durumlar:
            raise ValueError("yerel_dizin öğesi geçersiz")

    if not isinstance(adaylar, list) or not 1 <= len(adaylar) <= 20:
        raise ValueError("adaylar geçersiz")
    gorulen = set()
    sonuc = []

    for a in adaylar:
        if not isinstance(a, dict) or set(a) != {"paket", "tekrar_orani", "hedef_ortam"}:
            raise ValueError("aday şeması geçersiz")
        pk = a["paket"]
        oran = a["tekrar_orani"]
        ortam = a["hedef_ortam"]
        if not isinstance(pk, str) or not pk or pk in gorulen:
            raise ValueError("paket geçersiz")
        if isinstance(oran, bool) or not isinstance(oran, (int, float)) or not 0.0 <= float(oran) <= 1.0:
            raise ValueError("tekrar_orani geçersiz")
        if ortam not in ortamlar:
            raise ValueError("hedef_ortam geçersiz")
        gorulen.add(pk)

        durum = yerel_dizin.get(pk, "sahipsiz")
        acik = durum == "sahipsiz"
        if not acik:
            puan = 0
            sinif = "kayit-kapali"
        else:
            agirlik = 40 if ortam == "ci-cd" else 25 if ortam == "gelistirici-yerel" else 10
            puan = round(float(oran) * 60) + agirlik
            if puan >= 75:
                sinif = "kritik-slopsquat"
            elif puan >= 45:
                sinif = "orta-slopsquat"
            else:
                sinif = "dusuk-slopsquat"

        sonuc.append({
            "paket": pk,
            "kayit_acik": acik,
            "oncelik_puani": puan,
            "risk_sinifi": sinif,
        })
    return sonuc
```

```hint
`yerel_dizin.get(pk, "sahipsiz") == "sahipsiz"` olduğunda `kayit_acik = True` olur; aksi durumda puan `0` ve sınıf `"kayit-kapali"` döner.
```
:::

::: gorev 3 · Kodlama ajanı kurulum izlerinde setup.py ve import tetikleme evresini belirle
`otomatik_kurulum_zinciri(ajan_izleri, sahipsiz_paketler)` işlevini yaz:

- `sahipsiz_paketler`: `1..50` öğeli, her öğesi boş olmayan ve benzersiz `str` olan liste.
- `ajan_izleri`: `1..20` öğeli liste; her öğe tam olarak `{"iz_id", "paket", "kurulum_onayi", "ag_erisim", "pip_bayraklari"}` anahtarlarını taşır:
  - `iz_id`: boş olmayan ve listede benzersiz `str`.
  - `paket`: boş olmayan `str`.
  - `kurulum_onayi`: `"otomatik"` veya `"insan-onayli"`.
  - `ag_erisim`: `bool`.
  - `pip_bayraklari`: `0..10` öğeli, her öğesi boş olmayan `str` olan liste.
- Geçersiz şema, tür veya değer durumunda `ValueError` yükselt. Girdiyi değiştirme.

Her iz için:
- Eğer `paket in sahipsiz_paketler` **ve** `ag_erisim == True` **ve** `kurulum_onayi == "otomatik"` ise:
  - `tetiklenir_mi = True`
  - `"--only-binary=:all:" in pip_bayraklari` ise `tetik_evresi = "import-ani"`, değilse `tetik_evresi = "kurulum-setup-py"`.
- Aksi hâlde:
  - `tetiklenir_mi = False`
  - `tetik_evresi = "engellendi"`.

Girdi sırasıyla `{"iz_id": str, "tetiklenir_mi": bool, "tetik_evresi": str}` listesi döndür.

```starter
from ai_saldiri_veri import json_yukle

izler = json_yukle("slop/ajan_kurulum_izleri.json")

def otomatik_kurulum_zinciri(ajan_izleri, sahipsiz_paketler):
    # HATA: --only-binary=:all: bayrağını ve insan onayını dikkate almıyor.
    return [
        {
            "iz_id": iz["iz_id"],
            "tetiklenir_mi": iz["paket"] in sahipsiz_paketler,
            "tetik_evresi": "kurulum-setup-py" if iz["paket"] in sahipsiz_paketler else "engellendi",
        }
        for iz in ajan_izleri
    ]

print(otomatik_kurulum_zinciri(izler, ["fastapi-jwt-guard", "py-graphql-shield"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-41")
```

```test
import copy
from pathlib import Path

ok(Path("slop/ajan_kurulum_izleri.json").is_file(), "görünür ajan kurulum izleri dosyası hazır")

ORNEK_SAHIPSIZ = ["fastapi-jwt-guard", "py-graphql-shield"]
ORNEK_KURULUM = [
    {"iz_id": "k1", "paket": "fastapi-jwt-guard", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": ["--no-cache-dir"]},
    {"iz_id": "k2", "paket": "py-graphql-shield", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": ["--only-binary=:all:"]},
    {"iz_id": "k3", "paket": "fastapi-jwt-guard", "kurulum_onayi": "insan-onayli", "ag_erisim": True, "pip_bayraklari": []},
    {"iz_id": "k4", "paket": "fastapi-jwt-guard", "kurulum_onayi": "otomatik", "ag_erisim": False, "pip_bayraklari": []},
    {"iz_id": "k5", "paket": "requests", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": []},
]

def sozlesme(fn):
    try:
        k_once = copy.deepcopy(ORNEK_KURULUM)
        s_once = copy.deepcopy(ORNEK_SAHIPSIZ)
        r = fn(ORNEK_KURULUM, ORNEK_SAHIPSIZ)
        if ORNEK_KURULUM != k_once or ORNEK_SAHIPSIZ != s_once:
            return False
        if r != [
            {"iz_id": "k1", "tetiklenir_mi": True, "tetik_evresi": "kurulum-setup-py"},
            {"iz_id": "k2", "tetiklenir_mi": True, "tetik_evresi": "import-ani"},
            {"iz_id": "k3", "tetiklenir_mi": False, "tetik_evresi": "engellendi"},
            {"iz_id": "k4", "tetiklenir_mi": False, "tetik_evresi": "engellendi"},
            {"iz_id": "k5", "tetiklenir_mi": False, "tetik_evresi": "engellendi"},
        ]:
            return False
        yirmi_iz = [{"iz_id": f"z{i}", "paket": "s0", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": [f"--f{j}" for j in range(10)]} for i in range(20)]
        elli_s = [f"s{i}" for i in range(50)]
        if len(fn(yirmi_iz, elli_s)) != 20 or len(fn([yirmi_iz[0]], ["s0"])) != 1:
            return False
        for bi, bs in [
            (None, ORNEK_SAHIPSIZ), ([], ORNEK_SAHIPSIZ), ("iz", ORNEK_SAHIPSIZ), ([None], ORNEK_SAHIPSIZ), ([{}], ORNEK_SAHIPSIZ),
            (ORNEK_KURULUM, None), (ORNEK_KURULUM, []), (ORNEK_KURULUM, "s"),
            (ORNEK_KURULUM, [f"s{i}" for i in range(51)]),
            (ORNEK_KURULUM, [""]), (ORNEK_KURULUM, [1]), (ORNEK_KURULUM, ["a", "a"]),
            ([{"iz_id": f"z{i}", "paket": "a", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": []} for i in range(21)], ORNEK_SAHIPSIZ),
            ([{"iz_id": "", "paket": "a", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": []}], ORNEK_SAHIPSIZ),
            ([{"iz_id": 1, "paket": "a", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": []}], ORNEK_SAHIPSIZ),
            ([{"iz_id": "a", "paket": "a", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": []},
              {"iz_id": "a", "paket": "a", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": []}], ORNEK_SAHIPSIZ),
            ([{"iz_id": "a", "paket": "", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": []}], ORNEK_SAHIPSIZ),
            ([{"iz_id": "a", "paket": 1, "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": []}], ORNEK_SAHIPSIZ),
            ([{"iz_id": "a", "paket": "a", "kurulum_onayi": "belirsiz", "ag_erisim": True, "pip_bayraklari": []}], ORNEK_SAHIPSIZ),
            ([{"iz_id": "a", "paket": "a", "kurulum_onayi": "otomatik", "ag_erisim": 1, "pip_bayraklari": []}], ORNEK_SAHIPSIZ),
            ([{"iz_id": "a", "paket": "a", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": "bayrak"}], ORNEK_SAHIPSIZ),
            ([{"iz_id": "a", "paket": "a", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": [f"b{i}" for i in range(11)]}], ORNEK_SAHIPSIZ),
            ([{"iz_id": "a", "paket": "a", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": [""]}], ORNEK_SAHIPSIZ),
            ([{"iz_id": "a", "paket": "a", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": [1]}], ORNEK_SAHIPSIZ),
            ([{"iz_id": "a", "paket": "a", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": [], "ek": 1}], ORNEK_SAHIPSIZ),
        ]:
            try:
                fn(bi, bs)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(otomatik_kurulum_zinciri), "otomatik kurulum onayı, ağ erişimi ve --only-binary=:all: tetik evresi doğru ayrılmalı")
def m_hep_setup(iz, s):
    return [dict(x, tetik_evresi="kurulum-setup-py" if x["tetiklenir_mi"] else "engellendi") for x in otomatik_kurulum_zinciri(iz, s)]
def m_onaysiz(iz, s):
    return otomatik_kurulum_zinciri([dict(x, kurulum_onayi="otomatik") for x in iz], s)
for ad, mutant in [("--only-binary bayrağını yok sayan", m_hep_setup), ("insan onayını atlayan", m_onaysiz)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def otomatik_kurulum_zinciri(ajan_izleri, sahipsiz_paketler):
    if not isinstance(sahipsiz_paketler, list) or not 1 <= len(sahipsiz_paketler) <= 50:
        raise ValueError("sahipsiz_paketler geçersiz")
    sahipsiz_kume = set()
    for p in sahipsiz_paketler:
        if not isinstance(p, str) or not p or p in sahipsiz_kume:
            raise ValueError("sahipsiz paket geçersiz")
        sahipsiz_kume.add(p)

    if not isinstance(ajan_izleri, list) or not 1 <= len(ajan_izleri) <= 20:
        raise ValueError("ajan_izleri geçersiz")
    gorulen = set()
    sonuc = []

    for iz in ajan_izleri:
        if not isinstance(iz, dict) or set(iz) != {"iz_id", "paket", "kurulum_onayi", "ag_erisim", "pip_bayraklari"}:
            raise ValueError("iz şeması geçersiz")
        iid = iz["iz_id"]
        pk = iz["paket"]
        onay = iz["kurulum_onayi"]
        ag = iz["ag_erisim"]
        bayraklar = iz["pip_bayraklari"]
        if not isinstance(iid, str) or not iid or iid in gorulen:
            raise ValueError("iz_id geçersiz")
        if not isinstance(pk, str) or not pk:
            raise ValueError("paket geçersiz")
        if onay not in ("otomatik", "insan-onayli"):
            raise ValueError("kurulum_onayi geçersiz")
        if not isinstance(ag, bool):
            raise ValueError("ag_erisim geçersiz")
        if not isinstance(bayraklar, list) or len(bayraklar) > 10:
            raise ValueError("pip_bayraklari geçersiz")
        for b in bayraklar:
            if not isinstance(b, str) or not b:
                raise ValueError("bayrak geçersiz")
        gorulen.add(iid)

        if pk in sahipsiz_kume and ag and onay == "otomatik":
            tetik = True
            evre = "import-ani" if "--only-binary=:all:" in bayraklar else "kurulum-setup-py"
        else:
            tetik = False
            evre = "engellendi"

        sonuc.append({
            "iz_id": iid,
            "tetiklenir_mi": tetik,
            "tetik_evresi": evre,
        })
    return sonuc
```

```hint
Yalnız `pk in sahipsiz_kume and ag and onay == "otomatik"` olduğunda `tetiklenir_mi = True` olur; `"--only-binary=:all:"` bayrağı varsa `setup.py` atlandığından evre `"import-ani"` döner.
```
:::

::: gorev Gerçek deney · Yerel modelde paket halüsinasyonu hasadı ve yerel dizin risk analizi
Önceki üç görevdeki `halusinasyon_tekrar_analizi`, `yerel_dizin_ele_gecirme_riski` ve `otomatik_kurulum_zinciri` işlevlerini burada birleştir.

Canlı deneyde `ai_lab.SohbetOturumu` ile yerel Ollama modeline niş kriptografi/yetkilendirme görevleri için iki farklı istem gönderilerek `pip install <paket>` önerileri toplanır; hiçbir gerçek paket deposuna bağlanmadan **yalnızca yerel sentetik dizin** karşısında tekrarlayan halüsinasyon adayları ve kurulum zinciri riski ölçülür.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab
from ai_saldiri_veri import json_yukle

def halusinasyon_tekrar_analizi(denemeler, kayitli_dizin):
    return {"uydurma_sayisi": 0, "kalici_adaylar": [], "en_kalici_paket": None}

def yerel_dizin_ele_gecirme_riski(adaylar, yerel_dizin):
    return []

def otomatik_kurulum_zinciri(ajan_izleri, sahipsiz_paketler):
    return []

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_41 as deney
    deney.goster(halusinasyon_tekrar_analizi, yerel_dizin_ele_gecirme_riski, otomatik_kurulum_zinciri)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-41")
```

```test
import ai_lab
import copy
from sandbox import ai_gercek_ai_saldiri_41 as D

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for ad in ("halusinasyon_tekrar_analizi", "yerel_dizin_ele_gecirme_riski", "otomatik_kurulum_zinciri"):
    need(ad)

sorun = ai_lab.kod_denetimi(src, ("halusinasyon_tekrar_referans", "yerel_dizin_risk_referans", "otomatik_kurulum_referans"))
ok(not sorun, "laboratuvar yamalanmamalı, referans işlevler çağrılmamalı")

ORNEK_DIZIN = ["Requests", "FastAPI", "Pydantic"]
ORNEK_DENEMELER = [
    {"istem_id": "i1", "seed": 0, "onerilen_paketler": ["FastAPI", "FastAPI-JWT-Guard", "FastAPI-JWT-Guard"]},
    {"istem_id": "i1", "seed": 1, "onerilen_paketler": ["Requests", "py-graphql-shield", "z-ortak"]},
    {"istem_id": "i2", "seed": 0, "onerilen_paketler": ["Pydantic", "py-graphql-shield", "fastapi-jwt-guard", "tek-paket"]},
    {"istem_id": "i1", "seed": 2, "onerilen_paketler": ["z-ortak"]},
]
ORNEK_YEREL = {
    "fastapi": "resmi",
    "ic-paket": "rezerve-yasakli",
    "acik-1": "sahipsiz",
}
ORNEK_ADAYLAR = [
    {"paket": "acik-1", "tekrar_orani": 0.75, "hedef_ortam": "ci-cd"},
    {"paket": "acik-2", "tekrar_orani": 0.5, "hedef_ortam": "gelistirici-yerel"},
    {"paket": "acik-3", "tekrar_orani": 0.5, "hedef_ortam": "izole-kum-havuzu"},
    {"paket": "ic-paket", "tekrar_orani": 1.0, "hedef_ortam": "ci-cd"},
    {"paket": "fastapi", "tekrar_orani": 1.0, "hedef_ortam": "ci-cd"},
]
ORNEK_SAHIPSIZ = ["fastapi-jwt-guard", "py-graphql-shield"]
ORNEK_KURULUM = [
    {"iz_id": "k1", "paket": "fastapi-jwt-guard", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": ["--no-cache-dir"]},
    {"iz_id": "k2", "paket": "py-graphql-shield", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": ["--only-binary=:all:"]},
    {"iz_id": "k3", "paket": "fastapi-jwt-guard", "kurulum_onayi": "insan-onayli", "ag_erisim": True, "pip_bayraklari": []},
    {"iz_id": "k4", "paket": "fastapi-jwt-guard", "kurulum_onayi": "otomatik", "ag_erisim": False, "pip_bayraklari": []},
    {"iz_id": "k5", "paket": "requests", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": []},
]

def _sinir_ve_sema_kontrol():
    try:
        temiz = [{"istem_id": f"x{i}", "seed": i, "onerilen_paketler": ["requests"] * 20} for i in range(20)]
        elli_dizin = [f"pk{i}" for i in range(49)] + ["requests"]
        if (
            halusinasyon_tekrar_analizi(copy.deepcopy(ORNEK_DENEMELER), copy.deepcopy(ORNEK_DIZIN))
            != D.halusinasyon_tekrar_referans(ORNEK_DENEMELER, ORNEK_DIZIN)
            or halusinasyon_tekrar_analizi(temiz, elli_dizin) != {"uydurma_sayisi": 0, "kalici_adaylar": [], "en_kalici_paket": None}
            or halusinasyon_tekrar_analizi([temiz[0]], ["requests"])["en_kalici_paket"] is not None
            or halusinasyon_tekrar_analizi([{"istem_id": "i1", "seed": 0, "onerilen_paketler": ["cok-gecen", "az-gecen"]}, {"istem_id": "i1", "seed": 1, "onerilen_paketler": ["cok-gecen"]}, {"istem_id": "i2", "seed": 0, "onerilen_paketler": ["cok-gecen", "az-gecen"]}], ["requests"])["en_kalici_paket"] != "cok-gecen"
        ):
            return False
        for b_den, b_diz in [
            (None, ORNEK_DIZIN), ([], ORNEK_DIZIN), ("den", ORNEK_DIZIN), ([None], ORNEK_DIZIN), ([{}], ORNEK_DIZIN),
            (ORNEK_DENEMELER, None), (ORNEK_DENEMELER, []), (ORNEK_DENEMELER, "dizin"),
            (ORNEK_DENEMELER, [f"p{i}" for i in range(51)]),
            (ORNEK_DENEMELER, [""]), (ORNEK_DENEMELER, [1]), (ORNEK_DENEMELER, ["a", "A"]),
            ([{"istem_id": f"x{i}", "seed": 1, "onerilen_paketler": ["a"]} for i in range(21)], ORNEK_DIZIN),
            ([{"istem_id": "", "seed": 1, "onerilen_paketler": ["a"]}], ORNEK_DIZIN),
            ([{"istem_id": 1, "seed": 1, "onerilen_paketler": ["a"]}], ORNEK_DIZIN),
            ([{"istem_id": "a", "seed": -1, "onerilen_paketler": ["a"]}], ORNEK_DIZIN),
            ([{"istem_id": "a", "seed": True, "onerilen_paketler": ["a"]}], ORNEK_DIZIN),
            ([{"istem_id": "a", "seed": 1.5, "onerilen_paketler": ["a"]}], ORNEK_DIZIN),
            ([{"istem_id": "a", "seed": 1, "onerilen_paketler": ["a"]},
              {"istem_id": "a", "seed": 1, "onerilen_paketler": ["b"]}], ORNEK_DIZIN),
            ([{"istem_id": "a", "seed": 1, "onerilen_paketler": []}], ORNEK_DIZIN),
            ([{"istem_id": "a", "seed": 1, "onerilen_paketler": [f"p{i}" for i in range(21)]}], ORNEK_DIZIN),
            ([{"istem_id": "a", "seed": 1, "onerilen_paketler": "a"}], ORNEK_DIZIN),
            ([{"istem_id": "a", "seed": 1, "onerilen_paketler": [""]}], ORNEK_DIZIN),
            ([{"istem_id": "a", "seed": 1, "onerilen_paketler": [1]}], ORNEK_DIZIN),
            ([{"istem_id": "a", "seed": 1, "onerilen_paketler": ["a"], "ek": 1}], ORNEK_DIZIN),
        ]:
            try:
                halusinasyon_tekrar_analizi(b_den, b_diz)
                return False
            except ValueError:
                pass

        sinir_adaylar = [
            {"paket": "s75", "tekrar_orani": 5 / 6, "hedef_ortam": "gelistirici-yerel"},
            {"paket": "s74", "tekrar_orani": 34 / 60, "hedef_ortam": "ci-cd"},
            {"paket": "s45", "tekrar_orani": 7 / 12, "hedef_ortam": "izole-kum-havuzu"},
            {"paket": "s44", "tekrar_orani": 34 / 60, "hedef_ortam": "izole-kum-havuzu"},
            {"paket": "s0", "tekrar_orani": 0.0, "hedef_ortam": "izole-kum-havuzu"},
        ]
        yirmi_a = [{"paket": f"p{i}", "tekrar_orani": 0.1, "hedef_ortam": "ci-cd"} for i in range(20)]
        elli_y = {f"d{i}": "sahipsiz" for i in range(50)}
        if (
            yerel_dizin_ele_gecirme_riski(copy.deepcopy(ORNEK_ADAYLAR), copy.deepcopy(ORNEK_YEREL))
            != D.yerel_dizin_risk_referans(ORNEK_ADAYLAR, ORNEK_YEREL)
            or [x["risk_sinifi"] for x in yerel_dizin_ele_gecirme_riski(sinir_adaylar, {"a": "resmi"})]
            != ["kritik-slopsquat", "orta-slopsquat", "orta-slopsquat", "dusuk-slopsquat", "dusuk-slopsquat"]
            or len(yerel_dizin_ele_gecirme_riski(yirmi_a, elli_y)) != 20
            or len(yerel_dizin_ele_gecirme_riski([yirmi_a[0]], {"d0": "sahipsiz"})) != 1
        ):
            return False
        for ba, by in [
            (None, ORNEK_YEREL), ([], ORNEK_YEREL), ("aday", ORNEK_YEREL), ([None], ORNEK_YEREL), ([{}], ORNEK_YEREL),
            (ORNEK_ADAYLAR, None), (ORNEK_ADAYLAR, {}), (ORNEK_ADAYLAR, "dizin"),
            (ORNEK_ADAYLAR, {f"d{i}": "sahipsiz" for i in range(51)}),
            (ORNEK_ADAYLAR, {"": "sahipsiz"}), (ORNEK_ADAYLAR, {1: "sahipsiz"}), (ORNEK_ADAYLAR, {"a": "bilinmeyen"}),
            ([{"paket": f"p{i}", "tekrar_orani": 0.5, "hedef_ortam": "ci-cd"} for i in range(21)], ORNEK_YEREL),
            ([{"paket": "", "tekrar_orani": 0.5, "hedef_ortam": "ci-cd"}], ORNEK_YEREL),
            ([{"paket": 1, "tekrar_orani": 0.5, "hedef_ortam": "ci-cd"}], ORNEK_YEREL),
            ([{"paket": "a", "tekrar_orani": 0.5, "hedef_ortam": "ci-cd"},
              {"paket": "a", "tekrar_orani": 0.5, "hedef_ortam": "ci-cd"}], ORNEK_YEREL),
            ([{"paket": "a", "tekrar_orani": -0.1, "hedef_ortam": "ci-cd"}], ORNEK_YEREL),
            ([{"paket": "a", "tekrar_orani": 1.1, "hedef_ortam": "ci-cd"}], ORNEK_YEREL),
            ([{"paket": "a", "tekrar_orani": float("nan"), "hedef_ortam": "ci-cd"}], {"a": "resmi"}),
            ([{"paket": "a", "tekrar_orani": True, "hedef_ortam": "ci-cd"}], ORNEK_YEREL),
            ([{"paket": "a", "tekrar_orani": "0.5", "hedef_ortam": "ci-cd"}], ORNEK_YEREL),
            ([{"paket": "a", "tekrar_orani": 0.5, "hedef_ortam": "bulut"}], ORNEK_YEREL),
            ([{"paket": "a", "tekrar_orani": 0.5, "hedef_ortam": "ci-cd", "ek": 1}], ORNEK_YEREL),
        ]:
            try:
                yerel_dizin_ele_gecirme_riski(ba, by)
                return False
            except ValueError:
                pass

        yirmi_iz = [{"iz_id": f"z{i}", "paket": "s0", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": [f"--f{j}" for j in range(10)]} for i in range(20)]
        elli_s = [f"s{i}" for i in range(50)]
        if (
            otomatik_kurulum_zinciri(copy.deepcopy(ORNEK_KURULUM), copy.deepcopy(ORNEK_SAHIPSIZ))
            != D.otomatik_kurulum_referans(ORNEK_KURULUM, ORNEK_SAHIPSIZ)
            or len(otomatik_kurulum_zinciri(yirmi_iz, elli_s)) != 20
            or len(otomatik_kurulum_zinciri([yirmi_iz[0]], ["s0"])) != 1
        ):
            return False
        for bi, bs in [
            (None, ORNEK_SAHIPSIZ), ([], ORNEK_SAHIPSIZ), ("iz", ORNEK_SAHIPSIZ), ([None], ORNEK_SAHIPSIZ), ([{}], ORNEK_SAHIPSIZ),
            (ORNEK_KURULUM, None), (ORNEK_KURULUM, []), (ORNEK_KURULUM, "s"),
            (ORNEK_KURULUM, [f"s{i}" for i in range(51)]),
            (ORNEK_KURULUM, [""]), (ORNEK_KURULUM, [1]), (ORNEK_KURULUM, ["a", "a"]),
            ([{"iz_id": f"z{i}", "paket": "a", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": []} for i in range(21)], ORNEK_SAHIPSIZ),
            ([{"iz_id": "", "paket": "a", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": []}], ORNEK_SAHIPSIZ),
            ([{"iz_id": 1, "paket": "a", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": []}], ORNEK_SAHIPSIZ),
            ([{"iz_id": "a", "paket": "a", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": []},
              {"iz_id": "a", "paket": "a", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": []}], ORNEK_SAHIPSIZ),
            ([{"iz_id": "a", "paket": "", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": []}], ORNEK_SAHIPSIZ),
            ([{"iz_id": "a", "paket": 1, "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": []}], ORNEK_SAHIPSIZ),
            ([{"iz_id": "a", "paket": "a", "kurulum_onayi": "belirsiz", "ag_erisim": True, "pip_bayraklari": []}], ORNEK_SAHIPSIZ),
            ([{"iz_id": "a", "paket": "a", "kurulum_onayi": "otomatik", "ag_erisim": 1, "pip_bayraklari": []}], ORNEK_SAHIPSIZ),
            ([{"iz_id": "a", "paket": "a", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": "bayrak"}], ORNEK_SAHIPSIZ),
            ([{"iz_id": "a", "paket": "a", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": [f"b{i}" for i in range(11)]}], ORNEK_SAHIPSIZ),
            ([{"iz_id": "a", "paket": "a", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": [""]}], ORNEK_SAHIPSIZ),
            ([{"iz_id": "a", "paket": "a", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": [1]}], ORNEK_SAHIPSIZ),
            ([{"iz_id": "a", "paket": "a", "kurulum_onayi": "otomatik", "ag_erisim": True, "pip_bayraklari": [], "ek": 1}], ORNEK_SAHIPSIZ),
        ]:
            try:
                otomatik_kurulum_zinciri(bi, bs)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(_sinir_ve_sema_kontrol(), "halüsinasyon tekrar, yerel dizin risk ve otomatik kurulum işlevleri tüm sınır ve şema kurallarını geçti")

if not all(checks):
    stop()

try:
    r = D.deney(halusinasyon_tekrar_analizi, yerel_dizin_ele_gecirme_riski, otomatik_kurulum_zinciri)
except Exception as e:
    ok(False, f"GERÇEK SLOPSQUATTING DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

for ad, deger in r["kontroller"].items():
    ok(deger, "gerçek deney: " + ad)

ai_lab.kanit_yaz("saldiri-41-slopsquatting", {
    "kaynak": "gercek",
    "kabul": all(checks),
    "ders": "ai-saldiri-41",
    "ortam": r["ortam"],
    "ayarlar": r["ayarlar"],
    "deney": r,
    "ozet": r["ozet"],
})
o = r["ozet"]
ok(
    True,
    f"BULGU ({r['ortam']['model']['ad']}): canlı uydurma aday={o['canli_uydurma_sayisi']}, "
    f"en kalıcı aday={o['en_kalici_paket']}, kritik slopsquat={o['fixture_kritik_sayisi']}.",
)
```

```solution
import ai_lab

def halusinasyon_tekrar_analizi(denemeler, kayitli_dizin):
    if not isinstance(kayitli_dizin, list) or not 1 <= len(kayitli_dizin) <= 50:
        raise ValueError("kayitli_dizin geçersiz")
    kayitli_kume = set()
    for p in kayitli_dizin:
        if not isinstance(p, str) or not p:
            raise ValueError("dizin öğesi geçersiz")
        kl = p.lower()
        if kl in kayitli_kume:
            raise ValueError("yinelenen dizin öğesi")
        kayitli_kume.add(kl)

    if not isinstance(denemeler, list) or not 1 <= len(denemeler) <= 20:
        raise ValueError("denemeler geçersiz")
    gorulen_anahtar = set()
    gecis_sayisi = {}
    istem_kumeleri = {}

    for d in denemeler:
        if not isinstance(d, dict) or set(d) != {"istem_id", "seed", "onerilen_paketler"}:
            raise ValueError("deneme şeması geçersiz")
        iid = d["istem_id"]
        seed = d["seed"]
        paketler = d["onerilen_paketler"]
        if not isinstance(iid, str) or not iid:
            raise ValueError("istem_id geçersiz")
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise ValueError("seed geçersiz")
        if (iid, seed) in gorulen_anahtar:
            raise ValueError("yinelenen deneme anahtarı")
        if not isinstance(paketler, list) or not 1 <= len(paketler) <= 20:
            raise ValueError("onerilen_paketler geçersiz")
        gorulen_anahtar.add((iid, seed))

        bu_deneme = set()
        for pk in paketler:
            if not isinstance(pk, str) or not pk:
                raise ValueError("paket adı geçersiz")
            bu_deneme.add(pk.lower())

        for pk in bu_deneme:
            if pk not in kayitli_kume:
                gecis_sayisi[pk] = gecis_sayisi.get(pk, 0) + 1
                istem_kumeleri.setdefault(pk, set()).add(iid)

    kalici = []
    for pk, adet in gecis_sayisi.items():
        if adet >= 2:
            kalici.append({
                "paket": pk,
                "toplam_gecis": adet,
                "farkli_istem_sayisi": len(istem_kumeleri[pk]),
            })
    kalici.sort(key=lambda r: (-r["toplam_gecis"], -r["farkli_istem_sayisi"], r["paket"]))
    return {
        "uydurma_sayisi": len(gecis_sayisi),
        "kalici_adaylar": kalici,
        "en_kalici_paket": kalici[0]["paket"] if kalici else None,
    }

def yerel_dizin_ele_gecirme_riski(adaylar, yerel_dizin):
    durumlar = ("resmi", "rezerve-yasakli", "sahipsiz")
    ortamlar = ("ci-cd", "gelistirici-yerel", "izole-kum-havuzu")
    if not isinstance(yerel_dizin, dict) or not 1 <= len(yerel_dizin) <= 50:
        raise ValueError("yerel_dizin geçersiz")
    for k, v in yerel_dizin.items():
        if not isinstance(k, str) or not k or v not in durumlar:
            raise ValueError("yerel_dizin öğesi geçersiz")

    if not isinstance(adaylar, list) or not 1 <= len(adaylar) <= 20:
        raise ValueError("adaylar geçersiz")
    gorulen = set()
    sonuc = []

    for a in adaylar:
        if not isinstance(a, dict) or set(a) != {"paket", "tekrar_orani", "hedef_ortam"}:
            raise ValueError("aday şeması geçersiz")
        pk = a["paket"]
        oran = a["tekrar_orani"]
        ortam = a["hedef_ortam"]
        if not isinstance(pk, str) or not pk or pk in gorulen:
            raise ValueError("paket geçersiz")
        if isinstance(oran, bool) or not isinstance(oran, (int, float)) or not 0.0 <= float(oran) <= 1.0:
            raise ValueError("tekrar_orani geçersiz")
        if ortam not in ortamlar:
            raise ValueError("hedef_ortam geçersiz")
        gorulen.add(pk)

        durum = yerel_dizin.get(pk, "sahipsiz")
        acik = durum == "sahipsiz"
        if not acik:
            puan = 0
            sinif = "kayit-kapali"
        else:
            agirlik = 40 if ortam == "ci-cd" else 25 if ortam == "gelistirici-yerel" else 10
            puan = round(float(oran) * 60) + agirlik
            if puan >= 75:
                sinif = "kritik-slopsquat"
            elif puan >= 45:
                sinif = "orta-slopsquat"
            else:
                sinif = "dusuk-slopsquat"

        sonuc.append({
            "paket": pk,
            "kayit_acik": acik,
            "oncelik_puani": puan,
            "risk_sinifi": sinif,
        })
    return sonuc

def otomatik_kurulum_zinciri(ajan_izleri, sahipsiz_paketler):
    if not isinstance(sahipsiz_paketler, list) or not 1 <= len(sahipsiz_paketler) <= 50:
        raise ValueError("sahipsiz_paketler geçersiz")
    sahipsiz_kume = set()
    for p in sahipsiz_paketler:
        if not isinstance(p, str) or not p or p in sahipsiz_kume:
            raise ValueError("sahipsiz paket geçersiz")
        sahipsiz_kume.add(p)

    if not isinstance(ajan_izleri, list) or not 1 <= len(ajan_izleri) <= 20:
        raise ValueError("ajan_izleri geçersiz")
    gorulen = set()
    sonuc = []

    for iz in ajan_izleri:
        if not isinstance(iz, dict) or set(iz) != {"iz_id", "paket", "kurulum_onayi", "ag_erisim", "pip_bayraklari"}:
            raise ValueError("iz şeması geçersiz")
        iid = iz["iz_id"]
        pk = iz["paket"]
        onay = iz["kurulum_onayi"]
        ag = iz["ag_erisim"]
        bayraklar = iz["pip_bayraklari"]
        if not isinstance(iid, str) or not iid or iid in gorulen:
            raise ValueError("iz_id geçersiz")
        if not isinstance(pk, str) or not pk:
            raise ValueError("paket geçersiz")
        if onay not in ("otomatik", "insan-onayli"):
            raise ValueError("kurulum_onayi geçersiz")
        if not isinstance(ag, bool):
            raise ValueError("ag_erisim geçersiz")
        if not isinstance(bayraklar, list) or len(bayraklar) > 10:
            raise ValueError("pip_bayraklari geçersiz")
        for b in bayraklar:
            if not isinstance(b, str) or not b:
                raise ValueError("bayrak geçersiz")
        gorulen.add(iid)

        if pk in sahipsiz_kume and ag and onay == "otomatik":
            tetik = True
            evre = "import-ani" if "--only-binary=:all:" in bayraklar else "kurulum-setup-py"
        else:
            tetik = False
            evre = "engellendi"

        sonuc.append({
            "iz_id": iid,
            "tetiklenir_mi": tetik,
            "tetik_evresi": evre,
        })
    return sonuc

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_41 as deney
    deney.goster(halusinasyon_tekrar_analizi, yerel_dizin_ele_gecirme_riski, otomatik_kurulum_zinciri)
```

```hint
Önceki üç görevdeki çözümlerini birleştir; canlı deneyde yerel Ollama modelinin önerdiği paketler yalnızca yerel sentetik dizin karşısında analiz edilir.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Önerilen paket, var olan paket değildir

Bir adın birden çok seed ve istemde tekrar görünmesi kalıcı halüsinasyon adayını güçlendirir. Yerel sentetik dizinde sahipsiz olması gerçek PyPI sahipliği değildir. Sonraki kurulum ya da import evresinde kodun tetiklenmesi ayrı bir sınırdır; ad önerisi tek başına kod çalıştırma değildir. Labdaki gerçek model yanıtı, sentetik sahiplik ve evre kayıtlarıyla karıştırılmaz.

| Yaygın yanlış | Doğru sınır |
|---|---|
| İsim boşsa saldırı gerçekleşmiştir | Öneri, sahiplik ve tetiklenme kanıtları ayrıdır. |

Sonraki bağlantı: ai-savunma-20. [Birincil kaynak](https://pip.pypa.io/en/stable/cli/pip_install/). Kaynak mekanizmanın ilgili API veya yöntemini açıklar; bu labın başarı oranının kanıtı yerel ham koşudur.
:::
