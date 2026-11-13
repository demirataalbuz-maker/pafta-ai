---
id: ai-ile-guvenlik-14
title: "Yıkıcı Eylemlerde İnsan Onayı (HITL) ve İmzalı Görev Kapısı"
summary: Güvenlik ajanının IP engelleme veya hesap kapatma gibi yıkıcı eylemleri yalnızca parametreye bağlı HMAC-SHA256 insan onayı jetonu doğrulandığında çalıştırmasını sağla.
esleme: ai-savunma-12, ai-savunma-13
timeout: 300
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et
Güvenlik operasyonlarında otomatik olay müdahale (Incident Response - IR) ve SOAR (Güvenlik Orkestrasyonu, Otomasyon ve Müdahale) platformları, bir tehdit algılandığında hızlı karşı tedbirler uygulayabilir. Günümüzde bu orkestrasyon kararları giderek daha fazla otonom büyük dil modeli (LLM) ajanlarına emanet edilmektedir.

Ancak bir güvenlik ajanına `ip_engelle`, `hesap_kapat`, `guvenlik_duvari_kurali_yaz` veya `servis_durdur` gibi durum değiştiren araçlar bağlandığında sistemin karşılaşacağı en ölümcül tehlike, **insan onay mekanizmasını yalnızca `"onaylandi": true` gibi bağlamsız bir Boole bayrağına bırakmaktır**.

### 1. Parametre Değiştirme ve "confused deputy" (Confused Deputy) Tuzağı
Basit bir onay mekanizmasında insan analist meşru bir saldırgan IP adresi olan `10.20.9.88` için engelleme onayını tıklar. Ancak modelin otonom döngüsünde halüsinasyon, yarış durumu (race condition / TOCTOU) veya araya giren dolaylı bir istem enjeksiyonu meydana gelirse, ajan onay bayrağı (`onaylandi: true`) elindeyken parametreyi değiştirebilir: saldırgan IP'si yerine kurumsal ağ geçidi (`10.20.1.1`) veya etki alanı denetleyicisi (Domain Controller) hedefe yazılabilir. Yürütücü katman yalnızca bayrağa baktığı için meşru altyapıyı felç eder ve tüm şirketi çevrimdışı bırakır.

Bu nedenle güvenlik mühendisliğinde temel kural şudur: **Yıkıcı bir eylem için verilen insan onayı, eylemin hedef parametrelerine ve istek kimliğine kriptografik olarak sıkı sıkıya bağlı (parameter-bound HMAC token) olmak zorundadır.**

### 2. Aracın Altında Ne Olur: Kriptografik Parametreye Bağlı HITL Kapısı
Güvenilir bir Human-in-the-Loop (HITL) onay kapısı üç katmanlı bir mimariyle kurulur:
1. **Kanonik Görev İmzası (`gorev_imzasi_uret`):**
   - İnsan operatör onay verdiğinde, onay jetonu soyut bir izin dizesi olarak üretilmez. İstek kimliği, çağrılacak araç ve hedef parametresi deterministik kanonik bir dizgede birleştirilir: `json.dumps(["pafta-hitl-v2", istek_id, arac, hedef], ensure_ascii=False, separators=(",", ":"))`.
   - Bu kanonik mesaj, yalnızca yetkili operatör konsolu ve güvenlik yürütücüsü tarafından bilinen `gizli_anahtar` ile `HMAC-SHA256` algoritmasından geçirilerek 64 karakterlik onaltılık (`hexdigest`) özet üretilir.
2. **HITL Doğrulama Kapısı (`hitl_kapisi_dogrula`):**
   - **Salt-Okunur Eylemler:** `risk_sinifi == "salt_okunur"` olan sorgulama araçları durum değiştirmediği için onay jetonu aranmaksızın serbestçe yürütülür (`"salt_okunur_serbest"`).
   - **Yıkıcı Eylemler:** `risk_sinifi == "yikici"` olan eylemlerde `onay_jetonu` boşsa istek derhal `"eksik_onay_jetonu"` nedeniyle reddedilir.
   - Jeton mevcutsa, yürütücü anlık olarak istek parametrelerinden (`iid`, `arac`, `hedef`) beklenen HMAC özetini hesaplar ve gelen jeton ile `hmac.compare_digest` üzerinden karşılaştırır. İstek kimliği, araç adı veya hedef parametresinden tek bir karakter bile farklıysa imza tutmaz ve `"imza_uyumsuz"` kararıyla engellenir.
3. **Müdahale Kuyruğu Yürütücüsü (`mudahale_kuyrugu_yurut`):**
   - Gelen tüm müdahale istekleri sırayla HITL kapısından geçirilir. Onaylanan geçerli çağrılar `uygulanan_idleri` listesine, reddedilenler ise nedenleriyle birlikte `reddedilenler` sözlüğüne kaydedilir.

### 3. Çıktı Nasıl Okunur: HITL Denetim İzi
- `uygulanan_idleri`: Kriptografik onay kapısını başarıyla geçen ve fiilen yürütülen eylemlerin kimlikleri.
- `reddedilenler`: Güvenlik kapısına takılan eylemlerin kimlikleri ve engellenme nedenleri (`eksik_onay_jetonu`, `imza_uyumsuz`).

### 4. Saldırgan Neyi Dener? (Threat Vectors)
- **Jeton Yeniden Kullanımı ve Taşıma (Token Replay / Cross-Request Replay):** Saldırgan, meşru bir IP (`req-102: 10.20.9.88`) için üretilmiş onay jetonunu ağ trafiğinden veya loglardan ele geçirip kurumsal ağ geçidini hedefleyen başka bir isteğe (`req-104: 10.20.1.1`) yapıştırmayı dener. Kanonik mesajda `istek_id` ve `hedef` birlikte yer aldığından imza doğrulaması çöker.
- **Zamanlama Saldırıları (Timing Attacks):** Jeton karşılaştırmasında standart `==` operatörü kullanılırsa dizgeler baştan sona karakter karakter karşılaştırılır ve ilk uyuşmazlıkta durulur. Saldırgan mikrosaniyelik yanıt süresi farklarından jetonun karakterlerini tahmin edebilir. Savunmada `hmac.compare_digest` kullanılarak sabit-zamanlı (constant-time) güvenli karşılaştırma sağlanır.
- **Onay Yorgunluğu (Approval Fatigue):** Analistin ekranına yüzlerce sahte onay bildirimi göndererek analisti dikkatsizce rastgele onay vermeye teşvik etmek.

### 5. Savunma Neden Kırılır ve Sık Yapılan Geliştirici Hataları
- **Parametreleri İmzaya Dahil Etmemek:** Yalnızca `istek_id` alanını imzalamak, hedefin sonradan değiştirilmesini engelleyemez. Kanonik şablon mutlaka tüm kritik argümanları içermelidir.
- **Sabit-Zamanlı Karşılaştırmayı İhmal Etmek:** `==` kullanımı kriptografik doğrulamada kabul edilemez bir zafiyettir.
- **Boşluk ve Tip Denetimlerini Atlamak:** `strip()` yapılmaması veya parametrelerin `None` olabilmesi imza hesaplamasında `TypeError` veya sessiz güvenlik açıklarına yol açar.

| Gerçek araç / model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| SOAR onay kuyruğunu, `hmac.new(..., hashlib.sha256)` ile parametreye bağlı görev imzasını ve yerel Ollama (`qwen3`) müdahale akışını | İlk üç görevde `mudahale_istekleri.json` içindeki **sentetik** müdahale isteklerini ve HMAC jetonlarını; son görevde canlı `ai_lab.SohbetOturumu` ile HITL kapısı deneyini | Yalnızca HMAC doğrulamasının, insan operatörün yanlış hedefi dikkatsizce onaylamasını (sosyal mühendislik / onay yorgunluğu) tek başına engelleyebileceğini söyleyemez |
| Parametreye bağlı kanonik görev imzası (`json.dumps(["pafta-hitl-v2", istek_id, arac, hedef], ensure_ascii=False, separators=(",", ":"))`) ve sabit-zamanlı doğrulama (`hmac.compare_digest`) | `gorev_imzasi_uret` ve `hitl_kapisi_dogrula` işlevleri | İmzalı onay jetonunun yetkisiz sızdırılması durumunda gizli anahtarın rotasyonunu veya çok faktörlü operatör doğrulamasını (MFA) tek başına çözebileceğini söyleyemez |
| Yıkıcı eylemlerde müdahale kuyruğu yürütücüsü ve triyaj ayrımı (`uygulanan_idleri` vs `reddedilenler`) | `mudahale_kuyrugu_yurut` ile onaylı ve engellenen çağrıların yönetimi | Kuyruk yürütücüsünün hedef sistemde uygulanan eylemin (örn. iptables kuralı) ağda beklenmeyen bir yan etki veya kesinti yaratmayacağını garanti ettiğini söyleyemez |

> [!NOT]
> **Kapsam ve dürüstlük sınırı:** İlk üç görevdeki `mudahale_istekleri.json` dosyası ve içindeki `gizli_anahtar` **sentetik** eğitim verisidir; hiçbir gerçek güvenlik duvarı veya kullanıcı hesabı üzerinde işlem yapılmaz ve dosyalar her çalıştırmada (`setup`) yeniden yüklenir (kalıcılık yoktur). Dördüncü görevde yerel Ollama modeliyle canlı HITL kapısı ve imza doğrulama deneyi yürütülür.
:::

::: anlat Parametreye bağlı imzalı HITL kapısı üç adımda çalışır
Yıkıcı araç çağrılarını koruyan **Human-in-the-Loop (`HITL`)** kapısı şöyle kurulur:

1. **Kanoniğe Bağlı Görev İmzası (`gorev_imzasi_uret`):** İstek kimliği, araç adı ve hedef parametresi `json.dumps(["pafta-hitl-v2", istek_id, arac, hedef], ensure_ascii=False, separators=(",", ":"))` dizgesinde birleştirilir ve operatörün `gizli_anahtar` değeriyle `HMAC-SHA256` (`hexdigest`) imzası üretilir.
2. **HITL Doğrulama Kapısı (`hitl_kapisi_dogrula`):**
   - `risk_sinifi == "salt_okunur"` olan çağrılar imza aranmadan `"salt_okunur_serbest"` gerekçesiyle onaylanır.
   - `risk_sinifi == "yikici"` olan çağrılarda `onay_jetonu` boşsa `"eksik_onay_jetonu"` ile reddedilir; doluysa beklenen imza ile `hmac.compare_digest` üzerinden karşılaştırılır. Hedef veya araç değiştirilmişse imza tutmaz ve `"imza_uyumsuz"` döner.
3. **Müdahale Kuyruğu Yürütücüsü (`mudahale_kuyrugu_yurut`):** Kuyruktaki her isteği sırayla HITL kapısından geçirir; onaylananları `uygulanan_idleri` listesine, reddedilenleri `reddedilenler` sözlüğüne yazar.
:::

::: anlat Bulguyu sınırlı ve doğrulanabilir yaz: başka isteğin jetonu yeni hedefe taşınamaz
Saldırgan veya hatalı ajan, `req-102` (`10.20.9.88` engelleme) için alınmış geçerli bir onay jetonunu kopyalayıp `req-104` (`10.20.1.1` engelleme) isteğine yapıştırdığında, kanonik mesaj içinde hem `istek_id` hem de `hedef` bulunduğu için imza doğrulaması deterministik olarak başarısız olur.
:::

::: tahmin Parametre değiştiğinde HMAC imza karşılaştırmasını tahmin et
Aşağıdaki Python kodunun çıktısını tahmin et:

```python
import json
import hashlib, hmac

anahtar = b"sentetik-anahtar"
jeton = hmac.new(anahtar, json.dumps(["pafta-hitl-v2", "req-1", "ip_engelle", "10.0.0.99"], ensure_ascii=False, separators=(",", ":")).encode("utf-8"), hashlib.sha256).hexdigest()
kontrol_ayni = hmac.compare_digest(
    jeton,
    hmac.new(anahtar, json.dumps(["pafta-hitl-v2", "req-1", "ip_engelle", "10.0.0.99"], ensure_ascii=False, separators=(",", ":")).encode("utf-8"), hashlib.sha256).hexdigest(),
)
kontrol_degismis = hmac.compare_digest(
    jeton,
    hmac.new(anahtar, json.dumps(["pafta-hitl-v2", "req-1", "ip_engelle", "10.0.0.1"], ensure_ascii=False, separators=(",", ":")).encode("utf-8"), hashlib.sha256).hexdigest(),
)
print(kontrol_ayni, kontrol_degismis)
```

???

```cikti
True False
```

Hedef IP `10.0.0.99` yerine `10.0.0.1` yapıldığında üretilen HMAC özeti tamamen değişir ve `compare_digest` `False` döndürür.
:::

::: gorev 1 · İstek kimliği, araç ve hedefe bağlı HMAC-SHA256 görev imzası üret
`gorev_imzasi_uret(istek_id, arac, hedef, gizli_anahtar)` işlevini yaz.

Kurallar:
- Dört parametrenin tamamı boş olmayan (`strip()` sonrası dolu) `str` olmalıdır; aksi halde `ValueError` yükselt.
- Kanonik mesajı tam olarak `json.dumps(["pafta-hitl-v2", istek_id, arac, hedef], ensure_ascii=False, separators=(",", ":"))` biçiminde oluştur.
- `hmac.new(gizli_anahtar.encode("utf-8"), mesaj.encode("utf-8"), hashlib.sha256).hexdigest()` değerini döndür.

```starter
import hashlib
import hmac
import json
from ai_ile_guvenlik_veri import json_yukle

veri = json_yukle("mudahale_istekleri.json")

def gorev_imzasi_uret(istek_id, arac, hedef, gizli_anahtar):
    # KUSURLU BAŞLANGIÇ KODU: hedef ve araç parametrelerini imzaya dahil etmeden boş imza döndürüyor!
    return ""

print(gorev_imzasi_uret("req-102", "ip_engelle", "10.20.9.88", veri["gizli_anahtar"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-14")
```

```test
need("gorev_imzasi_uret")

def sozlesme(fn):
    try:
        imza1 = fn("req-102", "ip_engelle", "10.20.9.88", "pafta-hitl-sentetik-anahtar-2026")
        if imza1 != "acb88f7dfb510219f91db1f3cce397b7be2eeaa9dd8853a91a3abc3586c5b440":
            return False

        imza2 = fn("req-102", "ip_engelle", "10.20.1.1", "pafta-hitl-sentetik-anahtar-2026")
        if imza1 == imza2 or len(imza2) != 64:
            return False

        for args in [
            ("", "ip_engelle", "10.0.0.1", "k"),
            ("req-1", "   ", "10.0.0.1", "k"),
            ("req-1", "ip_engelle", None, "k"),
            ("req-1", "ip_engelle", "10.0.0.1", ""),
            (123, "ip_engelle", "10.0.0.1", "k"),
        ]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(gorev_imzasi_uret), "gorev_imzasi_uret: istek_id, arac ve hedefe bağlı HMAC-SHA256 imzası doğru")
ok(not sozlesme(lambda i, a, h, k: "acb88f7dfb510219f91db1f3cce397b7be2eeaa9dd8853a91a3abc3586c5b440"), "mutasyon: sabit imza döndüren işlev reddedilmeli")
import json as _j14, hmac as _h14, hashlib as _s14
_k14="synthetic"
_a14=("a:b","c","d");_b14=("a","b:c","d")
_expected14=_h14.new(_k14.encode(),_j14.dumps(["pafta-hitl-v2",*_a14],ensure_ascii=False,separators=(",", ":")).encode(),_s14.sha256).hexdigest()
ok(gorev_imzasi_uret(*_a14,_k14)==_expected14,"v2 JSON alan sınırları ve domain etiketi")
ok(gorev_imzasi_uret(*_a14,_k14)!=gorev_imzasi_uret(*_b14,_k14),"eski ayıraç çarpışması ayrıldı")
_u14=("a","c","kullanıcı-ö")
ok(gorev_imzasi_uret(*_u14,_k14)==_h14.new(_k14.encode(),_j14.dumps(["pafta-hitl-v2",*_u14],ensure_ascii=False,separators=(",", ":")).encode(),_s14.sha256).hexdigest(),"UTF-8 ensure_ascii=False imzası")
```

```solution
import hashlib
import hmac
import json

def gorev_imzasi_uret(istek_id, arac, hedef, gizli_anahtar):
    if not all(isinstance(x, str) and bool(x.strip()) for x in (istek_id, arac, hedef, gizli_anahtar)):
        raise ValueError("tüm parametreler boş olmayan string olmalı")
    mesaj = json.dumps(["pafta-hitl-v2", istek_id, arac, hedef], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    anahtar = gizli_anahtar.encode("utf-8")
    return hmac.new(anahtar, mesaj, hashlib.sha256).hexdigest()
```

```hint
`all(isinstance(x, str) and bool(x.strip()) for x in ...)` kontrolünden sonra `hmac.new(gizli_anahtar.encode("utf-8"), json.dumps(["pafta-hitl-v2", istek_id, arac, hedef], ensure_ascii=False, separators=(",", ":")).encode("utf-8"), hashlib.sha256).hexdigest()` hesapla.
```
:::

::: gorev 2 · Müdahale isteğini HITL kapısında doğrula
`hitl_kapisi_dogrula(istek, gizli_anahtar)` işlevini yaz.

Kurallar:
- `istek`: tam olarak `{"istek_id", "arac", "hedef", "risk_sinifi", "onay_jetonu"}` anahtarlarına sahip `dict`; `istek_id`, `arac`, `hedef` boş olmayan `str`, `risk_sinifi` `("salt_okunur", "yikici")` değerlerinden biri, `onay_jetonu` ise `str` olmalıdır.
- `gizli_anahtar`: boş olmayan (`strip()` sonrası dolu) `str` olmalıdır (aksi halde `ValueError` yükselt).
- Doğrulama sırası:
  1. `risk_sinifi == "salt_okunur"` ise `{"istek_id": iid, "izin_verildi": True, "neden": "salt_okunur_serbest"}` döndür.
  2. `risk_sinifi == "yikici"` ve `onay_jetonu.strip()` boşsa `{"istek_id": iid, "izin_verildi": False, "neden": "eksik_onay_jetonu"}` döndür.
  3. Beklenen HMAC-SHA256 imzasını hesapla; `hmac.compare_digest(jeton, beklenen)` `False` ise `{"istek_id": iid, "izin_verildi": False, "neden": "imza_uyumsuz"}` döndür.
  4. İmza eşleşiyorsa `{"istek_id": iid, "izin_verildi": True, "neden": "imzali_onay_gecerli"}` döndür.

```starter
from ai_ile_guvenlik_veri import json_yukle

veri = json_yukle("mudahale_istekleri.json")

def hitl_kapisi_dogrula(istek, gizli_anahtar):
    # KUSURLU BAŞLANGIÇ KODU: yıkıcı eylemlerde onay jetonu ve imza doğrulaması yapmadan her isteği doğrudan onaylıyor!
    return {
        "istek_id": istek.get("istek_id", ""),
        "izin_verildi": True,
        "neden": "imzali_onay_gecerli",
    }

for ist in veri["istekler"]:
    print(hitl_kapisi_dogrula(ist, veri["gizli_anahtar"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-14")
```

```test
need("hitl_kapisi_dogrula")
from ai_ile_guvenlik_veri import json_yukle

VERI = json_yukle("mudahale_istekleri.json")
ANAHTAR = VERI["gizli_anahtar"]
ISTEKLER = VERI["istekler"]

def sozlesme(fn):
    try:
        if fn(ISTEKLER[0], ANAHTAR) != {"istek_id": "req-101", "izin_verildi": True, "neden": "salt_okunur_serbest"}:
            return False
        if fn(ISTEKLER[1], ANAHTAR) != {"istek_id": "req-102", "izin_verildi": True, "neden": "imzali_onay_gecerli"}:
            return False
        if fn(ISTEKLER[2], ANAHTAR) != {"istek_id": "req-103", "izin_verildi": False, "neden": "eksik_onay_jetonu"}:
            return False
        if fn(ISTEKLER[3], ANAHTAR) != {"istek_id": "req-104", "izin_verildi": False, "neden": "imza_uyumsuz"}:
            return False

        for i_in, k_in in [
            (None, ANAHTAR),
            ({}, ANAHTAR),
            (dict(ISTEKLER[0], risk_sinifi="kritik"), ANAHTAR),
            (dict(ISTEKLER[0], onay_jetonu=None), ANAHTAR),
            (ISTEKLER[0], ""),
            (ISTEKLER[0], "   "),
            (ISTEKLER[0], None),
        ]:
            try:
                fn(i_in, k_in)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(hitl_kapisi_dogrula), "hitl_kapisi_dogrula: salt-okunur, eksik jeton ve imza uyumsuzluğu durumlarını doğru ayırmalı")
ok(not sozlesme(lambda i, k: {"istek_id": i["istek_id"], "izin_verildi": True, "neden": "imzali_onay_gecerli"}), "mutasyon: imzasız yıkıcı eylemi onaylayan işlev reddedilmeli")
import json as _j14, hmac as _h14, hashlib as _s14
_k14="synthetic"
_token14=_h14.new(_k14.encode(),_j14.dumps(["pafta-hitl-v2","a:b","c","d"],ensure_ascii=False,separators=(",", ":")).encode(),_s14.sha256).hexdigest()
_original14=dict(istek_id="a:b",arac="c",hedef="d",risk_sinifi="yikici",onay_jetonu=_token14)
_other14=dict(istek_id="a",arac="b:c",hedef="d",risk_sinifi="yikici",onay_jetonu=_token14)
ok(hitl_kapisi_dogrula(_original14,_k14)["izin_verildi"] is True,"v2 jeton kendi parametrelerine bağlı")
ok(hitl_kapisi_dogrula(_other14,_k14)["neden"]=="imza_uyumsuz","aynı ayıraç mesajına sahip farklı alanlar reddedilir")
ok(hitl_kapisi_dogrula(dict(_original14,onay_jetonu="onay-ş"),_k14)["neden"]=="imza_uyumsuz","Unicode jeton TypeError üretmez")
for _f14 in ("istek_id","arac","hedef"):
    for _bad14 in ("", "   ", 123):
        raises(ValueError, lambda f=_f14,b=_bad14: hitl_kapisi_dogrula(dict(_original14,**{f:b}),_k14), msg="alan türü ve boşluk doğrulaması: "+_f14)
        raises(ValueError, lambda f=_f14,b=_bad14: hitl_kapisi_dogrula(dict(_original14,risk_sinifi="salt_okunur",**{f:b}),_k14), msg="salt_okunur alan doğrulaması: "+_f14)
_utok14=_h14.new(_k14.encode(),_j14.dumps(["pafta-hitl-v2","u-1","c","kullanıcı-ö"],ensure_ascii=False,separators=(",", ":")).encode(),_s14.sha256).hexdigest()
ok(hitl_kapisi_dogrula(dict(_original14,istek_id="u-1",hedef="kullanıcı-ö",onay_jetonu=_utok14),_k14)["izin_verildi"] is True,"Unicode hedef ensure_ascii=False ile doğrulanır")
ok(hitl_kapisi_dogrula(dict(_original14,onay_jetonu=" "+_token14+"\t"),_k14)["izin_verildi"] is True,"jeton dış boşluğu sözleşmeye göre kaldırılır")
ok(hitl_kapisi_dogrula(dict(_original14,onay_jetonu=" \n "),_k14)=={"istek_id":"a:b","izin_verildi":False,"neden":"eksik_onay_jetonu"},"boşluk jetonu eksik onaydır")
```

```solution
import hashlib, hmac, json
ZORUNLU_ALANLAR = {"istek_id", "arac", "hedef", "risk_sinifi", "onay_jetonu"}

def _istek_kontrol(istek: dict) -> None:
    if not isinstance(istek, dict) or set(istek.keys()) != ZORUNLU_ALANLAR:
        raise ValueError('istek şeması geçersiz')
    if not all((isinstance(istek[k], str) and bool(istek[k].strip()) for k in ('istek_id', 'arac', 'hedef'))):
        raise ValueError('istek_id, arac ve hedef boş olmayan string olmalı')
    if istek['risk_sinifi'] not in ('salt_okunur', 'yikici'):
        raise ValueError('geçersiz risk_sinifi')
    if not isinstance(istek['onay_jetonu'], str):
        raise ValueError('onay_jetonu string olmalı')

def gorev_imzasi_uret(istek_id: str, arac: str, hedef: str, gizli_anahtar: str) -> str:
    if not all((isinstance(x, str) and bool(x.strip()) for x in (istek_id, arac, hedef, gizli_anahtar))):
        raise ValueError('istek_id, arac, hedef ve gizli_anahtar boş olmayan string olmalı')
    mesaj = json.dumps(['pafta-hitl-v2', istek_id, arac, hedef], ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    anahtar = gizli_anahtar.encode('utf-8')
    return hmac.new(anahtar, mesaj, hashlib.sha256).hexdigest()

def hitl_kapisi_dogrula(istek: dict, gizli_anahtar: str) -> dict:
    _istek_kontrol(istek)
    if not isinstance(gizli_anahtar, str) or not gizli_anahtar.strip():
        raise ValueError('gizli_anahtar boş olmayan string olmalı')
    iid = istek['istek_id']
    if istek['risk_sinifi'] == 'salt_okunur':
        return {'istek_id': iid, 'izin_verildi': True, 'neden': 'salt_okunur_serbest'}
    jeton = istek['onay_jetonu'].strip()
    if not jeton:
        return {'istek_id': iid, 'izin_verildi': False, 'neden': 'eksik_onay_jetonu'}
    beklenen = gorev_imzasi_uret(iid, istek['arac'], istek['hedef'], gizli_anahtar)
    if not jeton.isascii() or not hmac.compare_digest(jeton, beklenen):
        return {'istek_id': iid, 'izin_verildi': False, 'neden': 'imza_uyumsuz'}
    return {'istek_id': iid, 'izin_verildi': True, 'neden': 'imzali_onay_gecerli'}
```

```hint
`risk_sinifi == "salt_okunur"` ise doğrudan onayla; `"yikici"` ise önce boş jetonu (`"eksik_onay_jetonu"`), ardından `hmac.compare_digest(jeton, beklenen)` ile `"imza_uyumsuz"` durumunu kontrol et.
```
:::

::: gorev 3 · Müdahale kuyruğunu imzalı HITL kapısından geçirerek yürüt
`mudahale_kuyrugu_yurut(istekler, gizli_anahtar)` işlevini yaz.

Kurallar:
- `istekler`: boş olmayan `list`; her öğesi 2. görevdeki şemaya uymalı ve `istek_id` değerleri benzersiz olmalıdır.
- `gizli_anahtar`: boş olmayan (`strip()` sonrası dolu) `str` olmalıdır (aksi halde `ValueError` yükselt).
- Kuyruktaki her isteği `hitl_kapisi_dogrula` mantığıyla değerlendir:
  - `izin_verildi == True` olanların `istek_id` değerini sırasıyla `uygulanan_idleri` listesine ekle.
  - `izin_verildi == False` olanları `reddedilenler[istek_id] = neden` olarak kaydet.
- `{"uygulanan_idleri": uygulanan_idleri, "reddedilenler": reddedilenler}` sözlüğünü döndür.

```starter
from ai_ile_guvenlik_veri import json_yukle

veri = json_yukle("mudahale_istekleri.json")

def mudahale_kuyrugu_yurut(istekler, gizli_anahtar):
    # KUSURLU BAŞLANGIÇ KODU: tüm istekleri HITL kapısından geçirmeden doğrudan uygulanan listesine alıyor!
    return {
        "uygulanan_idleri": [i["istek_id"] for i in istekler],
        "reddedilenler": {},
    }

print(mudahale_kuyrugu_yurut(veri["istekler"], veri["gizli_anahtar"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-14")
```

```test
need("mudahale_kuyrugu_yurut")
from ai_ile_guvenlik_veri import json_yukle

VERI = json_yukle("mudahale_istekleri.json")
ANAHTAR = VERI["gizli_anahtar"]
ISTEKLER = VERI["istekler"]

def sozlesme(fn):
    try:
        r = fn(ISTEKLER, ANAHTAR)
        if r != {
            "uygulanan_idleri": ["req-101", "req-102"],
            "reddedilenler": {
                "req-103": "eksik_onay_jetonu",
                "req-104": "imza_uyumsuz",
            },
        }:
            return False

        for i_in, k_in in [
            (None, ANAHTAR),
            (123, ANAHTAR),
            ([], ANAHTAR),
            ([ISTEKLER[0], ISTEKLER[0]], ANAHTAR),
            (ISTEKLER, None),
            (ISTEKLER, ""),
            (ISTEKLER, "   "),
        ]:
            try:
                fn(i_in, k_in)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(sozlesme(mudahale_kuyrugu_yurut), "mudahale_kuyrugu_yurut: yalnızca salt-okunur ve geçerli imzalı yıkıcı istekleri uygulamalı")
ok(not sozlesme(lambda i, k: {"uygulanan_idleri": ["req-101", "req-102"], "reddedilenler": {}}), "mutasyon: reddedilenleri silen işlev reddedilmeli")
import json as _j14, hmac as _h14, hashlib as _s14
_k14="synthetic"
_token14=_h14.new(_k14.encode(),_j14.dumps(["pafta-hitl-v2","a:b","c","d"],ensure_ascii=False,separators=(",", ":")).encode(),_s14.sha256).hexdigest()
_q14=[dict(istek_id="a:b",arac="c",hedef="d",risk_sinifi="yikici",onay_jetonu=_token14),dict(istek_id="a",arac="b:c",hedef="d",risk_sinifi="yikici",onay_jetonu=_token14)]
ok(mudahale_kuyrugu_yurut(_q14,_k14)=={"uygulanan_idleri":["a:b"],"reddedilenler":{"a":"imza_uyumsuz"}},"kuyrukta çapraz parametre jetonu yürütülmez")
raises(ValueError, lambda: mudahale_kuyrugu_yurut([dict(_q14[0],extra=1)],_k14), msg="kuyrukta fazla alan kapıyı geçemez")
raises(ValueError, lambda: mudahale_kuyrugu_yurut(["bozuk"],_k14), msg="kuyrukta sözlük dışı öğe reddedilir")
raises(ValueError, lambda: mudahale_kuyrugu_yurut([dict(_q14[0],risk_sinifi="kritik")],_k14), msg="kuyrukta geçersiz risk_sinifi reddedilir")
raises(ValueError, lambda: mudahale_kuyrugu_yurut([dict(_q14[0],onay_jetonu=123)],_k14), msg="kuyrukta string dışı jeton reddedilir")
raises(ValueError, lambda: mudahale_kuyrugu_yurut([_q14[0]],123), msg="kuyrukta string dışı gizli_anahtar reddedilir")
raises(ValueError, gorev_imzasi_uret, "i-1", "arac", "hedef", "", msg="boş gizli anahtarla imza üretilmez")
raises(ValueError, gorev_imzasi_uret, "", "arac", "hedef", "k", msg="boş istek_id ile imza üretilmez")
raises(ValueError, hitl_kapisi_dogrula, dict(_q14[0],risk_sinifi="salt_okunur"), "   ", msg="salt okunur istekte de boş gizli anahtar reddedilir")
for _f14 in ("istek_id","arac","hedef"):
    for _bad14 in ("", "   ", 123):
        raises(ValueError, lambda f=_f14,b=_bad14: mudahale_kuyrugu_yurut([dict(_q14[0],**{f:b})],_k14), msg="kuyrukta alan şeması: "+_f14)
        raises(ValueError, lambda f=_f14,b=_bad14: mudahale_kuyrugu_yurut([dict(_q14[0],risk_sinifi="salt_okunur",**{f:b})],_k14), msg="kuyrukta salt_okunur alan şeması: "+_f14)
_utok14q=_h14.new(_k14.encode(),_j14.dumps(["pafta-hitl-v2","u-1","c","kullanıcı-ö"],ensure_ascii=False,separators=(",", ":")).encode(),_s14.sha256).hexdigest()
ok(mudahale_kuyrugu_yurut([dict(_q14[0],istek_id="u-1",hedef="kullanıcı-ö",onay_jetonu=_utok14q),dict(_q14[0],istek_id="u-2",onay_jetonu="onay-ş")],_k14)=={"uygulanan_idleri":["u-1"],"reddedilenler":{"u-2":"imza_uyumsuz"}},"kuyrukta Unicode hedef ve ASCII olmayan jeton")
ok(mudahale_kuyrugu_yurut([dict(_q14[0],onay_jetonu=" "+_token14+"\t")],_k14)["uygulanan_idleri"]==["a:b"],"kuyrukta jeton whitespace sözleşmesi")
```

```solution
import hashlib, hmac, json
ZORUNLU_ALANLAR = {"istek_id", "arac", "hedef", "risk_sinifi", "onay_jetonu"}

def _istek_kontrol(istek: dict) -> None:
    if not isinstance(istek, dict) or set(istek.keys()) != ZORUNLU_ALANLAR:
        raise ValueError('istek şeması geçersiz')
    if not all((isinstance(istek[k], str) and bool(istek[k].strip()) for k in ('istek_id', 'arac', 'hedef'))):
        raise ValueError('istek_id, arac ve hedef boş olmayan string olmalı')
    if istek['risk_sinifi'] not in ('salt_okunur', 'yikici'):
        raise ValueError('geçersiz risk_sinifi')
    if not isinstance(istek['onay_jetonu'], str):
        raise ValueError('onay_jetonu string olmalı')

def gorev_imzasi_uret(istek_id: str, arac: str, hedef: str, gizli_anahtar: str) -> str:
    if not all((isinstance(x, str) and bool(x.strip()) for x in (istek_id, arac, hedef, gizli_anahtar))):
        raise ValueError('istek_id, arac, hedef ve gizli_anahtar boş olmayan string olmalı')
    mesaj = json.dumps(['pafta-hitl-v2', istek_id, arac, hedef], ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    anahtar = gizli_anahtar.encode('utf-8')
    return hmac.new(anahtar, mesaj, hashlib.sha256).hexdigest()

def hitl_kapisi_dogrula(istek: dict, gizli_anahtar: str) -> dict:
    _istek_kontrol(istek)
    if not isinstance(gizli_anahtar, str) or not gizli_anahtar.strip():
        raise ValueError('gizli_anahtar boş olmayan string olmalı')
    iid = istek['istek_id']
    if istek['risk_sinifi'] == 'salt_okunur':
        return {'istek_id': iid, 'izin_verildi': True, 'neden': 'salt_okunur_serbest'}
    jeton = istek['onay_jetonu'].strip()
    if not jeton:
        return {'istek_id': iid, 'izin_verildi': False, 'neden': 'eksik_onay_jetonu'}
    beklenen = gorev_imzasi_uret(iid, istek['arac'], istek['hedef'], gizli_anahtar)
    if not jeton.isascii() or not hmac.compare_digest(jeton, beklenen):
        return {'istek_id': iid, 'izin_verildi': False, 'neden': 'imza_uyumsuz'}
    return {'istek_id': iid, 'izin_verildi': True, 'neden': 'imzali_onay_gecerli'}

def mudahale_kuyrugu_yurut(istekler: list[dict], gizli_anahtar: str) -> dict:
    if not isinstance(istekler, list) or not istekler:
        raise ValueError('istekler boş olmayan liste olmalı')
    if not isinstance(gizli_anahtar, str) or not gizli_anahtar.strip():
        raise ValueError('gizli_anahtar boş olmayan string olmalı')
    uygulanan = []
    reddedilen = {}
    gorulen = set()
    for ist in istekler:
        sonuc = hitl_kapisi_dogrula(ist, gizli_anahtar)
        iid = sonuc['istek_id']
        if iid in gorulen:
            raise ValueError('tekrarlanan istek_id')
        gorulen.add(iid)
        if sonuc['izin_verildi']:
            uygulanan.append(iid)
        else:
            reddedilen[iid] = sonuc['neden']
    return {'uygulanan_idleri': uygulanan, 'reddedilenler': reddedilen}
```

```hint
Her isteği doğrulama işlevinden geçir; benzersiz `istek_id` kontrolü yap ve `izin_verildi` durumuna göre `uygulanan_idleri` veya `reddedilenler` içine ayır.
```
:::

::: gorev Gerçek deney · Yerel modelle yıkıcı eylemlerde insan onayı (HITL) ve imzalı kapı deneyi
Önceki üç görevde yazdığın `gorev_imzasi_uret`, `hitl_kapisi_dogrula` ve `mudahale_kuyrugu_yurut` işlevlerini bu adımda birleştir.

Canlı deneyde:
1. Yerel Ollama modeli (`ai_lab.SohbetOturumu`) parametreye bağlı insan onayı jetonunun neden hedef değiştirme saldırılarını önlediğini değerlendirir.
2. Salt-okunur (`req-101`), geçerli imzalı (`req-102`), onaysız (`req-103`) ve hedefi değiştirilmiş (`req-104`) müdahale kuyruğu senin yazdığın `mudahale_kuyrugu_yurut` kapısından geçirilir.
3. Onaysız ve değiştirilmiş parametreli yıkıcı çağrıların deterministik olarak reddedildiği kanıtlanır.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def gorev_imzasi_uret(istek_id, arac, hedef, gizli_anahtar):
    # KUSURLU BAŞLANGIÇ KODU: parametreleri imzalamadan boş dize döndürüyor!
    return ""

def hitl_kapisi_dogrula(istek, gizli_anahtar):
    # KUSURLU BAŞLANGIÇ KODU: onay jetonunu doğrulamadan her isteği onaylıyor!
    return {"istek_id": istek.get("istek_id", "") if isinstance(istek, dict) else "", "izin_verildi": True, "neden": "imzali_onay_gecerli"}

def mudahale_kuyrugu_yurut(istekler, gizli_anahtar):
    # KUSURLU BAŞLANGIÇ KODU: istekleri doğrulamadan doğrudan uyguluyor!
    return {"uygulanan_idleri": [i["istek_id"] for i in istekler if isinstance(i, dict)], "reddedilenler": {}}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_ile_guvenlik_14 as deney
    deney.goster(gorev_imzasi_uret, hitl_kapisi_dogrula, mudahale_kuyrugu_yurut)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_ile_guvenlik_veri import hazirla
hazirla("ai-ile-guvenlik-14")
```

```test
import copy
import ast
import ai_lab
from sandbox import ai_gercek_ai_ile_guvenlik_14 as D

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for ad in ("gorev_imzasi_uret", "hitl_kapisi_dogrula", "mudahale_kuyrugu_yurut"):
    need(ad)

sorun = ai_lab.kod_denetimi(
    src,
    ("gorev_imzasi_uret_referans", "hitl_kapisi_dogrula_referans", "mudahale_kuyrugu_yurut_referans", "kanit_yaz"),
)
ok(not sorun, "laboratuvar yamalanmamalı, referans işlevler çağrılmamalı")
import json as _j14, hmac as _h14, hashlib as _s14
_k14="synthetic"
_a14=("a:b","c","d");_b14=("a","b:c","d")
_expected14=_h14.new(_k14.encode(),_j14.dumps(["pafta-hitl-v2",*_a14],ensure_ascii=False,separators=(",", ":")).encode(),_s14.sha256).hexdigest()
ok(gorev_imzasi_uret(*_a14,_k14)==_expected14,"v2 JSON alan sınırları ve domain etiketi")
ok(gorev_imzasi_uret(*_a14,_k14)!=gorev_imzasi_uret(*_b14,_k14),"eski ayıraç çarpışması ayrıldı")
_u14=("a","c","kullanıcı-ö")
ok(gorev_imzasi_uret(*_u14,_k14)==_h14.new(_k14.encode(),_j14.dumps(["pafta-hitl-v2",*_u14],ensure_ascii=False,separators=(",", ":")).encode(),_s14.sha256).hexdigest(),"UTF-8 ensure_ascii=False imzası")
import json as _j14, hmac as _h14, hashlib as _s14
_k14="synthetic"
_token14=_h14.new(_k14.encode(),_j14.dumps(["pafta-hitl-v2","a:b","c","d"],ensure_ascii=False,separators=(",", ":")).encode(),_s14.sha256).hexdigest()
_original14=dict(istek_id="a:b",arac="c",hedef="d",risk_sinifi="yikici",onay_jetonu=_token14)
_other14=dict(istek_id="a",arac="b:c",hedef="d",risk_sinifi="yikici",onay_jetonu=_token14)
ok(hitl_kapisi_dogrula(_original14,_k14)["izin_verildi"] is True,"v2 jeton kendi parametrelerine bağlı")
ok(hitl_kapisi_dogrula(_other14,_k14)["neden"]=="imza_uyumsuz","aynı ayıraç mesajına sahip farklı alanlar reddedilir")
ok(hitl_kapisi_dogrula(dict(_original14,onay_jetonu="onay-ş"),_k14)["neden"]=="imza_uyumsuz","Unicode jeton TypeError üretmez")
import json as _j14, hmac as _h14, hashlib as _s14
_k14="synthetic"
_token14=_h14.new(_k14.encode(),_j14.dumps(["pafta-hitl-v2","a:b","c","d"],ensure_ascii=False,separators=(",", ":")).encode(),_s14.sha256).hexdigest()
_q14=[dict(istek_id="a:b",arac="c",hedef="d",risk_sinifi="yikici",onay_jetonu=_token14),dict(istek_id="a",arac="b:c",hedef="d",risk_sinifi="yikici",onay_jetonu=_token14)]
ok(mudahale_kuyrugu_yurut(_q14,_k14)=={"uygulanan_idleri":["a:b"],"reddedilenler":{"a":"imza_uyumsuz"}},"kuyrukta çapraz parametre jetonu yürütülmez")

if not all(checks):
    stop()

try:
    _ag_tree = ast.parse(src)
    for _node in ast.walk(_ag_tree):
        if isinstance(_node, ast.ImportFrom):
            for _alias in _node.names:
                if _alias.name == "*":
                    ok(False, "Kopya/güvenlik ihlali: wildcard (*) import yasaktır")
        if isinstance(_node, ast.Name) and "referans" in _node.id.lower():
            ok(False, f"Kopya/güvenlik ihlali: 'referans' kullanımı tespit edildi: {_node.id}")
        if isinstance(_node, ast.Attribute) and "referans" in _node.attr.lower():
            ok(False, f"Kopya/güvenlik ihlali: 'referans' niteliği tespit edildi: {_node.attr}")
        if isinstance(_node, ast.Call) and isinstance(_node.func, ast.Name) and _node.func.id in ("getattr", "eval", "exec"):
            ok(False, f"Kopya/güvenlik ihlali: dinamik fonksiyon çağrısı yasaktır: {_node.func.id}")
except Exception as _e:
    ok(False, f"AST ayrıştırma hatası: {_e}")
if not all(checks):
    stop()

def _on_sozlesme():
    try:
        for args in [("", "a", "h", "k"), ("   ", "a", "h", "k"), (123, "a", "h", "k"), ("i", "", "h", "k"), ("i", "a", "", "k"), ("i", "a", "h", ""), ("i", "a", "h", "   "), ("i", "a", "h", None)]:
            try:
                gorev_imzasi_uret(*args)
                return False
            except ValueError:
                pass
        if hitl_kapisi_dogrula({"istek_id": "ro-1", "arac": "oku", "hedef": "h", "risk_sinifi": "salt_okunur", "onay_jetonu": ""}, _k14) != {"istek_id": "ro-1", "izin_verildi": True, "neden": "salt_okunur_serbest"}:
            return False
        for i_in, k_in in [(None, D.GIZLI_ANAHTAR), ({}, D.GIZLI_ANAHTAR), (dict(_original14, risk_sinifi="kritik"), _k14), (dict(_original14, onay_jetonu=123), _k14), (D.ORNEK_ISTEKLER[0], ""), (D.ORNEK_ISTEKLER[0], "   "), (D.ORNEK_ISTEKLER[0], None)]:
            try:
                hitl_kapisi_dogrula(i_in, k_in)
                return False
            except ValueError:
                pass
        for l_in in (None, 123, [], [D.ORNEK_ISTEKLER[0], D.ORNEK_ISTEKLER[0]]):
            try:
                mudahale_kuyrugu_yurut(l_in, D.GIZLI_ANAHTAR)
                return False
            except ValueError:
                pass
        for bad_k in (None, "", "   ", 123):
            try:
                mudahale_kuyrugu_yurut([_original14], bad_k)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(_on_sozlesme(), "sentetik ön kontrol: HMAC-SHA256 imza ve HITL kapısı kuralları tam")

if not all(checks):
    stop()

for _f14 in ("istek_id","arac","hedef"):
    for _bad14 in ("", "   ", 123):
        raises(ValueError, lambda f=_f14,b=_bad14: hitl_kapisi_dogrula(dict(_original14,**{f:b}),_k14), msg="alan türü ve boşluk doğrulaması: "+_f14)
        raises(ValueError, lambda f=_f14,b=_bad14: hitl_kapisi_dogrula(dict(_original14,risk_sinifi="salt_okunur",**{f:b}),_k14), msg="salt_okunur alan doğrulaması: "+_f14)
_utok14=_h14.new(_k14.encode(),_j14.dumps(["pafta-hitl-v2","u-1","c","kullanıcı-ö"],ensure_ascii=False,separators=(",", ":")).encode(),_s14.sha256).hexdigest()
ok(hitl_kapisi_dogrula(dict(_original14,istek_id="u-1",hedef="kullanıcı-ö",onay_jetonu=_utok14),_k14)["izin_verildi"] is True,"Unicode hedef ensure_ascii=False ile doğrulanır")
ok(hitl_kapisi_dogrula(dict(_original14,onay_jetonu=" "+_token14+"\t"),_k14)["izin_verildi"] is True,"jeton dış boşluğu sözleşmeye göre kaldırılır")
ok(hitl_kapisi_dogrula(dict(_original14,onay_jetonu=" \n "),_k14)=={"istek_id":"a:b","izin_verildi":False,"neden":"eksik_onay_jetonu"},"boşluk jetonu eksik onaydır")
raises(ValueError, lambda: mudahale_kuyrugu_yurut([dict(_q14[0],extra=1)],_k14), msg="kuyrukta fazla alan kapıyı geçemez")
raises(ValueError, lambda: mudahale_kuyrugu_yurut(["bozuk"],_k14), msg="kuyrukta sözlük dışı öğe reddedilir")
raises(ValueError, lambda: mudahale_kuyrugu_yurut([dict(_q14[0],risk_sinifi="kritik")],_k14), msg="kuyrukta geçersiz risk_sinifi reddedilir")
raises(ValueError, lambda: mudahale_kuyrugu_yurut([dict(_q14[0],onay_jetonu=123)],_k14), msg="kuyrukta string dışı jeton reddedilir")
raises(ValueError, lambda: mudahale_kuyrugu_yurut([_q14[0]],123), msg="kuyrukta string dışı gizli_anahtar reddedilir")
raises(ValueError, gorev_imzasi_uret, "i-1", "arac", "hedef", "", msg="boş gizli anahtarla imza üretilmez")
raises(ValueError, gorev_imzasi_uret, "", "arac", "hedef", "k", msg="boş istek_id ile imza üretilmez")
raises(ValueError, hitl_kapisi_dogrula, dict(_q14[0],risk_sinifi="salt_okunur"), "   ", msg="salt okunur istekte de boş gizli anahtar reddedilir")
for _f14 in ("istek_id","arac","hedef"):
    for _bad14 in ("", "   ", 123):
        raises(ValueError, lambda f=_f14,b=_bad14: mudahale_kuyrugu_yurut([dict(_q14[0],**{f:b})],_k14), msg="kuyrukta alan şeması: "+_f14)
        raises(ValueError, lambda f=_f14,b=_bad14: mudahale_kuyrugu_yurut([dict(_q14[0],risk_sinifi="salt_okunur",**{f:b})],_k14), msg="kuyrukta salt_okunur alan şeması: "+_f14)
_utok14q=_h14.new(_k14.encode(),_j14.dumps(["pafta-hitl-v2","u-1","c","kullanıcı-ö"],ensure_ascii=False,separators=(",", ":")).encode(),_s14.sha256).hexdigest()
ok(mudahale_kuyrugu_yurut([dict(_q14[0],istek_id="u-1",hedef="kullanıcı-ö",onay_jetonu=_utok14q),dict(_q14[0],istek_id="u-2",onay_jetonu="onay-ş")],_k14)=={"uygulanan_idleri":["u-1"],"reddedilenler":{"u-2":"imza_uyumsuz"}},"kuyrukta Unicode hedef ve ASCII olmayan jeton")
ok(mudahale_kuyrugu_yurut([dict(_q14[0],onay_jetonu=" "+_token14+"\t")],_k14)["uygulanan_idleri"]==["a:b"],"kuyrukta jeton whitespace sözleşmesi")

try:
    r = D.deney(gorev_imzasi_uret, hitl_kapisi_dogrula, mudahale_kuyrugu_yurut)
except Exception as e:
    ok(False, f"GERÇEK HITL KAPISI DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

for ad, deger in r["kontroller"].items():
    ok(deger, "gerçek deney: " + ad)

ai_lab.kanit_yaz("ile-guvenlik-14-hitl", {
    "kaynak": "gercek",
    "kabul": all(checks),
    "ders": "ai-ile-guvenlik-14",
    "ortam": r["ortam"],
    "ayarlar": r["ayarlar"],
    "deney": r,
    "ozet": r["ozet"],
})
o = r["ozet"]
ok(
    True,
    f"BULGU ({o['model']}): uygulanan={o['uygulanan']}, reddedilenler={o['reddedilenler']}.",
)
```

```solution
import hashlib, hmac, json
ZORUNLU_ALANLAR = {"istek_id", "arac", "hedef", "risk_sinifi", "onay_jetonu"}

def _istek_kontrol(istek: dict) -> None:
    if not isinstance(istek, dict) or set(istek.keys()) != ZORUNLU_ALANLAR:
        raise ValueError('istek şeması geçersiz')
    if not all((isinstance(istek[k], str) and bool(istek[k].strip()) for k in ('istek_id', 'arac', 'hedef'))):
        raise ValueError('istek_id, arac ve hedef boş olmayan string olmalı')
    if istek['risk_sinifi'] not in ('salt_okunur', 'yikici'):
        raise ValueError('geçersiz risk_sinifi')
    if not isinstance(istek['onay_jetonu'], str):
        raise ValueError('onay_jetonu string olmalı')

def gorev_imzasi_uret(istek_id: str, arac: str, hedef: str, gizli_anahtar: str) -> str:
    if not all((isinstance(x, str) and bool(x.strip()) for x in (istek_id, arac, hedef, gizli_anahtar))):
        raise ValueError('istek_id, arac, hedef ve gizli_anahtar boş olmayan string olmalı')
    mesaj = json.dumps(['pafta-hitl-v2', istek_id, arac, hedef], ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    anahtar = gizli_anahtar.encode('utf-8')
    return hmac.new(anahtar, mesaj, hashlib.sha256).hexdigest()

def hitl_kapisi_dogrula(istek: dict, gizli_anahtar: str) -> dict:
    _istek_kontrol(istek)
    if not isinstance(gizli_anahtar, str) or not gizli_anahtar.strip():
        raise ValueError('gizli_anahtar boş olmayan string olmalı')
    iid = istek['istek_id']
    if istek['risk_sinifi'] == 'salt_okunur':
        return {'istek_id': iid, 'izin_verildi': True, 'neden': 'salt_okunur_serbest'}
    jeton = istek['onay_jetonu'].strip()
    if not jeton:
        return {'istek_id': iid, 'izin_verildi': False, 'neden': 'eksik_onay_jetonu'}
    beklenen = gorev_imzasi_uret(iid, istek['arac'], istek['hedef'], gizli_anahtar)
    if not jeton.isascii() or not hmac.compare_digest(jeton, beklenen):
        return {'istek_id': iid, 'izin_verildi': False, 'neden': 'imza_uyumsuz'}
    return {'istek_id': iid, 'izin_verildi': True, 'neden': 'imzali_onay_gecerli'}

def mudahale_kuyrugu_yurut(istekler: list[dict], gizli_anahtar: str) -> dict:
    if not isinstance(istekler, list) or not istekler:
        raise ValueError('istekler boş olmayan liste olmalı')
    if not isinstance(gizli_anahtar, str) or not gizli_anahtar.strip():
        raise ValueError('gizli_anahtar boş olmayan string olmalı')
    uygulanan = []
    reddedilen = {}
    gorulen = set()
    for ist in istekler:
        sonuc = hitl_kapisi_dogrula(ist, gizli_anahtar)
        iid = sonuc['istek_id']
        if iid in gorulen:
            raise ValueError('tekrarlanan istek_id')
        gorulen.add(iid)
        if sonuc['izin_verildi']:
            uygulanan.append(iid)
        else:
            reddedilen[iid] = sonuc['neden']
    return {'uygulanan_idleri': uygulanan, 'reddedilenler': reddedilen}

import ai_lab
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_ile_guvenlik_14 as deney
    deney.goster(gorev_imzasi_uret, hitl_kapisi_dogrula, mudahale_kuyrugu_yurut)

```

```hint
Önceki üç görevdeki `gorev_imzasi_uret`, `hitl_kapisi_dogrula` ve `mudahale_kuyrugu_yurut` işlevlerini birleştir.
```
:::


::: anlat Kanonikleştirme v2 · HMAC çarpışması değil, mesaj çarpışması
Eski `id:arac:hedef` birleştirmesinde `("a:b","c","d")` ile `("a","b:c","d")` aynı `a:b:c:d` baytlarını üretir. HMAC sağlam olsa bile farklı parametreler aynı onay jetonunu alır. Bu dersin v2 sözleşmesi alan sınırlarını JSON array içinde korur ve `pafta-hitl-v2` domain etiketi ekler. Aynı string alanlar değişmeden korunur; trim edilerek yeni bir hedefe dönüştürülmez.

Eski fixture jetonları v2 ile yeniden üretildi. Bu bir yanlış test beklentisinin güvenlik gerekçeli düzeltilmesidir; bütün normal/ret vakaları ve negatif testler korunur. `onay_jetonu` Unicode veya bozuk metinse imza uyuşmazlığıdır; `compare_digest` ASCII string kısıtı nedeniyle TypeError ile akışı düşürmemelidir.

`risk_sinifi` bu görevde güvenilir host metadata'sıdır; modelin seçtiği risk sınıfı olarak kabul edilmez. Aynı istekte tekrar kullanım, son kullanma zamanı, tek kullanımlılık, anahtar rotasyonu ve gerçek insan onay arayüzü burada uygulanmaz. `GIZLI_ANAHTAR` sentetik eğitim anahtarıdır; gerçek bir operatör sırrı değildir. Gerçek Ollama yanıtı bir açıklama üretir; queue kararları Python'da ölçülür, gerçek IP engelleme/hesap kapatma yapılmaz.
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
Onay jetonu bir bool değil, tam görev parametrelerinin HMAC’idir. Ayıraçla birleştirmenin iki farklı alan üçlüsünü aynı bayta çevirebildiğini karşı örnekle göster. V2 JSON array alan sınırlarını ve domain etiketini korur. İmza kararını compare_digest ile ver, Unicode/bozuk jetonu uyumsuz olarak ayır. Kuyruğa yalnız geçerli salt-okunur veya imzalı yıkıcı kararlar girer; gerçek operatör arayüzü ve replay cache bu örnekte yoktur.

Önkoşul ve yol köprüsü: ai-savunma-12/13 yetki ve onay.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| Geçerli imza her yeni hedefte kullanılabilir | İstek, araç ve hedef birlikte bağlanır; alan serileştirmesi tekil olmalıdır |

Dinleyiciye sor: Bir model önerisini gerçek güvenlik kararı hâline getiren hangi uygulama denetimidir? Veri kökenini ve kalan sınırı koruyarak cevapla.
:::


### Birincil kaynak ve deneyin sınırı

[Python HMAC belgeleri](https://docs.python.org/3/library/hmac.html). compare_digest aynı türde girdiler ister; string kullanıldığında ASCII koşulu geçerlidir. İmzalanan alanların tek anlamlı kodlanması ayrıca uygulamanın sorumluluğudur.
