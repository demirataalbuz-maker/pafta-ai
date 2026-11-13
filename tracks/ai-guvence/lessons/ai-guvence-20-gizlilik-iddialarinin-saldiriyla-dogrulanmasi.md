---
id: ai-guvence-20
title: Gizlilik İddialarının Saldırıyla Doğrulanması
summary: Standart ve DP model çiftlerini aynı sentetik üyelik deneyinde karşılaştır; fayda kaybı ve saldırı başarısındaki azalışı ölç.
esleme: ai-guvence-17, ai-guvence-19, ai-guvence-39
timeout: 45
---

::: anlat Gizlilik iddiası karşılaştırmalı deneyle sınanır
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Eşleşmiş modellerin fayda ve üyelik saldırısı ölçümlerini birlikte verir | Görevler 1–3 görünür sentetik JSON model çiftleri; son görev gerçek standart ve örnek-başı kırpma/Gaussian gürültülü CPU eğitimlerini karşılaştırır | Düşük AUC biçimsel DP kanıtı değildir; canlı kolların epoch sayıları da farklı olduğundan fark yalnız gürültüye bağlanamaz |

> [!NOT]
> `veri/model_cifti.json` ve `veri/iddia_esikleri.json` elle hazırlanmış sentetik öğretim verisidir. Setup her çalıştırmada geçici dizine yeniden kopyalar; kalıcılık yoktur. Başlangıç kodları dosyaları gerçekten okur; aynı çalıştırmada bellekte kopyayı değiştirerek deneme yapabilirsin. Son gerçek deneyin `PAFTA_DATA/calisma/ai-guvence-20/ayarlar.json` kopyası ayrıdır ve kalıcıdır; varsa üzerine yazılmaz. Gizli kontrol girdileri öğrenci dosyasından bağımsızdır.

Bir DP modelin gizlilik-fayda iddiasını değerlendirirken aynı veri bölünmesi, saldırı yöntemi ve ölçüm düzeni kullanılan standart modelle karşılaştırma yapılır. Bu derste her deney grubunda tam olarak bir `standart` ve bir `dp` kaydı bulunur.

Görevler 1–3 sentetik dosya metrikleriyle çalışır; son görev sentetik veride gerçek PyTorch modelleri eğitir ve ölçer. ART veya Opacus çağrılmaz, kişisel veri kullanılmaz. Amaç aynı deney düzenindeki sonuçları doğru eşleştirmek ve iddia koşullarını denetlenebilir biçimde uygulamaktır.
:::

::: anlat Saldırı başarısındaki azalış biçimsel garanti değildir
Doğruluk kaybı `standart_dogruluk-dp_dogruluk`, AUC azalışı `standart_auc-dp_auc`, avantaj azalışı `standart_avantaj-dp_avantaj` olarak hesaplanır. Pozitif azalış DP modelde saldırı başarısının düştüğünü; negatif doğruluk kaybı ise DP modelin daha yüksek doğruluk verdiğini gösterir.

Deneysel destek için DP AUC üst sınırı aşmamalı, AUC azalışı alt sınıra ulaşmalı ve doğruluk kaybı üst sınırı aşmamalıdır. Üç koşulda da eşitlik kabul edilir. Bu sonuç yalnız verilen saldırı ve fixture için iddiayı destekler; diferansiyel gizlilik garantisini kanıtlamaz veya çürütmez.
:::

::: anlat Kayıt eşleştirmeden dürüst gizlilik yorumuna
Gizlilik iddiası iki ayrı tür kanıt gerektirebilir: tanımlı bir saldırıya karşı deneysel sonuç ve belirli bir mekanizmanın biçimsel güvencesi. Bu ders ilkinin raporlanmasını öğretir. AUC düşmesi, bu skorla üyeleri ayırmanın zorlaştığını gösterebilir; bütün saldırıları kapsayan garanti üretmez. Buna karşılık belirli bir mekanizma için yapılmış matematiksel bütçe hesabı da modelin görev doğruluğunu tek başına söylemez. Fayda, saldırı başarısı ve garanti kapsamını aynı raporda ayrı alanlarda tutmak gerekir. Sentetik dosyada model türüne dp yazmak o kaydın üretildiği yöntemi doğruladığın anlamına gelmez.

Önce `veri/model_cifti.json` içindeki iki kaydı ham biçimde yazdır. Grup, aynı karşılaştırmaya ait kayıtları eşler; model türü hangi kolun standart, hangisinin gizlilik mekanizmalı olarak sunulduğunu belirtir. Kimliklerin farklı, grubun aynı ve her türden tam bir kayıt bulunması gerekir. Liste sırasına bakarak ilkini standart saymak, dosya sırası değiştiğinde sonuçların işaretini tersine çevirebilir. İlk görev bu kayıtların tek tek şemasını doğrular; ikinci görev tam çift ilişkisini denetler. Bir kimliğin iki kez görünmesi veya başka gruptaki iki modelin karşılaştırılması görünürde geçerli sayılarla yanlış rapor üretir.

İkinci görev farkları her zaman standart eksi diğer kol yönünde hesaplar. Doğruluk kaybı negatif çıkarsa mekanizmalı model bu örnekte daha yüksek doğruluk vermiştir; sonucu sıfıra kırpma. AUC azalışı pozitifse verilen saldırı metriği düşmüştür. Avantaj azalışı ise seçilmiş çalışma noktasına ait başka bir ölçümdür; AUC ile eş anlamlı değildir. Yuvarlama yalnız görüntüleme içindir. Üçüncü görev `veri/iddia_esikleri.json` dosyasındaki üç koşulu birlikte uygular: mekanizmalı AUC üst sınırı, en az AUC azalışı ve en fazla doğruluk kaybı. Tam eşikte eşitlik uygundur. Yalnız iki koşulu kontrol etmek fayda veya saldırı sınırını sessizce devre dışı bırakır.

Görünür dosyadan bir kayıt kopyası çıkarıp yalnız doğruluğunu değiştir. Ölçümlerin hangilerinin değiştiğine ve destekli kararının nasıl etkilendiğine bak. Sonra AUC değerini değiştirip aynı işlemi yap. Bu alıştırma metriklerin bağımsız alanlarını görmene yardım eder; dosyadaki sayıyı değiştirmek canlı modelin davranışını değiştirmez. Gizli kontrol başka örnekler ve sınır değerleri kullandığı için görünür cevabı sabit döndürmek yeterli değildir. Başlangıç kodları özellikle şema kontrolü, fark yönü veya koşulların birlikte uygulanması bakımından kusurludur; çalışmaları doğru olduklarını göstermez.

Son görevde standart model ile gradyanları örnek başına kırpılıp Gaussian gürültüsü eklenen model gerçekten eğitilir. Aynı seed ile veri üretilir ve doğru sınıf olasılıklarından üyelik AUC hesaplanır. Mevcut düzende standart kol 35, gürültülü kol 8 epoch çalışır. Bu nedenle eğitim süresi de değişen bir faktördür: AUC farkını yalnız gürültünün nedensel etkisi olarak sunamazsın. Bu görev iki eğitim düzeninin sonucunu ölçer. Yalnız gürültü etkisini ayırmak için ayrıca epoch sayısı ve diğer ayarlar eşit tutulan kontrollü kollar gerekir. Deney davranışı burada değiştirilmez; sınırı açıkça raporlanır.

Saldırgan başka bir skor veya daha güçlü bir saldırı seçebilir; savunma yalnız tek AUC düşüşüne dayanırsa bu olasılığı atlar. İki seed de gözlenir ama bu küçük örneklem bütün veri dağılımlarını temsil etmez. Gerçek görevde bicimsel_garanti alanı bu yüzden False kalır. Açık seed ve ham eğitim izleri sentetik öğretim içindir; özel veride güvenli yayın kanıtı değildir. Çıktıda model hash'i, eğitim ayarları, ham skorlar ve test doğruluğunu birlikte incele. Destek koşullarının çıkmaması görevin başarısız olduğu anlamına gelmez; doğru hesaplama ve dürüst yorumlama da geçerli deney sonucudur.
:::

::: tahmin Karşılaştırma farklarını tahmin et
Üç çıktı satırını yaz:

```python
print(round(0.8 - 0.75, 6))
print(round(0.8 - 0.6, 6))
print(0.6 <= 0.6 and 0.2 >= 0.2 and 0.05 <= 0.05)
```

???

```cikti
0.05
0.2
True
```

İlk satır doğruluk kaybını, ikinci satır AUC azalışını, üçüncü satır üç destek koşulunun eşikte eşitlik kabul ettiğini gösterir.
:::

::: gorev 1 · Üyelik saldırısı deney kaydını doğrula
`saldiri_deneyi_dogrula(kayit)` işlevini yaz. Kayıt tam olarak `id`, `grup`, `model_turu`, `dogruluk`, `uyelik_auc`, `avantaj` alanlarını taşır. Kimlik ve grup 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren stringdir. Model türü yalnız `standart` veya `dp` olur.

Doğruluk ve AUC bool olmayan sonlu sayı ve `[0,1]`; avantaj bool olmayan sonlu sayı ve `[-1,1]` aralığındadır. Geçersiz veride `ValueError` yükselt. Bağımsız sözlük kopyası döndür ve girdiyi değiştirme.

```starter
def saldiri_deneyi_dogrula(kayit):
    # KUSURLU BAŞLANGIÇ KODU: model türü, şema ve sayısal sınırları doğrulamadan kaydı kopyalıyor.
    return dict(kayit)

from ai_guvence_veri import json_yukle
for kayit in json_yukle("veri/model_cifti.json"):
    print(saldiri_deneyi_dogrula(kayit))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-20")
```

```test
import copy
K = {"id": "dp-1", "grup": "deney-1", "model_turu": "dp", "dogruluk": 0.75, "uyelik_auc": 0.6, "avantaj": 0.2}
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K) != K or fn(K) is K or K != once:
            return False
        sinir = dict(K, id="a" * 64, grup="b" * 64, model_turu="standart", dogruluk=0, uyelik_auc=1, avantaj=-1)
        if fn(sinir) != sinir or fn(dict(sinir, dogruluk=1, uyelik_auc=0, avantaj=1))["avantaj"] != 1:
            return False
        for kayit in [
            None, [], dict(K, ek=1), dict(K, id=""), dict(K, id="a b"), dict(K, id="a" * 65), dict(K, id=None),
            dict(K, grup=""), dict(K, grup="a b"), dict(K, grup="a" * 65), dict(K, grup=None),
            dict(K, model_turu="Standart"), dict(K, model_turu="diger"), dict(K, model_turu=None), dict(K, model_turu=1),
            dict(K, dogruluk=True), dict(K, dogruluk="0.75"), dict(K, dogruluk=float("nan")), dict(K, dogruluk=-0.1), dict(K, dogruluk=1.1),
            dict(K, uyelik_auc=True), dict(K, uyelik_auc="0.6"), dict(K, uyelik_auc=float("inf")), dict(K, uyelik_auc=-0.1), dict(K, uyelik_auc=1.1),
            dict(K, avantaj=True), dict(K, avantaj="0.2"), dict(K, avantaj=float("nan")), dict(K, avantaj=-1.1), dict(K, avantaj=1.1),
        ]:
            try:
                fn(kayit)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(saldiri_deneyi_dogrula), "deney şeması, model türü, metrik aralıkları ve kopya korunmalı")
def m_tur(kayit):
    return saldiri_deneyi_dogrula(dict(kayit, model_turu="diger"))
def m_auc(kayit):
    return saldiri_deneyi_dogrula(dict(kayit, uyelik_auc=2))
def m_avantaj(kayit):
    return saldiri_deneyi_dogrula(dict(kayit, avantaj=-2))
for ad, mutant in [("model türünü bozan", m_tur), ("AUC sınırını bozan", m_auc), ("avantaj sınırını bozan", m_avantaj)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def saldiri_deneyi_dogrula(kayit):
    import math
    import re
    if not isinstance(kayit, dict):
        raise ValueError("kayıt sözlük olmalı")
    if set(kayit) != {"id", "grup", "model_turu", "dogruluk", "uyelik_auc", "avantaj"}:
        raise ValueError("kayıt şeması geçersiz")
    for alan in ("id", "grup"):
        if not isinstance(kayit[alan], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit[alan]):
            raise ValueError(alan + " geçersiz")
    if kayit["model_turu"] not in ("standart", "dp"):
        raise ValueError("model türü geçersiz")
    for alan, alt in (("dogruluk", 0), ("uyelik_auc", 0), ("avantaj", -1)):
        deger = kayit[alan]
        if isinstance(deger, bool) or not isinstance(deger, (int, float)):
            raise ValueError(alan + " sayı olmalı")
        if not math.isfinite(deger) or deger < alt or deger > 1:
            raise ValueError(alan + " geçersiz")
    return dict(kayit)

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    for kayit in json_yukle("veri/model_cifti.json"):
        print(saldiri_deneyi_dogrula(kayit))
```

```hint
Kimlik ve grup için aynı deseni uygula. Avantajın alt sınırının sıfır değil eksi bir olduğunu koru.
```
:::

::: gorev 2 · Standart ve DP model çiftini karşılaştır
`deney_cifti_karsilastir(kayitlar)` işlevini yaz. Girdi tam iki kayıtlık listedir; kayıtlar ilk görevdeki şemayı taşır, kimlikleri farklı, grupları aynı olur ve bir kayıt `standart`, diğeri `dp` olmalıdır. Girdi sırası önemli değildir. Geçersiz veride `ValueError` yükselt.

`{"grup":G,"standart_id":D,"dp_id":D,"dogruluk_kaybi":X,"auc_azalisi":X,"avantaj_azalisi":X}` döndür. Üç fark standart eksi DP olarak hesaplanır ve altı ondalık basamağa yuvarlanır; negatif değerler korunur. Girdiyi değiştirme.

```starter
def deney_cifti_karsilastir(kayitlar):
    import math
    import re
    if not isinstance(kayitlar, list) or len(kayitlar) != 2:
        raise ValueError("tam iki kayıt gerekli")
    for x in kayitlar:
        if not isinstance(x, dict) or set(x) != {"id", "grup", "model_turu", "dogruluk", "uyelik_auc", "avantaj"}:
            raise ValueError("kayıt şeması geçersiz")
        for alan in ("id", "grup"):
            if not isinstance(x[alan], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", x[alan]):
                raise ValueError(alan + " geçersiz")
        if x["model_turu"] not in ("standart", "dp"):
            raise ValueError("model türü geçersiz")
        for alan, alt in (("dogruluk", 0), ("uyelik_auc", 0), ("avantaj", -1)):
            deger = x[alan]
            if isinstance(deger, bool) or not isinstance(deger, (int, float)):
                raise ValueError(alan + " sayı olmalı")
            if not math.isfinite(deger) or deger < alt or deger > 1:
                raise ValueError(alan + " geçersiz")
    if kayitlar[0]["id"] == kayitlar[1]["id"]:
        raise ValueError("kimlikler farklı olmalı")
    if kayitlar[0]["grup"] != kayitlar[1]["grup"]:
        raise ValueError("gruplar aynı olmalı")
    if {x["model_turu"] for x in kayitlar} != {"standart", "dp"}:
        raise ValueError("bir standart ve bir DP kaydı gerekli")
    # KUSURLU BAŞLANGIÇ KODU: AUC azalışının yönünü ters hesaplıyor.
    standart = next(x for x in kayitlar if x["model_turu"] == "standart")
    dp = next(x for x in kayitlar if x["model_turu"] == "dp")
    return {"grup": standart["grup"], "standart_id": standart["id"], "dp_id": dp["id"], "dogruluk_kaybi": round(standart["dogruluk"] - dp["dogruluk"], 6), "auc_azalisi": round(dp["uyelik_auc"] - standart["uyelik_auc"], 6), "avantaj_azalisi": round(standart["avantaj"] - dp["avantaj"], 6)}

from ai_guvence_veri import json_yukle
print(deney_cifti_karsilastir(json_yukle("veri/model_cifti.json")))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-20")
```

```test
import copy
S = {"id": "s-1", "grup": "g-1", "model_turu": "standart", "dogruluk": 0.8, "uyelik_auc": 0.8, "avantaj": 0.4}
D = {"id": "d-1", "grup": "g-1", "model_turu": "dp", "dogruluk": 0.75, "uyelik_auc": 0.6, "avantaj": 0.2}
def sozlesme(fn):
    try:
        once = copy.deepcopy([D, S])
        beklenen = {"grup": "g-1", "standart_id": "s-1", "dp_id": "d-1", "dogruluk_kaybi": 0.05, "auc_azalisi": 0.2, "avantaj_azalisi": 0.2}
        if fn([D, S]) != beklenen or fn([S, D]) != beklenen or [D, S] != once:
            return False
        negatif = fn([dict(S, dogruluk=0.6, uyelik_auc=0.5, avantaj=0.1), D])
        if negatif["dogruluk_kaybi"] != -0.15 or negatif["auc_azalisi"] != -0.1 or negatif["avantaj_azalisi"] != -0.1:
            return False
        yuvarla = fn([dict(S, dogruluk=0.6666667, uyelik_auc=0.6666667, avantaj=0.6666667), dict(D, dogruluk=0.3333333, uyelik_auc=0.3333333, avantaj=0.3333333)])
        if yuvarla["dogruluk_kaybi"] != 0.333333 or yuvarla["auc_azalisi"] != 0.333333 or yuvarla["avantaj_azalisi"] != 0.333333:
            return False
        sinir = fn([dict(S, id="a" * 64, grup="b" * 64, dogruluk=1, uyelik_auc=1, avantaj=1), dict(D, grup="b" * 64, dogruluk=0, uyelik_auc=0, avantaj=-1)])
        if sinir["dogruluk_kaybi"] != 1 or sinir["avantaj_azalisi"] != 2:
            return False
        for kayitlar in [
            None, {}, (S, D), [], [S], [S, D, D], [None, D], [S, dict(D, ek=1)],
            [S, dict(D, grup="g-2")], [S, dict(S, id="s-2")], [D, dict(D, id="d-2")], [S, dict(D, id=S["id"])],
            [S, dict(D, id=123)], [S, dict(D, id="a b")], [S, dict(D, id="a" * 65)], [S, dict(D, dogruluk=True)], [S, dict(D, dogruluk="0.5")], [S, dict(D, dogruluk=-0.1)],
            [S, dict(D, uyelik_auc=float("nan"))], [S, dict(D, uyelik_auc=-0.1)], [S, dict(D, avantaj=-1.1)], [S, dict(D, avantaj=1.1)], [S, dict(D, model_turu="diger")], [S, dict(D, model_turu=[])],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(deney_cifti_karsilastir), "çift eşleştirme, standart eksi DP farkları ve sıra bağımsızlığı korunmalı")
def m_grup(kayitlar):
    return deney_cifti_karsilastir([dict(kayitlar[0], grup="baska"), kayitlar[1]])
def m_tur(kayitlar):
    return deney_cifti_karsilastir([dict(kayitlar[0], model_turu=kayitlar[1]["model_turu"]), kayitlar[1]])
def m_auc(kayitlar):
    return deney_cifti_karsilastir([dict(kayitlar[0], uyelik_auc=0), dict(kayitlar[1], uyelik_auc=0)])
for ad, mutant in [("grubu bölen", m_grup), ("model türünü birleştiren", m_tur), ("AUC farkını silen", m_auc)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def deney_cifti_karsilastir(kayitlar):
    import math
    import re
    if not isinstance(kayitlar, list) or len(kayitlar) != 2:
        raise ValueError("tam iki kayıt gerekli")
    for x in kayitlar:
        if not isinstance(x, dict) or set(x) != {"id", "grup", "model_turu", "dogruluk", "uyelik_auc", "avantaj"}:
            raise ValueError("kayıt şeması geçersiz")
        for alan in ("id", "grup"):
            if not isinstance(x[alan], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", x[alan]):
                raise ValueError(alan + " geçersiz")
        if x["model_turu"] not in ("standart", "dp"):
            raise ValueError("model türü geçersiz")
        for alan, alt in (("dogruluk", 0), ("uyelik_auc", 0), ("avantaj", -1)):
            deger = x[alan]
            if isinstance(deger, bool) or not isinstance(deger, (int, float)):
                raise ValueError(alan + " sayı olmalı")
            if not math.isfinite(deger) or deger < alt or deger > 1:
                raise ValueError(alan + " geçersiz")
    if kayitlar[0]["id"] == kayitlar[1]["id"]:
        raise ValueError("kimlikler farklı olmalı")
    if kayitlar[0]["grup"] != kayitlar[1]["grup"]:
        raise ValueError("gruplar aynı olmalı")
    if {x["model_turu"] for x in kayitlar} != {"standart", "dp"}:
        raise ValueError("bir standart ve bir DP kaydı gerekli")
    standart = next(x for x in kayitlar if x["model_turu"] == "standart")
    dp = next(x for x in kayitlar if x["model_turu"] == "dp")
    return {"grup": standart["grup"], "standart_id": standart["id"], "dp_id": dp["id"], "dogruluk_kaybi": round(standart["dogruluk"] - dp["dogruluk"], 6), "auc_azalisi": round(standart["uyelik_auc"] - dp["uyelik_auc"], 6), "avantaj_azalisi": round(standart["avantaj"] - dp["avantaj"], 6)}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    print(deney_cifti_karsilastir(json_yukle("veri/model_cifti.json")))
```

```hint
Kayıtları model türüne göre adlandırdıktan sonra farkları hep standart eksi DP sırasıyla hesapla.
```
:::

::: gorev 3 · Gizlilik-fayda iddiasının deneysel desteğini raporla
`gizlilik_iddiasi_raporu(kayitlar, dp_auc_ust, min_auc_azalisi, max_dogruluk_kaybi)` işlevini yaz. Kayıtlar ilk görevdeki şemayı taşıyan boş olmayan listedir; bütün kimlikler benzersizdir ve her grup tam bir standart-DP çifti içerir. DP AUC üst sınırı `[0,1]`, diğer iki sınır `[-1,1]` aralığında bool olmayan sonlu sayıdır. Geçersiz veride `ValueError` yükselt.

Her grup için `{"grup":G,"dp_auc":X,"auc_azalisi":X,"avantaj_azalisi":X,"dogruluk_kaybi":X,"destekli":BOOL}` üret ve gruba göre sırala. Destek için ham DP AUC üst sınıra eşit veya küçük, ham AUC azalışı alt sınıra eşit veya büyük, ham doğruluk kaybı üst sınıra eşit veya küçük olmalıdır. Destekli gruplardan en düşük ham DP AUC, eşitlikte en düşük ham doğruluk kaybı, sonra alfabetik grup seçilir. `{"satirlar":[...],"destekli_sayi":N,"secilen":G veya None}` döndür. Ölçümleri altı ondalık basamağa yuvarla ve girdiyi değiştirme.

```starter
def gizlilik_iddiasi_raporu(kayitlar, dp_auc_ust, min_auc_azalisi, max_dogruluk_kaybi):
    import math
    import re
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar boş olmayan liste olmalı")
    for deger, alt in ((dp_auc_ust, 0), (min_auc_azalisi, -1), (max_dogruluk_kaybi, -1)):
        if isinstance(deger, bool) or not isinstance(deger, (int, float)):
            raise ValueError("sınır sayı olmalı")
        if not math.isfinite(deger) or deger < alt or deger > 1:
            raise ValueError("sınır geçersiz")
    idler = set()
    for x in kayitlar:
        if not isinstance(x, dict) or set(x) != {"id", "grup", "model_turu", "dogruluk", "uyelik_auc", "avantaj"}:
            raise ValueError("kayıt şeması geçersiz")
        for alan in ("id", "grup"):
            if not isinstance(x[alan], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", x[alan]):
                raise ValueError(alan + " geçersiz")
        if x["id"] in idler:
            raise ValueError("kimlik yinelenemez")
        if x["model_turu"] not in ("standart", "dp"):
            raise ValueError("model türü geçersiz")
        for alan, alt in (("dogruluk", 0), ("uyelik_auc", 0), ("avantaj", -1)):
            deger = x[alan]
            if isinstance(deger, bool) or not isinstance(deger, (int, float)):
                raise ValueError(alan + " sayı olmalı")
            if not math.isfinite(deger) or deger < alt or deger > 1:
                raise ValueError(alan + " geçersiz")
        idler.add(x["id"])
    # KUSURLU BAŞLANGIÇ KODU: AUC koşullarından herhangi birini yeterli sayıyor.
    satirlar = []
    for grup in sorted({x["grup"] for x in kayitlar}):
        cift = [x for x in kayitlar if x["grup"] == grup]
        if len(cift) != 2 or {x["model_turu"] for x in cift} != {"standart", "dp"}:
            raise ValueError("her grup tam çift olmalı")
        standart = next(x for x in cift if x["model_turu"] == "standart")
        dp = next(x for x in cift if x["model_turu"] == "dp")
        dp_auc = dp["uyelik_auc"]
        auc_azalisi = standart["uyelik_auc"] - dp_auc
        avantaj_azalisi = standart["avantaj"] - dp["avantaj"]
        kayip = standart["dogruluk"] - dp["dogruluk"]
        destekli = (dp_auc <= dp_auc_ust or auc_azalisi >= min_auc_azalisi) and kayip <= max_dogruluk_kaybi
        satirlar.append({"grup": grup, "dp_auc": round(dp_auc, 6), "auc_azalisi": round(auc_azalisi, 6), "avantaj_azalisi": round(avantaj_azalisi, 6), "dogruluk_kaybi": round(kayip, 6), "destekli": destekli, "_dp_auc": dp_auc, "_kayip": kayip})
    destekli = [x for x in satirlar if x["destekli"]]
    secilen = min(destekli, key=lambda x: (x["_dp_auc"], x["_kayip"], x["grup"]))["grup"] if destekli else None
    for satir in satirlar:
        del satir["_dp_auc"]
        del satir["_kayip"]
    return {"satirlar": satirlar, "destekli_sayi": len(destekli), "secilen": secilen}

from ai_guvence_veri import json_yukle
esikler = json_yukle("veri/iddia_esikleri.json")
print(gizlilik_iddiasi_raporu(json_yukle("veri/model_cifti.json"), **esikler))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-20")
```

```test
import copy
def cift(g, sd, sa, sa_adv, dd, da, da_adv):
    return [
        {"id": "s-" + g, "grup": g, "model_turu": "standart", "dogruluk": sd, "uyelik_auc": sa, "avantaj": sa_adv},
        {"id": "d-" + g, "grup": g, "model_turu": "dp", "dogruluk": dd, "uyelik_auc": da, "avantaj": da_adv},
    ]
K = cift("g1", 0.75, 0.85, 0.4, 0.5, 0.6, 0.2) + cift("g2", 0.85, 0.9, 0.5, 0.82, 0.65, 0.3) + cift("g3", 0.8, 0.75, 0.4, 0.76, 0.6, 0.3) + cift("g4", 0.8, 0.8, 0.4, 0.4, 0.55, 0.2)
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        sonuc = fn(K, 0.6, 0.25, 0.25)
        if K != once or sonuc["secilen"] != "g1" or sonuc["destekli_sayi"] != 1:
            return False
        if [x["grup"] for x in sonuc["satirlar"]] != ["g1", "g2", "g3", "g4"] or [x["destekli"] for x in sonuc["satirlar"]] != [True, False, False, False]:
            return False
        if sonuc["satirlar"][0] != {"grup": "g1", "dp_auc": 0.6, "auc_azalisi": 0.25, "avantaj_azalisi": 0.2, "dogruluk_kaybi": 0.25, "destekli": True}:
            return False
        if fn(K, 0.6, 0.25, 0.25)["secilen"] != "g1" or fn(K, 0.5, 0.25, 0.25)["secilen"] is not None:
            return False
        yuvarla = fn(cift("y", 0.6666667, 0.6666667, 0.6666667, 0.3333333, 0.3333333, 0.3333333), 1, -1, 1)
        if yuvarla["satirlar"][0]["dp_auc"] != 0.333333 or yuvarla["satirlar"][0]["auc_azalisi"] != 0.333333:
            return False
        if yuvarla["satirlar"][0]["avantaj_azalisi"] != 0.333333 or yuvarla["satirlar"][0]["dogruluk_kaybi"] != 0.333333:
            return False
        sinir_kayitlar = cift("a" * 64, 1, 1, 1, 0, 0, -1)
        sinir_kayitlar[0]["id"] = "s"
        sinir_kayitlar[1]["id"] = "d"
        sinir = fn(sinir_kayitlar, 0, 1, 1)
        if sinir["destekli_sayi"] != 1 or sinir["satirlar"][0]["avantaj_azalisi"] != 2:
            return False
        if fn(cift("neg", 0.5, 0.8, 0.4, 0.8, 0.5, 0.1), 0.6, 0.2, -0.2)["destekli_sayi"] != 1:
            return False
        for kayitlar, au, aa, dk in [
            (None, 0.6, 0.2, 0.05), (K, None, 0.2, 0.05), (K, 0.6, None, 0.05), (K, 0.6, 0.2, None),
            ({}, 0.6, 0.2, 0.05), (tuple(K), 0.6, 0.2, 0.05), ([], 0.6, 0.2, 0.05), ([None], 0.6, 0.2, 0.05),
            (K[:1], 0.6, 0.2, 0.05), (K[:2] + [K[0]], 0.6, 0.2, 0.05), (K[:2] + [dict(K[2], grup="g1")], 0.6, 0.2, 0.05),
            (K[:2] + [dict(K[2], ek=1), K[3]], 0.6, 0.2, 0.05), (K[:2] + [dict(K[2], id="s-g1"), K[3]], 0.6, 0.2, 0.05),
            ([dict(K[0], id=123)] + K[1:2], 0.6, 0.2, 0.05), ([dict(K[0], id="a b")] + K[1:2], 0.6, 0.2, 0.05), ([dict(K[0], id="a" * 65)] + K[1:2], 0.6, 0.2, 0.05),
            ([dict(K[0], model_turu="dp")] + K[1:2], 0.6, 0.2, 0.05), ([dict(K[0], model_turu=[])] + K[1:2], 0.6, 0.2, 0.05), ([dict(K[0], dogruluk=True)] + K[1:2], 0.6, 0.2, 0.05), ([dict(K[0], dogruluk="0.5")] + K[1:2], 0.6, 0.2, 0.05), ([dict(K[0], dogruluk=-0.1)] + K[1:2], 0.6, 0.2, 0.05),
            ([dict(K[0], uyelik_auc=float("nan"))] + K[1:2], 0.6, 0.2, 0.05), ([dict(K[0], uyelik_auc=-0.1)] + K[1:2], 0.6, 0.2, 0.05), ([dict(K[0], avantaj=-1.1)] + K[1:2], 0.6, 0.2, 0.05), ([dict(K[0], avantaj=1.1)] + K[1:2], 0.6, 0.2, 0.05),
            (K, True, 0.2, 0.05), (K, "0.6", 0.2, 0.05), (K, float("nan"), 0.2, 0.05), (K, -0.1, 0.2, 0.05), (K, 1.1, 0.2, 0.05),
            (K, 0.6, True, 0.05), (K, 0.6, "0.2", 0.05), (K, 0.6, float("inf"), 0.05), (K, 0.6, -1.1, 0.05), (K, 0.6, 1.1, 0.05),
            (K, 0.6, 0.2, True), (K, 0.6, 0.2, "0.05"), (K, 0.6, 0.2, float("nan")), (K, 0.6, 0.2, -1.1), (K, 0.6, 0.2, 1.1),
        ]:
            try:
                fn(kayitlar, au, aa, dk)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(gizlilik_iddiasi_raporu), "çift bütünlüğü, üç destek koşulu ve seçim korunmalı")
def m_auc(kayitlar, au, aa, dk):
    return gizlilik_iddiasi_raporu([dict(x, uyelik_auc=0.5) for x in kayitlar], au, aa, dk)
def m_dogruluk(kayitlar, au, aa, dk):
    return gizlilik_iddiasi_raporu([dict(x, dogruluk=0.5) for x in kayitlar], au, aa, dk)
def m_avantaj(kayitlar, au, aa, dk):
    return gizlilik_iddiasi_raporu([dict(x, avantaj=0) for x in kayitlar], au, aa, dk)
for ad, mutant in [("AUC'yi değiştiren", m_auc), ("doğruluğu değiştiren", m_dogruluk), ("avantajı silen", m_avantaj)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def gizlilik_iddiasi_raporu(kayitlar, dp_auc_ust, min_auc_azalisi, max_dogruluk_kaybi):
    import math
    import re
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar boş olmayan liste olmalı")
    for deger, alt in ((dp_auc_ust, 0), (min_auc_azalisi, -1), (max_dogruluk_kaybi, -1)):
        if isinstance(deger, bool) or not isinstance(deger, (int, float)):
            raise ValueError("sınır sayı olmalı")
        if not math.isfinite(deger) or deger < alt or deger > 1:
            raise ValueError("sınır geçersiz")
    idler = set()
    for x in kayitlar:
        if not isinstance(x, dict) or set(x) != {"id", "grup", "model_turu", "dogruluk", "uyelik_auc", "avantaj"}:
            raise ValueError("kayıt şeması geçersiz")
        for alan in ("id", "grup"):
            if not isinstance(x[alan], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", x[alan]):
                raise ValueError(alan + " geçersiz")
        if x["id"] in idler:
            raise ValueError("kimlik yinelenemez")
        if x["model_turu"] not in ("standart", "dp"):
            raise ValueError("model türü geçersiz")
        for alan, alt in (("dogruluk", 0), ("uyelik_auc", 0), ("avantaj", -1)):
            deger = x[alan]
            if isinstance(deger, bool) or not isinstance(deger, (int, float)):
                raise ValueError(alan + " sayı olmalı")
            if not math.isfinite(deger) or deger < alt or deger > 1:
                raise ValueError(alan + " geçersiz")
        idler.add(x["id"])
    satirlar = []
    for grup in sorted({x["grup"] for x in kayitlar}):
        cift = [x for x in kayitlar if x["grup"] == grup]
        if len(cift) != 2 or {x["model_turu"] for x in cift} != {"standart", "dp"}:
            raise ValueError("her grup tam çift olmalı")
        standart = next(x for x in cift if x["model_turu"] == "standart")
        dp = next(x for x in cift if x["model_turu"] == "dp")
        dp_auc = dp["uyelik_auc"]
        auc_azalisi = standart["uyelik_auc"] - dp_auc
        avantaj_azalisi = standart["avantaj"] - dp["avantaj"]
        kayip = standart["dogruluk"] - dp["dogruluk"]
        destekli = dp_auc <= dp_auc_ust and auc_azalisi >= min_auc_azalisi and kayip <= max_dogruluk_kaybi
        satirlar.append({"grup": grup, "dp_auc": round(dp_auc, 6), "auc_azalisi": round(auc_azalisi, 6), "avantaj_azalisi": round(avantaj_azalisi, 6), "dogruluk_kaybi": round(kayip, 6), "destekli": destekli, "_dp_auc": dp_auc, "_kayip": kayip})
    destekli = [x for x in satirlar if x["destekli"]]
    secilen = min(destekli, key=lambda x: (x["_dp_auc"], x["_kayip"], x["grup"]))["grup"] if destekli else None
    for satir in satirlar:
        del satir["_dp_auc"]
        del satir["_kayip"]
    return {"satirlar": satirlar, "destekli_sayi": len(destekli), "secilen": secilen}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    esikler = json_yukle("veri/iddia_esikleri.json")
    print(gizlilik_iddiasi_raporu(json_yukle("veri/model_cifti.json"), **esikler))
```

```hint
Önce grup bütünlüğünü doğrula. Destek koşullarını ham farklarla ayrı ayrı uygula; avantaj azalışını da raporda tut.
```
:::


::: anlat Canlı CPU deneyi ve düzenlenebilir sentetik ayar
Önce [sentetik ayar dosyasını](/data/ai-guvence-20-ayarlar.txt) açıp seed, ornek, sigma alanlarını incele. Bu JSON örneği kaydedilmiş model çıktısı değildir. Yeni görev gerçek küçük MLP'yi torch autograd ile CPU'da eğitir; ağ/model indirme yoktur.

Çalıştır ilk kullanımda örneği `PAFTA_DATA/calisma/ai-guvence-20/ayarlar.json` konumuna yalnız yoksa kopyalar, tam yolu ekranda yazar. Göreli PAFTA_DATA proje köküne göre çözülür. Öğrenci bu kalıcı JSON'u metin düzenleyicide değiştirebilir (seed:0..2**30-1, ornek:8..32, sigma:0.5..8); yeniden Çalıştır düzenlemeyi korur. Tarayıcıdaki örnek salt okunur indirme bağlantısıdır; kalıcı kopyayı kendi editöründe aç. Kontrol bağımsız test ayarı kullanır, örneği değiştirmek beklenen cevabı değiştirmez.

Yalnız sentetik veriler kullanılır. Saldırının kazanması veya gizlilik iddiasının desteklenmesi PASS şartı değildir. Küçük deney sohbet modelinin gizliliğine genellenemez. DP eğitimli deneylerde açık tohum, ham veriler ve eğitim izleri öğretim içindir; bu yayınlar özel veri için DP garantisi taşımaz. Bütçe yalnız sabit boyutlu replace-one tam batch Gaussian ağırlık mekanizması içindir, ham izlere değil. Güvenli üretim RNG/accountant denetimi yapılmaz.
:::

::: gorev Gerçek deney · CPU gizlilik ölçümü 20
`olc(a,b,limit,drop,maxloss)` standart a ve DP-eğitimli b sözlüklerinden (`auc,dogruluk`) altı ondalıklı `auc_azalisi=a.auc-b.auc`, `dogruluk_kaybi=a.dogruluk-b.dogruluk`, bool `destekli` ve `bicimsel_garanti=False` döndürsün. Destek: ham b.auc<=limit VE ham AUC azalışı>=drop VE ham doğruluk kaybı<=maxloss. Deneysel desteğin çıkmaması geçmeyi engellemez. Düşük AUC biçimsel DP kanıtı değildir.

Girdileri değiştirme. Çalıştır gerçek öğrenci dosyasıyla sonuç ve kanıt yolunu gösterir; Kontrol farklı veri ve tohumlarda bağımsız hesap, boş/sabit/yanlış çözüm denetimi yapar. torch yokluğu PASS değildir.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 180
```

```starter
import ai_lab
def olc(a, b, limit, drop, maxloss):
    return {}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_17_20 as deney
    deney.goster(20,olc)
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
kontrol(deney.sozlesme(20,olc),'Görülmemiş sınırlar, eşitlik ve yanlış ölçüm reddi')
kontrol(olc({'auc': 2/3, 'dogruluk': 2/3}, {'auc': 1/3, 'dogruluk': 1/3}, 0.5, 0.3, 0.4) == {'auc_azalisi': 0.333333, 'dogruluk_kaybi': 0.333333, 'destekli': True, 'bicimsel_garanti': False} and olc({'auc': 0.75, 'dogruluk': 0.875}, {'auc': 0.5, 'dogruluk': 0.75}, 0.5, 0.25, 0.125)['destekli'] is True and olc({'auc': 0.75, 'dogruluk': 0.875}, {'auc': 0.51, 'dogruluk': 0.75}, 0.5, 0.2, 0.125)['destekli'] is False and olc({'auc': 0.74, 'dogruluk': 0.875}, {'auc': 0.5, 'dogruluk': 0.75}, 0.5, 0.25, 0.125)['destekli'] is False and olc({'auc': 0.75, 'dogruluk': 0.875}, {'auc': 0.5, 'dogruluk': 0.74}, 0.5, 0.25, 0.125)['destekli'] is False, '6 basamak yuvarlama ve üç bağımsız sınır koşulu')
with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp)/'ayar.json'
    p.write_text('{"seed": 8320, "ornek": 13, "sigma": 1.75}',encoding='utf-8')
    r=deney.deney(20,olc,path=p)
    for name,value in r['kontroller'].items(): kontrol(value,name)
ns={}
exec("def olc(a, b, limit, drop, maxloss):\n    return dict(auc_azalisi=round(b['auc']-a['auc'],6),dogruluk_kaybi=round(a['dogruluk']-b['dogruluk'],6),destekli=b['auc']<=limit and b['auc']-a['auc']>=drop and a['dogruluk']-b['dogruluk']<=maxloss,bicimsel_garanti=False)\n",ns)
kontrol(not deney.sozlesme(20,ns['olc']),'Mutant 1 reddedilir')
ns={}
exec("def olc(a, b, limit, drop, maxloss):\n    return dict(auc_azalisi=round(a['auc']-b['auc'],6),dogruluk_kaybi=round(a['dogruluk']-b['dogruluk'],6),destekli=b['auc']<=limit and a['auc']-b['auc']>=drop,bicimsel_garanti=False)\n",ns)
kontrol(not deney.sozlesme(20,ns['olc']),'Mutant 2 reddedilir')
ns={}
exec("def olc(a, b, limit, drop, maxloss):\n    return dict(auc_azalisi=round(a['auc']-b['auc'],6),dogruluk_kaybi=round(a['dogruluk']-b['dogruluk'],6),destekli=b['auc']<=limit and a['auc']-b['auc']>=drop and a['dogruluk']-b['dogruluk']<=maxloss,bicimsel_garanti=True)\n",ns)
kontrol(not deney.sozlesme(20,ns['olc']),'Mutant 3 reddedilir')
ai_lab.kanit_yaz('guvence-20-cpu',dict(r,kabul=all(checks)))

```

```solution
import ai_lab
def olc(a, b, limit, drop, maxloss):
    return dict(auc_azalisi=round(a['auc']-b['auc'],6),dogruluk_kaybi=round(a['dogruluk']-b['dogruluk'],6),destekli=b['auc']<=limit and a['auc']-b['auc']>=drop and a['dogruluk']-b['dogruluk']<=maxloss,bicimsel_garanti=False)

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_17_20 as deney
    deney.goster(20,olc)
```

```hint
Ham eşik koşulunu yuvarlamadan uygula. AUC eşitlikte yarım katkı verir. Gürültüyü başarı garantisi olarak yorumlama.
```
:::


::: anlat Hesabın varsayımları ve birincil kaynak
Örnek başına gradyan gerçekten autograd ile hesaplanıp L2 C=1 ile kırpılır; tam batch ortalamanın sabit n, bir kayıt değiştirme komşuluğunda duyarlılığı 2C/n olur. Her adıma sigma*(2C/n) Gaussian ekleme için ideal bağımsız gizli rastgelelik varsayımıyla rho=1/(2sigma²) yazılır; adaptif adımlarda rho toplanır. epsilon=rho+2sqrt(rho log(1/delta)) dönüşümü [Bun ve Steinke, önermeler 1.3/1.6 ve bileşim](https://arxiv.org/abs/1605.02065) ile açıklanır; [Mironov, Rényi Differential Privacy](https://arxiv.org/abs/1702.07476) Gaussian RDP bileşimini sunar. Burada altörnekleme veya üretim DP-SGD sertifikasyonu yoktur. Açık tohum ve ham sonuç yayını nedeniyle bu çalıştırma özel bir üretim yayını değildir.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Teorik iddia ile ampirik saldırı denetimi (35 sn).** "Bir savunmanın 'gizliliği koruyor' iddiası, standart model ile savunmalı modeli aynı veri ve aynı üyelik saldırısı altında yan yana yarıştırarak sınanır: saldırı `AUC`'si anlamlı düşmeli ve son `AUC` üst sınırın altında kalmalıdır."
2. **Fayda kaybı kısıtı (25 sn).** "Modeli rastgele tahminciye çevirip `AUC = 0.50` almak kolaydır; geçerli bir savunma saldırı başarısını düşürürken `dogruluk_kaybi` üst sınırını aşmamalıdır."
3. **Saldırı başarısızlığı formel kanıt değildir (`bicimsel_garanti=False`) (35 sn).** "Ampirik bir saldırının başarısız olması DP kodundaki olası bir kırpma veya gürültü hatasını yakalamaya yarar (alt sınır verir), ama daha güçlü bir saldırının sızıntı bulamayacağını matematiksel olarak kanıtlamaz."
4. **Soru (25 sn).** "Kodlanmış bir `DP-SGD` hattında teorik $\varepsilon=1$ hesabı küçük görünürken ampirik üyelik saldırısı `AUC=0.85` buluyorsa ilk hangi uygulama hatalarından şüphelenirsin?"
:::
