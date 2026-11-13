---
id: ai-savunma-31
title: "Sınırsız Tüketim Savunması: Bütçe ve Oran Sınırı"
summary: token bucket ile oran sınırla, token maliyetini hesapla, üretimi bütçeyle kes; denial-of-wallet'ı gerçek modelde deterministik olarak durdur.
esleme: ai-saldiri-40
timeout: 45
---

::: anlat Sınırsız tüketim: tek bir istek kaynakları ve faturayı tüketebilir
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Üretim token sayısı, kesilme nedeni ve gerçek istek ayarları | Görevler 1–3 görünür sentetik istek/kullanım JSON'ları; son görev kurulu yerel Ollama modeline yüksek ve bütçeli num_predict ile iki gerçek çağrı | Tek istekte çıkış tavanı bütün servis için tüketim savunması değildir; giriş uzunluğu, eşzamanlılık ve ajan döngüleri ayrıca sınırlandırılmalıdır |

> [!NOT]
> `veri/istekler.json`, `veri/kullanim.json` ve `veri/butce.json` sentetik öğretim dosyalarıdır. Setup her çalıştırmada geçici dizine yeniden kopyalar, kalıcılık yoktur. Başlangıçlar dosyaları gerçekten okur; aynı çalıştırmada bellekte kopyayı değiştirerek deneme yapılabilir. Fiyatlar örnektir, ücretli API veya gerçek fatura yoktur. Son görev gerçek yerel model tüketimini ölçer; onun sınırları deney modülünde sabittir. Kontrol ayrı girdiler kullanır.

Bir LLM servisinin en sessiz güvenlik açığı, bir girdiyi yanlış işlemek değil, **ne kadar** ürettiğini sınırlamamaktır (OWASP LLM "Unbounded Consumption"). Üretim token başına hem hesaplama hem para maliyetidir; `num_predict`/`max_tokens` üst sınırı yoksa, "10000'e kadar say" ya da özyinelemeli bir ajan döngüsü tek başına GPU'yu doldurur ve faturayı şişirir — buna **denial-of-wallet** denir. Savunma üç katmandan oluşur ve hepsi **deterministiktir**: modelin iş birliğine değil, kodun uyguladığı sayısal sınırlara dayanır.

**Oran sınırı**: her istemcinin birim zamanda tükettiği iş, bir **token bucket** (token bucket) ile sınırlanır — kova sabit hızda dolar, her istek maliyetince jeton harcar, kovada yeterli jeton yoksa istek reddedilir. Ani bir yük patlaması böyle emilir. **Maliyet muhasebesi**: giriş ve çıkış token sayıları birim fiyatla çarpılıp istemci başına toplanır; bu, hem bütçeyi izlemenin hem de bir istemcinin anormal maliyetini görmenin yoludur. **Üretim bütçesi**: her isteğin `num_predict`'i, istenen değer ile hesabın kalan bütçesi ve katı bir üst sınırın **en küçüğüne** kısılır; bütçe tükendiyse istek reddedilir. Bu sayede ele geçirilmiş ya da kötü niyetli bir istek bile sabit bir tavanın ötesine geçemez.
:::

::: anlat Ölçüm gerçek token ve maliyet üzerinden yapılır
Bu savunmanın değeri ölçülebilir olmasıdır. Aynı pahalı istek önce bütçesiz (yüksek `num_predict`), sonra bütçe-kısıtlı `num_predict` ile gerçek modele gönderilir; üretilen gerçek token sayısı ve bunun parasal karşılığı karşılaştırılır. Bütçe sınırı üretimi `done_reason="length"` ile keser: üretilen token sayısı asla tavanı aşamaz. Böylece "bütçe işe yarıyor" bir temenni değil, gerçek bir token/maliyet düşüşüdür.

İlk üç görevdeki kullanım dosyaları sentetiktir; setup ile çalışma dizinine kopyalanır ve başlangıç kodları bu dosyaları okur. Kalıcılık yoktur; aynı çalıştırmada bellekte kopyayı değiştirerek dene. Son görev gerçek yerel modeli çağırır; model/sürüm, istek, ayarlar ve gerçek tüketim kanıta yazılır. Bütçeli çağrının tavanı kesmesi bu deneyde denetlenir; doğal olarak erken biten başka bir istemin mutlaka length ile sonlanacağı iddia edilmez.
:::

::: anlat Dosyadan gerçek çağrı bütçesine
Bir servisin tüketim savunmasını yalnız modele kısa cevap vermesini söyleyerek kuramazsın. Model talimata uymayabilir, uzun girdinin işlenmesi zaten kaynak harcayabilir veya ajan aynı işi çok kez çağırabilir. Bu ders üç farklı katmanı ayırır: isteğin kabul edilme hızını sınırlamak, kullanımı muhasebeleştirmek ve bir üretim çağrısının çıkış tavanını uygulamak. Bunlardan biri diğerinin yerine geçmez. Yerel modelde gerçek API ücreti ödemesen de GPU zamanı, bellek ve başka kullanıcıların bekleme süresi sınırlı kaynaklardır. Dersin parasal fiyatları bu yüzden sentetik bir muhasebe örneğidir, gerçek tarife değildir.

Jeton muhasebesinde sayısal temsil de bir güvenlik sınırıdır. Binary64'te 2**54 değerinden 1 çıkarmak aynı float değere yuvarlanabilir: ilk istek maliyet 1'i tüketse de ikinci istek bütün kapasiteyi hâlâ harcayabilir. Referans çözüm kapasite ve harcamaları int, verilen int/float dolum hızını Fraction ile tam rasyonel tutar; bu yüzden küçük harcama kaybolmaz. Fraction(float), verilen binary64 hızının tam değerini korur; yeni bir fiyat ya da ondalık yuvarlama kuralı uydurmaz.

İlk görev `veri/istekler.json` dosyasındaki zaman ve maliyet çiftlerini okur. Buradaki token bucket jetonunu LLM'in metin tokenıyla karıştırma; kova bir istek maliyetini temsil eden soyut birimdir. Zaman milisaniye, dolum hızı milisaniye başına jetondur. İlk istekten önce sonsuz süre geçtiğini varsayıp kapasitenin üstünde birikim yapma; kova dolu başlar ve kapasiteyi aşmaz. Aynı zaman damgasındaki istekler arasında dolum yoktur. Reddedilen istekte jeton harcamamak önemlidir: aksi hâlde saldırgan başarısız isteklerle bile kovayı boş tutabilir. Başlangıç kodundaki kusuru görünür isteklerin karar sırasıyla karşılaştırarak bul.

İkinci görev `veri/kullanim.json` dosyasında giriş ve çıkış tokenlarını ayrı fiyatlarla hesaplar. Fiyat birimi bin token başınadır; bine bölmeyi atlamak sonucu bin kat büyütür. İstemci başına toplam ile genel toplamı ayrı tut. Her satırda yuvarlayıp sonra toplamak, en sonda yuvarlamayla aynı sonucu vermeyebilir; ham ara toplamları koru. Sıfır token veya sıfır fiyat geçerlidir. Bu muhasebe fonksiyonu kendi başına yeni bir çağrıyı durdurmaz; yalnız kullanımın nasıl hesaplandığını gösterir. Gerçek bir hesap bütçesinde kabul, rezervasyon ve harcama güncellemesinin atomik uygulanması gerekir. Örneğin kalan=32'yi aynı anda okuyan iki çağrı ayrı ayrı 32 planlarsa toplam 64 üretebilir. Kabul sırasında kullanılabilir bütçeyi rezervasyon kadar azalt; bitişte gerçek kullanımı mahsup edip kullanılmayan rezervasyonu geri ver. Bu ders tek liste/tek çağrı hesabıdır; bu sunucu işlemini veya dağıtık state deposunu kurmaz.

Üçüncü görev `veri/butce.json` içindeki istenen üretim, kalan hesap bütçesi ve katı tavanı okur. Kalan bütçe sıfırsa istek reddedilir; bu durumda num_predict sıfır sonucunu modele üretim ayarı olarak göndermek yerine çağrıyı hiç yapmamak gerekir. Kalan bir olduğunda ise izin verilip en fazla bir token ayrılır. İstenen, kalan ve tavanın her birinin en küçük olduğu örnekleri ayrı dene. Bool Python'da int alt türü olsa da bir token bütçesi olarak kabul edilmez. Başlangıç kodu çalışan ama bir sınırı atlayan bir politika içerir; yalnız görünür örneği geçmesi yeterli değildir.

Son görev öğrencinin hesapladığı planı gerçek Ollama çağrısına bağlar. Aynı uzun sayma isteği önce yüksek num_predict, sonra bütçeli değerle gönderilir. Buradaki bütçesiz adı sınırsız bir çağrı demek değildir; karşılaştırma kolunun da 512 çıkış tokenı tavanı vardır. Bütçeli kol 32 tokenla sınırlanır. Sunucu gerçek eval_count ve done_reason alanlarını verir; length üretim tavanında kesilmeyi gösterir. Metin karakterlerini saymak tokenizer çıktısını saymakla aynı değildir. Bu özel istem için üretimin kesildiği ölçülür; başka bir kısa yanıtın doğal bitişi bütçe hatası anlamına gelmez.

Saldırgan çok sayıda eşzamanlı istek, çok uzun giriş veya tekrar eden araç döngüsüyle başka tüketim yolları arayabilir. Bu dersin son canlı adımı yalnız tek isteğin çıkış planını ve gerçek token tüketimini sınar. İlk görevdeki kova tek çağrıdaki liste simülasyonudur; dağıtık istemci durum deposu veya atomik sunucu kotası kurulmuş değildir. Bu sınırları gizlemek yerine çıktıyla birlikte yaz. Modelin işbirliğine bağlı olmayan sayısal tavanı doğrula; daha az tokenın bütün saldırı yüzeyini kapattığını iddia etme. Yalnız laboratuvarın başlattığı kaynaklar temizlenir; kullanıcının Ollama sunucusu veya önceden yüklü modeli kapatılmaz.
:::

::: tahmin token bucket, maliyet ve bütçe kısıtı çıktısını tahmin et
Üç çıktı satırını yaz:

```python
# sentetik kullanım kaydı (fixture)
kayitlar = [{"istemci": "a", "giris_token": 1200, "cikis_token": 300},
            {"istemci": "a", "giris_token": 800, "cikis_token": 1500}]
toplam = round(sum(k["giris_token"] / 1000 * 0.05 + k["cikis_token"] / 1000 * 0.15 for k in kayitlar), 6)
print(toplam)
kova, dolum, son = 10.0, 1.0, 0
for t, maliyet in [(0, 5), (2, 5), (3, 5)]:
    kova = min(10.0, kova + (t - son) * dolum); son = t
    print("izin" if kova >= maliyet else "red", end=" ")
    if kova >= maliyet:
        kova -= maliyet
print()
print(min(512, 32, 256))
```

???

```cikti
0.37
izin izin red 
32
```

İlk satır iki isteğin parasal maliyetidir: giriş 2000 token × 0.05/1k + çıkış 1800 token × 0.15/1k = 0.10 + 0.27 = 0.37. İkinci satır token bucket: kova 10 jetonla başlar, ilk iki istek (maliyet 5) geçer, üçüncüde kovada yalnız 3 jeton kalır (2 ms'de 2 jeton doldu) ve istek reddedilir — ani yük emilir. Üçüncü satır bütçe kısıtı: istenen 512, kalan bütçe 32 ve katı tavan 256'nın en küçüğü 32; üretim en çok 32 tokenla sınırlanır.
:::

::: gorev 1 · token bucket ile oran sınırla
`jeton_kovasi(istekler, kapasite, dolum_hizi)` işlevini yaz. `istekler` 1–1000 öğeli listedir; her öğe `[zaman, maliyet]` listesidir; `zaman` bool olmayan negatif olmayan tamsayı ve liste boyunca azalmaz, `maliyet` bool olmayan ≥1 tamsayıdır. `kapasite` bool olmayan ≥1 tamsayı, `dolum_hizi` bool olmayan sonlu pozitif sayıdır (ms başına dolan jeton). Geçersiz veride `ValueError` yükselt.

Kova `kapasite` kadar **dolu** başlar. Her istekte: son istekten bu yana geçen süre kadar jeton ekle (`(zaman - son_zaman) * dolum_hizi`), kovayı `kapasite` ile sınırla; `son_zaman`'ı güncelle. Kovada en az `maliyet` jeton varsa `"izin"` ver ve o kadar jeton harca; yoksa `"red"` (jeton harcanmaz). Kararları sırayla liste döndür.

```starter
import math

def jeton_kovasi(istekler, kapasite, dolum_hizi):
    if not isinstance(istekler, list) or not 1 <= len(istekler) <= 1000:
        raise ValueError("istekler boş olmayan ve uzunluk sınırına uyan liste olmalı")
    onceki = -1
    for oge in istekler:
        if not isinstance(oge, list) or len(oge) != 2:
            raise ValueError("her istek [zaman, maliyet] olmalı")
        z, m = oge
        if isinstance(z, bool) or not isinstance(z, int) or z < 0 or z < onceki:
            raise ValueError("zaman azalmayan negatif olmayan tamsayı olmalı")
        if isinstance(m, bool) or not isinstance(m, int) or m < 1:
            raise ValueError("maliyet pozitif tamsayı olmalı")
        onceki = z
    if isinstance(kapasite, bool) or not isinstance(kapasite, int) or kapasite < 1:
        raise ValueError("kapasite pozitif tamsayı olmalı")
    if isinstance(dolum_hizi, bool) or not isinstance(dolum_hizi, (int, float)) or not math.isfinite(dolum_hizi) or dolum_hizi <= 0:
        raise ValueError("dolum_hizi pozitif sonlu sayı olmalı")
    kova, son, sonuc = float(kapasite), None, []
    for z, m in istekler:
        if son is not None:
            kova = min(float(kapasite), kova + (z - son) * dolum_hizi)
        son = z
        # KUSURLU BAŞLANGIÇ KODU: tam maliyet kadar jeton olduğunda gereksiz red veriyor.
        if kova > m:
            sonuc.append("izin")
            kova -= m
        else:
            sonuc.append("red")
    return sonuc

from ai_savunma_veri import json_yukle
print(jeton_kovasi(**json_yukle("veri/istekler.json")))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-31")
```

```test
def sozlesme(fn):
    try:
        if fn([[0, 5], [2, 5], [3, 5], [10, 5]], 10, 1) != ["izin", "izin", "red", "izin"]:
            return False
        if fn([[0, 10], [0, 1]], 10, 1) != ["izin", "red"] or fn([[0, 20]], 10, 1) != ["red"]:
            return False
        if fn([[0, 3], [1, 3], [2, 3]], 3, 3) != ["izin", "izin", "izin"]:
            return False
        if fn([[0,1],[0,2**54]],2**54,1)!=["izin","red"]:return False
        if fn([[0,2**53+1]],2**53+1,1)!=["izin"]:return False
        if fn([[0,1],[1,1]],1,10**400)!=["izin","izin"]:return False
        if fn([[0,1],[10**400,1]],1,1)!=["izin","izin"]:return False
        baz = [[0, 1]]
        for kotu in [(None, 10, 1), ([], 10, 1), ("x", 10, 1), ([[0, 1, 1]], 10, 1), ([["0", 1]], 10, 1), ([[0, 0]], 10, 1),
                     ([[0, 1.0]], 10, 1), ([[-1, 1]], 10, 1), ([[True, 1]], 10, 1), ([[1, 1], [0, 1]], 10, 1),
                     (baz, 0, 1), (baz, True, 1), (baz, 1.0, 1), (baz, 10, 0), (baz, 10, -1), (baz, 10, True), (baz, 10, "x"), (baz, 10, float("inf"))]:
            try:
                fn(*kotu)
                return False
            except ValueError:
                pass
        # Alt/üst uzunluk, kesirli dolum ve tam kapasite sınırları.
        if fn([[0, 1]], 1, 0.5) != ["izin"] or fn([[0,1],[1,1],[2,1]],1,0.5) != ["izin","red","izin"]:
            return False
        if fn([[0, 1]] * 1000, 1, 1) != ["izin"] + ["red"] * 999:
            return False
        for args in [([(0,1)],1,1), ([[0,1]]*1001,1,1), ([[0,True]],1,1), ([[0,1]],1,float("nan"))]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(jeton_kovasi), "jeton kovası oran sınırı doğru; geçersiz girdi reddedilmeli")
def m_dolum(i, k, d):
    kova, son, out = float(k), None, []
    for t, m in i:
        son = t
        out.append("izin" if kova >= m else "red")
        if kova >= m:
            kova -= m
    return out  # dolum yok
def m_tavan(i, k, d):
    kova, son, out = float(k), 0, []
    for t, m in i:
        kova = kova + (t - son) * d; son = t  # kapasiteyle sınırlanmıyor
        out.append("izin" if kova >= m else "red")
        if kova >= m:
            kova -= m
    return out
def m_red(i, k, d):
    kova, son, out = float(k), 0, []
    for t, m in i:
        kova = min(float(k), kova + (t - son) * d); son = t
        karar = "izin" if kova >= m else "red"
        kova -= m  # red bile harcıyor
        out.append(karar)
    return out
for ad, mut in [("dolumu yok sayan", m_dolum), ("kapasiteyle sınırlamayan", m_tavan), ("reddi de harcayan", m_red)]:
    ok(not sozlesme(mut), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
import math

def jeton_kovasi(istekler, kapasite, dolum_hizi):
    if not isinstance(istekler, list) or not 1 <= len(istekler) <= 1000:
        raise ValueError("istekler boş olmayan ve uzunluk sınırına uyan liste olmalı")
    onceki = -1
    for oge in istekler:
        if not isinstance(oge, list) or len(oge) != 2:
            raise ValueError("her istek [zaman, maliyet] olmalı")
        z, m = oge
        if isinstance(z, bool) or not isinstance(z, int) or z < 0 or z < onceki:
            raise ValueError("zaman azalmayan negatif olmayan tamsayı olmalı")
        if isinstance(m, bool) or not isinstance(m, int) or m < 1:
            raise ValueError("maliyet pozitif tamsayı olmalı")
        onceki = z
    if isinstance(kapasite, bool) or not isinstance(kapasite, int) or kapasite < 1:
        raise ValueError("kapasite pozitif tamsayı olmalı")
    if isinstance(dolum_hizi, bool) or not isinstance(dolum_hizi, (int, float)) or (isinstance(dolum_hizi, float) and not math.isfinite(dolum_hizi)) or dolum_hizi <= 0:
        raise ValueError("dolum_hizi pozitif sonlu sayı olmalı")
    from fractions import Fraction
    hiz = Fraction(dolum_hizi)  # Verilen int/float hızının tam rasyonel değeri.
    kova, son, sonuc = kapasite, None, []
    for z, m in istekler:
        if son is not None:
            kova = min(kapasite, kova + (z - son) * hiz)
        son = z
        if kova >= m:
            sonuc.append("izin")
            kova -= m
        else:
            sonuc.append("red")
    return sonuc

from ai_savunma_veri import json_yukle
print(jeton_kovasi(**json_yukle("veri/istekler.json")))
```

```hint
Kova dolu başlar; her istekte önce geçen süre kadar jeton ekle ama `kapasite`'yi aşma (`min`). Yalnız izin verilen istek jeton harcar — reddedilen istek kovayı boşaltmaz, yoksa saldırgan kovayı sürekli boş tutar. İlk istekte eklenecek süre yoktur.
```
:::

::: gorev 2 · Token maliyetini hesapla (denial-of-wallet muhasebesi)
`maliyet_hesapla(kayitlar, giris_1k, cikis_1k)` işlevini yaz. `kayitlar` 1–1000 öğeli listedir; her öğe tam `istemci` (boş olmayan str), `giris_token`, `cikis_token` (bool olmayan negatif olmayan tamsayı) anahtarlı sözlüktür. `giris_1k` ve `cikis_1k` bool olmayan negatif olmayan sayılardır (1000 token başına birim fiyat). Geçersiz veride `ValueError` yükselt.

Bir kaydın maliyeti `giris_token / 1000 * giris_1k + cikis_token / 1000 * cikis_1k`'tir. `{"toplam": bütün kayıtların maliyet toplamı (round 6), "istemci": {istemci: o istemcinin maliyet toplamı (round 6)}}` döndür.

```starter
import math

def maliyet_hesapla(kayitlar, giris_1k, cikis_1k):
    if not isinstance(kayitlar, list) or not 1 <= len(kayitlar) <= 1000:
        raise ValueError("kayıtlar boş olmayan ve uzunluk sınırına uyan liste olmalı")
    for x in kayitlar:
        if not isinstance(x, dict) or set(x) != {"istemci", "giris_token", "cikis_token"} \
                or not isinstance(x["istemci"], str) or not x["istemci"] \
                or any(isinstance(x[a], bool) or not isinstance(x[a], int) or x[a] < 0 for a in ("giris_token", "cikis_token")):
            raise ValueError("kayıt istemci(str), giris_token, cikis_token(int≥0) içermeli")
    for ad, v in (("giris_1k", giris_1k), ("cikis_1k", cikis_1k)):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
            raise ValueError(f"{ad} negatif olmayan sonlu sayı olmalı")
    # KUSURLU BAŞLANGIÇ KODU: giriş ve çıkış birim fiyatlarını ters kullanıyor.
    istemci = {}
    for x in kayitlar:
        bedel = x["giris_token"] / 1000 * cikis_1k + x["cikis_token"] / 1000 * giris_1k
        istemci[x["istemci"]] = istemci.get(x["istemci"], 0) + bedel
    istemci = {i: round(v, 6) for i, v in istemci.items()}
    return {"toplam": round(sum(x["giris_token"] / 1000 * cikis_1k + x["cikis_token"] / 1000 * giris_1k for x in kayitlar), 6),
            "istemci": istemci}

from ai_savunma_veri import json_yukle
print(maliyet_hesapla(**json_yukle("veri/kullanim.json")))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-31")
```

```test
def k(i, g, c):
    return {"istemci": i, "giris_token": g, "cikis_token": c}
def sozlesme(fn):
    try:
        r = fn([k("a", 1200, 300), k("a", 800, 1500), k("b", 1000, 0)], 0.05, 0.15)
        if r != {"toplam": round(0.1 + 0.27 + 0.05, 6), "istemci": {"a": round(0.37, 6), "b": round(0.05, 6)}}:
            return False
        if fn([k("x", 0, 0)], 0.05, 0.15) != {"toplam": 0.0, "istemci": {"x": 0.0}}:
            return False
        for kotu in [(None, 0.05, 0.15), ([], 0.05, 0.15), ([k("a", 1, 1)], -1, 0.15), ([k("a", 1, 1)], 0.05, -1),
                     ([{"istemci": "a", "giris_token": 1}], 0.05, 0.15), ([k("", 1, 1)], 0.05, 0.15), ([k("a", -1, 1)], 0.05, 0.15),
                     ([k("a", True, 1)], 0.05, 0.15), ([k("a", 1.0, 1)], 0.05, 0.15), ([k("a", 1, 1)], True, 0.15), ([k("a", 1, 1)], "x", 0.15)]:
            try:
                fn(*kotu)
                return False
            except ValueError:
                pass
        # Boş olmayan liste üst sınırı, sıfır fiyat ve ayrı token alanları.
        # Yuvarlama hassasiyeti: yedi basamakla raporlayan çözüm de yanlış.
        if fn([k("x",1,0)],0.1234567,0) != {"toplam":0.000123,"istemci":{"x":0.000123}}:
            return False
        if fn([k("x",1,0)]*1000,1,2) != {"toplam":1.0,"istemci":{"x":1.0}}:
            return False
        if fn([k("x",1000,2000)],0,0) != {"toplam":0.0,"istemci":{"x":0.0}}:
            return False
        if fn([k("x",1000,2000)],0,1) != {"toplam":2.0,"istemci":{"x":2.0}} or fn([k("x",1000,2000)],1,0) != {"toplam":1.0,"istemci":{"x":1.0}}:
            return False
        for args in [([k("x",1,0)]*1001,1,2), ([k("x",0,True)],1,2), ([k("x",0,-1)],1,2), ([k("x",0,1.0)],1,2), ([dict(k("x",1,0),ek=1)],1,2), ([k(1,1,0)],1,2), ([None],1,2), ([k("x",1,0)],1,True),
                     ([k("x",1,0)],float("nan"),1), ([k("x",1,0)],1,float("nan")), ([k("x",1,0)],float("inf"),1), ([k("x",1,0)],1,float("inf"))]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(maliyet_hesapla), "token maliyeti ve istemci başına toplam doğru; geçersiz girdi reddedilmeli")
def m_swap(ka, g, c):
    r = maliyet_hesapla(ka, c, g)  # giriş/çıkış fiyatı ters
    return r
def m_bolme(ka, g, c):
    top, ist = 0.0, {}
    for x in ka:
        d = x["giris_token"] * g + x["cikis_token"] * c  # /1000 yok
        top += d; ist[x["istemci"]] = round(ist.get(x["istemci"], 0) + d, 6)
    return {"toplam": round(top, 6), "istemci": ist}
for ad, mut in [("giriş/çıkış fiyatını değiştiren", m_swap), ("1000'e bölmeyen", m_bolme)]:
    ok(not sozlesme(mut), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
import math

def maliyet_hesapla(kayitlar, giris_1k, cikis_1k):
    if not isinstance(kayitlar, list) or not 1 <= len(kayitlar) <= 1000:
        raise ValueError("kayıtlar boş olmayan ve uzunluk sınırına uyan liste olmalı")
    for x in kayitlar:
        if not isinstance(x, dict) or set(x) != {"istemci", "giris_token", "cikis_token"} \
                or not isinstance(x["istemci"], str) or not x["istemci"] \
                or any(isinstance(x[a], bool) or not isinstance(x[a], int) or x[a] < 0 for a in ("giris_token", "cikis_token")):
            raise ValueError("kayıt istemci(str), giris_token, cikis_token(int≥0) içermeli")
    for ad, v in (("giris_1k", giris_1k), ("cikis_1k", cikis_1k)):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
            raise ValueError(f"{ad} negatif olmayan sonlu sayı olmalı")
    istemci = {}
    for x in kayitlar:
        bedel = x["giris_token"] / 1000 * giris_1k + x["cikis_token"] / 1000 * cikis_1k
        istemci[x["istemci"]] = istemci.get(x["istemci"], 0) + bedel
    istemci = {i: round(v, 6) for i, v in istemci.items()}
    return {"toplam": round(sum(x["giris_token"] / 1000 * giris_1k + x["cikis_token"] / 1000 * cikis_1k for x in kayitlar), 6),
            "istemci": istemci}

from ai_savunma_veri import json_yukle
print(maliyet_hesapla(**json_yukle("veri/kullanim.json")))
```

```hint
Her kaydın maliyeti giriş ve çıkış tokenlarının **ayrı** fiyatlarla (çıkış genelde daha pahalı) 1000'e bölünüp çarpılmasıdır. İstemci başına toplamı bir sözlükte biriktir; yuvarlamayı en sonda yap ki ara toplamlar kaymasın.
```
:::

::: gorev 3 · Üretimi bütçeyle kıs (num_predict tavanı)
`butce_num_predict(istenen, kalan, tavan)` işlevini yaz. `istenen` bool olmayan ≥1 tamsayı (isteğin istediği üst üretim), `kalan` bool olmayan ≥0 tamsayı (hesabın kalan token bütçesi), `tavan` bool olmayan ≥1 tamsayıdır (istek başına katı üst sınır). Geçersiz veride `ValueError` yükselt.

`kalan < 1` ise `{"karar": "red", "neden": "bütçe tükendi", "num_predict": 0}`. Aksi hâlde `{"karar": "izin", "neden": "bütçe uygulandı", "num_predict": min(istenen, kalan, tavan)}`.

```starter
def butce_num_predict(istenen, kalan, tavan):
    if isinstance(istenen, bool) or not isinstance(istenen, int) or istenen < 1:
        raise ValueError("istenen pozitif tamsayı olmalı")
    if isinstance(kalan, bool) or not isinstance(kalan, int) or kalan < 0:
        raise ValueError("kalan negatif olmayan tamsayı olmalı")
    if isinstance(tavan, bool) or not isinstance(tavan, int) or tavan < 1:
        raise ValueError("tavan pozitif tamsayı olmalı")
    if kalan < 1:
        return {"karar": "red", "neden": "bütçe tükendi", "num_predict": 0}
    # KUSURLU BAŞLANGIÇ KODU: katı istek tavanını üretim planına katmıyor.
    return {"karar": "izin", "neden": "bütçe uygulandı", "num_predict": min(istenen, kalan)}

from ai_savunma_veri import json_yukle
print(butce_num_predict(**json_yukle("veri/butce.json")))
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_savunma_veri import hazirla
hazirla("ai-savunma-31")
```

```test
def sozlesme(fn):
    try:
        if fn(512, 32, 256) != {"karar": "izin", "neden": "bütçe uygulandı", "num_predict": 32}:
            return False
        if fn(100, 500, 256) != {"karar": "izin", "neden": "bütçe uygulandı", "num_predict": 100}:
            return False
        if fn(512, 500, 256) != {"karar": "izin", "neden": "bütçe uygulandı", "num_predict": 256}:
            return False
        if fn(512, 0, 256) != {"karar": "red", "neden": "bütçe tükendi", "num_predict": 0}:
            return False
        for kotu in [(0, 32, 256), (512, -1, 256), (512, 32, 0), (True, 32, 256), (512, True, 256), (512, 32, True),
                     (1.0, 32, 256), (512, 1.0, 256), (512, 32, 1.0), ("512", 32, 256)]:
            try:
                fn(*kotu)
                return False
            except ValueError:
                pass
        # Her sınır ayrı ayrı bir olduğunda izin verilmeli; kalan=0 reddedilmeli.
        for args in [(1,1,1),(1,9,8),(9,1,8),(9,8,1)]:
            if fn(*args) != {"karar":"izin","neden":"bütçe uygulandı","num_predict":1}:
                return False
        return True
    except Exception:
        return False
ok(sozlesme(butce_num_predict), "bütçe-kısıtlı num_predict ve bütçe tükenmesi doğru; geçersiz girdi reddedilmeli")
def m_tavan(i, k, t):
    r = butce_num_predict(i, k, t)
    if r["karar"] == "izin":
        r["num_predict"] = min(i, k)  # tavanı yok sayar
    return r
def m_kalan(i, k, t):
    r = butce_num_predict(i, k, t)
    if r["karar"] == "izin":
        r["num_predict"] = min(i, t)  # kalan bütçeyi yok sayar
    return r
def m_red(i, k, t):
    return {"karar": "izin", "neden": "bütçe uygulandı", "num_predict": min(i, max(k, 1), t)}  # bütçe tükenmesini atlar
for ad, mut in [("tavanı yok sayan", m_tavan), ("kalan bütçeyi yok sayan", m_kalan), ("bütçe tükenmesini atlayan", m_red)]:
    ok(not sozlesme(mut), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def butce_num_predict(istenen, kalan, tavan):
    if isinstance(istenen, bool) or not isinstance(istenen, int) or istenen < 1:
        raise ValueError("istenen pozitif tamsayı olmalı")
    if isinstance(kalan, bool) or not isinstance(kalan, int) or kalan < 0:
        raise ValueError("kalan negatif olmayan tamsayı olmalı")
    if isinstance(tavan, bool) or not isinstance(tavan, int) or tavan < 1:
        raise ValueError("tavan pozitif tamsayı olmalı")
    if kalan < 1:
        return {"karar": "red", "neden": "bütçe tükendi", "num_predict": 0}
    return {"karar": "izin", "neden": "bütçe uygulandı", "num_predict": min(istenen, kalan, tavan)}

from ai_savunma_veri import json_yukle
print(butce_num_predict(**json_yukle("veri/butce.json")))
```

```hint
Üç sınırın (`istenen`, `kalan`, `tavan`) **en küçüğü** üretimi belirler; herhangi birini atlamak kapıyı açar. Önce bütçe tükendi mi (`kalan < 1`) diye bak, sonra `min` ile kıs. `bool`'u `int`'ten önce ele.
```
:::

::: anlat Gerçek modelde bütçesiz vs bütçeli tüketim
Bu deneyde pahalı bir istek ("1'den 400'e kadar say") gerçek yerel modele iki kez gönderilir: önce bütçesiz (yüksek `num_predict`), sonra senin `butce_uygula` işlevinin verdiği bütçe-kısıtlı `num_predict` ile. Deney her iki koşunun gerçek üretilen token sayısını, bitiş nedenini ve sentetik bir fiyatla maliyetini ölçer; bütçe sınırının üretimi gerçekten kestiğini (`done_reason="length"`, token ≤ tavan) doğrular. Böylece denial-of-wallet savunmasının soyut değil, ölçülen bir token/maliyet düşüşü olduğunu görürsün. Model bu deney tarafından yüklendiyse sonunda boşaltılır.
:::

::: gorev Gerçek deney · Bütçeyi uygula, gerçek tüketimi ölç
`butce_uygula(istenen, kalan, tavan)` işlevini yaz. Doğrulama ve davranış görev 3'teki `butce_num_predict` ile aynıdır: `istenen` (≥1), `kalan` (≥0), `tavan` (≥1) bool olmayan tamsayılar; geçersizde `ValueError`. `kalan < 1` ise `{"karar": "red", "neden": "bütçe tükendi", "num_predict": 0}`, aksi hâlde `{"karar": "izin", "neden": "bütçe uygulandı", "num_predict": min(istenen, kalan, tavan)}` döndür.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def butce_uygula(istenen, kalan, tavan):
    return {}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_31 as deney
    deney.goster(butce_uygula)
```

```test
import ai_lab
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
import ast
YASAK = ("referans", "referans_butce", "getattr", "kanit_yaz")
sorun = ai_lab.kod_denetimi(src, YASAK)
for dugum in ast.walk(ast.parse(src)):
    if isinstance(dugum, ast.ImportFrom):
        if any(ad.name in YASAK or ad.name == "*" for ad in dugum.names):
            sorun.append("referans veya kanıt yazıcısı içe aktarılamaz")
kontrol(not sorun, "laboratuvar yamalanmamalı, referans kullanılmamalı " + ", ".join(sorun))
if sorun:
    stop()
fn = need("butce_uygula")
from sandbox import ai_gercek_ai_savunma_31 as D
def sozlesme(f):
    try:
        for a, b, c in [(512, 32, 256), (100, 500, 256), (512, 500, 256), (512, 0, 256), (1, 1, 1)]:
            if f(a, b, c) != D.referans_butce(a, b, c):
                return False
        for kotu in [(0, 32, 256), (512, -1, 256), (512, 32, 0), (True, 32, 256), (512, True, 256), (512, "x", 256), (1.0, 32, 256), (512, 32, True), (512, 32, "x")]:
            try:
                f(*kotu)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(fn), "bütçe-kısıtlı num_predict doğru; geçersiz girdi reddedilmeli")
for ad, kw in [("katı tavanı yok sayan", {"tavan_yok": True}), ("kalan bütçeyi yok sayan", {"butce_yok": True})]:
    kontrol(not sozlesme(lambda a, b, c, kw=kw: D.referans_butce(a, b, c, **kw)), "hatalı çözüm reddedilmeli: " + ad)
r, oz = None, None
if all(sonuclar):
    try:
        r = D.deney(fn)
    except ai_lab.GercekLabYok as e:
        kontrol(False, f"GERÇEK MODEL YOK, deney yapılmadı: {e}")
        stop()
    kontrol(r["plan"]["num_predict"] == min(D.BUTCESIZ_TAVAN, D.KALAN_BUTCE, D.SERT_TAVAN),
            f"bütçe planı en küçük sınıra kısıldı: num_predict {r['plan']['num_predict']}")
    gecerli = [k for k in r["kayitlar"] if k.get("hata") is None]
    kontrol(len(gecerli) == 2, f"iki koşu da gerçek yanıt verdi ({len(gecerli)}/2)")
    oz = D.ozet(r)
    kontrol(oz["butceli_token"] <= r["plan"]["num_predict"] and oz["butceli_kesildi"],
            f"bütçe üretimi gerçekten kesti: {oz['butceli_token']} token ≤ {r['plan']['num_predict']} (done=length)")
    kontrol(oz["butcesiz_token"] > oz["butceli_token"], f"bütçe tüketimi düşürdü: {oz['butcesiz_token']} → {oz['butceli_token']} token")
yol = ai_lab.kanit_yaz("savunma-butce", {"kaynak": "gercek", "kabul": all(sonuclar), "ders": "ai-savunma-31",
                                         "ortam": (r or {}).get("ortam"), "deney": r, "ozet": oz})
if oz:
    ok(True, f"BULGU ({r['ortam']['model']['ad']}): pahalı istek bütçesiz {oz['butcesiz_token']} token (maliyet {oz['butcesiz_maliyet']}), "
             f"bütçeli {oz['butceli_token']} token (maliyet {oz['butceli_maliyet']}); {oz['token_dususu']} token daha az, bütçe kesti: {oz['butceli_kesildi']}. "
             f"Bu deneyde tek çağrının çıkış token tavanı uygulandı; servis çapındaki diğer tüketim yolları ayrıca sınırlandırılmalıdır.")
```

```solution
import ai_lab

def butce_uygula(istenen, kalan, tavan):
    if isinstance(istenen, bool) or not isinstance(istenen, int) or istenen < 1:
        raise ValueError("istenen pozitif tamsayı olmalı")
    if isinstance(kalan, bool) or not isinstance(kalan, int) or kalan < 0:
        raise ValueError("kalan negatif olmayan tamsayı olmalı")
    if isinstance(tavan, bool) or not isinstance(tavan, int) or tavan < 1:
        raise ValueError("tavan pozitif tamsayı olmalı")
    if kalan < 1:
        return {"karar": "red", "neden": "bütçe tükendi", "num_predict": 0}
    return {"karar": "izin", "neden": "bütçe uygulandı", "num_predict": min(istenen, kalan, tavan)}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_savunma_31 as deney
    deney.goster(butce_uygula)
```

```hint
Üretim bütçesi üç sınırın en küçüğüdür: isteğin istediği, hesabın kalanı ve katı tavan. Bu sayı `num_predict` olarak modele verilince üretim o tokenda kesilir (`done_reason="length"`) ve pahalı bir istek bile sabit bir tavanı aşamaz.
```
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
Token bucket kapasite ve yenileme hızıyla kısa süreli burst ile uzun dönem oranı ayırır. Maliyet hesabında giriş ve çıkış fiyatlarını ayrı tut; sonra izin verilen num_predict değerini istek, tavan ve kalan bütçenin minimumundan çıkar. Gerçek eval_count tavan denetimini kanıtlar. Yerel sentetik fiyatla hesaplanan para, güncel bulut faturası değildir; giriş uzunluğu ve eşzamanlılık ayrıca sınırlanır.

Önkoşul ve yol köprüsü: ai-saldiri-40 Denial-of-Wallet.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| Bir çıkış tavanı bütün tüketim riskini kapatır | Prefill, eşzamanlılık ve ajan döngüsü farklı bütçeler ister |

Dinleyiciye sor: Savunma güvenlik metriğini iyileştirirken meşru kullanıma ne kaybettirebilir? Ham çıktı ve ölçüm paydalarıyla cevapla.
:::


::: anlat Birincil kaynak ve deney sınırı
[OWASP LLM10:2025 Unbounded Consumption](https://genai.owasp.org/llmrisk/llm102025-unbounded-consumption/): Kontrolsüz inference tüketimi için risk referansı. Bu dersin fiyat/bütçe değerleri sentetik eğitim girdisidir, güncel hizmet teklifi değildir. Çalışan sürüm ve gerçek sonuç kanıtta kayıtlıdır.
:::
