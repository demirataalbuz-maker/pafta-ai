---
id: ai-temel-20
title: "Inference Gözlemlenebilirliği ve Kötüye Kullanım Kayıtları"
summary: Bearer başlığını katı ayrıştırıp özeti saklanan anahtarla sabit zamanlı doğrula, anahtar başına token bucket ile 429 ve Retry-After üret, bellek içi istek penceresinden HMAC takma adlı kötüye kullanım alarmları çıkar; son adımda gerçek yerel trafikten gizliliği koruyan istek kayıtları üret.
esleme: ai-temel-16, ai-temel-17, ai-savunma-27
timeout: 45
---

::: anlat Kimlik ve hız sınırı isteği modele ulaşmadan durdurur

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Bir inference ağ geçidi kimlik, hız sınırı ve kayıt üretir | İlk üç görev görünür sentetik HTTP alanları, zamanlı olaylar ve HMAC alarmları | FastAPI üzerinde gerçek 401/429 ağ geçidi veya dağıtık kova çalıştırıldığı anlamına gelmez |
| Yerel model gerçek token ve gecikme ölçüleri verir | Final kurulu Ollama'ya altı gerçek istek ve sentetik sırlar üzerinde kayıt redaksiyonu | Genel kişisel veri tespiti, tam anonimlik veya üretim gizlilik kabulü değildir |

> [!NOT]
> `veri/trafik.json` elle hazırlanmış sentetik veridir; gerçek sunucu kaydı değildir. İlk üç görev aynı dosyayı okur. Setup her Run/Check için geçici kopya oluşturur; kalıcılık yoktur. Kaynak dosyayı editörle aç veya kodda yüklenen kopyayı değiştirip Run ile dene. Gizli testler ayrıdır. Final gerçek yerel modeli çağırır; hiçbir gerçek kullanıcı anahtarı veya özel dosya kullanmaz.

RFC 6750'ye göre bearer jetonu `Authorization: Bearer <b64token>` biçiminde gelir; dilbilgisi `"Bearer" 1*SP b64token` şeklindedir ve b64token yalnız ASCII harf, rakam, `-._~+/` karakterlerinden en az birini ve sonda isteğe bağlı `=` dolgusunu içerir. Şema adı büyük/küçük harf duyarsızdır (RFC 9110 §11.1), ama `Bearerabc` bearer kimliği değildir ve şemayı jetondan yalnız boşluk (SP) ayırır, sekme ayırmaz; baştaki ve sondaki boşluklar ise uygulamaya hiç ulaşmaz, çünkü RFC 9110 §5.5'e göre alan değeri onları içermez ve HTTP ayrıştırıcısı değeri değerlendirmeden önce atar. Hata yanıtları ayrışır: kimlik bilgisi hiç yoksa ya da başka bir şema kullanılmışsa `401` ve hata kodu taşımayan `WWW-Authenticate: Bearer`; biçimi bozuk istekte `400` ve `error="invalid_request"`; tanınmayan jetonda `401` ve `error="invalid_token"`; kimliği doğru ama yetkisi yetmeyen istekte `403` ve `error="insufficient_scope"`. Gerçek yanıtlar çoğu zaman `realm` parametresi de taşır; bu derste yalnız hata kodu tutulur. Sunucu anahtarın kendisini değil SHA-256 özetini saklar: rastgele üretilmiş yüksek entropili API anahtarı için hızlı özet yeterlidir (düşük entropili parolalar ise Argon2 ya da scrypt gibi tuzlu, yavaş türetme ister), böylece sızan bir veritabanı doğrudan kullanılabilir anahtar vermez.

Özetler `hmac.compare_digest` ile karşılaştırılır; Python belgeleri bu işlevin içeriğe bağlı erken çıkışı önleyecek biçimde tasarlandığını, farklı uzunlukta girdilerde yalnız tür ve uzunluk bilgisinin sızabileceğini söyler. Saldırgan özetin önekini seçemediği için özet karşılaştırması zaten zamanlama sızıntısını zayıflatır; bütün kayıtları eşleşme bulunduktan sonra da gezmek, hangi kaydın eşleştiğini süreden okumayı ayrıca zorlaştıran ek bir katmandır. Kimliği doğrulanan istek jeton kovasından geçer: kapasite kadar jeton birikebilir, her `aralik` milisaniyede bir jeton sürekli (kesirli olarak) dolar, her istek bir jeton harcar ve kova boşsa `429 Too Many Requests` (RFC 6585) döner. `Retry-After` alanı RFC 9110'a göre ya HTTP tarihi ya da negatif olmayan tamsayı saniyedir; bir jetonun dolmasına kalan süre yukarı yuvarlanır ki istemci erken dönüp yeniden reddedilmesin, reddedilen istek jeton harcamaz. Sınırın anahtarı da önemlidir: geçersiz jetonla gelen `401` fırtınasında geçerli anahtar yoktur, o yüzden istemci (IP ya da mTLS kimliği) başına sayılır; çalınmış bir anahtar ise yüzlerce IP'den kullanılabilir ve yalnız anahtar başına sınırla yakalanır, NAT arkasındaki çok sayıda meşru kullanıcıyı da salt IP sınırı cezalandırır. Bu derste saat okunmaz, zaman tamsayı milisaniye olarak verilir; çok kopyalı bir dağıtımda kova durumunun kopyalar arasında paylaşılan bir depoda tutulması gerekir.
:::

::: anlat Kayıt kötüye kullanımı göstermeli, ikinci bir sızıntı olmamalı

Önce `veri/trafik.json` dosyasını incele. `kimlik` bölümü örnek Authorization değeri, kayıt kimlikleri ve SHA256 özetlerini taşır. README'de yazan anahtar eğitim örneğidir, gerçek bir servise erişim sağlamaz. İlk görev başlığın biçimini ve kapsamını kontrol eder. `kova` bölümündeki zamanlı olaylar ikinci göreve gider; JSON dizilerini bu görevin istediği tuple biçimine dönüştürürsün. `alarmlar` aynı örnek anahtar ve istemci kimlikleriyle üçüncü görevin izleme penceresidir. Örnekte beş `401`, beş `429` ve üç normalize aynı istem ayrı sinyaller üretir; bir kayıt tek başına saldırının kanıtı değildir.

Bearer jetonu kimlik bilgisidir, kapsam ise izin verilen işlemdir. Tanınan bir anahtarın yetkisi yetersizse kimliği tanınmamış gibi davranmak veya izin vermek farklı hatalardır. Özetleri sabit zamanlı karşılaştırmak yalnız bu karşılaştırma işleminin içeriğe bağlı erken çıkışını azaltır; bütün HTTP hizmetinin süresini sabitlemez. Döngüde eşleşince çıkmamak da tüm programın yan kanal güvenliği kanıtı değildir. Hız sınırı ise kimlik doğrulamadan ayrı bir karardır. Sürekli dolan kova anlık patlamaya kapasite kadar izin verir; reddedilen bir istek fazladan jeton harcamamalıdır. `Retry-After` saniye birimindedir, olay zamanları milisaniyedir; birim karışıklığı istemciyi gereksiz yere bekletir veya erken tekrar ettirir.

Alarm kuralları bir izleme penceresi içindir; görev kendi kendine süre tutmaz veya dosyadan akış izlemeye başlamaz. `401` istemciye, `429` ve başarılı token tüketimi anahtara bağlanır. Aynı anahtar farklı istemcilerde kullanılsa da anahtar bazlı hız alarmında birleşir. Aynı IP arkasındaki farklı meşru anahtarlar ise birbirine karıştırılmamalıdır. Normalizasyon yalnız lower ve boşluk birleştirmedir; benzer anlamlı bütün istemleri yakalayan bir anlamsal tespit değildir. Tekrar alarmında aynı anahtarın en büyük istem grubu alınır, farklı grupların sayıları toplanmaz. Girdi sırasını ters çevirmen alarm sonucunu değiştirmemelidir.

Üçüncü görevde takma ad gerçek `HMAC-SHA256`'dır. Finaldeki mevcut eğitim sözleşmesi ise gizli önek ile anahtarın SHA-256 özetinin ilk 16 hanesini kullanır; bu HMAC değildir ve bir üretim önerisi gibi aktarılmamalıdır. Anahtarın kendisi yerine kısa bir kimlik yazmak kayıtları ilişkilendirir, anonimlik sağlamaz. Finalde kullanılan tuz ve tüm sırlar deneyin ürettiği sentetik değerlerdir. Tuzun herkesin bildiği sabit bir değer olması başka bir gizlilik varsayımıdır. Bu ayrımı kodda kullanılan algoritmanın adına bakarak doğrula; başlıkta hash yazması tek başına yeterli değildir.

Redaksiyon yalnız görevde açıkça verilen üç regex desenini uygular. Anahtar deseni önce çalışır; uzun rakam içeren bir anahtarın parçası yanlışlıkla numara sayılmaz. Ardından e-posta ve 12 ve üzeri rakam dizileri işlenir. İstem uzunluğu ham metinden hesaplanır; redakte metnin uzunluğu değildir. Regex dışında yazılmış bir sır gözden kaçabilir. Dolayısıyla bu deneyde sızıntı yok sonucu sadece üretilen sentetik örneklere ve belirtilen desenlere aittir; sınırsız kişisel veri temizleme garantisi değildir. Kimlik özeti alanında dahi ham anahtar görünmemelidir. Girdiyi yerinde değiştirmek sonraki doğrulama için ham örneği kaybettireceğinden yasaktır.

Gerçek final altı yerel model çağrısının token, gecikme ve bitiş nedenini kullanır. Önce iki normal istem, sonra üç aynı istem ve bir sentetik sır içeren istem gönderilir. Başarılı tek çağrı yeterli değildir; altısında da gerçek ölçüm gerekir. Aynı istemin üç kez gönderilmesi tekrar oranını `0.5` yapar ama bunun saldırı olduğunu kendi başına kanıtlamaz. Test ölçülerin doğruluğunu ve kayıt biçimini denetler, modelin belli bir cümleyi üretmesini istemez. Çalıştır çıktısı kayıtları gösterir; kabul Check ile ayrı verilir.

Öğrenciye sunulan redakte olay kaydı ile laboratuvar kanıtı farklı amaçlar taşır. Olay kaydında yalnız izinli alanlar vardır. Yerel deney kanıtında ise deneyin ürettiği sentetik girdiler, modelin gerçek yanıtları, tohumlar ve tekil ölçümler izlenebilirlik için saklanır. Bu sentetik ham kayıtların bulunması gerçek kullanıcı sırlarını toplama izni değildir. Başka kişilerin anahtarını veya özel belgelerini bu dosyalara ekleme. Eksik model, sıfır ölçüm veya başarısız kontrol geçme sayılmaz.

İstek başına tek satırlık yapılandırılmış JSON kaydı yeterli sinyali taşır: zaman, takma ad (`kim`), model, durum kodu, giriş ve çıkış token sayısı, gecikme ve bitiş nedeni. OpenAI uyumlu sunucular (vLLM'in OpenAI uyumlu sunucusu dahil) bu sayıları yanıtta `usage.prompt_tokens`, `usage.completion_tokens` ve `choices[].finish_reason` (`stop`, `length` gibi) alanlarıyla verir, kayıt bunları kopyalayabilir. Ham istem, ham tamamlama, `Authorization` başlığı ve anahtar ise kayda girmez: istemler kişisel veri ve sır taşır, kayıtlar da çoğu zaman uygulamadan daha fazla sisteme, daha geniş erişimle ve daha uzun süre kopyalanır. Kimliği düz SHA-256 ile gizlemek yetmez; müşteri numarası ya da IPv4 adresi (en çok 2^32 değer) gibi düşük entropili bir değerin özeti bütün adaylar denenerek geri bulunur. Sunucu tarafındaki bir sırla hesaplanan HMAC-SHA256 takma adı bu numaralandırmayı sır sızmadıkça engeller; aynı yöntemle normalize edilmiş istemin izi de yazılabilir (eşit izler eşit istemleri ele verir, içerik ise sır olmadan geri bulunamaz), sırrın dönemsel değiştirilmesi de dönemler arası ilişkilendirmeyi keser; takma adlandırılmış veri GDPR'a göre (Gerekçe 26) yine kişisel veri sayıldığından saklama süresi ayrıca politika ile sınırlanır, örneğin istek satırları kısa süre, toplu sayaçlar daha uzun tutulur.

Kötüye kullanım bu kayıtların toplamında görünür: bir istemciden art arda gelen `401`'ler anahtar tahmini ya da çalıntı anahtar listesi denemesidir, bir anahtarın süren `429`'ları kazıma ya da sızmış anahtarın toplu kullanımıdır, ani token artışı maliyet saldırısına ve Tramèr ve arkadaşlarının (USENIX Security 2016) tahmin API'leri üzerinden model çalma çalışmasında anlatılan çıkarım trafiğine işaret eder, neredeyse aynı istemlerin tekrarı ise otomatik jailbreak aramasının izidir. Bu derste "neredeyse aynı" yalnız küçük harfe çevirip boşlukları tekleştirerek yaklaşık hesaplanır; gerçek sistemler MinHash/SimHash ya da embedding benzerliği gibi daha güçlü yöntemler kullanır; ham alanlar yalnız ağ geçidinin kısa ömürlü bellek penceresinde durur, kalıcı kayda yalnız takma adlı satırlar ve alarmlar yazılır. FastAPI'de doğrulama bir bağımlılık (`Depends` ya da `Security`) olarak yazılır ve reddi `HTTPException(status_code=401, headers={"WWW-Authenticate": "Bearer"})` ile bildirir; `@app.middleware("http")` ara katmanı `call_next` çağrısının çevresinde gecikmeyi ölçüp tek JSON satırı yazar. Hazır `fastapi.security.HTTPBearer` gibi güvenlik yardımcıları FastAPI 0.122.0 öncesinde başarısız kimlik doğrulamada `403`, 0.122.0 ve sonrasında `401` ve `WWW-Authenticate` döndürür; eski davranış `make_not_authenticated_error` yeniden tanımlanarak geri getirilir. Görevler 1–3 bu katmanların karar çekirdeğini sentetik anahtarlar ve verilen zamanlarla sınar. Son adım kurulu yerel Ollama modeline altı gerçek HTTP isteği gönderir ve ölçüleri kayda dönüştürür. FastAPI ağ geçidi bu derste çalıştırılmaz.

Kaynaklar: [RFC 6750 — The OAuth 2.0 Authorization Framework: Bearer Token Usage](https://datatracker.ietf.org/doc/html/rfc6750), [RFC 9110 — HTTP Semantics (`WWW-Authenticate` ve `Retry-After`)](https://datatracker.ietf.org/doc/html/rfc9110).
:::

::: tahmin Takma ad ve bekleme süresini tahmin et
Üç çıktı satırını yaz:

```python
import hashlib, hmac
h = hashlib.sha256(b"musteri-42").hexdigest()
print([i for i in range(1000) if hashlib.sha256(b"musteri-%d" % i).hexdigest() == h])
g = hmac.new(b"ORNEK-SUNUCU-SIRRI", b"musteri-42", hashlib.sha256).hexdigest()
print(g == h, len(g), len(g[:16]))
seviye, aralik = 400, 1500   # kovada 400/1500 jeton var, bir jeton 1500 ms'de dolar
print(-(-(aralik - seviye) // 1000))
```

???

```cikti
[42]
False 64 16
2
```

`[42]`: düz SHA-256 takma adı, bin adayı denemekle geri çözülür; düşük entropili kimlik için özet gizlilik sağlamaz. `False 64 16`: sunucu sırrıyla HMAC aynı girdiden bambaşka bir değer üretir (sırrı bilmeyen numaralandıramaz), tam onaltılık özet 64 karakterdir ve kayıtta 16 karakterlik kısaltma kullanılabilir. `2`: bir jetona 1100 ms eksik vardır; `Retry-After` saniyeye yukarı yuvarlanır, 1 yazılsaydı istemci erken dönüp yeniden `429` alırdı.
:::

::: gorev 1 · Bearer başlığını katı ayrıştır ve özeti sabit zamanlı karşılaştır
`bearer_dogrula(baslik, anahtarlar, gerekli)` işlevini yaz. `baslik`, `Authorization` alanının HTTP ayrıştırıcısından geçmiş değeridir: `None` (başlık yok) ya da başında ve sonunda boşluk (U+0020) ya da sekme (U+0009) bulunmayan string; bu iki karakterle başlayan ya da biten değer geçersiz veridir. `anahtarlar` 1–8 kayıtlı sözlüktür; anahtarı boş olmayan string kimlik (ör. `k1`), değeri tam `ozet` ve `kapsamlar` anahtarlı sözlüktür. `ozet`, jetonun UTF-8 baytlarının SHA-256 özetidir: tam 64 karakter, yalnız `0-9a-f` içeren string; özetler kayıtlar arasında yinelenmez. `kapsamlar` yalnız `sohbet`, `gomme`, `yonet` içeren, yinelenmeyen (boş olabilir) listedir; `gerekli` bu üç stringden biridir. Başlık ne olursa olsun geçersiz veride `ValueError` yükselt.

`{"durum": ..., "anahtar": ..., "www_authenticate": ...}` döndür. Şema, değerin ilk boşluk (U+0020) karakterine kadar olan kısmıdır (boşluk yoksa değerin tamamı) ve büyük/küçük harf duyarsız karşılaştırılır; sekme ve diğer beyaz boşluk karakterleri ayırıcı değildir. Başlık yoksa ya da şema `bearer` değilse `401`, `None`, `"Bearer"`. Şemadan sonra bir ya da daha çok boşluk (U+0020) ve ardından jeton gelir; jeton ASCII harf, rakam ya da `-._~+/` karakterlerinden en az birini, sonra sıfır ya da daha çok `=` içermelidir. Jeton yoksa ya da başka herhangi bir karakter varsa (sekme, satır sonu, ara boşluk, ortada `=`, ASCII olmayan harf, virgül) `400`, `None`, `'Bearer error="invalid_request"'`. Biçimi geçerli jetonun (dolgu dahil) SHA-256 özetini her kaydın özetiyle `hmac.compare_digest(...)` çağrısıyla karşılaştır: çağrıyı bu modül adıyla yaz, her kayıt için tam bir kez yap ve eşleşme bulsan da döngüden çıkma. Eşleşme yoksa `401`, `None`, `'Bearer error="invalid_token"'`; eşleşen kaydın kapsamlarında `gerekli` yoksa `403`, kayıt kimliği, `'Bearer error="insufficient_scope"'`; varsa `200`, kayıt kimliği, `None`. Girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-20")
```

```starter
from ai_temel_veri import json_yukle
def bearer_dogrula(baslik, anahtarlar, gerekli):
    # KUSURLU BAŞLANGIÇ KODU: normal eşitlik kullanır, kapsamı yok sayar, ilk eşleşmede döner.
    import hashlib
    jeton=(baslik or "").removeprefix("Bearer ")
    for kim,k in anahtarlar.items():
        if hashlib.sha256(jeton.encode()).hexdigest()==k["ozet"]:
            return {"durum":200,"anahtar":kim,"www_authenticate":None}
    return {"durum":401,"anahtar":None,"www_authenticate":"Bearer"}

v=json_yukle("veri/trafik.json")["kimlik"]
print("Sentetik kimlik girdisi:",v)
print("Kimlik sonucu:",bearer_dogrula(v["baslik"],v["anahtarlar"],v["gerekli"]))
```

```test
import copy
import hashlib
import hmac
def oz(x):
    return hashlib.sha256(x.encode()).hexdigest()
J1, J2, J3 = "ornek-anahtar-SOHBET-1", "ornek.anahtar~gomme/2==", "ORNEK_ANAHTAR+YONET-3"
A = {"k1": {"ozet": oz(J1), "kapsamlar": ["sohbet"]}, "k2": {"ozet": oz(J2), "kapsamlar": ["gomme", "sohbet"]}, "k3": {"ozet": oz(J3), "kapsamlar": ["yonet", "gomme", "sohbet"]}}
YOK = {"durum": 401, "anahtar": None, "www_authenticate": "Bearer"}
BOZUK = {"durum": 400, "anahtar": None, "www_authenticate": 'Bearer error="invalid_request"'}
TANINMAZ = {"durum": 401, "anahtar": None, "www_authenticate": 'Bearer error="invalid_token"'}
def tamam(k):
    return {"durum": 200, "anahtar": k, "www_authenticate": None}
def yetersiz(k):
    return {"durum": 403, "anahtar": k, "www_authenticate": 'Bearer error="insufficient_scope"'}
SEKIZ = {"s%d" % i: {"ozet": oz("s%d" % i), "kapsamlar": ["gomme"]} for i in range(8)}
def degis(**alan):
    return {"k1": dict(A["k1"], **alan)}
def sozlesme(fn):
    asil = hmac.compare_digest
    sayac = []
    def sayan(a, b):
        sayac.append(1)
        return asil(a, b)
    hmac.compare_digest = sayan
    try:
        kopya = copy.deepcopy(A)
        for baslik, an, gerekli, beklenen in [("Bearer " + J1, A, "sohbet", tamam("k1")), ("bearer " + J2, A, "gomme", tamam("k2")), ("BEARER   " + J3, A, "yonet", tamam("k3")), ("Bearer " + J1, A, "gomme", yetersiz("k1")), ("Bearer ornek-yok", A, "sohbet", TANINMAZ), ("Bearer " + J2.rstrip("="), A, "sohbet", TANINMAZ), ("Bearer s7", SEKIZ, "gomme", tamam("s7")), ("Bearer s0", SEKIZ, "yonet", yetersiz("s0"))]:
            sayac.clear()
            if fn(baslik, an, gerekli) != beklenen or len(sayac) != len(an):
                return False
        if A != kopya or fn("Bearer x", {"t": {"ozet": oz("x"), "kapsamlar": []}}, "sohbet") != yetersiz("t"):
            return False
        for baslik in [None, "", "Basic ZGVtbzpkZW1v", "Token " + J1, "Bearer" + J1, "Bearer\t" + J1]:
            if fn(baslik, A, "sohbet") != YOK:
                return False
        for baslik in ["Bearer", "Bearer a b", "Bearer a=b", "Bearer =", "Bearer çay", "Bearer a,b", "Bearer " + J1 + "\n", "Bearer a\tb", "Bearer \t" + J1]:
            if fn(baslik, A, "sohbet") != BOZUK:
                return False
        for args in [("Bearer x", None, "sohbet"), ("Bearer x", [], "sohbet"), ("Bearer x", {}, "sohbet"), ("Bearer x", dict(SEKIZ, s8={"ozet": oz("s8"), "kapsamlar": []}), "sohbet"), ("Bearer x", {"": A["k1"]}, "sohbet"), ("Bearer x", {1: A["k1"]}, "sohbet"), ("Bearer x", {"k1": ["ozet", "kapsamlar"]}, "sohbet"), ("Bearer x", {"k1": {"ozet": oz("x")}}, "sohbet"), ("Bearer x", A, ["sohbet"]), ("Bearer x", degis(ek=1), "sohbet"), ("Bearer x", degis(ozet=oz("x")[:63]), "sohbet"), ("Bearer x", degis(ozet=oz("x") + "a"), "sohbet"), ("Bearer x", degis(ozet=oz("x").upper()), "sohbet"), ("Bearer x", degis(ozet="g" * 64), "sohbet"), ("Bearer x", degis(ozet=oz("x").encode()), "sohbet"), ("Bearer x", degis(ozet=None), "sohbet"), ("Bearer x", degis(kapsamlar=("sohbet",)), "sohbet"), ("Bearer x", degis(kapsamlar=["sil"]), "sohbet"), ("Bearer x", degis(kapsamlar=["gomme", "gomme"]), "sohbet"), ("Bearer x", degis(kapsamlar=None), "sohbet"), ("Bearer x", degis(kapsamlar=[["sohbet"]]), "sohbet"), ("Bearer ", A, "sohbet"), (" Bearer " + J1, A, "sohbet"), ("\tBearer " + J1, A, "sohbet"), ("Bearer " + J1 + " ", A, "sohbet"), ("Bearer " + J1 + "\t", A, "sohbet"), ("Bearer x", {"k1": A["k1"], "k2": dict(A["k2"], ozet=A["k1"]["ozet"])}, "sohbet"), ("Bearer x", A, "sil"), ("Bearer x", A, None), ("Bearer x", A, b"sohbet"), ("Bearer x", A, True), (b"Bearer x", A, "sohbet"), (1, A, "sohbet"), (True, A, "sohbet"), (None, None, "sohbet")]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
    finally:
        hmac.compare_digest = asil
ok(sozlesme(bearer_dogrula), "bearer ayrıştırma, özet karşılaştırma ve 400/401/403 ayrımı korunmalı")
def m_kapsam(b, a, g):
    r = bearer_dogrula(b, a, g)
    return tamam(r["anahtar"]) if r["durum"] == 403 else r
def m_sema(b, a, g):
    if isinstance(b, str) and b.split(" ")[0] != "Bearer":
        return YOK
    return bearer_dogrula(b, a, g)
def m_dolgu(b, a, g):
    return bearer_dogrula(b.rstrip("=") if isinstance(b, str) else b, a, g)
for ad, mutant in [("kapsamı yok sayan", m_kapsam), ("şemayı harf duyarlı okuyan", m_sema), ("dolguyu kırpan", m_dolgu)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
import hashlib
import hmac
import string
def bearer_dogrula(baslik, anahtarlar, gerekli):
    izinli = {"sohbet", "gomme", "yonet"}
    if not isinstance(gerekli, str) or gerekli not in izinli or not isinstance(anahtarlar, dict) or not 1 <= len(anahtarlar) <= 8:
        raise ValueError("girdi")
    for kimlik, kayit in anahtarlar.items():
        if not isinstance(kimlik, str) or not kimlik or not isinstance(kayit, dict) or set(kayit) != {"ozet", "kapsamlar"}:
            raise ValueError("kayıt")
        ozet, kapsamlar = kayit["ozet"], kayit["kapsamlar"]
        if not isinstance(ozet, str) or len(ozet) != 64 or set(ozet) - set(string.digits + "abcdef"):
            raise ValueError("özet")
        if not isinstance(kapsamlar, list) or not all(isinstance(x, str) for x in kapsamlar) or set(kapsamlar) - izinli or len(set(kapsamlar)) != len(kapsamlar):
            raise ValueError("kapsam")
    if len({k["ozet"] for k in anahtarlar.values()}) != len(anahtarlar) or not isinstance(baslik, (str, type(None))):
        raise ValueError("yinelenen")
    deger = baslik or ""
    if deger != deger.strip(" \t"):
        raise ValueError("boşluk")
    sema, _, kalan = deger.partition(" ")
    if sema.lower() != "bearer":
        return {"durum": 401, "anahtar": None, "www_authenticate": "Bearer"}
    jeton = kalan.lstrip(" ")
    govde = jeton.rstrip("=")
    if not govde or set(govde) - set(string.ascii_letters + string.digits + "-._~+/"):
        return {"durum": 400, "anahtar": None, "www_authenticate": 'Bearer error="invalid_request"'}
    ozet = hashlib.sha256(jeton.encode()).hexdigest()
    bulunan = None
    for kimlik, kayit in anahtarlar.items():
        if hmac.compare_digest(ozet, kayit["ozet"]):
            bulunan = kimlik
    if bulunan is None:
        return {"durum": 401, "anahtar": None, "www_authenticate": 'Bearer error="invalid_token"'}
    if gerekli not in anahtarlar[bulunan]["kapsamlar"]:
        return {"durum": 403, "anahtar": bulunan, "www_authenticate": 'Bearer error="insufficient_scope"'}
    return {"durum": 200, "anahtar": bulunan, "www_authenticate": None}

if __name__ == "__main__":
    v=json_yukle("veri/trafik.json")["kimlik"]
    print("Sentetik kimlik girdisi:",v)
    print("Kimlik sonucu:",bearer_dogrula(v["baslik"],v["anahtarlar"],v["gerekli"]))
```

```hint
Önce bütün girdileri doğrula, sonra değeri ilk boşlukta ikiye böl: şemayı `lower()` ile karşılaştır, kalan kısmın baştaki boşluklarını at ve yalnız sondaki `=` dolgusunu ayırarak karakter kümesini denetle. Özeti dolgulu jetondan hesapla; eşleşen kimliği bir değişkende tut ve döngüyü sonuna kadar sürdür.
```
:::

::: gorev 2 · Anahtar başına token bucket ile 429 ve Retry-After üret
`kova_sinirla(olaylar, kapasite, aralik_ms)` işlevini yaz. `kapasite` 1–10, `aralik_ms` 1–60000 tamsayıdır (bool değil). `olaylar` `(t, anahtar)` demetlerinden oluşan listedir (boş olabilir): `t` 0 ya da daha büyük tamsayı milisaniyedir (bool değil) ve liste boyunca azalmaz (eşit olabilir), `anahtar` boş olmayan stringdir; her öğe tam iki öğeli `tuple` olmalıdır. Geçersiz veride `ValueError` yükselt.

Her anahtarın kendi kovası vardır ve anahtar ilk göründüğünde kova doludur (`kapasite` jeton). Kovaya her `aralik_ms` milisaniyede bir jeton, araya düşen süreyle orantılı ve kesirli olarak dolar; kova `kapasite` jetonu aşamaz. Kesirleri tam hesapla (ör. jetonu `aralik_ms` birime bölen tamsayı aritmetiği ya da `fractions.Fraction`), kayan nokta kullanma. Olay anında kovada en az bir tam jeton varsa bir jeton harca ve `(200, None)` üret; yoksa jeton harcamadan `(429, s)` üret: `s`, bir tam jetona eksik milisaniyenin saniyeye yukarı yuvarlanmış değeridir. Sonuçları olay sırasıyla liste olarak döndür. Girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-20")
```

```starter
from ai_temel_veri import json_yukle
def kova_sinirla(olaylar, kapasite, aralik_ms):
    # KUSURLU BAŞLANGIÇ KODU: bütün anahtarları tek kovada sayar ve zamanla doldurmaz.
    kalan=kapasite;sonuc=[]
    for t,anahtar in olaylar:
        sonuc.append((200,None) if kalan>0 else (429,1))
        kalan=max(0,kalan-1)
    return sonuc

v=json_yukle("veri/trafik.json")["kova"]
print("Sentetik kova olayları:",v)
print("Kova sonucu:",kova_sinirla([tuple(x) for x in v["olaylar"]],v["kapasite"],v["aralik_ms"]))
```

```test
import copy
OL = [(0, "a"), (0, "a"), (0, "a"), (500, "a"), (1500, "a"), (1500, "b"), (1999, "a"), (2498, "a"), (100000, "b"), (100000, "b"), (100000, "b")]
BEK = [(200, None), (200, None), (429, 2), (429, 1), (200, None), (200, None), (429, 2), (429, 1), (200, None), (200, None), (429, 2)]
def sozlesme(fn):
    try:
        kopya = copy.deepcopy(OL)
        if fn(OL, 2, 1500) != BEK or OL != kopya or fn([], 1, 1) != []:
            return False
        if fn([(0, "x"), (0, "x")], 1, 60000) != [(200, None), (429, 60)] or fn([(7, "x"), (7, "x")], 1, 1) != [(200, None), (429, 1)]:
            return False
        if fn([(0, "x")] * 11, 10, 1) != [(200, None)] * 10 + [(429, 1)]:
            return False
        if fn([(0, "a"), (0, "a"), (1500, "a"), (2000, "a"), (2001, "a")], 2, 1000) != [(200, None)] * 4 + [(429, 1)]:
            return False
        for args in [(None, 1, 1), (((0, "a"),), 1, 1), ([[0, "a"]], 1, 1), ([(0, "a", 1)], 1, 1), ([(0,)], 1, 1), ([(-1, "a")], 1, 1), ([(True, "a")], 1, 1), ([(1.0, "a")], 1, 1), ([(0, "")], 1, 1), ([(0, b"a")], 1, 1), ([(0, None)], 1, 1), ([(5, "a"), (4, "b")], 1, 1), ([], 0, 1), ([], 11, 1), ([], True, 1), ([], 1.0, 1), ([], None, 1), ([], 1, 0), ([], 1, 60001), ([], 1, True), ([], 1, "1")]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(kova_sinirla), "anahtar başına kova, tavan, sınır ve Retry-After yuvarlaması korunmalı")
def m_ortak(o, k, a):
    return kova_sinirla([(t, "ortak") for t, _ in o] if isinstance(o, list) else o, k, a)
def m_tavan(o, k, a):
    return kova_sinirla(o, k + 1 if type(k) is int and k < 10 else k, a)
def m_bekle(o, k, a):
    return [(d, r if r is None else r - 1) for d, r in kova_sinirla(o, k, a)]
for ad, mutant in [("tek ortak kova kullanan", m_ortak), ("kapasiteyi aşan", m_tavan), ("Retry-After'ı eksik veren", m_bekle)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def kova_sinirla(olaylar, kapasite, aralik_ms):
    for sayi, ust in ((kapasite, 10), (aralik_ms, 60000)):
        if type(sayi) is not int or not 1 <= sayi <= ust:
            raise ValueError("sınır")
    if not isinstance(olaylar, list):
        raise ValueError("olaylar")
    tavan = kapasite * aralik_ms
    kovalar, sonuc, onceki = {}, [], 0
    for olay in olaylar:
        if not isinstance(olay, tuple) or len(olay) != 2:
            raise ValueError("olay")
        t, anahtar = olay
        if type(t) is not int or t < onceki or not isinstance(anahtar, str) or not anahtar:
            raise ValueError("olay")
        onceki = t
        seviye, son = kovalar.get(anahtar, (tavan, t))
        seviye = min(tavan, seviye + t - son)
        if seviye >= aralik_ms:
            kovalar[anahtar] = (seviye - aralik_ms, t)
            sonuc.append((200, None))
        else:
            kovalar[anahtar] = (seviye, t)
            sonuc.append((429, -(-(aralik_ms - seviye) // 1000)))
    return sonuc

if __name__ == "__main__":
    v=json_yukle("veri/trafik.json")["kova"]
    print("Sentetik kova olayları:",v)
    print("Kova sonucu:",kova_sinirla([tuple(x) for x in v["olaylar"]],v["kapasite"],v["aralik_ms"]))
```

```hint
Jetonu milisaniye birimiyle say: bir jeton `aralik_ms` birimdir, tavan `kapasite * aralik_ms` birimdir ve geçen her milisaniye bir birim ekler. Her anahtar için `(seviye, son_zaman)` sakla; reddedilen istekte de doldurulmuş seviyeyi ve zamanı yaz, eksik birimi 1000'e bölerken yukarı yuvarlayan tamsayı bölmesi kullan.
```
:::

::: gorev 3 · Takma adlı olaylardan kötüye kullanım alarmları çıkar
`alarm_uret(olaylar, gizli)` işlevini yaz. `gizli` en az 16 baytlık `bytes` değeridir (`bytearray` ya da `str` değil). `olaylar` tek bir izleme penceresindeki olayların listesidir (boş olabilir); her olay tam `istemci`, `anahtar`, `durum`, `istem`, `token` anahtarlı sözlüktür. `istemci` ve `istem` boş olmayan string, `token` 0 ya da daha büyük tamsayı, `durum` tamsayı `200`, `401` ya da `429`'dur (bool ve float değil). `durum` `401` ise `anahtar` `None` olmalıdır, değilse boş olmayan string olmalıdır. Geçersiz veride `ValueError` yükselt.

Takma ad, değerin UTF-8 baytları üzerinde `gizli` anahtarıyla hesaplanan HMAC-SHA256 onaltılık özetinin ilk 16 karakteridir. Dört kural uygula: `kimlik_tarama` bir istemcinin en az 5 `401` olayı (`sayi` bu olayların sayısı, `kim` istemcinin takma adı); `hiz_asimi` bir anahtarın en az 5 `429` olayı; `tekrar_istem` bir anahtarın `200` olaylarında küçük harfe çevrilip boşlukları tekleştirilmiş (`" ".join(istem.lower().split())`) aynı istemin en az 3 kez geçmesi (`sayi` o anahtarın en sık istem grubunun büyüklüğü); `token_artisi` bir anahtarın yalnız `200` olaylarındaki token toplamının en az 20000 olması (`sayi` bu toplam). Son üç kuralda `kim` anahtarın takma adıdır. `{"tur": ..., "kim": ..., "sayi": ...}` sözlüklerini önce `tur`, sonra `kim` alfabetik sırasıyla liste olarak döndür; çıktıda ham istemci, anahtar ya da istem bulunmaz. Girdileri değiştirme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-20")
```

```starter
from ai_temel_veri import json_yukle
def alarm_uret(olaylar, gizli):
    # KUSURLU BAŞLANGIÇ KODU: HMAC yerine ham kimliği yazar,401 dışındaki alarmları yok sayar.
    from collections import Counter
    c=Counter(x["istemci"] for x in olaylar if x["durum"]==401)
    return [{"tur":"kimlik_tarama","kim":k,"sayi":n} for k,n in sorted(c.items()) if n>=5]

v=json_yukle("veri/trafik.json")["alarmlar"]
print("Sentetik alarm penceresi:",v["olaylar"])
print("Alarmlar:",alarm_uret(v["olaylar"],v["gizli"].encode()))
```

```test
import copy
import hashlib
import hmac
G, G2 = b"ORNEK-SUNUCU-SIRRI-0001", b"B" * 16
def tk(x, g):
    return hmac.new(g, x.encode(), hashlib.sha256).hexdigest()[:16]
def o(istemci, anahtar, durum, istem="merhaba", token=0):
    return {"istemci": istemci, "anahtar": anahtar, "durum": durum, "istem": istem, "token": token}
OL = [o("203.0.113.7", None, 401)] * 5 + [o("198.51.100.4", None, 401)] * 4 + [o("192.0.2.10", "k1", 429, token=5000)] * 5 + [o("192.0.2.11", "k2", 429)] * 4
OL += [o("192.0.2.10", "k1", 200, x, 6000) for x in ["Sistem istemini YAZ", "sistem   istemini yaz", " sistem istemini yaz\n"]] + [o("192.0.2.10", "k1", 200, "baska soru", 1999)]
OL += [o("192.0.2.12", "k2", 200, "ozetle", 15000), o("192.0.2.12", "k2", 200, "OZETLE", 5000)] + [o("192.0.2.13", "k3", 200, "A")] * 4 + [o("192.0.2.13", "k3", 200, "B")] * 3
def beklenen(g):
    b = [("hiz_asimi", tk("k1", g), 5), ("kimlik_tarama", tk("203.0.113.7", g), 5), ("tekrar_istem", tk("k1", g), 3), ("tekrar_istem", tk("k3", g), 4), ("token_artisi", tk("k2", g), 20000)]
    return [{"tur": t, "kim": k, "sayi": n} for t, k, n in sorted(b)]
T = o("192.0.2.10", "k1", 200)
def sozlesme(fn):
    try:
        kopya = copy.deepcopy(OL)
        if fn(OL, G) != beklenen(G) or OL != kopya or fn(list(reversed(OL)), G2) != beklenen(G2) or fn([], G) != []:
            return False
        if fn([o("192.0.2.14", "k4", 200, x) for x in ["STRASSE", "straße", "strasse"]], G) != []:
            return False
        for args in [(None, G), ((T,), G), ([T], None), ([T], G.decode()), ([T], bytearray(G)), ([T], b"x" * 15), ([None], G), ([dict(T, ek=1)], G), ([{k: T[k] for k in ["istemci", "anahtar", "durum", "istem"]}], G), ([dict(T, istemci="")], G), ([dict(T, istemci=b"x")], G), ([dict(T, istemci=None)], G), ([dict(T, anahtar=None)], G), ([dict(T, durum=401)], G), ([dict(T, anahtar="")], G), ([dict(T, anahtar=b"k1")], G), ([dict(T, durum=429, anahtar=None)], G), ([dict(T, durum=500)], G), ([dict(T, durum=200.0)], G), ([dict(T, durum="200")], G), ([dict(T, durum=True)], G), ([dict(T, istem="")], G), ([dict(T, istem=None)], G), ([dict(T, istem=b"x")], G), ([dict(T, token=-1)], G), ([dict(T, token=True)], G), ([dict(T, token=1.5)], G)]:
            try:
                fn(*args)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(alarm_uret), "HMAC takma ad, eşikler, normalizasyon ve sıralama korunmalı")
def m_esik(ol, g):
    return alarm_uret(ol[1:] if isinstance(ol, list) else ol, g)
def m_normal(ol, g):
    return alarm_uret([dict(x, istem=x["istem"] + str(i)) for i, x in enumerate(ol)] if isinstance(ol, list) else ol, g)
def m_kim(ol, g):
    return alarm_uret([dict(x, anahtar=x["istemci"]) if x["durum"] == 429 else x for x in ol] if isinstance(ol, list) else ol, g)
for ad, mutant in [("olay düşüren", m_esik), ("tekrar gruplarını bozan", m_normal), ("429'u istemciye bağlayan", m_kim)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
import hashlib
import hmac
from collections import Counter
def alarm_uret(olaylar, gizli):
    if not isinstance(gizli, bytes) or len(gizli) < 16 or not isinstance(olaylar, list):
        raise ValueError("girdi")
    def takma(deger):
        return hmac.new(gizli, deger.encode(), hashlib.sha256).hexdigest()[:16]
    ret, hiz, token, istem = Counter(), Counter(), Counter(), Counter()
    for o in olaylar:
        if not isinstance(o, dict) or set(o) != {"istemci", "anahtar", "durum", "istem", "token"}:
            raise ValueError("olay")
        ist, an, du, me, to = o["istemci"], o["anahtar"], o["durum"], o["istem"], o["token"]
        if not isinstance(ist, str) or not ist or not isinstance(me, str) or not me or type(to) is not int or to < 0:
            raise ValueError("alan")
        if type(du) is not int or du not in (200, 401, 429) or (du == 401) != (an is None) or an == "" or an is not None and not isinstance(an, str):
            raise ValueError("durum")
        if du == 401:
            ret[takma(ist)] += 1
        elif du == 429:
            hiz[takma(an)] += 1
        else:
            token[takma(an)] += to
            istem[takma(an), " ".join(me.lower().split())] += 1
    tekrar = dict(sorted((k, n) for (k, _), n in istem.items()))
    alarmlar = [("kimlik_tarama", k, n) for k, n in ret.items() if n >= 5]
    alarmlar += [("hiz_asimi", k, n) for k, n in hiz.items() if n >= 5]
    alarmlar += [("tekrar_istem", k, n) for k, n in tekrar.items() if n >= 3]
    alarmlar += [("token_artisi", k, n) for k, n in token.items() if n >= 20000]
    return [{"tur": t, "kim": k, "sayi": n} for t, k, n in sorted(alarmlar)]

if __name__ == "__main__":
    v=json_yukle("veri/trafik.json")["alarmlar"]
    print("Sentetik alarm penceresi:",v["olaylar"])
    print("Alarmlar:",alarm_uret(v["olaylar"],v["gizli"].encode()))
```

```hint
Her kural için ayrı bir `Counter` tut: `401`'leri istemcinin, `429` ve `200`'leri anahtarın takma adıyla say. Tekrar kuralında sayacın anahtarı `(takma ad, normalize istem)` çifti olsun; her takma ad için en büyük grup boyutunu seç, eşikleri en sonda uygula.
```
:::

::: gorev Gerçek deney · Gizliliği koruyan gözlemlenebilirlik kaydı
`olay_kaydi(ham, tuz)` işlevini yaz.

- Doğrulama, aksi hâlde `ValueError`: `ham` tam `zaman`, `anahtar`, `istem`, `token`, `sure_ms`, `done_reason` anahtarlı sözlük; `anahtar` boş olmayan str, `istem` str, `token` bool olmayan negatif olmayan int, `sure_ms` bool olmayan sonlu, negatif olmayan sayı, `done_reason` str, `zaman` bool olmayan sonlu, negatif olmayan sayı. `tuz` boş olmayan str.
- Döndür: `{"zaman": ham["zaman"], "anahtar_hash": sha256((tuz + anahtar) baytları) onaltılık özetinin ilk 16 hanesi, "istem_uzunluk": len(istem), "istem_redakte": istemdeki sırlar redakte edilmiş: sırayla önce **anahtar** (`sk-` ardından 16+ ASCII harf/rakam ya da `PAFTA-` ardından 8 onaltılık büyük harf/rakam), sonra **eposta** (`[\w.+-]+@[\w-]+\.[\w.-]+`), sonra **numara** (12+ ardışık rakam) bulunur ve her eşleşme `[GIZLI:tür]` olur, "turler": bulunan türler (alfabetik), "token": ham["token"], "sure_ms": ham["sure_ms"], "done_reason": ham["done_reason"]}`. Ham anahtarı ve ham istemi **kayda koyma**.

Test işlevini sentetik ham kayıtlarda sınar; sonra yerel modele gerçek istekler atıp senin kaydının sırrı sızdırmadığını ve ölçülerin gerçek olduğunu doğrular. Çalıştır düğmesi bütün kayıtları gösterir.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import hashlib
import re
import math
import ai_lab

def olay_kaydi(ham, tuz):
    return {}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_20 as deney
    deney.goster(olay_kaydi)
```

```test
import ai_lab
sonuclar = []
def kontrol(kosul, mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul, mesaj)
import ast
_yasak=("referans","referans_olay","_redakte","kanit_yaz","getattr")
sorun=ai_lab.kod_denetimi(src,yasak=_yasak)
for n in ast.walk(ast.parse(src)):
    if isinstance(n,ast.ImportFrom) and any(a.name in _yasak or a.name=="*" for a in n.names):
        sorun.append("referans importu yasak")
if not kontrol(not sorun,"Kendi olay kaydını yaz: "+"; ".join(sorun)):
    stop()
fn = need("olay_kaydi")
from sandbox import ai_gercek_ai_temel_20 as D
TUZ = "tuz-123"
hamlar = [{"zaman": 0, "anahtar": "sk-abc", "istem": "merhaba dünya", "token": 5, "sure_ms": 100, "done_reason": "stop"},
          {"zaman": 1, "anahtar": "sk-abc", "istem": "mail x@y.com ve PAFTA-DEADBEEF", "token": 9, "sure_ms": 200, "done_reason": "length"},
          {"zaman": 2, "anahtar": "k2", "istem": "kart 123456789012 son", "token": 3, "sure_ms": 50.5, "done_reason": "stop"}]
def sozlesme(f):
    try:
        for h in hamlar:
            if f(dict(h), TUZ) != D.referans_olay(dict(h), TUZ):
                return False
        import copy
        h0=hamlar[0]
        ek=[dict(h0,token=0),dict(h0,zaman=10**400),dict(h0,istem="sk-ABCDEFGHIJKLMNOP1234 ve PAFTA-12345678 ve 123456789012"),dict(h0,istem=""),dict(h0,istem="mail a.b+x@firma.test!")]
        for h in ek+hamlar:
            once=copy.deepcopy(h)
            for tuz in (TUZ,"farkli-tuz"):
                if f(h,tuz)!=D.referans_olay(once,tuz) or h!=once: return False
        for arg in [(dict(h0,zaman="0"),TUZ),(dict(h0,zaman=float("nan")),TUZ),(dict(h0,sure_ms=float("inf")),TUZ),(dict(h0,zaman=True),TUZ),(None, TUZ), ("x", TUZ), (dict(h0, ek=1), TUZ), ({k: h0[k] for k in h0 if k != "token"}, TUZ),
                    (dict(h0, anahtar=""), TUZ), (dict(h0, anahtar=5), TUZ), (dict(h0, istem=5), TUZ),
                    (dict(h0, token=-1), TUZ), (dict(h0, token=True), TUZ), (dict(h0, token=1.0), TUZ),
                    (dict(h0, sure_ms=-1), TUZ), (dict(h0, sure_ms=True), TUZ), (dict(h0, zaman=-1), TUZ), (dict(h0, done_reason=5), TUZ),
                    (dict(h0), ""), (dict(h0), 5)]:
            try:
                f(*arg)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(fn), "gizliliği koruyan kayıt doğru (hash + redaksiyon + ölçü); geçersiz girdi reddedilmeli")
for ad, kw in [("ham anahtarı kayda yazan", {"ham_anahtar": True}), ("istemi redakte etmeyen", {"redakte": False}),
               ("istemi uzunluk yerine ham yazan", {"uzunluk": False})]:
    kontrol(not sozlesme(lambda h, t, kw=kw: D.referans_olay(h, t, **kw)), "hatalı çözüm reddedilmeli: " + ad)
r, oz = None, None
if all(sonuclar):
    try:
        r = D.deney(fn)
    except ai_lab.GercekLabYok as e:
        kontrol(False, f"GERÇEK MODEL YOK, deney yapılmadı: {e}")
        stop()
    kayitlar = [k["kayit"] for k in r["kayitlar"]]
    kontrol(all(k == D.referans_olay(h, r["tuz"]) for k, h in zip(kayitlar, r["ham"])), "gerçek kayıtlar bağımsız referansla aynı")
    sir = next(k["kayit"] for k in r["kayitlar"] if k["etiket"] == "sir")
    sm = str(sir)
    sizan = [ad for ad, v in r["sirlar"].items() if v in sm] + (["ham_anahtar"] if r["anahtar"] in sm else [])
    kontrol(not sizan, f"gizli istek kaydı hiçbir sırrı sızdırmıyor (sızan: {sizan or 'yok'}); türler {sir['turler']}")
    kontrol(all(r["anahtar"] not in str(k["kayit"]) for k in r["kayitlar"]), "ham API anahtarı hiçbir kayıtta yok (tuzlanmış hash kullanıldı)")
    gecerli = [k for k in r["kayitlar"] if k["kayit"]["token"] and k["kayit"]["token"] > 0]
    kontrol(len(gecerli) == len(r["kayitlar"]) == 6, f"token ve gecikme gerçek ölçüldü ({len(gecerli)}/{len(r['kayitlar'])} istekte token>0)")
    oz = D.ozet(r)
    kontrol(oz["yineleme_orani"] >= 0.5, f"tekrarlı istem kayıtlarda görünür (tekrar oranı {oz['yineleme_orani']})")
yol = ai_lab.kanit_yaz("temel-gozlem", {"kaynak": "gercek", "kabul": all(sonuclar), "ders": "ai-temel-20",
                                        "ortam": (r or {}).get("ortam"), "ozet": oz, "deney": r, "sinir": "ham kanıt yalnız üretilmiş sentetik sırları taşır; öğrenci olay kaydıyla ayrı, regex redaksiyonu genel gizlilik garantisi değil"})
if oz:
    ok(True, f"BULGU ({r['ortam']['model']['ad']}): {oz['istek']} gerçek istek, toplam {oz['toplam_token']} token; sır kaydı türleri {oz['sir_turleri']}, "
             f"sızan sır: {oz['sizan_sir'] or 'yok'}, ham anahtar kayıtta: {oz['ham_anahtar_kayitta']}; tekrar oranı {oz['yineleme_orani']} (kötüye kullanım görünür).")
```

```solution
import hashlib
import re
import math
import ai_lab

def olay_kaydi(ham, tuz):
    if not isinstance(ham, dict) or set(ham) != {"zaman", "anahtar", "istem", "token", "sure_ms", "done_reason"}:
        raise ValueError("ham alanları: zaman, anahtar, istem, token, sure_ms, done_reason")
    if not isinstance(ham["anahtar"], str) or not ham["anahtar"]:
        raise ValueError("anahtar boş olmayan string olmalı")
    if not isinstance(ham["istem"], str):
        raise ValueError("istem string olmalı")
    if isinstance(ham["token"], bool) or not isinstance(ham["token"], int) or ham["token"] < 0:
        raise ValueError("token negatif olmayan tamsayı olmalı")
    for a in ("zaman", "sure_ms"):
        v = ham[a]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or (isinstance(v,float) and not math.isfinite(v)) or v < 0:
            raise ValueError(f"{a} sonlu, negatif olmayan sayı olmalı")
    if not isinstance(ham["done_reason"], str):
        raise ValueError("done_reason string olmalı")
    if not isinstance(tuz, str) or not tuz:
        raise ValueError("tuz boş olmayan string olmalı")
    desenler = [(re.compile(r"sk-[A-Za-z0-9]{16,}|PAFTA-[0-9A-F]{8}"), "anahtar"),
                (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "eposta"),
                (re.compile(r"\d{12,}"), "numara")]
    turler = set()
    def rep(tur):
        def f(_m):
            turler.add(tur)
            return f"[GIZLI:{tur}]"
        return f
    red = ham["istem"]
    for desen, tur in desenler:
        red = desen.sub(rep(tur), red)
    return {"zaman": ham["zaman"],
            "anahtar_hash": hashlib.sha256((tuz + ham["anahtar"]).encode("utf-8")).hexdigest()[:16],
            "istem_uzunluk": len(ham["istem"]), "istem_redakte": red, "turler": sorted(turler),
            "token": ham["token"], "sure_ms": ham["sure_ms"], "done_reason": ham["done_reason"]}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_20 as deney
    deney.goster(olay_kaydi)
```

```hint
Redaksiyonu üç desenle yukarıdaki sırayla yap (anahtar→eposta→numara); anahtar önce gelmeli ki içindeki uzun rakam dizisi numara sayılmasın. Bu deneyde tuz sunucu sırrı gibi gizli tutulur; üretimde anlatımdaki HMAC-SHA256 takma adı tercih edilir. Anahtarı `hashlib.sha256((tuz + anahtar).encode()).hexdigest()[:16]` ile özetle; kayda ne ham anahtarı ne de ham istemi koy, yalnız uzunluk, redakte metin, türler ve gerçek ölçüler girsin.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Ağ geçidi savunma katmanları (`RFC 6750` + `Token Bucket`) (30 sn).** "İstek modele ulaşmadan önce `Bearer` belirteci katı sözdizimiyle ayrıştırılıp `hmac.compare_digest` ile doğrulanır; ardından anahtar başına sürekli dolan jeton kovası hız aşımında jeton harcamadan `429` ve yukarı yuvarlanmış `Retry-After` döndürür."
2. **İkinci bir sızıntı olmayan gözlemlenebilirlik (35 sn).** "Kalıcı kayıtlara ham istem veya ham API anahtarı asla yazılmaz; düşük entropili kimlikler sunucu sırrıyla `HMAC-SHA256` takma adına çevrilir ve metin uzunluk/sayaç sinyalleriyle redaksiyon birlikte tutulur."
3. **Kötüye kullanım sinyalleri (30 sn).** "İstemci başına `401` fırtınası anahtar denemesini, anahtar başına `429` ve yüksek token/tekrar oranı ise sızmış anahtar kazımasını veya otomatik jailbreak/model çalma aramasını görünür kılar."
4. **Soru (25 sn).** "IPv4 adresini veya kısa müşteri numarasını sunucu sırrı olmadan düz `SHA-256` ile özetleyip loglarsan saldırgan gerçek değeri neden saniyeler içinde geri bulabilir?"
:::
