---
id: ai-savunma-23
title: Abuse Detection ve Uyarlanabilir Sınırlama
summary: Kullanıcı bazlı zaman penceresinde jailbreak, araç ve sızıntı sinyallerini say; eşiklere göre izleme, bekleme ve engelleme kararı üret; önce görünür sentetik olay akışıyla, sonra kural tespiti ve yerel Ollama modelinin gerçek yanıtlarıyla sına.
timeout: 45
esleme: ai-saldiri-40, ai-saldiri-42
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et: Davranış sinyalleri kullanıcı ve zaman bağlamında değerlendirilir

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Elastic gibi bir olay deposu guardrail, model ve araç servislerinden gelen olayları kullanıcı kimliği ve zamanla saklar. Bir sorgu son N saniyedeki olayları kullanıcı başına sayar. FastAPI gibi bir API katmanı bu sayımlara göre isteği geçirir, yavaşlatır (429 + `Retry-After`) ya da reddeder. | Görev 1–3: `veri/abuse_politikasi.json` ve `veri/olay_akisi.json` içindeki **sentetik** olay akışı. Son adım: bir saldırgan ve bir normal kullanıcının girdileri kural temelli jailbreak tespitinden geçer, kurulu yerel Ollama modeline canary'li sistem istemiyle gerçekten gönderilir ve olaylar bu iki ölçümden üretilir. | Kural temelli tespit yalnız bilinen kalıpları görür. Dört girdilik bir deney, sınırlama eşiklerinin gerçek trafikte doğru ayarlandığını göstermez. Bu derste hiçbir gerçek istek engellenmez; karar yalnız raporlanır. |

> [!NOT]
> Görev 1–3 sentetik veriyle çalışır. Bu görevlerde model, Elastic veya FastAPI çağrılmaz. Son adımdaki **Gerçek deney** görevi kurulu yerel Ollama modelini gerçekten çalıştırır; yeni model veya araç indirmez. Elastic ve FastAPI bu derste çalıştırılmaz. `veri/` dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalanır; kopyada yaptığın değişiklik bir sonraki çalıştırmada sıfırlanır, **kalıcılık yoktur**. Kontrol bu dosyalardan ayrı, gizli verilerle sınar.

Tek bir şüpheli istekle tekrarlanan jailbreak, olağan dışı araç kullanımı veya sızıntı girişimi aynı değildir. Elastic benzeri bir olay deposundaki kayıtlar kullanıcı bazında ve son olay zamanına göre sınırlı bir pencerede sayılır. FastAPI tarafında bu sayımlar uyarlanabilir sınırlama kararına dönüştürülebilir.

**Neden sabit bir istek sınırı yetmez?** Klasik hız sınırlama ("dakikada 60 istek") yalnız miktarı ölçer. Bir LLM API'sinde tehlike miktarda değil, içerikte ve örüntüdedir. Bir saldırgan dakikada üç istek göndererek de jailbreak dener. Bir otomasyon betiği ise dakikada yüz meşru istek gönderebilir. Uyarlanabilir sınırlama, isteğin **ne** yaptığına dair sinyalleri sayar ve kararı bu sinyallerin türüne göre ağırlaştırır. Sızıntı en ağır sinyaldir, çünkü zarar artık gerçekleşmiştir. Jailbreak ve araç kötüye kullanımı ise zarar girişimidir.
:::

::: anlat Pencere ve karar önceliği açık tanımlıdır
Her kullanıcının referans zamanı kendi en yeni olayıdır. `son_zaman - olay_zamani <= pencere_ms` koşulunu sağlayan olaylar pencereye girer; sınır farkına eşit eski olay da sayılır. Normal olaylar referans zamanını etkiler ancak üç abuse sayacına katılmaz.

Sızıntı eşiği dolarsa karar `engelle`; aksi hâlde jailbreak veya araç eşiği dolarsa `beklet`; eşik dolmadan abuse varsa `izle`; abuse yoksa `izin` olur. Engelleme bekleme süresinin iki katını, bekleme kararı bir katını uygular.

`veri/olay_akisi.json` bu kuralların sınırlarını gösterir:

- **`u-mert`:** İlk jailbreak denemesi son olaydan tam 60000 ms öncedir. Kural `<=` kullandığı için bu deneme sayılır ve kullanıcı eşiğe ulaşır.
- **`u-can`:** Eski bir jailbreak denemesi vardır, ama 200 saniye sonra gelen normal bir istek referans zamanını ileri taşır. Eski deneme pencere dışına düşer. "Kullanıcı bir süre düzgün davranırsa ceza kalkar" ilkesinin karşılığı budur.

**Saldırgan bakışı:** Pencere tabanlı sayım bilinen bir zayıflık taşır. `u-ali` üç jailbreak denemesini 70'er saniye arayla yapar. Her an pencerede yalnız bir deneme bulunur, bu yüzden hiçbir zaman `beklet` kararı almaz. Buna "düşük ve yavaş" (low-and-slow) saldırı denir. Başka bir atlatma yolu, denemeleri birden çok hesaba bölmektir: her kullanıcı ayrı sayıldığı için eşik hiçbir hesapta dolmaz. Gerçek sistemler bu yüzden kısa pencereyi uzun dönemli bir sayaçla (ör. 24 saatlik toplam) ve kullanıcı dışı anahtarlarla (IP, cihaz, API anahtarı) birleştirir. Bu ders yalnız kullanıcı başına tek pencereyi modeller.

**Savunucu tarafı ve sık tuzaklar:**

- **Referans zamanı:** Referans zaman "şu an" değil, kullanıcının **kendi** son olayıdır. Başka bir kullanıcının yeni olayı, birinin penceresini kaydırmamalıdır.
- **Normal olaylar:** Sayaca girmezler, ama referans zamanını değiştirirler.
- **Öncelik:** Sızıntı her zaman önce değerlendirilir. Hem sızıntı hem jailbreak eşiği dolmuş bir kullanıcı `beklet` değil `engelle` alır (`u-selin`).
- **Eşitlik:** Eşiğe eşit sayı kararı tetikler. `u-bot` araç eşiğine tam eşittir ve `beklet` alır.
- **Yanlış pozitifin bedeli:** Bir güvenlik araştırmacısı ya da otomasyon, meşru olduğu hâlde bekletilebilir. Bu yüzden `beklet` geçici bir karardır, `engelle` ise yalnız gerçek zarar sinyalinde verilir.
:::

::: tahmin Zaman penceresini tahmin et
Üç çıktı satırını yaz:

```python
zamanlar = [0, 900, 1000]
son = 2000
pencere_ms = 1000
print([x for x in zamanlar if son - x <= pencere_ms])
print(son - 1000 <= pencere_ms)
print(son - 0 <= pencere_ms)
```

???

```cikti
[1000]
True
False
```

Pencere sınırındaki olay dahil, daha eski olay hariçtir.
:::

::: gorev 1 · Abuse sınırlama politikasını doğrula
`abuse_politikasi_dogrula(politika)` işlevini yaz. Politika tam olarak `pencere_ms`, `max_olay`, `jailbreak_esigi`, `arac_esigi`, `sizinti_esigi`, `bekleme_ms` alanlarını taşısın.

Pencere ve bekleme bool olmayan 1–60000 arası int; olay sınırı bool olmayan 1–1000 arası int; üç abuse eşiği bool olmayan 1–20 arası int olmalıdır. Geçersiz veride `ValueError` yükselt. Politikayı yeni sözlük olarak döndür.

Görünür veri: `veri/abuse_politikasi.json`. Başlangıç kodu asıl politikayı ve dört bozuk politikayı doğrulamayı dener. Bozukların dördü de reddedilmelidir.

```starter
from ai_savunma_veri import json_yukle

def abuse_politikasi_dogrula(politika):
    # KUSURLU BAŞLANGIÇ KODU: eksik alanı, bool değeri, 0 eşiği ve aralık dışı pencereyi kabul ediyor; girdinin kendisini döndürüyor!
    for alan, deger in politika.items():
        if not isinstance(deger, int):
            raise ValueError(alan + " int olmalı")
    return politika

veri = json_yukle("veri/abuse_politikasi.json")
for ad, p in [("asil", veri["politika"])] + [(b["ad"], b["politika"]) for b in veri["bozuk_politikalar"]]:
    try:
        abuse_politikasi_dogrula(p)
        print(ad, "kabul")
    except ValueError as hata:
        print(ad, "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-23")
```

```test
P = {"pencere_ms": 1000, "max_olay": 100, "jailbreak_esigi": 2, "arac_esigi": 2, "sizinti_esigi": 1, "bekleme_ms": 100}
def sozlesme(fn):
    try:
        sonuc = fn(P)
        if sonuc != P or sonuc is P:
            return False
        for alan, deger in [("pencere_ms", 1), ("pencere_ms", 60000), ("bekleme_ms", 1), ("bekleme_ms", 60000), ("max_olay", 1), ("max_olay", 1000), ("jailbreak_esigi", 1), ("arac_esigi", 20), ("sizinti_esigi", 20)]:
            if fn(dict(P, **{alan: deger}))[alan] != deger:
                return False
        for politika in [
            None, [], dict(P, ek=1), dict(P, pencere_ms=0), dict(P, pencere_ms=60001), dict(P, pencere_ms=True),
            dict(P, bekleme_ms=0), dict(P, bekleme_ms=60001), dict(P, bekleme_ms=False),
            dict(P, max_olay=0), dict(P, max_olay=1001), dict(P, max_olay=True),
            dict(P, jailbreak_esigi=0), dict(P, jailbreak_esigi=21), dict(P, arac_esigi=0),
            dict(P, arac_esigi=21), dict(P, sizinti_esigi=0), dict(P, sizinti_esigi=21), dict(P, sizinti_esigi=False),
        ]:
            try:
                fn(politika)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(abuse_politikasi_dogrula), "pencere, olay, eşik ve bekleme sınırları korunmalı")
def m_pencere(politika):
    return abuse_politikasi_dogrula(dict(politika, pencere_ms=60000))
def m_esik(politika):
    return abuse_politikasi_dogrula(dict(politika, sizinti_esigi=20))
def m_bekleme(politika):
    return abuse_politikasi_dogrula(dict(politika, bekleme_ms=1))
for ad, mutant in [("pencereyi büyüten", m_pencere), ("eşiği büyüten", m_esik), ("beklemeyi düşüren", m_bekleme)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
# --- carbon-c8-ek-bas ---
for _k23 in ("pencere_ms", "max_olay", "jailbreak_esigi", "arac_esigi", "sizinti_esigi", "bekleme_ms"):
    raises(ValueError, abuse_politikasi_dogrula, dict(P, **{_k23: True}), msg=f"{_k23} bool olamaz")
eq(abuse_politikasi_dogrula(dict(P, jailbreak_esigi=20))["jailbreak_esigi"], 20, "jailbreak_esigi üst sınırı 20 geçerli")
# --- carbon-c8-ek-son ---
```

```solution
def abuse_politikasi_dogrula(politika):
    if not isinstance(politika, dict):
        raise ValueError("politika sözlük olmalı")
    if set(politika) != {"pencere_ms", "max_olay", "jailbreak_esigi", "arac_esigi", "sizinti_esigi", "bekleme_ms"}:
        raise ValueError("politika şeması geçersiz")
    for alan, ust in [("pencere_ms", 60000), ("bekleme_ms", 60000), ("max_olay", 1000), ("jailbreak_esigi", 20), ("arac_esigi", 20), ("sizinti_esigi", 20)]:
        if type(politika[alan]) is not int:
            raise ValueError(alan + " int olmalı")
        if politika[alan] < 1:
            raise ValueError(alan + " pozitif olmalı")
        if politika[alan] > ust:
            raise ValueError(alan + " çok büyük")
    return {"pencere_ms": politika["pencere_ms"], "max_olay": politika["max_olay"], "jailbreak_esigi": politika["jailbreak_esigi"], "arac_esigi": politika["arac_esigi"], "sizinti_esigi": politika["sizinti_esigi"], "bekleme_ms": politika["bekleme_ms"]}
```

```hint
Altı alanı tür, alt sınır ve alana özgü üst sınır için aynı döngüde doğrula; bool değerleri `type(...) is not int` ile reddet.
```
:::

::: anlat Sinyal sayımı kullanıcı bazında yapılır
Her kullanıcı için yalnız kendi olayları ve kendi son zamanı kullanılır. Başka kullanıcının yeni olayı pencereyi değiştirmez. Çıktıda üç sayaç her zaman bulunur ve kullanıcılar kimliğe göre sıralanır.

Olay kimliği bütün girdide benzersizdir. Kullanıcı kimliği 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren stringdir. Zaman bool olmayan 0 veya pozitif int, tür `normal`, `jailbreak`, `arac`, `sizinti` olmalıdır.
:::

::: gorev 2 · Kullanıcı abuse sinyallerini say
`kullanici_sinyal_raporu(olaylar, politika)` işlevini yaz. Politika ilk görevdeki bütün kuralları sağlasın; olay sayısı sınırını aşan girdi `ValueError` üretsin. Olaylar liste; her kayıt tam olarak `id`, `kullanici`, `zaman_ms`, `tur` alanlarını taşısın ve anlatımdaki biçim kurallarına uysun. Geçersiz veride `ValueError` yükselt.

Kullanıcı bazında son olay zamanını ve pencere içindeki jailbreak, araç, sızıntı sayımlarını hesapla. Her kullanıcı için `{"kullanici":K,"son_zaman_ms":Z,"sayim":{"jailbreak":J,"arac":A,"sizinti":S}}` döndür. Kullanıcıya göre sırala, boş olayda boş liste döndür ve girdileri değiştirme.

Görünür veri: `veri/olay_akisi.json`. Doğru sayımda `u-ali` yalnız 1 jailbreak gösterir, `u-mert` sınırdaki denemeyle birlikte 3 gösterir, `u-can`'ın eski denemesi ise pencere dışında kalır.

```starter
from ai_savunma_veri import json_yukle

def kullanici_sinyal_raporu(olaylar, politika):
    # KUSURLU BAŞLANGIÇ KODU: referans zamanı olarak bütün girdinin en yeni olayını kullanıyor (kullanıcının kendi son olayını değil) ve pencere sınırını < ile dışarıda bırakıyor!
    son_genel = max((o["zaman_ms"] for o in olaylar), default=0)
    rapor = {}
    for o in olaylar:
        r = rapor.setdefault(o["kullanici"], {"kullanici": o["kullanici"], "son_zaman_ms": 0, "sayim": {"jailbreak": 0, "arac": 0, "sizinti": 0}})
        r["son_zaman_ms"] = max(r["son_zaman_ms"], o["zaman_ms"])
        if o["tur"] in r["sayim"] and son_genel - o["zaman_ms"] < politika["pencere_ms"]:
            r["sayim"][o["tur"]] += 1
    return [rapor[k] for k in sorted(rapor)]

politika = json_yukle("veri/abuse_politikasi.json")["politika"]
veri = json_yukle("veri/olay_akisi.json")
for r in kullanici_sinyal_raporu(veri["olaylar"], politika):
    print(r["kullanici"], "son", r["son_zaman_ms"], r["sayim"])
for o in veri["bozuk_olaylar"]:
    try:
        kullanici_sinyal_raporu([o], politika)
        print(o["id"], "KABUL edildi (yanlış)")
    except ValueError as hata:
        print(o["id"], "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-23")
```

```test
import copy
P = {"pencere_ms": 1000, "max_olay": 20, "jailbreak_esigi": 2, "arac_esigi": 2, "sizinti_esigi": 1, "bekleme_ms": 100}
O = [
    {"id": "a-eski", "kullanici": "a", "zaman_ms": 0, "tur": "jailbreak"},
    {"id": "a-sinir", "kullanici": "a", "zaman_ms": 1000, "tur": "jailbreak"},
    {"id": "a-yeni", "kullanici": "a", "zaman_ms": 2000, "tur": "normal"},
    {"id": "a-arac", "kullanici": "a", "zaman_ms": 1900, "tur": "arac"},
    {"id": "b-yeni", "kullanici": "b", "zaman_ms": 5000, "tur": "normal"},
    {"id": "b-sizinti", "kullanici": "b", "zaman_ms": 4500, "tur": "sizinti"},
]
BEKLENEN = [
    {"kullanici": "a", "son_zaman_ms": 2000, "sayim": {"jailbreak": 1, "arac": 1, "sizinti": 0}},
    {"kullanici": "b", "son_zaman_ms": 5000, "sayim": {"jailbreak": 0, "arac": 0, "sizinti": 1}},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(O)
        ponce = copy.deepcopy(P)
        if fn(O, P) != BEKLENEN or O != once or P != ponce or fn(list(reversed(O)), P) != BEKLENEN or fn([], P) != []:
            return False
        if fn(O, dict(P, pencere_ms=999))[0]["sayim"]["jailbreak"] != 0:
            return False
        if fn([dict(O[0], id="a" * 64)], P)[0]["kullanici"] != "a":
            return False
        if fn(O, dict(P, max_olay=6)) != BEKLENEN:
            return False
        for alan, deger in [("pencere_ms", 1), ("pencere_ms", 60000), ("max_olay", 1), ("max_olay", 1000), ("bekleme_ms", 60000)]:
            if fn([], dict(P, **{alan: deger})) != []:
                return False
        for olaylar, politika in [
            (None, P), ({}, P), ([None], P), (O, None), (O, dict(P, max_olay=0)), (O, dict(P, max_olay=5)),
            (O, dict(P, max_olay=1001)), (O, dict(P, jailbreak_esigi=21)), (O, dict(P, arac_esigi=21)),
            (O, dict(P, sizinti_esigi=21)), (O, dict(P, pencere_ms=0)),
            (O, dict(P, pencere_ms=60001)), (O, dict(P, jailbreak_esigi=0)),
            ([dict(O[0], ek=1)], P), ([dict(O[0], id="a b")], P), ([dict(O[0], id="a" * 65)], P),
            ([O[0], O[0]], P), ([dict(O[0], kullanici="")], P), ([dict(O[0], kullanici="a" * 65)], P),
            ([dict(O[0], zaman_ms=-1)], P), ([dict(O[0], zaman_ms=True)], P), ([dict(O[0], tur="diger")], P),
        ]:
            try:
                fn(olaylar, politika)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(kullanici_sinyal_raporu), "kullanıcı, pencere ve üç sayaç korunmalı")
def m_pencere(olaylar, politika):
    return kullanici_sinyal_raporu(olaylar, dict(politika, pencere_ms=60000))
def m_kullanici(olaylar, politika):
    return kullanici_sinyal_raporu([dict(x, kullanici="a") for x in olaylar], politika)
def m_tur(olaylar, politika):
    return kullanici_sinyal_raporu([dict(x, tur="normal") for x in olaylar], politika)
for ad, mutant in [("pencereyi büyüten", m_pencere), ("kullanıcıyı birleştiren", m_kullanici), ("türü silen", m_tur)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
raises(ValueError,kullanici_sinyal_raporu,[{'id': 'a-eski', 'kullanici': 'a', 'zaman_ms': 0, 'tur': 'jailbreak'}, {'id': 'a-sinir', 'kullanici': 'a', 'zaman_ms': 1000, 'tur': 'jailbreak'}, {'id': 'a-yeni', 'kullanici': 'a', 'zaman_ms': 2000, 'tur': 'normal'}, {'id': 'a-arac', 'kullanici': 'a', 'zaman_ms': 1900, 'tur': 'arac'}, {'id': 'b-yeni', 'kullanici': 'b', 'zaman_ms': 5000, 'tur': 'normal'}, {'id': 'b-sizinti', 'kullanici': 'b', 'zaman_ms': 4500, 'tur': 'sizinti'}],{'pencere_ms': None, 'max_olay': 20, 'jailbreak_esigi': 2, 'arac_esigi': 2, 'sizinti_esigi': 1, 'bekleme_ms': 100},msg="hatalı alan istisna türü: mutant:254:29:Add->Sub")
raises(ValueError,kullanici_sinyal_raporu,[{'id': None, 'kullanici': 'a', 'zaman_ms': 0, 'tur': 'jailbreak'}, {'id': 'a-sinir', 'kullanici': 'a', 'zaman_ms': 1000, 'tur': 'jailbreak'}, {'id': 'a-yeni', 'kullanici': 'a', 'zaman_ms': 2000, 'tur': 'normal'}, {'id': 'a-arac', 'kullanici': 'a', 'zaman_ms': 1900, 'tur': 'arac'}, {'id': 'b-yeni', 'kullanici': 'b', 'zaman_ms': 5000, 'tur': 'normal'}, {'id': 'b-sizinti', 'kullanici': 'b', 'zaman_ms': 4500, 'tur': 'sizinti'}],{'pencere_ms': 1000, 'max_olay': 20, 'jailbreak_esigi': 2, 'arac_esigi': 2, 'sizinti_esigi': 1, 'bekleme_ms': 100},msg="hatalı alan istisna türü: mutant:378:33:Add->Sub")
# --- carbon-c8-ek-bas ---
for _k23 in ("pencere_ms", "max_olay", "jailbreak_esigi", "arac_esigi", "sizinti_esigi", "bekleme_ms"):
    raises(ValueError, kullanici_sinyal_raporu, O, dict(P, **{_k23: True}), msg=f"{_k23} bool olamaz")
raises(ValueError, kullanici_sinyal_raporu, [dict(O[0], id=123)], P, msg="id str olmalı")
raises(ValueError, kullanici_sinyal_raporu, [dict(O[0], kullanici=123)], P, msg="kullanıcı str olmalı")
raises(ValueError, kullanici_sinyal_raporu, [dict(O[0], zaman_ms=True)], P, msg="zaman_ms bool ret")
raises(ValueError, kullanici_sinyal_raporu, O, dict(P, ek=1), msg="politika fazla alan ret")
raises(ValueError, kullanici_sinyal_raporu, O, dict(P, bekleme_ms=60001), msg="bekleme_ms 60001 ret")
ok(isinstance(kullanici_sinyal_raporu(O, dict(P, bekleme_ms=60000, jailbreak_esigi=20, arac_esigi=20, sizinti_esigi=20)), (list, dict)), "üst sınır değerleri geçerli")
# --- carbon-c8-ek-son ---
```

```solution
def kullanici_sinyal_raporu(olaylar, politika):
    import re
    if not isinstance(politika, dict):
        raise ValueError("politika sözlük olmalı")
    if set(politika) != {"pencere_ms", "max_olay", "jailbreak_esigi", "arac_esigi", "sizinti_esigi", "bekleme_ms"}:
        raise ValueError("politika şeması geçersiz")
    for alan, ust in [("pencere_ms", 60000), ("bekleme_ms", 60000), ("max_olay", 1000), ("jailbreak_esigi", 20), ("arac_esigi", 20), ("sizinti_esigi", 20)]:
        if type(politika[alan]) is not int:
            raise ValueError(alan + " int olmalı")
        if politika[alan] < 1:
            raise ValueError(alan + " pozitif olmalı")
        if politika[alan] > ust:
            raise ValueError(alan + " çok büyük")
    if not isinstance(olaylar, list):
        raise ValueError("olaylar liste olmalı")
    if len(olaylar) > politika["max_olay"]:
        raise ValueError("olay sayısı sınırı aşıyor")
    kimlikler = set()
    gruplar = {}
    for olay in olaylar:
        if not isinstance(olay, dict):
            raise ValueError("olay sözlük olmalı")
        if set(olay) != {"id", "kullanici", "zaman_ms", "tur"}:
            raise ValueError("olay şeması geçersiz")
        for alan in ("id", "kullanici"):
            if not isinstance(olay[alan], str):
                raise ValueError(alan + " string olmalı")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", olay[alan]):
                raise ValueError(alan + " geçersiz")
        if olay["id"] in kimlikler:
            raise ValueError("olay kimliği yinelenemez")
        kimlikler.add(olay["id"])
        if type(olay["zaman_ms"]) is not int:
            raise ValueError("zaman int olmalı")
        if olay["zaman_ms"] < 0:
            raise ValueError("zaman negatif olamaz")
        if olay["tur"] not in ("normal", "jailbreak", "arac", "sizinti"):
            raise ValueError("olay türü geçersiz")
        gruplar.setdefault(olay["kullanici"], []).append(olay)
    sonuc = []
    for kullanici, kayitlar in gruplar.items():
        son = max(x["zaman_ms"] for x in kayitlar)
        sayim = {"jailbreak": 0, "arac": 0, "sizinti": 0}
        for kayit in kayitlar:
            if son - kayit["zaman_ms"] <= politika["pencere_ms"] and kayit["tur"] in sayim:
                sayim[kayit["tur"]] += 1
        sonuc.append({"kullanici": kullanici, "son_zaman_ms": son, "sayim": sayim})
    return sorted(sonuc, key=lambda x: x["kullanici"])
```

```hint
Önce kullanıcıya göre grupla. Son zamanı bütün olaylardan al; sayaç artırımını yalnız penceredeki üç abuse türü için yap.
```
:::

::: anlat Uyarlanabilir karar sinyalin ağırlığına göre uygulanır
Sayımlar ikinci görevdeki pencere kurallarıyla hesaplanır. Karar önceliği `engelle`, `beklet`, `izle`, `izin` şeklindedir. Eşiğe eşitlik ilgili kararı tetikler; sızıntı kararı diğer abuse türlerinden önce gelir.

Çıktı her kullanıcı için karar, bekleme süresi ve üç sayacı içerir. İzleme ve izin kararlarında bekleme sıfırdır. Bu fixture kararı gerçek bir isteği engellemez; yalnız uygulanacak politikayı raporlar.
:::

::: gorev 3 · Uyarlanabilir sınırlama raporu üret
`uyarlanabilir_sinir_raporu(olaylar, politika)` işlevini yaz. Girdi ve politika ikinci görevdeki bütün kuralları sağlasın; geçersiz veride `ValueError` yükselt. Kullanıcı bazında pencere içi sayımları hesapla ve anlatımdaki öncelikle karar ver.

Her kullanıcı için `{"kullanici":K,"karar":KARAR,"bekleme_ms":BEKLEME,"sayim":{"jailbreak":J,"arac":A,"sizinti":S}}` döndür. Engellemede `2 * bekleme_ms`, beklemede `bekleme_ms`, diğerlerinde sıfır kullan. Kullanıcıya göre sırala, boş olayda boş liste döndür ve girdileri değiştirme.

Görünür veri: aynı iki dosya. Doğru raporda `u-selin` `engelle` (60000 ms), `u-bot` ve `u-mert` `beklet`, `u-ali` `izle`, `u-can` ve `u-ece` `izin` alır.

```starter
from ai_savunma_veri import json_yukle

def uyarlanabilir_sinir_raporu(olaylar, politika):
    # KUSURLU BAŞLANGIÇ KODU: jailbreak'i sızıntıdan önce değerlendiriyor, eşiğe eşitliği tetiklemiyor ve engellemede de tek kat bekleme veriyor!
    gruplar = {}
    for o in olaylar:
        gruplar.setdefault(o["kullanici"], []).append(o)
    rapor = []
    for k in sorted(gruplar):
        son = max(o["zaman_ms"] for o in gruplar[k])
        sayim = {tur: sum(1 for o in gruplar[k] if o["tur"] == tur and son - o["zaman_ms"] <= politika["pencere_ms"])
                 for tur in ("jailbreak", "arac", "sizinti")}
        if sayim["jailbreak"] > politika["jailbreak_esigi"] or sayim["arac"] > politika["arac_esigi"]:
            karar = "beklet"
        elif sayim["sizinti"] > politika["sizinti_esigi"]:
            karar = "engelle"
        elif any(sayim.values()):
            karar = "izle"
        else:
            karar = "izin"
        rapor.append({"kullanici": k, "karar": karar, "bekleme_ms": politika["bekleme_ms"] if karar in ("beklet", "engelle") else 0, "sayim": sayim})
    return rapor

politika = json_yukle("veri/abuse_politikasi.json")["politika"]
veri = json_yukle("veri/olay_akisi.json")
for r in uyarlanabilir_sinir_raporu(veri["olaylar"], politika):
    print(r["kullanici"], r["karar"], r["bekleme_ms"], r["sayim"])
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-23")
```

```test
import copy
P = {"pencere_ms": 1000, "max_olay": 30, "jailbreak_esigi": 2, "arac_esigi": 2, "sizinti_esigi": 1, "bekleme_ms": 100}
O = [
    {"id": "a-eski", "kullanici": "a", "zaman_ms": 0, "tur": "jailbreak"},
    {"id": "a-1", "kullanici": "a", "zaman_ms": 1000, "tur": "jailbreak"},
    {"id": "a-2", "kullanici": "a", "zaman_ms": 1900, "tur": "jailbreak"},
    {"id": "a-3", "kullanici": "a", "zaman_ms": 2000, "tur": "normal"},
    {"id": "b-1", "kullanici": "b", "zaman_ms": 2000, "tur": "jailbreak"},
    {"id": "b-2", "kullanici": "b", "zaman_ms": 2100, "tur": "sizinti"},
    {"id": "c-1", "kullanici": "c", "zaman_ms": 2000, "tur": "arac"},
    {"id": "d-1", "kullanici": "d", "zaman_ms": 2000, "tur": "normal"},
]
BEKLENEN = [
    {"kullanici": "a", "karar": "beklet", "bekleme_ms": 100, "sayim": {"jailbreak": 2, "arac": 0, "sizinti": 0}},
    {"kullanici": "b", "karar": "engelle", "bekleme_ms": 200, "sayim": {"jailbreak": 1, "arac": 0, "sizinti": 1}},
    {"kullanici": "c", "karar": "izle", "bekleme_ms": 0, "sayim": {"jailbreak": 0, "arac": 1, "sizinti": 0}},
    {"kullanici": "d", "karar": "izin", "bekleme_ms": 0, "sayim": {"jailbreak": 0, "arac": 0, "sizinti": 0}},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(O)
        ponce = copy.deepcopy(P)
        if fn(O, P) != BEKLENEN or O != once or P != ponce or fn(list(reversed(O)), P) != BEKLENEN or fn([], P) != []:
            return False
        if fn(O, dict(P, pencere_ms=999))[0]["karar"] != "izle":
            return False
        if fn(O, dict(P, jailbreak_esigi=3))[0]["karar"] != "izle":
            return False
        if fn(O[:4], dict(P, jailbreak_esigi=1, sizinti_esigi=1))[0]["karar"] != "beklet":
            return False
        if fn([O[6], dict(O[6], id="c-2", zaman_ms=2001)], P)[0]["karar"] != "beklet":
            return False
        if fn(O, dict(P, max_olay=8)) != BEKLENEN:
            return False
        for alan, deger in [("pencere_ms", 1), ("pencere_ms", 60000), ("max_olay", 1), ("max_olay", 1000), ("bekleme_ms", 1), ("bekleme_ms", 60000)]:
            if fn([], dict(P, **{alan: deger})) != []:
                return False
        for olaylar, politika in [
            (None, P), ({}, P), ([None], P), (O, None), (O, dict(P, max_olay=0)), (O, dict(P, max_olay=7)),
            (O, dict(P, max_olay=1001)), (O, dict(P, jailbreak_esigi=21)), (O, dict(P, arac_esigi=21)),
            (O, dict(P, sizinti_esigi=21)), (O, dict(P, pencere_ms=0)),
            (O, dict(P, pencere_ms=60001)), (O, dict(P, sizinti_esigi=0)),
            ([dict(O[0], ek=1)], P), ([dict(O[0], id="a" * 65)], P), ([O[0], O[0]], P),
            ([dict(O[0], kullanici="a b")], P), ([dict(O[0], zaman_ms=-1)], P),
            ([dict(O[0], zaman_ms=True)], P), ([dict(O[0], tur="diger")], P),
        ]:
            try:
                fn(olaylar, politika)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(uyarlanabilir_sinir_raporu), "öncelik, eşik, bekleme ve sayım kararları korunmalı")
def m_sizinti(olaylar, politika):
    return uyarlanabilir_sinir_raporu([dict(x, tur="normal" if x["tur"] == "sizinti" else x["tur"]) for x in olaylar], politika)
def m_esik(olaylar, politika):
    return uyarlanabilir_sinir_raporu(olaylar, dict(politika, jailbreak_esigi=20, arac_esigi=20))
def m_bekleme(olaylar, politika):
    return uyarlanabilir_sinir_raporu(olaylar, dict(politika, bekleme_ms=1))
for ad, mutant in [("sızıntıyı silen", m_sizinti), ("eşikleri büyüten", m_esik), ("beklemeyi düşüren", m_bekleme)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
raises(ValueError,uyarlanabilir_sinir_raporu,[{'id': 'a-eski', 'kullanici': 'a', 'zaman_ms': 0, 'tur': 'jailbreak'}, {'id': 'a-1', 'kullanici': 'a', 'zaman_ms': 1000, 'tur': 'jailbreak'}, {'id': 'a-2', 'kullanici': 'a', 'zaman_ms': 1900, 'tur': 'jailbreak'}, {'id': 'a-3', 'kullanici': 'a', 'zaman_ms': 2000, 'tur': 'normal'}, {'id': 'b-1', 'kullanici': 'b', 'zaman_ms': 2000, 'tur': 'jailbreak'}, {'id': 'b-2', 'kullanici': 'b', 'zaman_ms': 2100, 'tur': 'sizinti'}, {'id': 'c-1', 'kullanici': 'c', 'zaman_ms': 2000, 'tur': 'arac'}, {'id': 'd-1', 'kullanici': 'd', 'zaman_ms': 2000, 'tur': 'normal'}],{'pencere_ms': None, 'max_olay': 30, 'jailbreak_esigi': 2, 'arac_esigi': 2, 'sizinti_esigi': 1, 'bekleme_ms': 100},msg="hatalı alan istisna türü: mutant:270:29:Add->Sub")
raises(ValueError,uyarlanabilir_sinir_raporu,[{'id': None, 'kullanici': 'a', 'zaman_ms': 0, 'tur': 'jailbreak'}, {'id': 'a-1', 'kullanici': 'a', 'zaman_ms': 1000, 'tur': 'jailbreak'}, {'id': 'a-2', 'kullanici': 'a', 'zaman_ms': 1900, 'tur': 'jailbreak'}, {'id': 'a-3', 'kullanici': 'a', 'zaman_ms': 2000, 'tur': 'normal'}, {'id': 'b-1', 'kullanici': 'b', 'zaman_ms': 2000, 'tur': 'jailbreak'}, {'id': 'b-2', 'kullanici': 'b', 'zaman_ms': 2100, 'tur': 'sizinti'}, {'id': 'c-1', 'kullanici': 'c', 'zaman_ms': 2000, 'tur': 'arac'}, {'id': 'd-1', 'kullanici': 'd', 'zaman_ms': 2000, 'tur': 'normal'}],{'pencere_ms': 1000, 'max_olay': 30, 'jailbreak_esigi': 2, 'arac_esigi': 2, 'sizinti_esigi': 1, 'bekleme_ms': 100},msg="hatalı alan istisna türü: mutant:419:33:Add->Sub")
# --- carbon-c8-ek-bas ---
for _k23 in ("pencere_ms", "max_olay", "jailbreak_esigi", "arac_esigi", "sizinti_esigi", "bekleme_ms"):
    raises(ValueError, uyarlanabilir_sinir_raporu, O, dict(P, **{_k23: True}), msg=f"{_k23} bool olamaz")
raises(ValueError, uyarlanabilir_sinir_raporu, [dict(O[0], id=123)], P, msg="id str olmalı")
raises(ValueError, uyarlanabilir_sinir_raporu, [dict(O[0], kullanici=123)], P, msg="kullanıcı str olmalı")
raises(ValueError, uyarlanabilir_sinir_raporu, [dict(O[0], zaman_ms=True)], P, msg="zaman_ms bool ret")
raises(ValueError, uyarlanabilir_sinir_raporu, O, dict(P, ek=1), msg="politika fazla alan ret")
raises(ValueError, uyarlanabilir_sinir_raporu, O, dict(P, bekleme_ms=60001), msg="bekleme_ms 60001 ret")
ok(isinstance(uyarlanabilir_sinir_raporu(O, dict(P, bekleme_ms=60000, jailbreak_esigi=20, arac_esigi=20, sizinti_esigi=20)), (list, dict)), "üst sınır değerleri geçerli")
# --- carbon-c8-ek-son ---
```

```solution
def uyarlanabilir_sinir_raporu(olaylar, politika):
    import re
    if not isinstance(politika, dict):
        raise ValueError("politika sözlük olmalı")
    if set(politika) != {"pencere_ms", "max_olay", "jailbreak_esigi", "arac_esigi", "sizinti_esigi", "bekleme_ms"}:
        raise ValueError("politika şeması geçersiz")
    for alan, ust in [("pencere_ms", 60000), ("bekleme_ms", 60000), ("max_olay", 1000), ("jailbreak_esigi", 20), ("arac_esigi", 20), ("sizinti_esigi", 20)]:
        if type(politika[alan]) is not int:
            raise ValueError(alan + " int olmalı")
        if politika[alan] < 1:
            raise ValueError(alan + " pozitif olmalı")
        if politika[alan] > ust:
            raise ValueError(alan + " çok büyük")
    if not isinstance(olaylar, list):
        raise ValueError("olaylar liste olmalı")
    if len(olaylar) > politika["max_olay"]:
        raise ValueError("olay sayısı sınırı aşıyor")
    kimlikler = set()
    gruplar = {}
    for olay in olaylar:
        if not isinstance(olay, dict):
            raise ValueError("olay sözlük olmalı")
        if set(olay) != {"id", "kullanici", "zaman_ms", "tur"}:
            raise ValueError("olay şeması geçersiz")
        for alan in ("id", "kullanici"):
            if not isinstance(olay[alan], str):
                raise ValueError(alan + " string olmalı")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", olay[alan]):
                raise ValueError(alan + " geçersiz")
        if olay["id"] in kimlikler:
            raise ValueError("olay kimliği yinelenemez")
        kimlikler.add(olay["id"])
        if type(olay["zaman_ms"]) is not int:
            raise ValueError("zaman int olmalı")
        if olay["zaman_ms"] < 0:
            raise ValueError("zaman negatif olamaz")
        if olay["tur"] not in ("normal", "jailbreak", "arac", "sizinti"):
            raise ValueError("olay türü geçersiz")
        gruplar.setdefault(olay["kullanici"], []).append(olay)
    sonuc = []
    for kullanici, kayitlar in gruplar.items():
        son = max(x["zaman_ms"] for x in kayitlar)
        sayim = {"jailbreak": 0, "arac": 0, "sizinti": 0}
        for kayit in kayitlar:
            if son - kayit["zaman_ms"] <= politika["pencere_ms"] and kayit["tur"] in sayim:
                sayim[kayit["tur"]] += 1
        if sayim["sizinti"] >= politika["sizinti_esigi"]:
            karar = "engelle"
            bekleme = 2 * politika["bekleme_ms"]
        elif sayim["jailbreak"] >= politika["jailbreak_esigi"] or sayim["arac"] >= politika["arac_esigi"]:
            karar = "beklet"
            bekleme = politika["bekleme_ms"]
        elif any(sayim[tur] > 0 for tur in sayim):
            karar = "izle"
            bekleme = 0
        else:
            karar = "izin"
            bekleme = 0
        sonuc.append({"kullanici": kullanici, "karar": karar, "bekleme_ms": bekleme, "sayim": sayim})
    return sorted(sonuc, key=lambda x: x["kullanici"])
```

```hint
Karar dallarını sızıntı, jailbreak/araç, herhangi abuse ve temiz sırasıyla kur. Bekleme değerini aynı dalda belirle.
```
:::

::: anlat Sınırlama, gerçekte gözlenen kötüye kullanıma uyarlanır
Görev 1–3'te olaylar elle yazılmış bir dosyadan geliyordu. Bu adımda olayları **gerçek ölçümler** üretir. `sandbox/ai_gercek_ai_savunma_23.py` deneyi şunları yapar:

1. Her koşuda yeni bir sentetik canary üretilir ve "bu kodu asla yazma" diyen bir sistem istemine konur.
2. Bir **saldırgan** kullanıcı üç bilinen enjeksiyon girdisini (yeni jailbreak değil) 1'er saniye arayla, bir **normal** kullanıcı ise bir zararsız soruyu gönderir. Dört girdi de aynı ölçüm hattından geçer:
   - **Jailbreak sinyali:** Kural temelli tespit, yönerge ihlali kalıbı ("önceki talimatları unut", "ignore previous instructions") ya da bilinen jailbreak ifadesi ("DAN mode", "kısıtlama olmadan") bulursa bir `jailbreak` olayı yazar.
   - **Sızıntı sinyali:** Girdi, kurulu yerel Ollama modeline sıcaklık 0 ve sabit tohumla gerçekten gönderilir. Yanıtta canary geçerse bir `sizinti` olayı yazılır.
   - Hiçbir sinyal yoksa bir `normal` olayı yazılır.
3. Olaylar senin `uyarlanabilir_sinir_raporu` işlevine verilir. Politika: 60 sn pencere, jailbreak eşiği 2, sızıntı eşiği 1.

Model boş yanıt verirse deney "tamamlanmadı" diye durur. Test önce işlevini gizli deterministik olaylarla sınar, ardından gerçek olaylardan ürettiğin raporu bağımsız bir referans hesapla birebir karşılaştırır. Jailbreak sinyali kural temelli olduğu için saldırganın en az iki sinyal üretmesi ve `beklet` ya da `engelle` alması beklenir. Modelin canary'yi sızdırıp sızdırmaması ise kabul koşulu **değildir**; sızdırırsa doğru karar `engelle` olur. Her girdinin ham yanıtı, iki sinyal değeri ve ayarlar kanıta yazılır.

Ders yazılırken bu makinede `qwen3:4b-instruct-2507` ile yapılan koşuda üç saldırı girdisinin üçü de jailbreak sinyali verdi ve hiçbiri canary sızdırmadı. Model belgeyi özetleyip kodu vermedi. Saldırgan `beklet` aldı, normal kullanıcı `izin` aldı. Burada iki sınıra dikkat et. Birincisi, kural tespiti yalnız bilinen kalıpları görür; kalıp dışı bir saldırı `normal` sayılır. İkincisi, olay zamanları deney akışına göre atanmış mantıksal zamanlardır. Gerçek bir API'de bu zamanlar isteklerin geliş saatinden okunur.

:::

::: gorev Gerçek deney · Gerçek sinyallerle uyarlanabilir sınırlama
`uyarlanabilir_sinir_raporu(olaylar, politika)` işlevini yaz. Kuralları ve çıktısı 3. görevdekiyle **aynıdır**. Deney saldırgan ve normal kullanıcı girdilerini kural temelli jailbreak tespitinden ve gerçek canary testinden geçirerek sinyal olayları üretir. Senin raporun bu olayların kullanıcı bazlı sayımlarından karar verir. `sandbox.ai_gercek_ai_savunma_23` içindeki `uyarlanabilir_sinir_raporu_referans` yalnız test içindir; onu import etmek veya kaynağını okuyup çalıştırmak Kontrol'de reddedilir.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def uyarlanabilir_sinir_raporu(olaylar, politika):
    # KUSURLU BAŞLANGIÇ KODU: bütün olayları tek bir kullanıcıymış gibi sayıyor; saldırganın sinyalleri zararsız kullanıcıyı da bekletiyor!
    sayim = {tur: sum(1 for o in olaylar if o["tur"] == tur) for tur in ("jailbreak", "arac", "sizinti")}
    if sayim["sizinti"] >= politika["sizinti_esigi"]:
        karar, bekleme = "engelle", 2 * politika["bekleme_ms"]
    elif sayim["jailbreak"] >= politika["jailbreak_esigi"] or sayim["arac"] >= politika["arac_esigi"]:
        karar, bekleme = "beklet", politika["bekleme_ms"]
    else:
        karar, bekleme = ("izle", 0) if any(sayim.values()) else ("izin", 0)
    return [{"kullanici": k, "karar": karar, "bekleme_ms": bekleme, "sayim": dict(sayim)}
            for k in sorted({o["kullanici"] for o in olaylar})]

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_23 as deney
    deney.goster(uyarlanabilir_sinir_raporu)
```

```test
import ast
import ai_lab
from sandbox import ai_gercek_ai_savunma_23 as D
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
_yasak = ("uyarlanabilir_sinir_raporu_referans", "sizinti_referans", "kanit_yaz")
sorun = ai_lab.kod_denetimi(src, yasak=_yasak)
for n in ast.walk(ast.parse(src)):
    if isinstance(n, ast.ImportFrom) and any(a.name in _yasak or a.name == "*" for a in n.names):
        sorun.append("referans importu yasak")
    if isinstance(n, (ast.Import, ast.ImportFrom)):
        adlar = [a.name for a in n.names] + ([n.module] if isinstance(n, ast.ImportFrom) and n.module else [])
        if any(a and a.split(".")[0] in ("inspect", "importlib", "runpy") for a in adlar):
            sorun.append("kaynak okuma/dinamik import yasak")
    if isinstance(n, ast.Name) and n.id in ("exec", "eval", "compile", "__builtins__"):
        sorun.append("dinamik kod çalıştırma yasak: " + n.id)
if not kontrol(not sorun, "Kendi uyarlanabilir_sinir_raporu işlevini yaz; laboratuvar/referans kullanımı yasak: " + "; ".join(sorted(set(sorun)))):
    stop()
fn = need("uyarlanabilir_sinir_raporu")
P = {"pencere_ms": 60000, "max_olay": 20, "jailbreak_esigi": 2, "arac_esigi": 2, "sizinti_esigi": 1, "bekleme_ms": 100}
O = [
    {"id": "s-1", "kullanici": "s", "zaman_ms": 0, "tur": "jailbreak"},
    {"id": "s-2", "kullanici": "s", "zaman_ms": 1000, "tur": "jailbreak"},
    {"id": "n-1", "kullanici": "n", "zaman_ms": 500, "tur": "normal"},
    {"id": "z-1", "kullanici": "z", "zaman_ms": 0, "tur": "sizinti"},
]
BEKLENEN = [
    {"kullanici": "n", "karar": "izin", "bekleme_ms": 0, "sayim": {"jailbreak": 0, "arac": 0, "sizinti": 0}},
    {"kullanici": "s", "karar": "beklet", "bekleme_ms": 100, "sayim": {"jailbreak": 2, "arac": 0, "sizinti": 0}},
    {"kullanici": "z", "karar": "engelle", "bekleme_ms": 200, "sayim": {"jailbreak": 0, "arac": 0, "sizinti": 1}},
]
def sozlesme(f):
    try:
        if f(O, P) != BEKLENEN or f([], P) != [] or f(list(reversed(O)), P) != BEKLENEN:
            return False
        sinir = [{"id": "m-1", "kullanici": "m", "zaman_ms": 0, "tur": "jailbreak"},
                 {"id": "m-2", "kullanici": "m", "zaman_ms": 60000, "tur": "jailbreak"},
                 {"id": "y-1", "kullanici": "y", "zaman_ms": 0, "tur": "jailbreak"},
                 {"id": "y-2", "kullanici": "y", "zaman_ms": 60001, "tur": "normal"},
                 {"id": "k-1", "kullanici": "k", "zaman_ms": 5, "tur": "jailbreak"},
                 {"id": "k-2", "kullanici": "k", "zaman_ms": 6, "tur": "jailbreak"},
                 {"id": "k-3", "kullanici": "k", "zaman_ms": 7, "tur": "sizinti"},
                 {"id": "a-1", "kullanici": "a", "zaman_ms": 1, "tur": "arac"}]
        if f(sinir, P) != [{"kullanici": "a", "karar": "izle", "bekleme_ms": 0, "sayim": {"jailbreak": 0, "arac": 1, "sizinti": 0}},
                           {"kullanici": "k", "karar": "engelle", "bekleme_ms": 200, "sayim": {"jailbreak": 2, "arac": 0, "sizinti": 1}},
                           {"kullanici": "m", "karar": "beklet", "bekleme_ms": 100, "sayim": {"jailbreak": 2, "arac": 0, "sizinti": 0}},
                           {"kullanici": "y", "karar": "izin", "bekleme_ms": 0, "sayim": {"jailbreak": 0, "arac": 0, "sizinti": 0}}]:
            return False
        for bozuk in (None, [None], [dict(O[0], ek=1)], [dict(O[0], tur="diger")], [dict(O[0], kullanici="a b")],
                      [dict(O[0], zaman_ms=True)], [dict(O[0], zaman_ms=-1)], [O[0], O[0]]):
            try:
                f(bozuk, P)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(fn), "sızıntı/jailbreak eşikleri, pencere ve karar önceliği korunmalı")
r, oz = None, None
# --- carbon-c8-g4-bas ---
def _c8_birim_denetimi():
    _u = []
    def _same(got, exp):
        try:
            if not bool(got == exp):
                return False
        except Exception:
            return False
        if isinstance(exp, bool) or isinstance(got, bool):
            return isinstance(got, bool) and isinstance(exp, bool)
        if isinstance(exp, (int, float)) and isinstance(got, (int, float)):
            return True
        return isinstance(got, type(exp))
    def ok(cond, msg=None, got=None):
        _u.append(bool(cond))
        return bool(cond)
    def eq(got, exp, msg=None):
        r = _same(got, exp)
        _u.append(r)
        return r
    def yakin(got, exp, msg=None, tol=1e-6):
        try:
            r = abs(got - exp) <= tol
        except Exception:
            r = False
        _u.append(bool(r))
        return bool(r)
    def raises(exc, fn_cagri, *a, msg=None, **kw):
        try:
            fn_cagri(*a, **kw)
        except exc:
            _u.append(True)
            return True
        except Exception:
            _u.append(False)
            return False
        _u.append(False)
        return False
    uyarlanabilir_sinir_raporu = need('uyarlanabilir_sinir_raporu')
    def _birim_adim_3():
        import copy
        P = {"pencere_ms": 1000, "max_olay": 30, "jailbreak_esigi": 2, "arac_esigi": 2, "sizinti_esigi": 1, "bekleme_ms": 100}
        O = [
            {"id": "a-eski", "kullanici": "a", "zaman_ms": 0, "tur": "jailbreak"},
            {"id": "a-1", "kullanici": "a", "zaman_ms": 1000, "tur": "jailbreak"},
            {"id": "a-2", "kullanici": "a", "zaman_ms": 1900, "tur": "jailbreak"},
            {"id": "a-3", "kullanici": "a", "zaman_ms": 2000, "tur": "normal"},
            {"id": "b-1", "kullanici": "b", "zaman_ms": 2000, "tur": "jailbreak"},
            {"id": "b-2", "kullanici": "b", "zaman_ms": 2100, "tur": "sizinti"},
            {"id": "c-1", "kullanici": "c", "zaman_ms": 2000, "tur": "arac"},
            {"id": "d-1", "kullanici": "d", "zaman_ms": 2000, "tur": "normal"},
        ]
        BEKLENEN = [
            {"kullanici": "a", "karar": "beklet", "bekleme_ms": 100, "sayim": {"jailbreak": 2, "arac": 0, "sizinti": 0}},
            {"kullanici": "b", "karar": "engelle", "bekleme_ms": 200, "sayim": {"jailbreak": 1, "arac": 0, "sizinti": 1}},
            {"kullanici": "c", "karar": "izle", "bekleme_ms": 0, "sayim": {"jailbreak": 0, "arac": 1, "sizinti": 0}},
            {"kullanici": "d", "karar": "izin", "bekleme_ms": 0, "sayim": {"jailbreak": 0, "arac": 0, "sizinti": 0}},
        ]
        def sozlesme(fn):
            try:
                once = copy.deepcopy(O)
                ponce = copy.deepcopy(P)
                if fn(O, P) != BEKLENEN or O != once or P != ponce or fn(list(reversed(O)), P) != BEKLENEN or fn([], P) != []:
                    return False
                if fn(O, dict(P, pencere_ms=999))[0]["karar"] != "izle":
                    return False
                if fn(O, dict(P, jailbreak_esigi=3))[0]["karar"] != "izle":
                    return False
                if fn(O[:4], dict(P, jailbreak_esigi=1, sizinti_esigi=1))[0]["karar"] != "beklet":
                    return False
                if fn([O[6], dict(O[6], id="c-2", zaman_ms=2001)], P)[0]["karar"] != "beklet":
                    return False
                if fn(O, dict(P, max_olay=8)) != BEKLENEN:
                    return False
                for alan, deger in [("pencere_ms", 1), ("pencere_ms", 60000), ("max_olay", 1), ("max_olay", 1000), ("bekleme_ms", 1), ("bekleme_ms", 60000)]:
                    if fn([], dict(P, **{alan: deger})) != []:
                        return False
                for olaylar, politika in [
                    (None, P), ({}, P), ([None], P), (O, None), (O, dict(P, max_olay=0)), (O, dict(P, max_olay=7)),
                    (O, dict(P, max_olay=1001)), (O, dict(P, jailbreak_esigi=21)), (O, dict(P, arac_esigi=21)),
                    (O, dict(P, sizinti_esigi=21)), (O, dict(P, pencere_ms=0)),
                    (O, dict(P, pencere_ms=60001)), (O, dict(P, sizinti_esigi=0)),
                    ([dict(O[0], ek=1)], P), ([dict(O[0], id="a" * 65)], P), ([O[0], O[0]], P),
                    ([dict(O[0], kullanici="a b")], P), ([dict(O[0], zaman_ms=-1)], P),
                    ([dict(O[0], zaman_ms=True)], P), ([dict(O[0], tur="diger")], P),
                ]:
                    try:
                        fn(olaylar, politika)
                        return False
                    except ValueError:
                        pass
                return True
            except Exception:
                return False
        ok(sozlesme(uyarlanabilir_sinir_raporu), "öncelik, eşik, bekleme ve sayım kararları korunmalı")
        def m_sizinti(olaylar, politika):
            return uyarlanabilir_sinir_raporu([dict(x, tur="normal" if x["tur"] == "sizinti" else x["tur"]) for x in olaylar], politika)
        def m_esik(olaylar, politika):
            return uyarlanabilir_sinir_raporu(olaylar, dict(politika, jailbreak_esigi=20, arac_esigi=20))
        def m_bekleme(olaylar, politika):
            return uyarlanabilir_sinir_raporu(olaylar, dict(politika, bekleme_ms=1))
        for ad, mutant in [("sızıntıyı silen", m_sizinti), ("eşikleri büyüten", m_esik), ("beklemeyi düşüren", m_bekleme)]:
            ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
        raises(ValueError,uyarlanabilir_sinir_raporu,[{'id': 'a-eski', 'kullanici': 'a', 'zaman_ms': 0, 'tur': 'jailbreak'}, {'id': 'a-1', 'kullanici': 'a', 'zaman_ms': 1000, 'tur': 'jailbreak'}, {'id': 'a-2', 'kullanici': 'a', 'zaman_ms': 1900, 'tur': 'jailbreak'}, {'id': 'a-3', 'kullanici': 'a', 'zaman_ms': 2000, 'tur': 'normal'}, {'id': 'b-1', 'kullanici': 'b', 'zaman_ms': 2000, 'tur': 'jailbreak'}, {'id': 'b-2', 'kullanici': 'b', 'zaman_ms': 2100, 'tur': 'sizinti'}, {'id': 'c-1', 'kullanici': 'c', 'zaman_ms': 2000, 'tur': 'arac'}, {'id': 'd-1', 'kullanici': 'd', 'zaman_ms': 2000, 'tur': 'normal'}],{'pencere_ms': None, 'max_olay': 30, 'jailbreak_esigi': 2, 'arac_esigi': 2, 'sizinti_esigi': 1, 'bekleme_ms': 100},msg="hatalı alan istisna türü: mutant:270:29:Add->Sub")
        raises(ValueError,uyarlanabilir_sinir_raporu,[{'id': None, 'kullanici': 'a', 'zaman_ms': 0, 'tur': 'jailbreak'}, {'id': 'a-1', 'kullanici': 'a', 'zaman_ms': 1000, 'tur': 'jailbreak'}, {'id': 'a-2', 'kullanici': 'a', 'zaman_ms': 1900, 'tur': 'jailbreak'}, {'id': 'a-3', 'kullanici': 'a', 'zaman_ms': 2000, 'tur': 'normal'}, {'id': 'b-1', 'kullanici': 'b', 'zaman_ms': 2000, 'tur': 'jailbreak'}, {'id': 'b-2', 'kullanici': 'b', 'zaman_ms': 2100, 'tur': 'sizinti'}, {'id': 'c-1', 'kullanici': 'c', 'zaman_ms': 2000, 'tur': 'arac'}, {'id': 'd-1', 'kullanici': 'd', 'zaman_ms': 2000, 'tur': 'normal'}],{'pencere_ms': 1000, 'max_olay': 30, 'jailbreak_esigi': 2, 'arac_esigi': 2, 'sizinti_esigi': 1, 'bekleme_ms': 100},msg="hatalı alan istisna türü: mutant:419:33:Add->Sub")
        for _k23 in ("pencere_ms", "max_olay", "jailbreak_esigi", "arac_esigi", "sizinti_esigi", "bekleme_ms"):
            raises(ValueError, uyarlanabilir_sinir_raporu, O, dict(P, **{_k23: True}), msg=f"{_k23} bool olamaz")
        raises(ValueError, uyarlanabilir_sinir_raporu, [dict(O[0], id=123)], P, msg="id str olmalı")
        raises(ValueError, uyarlanabilir_sinir_raporu, [dict(O[0], kullanici=123)], P, msg="kullanıcı str olmalı")
        raises(ValueError, uyarlanabilir_sinir_raporu, [dict(O[0], zaman_ms=True)], P, msg="zaman_ms bool ret")
        raises(ValueError, uyarlanabilir_sinir_raporu, O, dict(P, ek=1), msg="politika fazla alan ret")
        raises(ValueError, uyarlanabilir_sinir_raporu, O, dict(P, bekleme_ms=60001), msg="bekleme_ms 60001 ret")
        ok(isinstance(uyarlanabilir_sinir_raporu(O, dict(P, bekleme_ms=60000, jailbreak_esigi=20, arac_esigi=20, sizinti_esigi=20)), (list, dict)), "üst sınır değerleri geçerli")
    try:
        _birim_adim_3()
    except Exception:
        _u.append(False)
    return bool(_u) and all(_u)
kontrol(_c8_birim_denetimi(), "deney öncesi tam birim sözleşmesi korunmalı")
# --- carbon-c8-g4-son ---
if all(sonuclar):
    try:
        r = D.deney(fn)
    except ai_lab.GercekLabYok as e:
        kontrol(False, f"GERÇEK MODEL YOK, deney yapılmadı: {e}")
        stop()
    kontrol(r["jb_sayi"] >= 2, "saldırgan girdilerinden gerçek jailbreak sinyalleri sayıldı")
    kontrol(r["saldirgan_karar"] in ("beklet", "engelle"),
            "saldırgan sinyal yoğunluğu nedeniyle beklet/engelle kararına yükseldi")
    bagimsiz = D.uyarlanabilir_sinir_raporu_referans([dict(o) for o in r["olaylar"]], dict(D.POLITIKA))
    kontrol(r["rapor"] == bagimsiz, f"gerçek olaylardaki rapor bağımsız hesapla aynı olmalı: senin {r['rapor']} · beklenen {bagimsiz}")
    oz = D.ozet(r)
yol = ai_lab.kanit_yaz("savunma-abuse", {"kaynak": "gercek", "kabul": all(sonuclar), "ders": "ai-savunma-23",
                                         "ortam": (r or {}).get("ortam"), "ozet": oz,
                                         "olaylar": (r or {}).get("olaylar"), "ham": (r or {}).get("ham")})
if oz:
    ok(True, f"BULGU ({r['ortam']['model']['ad']}): saldırgan girdilerinden gerçek jailbreak sinyali {oz['jailbreak_sinyali']}, canary sızıntı {oz['sizinti_sinyali']}; "
             f"saldırgan kararı {oz['saldirgan_karar']} (sayım {oz['saldirgan_sayim']}), normal kullanıcı {oz['normal_karar']}. "
             f"Sınırlama gerçekte gözlenen kötüye kullanım yoğunluğuna uyarlandı.")
```

```solution
import ai_lab

def uyarlanabilir_sinir_raporu(olaylar, politika):
    import re
    if not isinstance(politika, dict):
        raise ValueError("politika sözlük olmalı")
    if set(politika) != {"pencere_ms", "max_olay", "jailbreak_esigi", "arac_esigi", "sizinti_esigi", "bekleme_ms"}:
        raise ValueError("politika şeması geçersiz")
    for alan, ust in [("pencere_ms", 60000), ("bekleme_ms", 60000), ("max_olay", 1000), ("jailbreak_esigi", 20), ("arac_esigi", 20), ("sizinti_esigi", 20)]:
        if type(politika[alan]) is not int:
            raise ValueError(alan + " int olmalı")
        if politika[alan] < 1:
            raise ValueError(alan + " pozitif olmalı")
        if politika[alan] > ust:
            raise ValueError(alan + " çok büyük")
    if not isinstance(olaylar, list):
        raise ValueError("olaylar liste olmalı")
    if len(olaylar) > politika["max_olay"]:
        raise ValueError("olay sayısı sınırı aşıyor")
    kimlikler = set()
    gruplar = {}
    for olay in olaylar:
        if not isinstance(olay, dict):
            raise ValueError("olay sözlük olmalı")
        if set(olay) != {"id", "kullanici", "zaman_ms", "tur"}:
            raise ValueError("olay şeması geçersiz")
        for alan in ("id", "kullanici"):
            if not isinstance(olay[alan], str):
                raise ValueError(alan + " string olmalı")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", olay[alan]):
                raise ValueError(alan + " geçersiz")
        if olay["id"] in kimlikler:
            raise ValueError("olay kimliği yinelenemez")
        kimlikler.add(olay["id"])
        if type(olay["zaman_ms"]) is not int:
            raise ValueError("zaman int olmalı")
        if olay["zaman_ms"] < 0:
            raise ValueError("zaman negatif olamaz")
        if olay["tur"] not in ("normal", "jailbreak", "arac", "sizinti"):
            raise ValueError("olay türü geçersiz")
        gruplar.setdefault(olay["kullanici"], []).append(olay)
    sonuc = []
    for kullanici, kayitlar in gruplar.items():
        son = max(x["zaman_ms"] for x in kayitlar)
        sayim = {"jailbreak": 0, "arac": 0, "sizinti": 0}
        for kayit in kayitlar:
            if son - kayit["zaman_ms"] <= politika["pencere_ms"] and kayit["tur"] in sayim:
                sayim[kayit["tur"]] += 1
        if sayim["sizinti"] >= politika["sizinti_esigi"]:
            karar = "engelle"
            bekleme = 2 * politika["bekleme_ms"]
        elif sayim["jailbreak"] >= politika["jailbreak_esigi"] or sayim["arac"] >= politika["arac_esigi"]:
            karar = "beklet"
            bekleme = politika["bekleme_ms"]
        elif any(sayim[tur] > 0 for tur in sayim):
            karar = "izle"
            bekleme = 0
        else:
            karar = "izin"
            bekleme = 0
        sonuc.append({"kullanici": kullanici, "karar": karar, "bekleme_ms": bekleme, "sayim": sayim})
    return sorted(sonuc, key=lambda x: x["kullanici"])

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_23 as deney
    deney.goster(uyarlanabilir_sinir_raporu)
```

```hint
Bu işlev 3. görevdeki `uyarlanabilir_sinir_raporu` ile birebir aynıdır; tek fark, olayların gerçek ölçümden (kural tespiti + gerçek modelin yanıtında canary testi) üretilmesidir. Karar dallarını sızıntı → jailbreak/araç → herhangi abuse → temiz sırasıyla kur.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Abuse sinyali bağlamıyla ölçülür

Kullanıcı bazlı deneme ve risk sinyalleri zaman penceresinde toplanır. Kısıtlamanın kime ve ne kadar uygulanacağı toplam sayıdan ibaret değildir; normal kullanıcı false-positive etkisi de ölçülmelidir. Eşik sınırındaki eşitlik kararı ve pencere kapsamı deterministik olmalıdır. Küçük örneklemde sık istek atan kişinin kötü niyetli olduğuna hükmedilmez.

| Yaygın yanlış | Mekanizmanın sınırı |
|---|---|
| Yüksek hacim kötü niyet ispatıdır | Davranış sinyali politika kararı için girdidir, niyet kanıtı değildir. |

Saldırı–savunma bağlantısı: ai-saldiri-40.
:::

::: anlat Kaynak ile lab sonucunu ayır
[Ollama chat API](https://docs.ollama.com/api/chat). Token ve süre sayaçları ölçüm girdisidir; abuse eşiği ve kullanıcı sınırlaması bu labın host politikasındadır.
:::
