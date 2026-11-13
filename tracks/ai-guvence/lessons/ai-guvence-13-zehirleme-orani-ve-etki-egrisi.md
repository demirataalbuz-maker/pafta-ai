---
id: ai-guvence-13
title: Zehirleme Oranı ve Etki Eğrisi
summary: Zehirli örnek oranını doğrula; tabana göre performans kaybı eğrisini ve eşik–doyum noktalarını hesapla.
esleme: ai-guvence-12, ai-guvence-14, ai-guvence-15
timeout: 45
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et: Oran ve etki ayrı ölçümlerdir
Zehirli örnek oranı, eğitim kümesine kasten enjekte edilmiş zehirli kayıt sayısının toplam veri büyüklüğüne bölümüdür. Sıfır zehirli kayıt modelin tertemiz veriyle eğitildiği geçerli taban (`baseline`) deneyini verir; bütün kayıtların zehirli olduğu sınır durumunda ise oran birdir. Ancak ham sayılar ile bu sayılardan türetilen güvenlik metrikleri birbirinden bağımsız değerlendirilmelidir.

| Gerçek araç / model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Zehirleme araştırmalarında model, artan zehir oranlarıyla defalarca yeniden eğitilir; her oran için hedef ve temiz doğruluk ölçülüp etki eğrisi çizilir | İlk üç görevde `veri/zehir_sayimlari.json` ve `veri/etki_olcumleri.json` içindeki **sentetik** sayım ve ölçümleri; son görevde artan sayıda hedef sınıf etiketi çevrilerek `scikit-learn` (`LogisticRegression`) ile yeniden eğitilen canlı modelleri | Tek bir veri kümesi ve tek model ailesindeki eğri, başka veri, model veya saldırı türü için genel bir "güvenli zehir oranı" vermez |

> [!NOT]
> İlk üç görevde çalışma dizinine kopyalanan `veri/` dosyaları **sentetik** eğitim örnekleridir. Her çalıştırmada yeniden kopyalanır; çalıştırmalar arasında **kalıcılık yoktur**. Son adımdaki **Gerçek deney** görevinde yazdığın üç işlev canlı yeniden eğitim sonuçlarıyla sınanır; harici bir saldırı aracı ya da framework çalıştırılmaz.
:::

::: anlat Bir zehirleme etki eğrisinde ne olur, saldırgan neyi dener ve savunma neden kırılır?
Yapay zeka modellerinin veri zehirlemesine (`data poisoning`) karşı direncini ölçmek, güvenlik mühendisliğinin en temel güvence testlerinden biridir:

- **Aracın Altında Ne Olur?**
  1. *Zehirleme Oranı Hesaplama (`zehir_orani_hesapla`):* Toplam veri kümesi ve zehirli kayıt sayıları doğrulanır; oran \(\text{zehirli} / \text{toplam}\) formülüyle altı ondalık basamağa yuvarlanarak hesaplanır.
  2. *Performans Kaybı Eğrisi (`etki_egrisi`):* Model artan zehir oranlarında (\(0, 8, 16, \dots, 48\)) sıfırdan yeniden eğitilir. Sıfır zehir oranındaki taban doğruluğu (\(\text{taban\_dogruluk}\)) referans alınarak her orandaki doğruluk kaybı (\(\text{kayip} = \text{taban\_dogruluk} - \text{dogruluk}\)) hesaplanır ve satırlar orana göre sıralanır.
  3. *Eşik ve Doyum Analizi (`esik_doyum_raporu`):* Kaybın kabul edilemez risk eşiğine (ör. \(0.5\)) ilk ulaştığı an *eşik oranı*, modelin zehirlenmeye daha fazla tepki veremeyip performans kaybının plato çizdiği (ardışık iki nokta arasındaki mutlak kayıp farkının \(\le \delta\) olduğu) an ise *doyum noktası* olarak tespit edilir.
- **Çıktı Nasıl Okunur?**
  - Çizilen etki eğrisi doğrusal olmak zorunda değildir; modeller genellikle belirli bir eşiğe kadar zehre direnç gösterip ardından ani bir çöküş (`cliff effect`) yaşayabilir.
  - *Erken Düzlük Tuzağı:* Zehirlenmenin henüz başlangıcında (düşük oranlarda) model doğruluk kaybetmemişse ardışık fark \(\approx 0\) çıkar ve "ilk doyum" henüz saldırı etkisini göstermeden erken düz bölgede yakalanabilir. Bu nedenle doyum oranı mutlaka eşik oranıyla birlikte okunmalıdır.
- **Saldırganın Taktikleri:**
  1. *Eşik Altı Zehirleme (Sub-threshold Poisoning):* Saldırgan, savunma ekiplerinin performans izleme eşiklerini tetiklemeyecek kadar az zehir enjekte eder; modelin genel temiz doğruluğunu korurken hedef sınıfta gizli arka kapılar (`backdoors`) oluşturur.
  2. *Doyum Noktasını Bilmek:* Doyumdan sonra eklenen her zehirli kayıt ek kayıp getirmez, yalnızca tespit riskini artırır; yüksek zehir oranı veri doğrulama ve anomali tespitinde en kolay yakalanan durumdur. Bu yüzden saldırgan doyum noktasını öğrenip zehir miktarını eşik ile doyum arasında, istediği etkiyi veren en küçük orana ayarlamaya çalışır.
- **Savunmanın Kırılma Noktaları:**
  - Taban noktasının (\(\text{oran}=0\)) temiz kabul edilip doğrulanmaması: Eğitim verisi zaten baştan zehirlenmişse taban performansı yanıltıcı olur.
  - Orantısız sınıf dağılımı: Hedef sınıf azınlıktaysa, küçük bir zehirli örnek sayısı bile o sınıfta devasa kayba yol açar.
- **Sık Yapılan Geliştirici Tuzakları:**
  1. Python'da `bool` tipinin `int` alt sınıfı olması (`issubclass(bool, int) is True`): `isinstance(True, int)` ifadesi `True` döndürdüğünden, sayım girdilerinde `not isinstance(x, bool)` kontrolünün unutulması.
  2. Oranı toplam kayıt yerine temiz kayıtlara bölmek (`zehirli / temiz`): Tüm kayıtlar zehirli olduğunda sıfıra bölme hatası (`ZeroDivisionError`) oluşur.
  3. Kayıtları sıralamadan maksimum kayıp ve eşik aramak: Girdi listesi karışık sıralıysa `next()` ilk eşik yerine rastgele bir noktayı yakalar.
  4. Maksimum kayıp seçiminde eşitlik durumu: Aynı maksimum kayba sahip birden fazla oran varsa *en küçük oran* seçilmelidir (`min(satirlar, key=lambda x: (-x["_ham"], x["oran"]))`).
:::

::: anlat Eşik ve doyum noktası aynı şey değildir
Her oranın performans kaybı, sıfır zehir oranındaki taban doğruluğu eksi o oranın doğruluğudur. Eşik oranı, kaybın belirlenen eşiğe ilk ulaştığı noktadır. Doyum noktası ise ardışık iki nokta arasındaki mutlak kayıp değişiminin seçilen delta sınırına ilk indiği orandır.

Eşiğe eşit kayıp eşik koşulunu, değişimin deltaya eşit olması doyum koşulunu sağlar. Koşul hiç sağlanmazsa sonuç `None` olur. Tek eğri gerçek bir saldırının genel etkisini kanıtlamaz; yalnız verilen deney kayıtlarını özetler.
:::

::: tahmin Oran, kayıp ve eşiği tahmin et
Üç çıktı satırını yaz:

```python
print(round(2 / 6, 6))
print(round(0.9 - 0.55, 6))
print(next((r for r, k in [(0, 0.1), (0.2, 0.4), (0.3, 0.5)] if k >= 0.4), None))
```

???

```cikti
0.333333
0.35
0.2
```

İlk satır zehirli örnek oranını, ikinci satır tabana göre kaybı, üçüncü satır eşiğe ulaşan ilk oranı gösterir.
:::

::: gorev 1 · Zehirli örnek oranını hesapla
`zehir_orani_hesapla(toplam, zehirli)` işlevini yaz. Toplam bool olmayan pozitif tamsayı, zehirli bool olmayan sıfır veya pozitif tamsayıdır ve `zehirli <= toplam` olmalıdır. Geçersiz veride `ValueError` yükselt.

`{"toplam":N,"zehirli":N,"temiz":N,"oran":X}` döndür. Temiz kayıt toplam eksi zehirli, oran zehirli/toplamdır ve altı ondalık basamağa yuvarlanır.

```starter
from ai_guvence_veri import json_yukle

def zehir_orani_hesapla(toplam, zehirli):
    # KUSURLU BAŞLANGIÇ KODU: zehirli > toplam ve negatif değerleri reddetmiyor, oranı temiz kayıtlara bölüyor!
    temiz = toplam - zehirli
    return {"toplam": toplam, "zehirli": zehirli, "temiz": temiz, "oran": round(zehirli / max(temiz, 1), 6)}

for d in json_yukle("veri/zehir_sayimlari.json")["deneyler"]:
    print(d["ad"], zehir_orani_hesapla(d["toplam"], d["zehirli"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-13")
```

```test
def sozlesme(fn):
    try:
        if fn(10, 2) != {"toplam": 10, "zehirli": 2, "temiz": 8, "oran": 0.2}:
            return False
        if fn(3, 0) != {"toplam": 3, "zehirli": 0, "temiz": 3, "oran": 0.0}:
            return False
        if fn(3, 3) != {"toplam": 3, "zehirli": 3, "temiz": 0, "oran": 1.0} or fn(1, 1) != {"toplam": 1, "zehirli": 1, "temiz": 0, "oran": 1.0}:
            return False
        if fn(6, 2)["oran"] != 0.333333:
            return False
        for toplam, zehirli in [
            (None, 1), (1, None), (0, 0), (-1, 0), (True, 1), (1.0, 1), ("1", 1),
            (1, -1), (1, 2), (1, True), (1, 1.0), (1, "1"),
        ]:
            try:
                fn(toplam, zehirli)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(zehir_orani_hesapla), "sayımlar, sınırlar ve zehir oranı korunmalı")
def m_toplam(toplam, zehirli):
    return zehir_orani_hesapla(0, zehirli)
def m_zehirli(toplam, zehirli):
    return zehir_orani_hesapla(toplam, -1)
def m_sinir(toplam, zehirli):
    return zehir_orani_hesapla(toplam, toplam + 1)
for ad, mutant in [("toplamı silen", m_toplam), ("zehirliyi bozan", m_zehirli), ("sınırı aşan", m_sinir)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def zehir_orani_hesapla(toplam, zehirli):
    if isinstance(toplam, bool):
        raise ValueError("toplam tamsayı olmalı")
    if not isinstance(toplam, int):
        raise ValueError("toplam tamsayı olmalı")
    if toplam <= 0:
        raise ValueError("toplam pozitif olmalı")
    if isinstance(zehirli, bool):
        raise ValueError("zehirli tamsayı olmalı")
    if not isinstance(zehirli, int):
        raise ValueError("zehirli tamsayı olmalı")
    if zehirli < 0:
        raise ValueError("zehirli negatif olamaz")
    if zehirli > toplam:
        raise ValueError("zehirli toplamı aşamaz")
    return {"toplam": toplam, "zehirli": zehirli, "temiz": toplam - zehirli, "oran": round(zehirli / toplam, 6)}
```

```hint
İki sayımın türünü ayrı doğrula. Zehirli sayısının hem alt hem üst sınırını denetle; oranı son adımda üret.
```
:::

::: gorev 2 · Performans kaybı eğrisini üret
`etki_egrisi(kayitlar)` işlevini yaz. Kayıtlar boş olmayan listedir; her kayıt tam olarak `oran` ve `dogruluk` alanlarını taşır. İki alan da bool olmayan sonlu sayı ve `[0,1]` aralığındadır. Oran yinelenemez ve tam bir `oran=0` tabanı bulunmalıdır. Geçersiz veride `ValueError` yükselt.

Satırları orana göre sırala ve her satıra `kayip` ekle. Kayıp taban doğruluğu eksi satır doğruluğudur. `{"satirlar":[KAYIT+kayip,...],"taban_dogruluk":X,"maksimum_kayip":X,"maksimum_oran":X}` döndür. Maksimum kayıp en yüksek ham kayıp, eşitlikte en küçük oran seçilir. Kayıpları ve maksimum kaybı altı ondalık basamağa yuvarla; girdiyi değiştirme.

```starter
from ai_guvence_veri import json_yukle

def etki_egrisi(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: tabanı oran=0 satırı yerine listedeki ilk kayıttan alıyor (sıralamadan önce)!
    taban = kayitlar[0]["dogruluk"]
    satirlar = [dict(x, kayip=round(taban - x["dogruluk"], 6)) for x in sorted(kayitlar, key=lambda x: x["oran"])]
    en = max(satirlar, key=lambda x: x["kayip"])
    return {"satirlar": satirlar, "taban_dogruluk": taban, "maksimum_kayip": en["kayip"], "maksimum_oran": en["oran"]}

print("Örnek eğri:", etki_egrisi(json_yukle("veri/etki_olcumleri.json")["egri"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-13")
```

```test
import copy
K = [{"oran": 0.2, "dogruluk": 0.5}, {"oran": 0, "dogruluk": 0.9}, {"oran": 0.1, "dogruluk": 0.7}]
BEKLENEN = {
    "satirlar": [{"oran": 0, "dogruluk": 0.9, "kayip": 0.0}, {"oran": 0.1, "dogruluk": 0.7, "kayip": 0.2}, {"oran": 0.2, "dogruluk": 0.5, "kayip": 0.4}],
    "taban_dogruluk": 0.9, "maksimum_kayip": 0.4, "maksimum_oran": 0.2,
}
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K) != BEKLENEN or K != once:
            return False
        esit = fn([K[1], dict(K[2], dogruluk=0.5), K[0]])
        if esit["maksimum_oran"] != 0.1:
            return False
        sinir = fn([{"oran": 0, "dogruluk": 1}, {"oran": 1, "dogruluk": 0}])
        if sinir["maksimum_kayip"] != 1 or sinir["maksimum_oran"] != 1:
            return False
        yuvarla = fn([{"oran": 0, "dogruluk": 1}, {"oran": 1, "dogruluk": 2 / 3}])
        if yuvarla["satirlar"][1]["kayip"] != 0.333333 or yuvarla["maksimum_kayip"] != 0.333333:
            return False
        for kayitlar in [
            None, {}, tuple(K), [], [None], [dict(K[0], ek=1), K[1]], [K[1], K[0], K[0]], [K[0]],
            [dict(K[0], oran=True), K[1]], [dict(K[0], oran="0.2"), K[1]],
            [dict(K[0], oran=float("nan")), K[1]], [dict(K[0], oran=float("inf")), K[1]],
            [dict(K[0], oran=-0.1), K[1]], [dict(K[0], oran=1.1), K[1]],
            [dict(K[0], dogruluk=True), K[1]], [dict(K[0], dogruluk="0.5"), K[1]],
            [dict(K[0], dogruluk=float("nan")), K[1]], [dict(K[0], dogruluk=float("inf")), K[1]],
            [dict(K[0], dogruluk=-0.1), K[1]], [dict(K[0], dogruluk=1.1), K[1]],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(etki_egrisi), "taban, sıralama, kayıp ve maksimum seçimi korunmalı")
def m_dogruluk(kayitlar):
    return etki_egrisi([dict(x, dogruluk=0.9) for x in kayitlar])
def m_oran(kayitlar):
    return etki_egrisi([dict(x, oran=0) for x in kayitlar])
def m_sil(kayitlar):
    return etki_egrisi(kayitlar[:2])
for ad, mutant in [("doğruluğu silen", m_dogruluk), ("oranları silen", m_oran), ("noktaları silen", m_sil)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def etki_egrisi(kayitlar):
    import math
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    if not kayitlar:
        raise ValueError("kayıtlar boş olamaz")
    oranlar = set()
    taban = None
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"oran", "dogruluk"}:
            raise ValueError("kayıt şeması geçersiz")
        for alan in ("oran", "dogruluk"):
            deger = kayit[alan]
            if isinstance(deger, bool):
                raise ValueError("ölçüm sayı olmalı")
            if not isinstance(deger, (int, float)):
                raise ValueError("ölçüm sayı olmalı")
            if not math.isfinite(deger):
                raise ValueError("ölçüm sonlu olmalı")
            if deger < 0 or deger > 1:
                raise ValueError("ölçüm aralık dışında")
        if kayit["oran"] in oranlar:
            raise ValueError("oran yinelenemez")
        if kayit["oran"] == 0:
            taban = kayit["dogruluk"]
        oranlar.add(kayit["oran"])
    if taban is None:
        raise ValueError("sıfır oranlı taban gerekli")
    satirlar = []
    for kayit in sorted(kayitlar, key=lambda x: x["oran"]):
        kayip = taban - kayit["dogruluk"]
        satirlar.append({"oran": kayit["oran"], "dogruluk": kayit["dogruluk"], "kayip": round(kayip, 6), "_ham": kayip})
    en_iyi = min(satirlar, key=lambda x: (-x["_ham"], x["oran"]))
    maksimum = en_iyi["_ham"]
    for satir in satirlar:
        del satir["_ham"]
    return {"satirlar": satirlar, "taban_dogruluk": taban, "maksimum_kayip": round(maksimum, 6), "maksimum_oran": en_iyi["oran"]}
```

```hint
Ham kaybı maksimum seçimi bitene kadar sakla. En yüksek kayıp ve en küçük oran için `(-kayıp, oran)` anahtarı kullan.
```
:::

::: gorev 3 · Eşik ve doyum noktalarını bul
`esik_doyum_raporu(kayitlar, esik, delta)` işlevini yaz. Kayıtlar boş olmayan listedir; her kayıt tam olarak `oran` ve `kayip` alanlarını taşır. Oran, kayıp, eşik ve delta bool olmayan sonlu sayı ve `[0,1]` aralığındadır. Oran yinelenemez ve `oran=0` noktası bulunmalıdır. Geçersiz veride `ValueError` yükselt.

Satırları orana göre sırala. Eşik oranı kaybı `>= esik` olan ilk noktanın oranı; yoksa `None` olur. Doyum oranı, ikinci noktadan başlayarak önceki noktayla mutlak kayıp farkı `<= delta` olan ilk noktanın oranıdır; yoksa `None` olur. `{"esik_orani":X veya None,"doyum_orani":X veya None,"maksimum_kayip":X}` döndür. Maksimum ham kaybı altı ondalık basamağa yuvarla ve girdiyi değiştirme.

```starter
from ai_guvence_veri import json_yukle

def esik_doyum_raporu(kayitlar, esik, delta):
    # KUSURLU BAŞLANGIÇ KODU: satırları orana göre sıralamadan dosya sırasıyla eşik ve doyum arıyor!
    esik_orani = next((x["oran"] for x in kayitlar if x["kayip"] >= esik), None)
    doyum = None
    for i in range(1, len(kayitlar)):
        if abs(kayitlar[i]["kayip"] - kayitlar[i - 1]["kayip"]) <= delta:
            doyum = kayitlar[i]["oran"]
            break
    return {"esik_orani": esik_orani, "doyum_orani": doyum, "maksimum_kayip": max(x["kayip"] for x in kayitlar)}

print("Örnek rapor:", esik_doyum_raporu(json_yukle("veri/etki_olcumleri.json")["kayip_noktalari"], 0.3, 0.05))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-13")
```

```test
import copy
K = [{"oran": 0.3, "kayip": 0.5}, {"oran": 0, "kayip": 0}, {"oran": 0.1, "kayip": 0.2}, {"oran": 0.2, "kayip": 0.45}]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K, 0.4, 0.1) != {"esik_orani": 0.2, "doyum_orani": 0.3, "maksimum_kayip": 0.5} or K != once:
            return False
        esikte = fn(K, 0.2, 0.2)
        if esikte["esik_orani"] != 0.1 or esikte["doyum_orani"] != 0.1:
            return False
        yok = fn(K, 1, 0)
        if yok["esik_orani"] is not None or yok["doyum_orani"] is not None:
            return False
        tek = fn([{"oran": 0, "kayip": 1}], 1, 1)
        if tek != {"esik_orani": 0, "doyum_orani": None, "maksimum_kayip": 1}:
            return False
        yuvarla = fn([{"oran": 0, "kayip": 0}, {"oran": 1, "kayip": 1 / 3}], 0, 1)
        if yuvarla["maksimum_kayip"] != 0.333333:
            return False
        for kayitlar, esik, delta in [
            (None, 0.4, 0.1), (K, None, 0.1), (K, 0.4, None), ({}, 0.4, 0.1), (tuple(K), 0.4, 0.1), ([], 0.4, 0.1),
            ([None], 0.4, 0.1), ([dict(K[0], ek=1), K[1]], 0.4, 0.1), ([K[1], K[0], K[0]], 0.4, 0.1), ([K[0]], 0.4, 0.1),
            ([dict(K[0], oran=True), K[1]], 0.4, 0.1), ([dict(K[0], oran="0.3"), K[1]], 0.4, 0.1),
            ([dict(K[0], oran=float("nan")), K[1]], 0.4, 0.1), ([dict(K[0], oran=-0.1), K[1]], 0.4, 0.1),
            ([dict(K[0], oran=1.1), K[1]], 0.4, 0.1), ([dict(K[0], kayip=True), K[1]], 0.4, 0.1),
            ([dict(K[0], kayip="0.5"), K[1]], 0.4, 0.1), ([dict(K[0], kayip=float("inf")), K[1]], 0.4, 0.1),
            ([dict(K[0], kayip=-0.1), K[1]], 0.4, 0.1), ([dict(K[0], kayip=1.1), K[1]], 0.4, 0.1),
            (K, True, 0.1), (K, "0.4", 0.1), (K, float("nan"), 0.1), (K, -0.1, 0.1), (K, 1.1, 0.1),
            (K, 0.4, True), (K, 0.4, "0.1"), (K, 0.4, float("inf")), (K, 0.4, -0.1), (K, 0.4, 1.1),
        ]:
            try:
                fn(kayitlar, esik, delta)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(esik_doyum_raporu), "eşik, ardışık değişim, doyum ve None kuralları korunmalı")
def m_kayip(kayitlar, esik, delta):
    return esik_doyum_raporu([dict(x, kayip=0) for x in kayitlar], esik, delta)
def m_oran(kayitlar, esik, delta):
    return esik_doyum_raporu([dict(x, oran=0) for x in kayitlar], esik, delta)
def m_esik(kayitlar, esik, delta):
    return esik_doyum_raporu(kayitlar, 1, delta)
for ad, mutant in [("kayıpları silen", m_kayip), ("oranları silen", m_oran), ("eşiği değiştiren", m_esik)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def esik_doyum_raporu(kayitlar, esik, delta):
    import math
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    if not kayitlar:
        raise ValueError("kayıtlar boş olamaz")
    for deger in (esik, delta):
        if isinstance(deger, bool):
            raise ValueError("eşik sayı olmalı")
        if not isinstance(deger, (int, float)):
            raise ValueError("eşik sayı olmalı")
        if not math.isfinite(deger):
            raise ValueError("eşik sonlu olmalı")
        if deger < 0 or deger > 1:
            raise ValueError("eşik aralık dışında")
    oranlar = set()
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"oran", "kayip"}:
            raise ValueError("kayıt şeması geçersiz")
        for alan in ("oran", "kayip"):
            deger = kayit[alan]
            if isinstance(deger, bool):
                raise ValueError("ölçüm sayı olmalı")
            if not isinstance(deger, (int, float)):
                raise ValueError("ölçüm sayı olmalı")
            if not math.isfinite(deger):
                raise ValueError("ölçüm sonlu olmalı")
            if deger < 0 or deger > 1:
                raise ValueError("ölçüm aralık dışında")
        if kayit["oran"] in oranlar:
            raise ValueError("oran yinelenemez")
        oranlar.add(kayit["oran"])
    if 0 not in oranlar:
        raise ValueError("sıfır oranlı nokta gerekli")
    satirlar = sorted(kayitlar, key=lambda x: x["oran"])
    esik_orani = next((x["oran"] for x in satirlar if x["kayip"] >= esik), None)
    doyum_orani = None
    for i in range(1, len(satirlar)):
        if abs(satirlar[i]["kayip"] - satirlar[i - 1]["kayip"]) <= delta:
            doyum_orani = satirlar[i]["oran"]
            break
    return {"esik_orani": esik_orani, "doyum_orani": doyum_orani, "maksimum_kayip": round(max(x["kayip"] for x in satirlar), 6)}
```

```hint
İlk eşik noktasını `next` ile bul. Doyum için ikinci sıradan başla ve her noktayı yalnız bir öncekiyle karşılaştır.
```
:::

::: anlat `scikit-learn` ile artan zehir oranlarında canlı yeniden eğitim ve etki eğrisi
Önceki üç görevde zehir oranını, kayıp eğrisini ve eşik–doyum noktalarını sentetik ölçümlerle hesapladın. Şimdi aynı üç işlevi **gerçek yeniden eğitim döngüsüne** bağlıyoruz:

1. 160 örneklik eğitim kümesinde hedef sınıf (`2`) etiketlerinden 0, 8, 16, … 48 tanesi sınıf `0`'a çevrilir; her deneyin oranı `zehir_orani_hesapla` ile hesaplanır,
2. Her oran için `LogisticRegression` sıfırdan eğitilir ve hedef sınıf test doğruluğu `etki_egrisi` ile tabana göre kayba çevrilir,
3. Kayıp noktaları `esik_doyum_raporu` ile (eşik `0.5`, delta `0.05`) özetlenip kanıt dosyasına kaydedilir.

Eğri bu veri kümesi ve bu model içindir; başka bir sistem için güvenli oran iddiası kurmaz. Kanıta bakarken şuna dikkat et: düşük oranlarda kayıp henüz başlamadıysa ardışık fark da küçüktür ve "ilk doyum" bu erken düz bölgede çıkabilir. Doyum oranını eşik oranıyla birlikte okumadan "etki şurada doydu" deme.

Kaynaklar: [Steinhardt vd. 2017 — Certified Defenses for Data Poisoning Attacks (arXiv:1706.03691)](https://arxiv.org/abs/1706.03691), [NIST AI 100-2 E2023 — Adversarial Machine Learning](https://csrc.nist.gov/pubs/ai/100/2/e2023/final).
:::

::: gorev Gerçek deney · scikit-learn ile zehir oranı–etki eğrisi
Önceki üç görevde yazdığın `zehir_orani_hesapla(toplam, zehirli)`, `etki_egrisi(kayitlar)` ve `esik_doyum_raporu(kayitlar, esik, delta)` işlevlerini burada birleştir.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 180
```

```starter
import math
import ai_lab
from sandbox import ai_gercek_ai_guvence_13 as L

def zehir_orani_hesapla(toplam, zehirli):
    # KUSURLU BAŞLANGIÇ KODU: oranı temiz kayıtlara bölüyor!
    return {"toplam": toplam, "zehirli": zehirli, "temiz": toplam - zehirli, "oran": round(zehirli / max(toplam - zehirli, 1), 6)}

def etki_egrisi(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: kayıtları sıralamadan ve tabanı aramadan boş liste dönüyor!
    return {"satirlar": list(kayitlar or []), "taban_dogruluk": 0.0, "maksimum_kayip": 0.0, "maksimum_oran": 0.0}

def esik_doyum_raporu(kayitlar, esik, delta):
    # KUSURLU BAŞLANGIÇ KODU: ardışık farkı denetlemeden doyum oranını ilk eleman sayıyor!
    return {"esik_orani": None, "doyum_orani": (kayitlar or [{}])[0].get("oran"), "maksimum_kayip": 0.0}

if ai_lab.CALISTIR:
    L.goster(zehir_orani_hesapla, etki_egrisi, esik_doyum_raporu)
```

```test
import ast
import ai_lab
from sandbox import ai_gercek_ai_guvence_13 as L

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for ad in ("zehir_orani_hesapla", "etki_egrisi", "esik_doyum_raporu"):
    need(ad)

yasak = (
    "referans",
    "zehir_orani_hesapla_referans",
    "etki_egrisi_referans",
    "esik_doyum_raporu_referans",
    "getattr",
    "kanit_yaz",
)
ihlal = ai_lab.kod_denetimi(src, yasak=yasak)
try:
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.ImportFrom) and any(a.name in yasak or a.name == "*" for a in node.names):
            ihlal.append("referans ithali")
except SyntaxError:
    ihlal.append("sözdizimi")
ok(not ihlal, "Kendi çözümünü yaz; referans işlevler ithal edilemez: " + ", ".join(ihlal))
if not all(checks):
    stop()

def _sozlesme_kontrol():
    try:
        if zehir_orani_hesapla(10, 2) != {"toplam": 10, "zehirli": 2, "temiz": 8, "oran": 0.2}:
            return False
        for t, z in [(0, 0), (1, 2), (True, 1), (1, -1)]:
            try:
                zehir_orani_hesapla(t, z)
                return False
            except ValueError:
                pass
        K = [{"oran": 0.2, "dogruluk": 0.5}, {"oran": 0, "dogruluk": 0.9}, {"oran": 0.1, "dogruluk": 0.7}]
        e = etki_egrisi(K)
        if e["taban_dogruluk"] != 0.9 or e["maksimum_kayip"] != 0.4 or e["maksimum_oran"] != 0.2:
            return False
        R = [{"oran": 0.3, "kayip": 0.5}, {"oran": 0, "kayip": 0}, {"oran": 0.1, "kayip": 0.2}, {"oran": 0.2, "kayip": 0.45}]
        if esik_doyum_raporu(R, 0.4, 0.1) != {"esik_orani": 0.2, "doyum_orani": 0.3, "maksimum_kayip": 0.5}:
            return False
        return True
    except Exception:
        return False

def _birim1(fn):
    def sozlesme(fn):
        try:
            if fn(10, 2) != {"toplam": 10, "zehirli": 2, "temiz": 8, "oran": 0.2}:
                return False
            if fn(3, 0) != {"toplam": 3, "zehirli": 0, "temiz": 3, "oran": 0.0}:
                return False
            if fn(3, 3) != {"toplam": 3, "zehirli": 3, "temiz": 0, "oran": 1.0} or fn(1, 1) != {"toplam": 1, "zehirli": 1, "temiz": 0, "oran": 1.0}:
                return False
            if fn(6, 2)["oran"] != 0.333333:
                return False
            for toplam, zehirli in [
                (None, 1), (1, None), (0, 0), (-1, 0), (True, 1), (1.0, 1), ("1", 1),
                (1, -1), (1, 2), (1, True), (1, 1.0), (1, "1"),
            ]:
                try:
                    fn(toplam, zehirli)
                    return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False
    return sozlesme(fn)

def _birim2(fn):
    import copy
    K = [{"oran": 0.2, "dogruluk": 0.5}, {"oran": 0, "dogruluk": 0.9}, {"oran": 0.1, "dogruluk": 0.7}]
    BEKLENEN = {
        "satirlar": [{"oran": 0, "dogruluk": 0.9, "kayip": 0.0}, {"oran": 0.1, "dogruluk": 0.7, "kayip": 0.2}, {"oran": 0.2, "dogruluk": 0.5, "kayip": 0.4}],
        "taban_dogruluk": 0.9, "maksimum_kayip": 0.4, "maksimum_oran": 0.2,
    }
    def sozlesme(fn):
        try:
            once = copy.deepcopy(K)
            if fn(K) != BEKLENEN or K != once:
                return False
            esit = fn([K[1], dict(K[2], dogruluk=0.5), K[0]])
            if esit["maksimum_oran"] != 0.1:
                return False
            sinir = fn([{"oran": 0, "dogruluk": 1}, {"oran": 1, "dogruluk": 0}])
            if sinir["maksimum_kayip"] != 1 or sinir["maksimum_oran"] != 1:
                return False
            yuvarla = fn([{"oran": 0, "dogruluk": 1}, {"oran": 1, "dogruluk": 2 / 3}])
            if yuvarla["satirlar"][1]["kayip"] != 0.333333 or yuvarla["maksimum_kayip"] != 0.333333:
                return False
            for kayitlar in [
                None, {}, tuple(K), [], [None], [dict(K[0], ek=1), K[1]], [K[1], K[0], K[0]], [K[0]],
                [dict(K[0], oran=True), K[1]], [dict(K[0], oran="0.2"), K[1]],
                [dict(K[0], oran=float("nan")), K[1]], [dict(K[0], oran=float("inf")), K[1]],
                [dict(K[0], oran=-0.1), K[1]], [dict(K[0], oran=1.1), K[1]],
                [dict(K[0], dogruluk=True), K[1]], [dict(K[0], dogruluk="0.5"), K[1]],
                [dict(K[0], dogruluk=float("nan")), K[1]], [dict(K[0], dogruluk=float("inf")), K[1]],
                [dict(K[0], dogruluk=-0.1), K[1]], [dict(K[0], dogruluk=1.1), K[1]],
            ]:
                try:
                    fn(kayitlar)
                    return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False
    return sozlesme(fn)

def _birim3(fn):
    import copy
    K = [{"oran": 0.3, "kayip": 0.5}, {"oran": 0, "kayip": 0}, {"oran": 0.1, "kayip": 0.2}, {"oran": 0.2, "kayip": 0.45}]
    def sozlesme(fn):
        try:
            once = copy.deepcopy(K)
            if fn(K, 0.4, 0.1) != {"esik_orani": 0.2, "doyum_orani": 0.3, "maksimum_kayip": 0.5} or K != once:
                return False
            esikte = fn(K, 0.2, 0.2)
            if esikte["esik_orani"] != 0.1 or esikte["doyum_orani"] != 0.1:
                return False
            yok = fn(K, 1, 0)
            if yok["esik_orani"] is not None or yok["doyum_orani"] is not None:
                return False
            tek = fn([{"oran": 0, "kayip": 1}], 1, 1)
            if tek != {"esik_orani": 0, "doyum_orani": None, "maksimum_kayip": 1}:
                return False
            yuvarla = fn([{"oran": 0, "kayip": 0}, {"oran": 1, "kayip": 1 / 3}], 0, 1)
            if yuvarla["maksimum_kayip"] != 0.333333:
                return False
            for kayitlar, esik, delta in [
                (None, 0.4, 0.1), (K, None, 0.1), (K, 0.4, None), ({}, 0.4, 0.1), (tuple(K), 0.4, 0.1), ([], 0.4, 0.1),
                ([None], 0.4, 0.1), ([dict(K[0], ek=1), K[1]], 0.4, 0.1), ([K[1], K[0], K[0]], 0.4, 0.1), ([K[0]], 0.4, 0.1),
                ([dict(K[0], oran=True), K[1]], 0.4, 0.1), ([dict(K[0], oran="0.3"), K[1]], 0.4, 0.1),
                ([dict(K[0], oran=float("nan")), K[1]], 0.4, 0.1), ([dict(K[0], oran=-0.1), K[1]], 0.4, 0.1),
                ([dict(K[0], oran=1.1), K[1]], 0.4, 0.1), ([dict(K[0], kayip=True), K[1]], 0.4, 0.1),
                ([dict(K[0], kayip="0.5"), K[1]], 0.4, 0.1), ([dict(K[0], kayip=float("inf")), K[1]], 0.4, 0.1),
                ([dict(K[0], kayip=-0.1), K[1]], 0.4, 0.1), ([dict(K[0], kayip=1.1), K[1]], 0.4, 0.1),
                (K, True, 0.1), (K, "0.4", 0.1), (K, float("nan"), 0.1), (K, -0.1, 0.1), (K, 1.1, 0.1),
                (K, 0.4, True), (K, 0.4, "0.1"), (K, 0.4, float("inf")), (K, 0.4, -0.1), (K, 0.4, 1.1),
            ]:
                try:
                    fn(kayitlar, esik, delta)
                    return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False
    return sozlesme(fn)

ok(_birim1(zehir_orani_hesapla), "zehir_orani_hesapla tam birim sözleşmesini geçmeli")
ok(_birim2(etki_egrisi), "etki_egrisi tam birim sözleşmesini geçmeli")
ok(_birim3(esik_doyum_raporu), "esik_doyum_raporu tam birim sözleşmesini geçmeli")
ok(_sozlesme_kontrol(), "zehir_orani_hesapla, etki_egrisi ve esik_doyum_raporu sözleşme kontrollerini geçmeli")
if not all(checks):
    stop()

try:
    rapor = L.deney(zehir_orani_hesapla, etki_egrisi, esik_doyum_raporu)
except ai_lab.GercekLabYok as e:
    ok(False, str(e))
    stop()
except Exception as e:
    ok(False, f"GERÇEK ZEHİR ORANI DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

k = rapor["kontroller"]
ok(k["oran_uyumu"], f"zehir_orani_hesapla canlı deney sayımlarında referansla uyuşmalı: {rapor['oranlar']}")
ok(k["egri_uyumu"] and k["etki_gozlendi"], f"etki_egrisi canlı yeniden eğitim doğruluklarında referansla uyuşmalı: {rapor['ozet']['egri']}")
ok(k["esik_doyum_uyumu"], f"esik_doyum_raporu canlı kayıp noktalarında referansla uyuşmalı: {rapor['esik_doyum']}")

kabul = all(checks)
kanit_yolu = ai_lab.kanit_yaz("guvence-13-zehir-egrisi", dict(rapor, kaynak="gercek", kabul=kabul))
o = rapor["ozet"]
print(f"GERÇEK ZEHİR ORANI DENEYİ: sklearn={o['sklearn_surum']} eşik={o['esik_orani']} doyum={o['doyum_orani']} maks_kayıp={o['maksimum_kayip']} kanıt={kanit_yolu}")
```

```solution
import math
import ai_lab
from sandbox import ai_gercek_ai_guvence_13 as L

def _sayi_mi(d):
    return not isinstance(d, bool) and isinstance(d, (int, float)) and math.isfinite(d) and 0 <= d <= 1

def zehir_orani_hesapla(toplam, zehirli):
    if isinstance(toplam, bool) or not isinstance(toplam, int) or toplam <= 0:
        raise ValueError("toplam geçersiz")
    if isinstance(zehirli, bool) or not isinstance(zehirli, int) or zehirli < 0 or zehirli > toplam:
        raise ValueError("zehirli geçersiz")
    return {"toplam": toplam, "zehirli": zehirli, "temiz": toplam - zehirli, "oran": round(zehirli / toplam, 6)}

def etki_egrisi(kayitlar):
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar geçersiz")
    oranlar = set()
    taban = None
    for k in kayitlar:
        if not isinstance(k, dict) or set(k) != {"oran", "dogruluk"}:
            raise ValueError("şema geçersiz")
        if not _sayi_mi(k["oran"]) or not _sayi_mi(k["dogruluk"]):
            raise ValueError("ölçüm geçersiz")
        if k["oran"] in oranlar:
            raise ValueError("oran yinelenemez")
        if k["oran"] == 0:
            taban = k["dogruluk"]
        oranlar.add(k["oran"])
    if taban is None:
        raise ValueError("taban gerekli")
    satirlar = []
    for k in sorted(kayitlar, key=lambda x: x["oran"]):
        kayip = taban - k["dogruluk"]
        satirlar.append({"oran": k["oran"], "dogruluk": k["dogruluk"], "kayip": round(kayip, 6), "_ham": kayip})
    en = min(satirlar, key=lambda x: (-x["_ham"], x["oran"]))
    maks = en["_ham"]
    for s in satirlar:
        del s["_ham"]
    return {"satirlar": satirlar, "taban_dogruluk": taban, "maksimum_kayip": round(maks, 6), "maksimum_oran": en["oran"]}

def esik_doyum_raporu(kayitlar, esik, delta):
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar geçersiz")
    if not _sayi_mi(esik) or not _sayi_mi(delta):
        raise ValueError("eşik geçersiz")
    oranlar = set()
    for k in kayitlar:
        if not isinstance(k, dict) or set(k) != {"oran", "kayip"}:
            raise ValueError("şema geçersiz")
        if not _sayi_mi(k["oran"]) or not _sayi_mi(k["kayip"]):
            raise ValueError("ölçüm geçersiz")
        if k["oran"] in oranlar:
            raise ValueError("oran yinelenemez")
        oranlar.add(k["oran"])
    if 0 not in oranlar:
        raise ValueError("sıfır noktası gerekli")
    satirlar = sorted(kayitlar, key=lambda x: x["oran"])
    esik_orani = next((x["oran"] for x in satirlar if x["kayip"] >= esik), None)
    doyum = None
    for i in range(1, len(satirlar)):
        if abs(satirlar[i]["kayip"] - satirlar[i - 1]["kayip"]) <= delta:
            doyum = satirlar[i]["oran"]
            break
    return {"esik_orani": esik_orani, "doyum_orani": doyum, "maksimum_kayip": round(max(x["kayip"] for x in satirlar), 6)}

if ai_lab.CALISTIR:
    L.goster(zehir_orani_hesapla, etki_egrisi, esik_doyum_raporu)
```

```hint
Önceki üç görevde yazdığın işlevleri eksiksiz taşı; canlı deneyde her zehir oranı için `LogisticRegression` yeniden eğitilir ve hedef sınıf doğruluk kaybı eğriye dönüşür.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Tek oran yerine doz–yanıt (`etki`) eğrisi (30 sn).** "'Verinin %10'u zehirlenirse model çöker' tek noktalı bir iddiadır; zehir oranını `%0` tabanından başlayarak taramak hasarın hangi eşikte başladığını ve nerede doyuma ulaştığını gösterir."
2. **Taban (`oran=0`) zorunluluğu (30 sn).** "Zehirsiz taban doğruluk ölçülmeden hesaplanan performans kaybı havada kalır; her orandaki kayıp aynı eğitim protokolündeki `%0` tabanına göre ölçülür."
3. **Erken düz bölge tuzağı (35 sn).** "Çok düşük zehir oranlarında kayıp henüz başlamadığı için ardışık fark küçük çıkabilir; bu yüzden `doyum_orani` asla `esik_orani`'ndan bağımsız okunmaz."
4. **Soru (25 sn).** "Saldırgan toplam veri kümesinin yalnız `%0.5`'ini değiştirebiliyorsa neden rastgele etiket çevirme yerine arka kapı (`backdoor`) tetikleyicisine yönelir?"
:::
