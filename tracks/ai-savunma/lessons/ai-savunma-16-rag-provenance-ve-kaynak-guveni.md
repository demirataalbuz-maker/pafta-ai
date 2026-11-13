---
id: ai-savunma-16
title: RAG Provenance ve Kaynak Güveni
summary: Kaynak defterini doğrula, RAG parçalarını kaynak sürümü ve imzayla ilişkilendir, yalnız doğrulanabilir parçaları güven eşiğiyle seç.
esleme: ai-saldiri-14, ai-saldiri-15
timeout: 45
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et: Provenance parçanın doğrulanabilir kimliğidir

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Qdrant gibi bir vektör veritabanı her noktayı bir vektör ve bir metadata yükü (`payload`) ile saklar. Arama, benzerlik skoru ve payload döndürür. Kaynak, sürüm ve imza bilgisi payload'da taşınır; uygulama bunları ayrı bir kaynak defteriyle karşılaştırır. | Görev 1–3: `veri/kaynak_defteri.json`, `veri/getirilen_parcalar.json` ve `veri/provenance_kayitlari.json` içindeki **sentetik** defter, parça ve skorlar. Son adım: kurulu `all-minilm:22m` embedding modeli sorgu ve üç parça için gerçek vektör üretir ve kosinüs benzerliği hesaplanır. Senin seçimin bu gerçek skorlarla çalışır. | `metin_sha256` alanı yalnız biçim olarak doğrulanır. Bu ders özeti metinden yeniden hesaplamaz, imzayı kriptografik olarak doğrulamaz. Gerçek bir sistemde ikisi de gerekir. Üç parçalık deney, bir retrieval sisteminin genel davranışını göstermez. |

> [!NOT]
> Görev 1–3 sentetik veriyle çalışır. Bu görevlerde gömme modeli, Qdrant veya FastAPI çağrılmaz. Son adımdaki **Gerçek deney** görevi kurulu yerel Ollama gömme modelini gerçekten çalıştırır; Qdrant çalıştırılmaz, yeni model indirilmez. `veri/` dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalanır; kopyada yaptığın değişiklik bir sonraki çalıştırmada sıfırlanır, **kalıcılık yoktur**. Kontrol bu dosyalardan ayrı, gizli verilerle sınar.

RAG yanıtındaki her parça kaynak, belge sürümü ve içerik özetiyle ilişkilendirilir. Qdrant benzerlik skoru parçanın konuyla ilgisini ölçer; kaynağın güvenilir veya doğrulanabilir olduğunu kanıtlamaz. Bu nedenle skor ile kaynak güveni ayrı alanlardır.

Görev 1–3'te kaynak defteri ve getirilen parçalar sentetik kayıtlardır; son adımda skorlar gerçek bir gömme modelinden gelir. Kaynağı bulunmayan, sürümü uyuşmayan, imzasız veya pasif kaynaktan gelen parça doğrulanabilir sayılmaz.

**Saldırgan bakışı:** Bir saldırgan RAG deposuna sahte içerik sokmak ister. Bunu genellikle şöyle yapar:

- Güvenilir bir kaynağın adını taşıyan ama yeni ya da farklı sürüm numaralı bir belge yükler (`p-tahrif`).
- Defterde hiç olmayan bir kaynaktan belge ekler (`p-yetim`).
- Eskimiş ama hâlâ indekste duran bir belgeyi hedefler (`p-eski`).
- İmzasız bir kullanıcı notunu kurumsal belge gibi gösterir (`p-not`).

Saldırgan metni sorguya çok benzeyecek biçimde yazdığı için bu parçalar yüksek benzerlik skoru alır. `veri/getirilen_parcalar.json` içinde en yüksek skorlu dört parçanın üçü doğrulanamaz.

**Neden skor güven değildir?** Benzerlik skoru iki vektörün yakınlığını ölçer, yani "bu metin soruyla ilgili mi?" sorusunu cevaplar. "Bu metin kimden geldi?" ya da "değiştirildi mi?" sorularını cevaplamaz. Skora göre sıralayıp ilk N parçayı almak, saldırganın en çok emek verdiği parçayı ödüllendirir. Provenance kapısı bu yüzden skor sıralamasından **önce** çalışır.
:::

::: anlat Güven eşiği sıralama skorundan bağımsızdır
Güven düzeyleri `yuksek`, `orta`, `dusuk` sırasıyla değerlendirilir. `orta` eşiği yüksek ve orta kaynakları kapsar; düşük kaynağı kapsamaz. Yüksek benzerlik skoru, doğrulanamayan veya eşiğin altındaki parçayı yeniden güvenli yapmaz.

**Sık tuzaklar:**

- **Sürümü sayı gibi karşılaştırmak:** `1.0.12` ile `1.0.2` metin olarak karşılaştırılırsa sıra yanlış çıkar. Bu ders sürümü yalnız **tam eşitlikle** karşılaştırır. Biçim kuralı da başında sıfır olan (`3.01.0`) ve önekli (`v3.1.0`) yazımları reddeder. Böylece aynı sürüm iki farklı biçimde yazılamaz.
- **Bilinmeyen kaynağa varsayılan güven vermek:** Defterde olmayan kaynak `bilinmiyor` alır ve hiçbir eşikte seçilmez. "Orta sayalım" demek, saldırgana defter dışı içerik ekleme yolunu açar.
- **Pasif kaynağı unutmak:** Bir kaynak kaldırıldığında indeksteki parçaları hemen silinmeyebilir. Defterdeki `aktif=false` bayrağı bu parçaları kapının dışında tutar.
- **Çelişkili kayıt:** `dogrulanabilir=true` ama neden listesi dolu bir kayıt, ya yanlış üretilmiş ya da sonradan değiştirilmiştir. Seçim aşaması bu kaydı "doğrulanabilir" diye kabul etmez, biçim hatası olarak reddeder.
:::

::: tahmin Güven eşiğini tahmin et
Üç çıktı satırını yaz:

```python
sira = {"yuksek": 0, "orta": 1, "dusuk": 2}
for guven in ["yuksek", "orta", "dusuk"]:
    print(sira[guven] <= sira["orta"])
```

???

```cikti
True
True
False
```

Eşik kapsamı ile skor sıralaması iki ayrı karardır; seçimden önce provenance ve güven denetimi uygulanır.
:::

::: gorev 1 · RAG kaynak defterini doğrula
`kaynak_defteri_dogrula(kaynaklar)` işlevini yaz. Kaynaklar liste; her kayıt tam olarak `kaynak_id`, `tur`, `surum`, `guven`, `imzali`, `aktif` alanlarını taşısın. Kaynak kimliği 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren benzersiz stringdir.

Tür `kurumsal`, `acik`, `kullanici`; güven `yuksek`, `orta`, `dusuk` olmalıdır. Sürüm `MAJOR.MINOR.PATCH` biçiminde, her bileşeni başında gereksiz sıfır olmayan ASCII rakamlardan oluşan stringdir. `imzali` ve `aktif` gerçek bool olmalıdır. Geçersiz veride `ValueError` yükselt.

Kayıtları `kaynak_id` değerine göre sıralanmış yeni sözlükler olarak döndür. Boş defterde boş liste döndür ve girdiyi değiştirme.

Görünür veri: `veri/kaynak_defteri.json`. Beş kaynak geçerlidir (`1.0.12` sürümü dahil). `bozuk_defterler` içindeki beş defter reddedilmelidir.

```starter
from ai_savunma_veri import json_yukle

def kaynak_defteri_dogrula(kaynaklar):
    # KUSURLU BAŞLANGIÇ KODU: sürümü yalnız "üç parça var mı" diye denetliyor (3.01.0 ve v3.1.0 geçer), güven/tür değerini, bool alanları ve yinelenen kimliği denetlemiyor!
    for k in kaynaklar:
        if len(k["surum"].split(".")) != 3:
            raise ValueError("sürüm üç parçalı olmalı")
    return sorted([dict(k) for k in kaynaklar], key=lambda x: x["kaynak_id"])

veri = json_yukle("veri/kaynak_defteri.json")
print([k["kaynak_id"] for k in kaynak_defteri_dogrula(veri["kaynaklar"])])
for i, d in enumerate(veri["bozuk_defterler"]):
    try:
        kaynak_defteri_dogrula(d)
        print("bozuk", i, "KABUL edildi (yanlış)")
    except ValueError as hata:
        print("bozuk", i, "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-16")
```

```test
import copy
K = [
    {"kaynak_id": "acik-1", "tur": "acik", "surum": "0.10.0", "guven": "dusuk", "imzali": False, "aktif": True},
    {"kaynak_id": "kurum-1", "tur": "kurumsal", "surum": "1.2.3", "guven": "yuksek", "imzali": True, "aktif": True},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K) != K or K != once or fn(list(reversed(K))) != K or fn([]) != []:
            return False
        sonuc = fn(K)
        if sonuc[0] is K[0] or fn([dict(K[0], kaynak_id="a" * 64)])[0]["kaynak_id"] != "a" * 64:
            return False
        for surum in ["0.0.0", "0.1.1", "10.20.30"]:
            if fn([dict(K[0], surum=surum)])[0]["surum"] != surum:
                return False
        for kaynaklar in [
            None, {}, [None], [dict(K[0], ek=1)], [dict(K[0], kaynak_id="")], [dict(K[0], kaynak_id="a b")],
            [dict(K[0], kaynak_id="a" * 65)], [K[0], K[0]], [dict(K[0], tur="diger")], [dict(K[0], guven="bilinmiyor")],
            [dict(K[0], surum="1.2")], [dict(K[0], surum="01.2.3")], [dict(K[0], surum="1.02.3")],
            [dict(K[0], surum="1.2.03")], [dict(K[0], surum="1.2.-3")], [dict(K[0], kaynak_id=123)], [dict(K[0], surum=123)], [dict(K[0], imzali=1)], [dict(K[0], aktif=0)],
        ]:
            try:
                fn(kaynaklar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(kaynak_defteri_dogrula), "kaynak kimliği, tür, sürüm, güven ve durum korunmalı")
def m_imza(kaynaklar):
    return kaynak_defteri_dogrula([dict(x, imzali=False) for x in kaynaklar])
def m_surum(kaynaklar):
    return kaynak_defteri_dogrula([dict(x, surum="9.9.9") for x in kaynaklar])
def m_guven(kaynaklar):
    return kaynak_defteri_dogrula([dict(x, guven="dusuk") for x in kaynaklar])
for ad, mutant in [("imzayı silen", m_imza), ("sürümü değiştiren", m_surum), ("güveni düşüren", m_guven)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def kaynak_defteri_dogrula(kaynaklar):
    import re
    if not isinstance(kaynaklar, list):
        raise ValueError("kaynaklar liste olmalı")
    kimlikler = set()
    defter = []
    for kaynak in kaynaklar:
        if not isinstance(kaynak, dict):
            raise ValueError("kaynak sözlük olmalı")
        if set(kaynak) != {"kaynak_id", "tur", "surum", "guven", "imzali", "aktif"}:
            raise ValueError("kaynak şeması geçersiz")
        kimlik = kaynak["kaynak_id"]
        if not isinstance(kimlik, str):
            raise ValueError("kaynak kimliği metin olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kimlik):
            raise ValueError("kaynak kimliği geçersiz")
        if kimlik in kimlikler:
            raise ValueError("kaynak kimliği yinelenemez")
        kimlikler.add(kimlik)
        if kaynak["tur"] not in ("kurumsal", "acik", "kullanici"):
            raise ValueError("kaynak türü geçersiz")
        if not isinstance(kaynak["surum"], str):
            raise ValueError("sürüm metin olmalı")
        if not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", kaynak["surum"]):
            raise ValueError("sürüm biçimi geçersiz")
        if kaynak["guven"] not in ("yuksek", "orta", "dusuk"):
            raise ValueError("güven düzeyi geçersiz")
        if type(kaynak["imzali"]) is not bool:
            raise ValueError("imza durumu bool olmalı")
        if type(kaynak["aktif"]) is not bool:
            raise ValueError("aktif durumu bool olmalı")
        defter.append(dict(kaynak))
    return sorted(defter, key=lambda x: x["kaynak_id"])
```

```hint
Her kaydı alan alan doğrula ve kimlik kümesiyle tekiliği koru. Sürümde her sayısal bileşen için ayrı desen kullan; dönüşte kayıtları kopyala.
```
:::

::: anlat Parça ile kaynak sürümü birebir eşleşir
Getirilen parçanın kaynak kimliği defterde yoksa `kaynak`, sürümü farklıysa `surum`, kaynak imzasızsa `imza`, kaynak pasifse `durum` nedeni eklenir. Kaynak yoksa sürüm karşılaştırması yapılmaz ve güven `bilinmiyor` olur. Bütün nedenler yoksa parça doğrulanabilirdir.

`metin_sha256` alanı içerik bütünlüğünün bağlantı noktasıdır. Bu ders özeti yeniden hesaplamaz; 64 küçük harfli hexadecimal karakterden oluşan kayıt biçimini doğrular.
:::

::: gorev 2 · RAG parçalarına provenance üret
`provenance_uret(parcalalar, kaynaklar)` işlevini yaz. Kaynak defteri ilk görevdeki bütün kuralları sağlasın. Parçalar liste; her kayıt tam olarak `id`, `kaynak_id`, `belge_id`, `surum`, `metin_sha256`, `skor` alanlarını taşısın. Parça ve belge kimlikleri ilk görevdeki desene uysun; parça kimliği benzersiz olsun. Kaynak kimliği ve sürüm stringdir. Özet 64 küçük harfli hexadecimal karakterdir. Skor bool olmayan, sonlu ve 0–1 arası int/float olmalıdır. Geçersiz veride `ValueError` yükselt.

Yukarıdaki sırayla `kaynak`, `surum`, `imza`, `durum` nedenlerini topla. Her kayıt için `{"id":ID,"kaynak_id":KAYNAK,"guven":GUVEN,"dogrulanabilir":not nedenler,"skor":SKOR,"nedenler":[...]}` döndür. Kimliğe göre sırala, boş parçada boş liste döndür ve girdileri değiştirme.

Görünür veri: `veri/getirilen_parcalar.json` ve `veri/kaynak_defteri.json`. Doğru provenance README tablosundadır; özellikle `p-tahrif` için `surum`, `p-yetim` için `kaynak` nedeni beklenir.

```starter
from ai_savunma_veri import json_yukle

def provenance_uret(parcalalar, kaynaklar):
    # KUSURLU BAŞLANGIÇ KODU: yalnız kaynağın defterde olup olmadığına bakıyor; sürüm, imza ve aktiflik denetlenmiyor, bilinmeyen kaynağa "orta" güven veriyor!
    defter = {k["kaynak_id"]: k for k in kaynaklar}
    sonuc = []
    for p in parcalalar:
        k = defter.get(p["kaynak_id"])
        nedenler = [] if k else ["kaynak"]
        sonuc.append({"id": p["id"], "kaynak_id": p["kaynak_id"], "guven": k["guven"] if k else "orta",
                      "dogrulanabilir": not nedenler, "skor": p["skor"], "nedenler": nedenler})
    return sorted(sonuc, key=lambda x: x["id"])

kaynaklar = json_yukle("veri/kaynak_defteri.json")["kaynaklar"]
veri = json_yukle("veri/getirilen_parcalar.json")
for r in provenance_uret(veri["parcalar"], kaynaklar):
    print(r["id"], r["guven"], r["dogrulanabilir"], r["nedenler"], r["skor"])
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-16")
```

```test
import copy
K = [
    {"kaynak_id": "kurum-1", "tur": "kurumsal", "surum": "1.2.3", "guven": "yuksek", "imzali": True, "aktif": True},
    {"kaynak_id": "pasif-1", "tur": "acik", "surum": "2.0.0", "guven": "orta", "imzali": False, "aktif": False},
]
P = [
    {"id": "p-1", "kaynak_id": "kurum-1", "belge_id": "b-1", "surum": "1.2.3", "metin_sha256": "a" * 64, "skor": 0.9},
    {"id": "p-2", "kaynak_id": "kurum-1", "belge_id": "b-2", "surum": "1.2.4", "metin_sha256": "b" * 64, "skor": 0.8},
    {"id": "p-3", "kaynak_id": "yok-1", "belge_id": "b-3", "surum": "1.0.0", "metin_sha256": "c" * 64, "skor": 0.7},
    {"id": "p-4", "kaynak_id": "pasif-1", "belge_id": "b-4", "surum": "2.0.0", "metin_sha256": "d" * 64, "skor": 0.6},
]
BEKLENEN = [
    {"id": "p-1", "kaynak_id": "kurum-1", "guven": "yuksek", "dogrulanabilir": True, "skor": 0.9, "nedenler": []},
    {"id": "p-2", "kaynak_id": "kurum-1", "guven": "yuksek", "dogrulanabilir": False, "skor": 0.8, "nedenler": ["surum"]},
    {"id": "p-3", "kaynak_id": "yok-1", "guven": "bilinmiyor", "dogrulanabilir": False, "skor": 0.7, "nedenler": ["kaynak"]},
    {"id": "p-4", "kaynak_id": "pasif-1", "guven": "orta", "dogrulanabilir": False, "skor": 0.6, "nedenler": ["imza", "durum"]},
]
def sozlesme(fn):
    try:
        ponce = copy.deepcopy(P)
        konce = copy.deepcopy(K)
        if fn(P, K) != BEKLENEN or P != ponce or K != konce or fn(list(reversed(P)), K) != BEKLENEN or fn([], K) != []:
            return False
        for skor in (0, 1):
            if fn([dict(P[0], skor=skor)], K)[0]["skor"] != skor:
                return False
        if fn([dict(P[0], kaynak_id="a" * 64, surum="0.1.1")], [dict(K[0], kaynak_id="a" * 64, surum="0.1.1")])[0]["dogrulanabilir"] is not True:
            return False
        for parcalar, kaynaklar in [
            (None, K), ({}, K), ([None], K), (P, None), (P, [dict(K[0], imzali=1)]),
            (P, [dict(K[0], kaynak_id=None)]), (P, [dict(K[0], kaynak_id="a" * 65)]),
            (P, [dict(K[0], surum=None)]), (P, [dict(K[0], surum="01.2.3")]),
            (P, [None]), (P, [dict(K[0], ek=1)]), (P, [K[0], K[0]]),
            (P, [dict(K[0], tur="diger")]), (P, [dict(K[0], guven="diger")]), (P, [dict(K[0], aktif=0)]),
            ([dict(P[0], id=123)], K), ([dict(P[0], belge_id=123)], K), ([dict(P[0], metin_sha256=123)], K),
            ([dict(P[0], ek=1)], K), ([dict(P[0], id="")], K), ([dict(P[0], id="a b")], K),
            ([dict(P[0], id="a" * 65)], K), ([P[0], P[0]], K), ([dict(P[0], belge_id="")], K),
            ([dict(P[0], kaynak_id=None)], K), ([dict(P[0], surum=1)], K),
            ([dict(P[0], metin_sha256="a" * 63)], K), ([dict(P[0], metin_sha256="A" * 64)], K),
            ([dict(P[0], metin_sha256="g" * 64)], K), ([dict(P[0], skor=True)], K),
            ([dict(P[0], skor=-0.1)], K), ([dict(P[0], skor=1.1)], K),
            ([dict(P[0], skor=float("nan"))], K), ([dict(P[0], skor=10**400)], K), ([dict(P[0], skor=float("inf"))], K),
        ]:
            try:
                fn(parcalar, kaynaklar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(provenance_uret), "kaynak, sürüm, imza, durum ve skor doğrulaması korunmalı")
def m_kaynak(parcalalar, kaynaklar):
    return provenance_uret([dict(x, kaynak_id="kurum-1", surum="1.2.3") for x in parcalalar], kaynaklar)
def m_surum(parcalalar, kaynaklar):
    return provenance_uret([dict(x, surum="1.2.3") for x in parcalalar], kaynaklar)
def m_durum(parcalalar, kaynaklar):
    return provenance_uret(parcalalar, [dict(x, imzali=True, aktif=True) for x in kaynaklar])
for ad, mutant in [("kaynağı zorlayan", m_kaynak), ("sürümü zorlayan", m_surum), ("durumu zorlayan", m_durum)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def provenance_uret(parcalalar, kaynaklar):
    import re
    if not isinstance(kaynaklar, list):
        raise ValueError("kaynaklar liste olmalı")
    defter = {}
    for kaynak in kaynaklar:
        if not isinstance(kaynak, dict):
            raise ValueError("kaynak sözlük olmalı")
        if set(kaynak) != {"kaynak_id", "tur", "surum", "guven", "imzali", "aktif"}:
            raise ValueError("kaynak şeması geçersiz")
        kimlik = kaynak["kaynak_id"]
        if not isinstance(kimlik, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kimlik):
            raise ValueError("kaynak kimliği geçersiz")
        if kimlik in defter:
            raise ValueError("kaynak yinelenemez")
        if kaynak["tur"] not in ("kurumsal", "acik", "kullanici"):
            raise ValueError("kaynak türü geçersiz")
        if not isinstance(kaynak["surum"], str) or not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", kaynak["surum"]):
            raise ValueError("sürüm geçersiz")
        if kaynak["guven"] not in ("yuksek", "orta", "dusuk"):
            raise ValueError("güven geçersiz")
        if type(kaynak["imzali"]) is not bool or type(kaynak["aktif"]) is not bool:
            raise ValueError("kaynak durumları bool olmalı")
        defter[kimlik] = kaynak
    if not isinstance(parcalalar, list):
        raise ValueError("parçalar liste olmalı")
    kimlikler = set()
    rapor = []
    for parca in parcalalar:
        if not isinstance(parca, dict):
            raise ValueError("parça sözlük olmalı")
        if set(parca) != {"id", "kaynak_id", "belge_id", "surum", "metin_sha256", "skor"}:
            raise ValueError("parça şeması geçersiz")
        for alan in ("id", "belge_id"):
            if not isinstance(parca[alan], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", parca[alan]):
                raise ValueError(alan + " geçersiz")
        if parca["id"] in kimlikler:
            raise ValueError("parça kimliği yinelenemez")
        kimlikler.add(parca["id"])
        if not isinstance(parca["kaynak_id"], str) or not isinstance(parca["surum"], str):
            raise ValueError("kaynak ve sürüm metin olmalı")
        if not isinstance(parca["metin_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", parca["metin_sha256"]):
            raise ValueError("içerik özeti geçersiz")
        if type(parca["skor"]) not in (int, float):
            raise ValueError("skor int veya float olmalı")
        if not 0 <= parca["skor"] <= 1:
            raise ValueError("skor aralık dışı")
        kaynak = defter.get(parca["kaynak_id"])
        nedenler = []
        if kaynak is None:
            nedenler.append("kaynak")
        else:
            if parca["surum"] != kaynak["surum"]:
                nedenler.append("surum")
            if not kaynak["imzali"]:
                nedenler.append("imza")
            if not kaynak["aktif"]:
                nedenler.append("durum")
        rapor.append({"id": parca["id"], "kaynak_id": parca["kaynak_id"], "guven": kaynak["guven"] if kaynak else "bilinmiyor", "dogrulanabilir": not nedenler, "skor": parca["skor"], "nedenler": nedenler})
    return sorted(rapor, key=lambda x: x["id"])
```

```hint
Defteri kaynak kimliğiyle haritala. Kaynak yoksa yalnız `kaynak` nedeni üret; varsa sürüm, imza ve aktiflik denetimlerini bağımsız uygula.
```
:::

::: anlat Son seçim provenance ve güven eşiğini birlikte uygular
Seçim girdisi ikinci görevin raporudur. `dogrulanabilir` alanı neden listesiyle tutarlı olmalıdır; çelişkili kayıt güvenlik açısından biçim hatasıdır. Eşiği geçen doğrulanabilir parçalar skor bakımından azalan, eşit skorda kimliğe göre artan sıralanır.

Seçim sonucunda neden listesi taşınmaz. Kullanıcıya veya sonraki aşamaya yalnız parça kimliği, kaynak, güven ve skor verilir; doğrulanamayan kayıtlar hiçbir zaman yüksek skorla listeye girmez.
:::

::: gorev 3 · Doğrulanabilir parçaları güven eşiğiyle seç
`guvenli_rag_secimi(provenance, minimum_guven)` işlevini yaz. Minimum güven `yuksek`, `orta`, `dusuk` olmalıdır. Provenance liste; her kayıt tam olarak `id`, `kaynak_id`, `guven`, `dogrulanabilir`, `skor`, `nedenler` alanlarını taşısın. Kimlikler ilk görevdeki desene uysun ve benzersiz olsun; kaynak kimliği stringdir. Güven `yuksek`, `orta`, `dusuk`, `bilinmiyor`; doğrulanabilirlik gerçek bool; skor ikinci görevdeki aralıktadır. Nedenler `kaynak`, `surum`, `imza`, `durum` değerlerinden oluşan yinelenmeyen listedir ve `dogrulanabilir == (nedenler boş)` olmalıdır. Geçersiz veride `ValueError` yükselt.

Yalnız doğrulanabilir ve güven düzeyi eşiği karşılayan kayıtları seç. `yuksek` yalnız yükseği, `orta` yüksek ve ortayı, `dusuk` üç güven düzeyini kapsar; `bilinmiyor` hiçbir eşikte seçilmez. Skora göre azalan, eşit skorda kimliğe göre artan sırala.

Her seçim için `{"id":ID,"kaynak_id":KAYNAK,"guven":GUVEN,"skor":SKOR}` döndür. Boş girdide boş liste döndür ve girdiyi değiştirme.

Görünür veri: `veri/provenance_kayitlari.json`. `orta` eşiğinde doğru seçim `p-politika` ve `p-sss` olur. En yüksek skorlu `p-tahrif` ve `p-yetim` seçime girmemelidir.

```starter
from ai_savunma_veri import json_yukle

def guvenli_rag_secimi(provenance, minimum_guven):
    # KUSURLU BAŞLANGIÇ KODU: yalnız güven eşiğine bakıyor, doğrulanabilirliği yok sayıyor ve çelişkili kaydı denetlemiyor; yüksek skorlu tahrif edilmiş parça en üste çıkar!
    sira = ("yuksek", "orta", "dusuk")
    izinli = sira[:sira.index(minimum_guven) + 1]
    secilen = [{"id": p["id"], "kaynak_id": p["kaynak_id"], "guven": p["guven"], "skor": p["skor"]}
               for p in provenance if p["guven"] in izinli]
    return sorted(secilen, key=lambda x: (-x["skor"], x["id"]))

veri = json_yukle("veri/provenance_kayitlari.json")
for s in guvenli_rag_secimi(veri["provenance"], veri["minimum_guven"]):
    print(s["id"], s["guven"], s["skor"])
for b in veri["bozuk_kayitlar"]:
    try:
        guvenli_rag_secimi([b], "orta")
        print(b["id"], "KABUL edildi (yanlış)")
    except ValueError as hata:
        print(b["id"], "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-16")
```

```test
from collections import UserString
import copy
P = [
    {"id": "y-1", "kaynak_id": "kurum", "guven": "yuksek", "dogrulanabilir": True, "skor": 0.7, "nedenler": []},
    {"id": "y-2", "kaynak_id": "kurum", "guven": "yuksek", "dogrulanabilir": True, "skor": 0.9, "nedenler": []},
    {"id": "o-1", "kaynak_id": "acik", "guven": "orta", "dogrulanabilir": True, "skor": 0.8, "nedenler": []},
    {"id": "d-1", "kaynak_id": "kullanici", "guven": "dusuk", "dogrulanabilir": True, "skor": 0.95, "nedenler": []},
    {"id": "b-1", "kaynak_id": "yok", "guven": "bilinmiyor", "dogrulanabilir": False, "skor": 1.0, "nedenler": ["kaynak"]},
]
def beklenen(esik):
    secilen = [x for x in P if x["dogrulanabilir"] and x["guven"] in ({"yuksek": ["yuksek"], "orta": ["yuksek", "orta"], "dusuk": ["yuksek", "orta", "dusuk"]}[esik])]
    return [{k: x[k] for k in ("id", "kaynak_id", "guven", "skor")} for x in sorted(secilen, key=lambda x: (-x["skor"], x["id"]))]
def sozlesme(fn):
    try:
        once = copy.deepcopy(P)
        for esik in ("yuksek", "orta", "dusuk"):
            if fn(P, esik) != beklenen(esik) or P != once:
                return False
        if fn([], "dusuk") != [] or fn([P[0], P[1]], "yuksek")[0]["id"] != "y-2":
            return False
        if fn([dict(P[4], nedenler=[], dogrulanabilir=True)], "dusuk") != [] or fn([dict(P[0], id="y-3", dogrulanabilir=False, nedenler=["imza"])], "dusuk") != []:
            return False
        if fn([dict(P[0], skor=0)], "yuksek")[0]["skor"] != 0:
            return False
        for provenance, esik in [
            (None, "dusuk"), ({}, "dusuk"), ([None], "dusuk"), (P, "bilinmiyor"), ([], "bilinmiyor"), (P, None),
            ([dict(P[0], ek=1)], "dusuk"), ([dict(P[0], id="")], "dusuk"), ([dict(P[0], id=123)], "dusuk"), ([P[0], P[0]], "dusuk"),
            ([dict(P[0], id="a" * 65)], "dusuk"),
            ([dict(P[0], kaynak_id=None)], "dusuk"), ([dict(P[0], guven="diger")], "dusuk"),
            ([dict(P[0], dogrulanabilir=1)], "dusuk"), ([dict(P[0], skor=True)], "dusuk"),
            ([dict(P[0], skor=-0.1)], "dusuk"), ([dict(P[0], skor=1.1)], "dusuk"),
            ([dict(P[0], skor=float("nan"))], "dusuk"), ([dict(P[0], skor=float("inf"))], "dusuk"), ([dict(P[0], skor=10**400)], "dusuk"), ([dict(P[0], nedenler=[[]])], "dusuk"), ([dict(P[0], nedenler=[UserString("imza")], dogrulanabilir=False)], "dusuk"),
            ([dict(P[0], nedenler=None)], "dusuk"), ([dict(P[0], nedenler=["diger"])], "dusuk"), ([dict(P[0], dogrulanabilir=False, nedenler=["diger"])], "dusuk"),
            ([dict(P[0], nedenler=["kaynak", "kaynak"], dogrulanabilir=False)], "dusuk"),
            ([dict(P[0], nedenler=["kaynak"])], "dusuk"),
        ]:
            try:
                fn(provenance, esik)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(guvenli_rag_secimi), "provenance tutarlılığı, güven eşiği ve sıralama korunmalı")
def m_dogrulama(provenance, esik):
    return guvenli_rag_secimi([dict(x, dogrulanabilir=True, nedenler=[]) for x in provenance], esik)
def m_guven(provenance, esik):
    return guvenli_rag_secimi([dict(x, guven="yuksek") for x in provenance], esik)
def m_skor(provenance, esik):
    return guvenli_rag_secimi([dict(x, skor=0) for x in provenance], esik)
for ad, mutant in [("doğrulamayı zorlayan", m_dogrulama), ("güveni yükselten", m_guven), ("skoru silen", m_skor)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def guvenli_rag_secimi(provenance, minimum_guven):
    import re
    sira = ("yuksek", "orta", "dusuk")
    if minimum_guven not in sira:
        raise ValueError("minimum güven geçersiz")
    if not isinstance(provenance, list):
        raise ValueError("provenance liste olmalı")
    kimlikler = set()
    secilen = []
    for kayit in provenance:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"id", "kaynak_id", "guven", "dogrulanabilir", "skor", "nedenler"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
            raise ValueError("kimlik geçersiz")
        if kayit["id"] in kimlikler:
            raise ValueError("kimlik yinelenemez")
        kimlikler.add(kayit["id"])
        if not isinstance(kayit["kaynak_id"], str):
            raise ValueError("kaynak kimliği metin olmalı")
        if kayit["guven"] not in ("yuksek", "orta", "dusuk", "bilinmiyor"):
            raise ValueError("güven geçersiz")
        if type(kayit["dogrulanabilir"]) is not bool:
            raise ValueError("doğrulanabilirlik bool olmalı")
        if type(kayit["skor"]) not in (int, float):
            raise ValueError("skor int veya float olmalı")
        if not 0 <= kayit["skor"] <= 1:
            raise ValueError("skor aralık dışı")
        if not isinstance(kayit["nedenler"], list):
            raise ValueError("nedenler liste olmalı")
        if any(not isinstance(neden, str) or neden not in ("kaynak", "surum", "imza", "durum") for neden in kayit["nedenler"]):
            raise ValueError("neden geçersiz")
        if len(set(kayit["nedenler"])) != len(kayit["nedenler"]):
            raise ValueError("nedenler yinelenemez")
        if kayit["dogrulanabilir"] != (not kayit["nedenler"]):
            raise ValueError("doğrulanabilirlik nedenlerle tutarsız")
        if kayit["dogrulanabilir"] and kayit["guven"] in sira and sira.index(kayit["guven"]) <= sira.index(minimum_guven):
            secilen.append({"id": kayit["id"], "kaynak_id": kayit["kaynak_id"], "guven": kayit["guven"], "skor": kayit["skor"]})
    return sorted(secilen, key=lambda x: (-x["skor"], x["id"]))
```

```hint
Önce raporun iç tutarlılığını doğrula. Güvenleri sayısal sıraya çevir; seçimi yaptıktan sonra `(-skor, id)` anahtarıyla sırala.
```
:::

::: anlat Alakalılık sıralaması güven vermez; seçim gerçek skorlarla sınanır
Görev 1–3'te skorlar elle yazılmıştı. Bu adımda skorları **gerçek bir gömme modeli** üretir. `sandbox/ai_gercek_ai_savunma_16.py` deneyi şunları yapar:

1. Kurulu `all-minilm:22m` embedding modeli (Ollama `/api/embed`) sorguyu ("İade süresi kaç gündür?") ve üç parçayı 384 boyutlu vektörlere çevirir. Vektörler eksik ya da geçersizse deney "tamamlanmadı" diye durur.
2. Her parça için sorguyla kosinüs benzerliği hesaplanır. Bu, iki vektörün açısının kosinüsüdür; 1'e yakınsa anlam yakındır.
3. Parçalar şunlardır:
   - Güncel kurumsal politika.
   - Aynı kaynağın sahte `9.9.9` sürümünü iddia eden ve içinde bir enjeksiyon talimatı taşıyan tahrif edilmiş parça.
   - Açık kaynaklı bir kargo bilgisi.
4. Provenance kaynak defterine göre bağımsız olarak üretilir. Senin `guvenli_rag_secimi` işlevin `orta` eşiğiyle seçim yapar. Aynı provenance bağımsız bir referans seçimden de geçirilir.

Test önce işlevini gizli deterministik kayıtlarla sınar. Ardından gerçek skorlarla yaptığın seçimin referans seçimle birebir aynı olmasını ve tahrif edilmiş parçanın seçime girmemesini ister. Tahrif edilmiş parçanın skor sıralamasındaki yeri kabul koşulu değildir; bulgu olarak kaydedilir. Metinler, provenance ve skorlar kanıta yazılır.

Ders yazılırken bu makinede elde edilen skorlar şunlardı: güncel politika 0.761, tahrif edilmiş parça 0.579, kargo parçası 0.496. Tahrif edilmiş parça, seçilen kargo parçasından daha alakalı bulundu ama `surum` nedeniyle elendi. Yalnız skora göre ilk iki parçayı alan bir sistem, enjeksiyon talimatlı bu parçayı modele verirdi. Dikkat: tahrif edilmiş metin doğru cevabı da içeriyor. Saldırgan çoğu zaman doğru bilginin yanına talimat ekler. Bu yüzden içerik "doğru görünüyor" diye güvenilir sayılmaz.

:::

::: gorev Gerçek deney · Gerçek skorlarla provenance seçimi
`guvenli_rag_secimi(provenance, minimum_guven)` işlevini yaz. Kuralları ve çıktısı 3. görevdekiyle **aynıdır**. Deney gerçek gömme modeliyle skorları üretir ve provenance'ı kaynak defterine göre kurar. Senin seçimin yalnız doğrulanabilir ve güven eşiğini karşılayan parçaları almalıdır; tahrif edilmiş parça yüksek skorlu olsa bile elenir. `sandbox.ai_gercek_ai_savunma_16` içindeki `guvenli_rag_secimi_referans` ve `referans_provenance` yalnız test içindir; onları import etmek veya kaynaklarını okuyup çalıştırmak Kontrol'de reddedilir.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def guvenli_rag_secimi(provenance, minimum_guven):
    # KUSURLU BAŞLANGIÇ KODU: güveni ve doğrulanabilirliği yok sayıp en yüksek skorlu iki parçayı alıyor; tahrif edilmiş parça kargo parçasının yerine bağlama girer!
    return [{"id": p["id"], "kaynak_id": p["kaynak_id"], "guven": p["guven"], "skor": p["skor"]}
            for p in sorted(provenance, key=lambda x: (-x["skor"], x["id"]))[:2]]

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_16 as deney
    deney.goster(guvenli_rag_secimi)
```

```test
import ast
import ai_lab
from sandbox import ai_gercek_ai_savunma_16 as D
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
_yasak = ("guvenli_rag_secimi_referans", "referans_provenance", "kanit_yaz")
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
if not kontrol(not sorun, "Kendi guvenli_rag_secimi işlevini yaz; laboratuvar/referans kullanımı yasak: " + "; ".join(sorted(set(sorun)))):
    stop()
fn = need("guvenli_rag_secimi")
P = [
    {"id": "y-1", "kaynak_id": "kurum", "guven": "yuksek", "dogrulanabilir": True, "skor": 0.7, "nedenler": []},
    {"id": "o-1", "kaynak_id": "acik", "guven": "orta", "dogrulanabilir": True, "skor": 0.5, "nedenler": []},
    {"id": "z-1", "kaynak_id": "kurum", "guven": "yuksek", "dogrulanabilir": False, "skor": 0.95, "nedenler": ["surum"]},
]
BEKLENEN = [
    {"id": "y-1", "kaynak_id": "kurum", "guven": "yuksek", "skor": 0.7},
    {"id": "o-1", "kaynak_id": "acik", "guven": "orta", "skor": 0.5},
]
def sozlesme(f):
    try:
        if f(P, "orta") != BEKLENEN or f([], "orta") != []:
            return False
        if f(P, "yuksek") != [{"id": "y-1", "kaynak_id": "kurum", "guven": "yuksek", "skor": 0.7}]:
            return False
        if f(P, "dusuk") != BEKLENEN:
            return False
        for kotu_esik in ("gecersiz", None):
            try:
                f([], kotu_esik)
                return False
            except ValueError:
                pass
        for sc in (0.0, 1.0):
            if f([dict(P[0], skor=sc)], "yuksek")[0]["skor"] != sc:
                return False
        esit = [dict(P[0], id="b-2", skor=0.5), dict(P[1], id="b-1")]
        if [x["id"] for x in f(esit, "orta")] != ["b-1", "b-2"]:
            return False
        bilinmeyen = [{"id": "u-1", "kaynak_id": "yok", "guven": "bilinmiyor", "dogrulanabilir": False, "skor": 0.99, "nedenler": ["kaynak"]},
                      {"id": "u-2", "kaynak_id": "yok", "guven": "bilinmiyor", "dogrulanabilir": True, "skor": 0.99, "nedenler": []}]
        if f(bilinmeyen, "dusuk") != []:
            return False
        for bozuk in (None, {}, [None], [dict(P[0], ek=1)], [dict(P[0], id=123)], [dict(P[0], id="")], [dict(P[0], id="a" * 65)],
                      [dict(P[0], kaynak_id=123)], [dict(P[0], dogrulanabilir=1)], [dict(P[0], dogrulanabilir=False)],
                      [dict(P[0], nedenler=None)], [dict(P[0], nedenler=["bilinmeyen"])], [dict(P[0], dogrulanabilir=False, nedenler=["diger"])],
                      [P[0], P[0]], [dict(P[0], skor=-0.1)], [dict(P[0], skor=1.5)], [dict(P[0], skor=True)], [dict(P[0], skor=float("nan"))], [dict(P[0], skor=float("inf"))], [dict(P[0], skor=10**400)], [dict(P[0], nedenler=[[]])],
                      [dict(P[2], nedenler=["surum", "surum"])], [dict(P[0], guven="kritik")]):
            try:
                f(bozuk, "orta")
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(fn), "doğrulanabilirlik, güven eşiği, tutarlılık ve sıralama korunmalı")
r, oz = None, None
if all(sonuclar):
    try:
        r = D.deney(fn)
    except ai_lab.GercekLabYok as e:
        kontrol(False, f"GERÇEK MODEL YOK, deney yapılmadı: {e}")
        stop()
    kontrol(not r["zehirli_secildi"] and r["zehirli_dogrulanabilir"] is False,
            "tampered parça doğrulanamadı ve seçime girmedi")
    kontrol(r["secim_dogru"], f"gerçek skorlarla seçim bağımsız referansla aynı olmalı: senin {r['secim']} · beklenen {r['beklenen_secim']}")
    oz = D.ozet(r)
yol = ai_lab.kanit_yaz("savunma-rag", {"kaynak": "gercek", "kabul": all(sonuclar), "ders": "ai-savunma-16",
                                       "ortam": (r or {}).get("ortam"), "ozet": oz,
                                       "provenance": (r or {}).get("provenance"), "metinler": (r or {}).get("metinler")})
if oz:
    ok(True, f"BULGU ({(r['ortam'].get('gomme') or {}).get('model')}): gerçek skorlar {oz['skorlar']}; seçilen {oz['secilen']}. "
             f"Tampered parça nedenler {oz['zehirli_nedenler']} ile seçilmedi; seçilen bir parçadan daha alakalı olsa bile elendi "
             f"({oz['zehirli_daha_alakali']}). Alakalılık sıralaması güven vermez; provenance karar verir.")
```

```solution
import ai_lab

def guvenli_rag_secimi(provenance, minimum_guven):
    import re
    sira = ("yuksek", "orta", "dusuk")
    if minimum_guven not in sira:
        raise ValueError("minimum güven geçersiz")
    if not isinstance(provenance, list):
        raise ValueError("provenance liste olmalı")
    kimlikler = set()
    secilen = []
    for kayit in provenance:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"id", "kaynak_id", "guven", "dogrulanabilir", "skor", "nedenler"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
            raise ValueError("kimlik geçersiz")
        if kayit["id"] in kimlikler:
            raise ValueError("kimlik yinelenemez")
        kimlikler.add(kayit["id"])
        if not isinstance(kayit["kaynak_id"], str):
            raise ValueError("kaynak kimliği metin olmalı")
        if kayit["guven"] not in ("yuksek", "orta", "dusuk", "bilinmiyor"):
            raise ValueError("güven geçersiz")
        if type(kayit["dogrulanabilir"]) is not bool:
            raise ValueError("doğrulanabilirlik bool olmalı")
        if type(kayit["skor"]) not in (int, float):
            raise ValueError("skor int veya float olmalı")
        if not 0 <= kayit["skor"] <= 1:
            raise ValueError("skor aralık dışı")
        if not isinstance(kayit["nedenler"], list):
            raise ValueError("nedenler liste olmalı")
        if any(not isinstance(neden, str) or neden not in ("kaynak", "surum", "imza", "durum") for neden in kayit["nedenler"]):
            raise ValueError("neden geçersiz")
        if len(set(kayit["nedenler"])) != len(kayit["nedenler"]):
            raise ValueError("nedenler yinelenemez")
        if kayit["dogrulanabilir"] != (not kayit["nedenler"]):
            raise ValueError("doğrulanabilirlik nedenlerle tutarsız")
        if kayit["dogrulanabilir"] and kayit["guven"] in sira and sira.index(kayit["guven"]) <= sira.index(minimum_guven):
            secilen.append({"id": kayit["id"], "kaynak_id": kayit["kaynak_id"], "guven": kayit["guven"], "skor": kayit["skor"]})
    return sorted(secilen, key=lambda x: (-x["skor"], x["id"]))

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_16 as deney
    deney.goster(guvenli_rag_secimi)
```

```hint
Bu işlev 3. görevdeki `guvenli_rag_secimi` ile birebir aynıdır; tek fark, skorların gerçek gömme modelinden gelmesidir. Raporun iç tutarlılığını doğrula; seçimi `(-skor, id)` anahtarıyla sırala.
```
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
Provenance bir parçanın kaynak, sürüm ve bütünlük bağını taşır. Kaynak defteri bağımsız doğrulama dayanağıdır; yüksek retrieval skoru bu eşlemenin yerini tutmaz. Sürümü sıralamakla tam sürüm eşitliği denetlemek farklı sözleşmelerdir. Önce defter ve parça bağını doğrula, sonra güven düzeyi eşiğini uygula. Bir parçanın imzası tutması içindeki doğal dil talimatının yetkili olduğunu göstermez.

Önkoşul ve yol köprüsü: ai-saldiri-14 RAG zehirlenmesi.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| Benzerlik yüksekse kaynak güvenilirdir | Relevance ile provenance/trust ayrı eksenlerdir |

Dinleyiciye sor: Savunma güvenlik metriğini iyileştirirken meşru kullanıma ne kaybettirebilir? Ham çıktı ve ölçüm paydalarıyla cevapla.
:::


::: anlat Birincil kaynak ve deney sınırı
[Qdrant Filtering](https://qdrant.tech/documentation/search/filtering/): Payload filtresi için araç referansı. Provenance kaynak/sürüm doğrulaması dersin bağımsız uygulama katmanıdır. Çalışan sürüm ve gerçek sonuç kanıtta kayıtlıdır.
:::
