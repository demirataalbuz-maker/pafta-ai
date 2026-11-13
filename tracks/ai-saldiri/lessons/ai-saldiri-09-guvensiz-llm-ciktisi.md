---
id: ai-saldiri-09
title: Güvensiz LLM Çıktısının İşlenmesi
summary: Model çıktısındaki HTML ve Markdown bağlantılarını güvenilmeyen girdi olarak ele al; HTML bağlamında kaçış uygula, URL şemasını ve sınırlı Markdown dönüşümünü doğrula.
timeout: 45
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et: Model çıktısı da güvenilmeyen girdidir

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Gerçek bir uygulamada model yanıtı bir sohbet arayüzünde, e-posta önizlemesinde ya da bir Markdown görüntüleyicide render edilir. Burp Suite ya da tarayıcı geliştirici araçları, yanıttaki `<img onerror>` veya `javascript:` bağlantısının DOM'a nasıl girdiğini gösterir. DOMPurify ve bleach gibi sanitizer'lar ile CSP bu yüzeyi daraltır. | Görev 1–3: `veri/html_ornekleri.json`, `veri/url_ornekleri.json` ve `veri/markdown_ornekleri.json` içindeki **sentetik** model çıktıları. Son adım: kurulu yerel Ollama modelinden iki gerçek yanıt ve Python'un gerçek `HTMLParser` ile yapılan etiket ölçümü. | Tarayıcı açılmaz ve JavaScript çalıştırılmaz. `HTMLParser`'ın etiket bulması, bir tarayıcıda XSS çalıştığını kanıtlamaz. Dersin Markdown dönüştürücüsü genel bir Markdown motoru değildir. URL kabulü SSRF koruması değildir. |

> [!NOT]
> Görev 1–3 sentetik veriyle çalışır. Bu görevlerde model, tarayıcı ve ağ yoktur. Son adımdaki **Gerçek deney** görevi yalnız kurulu yerel Ollama modelini ve deneyin kendi geçici klasörünü kullanır. `veri/` dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalanır; kopyada yaptığın değişiklik bir sonraki çalıştırmada sıfırlanır, **kalıcılık yoktur**. Son adımın düzenlenebilir örnek dosyası ise ayrıca kalıcı tutulur. Kontrol bu dosyalardan ayrı, gizli verilerle sınar.

Bir metni model üretmiş olması onu HTML, Markdown veya URL bağlamında güvenli yapmaz. Model; kullanıcı girdisini, web belgesini veya araç çıktısını yanıtına aynen taşıyabilir. `<script>` gibi bir etiket, olay işleyici özellik veya `javascript:` bağlantısı da model çıktısında bulunabilir.

Güvenli işleme, çıktının gideceği **sink** bağlamına göre yapılır:

- Düz metin bağlamında HTML etiketi yorumlanmamalıdır.
- HTML metin bağlamında `&`, `<`, `>`, `"`, `'` kaçışlanmalıdır.
- URL bağlamında izinli şema ve ağ konumu doğrulanmalıdır.
- HTML attribute, JavaScript veya CSS bağlamı için ayrı kodlama ve politika gerekir.

```python
import html
ham = '<img src=x onerror="alert(1)"> & not'
guvenli = html.escape(ham, quote=True)
print(guvenli)
print("<script>" in guvenli, "&lt;img" in guvenli)
```

Kaçış uygulamak içeriği anlamsal olarak zararsız veya doğru yapmaz; yalnız belirtilen HTML metin/attribute karakterlerinin markup olarak yorumlanmasını önler. Bu ders tarayıcı açmaz ve Burp Suite gerektirmez. Görev 1–3 dönüşüm sözleşmesini sentetik Python fixture'larıyla test eder. Son adım gerçek yerel model yanıtlarını gerçek bir HTML ayrıştırıcısından geçirir; JavaScript yine çalıştırılmaz.

**Sık tuzaklar:** Elle yazılmış bir `replace` zinciri, `&` karakterini en sona bırakırsa önce ürettiği `&lt;` dizisini de bozar (`&amp;lt;`). Tek tırnağı unutursa `title='...'` gibi bir attribute'un dışına çıkılabilir (`veri/html_ornekleri.json`, `h-01`, `h-04`). Önceden kaçışlanmış görünen metni "zaten güvenli" sanıp atlamak da yanlıştır. İşlev her zaman ham girdiyi bir kez kodlar (`h-03`).
:::

::: tahmin
HTML kaçışı ve URL şeması ayrı denetleniyor. Üç çıktı satırını yaz:

```python
import html
from urllib.parse import urlsplit
metin = '<b>Pafta</b> & "not"'
print(html.escape(metin, quote=True))
for url in ("https://ornek.test/ders", "javascript:alert(1)"):
    print(urlsplit(url).scheme in ("http", "https"))
```

???

```cikti
&lt;b&gt;Pafta&lt;/b&gt; &amp; &quot;not&quot;
True
False
```

İlk satırda etiketler artık markup değil metindir. İkinci URL izinli HTTPS şemasını kullanır; üçüncü satır `javascript:` için `False` olur.
:::

::: gorev 1 · HTML metin ve attribute kaçışını doğru uygula
`html_guvenli(metin)` işlevini yaz. `metin` string değilse `ValueError` yükselt. Standart kütüphanedeki `html.escape` ile `&`, `<`, `>`, `"`, `'` karakterlerini kaçışla; tırnak kaçışını açık tut. Boş string boş döner. Girdi stringi değiştirilemez; yeni string döndür.

Çift kaçış yapmaya çalışma: işlev her çağrıda kendisine verilen ham metni bir kez kodlar. Daha önce kaçışlanmış metin tekrar verilirse `&` karakterinin yeniden kodlanması beklenen davranıştır.

Görünür veri: `veri/html_ornekleri.json`. Beklenen çıktılar README tablosundadır. Üç bozuk girdi `ValueError` almalıdır.

```starter
from ai_saldiri_veri import json_yukle

def html_guvenli(metin):
    # KUSURLU BAŞLANGIÇ KODU: kaçışı elle ve yanlış sırayla yapıyor (& en son kodlanınca &lt; bozulur), tek tırnağı kaçırmıyor ve string olmayan girdiyi str() ile kabul ediyor!
    metin = str(metin)
    return metin.replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("&", "&amp;")

veri = json_yukle("veri/html_ornekleri.json")
for o in veri["ornekler"]:
    print(o["id"], repr(html_guvenli(o["metin"])))
for b in veri["bozuk_girdiler"]:
    try:
        html_guvenli(b)
        print(repr(b), "KABUL edildi (yanlış)")
    except ValueError as hata:
        print(repr(b), "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-09")
```

```test
import html
def sozlesme(fn):
    try:
        if fn('<b>Pafta</b> & "not"') != "&lt;b&gt;Pafta&lt;/b&gt; &amp; &quot;not&quot;":
            return False
        if fn("'tek'") != "&#x27;tek&#x27;" or fn("") != "":
            return False
        ham = '<img src=x onerror="alert(1)">'
        if fn(ham) != html.escape(ham, quote=True) or "<img" in fn(ham):
            return False
        if fn("&lt;") != "&amp;lt;":
            return False
        try:
            fn(None)
            return False
        except ValueError:
            pass
        return True
    except Exception:
        return False
ok(sozlesme(html_guvenli), "beş HTML karakteri, boş metin ve tür denetimi korunmalı")
def m_tirnaksiz(metin):
    return html.escape(metin, quote=False)
def m_degistir(metin):
    return metin.replace("<", "&lt;").replace(">", "&gt;")
def m_iki(metin):
    return html.escape(html.escape(metin, quote=True), quote=True)
for ad, mutant in [("tırnakları kaçırmayan", m_tirnaksiz), ("yalnız etiket köşelerini kodlayan", m_degistir), ("çift kaçış uygulayan", m_iki)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
import html

def html_guvenli(metin):
    if not isinstance(metin, str):
        raise ValueError("metin string olmalı")
    return html.escape(metin, quote=True)
```

```hint
`html.escape(metin, quote=True)` yeterlidir. Elle `replace` zinciri kurmak `&` karakterinin sırasını ve tek tırnağı kaçırabilir.
```
:::

::: anlat URL izni şemayla başlar ama bitmez
`javascript:` ve `data:` şemaları istemcide aktif içerik çalıştırabilir; bu nedenle Markdown bağlantısına izin verilen şemalar açıkça sınırlanır. `http` ve `https` için de yalnız öneki aramak yetmez: `https://` benzeri metin taşıyan kullanıcı bilgisi, eksik alan adı, kontrol karakterleri veya ayrıştırıcı farklılıkları denetlenmelidir.

Bu dersin dar URL sözleşmesinde kontrol/boşluk karakteri ve ters eğik çizgi reddedilir, şema `http` veya `https`, hostname zorunlu, kullanıcı adı/parola yasaktır. Bu politika XSS yüzeyini daraltır; hedef sunucunun güvenli olduğunu veya SSRF yapılamayacağını göstermez. Ağ bağlantısı güvenliği `ai-saldiri-21` dersindeki ayrı kontrolleri gerektirir.

`veri/url_ornekleri.json` içinde "https:// ile başlıyor" kontrolünü geçen ama politikaya uymayan beş adres vardır: kullanıcı bilgisi taşıyan, host'u boş olan, geçersiz portlu, boşluk ve sekme içeren adresler. `JaVaScRiPt:` gibi karışık harfli bir şema ise küçük harfe çevrilmeden yapılan kara liste kontrolünü atlatır. Bu yüzden izin listesi, ayrıştırılmış `scheme` üzerinde kurulur.
:::

::: gorev 2 · Markdown hedefinde kullanılabilir URL'yi doğrula
`url_guvenli(url)` işlevini yaz. String olmayan girdide `ValueError` yükselt. Aşağıdaki koşulların tamamı sağlanıyorsa özgün URL'yi aynen döndür, aksi hâlde `None` dön:

- Boş string, herhangi bir whitespace/kontrol karakteri veya `\\` içermemeli.
- `urllib.parse.urlsplit` ile ayrıştırıldığında şema `http` veya `https` olmalı.
- `hostname` boş olmamalı; kullanıcı adı ve parola bulunmamalı.
- Ayrıştırma veya port okuma hatası güvenli kabul edilmemeli.

Şema karşılaştırması büyük/küçük harf duyarsızdır. URL'de sorgu ve fragment bulunabilir. Bu işlev ağ isteği yapmaz ve hedefin iç ağda olup olmadığını değerlendirmez.

Görünür veri: `veri/url_ornekleri.json`. On iki adresten yalnız ilk ikisi aynen dönmelidir. İki bozuk girdi `ValueError` almalıdır.

```starter
from ai_saldiri_veri import json_yukle

def url_guvenli(url):
    # KUSURLU BAŞLANGIÇ KODU: yalnız öneke bakıyor (kullanıcı bilgisi, boş host, geçersiz port, boşluk ve sekme geçer) ve string olmayan girdide ValueError yerine None dönüyor!
    if not isinstance(url, str):
        return None
    if url.lower().startswith(("http://", "https://")):
        return url
    return None

veri = json_yukle("veri/url_ornekleri.json")
for u in veri["urller"]:
    print(repr(u), "→", repr(url_guvenli(u)))
for b in veri["bozuk_girdiler"]:
    try:
        url_guvenli(b)
        print(repr(b), "ValueError yerine sessizce döndü (yanlış)")
    except ValueError as hata:
        print(repr(b), "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-09")
```

```test
def sozlesme(fn):
    try:
        for url in ["https://ornek.test/ders", "HTTP://ORNEK.TEST/a?x=1&y=2#b", "http://127.0.0.1:8080/ Fixture".replace(" ", "")]:
            if fn(url) != url:
                return False
        for url in [
            "", "javascript:alert(1)", "data:text/html,x", "//ornek.test/yol",
            "https:///yol", "https://user:pass@ornek.test/", "https://user@ornek.test/",
            "https://ornek.test/a b", "https://ornek.test/\n", "https://ornek.test/\x00", "https://ornek.test\\@kotu.test/",
            "https://ornek.test/a\\b", "https://ornek.test:gecersiz/", "ftp://ornek.test/dosya",
        ]:
            if fn(url) is not None:
                return False
        for url in [None, 3]:
            try:
                fn(url)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(url_guvenli), "şema, hostname, kullanıcı bilgisi ve ayrıştırma hataları birlikte denetlenmeli")
def m_onek(url):
    return url if isinstance(url, str) and url.casefold().startswith(("http://", "https://")) else None
def m_scheme(url):
    from urllib.parse import urlsplit
    try:
        return url if urlsplit(url).scheme in ("http", "https") else None
    except Exception:
        return None
def m_userinfo(url):
    from urllib.parse import urlsplit
    try:
        parca = urlsplit(url)
        return url if parca.scheme in ("http", "https") and parca.hostname else None
    except Exception:
        return None
for ad, mutant in [("yalnız önek arayan", m_onek), ("hostname denetlemeyen", m_scheme), ("kullanıcı bilgisini kabul eden", m_userinfo)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
from urllib.parse import urlsplit

def url_guvenli(url):
    if not isinstance(url, str):
        raise ValueError("URL string olmalı")
    if not url or "\\" in url or any(c.isspace() or not c.isprintable() for c in url):
        return None
    try:
        parca = urlsplit(url)
        if parca.scheme not in ("http", "https") or not parca.hostname:
            return None
        if parca.username is not None or parca.password is not None:
            return None
        parca.port
    except (ValueError, UnicodeError):
        return None
    return url
```

```hint
`urlsplit` sonucundaki `scheme` ve `hostname` alanlarını kullan. `port` özelliğine erişmek geçersiz portu da ayrıştırma aşamasında yakalar; hiçbir yerde `urlopen` çağırma.
```
:::

::: anlat Sınırlı Markdown dönüşümü bütün Markdown değildir
Markdown'daki `[metin](hedef)` görünümü, hedef güvenli değilse tehlikeli bağlantıya dönüşebilir. Ayrıca metin veya hedefin dışındaki ham HTML de istemciye taşınmamalıdır. Bu derste yalnız tek satırlık, iç içe olmayan `[metin](hedef)` bağlantılarını tanıyan küçük bir dönüştürücü yazıyoruz. Başlık, tablo, kod bloğu, resim ve referans bağlantısı desteklediğini iddia etmiyoruz.

Algoritma özgün metindeki sınırlı bağlantıları bulur; güvenli URL'yi korur, güvensiz bağlantıyı yalnız görünen metne indirger. Sonra bütün sonuca HTML kaçışı uygular. Böylece etiketler metne dönüşür, URL'deki `&` HTML bağlamında `&amp;` olur. Gerçek üründe bakımı yapılan bir Markdown ayrıştırıcısı ve HTML allowlist sanitizer tercih edilmelidir; regex genel amaçlı HTML ayrıştırıcısı değildir.
:::

::: gorev 3 · Sınırlı Markdown çıktısını güvenli biçime dönüştür
`markdown_guvenli(metin)` işlevini yaz. String olmayan girdide `ValueError` yükselt. Yalnız `\[([^\]\n]*)\]\(([^)\s]+)\)` biçimindeki bağlantıları ele al. İkinci görevdeki URL politikasını uygula:

- Güvenli bağlantıyı `[görünen-metin](özgün-url)` olarak koru.
- Güvensiz bağlantıyı yalnız `görünen-metin` ile değiştir; hedefi sonuçta bırakma.

Dönüşümün sonunda bütün metne `html.escape(..., quote=True)` uygula. Böylece ham HTML, bağlantı metni ve dışarıdaki karakterler kaçışlanır. Yeni satır taşıyan veya sözleşmeye uymayan bağlantı biçimlerini ayrıştırmaya çalışma; onlar da HTML açısından kaçışlanmış düz metin kalır.

Görünür veri: `veri/markdown_ornekleri.json`. Beklenen çıktılar README tablosundadır. Sonuçta hiçbir ham `<` karakteri ya da güvensiz hedef kalmamalıdır. İki bozuk girdi `ValueError` almalıdır.

```starter
from ai_saldiri_veri import json_yukle

import re

def markdown_guvenli(metin):
    # KUSURLU BAŞLANGIÇ KODU: bağlantı hedefini yalnız önekle denetliyor ve sonuca HTML kaçışı uygulamıyor (ham <img onerror> ve <script> metni sink'e aynen gider)!
    def degistir(eslesme):
        gorunen, hedef = eslesme.group(1), eslesme.group(2)
        if hedef.lower().startswith(("http://", "https://")):
            return eslesme.group(0)
        return gorunen
    return re.sub(r"\[([^\]\n]*)\]\(([^)\s]+)\)", degistir, str(metin))

veri = json_yukle("veri/markdown_ornekleri.json")
for o in veri["ornekler"]:
    sonuc = markdown_guvenli(o["metin"])
    print(o["id"], repr(sonuc), "HAM <" if "<" in sonuc else "")
for b in veri["bozuk_girdiler"]:
    try:
        markdown_guvenli(b)
        print(repr(b), "KABUL edildi (yanlış)")
    except ValueError as hata:
        print(repr(b), "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-09")
```

```test
def sozlesme(fn):
    try:
        if fn('[Pafta](https://ornek.test/ders)') != '[Pafta](https://ornek.test/ders)':
            return False
        if fn('[tıkla](javascript:alert)') != 'tıkla' or 'javascript' in fn('[tıkla](javascript:alert)'):
            return False
        if fn('<b>kalın</b> [x](data:text/html,y)') != '&lt;b&gt;kalın&lt;/b&gt; x':
            return False
        cok = fn('[a](https://a.test/) ve <i>[b](HTTP://b.test/?x=1&y=2)</i>')
        if cok != '[a](https://a.test/) ve &lt;i&gt;[b](HTTP://b.test/?x=1&amp;y=2)&lt;/i&gt;':
            return False
        if fn('[<img src=x>](https://ornek.test/)') != '[&lt;img src=x&gt;](https://ornek.test/)':
            return False
        if fn('[a](https://ornek.test/a b)') != '[a](https://ornek.test/a b)':
            return False
        for baglanti in ['[x](ftp://ornek.test/a)', '[x](https://user@ornek.test/)', '[x](https://:80/yol)', '[x](https://ornek.test:gecersiz/)', '[x](https://ornek.test/\x00)', '[x](https://ornek.test/a\\b)']:
            if fn(baglanti) != 'x':
                return False
        if fn('"\' &') != '&quot;&#x27; &amp;' or fn('') != '':
            return False
        try:
            fn(None)
            return False
        except ValueError:
            pass
        return True
    except Exception:
        return False
ok(sozlesme(markdown_guvenli), "izinli bağlantı, güvensiz hedef temizliği ve bütün metin kaçışı korunmalı")
def m_dogrudan(metin):
    return metin
def m_sadece_html(metin):
    import html
    return html.escape(metin, quote=True)
def m_hedef_koran(metin):
    import re
    return re.sub(r'\[([^\]\n]*)\]\(([^)\s]+)\)', lambda m: m.group(1) + ' ' + m.group(2), metin)
for ad, mutant in [("çıktıyı doğrudan HTML sayan", m_dogrudan), ("tehlikeli bağlantıyı koruyan", m_sadece_html), ("güvensiz hedefi metne döken", m_hedef_koran)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
import html
import re
from urllib.parse import urlsplit

def markdown_guvenli(metin):
    if not isinstance(metin, str):
        raise ValueError("metin string olmalı")
    def guvenli_url(url):
        if not url or "\\" in url or any(c.isspace() or not c.isprintable() for c in url):
            return False
        try:
            parca = urlsplit(url)
            if parca.scheme not in ("http", "https") or not parca.hostname:
                return False
            if parca.username is not None or parca.password is not None:
                return False
            parca.port
            return True
        except (ValueError, UnicodeError):
            return False
    def donustur(eslesme):
        gorunen, hedef = eslesme.group(1), eslesme.group(2)
        return eslesme.group(0) if guvenli_url(hedef) else gorunen
    sinirli = re.sub(r"\[([^\]\n]*)\]\(([^)\s]+)\)", donustur, metin)
    return html.escape(sinirli, quote=True)
```

```hint
Önce `re.sub` callback'iyle yalnız sınırlı bağlantıları işle, sonra `html.escape` uygula. Güvensiz hedefin callback dönüşünde hiç yer almaması gerekir.
```
:::


::: anlat Gerçek model çıktısını dosyadan sink'e izle
[Sentetik ham örnek dosyasını aç](/data/ai-saldiri-09-ciktilar.txt). JSON listesi düz metin, HTML etiketi, güvenli URL ve güvensiz bağlantı örnekleri taşır; canlı yanıt diye sunulmaz. Çalıştır ayrı kalıcı `calisma/ai-saldiri-09/ciktilar.json` öğrenci kopyasının tam yolunu ve içeriğini gösterir. Kendi editöründe veya Python ile düzenleyip tekrar çalıştır; değişiklikler sıfırlanmaz. 1–8 adet, benzersiz `id` ve en çok 1500 karakterli `metin` taşıyan kayıt kullan. Uygulamada ayrı dosya editörü yoktur.

İki yeni yanıt gerçek yerel modelden alınır; modelin belirli metni aynen döndürmesi şart değildir. Öğrencinin üç işlevi hem sentetik kontrolleri hem canlı yanıtları işler. Gerçek `HTMLParser`, ham girdide oluşan etiketleri ve kaçışlanmış girdinin yalnız metne dönüşmesini ölçer. Bu ayrıştırıcı JavaScript çalıştırmaz; sonuçları tarayıcıda XSS çalıştırılmış gibi yorumlama. Markdown çıktısı bu dersin dar sözleşmesine göre dönüştürülmüş metindir; genel Markdown motoru yoktur.

Çalıştır ham yanıtları `.txt`, güvenli metin belgelerini `.html` olarak ayrı dosyalara yazar ve yollarını gösterir. Güvenli belgeyi tarayıcında açıp etiketlerin metin olarak göründüğünü inceleyebilirsin. Bu dosyalar öğrenci alanında korunur; hatalı kaçış çözümünün etkin HTML'si belgeye konmaz, güvenli referans kopyası kullanılır ve test yine başarısız olur. Kabul, örneği ezberlemek yerine yeni metinlerle ve gerçek çağrılarla yapılır. URL kabulü SSRF koruması değildir.
:::

::: gorev Gerçek deney · Canlı çıktıyı HTML sink'inde ve dosyada incele
Önceki üç işlevi birleştir: `html_guvenli`, `url_guvenli`, `markdown_guvenli`. Çalıştır ham/sentetik ve canlı model kayıtlarını ayrı etiketlerle, parser sonuçlarını ve güvenli dosya yollarını gösterir. Kontrol Et yeni metinlerde doğruluğu ve gerçek çağrıların tamamlanmasını sınar. GPU ortak kilitle sıraya girer, model çıktısı sabit metinle karşılaştırılmaz.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab

def html_guvenli(metin):
    # KUSURLU BAŞLANGIÇ KODU: kaçışı elle ve yanlış sırayla yapıyor (& en son kodlanınca &lt; bozulur), tek tırnağı kaçırmıyor ve string olmayan girdiyi str() ile kabul ediyor!
    metin = str(metin)
    return metin.replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("&", "&amp;")

def url_guvenli(url):
    # KUSURLU BAŞLANGIÇ KODU: yalnız öneke bakıyor (kullanıcı bilgisi, boş host, geçersiz port, boşluk ve sekme geçer) ve string olmayan girdide ValueError yerine None dönüyor!
    if not isinstance(url, str):
        return None
    if url.lower().startswith(("http://", "https://")):
        return url
    return None

import re

def markdown_guvenli(metin):
    # KUSURLU BAŞLANGIÇ KODU: bağlantı hedefini yalnız önekle denetliyor ve sonuca HTML kaçışı uygulamıyor (ham <img onerror> ve <script> metni sink'e aynen gider)!
    def degistir(eslesme):
        gorunen, hedef = eslesme.group(1), eslesme.group(2)
        if hedef.lower().startswith(("http://", "https://")):
            return eslesme.group(0)
        return gorunen
    return re.sub(r"\[([^\]\n]*)\]\(([^)\s]+)\)", degistir, str(metin))

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_09 as deney
    deney.goster(html_guvenli,url_guvenli,markdown_guvenli)

```

```test
import html
def sozlesme(fn):
    try:
        if fn('<b>Pafta</b> & "not"') != "&lt;b&gt;Pafta&lt;/b&gt; &amp; &quot;not&quot;":
            return False
        if fn("'tek'") != "&#x27;tek&#x27;" or fn("") != "":
            return False
        ham = '<img src=x onerror="alert(1)">'
        if fn(ham) != html.escape(ham, quote=True) or "<img" in fn(ham):
            return False
        if fn("&lt;") != "&amp;lt;":
            return False
        try:
            fn(None)
            return False
        except ValueError:
            pass
        return True
    except Exception:
        return False
ok(sozlesme(html_guvenli), "beş HTML karakteri, boş metin ve tür denetimi korunmalı")
def m_tirnaksiz(metin):
    return html.escape(metin, quote=False)
def m_degistir(metin):
    return metin.replace("<", "&lt;").replace(">", "&gt;")
def m_iki(metin):
    return html.escape(html.escape(metin, quote=True), quote=True)
for ad, mutant in [("tırnakları kaçırmayan", m_tirnaksiz), ("yalnız etiket köşelerini kodlayan", m_degistir), ("çift kaçış uygulayan", m_iki)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

def sozlesme(fn):
    try:
        for url in ["https://ornek.test/ders", "HTTP://ORNEK.TEST/a?x=1&y=2#b", "http://127.0.0.1:8080/ Fixture".replace(" ", "")]:
            if fn(url) != url:
                return False
        for url in [
            "", "javascript:alert(1)", "data:text/html,x", "//ornek.test/yol",
            "https:///yol", "https://user:pass@ornek.test/", "https://user@ornek.test/",
            "https://ornek.test/a b", "https://ornek.test/\n", "https://ornek.test/\x00", "https://ornek.test\\@kotu.test/",
            "https://ornek.test/a\\b", "https://ornek.test:gecersiz/", "ftp://ornek.test/dosya",
        ]:
            if fn(url) is not None:
                return False
        for url in [None, 3]:
            try:
                fn(url)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(url_guvenli), "şema, hostname, kullanıcı bilgisi ve ayrıştırma hataları birlikte denetlenmeli")
def m_onek(url):
    return url if isinstance(url, str) and url.casefold().startswith(("http://", "https://")) else None
def m_scheme(url):
    from urllib.parse import urlsplit
    try:
        return url if urlsplit(url).scheme in ("http", "https") else None
    except Exception:
        return None
def m_userinfo(url):
    from urllib.parse import urlsplit
    try:
        parca = urlsplit(url)
        return url if parca.scheme in ("http", "https") and parca.hostname else None
    except Exception:
        return None
for ad, mutant in [("yalnız önek arayan", m_onek), ("hostname denetlemeyen", m_scheme), ("kullanıcı bilgisini kabul eden", m_userinfo)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

def sozlesme(fn):
    try:
        if fn('[Pafta](https://ornek.test/ders)') != '[Pafta](https://ornek.test/ders)':
            return False
        if fn('[tıkla](javascript:alert)') != 'tıkla' or 'javascript' in fn('[tıkla](javascript:alert)'):
            return False
        if fn('<b>kalın</b> [x](data:text/html,y)') != '&lt;b&gt;kalın&lt;/b&gt; x':
            return False
        cok = fn('[a](https://a.test/) ve <i>[b](HTTP://b.test/?x=1&y=2)</i>')
        if cok != '[a](https://a.test/) ve &lt;i&gt;[b](HTTP://b.test/?x=1&amp;y=2)&lt;/i&gt;':
            return False
        if fn('[<img src=x>](https://ornek.test/)') != '[&lt;img src=x&gt;](https://ornek.test/)':
            return False
        if fn('[a](https://ornek.test/a b)') != '[a](https://ornek.test/a b)':
            return False
        for baglanti in ['[x](ftp://ornek.test/a)', '[x](https://user@ornek.test/)', '[x](https://:80/yol)', '[x](https://ornek.test:gecersiz/)', '[x](https://ornek.test/\x00)', '[x](https://ornek.test/a\\b)']:
            if fn(baglanti) != 'x':
                return False
        if fn('"\' &') != '&quot;&#x27; &amp;' or fn('') != '':
            return False
        try:
            fn(None)
            return False
        except ValueError:
            pass
        return True
    except Exception:
        return False
ok(sozlesme(markdown_guvenli), "izinli bağlantı, güvensiz hedef temizliği ve bütün metin kaçışı korunmalı")
def m_dogrudan(metin):
    return metin
def m_sadece_html(metin):
    import html
    return html.escape(metin, quote=True)
def m_hedef_koran(metin):
    import re
    return re.sub(r'\[([^\]\n]*)\]\(([^)\s]+)\)', lambda m: m.group(1) + ' ' + m.group(2), metin)
for ad, mutant in [("çıktıyı doğrudan HTML sayan", m_dogrudan), ("tehlikeli bağlantıyı koruyan", m_sadece_html), ("güvensiz hedefi metne döken", m_hedef_koran)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

from sandbox import ai_gercek_ai_saldiri_09 as deney
import html, secrets, tempfile
from pathlib import Path
import ast
_yasak=('url_referans','markdown_referans','_sink','kanit_yaz')
_sorun=list(ai_lab.kod_denetimi(src,_yasak))
for _n in ast.walk(ast.parse(src)):
    if isinstance(_n,ast.ImportFrom) and any(a.name in _yasak or a.name=='*' for a in _n.names):_sorun.append('referans importu yasak')
    if isinstance(_n,(ast.Import,ast.ImportFrom)) and any(x and x.split('.')[0] in ('inspect','importlib','runpy') for x in [a.name for a in _n.names]+([_n.module] if isinstance(_n,ast.ImportFrom) else [])):_sorun.append('kaynak okuma/dinamik import yasak')
    if isinstance(_n,ast.Name) and _n.id in ('exec','eval','compile','__builtins__'):_sorun.append('dinamik kod çalıştırma yasak: '+_n.id)
if not ok(not _sorun, 'laboratuvar/referanslar yamalanmamalı, referans kullanılmamalı: '+'; '.join(sorted(set(_sorun)))):stop()
for i in range(5):
    marker=secrets.token_hex(4)
    raw='<b data-x="'+marker+'">'+marker+"</b> & '\""
    if not ok(html_guvenli(raw)==html.escape(raw,quote=True),'yeni metin/attribute beş karakter kaçışı'):stop()
    if not ok(markdown_guvenli('[x](javascript:'+marker+') '+raw)=='x '+html.escape(raw,quote=True),'yeni güvensiz hedef kaldırılmalı ve HTML kaçışlanmalı'):stop()
    if not ok(url_guvenli('https://user@'+marker+'.test/') is None and url_guvenli('https://'+marker+'.test/')=='https://'+marker+'.test/','yeni URL kullanıcı bilgisi ve meşru hedef ayrılmalı'):stop()
with tempfile.TemporaryDirectory(prefix='pafta_sink09_') as tmp:
    samples=[dict(id='yeni-'+str(i),metin='<b>'+secrets.token_hex(4)+'</b> [x](javascript:alert)') for i in range(3)]
    result=deney.deney(html_guvenli,url_guvenli,markdown_guvenli,samples,Path(tmp))
    for key,value in result['kontroller'].items():ok(value,'gerçek deney: '+key)
    ok(result['ozet']['ham_markup_ornek']>=3 and result['ozet']['korumali_markup_ornek']==0,'sentetik pozitif kontrolde gerçek HTML parser farkı')
    accepted=all(result['kontroller'].values()) and result['ozet']['korumali_markup_ornek']==0
    ai_lab.kanit_yaz('saldiri-09-cikti',dict(result,kabul=accepted))
    ok(accepted,'iki canlı model yanıtı gerçek sinkte işlendi; modelin tehlikeli çıktı vermesi şart değil')

```

```solution
import ai_lab

import html

def html_guvenli(metin):
    if not isinstance(metin, str):
        raise ValueError("metin string olmalı")
    return html.escape(metin, quote=True)

from urllib.parse import urlsplit

def url_guvenli(url):
    if not isinstance(url, str):
        raise ValueError("URL string olmalı")
    if not url or "\\" in url or any(c.isspace() or not c.isprintable() for c in url):
        return None
    try:
        parca = urlsplit(url)
        if parca.scheme not in ("http", "https") or not parca.hostname:
            return None
        if parca.username is not None or parca.password is not None:
            return None
        parca.port
    except (ValueError, UnicodeError):
        return None
    return url

import html
import re
from urllib.parse import urlsplit

def markdown_guvenli(metin):
    if not isinstance(metin, str):
        raise ValueError("metin string olmalı")
    def guvenli_url(url):
        if not url or "\\" in url or any(c.isspace() or not c.isprintable() for c in url):
            return False
        try:
            parca = urlsplit(url)
            if parca.scheme not in ("http", "https") or not parca.hostname:
                return False
            if parca.username is not None or parca.password is not None:
                return False
            parca.port
            return True
        except (ValueError, UnicodeError):
            return False
    def donustur(eslesme):
        gorunen, hedef = eslesme.group(1), eslesme.group(2)
        return eslesme.group(0) if guvenli_url(hedef) else gorunen
    sinirli = re.sub(r"\[([^\]\n]*)\]\(([^)\s]+)\)", donustur, metin)
    return html.escape(sinirli, quote=True)
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_09 as deney
    deney.goster(html_guvenli,url_guvenli,markdown_guvenli)

```

```hint
HTML kaçışını bir kez ve quote=True uygula. URL politikasını Markdown callback'inde kullan; güvensiz hedefi tamamen at. Çıktıyı gerçek parser'dan geçirirken etiket oluşmaması ile ham metnin korunmasını birlikte kontrol et.
```
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
Modelin ürettiği HTML bir başka güvenilmeyen girdidir. Metin kaçışı, URL politikasından farklı işlemdir: ilki etiket karakterlerini metin yapar; ikincisi scheme/host/userinfo belirsizliklerini reddeder. Sınırlı Markdown dönüştürücünün desteklediği dil alt kümesini söyle. HTMLParser ile ayrıştırma gerçek tarayıcıda JavaScript çalıştırma değildir; sonucun hangi render iddiasını doğrulamadığını açık tut.

Önkoşul ve yol köprüsü: ai-saldiri-21 gerçek bağlantı sınırı.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| HTTP URL güvenliyse SSRF de engellenir | XSS URL politikası ağ hedefi yetkisini kanıtlamaz |

Dinleyiciye sor: Bu mekanizmada hangi bilgi veri, hangisi yetki kaynağıdır; testin geçtiğini hangi gerçek gözlemle kanıtlarsın? Sentetik örnek ile canlı deney kaydını ayrı göstererek cevapla.
:::


::: anlat Birincil kaynak ve deney sınırı
[Python html.escape](https://docs.python.org/3/library/html.html): HTML karakter kaçışının anlamı için referans. Kaçış URL yetkilendirmesi, CSP veya tarayıcı tabanlı XSS doğrulamasıyla aynı işlem değildir. Çalışan araç/model sürümü canlı kanıtta saklanır; bağlantıdaki belge sürümüyle otomatik eşit kabul edilmez.
:::
