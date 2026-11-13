---
id: ai-guvence-18
title: Overfitting ile Gizlilik Riski İlişkisi
summary: Kapasite ve epoch kayıtlarında genelleme açığını hesapla; üyelik AUC'siyle birlikte risk sinyallerini karşılaştır.
esleme: ai-guvence-16, ai-guvence-17, ai-guvence-19
timeout: 45
---

::: anlat Genelleme açığı ile gizlilik riski aynı şey değildir
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Eğitim/test doğruluğu, örnek bazında güven skorları ve üyelik ayırt etme başarısı | Görevler 1–3 görünür sentetik JSON deney kayıtları; son görevde iki seed ile 3 ve 35 epoch gerçekten eğitilen yerel 12-24-2 MLP | Genelleme açığı gizlilik ihlalinin kanıtı değildir; küçük sentetik model sonucu bütün modelleri veya saldırıları temsil etmez |

> [!NOT]
> `veri/deney_kayitlari.json` ve `veri/esikler.json` elle yazılmış sentetik öğretim dosyalarıdır. Setup bunları her çalıştırmada geçici dizine yeniden kopyalar; değişiklikler kalıcı değildir. Başlangıç kodu dosyaları gerçekten okur; bellekte kopyayı değiştirip aynı çalıştırmada deneme yapabilirsin. Son gerçek deneyin `PAFTA_DATA/calisma/ai-guvence-18/ayarlar.json` kopyası ise kalıcıdır ve varsa üzerine yazılmaz. Gizli test girdileri öğrenci örneğinden ayrıdır.

Eğitim doğruluğu ile test doğruluğu arasındaki fark genelleme açığıdır. Büyük açık overfitting sinyali olabilir; üyelik çıkarımı AUC'si ise saldırının üyeleri üye olmayanlardan ayırma başarısını özetler. Bu iki ölçüm ilişkili olabilir ancak biri diğerinin kanıtı değildir.

İlk üç görevde kapasite, epoch, doğruluk ve AUC değerleri sentetik dosya kayıtlarıdır. Son adım gerçek PyTorch autograd eğitimiyle ölçüm üretir; eğitim verisi yine sentetiktir. Amaç aynı deney düzenindeki sonuçları ölçülebilir ve karşılaştırılabilir biçimde raporlamaktır.
:::

::: anlat Kapasite ve eğitim süresi birlikte okunmalıdır
Kapasite artırılırken epoch sabit tutulabilir veya aynı kapasitede eğitim süresi uzatılabilir. Genelleme açığı `egitim_dogrulugu-test_dogrulugu` olarak hesaplanır. Negatif değer de geçerli bir ölçümdür ve otomatik olarak sıfıra çekilmez.

Risk bayrağı bu derste iki koşulun birlikte sağlanmasını gerektirir: genelleme açığı kendi eşiğine, üyelik AUC'si kendi eşiğine eşit veya büyük olmalıdır. Riskli kayıtlar arasında önce yüksek AUC, sonra yüksek açık, en son alfabetik kimlik seçilir. Bu sıralama kesin ihlal hükmü değil, inceleme önceliğidir.
:::

::: anlat Dosya, eğitim ve üyelik ölçümünü birlikte oku
Bir gizlilik deneyini okumaya başlamadan önce hangi kayıtların eğitimde kullanıldığını ve hangi kayıtların dışarıda bırakıldığını bilmelisin. Üyelik çıkarımı, bir örneğin eğitim kümesine katılıp katılmadığını verilen model davranışından tahmin eder. Bu derste gözlem olarak modelin doğru sınıfa verdiği olasılık kullanılır. Eğitim örneklerinde yüksek güven bazen üyelik sinyali taşır; fakat tek bir yüksek olasılık kesin üyelik kanıtı değildir. Eğitimin nasıl yapıldığı, örneklerin zorluğu ve dağılımların benzerliği bu ölçümü etkiler. Bu nedenle eğitim doğruluğu ile üyelik çıkarımı başarısını ayrı alanlarda tutuyoruz.

İlk görevde `veri/deney_kayitlari.json` dosyasını okuyup kayıtları yazdır. JSON dosyası, bir deney hattından alınabilecek kayıt biçimini öğretmek için hazırlanmıştır; canlı deney çıktısı diye yorumlanmamalıdır. Kimliğin, kapasitenin ve epoch sayısının geçerliliğini denetlemeden sonuçları birleştirmek birbirinden farklı deneyleri aynı başlıkta toplamana yol açar. Python'da bool bir int alt türüdür; kapasite alanındaki True değerini bir parametre sayısı olarak kabul etmemelisin. NaN ve sonsuzluk ise görünürde sayıdır ama sıralama ve karşılaştırma mantığını bozar. Şema doğrulaması sonuçların biyolojik veya toplumsal anlamını doğrulamaz; yalnız rapor hesaplamasının giriş sözleşmesini korur.

İkinci görevde aynı dosyayı kapasite ve epoch sırasıyla raporlayacaksın. Eğitim doğruluğundan test doğruluğunu çıkararak genelleme açığını bul. Negatif açık mümkündür: küçük örneklemde test kümesi daha kolay gelmiş olabilir. Negatif sonucu sıfıra kırpmak ham gözlemi gizler. Seçim sıralamasında ham açık ve ham AUC kullan; ekrana altı ondalıkla basılan değerler eşit görünse de gerçek değerler farklı olabilir. Eşitlikleri çözmek için belirtilmiş kimlik sırasını kullanmak tekrar üretilebilir bir rapor sağlar. Kapasiteyi veya epoch'u değiştirirken diğer koşulları kaydetmezsen nedensel bir yorum yapamazsın.

Üçüncü görev, dosyadaki eşikleri kullanarak inceleme önceliği çıkarır. Açık ile AUC koşulları birlikte sağlanmalıdır; bunları or ile bağlamak yüksek açık fakat düşük ayırt etme başarısı olan bir kaydı yanlış işaretler. Tam eşikte eşitlik kabul edilir. Buradaki riskli etiketi eğitim amaçlı bir karar kuralıdır; resmi gizlilik garantisi veya gerçek kişiye ait ihlal bildirimi değildir. Kayıtlardan birinin test doğruluğunu bellekte değiştirip raporu yeniden hesapla; tek bir alanın seçilen kimliği nasıl değiştirdiğine bak. Görünür örnek üzerinde işe yarayan sabit bir cevap, farklı sınırları kullanan kontrol testini geçmemelidir.

Son adımda yerel MLP gerçekten eğitilir. Küçük sentetik özellikler ve etiketler oluşturulur; SGD, çapraz entropi kaybının gerçek autograd türevleriyle ağırlıkları günceller. Aynı seed ve aynı mimari ile kısa ve uzun eğitim karşılaştırılır; iki farklı seed ile gözlemin tekrarı alınır. Üyelik AUC hesabı, üye ile üye olmayan örneklerin skor sıralamasını karşılaştırır ve eşit skorlara yarım katkı verir. AUC yaklaşık 0.5 ise bu gözlemciyle ayrım zayıftır; bütün olası saldırıların başarısız olduğu sonucu çıkmaz. Tersine yüksek AUC, bu deney ve skor için bir gizlilik riski sinyalidir.

Saldırgan daha uygun bir skor, farklı eşik veya ek bilgi deneyebilir; savunma yalnız model doğruluğuna bakarsa bu yolu kaçırır. Eğitim süresini azaltmak veya kapasiteyi sınırlamak bazı durumlarda riski etkileyebilir, fakat diferansiyel gizlilik garantisi vermez. Çıktıda eğitim/test doğruluğunu, açık ve AUC'yi birlikte incele; riskin mutlaka artmasını kabul şartı yapma. Kanıt dosyası seed, örnek sayısı, eğitim kaybı, model ağırlık hash'i ve ham skorları saklar. Bu izler sentetik veride öğretim içindir; özel bir veri kümesinde ham izleri yayımlamak ayrı bir sızıntı yaratabilir.
:::

::: tahmin Genelleme açığını ve risk bayrağını tahmin et
Üç çıktı satırını yaz:

```python
print(round(0.9 - 0.65, 6))
print(round(1 / 3, 6))
print(0.25 >= 0.25 and 0.8 >= 0.7)
```

???

```cikti
0.25
0.333333
True
```

İlk satır genelleme açığını, ikinci satır yuvarlanmış örnek oranı, üçüncü satır iki risk koşulunun eşikte eşitlik kabul ettiğini gösterir.
:::

::: gorev 1 · overfitting deney kaydını doğrula
`deney_kaydi_dogrula(kayit)` işlevini yaz. Kayıt tam olarak `id`, `kapasite`, `epoch`, `egitim_dogrulugu`, `test_dogrulugu`, `uyelik_auc` alanlarını taşıyan sözlüktür. Kimlik 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren stringdir.

Kapasite bool olmayan tam sayı ve `[1,100000]`, epoch bool olmayan tam sayı ve `[1,10000]` aralığındadır. Üç ölçüm bool olmayan sonlu sayı ve `[0,1]` aralığında olmalıdır. Geçersiz veride `ValueError` yükselt. Aynı alanları taşıyan bağımsız sözlük kopyası döndür ve girdiyi değiştirme.

```starter
def deney_kaydi_dogrula(kayit):
    # KUSURLU BAŞLANGIÇ KODU: sözlüğü kopyalıyor ama tür, sonluluk ve sınırları denetlemiyor.
    return dict(kayit)

from ai_guvence_veri import json_yukle
for kayit in json_yukle("veri/deney_kayitlari.json"):
    print(deney_kaydi_dogrula(kayit))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-18")
```

```test
import copy
K = {"id": "deney-1", "kapasite": 20, "epoch": 10, "egitim_dogrulugu": 0.9, "test_dogrulugu": 0.65, "uyelik_auc": 0.75}
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        sonuc = fn(K)
        if sonuc != K or sonuc is K or K != once:
            return False
        sinir = {"id": "a" * 64, "kapasite": 1, "epoch": 1, "egitim_dogrulugu": 0, "test_dogrulugu": 1, "uyelik_auc": 0}
        if fn(sinir) != sinir:
            return False
        ust = dict(sinir, kapasite=100000, epoch=10000, uyelik_auc=1)
        if fn(ust) != ust:
            return False
        for kayit in [
            None, [], dict(K, ek=1), dict(K, id=""), dict(K, id="a b"), dict(K, id="a" * 65), dict(K, id=None),
            dict(K, kapasite=True), dict(K, kapasite=1.5), dict(K, kapasite="20"), dict(K, kapasite=0),
            dict(K, kapasite=-1), dict(K, kapasite=100001), dict(K, kapasite=None),
            dict(K, epoch=True), dict(K, epoch=1.5), dict(K, epoch="10"), dict(K, epoch=0),
            dict(K, epoch=-1), dict(K, epoch=10001), dict(K, epoch=None),
            dict(K, egitim_dogrulugu=True), dict(K, egitim_dogrulugu="0.9"), dict(K, egitim_dogrulugu=float("nan")),
            dict(K, egitim_dogrulugu=-0.1), dict(K, egitim_dogrulugu=1.1),
            dict(K, test_dogrulugu=True), dict(K, test_dogrulugu=float("inf")), dict(K, test_dogrulugu=-0.1), dict(K, test_dogrulugu=1.1),
            dict(K, uyelik_auc=True), dict(K, uyelik_auc="0.75"), dict(K, uyelik_auc=float("nan")),
            dict(K, uyelik_auc=-0.1), dict(K, uyelik_auc=1.1),
        ]:
            try:
                fn(kayit)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(deney_kaydi_dogrula), "deney şeması, sayı türleri, sınırlar ve kopya korunmalı")
def m_kapasite(kayit):
    return deney_kaydi_dogrula(dict(kayit, kapasite=0))
def m_epoch(kayit):
    return deney_kaydi_dogrula(dict(kayit, epoch=0))
def m_auc(kayit):
    return deney_kaydi_dogrula(dict(kayit, uyelik_auc=2))
for ad, mutant in [("kapasiteyi silen", m_kapasite), ("epochu silen", m_epoch), ("AUC sınırını bozan", m_auc)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def deney_kaydi_dogrula(kayit):
    import math
    import re
    if not isinstance(kayit, dict):
        raise ValueError("kayıt sözlük olmalı")
    if set(kayit) != {"id", "kapasite", "epoch", "egitim_dogrulugu", "test_dogrulugu", "uyelik_auc"}:
        raise ValueError("kayıt şeması geçersiz")
    if not isinstance(kayit["id"], str):
        raise ValueError("kimlik string olmalı")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
        raise ValueError("kimlik geçersiz")
    for alan, ust in (("kapasite", 100000), ("epoch", 10000)):
        deger = kayit[alan]
        if isinstance(deger, bool) or not isinstance(deger, int):
            raise ValueError(alan + " tam sayı olmalı")
        if deger < 1 or deger > ust:
            raise ValueError(alan + " aralık dışında")
    for alan in ("egitim_dogrulugu", "test_dogrulugu", "uyelik_auc"):
        deger = kayit[alan]
        if isinstance(deger, bool) or not isinstance(deger, (int, float)):
            raise ValueError(alan + " sayı olmalı")
        if not math.isfinite(deger):
            raise ValueError(alan + " sonlu olmalı")
        if deger < 0 or deger > 1:
            raise ValueError(alan + " aralık dışında")
    return dict(kayit)

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    for kayit in json_yukle("veri/deney_kayitlari.json"):
        print(deney_kaydi_dogrula(kayit))
```

```hint
Tam sayı alanlarında bool değerlerini de reddet. Ölçümlerde tür, sonluluk ve aralık kontrollerini ayrı uygula.
```
:::

::: gorev 2 · Genelleme açığını kapasite ve epochla karşılaştır
`genelleme_raporu(kayitlar)` işlevini yaz. Kayıtlar ilk görevdeki şemayı taşıyan boş olmayan listedir ve kimlikler yinelenemez. Geçersiz veride `ValueError` yükselt.

Her kayıt için `{"id":D,"kapasite":N,"epoch":N,"genelleme_acigi":X,"uyelik_auc":X}` üret. Açık eğitim eksi test doğruluğudur; altı ondalık basamağa yuvarlanır ve negatif değer korunur. Satırları kapasite, epoch ve kimlik artan sırala. En yüksek ham açığı, eşitlikte en yüksek ham AUC'yi, hâlâ eşitlikte alfabetik kimliği seç. `{"satirlar":[...],"en_yuksek_acik":D}` döndür ve girdiyi değiştirme.

```starter
def genelleme_raporu(kayitlar):
    import math
    import re
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar boş olmayan liste olmalı")
    idler = set()
    for x in kayitlar:
        if not isinstance(x, dict) or set(x) != {"id", "kapasite", "epoch", "egitim_dogrulugu", "test_dogrulugu", "uyelik_auc"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(x["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", x["id"]):
            raise ValueError("kimlik geçersiz")
        if x["id"] in idler:
            raise ValueError("kimlik yinelenemez")
        for alan, ust in (("kapasite", 100000), ("epoch", 10000)):
            if isinstance(x[alan], bool) or not isinstance(x[alan], int):
                raise ValueError(alan + " tam sayı olmalı")
            if x[alan] < 1 or x[alan] > ust:
                raise ValueError(alan + " aralık dışında")
        for alan in ("egitim_dogrulugu", "test_dogrulugu", "uyelik_auc"):
            if isinstance(x[alan], bool) or not isinstance(x[alan], (int, float)):
                raise ValueError(alan + " sayı olmalı")
            if not math.isfinite(x[alan]) or x[alan] < 0 or x[alan] > 1:
                raise ValueError(alan + " geçersiz")
        idler.add(x["id"])
    satirlar = []
    for x in sorted(kayitlar, key=lambda x: (x["kapasite"], x["epoch"], x["id"])):
        # KUSURLU BAŞLANGIÇ KODU: açığın yönünü ters hesaplıyor.
        acik = x["test_dogrulugu"] - x["egitim_dogrulugu"]
        satirlar.append({"id": x["id"], "kapasite": x["kapasite"], "epoch": x["epoch"], "genelleme_acigi": round(acik, 6), "uyelik_auc": round(x["uyelik_auc"], 6), "_acik": acik, "_auc": x["uyelik_auc"]})
    secilen = min(satirlar, key=lambda x: (-x["_acik"], -x["_auc"], x["id"]))["id"]
    for satir in satirlar:
        del satir["_acik"]
        del satir["_auc"]
    return {"satirlar": satirlar, "en_yuksek_acik": secilen}

from ai_guvence_veri import json_yukle
print(genelleme_raporu(json_yukle("veri/deney_kayitlari.json")))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-18")
```

```test
import copy
K = [
    {"id": "c", "kapasite": 20, "epoch": 20, "egitim_dogrulugu": 0.95, "test_dogrulugu": 0.7, "uyelik_auc": 0.8},
    {"id": "a", "kapasite": 10, "epoch": 10, "egitim_dogrulugu": 0.8, "test_dogrulugu": 0.7, "uyelik_auc": 0.6},
    {"id": "b", "kapasite": 20, "epoch": 10, "egitim_dogrulugu": 0.9, "test_dogrulugu": 0.65, "uyelik_auc": 0.75},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        sonuc = fn(K)
        if K != once or sonuc["en_yuksek_acik"] != "c" or [x["id"] for x in sonuc["satirlar"]] != ["a", "b", "c"]:
            return False
        if sonuc["satirlar"][1] != {"id": "b", "kapasite": 20, "epoch": 10, "genelleme_acigi": 0.25, "uyelik_auc": 0.75}:
            return False
        negatif = fn([dict(K[0], id="n", egitim_dogrulugu=0.5, test_dogrulugu=0.8)])
        if negatif["satirlar"][0]["genelleme_acigi"] != -0.3 or negatif["en_yuksek_acik"] != "n":
            return False
        yuvarla = fn([dict(K[0], id="y", egitim_dogrulugu=0.7, test_dogrulugu=0.3666667, uyelik_auc=0.6666667)])
        if yuvarla["satirlar"][0]["genelleme_acigi"] != 0.333333 or yuvarla["satirlar"][0]["uyelik_auc"] != 0.666667:
            return False
        sinir = fn([
            dict(K[0], id="a" * 64, kapasite=1, epoch=1, egitim_dogrulugu=0, test_dogrulugu=1, uyelik_auc=0),
            dict(K[0], id="ust", kapasite=100000, epoch=10000, egitim_dogrulugu=1, test_dogrulugu=0, uyelik_auc=1),
        ])
        if len(sinir["satirlar"]) != 2:
            return False
        for kayitlar in [
            None, {}, tuple(K), [], [None], [dict(K[0], ek=1)], [K[0], K[0]],
            [dict(K[0], id=123)], [dict(K[0], id="a b")], [dict(K[0], id="a" * 65)], [dict(K[0], kapasite=True)], [dict(K[0], kapasite=0)], [dict(K[0], kapasite=100001)],
            [dict(K[0], epoch=1.5)], [dict(K[0], epoch=0)], [dict(K[0], epoch=10001)], [dict(K[0], egitim_dogrulugu=True)], [dict(K[0], egitim_dogrulugu="0.9")],
            [dict(K[0], egitim_dogrulugu=float("nan"))], [dict(K[0], test_dogrulugu=-0.1)],
            [dict(K[0], test_dogrulugu=1.1)], [dict(K[0], uyelik_auc=float("inf"))], [dict(K[0], uyelik_auc=1.1)],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(genelleme_raporu), "açık hesabı, kapasite-epoch sıralaması ve ham seçim korunmalı")
def m_egitim(kayitlar):
    return genelleme_raporu([dict(x, egitim_dogrulugu=0) for x in kayitlar])
def m_test(kayitlar):
    return genelleme_raporu([dict(x, test_dogrulugu=1) for x in kayitlar])
def m_kapasite(kayitlar):
    return genelleme_raporu([dict(x, kapasite=1) for x in kayitlar])
for ad, mutant in [("eğitim doğruluğunu silen", m_egitim), ("test doğruluğunu silen", m_test), ("kapasiteyi birleştiren", m_kapasite)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def genelleme_raporu(kayitlar):
    import math
    import re
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar boş olmayan liste olmalı")
    idler = set()
    for x in kayitlar:
        if not isinstance(x, dict) or set(x) != {"id", "kapasite", "epoch", "egitim_dogrulugu", "test_dogrulugu", "uyelik_auc"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(x["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", x["id"]):
            raise ValueError("kimlik geçersiz")
        if x["id"] in idler:
            raise ValueError("kimlik yinelenemez")
        for alan, ust in (("kapasite", 100000), ("epoch", 10000)):
            if isinstance(x[alan], bool) or not isinstance(x[alan], int):
                raise ValueError(alan + " tam sayı olmalı")
            if x[alan] < 1 or x[alan] > ust:
                raise ValueError(alan + " aralık dışında")
        for alan in ("egitim_dogrulugu", "test_dogrulugu", "uyelik_auc"):
            if isinstance(x[alan], bool) or not isinstance(x[alan], (int, float)):
                raise ValueError(alan + " sayı olmalı")
            if not math.isfinite(x[alan]) or x[alan] < 0 or x[alan] > 1:
                raise ValueError(alan + " geçersiz")
        idler.add(x["id"])
    satirlar = []
    for x in sorted(kayitlar, key=lambda x: (x["kapasite"], x["epoch"], x["id"])):
        acik = x["egitim_dogrulugu"] - x["test_dogrulugu"]
        satirlar.append({"id": x["id"], "kapasite": x["kapasite"], "epoch": x["epoch"], "genelleme_acigi": round(acik, 6), "uyelik_auc": round(x["uyelik_auc"], 6), "_acik": acik, "_auc": x["uyelik_auc"]})
    secilen = min(satirlar, key=lambda x: (-x["_acik"], -x["_auc"], x["id"]))["id"]
    for satir in satirlar:
        del satir["_acik"]
        del satir["_auc"]
    return {"satirlar": satirlar, "en_yuksek_acik": secilen}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    print(genelleme_raporu(json_yukle("veri/deney_kayitlari.json")))
```

```hint
Sıralanmış kopyalar üzerinde açığı hesapla. Seçim için ham açık ve AUC değerlerini geçici alanlarda tut.
```
:::

::: gorev 3 · Genelleme açığı ve AUC riskini birlikte değerlendir
`gizlilik_risk_karsilastir(kayitlar, acik_esik, auc_esik)` işlevini yaz. Kayıtlar ilk görevdeki şemayı taşır, liste boş olamaz ve kimlikler yinelenemez. İki eşik bool olmayan sonlu sayıdır; açık eşiği `[-1,1]`, AUC eşiği `[0,1]` aralığındadır. Geçersiz veride `ValueError` yükselt.

Her kayıt için `{"id":D,"kapasite":N,"epoch":N,"genelleme_acigi":X,"uyelik_auc":X,"riskli":BOOL}` üret ve kimliğe göre sırala. Risk için ham açık ve ham AUC kendi eşiklerine eşit veya büyük olmalıdır. Riskli kayıtlardan en yüksek ham AUC, eşitlikte en yüksek ham açık, sonra alfabetik kimlik seçilir. `{"satirlar":[...],"riskli_sayi":N,"secilen":D veya None}` döndür. Ölçümleri altı ondalık basamağa yuvarla ve girdiyi değiştirme.

```starter
def gizlilik_risk_karsilastir(kayitlar, acik_esik, auc_esik):
    import math
    import re
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar boş olmayan liste olmalı")
    for esik, alt in ((acik_esik, -1), (auc_esik, 0)):
        if isinstance(esik, bool) or not isinstance(esik, (int, float)):
            raise ValueError("eşik sayı olmalı")
        if not math.isfinite(esik) or esik < alt or esik > 1:
            raise ValueError("eşik geçersiz")
    idler = set()
    for x in kayitlar:
        if not isinstance(x, dict) or set(x) != {"id", "kapasite", "epoch", "egitim_dogrulugu", "test_dogrulugu", "uyelik_auc"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(x["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", x["id"]):
            raise ValueError("kimlik geçersiz")
        if x["id"] in idler:
            raise ValueError("kimlik yinelenemez")
        for alan, ust in (("kapasite", 100000), ("epoch", 10000)):
            if isinstance(x[alan], bool) or not isinstance(x[alan], int) or x[alan] < 1 or x[alan] > ust:
                raise ValueError(alan + " geçersiz")
        for alan in ("egitim_dogrulugu", "test_dogrulugu", "uyelik_auc"):
            if isinstance(x[alan], bool) or not isinstance(x[alan], (int, float)):
                raise ValueError(alan + " sayı olmalı")
            if not math.isfinite(x[alan]) or x[alan] < 0 or x[alan] > 1:
                raise ValueError(alan + " geçersiz")
        idler.add(x["id"])
    # KUSURLU BAŞLANGIÇ KODU: iki risk koşulunu birlikte aramak yerine herhangi birini yeterli sayıyor.
    satirlar = []
    for x in sorted(kayitlar, key=lambda x: x["id"]):
        acik = x["egitim_dogrulugu"] - x["test_dogrulugu"]
        auc = x["uyelik_auc"]
        satirlar.append({"id": x["id"], "kapasite": x["kapasite"], "epoch": x["epoch"], "genelleme_acigi": round(acik, 6), "uyelik_auc": round(auc, 6), "riskli": acik >= acik_esik or auc >= auc_esik, "_acik": acik, "_auc": auc})
    riskli = [x for x in satirlar if x["riskli"]]
    secilen = min(riskli, key=lambda x: (-x["_auc"], -x["_acik"], x["id"]))["id"] if riskli else None
    for satir in satirlar:
        del satir["_acik"]
        del satir["_auc"]
    return {"satirlar": satirlar, "riskli_sayi": len(riskli), "secilen": secilen}

from ai_guvence_veri import json_yukle
esikler = json_yukle("veri/esikler.json")
print(gizlilik_risk_karsilastir(json_yukle("veri/deney_kayitlari.json"), **esikler))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-18")
```

```test
import copy
K = [
    {"id": "c", "kapasite": 20, "epoch": 20, "egitim_dogrulugu": 0.95, "test_dogrulugu": 0.7, "uyelik_auc": 0.8},
    {"id": "a", "kapasite": 10, "epoch": 10, "egitim_dogrulugu": 0.8, "test_dogrulugu": 0.7, "uyelik_auc": 0.6},
    {"id": "b", "kapasite": 20, "epoch": 10, "egitim_dogrulugu": 0.9, "test_dogrulugu": 0.65, "uyelik_auc": 0.75},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        sonuc = fn(K, 0.2, 0.7)
        if K != once or sonuc["secilen"] != "c" or sonuc["riskli_sayi"] != 2:
            return False
        if [x["id"] for x in sonuc["satirlar"]] != ["a", "b", "c"] or [x["riskli"] for x in sonuc["satirlar"]] != [False, True, True]:
            return False
        if fn(K, 0.25, 0.8)["secilen"] != "c" or fn(K, 1, 1)["secilen"] is not None:
            return False
        negatif = fn([dict(K[0], id="n", egitim_dogrulugu=0.4, test_dogrulugu=0.8, uyelik_auc=0.5)], -0.4, 0.5)
        if negatif["satirlar"][0]["genelleme_acigi"] != -0.4 or negatif["secilen"] != "n":
            return False
        yuvarla = fn([dict(K[0], id="y", egitim_dogrulugu=0.7, test_dogrulugu=0.3666667, uyelik_auc=0.6666667)], 0, 0)
        if yuvarla["satirlar"][0]["genelleme_acigi"] != 0.333333 or yuvarla["satirlar"][0]["uyelik_auc"] != 0.666667:
            return False
        tek_kosul = fn([dict(K[0], id="tek", egitim_dogrulugu=0.9, test_dogrulugu=0.7, uyelik_auc=0.6)], 0.2, 0.7)
        if tek_kosul["riskli_sayi"] != 0 or tek_kosul["secilen"] is not None:
            return False
        if fn([dict(K[0], id="az", egitim_dogrulugu=0.75, test_dogrulugu=0.7, uyelik_auc=0.8)], 0.2, 0.7)["riskli_sayi"] != 0:
            return False
        if fn([dict(K[0], id="d1", egitim_dogrulugu=0.9, test_dogrulugu=0.7, uyelik_auc=0.8), dict(K[0], id="d2", egitim_dogrulugu=0.95, test_dogrulugu=0.7, uyelik_auc=0.8)], 0.2, 0.7)["secilen"] != "d2":
            return False
        sinir = fn([
            dict(K[0], id="a" * 64, kapasite=1, epoch=1, egitim_dogrulugu=0, test_dogrulugu=1, uyelik_auc=0),
            dict(K[0], id="ust", kapasite=100000, epoch=10000, egitim_dogrulugu=1, test_dogrulugu=0, uyelik_auc=1),
        ], -1, 0)
        if sinir["riskli_sayi"] != 2:
            return False
        for kayitlar, ae, ue in [
            (None, 0.2, 0.7), (K, None, 0.7), (K, 0.2, None), ({}, 0.2, 0.7), (tuple(K), 0.2, 0.7), ([], 0.2, 0.7),
            ([None], 0.2, 0.7), ([dict(K[0], ek=1)], 0.2, 0.7), ([K[0], K[0]], 0.2, 0.7),
            ([dict(K[0], id=123)], 0.2, 0.7), ([dict(K[0], id="a b")], 0.2, 0.7), ([dict(K[0], id="a" * 65)], 0.2, 0.7), ([dict(K[0], kapasite=0)], 0.2, 0.7), ([dict(K[0], kapasite=100001)], 0.2, 0.7), ([dict(K[0], kapasite=1.5)], 0.2, 0.7), ([dict(K[0], epoch=True)], 0.2, 0.7), ([dict(K[0], epoch=10001)], 0.2, 0.7),
            ([dict(K[0], egitim_dogrulugu=True)], 0.2, 0.7), ([dict(K[0], test_dogrulugu="0.7")], 0.2, 0.7), ([dict(K[0], uyelik_auc=True)], 0.2, 0.7),
            ([dict(K[0], egitim_dogrulugu=float("nan"))], 0.2, 0.7), ([dict(K[0], test_dogrulugu=1.1)], 0.2, 0.7),
            ([dict(K[0], uyelik_auc=-0.1)], 0.2, 0.7),
            (K, True, 0.7), (K, "0.2", 0.7), (K, float("nan"), 0.7), (K, float("inf"), 0.7), (K, -1.1, 0.7), (K, 1.1, 0.7),
            (K, 0.2, True), (K, 0.2, "0.7"), (K, 0.2, float("nan")), (K, 0.2, float("inf")), (K, 0.2, -0.1), (K, 0.2, 1.1),
        ]:
            try:
                fn(kayitlar, ae, ue)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(gizlilik_risk_karsilastir), "iki risk koşulu, eşik sınırları ve seçim korunmalı")
def m_acik(kayitlar, ae, ue):
    return gizlilik_risk_karsilastir([dict(x, test_dogrulugu=1) for x in kayitlar], ae, ue)
def m_auc(kayitlar, ae, ue):
    return gizlilik_risk_karsilastir([dict(x, uyelik_auc=0) for x in kayitlar], ae, ue)
def m_esik(kayitlar, ae, ue):
    return gizlilik_risk_karsilastir(kayitlar, 1, 1)
for ad, mutant in [("açığı silen", m_acik), ("AUC'yi silen", m_auc), ("eşikleri değiştiren", m_esik)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def gizlilik_risk_karsilastir(kayitlar, acik_esik, auc_esik):
    import math
    import re
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar boş olmayan liste olmalı")
    for esik, alt in ((acik_esik, -1), (auc_esik, 0)):
        if isinstance(esik, bool) or not isinstance(esik, (int, float)):
            raise ValueError("eşik sayı olmalı")
        if not math.isfinite(esik) or esik < alt or esik > 1:
            raise ValueError("eşik geçersiz")
    idler = set()
    for x in kayitlar:
        if not isinstance(x, dict) or set(x) != {"id", "kapasite", "epoch", "egitim_dogrulugu", "test_dogrulugu", "uyelik_auc"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(x["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", x["id"]):
            raise ValueError("kimlik geçersiz")
        if x["id"] in idler:
            raise ValueError("kimlik yinelenemez")
        for alan, ust in (("kapasite", 100000), ("epoch", 10000)):
            if isinstance(x[alan], bool) or not isinstance(x[alan], int) or x[alan] < 1 or x[alan] > ust:
                raise ValueError(alan + " geçersiz")
        for alan in ("egitim_dogrulugu", "test_dogrulugu", "uyelik_auc"):
            if isinstance(x[alan], bool) or not isinstance(x[alan], (int, float)):
                raise ValueError(alan + " sayı olmalı")
            if not math.isfinite(x[alan]) or x[alan] < 0 or x[alan] > 1:
                raise ValueError(alan + " geçersiz")
        idler.add(x["id"])
    satirlar = []
    for x in sorted(kayitlar, key=lambda x: x["id"]):
        acik = x["egitim_dogrulugu"] - x["test_dogrulugu"]
        auc = x["uyelik_auc"]
        satirlar.append({"id": x["id"], "kapasite": x["kapasite"], "epoch": x["epoch"], "genelleme_acigi": round(acik, 6), "uyelik_auc": round(auc, 6), "riskli": acik >= acik_esik and auc >= auc_esik, "_acik": acik, "_auc": auc})
    riskli = [x for x in satirlar if x["riskli"]]
    secilen = min(riskli, key=lambda x: (-x["_auc"], -x["_acik"], x["id"]))["id"] if riskli else None
    for satir in satirlar:
        del satir["_acik"]
        del satir["_auc"]
    return {"satirlar": satirlar, "riskli_sayi": len(riskli), "secilen": secilen}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    esikler = json_yukle("veri/esikler.json")
    print(gizlilik_risk_karsilastir(json_yukle("veri/deney_kayitlari.json"), **esikler))
```

```hint
İki eşik koşulunu ayrı yaz ve `and` ile birleştir. Riskli satır sayısını seçimden bağımsız hesapla.
```
:::


::: anlat Canlı CPU deneyi ve düzenlenebilir sentetik ayar
Önce [sentetik ayar dosyasını](/data/ai-guvence-18-ayarlar.txt) açıp seed, ornek, sigma alanlarını incele. Bu JSON örneği kaydedilmiş model çıktısı değildir. Yeni görev gerçek küçük MLP'yi torch autograd ile CPU'da eğitir; ağ/model indirme yoktur.

Çalıştır ilk kullanımda örneği `PAFTA_DATA/calisma/ai-guvence-18/ayarlar.json` konumuna yalnız yoksa kopyalar, tam yolu ekranda yazar. Göreli PAFTA_DATA proje köküne göre çözülür. Öğrenci bu kalıcı JSON'u metin düzenleyicide değiştirebilir (seed:0..2**30-1, ornek:8..32, sigma:0.5..8); yeniden Çalıştır düzenlemeyi korur. Tarayıcıdaki örnek salt okunur indirme bağlantısıdır; kalıcı kopyayı kendi editöründe aç. Kontrol bağımsız test ayarı kullanır, örneği değiştirmek beklenen cevabı değiştirmez.

Yalnız sentetik veriler kullanılır. Saldırının kazanması veya gizlilik iddiasının desteklenmesi PASS şartı değildir. Küçük deney sohbet modelinin gizliliğine genellenemez. DP eğitimli deneylerde açık tohum, ham veriler ve eğitim izleri öğretim içindir; bu yayınlar özel veri için DP garantisi taşımaz. Bütçe yalnız sabit boyutlu replace-one tam batch Gaussian ağırlık mekanizması içindir, ham izlere değil. Güvenli üretim RNG/accountant denetimi yapılmaz.

Kaynaklar: [Yeom vd. 2018 — Privacy Risk in Machine Learning: Analyzing the Connection to Overfitting (arXiv:1709.01604)](https://arxiv.org/abs/1709.01604), [Carlini vd. 2019 — The Secret Sharer: Evaluating and Testing Unintended Memorization (arXiv:1802.08232)](https://arxiv.org/abs/1802.08232).
:::

::: gorev Gerçek deney · CPU gizlilik ölçümü 18
`olc(train_acc,test_acc,a)` altı ondalıklı `acik=train_acc-test_acc`, `auc=a` ve `risk` döndürsün. Risk ham açık>=0.1 VE ham AUC>=0.65 koşuludur. Aynı veri/tohum/mimariyle 3 ve 35 epoch gerçek eğitim ölçülür. İlişki gözlemlenir; nedensellik veya her model için monoton artış iddiası yok.

Girdileri değiştirme. Çalıştır gerçek öğrenci dosyasıyla sonuç ve kanıt yolunu gösterir; Kontrol farklı veri ve tohumlarda bağımsız hesap, boş/sabit/yanlış çözüm denetimi yapar. torch yokluğu PASS değildir.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 180
```

```starter
import ai_lab
def olc(train_acc, test_acc, a):
    return {}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_17_20 as deney
    deney.goster(18,olc)
```

```test
import ai_lab
import ast
YASAK = ("ref17", "ref18", "ref19clip", "ref19budget", "ref20", "kanit_yaz")
sorunlar = ai_lab.kod_denetimi(src, yasak=YASAK)
for dugum in ast.walk(ast.parse(src)):
    if isinstance(dugum, ast.ImportFrom):
        if any(ad.name in YASAK or ad.name == "*" for ad in dugum.names):
            sorunlar.append("referans veya kanıt yazıcısı içe aktarılamaz")
if sorunlar:
    ok(False, "Kendi ölçüm işlevini yaz: " + "; ".join(sorunlar))
    stop()
checks = []
def kontrol(deger, mesaj):
    checks.append(bool(deger))
    ok(deger, mesaj)
from sandbox import ai_gercek_ai_guvence_17_20 as deney
import tempfile
from pathlib import Path
kontrol(deney.sozlesme(18,olc),'Görülmemiş sınırlar, eşitlik ve yanlış ölçüm reddi')
kontrol(olc(2/3, 1/3, 2/3) == {'acik': 0.333333, 'auc': 0.666667, 'risk': True} and olc(0.2, 0.1, 0.65) == {'acik': 0.1, 'auc': 0.65, 'risk': True} and olc(0.19, 0.1, 0.8)['risk'] is False and olc(0.8, 0.6, 0.649)['risk'] is False, '6 basamak yuvarlama ve bağımsız >=0.1 / >=0.65 sınırları')
with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp)/'ayar.json'
    p.write_text('{"seed": 8318, "ornek": 13, "sigma": 1.75}',encoding='utf-8')
    r=deney.deney(18,olc,path=p)
    for name,value in r['kontroller'].items(): kontrol(value,name)
ns={}
exec('def olc(train_acc, test_acc, a):\n    return dict(acik=round(test_acc-train_acc,6),auc=round(a,6),risk=test_acc-train_acc>=.1 and a>=.65)\n',ns)
kontrol(not deney.sozlesme(18,ns['olc']),'Mutant 1 reddedilir')
ns={}
exec('def olc(train_acc, test_acc, a):\n    return dict(acik=round(train_acc-test_acc,6),auc=round(a,6),risk=train_acc-test_acc>=.1 or a>=.65)\n',ns)
kontrol(not deney.sozlesme(18,ns['olc']),'Mutant 2 reddedilir')
ns={}
exec('def olc(train_acc, test_acc, a):\n    return dict(acik=round(train_acc-test_acc,6),auc=round(a,6),risk=train_acc-test_acc>=.1 and a>.65)\n',ns)
kontrol(not deney.sozlesme(18,ns['olc']),'Mutant 3 reddedilir')
ai_lab.kanit_yaz('guvence-18-cpu',dict(r,kabul=all(checks)))

```

```solution
import ai_lab
def olc(train_acc, test_acc, a):
    return dict(acik=round(train_acc-test_acc,6),auc=round(a,6),risk=train_acc-test_acc>=.1 and a>=.65)

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_17_20 as deney
    deney.goster(18,olc)
```

```hint
Ham eşik koşulunu yuvarlamadan uygula. AUC eşitlikte yarım katkı verir. Gürültüyü başarı garantisi olarak yorumlama.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Genelleme açığı neden gizlilik sinyalidir? (35 sn).** "Model eğitim kümesinde `%98`, test kümesinde `%75` doğruluk veriyorsa eğitim örneklerine daha düşük kayıp ve daha yüksek güven atıyor demektir; saldırgan tam da bu kayıp farkını üyelik çıkarımına çevirir."
2. **Yeterli ama zorunlu olmayan koşul (30 sn).** "Yüksek `egitim - test` açığı ortalama üyelik `AUC`'sini yukarı çeker; ancak genelleme açığının küçük olması nadir kuyruk örneklerinin ezberlenmediğini garanti etmez."
3. **Ham farkla eşik kararı (30 sn).** "Yuvarlanmış rapor sayıları sınırda yanıltabilir; hem genelleme açığı hem üyelik `AUC` eşiği ham kayan nokta değerleri üzerinden birlikte denetlenir."
4. **Soru (25 sn).** "Erken durdurma (`early stopping`) ve ağırlık çürümesi (`weight decay`) genelleme açığını daraltırken neden formel bir diferansiyel gizlilik ($\varepsilon$) üst sınırı yerine geçmez?"
:::
