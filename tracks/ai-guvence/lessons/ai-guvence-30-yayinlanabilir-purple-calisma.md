---
id: ai-guvence-30
title: Yayınlanabilir Purple Çalışma
summary: Saldırı ve savunma deneylerini ortak görev ve tekrarlarla karşılaştır; kanıt özetleri, yöntem ve yeniden üretim sınırlarıyla yayın paketi üret.
esleme: ai-guvence-26, ai-guvence-29, ai-guvence-33
timeout: 45
---

::: anlat Purple çalışma ortak ölçütlerle kurulur
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Eşleşmiş saldırı/savunma ölçümleri, tekrar ayarları ve doğrulanabilir yayın dosyaları | Görevler 1–3 görünür sentetik JSON kayıtları; son görev üç gerçek CPU eğitimi, FGSM, gerçek tahmin dosyası yazım kapısı ve hash doğrulamalı yerel ZIP | Kapsamı küçük sentetik bir yerel paket, hakemli yayın kabulü veya genel model güvenlik garantisi değildir |

> [!NOT]
> `veri/purple_kayitlari.json` ve `veri/yayin_esikleri.json` elle hazırlanmış sentetik öğretim dosyalarıdır. Örnek kanit_sha256 dizileri yalnız biçim temsilidir; gerçek dosya hash'i değildir. Setup her çalıştırmada geçici kopya oluşturur, kalıcılık yoktur. Başlangıçlar dosyayı gerçekten okur. Son gerçek deneyin `PAFTA_DATA/calisma/ai-guvence-30/ayar.json` kopyası ayrıdır ve kalıcıdır; varsa üzerine yazılmaz. Kontrol ayrı girdiler kullanır; paket yalnız yerel diske yazılır.

Yayınlanabilir bir purple çalışmada saldırı ve savunma kolları aynı görevleri ve aynı tekrar numaralarını kullanır. Yöntem, model ve çalışma kimliği bütün kayıtlarda ortaktır. Başarı ve güvenlik oranları, maliyet ve gecikme iki kol için de aynı tanımlarla hesaplanır. Her çalıştırmanın kanıt özeti saklanır.

Görevler 1–3 sentetik dosya kayıtlarını karşılaştırır; son görev PyTorch ile gerçekten model eğitir ve sentetik örnekler üzerinde gerçek autograd FGSM uygular. ART, Promptfoo veya MLflow çalıştırılmaz; model indirilmez. Amaç, gerçek araçların yerine geçmek değil, yayın paketinin doğrulanabilir veri sözleşmesini ve karşılaştırma mantığını öğrenmektir.
:::

::: anlat Yeniden üretim sonuçtan bağımsız bir yayın şartıdır
Tek bir başarılı deney yayın için yeterli değildir. Her görevde iki kolun da aynı tekrar kümesini içermesi, kanıt özetlerinin biçimsel olarak geçerli olması ve en az tekrar şartının sağlanması gerekir. Birleşik maliyet sınırı da açıkça raporlanır.

Savunmanın başarısı düşebilir, aynı kalabilir veya artabilir. Bu üç sonuç da çalışmanın bulgusudur; olumsuz sonuç yayın paketini tek başına engellemez. Yayın kararı yöntemsel tekrar ve maliyet şartlarına bağlıdır. Farklar `savunma - saldırı` olarak hesaplanır ve küçük sentetik örneklerden genel üstünlük iddiası çıkarılmaz.
:::

::: anlat Kayıt eşleştirmeden gerçek etki ve yayın paketine
Purple çalışmanın değeri saldırı ile savunmayı aynı soruya cevap verecek biçimde ölçmesidir. Bir kolda başka model, başka görev veya başka tekrar kümesi varsa görülen fark savunmanın etkisini temsil etmeyebilir. Bu dersin ilk üç görevi karşılaştırma kayıtlarının sözleşmesini öğretir; son adım gerçek yerel etki ve dosya paketi üretir. Yayın paketi hazır etiketi, bir derginin makaleyi kabul ettiği veya deneyin yeni bir bilimsel katkı sunduğu anlamına gelmez. Yöntem, yeniden üretim ve sonuç sınırlarının bir arada taşındığı yerel bir teslim durumudur.

İlk adımda `veri/purple_kayitlari.json` dosyasını okuyup ham satırları incele. Her görev ve tekrar numarası iki kolda da bulunur. Aynı satırı iki kimlikle çoğaltmak gerçek tekrar sayısını artırmaz; kol, görev ve tekrar birleşimi de benzersiz olmalıdır. Çalışma, yöntem ve model alanları ortak kalır. İlk görevdeki hash alanının yalnız altmış dört küçük onaltılık karakterden oluştuğu doğrulanır. Bu biçim denetimi dosyanın varlığını veya hash'in gerçek bir kaynaktan hesaplandığını göstermez. Görünür örnekteki hash dizileri sentetik yer tutuculardır; canlı adımda ise gerçek dosya byte'larından hash hesaplanır.

İkinci görev iki kolu kendi örnek sayısına göre özetler. Başarı ve güvenlik oranlarını aynı tanımlarla kullan; maliyet toplanırken gecikme ortalanır. Farkın yönü savunma eksi saldırıdır. Başarı artışı ile güvenlik artışı aynı şey değildir; bir görevi reddetmek zararlı çıktıyı azaltırken faydalı işi de engelleyebilir. Üçüncü görev `veri/yayin_esikleri.json` içindeki minimum tekrar ve birleşik maliyet sınırlarını denetler. Savunma sonucu kötü çıktığında kaydı silmek veya yayını otomatik engellemek seçici raporlama yaratır. Olumsuz sonuç da yöntemi açık bir çalışmanın bulgusu olabilir.

Canlı adım üç seed ile küçük modelleri gerçekten eğitir. Aynı bozulmuş FGSM örnekleri kapısız ve kapılı kollarda kullanılır. Buradaki savunma model ağırlıklarını değiştirmez; güven eşiği yalnız bir tahmin dosyasının yazılmasına izin verilip verilmeyeceğini belirler. Bu nedenle bütün örneklerde hesaplanan doğruluk iki kolda aynı kalabilir. Kapılı kolda kapsama düşerken izinli yanlış etki sayısı da düşebilir. Bunu modelin tahmin yeteneği iyileşti diye yorumlama. İzinli doğru sayısı bir adettir; raporlanan genel doğruluk veya kapsama oranıyla aynı alan değildir.

Politika fonksiyonunda eşitlik kabul edilir ve sonuç gerçekten bool olmalıdır. Güven eşiğinin altında kalan örneğe dosya yazılırsa sözlükte red görünmesi yeterli değildir; diskte yetkisiz etki oluşmuştur. Deney bu yüzden her örneğin dosya varlığını ölçer. Güvenli görünen bir yüksek güvenli yanlış tahmin yine kapıdan geçebilir. FGSM bu küçük sınıflandırıcıyı hedefler; bütün olası adaptif saldırıların veya sohbet modeli enjeksiyonlarının sınandığı iddia edilmez. Eşiği yükseltmenin reddetme maliyeti kapsama alanında görünmelidir.

Son aşamada ayarlar, ölçümler, model kayıtları, yeniden üretim bilgisi ve sınırlar yerel pakete yazılır. ZIP yeniden açılıp dosya hash'leriyle karşılaştırılır. Hash bütünlüğü içerik değişimini yakalamaya yarar; raporun doğru bilimsel yorum taşıdığını veya güvenilir bir yazar tarafından imzalandığını tek başına göstermez. Ham logitler ve eğitim izleri sentetik veride öğretim amacıyla saklanır. Saldırgan veya hatalı rapor seçilmiş seed'leri, eksik tekrarları veya reddedilen doğru işleri gizleyebilir. Savunma tüm koşuları, fayda kaybını ve olumsuz bulguları görünür tutmalıdır. Görev daha güvenli bir sonuç çıkmasını şart koşmaz; politika, ölçüm ve paketin doğru üretimini sınar.
:::

::: tahmin Purple farkını ve tekrar sayısını tahmin et
Üç çıktı satırını yaz:

```python
print(round(2 / 4 - 3 / 4, 6))
print(min(len({1, 2, 3}), len({1, 2, 3})))
print(round(4 * 0.01 + 4 * 0.02, 6))
```

???

```cikti
-0.25
3
0.12
```

İlk satır savunma eksi saldırı başarı farkını, ikinci satır eşleşen tekrar kümelerinin küçük olan boyutunu, üçüncü satır iki kolun birleşik maliyetini gösterir.
:::

::: gorev 1 · Sentetik purple deney kaydını doğrula
`purple_deney_dogrula(kayit)` işlevini yaz. Kayıt tam olarak `id`, `calisma`, `yontem`, `model`, `kol`, `gorev`, `tekrar`, `basarili`, `guvenli`, `maliyet`, `gecikme_ms`, `kanit_sha256` alanlarını taşır. Kimlik 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren stringdir. Çalışma, yöntem, model ve görev 1–64 karakterlik stringdir.

Kol yalnız `saldiri` veya `savunma`; tekrar bool olmayan 1–100 aralığında tam sayıdır. Başarılı ve güvenli alanları bool olur. Maliyet ve gecikme bool olmayan, sonlu, 0–1000000 aralığında `int` veya `float` olur. Kanıt özeti tam 64 küçük onaltılık karakterdir. Geçersiz veride `ValueError` yükselt. Bağımsız sözlük kopyası döndür ve girdiyi değiştirme.

```starter
def purple_deney_dogrula(kayit):
    # KUSURLU BAŞLANGIÇ KODU: hash biçimi, şema ve tekrar sınırlarını doğrulamadan kopyalıyor.
    return dict(kayit)

from ai_guvence_veri import json_yukle
for kayit in json_yukle("veri/purple_kayitlari.json"):
    print(purple_deney_dogrula(kayit))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-30")
```

```test
import copy
K = {"id": "deney-1", "calisma": "purple-sentetik", "yontem": "ortak-eval-v1", "model": "sentetik-model", "kol": "saldiri", "gorev": "g1", "tekrar": 1, "basarili": True, "guvenli": False, "maliyet": 0.01, "gecikme_ms": 100, "kanit_sha256": "a" * 64}
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K) != K or fn(K) is K or K != once:
            return False
        sinir = dict(K, id="a" * 64, calisma="c" * 64, yontem="y" * 64, model="m" * 64, kol="savunma", gorev="g" * 64, tekrar=100, basarili=False, guvenli=True, maliyet=1000000, gecikme_ms=1000000, kanit_sha256="0123456789abcdef" * 4)
        if fn(sinir) != sinir or fn(dict(K, maliyet=0, gecikme_ms=0))["maliyet"] != 0:
            return False
        if fn(dict(K, calisma="c", yontem="y", model="m", gorev="g"))["gorev"] != "g":
            return False
        for kayit in [
            None, [], dict(K, ek=1), dict(K, id=""), dict(K, id="a b"), dict(K, id="a" * 65), dict(K, id=None),
            dict(K, calisma=""), dict(K, calisma="c" * 65), dict(K, calisma=None), dict(K, yontem=""), dict(K, yontem=None),
            dict(K, model=""), dict(K, model=None), dict(K, gorev=""), dict(K, gorev="g" * 65), dict(K, gorev=None),
            dict(K, kol="diger"), dict(K, kol=None), dict(K, tekrar=0), dict(K, tekrar=101), dict(K, tekrar=1.5), dict(K, tekrar=True), dict(K, tekrar=None),
            dict(K, basarili=1), dict(K, basarili=None), dict(K, guvenli=0), dict(K, guvenli=None),
            dict(K, maliyet=-1), dict(K, maliyet=1000001), dict(K, maliyet=float("nan")), dict(K, maliyet=float("inf")), dict(K, maliyet=True), dict(K, maliyet=None),
            dict(K, gecikme_ms=-1), dict(K, gecikme_ms=1000001), dict(K, gecikme_ms=float("nan")), dict(K, gecikme_ms=float("inf")), dict(K, gecikme_ms=True), dict(K, gecikme_ms=None),
            dict(K, kanit_sha256="a" * 63), dict(K, kanit_sha256="a" * 65), dict(K, kanit_sha256="A" * 64), dict(K, kanit_sha256="g" * 64), dict(K, kanit_sha256=None),
        ]:
            try:
                fn(kayit)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(purple_deney_dogrula), "deney şeması, tekrar, ölçümler ve kanıt özeti korunmalı")
def m_tekrar(kayit):
    return purple_deney_dogrula(dict(kayit, tekrar=0))
def m_kanit(kayit):
    return purple_deney_dogrula(dict(kayit, kanit_sha256="A" * 64))
def m_kol(kayit):
    return purple_deney_dogrula(dict(kayit, kol="diger"))
def m_olcum(kayit):
    return purple_deney_dogrula(dict(kayit, gecikme_ms=-1))
for ad, mutant in [("tekrarı bozan", m_tekrar), ("kanıtı bozan", m_kanit), ("kolu bozan", m_kol), ("ölçümü bozan", m_olcum)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def purple_deney_dogrula(kayit):
    import math
    import re
    if not isinstance(kayit, dict):
        raise ValueError("kayıt sözlük olmalı")
    alanlar = {"id", "calisma", "yontem", "model", "kol", "gorev", "tekrar", "basarili", "guvenli", "maliyet", "gecikme_ms", "kanit_sha256"}
    if set(kayit) != alanlar:
        raise ValueError("kayıt şeması geçersiz")
    if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
        raise ValueError("kimlik geçersiz")
    for alan in ("calisma", "yontem", "model", "gorev"):
        if not isinstance(kayit[alan], str) or not 1 <= len(kayit[alan]) <= 64:
            raise ValueError("metin alanı geçersiz")
    if kayit["kol"] not in ("saldiri", "savunma"):
        raise ValueError("kol geçersiz")
    if not isinstance(kayit["tekrar"], int) or isinstance(kayit["tekrar"], bool) or not 1 <= kayit["tekrar"] <= 100:
        raise ValueError("tekrar geçersiz")
    if not isinstance(kayit["basarili"], bool) or not isinstance(kayit["guvenli"], bool):
        raise ValueError("ikilik alanlar bool olmalı")
    for alan in ("maliyet", "gecikme_ms"):
        deger = kayit[alan]
        if not isinstance(deger, (int, float)) or isinstance(deger, bool) or not math.isfinite(deger) or not 0 <= deger <= 1000000:
            raise ValueError("ölçüm geçersiz")
    if not isinstance(kayit["kanit_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", kayit["kanit_sha256"]):
        raise ValueError("kanıt özeti geçersiz")
    return dict(kayit)

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    for kayit in json_yukle("veri/purple_kayitlari.json"):
        print(purple_deney_dogrula(kayit))
```

```hint
Metin alanlarını ve iki sayısal ölçümü ortak döngülerle doğrula. Kanıt özetinde yalnız küçük harfli onaltılık karakterleri kabul et.
```
:::

::: gorev 2 · Saldırı ve savunma kollarını ortak ölçütlerle karşılaştır
`purple_karsilastirma_raporu(kayitlar)` işlevini yaz. Girdi ilk görevdeki kayıtların boş olmayan listesidir; kimlikler ve `(kol, gorev, tekrar)` üçlüleri yinelenemez. Bütün kayıtlarda çalışma, yöntem ve model aynı olmalıdır. İki kolun görev kümeleri eşit ve her görevdeki tekrar kümeleri birebir aynı olmalıdır. Geçersiz veride `ValueError` yükselt.

Her kol için `sayi`, `basari_orani`, `guvenlik_orani`, `toplam_maliyet`, `ortalama_gecikme_ms` hesapla. Oranları, maliyeti ve gecikmeyi 6 ondalığa yuvarla. `{"calisma":C,"yontem":Y,"model":M,"gorev_sayisi":G,"kollar":{"saldiri":S,"savunma":D},"farklar":F}` döndür.

Farklar `basari_orani`, `guvenlik_orani`, `toplam_maliyet`, `ortalama_gecikme_ms` anahtarlarını bu sırayla taşır; ham ölçümlerde savunma eksi saldırı değeridir ve 6 ondalığa yuvarlanır. Girdiyi değiştirme.

```starter
def purple_karsilastirma_raporu(kayitlar):
    import math
    import re
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    if not kayitlar:
        raise ValueError("kayıtlar boş olamaz")
    temiz = []
    for kayit in kayitlar:
        alanlar = {"id", "calisma", "yontem", "model", "kol", "gorev", "tekrar", "basarili", "guvenli", "maliyet", "gecikme_ms", "kanit_sha256"}
        if not isinstance(kayit, dict) or set(kayit) != alanlar:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
            raise ValueError("kimlik geçersiz")
        for alan in ("calisma", "yontem", "model", "gorev"):
            if not isinstance(kayit[alan], str) or not 1 <= len(kayit[alan]) <= 64:
                raise ValueError("metin alanı geçersiz")
        if kayit["kol"] not in ("saldiri", "savunma"):
            raise ValueError("kol geçersiz")
        if not isinstance(kayit["tekrar"], int) or isinstance(kayit["tekrar"], bool) or not 1 <= kayit["tekrar"] <= 100:
            raise ValueError("tekrar geçersiz")
        if not isinstance(kayit["basarili"], bool) or not isinstance(kayit["guvenli"], bool):
            raise ValueError("ikilik alanlar bool olmalı")
        for alan in ("maliyet", "gecikme_ms"):
            deger = kayit[alan]
            if not isinstance(deger, (int, float)) or isinstance(deger, bool) or not math.isfinite(deger) or not 0 <= deger <= 1000000:
                raise ValueError("ölçüm geçersiz")
        if not isinstance(kayit["kanit_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", kayit["kanit_sha256"]):
            raise ValueError("kanıt özeti geçersiz")
        temiz.append(dict(kayit))
    if len({x["id"] for x in temiz}) != len(temiz) or len({(x["kol"], x["gorev"], x["tekrar"]) for x in temiz}) != len(temiz):
        raise ValueError("kayıtlar benzersiz olmalı")
    for alan in ("calisma", "yontem", "model"):
        if len({x[alan] for x in temiz}) != 1:
            raise ValueError("çalışma meta verileri ortak olmalı")
    saldiri = [x for x in temiz if x["kol"] == "saldiri"]
    savunma = [x for x in temiz if x["kol"] == "savunma"]
    if {x["gorev"] for x in saldiri} != {x["gorev"] for x in savunma}:
        raise ValueError("görev kümeleri eşleşmeli")
    for gorev in {x["gorev"] for x in temiz}:
        if {x["tekrar"] for x in saldiri if x["gorev"] == gorev} != {x["tekrar"] for x in savunma if x["gorev"] == gorev}:
            raise ValueError("tekrar kümeleri eşleşmeli")
    kollar = {}
    ham = {}
    for ad, grup in (("saldiri", saldiri), ("savunma", savunma)):
        if not grup:
            raise ValueError("iki kol da gerekli")
        sayi = len(grup)
        ham[ad] = {
            "basari_orani": sum(x["basarili"] for x in grup) / sayi,
            "guvenlik_orani": sum(x["guvenli"] for x in grup) / sayi,
            "toplam_maliyet": sum(x["maliyet"] for x in grup),
            "ortalama_gecikme_ms": sum(x["gecikme_ms"] for x in grup) / sayi,
        }
        kollar[ad] = {"sayi": sayi}
        for alan, deger in ham[ad].items():
            kollar[ad][alan] = round(deger, 6)
    # KUSURLU BAŞLANGIÇ KODU: farkı saldırı eksi savunma olarak ters hesaplıyor.
    farklar = {}
    for alan in ("basari_orani", "guvenlik_orani", "toplam_maliyet", "ortalama_gecikme_ms"):
        farklar[alan] = round(ham["saldiri"][alan] - ham["savunma"][alan], 6)
    return {"calisma": temiz[0]["calisma"], "yontem": temiz[0]["yontem"], "model": temiz[0]["model"], "gorev_sayisi": len({x["gorev"] for x in temiz}), "kollar": kollar, "farklar": farklar}

from ai_guvence_veri import json_yukle
print(purple_karsilastirma_raporu(json_yukle("veri/purple_kayitlari.json")))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-30")
```

```test
import copy
import hashlib
def yap(id, kol, gorev, tekrar, basarili, guvenli, maliyet, gecikme):
    return {"id": id, "calisma": "purple-sentetik", "yontem": "ortak-eval-v1", "model": "sentetik-model", "kol": kol, "gorev": gorev, "tekrar": tekrar, "basarili": basarili, "guvenli": guvenli, "maliyet": maliyet, "gecikme_ms": gecikme, "kanit_sha256": hashlib.sha256(id.encode()).hexdigest()}
K = []
for gorev in ("g1", "g2"):
    for tekrar in (1, 2):
        K.append(yap(f"a-{gorev}-{tekrar}", "saldiri", gorev, tekrar, not (gorev == "g2" and tekrar == 2), tekrar == 1, 0.01, 100))
        K.append(yap(f"d-{gorev}-{tekrar}", "savunma", gorev, tekrar, tekrar == 1, True, 0.02, 150))
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        sonuc = fn(K)
        if K != once or sonuc["calisma"] != "purple-sentetik" or sonuc["yontem"] != "ortak-eval-v1" or sonuc["model"] != "sentetik-model" or sonuc["gorev_sayisi"] != 2:
            return False
        if sonuc["kollar"]["saldiri"] != {"sayi": 4, "basari_orani": 0.75, "guvenlik_orani": 0.5, "toplam_maliyet": 0.04, "ortalama_gecikme_ms": 100.0}:
            return False
        if sonuc["kollar"]["savunma"] != {"sayi": 4, "basari_orani": 0.5, "guvenlik_orani": 1.0, "toplam_maliyet": 0.08, "ortalama_gecikme_ms": 150.0}:
            return False
        if sonuc["farklar"] != {"basari_orani": -0.25, "guvenlik_orani": 0.5, "toplam_maliyet": 0.04, "ortalama_gecikme_ms": 50.0}:
            return False
        tek = fn(K[:2])
        if tek["gorev_sayisi"] != 1 or tek["kollar"]["saldiri"]["sayi"] != 1 or tek["farklar"]["basari_orani"] != 0.0:
            return False
        uc = fn(K + [yap("a-g3-1", "saldiri", "g3", 1, False, False, 0.1234567, 101), yap("d-g3-1", "savunma", "g3", 1, True, True, 0.02, 151)])
        if uc["kollar"]["saldiri"]["basari_orani"] != 0.6 or uc["kollar"]["savunma"]["basari_orani"] != 0.6 or uc["farklar"]["basari_orani"] != 0.0:
            return False
        if uc["kollar"]["saldiri"]["guvenlik_orani"] != 0.4 or uc["kollar"]["savunma"]["guvenlik_orani"] != 1.0 or uc["farklar"]["guvenlik_orani"] != 0.6:
            return False
        if uc["kollar"]["saldiri"]["toplam_maliyet"] != 0.163457 or uc["farklar"]["toplam_maliyet"] != -0.063457:
            return False
        tekrarlar = [dict(x, tekrar=x["tekrar"] + 2) for x in K]
        if fn(tekrarlar)["kollar"]["saldiri"]["sayi"] != 4:
            return False
        sinir = [dict(K[0], id="a" * 64, calisma="c" * 64, yontem="y" * 64, model="m" * 64, gorev="g" * 64, tekrar=100, maliyet=1000000, gecikme_ms=1000000), dict(K[1], calisma="c" * 64, yontem="y" * 64, model="m" * 64, gorev="g" * 64, tekrar=100, maliyet=1000000, gecikme_ms=1000000)]
        if fn(sinir)["gorev_sayisi"] != 1:
            return False
        kisa = [dict(K[0], calisma="c", yontem="y", model="m", gorev="g", maliyet=0, gecikme_ms=0), dict(K[1], calisma="c", yontem="y", model="m", gorev="g", maliyet=0, gecikme_ms=0)]
        if fn(kisa)["calisma"] != "c":
            return False
        bozuk_alanlar = [
            ("id", "a b"), ("id", "a" * 65), ("id", None), ("calisma", ""), ("calisma", None), ("yontem", ""), ("model", None), ("gorev", ""),
            ("kol", "diger"), ("tekrar", 0), ("tekrar", 101), ("tekrar", True), ("basarili", 1), ("guvenli", None),
            ("maliyet", -1), ("maliyet", 1000001), ("maliyet", float("nan")), ("maliyet", True), ("gecikme_ms", -1), ("gecikme_ms", 1000001), ("gecikme_ms", float("inf")), ("gecikme_ms", None),
            ("kanit_sha256", "A" * 64), ("kanit_sha256", "a" * 63),
        ]
        bozuklar = [[dict(K[0], **{a: d})] + K[1:] for a, d in bozuk_alanlar]
        bozuklar += [K[:-1], [K[0], K[0]], [K[0], dict(K[1], id=K[0]["id"])], [K[0], dict(K[1], tekrar=2)], [dict(K[0], model="baska")] + K[1:], [dict(K[0], yontem="baska")] + K[1:], [dict(K[0], calisma="baska")] + K[1:]]
        bozuklar += [[dict(K[0], calisma="c" * 65), dict(K[1], calisma="c" * 65)], [dict(K[0], gorev="g" * 65), dict(K[1], gorev="g" * 65)], [dict(K[0], tekrar=101), dict(K[1], tekrar=101)]]
        bozuklar += [[dict(K[0], ek=1)] + K[1:], [dict(x, calisma="") for x in K], [dict(K[0], kol="diger", id="x1")] + K, [dict(x, tekrar=0) for x in K[:2]], [dict(x, tekrar=1.5) for x in K[:2]], [dict(K[0], kanit_sha256=None)] + K[1:], [dict(K[0], id="kopya")] + K]
        for kayitlar in [None, {}, tuple(K), [], [None]] + bozuklar:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(purple_karsilastirma_raporu), "ortak görevler, tekrarlar ve savunma eksi saldırı farkları korunmalı")
def m_basari(kayitlar):
    return purple_karsilastirma_raporu([dict(x, basarili=True) for x in kayitlar])
def m_guvenli(kayitlar):
    return purple_karsilastirma_raporu([dict(x, guvenli=True) for x in kayitlar])
def m_tekrar(kayitlar):
    return purple_karsilastirma_raporu([dict(x, tekrar=2) for x in kayitlar])
def m_maliyet(kayitlar):
    return purple_karsilastirma_raporu([dict(x, maliyet=0) for x in kayitlar])
for ad, mutant in [("başarıyı silen", m_basari), ("güvenliği silen", m_guvenli), ("tekrarları bozan", m_tekrar), ("maliyeti silen", m_maliyet)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def purple_karsilastirma_raporu(kayitlar):
    import math
    import re
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    if not kayitlar:
        raise ValueError("kayıtlar boş olamaz")
    temiz = []
    for kayit in kayitlar:
        alanlar = {"id", "calisma", "yontem", "model", "kol", "gorev", "tekrar", "basarili", "guvenli", "maliyet", "gecikme_ms", "kanit_sha256"}
        if not isinstance(kayit, dict) or set(kayit) != alanlar:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
            raise ValueError("kimlik geçersiz")
        for alan in ("calisma", "yontem", "model", "gorev"):
            if not isinstance(kayit[alan], str) or not 1 <= len(kayit[alan]) <= 64:
                raise ValueError("metin alanı geçersiz")
        if kayit["kol"] not in ("saldiri", "savunma"):
            raise ValueError("kol geçersiz")
        if not isinstance(kayit["tekrar"], int) or isinstance(kayit["tekrar"], bool) or not 1 <= kayit["tekrar"] <= 100:
            raise ValueError("tekrar geçersiz")
        if not isinstance(kayit["basarili"], bool) or not isinstance(kayit["guvenli"], bool):
            raise ValueError("ikilik alanlar bool olmalı")
        for alan in ("maliyet", "gecikme_ms"):
            deger = kayit[alan]
            if not isinstance(deger, (int, float)) or isinstance(deger, bool) or not math.isfinite(deger) or not 0 <= deger <= 1000000:
                raise ValueError("ölçüm geçersiz")
        if not isinstance(kayit["kanit_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", kayit["kanit_sha256"]):
            raise ValueError("kanıt özeti geçersiz")
        temiz.append(dict(kayit))
    if len({x["id"] for x in temiz}) != len(temiz) or len({(x["kol"], x["gorev"], x["tekrar"]) for x in temiz}) != len(temiz):
        raise ValueError("kayıtlar benzersiz olmalı")
    for alan in ("calisma", "yontem", "model"):
        if len({x[alan] for x in temiz}) != 1:
            raise ValueError("çalışma meta verileri ortak olmalı")
    saldiri = [x for x in temiz if x["kol"] == "saldiri"]
    savunma = [x for x in temiz if x["kol"] == "savunma"]
    if {x["gorev"] for x in saldiri} != {x["gorev"] for x in savunma}:
        raise ValueError("görev kümeleri eşleşmeli")
    for gorev in {x["gorev"] for x in temiz}:
        if {x["tekrar"] for x in saldiri if x["gorev"] == gorev} != {x["tekrar"] for x in savunma if x["gorev"] == gorev}:
            raise ValueError("tekrar kümeleri eşleşmeli")
    kollar = {}
    ham = {}
    for ad, grup in (("saldiri", saldiri), ("savunma", savunma)):
        if not grup:
            raise ValueError("iki kol da gerekli")
        sayi = len(grup)
        ham[ad] = {
            "basari_orani": sum(x["basarili"] for x in grup) / sayi,
            "guvenlik_orani": sum(x["guvenli"] for x in grup) / sayi,
            "toplam_maliyet": sum(x["maliyet"] for x in grup),
            "ortalama_gecikme_ms": sum(x["gecikme_ms"] for x in grup) / sayi,
        }
        kollar[ad] = {"sayi": sayi}
        for alan, deger in ham[ad].items():
            kollar[ad][alan] = round(deger, 6)
    farklar = {}
    for alan in ("basari_orani", "guvenlik_orani", "toplam_maliyet", "ortalama_gecikme_ms"):
        farklar[alan] = round(ham["savunma"][alan] - ham["saldiri"][alan], 6)
    return {"calisma": temiz[0]["calisma"], "yontem": temiz[0]["yontem"], "model": temiz[0]["model"], "gorev_sayisi": len({x["gorev"] for x in temiz}), "kollar": kollar, "farklar": farklar}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    print(purple_karsilastirma_raporu(json_yukle("veri/purple_kayitlari.json")))
```

```hint
Önce üçlü benzersizliği, ortak meta verileri ve görev bazında tekrar kümelerini denetle. Raporlanan değerleri yuvarla; farkları ham toplu ölçümlerden hesapla.
```
:::

::: gorev 3 · Tekrar ve maliyet şartıyla yayın paketi kararı üret
`purple_yayin_paketi(kayitlar, min_tekrar, max_birlesik_maliyet)` işlevini yaz. Kayıtlar ikinci görevdeki kurallara uyar. `min_tekrar` bool olmayan 1–100 aralığında tam sayı; maliyet sınırı bool olmayan, sonlu, 0–2000000 aralığında `int` veya `float` olmalıdır. Geçersiz veride `ValueError` yükselt.

İkinci görevdeki raporu `rapor` alanında döndür. `minimum_tekrar`, görev ve kol başına düşen kayıt sayılarının en küçüğüdür. Bu sayı `min_tekrar` altındaysa `tekrar_yetersiz`; iki kolun ham birleşik maliyeti sınır üstündeyse `maliyet_asimi` alarmı ekle. Tam eşikte alarm yoktur.

Başarı farkı pozitifse sonuç `savunma_basari_artisi`, negatifse `savunma_basari_dususu`, sıfırsa `fark_yok` olur. Alarm yoksa karar `yayin_paketi_hazir`, varsa `calisma_gerekli` olur; sonuç türü kararı değiştirmez. `{"rapor":R,"minimum_tekrar":N,"alarmlar":A,"sonuc":S,"karar":K}` döndür ve girdiyi değiştirme.

```starter
def purple_yayin_paketi(kayitlar, min_tekrar, max_birlesik_maliyet):
    import math
    import re
    if not isinstance(min_tekrar, int) or isinstance(min_tekrar, bool) or not 1 <= min_tekrar <= 100:
        raise ValueError("minimum tekrar geçersiz")
    if not isinstance(max_birlesik_maliyet, (int, float)) or isinstance(max_birlesik_maliyet, bool) or not math.isfinite(max_birlesik_maliyet) or not 0 <= max_birlesik_maliyet <= 2000000:
        raise ValueError("maliyet sınırı geçersiz")
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    if not kayitlar:
        raise ValueError("kayıtlar boş olamaz")
    temiz = []
    for kayit in kayitlar:
        alanlar = {"id", "calisma", "yontem", "model", "kol", "gorev", "tekrar", "basarili", "guvenli", "maliyet", "gecikme_ms", "kanit_sha256"}
        if not isinstance(kayit, dict) or set(kayit) != alanlar:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
            raise ValueError("kimlik geçersiz")
        for alan in ("calisma", "yontem", "model", "gorev"):
            if not isinstance(kayit[alan], str) or not 1 <= len(kayit[alan]) <= 64:
                raise ValueError("metin alanı geçersiz")
        if kayit["kol"] not in ("saldiri", "savunma"):
            raise ValueError("kol geçersiz")
        if not isinstance(kayit["tekrar"], int) or isinstance(kayit["tekrar"], bool) or not 1 <= kayit["tekrar"] <= 100:
            raise ValueError("tekrar geçersiz")
        if not isinstance(kayit["basarili"], bool) or not isinstance(kayit["guvenli"], bool):
            raise ValueError("ikilik alanlar bool olmalı")
        for alan in ("maliyet", "gecikme_ms"):
            deger = kayit[alan]
            if not isinstance(deger, (int, float)) or isinstance(deger, bool) or not math.isfinite(deger) or not 0 <= deger <= 1000000:
                raise ValueError("ölçüm geçersiz")
        if not isinstance(kayit["kanit_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", kayit["kanit_sha256"]):
            raise ValueError("kanıt özeti geçersiz")
        temiz.append(dict(kayit))
    if len({x["id"] for x in temiz}) != len(temiz) or len({(x["kol"], x["gorev"], x["tekrar"]) for x in temiz}) != len(temiz):
        raise ValueError("kayıtlar benzersiz olmalı")
    for alan in ("calisma", "yontem", "model"):
        if len({x[alan] for x in temiz}) != 1:
            raise ValueError("çalışma meta verileri ortak olmalı")
    saldiri = [x for x in temiz if x["kol"] == "saldiri"]
    savunma = [x for x in temiz if x["kol"] == "savunma"]
    if {x["gorev"] for x in saldiri} != {x["gorev"] for x in savunma}:
        raise ValueError("görev kümeleri eşleşmeli")
    sayimlar = []
    for gorev in {x["gorev"] for x in temiz}:
        saldiri_tekrar = {x["tekrar"] for x in saldiri if x["gorev"] == gorev}
        savunma_tekrar = {x["tekrar"] for x in savunma if x["gorev"] == gorev}
        if saldiri_tekrar != savunma_tekrar:
            raise ValueError("tekrar kümeleri eşleşmeli")
        sayimlar += [len(saldiri_tekrar), len(savunma_tekrar)]
    if not saldiri:
        raise ValueError("saldırı kolu gerekli")
    if not savunma:
        raise ValueError("savunma kolu gerekli")
    kollar = {}
    ham = {}
    for ad, grup in (("saldiri", saldiri), ("savunma", savunma)):
        sayi = len(grup)
        ham[ad] = {
            "basari_orani": sum(x["basarili"] for x in grup) / sayi,
            "guvenlik_orani": sum(x["guvenli"] for x in grup) / sayi,
            "toplam_maliyet": sum(x["maliyet"] for x in grup),
            "ortalama_gecikme_ms": sum(x["gecikme_ms"] for x in grup) / sayi,
        }
        kollar[ad] = {"sayi": sayi}
        for alan, deger in ham[ad].items():
            kollar[ad][alan] = round(deger, 6)
    farklar = {}
    for alan in ("basari_orani", "guvenlik_orani", "toplam_maliyet", "ortalama_gecikme_ms"):
        farklar[alan] = round(ham["savunma"][alan] - ham["saldiri"][alan], 6)
    rapor = {"calisma": temiz[0]["calisma"], "yontem": temiz[0]["yontem"], "model": temiz[0]["model"], "gorev_sayisi": len({x["gorev"] for x in temiz}), "kollar": kollar, "farklar": farklar}
    minimum = min(sayimlar)
    # KUSURLU BAŞLANGIÇ KODU: tam minimum tekrar sayısını yetersiz kabul ediyor.
    alarmlar = []
    if minimum <= min_tekrar:
        alarmlar.append("tekrar_yetersiz")
    if ham["saldiri"]["toplam_maliyet"] + ham["savunma"]["toplam_maliyet"] > max_birlesik_maliyet:
        alarmlar.append("maliyet_asimi")
    fark = ham["savunma"]["basari_orani"] - ham["saldiri"]["basari_orani"]
    if fark > 0:
        sonuc = "savunma_basari_artisi"
    elif fark < 0:
        sonuc = "savunma_basari_dususu"
    else:
        sonuc = "fark_yok"
    return {"rapor": rapor, "minimum_tekrar": minimum, "alarmlar": alarmlar, "sonuc": sonuc, "karar": "calisma_gerekli" if alarmlar else "yayin_paketi_hazir"}

from ai_guvence_veri import json_yukle
esikler = json_yukle("veri/yayin_esikleri.json")
print(purple_yayin_paketi(json_yukle("veri/purple_kayitlari.json"), **esikler))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-30")
```

```test
import copy
import hashlib
def yap(id, kol, gorev, tekrar, basarili, guvenli, maliyet, gecikme):
    return {"id": id, "calisma": "purple-sentetik", "yontem": "ortak-eval-v1", "model": "sentetik-model", "kol": kol, "gorev": gorev, "tekrar": tekrar, "basarili": basarili, "guvenli": guvenli, "maliyet": maliyet, "gecikme_ms": gecikme, "kanit_sha256": hashlib.sha256(id.encode()).hexdigest()}
K = []
for gorev in ("g1", "g2"):
    for tekrar in (1, 2):
        K.append(yap(f"a-{gorev}-{tekrar}", "saldiri", gorev, tekrar, not (gorev == "g2" and tekrar == 2), tekrar == 1, 0.01, 100))
        K.append(yap(f"d-{gorev}-{tekrar}", "savunma", gorev, tekrar, tekrar == 1, True, 0.02, 150))
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        sonuc = fn(K, 2, 0.12)
        if K != once or sonuc["minimum_tekrar"] != 2 or sonuc["alarmlar"] != [] or sonuc["sonuc"] != "savunma_basari_dususu" or sonuc["karar"] != "yayin_paketi_hazir":
            return False
        if sonuc["rapor"]["farklar"] != {"basari_orani": -0.25, "guvenlik_orani": 0.5, "toplam_maliyet": 0.04, "ortalama_gecikme_ms": 50.0}:
            return False
        if fn(K, 3, 0.12)["alarmlar"] != ["tekrar_yetersiz"] or fn(K, 3, 0.119999)["alarmlar"] != ["tekrar_yetersiz", "maliyet_asimi"] or fn(K, 2, 0.119999)["karar"] != "calisma_gerekli":
            return False
        if fn(K, 1, 0.12)["karar"] != "yayin_paketi_hazir" or fn(K, 100, 2000000)["karar"] != "calisma_gerekli" or fn(K, 2, 0)["alarmlar"] != ["maliyet_asimi"]:
            return False
        artis = [dict(x, basarili=True) if x["kol"] == "savunma" else dict(x, basarili=False) for x in K]
        if fn(artis, 2, 0.12)["sonuc"] != "savunma_basari_artisi" or fn(artis, 2, 0.12)["karar"] != "yayin_paketi_hazir":
            return False
        esit = fn(K[:2], 1, 0.03)
        if esit["sonuc"] != "fark_yok" or esit["karar"] != "yayin_paketi_hazir":
            return False
        uc = fn(K + [yap("a-g3-1", "saldiri", "g3", 1, False, False, 0.01, 100), yap("d-g3-1", "savunma", "g3", 1, True, True, 0.02, 150)], 1, 0.15)
        if uc["minimum_tekrar"] != 1 or uc["rapor"]["gorev_sayisi"] != 3 or uc["rapor"]["kollar"]["saldiri"]["basari_orani"] != 0.6:
            return False
        ondalik = fn(K + [yap("a-g3-1", "saldiri", "g3", 1, False, False, 0.1234567, 100), yap("d-g3-1", "savunma", "g3", 1, True, True, 0.02, 150), yap("a-g3-2", "saldiri", "g3", 2, True, True, 0.01, 100), yap("d-g3-2", "savunma", "g3", 2, False, True, 0.02, 150)], 2, 0.3)
        if ondalik["rapor"]["kollar"]["saldiri"]["basari_orani"] != 0.666667 or ondalik["rapor"]["kollar"]["savunma"]["basari_orani"] != 0.5 or ondalik["rapor"]["farklar"]["basari_orani"] != -0.166667:
            return False
        if ondalik["rapor"]["kollar"]["saldiri"]["toplam_maliyet"] != 0.173457 or ondalik["rapor"]["farklar"]["toplam_maliyet"] != -0.053457:
            return False
        sinir = [dict(K[0], id="a" * 64, calisma="c" * 64, yontem="y" * 64, model="m" * 64, gorev="g" * 64, tekrar=100, maliyet=1000000), dict(K[1], calisma="c" * 64, yontem="y" * 64, model="m" * 64, gorev="g" * 64, tekrar=100, maliyet=1000000)]
        if fn(sinir, 100, 2000000)["alarmlar"] != ["tekrar_yetersiz"]:
            return False
        kisa = [dict(K[0], calisma="c", yontem="y", model="m", gorev="g", maliyet=0, gecikme_ms=0), dict(K[1], calisma="c", yontem="y", model="m", gorev="g", maliyet=0, gecikme_ms=0)]
        if fn(kisa, 1, 0)["rapor"]["calisma"] != "c":
            return False
        bozuk_alanlar = [
            ("id", "a b"), ("id", "a" * 65), ("id", None), ("calisma", ""), ("calisma", None), ("yontem", None), ("model", ""), ("gorev", None), ("kol", "diger"),
            ("tekrar", 0), ("tekrar", 101), ("tekrar", 1.5), ("tekrar", True), ("tekrar", None), ("basarili", 1), ("guvenli", None),
            ("maliyet", -1), ("maliyet", 1000001), ("maliyet", float("nan")), ("maliyet", True), ("maliyet", None), ("gecikme_ms", -1), ("gecikme_ms", 1000001), ("gecikme_ms", float("nan")), ("gecikme_ms", True), ("gecikme_ms", None), ("kanit_sha256", "A" * 64),
        ]
        bozuklar = [[dict(K[0], **{a: d})] + K[1:] for a, d in bozuk_alanlar]
        bozuklar += [[K[0], dict(K[1], id=K[0]["id"])], [K[0], dict(K[1], tekrar=2)], [dict(K[0], model="baska")] + K[1:], [dict(K[0], calisma="c" * 65), dict(K[1], calisma="c" * 65)], [dict(K[0], tekrar=101), dict(K[1], tekrar=101)]]
        bozuklar += [[dict(K[0], ek=1)] + K[1:], [dict(x, calisma="") for x in K], [dict(K[0], kol="diger", id="x1")] + K, [dict(x, tekrar=0) for x in K[:2]], [dict(K[0], kanit_sha256=None)] + K[1:], [dict(K[0], id="kopya")] + K]
        for args in [(x, 2, 0.12) for x in [None, {}, tuple(K), [], [None], [dict(K[0], ek=1)], K[:-1]] + bozuklar] + [
            (K, 0, 0.12), (K, 101, 0.12), (K, 1.5, 0.12), (K, True, 0.12), (K, None, 0.12),
            (K, 2, -1), (K, 2, 2000001), (K, 2, float("nan")), (K, 2, float("inf")), (K, 2, True), (K, 2, None),
        ]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(purple_yayin_paketi), "tekrar, maliyet, sonuç ve yayın kararı korunmalı")
def m_tekrar(kayitlar, a, b):
    return purple_yayin_paketi(kayitlar, 3, b)
def m_maliyet(kayitlar, a, b):
    return purple_yayin_paketi([dict(x, maliyet=0) for x in kayitlar], a, b)
def m_basari(kayitlar, a, b):
    return purple_yayin_paketi([dict(x, basarili=True) for x in kayitlar], a, b)
def m_eslesme(kayitlar, a, b):
    return purple_yayin_paketi([dict(x, tekrar=2) for x in kayitlar], a, b)
for ad, mutant in [("tekrar şartını değiştiren", m_tekrar), ("maliyeti silen", m_maliyet), ("sonucu silen", m_basari), ("eşleşmeyi bozan", m_eslesme)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def purple_yayin_paketi(kayitlar, min_tekrar, max_birlesik_maliyet):
    import math
    import re
    if not isinstance(min_tekrar, int) or isinstance(min_tekrar, bool) or not 1 <= min_tekrar <= 100:
        raise ValueError("minimum tekrar geçersiz")
    if not isinstance(max_birlesik_maliyet, (int, float)) or isinstance(max_birlesik_maliyet, bool) or not math.isfinite(max_birlesik_maliyet) or not 0 <= max_birlesik_maliyet <= 2000000:
        raise ValueError("maliyet sınırı geçersiz")
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    if not kayitlar:
        raise ValueError("kayıtlar boş olamaz")
    temiz = []
    for kayit in kayitlar:
        alanlar = {"id", "calisma", "yontem", "model", "kol", "gorev", "tekrar", "basarili", "guvenli", "maliyet", "gecikme_ms", "kanit_sha256"}
        if not isinstance(kayit, dict) or set(kayit) != alanlar:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
            raise ValueError("kimlik geçersiz")
        for alan in ("calisma", "yontem", "model", "gorev"):
            if not isinstance(kayit[alan], str) or not 1 <= len(kayit[alan]) <= 64:
                raise ValueError("metin alanı geçersiz")
        if kayit["kol"] not in ("saldiri", "savunma"):
            raise ValueError("kol geçersiz")
        if not isinstance(kayit["tekrar"], int) or isinstance(kayit["tekrar"], bool) or not 1 <= kayit["tekrar"] <= 100:
            raise ValueError("tekrar geçersiz")
        if not isinstance(kayit["basarili"], bool) or not isinstance(kayit["guvenli"], bool):
            raise ValueError("ikilik alanlar bool olmalı")
        for alan in ("maliyet", "gecikme_ms"):
            deger = kayit[alan]
            if not isinstance(deger, (int, float)) or isinstance(deger, bool) or not math.isfinite(deger) or not 0 <= deger <= 1000000:
                raise ValueError("ölçüm geçersiz")
        if not isinstance(kayit["kanit_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", kayit["kanit_sha256"]):
            raise ValueError("kanıt özeti geçersiz")
        temiz.append(dict(kayit))
    if len({x["id"] for x in temiz}) != len(temiz) or len({(x["kol"], x["gorev"], x["tekrar"]) for x in temiz}) != len(temiz):
        raise ValueError("kayıtlar benzersiz olmalı")
    for alan in ("calisma", "yontem", "model"):
        if len({x[alan] for x in temiz}) != 1:
            raise ValueError("çalışma meta verileri ortak olmalı")
    saldiri = [x for x in temiz if x["kol"] == "saldiri"]
    savunma = [x for x in temiz if x["kol"] == "savunma"]
    if {x["gorev"] for x in saldiri} != {x["gorev"] for x in savunma}:
        raise ValueError("görev kümeleri eşleşmeli")
    sayimlar = []
    for gorev in {x["gorev"] for x in temiz}:
        saldiri_tekrar = {x["tekrar"] for x in saldiri if x["gorev"] == gorev}
        savunma_tekrar = {x["tekrar"] for x in savunma if x["gorev"] == gorev}
        if saldiri_tekrar != savunma_tekrar:
            raise ValueError("tekrar kümeleri eşleşmeli")
        sayimlar += [len(saldiri_tekrar), len(savunma_tekrar)]
    if not saldiri:
        raise ValueError("saldırı kolu gerekli")
    if not savunma:
        raise ValueError("savunma kolu gerekli")
    kollar = {}
    ham = {}
    for ad, grup in (("saldiri", saldiri), ("savunma", savunma)):
        sayi = len(grup)
        ham[ad] = {
            "basari_orani": sum(x["basarili"] for x in grup) / sayi,
            "guvenlik_orani": sum(x["guvenli"] for x in grup) / sayi,
            "toplam_maliyet": sum(x["maliyet"] for x in grup),
            "ortalama_gecikme_ms": sum(x["gecikme_ms"] for x in grup) / sayi,
        }
        kollar[ad] = {"sayi": sayi}
        for alan, deger in ham[ad].items():
            kollar[ad][alan] = round(deger, 6)
    farklar = {}
    for alan in ("basari_orani", "guvenlik_orani", "toplam_maliyet", "ortalama_gecikme_ms"):
        farklar[alan] = round(ham["savunma"][alan] - ham["saldiri"][alan], 6)
    rapor = {"calisma": temiz[0]["calisma"], "yontem": temiz[0]["yontem"], "model": temiz[0]["model"], "gorev_sayisi": len({x["gorev"] for x in temiz}), "kollar": kollar, "farklar": farklar}
    minimum = min(sayimlar)
    alarmlar = []
    if minimum < min_tekrar:
        alarmlar.append("tekrar_yetersiz")
    if ham["saldiri"]["toplam_maliyet"] + ham["savunma"]["toplam_maliyet"] > max_birlesik_maliyet:
        alarmlar.append("maliyet_asimi")
    fark = ham["savunma"]["basari_orani"] - ham["saldiri"]["basari_orani"]
    if fark > 0:
        sonuc = "savunma_basari_artisi"
    elif fark < 0:
        sonuc = "savunma_basari_dususu"
    else:
        sonuc = "fark_yok"
    return {"rapor": rapor, "minimum_tekrar": minimum, "alarmlar": alarmlar, "sonuc": sonuc, "karar": "calisma_gerekli" if alarmlar else "yayin_paketi_hazir"}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    esikler = json_yukle("veri/yayin_esikleri.json")
    print(purple_yayin_paketi(json_yukle("veri/purple_kayitlari.json"), **esikler))
```

```hint
Minimum tekrarı her görevdeki iki kolun kayıt sayılarından bul. Birleşik maliyeti ham toplamlardan hesapla; sonuç sınıfını yayın alarmı olarak kullanma.
```
:::


::: anlat Gerçek deney · Yayınlanabilir yerel purple paketi
Önce görünür sentetik [ayar dosyasını](/data/ai-guvence-30-deney.txt) incele: /data/ai-guvence-30-deney.txt. Bu bir sunucu kaydı değildir. Çalıştır ilk kullanımda ayrı kalıcı kopya oluşturur ve gerçek yol/içeriğini gösterir. Yerleşik dosya editörü yoktur; yolu yerel editörde aç, seed veya eps değiştir ve yeniden Çalıştır. Kopya varsa üzerine yazılmaz. Göreli PAFTA_DATA proje köküne göre çözülür; geçici koşucu klasörüne göre değil. Kontrol ayrı görülmemiş ayarı kullanır; öğrenci dosyasını değiştirmek beklenen cevabı değiştirmez.

yayin_politikasi(confidence,threshold): güven>=eşik olduğunda bool True. İzin gerçek tahmin dosyasının yazılmasını belirler; red durumunda dosya yazılmaz. purple_gercek_ozet(rows): saldiri ve savunma anahtarları altında kol başına n,dogruluk,kapsama,zararli_etki,izinli_dogru döndür. Doğruluk bütün örneklerde, kapsama izin/n; zararlı etki izinli yanlış sayısıdır. Oranlar 6 basamak. Üç gerçek eğitim, aynı FGSM örneklerinde kapısız/kapılı eşleşme, reddetme maliyeti ve hash doğrulamalı ZIP üretilir. Bir kolun daha güvenli çıkması kabul koşulu değildir. Paket yalnız yerel yazılır; genel güvenlik/yayın garantisi yoktur.

CPU .ai-venv torch ile gerçek Adam/autograd eğitimi, ağırlık hash'i, ham logitler ve ölçüm kanıtı yazılır. Model indirilmez, GPU kullanılmaz. Testte geçici ağırlıklar temizlenir; eğitim/logit/hash kanıtta korunur. Çalıştır çıktıları kalıcı öğrenci klasöründe kalır. Eski adımlar yukarıda fixture olarak korunmuştur; bu ek adım canlı deneydir.

Kaynaklar: [NIST AI 100-2 E2023 — Adversarial Machine Learning](https://csrc.nist.gov/pubs/ai/100/2/e2023/final), [MITRE ATLAS — Adversarial Threat Landscape for Artificial-Intelligence Systems](https://atlas.mitre.org/).
:::

::: gorev Gerçek deney · Yayınlanabilir yerel purple paketi
yayin_politikasi(confidence,threshold): güven>=eşik olduğunda bool True. İzin gerçek tahmin dosyasının yazılmasını belirler; red durumunda dosya yazılmaz. purple_gercek_ozet(rows): saldiri ve savunma anahtarları altında kol başına n,dogruluk,kapsama,zararli_etki,izinli_dogru döndür. Doğruluk bütün örneklerde, kapsama izin/n; zararlı etki izinli yanlış sayısıdır. Oranlar 6 basamak. Üç gerçek eğitim, aynı FGSM örneklerinde kapısız/kapılı eşleşme, reddetme maliyeti ve hash doğrulamalı ZIP üretilir. Bir kolun daha güvenli çıkması kabul koşulu değildir. Paket yalnız yerel yazılır; genel güvenlik/yayın garantisi yoktur.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 120
```

```starter
def yayin_politikasi(*args):
    return None

def purple_gercek_ozet(*args):
    return None

import ai_lab
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_30 as deney
    deney.goster(yayin_politikasi,purple_gercek_ozet)
```

```test
import ai_lab
import ast
YASAK = ("attack_ref", "policy_ref", "report_ref", "kanit_yaz")
sorunlar = ai_lab.kod_denetimi(src, yasak=YASAK)
for dugum in ast.walk(ast.parse(src)):
    if isinstance(dugum, ast.ImportFrom):
        if any(ad.name in YASAK or ad.name == "*" for ad in dugum.names):
            sorunlar.append("referans veya kanıt yazıcısı içe aktarılamaz")
if sorunlar:
    ok(False, "Kendi ölçüm işlevlerini yaz: " + "; ".join(sorunlar))
    stop()
import tempfile
from pathlib import Path
from sandbox import ai_gercek_ai_guvence_30 as deney
# Test configuration is separate from the persistent editable student copy.
ok(yayin_politikasi(0.8, 0.8) is True and yayin_politikasi(0.81, 0.8) is True and yayin_politikasi(0.79, 0.8) is False, 'yayin_politikasi >= eşik sınırını bool olarak uygulamalı')
_po = purple_gercek_ozet([
    {'kol': 'saldiri', 'dogru': True, 'izin': True},
    {'kol': 'saldiri', 'dogru': False, 'izin': True},
    {'kol': 'saldiri', 'dogru': False, 'izin': False},
    {'kol': 'savunma', 'dogru': True, 'izin': True},
    {'kol': 'savunma', 'dogru': True, 'izin': False},
    {'kol': 'savunma', 'dogru': False, 'izin': False},
])
ok(_po == {
    'saldiri': {'n': 3, 'dogruluk': 0.333333, 'kapsama': 0.666667, 'zararli_etki': 1, 'izinli_dogru': 1},
    'savunma': {'n': 3, 'dogruluk': 0.666667, 'kapsama': 0.333333, 'zararli_etki': 0, 'izinli_dogru': 1},
}, 'purple_gercek_ozet 6 basamak doğruluk/kapsama ve zararlı etki sayımını doğru üretmeli')
with tempfile.TemporaryDirectory(prefix="pafta-guvence-30-") as tmp:
    config=Path(tmp)/"ayar.json"
    config.write_text('{"seed":943,"eps":0.23}',encoding="utf-8")
    r=deney.deney(yayin_politikasi,purple_gercek_ozet,config,Path(tmp)/"deney")
    for name,value in r["kontroller"].items():ok(value,"GERCEK: "+name)
    ai_lab.kanit_yaz("guvence-30",dict(r,kabul=all(r["kontroller"].values())))
```

```solution
def yayin_politikasi(confidence,threshold):
    return confidence>=threshold

def purple_gercek_ozet(rows):
    out={}
    for arm in ('saldiri','savunma'):
        rs=[r for r in rows if r['kol']==arm];n=len(rs)
        out[arm]=dict(n=n,dogruluk=round(sum(r['dogru'] for r in rs)/n,6),kapsama=round(sum(r['izin'] for r in rs)/n,6),zararli_etki=sum(r['izin'] and not r['dogru'] for r in rs),izinli_dogru=sum(r['izin'] and r['dogru'] for r in rs))
    return out

import ai_lab
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_30 as deney
    deney.goster(yayin_politikasi,purple_gercek_ozet)
```

```hint
Fonksiyonların etkisini gerçek model/araç akışında koru. Sabit oran veya hep izin/red kullanma. Bağımlılık yoksa gerçek kabul verilmez. Veri sentetiktir, eğitim ve dosya etkileri gerçektir.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Red ve Blue'yu aynı protokolde buluşturmak (`Purple` çalışma) (35 sn).** "Saldırı ekibi yalnız kırılma oranını, savunma ekibi yalnız temiz doğruluğu raporladığında iki tablo kıyaslanamaz; `purple` çalışma her iki kolu ortak görev, ortak tohum ve ortak eşleşme anahtarında birleştirir."
2. **Çekimser kalma (`abstention`) ve kapsama maliyeti (30 sn).** "Güven eşiği kapısı (`yayin_politikasi`) izinli yanlışları (`zararli_etki`) düşürür ama geçerli isteklerin bir kısmını da reddederek `kapsama` oranını azaltır; dürüst rapor ikisini birlikte gösterir."
3. **Doğrulanabilir yerel yayın paketi (30 sn).** "Ham deney çıktıları, özet metrikler, yöntem sınırları ve `SHA-256` dosya özetleri tek bir denetlenebilir pakette kilitlenir; böylece üçüncü bir göz sayıları ham kayıtlardan yeniden üretebilir."
4. **Soru (25 sn).** "`zararli_etki = 0` yapan çok yüksek bir güven eşiği kapsama oranını `%15`'e düşürüyorsa üretimde bu eşiği nasıl dengelersin?"
:::
