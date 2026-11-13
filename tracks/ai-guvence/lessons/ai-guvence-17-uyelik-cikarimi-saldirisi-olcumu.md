---
id: ai-guvence-17
title: Üyelik Çıkarımı Saldırısı Ölçümü
summary: Sentetik üye ve üye olmayan skorlarıyla ROC AUC, üyelik avantajı ve FPR sınırlı eşik seçimini ölç.
esleme: ai-guvence-16, ai-guvence-18, ai-guvence-39
timeout: 45
---

::: anlat Üyelik skoru tek başına saldırı başarısı değildir
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Üye ve üye olmayan örneklerin model skorları, ROC AUC ve seçilmiş eşikte TPR/FPR | Görevler 1–3 görünür sentetik JSON skorları; son görev gerçek yerel PyTorch shadow/hedef modellerinden üretilen doğru-sınıf olasılıkları | Yüksek bir skor kesin üyelik kanıtı değildir; tek bir düşük AUC bütün saldırılara karşı gizlilik garantisi vermez |

> [!NOT]
> `veri/uyelik_kayitlari.json` ve `veri/esikler.json` elle hazırlanmış sentetik eğitim dosyalarıdır. Setup her çalıştırmada geçici dizine yeniden kopyalar; kalıcılık yoktur. Başlangıç kodu dosyayı gerçekten okur; aynı çalıştırmada bellekte kopyayı değiştirip sonucu gözleyebilirsin. Son gerçek deneyin `PAFTA_DATA/calisma/ai-guvence-17/ayarlar.json` kopyası ayrıdır ve kalıcıdır; varsa üzerine yazılmaz. Öğrenci dosyaları gizli kontrol girdilerini değiştirmez.

Üyelik çıkarımı deneyinde her kaydın gerçek üyelik etiketi ve saldırının ürettiği skoru bulunur. Skor yükseldikçe kaydın üye olduğuna dair şüphe artar; ancak tek bir skor, veri bölünmesi veya model ayrıntısı bilinmeden gizlilik ihlali kanıtı sayılmaz.

İlk üç görevde sentetik etiketler ve dosyaya yazılmış skorlar kullanılır. Son görev yerel shadow ve hedef modellerini gerçekten eğitir; veri yine sentetiktir. Gerçek kullanıcı verisi veya dış saldırı API'si kullanılmaz. Amaç yetkili bir gizlilik değerlendirmesinde kullanılabilecek metrikleri doğru hesaplamaktır.
:::

::: anlat AUC, avantaj ve FPR farklı soruları yanıtlar
ROC AUC, rastgele seçilen bir üyenin skorunun rastgele seçilen bir üye olmayandan yüksek gelme olasılığını ölçer; eşit skorlar yarım katkı verir. Belirli bir eşikte skor eşiğe eşit veya büyükse kayıt üye tahmin edilir. Avantaj `TPR-FPR`, yanlış pozitif oranı ise `FP/(FP+TN)` olur.

AUC bütün eşiklerin sıralama başarısını özetlerken avantaj ve FPR seçilen çalışma noktasını anlatır. Paydası sıfır olan oranlar ve tanımsız AUC bu derste `0.0` kabul edilir. FPR üst sınırı altında eşik seçilirken önce avantaj, sonra TPR en yüksek; hâlâ eşitlik varsa en düşük eşik seçilir.
:::

::: anlat Dosyadan shadow/hedef değerlendirmesine
Üyelik çıkarımında saldırganın sorusu bir kaydın eğitim kümesinde bulunup bulunmadığıdır. Bu, kaydın hangi sınıfa ait olduğunu tahmin etmekten farklıdır. Bir sınıflandırıcı doğru etiketin olasılığını eğitimde gördüğü örneklere daha yüksek verebilir; saldırgan bu farkı skor olarak kullanabilir. Ancak zor bir eğitim örneği düşük, kolay bir dış örnek yüksek skor alabilir. Etiketler ile skorları birlikte saklamak hangi tahminin yanlış olduğunu görmeni sağlar. Bu dersin ilk görevinde üyelik etiketleri deney tasarımından bilinir; gerçek dünyada saldırganın her kayıt için böyle bir doğrulama imkânı olmayabilir.

Önce `veri/uyelik_kayitlari.json` dosyasını okuyup ham biçimde yazdır. Kaydın kimliği, üyelik bool değeri ve sonlu sayısal skoru aynı satırda bulunur. Dosyada iki eşit skor vardır; bu tesadüf değil, eşitlik davranışını incelemen için hazırlanmış bir sınır örneğidir. İlk görev skorları azalan sıraya koyarken aynı skorda kimliği artan sıralar. Böylece farklı giriş sıraları aynı raporu üretir. Girdiyi yerinde sıralamak sonraki işlemlerin başlangıç verisini değiştirebilir; bağımsız sözlük kopyaları döndürmek bu yan etkiyi önler. Şema doğrulaması gizlilik ölçümünden önce gelir.

İkinci görevde `veri/esikler.json` içindeki çalışma eşiğini kullan. Skor eşiğe eşit olduğunda örnek üye tahmin edilir. TP gerçekten üye olup üye tahmin edilenleri, FP dışarıdan gelip üye tahmin edilenleri sayar. TPR yalnız gerçek üyeleri, FPR yalnız gerçek üye olmayanları payda olarak kullanır. Her ikisini toplam kayıt sayısına bölmek sınıflar dengesizken yanıltıcıdır. Avantaj TPR eksi FPR'dir; işaretini ters çevirmek iyi bir ayrımı kötü gibi gösterir. AUC ise tek bir eşikteki doğruluk değildir: bütün üye/dış örnek çiftlerinin skor sırasını özetler ve eşit skora yarım katkı verir.

Üçüncü görev aynı dosyada aday eşikleri tarar. Her eşikte yanlış pozitif oranı üst sınırını kontrol et; sınırla eşitlik uygundur. Uygun adaylar arasında ham avantaj ve TPR ile seçim yap, eşitlikte en düşük eşiği seç. Raporlanan yuvarlanmış değerleri karşılaştırmak birbirine çok yakın adayları yanlış eşitleyebilir. Dersin sentetik görevlerinde yalnız tek sınıf kaldığında tanımsız oran ve AUC için sıfır kullanılması bir arayüz sözleşmesidir. Bu sıfırı istatistiksel olarak anlamlı başarısızlık ölçümü gibi yorumlama. Son gerçek deneyde ise her iki üyelik sınıfı da vardır.

Canlı görevde PyTorch iki ayrı küçük model eğitir. Shadow model saldırganın eşik seçimi için kullandığı yardımcı modeldir; hedef modelin üyelikleri eşik ayarlamaya katılmaz. Gerçek autograd ve SGD eğitiminden sonra her örneğin doğru sınıfına verilen softmax olasılığı ölçülür. Shadow verisinde seçilen eşik hedef skorlarına uygulanır; iki seed ile yeni koşular yapılır. Hedef etiketlerine bakıp en iyi eşiği seçmek değerlendirmeyi olduğundan iyi gösteren bilgi sızıntısıdır. Modelin ağırlık hash'i, eğitim ayarları ve ham skorlar hangi koşunun ölçüldüğünü denetlemene yardım eder.

Saldırgan farklı skor işlevleri, başka yardımcı modeller veya daha fazla örnek deneyebilir; savunma yalnız bu tek skorun AUC'sine bakarsa genel bir gizlilik sonucu çıkaramaz. Düşük yanlış pozitif isteyen bir kullanımda yüksek AUC bile seçilen çalışma noktasının işe yarayacağını garanti etmez. Bu yüzden eşik, TPR, FPR ve avantajı birlikte raporla. Görevin geçmesi saldırının mutlaka kazanmasına bağlı değildir; hesaplamanın ve deney akışının doğruluğuna bağlıdır. Ham skorlar burada sentetik olduğu için öğretimde saklanır. Özel eğitim verisiyle çalışırken aynı izleri yayımlamak ayrıca gizlilik riski yaratabilir; bu küçük deney bir üretim sistemi sertifikası değildir.
:::

::: tahmin AUC ve çalışma noktasını tahmin et
Üç çıktı satırını yaz:

```python
print(round((2 + 1 + 0.5) / 6, 6))
print(round(2 / 3 - 1 / 3, 6))
print(0.25 <= 0.25 and 0.5 > 0.4)
```

???

```cikti
0.583333
0.333333
True
```

İlk satır iki galibiyet, bir mağlubiyet ve bir skor eşitliğinin AUC katkısını; ikinci satır avantajı; üçüncü satır FPR sınırında eşitliğin kabul edildiğini gösterir.
:::

::: gorev 1 · Üyelik deneyi verisini doğrula
`uyelik_verisi_dogrula(kayitlar)` işlevini yaz. Kayıtlar boş olmayan listedir; her kayıt tam olarak `id`, `uye`, `skor` alanlarını taşır. Kimlik 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren stringdir; kimlikler yinelenemez. Üyelik bool, skor bool olmayan sonlu sayı ve `[0,1]` aralığında olmalıdır. Geçersiz veride `ValueError` yükselt.

Bağımsız sözlük kopyalarını skoru azalan, eşit skorda kimliği artan sırayla döndür. Girdiyi değiştirme.

```starter
def uyelik_verisi_dogrula(kayitlar):
    import math
    import re
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    if not kayitlar:
        raise ValueError("kayıtlar boş olamaz")
    idler = set()
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"id", "uye", "skor"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["id"], str):
            raise ValueError("kimlik string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
            raise ValueError("kimlik geçersiz")
        if kayit["id"] in idler:
            raise ValueError("kimlik yinelenemez")
        if not isinstance(kayit["uye"], bool):
            raise ValueError("üyelik bool olmalı")
        skor = kayit["skor"]
        if isinstance(skor, bool):
            raise ValueError("skor sayı olmalı")
        if not isinstance(skor, (int, float)):
            raise ValueError("skor sayı olmalı")
        if not math.isfinite(skor):
            raise ValueError("skor sonlu olmalı")
        if skor < 0 or skor > 1:
            raise ValueError("skor aralık dışında")
        idler.add(kayit["id"])
    # KUSURLU BAŞLANGIÇ KODU: skorları azalan yerine artan sıraya koyuyor.
    return [dict(x) for x in sorted(kayitlar, key=lambda x: (x["skor"], x["id"]))]

from ai_guvence_veri import json_yukle
print(uyelik_verisi_dogrula(json_yukle("veri/uyelik_kayitlari.json")))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-17")
```

```test
import copy
K = [
    {"id": "d-1", "uye": False, "skor": 0.8},
    {"id": "u-2", "uye": True, "skor": 0.7},
    {"id": "u-1", "uye": True, "skor": 0.9},
    {"id": "d-2", "uye": False, "skor": 0.7},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        sonuc = fn(K)
        if [x["id"] for x in sonuc] != ["u-1", "d-1", "d-2", "u-2"] or K != once:
            return False
        if any(a is b for a, b in zip(sonuc, [K[2], K[0], K[3], K[1]])):
            return False
        sinir = [{"id": "a" * 64, "uye": False, "skor": 0}, {"id": "b", "uye": True, "skor": 1}]
        if fn(sinir) != [sinir[1], sinir[0]]:
            return False
        for kayitlar in [
            None, {}, tuple(K), [], [None], [dict(K[0], ek=1)], [K[0], K[0]],
            [dict(K[0], id="")], [dict(K[0], id="a b")], [dict(K[0], id="a" * 65)], [dict(K[0], id=None)],
            [dict(K[0], uye=1)], [dict(K[0], uye="false")], [dict(K[0], uye=None)],
            [dict(K[0], skor=True)], [dict(K[0], skor="0.8")], [dict(K[0], skor=None)],
            [dict(K[0], skor=float("nan"))], [dict(K[0], skor=float("inf"))],
            [dict(K[0], skor=-0.1)], [dict(K[0], skor=1.1)],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(uyelik_verisi_dogrula), "şema, kimlikler, üyelik, skor aralığı ve sıralama korunmalı")
def m_uye(kayitlar):
    return uyelik_verisi_dogrula([dict(x, uye=False) for x in kayitlar])
def m_skor(kayitlar):
    return uyelik_verisi_dogrula([dict(x, skor=0) for x in kayitlar])
def m_id(kayitlar):
    return uyelik_verisi_dogrula([dict(x, id="u") for x in kayitlar])
for ad, mutant in [("üyelikleri silen", m_uye), ("skorları silen", m_skor), ("kimlikleri birleştiren", m_id)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def uyelik_verisi_dogrula(kayitlar):
    import math
    import re
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    if not kayitlar:
        raise ValueError("kayıtlar boş olamaz")
    idler = set()
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"id", "uye", "skor"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["id"], str):
            raise ValueError("kimlik string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
            raise ValueError("kimlik geçersiz")
        if kayit["id"] in idler:
            raise ValueError("kimlik yinelenemez")
        if not isinstance(kayit["uye"], bool):
            raise ValueError("üyelik bool olmalı")
        skor = kayit["skor"]
        if isinstance(skor, bool):
            raise ValueError("skor sayı olmalı")
        if not isinstance(skor, (int, float)):
            raise ValueError("skor sayı olmalı")
        if not math.isfinite(skor):
            raise ValueError("skor sonlu olmalı")
        if skor < 0 or skor > 1:
            raise ValueError("skor aralık dışında")
        idler.add(kayit["id"])
    return [dict(x) for x in sorted(kayitlar, key=lambda x: (-x["skor"], x["id"]))]

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    print(uyelik_verisi_dogrula(json_yukle("veri/uyelik_kayitlari.json")))
```

```hint
Önce bütün kayıtları ve alan türlerini doğrula. Sıralama anahtarında negatif skor ile kimliği birlikte kullan.
```
:::

::: gorev 2 · ROC AUC ve üyelik metriklerini hesapla
`uyelik_roc_olc(kayitlar, esik)` işlevini yaz. Kayıtlar ilk görevdeki biçimdedir; eşik bool olmayan sonlu sayı ve `[0,1]` aralığındadır. Geçersiz veride `ValueError` yükselt. Skor eşiğe eşit veya büyükse üye tahmini yapılır.

`{"toplam":N,"tp":N,"fp":N,"tn":N,"fn":N,"tpr":X,"fpr":X,"avantaj":X,"auc":X}` döndür. TPR `TP/(TP+FN)`, FPR `FP/(FP+TN)`, avantaj `TPR-FPR` olur. AUC'yi bütün eşiklerdeki ROC alanı olarak hesapla; eşit skorlu grupları birlikte işle. Paydası sıfır olan oranlar veya AUC `0.0` olur. Oranları altı ondalık basamağa yuvarla ve girdiyi değiştirme.

```starter
def uyelik_roc_olc(kayitlar, esik):
    import math
    import re
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar boş olmayan liste olmalı")
    if isinstance(esik, bool) or not isinstance(esik, (int, float)):
        raise ValueError("eşik sayı olmalı")
    if not math.isfinite(esik) or esik < 0 or esik > 1:
        raise ValueError("eşik geçersiz")
    idler = set()
    for x in kayitlar:
        if not isinstance(x, dict) or set(x) != {"id", "uye", "skor"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(x["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", x["id"]):
            raise ValueError("kimlik geçersiz")
        if x["id"] in idler:
            raise ValueError("kimlik yinelenemez")
        if not isinstance(x["uye"], bool):
            raise ValueError("üyelik bool olmalı")
        if isinstance(x["skor"], bool) or not isinstance(x["skor"], (int, float)):
            raise ValueError("skor sayı olmalı")
        if not math.isfinite(x["skor"]) or x["skor"] < 0 or x["skor"] > 1:
            raise ValueError("skor geçersiz")
        idler.add(x["id"])
    tp = sum(1 for x in kayitlar if x["uye"] and x["skor"] >= esik)
    fp = sum(1 for x in kayitlar if not x["uye"] and x["skor"] >= esik)
    tn = sum(1 for x in kayitlar if not x["uye"] and x["skor"] < esik)
    fn = sum(1 for x in kayitlar if x["uye"] and x["skor"] < esik)
    p = tp + fn
    n = fp + tn
    tpr = tp / p if p else 0.0
    fpr = fp / n if n else 0.0
    once_tp = 0
    once_fp = 0
    alan = 0.0
    for skor in sorted({x["skor"] for x in kayitlar}, reverse=True):
        grup = [x for x in kayitlar if x["skor"] == skor]
        yeni_tp = once_tp + sum(1 for x in grup if x["uye"])
        yeni_fp = once_fp + sum(1 for x in grup if not x["uye"])
        alan += (yeni_fp - once_fp) * (yeni_tp + once_tp) / 2
        once_tp, once_fp = yeni_tp, yeni_fp
    # KUSURLU BAŞLANGIÇ KODU: AUC alanını çift sayısı yerine bütün kayıt sayısına bölüyor.
    auc = alan / len(kayitlar)
    return {"toplam": len(kayitlar), "tp": tp, "fp": fp, "tn": tn, "fn": fn, "tpr": round(tpr, 6), "fpr": round(fpr, 6), "avantaj": round(tpr - fpr, 6), "auc": round(auc, 6)}

from ai_guvence_veri import json_yukle
esikler = json_yukle("veri/esikler.json")
print(uyelik_roc_olc(json_yukle("veri/uyelik_kayitlari.json"), esikler["esik"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-17")
```

```test
import copy
K = [
    {"id": "u-1", "uye": True, "skor": 0.9},
    {"id": "u-2", "uye": True, "skor": 0.7},
    {"id": "d-1", "uye": False, "skor": 0.8},
    {"id": "d-2", "uye": False, "skor": 0.6},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        beklenen = {"toplam": 4, "tp": 2, "fp": 1, "tn": 1, "fn": 0, "tpr": 1.0, "fpr": 0.5, "avantaj": 0.5, "auc": 0.75}
        if fn(K, 0.7) != beklenen or K != once:
            return False
        if fn(K, 0.9)["tp"] != 1 or fn(K, 1)["fpr"] != 0:
            return False
        eksik = fn(K, 0.8)
        if eksik != {"toplam": 4, "tp": 1, "fp": 1, "tn": 1, "fn": 1, "tpr": 0.5, "fpr": 0.5, "avantaj": 0.0, "auc": 0.75}:
            return False
        esit = fn([{"id": "u", "uye": True, "skor": 0.5}, {"id": "d", "uye": False, "skor": 0.5}], 0.5)
        if esit["auc"] != 0.5 or esit["avantaj"] != 0:
            return False
        sadece_uye = fn([{"id": "u", "uye": True, "skor": 1}], 1)
        if sadece_uye["auc"] != 0 or sadece_uye["fpr"] != 0 or sadece_uye["tpr"] != 1:
            return False
        sadece_dis = fn([{"id": "d", "uye": False, "skor": 0}], 0)
        if sadece_dis["auc"] != 0 or sadece_dis["tpr"] != 0 or sadece_dis["fpr"] != 1:
            return False
        yuvarla = fn([
            {"id": "u1", "uye": True, "skor": 0.9}, {"id": "u2", "uye": True, "skor": 0.8},
            {"id": "u3", "uye": True, "skor": 0.7}, {"id": "d1", "uye": False, "skor": 0.85},
            {"id": "d2", "uye": False, "skor": 0.75}, {"id": "d3", "uye": False, "skor": 0.65},
        ], 0.8)
        if yuvarla != {"toplam": 6, "tp": 2, "fp": 1, "tn": 2, "fn": 1, "tpr": 0.666667, "fpr": 0.333333, "avantaj": 0.333333, "auc": 0.666667}:
            return False
        for kayitlar, esik in [
            (None, 0.5), (K, None), ({}, 0.5), (tuple(K), 0.5), ([], 0.5), ([None], 0.5), ([dict(K[0], ek=1)], 0.5),
            ([K[0], K[0]], 0.5), ([dict(K[0], id=123)], 0.5), ([dict(K[0], id="a b")], 0.5), ([dict(K[0], id="a" * 65)], 0.5),
            ([dict(K[0], uye=1)], 0.5), ([dict(K[0], skor=True)], 0.5), ([dict(K[0], skor="0.9")], 0.5), ([dict(K[0], skor=float("nan"))], 0.5),
            ([dict(K[0], skor=-0.1)], 0.5), ([dict(K[0], skor=1.1)], 0.5),
            (K, True), (K, "0.5"), (K, float("nan")), (K, float("inf")), (K, -0.1), (K, 1.1),
        ]:
            try:
                fn(kayitlar, esik)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(uyelik_roc_olc), "karışıklık sayıları, AUC, eşit skorlar ve sıfır paydalar korunmalı")
def m_uye(kayitlar, esik):
    return uyelik_roc_olc([dict(x, uye=False) for x in kayitlar], esik)
def m_skor(kayitlar, esik):
    return uyelik_roc_olc([dict(x, skor=0) for x in kayitlar], esik)
def m_esik(kayitlar, esik):
    return uyelik_roc_olc(kayitlar, 1)
for ad, mutant in [("üyelikleri silen", m_uye), ("skorları silen", m_skor), ("eşiği değiştiren", m_esik)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def uyelik_roc_olc(kayitlar, esik):
    import math
    import re
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar boş olmayan liste olmalı")
    if isinstance(esik, bool) or not isinstance(esik, (int, float)):
        raise ValueError("eşik sayı olmalı")
    if not math.isfinite(esik) or esik < 0 or esik > 1:
        raise ValueError("eşik geçersiz")
    idler = set()
    for x in kayitlar:
        if not isinstance(x, dict) or set(x) != {"id", "uye", "skor"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(x["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", x["id"]):
            raise ValueError("kimlik geçersiz")
        if x["id"] in idler:
            raise ValueError("kimlik yinelenemez")
        if not isinstance(x["uye"], bool):
            raise ValueError("üyelik bool olmalı")
        if isinstance(x["skor"], bool) or not isinstance(x["skor"], (int, float)):
            raise ValueError("skor sayı olmalı")
        if not math.isfinite(x["skor"]) or x["skor"] < 0 or x["skor"] > 1:
            raise ValueError("skor geçersiz")
        idler.add(x["id"])
    tp = sum(1 for x in kayitlar if x["uye"] and x["skor"] >= esik)
    fp = sum(1 for x in kayitlar if not x["uye"] and x["skor"] >= esik)
    tn = sum(1 for x in kayitlar if not x["uye"] and x["skor"] < esik)
    fn = sum(1 for x in kayitlar if x["uye"] and x["skor"] < esik)
    p = tp + fn
    n = fp + tn
    tpr = tp / p if p else 0.0
    fpr = fp / n if n else 0.0
    once_tp = 0
    once_fp = 0
    alan = 0.0
    for skor in sorted({x["skor"] for x in kayitlar}, reverse=True):
        grup = [x for x in kayitlar if x["skor"] == skor]
        yeni_tp = once_tp + sum(1 for x in grup if x["uye"])
        yeni_fp = once_fp + sum(1 for x in grup if not x["uye"])
        alan += (yeni_fp - once_fp) * (yeni_tp + once_tp) / 2
        once_tp, once_fp = yeni_tp, yeni_fp
    auc = alan / (p * n) if p and n else 0.0
    return {"toplam": len(kayitlar), "tp": tp, "fp": fp, "tn": tn, "fn": fn, "tpr": round(tpr, 6), "fpr": round(fpr, 6), "avantaj": round(tpr - fpr, 6), "auc": round(auc, 6)}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    esikler = json_yukle("veri/esikler.json")
    print(uyelik_roc_olc(json_yukle("veri/uyelik_kayitlari.json"), esikler["esik"]))
```

```hint
AUC için azalan skor gruplarında FP genişliği ile ortalama TP yüksekliğinin çarpımını topla. Sonunda üye ve üye olmayan sayılarının çarpımına böl.
```
:::

::: gorev 3 · FPR sınırına uyan çalışma eşiğini seç
`uyelik_esik_tara(kayitlar, fpr_ust)` işlevini yaz. Kayıtlar ilk görevdeki biçimdedir; FPR üst sınırı bool olmayan sonlu sayı ve `[0,1]` aralığındadır. Geçersiz veride `ValueError` yükselt. Aday eşikler kayıtlardaki benzersiz skorlardır ve her adayda skor eşiğe eşit veya büyükse üye tahmini yapılır.

Her aday için `{"esik":X,"tpr":X,"fpr":X,"avantaj":X,"uygun":BOOL}` üret; satırları eşiği azalan sırala. `uygun`, ham FPR üst sınıra eşit veya küçükse doğrudur. Uygun adaylardan en yüksek ham avantajı, eşitlikte en yüksek ham TPR'yi, hâlâ eşitlikte en düşük eşiği seç. AUC'yi ikinci görevdeki kuralla hesapla. `{"satirlar":[...],"secilen":X veya None,"auc":X}` döndür; oranları altı ondalık basamağa yuvarla, eşikleri olduğu gibi bırak ve girdiyi değiştirme.

```starter
def uyelik_esik_tara(kayitlar, fpr_ust):
    import math
    import re
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar boş olmayan liste olmalı")
    if isinstance(fpr_ust, bool) or not isinstance(fpr_ust, (int, float)):
        raise ValueError("FPR üst sınırı sayı olmalı")
    if not math.isfinite(fpr_ust) or fpr_ust < 0 or fpr_ust > 1:
        raise ValueError("FPR üst sınırı geçersiz")
    idler = set()
    for x in kayitlar:
        if not isinstance(x, dict) or set(x) != {"id", "uye", "skor"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(x["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", x["id"]):
            raise ValueError("kimlik geçersiz")
        if x["id"] in idler:
            raise ValueError("kimlik yinelenemez")
        if not isinstance(x["uye"], bool):
            raise ValueError("üyelik bool olmalı")
        if isinstance(x["skor"], bool) or not isinstance(x["skor"], (int, float)):
            raise ValueError("skor sayı olmalı")
        if not math.isfinite(x["skor"]) or x["skor"] < 0 or x["skor"] > 1:
            raise ValueError("skor geçersiz")
        idler.add(x["id"])
    p = sum(1 for x in kayitlar if x["uye"])
    n = len(kayitlar) - p
    # KUSURLU BAŞLANGIÇ KODU: FPR üst sınırına eşit adayı gereksiz reddediyor.
    satirlar = []
    for esik in sorted({x["skor"] for x in kayitlar}, reverse=True):
        tp = sum(1 for x in kayitlar if x["uye"] and x["skor"] >= esik)
        fp = sum(1 for x in kayitlar if not x["uye"] and x["skor"] >= esik)
        tpr = tp / p if p else 0.0
        fpr = fp / n if n else 0.0
        satirlar.append({"esik": esik, "tpr": round(tpr, 6), "fpr": round(fpr, 6), "avantaj": round(tpr - fpr, 6), "uygun": fpr < fpr_ust, "_tpr": tpr, "_avantaj": tpr - fpr})
    uygun = [x for x in satirlar if x["uygun"]]
    secilen = min(uygun, key=lambda x: (-x["_avantaj"], -x["_tpr"], x["esik"]))["esik"] if uygun else None
    once_tp = 0
    once_fp = 0
    alan = 0.0
    for satir in satirlar:
        esik = satir["esik"]
        yeni_tp = sum(1 for x in kayitlar if x["uye"] and x["skor"] >= esik)
        yeni_fp = sum(1 for x in kayitlar if not x["uye"] and x["skor"] >= esik)
        alan += (yeni_fp - once_fp) * (yeni_tp + once_tp) / 2
        once_tp, once_fp = yeni_tp, yeni_fp
        del satir["_tpr"]
        del satir["_avantaj"]
    return {"satirlar": satirlar, "secilen": secilen, "auc": round(alan / (p * n), 6) if p and n else 0.0}

from ai_guvence_veri import json_yukle
esikler = json_yukle("veri/esikler.json")
print(uyelik_esik_tara(json_yukle("veri/uyelik_kayitlari.json"), esikler["fpr_ust"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-17")
```

```test
import copy
K = [
    {"id": "u-1", "uye": True, "skor": 0.9},
    {"id": "u-2", "uye": True, "skor": 0.7},
    {"id": "d-1", "uye": False, "skor": 0.8},
    {"id": "d-2", "uye": False, "skor": 0.6},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        sonuc = fn(K, 0.5)
        if K != once or sonuc["secilen"] != 0.7 or sonuc["auc"] != 0.75:
            return False
        if [x["esik"] for x in sonuc["satirlar"]] != [0.9, 0.8, 0.7, 0.6]:
            return False
        if [x["uygun"] for x in sonuc["satirlar"]] != [True, True, True, False]:
            return False
        if sonuc["satirlar"][0] != {"esik": 0.9, "tpr": 0.5, "fpr": 0.0, "avantaj": 0.5, "uygun": True}:
            return False
        if fn(K, 0)["secilen"] != 0.9:
            return False
        esit = [{"id": "u", "uye": True, "skor": 0.5}, {"id": "d", "uye": False, "skor": 0.5}]
        if fn(esit, 0)["secilen"] is not None or fn(esit, 0)["auc"] != 0.5:
            return False
        sadece_uye = fn([{"id": "u", "uye": True, "skor": 0.4}], 0)
        if sadece_uye["secilen"] != 0.4 or sadece_uye["satirlar"][0]["fpr"] != 0:
            return False
        sadece_dis = fn([{"id": "d", "uye": False, "skor": 0.4}], 1)
        if sadece_dis["auc"] != 0.0 or sadece_dis["satirlar"][0]["tpr"] != 0.0:
            return False
        sinir = fn([{"id": "u", "uye": True, "skor": 1}, {"id": "d", "uye": False, "skor": 0}], 1)
        if sinir["secilen"] != 1 or sinir["auc"] != 1:
            return False
        yuvarla = fn([
            {"id": "u1", "uye": True, "skor": 0.9}, {"id": "u2", "uye": True, "skor": 0.8},
            {"id": "u3", "uye": True, "skor": 0.7}, {"id": "d1", "uye": False, "skor": 0.85},
            {"id": "d2", "uye": False, "skor": 0.75}, {"id": "d3", "uye": False, "skor": 0.65},
        ], 1)
        if yuvarla["auc"] != 0.666667 or yuvarla["satirlar"][0]["tpr"] != 0.333333:
            return False
        if yuvarla["satirlar"][2] != {"esik": 0.8, "tpr": 0.666667, "fpr": 0.333333, "avantaj": 0.333333, "uygun": True}:
            return False
        for kayitlar, ust in [
            (None, 0.5), (K, None), ({}, 0.5), (tuple(K), 0.5), ([], 0.5), ([None], 0.5), ([dict(K[0], ek=1)], 0.5),
            ([K[0], K[0]], 0.5), ([dict(K[0], id=123)], 0.5), ([dict(K[0], id="a b")], 0.5), ([dict(K[0], id="a" * 65)], 0.5),
            ([dict(K[0], uye=1)], 0.5), ([dict(K[0], skor=True)], 0.5), ([dict(K[0], skor="0.9")], 0.5), ([dict(K[0], skor=float("nan"))], 0.5), ([dict(K[0], skor=float("inf"))], 0.5),
            ([dict(K[0], skor=-0.1)], 0.5), ([dict(K[0], skor=1.1)], 0.5),
            (K, True), (K, "0.5"), (K, float("nan")), (K, float("inf")), (K, -0.1), (K, 1.1),
        ]:
            try:
                fn(kayitlar, ust)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(uyelik_esik_tara), "FPR sınırı, aday eşikler, seçim sırası ve AUC korunmalı")
def m_uye(kayitlar, ust):
    return uyelik_esik_tara([dict(x, uye=False) for x in kayitlar], ust)
def m_skor(kayitlar, ust):
    return uyelik_esik_tara([dict(x, skor=0) for x in kayitlar], ust)
def m_ust(kayitlar, ust):
    return uyelik_esik_tara(kayitlar, 0)
for ad, mutant in [("üyelikleri silen", m_uye), ("skorları silen", m_skor), ("FPR sınırını değiştiren", m_ust)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def uyelik_esik_tara(kayitlar, fpr_ust):
    import math
    import re
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar boş olmayan liste olmalı")
    if isinstance(fpr_ust, bool) or not isinstance(fpr_ust, (int, float)):
        raise ValueError("FPR üst sınırı sayı olmalı")
    if not math.isfinite(fpr_ust) or fpr_ust < 0 or fpr_ust > 1:
        raise ValueError("FPR üst sınırı geçersiz")
    idler = set()
    for x in kayitlar:
        if not isinstance(x, dict) or set(x) != {"id", "uye", "skor"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(x["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", x["id"]):
            raise ValueError("kimlik geçersiz")
        if x["id"] in idler:
            raise ValueError("kimlik yinelenemez")
        if not isinstance(x["uye"], bool):
            raise ValueError("üyelik bool olmalı")
        if isinstance(x["skor"], bool) or not isinstance(x["skor"], (int, float)):
            raise ValueError("skor sayı olmalı")
        if not math.isfinite(x["skor"]) or x["skor"] < 0 or x["skor"] > 1:
            raise ValueError("skor geçersiz")
        idler.add(x["id"])
    p = sum(1 for x in kayitlar if x["uye"])
    n = len(kayitlar) - p
    satirlar = []
    for esik in sorted({x["skor"] for x in kayitlar}, reverse=True):
        tp = sum(1 for x in kayitlar if x["uye"] and x["skor"] >= esik)
        fp = sum(1 for x in kayitlar if not x["uye"] and x["skor"] >= esik)
        tpr = tp / p if p else 0.0
        fpr = fp / n if n else 0.0
        satirlar.append({"esik": esik, "tpr": round(tpr, 6), "fpr": round(fpr, 6), "avantaj": round(tpr - fpr, 6), "uygun": fpr <= fpr_ust, "_tpr": tpr, "_avantaj": tpr - fpr})
    uygun = [x for x in satirlar if x["uygun"]]
    secilen = min(uygun, key=lambda x: (-x["_avantaj"], -x["_tpr"], x["esik"]))["esik"] if uygun else None
    once_tp = 0
    once_fp = 0
    alan = 0.0
    for satir in satirlar:
        esik = satir["esik"]
        yeni_tp = sum(1 for x in kayitlar if x["uye"] and x["skor"] >= esik)
        yeni_fp = sum(1 for x in kayitlar if not x["uye"] and x["skor"] >= esik)
        alan += (yeni_fp - once_fp) * (yeni_tp + once_tp) / 2
        once_tp, once_fp = yeni_tp, yeni_fp
        del satir["_tpr"]
        del satir["_avantaj"]
    return {"satirlar": satirlar, "secilen": secilen, "auc": round(alan / (p * n), 6) if p and n else 0.0}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    esikler = json_yukle("veri/esikler.json")
    print(uyelik_esik_tara(json_yukle("veri/uyelik_kayitlari.json"), esikler["fpr_ust"]))
```

```hint
Her eşikte TPR ve FPR'yi yeniden hesapla; uygunluk ve seçimde ham değerleri sakla. AUC'de aynı azalan eşik sırasındaki yamuk alanlarını toplayabilirsin.
```
:::


::: anlat Canlı CPU deneyi ve düzenlenebilir sentetik ayar
Önce [sentetik ayar dosyasını](/data/ai-guvence-17-ayarlar.txt) açıp seed, ornek, sigma alanlarını incele. Bu JSON örneği kaydedilmiş model çıktısı değildir. Yeni görev gerçek küçük MLP'yi torch autograd ile CPU'da eğitir; ağ/model indirme yoktur.

Çalıştır ilk kullanımda örneği `PAFTA_DATA/calisma/ai-guvence-17/ayarlar.json` konumuna yalnız yoksa kopyalar, tam yolu ekranda yazar. Göreli PAFTA_DATA proje köküne göre çözülür. Öğrenci bu kalıcı JSON'u metin düzenleyicide değiştirebilir (seed:0..2**30-1, ornek:8..32, sigma:0.5..8); yeniden Çalıştır düzenlemeyi korur. Tarayıcıdaki örnek salt okunur indirme bağlantısıdır; kalıcı kopyayı kendi editöründe aç. Kontrol bağımsız test ayarı kullanır, örneği değiştirmek beklenen cevabı değiştirmez.

Yalnız sentetik veriler kullanılır. Saldırının kazanması veya gizlilik iddiasının desteklenmesi PASS şartı değildir. Küçük deney sohbet modelinin gizliliğine genellenemez. DP eğitimli deneylerde açık tohum, ham veriler ve eğitim izleri öğretim içindir; bu yayınlar özel veri için DP garantisi taşımaz. Bütçe yalnız sabit boyutlu replace-one tam batch Gaussian ağırlık mekanizması içindir, ham izlere değil. Güvenli üretim RNG/accountant denetimi yapılmaz.

Kaynaklar: [Carlini vd. 2022 — Membership Inference Attacks From First Principles / LiRA (arXiv:2112.03570)](https://arxiv.org/abs/2112.03570), [Shokri vd. 2017 — Membership Inference Attacks Against Machine Learning Models (arXiv:1610.05820)](https://arxiv.org/abs/1610.05820).
:::

::: gorev Gerçek deney · CPU gizlilik ölçümü 17
`olc(scores, labels, threshold)` gerçek hedefin doğru-sınıf olasılıkları ve bool üyelikleri üzerinde AUC (eşitlik yarım), TPR, FPR, TPR−FPR hesaplasın; alanlar `auc,tpr,fpr,avantaj`, altı ondalık. İki sınıf da mevcut. Tahmin `skor>=eşik`. Ayrı shadow model eşik seçer, hedef yalnız ölçülür.

Girdileri değiştirme. Çalıştır gerçek öğrenci dosyasıyla sonuç ve kanıt yolunu gösterir; Kontrol farklı veri ve tohumlarda bağımsız hesap, boş/sabit/yanlış çözüm denetimi yapar. torch yokluğu PASS değildir.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 180
```

```starter
import ai_lab
def olc(scores, labels, threshold):
    return {}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_17_20 as deney
    deney.goster(17,olc)
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
kontrol(deney.sozlesme(17,olc),'Görülmemiş sınırlar, eşitlik ve yanlış ölçüm reddi')
kontrol(olc([0.9, 0.5, 0.1, 0.8, 0.1, 0.1], [True, True, True, False, False, False], 0.5) == {'auc': 0.666667, 'tpr': 0.666667, 'fpr': 0.333333, 'avantaj': 0.333333}, '6 basamak yuvarlama, eşit skor yarı-katkısı ve >= eşik sınırı')
with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp)/'ayar.json'
    p.write_text('{"seed": 8317, "ornek": 13, "sigma": 1.75}',encoding='utf-8')
    r=deney.deney(17,olc,path=p)
    for name,value in r['kontroller'].items(): kontrol(value,name)
ns={}
exec('def olc(scores, labels, threshold):\n    p=sum(labels); n=len(labels)-p\n    tp=sum(y and s>=threshold for s,y in zip(scores,labels))\n    fp=sum(not y and s>=threshold for s,y in zip(scores,labels))\n    positives=[s for s,y in zip(scores,labels) if y]\n    negatives=[s for s,y in zip(scores,labels) if not y]\n    a=sum((x>y) for x in positives for y in negatives)/(p*n)\n    return dict(auc=round(a,6),tpr=round(tp/p,6),fpr=round(fp/n,6),avantaj=round(tp/p-fp/n,6))\n',ns)
kontrol(not deney.sozlesme(17,ns['olc']),'Mutant 1 reddedilir')
ns={}
exec('def olc(scores, labels, threshold):\n    p=sum(labels); n=len(labels)-p\n    tp=sum(y and s>threshold for s,y in zip(scores,labels))\n    fp=sum(not y and s>threshold for s,y in zip(scores,labels))\n    positives=[s for s,y in zip(scores,labels) if y]\n    negatives=[s for s,y in zip(scores,labels) if not y]\n    a=sum((x>y)+0.5*(x==y) for x in positives for y in negatives)/(p*n)\n    return dict(auc=round(a,6),tpr=round(tp/p,6),fpr=round(fp/n,6),avantaj=round(tp/p-fp/n,6))\n',ns)
kontrol(not deney.sozlesme(17,ns['olc']),'Mutant 2 reddedilir')
ns={}
exec('def olc(scores, labels, threshold):\n    p=sum(labels); n=len(labels)-p\n    tp=sum(y and s>=threshold for s,y in zip(scores,labels))\n    fp=sum(not y and s>=threshold for s,y in zip(scores,labels))\n    positives=[s for s,y in zip(scores,labels) if y]\n    negatives=[s for s,y in zip(scores,labels) if not y]\n    a=sum((x>y)+0.5*(x==y) for x in positives for y in negatives)/(p*n)\n    return dict(auc=round(a,6),tpr=round(tp/p,6),fpr=round(fp/n,6),avantaj=round(fp/n-tp/p,6))\n',ns)
kontrol(not deney.sozlesme(17,ns['olc']),'Mutant 3 reddedilir')
ai_lab.kanit_yaz('guvence-17-cpu',dict(r,kabul=all(checks)))

```

```solution
import ai_lab
def olc(scores, labels, threshold):
    p=sum(labels); n=len(labels)-p
    tp=sum(y and s>=threshold for s,y in zip(scores,labels))
    fp=sum(not y and s>=threshold for s,y in zip(scores,labels))
    positives=[s for s,y in zip(scores,labels) if y]
    negatives=[s for s,y in zip(scores,labels) if not y]
    a=sum((x>y)+0.5*(x==y) for x in positives for y in negatives)/(p*n)
    return dict(auc=round(a,6),tpr=round(tp/p,6),fpr=round(fp/n,6),avantaj=round(tp/p-fp/n,6))

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_17_20 as deney
    deney.goster(17,olc)
```

```hint
Ham eşik koşulunu yuvarlamadan uygula. AUC eşitlikte yarım katkı verir. Gürültüyü başarı garantisi olarak yorumlama.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Ortalama doğruluk yerine düşük `FPR` çalışma noktası (35 sn).** "Üyelik çıkarımında `%50` yanlış pozitif pahasına `%70` yakalama pratik bir gizlilik ihlali değildir; Carlini vd.'nin gösterdiği gibi asıl tehlike çok düşük `FPR` altında bile yüksek güvenle tekil üyelerin teşhis edilebilmesidir."
2. **Eşit skorlu çiftlerde `AUC` hesabı (30 sn).** "Pozitif ve negatif örnek çiftlerini karşılaştırırken $s_+ > s_-$ tam katkı, $s_+ = s_-$ ise `0.5` katkı alır; aksi halde sabit skor üreten bozuk bir model `0.5` yerine `0.0` veya `1.0` `AUC` alabilir."
3. **Eşik tarama disiplini (30 sn).** "`fpr_ust` bütçesini aşmayan eşikler arasından önce en yüksek `avantaj` (`TPR - FPR`), eşitlikte daha yüksek `TPR` ve en düşük eşik seçilerek karar noktası deterministik hale getirilir."
4. **Soru (25 sn).** "Genel `ROC-AUC` değeri `0.54` görünen bir model neden birkaç aykırı hasta kaydı için hâlâ ciddi bir gizlilik sızıntısı taşıyor olabilir?"
:::
