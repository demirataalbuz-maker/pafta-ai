---
id: ai-guvence-07
title: white-box FGSM Ölçümü
summary: FGSM bozuntusunu önce görünür sentetik gradyanlarla, sonra eğitilmiş bir PyTorch modelinde autograd ile üret; epsilon, gerçekleşen L∞ ve doğruluk kaybı ilişkisini ölç.
esleme: ai-guvence-08, ai-guvence-35, ai-guvence-36
timeout: 45
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et: FGSM tek adımlık bir gradyan saldırısıdır
Fast Gradient Sign Method (FGSM), sınıflandırıcının kaybını girdiye göre türevler ve girdiyi bu türevin **işareti** yönünde `ε` kadar iter: `x' = clip(x + ε·sign(∇ₓ L(f(x), y)), 0, 1)`. "white-box" denmesinin nedeni saldırganın modelin ağırlıklarına ve gradyanına erişebildiğini varsaymasıdır. Bu ölçümü yapan kişi çoğunlukla saldırgan değil, kendi modelinin dayanıklılığını sınayan savunucudur.

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| PyTorch autograd (veya ART, torchattacks) eğitilmiş bir modelde her örnek için gerçek gradyanı hesaplar. Bozulmuş girdiler modele yeniden verilir ve ε'a göre doğruluk eğrisi çizilir. | İlk üç görevde `veri/fgsm_ornekleri.json` ve `veri/epsilon_gozlemleri.json` içindeki **sentetik** girdi, gradyan ve ölçümler kullanılır. Son görevde 8×8 sentetik desenlerle CPU'da eğitilen küçük bir PyTorch MLP'si ve onun gerçek autograd gradyanı kullanılır; ağa erişilmez. | Tek bir küçük modelde ve tek bir veri kümesinde ölçülen eğri, büyük görüntü modellerinin veya başka saldırıların (PGD, C&W) sonucunu öngörmez. FGSM'e dayanıklı görünen bir model gerçekte dayanıklı olmayabilir. |

> [!NOT]
> Görev 1–3 sentetik veriyle çalışır. Bu görevlerde PyTorch çalıştırılmaz ve gradyanlar elle yazılmıştır, gerçek bir modelden gelmez. Son adımdaki **Gerçek deney** görevi ise PyTorch ile gerçek bir modeli eğitir ve gradyanı autograd ile hesaplar. `veri/` dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalanır; kopyada yaptığın değişiklik bir sonraki çalıştırmada sıfırlanır, **kalıcılık yoktur**. Kontrol, bu dosyalardan ayrı gizli verilerle sınar.

**Neden yalnız işaret?** Goodfellow ve arkadaşlarının 2015 tarihli makalesindeki "doğrusallık" açıklamasına göre, yüksek boyutlu girdide her koordinattaki küçük ama aynı yönlü değişiklikler toplanır ve logitte büyük bir kaymaya dönüşür. İşaret almak, L∞ bütçesi `ε` olan bölgede kaybı ilk dereceden en çok artıran adımdır. Gradyanın büyüklüğü bilgisi bilerek atılır, yalnız yönü kullanılır.
:::

::: anlat Epsilon ile gerçekleşen bozuntu aynı olmak zorunda değildir
Bozuntu ham olarak `epsilon*sign(gradyan)` hesaplanır; işaret sıfırsa katkı da sıfırdır. Girdi `[0,1]` aralığına kırpıldığında bazı koordinatların gerçekleşen farkı epsilondan küçük olabilir. `L∞`, bütün koordinatlardaki mutlak gerçekleşen farkların maksimumudur. Raporda `ε` değil, gerçekleşen `x_adv-x` farkından hesaplanan `L∞` yazılır. `veri/fgsm_ornekleri.json` içindeki `satir-02-kirpma` örneği 0.97 ve 1.0 gibi sınıra yakın piksellerle bu farkı görünür kılar.

Doğruluk kaybı `taban_dogruluk-saldiri_dogruluk`, bağıl kayıp ise bu farkın taban doğruluğa oranıdır. Taban sıfırsa bağıl kayıp `None` olur. Eğri raporunda en yüksek ham kayıp seçilir; eşitlikte düşük epsilon kazanır. Bu kuralın nedeni şudur: aynı zararı daha küçük bütçeyle veren nokta, savunucu için daha önemli bir bulgudur. `veri/epsilon_gozlemleri.json` içinde ε=0.2 ve ε=0.3 aynı doğruluğu verir. Eğri doymuştur ve doğru cevap 0.2'dir.

**Çıktı nasıl okunur?** Eğrinin ε=0 noktası temiz doğruluğa eşit olmalıdır. Değilse ölçüm hattında bir hata vardır (yanlış etiket, `model.train()` modunda kalmış dropout veya normalizasyon). Eğri ε büyüdükçe genellikle düşer. Düşmüyorsa ya model gerçekten dayanıklıdır ya da gradyan bozuktur. Sık görülen tuzaklar şunlardır:

- **Yanlış uzayda ε:** Görüntü normalize ediliyorsa (ortalama çıkarılıp std'ye bölünüyorsa) `ε=8/255` piksel uzayında mı, yoksa normalize uzayda mı uygulandı? Rapor bunu söylemezse sayı karşılaştırılamaz.
- **Kırpmayı unutmak:** Geçersiz piksel değerleri modele gerçekte verilemeyecek girdiler üretir ve saldırıyı olduğundan güçlü gösterir.
- **Ters işaret:** `x - ε·sign(g)` kaybı azaltır, yani modelin işini kolaylaştırır. Doğruluk artıyorsa ilk bakılacak yer burasıdır.
- **Gradyan maskeleme:** Türevlenemeyen bir ön işleme, sıfıra yakın gradyan veren doygun bir softmax ya da rastgelelik FGSM'i başarısız gösterebilir. Bu, modelin güvenli olduğu anlamına gelmez. Saldırgan aynı modele çok adımlı PGD (ders 08) veya transfer saldırısıyla gelir. FGSM bu yüzden bir **alt sınır** testidir: "FGSM'de %40 düştü" bilgilendiricidir, "FGSM'de düşmedi" ise kanıt değildir.

**Savunucu tarafı:** FGSM ucuz olduğu için adversarial eğitimde sıkça kullanılır. Ancak yalnız FGSM ile eğitilen modeller "katastrofik aşırı uyum" yaşayıp tek adımlı saldırıya dayanıklı, çok adımlıya savunmasız hâle gelebilir. Bu nedenle savunma iddiası her zaman daha güçlü bir saldırı ve gerçekleşen bütçeyle birlikte raporlanır.

Kaynaklar: [Goodfellow vd. 2015 — Explaining and Harnessing Adversarial Examples (arXiv:1412.6572)](https://arxiv.org/abs/1412.6572), [Wong vd. 2020 — Fast is better than free: Revisiting adversarial training (arXiv:2001.03994)](https://arxiv.org/abs/2001.03994).
:::

::: tahmin FGSM farkını tahmin et
Üç çıktı satırını yaz:

```python
print(min(1, 0.95 + 0.1))
print(round(min(1, 0.95 + 0.1) - 0.95, 6))
print(round((0.8 - 0.5) / 0.8, 6))
```

???

```cikti
1
0.05
0.375
```

İkinci satır kırpma nedeniyle gerçekleşen farkın `0.1` epsilon değerinden küçük olduğunu gösterir.
:::

::: gorev 1 · FGSM örneğini doğrula
`fgsm_ornegi_dogrula(ornek)` işlevini yaz. Örnek tam olarak `id`, `etiket`, `x`, `gradyan` alanlarını taşısın. Kimlik 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren stringdir. Etiket `yelkovan` veya `diger` olmalıdır.

`x` ve `gradyan` aynı uzunlukta, boş olmayan listelerdir. Girdi değerleri bool olmayan sonlu sayı ve `[0,1]` aralığında, gradyanlar bool olmayan sonlu sayı olmalıdır. Geçersiz veride `ValueError` yükselt. İki listeyi de kopyalayan yeni sözlükle döndür ve girdiyi değiştirme.

Görünür veri: `veri/fgsm_ornekleri.json`. Başlangıç kodu dosyadaki beş örneği doğrulamayı dener. `bozuk-aralik` ve `bozuk-boyut` örnekleri reddedilmelidir, ama kusurlu kod ikisini de kabul ediyor.

```starter
from ai_guvence_veri import json_yukle

def fgsm_ornegi_dogrula(ornek):
    # KUSURLU BAŞLANGIÇ KODU: aralık, boyut ve tür denetimi yok; girdinin kendisini kopyalamadan döndürüyor!
    if "x" not in ornek or "gradyan" not in ornek:
        raise ValueError("eksik alan")
    return ornek

veri = json_yukle("veri/fgsm_ornekleri.json")
for o in veri["ornekler"]:
    try:
        sonuc = fgsm_ornegi_dogrula(o)
        print(o["id"], "kabul:", len(sonuc["x"]), "piksel")
    except ValueError as hata:
        print(o["id"], "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-07")
```

```test
import copy
O = {"id": "ornek-1", "etiket": "yelkovan", "x": [0.5, 0.2, 0.7], "gradyan": [1, -1, 0]}
def sozlesme(fn):
    try:
        once = copy.deepcopy(O)
        sonuc = fn(O)
        if sonuc != O or O != once or sonuc is O or sonuc["x"] is O["x"] or sonuc["gradyan"] is O["gradyan"]:
            return False
        if fn(dict(O, id="a" * 64, x=[0, 1], gradyan=[0, 0]))["x"] != [0, 1]:
            return False
        for ornek in [
            None, [], dict(O, ek=1), dict(O, id=""), dict(O, id="a b"), dict(O, id="a" * 65), dict(O, id=None),
            dict(O, id=123), dict(O, etiket="baska"), dict(O, etiket=None),
            dict(O, x=(0.5, 0.2, 0.7)), dict(O, gradyan=(1, -1, 0)), dict(O, x=[], gradyan=[]),
            dict(O, x=[]), dict(O, x=None), dict(O, x="0.5"),
            dict(O, gradyan=[]), dict(O, gradyan=None), dict(O, gradyan="1"), dict(O, gradyan=[1, 2]),
            dict(O, x=[True, 0.2, 0.7]), dict(O, x=["0.5", 0.2, 0.7]),
            dict(O, x=[float("nan"), 0.2, 0.7]), dict(O, x=[float("inf"), 0.2, 0.7]),
            dict(O, x=[-0.1, 0.2, 0.7]), dict(O, x=[1.1, 0.2, 0.7]),
            dict(O, gradyan=[True, -1, 0]), dict(O, gradyan=["1", -1, 0]),
            dict(O, gradyan=[float("nan"), -1, 0]), dict(O, gradyan=[float("inf"), -1, 0]),
        ]:
            try:
                fn(ornek)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(fgsm_ornegi_dogrula), "örnek şeması, girdi aralığı ve gradyan boyutu korunmalı")
def m_x(ornek):
    return fgsm_ornegi_dogrula(dict(ornek, x=[0 for _ in ornek["x"]]))
def m_grad(ornek):
    return fgsm_ornegi_dogrula(dict(ornek, gradyan=[0 for _ in ornek["gradyan"]]))
def m_etiket(ornek):
    return fgsm_ornegi_dogrula(dict(ornek, etiket="diger"))
for ad, mutant in [("girdiyi silen", m_x), ("gradyanı silen", m_grad), ("etiketi değiştiren", m_etiket)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def fgsm_ornegi_dogrula(ornek):
    import math
    import re
    if not isinstance(ornek, dict):
        raise ValueError("örnek sözlük olmalı")
    if set(ornek) != {"id", "etiket", "x", "gradyan"}:
        raise ValueError("örnek şeması geçersiz")
    if not isinstance(ornek["id"], str):
        raise ValueError("kimlik string olmalı")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", ornek["id"]):
        raise ValueError("kimlik geçersiz")
    if ornek["etiket"] not in ("yelkovan", "diger"):
        raise ValueError("etiket geçersiz")
    x = ornek["x"]
    gradyan = ornek["gradyan"]
    if not isinstance(x, list) or not isinstance(gradyan, list):
        raise ValueError("x ve gradyan liste olmalı")
    if not x or len(x) != len(gradyan):
        raise ValueError("x ve gradyan aynı boyutta ve boş olmayan olmalı")
    for deger in x:
        if isinstance(deger, bool) or not isinstance(deger, (int, float)):
            raise ValueError("girdi sayı olmalı")
        if not math.isfinite(deger):
            raise ValueError("girdi sonlu olmalı")
        if deger < 0 or deger > 1:
            raise ValueError("girdi aralık dışında")
    for deger in gradyan:
        if isinstance(deger, bool) or not isinstance(deger, (int, float)):
            raise ValueError("gradyan sayı olmalı")
        if not math.isfinite(deger):
            raise ValueError("gradyan sonlu olmalı")
    return {"id": ornek["id"], "etiket": ornek["etiket"], "x": list(x), "gradyan": list(gradyan)}
```

```hint
İki listenin türünü ve ortak boyutunu önce denetle. Girdi ve gradyan değerlerini ayrı döngülerde doğrulayıp listeleri kopyala.
```
:::

::: gorev 2 · Kırpılmış FGSM bozuntusu üret
`fgsm_uret(ornek, epsilon)` işlevini yaz. Örnek ilk görevdeki kuralları sağlasın. Epsilon bool olmayan sonlu sayı ve `[0,1]` aralığında olmalıdır. Geçersiz veride `ValueError` yükselt.

Her koordinatta `x_adv = min(1, max(0, x + epsilon*isaret(gradyan)))` hesapla; işaret pozitifte `1`, negatifte `-1`, sıfırda `0` olsun. Gerçekleşen fark `x_adv-x` olarak hesaplanır. `{"id":ID,"etiket":ETIKET,"x_adv":[X,...],"bozuntu":[D,...],"l_inf":X}` döndür. Listeleri ve `L∞` değerini altı ondalık basamağa yuvarla; `L∞` mutlak farkların maksimumudur. Girdiyi değiştirme.

Görünür veri: `veri/fgsm_ornekleri.json` içindeki geçerli örnekler ve `epsilonlar` listesi. `satir-02-kirpma` örneğinde gerçekleşen fark ile `ε` arasındaki ayrılığa bak.

```starter
from ai_guvence_veri import json_yukle

def fgsm_uret(ornek, epsilon):
    # KUSURLU BAŞLANGIÇ KODU: sıfır gradyana da +ε uyguluyor ve bozuntuyu kırpmadan önceki ham ε·işaret olarak raporluyor!
    xadv, bozuntu = [], []
    for xv, gv in zip(ornek["x"], ornek["gradyan"]):
        isaret = 1 if gv >= 0 else -1
        xadv.append(round(min(1, max(0, xv + epsilon * isaret)), 6))
        bozuntu.append(round(epsilon * isaret, 6))
    return {"id": ornek["id"], "etiket": ornek["etiket"], "x_adv": xadv, "bozuntu": bozuntu,
            "l_inf": max(abs(d) for d in bozuntu)}

veri = json_yukle("veri/fgsm_ornekleri.json")
for o in veri["ornekler"][:3]:
    for eps in veri["epsilonlar"]:
        s = fgsm_uret(o, eps)
        print(o["id"], "ε =", eps, "L∞ =", s["l_inf"], "bozuntu =", s["bozuntu"])
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-07")
```

```test
import copy
O = {"id": "ornek-1", "etiket": "yelkovan", "x": [0.5, 0.2, 0.7], "gradyan": [1, -1, 0]}
BEKLENEN = {"id": "ornek-1", "etiket": "yelkovan", "x_adv": [0.6, 0.1, 0.7], "bozuntu": [0.1, -0.1, 0.0], "l_inf": 0.1}
def sozlesme(fn):
    try:
        once = copy.deepcopy(O)
        if fn(O, 0.1) != BEKLENEN or O != once:
            return False
        if fn(O, 0) != {"id": "ornek-1", "etiket": "yelkovan", "x_adv": [0.5, 0.2, 0.7], "bozuntu": [0.0, 0.0, 0.0], "l_inf": 0.0}:
            return False
        kirp = dict(O, x=[0.95, 0.05, 0.7])
        if fn(kirp, 0.1)["x_adv"] != [1.0, 0.0, 0.7] or fn(kirp, 0.1)["bozuntu"] != [0.05, -0.05, 0.0]:
            return False
        if fn(dict(O, x=[0], gradyan=[1]), 1 / 3) != {"id": "ornek-1", "etiket": "yelkovan", "x_adv": [0.333333], "bozuntu": [0.333333], "l_inf": 0.333333}:
            return False
        if fn(dict(O, x=[0], gradyan=[0]), 1)["l_inf"] != 0:
            return False
        if fn(dict(O, x=[1], gradyan=[0]), 0)["x_adv"] != [1.0]:
            return False
        for ornek, epsilon in [
            (None, 0.1), (dict(O, ek=1), 0.1), (dict(O, id=123), 0.1), (dict(O, id="a" * 65), 0.1), (dict(O, etiket="baska"), 0.1),
            (dict(O, x=(0.5, 0.2, 0.7)), 0.1), (dict(O, gradyan=(1, -1, 0)), 0.1), (dict(O, x=[], gradyan=[]), 0.1),
            (dict(O, x=["0.5", 0.2, 0.7]), 0.1), (dict(O, gradyan=["1", -1, 0]), 0.1),
            (dict(O, x=None), 0.1), (dict(O, gradyan=None), 0.1),
            (dict(O, x=[]), 0.1), (dict(O, gradyan=[1]), 0.1), (dict(O, x=[-0.1, 0.2, 0.7]), 0.1),
            (dict(O, x=[1.1, 0.2, 0.7]), 0.1), (dict(O, x=[True, 0.2, 0.7]), 0.1),
            (dict(O, x=[float("nan"), 0.2, 0.7]), 0.1), (dict(O, gradyan=[float("inf"), -1, 0]), 0.1),
            (dict(O, gradyan=[True, -1, 0]), 0.1),
            (O, None), (O, True), (O, "0.1"), (O, float("nan")), (O, float("inf")), (O, -0.1), (O, 1.1),
        ]:
            try:
                fn(ornek, epsilon)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(fgsm_uret), "işaret, kırpma, gerçekleşen fark ve L∞ korunmalı")
def m_grad(ornek, epsilon):
    return fgsm_uret(dict(ornek, gradyan=[0 for _ in ornek["gradyan"]]), epsilon)
def m_x(ornek, epsilon):
    return fgsm_uret(dict(ornek, x=[0.5 for _ in ornek["x"]]), epsilon)
def m_epsilon(ornek, epsilon):
    return fgsm_uret(ornek, 0)
for ad, mutant in [("gradyanı silen", m_grad), ("girdiyi değiştiren", m_x), ("epsilonu silen", m_epsilon)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def fgsm_uret(ornek, epsilon):
    import math
    import re
    if isinstance(epsilon, bool) or not isinstance(epsilon, (int, float)):
        raise ValueError("epsilon sayı olmalı")
    if not math.isfinite(epsilon):
        raise ValueError("epsilon sonlu olmalı")
    if epsilon < 0 or epsilon > 1:
        raise ValueError("epsilon aralık dışında")
    if not isinstance(ornek, dict):
        raise ValueError("örnek sözlük olmalı")
    if set(ornek) != {"id", "etiket", "x", "gradyan"}:
        raise ValueError("örnek şeması geçersiz")
    if not isinstance(ornek["id"], str):
        raise ValueError("kimlik string olmalı")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", ornek["id"]):
        raise ValueError("kimlik geçersiz")
    if ornek["etiket"] not in ("yelkovan", "diger"):
        raise ValueError("etiket geçersiz")
    x = ornek["x"]
    gradyan = ornek["gradyan"]
    if not isinstance(x, list) or not isinstance(gradyan, list):
        raise ValueError("x ve gradyan liste olmalı")
    if not x or len(x) != len(gradyan):
        raise ValueError("x ve gradyan aynı boyutta ve boş olmayan olmalı")
    for deger in x:
        if isinstance(deger, bool) or not isinstance(deger, (int, float)):
            raise ValueError("girdi sayı olmalı")
        if not math.isfinite(deger):
            raise ValueError("girdi sonlu olmalı")
        if deger < 0 or deger > 1:
            raise ValueError("girdi aralık dışında")
    for deger in gradyan:
        if isinstance(deger, bool) or not isinstance(deger, (int, float)):
            raise ValueError("gradyan sayı olmalı")
        if not math.isfinite(deger):
            raise ValueError("gradyan sonlu olmalı")
    xadv = []
    bozuntu = []
    for xv, gv in zip(x, gradyan):
        isaret = 1 if gv > 0 else -1 if gv < 0 else 0
        yeni = min(1, max(0, xv + epsilon * isaret))
        xadv.append(yeni)
        bozuntu.append(yeni - xv)
    return {"id": ornek["id"], "etiket": ornek["etiket"], "x_adv": [round(v, 6) for v in xadv], "bozuntu": [round(v, 6) for v in bozuntu], "l_inf": round(max(abs(v) for v in bozuntu), 6)}
```

```hint
Gradyan işaretini üç dala ayır. Yeni girdiyi kırptıktan sonra bozuntuyu yeni ve eski değerin farkından hesapla.
```
:::

::: gorev 3 · Epsilon-doğruluk eğrisini raporla
`fgsm_egri_raporu(gozlemler)` işlevini yaz. Gözlemler boş olmayan listedir. Her kayıt tam olarak `epsilon`, `taban_dogruluk`, `saldiri_dogruluk`, `l_inf` alanlarını taşısın. Bütün değerler bool olmayan sonlu sayı ve `[0,1]` aralığındadır. Epsilon yinelenemez, taban doğruluk bütün kayıtlarda aynı olmalı ve `l_inf <= epsilon + 1e-9` sağlanmalıdır. Geçersiz veride `ValueError` yükselt.

Her satıra `kayip = taban_dogruluk-saldiri_dogruluk` ve bağıl kayıp ekle. Bağıl kayıp `kayip/taban_dogruluk`, taban sıfırsa `None` olsun. Kayıp ve bağıl kaybı altı ondalık basamağa yuvarla. `{"satirlar":[KAYIT,...],"maksimum_kayip":X,"en_yuksek_kayip_epsilon":E}` döndür. Satırları epsilona göre artan sırala; en yüksek ham kaybı bul ve eşitlikte düşük epsilonu seç. Girdiyi değiştirme.

Görünür veri: `veri/epsilon_gozlemleri.json`. `gozlemler` listesi sırasızdır. ε=0.2 ile ε=0.3 aynı kaybı verir, `bozuk_gozlem` ise L∞ bütçesini aşar.

```starter
from ai_guvence_veri import json_yukle

def fgsm_egri_raporu(gozlemler):
    # KUSURLU BAŞLANGIÇ KODU: L∞ bütçesini denetlemiyor, taban sıfırsa sıfıra bölüyor ve eşitlikte YÜKSEK epsilonu seçiyor!
    satirlar = []
    for g in sorted(gozlemler, key=lambda x: x["epsilon"]):
        kayip = g["taban_dogruluk"] - g["saldiri_dogruluk"]
        satirlar.append(dict(g, kayip=round(kayip, 6), bagil_kayip=round(kayip / g["taban_dogruluk"], 6)))
    en = max(satirlar, key=lambda x: (x["kayip"], x["epsilon"]))
    return {"satirlar": satirlar, "maksimum_kayip": en["kayip"], "en_yuksek_kayip_epsilon": en["epsilon"]}

veri = json_yukle("veri/epsilon_gozlemleri.json")
rapor = fgsm_egri_raporu(veri["gozlemler"])
for s in rapor["satirlar"]:
    print(f"ε={s['epsilon']:<5} doğruluk={s['saldiri_dogruluk']:.2f} kayıp={s['kayip']:.2f} L∞={s['l_inf']}")
print("en yüksek kayıp:", rapor["maksimum_kayip"], "ε =", rapor["en_yuksek_kayip_epsilon"])
try:
    fgsm_egri_raporu(veri["gozlemler"] + [veri["bozuk_gozlem"]])
    print("bozuk gözlem KABUL edildi (yanlış)")
except ValueError as hata:
    print("bozuk gözlem reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-07")
```

```test
import copy
G = [
    {"epsilon": 0.2, "taban_dogruluk": 0.8, "saldiri_dogruluk": 0.5, "l_inf": 0.2},
    {"epsilon": 0, "taban_dogruluk": 0.8, "saldiri_dogruluk": 0.8, "l_inf": 0},
    {"epsilon": 0.1, "taban_dogruluk": 0.8, "saldiri_dogruluk": 0.6, "l_inf": 0.05},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(G)
        sonuc = fn(G)
        if G != once or [x["epsilon"] for x in sonuc["satirlar"]] != [0, 0.1, 0.2]:
            return False
        if sonuc["maksimum_kayip"] != 0.3 or sonuc["en_yuksek_kayip_epsilon"] != 0.2:
            return False
        if [x["kayip"] for x in sonuc["satirlar"]] != [0.0, 0.2, 0.3]:
            return False
        if [x["bagil_kayip"] for x in sonuc["satirlar"]] != [0.0, 0.25, 0.375]:
            return False
        if any(sonuc["satirlar"][i] is G[i] for i in range(len(G))):
            return False
        sifir = fn([{"epsilon": 0, "taban_dogruluk": 0, "saldiri_dogruluk": 0, "l_inf": 0}])
        if sifir["satirlar"][0]["bagil_kayip"] is not None or sifir["maksimum_kayip"] != 0:
            return False
        yuvarla = fn([{"epsilon": 0.1, "taban_dogruluk": 0.3, "saldiri_dogruluk": 0.2, "l_inf": 0.1}])
        if yuvarla["satirlar"][0]["kayip"] != 0.1 or yuvarla["satirlar"][0]["bagil_kayip"] != 0.333333:
            return False
        ust = fn([{"epsilon": 1, "taban_dogruluk": 1, "saldiri_dogruluk": 2 / 3, "l_inf": 1}])
        if ust["maksimum_kayip"] != 0.333333 or ust["satirlar"][0]["bagil_kayip"] != 0.333333 or ust["satirlar"][0]["kayip"] != 0.333333:
            return False
        tolerans = fn([{"epsilon": 0.1, "taban_dogruluk": 0.8, "saldiri_dogruluk": 0.8, "l_inf": 0.1 + 1e-9}])
        if tolerans["satirlar"][0]["l_inf"] != 0.1 + 1e-9:
            return False
        esit = fn([G[1], G[2]])
        if esit["en_yuksek_kayip_epsilon"] != 0.1:
            return False
        for gozlemler in [
            None, tuple(G), {}, [], [None], [dict(G[0], ek=1)], [G[0], G[0]],
            [dict(G[0], epsilon=True)], [dict(G[0], epsilon="0.2")], [dict(G[0], epsilon=float("nan"))],
            [dict(G[0], epsilon=-0.1)], [dict(G[0], epsilon=1.1)],
            [dict(G[0], taban_dogruluk=True)], [dict(G[0], taban_dogruluk="0.8")],
            [dict(G[0], taban_dogruluk=float("inf"))], [dict(G[0], taban_dogruluk=-0.1)], [dict(G[0], taban_dogruluk=1.1)],
            [dict(G[0], saldiri_dogruluk=True)], [dict(G[0], saldiri_dogruluk="0.5")],
            [dict(G[0], saldiri_dogruluk=float("nan"))], [dict(G[0], saldiri_dogruluk=-0.1)], [dict(G[0], saldiri_dogruluk=1.1)],
            [dict(G[0], l_inf=True)], [dict(G[0], l_inf="0.2")], [dict(G[0], l_inf=float("inf"))],
            [dict(G[0], l_inf=-0.1)], [dict(G[0], l_inf=1.1)], [dict(G[0], l_inf=0.21)], [dict(G[0], l_inf=0.2 + 1.5e-9)],
            [G[0], dict(G[1], epsilon=0.1, taban_dogruluk=0.7, l_inf=0)],
        ]:
            try:
                fn(gozlemler)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(fgsm_egri_raporu), "eğri sırası, kayıp, L∞ sınırı ve maksimum korunmalı")
def m_dogruluk(gozlemler):
    return fgsm_egri_raporu([dict(x, saldiri_dogruluk=0.8) for x in gozlemler])
def m_epsilon(gozlemler):
    return fgsm_egri_raporu([dict(x, epsilon=0.3, l_inf=0.2) for x in gozlemler])
def m_sil(gozlemler):
    return fgsm_egri_raporu(gozlemler[:2])
for ad, mutant in [("doğruluğu değiştiren", m_dogruluk), ("epsilonu değiştiren", m_epsilon), ("noktaları silen", m_sil)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def fgsm_egri_raporu(gozlemler):
    import math
    if not isinstance(gozlemler, list):
        raise ValueError("gözlemler liste olmalı")
    if not gozlemler:
        raise ValueError("gözlemler boş olamaz")
    epsilonlar = set()
    taban = None
    satirlar = []
    for gozlem in gozlemler:
        if not isinstance(gozlem, dict):
            raise ValueError("gözlem sözlük olmalı")
        if set(gozlem) != {"epsilon", "taban_dogruluk", "saldiri_dogruluk", "l_inf"}:
            raise ValueError("gözlem şeması geçersiz")
        for alan in ("epsilon", "taban_dogruluk", "saldiri_dogruluk", "l_inf"):
            deger = gozlem[alan]
            if isinstance(deger, bool) or not isinstance(deger, (int, float)):
                raise ValueError("ölçüm sayı olmalı")
            if not math.isfinite(deger):
                raise ValueError("ölçüm sonlu olmalı")
            if deger < 0 or deger > 1:
                raise ValueError("ölçüm aralık dışında")
        epsilon = gozlem["epsilon"]
        if epsilon in epsilonlar:
            raise ValueError("epsilon yinelenemez")
        if taban is None:
            taban = gozlem["taban_dogruluk"]
        if gozlem["taban_dogruluk"] != taban:
            raise ValueError("taban doğruluk değişemez")
        if gozlem["l_inf"] > epsilon + 1e-9:
            raise ValueError("L∞ epsilon bütçesini aşamaz")
        kayip = taban - gozlem["saldiri_dogruluk"]
        bagil = kayip / taban if taban else None
        satirlar.append({"epsilon": epsilon, "taban_dogruluk": taban, "saldiri_dogruluk": gozlem["saldiri_dogruluk"], "l_inf": gozlem["l_inf"], "kayip": round(kayip, 6), "bagil_kayip": round(bagil, 6) if bagil is not None else None, "_ham_kayip": kayip})
        epsilonlar.add(epsilon)
    satirlar.sort(key=lambda x: x["epsilon"])
    en_yuksek = min(satirlar, key=lambda x: (-x["_ham_kayip"], x["epsilon"]))
    maksimum = round(en_yuksek["_ham_kayip"], 6)
    epsilon = en_yuksek["epsilon"]
    for satir in satirlar:
        del satir["_ham_kayip"]
    return {"satirlar": satirlar, "maksimum_kayip": maksimum, "en_yuksek_kayip_epsilon": epsilon}
```

```hint
Ham kaybı geçici alanda tut. Maksimumu eksi ham kayıp ve epsilon anahtarıyla seçip geçici alanı çıktıdan kaldır.
```
:::

::: anlat Gerçek deney: eğitilmiş sınıflandırıcıda autograd ile FGSM
Görev 1–3'te gradyanlar elle yazılmış bir JSON dosyasından geliyordu. Bu adımda hazır tablo yoktur. `ai_lab.fgsm_siniflandirici()` küçük bir sınıflandırıcıyı (64-32-4 MLP; yatay, dikey, çapraz ve çerçeve olmak üzere dört sınıf 8×8 sentetik desen) sabit tohumla **CPU'da gerçekten eğitir** ve 400 örneklik test kümesini verir. Gradyanı **torch otomatik türevi** hesaplar. Bu adımda PyTorch gerçekten çalışır ve modelin gerçek tahminleri ölçülür.

Görev 2'deki koordinat koordinat hesap burada tek tensör işlemine dönüşür:

1. Girdinin bir kopyasında `requires_grad_(True)` açılır. Model ileri geçirilir ve ortalama çapraz entropi kaybı hesaplanır.
2. `torch.autograd.grad(kayip, x0)` yalnız **girdiye** göre türevi verir. Model ağırlıkları dondurulmuştur ve değişmemelidir.
3. `x0 + ε·grad.sign()` hesaplanır, `[0,1]` aralığına kırpılır ve `detach()` ile hesap grafiğinden koparılır. Kopmayan tensör sonraki ölçümlerde gereksiz grafik taşır ve bellek tüketir.
4. Doğruluk `torch.no_grad()` altında `argmax` tahminlerinden ölçülür. L∞, Görev 2'deki gibi gerçekleşen farktan hesaplanır.

Test her Kontrol'de rastgele 96 örneklik bir altküme ve rastgele bir ε seçer. Senin bozuntunu bağımsız bir autograd hesabıyla karşılaştırır ve doğruluğu modelin gerçek tahminlerinden ölçer. Ters işaret, kırpmasız, ölçekli gradyan ve rastgele işaret gibi yanlış FGSM'ler reddedilir. Kanıta torch sürümü, eğitim istatistikleri (adım, kayıp, test doğruluğu, süre), seçilen altküme, ε eğrisi ve tahmini değişen örnekler yazılır.

Sonucu okurken şuna dikkat et. Ders yazılırken bu makinede (torch 2.14.1, CPU) yapılan bir koşuda model temiz testte 1.000 doğruluk verdi. Tam test kümesindeki FGSM eğrisi ise şöyleydi: ε=0.05'te 0.988, ε=0.1'de 0.723, ε=0.2'de 0.075, ε=0.3'te 0.015. ε=0.1'de 400 tahminin 111'i değişti. %100 temiz doğruluk dayanıklılık anlamına gelmez; eğri 0.05 ile 0.2 arasında hızla çöküyor. Kanıttaki `ornekler` alanı hangi sınıfın hangisine kaydığını gösterir. O koşuda en sık görülen kayma "cerceve"den "yatay"ya veya "dikey"e doğruydu; çerçeve deseni zaten yatay ve dikey çizgilerden oluşur. Kendi koşunda sayılar farklı çıkabilir. Bu sayılar yalnız bu küçük modele aittir ve genellenemez.
:::

::: gorev Gerçek deney · Autograd ile FGSM ve gerçek tahminlerde doğruluk eğrisi
İki işlev yaz (torch kullan):

- `fgsm(model, x, y, eps)`: `x` `[n, 64]` float tensör, `y` `[n]` etiket, `eps` ≥ 0 sayı. Ortalama çapraz entropi kaybının `x`'e göre gradyanını autograd ile al, `x + eps * sign(grad)` hesapla, `[0, 1]`'e kırp ve **gradyan izi taşımayan** (`requires_grad=False`) yeni tensör döndür. `x`'i ve modeli değiştirme.
- `epsilon_egrisi(model, x, y, epsler)`: her `eps` için `{"eps", "temiz_dogruluk", "bozuk_dogruluk", "linf"}` sözlüğü üret (aynı sırada liste). Doğruluklar `argmax` tahminlerinin etiketle eşleşme oranı (float), `linf` = `max |x' - x|` (float). Bozuntuyu kendi `fgsm` işlevinle üret.

Hazır gradyan/tahmin tablosu kullanma; laboratuvarı değiştirme. `sandbox.ai_gercek_ai_guvence_07` içindeki referans işlevleri yalnız test içindir; onları import etmek veya kaynaklarını kopyalamak Kontrol'de reddedilir.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 240
```

```starter
import torch
import torch.nn.functional as F
import ai_lab

def fgsm(model, x, y, eps):
    # KUSURLU BAŞLANGIÇ KODU: gradyanın TERSİNE adım atıyor (kaybı azaltır) ve [0,1] kırpması yok!
    x0 = x.clone().detach().requires_grad_(True)
    kayip = F.cross_entropy(model(x0), y)
    gradyan, = torch.autograd.grad(kayip, x0)
    return (x0 - eps * gradyan.sign()).detach()

def epsilon_egrisi(model, x, y, epsler):
    # KUSURLU BAŞLANGIÇ KODU: L∞'u ölçmek yerine ε'u yazıyor ve temiz doğruluğu hiç ölçmüyor!
    sonuc = []
    for eps in epsler:
        bozuk = fgsm(model, x, y, eps)
        with torch.no_grad():
            bozuk_d = (model(bozuk).argmax(1) == y).float().mean().item()
        sonuc.append({"eps": eps, "temiz_dogruluk": 1.0, "bozuk_dogruluk": bozuk_d, "linf": float(eps)})
    return sonuc

if ai_lab.CALISTIR:
    ai_lab.guvence_goster(fgsm, epsilon_egrisi)
```

```test
import ast
import random
import ai_lab
from sandbox import ai_gercek_ai_guvence_07 as L
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
_yasak = ("fgsm_referans", "epsilon_egrisi_referans", "kanit_yaz")
sorun = ai_lab.kod_denetimi(src, yasak=_yasak)
for n in ast.walk(ast.parse(src)):
    if isinstance(n, ast.ImportFrom) and any(a.name in _yasak or a.name == "*" for a in n.names):
        sorun.append("referans importu yasak")
    if isinstance(n, (ast.Import, ast.ImportFrom)):
        adlar = [a.name for a in n.names] + ([n.module] if isinstance(n, ast.ImportFrom) and n.module else [])
        if any(a and (a.split(".")[0] in ("inspect", "importlib", "runpy") or a.endswith("ai_gercek_ai_guvence_07")) for a in adlar):
            sorun.append("referans modülü/kaynak okuma importu yasak")
    if isinstance(n, ast.Name) and n.id in ("exec", "eval", "compile", "__builtins__"):
        sorun.append("dinamik kod çalıştırma yasak: " + n.id)
if not kontrol(not sorun, "Kendi FGSM işlevini yaz; laboratuvar/referans kullanımı yasak: " + "; ".join(sorted(set(sorun)))):
    stop()
fgsm = need("fgsm")
egri = need("epsilon_egrisi")
try:
    model, (X, Y), bilgi = ai_lab.fgsm_siniflandirici()
    import torch
except ai_lab.GercekLabYok as e:
    kontrol(False, f"GERÇEK MODEL YOK, deney yapılmadı: {e}")
    stop()
F = torch.nn.functional
def ref_fgsm(m, x, y, eps, isaret=1, kirp=True, isaret_al=True):
    x0 = x.clone().detach().requires_grad_(True)
    g, = torch.autograd.grad(F.cross_entropy(m(x0), y), x0)
    adim = g.sign() if isaret_al else g / (g.abs().max() + 1e-12)
    out = x0.detach() + isaret * eps * adim
    return out.clamp(0, 1) if kirp else out
def dogruluk(m, x, y):
    with torch.no_grad():
        return (m(x).argmax(1) == y).float().mean().item()
rnd = random.Random()
secim = rnd.sample(range(len(X)), 96)
xs, ys = X[secim].clone(), Y[secim].clone()
eps = rnd.choice([0.05, 0.1, 0.15, 0.2, 0.3])
parametre = [p.detach().clone() for p in model.parameters()]
def fgsm_sozlesme(f):
    try:
        once = xs.clone()
        out = f(model, xs, ys, eps)
        ref = L.fgsm_referans(model, xs, ys, eps)
        return (torch.is_tensor(out) and out.shape == xs.shape and not out.requires_grad
                and torch.allclose(out, ref, atol=1e-6) and torch.equal(xs, once)
                and float((out - xs).abs().max()) <= eps + 1e-6 and float(out.min()) >= 0 and float(out.max()) <= 1
                and all(torch.equal(p, q) for p, q in zip(model.parameters(), parametre)))
    except Exception:
        return False
kontrol(fgsm_sozlesme(fgsm), f"FGSM bozuntusu bağımsız autograd hesabıyla aynı (rastgele 96 örnek, ε={eps})")
for ad, mutant in [("rastgele işaret", lambda m, x, y, e: (x + e * (torch.randint(0, 2, x.shape) * 2 - 1)).clamp(0, 1)),
                   ("ters işaret", lambda m, x, y, e: ref_fgsm(m, x, y, e, isaret=-1)),
                   ("kırpma yok", lambda m, x, y, e: ref_fgsm(m, x, y, e, kirp=False)),
                   ("işaret yerine ölçekli gradyan", lambda m, x, y, e: ref_fgsm(m, x, y, e, isaret_al=False)),
                   ("bozuntu yok", lambda m, x, y, e: x.clone())]:
    kontrol(not fgsm_sozlesme(mutant), "hatalı FGSM reddedilmeli: " + ad)
epsler = [0.0, eps, 0.3]
try:
    ogr = egri(model, xs, ys, epsler)
    beklenen = L.epsilon_egrisi_referans(model, xs, ys, epsler)
    uygun = (isinstance(ogr, list) and len(ogr) == len(beklenen) and all(
        isinstance(a, dict) and set(a) == set(b) and a["eps"] == b["eps"]
        and all(isinstance(a[k], float) and abs(a[k] - b[k]) <= 1e-6 for k in ("temiz_dogruluk", "bozuk_dogruluk", "linf"))
        for a, b in zip(ogr, beklenen)))
except Exception as e:
    uygun, beklenen = False, L.epsilon_egrisi_referans(model, xs, ys, epsler)
kontrol(uygun, "ε eğrisi gerçek tahminlerden: temiz/bozuk doğruluk ve L∞ doğru")
xa_tam = L.fgsm_referans(model, X, Y, eps)
with torch.no_grad():
    temiz_t, bozuk_t = model(X).argmax(1), model(xa_tam).argmax(1)
degisen = (temiz_t != bozuk_t).nonzero().flatten().tolist()
ornekler = [{"indeks": i, "etiket": ai_lab.SINIF_ADLARI[int(Y[i])], "temiz_tahmin": ai_lab.SINIF_ADLARI[int(temiz_t[i])],
             "bozuk_tahmin": ai_lab.SINIF_ADLARI[int(bozuk_t[i])]} for i in degisen[:8]]
tam_egri = [{"eps": e, "bozuk_dogruluk": dogruluk(model, ref_fgsm(model, X, Y, e), Y)} for e in [0.0, 0.05, 0.1, 0.2, 0.3]]
yol = ai_lab.kanit_yaz("guvence-fgsm", {
    "kaynak": "gercek", "kabul": all(sonuclar), "model_bilgisi": dict(bilgi, model="fgsm-mlp-64-32-4"),
    "ayarlar": {"altkume": secim, "eps": eps, "epsler": epsler, "tolerans": 1e-6},
    "ogrenci_egrisi": ogr if uygun else None, "referans_egrisi": beklenen, "tam_test_egrisi": tam_egri,
    "tahmini_degisen_ornek_sayisi": len(degisen), "ornekler": ornekler,
    "ozet": {"test_dogrulugu": bilgi["egitim"]["test_dogrulugu"], "eps": eps, "degisen": len(degisen)}})
ok(True, f"GERÇEK ÖLÇÜM: temiz test doğruluğu {bilgi['egitim']['test_dogrulugu']:.3f}; ε={eps} ile tam test kümesinde "
         f"{len(degisen)}/{len(X)} tahmin değişti; eğri " + ", ".join(f"ε={r['eps']}:{r['bozuk_dogruluk']:.3f}" for r in tam_egri))
```

```solution
import torch
import torch.nn.functional as F
import ai_lab

def fgsm(model, x, y, eps):
    x0 = x.clone().detach().requires_grad_(True)
    kayip = F.cross_entropy(model(x0), y)
    gradyan, = torch.autograd.grad(kayip, x0)
    return (x0.detach() + eps * gradyan.sign()).clamp(0, 1)

def _dogruluk(model, x, y):
    with torch.no_grad():
        return (model(x).argmax(1) == y).float().mean().item()

def epsilon_egrisi(model, x, y, epsler):
    temiz = _dogruluk(model, x, y)
    sonuc = []
    for eps in epsler:
        bozuk = fgsm(model, x, y, eps)
        sonuc.append({"eps": eps, "temiz_dogruluk": temiz, "bozuk_dogruluk": _dogruluk(model, bozuk, y),
                      "linf": float((bozuk - x).abs().max())})
    return sonuc

if ai_lab.CALISTIR:
    ai_lab.guvence_goster(fgsm, epsilon_egrisi)
```

```hint
Girdinin kopyasında `requires_grad_(True)` aç, kaybı hesapla ve `torch.autograd.grad(kayip, x0)` ile yalnız girdiye göre türevi al. Sonucu `detach()` edip kırp.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Tek adımlık doğrusal bozuntu (`FGSM`) (30 sn).** "Beyaz kutu erişiminde kaybın girdiye göre gradyan işareti alınır ve girdi $x' = \text{clip}(x + \varepsilon \cdot \text{sign}(\nabla_x \mathcal{L}), 0, 1)$ yönünde tek adımda itilir."
2. **İlan edilen $\varepsilon$ ile gerçekleşen $L_\infty$ farkı (35 sn).** "Sınıra yakın pikseller `[0, 1]` aralığına kırpıldığında gerçekleşen $\|x' - x\|_\infty$ bütçeden küçük kalabilir; doğru rapor ham $\varepsilon$'u değil gerçekleşen $L_\infty$ farkını ve en küçük bütçeli maksimum kayıp noktasını yazar."
3. **Alt sınır sınaması ve gradyan maskeleme (30 sn).** "FGSM'de doğruluğun çökmesi kırılganlığı gösterir ama çökmemesi güvenliği kanıtlamaz; doygun softmax veya türevlenemeyen ön işleme tek adımlı gradyanı gizleyebilir."
4. **Soru (25 sn).** "Bozuntu formülünde `+ eps * sign(grad)` yerine `- eps * sign(grad)` yazılırsa saldırı altında model doğruluğu neden düşmek yerine artabilir?"
:::
