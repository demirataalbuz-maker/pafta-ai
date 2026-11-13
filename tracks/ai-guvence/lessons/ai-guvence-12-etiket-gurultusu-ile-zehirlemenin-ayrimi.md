---
id: ai-guvence-12
title: Etiket Gürültüsü ile Zehirlemenin Ayrımı
summary: Etiket geçişlerini ve performans etkilerini ayrı deneylerde ölç; hedefli değişim sinyalini temiz veri maliyetiyle birlikte değerlendir.
esleme: ai-guvence-13, ai-guvence-14, ai-guvence-15
timeout: 45
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et: Etiket değişiminin yönü önemlidir
Eğitim kümelerindeki veri bozulmaları her zaman kasıtlı bir saldırıdan kaynaklanmaz. İnsan etiketleyicilerin yorgunluğu, belirsiz sınır örnekleri veya sensör hataları veri kümesine **rastgele etiket gürültüsü (`random label noise`)** sokabilir. Rastgele gürültüde etiket geçişleri sınıflar arasında homojen ve yönsüz olarak dağılır. Buna karşılık bir saldırganın gerçekleştirdiği **hedefli etiket zehirlemesi (`targeted label flipping`)**, modelin yalnızca belirli bir hedef sınıfı (ör. kötü amaçlı yazılım sınıfı `2`) zararsız sınıfa (`0`) karıştırmasını sağlamak için tek yönlü olarak kurgulanır.

Bu nedenle güvence analizinde yalnız değişen etiket oranını değil, hangi eski etiketten hangi yeni etikete geçildiğini (`"eski>yeni"`) yönlü olarak saymak zorunludur.

| Gerçek araç / model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Eğitim kümesi denetim araçları (Cleanlab, `scikit-learn` çapraz doğrulama, veri versiyonlama farkları) sınıf geçiş matrislerini ve temiz/hedef altküme doğruluklarını ayrı ayrı raporlar | İlk üç görevde `veri/etiket_gecisleri.json` ve `veri/deney_sonuclari.json` içindeki **sentetik** kayıtları; son görevde `scikit-learn` (`LogisticRegression`) ile `taban`, `rastgele` ve `hedefli` koşullarında eğitilen üç canlı sınıflandırıcıyı | Yalnızca etiket geçiş yoğunluğuna veya tek bir eşik bayrağına bakarak "veri kümesi kesinlikle kasıtlı zehirlenmiştir" hükmü kurulamaz; doğal etiketleme hatası ve sınıf zorluğu da benzer sinyal üretebilir |

> [!NOT]
> İlk üç görevde çalışma dizinine kopyalanan `veri/etiket_gecisleri.json` ve `veri/deney_sonuclari.json` dosyaları **sentetik** eğitim örnekleridir. Her çalıştırmada yeniden kopyalanır; çalıştırmalar arasında **kalıcılık yoktur**. Son adımdaki **Gerçek deney** görevinde ise yazdığın üç işlev `scikit-learn` sınıflandırıcılarının canlı test doğruluklarıyla sınanır; harici denetim araçları veya üçüncü parti fuzzer süreçleri çalıştırılmaz.
:::

::: anlat Rastgele gürültü ile hedefli zehirleme ayrımında ne olur, saldırgan ne dener ve savunma neden kırılır?
Veri güvenliği operasyonlarında rastgele kalite problemleri ile sofistike veri zehirleme saldırılarını birbirinden ayırt etmek kritik öneme sahiptir:

- **Aracın Altında Ne Olur?**
  1. *Etiket Geçiş Profili Çıkarma (`etiket_gecis_profili`):* Orijinal ve değiştirilmiş etiket dizileri karşılaştırılır. Değişen etiketler `"eski>yeni"` kalıbıyla yönlü geçiş sözlüğünde toplanır ve alfabetik olarak sıralanır. Rastgele gürültüde geçişler (`0>1, 1>2, 2>0`) dengeli dağılırken, hedefli zehirlemede belirli bir koldan (`2>0`) ezici bir yoğunlaşma saptanır.
  2. *Etki Karşılaştırması (`etki_karsilastirmasi`):* Üç ayrı senaryoda model eğitilir: Temiz referans (`taban`), rastgele bozulmuş (`rastgele`) ve hedefli manipüle edilmiş (`hedefli`). Her koşul için temiz sınıflardaki doğruluk ile hedef sınıftaki doğruluk ayrı ayrı ölçülür. Taban ortalaması referans alınarak mutlak performans kayıpları (`temiz_kayip` ve `hedef_kayip`) türetilir.
  3. *Hedef Odaklı İnceleme Sinyali (`deney_bayraklari`):* Rastgele gürültü tüm sınıfların ayrılabilirliğini bozar; bu yüzden hem temiz hem hedef sınıfta kayıp oluşur (`temiz_kayip` büyüktür). Hedefli zehirleme ise temiz sınıfların doğruluğunu neredeyse hiç etkilemez (`temiz_kayip <= temiz_esik`), fakat hedef sınıfı felç eder (`hedef_kayip >= hedef_esik`). Bu asimetrik etki güvenlik analistine hedef odaklı inceleme sinyali (`hedef_odakli: True`) üretir.
- **Çıktı Nasıl Okunur?**
  - İnceleme sinyali tek başına adli bir mahkumiyet kararı değildir; hedef sınıfın doğası gereği diğer sınıflarla yüksek örtüşmeye (`class overlap`) sahip olması da benzer bir kayıp tablosu üretebilir.
  - Sinyal, analistlerin körü körüne tüm veri kümesini silmek yerine, doğrudan o belirli geçişe odaklanmasını sağlar.
- **Saldırganın Taktikleri:**
  1. *Temiz Sınıf Maliyetini Asgariye İndirme (Stealth Poisoning):* Saldırgan temiz sınıflara ait etiketlere asla dokunmaz; böylece genel doğruluk tablosunda (`overall validation accuracy`) dikkat çekici bir düşüş yaratmadan modeli hedefine ulaştırır.
  2. *Gürültüyle Kamufle Olma:* Saldırgan, hedefli zehirlemenin etrafına az miktarda rastgele geçiş ekleyerek geçiş matrisini gürültülü göstermeye çalışır.
- **Savunmanın Kırılma Noktaları:**
  - Genel doğruluğa (tüm örnekler üzerinden `accuracy`) odaklanıp sınıf bazlı ayrımı ihmal etmek: Hedef sınıf örneklerin %5'iyse ve tamamen bozulsa bile genel doğruluk %95 civarında kalır, zehirleme gizlenir. Her sınıfa eşit ağırlık veren sınıf bazlı doğruluk ya da macro ortalama bu kaybı ortaya çıkarır.
  - Yönsüz inceleme: Sadece "kaç etiket değişti" sorusuna cevap arayıp "hangi sınıftan hangi sınıfa dönüştü" matrisini çıkarmamak.
- **Sık Yapılan Geliştirici Tuzakları:**
  1. Python'da `bool` sınıfının `int` alt sınıfı olması nedeniyle `isinstance(True, int) == True` tuzağı: Etiket dizilerinde ve doğruluk sayılarında `not isinstance(x, bool)` kontrolünün unutulması.
  2. Değişmeyen etiket çiftlerini (`0>0`) geçiş sözlüğüne dahil etmek: Geçiş sözlüğü yalnız `eski != yeni` olan çiftleri içermelidir.
  3. Performans kaybı hesabında oransal fark almak: Kayıp mutlak farktır (`taban - kosul`), tabana bölünen bir yüzdelik oran değildir.
  4. Koşul gruplarını hesaplarken eksik koşul denetimi yapmamak: Listedeki üç koşulun da (`taban`, `rastgele`, `hedefli`) varlığı doğrulanmazsa sıfıra bölme hatası yaşanır.
:::

::: anlat Temiz ve hedef performans ayrı deneylerde karşılaştırılır
Taban, rastgele gürültü ve hedefli değişim koşullarında temiz veri doğruluğu ile hedef sınıf doğruluğu ayrı tutulur. Performans kaybı taban ortalaması eksi ilgili koşulun ortalamasıdır. Hedefli koşulda büyük hedef kaybı ve küçük temiz kayıp inceleme sinyali üretebilir.

Bu sinyal bir sınıflandırma veya kesin zehirleme hükmü değildir. Veri kümesi, hedef sınıfın doğal zorluğu ve rastgele gürültünün dağılımı sonucu etkileyebilir. Eşikler deney bağlamında seçilir ve iki koşul da raporlanır.
:::

::: tahmin Geçiş oranı ve performans farkını tahmin et
Üç çıktı satırını yaz:

```python
print(round(1 / 3, 6))
print(round(0.9 - 0.75, 6))
print(0.45 >= 0.4 and 0.05 <= 0.1)
```

???

```cikti
0.333333
0.15
True
```

İlk satır değişim oranını, ikinci satır taban eksi koşul performansını, üçüncü satır iki eşiğin birlikte sağlanmasını gösterir.
:::

::: gorev 1 · Etiket geçiş profili çıkar
`etiket_gecis_profili(once, sonra)` işlevini yaz. İki girdi de aynı uzunlukta, boş olmayan listedir. Etiketler bool olmayan, sıfır veya pozitif tamsayılardır. Geçersiz veride `ValueError` yükselt ve girdileri değiştirme.

`{"toplam":N,"degisen":N,"degisim_orani":X,"gecisler":{"eski>yeni":N,...}}` döndür. Geçişlerde yalnız değişen çiftler bulunur ve anahtarlar alfabetik sıralı oluşturulur. Oran değişen/toplam olup altı ondalık basamağa yuvarlanır.

```starter
from ai_guvence_veri import json_yukle

def etiket_gecis_profili(once, sonra):
    # KUSURLU BAŞLANGIÇ KODU: yönlü geçiş sözlüğünü (eski>yeni) boş bırakıp yalnız değişen sayısını döndürüyor!
    if not isinstance(once, list) or not isinstance(sonra, list) or not once or len(once) != len(sonra):
        raise ValueError("liste hatası")
    degisen = sum(1 for a, b in zip(once, sonra) if a != b)
    return {"toplam": len(once), "degisen": degisen, "degisim_orani": round(degisen / len(once), 6), "gecisler": {}}

ornek = json_yukle("veri/etiket_gecisleri.json")
print("Örnek geçiş profili:", etiket_gecis_profili(ornek["once"], ornek["sonra"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-12")
```

```test
import copy
A = [0, 1, 1, 2]
B = [0, 2, 1, 0]
def sozlesme(fn):
    try:
        aonce = copy.deepcopy(A)
        bonce = copy.deepcopy(B)
        beklenen = {"toplam": 4, "degisen": 2, "degisim_orani": 0.5, "gecisler": {"1>2": 1, "2>0": 1}}
        if fn(A, B) != beklenen or A != aonce or B != bonce:
            return False
        if fn([0, 0], [0, 0]) != {"toplam": 2, "degisen": 0, "degisim_orani": 0.0, "gecisler": {}}:
            return False
        yuvarla = fn([0, 1, 2], [0, 0, 0])
        if yuvarla != {"toplam": 3, "degisen": 2, "degisim_orani": 0.666667, "gecisler": {"1>0": 1, "2>0": 1}}:
            return False
        tekrar = fn([1, 1, 2], [0, 0, 0])
        if tekrar["gecisler"] != {"1>0": 2, "2>0": 1}:
            return False
        for once, sonra in [
            (None, B), (A, None), ({}, B), (A, {}), (tuple(A), B), (A, tuple(B)), ([], []), ([], B), (A, []), ([0], B), (A, [0]),
            ([True, 1], [0, 1]), ([0.0, 1], [0, 1]), ([-1, 1], [0, 1]), (["0", 1], [0, 1]),
            (A, [True, 1, 1, 2]), (A, [0.0, 1, 1, 2]), (A, [-1, 1, 1, 2]), (A, ["0", 1, 1, 2]),
        ]:
            try:
                fn(once, sonra)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(etiket_gecis_profili), "etiket geçişleri, oran ve sayımlar korunmalı")
def m_once(once, sonra):
    return etiket_gecis_profili([0 for _ in once], sonra)
def m_sonra(once, sonra):
    return etiket_gecis_profili(once, [0 for _ in sonra])
def m_boyut(once, sonra):
    return etiket_gecis_profili(once[:1], sonra)
for ad, mutant in [("eski etiketleri silen", m_once), ("yeni etiketleri silen", m_sonra), ("boyutu bozan", m_boyut)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def etiket_gecis_profili(once, sonra):
    if not isinstance(once, list):
        raise ValueError("önce liste olmalı")
    if not isinstance(sonra, list):
        raise ValueError("sonra liste olmalı")
    if not once:
        raise ValueError("etiket listeleri boş olamaz")
    if not sonra:
        raise ValueError("etiket listeleri boş olamaz")
    if len(once) != len(sonra):
        raise ValueError("etiket listeleri aynı boyutta olmalı")
    for etiketler in (once, sonra):
        for etiket in etiketler:
            if isinstance(etiket, bool):
                raise ValueError("etiket tamsayı olmalı")
            if not isinstance(etiket, int):
                raise ValueError("etiket tamsayı olmalı")
            if etiket < 0:
                raise ValueError("etiket negatif olamaz")
    sayimlar = {}
    degisen = 0
    for eski, yeni in zip(once, sonra):
        if eski != yeni:
            degisen += 1
            anahtar = f"{eski}>{yeni}"
            sayimlar[anahtar] = sayimlar.get(anahtar, 0) + 1
    gecisler = {anahtar: sayimlar[anahtar] for anahtar in sorted(sayimlar)}
    return {"toplam": len(once), "degisen": degisen, "degisim_orani": round(degisen / len(once), 6), "gecisler": gecisler}
```

```hint
Yalnız eski ve yeni etiketin farklı olduğu çiftleri say. Geçiş anahtarlarını son çıktıda sıralı oluştur.
```
:::

::: gorev 2 · Rastgele ve hedefli deney etkilerini karşılaştır
`etki_karsilastirmasi(kayitlar)` işlevini yaz. Kayıtlar boş olmayan listedir; her kayıt tam olarak `kosul`, `temiz`, `hedef` alanlarını taşır. Koşul yalnız `taban`, `rastgele` veya `hedefli`; iki doğruluk da bool olmayan sonlu sayı ve `[0,1]` aralığındadır. Üç koşuldan da en az bir kayıt bulunmalıdır. Geçersiz veride `ValueError` yükselt.

Her koşulun temiz ve hedef ortalamasını hesapla. Rastgele ve hedefli için performans kaybı taban ortalaması eksi koşul ortalamasıdır. `{"ortalamalar":{KOSUL:{"temiz":X,"hedef":X},...},"temiz_kayip":{"rastgele":X,"hedefli":X},"hedef_kayip":{"rastgele":X,"hedefli":X}}` döndür; koşulları `taban`, `rastgele`, `hedefli` sırasıyla ver. Bütün çıktıları ham ortalamalardan hesaplayıp altı ondalık basamağa yuvarla ve girdiyi değiştirme.

```starter
from ai_guvence_veri import json_yukle

def etki_karsilastirmasi(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: taban ortalamasından fark almak yerine kayıpları sıfır bırakıyor!
    return {
        "ortalamalar": {"taban": {"temiz": 0.0, "hedef": 0.0}, "rastgele": {"temiz": 0.0, "hedef": 0.0}, "hedefli": {"temiz": 0.0, "hedef": 0.0}},
        "temiz_kayip": {"rastgele": 0.0, "hedefli": 0.0},
        "hedef_kayip": {"rastgele": 0.0, "hedefli": 0.0},
    }

ornek = json_yukle("veri/deney_sonuclari.json")
print("Örnek etki karşılaştırması:", etki_karsilastirmasi(ornek["kosul_kayitlari"]))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-12")
```

```test
import copy
K = [
    {"kosul": "taban", "temiz": 0.9, "hedef": 0.85},
    {"kosul": "rastgele", "temiz": 0.75, "hedef": 0.8},
    {"kosul": "hedefli", "temiz": 0.85, "hedef": 0.4},
]
BEKLENEN = {
    "ortalamalar": {"taban": {"temiz": 0.9, "hedef": 0.85}, "rastgele": {"temiz": 0.75, "hedef": 0.8}, "hedefli": {"temiz": 0.85, "hedef": 0.4}},
    "temiz_kayip": {"rastgele": 0.15, "hedefli": 0.05},
    "hedef_kayip": {"rastgele": 0.05, "hedefli": 0.45},
}
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K) != BEKLENEN or K != once:
            return False
        sinir = fn([{"kosul": "taban", "temiz": 1, "hedef": 1}, {"kosul": "rastgele", "temiz": 0, "hedef": 0}, {"kosul": "hedefli", "temiz": 1, "hedef": 0}])
        if sinir["temiz_kayip"] != {"rastgele": 1, "hedefli": 0} or sinir["hedef_kayip"] != {"rastgele": 1, "hedefli": 1}:
            return False
        yuvarla = fn([
            {"kosul": "taban", "temiz": 1, "hedef": 1}, {"kosul": "taban", "temiz": 0, "hedef": 0}, {"kosul": "taban", "temiz": 0, "hedef": 0},
            {"kosul": "rastgele", "temiz": 0, "hedef": 0}, {"kosul": "hedefli", "temiz": 0, "hedef": 0},
        ])
        if yuvarla["ortalamalar"]["taban"] != {"temiz": 0.333333, "hedef": 0.333333} or yuvarla["temiz_kayip"]["rastgele"] != 0.333333 or yuvarla["hedef_kayip"]["hedefli"] != 0.333333:
            return False
        for kayitlar in [
            None, {}, tuple(K), [], [None], [dict(K[0], ek=1), K[1], K[2]], [K[0], K[1], K[2], dict(K[0], kosul="diger")], [dict(K[0], kosul=[]), K[1], K[2]], [dict(K[0], kosul="diger"), K[1], K[2]],
            [K[0], K[1]], [K[0], K[2]], [K[1], K[2]],
            [dict(K[0], temiz=True), K[1], K[2]], [dict(K[0], temiz="0.9"), K[1], K[2]],
            [dict(K[0], temiz=float("nan")), K[1], K[2]], [dict(K[0], temiz=float("inf")), K[1], K[2]],
            [dict(K[0], temiz=-0.1), K[1], K[2]], [dict(K[0], temiz=1.1), K[1], K[2]],
            [dict(K[0], hedef=True), K[1], K[2]], [dict(K[0], hedef="0.85"), K[1], K[2]],
            [dict(K[0], hedef=float("nan")), K[1], K[2]], [dict(K[0], hedef=float("inf")), K[1], K[2]],
            [dict(K[0], hedef=-0.1), K[1], K[2]], [dict(K[0], hedef=1.1), K[1], K[2]],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(etki_karsilastirmasi), "üç koşul, ortalamalar ve iki performans kaybı korunmalı")
def m_temiz(kayitlar):
    return etki_karsilastirmasi([dict(x, temiz=0) for x in kayitlar])
def m_hedef(kayitlar):
    return etki_karsilastirmasi([dict(x, hedef=0) for x in kayitlar])
def m_kosul(kayitlar):
    return etki_karsilastirmasi([dict(x, kosul="taban") for x in kayitlar])
for ad, mutant in [("temiz ölçümü silen", m_temiz), ("hedef ölçümü silen", m_hedef), ("koşulları birleştiren", m_kosul)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def etki_karsilastirmasi(kayitlar):
    import math
    kosul_sirasi = ("taban", "rastgele", "hedefli")
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    if not kayitlar:
        raise ValueError("kayıtlar boş olamaz")
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"kosul", "temiz", "hedef"}:
            raise ValueError("kayıt şeması geçersiz")
        if kayit["kosul"] not in kosul_sirasi:
            raise ValueError("koşul geçersiz")
        for alan in ("temiz", "hedef"):
            deger = kayit[alan]
            if isinstance(deger, bool):
                raise ValueError("doğruluk sayı olmalı")
            if not isinstance(deger, (int, float)):
                raise ValueError("doğruluk sayı olmalı")
            if not math.isfinite(deger):
                raise ValueError("doğruluk sonlu olmalı")
            if deger < 0 or deger > 1:
                raise ValueError("doğruluk aralık dışında")
    if {x["kosul"] for x in kayitlar} != set(kosul_sirasi):
        raise ValueError("üç koşul da gerekli")
    ortalamalar = {}
    for kosul in kosul_sirasi:
        grup = [x for x in kayitlar if x["kosul"] == kosul]
        ortalamalar[kosul] = {alan: sum(x[alan] for x in grup) / len(grup) for alan in ("temiz", "hedef")}
    return {
        "ortalamalar": {kosul: {alan: round(deger, 6) for alan, deger in ortalamalar[kosul].items()} for kosul in kosul_sirasi},
        "temiz_kayip": {kosul: round(ortalamalar["taban"]["temiz"] - ortalamalar[kosul]["temiz"], 6) for kosul in ("rastgele", "hedefli")},
        "hedef_kayip": {kosul: round(ortalamalar["taban"]["hedef"] - ortalamalar[kosul]["hedef"], 6) for kosul in ("rastgele", "hedefli")},
    }
```

```hint
Önce üç koşulun ham ortalamalarını üret. Kayıpları bu ortalamalar arasındaki farklardan hesapla; tabanı payda gibi kullanma.
```
:::

::: gorev 3 · Hedef odaklı inceleme sinyali üret
`deney_bayraklari(kayitlar, temiz_esik, hedef_esik)` işlevini yaz. Kayıtlar boş olmayan listedir; her kayıt tam olarak `tur`, `temiz_kayip`, `hedef_kayip` alanlarını taşır. Tür yalnız `rastgele` veya `hedefli`; iki kayıp ve iki eşik bool olmayan sonlu sayı ve `[0,1]` aralığındadır. İki türden de en az bir kayıt bulunmalıdır. Geçersiz veride `ValueError` yükselt.

Her türün iki kayıp ortalamasını altı ondalık basamağa yuvarla. `hedef_odakli` bayrağı ham `hedef_kayip >= hedef_esik` ve ham `temiz_kayip <= temiz_esik` koşullarının birlikte sağlanmasıdır. `{"rastgele":{"temiz_kayip":X,"hedef_kayip":X,"hedef_odakli":BOOL},"hedefli":{...}}` döndür ve girdiyi değiştirme. Bayrak kesin zehirleme hükmü değildir.

```starter
from ai_guvence_veri import json_yukle

def deney_bayraklari(kayitlar, temiz_esik, hedef_esik):
    # KUSURLU BAŞLANGIÇ KODU: temiz_kayip <= temiz_esik koşulunu kontrol etmeden yalnız hedef_kayip'a bakıyor!
    sonuc = {}
    for tur in ("rastgele", "hedefli"):
        grup = [x for x in (kayitlar or []) if isinstance(x, dict) and x.get("tur") == tur]
        if grup:
            t = sum(x["temiz_kayip"] for x in grup) / len(grup)
            h = sum(x["hedef_kayip"] for x in grup) / len(grup)
            sonuc[tur] = {"temiz_kayip": round(t, 6), "hedef_kayip": round(h, 6), "hedef_odakli": h >= hedef_esik}
    return sonuc

ornek = json_yukle("veri/deney_sonuclari.json")
print("Örnek bayraklar:", deney_bayraklari(ornek["kayip_kayitlari"], 0.1, 0.4))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-12")
```

```test
import copy
K = [
    {"tur": "rastgele", "temiz_kayip": 0.2, "hedef_kayip": 0.1},
    {"tur": "hedefli", "temiz_kayip": 0.05, "hedef_kayip": 0.5},
]
BEKLENEN = {"rastgele": {"temiz_kayip": 0.2, "hedef_kayip": 0.1, "hedef_odakli": False}, "hedefli": {"temiz_kayip": 0.05, "hedef_kayip": 0.5, "hedef_odakli": True}}
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K, 0.1, 0.4) != BEKLENEN or K != once:
            return False
        esikte = fn([K[1], K[0]], 0.05, 0.5)
        if not esikte["hedefli"]["hedef_odakli"]:
            return False
        ters = fn([K[1], K[0]], 0.01, 0.4)
        if ters["hedefli"]["hedef_odakli"]:
            return False
        if fn([{"tur": "rastgele", "temiz_kayip": 0.05, "hedef_kayip": 0.1}, K[1]], 0.1, 0.4)["rastgele"]["hedef_odakli"] is not False:
            return False
        yuvarla = fn([
            {"tur": "rastgele", "temiz_kayip": 1, "hedef_kayip": 1}, {"tur": "rastgele", "temiz_kayip": 0, "hedef_kayip": 0}, {"tur": "rastgele", "temiz_kayip": 0, "hedef_kayip": 0},
            {"tur": "hedefli", "temiz_kayip": 0, "hedef_kayip": 0},
        ], 1, 0)
        if yuvarla["rastgele"] != {"temiz_kayip": 0.333333, "hedef_kayip": 0.333333, "hedef_odakli": True}:
            return False
        for kayitlar, temiz_esik, hedef_esik in [
            (None, 0.1, 0.4), (K, None, 0.4), (K, 0.1, None), ({}, 0.1, 0.4), (tuple(K), 0.1, 0.4), ([], 0.1, 0.4),
            ([None], 0.1, 0.4), ([dict(K[0], ek=1), K[1]], 0.1, 0.4), ([K[0]], 0.1, 0.4), ([K[1]], 0.1, 0.4),
            ([dict(K[0], tur="diger"), K[1]], 0.1, 0.4), ([K[0], K[1], dict(K[0], tur="diger")], 0.1, 0.4), ([dict(K[0], tur=[]), K[1]], 0.1, 0.4),
            ([dict(K[0], temiz_kayip=True), K[1]], 0.1, 0.4), ([dict(K[0], temiz_kayip="0.2"), K[1]], 0.1, 0.4),
            ([dict(K[0], temiz_kayip=float("nan")), K[1]], 0.1, 0.4), ([dict(K[0], temiz_kayip=-0.1), K[1]], 0.1, 0.4),
            ([dict(K[0], temiz_kayip=1.1), K[1]], 0.1, 0.4), ([dict(K[0], hedef_kayip=True), K[1]], 0.1, 0.4),
            ([dict(K[0], hedef_kayip="0.1"), K[1]], 0.1, 0.4), ([dict(K[0], hedef_kayip=float("inf")), K[1]], 0.1, 0.4),
            ([dict(K[0], hedef_kayip=-0.1), K[1]], 0.1, 0.4), ([dict(K[0], hedef_kayip=1.1), K[1]], 0.1, 0.4),
            (K, True, 0.4), (K, "0.1", 0.4), (K, float("nan"), 0.4), (K, -0.1, 0.4), (K, 1.1, 0.4),
            (K, 0.1, True), (K, 0.1, "0.4"), (K, 0.1, float("inf")), (K, 0.1, -0.1), (K, 0.1, 1.1),
        ]:
            try:
                fn(kayitlar, temiz_esik, hedef_esik)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(deney_bayraklari), "eşikler, iki kayıp ve inceleme bayrağı korunmalı")
def m_temiz(kayitlar, temiz_esik, hedef_esik):
    return deney_bayraklari([dict(x, temiz_kayip=0) for x in kayitlar], temiz_esik, hedef_esik)
def m_hedef(kayitlar, temiz_esik, hedef_esik):
    return deney_bayraklari([dict(x, hedef_kayip=0) for x in kayitlar], temiz_esik, hedef_esik)
def m_tur(kayitlar, temiz_esik, hedef_esik):
    return deney_bayraklari([dict(x, tur="hedefli") for x in kayitlar], temiz_esik, hedef_esik)
for ad, mutant in [("temiz kaybı silen", m_temiz), ("hedef kaybı silen", m_hedef), ("türleri birleştiren", m_tur)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def deney_bayraklari(kayitlar, temiz_esik, hedef_esik):
    import math
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    if not kayitlar:
        raise ValueError("kayıtlar boş olamaz")
    for esik in (temiz_esik, hedef_esik):
        if isinstance(esik, bool):
            raise ValueError("eşik sayı olmalı")
        if not isinstance(esik, (int, float)):
            raise ValueError("eşik sayı olmalı")
        if not math.isfinite(esik):
            raise ValueError("eşik sonlu olmalı")
        if esik < 0 or esik > 1:
            raise ValueError("eşik aralık dışında")
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            raise ValueError("kayıt sözlük olmalı")
        if set(kayit) != {"tur", "temiz_kayip", "hedef_kayip"}:
            raise ValueError("kayıt şeması geçersiz")
        if kayit["tur"] not in ("rastgele", "hedefli"):
            raise ValueError("tür geçersiz")
        for alan in ("temiz_kayip", "hedef_kayip"):
            deger = kayit[alan]
            if isinstance(deger, bool):
                raise ValueError("kayıp sayı olmalı")
            if not isinstance(deger, (int, float)):
                raise ValueError("kayıp sayı olmalı")
            if not math.isfinite(deger):
                raise ValueError("kayıp sonlu olmalı")
            if deger < 0 or deger > 1:
                raise ValueError("kayıp aralık dışında")
    if {x["tur"] for x in kayitlar} != {"rastgele", "hedefli"}:
        raise ValueError("iki tür de gerekli")
    sonuc = {}
    for tur in ("rastgele", "hedefli"):
        grup = [x for x in kayitlar if x["tur"] == tur]
        temiz = sum(x["temiz_kayip"] for x in grup) / len(grup)
        hedef = sum(x["hedef_kayip"] for x in grup) / len(grup)
        sonuc[tur] = {"temiz_kayip": round(temiz, 6), "hedef_kayip": round(hedef, 6), "hedef_odakli": hedef >= hedef_esik and temiz <= temiz_esik}
    return sonuc
```

```hint
Bayrağı yuvarlanmış görüntü değerlerinden değil ham ortalamalardan hesapla. İki eşik koşulunu `and` ile birleştir.
```
:::

::: anlat `scikit-learn` ile taban, rastgele gürültü ve hedefli zehirleme deneylerinin canlı karşılaştırması
Önceki üç görevde etiket geçiş sayımını, koşullar arası doğruluk kaybını ve hedef odaklı inceleme bayrağını sentetik veriler üzerinde yazdın. Şimdi aynı üç işlevi **`scikit-learn` (`LogisticRegression`) ile üç ayrı koşulda (`taban`, `rastgele` etiket gürültüsü, `hedefli` sınıf çevirme) gerçekten eğitilen sınıflandırıcılara** bağlıyoruz:

1. Hedefli zehirleme koşulunda hedef sınıf (`2`) örneklerinin sınıf `0`'a çevrilmesi `etiket_gecis_profili` ile ölçülür,
2. Üç modelin temiz altküme ve hedef sınıf üzerindeki gerçek test doğrulukları `etki_karsilastirmasi` ile karşılaştırılır,
3. Oluşan temiz ve hedef doğruluk kayıpları `deney_bayraklari` ile değerlendirilerek hedefli zehirlemenin temiz doğruluğu bozmadan hedef sınıfı çökerttiği kanıt dosyasına kaydedilir.

Kaynaklar: [Biggio vd. 2012 — Poisoning Attacks against Support Vector Machines (arXiv:1206.6389)](https://arxiv.org/abs/1206.6389), [NIST AI 100-2 E2023 — Adversarial Machine Learning](https://csrc.nist.gov/pubs/ai/100/2/e2023/final).
:::

::: gorev Gerçek deney · scikit-learn ile rastgele gürültü ve hedefli zehirleme ayrımı
Önceki üç görevde yazdığın `etiket_gecis_profili(once, sonra)`, `etki_karsilastirmasi(kayitlar)` ve `deney_bayraklari(kayitlar, temiz_esik, hedef_esik)` işlevlerini burada birleştir.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 180
```

```starter
import math
import ai_lab
from sandbox import ai_gercek_ai_guvence_12 as L

def etiket_gecis_profili(once, sonra):
    # KUSURLU BAŞLANGIÇ KODU: yönlü geçişleri boş bırakıyor!
    return {"toplam": len(once), "degisen": 0, "degisim_orani": 0.0, "gecisler": {}}

def etki_karsilastirmasi(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: taban ortalamasını çıkarmadan kayıpları sıfır bırakıyor!
    return {"ortalamalar": {}, "temiz_kayip": {"rastgele": 0.0, "hedefli": 0.0}, "hedef_kayip": {"rastgele": 0.0, "hedefli": 0.0}}

def deney_bayraklari(kayitlar, temiz_esik, hedef_esik):
    # KUSURLU BAŞLANGIÇ KODU: temiz kaybı denetlemeden bayrağı doğrudan False dönüyor!
    return {"rastgele": {"hedef_odakli": False}, "hedefli": {"hedef_odakli": False}}

if ai_lab.CALISTIR:
    L.goster(etiket_gecis_profili, etki_karsilastirmasi, deney_bayraklari)
```

```test
import ast
import ai_lab
from sandbox import ai_gercek_ai_guvence_12 as L

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for ad in ("etiket_gecis_profili", "etki_karsilastirmasi", "deney_bayraklari"):
    need(ad)

yasak = (
    "referans",
    "etiket_gecis_profili_referans",
    "etki_karsilastirmasi_referans",
    "deney_bayraklari_referans",
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
        if etiket_gecis_profili([0, 1, 1, 2], [0, 2, 1, 0]) != {"toplam": 4, "degisen": 2, "degisim_orani": 0.5, "gecisler": {"1>2": 1, "2>0": 1}}:
            return False
        for bo, bs in [(None, [0]), ([0], [0, 1]), ([True], [0])]:
            try:
                etiket_gecis_profili(bo, bs)
                return False
            except ValueError:
                pass
        K = [
            {"kosul": "taban", "temiz": 0.9, "hedef": 0.85},
            {"kosul": "rastgele", "temiz": 0.75, "hedef": 0.8},
            {"kosul": "hedefli", "temiz": 0.85, "hedef": 0.4},
        ]
        if etki_karsilastirmasi(K)["hedef_kayip"] != {"rastgele": 0.05, "hedefli": 0.45}:
            return False
        B = [
            {"tur": "rastgele", "temiz_kayip": 0.2, "hedef_kayip": 0.1},
            {"tur": "hedefli", "temiz_kayip": 0.05, "hedef_kayip": 0.5},
        ]
        if deney_bayraklari(B, 0.1, 0.4)["hedefli"]["hedef_odakli"] is not True:
            return False
        return True
    except Exception:
        return False

def _birim1(fn):
    import copy
    A = [0, 1, 1, 2]
    B = [0, 2, 1, 0]
    def sozlesme(fn):
        try:
            aonce = copy.deepcopy(A)
            bonce = copy.deepcopy(B)
            beklenen = {"toplam": 4, "degisen": 2, "degisim_orani": 0.5, "gecisler": {"1>2": 1, "2>0": 1}}
            if fn(A, B) != beklenen or A != aonce or B != bonce:
                return False
            if fn([0, 0], [0, 0]) != {"toplam": 2, "degisen": 0, "degisim_orani": 0.0, "gecisler": {}}:
                return False
            yuvarla = fn([0, 1, 2], [0, 0, 0])
            if yuvarla != {"toplam": 3, "degisen": 2, "degisim_orani": 0.666667, "gecisler": {"1>0": 1, "2>0": 1}}:
                return False
            tekrar = fn([1, 1, 2], [0, 0, 0])
            if tekrar["gecisler"] != {"1>0": 2, "2>0": 1}:
                return False
            for once, sonra in [
                (None, B), (A, None), ({}, B), (A, {}), (tuple(A), B), (A, tuple(B)), ([], []), ([], B), (A, []), ([0], B), (A, [0]),
                ([True, 1], [0, 1]), ([0.0, 1], [0, 1]), ([-1, 1], [0, 1]), (["0", 1], [0, 1]),
                (A, [True, 1, 1, 2]), (A, [0.0, 1, 1, 2]), (A, [-1, 1, 1, 2]), (A, ["0", 1, 1, 2]),
            ]:
                try:
                    fn(once, sonra)
                    return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False
    return sozlesme(fn)

def _birim2(fn):
    import copy
    K = [
        {"kosul": "taban", "temiz": 0.9, "hedef": 0.85},
        {"kosul": "rastgele", "temiz": 0.75, "hedef": 0.8},
        {"kosul": "hedefli", "temiz": 0.85, "hedef": 0.4},
    ]
    BEKLENEN = {
        "ortalamalar": {"taban": {"temiz": 0.9, "hedef": 0.85}, "rastgele": {"temiz": 0.75, "hedef": 0.8}, "hedefli": {"temiz": 0.85, "hedef": 0.4}},
        "temiz_kayip": {"rastgele": 0.15, "hedefli": 0.05},
        "hedef_kayip": {"rastgele": 0.05, "hedefli": 0.45},
    }
    def sozlesme(fn):
        try:
            once = copy.deepcopy(K)
            if fn(K) != BEKLENEN or K != once:
                return False
            sinir = fn([{"kosul": "taban", "temiz": 1, "hedef": 1}, {"kosul": "rastgele", "temiz": 0, "hedef": 0}, {"kosul": "hedefli", "temiz": 1, "hedef": 0}])
            if sinir["temiz_kayip"] != {"rastgele": 1, "hedefli": 0} or sinir["hedef_kayip"] != {"rastgele": 1, "hedefli": 1}:
                return False
            yuvarla = fn([
                {"kosul": "taban", "temiz": 1, "hedef": 1}, {"kosul": "taban", "temiz": 0, "hedef": 0}, {"kosul": "taban", "temiz": 0, "hedef": 0},
                {"kosul": "rastgele", "temiz": 0, "hedef": 0}, {"kosul": "hedefli", "temiz": 0, "hedef": 0},
            ])
            if yuvarla["ortalamalar"]["taban"] != {"temiz": 0.333333, "hedef": 0.333333} or yuvarla["temiz_kayip"]["rastgele"] != 0.333333 or yuvarla["hedef_kayip"]["hedefli"] != 0.333333:
                return False
            for kayitlar in [
                None, {}, tuple(K), [], [None], [dict(K[0], ek=1), K[1], K[2]], [K[0], K[1], K[2], dict(K[0], kosul="diger")], [dict(K[0], kosul=[]), K[1], K[2]], [dict(K[0], kosul="diger"), K[1], K[2]],
                [K[0], K[1]], [K[0], K[2]], [K[1], K[2]],
                [dict(K[0], temiz=True), K[1], K[2]], [dict(K[0], temiz="0.9"), K[1], K[2]],
                [dict(K[0], temiz=float("nan")), K[1], K[2]], [dict(K[0], temiz=float("inf")), K[1], K[2]],
                [dict(K[0], temiz=-0.1), K[1], K[2]], [dict(K[0], temiz=1.1), K[1], K[2]],
                [dict(K[0], hedef=True), K[1], K[2]], [dict(K[0], hedef="0.85"), K[1], K[2]],
                [dict(K[0], hedef=float("nan")), K[1], K[2]], [dict(K[0], hedef=float("inf")), K[1], K[2]],
                [dict(K[0], hedef=-0.1), K[1], K[2]], [dict(K[0], hedef=1.1), K[1], K[2]],
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
    K = [
        {"tur": "rastgele", "temiz_kayip": 0.2, "hedef_kayip": 0.1},
        {"tur": "hedefli", "temiz_kayip": 0.05, "hedef_kayip": 0.5},
    ]
    BEKLENEN = {"rastgele": {"temiz_kayip": 0.2, "hedef_kayip": 0.1, "hedef_odakli": False}, "hedefli": {"temiz_kayip": 0.05, "hedef_kayip": 0.5, "hedef_odakli": True}}
    def sozlesme(fn):
        try:
            once = copy.deepcopy(K)
            if fn(K, 0.1, 0.4) != BEKLENEN or K != once:
                return False
            esikte = fn([K[1], K[0]], 0.05, 0.5)
            if not esikte["hedefli"]["hedef_odakli"]:
                return False
            ters = fn([K[1], K[0]], 0.01, 0.4)
            if ters["hedefli"]["hedef_odakli"]:
                return False
            if fn([{"tur": "rastgele", "temiz_kayip": 0.05, "hedef_kayip": 0.1}, K[1]], 0.1, 0.4)["rastgele"]["hedef_odakli"] is not False:
                return False
            yuvarla = fn([
                {"tur": "rastgele", "temiz_kayip": 1, "hedef_kayip": 1}, {"tur": "rastgele", "temiz_kayip": 0, "hedef_kayip": 0}, {"tur": "rastgele", "temiz_kayip": 0, "hedef_kayip": 0},
                {"tur": "hedefli", "temiz_kayip": 0, "hedef_kayip": 0},
            ], 1, 0)
            if yuvarla["rastgele"] != {"temiz_kayip": 0.333333, "hedef_kayip": 0.333333, "hedef_odakli": True}:
                return False
            for kayitlar, temiz_esik, hedef_esik in [
                (None, 0.1, 0.4), (K, None, 0.4), (K, 0.1, None), ({}, 0.1, 0.4), (tuple(K), 0.1, 0.4), ([], 0.1, 0.4),
                ([None], 0.1, 0.4), ([dict(K[0], ek=1), K[1]], 0.1, 0.4), ([K[0]], 0.1, 0.4), ([K[1]], 0.1, 0.4),
                ([dict(K[0], tur="diger"), K[1]], 0.1, 0.4), ([K[0], K[1], dict(K[0], tur="diger")], 0.1, 0.4), ([dict(K[0], tur=[]), K[1]], 0.1, 0.4),
                ([dict(K[0], temiz_kayip=True), K[1]], 0.1, 0.4), ([dict(K[0], temiz_kayip="0.2"), K[1]], 0.1, 0.4),
                ([dict(K[0], temiz_kayip=float("nan")), K[1]], 0.1, 0.4), ([dict(K[0], temiz_kayip=-0.1), K[1]], 0.1, 0.4),
                ([dict(K[0], temiz_kayip=1.1), K[1]], 0.1, 0.4), ([dict(K[0], hedef_kayip=True), K[1]], 0.1, 0.4),
                ([dict(K[0], hedef_kayip="0.1"), K[1]], 0.1, 0.4), ([dict(K[0], hedef_kayip=float("inf")), K[1]], 0.1, 0.4),
                ([dict(K[0], hedef_kayip=-0.1), K[1]], 0.1, 0.4), ([dict(K[0], hedef_kayip=1.1), K[1]], 0.1, 0.4),
                (K, True, 0.4), (K, "0.1", 0.4), (K, float("nan"), 0.4), (K, -0.1, 0.4), (K, 1.1, 0.4),
                (K, 0.1, True), (K, 0.1, "0.4"), (K, 0.1, float("inf")), (K, 0.1, -0.1), (K, 0.1, 1.1),
            ]:
                try:
                    fn(kayitlar, temiz_esik, hedef_esik)
                    return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False
    return sozlesme(fn)

ok(_birim1(etiket_gecis_profili), "etiket_gecis_profili tam birim sözleşmesini geçmeli")
ok(_birim2(etki_karsilastirmasi), "etki_karsilastirmasi tam birim sözleşmesini geçmeli")
ok(_birim3(deney_bayraklari), "deney_bayraklari tam birim sözleşmesini geçmeli")
ok(_sozlesme_kontrol(), "etiket_gecis_profili, etki_karsilastirmasi ve deney_bayraklari sözleşme kontrollerini geçmeli")
if not all(checks):
    stop()

try:
    rapor = L.deney(etiket_gecis_profili, etki_karsilastirmasi, deney_bayraklari)
except ai_lab.GercekLabYok as e:
    ok(False, str(e))
    stop()
except Exception as e:
    ok(False, f"GERÇEK ETİKET GÜRÜLTÜSÜ/ZEHİRLEME DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

k = rapor["kontroller"]
ok(k["gecis_uyumu"], f"etiket_gecis_profili canlı hedefli geçişlerde referansla uyuşmalı: {rapor['gecis']}")
ok(k["etki_uyumu"], f"etki_karsilastirmasi canlı model doğruluklarında referansla uyuşmalı: {rapor['etki']}")
ok(k["bayrak_uyumu"] and k["hedefli_yakalandi"], f"deney_bayraklari canlı deneyde hedefli zehirleme sinyalini yakalamalı: {rapor['bayraklar']}")

kabul = all(checks)
kanit_yolu = ai_lab.kanit_yaz("guvence-12-etiket-zehirleme", dict(rapor, kaynak="gercek", kabul=kabul))
o = rapor["ozet"]
print(f"GERÇEK ETİKET ZEHİRLEME DENEYİ: sklearn={o['sklearn_surum']} geçiş={o['hedefli_gecisler']} hedef_kayıp={o['hedef_kayip']} kanıt={kanit_yolu}")
```

```solution
import math
import ai_lab
from sandbox import ai_gercek_ai_guvence_12 as L

def etiket_gecis_profili(once, sonra):
    if not isinstance(once, list) or not isinstance(sonra, list) or not once or len(once) != len(sonra):
        raise ValueError("etiket listeleri geçersiz")
    for etiketler in (once, sonra):
        for e in etiketler:
            if isinstance(e, bool) or not isinstance(e, int) or e < 0:
                raise ValueError("etiket geçersiz")
    sayimlar = {}
    degisen = 0
    for eski, yeni in zip(once, sonra):
        if eski != yeni:
            degisen += 1
            k = f"{eski}>{yeni}"
            sayimlar[k] = sayimlar.get(k, 0) + 1
    return {"toplam": len(once), "degisen": degisen, "degisim_orani": round(degisen / len(once), 6), "gecisler": {k: sayimlar[k] for k in sorted(sayimlar)}}

def etki_karsilastirmasi(kayitlar):
    kosul_sirasi = ("taban", "rastgele", "hedefli")
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar geçersiz")
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"kosul", "temiz", "hedef"}:
            raise ValueError("şema geçersiz")
        if kayit["kosul"] not in kosul_sirasi:
            raise ValueError("koşul geçersiz")
        for alan in ("temiz", "hedef"):
            d = kayit[alan]
            if isinstance(d, bool) or not isinstance(d, (int, float)) or not math.isfinite(d) or d < 0 or d > 1:
                raise ValueError("doğruluk geçersiz")
    if {x["kosul"] for x in kayitlar} != set(kosul_sirasi):
        raise ValueError("üç koşul gerekli")
    ort = {}
    for kosul in kosul_sirasi:
        grup = [x for x in kayitlar if x["kosul"] == kosul]
        ort[kosul] = {a: sum(x[a] for x in grup) / len(grup) for a in ("temiz", "hedef")}
    return {
        "ortalamalar": {k: {a: round(v, 6) for a, v in ort[k].items()} for k in kosul_sirasi},
        "temiz_kayip": {k: round(ort["taban"]["temiz"] - ort[k]["temiz"], 6) for k in ("rastgele", "hedefli")},
        "hedef_kayip": {k: round(ort["taban"]["hedef"] - ort[k]["hedef"], 6) for k in ("rastgele", "hedefli")},
    }

def deney_bayraklari(kayitlar, temiz_esik, hedef_esik):
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar geçersiz")
    for esik in (temiz_esik, hedef_esik):
        if isinstance(esik, bool) or not isinstance(esik, (int, float)) or not math.isfinite(esik) or esik < 0 or esik > 1:
            raise ValueError("eşik geçersiz")
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"tur", "temiz_kayip", "hedef_kayip"}:
            raise ValueError("şema geçersiz")
        if kayit["tur"] not in ("rastgele", "hedefli"):
            raise ValueError("tür geçersiz")
        for alan in ("temiz_kayip", "hedef_kayip"):
            d = kayit[alan]
            if isinstance(d, bool) or not isinstance(d, (int, float)) or not math.isfinite(d) or d < 0 or d > 1:
                raise ValueError("kayıp geçersiz")
    if {x["tur"] for x in kayitlar} != {"rastgele", "hedefli"}:
        raise ValueError("iki tür gerekli")
    sonuc = {}
    for tur in ("rastgele", "hedefli"):
        grup = [x for x in kayitlar if x["tur"] == tur]
        temiz = sum(x["temiz_kayip"] for x in grup) / len(grup)
        hedef = sum(x["hedef_kayip"] for x in grup) / len(grup)
        sonuc[tur] = {"temiz_kayip": round(temiz, 6), "hedef_kayip": round(hedef, 6), "hedef_odakli": hedef >= hedef_esik and temiz <= temiz_esik}
    return sonuc

if ai_lab.CALISTIR:
    L.goster(etiket_gecis_profili, etki_karsilastirmasi, deney_bayraklari)
```

```hint
Önceki üç görevde yazdığın `etiket_gecis_profili`, `etki_karsilastirmasi` ve `deney_bayraklari` işlevlerini eksiksiz taşı; canlı deneyde üç ayrı `LogisticRegression` modeli eğitilerek hedefli zehirleme sinyali doğrulanır.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Rastgele etiket gürültüsü ile hedefli zehirleme farkı (35 sn).** "Rastgele etiket bozulması geçiş matrisine dağınık yayılır ve genel doğruluğu sınırlı aşındırır; hedefli etiket çevirme (`label-flipping`) ise belirli bir kaynak–hedef sınıf çiftine odaklanıp genel temiz doğruluğu korurken hedef sınıfı çökertir."
2. **Geçiş profili + iki ayrı kayıp ekseni (30 sn).** "Yalnız genel test doğruluğunu izleyen ekip hedefli zehirlemeyi kaçırır; `etiket_gecis_profili` yönlü sınıf kaymasını, `temiz_kayip` ve `hedef_kayip` ikilisi ise seçici hasarı görünür kılar."
3. **İnceleme bayrağının sınırı (30 sn).** "`hedef_odakli` bayrağı kasıtlı saldırının kesin hukuki ispatı değil, veri hattında belirli bir sınıf çiftinin sistematik bozulduğuna dair öncelikli denetim alarmıdır."
4. **Soru (25 sn).** "Etiketleme arayüzündeki sistematik bir insan hatası da yönlü sınıf geçişi üretebiliyorsa kasıtlı zehirlemeyi operasyonel hatadan ayırmak için hangi ek üstveriye bakarsın?"
:::
