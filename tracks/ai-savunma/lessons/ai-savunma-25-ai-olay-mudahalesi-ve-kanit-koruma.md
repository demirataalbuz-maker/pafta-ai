---
id: ai-savunma-25
title: AI Olay Müdahalesi ve Kanıt Koruma
summary: Olayları önceliklendir; kanıt manifestolarını ve devir zincirini doğrulayarak güvenli toparlanma için tekrarlanabilir kayıtlar üret.
timeout: 45
esleme: ai-saldiri-33, ai-saldiri-37
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et: Müdahale sırası kanıt bütünlüğünü korumalıdır

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Gerçek bir olayda kanıtlar log sisteminden (Elastic, SigNoz), model kayıt defterinden (MLflow) ve uygulama sunucusundan toplanır. Her dosya özetlenir, bir manifestoya yazılır ve her devirde kimin kime ne zaman verdiği kaydedilir (chain of custody). | Görev 1–3: `veri/kanit_manifestolari.json`, `veri/olaylar.json` ve `veri/devir_zinciri.json` içindeki **sentetik** manifesto, olay ve devir kayıtları. Son adım: kurulu yerel Ollama modelinin gerçek yanıtı bir kanıt dosyasına yazılır, dosyanın gerçek SHA-256 değeri hesaplanır ve geçici bir kopyası tahrif edilerek yeniden özetlenir. | Dersin adım listeleri örnek bir müdahale politikasıdır, kurumun olay planının yerine geçmez. Özet, dosyanın değişmediğini gösterir; içeriğin doğru, eksiksiz ya da hukuken kabul edilebilir olduğunu göstermez. Gerçek bir adli süreçte imza, zaman damgası servisi ve yazılamaz depolama da gerekir. |

> [!NOT]
> Görev 1–3 sentetik veriyle çalışır. Bu görevlerde model, Elastic, SigNoz veya MLflow çağrılmaz. Son adımdaki **Gerçek deney** görevi kurulu yerel Ollama modelini gerçekten çalıştırır ve gerçek bir kanıt dosyası yazar; yeni model indirmez. `veri/` dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalanır; kopyada yaptığın değişiklik bir sonraki çalıştırmada sıfırlanır, **kalıcılık yoktur**. Kontrol bu dosyalardan ayrı, gizli verilerle sınar.

AI olayında kapsam, etkilenen sistem, olay seviyesi ve korunacak kanıtlar açıkça kaydedilir. Erişimi sınırlama veya önceki model sürümüne dönme gibi adımlar, kanıtların kaynağını ve bütünlüğünü kaybettirmemelidir. Manifestodaki özet değeri, bayt sayısı ve zaman bilgisi sonradan yapılan karşılaştırmaların dayanağıdır.

Görev 1–3 sentetik olay ve kanıt kayıtlarıyla çalışır; son adım bir manifestoyu gerçek bir kanıt dosyasının yeniden hesaplanan özetiyle karşılaştırır. Dersin listeleri örnek bir müdahale politikasıdır, her kurumun olay planının yerine geçmez.

**AI olayının farkı:** Bir LLM uygulamasında olay çoğu zaman tek bir sunucu kaydında görünmez. Sızan bir sır sohbet kaydında, onu tetikleyen talimat bir RAG belgesinde, yetkisiz araç çağrısı ajan logunda, davranış değişikliği ise yeni bir model sürümünde durur. Müdahale ekibi hızlı davranmak ister: modeli eski sürüme döndürür, belgeyi siler, oturumları kapatır. Bu adımlar kanıtı da yok edebilir. Örneğin geri dönülen model sürümü yeni sürümün ağırlıklarını diskten siler, temizlenen vektör veritabanı zehirli belgenin nereden geldiğini unutur. Bu yüzden sıra şudur: önce kaydet, sonra koru, sonra sınırla. Sınırlama kanıtı kopyaladıktan sonra yapılır.

**Saldırgan bakışı:** İçeriden ya da sızmış bir saldırgan izini siler veya değiştirir. Log satırlarını düzenler, kanıtın bir kopyasını başka bir kopyayla değiştirir, zaman damgalarını geriye alır. Manifesto ve devir zinciri bu tür değişiklikleri görünür kılar. Ancak yalnız manifesto şemasının doğrulanması yetmez; özet her devirde dosyadan **yeniden** hesaplanmalıdır.

**Savunucu tarafı ve sık tuzaklar:**

- **Boş dosya:** 0 baytlık dosya da kanıttır ve geçerli bir özeti vardır (`bos-yedek`). Onu "boş" diye atlamak, bir silme işleminin izini kaybettirir.
- **Biçim:** Özet büyük harfle ya da kısaltılmış yazılırsa karşılaştırma ya hata verir ya da sessizce yanlış sonuç üretir. Biçim kayıt anında sıkı tutulur.
- **Zaman:** Devir zamanı geriye gidemez. Aynı saniyede iki devir olabilir; eşit zaman geçerlidir.
- **Sahiplik:** Her devirde gönderen, bir önceki adımın alıcısıdır. Kopuk bir zincir, kanıtın arada kimde olduğunun bilinmediği anlamına gelir.
:::

::: anlat Devir zinciri sıra, zaman ve sahiplik ilişkisini korur
Kanıt her devrinde sıra numarası, zaman, gönderen, alan ve SHA-256 özetiyle kaydedilir. Sıralar her kanıt için sıfırdan başlar ve birer artar. Zaman geriye gidemez; bir adımın alıcısı sonraki adımın göndereni olur. Özet değeri zincir boyunca değişmez.

Sıralama yalnız görünüm için yapılmaz: müdahale planında yüksek seviye önce gelir, kanıt raporunda ise kanıt kimlikleri alfabetik sıralanır. Böylece aynı kayıtlar farklı sırada verilse bile aynı sonuç üretilir.
:::

::: tahmin Sıra ve zaman koşullarını tahmin et
Üç çıktı satırını yaz:

```python
siralar = [0, 1, 2]
zamanlar = [10, 10, 12]
print(siralar == list(range(len(siralar))))
print(all(a <= b for a, b in zip(zamanlar, zamanlar[1:])))
print(all(x == "ab" * 32 for x in ["ab" * 32, "ab" * 32]))
```

???

```cikti
True
True
True
```

Bu koşullar tek başına kanıtın gerçekliğini kanıtlamaz; yalnız fixture zincirinin iç tutarlılığını denetler.
:::

::: gorev 1 · Kanıt manifestosunu doğrula
`kanit_manifestu_dogrula(kayit)` işlevini yaz. Kayıt tam olarak `olay_id`, `kanit_id`, `sha256`, `bayt`, `zaman` alanlarını taşısın. İki kimlik de 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren stringdir.

`sha256`, 64 küçük harfli onaltılık karakterden oluşan stringdir. `bayt` ve `zaman`, bool olmayan, sıfır veya pozitif tamsayılardır. Geçersiz veride `ValueError` yükselt. Alanları aynı değerlerle yeni bir sözlükte döndür; girdiyi değiştirme.

Görünür veri: `veri/kanit_manifestolari.json`. Üç geçerli manifesto (0 baytlık boş yedek dahil) kabul edilmeli, beş bozuk manifesto reddedilmelidir.

```starter
from ai_savunma_veri import json_yukle

def kanit_manifestu_dogrula(kayit):
    # KUSURLU BAŞLANGIÇ KODU: özeti yalnız uzunluğa göre denetliyor (büyük harfi kabul ediyor), bayt=0'ı "boş kanıt" diye reddediyor, bool zamanı ve boşluklu kimliği kabul ediyor!
    if len(kayit["sha256"]) != 64:
        raise ValueError("özet 64 karakter olmalı")
    if not kayit["bayt"]:
        raise ValueError("boş kanıt kabul edilmez")
    if kayit["bayt"] < 0:
        raise ValueError("bayt negatif olamaz")
    return kayit

veri = json_yukle("veri/kanit_manifestolari.json")
for m in veri["manifestolar"] + veri["bozuk_manifestolar"]:
    try:
        kanit_manifestu_dogrula(m)
        print(m["kanit_id"], "kabul")
    except ValueError as hata:
        print(m["kanit_id"], "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-25")
```

```test
import copy
M = {"olay_id": "o-1", "kanit_id": "k-1", "sha256": "ab" * 32, "bayt": 0, "zaman": 0}
def sozlesme(fn):
    try:
        once = copy.deepcopy(M)
        sonuc = fn(M)
        if sonuc != M or M != once or sonuc is M:
            return False
        if fn(dict(M, olay_id="a" * 64, kanit_id="k" * 64, sha256="0" * 64))["bayt"] != 0:
            return False
        if fn(dict(M, bayt=1024, zaman=99))["zaman"] != 99:
            return False
        for kayit in [
            None, [], dict(M, ek=1), dict(M, olay_id=""), dict(M, olay_id="a b"), dict(M, olay_id="a" * 65),
            dict(M, kanit_id=""), dict(M, kanit_id="a b"), dict(M, kanit_id="a" * 65),
            dict(M, sha256="AB" * 32), dict(M, sha256="a" * 63), dict(M, sha256="g" * 64), dict(M, sha256=1),
            dict(M, bayt=-1), dict(M, bayt=True), dict(M, bayt=1.0),
            dict(M, zaman=-1), dict(M, zaman=False), dict(M, zaman=1.0),
        ]:
            try:
                fn(kayit)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(kanit_manifestu_dogrula), "kimlik, özet, bayt ve zaman kuralları korunmalı")
def m_sha(kayit):
    sonuc = kanit_manifestu_dogrula(kayit)
    sonuc["sha256"] = "0" * 64
    return sonuc
def m_bayt(kayit):
    sonuc = kanit_manifestu_dogrula(kayit)
    sonuc["bayt"] = 1
    return sonuc
def m_zaman(kayit):
    sonuc = kanit_manifestu_dogrula(kayit)
    sonuc["zaman"] = 1
    return sonuc
for ad, mutant in [("özeti değiştiren", m_sha), ("baytı değiştiren", m_bayt), ("zamanı değiştiren", m_zaman)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
# --- carbon-c8-ek-bas ---
raises(ValueError, kanit_manifestu_dogrula, dict(M, olay_id=123), msg="olay_id str olmalı")
raises(ValueError, kanit_manifestu_dogrula, dict(M, kanit_id=123), msg="kanit_id str olmalı")
raises(ValueError, kanit_manifestu_dogrula, dict(M, sha256=123), msg="sha256 str olmalı")
raises(ValueError, kanit_manifestu_dogrula, dict(M, bayt=True), msg="bayt bool ret")
raises(ValueError, kanit_manifestu_dogrula, dict(M, zaman=True), msg="zaman bool ret")
# --- carbon-c8-ek-son ---
```

```solution
def kanit_manifestu_dogrula(kayit):
    import re
    if not isinstance(kayit, dict):
        raise ValueError("kayıt sözlük olmalı")
    if set(kayit) != {"olay_id", "kanit_id", "sha256", "bayt", "zaman"}:
        raise ValueError("manifesto şeması geçersiz")
    for alan in ("olay_id", "kanit_id"):
        deger = kayit[alan]
        if not isinstance(deger, str):
            raise ValueError("kimlik string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", deger):
            raise ValueError("kimlik geçersiz")
    if not isinstance(kayit["sha256"], str):
        raise ValueError("özet string olmalı")
    if not re.fullmatch(r"[0-9a-f]{64}", kayit["sha256"]):
        raise ValueError("özet geçersiz")
    for alan in ("bayt", "zaman"):
        deger = kayit[alan]
        if isinstance(deger, bool) or not isinstance(deger, int):
            raise ValueError("sayısal alan tamsayı olmalı")
        if deger < 0:
            raise ValueError("sayısal alan negatif olamaz")
    return {"olay_id": kayit["olay_id"], "kanit_id": kayit["kanit_id"], "sha256": kayit["sha256"], "bayt": kayit["bayt"], "zaman": kayit["zaman"]}
```

```hint
Kimlik ve özeti ayrı desenlerle doğrula. Tamsayı alanlarında `bool` değerlerini açıkça reddet; sıfır geçerlidir.
```
:::

::: gorev 2 · Olaylardan öncelikli müdahale planı üret
`mudahale_plani_uret(olaylar)` işlevini yaz. Girdi liste olmalı; her olay tam olarak `id`, `seviye`, `kategori`, `sistem`, `kanit_ids` alanlarını taşısın. Olay kimliği ilk görevdeki desene uyan benzersiz stringdir. Seviye `dusuk`, `orta`, `yuksek`, `kritik`; kategori `sizinti`, `prompt_injection`, `yetkisiz_erisim`, `model_sapmasi` olmalıdır.

Sistem başı/sonu boşluğu olmayan boş olmayan stringdir ve kontrol karakteri içeremez. Kanıt kimlikleri yinelenmeyen listedir; her öğe ilk görevdeki kimlik desenine uyar. Liste boş olabilir. Geçersiz veride `ValueError` yükselt.

Her olay için `{"olay_id":ID,"oncelik":SAYI,"adimlar":[...]}` döndür. Öncelik `kritik=0`, `yuksek=1`, `orta=2`, `dusuk=3` olsun. Adımlar sırasıyla `olayi_kaydet`, `kanitlari_koru`; yüksek veya kritikse `erisimi_sinirla`; kategoriye göre sırasıyla `veri_sizintisini_durdur`, `istekleri_filtrele`, `oturumlari_iptal_et`, `onceki_surume_don`; son olarak `guvenli_toparlanmayi_dogrula` içersin. Sonuçları öncelik, sonra olay kimliğiyle sırala. Boş girdide boş liste döndür ve girdileri değiştirme.

Görünür veri: `veri/olaylar.json`. Doğru planda olaylar `INC-041`, `INC-042`, `INC-043`, `INC-044` sırasıyla gelir. Yalnız ilk ikisi `erisimi_sinirla` adımını alır.

```starter
from ai_savunma_veri import json_yukle

def mudahale_plani_uret(olaylar):
    # KUSURLU BAŞLANGIÇ KODU: erişimi kanıtı korumadan ÖNCE sınırlıyor, her olaya erisimi_sinirla ekliyor ve seviyeyi alfabetik sıralıyor!
    oncelik = {"kritik": 0, "yuksek": 1, "orta": 2, "dusuk": 3}
    kategori = {"sizinti": "veri_sizintisini_durdur", "prompt_injection": "istekleri_filtrele",
                "yetkisiz_erisim": "oturumlari_iptal_et", "model_sapmasi": "onceki_surume_don"}
    plan = [{"olay_id": o["id"], "oncelik": oncelik[o["seviye"]],
             "adimlar": ["olayi_kaydet", "erisimi_sinirla", "kanitlari_koru", kategori[o["kategori"]], "guvenli_toparlanmayi_dogrula"],
             "_seviye": o["seviye"]} for o in olaylar]
    plan.sort(key=lambda x: (x["_seviye"], x["olay_id"]))
    return [{k: v for k, v in p.items() if k != "_seviye"} for p in plan]

veri = json_yukle("veri/olaylar.json")
for p in mudahale_plani_uret(veri["olaylar"]):
    print(p["olay_id"], p["oncelik"], p["adimlar"])
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-25")
```

```test
import copy
O = [
    {"id": "o-dusuk", "seviye": "dusuk", "kategori": "model_sapmasi", "sistem": "AI API", "kanit_ids": []},
    {"id": "o-kritik", "seviye": "kritik", "kategori": "sizinti", "sistem": "sohbet", "kanit_ids": ["k-1", "k-2"]},
    {"id": "o-yuksek", "seviye": "yuksek", "kategori": "prompt_injection", "sistem": "yardim", "kanit_ids": ["k-3"]},
]
BEKLENEN = [
    {"olay_id": "o-kritik", "oncelik": 0, "adimlar": ["olayi_kaydet", "kanitlari_koru", "erisimi_sinirla", "veri_sizintisini_durdur", "guvenli_toparlanmayi_dogrula"]},
    {"olay_id": "o-yuksek", "oncelik": 1, "adimlar": ["olayi_kaydet", "kanitlari_koru", "erisimi_sinirla", "istekleri_filtrele", "guvenli_toparlanmayi_dogrula"]},
    {"olay_id": "o-dusuk", "oncelik": 3, "adimlar": ["olayi_kaydet", "kanitlari_koru", "onceki_surume_don", "guvenli_toparlanmayi_dogrula"]},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(O)
        if fn(O) != BEKLENEN or O != once or fn(list(reversed(O))) != BEKLENEN or fn([]) != []:
            return False
        if fn([dict(O[0], id="a" * 64, seviye="orta")])[0]["oncelik"] != 2:
            return False
        yetki = fn([dict(O[0], id="o-yetki", kategori="yetkisiz_erisim")])
        if yetki[0]["adimlar"][-2] != "oturumlari_iptal_et":
            return False
        if fn([dict(O[0], kanit_ids=["a" * 64])])[0]["olay_id"] != "o-dusuk":
            return False
        for olaylar in [
            None, {}, [None], [dict(O[0], ek=1)], [dict(O[0], id="a b")], [dict(O[0], id="a" * 65)],
            [O[0], O[0]], [dict(O[0], seviye="bilinmeyen")], [dict(O[0], kategori="diger")],
            [dict(O[0], sistem="")], [dict(O[0], sistem=" x")], [dict(O[0], sistem="a\0b")],
            [dict(O[0], kanit_ids=None)], [dict(O[0], kanit_ids="k-1")], [dict(O[0], kanit_ids=["a b"])],
            [dict(O[0], kanit_ids=["a" * 65])], [dict(O[0], kanit_ids=["k-1", "k-1"])],
        ]:
            try:
                fn(olaylar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(mudahale_plani_uret), "öncelik, kategori adımı ve kanıt kimlikleri korunmalı")
def m_seviye(olaylar):
    return mudahale_plani_uret([dict(x, seviye="dusuk") for x in olaylar])
def m_kategori(olaylar):
    return mudahale_plani_uret([dict(x, kategori="model_sapmasi") for x in olaylar])
def m_sistem(olaylar):
    return mudahale_plani_uret([dict(x, sistem=" " + x["sistem"]) for x in olaylar])
for ad, mutant in [("seviyeyi düşüren", m_seviye), ("kategoriyi değiştiren", m_kategori), ("sistemi bozan", m_sistem)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
# --- carbon-c8-ek-bas ---
raises(ValueError, mudahale_plani_uret, [dict(O[0], olay_id=123)], msg="olay_id str olmalı")
if "kanit_id" in O[0]:
    raises(ValueError, mudahale_plani_uret, [dict(O[0], kanit_id=123)], msg="kanit_id str olmalı")
if "kaynak" in O[0]:
    raises(ValueError, mudahale_plani_uret, [dict(O[0], kaynak="a\x1fb")], msg="kontrol karakteri ret")
raises(ValueError, mudahale_plani_uret, [dict(O[0], id=123)], msg="olay id str olmalı")
raises(ValueError, mudahale_plani_uret, [dict(O[0], sistem=123)], msg="sistem str olmalı")
raises(ValueError, mudahale_plani_uret, [dict(O[0], sistem="a\x1fb")], msg="sistem 0x1f kontrol karakteri ret")
raises(ValueError, mudahale_plani_uret, [dict(O[0], kanit_ids=[123])], msg="kanıt id str olmalı")
# --- carbon-c8-ek-son ---
```

```solution
def mudahale_plani_uret(olaylar):
    import re
    if not isinstance(olaylar, list):
        raise ValueError("olaylar liste olmalı")
    oncelikler = {"kritik": 0, "yuksek": 1, "orta": 2, "dusuk": 3}
    kategori_adimlari = {
        "sizinti": "veri_sizintisini_durdur",
        "prompt_injection": "istekleri_filtrele",
        "yetkisiz_erisim": "oturumlari_iptal_et",
        "model_sapmasi": "onceki_surume_don",
    }
    gorulen = set()
    for olay in olaylar:
        if not isinstance(olay, dict):
            raise ValueError("olay sözlük olmalı")
        if set(olay) != {"id", "seviye", "kategori", "sistem", "kanit_ids"}:
            raise ValueError("olay şeması geçersiz")
        if not isinstance(olay["id"], str):
            raise ValueError("olay kimliği string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", olay["id"]):
            raise ValueError("olay kimliği geçersiz")
        if olay["id"] in gorulen:
            raise ValueError("olay kimliği yinelenemez")
        gorulen.add(olay["id"])
        if olay["seviye"] not in oncelikler:
            raise ValueError("seviye geçersiz")
        if olay["kategori"] not in kategori_adimlari:
            raise ValueError("kategori geçersiz")
        sistem = olay["sistem"]
        if not isinstance(sistem, str):
            raise ValueError("sistem string olmalı")
        if not sistem or sistem != sistem.strip():
            raise ValueError("sistem boşluk biçimi geçersiz")
        if any(ord(k) < 32 for k in sistem):
            raise ValueError("sistem kontrol karakteri içeremez")
        kanit_ids = olay["kanit_ids"]
        if not isinstance(kanit_ids, list):
            raise ValueError("kanıt kimlikleri liste olmalı")
        if len(set(kanit_ids)) != len(kanit_ids):
            raise ValueError("kanıt kimlikleri yinelenemez")
        for kanit_id in kanit_ids:
            if not isinstance(kanit_id, str):
                raise ValueError("kanıt kimliği string olmalı")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kanit_id):
                raise ValueError("kanıt kimliği geçersiz")
    sonuc = []
    for olay in olaylar:
        adimlar = ["olayi_kaydet", "kanitlari_koru"]
        if olay["seviye"] in ("kritik", "yuksek"):
            adimlar.append("erisimi_sinirla")
        adimlar.append(kategori_adimlari[olay["kategori"]])
        adimlar.append("guvenli_toparlanmayi_dogrula")
        sonuc.append({"olay_id": olay["id"], "oncelik": oncelikler[olay["seviye"]], "adimlar": adimlar})
    return sorted(sonuc, key=lambda x: (x["oncelik"], x["olay_id"]))
```

```hint
Öncelik ve kategori adımlarını sözlüklerde tut. Erişim sınırlama adımını yalnız yüksek ve kritik olaylarda ekle.
```
:::

::: gorev 3 · Kanıt devir zincirini doğrula ve özetle
`kanit_zinciri_dogrula(kayitlar)` işlevini yaz. Girdi liste olmalı; her kayıt tam olarak `kanit_id`, `sira`, `zaman`, `gonderen`, `alan`, `sha256` alanlarını taşısın. Kimlik ve özet ilk görevdeki kuralları sağlasın. Sıra ve zaman bool olmayan, sıfır veya pozitif tamsayılardır. Gönderen ve alan başı/sonu boşluğu olmayan boş olmayan stringdir ve kontrol karakteri içeremez.

Her kanıtın sıraları sıfırdan başlamalı ve birer artmalı, zamanları geriye gitmemeli, SHA-256 özeti değişmemelidir. Sıfırdan büyük adımın göndereni, önceki adımın alanıyla aynı olmalıdır. Aynı kanıt ve sıra numarası yinelenemez. Geçersiz veride `ValueError` yükselt.

Her kanıt için `{"kanit_id":ID,"adim_sayisi":N,"son_zaman":ZAMAN,"son_sahip":ALAN,"sha256":OZET}` döndür. Kanıt kimliğine göre sırala; girdi sırasından bağımsız çalış. Boş girdide boş liste döndür ve girdileri değiştirme.

Görünür veri: `veri/devir_zinciri.json`. Kayıtlar karışık sıradadır. Doğru özette `gateway-log` 3 adımlıdır ve son sahibi `adli-depo` olur. `bozuk_zincirler` içindeki beş zincirin hepsi reddedilmelidir.

```starter
from ai_savunma_veri import json_yukle

def kanit_zinciri_dogrula(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: kayıtları sıralamadan girdi sırasıyla işliyor ve yalnız adım sayar; sıra boşluğunu, geri giden zamanı, kopuk sahipliği ve değişen özeti denetlemiyor!
    ozet = {}
    for k in kayitlar:
        o = ozet.setdefault(k["kanit_id"], {"kanit_id": k["kanit_id"], "adim_sayisi": 0, "son_zaman": 0, "son_sahip": None, "sha256": k["sha256"]})
        o["adim_sayisi"] += 1
        o["son_zaman"] = k["zaman"]
        o["son_sahip"] = k["alan"]
    return [ozet[x] for x in sorted(ozet)]

veri = json_yukle("veri/devir_zinciri.json")
for o in kanit_zinciri_dogrula(veri["kayitlar"]):
    print(o["kanit_id"], o["adim_sayisi"], "adım · son:", o["son_sahip"], o["son_zaman"])
for ad, zincir in veri["bozuk_zincirler"].items():
    try:
        kanit_zinciri_dogrula(zincir)
        print(ad, "KABUL edildi (yanlış)")
    except ValueError as hata:
        print(ad, "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-25")
```

```test
import copy
Z = [
    {"kanit_id": "k-b", "sira": 0, "zaman": 0, "gonderen": "olay muhafizi", "alan": "adli laboratuvar", "sha256": "ab" * 32},
    {"kanit_id": "k-b", "sira": 1, "zaman": 5, "gonderen": "adli laboratuvar", "alan": "kanit arsivi", "sha256": "ab" * 32},
    {"kanit_id": "k-a", "sira": 0, "zaman": 0, "gonderen": "saha eki", "alan": "adli laboratuvar", "sha256": "0" * 64},
]
BEKLENEN = [
    {"kanit_id": "k-a", "adim_sayisi": 1, "son_zaman": 0, "son_sahip": "adli laboratuvar", "sha256": "0" * 64},
    {"kanit_id": "k-b", "adim_sayisi": 2, "son_zaman": 5, "son_sahip": "kanit arsivi", "sha256": "ab" * 32},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(Z)
        if fn(Z) != BEKLENEN or Z != once or fn(list(reversed(Z))) != BEKLENEN or fn([]) != []:
            return False
        if fn([dict(Z[0], kanit_id="a" * 64)])[0]["adim_sayisi"] != 1:
            return False
        esit_zaman = [Z[0], dict(Z[1], zaman=0)]
        if fn(esit_zaman)[0]["son_zaman"] != 0:
            return False
        for kayitlar in [
            None, {}, [None], [dict(Z[0], ek=1)], [dict(Z[0], kanit_id="a b")], [dict(Z[0], kanit_id="a" * 65)],
            [dict(Z[0], sira=-1)], [dict(Z[0], sira=True)], [dict(Z[0], sira=1.0)],
            [dict(Z[0], zaman=-1)], [dict(Z[0], zaman=False)], [dict(Z[0], zaman=1.0)],
            [dict(Z[0], gonderen="")], [dict(Z[0], gonderen=" x")], [dict(Z[0], gonderen="a\0b")],
            [dict(Z[0], alan="")], [dict(Z[0], alan="x ")], [dict(Z[0], sha256="AB" * 32)],
            [Z[0], Z[0]], [dict(Z[0], sira=1)], [Z[0], dict(Z[1], sira=2)],
            [Z[0], dict(Z[1], zaman=-1)], [Z[0], dict(Z[1], sha256="0" * 64)],
            [Z[0], dict(Z[1], gonderen="baska ekip")],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(kanit_zinciri_dogrula), "sıra, zaman, devir ve özet bütünlüğü korunmalı")
def m_zaman(kayitlar):
    return kanit_zinciri_dogrula([dict(x, zaman=99) for x in kayitlar])
def m_sira(kayitlar):
    return kanit_zinciri_dogrula([dict(x, sira=0) for x in kayitlar])
def m_alan(kayitlar):
    return kanit_zinciri_dogrula([dict(x, alan="baska ekip") for x in kayitlar])
for ad, mutant in [("zamanı değiştiren", m_zaman), ("sırayı bozan", m_sira), ("devri bozan", m_alan)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
# --- carbon-c8-ek-bas ---
raises(ValueError, kanit_zinciri_dogrula, [dict(Z[0], kanit_id=123)], msg="kanit_id str olmalı")
raises(ValueError, kanit_zinciri_dogrula, [dict(Z[0], gonderen=123)] if "gonderen" in Z[0] else [dict(Z[0], teslim_eden=123)], msg="teslim eden str olmalı")
raises(ValueError, kanit_zinciri_dogrula, [dict(Z[0], sira=True)], msg="sıra bool ret")
raises(ValueError, kanit_zinciri_dogrula, [dict(Z[0], zaman=True)], msg="zaman bool ret")
_z25_geri = [dict(Z[0], sira=0, zaman=20), dict(Z[1], kanit_id=Z[0]["kanit_id"], sira=1, zaman=10, sha256=Z[0]["sha256"])]
if "teslim_eden" in Z[0]:
    _z25_geri[1]["teslim_eden"] = Z[0]["teslim_alan"]
elif "gonderen" in Z[0]:
    _z25_geri[1]["gonderen"] = Z[0]["alan"]
raises(ValueError, kanit_zinciri_dogrula, _z25_geri, msg="zaman geriye gidemez")
raises(ValueError, kanit_zinciri_dogrula, [dict(Z[0], gonderen="a\x1fb")], msg="gönderen 0x1f kontrol karakteri ret")
raises(ValueError, kanit_zinciri_dogrula, [dict(Z[0], sha256=123)], msg="sha256 str olmalı")
# --- carbon-c8-ek-son ---
```

```solution
def kanit_zinciri_dogrula(kayitlar):
    import re
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    gorulen = set()
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"kanit_id", "sira", "zaman", "gonderen", "alan", "sha256"}:
            raise ValueError("zincir şeması geçersiz")
        if not isinstance(kayit["kanit_id"], str):
            raise ValueError("kanıt kimliği string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["kanit_id"]):
            raise ValueError("kanıt kimliği geçersiz")
        for alan in ("sira", "zaman"):
            deger = kayit[alan]
            if isinstance(deger, bool) or not isinstance(deger, int):
                raise ValueError("sıra ve zaman tamsayı olmalı")
            if deger < 0:
                raise ValueError("sıra ve zaman negatif olamaz")
        for alan in ("gonderen", "alan"):
            deger = kayit[alan]
            if not isinstance(deger, str):
                raise ValueError("sahip string olmalı")
            if not deger or deger != deger.strip():
                raise ValueError("sahip boşluk biçimi geçersiz")
            if any(ord(k) < 32 for k in deger):
                raise ValueError("sahip kontrol karakteri içeremez")
        if not isinstance(kayit["sha256"], str):
            raise ValueError("özet string olmalı")
        if not re.fullmatch(r"[0-9a-f]{64}", kayit["sha256"]):
            raise ValueError("özet geçersiz")
        anahtar = (kayit["kanit_id"], kayit["sira"])
        if anahtar in gorulen:
            raise ValueError("kanıt ve sıra yinelenemez")
        gorulen.add(anahtar)
    gruplar = {}
    for kayit in kayitlar:
        gruplar.setdefault(kayit["kanit_id"], []).append(kayit)
    sonuc = []
    for kanit_id in sorted(gruplar):
        zincir = sorted(gruplar[kanit_id], key=lambda x: x["sira"])
        for indeks, kayit in enumerate(zincir):
            if kayit["sira"] != indeks:
                raise ValueError("sıralar kesintisiz olmalı")
            if indeks:
                onceki = zincir[indeks - 1]
                if kayit["zaman"] < onceki["zaman"]:
                    raise ValueError("zaman geriye gidemez")
                if kayit["gonderen"] != onceki["alan"]:
                    raise ValueError("devir sahipleri uyuşmalı")
                if kayit["sha256"] != onceki["sha256"]:
                    raise ValueError("özet zincirde değişemez")
        son = zincir[-1]
        sonuc.append({"kanit_id": kanit_id, "adim_sayisi": len(zincir), "son_zaman": son["zaman"], "son_sahip": son["alan"], "sha256": son["sha256"]})
    return sonuc
```

```hint
Kayıtları kanıt kimliğiyle grupla ve her grubu sıra numarasına göre sırala. Beklenen sıra, grup içindeki indekse eşit olmalıdır.
```
:::

::: anlat Kanıt bütünlüğü gerçek bir artefakt üzerinde doğrulanır
Görev 1–3'te özetler JSON dosyasında hazır yazılıydı. Bu adımda gerçek bir dosyanın özeti hesaplanır. `sandbox/ai_gercek_ai_savunma_25.py` deneyi şunları yapar:

1. Kurulu yerel Ollama modeli kısa bir belgeyi özetler (sıcaklık 0, tohum 5). Model boş yanıt verirse deney "tamamlanmadı" diye durur.
2. Yanıt `ai_lab.kanit_yaz` ile gerçek bir kanıt JSON dosyasına yazılır. Dosyanın baytlarından gerçek SHA-256 ve bayt sayısı hesaplanır.
3. İki manifesto kurulur ve senin `kanit_manifestu_dogrula` işlevinden geçirilir. Doğru manifesto gerçek özeti taşır. Uydurma manifestonun özeti sıfırlarla doldurulmuştur, ama 64 küçük onaltılık karakter olduğu için **şema olarak geçerlidir**.
4. Dosya yeniden okunup özetlenir ve iki manifestoyla karşılaştırılır.
5. **Tahrif:** Kanıt dosyasının geçici bir kopyasında yalnız `ozet` alanının sonuna ` [duzenlendi]` eklenir. Kopya yeniden özetlenir. Doğru manifesto bu kopyayla karşılaştırıldığında eşleşmez. Asıl kanıt dosyasına dokunulmaz; kopya hemen silinir.

Test önce işlevini gizli deterministik kayıtlarla sınar. Ardından iki manifestonun çıktısını bağımsız referans doğrulamayla birebir karşılaştırır. Şunlar da denetlenir: doğru manifesto şemadan ve yeniden özetten geçmeli; uydurma manifesto şemadan geçmeli ama özet karşılaştırmasında kalmalı; tahrif edilmiş kopya yakalanmalı.

Ders yazılırken bu makinede yapılan koşuda kanıt dosyası yaklaşık 1,9 KB çıktı. 13 baytlık ` [duzenlendi]` eki SHA-256 özetini tamamen değiştirdi. Doğru manifesto asıl dosyayla eşleşti, tahrif edilmiş kopyayla eşleşmedi. Buradaki ders şudur: **şema geçerliliği kanıt bütünlüğünü kanıtlamaz.** Manifesto yalnız bir iddiadır; her devirde dosyanın yeniden hesaplanan özetiyle doğrulanır.

:::

::: gorev Gerçek deney · Gerçek kanıt dosyasının manifestosunu doğrula
`kanit_manifestu_dogrula(kayit)` işlevini yaz. Kuralları ve çıktısı 1. görevdekiyle **aynıdır**. Deney gerçek bir kanıt dosyası yazar ve dosyanın gerçek SHA-256 ve bayt değerleriyle manifesto kurar. Senin işlevin manifestoyu doğrular. Deney ise dosyayı yeniden özetleyerek bütünlüğü teyit eder ve tahrif edilmiş bir kopyayı yakalar. `sandbox.ai_gercek_ai_savunma_25` içindeki `kanit_manifestu_dogrula_referans` yalnız test içindir; onu import etmek veya kaynağını okuyup çalıştırmak Kontrol'de reddedilir.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def kanit_manifestu_dogrula(kayit):
    # KUSURLU BAŞLANGIÇ KODU: özeti "normalleştirmek" için büyük harfe çeviriyor; yeniden hesaplanan küçük harfli özetle hiçbir zaman eşleşmez ve şema doğrulaması yapmıyor!
    return dict(kayit, sha256=kayit["sha256"].upper())

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_25 as deney
    deney.goster(kanit_manifestu_dogrula)
```

```test
import ast
import ai_lab
from sandbox import ai_gercek_ai_savunma_25 as D
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
_yasak = ("kanit_manifestu_dogrula_referans", "kanit_yaz")
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
if not kontrol(not sorun, "Kendi kanit_manifestu_dogrula işlevini yaz; laboratuvar/referans kullanımı yasak: " + "; ".join(sorted(set(sorun)))):
    stop()
fn = need("kanit_manifestu_dogrula")
M = {"olay_id": "o-1", "kanit_id": "k-1", "sha256": "ab" * 32, "bayt": 10, "zaman": 5}
def sozlesme(f):
    try:
        girdi = dict(M)
        if f(girdi) != M or f(girdi) is girdi or girdi != M:
            return False
        sinir = dict(M, olay_id="a" * 64, kanit_id="K_1-x", bayt=0, zaman=0)
        if f(dict(sinir)) != sinir:
            return False
        for bozuk in (None, dict(M, ek=1), dict(M, sha256="AB" * 32), dict(M, sha256="a" * 63), dict(M, bayt=-1), dict(M, bayt=True), dict(M, olay_id="a b"),
                      dict(M, zaman=True), dict(M, zaman=1.5), dict(M, kanit_id="a" * 65), dict(M, kanit_id="-k"), dict(M, sha256="g" * 64)):
            try:
                f(bozuk)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(fn), "kimlik, özet, bayt ve zaman kuralları korunmalı")
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
    kanit_manifestu_dogrula = need('kanit_manifestu_dogrula')
    def _birim_adim_1():
        import copy
        M = {"olay_id": "o-1", "kanit_id": "k-1", "sha256": "ab" * 32, "bayt": 0, "zaman": 0}
        def sozlesme(fn):
            try:
                once = copy.deepcopy(M)
                sonuc = fn(M)
                if sonuc != M or M != once or sonuc is M:
                    return False
                if fn(dict(M, olay_id="a" * 64, kanit_id="k" * 64, sha256="0" * 64))["bayt"] != 0:
                    return False
                if fn(dict(M, bayt=1024, zaman=99))["zaman"] != 99:
                    return False
                for kayit in [
                    None, [], dict(M, ek=1), dict(M, olay_id=""), dict(M, olay_id="a b"), dict(M, olay_id="a" * 65),
                    dict(M, kanit_id=""), dict(M, kanit_id="a b"), dict(M, kanit_id="a" * 65),
                    dict(M, sha256="AB" * 32), dict(M, sha256="a" * 63), dict(M, sha256="g" * 64), dict(M, sha256=1),
                    dict(M, bayt=-1), dict(M, bayt=True), dict(M, bayt=1.0),
                    dict(M, zaman=-1), dict(M, zaman=False), dict(M, zaman=1.0),
                ]:
                    try:
                        fn(kayit)
                        return False
                    except ValueError:
                        pass
                return True
            except Exception:
                return False
        ok(sozlesme(kanit_manifestu_dogrula), "kimlik, özet, bayt ve zaman kuralları korunmalı")
        def m_sha(kayit):
            sonuc = kanit_manifestu_dogrula(kayit)
            sonuc["sha256"] = "0" * 64
            return sonuc
        def m_bayt(kayit):
            sonuc = kanit_manifestu_dogrula(kayit)
            sonuc["bayt"] = 1
            return sonuc
        def m_zaman(kayit):
            sonuc = kanit_manifestu_dogrula(kayit)
            sonuc["zaman"] = 1
            return sonuc
        for ad, mutant in [("özeti değiştiren", m_sha), ("baytı değiştiren", m_bayt), ("zamanı değiştiren", m_zaman)]:
            ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
        raises(ValueError, kanit_manifestu_dogrula, dict(M, olay_id=123), msg="olay_id str olmalı")
        raises(ValueError, kanit_manifestu_dogrula, dict(M, kanit_id=123), msg="kanit_id str olmalı")
        raises(ValueError, kanit_manifestu_dogrula, dict(M, sha256=123), msg="sha256 str olmalı")
        raises(ValueError, kanit_manifestu_dogrula, dict(M, bayt=True), msg="bayt bool ret")
        raises(ValueError, kanit_manifestu_dogrula, dict(M, zaman=True), msg="zaman bool ret")
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
    kontrol(r["dogru_sema_gecerli"] and r["dogru_butunluk"],
            "doğru manifesto hem şemadan hem gerçek dosyanın yeniden-hash'inden geçti")
    kontrol(r["sahte_sema_gecerli"] and not r["sahte_butunluk"],
            "sahte manifesto şema olarak geçerli ama yeniden-hash'te bütünlük bozuk (yakalandı)")
    kontrol(not r["tahrif_butunluk"] and r["tahrif_sha"] != r["gercek_sha"],
            "tahrif edilmiş kopya doğru manifestoyla eşleşmedi (yakalandı)")
    kontrol(r["dogru"] == D.kanit_manifestu_dogrula_referans(dict(r["manifestolar"]["dogru"]))
            and r["sahte"] == D.kanit_manifestu_dogrula_referans(dict(r["manifestolar"]["sahte"])),
            "gerçek manifestolarda çıktı bağımsız doğrulamayla aynı")
    oz = D.ozet(r)
yol = ai_lab.kanit_yaz("savunma-olay", {"kaynak": "gercek", "kabul": all(sonuclar), "ders": "ai-savunma-25",
                                        "ortam": (r or {}).get("ortam"), "ozet": oz,
                                        "model_yaniti": (r or {}).get("model_yaniti"), "manifestolar": (r or {}).get("manifestolar")})
if oz:
    ok(True, f"BULGU ({r['ortam']['model']['ad']}): gerçek kanıt dosyası SHA-256 {oz['gercek_sha_onek']} ({oz['gercek_bayt']} bayt); "
             f"doğru manifesto şema+bütünlük {oz['dogru_sema_gecerli']}/{oz['dogru_butunluk']}, sahte manifesto şema {oz['sahte_sema_gecerli']} ama bütünlük {oz['sahte_butunluk']}, "
             f"tahrif kopyası {oz['tahrif_sha_onek']} ({oz['tahrif_bayt']} bayt) bütünlük {oz['tahrif_butunluk']}. "
             f"Şema geçerliliği kanıt bütünlüğünü kanıtlamaz; yeniden-hash şart.")
```

```solution
import ai_lab

def kanit_manifestu_dogrula(kayit):
    import re
    if not isinstance(kayit, dict):
        raise ValueError("kayıt sözlük olmalı")
    if set(kayit) != {"olay_id", "kanit_id", "sha256", "bayt", "zaman"}:
        raise ValueError("manifesto şeması geçersiz")
    for alan in ("olay_id", "kanit_id"):
        deger = kayit[alan]
        if not isinstance(deger, str):
            raise ValueError("kimlik string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", deger):
            raise ValueError("kimlik geçersiz")
    if not isinstance(kayit["sha256"], str):
        raise ValueError("özet string olmalı")
    if not re.fullmatch(r"[0-9a-f]{64}", kayit["sha256"]):
        raise ValueError("özet geçersiz")
    for alan in ("bayt", "zaman"):
        deger = kayit[alan]
        if isinstance(deger, bool) or not isinstance(deger, int):
            raise ValueError("sayısal alan tamsayı olmalı")
        if deger < 0:
            raise ValueError("sayısal alan negatif olamaz")
    return {"olay_id": kayit["olay_id"], "kanit_id": kayit["kanit_id"], "sha256": kayit["sha256"], "bayt": kayit["bayt"], "zaman": kayit["zaman"]}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_25 as deney
    deney.goster(kanit_manifestu_dogrula)
```

```hint
Bu işlev 1. görevdeki `kanit_manifestu_dogrula` ile birebir aynıdır; tek fark, manifestonun gerçek bir kanıt dosyasından kurulmasıdır. Kimlik ve özeti ayrı desenlerle doğrula; tamsayı alanlarında `bool`'u reddet.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Kanıt teslimi hash ve sıra taşır

Manifest dosya bytesı ile kaydedilmiş özeti bağlar. Olay müdahalesinde hangi işlemin önce yapıldığı ve kanıtın kimden kime geçtiği ayrıca korunur. Hash eşleşmesi kaynağın dürüstlüğünü veya olay yorumunun doğruluğunu kanıtlamaz. Önce ham kanıtı korumadan temizlik yapmak yeniden üretim olanağını ortadan kaldırabilir.

| Yaygın yanlış | Mekanizmanın sınırı |
|---|---|
| SHA256 olayın doğru yorumlandığını kanıtlar | Hash bütünlük verir; yorum ve kaynak güveni ayrı kanıttır. |

Saldırı–savunma bağlantısı: ai-saldiri-37.
:::

::: anlat Kaynak ile lab sonucunu ayır
[Python hashlib](https://docs.python.org/3/library/hashlib.html). Dosya özeti kanıt bytesının değişip değişmediğini sınar; olayın kaynağı ve devir kimliği ayrıca belgelenir.
:::
