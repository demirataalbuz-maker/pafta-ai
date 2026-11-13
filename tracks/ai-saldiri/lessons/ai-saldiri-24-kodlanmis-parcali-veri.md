---
id: ai-saldiri-24
title: Kodlanmış ve Parçalı Veri Dışarı Aktarımı
summary: Sentetik canary'yi Base64URL parçalarına ayır, sıra ve kanonik kodlama denetimiyle birleştir, tek çıktıda görünmeyen parçalı kanıtı raporla.
timeout: 45
---

::: anlat Kodlama gizleme veya şifreleme değildir
| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Bir alıcı sıralı olaylar ve kodlanmış yükler kaydeder; kodlanmış baytlar ve çözülmüş içerik ayrı kanıt katmanlarıdır | İlk üç görevde `veri/parcalar.json` içindeki elle hazırlanmış sentetik örnekler; son görevde gerçek yerel HTTP alıcısı, diske kaydedilen canary ve yerel modelin açıkça izinli native araç aktarımı | Bu izinli relay jailbreak veya modelden gizli sır çalma deneyi değildir; kanonik kod/sıra kontrolü göndericinin kimliğini ya da kriptografik bütünlüğü doğrulamaz |

> [!NOT]
> İlk üç görevin dosyaları **sentetiktir**, gerçek sunucu/model kaydı değildir. **Çalıştır** aynı JSON'u okuyup sonucunu gösterir. Aynı çalıştırmada kopyayı koddan değiştirebilirsin; çalışma klasörü geçicidir, sonraki çalıştırmada örnek yeniden kopyalanır ve değişiklik kalmaz. Son gerçek deneyin `PAFTA_DATA/calisma/ai-saldiri-24/parcalar.json` ayarı ise kalıcıdır. Gizli testler örnek dosyadan bağımsızdır; yalnız sentetik yerel canary kullanılır.

Base64URL yalnız baytları URL-benzeri alfabe ile temsil eder; gizlilik sağlamaz. Parçalama ise tek bir çıktıda görünen bütün canary'yi birkaç modele veya araç olayına dağıtır. Bu nedenle yalnız her çıktıyı ayrı arayan dedektör, birleşik akıştaki kanıtı kaçırabilir.

Görevler 1–3 hassas veri, ağ veya model kullanmaz; kısa ASCII canary örnekleri kodlanır ve bellek içinde birleştirilir. Son adım gerçek yerel HTTP alıcısı ve yerel modelle açıkça izinli aktarım çalıştırır; mitmproxy kullanılmaz. Amaç veri çıkarma yöntemi uygulamak değil, kodlama ve parça meta verisini doğrulayan regresyon sözleşmelerini öğretmektir.
:::

::: anlat Ham kayıttan kanıta: kodlama, sıra ve kaynak ayrımı
Bir olay kaydında birkaç anlamsız görünen dizi bulman tek başına veri sızıntısı kanıtı değildir. Önce bunların hangi temsil olduğunu, hangi akışa ait olduğunu ve hangi sırayla üretildiğini belirlemelisin. Base64URL baytları başka bir alfabeyle yazar; şifreleme anahtarı yoktur ve çözme işlemi gizli bir bilgi gerektirmez. Buna rağmen yalnız açık canary metnini arayan bir tarayıcı kodlanmış görünümde eşleşme bulmayabilir. Bu, canary'nin sistemde bulunmadığını değil, seçtiğin dedektörün o temsil katmanını incelemediğini gösterir. Dersin amacı bu ölçüm sınırını görünür kılmaktır.

`veri/parcalar.json` dosyasında aynı örneğin kaynak metni, kodlanmış paketleri ve ham çıktı parçaları birlikte durur. İlk görev kaynak metni belirli boyutta baytlara ayırır. İkinci görev dosyadaki kodlanmış paketleri çözer; listeyi ters sıraya koyduğunda sonuç değişmemelidir, çünkü geliş sırası yerine açık sıra alanı kullanılır. Üçüncü görev ise Base64 çözmez: ham çıktı parçalarını sıraya koyar ve birleşik metinde canary arar. Bu iki işlemi tek bir ölçüm gibi raporlarsan kod çözme sayesinde bulunan işareti modelin ham çıktısında açıkça varmış gibi gösterebilirsin.

Sıra ve toplam alanları basit bir veri sözleşmesidir. Aynı sıra iki kez gelmişse son görüleni seçmek önceki kaydı sessizce kaybettirir. Eksik parça varsa onu atlayıp kalanları birleştirmek başka metinlerin yan yana gelmesine ve yanlış kanıta yol açabilir. Bu nedenle tam sıra kümesi, ortak toplam ve gerçek parça sayısı birlikte doğrulanır. Fakat bu kontroller kimlik doğrulaması değildir: sahte bir gönderici de düzgün numaralandırılmış paketler hazırlayabilir. Üretimde kaynağa güvenmek için oturum bağlamı, yetkilendirme ve gerekirse ayrı kriptografik doğrulama gerekir. Bu ders onları uyguladığı iddiasında değildir.

Kanonik kodlama aynı bayt dizisinin tek kabul edilen metinsel gösterimini seçer. Çözücü dolguyu teknik olarak tamamlayabilir, ancak girdi sözleşmesi dolgusuz Base64URL ister. Çözülmüş baytları yeniden kodlayıp girdiye birebir eşitlemek, normalleştiricinin bozuk bir girdiyi sessizce onarmasını önler. “Çözülebildi” demek “geçerli sözleşmeye uyuyor” demek değildir. Parçanın kendi bayt sınırı ile birleşik metnin toplam sınırı da ayrıdır; küçük parçaların çokluğu toplam boyut sınırını aşabilir. Bool değerlerinin Python'da tam sayıya benzemesi sıra alanında ayrıca reddedilmesi gereken bir tuzaktır.

Gerçek deney kendi yerel alıcısını açar, rastgele sentetik canary'yi dosyaya yazar ve öğrencinin kodladığı JSON paketlerini gerçek HTTP üzerinden kaydeder. Alıcı kayıtları ters sırayla çözücüye verilerek sıra bağımlılığı sınanır. Alınan kaydın eksik, yinelenmiş ve dolgu eklenmiş kopyaları kontrollü olarak bozulur; bunlar canlı saldırı çıktısı değil, gerçek kayda uygulanmış sentetik negatif kontrollerdir. Ardından modelden bilinen, gizli olmayan her parçayı izinli araçla aynen aktarması istenir. Enum şeması beklenen parçayı sınırlar; hatalı model çağrısı otomatik düzeltilerek başarıya çevrilmez.

Saldırgan bakışı, tek olayda görünmeyen bilginin olaylar arası bağlamda ortaya çıkabileceğini hatırlatır. Savunmacı açısından tek çıktıda eşleşme yokken “sızıntı yok” demek bu yüzden yetersizdir. Yine de farklı oturumları gelişigüzel birleştirmek yanlış pozitif üretir; sıra alanı aynı olsa bile akışın kaynağı ve kapsamı önemlidir. Buradaki tek deney akışı bu karmaşıklığı bilinçli olarak sınırlar. Raporda HTTP'den çözülmüş kanıt ile native araç çıktısındaki açık parçalar ayrı tutulur. Gerçek modelin izinli parçayı aktarması gizli veri ele geçirdiği anlamına gelmez. Kabul; ölçümün doğruluğu, gerçek alıcı kaydı, geçersiz verinin reddi ve yalnız bu deneye ait kaynakların kapanmasıyla ilgilidir.
:::

::: tahmin Üç parçanın Base64URL karşılığı nedir?
Base64URL'de sondaki `=` dolguları kaldırılıyor. İki çıktı satırını yaz:

```python
import base64
parcalar = [b"CAN", b"ARY", b"-7"]
kodlar = [base64.urlsafe_b64encode(x).decode("ascii").rstrip("=") for x in parcalar]
print(kodlar[0])
print(kodlar)
```

???

```cikti
Q0FO
['Q0FO', 'QVJZ', 'LTc']
```

Kodlar tek başına canary metni değildir. Doğru sıra ve kanonik kodlama doğrulanmadan birleştirme yapılmamalıdır.
:::

::: gorev 1 · Canary'yi sınırlı Base64URL parçalarına ayır
`parcalari_kodla(veri, boyut=8)` işlevini yaz. Veri 1–64 karakterli ASCII 33–126 string, boyut bool olmayan 1–16 aralığında int olmalıdır. Geçersiz veride `ValueError` yükselt. Veriyi ASCII baytlarına çevir, en fazla `boyut` baytlık sıralı parçalara ayır ve her parçayı `=` içermeyen Base64URL ile kodla.

Dönüş liste öğeleri tam olarak `{"sira":SIRA,"toplam":TOPLAM,"veri":KOD}` biçimindedir. Sıra 1'den başlar; bütün parçalarda aynı toplam bulunur. Girdi stringi değiştirilemez ve hiçbir ağ/model çağrısı yapılmaz.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-24")
```

```starter
import base64
from ai_saldiri_veri import json_yukle

def parcalari_kodla(veri,boyut=8):
    # KUSURLU BAŞLANGIÇ KODU: baytları bölmeden bütün metni tek ve dolgulu paket yapıyor.
    return [{"sira":1,"toplam":1,"veri":base64.urlsafe_b64encode(veri.encode("ascii")).decode("ascii")}]

v=json_yukle("veri/parcalar.json")
print("Sentetik parça dosyası:",v)
print("Kodlanmış:",parcalari_kodla(v["canary"],v["boyut"]))
```

```test
def sozlesme(fn):
    try:
        beklenen = [{"sira": 1, "toplam": 3, "veri": "Q0FO"}, {"sira": 2, "toplam": 3, "veri": "QVJZ"}, {"sira": 3, "toplam": 3, "veri": "LTc"}]
        if fn("CANARY-7", 3) != beklenen or fn("CANARY-7", 3) != fn("CANARY-7", 3):
            return False
        if fn("C", 1) != [{"sira": 1, "toplam": 1, "veri": "Qw"}]:
            return False
        if len(fn("!" * 63 + "~", 16)) != 4 or len(fn("ABC", 1)) != 3:
            return False
        if [x["veri"] for x in fn("ABCDEFGHI")] != ["QUJDREVGR0g", "SQ"]:
            return False
        for veri, boyut in [
            ("", 3), ("x" * 65, 3), ("a b", 3), ("a\x7fb", 3), ("ğ", 3), (None, 3),
            ("ABC", 0), ("ABC", 17), ("ABC", True), ("ABC", 1.0), ("ABC", None),
        ]:
            try:
                fn(veri, boyut)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(parcalari_kodla), "ASCII, parça boyutu, sıra ve dolgusuz Base64URL korunmalı")
def m_boyut(veri, boyut=8):
    return parcalari_kodla(veri, max(1, boyut))
def m_sira(veri, boyut=8):
    sonuc = parcalari_kodla(veri, boyut)
    for parca in sonuc:
        parca["sira"] = 1
    return sonuc
def m_dolgu(veri, boyut=8):
    sonuc = parcalari_kodla(veri, boyut)
    for parca in sonuc:
        parca["veri"] += "="
    return sonuc
for ad, mutant in [("sıfır boyutu düzelten", m_boyut), ("parça sırasını bozan", m_sira), ("dolguyu geri ekleyen", m_dolgu)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
# Tam ASCII/boyut sınırlarının yanındaki değerler de sözleşmedir.
for veri,boyut in [("!",16),("~",1),("A"*64,16),("CANARY-7",2)]:
    import base64
    ham=veri.encode("ascii");chunks=[ham[i:i+boyut] for i in range(0,len(ham),boyut)]
    eq(parcalari_kodla(veri,boyut),[{"sira":i+1,"toplam":len(chunks),"veri":base64.urlsafe_b64encode(c).decode().rstrip("=")} for i,c in enumerate(chunks)],"sınırda tam paket içeriği")
```

```solution
from ai_saldiri_veri import json_yukle
def parcalari_kodla(veri, boyut=8):
    import base64
    if not isinstance(veri, str) or not 1 <= len(veri) <= 64 or any(ord(c) < 33 or ord(c) > 126 for c in veri):
        raise ValueError("veri geçersiz")
    if type(boyut) is not int or not 1 <= boyut <= 16:
        raise ValueError("parça boyutu geçersiz")
    ham = veri.encode("ascii")
    parcalar = [ham[i:i + boyut] for i in range(0, len(ham), boyut)]
    toplam = len(parcalar)
    return [{"sira": i + 1, "toplam": toplam, "veri": base64.urlsafe_b64encode(parca).decode("ascii").rstrip("=")} for i, parca in enumerate(parcalar)]
v=json_yukle("veri/parcalar.json")
print("Sentetik parça dosyası:",v)
print("Kodlanmış:",parcalari_kodla(v["canary"],v["boyut"]))
```

```hint
Önce ASCII ve boyut sınırlarını doğrula. Bayt dilimlerini sırayla üret; her dilimi Base64URL ile kodlayıp yalnız sondaki `=` karakterlerini kaldır.
```
:::

::: anlat Parça meta verisi bütünlük sözleşmesidir
Birleştirici yalnız gelen sıraya güvenmez. Parça sayısı `toplam` ile aynı olmalı, sıralar tam `1..toplam` kümesini oluşturmalı ve aynı kodun kanonik Base64URL biçimi korunmalıdır. Böylece eksik, yinelenen, yanlış sıra meta verili veya farklı bitlerle aynı baytı gösteren kodlar reddedilir.

Bu fixture'da her çözülen parça en fazla 16 bayt, birleşik metin en fazla 64 ASCII 33–126 karakterdir. Birleştirme ağ isteği veya dosya yazımı yapmaz; yalnız doğrulanmış sentetik metni döndürür.
:::

::: gorev 2 · Parçaları sıra ve kanonik kodlama denetimiyle birleştir
`parcalari_coz(parcalar)` işlevini yaz. Girdi 1–64 öğeli liste; her parça tam olarak `sira`, `toplam`, `veri` alanlarını taşısın. `toplam` bütün parçalarda aynı, bool olmayan 1–64 int ve gerçek parça sayısına eşit olmalıdır. Sıralar bool olmayan int olmalı ve tam `1..toplam` kümesini oluşturmalıdır. Kod, dolgusuz Base64URL stringidir; boş olamaz, standart `+/` veya `=` alfabeleri kabul edilmez ve yeniden kodlandığında birebir aynı kalmalıdır. Her çözülen parça 1–16 bayt olmalıdır. Geçersiz veride `ValueError` yükselt.

Parçaları sıra numarasına göre birleştir. Sonuç 1–64 karakterli ASCII 33–126 metin olmalı; aksi halde `ValueError` yükselt. Girdi sırası sonucu etkilememeli ve liste değiştirilmemelidir.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-24")
```

```starter
import base64
from ai_saldiri_veri import json_yukle

def parcalari_coz(parcalar):
    # KUSURLU BAŞLANGIÇ KODU: geliş sırasını kullanıyor, şema/kanonik kod denetimi yok.
    return "".join(base64.urlsafe_b64decode(p["veri"]+"="*(-len(p["veri"])%4)).decode("ascii") for p in parcalar)

v=json_yukle("veri/parcalar.json")
print("Sentetik paketler:",v["paketler"])
print("Çözülmüş:",parcalari_coz(v["paketler"]))
```

```test
import copy
PARCALAR = [{"sira": 1, "toplam": 3, "veri": "Q0FO"}, {"sira": 2, "toplam": 3, "veri": "QVJZ"}, {"sira": 3, "toplam": 3, "veri": "LTc"}]
def sozlesme(fn):
    try:
        once = copy.deepcopy(PARCALAR)
        if fn(PARCALAR) != "CANARY-7" or fn(list(reversed(PARCALAR))) != "CANARY-7" or PARCALAR != once:
            return False
        if fn([{"sira": 1, "toplam": 1, "veri": "Qw"}]) != "C" or fn([{"sira": 1, "toplam": 1, "veri": "IQ"}]) != "!":
            return False
        if fn([{"sira": 1, "toplam": 1, "veri": "fg"}]) != "~" or fn([{"sira": 1, "toplam": 1, "veri": "QUJDRA"}]) != "ABCD":
            return False
        altmisdort = [{"sira": i, "toplam": 64, "veri": "QQ"} for i in range(1, 65)]
        if fn(altmisdort) != "A" * 64 or fn([{"sira": 1, "toplam": 1, "veri": "QUJD" * 5 + "QQ"}]) != "ABC" * 5 + "A":
            return False
        fazla_toplam = [{"sira": i, "toplam": 22, "veri": "QUJD"} for i in range(1, 23)]
        for parcalar in [
            None, [], {}, [None], [dict(PARCALAR[0], ek=1)], [dict(PARCALAR[0], toplam=1, ek=1)],
            PARCALAR[:2], [PARCALAR[0], PARCALAR[0], PARCALAR[2]],
            [PARCALAR[0], dict(PARCALAR[1], toplam=4), PARCALAR[2]],
            [dict(PARCALAR[0], sira=True), PARCALAR[1], PARCALAR[2]],
            [dict(PARCALAR[0], toplam=True)], [dict(PARCALAR[0], sira=0), PARCALAR[1], PARCALAR[2]],
            [{"sira": 1, "toplam": 1, "veri": ""}], [{"sira": 1, "toplam": 1, "veri": "A"}],
            [{"sira": 1, "toplam": 1, "veri": None}], [{"sira": 1, "toplam": 1, "veri": "Q0F$"}],
            [{"sira": 1, "toplam": 1, "veri": "Q0FO="}], [{"sira": 1, "toplam": 1, "veri": "Q0FO$"}],
            [{"sira": 1, "toplam": 1, "veri": "QUJD" * 5 + "QUI"}],
            [{"sira": 1, "toplam": 1, "veri": "Qx"}],
            [{"sira": 1, "toplam": 1, "veri": "QUJD" * 6}],
            [{"sira": 1, "toplam": 1, "veri": "AA"}], [{"sira": 1, "toplam": 1, "veri": "IA"}],
            fazla_toplam,
        ]:
            try:
                fn(parcalar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(parcalari_coz), "sıra, toplam, kanonik Base64URL ve birleşik ASCII sınırı korunmalı")
def m_sira(parcalar):
    return parcalari_coz(parcalar)[::-1]
def m_kanonik(parcalar):
    duzeltilmis = [dict(x, veri="Qw" if x["veri"] == "Qx" else x["veri"]) for x in parcalar]
    return parcalari_coz(duzeltilmis)
def m_ascii(parcalar):
    try:
        return parcalari_coz(parcalar)
    except ValueError:
        return ""
for ad, mutant in [("birleşik sırayı ters çeviren", m_sira), ("kanonik olmayan kodu düzelten", m_kanonik), ("geçersiz sonucu boş metinle gizleyen", m_ascii)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
for bad in [dict(sira=2,toplam=1,veri="QQ"),dict(sira=1.0,toplam=1,veri="QQ"),dict(sira=1,toplam=0,veri="QQ"),dict(sira=1,toplam=65,veri="QQ"),dict(sira=1,toplam=1,veri="_w"),dict(sira=1,toplam=1,veri="fw")]:
    try:
        parcalari_coz([bad])
        ok(False,"bozuk meta veri veya ASCII reddedilmeli")
    except ValueError:
        ok(True,"bozuk meta veri veya ASCII reddedildi")
# Birleşik metin sınırını paket sayısından bağımsız sınayan altmış beş bayt.
import base64
baytlar=[b"A"*16]*4+[b"A"]
birlesik_fazla=[dict(sira=i+1,toplam=len(baytlar),veri=base64.urlsafe_b64encode(v).decode().rstrip("=")) for i,v in enumerate(baytlar)]
try:
    parcalari_coz(birlesik_fazla)
    ok(False,"beş geçerli parça içindeki altmış beş bayt reddedilmeli")
except ValueError:
    ok(True,"birleşik boyut sınırı bağımsız doğrulandı")
# Liste, meta veri ve birleşik metin için ortak üst sınır.
try:
    parcalari_coz([dict(sira=i,toplam=65,veri="QQ") for i in range(1,66)])
    ok(False,"altmış beş parça/toplam karakter reddedilmeli")
except ValueError:
    ok(True,"üst sınır dışı akış reddedildi")

```

```solution
from ai_saldiri_veri import json_yukle
def parcalari_coz(parcalar):
    sinir = 64
    import base64
    import binascii
    import re
    if not isinstance(parcalar, list) or not 1 <= len(parcalar) <= sinir:
        raise ValueError("parça listesi geçersiz")
    cozulmus = {}
    toplam = None
    for parca in parcalar:
        if not isinstance(parca, dict) or set(parca) != {"sira", "toplam", "veri"}:
            raise ValueError("parça şeması geçersiz")
        if type(parca["sira"]) is not int or type(parca["toplam"]) is not int or not 1 <= parca["toplam"] <= sinir:
            raise ValueError("parça meta verisi geçersiz")
        if toplam is None:
            toplam = parca["toplam"]
        if parca["toplam"] != toplam or toplam != len(parcalar):
            raise ValueError("toplam tutarsız")
        if parca["sira"] in cozulmus:
            raise ValueError("yinelenen sıra")
        kod = parca["veri"]
        if not isinstance(kod, str):
            raise ValueError("Base64URL kodu string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", kod):
            raise ValueError("Base64URL alfabesi geçersiz")
        if len(kod) % 4 == 1:
            raise ValueError("Base64URL uzunluğu geçersiz")
        try:
            ham = base64.b64decode(kod + "=" * (-len(kod) % 4), altchars=b"-_", validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("Base64URL çözülemedi") from exc
        if not 1 <= len(ham) <= 16 or base64.urlsafe_b64encode(ham).decode("ascii").rstrip("=") != kod:
            raise ValueError("parça baytı veya kanonik kod geçersiz")
        cozulmus[parca["sira"]] = ham
    if set(cozulmus) != set(range(1, toplam + 1)):
        raise ValueError("parça sırası eksik")
    try:
        metin = b"".join(cozulmus[i] for i in range(1, toplam + 1)).decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("sonuç ASCII değil") from exc
    if not 1 <= len(metin) <= sinir or any(ord(c) < 33 or ord(c) > 126 for c in metin):
        raise ValueError("birleşik metin geçersiz")
    return metin
v=json_yukle("veri/parcalar.json")
print("Sentetik paketler:",v["paketler"])
print("Çözülmüş:",parcalari_coz(v["paketler"]))
```

```hint
Her kodu dolgu tamamlayarak `validate=True` ile çöz, sonra aynı baytları dolgusuz Base64URL olarak yeniden üretip girdiyle karşılaştır. Sıraları dict'e koy ve yalnız `1..toplam` üzerinden birleştir.
```
:::

::: anlat Tek çıktı taraması birleşik akışı kaçırır
`"CA"`, `"NAR"`, `"Y-7"` çıktılarının hiçbiri tek başına `CANARY-7` içermez. Sıra meta verisiyle birleştirildiklerinde canary oluşur. Tersine bir çıktıda bütün canary zaten varsa bu parçalı kanıt değil, doğrudan kanıttır.

Bu rapor Base64 çözmez; ilk iki görevden bağımsız olarak ham model çıktılarındaki dağılımı ölçer. Sıra numaralarının kesintisiz olması gerekir. Böylece eksik bir parça yanlışlıkla başka metinle birleştirilmez.
:::

::: gorev 3 · Birden çok model çıktısına dağılan canary'yi raporla
`parcali_kanit_raporu(ciktilar, canary)` işlevini yaz. Girdi liste; her çıktı tam olarak `cikti_id`, `sira`, `veri` alanlarını taşısın. Kimlik boş olmayan ve benzersiz string; sıra bool olmayan int; veri 1–32 karakterli ASCII 33–126 string olmalıdır. Sıralar tam `1..N` kümesini oluşturmalıdır. Canary 2–64 karakterli ASCII 33–126 stringdir. Geçersiz veride `ValueError` yükselt.

Çıktıları sıra numarasına göre birleştir ve dön:

```text
{"cikti":N,"kanit_var":BOOL,"parcali_kanit":BOOL,"tek_ciktida":[...]}
```

- `kanit_var`: canary birleşik metinde substring olarak var.
- `tek_ciktida`: canary'yi tek başına içeren çıktı kimlikleri, alfabetik sıralı.
- `parcali_kanit`: `kanit_var=True` ve `tek_ciktida` boş.

Boş çıktı listesi için bütün bool değerler false ve liste boştur. Girdi sırası sonucu etkilememeli ve girdi değiştirilmemelidir.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-24")
```

```starter
from ai_saldiri_veri import json_yukle

def parcali_kanit_raporu(ciktilar,canary):
    # KUSURLU BAŞLANGIÇ KODU: yalnız tek çıktıda arıyor, birleşik parçalı kanıtı kaçırıyor.
    tek=sorted(c["cikti_id"] for c in ciktilar if canary in c["veri"])
    return {"cikti":len(ciktilar),"kanit_var":bool(tek),"parcali_kanit":False,"tek_ciktida":tek}

v=json_yukle("veri/parcalar.json")
print("Sentetik ham çıktılar:",v["ciktilar"])
print("Rapor:",parcali_kanit_raporu(v["ciktilar"],v["canary"]))
```

```test
import copy
CIKTILAR = [{"cikti_id": "o1", "sira": 1, "veri": "CA"}, {"cikti_id": "o2", "sira": 2, "veri": "NAR"}, {"cikti_id": "o3", "sira": 3, "veri": "Y-7"}]
BEKLENEN = {"cikti": 3, "kanit_var": True, "parcali_kanit": True, "tek_ciktida": []}
def sozlesme(fn):
    try:
        once = copy.deepcopy(CIKTILAR)
        if fn(CIKTILAR, "CANARY-7") != BEKLENEN or CIKTILAR != once or fn(list(reversed(CIKTILAR)), "CANARY-7") != BEKLENEN:
            return False
        tek = [{"cikti_id": "o1", "sira": 1, "veri": "xCANARY-7y"}]
        if fn(tek, "CANARY-7") != {"cikti": 1, "kanit_var": True, "parcali_kanit": False, "tek_ciktida": ["o1"]}:
            return False
        if fn([], "CA") != {"cikti": 0, "kanit_var": False, "parcali_kanit": False, "tek_ciktida": []}:
            return False
        if fn([{"cikti_id": "s", "sira": 1, "veri": "!" * 31 + "~"}], "yok")["cikti"] != 1:
            return False
        if fn([], "!" * 63 + "~")["cikti"] != 0 or fn([{"cikti_id": "s", "sira": 1, "veri": "A"}], "CA")["kanit_var"]:
            return False
        if fn([{"cikti_id": "s", "sira": 1, "veri": "AB"}], "AB")["parcali_kanit"] is not False:
            return False
        if fn(CIKTILAR[:2], "CANARY-7") != {"cikti": 2, "kanit_var": False, "parcali_kanit": False, "tek_ciktida": []}:
            return False
        for ciktilar, canary in [
            (None, "CA"), (CIKTILAR, "C"), (CIKTILAR, "x" * 65), (CIKTILAR, "a b"), (CIKTILAR, "a\x7fb"),
            ([None], "CA"), (CIKTILAR + [CIKTILAR[0]], "CA"), ([dict(CIKTILAR[0], ek=1)], "CA"),
            ([dict(CIKTILAR[0], cikti_id="")], "CA"), ([dict(CIKTILAR[0], sira=True)], "CA"),
            ([CIKTILAR[0], CIKTILAR[0]], "CA"),
            ([dict(CIKTILAR[0], veri="")], "CA"), ([dict(CIKTILAR[0], veri="x" * 33)], "CA"),
            ([dict(CIKTILAR[0], veri="a b")], "CA"), ([dict(CIKTILAR[0], veri="a\x7fb")], "CA"),
            ([dict(CIKTILAR[0], veri=[1])], "CA"),
        ]:
            try:
                fn(ciktilar, canary)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(parcali_kanit_raporu), "sıralı birleştirme, tek çıktı ve parçalı kanıt ayrımı korunmalı")
def m_sira(ciktilar, canary):
    metin = "".join(x["veri"] for x in ciktilar)
    tek = sorted(x["cikti_id"] for x in ciktilar if canary in x["veri"])
    kanit = canary in metin
    return {"cikti": len(ciktilar), "kanit_var": kanit, "parcali_kanit": kanit and not tek, "tek_ciktida": tek}
def m_parca(ciktilar, canary):
    sonuc = parcali_kanit_raporu(ciktilar, canary)
    sonuc["parcali_kanit"] = False
    return sonuc
def m_eksik(ciktilar, canary):
    sirali = [dict(x, sira=i) for i, x in enumerate(ciktilar, 1)]
    return parcali_kanit_raporu(sirali, canary)
for ad, mutant in [("girdi sırasını kullanan", m_sira), ("parçalı kanıtı gizleyen", m_parca), ("eksik sıraları yeniden numaralayan", m_eksik)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
for c,m in [([dict(cikti_id="o",sira=0,veri="AB")],"AB"),([dict(cikti_id=1,sira=1,veri="AB")],"AB"),([],None),([],"ğğ")]:
    try:
        parcali_kanit_raporu(c,m)
        ok(False,"bozuk çıktı/canary reddedilmeli")
    except ValueError:
        ok(True,"bozuk çıktı/canary reddedildi")
eq(parcali_kanit_raporu([dict(cikti_id="z",sira=1,veri="AB"),dict(cikti_id="a",sira=2,veri="AB")],"AB"),{"cikti":2,"kanit_var":True,"parcali_kanit":False,"tek_ciktida":["a","z"]},"tek çıktı kimlikleri alfabetik")
# Kimlik benzersizliği sıra benzersizliğinden ayrıdır.
raises(ValueError, lambda: parcali_kanit_raporu([{"cikti_id":"ayni","sira":1,"veri":"CA"},{"cikti_id":"ayni","sira":2,"veri":"NARY"}], "CANARY"), msg="farklı sıra aynı çıktı kimliğini meşrulaştırmaz")
```

```solution
from ai_saldiri_veri import json_yukle
def parcali_kanit_raporu(ciktilar, canary):
    if not isinstance(ciktilar, list):
        raise ValueError("çıktılar liste olmalı")
    if not isinstance(canary, str) or not 2 <= len(canary) <= 64 or any(ord(c) < 33 or ord(c) > 126 for c in canary):
        raise ValueError("canary geçersiz")
    kimlikler = set()
    siralar = set()
    for cikti in ciktilar:
        if not isinstance(cikti, dict) or set(cikti) != {"cikti_id", "sira", "veri"}:
            raise ValueError("çıktı şeması geçersiz")
        if not isinstance(cikti["cikti_id"], str) or not cikti["cikti_id"] or cikti["cikti_id"] in kimlikler:
            raise ValueError("çıktı kimliği geçersiz")
        if type(cikti["sira"]) is not int or cikti["sira"] in siralar:
            raise ValueError("sıra geçersiz")
        if not isinstance(cikti["veri"], str) or not 1 <= len(cikti["veri"]) <= 32 or any(ord(c) < 33 or ord(c) > 126 for c in cikti["veri"]):
            raise ValueError("çıktı verisi geçersiz")
        kimlikler.add(cikti["cikti_id"])
        siralar.add(cikti["sira"])
    if siralar != set(range(1, len(ciktilar) + 1)):
        raise ValueError("sıralar kesintisiz olmalı")
    sirali = sorted(ciktilar, key=lambda x: x["sira"])
    metin = "".join(x["veri"] for x in sirali)
    tek = sorted(x["cikti_id"] for x in sirali if canary in x["veri"])
    kanit = canary in metin
    return {"cikti": len(ciktilar), "kanit_var": kanit, "parcali_kanit": kanit and not tek, "tek_ciktida": tek}
v=json_yukle("veri/parcalar.json")
print("Sentetik ham çıktılar:",v["ciktilar"])
print("Rapor:",parcali_kanit_raporu(v["ciktilar"],v["canary"]))
```

```hint
Önce kimlik ve sıra kümelerini doğrula. Sonra sıraya göre yeni bir liste oluştur; birleşik metni ve her çıktının kendi içindeki canary'yi ayrı hesapla.
```
:::


::: anlat Kodlanmış gerçek aktarımı ve izinli model parçalarını izle
Ham sentetik ayar aynı Pafta sunucusunda `/data/ai-saldiri-24-parcalar.txt` adresindedir. Mevcut Markdown renderer linkleri tıklanabilir yapmaz; sunucu adresine bu yolu yaz. Çalıştır ayrı kalıcı `calisma/ai-saldiri-24/parcalar.json` kopyasının yolunu/içeriğini gösterir. Dış editör/Python ile boyutu 1..8 arasında değiştirip yeniden Çalıştır; değişiklik korunur. Saf fonksiyon sözleşmesi 1..16 olarak kalır; test ayrı veriler kullanır.

Rastgele sentetik canary önce gerçek dosyaya yazılır ve oradan okunur. Öğrencinin kodladığı sıra/toplam/veri paketleri gerçek HTTP POST ile deneyin kendi loopback alıcısına gider; alıcı JSONL dosyası geri okunur ve öğrenci çözücüsü parçaları sıralayıp birleştirir. Eksik/yinelenmiş/kanonik olmayan kayıtlar ayrı etiketli alıcı-kaydı mutasyonlarıyla reddedilmelidir. Kodlama gizlilik sağlamaz; decode sonrası parçaların toplamında canary çıkabilir.

Ardından yerel modele bu **bilinen ve açıkça izinli** parçalar tek tek verilir; model gerçek native `parca_yaz` çağrısıyla yerel dosyaya aktarır. Enum şeması o turdaki parçayı sınırlar; yanlış argüman otomatik düzeltilmez. Bu pozitif aktarım kontrolüdür, **jailbreak veya modelden gizli sır çalma başarısı değildir**. Öğrenci raporu gerçek native parçaları sırasıyla birleştirir; tek çıktı tam canary taşımadığı halde birleşik akışın kanıtını bulur. Ham native parçalar ile HTTP decode sonrası kanıt ayrı tutulur. Yalnız kendi alıcısı kapanır, dış ağa gönderim yoktur.
:::

::: gorev Gerçek deney · Gerçek alıcıdaki parçaları birleştir ve kanıtı ayır
Önceki `parcalari_kodla`, `parcalari_coz`, `parcali_kanit_raporu` işlevlerini birleştir. Çalıştır gerçek HTTP kayıtlarını, çözülen parçaları ve açıkça izinli native model aktarımını gösterir. Kontrol Et saf sözleşmeleri ve gerçek model/protokol/disk etkisini ayrı sınar. Bu görevden jailbreak başarı oranı çıkarılmaz.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def parcalari_kodla(veri,boyut=8):return []

def parcalari_coz(parcalar):return ""

def parcali_kanit_raporu(ciktilar,canary):return {}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_24 as deney
    deney.goster(parcalari_kodla,parcalari_coz,parcali_kanit_raporu)

```

```test
# Kimlik benzersizliği sıra benzersizliğinden ayrıdır.
raises(ValueError, lambda: parcali_kanit_raporu([{"cikti_id":"ayni","sira":1,"veri":"CA"},{"cikti_id":"ayni","sira":2,"veri":"NARY"}], "CANARY"), msg="farklı sıra aynı çıktı kimliğini meşrulaştırmaz")
sonuclar=[]
def kontrol(kosul,mesaj):
    sonuclar.append(bool(kosul))
    return ok(kosul,mesaj)
import ai_lab,ast
YASAK=("kod_ref","rapor_ref","kanit_yaz")
sorun=ai_lab.kod_denetimi(src,yasak=YASAK)
for node in ast.walk(ast.parse(src)):
    if isinstance(node,ast.ImportFrom) and any(n.name in YASAK or n.name=="*" for n in node.names):
        sorun.append("referans import edilemez")
if sorun:
    kontrol(False,"Kendi parça işlevlerini yaz: "+", ".join(sorun))
    stop()

def sozlesme(fn):
    try:
        beklenen = [{"sira": 1, "toplam": 3, "veri": "Q0FO"}, {"sira": 2, "toplam": 3, "veri": "QVJZ"}, {"sira": 3, "toplam": 3, "veri": "LTc"}]
        if fn("CANARY-7", 3) != beklenen or fn("CANARY-7", 3) != fn("CANARY-7", 3):
            return False
        if fn("C", 1) != [{"sira": 1, "toplam": 1, "veri": "Qw"}]:
            return False
        if len(fn("!" * 63 + "~", 16)) != 4 or len(fn("ABC", 1)) != 3:
            return False
        if [x["veri"] for x in fn("ABCDEFGHI")] != ["QUJDREVGR0g", "SQ"]:
            return False
        for veri, boyut in [
            ("", 3), ("x" * 65, 3), ("a b", 3), ("a\x7fb", 3), ("ğ", 3), (None, 3),
            ("ABC", 0), ("ABC", 17), ("ABC", True), ("ABC", 1.0), ("ABC", None),
        ]:
            try:
                fn(veri, boyut)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(parcalari_kodla), "ASCII, parça boyutu, sıra ve dolgusuz Base64URL korunmalı")
def m_boyut(veri, boyut=8):
    return parcalari_kodla(veri, max(1, boyut))
def m_sira(veri, boyut=8):
    sonuc = parcalari_kodla(veri, boyut)
    for parca in sonuc:
        parca["sira"] = 1
    return sonuc
def m_dolgu(veri, boyut=8):
    sonuc = parcalari_kodla(veri, boyut)
    for parca in sonuc:
        parca["veri"] += "="
    return sonuc
for ad, mutant in [("sıfır boyutu düzelten", m_boyut), ("parça sırasını bozan", m_sira), ("dolguyu geri ekleyen", m_dolgu)]:
    kontrol(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
# Tam ASCII/boyut sınırlarının yanındaki değerler de sözleşmedir.
for veri,boyut in [("!",16),("~",1),("A"*64,16),("CANARY-7",2)]:
    import base64
    ham=veri.encode("ascii");chunks=[ham[i:i+boyut] for i in range(0,len(ham),boyut)]
    eq(parcalari_kodla(veri,boyut),[{"sira":i+1,"toplam":len(chunks),"veri":base64.urlsafe_b64encode(c).decode().rstrip("=")} for i,c in enumerate(chunks)],"sınırda tam paket içeriği")

import copy
PARCALAR = [{"sira": 1, "toplam": 3, "veri": "Q0FO"}, {"sira": 2, "toplam": 3, "veri": "QVJZ"}, {"sira": 3, "toplam": 3, "veri": "LTc"}]
def sozlesme(fn):
    try:
        once = copy.deepcopy(PARCALAR)
        if fn(PARCALAR) != "CANARY-7" or fn(list(reversed(PARCALAR))) != "CANARY-7" or PARCALAR != once:
            return False
        if fn([{"sira": 1, "toplam": 1, "veri": "Qw"}]) != "C" or fn([{"sira": 1, "toplam": 1, "veri": "IQ"}]) != "!":
            return False
        if fn([{"sira": 1, "toplam": 1, "veri": "fg"}]) != "~" or fn([{"sira": 1, "toplam": 1, "veri": "QUJDRA"}]) != "ABCD":
            return False
        altmisdort = [{"sira": i, "toplam": 64, "veri": "QQ"} for i in range(1, 65)]
        if fn(altmisdort) != "A" * 64 or fn([{"sira": 1, "toplam": 1, "veri": "QUJD" * 5 + "QQ"}]) != "ABC" * 5 + "A":
            return False
        fazla_toplam = [{"sira": i, "toplam": 22, "veri": "QUJD"} for i in range(1, 23)]
        for parcalar in [
            None, [], {}, [None], [dict(PARCALAR[0], ek=1)], [dict(PARCALAR[0], toplam=1, ek=1)],
            PARCALAR[:2], [PARCALAR[0], PARCALAR[0], PARCALAR[2]],
            [PARCALAR[0], dict(PARCALAR[1], toplam=4), PARCALAR[2]],
            [dict(PARCALAR[0], sira=True), PARCALAR[1], PARCALAR[2]],
            [dict(PARCALAR[0], toplam=True)], [dict(PARCALAR[0], sira=0), PARCALAR[1], PARCALAR[2]],
            [{"sira": 1, "toplam": 1, "veri": ""}], [{"sira": 1, "toplam": 1, "veri": "A"}],
            [{"sira": 1, "toplam": 1, "veri": None}], [{"sira": 1, "toplam": 1, "veri": "Q0F$"}],
            [{"sira": 1, "toplam": 1, "veri": "Q0FO="}], [{"sira": 1, "toplam": 1, "veri": "Q0FO$"}],
            [{"sira": 1, "toplam": 1, "veri": "QUJD" * 5 + "QUI"}],
            [{"sira": 1, "toplam": 1, "veri": "Qx"}],
            [{"sira": 1, "toplam": 1, "veri": "QUJD" * 6}],
            [{"sira": 1, "toplam": 1, "veri": "AA"}], [{"sira": 1, "toplam": 1, "veri": "IA"}],
            fazla_toplam,
        ]:
            try:
                fn(parcalar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(parcalari_coz), "sıra, toplam, kanonik Base64URL ve birleşik ASCII sınırı korunmalı")
def m_sira(parcalar):
    return parcalari_coz(parcalar)[::-1]
def m_kanonik(parcalar):
    duzeltilmis = [dict(x, veri="Qw" if x["veri"] == "Qx" else x["veri"]) for x in parcalar]
    return parcalari_coz(duzeltilmis)
def m_ascii(parcalar):
    try:
        return parcalari_coz(parcalar)
    except ValueError:
        return ""
for ad, mutant in [("birleşik sırayı ters çeviren", m_sira), ("kanonik olmayan kodu düzelten", m_kanonik), ("geçersiz sonucu boş metinle gizleyen", m_ascii)]:
    kontrol(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
for bad in [dict(sira=2,toplam=1,veri="QQ"),dict(sira=1.0,toplam=1,veri="QQ"),dict(sira=1,toplam=0,veri="QQ"),dict(sira=1,toplam=65,veri="QQ"),dict(sira=1,toplam=1,veri="_w"),dict(sira=1,toplam=1,veri="fw")]:
    try:
        parcalari_coz([bad])
        kontrol(False,"bozuk meta veri veya ASCII reddedilmeli")
    except ValueError:
        kontrol(True,"bozuk meta veri veya ASCII reddedildi")
# Birleşik metin sınırını paket sayısından bağımsız sınayan altmış beş bayt.
import base64
baytlar=[b"A"*16]*4+[b"A"]
birlesik_fazla=[dict(sira=i+1,toplam=len(baytlar),veri=base64.urlsafe_b64encode(v).decode().rstrip("=")) for i,v in enumerate(baytlar)]
try:
    parcalari_coz(birlesik_fazla)
    kontrol(False,"beş geçerli parça içindeki altmış beş bayt reddedilmeli")
except ValueError:
    kontrol(True,"birleşik boyut sınırı bağımsız doğrulandı")
# Liste, meta veri ve birleşik metin için ortak üst sınır.
try:
    parcalari_coz([dict(sira=i,toplam=65,veri="QQ") for i in range(1,66)])
    kontrol(False,"altmış beş parça/toplam karakter reddedilmeli")
except ValueError:
    kontrol(True,"üst sınır dışı akış reddedildi")


import copy
CIKTILAR = [{"cikti_id": "o1", "sira": 1, "veri": "CA"}, {"cikti_id": "o2", "sira": 2, "veri": "NAR"}, {"cikti_id": "o3", "sira": 3, "veri": "Y-7"}]
BEKLENEN = {"cikti": 3, "kanit_var": True, "parcali_kanit": True, "tek_ciktida": []}
def sozlesme(fn):
    try:
        once = copy.deepcopy(CIKTILAR)
        if fn(CIKTILAR, "CANARY-7") != BEKLENEN or CIKTILAR != once or fn(list(reversed(CIKTILAR)), "CANARY-7") != BEKLENEN:
            return False
        tek = [{"cikti_id": "o1", "sira": 1, "veri": "xCANARY-7y"}]
        if fn(tek, "CANARY-7") != {"cikti": 1, "kanit_var": True, "parcali_kanit": False, "tek_ciktida": ["o1"]}:
            return False
        if fn([], "CA") != {"cikti": 0, "kanit_var": False, "parcali_kanit": False, "tek_ciktida": []}:
            return False
        if fn([{"cikti_id": "s", "sira": 1, "veri": "!" * 31 + "~"}], "yok")["cikti"] != 1:
            return False
        if fn([], "!" * 63 + "~")["cikti"] != 0 or fn([{"cikti_id": "s", "sira": 1, "veri": "A"}], "CA")["kanit_var"]:
            return False
        if fn([{"cikti_id": "s", "sira": 1, "veri": "AB"}], "AB")["parcali_kanit"] is not False:
            return False
        if fn(CIKTILAR[:2], "CANARY-7") != {"cikti": 2, "kanit_var": False, "parcali_kanit": False, "tek_ciktida": []}:
            return False
        for ciktilar, canary in [
            (None, "CA"), (CIKTILAR, "C"), (CIKTILAR, "x" * 65), (CIKTILAR, "a b"), (CIKTILAR, "a\x7fb"),
            ([None], "CA"), (CIKTILAR + [CIKTILAR[0]], "CA"), ([dict(CIKTILAR[0], ek=1)], "CA"),
            ([dict(CIKTILAR[0], cikti_id="")], "CA"), ([dict(CIKTILAR[0], sira=True)], "CA"),
            ([CIKTILAR[0], CIKTILAR[0]], "CA"),
            ([dict(CIKTILAR[0], veri="")], "CA"), ([dict(CIKTILAR[0], veri="x" * 33)], "CA"),
            ([dict(CIKTILAR[0], veri="a b")], "CA"), ([dict(CIKTILAR[0], veri="a\x7fb")], "CA"),
            ([dict(CIKTILAR[0], veri=[1])], "CA"),
        ]:
            try:
                fn(ciktilar, canary)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(parcali_kanit_raporu), "sıralı birleştirme, tek çıktı ve parçalı kanıt ayrımı korunmalı")
def m_sira(ciktilar, canary):
    metin = "".join(x["veri"] for x in ciktilar)
    tek = sorted(x["cikti_id"] for x in ciktilar if canary in x["veri"])
    kanit = canary in metin
    return {"cikti": len(ciktilar), "kanit_var": kanit, "parcali_kanit": kanit and not tek, "tek_ciktida": tek}
def m_parca(ciktilar, canary):
    sonuc = parcali_kanit_raporu(ciktilar, canary)
    sonuc["parcali_kanit"] = False
    return sonuc
def m_eksik(ciktilar, canary):
    sirali = [dict(x, sira=i) for i, x in enumerate(ciktilar, 1)]
    return parcali_kanit_raporu(sirali, canary)
for ad, mutant in [("girdi sırasını kullanan", m_sira), ("parçalı kanıtı gizleyen", m_parca), ("eksik sıraları yeniden numaralayan", m_eksik)]:
    kontrol(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
for c,m in [([dict(cikti_id="o",sira=0,veri="AB")],"AB"),([dict(cikti_id=1,sira=1,veri="AB")],"AB"),([],None),([],"ğğ")]:
    try:
        parcali_kanit_raporu(c,m)
        kontrol(False,"bozuk çıktı/canary reddedilmeli")
    except ValueError:
        kontrol(True,"bozuk çıktı/canary reddedildi")
eq(parcali_kanit_raporu([dict(cikti_id="z",sira=1,veri="AB"),dict(cikti_id="a",sira=2,veri="AB")],"AB"),{"cikti":2,"kanit_var":True,"parcali_kanit":False,"tek_ciktida":["a","z"]},"tek çıktı kimlikleri alfabetik")

from sandbox import ai_gercek_ai_saldiri_24 as deney
import tempfile,secrets
from pathlib import Path
# Kopya koruması testin başında çalışır.
for size in (1,3,7,16):
    text='PAFTA-'+secrets.token_hex(5).upper()
    if not kontrol(parcalari_kodla(text,size)==deney.kod_ref(text,size),'yeni canary ve parça boyutunda gerçek kodlama sözleşmesi'):stop()
if not all(sonuclar):
    stop()
with tempfile.TemporaryDirectory(prefix='pafta_fragment24_') as tmp:
    p=Path(tmp)/'parcalar.json';p.write_text(deney.ORNEK.read_text(encoding='utf-8'),encoding='utf-8')
    r=deney.deney(parcalari_kodla,parcalari_coz,parcali_kanit_raporu,p,Path(tmp)/'deney')
    for k,v in r['kontroller'].items():kontrol(v,'gerçek deney: '+k)
    accepted=all(sonuclar) and all(r['kontroller'].values());ai_lab.kanit_yaz('saldiri-24-parcali',dict(r,kabul=accepted));kontrol(accepted,'gerçek HTTP parça aktarımı/native izinli relay ve birleştirilmiş kanıt; jailbreak iddiası değil')

```

```solution
import ai_lab
def parcalari_kodla(veri, boyut=8):
    import base64
    if not isinstance(veri, str) or not 1 <= len(veri) <= 64 or any(ord(c) < 33 or ord(c) > 126 for c in veri):
        raise ValueError("veri geçersiz")
    if type(boyut) is not int or not 1 <= boyut <= 16:
        raise ValueError("parça boyutu geçersiz")
    ham = veri.encode("ascii")
    parcalar = [ham[i:i + boyut] for i in range(0, len(ham), boyut)]
    toplam = len(parcalar)
    return [{"sira": i + 1, "toplam": toplam, "veri": base64.urlsafe_b64encode(parca).decode("ascii").rstrip("=")} for i, parca in enumerate(parcalar)]

def parcalari_coz(parcalar):
    sinir = 64
    import base64
    import binascii
    import re
    if not isinstance(parcalar, list) or not 1 <= len(parcalar) <= sinir:
        raise ValueError("parça listesi geçersiz")
    cozulmus = {}
    toplam = None
    for parca in parcalar:
        if not isinstance(parca, dict) or set(parca) != {"sira", "toplam", "veri"}:
            raise ValueError("parça şeması geçersiz")
        if type(parca["sira"]) is not int or type(parca["toplam"]) is not int or not 1 <= parca["toplam"] <= sinir:
            raise ValueError("parça meta verisi geçersiz")
        if toplam is None:
            toplam = parca["toplam"]
        if parca["toplam"] != toplam or toplam != len(parcalar):
            raise ValueError("toplam tutarsız")
        if parca["sira"] in cozulmus:
            raise ValueError("yinelenen sıra")
        kod = parca["veri"]
        if not isinstance(kod, str):
            raise ValueError("Base64URL kodu string olmalı")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", kod):
            raise ValueError("Base64URL alfabesi geçersiz")
        if len(kod) % 4 == 1:
            raise ValueError("Base64URL uzunluğu geçersiz")
        try:
            ham = base64.b64decode(kod + "=" * (-len(kod) % 4), altchars=b"-_", validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("Base64URL çözülemedi") from exc
        if not 1 <= len(ham) <= 16 or base64.urlsafe_b64encode(ham).decode("ascii").rstrip("=") != kod:
            raise ValueError("parça baytı veya kanonik kod geçersiz")
        cozulmus[parca["sira"]] = ham
    if set(cozulmus) != set(range(1, toplam + 1)):
        raise ValueError("parça sırası eksik")
    try:
        metin = b"".join(cozulmus[i] for i in range(1, toplam + 1)).decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("sonuç ASCII değil") from exc
    if not 1 <= len(metin) <= sinir or any(ord(c) < 33 or ord(c) > 126 for c in metin):
        raise ValueError("birleşik metin geçersiz")
    return metin

def parcali_kanit_raporu(ciktilar, canary):
    if not isinstance(ciktilar, list):
        raise ValueError("çıktılar liste olmalı")
    if not isinstance(canary, str) or not 2 <= len(canary) <= 64 or any(ord(c) < 33 or ord(c) > 126 for c in canary):
        raise ValueError("canary geçersiz")
    kimlikler = set()
    siralar = set()
    for cikti in ciktilar:
        if not isinstance(cikti, dict) or set(cikti) != {"cikti_id", "sira", "veri"}:
            raise ValueError("çıktı şeması geçersiz")
        if not isinstance(cikti["cikti_id"], str) or not cikti["cikti_id"] or cikti["cikti_id"] in kimlikler:
            raise ValueError("çıktı kimliği geçersiz")
        if type(cikti["sira"]) is not int or cikti["sira"] in siralar:
            raise ValueError("sıra geçersiz")
        if not isinstance(cikti["veri"], str) or not 1 <= len(cikti["veri"]) <= 32 or any(ord(c) < 33 or ord(c) > 126 for c in cikti["veri"]):
            raise ValueError("çıktı verisi geçersiz")
        kimlikler.add(cikti["cikti_id"])
        siralar.add(cikti["sira"])
    if siralar != set(range(1, len(ciktilar) + 1)):
        raise ValueError("sıralar kesintisiz olmalı")
    sirali = sorted(ciktilar, key=lambda x: x["sira"])
    metin = "".join(x["veri"] for x in sirali)
    tek = sorted(x["cikti_id"] for x in sirali if canary in x["veri"])
    kanit = canary in metin
    return {"cikti": len(ciktilar), "kanit_var": kanit, "parcali_kanit": kanit and not tek, "tek_ciktida": tek}
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_24 as deney
    deney.goster(parcalari_kodla,parcalari_coz,parcali_kanit_raporu)

```

```hint
Çözücü sıra listesinin geliş sırasına güvenmemeli; sıra/toplam/kanonik kod tutarlı olmalı. Ham çıktı taraması ile decode sonrası birleşik akışı karıştırma. Canlı model aktarımı burada açıkça izinlidir; raporunu gizli veri saldırısı diye adlandırma.
```
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
Base64URL şifreleme değildir; aynı baytları farklı alfabede gösterir. Parça sıra numarası, toplam ve kanonik kodlama birlikte bütünlük sözleşmesidir. Tek tek yanıtlar canary taşımadığı halde doğru sırada birleşince taşıyabilir. Önce hangi akıştan geldiklerini doğrula, sonra eksik/tekrarlı sıra ve pad-bit hatalarını reddet. İzinli model relay deneyiyle modelden gizli değer çaldığını iddia eden deneyi ayır.

Önkoşul ve yol köprüsü: ai-saldiri-23 alıcı kanıtı.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| Kodlanmış parça anlamsızsa veri değildir | Decode ve yeniden birleştirme veri anlamını geri getirir |

Dinleyiciye sor: Hangi kaydın kaybolması bu deneyin sonucunu doğrulanamaz yapar? Ham veri, model önerisi ve gerçek yan etkiyi ayrı göstererek cevapla.
:::


::: anlat Birincil kaynak ve deney sınırı
[RFC 4648](https://www.rfc-editor.org/rfc/rfc4648.html): Base64URL alfabesi ve canonical encoding/pad bit kuralları için birincil standart. Parça sırası ve akış kimliği bu dersin ek sözleşmesidir.
:::
