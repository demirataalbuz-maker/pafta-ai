---
id: p30
title: XML ve INI Dosyaları
summary: xml.etree.ElementTree ile XML okumak (parse, fromstring, find, findall, iter, öznitelikler ve metin, XPath alt kümesi) ve üretmek (Element, SubElement, tostring, indent), güvenilmeyen XML için uyarı; configparser ile .ini dosyaları, DEFAULT bölümü, getint/getboolean/fallback, değer ara değerlendirmesi ve yazmak.
kazanim: PCPP1 4.3, PCPP1 5.2
---

::: anlat XML: etiketlerden ağaç
JSON'dan önce yapılandırma, belge ve veri alışverişinin ortak dili XML'di ve bugün de her yerde: Office dosyalarının içi, RSS akışları, SVG, Maven ve .NET proje dosyaları, birçok cihazın ve kurumsal sistemin yapılandırması. Python'un standart kütüphanesindeki `xml.etree.ElementTree` bir XML belgesini **eleman ağacına** çevirir:

```python
import xml.etree.ElementTree as ET

xml = """<envanter>
  <sunucu ad="web01" rol="web"><cpu>72</cpu><sehir>İstanbul</sehir></sunucu>
  <sunucu ad="db01" rol="veritabani"><cpu>91</cpu></sunucu>
</envanter>"""
kok = ET.fromstring(xml)                          #! metinden; dosyadan: ET.parse("a.xml").getroot()
print(kok.tag, len(kok))                          #! etiket adı, çocuk sayısı
for s in kok:                                     #! doğrudan çocuklar
    print(s.get("ad"), s.attrib["rol"], s.find("cpu").text)
print(kok.find("sunucu/sehir").text)              #! yol: çocuğun çocuğu
print(kok.findtext("sunucu[@ad='db01']/sehir", default="yok"))
```

| Yöntem | Döndürdüğü |
|---|---|
| `e.tag`, `e.attrib`, `e.text` | etiket adı, öznitelik sözlüğü, içindeki metin |
| `e.get("ad")` | bir öznitelik (yoksa `None`) |
| `e.find("yol")` | ilk eşleşen eleman ya da `None` |
| `e.findall("yol")` | bütün eşleşenler (liste) |
| `e.findtext("yol", default=...)` | ilk eşleşenin metni |
| `e.iter("cpu")` | ağacın **her derinliğindeki** `cpu` elemanları |

Yollar XPath'in bir alt kümesidir: `sunucu/cpu` (çocuk), `.//cpu` (her derinlik), `sunucu[@rol='web']` (öznitelik koşulu), `sunucu[cpu]` (çocuğu olan).

> [!TUZAK]
> `.text` her zaman **metindir** ya da hiç metin yoksa `None`'dır. Sayı olarak kullanmadan önce `int(...)` gerekir; eksik bir eleman için `find(...)` `None` döndürür ve `.text` çağrısı `AttributeError` verir. `findtext(..., default=...)` eksik elemanda varsayılanı verir; var olan ama boş elemanda boş metin dönebilir. Sayıya dönüştürmeden önce içeriği ayrıca doğrulamak gerekir.

### XML üretmek
```python
import xml.etree.ElementTree as ET

kok = ET.Element("envanter")
s = ET.SubElement(kok, "sunucu", ad="web01", rol="web")   #! öznitelikler sırasıyla
ET.SubElement(s, "cpu").text = "72"                        #! metin her zaman str
ET.indent(kok)                                             #! okunur girinti (3.9+)
print(ET.tostring(kok, encoding="unicode"))
```

> [!GÜVENLİK]
> XML belgeleri başında **DTD** (*Document Type Definition*, `<!DOCTYPE ...>`) ile belge yapısını ve `<!ENTITY ...>` varlık kısaltmalarını tanımlayabilir. Bu özellikler (iç varlık genişletme ya da dış varlık — XXE) kötü niyetle hazırlanmış bir belgede bellek tüketen ya da yerel dosya okuyan ayrıştırıcı davranışlarına yol açabilir. Python belgeleri, **güvenilmeyen** XML için standart modüller yerine bu korumaları açık getiren `defusedxml` paketini önerir: `from defusedxml.ElementTree import fromstring`. Kendi ürettiğin ya da güvendiğin dosyalar için `xml.etree` yeterlidir.
:::

::: anlat INI dosyaları: configparser
Birçok uygulama ayarlarını `.ini` biçiminde tutar: köşeli parantezli **bölümler** ve `anahtar = değer` satırları. `configparser` bunları okur ve yazar:

```ini
[DEFAULT]
kok = /srv/pafta
zaman_asimi = 30

[web]
port = 8443
gunluk = %(kok)s/gunluk/web.log

[db]
port = 5432
zaman_asimi = 60
```

```python
import configparser

metin = "[DEFAULT]\nkok = /srv/pafta\nzaman_asimi = 30\n\n[web]\nport = 8443\ngunluk = %(kok)s/gunluk/web.log\n\n[db]\nport = 5432\nzaman_asimi = 60\n"
cp = configparser.ConfigParser()
cp.read_string(metin)                              #! dosyadan: cp.read("ayar.ini", encoding="utf-8")
print(cp.sections())                               #! DEFAULT listede yer almaz
print(cp.getint("web", "port") + 1)                #! değerler metindir; tür dönüştüren okuyucular var
print(cp["web"]["gunluk"])                         #! %(kok)s yerine konur
print(cp.getint("web", "zaman_asimi"), cp.getint("db", "zaman_asimi"))   #! DEFAULT'tan miras, db kendi değerini ezer
print(cp.get("db", "kullanici", fallback="pafta"))
```

| Kural | Ayrıntı |
|---|---|
| Değerler | her zaman metin: `getint`, `getfloat`, `getboolean` dönüştürür |
| `getboolean` | `1/yes/true/on` ve `0/no/false/off` kabul eder; başka sözcükler için `cp.BOOLEAN_STATES` sözlüğünü değiştir |
| `[DEFAULT]` | her bölümde varmış gibi görünür; bölüm kendi değeriyle ezebilir |
| Anahtarlar | büyük-küçük harfe **duyarsız**: `Port` ile `port` aynı |
| Ara değerlendirme | `%(anahtar)s` aynı bölümden ya da DEFAULT'tan; `ExtendedInterpolation()` ile `${bolum:anahtar}` |
| Eksik anahtar | `KeyError` / `NoOptionError`; `fallback=` ile varsayılan |

Yazmak için bölümleri sözlük gibi doldurup `cp.write(dosya)` çağrılır. Yorumlar okunurken atılır; yazılan dosyada yorum kalmaz.
:::

::: tahmin
Üç satır yazar:

```python
import xml.etree.ElementTree as ET
xml = """<envanter><sunucu ad="web01" rol="web"><cpu>72</cpu></sunucu>
<sunucu ad="db01" rol="veritabani"><cpu>91</cpu></sunucu>
<sunucu ad="web02" rol="web"><cpu>65</cpu></sunucu></envanter>"""
kok = ET.fromstring(xml)
print(len(kok), kok[1].get("ad"), kok[1].find("cpu").text)
print([s.get("ad") for s in kok.findall("sunucu[@rol='web']")])
print(sum(int(c.text) for c in kok.iter("cpu")))
```

???

`3 db01 91`, `['web01', 'web02']`, `228`. Kökün üç çocuğu var ve çocuklara liste gibi indeksle erişilir; `.text` metin döndürür. Öznitelik koşulu yalnızca rolü `web` olanları bırakır. `iter` her derinlikteki `cpu`'ları gezer; metinleri sayıya çevirip toplamak 72 + 91 + 65 = 228 verir.
:::

::: gorev XML'den rapor
`envanter.xml` dosyasını oku ve CPU'su **70'ten büyük** sunucuları CPU'ya göre büyükten küçüğe `ad cpu` biçiminde, her biri ayrı satırda yazdır. Bazı sunucularda `cpu` elemanı yok; onları atla. Bu alıştırmada mevcut cpu elemanları tam sayı metnidir; CPU değerleri eşit olan kayıtların kendi aralarındaki sırası şart koşulmuyor.

```setup
xml = """<?xml version="1.0" encoding="utf-8"?>
<envanter>
  <sunucu ad="web01" rol="web"><cpu>72</cpu><sehir>İstanbul</sehir></sunucu>
  <sunucu ad="db01" rol="veritabani"><cpu>91</cpu></sunucu>
  <sunucu ad="test01" rol="test"/>
  <sunucu ad="cache01" rol="onbellek"><cpu>84</cpu></sunucu>
  <sunucu ad="web02" rol="web"><cpu>65</cpu></sunucu>
</envanter>
"""
with open("envanter.xml", "w", encoding="utf-8") as f:
    f.write(xml)
```

```starter
import xml.etree.ElementTree as ET

kok = ET.parse("envanter.xml").getroot()
for s in kok:
    print(s.get("ad"), s.find("cpu").text)
```

```test
eq(out, "db01 91\ncache01 84\nweb01 72\n", "üç sunucu, büyükten küçüğe")
with open("envanter.xml", "w", encoding="utf-8") as f:
    f.write('<envanter><sunucu ad="esik"><cpu>70</cpu></sunucu><sunucu ad="ilk"><cpu>71</cpu></sunucu><sunucu ad="en"><cpu>100</cpu></sunucu><sunucu ad="eksik"/></envanter>')
eq(run(), "en 100\nilk 71\n", "70 hariç, 71 dahil, sayısal sıra")
with open("envanter.xml", "w", encoding="utf-8") as f:
    f.write('<envanter/>')
eq(run(), "", "boş envanter")
```

```solution
import xml.etree.ElementTree as ET

kok = ET.parse("envanter.xml").getroot()
yuksek = []
for s in kok.findall("sunucu"):
    cpu = s.findtext("cpu")
    if cpu is not None and int(cpu) > 70:
        yuksek.append((int(cpu), s.get("ad")))
for cpu, ad in sorted(yuksek, reverse=True):
    print(ad, cpu)
```

```hint
`test01`'in `cpu` elemanı yok: `s.find("cpu")` `None` döner ve `.text` hata verir. `s.findtext("cpu")` eksik elemanda `None` döndürür.
```

```hint
Metni sayıya çevir (`int(cpu)`), `(cpu, ad)` çiftlerini topla ve `sorted(..., reverse=True)`.
```
:::

::: gorev XML üret
`xml_uret(sunucular)` fonksiyonunu yaz: `{"ad": ..., "rol": ..., "cpu": ...}` sözlüklerinden oluşan listeyi, her sunucu için `ad` ve `rol` öznitelikli bir `sunucu` elemanı ve içinde `cpu` elemanı olan bir `envanter` belgesine çevirsin; girintisiz tek satırlık metin olarak döndürsün. `cpu` değeri yoksa (`None`) `cpu` elemanı hiç eklenmesin.

```starter
def xml_uret(sunucular):
    parcalar = ["<envanter>"]
    for s in sunucular:
        parcalar.append(f'<sunucu ad="{s["ad"]}" rol="{s["rol"]}"><cpu>{s["cpu"]}</cpu></sunucu>')
    parcalar.append("</envanter>")
    return "".join(parcalar)
```

```test
need("xml_uret")
eq(xml_uret([{"ad": "web01", "rol": "web", "cpu": 72}]),
   '<envanter><sunucu ad="web01" rol="web"><cpu>72</cpu></sunucu></envanter>', "tek sunucu")
eq(xml_uret([{"ad": "test01", "rol": "test", "cpu": None}]),
   '<envanter><sunucu ad="test01" rol="test" /></envanter>', "cpu yoksa eleman yok")
eq(xml_uret([{"ad": "a&b", "rol": "<web>", "cpu": 1}]),
   '<envanter><sunucu ad="a&amp;b" rol="&lt;web&gt;"><cpu>1</cpu></sunucu></envanter>', "özel karakterler kaçırılır")
eq(xml_uret([]), "<envanter />", "boş envanter")
ok(calls("SubElement"), "ElementTree ile üret")
```

```solution
import xml.etree.ElementTree as ET


def xml_uret(sunucular):
    kok = ET.Element("envanter")
    for s in sunucular:
        e = ET.SubElement(kok, "sunucu", ad=s["ad"], rol=s["rol"])
        if s["cpu"] is not None:
            ET.SubElement(e, "cpu").text = str(s["cpu"])
    return ET.tostring(kok, encoding="unicode")
```

```hint
Metni elle birleştirmek `&` ve `<` gibi karakterleri kaçırmaz ve bozuk XML üretir. `ET.Element`, `ET.SubElement` ve `ET.tostring(kok, encoding="unicode")` bunu senin yerine yapar.
```

```hint
`.text` her zaman metin olmalı: `str(s["cpu"])`. Çocuksuz eleman `<sunucu ... />` biçiminde yazılır.
```
:::

::: gorev Ayar dosyası
Verilen `yol` dosyasını `configparser` ile UTF-8 kodlamasıyla (`encoding="utf-8"`) oku ve şu sözlüğü döndüren `ayarlar(yol)` fonksiyonunu yaz:

| Anahtar | Değer |
|---|---|
| `web_port` | `[web] port`, **tam sayı** |
| `web_gunluk` | `[web] gunluk`, ara değerlendirme uygulanmış |
| `web_hata_ayikla` | `[web] hata_ayikla`, **bool** (dosyada `evet` / `hayır` yazıyor) |
| `web_zaman_asimi` | `[web] zaman_asimi`, tam sayı (DEFAULT'tan) |
| `db_zaman_asimi` | `[db] zaman_asimi`, tam sayı |
| `db_kullanici` | `[db] kullanici`, yoksa `"pafta"` |

```setup
ini = """[DEFAULT]
kok = /srv/pafta
zaman_asimi = 30

[web]
Port = 8443
gunluk = %(kok)s/gunluk/web.log
hata_ayikla = evet

[db]
port = 5432
zaman_asimi = 60
"""
with open("ayar.ini", "w", encoding="utf-8") as f:
    f.write(ini)
```

```starter
import configparser


def ayarlar(yol):
    cp = configparser.ConfigParser()
    cp.read(yol, encoding="utf-8")
    return {"web_port": cp["web"]["Port"]}
```

```test
need("ayarlar")
import ast as _ast
_reads = [n for n in _ast.walk(_ast.parse(src)) if isinstance(n, _ast.Call) and getattr(n.func, "attr", "") == "read"]
ok(bool(_reads) and all(any(k.arg == "encoding" for k in n.keywords) for n in _reads), "cp.read çağrısında encoding='utf-8' belirt")
with open("ikinci.ini", "w", encoding="utf-8") as f:
    f.write("[DEFAULT]\nkok=/tmp/rapor\nzaman_asimi=7\n[web]\nport=80\ngunluk=%(kok)s/a.log\nhata_ayikla=hayır\n[db]\nzaman_asimi=9\nkullanici=ali\n")
eq(ayarlar("ikinci.ini"), {"web_port":80, "web_gunluk":"/tmp/rapor/a.log", "web_hata_ayikla":False, "web_zaman_asimi":7, "db_zaman_asimi":9, "db_kullanici":"ali"}, "hayır, açık kullanıcı ve değişen varsayılan")
eq(ayarlar("ayar.ini"), {"web_port": 8443, "web_gunluk": "/srv/pafta/gunluk/web.log", "web_hata_ayikla": True,
                         "web_zaman_asimi": 30, "db_zaman_asimi": 60, "db_kullanici": "pafta"}, "altı ayar")
```

```solution
import configparser


def ayarlar(yol):
    cp = configparser.ConfigParser()
    cp.BOOLEAN_STATES = {"evet": True, "hayır": False}
    cp.read(yol, encoding="utf-8")
    return {
        "web_port": cp.getint("web", "port"),
        "web_gunluk": cp.get("web", "gunluk"),
        "web_hata_ayikla": cp.getboolean("web", "hata_ayikla"),
        "web_zaman_asimi": cp.getint("web", "zaman_asimi"),
        "db_zaman_asimi": cp.getint("db", "zaman_asimi"),
        "db_kullanici": cp.get("db", "kullanici", fallback="pafta"),
    }
```

```hint
Değerler metin olarak gelir: `getint` ve `getboolean` kullan. Anahtarlar harfe duyarsızdır; `Port` ile `port` aynı ayardır.
```

```hint
`getboolean` "evet"i tanımaz. Okumadan önce `cp.BOOLEAN_STATES = {"evet": True, "hayır": False}`. Eksik ayar için `fallback="pafta"`.
```
:::


::: anlat Yaygın yanlışlar
| Yanlış yaklaşım | Neden kırılır? | Doğrusu |
|---|---|---|
| XML metnini elle birleştirmek | Öznitelikteki &, < ve tırnaklar belgeyi bozabilir. | ElementTree ile üret ve tostring kullan. |
| Eksik elemanda `.text` okumak | find None döndürür; AttributeError oluşur. | Eksik elemanı ayrı ele al; findtext sonucunun boşluğunu da değerlendir. |
| INI değerlerini hazır sayı/bool sanmak | Okunan değer metindir; bool("hayır") da True olur. | getint/getboolean ve uygun BOOLEAN_STATES kullan. |
:::

::: anlat AI derslerinde nerede?
- `ai-saldiri-11` testindeki "belgeyi ham XML'e gömen" kusurlu aday, güvenilmeyen metni elle etiketler içine eklemenin riskini gösterir. O dersin doğru çözümü XML yerine JSON paketi üretir; burada XML gerekiyorsa yapısal üretim ve kaçış öğrenilir.
- `ai-saldiri-17` model adaptörü `<untrusted>` gibi XML benzeri prompt sınırları kullanır. Bunlar ElementTree ile ayrıştırılan bir XML belgesi değildir; biçimsel sınır ile yetki/güven sınırının aynı şey olmadığını ayırt etmek önemlidir.
:::
