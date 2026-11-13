---
id: ai-guvence-16
title: Gizlilik Tehdit Modeli ve Bilgi Sızdıran Kanıtlar
summary: Varlık, çıktı kanalı ve saldırgan bilgisini tanımla; üyelik çıkarımı sinyalini taban doğrulukla karşılaştır.
esleme: ai-guvence-17, ai-guvence-18, ai-guvence-39
timeout: 45
---

::: anlat Gizlilik riski varlık ve erişimle tanımlanır

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Üyelik saldırısı, görünür model çıktısından eğitim üyeliği tahmin eder | İlk üç görev görünür sentetik JSON; final gerçek autograd ile eğitilen küçük PyTorch shadow/target sınıflandırıcıları | Sentetik etiketler gerçek kişisel veri değildir; sohbet modeli gizliliği ölçülmez |
| TPR-FPR ve doğruluk tabanı farklı sorulara cevap verir | Ayrı shadow verisinden eşik; üç hedef deneyinin olasılıkları ve ölçümleri | Pozitif avantaj veya kanıt bayrağı zorunlu değildir; genel gizlilik garantisi verilmez |

> [!NOT]
> `veri/gizlilik.json` elle hazırlanmış sentetik çalışma verisidir. İlk üç görev aynı dosyayı okur; ilk Çalıştır ham dosyayı gösterir. Setup her Run/Check için yeni geçici veri/ kopyası kurar, bu kopyanın değişiklikleri kalıcı değildir. Kaynağı haricî editörde veya yüklenen sözlüğü kodda değiştirip Çalıştır deneyebilirsin. Finalin `calisma/ai-guvence-16/gizlilik.json` ayarı ayrı ve kalıcıdır; mevcut dosya üzerine yazılmaz. Gizli test bu dosyalardan bağımsız seed kullanır. Yeni indirme yapılmaz.

Tehdit modelinde korunacak varlıklar, modelin görünür çıktı kanalları ve saldırganın önceden bildikleri açıkça yazılır. Metin, olasılık veya embedding çıktısı aynı bilgiyi açığa vurmayabilir; mimari bilmek ile örnek veriye sahip olmak da aynı varsayım değildir.

İlk üç görevde model veya sorgu API'si çalıştırılmaz; ölçümler elle hazırlanmış sentetik örneklerdir. Finalde sentetik rastgele veriyle küçük sınıflandırıcılar gerçekten eğitilir ve gerçek model olasılıkları ölçülür. Gerçek kişisel veri kullanılmaz. Amaç tehdit varsayımlarını ve kanıtları denetlenebilir biçimde kaydetmektir.
:::

::: anlat Doğruluk tek başına bilgi sızıntısı kanıtı değildir

Önce gizlilik.json dosyasının tehdit_modeli alanını aç. Varlık neyin korunacağını, çıktı kanalı saldırganın neyi görebildiğini, saldırgan bilgisi ise hangi önbilgiye sahip olduğunu anlatır. Bunlar aynı şey değildir. Model mimarisini bilmek eğitim örneklerini bildiğini göstermez; olasılık çıktısına erişmek de gizli parametre dosyasını okuyabildiğin anlamına gelmez. Birinci görev bu ayrımı dar izin kümeleriyle kaydeder. Alanı sessizce atmak yerine bilinmeyen alanı reddetmek, varsayımın raporda kaybolmasını önler. Liste sırası modelin içeriğini değiştirmediği için çıktı alfabetik sıralanır; ancak kaynak listeyi yerinde sıralamak başka bir adımın ham kaydını bozabilir. Bağımsız kopya bu yüzden sözleşmenin parçasıdır.

İkinci görev aynı dosyanın uyelik_kayitlari alanını kullanır. uye gerçek deneyin değerlendirme etiketini, tahmin_uye ise saldırının kararını temsil eder. İlk üç görevde her ikisi de elle yazılmıştır. Dört olası sonucu ayrı say: gerçek üye ve tahmin üye TP, gerçek üye olmayan ve tahmin üye FP, ikisi de hayır TN, gerçek üye olup kaçırılan FN olur. Sadece doğru tahmin sayısını toplamak yanlış alarm oranını gizler. Bu dersin avantajı TPR eksi FPR'dir; negatif avantaj da geçerli bir sonuçtur. Üyelerin tamamını üye olmayan sayan bir saldırı düşük TPR verebilir, ama dengesiz örnekte yüksek doğruluk gösterebilir.

Payda sıfırsa bu küçük görevin oranı `0.0` kabul edilir. Bu seçim ölçümün evrensel istatistik kuralı değildir; üyeler veya üye olmayanlar hiç yoksa o oran için yeterli gözlem bulunmadığını ayrıca not etmek gerekir. Gerçek final dengeli üye/üyeolmayan örnekler kullanır, dolayısıyla çoğunluk tabanı `0.5` olur. Üçüncü görev dosyanın deney_sonuclari alanında daha farklı tabanları da karşılaştırır. Aynı doğruluk değerinin farklı sınıf dağılımlarında farklı anlamı olabileceğini görmek için tabanı değiştirip Çalıştır. Tabana eşit doğruluk kanıt sayılmaz; avantajın eşik değerine eşit olması ise yeterlidir.

Üçüncü görevde aynı deney adındaki tekrarların ortalamaları alınır. Karar, ekranda yuvarlanmış sayılarla verilmez. Örneğin ham avantaj eşikten az ama altı ondalık gösterimde eşik gibi görünüyorsa kanıt bayrağı yine False olmalıdır. Kanıtlı adaylar ham avantaj, sonra ham doğruluk ve sonra alfabetik adla seçilir. Üçüncü eşitlik kuralı raporu girdi sırasından bağımsız yapar. Kazananı seçmeden önce ortalamayı yuvarlamak veya doğruluğu tabana büyük-eşit ile kıyaslamak anlamlı biçimde yanlış sonuç verebilir. Uygun aday yoksa None dönmek normaldir; yüksek bir sayı çıkarmak için zorla seçim yapılmaz.

Finalde her tekrarda ayrı bir shadow model ve ayrı bir target model kurulur. Özellikler 24 boyutlu rastgele sayılar, etiketler rastgele iki sınıftır. Bu kurgu gerçek müşteri verisini veya bir dil modelinin eğitim kümesini temsil etmez; küçük bir sınıflandırıcının eğitim örneklerine aşırı uyumunu kontrollü incelemeyi sağlar. İki katmanlı ağ gerçek PyTorch parametreleri, cross-entropy, backward ve Adam ile 100 adım eğitilir. Olasılıklar gerçek ileri hesapta softmax ile elde edilir. Bu nedenle üyelik kayıtlarının kaynağı gerçek model çalışmasıdır; fakat alttaki özellik ve etiketlerin kökeni sentetiktir.

Saldırgan için görünür skor örneğin gerçek sınıfına verilen olasılıktır; örneğin etiketini bildiği varsayımı bu nedenle önemlidir. Shadow modelin üye ve dış örnekleri üzerinde TPR-FPR'yi en büyük yapan eşik seçilir. Target modelin üyelik etiketleri bu eşiği ayarlamak için kullanılmaz; yalnız son ölçümü değerlendirmeye yarar. Aynı hedef etiketlerle eşik arayıp sonra başarıyı yine aynı örneklerde raporlamak değerlendirmeyi iyimserleştirirdi. Bu deney üç ayrı seed ile tekrarlanır; sonuçların değişmesi bulgudur. Pozitif avantaj, kanıt=True veya belirli bir başarı oranı kabul şartı değildir.

Ham eğitim loss izleri, logits, gerçek sınıf olasılıkları, örnek özellik/etiketleri, üyelik kararları, model parametre sayısı, ağırlık dosyası özeti, sürüm ve cihaz kanıtta bulunur. Shadow ve target kayıtları ayrı tutulduğu için eşiğin nereden geldiğini inceleyebilirsin. Eğitim süresi donanıma göre değişir ve test sabit milisaniye istemez. Kontrol kendi geçici ağırlık klasörlerini kapanınca temizler; ölçüm JSON'ları kalır. Çalıştır kendi deney klasöründeki ağırlıkları inceleme için korur. Bunlar öğrencinin diğer dosyaları veya kurulu modelleri değildir.

Bir saldırgan, yetkili bir laboratuvarda modelin güven skorlarından üyelik farkı arayabilir. Bu fark gerçek bir bireyin verisinin kesin olarak eğitimde bulunduğunu göstermez. Küçük örnek sayısı, veri dağılımı, rastgele etiketler ve eşik seçimi sonucu etkiler. Parametre erişimi, embedding tersine çevirme, gerçek kişisel kayıt çıkarma veya sohbet modelinden sır alma bu dersin deneyi değildir. Savunmayı değerlendirirken yalnız doğruluğun düşmesine değil yanlış alarm, üye yakalama oranı ve normal işlevin kalmasına da bakmak gerekir. Buradaki rapor bir inceleme sinyali üretir; tek başına gizlilik güvencesi veya hukuki hüküm değildir.

İlk üç görevdeki çalışma dosyası her seferinde geçici kopyadır. Finalin ayar dosyası ise Çalıştır çıktısında mutlak konumuyla gösterilen, uygulamanın veri dizinindeki ayrı kalıcı kopyadır. Aynı adlara rağmen bu iki dosyayı karıştırma. Kalıcı ayarda seed ve ornek alanlarını değiştirerek kendi deneyini tekrar çalıştırabilirsin; Kontrol ayrı geçici ayar üretir ve kendi sınamasını senin ayarına bağlamaz. Boş, sabit veya anlamlı yanlış çözüm; eksik bağımlılık; başarısız veya yarım deney geçmez. Çalıştır kabulfalse keşif kaydı, Kontrol bütün koşullar sağlanırsa kabul kaydı üretir. Yeni paket veya model indirilmez, kullanıcı sunucuları kapatılmaz.

Üyelik çıkarımında tahminler TP, FP, TN ve FN olarak sayılır. Üye doğru tahmin oranı ile üye olmayanların yanlış üye tahmin oranı arasındaki fark, bu derste avantaj olarak kullanılır. Paydası sıfır olan oran `0.0` kabul edilir.

Bir deneyin doğruluğu, sınıf dağılımından kaynaklanan taban doğrulukla karşılaştırılmalıdır. Kanıt bayrağı için avantaj eşiğe eşit veya büyük, doğruluk ise taban doğruluktan katı biçimde büyük olmalıdır. Bu ölçüm kesin sızıntı hükmü değil, ek inceleme gerektiren bir sinyaldir.
:::

::: tahmin Üyelik avantajı ve kanıt bayrağını tahmin et
Üç çıktı satırını yaz:

```python
print(round(0.75 - 0.25, 6))
print(round(2 / 3, 6))
print(0.4 >= 0.3 and 0.7 > 0.6)
```

???

```cikti
0.5
0.666667
True
```

İlk satır üyelik avantajını, ikinci satır doğruluğu, üçüncü satır avantaj ve taban koşullarının birlikte sağlanmasını gösterir.
:::

::: gorev 1 · Gizlilik tehdit modelini doğrula
`tehdit_modeli_dogrula(model)` işlevini yaz. Model tam olarak `id`, `varliklar`, `cikti_kanallari`, `saldirgan_bilgisi` alanlarını taşır. Kimlik 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren stringdir.

Üç alan da boş olmayan, yinelenmeyen string listeleridir. Varlıklar yalnız `egitim_verisi`, `model_parametreleri`, `kullanici_girdisi`; çıktılar yalnız `metin`, `olasilik`, `embedding`; saldırgan bilgisi yalnız `mimari`, `ornek_veri`, `sorgu_erisimi` içerebilir. Geçersiz veride `ValueError` yükselt. Aynı alanları, listeleri alfabetik sıralanmış bağımsız kopyalarla döndür ve girdiyi değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-16")
```

```starter
from ai_guvence_veri import json_yukle,metin_yukle

def tehdit_modeli_dogrula(model):
    # KUSURLU BAŞLANGIÇ KODU: dış sözlüğü kopyalar ama listeleri paylaşır ve izin kümelerini doğrulamaz.
    return dict(model)

v=json_yukle("veri/gizlilik.json")
print("Sentetik ham dosya:\n",metin_yukle("veri/gizlilik.json"))
print("Tehdit modeli:",tehdit_modeli_dogrula(v["tehdit_modeli"]))
```

```test
import copy
M = {"id": "gizlilik-1", "varliklar": ["kullanici_girdisi", "egitim_verisi"], "cikti_kanallari": ["olasilik", "metin"], "saldirgan_bilgisi": ["sorgu_erisimi", "mimari"]}
BEKLENEN = {"id": "gizlilik-1", "varliklar": ["egitim_verisi", "kullanici_girdisi"], "cikti_kanallari": ["metin", "olasilik"], "saldirgan_bilgisi": ["mimari", "sorgu_erisimi"]}
def sozlesme(fn):
    try:
        once = copy.deepcopy(M)
        sonuc = fn(M)
        if sonuc != BEKLENEN or M != once or any(sonuc[k] is M[k] for k in ("varliklar", "cikti_kanallari", "saldirgan_bilgisi")):
            return False
        sinir = {"id": "a" * 64, "varliklar": ["model_parametreleri"], "cikti_kanallari": ["embedding"], "saldirgan_bilgisi": ["ornek_veri"]}
        if fn(sinir) != sinir:
            return False
        tam = dict(sinir, varliklar=["egitim_verisi", "model_parametreleri", "kullanici_girdisi"])
        if fn(tam)["varliklar"] != ["egitim_verisi", "kullanici_girdisi", "model_parametreleri"]:
            return False
        for model in [
            None, [], dict(M, ek=1), dict(M, id=123), dict(M, id=""), dict(M, id="a b"), dict(M, id="a" * 65),
            dict(M, varliklar=[]), dict(M, varliklar=None), dict(M, varliklar={}), dict(M, varliklar=("egitim_verisi",)), dict(M, varliklar=["diger"]),
            dict(M, varliklar=["egitim_verisi", "egitim_verisi"]), dict(M, varliklar=[1]), dict(M, varliklar=[["egitim_verisi"]]),
            dict(M, cikti_kanallari=[]), dict(M, cikti_kanallari=None), dict(M, cikti_kanallari=["diger"]),
            dict(M, cikti_kanallari=["metin", "metin"]), dict(M, cikti_kanallari=[1]),
            dict(M, saldirgan_bilgisi=[]), dict(M, saldirgan_bilgisi=None), dict(M, saldirgan_bilgisi=["diger"]),
            dict(M, saldirgan_bilgisi=["mimari", "mimari"]), dict(M, saldirgan_bilgisi=[1]),
        ]:
            try:
                fn(model)
                return False
            except ValueError:
                pass
        for ad in ["_a","-a","éx","a\n"]:
            try:fn(dict(M,id=ad));return False
            except ValueError:pass
        return True
    except Exception:
        return False
ok(sozlesme(tehdit_modeli_dogrula), "tehdit şeması, izinli değerler, sıralama ve kopyalar korunmalı")
def m_varlik(model):
    return tehdit_modeli_dogrula(dict(model, varliklar=[]))
def m_cikti(model):
    return tehdit_modeli_dogrula(dict(model, cikti_kanallari=[]))
def m_bilgi(model):
    return tehdit_modeli_dogrula(dict(model, saldirgan_bilgisi=[]))
for ad, mutant in [("varlıkları silen", m_varlik), ("çıktıları silen", m_cikti), ("saldırgan bilgisini silen", m_bilgi)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_guvence_veri import json_yukle,metin_yukle

def tehdit_modeli_dogrula(model):
    import re
    if not isinstance(model, dict):
        raise ValueError("model sözlük olmalı")
    if set(model) != {"id", "varliklar", "cikti_kanallari", "saldirgan_bilgisi"}:
        raise ValueError("model şeması geçersiz")
    if not isinstance(model["id"], str):
        raise ValueError("kimlik string olmalı")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", model["id"]):
        raise ValueError("kimlik geçersiz")
    izinler = {
        "varliklar": {"egitim_verisi", "model_parametreleri", "kullanici_girdisi"},
        "cikti_kanallari": {"metin", "olasilik", "embedding"},
        "saldirgan_bilgisi": {"mimari", "ornek_veri", "sorgu_erisimi"},
    }
    for alan, izinli in izinler.items():
        degerler = model[alan]
        if not isinstance(degerler, list):
            raise ValueError(alan + " liste olmalı")
        if not degerler:
            raise ValueError(alan + " boş olamaz")
        if any(not isinstance(deger, str) for deger in degerler):
            raise ValueError(alan + " string listesi olmalı")
        if len(set(degerler)) != len(degerler):
            raise ValueError(alan + " yinelenemez")
        if not set(degerler) <= izinli:
            raise ValueError(alan + " izinli değerler dışında")
    return {"id": model["id"], "varliklar": sorted(model["varliklar"]), "cikti_kanallari": sorted(model["cikti_kanallari"]), "saldirgan_bilgisi": sorted(model["saldirgan_bilgisi"])}

if __name__ == "__main__":
    v=json_yukle("veri/gizlilik.json")
    print("Sentetik ham dosya:\n",metin_yukle("veri/gizlilik.json"))
    print("Tehdit modeli:",tehdit_modeli_dogrula(v["tehdit_modeli"]))
```

```hint
Her listenin türünü, boşluğunu, tekrarını ve izinli kümesini ayrı doğrula. Çıktıda `sorted` ile yeni listeler üret.
```
:::

::: gorev 2 · Üyelik çıkarımı kanıtını ölç
`uyelik_kaniti_olc(kayitlar)` işlevini yaz. Kayıtlar boş olmayan listedir; her kayıt tam olarak `id`, `uye`, `tahmin_uye` alanlarını taşır. Kimlik ilk görevdeki biçimdedir ve yinelenemez. Diğer iki alan bool olmalıdır. Geçersiz veride `ValueError` yükselt.

`{"toplam":N,"tp":N,"fp":N,"tn":N,"fn":N,"dogruluk":X,"avantaj":X}` döndür. Doğruluk `(TP+TN)/toplam`; avantaj `TP/(TP+FN)-FP/(FP+TN)` olur. Paydası sıfır olan oran `0.0` kabul edilir. İki ölçümü de altı ondalık basamağa yuvarla ve girdiyi değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-16")
```

```starter
from ai_guvence_veri import json_yukle,metin_yukle

def uyelik_kaniti_olc(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: doğruluğu üyelik avantajı yerine koyar.
    tp=sum(x["uye"] and x["tahmin_uye"] for x in kayitlar)
    fp=sum(not x["uye"] and x["tahmin_uye"] for x in kayitlar)
    tn=sum(not x["uye"] and not x["tahmin_uye"] for x in kayitlar)
    fn=sum(x["uye"] and not x["tahmin_uye"] for x in kayitlar)
    a=round((tp+tn)/len(kayitlar),6)
    return {"toplam":len(kayitlar),"tp":tp,"fp":fp,"tn":tn,"fn":fn,"dogruluk":a,"avantaj":a}

v=json_yukle("veri/gizlilik.json")
print("Sentetik üyelik ölçümü:",uyelik_kaniti_olc(v["uyelik_kayitlari"]))
```

```test
import copy
K = [
    {"id": "u-1", "uye": True, "tahmin_uye": True},
    {"id": "u-2", "uye": False, "tahmin_uye": True},
    {"id": "u-3", "uye": False, "tahmin_uye": False},
    {"id": "u-4", "uye": True, "tahmin_uye": False},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K) != {"toplam": 4, "tp": 1, "fp": 1, "tn": 1, "fn": 1, "dogruluk": 0.5, "avantaj": 0.0} or K != once:
            return False
        yuvarla = fn(K + [
            {"id": "u-5", "uye": True, "tahmin_uye": True},
            {"id": "u-6", "uye": False, "tahmin_uye": False},
        ])
        if yuvarla["dogruluk"] != 0.666667 or yuvarla["avantaj"] != 0.333333:
            return False
        sadece_uye = fn([{"id": "u", "uye": True, "tahmin_uye": True}])
        if sadece_uye["avantaj"] != 1 or sadece_uye["dogruluk"] != 1:
            return False
        sadece_dis = fn([{"id": "d", "uye": False, "tahmin_uye": False}])
        if sadece_dis["avantaj"] != 0 or fn([{"id": "d", "uye": False, "tahmin_uye": True}])["avantaj"] != -1.0:
            return False
        for kayitlar in [
            None, {}, tuple(K), [], [None], [dict(K[0], ek=1)], [K[0], K[0]],
            [dict(K[0], id="a b")], [dict(K[0], id="a" * 65)], [dict(K[0], id=None)],
            [dict(K[0], uye=1)], [dict(K[0], uye="true")], [dict(K[0], uye=None)],
            [dict(K[0], tahmin_uye=1)], [dict(K[0], tahmin_uye="true")], [dict(K[0], tahmin_uye=None)],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(uyelik_kaniti_olc), "üyelik sayımları, doğruluk, avantaj ve sıfır payda korunmalı")
def m_uye(kayitlar):
    return uyelik_kaniti_olc([dict(x, uye=False) for x in kayitlar])
def m_tahmin(kayitlar):
    return uyelik_kaniti_olc([dict(x, tahmin_uye=False) for x in kayitlar])
def m_id(kayitlar):
    return uyelik_kaniti_olc([dict(x, id="u") for x in kayitlar])
for ad, mutant in [("üyeliği silen", m_uye), ("tahminleri silen", m_tahmin), ("kimlikleri birleştiren", m_id)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_guvence_veri import json_yukle,metin_yukle

def uyelik_kaniti_olc(kayitlar):
    import re
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    if not kayitlar:
        raise ValueError("kayıtlar boş olamaz")
    idler = set()
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"id", "uye", "tahmin_uye"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["id"], str):
            raise ValueError("kimlik string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
            raise ValueError("kimlik geçersiz")
        if kayit["id"] in idler:
            raise ValueError("kimlik yinelenemez")
        if not isinstance(kayit["uye"], bool):
            raise ValueError("üyelik bool olmalı")
        if not isinstance(kayit["tahmin_uye"], bool):
            raise ValueError("tahmin bool olmalı")
        idler.add(kayit["id"])
    tp = sum(1 for x in kayitlar if x["uye"] and x["tahmin_uye"])
    fp = sum(1 for x in kayitlar if not x["uye"] and x["tahmin_uye"])
    tn = sum(1 for x in kayitlar if not x["uye"] and not x["tahmin_uye"])
    fn = sum(1 for x in kayitlar if x["uye"] and not x["tahmin_uye"])
    tpr = tp / (tp + fn) if tp + fn > 0 else 0.0
    fpr = fp / (fp + tn) if fp + tn > 0 else 0.0
    return {"toplam": len(kayitlar), "tp": tp, "fp": fp, "tn": tn, "fn": fn, "dogruluk": round((tp + tn) / len(kayitlar), 6), "avantaj": round(tpr - fpr, 6)}

if __name__ == "__main__":
    v=json_yukle("veri/gizlilik.json")
    print("Sentetik üyelik ölçümü:",uyelik_kaniti_olc(v["uyelik_kayitlari"]))
```

```hint
Dört kararı say, sonra iki oranın paydasını ayrı ele al. Avantaj üye yakalama oranı eksi yanlış üye alarmıdır.
```
:::

::: gorev 3 · Kanıtı taban doğrulukla karşılaştır
`gizlilik_kanit_raporu(kayitlar, avantaj_esik)` işlevini yaz. Kayıtlar boş olmayan listedir; her kayıt tam olarak `deney`, `dogruluk`, `taban_dogrulugu`, `avantaj` alanlarını taşır. Deney ilk görevdeki kimlik biçimindedir. Doğruluk, taban ve eşik bool olmayan sonlu sayı ve `[0,1]`; avantaj bool olmayan sonlu sayı ve `[-1,1]` aralığındadır. Geçersiz veride `ValueError` yükselt.

Her deneyin üç ortalamasını altı ondalık basamağa yuvarla. Ham avantaj eşiğe eşit veya büyük ve ham doğruluk ham tabandan katı büyükse `kanit=True` olur. Kanıtlı deneylerden en yüksek ham avantaj, eşitlikte en yüksek ham doğruluk, sonra alfabetik ad seçilir. `{"satirlar":[{"deney":D,"dogruluk":X,"taban_dogrulugu":X,"avantaj":X,"kanit":BOOL},...],"secilen":D veya None}` döndür. Satırları deney adına göre sırala; uygun yoksa `None` döndür ve girdiyi değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-16")
```

```starter
from ai_guvence_veri import json_yukle,metin_yukle

def gizlilik_kanit_raporu(kayitlar,avantaj_esik):
    # KUSURLU BAŞLANGIÇ KODU: tabana eşit doğruluğu da kanıt sayar.
    satirlar=[]
    for ad in sorted({x["deney"] for x in kayitlar}):
        vs=[x for x in kayitlar if x["deney"]==ad]
        a=sum(x["dogruluk"] for x in vs)/len(vs);b=sum(x["taban_dogrulugu"] for x in vs)/len(vs);v=sum(x["avantaj"] for x in vs)/len(vs)
        satirlar.append({"deney":ad,"dogruluk":round(a,6),"taban_dogrulugu":round(b,6),"avantaj":round(v,6),"kanit":v>=avantaj_esik and a>=b})
    aday=[x for x in satirlar if x["kanit"]]
    secilen=min(aday,key=lambda x:(-x["avantaj"],-x["dogruluk"],x["deney"]))["deney"] if aday else None
    return {"satirlar":satirlar,"secilen":secilen}

v=json_yukle("veri/gizlilik.json")
print("Sentetik kanıt raporu:",gizlilik_kanit_raporu(v["deney_sonuclari"],v["avantaj_esik"]))
```

```test
import copy
K = [
    {"deney": "olasilik", "dogruluk": 0.8, "taban_dogrulugu": 0.6, "avantaj": 0.4},
    {"deney": "metin", "dogruluk": 0.7, "taban_dogrulugu": 0.6, "avantaj": 0.1},
    {"deney": "tabanli", "dogruluk": 0.6, "taban_dogrulugu": 0.6, "avantaj": 0.9},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        sonuc = fn(K, 0.3)
        if K != once or sonuc["secilen"] != "olasilik" or [x["kanit"] for x in sonuc["satirlar"]] != [False, True, False]:
            return False
        esikte = fn(K, 0.4)
        if esikte["secilen"] != "olasilik" or esikte["satirlar"][0]["kanit"]:
            return False
        if fn(K, 1)["secilen"] is not None:
            return False
        yuvarla = fn([
            {"deney": "a", "dogruluk": 1, "taban_dogrulugu": 0, "avantaj": 1},
            {"deney": "a", "dogruluk": 0, "taban_dogrulugu": 0, "avantaj": 0},
            {"deney": "a", "dogruluk": 0, "taban_dogrulugu": 0, "avantaj": 0},
        ], 0)
        if yuvarla["satirlar"][0] != {"deney": "a", "dogruluk": 0.333333, "taban_dogrulugu": 0.0, "avantaj": 0.333333, "kanit": True}:
            return False
        taban_yuvarla = fn([
            {"deney": "b", "dogruluk": 1, "taban_dogrulugu": 1, "avantaj": 1},
            {"deney": "b", "dogruluk": 1, "taban_dogrulugu": 0, "avantaj": 1},
            {"deney": "b", "dogruluk": 1, "taban_dogrulugu": 0, "avantaj": 1},
        ], 0)
        if taban_yuvarla["satirlar"][0]["taban_dogrulugu"] != 0.333333:
            return False
        sinir = fn([{"deney": "a", "dogruluk": 1, "taban_dogrulugu": 0, "avantaj": -1}], 0)
        if sinir["satirlar"][0]["avantaj"] != -1 or sinir["secilen"] is not None:
            return False
        for kayitlar, esik in [
            (None, 0.3), (K, None), ({}, 0.3), (tuple(K), 0.3), ([], 0.3), ([None], 0.3), ([dict(K[0], ek=1)], 0.3),
            ([dict(K[0], deney=123)], 0.3), ([dict(K[0], deney="a b")], 0.3), ([dict(K[0], deney="a" * 65)], 0.3),
            ([dict(K[0], dogruluk=True)], 0.3), ([dict(K[0], dogruluk="0.8")], 0.3), ([dict(K[0], dogruluk=float("nan"))], 0.3),
            ([dict(K[0], dogruluk=-0.1)], 0.3), ([dict(K[0], dogruluk=1.1)], 0.3),
            ([dict(K[0], taban_dogrulugu=True)], 0.3), ([dict(K[0], taban_dogrulugu=-0.1)], 0.3), ([dict(K[0], taban_dogrulugu=1.1)], 0.3),
            ([dict(K[0], avantaj=True)], 0.3), ([dict(K[0], avantaj="0.4")], 0.3), ([dict(K[0], avantaj=float("inf"))], 0.3),
            ([dict(K[0], avantaj=-1.1)], 0.3), ([dict(K[0], avantaj=1.1)], 0.3),
            (K, True), (K, "0.3"), (K, float("nan")), (K, float("inf")), (K, -0.1), (K, 1.1),
        ]:
            try:
                fn(kayitlar, esik)
                return False
            except ValueError:
                pass
        empate=[{"deney":"z","dogruluk":0.8,"taban_dogrulugu":0.5,"avantaj":0.4},{"deney":"a","dogruluk":0.8,"taban_dogrulugu":0.5,"avantaj":0.4}]
        if fn(empate,0.4)["secilen"]!="a":return False
        if fn([dict(empate[0],dogruluk=0.9),empate[1]],0.4)["secilen"]!="z":return False
        if fn([{"deney":"d1","dogruluk":0.9,"taban_dogrulugu":0.5,"avantaj":0.4},{"deney":"d2","dogruluk":0.8,"taban_dogrulugu":0.5,"avantaj":0.7}],0.3)["secilen"]!="d2":return False
        tiny=[{"deney":"a","dogruluk":0.80000001,"taban_dogrulugu":0.8,"avantaj":0.39999999}]
        if fn(tiny,0.4)["secilen"] is not None:return False
        if fn([dict(tiny[0],avantaj=0.4)],0.4)["secilen"]!="a":return False
        return True
    except Exception:
        return False
ok(sozlesme(gizlilik_kanit_raporu), "taban karşılaştırması, avantaj eşiği ve seçim korunmalı")
def m_avantaj(kayitlar, esik):
    return gizlilik_kanit_raporu([dict(x, avantaj=0) for x in kayitlar], esik)
def m_dogruluk(kayitlar, esik):
    return gizlilik_kanit_raporu([dict(x, dogruluk=0) for x in kayitlar], esik)
def m_taban(kayitlar, esik):
    return gizlilik_kanit_raporu([dict(x, taban_dogrulugu=1) for x in kayitlar], esik)
for ad, mutant in [("avantajı silen", m_avantaj), ("doğruluğu silen", m_dogruluk), ("tabanı değiştiren", m_taban)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_guvence_veri import json_yukle,metin_yukle

def gizlilik_kanit_raporu(kayitlar, avantaj_esik):
    import math
    import re
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    if not kayitlar:
        raise ValueError("kayıtlar boş olamaz")
    if isinstance(avantaj_esik, bool):
        raise ValueError("eşik sayı olmalı")
    if not isinstance(avantaj_esik, (int, float)):
        raise ValueError("eşik sayı olmalı")
    if not math.isfinite(avantaj_esik):
        raise ValueError("eşik sonlu olmalı")
    if avantaj_esik < 0 or avantaj_esik > 1:
        raise ValueError("eşik aralık dışında")
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"deney", "dogruluk", "taban_dogrulugu", "avantaj"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["deney"], str):
            raise ValueError("deney string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["deney"]):
            raise ValueError("deney geçersiz")
        for alan in ("dogruluk", "taban_dogrulugu", "avantaj"):
            deger = kayit[alan]
            if isinstance(deger, bool):
                raise ValueError("ölçüm sayı olmalı")
            if not isinstance(deger, (int, float)):
                raise ValueError("ölçüm sayı olmalı")
            if not math.isfinite(deger):
                raise ValueError("ölçüm sonlu olmalı")
            alt = -1 if alan == "avantaj" else 0
            if deger < alt or deger > 1:
                raise ValueError("ölçüm aralık dışında")
    satirlar = []
    for deney in sorted({x["deney"] for x in kayitlar}):
        grup = [x for x in kayitlar if x["deney"] == deney]
        dogruluk = sum(x["dogruluk"] for x in grup) / len(grup)
        taban = sum(x["taban_dogrulugu"] for x in grup) / len(grup)
        avantaj = sum(x["avantaj"] for x in grup) / len(grup)
        satirlar.append({"deney": deney, "dogruluk": round(dogruluk, 6), "taban_dogrulugu": round(taban, 6), "avantaj": round(avantaj, 6), "kanit": avantaj >= avantaj_esik and dogruluk > taban, "_dogruluk": dogruluk, "_avantaj": avantaj})
    kanitlar = [x for x in satirlar if x["kanit"]]
    secilen = min(kanitlar, key=lambda x: (-x["_avantaj"], -x["_dogruluk"], x["deney"]))["deney"] if kanitlar else None
    for satir in satirlar:
        del satir["_dogruluk"]
        del satir["_avantaj"]
    return {"satirlar": satirlar, "secilen": secilen}

if __name__ == "__main__":
    v=json_yukle("veri/gizlilik.json")
    print("Sentetik kanıt raporu:",gizlilik_kanit_raporu(v["deney_sonuclari"],v["avantaj_esik"]))
```

```hint
Kanit ve seçim kararlarını ham ortalamalarla ver. Avantaj eşiğini ve doğruluğun tabanı aşmasını iki ayrı koşul olarak uygula.
```
:::


::: anlat Gerçek model olasılıklarından gizlilik kanıtı çıkar
Ham sentetik ayar aynı Pafta sunucusunda `/data/ai-guvence-16-gizlilik.txt` adresindedir. Markdown işleyici bu yerel yolu tıklanabilir yapmaz; sunucu adresine bu yolu yaz. Çalıştır ayrı kalıcı `calisma/ai-guvence-16/gizlilik.json` kopyasının yolunu ve içeriğini gösterir. Dış editör veya Python ile `seed` ve örnek sayısını değiştirip yeniden Çalıştır; değişikliğin korunur. Test ayrı görülmemiş `seed` kullanır.

Bu deneyde Qwen yerine CPU'da küçük bir PyTorch sınıflandırıcı gerçekten `autograd` ile eğitilir. Rastgele özellik ve etiketler sentetiktir; modelin logit ve olasılıkları gerçek çıkarım çıktısıdır. Üyelik eşiği ayrı `shadow` modelinin üye ve üye olmayan örneklerinden seçilir; hedef model üyeliği eşik ayarlamak için kullanılmaz. Üç bağımsız tekrar yapılır. Öğrenci gerçek hedef olasılıklarının ürettiği üyelik kayıtlarını ölçer, `0.5` çoğunluk tabanıyla ve `TPR - FPR` avantajıyla raporlar. Pozitif avantaj veya saldırı başarısı geçme şartı değildir.

Tehdit modeli gerçek varlığı (`egitim_verisi` / `model_parametreleri`), erişilen kanıtı (`olasilik`) ve saldırgan bilgisini tanımlar. Bu ölçüm sohbet modellerinin veya gerçek kişisel verinin gizliliği hakkında genel garanti değildir. Gerçek eğitim kaybı, logit, olasılık, üyelik kaydı, sürüm, cihaz ve ağırlık özeti kanıttadır. Testin geçici ağırlıkları kapanınca silinir; JSON izleri kalır. Çalıştır'da kendi deney klasöründeki ağırlıkları inceleyebilirsin. Kullanıcı verisi silinmez, yeni indirme yapılmaz.

Kaynaklar: [Shokri vd. 2017 — Membership Inference Attacks Against Machine Learning Models (arXiv:1610.05820)](https://arxiv.org/abs/1610.05820), [Yeom vd. 2018 — Privacy Risk in Machine Learning: Analyzing the Connection to Overfitting (arXiv:1709.01604)](https://arxiv.org/abs/1709.01604).
:::

::: gorev Gerçek deney · Gizlilik iddiasını gerçek autograd modelinden ölç
Önceki `tehdit_modeli_dogrula`, `uyelik_kaniti_olc` ve `gizlilik_kanit_raporu` işlevlerini birleştir. Kontrol Et saf sözleşmelerden sonra ayrı `shadow` ve `target` modellerini gerçekten eğitip model çıktılarından hesaplamanı sınar. Dengesiz veride doğruluğu üyelik avantajı diye yorumlama.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 240
```

```starter
import ai_lab
def tehdit_modeli_dogrula(model):return {}
def uyelik_kaniti_olc(kayitlar):return {}
def gizlilik_kanit_raporu(kayitlar,avantaj_esik):return {}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_16 as deney
    deney.goster(tehdit_modeli_dogrula,uyelik_kaniti_olc,gizlilik_kanit_raporu)

```

```test
import ai_lab,ast
sonuclar=[]
_ok=ok
def ok(kosul,mesaj):
    sonuclar.append(bool(kosul));return _ok(kosul,mesaj)
yasak=("olcu_ref","rapor_ref","_train","kanit_yaz","getattr")
ihlal=ai_lab.kod_denetimi(src,yasak=yasak)
try:
    for node in ast.walk(ast.parse(src)):
        if isinstance(node,ast.ImportFrom) and any(a.name in yasak or a.name=="*" for a in node.names):ihlal.append("referans ithali")
except SyntaxError:ihlal.append("sözdizimi")
ok(not ihlal,"Kendi gizlilik ölçümünü yaz; referans ithali yasak")
if ihlal:stop()
import copy
M = {"id": "gizlilik-1", "varliklar": ["kullanici_girdisi", "egitim_verisi"], "cikti_kanallari": ["olasilik", "metin"], "saldirgan_bilgisi": ["sorgu_erisimi", "mimari"]}
BEKLENEN = {"id": "gizlilik-1", "varliklar": ["egitim_verisi", "kullanici_girdisi"], "cikti_kanallari": ["metin", "olasilik"], "saldirgan_bilgisi": ["mimari", "sorgu_erisimi"]}
def sozlesme(fn):
    try:
        once = copy.deepcopy(M)
        sonuc = fn(M)
        if sonuc != BEKLENEN or M != once or any(sonuc[k] is M[k] for k in ("varliklar", "cikti_kanallari", "saldirgan_bilgisi")):
            return False
        sinir = {"id": "a" * 64, "varliklar": ["model_parametreleri"], "cikti_kanallari": ["embedding"], "saldirgan_bilgisi": ["ornek_veri"]}
        if fn(sinir) != sinir:
            return False
        tam = dict(sinir, varliklar=["egitim_verisi", "model_parametreleri", "kullanici_girdisi"])
        if fn(tam)["varliklar"] != ["egitim_verisi", "kullanici_girdisi", "model_parametreleri"]:
            return False
        for model in [
            None, [], dict(M, ek=1), dict(M, id=123), dict(M, id=""), dict(M, id="a b"), dict(M, id="a" * 65),
            dict(M, varliklar=[]), dict(M, varliklar=None), dict(M, varliklar={}), dict(M, varliklar=("egitim_verisi",)), dict(M, varliklar=["diger"]),
            dict(M, varliklar=["egitim_verisi", "egitim_verisi"]), dict(M, varliklar=[1]), dict(M, varliklar=[["egitim_verisi"]]),
            dict(M, cikti_kanallari=[]), dict(M, cikti_kanallari=None), dict(M, cikti_kanallari=["diger"]),
            dict(M, cikti_kanallari=["metin", "metin"]), dict(M, cikti_kanallari=[1]),
            dict(M, saldirgan_bilgisi=[]), dict(M, saldirgan_bilgisi=None), dict(M, saldirgan_bilgisi=["diger"]),
            dict(M, saldirgan_bilgisi=["mimari", "mimari"]), dict(M, saldirgan_bilgisi=[1]),
        ]:
            try:
                fn(model)
                return False
            except ValueError:
                pass
        for ad in ["_a","-a","éx","a\n"]:
            try:fn(dict(M,id=ad));return False
            except ValueError:pass
        return True
    except Exception:
        return False
ok(sozlesme(tehdit_modeli_dogrula), "tehdit şeması, izinli değerler, sıralama ve kopyalar korunmalı")
def m_varlik(model):
    return tehdit_modeli_dogrula(dict(model, varliklar=[]))
def m_cikti(model):
    return tehdit_modeli_dogrula(dict(model, cikti_kanallari=[]))
def m_bilgi(model):
    return tehdit_modeli_dogrula(dict(model, saldirgan_bilgisi=[]))
for ad, mutant in [("varlıkları silen", m_varlik), ("çıktıları silen", m_cikti), ("saldırgan bilgisini silen", m_bilgi)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

import copy
K = [
    {"id": "u-1", "uye": True, "tahmin_uye": True},
    {"id": "u-2", "uye": False, "tahmin_uye": True},
    {"id": "u-3", "uye": False, "tahmin_uye": False},
    {"id": "u-4", "uye": True, "tahmin_uye": False},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K) != {"toplam": 4, "tp": 1, "fp": 1, "tn": 1, "fn": 1, "dogruluk": 0.5, "avantaj": 0.0} or K != once:
            return False
        yuvarla = fn(K + [
            {"id": "u-5", "uye": True, "tahmin_uye": True},
            {"id": "u-6", "uye": False, "tahmin_uye": False},
        ])
        if yuvarla["dogruluk"] != 0.666667 or yuvarla["avantaj"] != 0.333333:
            return False
        sadece_uye = fn([{"id": "u", "uye": True, "tahmin_uye": True}])
        if sadece_uye["avantaj"] != 1 or sadece_uye["dogruluk"] != 1:
            return False
        sadece_dis = fn([{"id": "d", "uye": False, "tahmin_uye": False}])
        if sadece_dis["avantaj"] != 0 or fn([{"id": "d", "uye": False, "tahmin_uye": True}])["avantaj"] != -1.0:
            return False
        for kayitlar in [
            None, {}, tuple(K), [], [None], [dict(K[0], ek=1)], [K[0], K[0]],
            [dict(K[0], id="a b")], [dict(K[0], id="a" * 65)], [dict(K[0], id=None)],
            [dict(K[0], uye=1)], [dict(K[0], uye="true")], [dict(K[0], uye=None)],
            [dict(K[0], tahmin_uye=1)], [dict(K[0], tahmin_uye="true")], [dict(K[0], tahmin_uye=None)],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(uyelik_kaniti_olc), "üyelik sayımları, doğruluk, avantaj ve sıfır payda korunmalı")
def m_uye(kayitlar):
    return uyelik_kaniti_olc([dict(x, uye=False) for x in kayitlar])
def m_tahmin(kayitlar):
    return uyelik_kaniti_olc([dict(x, tahmin_uye=False) for x in kayitlar])
def m_id(kayitlar):
    return uyelik_kaniti_olc([dict(x, id="u") for x in kayitlar])
for ad, mutant in [("üyeliği silen", m_uye), ("tahminleri silen", m_tahmin), ("kimlikleri birleştiren", m_id)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

import copy
K = [
    {"deney": "olasilik", "dogruluk": 0.8, "taban_dogrulugu": 0.6, "avantaj": 0.4},
    {"deney": "metin", "dogruluk": 0.7, "taban_dogrulugu": 0.6, "avantaj": 0.1},
    {"deney": "tabanli", "dogruluk": 0.6, "taban_dogrulugu": 0.6, "avantaj": 0.9},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        sonuc = fn(K, 0.3)
        if K != once or sonuc["secilen"] != "olasilik" or [x["kanit"] for x in sonuc["satirlar"]] != [False, True, False]:
            return False
        esikte = fn(K, 0.4)
        if esikte["secilen"] != "olasilik" or esikte["satirlar"][0]["kanit"]:
            return False
        if fn(K, 1)["secilen"] is not None:
            return False
        yuvarla = fn([
            {"deney": "a", "dogruluk": 1, "taban_dogrulugu": 0, "avantaj": 1},
            {"deney": "a", "dogruluk": 0, "taban_dogrulugu": 0, "avantaj": 0},
            {"deney": "a", "dogruluk": 0, "taban_dogrulugu": 0, "avantaj": 0},
        ], 0)
        if yuvarla["satirlar"][0] != {"deney": "a", "dogruluk": 0.333333, "taban_dogrulugu": 0.0, "avantaj": 0.333333, "kanit": True}:
            return False
        taban_yuvarla = fn([
            {"deney": "b", "dogruluk": 1, "taban_dogrulugu": 1, "avantaj": 1},
            {"deney": "b", "dogruluk": 1, "taban_dogrulugu": 0, "avantaj": 1},
            {"deney": "b", "dogruluk": 1, "taban_dogrulugu": 0, "avantaj": 1},
        ], 0)
        if taban_yuvarla["satirlar"][0]["taban_dogrulugu"] != 0.333333:
            return False
        sinir = fn([{"deney": "a", "dogruluk": 1, "taban_dogrulugu": 0, "avantaj": -1}], 0)
        if sinir["satirlar"][0]["avantaj"] != -1 or sinir["secilen"] is not None:
            return False
        for kayitlar, esik in [
            (None, 0.3), (K, None), ({}, 0.3), (tuple(K), 0.3), ([], 0.3), ([None], 0.3), ([dict(K[0], ek=1)], 0.3),
            ([dict(K[0], deney=123)], 0.3), ([dict(K[0], deney="a b")], 0.3), ([dict(K[0], deney="a" * 65)], 0.3),
            ([dict(K[0], dogruluk=True)], 0.3), ([dict(K[0], dogruluk="0.8")], 0.3), ([dict(K[0], dogruluk=float("nan"))], 0.3),
            ([dict(K[0], dogruluk=-0.1)], 0.3), ([dict(K[0], dogruluk=1.1)], 0.3),
            ([dict(K[0], taban_dogrulugu=True)], 0.3), ([dict(K[0], taban_dogrulugu=-0.1)], 0.3), ([dict(K[0], taban_dogrulugu=1.1)], 0.3),
            ([dict(K[0], avantaj=True)], 0.3), ([dict(K[0], avantaj="0.4")], 0.3), ([dict(K[0], avantaj=float("inf"))], 0.3),
            ([dict(K[0], avantaj=-1.1)], 0.3), ([dict(K[0], avantaj=1.1)], 0.3),
            (K, True), (K, "0.3"), (K, float("nan")), (K, float("inf")), (K, -0.1), (K, 1.1),
        ]:
            try:
                fn(kayitlar, esik)
                return False
            except ValueError:
                pass
        empate=[{"deney":"z","dogruluk":0.8,"taban_dogrulugu":0.5,"avantaj":0.4},{"deney":"a","dogruluk":0.8,"taban_dogrulugu":0.5,"avantaj":0.4}]
        if fn(empate,0.4)["secilen"]!="a":return False
        if fn([dict(empate[0],dogruluk=0.9),empate[1]],0.4)["secilen"]!="z":return False
        if fn([{"deney":"d1","dogruluk":0.9,"taban_dogrulugu":0.5,"avantaj":0.4},{"deney":"d2","dogruluk":0.8,"taban_dogrulugu":0.5,"avantaj":0.7}],0.3)["secilen"]!="d2":return False
        tiny=[{"deney":"a","dogruluk":0.80000001,"taban_dogrulugu":0.8,"avantaj":0.39999999}]
        if fn(tiny,0.4)["secilen"] is not None:return False
        if fn([dict(tiny[0],avantaj=0.4)],0.4)["secilen"]!="a":return False
        return True
    except Exception:
        return False
ok(sozlesme(gizlilik_kanit_raporu), "taban karşılaştırması, avantaj eşiği ve seçim korunmalı")
def m_avantaj(kayitlar, esik):
    return gizlilik_kanit_raporu([dict(x, avantaj=0) for x in kayitlar], esik)
def m_dogruluk(kayitlar, esik):
    return gizlilik_kanit_raporu([dict(x, dogruluk=0) for x in kayitlar], esik)
def m_taban(kayitlar, esik):
    return gizlilik_kanit_raporu([dict(x, taban_dogrulugu=1) for x in kayitlar], esik)
for ad, mutant in [("avantajı silen", m_avantaj), ("doğruluğu silen", m_dogruluk), ("tabanı değiştiren", m_taban)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

if not all(sonuclar):stop()
from sandbox import ai_gercek_ai_guvence_16 as deney
import tempfile,secrets,json
from pathlib import Path
if not ok(not ai_lab.kod_denetimi(src,('olcu_ref','rapor_ref','_train')),'gerçek deney yamalanmamalı'):stop()
probe=[{'id':'u'+str(i),'uye':i<4,'tahmin_uye':i%3==0} for i in range(12)]
if not ok(uyelik_kaniti_olc(probe)==deney.olcu_ref(probe),'yeni dengesiz üyelikte TPR-FPR'):stop()
with tempfile.TemporaryDirectory(prefix='pafta_privacy16_') as tmp:
    p=Path(tmp)/'ayar.json';p.write_text(json.dumps({'seed':secrets.randbelow(1000000),'ornek':32}),encoding='utf-8')
    r=deney.deney(tehdit_modeli_dogrula,uyelik_kaniti_olc,gizlilik_kanit_raporu,p,Path(tmp)/'deney')
    for k,v in r['kontroller'].items():ok(v,'gerçek deney: '+k)
    accepted=all(sonuclar) and all(r['kontroller'].values());ai_lab.kanit_yaz('guvence-16-gizlilik',dict(r,kabul=accepted));ok(accepted,'gerçek autograd/modelolasılığı/üyelikölçümü; saldırıbaşarısı şart değil')

```

```solution
import ai_lab
def tehdit_modeli_dogrula(model):
    import re
    if not isinstance(model, dict):
        raise ValueError("model sözlük olmalı")
    if set(model) != {"id", "varliklar", "cikti_kanallari", "saldirgan_bilgisi"}:
        raise ValueError("model şeması geçersiz")
    if not isinstance(model["id"], str):
        raise ValueError("kimlik string olmalı")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", model["id"]):
        raise ValueError("kimlik geçersiz")
    izinler = {
        "varliklar": {"egitim_verisi", "model_parametreleri", "kullanici_girdisi"},
        "cikti_kanallari": {"metin", "olasilik", "embedding"},
        "saldirgan_bilgisi": {"mimari", "ornek_veri", "sorgu_erisimi"},
    }
    for alan, izinli in izinler.items():
        degerler = model[alan]
        if not isinstance(degerler, list):
            raise ValueError(alan + " liste olmalı")
        if not degerler:
            raise ValueError(alan + " boş olamaz")
        if any(not isinstance(deger, str) for deger in degerler):
            raise ValueError(alan + " string listesi olmalı")
        if len(set(degerler)) != len(degerler):
            raise ValueError(alan + " yinelenemez")
        if not set(degerler) <= izinli:
            raise ValueError(alan + " izinli değerler dışında")
    return {"id": model["id"], "varliklar": sorted(model["varliklar"]), "cikti_kanallari": sorted(model["cikti_kanallari"]), "saldirgan_bilgisi": sorted(model["saldirgan_bilgisi"])}

def uyelik_kaniti_olc(kayitlar):
    import re
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    if not kayitlar:
        raise ValueError("kayıtlar boş olamaz")
    idler = set()
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"id", "uye", "tahmin_uye"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["id"], str):
            raise ValueError("kimlik string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
            raise ValueError("kimlik geçersiz")
        if kayit["id"] in idler:
            raise ValueError("kimlik yinelenemez")
        if not isinstance(kayit["uye"], bool):
            raise ValueError("üyelik bool olmalı")
        if not isinstance(kayit["tahmin_uye"], bool):
            raise ValueError("tahmin bool olmalı")
        idler.add(kayit["id"])
    tp = sum(1 for x in kayitlar if x["uye"] and x["tahmin_uye"])
    fp = sum(1 for x in kayitlar if not x["uye"] and x["tahmin_uye"])
    tn = sum(1 for x in kayitlar if not x["uye"] and not x["tahmin_uye"])
    fn = sum(1 for x in kayitlar if x["uye"] and not x["tahmin_uye"])
    tpr = tp / (tp + fn) if tp + fn > 0 else 0.0
    fpr = fp / (fp + tn) if fp + tn > 0 else 0.0
    return {"toplam": len(kayitlar), "tp": tp, "fp": fp, "tn": tn, "fn": fn, "dogruluk": round((tp + tn) / len(kayitlar), 6), "avantaj": round(tpr - fpr, 6)}

def gizlilik_kanit_raporu(kayitlar, avantaj_esik):
    import math
    import re
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    if not kayitlar:
        raise ValueError("kayıtlar boş olamaz")
    if isinstance(avantaj_esik, bool):
        raise ValueError("eşik sayı olmalı")
    if not isinstance(avantaj_esik, (int, float)):
        raise ValueError("eşik sayı olmalı")
    if not math.isfinite(avantaj_esik):
        raise ValueError("eşik sonlu olmalı")
    if avantaj_esik < 0 or avantaj_esik > 1:
        raise ValueError("eşik aralık dışında")
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"deney", "dogruluk", "taban_dogrulugu", "avantaj"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["deney"], str):
            raise ValueError("deney string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["deney"]):
            raise ValueError("deney geçersiz")
        for alan in ("dogruluk", "taban_dogrulugu", "avantaj"):
            deger = kayit[alan]
            if isinstance(deger, bool):
                raise ValueError("ölçüm sayı olmalı")
            if not isinstance(deger, (int, float)):
                raise ValueError("ölçüm sayı olmalı")
            if not math.isfinite(deger):
                raise ValueError("ölçüm sonlu olmalı")
            alt = -1 if alan == "avantaj" else 0
            if deger < alt or deger > 1:
                raise ValueError("ölçüm aralık dışında")
    satirlar = []
    for deney in sorted({x["deney"] for x in kayitlar}):
        grup = [x for x in kayitlar if x["deney"] == deney]
        dogruluk = sum(x["dogruluk"] for x in grup) / len(grup)
        taban = sum(x["taban_dogrulugu"] for x in grup) / len(grup)
        avantaj = sum(x["avantaj"] for x in grup) / len(grup)
        satirlar.append({"deney": deney, "dogruluk": round(dogruluk, 6), "taban_dogrulugu": round(taban, 6), "avantaj": round(avantaj, 6), "kanit": avantaj >= avantaj_esik and dogruluk > taban, "_dogruluk": dogruluk, "_avantaj": avantaj})
    kanitlar = [x for x in satirlar if x["kanit"]]
    secilen = min(kanitlar, key=lambda x: (-x["_avantaj"], -x["_dogruluk"], x["deney"]))["deney"] if kanitlar else None
    for satir in satirlar:
        del satir["_dogruluk"]
        del satir["_avantaj"]
    return {"satirlar": satirlar, "secilen": secilen}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_16 as deney
    deney.goster(tehdit_modeli_dogrula,uyelik_kaniti_olc,gizlilik_kanit_raporu)

```

```hint
Shadow eşiği ayrı öğrenilir; hedef üyeliği yalnız ölçüm içindir. `TPR - FPR` ve taban doğruluk koşullarını ayrı koru. Saldırının kazanması şart değildir.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Gizlilik tehdit modelinin üç bileşeni (30 sn).** "'Model veri sızdırıyor mu?' sorusu tek başına belirsizdir; önce korunan varlığı (`egitim_verisi`, `kullanici_girdisi`, `model_parametreleri`), dışarı açılan çıktı kanalını (`metin`, `olasilik`, `embedding`) ve saldırganın ön bilgisini sabitlemek gerekir."
2. **Çoğunluk tabanı tuzağı ve `TPR - FPR` avantajı (35 sn).** "Test kümesinin `%90`'ı üye değilse hep 'üye değil' diyen saldırgan `%90` doğruluk alır ama hiçbir şey öğrenmemiştir; gerçek gizlilik sızıntısı sinyali çoğunluk tabanını aşan doğruluk ve pozitif `TPR - FPR` avantajıyla ölçülür."
3. **`Shadow` model ayrımı (30 sn).** "Saldırı eşiği hedef modelin gerçek üyelik etiketlerine bakılarak seçilirse veri sızıntısı deneyi kendi kendini kandırır; eşik bağımsız `shadow` modelde öğrenilip hedefte kör biçimde sınanır."
4. **Soru (25 sn).** "Bir API tam olasılık vektörü yerine yalnız `top-1` sınıf etiketini döndürdüğünde üyelik çıkarımı kanalı tamamen kapanır mı, yoksa nasıl zayıflar?"
:::
