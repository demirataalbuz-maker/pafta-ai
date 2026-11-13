---
id: ai-ile-guvenlik-23
title: "Oltalama E-postası · Modelin Kaçırdığı Kanıt"
summary: Oltalama kararını üsluptan değil, ayrıştırılmış kanıttan (gönderen alanı, DMARC sonucu, bağlantı hedefi) ver; DMARC'ın kapsamadığı görünen ad taklidini ve görünen ada gizlenmiş adresi ayrıca yakala.
esleme: ai-ile-guvenlik-10, ai-ile-guvenlik-22, ai-ile-guvenlik-01, ai-savunma-08
timeout: 30
---

::: anlat 1. Akıcı Türkçe kanıt değildir
Bir dil modeli bir e-postayı okuyup "dili düzgün, kurumsal üslup, güvenli görünüyor" diyebilir. Eskiden oltalamayı ele veren yazım hataları, artık modelle yazılmış metinlerde yok. Bu yüzden üslup bir **kanıt değildir**. Karar ayrıştırılmış meta veriye dayanır:

1. **Gönderen alan adı:** `From` başlığındaki adresin alan adı kurumun alan adı mı?
2. **DMARC sonucu:** RFC 7489'daki DMARC, `From` alan adını SPF ya da DKIM ile doğrulanmış bir alan adıyla eşleştirir (*Identifier Alignment*, bölüm 3.1). `pass` değilse gönderen alan adı doğrulanmamıştır.
3. **Bağlantı hedefi:** e-postadaki bağlantıların gerçek ana makinesi (görünen metni değil) kurumun alan adı mı?

DMARC güçlüdür ama bir şeyi bilerek kapsamaz. RFC 7489 kapsam dışı konuları sayarken (bölüm 2.2) `From` alanındaki *"display name"* saldırılarını ve insanın okuduğu görünen adın kötüye kullanımını (bölüm 2.4) açıkça dışarıda bırakır. `"Örnek Bank Güvenlik" <bildirim@baska.invalid>` biçiminde bir e-posta, kendi alan adı için DMARC'tan `pass` alabilir; DMARC'ın baktığı şey `baska.invalid`'dir, görünen ad değil.

> [!NOTE]
> Bu derste gerçek e-posta, MIME ayrıştırma, DKIM doğrulaması ya da DNS sorgusu yoktur. Başlıklar ve DMARC sonucu önceden ayrıştırılmış **sentetik** alanlar olarak verilir. `.invalid` alan adları RFC 2606 gereği hiçbir zaman gerçek bir ana makineye çözülmez.
:::

::: anlat 2. Mekanizma: üç kanıt, iki kör nokta
Kanıtlar bağımsızdır ve her biri ayrı raporlanır. Bir e-posta doğru alandan gelip DMARC'ı geçebilir, ama bağlantısı `bank.invalid.toplama.invalid` gibi bir ana makineye gidebilir. Ana makine karşılaştırması **tam eşitlikle** yapılır: `bank.invalid` öneki, `.invalid` soneki ya da alt alan adı otomatik izinli değildir.

Bu kanıtların göremediği iki kör nokta vardır, ikisi de görünen addadır (RFC 5322 bölüm 3.4'teki `display-name`):

- **Görünen ad taklidi:** görünen ad kurumun adını taşır (`Örnek Bank Güvenlik`), ama gerçek adres başka bir alandandır.
- **Adres gizleme:** görünen adın kendisi bir adres gibi yazılır (`"guvenlik@bank.invalid" <x@baska.invalid>`). Birçok istemci yalnız görünen adı gösterdiği için kullanıcı kurumun adresini görür.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| "Dili düzgün, güvenli" | Model akıcı oltalama metni yazar | Karar meta veriye dayanır |
| DMARC `pass` = güvenli | DMARC görünen adı denetlemez | Görünen adı ayrıca denetle |
| `hostname.endswith(kurum)` | `kotubank.invalid` de `bank.invalid` ile biter | Tam eşitlik |
| Bağlantının görünen metnine bakmak | Metin `bank.invalid`, hedef başka yer olabilir | Ayrıştırılmış hedef URL'nin ana makinesi |
| Alan adını büyük/küçük harfe duyarlı karşılaştırmak | `BANK.invalid` aynı alandır | İki tarafı da küçült |
:::

::: tahmin DMARC geçti, görünen ad yalan söylüyor
Aşağıdaki e-posta kendi alan adı için DMARC'tan geçmiş. DMARC'a ve görünen ada bakan iki kontrol ne söyler?

```python
gorunen_ad = 'Örnek Bank Güvenlik'
adres = 'bildirim@baska.invalid'
dmarc = 'pass'
kurum_domain = 'bank.invalid'

alan = adres.rsplit('@', 1)[1]
print('DMARC kontrolü:', 'temiz' if dmarc == 'pass' else 'şüpheli')
print('görünen ad kontrolü:', 'taklit' if 'bank' in gorunen_ad.casefold() and alan != kurum_domain else 'temiz')
```

???

```cikti
DMARC kontrolü: temiz
görünen ad kontrolü: taklit
```
DMARC `baska.invalid` için doğru sonuç verdi: e-posta gerçekten oradan geliyor. Ama kullanıcının gördüğü ad kurumun adı. RFC 7489 bu saldırıyı kapsam dışı bırakır; ayrı bir kontrol gerekir.
:::

::: gorev 1 · Ayrıştırılmış kanıttan oltalama bulguları
`posta_bulgulari(kayit, kurum)` işlevini yaz.

- `kurum` boş olmayan bir `str`. `kayit` bir `dict`: `sender_domain` boş olmayan `str`, `dmarc` `'pass'`, `'fail'` ya da `'none'`, `links` bir `str` listesi. Değilse `ValueError`.
- Bulgular **bu sırayla**:
  1. `sender_domain.lower() != kurum.lower()` → `'sender-mismatch'`;
  2. `dmarc != 'pass'` → `'dmarc'`;
  3. Bağlantılardan herhangi birinin şeması `https` değilse ya da `urlsplit(link).hostname` kurumun küçük harfli alan adına **tam eşit** değilse (ayrıştırılamayan bağlantı dahil) → `'link-target'` (bir kez).
- Dönüş: bulgu listesi.

KUSURLU başlangıç alan adını büyük/küçük harfe duyarlı karşılaştırıyor, bağlantıda `endswith` kullanıyor ve `none` DMARC sonucunu temiz sayıyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[{"sender_domain": "BANK.invalid", "dmarc": "none", "links": ["https://kotubank.invalid/giris"]}, "bank.invalid"]', encoding='utf-8')
```

```starter
from urllib.parse import urlsplit

def posta_bulgulari(kayit, kurum):
    bulgu = []
    if kayit['sender_domain'] != kurum:
        bulgu.append('sender-mismatch')
    if kayit['dmarc'] == 'fail':
        bulgu.append('dmarc')
    if any(not (urlsplit(u).hostname or '').endswith(kurum) for u in kayit['links']):
        bulgu.append('link-target')
    return bulgu

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(posta_bulgulari(*_args))
```

```solution
from urllib.parse import urlsplit

def posta_bulgulari(kayit, kurum):
    if not isinstance(kurum, str) or not kurum.strip():
        raise ValueError('kurum bos olmayan str olmali')
    if (not isinstance(kayit, dict) or not isinstance(kayit.get('sender_domain'), str) or not kayit['sender_domain'].strip()
            or kayit.get('dmarc') not in ('pass', 'fail', 'none') or not isinstance(kayit.get('links'), list)
            or any(not isinstance(u, str) for u in kayit['links'])):
        raise ValueError('bozuk kayit')
    hedef = kurum.lower()
    bulgu = []
    if kayit['sender_domain'].lower() != hedef:
        bulgu.append('sender-mismatch')
    if kayit['dmarc'] != 'pass':
        bulgu.append('dmarc')

    def gecerli(u):
        try:
            p = urlsplit(u)
            return p.scheme == 'https' and p.hostname == hedef
        except ValueError:
            return False

    if any(not gecerli(u) for u in kayit['links']):
        bulgu.append('link-target')
    return bulgu

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(posta_bulgulari(*_args))
```

```test
need('posta_bulgulari')
import copy
_iyi = {'sender_domain': 'bank.invalid', 'dmarc': 'pass', 'links': ['https://bank.invalid/giris', 'https://BANK.invalid:443/yardim']}
_yedek = copy.deepcopy(_iyi)
eq(posta_bulgulari(_iyi, 'bank.invalid'), [], 'kurum alanı, DMARC pass ve kurum bağlantıları temiz')
eq(_iyi, _yedek, 'girdi değişmemeli')
eq(posta_bulgulari(dict(_iyi, sender_domain='BANK.Invalid'), 'Bank.INVALID'), [], 'alan adları büyük/küçük harfe duyarsız')
eq(posta_bulgulari(dict(_iyi, links=[]), 'bank.invalid'), [], 'bağlantısız e-posta link bulgusu üretmez')
eq(posta_bulgulari({'sender_domain': 'baska.invalid', 'dmarc': 'fail', 'links': ['http://bank.invalid/x', 'https://bank.invalid/y']}, 'bank.invalid'),
   ['sender-mismatch', 'dmarc', 'link-target'], 'üç bulgu sabit sırayla; link bulgusu bir kez')
eq(posta_bulgulari(dict(_iyi, dmarc='none'), 'bank.invalid'), ['dmarc'], 'DMARC none da doğrulanmamıştır')
for _link in ('https://kotubank.invalid/', 'https://bank.invalid.toplama.invalid/', 'https://giris.bank.invalid/',
              'https://bank.invalid@toplama.invalid/', 'http://bank.invalid/', 'https://[::1/', 'bank.invalid/giris'):
    eq(posta_bulgulari(dict(_iyi, links=[_link]), 'bank.invalid'), ['link-target'], f'güvenilmeyen bağlantı hedefi: {_link}')
for _alan in ('kotubank.invalid', 'bank.invalid.x', 'giris.bank.invalid'):
    eq(posta_bulgulari(dict(_iyi, sender_domain=_alan), 'bank.invalid'), ['sender-mismatch'], f'gönderen tam eşleşmeli: {_alan}')

for _kurum in ('', '   ', None, 5):
    raises(ValueError, posta_bulgulari, _iyi, _kurum, msg=f'bozuk kurum ValueError: {_kurum!r}')
for _bozuk in (None, [], {'dmarc': 'pass', 'links': []}, dict(_iyi, sender_domain=''), dict(_iyi, sender_domain='  '),
               dict(_iyi, sender_domain=5), dict(_iyi, dmarc='PASS'), dict(_iyi, dmarc=None), dict(_iyi, links='https://bank.invalid'),
               dict(_iyi, links=['https://bank.invalid', None])):
    raises(ValueError, posta_bulgulari, _bozuk, 'bank.invalid', msg=f'bozuk kayıt ValueError: {_bozuk!r}')
```

```hint
Kurum adını bir kez küçült ve hem gönderen hem bağlantı karşılaştırmasında onu kullan. `urlsplit(...).hostname` zaten küçük harf döndürür; `[::1` gibi bozuk bir URL'de `ValueError` fırlatabilir, onu yakala.
```
:::

::: gorev 2 · Görünen ad taklidini ve gizlenmiş adresi yakala
DMARC'ın kapsamadığı görünen ad saldırılarını denetleyen `gorunen_ad_denetle(gorunen_ad, adres, kurum_adlari, kurum_domain)` işlevini yaz. Başlık önceden ayrıştırılmıştır: `gorunen_ad` kullanıcının gördüğü ad, `adres` gerçek adrestir.

- `gorunen_ad` bir `str` (boş olabilir); `adres` içinde tam bir `@` bulunan, iki yanı boş olmayan bir `str`; `kurum_adlari` boş olmayan `str`'lerden oluşan bir `list`; `kurum_domain` boş olmayan bir `str`. Değilse `ValueError`.
- Gerçek alan adı: `adres`'in `@` sonrası, küçük harfle.
- Bulgular **bu sırayla**:
  1. `kurum_adlari`'ndan biri `gorunen_ad` içinde geçiyorsa (`casefold` ile) ve gerçek alan adı `kurum_domain.lower()` değilse → `'gorunen-ad-taklidi'`;
  2. `gorunen_ad` içinde `@` varsa ve görünen addaki adres (baştaki/sondaki boşluk ve çift tırnak atılmış hâli, `casefold`) gerçek `adres.casefold()`'a eşit değilse → `'adres-gizleme'`.
- Dönüş: bulgu listesi.

KUSURLU başlangıç kurum adını büyük/küçük harfe duyarlı arıyor ve görünen addaki adresi hiç denetlemiyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def gorunen_ad_denetle(gorunen_ad, adres, kurum_adlari, kurum_domain):
    alan = adres.split('@')[1]
    if any(a in gorunen_ad for a in kurum_adlari) and alan != kurum_domain:
        return ['gorunen-ad-taklidi']
    return []
```

```solution
def gorunen_ad_denetle(gorunen_ad, adres, kurum_adlari, kurum_domain):
    if (not isinstance(gorunen_ad, str) or not isinstance(adres, str) or adres.count('@') != 1
            or not isinstance(kurum_domain, str) or not kurum_domain.strip()
            or not isinstance(kurum_adlari, list) or not kurum_adlari
            or any(not isinstance(a, str) or not a.strip() for a in kurum_adlari)):
        raise ValueError('bozuk girdi')
    yerel, alan = adres.split('@')
    if not yerel or not alan:
        raise ValueError('adres yerel@alan olmali')
    bulgu = []
    ad = gorunen_ad.casefold()
    if any(a.casefold() in ad for a in kurum_adlari) and alan.lower() != kurum_domain.lower():
        bulgu.append('gorunen-ad-taklidi')
    if '@' in gorunen_ad and gorunen_ad.strip().strip('"').strip().casefold() != adres.casefold():
        bulgu.append('adres-gizleme')
    return bulgu
```

```test
need('gorunen_ad_denetle')
_ad = ['Örnek Bank']
eq(gorunen_ad_denetle('Örnek Bank Güvenlik', 'bildirim@bank.invalid', _ad, 'bank.invalid'), [], 'kurum adı kurum alanından geliyorsa temiz')
eq(gorunen_ad_denetle('Örnek Bank Güvenlik', 'bildirim@BANK.Invalid', _ad, 'Bank.invalid'), [], 'alan karşılaştırması harfe duyarsız')
eq(gorunen_ad_denetle('ÖRNEK BANK güvenlik', 'bildirim@baska.invalid', _ad, 'bank.invalid'), ['gorunen-ad-taklidi'],
   'görünen ad casefold ile aranır')
eq(gorunen_ad_denetle('Ayşe Yılmaz', 'ayse@baska.invalid', _ad, 'bank.invalid'), [], 'kurum adı geçmeyen dış gönderen taklit değil')
eq(gorunen_ad_denetle('', 'x@baska.invalid', _ad, 'bank.invalid'), [], 'boş görünen ad')
eq(gorunen_ad_denetle('"guvenlik@bank.invalid"', 'x@baska.invalid', _ad, 'bank.invalid'), ['adres-gizleme'],
   'görünen ada yazılmış başka adres gizlemedir')
eq(gorunen_ad_denetle('Örnek Bank <guvenlik@bank.invalid>', 'x@baska.invalid', _ad, 'bank.invalid'),
   ['gorunen-ad-taklidi', 'adres-gizleme'], 'iki bulgu birlikte, sabit sırayla')
eq(gorunen_ad_denetle(' "Bildirim@Bank.Invalid" ', 'bildirim@bank.invalid', _ad, 'bank.invalid'), [],
   'görünen ad gerçek adresin kendisiyse (tırnak, boşluk, harf farkıyla) gizleme değil')
eq(gorunen_ad_denetle('Kredi Birimi', 'a@baska.invalid', ['Örnek Bank', 'Kredi Birimi'], 'bank.invalid'), ['gorunen-ad-taklidi'],
   'listedeki herhangi bir kurum adı yeter')

for _arg in (
    (None, 'a@b.invalid', _ad, 'bank.invalid'),
    ('Ad', 'ab.invalid', _ad, 'bank.invalid'),
    ('Ad', 'a@b@c.invalid', _ad, 'bank.invalid'),
    ('Ad', '@b.invalid', _ad, 'bank.invalid'),
    ('Ad', 'a@', _ad, 'bank.invalid'),
    ('Ad', 5, _ad, 'bank.invalid'),
    ('Ad', 'a@b.invalid', [], 'bank.invalid'),
    ('Ad', 'a@b.invalid', 'Örnek Bank', 'bank.invalid'),
    ('Ad', 'a@b.invalid', ('Örnek Bank',), 'bank.invalid'),
    ('Ad', 'a@b.invalid', ['Örnek Bank', ''], 'bank.invalid'),
    ('Ad', 'a@b.invalid', ['  '], 'bank.invalid'),
    ('Ad', 'a@b.invalid', [None], 'bank.invalid'),
    ('Ad', 'a@b.invalid', _ad, ''),
    ('Ad', 'a@b.invalid', _ad, '   '),
    ('Ad', 'a@b.invalid', _ad, None),
):
    raises(ValueError, gorunen_ad_denetle, *_arg, msg=f'bozuk girdi ValueError: {_arg!r}')
```

```hint
Gerçek alan adını `adres.split('@')` ile al ve iki parçanın da dolu olduğunu doğrula. Kurum adı aramasında iki tarafa da `casefold()` uygula; görünen addaki adresi karşılaştırmadan önce boşlukları ve çift tırnakları kırp.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Üslup kanıt değil (20 sn).** "Model akıcı Türkçe oltalama metni yazabildiği için 'dili düzgün' bir güven sinyali olmaktan çıktı. Kararı ayrıştırılmış meta veriye bağladık."
2. **Üç kanıt (30 sn).** "Gönderen alanı, DMARC sonucu ve bağlantının gerçek ana makinesi. Ana makineyi tam eşitlikle karşılaştırdık: kotubank, alt alan adı ve @ ile kandırılmış URL testte ayrı ayrı yakalanıyor."
3. **DMARC'ın kör noktası (30 sn).** "RFC 7489 görünen ad saldırılarını açıkça kapsam dışı bırakıyor. 'Örnek Bank Güvenlik' adıyla başka alandan gelen e-posta kendi alanı için DMARC'ı geçebilir."
4. **İkinci halka (25 sn).** "Görünen adda kurum adı geçip adres başka alandansa taklit; görünen ada başka bir adres yazılmışsa gizleme olarak işaretledik."
5. **Sınır (15 sn).** "Başlıklar önceden ayrıştırılmış; gerçek MIME ayrıştırma, DKIM ve DNS bu derste yok."
:::

::: anlat Sınır ve kaynak
Bu ders önceden ayrıştırılmış alanlarla çalışır. Gerçek e-postada başlık ayrıştırma kendisi bir saldırı yüzeyidir: kodlanmış sözcükler (RFC 2047), birden çok `From` başlığı, yorumlar ve Unicode benzeşmeleri (*homoglyph*) bu derste yoktur. Kurum adı araması alt dizge eşleşmesidir; "Bank" gibi genel bir ad yanlış pozitif üretir, gerçek sistemde kurum adları ve benzeşme listeleri dikkatle seçilir. RFC 7489'un sayfası, belgenin RFC 9989–9991 ile geçersiz kılındığını (*obsoleted*) belirtir; kapsam dışı bölümlere ilişkin ifadeler burada RFC 7489'dan alınmıştır.

- Birincil kaynaklar: [IETF RFC 7489 — DMARC](https://www.rfc-editor.org/rfc/rfc7489) (bölüm 3.1 Identifier Alignment; bölüm 2.2 ve 2.4 görünen ad saldırılarının kapsam dışı olması); [IETF RFC 5322 — Internet Message Format](https://www.rfc-editor.org/rfc/rfc5322) (bölüm 3.4, `display-name` ve `addr-spec`). Doğrulama tarihi: 11 Kasım 2026.
:::

::: dusun
Kurum, çalışanların dışarıdan gelen e-postalarında görünen adın yanına "[DIŞ]" etiketi ekliyor. Bu etiket görünen ad taklidine karşı neden yardımcı olur, adres gizlemeye karşı neden tek başına yetmez?
:::

::: ozet
- Akıcı metin oltalama için kanıt değildir; karar gönderen alanı, DMARC sonucu ve bağlantı hedefine dayanır.
- Ana makine ve alan adı karşılaştırması tam eşitlikle ve harf duyarsız yapılır.
- DMARC `From` alan adını doğrular; görünen adı denetlemez ve bunu kapsam dışı sayar.
- Görünen ad taklidi ve görünen ada gizlenmiş adres ayrı bir kontrolle yakalanır.
:::
