---
id: ai-guvence-19
title: Diferansiyel Gizlilik Bütçesi Deneyi
summary: Sentetik DP-SGD kayıtlarında temel ε-δ kompozisyonunu ve gürültü standardını hesapla; gizlilik ve fayda koşullarını karşılaştır.
esleme: ai-guvence-18, ai-guvence-20, ai-guvence-39
timeout: 45
---

::: anlat Gizlilik bütçesi deneyin tamamı için hesaplanır
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Bir mekanizma, komşuluk tanımı ve açıklanan çıktı için hesaplanmış gizlilik bütçesi | Görevler 1–3 sentetik JSON kayıtlarında verilmiş adım bütçelerinin basit toplamı; son adım gerçek örnek-başı autograd kırpma ve Gaussian gürültülü CPU eğitimi | Rastgele gürültü eklemek veya düşük bir ε yazdırmak üretim DP garantisi değildir; açık tohum ve ham iz yayını bu deneyin özel veriyle güvenli yayını olmasını engeller |

> [!NOT]
> `veri/dp_kayitlari.json` ve `veri/politika.json` elle yazılmış sentetik öğretim dosyalarıdır. Setup her çalıştırmada geçici dizine yeniden kopyalar; kalıcılık yoktur. Başlangıç kodu dosyayı gerçekten okur ve sonuç yazdırır. Son gerçek deneyin `PAFTA_DATA/calisma/ai-guvence-19/ayarlar.json` dosyası ayrıdır ve kalıcıdır; varsa üzerine yazılmaz. Kontrol ayrı girdiler kullanır. İlk görevlerdeki adım ε değerleri gürültü çarpanından türetilmiş değildir.

Diferansiyel gizlilik, komşu veri kümelerinde mekanizma çıktı dağılımlarının ne kadar ayırt edilebildiğini sınırlar. ε çarpımsal, δ toplamsal gevşeme parametresidir; bunları doğrudan sızan kayıt sayısı veya kişinin ifşa olma olasılığı diye yorumlama. Bu derste her adım için önceden verilmiş ε ve δ değerleri temel kompozisyonla toplanır: `toplam_epsilon=adim*adim_epsilon`, `toplam_delta=min(1,adim*adim_delta)`.

Bu basit toplam, RDP gibi gelişmiş muhasebe yöntemlerinin yerine geçmez ve gerçek bir DP-SGD eğitiminin ε değerini kendiliğinden üretmez. Görevler 1–3 sentetik dosya kayıtlarıdır; son görev sentetik veride gerçekten model eğitir. Opacus kullanılmaz; üretim DP-SGD sertifikasyonu yapılmaz.
:::

::: anlat Gürültü ve kırpma gizlilik-fayda ödünleşimini etkiler
İlk üç görevin sentetik kayıtlarında `gurultu_std=gurultu_carpani*kirpma_esigi` alanı tanımlıdır. Son gerçek görevde ise ortalama gradyana eklendiği için ölçek `sigma*2C/n` olur; iki ölçeğin birimini karıştırma. Kırpma, tek örneğin gradyan etkisini sınırlar; gürültü çarpanı ise bu sınırla birlikte eklenen gürültünün ölçeğini belirler. Daha düşük ε genel olarak daha güçlü gizlilik talebini anlatır, fakat doğruluk üzerindeki etkisi deneyle ölçülmelidir.

Politika raporunda toplam ε ve δ kendi üst sınırlarına eşit veya küçük, test doğruluğu alt sınıra eşit veya büyük olmalıdır. Uygun kayıtlarda önce yüksek doğruluk, sonra düşük ε, ardından düşük gürültü standardı ve alfabetik kimlik seçilir. Bu, yalnız verilen politika için deterministik bir seçimdir.
:::

::: anlat Dosya bütçesi ile gerçek gradyan mekanizmasını ayır
Bu dersin iki ayrı bütçe hesabını birbirine karıştırma. İlk üç görevde her adımın epsilon ve delta değerleri hazır verilmiştir; görevin bu iddiaları doğrulamak değil, belirtilen temel kompozisyonu ve politika seçimini doğru hesaplamaktır. Dosyaya küçük bir epsilon yazılmış olması o deneyi gizli yapmaz. Mekanizma, duyarlılık, komşuluk, rastgelelik ve hangi çıktının yayımlandığı bilinmeden bu sayı bir güvence taşımaz. İlk tablo bu sınırı özellikle gösterir. Gerçek görev ise kendi tanımlı Gaussian mekanizması için farklı bir hesap kullanır; ilk görevdeki basit epsilon toplamını bu fonksiyonun yerine koymamalısın.

Önce `veri/dp_kayitlari.json` dosyasındaki ham kayıtları oku. Bir kaydın adım sayısı, gürültü çarpanı ve kırpma eşiği farklı şeylerdir. Bool değerini adım sayısı kabul etmek veya NaN değerini sonlu bütçe saymak sonraki sıralamayı bozabilir. İlk görev bu alanların türünü ve sınırlarını doğrular. İkinci görev aynı dosyadaki her kaydı toplam epsilon, toplam delta ve gürültü standardı biçimine dönüştürür. Delta toplamını bire sınırlamak bu alıştırmanın çıktı sözleşmesidir; delta bire ulaştığında anlamlı bir gizlilik iddiası kaldığını düşünme. Ara değerleri yuvarlama, altı ondalığı yalnız rapor çıktısında uygula.

Üçüncü görev `veri/politika.json` dosyasındaki sınırları okur. Uygunluk için epsilon ve delta üst sınırları ile doğruluk alt sınırı birlikte sağlanır. Bu koşullardan yalnız birinin sağlanmasını yeterli görmek güvenlik ve fayda kararını değiştirir. Eşitlik uygundur; uygun adaylar arasında önce doğruluk, sonra epsilon ve gürültü standardı üzerinden tarif edilen sıra uygulanır. JSON kaydının bir kopyasında doğruluğu değiştirip seçilen kimliği gözlemle. Bu işlem verilen kayıtların politika muhasebesidir, model eğitiminin yeniden yapıldığı anlamına gelmez. Görünür örneği değiştirmen gizli kontrolün beklenen cevabını değiştirmez.

Canlı görevde optimizer her örneğin kaybı için gerçek autograd gradyanı alır. Vektörün L2 normu kırpma sınırından büyükse yönü korunarak ölçek küçültülür; küçük gradyan büyütülmez. Sıfır normda bölme sorununu önlemek için tarifte küçük bir payda eki kullanılır. Sonra örnek gradyanlarının ortalamasına Gaussian gürültüsü eklenir. Buradaki sabit boyutlu replace-one komşulukta ortalamanın duyarlılığı 2C/n olarak sınırlandırılır; standart sapma sigma çarpı bu duyarlılıktır. Toplam gradyanı bir kez kırpmak, örnek başına kırpmanın yerine geçmez. Öğrencinin kırpma fonksiyonu gerçek optimizer akışında kullanılır.

İdeal Gaussian mekanizması için adım başına rho=1/(2sigma²), adımların bileşiminde rho toplamı ve epsilon=rho+2sqrt(rho log(1/delta)) dönüşümü kullanılır. Bu dönüşümün koşulları ve Gaussian mekanizması [Bun ve Steinke](https://arxiv.org/html/1605.02065v1) içinde açıklanır. Bu deneyde altörnekleme olmadığı için altörnekleme kazancı eklenmez. Daha çok adım bütçeyi, daha büyük sigma ise gürültü ölçeğini etkiler; modelin faydasını ayrı ölçmelisin. Gerçek görev bu hesabı her adımda çağırarak iki sigma değerinin sonuçlarını karşılaştırır.

Saldırgan veya hatalı rapor yalnız son epsilon'u gösterip ham skorları, seed'i veya eğitim izlerini ayrıca yayımlayabilir. Bu ek açıklamalar garanti kapsamının dışında bilgi açığa çıkarabilir. Burada bunlar sentetik veride öğretim amacıyla açık tutulur; üretim için gizli ve uygun rastgelelik, doğru muhasebe ve yayın yüzeyinin birlikte denetlenmesi gerekir. Çıktıda ham ve kırpılmış normları, gürültü büyüklüğünü, eğitim kaybını ve test doğruluğunu birlikte oku. Gürültü eklenmesi doğruluğun mutlaka belirli miktarda düşmesini gerektirmez. Görev ölçümün doğruluğunu sınar; özel bir veri kümesi için sertifika üretmez.
:::

::: tahmin Bütçe ve gürültü standardını tahmin et
Üç çıktı satırını yaz:

```python
print(round(3 * 0.2, 6))
print(round(1.1 * 0.5, 6))
print(2.0 <= 2.0 and 0.0001 <= 0.0001 and 0.75 >= 0.7)
```

???

```cikti
0.6
0.55
True
```

İlk satır temel ε kompozisyonunu, ikinci satır gürültü standardını, üçüncü satır üç politika koşulunun eşitlikte kabul edildiğini gösterir.
:::

::: gorev 1 · DP deney kaydını doğrula
`dp_deneyi_dogrula(kayit)` işlevini yaz. Kayıt tam olarak `id`, `adim_epsilon`, `adim_delta`, `adim`, `gurultu_carpani`, `kirpma_esigi`, `test_dogrulugu` alanlarını taşır. Kimlik 1–64 karakterlik, ASCII harf/rakamla başlayan ve yalnız ASCII harf, rakam, alt çizgi veya tire içeren stringdir.

Adım bool olmayan tam sayı ve `[1,100000]` aralığındadır. Adım ε `(0,1000]`, gürültü çarpanı `(0,1000]`, kırpma eşiği `(0,10000]` aralığında bool olmayan sonlu sayıdır. Adım δ ve test doğruluğu bool olmayan sonlu sayı ve `[0,1]` aralığındadır. Geçersiz veride `ValueError` yükselt. Bağımsız sözlük kopyası döndür ve girdiyi değiştirme.

```starter
def dp_deneyi_dogrula(kayit):
    # KUSURLU BAŞLANGIÇ KODU: şema, sonluluk ve sayı sınırlarını doğrulamadan kopyalıyor.
    return dict(kayit)

from ai_guvence_veri import json_yukle
for kayit in json_yukle("veri/dp_kayitlari.json"):
    print(dp_deneyi_dogrula(kayit))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-19")
```

```test
import copy
K = {"id": "dp-1", "adim_epsilon": 0.2, "adim_delta": 0.00001, "adim": 10, "gurultu_carpani": 1.1, "kirpma_esigi": 1.0, "test_dogrulugu": 0.75}
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K) != K or fn(K) is K or K != once:
            return False
        sinir = dict(K, id="a" * 64, adim_epsilon=1000, adim_delta=0, adim=1, gurultu_carpani=1000, kirpma_esigi=10000, test_dogrulugu=0)
        if fn(sinir) != sinir or fn(dict(sinir, adim=100000, adim_delta=1, test_dogrulugu=1))["adim"] != 100000:
            return False
        for kayit in [
            None, [], dict(K, ek=1), dict(K, id=""), dict(K, id="a b"), dict(K, id="a" * 65), dict(K, id=None),
            dict(K, adim=True), dict(K, adim=1.5), dict(K, adim="10"), dict(K, adim=0), dict(K, adim=100001),
            dict(K, adim_epsilon=True), dict(K, adim_epsilon="0.2"), dict(K, adim_epsilon=float("nan")),
            dict(K, adim_epsilon=0), dict(K, adim_epsilon=-1), dict(K, adim_epsilon=1000.1),
            dict(K, adim_delta=True), dict(K, adim_delta=float("inf")), dict(K, adim_delta=-0.1), dict(K, adim_delta=1.1),
            dict(K, gurultu_carpani=True), dict(K, gurultu_carpani=0), dict(K, gurultu_carpani=-1), dict(K, gurultu_carpani=1000.1),
            dict(K, kirpma_esigi=True), dict(K, kirpma_esigi=0), dict(K, kirpma_esigi=-1), dict(K, kirpma_esigi=10000.1),
            dict(K, test_dogrulugu=True), dict(K, test_dogrulugu="0.75"), dict(K, test_dogrulugu=float("nan")),
            dict(K, test_dogrulugu=-0.1), dict(K, test_dogrulugu=1.1),
        ]:
            try:
                fn(kayit)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(dp_deneyi_dogrula), "DP şeması, pozitif parametreler, sınırlar ve kopya korunmalı")
def m_epsilon(kayit):
    return dp_deneyi_dogrula(dict(kayit, adim_epsilon=0))
def m_adim(kayit):
    return dp_deneyi_dogrula(dict(kayit, adim=0))
def m_kirpma(kayit):
    return dp_deneyi_dogrula(dict(kayit, kirpma_esigi=0))
for ad, mutant in [("epsilonu silen", m_epsilon), ("adımı silen", m_adim), ("kırpmayı silen", m_kirpma)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def dp_deneyi_dogrula(kayit):
    import math
    import re
    if not isinstance(kayit, dict):
        raise ValueError("kayıt sözlük olmalı")
    if set(kayit) != {"id", "adim_epsilon", "adim_delta", "adim", "gurultu_carpani", "kirpma_esigi", "test_dogrulugu"}:
        raise ValueError("kayıt şeması geçersiz")
    if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
        raise ValueError("kimlik geçersiz")
    if isinstance(kayit["adim"], bool) or not isinstance(kayit["adim"], int):
        raise ValueError("adım tam sayı olmalı")
    if kayit["adim"] < 1 or kayit["adim"] > 100000:
        raise ValueError("adım aralık dışında")
    for alan, ust in (("adim_epsilon", 1000), ("gurultu_carpani", 1000), ("kirpma_esigi", 10000)):
        deger = kayit[alan]
        if isinstance(deger, bool) or not isinstance(deger, (int, float)):
            raise ValueError(alan + " sayı olmalı")
        if not math.isfinite(deger) or deger <= 0 or deger > ust:
            raise ValueError(alan + " geçersiz")
    for alan in ("adim_delta", "test_dogrulugu"):
        deger = kayit[alan]
        if isinstance(deger, bool) or not isinstance(deger, (int, float)):
            raise ValueError(alan + " sayı olmalı")
        if not math.isfinite(deger) or deger < 0 or deger > 1:
            raise ValueError(alan + " geçersiz")
    return dict(kayit)

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    for kayit in json_yukle("veri/dp_kayitlari.json"):
        print(dp_deneyi_dogrula(kayit))
```

```hint
Pozitif olması gereken üç parametrede sıfırı reddet; δ ve doğrulukta sıfıra izin ver. Adım için bool kontrolünü unutma.
```
:::

::: gorev 2 · Temel bütçe kompozisyonunu ve gürültüyü hesapla
`dp_butce_olc(kayit)` işlevini yaz. Kayıt ilk görevdeki şemadadır; geçersiz veride `ValueError` yükselt.

`{"id":D,"toplam_epsilon":X,"toplam_delta":X,"gurultu_std":X,"test_dogrulugu":X}` döndür. Toplam ε `adim*adim_epsilon`, toplam δ `min(1,adim*adim_delta)`, gürültü standardı `gurultu_carpani*kirpma_esigi` olur. Dört sayısal sonucu altı ondalık basamağa yuvarla ve girdiyi değiştirme.

```starter
def dp_butce_olc(kayit):
    import math
    import re
    if not isinstance(kayit, dict) or set(kayit) != {"id", "adim_epsilon", "adim_delta", "adim", "gurultu_carpani", "kirpma_esigi", "test_dogrulugu"}:
        raise ValueError("kayıt şeması geçersiz")
    if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
        raise ValueError("kimlik geçersiz")
    if isinstance(kayit["adim"], bool) or not isinstance(kayit["adim"], int) or kayit["adim"] < 1 or kayit["adim"] > 100000:
        raise ValueError("adım geçersiz")
    for alan, ust in (("adim_epsilon", 1000), ("gurultu_carpani", 1000), ("kirpma_esigi", 10000)):
        deger = kayit[alan]
        if isinstance(deger, bool) or not isinstance(deger, (int, float)):
            raise ValueError(alan + " sayı olmalı")
        if not math.isfinite(deger) or deger <= 0 or deger > ust:
            raise ValueError(alan + " geçersiz")
    for alan in ("adim_delta", "test_dogrulugu"):
        deger = kayit[alan]
        if isinstance(deger, bool) or not isinstance(deger, (int, float)):
            raise ValueError(alan + " sayı olmalı")
        if not math.isfinite(deger) or deger < 0 or deger > 1:
            raise ValueError(alan + " geçersiz")
    # KUSURLU BAŞLANGIÇ KODU: epsilon hesabında bütün adımlar yerine tek adımı kullanıyor.
    epsilon = kayit["adim_epsilon"]
    delta = min(1.0, kayit["adim"] * kayit["adim_delta"])
    std = kayit["gurultu_carpani"] * kayit["kirpma_esigi"]
    return {"id": kayit["id"], "toplam_epsilon": round(epsilon, 6), "toplam_delta": round(delta, 6), "gurultu_std": round(std, 6), "test_dogrulugu": round(kayit["test_dogrulugu"], 6)}

from ai_guvence_veri import json_yukle
for kayit in json_yukle("veri/dp_kayitlari.json"):
    print(dp_butce_olc(kayit))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-19")
```

```test
import copy
K = {"id": "dp-1", "adim_epsilon": 0.2, "adim_delta": 0.00001, "adim": 10, "gurultu_carpani": 1.1, "kirpma_esigi": 1.0, "test_dogrulugu": 0.75}
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        if fn(K) != {"id": "dp-1", "toplam_epsilon": 2.0, "toplam_delta": 0.0001, "gurultu_std": 1.1, "test_dogrulugu": 0.75} or K != once:
            return False
        sinir = fn(dict(K, id="a" * 64, adim=1, adim_delta=0, test_dogrulugu=0))
        if sinir["toplam_delta"] != 0 or sinir["test_dogrulugu"] != 0:
            return False
        kapali = fn(dict(K, adim=1000, adim_delta=0.002))
        if kapali["toplam_delta"] != 1:
            return False
        yuvarla = fn(dict(K, adim_epsilon=0.3333333, adim_delta=0.0000004, adim=2, gurultu_carpani=0.3333333, kirpma_esigi=1, test_dogrulugu=0.6666667))
        if yuvarla != {"id": "dp-1", "toplam_epsilon": 0.666667, "toplam_delta": 0.000001, "gurultu_std": 0.333333, "test_dogrulugu": 0.666667}:
            return False
        ust = fn(dict(K, adim_epsilon=1000, adim_delta=1, adim=100000, gurultu_carpani=1000, kirpma_esigi=10000, test_dogrulugu=1))
        if ust["toplam_epsilon"] != 100000000 or ust["toplam_delta"] != 1 or ust["gurultu_std"] != 10000000:
            return False
        for kayit in [
            None, [], dict(K, ek=1), dict(K, id=123), dict(K, id="a b"), dict(K, id="a" * 65), dict(K, adim=True), dict(K, adim=1.5), dict(K, adim=0),
            dict(K, adim=100001), dict(K, adim_epsilon=True), dict(K, adim_epsilon="0.2"), dict(K, adim_epsilon=0), dict(K, adim_epsilon=1000.1), dict(K, adim_epsilon=float("nan")),
            dict(K, adim_delta=True), dict(K, adim_delta="0"), dict(K, adim_delta=-0.1), dict(K, adim_delta=1.1),
            dict(K, gurultu_carpani=True), dict(K, gurultu_carpani=0), dict(K, gurultu_carpani=1000.1),
            dict(K, kirpma_esigi=0), dict(K, kirpma_esigi=10000.1), dict(K, test_dogrulugu=True), dict(K, test_dogrulugu="0.75"), dict(K, test_dogrulugu=float("nan")), dict(K, test_dogrulugu=-0.1), dict(K, test_dogrulugu=1.1),
        ]:
            try:
                fn(kayit)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(dp_butce_olc), "temel kompozisyon, delta üst sınırı ve gürültü standardı korunmalı")
def m_epsilon(kayit):
    return dp_butce_olc(dict(kayit, adim_epsilon=1))
def m_delta(kayit):
    return dp_butce_olc(dict(kayit, adim_delta=0))
def m_gurultu(kayit):
    return dp_butce_olc(dict(kayit, gurultu_carpani=1))
for ad, mutant in [("epsilonu değiştiren", m_epsilon), ("deltayı silen", m_delta), ("gürültüyü değiştiren", m_gurultu)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def dp_butce_olc(kayit):
    import math
    import re
    if not isinstance(kayit, dict) or set(kayit) != {"id", "adim_epsilon", "adim_delta", "adim", "gurultu_carpani", "kirpma_esigi", "test_dogrulugu"}:
        raise ValueError("kayıt şeması geçersiz")
    if not isinstance(kayit["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", kayit["id"]):
        raise ValueError("kimlik geçersiz")
    if isinstance(kayit["adim"], bool) or not isinstance(kayit["adim"], int) or kayit["adim"] < 1 or kayit["adim"] > 100000:
        raise ValueError("adım geçersiz")
    for alan, ust in (("adim_epsilon", 1000), ("gurultu_carpani", 1000), ("kirpma_esigi", 10000)):
        deger = kayit[alan]
        if isinstance(deger, bool) or not isinstance(deger, (int, float)):
            raise ValueError(alan + " sayı olmalı")
        if not math.isfinite(deger) or deger <= 0 or deger > ust:
            raise ValueError(alan + " geçersiz")
    for alan in ("adim_delta", "test_dogrulugu"):
        deger = kayit[alan]
        if isinstance(deger, bool) or not isinstance(deger, (int, float)):
            raise ValueError(alan + " sayı olmalı")
        if not math.isfinite(deger) or deger < 0 or deger > 1:
            raise ValueError(alan + " geçersiz")
    epsilon = kayit["adim"] * kayit["adim_epsilon"]
    delta = min(1.0, kayit["adim"] * kayit["adim_delta"])
    std = kayit["gurultu_carpani"] * kayit["kirpma_esigi"]
    return {"id": kayit["id"], "toplam_epsilon": round(epsilon, 6), "toplam_delta": round(delta, 6), "gurultu_std": round(std, 6), "test_dogrulugu": round(kayit["test_dogrulugu"], 6)}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    for kayit in json_yukle("veri/dp_kayitlari.json"):
        print(dp_butce_olc(kayit))
```

```hint
Önce ham toplamları hesapla; δ'yı bire kırp. Gürültü çarpanı ile kırpma eşiğini birbirine değil, birbiriyle çarp.
```
:::

::: gorev 3 · Gizlilik ve fayda politikasını uygula
`dp_politika_raporu(kayitlar, epsilon_ust, delta_ust, dogruluk_alt)` işlevini yaz. Kayıtlar ilk görevdeki şemayı taşıyan boş olmayan listedir; kimlikler yinelenemez. ε üst sınırı bool olmayan sonlu sayı ve `(0,100000000]`, δ üst sınırı ve doğruluk alt sınırı `[0,1]` aralığındadır. Geçersiz veride `ValueError` yükselt.

Her kayıt için ikinci görevdeki ölçümleri ve `uygun` bayrağını içeren `{"id":D,"toplam_epsilon":X,"toplam_delta":X,"gurultu_std":X,"test_dogrulugu":X,"uygun":BOOL}` üret; satırları kimliğe göre sırala. Uygunluk için ham toplam ε ve δ üst sınırlarına eşit veya küçük, ham doğruluk alt sınıra eşit veya büyük olmalıdır. Uygun kayıtlardan en yüksek ham doğruluğu, eşitlikte en düşük ham ε'yı, sonra en düşük ham gürültü standardını ve alfabetik kimliği seç. `{"satirlar":[...],"uygun_sayi":N,"secilen":D veya None}` döndür ve girdiyi değiştirme.

```starter
def dp_politika_raporu(kayitlar, epsilon_ust, delta_ust, dogruluk_alt):
    import math
    import re
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar boş olmayan liste olmalı")
    if isinstance(epsilon_ust, bool) or not isinstance(epsilon_ust, (int, float)):
        raise ValueError("epsilon üst sınırı sayı olmalı")
    if not math.isfinite(epsilon_ust) or epsilon_ust <= 0 or epsilon_ust > 100000000:
        raise ValueError("epsilon üst sınırı geçersiz")
    for deger in (delta_ust, dogruluk_alt):
        if isinstance(deger, bool) or not isinstance(deger, (int, float)):
            raise ValueError("sınır sayı olmalı")
        if not math.isfinite(deger) or deger < 0 or deger > 1:
            raise ValueError("sınır geçersiz")
    idler = set()
    for x in kayitlar:
        if not isinstance(x, dict) or set(x) != {"id", "adim_epsilon", "adim_delta", "adim", "gurultu_carpani", "kirpma_esigi", "test_dogrulugu"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(x["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", x["id"]):
            raise ValueError("kimlik geçersiz")
        if x["id"] in idler:
            raise ValueError("kimlik yinelenemez")
        if isinstance(x["adim"], bool) or not isinstance(x["adim"], int) or x["adim"] < 1 or x["adim"] > 100000:
            raise ValueError("adım geçersiz")
        for alan, ust in (("adim_epsilon", 1000), ("gurultu_carpani", 1000), ("kirpma_esigi", 10000)):
            deger = x[alan]
            if isinstance(deger, bool) or not isinstance(deger, (int, float)):
                raise ValueError(alan + " sayı olmalı")
            if not math.isfinite(deger) or deger <= 0 or deger > ust:
                raise ValueError(alan + " geçersiz")
        for alan in ("adim_delta", "test_dogrulugu"):
            deger = x[alan]
            if isinstance(deger, bool) or not isinstance(deger, (int, float)):
                raise ValueError(alan + " sayı olmalı")
            if not math.isfinite(deger) or deger < 0 or deger > 1:
                raise ValueError(alan + " geçersiz")
        idler.add(x["id"])
    # KUSURLU BAŞLANGIÇ KODU: doğruluk alt sınırına eşit kaydı uygun saymıyor.
    satirlar = []
    for x in sorted(kayitlar, key=lambda x: x["id"]):
        epsilon = x["adim"] * x["adim_epsilon"]
        delta = min(1.0, x["adim"] * x["adim_delta"])
        std = x["gurultu_carpani"] * x["kirpma_esigi"]
        dogruluk = x["test_dogrulugu"]
        uygun = epsilon <= epsilon_ust and delta <= delta_ust and dogruluk > dogruluk_alt
        satirlar.append({"id": x["id"], "toplam_epsilon": round(epsilon, 6), "toplam_delta": round(delta, 6), "gurultu_std": round(std, 6), "test_dogrulugu": round(dogruluk, 6), "uygun": uygun, "_epsilon": epsilon, "_std": std, "_dogruluk": dogruluk})
    uygunlar = [x for x in satirlar if x["uygun"]]
    secilen = min(uygunlar, key=lambda x: (-x["_dogruluk"], x["_epsilon"], x["_std"], x["id"]))["id"] if uygunlar else None
    for satir in satirlar:
        del satir["_epsilon"]
        del satir["_std"]
        del satir["_dogruluk"]
    return {"satirlar": satirlar, "uygun_sayi": len(uygunlar), "secilen": secilen}

from ai_guvence_veri import json_yukle
politika = json_yukle("veri/politika.json")
print(dp_politika_raporu(json_yukle("veri/dp_kayitlari.json"), **politika))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_guvence_veri import hazirla
hazirla("ai-guvence-19")
```

```test
import copy
K = [
    {"id": "a", "adim_epsilon": 0.2, "adim_delta": 0.00001, "adim": 10, "gurultu_carpani": 1.1, "kirpma_esigi": 1, "test_dogrulugu": 0.75},
    {"id": "b", "adim_epsilon": 0.1, "adim_delta": 0.00001, "adim": 10, "gurultu_carpani": 1.5, "kirpma_esigi": 1, "test_dogrulugu": 0.72},
    {"id": "c", "adim_epsilon": 0.3, "adim_delta": 0.00001, "adim": 10, "gurultu_carpani": 0.8, "kirpma_esigi": 1, "test_dogrulugu": 0.8},
    {"id": "d", "adim_epsilon": 0.2, "adim_delta": 0.00002, "adim": 10, "gurultu_carpani": 1.1, "kirpma_esigi": 1, "test_dogrulugu": 0.75},
    {"id": "e", "adim_epsilon": 0.2, "adim_delta": 0.00001, "adim": 10, "gurultu_carpani": 1.1, "kirpma_esigi": 1, "test_dogrulugu": 0.6},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(K)
        sonuc = fn(K, 2, 0.0001, 0.7)
        if K != once or sonuc["secilen"] != "a" or sonuc["uygun_sayi"] != 2:
            return False
        if [x["uygun"] for x in sonuc["satirlar"]] != [True, True, False, False, False]:
            return False
        if sonuc["satirlar"][0] != {"id": "a", "toplam_epsilon": 2.0, "toplam_delta": 0.0001, "gurultu_std": 1.1, "test_dogrulugu": 0.75, "uygun": True}:
            return False
        if fn(K, 2, 0.0001, 0.75)["secilen"] != "a" or fn(K, 2, 0.0001, 0.9)["secilen"] is not None:
            return False
        yuvarla = fn([dict(K[0], id="y", adim_epsilon=0.3333333, adim_delta=0.0000004, adim=2, gurultu_carpani=0.3333333, test_dogrulugu=0.6666667)], 1, 0.000001, 0)
        if yuvarla["satirlar"][0]["toplam_epsilon"] != 0.666667 or yuvarla["satirlar"][0]["toplam_delta"] != 0.000001:
            return False
        if yuvarla["satirlar"][0]["gurultu_std"] != 0.333333 or yuvarla["satirlar"][0]["test_dogrulugu"] != 0.666667:
            return False
        sinir = fn([dict(K[0], id="a" * 64, adim=1, adim_delta=0, test_dogrulugu=0)], 2, 0, 0)
        if sinir["uygun_sayi"] != 1:
            return False
        ust = fn([dict(K[0], id="ust", adim_epsilon=1000, adim_delta=1, adim=100000, gurultu_carpani=1000, kirpma_esigi=10000, test_dogrulugu=1)], 100000000, 1, 1)
        if ust["uygun_sayi"] != 1 or ust["satirlar"][0]["gurultu_std"] != 10000000:
            return False
        if fn([dict(K[0], id="d8", adim=10, adim_delta=0.08)], 10, 1.0, 0.0)["satirlar"][0]["toplam_delta"] != 0.8:
            return False
        for kayitlar, eu, du, da in [
            (None, 2, 0.0001, 0.7), (K, None, 0.0001, 0.7), (K, 2, None, 0.7), (K, 2, 0.0001, None),
            ({}, 2, 0.0001, 0.7), (tuple(K), 2, 0.0001, 0.7), ([], 2, 0.0001, 0.7), ([None], 2, 0.0001, 0.7),
            ([K[0], K[0]], 2, 0.0001, 0.7), ([dict(K[0], ek=1)], 2, 0.0001, 0.7),
            ([dict(K[0], id=123)], 2, 0.0001, 0.7), ([dict(K[0], id="a b")], 2, 0.0001, 0.7), ([dict(K[0], id="a" * 65)], 2, 0.0001, 0.7),
            ([dict(K[0], adim=True)], 2, 0.0001, 0.7), ([dict(K[0], adim=1.5)], 2, 0.0001, 0.7), ([dict(K[0], adim=0)], 2, 0.0001, 0.7), ([dict(K[0], adim=100001)], 2, 0.0001, 0.7), ([dict(K[0], adim_epsilon=True)], 2, 0.0001, 0.7),
            ([dict(K[0], adim_epsilon="0.2")], 2, 0.0001, 0.7), ([dict(K[0], adim_epsilon=0)], 2, 0.0001, 0.7), ([dict(K[0], adim_epsilon=1000.1)], 2, 0.0001, 0.7),
            ([dict(K[0], adim_epsilon=float("nan"))], 2, 0.0001, 0.7), ([dict(K[0], gurultu_carpani=float("inf"))], 2, 0.0001, 0.7),
            ([dict(K[0], adim_delta=True)], 2, 0.0001, 0.7), ([dict(K[0], adim_delta="0")], 2, 0.0001, 0.7), ([dict(K[0], adim_delta=float("nan"))], 2, 0.0001, 0.7),
            ([dict(K[0], gurultu_carpani=True)], 2, 0.0001, 0.7), ([dict(K[0], gurultu_carpani="1.1")], 2, 0.0001, 0.7),
            ([dict(K[0], gurultu_carpani=0)], 2, 0.0001, 0.7), ([dict(K[0], gurultu_carpani=1000.1)], 2, 0.0001, 0.7),
            ([dict(K[0], kirpma_esigi=0)], 2, 0.0001, 0.7), ([dict(K[0], kirpma_esigi=10000.1)], 2, 0.0001, 0.7), ([dict(K[0], test_dogrulugu=True)], 2, 0.0001, 0.7),
            ([dict(K[0], test_dogrulugu="0.75")], 2, 0.0001, 0.7), ([dict(K[0], test_dogrulugu=-0.1)], 2, 0.0001, 0.7), ([dict(K[0], test_dogrulugu=1.1)], 2, 0.0001, 0.7),
            (K, True, 0.0001, 0.7), (K, "2", 0.0001, 0.7), (K, float("nan"), 0.0001, 0.7),
            (K, 0, 0.0001, 0.7), (K, -1, 0.0001, 0.7), (K, 100000001, 0.0001, 0.7),
            (K, 2, True, 0.7), (K, 2, -0.1, 0.7), (K, 2, 1.1, 0.7), (K, 2, float("inf"), 0.7),
            (K, 2, 0.0001, True), (K, 2, 0.0001, -0.1), (K, 2, 0.0001, 1.1), (K, 2, 0.0001, float("nan")),
        ]:
            try:
                fn(kayitlar, eu, du, da)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(dp_politika_raporu), "üç politika koşulu, bütçe hesabı ve seçim sırası korunmalı")
def m_epsilon(kayitlar, eu, du, da):
    return dp_politika_raporu([dict(x, adim_epsilon=1) for x in kayitlar], eu, du, da)
def m_delta(kayitlar, eu, du, da):
    return dp_politika_raporu([dict(x, adim_delta=0) for x in kayitlar], eu, du, da)
def m_dogruluk(kayitlar, eu, du, da):
    return dp_politika_raporu([dict(x, test_dogrulugu=0) for x in kayitlar], eu, du, da)
for ad, mutant in [("epsilonu değiştiren", m_epsilon), ("deltayı silen", m_delta), ("doğruluğu silen", m_dogruluk)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def dp_politika_raporu(kayitlar, epsilon_ust, delta_ust, dogruluk_alt):
    import math
    import re
    if not isinstance(kayitlar, list) or not kayitlar:
        raise ValueError("kayıtlar boş olmayan liste olmalı")
    if isinstance(epsilon_ust, bool) or not isinstance(epsilon_ust, (int, float)):
        raise ValueError("epsilon üst sınırı sayı olmalı")
    if not math.isfinite(epsilon_ust) or epsilon_ust <= 0 or epsilon_ust > 100000000:
        raise ValueError("epsilon üst sınırı geçersiz")
    for deger in (delta_ust, dogruluk_alt):
        if isinstance(deger, bool) or not isinstance(deger, (int, float)):
            raise ValueError("sınır sayı olmalı")
        if not math.isfinite(deger) or deger < 0 or deger > 1:
            raise ValueError("sınır geçersiz")
    idler = set()
    for x in kayitlar:
        if not isinstance(x, dict) or set(x) != {"id", "adim_epsilon", "adim_delta", "adim", "gurultu_carpani", "kirpma_esigi", "test_dogrulugu"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(x["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", x["id"]):
            raise ValueError("kimlik geçersiz")
        if x["id"] in idler:
            raise ValueError("kimlik yinelenemez")
        if isinstance(x["adim"], bool) or not isinstance(x["adim"], int) or x["adim"] < 1 or x["adim"] > 100000:
            raise ValueError("adım geçersiz")
        for alan, ust in (("adim_epsilon", 1000), ("gurultu_carpani", 1000), ("kirpma_esigi", 10000)):
            deger = x[alan]
            if isinstance(deger, bool) or not isinstance(deger, (int, float)):
                raise ValueError(alan + " sayı olmalı")
            if not math.isfinite(deger) or deger <= 0 or deger > ust:
                raise ValueError(alan + " geçersiz")
        for alan in ("adim_delta", "test_dogrulugu"):
            deger = x[alan]
            if isinstance(deger, bool) or not isinstance(deger, (int, float)):
                raise ValueError(alan + " sayı olmalı")
            if not math.isfinite(deger) or deger < 0 or deger > 1:
                raise ValueError(alan + " geçersiz")
        idler.add(x["id"])
    satirlar = []
    for x in sorted(kayitlar, key=lambda x: x["id"]):
        epsilon = x["adim"] * x["adim_epsilon"]
        delta = min(1.0, x["adim"] * x["adim_delta"])
        std = x["gurultu_carpani"] * x["kirpma_esigi"]
        dogruluk = x["test_dogrulugu"]
        uygun = epsilon <= epsilon_ust and delta <= delta_ust and dogruluk >= dogruluk_alt
        satirlar.append({"id": x["id"], "toplam_epsilon": round(epsilon, 6), "toplam_delta": round(delta, 6), "gurultu_std": round(std, 6), "test_dogrulugu": round(dogruluk, 6), "uygun": uygun, "_epsilon": epsilon, "_std": std, "_dogruluk": dogruluk})
    uygunlar = [x for x in satirlar if x["uygun"]]
    secilen = min(uygunlar, key=lambda x: (-x["_dogruluk"], x["_epsilon"], x["_std"], x["id"]))["id"] if uygunlar else None
    for satir in satirlar:
        del satir["_epsilon"]
        del satir["_std"]
        del satir["_dogruluk"]
    return {"satirlar": satirlar, "uygun_sayi": len(uygunlar), "secilen": secilen}

if __name__ == "__main__":
    from ai_guvence_veri import json_yukle
    politika = json_yukle("veri/politika.json")
    print(dp_politika_raporu(json_yukle("veri/dp_kayitlari.json"), **politika))
```

```hint
Üç uygunluk koşulunu ayrı hesaplayıp `and` ile birleştir. Seçimde yuvarlanmış görüntü değerleri yerine ham değerleri kullan.
```
:::


::: anlat Canlı CPU deneyi ve düzenlenebilir sentetik ayar
Önce [sentetik ayar dosyasını](/data/ai-guvence-19-ayarlar.txt) açıp seed, ornek, sigma alanlarını incele. Bu JSON örneği kaydedilmiş model çıktısı değildir. Yeni görev gerçek küçük MLP'yi torch autograd ile CPU'da eğitir; ağ/model indirme yoktur.

Çalıştır ilk kullanımda örneği `PAFTA_DATA/calisma/ai-guvence-19/ayarlar.json` konumuna yalnız yoksa kopyalar, tam yolu ekranda yazar. Göreli PAFTA_DATA proje köküne göre çözülür. Öğrenci bu kalıcı JSON'u metin düzenleyicide değiştirebilir (seed:0..2**30-1, ornek:8..32, sigma:0.5..8); yeniden Çalıştır düzenlemeyi korur. Tarayıcıdaki örnek salt okunur indirme bağlantısıdır; kalıcı kopyayı kendi editöründe aç. Kontrol bağımsız test ayarı kullanır, örneği değiştirmek beklenen cevabı değiştirmez.

Yalnız sentetik veriler kullanılır. Saldırının kazanması veya gizlilik iddiasının desteklenmesi PASS şartı değildir. Küçük deney sohbet modelinin gizliliğine genellenemez. DP eğitimli deneylerde açık tohum, ham veriler ve eğitim izleri öğretim içindir; bu yayınlar özel veri için DP garantisi taşımaz. Bütçe yalnız sabit boyutlu replace-one tam batch Gaussian ağırlık mekanizması içindir, ham izlere değil. Güvenli üretim RNG/accountant denetimi yapılmaz.
:::

::: gorev Gerçek deney · CPU gizlilik ölçümü 19
`olc(g,c)` bir örneğin düz gradyan vektörünü L2 normu c ile kırpsın: g*min(1,c/(norm+1e-12)). `butce(steps,sigma,delta)` rho=steps/(2*sigma**2), epsilon=rho+2*sqrt(rho*log(1/delta)) döndürsün. Gerçek optimizer öğrenci gradyanını kullanır; her adım bütçe fonksiyonunu çağırır. Tam batch, sabit n, replace-one duyarlılık 2C/n; Gaussian std=sigma*2C/n. Bu ek görevde önceki fixture basit epsilon toplama formülü kullanılmaz.

Girdileri değiştirme. Çalıştır gerçek öğrenci dosyasıyla sonuç ve kanıt yolunu gösterir; Kontrol farklı veri ve tohumlarda bağımsız hesap, boş/sabit/yanlış çözüm denetimi yapar. torch yokluğu PASS değildir.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 180
```

```starter
import ai_lab
def olc(g, c):
    return {}
def butce(steps,sigma,delta):
    return 0
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_17_20 as deney
    deney.goster(19,olc,butce)
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
kontrol(deney.sozlesme(19,olc,butce),'Görülmemiş sınırlar, eşitlik ve yanlış ölçüm reddi')
kontrol(olc([0.3, 0.4], 1.0) == [0.3, 0.4] and olc([3.0, 4.0], 10.0) == [3.0, 4.0] and len(olc([1e-12, 0.0], 1e-12)) == 2, 'norm < c iken kırpma katsayısı tam 1.0 kalmalı ve küçük normda sıfıra bölünmemeli')
with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp)/'ayar.json'
    p.write_text('{"seed": 8319, "ornek": 13, "sigma": 1.75}',encoding='utf-8')
    r=deney.deney(19,olc,butce,path=p)
    for name,value in r['kontroller'].items(): kontrol(value,name)
ns={}
exec('def olc(g, c):\n    import math\n    norm=math.sqrt(sum(v*v for v in g))\n    return [v*1. for v in g]\n\ndef butce(steps, sigma, delta):\n    import math\n    rho=steps/(2*sigma*sigma)\n    return rho+2*math.sqrt(rho*math.log(1/delta))\n',ns)
kontrol(not deney.sozlesme(19,ns['olc'],ns['butce']),'Mutant 1 reddedilir')
ns={}
exec('def olc(g, c):\n    import math\n    norm=math.sqrt(sum(v*v for v in g))\n    return [v*min(1.,c/(norm+1e-12)) for v in g]\n\ndef butce(steps, sigma, delta):\n    import math\n    rho=1/(2*sigma*sigma)\n    return rho+2*math.sqrt(rho*math.log(1/delta))\n',ns)
kontrol(not deney.sozlesme(19,ns['olc'],ns['butce']),'Mutant 2 reddedilir')
ns={}
exec('def olc(g, c):\n    import math\n    norm=math.sqrt(sum(v*v for v in g))\n    return [v*min(1.,c/(norm+1e-12)) for v in g]\n\ndef butce(steps, sigma, delta):\n    import math\n    rho=steps/(2*sigma)\n    return rho+2*math.sqrt(rho*math.log(1/delta))\n',ns)
kontrol(not deney.sozlesme(19,ns['olc'],ns['butce']),'Mutant 3 reddedilir')
ai_lab.kanit_yaz('guvence-19-cpu',dict(r,kabul=all(checks)))

```

```solution
import ai_lab
def olc(g, c):
    import math
    norm=math.sqrt(sum(v*v for v in g))
    return [v*min(1.,c/(norm+1e-12)) for v in g]

def butce(steps, sigma, delta):
    import math
    rho=steps/(2*sigma*sigma)
    return rho+2*math.sqrt(rho*math.log(1/delta))

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_guvence_17_20 as deney
    deney.goster(19,olc,butce)
```

```hint
Ham eşik koşulunu yuvarlamadan uygula. AUC eşitlikte yarım katkı verir. Gürültüyü başarı garantisi olarak yorumlama.
```
:::


::: anlat Hesabın varsayımları ve birincil kaynak
Örnek başına gradyan gerçekten autograd ile hesaplanıp L2 C=1 ile kırpılır; tam batch ortalamanın sabit n, bir kayıt değiştirme komşuluğunda duyarlılığı 2C/n olur. Her adıma sigma*(2C/n) Gaussian ekleme için ideal bağımsız gizli rastgelelik varsayımıyla rho=1/(2sigma²) yazılır; adaptif adımlarda rho toplanır. epsilon=rho+2sqrt(rho log(1/delta)) dönüşümü [Bun ve Steinke, önermeler 1.3/1.6 ve bileşim](https://arxiv.org/abs/1605.02065) ile açıklanır; [Mironov, Rényi Differential Privacy](https://arxiv.org/abs/1702.07476) Gaussian RDP bileşimini sunar. Burada altörnekleme veya üretim DP-SGD sertifikasyonu yoktur. Açık tohum ve ham sonuç yayını nedeniyle bu çalıştırma özel bir üretim yayını değildir.
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Örnek başına gradyan kırpma + Gaussian gürültü (35 sn).** "Toplu gradyana doğrudan gürültü eklemek tek bir uç kaydın sınırsız etkisini gizlemez; `DP-SGD` önce her örneğin gradyan normunu $C$ ile üstten kırpar, sonra duyarlılıkla orantılı $\sigma$ Gaussian gürültü ekler."
2. **Kompozisyon ve gizlilik bütçesi ($\varepsilon, \delta$) (30 sn).** "Her eğitim adımı ek bilgi sızdırır; $\rho = T / (2\sigma^2)$ yoğunlaşmış DP bileşimi adım sayısı $T$ arttıkça veya $\sigma$ küçüldükçe toplam $\varepsilon$ bütçesinin nasıl büyüdüğünü sayısallaştırır."
3. **Gizlilik–fayda ödünleşimi (30 sn).** "Çok yüksek gürültü $\varepsilon$'u küçültür ama doğruluğu tabanın altına düşürebilir; kabul politikası hem $\varepsilon \le \varepsilon_{\text{üst}}$ hem de minimum doğruluk eşiğini birlikte arar."
4. **Soru (25 sn).** "Hiperparametre aramasını aynı özel veri kümesi üzerinde 20 kez tekrarlayıp yalnız kazanan koşunun $\varepsilon$ değerini raporlamak gizlilik muhasebesini neden bozar?"
:::
