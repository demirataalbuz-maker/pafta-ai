---
id: ai-savunma-15
title: Secrets Yalıtımı ve Aracılı Kimlik Bilgileri
summary: Metindeki sırları maskele, kısa ömürlü ve dar kapsamlı kimlik bilgisini doğrula, gerçek sırrı göstermeden broker kullanım kararı üret.
timeout: 45
esleme: ai-saldiri-06, ai-ile-guvenlik-05
---

::: anlat Gerçek sır model bağlamına girmez

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| HashiCorp Vault, AWS STS ya da GCP Workload Identity kısa ömürlü, dar kapsamlı kimlik bilgisi üretir. Bir broker (ör. FastAPI üzerinde) bu bilgiyi araç çağrısına modelin göremeyeceği bir kanaldan ekler. Gitleaks/TruffleHog ve log redaksiyon katmanları sızan değeri arar. | Görev 1–3: `veri/log_kayitlari.json`, `veri/kapsamlar.json` ve `veri/broker_istekleri.json` içindeki **sentetik** log satırları, kapsamlar ve broker istekleri; zamanlar milisaniye ölçeğindedir. Son adım: kurulu yerel Ollama modelinin ürettiği iki metin ve sandbox'ın her çalıştırmada yeni ürettiği sentetik `sk-test-...` sırrıyla maskeleme. | Gerçek bir sır deposu, imza ya da token iptali sınanmaz. Birebir dize maskelemesi bölünmüş, kodlanmış ya da harf büyüklüğü değişmiş sırrı yakalamaz. İki senaryo bir oran vermez. |

> [!NOT]
> Görev 1–3 sentetik veriyle çalışır. Bu görevlerde model, ağ ve sır deposu yoktur. Son adımdaki **Gerçek deney** görevi yalnız kurulu yerel Ollama modelini ve sandbox'ın ürettiği yapay bir sırrı kullanır. `veri/` dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalanır; kopyada yaptığın değişiklik bir sonraki çalıştırmada sıfırlanır, **kalıcılık yoktur**. Kontrol bu dosyalardan ayrı, gizli verilerle sınar.

API anahtarı model istemine, araç çıktısına veya günlüğe açık metin olarak eklenmez. HashiCorp Vault gibi bir sır deposu ile FastAPI üzerindeki broker, kısa ömürlü ve yalnız belirli araç-eylem-kaynak kapsamında kimlik bilgisi üretebilir. Model yalnız opak bir referans veya kullanım kararı görür.

Bu dersteki bütün sır değerleri yapaydır: görev 1–3'te fixture verisi, son adımda sandbox'ın her çalıştırmada ürettiği sentetik bir token. Son adımın metinleri ise gerçek yerel modelden gelir. Maskeleme, günlükte yanlışlıkla görünen değeri temizlemek içindir; sırları modele göndermeyi güvenli hale getirme yöntemi değildir. Temel savunma, gerçek sırrı bağlama hiç eklememektir.

**Saldırgan ne dener?** Prompt injection'ın en değerli hedeflerinden biri, ajanın kullandığı API anahtarıdır. Sır sistem istemine, araç çıktısına ya da hata mesajına bir kez girerse saldırgan modele şunları yaptırmaya çalışır:

- Sırrı tekrar etmek.
- Harf harf yazmak ya da base64 ile kodlamak.
- Bir URL parametresine eklemek (`?k=...`).

Kimlik bilgisi uzun ömürlü ve geniş kapsamlıysa sızan tek bir değer her şeye erişim verir. Kısa ömürlü olsa bile, broker kanalı dışından "doğrudan" kullanılabiliyorsa ya da aynı belirteç tekrar kabul ediliyorsa saldırgan onu yeniden oynatır.

**Savunma neden kırılır?**
- Maskeleme yalnız bildiği biçimi yakalar. Bölünmüş, büyük harfe çevrilmiş ya da kodlanmış bir sır günlüğe olduğu gibi düşer.
- Birbirinin öneki olan sırlarda kısa olanı önce maskelemek uzun sırrın kuyruğunu açıkta bırakır.
- Kapsamda birim karışıklığı (300 ms yerine 300 saniye) belirtecin ömrünü bin kat uzatır.
- Broker kararında ham anahtarı döndürmek bütün mimariyi boşa çıkarır; model yalnız opak bir referans görmelidir.

**Görev 1'de sık tuzaklar:** Sırları verildiği sırayla maskelemek, `onek-cakisma` kaydında `[GIZLI]CD34` kuyruğu bırakır (`veri/log_kayitlari.json`). Bulguyu sır türü sayısı olarak tutmak, aynı token iki satırda geçse de 1 yazar (`http-log`). `bolunmus` ve `buyuk-harf` kayıtları doğru çözümde de maskelenmez; bu kaçınılmaz sınırı raporda gizlemek yerine bilmek gerekir.
:::

::: anlat Çakışan değerlerde en uzun sır önce maskelenir
Bir sır diğerinin başlangıcıysa kısa olanı önce değiştirmek uzun değerin bir bölümünü açıkta bırakabilir. Bu nedenle maskeler uzunluk sırasıyla, en uzun değerden başlanır. Bulunan sayısı her gerçek metin eşleşmesini sayar; aynı sır iki kez geçiyorsa iki bulgu üretir.
:::

::: tahmin Maskeleme sırasını tahmin et
Üç çıktı satırını yaz:

```python
sirlar = sorted(["abc123", "abc12345"], key=len, reverse=True)
metin = "abc12345 ve abc12345"
for sir in sirlar:
    metin = metin.replace(sir, "[GIZLI]")
print(metin)
print(metin.count("[GIZLI]"))
print("abc12345" in metin)
```

???

```cikti
[GIZLI] ve [GIZLI]
2
False
```

Uzun değer önce maskelendiği için kısa değer yalnız bağımsız eşleşmeleri etkiler; açık sır kalmaz.
:::

::: gorev 1 · Metindeki yapay sırları maskele
`sir_maskele(kayitlar)` işlevini yaz. Kayıtlar liste; her kayıt tam olarak `id`, `metin`, `gizliler` alanlarını taşısın. Kimlik 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren benzersiz stringdir. Metin string, gizliler liste olmalıdır.

Her gizli değer 4–128 karakterlik, yinelenmeyen ve satır sonu/NUL içermeyen stringdir. Geçersiz veride `ValueError` yükselt. Her kayıtta gizli değerleri uzunluğa göre azalan sırayla bütün eşleşmelerde `[GIZLI]` ile değiştir. Bulgu sayısı yapılan değişiklik değil, maskelenen eşleşme sayısıdır.

Her kayıt için `{"id":ID,"maskeli_metin":METIN,"bulgu":SAYI}` döndür. Kimliğe göre sırala, boş kayıtta boş liste döndür ve girdileri değiştirme.

Görünür veri: `veri/log_kayitlari.json`. Dosyada altı kayıt, beklenen rapor ve dört bozuk girdi vardır.

```starter
from ai_savunma_veri import json_yukle

def sir_maskele(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: sırları verildiği sırayla maskeliyor (kısa önek sır önce değişirse uzun sırrın kuyruğu açıkta kalır), bulguyu eşleşme sayısı yerine "bulunan sır türü" olarak sayıyor, gizli değerlerin uzunluğunu ve kontrol karakterlerini doğrulamıyor ve raporu sıralamıyor!
    rapor = []
    for kayit in kayitlar:
        metin = kayit["metin"]
        bulgu = 0
        for sir in kayit["gizliler"]:
            if sir in metin:
                bulgu += 1
                metin = metin.replace(sir, "[GIZLI]")
        rapor.append({"id": kayit["id"], "maskeli_metin": metin, "bulgu": bulgu})
    return rapor

veri = json_yukle("veri/log_kayitlari.json")
try:
    rapor = sir_maskele(veri["kayitlar"])
except Exception as hata:
    rapor = [{"id": "hata", "hata": type(hata).__name__}]
print("rapor sırası", "doğru" if [r["id"] for r in rapor] == [b["id"] for b in veri["beklenen"]] else "YANLIŞ")
for beklenen in veri["beklenen"]:
    bulunan = next((r for r in rapor if r["id"] == beklenen["id"]), None)
    print(beklenen["id"], "doğru" if bulunan == beklenen else "YANLIŞ", bulunan)
for b in veri["bozuk_girdiler"]:
    try:
        sir_maskele(b["girdi"])
        print(b["id"], "YANLIŞ: kabul edildi", b["aciklama"])
    except ValueError:
        print(b["id"], "doğru: ValueError", b["aciklama"])
    except Exception as hata:
        print(b["id"], "YANLIŞ:", type(hata).__name__, b["aciklama"])
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-15")
```

```test
import copy
K = [
    {"id": "kayit-1", "metin": "token=sk-live-1234; yedek=sk-live-1234; diger=abcd1234", "gizliler": ["abcd1234", "sk-live-1234"]},
    {"id": "temiz-1", "metin": "sır yok", "gizliler": ["abcd1234"]},
]
BEKLENEN = [
    {"id": "kayit-1", "maskeli_metin": "token=[GIZLI]; yedek=[GIZLI]; diger=[GIZLI]", "bulgu": 3},
    {"id": "temiz-1", "maskeli_metin": "sır yok", "bulgu": 0},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K) != BEKLENEN or K != once or fn(list(reversed(K))) != BEKLENEN or fn([]) != []:
            return False
        cakisan = [{"id": "c-1", "metin": "abc12345", "gizliler": ["abc123", "abc12345"]}]
        if fn(cakisan) != [{"id": "c-1", "maskeli_metin": "[GIZLI]", "bulgu": 1}]:
            return False
        for uzunluk in (4, 128):
            sir = "a" * uzunluk
            if fn([{"id": "s", "metin": sir, "gizliler": [sir]}])[0]["bulgu"] != 1:
                return False
        if fn([dict(K[0], id="a" * 64)])[0]["id"] != "a" * 64:
            return False
        for kayitlar in [
            None, {}, [None], [dict(K[0], ek=1)], [dict(K[0], id="")], [dict(K[0], id="a b")],
            [dict(K[0], id="a" * 65)], [K[0], K[0]], [dict(K[0], metin=None)], [dict(K[0], gizliler=None)],
            [dict(K[0], gizliler=["abc"])], [dict(K[0], gizliler=["a" * 129])],
            [dict(K[0], gizliler=["abc\n"])], [dict(K[0], gizliler=["abc\0"])],
            [dict(K[0], gizliler=["abcd", "abcd"])],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(sir_maskele), "bütün eşleşmeler ve çakışan sırlar maskelenmeli")
def m_sayac(kayitlar):
    sonuc = sir_maskele(kayitlar)
    for kayit in sonuc:
        kayit["bulgu"] = 0
    return sonuc
def m_sira(kayitlar):
    degisen = [dict(x, gizliler=sorted(x["gizliler"], key=len)) for x in kayitlar]
    return sir_maskele(degisen)
def m_metin(kayitlar):
    return sir_maskele([dict(x, metin="") for x in kayitlar])
for ad, mutant in [("sayacı silen", m_sayac), ("sırayı bozan", m_sira), ("metni silen", m_metin)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
# --- carbon-c8-ek-bas ---
raises(ValueError, sir_maskele, [{"id": 123, "metin": "temiz"}], msg="id str olmalı")
raises(ValueError, sir_maskele, [{"id": "m1", "metin": 123}], msg="metin str olmalı")
raises(ValueError, sir_maskele, [{"id": 123, "metin": "temiz", "gizliler": []}], msg="kimlik str olmalı")
raises(ValueError, sir_maskele, [{"id": "m1", "metin": "temiz", "gizliler": [123]}], msg="gizli değer str olmalı")
raises(ValueError, sir_maskele, [{"id": "m1", "metin": "temiz", "gizliler": ["abcd\r1234"]}], msg="gizli değer CR içeremez")
# --- carbon-c8-ek-son ---
```

```solution
def sir_maskele(kayitlar):
    import re
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    kimlikler = set()
    rapor = []
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"id", "metin", "gizliler"}:
            raise ValueError("kayıt şeması geçersiz")
        kimlik = kayit["id"]
        if not isinstance(kimlik, str):
            raise ValueError("kimlik metin olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kimlik):
            raise ValueError("kimlik geçersiz")
        if kimlik in kimlikler:
            raise ValueError("kimlik yinelenemez")
        kimlikler.add(kimlik)
        if not isinstance(kayit["metin"], str):
            raise ValueError("metin string olmalı")
        if not isinstance(kayit["gizliler"], list):
            raise ValueError("gizliler liste olmalı")
        if len(set(kayit["gizliler"])) != len(kayit["gizliler"]):
            raise ValueError("gizliler yinelenemez")
        for sir in kayit["gizliler"]:
            if not isinstance(sir, str):
                raise ValueError("gizli değer metin olmalı")
            if len(sir) < 4:
                raise ValueError("gizli değer çok kısa")
            if len(sir) > 128:
                raise ValueError("gizli değer çok uzun")
            if "\n" in sir or "\r" in sir or "\0" in sir:
                raise ValueError("gizli değer kontrol karakteri içeremez")
        metin = kayit["metin"]
        bulgu = 0
        for sir in sorted(kayit["gizliler"], key=len, reverse=True):
            sayi = metin.count(sir)
            bulgu += sayi
            metin = metin.replace(sir, "[GIZLI]")
        rapor.append({"id": kimlik, "maskeli_metin": metin, "bulgu": bulgu})
    return sorted(rapor, key=lambda x: x["id"])
```

```hint
Önce gizli değerleri doğrula ve uzunluğa göre azalan sırala. `count` ile eşleşme sayısını topla, ardından `replace` ile bütün eşleşmeleri maskele.
```
:::

::: anlat Kapsam hem yetkiyi hem süreyi sınırlar
Aracılı kimlik bilgisi yalnız belirli araç, eylem ve kaynaklarda kullanılabilir. Modelin gerçek değeri görmesi yasaktır. Bu derste ömür 1 ile 300 **milisaniye** arasındadır; gerçek sistemlerdeki dakikalar mertebesindeki ömrün kısaltılmış, sentetik bir ölçeğidir. Son geçerlilik anı kullanım kararında hâlâ geçerlidir, sonrası süresi dolmuş sayılır.

Kapsam listelerindeki değerler benzersizdir. Böylece aynı yetkinin yinelenmesi denetim raporunu ve politika karşılaştırmasını bulandırmaz.

**Görev 2'de sık tuzaklar:** Ömrü saniye sanmak 300 saniyelik (300000 ms) bir kapsamı geçirir (`veri/kapsamlar.json`, `k-03`). `if kapsam["model_gorebilir"]` denetimi `0` değerini kapalı sayar; `is False` gerekir (`k-05`). Kaynak listesine joker ya da araca `sil` eylemi girmesi, "dar kapsam" iddiasını boşa çıkarır (`k-06`, `k-07`).
:::

::: gorev 2 · Kısa ömürlü ve dar kimlik kapsamını doğrula
`kimlik_kapsami_dogrula(kapsam)` işlevini yaz. Kapsam tam olarak `arac`, `eylemler`, `kaynaklar`, `verilis_ms`, `son_gecerlilik_ms`, `model_gorebilir` alanlarını taşısın. Araç `dosya_oku`, `web_getir`, `rapor_yaz`; eylemler `oku`, `yaz`, `getir`; kaynaklar `api.ornek.com`, `cdn.ornek.com`, `yerel/rapor` değerlerinden oluşan boş olmayan ve yinelenmeyen listelerdir.

Zamanlar bool olmayan sıfır/pozitif int olmalı; son geçerlilik verilişten büyük olmalı ve fark 1–300 ms olmalıdır. `model_gorebilir` gerçek bool `False` olmalıdır. Geçersiz veride `ValueError` yükselt.

Kapsamı yeni listelerle döndür; girdiyi değiştirme.

Görünür veri: `veri/kapsamlar.json`. Her kapsamın `beklenen` alanı vardır; `null`, `ValueError` demektir.

```starter
from ai_savunma_veri import json_yukle

def kimlik_kapsami_dogrula(kapsam):
    # KUSURLU BAŞLANGIÇ KODU: ömrü saniye sanıp 300000 ms'ye kadar kabul ediyor, model_gorebilir alanını doğruluk değeriyle okuyor (0 kabul edilir), araç, eylem ve kaynak listelerini doğrulamıyor (joker, sil, boş liste geçer) ve girdiyi kopyalamadan döndürüyor!
    if kapsam.get("model_gorebilir"):
        raise ValueError("model gerçek sırrı göremez")
    omur = kapsam["son_gecerlilik_ms"] - kapsam["verilis_ms"]
    if not 0 < omur <= 300000:
        raise ValueError("ömür geçersiz")
    return kapsam

veri = json_yukle("veri/kapsamlar.json")
for o in veri["ornekler"]:
    try:
        sonuc = kimlik_kapsami_dogrula(o["kapsam"])
    except ValueError:
        sonuc = None
    except Exception as hata:
        sonuc = type(hata).__name__
    print(o["id"], "doğru" if sonuc == o["beklenen"] else "YANLIŞ", o["aciklama"])
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-15")
```

```test
import copy
K = {"arac": "web_getir", "eylemler": ["getir"], "kaynaklar": ["api.ornek.com"], "verilis_ms": 1000, "son_gecerlilik_ms": 1200, "model_gorebilir": False}
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        sonuc = fn(K)
        if sonuc != K or K != once or sonuc is K or sonuc["eylemler"] is K["eylemler"] or sonuc["kaynaklar"] is K["kaynaklar"]:
            return False
        for omur in (1, 300):
            if fn(dict(K, son_gecerlilik_ms=1000 + omur))["son_gecerlilik_ms"] != 1000 + omur:
                return False
        if fn(dict(K, verilis_ms=0, son_gecerlilik_ms=1))["verilis_ms"] != 0:
            return False
        for kapsam in [
            None, [], dict(K, ek=1), dict(K, arac="diger"), dict(K, eylemler=[]), dict(K, eylemler=None),
            dict(K, eylemler=["sil"]), dict(K, eylemler=["getir", "getir"]),
            dict(K, kaynaklar=[]), dict(K, kaynaklar=None), dict(K, kaynaklar=["127.0.0.1"]),
            dict(K, kaynaklar=["api.ornek.com", "api.ornek.com"]),
            dict(K, verilis_ms=-1), dict(K, verilis_ms=True), dict(K, son_gecerlilik_ms=1000),
            dict(K, son_gecerlilik_ms=999), dict(K, son_gecerlilik_ms=1301),
            dict(K, son_gecerlilik_ms=False), dict(K, model_gorebilir=True), dict(K, model_gorebilir=0),
        ]:
            try:
                fn(kapsam)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(kimlik_kapsami_dogrula), "araç, eylem, kaynak, ömür ve model yalıtımı korunmalı")
def m_model(kapsam):
    sonuc = kimlik_kapsami_dogrula(kapsam)
    sonuc["model_gorebilir"] = True
    return sonuc
def m_kaynak(kapsam):
    sonuc = kimlik_kapsami_dogrula(kapsam)
    sonuc["kaynaklar"].append("127.0.0.1")
    return sonuc
def m_omur(kapsam):
    sonuc = kimlik_kapsami_dogrula(kapsam)
    sonuc["son_gecerlilik_ms"] += 301
    return sonuc
for ad, mutant in [("modeli açan", m_model), ("kaynağı açan", m_kaynak), ("ömürü uzatan", m_omur)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
# --- carbon-c8-ek-bas ---
raises(ValueError, kimlik_kapsami_dogrula, dict(K, arac=123), msg="arac str olmalı")
raises(ValueError, kimlik_kapsami_dogrula, dict(K, eylemler=[123]), msg="eylem str olmalı")
raises(ValueError, kimlik_kapsami_dogrula, dict(K, kaynaklar=[123]), msg="kaynak str olmalı")
raises(ValueError, kimlik_kapsami_dogrula, dict(K, verilis_ms=True), msg="verilis_ms bool ret")
raises(ValueError, kimlik_kapsami_dogrula, dict(K, son_gecerlilik_ms=True), msg="son_gecerlilik_ms bool ret")
raises(ValueError, kimlik_kapsami_dogrula, dict(K, eylemler=tuple(K["eylemler"])), msg="eylemler tuple olamaz")
raises(ValueError, kimlik_kapsami_dogrula, dict(K, verilis_ms="0"), msg="verilis_ms str olamaz")
raises(ValueError, kimlik_kapsami_dogrula, dict(K, verilis_ms=-1), msg="verilis_ms negatif olamaz")
raises(ValueError, kimlik_kapsami_dogrula, dict(K, son_gecerlilik_ms="200"), msg="son_gecerlilik_ms str olamaz")
eq(kimlik_kapsami_dogrula(dict(K, verilis_ms=0, son_gecerlilik_ms=100))["verilis_ms"], 0, "verilis_ms 0 geçerli")
raises(ValueError, kimlik_kapsami_dogrula, dict(K, verilis_ms=-1, son_gecerlilik_ms=100), msg="TTL içinde negatif verilis_ms ret")
# --- carbon-c8-ek-son ---
```

```solution
def kimlik_kapsami_dogrula(kapsam):
    if not isinstance(kapsam, dict):
        raise ValueError("kapsam sözlük olmalı")
    if set(kapsam) != {"arac", "eylemler", "kaynaklar", "verilis_ms", "son_gecerlilik_ms", "model_gorebilir"}:
        raise ValueError("kapsam şeması geçersiz")
    if kapsam["arac"] not in ("dosya_oku", "web_getir", "rapor_yaz"):
        raise ValueError("araç geçersiz")
    for alan, izinli in [("eylemler", ("oku", "yaz", "getir")), ("kaynaklar", ("api.ornek.com", "cdn.ornek.com", "yerel/rapor"))]:
        degerler = kapsam[alan]
        if not isinstance(degerler, list):
            raise ValueError(alan + " liste olmalı")
        if not degerler:
            raise ValueError(alan + " boş olamaz")
        if len(set(degerler)) != len(degerler):
            raise ValueError(alan + " yinelenemez")
        if any(deger not in izinli for deger in degerler):
            raise ValueError(alan + " izinli değil")
    if type(kapsam["verilis_ms"]) is not int:
        raise ValueError("veriliş int olmalı")
    if kapsam["verilis_ms"] < 0:
        raise ValueError("veriliş negatif olamaz")
    if type(kapsam["son_gecerlilik_ms"]) is not int:
        raise ValueError("son geçerlilik int olmalı")
    omur = kapsam["son_gecerlilik_ms"] - kapsam["verilis_ms"]
    if omur < 1:
        raise ValueError("ömür pozitif olmalı")
    if omur > 300:
        raise ValueError("ömür çok uzun")
    if kapsam["model_gorebilir"] is not False:
        raise ValueError("model gerçek sırrı göremez")
    return {"arac": kapsam["arac"], "eylemler": list(kapsam["eylemler"]), "kaynaklar": list(kapsam["kaynaklar"]), "verilis_ms": kapsam["verilis_ms"], "son_gecerlilik_ms": kapsam["son_gecerlilik_ms"], "model_gorebilir": False}
```

```hint
İki kapsam listesini aynı desenle doğrula. Ömrü son geçerlilik eksi veriliş olarak hesapla; model görünürlüğünü kimlik `False` denetimiyle kapat.
```
:::

::: anlat Broker kararı gerçek sırrı döndürmez
İstek kapsam dışındaysa `kapsam`, broker dışı kanaldan geldiyse `kanal`, kullanım zamanı aralık dışındaysa `zaman`, kimlik bilgisi daha önce kullanıldıysa `tekrar` nedeni eklenir. Nedenler bu sıradadır ve birden fazlası görünür kalır.

Karar `izin` olsa bile dönen değer gerçek API anahtarı değil, opak `kisa-omurlu-belirtec` referansıdır. Ret kararında referans `None` olur. Böylece model veya günlük kaydı gerçek sırrı elde etmez.

**Görev 3'te sık tuzaklar:** Yalnız aracı karşılaştırmak, aynı araçla başka kaynağa ya da başka eyleme gidilmesine izin verir (`veri/broker_istekleri.json`, `baska-kaynak`, `baska-eylem`). Kanal ve tekrar denetimi olmadan sızan belirteç broker dışından ya da ikinci kez kullanılabilir. `<` ile son anı dışarıda bırakmak sözleşmedeki kapalı aralığı bozar (`mesru` tam son geçerlilik anındadır). İzin kararına ham anahtarı koymak, broker'ın tek amacını tersine çevirir.
:::

::: gorev 3 · Aracılı kimlik bilgisi kullanımını denetle
`broker_kullanim_deneti(istekler, kapsam, simdi_ms)` işlevini yaz. Kapsam ikinci görevdeki bütün kuralları sağlasın. `simdi_ms` bool olmayan sıfır/pozitif int olmalıdır. İstekler liste; her kayıt tam olarak `id`, `arac`, `eylem`, `kaynak`, `kanal`, `kullanildi` alanlarını taşısın. Kimlik ilk görevdeki desene uysun ve benzersiz olsun. Kanal `broker` veya `dogrudan`, `kullanildi` gerçek bool olmalıdır. Araç, eylem ve kaynak stringdir. Geçersiz veride `ValueError` yükselt.

Araç, eylem veya kaynak kapsam dışındaysa `kapsam`; kanal broker değilse `kanal`; zaman verilişten küçük veya son geçerlilikten büyükse `zaman`; kullanım durumu doğruysa `tekrar` ekle. Neden yoksa `izin`, aksi halde `reddet` kararı ver.

Her kayıt için `{"id":ID,"karar":KARAR,"nedenler":[...],"referans":REFERANS}` döndür. Yalnız izinde `kisa-omurlu-belirtec`, rette `None` kullan. Kimliğe göre sırala, boş istekte boş liste döndür ve girdileri değiştirme.

Görünür veri: `veri/broker_istekleri.json`. Dosyada kapsam, `simdi_ms`, altı istek, 1 ms geç kalan örnek ve dört bozuk girdi vardır.

```starter
from ai_savunma_veri import json_yukle

def broker_kullanim_deneti(istekler, kapsam, simdi_ms):
    # KUSURLU BAŞLANGIÇ KODU: yalnız aracı kapsamla karşılaştırıyor (eylem ve kaynak kaçar), doğrudan kanalı ve tekrar kullanımı denetlemiyor, son geçerlilik anını dışarıda bırakıyor, izin verilen kayda opak referans yerine ham anahtarı koyuyor, girdileri doğrulamıyor ve raporu sıralamıyor!
    rapor = []
    for istek in istekler:
        nedenler = []
        if istek["arac"] != kapsam["arac"]:
            nedenler.append("kapsam")
        if not (kapsam["verilis_ms"] <= simdi_ms < kapsam["son_gecerlilik_ms"]):
            nedenler.append("zaman")
        rapor.append({"id": istek["id"], "karar": "reddet" if nedenler else "izin", "nedenler": nedenler,
                      "referans": None if nedenler else "sk-test-AB12CD34"})
    return rapor

veri = json_yukle("veri/broker_istekleri.json")
try:
    rapor = broker_kullanim_deneti(veri["istekler"], veri["kapsam"], veri["simdi_ms"])
except Exception as hata:
    rapor = [{"id": "hata", "hata": type(hata).__name__}]
print("rapor sırası", "doğru" if [r["id"] for r in rapor] == [b["id"] for b in veri["beklenen"]] else "YANLIŞ")
for beklenen in veri["beklenen"]:
    bulunan = next((r for r in rapor if r["id"] == beklenen["id"]), None)
    print(beklenen["id"], "doğru" if bulunan == beklenen else "YANLIŞ", bulunan)
gec = broker_kullanim_deneti(veri["istekler"][:1], veri["kapsam"], veri["gec_kalan"]["simdi_ms"])
print("1 ms geç", "doğru" if gec == veri["gec_kalan"]["beklenen"] else "YANLIŞ", gec)
for b in veri["bozuk_girdiler"]:
    try:
        broker_kullanim_deneti(b["girdi"], veri["kapsam"], veri["simdi_ms"])
        print(b["id"], "YANLIŞ: kabul edildi", b["aciklama"])
    except ValueError:
        print(b["id"], "doğru: ValueError", b["aciklama"])
    except Exception as hata:
        print(b["id"], "YANLIŞ:", type(hata).__name__, b["aciklama"])
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-15")
```

```test
import copy
K = {"arac": "web_getir", "eylemler": ["getir"], "kaynaklar": ["api.ornek.com"], "verilis_ms": 100, "son_gecerlilik_ms": 200, "model_gorebilir": False}
I = [
    {"id": "izin-1", "arac": "web_getir", "eylem": "getir", "kaynak": "api.ornek.com", "kanal": "broker", "kullanildi": False},
    {"id": "ret-1", "arac": "dosya_oku", "eylem": "oku", "kaynak": "yerel/rapor", "kanal": "dogrudan", "kullanildi": True},
]
BEKLENEN = [
    {"id": "izin-1", "karar": "izin", "nedenler": [], "referans": "kisa-omurlu-belirtec"},
    {"id": "ret-1", "karar": "reddet", "nedenler": ["kapsam", "kanal", "tekrar"], "referans": None},
]
def sozlesme(fn):
    try:
        ionce = copy.deepcopy(I)
        konce = copy.deepcopy(K)
        if fn(I, K, 100) != BEKLENEN or fn(I, K, 200) != BEKLENEN or I != ionce or K != konce or fn([], K, 150) != []:
            return False
        for alan, deger in [("arac", "dosya_oku"), ("eylem", "oku"), ("kaynak", "yerel/rapor")]:
            if fn([dict(I[0], **{alan: deger})], K, 150)[0]["nedenler"] != ["kapsam"]:
                return False
        for zaman in (99, 201):
            if fn([I[0]], K, zaman)[0]["nedenler"] != ["zaman"]:
                return False
        for omur in (1, 300):
            if fn([], dict(K, verilis_ms=0, son_gecerlilik_ms=omur), 0) != []:
                return False
        for istekler, kapsam, simdi in [
            (None, K, 100), ({}, K, 100), ([None], K, 100), (I, None, 100),
            (I, dict(K, model_gorebilir=True), 100), (I, K, True), (I, K, -1),
            (I, dict(K, son_gecerlilik_ms=100), 100), (I, dict(K, son_gecerlilik_ms=401), 100),
            ([dict(I[0], ek=1)], K, 100), ([dict(I[0], id="")], K, 100), ([dict(I[0], id="a b")], K, 100),
            ([dict(I[0], id="a" * 65)], K, 100), ([I[0], I[0]], K, 100),
            ([dict(I[0], arac=None)], K, 100), ([dict(I[0], eylem=1)], K, 100), ([dict(I[0], kaynak=None)], K, 100),
            ([dict(I[0], kanal="model")], K, 100), ([dict(I[0], kullanildi=0)], K, 100),
        ]:
            try:
                fn(istekler, kapsam, simdi)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(broker_kullanim_deneti), "kapsam, broker kanalı, kapalı zaman aralığı ve tek kullanım korunmalı")
def m_kapsam(istekler, kapsam, simdi):
    yeni = copy.deepcopy(kapsam)
    yeni.update(arac="dosya_oku", eylemler=["oku"], kaynaklar=["yerel/rapor"])
    return broker_kullanim_deneti(istekler, yeni, simdi)
def m_zaman(istekler, kapsam, simdi):
    yeni = dict(kapsam, verilis_ms=0, son_gecerlilik_ms=300)
    return broker_kullanim_deneti(istekler, yeni, simdi)
def m_tekrar(istekler, kapsam, simdi):
    return broker_kullanim_deneti([dict(x, kullanildi=False) for x in istekler], kapsam, simdi)
for ad, mutant in [("kapsamı açan", m_kapsam), ("zamanı genişleten", m_zaman), ("tekrarı silen", m_tekrar)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
raises(ValueError,broker_kullanim_deneti,[{'id': 'izin-1', 'arac': 'web_getir', 'eylem': 'getir', 'kaynak': 'api.ornek.com', 'kanal': 'broker', 'kullanildi': False}, {'id': 'ret-1', 'arac': 'dosya_oku', 'eylem': 'oku', 'kaynak': 'yerel/rapor', 'kanal': 'dogrudan', 'kullanildi': True}],{'arac': 'web_getir', 'eylemler': None, 'kaynaklar': ['api.ornek.com'], 'verilis_ms': 100, 'son_gecerlilik_ms': 200, 'model_gorebilir': False},150,msg="hatalı alan ValueError sözleşmesi: mutant:391:29:Add->Sub")
raises(ValueError,broker_kullanim_deneti,[{'id': 'izin-1', 'arac': 'web_getir', 'eylem': 'getir', 'kaynak': 'api.ornek.com', 'kanal': 'broker', 'kullanildi': False}, {'id': 'ret-1', 'arac': 'dosya_oku', 'eylem': 'oku', 'kaynak': 'yerel/rapor', 'kanal': 'dogrudan', 'kullanildi': True}],{'arac': 'web_getir', 'eylemler': [], 'kaynaklar': ['api.ornek.com'], 'verilis_ms': 100, 'son_gecerlilik_ms': 200, 'model_gorebilir': False},150,msg="hatalı alan ValueError sözleşmesi: mutant:396:29:Add->Sub")
raises(ValueError,broker_kullanim_deneti,[{'id': 'izin-1', 'arac': 'web_getir', 'eylem': 'getir', 'kaynak': 'api.ornek.com', 'kanal': 'broker', 'kullanildi': False}, {'id': 'ret-1', 'arac': 'dosya_oku', 'eylem': 'oku', 'kaynak': 'yerel/rapor', 'kanal': 'dogrudan', 'kullanildi': True}],{'arac': 'web_getir', 'eylemler': [''], 'kaynaklar': ['api.ornek.com'], 'verilis_ms': 100, 'son_gecerlilik_ms': 200, 'model_gorebilir': False},150,msg="hatalı alan ValueError sözleşmesi: mutant:401:29:Add->Sub")
# --- carbon-c8-ek-bas ---
raises(ValueError, broker_kullanim_deneti, I, dict(K, arac=123), 150, msg="arac str olmalı")
raises(ValueError, broker_kullanim_deneti, I, dict(K, eylemler=[123]), 150, msg="eylem str olmalı")
raises(ValueError, broker_kullanim_deneti, I, dict(K, kaynaklar=[123]), 150, msg="kaynak str olmalı")
raises(ValueError, broker_kullanim_deneti, I, dict(K, verilis_ms=True), 150, msg="verilis_ms bool ret")
raises(ValueError, broker_kullanim_deneti, I, dict(K, son_gecerlilik_ms=True), 150, msg="son_gecerlilik_ms bool ret")
raises(ValueError, broker_kullanim_deneti, I, K, True, msg="simdi_ms bool ret")
raises(ValueError, broker_kullanim_deneti, [dict(I[0], id=123)], K, 150, msg="istek id str olmalı")
raises(ValueError, broker_kullanim_deneti, [dict(I[0], arac=123)], K, 150, msg="istek arac str olmalı")
raises(ValueError, broker_kullanim_deneti, [dict(I[0], eylem=123)], K, 150, msg="istek eylem str olmalı")
raises(ValueError, broker_kullanim_deneti, [dict(I[0], kaynak=123)], K, 150, msg="istek kaynak str olmalı")
raises(ValueError, broker_kullanim_deneti, I, dict(K, ek=1), 50, msg="kapsam fazla alan ret")
raises(ValueError, broker_kullanim_deneti, I, dict(K, eylemler=tuple(K["eylemler"])), 50, msg="eylemler tuple olamaz")
raises(ValueError, broker_kullanim_deneti, I, dict(K, verilis_ms=-1), 50, msg="verilis_ms negatif olamaz")
raises(ValueError, broker_kullanim_deneti, I, dict(K, son_gecerlilik_ms="200"), 50, msg="son_gecerlilik_ms str olamaz")
ok(isinstance(broker_kullanim_deneti(I, dict(K, verilis_ms=0, son_gecerlilik_ms=100), 50), list), "verilis_ms 0 geçerli")
# --- carbon-c8-ek-son ---
```

```solution
def broker_kullanim_deneti(istekler, kapsam, simdi_ms):
    import re
    if not isinstance(kapsam, dict):
        raise ValueError("kapsam sözlük olmalı")
    if set(kapsam) != {"arac", "eylemler", "kaynaklar", "verilis_ms", "son_gecerlilik_ms", "model_gorebilir"}:
        raise ValueError("kapsam şeması geçersiz")
    if kapsam["arac"] not in ("dosya_oku", "web_getir", "rapor_yaz"):
        raise ValueError("araç geçersiz")
    for alan, izinli in [("eylemler", ("oku", "yaz", "getir")), ("kaynaklar", ("api.ornek.com", "cdn.ornek.com", "yerel/rapor"))]:
        if not isinstance(kapsam[alan], list):
            raise ValueError(alan + " liste olmalı")
        if not kapsam[alan]:
            raise ValueError(alan + " boş olamaz")
        if any(deger not in izinli for deger in kapsam[alan]):
            raise ValueError(alan + " izinli değil")
    if type(kapsam["verilis_ms"]) is not int:
        raise ValueError("veriliş int olmalı")
    if kapsam["verilis_ms"] < 0:
        raise ValueError("veriliş negatif olamaz")
    if type(kapsam["son_gecerlilik_ms"]) is not int:
        raise ValueError("son geçerlilik int olmalı")
    omur = kapsam["son_gecerlilik_ms"] - kapsam["verilis_ms"]
    if omur < 1:
        raise ValueError("ömür pozitif olmalı")
    if omur > 300:
        raise ValueError("ömür çok uzun")
    if kapsam["model_gorebilir"] is not False:
        raise ValueError("model gerçek sırrı göremez")
    if type(simdi_ms) is not int:
        raise ValueError("şimdiki zaman int olmalı")
    if simdi_ms < 0:
        raise ValueError("şimdiki zaman negatif olamaz")
    if not isinstance(istekler, list):
        raise ValueError("istekler liste olmalı")
    kimlikler = set()
    rapor = []
    for istek in istekler:
        if not isinstance(istek, dict):
            raise ValueError("istek sözlük olmalı")
        if set(istek) != {"id", "arac", "eylem", "kaynak", "kanal", "kullanildi"}:
            raise ValueError("istek şeması geçersiz")
        kimlik = istek["id"]
        if not isinstance(kimlik, str):
            raise ValueError("kimlik metin olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kimlik):
            raise ValueError("kimlik geçersiz")
        if kimlik in kimlikler:
            raise ValueError("kimlik yinelenemez")
        kimlikler.add(kimlik)
        for alan in ("arac", "eylem", "kaynak"):
            if not isinstance(istek[alan], str):
                raise ValueError(alan + " metin olmalı")
        if istek["kanal"] not in ("broker", "dogrudan"):
            raise ValueError("kanal geçersiz")
        if type(istek["kullanildi"]) is not bool:
            raise ValueError("kullanım durumu bool olmalı")
        nedenler = []
        kapsam_hatasi = istek["arac"] != kapsam["arac"]
        if istek["eylem"] not in kapsam["eylemler"]:
            kapsam_hatasi = True
        if istek["kaynak"] not in kapsam["kaynaklar"]:
            kapsam_hatasi = True
        if kapsam_hatasi:
            nedenler.append("kapsam")
        if istek["kanal"] != "broker":
            nedenler.append("kanal")
        zaman_hatasi = simdi_ms < kapsam["verilis_ms"]
        if simdi_ms > kapsam["son_gecerlilik_ms"]:
            zaman_hatasi = True
        if zaman_hatasi:
            nedenler.append("zaman")
        if istek["kullanildi"]:
            nedenler.append("tekrar")
        izin = not nedenler
        rapor.append({"id": kimlik, "karar": "izin" if izin else "reddet", "nedenler": nedenler, "referans": "kisa-omurlu-belirtec" if izin else None})
    return sorted(rapor, key=lambda x: x["id"])
```

```hint
Kapsam ve zaman hatalarını ayrı bayraklarla topla; son geçerlilik anını kabul et. Dönüşte yalnız izin verilen kayda opak referans koy.
```
:::

::: anlat Maskeleme, gerçek çıktıdaki sırrı loglardan uzak tutar
Secrets yalıtımının son hattı maskelemedir: bir sır modelin çıktısına ya da bir log satırına sızsa bile, saklanan/telemetriye giden metin ham değeri taşımamalıdır. Son görevde senin `sir_maskele` işlevin, gerçek yerel modelin ürettiği metinleri broker'ın bildiği sır değeriyle maskeler. Deney iki görev koşar: modelin bir sır token'ı içeren Authorization log satırı yazdığı senaryo ve zararsız bir özet.

Sır değerini yalnız broker (sandbox) bilir; model onu yalnızca bu deneyde, maskelemenin çalıştığını gösterebilmek için yazar. Maskeleme sonrası loglanacak metinde ham sır **kalmaz**, yalnız `[GIZLI]` ve olay sayısı (bulgu) kalır. Böylece gerçek değer değil, yalnız olayın kendisi telemetriye taşınır.

**Çıktıyı okurken:** Log senaryosunda modelin sırrı kaç kez yazdığını (`ham_sir_sayisi`) ve senin `bulgu` sayını karşılaştır; ikisi eşit olmalıdır. Model sırrı yeniden biçimlendirdiyse (büyük harf, araya boşluk) ham sayı da maskeleme de onu görmez. Bu yüzden asıl hedef, sırrın modele hiç verilmemesidir; bu deney yalnız son hat savunmasını ölçer.
:::

::: gorev Gerçek deney · Gerçek çıktıdaki sırrı maskele
`sir_maskele(kayitlar)` işlevini yaz — kuralları ve çıktısı 1. görevdekiyle **aynıdır**. Deney gerçek modelin ürettiği metinleri (biri sır token'ı içerir) broker'ın sır değeriyle maskeler; senin işlevin tüm eşleşmeleri `[GIZLI]` ile değiştirir ve olay sayısını raporlar.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def sir_maskele(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: sırları verildiği sırayla maskeliyor (kısa önek sır önce değişirse uzun sırrın kuyruğu açıkta kalır), bulguyu eşleşme sayısı yerine "bulunan sır türü" olarak sayıyor, gizli değerlerin uzunluğunu ve kontrol karakterlerini doğrulamıyor ve raporu sıralamıyor!
    rapor = []
    for kayit in kayitlar:
        metin = kayit["metin"]
        bulgu = 0
        for sir in kayit["gizliler"]:
            if sir in metin:
                bulgu += 1
                metin = metin.replace(sir, "[GIZLI]")
        rapor.append({"id": kayit["id"], "maskeli_metin": metin, "bulgu": bulgu})
    return rapor

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_15 as deney
    deney.goster(sir_maskele)
```

```test
import ai_lab
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
import ast
_yasak = ("referans", "getattr", "kanit_yaz", "SECRET")
sorun = list(ai_lab.kod_denetimi(src, _yasak))
for _n in ast.walk(ast.parse(src)):
    if isinstance(_n, ast.ImportFrom) and any(a.name in _yasak or a.name == "*" for a in _n.names):
        sorun.append("referans importu yasak")
    if isinstance(_n, (ast.Import, ast.ImportFrom)) and any(x and x.split(".")[0] in ("inspect", "importlib", "runpy") for x in [a.name for a in _n.names] + ([_n.module] if isinstance(_n, ast.ImportFrom) else [])):
        sorun.append("kaynak okuma/dinamik import yasak")
    if isinstance(_n, ast.Name) and _n.id in ("exec", "eval", "compile", "__builtins__"):
        sorun.append("dinamik kod çalıştırma yasak: " + _n.id)
sorun = sorted(set(sorun))
if not kontrol(not sorun, "laboratuvar yamalanmamalı, referans kullanılmamalı " + ", ".join(sorun)):
    stop()
fn = need("sir_maskele")
from sandbox import ai_gercek_ai_savunma_15 as D
K = [
    {"id": "kayit-1", "metin": "token=sk-live-1234; yedek=sk-live-1234", "gizliler": ["sk-live-1234"]},
    {"id": "temiz-1", "metin": "sır yok", "gizliler": ["abcd1234"]},
]
BEKLENEN = [
    {"id": "kayit-1", "maskeli_metin": "token=[GIZLI]; yedek=[GIZLI]", "bulgu": 2},
    {"id": "temiz-1", "maskeli_metin": "sır yok", "bulgu": 0},
]
def sozlesme(f):
    try:
        if f([dict(k) for k in K]) != BEKLENEN or f([]) != []:
            return False
        for bozuk in (None, [None], [dict(K[0], ek=1)], [dict(K[0], gizliler=["abc"])], [dict(K[0], gizliler=["x", "x"])]):
            try:
                f(bozuk)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(fn), "bütün eşleşmeler ve çakışan sırlar maskelenmeli")
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
    sir_maskele = need('sir_maskele')
    def _birim_adim_1():
        import copy
        K = [
            {"id": "kayit-1", "metin": "token=sk-live-1234; yedek=sk-live-1234; diger=abcd1234", "gizliler": ["abcd1234", "sk-live-1234"]},
            {"id": "temiz-1", "metin": "sır yok", "gizliler": ["abcd1234"]},
        ]
        BEKLENEN = [
            {"id": "kayit-1", "maskeli_metin": "token=[GIZLI]; yedek=[GIZLI]; diger=[GIZLI]", "bulgu": 3},
            {"id": "temiz-1", "maskeli_metin": "sır yok", "bulgu": 0},
        ]
        def sozlesme(fn):
            try:
                once = copy.deepcopy(K)
                if fn(K) != BEKLENEN or K != once or fn(list(reversed(K))) != BEKLENEN or fn([]) != []:
                    return False
                cakisan = [{"id": "c-1", "metin": "abc12345", "gizliler": ["abc123", "abc12345"]}]
                if fn(cakisan) != [{"id": "c-1", "maskeli_metin": "[GIZLI]", "bulgu": 1}]:
                    return False
                for uzunluk in (4, 128):
                    sir = "a" * uzunluk
                    if fn([{"id": "s", "metin": sir, "gizliler": [sir]}])[0]["bulgu"] != 1:
                        return False
                if fn([dict(K[0], id="a" * 64)])[0]["id"] != "a" * 64:
                    return False
                for kayitlar in [
                    None, {}, [None], [dict(K[0], ek=1)], [dict(K[0], id="")], [dict(K[0], id="a b")],
                    [dict(K[0], id="a" * 65)], [K[0], K[0]], [dict(K[0], metin=None)], [dict(K[0], gizliler=None)],
                    [dict(K[0], gizliler=["abc"])], [dict(K[0], gizliler=["a" * 129])],
                    [dict(K[0], gizliler=["abc\n"])], [dict(K[0], gizliler=["abc\0"])],
                    [dict(K[0], gizliler=["abcd", "abcd"])],
                ]:
                    try:
                        fn(kayitlar)
                        return False
                    except ValueError:
                        pass
                return True
            except Exception:
                return False
        ok(sozlesme(sir_maskele), "bütün eşleşmeler ve çakışan sırlar maskelenmeli")
        def m_sayac(kayitlar):
            sonuc = sir_maskele(kayitlar)
            for kayit in sonuc:
                kayit["bulgu"] = 0
            return sonuc
        def m_sira(kayitlar):
            degisen = [dict(x, gizliler=sorted(x["gizliler"], key=len)) for x in kayitlar]
            return sir_maskele(degisen)
        def m_metin(kayitlar):
            return sir_maskele([dict(x, metin="") for x in kayitlar])
        for ad, mutant in [("sayacı silen", m_sayac), ("sırayı bozan", m_sira), ("metni silen", m_metin)]:
            ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
        raises(ValueError, sir_maskele, [{"id": 123, "metin": "temiz"}], msg="id str olmalı")
        raises(ValueError, sir_maskele, [{"id": "m1", "metin": 123}], msg="metin str olmalı")
        raises(ValueError, sir_maskele, [{"id": 123, "metin": "temiz", "gizliler": []}], msg="kimlik str olmalı")
        raises(ValueError, sir_maskele, [{"id": "m1", "metin": "temiz", "gizliler": [123]}], msg="gizli değer str olmalı")
        raises(ValueError, sir_maskele, [{"id": "m1", "metin": "temiz", "gizliler": ["abcd\r1234"]}], msg="gizli değer CR içeremez")
    try:
        _birim_adim_1()
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
    kontrol(r["sir_sizmadi"], "maskelenmiş gerçek metinlerde ham sır kalmadı")
    log = next((a for a in r["akislar"] if a["id"] == "log-1"), {})
    kontrol(log.get("ham_sir_sayisi", 0) >= 1 and log.get("bulgu", 0) == log.get("ham_sir_sayisi"),
            "modelin gerçek çıktısındaki sır tüm eşleşmelerde maskelendi")
    oz = D.ozet(r)
yol = ai_lab.kanit_yaz("savunma-secret", {"kaynak": "gercek", "kabul": all(sonuclar), "ders": "ai-savunma-15",
                                          "ortam": (r or {}).get("ortam"), "ozet": oz})
if oz:
    ok(True, f"BULGU ({r['ortam']['model']['ad']}): model gerçek çıktısında sırrı {oz['ham_sir_toplam']} kez yazdı; "
             f"maskeleme {oz['maskelenen_bulgu']} eşleşmeyi [GIZLI] yaptı, maskeli metinde ham sır sızmadı: {oz['sir_sizmadi']}. "
             f"Telemetri sırrın değerini değil yalnız olayını taşıdı (secrets yalıtımı).")
```

```solution
import ai_lab

def sir_maskele(kayitlar):
    import re
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    kimlikler = set()
    rapor = []
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"id", "metin", "gizliler"}:
            raise ValueError("kayıt şeması geçersiz")
        kimlik = kayit["id"]
        if not isinstance(kimlik, str):
            raise ValueError("kimlik metin olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kimlik):
            raise ValueError("kimlik geçersiz")
        if kimlik in kimlikler:
            raise ValueError("kimlik yinelenemez")
        kimlikler.add(kimlik)
        if not isinstance(kayit["metin"], str):
            raise ValueError("metin string olmalı")
        if not isinstance(kayit["gizliler"], list):
            raise ValueError("gizliler liste olmalı")
        if len(set(kayit["gizliler"])) != len(kayit["gizliler"]):
            raise ValueError("gizliler yinelenemez")
        for sir in kayit["gizliler"]:
            if not isinstance(sir, str):
                raise ValueError("gizli değer metin olmalı")
            if len(sir) < 4:
                raise ValueError("gizli değer çok kısa")
            if len(sir) > 128:
                raise ValueError("gizli değer çok uzun")
            if "\n" in sir or "\r" in sir or "\0" in sir:
                raise ValueError("gizli değer kontrol karakteri içeremez")
        metin = kayit["metin"]
        bulgu = 0
        for sir in sorted(kayit["gizliler"], key=len, reverse=True):
            sayi = metin.count(sir)
            bulgu += sayi
            metin = metin.replace(sir, "[GIZLI]")
        rapor.append({"id": kimlik, "maskeli_metin": metin, "bulgu": bulgu})
    return sorted(rapor, key=lambda x: x["id"])

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_15 as deney
    deney.goster(sir_maskele)
```

```hint
Bu işlev 1. görevdeki `sir_maskele` ile birebir aynıdır; tek fark, metinlerin gerçek model çıktısından gelmesidir. Gizli değerleri uzunluğa göre azalan sırala, `count` ile say ve `replace` ile tüm eşleşmeleri maskele.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Sır yerine dar yetkili aracılık kullan

Modelin kullanacağı API sırrını prompta yerleştirirsen çıktı ve telemetri yeni sızıntı kanalları olur. Maskeleme görünür kopyayı azaltır; en güçlü sınır modelin ham sırra hiç erişmemesidir. Kısa ömür, dar scope ve host aracılığı ayrı kontrollerdir. Süresi dolmamış bir credentialın istenen hedef için yetkili olup olmadığı ayrıca sınanır.

| Yaygın yanlış | Mekanizmanın sınırı |
|---|---|
| Maskelenmiş örnek gerçek secret yönetimidir | Sentetik redaksiyon gerçek vault ve kimlik rotasyonunun yerine geçmez. |

Saldırı–savunma bağlantısı: ai-saldiri-06.
:::

::: anlat Kaynak ile lab sonucunu ayır
[OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html). Dar yetki ve yaşam döngüsü credential güvenliğinin parçalarıdır; maskeleme gerçek sır deposunun yerine geçmez.
:::
