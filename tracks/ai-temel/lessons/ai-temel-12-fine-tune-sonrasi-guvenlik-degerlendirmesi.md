---
id: ai-temel-12
title: "Fine-Tune Sonrası Güvenlik Değerlendirmesi"
summary: Temel ve ince ayarlı sonuçları aynı kayıtlarda karşılaştır, regresyonları bul ve yayın kapısı uygula.
esleme: ai-temel-11, ai-guvence-01, ai-savunma-22
timeout: 45
---

::: anlat Aynı test seti olmadan karşılaştırma zayıftır

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Değerlendirme araçları aynı vaka kimliklerinde temel/yeni sonuçları karşılaştırır | Görevler 1–3 görünür sentetik JSON kayıtları ve açık yayın eşikleri | Promptfoo, garak veya LM Evaluation Harness çalıştırıldığı anlamına gelmez |
| Torch ileri hesap, autograd ve SGD gerçek sayısal değişimi ölçer | Son görev yerel SmolLM2 son-token logitleri üstünde gerçek eğitilen token-bias katmanları | Tam dil modeli fine-tuning, gerçek jailbreak veya genel güvenlik sertifikası değildir |

> [!NOT]
> `veri/degerlendirme.json` elle hazırlanmış sentetik örnektir; canlı model kaydı değildir. İlk üç görev aynı dosyadan ilerler; gizli testler ayrıdır. Setup her Run/Check için geçici kopya oluşturur, değişiklikler kalıcı değildir. Kaynak fixture dosyasını editörde aç veya ders kodunda yüklenen kopyayı değiştirip Run ile dene. Son adım kurulu modelle gerçek hesap yapar; indirme ve dış servis yoktur.

Fine-tune sonrası değerlendirme, temel ve yeni modelin aynı girdilerdeki sonuçlarını karşılaştırmalıdır. Toplam başarı artarken bazı vakalarda güvenlik gerileyebilir. Bu kayıplar vaka kimlikleriyle raporlanmalıdır.

Görevler 1–3 önceden etiketlenmiş sentetik sonuçlarda karşılaştırma ve yayın kararı mantığını öğretir. Son adım gerçek yerel dil modeli hesabı ve SGD ile eğitilen token-bias uyarlayıcılarını değerlendirir. Promptfoo, garak ve LM Evaluation Harness bu derste kullanılmaz.
:::

::: anlat Ortalama kazanç regresyonu gizleyebilir

Önce `veri/degerlendirme.json` dosyasını açıp dört vaka kimliğini oku. `kayitlar` temel ve yeni sürüm için bool etiketler taşır; aynı sıradan iki liste çıkararak birinci görevi çalıştırırsın. İkinci görev aynı kayıtları kimlikli rapora dönüştürür. `metrikler` üçüncü görevin yayın kapısı girdisidir. Dosyada bir güvenlik iyileşmesi ve bir gerileme birlikte vardır. Örneğin temel sürümde güvenli olan kritik bir belge vakası yeni sürümde güvensiz olabilir; başka bir vaka düzelince ortalama aynı kalır. Tek yüzdeye bakarak bu iki değişimi birbirini götürmüş sayma.

Eşleştirme önemlidir: aynı indekste veya kimlikte aynı girdi olmalıdır. Temel sonuçları başka sıraya dizip yeni sonuçları olduğu gibi bırakırsan gerçekte olmayan regresyonlar üretirsin. Birinci görev sırayı koruyan sabit dört öğeli listeler kullanır; ikinci görev kimlikleri zorunlu ve benzersiz yapar. Bu küçük sözleşme bir genel değerlendirme sistemi değildir; veri birleştirme veya eksik vakaları otomatik tamamlama yapmaz. Eksik kayıtlar ve yanlış türler açık ValueError üretmelidir. Python'da True tamsayı gibi davranabilse de sonuç alanında yalnız bool, regresyon sayısında ise bool olmayan int kabul edilir.

Kazanç yeni oran eksi temel orandır; negatif değer bozulmayı, sıfır değer eşit ortalamayı gösterir. İyileşen False→True, gerileyen True→False, sabit ise iki değerin eşit olmasıdır. Sabit sınıf hem iki güvenli hem iki güvensiz sonucu içerir. Bu nedenle sabit sözcüğü tek başına güvenli demek değildir. Rapor listeleri özgün kayıt sırasını korur; kimlikleri alfabetik sıralamak çıktı sözleşmesini değiştirir. Fonksiyonların girdiyi değiştirmemesi sonraki karşılaştırmaların aynı veride yapılmasını sağlar.

Üçüncü görev bir karar kuralıdır. Doğruluk 0.8 ve güvenlik 0.95 değerlerinde eşitlik kabul edilir; regresyon sıfır olmalıdır. Üç koşul birlikte aranır. `or` kullanmak çok doğru ama güvenliği düşük bir sürümü yanlışlıkla yayımlatabilir. Hatalı metrik False gibi normal bir karar olarak gizlenmez, hata üretir. NaN ve sonsuz değerler bir oran değildir; geçerli aralığa ait değillerdir. Eşiklerin hemen altını, eşitini ve üstünü denemek yalnız rahatça geçen bir örneği çalıştırmaktan daha öğreticidir. Bu kapı bir örnek politikadır, gerçek üretim dağıtımı yapmaz.

Son görevde hazır bool sonuçlarını okumazsın. Dondurulmuş SmolLM2 gerçek istemler için son konumdaki logitleri hesaplar. Üzerine eklenen öğrenilebilir bias gerçek gradyan ve SGD ile değişir; dil modelinin tüm ağırlıkları eğitilmez. Üç sentetik tercih çifti farklı token kimlikleri kullanır. Aynı başlangıçtan olumlu kontrol ve ilk kritik vakada yanlış etikete eğitilen bozuk uyarlayıcı hazırlanır. İyi kontrol, her şeyi engelleyen kapının da yanlış olduğunu gösterir. Bozuk kontrol ölçüm hattının gerilemeyi gerçekten yakalayıp yakalamadığını sınar.

Karar uzayı yalnız chosen ve rejected tokenlarından oluşur. Softmax bütün sözlük yerine bu iki logite uygulanır; elde edilen olasılık modelin serbest üretimde genel güvenli davranma olasılığı değildir. Örneğin chosen tokenının metni yes olabilir ama bu sözcük tüm bağlamlarda güvenli sayılmaz. Etiketler yalnız sentetik göreve aittir. Değerlendirmede torch.no_grad kullanılır; öğrenme bitmiştir, ölçerken modeli veya vakayı değiştirmek karşılaştırmayı bozar. Eşikteki olasılık güvenli kabul edilir. Aynı vakaların ters sırada verilmesi oranı değiştirmez, raporun kayıt sırasını değiştirir.

Saldırgan veya hatalı raporlama sistemi kritik regresyon kimliklerini saklayabilir, yalnız toplam kazancı gösterebilir ya da temel/yeni taraflarını ters çevirebilir. Bu yüzden test yalnız yayın bool değerini değil her gerçek olasılığı, iki yönlü oranı, kritik listesini ve kayıt sırasını karşılaştırır. Gerçek finalin kapısı yeni güvenli oranı 0.95 ve sıfır kritik regresyon ister; önceki sentetik kapıdaki doğruluk alanı finalde ölçülmez. İki sözleşmeyi karıştırma. Çıktıyı yorumlarken hangi eşik ve hangi vaka grubunun kullanıldığını kanıttan kontrol et. Küçük ve kontrollü bu sonuçtan gerçek bir jailbreak başarısı veya üretime hazır güvenlik sonucu çıkarılamaz.

Güvenlik oranı yükselse bile önceden güvenli olan bir vakanın artık güvensiz olması ayrı bir risktir. Regresyon sayısını sıfıra yakın izlemek ve kritik vakalarda sıfır istemek, tek ortalamaya göre daha güçlü bir yayın politikasıdır.

Yayın kapısı sabit eşikleri açıkça uygular. Eşikteki değerler kabul edilir; eksik veya türü bozuk metrik reddedilmek yerine hata üretir ki hatalı rapor sessizce dağıtılmasın.

Kaynaklar: [Qi vd. — Fine-tuning Aligned Language Models Compromises Safety, Even When Users Do Not Intend To! (arXiv:2310.03693)](https://arxiv.org/abs/2310.03693), [OWASP Top 10 for Large Language Model Applications](https://genai.owasp.org/llm-top-10/).
:::

::: tahmin Regresyon ve kapıyı tahmin et
Üç çıktı satırını yaz:

```python
temel = [True, False, True]
yeni = [True, True, False]
print([i for i in range(3) if temel[i] and not yeni[i]])
print(round(sum(yeni) / 3, 6))
print(0.9 >= 0.8 and 0.95 >= 0.95 and 0 == 0)
```

???

```cikti
[2]
0.666667
True
```

İlk satır gerileyen vaka indeksini, ikinci satır yeni güvenlik oranını, üçüncü satır eşikteki yayın kararını gösterir.
:::

::: gorev 1 · Güvenlik kazancını ve regresyonu karşılaştır
`guvenlik_karsilastir(temel, yeni)` işlevini yaz. İki girdi de dört bool değerli listedir; geçersiz veride `ValueError` yükselt.

`{"temel_oran":T,"yeni_oran":Y,"kazanc":K,"regresyonlar":R}` döndür. Kazanç yeni eksi temel orandır. Regresyonlar temelde True, yenide False olan indekslerin artan listesidir. Girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-12")
```

```starter
from ai_temel_veri import json_yukle
def guvenlik_karsilastir(temel, yeni):
    # KUSURLU BAŞLANGIÇ KODU: regresyon yerine bütün yeni güvensiz vakaları listeler.
    t=sum(temel)/len(temel); y=sum(yeni)/len(yeni)
    return {"temel_oran":t,"yeni_oran":y,"kazanc":y-t,"regresyonlar":[i for i,v in enumerate(yeni) if not v]}

v=json_yukle("veri/degerlendirme.json")
print("Sentetik kayıtlar:",v["kayitlar"])
print("Karşılaştırma:",guvenlik_karsilastir([x["temel"] for x in v["kayitlar"]],[x["yeni"] for x in v["kayitlar"]]))
```

```test
def sozlesme(fn):
    try:
        if fn([True, False, True, False], [True, True, False, False]) != {"temel_oran": 0.5, "yeni_oran": 0.5, "kazanc": 0.0, "regresyonlar": [2]}:
            return False
        if fn([False, False, False, False], [True, True, True, True]) != {"temel_oran": 0.0, "yeni_oran": 1.0, "kazanc": 1.0, "regresyonlar": []}:
            return False
        if fn([True] * 4, [False] * 4)["regresyonlar"] != [0, 1, 2, 3]:
            return False
        import itertools
        for t0 in itertools.product((False,True),repeat=4):
            for y0 in itertools.product((False,True),repeat=4):
                t,y=list(t0),list(y0)
                out=fn(t,y)
                expected={"temel_oran":sum(t0)/4,"yeni_oran":sum(y0)/4,"kazanc":(sum(y0)-sum(t0))/4,"regresyonlar":[i for i in range(4) if t0[i] and not y0[i]]}
                if out!=expected or t!=list(t0) or y!=list(y0): return False
        for args in [ (None, [True] * 4), ([True] * 3, [True] * 4), ([True, 1, True, False], [True] * 4), ([True] * 4, None), ([True] * 4, [True, False, 0, True])]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(guvenlik_karsilastir), "oran, kazanç ve vaka regresyonu korunmalı")
def m_temel(t, y):
    return guvenlik_karsilastir([False] * 4, y)
def m_yeni(t, y):
    return guvenlik_karsilastir(t, [True] * 4)
def m_boyut(t, y):
    return guvenlik_karsilastir(t + [True], y + [True])
for ad, mutant in [("temeli bozan", m_temel), ("yeniyi bozan", m_yeni), ("boyutu bozan", m_boyut)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def guvenlik_karsilastir(temel, yeni):
    if any(not isinstance(x, list) or len(x) != 4 or any(not isinstance(v, bool) for v in x) for x in (temel, yeni)):
        raise ValueError("sonuç listesi geçersiz")
    t = sum(temel) / 4
    y = sum(yeni) / 4
    return {"temel_oran": t, "yeni_oran": y, "kazanc": y - t, "regresyonlar": [i for i in range(4) if temel[i] and not yeni[i]]}

v=json_yukle("veri/degerlendirme.json")
print("Sentetik kayıtlar:",v["kayitlar"])
print("Karşılaştırma:",guvenlik_karsilastir([x["temel"] for x in v["kayitlar"]],[x["yeni"] for x in v["kayitlar"]]))
```

```hint
İki oranı ayrı hesapla. Regresyon listesinde aynı indeksin temel değeri True ve yeni değeri False olmalı.
```
:::

::: gorev 2 · Vaka kimlikleriyle regresyon raporu üret
`regresyon_raporu(kayitlar)` işlevini yaz. Kayıtlar 1–8 öğeli listedir; her kayıt tam `id`, `temel`, `yeni` anahtarlarını içerir. Kimlikler farklı, boş olmayan stringler; sonuçlar bool değerdir. Geçersiz veride `ValueError` yükselt.

`{"iyilesen":[...],"gerileyen":[...],"sabit":[...]}` döndür. İyileşen temelde False/yenide True, gerileyen tersi, sabit iki sonucu aynı olan kimliklerdir. Her liste özgün kayıt sırasındadır.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-12")
```

```starter
from ai_temel_veri import json_yukle
def regresyon_raporu(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: değişmeyen bütün sonuçları güvenli sayıp sıralamayı değiştirir.
    return {"iyilesen":sorted(x["id"] for x in kayitlar if x["yeni"]),
            "gerileyen":sorted(x["id"] for x in kayitlar if not x["yeni"]),
            "sabit":[]}

v=json_yukle("veri/degerlendirme.json")
print("Sentetik kayıtlar:",v["kayitlar"])
print("Kimlikli rapor:",regresyon_raporu(v["kayitlar"]))
```

```test
R = [{"id": "a", "temel": False, "yeni": True}, {"id": "b", "temel": True, "yeni": False}, {"id": "c", "temel": True, "yeni": True}]
def sozlesme(fn):
    try:
        if fn(R) != {"iyilesen": ["a"], "gerileyen": ["b"], "sabit": ["c"]} or fn(R[:1]) != {"iyilesen": ["a"], "gerileyen": [], "sabit": []} or fn([{"id": "d", "temel": False, "yeni": False}]) != {"iyilesen": [], "gerileyen": [], "sabit": ["d"]}:
            return False
        sekiz = R + [dict(x, id=x["id"] + str(i)) for i, x in enumerate(R)] + R[:2]
        sekiz = [dict(x, id=str(i)) for i, x in enumerate(sekiz)]
        sekiz=[dict(x,id=k) for x,k in zip(sekiz,["z","a","m","b","q","c","y","d"])]
        expected={"iyilesen":[x["id"] for x in sekiz if not x["temel"] and x["yeni"]],
                  "gerileyen":[x["id"] for x in sekiz if x["temel"] and not x["yeni"]],
                  "sabit":[x["id"] for x in sekiz if x["temel"]==x["yeni"]]}
        if fn(sekiz)!=expected or fn(list(reversed(sekiz)))!={k:list(reversed(v)) for k,v in expected.items()}:
            return False
        import copy
        once=copy.deepcopy(R)
        fn(R)
        if R!=once: return False
        if fn(list(reversed(R)))!={"iyilesen":["a"],"gerileyen":["b"],"sabit":["c"]}: return False
        for deger in [None, [], [["id", "temel", "yeni"]], sekiz + [dict(R[0], id="9")], [dict(R[0], ek=1)], [dict(R[0], id=1)], [dict(R[0], id="")], [dict(R[0], temel=1)], [R[0], R[0]]]:
            try:
                fn(deger)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(regresyon_raporu), "vaka sınıfları, kimlik sırası ve şema korunmalı")
def m_temel(r):
    return regresyon_raporu([dict(x, temel=False) for x in r])
def m_yeni(r):
    return regresyon_raporu([dict(x, yeni=True) for x in r])
def m_boyut(r):
    return regresyon_raporu(r + [dict(r[0], id="x")])
for ad, mutant in [("temeli bozan", m_temel), ("yeniyi bozan", m_yeni), ("boyutu bozan", m_boyut)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def regresyon_raporu(kayitlar):
    if not isinstance(kayitlar, list) or not 1 <= len(kayitlar) <= 8:
        raise ValueError("kayıt listesi geçersiz")
    if any(not isinstance(x, dict) or set(x) != {"id", "temel", "yeni"} for x in kayitlar):
        raise ValueError("kayıt şeması geçersiz")
    if any(not isinstance(x["id"], str) or not x["id"] or any(not isinstance(x[a], bool) for a in ("temel", "yeni")) for x in kayitlar):
        raise ValueError("kayıt değeri geçersiz")
    if len({x["id"] for x in kayitlar}) != len(kayitlar):
        raise ValueError("kimlikler yinelenemez")
    return {"iyilesen": [x["id"] for x in kayitlar if not x["temel"] and x["yeni"]], "gerileyen": [x["id"] for x in kayitlar if x["temel"] and not x["yeni"]], "sabit": [x["id"] for x in kayitlar if x["temel"] == x["yeni"]]}

v=json_yukle("veri/degerlendirme.json")
print("Sentetik kayıtlar:",v["kayitlar"])
print("Kimlikli rapor:",regresyon_raporu(v["kayitlar"]))
```

```hint
Üç listeyi ayrı üret; sabit sınıf iki bool değerin eşitliğidir.
```
:::

::: gorev 3 · Sabit eşikli yayın kapısı uygula
`yayin_kapisi(metrik)` işlevini yaz. Metrik tam `dogruluk`, `guvenlik`, `regresyon` anahtarlı sözlüktür. İlk iki alan bool olmayan 0–1 arası sayı, regresyon bool olmayan 0–8 arası tamsayıdır. Geçersiz veride `ValueError` yükselt.

Doğruluk en az 0.8, güvenlik en az 0.95 ve regresyon tam 0 ise True, aksi halde False döndür. Eşikler dahildir; girdiyi değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-12")
```

```starter
from ai_temel_veri import json_yukle
def yayin_kapisi(metrik):
    # KUSURLU BAŞLANGIÇ KODU: koşulların tümü yerine tek birinin sağlanmasını yeterli sayar.
    return metrik["dogruluk"]>=0.8 or metrik["guvenlik"]>=0.95 or metrik["regresyon"]==0

v=json_yukle("veri/degerlendirme.json")
print("Sentetik metrikler:",v["metrikler"])
for m in v["metrikler"]: print("Yayın:",m,yayin_kapisi(m))
```

```test
M = {"dogruluk": 0.9, "guvenlik": 1.0, "regresyon": 0}
def sozlesme(fn):
    try:
        if not fn(M) or not fn({"dogruluk": 0.8, "guvenlik": 0.95, "regresyon": 0}) or not fn(dict(M, dogruluk=1)):
            return False
        if fn(dict(M, dogruluk=0)) or fn(dict(M, guvenlik=0)) or fn(dict(M, dogruluk=0.79)) or fn(dict(M, guvenlik=0.94)) or fn(dict(M, regresyon=1)) or fn(dict(M, regresyon=8)):
            return False
        once=dict(M)
        if type(fn(M)) is not bool or M!=once: return False
        if fn(dict(M,dogruluk=0.8-1e-10)) or fn(dict(M,guvenlik=0.95-1e-10)): return False
        for deger in [dict(M,dogruluk=float("nan")),dict(M,guvenlik=float("nan")),dict(M,dogruluk=float("inf")),dict(M,guvenlik=float("-inf")),None, {}, dict(M, ek=1), dict(M, dogruluk=True), dict(M, dogruluk="0.9"), dict(M, dogruluk=-0.1), dict(M, dogruluk=1.1), dict(M, guvenlik=-0.1), dict(M, guvenlik=1.1), dict(M, regresyon=True), dict(M, regresyon=-1), dict(M, regresyon=9), dict(M, regresyon=0.0)]:
            try:
                fn(deger)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
raises(ValueError, yayin_kapisi, {"dogruluk": 0.9, "guvenlik": 1.0},
       msg="Eksik regresyon sayısı sıfır kabul edilemez")
raises(ValueError, yayin_kapisi, dict(M, guvenlik=True),
       msg="Güvenlik oranında bool kabul edilmez")
raises(ValueError, yayin_kapisi, dict(M, dogruluk=0.0, regresyon="0"),
       msg="Başka bir eşik sağlanmasa da bütün metrikler doğrulanır")
ok(sozlesme(yayin_kapisi), "yayın eşikleri, regresyon ve metrik şeması korunmalı")
def m_dogruluk(m):
    return yayin_kapisi(dict(m, dogruluk=0))
def m_guvenlik(m):
    return yayin_kapisi(dict(m, guvenlik=0))
def m_regresyon(m):
    return yayin_kapisi(dict(m, regresyon=1))
for ad, mutant in [("doğruluğu bozan", m_dogruluk), ("güvenliği bozan", m_guvenlik), ("regresyonu bozan", m_regresyon)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def yayin_kapisi(metrik):
    if not isinstance(metrik, dict) or set(metrik) != {"dogruluk", "guvenlik", "regresyon"}:
        raise ValueError("metrik şeması geçersiz")
    if any(not isinstance(metrik[a], (int, float)) or isinstance(metrik[a], bool) or not 0 <= metrik[a] <= 1 for a in ("dogruluk", "guvenlik")):
        raise ValueError("oran geçersiz")
    if not isinstance(metrik["regresyon"], int) or isinstance(metrik["regresyon"], bool) or not 0 <= metrik["regresyon"] <= 8:
        raise ValueError("regresyon geçersiz")
    return metrik["dogruluk"] >= 0.8 and metrik["guvenlik"] >= 0.95 and metrik["regresyon"] == 0

v=json_yukle("veri/degerlendirme.json")
print("Sentetik metrikler:",v["metrikler"])
for m in v["metrikler"]: print("Yayın:",m,yayin_kapisi(m))
```

```hint
Son ifadede üç koşulu `and` ile birleştir; oranlarda `>=`, regresyonda `== 0` kullan.
```
:::

::: anlat Gerçek deney: önce/sonra kararlarını modelden yeniden ölç
Önceki görevde güvenli/güvensiz sonuçları hazır bool dizileriydi. Burada SmolLM2'nin gerçek son-token logitleri üzerine eklenen küçük bir token-bias katmanı **gerçek SGD ile** eğitilir. Aynı tabandan biri olumlu kontrol, diğeri ilk kritik vaka için bilerek yanlış etikete eğitilmiş iki uyarlayıcı çıkarılır. Gerçek LM hesabı çalışma başına yapılır; dondurulmuş taban tekrar kullanılır. Hazır etiketlenmiş model sonuçları verilmez: güvenli-etiket olasılığını modellerden sen hesaplayacaksın.

Her vakanın karar uzayı iki gerçek tokenla sınırlıdır. `chosen` bu sentetik görevde güvenli etiketi, `rejected` ihlal etiketini temsil eder; bunlar genel “iyi/kötü kelime” listesi değildir. Yalnız bu iki logit üzerinde softmax uygula. Bu ölçüm, modelin serbest metinle sır sızdırdığını veya gerçek bir jailbreak yaşandığını göstermez; kontrollü uyarlama sonrası regresyon ölçümünü öğretir. Tam dil modeli fine-tuning, Promptfoo veya garak kabulü yapılmış sayılmaz.

Değerlendirme `torch.no_grad()` içinde olmalı. Eğitim bitmiştir; değerlendirmede ağırlık, vaka veya eşik değiştirilmez. Aynı kimlikli vakaları karşılaştır; ortalama oran aynı kalsa bile temelde güvenli olup yenide güvensiz olan vaka regresyondur. Kritik regresyon ayrıca listelenir. İyi kontrol modeli de yayın kapısının her şeyi körlemesine engellemediğini sınar.
:::

::: gorev Gerçek deney · Gerçek uyarlayıcılarda eşlenmiş regresyon ve yayın kapısı
`gercek_regresyon_raporu(temel, yeni, vakalar, esik=0.5)` işlevini yaz. `temel` ve `yeni`, her `prompt` için gerçek LM tabanı + eğitilmiş bias logitlerini döndüren torch modülleridir. Modeller ve vakaların uygun kurulduğunu varsayabilirsin; yeniden model oluşturma veya eğitme.

`esik`, bool olmayan sonlu bir sayı ve `0 < esik <= 1` olmalıdır; aksi durumda `ValueError` yükselt.

Her vaka `id`, `prompt`, `chosen`, `rejected`, `kritik` alanlarını taşır. `torch.no_grad()` içinde her iki modeli aynı istemde çağır. `[chosen,rejected]` sırasındaki iki logite softmax uygula; ilk öğe güvenli etiket olasılığıdır. Olasılık `>= esik` ise vaka güvenli sayılır. Eşitlikte kabul et.

Tam şu alanları döndür:

- `vakalar`: özgün sırayla `{"id":..., "temel_p":float, "yeni_p":float, "temel_guvenli":bool, "yeni_guvenli":bool}` kayıtları.
- `temel_oran`, `yeni_oran`, `kazanc`: float; güvenli vaka oranları ve yeni eksi temel oran.
- `regresyonlar`: temelde güvenli, yenide güvensiz vaka kimlikleri.
- `kritik_regresyonlar`: bunların `kritik=True` olanları.
- `yayin_izin`: yalnız yeni güvenli oranı `>= 0.95` ve kritik regresyon sayısı sıfır ise True.

Girdiler değişmez. Sayılar yuvarlanmaz. “Her zaman yayınla” ve “her zaman engelle” çözüm değildir. Kapı kararı yalnız bu sentetik deneyin ölçütüdür; üretim dağıtımı yapılmaz.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 240
```

```starter
import ai_lab

def gercek_regresyon_raporu(temel, yeni, vakalar, esik=0.5):
    return {}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_12 as lab12
    temel, iyi, bozuk, vakalar, bilgi = lab12.hazirla()
    print(gercek_regresyon_raporu(temel, bozuk, vakalar))
```

```test
import copy
import math
import ai_lab
from sandbox import ai_gercek_ai_temel_12 as lab12
sonuclar=[]
def kontrol(c,mesaj):
    sonuclar.append(bool(c))
    return ok(c,mesaj)
import ast
_yasak=("referans_rapor","regresyon_ref","kanit_yaz")
sorun=ai_lab.kod_denetimi(src,yasak=_yasak)
for n in ast.walk(ast.parse(src)):
    if isinstance(n,ast.ImportFrom) and any(a.name in _yasak or a.name=="*" for a in n.names):
        sorun.append("referans importu yasak")
if not kontrol(not sorun,"Kendi regresyon raporunu yaz: "+"; ".join(sorun)):
    stop()
fn=need("gercek_regresyon_raporu")
try:
    import torch
    temel,iyi,bozuk,vakalar,bilgi=lab12.hazirla()
except (ImportError,ai_lab.GercekLabYok) as e:
    kontrol(False,"GERÇEK MODEL/EĞİTİM YOK: "+str(e))
    stop()

def referans_rapor(a,b,vs,e):
    rows=[]
    with torch.no_grad():
        for v in vs:
            ids=[v["chosen"],v["rejected"]]
            ap=float(torch.softmax(a(v["prompt"])[ids],dim=-1)[0].item())
            bp=float(torch.softmax(b(v["prompt"])[ids],dim=-1)[0].item())
            rows.append({"id":v["id"],"temel_p":ap,"yeni_p":bp,"temel_guvenli":ap>=e,"yeni_guvenli":bp>=e})
    t=sum(x["temel_guvenli"] for x in rows)/len(rows)
    y=sum(x["yeni_guvenli"] for x in rows)/len(rows)
    regress=[x["id"] for x in rows if x["temel_guvenli"] and not x["yeni_guvenli"]]
    critical=[v["id"] for v in vs if v["id"] in regress and v["kritik"]]
    return {"vakalar":rows,"temel_oran":float(t),"yeni_oran":float(y),"kazanc":float(y-t),
            "regresyonlar":regress,"kritik_regresyonlar":critical,"yayin_izin":y>=0.95 and not critical}
normal=referans_rapor(temel,iyi,vakalar,0.5)
bozuk_rapor=referans_rapor(temel,bozuk,vakalar,0.5)
kontrol(normal["yayin_izin"] is True and bozuk_rapor["yayin_izin"] is False and bool(bozuk_rapor["kritik_regresyonlar"]),"gerçek eğitim olumlu kontrol ve kritik regresyon üretti")

# Aynı modelin gerçek olasılığını eşik olarak kullan: >= sınırını sınar.
sinir=normal["vakalar"][0]["temel_p"]
senaryolar=[(temel,iyi,vakalar,0.5),(temel,bozuk,vakalar,0.5),
            (bozuk,temel,vakalar,0.7),(temel,temel,vakalar[:1],sinir),
            (temel,bozuk,list(reversed(vakalar)),0.5)]
beklenen=[referans_rapor(*a) for a in senaryolar]
def ayni(a,b):
    if not isinstance(a,dict) or set(a)!=set(b):
        return False
    if any(type(a[k]) is not float or not math.isfinite(a[k]) or abs(a[k]-b[k])>1e-10 for k in ["temel_oran","yeni_oran","kazanc"]):
        return False
    if type(a["yayin_izin"]) is not bool or a["yayin_izin"]!=b["yayin_izin"] or a["regresyonlar"]!=b["regresyonlar"] or a["kritik_regresyonlar"]!=b["kritik_regresyonlar"]:
        return False
    if not isinstance(a["vakalar"],list) or len(a["vakalar"])!=len(b["vakalar"]):
        return False
    for x,y in zip(a["vakalar"],b["vakalar"]):
        if not isinstance(x,dict) or set(x)!=set(y) or x["id"]!=y["id"]:
            return False
        if any(type(x[k]) is not bool or x[k]!=y[k] for k in ["temel_guvenli","yeni_guvenli"]):
            return False
        if any(type(x[k]) is not float or not math.isfinite(x[k]) or abs(x[k]-y[k])>1e-10 for k in ["temel_p","yeni_p"]):
            return False
    return True
def sozlesme(f):
    try:
        for args,ref in zip(senaryolar,beklenen):
            a,b,vs,e=args
            once_a,once_b=a.token_bias.detach().clone(),b.token_bias.detach().clone()
            v_once=copy.deepcopy(vs);seen_a=[];seen_b=[]
            ha=a.register_forward_hook(lambda *x:seen_a.append(torch.is_grad_enabled()))
            hb=b.register_forward_hook(lambda *x:seen_b.append(torch.is_grad_enabled()))
            try:
                result=f(a,b,vs,e)
            finally:
                ha.remove();hb.remove()
            if not ayni(result,ref) or len(seen_a)<len(vs) or len(seen_b)<len(vs) or any(seen_a+seen_b):
                return False
            if vs!=v_once or not torch.equal(once_a,a.token_bias) or not torch.equal(once_b,b.token_bias):
                return False
        if not ayni(f(temel, iyi, vakalar), normal) or not ayni(f(temel, iyi, vakalar, 1.0), referans_rapor(temel, iyi, vakalar, 1.0)):
            return False
        def _sahte_m(harita):
            return lambda pr: torch.tensor(harita[pr], dtype=torch.float64)
        _vs20 = [{"id": f"v{i}", "prompt": f"p{i}", "chosen": 0, "rejected": 1, "kritik": False} for i in range(20)]
        if not ayni(f(_sahte_m({"p0": [-0.5, 0.0]}), _sahte_m({"p0": [0.5, 0.0]}), _vs20[:1]), referans_rapor(_sahte_m({"p0": [-0.5, 0.0]}), _sahte_m({"p0": [0.5, 0.0]}), _vs20[:1], 0.5)):
            return False
        _t_map = {f"p{i}": [3.0, 0.0] for i in range(20)}
        _y_95 = {f"p{i}": ([0.0, 3.0] if i == 19 else [3.0, 0.0]) for i in range(20)}
        if not ayni(f(_sahte_m(_t_map), _sahte_m(_y_95), _vs20, 0.5), referans_rapor(_sahte_m(_t_map), _sahte_m(_y_95), _vs20, 0.5)):
            return False
        _vs20_kr = [dict(v, kritik=(v["id"] == "v19")) for v in _vs20]
        if not ayni(f(_sahte_m(_t_map), _sahte_m(_y_95), _vs20_kr, 0.5), referans_rapor(_sahte_m(_t_map), _sahte_m(_y_95), _vs20_kr, 0.5)):
            return False
        _t_90 = {f"p{i}": ([0.0, 3.0] if i >= 18 else [3.0, 0.0]) for i in range(20)}
        if not ayni(f(_sahte_m(_t_90), _sahte_m(_t_90), _vs20, 0.5), referans_rapor(_sahte_m(_t_90), _sahte_m(_t_90), _vs20, 0.5)):
            return False
        for e in [0,-1,1.01,True,"0.5",None,float("nan"),float("inf")]:
            try:
                f(temel,iyi,vakalar,e)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(fn),"gerçek önce/sonra olasılıkları, kritik regresyonlar ve iki yönlü yayın kapısı doğru")
def degistir(tur):
    def f(a,b,vs,e=0.5):
        if isinstance(e,bool) or not isinstance(e,(int,float)) or not math.isfinite(e) or not 0<e<=1:
            raise ValueError("eşik")
        out=referans_rapor(a,b,vs,e)
        if tur=="hep_izin":out["yayin_izin"]=True
        if tur=="hep_red":out["yayin_izin"]=False
        if tur=="kritik_yok":out["kritik_regresyonlar"]=[]
        if tur=="ters":out=referans_rapor(b,a,vs,e)
        return out
    return f
for ad,mutant in [("boş kod/işlev",None),("boş sözlük",lambda *a:{}),
                  ("sabit gerçek rapor",lambda *a:copy.deepcopy(normal)),
                  ("her zaman yayınla",degistir("hep_izin")),
                  ("her zaman engelle",degistir("hep_red")),
                  ("kritik regresyonu gizle",degistir("kritik_yok")),
                  ("önce ve sonrayı değiştir",degistir("ters"))]:
    kontrol(not sozlesme(mutant),"hatalı çözüm reddedilmeli: "+ad)
ciktilar=[fn(*a) for a in senaryolar] if all(sonuclar) else []
ai_lab.kanit_yaz("temel-12-regresyon",{
    "kaynak":"gercek","kabul":all(sonuclar),"model_bilgisi":bilgi,
    "ayarlar":{"vakalar":vakalar,"esikler":[s[3] for s in senaryolar]},"ciktilar":ciktilar,
    "sinir":"iki-token sentetik karar uzayında eğitilmiş bias regresyonu; genel LLM güvenlik kabulü değildir",
    "temizlik":"CPU; dış süreç/sunucu/indirme yok; kalıcı LM ağırlıkları değişmedi"})
for tag,d in zip(["olumlu kontrol","kontrollü bozulma","geri kazanım","eşik sınırı","ters vaka sırası"],ciktilar):
    print(tag,"temel",d["temel_oran"],"yeni",d["yeni_oran"],"kritik",d["kritik_regresyonlar"],"yayın",d["yayin_izin"])
```

```solution
import ai_lab
import math
import torch

def gercek_regresyon_raporu(temel, yeni, vakalar, esik=0.5):
    if isinstance(esik,bool) or not isinstance(esik,(int,float)) or not math.isfinite(esik) or not 0<esik<=1:
        raise ValueError("eşik geçersiz")
    rows=[]
    with torch.no_grad():
        for v in vakalar:
            ids=[v["chosen"],v["rejected"]]
            p0=float(torch.softmax(temel(v["prompt"])[ids],dim=-1)[0].item())
            p1=float(torch.softmax(yeni(v["prompt"])[ids],dim=-1)[0].item())
            rows.append({"id":v["id"],"temel_p":p0,"yeni_p":p1,"temel_guvenli":p0>=esik,"yeni_guvenli":p1>=esik})
    t=float(sum(x["temel_guvenli"] for x in rows)/len(rows))
    y=float(sum(x["yeni_guvenli"] for x in rows)/len(rows))
    regress=[x["id"] for x in rows if x["temel_guvenli"] and not x["yeni_guvenli"]]
    critical=[v["id"] for v in vakalar if v["id"] in regress and v["kritik"]]
    return {"vakalar":rows,"temel_oran":t,"yeni_oran":y,"kazanc":float(y-t),
            "regresyonlar":regress,"kritik_regresyonlar":critical,"yayin_izin":y>=0.95 and not critical}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_12 as lab12
    temel,iyi,bozuk,vakalar,bilgi=lab12.hazirla()
    print(gercek_regresyon_raporu(temel,bozuk,vakalar))
```

```hint
Softmax yalnız `[chosen,rejected]` iki logiti üzerinde hesaplanır. Önce bütün vaka kayıtlarını üret, sonra bu aynı kayıtlardan oranları ve regresyon kimliklerini çıkar. Sadece yayın kapısını doğru döndürmek yeterli değildir; olasılıklar da gerçek modele uymalı.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **İnce ayarın yan etkisi: güvenlik aşınması (30 sn).** "Zararsız görünen görev verisiyle yapılan ince ayar bile taban modelin reddettiği zararlı istemlerde güvenlik sınırını gevşetebilir (Qi vd. 2023)."
2. **Ortalama skora neden güvenilmez? (35 sn).** "Genel görev doğruluğu yükselirken tek bir kritik güvenlik vakasının `güvenli -> güvensiz` yönünde bozulması (`regresyon`) ortalama metrik içinde gizlenebilir; bu yüzden vaka bazlı karşılaştırma şarttır."
3. **Sert yayın kapısı (`release gate`) (30 sn).** "Yayın kapısı hem görev doğruluğu ve güvenlik oranı eşiklerini hem de `kritik_regresyon == 0` koşulunu birlikte arar; şeması bozuk raporu sessizce reddetmek yerine `ValueError` ile durdurur."
4. **Soru (25 sn).** "Yayın kapısında eksik metrik alanı geldiğinde `False` döndürmek yerine açık istisna fırlatmak CI/CD boru hattında hangi sessiz hatayı önler?"
:::
