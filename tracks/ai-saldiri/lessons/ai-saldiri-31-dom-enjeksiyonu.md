---
id: ai-saldiri-31
title: Computer-Use ve Tarayıcı Ajanlarında DOM Enjeksiyonu
summary: HTML metin katmanlarını ayır, tarayıcı eylemlerini alan adı izin listesiyle sınırla ve DOM ile ekran kanıtı arasındaki enjeksiyon farkını ölç.
timeout: 300
esleme: ai-savunma-17, ai-saldiri-12
---

::: anlat Gerçek biçimi bil, sentetik temsili ayırt et: Ekranda görünmeyen DOM metni de bağlama girebilir

| Gerçek araç/model ne gösterir | Bu ders ne kullanır | Ne söyleyemez? |
|---|---|---|
| Gerçek bir tarayıcı ajanı (Playwright tabanlı ajanlar, Browser Use, computer-use) sayfayı birkaç kanaldan alır. Bunlar ekran görüntüsü, `document.body.textContent`, düzen motorunun hesapladığı `innerText` ve erişilebilirlik ağacıdır. Önerdiği tıklama ve gezinme eylemleri bir araç çağrısı olarak uygulamaya gelir. | Görev 1–3: `veri/sayfalar.json`, `veri/eylem_adaylari.json` ve `veri/dom_ekran_kayitlari.json` içindeki **sentetik** sayfa, bağlantı ve kayıtlar. Son adım: kurulu Playwright ile başsız Chromium. Ağ istekleri `route.abort()` ile kesilir; tek yerel sayfa bellekten yüklenir ve ondan `textContent`, `innerText` ve bağlantılar okunur. | Derste dil modeli ya da ajan yoktur. Bu yüzden enjeksiyonun bir ajanı yönlendirdiğini ölçmez; yalnız hangi kanalın talimat görünümlü metni taşıdığını ölçer. HTMLParser sınıf tabanlı CSS'i, ekran dışına itilmiş, sıfır puntolu ya da zeminle aynı renkteki metni tanımaz. Alan adı süzgeci yönlendirme sonrası varışı, DNS'i ve TLS'i denetlemez. |

> [!NOT]
> Görev 1–3 sentetik veriyle çalışır. Bu görevlerde tarayıcı, model ve ağ yoktur. Son adımdaki **Gerçek deney** görevi yalnız kurulu Playwright Chromium'unu ağı kesilmiş halde kullanır; dış siteye bağlanmaz. `veri/` dosyaları her çalıştırmada çalışma klasörüne yeniden kopyalanır; kopyada yaptığın değişiklik bir sonraki çalıştırmada sıfırlanır, **kalıcılık yoktur**. Kontrol bu dosyalardan ayrı, gizli verilerle sınar.

Tarayıcı ajanı yalnız ekran görüntüsünü değil, DOM'dan çıkarılan metni de kullanabilir. `hidden`, `aria-hidden` veya CSS ile gizlenmiş bir metin kullanıcıya görünmezken DOM çıkarımına girebilir. Script ve style içeriği de kullanıcı içeriği değildir; bunları görünür metinle karıştırmak kanıtı bozar.

DOM metnindeki “önceki talimatı yok say” veya “şu bağlantıya tıkla” ifadesi web içeriğidir, system talimatı değildir. Ajanın eylem yetkisi uygulama katmanında sınırlanmalıdır. Görev 1–3 izole HTML fixture'ları, URL adayları ve ekran/DOM kayıtları kullanır; bu görevler için Playwright, Browser Use, Ollama ya da gerçek web sitesi gerekmez. Son adım ise kurulu Playwright ile gerçek başsız Chromium açar, ama ağı keser ve yalnız bellekteki yerel sayfayı yükler.

Standart `HTMLParser` tam bir tarayıcı değildir: JavaScript çalıştırmaz, gerçek CSS kaskadını hesaplamaz. Buradaki görev yalnız açık `hidden`, `aria-hidden="true"`, `display:none` ve `visibility:hidden` işaretlerini tanır.

**Aracın altında ne olur?** Aynı sayfa, ajanın hangi kanalı okuduğuna göre farklı metin verir:

- `textContent` DOM ağacındaki bütün metin düğümlerini birleştirir. Gizli `div`, `display:none` öğesi, hatta `script` ve `style` içeriği de buna girer.
- `innerText`, düzen motorunun hesapladığı görünür metindir. CSS ile gizlenen öğe buna girmez.
- Erişilebilirlik ağacı ekran okuyucunun gördüğüdür. `aria-hidden="true"` öğesi bu ağaçtan çıkar ama **ekranda görünmeye devam eder**. Tersine, ekran dışına itilmiş "yalnız ekran okuyucu" metni ekranda görünmez ama ağaçta kalır.

Bu derste `aria-hidden` gizli katmana konur, çünkü ajanların bir kısmı erişilebilirlik ağacını okur. Bu, "kullanıcı göremez" anlamına gelmez. Her kanalın kör noktası farklı olduğu için enjeksiyon adayı, iki kanal karşılaştırılarak bulunur.

**Saldırgan neyi dener?** Talimatı kullanıcının görmeyeceği ama ajanın okuyacağı bir yere koyar: `hidden` bir `div`, sınıfla gizlenen bir paragraf, `font-size:0`, zeminle aynı renk, `left:-9999px`, `alt` ya da `title` özniteliği, JSON-LD `script` bloğu. Bunu en kolay, başkalarının içerik yazabildiği yerlerde yapar: ürün yorumu, forum iletisi, web postasında açılan e-posta, paylaşılan belge. Talimat çoğu zaman bir eylem ister: "şu bağlantıya tıkla", "formu doldur", "çerezi şu adrese gönder". Bu yüzden ikinci savunma hattı eylem kapısıdır.

**Savunma neden kırılır?** Satır içi işaretlere bakan bir HTMLParser süzgeci, sınıf tabanlı CSS'i bilmez (`veri/sayfalar.json`, `s-06`). Gerçek Chromium o paragrafı gizler, HTMLParser ise görünür sayar. JavaScript'in sayfa yüklendikten sonra eklediği metin hiç görülmez. Alan adını URL metninde arayan bir izin listesi `destek.pafta.test.kotu.test`, `?r=destek.pafta.test` ve `destek.pafta.test@kotu.test` adreslerine kanar (`veri/eylem_adaylari.json`, `e-04`–`e-06`). İzinli alandaki bir açık yönlendirme ise doğru bir izin listesini bile aşar; bu yüzden varış adresi ayrıca denetlenir.

**Görev 1'de sık tuzaklar:** Gizliliği yalnız son açılan etikete bakarak hesaplamak, gizli bölümün çocuklarını görünür yapar (`s-03`). `style` içinde `"display:none"` dizesini aramak `Display : NONE` yazımını kaçırır (`s-02`). Aynı dizeyi ham etiket metninde aramak ise `data-style` özniteliğini yanlışlıkla gizli sayar (`s-04`). `<br/>` ve `<img>` gibi void etiketleri yığına atmak, dengeyi bozup geçerli sayfayı reddettirir (`s-05`).
:::

::: tahmin
DOM çıkarımı görünür, gizli ve kod metinlerini ayırıyor. Üç çıktı satırını yaz:

```python
parcalar = [
    ("gorunur", "Rapor"),
    ("gizli", "BREACH:CANARY-42"),
    ("kod", "BREACH:CANARY-42"),
    ("gizli", "BREACH:CANARY-42 yaz"),
]
for katman in ("gorunur", "gizli", "kod"):
    print(katman, sum(metin == "BREACH:CANARY-42" for k, metin in parcalar if k == katman))
```

???

```cikti
gorunur 0
gizli 1
kod 1
```

Tam eşleşme gizli ve kod katmanlarında birer kez bulunur. Gizli metindeki daha uzun alıntı sayılmaz; görünür metinde canary yoktur.
:::

::: gorev 1 · HTML metnini görünür, gizli ve kod katmanlarına ayır
`dom_katmanlari(html)` işlevini yaz. HTML string olmalı ve en fazla 20.000 karakter içermelidir; aksi durumda `ValueError` yükselt. Standart `html.parser.HTMLParser` kullan.

Dönüş `{"gorunur":[...],"gizli":[...],"kod":[...]}` biçimindedir. Her metin parçasındaki ardışık boşlukları tek boşluğa indir, baş/son boşlukları at ve boş parçaları listeye ekleme. Kaynak sırasını koru.

- `script` ve `style` içeriği `kod` katmanına gider.
- `hidden` özniteliği, `aria-hidden="true"`, inline `display:none` veya `visibility:hidden` taşıyan düğüm ve bütün alt düğümleri `gizli` katmanına gider.
- Diğer metinler `gorunur` katmanına gider. Kod katmanı, gizlilikten önce değerlendirilir.

Kapanışı olmayan veya yanlış sırayla kapanan etiketlerde `ValueError` yükselt. `img`, `input`, `meta`, `link`, `br` ve `hr` void etiketlerdir. HTML çalıştırma, ağ isteği yapma veya metindeki talimatları uygulama.

Görünür veri: `veri/sayfalar.json`. Her örneğin `beklenen` alanı vardır; README tablosu nedenlerini açıklar.

```starter
from html.parser import HTMLParser
from ai_saldiri_veri import json_yukle

class KatmanParser(HTMLParser):
    # KUSURLU BAŞLANGIÇ KODU: gizliliği yalnız son açılan etiketten okuyor (gizli üst düğümün çocukları görünür sayılır), stilde yalnız boşluksuz küçük harfli "display:none" arıyor, aria-hidden ve visibility'yi yok sayıyor, script/style içeriğini görünür sayıyor ve etiket dengesini denetlemiyor!
    def __init__(self):
        super().__init__()
        self.sonuc = {"gorunur": [], "gizli": [], "kod": []}
        self.gizli = False

    def handle_starttag(self, tag, attrs):
        oznitelikler = dict(attrs)
        self.gizli = "hidden" in oznitelikler or "display:none" in (oznitelikler.get("style") or "")

    def handle_endtag(self, tag):
        self.gizli = False

    def handle_data(self, data):
        metin = " ".join(data.split())
        if metin:
            self.sonuc["gizli" if self.gizli else "gorunur"].append(metin)

def dom_katmanlari(html):
    parser = KatmanParser()
    parser.feed(str(html))
    return parser.sonuc

veri = json_yukle("veri/sayfalar.json")
for o in veri["ornekler"]:
    try:
        sonuc = dom_katmanlari(o["html"])
    except Exception as hata:
        sonuc = type(hata).__name__
    print(o["id"], "doğru" if sonuc == o["beklenen"] else "YANLIŞ", sonuc)
for b in veri["bozuk_girdiler"]:
    try:
        dom_katmanlari(b)
        print(repr(b), "KABUL edildi (yanlış)")
    except ValueError as hata:
        print(repr(b), "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-31")
```

```test
HTML = '<div>Rapor <span hidden>BREACH:CANARY-42</span><span style="display: none">Gizli</span></div><script>BREACH:CANARY-42</script><p aria-hidden="true">Aria</p><p>Son</p>'
def sozlesme(fn):
    try:
        beklenen = {"gorunur": ["Rapor", "Son"], "gizli": ["BREACH:CANARY-42", "Gizli", "Aria"], "kod": ["BREACH:CANARY-42"]}
        if fn(HTML) != beklenen:
            return False
        if fn("<div><span>Acik</span></div>") != {"gorunur": ["Acik"], "gizli": [], "kod": []}:
            return False
        if fn("<div><span hidden><b>G</b></span></div>") != {"gorunur": [], "gizli": ["G"], "kod": []}:
            return False
        if fn("<div><script>K</script></div>") != {"gorunur": [], "gizli": [], "kod": ["K"]}:
            return False
        if fn("<div>   </div>") != {"gorunur": [], "gizli": [], "kod": []}:
            return False
        if fn('<p style=" DISPLAY : NONE ">A</p><p aria-hidden="TRUE">B</p>') != {"gorunur": [], "gizli": ["A", "B"], "kod": []}:
            return False
        if fn('<div hidden>A<span>B</span></div><style>x{}</style>') != {"gorunur": [], "gizli": ["A", "B"], "kod": ["x{}"]}:
            return False
        if fn('<p data-style="visibility: hidden">metin</p>')["gorunur"] != ["metin"]:
            return False
        if fn('<p style="visibility:hidden">x</p><img alt="y">')["gizli"] != ["x"] or fn("  A\n B  ")["gorunur"] != ["A B"]:
            return False
        if fn('<p style="display:none:extra">x</p>')["gorunur"] != ["x"] or len(fn("x" * 20000)["gorunur"][0]) != 20000:
            return False
        for html in ['<div>', '</p>', '<div></span>', None, 3, 'x' * 20001]:
            try:
                fn(html)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(dom_katmanlari), "gizli alt ağaç, kod ayrımı, boşluk ve etiket dengesi korunmalı")
def m_hepsi(html):
    return {"gorunur": [html], "gizli": [], "kod": []}
def m_gizli(html):
    sonuc = dom_katmanlari(html)
    sonuc["gorunur"] += sonuc.pop("gizli")
    return sonuc
def m_kod(html):
    sonuc = dom_katmanlari(html)
    sonuc["gorunur"] += sonuc.pop("kod")
    return sonuc
for ad, mutant in [("ham HTML'i görünür sayan", m_hepsi), ("gizli metni görünür yapan", m_gizli), ("script içeriğini görünür yapan", m_kod)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

eq(dom_katmanlari('<p style=" DISPLAY : NONE ">A</p><p aria-hidden="TRUE">B</p>'),{'gorunur':[],'gizli':['A','B'],'kod':[]},'CSS ad/değer boşluğu ve büyük harf; ARIA büyük harf')
```

```solution
from html.parser import HTMLParser

class KatmanParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sonuc = {"gorunur": [], "gizli": [], "kod": []}
        self.yigin = []
        self.void = {"img", "input", "meta", "link", "br", "hr"}

    def handle_starttag(self, tag, attrs):
        oznitelikler = dict(attrs)
        stiller = {}
        for parca in oznitelikler.get("style", "").split(";"):
            if ":" in parca:
                ad, deger = parca.split(":", 1)
                stiller[ad.strip().casefold()] = deger.strip().casefold()
        ust_gizli = self.yigin[-1][1] if self.yigin else False
        ust_kod = self.yigin[-1][2] if self.yigin else False
        gizli = ust_gizli or "hidden" in oznitelikler or oznitelikler.get("aria-hidden", "").casefold() == "true" or stiller.get("display") == "none" or stiller.get("visibility") == "hidden"
        kod = ust_kod or tag in ("script", "style")
        if tag not in self.void:
            self.yigin.append((tag, gizli, kod))

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if not self.yigin or self.yigin[-1][0] != tag:
            raise ValueError("etiket dengesi bozuk")
        self.yigin.pop()

    def handle_data(self, data):
        metin = " ".join(data.split())
        if not metin:
            return
        gizli = self.yigin[-1][1] if self.yigin else False
        kod = self.yigin[-1][2] if self.yigin else False
        katman = "kod" if kod else "gizli" if gizli else "gorunur"
        self.sonuc[katman].append(metin)

def dom_katmanlari(html):
    if not isinstance(html, str) or len(html) > 20000:
        raise ValueError("HTML geçersiz")
    parser = KatmanParser()
    parser.feed(html)
    parser.close()
    if parser.yigin:
        raise ValueError("kapanmamış etiket")
    return parser.sonuc
```

```hint
Yığında `(tag, gizli, kod)` üçlüsü tut; yeni düğümde üst düğümün bayraklarını miras al. `handle_data` içinde önce kod, sonra gizli katmanını seç; işlem sonunda yığının boş olduğunu doğrula.
```
:::

::: anlat DOM'un önerdiği eylem yetkili eylem değildir
Web içeriği bir bağlantıya tıklanmasını isteyebilir; uygulama ise yalnız izinli HTTPS alanlarına navigasyona izin verebilir. URL'nin metinde `ornek.test` geçirmesi yeterli değildir. `urlsplit` ile ayrıştırılan `hostname` izin listesiyle tam eşleşmeli; kullanıcı bilgisi ve açık farklı port reddedilmelidir.

Bu kontrol prompt injection savunmasının tamamı değildir. Yönlendirme sonrası varış alanı, DNS, TLS ve sayfa içeriği ayrıca denetlenir. Burada yalnız eylem adayındaki URL'nin ilk politika kapısını fixture ile sınarız; gerçek bağlantı kurmayız.

**Sık tuzaklar:** `urlsplit(...).port`, `:99999` gibi geçersiz portta `ValueError` yükseltir. Bu hata yakalanmazsa tek bir kötü bağlantı bütün süzgeci düşürür (`e-08`). Sondaki noktalı `destek.pafta.test.` DNS'te aynı adı gösterebilir, ama bu ders tam eşleşme ister ve adayı reddeder (`e-11`). `javascript:` bağlantısının (`e-10`) içinde `https://kotu.test` geçer. Şemaya bakmadan metinde `https://` arayan bir kontrol bu bağlantıyı geçirir. Şemayı her zaman ayrıştırılmış `scheme` alanından denetle.
:::

::: gorev 2 · Tarayıcı eylemlerini HTTPS alan izin listesinden geçir
`eylem_suz(adaylar, izinli_alanlar)` işlevini yaz. Her aday tam olarak `id`, `eylem`, `url` alanlarını taşısın. Kimlik boş olmayan ve benzersiz string, `eylem` `click` veya `navigate`, URL string olmalıdır. İzinli alanlar boş olmayan stringlerden oluşan liste olmalıdır. Şema ihlalinde `ValueError` yükselt.

Bir aday izinlidir yalnız:

1. URL şeması tam `https` ise.
2. `urlsplit(url).hostname` izinli alanlardan biriyle büyük/küçük harf duyarsız tam eşleşiyorsa.
3. Kullanıcı adı ve parola yoksa.
4. Açık port yoksa veya port `443` ise.

Geçersiz port gibi URL ayrıştırma hatalarında adayı reddet; bütün işlemi durdurma. Dönüş `{"izinli":[ID,...],"reddedilen":[ID,...]}` olup aday sırasını korur. Alt alan adlarını otomatik kabul etme, URL metni üzerinde alt string araması yapma. Girdiyi değiştirme.

Görünür veri: `veri/eylem_adaylari.json`. On bir adaydan yalnız ilk ikisi izinli olmalıdır. Dört bozuk girdi `ValueError` almalıdır.

```starter
from urllib.parse import urlsplit
from ai_saldiri_veri import json_yukle

def eylem_suz(adaylar, izinli_alanlar):
    # KUSURLU BAŞLANGIÇ KODU: izinli alan adını URL metninde alt string olarak arıyor (sahte son ek, sorgu parametresi ve kullanıcı bilgisi geçer), şemayı ve portu denetlemiyor, şema ihlalinde ValueError yükseltmiyor!
    sonuc = {"izinli": [], "reddedilen": []}
    for aday in adaylar:
        url = str(aday.get("url", "")).lower()
        izinli = any(alan.lower() in url for alan in izinli_alanlar)
        sonuc["izinli" if izinli else "reddedilen"].append(aday.get("id"))
    return sonuc

veri = json_yukle("veri/eylem_adaylari.json")
sonuc = eylem_suz(veri["adaylar"], veri["izinli_alanlar"])
print("sonuç   :", sonuc)
print("beklenen:", veri["beklenen"])
for b in veri["bozuk_girdiler"]:
    try:
        eylem_suz(b["adaylar"], b["izinli_alanlar"])
        print(b, "KABUL edildi (yanlış)")
    except ValueError as hata:
        print("reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-31")
```

```test
import copy
ADAYLAR = [
    {"id": "a1", "eylem": "click", "url": "https://ornek.test/belge"},
    {"id": "a2", "eylem": "navigate", "url": "https://ORNEK.test:443/x"},
    {"id": "a3", "eylem": "click", "url": "http://ornek.test/x"},
    {"id": "a4", "eylem": "click", "url": "https://alt.ornek.test/x"},
    {"id": "a5", "eylem": "click", "url": "https://ornek.test@evil.test/x"},
    {"id": "a6", "eylem": "click", "url": "https://ornek.test:444/x"},
    {"id": "a7", "eylem": "click", "url": "https://ornek.test:bad/x"},
]
def sozlesme(fn):
    try:
        once = copy.deepcopy(ADAYLAR)
        beklenen = {"izinli": ["a1", "a2"], "reddedilen": ["a3", "a4", "a5", "a6", "a7"]}
        if fn(ADAYLAR, ["ornek.test"]) != beklenen or ADAYLAR != once:
            return False
        if fn([], ["ornek.test"]) != {"izinli": [], "reddedilen": []} or fn(ADAYLAR[:1], ["diger.test"])["izinli"] != []:
            return False
        if fn([{"id": "u1", "eylem": "click", "url": "https://user@ornek.test/x"}, {"id": "u2", "eylem": "click", "url": "https://:pass@ornek.test/x"}], ["ornek.test"])["reddedilen"] != ["u1", "u2"]:
            return False
        for adaylar, alanlar in [
            (ADAYLAR, []), (ADAYLAR, [""]), (ADAYLAR, [123]), (ADAYLAR, "ornek.test"), ([123], ["ornek.test"]), ([["id", "eylem", "url"]], ["ornek.test"]),
            (ADAYLAR + [ADAYLAR[0]], ["ornek.test"]),
            ([dict(ADAYLAR[0], id="")], ["ornek.test"]),
            ([dict(ADAYLAR[0], eylem="submit")], ["ornek.test"]),
            ([dict(ADAYLAR[0], url=3)], ["ornek.test"]),
            ([dict(ADAYLAR[0], ek=1)], ["ornek.test"]),
        ]:
            try:
                fn(adaylar, alanlar)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(eylem_suz), "tam host, HTTPS, kimlik bilgisi ve port politikası korunmalı")
def m_altmetin(adaylar, izinli_alanlar):
    return {"izinli": [a["id"] for a in adaylar if any(x in a["url"] for x in izinli_alanlar)], "reddedilen": []}
def m_http(adaylar, izinli_alanlar):
    return {"izinli": [a["id"] for a in adaylar if a["url"].startswith("http")], "reddedilen": []}
def m_port(adaylar, izinli_alanlar):
    sonuc = eylem_suz(adaylar, izinli_alanlar)
    sonuc["izinli"].append("a6")
    sonuc["reddedilen"].remove("a6")
    return sonuc
for ad, mutant in [("URL alt metnini host sayan", m_altmetin), ("HTTP'ye izin veren", m_http), ("farklı portu kabul eden", m_port)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

eq(eylem_suz([{'id':'ust','eylem':'click','url':'https://ornek.test/a'}],['ORNEK.TEST']),{'izinli':['ust'],'reddedilen':[]},'izinli alan casefold')
```

```solution
from urllib.parse import urlsplit

def eylem_suz(adaylar, izinli_alanlar):
    if not isinstance(izinli_alanlar, list) or not izinli_alanlar or not all(isinstance(x, str) and bool(x) for x in izinli_alanlar):
        raise ValueError("izinli alan listesi geçersiz")
    alanlar = {x.casefold() for x in izinli_alanlar}
    kimlikler = set()
    sonuc = {"izinli": [], "reddedilen": []}
    for aday in adaylar:
        if not isinstance(aday, dict) or set(aday) != {"id", "eylem", "url"}:
            raise ValueError("aday şeması geçersiz")
        if not all((isinstance(aday["id"], str), bool(aday["id"]), aday["id"] not in kimlikler, aday["eylem"] in ("click", "navigate"), isinstance(aday["url"], str))):
            raise ValueError("aday alanları geçersiz")
        kimlikler.add(aday["id"])
        try:
            parca = urlsplit(aday["url"])
            izinli = parca.scheme == "https" and parca.hostname in alanlar and parca.username is None and parca.password is None and parca.port in (None, 443)
        except ValueError:
            izinli = False
        sonuc["izinli" if izinli else "reddedilen"].append(aday["id"])
    return sonuc
```

```hint
`urlsplit` sonucunun `scheme`, `hostname`, `username`, `password` ve `port` alanlarını ayrı denetle. Port erişimini `try/except ValueError` içine al; sonuç listesini tek koşulla seç.
```
:::

::: anlat DOM ve ekran kanıtı eşleştirilmelidir
Gizli DOM enjeksiyonu adayını bulmak için aynı vakanın DOM ve ekran/OCR metinleri karşılaştırılır. Canary DOM'da olup ekranda yoksa gizli DOM farkı adayıdır. Ekranda olup DOM'da olmaması da kayda değerdir; iki kanalda bulunması ise gizli metin iddiasını desteklemez.

Tam satır ölçütü, “canary yazma” gibi alıntıları eşleşme dışında bırakır. Bu fark, ajanın enjeksiyonu uyguladığını göstermez; hangi kanalın talimat görünümlü içerik taşıdığını gösterir. Eylem etkisini ayrıca politika ve araç kayıtlarıyla ölçmek gerekir.

**Çıktı nasıl okunur?** `veri/dom_ekran_kayitlari.json` içinde `d-03` canary'yi yalnız ekranda taşır. Bu, örneğin bir kampanya görselindeki yazının ekran görüntüsünden okunduğu durumdur. DOM'u süzen bir savunma bu kanalı hiç görmez; vaka `degisen` listesinden düşmemelidir. `d-04` canary'yi yalnız alıntılayan bir uyarıdır ve eşleşme sayılmaz. `d-05` canary satırını `\r\n` ile bitirir.
:::

::: gorev 3 · DOM ve ekran metinleri arasındaki canary farkını çıkar
`dom_ekran_farki(kayitlar, canary)` işlevini yaz. Her kayıt tam olarak `vaka_id`, `kanal`, `metin` alanlarını taşısın. Kimlik boş olmayan string, kanal `dom` veya `ekran`, metin string olmalıdır. Her vaka tam bir DOM ve bir ekran kaydına sahip olmalı; eksik veya yinelenen kanalda `ValueError` yükselt. Canary boş olmayan string olmalıdır.

Dönüş `{"vaka":N,"yalniz_dom":[...],"yalniz_ekran":[...],"her_iki":[...],"degisen":[...]}` biçimindedir. Canary tam satır aranır. `degisen`, iki kanalın canary durumu farklı olan vakalardır. Bütün listeler alfabetik sıralıdır; boş girdi için boş rapor dön. Kayıt sırası sonucu değiştirmemeli ve girdi değişmemelidir.

Görünür veri: `veri/dom_ekran_kayitlari.json`. Beklenen sonuç dosyanın `beklenen` alanındadır. Üç bozuk girdi `ValueError` almalıdır.

```starter
from ai_saldiri_veri import json_yukle

def dom_ekran_farki(kayitlar, canary):
    # KUSURLU BAŞLANGIÇ KODU: canary'yi alt metin olarak arıyor (alıntıyı da sayar), eksik/yinelenen kanalı ve boş canary'yi sessizce geçiyor, yalnız ekranda görülen farkı "degisen" listesine eklemiyor ve listeleri sıralamıyor!
    vakalar = {}
    for kayit in kayitlar:
        vakalar.setdefault(kayit["vaka_id"], {})[kayit["kanal"]] = kayit["metin"]
    sonuc = {"vaka": len(vakalar), "yalniz_dom": [], "yalniz_ekran": [], "her_iki": [], "degisen": []}
    for vaka, kanallar in vakalar.items():
        dom = canary in kanallar.get("dom", "")
        ekran = canary in kanallar.get("ekran", "")
        if dom and ekran:
            sonuc["her_iki"].append(vaka)
        elif dom:
            sonuc["yalniz_dom"].append(vaka)
            sonuc["degisen"].append(vaka)
        elif ekran:
            sonuc["yalniz_ekran"].append(vaka)
    return sonuc

veri = json_yukle("veri/dom_ekran_kayitlari.json")
sonuc = dom_ekran_farki(veri["kayitlar"], veri["canary"])
print("sonuç   :", sonuc)
print("beklenen:", veri["beklenen"])
for alan in veri["beklenen"]:
    if sonuc.get(alan) != veri["beklenen"][alan]:
        print("FARK:", alan, sonuc.get(alan), "≠", veri["beklenen"][alan])
for b in veri["bozuk_girdiler"]:
    try:
        dom_ekran_farki(b["kayitlar"], b["canary"])
        print(len(b["kayitlar"]), "kayıt, canary", repr(b["canary"]), "KABUL edildi (yanlış)")
    except ValueError as hata:
        print(len(b["kayitlar"]), "kayıt, canary", repr(b["canary"]), "reddedildi:", hata)
```

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules["__main__"].__file__).resolve().parent))
from ai_saldiri_veri import hazirla
hazirla("ai-saldiri-31")
```

```test
import copy
KAYITLAR = [
    {"vaka_id": "v1", "kanal": "ekran", "metin": "Rapor"},
    {"vaka_id": "v1", "kanal": "dom", "metin": "BREACH:CANARY-42"},
    {"vaka_id": "v2", "kanal": "dom", "metin": "Rapor"},
    {"vaka_id": "v2", "kanal": "ekran", "metin": "BREACH:CANARY-42"},
    {"vaka_id": "v3", "kanal": "dom", "metin": "BREACH:CANARY-42"},
    {"vaka_id": "v3", "kanal": "ekran", "metin": "BREACH:CANARY-42"},
    {"vaka_id": "v4", "kanal": "dom", "metin": "BREACH:CANARY-42 yazma"},
    {"vaka_id": "v4", "kanal": "ekran", "metin": "Rapor"},
]
BEKLENEN = {"vaka": 4, "yalniz_dom": ["v1"], "yalniz_ekran": ["v2"], "her_iki": ["v3"], "degisen": ["v1", "v2"]}
def sozlesme(fn):
    try:
        once = copy.deepcopy(KAYITLAR)
        if fn(KAYITLAR, "BREACH:CANARY-42") != BEKLENEN or KAYITLAR != once or fn(list(reversed(KAYITLAR)), "BREACH:CANARY-42") != BEKLENEN:
            return False
        if fn([], "BREACH:CANARY-42") != {"vaka": 0, "yalniz_dom": [], "yalniz_ekran": [], "her_iki": [], "degisen": []}:
            return False
        for kayitlar, canary in [
            (KAYITLAR, ""), (KAYITLAR, None), (KAYITLAR, 123), (KAYITLAR[:-1], "BREACH:CANARY-42"),
            (KAYITLAR + [KAYITLAR[0]], "BREACH:CANARY-42"),
            ([dict(KAYITLAR[0], kanal="diger"), KAYITLAR[1]], "BREACH:CANARY-42"),
            ([dict(KAYITLAR[0], vaka_id=""), KAYITLAR[1]], "BREACH:CANARY-42"),
            ([dict(KAYITLAR[0], metin=3), KAYITLAR[1]], "BREACH:CANARY-42"),
            ([dict(KAYITLAR[0], ek=1), KAYITLAR[1]], "BREACH:CANARY-42"), ([None], "BREACH:CANARY-42"),
        ]:
            try:
                fn(kayitlar, canary)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False
ok(sozlesme(dom_ekran_farki), "kanal eşleşmesi, tam satır ve iki yönlü fark korunmalı")
def m_altmetin(kayitlar, canary):
    return {"vaka": len(kayitlar), "yalniz_dom": [x["vaka_id"] for x in kayitlar if canary in x["metin"]], "yalniz_ekran": [], "her_iki": [], "degisen": []}
def m_ters(kayitlar, canary):
    sonuc = dom_ekran_farki(kayitlar, canary)
    sonuc["yalniz_dom"], sonuc["yalniz_ekran"] = sonuc["yalniz_ekran"], sonuc["yalniz_dom"]
    return sonuc
def m_degisen(kayitlar, canary):
    sonuc = dom_ekran_farki(kayitlar, canary)
    sonuc["degisen"] = sonuc["yalniz_dom"]
    return sonuc
for ad, mutant in [("kanalları ve tam satırı yok sayan", m_altmetin), ("DOM ve ekranı ters çeviren", m_ters), ("ekran-only farkını düşüren", m_degisen)]:
    ok(not sozlesme(mutant), "yanlış çözüm/mutant yakalanmalı: " + ad)

eq(dom_ekran_farki([{'vaka_id':'ek','kanal':'dom','metin':'CANARY'},{'vaka_id':'ek','kanal':'ekran','metin':'CANARY ek'}],'CANARY'),{'vaka':1,'yalniz_dom':['ek'],'yalniz_ekran':[],'her_iki':[],'degisen':['ek']},'ekran canary tam satır')
```

```solution
def dom_ekran_farki(kayitlar, canary):
    if not isinstance(canary, str) or not canary:
        raise ValueError("canary geçersiz")
    vakalar = {}
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"vaka_id", "kanal", "metin"}:
            raise ValueError("kayıt şeması geçersiz")
        if not all((isinstance(kayit["vaka_id"], str), bool(kayit["vaka_id"]), kayit["kanal"] in ("dom", "ekran"), isinstance(kayit["metin"], str))):
            raise ValueError("kayıt alanları geçersiz")
        kanallar = vakalar.setdefault(kayit["vaka_id"], {})
        if kayit["kanal"] in kanallar:
            raise ValueError("yinelenen kanal")
        kanallar[kayit["kanal"]] = kayit["metin"]
    sonuc = {"vaka": len(vakalar), "yalniz_dom": [], "yalniz_ekran": [], "her_iki": [], "degisen": []}
    for vaka in sorted(vakalar):
        kanallar = vakalar[vaka]
        if set(kanallar) != {"dom", "ekran"}:
            raise ValueError("kanallar eksik")
        dom = canary in kanallar["dom"].splitlines()
        ekran = canary in kanallar["ekran"].splitlines()
        if dom and ekran:
            sonuc["her_iki"].append(vaka)
        elif dom:
            sonuc["yalniz_dom"].append(vaka)
        elif ekran:
            sonuc["yalniz_ekran"].append(vaka)
        if dom != ekran:
            sonuc["degisen"].append(vaka)
    return sonuc
```

```hint
Vaka kimliğinden iki kanalın metnine giden sözlük kur. Her vaka için iki bool üret; üç durum listesini doldurduktan sonra bool farkını `degisen` listesine ekle.
```
:::

::: anlat Gerçek başsız tarayıcıda (Playwright + Chromium) DOM ve ekran farkı
İlk üç görevde saf Python ile kurduğun katman ayrıştırma (`dom_katmanlari`), HTTPS alan süzgeci (`eylem_suz`) ve DOM/ekran farkı (`dom_ekran_farki`), aşağıdaki son görevde **gerçek başsız Chromium tarayıcısı (Playwright)** üzerinde sınanır. Ağa hiç çıkmadan (`route.abort()`) yerel bir HTML sayfası Chromium'a yüklenir; tarayıcının gerçek düzen motorunun (layout engine) oluşturduğu görünür ekran metni (`locator("body").inner_text()`) ile ham DOM metni (`document.body.textContent`) ve `<a>` bağlantıları doğrudan Chromium'dan çekilerek senin işlevlerinle doğrulanır.

Deneyde dil modeli ya da ajan yoktur. Ölçülen, aynı sayfanın iki kanalda farklı metin vermesidir. Sayfanın `hidden` bloğundaki dinamik canary `textContent` içinde tam satırdır, `innerText` içinde yoktur. Kabul için `yalniz_dom` listesinde tam bu vaka olmalıdır. Bağlantılar da `data-eylem` özniteliğinden eylem adayına çevrilir ve senin süzgecinden geçer. İzinli alan `ic.pafta.test` olduğu için dış ve HTTP bağlantıları reddedilmelidir.

Sayfadaki `aria-hidden="true"` paragrafı senin `dom_katmanlari` sonucunda gizli katmandadır, ama Chromium'un `innerText` çıktısında görünür. İki sonuç çelişmez: `aria-hidden` yalnız erişilebilirlik ağacından gizler. Bu deney sayfayı ağ kapalı ve tek seferlik yükler; JavaScript ile sonradan eklenen içerik ya da gerçek bir sitenin davranışı hakkında bilgi vermez.
:::

::: gorev Gerçek deney · Başsız Chromium'da DOM katmanlarını ve ekran farkını ölç
Önceki üç görevdeki `dom_katmanlari`, `eylem_suz` ve `dom_ekran_farki` işlevlerini burada birleştir.

```meta
motor: ai-gercek
gereksinim: torch
timeout: 300
```

```starter
from html.parser import HTMLParser
from urllib.parse import urlsplit
import ai_lab

class KatmanParser(HTMLParser):
    # KUSURLU BAŞLANGIÇ KODU: gizliliği yalnız son açılan etiketten okuyor (gizli üst düğümün çocukları görünür sayılır), stilde yalnız boşluksuz küçük harfli "display:none" arıyor, aria-hidden ve visibility'yi yok sayıyor, script/style içeriğini görünür sayıyor ve etiket dengesini denetlemiyor!
    def __init__(self):
        super().__init__()
        self.sonuc = {"gorunur": [], "gizli": [], "kod": []}
        self.gizli = False

    def handle_starttag(self, tag, attrs):
        oznitelikler = dict(attrs)
        self.gizli = "hidden" in oznitelikler or "display:none" in (oznitelikler.get("style") or "")

    def handle_endtag(self, tag):
        self.gizli = False

    def handle_data(self, data):
        metin = " ".join(data.split())
        if metin:
            self.sonuc["gizli" if self.gizli else "gorunur"].append(metin)

def dom_katmanlari(html):
    parser = KatmanParser()
    parser.feed(str(html))
    return parser.sonuc

def eylem_suz(adaylar, izinli_alanlar):
    # KUSURLU BAŞLANGIÇ KODU: izinli alan adını URL metninde alt string olarak arıyor (sahte son ek, sorgu parametresi ve kullanıcı bilgisi geçer), şemayı ve portu denetlemiyor, şema ihlalinde ValueError yükseltmiyor!
    sonuc = {"izinli": [], "reddedilen": []}
    for aday in adaylar:
        url = str(aday.get("url", "")).lower()
        izinli = any(alan.lower() in url for alan in izinli_alanlar)
        sonuc["izinli" if izinli else "reddedilen"].append(aday.get("id"))
    return sonuc

def dom_ekran_farki(kayitlar, canary):
    # KUSURLU BAŞLANGIÇ KODU: canary'yi alt metin olarak arıyor (alıntıyı da sayar), eksik/yinelenen kanalı ve boş canary'yi sessizce geçiyor, yalnız ekranda görülen farkı "degisen" listesine eklemiyor ve listeleri sıralamıyor!
    vakalar = {}
    for kayit in kayitlar:
        vakalar.setdefault(kayit["vaka_id"], {})[kayit["kanal"]] = kayit["metin"]
    sonuc = {"vaka": len(vakalar), "yalniz_dom": [], "yalniz_ekran": [], "her_iki": [], "degisen": []}
    for vaka, kanallar in vakalar.items():
        dom = canary in kanallar.get("dom", "")
        ekran = canary in kanallar.get("ekran", "")
        if dom and ekran:
            sonuc["her_iki"].append(vaka)
        elif dom:
            sonuc["yalniz_dom"].append(vaka)
            sonuc["degisen"].append(vaka)
        elif ekran:
            sonuc["yalniz_ekran"].append(vaka)
    return sonuc

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_31 as deney
    deney.goster(dom_katmanlari, eylem_suz, dom_ekran_farki)
```

```test
import copy
import ai_lab
from sandbox import ai_gercek_ai_saldiri_31 as D

checks = []
_base_ok = ok
def ok(kosul, mesaj):
    checks.append(bool(kosul))
    return _base_ok(kosul, mesaj)

for ad in ("dom_katmanlari", "eylem_suz", "dom_ekran_farki"):
    need(ad)

import ast
_yasak = ("dom_katmanlari_referans", "eylem_suz_referans", "dom_ekran_farki_referans", "kanit_yaz")
sorun = list(ai_lab.kod_denetimi(src, _yasak))
for _n in ast.walk(ast.parse(src)):
    if isinstance(_n, ast.ImportFrom) and any(a.name in _yasak or a.name == "*" for a in _n.names): sorun.append("referans importu yasak")
    if isinstance(_n, (ast.Import, ast.ImportFrom)) and any(x and x.split(".")[0] in ("inspect", "importlib", "runpy") for x in [a.name for a in _n.names] + ([_n.module] if isinstance(_n, ast.ImportFrom) else [])): sorun.append("kaynak okuma/dinamik import yasak")
    if isinstance(_n, ast.Name) and _n.id in ("exec", "eval", "compile", "__builtins__"): sorun.append("dinamik kod çalıştırma yasak: " + _n.id)
ok(not sorun, "laboratuvar yamalanmamalı, referans işlevler çağrılmamalı: " + "; ".join(sorted(set(sorun))))

HTML = '<div>Rapor <span hidden>BREACH:CANARY-42</span><span style="display: none">Gizli</span></div><script>BREACH:CANARY-42</script><p aria-hidden="true">Aria</p><p>Son</p>'
ADAYLAR = [
    {"id": "a1", "eylem": "click", "url": "https://ornek.test/belge"},
    {"id": "a2", "eylem": "navigate", "url": "https://ORNEK.test:443/x"},
    {"id": "a3", "eylem": "click", "url": "http://ornek.test/x"},
    {"id": "a4", "eylem": "click", "url": "https://alt.ornek.test/x"},
    {"id": "a5", "eylem": "click", "url": "https://ornek.test@evil.test/x"},
    {"id": "a6", "eylem": "click", "url": "https://ornek.test:444/x"},
    {"id": "a7", "eylem": "click", "url": "https://ornek.test:bad/x"},
]
KAYITLAR = [
    {"vaka_id": "v1", "kanal": "ekran", "metin": "Rapor"},
    {"vaka_id": "v1", "kanal": "dom", "metin": "BREACH:CANARY-42"},
    {"vaka_id": "v2", "kanal": "dom", "metin": "Rapor"},
    {"vaka_id": "v2", "kanal": "ekran", "metin": "BREACH:CANARY-42"},
    {"vaka_id": "v3", "kanal": "dom", "metin": "BREACH:CANARY-42"},
    {"vaka_id": "v3", "kanal": "ekran", "metin": "BREACH:CANARY-42"},
    {"vaka_id": "v4", "kanal": "dom", "metin": "BREACH:CANARY-42 yazma"},
    {"vaka_id": "v4", "kanal": "ekran", "metin": "Rapor"},
]

def _sinir_ve_sema_kontrol():
    try:
        if dom_katmanlari(HTML) != D.dom_katmanlari_referans(HTML):
            return False
        if dom_katmanlari("<div><span>Acik</span></div>") != {"gorunur": ["Acik"], "gizli": [], "kod": []}:
            return False
        if dom_katmanlari("<div><span hidden><b>G</b></span></div>") != {"gorunur": [], "gizli": ["G"], "kod": []}:
            return False
        if dom_katmanlari("<div><script>K</script></div>") != {"gorunur": [], "gizli": [], "kod": ["K"]}:
            return False
        if dom_katmanlari("<div>   </div>") != {"gorunur": [], "gizli": [], "kod": []}:
            return False
        if dom_katmanlari('<p style=" DISPLAY : NONE ">A</p><p aria-hidden="TRUE">B</p>') != {"gorunur": [], "gizli": ["A", "B"], "kod": []}:
            return False
        if dom_katmanlari('<div hidden>A<span>B</span></div><style>x{}</style>') != {"gorunur": [], "gizli": ["A", "B"], "kod": ["x{}"]}:
            return False
        if dom_katmanlari('<p data-style="visibility: hidden">metin</p>')["gorunur"] != ["metin"]:
            return False
        if dom_katmanlari('<p style="visibility:hidden">x</p><img alt="y">')["gizli"] != ["x"] or dom_katmanlari("  A\n B  ")["gorunur"] != ["A B"]:
            return False
        if dom_katmanlari('<p style="display:none:extra">x</p>')["gorunur"] != ["x"] or len(dom_katmanlari("x" * 20000)["gorunur"][0]) != 20000:
            return False
        for bh in ['<div>', '</p>', '<div></span>', None, 3, 'x' * 20001]:
            try:
                dom_katmanlari(bh)
                return False
            except ValueError:
                pass

        once_a = copy.deepcopy(ADAYLAR)
        if eylem_suz(ADAYLAR, ["ornek.test"]) != D.eylem_suz_referans(ADAYLAR, ["ornek.test"]) or ADAYLAR != once_a:
            return False
        if eylem_suz([], ["ornek.test"]) != {"izinli": [], "reddedilen": []} or eylem_suz(ADAYLAR[:1], ["diger.test"])["izinli"] != []:
            return False
        if eylem_suz([{"id": "u1", "eylem": "click", "url": "https://user@ornek.test/x"}, {"id": "u2", "eylem": "click", "url": "https://:pass@ornek.test/x"}], ["ornek.test"])["reddedilen"] != ["u1", "u2"]:
            return False
        if eylem_suz([{"id": "ust", "eylem": "click", "url": "https://ornek.test/a"}], ["ORNEK.TEST"])["izinli"] != ["ust"]:
            return False
        for ba, bal in [
            (ADAYLAR, []), (ADAYLAR, [""]), (ADAYLAR, [123]), (ADAYLAR, "ornek.test"), ([123], ["ornek.test"]), ([["id", "eylem", "url"]], ["ornek.test"]),
            (ADAYLAR + [ADAYLAR[0]], ["ornek.test"]),
            ([dict(ADAYLAR[0], id="")], ["ornek.test"]),
            ([dict(ADAYLAR[0], eylem="submit")], ["ornek.test"]),
            ([dict(ADAYLAR[0], url=3)], ["ornek.test"]),
            ([dict(ADAYLAR[0], ek=1)], ["ornek.test"]),
        ]:
            try:
                eylem_suz(ba, bal)
                return False
            except ValueError:
                pass

        once_k = copy.deepcopy(KAYITLAR)
        bek_k = D.dom_ekran_farki_referans(KAYITLAR, "BREACH:CANARY-42")
        if dom_ekran_farki(KAYITLAR, "BREACH:CANARY-42") != bek_k or KAYITLAR != once_k or dom_ekran_farki(list(reversed(KAYITLAR)), "BREACH:CANARY-42") != bek_k:
            return False
        if dom_ekran_farki([], "BREACH:CANARY-42") != {"vaka": 0, "yalniz_dom": [], "yalniz_ekran": [], "her_iki": [], "degisen": []}:
            return False
        if dom_ekran_farki([{"vaka_id": "ek", "kanal": "dom", "metin": "CANARY"}, {"vaka_id": "ek", "kanal": "ekran", "metin": "CANARY ek"}], "CANARY")["yalniz_dom"] != ["ek"]:
            return False
        for bk, bc in [
            (KAYITLAR, ""), (KAYITLAR, None), (KAYITLAR, 123), (KAYITLAR[:-1], "BREACH:CANARY-42"),
            (KAYITLAR + [KAYITLAR[0]], "BREACH:CANARY-42"),
            ([dict(KAYITLAR[0], kanal="diger"), KAYITLAR[1]], "BREACH:CANARY-42"),
            ([dict(KAYITLAR[0], vaka_id=""), KAYITLAR[1]], "BREACH:CANARY-42"),
            ([dict(KAYITLAR[0], metin=3), KAYITLAR[1]], "BREACH:CANARY-42"),
            ([dict(KAYITLAR[0], ek=1), KAYITLAR[1]], "BREACH:CANARY-42"), ([None], "BREACH:CANARY-42"),
        ]:
            try:
                dom_ekran_farki(bk, bc)
                return False
            except ValueError:
                pass
        return True
    except Exception:
        return False

ok(_sinir_ve_sema_kontrol(), "DOM katmanları, eylem süzgeci ve DOM/ekran farkı işlevleri tüm sınır ve şema kurallarını geçti")

if not all(checks):
    stop()

try:
    r = D.deney(dom_katmanlari, eylem_suz, dom_ekran_farki)
except Exception as e:
    ok(False, f"GERÇEK PLAYWRIGHT CHROMIUM DENEYİ YAPILAMADI: {type(e).__name__}: {e}")
    stop()

for ad, deger in r["kontroller"].items():
    ok(deger, "gerçek deney: " + ad)

ai_lab.kanit_yaz("saldiri-31-dom-enjeksiyonu", {
    "kaynak": "gercek",
    "kabul": all(checks),
    "ders": "ai-saldiri-31",
    "ortam": r["ortam"],
    "ayarlar": r["ayarlar"],
    "deney": r,
    "ozet": r["ozet"],
})
o = r["ozet"]
ok(
    True,
    f"BULGU (Chromium {o['chromium_surumu']}): yalnız DOM'da görülen canary={o['yalniz_dom']}, "
    f"izinli eylemler={o['izinli_eylemler']}, reddedilen={o['reddedilen_eylemler']}.",
)
```

```solution
from html.parser import HTMLParser
from urllib.parse import urlsplit
import ai_lab

class KatmanParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sonuc = {"gorunur": [], "gizli": [], "kod": []}
        self.yigin = []
        self.void = {"img", "input", "meta", "link", "br", "hr"}

    def handle_starttag(self, tag, attrs):
        oznitelikler = dict(attrs)
        stiller = {}
        for parca in oznitelikler.get("style", "").split(";"):
            if ":" in parca:
                ad, deger = parca.split(":", 1)
                stiller[ad.strip().casefold()] = deger.strip().casefold()
        ust_gizli = self.yigin[-1][1] if self.yigin else False
        ust_kod = self.yigin[-1][2] if self.yigin else False
        gizli = ust_gizli or "hidden" in oznitelikler or oznitelikler.get("aria-hidden", "").casefold() == "true" or stiller.get("display") == "none" or stiller.get("visibility") == "hidden"
        kod = ust_kod or tag in ("script", "style")
        if tag not in self.void:
            self.yigin.append((tag, gizli, kod))

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if not self.yigin or self.yigin[-1][0] != tag:
            raise ValueError("etiket dengesi bozuk")
        self.yigin.pop()

    def handle_data(self, data):
        metin = " ".join(data.split())
        if not metin:
            return
        gizli = self.yigin[-1][1] if self.yigin else False
        kod = self.yigin[-1][2] if self.yigin else False
        katman = "kod" if kod else "gizli" if gizli else "gorunur"
        self.sonuc[katman].append(metin)

def dom_katmanlari(html):
    if not isinstance(html, str) or len(html) > 20000:
        raise ValueError("HTML geçersiz")
    parser = KatmanParser()
    parser.feed(html)
    parser.close()
    if parser.yigin:
        raise ValueError("kapanmamış etiket")
    return parser.sonuc

def eylem_suz(adaylar, izinli_alanlar):
    if not isinstance(izinli_alanlar, list) or not izinli_alanlar or not all(isinstance(x, str) and bool(x) for x in izinli_alanlar):
        raise ValueError("izinli alan listesi geçersiz")
    alanlar = {x.casefold() for x in izinli_alanlar}
    kimlikler = set()
    sonuc = {"izinli": [], "reddedilen": []}
    for aday in adaylar:
        if not isinstance(aday, dict) or set(aday) != {"id", "eylem", "url"}:
            raise ValueError("aday şeması geçersiz")
        if not all((isinstance(aday["id"], str), bool(aday["id"]), aday["id"] not in kimlikler, aday["eylem"] in ("click", "navigate"), isinstance(aday["url"], str))):
            raise ValueError("aday alanları geçersiz")
        kimlikler.add(aday["id"])
        try:
            parca = urlsplit(aday["url"])
            izinli = parca.scheme == "https" and parca.hostname in alanlar and parca.username is None and parca.password is None and parca.port in (None, 443)
        except ValueError:
            izinli = False
        sonuc["izinli" if izinli else "reddedilen"].append(aday["id"])
    return sonuc

def dom_ekran_farki(kayitlar, canary):
    if not isinstance(canary, str) or not canary:
        raise ValueError("canary geçersiz")
    vakalar = {}
    for kayit in kayitlar:
        if not isinstance(kayit, dict) or set(kayit) != {"vaka_id", "kanal", "metin"}:
            raise ValueError("kayıt şeması geçersiz")
        if not all((isinstance(kayit["vaka_id"], str), bool(kayit["vaka_id"]), kayit["kanal"] in ("dom", "ekran"), isinstance(kayit["metin"], str))):
            raise ValueError("kayıt alanları geçersiz")
        kanallar = vakalar.setdefault(kayit["vaka_id"], {})
        if kayit["kanal"] in kanallar:
            raise ValueError("yinelenen kanal")
        kanallar[kayit["kanal"]] = kayit["metin"]
    sonuc = {"vaka": len(vakalar), "yalniz_dom": [], "yalniz_ekran": [], "her_iki": [], "degisen": []}
    for vaka in sorted(vakalar):
        kanallar = vakalar[vaka]
        if set(kanallar) != {"dom", "ekran"}:
            raise ValueError("kanallar eksik")
        dom = canary in kanallar["dom"].splitlines()
        ekran = canary in kanallar["ekran"].splitlines()
        if dom and ekran:
            sonuc["her_iki"].append(vaka)
        elif dom:
            sonuc["yalniz_dom"].append(vaka)
        elif ekran:
            sonuc["yalniz_ekran"].append(vaka)
        if dom != ekran:
            sonuc["degisen"].append(vaka)
    return sonuc

if ai_lab.CALISTIR:
    from sandbox import ai_gercek_ai_saldiri_31 as deney
    deney.goster(dom_katmanlari, eylem_suz, dom_ekran_farki)
```

```hint
Önceki üç görevdeki çözümlerini birleştir; canlı deneyde başsız Chromium tarayıcısında yerel HTML işlenerek görünür ekran metni ile DOM metni karşılaştırılır.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
### DOM metni ekran metni değildir

textContent gizli düğümlerin metnini de taşıyabilir, innerText düzenin görünürlük kararlarına daha yakındır. HTMLParser yalnız verilen sözdizimini ayrıştırır; tarayıcının tüm CSS ve layout davranışını üretmez. Başsız Chromium gerçek kanal farkını ölçer ama bu derste LLM ajanı bulunmadığından talimatın ajan eylemine dönüştüğü sonucuna varılamaz.

| Yaygın yanlış | Doğru sınır |
|---|---|
| Ekranda yoksa modele gitmez | Hangi DOM/erişilebilirlik kanalının araca verildiği belirleyicidir. |

Sonraki bağlantı: ai-savunma-17. [Birincil kaynak](https://docs.python.org/3/library/html.parser.html). Kaynak mekanizmanın ilgili API veya yöntemini açıklar; bu labın başarı oranının kanıtı yerel ham koşudur.
:::
