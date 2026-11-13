---
id: ai-guvence-15
title: Veri Ayıklama Yöntemlerinin Kanıt Değeri
summary: Ayıklama kararlarını karışıklık matrisiyle say; tespit, yanlış alarm ve veri kaybı oranlarını karşılaştır.
esleme: ai-guvence-12, ai-guvence-13, ai-guvence-14
timeout: 45
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et: Ayıklama kararı dört sonuçtan oluşur
Zehirli olduğu bilinen kayıtlarda ayıklanan zehirli kayıt TP, ayıklanan temiz kayıt FP, korunan temiz kayıt TN ve korunan zehirli kayıt FN olur. Kimlik listesi sayımlarla birlikte tutulursa hangi kayıtların kaybedildiği denetlenebilir.

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Cleanlab gibi araçlar çapraz doğrulamalı olasılıklarla şüpheli etiketleri işaretler; kNN tutarlılığı veya anomali dedektörleri de ayıklama adayı üretir. Gerçek değerlendirmede zehirli olduğu bilinen kayıtlarla her yöntemin TP/FP/TN/FN sayıları raporlanır | İlk üç görevde `veri/ayiklama_kayitlari.json`, `veri/sayimlar.json` ve `veri/yontem_sonuclari.json` içindeki **sentetik** kararlar ve sayımlar; son görevde etiketlerinin yüzde onu bilerek çevrilmiş bir veri kümesinde `scikit-learn` ile canlı çalışan dört ayıklama yöntemi | Tek veri kümesi ve tek zehirleme türündeki sıralama, başka veri, model veya saldırı (ör. tetikleyicili zehirleme) için genel bir "en iyi ayıklama yöntemi" vermez |

> [!NOT]
> İlk üç görevde çalışma dizinine kopyalanan `veri/` dosyaları **sentetik** eğitim örnekleridir. Her çalıştırmada yeniden kopyalanır; çalıştırmalar arasında **kalıcılık yoktur**. Son adımdaki **Gerçek deney** görevinde yazdığın üç işlev canlı ayıklama kararlarıyla sınanır.
:::

::: anlat Yüksek tespit tek başına iyi ayıklama demek değildir
Tespit oranı `TP/(TP+FN)`, yanlış alarm oranı `FP/(FP+TN)`, veri kaybı ise ayıklanan bütün kayıtların toplam içindeki payıdır. Bir yöntem her şeyi ayıklayarak tespiti bire çıkarabilir; ancak veri kaybını da en üst düzeye çıkarır.

Paydası sıfır olan oran bu derste `0.0` olarak raporlanır ve bu durum ayrıca yorumlanmalıdır. Yöntem seçiminde önce veri kaybı üst sınırı uygulanır; kalanlarda en yüksek tespit, eşitlikte en düşük yanlış alarm ve alfabetik yöntem adı seçilir. Bu sıralama yalnız verilen fixture deneyini özetler.
:::

::: tahmin Tespit ve yanlış alarmı tahmin et
Üç çıktı satırını yaz:

```python
print(round(2 / (2 + 1), 6))
print(round(1 / (1 + 3), 6))
print(max([("a", 0.6), ("b", 0.8)], key=lambda x: x[1])[0])
```

???

```cikti
0.666667
0.25
b
```

İlk satır tespit oranını, ikinci satır yanlış alarmı, üçüncü satır daha yüksek tespitli yöntemi gösterir.
:::

::: gorev 1 · Ayıklama kararlarını say
`ayiklama_kararlari(kayitlar)` işlevini yaz. Kayıtlar boş olmayan listedir; her kayıt tam olarak `id`, `gercek_zehirli`, `ayiklandi` alanlarını taşır. Kimlik 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren, yinelenmeyen stringdir. Diğer iki alan bool olmalıdır. Geçersiz veride `ValueError` yükselt.

`{"tp":N,"fp":N,"tn":N,"fn":N,"ayiklanan_idler":[ID,...]}` döndür. Ayıklanan kimlikleri sırala ve girdiyi değiştirme.

```starter
from ai_guvence_veri import json_yukle

def ayiklama_kararlari(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: ayıklanan temiz kaydı FN, korunan zehirli kaydı FP sayıyor; kimlikleri sıralamıyor!
    return {
        "tp": sum(1 for x in kayitlar if x["gercek_zehirli"] and x["ayiklandi"]),
        "fp": sum(1 for x in kayitlar if x["gercek_zehirli"] and not x["ayiklandi"]),
        "tn": sum(1 for x in kayitlar if not x["gercek_zehirli"] and not x["ayiklandi"]),
        "fn": sum(1 for x in kayitlar if not x["gercek_zehirli"] and x["ayiklandi"]),
        "ayiklanan_idler": [x["id"] for x in kayitlar if x["ayiklandi"]],
    }

print(ayiklama_kararlari(json_yukle("veri/ayiklama_kayitlari.json")["kayitlar"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-15")
```

```test
import copy
K = [
    {"id": "r-1", "gercek_zehirli": True, "ayiklandi": True},
    {"id": "r-2", "gercek_zehirli": False, "ayiklandi": True},
    {"id": "r-3", "gercek_zehirli": False, "ayiklandi": False},
    {"id": "r-4", "gercek_zehirli": True, "ayiklandi": False},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K) != {"tp": 1, "fp": 1, "tn": 1, "fn": 1, "ayiklanan_idler": ["r-1", "r-2"]} or K != once:
            return False
        sinir = fn([{"id": "a" * 64, "gercek_zehirli": False, "ayiklandi": False}])
        if sinir != {"tp": 0, "fp": 0, "tn": 1, "fn": 0, "ayiklanan_idler": []}:
            return False
        if fn([{"id": "z1", "gercek_zehirli": True, "ayiklandi": True}, {"id": "z2", "gercek_zehirli": True, "ayiklandi": True}, {"id": "z3", "gercek_zehirli": True, "ayiklandi": False}]) != {"tp": 2, "fp": 0, "tn": 0, "fn": 1, "ayiklanan_idler": ["z1", "z2"]}:
            return False
        for kayitlar in [
            None, {}, tuple(K), [], [None], [dict(K[0], ek=1)], [K[0], K[0]],
            [dict(K[0], id="")], [dict(K[0], id="a b")], [dict(K[0], id="a" * 65)], [dict(K[0], id=None)],
            [dict(K[0], gercek_zehirli=1)], [dict(K[0], gercek_zehirli="true")], [dict(K[0], gercek_zehirli=None)],
            [dict(K[0], ayiklandi=1)], [dict(K[0], ayiklandi="true")], [dict(K[0], ayiklandi=None)],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(ayiklama_kararlari), "dört karar türü, kimlikler ve ayıklama listesi korunmalı")
def m_gercek(kayitlar):
    return ayiklama_kararlari([dict(x, gercek_zehirli=False) for x in kayitlar])
def m_karar(kayitlar):
    return ayiklama_kararlari([dict(x, ayiklandi=False) for x in kayitlar])
def m_id(kayitlar):
    return ayiklama_kararlari([dict(x, id="r") for x in kayitlar])
for ad, mutant in [("gerçek durumu silen", m_gercek), ("kararları silen", m_karar), ("kimlikleri birleştiren", m_id)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def ayiklama_kararlari(kayitlar):
    import re
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    if not kayitlar:
        raise ValueError("kayıtlar boş olamaz")
    idler = set()
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"id", "gercek_zehirli", "ayiklandi"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["id"], str):
            raise ValueError("kimlik string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
            raise ValueError("kimlik geçersiz")
        if kayit["id"] in idler:
            raise ValueError("kimlik yinelenemez")
        if not isinstance(kayit["gercek_zehirli"], bool):
            raise ValueError("gerçek durum bool olmalı")
        if not isinstance(kayit["ayiklandi"], bool):
            raise ValueError("ayıklama kararı bool olmalı")
        idler.add(kayit["id"])
    return {
        "tp": sum(1 for x in kayitlar if x["gercek_zehirli"] and x["ayiklandi"]),
        "fp": sum(1 for x in kayitlar if not x["gercek_zehirli"] and x["ayiklandi"]),
        "tn": sum(1 for x in kayitlar if not x["gercek_zehirli"] and not x["ayiklandi"]),
        "fn": sum(1 for x in kayitlar if x["gercek_zehirli"] and not x["ayiklandi"]),
        "ayiklanan_idler": sorted(x["id"] for x in kayitlar if x["ayiklandi"]),
    }
```

```hint
Dört sayımı ayrı üret. Gerçek durum ve ayıklama kararını her satırda birlikte kullan; listeyi yalnız ayıklananlardan oluştur.
```
:::

::: gorev 2 · Kanıt oranlarını hesapla
`ayiklama_metrikleri(sayimlar)` işlevini yaz. Sözlük tam olarak `tp`, `fp`, `tn`, `fn` alanlarını taşır; değerler bool olmayan, sıfır veya pozitif tamsayılardır ve toplamları pozitif olmalıdır. Geçersiz veride `ValueError` yükselt ve girdiyi değiştirme.

`{"toplam":N,"tespit":X,"yanlis_alarm":X,"veri_kaybi":X}` döndür. Tespit `TP/(TP+FN)`, yanlış alarm `FP/(FP+TN)`, veri kaybı `(TP+FP)/toplam` olur. Paydası sıfır olan tespit veya yanlış alarm `0.0` kabul edilir. Oranları altı ondalık basamağa yuvarla.

```starter
from ai_guvence_veri import json_yukle

def ayiklama_metrikleri(sayimlar):
    # KUSURLU BAŞLANGIÇ KODU: yanlış alarmı temiz kayıtlara değil bütün kayıtlara bölüyor; sıfır paydada çöküyor!
    toplam = sum(sayimlar.values())
    return {"toplam": toplam,
            "tespit": round(sayimlar["tp"] / (sayimlar["tp"] + sayimlar["fn"]), 6),
            "yanlis_alarm": round(sayimlar["fp"] / toplam, 6),
            "veri_kaybi": round((sayimlar["tp"] + sayimlar["fp"]) / toplam, 6)}

for ornek in json_yukle("veri/sayimlar.json")["ornekler"]:
    try:
        print(ornek["ad"], ayiklama_metrikleri(ornek["sayim"]))
    except ZeroDivisionError as hata:
        print(ornek["ad"], "çöktü:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-15")
```

```test
import copy
S = {"tp": 2, "fp": 1, "tn": 3, "fn": 1}
def sozlesme(fn):
    try:
        once = copy.deepcopy(S)
        if fn(S) != {"toplam": 7, "tespit": 0.666667, "yanlis_alarm": 0.25, "veri_kaybi": 0.428571} or S != once:
            return False
        sifir = fn({"tp": 0, "fp": 0, "tn": 2, "fn": 0})
        if sifir != {"toplam": 2, "tespit": 0.0, "yanlis_alarm": 0.0, "veri_kaybi": 0.0}:
            return False
        if fn({"tp": 1, "fp": 0, "tn": 0, "fn": 0})["yanlis_alarm"] != 0 or fn({"tp": 1, "fp": 0, "tn": 1, "fn": 0})["tespit"] != 1.0 or fn({"tp": 1, "fp": 0, "tn": 0, "fn": 1})["tespit"] != 0.5:
            return False
        if fn({"tp": 0, "fp": 1, "tn": 2, "fn": 1})["yanlis_alarm"] != 0.333333 or fn({"tp": 0, "fp": 1, "tn": 0, "fn": 1})["yanlis_alarm"] != 1.0:
            return False
        for sayimlar in [
            None, [], {}, dict(S, ek=1), {k: 0 for k in S},
            dict(S, tp=True), dict(S, tp=1.0), dict(S, tp="1"), dict(S, tp=-1), dict(S, tp=None),
            dict(S, fp=True), dict(S, fp=1.0), dict(S, fp=-1),
            dict(S, tn=True), dict(S, tn=1.0), dict(S, tn=-1),
            dict(S, fn=True), dict(S, fn=1.0), dict(S, fn=-1),
        ]:
            try:
                fn(sayimlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(ayiklama_metrikleri), "paydalar, sıfır durumları ve üç oran korunmalı")
def m_tp(sayimlar):
    return ayiklama_metrikleri(dict(sayimlar, tp=0))
def m_fp(sayimlar):
    return ayiklama_metrikleri(dict(sayimlar, fp=0))
def m_toplam(sayimlar):
    return ayiklama_metrikleri({k: 0 for k in sayimlar})
for ad, mutant in [("tespiti silen", m_tp), ("yanlış alarmı silen", m_fp), ("toplamı silen", m_toplam)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def ayiklama_metrikleri(sayimlar):
    if not isinstance(sayimlar, dict):
        raise ValueError("sayımlar sözlük olmalı")
    if set(sayimlar) != {"tp", "fp", "tn", "fn"}:
        raise ValueError("sayım şeması geçersiz")
    for alan in ("tp", "fp", "tn", "fn"):
        deger = sayimlar[alan]
        if isinstance(deger, bool):
            raise ValueError("sayım tamsayı olmalı")
        if not isinstance(deger, int):
            raise ValueError("sayım tamsayı olmalı")
        if deger < 0:
            raise ValueError("sayım negatif olamaz")
    toplam = sum(sayimlar.values())
    if toplam == 0:
        raise ValueError("toplam pozitif olmalı")
    tespit_payda = sayimlar["tp"] + sayimlar["fn"]
    alarm_payda = sayimlar["fp"] + sayimlar["tn"]
    tespit = sayimlar["tp"] / tespit_payda if tespit_payda > 0 else 0.0
    alarm = sayimlar["fp"] / alarm_payda if alarm_payda > 0 else 0.0
    kayip = (sayimlar["tp"] + sayimlar["fp"]) / toplam
    return {"toplam": toplam, "tespit": round(tespit, 6), "yanlis_alarm": round(alarm, 6), "veri_kaybi": round(kayip, 6)}
```

```hint
İki oranın paydasını ayrı hesapla. Yalnız ilgili payda sıfırsa sıfır dön; veri kaybının paydası her zaman toplam kayıttır.
```
:::

::: gorev 3 · Ayıklama yöntemlerini kanıtla seç
`yontem_karsilastir(kayitlar, kayip_ust_sinir)` işlevini yaz. Kayıtlar boş olmayan listedir; her kayıt tam olarak `yontem`, `tp`, `fp`, `tn`, `fn` alanlarını taşır. Yöntem 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren, yinelenmeyen stringdir. Sayımlar ikinci görevdeki kuralları sağlar. Veri kaybı üst sınırı bool olmayan sonlu sayı ve `[0,1]` aralığındadır. Geçersiz veride `ValueError` yükselt.

Her yöntem için `{"yontem":Y,"tespit":X,"yanlis_alarm":X,"veri_kaybi":X,"uygun":BOOL}` üret; oranlar ikinci görevdeki gibidir. Ham veri kaybı üst sınıra eşit veya küçükse yöntem uygundur. Uygunlar içinde en yüksek ham tespit, eşitlikte en düşük ham yanlış alarm, sonra alfabetik ad seçilir. `{"satirlar":[SATIR,...],"secilen":Y veya None}` döndür, satırları yöntem adına göre sırala ve girdiyi değiştirme.

```starter
from ai_guvence_veri import json_yukle

def yontem_karsilastir(kayitlar, kayip_ust_sinir):
    # KUSURLU BAŞLANGIÇ KODU: veri kaybı üst sınırını uygulamıyor; en yüksek tespiti her durumda seçiyor!
    satirlar = []
    for k in sorted(kayitlar, key=lambda x: x["yontem"]):
        toplam = k["tp"] + k["fp"] + k["tn"] + k["fn"]
        satirlar.append({"yontem": k["yontem"], "tespit": round(k["tp"] / max(k["tp"] + k["fn"], 1), 6),
                         "yanlis_alarm": round(k["fp"] / max(k["fp"] + k["tn"], 1), 6),
                         "veri_kaybi": round((k["tp"] + k["fp"]) / toplam, 6), "uygun": True})
    return {"satirlar": satirlar, "secilen": max(satirlar, key=lambda x: x["tespit"])["yontem"]}

veri = json_yukle("veri/yontem_sonuclari.json")
print(yontem_karsilastir(veri["yontemler"], veri["kayip_ust_sinir"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-15")
```

```test
import copy
K = [
    {"yontem": "anomali", "tp": 2, "fp": 1, "tn": 3, "fn": 1},
    {"yontem": "etki", "tp": 3, "fp": 0, "tn": 4, "fn": 0},
    {"yontem": "agresif", "tp": 3, "fp": 4, "tn": 0, "fn": 0},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        sonuc = fn(K, 0.5)
        if K != once or sonuc["secilen"] != "etki" or [x["yontem"] for x in sonuc["satirlar"]] != ["agresif", "anomali", "etki"]:
            return False
        if [x["uygun"] for x in sonuc["satirlar"]] != [False, True, True]:
            return False
        if sonuc["satirlar"][1]["tespit"] != 0.666667 or sonuc["satirlar"][1]["veri_kaybi"] != 0.428571:
            return False
        hepsi = fn(K, 1)
        if hepsi["secilen"] != "etki" or not all(x["uygun"] for x in hepsi["satirlar"]):
            return False
        sifir_kayip = fn([{"yontem": "koruyucu", "tp": 0, "fp": 0, "tn": 2, "fn": 1}], 0)
        if sifir_kayip["secilen"] != "koruyucu" or sifir_kayip["satirlar"][0]["tespit"] != 0:
            return False
        if fn(K, 0.1)["secilen"] is not None:
            return False
        esit = fn([
            {"yontem": "b", "tp": 1, "fp": 0, "tn": 1, "fn": 0},
            {"yontem": "a", "tp": 1, "fp": 0, "tn": 1, "fn": 0},
        ], 1)
        if esit["secilen"] != "a":
            return False
        yuvarla = fn([{"yontem": "a", "tp": 1, "fp": 1, "tn": 1, "fn": 0}], 1)
        if yuvarla["satirlar"][0]["tespit"] != 1 or yuvarla["satirlar"][0]["veri_kaybi"] != 0.666667:
            return False
        paydasiz = fn([
            {"yontem": "a", "tp": 0, "fp": 0, "tn": 0, "fn": 1},
            {"yontem": "b", "tp": 0, "fp": 1, "tn": 0, "fn": 0},
            {"yontem": "c", "tp": 0, "fp": 1, "tn": 2, "fn": 1},
        ], 1)
        if paydasiz["satirlar"][0]["yanlis_alarm"] != 0 or paydasiz["satirlar"][1]["tespit"] != 0 or paydasiz["satirlar"][1]["yanlis_alarm"] != 1.0 or paydasiz["satirlar"][2]["yanlis_alarm"] != 0.333333:
            return False
        for kayitlar, sinir in [
            (None, 0.5), (K, None), ({}, 0.5), (tuple(K), 0.5), ([], 0.5), ([None], 0.5), ([dict(K[0], ek=1)], 0.5), ([K[0], K[0]], 0.5),
            ([dict(K[0], yontem=123)], 0.5), ([dict(K[0], yontem="a b")], 0.5), ([dict(K[0], yontem="a" * 65)], 0.5),
            ([dict(K[0], tp=True)], 0.5), ([dict(K[0], tp=1.0)], 0.5), ([dict(K[0], tp=-1)], 0.5),
            ([dict(K[0], fp=-1)], 0.5), ([dict(K[0], tn=-1)], 0.5), ([dict(K[0], fn=-1)], 0.5),
            ([{"yontem": "a", "tp": 0, "fp": 0, "tn": 0, "fn": 0}], 0.5),
            (K, True), (K, "0.5"), (K, float("nan")), (K, float("inf")), (K, -0.1), (K, 1.1),
        ]:
            try:
                fn(kayitlar, sinir)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(yontem_karsilastir), "oranlar, veri kaybı sınırı ve yöntem seçimi korunmalı")
def m_tespit(kayitlar, sinir):
    return yontem_karsilastir([dict(x, tp=0) for x in kayitlar], sinir)
def m_alarm(kayitlar, sinir):
    return yontem_karsilastir([dict(x, fp=0) for x in kayitlar], sinir)
def m_sinir(kayitlar, sinir):
    return yontem_karsilastir(kayitlar, 0)
for ad, mutant in [("tespiti silen", m_tespit), ("yanlış alarmı silen", m_alarm), ("üst sınırı değiştiren", m_sinir)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def yontem_karsilastir(kayitlar, kayip_ust_sinir):
    import math
    import re
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    if not kayitlar:
        raise ValueError("kayıtlar boş olamaz")
    if isinstance(kayip_ust_sinir, bool):
        raise ValueError("üst sınır sayı olmalı")
    if not isinstance(kayip_ust_sinir, (int, float)):
        raise ValueError("üst sınır sayı olmalı")
    if not math.isfinite(kayip_ust_sinir):
        raise ValueError("üst sınır sonlu olmalı")
    if kayip_ust_sinir < 0 or kayip_ust_sinir > 1:
        raise ValueError("üst sınır aralık dışında")
    yontemler = set()
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"yontem", "tp", "fp", "tn", "fn"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["yontem"], str):
            raise ValueError("yöntem string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["yontem"]):
            raise ValueError("yöntem geçersiz")
        if kayit["yontem"] in yontemler:
            raise ValueError("yöntem yinelenemez")
        for alan in ("tp", "fp", "tn", "fn"):
            deger = kayit[alan]
            if isinstance(deger, bool):
                raise ValueError("sayım tamsayı olmalı")
            if not isinstance(deger, int):
                raise ValueError("sayım tamsayı olmalı")
            if deger < 0:
                raise ValueError("sayım negatif olamaz")
        if sum(kayit[alan] for alan in ("tp", "fp", "tn", "fn")) == 0:
            raise ValueError("yöntem toplamı pozitif olmalı")
        yontemler.add(kayit["yontem"])
    satirlar = []
    for kayit in sorted(kayitlar, key=lambda x: x["yontem"]):
        toplam = sum(kayit[alan] for alan in ("tp", "fp", "tn", "fn"))
        tespit_payda = kayit["tp"] + kayit["fn"]
        alarm_payda = kayit["fp"] + kayit["tn"]
        tespit = kayit["tp"] / tespit_payda if tespit_payda > 0 else 0.0
        alarm = kayit["fp"] / alarm_payda if alarm_payda > 0 else 0.0
        kayip = (kayit["tp"] + kayit["fp"]) / toplam
        satirlar.append({"yontem": kayit["yontem"], "tespit": round(tespit, 6), "yanlis_alarm": round(alarm, 6), "veri_kaybi": round(kayip, 6), "uygun": kayip <= kayip_ust_sinir, "_tespit": tespit, "_alarm": alarm})
    uygunlar = [x for x in satirlar if x["uygun"]]
    secilen = min(uygunlar, key=lambda x: (-x["_tespit"], x["_alarm"], x["yontem"]))["yontem"] if uygunlar else None
    for satir in satirlar:
        del satir["_tespit"]
        del satir["_alarm"]
    return {"satirlar": satirlar, "secilen": secilen}
```

```hint
Ham oranları seçim bitene kadar sakla. Uygunluk veri kaybından, sıralama ise tespit ve yanlış alarmdan belirlenir.
```
:::

::: anlat `scikit-learn` ile canlı ayıklama: hangi kanıt neyi gösterir?
Önceki üç görevde ayıklama kararlarını saydın, oranları hesapladın ve veri kaybı sınırıyla yöntem seçtin. Şimdi aynı üç işlevi **gerçek ayıklama yöntemlerine** bağlıyoruz:

1. Üç tohum için 400 eğitim + 200 test örneklik sentetik sınıflandırma verisi üretilir; eğitim etiketlerinin 40'ı (yüzde 10) bilerek çevrilir. Hangi kaydın çevrildiği bilindiği için her karar TP/FP/TN/FN olarak sayılabilir,
2. Dört yöntem canlı çalışır: `kayip_esigi` (çapraz doğrulamalı olasılıkta kendi etiketine 0.25'ten düşük güven, Cleanlab'in temel fikri), `knn_tutarlilik` (8 komşudan yüzde 40'tan azı aynı etiketi taşıyorsa), `izolasyon` (yalnız özelliklere bakan IsolationForest) ve `agresif` (0.6 güven eşiği),
3. Her yöntemin 400 kararı senin `ayiklama_kararlari` işlevinle sayılır, üç tohumun toplamı `ayiklama_metrikleri` ile oranlara çevrilir ve `yontem_karsilastir` ile (veri kaybı sınırı `0.15`) yöntem seçilir.

Kanıtta iki şeye dikkat et. Birincisi, `izolasyon` zehirlilerin çok azını yakalar: etiket çevirme özellik uzayında aykırı nokta üretmez, yani yanlış tehdide yanlış araç uygulanmıştır. İkincisi, `yeniden_egitim_test_dogrulugu` alanında yöntemler arasındaki farklar küçüktür; zehirli kayıtları tam bilen `kahin_temiz` ayıklaması bile doğruluğu belirgin artırmayabilir, çünkü rastgele etiket gürültüsüne bu model zaten dayanıklıdır. "Ayıkladım, doğruluk arttı" bu durumda zayıf kanıttır; zehirli olduğu bilinen kayıtlarla ölçülen karışıklık matrisi ise yöntemin ne yaptığını doğrudan gösterir.

Kaynaklar: [Koh ve Liang 2017 — Understanding Black-box Predictions via Influence Functions (arXiv:1703.04730)](https://arxiv.org/abs/1703.04730), [Peri vd. 2020 — Deep k-NN Defense against Clean-Label Data Poisoning Attacks (arXiv:1909.13374)](https://arxiv.org/abs/1909.13374).
:::

::: gorev Gerçek deney · scikit-learn ile ayıklama yöntemlerini karışıklık matrisiyle kanıtla
Önceki üç görevde yazdığın `ayiklama_kararlari(kayitlar)`, `ayiklama_metrikleri(sayimlar)` ve `yontem_karsilastir(kayitlar, kayip_ust_sinir)` işlevlerini burada birleştir.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 180
```

```starter
import ai_lab
from sandbox import ai_gercek_ai_guvence_15 as L

def ayiklama_kararlari(kayitlar):
    return {"tp": 0, "fp": 0, "tn": 0, "fn": 0, "ayiklanan_idler": []}

def ayiklama_metrikleri(sayimlar):
    # KUSURLU BAŞLANGIÇ KODU: yanlış alarmı bütün kayıtlara bölüyor!
    toplam = sum(sayimlar.values())
    return {"toplam": toplam, "tespit": 0.0, "yanlis_alarm": round(sayimlar["fp"] / toplam, 6), "veri_kaybi": 0.0}

def yontem_karsilastir(kayitlar, kayip_ust_sinir):
    return {"satirlar": [], "secilen": None}

if ai_lab.CALISTIR:
    L.goster(ayiklama_kararlari, ayiklama_metrikleri, yontem_karsilastir)
```

```test
import ai_lab
from sandbox import ai_gercek_ai_guvence_15 as L

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for s in ai_lab.kod_denetimi(src, yasak=("ayiklama_kararlari_referans", "ayiklama_metrikleri_referans", "yontem_karsilastir_referans", "kanit_yaz")):
    ok(False, f"Güvenlik/kopya denetimi: {s}")
if not all(checks):
    stop()

def _sozlesme_kontrol():
    try:
        K = [{"id": "b", "gercek_zehirli": False, "ayiklandi": True}, {"id": "a", "gercek_zehirli": True, "ayiklandi": True},
             {"id": "c", "gercek_zehirli": True, "ayiklandi": False}]
        if ayiklama_kararlari(K) != {"tp": 1, "fp": 1, "tn": 0, "fn": 1, "ayiklanan_idler": ["a", "b"]}:
            return False
        for bozuk in [[], [K[0], K[0]], [dict(K[0], ayiklandi=1)]]:
            try:
                ayiklama_kararlari(bozuk)
                return False
            except ValueError:
                pass
        if ayiklama_metrikleri({"tp": 0, "fp": 1, "tn": 3, "fn": 0}) != {"toplam": 4, "tespit": 0.0, "yanlis_alarm": 0.25, "veri_kaybi": 0.25}:
            return False
        r = yontem_karsilastir([{"yontem": "x", "tp": 2, "fp": 2, "tn": 0, "fn": 0}, {"yontem": "y", "tp": 1, "fp": 0, "tn": 2, "fn": 1}], 0.5)
        if r["secilen"] != "y" or [s["uygun"] for s in r["satirlar"]] != [False, True]:
            return False
        return True
    except Exception:
        return False

def _birim1(fn):
    import copy
    K = [
        {"id": "r-1", "gercek_zehirli": True, "ayiklandi": True},
        {"id": "r-2", "gercek_zehirli": False, "ayiklandi": True},
        {"id": "r-3", "gercek_zehirli": False, "ayiklandi": False},
        {"id": "r-4", "gercek_zehirli": True, "ayiklandi": False},
    ]
    def sozlesme(fn):
        try:
            once = copy.deepcopy(K)
            if fn(K) != {"tp": 1, "fp": 1, "tn": 1, "fn": 1, "ayiklanan_idler": ["r-1", "r-2"]} or K != once:
                return False
            sinir = fn([{"id": "a" * 64, "gercek_zehirli": False, "ayiklandi": False}])
            if sinir != {"tp": 0, "fp": 0, "tn": 1, "fn": 0, "ayiklanan_idler": []}:
                return False
            if fn([{"id": "z1", "gercek_zehirli": True, "ayiklandi": True}, {"id": "z2", "gercek_zehirli": True, "ayiklandi": True}, {"id": "z3", "gercek_zehirli": True, "ayiklandi": False}]) != {"tp": 2, "fp": 0, "tn": 0, "fn": 1, "ayiklanan_idler": ["z1", "z2"]}:
                return False
            for kayitlar in [
                None, {}, tuple(K), [], [None], [dict(K[0], ek=1)], [K[0], K[0]],
                [dict(K[0], id="")], [dict(K[0], id="a b")], [dict(K[0], id="a" * 65)], [dict(K[0], id=None)],
                [dict(K[0], gercek_zehirli=1)], [dict(K[0], gercek_zehirli="true")], [dict(K[0], gercek_zehirli=None)],
                [dict(K[0], ayiklandi=1)], [dict(K[0], ayiklandi="true")], [dict(K[0], ayiklandi=None)],
            ]:
                try:
                    fn(kayitlar)
                    return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False
    return sozlesme(fn)

def _birim2(fn):
    import copy
    S = {"tp": 2, "fp": 1, "tn": 3, "fn": 1}
    def sozlesme(fn):
        try:
            once = copy.deepcopy(S)
            if fn(S) != {"toplam": 7, "tespit": 0.666667, "yanlis_alarm": 0.25, "veri_kaybi": 0.428571} or S != once:
                return False
            sifir = fn({"tp": 0, "fp": 0, "tn": 2, "fn": 0})
            if sifir != {"toplam": 2, "tespit": 0.0, "yanlis_alarm": 0.0, "veri_kaybi": 0.0}:
                return False
            if fn({"tp": 1, "fp": 0, "tn": 0, "fn": 0})["yanlis_alarm"] != 0 or fn({"tp": 1, "fp": 0, "tn": 1, "fn": 0})["tespit"] != 1.0 or fn({"tp": 1, "fp": 0, "tn": 0, "fn": 1})["tespit"] != 0.5:
                return False
            if fn({"tp": 0, "fp": 1, "tn": 2, "fn": 1})["yanlis_alarm"] != 0.333333 or fn({"tp": 0, "fp": 1, "tn": 0, "fn": 1})["yanlis_alarm"] != 1.0:
                return False
            for sayimlar in [
                None, [], {}, dict(S, ek=1), {k: 0 for k in S},
                dict(S, tp=True), dict(S, tp=1.0), dict(S, tp="1"), dict(S, tp=-1), dict(S, tp=None),
                dict(S, fp=True), dict(S, fp=1.0), dict(S, fp=-1),
                dict(S, tn=True), dict(S, tn=1.0), dict(S, tn=-1),
                dict(S, fn=True), dict(S, fn=1.0), dict(S, fn=-1),
            ]:
                try:
                    fn(sayimlar)
                    return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False
    return sozlesme(fn)

def _birim3(fn):
    import copy
    K = [
        {"yontem": "anomali", "tp": 2, "fp": 1, "tn": 3, "fn": 1},
        {"yontem": "etki", "tp": 3, "fp": 0, "tn": 4, "fn": 0},
        {"yontem": "agresif", "tp": 3, "fp": 4, "tn": 0, "fn": 0},
    ]
    def sozlesme(fn):
        try:
            once = copy.deepcopy(K)
            sonuc = fn(K, 0.5)
            if K != once or sonuc["secilen"] != "etki" or [x["yontem"] for x in sonuc["satirlar"]] != ["agresif", "anomali", "etki"]:
                return False
            if [x["uygun"] for x in sonuc["satirlar"]] != [False, True, True]:
                return False
            if sonuc["satirlar"][1]["tespit"] != 0.666667 or sonuc["satirlar"][1]["veri_kaybi"] != 0.428571:
                return False
            hepsi = fn(K, 1)
            if hepsi["secilen"] != "etki" or not all(x["uygun"] for x in hepsi["satirlar"]):
                return False
            sifir_kayip = fn([{"yontem": "koruyucu", "tp": 0, "fp": 0, "tn": 2, "fn": 1}], 0)
            if sifir_kayip["secilen"] != "koruyucu" or sifir_kayip["satirlar"][0]["tespit"] != 0:
                return False
            if fn(K, 0.1)["secilen"] is not None:
                return False
            esit = fn([
                {"yontem": "b", "tp": 1, "fp": 0, "tn": 1, "fn": 0},
                {"yontem": "a", "tp": 1, "fp": 0, "tn": 1, "fn": 0},
            ], 1)
            if esit["secilen"] != "a":
                return False
            yuvarla = fn([{"yontem": "a", "tp": 1, "fp": 1, "tn": 1, "fn": 0}], 1)
            if yuvarla["satirlar"][0]["tespit"] != 1 or yuvarla["satirlar"][0]["veri_kaybi"] != 0.666667:
                return False
            paydasiz = fn([
                {"yontem": "a", "tp": 0, "fp": 0, "tn": 0, "fn": 1},
                {"yontem": "b", "tp": 0, "fp": 1, "tn": 0, "fn": 0},
                {"yontem": "c", "tp": 0, "fp": 1, "tn": 2, "fn": 1},
            ], 1)
            if paydasiz["satirlar"][0]["yanlis_alarm"] != 0 or paydasiz["satirlar"][1]["tespit"] != 0 or paydasiz["satirlar"][1]["yanlis_alarm"] != 1.0 or paydasiz["satirlar"][2]["yanlis_alarm"] != 0.333333:
                return False
            for kayitlar, sinir in [
                (None, 0.5), (K, None), ({}, 0.5), (tuple(K), 0.5), ([], 0.5), ([None], 0.5), ([dict(K[0], ek=1)], 0.5), ([K[0], K[0]], 0.5),
                ([dict(K[0], yontem=123)], 0.5), ([dict(K[0], yontem="a b")], 0.5), ([dict(K[0], yontem="a" * 65)], 0.5),
                ([dict(K[0], tp=True)], 0.5), ([dict(K[0], tp=1.0)], 0.5), ([dict(K[0], tp=-1)], 0.5),
                ([dict(K[0], fp=-1)], 0.5), ([dict(K[0], tn=-1)], 0.5), ([dict(K[0], fn=-1)], 0.5),
                ([{"yontem": "a", "tp": 0, "fp": 0, "tn": 0, "fn": 0}], 0.5),
                (K, True), (K, "0.5"), (K, float("nan")), (K, float("inf")), (K, -0.1), (K, 1.1),
            ]:
                try:
                    fn(kayitlar, sinir)
                    return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False
    return sozlesme(fn)

ok(_birim1(ayiklama_kararlari), "ayiklama_kararlari tam birim sözleşmesini geçmeli")
ok(_birim2(ayiklama_metrikleri), "ayiklama_metrikleri tam birim sözleşmesini geçmeli")
ok(_birim3(yontem_karsilastir), "yontem_karsilastir tam birim sözleşmesini geçmeli")
ok(_sozlesme_kontrol(), "ayiklama_kararlari, ayiklama_metrikleri ve yontem_karsilastir sözleşme kontrollerini geçmeli")
if not all(checks):
    stop()

try:
    rapor = L.deney(ayiklama_kararlari, ayiklama_metrikleri, yontem_karsilastir)
except ai_lab.GercekLabYok as e:
    ok(False, str(e))
    stop()
except Exception as e:
    ok(False, f"GERÇEK AYIKLAMA DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

k = rapor["kontroller"]
ok(k["kararlar_uyumu"], f"ayiklama_kararlari canlı yöntem kararlarında referansla aynı sayımı vermeli: {rapor['karar_ornegi']}")
ok(k["metrik_uyumu"], f"ayiklama_metrikleri canlı sayımlarda referansla uyuşmalı: {rapor['metrik_ogrenci']}")
ok(k["secim_uyumu"], f"yontem_karsilastir canlı yöntem sonuçlarında referansla uyuşmalı: {rapor['secim_ogrenci']}")
ok(k["ayrim_gozlendi"], f"etiket tutarlılığına bakan yöntem zehirlilerin çoğunu, özellik tabanlı yöntem azını yakalamalı: {rapor['ozet']['yontemler']}")

kabul = all(checks)
kanit_yolu = ai_lab.kanit_yaz("guvence-15-ayiklama-kaniti", dict(rapor, kaynak="gercek", kabul=kabul))
o = rapor["ozet"]
print(f"GERÇEK AYIKLAMA DENEYİ: sklearn={o['sklearn_surum']} secilen={o['secilen']} test_dogrulugu={o['yeniden_egitim_test_dogrulugu']} kanıt={kanit_yolu}")
```

```solution
import math
import re
import ai_lab
from sandbox import ai_gercek_ai_guvence_15 as L

_AD = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")

def _sayim_mi(d):
    return not isinstance(d, bool) and isinstance(d, int) and d >= 0

def _oranlar(s):
    toplam = s["tp"] + s["fp"] + s["tn"] + s["fn"]
    tespit = s["tp"] / (s["tp"] + s["fn"]) if s["tp"] + s["fn"] > 0 else 0.0
    alarm = s["fp"] / (s["fp"] + s["tn"]) if s["fp"] + s["tn"] > 0 else 0.0
    return toplam, tespit, alarm, (s["tp"] + s["fp"]) / toplam

def ayiklama_kararlari(kayitlar):
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar geçersiz")
    idler = set()
    for k in kayitlar:
        if not isinstance(k, dict) or set(k) != {"id", "gercek_zehirli", "ayiklandi"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(k["id"], str) or not _AD.fullmatch(k["id"]) or k["id"] in idler:
            raise ValueError("kimlik geçersiz")
        if not isinstance(k["gercek_zehirli"], bool) or not isinstance(k["ayiklandi"], bool):
            raise ValueError("alanlar bool olmalı")
        idler.add(k["id"])
    return {
        "tp": sum(1 for x in kayitlar if x["gercek_zehirli"] and x["ayiklandi"]),
        "fp": sum(1 for x in kayitlar if not x["gercek_zehirli"] and x["ayiklandi"]),
        "tn": sum(1 for x in kayitlar if not x["gercek_zehirli"] and not x["ayiklandi"]),
        "fn": sum(1 for x in kayitlar if x["gercek_zehirli"] and not x["ayiklandi"]),
        "ayiklanan_idler": sorted(x["id"] for x in kayitlar if x["ayiklandi"]),
    }

def ayiklama_metrikleri(sayimlar):
    if not isinstance(sayimlar, dict) or set(sayimlar) != {"tp", "fp", "tn", "fn"}:
        raise ValueError("sayım şeması geçersiz")
    if not all(_sayim_mi(v) for v in sayimlar.values()) or sum(sayimlar.values()) == 0:
        raise ValueError("sayımlar geçersiz")
    toplam, tespit, alarm, kayip = _oranlar(sayimlar)
    return {"toplam": toplam, "tespit": round(tespit, 6), "yanlis_alarm": round(alarm, 6), "veri_kaybi": round(kayip, 6)}

def yontem_karsilastir(kayitlar, kayip_ust_sinir):
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar geçersiz")
    if isinstance(kayip_ust_sinir, bool) or not isinstance(kayip_ust_sinir, (int, float)) \
            or not math.isfinite(kayip_ust_sinir) or not 0 <= kayip_ust_sinir <= 1:
        raise ValueError("üst sınır geçersiz")
    adlar = set()
    for k in kayitlar:
        if not isinstance(k, dict) or set(k) != {"yontem", "tp", "fp", "tn", "fn"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(k["yontem"], str) or not _AD.fullmatch(k["yontem"]) or k["yontem"] in adlar:
            raise ValueError("yöntem geçersiz")
        if not all(_sayim_mi(k[a]) for a in ("tp", "fp", "tn", "fn")) or sum(k[a] for a in ("tp", "fp", "tn", "fn")) == 0:
            raise ValueError("sayımlar geçersiz")
        adlar.add(k["yontem"])
    satirlar = []
    for k in sorted(kayitlar, key=lambda x: x["yontem"]):
        _, tespit, alarm, kayip = _oranlar(k)
        satirlar.append({"yontem": k["yontem"], "tespit": round(tespit, 6), "yanlis_alarm": round(alarm, 6),
                         "veri_kaybi": round(kayip, 6), "uygun": kayip <= kayip_ust_sinir, "_t": tespit, "_a": alarm})
    uygunlar = [x for x in satirlar if x["uygun"]]
    secilen = min(uygunlar, key=lambda x: (-x["_t"], x["_a"], x["yontem"]))["yontem"] if uygunlar else None
    for s in satirlar:
        del s["_t"], s["_a"]
    return {"satirlar": satirlar, "secilen": secilen}

if ai_lab.CALISTIR:
    L.goster(ayiklama_kararlari, ayiklama_metrikleri, yontem_karsilastir)
```

```hint
Önceki üç görevde yazdığın işlevleri eksiksiz taşı. Canlı deneyde her yöntemin 400 kararı ayrı sayılır; kanıtta `izolasyon` satırını ve `yeniden_egitim_test_dogrulugu` alanını birlikte oku.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **'Temizledim, doğruluk arttı' neden zayıf kanıttır? (35 sn).** "Dayanıklı bir sınıflandırıcı küçük etiket zehirlemesinde zaten aynı test doğruluğunu verebilir; ya da agresif bir filtre nadir ama temiz azınlık örneklerini silip ortalama doğruluğu şişirebilir."
2. **Karışıklık matrisi ve üçlü ödünleşim (30 sn).** "Veri ayıklama (`sanitization`) yöntemini değerlendirirken zehir yakalama oranı (`tespit`), temiz veriyi çöpe atma oranı (`yanlis_alarm`) ve toplam `veri_kaybi` üst sınırı birlikte okunmalıdır."
3. **Saldırı mekanizmasıyla savunma uyumu (30 sn).** "Özellik uzayında aykırılık arayan `IsolationForest`, özelliklere dokunmayan saf etiket çevirme saldırısını göremezken komşuluk etiket uyumuna bakan yöntem doğrudan yakalar."
4. **Soru (25 sn).** "Gerçek sahada hangi örneklerin zehirli olduğunu bilmiyorsak bir veri ayıklama filtresinin `yanlis_alarm` maliyetini yayına almadan önce nasıl kalibre edersin?"
:::
