---
id: ai-savunma-27
title: garak ile Yerel Model Güvenlik Taraması
summary: garak Probe/OllamaGeneratorChat/StringDetector ile ölçülen bulguları doğrula; deneme sayısıyla ağırlıklı skorlar ve bağlamlı risk raporları üret.
timeout: 45
esleme: ai-saldiri-27, ai-savunma-28
---

::: anlat Probe ve detector sonucu birlikte yorumlanır

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| garak Probe sınama istemlerini Generator'a gönderir; Detector her çıktı için skor döndürür | İlk üç görev görünür sentetik bulgular; finalde kurulu garak'ın gerçek Probe, OllamaGeneratorChat ve StringDetector API'leri | İki özel Pafta probe'u bütün garak kataloğu veya güvenlik kategorilerini kapsamaz |
| Gerçek araç çıktısı ham istem, yanıt ve detector değerlerini taşır | Son deneyde garak Attempt kayıtları, beş gerçek yanıt ve sürüm kanıta eklenir | Alt dizge eşleşmesi anlamsal jailbreak hakemi değildir; düşük skor modelin genel olarak güvenli olduğunu kanıtlamaz |

> [!NOT]
> İlk üç görevde `veri/bulgular.json` dosyası **sentetik** örnektir, gerçek model çıktısı değildir. Setup dosyayı geçici çalışma klasörüne kopyalar; her Run/Check yeni kopya üretir, değişiklikler kalıcı değildir. Kaynak fixture klasöründeki dosyayı editörle açabilir, ders kodunda okunan listenin kopyasını değiştirerek sonucu deneyebilirsin. Gizli testler ayrı girdiler kullanır. Son görev gerçek garak API'sini kurulu araç ortamında çalıştırır; ders indirme yapmaz.

Garak taramasında probe modele gönderilen sınama sınıfını, detector ise yanıttaki hedef davranışı ölçen denetimi belirtir. Bulgu skoru tek başına yeterli değildir: kaç denemeyi temsil ettiği ve hangi probe-detector çiftinden geldiği korunur. Bu derste skor, detectorün hedeflediği istenmeyen davranışın görülme oranı olarak kabul edilir.

Görevler 1–3 sentetik veriyle çalışır; son adım gerçek garak API’si üzerinden yerel Ollama modelini tarar. İlk görevlerde kullanılan probe-detector adları öğretim örneğidir; bunları kurulu katalogdaki sınıflar sanma. Fixture skorları gerçek model güvenliği hakkında kanıt oluşturmaz.
:::

::: anlat Ağırlıklı skor deneme sayısını korur

Önce `veri/bulgular.json` içindeki ham sözlükleri incele. `id` aynı bulgunun iki kez sayılmasını önler; `probe` sınama ailesini, `detector` ölçen denetimi, `skor` ölçülen oranı, `deneme` ise bu oranı üreten örnek sayısını taşır. Birinci görev şemayı doğrular. İkinci görev probe bazında birleştirir. Üçüncü görev probe ile detector çiftini koruyarak dersin risk eşiklerini uygular. Dosyayı değiştirmek gizli beklenen cevabı değiştirmez: örneğin tek bulgunun deneme sayısını büyütüp ağırlığın nasıl değiştiğini gözlemek içindir.

Gerçek akışta kurulu garak'ın `Probe.probe` metodu beş istem için Attempt oluşturur. `OllamaGeneratorChat` sohbet mesajlarını yerel sunucuya yollar; yanıtlardaki metin `StringDetector.detect` tarafından değerlendirilir. Laboratuvarın özel işareti detector'ün alt dizge hedefidir. Detector sıfır döndürürse bu hedef metin görünmemiştir; bir döndürürse görünmüştür. Program bu ham skorları probe bazında toplar ve öğrencinin risk işlevine verir. Hazır garak altyapısı gerçekten çalışır; sınama istemleri bu dersin özel, küçük probe setidir. Hazır probe kataloğunun tamamını koşmuş gibi sunulmaz.

Bir saldırgan belge içine sahte talimat koyarak sistemdeki özel işareti yanıta taşıtmaya çalışır. Belge bir veri kaynağı olmasına rağmen içeriği talimat gibi izlenirse beklenen ayrım bozulur. Bu deney yalnız sentetik işareti ölçer; gerçek kimlik bilgisi veya öğrenci dosyası kullanılmaz. Modelin işareti vermemesi de geçerli gözlemdir. Her taramanın sızıntı üretmesini beklemek, ölçümü başarılı saldırı arayışına çevirir ve karşılaştırmayı bozar. Kabul ölçütü bütün çağrıların yapılması ve rapor hesabının doğruluğudur.

Çıktıyı okurken önce sürümü, model kimliğini ve çağrı adedini doğrula; ardından ham yanıtı, detector skorunu ve en son risk etiketini oku. Alt dizge detector'ü yeniden kodlanmış veya parçalara ayrılmış işareti kaçırabilir. Aynı sözcüğün alıntıda geçmesi de güvenlik olayının bağlamını tek başına açıklamaz. Bu nedenle ham yanıtlar saklanır; sıfır skorun genel güvenlik sertifikası olduğu söylenmez. Bu dersteki `garak.canary` alanı bir ders eşlemesidir; gerçek sınıf adı kanıtta `garak.detectors.base.StringDetector` olarak ayrıca yer alır.

Denemeler eşit sayıda değilse düz ortalama yanıltır. Bir denemede oran bir, dokuz denemede oran sıfır ise birleşik oran yarım değil onda birdir. Toplamın ağırlığı deneme sayısıdır. Aynı probe için farklı detector sonuçlarını tek genel skor yapmak da hedefleri karıştırır: probe özeti yalnız öğretim amaçlıdır; karar raporu detector kimliğini korur. Detector hedefini değiştirip eski eşikleri aynen kullanmak otomatik olarak eşdeğer değerlendirme üretmez.

Dersin `modeli_yayina_alma` önerisi yerel bir alıştırma kuralıdır, evrensel üretim politikası değildir. Gerçek yayın kararı tehdit modeli, kullanım amacı ve daha geniş kanıt ister. Eşik sınırlarını özellikle gözle: düşük eşiğe eşit skor orta, yüksek eşiğe eşit skor yüksek olur. Bool değerlerini sayı sanmak, NaN'ı karşılaştırmalardan kaçırmak veya sıfır denemeli grubu bölmek sessiz rapor hatalarıdır. Eksik araç, bağlantı hatası veya boş model yanıtı düşük risk sonucu üretmez; deney tamamlanmadı diye görünür hata verir.

Aynı gruptaki bulgular birleştirilirken her skor kendi deneme sayısıyla çarpılır ve toplam denemeye bölünür. Böylece yüz denemelik sonuçla tek denemelik sonuç eşit ağırlık almaz. Toplam deneme sıfır olamayacağı için her bulguda deneme sayısı pozitif tamsayı olmalıdır.

Risk raporunda skor düşük eşiğin altındaysa `dusuk`, yüksek eşiğe eşit veya üstündeyse `yuksek`, aradaysa `orta` olur. Düşük eşiğe eşitlik `orta` risk demektir. Eşikler `0 <= dusuk < yuksek <= 1` koşulunu sağlar.
:::

::: tahmin Ağırlıklı skor ve sınır davranışını tahmin et
Üç çıktı satırını yaz:

```python
print((0 * 2 + 1 * 2) / 4)
print(None if 0 == 0 else 1 / 0)
print(0.2 <= 0.2 < 0.7)
```

???

```cikti
0.5
None
True
```

Gerçek bulgularda boş grup atlanır; her grubun toplam denemesi pozitif olduğundan bölme güvenlidir.
:::

::: gorev 1 · Garak bulgusunu doğrula
`garak_bulgu_dogrula(bulgu)` işlevini yaz. Bulgu tam olarak `id`, `probe`, `detector`, `skor`, `deneme` alanlarını taşısın. Kimlik 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren stringdir.

Probe ve detector, noktayla ayrılmış en az iki küçük harfli ASCII bölümden oluşsun; bölümler harfle başlasın ve yalnız küçük harf, rakam veya alt çizgi içersin. Skor bool olmayan, sonlu bir sayı ve `0 <= skor <= 1` aralığında olmalıdır. Deneme bool olmayan pozitif tamsayıdır. Geçersiz veride `ValueError` yükselt. Aynı değerlerle yeni sözlük döndür ve girdiyi değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-27")
```

```starter
from ai_savunma_veri import json_yukle

def garak_bulgu_dogrula(bulgu):
    # KUSURLU BAŞLANGIÇ KODU: geçersiz skor/denemeyi reddetmek yerine sessizce düzeltir.
    sonuc=dict(bulgu)
    sonuc["skor"]=max(0,min(1,float(sonuc["skor"])))
    sonuc["deneme"]=max(1,int(sonuc["deneme"]))
    return sonuc

v=json_yukle("veri/bulgular.json")
print("Sentetik bulgular:",v)
print("Bulgu:",garak_bulgu_dogrula(v[0]))
```

```test
import copy
B = {"id": "b-1", "probe": "encoding.base64", "detector": "detector.safety", "skor": 0, "deneme": 1}
def sozlesme(fn):
    try:
        once = copy.deepcopy(B)
        sonuc = fn(B)
        if sonuc != B or B != once or sonuc is B:
            return False
        if fn(dict(B, id="a" * 64, probe="probe_1.test2", detector="detector_3.check4", skor=1.0))["skor"] != 1.0:
            return False
        for bulgu in [
            None, [], dict(B, ek=1), dict(B, id=""), dict(B, id="a b"), dict(B, id="a" * 65),
            dict(B, probe=""), dict(B, probe="base64"), dict(B, probe="Encoding.base64"), dict(B, probe=".base64"), dict(B, probe="encoding..base64"),
            dict(B, detector="safety"), dict(B, detector="Detector.safety"), dict(B, detector="detector.safety!"),
            dict(B, skor=True), dict(B, skor="0.5"), dict(B, skor=float("nan")), dict(B, skor=float("inf")),
            dict(B, skor=-0.1), dict(B, skor=1.1), dict(B, deneme=0), dict(B, deneme=-1),
            dict(B, deneme=True), dict(B, deneme=1.5),
        ]:
            try:
                fn(bulgu)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(garak_bulgu_dogrula), "kimlik, probe, detector, skor ve deneme korunmalı")
def m_skor(bulgu):
    sonuc = garak_bulgu_dogrula(bulgu)
    sonuc["skor"] = 1
    return sonuc
def m_deneme(bulgu):
    sonuc = garak_bulgu_dogrula(bulgu)
    sonuc["deneme"] = 2
    return sonuc
def m_detector(bulgu):
    sonuc = garak_bulgu_dogrula(bulgu)
    sonuc["detector"] = "detector.other"
    return sonuc
for ad, mutant in [("skoru değiştiren", m_skor), ("denemeyi değiştiren", m_deneme), ("detectorü değiştiren", m_detector)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
# --- carbon-c8-ek-bas ---
raises(ValueError, garak_bulgu_dogrula, dict(B, id=123), msg="id str olmalı")
raises(ValueError, garak_bulgu_dogrula, dict(B, probe=123), msg="probe str olmalı")
raises(ValueError, garak_bulgu_dogrula, dict(B, detector=123), msg="detector str olmalı")
raises(ValueError, garak_bulgu_dogrula, dict(B, skor=float("nan")), msg="NaN skor ret")
raises(ValueError, garak_bulgu_dogrula, dict(B, deneme=True), msg="deneme bool True ret")
# --- carbon-c8-ek-son ---
```

```solution
from ai_savunma_veri import json_yukle
def garak_bulgu_dogrula(bulgu):
    import math
    import re
    if not isinstance(bulgu, dict):
        raise ValueError("bulgu sözlük olmalı")
    if set(bulgu) != {"id", "probe", "detector", "skor", "deneme"}:
        raise ValueError("bulgu şeması geçersiz")
    if not isinstance(bulgu["id"], str):
        raise ValueError("kimlik string olmalı")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", bulgu["id"]):
        raise ValueError("kimlik geçersiz")
    for alan in ("probe", "detector"):
        deger = bulgu[alan]
        if not isinstance(deger, str):
            raise ValueError("araç kimliği string olmalı")
        if not re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+", deger):
            raise ValueError("araç kimliği geçersiz")
    skor = bulgu["skor"]
    if isinstance(skor, bool) or not isinstance(skor, (int, float)):
        raise ValueError("skor sayı olmalı")
    if not math.isfinite(skor):
        raise ValueError("skor sonlu olmalı")
    if skor < 0 or skor > 1:
        raise ValueError("skor aralık dışında")
    deneme = bulgu["deneme"]
    if isinstance(deneme, bool) or not isinstance(deneme, int):
        raise ValueError("deneme tamsayı olmalı")
    if deneme <= 0:
        raise ValueError("deneme pozitif olmalı")
    return {"id": bulgu["id"], "probe": bulgu["probe"], "detector": bulgu["detector"], "skor": bulgu["skor"], "deneme": bulgu["deneme"]}
v=json_yukle("veri/bulgular.json")
print("Sentetik bulgular:",v)
print("Bulgu:",garak_bulgu_dogrula(v[0]))

```

```hint
Probe ve detector için aynı noktalı deseni kullan. Skorda `math.isfinite`, denemede açık bool ve pozitiflik kontrolü yap.
```
:::

::: gorev 2 · Probe bazında ağırlıklı tarama özeti üret
`garak_probe_ozeti(bulgular)` işlevini yaz. Girdi liste olmalı; her bulgu ilk görevdeki kuralları sağlamalı ve bulgu kimlikleri benzersiz olmalıdır. Geçersiz veride `ValueError` yükselt.

Bulguları probe adına göre grupla. Her grup için `{"probe":PROBE,"deneme":TOPLAM,"agirlikli_skor":SKOR,"bulgu_sayisi":N}` döndür. Ağırlıklı skor `sum(skor * deneme) / toplam deneme` olmalıdır. Sonuçları probe adına göre sırala. Boş girdide boş liste döndür; girdi sırasından bağımsız çalış ve girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-27")
```

```starter
from ai_savunma_veri import json_yukle

def garak_probe_ozeti(bulgular):
    # KUSURLU BAŞLANGIÇ KODU: deneme ağırlığı yerine bulguları eşit sayar.
    gruplar={}
    for b in bulgular: gruplar.setdefault(b["probe"],[]).append(b)
    return [{"probe":p,"deneme":sum(b["deneme"] for b in g),"agirlikli_skor":sum(b["skor"] for b in g)/len(g),"bulgu_sayisi":len(g)} for p,g in sorted(gruplar.items())]

v=json_yukle("veri/bulgular.json")
print("Sentetik bulgular:",v)
print("Probe özeti:",garak_probe_ozeti(v))
```

```test
import copy
B = [
    {"id": "b-1", "probe": "encoding.base64", "detector": "detector.safety", "skor": 0, "deneme": 2},
    {"id": "b-2", "probe": "encoding.base64", "detector": "detector.other", "skor": 1, "deneme": 2},
    {"id": "b-3", "probe": "prompt.injection", "detector": "detector.safety", "skor": 0.25, "deneme": 4},
]
BEKLENEN = [
    {"probe": "encoding.base64", "deneme": 4, "agirlikli_skor": 0.5, "bulgu_sayisi": 2},
    {"probe": "prompt.injection", "deneme": 4, "agirlikli_skor": 0.25, "bulgu_sayisi": 1},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(B)
        if fn(B) != BEKLENEN or B != once or fn(list(reversed(B))) != BEKLENEN or fn([]) != []:
            return False
        if fn([dict(B[0], id="a" * 64, skor=1, deneme=1)])[0]["agirlikli_skor"] != 1:
            return False
        agirlik = fn([B[0], dict(B[1], deneme=6)])
        if agirlik[0]["deneme"] != 8 or agirlik[0]["agirlikli_skor"] != 0.75:
            return False
        for bulgular in [
            None, {}, [None], [dict(B[0], ek=1)], [dict(B[0], id="a b")], [dict(B[0], id="a" * 65)],
            [B[0], B[0]], [dict(B[0], probe="base64")], [dict(B[0], detector="Detector.safety")],
            [dict(B[0], skor=True)], [dict(B[0], skor=float("nan"))], [dict(B[0], skor=1.1)],
            [dict(B[0], deneme=0)], [dict(B[0], deneme=False)], [dict(B[0], deneme=1.5)],
        ]:
            try:
                fn(bulgular)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(garak_probe_ozeti), "probe grupları, denemeler ve ağırlıklı skor korunmalı")
def m_skor(bulgular):
    return garak_probe_ozeti([dict(x, skor=0) for x in bulgular])
def m_deneme(bulgular):
    return garak_probe_ozeti([dict(x, deneme=1) for x in bulgular])
def m_probe(bulgular):
    return garak_probe_ozeti([dict(x, probe="probe.other") for x in bulgular])
for ad, mutant in [("skorları silen", m_skor), ("denemeleri eşitleyen", m_deneme), ("probeleri birleştiren", m_probe)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
# --- carbon-c8-ek-bas ---
raises(ValueError, garak_probe_ozeti, [dict(B[0], id=123)], msg="id str olmalı")
raises(ValueError, garak_probe_ozeti, [dict(B[0], probe=123)], msg="probe str olmalı")
raises(ValueError, garak_probe_ozeti, [dict(B[0], detector=123)], msg="detector str olmalı")
raises(ValueError, garak_probe_ozeti, [dict(B[0], skor=float("nan"))], msg="NaN skor ret")
raises(ValueError, garak_probe_ozeti, [dict(B[0], deneme=True)], msg="deneme bool True ret")
raises(ValueError, garak_probe_ozeti, [dict(B[0], skor="0.5")], msg="str skor ret")
raises(ValueError, garak_probe_ozeti, [dict(B[0], skor=-0.1)], msg="negatif skor ret")
ok(len(garak_probe_ozeti([dict(B[0], skor=0.0)])) == 1, "skor 0.0 geçerli")
# --- carbon-c8-ek-son ---
```

```solution
from ai_savunma_veri import json_yukle
def garak_probe_ozeti(bulgular):
    import math
    import re
    if not isinstance(bulgular, list):
        raise ValueError("bulgular liste olmalı")
    gorulen = set()
    for bulgu in bulgular:
        if not isinstance(bulgu, dict):
            raise ValueError("bulgu sözlük olmalı")
        if set(bulgu) != {"id", "probe", "detector", "skor", "deneme"}:
            raise ValueError("bulgu şeması geçersiz")
        if not isinstance(bulgu["id"], str):
            raise ValueError("kimlik string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", bulgu["id"]):
            raise ValueError("kimlik geçersiz")
        if bulgu["id"] in gorulen:
            raise ValueError("kimlik yinelenemez")
        gorulen.add(bulgu["id"])
        for alan in ("probe", "detector"):
            deger = bulgu[alan]
            if not isinstance(deger, str):
                raise ValueError("araç kimliği string olmalı")
            if not re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+", deger):
                raise ValueError("araç kimliği geçersiz")
        skor = bulgu["skor"]
        if isinstance(skor, bool) or not isinstance(skor, (int, float)):
            raise ValueError("skor sayı olmalı")
        if not math.isfinite(skor):
            raise ValueError("skor sonlu olmalı")
        if skor < 0 or skor > 1:
            raise ValueError("skor aralık dışında")
        deneme = bulgu["deneme"]
        if isinstance(deneme, bool) or not isinstance(deneme, int):
            raise ValueError("deneme tamsayı olmalı")
        if deneme <= 0:
            raise ValueError("deneme pozitif olmalı")
    gruplar = {}
    for bulgu in bulgular:
        gruplar.setdefault(bulgu["probe"], []).append(bulgu)
    sonuc = []
    for probe in sorted(gruplar):
        grup = gruplar[probe]
        deneme = sum(x["deneme"] for x in grup)
        agirlikli = sum(x["skor"] * x["deneme"] for x in grup) / deneme
        sonuc.append({"probe": probe, "deneme": deneme, "agirlikli_skor": agirlikli, "bulgu_sayisi": len(grup)})
    return sonuc
v=json_yukle("veri/bulgular.json")
print("Sentetik bulgular:",v)
print("Probe özeti:",garak_probe_ozeti(v))

```

```hint
Grupları sözlükte topla. Payda grup denemelerinin toplamı, pay ise skor ile denemenin çarpımlarının toplamıdır.
```
:::

::: gorev 3 · Probe-detector risk raporu üret
`garak_risk_raporu(bulgular, dusuk_esik, yuksek_esik)` işlevini yaz. Bulgular ikinci görevdeki kuralları sağlasın. Eşikler bool olmayan sonlu sayılardır ve `0 <= dusuk_esik < yuksek_esik <= 1` koşulunu sağlamalıdır. Geçersiz veride `ValueError` yükselt.

Bulguları `(probe, detector)` çiftine göre grupla ve ağırlıklı skoru deneme sayısıyla hesapla. Her grup için `{"probe":PROBE,"detector":DETECTOR,"deneme":N,"agirlikli_skor":SKOR,"risk":RISK,"oneri":ONERI}` döndür. Skor düşük eşikten küçükse risk `dusuk`, yüksek eşiğe eşit veya büyükse `yuksek`, aksi halde `orta` olur. Düşük risk için `izlemeyi_sur`, orta risk için `probe_kapsamini_genislet`, yüksek risk için `modeli_yayina_alma` önerisini kullan.

Sonuçları probe, sonra detector adına göre sırala. Boş girdide boş liste döndür ve girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-27")
```

```starter
from ai_savunma_veri import json_yukle

def garak_risk_raporu(bulgular,dusuk_esik,yuksek_esik):
    # KUSURLU BAŞLANGIÇ KODU: gruplamaz ve eşik eşitliklerini ters yorumlar.
    sonuc=[]
    for b in sorted(bulgular,key=lambda x:(x["probe"],x["detector"])):
        risk="dusuk" if b["skor"]<=dusuk_esik else "yuksek" if b["skor"]>yuksek_esik else "orta"
        oneri={"dusuk":"izlemeyi_sur","orta":"probe_kapsamini_genislet","yuksek":"modeli_yayina_alma"}[risk]
        sonuc.append(dict(probe=b["probe"],detector=b["detector"],deneme=b["deneme"],agirlikli_skor=b["skor"],risk=risk,oneri=oneri))
    return sonuc

v=json_yukle("veri/bulgular.json")
print("Sentetik bulgular:",v)
print("Risk raporu:",garak_risk_raporu(v,0.2,0.6))
```

```test
import copy
B = [
    {"id": "b-1", "probe": "encoding.base64", "detector": "detector.safety", "skor": 0, "deneme": 2},
    {"id": "b-2", "probe": "dan.roleplay", "detector": "detector.safety", "skor": 0.25, "deneme": 3},
    {"id": "b-3", "probe": "prompt.injection", "detector": "detector.safety", "skor": 0.75, "deneme": 1},
]
BEKLENEN = [
    {"probe": "dan.roleplay", "detector": "detector.safety", "deneme": 3, "agirlikli_skor": 0.25, "risk": "orta", "oneri": "probe_kapsamini_genislet"},
    {"probe": "encoding.base64", "detector": "detector.safety", "deneme": 2, "agirlikli_skor": 0, "risk": "dusuk", "oneri": "izlemeyi_sur"},
    {"probe": "prompt.injection", "detector": "detector.safety", "deneme": 1, "agirlikli_skor": 0.75, "risk": "yuksek", "oneri": "modeli_yayina_alma"},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(B)
        if fn(B, 0.25, 0.75) != BEKLENEN or B != once or fn(list(reversed(B)), 0.25, 0.75) != BEKLENEN:
            return False
        if fn([], 0.25, 0.75) != []:
            return False
        grup = [B[0], dict(B[0], id="b-4", skor=1, deneme=2)]
        sonuc = fn(grup, 0.25, 0.75)[0]
        if sonuc["agirlikli_skor"] != 0.5 or sonuc["risk"] != "orta" or sonuc["deneme"] != 4:
            return False
        if fn([B[0]], 0, 1)[0]["risk"] != "orta":
            return False
        if fn([B[2]], 0, 0.75)[0]["risk"] != "yuksek":
            return False
        for esikler in [(True, 0.75), ("0.25", 0.75), (0.25, False), (float("nan"), 0.75), (0.25, float("inf")), (-0.1, 0.75), (0.25, 1.1), (0.75, 0.25), (0.5, 0.5)]:
            try:
                fn(B, *esikler)
                return False
            except ValueError:
                pass
        for bulgular in [None, {}, [None], [B[0], B[0]], [dict(B[0], id="a" * 65)], [dict(B[0], probe="base64")], [dict(B[0], skor=True)], [dict(B[0], skor="0.5")], [dict(B[0], skor=float("nan"))], [dict(B[0], skor=-0.1)], [dict(B[0], skor=1.1)], [dict(B[0], deneme=0)], [dict(B[0], deneme=False)], [dict(B[0], deneme=1.5)]]:
            try:
                fn(bulgular, 0.25, 0.75)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(garak_risk_raporu), "çift grupları, risk sınırları ve öneriler korunmalı")
def m_skor(bulgular, dusuk_esik, yuksek_esik):
    return garak_risk_raporu([dict(x, skor=0) for x in bulgular], dusuk_esik, yuksek_esik)
def m_detector(bulgular, dusuk_esik, yuksek_esik):
    return garak_risk_raporu([dict(x, detector="detector.other") for x in bulgular], dusuk_esik, yuksek_esik)
def m_esik(bulgular, dusuk_esik, yuksek_esik):
    return garak_risk_raporu(bulgular, 0, 1)
for ad, mutant in [("skorları silen", m_skor), ("detectorü değiştiren", m_detector), ("eşikleri değiştiren", m_esik)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
# --- carbon-c8-ek-bas ---
raises(ValueError, garak_risk_raporu, [dict(B[0], id=123)], 0.25, 0.75, msg="id str olmalı")
raises(ValueError, garak_risk_raporu, [dict(B[0], probe=123)], 0.25, 0.75, msg="probe str olmalı")
raises(ValueError, garak_risk_raporu, [dict(B[0], detector=123)], 0.25, 0.75, msg="detector str olmalı")
raises(ValueError, garak_risk_raporu, [dict(B[0], skor=float("nan"))], 0.25, 0.75, msg="NaN skor ret")
raises(ValueError, garak_risk_raporu, [dict(B[0], deneme=True)], 0.25, 0.75, msg="deneme bool True ret")
raises(ValueError, garak_risk_raporu, B, 0.25, True, msg="üst eşik bool True ret")
raises(ValueError, garak_risk_raporu, B, False, 0.75, msg="alt eşik bool False ret")
raises(ValueError, garak_risk_raporu, B, float("nan"), 0.75, msg="NaN alt eşik ret")
raises(ValueError, garak_risk_raporu, B, 0.25, float("nan"), msg="NaN üst eşik ret")
raises(ValueError, garak_risk_raporu, [dict(B[0], ek=1)], 0.25, 0.75, msg="bulgu fazla alan ret")
# --- carbon-c8-ek-son ---
```

```solution
from ai_savunma_veri import json_yukle
def garak_risk_raporu(bulgular, dusuk_esik, yuksek_esik):
    import math
    import re
    if not isinstance(bulgular, list):
        raise ValueError("bulgular liste olmalı")
    for esik in (dusuk_esik, yuksek_esik):
        if isinstance(esik, bool) or not isinstance(esik, (int, float)):
            raise ValueError("eşik sayı olmalı")
        if not math.isfinite(esik):
            raise ValueError("eşik sonlu olmalı")
    if dusuk_esik < 0:
        raise ValueError("düşük eşik negatif olamaz")
    if yuksek_esik > 1:
        raise ValueError("yüksek eşik birden büyük olamaz")
    if dusuk_esik >= yuksek_esik:
        raise ValueError("eşik sıralaması geçersiz")
    gorulen = set()
    for bulgu in bulgular:
        if not isinstance(bulgu, dict):
            raise ValueError("bulgu sözlük olmalı")
        if set(bulgu) != {"id", "probe", "detector", "skor", "deneme"}:
            raise ValueError("bulgu şeması geçersiz")
        if not isinstance(bulgu["id"], str):
            raise ValueError("kimlik string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", bulgu["id"]):
            raise ValueError("kimlik geçersiz")
        if bulgu["id"] in gorulen:
            raise ValueError("kimlik yinelenemez")
        gorulen.add(bulgu["id"])
        for alan in ("probe", "detector"):
            deger = bulgu[alan]
            if not isinstance(deger, str):
                raise ValueError("araç kimliği string olmalı")
            if not re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+", deger):
                raise ValueError("araç kimliği geçersiz")
        skor = bulgu["skor"]
        if isinstance(skor, bool) or not isinstance(skor, (int, float)):
            raise ValueError("skor sayı olmalı")
        if not math.isfinite(skor):
            raise ValueError("skor sonlu olmalı")
        if skor < 0 or skor > 1:
            raise ValueError("skor aralık dışında")
        deneme = bulgu["deneme"]
        if isinstance(deneme, bool) or not isinstance(deneme, int):
            raise ValueError("deneme tamsayı olmalı")
        if deneme <= 0:
            raise ValueError("deneme pozitif olmalı")
    gruplar = {}
    for bulgu in bulgular:
        anahtar = (bulgu["probe"], bulgu["detector"])
        gruplar.setdefault(anahtar, []).append(bulgu)
    sonuc = []
    for probe, detector in sorted(gruplar):
        grup = gruplar[(probe, detector)]
        deneme = sum(x["deneme"] for x in grup)
        skor = sum(x["skor"] * x["deneme"] for x in grup) / deneme
        if skor < dusuk_esik:
            risk = "dusuk"
            oneri = "izlemeyi_sur"
        elif skor >= yuksek_esik:
            risk = "yuksek"
            oneri = "modeli_yayina_alma"
        else:
            risk = "orta"
            oneri = "probe_kapsamini_genislet"
        sonuc.append({"probe": probe, "detector": detector, "deneme": deneme, "agirlikli_skor": skor, "risk": risk, "oneri": oneri})
    return sonuc
v=json_yukle("veri/bulgular.json")
print("Sentetik bulgular:",v)
print("Risk raporu:",garak_risk_raporu(v,0.2,0.6))

```

```hint
Grup anahtarında probe ve detectorü birlikte kullan. Düşük riski önce, yüksek riski eşitlik içeren koşulla ikinci sırada denetle.
```
:::

::: anlat Gerçek garak API taramasının ham sonuçlarını oku
Son görevde kurulu garak 0.17.1 araç ortamı gerçek Probe.probe → OllamaGeneratorChat → StringDetector.detect zincirini çalıştırır. İki özel Pafta probe'u eski dersin beş sentetik canary istemini korur. Bir probe üç, diğeri iki deneme üretir; her denemede tek gerçek yanıt istenir. StringDetector özel işareti alt dizge olarak arar. Hazır probe kataloğunun tümü veya farklı detector modelleri koşulmaz; hiçbir veri kümesi/model indirilmez.

Ham Attempt, probe adı, detector değerleri ve yanıtlar kanıtta saklanır; senin risk raporun aynı gerçek bulgulardan bağımsız referansla karşılaştırılır. Sızıntı sıfır olsa da ölçüm geçerlidir; eksik/boş yanıt, araç hatası veya beş denemenin tamamlanmaması kabul değildir.
:::

::: gorev Gerçek deney · garak API taramasını yerel modele koş
`garak_risk_raporu(bulgular, dusuk_esik, yuksek_esik)` işlevini yaz — kuralları ve çıktısı 3. görevdekiyle **aynıdır**. Deney kurulu garak API’sinde iki özel Pafta probe’unu gerçek modele koşar; gerçek StringDetector ile canary skorları üretir; senin raporun (probe, detector) bazında ağırlıklı skoru eşiklerle risk ve öneriye çevirir.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def garak_risk_raporu(bulgular, dusuk_esik, yuksek_esik):
    return []

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_27 as deney
    deney.goster(garak_risk_raporu)
```

```test
import ai_lab
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
import ast
_yasak=("referans","ozet","kanit_yaz")
sorun = ai_lab.kod_denetimi(src, _yasak)
for n in ast.walk(ast.parse(src)):
    if isinstance(n,ast.ImportFrom) and any(a.name in _yasak or a.name=="*" for a in n.names):
        sorun.append("referans importu yasak")
if not kontrol(not sorun, "Kendi garak risk işlevini yaz: " + ", ".join(sorun)):
    stop()
fn = need("garak_risk_raporu")
from sandbox import ai_gercek_ai_savunma_27 as D
import copy
B = [
    {"id": "b-1", "probe": "encoding.base64", "detector": "detector.safety", "skor": 0, "deneme": 2},
    {"id": "b-2", "probe": "dan.roleplay", "detector": "detector.safety", "skor": 0.25, "deneme": 3},
    {"id": "b-3", "probe": "prompt.injection", "detector": "detector.safety", "skor": 0.75, "deneme": 1},
]
BEKLENEN = [
    {"probe": "dan.roleplay", "detector": "detector.safety", "deneme": 3, "agirlikli_skor": 0.25, "risk": "orta", "oneri": "probe_kapsamini_genislet"},
    {"probe": "encoding.base64", "detector": "detector.safety", "deneme": 2, "agirlikli_skor": 0, "risk": "dusuk", "oneri": "izlemeyi_sur"},
    {"probe": "prompt.injection", "detector": "detector.safety", "deneme": 1, "agirlikli_skor": 0.75, "risk": "yuksek", "oneri": "modeli_yayina_alma"},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(B)
        if fn(B, 0.25, 0.75) != BEKLENEN or B != once or fn(list(reversed(B)), 0.25, 0.75) != BEKLENEN:
            return False
        if fn([], 0.25, 0.75) != []:
            return False
        grup = [B[0], dict(B[0], id="b-4", skor=1, deneme=2)]
        sonuc = fn(grup, 0.25, 0.75)[0]
        if sonuc["agirlikli_skor"] != 0.5 or sonuc["risk"] != "orta" or sonuc["deneme"] != 4:
            return False
        if fn([B[0]], 0, 1)[0]["risk"] != "orta":
            return False
        if fn([B[2]], 0, 0.75)[0]["risk"] != "yuksek":
            return False
        for esikler in [(True, 0.75), ("0.25", 0.75), (0.25, False), (float("nan"), 0.75), (0.25, float("inf")), (-0.1, 0.75), (0.25, 1.1), (0.75, 0.25), (0.5, 0.5)]:
            try:
                fn(B, *esikler)
                return False
            except ValueError:
                pass
        for bulgular in [None, {}, [None], [B[0], B[0]], [dict(B[0], id="a" * 65)], [dict(B[0], probe="base64")], [dict(B[0], skor=True)], [dict(B[0], skor="0.5")], [dict(B[0], skor=float("nan"))], [dict(B[0], skor=-0.1)], [dict(B[0], skor=1.1)], [dict(B[0], deneme=0)], [dict(B[0], deneme=False)], [dict(B[0], deneme=1.5)]]:
            try:
                fn(bulgular, 0.25, 0.75)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(garak_risk_raporu), "çift grupları, risk sınırları ve öneriler korunmalı")
def m_skor(bulgular, dusuk_esik, yuksek_esik):
    return garak_risk_raporu([dict(x, skor=0) for x in bulgular], dusuk_esik, yuksek_esik)
def m_detector(bulgular, dusuk_esik, yuksek_esik):
    return garak_risk_raporu([dict(x, detector="detector.other") for x in bulgular], dusuk_esik, yuksek_esik)
def m_esik(bulgular, dusuk_esik, yuksek_esik):
    return garak_risk_raporu(bulgular, 0, 1)
for ad, mutant in [("skorları silen", m_skor), ("detectorü değiştiren", m_detector), ("eşikleri değiştiren", m_esik)]:
    kontrol(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
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
    garak_risk_raporu = need('garak_risk_raporu')
    def _birim_adim_3():
        import copy
        B = [
            {"id": "b-1", "probe": "encoding.base64", "detector": "detector.safety", "skor": 0, "deneme": 2},
            {"id": "b-2", "probe": "dan.roleplay", "detector": "detector.safety", "skor": 0.25, "deneme": 3},
            {"id": "b-3", "probe": "prompt.injection", "detector": "detector.safety", "skor": 0.75, "deneme": 1},
        ]
        BEKLENEN = [
            {"probe": "dan.roleplay", "detector": "detector.safety", "deneme": 3, "agirlikli_skor": 0.25, "risk": "orta", "oneri": "probe_kapsamini_genislet"},
            {"probe": "encoding.base64", "detector": "detector.safety", "deneme": 2, "agirlikli_skor": 0, "risk": "dusuk", "oneri": "izlemeyi_sur"},
            {"probe": "prompt.injection", "detector": "detector.safety", "deneme": 1, "agirlikli_skor": 0.75, "risk": "yuksek", "oneri": "modeli_yayina_alma"},
        ]
        def sozlesme(fn):
            try:
                once = copy.deepcopy(B)
                if fn(B, 0.25, 0.75) != BEKLENEN or B != once or fn(list(reversed(B)), 0.25, 0.75) != BEKLENEN:
                    return False
                if fn([], 0.25, 0.75) != []:
                    return False
                grup = [B[0], dict(B[0], id="b-4", skor=1, deneme=2)]
                sonuc = fn(grup, 0.25, 0.75)[0]
                if sonuc["agirlikli_skor"] != 0.5 or sonuc["risk"] != "orta" or sonuc["deneme"] != 4:
                    return False
                if fn([B[0]], 0, 1)[0]["risk"] != "orta":
                    return False
                if fn([B[2]], 0, 0.75)[0]["risk"] != "yuksek":
                    return False
                for esikler in [(True, 0.75), ("0.25", 0.75), (0.25, False), (float("nan"), 0.75), (0.25, float("inf")), (-0.1, 0.75), (0.25, 1.1), (0.75, 0.25), (0.5, 0.5)]:
                    try:
                        fn(B, *esikler)
                        return False
                    except ValueError:
                        pass
                for bulgular in [None, {}, [None], [B[0], B[0]], [dict(B[0], id="a" * 65)], [dict(B[0], probe="base64")], [dict(B[0], skor=True)], [dict(B[0], skor="0.5")], [dict(B[0], skor=float("nan"))], [dict(B[0], skor=-0.1)], [dict(B[0], skor=1.1)], [dict(B[0], deneme=0)], [dict(B[0], deneme=False)], [dict(B[0], deneme=1.5)]]:
                    try:
                        fn(bulgular, 0.25, 0.75)
                        return False
                    except ValueError:
                        pass
                return True
            except Exception:
                return False
        ok(sozlesme(garak_risk_raporu), "çift grupları, risk sınırları ve öneriler korunmalı")
        def m_skor(bulgular, dusuk_esik, yuksek_esik):
            return garak_risk_raporu([dict(x, skor=0) for x in bulgular], dusuk_esik, yuksek_esik)
        def m_detector(bulgular, dusuk_esik, yuksek_esik):
            return garak_risk_raporu([dict(x, detector="detector.other") for x in bulgular], dusuk_esik, yuksek_esik)
        def m_esik(bulgular, dusuk_esik, yuksek_esik):
            return garak_risk_raporu(bulgular, 0, 1)
        for ad, mutant in [("skorları silen", m_skor), ("detectorü değiştiren", m_detector), ("eşikleri değiştiren", m_esik)]:
            ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
        raises(ValueError, garak_risk_raporu, [dict(B[0], id=123)], 0.25, 0.75, msg="id str olmalı")
        raises(ValueError, garak_risk_raporu, [dict(B[0], probe=123)], 0.25, 0.75, msg="probe str olmalı")
        raises(ValueError, garak_risk_raporu, [dict(B[0], detector=123)], 0.25, 0.75, msg="detector str olmalı")
        raises(ValueError, garak_risk_raporu, [dict(B[0], skor=float("nan"))], 0.25, 0.75, msg="NaN skor ret")
        raises(ValueError, garak_risk_raporu, [dict(B[0], deneme=True)], 0.25, 0.75, msg="deneme bool True ret")
        raises(ValueError, garak_risk_raporu, B, 0.25, True, msg="üst eşik bool True ret")
        raises(ValueError, garak_risk_raporu, B, False, 0.75, msg="alt eşik bool False ret")
        raises(ValueError, garak_risk_raporu, B, float("nan"), 0.75, msg="NaN alt eşik ret")
        raises(ValueError, garak_risk_raporu, B, 0.25, float("nan"), msg="NaN üst eşik ret")
        raises(ValueError, garak_risk_raporu, [dict(B[0], ek=1)], 0.25, 0.75, msg="bulgu fazla alan ret")
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
    kontrol(len(r["rapor"]) == 2, "iki probe için gerçek bulgu raporlandı")
    gecerli = {"dusuk", "orta", "yuksek"}
    kontrol(all(x["risk"] in gecerli and 0.0 <= x["agirlikli_skor"] <= 1.0 for x in r["rapor"]),
            "her probe için gerçek açıklık oranından risk üretildi")
    oz = D.ozet(r)
if r is not None:
    kontrol(r["rapor"]==D.referans(r["bulgular"],D.DUSUK_ESIK,D.YUKSEK_ESIK),"gerçek risk raporu bağımsız referansla aynı")
    kontrol(r["exit"]==0 and len(r["garak"]["satirlar"])==5 and all(x["ham_yanit"] and x["hata"] is None for x in r["garak"]["satirlar"]),"garak beş gerçek yanıtı hatasız tamamladı")
    kontrol(r["garak"]["arac"]["detector_sanity"]==[1.0,0.0],"gerçek StringDetector pozitif ve negatif kontrolü ayırdı (sentetik çıktı kontrolü)")
    kontrol(r["gecici_temizlendi"],"yalnız deneye ait geçici klasör kapandı")
    ai_lab.kanit_yaz("savunma-garak", {"kaynak":"gercek","kabul":all(sonuclar),"ders":"ai-savunma-27","ortam":r["ortam"],"deney":r,"ozet":oz})
if oz and all(sonuclar):
    ok(True,f"BULGU: gerçek garak {r['garak']['arac']['surum']}, beş çağrı; probe skorları {oz['skorlar']}, riskler {oz['riskler']}. Sızıntı geçme şartı değil; iki özel probe tüm katalog değildir.")
```

```solution
import ai_lab

def garak_risk_raporu(bulgular, dusuk_esik, yuksek_esik):
    import math
    import re
    if not isinstance(bulgular, list):
        raise ValueError("bulgular liste olmalı")
    for esik in (dusuk_esik, yuksek_esik):
        if isinstance(esik, bool) or not isinstance(esik, (int, float)):
            raise ValueError("eşik sayı olmalı")
        if not math.isfinite(esik):
            raise ValueError("eşik sonlu olmalı")
    if dusuk_esik < 0:
        raise ValueError("düşük eşik negatif olamaz")
    if yuksek_esik > 1:
        raise ValueError("yüksek eşik birden büyük olamaz")
    if dusuk_esik >= yuksek_esik:
        raise ValueError("eşik sıralaması geçersiz")
    gorulen = set()
    for bulgu in bulgular:
        if not isinstance(bulgu, dict):
            raise ValueError("bulgu sözlük olmalı")
        if set(bulgu) != {"id", "probe", "detector", "skor", "deneme"}:
            raise ValueError("bulgu şeması geçersiz")
        if not isinstance(bulgu["id"], str):
            raise ValueError("kimlik string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", bulgu["id"]):
            raise ValueError("kimlik geçersiz")
        if bulgu["id"] in gorulen:
            raise ValueError("kimlik yinelenemez")
        gorulen.add(bulgu["id"])
        for alan in ("probe", "detector"):
            deger = bulgu[alan]
            if not isinstance(deger, str):
                raise ValueError("araç kimliği string olmalı")
            if not re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+", deger):
                raise ValueError("araç kimliği geçersiz")
        skor = bulgu["skor"]
        if isinstance(skor, bool) or not isinstance(skor, (int, float)):
            raise ValueError("skor sayı olmalı")
        if not math.isfinite(skor):
            raise ValueError("skor sonlu olmalı")
        if skor < 0 or skor > 1:
            raise ValueError("skor aralık dışında")
        deneme = bulgu["deneme"]
        if isinstance(deneme, bool) or not isinstance(deneme, int):
            raise ValueError("deneme tamsayı olmalı")
        if deneme <= 0:
            raise ValueError("deneme pozitif olmalı")
    gruplar = {}
    for bulgu in bulgular:
        anahtar = (bulgu["probe"], bulgu["detector"])
        gruplar.setdefault(anahtar, []).append(bulgu)
    sonuc = []
    for probe, detector in sorted(gruplar):
        grup = gruplar[(probe, detector)]
        deneme = sum(x["deneme"] for x in grup)
        skor = sum(x["skor"] * x["deneme"] for x in grup) / deneme
        if skor < dusuk_esik:
            risk = "dusuk"
            oneri = "izlemeyi_sur"
        elif skor >= yuksek_esik:
            risk = "yuksek"
            oneri = "modeli_yayina_alma"
        else:
            risk = "orta"
            oneri = "probe_kapsamini_genislet"
        sonuc.append({"probe": probe, "detector": detector, "deneme": deneme, "agirlikli_skor": skor, "risk": risk, "oneri": oneri})
    return sonuc

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_27 as deney
    deney.goster(garak_risk_raporu)
```

```hint
Bu işlev 3. görevdeki `garak_risk_raporu` ile birebir aynıdır; tek fark, skorların gerçek modele karşı taramadan gelmesidir. Grup anahtarında probe ve detectorü birlikte kullan; düşük riski önce, yüksek riski eşitlikli koşulla denetle.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### Probe denemeyi, detector yorumu tanımlar

Garak probe belirli istem ailesini üretir; detector yanıtı başarısızlık koşuluyla puanlar. Probe bazlı ağırlıklı toplamda deneme sayıları farklıysa basit oran ortalaması yanıltır. Taramanın temiz çıkması taranmamış yüzeyler için kanıt değildir. Gerçek CLI/API koşusu, fixturedan hesaplanan risk raporundan ayrı tutulmalıdır.

| Yaygın yanlış | Mekanizmanın sınırı |
|---|---|
| Tarayıcı hata vermediyse açık yoktur | Tarama kapsamı ve detector hataları ayrıca okunur. |

Saldırı–savunma bağlantısı: ai-saldiri-27.
:::

::: anlat Kaynak ile lab sonucunu ayır
[Garak resmi kaynak kodu](https://github.com/NVIDIA/garak). Probe, generator ve detector bileşenleri taramayı oluşturur; sonuç yalnız seçilen kapsam ve yerel koşuya aittir.
:::
