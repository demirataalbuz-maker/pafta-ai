---
id: ai-guvence-27
title: Açık Eval Tasarımı ve Kalibrasyonu
summary: Otomatik değerlendirici ile insan kararlarını karşılaştır; örnekleme oranı, uyum ve başarısızlık sınıflarıyla eval kalibrasyonunu raporla.
esleme: ai-guvence-02, ai-guvence-40, ai-uretim-19
timeout: 45
---

::: anlat Eval ölçümü görev ve karar şemasıyla başlar
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Bir eval sistemi görev bazında model kararını, insan incelemesini ve güven skorunu kaydeder | Görevler 1–3 açılabilir sentetik JSON kayıtları; son görev CPU üzerinde gerçekten eğitilen küçük PyTorch sınıflandırıcısının logitleri | Küçük örneklemde uyum veya düşük ECE, bir sohbet modelinin bütün güvenlik görevlerinde güvenilir olduğunu göstermez |

> [!NOT]
> `veri/eval_kayitlari.json` ve `veri/esikler.json` sentetik öğretim dosyalarıdır; gerçek sunucu kaydı değildir. Setup her çalıştırmada geçici çalışma dizinine yeniden kopyalar, bu kopyadaki değişiklikler kalıcı değildir. İlk satırlarda dosyayı okuyup yazdırabilir, aynı çalıştırmada değiştirerek sonucu gözleyebilirsin. Son gerçek deneyin `PAFTA_DATA/calisma/ai-guvence-27/ayar.json` kopyası ise kalıcıdır; varsa üzerine yazılmaz. Gizli kontrol girdileri bu dosyalardan bağımsızdır.

Açık bir eval tasarımında görevler, otomatik değerlendirici kararları, başarısızlık sınıfları ve insan incelemesi kaydedilir. Otomatik `gecerli` veya `hatali` kararı, insan incelemesiyle karşılaştırılmadan doğru kabul edilmez. `belirsiz` otomatik karar ile `incelemede` insan durumu ayrı tutulur.

Görevler 1–3 sentetik dosyalarla çalışır; son adım gerçek PyTorch modeli eğitir ve modelin ham logitleri üzerinde kalibrasyon ölçer. LM Evaluation Harness, Promptfoo veya Ollama bu deneyin yürütücüsü değildir. İnsan tarafından hatalı bulunan örneklerde somut bir başarısızlık sınıfı bulunur; diğer kayıtlarda bu alan `yok` olur.
:::

::: anlat Kalibrasyon örneklem ve uyumla sınırlıdır
Yanlış pozitif, otomatik sistemin geçerli dediği örneğin insan tarafından hatalı bulunmasıdır. Yanlış negatif bunun tersidir. Belirsiz otomatik karar, insan kararıyla uyumlu sayılmaz. Henüz incelenmemiş kayıtlar uyum oranının paydasına girmez, ancak örnekleme oranının toplamında yer alır.

Örnekleme ve uyum eşikleri yalnız kalibrasyon eksiklerini gösterir. Küçük bir insan örneklemindeki yüksek uyum, değerlendiricinin bütün görevlerde güvenilir olduğunu kanıtlamaz. Başarısızlık sınıflarının dağılımı hangi alanların yeniden tasarlanacağını gösterir.
:::

::: anlat Dosyadan ölçüme: kalibrasyonu nasıl okuyacaksın?

Bir eval kaydındaki insan alanı kendiliğinden mutlak gerçek değildir: burada alıştırmanın karşılaştırma etiketi olarak kabul edilir. Gerçek projede değerlendirme rubriği, inceleyiciler arasındaki anlaşmazlık ve örnek seçiminin nasıl yapıldığı ayrıca kaydedilmelidir. Bu dersin ilk üç görevi insan kararını yeniden üretmez; verilmiş kararlarla muhasebeyi doğru yapmayı öğretir. `incelemede` satırını başarısızlık veya uyum saymak aynı hatayı iki farklı biçimde gizler. Satır toplam örnek sayısında kalır, fakat incelenen paydasına girmez. `belirsiz` otomatik karar ise incelenmiş bir örnekte uyum sayılmaz. Bu ayrım özellikle az sayıda örnek incelendiğinde oranları belirgin biçimde değiştirir.

Önce başlangıç kodundaki dosya okuma satırlarını Çalıştır. `veri/eval_kayitlari.json` içindeki altı kaydı ham biçimde yazdır; aynı kimliğin yalnız bir kez bulunmasına, hata sınıfının insan kararıyla ilişkisine bak. İkinci görev aynı dosyayı toplulaştırır; üçüncü görev `veri/esikler.json` içindeki eşiklerle karar üretir. Böylece tek tek kayıt, toplam rapor ve karar arasında izlenebilir bir bağ kurarsın. Bir kaydı bellekte kopyalayıp insan kararını `incelemede` yaparak paydanın nasıl değiştiğini karşılaştır. Öğrenci örneğini değiştirmen testin beklenen cevabını değiştirmez. Kusurlu başlangıçta kodun çalışması doğruluğunu göstermez: eksik şema kontrolü, yanlış payda ve eşikte yanlış alarm ayrı kusurlardır.

Son görev farklı bir ölçüm katmanına geçer. Yerel model dört sayısal özellikten iki sınıf tahmin eder. Adam optimizasyonu eğitim bölümündeki kaybın türevlerini gerçek autograd ile hesaplayarak ağırlıkları günceller. Eğitim, kalibrasyon ve test örnekleri ayrıdır. Logitler olasılık değildir; sıcaklığa bölündükten sonra softmax ile normalize edilir. Pozitif sıcaklık sınıf sıralamasını değiştirmediği için doğruluk aynı kalabilirken güven değerleri ve negatif log olabilirlik değişebilir. Bu yüzden yalnız doğruluğa bakarak kalibrasyonun işe yaramadığı sonucuna varma. Sıcaklık yalnız kalibrasyon bölümündeki çapraz entropiyi küçülterek seçilir. Test etiketlerine bakıp sıcaklığı seçmek rapora veri sızıntısı sokar.

Çıktıda `n` ölçülen test örneği sayısı, `nll` doğru etikete verilen olasılığın log kaybı, `ece` ise güven bölmeleri içindeki güven ile doğruluk farkının ağırlıklı toplamıdır. ECE tek bir örneğin güvenilirlik garantisi değildir; bölme sınırları ve örnek sayısı sonucu etkiler. Burada alt sınır açık, üst sınır kapalıdır; tam 0.5 güven ilk bölmeye girer. Boş bölmenin katkısı sıfırdır. Her bölmeyi eşit ağırlıklandırmak yerine o bölmedeki örneklerin bütün testteki payını kullan. Oranları yalnız raporlarken yuvarla; eşik karşılaştırmasını yuvarlanmış değerle yapmak sınıra yakın örneklerde yanlış karar verebilir.

Saldırgan veya hatalı değerlendirme hattı kolay örnekleri seçerek, belirsiz kararları silerek, başarısızlık sınıflarını değiştirerek ve test kümesini ayar seçimine katarak sonucu olduğundan iyi gösterebilir. Savunma yalnız bir `kalibre` etiketi basmakla kurulmaz: kaynak kayıtları sakla, inceleme kapsamını ayrı raporla ve başarısızlık sınıflarını gözden geçir. İnsan ile otomatik sistem aynı yanlışı paylaşıyorsa yüksek uyum bu ortak yanlışı açığa çıkarmaz. Bu nedenle sentetik karar uyumu ile modelin olasılık kalibrasyonunu birbirinin yerine kullanma. Gerçek deney kanıtında iki seed, bölüm sınırları, eğitim kaybı, ağırlık hash'i ve ham logitler bulunur; ölçümü bu bilgilerle yorumla. Küçük CPU modelinden elde edilen bulgu daha büyük bir model veya başka veri dağılımı için sertifika değildir.
:::

::: tahmin Eval uyumunu ve örnekleme oranını tahmin et
Üç çıktı satırını yaz:

```python
print(round(5 / 6, 6))
print(round(2 / 5, 6))
print("gecerli" == "hatali")
```

???

```cikti
0.833333
0.4
False
```

İlk satır incelenen örnek oranını, ikinci satır iki uyumlu kararın beş incelenen kayda oranını, üçüncü satır otomatik ve insan kararlarının farklı olduğunu gösterir.
:::

::: gorev 1 · Eval kaydını ve hata sınıfını doğrula
`eval_kaydi_dogrula(kayit)` işlevini yaz. Kayıt tam olarak `id`, `gorev`, `otomatik`, `insan`, `basarisizlik` alanlarını taşır. Kimlik 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren; görev 1–64 karakterlik stringdir.

Otomatik karar yalnız `gecerli`, `hatali`, `belirsiz`; insan kararı yalnız `gecerli`, `hatali`, `incelemede` olur. İnsan kararı `hatali` ise başarısızlık yalnız `bilgi`, `politika`, `bicim`, `diger` olabilir. Diğer insan kararlarında başarısızlık `yok` olmalıdır. Geçersiz veride `ValueError` yükselt. Bağımsız sözlük kopyası döndür ve girdiyi değiştirme.

```starter
def eval_kaydi_dogrula(kayit):
    # KUSURLU BAŞLANGIÇ KODU: alanları kopyalıyor fakat şema ve karar ilişkisini doğrulamıyor.
    return dict(kayit)

from ai_guvence_veri import json_yukle
for kayit in json_yukle("veri/eval_kayitlari.json"):
    print(eval_kaydi_dogrula(kayit))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-27")
```

```test
import copy
K = {"id": "ornek-1", "gorev": "g1", "otomatik": "gecerli", "insan": "gecerli", "basarisizlik": "yok"}
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K) != K or fn(K) is K or K != once:
            return False
        sinir = dict(K, id="a" * 64, gorev="g" * 64, otomatik="belirsiz", insan="hatali", basarisizlik="diger")
        if fn(sinir) != sinir or fn(dict(K, insan="incelemede"))["insan"] != "incelemede" or fn(dict(K, gorev="g"))["gorev"] != "g":
            return False
        for kayit in [
            None, [], dict(K, ek=1), dict(K, id=""), dict(K, id="a b"), dict(K, id="a" * 65), dict(K, id=None),
            dict(K, gorev=""), dict(K, gorev="g" * 65), dict(K, gorev=None), dict(K, gorev=1),
            dict(K, otomatik="diger"), dict(K, otomatik=None), dict(K, otomatik=1),
            dict(K, insan="belirsiz"), dict(K, insan=None), dict(K, insan=1),
            dict(K, basarisizlik="bilgi"), dict(K, basarisizlik="diger"), dict(K, basarisizlik=None), dict(K, basarisizlik=1),
            dict(K, insan="hatali", basarisizlik="yok"), dict(K, insan="hatali", basarisizlik="bilinmeyen"),
        ]:
            try:
                fn(kayit)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(eval_kaydi_dogrula), "eval şeması, kararlar ve hata sınıfı ilişkisi korunmalı")
def m_oto(kayit):
    return eval_kaydi_dogrula(dict(kayit, otomatik="diger"))
def m_insan(kayit):
    return eval_kaydi_dogrula(dict(kayit, insan="belirsiz"))
def m_hata(kayit):
    return eval_kaydi_dogrula(dict(kayit, insan="hatali", basarisizlik="yok"))
def m_gorev(kayit):
    return eval_kaydi_dogrula(dict(kayit, gorev=""))
for ad, mutant in [("otomatik kararı bozan", m_oto), ("insan kararını bozan", m_insan), ("hata ilişkisini bozan", m_hata), ("görevi bozan", m_gorev)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def eval_kaydi_dogrula(kayit):
    import re
    if not isinstance(kayit, dict):
        raise ValueError("kayıt sözlük olmalı")
    if set(kayit) != {"id", "gorev", "otomatik", "insan", "basarisizlik"}:
        raise ValueError("kayıt şeması geçersiz")
    if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
        raise ValueError("kimlik geçersiz")
    if not isinstance(kayit["gorev"], str) or not 1 <= len(kayit["gorev"]) <= 64:
        raise ValueError("görev geçersiz")
    if kayit["otomatik"] not in ("gecerli", "hatali", "belirsiz"):
        raise ValueError("otomatik karar geçersiz")
    if kayit["insan"] not in ("gecerli", "hatali", "incelemede"):
        raise ValueError("insan kararı geçersiz")
    if kayit["insan"] == "hatali":
        if kayit["basarisizlik"] not in ("bilgi", "politika", "bicim", "diger"):
            raise ValueError("hata sınıfı geçersiz")
    elif kayit["basarisizlik"] != "yok":
        raise ValueError("hatasız kayıtta sınıf yok olmalı")
    return dict(kayit)

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    for kayit in json_yukle("veri/eval_kayitlari.json"):
        print(eval_kaydi_dogrula(kayit))
```

```hint
Önce insan kararını denetle. Hata sınıfının izinli kümesini insanın hatalı kararına, `yok` değerini diğer durumlara bağla.
```
:::

::: gorev 2 · Otomatik değerlendirici ile insan uyumunu ölç
`eval_uyum_raporu(kayitlar)` işlevini yaz. Girdi ilk görevdeki kayıtların boş olmayan listesidir; kimlikler yinelenemez. Geçersiz veride `ValueError` yükselt.

İnsan kararı `incelemede` olmayan kayıtları değerlendir. Otomatik ve insan kararı aynıysa `uyum`; otomatik `belirsiz` ise `belirsiz`; otomatik `gecerli`, insan `hatali` ise `yanlis_pozitif`; otomatik `hatali`, insan `gecerli` ise `yanlis_negatif` sayılır.

`{"sayim":S,"incelenen":N,"toplam":T,"uyum_orani":U,"ornekleme_orani":O}` döndür. `sayim` dört sınıfı `uyum`, `yanlis_pozitif`, `yanlis_negatif`, `belirsiz` sırasıyla her zaman içerir. Uyum oranı `uyum / incelenen`, örnekleme oranı `incelenen / toplam` olup 6 ondalığa yuvarlanır. İncelenen kayıt yoksa uyum oranı 0.0 olur. Girdiyi değiştirme.

```starter
def eval_uyum_raporu(kayitlar):
    import re
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar boş olmayan liste olmalı")
    temiz = []
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"id", "gorev", "otomatik", "insan", "basarisizlik"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
            raise ValueError("kimlik geçersiz")
        if not isinstance(kayit["gorev"], str) or not 1 <= len(kayit["gorev"]) <= 64:
            raise ValueError("görev geçersiz")
        if kayit["otomatik"] not in ("gecerli", "hatali", "belirsiz"):
            raise ValueError("otomatik karar geçersiz")
        if kayit["insan"] not in ("gecerli", "hatali", "incelemede"):
            raise ValueError("insan kararı geçersiz")
        if kayit["insan"] == "hatali":
            if kayit["basarisizlik"] not in ("bilgi", "politika", "bicim", "diger"):
                raise ValueError("hata sınıfı geçersiz")
        elif kayit["basarisizlik"] != "yok":
            raise ValueError("hatasız kayıtta sınıf yok olmalı")
        temiz.append(dict(kayit))
    if len({x["id"] for x in temiz}) != len(temiz):
        raise ValueError("kimlikler yinelenemez")
    sayim = {"uyum": 0, "yanlis_pozitif": 0, "yanlis_negatif": 0, "belirsiz": 0}
    incelenen = 0
    for kayit in temiz:
        if kayit["insan"] == "incelemede":
            continue
        incelenen += 1
        if kayit["otomatik"] == kayit["insan"]:
            sinif = "uyum"
        elif kayit["otomatik"] == "belirsiz":
            sinif = "belirsiz"
        elif kayit["insan"] in ("hatali",):
            sinif = "yanlis_pozitif"
        else:
            sinif = "yanlis_negatif"
        sayim[sinif] += 1
    # KUSURLU BAŞLANGIÇ KODU: uyum paydasına henüz incelenmemiş kayıtları da katıyor.
    uyum = sayim["uyum"] / len(temiz)
    return {"sayim": sayim, "incelenen": incelenen, "toplam": len(temiz), "uyum_orani": round(uyum, 6), "ornekleme_orani": round(incelenen / len(temiz), 6)}

from ai_guvence_veri import json_yukle
print(eval_uyum_raporu(json_yukle("veri/eval_kayitlari.json")))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-27")
```

```test
import copy
K = [
    {"id": "a", "gorev": "g1", "otomatik": "gecerli", "insan": "gecerli", "basarisizlik": "yok"},
    {"id": "b", "gorev": "g2", "otomatik": "gecerli", "insan": "hatali", "basarisizlik": "politika"},
    {"id": "c", "gorev": "g1", "otomatik": "hatali", "insan": "gecerli", "basarisizlik": "yok"},
    {"id": "d", "gorev": "g3", "otomatik": "belirsiz", "insan": "hatali", "basarisizlik": "bicim"},
    {"id": "e", "gorev": "g2", "otomatik": "hatali", "insan": "hatali", "basarisizlik": "bilgi"},
    {"id": "f", "gorev": "g1", "otomatik": "gecerli", "insan": "incelemede", "basarisizlik": "yok"},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        sonuc = fn(K)
        if K != once or sonuc != {"sayim": {"uyum": 2, "yanlis_pozitif": 1, "yanlis_negatif": 1, "belirsiz": 1}, "incelenen": 5, "toplam": 6, "uyum_orani": 0.4, "ornekleme_orani": 0.833333}:
            return False
        if fn(K[5:]) != {"sayim": {"uyum": 0, "yanlis_pozitif": 0, "yanlis_negatif": 0, "belirsiz": 0}, "incelenen": 0, "toplam": 1, "uyum_orani": 0.0, "ornekleme_orani": 0.0}:
            return False
        sinir = dict(K[0], id="a" * 64, gorev="g" * 64)
        if fn([sinir])["uyum_orani"] != 1.0 or fn([sinir])["ornekleme_orani"] != 1.0 or fn([dict(sinir, gorev="g")])["toplam"] != 1:
            return False
        uc = fn(K[:3])
        if uc["uyum_orani"] != 0.333333 or uc["ornekleme_orani"] != 1.0 or fn(K[:2])["sayim"] != {"uyum": 1, "yanlis_pozitif": 1, "yanlis_negatif": 0, "belirsiz": 0}:
            return False
        for kayitlar in [
            None, {}, tuple(K), [], [None], [dict(K[0], ek=1)], [dict(K[0], id="a b")], [dict(K[0], id="a" * 65)], [dict(K[0], id=None)],
            [dict(K[0], gorev="")], [dict(K[0], gorev="g" * 65)], [dict(K[0], gorev=None)],
            [dict(K[0], otomatik="diger")], [dict(K[0], otomatik=None)], [dict(K[0], insan="belirsiz")], [dict(K[0], insan=None)],
            [dict(K[0], basarisizlik="bilgi")], [dict(K[0], basarisizlik=None)], [dict(K[0], insan="hatali", basarisizlik="yok")],
            [K[0], K[0]],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(eval_uyum_raporu), "uyum sınıfları, inceleme paydası ve örnekleme oranı korunmalı")
def m_insan(kayitlar):
    return eval_uyum_raporu([dict(x, insan="incelemede", basarisizlik="yok") for x in kayitlar])
def m_oto(kayitlar):
    return eval_uyum_raporu([dict(x, otomatik="gecerli") for x in kayitlar])
def m_sil(kayitlar):
    return eval_uyum_raporu(kayitlar[:1])
def m_id(kayitlar):
    return eval_uyum_raporu([dict(x, id="a") for x in kayitlar])
for ad, mutant in [("insanı silen", m_insan), ("otomatiği değiştiren", m_oto), ("kayıtları silen", m_sil), ("kimlikleri yineleyen", m_id)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def eval_uyum_raporu(kayitlar):
    import re
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar boş olmayan liste olmalı")
    temiz = []
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"id", "gorev", "otomatik", "insan", "basarisizlik"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
            raise ValueError("kimlik geçersiz")
        if not isinstance(kayit["gorev"], str) or not 1 <= len(kayit["gorev"]) <= 64:
            raise ValueError("görev geçersiz")
        if kayit["otomatik"] not in ("gecerli", "hatali", "belirsiz"):
            raise ValueError("otomatik karar geçersiz")
        if kayit["insan"] not in ("gecerli", "hatali", "incelemede"):
            raise ValueError("insan kararı geçersiz")
        if kayit["insan"] == "hatali":
            if kayit["basarisizlik"] not in ("bilgi", "politika", "bicim", "diger"):
                raise ValueError("hata sınıfı geçersiz")
        elif kayit["basarisizlik"] != "yok":
            raise ValueError("hatasız kayıtta sınıf yok olmalı")
        temiz.append(dict(kayit))
    if len({x["id"] for x in temiz}) != len(temiz):
        raise ValueError("kimlikler yinelenemez")
    sayim = {"uyum": 0, "yanlis_pozitif": 0, "yanlis_negatif": 0, "belirsiz": 0}
    incelenen = 0
    for kayit in temiz:
        if kayit["insan"] == "incelemede":
            continue
        incelenen += 1
        if kayit["otomatik"] == kayit["insan"]:
            sinif = "uyum"
        elif kayit["otomatik"] == "belirsiz":
            sinif = "belirsiz"
        elif kayit["insan"] in ("hatali",):
            sinif = "yanlis_pozitif"
        else:
            sinif = "yanlis_negatif"
        sayim[sinif] += 1
    uyum = sayim["uyum"] / incelenen if incelenen else 0.0
    return {"sayim": sayim, "incelenen": incelenen, "toplam": len(temiz), "uyum_orani": round(uyum, 6), "ornekleme_orani": round(incelenen / len(temiz), 6)}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    print(eval_uyum_raporu(json_yukle("veri/eval_kayitlari.json")))
```

```hint
İncelemede kayıtlarını önce atla. Sınıflandırmada eşitlik ve belirsizlik dallarını yanlış pozitif ile negatiften önce kontrol et.
```
:::

::: gorev 3 · Örnekleme, uyum ve hata sınıflarıyla kalibrasyon kararı ver
`eval_kalibrasyon_raporu(kayitlar, min_ornekleme, min_uyum)` işlevini yaz. Kayıtlar ikinci görevdeki kurallara uyar. Eşikler bool olmayan, sonlu, 0–1 aralığında `int` veya `float` olmalıdır; geçersiz veride `ValueError` yükselt.

İkinci görevdeki bütün alanları hesapla. Ayrıca insan tarafından `hatali` bulunan kayıtların `basarisizlik` dağılımını `bilgi`, `politika`, `bicim`, `diger` sırasıyla ve her anahtar her zaman bulunacak şekilde `hata_siniflari` alanında döndür.

Ham örnekleme oranı `min_ornekleme` altındaysa `ornekleme_yetersiz`; incelenen kayıt yokken uyum oranını 0 kabul ederek ham uyum oranı `min_uyum` altındaysa `uyum_yetersiz` alarmı ekle. Tam eşikte alarm yoktur. Alarm yoksa karar `kalibre`, varsa `gozden_gecir` olur.

`{"sayim":S,"incelenen":N,"toplam":T,"uyum_orani":U,"ornekleme_orani":O,"hata_siniflari":H,"alarmlar":A,"karar":K}` döndür. Girdiyi değiştirme.

```starter
def eval_kalibrasyon_raporu(kayitlar, min_ornekleme, min_uyum):
    import math
    import re
    for esik in (min_ornekleme, min_uyum):
        if not isinstance(esik, (int, float)) or isinstance(esik, bool) or not math.isfinite(esik) or not 0 <= esik <= 1:
            raise ValueError("eşikler sonlu ve izinli aralıkta olmalı")
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar boş olmayan liste olmalı")
    temiz = []
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"id", "gorev", "otomatik", "insan", "basarisizlik"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
            raise ValueError("kimlik geçersiz")
        if not isinstance(kayit["gorev"], str) or not 1 <= len(kayit["gorev"]) <= 64:
            raise ValueError("görev geçersiz")
        if kayit["otomatik"] not in ("gecerli", "hatali", "belirsiz"):
            raise ValueError("otomatik karar geçersiz")
        if kayit["insan"] not in ("gecerli", "hatali", "incelemede"):
            raise ValueError("insan kararı geçersiz")
        if kayit["insan"] == "hatali":
            if kayit["basarisizlik"] not in ("bilgi", "politika", "bicim", "diger"):
                raise ValueError("hata sınıfı geçersiz")
        elif kayit["basarisizlik"] != "yok":
            raise ValueError("hatasız kayıtta sınıf yok olmalı")
        temiz.append(dict(kayit))
    if len({x["id"] for x in temiz}) != len(temiz):
        raise ValueError("kimlikler yinelenemez")
    sayim = {"uyum": 0, "yanlis_pozitif": 0, "yanlis_negatif": 0, "belirsiz": 0}
    hata_siniflari = {"bilgi": 0, "politika": 0, "bicim": 0, "diger": 0}
    incelenen = 0
    for kayit in temiz:
        if kayit["insan"] == "hatali":
            hata_siniflari[kayit["basarisizlik"]] += 1
        if kayit["insan"] == "incelemede":
            continue
        incelenen += 1
        if kayit["otomatik"] == kayit["insan"]:
            sinif = "uyum"
        elif kayit["otomatik"] == "belirsiz":
            sinif = "belirsiz"
        elif kayit["insan"] in ("hatali",):
            sinif = "yanlis_pozitif"
        else:
            sinif = "yanlis_negatif"
        sayim[sinif] += 1
    ham_uyum = sayim["uyum"] / incelenen if incelenen else 0.0
    ham_ornekleme = incelenen / len(temiz)
    alarmlar = []
    if ham_ornekleme < min_ornekleme:
        alarmlar.append("ornekleme_yetersiz")
    # KUSURLU BAŞLANGIÇ KODU: tam eşitlikte de uyum alarmı veriyor.
    if ham_uyum <= min_uyum:
        alarmlar.append("uyum_yetersiz")
    return {"sayim": sayim, "incelenen": incelenen, "toplam": len(temiz), "uyum_orani": round(ham_uyum, 6), "ornekleme_orani": round(ham_ornekleme, 6), "hata_siniflari": hata_siniflari, "alarmlar": alarmlar, "karar": "gozden_gecir" if alarmlar else "kalibre"}

from ai_guvence_veri import json_yukle
esikler = json_yukle("veri/esikler.json")
print(eval_kalibrasyon_raporu(json_yukle("veri/eval_kayitlari.json"), **esikler))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-27")
```

```test
import copy
K = [
    {"id": "a", "gorev": "g1", "otomatik": "gecerli", "insan": "gecerli", "basarisizlik": "yok"},
    {"id": "b", "gorev": "g2", "otomatik": "gecerli", "insan": "hatali", "basarisizlik": "politika"},
    {"id": "c", "gorev": "g1", "otomatik": "hatali", "insan": "gecerli", "basarisizlik": "yok"},
    {"id": "d", "gorev": "g3", "otomatik": "belirsiz", "insan": "hatali", "basarisizlik": "bicim"},
    {"id": "e", "gorev": "g2", "otomatik": "hatali", "insan": "hatali", "basarisizlik": "bilgi"},
    {"id": "f", "gorev": "g1", "otomatik": "gecerli", "insan": "incelemede", "basarisizlik": "yok"},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        sonuc = fn(K, 0.8, 0.5)
        if K != once or sonuc["alarmlar"] != ["uyum_yetersiz"] or sonuc["karar"] != "gozden_gecir":
            return False
        if sonuc["sayim"] != {"uyum": 2, "yanlis_pozitif": 1, "yanlis_negatif": 1, "belirsiz": 1} or sonuc["incelenen"] != 5 or sonuc["toplam"] != 6:
            return False
        if sonuc["uyum_orani"] != 0.4 or sonuc["ornekleme_orani"] != 0.833333:
            return False
        if sonuc["hata_siniflari"] != {"bilgi": 1, "politika": 1, "bicim": 1, "diger": 0}:
            return False
        if fn(K, 0.9, 0.3)["alarmlar"] != ["ornekleme_yetersiz"] or fn(K, 0.9, 0.5)["alarmlar"] != ["ornekleme_yetersiz", "uyum_yetersiz"]:
            return False
        sinir = fn(K, 5 / 6, 0.4)
        if sinir["alarmlar"] != [] or sinir["karar"] != "kalibre":
            return False
        bos = fn(K[5:], 0, 0)
        if bos["hata_siniflari"] != {"bilgi": 0, "politika": 0, "bicim": 0, "diger": 0} or bos["uyum_orani"] != 0.0 or bos["karar"] != "kalibre":
            return False
        if fn(K[5:], 0, 0.1)["alarmlar"] != ["uyum_yetersiz"]:
            return False
        if fn(K, 1, 1)["alarmlar"] != ["ornekleme_yetersiz", "uyum_yetersiz"]:
            return False
        if fn([dict(K[0], gorev="g")], 1, 1)["karar"] != "kalibre" or fn([dict(K[0], gorev="g" * 64)], 1, 1)["karar"] != "kalibre":
            return False
        uc = fn(K[:3], 1, 0.5)
        if uc["uyum_orani"] != 0.333333 or uc["ornekleme_orani"] != 1.0 or fn(K[:2], 1, 0.5)["sayim"] != {"uyum": 1, "yanlis_pozitif": 1, "yanlis_negatif": 0, "belirsiz": 0}:
            return False
        for args in [
            (None, 0.8, 0.5), (tuple(K), 0.8, 0.5), ([], 0.8, 0.5), ([None], 0.8, 0.5), ([dict(K[0], ek=1)], 0.8, 0.5),
            ([dict(K[0], id="a b")], 0.8, 0.5), ([dict(K[0], id="a" * 65)], 0.8, 0.5), ([dict(K[0], id=None)], 0.8, 0.5),
            ([dict(K[0], gorev="")], 0.8, 0.5), ([dict(K[0], gorev="g" * 65)], 0.8, 0.5), ([dict(K[0], gorev=None)], 0.8, 0.5),
            ([dict(K[0], otomatik="diger")], 0.8, 0.5), ([dict(K[0], otomatik=None)], 0.8, 0.5),
            ([dict(K[0], insan="belirsiz")], 0.8, 0.5), ([dict(K[0], insan=None)], 0.8, 0.5),
            ([dict(K[0], basarisizlik="bilgi")], 0.8, 0.5), ([dict(K[0], basarisizlik=None)], 0.8, 0.5),
            ([dict(K[0], insan="hatali", basarisizlik="yok")], 0.8, 0.5), ([K[0], K[0]], 0.8, 0.5),
            (K, -0.1, 0.5), (K, 1.1, 0.5), (K, float("nan"), 0.5), (K, float("inf"), 0.5), (K, True, 0.5), (K, None, 0.5),
            (K, 0.8, -0.1), (K, 0.8, 1.1), (K, 0.8, float("nan")), (K, 0.8, float("inf")), (K, 0.8, False), (K, 0.8, None),
        ]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(eval_kalibrasyon_raporu), "kalibrasyon eşikleri, hata dağılımı ve alarm sırası korunmalı")
def m_hata(kayitlar, min_ornekleme, min_uyum):
    return eval_kalibrasyon_raporu([dict(x, basarisizlik="diger" if x["insan"] == "hatali" else "yok") for x in kayitlar], min_ornekleme, min_uyum)
def m_insan(kayitlar, min_ornekleme, min_uyum):
    return eval_kalibrasyon_raporu([dict(x, insan="incelemede", basarisizlik="yok") for x in kayitlar], min_ornekleme, min_uyum)
def m_esik(kayitlar, min_ornekleme, min_uyum):
    return eval_kalibrasyon_raporu(kayitlar, 0, 0)
def m_oto(kayitlar, min_ornekleme, min_uyum):
    return eval_kalibrasyon_raporu([dict(x, otomatik="gecerli") for x in kayitlar], min_ornekleme, min_uyum)
for ad, mutant in [("hataları değiştiren", m_hata), ("insanı silen", m_insan), ("eşikleri silen", m_esik), ("otomatiği değiştiren", m_oto)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def eval_kalibrasyon_raporu(kayitlar, min_ornekleme, min_uyum):
    import math
    import re
    for esik in (min_ornekleme, min_uyum):
        if not isinstance(esik, (int, float)) or isinstance(esik, bool) or not math.isfinite(esik) or not 0 <= esik <= 1:
            raise ValueError("eşikler sonlu ve izinli aralıkta olmalı")
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar boş olmayan liste olmalı")
    temiz = []
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"id", "gorev", "otomatik", "insan", "basarisizlik"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
            raise ValueError("kimlik geçersiz")
        if not isinstance(kayit["gorev"], str) or not 1 <= len(kayit["gorev"]) <= 64:
            raise ValueError("görev geçersiz")
        if kayit["otomatik"] not in ("gecerli", "hatali", "belirsiz"):
            raise ValueError("otomatik karar geçersiz")
        if kayit["insan"] not in ("gecerli", "hatali", "incelemede"):
            raise ValueError("insan kararı geçersiz")
        if kayit["insan"] == "hatali":
            if kayit["basarisizlik"] not in ("bilgi", "politika", "bicim", "diger"):
                raise ValueError("hata sınıfı geçersiz")
        elif kayit["basarisizlik"] != "yok":
            raise ValueError("hatasız kayıtta sınıf yok olmalı")
        temiz.append(dict(kayit))
    if len({x["id"] for x in temiz}) != len(temiz):
        raise ValueError("kimlikler yinelenemez")
    sayim = {"uyum": 0, "yanlis_pozitif": 0, "yanlis_negatif": 0, "belirsiz": 0}
    hata_siniflari = {"bilgi": 0, "politika": 0, "bicim": 0, "diger": 0}
    incelenen = 0
    for kayit in temiz:
        if kayit["insan"] == "hatali":
            hata_siniflari[kayit["basarisizlik"]] += 1
        if kayit["insan"] == "incelemede":
            continue
        incelenen += 1
        if kayit["otomatik"] == kayit["insan"]:
            sinif = "uyum"
        elif kayit["otomatik"] == "belirsiz":
            sinif = "belirsiz"
        elif kayit["insan"] in ("hatali",):
            sinif = "yanlis_pozitif"
        else:
            sinif = "yanlis_negatif"
        sayim[sinif] += 1
    ham_uyum = sayim["uyum"] / incelenen if incelenen else 0.0
    ham_ornekleme = incelenen / len(temiz)
    alarmlar = []
    if ham_ornekleme < min_ornekleme:
        alarmlar.append("ornekleme_yetersiz")
    if ham_uyum < min_uyum:
        alarmlar.append("uyum_yetersiz")
    return {"sayim": sayim, "incelenen": incelenen, "toplam": len(temiz), "uyum_orani": round(ham_uyum, 6), "ornekleme_orani": round(ham_ornekleme, 6), "hata_siniflari": hata_siniflari, "alarmlar": alarmlar, "karar": "gozden_gecir" if alarmlar else "kalibre"}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    esikler = json_yukle("veri/esikler.json")
    print(eval_kalibrasyon_raporu(json_yukle("veri/eval_kayitlari.json"), **esikler))
```

```hint
Hata sınıfı dağılımını insanın hatalı kararlarından üret. Alarm kararlarında ham oranları kullan; raporlanan oranları en sonda yuvarla.
```
:::


::: anlat Gerçek deney · Ayrı kalibrasyon ve açık eval
Önce görünür sentetik [ayar dosyasını](/data/ai-guvence-27-deney.txt) incele: /data/ai-guvence-27-deney.txt. Bu bir sunucu kaydı değildir. Çalıştır ilk kullanımda ayrı kalıcı kopya oluşturur ve gerçek yol/içeriğini gösterir. Yerleşik dosya editörü yoktur; yolu yerel editörde aç, seed veya eps değiştir ve yeniden Çalıştır. Kopya varsa üzerine yazılmaz. Göreli PAFTA_DATA proje köküne göre çözülür; geçici koşucu klasörüne göre değil. Kontrol ayrı görülmemiş ayarı kullanır; öğrenci dosyasını değiştirmek beklenen cevabı değiştirmez.

sicaklik_sec(logits,labels,grid): yalnız verilen kalibrasyon bölmesinde cross entropy en küçük sıcaklığı seç; eşitte grid içindeki ilk. acik_eval_skoru(logits,labels,t): logits/t için NLL, doğruluk ve ECE hesapla. ECE bölmeleri `(0, .5]`, `(.5, .7]`, `(.7, .9]`, `(.9, 1.]`; her bölmenin `|ortalama güven - doğruluk|` değerini örnek payıyla ağırlıkla. `n`, `nll`, `dogruluk`, `ece` döndür; son 3 alan 6 basamak. Model eğitim `0:96`, kalibrasyon `96:144`, test `144:192`; testten sıcaklık seçilmez. [Guo vd.2017](https://proceedings.mlr.press/v70/guo17a.html) yönteminden küçük sentetik uyarlama; genel kalibrasyon garantisi yok.

CPU .ai-venv torch ile gerçek Adam/autograd eğitimi, ağırlık hash'i, ham logitler ve ölçüm kanıtı yazılır. Model indirilmez, GPU kullanılmaz. Testte geçici ağırlıklar temizlenir; eğitim/logit/hash kanıtta korunur. Çalıştır çıktıları kalıcı öğrenci klasöründe kalır. Eski adımlar yukarıda fixture olarak korunmuştur; bu ek adım canlı deneydir.
:::

::: gorev Gerçek deney · Ayrı kalibrasyon ve açık eval
sicaklik_sec(logits,labels,grid): yalnız verilen kalibrasyon bölmesinde cross entropy en küçük sıcaklığı seç; eşitte grid içindeki ilk. acik_eval_skoru(logits,labels,t): logits/t için NLL, doğruluk ve ECE hesapla. ECE bölmeleri `(0, .5]`, `(.5, .7]`, `(.7, .9]`, `(.9, 1.]`; her bölmenin `|ortalama güven - doğruluk|` değerini örnek payıyla ağırlıkla. `n`, `nll`, `dogruluk`, `ece` döndür; son 3 alan 6 basamak. Model eğitim `0:96`, kalibrasyon `96:144`, test `144:192`; testten sıcaklık seçilmez. [Guo vd.2017](https://proceedings.mlr.press/v70/guo17a.html) yönteminden küçük sentetik uyarlama; genel kalibrasyon garantisi yok.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 120
```

```starter
def sicaklik_sec(*args):
    return None

def acik_eval_skoru(*args):
    return None

import ai_lab
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_27 as deney
    deney.goster(sicaklik_sec,acik_eval_skoru)
```

```test
import ai_lab
import ast
YASAK = ("attack_ref", "temperature_ref", "score_ref", "kanit_yaz")
sorunlar = ai_lab.kod_denetimi(src, yasak=YASAK)
# Import aliases have no ast.Name for their original name; inspect these explicitly.
for dugum in ast.walk(ast.parse(src)):
    if isinstance(dugum, ast.ImportFrom):
        if any(ad.name in YASAK or ad.name == "*" for ad in dugum.names):
            sorunlar.append("referans veya kanıt yazıcısı içe aktarılamaz")
if sorunlar:
    ok(False, "Kendi ölçüm işlevlerini yaz: " + "; ".join(sorunlar))
    stop()
import tempfile
from pathlib import Path
from sandbox import ai_gercek_ai_guvence_27 as deney
# Test configuration is separate from the persistent editable student copy.
import torch as _tc
_lg = _tc.tensor([[4.0, 0.0], [4.0, 0.0], [0.0, 4.0]], dtype=_tc.float32)
_lb = _tc.tensor([0, 1, 1], dtype=_tc.long)
ok(sicaklik_sec(_lg, _lb, [0.5, 2.0, 4.0]) == 4.0 and sicaklik_sec(_tc.zeros((2, 2)), _tc.tensor([0, 1]), [1.5, 2.5]) == 1.5, 'sicaklik_sec NLL en küçük sıcaklığı ve eşitlikte ilk elemanı seçmeli')
_sk = acik_eval_skoru(_tc.tensor([[0.0, 0.0], [0.4054651, 0.0], [1.3862944, 0.0], [3.0, 0.0]]), _tc.tensor([0, 1, 0, 0]), 1.0)
ok(_sk['n'] == 4 and _sk['dogruluk'] == 0.75 and 0.1 < _sk['ece'] < 0.4 and len(str(_sk['nll']).split('.')[-1]) <= 6, 'acik_eval_skoru tüm ECE bölmelerini ve 6 basamak yuvarlamayı doğru hesaplamalı')
_sk3 = acik_eval_skoru(_lg, _lb, 2.0)
ok(_sk3 == {'n': 3, 'nll': round(float(_tc.nn.functional.cross_entropy(_lg / 2.0, _lb)), 6), 'dogruluk': 0.666667, 'ece': round(abs(float((_lg / 2.0).softmax(-1).max(-1).values.mean()) - 2 / 3), 6)}, 'acik_eval_skoru 1/3 kesirlerinde 6 basamak yuvarlamayı korumalı')
import math as _mt
ok(acik_eval_skoru(_tc.tensor([[0.0, 0.0, 0.0]], dtype=_tc.float64), _tc.tensor([1]), 1.0)['ece'] == 0.333333 and acik_eval_skoru(_tc.tensor([[0.0, 0.0, -1000.0]], dtype=_tc.float64), _tc.tensor([1]), 1.0)['ece'] == 0.5 and acik_eval_skoru(_tc.tensor([[_mt.log(1.5), 0.0]], dtype=_tc.float64), _tc.tensor([1]), 1.0)['ece'] == 0.6 and acik_eval_skoru(_tc.tensor([[_mt.log(0.7 / 0.3), 0.0]], dtype=_tc.float64), _tc.tensor([1]), 1.0)['ece'] == 0.7 and acik_eval_skoru(_tc.tensor([[_mt.log(4.0), 0.0]], dtype=_tc.float64), _tc.tensor([1]), 1.0)['ece'] == 0.8 and acik_eval_skoru(_tc.tensor([[_mt.log(9.0), 0.0]], dtype=_tc.float64), _tc.tensor([1]), 1.0)['ece'] == 0.9 and acik_eval_skoru(_tc.tensor([[_mt.log(19.0), 0.0]], dtype=_tc.float64), _tc.tensor([1]), 1.0)['ece'] == 0.95 and acik_eval_skoru(_tc.tensor([[1000.0, 0.0]], dtype=_tc.float64), _tc.tensor([1]), 1.0)['ece'] == 1.0, 'acik_eval_skoru her dört ECE bölmesini, (a, b] sınırlarını ve 6 basamak yuvarlamayı korumalı')
with tempfile.TemporaryDirectory(prefix="pafta-guvence-27-") as tmp:
    config=Path(tmp)/"ayar.json"
    config.write_text('{"seed":940,"eps":0.23}',encoding="utf-8")
    r=deney.deney(sicaklik_sec,acik_eval_skoru,config,Path(tmp)/"deney")
    for name,value in r["kontroller"].items():ok(value,"GERCEK: "+name)
    ai_lab.kanit_yaz("guvence-27",dict(r,kabul=all(r["kontroller"].values())))
```

```solution
def sicaklik_sec(logits,labels,grid):
    import torch
    return min(grid,key=lambda t:float(torch.nn.functional.cross_entropy(logits/t,labels)))

def acik_eval_skoru(logits,labels,t):
    import torch
    p=(logits/t).softmax(-1);confidence,pred=p.max(-1);correct=(pred==labels).float();ece=0.
    for a,b in [(0.,.5),(.5,.7),(.7,.9),(.9,1.)]:
        mask=(confidence>a)&(confidence<=b)
        if mask.any():ece+=float(mask.float().mean())*abs(float(confidence[mask].mean()-correct[mask].mean()))
    return dict(n=len(labels),nll=round(float(torch.nn.functional.cross_entropy(logits/t,labels)),6),dogruluk=round(float(correct.mean()),6),ece=round(ece,6))

import ai_lab
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_27 as deney
    deney.goster(sicaklik_sec,acik_eval_skoru)
```

```hint
Fonksiyonların etkisini gerçek model/araç akışında koru. Sabit oran veya hep izin/red kullanma. Bağımlılık yoksa gerçek kabul verilmez. Veri sentetiktir, eğitim ve dosya etkileri gerçektir.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Değerlendiriciyi kim değerlendirir? (`eval calibration`) (35 sn).** "Otomatik güvenlik hakemi (`LLM-as-a-judge` veya sınıflandırıcı) insan etiketleriyle tam uyuşmaz; kalibrasyon bölmesinde insan kararlarıyla uyum oranı, yanlış red ve kaçırma sınıfları ölçülmeden hakem skoruna güvenilmez."
2. **Ayrık kalibrasyon bölmesinde sıcaklık seçimi (30 sn).** "Sıcaklık parametresi $T$, test kümesine hiç bakmadan yalnız `kalibrasyon` bölmesinde `NLL` en küçük olacak biçimde seçilir; ardından kilitli test kümesinde `ECE` ve doğruluk raporlanır."
3. **Açık değerlendirme şeffaflığı (30 sn).** "İyi bir açık `eval`, yalnız tek bir yüzdelik skor değil; örneklem büyüklüğü, bölme sınırları ve hakemin nerede yanıldığına dair hata dağılımını birlikte yayımlar."
4. **Soru (25 sn).** "Sıcaklık parametresini kalibrasyon yerine doğrudan test kümesi üzerinde optimize edersek raporlanan `ECE` neden iyimser biçimde yanlı çıkar?"
:::
