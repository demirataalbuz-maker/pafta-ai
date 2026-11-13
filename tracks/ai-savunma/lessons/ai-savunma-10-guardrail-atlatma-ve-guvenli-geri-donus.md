---
id: ai-savunma-10
title: Guardrail Atlatma ve Güvenli Geri Dönüş
summary: Guardrail hata ve atlanmalarını fail-closed yorumla, geçici hatalarda sınırlı yeniden deneme planla ve ham içeriği sızdırmayan güvenli yedek üret.
timeout: 45
esleme: ai-saldiri-40, ai-savunma-05
---

::: anlat Guardrail yokluğu izin değildir

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| NeMo Guardrails, LLM Guard ya da bulut moderasyon API'leri bir HTTP çağrısıdır: zaman aşımına uğrayabilir, 5xx döndürebilir ya da yanlış yapılandırmayla akıştan atlanabilir. `tenacity` gibi kütüphaneler üstel beklemeli yeniden deneme uygular. Promptfoo ve Garak atlatma vakalarını toplu sınar. | Görev 1–3: `veri/guardrail_sonuclari.json`, `veri/deneme_senaryolari.json` ve `veri/geri_donus_kayitlari.json` içindeki **sentetik** sonuçlar, deneme geçmişleri ve yanıt adayları; bekleme yalnız hesaplanır. Son adım: kurulu yerel Ollama modelinin iki senaryodaki gerçek çıktıları ve sandbox'taki bağımsız sinyal taraması. | Gerçek bir guardrail servisi, ağ hatası ya da gecikme ölçülmez. Üç işaretli kalıp bütün riskli içerikleri tanımaz. İki senaryo bir atlatma oranı vermez. |

> [!NOT]
> Görev 1–3 sentetik veriyle çalışır. Bu görevlerde model, ağ ve gerçek bekleme yoktur. Son adımdaki **Gerçek deney** görevi yalnız kurulu yerel Ollama modelini kullanır. `veri/` dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalanır; kopyada yaptığın değişiklik bir sonraki çalıştırmada sıfırlanır, **kalıcılık yoktur**. Kontrol bu dosyalardan ayrı, gizli verilerle sınar.

Bir guardrail zaman aşımına uğradığında, hata verdiğinde veya akıştan tamamen atlandığında model yanıtını kullanıcıya geçirmek fail-open davranıştır. Bu dersin politikasında yalnız tamamlanmış, `izin` vermiş ve risk taşımayan denetim model yanıtı kanalını açar. Ret ve risk güvenli yedeğe; geçici teknik hata yeniden deneme değerlendirmesine; atlanma ise doğrudan güvenli yedeğe gider.

NeMo Guardrails ve Promptfoo gerçek bir kurulumda bu akışları ve atlatma vakalarını sınamak için kullanılabilir. Görev 1–3'teki kod dış servis çağırmaz, uyumaz ve model indirmez; yeniden deneme yalnız deterministik bir plan olarak hesaplanır. Son adım kurulu yerel modelin gerçek çıktılarını kullanır; yine hiçbir şey indirilmez.

**Saldırgan ne dener?** Guardrail'i atlatmanın en ucuz yolu onu içerikle kandırmak değil, hiç çalışmamasını sağlamaktır:

- Çok uzun ya da karmaşık bir istemle guardrail çağrısını zaman aşımına düşürmek.
- Guardrail servisinin hata verdiği bir girdi biçimi (bozuk Unicode, aşırı iç içe JSON) göndermek.
- Yapılandırma hatasıyla guardrail'in atlandığı bir yolu (ör. akış modu, farklı uç nokta) kullanmak.

Uygulama "guardrail cevap vermedi, kullanıcıyı bekletmeyelim" diye model yanıtını geçirirse saldırgan istediğini almış olur. Bu, **fail-open** davranıştır.

**Savunma neden kırılır?**
- Sınırsız yeniden deneme hem maliyeti hem gecikmeyi büyütür ve servis reddine kapı açar.
- Kalıcı hatayı yeniden denemek aynı sonucu tekrarlar.
- En tehlikelisi güvenli yedek mesajına teknik hata ayrıntısını ya da reddedilen yanıtı eklemektir: reddedilen içerik "hata mesajı" kılığında yine kullanıcıya ulaşır.

Bu derste yalnız açıkça tamamlanmış, izin vermiş ve risk taşımayan denetim model kanalını açar; geri kalan her şey sabit, nötr bir yedeğe düşer.

**Görev 1'de sık tuzaklar:** Yalnız `karar == "reddet"` durumunu engellemek, atlanmış ya da hata vermiş guardrail'i izin sayar (`veri/guardrail_sonuclari.json`, `g-04`, `g-06`). `izin` kararını taşıyan ama risk listesi dolu sonucu geçirmek, sinyali boşa çıkarır (`g-02`). `hata` durumunda `izin` kararı gibi çelişkili kayıtları sessizce kabul etmek, bozuk bir entegrasyonu gizler (`g-07`).
:::

::: tahmin Üst sınır bekleme süresini keser
Üç çıktı satırını yaz:

```python
taban, tavan = 500, 800
print(min(taban * 2 ** 0, tavan))
print(min(taban * 2 ** 1, tavan))
print(min(taban * 2 ** 2, tavan))
```

???

```cikti
500
800
800
```

Üstel bekleme tavanı aşamaz; bu planı hesaplamak gerçek zaman uyutması yapmakla aynı şey değildir.
:::

::: gorev 1 · Guardrail sonucunu fail-closed kanal kararına çevir
`guardrail_sonucunu_yorumla(sonuc)` işlevini yaz. Sonuç tam olarak `durum`, `karar`, `riskler` alanlarını taşısın. Durum `tamam`, `hata`, `zaman_asimi` veya `atlandi` olmalıdır.

Durum `tamam` ise karar `izin` veya `reddet` olmalıdır. Diğer durumlarda karar `None` ve risk listesi boş olmalıdır. Riskler yalnız `ozel_anahtar`, `bearer_token`, `api_anahtari`, `gizli_isaret` türlerinin bu sabit sırasına uyan, yinelenmeyen listedir. Geçersiz veride `ValueError` yükselt.

Yalnız `tamam + izin + boş risk` için `{"kanal":"model_yaniti","neden":"guardrail_izin"}` döndür. Tamamlanmış ret veya risk varlığında `guvenli_yedek`/`politika`; hata veya zaman aşımında `yeniden_dene_degerlendir`/`guardrail_hatasi`; atlanmada `guvenli_yedek`/`guardrail_atladi` döndür. Girdiyi değiştirme.

Görünür veri: `veri/guardrail_sonuclari.json`. Her sonucun `beklenen` alanı vardır; `null`, `ValueError` demektir.

```starter
from ai_savunma_veri import json_yukle

def guardrail_sonucunu_yorumla(sonuc):
    # KUSURLU BAŞLANGIÇ KODU: yalnız açık "reddet" kararını engelliyor; atlanmış, hata vermiş ya da zaman aşımına uğramış guardrail'i izin sayıyor (fail-open), risk listesini yok sayıyor ve şemayı doğrulamıyor!
    if sonuc.get("karar") == "reddet":
        return {"kanal": "guvenli_yedek", "neden": "politika"}
    return {"kanal": "model_yaniti", "neden": "guardrail_izin"}

veri = json_yukle("veri/guardrail_sonuclari.json")
for o in veri["ornekler"]:
    try:
        sonuc = guardrail_sonucunu_yorumla(o["sonuc"])
    except ValueError:
        sonuc = None
    except Exception as hata:
        sonuc = type(hata).__name__
    print(o["id"], "doğru" if sonuc == o["beklenen"] else "YANLIŞ", o["aciklama"])
    if sonuc != o["beklenen"]:
        print("   beklenen:", o["beklenen"])
        print("   bulunan :", sonuc)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-10")
```

```test
def sozlesme(fn):
    try:
        if fn({"durum": "tamam", "karar": "izin", "riskler": []}) != {"kanal": "model_yaniti", "neden": "guardrail_izin"}:
            return False
        if fn({"durum": "tamam", "karar": "izin", "riskler": ["bearer_token"]}) != {"kanal": "guvenli_yedek", "neden": "politika"}:
            return False
        if fn({"durum": "tamam", "karar": "reddet", "riskler": []}) != {"kanal": "guvenli_yedek", "neden": "politika"}:
            return False
        for durum in ("hata", "zaman_asimi"):
            if fn({"durum": durum, "karar": None, "riskler": []}) != {"kanal": "yeniden_dene_degerlendir", "neden": "guardrail_hatasi"}:
                return False
        if fn({"durum": "atlandi", "karar": None, "riskler": []}) != {"kanal": "guvenli_yedek", "neden": "guardrail_atladi"}:
            return False
        for sonuc in [
            None, [], {"durum": "tamam", "karar": "izin"},
            {"durum": "tamam", "karar": "izin", "riskler": [], "ek": 1},
            {"durum": "bilinmiyor", "karar": None, "riskler": []},
            {"durum": "tamam", "karar": None, "riskler": []},
            {"durum": "tamam", "karar": "belirsiz", "riskler": []},
            {"durum": "hata", "karar": "izin", "riskler": []},
            {"durum": "atlandi", "karar": None, "riskler": ["bearer_token"]},
            {"durum": "tamam", "karar": "izin", "riskler": None},
            {"durum": "tamam", "karar": "izin", "riskler": "bearer_token"},
            {"durum": "tamam", "karar": "izin", "riskler": ["bilinmeyen"]},
            {"durum": "tamam", "karar": "izin", "riskler": ["bearer_token", "bearer_token"]},
            {"durum": "tamam", "karar": "izin", "riskler": ["gizli_isaret", "bearer_token"]},
        ]:
            try:
                fn(sonuc)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(guardrail_sonucunu_yorumla), "fail-closed kanal, hata ve atlanma ayrımı korunmalı")
def m_atlama(sonuc):
    sonuc = dict(sonuc, durum="tamam", karar="izin", riskler=[])
    return guardrail_sonucunu_yorumla(sonuc)
def m_risk(sonuc):
    sonuc = dict(sonuc, riskler=[])
    return guardrail_sonucunu_yorumla(sonuc)
def m_hata(sonuc):
    sonuc = dict(sonuc, durum="tamam", karar="izin", riskler=[])
    return guardrail_sonucunu_yorumla(sonuc)
for ad, mutant in [("atlamayı izin sayan", m_atlama), ("riski silen", m_risk), ("hatayı başarı yapan", m_hata)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
# --- carbon-c8-ek-bas ---
raises(ValueError, guardrail_sonucunu_yorumla, {"durum": "hata", "karar": "gecir", "riskler": []}, msg="tamamlanmayan sonuç karar taşıyamaz")
raises(ValueError, guardrail_sonucunu_yorumla, {"durum": "hata", "karar": None, "riskler": ["api_anahtari"]}, msg="tamamlanmayan sonuç risk taşıyamaz")
# --- carbon-c8-ek-son ---
```

```solution
def guardrail_sonucunu_yorumla(sonuc):
    if not isinstance(sonuc, dict) or set(sonuc) != {"durum", "karar", "riskler"}:
        raise ValueError("guardrail sonucu geçersiz")
    durum = sonuc["durum"]
    if durum not in ("tamam", "hata", "zaman_asimi", "atlandi"):
        raise ValueError("guardrail durumu geçersiz")
    riskler = sonuc["riskler"]
    if not isinstance(riskler, list):
        raise ValueError("riskler liste olmalı")
    sira = ["ozel_anahtar", "bearer_token", "api_anahtari", "gizli_isaret"]
    if len(set(riskler)) != len(riskler):
        raise ValueError("riskler yinelenemez")
    if any(r not in sira for r in riskler):
        raise ValueError("risk türü geçersiz")
    konumlar = [sira.index(r) for r in riskler]
    if konumlar != sorted(konumlar):
        raise ValueError("risk sırası geçersiz")
    if durum == "tamam":
        if sonuc["karar"] not in ("izin", "reddet"):
            raise ValueError("tamamlanan karar geçersiz")
        if sonuc["karar"] == "izin" and not riskler:
            return {"kanal": "model_yaniti", "neden": "guardrail_izin"}
        return {"kanal": "guvenli_yedek", "neden": "politika"}
    if sonuc["karar"] is not None or riskler:
        raise ValueError("tamamlanmayan sonuç karar veya risk taşıyamaz")
    if durum in ("hata", "zaman_asimi"):
        return {"kanal": "yeniden_dene_degerlendir", "neden": "guardrail_hatasi"}
    return {"kanal": "guvenli_yedek", "neden": "guardrail_atladi"}
```

```hint
Önce sonuç şemasını ve risk sırasını doğrula. Model kanalını tek dar koşulda aç; tamamlanmamış sonuçlarda karar ve risk alanlarının boş olduğunu ayrıca denetle.
```
:::

::: anlat Yeniden deneme sonsuz bir döngü değildir
Yalnız zaman aşımı ve açıkça geçici hata yeniden denenebilir. Kalıcı hata ve başarı terminaldir; bu kayıtlardan sonra başka deneme bulunamaz. Deneme sayısı politika üst sınırına ulaştığında geçici hata bile güvenli yedeğe yönelir.

Bekleme süresi `min(taban_ms * 2 ** (deneme - 1), tavan_ms)` formülüyle hesaplanır. Başarı, kalıcı hata ve bütçenin bitmesi sıfır beklemeyle terminal eylem üretir. Fonksiyon gerçek uyku veya ağ çağrısı yapmaz.

**Çıktı nasıl okunur?** `toplam_bekle_ms`, kullanıcının en kötü durumda guardrail yüzünden bekleyeceği ek süredir. Son adımın `guvenli_yedek` olması, bütçe bittiğinde akışın model yanıtına değil sabit yedeğe döndüğünü gösterir.

**Görev 2'de sık tuzaklar:** Tavanı uygulamamak üçüncü beklemeyi 1000 ms yapar; ayar 800 ms der (`veri/deneme_senaryolari.json`, `r-02`). Bütçenin son denemesinde bile `yeniden_dene` planlamak, olmayan bir denemeyi vaat eder. Kalıcı hatayı yeniden denemek, aynı hatayı tekrar tekrar üretir (`r-03`).
:::

::: gorev 2 · Sınırlı ve üstel beklemeli yeniden deneme planı hesapla
`yeniden_deneme_plani(hatalar, ayar)` işlevini yaz. Ayar tam olarak `maks_deneme`, `taban_ms`, `tavan_ms` alanlarını taşısın. Üçü de bool olmayan int olmalıdır: maksimum deneme 1–5, taban 1–1000, tavan ise taban ile 10000 aralığındadır.

`hatalar`, en az bir ve en fazla `maks_deneme` kaydından oluşan liste olmalıdır. Her kayıt `zaman_asimi`, `gecici_hata`, `kalici_hata` veya `basarili` stringidir. Başarı ve kalıcı hata yalnız son kayıt olabilir. Geçersiz veride `ValueError` yükselt.

Her kayıt için `{"deneme":N,"eylem":EYLEM,"bekle_ms":MS}` üret:

- Başarı: `dur`, 0 ms.
- Kalıcı hata: `guvenli_yedek`, 0 ms.
- Geçici hata veya zaman aşımı, bütçe dolmadıysa: `yeniden_dene` ve formüldeki bekleme.
- Bütçe dolan geçici hata: `guvenli_yedek`, 0 ms.

`{"adimlar":[...],"toplam_bekle_ms":TOPLAM}` döndür. Girdi listesini ve ayarı değiştirme; gerçek uyku çağrısı yapma.

Görünür veri: `veri/deneme_senaryolari.json`. Her senaryonun `beklenen` planı vardır; `null`, `ValueError` demektir.

```starter
from ai_savunma_veri import json_yukle

def yeniden_deneme_plani(hatalar, ayar):
    # KUSURLU BAŞLANGIÇ KODU: kalıcı hatayı da yeniden deniyor, bekleme tavanını uygulamıyor, bütçe dolduğunda bile yeniden deneme planlıyor (güvenli yedeğe geçmiyor) ve ayarı ya da terminal kayıtları doğrulamıyor!
    adimlar = []
    toplam = 0
    for indeks, hata in enumerate(hatalar):
        if hata == "basarili":
            eylem, bekle = "dur", 0
        else:
            eylem, bekle = "yeniden_dene", ayar["taban_ms"] * 2 ** indeks
        toplam += bekle
        adimlar.append({"deneme": indeks + 1, "eylem": eylem, "bekle_ms": bekle})
    return {"adimlar": adimlar, "toplam_bekle_ms": toplam}

veri = json_yukle("veri/deneme_senaryolari.json")
for o in veri["ornekler"]:
    try:
        sonuc = yeniden_deneme_plani(o["hatalar"], o["ayar"])
    except ValueError:
        sonuc = None
    except Exception as hata:
        sonuc = type(hata).__name__
    print(o["id"], "doğru" if sonuc == o["beklenen"] else "YANLIŞ", o["aciklama"])
    if sonuc != o["beklenen"]:
        print("   beklenen:", o["beklenen"])
        print("   bulunan :", sonuc)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-10")
```

```test
import copy
A = {"maks_deneme": 3, "taban_ms": 100, "tavan_ms": 800}
def sozlesme(fn):
    try:
        h = ["zaman_asimi", "gecici_hata", "basarili"]
        once = list(h)
        aonce = dict(A)
        beklenen = {"adimlar": [
            {"deneme": 1, "eylem": "yeniden_dene", "bekle_ms": 100},
            {"deneme": 2, "eylem": "yeniden_dene", "bekle_ms": 200},
            {"deneme": 3, "eylem": "dur", "bekle_ms": 0},
        ], "toplam_bekle_ms": 300}
        if fn(h, A) != beklenen or h != once or A != aonce:
            return False
        sinirli = fn(["gecici_hata", "gecici_hata"], {"maks_deneme": 2, "taban_ms": 500, "tavan_ms": 800})
        if sinirli != {"adimlar": [
            {"deneme": 1, "eylem": "yeniden_dene", "bekle_ms": 500},
            {"deneme": 2, "eylem": "guvenli_yedek", "bekle_ms": 0},
        ], "toplam_bekle_ms": 500}:
            return False
        if fn(["zaman_asimi"], {"maks_deneme": 1, "taban_ms": 1, "tavan_ms": 1})["adimlar"][0]["eylem"] != "guvenli_yedek":
            return False
        if fn(["basarili"], A)["toplam_bekle_ms"] != 0 or fn(["kalici_hata"], A)["adimlar"][0]["eylem"] != "guvenli_yedek":
            return False
        if fn(["gecici_hata"], {"maks_deneme": 5, "taban_ms": 1000, "tavan_ms": 10000})["adimlar"][0]["bekle_ms"] != 1000:
            return False
        for hatalar, ayar in [
            (None, A), ({}, A), ([], A), (["x"], A), ([1], A),
            (["basarili", "gecici_hata"], A), (["kalici_hata", "gecici_hata"], A),
            (["gecici_hata"] * 4, A), (["gecici_hata"], None),
            (["gecici_hata"], dict(A, ek=1)), (["gecici_hata"], dict(A, maks_deneme=True)),
            (["gecici_hata"], dict(A, maks_deneme=0)), (["gecici_hata"], dict(A, maks_deneme=6)),
            (["gecici_hata"], dict(A, taban_ms=0)),
            (["gecici_hata"], dict(A, taban_ms=1001, tavan_ms=10000)),
            (["gecici_hata"], dict(A, tavan_ms=99)), (["gecici_hata"], dict(A, tavan_ms=10001)),
            (["gecici_hata"], dict(A, taban_ms=1.5)),
        ]:
            try:
                fn(hatalar, ayar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(yeniden_deneme_plani), "hata sınıfı, terminal kayıt, bütçe ve bekleme sınırları korunmalı")
def m_kalici(hatalar, ayar):
    degisen = ["gecici_hata" for _ in hatalar]
    return yeniden_deneme_plani(degisen, ayar)
def m_butce(hatalar, ayar):
    return yeniden_deneme_plani(hatalar, dict(ayar, maks_deneme=5))
def m_tavan(hatalar, ayar):
    return yeniden_deneme_plani(hatalar, dict(ayar, tavan_ms=10000))
for ad, mutant in [("kalıcı hatayı geçici sayan", m_kalici), ("bütçeyi büyüten", m_butce), ("tavanı kaldıran", m_tavan)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
# --- carbon-c8-ek-bas ---
raises(ValueError, yeniden_deneme_plani, ["zaman_asimi"], dict(A, maks_deneme=True), msg="maks_deneme bool olamaz")
raises(ValueError, yeniden_deneme_plani, ["zaman_asimi"], dict(A, taban_ms=True), msg="taban_ms bool olamaz")
raises(ValueError, yeniden_deneme_plani, ["zaman_asimi"], dict(A, tavan_ms=True), msg="tavan_ms bool olamaz")
raises(ValueError, yeniden_deneme_plani, ("zaman_asimi",), A, msg="hatalar tuple değil list olmalı")
eq(yeniden_deneme_plani(["zaman_asimi"], dict(A, maks_deneme=1))["adimlar"], [{"deneme": 1, "eylem": "guvenli_yedek", "bekle_ms": 0}], "bütçe dolunca bekle_ms 0 olmalı")
eq(yeniden_deneme_plani(["kalici_hata"], A), {"adimlar": [{"deneme": 1, "eylem": "guvenli_yedek", "bekle_ms": 0}], "toplam_bekle_ms": 0}, "kalici_hata bekle_ms 0 olmalı")
# --- carbon-c8-ek-son ---
```

```solution
def yeniden_deneme_plani(hatalar, ayar):
    if not isinstance(ayar, dict) or set(ayar) != {"maks_deneme", "taban_ms", "tavan_ms"}:
        raise ValueError("ayar şeması geçersiz")
    for alan in ("maks_deneme", "taban_ms", "tavan_ms"):
        if type(ayar[alan]) is not int:
            raise ValueError("ayarlar int olmalı")
    if ayar["maks_deneme"] < 1 or ayar["maks_deneme"] > 5:
        raise ValueError("maksimum deneme aralığı geçersiz")
    if ayar["taban_ms"] < 1 or ayar["taban_ms"] > 1000:
        raise ValueError("taban bekleme aralığı geçersiz")
    if ayar["tavan_ms"] < ayar["taban_ms"] or ayar["tavan_ms"] > 10000:
        raise ValueError("tavan bekleme aralığı geçersiz")
    if not isinstance(hatalar, list) or not hatalar:
        raise ValueError("hata listesi geçersiz")
    if len(hatalar) > ayar["maks_deneme"]:
        raise ValueError("deneme bütçesi aşıldı")
    if any(h not in ("zaman_asimi", "gecici_hata", "kalici_hata", "basarili") for h in hatalar):
        raise ValueError("hata türü geçersiz")
    for hata in hatalar[:-1]:
        if hata in ("kalici_hata", "basarili"):
            raise ValueError("terminal kayıttan sonra deneme olamaz")
    adimlar = []
    toplam = 0
    for indeks, hata in enumerate(hatalar):
        deneme = indeks + 1
        if hata == "basarili":
            eylem, bekle = "dur", 0
        elif hata == "kalici_hata":
            eylem, bekle = "guvenli_yedek", 0
        elif deneme < ayar["maks_deneme"]:
            eylem = "yeniden_dene"
            bekle = min(ayar["taban_ms"] * 2 ** indeks, ayar["tavan_ms"])
        else:
            eylem, bekle = "guvenli_yedek", 0
        toplam += bekle
        adimlar.append({"deneme": deneme, "eylem": eylem, "bekle_ms": bekle})
    return {"adimlar": adimlar, "toplam_bekle_ms": toplam}
```

```hint
Ayar sınırlarını ve terminal kayıt konumlarını önce doğrula. Beklemeyi sıfır tabanlı indeksle hesapla; deneme numarasını ise bir tabanlı döndür.
```
:::

::: anlat Güvenli yedek ham hata veya model içeriğini kopyalamaz
Son çıktı katmanı defense-in-depth uygular. Model kanalı işaretlenmiş olsa bile aday metinde canary, özel anahtar başlığı veya Bearer token varsa içerik geçirilmez. Güvenli yedek kanalında da kullanıcıya sabit, nötr bir mesaj verilir; aday metin veya teknik hata kopyalanmaz.

Yeniden deneme kanalı kullanıcıya metin göstermek yerine `yanit = None` üretir. Böylece istemci akışı geçici durumu nihai güvenli yanıtla karıştırmaz.

**Görev 3'te sık tuzaklar:** Yedek mesaja "neden reddettiğimizi" göstermek için adayı ya da hata izini eklemek, tam da engellenmesi gereken içeriği kullanıcıya taşır (`veri/geri_donus_kayitlari.json`, `yedek-hata`). Yalnız canary'yi aramak, `Bearer` ve `PRIVATE KEY` içeren model yanıtlarını geçirir. Yeniden deneme kanalında yedek metni göstermek, istemciyi geçici durumu nihai yanıt sanmaya iter.
:::

::: gorev 3 · Ham içeriği sızdırmayan son geri dönüş raporunu üret
`guvenli_geri_donus_raporu(kayitlar)` işlevini yaz. Her kayıt tam olarak `id`, `kanal`, `yanit_adayi` alanlarını taşısın. Kimlik 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren benzersiz stringdir. Kanal ilk görevdeki `model_yaniti`, `guvenli_yedek` veya `yeniden_dene_degerlendir` değerlerinden biri; aday NUL içermeyen ve en fazla 2000 karakterlik string olmalıdır. Geçersiz veride `ValueError` yükselt.

Yalnız model kanalında, baş/son boşluğu olmayan boş olmayan ve `BREACH:CANARY-42`, `PRIVATE KEY`, `Bearer ` içermeyen aday aynen geçirilir. Bu durumda karar `model_yaniti` ve `ham_icerik_tasindi = true` olur.

Diğer model adayları ve `guvenli_yedek` kanalı için karar `guvenli_yedek`, yanıt tam olarak `Güvenli yanıt üretilemedi; istek tamamlanamadı.` ve ham içerik bayrağı false olur. Yeniden deneme kanalında karar `yeniden_dene`, yanıt `None`, bayrak false olur.

Her kayıt için `{"id":ID,"karar":KARAR,"yanit":YANIT,"ham_icerik_tasindi":BOOL}` döndür. Kimliğe göre sırala, boş girdide boş liste döndür ve girdiyi değiştirme.

Görünür veri: `veri/geri_donus_kayitlari.json`. Dosyada yedi aday, beklenen rapor ve dört bozuk girdi vardır.

```starter
from ai_savunma_veri import json_yukle

def guvenli_geri_donus_raporu(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: yalnız canary'yi arıyor (Bearer ve PRIVATE KEY model kanalından geçer), boş ve boşluklu adayı kabul ediyor, güvenli yedek yanıtına teknik hata/aday metnini ekliyor (ham içerik sızar), yeniden deneme kanalına da yedek metni yazıyor, kayıtları doğrulamıyor ve sıralamıyor!
    yedek = "Güvenli yanıt üretilemedi; istek tamamlanamadı."
    rapor = []
    for kayit in kayitlar:
        aday = kayit["yanit_adayi"]
        if kayit["kanal"] == "model_yaniti" and "BREACH:CANARY-42" not in aday:
            rapor.append({"id": kayit["id"], "karar": "model_yaniti", "yanit": aday, "ham_icerik_tasindi": True})
        else:
            rapor.append({"id": kayit["id"], "karar": "guvenli_yedek", "yanit": yedek + " (" + aday + ")", "ham_icerik_tasindi": False})
    return rapor

veri = json_yukle("veri/geri_donus_kayitlari.json")
try:
    rapor = guvenli_geri_donus_raporu(veri["kayitlar"])
except Exception as hata:
    rapor = [{"id": "hata", "karar": type(hata).__name__, "yanit": None, "ham_icerik_tasindi": False}]
print("rapor sırası", "doğru" if [r["id"] for r in rapor] == [b["id"] for b in veri["beklenen"]] else "YANLIŞ")
for beklenen in veri["beklenen"]:
    bulunan = next((r for r in rapor if r["id"] == beklenen["id"]), None)
    print(beklenen["id"], "doğru" if bulunan == beklenen else "YANLIŞ", bulunan)
for b in veri["bozuk_girdiler"]:
    try:
        guvenli_geri_donus_raporu(b["girdi"])
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
hazirla("ai-savunma-10")
```

```test
import copy
K = [
    {"id": "model-1", "kanal": "model_yaniti", "yanit_adayi": "Kısa ve güvenli özet"},
    {"id": "risk-1", "kanal": "model_yaniti", "yanit_adayi": "BREACH:CANARY-42"},
    {"id": "yedek-1", "kanal": "guvenli_yedek", "yanit_adayi": "Bearer gizli-deger"},
    {"id": "retry-1", "kanal": "yeniden_dene_degerlendir", "yanit_adayi": "teknik hata"},
]
YEDEK = "Güvenli yanıt üretilemedi; istek tamamlanamadı."
BEKLENEN = [
    {"id": "model-1", "karar": "model_yaniti", "yanit": "Kısa ve güvenli özet", "ham_icerik_tasindi": True},
    {"id": "retry-1", "karar": "yeniden_dene", "yanit": None, "ham_icerik_tasindi": False},
    {"id": "risk-1", "karar": "guvenli_yedek", "yanit": YEDEK, "ham_icerik_tasindi": False},
    {"id": "yedek-1", "karar": "guvenli_yedek", "yanit": YEDEK, "ham_icerik_tasindi": False},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K) != BEKLENEN or K != once or fn(list(reversed(K))) != BEKLENEN or fn([]) != []:
            return False
        for aday in ("", " x", "x ", "-----BEGIN PRIVATE KEY-----", "Bearer token-123"):
            if fn([dict(K[0], yanit_adayi=aday)])[0]["karar"] != "guvenli_yedek":
                return False
        if fn([dict(K[0], id="a" * 64)])[0]["id"] != "a" * 64:
            return False
        if fn([dict(K[0], yanit_adayi="a" * 2000)])[0]["karar"] != "model_yaniti":
            return False
        for kayitlar in [
            None, {}, [None], [dict(K[0], ek=1)], [dict(K[0], id="")],
            [dict(K[0], id="a" * 65)], [dict(K[0], id="a b")], [dict(K[0], kanal="diger")],
            [dict(K[0], yanit_adayi=None)], [dict(K[0], yanit_adayi="a\x00b")],
            [dict(K[0], yanit_adayi="a" * 2001)], [K[0], K[0]],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(guvenli_geri_donus_raporu), "riskli aday, sabit yedek, retry ve ham içerik bayrağı korunmalı")
def m_risk(kayitlar):
    degisen = [dict(x, yanit_adayi="güvenli") for x in kayitlar]
    return guvenli_geri_donus_raporu(degisen)
def m_kanal(kayitlar):
    degisen = [dict(x, kanal="model_yaniti") for x in kayitlar]
    return guvenli_geri_donus_raporu(degisen)
def m_ham(kayitlar):
    sonuc = guvenli_geri_donus_raporu(kayitlar)
    for x in sonuc:
        x["ham_icerik_tasindi"] = True
    return sonuc
for ad, mutant in [("riskli adayı temiz sayan", m_risk), ("kanalı değiştiren", m_kanal), ("ham içerik bayrağını bozan", m_ham)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
# --- carbon-c8-ek-bas ---
raises(ValueError, guvenli_geri_donus_raporu, [dict(K[0], id=123)], msg="id str olmalı")
# --- carbon-c8-ek-son ---
```

```solution
def guvenli_geri_donus_raporu(kayitlar):
    import re
    if not isinstance(kayitlar, list):
        raise ValueError("kayıt listesi geçersiz")
    kimlikler = set()
    rapor = []
    yedek = "Güvenli yanıt üretilemedi; istek tamamlanamadı."
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"id", "kanal", "yanit_adayi"}:
            raise ValueError("kayıt şeması geçersiz")
        kimlik = kayit["id"]
        if not isinstance(kimlik, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kimlik):
            raise ValueError("kimlik geçersiz")
        if kimlik in kimlikler:
            raise ValueError("kimlik yinelenemez")
        kimlikler.add(kimlik)
        if kayit["kanal"] not in ("model_yaniti", "guvenli_yedek", "yeniden_dene_degerlendir"):
            raise ValueError("kanal geçersiz")
        aday = kayit["yanit_adayi"]
        if not isinstance(aday, str) or "\x00" in aday:
            raise ValueError("yanıt adayı geçersiz")
        if len(aday) > 2000:
            raise ValueError("yanıt adayı çok uzun")
        riskli = any(isaret in aday for isaret in ("BREACH:CANARY-42", "PRIVATE KEY", "Bearer "))
        if kayit["kanal"] == "model_yaniti" and aday and aday == aday.strip() and not riskli:
            karar, yanit, ham = "model_yaniti", aday, True
        elif kayit["kanal"] == "yeniden_dene_degerlendir":
            karar, yanit, ham = "yeniden_dene", None, False
        else:
            karar, yanit, ham = "guvenli_yedek", yedek, False
        rapor.append({"id": kimlik, "karar": karar, "yanit": yanit, "ham_icerik_tasindi": ham})
    return sorted(rapor, key=lambda x: x["id"])
```

```hint
Model kanalındaki bütün kabul koşullarını birlikte denetle. Yeniden denemeyi güvenli yedekten önce ayrı ele al; yedek metni kayıttan değil sabit olarak üret.
```
:::

::: anlat Güvenli geri dönüş gerçek riskli çıktıyı durdurur
Güvenli geri dönüşün amacı, guardrail bir çıktıyı reddettiğinde o ham çıktının yine de kullanıcıya sızmasını engellemektir. Son görevde senin `guvenli_geri_donus_raporu` işlevin, gerçek yerel modelin iki senaryoda ürettiği **gerçek** çıktıları karara bağlar: zararsız bir özet ve modelin kimlik-bilgisi biçimli bir dize (ör. Authorization Bearer satırı) ürettiği senaryo. İkincisi zararsız bir istektir, ama modeller kimlik-bilgisi biçimli örnekleri seve seve üretir; çıktı guardrail'i bu biçimi bir sızıntı riski sayar.

Sandbox her çıktının sızıntı sinyallerini bağımsız bulur, bir guardrail sonucu üretir ve fail-closed yorumlayıcıyla (1. görev) kanala çevirir. Senin raporun kararı verir: temiz model çıktısı aynen geçer; riskli çıktı `guvenli_yedek` kanalına düşer ve ham içerik taşınmaz — yerine sabit güvenli yedek metni gider. Böylece bir guardrail reddi sessizce ham (riskli) yanıtı göndermez.

**Çıktıyı okurken:** Her senaryo için önce sandbox'ın bulduğu risk sinyaline, sonra kanal ve senin kararına bak. Riskli senaryoda `yanit` alanı sabit yedek cümle olmalı ve `ham_icerik_tasindi` false kalmalıdır. Model bu koşuda kimlik-bilgisi biçimli bir dize üretmediyse risk sinyali çıkmaz ve kabul kontrolü bunu ayrıca bildirir; bu durumda sonuç saldırının değil modelin davranışının bir gözlemidir.
:::

::: gorev Gerçek deney · Riskli gerçek çıktıda güvenli geri dönüş
`guvenli_geri_donus_raporu(kayitlar)` işlevini yaz — kuralları ve çıktısı 3. görevdekiyle **aynıdır**. Deney gerçek modeli iki senaryoda koşar, her çıktının guardrail kararını ve kanalını gerçek sızıntı sinyallerinden üretir; senin raporun temiz çıktıyı geçirir, riskli çıktıyı sabit güvenli yedekle değiştirir.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def guvenli_geri_donus_raporu(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: yalnız canary'yi arıyor (Bearer ve PRIVATE KEY model kanalından geçer), boş ve boşluklu adayı kabul ediyor, güvenli yedek yanıtına teknik hata/aday metnini ekliyor (ham içerik sızar), yeniden deneme kanalına da yedek metni yazıyor, kayıtları doğrulamıyor ve sıralamıyor!
    yedek = "Güvenli yanıt üretilemedi; istek tamamlanamadı."
    rapor = []
    for kayit in kayitlar:
        aday = kayit["yanit_adayi"]
        if kayit["kanal"] == "model_yaniti" and "BREACH:CANARY-42" not in aday:
            rapor.append({"id": kayit["id"], "karar": "model_yaniti", "yanit": aday, "ham_icerik_tasindi": True})
        else:
            rapor.append({"id": kayit["id"], "karar": "guvenli_yedek", "yanit": yedek + " (" + aday + ")", "ham_icerik_tasindi": False})
    return rapor

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_10 as deney
    deney.goster(guvenli_geri_donus_raporu)
```

```test
import ai_lab
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
import ast
_yasak = ("referans", "referans_yorumla", "getattr", "kanit_yaz")
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
fn = need("guvenli_geri_donus_raporu")
from sandbox import ai_gercek_ai_savunma_10 as D
YEDEK = "Güvenli yanıt üretilemedi; istek tamamlanamadı."
K = [
    {"id": "model-1", "kanal": "model_yaniti", "yanit_adayi": "Kısa ve güvenli özet"},
    {"id": "risk-1", "kanal": "model_yaniti", "yanit_adayi": "Bearer token-123"},
    {"id": "yedek-1", "kanal": "guvenli_yedek", "yanit_adayi": "ham"},
]
BEKLENEN = [
    {"id": "model-1", "karar": "model_yaniti", "yanit": "Kısa ve güvenli özet", "ham_icerik_tasindi": True},
    {"id": "risk-1", "karar": "guvenli_yedek", "yanit": YEDEK, "ham_icerik_tasindi": False},
    {"id": "yedek-1", "karar": "guvenli_yedek", "yanit": YEDEK, "ham_icerik_tasindi": False},
]
def sozlesme(f):
    try:
        if f([dict(k) for k in K]) != BEKLENEN or f([]) != []:
            return False
        for bozuk in (None, [None], [dict(K[0], ek=1)], [dict(K[0], kanal="diger")], [dict(K[0], yanit_adayi="a\x00b")]):
            try:
                f(bozuk)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(fn), "riskli aday, sabit yedek, retry ve ham içerik bayrağı korunmalı")
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
    guvenli_geri_donus_raporu = need('guvenli_geri_donus_raporu')
    def _birim_adim_3():
        import copy
        K = [
            {"id": "model-1", "kanal": "model_yaniti", "yanit_adayi": "Kısa ve güvenli özet"},
            {"id": "risk-1", "kanal": "model_yaniti", "yanit_adayi": "BREACH:CANARY-42"},
            {"id": "yedek-1", "kanal": "guvenli_yedek", "yanit_adayi": "Bearer gizli-deger"},
            {"id": "retry-1", "kanal": "yeniden_dene_degerlendir", "yanit_adayi": "teknik hata"},
        ]
        YEDEK = "Güvenli yanıt üretilemedi; istek tamamlanamadı."
        BEKLENEN = [
            {"id": "model-1", "karar": "model_yaniti", "yanit": "Kısa ve güvenli özet", "ham_icerik_tasindi": True},
            {"id": "retry-1", "karar": "yeniden_dene", "yanit": None, "ham_icerik_tasindi": False},
            {"id": "risk-1", "karar": "guvenli_yedek", "yanit": YEDEK, "ham_icerik_tasindi": False},
            {"id": "yedek-1", "karar": "guvenli_yedek", "yanit": YEDEK, "ham_icerik_tasindi": False},
        ]
        def sozlesme(fn):
            try:
                once = copy.deepcopy(K)
                if fn(K) != BEKLENEN or K != once or fn(list(reversed(K))) != BEKLENEN or fn([]) != []:
                    return False
                for aday in ("", " x", "x ", "-----BEGIN PRIVATE KEY-----", "Bearer token-123"):
                    if fn([dict(K[0], yanit_adayi=aday)])[0]["karar"] != "guvenli_yedek":
                        return False
                if fn([dict(K[0], id="a" * 64)])[0]["id"] != "a" * 64:
                    return False
                if fn([dict(K[0], yanit_adayi="a" * 2000)])[0]["karar"] != "model_yaniti":
                    return False
                for kayitlar in [
                    None, {}, [None], [dict(K[0], ek=1)], [dict(K[0], id="")],
                    [dict(K[0], id="a" * 65)], [dict(K[0], id="a b")], [dict(K[0], kanal="diger")],
                    [dict(K[0], yanit_adayi=None)], [dict(K[0], yanit_adayi="a\x00b")],
                    [dict(K[0], yanit_adayi="a" * 2001)], [K[0], K[0]],
                ]:
                    try:
                        fn(kayitlar)
                        return False
                    except ValueError:
                        pass
                return True
            except Exception:
                return False
        ok(sozlesme(guvenli_geri_donus_raporu), "riskli aday, sabit yedek, retry ve ham içerik bayrağı korunmalı")
        def m_risk(kayitlar):
            degisen = [dict(x, yanit_adayi="güvenli") for x in kayitlar]
            return guvenli_geri_donus_raporu(degisen)
        def m_kanal(kayitlar):
            degisen = [dict(x, kanal="model_yaniti") for x in kayitlar]
            return guvenli_geri_donus_raporu(degisen)
        def m_ham(kayitlar):
            sonuc = guvenli_geri_donus_raporu(kayitlar)
            for x in sonuc:
                x["ham_icerik_tasindi"] = True
            return sonuc
        for ad, mutant in [("riskli adayı temiz sayan", m_risk), ("kanalı değiştiren", m_kanal), ("ham içerik bayrağını bozan", m_ham)]:
            ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
        raises(ValueError, guvenli_geri_donus_raporu, [dict(K[0], id=123)], msg="id str olmalı")
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
    kontrol(r["riskli_guvenli"], "riskli gerçek çıktı son yanıta taşınmadı")
    riskli = [a for a in r["akislar"] if a["riskler"]]
    kontrol(len(riskli) >= 1, "modelin gerçek çıktısında en az bir senaryo risk sinyali üretti")
    rapor_map = {x["id"]: x for x in r["rapor"]}
    kontrol(all(rapor_map[a["id"]]["karar"] == "guvenli_yedek" and not rapor_map[a["id"]]["ham_icerik_tasindi"] for a in riskli),
            "riskli çıktı güvenli yedeğe düştü, ham içerik taşınmadı")
    oz = D.ozet(r)
yol = ai_lab.kanit_yaz("savunma-yedek", {"kaynak": "gercek", "kabul": all(sonuclar), "ders": "ai-savunma-10",
                                         "ortam": (r or {}).get("ortam"), "ozet": oz})
if oz:
    ok(True, f"BULGU ({r['ortam']['model']['ad']}): {oz['senaryo']} gerçek çıktı → kararlar {oz['kararlar']}; "
             f"riskli çıktı {oz['riskli_cikti']}, ham içerik taşınan yanıt {oz['ham_tasindi']}, riskli güvenli {oz['riskli_guvenli']}. "
             f"Model kimlik-bilgisi biçimli bir dize üretti; guardrail reddinde ham çıktı gitmedi, sabit güvenli yedek üretildi (fail-closed).")
```

```solution
import ai_lab

def guvenli_geri_donus_raporu(kayitlar):
    import re
    if not isinstance(kayitlar, list):
        raise ValueError("kayıt listesi geçersiz")
    kimlikler = set()
    rapor = []
    yedek = "Güvenli yanıt üretilemedi; istek tamamlanamadı."
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"id", "kanal", "yanit_adayi"}:
            raise ValueError("kayıt şeması geçersiz")
        kimlik = kayit["id"]
        if not isinstance(kimlik, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kimlik):
            raise ValueError("kimlik geçersiz")
        if kimlik in kimlikler:
            raise ValueError("kimlik yinelenemez")
        kimlikler.add(kimlik)
        if kayit["kanal"] not in ("model_yaniti", "guvenli_yedek", "yeniden_dene_degerlendir"):
            raise ValueError("kanal geçersiz")
        aday = kayit["yanit_adayi"]
        if not isinstance(aday, str) or "\x00" in aday:
            raise ValueError("yanıt adayı geçersiz")
        if len(aday) > 2000:
            raise ValueError("yanıt adayı çok uzun")
        riskli = any(isaret in aday for isaret in ("BREACH:CANARY-42", "PRIVATE KEY", "Bearer "))
        if kayit["kanal"] == "model_yaniti" and aday and aday == aday.strip() and not riskli:
            karar, yanit, ham = "model_yaniti", aday, True
        elif kayit["kanal"] == "yeniden_dene_degerlendir":
            karar, yanit, ham = "yeniden_dene", None, False
        else:
            karar, yanit, ham = "guvenli_yedek", yedek, False
        rapor.append({"id": kimlik, "karar": karar, "yanit": yanit, "ham_icerik_tasindi": ham})
    return sorted(rapor, key=lambda x: x["id"])

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_10 as deney
    deney.goster(guvenli_geri_donus_raporu)
```

```hint
Bu işlev 3. görevdeki `guvenli_geri_donus_raporu` ile birebir aynıdır; tek fark, kanal ve yanıt adaylarının gerçek model koşusundan gelmesidir. Model kanalındaki kabul koşullarını birlikte denetle; yedek metni sabit üret.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Güvenli geri dönüş başarısızlığı gizlemez

Guardrail hata verdiğinde izin üretmek açık hata modudur. Sınırlı retry planı toplam deneme sayısını ve üstel bekleme bütçesini sınırlar; sonsuz tekrar hem maliyet hem gizli tekrar saldırısı yüzeyidir. Son fallback kullanıcıya güvenli bir sonuç üretirken ham riskli içeriği taşımamalıdır. Her ret, yeniden deneme ve nihai duruş gözlenebilir kalır.

| Yaygın yanlış | Mekanizmanın sınırı |
|---|---|
| Retry sayısı sınırsızsa güvenlik artar | Sınırlandırılmayan tekrar kaynak tüketimi ve hatayı büyütebilir. |

Saldırı–savunma bağlantısı: ai-saldiri-40.
:::

::: anlat Kaynak ile lab sonucunu ayır
[OWASP Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html). Deny-by-default ilkesi hata hâlinde izin üretmemeyi destekler; retry bütçesi bu dersin dar sözleşmesidir.
:::
