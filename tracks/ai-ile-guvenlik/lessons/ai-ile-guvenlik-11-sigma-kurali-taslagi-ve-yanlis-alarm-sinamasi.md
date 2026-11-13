---
id: ai-ile-guvenlik-11
title: "LLM Destekli Sigma Kuralı Taslağı ve Yanlış Alarm Sınaması"
summary: Yerel dil modelinin saldırı örneğinden ürettiği Sigma kural taslaklarını şema doğrulamasından geçir, süreç telemetrisi korpusunda yakalama (TPR) ile yanlış alarm (FPR) oranlarını ölç ve gürültülü kuralları ele.
esleme: ai-ile-guvenlik-02, ai-ile-guvenlik-12, ai-savunma-24
timeout: 300
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et
Bir olay müdahale (`IR`) sonrasında analistler yeni görülen bir saldırı komutunu yakalamak için hızla **Sigma** kuralı yazmak ister. Yerel dil modelleri örnek bir süreç oluşturma (`process_creation`) kaydından dakikalar içinde Sigma taslağı çıkarabilir; ancak model çoğu zaman ya yalnızca saldırı ikilisinin adını (`rundll32`) seçip meşru yönetim işlemlerini alarma boğar ya da joker (`*`) içeren geçersiz bir şema üretir (`pu08` ve `ai-savunma-24` derslerindeki tespit ilkelerini hatırla).

| Gerçek araç / model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Sysmon / Windows `process_creation` telemetrisini, `pySigma` derleyicisini ve yerel Ollama modelinin (`qwen3`) ürettiği Sigma taslağını | İlk üç görevde `telemetri_korpusu.jsonl` ve `aday_kurallar.json` içindeki **sentetik** kural/telemetri verilerini; son görevde canlı `ai_lab.SohbetOturumu` ile Sigma doğrulama deneyini | Yalnızca küçük bir test korpusunda `FPR = 0.0` çıkmasının, kuralın tüm kurumsal sunucu rollerinde hiç yanlış alarm üretmeyeceğini tek başına garanti edebileceğini söyleyemez |

> [!GÜVENLİK]
> **Kapsam ve dürüstlük sınırı:** İlk üç görevdeki `telemetri_korpusu.jsonl` ve `aday_kurallar.json` dosyaları **sentetik** eğitim verisidir; yalnız savunma amaçlı tespit mühendisliği (`detection engineering`) doğrulaması yapılır ve dosyalar her çalıştırmada (`setup`) yeniden kopyalanır.
:::

::: anlat Sigma şema kapısı ve korpus üzerinde TPR/FPR ölçümü üç adımda çalışır
Doğrulanabilir bir Sigma kural değerlendirme hattı üç aşamadan oluşur:

1. **Şema ve Joker Denetimi (`sigma_sema_dogrula`):** Kuralın `title`, `logsource.category`, `detection.selection`, `detection.condition` ve `level` (`low`, `medium`, `high`, `critical`) alanları doğrulanır. `selection["CommandLine|contains"]` listesinde boş dizge veya `"*"` jokeri varsa `"joker_veya_bos_secim"` hatası kaydedilir.
2. **Korpus Üzerinde TPR ve FPR Ölçümü (`kural_korpusta_olc`):** Etiketli süreç korpusunda (`"saldiri"` veya `"temiz"`) her kaydın `CommandLine` alanı küçük harfe çevrilerek `selection` parçalarının tamamını içerip içermediği kontrol edilir. Eğer `condition` içinde `"not filter"` geçiyorsa ve `filter["CommandLine|contains"]` doluysa, filtre parçalarının tamamını içeren kayıtlar alarmdan düşülür (`secim_ok and not flt_ok`).
3. **Yanlış Alarm Eşiğiyle Seçim (`aday_kurallari_sirala`):** Şeması bozuk olanlar `"gecersiz_sema"`, `fpr > azami_fpr` olanlar `"yuksek_fpr"` gerekçesiyle elenir; kalanlar arasında en yüksek `tpr` ve en düşük `fpr` değerine sahip kural seçilir.
:::

::: anlat Bulguyu sınırlı ve doğrulanabilir yaz: yüksek yakalama oranı yüksek yanlış alarmı meşrulaştırmaz
Saldırıların tamamını yakalayan (`TPR = 1.0`) ancak temiz sistem komutlarının %75'inde yanlış alarm üreten (`FPR = 0.75`) bir kural SOC analistlerini alarm yorgunluğuna sokar. Kural kabul kapısı hem şema bütünlüğünü hem de `azami_fpr` sınırını birlikte zorlamalıdır.
:::

::: tahmin Seçim ve istisna (filter) koşulunun yanlış alarma etkisini tahmin et
Aşağıdaki Python kodunun çıktısını tahmin et:

```python
komutlar = [
    ("saldiri", "rundll32.exe comsvcs.dll, MiniDump 644 lsass.dmp"),
    ("temiz", "rundll32_diag.exe comsvcs.dll MiniDump --safe-audit"),
]
secim = ["comsvcs", "minidump"]
filtre = ["--safe-audit"]

sonuclar = []
for etiket, cmd in komutlar:
    c = cmd.lower()
    eslesti = all(p in c for p in secim) and not all(f in c for f in filtre)
    sonuclar.append((etiket, eslesti))
print(sonuclar)
```

???

```cikti
[('saldiri', True), ('temiz', False)]
```

`selection` her iki komutta da eşleşir; ancak `not filter` koşulu `--safe-audit` taşıyan meşru tanı komutunu hariç tutarak yanlış alarmı önler.
:::

::: gorev 1 · Sigma kural şemasını ve joker kısıtlarını doğrula
`sigma_sema_dogrula(kural)` işlevini yaz.

Girdi ve doğrulama kuralları:
- `kural`: sözlük (`dict`) olmalı ve boş olmayan (`strip()` sonrası dolu) `str` tipinde `"kural_id"` taşımalıdır; aksi halde `ValueError` yükselt.
- Aşağıdaki eksiklikleri sırasıyla `hatalar` listesine ekle:
  - `title` boş olmayan `str` değilse `"eksik_title"`,
  - `logsource` sözlük değilse veya `logsource.get("category")` boş olmayan `str` değilse `"eksik_logsource"`,
  - `detection` sözlük değilse `"eksik_detection"`; sözlükse:
    - `detection.get("selection")` boş olmayan sözlük değilse `"eksik_selection"`,
    - `selection` sözlükse fakat `selection.get("CommandLine|contains")` boş olmayan bir `str` listesi değilse ya da elemanlarından herhangi biri boşsa veya `"*"` ise `"joker_veya_bos_secim"`,
    - `detection.get("condition")` boş olmayan `str` değilse `"eksik_condition"`,
  - `level` alanı `("low", "medium", "high", "critical")` değerlerinden biri değilse `"gecersiz_level"`.
- `{"kural_id": kural["kural_id"], "gecerli": len(hatalar) == 0, "hatalar": hatalar}` sözlüğünü döndür.

```starter
from ai_ile_guvenlik_veri import json_yukle

adaylar = json_yukle("aday_kurallar.json")

def sigma_sema_dogrula(kural):
    # HATA: logsource, selection joker kontrolü ve level denetimini atlıyor.
    return {
        "kural_id": kural.get("kural_id", ""),
        "gecerli": True,
        "hatalar": [],
    }

for a in adaylar:
    print(sigma_sema_dogrula(a))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-11")
```

```test
need("sigma_sema_dogrula")

def sozlesme(fn):
    try:
        r1 = fn({
            "kural_id": "K-1",
            "title": "Comsvcs MiniDump",
            "logsource": {"category": "process_creation"},
            "detection": {"selection": {"CommandLine|contains": ["comsvcs", "MiniDump"]}, "condition": "selection"},
            "level": "critical",
        })
        if r1 != {"kural_id": "K-1", "gecerli": True, "hatalar": []}:
            return False

        r2 = fn({
            "kural_id": "K-2",
            "title": "   ",
            "logsource": {},
            "detection": {"selection": {"CommandLine|contains": ["*"]}, "condition": ""},
            "level": "urgent",
        })
        if r2["gecerli"] is not False:
            return False
        if r2["hatalar"] != ["eksik_title", "eksik_logsource", "joker_veya_bos_secim", "eksik_condition", "gecersiz_level"]:
            return False

        r3 = fn({
            "kural_id": "K-3",
            "title": "Baslik",
            "logsource": {"category": "process_creation"},
            "detection": "bozuk",
            "level": "low",
        })
        if r3["gecerli"] is not False or r3["hatalar"] != ["eksik_detection"]:
            return False

        r4 = fn({
            "kural_id": "K-4",
            "title": "Baslik",
            "logsource": {"category": "process_creation"},
            "detection": {"selection": {}, "condition": "selection"},
            "level": "medium",
        })
        if r4["gecerli"] is not False or r4["hatalar"] != ["eksik_selection"]:
            return False

        r4b = fn({
            "kural_id": "K-4B",
            "title": "Baslik",
            "logsource": "bozuk",
            "detection": {"selection": ["bozuk"], "condition": "selection"},
            "level": 123,
        })
        if r4b["gecerli"] is not False or r4b["hatalar"] != ["eksik_logsource", "eksik_selection", "gecersiz_level"]:
            return False

        for kotu_secim in ([], "rundll32", ["  "], [123], ["lsass", "*"]):
            rk = fn({
                "kural_id": "K-5",
                "title": "Baslik",
                "logsource": {"category": "process_creation"},
                "detection": {"selection": {"CommandLine|contains": kotu_secim}, "condition": "selection"},
                "level": "high",
            })
            if rk["gecerli"] is not False or rk["hatalar"] != ["joker_veya_bos_secim"]:
                return False

        for h in (None, [], {}, {"kural_id": ""}, {"kural_id": "   "}, {"kural_id": 12}):
            try:
                fn(h)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(sigma_sema_dogrula), "sigma_sema_dogrula: şema alanları, joker kısıtı ve level kuralları doğru")
ok(not sozlesme(lambda k: {"kural_id": k["kural_id"], "gecerli": True, "hatalar": []}), "mutasyon: her kuralı geçerli sayan işlev reddedilmeli")
```

```solution
IZINLI_SEVIYELER = ("low", "medium", "high", "critical")

def _dolu_metin(deger):
    return isinstance(deger, str) and bool(deger.strip())

def sigma_sema_dogrula(kural):
    if not isinstance(kural, dict):
        raise ValueError("kural sözlük olmalı")
    kid = kural.get("kural_id")
    if not _dolu_metin(kid):
        raise ValueError("kural_id boş olmayan string olmalı")

    hatalar = []
    if not _dolu_metin(kural.get("title")):
        hatalar.append("eksik_title")

    ls = kural.get("logsource")
    if not isinstance(ls, dict) or not _dolu_metin(ls.get("category")):
        hatalar.append("eksik_logsource")

    det = kural.get("detection")
    if not isinstance(det, dict):
        hatalar.append("eksik_detection")
    else:
        sel = det.get("selection")
        if not isinstance(sel, dict) or not sel:
            hatalar.append("eksik_selection")
        else:
            parcalar = sel.get("CommandLine|contains")
            if not isinstance(parcalar, list) or not parcalar or not all(_dolu_metin(x) and x.strip() != "*" for x in parcalar):
                hatalar.append("joker_veya_bos_secim")
        if not _dolu_metin(det.get("condition")):
            hatalar.append("eksik_condition")

    seviye = kural.get("level")
    if not _dolu_metin(seviye) or seviye.strip().lower() not in IZINLI_SEVIYELER:
        hatalar.append("gecersiz_level")

    return {
        "kural_id": kid,
        "gecerli": len(hatalar) == 0,
        "hatalar": hatalar,
    }
```

```hint
`title`, `logsource.category`, `detection.selection["CommandLine|contains"]`, `detection.condition` ve `level` alanlarını sırayla kontrol et; `"*"` jokerini `"joker_veya_bos_secim"` olarak işaretle.
```
:::

::: gorev 2 · Sigma kuralını telemetri korpusunda çalıştır ve TPR/FPR ölç
`kural_korpusta_olc(kural, korpus)` işlevini yaz.

Kurallar:
- `kural` geçerli bir Sigma şemasına sahip değilse (`sigma_sema_dogrula` mantığına göre) veya `korpus` boş olmayan bir `list` değilse `ValueError` yükselt.
- Korpustaki her olay `dict` olmalı, `"etiket"` alanı `"saldiri"` veya `"temiz"` olmalı ve `"CommandLine"` alanı `str` olmalıdır; ayrıca korpusta en az bir `"saldiri"` ve en az bir `"temiz"` kayıt bulunmalıdır (aksi halde `ValueError` yükselt).
- Her olayda `CommandLine.lower()` değeri `selection["CommandLine|contains"]` içindeki tüm dizgeleri (küçük harfe çevrilmiş) içeriyorsa `secim_ok = True` olur.
- Eğer `detection["condition"].lower()` içinde `"not filter"` geçiyorsa ve `detection.get("filter", {}).get("CommandLine|contains")` dolu bir listeyse, bu listedeki tüm dizgeleri içeren kayıtlar hariç tutulur (`eslesti = secim_ok and not flt_ok`).
- `tp`, `fp`, `tn`, `fn` sayılarını ve `tpr = round(tp / (tp + fn), 4)`, `fpr = round(fp / (fp + tn), 4)` oranlarını içeren sözlüğü döndür.

```starter
import json
from ai_ile_guvenlik_veri import json_yukle, metin_yukle

adaylar = json_yukle("aday_kurallar.json")
korpus = [json.loads(s) for s in metin_yukle("telemetri_korpusu.jsonl").splitlines() if s.strip()]

def kural_korpusta_olc(kural, korpus):
    # HATA: filter istisnasını uygulamadığı için meşru tanı komutunu yanlış alarm sayıyor.
    return {
        "kural_id": kural["kural_id"],
        "tp": 0,
        "fp": 0,
        "tn": 0,
        "fn": 0,
        "tpr": 0.0,
        "fpr": 0.0,
    }

print(kural_korpusta_olc(adaylar[1], korpus))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-11")
```

```test
need("kural_korpusta_olc")

ORNEK_KORPUS = [
    {"olay_id": "p1", "CommandLine": "rundll32.exe comsvcs.dll, MiniDump 644 lsass.dmp", "etiket": "saldiri"},
    {"olay_id": "p2", "CommandLine": "rundll32.exe comsvcs.dll,MiniDump 700 dump.bin", "etiket": "saldiri"},
    {"olay_id": "p3", "CommandLine": "procdump.exe -ma lsass.exe", "etiket": "saldiri"},
    {"olay_id": "p4", "CommandLine": "rundll32.exe shell32.dll,Control_RunDLL", "etiket": "temiz"},
    {"olay_id": "p5", "CommandLine": "rundll32_diag.exe comsvcs.dll MiniDump --safe-audit", "etiket": "temiz"},
    {"olay_id": "p6", "CommandLine": "cmd.exe /c whoami", "etiket": "temiz"},
]

KURAL_GENIS = {
    "kural_id": "KG",
    "title": "Genis",
    "logsource": {"category": "process_creation"},
    "detection": {"selection": {"CommandLine|contains": ["rundll32"]}, "condition": "selection"},
    "level": "high",
}

KURAL_FILTRELI = {
    "kural_id": "KF",
    "title": "Filtreli",
    "logsource": {"category": "process_creation"},
    "detection": {
        "selection": {"CommandLine|contains": ["comsvcs", "MiniDump"]},
        "filter": {"CommandLine|contains": ["--safe-audit"]},
        "condition": "selection and not filter",
    },
    "level": "critical",
}

def sozlesme(fn):
    try:
        m1 = fn(KURAL_GENIS, ORNEK_KORPUS)
        if m1 != {"kural_id": "KG", "tp": 2, "fp": 2, "tn": 1, "fn": 1, "tpr": 0.6667, "fpr": 0.6667}:
            return False

        m2 = fn(KURAL_FILTRELI, ORNEK_KORPUS)
        if m2 != {"kural_id": "KF", "tp": 2, "fp": 0, "tn": 3, "fn": 1, "tpr": 0.6667, "fpr": 0.0}:
            return False

        m2_kapali_flt = fn({
            "kural_id": "KF-KAPALI",
            "title": "Filtre kosulda yok",
            "logsource": {"category": "process_creation"},
            "detection": {
                "selection": {"CommandLine|contains": ["comsvcs", "MiniDump"]},
                "filter": {"CommandLine|contains": ["--safe-audit"]},
                "condition": "selection",
            },
            "level": "high",
        }, ORNEK_KORPUS)
        if m2_kapali_flt["fp"] != 1:
            return False

        m2_bos_flt = fn({
            "kural_id": "KF-BOS",
            "title": "Bos filtre listesi",
            "logsource": {"category": "process_creation"},
            "detection": {
                "selection": {"CommandLine|contains": ["comsvcs", "MiniDump"]},
                "filter": {"CommandLine|contains": []},
                "condition": "selection and not filter",
            },
            "level": "high",
        }, ORNEK_KORPUS)
        if m2_bos_flt["tp"] != 2 or m2_bos_flt["fp"] != 1:
            return False

        for k_in, c_in in [
            (None, ORNEK_KORPUS),
            ({"kural_id": "X"}, ORNEK_KORPUS),
            (KURAL_FILTRELI, None),
            (KURAL_FILTRELI, 123),
            (KURAL_FILTRELI, "liste_degil"),
            (KURAL_FILTRELI, []),
            (KURAL_FILTRELI, ["bozuk"]),
            (KURAL_FILTRELI, [{"olay_id": "p1", "CommandLine": "a", "etiket": "saldiri"}]),
            (KURAL_FILTRELI, [{"olay_id": "p1", "CommandLine": "a", "etiket": "temiz"}]),
            (KURAL_FILTRELI, [{"olay_id": "p1", "CommandLine": "a", "etiket": "bilinmeyen"}, {"olay_id": "p2", "CommandLine": "b", "etiket": "temiz"}]),
            (KURAL_FILTRELI, ORNEK_KORPUS + [{"olay_id": "px", "CommandLine": "b", "etiket": "bilinmeyen"}]),
            (KURAL_FILTRELI, [{"olay_id": "p1", "CommandLine": 123, "etiket": "saldiri"}, {"olay_id": "p2", "CommandLine": "b", "etiket": "temiz"}]),
        ]:
            try:
                fn(k_in, c_in)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(kural_korpusta_olc), "kural_korpusta_olc: selection ve not filter kurallarıyla TP/FP/TN/FN ve TPR/FPR hesabı doğru")
ok(not sozlesme(lambda k, c: {"kural_id": "KF", "tp": 2, "fp": 0, "tn": 3, "fn": 1, "tpr": 0.6667, "fpr": 0.0}), "mutasyon: sabit metrik döndüren işlev reddedilmeli")
```

```solution
from ai_gercek_ai_ile_guvenlik_11 import sigma_sema_dogrula_referans as _sema_dogrula

def kural_korpusta_olc(kural, korpus):
    sema = _sema_dogrula(kural)
    if not sema["gecerli"]:
        raise ValueError("geçersiz Sigma şeması")
    if not isinstance(korpus, list) or not korpus:
        raise ValueError("korpus boş olmayan liste olmalı")

    det = kural["detection"]
    secim = [s.lower() for s in det["selection"]["CommandLine|contains"]]
    flt_blok = det.get("filter")
    flt_liste = [s.lower() for s in flt_blok.get("CommandLine|contains", [])] if isinstance(flt_blok, dict) else []
    flt_aktif = "not filter" in det["condition"].lower()

    saldiri_eslesmeleri = []
    temiz_eslesmeleri = []
    for olay in korpus:
        if not isinstance(olay, dict):
            raise ValueError("olay sözlük olmalı")
        etiket = olay.get("etiket")
        cmd_ham = olay.get("CommandLine")
        if etiket not in ("saldiri", "temiz") or not isinstance(cmd_ham, str):
            raise ValueError("geçersiz olay kaydı")
        cmd = cmd_ham.lower()
        secim_ok = all(p in cmd for p in secim)
        flt_ok = bool(flt_liste) and all(p in cmd for p in flt_liste) if flt_aktif else False
        eslesti = secim_ok and not flt_ok
        if etiket == "saldiri":
            saldiri_eslesmeleri.append(eslesti)
        else:
            temiz_eslesmeleri.append(eslesti)

    if not saldiri_eslesmeleri or not temiz_eslesmeleri:
        raise ValueError("korpusta hem saldiri hem temiz kayıt bulunmalı")

    tp = len([x for x in saldiri_eslesmeleri if x])
    fn = len([x for x in saldiri_eslesmeleri if not x])
    fp = len([x for x in temiz_eslesmeleri if x])
    tn = len([x for x in temiz_eslesmeleri if not x])

    return {
        "kural_id": kural["kural_id"],
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "tpr": round(tp / len(saldiri_eslesmeleri), 4),
        "fpr": round(fp / len(temiz_eslesmeleri), 4),
    }
```

```hint
`selection["CommandLine|contains"]` içindeki her alt dizgenin `CommandLine.lower()` içinde geçip geçmediğini kontrol et; `"not filter"` varsa `filter["CommandLine|contains"]` eşleşmelerini alarmdan çıkar.
```
:::

::: gorev 3 · Yanlış alarm eşiğine göre en iyi Sigma kuralını seç
`aday_kurallari_sirala(adaylar, korpus, azami_fpr)` işlevini yaz.

Kurallar:
- `adaylar` boş olmayan bir `list` olmalı, `azami_fpr` ise `0.0 <= azami_fpr <= 1.0` aralığında sayısal (`int` veya `float`, `bool` hariç) olmalıdır; aksi halde `ValueError` yükselt.
- Her adayı önce şema doğrulamasından geçir:
  - Şeması geçersiz olanları `elenen_kurallar[kural_id] = "gecersiz_sema"` olarak kaydet.
  - Şeması geçerli olanları `kural_korpusta_olc` ile ölç; `fpr > azami_fpr` olanları `elenen_kurallar[kural_id] = "yuksek_fpr"` olarak kaydet.
- Kalan uygun kuralları `(-tpr, fpr, kural_id)` anahtarına göre sırala ve ilkini `secilen_kural_id` olarak seç (uygun kural yoksa `None`).
- `{"secilen_kural_id": secilen_kural_id, "uygun_sayisi": len(uygunlar), "elenen_kurallar": elenen_kurallar}` sözlüğünü döndür.

```starter
import json
from ai_ile_guvenlik_veri import json_yukle, metin_yukle

adaylar = json_yukle("aday_kurallar.json")
korpus = [json.loads(s) for s in metin_yukle("telemetri_korpusu.jsonl").splitlines() if s.strip()]

def aday_kurallari_sirala(adaylar, korpus, azami_fpr):
    # HATA: Şema ve FPR kapısını uygulamadan ilk adayı seçiyor.
    return {
        "secilen_kural_id": adaylar[0]["kural_id"],
        "uygun_sayisi": len(adaylar),
        "elenen_kurallar": {},
    }

print(aday_kurallari_sirala(adaylar, korpus, 0.1))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-11")
```

```test
need("aday_kurallari_sirala")
import json
from ai_ile_guvenlik_veri import json_yukle, metin_yukle

ADAYLAR = json_yukle("aday_kurallar.json")
KORPUS = [json.loads(s) for s in metin_yukle("telemetri_korpusu.jsonl").splitlines() if s.strip()]

def sozlesme(fn):
    try:
        r = fn(ADAYLAR, KORPUS, 0.0)
        if r != {
            "secilen_kural_id": "SIG-ADAY-B",
            "uygun_sayisi": 1,
            "elenen_kurallar": {
                "SIG-ADAY-A": "yuksek_fpr",
                "SIG-ADAY-C": "gecersiz_sema",
            },
        }:
            return False

        r_tam_esik = fn([ADAYLAR[0]], KORPUS, 0.75)
        if r_tam_esik["secilen_kural_id"] != "SIG-ADAY-A" or r_tam_esik["uygun_sayisi"] != 1:
            return False

        r_ust_sinir = fn([ADAYLAR[0]], KORPUS, 1.0)
        if r_ust_sinir["secilen_kural_id"] != "SIG-ADAY-A":
            return False

        r_bos = fn([ADAYLAR[0], ADAYLAR[2]], KORPUS, 0.2)
        if r_bos["secilen_kural_id"] is not None or r_bos["uygun_sayisi"] != 0:
            return False

        k_dar = {
            "kural_id": "SIG-ADAY-DAR",
            "title": "Tek saldiri yakalayan dar kural",
            "logsource": {"category": "process_creation"},
            "detection": {"selection": {"CommandLine|contains": ["comsvcs", "lsass.dmp"]}, "condition": "selection"},
            "level": "high",
        }
        r_tpr = fn([k_dar, ADAYLAR[1]], KORPUS, 0.2)
        if r_tpr["secilen_kural_id"] != "SIG-ADAY-B" or r_tpr["uygun_sayisi"] != 2:
            return False

        for a_in, f_in in [
            (None, 0.1),
            ("liste_degil", 0.1),
            (tuple(ADAYLAR), 0.1),
            ([], 0.1),
            (ADAYLAR, "0.1"),
            (ADAYLAR, True),
            (ADAYLAR, float("nan")),
            (ADAYLAR, -0.01),
            (ADAYLAR, 1.01),
        ]:
            try:
                fn(a_in, KORPUS, f_in)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(aday_kurallari_sirala), "aday_kurallari_sirala: şema ve FPR kapısıyla en uygun Sigma kuralı seçildi")
ok(not sozlesme(lambda a, k, f: {"secilen_kural_id": "SIG-ADAY-A", "uygun_sayisi": 1, "elenen_kurallar": {}}), "mutasyon: yüksek FPR'li kuralı seçen işlev reddedilmeli")
```

```solution
import math
from ai_gercek_ai_ile_guvenlik_11 import (
    kural_korpusta_olc_referans as _korpus_olc,
    sigma_sema_dogrula_referans as _sema_dogrula,
)

def aday_kurallari_sirala(adaylar, korpus, azami_fpr):
    if not isinstance(adaylar, list) or not adaylar:
        raise ValueError("adaylar boş olmayan liste olmalı")
    if isinstance(azami_fpr, bool) or not isinstance(azami_fpr, (int, float)) or not math.isfinite(azami_fpr):
        raise ValueError("azami_fpr sayısal olmalı")
    if not (0.0 <= float(azami_fpr) <= 1.0):
        raise ValueError("azami_fpr aralık dışında")

    uygunlar = []
    elenenler = {}
    for kural in adaylar:
        sema = _sema_dogrula(kural)
        kid = sema["kural_id"]
        if not sema["gecerli"]:
            elenenler[kid] = "gecersiz_sema"
            continue
        m = _korpus_olc(kural, korpus)
        if m["fpr"] > azami_fpr:
            elenenler[kid] = "yuksek_fpr"
            continue
        uygunlar.append(m)

    uygunlar.sort(key=lambda x: (-x["tpr"], x["fpr"], x["kural_id"]))
    secilen = uygunlar[0]["kural_id"] if uygunlar else None
    return {
        "secilen_kural_id": secilen,
        "uygun_sayisi": len(uygunlar),
        "elenen_kurallar": elenenler,
    }
```

```hint
Şeması geçersiz kuralları `"gecersiz_sema"`, `fpr > azami_fpr` olanları `"yuksek_fpr"` ile `elenen_kurallar` sözlüğüne ekle; kalanları `(-tpr, fpr, kural_id)` ile sırala.
```
:::

::: gorev Gerçek deney · Yerel modelle Sigma kuralı üret ve korpusta yanlış alarm sınaması yap
Önceki üç görevde yazdığın `sigma_sema_dogrula`, `kural_korpusta_olc` ve `aday_kurallari_sirala` işlevlerini bu adımda birleştir.

Canlı deneyde:
1. Süreç oluşturma korpusu yerel Ollama modeline (`ai_lab.SohbetOturumu`) verilerek `comsvcs.dll, MiniDump` saldırısını yakalayan ve `--safe-audit` tanı aracını hariç tutan Sigma mantığı özetletilir.
2. Geniş kural (`SIG-ADAY-A`), filtreli kural (`SIG-ADAY-B`) ve bozuk şemalı kural (`SIG-ADAY-C`) senin yazdığın değerlendirme hattından geçirilir.
3. Yalnızca şeması geçerli ve yanlış alarm oranı eşik altında kalan `SIG-ADAY-B` kuralının seçildiği doğrulanır.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def sigma_sema_dogrula(kural):
    return {}

def kural_korpusta_olc(kural, korpus):
    return {}

def aday_kurallari_sirala(adaylar, korpus, azami_fpr):
    return {}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_ile_guvenlik_11 as deney
    deney.goster(sigma_sema_dogrula, kural_korpusta_olc, aday_kurallari_sirala)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-11")
```

```test
import ai_lab
from sandbox import ai_gercek_ai_ile_guvenlik_11 as D

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for ad in ("sigma_sema_dogrula", "kural_korpusta_olc", "aday_kurallari_sirala"):
    need(ad)

sorun = ai_lab.kod_denetimi(
    src,
    ("sigma_sema_dogrula_referans", "kural_korpusta_olc_referans", "aday_kurallari_sirala_referans"),
)
ok(not sorun, "laboratuvar yamalanmamalı, referans işlevler çağrılmamalı")

def _on_sozlesme():
    try:
        r1 = sigma_sema_dogrula({
            "kural_id": "K-1",
            "title": "Comsvcs MiniDump",
            "logsource": {"category": "process_creation"},
            "detection": {"selection": {"CommandLine|contains": ["comsvcs", "MiniDump"]}, "condition": "selection"},
            "level": "critical",
        })
        if r1 != {"kural_id": "K-1", "gecerli": True, "hatalar": []}:
            return False
        r2 = sigma_sema_dogrula({
            "kural_id": "K-2",
            "title": "   ",
            "logsource": {},
            "detection": {"selection": {"CommandLine|contains": ["*"]}, "condition": ""},
            "level": "urgent",
        })
        if r2["gecerli"] is not False or r2["hatalar"] != ["eksik_title", "eksik_logsource", "joker_veya_bos_secim", "eksik_condition", "gecersiz_level"]:
            return False
        r3 = sigma_sema_dogrula({"kural_id": "K-3", "title": "B", "logsource": {"category": "p"}, "detection": "bozuk", "level": "low"})
        if r3["gecerli"] is not False or r3["hatalar"] != ["eksik_detection"]:
            return False
        r4 = sigma_sema_dogrula({"kural_id": "K-4", "title": "B", "logsource": "bozuk", "detection": {"selection": ["bozuk"], "condition": "selection"}, "level": 123})
        if r4["gecerli"] is not False or r4["hatalar"] != ["eksik_logsource", "eksik_selection", "gecersiz_level"]:
            return False
        if sigma_sema_dogrula({"kural_id": "K-4C", "title": "B", "logsource": {"category": "p"}, "detection": {"selection": {}, "condition": "selection"}, "level": "low"})["hatalar"] != ["eksik_selection"]:
            return False
        for kotu_secim in ([], "rundll32", ["  "], [123], ["lsass", "*"]):
            rk = sigma_sema_dogrula({"kural_id": "K-5", "title": "B", "logsource": {"category": "p"}, "detection": {"selection": {"CommandLine|contains": kotu_secim}, "condition": "selection"}, "level": "high"})
            if rk["gecerli"] is not False or rk["hatalar"] != ["joker_veya_bos_secim"]:
                return False
        for h in (None, [], {}, {"kural_id": ""}, {"kural_id": "   "}, {"kural_id": 12}):
            try:
                sigma_sema_dogrula(h)
                return False
            except ValueError:
                pass

        _kp = [
            {"olay_id": "p1", "CommandLine": "rundll32.exe comsvcs.dll, MiniDump 644 lsass.dmp", "etiket": "saldiri"},
            {"olay_id": "p2", "CommandLine": "rundll32.exe comsvcs.dll,MiniDump 700 dump.bin", "etiket": "saldiri"},
            {"olay_id": "p3", "CommandLine": "procdump.exe -ma lsass.exe", "etiket": "saldiri"},
            {"olay_id": "p4", "CommandLine": "rundll32.exe shell32.dll,Control_RunDLL", "etiket": "temiz"},
            {"olay_id": "p5", "CommandLine": "rundll32_diag.exe comsvcs.dll MiniDump --safe-audit", "etiket": "temiz"},
            {"olay_id": "p6", "CommandLine": "cmd.exe /c whoami", "etiket": "temiz"},
        ]
        _kg = {"kural_id": "KG", "title": "G", "logsource": {"category": "p"}, "detection": {"selection": {"CommandLine|contains": ["rundll32"]}, "condition": "selection"}, "level": "high"}
        _kf = {"kural_id": "KF", "title": "F", "logsource": {"category": "p"}, "detection": {"selection": {"CommandLine|contains": ["comsvcs", "MiniDump"]}, "filter": {"CommandLine|contains": ["--safe-audit"]}, "condition": "selection and not filter"}, "level": "critical"}
        if kural_korpusta_olc(_kg, _kp) != {"kural_id": "KG", "tp": 2, "fp": 2, "tn": 1, "fn": 1, "tpr": 0.6667, "fpr": 0.6667}:
            return False
        if kural_korpusta_olc(_kf, _kp) != {"kural_id": "KF", "tp": 2, "fp": 0, "tn": 3, "fn": 1, "tpr": 0.6667, "fpr": 0.0}:
            return False
        if kural_korpusta_olc({"kural_id": "KF2", "title": "F", "logsource": {"category": "p"}, "detection": {"selection": {"CommandLine|contains": ["comsvcs", "MiniDump"]}, "filter": {"CommandLine|contains": ["--safe-audit"]}, "condition": "selection"}, "level": "high"}, _kp)["fp"] != 1:
            return False
        if kural_korpusta_olc({"kural_id": "KF3", "title": "F", "logsource": {"category": "p"}, "detection": {"selection": {"CommandLine|contains": ["comsvcs", "MiniDump"]}, "filter": {"CommandLine|contains": []}, "condition": "selection and not filter"}, "level": "high"}, _kp)["fp"] != 1:
            return False
        for k_in, c_in in [
            (D.ADAY_KURALLAR[2], D.KORPUS), (D.ADAY_KURALLAR[1], None), (D.ADAY_KURALLAR[1], "x"), (D.ADAY_KURALLAR[1], tuple(D.KORPUS)), (D.ADAY_KURALLAR[1], []),
            (D.ADAY_KURALLAR[1], ["bozuk"]), (D.ADAY_KURALLAR[1], [_kp[0]]), (D.ADAY_KURALLAR[1], [_kp[3]]),
            (D.ADAY_KURALLAR[1], _kp + [{"olay_id": "px", "CommandLine": "b", "etiket": "bilinmeyen"}]),
            (D.ADAY_KURALLAR[1], [{"olay_id": "p1", "CommandLine": 123, "etiket": "saldiri"}, _kp[3]]),
        ]:
            try:
                kural_korpusta_olc(k_in, c_in)
                return False
            except ValueError:
                pass

        if aday_kurallari_sirala(D.ADAY_KURALLAR, D.KORPUS, 0.0) != {"secilen_kural_id": "SIG-ADAY-B", "uygun_sayisi": 1, "elenen_kurallar": {"SIG-ADAY-A": "yuksek_fpr", "SIG-ADAY-C": "gecersiz_sema"}}:
            return False
        if aday_kurallari_sirala([_kg], _kp, 0.6667)["secilen_kural_id"] != "KG":
            return False
        if aday_kurallari_sirala([D.ADAY_KURALLAR[0]], D.KORPUS, 1.0)["secilen_kural_id"] != "SIG-ADAY-A":
            return False
        if aday_kurallari_sirala([D.ADAY_KURALLAR[0], D.ADAY_KURALLAR[2]], D.KORPUS, 0.2)["secilen_kural_id"] is not None:
            return False
        _kdar = {"kural_id": "SIG-ADAY-DAR", "title": "Dar", "logsource": {"category": "p"}, "detection": {"selection": {"CommandLine|contains": ["comsvcs", "lsass.dmp"]}, "condition": "selection"}, "level": "high"}
        if aday_kurallari_sirala([_kdar, _kf], _kp, 0.2)["secilen_kural_id"] != "KF":
            return False
        for a_in, f_in in [(None, 0.1), ("x", 0.1), (tuple(D.ADAY_KURALLAR), 0.1), ([], 0.1), (D.ADAY_KURALLAR, "0.1"), (D.ADAY_KURALLAR, True), (D.ADAY_KURALLAR, float("nan")), (D.ADAY_KURALLAR, -0.1), (D.ADAY_KURALLAR, 1.2)]:
            try:
                aday_kurallari_sirala(a_in, D.KORPUS, f_in)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(_on_sozlesme(), "sentetik ön kontrol: Sigma şema ve TPR/FPR kapısı kuralları tam")

if not all(checks):
    stop()

try:
    r = D.deney(sigma_sema_dogrula, kural_korpusta_olc, aday_kurallari_sirala)
except Exception as e:
    ok(False, f"GERÇEK SIGMA KURAL DOĞRULAMA DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

for ad, deger in r["kontroller"].items():
    ok(deger, "gerçek deney: " + ad)

ai_lab.kanit_yaz("ile-guvenlik-11-sigma", {
    "kaynak": "gercek",
    "kabul": all(checks),
    "ders": "ai-ile-guvenlik-11",
    "ortam": r["ortam"],
    "ayarlar": r["ayarlar"],
    "deney": r,
    "ozet": r["ozet"],
})
o = r["ozet"]
ok(
    True,
    f"BULGU ({o['model']}): secilen={o['secilen_kural']}, elenen={o['elenen_kurallar']}.",
)
```

```solution
import ai_lab
import math

IZINLI_SEVIYELER = ("low", "medium", "high", "critical")

def _dolu_metin(deger):
    return isinstance(deger, str) and bool(deger.strip())

def sigma_sema_dogrula(kural):
    if not isinstance(kural, dict):
        raise ValueError("kural sözlük olmalı")
    kid = kural.get("kural_id")
    if not _dolu_metin(kid):
        raise ValueError("kural_id boş olmayan string olmalı")

    hatalar = []
    if not _dolu_metin(kural.get("title")):
        hatalar.append("eksik_title")

    ls = kural.get("logsource")
    if not isinstance(ls, dict) or not _dolu_metin(ls.get("category")):
        hatalar.append("eksik_logsource")

    det = kural.get("detection")
    if not isinstance(det, dict):
        hatalar.append("eksik_detection")
    else:
        sel = det.get("selection")
        if not isinstance(sel, dict) or not sel:
            hatalar.append("eksik_selection")
        else:
            parcalar = sel.get("CommandLine|contains")
            if not isinstance(parcalar, list) or not parcalar or not all(_dolu_metin(x) and x.strip() != "*" for x in parcalar):
                hatalar.append("joker_veya_bos_secim")
        if not _dolu_metin(det.get("condition")):
            hatalar.append("eksik_condition")

    seviye = kural.get("level")
    if not _dolu_metin(seviye) or seviye.strip().lower() not in IZINLI_SEVIYELER:
        hatalar.append("gecersiz_level")

    return {
        "kural_id": kid,
        "gecerli": len(hatalar) == 0,
        "hatalar": hatalar,
    }

def kural_korpusta_olc(kural, korpus):
    sema = sigma_sema_dogrula(kural)
    if not sema["gecerli"]:
        raise ValueError("geçersiz Sigma şeması")
    if not isinstance(korpus, list) or not korpus:
        raise ValueError("korpus boş olmayan liste olmalı")

    det = kural["detection"]
    secim = [s.lower() for s in det["selection"]["CommandLine|contains"]]
    flt_blok = det.get("filter")
    flt_liste = [s.lower() for s in flt_blok.get("CommandLine|contains", [])] if isinstance(flt_blok, dict) else []
    flt_aktif = "not filter" in det["condition"].lower()

    saldiri_eslesmeleri = []
    temiz_eslesmeleri = []
    for olay in korpus:
        if not isinstance(olay, dict):
            raise ValueError("olay sözlük olmalı")
        etiket = olay.get("etiket")
        cmd_ham = olay.get("CommandLine")
        if etiket not in ("saldiri", "temiz") or not isinstance(cmd_ham, str):
            raise ValueError("geçersiz olay kaydı")
        cmd = cmd_ham.lower()
        secim_ok = all(p in cmd for p in secim)
        flt_ok = bool(flt_liste) and all(p in cmd for p in flt_liste) if flt_aktif else False
        eslesti = secim_ok and not flt_ok
        if etiket == "saldiri":
            saldiri_eslesmeleri.append(eslesti)
        else:
            temiz_eslesmeleri.append(eslesti)

    if not saldiri_eslesmeleri or not temiz_eslesmeleri:
        raise ValueError("korpusta hem saldiri hem temiz kayıt bulunmalı")

    tp = len([x for x in saldiri_eslesmeleri if x])
    fn = len([x for x in saldiri_eslesmeleri if not x])
    fp = len([x for x in temiz_eslesmeleri if x])
    tn = len([x for x in temiz_eslesmeleri if not x])

    return {
        "kural_id": kural["kural_id"],
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "tpr": round(tp / len(saldiri_eslesmeleri), 4),
        "fpr": round(fp / len(temiz_eslesmeleri), 4),
    }

def aday_kurallari_sirala(adaylar, korpus, azami_fpr):
    if not isinstance(adaylar, list) or not adaylar:
        raise ValueError("adaylar boş olmayan liste olmalı")
    if isinstance(azami_fpr, bool) or not isinstance(azami_fpr, (int, float)) or not math.isfinite(azami_fpr):
        raise ValueError("azami_fpr sayısal olmalı")
    if not (0.0 <= float(azami_fpr) <= 1.0):
        raise ValueError("azami_fpr aralık dışında")

    uygunlar = []
    elenenler = {}
    for kural in adaylar:
        sema = sigma_sema_dogrula(kural)
        kid = sema["kural_id"]
        if not sema["gecerli"]:
            elenenler[kid] = "gecersiz_sema"
            continue
        m = kural_korpusta_olc(kural, korpus)
        if m["fpr"] > azami_fpr:
            elenenler[kid] = "yuksek_fpr"
            continue
        uygunlar.append(m)

    uygunlar.sort(key=lambda x: (-x["tpr"], x["fpr"], x["kural_id"]))
    secilen = uygunlar[0]["kural_id"] if uygunlar else None
    return {
        "secilen_kural_id": secilen,
        "uygun_sayisi": len(uygunlar),
        "elenen_kurallar": elenenler,
    }

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_ile_guvenlik_11 as deney
    deney.goster(sigma_sema_dogrula, kural_korpusta_olc, aday_kurallari_sirala)
```

```hint
Önceki üç görevdeki `sigma_sema_dogrula`, `kural_korpusta_olc` ve `aday_kurallari_sirala` işlevlerini birleştir.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Hızlı taslak, gürültülü seçim riski (30 sn).** "Dil modeli tek bir saldırı komutundan saniyeler içinde Sigma taslağı çıkarabilir; ancak yalnız ikili adını (`rundll32`) seçen ya da `*` jokeri koyan kural meşru yönetim trafiğini yanlış alarma boğar."
2. **İki aşamalı kapı: şema + korpus ölçümü (35 sn).** "Üretilen her taslak önce zorunlu Sigma alanları ve joker yasağıyla şema kapısından geçer, ardından etiketli süreç telemetrisinde `TPR` ve `FPR` ölçülerek `azami_fpr` tavanını aşan adaylar elenir."
3. **İstisna (`not filter`) ve kaçınma sınırı (30 sn).** "Meşru bakım komutlarını `filter` bloğuyla dışlamak yanlış alarmı düşürür; fakat aşırı geniş filtre saldırgana aynı dizgeyi komutuna ekleyip kuralı atlatma (`evasion`) penceresi açabilir."
4. **Soru (25 sn).** "Üretim SIEM'ine geçmeden önce korpusta `FPR = 0` çıkan bir LLM Sigma taslağını neden önce sessiz gölge kipte (`canary / audit mode`) koşturmalısın?"
:::
