---
id: ai-saldiri-07
title: Model Extraction ve Davranışsal Parmak İzi
summary: Tekrarlanan yerel sorgularla yanıt kararlılığını ölç, kanonik davranış kaydından parmak izi üret ve iki fixture arasındaki benzerliği model kimliği iddiasından ayır.
timeout: 45
esleme: ai-guvence-01, ai-saldiri-33
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et: Davranış gözlemi modelin kendisi değildir

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Gerçek bir extraction ya da parmak izi çalışmasında bir API uç noktasına yüzlerce, binlerce sorgu gönderilir. İstekler ve ham yanıtlar (Ollama'da `/api/chat` gövdesi, `model`, `seed`, `temperature`, `done_reason`) kaydedilir. Sonra yanıt dağılımı ya da logit/olasılık bilgisi bir aday modelle karşılaştırılır. Fiyatlandırma, hız sınırı ve kullanım şartları da sorgu bütçesini belirler. | Görev 1–3: `veri/sorgu_seti.json` (sorgular ve kayıttan oynatılan yanıt kaseti), `veri/gozlem_kayitlari.json` ve `veri/uc_karsilastirma.json` içindeki **sentetik** kayıtlar. Son adım: kendi CPU Ollama sunucusunda kurulu yerel modele iki profille (`T=0.0` ve `T=0.6`) 2 sorgu × 2 tekrar × 2 profil = 8 gerçek çağrı. | Birkaç sorgu, bir modelin ağırlıklarını, mimarisini ya da kimliğini ortaya çıkarmaz. Eşleşme oranı yalnız bu sorgu setinde ölçülür. Son adımdaki iki profil aynı modeldir; farklılık kimlik farkı değildir. Ders başka birinin uç noktasına sorgu göndermez. |

> [!NOT]
> Görev 1–3 sentetik veriyle çalışır. Bu görevlerde model ve ağ yoktur; model çağrısı kaydedilmiş yanıtları sırayla veren bir adaptördür. Son adımdaki **Gerçek deney** görevi yalnız kurulu yerel Ollama modelini kendi CPU sunucusunda kullanır. `veri/` dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalanır; kopyada yaptığın değişiklik bir sonraki çalıştırmada sıfırlanır, **kalıcılık yoktur**. Kontrol bu dosyalardan ayrı, gizli verilerle sınar.

Model extraction bazen model parametrelerini veya eşdeğer bir kopyayı çıkarma, bazen de yalnız dışarıdan gözlenen davranışı çıkarma anlamında kullanılır. Bu derste ikinci, sınırlı anlamı ölçüyoruz: sabit sorgulara verilen yanıtları kaydetmek. Elde edilen parmak izi modelin mimarisini, ağırlıklarını veya gerçek kimliğini kanıtlamaz.

Bir davranış deneyinde en az şu katmanlar ayrılmalıdır:

- **Sorgu seti:** Kimliği, metni ve tekrar sayısı önceden belli girdiler.
- **Gözlem:** Her sorgu ve tekrar için ham yanıt; taşıma hatası yanıta çevrilmez.
- **Kararlılık:** Aynı vakanın tekrarları aynı yanıtı veriyor mu?
- **Parmak izi:** Kanonik gözlem kaydının içerik özeti.
- **Karşılaştırma:** Aynı sorgu/tekrar anahtarlarındaki yanıt eşleşmesi.

```python
import hashlib
import json
kayit = [{"vaka_id": "q1", "tekrar": 1, "yanit": "EVET"}]
kanonik = json.dumps(kayit, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
print(len(kayit), kayit[0]["yanit"])
print(hashlib.sha256(kanonik.encode("utf-8")).hexdigest()[:12])
```

Gerçek modelde `temperature=0` bile her ortamda mutlak tekrarlanabilirlik garantisi değildir. Sürüm, çalışma zamanı, kuantizasyon ve sohbet şablonu değişebilir. Görev 1–3 ağ çağrısı yapmadan deterministik fixture kullanır. Son adım yalnız yerel Ollama modelini çağırır. İki durumda da sonuçları gerçek model extraction başarısı olarak sunmayız.

**Görev 1'de sık tuzaklar:** Doğrulamayı çağrılarla aynı döngüde yapmak, bozuk sette önceki geçerli sorgular için modeli çağırır. Gerçek bir API'de bu, ücreti ödenmiş ve kaydı tutulmuş istekler demektir (`veri/sorgu_seti.json`, altıncı bozuk set). `range(tekrar)` tekrarları `0`'dan sayar. `int(True)` ve `int(2.0)` bozuk değerleri sessizce kabul eder. Adaptör hatasını `"HATA"` yanıtına çevirmek, taşıma hatasını bir model davranışı gibi gösterir ve parmak izine karıştırır (`kesinti`).
:::

::: tahmin
Aynı vakanın iki tekrarı farklı yanıt veriyor. Üç çıktı satırını yaz:

```python
kayitlar = [
    ("q1", 1, "EVET"),
    ("q1", 2, "HAYIR"),
    ("q2", 1, "EVET"),
    ("q2", 2, "EVET"),
]
for vaka in ("q1", "q2"):
    yanitlar = [yanit for kimlik, _, yanit in kayitlar if kimlik == vaka]
    print(vaka, len(set(yanitlar)) == 1)
print(sum(yanit == "EVET" for _, _, yanit in kayitlar))
```

???

```cikti
q1 False
q2 True
3
```

`q1` kararsız, `q2` kararlıdır. Dört yanıtın üçü `EVET` olması iki vakanın da kararlı olduğu anlamına gelmez.
:::

::: gorev 1 · Tekrarlı sorgu matrisini modelden topla
`sorgu_matrisi(sorgular, model_cagir)` işlevini yaz. Her sorgu `id`, `metin`, `tekrar` alanlarını taşır. `id` benzersiz ve boş olmayan string, `metin` string, `tekrar` bool olmayan `1..4` aralığında tam sayı olmalıdır. Kuralları çağrıdan önce doğrula; geçersiz sette modeli hiç çağırma ve `ValueError` yükselt.

Her vaka için tekrar `1..tekrar` sırasıyla `model_cagir(metin)` çağır. Dönüş kayıtları `vaka_id`, `tekrar`, `metin`, `yanit` alanlarını taşısın; sorgu ve tekrar sırası korunsun. Adaptör hatasını yakalayıp sahte yanıt üretme. Girdi listesini değiştirme.

Görünür veri: `veri/sorgu_seti.json`. Adaptör, kasetteki yanıtları sırayla verir ve kaç kez çağrıldığını sayar. Bozuk setlerde model hiç çağrılmamalıdır.

```starter
from ai_saldiri_veri import json_yukle

def sorgu_matrisi(sorgular, model_cagir):
    # KUSURLU BAŞLANGIÇ KODU: doğrulamayı çağrılarla iç içe yapıyor (geçersiz sorgudan önceki sorgular modeli çağırır), tekrarı 0'dan sayıyor, int() ile bool/float tekrarı kabul ediyor, 1..4 sınırını ve yinelenen kimliği denetlemiyor ve adaptör hatasını "HATA" yanıtına çeviriyor!
    kayitlar = []
    for sorgu in sorgular:
        if not sorgu["id"]:
            raise ValueError("sorgu kimliği boş")
        for tekrar in range(int(sorgu["tekrar"])):
            try:
                yanit = model_cagir(sorgu["metin"])
            except Exception:
                yanit = "HATA"
            kayitlar.append({"vaka_id": sorgu["id"], "tekrar": tekrar, "metin": sorgu["metin"], "yanit": yanit})
    return kayitlar

veri = json_yukle("veri/sorgu_seti.json")
def adaptor_kur():
    sira = {m: list(y) for m, y in veri["kaset"].items()}
    sayac = [0]
    def model_cagir(metin):
        sayac[0] += 1
        if metin.startswith("KESİNTİ"):
            raise TimeoutError("model çağrısı zaman aşımına uğradı")
        return sira[metin].pop(0) if sira.get(metin) else "x"
    return model_cagir, sayac
model_cagir, _ = adaptor_kur()
sonuc = sorgu_matrisi(veri["sorgular"], model_cagir)
print("doğru" if sonuc == veri["beklenen"] else "YANLIŞ", [(k["vaka_id"], k["tekrar"], k["yanit"]) for k in sonuc])
for kume in veri["bozuk_setler"]:
    model_cagir, sayac = adaptor_kur()
    try:
        sorgu_matrisi(kume, model_cagir)
        print(kume, "KABUL edildi (yanlış), çağrı:", sayac[0])
    except ValueError as hata:
        print("reddedildi:", hata, "| çağrı:", sayac[0], "(0 olmalı)")
model_cagir, _ = adaptor_kur()
try:
    print("kesinti yutuldu (yanlış):", sorgu_matrisi(veri["kesinti"]["sorgular"], model_cagir))
except TimeoutError as hata:
    print("kesinti görünür kaldı:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-07")
```

```test
import copy
SORGULAR = [{"id": "q1", "metin": "Sınıfla: A", "tekrar": 2}, {"id": "q2", "metin": "Sınıfla: B", "tekrar": 1}]
def sozlesme(fn):
    try:
        cagrilar = []
        def model(metin):
            cagrilar.append(metin)
            return "EVET" if metin.endswith("A") else "HAYIR"
        once = copy.deepcopy(SORGULAR)
        sonuc = fn(SORGULAR, model)
        beklenen = [
            {"vaka_id": "q1", "tekrar": 1, "metin": "Sınıfla: A", "yanit": "EVET"},
            {"vaka_id": "q1", "tekrar": 2, "metin": "Sınıfla: A", "yanit": "EVET"},
            {"vaka_id": "q2", "tekrar": 1, "metin": "Sınıfla: B", "yanit": "HAYIR"},
        ]
        if sonuc != beklenen or cagrilar != ["Sınıfla: A", "Sınıfla: A", "Sınıfla: B"] or SORGULAR != once:
            return False
        if fn([], model) != [] or len(fn([{"id": "q", "metin": "x", "tekrar": 4}], model)) != 4:
            return False
        for sorgu in [
            [{"id": "", "metin": "x", "tekrar": 1}],
            [{"id": 123, "metin": "x", "tekrar": 1}],
            [{"id": "q", "metin": "x", "tekrar": 2.0}],
            [{"id": "q", "metin": "x", "tekrar": "1"}],
            [{"id": "q", "metin": "x", "tekrar": 0}],
            [{"id": "q", "metin": "x", "tekrar": 5}],
            [{"id": "q", "metin": "x", "tekrar": True}],
            [{"id": "q", "metin": 3, "tekrar": 1}],
            [{"id": "q", "metin": "x", "tekrar": 1}, {"id": "q", "metin": "y", "tekrar": 1}],
        ]:
            sayi = [0]
            def yasak(metin):
                sayi[0] += 1
                return "x"
            try:
                fn(sorgu, yasak)
                return False
            except ValueError:
                if sayi[0] != 0:
                    return False
        try:
            fn([{"id": "q", "metin": "x", "tekrar": 1}], lambda _: (_ for _ in ()).throw(RuntimeError("kesinti")))
            return False
        except RuntimeError:
            pass
        return True
    except Exception:
        return False
ok(sozlesme(sorgu_matrisi), "sıra, tekrar, adaptör hatası ve çağrıdan önce doğrulama korunmalı")
def m_tekrar(sorgular, model_cagir):
    return [{"vaka_id": s["id"], "tekrar": t, "metin": s["metin"], "yanit": model_cagir(s["metin"])} for s in sorgular for t in range(s["tekrar"])]
def m_once_cagir(sorgular, model_cagir):
    return [{"vaka_id": s["id"], "tekrar": t, "metin": s["metin"], "yanit": model_cagir(s["metin"])} for s in sorgular for t in range(1, s["tekrar"] + 1)]
def m_hata_yutan(sorgular, model_cagir):
    try:
        return sorgu_matrisi(sorgular, model_cagir)
    except RuntimeError:
        return []
for ad, mutant in [("tekrarı sıfırdan başlatan", m_tekrar), ("seti doğrulamadan çağıran", m_once_cagir), ("adaptör hatasını yutan", m_hata_yutan)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def sorgu_matrisi(sorgular, model_cagir):
    kimlikler = set()
    for sorgu in sorgular:
        tekrar = sorgu["tekrar"]
        if not isinstance(sorgu["id"], str) or not sorgu["id"] or sorgu["id"] in kimlikler:
            raise ValueError("sorgu kimliği boş veya yinelenen")
        if not isinstance(sorgu["metin"], str):
            raise ValueError("sorgu metni string olmalı")
        if isinstance(tekrar, bool) or not isinstance(tekrar, int) or not 1 <= tekrar <= 4:
            raise ValueError("tekrar 1..4 olmalı")
        kimlikler.add(sorgu["id"])
    return [
        {"vaka_id": sorgu["id"], "tekrar": tekrar, "metin": sorgu["metin"], "yanit": model_cagir(sorgu["metin"])}
        for sorgu in sorgular
        for tekrar in range(1, sorgu["tekrar"] + 1)
    ]
```

```hint
İki aşama kur: önce bütün sorguları doğrula, sonra list comprehension ile çağrıları yap. Hata yakalama eklemezsen adaptör hatası doğal olarak görünür kalır.
```
:::

::: anlat Parmak izi gözlem sözleşmesine bağlıdır
Aynı yanıtları farklı sırada toplamak gözlem içeriğini değiştirmez; kayıtları `(vaka_id, tekrar)` ile sıralayıp kanonik JSON üretmek bu sıra farkını ortadan kaldırır. Buna karşılık bir yanıtın değişmesi parmak izini değiştirmelidir. Tekrar anahtarı yinelenirse kayıt kümesi belirsizdir ve imza hesaplanmamalıdır.

Kararlılık ayrı bir ölçümdür. Her vaka için tekrar yanıtlarının kümesi tek elemanlıysa vaka kararlıdır. Üç vakanın ikisi kararlıysa oran `2/3` olur. Tek bir parmak izi, farklı iki modelin aynı fixture'da aynı cevabı veremeyeceğini göstermez; yalnız bu gözlem setinin aynı olduğunu gösterir.

**Sık tuzaklar:** Yanıtları `strip()` ile "düzeltmek", ölçülen davranışı değiştirir. `veri/gozlem_kayitlari.json` içindeki `HAYIR\n` yanıtı ayrı bir gözlemdir. Normalleştirme gerekiyorsa sözleşmede açıkça yazılmalıdır. `ensure_ascii` varsayılanıyla `Türkçe` yanıtı `\u` kaçışına döner ve başka bir imza üretir. Kararlılığı kayıt sayısına bölmek, tekrar sayısı fazla olan vakaya gereğinden fazla ağırlık verir.
:::

::: gorev 2 · Kanonik davranış parmak izi ve kararlılık üret
`parmak_izi(kayitlar)` işlevini yaz. Her kayıt `vaka_id`, `tekrar`, `yanit` alanlarını taşır; `vaka_id` boş olmayan string, `tekrar` bool olmayan pozitif tam sayı, `yanit` string olmalıdır. `(vaka_id, tekrar)` benzersizdir. Hatalı kayıtta `ValueError` yükselt.

Kayıtları `(vaka_id, tekrar)` ile artan sıralayıp kanonik JSON (`ensure_ascii=False`, `sort_keys=True`, `separators=(",", ":")`) üzerinden SHA-256 hex özeti hesapla. Dönüş `{"imza", "gozlem", "kararli_vaka", "kararlilik"}` sözlüğüdür. `gozlem` kayıt sayısıdır; `kararli_vaka`, bütün tekrarları aynı yanıtı veren vaka sayısıdır; `kararlilik = kararli_vaka / vaka_sayisi`, vaka yoksa `None` olur. Girdiyi değiştirme.

Görünür veri: `veri/gozlem_kayitlari.json`. Beklenen sonuç dosyanın `beklenen` alanındadır. Ters sırada verilen kayıtlar aynı imzayı üretmelidir.

```starter
import hashlib
import json
from ai_saldiri_veri import json_yukle

def parmak_izi(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: kayıtları sıralamadan ve ensure_ascii=True ile özetliyor (kayıt sırası imzayı değiştirir), yanıtları strip() ile "düzeltiyor", kararlılığı vaka yerine kayıt sayısına bölüyor, boş sette 0.0 dönüyor ve yinelenen anahtarı denetlemiyor!
    temiz = [dict(k, yanit=str(k["yanit"]).strip()) for k in kayitlar]
    kanonik = json.dumps(temiz, sort_keys=True)
    yanitlar = {}
    for k in temiz:
        yanitlar.setdefault(k["vaka_id"], set()).add(k["yanit"])
    kararli = sum(len(v) == 1 for v in yanitlar.values())
    return {
        "imza": hashlib.sha256(kanonik.encode("utf-8")).hexdigest(),
        "gozlem": len(kayitlar),
        "kararli_vaka": kararli,
        "kararlilik": kararli / len(kayitlar) if kayitlar else 0.0,
    }

veri = json_yukle("veri/gozlem_kayitlari.json")
sonuc = parmak_izi(veri["kayitlar"])
print("sonuç   :", sonuc)
print("beklenen:", veri["beklenen"])
print("ters sırada aynı imza:", parmak_izi(list(reversed(veri["kayitlar"])))["imza"] == sonuc["imza"])
for kume in veri["bozuk_kumeler"]:
    try:
        parmak_izi(kume)
        print(kume, "KABUL edildi (yanlış)")
    except ValueError as hata:
        print("reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-07")
```

```test
import copy
import hashlib
import json
KAYITLAR = [
    {"vaka_id": "q2", "tekrar": 1, "yanit": "HAYIR"},
    {"vaka_id": "q1", "tekrar": 2, "yanit": "HAYIR"},
    {"vaka_id": "q1", "tekrar": 1, "yanit": "EVET"},
    {"vaka_id": "q2", "tekrar": 2, "yanit": "HAYIR"},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(KAYITLAR)
        sonuc = fn(KAYITLAR)
        sirali = sorted(KAYITLAR, key=lambda x: (x["vaka_id"], x["tekrar"]))
        kanonik = json.dumps(sirali, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if sonuc != {"imza": hashlib.sha256(kanonik.encode()).hexdigest(), "gozlem": 4, "kararli_vaka": 1, "kararlilik": 0.5} or KAYITLAR != once:
            return False
        if fn(list(reversed(KAYITLAR))) != sonuc:
            return False
        degisen = copy.deepcopy(KAYITLAR)
        degisen[1]["yanit"] = "EVET"
        if fn(degisen)["imza"] == sonuc["imza"] or fn(degisen)["kararli_vaka"] != 2:
            return False
        tr_k = [{"vaka_id": "q1", "tekrar": 1, "yanit": "Özet"}]
        if fn(tr_k)["imza"] != hashlib.sha256(json.dumps([{"tekrar": 1, "vaka_id": "q1", "yanit": "Özet"}], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest():
            return False
        bos = fn([])
        if bos["gozlem"] != 0 or bos["kararlilik"] is not None or bos["imza"] != hashlib.sha256(b"[]").hexdigest():
            return False
        for kayit in [
            [{"vaka_id": "q", "tekrar": 1, "yanit": "x"}, {"vaka_id": "q", "tekrar": 1, "yanit": "y"}],
            [{"vaka_id": "", "tekrar": 1, "yanit": "x"}],
            [{"vaka_id": 123, "tekrar": 1, "yanit": "x"}],
            [{"vaka_id": "q", "tekrar": 1.5, "yanit": "x"}],
            [{"vaka_id": "q", "tekrar": "1", "yanit": "x"}],
            [{"vaka_id": "q", "tekrar": 0, "yanit": "x"}],
            [{"vaka_id": "q", "tekrar": True, "yanit": "x"}],
            [{"vaka_id": "q", "tekrar": 1, "yanit": None}],
        ]:
            try:
                fn(kayit)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(parmak_izi), "kanonik sıra, içerik duyarlılığı, kararlılık ve kayıt şeması korunmalı")
def m_sira(kayitlar):
    kanonik = json.dumps(kayitlar, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {"imza": hashlib.sha256(kanonik.encode()).hexdigest(), "gozlem": len(kayitlar), "kararli_vaka": 0, "kararlilik": None}
def m_sabit(kayitlar):
    return {"imza": "sabit", "gozlem": len(kayitlar), "kararli_vaka": 0, "kararlilik": 0.0}
def m_yanit(kayitlar):
    sonuc = parmak_izi(kayitlar)
    sonuc["kararli_vaka"] = len({k["vaka_id"] for k in kayitlar})
    sonuc["kararlilik"] = 1.0 if kayitlar else None
    return sonuc
for ad, mutant in [("gözlem sırasına bağımlı kalan", m_sira), ("içeriği imzalamayan", m_sabit), ("her vakayı kararlı sayan", m_yanit)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
import hashlib
import json

def parmak_izi(kayitlar):
    anahtarlar = set()
    for kayit in kayitlar:
        anahtar = (kayit["vaka_id"], kayit["tekrar"])
        if not isinstance(kayit["vaka_id"], str) or not kayit["vaka_id"]:
            raise ValueError("vaka kimliği geçersiz")
        if isinstance(kayit["tekrar"], bool) or not isinstance(kayit["tekrar"], int) or kayit["tekrar"] < 1:
            raise ValueError("tekrar pozitif tam sayı olmalı")
        if not isinstance(kayit["yanit"], str) or anahtar in anahtarlar:
            raise ValueError("yanıt veya kayıt anahtarı geçersiz")
        anahtarlar.add(anahtar)
    sirali = sorted(kayitlar, key=lambda x: (x["vaka_id"], x["tekrar"]))
    kanonik = json.dumps(sirali, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    yanitlar = {}
    for kayit in kayitlar:
        yanitlar.setdefault(kayit["vaka_id"], set()).add(kayit["yanit"])
    kararli = sum(len(cevaplar) == 1 for cevaplar in yanitlar.values())
    return {
        "imza": hashlib.sha256(kanonik.encode("utf-8")).hexdigest(),
        "gozlem": len(kayitlar),
        "kararli_vaka": kararli,
        "kararlilik": kararli / len(yanitlar) if yanitlar else None,
    }
```

```hint
Önce anahtar ve türleri doğrula. İmza için sıralı kayıtları, kararlılık için vaka kimliğinden yanıt kümesine giden ayrı bir sözlüğü kullan.
```
:::

::: anlat Benzerlik oranı kimlik kanıtı değildir
İki davranış kaydını karşılaştırırken aynı vaka ve tekrar anahtarları bulunmalıdır. Bir taraftaki ekstra veya eksik gözlemleri sessizce atmak, seçilmiş ortak alt küme üzerinden yapay olarak yüksek benzerlik üretir. Tam anahtar eşleşmesi yoksa karşılaştırma yapılmaz.

`eslesme = ayni_yanit / gozlem` yalnız ölçülen sorgu setindeki benzerliktir. Yüzde 100 eşleşme iki modelin aynı olduğunu, düşük eşleşme ise kesinlikle farklı mimariye sahip olduklarını kanıtlamaz. Farklı sorgu setleri, rastgelelik, sürüm ve sistem talimatları sonucu değiştirebilir.

**Çıktı nasıl okunur?** `veri/uc_karsilastirma.json` içinde `eksik_uc_b`, `q-sayi` gözlemleri atılmış kayıttır. Ortak anahtarlar üzerinden hesap yapan bir kod burada `1.0` eşleşme bulur. Oysa tek farklı vaka tam da atılan vakadır. Anahtar kümeleri eşit değilse karşılaştırma reddedilir.
:::

::: gorev 3 · İki gözlem setinin yanıt eşleşmesini ölç
`gozlem_karsilastir(sol, sag)` işlevini yaz. Kayıtlar `vaka_id`, `tekrar`, `yanit` alanlarını taşır. Her iki tarafta `(vaka_id, tekrar)` anahtarları benzersiz ve iki tarafın anahtar kümeleri tam eşit olmalıdır; aksi durumda `ValueError` yükselt. Yanıt string değilse de `ValueError` yükselt.

Dönüş `{"gozlem", "ayni", "eslesme", "farkli_vakalar"}` sözlüğüdür. `gozlem` ortak kayıt sayısı, `ayni` aynı yanıtı veren kayıt sayısıdır. `eslesme = ayni / gozlem`; boş sette `None` olur. `farkli_vakalar`, en az bir tekrarı farklı olan vaka kimliklerinin alfabetik listesidir. Kayıt sırası sonucu etkilememeli ve girdiler değişmemelidir.

Görünür veri: `veri/uc_karsilastirma.json`. Beklenen sonuç dosyanın `beklenen` alanındadır. Üç bozuk çift `ValueError` almalıdır.

```starter
from ai_saldiri_veri import json_yukle

def gozlem_karsilastir(sol, sag):
    # KUSURLU BAŞLANGIÇ KODU: yalnız ortak anahtarları karşılaştırıyor (eksik/fazla gözlem sessizce atılır, benzerlik yapay yükselir), yinelenen anahtarda son kaydı tutuyor, yanıt türünü denetlemiyor, boş sette 0.0 dönüyor ve farklı vakaları sıralamıyor!
    a = {(k["vaka_id"], k["tekrar"]): k["yanit"] for k in sol}
    b = {(k["vaka_id"], k["tekrar"]): k["yanit"] for k in sag}
    ortak = [x for x in a if x in b]
    ayni = 0
    farkli = []
    for x in ortak:
        if a[x] == b[x]:
            ayni += 1
        elif x[0] not in farkli:
            farkli.append(x[0])
    return {"gozlem": len(ortak), "ayni": ayni, "eslesme": ayni / len(ortak) if ortak else 0.0, "farkli_vakalar": farkli}

veri = json_yukle("veri/uc_karsilastirma.json")
sonuc = gozlem_karsilastir(veri["uc_a"], veri["uc_b"])
print("sonuç   :", sonuc)
print("beklenen:", veri["beklenen"])
for cift in veri["bozuk_ciftler"]:
    try:
        print("KABUL edildi (yanlış):", gozlem_karsilastir(cift["sol"], cift["sag"]))
    except ValueError as hata:
        print("reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-07")
```

```test
import copy
SOL = [
    {"vaka_id": "q1", "tekrar": 1, "yanit": "EVET"},
    {"vaka_id": "q1", "tekrar": 2, "yanit": "EVET"},
    {"vaka_id": "q2", "tekrar": 1, "yanit": "HAYIR"},
]
SAG = [
    {"vaka_id": "q2", "tekrar": 1, "yanit": "EVET"},
    {"vaka_id": "q1", "tekrar": 2, "yanit": "EVET"},
    {"vaka_id": "q1", "tekrar": 1, "yanit": "HAYIR"},
]
BEKLENEN = {"gozlem": 3, "ayni": 1, "eslesme": 1 / 3, "farkli_vakalar": ["q1", "q2"]}
def sozlesme(fn):
    try:
        a, b = copy.deepcopy(SOL), copy.deepcopy(SAG)
        if fn(a, b) != BEKLENEN or a != SOL or b != SAG or fn(list(reversed(SOL)), SAG) != BEKLENEN:
            return False
        if fn([], []) != {"gozlem": 0, "ayni": 0, "eslesme": None, "farkli_vakalar": []}:
            return False
        if fn(SOL, copy.deepcopy(SOL)) != {"gozlem": 3, "ayni": 3, "eslesme": 1.0, "farkli_vakalar": []}:
            return False
        for a, b in [
            (SOL, SAG[:-1]),
            (SOL, SAG[:-1] + [{"vaka_id": "q9", "tekrar": 1, "yanit": "x"}]),
            (SOL[:-1] + [SOL[0]], SAG),
            ([SOL[0], dict(SOL[0], yanit="X"), SOL[1], SOL[2]], SAG),
            (SOL, [SAG[0], dict(SAG[0], yanit="X"), SAG[1], SAG[2]]),
            ([{"vaka_id": "q", "tekrar": 1, "yanit": None}], [{"vaka_id": "q", "tekrar": 1, "yanit": "x"}]),
        ]:
            try:
                fn(a, b)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(gozlem_karsilastir), "tam anahtar eşleşmesi, sıradan bağımsızlık ve fark listesi korunmalı")
def m_kesisim(sol, sag):
    a = {(k["vaka_id"], k["tekrar"]): k["yanit"] for k in sol}
    b = {(k["vaka_id"], k["tekrar"]): k["yanit"] for k in sag}
    ortak = set(a) & set(b)
    ayni = sum(a[k] == b[k] for k in ortak)
    return {"gozlem": len(ortak), "ayni": ayni, "eslesme": ayni / len(ortak) if ortak else None, "farkli_vakalar": []}
def m_toplam(sol, sag):
    sonuc = gozlem_karsilastir(sol, sag)
    sonuc["ayni"] = sonuc["gozlem"]
    sonuc["eslesme"] = 1.0 if sonuc["gozlem"] else None
    return sonuc
def m_fark(sol, sag):
    sonuc = gozlem_karsilastir(sol, sag)
    sonuc["farkli_vakalar"] = []
    return sonuc
for ad, mutant in [("yalnız ortak alt kümeyi ölçen", m_kesisim), ("her yanıtı aynı sayan", m_toplam), ("farklı vakaları gizleyen", m_fark)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def gozlem_karsilastir(sol, sag):
    def indeksle(kayitlar):
        indeks = {}
        for kayit in kayitlar:
            anahtar = (kayit["vaka_id"], kayit["tekrar"])
            if anahtar in indeks or not isinstance(kayit["yanit"], str):
                raise ValueError("yinelenen anahtar veya geçersiz yanıt")
            indeks[anahtar] = kayit["yanit"]
        return indeks
    a = indeksle(sol)
    b = indeksle(sag)
    if set(a) != set(b):
        raise ValueError("gözlem anahtarları eşleşmiyor")
    farkli = {anahtar[0] for anahtar in a if a[anahtar] != b[anahtar]}
    ayni = sum(a[anahtar] == b[anahtar] for anahtar in a)
    return {
        "gozlem": len(a),
        "ayni": ayni,
        "eslesme": ayni / len(a) if a else None,
        "farkli_vakalar": sorted(farkli),
    }
```

```hint
Her iki tarafı anahtardan yanıta giden sözlüğe çevir. Önce anahtar kümelerini karşılaştır, sonra tek geçişte hem aynı yanıtları hem farklı vaka kümesini çıkar.
```
:::

::: anlat Gerçek davranış gözlemi, görünür örnek dosya ve karşılaştırma
Bu adımda üç görevi birleştiriyoruz ve iki veri kaynağını açıkça ayırıyoruz:

- **Sentetik örnek / fixture (`ornek_gozlem.jsonl`):** Proje içindeki `tracks/ai-saldiri/veri/ai-saldiri-07-ornek-gozlem.jsonl` dosyası her çalıştırmada geçici çalışma klasörüne `ornek_gozlem.jsonl` adıyla kopyalanır. Canlı sunucu yanıtı değildir; kanonik sıralama ve kararlılık hesabını satır bazında incelemek ve çalışma kopyasını kod içinde değiştirerek denemek içindir. Koşucu her çalıştırmada temiz bir geçici çalışma dizini açtığından, çalışma içindeki dosya değişiklikleri o koşu boyunca korunur; sonraki çalıştırmada temiz başlangıç kopyasına dönülür.
- **Canlı gerçek deney (`motor: ai-gercek`):** Görev çalışırken kendine ait özel CPU Ollama sunucusunda iki farklı profille (`T=0.0` kısa sınıflandırıcı ve `T=0.6` açıklamalı yanıt, 2 sorgu × 2 tekrar = 8 gerçek çağrı) yerel modele gerçek sorgular gönderilir. Kullanıcının veya başka bir ajanın Ollama oturumuna dokunulmaz; deney sonunda yalnız kendi başlattığı süreç kapatılır.

```setup
from pathlib import Path
Path("ornek_gozlem.jsonl").write_text(
    '{"vaka_id":"q1","tekrar":1,"metin":"Sınıfla (EVET/HAYIR): Bu parselde iki mavi klasör var mı?","yanit":"EVET","etiket":"sentetik-fixture"}\n'
    '{"vaka_id":"q1","tekrar":2,"metin":"Sınıfla (EVET/HAYIR): Bu parselde iki mavi klasör var mı?","yanit":"EVET","etiket":"sentetik-fixture"}\n'
    '{"vaka_id":"q2","tekrar":1,"metin":"Sınıfla (EVET/HAYIR): Kayıt numarası 42 tek sayı mı?","yanit":"HAYIR","etiket":"sentetik-fixture"}\n'
    '{"vaka_id":"q2","tekrar":2,"metin":"Sınıfla (EVET/HAYIR): Kayıt numarası 42 tek sayı mı?","yanit":"EVET","etiket":"sentetik-fixture"}\n',
    encoding="utf-8",
)
```

```python
import hashlib
import json
from pathlib import Path

yol = Path("ornek_gozlem.jsonl")
satirlar = [json.loads(s) for s in yol.read_text(encoding="utf-8").splitlines() if s.strip()]
print("Dosya:", yol.name, "satır:", len(satirlar), "etiket:", satirlar[0]["etiket"])
temiz = sorted(
    [{k: s[k] for k in ("vaka_id", "tekrar", "yanit")} for s in satirlar],
    key=lambda x: (x["vaka_id"], x["tekrar"]),
)
kanonik = json.dumps(temiz, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
print("Kanonik imza[:12]:", hashlib.sha256(kanonik.encode("utf-8")).hexdigest()[:12])
```

Aynı model iki farklı sıcaklık ve sistem talimatı altında farklı yanıtlar ve farklı parmak izi üretebilir; bu fark model ağırlıklarının değiştiğini göstermediği gibi, yüksek eşleşme de iki uç noktanın aynı ağırlıklara sahip olduğunu kanıtlamaz.
:::

::: gorev Gerçek deney · Yerel modelde tekrarlı davranış gözlemi, parmak izi ve karşılaştırma
Önceki üç görevdeki `sorgu_matrisi(sorgular, model_cagir)`, `parmak_izi(kayitlar)` ve `gozlem_karsilastir(sol, sag)` işlevlerini burada birleştir. Sözleşmeleri aynıdır:

- `sorgu_matrisi`: çağrıdan önce tüm sorguları doğrular (`id` boş olmayan benzersiz string, `metin` string, `tekrar` bool olmayan `1..4` tam sayı), adaptör hatasını yutmaz, girdiyi değiştirmez.
- `parmak_izi`: `(vaka_id, tekrar)` benzersizliğini ve türleri doğrular, kanonik JSON (`ensure_ascii=False`, `sort_keys=True`, `separators=(",", ":")`) üzerinden SHA-256 `imza`, `gozlem`, `kararli_vaka` ve `kararlilik` döndürür.
- `gozlem_karsilastir`: iki gözlem setinin `(vaka_id, tekrar)` anahtar kümelerinin tam eşitliğini doğrular; `gozlem`, `ayni`, `eslesme` ve alfabetik `farkli_vakalar` döndürür.

Çalışma klasöründeki `ornek_gozlem.jsonl` (**sentetik örnek / fixture**) dosyasını kod içinde okuyup değiştirebilirsin; değerlendirme bu dosyadan bağımsız gizli testlerle ve **canlı gerçek deney** (8 yerel Ollama çağrısı) ile yapılır. Belirli bir kararlılık veya eşleşme oranı geçme şartı değildir; tüm gerçek çağrıların tamamlanması ve ölçümlerin bağımsız hesapla birebir örtüşmesi gerekir.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```setup
from sandbox import ai_gercek_ai_saldiri_07 as _d07
_d07.ornek_dosya_hazirla("ornek_gozlem.jsonl")
```

```starter
import hashlib
import json
import ai_lab

def sorgu_matrisi(sorgular, model_cagir):
    # KUSURLU BAŞLANGIÇ KODU: doğrulamayı çağrılarla iç içe yapıyor (geçersiz sorgudan önceki sorgular modeli çağırır), tekrarı 0'dan sayıyor, int() ile bool/float tekrarı kabul ediyor, 1..4 sınırını ve yinelenen kimliği denetlemiyor ve adaptör hatasını "HATA" yanıtına çeviriyor!
    kayitlar = []
    for sorgu in sorgular:
        if not sorgu["id"]:
            raise ValueError("sorgu kimliği boş")
        for tekrar in range(int(sorgu["tekrar"])):
            try:
                yanit = model_cagir(sorgu["metin"])
            except Exception:
                yanit = "HATA"
            kayitlar.append({"vaka_id": sorgu["id"], "tekrar": tekrar, "metin": sorgu["metin"], "yanit": yanit})
    return kayitlar

def parmak_izi(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: kayıtları sıralamadan ve ensure_ascii=True ile özetliyor (kayıt sırası imzayı değiştirir), yanıtları strip() ile "düzeltiyor", kararlılığı vaka yerine kayıt sayısına bölüyor, boş sette 0.0 dönüyor ve yinelenen anahtarı denetlemiyor!
    temiz = [dict(k, yanit=str(k["yanit"]).strip()) for k in kayitlar]
    kanonik = json.dumps(temiz, sort_keys=True)
    yanitlar = {}
    for k in temiz:
        yanitlar.setdefault(k["vaka_id"], set()).add(k["yanit"])
    kararli = sum(len(v) == 1 for v in yanitlar.values())
    return {
        "imza": hashlib.sha256(kanonik.encode("utf-8")).hexdigest(),
        "gozlem": len(kayitlar),
        "kararli_vaka": kararli,
        "kararlilik": kararli / len(kayitlar) if kayitlar else 0.0,
    }

def gozlem_karsilastir(sol, sag):
    # KUSURLU BAŞLANGIÇ KODU: yalnız ortak anahtarları karşılaştırıyor (eksik/fazla gözlem sessizce atılır, benzerlik yapay yükselir), yinelenen anahtarda son kaydı tutuyor, yanıt türünü denetlemiyor, boş sette 0.0 dönüyor ve farklı vakaları sıralamıyor!
    a = {(k["vaka_id"], k["tekrar"]): k["yanit"] for k in sol}
    b = {(k["vaka_id"], k["tekrar"]): k["yanit"] for k in sag}
    ortak = [x for x in a if x in b]
    ayni = 0
    farkli = []
    for x in ortak:
        if a[x] == b[x]:
            ayni += 1
        elif x[0] not in farkli:
            farkli.append(x[0])
    return {"gozlem": len(ortak), "ayni": ayni, "eslesme": ayni / len(ortak) if ortak else 0.0, "farkli_vakalar": farkli}


if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_07 as deney
    deney.goster(sorgu_matrisi, parmak_izi, gozlem_karsilastir)
```

```test
import ai_lab
import copy
import hashlib
import json
from pathlib import Path
import secrets

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for ad in ("sorgu_matrisi", "parmak_izi", "gozlem_karsilastir"):
    need(ad)

import ast
_yasak = ("matris_referans", "parmak_izi_referans", "karsilastir_referans", "kanit_yaz")
_sorun = list(ai_lab.kod_denetimi(src, _yasak))
for _n in ast.walk(ast.parse(src)):
    if isinstance(_n, ast.ImportFrom) and any(a.name in _yasak or a.name == "*" for a in _n.names): _sorun.append("referans importu yasak")
    if isinstance(_n, (ast.Import, ast.ImportFrom)) and any(x and x.split(".")[0] in ("inspect", "importlib", "runpy") for x in [a.name for a in _n.names] + ([_n.module] if isinstance(_n, ast.ImportFrom) else [])): _sorun.append("kaynak okuma/dinamik import yasak")
    if isinstance(_n, ast.Name) and _n.id in ("exec", "eval", "compile", "__builtins__"): _sorun.append("dinamik kod çalıştırma yasak: " + _n.id)
if not ok(not _sorun, "laboratuvar yamalanmamalı, test referansları çağrılmamalı: " + "; ".join(sorted(set(_sorun)))):
    stop()

ornek_yol = Path("ornek_gozlem.jsonl")
ok(ornek_yol.is_file() and "sentetik-fixture" in ornek_yol.read_text(encoding="utf-8"), "görünür sentetik çalışma dosyası (ornek_gozlem.jsonl) çalışma klasöründe erişilebilir olmalı")

SORGULAR = [{"id": "q1", "metin": "Sınıfla: A", "tekrar": 2}, {"id": "q2", "metin": "Sınıfla: B", "tekrar": 1}]
def sozlesme_matris(fn):
    try:
        cagrilar = []
        def model(metin):
            cagrilar.append(metin)
            return "EVET" if metin.endswith("A") else "HAYIR"
        once = copy.deepcopy(SORGULAR)
        sonuc = fn(SORGULAR, model)
        beklenen = [
            {"vaka_id": "q1", "tekrar": 1, "metin": "Sınıfla: A", "yanit": "EVET"},
            {"vaka_id": "q1", "tekrar": 2, "metin": "Sınıfla: A", "yanit": "EVET"},
            {"vaka_id": "q2", "tekrar": 1, "metin": "Sınıfla: B", "yanit": "HAYIR"},
        ]
        if sonuc != beklenen or cagrilar != ["Sınıfla: A", "Sınıfla: A", "Sınıfla: B"] or SORGULAR != once:
            return False
        if fn([], model) != [] or len(fn([{"id": "q", "metin": "x", "tekrar": 4}], model)) != 4:
            return False
        for sorgu in [
            [{"id": "", "metin": "x", "tekrar": 1}],
            [{"id": 123, "metin": "x", "tekrar": 1}],
            [{"id": "q", "metin": "x", "tekrar": 2.0}],
            [{"id": "q", "metin": "x", "tekrar": "1"}],
            [{"id": "q", "metin": "x", "tekrar": 0}],
            [{"id": "q", "metin": "x", "tekrar": 5}],
            [{"id": "q", "metin": "x", "tekrar": True}],
            [{"id": "q", "metin": 3, "tekrar": 1}],
            [{"id": "q", "metin": "x", "tekrar": 1}, {"id": "q", "metin": "y", "tekrar": 1}],
        ]:
            sayi = [0]
            def yasak(metin):
                sayi[0] += 1
                return "x"
            try:
                fn(sorgu, yasak)
                return False
            except ValueError:
                if sayi[0] != 0:
                    return False
        try:
            fn([{"id": "q", "metin": "x", "tekrar": 1}], lambda _: (_ for _ in ()).throw(RuntimeError("kesinti")))
            return False
        except RuntimeError:
            pass
        return True
    except Exception:
        return False

ok(sozlesme_matris(sorgu_matrisi), "sorgu_matrisi: sıra, tekrar, adaptör hatası ve çağrıdan önce doğrulama korunmalı")
def m_tekrar(sorgular, model_cagir):
    return [{"vaka_id": s["id"], "tekrar": t, "metin": s["metin"], "yanit": model_cagir(s["metin"])} for s in sorgular for t in range(s["tekrar"])]
def m_once_cagir(sorgular, model_cagir):
    return [{"vaka_id": s["id"], "tekrar": t, "metin": s["metin"], "yanit": model_cagir(s["metin"])} for s in sorgular for t in range(1, s["tekrar"] + 1)]
def m_hata_yutan(sorgular, model_cagir):
    try:
        return sorgu_matrisi(sorgular, model_cagir)
    except RuntimeError:
        return []
for ad, mutant in [("tekrarı sıfırdan başlatan", m_tekrar), ("seti doğrulamadan çağıran", m_once_cagir), ("adaptör hatasını yutan", m_hata_yutan)]:
    ok(not sozlesme_matris(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

KAYITLAR = [
    {"vaka_id": "q2", "tekrar": 1, "yanit": "HAYIR"},
    {"vaka_id": "q1", "tekrar": 2, "yanit": "HAYIR"},
    {"vaka_id": "q1", "tekrar": 1, "yanit": "EVET"},
    {"vaka_id": "q2", "tekrar": 2, "yanit": "HAYIR"},
]
def sozlesme_iz(fn):
    try:
        once = copy.deepcopy(KAYITLAR)
        sonuc = fn(KAYITLAR)
        sirali = sorted(KAYITLAR, key=lambda x: (x["vaka_id"], x["tekrar"]))
        kanonik = json.dumps(sirali, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if sonuc != {"imza": hashlib.sha256(kanonik.encode()).hexdigest(), "gozlem": 4, "kararli_vaka": 1, "kararlilik": 0.5} or KAYITLAR != once:
            return False
        if fn(list(reversed(KAYITLAR))) != sonuc:
            return False
        degisen = copy.deepcopy(KAYITLAR)
        degisen[1]["yanit"] = "EVET"
        if fn(degisen)["imza"] == sonuc["imza"] or fn(degisen)["kararli_vaka"] != 2:
            return False
        tr_k = [{"vaka_id": "q1", "tekrar": 1, "yanit": "Özet"}]
        if fn(tr_k)["imza"] != hashlib.sha256(json.dumps([{"tekrar": 1, "vaka_id": "q1", "yanit": "Özet"}], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest():
            return False
        bos = fn([])
        if bos["gozlem"] != 0 or bos["kararlilik"] is not None or bos["imza"] != hashlib.sha256(b"[]").hexdigest():
            return False
        for kayit in [
            [{"vaka_id": "q", "tekrar": 1, "yanit": "x"}, {"vaka_id": "q", "tekrar": 1, "yanit": "y"}],
            [{"vaka_id": "", "tekrar": 1, "yanit": "x"}],
            [{"vaka_id": 123, "tekrar": 1, "yanit": "x"}],
            [{"vaka_id": "q", "tekrar": 1.5, "yanit": "x"}],
            [{"vaka_id": "q", "tekrar": "1", "yanit": "x"}],
            [{"vaka_id": "q", "tekrar": 0, "yanit": "x"}],
            [{"vaka_id": "q", "tekrar": True, "yanit": "x"}],
            [{"vaka_id": "q", "tekrar": 1, "yanit": None}],
        ]:
            try:
                fn(kayit)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme_iz(parmak_izi), "parmak_izi: kanonik sıra, içerik duyarlılığı, kararlılık ve kayıt şeması korunmalı")
def m_sira(kayitlar):
    kanonik = json.dumps(kayitlar, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {"imza": hashlib.sha256(kanonik.encode()).hexdigest(), "gozlem": len(kayitlar), "kararli_vaka": 0, "kararlilik": None}
def m_sabit(kayitlar):
    return {"imza": "sabit", "gozlem": len(kayitlar), "kararli_vaka": 0, "kararlilik": 0.0}
def m_yanit(kayitlar):
    sonuc = parmak_izi(kayitlar)
    sonuc["kararli_vaka"] = len({k["vaka_id"] for k in kayitlar})
    sonuc["kararlilik"] = 1.0 if kayitlar else None
    return sonuc
for ad, mutant in [("gözlem sırasına bağımlı kalan", m_sira), ("içeriği imzalamayan", m_sabit), ("her vakayı kararlı sayan", m_yanit)]:
    ok(not sozlesme_iz(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

SOL = [
    {"vaka_id": "q1", "tekrar": 1, "yanit": "EVET"},
    {"vaka_id": "q1", "tekrar": 2, "yanit": "EVET"},
    {"vaka_id": "q2", "tekrar": 1, "yanit": "HAYIR"},
]
SAG = [
    {"vaka_id": "q2", "tekrar": 1, "yanit": "EVET"},
    {"vaka_id": "q1", "tekrar": 2, "yanit": "EVET"},
    {"vaka_id": "q1", "tekrar": 1, "yanit": "HAYIR"},
]
BEKLENEN_KARS = {"gozlem": 3, "ayni": 1, "eslesme": 1 / 3, "farkli_vakalar": ["q1", "q2"]}
def sozlesme_kars(fn):
    try:
        a, b = copy.deepcopy(SOL), copy.deepcopy(SAG)
        if fn(a, b) != BEKLENEN_KARS or a != SOL or b != SAG or fn(list(reversed(SOL)), SAG) != BEKLENEN_KARS:
            return False
        if fn([], []) != {"gozlem": 0, "ayni": 0, "eslesme": None, "farkli_vakalar": []}:
            return False
        if fn(SOL, copy.deepcopy(SOL)) != {"gozlem": 3, "ayni": 3, "eslesme": 1.0, "farkli_vakalar": []}:
            return False
        for a, b in [
            (SOL, SAG[:-1]),
            (SOL, SAG[:-1] + [{"vaka_id": "q9", "tekrar": 1, "yanit": "x"}]),
            (SOL[:-1] + [SOL[0]], SAG),
            ([SOL[0], dict(SOL[0], yanit="X"), SOL[1], SOL[2]], SAG),
            (SOL, [SAG[0], dict(SAG[0], yanit="X"), SAG[1], SAG[2]]),
            ([{"vaka_id": "q", "tekrar": 1, "yanit": None}], [{"vaka_id": "q", "tekrar": 1, "yanit": "x"}]),
        ]:
            try:
                fn(a, b)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme_kars(gozlem_karsilastir), "gozlem_karsilastir: tam anahtar eşleşmesi, sıradan bağımsızlık ve fark listesi korunmalı")
def m_kesisim(sol, sag):
    a = {(k["vaka_id"], k["tekrar"]): k["yanit"] for k in sol}
    b = {(k["vaka_id"], k["tekrar"]): k["yanit"] for k in sag}
    ortak = set(a) & set(b)
    ayni = sum(a[k] == b[k] for k in ortak)
    return {"gozlem": len(ortak), "ayni": ayni, "eslesme": ayni / len(ortak) if ortak else None, "farkli_vakalar": []}
def m_toplam(sol, sag):
    sonuc = gozlem_karsilastir(sol, sag)
    sonuc["ayni"] = sonuc["gozlem"]
    sonuc["eslesme"] = 1.0 if sonuc["gozlem"] else None
    return sonuc
def m_fark(sol, sag):
    sonuc = gozlem_karsilastir(sol, sag)
    sonuc["farkli_vakalar"] = []
    return sonuc
for ad, mutant in [("yalnız ortak alt kümeyi ölçen", m_kesisim), ("her yanıtı aynı sayan", m_toplam), ("farklı vakaları gizleyen", m_fark)]:
    ok(not sozlesme_kars(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

from sandbox import ai_gercek_ai_saldiri_07 as D
rastgele_etiket = " ETIKET-" + secrets.token_hex(4)
ornek_yol.write_text(ornek_yol.read_text(encoding="utf-8") + "\n", encoding="utf-8")
for _ in range(3):
    tok_a = "YANIT-" + secrets.token_hex(4)
    tok_b = "YANIT-" + secrets.token_hex(4)
    gizli_sol = [
        {"vaka_id": "r2", "tekrar": 1, "yanit": tok_a},
        {"vaka_id": "r1", "tekrar": 2, "yanit": tok_b},
        {"vaka_id": "r1", "tekrar": 1, "yanit": tok_a},
    ]
    gizli_sag = [
        {"vaka_id": "r1", "tekrar": 1, "yanit": tok_a},
        {"vaka_id": "r1", "tekrar": 2, "yanit": tok_a},
        {"vaka_id": "r2", "tekrar": 1, "yanit": tok_b + rastgele_etiket},
    ]
    ok(
        parmak_izi(gizli_sol) == D.parmak_izi_referans(gizli_sol)
        and gozlem_karsilastir(gizli_sol, gizli_sag) == D.karsilastir_referans(gizli_sol, gizli_sag),
        "görünür örnek dosyadan bağımsız rastgele gizli veride parmak izi ve karşılaştırma referansla aynı",
    )

if not all(checks):
    stop()

try:
    r = D.deney(sorgu_matrisi, parmak_izi, gozlem_karsilastir)
except Exception as e:
    ok(False, f"GERÇEK DAVRANIŞ GÖZLEMİ DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

for ad, deger in r["kontroller"].items():
    ok(deger, "gerçek deney: " + ad)
ok(r["hata_sayisi"] == 0, "sekiz gerçek model çağrısı eksiksiz ve hatasız tamamlandı")
ai_lab.kanit_yaz("saldiri-07-parmak-izi", {"kaynak": "gercek", "kabul": all(checks), "ortam": r["ortam"], "deney": r, "ozet": r["ozet"]})
o = r["ozet"]
ok(
    True,
    f"BULGU ({r['ortam']['model']['ad']}): 8 gerçek çağrı; sol kararlılık {o['sol_parmak_izi']['kararlilik']}, "
    f"sağ kararlılık {o['sag_parmak_izi']['kararlilik']}, iki profil eşleşmesi {o['karsilastirma']['eslesme']}. "
    "Eşleşme oranı geçme şartı değildir.",
)
```

```solution
import ai_lab
import hashlib
import json

def sorgu_matrisi(sorgular, model_cagir):
    kimlikler = set()
    for sorgu in sorgular:
        tekrar = sorgu["tekrar"]
        if not isinstance(sorgu["id"], str) or not sorgu["id"] or sorgu["id"] in kimlikler:
            raise ValueError("sorgu kimliği boş veya yinelenen")
        if not isinstance(sorgu["metin"], str):
            raise ValueError("sorgu metni string olmalı")
        if isinstance(tekrar, bool) or not isinstance(tekrar, int) or not 1 <= tekrar <= 4:
            raise ValueError("tekrar 1..4 olmalı")
        kimlikler.add(sorgu["id"])
    return [
        {"vaka_id": sorgu["id"], "tekrar": tekrar, "metin": sorgu["metin"], "yanit": model_cagir(sorgu["metin"])}
        for sorgu in sorgular
        for tekrar in range(1, sorgu["tekrar"] + 1)
    ]

def parmak_izi(kayitlar):
    anahtarlar = set()
    for kayit in kayitlar:
        anahtar = (kayit["vaka_id"], kayit["tekrar"])
        if not isinstance(kayit["vaka_id"], str) or not kayit["vaka_id"]:
            raise ValueError("vaka kimliği geçersiz")
        if isinstance(kayit["tekrar"], bool) or not isinstance(kayit["tekrar"], int) or kayit["tekrar"] < 1:
            raise ValueError("tekrar pozitif tam sayı olmalı")
        if not isinstance(kayit["yanit"], str) or anahtar in anahtarlar:
            raise ValueError("yanıt veya kayıt anahtarı geçersiz")
        anahtarlar.add(anahtar)
    sirali = sorted(kayitlar, key=lambda x: (x["vaka_id"], x["tekrar"]))
    kanonik = json.dumps(sirali, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    yanitlar = {}
    for kayit in kayitlar:
        yanitlar.setdefault(kayit["vaka_id"], set()).add(kayit["yanit"])
    kararli = sum(len(cevaplar) == 1 for cevaplar in yanitlar.values())
    return {
        "imza": hashlib.sha256(kanonik.encode("utf-8")).hexdigest(),
        "gozlem": len(kayitlar),
        "kararli_vaka": kararli,
        "kararlilik": kararli / len(yanitlar) if yanitlar else None,
    }

def gozlem_karsilastir(sol, sag):
    def indeksle(kayitlar):
        indeks = {}
        for kayit in kayitlar:
            anahtar = (kayit["vaka_id"], kayit["tekrar"])
            if anahtar in indeks or not isinstance(kayit["yanit"], str):
                raise ValueError("yinelenen anahtar veya geçersiz yanıt")
            indeks[anahtar] = kayit["yanit"]
        return indeks
    a = indeksle(sol)
    b = indeksle(sag)
    if set(a) != set(b):
        raise ValueError("gözlem anahtarları eşleşmiyor")
    farkli = {anahtar[0] for anahtar in a if a[anahtar] != b[anahtar]}
    ayni = sum(a[anahtar] == b[anahtar] for anahtar in a)
    return {
        "gozlem": len(a),
        "ayni": ayni,
        "eslesme": ayni / len(a) if a else None,
        "farkli_vakalar": sorted(farkli),
    }

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_07 as deney
    deney.goster(sorgu_matrisi, parmak_izi, gozlem_karsilastir)
```

```hint
Önceki üç görevdeki doğrulama ve kanonik JSON kurallarını aynen koru; gerçek deneyde model_cagir adaptörü yerel Ollama modeline bağlanır ve iki farklı sıcaklık/talimat profilinin gözlem matrislerini karşılaştırır.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Davranış parmak izi model kimliğini ispatlamaz

Aynı istemi tekrarlayıp yanıtları kanonik biçimde karşılaştırmak gözlenen davranışın kararlılığını ölçer. Sampling, sürüm, chat template ve sistem talimatı aynı modelin çıktısını değiştirebilir. İki gözlem setinin eşleşmesi ortak ağırlık dosyası kullandıklarını kanıtlamaz; yalnız seçilen sorularda benzer yanıt verdiklerini gösterir.

| Yaygın yanlış | Doğru sınır |
|---|---|
| Hash eşitse model kesin aynıdır | Hashin kapsadığı şey sınırlı yanıt kümesidir. |

Sonraki bağlantı: ai-guvence-01. [Birincil kaynak](https://docs.ollama.com/api/chat). Kaynak mekanizmanın ilgili API veya yöntemini açıklar; bu labın başarı oranının kanıtı yerel ham koşudur.
:::
