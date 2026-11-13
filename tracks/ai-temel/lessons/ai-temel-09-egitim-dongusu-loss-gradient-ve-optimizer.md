---
id: ai-temel-09
title: "Eğitim Döngüsü: Loss, Gradient ve Optimizer"
summary: Sentetik MSE kaybı, gradyan ve SGD adımlarıyla tek ağırlıklı eğitim döngüsü oluştur.
esleme: ai-matematik-04, ai-temel-05, ai-temel-10
timeout: 45
---

::: anlat Kayıp hatayı, gradyan yönü gösterir

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| PyTorch autograd işlem grafiğinden parametre gradyanları üretir, optimizer parametreleri günceller | İlk üç görev görünür sentetik sayılar ve elle MSE/SGD hesabı; son görev gerçek Linear(2,1), backward ve SGD.step | Elle yazılmış gradyan tablosu autograd deneyi değildir; küçük lineer model LLM fine-tuning yerine geçmez |
| Eğitim izi güncelleme öncesi kayıpları ve son parametreleri kaydeder | CPU/float64 hesap ve analitik referansla karşılaştırma; gerçek gradient/step hook'ları | Kayıp düşüşü genelleme, üretim doğruluğu veya güvenlik kanıtı değildir |

> [!NOT]
> `veri/egitim.json` elle hazırlanmış **sentetik** veridir; gerçek eğitim kaydı değildir. İlk üç görev aynı dosyanın alanlarını okur. Setup her çalıştırmada geçici kopya oluşturur; düzenlemeler kalıcı değildir. Kaynak fixture dosyasını editörle açabilir, ders kodunda okunan kopyayı değiştirerek Run ile deneyebilirsin. Gizli testler ayrı. Son görev kurulu PyTorch ile gerçek eğitim çalıştırır; önceden eğitilmiş model veya yeni indirme gerekmez.

Ortalama kare hata tahmin ile hedefin farkını cezalandırır. Gradyan kaybın ağırlıklara göre değişim yönünü verir; optimizer bu bilgiyi kullanarak ağırlıkları günceller. PyTorch bu işlemleri otomatik türevle yapar, ancak temel döngü aynıdır.

Görevler 1–3 sentetik veride elle formül uygular; son adım gerçek PyTorch autograd ve SGD optimizer çalıştırır. TensorBoard bu derste kullanılmaz. Üç tahminlik küçük MSE ve tek ağırlıklı lineer regresyon kullanılır. Böylece her güncellemenin kaybı nasıl değiştirdiği gerçek Python çıktısıyla izlenebilir.
:::

::: anlat learning rate güncellemenin ölçeğidir

Önce `veri/egitim.json` dosyasını aç. `tahmin` ve `hedef` ilk görevde üç örneğin hatasını, `agirliklar` ve `gradyan` ikinci görevde güncelleme girdilerini, `tek_agirlik` ise üçüncü görevdeki küçük veri/model ayarını taşır. Bunlar farklı şekillerde aynı eğitim döngüsüne hazırlanır. İlk görevdeki gradyan tahmine göredir; gerçek modelin ağırlık gradyanı için zincir kuralıyla girdinin etkisi de gerekir. Üçüncü görevde bu yüzden iki çarpı x çarpı hata kullanılır. Tahmine göre türevi doğrudan ağırlık türevi sanmak güncellemeyi yanlış ölçekler.

Ortalama kare hata, kare farkların toplamını örnek sayısına böler. Ortalama yerine toplam kullanırsan örnek sayısı arttığında aynı öğrenme oranında gradyan da büyür. Bu yalnız rapor biçimi değişikliği değildir; parametre adımı değişir. Sıfır hata örneğinde gradyan sıfır olmalı; negatif farkın gradyanı negatif olabilir. Gradyan mutlak hata değildir. SGD, işareti tersine çevirerek bu gradyanı ağırlıktan çıkarır; eklemek çoğu küçük adımda kaybı artırır.

Gerçek PyTorch eğitiminde ileri hesap bir işlem grafiği kurar. Loss.backward bu grafikteki türevleri parametrelerin grad alanına biriktirir. Optimizer.step mevcut gradyanları kullanarak kendisine verilmiş parametreleri günceller. Bu yüzden yalnız son ağırlığı doğru sayıya atamak eğitim yapıldığının kanıtı değildir. Laboratuvar hem parametre gradient hook'larını hem verilen optimizer'ın adım hook'unu gözlemler. Öğrenci başka model veya optimizer oluşturup yalnız rapor döndürerek bu sözleşmeyi karşılayamaz.

Her adımın başında zero_grad gerekir. Temizlemezsen bir önceki adımın gradyanı yeni gradyana eklenir; bu dersin bağımsız SGD adımlarıyla aynı hesap olmaz. Bilinçli gradient accumulation bazı büyük eğitimlerde kullanılır ama ayrı tasarlanmış bir yöntemdir. Burada onu yanlışlıkla uygulamak kabul edilmez. Eğitim sırasında no_grad kullanmak ise backward için gereken grafiği keser. Son parametreleri raporlarken detach kullanmak doğrudur; kaybı hesaplamadan önce parametreyi detach etmek farklıdır.

İzi okurken kaybın ne zaman ölçüldüğüne bak. Bu derste her kayıp o adımın güncellemesinden öncedir, son ağırlık ise bütün adımlardan sonradır. Bu yüzden son raporlanan kayıp son ağırlığın değerlendirme kaybı olmak zorunda değildir. Çıktıları bir adım kaydırmak doğru gibi görünen ama farklı bir eğitim izi üretir. İlk üç görev altı haneli sonuçlar döndürür; gerçek eğitim görevi yuvarlanmamış Python float ister ve toleransla karşılaştırır. Ara ağırlıkları her adımda yuvarlamak sonraki hesabı da değiştirir.

Saldırgan bir eğitim verisinin hedeflerini veya örnek dağılımını değiştirerek öğrenilen parametreleri etkileyebilir. Bu görev zehirleme saldırısını ölçmez; kayıp, veri ve güncelleme arasındaki bağı anlamaya hazırlık sağlar. Savunma açısından yalnız eğitim kaybının düşmesine güvenmek yetmez: kirli veriye de iyi uyum sağlanabilir. Değerlendirme ayrımı, veri kökeni ve bağımsız testler başka görevlerde ayrıca ele alınır. Küçük lineer deneyin LLM hizalama veya güvenlik başarısı olduğu iddia edilmez.

Sık tuzaklar bool'u sayı sanmak, NaN'ı normal kayıp gibi geçirmek, girdi listesini yerinde değiştirmek ve öğrenme oranını sessizce başka değere ayarlamaktır. Sayısal girdiler sonlu olmalıdır. Gerçek test verilen modelin parametrelerini, x/y girdilerini ve optimizer öğrenme oranını da kontrol eder. Boş veya sabit rapor, backward olmadan atanan ağırlık ve toplam kayıp kullanan döngü ayrı yanlış örneklerdir. Bağımlılık eksikliği başarı sayılmaz; hiçbir indirme dersin içinde kendiliğinden yapılmaz.

SGD ağırlığı gradyanın ters yönünde, öğrenme oranıyla ölçeklenmiş miktarda değiştirir. Çok büyük oran salınım veya ıraksama, çok küçük oran yavaş öğrenme yaratabilir. Kayıp düşüşü tek başına güvenlik iyileşmesi anlamına gelmez.

Eğitim kayıtlarında her adımın kaybını o adım güncellenmeden önce hesaplayacağız. Bu sözleşme, kayıp dizisiyle ağırlık dizisinin bir adım kaymasını önler.

Kaynaklar: [PyTorch Autograd Mechanics](https://docs.pytorch.org/docs/stable/notes/autograd.html), [PyTorch SGD Optimizer](https://docs.pytorch.org/docs/stable/generated/torch.optim.SGD.html).
:::

::: tahmin Gradyan ve SGD adımını tahmin et
Üç çıktı satırını yaz:

```python
tahmin, hedef = [1, 3], [0, 1]
print(round(sum((a-b)**2 for a,b in zip(tahmin,hedef))/2, 6))
print(round(2*(1-0)/2, 6))
print(round(1 - 0.1 * 2, 6))
```

???

```cikti
2.5
1.0
0.8
```

İlk satır ortalama kare hatayı, ikinci satır ilk tahminin gradyanını, üçüncü satır SGD güncellemesini gösterir.
:::

::: gorev 1 · MSE kaybını ve gradyanı hesapla
`mse(tahmin, hedef)` işlevini yaz. İki girdi de üç adet sonlu, bool olmayan int/float içeren listedir; geçersiz veride `ValueError` yükselt.

Ortalama kare hatayı ve her tahmin için `2*(tahmin-hedef)/3` gradyanını hesapla. `{"kayip":K,"gradyan":G}` döndür; bütün sayıları altı ondalığa yuvarla. Girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-09")
```

```starter
from ai_temel_veri import json_yukle

def mse(tahmin,hedef):
    # KUSURLU BAŞLANGIÇ KODU: ortalama yerine toplam kayıp ve toplamın türevini kullanır.
    fark=[a-b for a,b in zip(tahmin,hedef)]
    return {"kayip":round(sum(x*x for x in fark),6),"gradyan":[round(2*x,6) for x in fark]}

v=json_yukle("veri/egitim.json")
print("Sentetik veri:",v)
print("MSE:",mse(v["tahmin"],v["hedef"]))
```

```test
def sozlesme(fn):
    try:
        if fn([1, 2, 3], [1, 2, 3]) != {"kayip": 0.0, "gradyan": [0.0, 0.0, 0.0]}:
            return False
        if fn([0, 0, 0], [1, 1, 1]) != {"kayip": 1.0, "gradyan": [-0.666667, -0.666667, -0.666667]}:
            return False
        if fn([2, 0, -2], [0, 2, 0]) != {"kayip": 4.0, "gradyan": [1.333333, -1.333333, -1.333333]} or fn([0, 0, 0], [1, 0, 0]) != {"kayip": 0.333333, "gradyan": [-0.666667, 0.0, 0.0]}:
            return False
        a,b=[1.,2.,4.],[0.,3.,1.]
        aa,bb=a[:],b[:]
        fn(a,b)
        if a!=aa or b!=bb:
            return False
        for args in [([float("nan"),0,0],[0,0,0]),([0,0,0],[float("inf"),0,0]),(None, [0, 0, 0]), ([0, 0], [0, 0]), ([0, True, 0], [0, 0, 0]), ([0, 0, 0], [0, 0]), ([0, 0, 0], [0, "0", 0])]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(mse), "MSE, gradyan işareti ve yuvarlama korunmalı")
def m_tahmin(t, h):
    return mse(list(reversed(t)), h)
def m_hedef(t, h):
    return mse(t, [x + 1 for x in h])
def m_boyut(t, h):
    return mse(t + [0], h + [0])
for ad, mutant in [("tahmini bozan", m_tahmin), ("hedefi bozan", m_hedef), ("boyutu bozan", m_boyut)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def mse(tahmin, hedef):
    import math
    def vektor(x):
        return isinstance(x, list) and len(x) == 3 and all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in x)
    if not vektor(tahmin) or not vektor(hedef):
        raise ValueError("vektör geçersiz")
    farklar = [a - b for a, b in zip(tahmin, hedef)]
    return {"kayip": round(sum(x * x for x in farklar) / 3, 6), "gradyan": [round(2 * x / 3, 6) for x in farklar]}
v=json_yukle("veri/egitim.json")
print("Sentetik veri:",v)
print("MSE:",mse(v["tahmin"],v["hedef"]))

```

```hint
Önce fark listesini çıkar. Kayıp karelerin ortalaması, gradyan ise her farkın `2/3` katıdır.
```
:::

::: gorev 2 · Üç ağırlıklı SGD güncellemesi yap
`sgd(agirliklar, gradyan, oran)` işlevini yaz. Ağırlıklar ve gradyan üç sonlu, bool olmayan int/float içeren listedir. Oran bool olmayan, `0 < oran <= 1` koşulundaki sayıdır. Geçersiz veride `ValueError` yükselt.

Her ağırlıktan `oran * gradyan` çıkar ve sonucu altı ondalığa yuvarla. Yeni liste döndür; girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-09")
```

```starter
from ai_temel_veri import json_yukle

def sgd(agirliklar,gradyan,oran):
    # KUSURLU BAŞLANGIÇ KODU: gradyanı çıkarmak yerine ekler.
    return [round(a+oran*g,6) for a,g in zip(agirliklar,gradyan)]

v=json_yukle("veri/egitim.json")
print("Sentetik veri:",v)
print("SGD:",sgd(v["agirliklar"],v["gradyan"],v["oran"]))
```

```test
def sozlesme(fn):
    try:
        if fn([1, 2, 3], [0.5, -0.5, 1], 0.1) != [0.95, 2.05, 2.9] or fn([1, 1, 1], [1, 1, 1], 1) != [0.0, 0.0, 0.0]:
            return False
        if fn([1, 1, 1], [1, 2, 3], 0.3) != [0.7, 0.4, 0.1] or fn([1, 1, 1], [1, 1, 1], 1 / 3) != [0.666667, 0.666667, 0.666667]:
            return False
        a,g=[1.,2.,3.],[0.5,-0.5,1.]
        aa,gg=a[:],g[:]
        out=fn(a,g,0.1)
        if a!=aa or g!=gg or out is a or out is g:
            return False
        for args in [([float("nan"),0,0],[0,0,0],0.1),([0,0,0],[float("inf"),0,0],0.1),(None, [0, 0, 0], 0.1), ([0, 0], [0, 0], 0.1), ([0, True, 0], [0, 0, 0], 0.1), ([0, "0", 0], [0, 0, 0], 0.1), ([0, 0, 0], [0, 0], 0.1), ([0, 0, 0], [0, 0, 0], 0), ([0, 0, 0], [0, 0, 0], 1.1), ([0, 0, 0], [0, 0, 0], True), ([0, 0, 0], [0, 0, 0], "0.1"), ([0, 0, 0], [0, 0, 0], float("nan"))]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(sgd), "SGD yönü, oran ve şema korunmalı")
def m_agirlik(a, g, o):
    return sgd(list(reversed(a)), g, o)
def m_gradyan(a, g, o):
    return sgd(a, list(reversed(g)), o)
def m_oran(a, g, o):
    return sgd(a, g, o * 2)
for ad, mutant in [("ağırlığı bozan", m_agirlik), ("gradyanı bozan", m_gradyan), ("oranı bozan", m_oran)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def sgd(agirliklar, gradyan, oran):
    import math
    def vektor(x):
        return isinstance(x, list) and len(x) == 3 and all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in x)
    if not vektor(agirliklar) or not vektor(gradyan):
        raise ValueError("vektör geçersiz")
    if not isinstance(oran, (int, float)) or isinstance(oran, bool) or not 0 < oran <= 1:
        raise ValueError("oran geçersiz")
    return [round(a - oran * g, 6) for a, g in zip(agirliklar, gradyan)]
v=json_yukle("veri/egitim.json")
print("Sentetik veri:",v)
print("SGD:",sgd(v["agirliklar"],v["gradyan"],v["oran"]))

```

```hint
Her ağırlık/gradyan çiftinde `a - oran * g` hesapla; güncellemeyi yeni listede topla.
```
:::

::: gorev 3 · Tek ağırlıklı eğitim izini üret
`egitim(x, y, baslangic, oran, adim)` işlevini yaz. x, y ve başlangıç sonlu, bool olmayan sayılardır; oran ikinci görevdeki biçimdedir. Adım bool olmayan 1–8 tamsayısıdır. Geçersiz veride `ValueError` yükselt.

Model `tahmin = agirlik*x` olsun. Her adımda güncelleme öncesi MSE kaybını (`tahmin-y` karesi), ardından gradyanı `2*x*(tahmin-y)` hesapla ve SGD uygula. `{"agirlik":W,"kayiplar":L}` döndür; ağırlığı ve her kaybı altı ondalığa yuvarla.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-09")
```

```starter
from ai_temel_veri import json_yukle

def egitim(x,y,baslangic,oran,adim):
    # KUSURLU BAŞLANGIÇ KODU: kaybı güncellemeden sonra kaydederek izi bir adım kaydırır.
    w=float(baslangic)
    kayiplar=[]
    for _ in range(adim):
        w-=oran*2*x*(w*x-y)
        kayiplar.append(round((w*x-y)**2,6))
    return {"agirlik":round(w,6),"kayiplar":kayiplar}

v=json_yukle("veri/egitim.json")
print("Sentetik veri:",v)
print("Eğitim:",egitim(**v["tek_agirlik"]))
```

```test
def sozlesme(fn):
    try:
        if fn(1, 2, 0, 0.1, 1) != {"agirlik": 0.4, "kayiplar": [4.0]}:
            return False
        if fn(1, 1, 0, 0.1, 3) != {"agirlik": 0.488, "kayiplar": [1.0, 0.64, 0.4096]}:
            return False
        if fn(0, 1, 2, 1, 1) != {"agirlik": 2.0, "kayiplar": [1.0]} or fn(1, 1, 0, 1 / 3, 2) != {"agirlik": 0.888889, "kayiplar": [1.0, 0.111111]} or len(fn(1, 1, 0, 0.1, 8)["kayiplar"]) != 8:
            return False
        if fn(1,1,0,0.5,2)!={"agirlik":1.0,"kayiplar":[1.0,0.0]}:
            return False
        for args in [(float("nan"),1,0,0.1,1),(1,float("inf"),0,0.1,1),(True, 1, 0, 0.1, 1), (1, None, 0, 0.1, 1), (1, 1, "0", 0.1, 1), (1, 1, 0, 0, 1), (1, 1, 0, 1.1, 1), (1, 1, 0, True, 1), (1, 1, 0, "0.1", 1), (1, 1, 0, float("nan"), 1), (1, 1, 0, 0.1, 0), (1, 1, 0, 0.1, 9), (1, 1, 0, 0.1, True), (1, 1, 0, 0.1, "1")]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
eq(egitim(0, 2, -3, 0.5, 3), {"agirlik": -3.0, "kayiplar": [4.0, 4.0, 4.0]},
   "Sıfır girdide kayıp sıfır olmayabilir ve gradyan sıfırdır")
eq(egitim(1, 0, 2, 1, 3), {"agirlik": -2.0, "kayiplar": [4.0, 4.0, 4.0]},
   "Büyük adım ağırlığı sıfırın ötesine taşır ve kayıp salınım boyunca sabit kalır")
eq(egitim(-2, 4, 0, 0.125, 2), {"agirlik": -2.0, "kayiplar": [16.0, 0.0]},
   "Negatif girdide zincir kuralı ağırlığı negatif yöne günceller")
ok(sozlesme(egitim), "eğitim sırası, kayıp izi ve adım sınırı korunmalı")
def m_x(x, y, b, o, a):
    return egitim(x * 2, y, b, o, a)
def m_y(x, y, b, o, a):
    return egitim(x, y + 1, b, o, a)
def m_adim(x, y, b, o, a):
    return egitim(x, y, b, o, 1)
for ad, mutant in [("x değerini bozan", m_x), ("hedefi bozan", m_y), ("adımı bozan", m_adim)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def egitim(x, y, baslangic, oran, adim):
    import math
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) for v in (x, y, baslangic)):
        raise ValueError("sayı geçersiz")
    if not isinstance(oran, (int, float)) or isinstance(oran, bool) or not 0 < oran <= 1:
        raise ValueError("oran geçersiz")
    if not isinstance(adim, int) or isinstance(adim, bool) or not 1 <= adim <= 8:
        raise ValueError("adım geçersiz")
    agirlik = float(baslangic)
    kayiplar = []
    for _ in range(adim):
        fark = agirlik * x - y
        kayiplar.append(round(fark * fark, 6))
        agirlik -= oran * 2 * x * fark
    return {"agirlik": round(agirlik, 6), "kayiplar": kayiplar}
v=json_yukle("veri/egitim.json")
print("Sentetik veri:",v)
print("Eğitim:",egitim(**v["tek_agirlik"]))

```

```hint
Döngüde önce farkı ve kaybı kaydet; sonra aynı farkı kullanarak ağırlığı güncelle.
```
:::

::: anlat Gerçek deney: formülün yanında autograd ve optimizer çalışsın
Önceki tek ağırlıklı döngü SGD'nin matematiğini gösterdi. Bu görevde gerçek `torch.nn.Linear(2,1)` modeli, `torch.nn.functional.mse_loss`, `loss.backward()` ve `torch.optim.SGD.step()` çalıştırılır. Veri sentetik, hesap CPU ve float64'tür; önceden eğitilmiş model veya indirme gerekmez.

PyTorch gradyanları varsayılan olarak biriktirir. Her eğitim adımında optimizer gradyanlarını temizle, tahmini yap, **güncellemeden önceki** ortalama kaybı kaydet, geriye türev al ve optimizer'ı ilerlet. `zero_grad` unutulursa önceki adımın gradyanı bir sonraki güncellemeye karışır. `no_grad` eğitimde backward hesabını engeller; yalnız son ağırlıkları raporlarken veya değerlendirmede kullanılır.

Test yalnız düşen kayba bakmaz: gerçek parametre gradyan hookları ve optimizer adım hookları doğru sayıda backward/step çalıştığını gözlemler. Son ağırlıkları ayrıca autograd veya optimizer kullanmayan analitik MSE hesabıyla karşılaştırır. Eğitim kaybının düşmesi, üretimde doğruluk, genelleme veya güvenlik kanıtı değildir.
:::

::: gorev Gerçek deney · Gerçek backward ve SGD eğitim döngüsü
`torch_egit(model, optimizer, x, y, adim)` işlevini yaz. Laboratuvar sana bağımsız, CPU'da float64 `Linear(2,1,bias=True)` modeli ve onun momentum/weight-decay içermeyen SGD optimizer'ını verir. `x`, N×2; `y`, N×1 tensörüdür. Bu dört girdinin uygun kurulduğunu varsayabilirsin; bunları yeniden oluşturma veya verilen optimizer yerine başka optimizer kullanma.

`adim` bool olmayan 1–8 aralığında int olmalı; diğer değerlerde modeli değiştirmeden `ValueError` yükselt.

Her adımda sırasıyla:

1. `optimizer.zero_grad(set_to_none=True)` çağır.
2. `model(x)` tahminlerinden `torch.nn.functional.mse_loss(..., y, reduction="mean")` hesapla.
3. Güncelleme öncesi kaybı Python float olarak kaydet.
4. `loss.backward()` ve `optimizer.step()` çağır.

Tam `{"kayiplar": [...], "agirlik": [w0,w1], "bias": b}` sözlüğü döndür. Ağırlıklar ve bias **son** güncellemeden sonradır; sayılar Python float, yuvarlanmamış olsun. `x` ve `y` değiştirilmez. Verilen model gerçekten eğitilmiş kalmalı; yalnız doğru görünümlü rapor döndürmek yetmez. Başka bir modelin parametrelerini veya optimizer ayarlarını değiştirme.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 120
```

```starter
import ai_lab

def torch_egit(model, optimizer, x, y, adim):
    return {}

if ai_lab.CALISTIR:
    import torch
    model = torch.nn.Linear(2, 1, dtype=torch.float64)
    optimizer = torch.optim.SGD(model.parameters(), lr=0.05)
    x = torch.tensor([[0.,1.],[1.,0.],[1.,1.]], dtype=torch.float64)
    y = torch.tensor([[1.],[2.],[3.]], dtype=torch.float64)
    print(torch_egit(model, optimizer, x, y, 4))
```

```test
import copy
import random
import ai_lab
sonuclar=[]
def kontrol(c,mesaj):
    sonuclar.append(bool(c))
    return ok(c,mesaj)
import ast
_yasak=("referans_egit","kanit_yaz")
sorun=ai_lab.kod_denetimi(src,yasak=_yasak)
for n in ast.walk(ast.parse(src)):
    if isinstance(n,ast.ImportFrom) and any(a.name in _yasak or a.name=="*" for a in n.names):
        sorun.append("referans importu yasak")
if not kontrol(not sorun,"Kendi autograd eğitim işlevini yaz: "+"; ".join(sorun)):
    stop()
fn=need("torch_egit")
try:
    import torch
except ImportError as e:
    kontrol(False,"GERÇEK TORCH YOK: "+str(e))
    stop()

rng=random.SystemRandom()
seed=rng.randrange(1,2**31)
r=random.Random(seed)
vakalar=[]
for n,adim,lr in [(3,1,0.03),(5,3,0.08),(6,5,0.02),(4,8,0.05)]:
    x=[[r.uniform(-1,1),r.uniform(-1,1)] for _ in range(n)]
    y=[[1.5*a-0.6*b+0.4] for a,b in x]
    vakalar.append({"x":x,"y":y,"agirlik":[r.uniform(-0.7,0.7),r.uniform(-0.7,0.7)],
                    "bias":r.uniform(-0.3,0.3),"lr":lr,"adim":adim})

def kur(v):
    # Model oluştururken küresel RNG durumunu değiştirme.
    with torch.random.fork_rng(devices=[]):
        m=torch.nn.Linear(2,1,bias=True,dtype=torch.float64)
    with torch.no_grad():
        m.weight.copy_(torch.tensor([v["agirlik"]],dtype=torch.float64))
        m.bias.fill_(v["bias"])
    opt=torch.optim.SGD(m.parameters(),lr=v["lr"],momentum=0,weight_decay=0)
    return m,opt,torch.tensor(v["x"],dtype=torch.float64),torch.tensor(v["y"],dtype=torch.float64)

def analitik(v):
    x=torch.tensor(v["x"],dtype=torch.float64)
    y=torch.tensor(v["y"],dtype=torch.float64)
    w=torch.tensor(v["agirlik"],dtype=torch.float64).reshape(2,1)
    b=torch.tensor(v["bias"],dtype=torch.float64)
    losses=[]
    for _ in range(v["adim"]):
        e=x@w+b-y
        losses.append(float((e*e).mean().item()))
        dw=2*x.T@e/len(x)
        db=2*e.mean()
        w=w-v["lr"]*dw
        b=b-v["lr"]*db
    return {"kayiplar":losses,"agirlik":w.flatten().tolist(),"bias":float(b.item())}
beklenen=[analitik(v) for v in vakalar]
def ayni(a,b):
    if not isinstance(a,dict) or set(a)!=set(b) or type(a["bias"]) is not float:
        return False
    for k in ["kayiplar","agirlik"]:
        if not isinstance(a[k],list) or len(a[k])!=len(b[k]) or any(type(x) is not float for x in a[k]):
            return False
        x,y=torch.tensor(a[k],dtype=torch.float64),torch.tensor(b[k],dtype=torch.float64)
        if not bool(torch.isfinite(x).all()) or not torch.allclose(x,y,atol=1e-9,rtol=1e-8):
            return False
    return abs(a["bias"]-b["bias"])<=1e-9

def sozlesme(f):
    try:
        for v,ref in zip(vakalar,beklenen):
            m,opt,x,y=kur(v)
            eski_x,eski_y=x.clone(),y.clone()
            grad_w,grad_b,steps=[],[],[]
            hw=m.weight.register_hook(lambda g:grad_w.append(g.detach().clone()))
            hb=m.bias.register_hook(lambda g:grad_b.append(g.detach().clone()))
            hs=opt.register_step_post_hook(lambda *args:steps.append(True))
            try:
                a=f(m,opt,x,y,v["adim"])
            finally:
                hw.remove();hb.remove();hs.remove()
            if not ayni(a,ref) or len(grad_w)!=v["adim"] or len(grad_b)!=v["adim"] or len(steps)!=v["adim"]:
                return False
            if not torch.equal(x,eski_x) or not torch.equal(y,eski_y):
                return False
            if not torch.allclose(m.weight.detach().flatten(),torch.tensor(ref["agirlik"],dtype=torch.float64),atol=1e-9,rtol=1e-8) or abs(m.bias.item()-ref["bias"])>1e-9:
                return False
            if opt.param_groups[0]["lr"]!=v["lr"]:
                return False
        for n in [0,9,True,1.0,None]:
            m,opt,x,y=kur(vakalar[0])
            w,b=m.weight.detach().clone(),m.bias.detach().clone()
            try:
                f(m,opt,x,y,n)
                return False
            except ValueError:
                if not torch.equal(w,m.weight) or not torch.equal(b,m.bias):
                    return False
        return True
    except Exception:
        return False
kontrol(sozlesme(fn),"gerçek autograd gradyanları, SGD adımları, analitik ağırlık ve güncelleme öncesi kayıp doğru")

def hata(tur):
    def f(m,opt,x,y,n):
        if type(n) is not int or not 1<=n<=8:
            raise ValueError("adım")
        losses=[]
        for _ in range(n):
            if tur!="gradyan_birikimi":
                opt.zero_grad(set_to_none=True)
            loss=torch.nn.functional.mse_loss(m(x),y,reduction="sum" if tur=="toplam" else "mean")
            losses.append(float(loss.item()))
            if tur!="backward_yok":
                loss.backward()
            if tur!="step_yok":
                opt.step()
        return {"kayiplar":losses,"agirlik":m.weight.detach().flatten().tolist(),"bias":float(m.bias.item())}
    return f
for ad,mutant in [("boş kod/işlev",None),("boş sözlük",lambda *a:{}),
                  ("ezber sonuç",lambda *a:copy.deepcopy(beklenen[0])),
                  ("zero_grad unutulmuş",hata("gradyan_birikimi")),
                  ("ortalama yerine toplam kayıp",hata("toplam")),
                  ("backward çağrılmıyor",hata("backward_yok")),
                  ("optimizer adımı yok",hata("step_yok"))]:
    kontrol(not sozlesme(mutant),"hatalı çözüm reddedilmeli: "+ad)

ciktilar=[]
if all(sonuclar):
    for v in vakalar:
        m,opt,x,y=kur(v)
        ciktilar.append(fn(m,opt,x,y,v["adim"]))
if not all(sonuclar):
    stop()
ai_lab.kanit_yaz("temel-09-egitim",{
    "kaynak":"gercek","kabul":all(sonuclar),
    "model_bilgisi":{"model":"yerelde oluşturulan Linear(2,1,bias=True)","arac":"torch","surum":torch.__version__,"dtype":"float64","aygit":"cpu"},
    "ayarlar":{"veri_tohumu":seed,"vakalar":vakalar,"optimizer":"SGD momentum=0 weight_decay=0","kayip":"mean MSE"},
    "ciktilar":ciktilar,"gozlem":"parametre gradyan hook'ları ve gerçek optimizer step-post-hook",
    "sinir":"sentetik regresyon eğitimi; dil modeli fine-tuning veya genelleme/güvenlik kabulü değildir",
    "temizlik":"kalıcı süreç, model indirme veya dış sunucu yok"})
for v,d in zip(vakalar,ciktilar):
    print("gerçek SGD",v["adim"],"adım, lr",v["lr"],"kayıplar",d["kayiplar"],"son ağırlık",d["agirlik"],"bias",d["bias"])
```

```solution
import ai_lab
import torch

def torch_egit(model, optimizer, x, y, adim):
    if type(adim) is not int or not 1<=adim<=8:
        raise ValueError("adım 1-8 tamsayı olmalı")
    kayiplar=[]
    for _ in range(adim):
        optimizer.zero_grad(set_to_none=True)
        loss=torch.nn.functional.mse_loss(model(x),y,reduction="mean")
        kayiplar.append(float(loss.item()))
        loss.backward()
        optimizer.step()
    return {"kayiplar":kayiplar,"agirlik":model.weight.detach().flatten().tolist(),"bias":float(model.bias.item())}

if ai_lab.CALISTIR:
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(2026)
        model=torch.nn.Linear(2,1,dtype=torch.float64)
    optimizer=torch.optim.SGD(model.parameters(),lr=0.05)
    x=torch.tensor([[0.,1.],[1.,0.],[1.,1.]],dtype=torch.float64)
    y=torch.tensor([[1.],[2.],[3.]],dtype=torch.float64)
    print(torch_egit(model,optimizer,x,y,4))
```

```hint
`loss.item()` kaydı `optimizer.step()` öncesinde alınır. Sonuç vektörü `model.weight.detach().flatten().tolist()` ile Python float listesine çevrilir. Gradyanları temizlemeden birkaç adım çalıştırıp neden sonucun değiştiğini Çalıştır'da gözlemleyebilirsin.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Dört adımlı çekirdek döngü (30 sn).** "Her eğitim adımı aynı sırayla yürür: `zero_grad` ile eski birikimi sil, ileri geçişle kaybı ölç, `backward` ile $\nabla_w L$ türevini üret ve `step` ile ağırlığı $-\eta \nabla_w L$ yönünde güncelle."
2. **`zero_grad` ve adım sırası tuzağı (35 sn).** "PyTorch gradyanları varsayılan olarak toplar; `zero_grad` unutulursa eski adımların türevleri yeni adıma karışır, kayıp `step` sonrasında kaydedilirse günlük bir adım kayar."
3. **Öğrenme oranı (`learning rate`) dengesi (30 sn).** "Çok küçük $\eta$ eğitimi dondurur, çok büyük $\eta$ minimumun üzerinden atlayarak kaybı ıraksatır."
4. **Soru (25 sn).** "Gradyan biriktirme (`gradient accumulation`) yapmak istediğimizde `zero_grad()` çağrısını her mikro-batch yerine kaç adımda bir çalıştırırız?"
:::
