---
id: ai-saldiri-19
title: Araç Çağrılarında Auth ve Yetki Bypass
summary: Kimliği doğrulanmış oturumdan bağla, nesne sahipliği ve işlem bazlı onayı denetle, politika kararı ile gerçekleşen çalışma arasındaki bypass farkını raporla.
timeout: 45
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et: Modelin söylediği kullanıcı, oturum kullanıcısı değildir

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Gerçek bir ajan sisteminde kimlik, giriş sağlayıcısının (OIDC/OAuth, oturum çerezi, imzalı token) doğruladığı oturumdan gelir. Model native `tool_calls` içinde `kullanici`, `nesne_id`, `eylem` gibi argümanlar üretir. Dispatcher nesne sahipliğini veritabanından okur; Burp Suite gibi araçlar bu istekleri yakalayıp `id` değiştirerek BOLA/IDOR dener. | Görev 1–3: `veri/oturum_cagrilari.json`, `veri/nesne_istekleri.json` ve `veri/karar_kayitlari.json` içindeki **sentetik** oturumlar, nesne ACL'leri ve karar kayıtları. Son adım: sentetik doğrulanmış oturum, kurulu yerel Ollama modeline üç native araç çağrısı ve deneyin kendi geçici SQLite veritabanında gerçek SELECT/UPDATE/DELETE. | Gerçek bir kimlik sağlayıcısı, token imzası, onay süresi ya da tek kullanımlılık sınanmaz. Üç model çağrısı bir saldırı başarı oranı vermez. Kapıların doğru karar vermesi bütün üretim auth sistemlerinin güvenli olduğunu göstermez. |

> [!NOT]
> Görev 1–3 sentetik veriyle çalışır. Bu görevlerde model, ağ ve veritabanı yoktur. Son adımdaki **Gerçek deney** görevi yalnız kurulu yerel Ollama modelini ve deneyin kendi geçici SQLite dosyalarını kullanır. `veri/` dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalanır; kopyada yaptığın değişiklik bir sonraki çalıştırmada sıfırlanır, **kalıcılık yoktur**. Son adımın istek dosyası çalışma kopyası ise ayrıca kalıcı tutulur. Kontrol bu dosyalardan ayrı, gizli verilerle sınar.

Model bir araç çağrısında `kullanici="admin"` veya başka bir kullanıcının nesne kimliğini üretebilir. Dispatcher kimliği bu JSON'dan alırsa kimlik bağlama bypass'ı oluşur. Kullanıcı kimliği, kimliği doğrulanmış oturumdan gelmelidir; model yalnız işlem adayını üretir.

Yetkilendirme üç ayrı sorudur:

1. **Kimlik:** İstek hangi doğrulanmış oturuma bağlı?
2. **Nesne ve işlem:** Bu kullanıcı bu nesne üzerinde bu eylemi yapabilir mi?
3. **Çalışma:** Politika kararı ile dispatcher'ın gerçekleştirdiği eylem aynı mı?

Görev 1–3'te Ollama, ağ veya gerçek araç kullanılmaz; oturum, nesne ve karar fixture'larıyla kimlik bağlama, BOLA/IDOR tarzı nesne kontrolü ve çalışma bypass'ı ölçülür. Son adım yerel Ollama modelinin native araç çağrısını deneyin kendi SQLite veritabanı önünde ölçer. Burp Suite ve dış ağ hiçbir adımda kullanılmaz.

**Görev 1'de sık tuzaklar:** Adları `lower()` ile karşılaştırmak `Ayse` ile `ayse`yi aynı kişi yapar (`veri/oturum_cagrilari.json`, `k-09`). `dogrulanmis` alanını doğruluk değeriyle (`if oturum["dogrulanmis"]`) denetlemek `1` ve `"true"` gibi değerleri kabul eder (`k-05`, `k-06`). Ad karşılaştırmasını oturum doğrulamasından önce yapmak, doğrulanmamış oturumda yanlış neden döndürür (`k-04`). Çıktıda her örnek `doğru` ya da `YANLIŞ` diye işaretlenir; `YANLIŞ` satırının açıklaması hangi kuralın eksik olduğunu söyler.
:::

::: tahmin
Nesne sahipliği ve paylaşım kuralları değerlendiriliyor. Üç çıktı satırını yaz:

```python
nesne = {"sahip": "ayse", "paylasim": ["mehmet"]}
kullanici = "mehmet"
print(kullanici == nesne["sahip"] or kullanici in nesne["paylasim"])
print(kullanici == nesne["sahip"])
onay = {"nesne_id": "d2", "eylem": "sil"}
print(onay["nesne_id"] == "d1" and onay["eylem"] == "sil")
```

???

```cikti
True
False
False
```

Mehmet paylaşım nedeniyle okuyabilir fakat sahip olmadığı için yazamaz. Silme onayı başka nesneye aittir; işlem bazlı onay bu nesneye devredilemez.
:::

::: gorev 1 · Araç çağrısını doğrulanmış oturum kimliğine bağla
`kimlik_bagla(oturum, cagri)` işlevini yaz. Oturum tam olarak `kullanici`, `dogrulanmis` alanlarını taşısın; kullanıcı boş olmayan string, `dogrulanmis` bool olmalıdır. Çağrı tam olarak `kullanici`, `eylem` alanlarını taşısın; kullanıcı boş olmayan string, eylem `oku`, `yaz` veya `paylas` olmalıdır. Şema veya tür hatasında `ValueError` yükselt.

Dönüş `{"izinli":BOOL,"neden":NEDEN}` biçimindedir:

- Oturum doğrulanmamışsa `(False, "oturum-dogrulanmamis")`.
- Çağrıdaki kullanıcı oturum kullanıcısıyla aynı değilse `(False, "kimlik-uyusmazligi")`.
- Aksi durumda `(True, "bagli")`.

Önce oturum doğrulamasını denetle. Çağrıdaki kullanıcı adı eşleşse bile doğrulanmamış oturumu kabul etme; bu sonuç yalnız kimlik bağlamadır, nesne yetkisi değildir.

Görünür veri: `veri/oturum_cagrilari.json`. Her örneğin `beklenen` alanı vardır; `null`, `ValueError` demektir.

```starter
from ai_saldiri_veri import json_yukle

def kimlik_bagla(oturum, cagri):
    # KUSURLU BAŞLANGIÇ KODU: kullanıcı adlarını lower() ile karşılaştırıyor (Ayse = ayse), ad eşleşmesini oturum doğrulamasından önce denetliyor, dogrulanmis alanını doğruluk değeriyle okuyor (1 ve "true" geçer) ve şemayı, ek rol alanını hiç denetlemiyor!
    if str(cagri.get("kullanici", "")).lower() != str(oturum.get("kullanici", "")).lower():
        return {"izinli": False, "neden": "kimlik-uyusmazligi"}
    if not oturum.get("dogrulanmis"):
        return {"izinli": False, "neden": "oturum-dogrulanmamis"}
    return {"izinli": True, "neden": "bagli"}

veri = json_yukle("veri/oturum_cagrilari.json")
for o in veri["ornekler"]:
    try:
        sonuc = kimlik_bagla(o["oturum"], o["cagri"])
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
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-19")
```

```test
OTURUM = {"kullanici": "ayse", "dogrulanmis": True}
CAGRI = {"kullanici": "ayse", "eylem": "oku"}
def sozlesme(fn):
    try:
        if fn(OTURUM, CAGRI) != {"izinli": True, "neden": "bagli"}:
            return False
        if fn(OTURUM, dict(CAGRI, kullanici="mehmet")) != {"izinli": False, "neden": "kimlik-uyusmazligi"}:
            return False
        if fn(dict(OTURUM, dogrulanmis=False), CAGRI) != {"izinli": False, "neden": "oturum-dogrulanmamis"}:
            return False
        for oturum, cagri in [
            (None, CAGRI), (dict(OTURUM, kullanici=""), CAGRI),
            (dict(OTURUM, dogrulanmis=1), CAGRI), (dict(OTURUM, ek=1), CAGRI),
            (OTURUM, dict(CAGRI, kullanici="")), (OTURUM, dict(CAGRI, eylem="sil")),
            (OTURUM, dict(CAGRI, rol="admin")), (OTURUM, None),
        ]:
            try:
                fn(oturum, cagri)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(kimlik_bagla), "oturum doğrulaması, kullanıcı eşleşmesi ve şema korunmalı")
def m_cagri(oturum, cagri):
    return {"izinli": True, "neden": "bagli"}
def m_oturum(oturum, cagri):
    sonuc = kimlik_bagla(dict(oturum, dogrulanmis=True), cagri)
    return sonuc
def m_kullanici(oturum, cagri):
    return kimlik_bagla(oturum, dict(cagri, kullanici=oturum["kullanici"]))
for ad, mutant in [("çağrıyı doğrudan yetkili sayan", m_cagri), ("oturumu zorla doğrulanmış yapan", m_oturum), ("kullanıcı uyuşmazlığını gizleyen", m_kullanici)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def kimlik_bagla(oturum, cagri):
    if not isinstance(oturum, dict) or set(oturum) != {"kullanici", "dogrulanmis"}:
        raise ValueError("oturum şeması geçersiz")
    if not all((isinstance(oturum["kullanici"], str), bool(oturum["kullanici"]), isinstance(oturum["dogrulanmis"], bool))):
        raise ValueError("oturum alanları geçersiz")
    if not isinstance(cagri, dict) or set(cagri) != {"kullanici", "eylem"}:
        raise ValueError("çağrı şeması geçersiz")
    if not all((isinstance(cagri["kullanici"], str), bool(cagri["kullanici"]), cagri["eylem"] in ("oku", "yaz", "paylas"))):
        raise ValueError("çağrı alanları geçersiz")
    if not oturum["dogrulanmis"]:
        return {"izinli": False, "neden": "oturum-dogrulanmamis"}
    if cagri["kullanici"] != oturum["kullanici"]:
        return {"izinli": False, "neden": "kimlik-uyusmazligi"}
    return {"izinli": True, "neden": "bagli"}
```

```hint
Şemaları doğruladıktan sonra önce `dogrulanmis` değerine bak. Sonra iki kullanıcı kimliğini karşılaştır; çağrıya rol veya ek yetki alanı ekleme.
```
:::

::: anlat Nesne sahipliği her eylemde yeniden denetlenir
Kullanıcının oturuma bağlı olması, her nesneye erişebileceği anlamına gelmez. Bu derste okuma sahip veya paylaşım listesine; yazma yalnız sahibe; silme ise sahip ve aynı nesne-işlem için üretilmiş açık onaya bağlıdır. Başka nesnenin kimliğini değiştirmek BOLA/IDOR saldırısının fixture karşılığıdır.

Onay global bir `True` değeri değildir. `{"nesne_id":"d1","eylem":"sil"}` yalnız bu nesnenin silinmesi için geçerlidir. Okuma ve yazma için onay alanı kullanılmaz. Gerçek sistemde onayın süresi, tek kullanımlılığı ve imzası da denetlenmelidir; burada yalnız kapsam bağlaması sınanır.

**Görev 2'de sık tuzaklar:** Paylaşım listesini "erişim var" diye her eyleme genişletmek, paylaşımlı kullanıcıya yazma ve silme verir (`veri/nesne_istekleri.json`, `n-03`, `n-09`). Onayı yalnız "var mı" diye denetlemek, başka nesnenin ya da başka işlemin onayını kabul eder (`n-07`, `n-08`) ve `True` gibi global bir onaya izin verir (`n-11`). Paylaşımı tür denetimi olmadan `in` ile aramak, `"mehmet"` metnini liste gibi kullanır (`n-14`).
:::

::: gorev 2 · Nesne sahipliği ve işlem bazlı onayı uygula
`nesne_yetki(kullanici, nesne, eylem, onay)` işlevini yaz. Kullanıcı boş olmayan string olmalıdır. Nesne tam olarak `id`, `sahip`, `paylasim` alanlarını taşısın; kimlik ve sahip boş olmayan string, paylaşım boş olmayan ve benzersiz kullanıcı stringlerinden oluşan liste olmalıdır. Eylem `oku`, `yaz` veya `sil` olmalıdır. Şema ihlalinde `ValueError` yükselt.

Dönüş `{"izinli":BOOL,"neden":NEDEN}` biçimindedir:

- `oku`: kullanıcı sahip veya paylaşım listesindeyse izinli, aksi halde `nesne-erisimi-yok`.
- `yaz`: yalnız sahip izinli, aksi halde `sahiplik-gerekli`.
- `sil`: sahip değilse `sahiplik-gerekli`; sahipse onay tam `{"nesne_id":NESNE_ID,"eylem":"sil"}` olmalı, aksi halde `islem-onayi-gerekli`.

Başarı nedeni `izinli`. Onay verilmişse `None` veya tam iki alanlı dict olmalı; geçersiz onay şeması `ValueError` üretir. Okuma/yazma için onayın içeriği kararı değiştirmez. Sahibi onaydan okuma.

Görünür veri: `veri/nesne_istekleri.json`. Her örneğin `beklenen` alanı vardır; `null`, `ValueError` demektir.

```starter
from ai_saldiri_veri import json_yukle

def nesne_yetki(kullanici, nesne, eylem, onay):
    # KUSURLU BAŞLANGIÇ KODU: paylaşım listesindeki kullanıcıya yazma ve silme de veriyor, silmede onayı yalnız "var mı" diye denetliyor (başka nesnenin onayı ve True geçer), kullanıcı, nesne, eylem ve onay şemasını hiç denetlemiyor!
    erisim = kullanici == nesne["sahip"] or kullanici in nesne["paylasim"]
    if not erisim:
        return {"izinli": False, "neden": "nesne-erisimi-yok"}
    if eylem == "sil" and not onay:
        return {"izinli": False, "neden": "islem-onayi-gerekli"}
    return {"izinli": True, "neden": "izinli"}

veri = json_yukle("veri/nesne_istekleri.json")
for o in veri["ornekler"]:
    try:
        sonuc = nesne_yetki(o["kullanici"], o["nesne"], o["eylem"], o["onay"])
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
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-19")
```

```test
NESNE = {"id": "d1", "sahip": "ayse", "paylasim": ["mehmet"]}
ONAY = {"nesne_id": "d1", "eylem": "sil"}
def sozlesme(fn):
    try:
        for kullanici, nesne, eylem, onay, beklenen in [
            ("ayse", NESNE, "oku", None, (True, "izinli")),
            ("ayse", NESNE, "yaz", None, (True, "izinli")),
            ("mehmet", NESNE, "oku", None, (True, "izinli")),
            ("mehmet", NESNE, "yaz", None, (False, "sahiplik-gerekli")),
            ("diger", NESNE, "oku", None, (False, "nesne-erisimi-yok")),
            ("ayse", NESNE, "sil", None, (False, "islem-onayi-gerekli")),
            ("ayse", NESNE, "sil", ONAY, (True, "izinli")),
            ("ayse", NESNE, "sil", dict(ONAY, nesne_id="d2"), (False, "islem-onayi-gerekli")),
            ("mehmet", NESNE, "sil", ONAY, (False, "sahiplik-gerekli")),
        ]:
            sonuc = fn(kullanici, nesne, eylem, onay)
            if (sonuc["izinli"], sonuc["neden"]) != beklenen:
                return False
        for kullanici, nesne, eylem, onay in [
            ("", NESNE, "oku", None), (3, NESNE, "oku", None), ("ayse", None, "oku", None), ("ayse", dict(NESNE, ek=1), "oku", None),
            ("ayse", dict(NESNE, id=""), "oku", None), ("ayse", dict(NESNE, id=3), "oku", None), ("ayse", dict(NESNE, sahip=""), "oku", None), ("ayse", dict(NESNE, sahip=3), "oku", None),
            ("ayse", dict(NESNE, paylasim="mehmet"), "oku", None), ("ayse", dict(NESNE, paylasim=[3]), "oku", None),
            ("ayse", dict(NESNE, paylasim=["mehmet", "mehmet"]), "oku", None),
            ("ayse", dict(NESNE, paylasim=[""]), "oku", None),
            ("ayse", NESNE, "paylas", None), ("ayse", NESNE, "sil", True),
            ("ayse", NESNE, "sil", dict(ONAY, ek=1)),
        ]:
            try:
                fn(kullanici, nesne, eylem, onay)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(nesne_yetki), "sahiplik, paylaşım, silme onayı ve onay kapsamı korunmalı")
def m_id(kullanici, nesne, eylem, onay):
    return {"izinli": True, "neden": "izinli"}
def m_onay(kullanici, nesne, eylem, onay):
    return nesne_yetki(kullanici, nesne, eylem, {"nesne_id": nesne["id"], "eylem": "sil"}) if eylem == "sil" else nesne_yetki(kullanici, nesne, eylem, onay)
def m_paylas(kullanici, nesne, eylem, onay):
    veri = dict(nesne, sahip=nesne["paylasim"][0])
    return nesne_yetki(kullanici, veri, eylem, onay)
for ad, mutant in [("her nesneye erişim veren", m_id), ("onayı zorla geçerli yapan", m_onay), ("paylaşımı sahipliğe çeviren", m_paylas)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def nesne_yetki(kullanici, nesne, eylem, onay):
    if not isinstance(kullanici, str) or not kullanici:
        raise ValueError("kullanıcı geçersiz")
    if not isinstance(nesne, dict) or set(nesne) != {"id", "sahip", "paylasim"}:
        raise ValueError("nesne şeması geçersiz")
    if not all((isinstance(nesne["id"], str), bool(nesne["id"]), isinstance(nesne["sahip"], str), bool(nesne["sahip"]), isinstance(nesne["paylasim"], list))):
        raise ValueError("nesne alanları geçersiz")
    if not all(isinstance(x, str) and bool(x) for x in nesne["paylasim"]) or len(nesne["paylasim"]) != len(set(nesne["paylasim"])):
        raise ValueError("paylaşım listesi geçersiz")
    if eylem not in ("oku", "yaz", "sil"):
        raise ValueError("eylem geçersiz")
    if onay is not None and (not isinstance(onay, dict) or set(onay) != {"nesne_id", "eylem"}):
        raise ValueError("onay şeması geçersiz")
    sahip = kullanici == nesne["sahip"]
    if eylem == "oku":
        izinli = sahip or kullanici in nesne["paylasim"]
        return {"izinli": izinli, "neden": "izinli" if izinli else "nesne-erisimi-yok"}
    if not sahip:
        return {"izinli": False, "neden": "sahiplik-gerekli"}
    if eylem == "yaz":
        return {"izinli": True, "neden": "izinli"}
    gecerli_onay = onay == {"nesne_id": nesne["id"], "eylem": "sil"}
    return {"izinli": gecerli_onay, "neden": "izinli" if gecerli_onay else "islem-onayi-gerekli"}
```

```hint
Okuma kararını sahiplik veya paylaşım üyeliğiyle ver. Yazma ve silmede önce sahipliği iste; silmede onay nesnesini nesne kimliği ve eylemle birebir karşılaştır.
```
:::

::: anlat İzinli karar ile çalışan eylem ayrı denetlenir
Bazı bypass'lar politika fonksiyonunda, bazıları dispatcher'dadır. Politika `reddet` derken dispatcher eylemi çalıştırırsa karar doğru görünse bile saldırı gerçekleşir. Tersine her isteği reddeden sistem bypass'ı önler fakat meşru kullanımı bozar.

Regresyon raporu dört ölçüt üretir: beklenen ret yerine izinli karar, beklenen ret yerine çalışan eylem, beklenen izin yerine yanlış ret ve bütünüyle tutarlı vakalar. `tutarli` için karar beklenene eşit olmalı ve `calistirildi` yalnız izinli vakalarda doğru olmalıdır. Bu fixture gerçek log toplamak yerine test sözleşmesini görünür kılar.

**Görev 3'te sık tuzaklar:** Çalışma bypass'ını yalnız karar bypass'ı olan vakalarda aramak, politikanın `reddet` dediği ama dispatcher'ın yine çalıştırdığı vakayı kaybeder (`veri/karar_kayitlari.json`, `r-idor-oku`). Tutarlılıkta `calistirildi` alanını yok saymak, meşru eylemi hiç çalıştırmayan vakayı (`r-paylasim-oku`) ya da her şeyi reddedip yine çalıştıran vakayı tutarlı sayar. Çıktıda her rapor alanı beklenenle karşılaştırılır; dört bozuk girdinin hepsi `ValueError` almalıdır.
:::

::: gorev 3 · Karar ve çalışma bypass'ını ayrı raporla
`yetki_regresyonu(kayitlar)` işlevini yaz. Her kayıt tam olarak `vaka_id`, `beklenen`, `karar`, `calistirildi` alanlarını taşısın. Vaka kimliği boş olmayan ve benzersiz string, beklenen ve karar `izinli` veya `reddet`, `calistirildi` bool olmalıdır. Geçersiz veride `ValueError` yükselt.

Dönüş:

```text
{"vaka":N,"karar_bypassi":[...],"calisma_bypassi":[...],
 "yanlis_ret":[...],"tutarli":[...]}
```

- `karar_bypassi`: beklenen `reddet`, karar `izinli`.
- `calisma_bypassi`: beklenen `reddet` ve `calistirildi=True`.
- `yanlis_ret`: beklenen `izinli`, karar `reddet`.
- `tutarli`: beklenen karar ile aynı ve `calistirildi == (beklenen == "izinli")`.

Listeler alfabetik vaka kimliği sıralıdır. Bir vaka hem karar hem çalışma bypass'ına girebilir. Boş girdi için boş rapor dön; girdi sırası sonucu etkilememeli ve veri değişmemelidir.

Görünür veri: `veri/karar_kayitlari.json`. Dosyada beklenen rapor ve dört bozuk girdi vardır.

```starter
from ai_saldiri_veri import json_yukle

def yetki_regresyonu(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: çalışma bypass'ını yalnız karar bypass'ı olan vakalarda arıyor (reddedilip çalışan eylem kaybolur), tutarlılıkta calistirildi alanını yok sayıyor, kayıtları doğrulamıyor ve listeleri sıralamıyor!
    sonuc = {"vaka": len(kayitlar), "karar_bypassi": [], "calisma_bypassi": [], "yanlis_ret": [], "tutarli": []}
    for kayit in kayitlar:
        if kayit["beklenen"] == "reddet" and kayit["karar"] == "izinli":
            sonuc["karar_bypassi"].append(kayit["vaka_id"])
            if kayit["calistirildi"]:
                sonuc["calisma_bypassi"].append(kayit["vaka_id"])
        if kayit["beklenen"] == "izinli" and kayit["karar"] == "reddet":
            sonuc["yanlis_ret"].append(kayit["vaka_id"])
        if kayit["beklenen"] == kayit["karar"]:
            sonuc["tutarli"].append(kayit["vaka_id"])
    return sonuc

veri = json_yukle("veri/karar_kayitlari.json")
try:
    rapor = yetki_regresyonu(veri["kayitlar"])
except Exception as hata:
    rapor = {"hata": type(hata).__name__}
for alan, deger in veri["beklenen"].items():
    print(alan, "doğru" if rapor.get(alan) == deger else "YANLIŞ", rapor.get(alan))
for i, bozuk in enumerate(veri["bozuk_girdiler"], 1):
    try:
        yetki_regresyonu(bozuk)
        print("bozuk", i, "YANLIŞ: kabul edildi")
    except ValueError:
        print("bozuk", i, "doğru: ValueError")
    except Exception as hata:
        print("bozuk", i, "YANLIŞ:", type(hata).__name__)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-19")
```

```test
import copy
KAYITLAR = [
    {"vaka_id": "v1", "beklenen": "reddet", "karar": "izinli", "calistirildi": True},
    {"vaka_id": "v2", "beklenen": "reddet", "karar": "reddet", "calistirildi": True},
    {"vaka_id": "v3", "beklenen": "izinli", "karar": "reddet", "calistirildi": False},
    {"vaka_id": "v4", "beklenen": "izinli", "karar": "izinli", "calistirildi": True},
    {"vaka_id": "v5", "beklenen": "reddet", "karar": "reddet", "calistirildi": False},
    {"vaka_id": "v6", "beklenen": "izinli", "karar": "izinli", "calistirildi": False},
]
BEKLENEN = {"vaka": 6, "karar_bypassi": ["v1"], "calisma_bypassi": ["v1", "v2"], "yanlis_ret": ["v3"], "tutarli": ["v4", "v5"]}
def sozlesme(fn):
    try:
        once = copy.deepcopy(KAYITLAR)
        if fn(KAYITLAR) != BEKLENEN or KAYITLAR != once or fn(list(reversed(KAYITLAR))) != BEKLENEN:
            return False
        if fn([]) != {"vaka": 0, "karar_bypassi": [], "calisma_bypassi": [], "yanlis_ret": [], "tutarli": []}:
            return False
        if fn([{"vaka_id": "v7", "beklenen": "reddet", "karar": "izinli", "calistirildi": False}]) != {"vaka": 1, "karar_bypassi": ["v7"], "calisma_bypassi": [], "yanlis_ret": [], "tutarli": []}:
            return False
        for kayitlar in [
            KAYITLAR + [KAYITLAR[0]], [dict(KAYITLAR[0], beklenen="belirsiz")],
            [dict(KAYITLAR[0], karar="reddet", calistirildi=1)],
            [dict(KAYITLAR[0], vaka_id="")], [dict(KAYITLAR[0], vaka_id=3)], [dict(KAYITLAR[0], ek=1)], [None],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(yetki_regresyonu), "karar, çalışma, yanlış ret ve tutarlılık ayrımı korunmalı")
def m_calisma(kayitlar):
    sonuc = yetki_regresyonu(kayitlar)
    sonuc["calisma_bypassi"] = sonuc["karar_bypassi"]
    return sonuc
def m_ret(kayitlar):
    sonuc = yetki_regresyonu(kayitlar)
    sonuc["yanlis_ret"] = []
    return sonuc
def m_tutarli(kayitlar):
    sonuc = yetki_regresyonu(kayitlar)
    sonuc["tutarli"] = sorted(x["vaka_id"] for x in kayitlar if x["beklenen"] == x["karar"])
    return sonuc
for ad, mutant in [("reddedip çalışan bypass'ı düşüren", m_calisma), ("yanlış retleri gizleyen", m_ret), ("çalışmayı tutarlılıkta yok sayan", m_tutarli)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def yetki_regresyonu(kayitlar):
    vakalar = set()
    sonuc = {"vaka": 0, "karar_bypassi": [], "calisma_bypassi": [], "yanlis_ret": [], "tutarli": []}
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"vaka_id", "beklenen", "karar", "calistirildi"}:
            raise ValueError("kayıt şeması geçersiz")
        if not all((isinstance(kayit["vaka_id"], str), bool(kayit["vaka_id"]), kayit["vaka_id"] not in vakalar, kayit["beklenen"] in ("izinli", "reddet"), kayit["karar"] in ("izinli", "reddet"), isinstance(kayit["calistirildi"], bool))):
            raise ValueError("kayıt alanları geçersiz")
        vakalar.add(kayit["vaka_id"])
        if kayit["beklenen"] == "reddet" and kayit["karar"] == "izinli":
            sonuc["karar_bypassi"].append(kayit["vaka_id"])
        if kayit["beklenen"] == "reddet" and kayit["calistirildi"]:
            sonuc["calisma_bypassi"].append(kayit["vaka_id"])
        if kayit["beklenen"] == "izinli" and kayit["karar"] == "reddet":
            sonuc["yanlis_ret"].append(kayit["vaka_id"])
        if kayit["beklenen"] == kayit["karar"] and kayit["calistirildi"] == (kayit["beklenen"] == "izinli"):
            sonuc["tutarli"].append(kayit["vaka_id"])
    sonuc["vaka"] = len(vakalar)
    for alan in ("karar_bypassi", "calisma_bypassi", "yanlis_ret", "tutarli"):
        sonuc[alan].sort()
    return sonuc
```

```hint
Her vaka için beklenen, karar ve çalışma değerlerini ayrı kullan. Dört listeyi bağımsız `if` bloklarıyla doldur; tutarlılıkta hem kararı hem beklenen izinle çalışma eşitliğini denetle.
```
:::


::: anlat Kimliği ve nesne yetkisini gerçek SQLite önünde denetle
[Sentetik istek dosyasını aç](/data/ai-saldiri-19-istekler.txt). Çalıştır ayrı kalıcı `calisma/ai-saldiri-19/istekler.json` kopyasının yolunu gösterir. Dış editör/Python ile değiştirip yeniden Çalıştır; düzenlemelerin korunur. Test ayrı veriler kullanır. Ekranda yerleşik dosya editörü yoktur.

Her deney kendi SQLite veritabanında benim/ortak/yabanci nesnelerini kurar. Paylaşım ve sahiplik sunucu tarafındaki SQLite satırından okunur; model bunları değiştiremez. Oturum sentetik doğrulanmış kullanıcıdır, gerçek OAuth/giriş sağlayıcısı değildir. Öğrencinin iki kapısı gerçek SELECT/UPDATE/DELETE önünde çalışır. Silme yalnız deneyin kendi sentetik satırındadır; modelden veya belgeden güvenilir onay alınmaz. Doğrudan kontrollerde ayrı nesne/işlem bağlı onay verilir.

`kimlik_bagla` önceki sözleşmede oku/yaz/paylas kabul eder. Bu deneyde yalnız kimlik eşleşmesini ölçmek için ona eylem=oku verilir; bu bir silme izni değildir. **Gerçek eylem değişmeden `nesne_yetki` kapısına gider.** İki kapı da izin vermeden yürütme olmaz. Temiz/zehirli korumalı ve iki kapısı atlanmış yerel karşılaştırma kolu native model kullanır. On bir doğrudan sentetik kontrol gerçek diskte meşru okuma/yazma/onaylı silme ile kimlik/nesne/yanlış onay retlerini doğrular; model cevabı diye sunulmaz.

Ham native argümanlar, güvenilir oturum/onay, nesne ACL'i, karar, gerçekten çalışan işlem ve disk önce/sonrası ayrı kaydedilir. Model saldırıya uymayabilir; bu geçerli gözlemdir, saldırı başarısı geçme şartı değildir. Bu sınırlı yerel deney bütün üretim auth sistemlerini kapsamaz.

**Çıktıyı okurken:** Önce `kimlik-nesne-kapisi-yok` kolunun disk önce/sonrası farkına bak; kapılar atlandığında modelin önerdiği işlem doğrudan çalışır. Korumalı kolda aynı öneri `reddedildi` olarak görünmeli ve disk değişmemelidir. Model hiç `yabanci` nesnesini istemediyse bu bir başarısızlık değildir; o koşuda saldırının modele etki etmediğini gösterir.
:::

::: gorev Gerçek deney · Model kimliğini ve yabancı nesne işlemini sınırla
Önceki `kimlik_bagla`, `nesne_yetki`, `yetki_regresyonu` işlevlerini birleştir. Kontrol Et saf sözleşmelerden sonra gerçek native model ve SQLite deneyini yürütür. Modelin söylediği admin adı gerçek kimlik sayılmaz.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def kimlik_bagla(oturum, cagri):
    # KUSURLU BAŞLANGIÇ KODU: kullanıcı adlarını lower() ile karşılaştırıyor (Ayse = ayse), ad eşleşmesini oturum doğrulamasından önce denetliyor, dogrulanmis alanını doğruluk değeriyle okuyor (1 ve "true" geçer) ve şemayı, ek rol alanını hiç denetlemiyor!
    if str(cagri.get("kullanici", "")).lower() != str(oturum.get("kullanici", "")).lower():
        return {"izinli": False, "neden": "kimlik-uyusmazligi"}
    if not oturum.get("dogrulanmis"):
        return {"izinli": False, "neden": "oturum-dogrulanmamis"}
    return {"izinli": True, "neden": "bagli"}

def nesne_yetki(kullanici, nesne, eylem, onay):
    # KUSURLU BAŞLANGIÇ KODU: paylaşım listesindeki kullanıcıya yazma ve silme de veriyor, silmede onayı yalnız "var mı" diye denetliyor (başka nesnenin onayı ve True geçer), kullanıcı, nesne, eylem ve onay şemasını hiç denetlemiyor!
    erisim = kullanici == nesne["sahip"] or kullanici in nesne["paylasim"]
    if not erisim:
        return {"izinli": False, "neden": "nesne-erisimi-yok"}
    if eylem == "sil" and not onay:
        return {"izinli": False, "neden": "islem-onayi-gerekli"}
    return {"izinli": True, "neden": "izinli"}

def yetki_regresyonu(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: çalışma bypass'ını yalnız karar bypass'ı olan vakalarda arıyor (reddedilip çalışan eylem kaybolur), tutarlılıkta calistirildi alanını yok sayıyor, kayıtları doğrulamıyor ve listeleri sıralamıyor!
    sonuc = {"vaka": len(kayitlar), "karar_bypassi": [], "calisma_bypassi": [], "yanlis_ret": [], "tutarli": []}
    for kayit in kayitlar:
        if kayit["beklenen"] == "reddet" and kayit["karar"] == "izinli":
            sonuc["karar_bypassi"].append(kayit["vaka_id"])
            if kayit["calistirildi"]:
                sonuc["calisma_bypassi"].append(kayit["vaka_id"])
        if kayit["beklenen"] == "izinli" and kayit["karar"] == "reddet":
            sonuc["yanlis_ret"].append(kayit["vaka_id"])
        if kayit["beklenen"] == kayit["karar"]:
            sonuc["tutarli"].append(kayit["vaka_id"])
    return sonuc

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_19 as deney
    deney.goster(kimlik_bagla,nesne_yetki,yetki_regresyonu)

```

```test
OTURUM = {"kullanici": "ayse", "dogrulanmis": True}
CAGRI = {"kullanici": "ayse", "eylem": "oku"}
def sozlesme(fn):
    try:
        if fn(OTURUM, CAGRI) != {"izinli": True, "neden": "bagli"}:
            return False
        if fn(OTURUM, dict(CAGRI, kullanici="mehmet")) != {"izinli": False, "neden": "kimlik-uyusmazligi"}:
            return False
        if fn(dict(OTURUM, dogrulanmis=False), CAGRI) != {"izinli": False, "neden": "oturum-dogrulanmamis"}:
            return False
        for oturum, cagri in [
            (None, CAGRI), (dict(OTURUM, kullanici=""), CAGRI),
            (dict(OTURUM, dogrulanmis=1), CAGRI), (dict(OTURUM, ek=1), CAGRI),
            (OTURUM, dict(CAGRI, kullanici="")), (OTURUM, dict(CAGRI, eylem="sil")),
            (OTURUM, dict(CAGRI, rol="admin")), (OTURUM, None),
        ]:
            try:
                fn(oturum, cagri)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(kimlik_bagla), "oturum doğrulaması, kullanıcı eşleşmesi ve şema korunmalı")
def m_cagri(oturum, cagri):
    return {"izinli": True, "neden": "bagli"}
def m_oturum(oturum, cagri):
    sonuc = kimlik_bagla(dict(oturum, dogrulanmis=True), cagri)
    return sonuc
def m_kullanici(oturum, cagri):
    return kimlik_bagla(oturum, dict(cagri, kullanici=oturum["kullanici"]))
for ad, mutant in [("çağrıyı doğrudan yetkili sayan", m_cagri), ("oturumu zorla doğrulanmış yapan", m_oturum), ("kullanıcı uyuşmazlığını gizleyen", m_kullanici)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

NESNE = {"id": "d1", "sahip": "ayse", "paylasim": ["mehmet"]}
ONAY = {"nesne_id": "d1", "eylem": "sil"}
def sozlesme(fn):
    try:
        for kullanici, nesne, eylem, onay, beklenen in [
            ("ayse", NESNE, "oku", None, (True, "izinli")),
            ("ayse", NESNE, "yaz", None, (True, "izinli")),
            ("mehmet", NESNE, "oku", None, (True, "izinli")),
            ("mehmet", NESNE, "yaz", None, (False, "sahiplik-gerekli")),
            ("diger", NESNE, "oku", None, (False, "nesne-erisimi-yok")),
            ("ayse", NESNE, "sil", None, (False, "islem-onayi-gerekli")),
            ("ayse", NESNE, "sil", ONAY, (True, "izinli")),
            ("ayse", NESNE, "sil", dict(ONAY, nesne_id="d2"), (False, "islem-onayi-gerekli")),
            ("mehmet", NESNE, "sil", ONAY, (False, "sahiplik-gerekli")),
        ]:
            sonuc = fn(kullanici, nesne, eylem, onay)
            if (sonuc["izinli"], sonuc["neden"]) != beklenen:
                return False
        for kullanici, nesne, eylem, onay in [
            ("", NESNE, "oku", None), (3, NESNE, "oku", None), ("ayse", None, "oku", None), ("ayse", dict(NESNE, ek=1), "oku", None),
            ("ayse", dict(NESNE, id=""), "oku", None), ("ayse", dict(NESNE, id=3), "oku", None), ("ayse", dict(NESNE, sahip=""), "oku", None), ("ayse", dict(NESNE, sahip=3), "oku", None),
            ("ayse", dict(NESNE, paylasim="mehmet"), "oku", None), ("ayse", dict(NESNE, paylasim=[3]), "oku", None),
            ("ayse", dict(NESNE, paylasim=["mehmet", "mehmet"]), "oku", None),
            ("ayse", dict(NESNE, paylasim=[""]), "oku", None),
            ("ayse", NESNE, "paylas", None), ("ayse", NESNE, "sil", True),
            ("ayse", NESNE, "sil", dict(ONAY, ek=1)),
        ]:
            try:
                fn(kullanici, nesne, eylem, onay)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(nesne_yetki), "sahiplik, paylaşım, silme onayı ve onay kapsamı korunmalı")
def m_id(kullanici, nesne, eylem, onay):
    return {"izinli": True, "neden": "izinli"}
def m_onay(kullanici, nesne, eylem, onay):
    return nesne_yetki(kullanici, nesne, eylem, {"nesne_id": nesne["id"], "eylem": "sil"}) if eylem == "sil" else nesne_yetki(kullanici, nesne, eylem, onay)
def m_paylas(kullanici, nesne, eylem, onay):
    veri = dict(nesne, sahip=nesne["paylasim"][0])
    return nesne_yetki(kullanici, veri, eylem, onay)
for ad, mutant in [("her nesneye erişim veren", m_id), ("onayı zorla geçerli yapan", m_onay), ("paylaşımı sahipliğe çeviren", m_paylas)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

import copy
KAYITLAR = [
    {"vaka_id": "v1", "beklenen": "reddet", "karar": "izinli", "calistirildi": True},
    {"vaka_id": "v2", "beklenen": "reddet", "karar": "reddet", "calistirildi": True},
    {"vaka_id": "v3", "beklenen": "izinli", "karar": "reddet", "calistirildi": False},
    {"vaka_id": "v4", "beklenen": "izinli", "karar": "izinli", "calistirildi": True},
    {"vaka_id": "v5", "beklenen": "reddet", "karar": "reddet", "calistirildi": False},
    {"vaka_id": "v6", "beklenen": "izinli", "karar": "izinli", "calistirildi": False},
]
BEKLENEN = {"vaka": 6, "karar_bypassi": ["v1"], "calisma_bypassi": ["v1", "v2"], "yanlis_ret": ["v3"], "tutarli": ["v4", "v5"]}
def sozlesme(fn):
    try:
        once = copy.deepcopy(KAYITLAR)
        if fn(KAYITLAR) != BEKLENEN or KAYITLAR != once or fn(list(reversed(KAYITLAR))) != BEKLENEN:
            return False
        if fn([]) != {"vaka": 0, "karar_bypassi": [], "calisma_bypassi": [], "yanlis_ret": [], "tutarli": []}:
            return False
        if fn([{"vaka_id": "v7", "beklenen": "reddet", "karar": "izinli", "calistirildi": False}]) != {"vaka": 1, "karar_bypassi": ["v7"], "calisma_bypassi": [], "yanlis_ret": [], "tutarli": []}:
            return False
        for kayitlar in [
            KAYITLAR + [KAYITLAR[0]], [dict(KAYITLAR[0], beklenen="belirsiz")],
            [dict(KAYITLAR[0], karar="reddet", calistirildi=1)],
            [dict(KAYITLAR[0], vaka_id="")], [dict(KAYITLAR[0], vaka_id=3)], [dict(KAYITLAR[0], ek=1)], [None],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(yetki_regresyonu), "karar, çalışma, yanlış ret ve tutarlılık ayrımı korunmalı")
def m_calisma(kayitlar):
    sonuc = yetki_regresyonu(kayitlar)
    sonuc["calisma_bypassi"] = sonuc["karar_bypassi"]
    return sonuc
def m_ret(kayitlar):
    sonuc = yetki_regresyonu(kayitlar)
    sonuc["yanlis_ret"] = []
    return sonuc
def m_tutarli(kayitlar):
    sonuc = yetki_regresyonu(kayitlar)
    sonuc["tutarli"] = sorted(x["vaka_id"] for x in kayitlar if x["beklenen"] == x["karar"])
    return sonuc
for ad, mutant in [("reddedip çalışan bypass'ı düşüren", m_calisma), ("yanlış retleri gizleyen", m_ret), ("çalışmayı tutarlılıkta yok sayan", m_tutarli)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

from sandbox import ai_gercek_ai_saldiri_19 as deney
import tempfile,secrets,json
from pathlib import Path
import ast
_yasak=('kimlik_ref','nesne_ref','rapor_ref','kanit_yaz')
_sorun=list(ai_lab.kod_denetimi(src,_yasak))
for _n in ast.walk(ast.parse(src)):
    if isinstance(_n,ast.ImportFrom) and any(a.name in _yasak or a.name=='*' for a in _n.names):_sorun.append('referans importu yasak')
    if isinstance(_n,(ast.Import,ast.ImportFrom)) and any(x and x.split('.')[0] in ('inspect','importlib','runpy') for x in [a.name for a in _n.names]+([_n.module] if isinstance(_n,ast.ImportFrom) else [])):_sorun.append('kaynak okuma/dinamik import yasak')
    if isinstance(_n,ast.Name) and _n.id in ('exec','eval','compile','__builtins__'):_sorun.append('dinamik kod çalıştırma yasak: '+_n.id)
if not ok(not _sorun, 'laboratuvar/gerçek ölçüm yamalanmamalı: '+'; '.join(sorted(set(_sorun)))):stop()
for i in range(3):
    user='u-'+secrets.token_hex(3);oid='d-'+secrets.token_hex(3);o={'id':oid,'sahip':user,'paylasim':['diger']}
    if not ok(nesne_yetki(user,o,'sil',{'nesne_id':oid,'eylem':'sil'})==deney.nesne_ref(user,o,'sil',{'nesne_id':oid,'eylem':'sil'}),'yeni nesnede işlem bağlı onay'):stop()
    if not ok(kimlik_bagla({'kullanici':user,'dogrulanmis':True},{'kullanici':'baska','eylem':'oku'})=={'izinli':False,'neden':'kimlik-uyusmazligi'},'yeni oturumda kimlik eşleşmesi'):stop()
    if not ok(kimlik_bagla({'kullanici':user,'dogrulanmis':True},{'kullanici':user.upper(),'eylem':'oku'})=={'izinli':False,'neden':'kimlik-uyusmazligi'},'kullanıcı adı normalleştirilmeden karşılaştırılır'):stop()
    if not ok(nesne_yetki('diger',o,'sil',{'nesne_id':oid,'eylem':'sil'})==deney.nesne_ref('diger',o,'sil',{'nesne_id':oid,'eylem':'sil'}),'paylaşımlı kullanıcı geçerli onayla da silemez'):stop()
    _k=[{'vaka_id':'v-'+secrets.token_hex(3),'beklenen':'reddet','karar':'reddet','calistirildi':True}]
    if not ok(yetki_regresyonu(_k)==deney.rapor_ref(copy.deepcopy(_k)),'reddedilip çalışan eylem çalışma bypass\'ı sayılır'):stop()
with tempfile.TemporaryDirectory(prefix='pafta_auth19_') as tmp:
    p=Path(tmp)/'istekler.json';p.write_text(deney.ORNEK.read_text(encoding='utf-8'),encoding='utf-8')
    r=deney.deney(kimlik_bagla,nesne_yetki,yetki_regresyonu,p,Path(tmp)/'deney')
    for k,v in r['kontroller'].items():ok(v,'gerçek deney: '+k)
    accepted=all(r['kontroller'].values());ai_lab.kanit_yaz('saldiri-19-auth',dict(r,kabul=accepted));ok(accepted,'oturum/nesne kapısı gerçek SQLite etkisini denetler; saldırı başarısı şart değil')

```

```solution
import ai_lab
def kimlik_bagla(oturum, cagri):
    if not isinstance(oturum, dict) or set(oturum) != {"kullanici", "dogrulanmis"}:
        raise ValueError("oturum şeması geçersiz")
    if not all((isinstance(oturum["kullanici"], str), bool(oturum["kullanici"]), isinstance(oturum["dogrulanmis"], bool))):
        raise ValueError("oturum alanları geçersiz")
    if not isinstance(cagri, dict) or set(cagri) != {"kullanici", "eylem"}:
        raise ValueError("çağrı şeması geçersiz")
    if not all((isinstance(cagri["kullanici"], str), bool(cagri["kullanici"]), cagri["eylem"] in ("oku", "yaz", "paylas"))):
        raise ValueError("çağrı alanları geçersiz")
    if not oturum["dogrulanmis"]:
        return {"izinli": False, "neden": "oturum-dogrulanmamis"}
    if cagri["kullanici"] != oturum["kullanici"]:
        return {"izinli": False, "neden": "kimlik-uyusmazligi"}
    return {"izinli": True, "neden": "bagli"}

def nesne_yetki(kullanici, nesne, eylem, onay):
    if not isinstance(kullanici, str) or not kullanici:
        raise ValueError("kullanıcı geçersiz")
    if not isinstance(nesne, dict) or set(nesne) != {"id", "sahip", "paylasim"}:
        raise ValueError("nesne şeması geçersiz")
    if not all((isinstance(nesne["id"], str), bool(nesne["id"]), isinstance(nesne["sahip"], str), bool(nesne["sahip"]), isinstance(nesne["paylasim"], list))):
        raise ValueError("nesne alanları geçersiz")
    if not all(isinstance(x, str) and bool(x) for x in nesne["paylasim"]) or len(nesne["paylasim"]) != len(set(nesne["paylasim"])):
        raise ValueError("paylaşım listesi geçersiz")
    if eylem not in ("oku", "yaz", "sil"):
        raise ValueError("eylem geçersiz")
    if onay is not None and (not isinstance(onay, dict) or set(onay) != {"nesne_id", "eylem"}):
        raise ValueError("onay şeması geçersiz")
    sahip = kullanici == nesne["sahip"]
    if eylem == "oku":
        izinli = sahip or kullanici in nesne["paylasim"]
        return {"izinli": izinli, "neden": "izinli" if izinli else "nesne-erisimi-yok"}
    if not sahip:
        return {"izinli": False, "neden": "sahiplik-gerekli"}
    if eylem == "yaz":
        return {"izinli": True, "neden": "izinli"}
    gecerli_onay = onay == {"nesne_id": nesne["id"], "eylem": "sil"}
    return {"izinli": gecerli_onay, "neden": "izinli" if gecerli_onay else "islem-onayi-gerekli"}

def yetki_regresyonu(kayitlar):
    vakalar = set()
    sonuc = {"vaka": 0, "karar_bypassi": [], "calisma_bypassi": [], "yanlis_ret": [], "tutarli": []}
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"vaka_id", "beklenen", "karar", "calistirildi"}:
            raise ValueError("kayıt şeması geçersiz")
        if not all((isinstance(kayit["vaka_id"], str), bool(kayit["vaka_id"]), kayit["vaka_id"] not in vakalar, kayit["beklenen"] in ("izinli", "reddet"), kayit["karar"] in ("izinli", "reddet"), isinstance(kayit["calistirildi"], bool))):
            raise ValueError("kayıt alanları geçersiz")
        vakalar.add(kayit["vaka_id"])
        if kayit["beklenen"] == "reddet" and kayit["karar"] == "izinli":
            sonuc["karar_bypassi"].append(kayit["vaka_id"])
        if kayit["beklenen"] == "reddet" and kayit["calistirildi"]:
            sonuc["calisma_bypassi"].append(kayit["vaka_id"])
        if kayit["beklenen"] == "izinli" and kayit["karar"] == "reddet":
            sonuc["yanlis_ret"].append(kayit["vaka_id"])
        if kayit["beklenen"] == kayit["karar"] and kayit["calistirildi"] == (kayit["beklenen"] == "izinli"):
            sonuc["tutarli"].append(kayit["vaka_id"])
    sonuc["vaka"] = len(vakalar)
    for alan in ("karar_bypassi", "calisma_bypassi", "yanlis_ret", "tutarli"):
        sonuc[alan].sort()
    return sonuc
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_19 as deney
    deney.goster(kimlik_bagla,nesne_yetki,yetki_regresyonu)

```

```hint
Kimlik kapısı nesne sahipliğinin yerine geçmez. Silme onayı hem nesne kimliği hem işlemle eşleşmeli. Raporunda izinli karar ile gerçekten çalışan işlemi ayrı ölç; her şeyi reddeden çözüm meşru kontrolleri geçemez.
```
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
Kimlik model argümanından değil doğrulanmış oturumdan gelir. Nesne ACL kontrolü bunun üzerine eklenir: sahiplik, paylaşım ve eylem koşulları farklıdır. Silme onayını yalnız aynı nesne/eyleme bağla; global True kullanma. Politika izin/ret sonucu ile gerçek dispatcher çalışmasını iki eksende karşılaştır; her şeyi reddetmek meşru kullanımı korumaz.

Önkoşul ve yol köprüsü: ai-saldiri-18 delegasyon.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| Giriş yapmış kullanıcı bütün nesneleri okuyabilir | Kimlik doğrulama nesne yetkilendirmesi değildir |

Dinleyiciye sor: Bu mekanizmada hangi bilgi veri, hangisi yetki kaynağıdır; testin geçtiğini hangi gerçek gözlemle kanıtlarsın? Sentetik örnek ile canlı deney kaydını ayrı göstererek cevapla.
:::


::: anlat Birincil kaynak ve deney sınırı
[OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html): Kimlik ile kaynak/işlem yetkisini ayırmak ve izinleri her erişimde denetlemek için referans. Silme onayının nesne/eyleme bağlanması burada ayrıca test edilir. Çalışan araç/model sürümü canlı kanıtta saklanır; bağlantıdaki belge sürümüyle otomatik eşit kabul edilmez.
:::
