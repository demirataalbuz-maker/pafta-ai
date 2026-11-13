---
id: ai-savunma-08
title: Çıktı Guardrail ve Yapısal Doğrulama
summary: Model çıktısını katı şemayla doğrula, hassas içerik sinyallerini tara ve güvensiz yanıtları fail-closed kararla durdur.
timeout: 45
esleme: ai-saldiri-10, ai-savunma-15
---

::: anlat Yapısal olarak geçerli çıktı güvenli çıktı demek değildir

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Gerçek bir uygulamada model çıktısı Ollama `format` (JSON şeması), Pydantic/JSON Schema, NeMo Guardrails çıkış rayları ya da Guardrails AI doğrulayıcıları gibi katmanlardan geçer. Gitleaks/TruffleHog benzeri tarayıcılar sır kalıplarını arar. Karar FastAPI gibi bir sunucuda yanıtı geçirir, durdurur ya da insana yollar. | Görev 1–3: `veri/model_ciktilari.json`, `veri/cikti_metinleri.json` ve `veri/guardrail_kayitlari.json` içindeki **sentetik** çıktılar ve kayıtlar; standart Python ile şema, dört dar sızıntı kalıbı ve karar. Son adım: kurulu yerel Ollama modelinin yapısal (JSON) ve serbest modda ürettiği gerçek çıktılar. | Dört kalıp gerçek sırların çoğunu tanımaz: kodlanmış, bölünmüş ya da yeniden ifade edilmiş sızıntılar kaçar. İki mod ve tek koşu bir oran vermez. Şemaya uyan bir yanıtın içeriği doğru ya da zararsız olmak zorunda değildir. |

> [!NOT]
> Görev 1–3 sentetik veriyle çalışır. Bu görevlerde model ve ağ yoktur. Son adımdaki **Gerçek deney** görevi yalnız kurulu yerel Ollama modelini kullanır. `veri/` dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalanır; kopyada yaptığın değişiklik bir sonraki çalıştırmada sıfırlanır, **kalıcılık yoktur**. Kontrol bu dosyalardan ayrı, gizli verilerle sınar.

Modelden dönen JSON, istenen alanları taşısa bile özel anahtar, erişim belirteci veya yasaklı canary içerebilir. Çıktı guardrail katmanı bu yüzden en az iki denetimi ayırır: yapısal şema, uygulamanın veriyi işleyip işleyemeyeceğini; politika taraması, içeriğin kullanıcıya veya başka bir araca verilip verilemeyeceğini gösterir.

NeMo Guardrails ve FastAPI gerçek bir uygulamada yanıt doğrulama ve durdurma akışına bağlanabilir. Görev 1–3'teki fixture dış model çağırmaz; standart Python ile katı şema, sızıntı sinyali ve karar mantığını sınar. Son adım aynı kararı kurulu yerel modelin gerçek çıktılarına uygular. Sinyal raporu hassas değerin kendisini döndürmez.

**Saldırgan ne dener?** Çıktı tarafındaki saldırgan, modelin bağlamındaki sırrı (sistem istemi, araç sonucu, başka kullanıcının verisi) kullanıcıya ya da bir sonraki araca taşımaya çalışır. Dar bir kalıp tarayıcısını aşmak için değeri base64 ya da hex ile kodlatır. Ayrıca şunları dener:

- Değeri harflere bölmek ya da araya boşluk koydurmak.
- Tam genişlikli Unicode harflerle yazdırmak.
- Değeri şemanın izin verdiği bir alana gömmek: `kaynaklar` içinde bir kimlik ya da şemaya eklenmiş `sistem_notu`.
- Güven alanını yüksek göstererek insan incelemesinden kaçmak.

**Savunma neden kırılır?** Kalıp tarayıcısı yalnız bildiği biçimi görür. `api_key=` aranırken `ＡＰＩ＿ＫＥＹ＝` ya da base64 kopyası kaçar. Şema doğrulaması fazladan alanı sessizce atarsa hata görünmez olur. Atmak yerine bütün çıktıyı reddetmek, saldırının izini korur. Çıktıyı "düzeltmek" de savunmayı zayıflatır: `strip()`, kırpma ya da tür dönüştürme, modelin bozuk çıktısını geçerli gibi gösterir. Bu yüzden iki katman birlikte kullanılır: katı şema biçimi zorlar, tarayıcı bilinen kalıpları yakalar, karar katmanı ilk hatada değil bütün kanıtlarla karar verir.

**Görev 1'de sık tuzaklar:** Ek alanları bırakmak, `sistem_notu` gibi bir alanla gizli değer taşınmasına izin verir (`veri/model_ciktilari.json`, `m-04`). `isinstance(guven, (int, float))` denetimi `True` değerini kabul eder; `bool` ayrıca dışlanmalıdır (`m-06`). Kaynak listesini kopyalamadan döndürmek, çağıranın girdiyi değiştirmesine yol açar.
:::

::: tahmin Güven eşiği alt sınırı dahil etmez
Üç çıktı satırını yaz:

```python
print(0.5 < 0.5)
print(0.499 < 0.5)
print(len("token-123") >= 8)
```

???

```cikti
False
True
True
```

Bu derste güven 0.5 ise insan incelemesi gerekmez; daha düşük değerler incelemeye gider. Token uzunluğu eşiği ise sekiz karakterden başlar.
:::

::: gorev 1 · Model çıktısını katı ve kopyalanmış bir şemayla doğrula
`model_ciktisi_dogrula(cikti)` işlevini yaz. Çıktı tam olarak `ozet`, `etiket`, `guven`, `kaynaklar` alanlarını taşısın. Özet baş/son boşluğu olmayan, NUL içermeyen ve 1–500 karakterlik stringdir. Etiket yalnız `bilgi`, `islem` veya `reddetme` olmalıdır. Güven bool olmayan, sonlu ve 0–1 aralığında bir sayıdır.

Kaynaklar en fazla beş benzersiz kimlikten oluşan bir listedir. Her kimlik 1–64 karakterlik, ASCII harf veya rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren bir stringdir. Geçersiz veride `ValueError` yükselt.

Bütün alanları koruyan yeni bir sözlük ve yeni bir kaynak listesi döndür; girdiyi değiştirme.

Görünür veri: `veri/model_ciktilari.json`. Her örneğin `beklenen` alanı vardır; `null`, `ValueError` demektir.

```starter
from ai_savunma_veri import json_yukle

def model_ciktisi_dogrula(cikti):
    # KUSURLU BAŞLANGIÇ KODU: ek alanları sessizce bırakıyor (gizli değer sistem_notu gibi bir alanla taşınır), özeti strip() ile "düzeltiyor", güvende bool'u, türü ve aralığı denetlemiyor, kaynak kimliklerini doğrulamıyor ve kaynak listesini kopyalamıyor!
    for alan in ("ozet", "etiket", "guven", "kaynaklar"):
        if alan not in cikti:
            raise ValueError("eksik alan: " + alan)
    if cikti["etiket"] not in ("bilgi", "islem", "reddetme"):
        raise ValueError("etiket geçersiz")
    sonuc = dict(cikti)
    sonuc["ozet"] = str(cikti["ozet"]).strip()
    return sonuc

veri = json_yukle("veri/model_ciktilari.json")
for o in veri["ornekler"]:
    try:
        sonuc = model_ciktisi_dogrula(o["cikti"])
    except ValueError:
        sonuc = None
    except Exception as hata:
        sonuc = type(hata).__name__
    print(o["id"], "doğru" if sonuc == o["beklenen"] else "YANLIŞ", o["aciklama"], sonuc)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-08")
```

```test
import copy
C = {"ozet": "Kısa özet", "etiket": "bilgi", "guven": 0.5, "kaynaklar": ["belge-1", "belge-2"]}
def sozlesme(fn):
    try:
        once = copy.deepcopy(C)
        sonuc = fn(C)
        if sonuc != C or C != once or sonuc is C or sonuc["kaynaklar"] is C["kaynaklar"]:
            return False
        for guven in (0, 1, 0.5):
            if fn(dict(C, guven=guven))["guven"] != guven:
                return False
        if fn(dict(C, ozet="a" * 500))["ozet"] != "a" * 500:
            return False
        bes = [f"k{i}" for i in range(5)]
        if fn(dict(C, kaynaklar=bes))["kaynaklar"] != bes:
            return False
        if fn(dict(C, kaynaklar=["a" * 64]))["kaynaklar"] != ["a" * 64]:
            return False
        for cikti in [
            None, [], dict(C, ek=1), dict(C, ozet=""), dict(C, ozet=" x"),
            dict(C, ozet="x "), dict(C, ozet="a\x00b"), dict(C, ozet="a" * 501),
            dict(C, ozet=None), dict(C, etiket="diger"), dict(C, guven=True),
            dict(C, guven=-0.1), dict(C, guven=1.1), dict(C, guven=float("nan")),
            dict(C, guven=float("inf")), dict(C, kaynaklar=None), dict(C, kaynaklar="a"),
            dict(C, kaynaklar=[f"k{i}" for i in range(6)]), dict(C, kaynaklar=["a", "a"]),
            dict(C, kaynaklar=[""]), dict(C, kaynaklar=["-a"]), dict(C, kaynaklar=["a b"]),
            dict(C, kaynaklar=["a" * 65]), dict(C, kaynaklar=[1]),
        ]:
            try:
                fn(cikti)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(model_ciktisi_dogrula), "katı alanlar, metin, güven, kaynak sınırları ve kopyalama korunmalı")
def m_etiket(cikti):
    sonuc = model_ciktisi_dogrula(cikti)
    sonuc["etiket"] = "diger"
    return sonuc
def m_guven(cikti):
    sonuc = model_ciktisi_dogrula(cikti)
    sonuc["guven"] = 1.1
    return sonuc
def m_kaynak(cikti):
    sonuc = model_ciktisi_dogrula(cikti)
    sonuc["kaynaklar"].append("bilinmeyen")
    return sonuc
for ad, mutant in [("etiketi değiştiren", m_etiket), ("güveni bozan", m_guven), ("kaynak ekleyen", m_kaynak)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
# --- carbon-c8-ek-bas ---
raises(ValueError, model_ciktisi_dogrula, dict(C, ozet=123), msg="özet str olmalı")
raises(ValueError, model_ciktisi_dogrula, dict(C, kaynaklar=[123]), msg="kaynak elemanı str olmalı")
raises(ValueError, model_ciktisi_dogrula, dict(C, guven=float("nan")), msg="NaN güven reddedilmeli")
raises(ValueError, model_ciktisi_dogrula, dict(C, guven="0.5"), msg="str güven reddedilmeli")
# --- carbon-c8-ek-son ---
```

```solution
def model_ciktisi_dogrula(cikti):
    import math
    import re
    if not isinstance(cikti, dict):
        raise ValueError("çıktı geçersiz")
    if set(cikti) != {"ozet", "etiket", "guven", "kaynaklar"}:
        raise ValueError("çıktı şeması geçersiz")
    ozet = cikti["ozet"]
    if not isinstance(ozet, str):
        raise ValueError("özet string olmalı")
    if not ozet or ozet != ozet.strip() or "\x00" in ozet:
        raise ValueError("özet geçersiz")
    if len(ozet) > 500:
        raise ValueError("özet çok uzun")
    if cikti["etiket"] not in ("bilgi", "islem", "reddetme"):
        raise ValueError("etiket geçersiz")
    guven = cikti["guven"]
    if isinstance(guven, bool) or not isinstance(guven, (int, float)):
        raise ValueError("güven sayı olmalı")
    if not math.isfinite(guven):
        raise ValueError("güven sonlu olmalı")
    if guven < 0 or guven > 1:
        raise ValueError("güven aralık dışında")
    kaynaklar = cikti["kaynaklar"]
    if not isinstance(kaynaklar, list):
        raise ValueError("kaynaklar liste olmalı")
    if len(kaynaklar) > 5:
        raise ValueError("kaynak sayısı üst sınırı aştı")
    if len(set(kaynaklar)) != len(kaynaklar):
        raise ValueError("kaynak kimliği yinelenemez")
    for kaynak in kaynaklar:
        if not isinstance(kaynak, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kaynak):
            raise ValueError("kaynak kimliği geçersiz")
    sonuc = dict(cikti)
    sonuc["kaynaklar"] = list(kaynaklar)
    return sonuc
```

```hint
Önce alan kümesini ve temel türleri ayır. Kaynakları ayrı liste olarak kopyala; metin ve kimliklerin hem alt hem üst sınırlarını denetle.
```
:::

::: anlat Sızıntı taraması değeri değil olay türünü raporlar
Çıktı taraması ham gizli değeri loglamamalıdır. Bu ders dört dar fixture sinyali kullanır: PEM biçimli özel anahtar başlığı, yeterli uzunlukta Bearer token, atanmış API anahtarı ve yasaklı `BREACH:CANARY-42` işareti. Bu kurallar her gerçek sırrı tanımaz; yalnız açıkça tanımlanan test kalıplarını bulur.

NFKC ve `casefold` yalnız karşılaştırma görünümünde kullanılır. İçerik temizlenmiş veya güvenli hâle getirilmiş sayılmaz. Karar katmanı sinyal türlerini alır; hassas eşleşmenin kendisini almaz.

**Çıktı nasıl okunur?** Sinyal listesi boşsa bu "sızıntı yok" demek değildir, "bilinen dört kalıptan biri yok" demektir. `veri/cikti_metinleri.json` içindeki `s-09` base64 kodlu bir anahtar taşır ve hiçbir sinyal üretmez. Bu, kasıtlı bırakılmış bir sınırdır.

**Görev 2'de sık tuzaklar:** Normalize etmeden aramak tam genişlikli `ＡＰＩ＿ＫＥＹ` yazımını kaçırır (`s-05`). Kelime sınırı olmadan aramak, `BREACH:CANARY-420` gibi başka bir değeri canary sayar (`s-07`). Uzunluk sınırı olmayan Bearer kalıbı kısa ve zararsız değerlerde gürültü üretir (`s-04`). Aynı sinyali tekrar eklemek karar katmanının sabit sıra beklentisini bozar (`s-08`).
:::

::: gorev 2 · Hassas değeri açığa çıkarmadan çıktı risk sinyalleri üret
`cikti_risk_sinyalleri(cikti)` işlevini yaz. Çıktı NUL içermeyen bir string olmalıdır; boş string kabul edilir ve sinyal üretmez. Diğer türlerde `ValueError` yükselt. Karşılaştırma görünümünü NFKC ve `casefold` ile normalize et.

Şu sinyalleri sabit sırayla ve her biri en fazla bir kez döndür:

1. `ozel_anahtar`: `-----BEGIN PRIVATE KEY-----`, `-----BEGIN RSA PRIVATE KEY-----`, `-----BEGIN EC PRIVATE KEY-----` veya `-----BEGIN OPENSSH PRIVATE KEY-----` başlığı.
2. `bearer_token`: kelime sınırında `Bearer`, boşluk ve ardından yalnız ASCII harf, rakam, nokta, alt çizgi, tire veya tilde içeren en az 8 karakterlik değer.
3. `api_anahtari`: `api key`, `api-key`, `api_key` veya `apikey` adı, `:`/`=` ve ardından aynı sınırlı karakter kümesinden en az 8 karakter.
4. `gizli_isaret`: bağımsız `BREACH:CANARY-42` işareti.

Görünür veri: `veri/cikti_metinleri.json`. Her metnin `beklenen` sinyal listesi vardır; `null`, `ValueError` demektir.

```starter
from ai_savunma_veri import json_yukle

def cikti_risk_sinyalleri(cikti):
    # KUSURLU BAŞLANGIÇ KODU: normalize etmeden büyük/küçük harfe duyarlı arıyor (bearer ve tam genişlikli harfler kaçar), yalnız "-----BEGIN PRIVATE KEY-----" başlığını tanıyor, token uzunluğunu denetlemiyor, canary'yi kelime sınırı olmadan arıyor ve aynı sinyali birden çok kez ekliyor!
    sinyaller = []
    if "-----BEGIN PRIVATE KEY-----" in cikti:
        sinyaller.append("ozel_anahtar")
    for satir in cikti.splitlines():
        if "Bearer " in satir:
            sinyaller.append("bearer_token")
        if "api_key=" in satir:
            sinyaller.append("api_anahtari")
    if "BREACH:CANARY-42" in cikti:
        sinyaller.append("gizli_isaret")
    return sinyaller

veri = json_yukle("veri/cikti_metinleri.json")
for o in veri["ornekler"]:
    try:
        sonuc = cikti_risk_sinyalleri(o["cikti"])
    except ValueError:
        sonuc = None
    except Exception as hata:
        sonuc = type(hata).__name__
    print(o["id"], "doğru" if sonuc == o["beklenen"] else "YANLIŞ", o["aciklama"], sonuc)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-08")
```

```test
def sozlesme(fn):
    try:
        if fn("") != [] or fn("Yalnız kısa bir özet") != []:
            return False
        tum = "-----BEGIN PRIVATE KEY-----\nBearer token-123\napi_key=abcd1234\nBREACH:CANARY-42"
        if fn(tum) != ["ozel_anahtar", "bearer_token", "api_anahtari", "gizli_isaret"]:
            return False
        for baslik in ("RSA", "EC", "OPENSSH"):
            if fn(f"-----BEGIN {baslik} PRIVATE KEY-----") != ["ozel_anahtar"]:
                return False
        if fn("Bearer abcdefgh") != ["bearer_token"]:
            return False
        if fn("Bearer abcdefg") != []:
            return False
        if fn("APIKEY:abcdefgh") != ["api_anahtari"]:
            return False
        if fn("api-key=abcdefg") != []:
            return False
        if fn("BREACH:CANARY-42 BREACH:CANARY-42") != ["gizli_isaret"]:
            return False
        if fn("BREACH:CANARY-42 yazmayacağım") != ["gizli_isaret"]:
            return False
        for cikti in (None, 1, [], "a\x00b"):
            try:
                fn(cikti)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(cikti_risk_sinyalleri), "dört sızıntı türü, uzunluk sınırları ve sabit sıra korunmalı")
def m_ozel(cikti):
    return [x for x in cikti_risk_sinyalleri(cikti) if x != "ozel_anahtar"]
def m_token(cikti):
    return [x for x in cikti_risk_sinyalleri(cikti) if x != "bearer_token"]
def m_isaret(cikti):
    return [x for x in cikti_risk_sinyalleri(cikti) if x != "gizli_isaret"]
for ad, mutant in [("özel anahtarı silen", m_ozel), ("Bearer tokenı silen", m_token), ("canary sinyalini silen", m_isaret)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def cikti_risk_sinyalleri(cikti):
    import re
    import unicodedata
    if not isinstance(cikti, str):
        raise ValueError("çıktı string olmalı")
    if "\x00" in cikti:
        raise ValueError("çıktı NUL içeremez")
    normal = unicodedata.normalize("NFKC", cikti).casefold()
    sinyaller = []
    if re.search(r"-----begin (?:rsa |ec |openssh )?private key-----", normal):
        sinyaller.append("ozel_anahtar")
    if re.search(r"\bbearer\s+[a-z0-9._~-]{8,}", normal):
        sinyaller.append("bearer_token")
    if re.search(r"\b(?:api[_ -]?key|apikey)\s*[:=]\s*[a-z0-9_~-]{8,}", normal):
        sinyaller.append("api_anahtari")
    if re.search(r"\bbreach:canary-42\b", normal):
        sinyaller.append("gizli_isaret")
    return sinyaller
```

```hint
Her kalıbı normalize edilmiş görünümde küçük harfle yaz. İki gizli değer kalıbının 8/7 karakter sınırını ayrı test et; sonuçta yalnız sinyal adlarını döndür.
```
:::

::: anlat Fail-closed karar güvenli olmayan çıktıyı durdurur
Son kararda şema hatası, özel anahtar veya token sızıntısı ve yasaklı canary `durdur` sonucunu üretir. Bu nedenlerden hiçbiri yokken güven 0.5'in altındaysa çıktı `insan_incelemesi` durumuna gider. Diğer durumlarda `gecir` denir.

Nedenler `sema`, `gizli_veri`, `gizli_isaret`, `dusuk_guven` sırasındadır. Şema bozukken de mevcut politika sinyalleri korunur; ilk hata diğer kanıtları silmemelidir. Rapor ham çıktı veya gizli değer taşımaz.

**Görev 3'te sık tuzaklar:** İlk nedeni bulunca durmak, olay incelemesinde "şema da bozuktu" kanıtını kaybettirir (`veri/guardrail_kayitlari.json`, `yanit-coklu`). Şema hatasını yalnız uyarı sayıp sızıntı yoksa geçirmek fail-open'dır (`yanit-sema`). `<=` eşiği tam 0.5 güveni gereksiz yere insana yollar (`yanit-sinir`); `<` kullan.
:::

::: gorev 3 · Şema, sızıntı ve güven kanıtlarıyla çıktı kararı üret
`cikti_guardrail_raporu(kayitlar)` işlevini yaz. Her kayıt tam olarak `id`, `sema_gecerli`, `sinyaller`, `guven` alanlarını taşısın. Kimlik ilk görevdeki kaynak kimliği kurallarına uysun ve benzersiz olsun. `sema_gecerli` gerçek bool; güven ilk görevdeki aralıkta sonlu sayı olmalıdır. Sinyaller ikinci görevdeki dört türün sabit sırasına uyan, yinelenmeyen listedir. Geçersiz veride `ValueError` yükselt.

Her kayıt için `{"id":ID,"karar":KARAR,"nedenler":[...]}` döndür:

- Şema false ise `sema` nedenini ekle.
- İlk üç sızıntı sinyalinden biri varsa `gizli_veri`; `gizli_isaret` varsa aynı adlı nedeni ekle.
- Bu üç nedenden biri varsa karar `durdur`.
- Aksi hâlde güven 0.5'ten küçükse `dusuk_guven` nedeniyle `insan_incelemesi`; değilse nedensiz `gecir` olsun.

Kayıtları kimliğe göre sırala, boş girdide boş liste döndür ve girdiyi değiştirme.

Görünür veri: `veri/guardrail_kayitlari.json`. Dosyada yedi kayıt, beklenen rapor ve dört bozuk girdi vardır.

```starter
from ai_savunma_veri import json_yukle

def cikti_guardrail_raporu(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: ilk nedeni bulunca diğerlerini atlıyor (kanıt kaybolur), şema hatasını yalnız not edip çıktıyı geçiriyor, güven eşiğini <= ile uyguluyor (0.5 incelemeye gider), kayıtları doğrulamıyor ve sıralamıyor!
    rapor = []
    for kayit in kayitlar:
        if any(s in ("ozel_anahtar", "bearer_token", "api_anahtari") for s in kayit["sinyaller"]):
            rapor.append({"id": kayit["id"], "karar": "durdur", "nedenler": ["gizli_veri"]})
        elif "gizli_isaret" in kayit["sinyaller"]:
            rapor.append({"id": kayit["id"], "karar": "durdur", "nedenler": ["gizli_isaret"]})
        elif kayit["guven"] <= 0.5:
            rapor.append({"id": kayit["id"], "karar": "insan_incelemesi", "nedenler": ["dusuk_guven"]})
        else:
            rapor.append({"id": kayit["id"], "karar": "gecir", "nedenler": [] if kayit["sema_gecerli"] else ["sema"]})
    return rapor

veri = json_yukle("veri/guardrail_kayitlari.json")
try:
    rapor = cikti_guardrail_raporu(veri["kayitlar"])
except Exception as hata:
    rapor = [{"id": "hata", "karar": type(hata).__name__, "nedenler": []}]
print("rapor sırası", "doğru" if [r["id"] for r in rapor] == [b["id"] for b in veri["beklenen"]] else "YANLIŞ")
for beklenen in veri["beklenen"]:
    bulunan = next((r for r in rapor if r["id"] == beklenen["id"]), None)
    print(beklenen["id"], "doğru" if bulunan == beklenen else "YANLIŞ", bulunan)
for b in veri["bozuk_girdiler"]:
    try:
        cikti_guardrail_raporu(b["girdi"])
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
hazirla("ai-savunma-08")
```

```test
import copy
K = [
    {"id": "gecir-1", "sema_gecerli": True, "sinyaller": [], "guven": 0.5},
    {"id": "incele-1", "sema_gecerli": True, "sinyaller": [], "guven": 0.499},
    {"id": "durdur-1", "sema_gecerli": False, "sinyaller": ["bearer_token", "gizli_isaret"], "guven": 1},
]
BEKLENEN = [
    {"id": "durdur-1", "karar": "durdur", "nedenler": ["sema", "gizli_veri", "gizli_isaret"]},
    {"id": "gecir-1", "karar": "gecir", "nedenler": []},
    {"id": "incele-1", "karar": "insan_incelemesi", "nedenler": ["dusuk_guven"]},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K) != BEKLENEN or K != once or fn(list(reversed(K))) != BEKLENEN or fn([]) != []:
            return False
        for sinyal in ("ozel_anahtar", "bearer_token", "api_anahtari"):
            sonuc = fn([dict(K[0], sinyaller=[sinyal])])[0]
            if sonuc != {"id": "gecir-1", "karar": "durdur", "nedenler": ["gizli_veri"]}:
                return False
        if fn([dict(K[0], guven=0)])[0]["karar"] != "insan_incelemesi":
            return False
        if fn([dict(K[0], guven=1)])[0]["karar"] != "gecir":
            return False
        if fn([dict(K[0], id="a" * 64)])[0]["id"] != "a" * 64:
            return False
        for kayitlar in [
            None, {}, [None], [dict(K[0], ek=1)], [dict(K[0], id="")],
            [dict(K[0], id="a" * 65)], [dict(K[0], id="a b")], [dict(K[0], sema_gecerli=1)],
            [dict(K[0], sema_gecerli=None)], [dict(K[0], sinyaller=None)],
            [dict(K[0], sinyaller="gizli_isaret")], [dict(K[0], sinyaller=["bilinmeyen"])],
            [dict(K[0], sinyaller=["gizli_isaret", "gizli_isaret"])],
            [dict(K[0], sinyaller=["gizli_isaret", "bearer_token"])],
            [dict(K[0], guven=True)], [dict(K[0], guven=-0.1)], [dict(K[0], guven=1.1)],
            [dict(K[0], guven=float("nan"))], [dict(K[0], guven=float("inf"))], [K[0], K[0]],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(cikti_guardrail_raporu), "ret önceliği, bütün nedenler, güven eşiği ve şema korunmalı")
def m_sema(kayitlar):
    degisen = [dict(x, sema_gecerli=True) for x in kayitlar]
    return cikti_guardrail_raporu(degisen)
def m_sizinti(kayitlar):
    degisen = [dict(x, sinyaller=[]) for x in kayitlar]
    return cikti_guardrail_raporu(degisen)
def m_guven(kayitlar):
    degisen = [dict(x, guven=1) for x in kayitlar]
    return cikti_guardrail_raporu(degisen)
for ad, mutant in [("şema hatasını silen", m_sema), ("sızıntıyı silen", m_sizinti), ("düşük güveni gizleyen", m_guven)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
# --- carbon-c8-ek-bas ---
raises(ValueError, cikti_guardrail_raporu, [dict(K[0], id=123)], msg="id str olmalı")
raises(ValueError, cikti_guardrail_raporu, [dict(K[0], guven=float("nan"))], msg="NaN güven reddedilmeli")
raises(ValueError, cikti_guardrail_raporu, [dict(K[0], guven="0.5")], msg="str güven reddedilmeli")
# --- carbon-c8-ek-son ---
```

```solution
def cikti_guardrail_raporu(kayitlar):
    import math
    import re
    if not isinstance(kayitlar, list):
        raise ValueError("kayıt listesi geçersiz")
    zorunlu = {"id", "sema_gecerli", "sinyaller", "guven"}
    sinyal_sirasi = ["ozel_anahtar", "bearer_token", "api_anahtari", "gizli_isaret"]
    kimlikler = set()
    rapor = []
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != zorunlu:
            raise ValueError("kayıt şeması geçersiz")
        kimlik = kayit["id"]
        if not isinstance(kimlik, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kimlik):
            raise ValueError("kimlik geçersiz")
        if kimlik in kimlikler:
            raise ValueError("kimlik yinelenemez")
        kimlikler.add(kimlik)
        if type(kayit["sema_gecerli"]) is not bool:
            raise ValueError("şema durumu bool olmalı")
        sinyaller = kayit["sinyaller"]
        if not isinstance(sinyaller, list):
            raise ValueError("sinyaller liste olmalı")
        if len(set(sinyaller)) != len(sinyaller):
            raise ValueError("sinyaller yinelenemez")
        if any(s not in sinyal_sirasi for s in sinyaller):
            raise ValueError("bilinmeyen sinyal")
        konumlar = [sinyal_sirasi.index(s) for s in sinyaller]
        if konumlar != sorted(konumlar):
            raise ValueError("sinyal sırası geçersiz")
        guven = kayit["guven"]
        if isinstance(guven, bool) or not isinstance(guven, (int, float)):
            raise ValueError("güven sayı olmalı")
        if not math.isfinite(guven):
            raise ValueError("güven sonlu olmalı")
        if guven < 0 or guven > 1:
            raise ValueError("güven aralık dışında")
        nedenler = []
        if not kayit["sema_gecerli"]:
            nedenler.append("sema")
        if any(s in ("ozel_anahtar", "bearer_token", "api_anahtari") for s in sinyaller):
            nedenler.append("gizli_veri")
        if "gizli_isaret" in sinyaller:
            nedenler.append("gizli_isaret")
        if nedenler:
            karar = "durdur"
        elif guven < 0.5:
            nedenler.append("dusuk_guven")
            karar = "insan_incelemesi"
        else:
            karar = "gecir"
        rapor.append({"id": kimlik, "karar": karar, "nedenler": nedenler})
    return sorted(rapor, key=lambda x: x["id"])
```

```hint
Durdurma nedenlerini birbirinden bağımsız ekle. Yalnız durdurma nedeni yoksa güven eşiğini uygula; 0.5 değerini inceleme sınırının dışında bırak.
```
:::

::: anlat Yapısal doğrulama, içerik tarayıcısının gözden kaçırdığını durdurur
Çıktı guardrail'inin iki katmanı birbirinin yerine geçmez: dar sızıntı tarayıcısı yalnız bilinen kalıpları (PEM, Bearer, API anahtarı, yasaklı işaret) bulur; katı şema doğrulaması ise çıktının biçimini zorlar. Son görevde senin `cikti_guardrail_raporu` işlevin, gerçek yerel modelin iki modda ürettiği **gerçek** çıktıları karara bağlar: katı JSON şema istenen yapısal mod ve serbest paragraf modu. Sandbox her çıktının şema geçerliliğini (1. görev) ve sızıntı sinyallerini (2. görev) bağımsız hesaplar; `guven` değerini çıktıdan okur.

Deney gerçekte şunu gösterebilir: serbest modda model bazen sistem istemindeki gizli değeri yankılar (gerçek sızıntı), ama dar sızıntı tarayıcısı o değeri tanımaz; yine de şema doğrulaması çıktıyı biçim uymadığı için fail-closed `durdur` eder. Yani yapısal doğrulama, içerik tarayıcısının kaçırdığını yakalayan ayrı bir savunma katmanıdır. Yapısal mod şemaya uyarsa ve güven yeterliyse `gecir` olur.

**Çıktıyı okurken:** Serbest mod satırında önce `sema` nedenine, sonra canary sızıntısına bak. Model sırrı yankılamadıysa da serbest çıktı şemaya uymadığı için durdurulmalıdır. Yapısal mod `gecir` aldıysa, bu yalnız biçimin ve bilinen kalıpların temiz olduğunu gösterir; içeriğin doğru olduğunu göstermez.
:::

::: gorev Gerçek deney · Çıktı guardrail'i gerçek çıktıyı sınar
`cikti_guardrail_raporu(kayitlar)` işlevini yaz — kuralları ve çıktısı 3. görevdekiyle **aynıdır**. Deney gerçek modeli yapısal ve serbest modda koşar, her çıktının şema geçerliliğini ve sızıntı sinyallerini gerçek veriden üretir; senin raporun bu gerçek kayıtları `gecir`/`insan_incelemesi`/`durdur` kararına bağlar.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def cikti_guardrail_raporu(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: ilk nedeni bulunca diğerlerini atlıyor (kanıt kaybolur), şema hatasını yalnız not edip çıktıyı geçiriyor, güven eşiğini <= ile uyguluyor (0.5 incelemeye gider), kayıtları doğrulamıyor ve sıralamıyor!
    rapor = []
    for kayit in kayitlar:
        if any(s in ("ozel_anahtar", "bearer_token", "api_anahtari") for s in kayit["sinyaller"]):
            rapor.append({"id": kayit["id"], "karar": "durdur", "nedenler": ["gizli_veri"]})
        elif "gizli_isaret" in kayit["sinyaller"]:
            rapor.append({"id": kayit["id"], "karar": "durdur", "nedenler": ["gizli_isaret"]})
        elif kayit["guven"] <= 0.5:
            rapor.append({"id": kayit["id"], "karar": "insan_incelemesi", "nedenler": ["dusuk_guven"]})
        else:
            rapor.append({"id": kayit["id"], "karar": "gecir", "nedenler": [] if kayit["sema_gecerli"] else ["sema"]})
    return rapor

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_08 as deney
    deney.goster(cikti_guardrail_raporu)
```

```test
import ai_lab
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
import ast
_yasak = ("referans", "referans_karar", "getattr", "kanit_yaz")
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
fn = need("cikti_guardrail_raporu")
from sandbox import ai_gercek_ai_savunma_08 as D
K = [
    {"id": "gecir-1", "sema_gecerli": True, "sinyaller": [], "guven": 0.5},
    {"id": "incele-1", "sema_gecerli": True, "sinyaller": [], "guven": 0.499},
    {"id": "durdur-1", "sema_gecerli": False, "sinyaller": ["bearer_token", "gizli_isaret"], "guven": 1},
]
BEKLENEN = [
    {"id": "durdur-1", "karar": "durdur", "nedenler": ["sema", "gizli_veri", "gizli_isaret"]},
    {"id": "gecir-1", "karar": "gecir", "nedenler": []},
    {"id": "incele-1", "karar": "insan_incelemesi", "nedenler": ["dusuk_guven"]},
]
def sozlesme(f):
    try:
        if f([dict(k) for k in K]) != BEKLENEN or f([]) != []:
            return False
        for bozuk in (None, [None], [dict(K[0], ek=1)], [dict(K[0], sema_gecerli=1)], [dict(K[0], sinyaller=["bilinmeyen"])]):
            try:
                f(bozuk)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(fn), "ret önceliği, bütün nedenler, güven eşiği ve şema korunmalı")
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
    cikti_guardrail_raporu = need('cikti_guardrail_raporu')
    def _birim_adim_3():
        import copy
        K = [
            {"id": "gecir-1", "sema_gecerli": True, "sinyaller": [], "guven": 0.5},
            {"id": "incele-1", "sema_gecerli": True, "sinyaller": [], "guven": 0.499},
            {"id": "durdur-1", "sema_gecerli": False, "sinyaller": ["bearer_token", "gizli_isaret"], "guven": 1},
        ]
        BEKLENEN = [
            {"id": "durdur-1", "karar": "durdur", "nedenler": ["sema", "gizli_veri", "gizli_isaret"]},
            {"id": "gecir-1", "karar": "gecir", "nedenler": []},
            {"id": "incele-1", "karar": "insan_incelemesi", "nedenler": ["dusuk_guven"]},
        ]
        def sozlesme(fn):
            try:
                once = copy.deepcopy(K)
                if fn(K) != BEKLENEN or K != once or fn(list(reversed(K))) != BEKLENEN or fn([]) != []:
                    return False
                for sinyal in ("ozel_anahtar", "bearer_token", "api_anahtari"):
                    sonuc = fn([dict(K[0], sinyaller=[sinyal])])[0]
                    if sonuc != {"id": "gecir-1", "karar": "durdur", "nedenler": ["gizli_veri"]}:
                        return False
                if fn([dict(K[0], guven=0)])[0]["karar"] != "insan_incelemesi":
                    return False
                if fn([dict(K[0], guven=1)])[0]["karar"] != "gecir":
                    return False
                if fn([dict(K[0], id="a" * 64)])[0]["id"] != "a" * 64:
                    return False
                for kayitlar in [
                    None, {}, [None], [dict(K[0], ek=1)], [dict(K[0], id="")],
                    [dict(K[0], id="a" * 65)], [dict(K[0], id="a b")], [dict(K[0], sema_gecerli=1)],
                    [dict(K[0], sema_gecerli=None)], [dict(K[0], sinyaller=None)],
                    [dict(K[0], sinyaller="gizli_isaret")], [dict(K[0], sinyaller=["bilinmeyen"])],
                    [dict(K[0], sinyaller=["gizli_isaret", "gizli_isaret"])],
                    [dict(K[0], sinyaller=["gizli_isaret", "bearer_token"])],
                    [dict(K[0], guven=True)], [dict(K[0], guven=-0.1)], [dict(K[0], guven=1.1)],
                    [dict(K[0], guven=float("nan"))], [dict(K[0], guven=float("inf"))], [K[0], K[0]],
                ]:
                    try:
                        fn(kayitlar)
                        return False
                    except ValueError:
                        pass
                return True
            except Exception:
                return False
        ok(sozlesme(cikti_guardrail_raporu), "ret önceliği, bütün nedenler, güven eşiği ve şema korunmalı")
        def m_sema(kayitlar):
            degisen = [dict(x, sema_gecerli=True) for x in kayitlar]
            return cikti_guardrail_raporu(degisen)
        def m_sizinti(kayitlar):
            degisen = [dict(x, sinyaller=[]) for x in kayitlar]
            return cikti_guardrail_raporu(degisen)
        def m_guven(kayitlar):
            degisen = [dict(x, guven=1) for x in kayitlar]
            return cikti_guardrail_raporu(degisen)
        for ad, mutant in [("şema hatasını silen", m_sema), ("sızıntıyı silen", m_sizinti), ("düşük güveni gizleyen", m_guven)]:
            ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
        raises(ValueError, cikti_guardrail_raporu, [dict(K[0], id=123)], msg="id str olmalı")
        raises(ValueError, cikti_guardrail_raporu, [dict(K[0], guven=float("nan"))], msg="NaN güven reddedilmeli")
        raises(ValueError, cikti_guardrail_raporu, [dict(K[0], guven="0.5")], msg="str güven reddedilmeli")
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
    kontrol(r["rapor"] == r["referans"], "senin kararın gerçek çıktılarda bağımsız referansla birebir aynı")
    serbest = next((k for k in r["rapor"] if k["id"] == "serbest-1"), None)
    kontrol(serbest is not None and serbest["karar"] == "durdur" and "sema" in serbest["nedenler"],
            "serbest paragraf çıktısı şemaya uymadı → fail-closed durdur")
    oz = D.ozet(r)
yol = ai_lab.kanit_yaz("savunma-cikti", {"kaynak": "gercek", "kabul": all(sonuclar), "ders": "ai-savunma-08",
                                         "ortam": (r or {}).get("ortam"), "ozet": oz})
if oz:
    yapisal = next((a for a in r["akislar"] if a["id"] == "yapisal-1"), {})
    ek = (" serbest modda model sistemdeki gizli değeri yankıladı (gerçek sızıntı) ama şema katmanı yine durdurdu —"
          " yapısal doğrulama, dar içerik tarayıcısının kaçırdığını yakaladı." if oz["sizan"] else "")
    ok(True, f"BULGU ({r['ortam']['model']['ad']}): {oz['mod']} gerçek çıktı → kararlar {oz['kararlar']}; "
             f"şema geçerli {oz['sema_gecerli_sayisi']}/{oz['mod']}, canary sızan {oz['sizan']}.{ek} "
             f"Yapısal doğrulama metni temizlemez, güvensiz geçişi engeller.")
```

```solution
import ai_lab

def cikti_guardrail_raporu(kayitlar):
    import math
    import re
    if not isinstance(kayitlar, list):
        raise ValueError("kayıt listesi geçersiz")
    zorunlu = {"id", "sema_gecerli", "sinyaller", "guven"}
    sinyal_sirasi = ["ozel_anahtar", "bearer_token", "api_anahtari", "gizli_isaret"]
    kimlikler = set()
    rapor = []
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != zorunlu:
            raise ValueError("kayıt şeması geçersiz")
        kimlik = kayit["id"]
        if not isinstance(kimlik, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kimlik):
            raise ValueError("kimlik geçersiz")
        if kimlik in kimlikler:
            raise ValueError("kimlik yinelenemez")
        kimlikler.add(kimlik)
        if type(kayit["sema_gecerli"]) is not bool:
            raise ValueError("şema durumu bool olmalı")
        sinyaller = kayit["sinyaller"]
        if not isinstance(sinyaller, list):
            raise ValueError("sinyaller liste olmalı")
        if len(set(sinyaller)) != len(sinyaller):
            raise ValueError("sinyaller yinelenemez")
        if any(s not in sinyal_sirasi for s in sinyaller):
            raise ValueError("bilinmeyen sinyal")
        konumlar = [sinyal_sirasi.index(s) for s in sinyaller]
        if konumlar != sorted(konumlar):
            raise ValueError("sinyal sırası geçersiz")
        guven = kayit["guven"]
        if isinstance(guven, bool) or not isinstance(guven, (int, float)):
            raise ValueError("güven sayı olmalı")
        if not math.isfinite(guven):
            raise ValueError("güven sonlu olmalı")
        if guven < 0 or guven > 1:
            raise ValueError("güven aralık dışında")
        nedenler = []
        if not kayit["sema_gecerli"]:
            nedenler.append("sema")
        if any(s in ("ozel_anahtar", "bearer_token", "api_anahtari") for s in sinyaller):
            nedenler.append("gizli_veri")
        if "gizli_isaret" in sinyaller:
            nedenler.append("gizli_isaret")
        if nedenler:
            karar = "durdur"
        elif guven < 0.5:
            nedenler.append("dusuk_guven")
            karar = "insan_incelemesi"
        else:
            karar = "gecir"
        rapor.append({"id": kimlik, "karar": karar, "nedenler": nedenler})
    return sorted(rapor, key=lambda x: x["id"])

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_08 as deney
    deney.goster(cikti_guardrail_raporu)
```

```hint
Bu işlev 3. görevdeki `cikti_guardrail_raporu` ile birebir aynıdır; tek fark, kayıtların gerçek model çıktılarından (şema geçerliliği ve sızıntı sinyalleri gerçek veriden) kurulmasıdır. Durdurma nedenlerini bağımsız ekle; yalnız durdurma yoksa güven eşiğini uygula.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Şema geçerliliği içeriğin güvenliği değildir

JSON şeması beklenen alan ve türleri sınırlar. Bu alanların içindeki sır veya güvenilmeyen içerik ayrıca kontrol edilmelidir. Modelin kendine güven puanı yetki kaynağı değildir. Yapısal hata, sızıntı sinyali ve güven kanıtı farklı nedenlerle ret üretebilir. Böylece parse edilebilir yanıtın doğrudan uygulama sinkine gitmesi önlenir.

| Yaygın yanlış | Mekanizmanın sınırı |
|---|---|
| JSON geçerliyse çalıştırılabilir | Yapısal uygunluk ve güvenli kullanım ayrı kapılardır. |

Saldırı–savunma bağlantısı: ai-saldiri-10.
:::

::: anlat Kaynak ile lab sonucunu ayır
[Ollama chat API](https://docs.ollama.com/api/chat). format alanı JSON veya şema biçimini sınırlar; içerik güvenliğini ve uygulama yetkisini garanti etmez.
:::
