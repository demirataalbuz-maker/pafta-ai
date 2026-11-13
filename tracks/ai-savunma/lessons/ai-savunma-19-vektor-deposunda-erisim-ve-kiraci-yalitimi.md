---
id: ai-savunma-19
title: Vektör Deposunda Erişim ve Kiracı Yalıtımı
summary: Vektör getirme politikasını doğrula, kiracı filtresi ve sonuç sınırlarını zorunlu kıl, çapraz kiracı kayıtlarını bağlam dışında tut.
esleme: ai-saldiri-08, ai-saldiri-15
timeout: 45
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et: Benzerlik araması yetki kontrolünün yerine geçmez

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Qdrant çok kiracılı kullanımda her noktanın payload'ına bir kiracı alanı koyar. Arama isteği bu alana bir `filter` ekler (ör. `must: [{key: "tenant", match: {value: ...}}]`). Ayrı koleksiyon ya da ayrı sunucu da kullanılabilir. Uygulama katmanı kiracıyı oturumdan alır, istemciden almaz. | Görev 1–3: `veri/vektor_politikasi.json`, `veri/vektor_sorgulari.json` ve `veri/vektor_kayitlari.json` içindeki **sentetik** politika, sorgu ve ham arama sonuçları. Son adım: kurulu `all-minilm:22m` embedding modeli bir sorgu ve üç kayıt için gerçek vektör üretir. Kosinüs skorlarıyla sıralanan kayıtlar senin işlevinle kiracı yalıtımından geçer. | Bu ders veritabanı düzeyinde filtrelemeyi değil, getirme sonrasındaki ikinci kontrolü uygular. Üç kayıtlık deney, gerçek bir depodaki indeks ayrımını, yedekleri ya da embedding vektörlerinden veri sızmasını kapsamaz. |

> [!NOT]
> Görev 1–3 sentetik veriyle çalışır. Bu görevlerde gömme modeli, Qdrant veya FastAPI çağrılmaz. Son adımdaki **Gerçek deney** görevi kurulu yerel Ollama gömme modelini gerçekten çalıştırır; Qdrant çalıştırılmaz, yeni model indirilmez. `veri/` dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalanır; kopyada yaptığın değişiklik bir sonraki çalıştırmada sıfırlanır, **kalıcılık yoktur**. Kontrol bu dosyalardan ayrı, gizli verilerle sınar.

Qdrant gibi bir vektör deposu en yakın kayıtları bulabilir; ancak yüksek benzerlik skoru, kaydı görmeye yetkili olunduğunu göstermez. Sorgu kimliği doğrulanır, kiracı filtresi zorunlu tutulur ve getirme sonrasında da kiracı eşleşmesi yeniden denetlenir.

Görev 1–3'te sorgular ve depo kayıtları sentetiktir; son adımda skorlar gerçek bir gömme modelinden gelir. Amaç, erişim politikasının fail-closed biçimde sınanmasıdır.

Politika doğrulaması bütün giriş noktalarında aynı olmalıdır; sorgu veya sonuç listesi boş olsa da yinelenen/bozuk kiracı listesi kabul edilmez. Kimlik türünü hash tabanlı tekilleştirmeden önce denetle, yoksa bozuk liste elemanı ValueError yerine TypeError üretir.

**Neden iki kez filtrelenir?** Çok kiracılı RAG sistemlerinde en sık hata, kiracı filtresinin "çoğu" sorguya eklenip birine eklenmemesidir. Bu, yeni eklenen bir uç nokta, bir hata ayıklama aracı ya da bir toplu yeniden indeksleme betiği olabilir. Filtre eksik kaldığında arama bütün kiracıların vektörlerinde yapılır. En benzer kayıt başka bir müşterinin sözleşmesi ise modele o gider ve yanıtta görünür. Getirme sonrasında kiracıyı yeniden denetlemek bu hatayı ikinci bir kapıda yakalar (defense in depth).

**Saldırgan bakışı:** Bir kiracının kullanıcısı başka kiracının verisini görmek ister. Bunun yolları:

- İstemcinin gönderdiği `filtre_kiraci` değerini değiştirmek (`veri/vektor_sorgulari.json` içindeki `q-filtre-oyunu`).
- Çok büyük bir `top_k` isteyerek eşiğin altındaki ya da filtrede kaçak kalan kayıtları da çekmek (`q-genis`).
- Sorguyu başka kiracının belgelerine çok benzeyecek biçimde yazmak, böylece o belgelerin skorunu yükseltmek.

İlk iki yolu politika kapatır. Üçüncü yolda gizlilik için yetkisiz kayıtların bağlama hiç girmemesi gerekir. Depoda tenant filtresi top-k aday seçimine dahil olmalı; uygulamadaki ikinci kontrol savunma katmanıdır. Ham top-k zaten kesildiyse sonradan filtreleme yabancı kaydı çıkarır ama eksik kalan yetkili adayları geri getiremez. `veri/vektor_kayitlari.json` içinde en yüksek skorlu iki kayıt başka kiracıya aittir.
:::

::: anlat Kiracı kimlikleri ve skorlar katı biçimde doğrulanır
Kiracı ve kayıt kimlikleri ASCII harf/rakamla başlar; yalnız ASCII harf, rakam, alt çizgi ve tire içerir. Bu dersin skor protokolü bool olmayan, sonlu ve 0–1 aralığında sayıdır. Ham kosinüs benzerliği -1–1 aralığında olabilir; gerçek deney skoru altı basamağa yuvarlayıp [0,1] aralığına kırpar. Bu monoton, negatif bölgeyi birleştiren öğretici dönüşümdür; başka vektör deposunda aynı eşik doğrudan kullanılamaz. Alt skor eşiğine eşit kayıt kabul edilir.

`top_k` pozitif bir tam sayıdır. Politika üst sınırını aşan sorgu kırpılmaz; reddedilir. Böylece istemci geniş bir sonuç kümesi isteyerek veri maruziyetini artıramaz.

**Sık tuzaklar:**

- **Filtreyi istemciden almak:** Doğru kiracı oturumdan gelir. İstemcinin gönderdiği filtre yalnız oturumla **eşleşiyorsa** kabul edilir.
- **Aşırı `top_k` değerini sessizce kırpmak:** Kırpma, istemciye "sınırı zorlamak zararsız" mesajı verir ve kötüye kullanımı loglarda görünmez kılar. Ret ise görünür bir olaydır.
- **Top-k kesimini filtreden önce uygulamak:** Tenant ve skor koşulları aynı aday kümesinde birlikte uygulanabilir; sorun önce `top_k` ile kesip sonra kiracı filtresi uygulamaktır. Bu durumda en yüksek skorlu yabancı kayıtlar kotayı doldurur ve meşru kayıtlar hiç dönmez.
- **Eşitlik:** Skoru eşiğe eşit olan kayıt kabul edilir (`a-sinir`). Eşit skorlu kayıtlar kimlik sırasıyla dizilir; sonuç deterministik olur.
:::

::: tahmin Kiracı ve skor sıralamasını tahmin et
Üç çıktı satırını yaz:

```python
sorgu = {"kiraci": "a", "filtre_kiraci": "a", "top_k": 2}
print(sorgu["kiraci"] == sorgu["filtre_kiraci"])
kayitlar = [{"id": "b-1", "skor": 0.8}, {"id": "a-1", "skor": 0.8}]
print([x["id"] for x in sorted(kayitlar, key=lambda x: (-x["skor"], x["id"]))])
print(0.8 >= 0.8)
```

???

```cikti
True
['a-1', 'b-1']
True
```

Skor eşitliğinde kimlik sıralaması deterministik çıktı sağlar. Kiracı eşitliği ise ayrı bir yetki koşuludur.
:::

::: gorev 1 · Vektör erişim politikasını doğrula
`vektor_politikasi_dogrula(politika)` işlevini yaz. Politika tam olarak `izinli_kiracilar`, `min_skor`, `max_top_k`, `filtre_zorunlu`, `capraz_kiraci` alanlarını taşısın. İzinli kiracılar boş olmayan, yinelenmeyen listedir; her kimlik 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren stringdir.

Skor eşiği bool olmayan, sonlu ve 0–1 aralığında int veya float; sonuç sınırı bool olmayan 1–20 arası int olmalıdır. `filtre_zorunlu` gerçek `True`, `capraz_kiraci` gerçek `False` olmalıdır. Geçersiz veride `ValueError` yükselt.

Politikayı yeni listeyle döndür; girdiyi değiştirme.

Görünür veri: `veri/vektor_politikasi.json`. Asıl politika kabul edilmeli, beş bozuk politika reddedilmelidir.

```starter
from ai_savunma_veri import json_yukle

def vektor_politikasi_dogrula(politika):
    # KUSURLU BAŞLANGIÇ KODU: yalnız kiracı listesinin boş olmadığına bakıyor; bayrakları, joker kiracıyı, top_k sınırını ve bool skoru denetlemiyor, girdinin kendisini döndürüyor!
    if not politika.get("izinli_kiracilar"):
        raise ValueError("kiracı listesi boş olamaz")
    return politika

veri = json_yukle("veri/vektor_politikasi.json")
for ad, p in [("asil", veri["politika"])] + [(b["ad"], b["politika"]) for b in veri["bozuk_politikalar"]]:
    try:
        vektor_politikasi_dogrula(p)
        print(ad, "kabul")
    except ValueError as hata:
        print(ad, "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-19")
```

```test
import copy
P = {"izinli_kiracilar": ["a", "b"], "min_skor": 0.8, "max_top_k": 5, "filtre_zorunlu": True, "capraz_kiraci": False}
def sozlesme(fn):
    try:
        once = copy.deepcopy(P)
        sonuc = fn(P)
        if sonuc != P or P != once or sonuc is P or sonuc["izinli_kiracilar"] is P["izinli_kiracilar"]:
            return False
        for alan, deger in [("min_skor", 0), ("min_skor", 1), ("max_top_k", 1), ("max_top_k", 20)]:
            if fn(dict(P, **{alan: deger}))[alan] != deger:
                return False
        if fn(dict(P, izinli_kiracilar=["a" * 64]))["izinli_kiracilar"] != ["a" * 64]:
            return False
        for politika in [
            None, [], dict(P, ek=1), dict(P, izinli_kiracilar=[]), dict(P, izinli_kiracilar=None),
            dict(P, izinli_kiracilar=["a", "a"]), dict(P, izinli_kiracilar=[""]),
            dict(P, izinli_kiracilar=["a b"]), dict(P, izinli_kiracilar=["a" * 65]), dict(P, izinli_kiracilar=("a",)), dict(P, izinli_kiracilar=[123]),
            dict(P, min_skor=-0.01), dict(P, min_skor=1.01), dict(P, min_skor=True), dict(P, min_skor="0.5"),
            dict(P, min_skor=float("nan")), dict(P, min_skor=float("inf")),
            dict(P, max_top_k=0), dict(P, max_top_k=21), dict(P, max_top_k=False), dict(P, max_top_k=5.5),
            dict(P, filtre_zorunlu=False), dict(P, filtre_zorunlu=1),
            dict(P, capraz_kiraci=True), dict(P, capraz_kiraci=0),
        ]:
            try:
                fn(politika)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
raises(ValueError,vektor_politikasi_dogrula,dict(P,izinli_kiracilar=[["a"]]),msg="hash öncesi kiracı tür kontrolü")
ok(sozlesme(vektor_politikasi_dogrula), "kiracı, skor, sonuç ve filtre politikaları korunmalı")
def m_kiraci(politika):
    sonuc = vektor_politikasi_dogrula(politika)
    sonuc["izinli_kiracilar"].append("dis")
    return sonuc
def m_skor(politika):
    return vektor_politikasi_dogrula(dict(politika, min_skor=0.0))
def m_filtre(politika):
    sonuc = vektor_politikasi_dogrula(politika)
    sonuc["filtre_zorunlu"] = False
    return sonuc
for ad, mutant in [("kiracıyı açan", m_kiraci), ("skoru düşüren", m_skor), ("filtreyi kaldıran", m_filtre)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def vektor_politikasi_dogrula(politika):
    import math
    import re
    if not isinstance(politika, dict):
        raise ValueError("politika sözlük olmalı")
    if set(politika) != {"izinli_kiracilar", "min_skor", "max_top_k", "filtre_zorunlu", "capraz_kiraci"}:
        raise ValueError("politika şeması geçersiz")
    kiracilar = politika["izinli_kiracilar"]
    if not isinstance(kiracilar, list):
        raise ValueError("kiracılar liste olmalı")
    if not kiracilar:
        raise ValueError("kiracı listesi boş olamaz")
    for kiraci in kiracilar:
        if not isinstance(kiraci, str):
            raise ValueError("kiracı kimliği string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kiraci):
            raise ValueError("kiracı kimliği geçersiz")
    if len(set(kiracilar)) != len(kiracilar):
        raise ValueError("kiracılar yinelenemez")
    skor = politika["min_skor"]
    if isinstance(skor, bool):
        raise ValueError("skor bool olamaz")
    if not isinstance(skor, (int, float)):
        raise ValueError("skor sayı olmalı")
    if not math.isfinite(skor):
        raise ValueError("skor sonlu olmalı")
    if skor < 0:
        raise ValueError("skor sıfırdan küçük olamaz")
    if skor > 1:
        raise ValueError("skor birden büyük olamaz")
    if type(politika["max_top_k"]) is not int:
        raise ValueError("sonuç sınırı int olmalı")
    if politika["max_top_k"] < 1:
        raise ValueError("sonuç sınırı pozitif olmalı")
    if politika["max_top_k"] > 20:
        raise ValueError("sonuç sınırı çok büyük")
    if politika["filtre_zorunlu"] is not True:
        raise ValueError("kiracı filtresi zorunlu")
    if politika["capraz_kiraci"] is not False:
        raise ValueError("çapraz kiracı erişimi kapalı olmalı")
    return {"izinli_kiracilar": list(kiracilar), "min_skor": skor, "max_top_k": politika["max_top_k"], "filtre_zorunlu": True, "capraz_kiraci": False}
```

```hint
Kiracı listesindeki her kimliği desenle doğrula. Sayısal sınırları ayrı kontrol et; iki güvenlik bayrağını `is True` ve `is False` ile sabitle.
```
:::

::: anlat Sorgu reddi bütün ihlalleri görünür kılar
Sorgunun kiracısı izinli değilse `kiraci`, filtre kiracısı sorgu kiracısından farklıysa `filtre`, sonuç sayısı politika sınırını aşıyorsa `top_k` nedeni üretilir. Nedenler bu sıradadır ve herhangi biri sorguyu reddeder.

Filtre alanının bulunması yeterli değildir; doğru kiracıya eşit olması gerekir. Sınır değerine eşit `top_k` kabul edilir.
:::

::: gorev 2 · Vektör sorgularını yetki açısından denetle
`vektor_sorgularini_denetle(sorgular, politika)` işlevini yaz. Politika ilk görevdeki bütün kuralları sağlasın. Sorgular liste; her kayıt tam olarak `id`, `kiraci`, `filtre_kiraci`, `top_k` alanlarını taşısın. Sorgu kimliği benzersizdir; bütün kimlikler ilk görevdeki desene uyar. `top_k` bool olmayan pozitif int olmalıdır. Geçersiz veride `ValueError` yükselt.

Yukarıdaki üç yetki nedenini sırayla uygula. Her kayıt için `{"id":ID,"karar":"reddet" if nedenler else "kabul","nedenler":[...]}` döndür. Kimliğe göre sırala, boş sorguda boş liste döndür ve girdileri değiştirme.

Görünür veri: `veri/vektor_sorgulari.json`. Beklenen kararlar README tablosundadır. `q-filtre-oyunu` reddedilmeli, `q-sinir` ise kabul edilmelidir.

```starter
from ai_savunma_veri import json_yukle

def vektor_sorgularini_denetle(sorgular, politika):
    # KUSURLU BAŞLANGIÇ KODU: kiracı olarak istemcinin gönderdiği FİLTREYİ denetliyor (oturum kiracısını değil), filtre-oturum eşleşmesine bakmıyor ve top_k sınırına eşitliği ihlal sayıyor!
    rapor = []
    for q in sorted(sorgular, key=lambda x: x["id"]):
        nedenler = []
        if q["filtre_kiraci"] not in politika["izinli_kiracilar"]:
            nedenler.append("kiraci")
        if q["top_k"] >= politika["max_top_k"]:
            nedenler.append("top_k")
        rapor.append({"id": q["id"], "karar": "reddet" if nedenler else "kabul", "nedenler": nedenler})
    return rapor

politika = json_yukle("veri/vektor_politikasi.json")["politika"]
veri = json_yukle("veri/vektor_sorgulari.json")
for r in vektor_sorgularini_denetle(veri["sorgular"], politika):
    print(r["id"], r["karar"], r["nedenler"])
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-19")
```

```test
import copy
P = {"izinli_kiracilar": ["a", "b"], "min_skor": 0.8, "max_top_k": 5, "filtre_zorunlu": True, "capraz_kiraci": False}
S = [
    {"id": "kabul-1", "kiraci": "a", "filtre_kiraci": "a", "top_k": 5},
    {"id": "ret-1", "kiraci": "dis", "filtre_kiraci": "baska", "top_k": 6},
    {"id": "filtre-1", "kiraci": "a", "filtre_kiraci": "b", "top_k": 1},
]
BEKLENEN = [
    {"id": "filtre-1", "karar": "reddet", "nedenler": ["filtre"]},
    {"id": "kabul-1", "karar": "kabul", "nedenler": []},
    {"id": "ret-1", "karar": "reddet", "nedenler": ["kiraci", "filtre", "top_k"]},
]
def sozlesme(fn):
    try:
        sonce = copy.deepcopy(S)
        ponce = copy.deepcopy(P)
        if fn(S, P) != BEKLENEN or S != sonce or P != ponce or fn(list(reversed(S)), P) != BEKLENEN or fn([], P) != []:
            return False
        if fn([dict(S[0], id="a" * 64)], P)[0]["id"] != "a" * 64:
            return False
        for alan, deger in [("min_skor", 0), ("min_skor", 1), ("max_top_k", 1), ("max_top_k", 20)]:
            if fn([], dict(P, **{alan: deger})) != []:
                return False
        for sorgular, politika in [
            (None, P), ({}, P), ([None], P), (S, None), (S, dict(P, filtre_zorunlu=False)),
            (S, dict(P, capraz_kiraci=True)), (S, dict(P, min_skor=float("nan"))), (S, dict(P, min_skor=2)),
            (S, dict(P, max_top_k=0)), (S, dict(P, max_top_k=21)), (S, dict(P, max_top_k=5.5)), (S, dict(P, izinli_kiracilar=[])),
            (S, dict(P, izinli_kiracilar=["a" * 65])), (S, dict(P, izinli_kiracilar=("a",))), (S, dict(P, izinli_kiracilar=[123])),
            (S, dict(P, ek=1)), (S, dict(P, min_skor=True)), (S, dict(P, min_skor="0.5")), (S, dict(P, min_skor=-0.1)),
            ([dict(S[0], ek=1)], P), ([dict(S[0], id="")], P), ([dict(S[0], id="a b")], P),
            ([dict(S[0], id="a" * 65)], P), ([S[0], S[0]], P),
            ([dict(S[0], kiraci="")], P), ([dict(S[0], filtre_kiraci="a b")], P),
            ([dict(S[0], top_k=0)], P), ([dict(S[0], top_k=True)], P),
        ]:
            try:
                fn(sorgular, politika)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
raises(ValueError,vektor_sorgularini_denetle,[],dict(P,izinli_kiracilar=["a","a"]),msg="boş sorguda da tam politika doğrulaması")
ok(sozlesme(vektor_sorgularini_denetle), "kiracı, filtre ve top_k kararları korunmalı")
def m_kiraci(sorgular, politika):
    return vektor_sorgularini_denetle(sorgular, dict(politika, izinli_kiracilar=["a", "b", "dis"]))
def m_filtre(sorgular, politika):
    return vektor_sorgularini_denetle([dict(x, filtre_kiraci=x["kiraci"]) for x in sorgular], politika)
def m_topk(sorgular, politika):
    return vektor_sorgularini_denetle(sorgular, dict(politika, max_top_k=20))
for ad, mutant in [("kiracıyı açan", m_kiraci), ("filtreyi düzelten", m_filtre), ("sınırı büyüten", m_topk)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
_P19={"izinli_kiracilar":["a"],"min_skor":0.8,"max_top_k":5,"filtre_zorunlu":True,"capraz_kiraci":False}
for _alan in ("id","kiraci","filtre_kiraci"):
    _q19=dict(id="q1",kiraci="a",filtre_kiraci="a",top_k=1);_q19[_alan]=123
    raises(ValueError, lambda q=_q19: vektor_sorgularini_denetle([q],_P19), msg="string olmayan sorgu alanı ValueError: "+_alan)
```

```solution
def vektor_sorgularini_denetle(sorgular, politika):
    import math
    import re
    if not isinstance(politika, dict):
        raise ValueError("politika sözlük olmalı")
    if set(politika) != {"izinli_kiracilar", "min_skor", "max_top_k", "filtre_zorunlu", "capraz_kiraci"}:
        raise ValueError("politika şeması geçersiz")
    if not isinstance(politika["izinli_kiracilar"], list):
        raise ValueError("kiracılar liste olmalı")
    if not politika["izinli_kiracilar"]:
        raise ValueError("kiracı listesi boş olamaz")
    for kiraci in politika["izinli_kiracilar"]:
        if not isinstance(kiraci, str):
            raise ValueError("kiracı string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kiraci):
            raise ValueError("kiracı geçersiz")
    if len(set(politika["izinli_kiracilar"])) != len(politika["izinli_kiracilar"]):
        raise ValueError("kiracılar yinelenemez")
    skor = politika["min_skor"]
    if isinstance(skor, bool):
        raise ValueError("skor bool olamaz")
    if not isinstance(skor, (int, float)):
        raise ValueError("skor sayı olmalı")
    if not math.isfinite(skor):
        raise ValueError("skor sonlu olmalı")
    if skor < 0:
        raise ValueError("skor aralık dışı")
    if skor > 1:
        raise ValueError("skor aralık dışı")
    if type(politika["max_top_k"]) is not int:
        raise ValueError("sonuç sınırı int olmalı")
    if politika["max_top_k"] < 1:
        raise ValueError("sonuç sınırı pozitif olmalı")
    if politika["max_top_k"] > 20:
        raise ValueError("sonuç sınırı çok büyük")
    if politika["filtre_zorunlu"] is not True:
        raise ValueError("filtre zorunlu")
    if politika["capraz_kiraci"] is not False:
        raise ValueError("çapraz kiracı kapalı olmalı")
    if not isinstance(sorgular, list):
        raise ValueError("sorgular liste olmalı")
    kimlikler = set()
    sonuc = []
    for sorgu in sorgular:
        if not isinstance(sorgu, dict):
            raise ValueError("sorgu sözlük olmalı")
        if set(sorgu) != {"id", "kiraci", "filtre_kiraci", "top_k"}:
            raise ValueError("sorgu şeması geçersiz")
        for alan in ("id", "kiraci", "filtre_kiraci"):
            if not isinstance(sorgu[alan], str):
                raise ValueError(alan + " string olmalı")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", sorgu[alan]):
                raise ValueError(alan + " geçersiz")
        if sorgu["id"] in kimlikler:
            raise ValueError("sorgu kimliği yinelenemez")
        kimlikler.add(sorgu["id"])
        if type(sorgu["top_k"]) is not int:
            raise ValueError("top_k int olmalı")
        if sorgu["top_k"] < 1:
            raise ValueError("top_k pozitif olmalı")
        nedenler = []
        if sorgu["kiraci"] not in politika["izinli_kiracilar"]:
            nedenler.append("kiraci")
        if sorgu["filtre_kiraci"] != sorgu["kiraci"]:
            nedenler.append("filtre")
        if sorgu["top_k"] > politika["max_top_k"]:
            nedenler.append("top_k")
        sonuc.append({"id": sorgu["id"], "karar": "reddet" if nedenler else "kabul", "nedenler": nedenler})
    return sorted(sonuc, key=lambda x: x["id"])
```

```hint
Üç yetki nedenini bağımsız üret. Filtreyi doğrudan sorgu kiracısıyla karşılaştır; `top_k` için yalnız politika üstünü ihlal say.
```
:::

::: anlat Getirme sonrasında kiracı yalıtımı yeniden uygulanır
Depodan dönen her kayıt yeniden filtrelenir. Yalnız sorgu kiracısına ait ve skoru politika eşiğine eşit veya üstünde olan kayıtlar kalır. Başka kiracının kaydı, skoru daha yüksek olsa bile sonuçta yer alamaz.

Sonuçlar skor azalan, eşitlikte kimlik artan sıralanır ve istenen `top_k` kadar kayıtla sınırlanır. Biçimi geçerli olduğu hâlde yetkisiz, yanlış filtreli veya aşırı geniş sorgu boş liste üretir.
:::

::: gorev 3 · Yalnız yetkili vektör kayıtlarını getir
`yetkili_vektorleri_getir(kayitlar, sorgu, politika)` işlevini yaz. Politika ilk görevdeki bütün kuralları, sorgu ikinci görevdeki biçim kurallarını sağlasın. Kayıtlar liste; her kayıt tam olarak `id`, `kiraci`, `skor`, `metin` alanlarını taşısın. Kayıt kimliği benzersizdir ve kimlik desenine uyar. Skor bool olmayan, sonlu ve 0–1 aralığındaki sayı; metin stringdir. Metin NUL ve LF/CR/TAB dışındaki kontrol karakterlerini içeremez. Geçersiz veride `ValueError` yükselt.

Sorgu kiracısı izinli değilse, filtre kiracıdan farklıysa veya `top_k` politika sınırını aşıyorsa boş liste döndür. Aksi hâlde yalnız aynı kiracıdaki ve skor eşiğini geçen kayıtları skor azalan, kimlik artan sırayla ilk `top_k` kadar döndür. Her sonuç `{"id":ID,"kiraci":KIRACI,"skor":SKOR,"metin":METIN}` olsun. Girdileri değiştirme.

Görünür veri: `veri/vektor_kayitlari.json` ve `getirme_sorgusu`. Doğru sonuç `a-iade`, `a-sss`, `a-kargo` olur. En yüksek skorlu iki `globex` kaydı sonuçta yer almamalıdır.

```starter
from ai_savunma_veri import json_yukle

def yetkili_vektorleri_getir(kayitlar, sorgu, politika):
    # KUSURLU BAŞLANGIÇ KODU: önce skora göre top_k ile kesiyor, SONRA kiracıyı filtreliyor; yabancı kiracının yüksek skorlu kayıtları kotayı doldurup meşru kayıtları siliyor ve kayıt doğrulaması yapmıyor!
    sirali = sorted(kayitlar, key=lambda x: (-x["skor"], x["id"]))[:sorgu["top_k"]]
    return [{"id": x["id"], "kiraci": x["kiraci"], "skor": x["skor"], "metin": x["metin"]}
            for x in sirali if x["kiraci"] == sorgu["kiraci"] and x["skor"] >= politika["min_skor"]]

politika = json_yukle("veri/vektor_politikasi.json")["politika"]
sorgu = json_yukle("veri/vektor_sorgulari.json")["getirme_sorgusu"]
veri = json_yukle("veri/vektor_kayitlari.json")
for s in yetkili_vektorleri_getir(veri["kayitlar"], sorgu, politika):
    print(s["id"], s["kiraci"], s["skor"])
for b in veri["bozuk_kayitlar"]:
    try:
        yetkili_vektorleri_getir([b], sorgu, politika)
        print(b["id"], "KABUL edildi (yanlış)")
    except ValueError as hata:
        print(b["id"], "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-19")
```

```test
import copy
P = {"izinli_kiracilar": ["a", "b"], "min_skor": 0.8, "max_top_k": 5, "filtre_zorunlu": True, "capraz_kiraci": False}
Q = {"id": "q-1", "kiraci": "a", "filtre_kiraci": "a", "top_k": 3}
K = [
    {"id": "a-1", "kiraci": "a", "skor": 0.8, "metin": "A"},
    {"id": "b-1", "kiraci": "a", "skor": 0.95, "metin": "B"},
    {"id": "c-1", "kiraci": "b", "skor": 0.99, "metin": "C"},
    {"id": "d-1", "kiraci": "a", "skor": 0.79, "metin": "D"},
]
BEKLENEN = [
    {"id": "b-1", "kiraci": "a", "skor": 0.95, "metin": "B"},
    {"id": "a-1", "kiraci": "a", "skor": 0.8, "metin": "A"},
]
def sozlesme(fn):
    try:
        konce = copy.deepcopy(K)
        qonce = copy.deepcopy(Q)
        ponce = copy.deepcopy(P)
        if fn(K, Q, P) != BEKLENEN or K != konce or Q != qonce or P != ponce or fn(list(reversed(K)), Q, P) != BEKLENEN:
            return False
        if fn(K, dict(Q, top_k=1), P) != BEKLENEN[:1] or fn([], Q, P) != []:
            return False
        if fn(K, dict(Q, kiraci="b", filtre_kiraci="b"), P)[0]["id"] != "c-1":
            return False
        for sorgu in [dict(Q, kiraci="dis", filtre_kiraci="dis"), dict(Q, filtre_kiraci="b"), dict(Q, top_k=6)]:
            if fn(K, sorgu, P) != []:
                return False
        if fn([dict(K[0], id="dis-1", kiraci="dis", skor=0.99)], dict(Q, kiraci="dis", filtre_kiraci="dis"), P) != []:
            return False
        if fn([dict(K[0], id="a" * 64)], Q, P)[0]["id"] != "a" * 64:
            return False
        if fn([dict(K[0], skor=0)], dict(Q, top_k=1), dict(P, min_skor=0))[0]["skor"] != 0:
            return False
        if fn([dict(K[0], skor=1)], Q, P)[0]["skor"] != 1:
            return False
        if fn([dict(K[0], metin="A B\tC\nD\rE")], Q, P)[0]["metin"] != "A B\tC\nD\rE":
            return False
        if fn(K, dict(Q, top_k=5), P) != BEKLENEN or fn(K, Q, dict(P, max_top_k=3)) != BEKLENEN:
            return False
        for alan, deger in [("min_skor", 0), ("min_skor", 1), ("max_top_k", 1), ("max_top_k", 20)]:
            if fn([], Q, dict(P, **{alan: deger})) != []:
                return False
        for kayitlar, sorgu, politika in [
            (None, Q, P), ({}, Q, P), ([None], Q, P), (K, None, P), (K, Q, None), (K, Q, []), (K, Q, dict(P, ek=1)),
            (K, Q, dict(P, filtre_zorunlu=False)), (K, Q, dict(P, capraz_kiraci=True)),
            (K, Q, dict(P, min_skor=float("nan"))), (K, Q, dict(P, min_skor=-0.1)), (K, Q, dict(P, min_skor=2)), (K, Q, dict(P, min_skor=True)), (K, Q, dict(P, min_skor="0.5")),
            (K, Q, dict(P, max_top_k=0)), (K, Q, dict(P, max_top_k=21)), (K, Q, dict(P, max_top_k=5.5)),
            (K, Q, dict(P, izinli_kiracilar=[])), (K, Q, dict(P, izinli_kiracilar=["a" * 65])), (K, Q, dict(P, izinli_kiracilar=("a",))), (K, Q, dict(P, izinli_kiracilar=[123])),
            (K, dict(Q, ek=1), P), (K, dict(Q, id="a b"), P), (K, dict(Q, id="a" * 65), P),
            (K, dict(Q, kiraci="a" * 65), P), (K, dict(Q, filtre_kiraci="a" * 65), P),
            (K, dict(Q, top_k=0), P), (K, dict(Q, top_k=-1), P), (K, dict(Q, top_k=1.5), P), (K, dict(Q, top_k=True), P), (K, dict(Q, kiraci=""), P),
            ([dict(K[0], ek=1)], Q, P), ([dict(K[0], id="a" * 65)], Q, P), ([K[0], K[0]], Q, P),
            ([dict(K[0], kiraci="a b")], Q, P), ([dict(K[0], skor=-0.1)], Q, P),
            ([dict(K[0], skor=1.1)], Q, P), ([dict(K[0], skor=True)], Q, P), ([dict(K[0], skor="0.5")], Q, P),
            ([dict(K[0], skor=float("nan"))], Q, P), ([dict(K[0], skor=float("inf"))], Q, P),
            ([dict(K[0], metin=None)], Q, P), ([dict(K[0], metin="a\0b")], Q, P),
            ([dict(K[0], metin="a\x01b")], Q, P), ([dict(K[0], metin="a\x1fb")], Q, P),
        ]:
            try:
                fn(kayitlar, sorgu, politika)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
raises(ValueError,yetkili_vektorleri_getir,[],Q,dict(P,izinli_kiracilar=["a","a"]),msg="boş sonuçta da yinelenen kiracı politikası reddi")
ok(sozlesme(yetkili_vektorleri_getir), "kiracı yalıtımı, skor, sıralama ve top_k korunmalı")
def m_capraz(kayitlar, sorgu, politika):
    return yetkili_vektorleri_getir([dict(x, kiraci=sorgu["kiraci"]) for x in kayitlar], sorgu, politika)
def m_skor(kayitlar, sorgu, politika):
    return yetkili_vektorleri_getir(kayitlar, sorgu, dict(politika, min_skor=0.0))
def m_filtre(kayitlar, sorgu, politika):
    return yetkili_vektorleri_getir(kayitlar, dict(sorgu, filtre_kiraci=sorgu["kiraci"]), politika)
for ad, mutant in [("kiracıyı değiştiren", m_capraz), ("skoru düşüren", m_skor), ("filtreyi düzelten", m_filtre)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
_P19={"izinli_kiracilar":["a"],"min_skor":0.8,"max_top_k":5,"filtre_zorunlu":True,"capraz_kiraci":False}
_Q19=dict(id="q1",kiraci="a",filtre_kiraci="a",top_k=1)
for _alan in ("id","kiraci","filtre_kiraci"):
    _q19=dict(_Q19);_q19[_alan]=123
    raises(ValueError, lambda q=_q19: yetkili_vektorleri_getir([],q,_P19), msg="sorgu alanı string olmalı: "+_alan)
for _alan in ("id","kiraci"):
    _k19=dict(id="k1",kiraci="a",skor=0.9,metin="x");_k19[_alan]=123
    raises(ValueError, lambda k=_k19: yetkili_vektorleri_getir([k],_Q19,_P19), msg="kayıt alanı string olmalı: "+_alan)
```

```solution
def yetkili_vektorleri_getir(kayitlar, sorgu, politika):
    import math
    import re
    if not isinstance(politika, dict):
        raise ValueError("politika sözlük olmalı")
    if set(politika) != {"izinli_kiracilar", "min_skor", "max_top_k", "filtre_zorunlu", "capraz_kiraci"}:
        raise ValueError("politika şeması geçersiz")
    if not isinstance(politika["izinli_kiracilar"], list):
        raise ValueError("kiracılar liste olmalı")
    if not politika["izinli_kiracilar"]:
        raise ValueError("kiracı listesi boş olamaz")
    for kiraci in politika["izinli_kiracilar"]:
        if not isinstance(kiraci, str):
            raise ValueError("kiracı string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kiraci):
            raise ValueError("kiracı geçersiz")
    if len(set(politika["izinli_kiracilar"])) != len(politika["izinli_kiracilar"]):
        raise ValueError("kiracılar yinelenemez")
    esik = politika["min_skor"]
    if isinstance(esik, bool):
        raise ValueError("skor bool olamaz")
    if not isinstance(esik, (int, float)):
        raise ValueError("skor sayı olmalı")
    if not math.isfinite(esik):
        raise ValueError("skor sonlu olmalı")
    if esik < 0:
        raise ValueError("skor aralık dışı")
    if esik > 1:
        raise ValueError("skor aralık dışı")
    if type(politika["max_top_k"]) is not int:
        raise ValueError("sonuç sınırı int olmalı")
    if politika["max_top_k"] < 1:
        raise ValueError("sonuç sınırı pozitif olmalı")
    if politika["max_top_k"] > 20:
        raise ValueError("sonuç sınırı çok büyük")
    if politika["filtre_zorunlu"] is not True:
        raise ValueError("filtre zorunlu")
    if politika["capraz_kiraci"] is not False:
        raise ValueError("çapraz kiracı kapalı olmalı")
    if not isinstance(sorgu, dict):
        raise ValueError("sorgu sözlük olmalı")
    if set(sorgu) != {"id", "kiraci", "filtre_kiraci", "top_k"}:
        raise ValueError("sorgu şeması geçersiz")
    for alan in ("id", "kiraci", "filtre_kiraci"):
        if not isinstance(sorgu[alan], str):
            raise ValueError(alan + " string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", sorgu[alan]):
            raise ValueError(alan + " geçersiz")
    if type(sorgu["top_k"]) is not int:
        raise ValueError("top_k int olmalı")
    if sorgu["top_k"] < 1:
        raise ValueError("top_k pozitif olmalı")
    if not isinstance(kayitlar, list):
        raise ValueError("kayitlar liste olmalı")
    kimlikler = set()
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"id", "kiraci", "skor", "metin"}:
            raise ValueError("kayıt şeması geçersiz")
        for alan in ("id", "kiraci"):
            if not isinstance(kayit[alan], str):
                raise ValueError(alan + " string olmalı")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit[alan]):
                raise ValueError(alan + " geçersiz")
        if kayit["id"] in kimlikler:
            raise ValueError("kayıt kimliği yinelenemez")
        kimlikler.add(kayit["id"])
        skor = kayit["skor"]
        if isinstance(skor, bool):
            raise ValueError("skor bool olamaz")
        if not isinstance(skor, (int, float)):
            raise ValueError("skor sayı olmalı")
        if not math.isfinite(skor):
            raise ValueError("skor sonlu olmalı")
        if skor < 0:
            raise ValueError("skor sıfırdan küçük olamaz")
        if skor > 1:
            raise ValueError("skor birden büyük olamaz")
        metin = kayit["metin"]
        if not isinstance(metin, str):
            raise ValueError("metin string olmalı")
        for karakter in metin:
            if ord(karakter) < 32 and karakter not in "\n\r\t":
                raise ValueError("metin kontrol karakteri içeremez")
    if sorgu["kiraci"] not in politika["izinli_kiracilar"]:
        return []
    if sorgu["filtre_kiraci"] != sorgu["kiraci"]:
        return []
    if sorgu["top_k"] > politika["max_top_k"]:
        return []
    adaylar = [x for x in kayitlar if x["kiraci"] == sorgu["kiraci"] and x["skor"] >= esik]
    adaylar.sort(key=lambda x: (-x["skor"], x["id"]))
    return [{"id": x["id"], "kiraci": x["kiraci"], "skor": x["skor"], "metin": x["metin"]} for x in adaylar[:sorgu["top_k"]]]
```

```hint
Önce bütün girdileri doğrula, sonra yetkisiz sorguyu boş sonuçla reddet. Aday listesinde hem kiracı eşitliğini hem skor eşiğini birlikte uygula.
```
:::

::: anlat Benzerlik sıralaması kiracı sınırını aşamaz
Görev 1–3'te skorlar elle yazılmıştı. Bu adımda skorları **gerçek bir gömme modeli** üretir. `sandbox/ai_gercek_ai_savunma_19.py` deneyi şunları yapar:

1. Kurulu `all-minilm:22m` embedding modeli bir kiracı-a sorgusunu ("İade süresi kaç gündür?") ve üç kaydı vektöre çevirir. Vektörler eksik ya da geçersizse deney "tamamlanmadı" diye durur.
2. Kayıtlardan ikisi kiracı-a'ya, biri kiracı-b'ye aittir. Kiracı-b'nin kaydı sorgunun kelimelerini tekrar ettiği için sorguya çok benzer.
3. Senin `yetkili_vektorleri_getir` işlevin iki sorguyla çağrılır: olağan kiracı-a sorgusu ve filtresi kiracı-b'ye çevrilmiş manipüle bir sorgu. Olağan sorgunun sonucu bağımsız bir referans getirmeyle de karşılaştırılır.

Test önce işlevini gizli deterministik kayıtlarla sınar. Ardından şu üç koşulu ister:

- Gerçek skorlarla getirdiğin sonuç referansla birebir aynı olmalı.
- Sonuçta başka kiracının kaydı bulunmamalı.
- Manipüle sorgu boş dönmeli.

En yüksek skorlu kaydın hangi kiracıya ait olduğu kabul koşulu değildir; bulgu olarak kaydedilir.

Ders yazılırken bu makinede kiracı-b'nin kaydı 0.910 skorla en yüksek sırada çıktı. Kiracı-a'nın kayıtları 0.761 ve 0.496 aldı. Doğru getirme kiracı-b'nin kaydını dışarıda bıraktı ve kiracı-a'nın iki kaydını döndürdü. Yalnız skora göre sıralayan bir sistem kiracı-a'nın kullanıcısına önce kiracı-b'nin verisini gösterirdi. Saldırganın sorguyu hedef belgeye benzeterek skoru yükseltebileceğini unutma: benzerlik, erişim hakkı değildir.

:::

::: gorev Gerçek deney · Gerçek skorlarla kiracı yalıtımı
`yetkili_vektorleri_getir(kayitlar, sorgu, politika)` işlevini yaz. Kuralları ve çıktısı 3. görevdekiyle **aynıdır**. Deney gerçek gömme modeliyle skorları üretir. Senin işlevin yalnız aynı kiracıya ait ve skor eşiğini geçen kayıtları getirir; başka kiracının kaydı en yüksek skorlu olsa bile dışarıda kalır. `sandbox.ai_gercek_ai_savunma_19` içindeki `yetkili_vektorleri_getir_referans` yalnız test içindir; onu import etmek veya kaynağını okuyup çalıştırmak Kontrol'de reddedilir.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def yetkili_vektorleri_getir(kayitlar, sorgu, politika):
    # KUSURLU BAŞLANGIÇ KODU: kiracı olarak istemcinin gönderdiği FİLTREYİ kullanıyor; filtresi kiracı-b'ye çevrilmiş sorgu kiracı-b'nin kaydını getirir!
    uygun = [x for x in kayitlar if x["kiraci"] == sorgu["filtre_kiraci"] and x["skor"] >= politika["min_skor"]]
    uygun.sort(key=lambda x: (-x["skor"], x["id"]))
    return [{"id": x["id"], "kiraci": x["kiraci"], "skor": x["skor"], "metin": x["metin"]} for x in uygun[:sorgu["top_k"]]]

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_19 as deney
    deney.goster(yetkili_vektorleri_getir)
```

```test
import ast
import ai_lab
from sandbox import ai_gercek_ai_savunma_19 as D
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
_yasak = ("yetkili_vektorleri_getir_referans", "kanit_yaz")
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
if not kontrol(not sorun, "Kendi yetkili_vektorleri_getir işlevini yaz; laboratuvar/referans kullanımı yasak: " + "; ".join(sorted(set(sorun)))):
    stop()
fn = need("yetkili_vektorleri_getir")
_p19={"izinli_kiracilar":["a","a"],"min_skor":0.8,"max_top_k":5,"filtre_zorunlu":True,"capraz_kiraci":False}
_q19={"id":"q","kiraci":"a","filtre_kiraci":"a","top_k":1}
raises(ValueError,fn,[],_q19,_p19,msg="gerçek görevde de tam politika doğrulaması")

P = {"izinli_kiracilar": ["a", "b"], "min_skor": 0.3, "max_top_k": 5, "filtre_zorunlu": True, "capraz_kiraci": False}
Q = {"id": "q-1", "kiraci": "a", "filtre_kiraci": "a", "top_k": 3}
K = [
    {"id": "a-1", "kiraci": "a", "skor": 0.8, "metin": "A"},
    {"id": "c-1", "kiraci": "b", "skor": 0.99, "metin": "C"},
    {"id": "d-1", "kiraci": "a", "skor": 0.2, "metin": "D"},
]
BEKLENEN = [{"id": "a-1", "kiraci": "a", "skor": 0.8, "metin": "A"}]
def sozlesme(f):
    try:
        if f(K, Q, P) != BEKLENEN or f([], Q, P) != []:
            return False
        if f(K, dict(Q, kiraci="dis", filtre_kiraci="dis"), P) != [] or f([dict(K[0], id="dis-1", kiraci="dis", skor=0.99)], dict(Q, kiraci="dis", filtre_kiraci="dis"), P) != []:
            return False
        if f(K, dict(Q, filtre_kiraci="b"), P) != []:
            return False
        esit = [dict(K[0], id="e-2", skor=0.5), dict(K[0], id="e-1", skor=0.5), dict(K[0], id="e-0", skor=0.3)]
        if [x["id"] for x in f(esit, dict(Q, top_k=2), P)] != ["e-1", "e-2"] or [x["id"] for x in f(esit, dict(Q, top_k=3), P)] != ["e-1", "e-2", "e-0"] or [x["id"] for x in f(esit, dict(Q, top_k=1), P)] != ["e-1"]:
            return False
        if f([dict(K[0], skor=0)], dict(Q, top_k=1), dict(P, min_skor=0))[0]["skor"] != 0 or f([dict(K[0], skor=1)], Q, P)[0]["skor"] != 1:
            return False
        if f([dict(K[0], id="a" * 64, metin="A B\tC\nD\rE")], Q, P)[0]["metin"] != "A B\tC\nD\rE":
            return False
        for alan, deger in [("min_skor", 0), ("min_skor", 1), ("max_top_k", 1), ("max_top_k", 20)]:
            if f([], dict(Q, top_k=1), dict(P, **{alan: deger})) != []:
                return False
        if f(K, dict(Q, top_k=6), P) != [] or f(K, dict(Q, top_k=5), P) != BEKLENEN:
            return False
        dolu = [dict(K[1], id="b-%d" % i, skor=0.95) for i in range(3)] + [K[0]]
        if f(dolu, Q, P) != BEKLENEN:
            return False
        for bozuk_k, bozuk_q, bozuk_p in (
            (None, Q, P), ({}, Q, P), ([None], Q, P), (K, None, P), (K, [], P), (K, Q, None), (K, Q, []), (K, Q, dict(P, ek=1)),
            (K, Q, dict(P, filtre_zorunlu=False)), (K, Q, dict(P, capraz_kiraci=True)),
            (K, Q, dict(P, min_skor=-0.1)), (K, Q, dict(P, min_skor=1.1)), (K, Q, dict(P, min_skor=True)), (K, Q, dict(P, min_skor="0.5")), (K, Q, dict(P, min_skor=float("nan"))),
            (K, Q, dict(P, max_top_k=0)), (K, Q, dict(P, max_top_k=21)), (K, Q, dict(P, max_top_k=5.5)),
            (K, Q, dict(P, izinli_kiracilar=[])), (K, Q, dict(P, izinli_kiracilar=("a",))), (K, Q, dict(P, izinli_kiracilar=[123])), (K, Q, dict(P, izinli_kiracilar=["a b"])), (K, Q, dict(P, izinli_kiracilar=["a" * 65])),
            (K, dict(Q, ek=1), P), (K, dict(Q, id=123), P), (K, dict(Q, id=""), P), (K, dict(Q, id="a" * 65), P),
            (K, dict(Q, kiraci=123), P), (K, dict(Q, kiraci=""), P), (K, dict(Q, filtre_kiraci=123), P), (K, dict(Q, filtre_kiraci=""), P),
            (K, dict(Q, top_k=0), P), (K, dict(Q, top_k=-1), P), (K, dict(Q, top_k=1.5), P), (K, dict(Q, top_k=True), P),
            ([dict(K[0], ek=1)], Q, P), ([dict(K[0], id=123)], Q, P), ([dict(K[0], id="")], Q, P), ([dict(K[0], id="a" * 65)], Q, P),
            ([dict(K[0], kiraci=123)], Q, P), ([dict(K[0], kiraci="a b")], Q, P), ([K[0], K[0]], Q, P),
            ([dict(K[0], skor=-0.1)], Q, P), ([dict(K[0], skor=1.2)], Q, P), ([dict(K[0], skor=True)], Q, P), ([dict(K[0], skor="0.5")], Q, P), ([dict(K[0], skor=float("nan"))], Q, P),
            ([dict(K[0], metin=123)], Q, P), ([dict(K[0], metin="a\0b")], Q, P), ([dict(K[0], metin="a\x1fb")], Q, P),
        ):
            try:
                f(bozuk_k, bozuk_q, bozuk_p)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(fn), "kiracı yalıtımı, skor eşiği, sıralama ve top_k korunmalı")
r, oz = None, None
if all(sonuclar):
    try:
        r = D.deney(fn)
    except ai_lab.GercekLabYok as e:
        kontrol(False, f"GERÇEK MODEL YOK, deney yapılmadı: {e}")
        stop()
    kontrol(not r["capraz_sizinti"], "getirilen gerçek kayıtların hepsi sorgu kiracısına ait, çapraz sızıntı yok")
    kontrol(r["sonuc_dogru"], f"gerçek skorlarla getirme bağımsız referansla aynı olmalı: senin {r['sonuc']} · beklenen {r['beklenen']}")
    kontrol(r["filtre_sonuc"] == [], f"filtresi başka kiracıya çevrilmiş sorgu boş dönmeli: {r['filtre_sonuc']}")
    oz = D.ozet(r)
yol = ai_lab.kanit_yaz("savunma-kiraci", {"kaynak": "gercek", "kabul": all(sonuclar), "ders": "ai-savunma-19",
                                          "ortam": (r or {}).get("ortam"), "ozet": oz, "kayitlar": (r or {}).get("kayitlar")})
if oz:
    ok(True, f"BULGU ({(r['ortam'].get('gomme') or {}).get('model')}): gerçek skorlar {oz['skorlar']}; getirilen {oz['sonuc_idler']} (kiracılar {oz['sonuc_kiracilar']}). "
             f"En yüksek skorlu kayıt {oz['en_yuksek_id']} kiracı '{oz['en_yuksek_kiraci']}' (dışlandı: {oz['en_yuksek_dislandi']}); çapraz kiracı sızıntısı {oz['capraz_sizinti']}; manipüle filtreli sorgu boş: {oz['filtre_sorgusu_bos']}. "
             f"Benzerlik sıralaması kiracı sınırını aşamadı.")
```

```solution
import ai_lab

def yetkili_vektorleri_getir(kayitlar, sorgu, politika):
    import math
    import re
    if not isinstance(politika, dict):
        raise ValueError("politika sözlük olmalı")
    if set(politika) != {"izinli_kiracilar", "min_skor", "max_top_k", "filtre_zorunlu", "capraz_kiraci"}:
        raise ValueError("politika şeması geçersiz")
    if not isinstance(politika["izinli_kiracilar"], list):
        raise ValueError("kiracılar liste olmalı")
    if not politika["izinli_kiracilar"]:
        raise ValueError("kiracı listesi boş olamaz")
    for kiraci in politika["izinli_kiracilar"]:
        if not isinstance(kiraci, str):
            raise ValueError("kiracı string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kiraci):
            raise ValueError("kiracı geçersiz")
    if len(set(politika["izinli_kiracilar"])) != len(politika["izinli_kiracilar"]):
        raise ValueError("kiracılar yinelenemez")
    esik = politika["min_skor"]
    if isinstance(esik, bool):
        raise ValueError("skor bool olamaz")
    if not isinstance(esik, (int, float)):
        raise ValueError("skor sayı olmalı")
    if not math.isfinite(esik):
        raise ValueError("skor sonlu olmalı")
    if esik < 0:
        raise ValueError("skor aralık dışı")
    if esik > 1:
        raise ValueError("skor aralık dışı")
    if type(politika["max_top_k"]) is not int:
        raise ValueError("sonuç sınırı int olmalı")
    if politika["max_top_k"] < 1:
        raise ValueError("sonuç sınırı pozitif olmalı")
    if politika["max_top_k"] > 20:
        raise ValueError("sonuç sınırı çok büyük")
    if politika["filtre_zorunlu"] is not True:
        raise ValueError("filtre zorunlu")
    if politika["capraz_kiraci"] is not False:
        raise ValueError("çapraz kiracı kapalı olmalı")
    if not isinstance(sorgu, dict):
        raise ValueError("sorgu sözlük olmalı")
    if set(sorgu) != {"id", "kiraci", "filtre_kiraci", "top_k"}:
        raise ValueError("sorgu şeması geçersiz")
    for alan in ("id", "kiraci", "filtre_kiraci"):
        if not isinstance(sorgu[alan], str):
            raise ValueError(alan + " string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", sorgu[alan]):
            raise ValueError(alan + " geçersiz")
    if type(sorgu["top_k"]) is not int:
        raise ValueError("top_k int olmalı")
    if sorgu["top_k"] < 1:
        raise ValueError("top_k pozitif olmalı")
    if not isinstance(kayitlar, list):
        raise ValueError("kayitlar liste olmalı")
    kimlikler = set()
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"id", "kiraci", "skor", "metin"}:
            raise ValueError("kayıt şeması geçersiz")
        for alan in ("id", "kiraci"):
            if not isinstance(kayit[alan], str):
                raise ValueError(alan + " string olmalı")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit[alan]):
                raise ValueError(alan + " geçersiz")
        if kayit["id"] in kimlikler:
            raise ValueError("kayıt kimliği yinelenemez")
        kimlikler.add(kayit["id"])
        skor = kayit["skor"]
        if isinstance(skor, bool):
            raise ValueError("skor bool olamaz")
        if not isinstance(skor, (int, float)):
            raise ValueError("skor sayı olmalı")
        if not math.isfinite(skor):
            raise ValueError("skor sonlu olmalı")
        if skor < 0:
            raise ValueError("skor sıfırdan küçük olamaz")
        if skor > 1:
            raise ValueError("skor birden büyük olamaz")
        metin = kayit["metin"]
        if not isinstance(metin, str):
            raise ValueError("metin string olmalı")
        for karakter in metin:
            if ord(karakter) < 32 and karakter not in "\n\r\t":
                raise ValueError("metin kontrol karakteri içeremez")
    if sorgu["kiraci"] not in politika["izinli_kiracilar"]:
        return []
    if sorgu["filtre_kiraci"] != sorgu["kiraci"]:
        return []
    if sorgu["top_k"] > politika["max_top_k"]:
        return []
    adaylar = [x for x in kayitlar if x["kiraci"] == sorgu["kiraci"] and x["skor"] >= esik]
    adaylar.sort(key=lambda x: (-x["skor"], x["id"]))
    return [{"id": x["id"], "kiraci": x["kiraci"], "skor": x["skor"], "metin": x["metin"]} for x in adaylar[:sorgu["top_k"]]]

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_19 as deney
    deney.goster(yetkili_vektorleri_getir)
```

```hint
Bu işlev 3. görevdeki `yetkili_vektorleri_getir` ile birebir aynıdır; tek fark, skorların gerçek gömme modelinden gelmesidir. Yetkisiz sorguyu boş sonuçla reddet; adaylarda kiracı eşitliği ve skor eşiğini birlikte uygula.
```
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
Kiracı kimliği istemcinin query filter alanından değil doğrulanmış oturumdan gelir. Önce yetkili tenant koleksiyonunu filtrele, sonra benzerlik/top-k uygula. Skor eşiğine eşit kayıtla top_k üst sınırını ayrı denetle; büyük isteği sessiz kırpmak yerine politika sözleşmesini uygula. Yabancı kiracıdaki birebir aynı embedding yüksek skor alabilir; bu erişim hakkı yaratmaz.

Önkoşul ve yol köprüsü: ai-saldiri-08 hafıza kapsamı.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| En yakın vektör her zaman döndürülebilir | Tenant filtresi benzerlikten önce gelir |

Dinleyiciye sor: Savunma güvenlik metriğini iyileştirirken meşru kullanıma ne kaybettirebilir? Ham çıktı ve ölçüm paydalarıyla cevapla.
:::


::: anlat Birincil kaynak ve deney sınırı
[Qdrant Filtering](https://qdrant.tech/documentation/search/filtering/): Arama sırasında payload koşulu uygulanması için araç referansı. Oturumdan tenant seçmek uygulamanın sorumluluğudur. Çalışan sürüm ve gerçek sonuç kanıtta kayıtlıdır.
:::
