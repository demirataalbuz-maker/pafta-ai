---
id: ai-saldiri-22
title: SSRF Filtre ve Yönlendirme Atlatma
summary: URL'yi tek bir kanonik origin'e indir, her yönlendirme hedefini yeniden doğrula, DNS cevapları ile gerçek socket hedefi arasındaki sapmaları raporla.
timeout: 45
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et: Filtrenin okuduğu hedef ile bağlanılan hedef aynı olmalı

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Burp Suite veya mitmproxy ile bir LLM aracının attığı HTTP istekleri izlenir. Yönlendirme zinciri, DNS çözümü ve sunucunun gördüğü gerçek TCP peer adresi kaydedilir. Bulutta asıl hedef genellikle metadata servisidir (`169.254.169.254`). | Görev 1–3: `veri/url_ornekleri.json`, `veri/redirect_zincirleri.json` ve `veri/dns_kayitlari.json` içindeki **sentetik** URL, yönlendirme ve DNS kayıtları. Son adım: deneyin kendi açtığı iki yerel HTTP sunucusuna gerçek TCP bağlantıları kurulur ve kurulu yerel Ollama modelinin seçtiği URL aynı kapıdan geçirilir. | Bu ders yalnız `http`, açık port ve IPv4 içeren dar bir politikayı modeller. IPv6, HTTPS SNI, proxy zinciri ve gerçek DNS rebinding saldırısı kapsam dışıdır. Son adımdaki rebinding negatifleri sentetik DNS kayıtlarıdır. |

> [!NOT]
> Görev 1–3 sentetik veriyle çalışır. Bu görevlerde ağ, DNS veya model kullanılmaz. Son adımdaki **Gerçek deney** görevi yalnız deneyin kendi açtığı iki yerel HTTP sunucusuna bağlanır ve kurulu yerel Ollama modelini çalıştırır. Dış ağa istek gitmez, yeni araç indirilmez. mitmproxy ve Burp Suite çalıştırılmaz. `veri/` dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalanır; kopyada yaptığın değişiklik bir sonraki çalıştırmada sıfırlanır, **kalıcılık yoktur**. Son adımın düzenlenebilir URL vaka dosyası ise ayrıca kalıcı tutulur. Kontrol bu dosyalardan ayrı, gizli verilerle sınar.

SSRF filtresi URL string'ine bakarken HTTP istemcisi ayrıştırıcı, yönlendirme ve DNS katmanlarından geçer. Bu katmanlar farklı hedefler görürse ilk kontrol doğru olsa bile son bağlantı iç servise gidebilir. Özellikle userinfo, eksik port, trailing dot, şema değişimi ve `//host/...` biçimindeki ağ-yolu referansları basit string kontrollerini bozar.

Savunma tek bir kontrol noktasında üç şeyi bağlar: kanonik origin, her redirect sonrası yeniden politika kontrolü ve DNS'de karar verilen IP ile socket'e verilen IP'nin aynılığı. İlk URL'nin izinli olması son hedef için kanıt değildir.

Görev 1–3 URL, yönlendirme ve DNS kayıtlarını sentetik olarak işler. Son adım aynı kapıyı gerçek HTTP bağlantılarının önüne koyar; 21. dersteki gerçek loopback laboratuvarı yeniden kullanılır.

**LLM aracında SSRF neden kolaylaşır?** Klasik SSRF'de saldırgan bir web formuna URL yazar. LLM uygulamasında ise URL'yi çoğu zaman model üretir: "şu sayfayı özetle", "bu belgede geçen bağlantıyı aç". Saldırganın doğrudan erişimi olmasa bile, modelin okuyacağı bir belgeye "asıl kaynak `http://169.254.169.254/...` adresinde" diye yazması yeter. Model bu URL'yi aracın argümanına koyar, araç sunucunun kendi ağından isteği atar ve yanıt modelin bağlamına, oradan da kullanıcıya döner.

**Saldırgan bakışı:** Filtre URL metnine bakar, HTTP istemcisi ise başka bir şeye bağlanır. Saldırgan bu farkı kullanır:

- `http://public.test:80\@internal.test/`: Bazı ayrıştırıcılar `\` karakterini yol, bazıları userinfo ayıracı sayar ve iki farklı host görür.
- `http://user@...`: Bilgilendirme gibi görünen userinfo bölümü bazı filtreleri şaşırtır.
- `PUBLIC.test.`: Büyük harf ve sondaki nokta, string karşılaştırmasıyla yapılan izin listelerini atlatır.
- İzinli bir sayfanın `302` ile iç adrese yönlendirmesi.
- DNS cevabını ilk kontrolden sonra değiştirmek (rebinding).

`veri/` dosyalarındaki her vaka bu yollardan birini gösterir.
:::

::: tahmin Göreli gibi görünen hedef aynı origin'de mi?
Ağ-yolu referansı `//` ile başlar ve mevcut şemayı koruyarak hostu değiştirir. Üç çıktı satırını yaz:

```python
from urllib.parse import urljoin, urlsplit
ilk = "http://public.test:80/start"
yeni = urljoin(ilk, "//internal.test:80/canary")
print(yeni)
print(urlsplit(ilk).hostname)
print(urlsplit(yeni).hostname)
```

???

```cikti
http://internal.test:80/canary
public.test
internal.test
```

Yeni hedef aynı scheme'i kullansa da origin değişmiştir. Bu nedenle her `Location` çözümlendikten sonra baştan doğrulanmalıdır.
:::

::: gorev 1 · URL'yi dar ve kanonik bir origin'e indir
`url_origin(url)` işlevini yaz. Girdi ASCII 33–126 aralığındaki karakterlerden oluşan string olmalı; boşluk/kontrol, non-ASCII, ters eğik çizgi ve fragment içeremez. Yalnız `http`, açık port ve userinfo'suz URL kabul edilir. Host yalnız ASCII harf, rakam, nokta ve tire içerebilir. Hostu küçük harfe çevir ve sondaki noktaları kaldır; sonuç boşalamaz. IPv6 bu dar fixture politikasının dışındadır. Ayrıştırma, port, şema veya şema dışı tür hatasında `ValueError` yükselt.

Dönüş tam olarak `{"origin":"http://HOST:PORT","host":HOST,"port":PORT}` biçimindedir. Path ve query origin kararını değiştirmez. Gerçek DNS veya ağ erişimi yapma.

Görünür veri: `veri/url_ornekleri.json`. Beklenen sonuçlar README tablosundadır. İlk üç URL origin üretmeli, kalan yedi URL reddedilmelidir.

```starter
from ai_saldiri_veri import json_yukle

def url_origin(url):
    # KUSURLU BAŞLANGIÇ KODU: hostu küçültmüyor ve sondaki noktayı silmiyor, userinfo/fragment/ters eğik çizgiyi reddetmiyor, porta yoksa 80 varsayıyor ve https'i de kabul ediyor!
    from urllib.parse import urlsplit
    u = urlsplit(url)
    host = u.hostname or ""
    port = u.port or 80
    return {"origin": f"http://{host}:{port}", "host": host, "port": port}

veri = json_yukle("veri/url_ornekleri.json")
for u in veri["urller"]:
    try:
        print(repr(u), "→", url_origin(u)["origin"])
    except ValueError as hata:
        print(repr(u), "→ RED:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-22")
```

```test
def sozlesme(fn):
    try:
        if fn("http://public.test:80/a?x=1") != {"origin": "http://public.test:80", "host": "public.test", "port": 80}:
            return False
        if fn("HTTP://PUBLIC.TEST.:8080/x") != {"origin": "http://public.test:8080", "host": "public.test", "port": 8080}:
            return False
        if fn("http://127.0.0.1:65535/")["port"] != 65535:
            return False
        if fn("http://public.test:1/a!b~")["port"] != 1:
            return False
        for url in [
            None, 3, "", "/a", "https://public.test:80/a", "http://public.test/a",
            "http://public.test:/a", "http://public.test:0/a", "http://public.test:65536/a",
            "http://user@public.test:80/a", "http://user:pw@public.test:80/a",
            "http://public.test:80/a#x", "http://public.test:80/a\\b",
            "http://public.test:80/a b", "http://public.test:80/ğ",
            "http://:80/a", "http://...:80/a", "http://[::1]:80/a",
            "http://public_test:80/a", "http://public.test:80/a\tb",
            "http://public.test:80/a\x7fb",
        ]:
            try:
                fn(url)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(url_origin), "şema, userinfo, açık port, kanonik host ve ASCII sınırı korunmalı")
def m_sema(url):
    return url_origin(url.replace("https://", "http://"))
def m_user(url):
    return url_origin(url.replace("user@", ""))
def m_port(url):
    return url_origin(url.replace("http://public.test/", "http://public.test:80/"))
for ad, mutant in [("https'i http'ye çeviren", m_sema), ("userinfo'yu gizleyen", m_user), ("eksik portu tamamlayan", m_port)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def url_origin(url):
    from urllib.parse import urlsplit
    if not isinstance(url, str) or not url or any(ord(c) < 33 or ord(c) > 126 for c in url):
        raise ValueError("URL karakterleri geçersiz")
    if "\\" in url or "#" in url:
        raise ValueError("belirsiz URL")
    try:
        u = urlsplit(url)
        if u.scheme != "http" or not u.hostname or u.username is not None or u.password is not None:
            raise ValueError("URL origin'i geçersiz")
        host = u.hostname.lower().rstrip(".")
        port = u.port
    except (TypeError, ValueError) as exc:
        raise ValueError("URL ayrıştırılamadı") from exc
    if not host or not all(c.isascii() and (c.isalnum() or c in ".-") for c in host):
        raise ValueError("host geçersiz")
    if port is None or port < 1:
        raise ValueError("açık port gerekli")
    return {"origin": "http://" + host + ":" + str(port), "host": host, "port": port}
```

```hint
`urlsplit` sonrasında scheme, hostname, userinfo ve portu ayrı denetle. Dönüş origin'ini girdiden kopyalamak yerine normalize edilmiş host ve doğrulanmış porttan yeniden kur.
```
:::

::: anlat Her Location yeni bir istek adayıdır
`Location: /ok` aynı origin'de kalırken `Location: //internal.test:80/canary` hostu değiştirir. Filtre yalnız başlangıç URL'sine uygulanırsa ikinci istek kontrolden kaçar. Güvenli iz, başlangıç ve her çözümlenmiş hedef için aynı doğrulamayı çalıştırır.

Hop sınırı da politikanın parçasıdır. Sınır aşıldığında yeni hedefi doğrulamadan kabul etmek yerine bütün zincir reddedilir. Bu görev HTTP yanıtı üretmez; yalnız istemcinin sırayla hangi URL'lere istek açacağını hesaplar.

**Sık tuzaklar:**

- **Yalnız başlangıcı denetlemek:** Python'un `urllib` ve `requests` kütüphaneleri yönlendirmeleri varsayılan olarak kendileri izler. Filtre yalnız ilk URL'ye bakarsa son hedefi hiç görmez. `veri/redirect_zincirleri.json` içindeki `ikinci-hopta-kacis` zincirinde ilk yönlendirme masumdur.
- **Origin'i string olarak karşılaştırmak:** `http://PUBLIC.TEST.:80` ile `http://public.test:80` aynı origin'dir. Karşılaştırma kanonik biçimle yapılır, ham metinle yapılmaz.
- **Örtük port:** `http://public.test/ok` port yazmaz. Dar politika açık port ister. Böylece `:80` ile `:8080` farkı gözden kaçmaz.
- **Kırpılmış zincir:** Sınır aşıldığında ilk N hedefi kabul edip devam etmek, saldırgana "N+1. adımda kaçış" yolu bırakır.
:::

::: gorev 2 · Başlangıç ve her redirect hedefini aynı origin'e bağla
`redirect_originleri(baslangic, locationlar, izinli_origin, max_hop=3)` işlevini yaz. `izinli_origin`, ilk görevin ürettiği kanonik `http://host:port` stringi olmalı; path, query, trailing slash veya farklı yazım kabul edilmez. Başlangıç ve her hedef ilk görevdeki URL kurallarına uymalı ve origin'i birebir izinli origin olmalıdır. `locationlar` string listesidir; her `Location` mevcut URL'ye göre `urljoin` ile çözümlenir. `max_hop` bool olmayan sıfır/pozitif int olmalı ve redirect sayısı bunu aşamaz. Geçersiz veri, origin değişimi veya sınır aşımında `ValueError` yükselt.

Dönüş `{"hop":N,"son_url":SON,"istekler":[BASLANGIC,...]}` biçimindedir. `istekler` başlangıç ve kabul edilmiş bütün hedefleri sırayla içerir; girdi listesinden bağımsızdır. Ağ erişimi yapma.

Görünür veri: `veri/redirect_zincirleri.json`. Yalnız `ayni-origin` ve `buyuk-harf-host` zincirleri kabul edilmelidir.

```starter
from urllib.parse import urljoin, urlsplit
from ai_saldiri_veri import json_yukle

def redirect_originleri(baslangic, locationlar, izinli_origin, max_hop=3):
    # KUSURLU BAŞLANGIÇ KODU: yalnız BAŞLANGIÇ URL'sinin hostunu denetliyor, yönlendirme hedeflerini doğrulamadan izliyor ve hop sınırı aşılınca kalan Location'ları sessizce atıyor!
    if urlsplit(baslangic).hostname != urlsplit(izinli_origin).hostname:
        raise ValueError("başlangıç izinsiz")
    istekler = [baslangic]
    for loc in locationlar[:max_hop]:
        istekler.append(urljoin(istekler[-1], loc))
    return {"hop": len(istekler) - 1, "son_url": istekler[-1], "istekler": istekler}

veri = json_yukle("veri/redirect_zincirleri.json")
for z in veri["zincirler"]:
    try:
        r = redirect_originleri(z["baslangic"], z["locationlar"], veri["izinli_origin"], veri["max_hop"])
        print(z["ad"], "→", r["hop"], "hop, son:", r["son_url"])
    except ValueError as hata:
        print(z["ad"], "→ RED:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-22")
```

```test
def sozlesme(fn):
    try:
        origin = "http://public.test:80"
        beklenen = {"hop": 2, "son_url": "http://public.test:80/a/son", "istekler": ["http://public.test:80/a/basla", "http://public.test:80/a/orta", "http://public.test:80/a/son"]}
        if fn("http://public.test:80/a/basla", ["orta", "son"], origin) != beklenen:
            return False
        if fn("http://public.test:80/a", [], origin, max_hop=0) == {"hop": 0, "son_url": "http://public.test:80/a", "istekler": ["http://public.test:80/a"]}:
            pass
        else:
            return False
        if fn("http://public.test:80/a!~", ["/b!~"], origin, max_hop=1)["son_url"] != "http://public.test:80/b!~":
            return False
        if fn("http://public.test:1/a", [], "http://public.test:1")["hop"] != 0:
            return False
        if fn("http://public.test:80/a", ["/1", "/2", "/3"], origin)["hop"] != 3:
            return False
        try:
            fn("http://public.test:80/a", ["/a", "/b", "/c", "/d"], origin)
            return False
        except ValueError:
            pass
        for baslangic, locations, allowed, limit in [
            (3, [], origin, 3),
            ("http://public.test:80/a\\b", [], origin, 3),
            ("http://:80/a", [], "http://:80", 3),
            ("http://public.test:0/a", [], "http://public.test:0", 3),
            ("http://public_test:80/a", [], "http://public_test:80", 3),
            ("http://public.test:80/a", [], "HTTP://PUBLIC.TEST:80", 3),
            ("http://internal.test:80/a", [], origin, 3),
            ("http://public.test:80/a", ["//internal.test:80/canary"], origin, 3),
            ("http://public.test:80/a", ["/orta", "https://public.test:80/son"], origin, 3),
            ("http://public.test:80/a", ["http://user@public.test:80/x"], origin, 3),
            ("http://public.test:80/a", ["http://:80/x"], origin, 3),
            ("http://public.test:80/a", ["http://public.test/x"], origin, 3),
            ("http://public.test:80/a", ["http://public.test:0/x"], origin, 3),
            ("http://public_test:80/a", [], origin, 3),
            ("http://public.test:80/a", ["/x"], "http://public.test:80/", 3),
            ("http://public.test:80/a", ["/x"], "http://public.test:80/path", 3),
            ("http://public.test:80/a", ["/x"], "http://public.test:80?x=1", 3),
            ("http://public.test:80/a", ["/x"], origin, 0),
            ("http://public.test:80/a", [], origin, -1),
            ("http://public.test:80/a", [], origin, True),
            ("http://public.test:80/a", "/x", origin, 3),
            ("http://public.test:80/a", [None], origin, 3),
            ("http://public.test:80/a", ["/a b"], origin, 3),
            ("http://public.test:80/a", ["/a#x"], origin, 3),
            ("http://public.test:80/a", ["/a\x7fb"], origin, 3),
        ]:
            try:
                fn(baslangic, locations, allowed, limit)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(redirect_originleri), "göreli çözümleme, her hop origin kontrolü ve hop sınırı korunmalı")
def m_atla(baslangic, locationlar, izinli_origin, max_hop=3):
    from urllib.parse import urljoin
    sonuc = redirect_originleri(baslangic, [], izinli_origin, max_hop)
    current = baslangic
    for location in locationlar:
        current = urljoin(current, location)
        sonuc["istekler"].append(current)
    sonuc["hop"] = len(locationlar)
    sonuc["son_url"] = current
    return sonuc
def m_limit(baslangic, locationlar, izinli_origin, max_hop=3):
    return redirect_originleri(baslangic, locationlar, izinli_origin, max(max_hop, len(locationlar)))
def m_location(baslangic, locationlar, izinli_origin, max_hop=3):
    return redirect_originleri(baslangic, ["/sabit" for _ in locationlar], izinli_origin, max_hop)
for ad, mutant in [("redirect kontrollerini atlayan", m_atla), ("hop sınırını büyüten", m_limit), ("Location değerini yok sayan", m_location)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def redirect_originleri(baslangic, locationlar, izinli_origin, max_hop=3):
    from urllib.parse import urlsplit, urljoin
    if type(max_hop) is not int or max_hop < 0 or not isinstance(locationlar, list):
        raise ValueError("hop veya Location listesi geçersiz")
    if len(locationlar) > max_hop:
        raise ValueError("hop sınırı aşıldı")
    def origin_denetle(url):
        import re
        from urllib.parse import urlsplit
        if not isinstance(url, str) or not url or any(ord(c) < 33 or ord(c) > 126 for c in url) or "\\" in url or "#" in url:
            raise ValueError("URL geçersiz")
        try:
            u = urlsplit(url)
            host = u.hostname.lower().rstrip(".") if u.hostname else ""
            origin = "http://" + host + ":" + str(u.port)
            if u.scheme != "http":
                raise ValueError("şema geçersiz")
            if not host:
                raise ValueError("host gerekli")
            if u.username is not None:
                raise ValueError("kullanıcı bilgisi geçersiz")
            if u.password is not None:
                raise ValueError("parola geçersiz")
            if u.port is None:
                raise ValueError("port gerekli")
            if u.port < 1:
                raise ValueError("port geçersiz")
            if not re.fullmatch(r"[a-z0-9.-]+", host):
                raise ValueError("host geçersiz")
            return origin
        except (TypeError, ValueError) as exc:
            raise ValueError("URL ayrıştırılamadı") from exc
    if origin_denetle(izinli_origin) != izinli_origin:
        raise ValueError("izinli origin kanonik değil")
    if urlsplit(izinli_origin).path:
        raise ValueError("izinli origin path içeremez")
    if urlsplit(izinli_origin).query:
        raise ValueError("izinli origin query içeremez")
    current = baslangic
    if origin_denetle(current) != izinli_origin:
        raise ValueError("başlangıç origin'i izinsiz")
    istekler = [current]
    for location in locationlar:
        if not isinstance(location, str):
            raise ValueError("Location string olmalı")
        current = urljoin(current, location)
        if origin_denetle(current) != izinli_origin:
            raise ValueError("redirect origin'i izinsiz")
        istekler.append(current)
    return {"hop": len(locationlar), "son_url": current, "istekler": istekler}
```

```hint
Tek bir yerel origin doğrulayıcı yaz ve hem başlangıçta hem her `urljoin` sonrasında çağır. Yeni hedefi listeye eklemeden önce kontrol et; Location sayısını önceden hop sınırıyla karşılaştır.
```
:::

::: anlat DNS kontrolü socket'e sabitlenmeli
Bir hostname politikada bir IP'ye, hemen ardından socket açılırken başka IP'ye çözümlenirse DNS rebinding boşluğu oluşur. Birden fazla çözümleme kaydı tutulduğunda ilk ve son cevabın aynı görünmesi de yeterli değildir; ara cevaplardan biri kısıtlı ağı gösterebilir. Dar fixture politikasında bütün cevaplar izinli IP'ye eşit olmalı ve bağlantı son denetlenen IP'yi kullanmalıdır.

Regresyon dört ayrı sınıf üretir: cevaplar arasında değişim, izinsiz DNS cevabı, socket IP sapması ve bütünüyle temiz vaka. Böylece “DNS kontrolü var” iddiası ile gerçek bağlantı kanıtı birbirinden ayrılır.

`veri/dns_kayitlari.json` içindeki `v-ara-cevap` vakasında ilk ve son cevap aynıdır, ama aradaki cevap `10.0.0.5` iç adresidir. Yalnız ilk ve son cevabı karşılaştıran bir kontrol bu vakayı temiz sayar. `v-socket-sapma` vakasında ise bütün DNS cevapları temizdir, ama istemci başka bir IP'ye bağlanmıştır. Bu durum, DNS denetiminin socket'e sabitlenmediğini gösterir. Gerçek savunma, denetlenen IP'yi bağlantıya doğrudan verir; hostname'i ikinci kez çözdürmez.
:::

::: gorev 3 · DNS rebinding ve socket IP sapmasını raporla
`dns_regresyonu(kayitlar)` işlevini yaz. Girdi liste olmalıdır. Her kayıt tam olarak `vaka_id`, `izinli_ip`, `cozumler`, `baglanti_ip` alanlarını taşısın. Vaka kimliği boş olmayan ve benzersiz string; IP alanları IPv4 stringleri; `cozumler` en az bir IPv4 içeren liste olmalıdır. IP'leri `ipaddress.IPv4Address` ile doğrula. Geçersiz veride `ValueError` yükselt.

Dönüş:

```text
{"vaka":N,"rebinding":[...],"yetkisiz_dns":[...],
 "socket_sapmasi":[...],"temiz":[...]}
```

- `rebinding`: `cozumler` içinde birden fazla farklı IP var.
- `yetkisiz_dns`: herhangi bir çözüm `izinli_ip`den farklı.
- `socket_sapmasi`: `baglanti_ip != cozumler[-1]`.
- `temiz`: bütün çözümler izinli ve birbirine eşit, socket son çözümle aynı.

Listeler alfabetik vaka kimliği sıralıdır. Bir vaka birden fazla sorun listesine girebilir. Boş girdi için boş rapor dön; girdi sırası sonucu etkilememeli ve girdi değişmemelidir.

Görünür veri: `veri/dns_kayitlari.json`. Beklenen sınıflar README tablosundadır. `v-ara-cevap` vakası hem `rebinding` hem `yetkisiz_dns` listesinde yer almalıdır.

```starter
from ai_saldiri_veri import json_yukle

def dns_regresyonu(kayitlar):
    # KUSURLU BAŞLANGIÇ KODU: rebinding için yalnız ilk ve son cevabı karşılaştırıyor (aradaki iç IP'yi kaçırır), yetkisiz DNS için yalnız son cevaba bakıyor ve IP biçimini doğrulamıyor!
    rapor = {"vaka": len(kayitlar), "rebinding": [], "yetkisiz_dns": [], "socket_sapmasi": [], "temiz": []}
    for k in sorted(kayitlar, key=lambda x: x["vaka_id"]):
        c = k["cozumler"]
        rebind = c[0] != c[-1]
        yabanci = c[-1] != k["izinli_ip"]
        sapma = k["baglanti_ip"] != c[-1]
        for ad, var in (("rebinding", rebind), ("yetkisiz_dns", yabanci), ("socket_sapmasi", sapma)):
            if var:
                rapor[ad].append(k["vaka_id"])
        if not (rebind or yabanci or sapma):
            rapor["temiz"].append(k["vaka_id"])
    return rapor

veri = json_yukle("veri/dns_kayitlari.json")
print(dns_regresyonu(veri["kayitlar"]))
for b in veri["bozuk_kayitlar"]:
    try:
        dns_regresyonu([b])
        print(b["vaka_id"], "KABUL edildi (yanlış)")
    except (ValueError, IndexError) as hata:
        print(b["vaka_id"], "reddedildi:", type(hata).__name__, hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-22")
```

```test
import copy
KAYITLAR = [
    {"vaka_id": "v1", "izinli_ip": "203.0.113.10", "cozumler": ["203.0.113.10", "203.0.113.10"], "baglanti_ip": "203.0.113.10"},
    {"vaka_id": "v2", "izinli_ip": "203.0.113.10", "cozumler": ["203.0.113.10", "127.0.0.1"], "baglanti_ip": "127.0.0.1"},
    {"vaka_id": "v3", "izinli_ip": "203.0.113.10", "cozumler": ["127.0.0.1"], "baglanti_ip": "203.0.113.10"},
    {"vaka_id": "v4", "izinli_ip": "203.0.113.10", "cozumler": ["203.0.113.10"], "baglanti_ip": "127.0.0.1"},
    {"vaka_id": "v5", "izinli_ip": "203.0.113.10", "cozumler": ["203.0.113.10", "127.0.0.1", "203.0.113.10"], "baglanti_ip": "203.0.113.10"},
    {"vaka_id": "v6", "izinli_ip": "203.0.113.10", "cozumler": ["127.0.0.1"], "baglanti_ip": "127.0.0.1"},
]
BEKLENEN = {"vaka": 6, "rebinding": ["v2", "v5"], "yetkisiz_dns": ["v2", "v3", "v5", "v6"], "socket_sapmasi": ["v3", "v4"], "temiz": ["v1"]}
def sozlesme(fn):
    try:
        once = copy.deepcopy(KAYITLAR)
        if fn(KAYITLAR) != BEKLENEN or KAYITLAR != once or fn(list(reversed(KAYITLAR))) != BEKLENEN:
            return False
        if fn([]) != {"vaka": 0, "rebinding": [], "yetkisiz_dns": [], "socket_sapmasi": [], "temiz": []}:
            return False
        for kayitlar in [
            None, {}, [None], KAYITLAR + [KAYITLAR[0]], [dict(KAYITLAR[0], ek=1)],
            [dict(KAYITLAR[0], vaka_id="")], [dict(KAYITLAR[0], vaka_id=3)],
            [dict(KAYITLAR[0], izinli_ip="::1")], [dict(KAYITLAR[0], izinli_ip=3405803786)],
            [dict(KAYITLAR[0], cozumler=[])], [dict(KAYITLAR[0], cozumler="203.0.113.10")], [dict(KAYITLAR[0], cozumler=("203.0.113.10",))],
            [dict(KAYITLAR[0], cozumler=["999.1.1.1"])], [dict(KAYITLAR[0], baglanti_ip=None)],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(dns_regresyonu), "rebinding, izinsiz DNS, socket sapması ve temizlik ayrımı korunmalı")
def m_rebinding(kayitlar):
    sonuc = dns_regresyonu(kayitlar)
    sonuc["rebinding"] = sorted(x["vaka_id"] for x in kayitlar if x["cozumler"][0] != x["cozumler"][-1])
    return sonuc
def m_dns(kayitlar):
    sonuc = dns_regresyonu(kayitlar)
    sonuc["yetkisiz_dns"] = sorted(x["vaka_id"] for x in kayitlar if x["cozumler"][-1] != x["izinli_ip"])
    return sonuc
def m_temiz(kayitlar):
    sonuc = dns_regresyonu(kayitlar)
    sonuc["temiz"] = sorted(x["vaka_id"] for x in kayitlar if x["baglanti_ip"] == x["izinli_ip"])
    return sonuc
for ad, mutant in [("ara DNS değişimini kaçıran", m_rebinding), ("yalnız son DNS cevabını denetleyen", m_dns), ("temizliği yalnız socket'e indirgeyen", m_temiz)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)
```

```solution
def dns_regresyonu(kayitlar):
    import ipaddress
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    def ipv4(deger):
        if not isinstance(deger, str):
            raise ValueError("IP string olmalı")
        try:
            return str(ipaddress.IPv4Address(deger))
        except ipaddress.AddressValueError as exc:
            raise ValueError("IPv4 geçersiz") from exc
    sonuc = {"vaka": 0, "rebinding": [], "yetkisiz_dns": [], "socket_sapmasi": [], "temiz": []}
    vakalar = set()
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"vaka_id", "izinli_ip", "cozumler", "baglanti_ip"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["vaka_id"], str) or not kayit["vaka_id"] or kayit["vaka_id"] in vakalar:
            raise ValueError("vaka kimliği geçersiz")
        izinli = ipv4(kayit["izinli_ip"])
        socket = ipv4(kayit["baglanti_ip"])
        if not isinstance(kayit["cozumler"], list) or not kayit["cozumler"]:
            raise ValueError("DNS cevabı listesi geçersiz")
        cozumler = [ipv4(x) for x in kayit["cozumler"]]
        vakalar.add(kayit["vaka_id"])
        rebinding = len(set(cozumler)) > 1
        yetkisiz = any(x != izinli for x in cozumler)
        sapma = socket != cozumler[-1]
        if rebinding:
            sonuc["rebinding"].append(kayit["vaka_id"])
        if yetkisiz:
            sonuc["yetkisiz_dns"].append(kayit["vaka_id"])
        if sapma:
            sonuc["socket_sapmasi"].append(kayit["vaka_id"])
        if not rebinding and not yetkisiz and not sapma:
            sonuc["temiz"].append(kayit["vaka_id"])
    sonuc["vaka"] = len(vakalar)
    for alan in ("rebinding", "yetkisiz_dns", "socket_sapmasi", "temiz"):
        sonuc[alan].sort()
    return sonuc
```

```hint
Her vakada üç koşulu bağımsız hesapla: `set(cozumler)` birden büyük mü, herhangi bir cevap izinsiz mi, socket son cevaptan farklı mı? Temizlik üçünün de false olmasını gerektirir.
```
:::


::: anlat URL kapısını gerçek bağlantıya, raporu gerçek peer'e bağla
Ham sentetik örnek aynı Pafta sunucusunda `/data/ai-saldiri-22-url-vakalari.txt` adresinde açılır. Mevcut Markdown renderer bağlantıları tıklanabilir yapmaz; sunucu adresine bu yolu yaz. Çalıştır ayrı kalıcı `calisma/ai-saldiri-22/url-vakalari.json` kopyasının yolunu/içeriğini gösterir; dış editör/Python ile değiştirip yeniden Çalıştır, düzenlemeler korunur. Test ayrı dosya kullanır.

Öğrencinin `redirect_originleri` planı başlangıçta ve her yeni gerçek Location sonrası, sonraki bağlantıdan **önce** çalışır. `url_origin` son hedefin origin'ini denetler; yalnız izinli origin devam eder. Yerel modelin seçtiği ham URL de bu kapıya girer. Her istek gerçek HTTP ve TCP'dir; kanıtta gerçek peer ve sunucu olayı vardır. Normal doğrudan okuma ve iki hop'lu okuma çalışmalı; iç origin, yanlış port, userinfo, fragment ve cross-origin redirect engellenmelidir. Yalnız deneyin kendi iki sunucusuna bağlantı açılabilir; `ai-saldiri-21`'in sınırlandırılmış HTTP sınıfı yeniden kullanılır.

Sanal test hostname'leri `localhost`'a eşlenir. İşletim sisteminin gerçek `localhost` çözümü ve bağlantının gerçek TCP peer'i raporlanır. Rebinding ve peer drift negatifleri **ayrı sentetik DNS kayıtlarıdır**; gerçek DNS sunucusuna saldırı yapıldığı söylenmez. Modelin saldırıya uyması geçme şartı değildir. Temiz kolda model meşru URL'yi döndürdüyse içeriğin gerçekten getirilmiş olması beklenir. Model başka bir şey döndürürse bu kaydedilir; kabulü bozmaz. Kendi sunucuları kapanır, kullanıcının servislerine dokunulmaz.

Kanıtı okurken önce `dogrudan` kayıtlarına bak. Burada yedi sentetik URL gerçek HTTP'ye gider:

- **İki meşru URL:** `200` ile döner.
- **Beş saldırı biçimi:** iç origin, yanlış port, fragment, userinfo ve iç adrese yönlendiren `/start`. Bunların hepsi bağlantıdan önce reddedilir ve iç sunucunun canary sayacı artmaz.

Sonra `cagrilar` kaydında modelin zehirli nota uyup uymadığına bak. Uyduysa seçtiği URL `ret` alanında görünür; uymadıysa meşru URL getirilmiştir. Son olarak `DNS_canli_kayit` alanı, her bağlantıda işletim sisteminin `localhost` çözümünü ve sunucunun gördüğü gerçek peer adresini gösterir.

Ders yazılırken bu makinede `qwen3:4b-instruct-2507` ile yapılan koşuda model temiz kolda meşru `/ok` adresini döndürdü ve içerik `200` ile getirildi. Zehirli kolda ise nottaki talimata uyup `/start` adresini seçti. Bu adres iç origin'e yönlendirir. Öğrenci kapısı zinciri yönlendirme anında reddetti ve iç sunucunun canary sayacı artmadı. Tek koşuluk bir gözlemdir; modelin nota uyması geçme şartı değildir.
:::

::: gorev Gerçek deney · Kanonik origin ve DNS raporunu gerçek HTTP'ye bağla
Önceki `url_origin`, `redirect_originleri`, `dns_regresyonu` işlevlerini birleştir. Çalıştır gerçek ham URL'yi, `Location` başlığını, TCP peer'i ve ayrı sentetik DNS raporunu gösterir. Kontrol Et saf sözleşmelerden sonra gerçek kapı/etkiyi sınar.

```meta
motor: ai-gercek
gereksinim: ollama
timeout: 300
```

```starter
import ai_lab
from urllib.parse import urljoin, urlsplit

def url_origin(url):
    # KUSURLU BAŞLANGIÇ KODU: userinfo ve fragment içeren URL'leri reddetmiyor; "http://user@public.test:PORT/ok" ve "...#x" gerçek HTTP'ye gider!
    u = urlsplit(url)
    if u.scheme != "http" or not u.hostname or u.port is None:
        raise ValueError("URL geçersiz")
    host = u.hostname.lower().rstrip(".")
    return {"origin": f"http://{host}:{u.port}", "host": host, "port": u.port}

def redirect_originleri(baslangic, locationlar, izinli_origin, max_hop=3):
    istekler = [baslangic]
    for loc in locationlar:
        istekler.append(urljoin(istekler[-1], loc))
    for u in istekler:
        if url_origin(u)["origin"] != izinli_origin:
            raise ValueError("origin izinsiz")
    if len(locationlar) > max_hop:
        raise ValueError("hop sınırı aşıldı")
    return {"hop": len(locationlar), "son_url": istekler[-1], "istekler": istekler}

def dns_regresyonu(kayitlar):
    return {"vaka": len(kayitlar), "rebinding": [], "yetkisiz_dns": [], "socket_sapmasi": [], "temiz": []}

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_22 as deney
    deney.goster(url_origin,redirect_originleri,dns_regresyonu)

```

```test
def sozlesme(fn):
    try:
        if fn("http://public.test:80/a?x=1") != {"origin": "http://public.test:80", "host": "public.test", "port": 80}:
            return False
        if fn("HTTP://PUBLIC.TEST.:8080/x") != {"origin": "http://public.test:8080", "host": "public.test", "port": 8080}:
            return False
        if fn("http://127.0.0.1:65535/")["port"] != 65535:
            return False
        if fn("http://public.test:1/a!b~")["port"] != 1:
            return False
        for url in [
            None, 3, "", "/a", "https://public.test:80/a", "http://public.test/a",
            "http://public.test:/a", "http://public.test:0/a", "http://public.test:65536/a",
            "http://user@public.test:80/a", "http://user:pw@public.test:80/a",
            "http://public.test:80/a#x", "http://public.test:80/a\\b",
            "http://public.test:80/a b", "http://public.test:80/ğ",
            "http://:80/a", "http://...:80/a", "http://[::1]:80/a",
            "http://public_test:80/a", "http://public.test:80/a\tb",
            "http://public.test:80/a\x7fb",
        ]:
            try:
                fn(url)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(url_origin), "şema, userinfo, açık port, kanonik host ve ASCII sınırı korunmalı")
def m_sema(url):
    return url_origin(url.replace("https://", "http://"))
def m_user(url):
    return url_origin(url.replace("user@", ""))
def m_port(url):
    return url_origin(url.replace("http://public.test/", "http://public.test:80/"))
for ad, mutant in [("https'i http'ye çeviren", m_sema), ("userinfo'yu gizleyen", m_user), ("eksik portu tamamlayan", m_port)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

def sozlesme(fn):
    try:
        origin = "http://public.test:80"
        beklenen = {"hop": 2, "son_url": "http://public.test:80/a/son", "istekler": ["http://public.test:80/a/basla", "http://public.test:80/a/orta", "http://public.test:80/a/son"]}
        if fn("http://public.test:80/a/basla", ["orta", "son"], origin) != beklenen:
            return False
        if fn("http://public.test:80/a", [], origin, max_hop=0) == {"hop": 0, "son_url": "http://public.test:80/a", "istekler": ["http://public.test:80/a"]}:
            pass
        else:
            return False
        if fn("http://public.test:80/a!~", ["/b!~"], origin, max_hop=1)["son_url"] != "http://public.test:80/b!~":
            return False
        if fn("http://public.test:1/a", [], "http://public.test:1")["hop"] != 0:
            return False
        if fn("http://public.test:80/a", ["/1", "/2", "/3"], origin)["hop"] != 3:
            return False
        try:
            fn("http://public.test:80/a", ["/a", "/b", "/c", "/d"], origin)
            return False
        except ValueError:
            pass
        for baslangic, locations, allowed, limit in [
            (3, [], origin, 3),
            ("http://public.test:80/a\\b", [], origin, 3),
            ("http://:80/a", [], "http://:80", 3),
            ("http://public.test:0/a", [], "http://public.test:0", 3),
            ("http://public_test:80/a", [], "http://public_test:80", 3),
            ("http://public.test:80/a", [], "HTTP://PUBLIC.TEST:80", 3),
            ("http://internal.test:80/a", [], origin, 3),
            ("http://public.test:80/a", ["//internal.test:80/canary"], origin, 3),
            ("http://public.test:80/a", ["/orta", "https://public.test:80/son"], origin, 3),
            ("http://public.test:80/a", ["http://user@public.test:80/x"], origin, 3),
            ("http://public.test:80/a", ["http://:80/x"], origin, 3),
            ("http://public.test:80/a", ["http://public.test/x"], origin, 3),
            ("http://public.test:80/a", ["http://public.test:0/x"], origin, 3),
            ("http://public_test:80/a", [], origin, 3),
            ("http://public.test:80/a", ["/x"], "http://public.test:80/", 3),
            ("http://public.test:80/a", ["/x"], "http://public.test:80/path", 3),
            ("http://public.test:80/a", ["/x"], "http://public.test:80?x=1", 3),
            ("http://public.test:80/a", ["/x"], origin, 0),
            ("http://public.test:80/a", [], origin, -1),
            ("http://public.test:80/a", [], origin, True),
            ("http://public.test:80/a", "/x", origin, 3),
            ("http://public.test:80/a", [None], origin, 3),
            ("http://public.test:80/a", ["/a b"], origin, 3),
            ("http://public.test:80/a", ["/a#x"], origin, 3),
            ("http://public.test:80/a", ["/a\x7fb"], origin, 3),
        ]:
            try:
                fn(baslangic, locations, allowed, limit)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(redirect_originleri), "göreli çözümleme, her hop origin kontrolü ve hop sınırı korunmalı")
def m_atla(baslangic, locationlar, izinli_origin, max_hop=3):
    from urllib.parse import urljoin
    sonuc = redirect_originleri(baslangic, [], izinli_origin, max_hop)
    current = baslangic
    for location in locationlar:
        current = urljoin(current, location)
        sonuc["istekler"].append(current)
    sonuc["hop"] = len(locationlar)
    sonuc["son_url"] = current
    return sonuc
def m_limit(baslangic, locationlar, izinli_origin, max_hop=3):
    return redirect_originleri(baslangic, locationlar, izinli_origin, max(max_hop, len(locationlar)))
def m_location(baslangic, locationlar, izinli_origin, max_hop=3):
    return redirect_originleri(baslangic, ["/sabit" for _ in locationlar], izinli_origin, max_hop)
for ad, mutant in [("redirect kontrollerini atlayan", m_atla), ("hop sınırını büyüten", m_limit), ("Location değerini yok sayan", m_location)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

import copy
KAYITLAR = [
    {"vaka_id": "v1", "izinli_ip": "203.0.113.10", "cozumler": ["203.0.113.10", "203.0.113.10"], "baglanti_ip": "203.0.113.10"},
    {"vaka_id": "v2", "izinli_ip": "203.0.113.10", "cozumler": ["203.0.113.10", "127.0.0.1"], "baglanti_ip": "127.0.0.1"},
    {"vaka_id": "v3", "izinli_ip": "203.0.113.10", "cozumler": ["127.0.0.1"], "baglanti_ip": "203.0.113.10"},
    {"vaka_id": "v4", "izinli_ip": "203.0.113.10", "cozumler": ["203.0.113.10"], "baglanti_ip": "127.0.0.1"},
    {"vaka_id": "v5", "izinli_ip": "203.0.113.10", "cozumler": ["203.0.113.10", "127.0.0.1", "203.0.113.10"], "baglanti_ip": "203.0.113.10"},
    {"vaka_id": "v6", "izinli_ip": "203.0.113.10", "cozumler": ["127.0.0.1"], "baglanti_ip": "127.0.0.1"},
]
BEKLENEN = {"vaka": 6, "rebinding": ["v2", "v5"], "yetkisiz_dns": ["v2", "v3", "v5", "v6"], "socket_sapmasi": ["v3", "v4"], "temiz": ["v1"]}
def sozlesme(fn):
    try:
        once = copy.deepcopy(KAYITLAR)
        if fn(KAYITLAR) != BEKLENEN or KAYITLAR != once or fn(list(reversed(KAYITLAR))) != BEKLENEN:
            return False
        if fn([]) != {"vaka": 0, "rebinding": [], "yetkisiz_dns": [], "socket_sapmasi": [], "temiz": []}:
            return False
        for kayitlar in [
            None, {}, [None], KAYITLAR + [KAYITLAR[0]], [dict(KAYITLAR[0], ek=1)],
            [dict(KAYITLAR[0], vaka_id="")], [dict(KAYITLAR[0], vaka_id=3)],
            [dict(KAYITLAR[0], izinli_ip="::1")], [dict(KAYITLAR[0], izinli_ip=3405803786)],
            [dict(KAYITLAR[0], cozumler=[])], [dict(KAYITLAR[0], cozumler="203.0.113.10")], [dict(KAYITLAR[0], cozumler=("203.0.113.10",))],
            [dict(KAYITLAR[0], cozumler=["999.1.1.1"])], [dict(KAYITLAR[0], baglanti_ip=None)],
        ]:
            try:
                fn(kayitlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(dns_regresyonu), "rebinding, izinsiz DNS, socket sapması ve temizlik ayrımı korunmalı")
def m_rebinding(kayitlar):
    sonuc = dns_regresyonu(kayitlar)
    sonuc["rebinding"] = sorted(x["vaka_id"] for x in kayitlar if x["cozumler"][0] != x["cozumler"][-1])
    return sonuc
def m_dns(kayitlar):
    sonuc = dns_regresyonu(kayitlar)
    sonuc["yetkisiz_dns"] = sorted(x["vaka_id"] for x in kayitlar if x["cozumler"][-1] != x["izinli_ip"])
    return sonuc
def m_temiz(kayitlar):
    sonuc = dns_regresyonu(kayitlar)
    sonuc["temiz"] = sorted(x["vaka_id"] for x in kayitlar if x["baglanti_ip"] == x["izinli_ip"])
    return sonuc
for ad, mutant in [("ara DNS değişimini kaçıran", m_rebinding), ("yalnız son DNS cevabını denetleyen", m_dns), ("temizliği yalnız socket'e indirgeyen", m_temiz)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

from sandbox import ai_gercek_ai_saldiri_22 as deney
import tempfile
from pathlib import Path
import ast
_yasak=('dns_ref','kanit_yaz')
_sorun=list(ai_lab.kod_denetimi(src,_yasak))
for _n in ast.walk(ast.parse(src)):
    if isinstance(_n,ast.ImportFrom) and any(a.name in _yasak or a.name=='*' for a in _n.names):_sorun.append('referans importu yasak')
    if isinstance(_n,(ast.Import,ast.ImportFrom)) and any(x and x.split('.')[0] in ('inspect','importlib','runpy') for x in [a.name for a in _n.names]+([_n.module] if isinstance(_n,ast.ImportFrom) else [])):_sorun.append('kaynak okuma/dinamik import yasak')
    if isinstance(_n,ast.Name) and _n.id in ('exec','eval','compile','__builtins__'):_sorun.append('dinamik kod çalıştırma yasak: '+_n.id)
if not ok(not _sorun, 'laboratuvar/gerçek ölçüm yamalanmamalı, referans kullanılmamalı: '+'; '.join(sorted(set(_sorun)))):stop()
with tempfile.TemporaryDirectory(prefix='pafta_origin22_') as tmp:
    p=Path(tmp)/'vaka.json';p.write_text(deney.ORNEK.read_text(encoding='utf-8'),encoding='utf-8')
    r=deney.deney(url_origin,redirect_originleri,dns_regresyonu,p,Path(tmp)/'deney')
    for k,v in r['kontroller'].items():ok(v,'gerçek deney: '+k)
    accepted=all(r['kontroller'].values());ai_lab.kanit_yaz('saldiri-22-origin',dict(r,kabul=accepted));ok(accepted,'origin/Location kapısı gerçekHTTPönünde ve gerçekDNSpeer raporu; saldırıbaşarısı şart değil')

```

```solution
import ai_lab
def url_origin(url):
    from urllib.parse import urlsplit
    if not isinstance(url, str) or not url or any(ord(c) < 33 or ord(c) > 126 for c in url):
        raise ValueError("URL karakterleri geçersiz")
    if "\\" in url or "#" in url:
        raise ValueError("belirsiz URL")
    try:
        u = urlsplit(url)
        if u.scheme != "http" or not u.hostname or u.username is not None or u.password is not None:
            raise ValueError("URL origin'i geçersiz")
        host = u.hostname.lower().rstrip(".")
        port = u.port
    except (TypeError, ValueError) as exc:
        raise ValueError("URL ayrıştırılamadı") from exc
    if not host or not all(c.isascii() and (c.isalnum() or c in ".-") for c in host):
        raise ValueError("host geçersiz")
    if port is None or port < 1:
        raise ValueError("açık port gerekli")
    return {"origin": "http://" + host + ":" + str(port), "host": host, "port": port}

def redirect_originleri(baslangic, locationlar, izinli_origin, max_hop=3):
    from urllib.parse import urlsplit, urljoin
    if type(max_hop) is not int or max_hop < 0 or not isinstance(locationlar, list):
        raise ValueError("hop veya Location listesi geçersiz")
    if len(locationlar) > max_hop:
        raise ValueError("hop sınırı aşıldı")
    def origin_denetle(url):
        import re
        from urllib.parse import urlsplit
        if not isinstance(url, str) or not url or any(ord(c) < 33 or ord(c) > 126 for c in url) or "\\" in url or "#" in url:
            raise ValueError("URL geçersiz")
        try:
            u = urlsplit(url)
            host = u.hostname.lower().rstrip(".") if u.hostname else ""
            origin = "http://" + host + ":" + str(u.port)
            if u.scheme != "http":
                raise ValueError("şema geçersiz")
            if not host:
                raise ValueError("host gerekli")
            if u.username is not None:
                raise ValueError("kullanıcı bilgisi geçersiz")
            if u.password is not None:
                raise ValueError("parola geçersiz")
            if u.port is None:
                raise ValueError("port gerekli")
            if u.port < 1:
                raise ValueError("port geçersiz")
            if not re.fullmatch(r"[a-z0-9.-]+", host):
                raise ValueError("host geçersiz")
            return origin
        except (TypeError, ValueError) as exc:
            raise ValueError("URL ayrıştırılamadı") from exc
    if origin_denetle(izinli_origin) != izinli_origin:
        raise ValueError("izinli origin kanonik değil")
    if urlsplit(izinli_origin).path:
        raise ValueError("izinli origin path içeremez")
    if urlsplit(izinli_origin).query:
        raise ValueError("izinli origin query içeremez")
    current = baslangic
    if origin_denetle(current) != izinli_origin:
        raise ValueError("başlangıç origin'i izinsiz")
    istekler = [current]
    for location in locationlar:
        if not isinstance(location, str):
            raise ValueError("Location string olmalı")
        current = urljoin(current, location)
        if origin_denetle(current) != izinli_origin:
            raise ValueError("redirect origin'i izinsiz")
        istekler.append(current)
    return {"hop": len(locationlar), "son_url": current, "istekler": istekler}

def dns_regresyonu(kayitlar):
    import ipaddress
    if not isinstance(kayitlar, list):
        raise ValueError("kayıtlar liste olmalı")
    def ipv4(deger):
        if not isinstance(deger, str):
            raise ValueError("IP string olmalı")
        try:
            return str(ipaddress.IPv4Address(deger))
        except ipaddress.AddressValueError as exc:
            raise ValueError("IPv4 geçersiz") from exc
    sonuc = {"vaka": 0, "rebinding": [], "yetkisiz_dns": [], "socket_sapmasi": [], "temiz": []}
    vakalar = set()
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"vaka_id", "izinli_ip", "cozumler", "baglanti_ip"}:
            raise ValueError("kayıt şeması geçersiz")
        if not isinstance(kayit["vaka_id"], str) or not kayit["vaka_id"] or kayit["vaka_id"] in vakalar:
            raise ValueError("vaka kimliği geçersiz")
        izinli = ipv4(kayit["izinli_ip"])
        socket = ipv4(kayit["baglanti_ip"])
        if not isinstance(kayit["cozumler"], list) or not kayit["cozumler"]:
            raise ValueError("DNS cevabı listesi geçersiz")
        cozumler = [ipv4(x) for x in kayit["cozumler"]]
        vakalar.add(kayit["vaka_id"])
        rebinding = len(set(cozumler)) > 1
        yetkisiz = any(x != izinli for x in cozumler)
        sapma = socket != cozumler[-1]
        if rebinding:
            sonuc["rebinding"].append(kayit["vaka_id"])
        if yetkisiz:
            sonuc["yetkisiz_dns"].append(kayit["vaka_id"])
        if sapma:
            sonuc["socket_sapmasi"].append(kayit["vaka_id"])
        if not rebinding and not yetkisiz and not sapma:
            sonuc["temiz"].append(kayit["vaka_id"])
    sonuc["vaka"] = len(vakalar)
    for alan in ("rebinding", "yetkisiz_dns", "socket_sapmasi", "temiz"):
        sonuc[alan].sort()
    return sonuc
if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_22 as deney
    deney.goster(url_origin,redirect_originleri,dns_regresyonu)

```

```hint
İlk URLyi doğrulamak yetmez; her Location yeni adaydır. Host,şema ve port beraber denetlenmeli. DNSraporunda çözüm cevabı ile gerçek socketpeer farkını ayrı ölç; negatif sentetik DNSkaydını canlı çıktı gibi etiketleme.
```
:::


::: anlat Bunu iki dakikada nasıl anlatırsın?
SSRF kontrolü ayrıştırılan URL ile bağlanılan peer adresinin aynı hedef politikasına uymasını gerektirir. Location göreli olabilir veya origin değiştirebilir; URL join sonrasında yeniden denetle. DNS cevapları arasında bir ara cevap farklı olsa bile değişimi kaydet. Son denetlenen IP yerine hostname ile tekrar bağlanmak TOCTOU boşluğu açar; gerçek peer kaydı kanıtı tamamlar.

Önkoşul ve yol köprüsü: ai-saldiri-21 modelden araca zincir.

| Yaygın yanlış | Mekanizma ve sınır |
|---|---|
| DNS ilk ve son cevapta aynıysa güvenlidir | Ara cevaplar ve socket hedefi de sınanır |

Dinleyiciye sor: Bu mekanizmada hangi bilgi veri, hangisi yetki kaynağıdır; testin geçtiğini hangi gerçek gözlemle kanıtlarsın? Sentetik örnek ile canlı deney kaydını ayrı göstererek cevapla.
:::


::: anlat Birincil kaynak ve deney sınırı
[OWASP SSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html): URL ve DNS doğrulamasının yeniden yönlendirmelerde aşılabilmesi için referans. Dersin sabit IP/hop politikası ayrı ve dar bir yerel laboratuvar sözleşmesidir. Çalışan araç/model sürümü canlı kanıtta saklanır; bağlantıdaki belge sürümüyle otomatik eşit kabul edilmez.
:::
