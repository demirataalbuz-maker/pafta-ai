---
id: ai-temel-14
title: "Yapılandırılmış Çıktı ve Şema Doğrulama"
summary: Katı kayıt şeması, allowlist'li JSON araç çağrısı ve geçerli ilk çıktı seçimi uygula.
esleme: ai-temel-13, ai-temel-16, ai-savunma-05
timeout: 45
---

::: anlat JSON olması şemaya uyması demek değildir

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Ollama format alanında JSON Schema ile modelden yapılandırılmış yanıt ister | İlk üç görev görünür sentetik JSON örnekleri; finalde kurulu modelin iki gerçek şemalı yanıtı ve katı yerel ayrıştırıcı | Şemaya uygun nesne doğru içerik, kullanıcı onayı veya araç yetkisi değildir |
| Yerel doğrulayıcı tam anahtar, tür, sınır ve yinelenen alanları denetler | Standart json, katı sözleşme ve yalnız normalize edilen oyuncak araç çağrıları | Yol metnini denetlemek gerçek dosya sistemi yalıtımı veya symlink güvenliği testi değildir |

> [!NOT]
> `veri/ornekler.json` elle hazırlanmış **sentetik** veridir, kaydedilmiş model çıktısı değildir. İlk üç görev aynı dosyanın alanlarını okur. Setup her Run/Check için geçici kopya oluşturur; düzenlemeler kalıcı değildir. Kaynak fixture dosyasını editörle açabilir, ders kodunda yüklenen kopyayı değiştirip Run ile deneyebilirsin. Gizli testler ayrı. Son görev kurulu Ollama ile gerçek JSON Schema üretimi yapar; yeni araç/model indirmez.

Model çıktısı sözdizimsel olarak geçerli JSON olsa bile eksik alan, yanlış tür veya beklenmeyen komut içerebilir. Katı doğrulama tam anahtar kümesini, değer türlerini ve izinli değer aralıklarını kontrol eder. Bilinmeyen alanları sessizce kabul etmek ileride güvenlik açığına dönüşebilir.

Görevler 1–3 standart json ile sentetik veride açık kuralları uygular; son adım gerçek Ollama modelini JSON Schema ile çalıştırır. Pydantic bu derste kullanılmaz. Hatalı aday reddedilir, ancak hiçbir araç gerçekten çalıştırılmaz.
:::

::: anlat Araç çağrısı veridir, yürütme ayrı karardır

Önce `veri/ornekler.json` dosyasını aç. `kayit` ilk görevdeki üç alanı, `cagrilar` ikinci görevdeki araç metinlerini, `adaylar` üçüncü görevdeki sırayla denenmiş çıktıları taşır. Dosyada hem geçerli hem bozuk örnekler vardır; JSON olarak okunabilen bir çağrının araç adı yine yasak olabilir. Görevlerin şemaları farklıdır: ilkinde ad/miktar/aktif, ikincide arac/argumanlar, üçüncüde islem/deger, gerçek finalde ise bunlara onay alanı da eklenir. Bunları tek şema sanmadan her aşamanın sözleşmesini oku.

Ayrıştırma ve doğrulama iki ayrı adımdır. JSON ayrıştırıcı metni Python değerlerine dönüştürür; doğru anahtarları veya iş kurallarını kendiliğinden sağlamaz. Örneğin Python'da bool int alt sınıfıdır ama miktar alanında True kabul edilmemelidir. onay alanında ise bir tamsayısını bool'a dönüştürmek model çıktısını sessizce onarmaktır. Bu ders böyle onarım yapmaz: yanlış türü açık hata olarak döndürür. Kullanıcı onayı uygulamanın ayrı güven sınırından gelir, modelin yazdığı onay kelimesinden gelmez.

Yinelenen JSON anahtarları da belirsizlik yaratır. Bir alan önce yasak, sonra izinli değerle yazılırsa sıradan sözlük dönüşümü önceki değeri kaybedebilir. Katı ayrıştırıcı bu yüzden anahtar çiftlerini sözlüğe dönüşmeden görür ve yineleneni reddeder. NaN ve Infinity Python json ayrıştırıcısının bazı varsayılanlarında sayı gibi okunabilse de bu dersin standart JSON sözleşmesinde kabul edilmez. Topla için sonlu değerler gerekir; hesap yapılmasa bile sonraki katmana taşınan sayı anlamlı olmalıdır.

Yol doğrulaması Windows ve Unix biçimlerini birlikte düşünmelidir. Sadece başında eğik çizgi aramak C sürücüsündeki mutlak yolu yakalamaz. Sürücü öneki, UNC biçimi, üst dizin parçası ve NUL içeren metinler reddedilir. Göreli veri/a.txt gibi örnekler korunur. Bununla birlikte dosya burada açılmaz; sembolik bağlantı veya gerçek dizin kökü çevrelemesi ölçülmüş sayılmaz. Şema doğrulamasını gerçek dosya yetkisiyle karıştırmamak eğitimin bir parçasıdır.

İlk geçerli aday seçilirken üst düzey listenin tümü önce doğrulanır. Listenin sonunda yanlış tür veya aşırı uzun metin varsa baştaki geçerli adayı bulmak bu hatayı gizlememelidir. Sözdizimi veya nesne şeması bozuk aday ise sıradaki adayın denenmesine izin verir. İlk geçerli indeksi döndürmek ile geçerli adayların sonuncusunu seçmek farklıdır. Hiçbirinin uygun olmadığı durumda eksi bir, boş listede de aynı sonuç döner.

Gerçek model çağrısı format alanına tam JSON Schema gönderir. Modelden sadece JSON yazmasını istemek ile alan/tür kuralları içeren şema vermek aynı istek değildir. Buna rağmen yanıt yeniden yerel katı doğrulamaya girer; tamamlanmamış üretim veya Markdown içine alınmış nesne kabul edilmez. İstenen rastgele notun kopyalanıp kopyalanmadığı ayrıca kaydedilir, sabit yanıt metni geçme şartı değildir. Böylece biçim kabulü ile semantik başarı ayrı kalır.

Saldırgan çıktı içine ek komut, bilinmeyen alan veya sayısal onay yerleştirmeyi deneyebilir. Savunucu bu alanı sessizce düşürürse aşağıdaki katmanlarla farklı yorumlar oluşabilir. Bu ders yalnız izinli nesneyi döndürür; araç çalıştırma veya kullanıcı dosyasına yazma etkisi yoktur. Gerçek deney kaynaklarını da ölçer: seçili cihaz, model belleği ve yalnız kendisine ait kaynakların temizliği kanıtta görünür. Eksik model, yarım üretim veya başarısız kabul geçme sayılmaz.

Allowlist yalnız tanımlı araç adlarına izin verir. Her aracın argüman şeması ayrıdır; `oku` yalnız göreli ve `..` içermeyen bir yol, `topla` iki sayı alır. Bu aşama oku yolundaki dosyayı açmaz veya topla aracını yürütmez; yalnız öğrenci örnek JSON dosyasını okuyup çağrıyı normalize eder.

Birden çok model adayı arasından ilk geçerli çıktıyı seçmek, geçersiz metni düzeltmeye çalışmaktan daha öngörülebilirdir. Seçimden sonra yetki ve kullanıcı onayı gibi ek katmanlar yine gerekir.
:::

::: tahmin Şema sonucunu tahmin et
Üç çıktı satırını yaz:

```python
import json
x = json.loads('{"arac":"topla","argumanlar":{"a":1,"b":2}}')
print(x["arac"])
print(set(x) == {"arac", "argumanlar"})
print([0, 1, 2] if -1 < 0 else [])
```

???

```cikti
topla
True
[0, 1, 2]
```

İlk satır izinli araç adını, ikinci satır tam anahtar eşleşmesini, üçüncü satır aday indekslerinin sırasını gösterir.
:::

::: gorev 1 · Katı kayıt şemasını doğrula
`kayit_dogrula(kayit)` işlevini yaz. Kayıt tam `ad`, `miktar`, `aktif` anahtarlı sözlüktür. Ad boş olmayan string, miktar bool olmayan 1–8 tamsayısı, aktif bool değerdir. Geçersiz veride `ValueError` yükselt.

Aynı alanları içeren bağımsız sözlük döndür; girdiyi değiştirme. Ek anahtarları kabul etme.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-14")
```

```starter
from ai_temel_veri import json_yukle

def kayit_dogrula(kayit):
    # KUSURLU BAŞLANGIÇ KODU: ek alanları düşürür ve bool/sayı türlerini dönüştürür.
    return {"ad":str(kayit["ad"]),"miktar":int(kayit["miktar"]),"aktif":bool(kayit["aktif"])}

v=json_yukle("veri/ornekler.json")
print("Sentetik veri:",v)
print("Kayıt:",kayit_dogrula(v["kayit"]))
```

```test
K = {"ad": "rapor", "miktar": 2, "aktif": True}
def sozlesme(fn):
    try:
        once=dict(K)
        sonuc = fn(K)
        if K!=once:
            return False
        if sonuc != K or sonuc is K or fn(dict(K, miktar=1))["miktar"] != 1 or fn(dict(K, miktar=8))["miktar"] != 8:
            return False
        original=dict(K)
        sonuc["ad"]="değişti"
        if K!=original:
            return False
        for deger in [None, [], {}, dict(K, ek=1), dict(K, ad=""), dict(K, ad=1), dict(K, miktar=0), dict(K, miktar=9), dict(K, miktar=True), dict(K, miktar=1.0), dict(K, aktif=1)]:
            try:
                fn(deger)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(kayit_dogrula), "tam anahtar, tür ve miktar sınırı korunmalı")
def m_ad(k):
    return kayit_dogrula(dict(k, ad="x"))
def m_miktar(k):
    return kayit_dogrula(dict(k, miktar=9))
def m_aktif(k):
    return kayit_dogrula(dict(k, aktif=False))
for ad, mutant in [("adı bozan", m_ad), ("miktarı bozan", m_miktar), ("aktifi bozan", m_aktif)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def kayit_dogrula(kayit):
    if not isinstance(kayit, dict) or set(kayit) != {"ad", "miktar", "aktif"}:
        raise ValueError("kayıt şeması geçersiz")
    if not isinstance(kayit["ad"], str) or not kayit["ad"]:
        raise ValueError("ad geçersiz")
    if not isinstance(kayit["miktar"], int) or isinstance(kayit["miktar"], bool) or not 1 <= kayit["miktar"] <= 8:
        raise ValueError("miktar geçersiz")
    if not isinstance(kayit["aktif"], bool):
        raise ValueError("aktif geçersiz")
    return {"ad": kayit["ad"], "miktar": kayit["miktar"], "aktif": kayit["aktif"]}
if __name__ == "__main__":
    v=json_yukle("veri/ornekler.json")
    print("Sentetik veri:",v)
    print("Kayıt:",kayit_dogrula(v["kayit"]))

```

```hint
Önce `set(kayit)` ile anahtarları, sonra her alanı ayrı doğrula; sonunda yeni sözlük oluştur.
```
:::

::: gorev 2 · Allowlist'li araç çağrısını ayrıştır
`cagri_ayristir(metin)` işlevini yaz. Metin en çok 512 karakterlik JSON object stringidir. Nesne tam `arac`, `argumanlar` anahtarlarını içerir. Geçersiz JSON, tür veya şemada `ValueError` yükselt.

`oku` için argumanlar tam `yol` anahtarlıdır; yol boş olmayan string, mutlak yol olmayan ve `..` yol parçası içermeyen göreli yoldur. `topla` için argumanlar tam `a`, `b` anahtarlı iki bool olmayan sayıdır. Başka araç kabul edilmez. Yinelenen JSON anahtarı, NaN/Infinity ve sonlu olmayan sayılar geçersizdir. Windows sürücü öneki, UNC ve NUL içeren yol da reddedilir. Normalize edilmiş yeni sözlük döndür; aracı çalıştırma.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-14")
```

```starter
from ai_temel_veri import json_yukle
import json

def cagri_ayristir(metin):
    # KUSURLU BAŞLANGIÇ KODU: JSON parse etmeyi allowlist ve argüman doğrulaması sanır.
    return json.loads(metin)

v=json_yukle("veri/ornekler.json")
print("Sentetik veri:",v)
for metin in v["cagrilar"]:
    try: print(metin,"→",cagri_ayristir(metin))
    except ValueError as e: print(metin,"reddedildi:",e)
```

```test
import json
def sozlesme(fn):
    try:
        if fn('{"arac":"topla","argumanlar":{"a":1,"b":2.5}}') != {"arac": "topla", "argumanlar": {"a": 1, "b": 2.5}}:
            return False
        if fn('{"arac":"oku","argumanlar":{"yol":"veri/a.txt"}}')["argumanlar"]["yol"] != "veri/a.txt":
            return False
        temel = '{"arac":"topla","argumanlar":{"a":1,"b":2}}'
        sinir = temel + " " * (512 - len(temel))
        if fn(sinir) != {"arac": "topla", "argumanlar": {"a": 1, "b": 2}}:
            return False
        buyuk=10**400
        if fn(json.dumps({"arac":"topla","argumanlar":{"a":buyuk,"b":0}}))["argumanlar"]["a"]!=buyuk:
            return False
        yollar=["C:/veri/a.txt","C:\\veri\\a.txt","C:a.txt","\\\\sunucu\\paylasim\\a.txt","a\x00.txt"]
        ek=[json.dumps({"arac":"oku","argumanlar":{"yol":q}}) for q in yollar]
        ek += ['["arac","argumanlar"]','{"arac":"oku","argumanlar":["yol"]}','{"arac":"sil","arac":"topla","argumanlar":{"a":1,"b":2}}','{"arac":"topla","argumanlar":{"a":NaN,"b":2}}','{"arac":"topla","argumanlar":{"a":1e999,"b":2}}']
        for bad in ek:
            try: fn(bad); return False
            except ValueError: pass
        for metin in [None, temel.encode(), "", "x", "[]", sinir + " ", '{"arac":"sil","argumanlar":{"a":1,"b":2}}', '{"arac":"topla","argumanlar":{"a":1}}', '{"arac":"topla","argumanlar":{"a":1,"b":2,"c":3}}', '{"arac":"topla","argumanlar":{"a":"1","b":2}}', '{"arac":"topla","argumanlar":{"a":true,"b":2}}', '{"arac":"topla","argumanlar":{"a":1,"b":2},"ek":0}', '{"arac":"oku","argumanlar":{"yol":"x","ek":1}}', '{"arac":"oku","argumanlar":{"yol":1}}', '{"arac":"oku","argumanlar":{"yol":""}}', '{"arac":"oku","argumanlar":{"yol":"/etc/passwd"}}', '{"arac":"oku","argumanlar":{"yol":"../x"}}', '{"arac":"oku","argumanlar":{"yol":"a/../x"}}']:
            try:
                fn(metin)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(cagri_ayristir), "JSON, araç allowlist'i ve argüman sınırları korunmalı")
def m_arac(m):
    return cagri_ayristir(m.replace("topla", "sil"))
def m_arg(m):
    return cagri_ayristir(m.replace('"a":1', '"a":9'))
def m_bicim(m):
    return cagri_ayristir(m + " ")
for ad, mutant in [("aracı bozan", m_arac), ("argümanı bozan", m_arg), ("biçimi bozan", m_bicim)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def cagri_ayristir(metin):
    import json
    import math
    import ntpath
    if not isinstance(metin, str) or not metin or len(metin) > 512:
        raise ValueError("metin geçersiz")
    def nesne(ciftler):
        out={}
        for key,value in ciftler:
            if key in out: raise ValueError("yinelenen anahtar")
            out[key]=value
        return out
    def sabit(_):
        raise ValueError("standart dışı sayı")
    try:
        cagri = json.loads(metin,object_pairs_hook=nesne,parse_constant=sabit)
    except (json.JSONDecodeError, TypeError):
        raise ValueError("JSON geçersiz")
    if not isinstance(cagri, dict) or set(cagri) != {"arac", "argumanlar"} or cagri["arac"] not in ("oku", "topla") or not isinstance(cagri["argumanlar"], dict):
        raise ValueError("çağrı geçersiz")
    arac = cagri["arac"]
    arg = cagri["argumanlar"]
    if arac == "oku":
        if set(arg) != {"yol"} or not isinstance(arg["yol"], str) or not arg["yol"] or arg["yol"].startswith(("/", "\\")) or ntpath.splitdrive(arg["yol"])[0] or "\x00" in arg["yol"] or ".." in arg["yol"].replace("\\", "/").split("/"):
            raise ValueError("yol geçersiz")
        return {"arac": arac, "argumanlar": {"yol": arg["yol"]}}
    if set(arg) != {"a", "b"} or any(not isinstance(arg[x], (int, float)) or isinstance(arg[x], bool) or (isinstance(arg[x],float) and not math.isfinite(arg[x])) for x in ("a", "b")):
        raise ValueError("sayı geçersiz")
    return {"arac": arac, "argumanlar": {"a": arg["a"], "b": arg["b"]}}
if __name__ == "__main__":
    v=json_yukle("veri/ornekler.json")
    print("Sentetik veri:",v)
    for metin in v["cagrilar"]:
        try: print(metin,"→",cagri_ayristir(metin))
        except ValueError as e: print(metin,"reddedildi:",e)

```

```hint
JSON'u önce ayrıştır, sonra araç adına göre iki ayrı şema uygula. Yolu `/` ve `\\` ayraçlarıyla parçalayıp `..` ara.
```
:::

::: gorev 3 · İlk geçerli yapılandırılmış çıktıyı seç
`ilk_gecerli_cikti(adaylar)` işlevini yaz. Adaylar 0–8 öğeli string listesidir; her string en çok 512 karakterdir. Geçersiz üst düzey veride `ValueError` yükselt.

Her adayı JSON olarak ayrıştır. Tam `islem`, `deger` anahtarlı nesne, `islem` alanı `not_ekle` veya `raporla`, değer alanı boş olmayan string ise aday geçerlidir. Yinelenen anahtarlı veya standart dışı sayılı JSON adayı geçersiz say. Hatalı adayı reddet ve ilk geçerli adayın indeksini döndür; hiçbiri geçerli değilse -1 döndür.

```setup
import sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_temel_veri import hazirla
hazirla("ai-temel-14")
```

```starter
from ai_temel_veri import json_yukle
import json

def ilk_gecerli_cikti(adaylar):
    # KUSURLU BAŞLANGIÇ KODU: ilk yerine son geçerli adayı seçer.
    sonuc=-1
    for i,m in enumerate(adaylar):
        try: x=json.loads(m)
        except ValueError: continue
        if isinstance(x,dict) and set(x)=={"islem","deger"} and x["islem"] in ("not_ekle","raporla") and isinstance(x["deger"],str) and x["deger"]: sonuc=i
    return sonuc

v=json_yukle("veri/ornekler.json")
print("Sentetik veri:",v)
print("İlk geçerli indeks:",ilk_gecerli_cikti(v["adaylar"]))
```

```test
A = ["x", '{"islem":"sil","deger":"a"}', '{"islem":"not_ekle","deger":"not"}', '{"islem":"raporla","deger":"rapor"}']
def sozlesme(fn):
    try:
        if fn(A) != 2 or fn(A[2:]) != 0 or fn(A[:2]) != -1 or fn([]) != -1:
            return False
        if len(A + A) != 8 or fn(A + A) != 2 or fn([A[2] + " " * (512 - len(A[2]))]) != 0:
            return False
        if fn(['{"islem":"sil","islem":"raporla","deger":"not"}'])!=-1 or fn(['{"islem":"raporla","deger":NaN}'])!=-1:
            return False
        if fn(['{}','["islem","deger"]','{"islem":"raporla","deger":1}','{"islem":"raporla","deger":""}'])!=-1:
            return False
        for deger in [None, {}, [1], ["x" * 513], A + A + A[:1]]:
            try:
                fn(deger)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(ilk_gecerli_cikti), "aday reddi, ilk geçerli indeks ve şema korunmalı")
def m_sira(a):
    return ilk_gecerli_cikti(list(reversed(a)))
def m_icerik(a):
    return ilk_gecerli_cikti([x.replace("not_ekle", "sil") for x in a])
def m_boyut(a):
    return ilk_gecerli_cikti(a + a)
for ad, mutant in [("sırayı bozan", m_sira), ("içeriği bozan", m_icerik), ("boyutu bozan", m_boyut)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from ai_temel_veri import json_yukle
def ilk_gecerli_cikti(adaylar):
    import json
    if not isinstance(adaylar, list) or len(adaylar) > 8 or any(not isinstance(x, str) or len(x) > 512 for x in adaylar):
        raise ValueError("adaylar geçersiz")
    def nesne(ciftler):
        out={}
        for key,value in ciftler:
            if key in out: raise ValueError("yinelenen anahtar")
            out[key]=value
        return out
    def sabit(_):
        raise ValueError("standart dışı sayı")
    for i, metin in enumerate(adaylar):
        try:
            x = json.loads(metin,object_pairs_hook=nesne,parse_constant=sabit)
        except ValueError:
            continue
        if isinstance(x, dict) and set(x) == {"islem", "deger"} and x["islem"] in ("not_ekle", "raporla") and isinstance(x["deger"], str) and x["deger"]:
            return i
    return -1
if __name__ == "__main__":
    v=json_yukle("veri/ornekler.json")
    print("Sentetik veri:",v)
    print("İlk geçerli indeks:",ilk_gecerli_cikti(v["adaylar"]))

```

```hint
Her adayı try/except ile ayrıştır; geçersizse `continue`, bütün koşullar sağlanıyorsa hemen indeksi döndür.
```
:::

::: anlat Gerçek deney: şemayla ürettir, sonra yine doğrula
Önceki görevlerdeki JSON örnekleri hazır metinlerdi. Bu adımda kurulu Ollama modeli gerçekten `/api/chat` ile çağrılır ve `format` alanına JSON Schema verilir. Test gerçek modelin ham yanıtını saklar ve senin doğrulayıcını o yanıt üzerinde çalıştırır. [Resmî protokol](https://docs.ollama.com/capabilities/structured-outputs) JSON üretimi ile şemaya göre üretimi ayırır; burada tam şema gönderilir.

Şema doğruluğu içerik doğruluğu veya yetki değildir. Modelin `onay:true` demesi kullanıcı onayı sayılmaz; bu derste hiçbir dosya veya araç eylemi çalıştırılmaz. İstenen rastgele notun aynen kopyalanıp kopyalanmadığı ayrıca **bulgu** olarak kaydedilir, modelin sabit bir metin üretmesi kabul şartı değildir. Asıl kabul, gerçek şema isteğinin tamamlanması ve gerçek yanıtın katı yerel doğrulamadan geçmesidir.

Deney varsayılan olarak GPU'da çalışır: bilgisayardaki Ollama sunucusunu kullanır ve aynı anda başka bir Ollama deneyi GPU'yu tutuyorsa sırasını bekler (makine genelinde GPU kilidi). Yalnız kendi yüklediği modeli boşaltır; senin önceden yüklediğin modele dokunmaz. `PAFTA_OLLAMA_CIHAZ=cpu` ayarlanırsa deney kendi ayrı Ollama sunucusunu açar, istekte `num_gpu=0` kullanır ve iş bitince yalnız o sürecin ağacını kapatır; CPU üretimi daha yavaştır. Hangi cihazın kullanıldığı kanıta yazılır; model dosyaları korunur. Kurulu model/araç yoksa deney geçmez, indirme yapmaz.
:::

::: gorev Gerçek deney · Gerçek şemalı model çıktısını katı doğrula
`kati_model_jsonu(metin)` işlevini yaz. `metin`, en fazla 4096 karakterlik bir str olmalı; aksi hâlde `ValueError` yükselt.

Metnin **tamamı** tek bir JSON nesnesi olmalıdır. Markdown kod bloğu, JSON sonrası yazı, NaN/Infinity, yinelenen anahtar veya nesne dışı kök kabul edilmez. Nesne tam şu alanları taşır:

- `islem`: yalnız `not_ekle` veya `raporla` stringi.
- `deger`: 1–80 karakterlik str; boşluk dışında en az bir karakter içerir. Metni strip/normalize etme, aynen koru.
- `onay`: tam bool; 0/1, string veya None kabul edilmez. True da False da şema açısından geçerlidir; ikisi de araç yürütme yetkisi vermez.

Geçerli nesneyi bağımsız sözlük olarak döndür, her geçersiz girdide `ValueError` yükselt. Bilinmeyen alanları düşürerek veya tipleri otomatik dönüştürerek “düzeltme” yapma. JSON'un ön/son standart boşluğuna izin ver. Şemadaki karakter sınırı UTF-8 bayt değil Python str uzunluğudur.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def kati_model_jsonu(metin):
    return {}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_14 as lab14
    kayitlar, ortam = lab14.gercek_ciktilar()
    for k in kayitlar:
        print("Gerçek ham yanıt:", k["icerik"])
        print("Doğrulama:", kati_model_jsonu(k["icerik"]))
```

```test
import copy
import json
import secrets
import ai_lab
from sandbox import ai_gercek_ai_temel_14 as lab14
sonuclar=[]
def kontrol(c,mesaj):
    sonuclar.append(bool(c))
    return ok(c,mesaj)
import ast
_yasak=("kati_json_ref","kanit_yaz")
sorun=ai_lab.kod_denetimi(src,yasak=_yasak)
for n in ast.walk(ast.parse(src)):
    if isinstance(n,ast.ImportFrom) and any(a.name in _yasak or a.name=="*" for a in n.names):
        sorun.append("referans importu yasak")
if not kontrol(not sorun,"Kendi katı JSON doğrulayıcını yaz: "+"; ".join(sorun)):
    stop()
fn=need("kati_model_jsonu")

v={"islem":"raporla","deger":"PAFTA-"+secrets.token_hex(4),"onay":False}
valid=[v,dict(v,islem="not_ekle",onay=True),dict(v,deger="a"),dict(v,deger=" çay 🧪 "),dict(v,deger="x"*80)]
base=json.dumps(v,ensure_ascii=False)
bosluk_siniri=base+" "*(4096-len(base))
invalid=[None,42,b"{}","", "{}", "[]", "true", "null", "NaN", "Infinity",
         "```json\n"+base+"\n```", base+" trailing", base+"{}", bosluk_siniri+" ",
         json.dumps(dict(v,ek="komut")), json.dumps(dict(v,onay=1)),json.dumps(dict(v,onay=0)),
         json.dumps(dict(v,onay="false")),json.dumps(dict(v,onay=None)),
         json.dumps(dict(v,islem="sil")),json.dumps(dict(v,islem=[])),
         json.dumps(dict(v,deger="")),json.dumps(dict(v,deger="  ")),json.dumps(dict(v,deger="x"*81)),
         json.dumps(dict(v,deger=42)),json.dumps(dict(v,deger=float("nan"))),
         '{"islem":"sil","islem":"raporla","deger":"not","onay":false}',
         '{"islem":"raporla","deger":"ilk","deger":"son","onay":false}']
def sozlesme(f):
    try:
        for obj in valid:
            text=" \n"+json.dumps(obj,ensure_ascii=False)+"\t"
            a=f(text)
            if type(a) is not dict or a!=obj or type(a["onay"]) is not bool:
                return False
        if f(bosluk_siniri)!=v:
            return False
        for text in invalid:
            try:
                f(text)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
kontrol(sozlesme(fn),"katı JSON: tam şema, tam bool, uzunluk ve yinelenen anahtar reddi")

def onar(tur):
    def f(m):
        if not isinstance(m,str):
            raise ValueError("metin")
        if tur=="markdown" and m.startswith("```json"):
            m=m[7:-3].strip()
        if tur in ("ek","bool","duplicate"):
            x=json.loads(m)
            if isinstance(x,dict):
                if tur=="ek":x={k:v for k,v in x.items() if k in {"islem","deger","onay"}}
                if tur=="bool" and type(x.get("onay")) is int:x["onay"]=bool(x["onay"])
                m=json.dumps(x)
        return fn(m)
    return f
for ad,mutant in [("boş kod/işlev",None),("boş sözlük",lambda m:{}),
                  ("sabit gerçek şekilli nesne",lambda m:copy.deepcopy(v)),
                  ("bilinmeyen alanı düşüren",onar("ek")),
                  ("sayısal onayı bool'a çeviren",onar("bool")),
                  ("yinelenen anahtarı gizleyen",onar("duplicate")),
                  ("Markdown'u sessiz temizleyen",onar("markdown"))]:
    kontrol(not sozlesme(mutant),"hatalı çözüm reddedilmeli: "+ad)
if not all(sonuclar):
    stop()

try:
    kayitlar,ortam=lab14.gercek_ciktilar()
except Exception as e:
    kontrol(False,"GERÇEK JSON SCHEMA ÇAĞRISI YAPILAMADI: "+str(e))
    stop()
kontrol(len(kayitlar)==2,"iki gerçek şemalı model çağrısı tamamlandı")
ciktilar=[]
for k in kayitlar:
    try:
        a=fn(k["icerik"])
    except Exception as e:
        kontrol(False,"gerçek model çıktısı şemaya uymadı: "+str(e))
        continue
    kontrol(type(a) is dict and set(a)=={"islem","deger","onay"},"gerçek model JSON'u katı doğrulamadan geçti")
    kontrol(k["istek"]["format"]==lab14.SCHEMA and (k["istek"]["options"].get("num_gpu")==0)==(ai_lab.cihaz_kipi()=="cpu"),"gerçek istekte JSON Schema ve seçili cihaz ayarı kullanıldı")
    ciktilar.append({"ham":k,"dogrulanan":a,"istenen_degerlerle_ayni":a==k["beklenen"]})
kontrol(ai_lab.kaynak_temizlendi(ortam.get("temizlik")),"deney yalnız kendi kaynağını bıraktı (kendi sunucusu ya da kendi yüklediği model)")
bellek=ortam.get("bellek") or {}
kontrol(ai_lab.cihaz_dogrulandi(bellek),"gerçek /api/ps ölçümü seçili cihazla tutarlı (CPU kipinde VRAM 0)")
ai_lab.kanit_yaz("temel-14-schema",{
    "kaynak":"gercek","kabul":all(sonuclar),"ortam":ortam,
    "ayarlar":{"schema":lab14.SCHEMA,"cihaz":ai_lab.cihaz_kipi(),"num_ctx":1024,"num_predict":96},
    "ciktilar":ciktilar,"sinir":"şema/tür kabulü; semantik doğruluk ve araç yetkisi ayrı; araç yürütülmedi",
    "kaynak_belge":"https://docs.ollama.com/capabilities/structured-outputs"})
for k in ciktilar:
    print("gerçek JSON:",k["ham"]["icerik"],"istenen değerlerle aynı:",k["istenen_degerlerle_ayni"])
```

```solution
import ai_lab
import json

def kati_model_jsonu(metin):
    if not isinstance(metin,str) or len(metin)>4096:
        raise ValueError("metin geçersiz")
    def nesne(ciftler):
        out={}
        for k,v in ciftler:
            if k in out:
                raise ValueError("yinelenen anahtar")
            out[k]=v
        return out
    def sabit(_):
        raise ValueError("standart dışı JSON sayısı")
    x=json.loads(metin,object_pairs_hook=nesne,parse_constant=sabit)
    if type(x) is not dict or set(x)!={"islem","deger","onay"}:
        raise ValueError("şema geçersiz")
    if not isinstance(x["islem"],str) or x["islem"] not in ("not_ekle","raporla"):
        raise ValueError("işlem geçersiz")
    if not isinstance(x["deger"],str) or not 1<=len(x["deger"])<=80 or not x["deger"].strip():
        raise ValueError("değer geçersiz")
    if type(x["onay"]) is not bool:
        raise ValueError("onay bool olmalı")
    return dict(x)

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_temel_14 as lab14
    kayitlar,ortam=lab14.gercek_ciktilar()
    for k in kayitlar:
        print("Gerçek ham yanıt:",k["icerik"])
        print("Doğrulama:",kati_model_jsonu(k["icerik"]))
```

```hint
`object_pairs_hook`, JSON nesnesi sözlüğe dönüşmeden önce anahtar çiftlerini görür; yinelenen anahtarları burada reddet. `parse_constant` ile NaN/Infinity'yi engelle. Kod bloklarını veya bilinmeyen alanları temizlemek yerine geçersiz say.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Geçerli JSON != güvenli şema (30 sn).** "Modelin kısıtlı çözme (`constrained decoding`) ile sözdizimsel olarak geçerli JSON üretmesi, yinelenen anahtar, `NaN/Infinity`, beklenmeyen ek alan veya dizin geçişi (`../`) taşımadığı anlamına gelmez."
2. **Araç çağrısı veridir, yürütme ayrı karardır (35 sn).** "Modelin ürettiği araç adı ve argümanlar güvenilmeyen girdidir: yalnız izinli araç listesi (`allowlist`), katı tür/sınır denetimi (`bool` != `int`) ve göreli yol doğrulamasından geçtikten sonra çalıştırılabilir."
3. **Ayrıştırıcı farkları (`Parser Differential`) (30 sn).** "`object_pairs_hook` ile yinelenen anahtarları ve `parse_constant` ile standart dışı sayıları reddetmezsen doğrulayıcı ile alt katman farklı değeri okuyabilir."
4. **Soru (25 sn).** "Bir JSON nesnesinde `{"arac": "sil", "arac": "oku"}` gibi yinelenen anahtar geldiğinde standart `json.loads` sonuncuyu seçerken başka bir servis ilkini seçerse hangi güvenlik kapısı atlanır?"
:::
