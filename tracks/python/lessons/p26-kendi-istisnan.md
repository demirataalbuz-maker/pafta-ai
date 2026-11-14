---
id: p26
title: Kendi İstisnaların ve EAFP
summary: Özel istisna sınıfları, raise from zinciri, EAFP ve LBYL, assert'in doğru yeri.
kazanim: PCEP 4.4, PCAP 2.1, PCAP 2.2, PCPP1 1.9
---

::: anlat Kendi hata türlerin
Kütüphane ya da araç yazarken kendi hata türlerini tanımlarsın. Böylece kodunu kullanan kişi senin hatalarını diğerlerinden ayırt edebilir. Sınıfları P36'te öğreneceğiz; şimdilik şu ilişkiyi bilmen yeterli: `class YeniHata(Exception):` yeni bir hata türü tanımlar; parantezdeki tür onun atasıdır. `pass`, gövdeye ek davranış yazılmadığını belirtir. Böylece var olan hata davranışını devralır:

```python
class AgHatasi(Exception):            #! Exception'dan türeyen yeni bir tür
    """Ağ işlemleriyle ilgili hataların atası."""

class ZamanAsimi(AgHatasi):           #! AgHatasi'nin alt türü
    pass

class BaglantiReddedildi(AgHatasi):
    pass

def baglan(host):
    if host == "yavas":
        raise ZamanAsimi(f"{host}: 5 sn içinde yanıt yok")
    if host == "kapali":
        raise BaglantiReddedildi(host)
    return "bağlandı"

for h in ["web01", "yavas", "kapali"]:
    try:
        print(baglan(h))
    except AgHatasi as e:                 #! atayı yakalayınca tüm ağ hataları gelir
        print(f"{type(e).__name__}: {e}")
```

Bir **hata hiyerarşisi** kurmak, kullanıcına seçenek verir: ister tek tek (`except ZamanAsimi`), ister toptan (`except AgHatasi`) yakalar.

### raise ... from: hata zinciri
Alt düzeydeki bir hatayı daha anlamlı bir hataya çevirirken orijinali kaybetme:

```python
class AyarHatasi(Exception):
    pass

def port_oku(ayarlar):
    try:
        return int(ayarlar["port"])
    except (KeyError, ValueError, TypeError) as e:
        raise AyarHatasi("port ayarı okunamadı") from e   #! sebep zincire eklenir

try:
    port_oku({"port": "seksen"})
except AyarHatasi as e:
    print(e, "← sebep:", repr(e.__cause__))
```

Traceback'te "The above exception was the direct cause of the following exception" satırını görürsün: iki hata da kayıtlıdır. Bir hatayı ekrana basmak yerine log dosyasına metin olarak kaydetmek istediğinde standart `traceback` modülündeki `traceback.format_exc()` çağrısı o anki hata izini (`e.__traceback__`) çok satırlı `str` olarak döndürür.
:::

::: tahmin
Çıktı tek satır:

```python
class AgHatasi(Exception):
    pass

class ZamanAsimi(AgHatasi):
    pass

try:
    raise ZamanAsimi("5 sn")
except AgHatasi as e:
    print(type(e).__name__, e)
```

???

`ZamanAsimi 5 sn`. `except AgHatasi` alt türleri de yakalar. Yakalanan nesnenin **gerçek türü** ise hâlâ `ZamanAsimi`'dir.
:::

::: anlat EAFP ve LBYL
Hatayla başa çıkmanın iki felsefesi var:

- **LBYL** (*Look Before You Leap*, "atlamadan önce bak"): önce kontrol et, sonra yap.
- **EAFP** (*Easier to Ask Forgiveness than Permission*, "izin istemektense af dilemek kolaydır"): doğrudan yap, olmazsa istisnayı yakala.

```python
roller = {"ali": "admin", "veli": "user"}

# LBYL
if "ayse" in roller:
    rol = roller["ayse"]
else:
    rol = "misafir"

# EAFP — Python'cası
try:
    rol = roller["ayse"]
except KeyError:
    rol = "misafir"
print(rol)
```

Python topluluğu genelde **EAFP**'yi tercih eder: "mutlu yol" daha okunaklıdır ve ayrı bir ön kontrol gerektirmez. İşlemin kendisinin atomik ya da yarışlardan arınmış olduğu anlamına gelmez.

> [!GÜVENLİK]
> Bu son madde bir güvenlik açığının adıdır: **TOCTOU** (*Time Of Check to Time Of Use*). `if os.path.exists(yol): open(yol)` kalıbında kontrol ile açma arasında saldırgan dosyayı bir sembolik bağla değiştirebilir. Sonuçta program, kontrol ettiği dosyayı değil başka bir dosyayı açar. Doğrudan açıp `FileNotFoundError` yakalamak gereksiz varlık ön kontrolünü kaldırır; fakat sembolik bağ yönlendirmesi ve dosya açma yetkilerini tek başına güvenceye almaz. Güvenilmeyen klasörlerde güvenlik, işletim sisteminin dosya açma ve erişim denetimlerine de bağlıdır.

> [!TUZAK]
> **`assert`'i güvenlik ya da girdi kontrolü için kullanma.** `assert kullanici.yetkili` gibi bir satır, Python `-O` (optimize) bayrağıyla çalıştırıldığında **tamamen silinir**. Kontrolün yok olur. `assert` sadece "bu asla olmamalı" türünden iç tutarlılık kontrolleri ve testler içindir. Gerçek kontroller `if` + `raise` ile yapılır.

> [!DERİN]
> Python 3.11 **istisna grupları** getirdi: aynı anda birden çok bağımsız hata (ör. paralel 10 isteğin 3'ü başarısız) `ExceptionGroup` olarak yükselir ve `except*` ile türlerine göre ayrı ayrı yakalanır. Bunu P60'da asyncio'nun `TaskGroup`'u ile göreceksin.
:::

::: tahmin
Çıktı tek satır:

```python
try:
    try:
        int("x")
    except ValueError as e:
        raise RuntimeError("ayar okunamadı") from e
except RuntimeError as e:
    print(e, "|", type(e.__cause__).__name__)
```

???

`ayar okunamadı | ValueError`. `raise ... from e` orijinal hatayı yeni hatanın `__cause__` niteliğine bağlar.
:::

::: gorev Yetersiz bakiye
`YetersizBakiye` adında, `Exception`'dan türeyen bir istisna sınıfı tanımla. Sonra `cek(bakiye, miktar)` fonksiyonunu yaz:

- `miktar <= 0` → `ValueError`
- `miktar > bakiye` → `YetersizBakiye`
- aksi halde yeni bakiyeyi döndür

```starter
def cek(bakiye, miktar):
    return bakiye - miktar
```

```test
need("cek")
Y = need("YetersizBakiye", "sınıf")
ok(Y is not Exception and Y.__name__ == "YetersizBakiye", "ayrı ve adlandırılmış istisna sınıfı")
eq(cek(1.5, 0.5), 1.0, "pozitif ondalık miktar")
ok(issubclass(Y, Exception), "YetersizBakiye, Exception'dan türemeli")
eq(cek(2, 1), 1, "en küçük pozitif tam miktar")
eq(cek(100, 30), 70, "cek(100, 30) → 70")
eq(cek(50, 50), 0, "cek(50, 50) → 0")
raises(Y, cek, 10, 20, msg="cek(10, 20) → YetersizBakiye")
raises(ValueError, cek, 10, 0, msg="cek(10, 0) → ValueError")
raises(ValueError, cek, 10, -5, msg="cek(10, -5) → ValueError")
```

```solution
class YetersizBakiye(Exception):
    pass

def cek(bakiye, miktar):
    if miktar <= 0:
        raise ValueError("miktar pozitif olmalı")
    if miktar > bakiye:
        raise YetersizBakiye(f"bakiye {bakiye}, istenen {miktar}")
    return bakiye - miktar
```

```hint
`class YetersizBakiye(Exception): pass`
```
:::

::: gorev EAFP ile rol bul
`kullanici_rolu(roller, ad)` fonksiyonu sözlükteki rolü döndürsün; ad yoksa `"misafir"` döndürsün. **EAFP** ile yaz: `in` ve `.get()` kullanmak yok, `KeyError` yakala.

```starter
def kullanici_rolu(roller, ad):
    if ad in roller:
        return roller[ad]
    return "misafir"
```

```test
need("kullanici_rolu")
r = {"ali": "admin", "veli": "user"}
eq(kullanici_rolu(r, "ali"), "admin", "ali → admin")
eq(kullanici_rolu(r, "zeynep"), "misafir", "zeynep → misafir")
eq(kullanici_rolu({"x": None}, "x"), None, "var olan None rolü misafir değildir")
eq(kullanici_rolu({}, "x"), "misafir", "boş sözlük → misafir")
ok(uses("try"), "try/except KeyError kullan")
ok(" in " not in src.split("def", 1)[1].split("\n", 1)[1] and not calls("get"), "in ve .get() olmadan")
```

```solution
def kullanici_rolu(roller, ad):
    try:
        return roller[ad]
    except KeyError:
        return "misafir"
```

```hint
`try: return roller[ad]` / `except KeyError: return "misafir"`
```
:::

::: gorev Ayar dosyası ayrıştırıcı
`AyarHatasi` istisnasını tanımla ve `ayar_yukle(metin)` fonksiyonunu yaz. Metin satırlardan oluşuyor; her satır `anahtar=değer`. Boş satırları ve `#` ile başlayan yorum satırlarını atla. Sonuç bir sözlük olsun (anahtar ve değerin kenar boşlukları temizlenmiş). Yorumdan önceki boşlukları da yok say. Tekrarlanan anahtarda son değer kazanır; boş değer serbesttir.

`=` içermeyen bir satırda `AyarHatasi` yükselt ve mesajda **satır numarası** olsun: `satır 3: '=' yok`.

```starter
class AyarHatasi(Exception):
    pass

def ayar_yukle(metin):
    ayarlar = {}
    for satir in metin.splitlines():
        anahtar, deger = satir.split("=")
        ayarlar[anahtar] = deger
    return ayarlar
```

```test
need("ayar_yukle")
eq(ayar_yukle("  # yorum\na = 1\na = 2\nb="), {"a": "2", "b": ""}, "boşluklu yorum, son değer ve boş değer")
A = need("AyarHatasi", "sınıf")
ok(issubclass(A, Exception) and A is not Exception and A.__name__ == "AyarHatasi", "ayrı AyarHatasi istisna sınıfı")
eq(ayar_yukle("port = 8080\n# yorum\n\ndebug=true"), {"port": "8080", "debug": "true"}, "yorum ve boş satır atlanır")
eq(ayar_yukle(""), {}, "boş metin → {}")
eq(ayar_yukle("url=http://x/?a=b"), {"url": "http://x/?a=b"}, "değerin içinde = olabilir")
try:
    ayar_yukle("a=1\nb=2\nbozuk satir")
    ok(False, "bozuk satırda AyarHatasi yükselmeli")
except A as e:
    ok("satır 3" in str(e), "mesajda 'satır 3' geçmeli", got=str(e))
```

```solution
class AyarHatasi(Exception):
    pass

def ayar_yukle(metin):
    ayarlar = {}
    for no, satir in enumerate(metin.splitlines(), 1):
        satir = satir.strip()
        if not satir or satir.startswith("#"):
            continue
        if "=" not in satir:
            raise AyarHatasi(f"satır {no}: '=' yok")
        anahtar, deger = satir.split("=", 1)
        ayarlar[anahtar.strip()] = deger.strip()
    return ayarlar
```

```hint
Satır numarası için `enumerate(metin.splitlines(), 1)`.
```

```hint
`split("=", 1)` sadece ilk eşittirden böler.
```
:::


::: anlat Yaygın yanlışlar
| Yanlış yaklaşım | Neden kırılır? | Doğrusu |
|---|---|---|
| Yeni hatayı Exception yerine sıradan değer yapmak | Raise ve except bir istisna türü bekler. | `class YeniHata(Exception)` kalıbını kullan. |
| EAFP tüm dosya yarışlarını çözer sanmak | İşlemin kendisinin güvenliği ayrı konudur. | Gereksiz ön kontrolü kaldır ama erişim sınırlarını ayrıca değerlendir. |
| Girdi doğrulamasını assert ile yapmak | Optimize çalıştırmada assert kaldırılabilir. | `if` ve `raise` kullan. |
:::

::: anlat AI derslerinde nerede?
- `ai-saldiri-11` çözümü bozuk belge paketini yakalarken `raise ValueError(...) from e` kullanır; asıl ayrıştırma hatasını neden zincirinde saklar.
- `ai-savunma-19` çözümünde geçersiz politika için `ValueError` yükseltilir. Özel hata türleri de aynı raise/except mekanizmasına bağlanır.
:::
