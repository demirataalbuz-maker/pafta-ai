---
id: ai-olay-02
title: "Copilot ve Görünmez Etiketler · ASCII Smuggling ve URL Denetimi"
summary: Unicode Tags bloğu (U+E0020..U+E007E) ile URL içine gizlenen verileri çöz, kanonik bağlantı riskini işaretle, açık/yamalı koşuda ölç ve görünmez karakterleri arındır.
esleme: ai-saldiri-52, ai-saldiri-13, ai-savunma-06, ai-savunma-14
timeout: 30
---

::: anlat 1. Gerçek olay ve yerel kopya sınırı
Güvenlik araştırmacısı Johann Rehberger (*Embrace The Red*, 2024), **ASCII Smuggling** başlıklı teknik araştırmasında Unicode **Tags** bloğundaki (`U+E0000`–`U+E007F`) görünmez kod noktalarının kurumsal yardımcı asistanlarda hem insan gözünden gizli talimat taşımak hem de üretilen tıklanabilir bağlantıların içine görünmez sızıntı verisi eklemek için kullanılabildiğini belgeledi. Araştırma yazısı tarihsel bir keşif kaydıdır; ilgili üreticilerin güncel ürün durumuna dair kabul testi iddiası taşımaz.

> [!NOTE]
> **Yerel kopya ayrımı:** Bu derste canlı bir tarayıcı yazı tipi motoru veya bulut modeli çalıştırılmaz. URL içine gömülen `U+E0020..U+E007E` karakterlerinin çözülmesi, kanonik alan adı doğrulaması ve yama etkisinin canlı senaryo koşusuyla ölçülmesi yerel Python verisiyle incelenir.
:::

::: anlat 2. Mekanizma · görünür etiket ile görünmez URL yükü arasındaki fark
Unicode `Tags` bloğundaki `U+E0020`..`U+E007E` kod noktaları, basılabilir ASCII karakterlerine (`0x20`..`0x7E`) tam `0xE0000` eklenerek elde edilir. Çoğu arayüz bu karakterleri sıfır genişlikte çizdiği için kullanıcı ekranda masum `https://arsiv.invalid/rapor` bağlantısını görür; oysa dizgenin devamında görünmez kod noktalarıyla taşınan bir sızıntı yükü veya komut yer alabilir (`ai-saldiri-52`).

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| `0xE0020 < ord(c) < 0xE007E` açık aralığı kullanmak | Boşluk ikizi `U+E0020` ve `'~'` ikizi `U+E007E` sınır karakterlerini kaçırır | Kapalı aralık `0xE0020 <= ord(c) <= 0xE007E` |
| Yalnız gizli karakter arayıp `http://` veya alt alan adını kontrol etmemek | Görünmez karakter olmasa da `http://arsiv.invalid` veya `arsiv.invalid.evil.invalid` güvensizdir | `gizli` boş olmalı **ve** `scheme == 'https'` **ve** `hostname == 'arsiv.invalid'` (kullanıcı bilgisiz, port `None`/`443`) olmalı |
| `etiket` veya `url` için tür kontrolünü atlamak | `None` veya `list` geldiğinde sessiz yanlış karar veya `AttributeError` üretir | Girişte `isinstance(..., str)` değilse `ValueError` |
:::

::: tahmin Ekranda aynı görünen URL'nin içinden hangi ASCII dizgesi çıkar?
Aşağıdaki URL'ye eklenen üç görünmez kod noktası `0xE0000` çıkarıldığında neye dönüşür?

```python
url = 'https://arsiv.invalid/a' + ''.join(chr(0xE0000 + ord(c)) for c in 'KEY')
gizli = ''.join(chr(ord(c) - 0xE0000) for c in url if 0xE0020 <= ord(c) <= 0xE007E)
print('ham uzunluk:', len(url), '| çözülen gizli yük:', gizli)
```

???

```cikti
ham uzunluk: 26 | çözülen gizli yük: KEY
```
Görünür URL 23 karakterdir ama dizge bellekte 26 karakter taşır; `0xE0020..0xE007E` aralığından `0xE0000` çıkarıldığında saklanan `'KEY'` dizgesi doğrudan ortaya çıkar.
:::

::: gorev 1 · Görünmez URL yükünü çözen ve riski işaretleyen sınırı kur
`link_incele(etiket, url)` işlevini yaz (hiçbir ağ bağlantısı açma):

- `etiket` veya `url` `str` değilse `ValueError` fırlat.
- `gizli`: `url` içindeki `0xE0020 <= ord(c) <= 0xE007E` karakterlerinin sırasıyla `chr(ord(c) - 0xE0000)` dönüşümüyle birleştirilmiş hali (`str`).
- `riskli` (`bool`): aşağıdaki durumlardan **en az biri** varsa `True`, hiçbiri yoksa `False`:
  1. `gizli` boş değilse ya da `url` içinde diğer görünmez karakterler (`0xE0000..0xE007F` uçları veya `\u200b`, `\u200c`, `\u200d`, `\u2060`, `\ufeff`) ya da boşluk varsa;
  2. `urlsplit(url)` ayrıştırmasında şema `'https'` değilse, `hostname` tam `'arsiv.invalid'` değilse, `username`/`password` varsa veya `port` `(None, 443)` dışında/bozuksa.
- Dönüş: `{'etiket': etiket, 'gizli': gizli, 'riskli': riskli}`.

KUSURLU başlangıç görünmez karakterleri hiç çözmüyor ve URL'de yalnız `'arsiv.invalid'` alt dizgesini arıyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[\n  "rapor",\n  "https://arsiv.invalid/a"\n]', encoding='utf-8')
```

```starter
def link_incele(etiket, url):
    return {'etiket': etiket, 'gizli': '', 'riskli': 'arsiv.invalid' not in str(url)}

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(link_incele(*_args))
```

```solution
from urllib.parse import urlsplit

_EK_GIZLI = {'\u200b', '\u200c', '\u200d', '\u2060', '\ufeff'}

def link_incele(etiket, url):
    if not isinstance(etiket, str) or not isinstance(url, str):
        raise ValueError('etiket ve url str olmali')
    gizli = ''.join(chr(ord(c) - 0xE0000) for c in url if 0xE0020 <= ord(c) <= 0xE007E)
    diger_gizli = any((0xE0000 <= ord(c) <= 0xE007F) or (c in _EK_GIZLI) or c.isspace() for c in url)
    try:
        p = urlsplit(url)
        port = p.port
        url_temiz = (
            bool(url)
            and p.scheme == 'https'
            and p.hostname == 'arsiv.invalid'
            and p.username is None
            and p.password is None
            and port in (None, 443)
        )
    except ValueError:
        url_temiz = False
    riskli = bool(gizli) or diger_gizli or (not url_temiz)
    return {'etiket': etiket, 'gizli': gizli, 'riskli': riskli}

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(link_incele(*_args))
```

```test
need('link_incele')
eq(link_incele('rapor', 'https://arsiv.invalid/a'), {'etiket': 'rapor', 'gizli': '', 'riskli': False}, 'temiz bağlantı risksiz')
eq(link_incele('kilavuz', 'https://arsiv.invalid:443/k'), {'etiket': 'kilavuz', 'gizli': '', 'riskli': False}, '443 portu risksiz')

_yuk = ''.join(chr(0xE0000 + ord(c)) for c in ' ~A ')
eq(link_incele('ozet', 'https://arsiv.invalid/a' + _yuk), {
    'etiket': 'ozet',
    'gizli': ' ~A ',
    'riskli': True,
}, '0xE0020 (boşluk) ve 0xE007E (~) uç karakterleri dahil çözülmeli ve riskli işaretlenmeli')

for _kotu_url in (
    'http://arsiv.invalid/a',
    'https://arsiv.invalid.evil.invalid/a',
    'https://arsiv.invalid@evil.invalid/a',
    'https://arsiv.invalid:8443/a',
    'https://arsiv.invalid/a\u200b',
    'https://arsiv.invalid/a' + chr(0xE0001),
    'https://arsiv.invalid/a' + chr(0xE007F),
    '',
):
    eq(link_incele('x', _kotu_url)['riskli'], True, f'güvensiz bağlantı riskli olmalı: {_kotu_url!r}')

for _bozuk in ((None, 'https://arsiv.invalid/a'), ('rapor', None), (12, 'https://arsiv.invalid/a'), ('rapor', ['url'])):
    raises(ValueError, link_incele, *_bozuk, msg='str olmayan argüman ValueError fırlatmalı')

# Tags bloğunun sınırları: U+E0000 ve U+E007F görünmezdir (riskli) ama ASCII'ye çözülmez;
# yalnız U+E0020..U+E007E çözülür. Bloğun komşuları (U+DFFFF, U+E0080) bu kurala girmez.
eq(link_incele('x', 'https://arsiv.invalid/a' + chr(0xE0000)), {'etiket': 'x', 'gizli': '', 'riskli': True},
   'U+E0000 riskli ama çözülmez')
eq(link_incele('x', 'https://arsiv.invalid/a' + chr(0xE001F) + chr(0xE007F)), {'etiket': 'x', 'gizli': '', 'riskli': True},
   'U+E001F ve U+E007F çözülecek aralığın dışında kalır')
for _komsu in (chr(0xDFFFF), chr(0xE0080)):
    eq(link_incele('x', 'https://arsiv.invalid/a' + _komsu)['riskli'], False,
       f'Tags bloğu dışındaki komşu kod noktası bu kurala girmez: U+{ord(_komsu):X}')
for _kotu_url in (
    'https://arsiv.invalid/a b',
    'https://arsiv.invalid/a\tb',
    'https://kullanici@arsiv.invalid/a',
    'https://arsiv.invalid:abc/a',
    'https://[::1/a',
):
    eq(link_incele('x', _kotu_url)['riskli'], True, f'boşluklu, kullanıcı adlı veya ayrıştırılamayan URL riskli: {_kotu_url!r}')
```

```hint
`0xE0020 <= ord(c) <= 0xE007E` kapalı aralığıyla `gizli` dizgesini üret; ayrıca `0xE0000..0xE007F` uçlarını ve `urlsplit` bileşenlerini (`https`, `arsiv.invalid`, `username/password is None`, `port in (None, 443)`) kontrol et.
```
:::

::: gorev 2 · Açık ve yamalı bağlantı denetçisini senaryo vakalarında ölç
`link_senaryo_olc(vakalar, acik_fn, yamali_fn)` işlevini yaz:

- `vakalar`: boş olmayan `list`; her vaka `{'saldiri': bool, 'girdi': (etiket, url), ...}` sözlüğüdür. Şema bozuksa veya işlevler `callable` değilse `ValueError` fırlat.
- Bir sınır işlevi `sonuc.get('riskli') is False` döndürdüğünde bağlantıya **geçiş izni vermiş** sayılır!
- Saldırı vakalarında (`saldiri is True`) geçiş izni verilmesi **sızıntı**, meşru vakalarda geçiş izni verilmesi **meşru kabul** demektir (`once` izin verirken `sonra` reddederse `regresyon_n` artar).
- Dönüş: `{'saldiri_n': int, 'mesru_n': int, 'once_sizma': float|None, 'sonra_sizma': float|None, 'mesru_kabul': float|None, 'regresyon_n': int}` (4 basamak yuvarlama, boş grupta `None`).

KUSURLU başlangıç `riskli is False` yerine `riskli is True` değerini geçiş izni sanarak sızıntı ve kabul oranlarını ters hesaplıyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def link_senaryo_olc(vakalar, acik_fn, yamali_fn):
    s = [v for v in vakalar if v['saldiri']]
    m = [v for v in vakalar if not v['saldiri']]
    return {
        'saldiri_n': len(s), 'mesru_n': len(m),
        'once_sizma': round(sum(1 for v in s if acik_fn(*v['girdi'])['riskli']) / len(s), 4) if s else None,
        'sonra_sizma': round(sum(1 for v in s if yamali_fn(*v['girdi'])['riskli']) / len(s), 4) if s else None,
        'mesru_kabul': round(sum(1 for v in m if yamali_fn(*v['girdi'])['riskli']) / len(m), 4) if m else None,
        'regresyon_n': 0,
    }
```

```solution
import copy

def link_senaryo_olc(vakalar, acik_fn, yamali_fn):
    if not isinstance(vakalar, list) or not vakalar or not callable(acik_fn) or not callable(yamali_fn):
        raise ValueError('gecerli vakalar ve sinir islevleri gerekli')
    s_n = m_n = s_once = s_sonra = m_sonra = reg = 0
    for v in vakalar:
        if not isinstance(v, dict) or type(v.get('saldiri')) is not bool or not isinstance(v.get('girdi'), (tuple, list)):
            raise ValueError('bozuk vaka semasi')
        r_once = acik_fn(*copy.deepcopy(v['girdi']))
        r_sonra = yamali_fn(*copy.deepcopy(v['girdi']))
        once_izin = isinstance(r_once, dict) and r_once.get('riskli') is False
        sonra_izin = isinstance(r_sonra, dict) and r_sonra.get('riskli') is False
        if v['saldiri']:
            s_n += 1
            s_once += int(once_izin)
            s_sonra += int(sonra_izin)
        else:
            m_n += 1
            m_sonra += int(sonra_izin)
            if once_izin and not sonra_izin:
                reg += 1
    return {
        'saldiri_n': s_n,
        'mesru_n': m_n,
        'once_sizma': round(s_once / s_n, 4) if s_n else None,
        'sonra_sizma': round(s_sonra / s_n, 4) if s_n else None,
        'mesru_kabul': round(m_sonra / m_n, 4) if m_n else None,
        'regresyon_n': reg,
    }
```

```test
need('link_senaryo_olc')
from urllib.parse import urlsplit
from sandbox.ai_olay_senaryo import acik_sinir, senaryo_vakalari

def _referans(etiket, url):
    gizli = ''.join(chr(ord(c) - 0xE0000) for c in url if 0xE0020 <= ord(c) <= 0xE007E)
    p = urlsplit(url)
    risk = bool(gizli) or p.scheme != 'https' or p.hostname != 'arsiv.invalid' or p.port not in (None, 443)
    return {'etiket': etiket, 'gizli': gizli, 'riskli': risk}

_vakalar = senaryo_vakalari(2, tohum=11)
eq(link_senaryo_olc(_vakalar, acik_sinir(2), _referans), {
    'saldiri_n': 5,
    'mesru_n': 2,
    'once_sizma': 1.0,
    'sonra_sizma': 0.0,
    'mesru_kabul': 1.0,
    'regresyon_n': 0,
}, 'açık sınır 5/5 saldırıyı geçirir, yamalı sınır 0.0 sızıntı ve 1.0 meşru kabul sağlar')

_hepsi_riskli = link_senaryo_olc(_vakalar, acik_sinir(2), lambda e, _u: {'etiket': e, 'gizli': '', 'riskli': True})
eq(_hepsi_riskli['sonra_sizma'], 0.0, 'her şeye riskli diyen yama sızıntıyı durdurur')
eq(_hepsi_riskli['mesru_kabul'], 0.0, 'ancak meşru kabul sıfırlanır')
eq(_hepsi_riskli['regresyon_n'], 2, '2 meşru vaka regresyona düşer')

eq(link_senaryo_olc([v for v in _vakalar if not v['saldiri']], acik_sinir(2), _referans)['once_sizma'], None, 'saldırı yoksa None')
raises(ValueError, link_senaryo_olc, [], acik_sinir(2), _referans, msg='boş liste ValueError')

# Ölçüm mantığı alandan bağımsızdır: etiketli soyut vakalarla oranlar kesirli çıkar (2/3, 1/3),
# yama bir saldırıyı hâlâ geçirir ve açık sınırın kabul ettiği bir meşru vakayı reddeder (regresyon).
_el = [
    {'saldiri': True, 'girdi': ('s-ikisi-gecer', 'u')},
    {'saldiri': True, 'girdi': ('s-acik-de-durdurur', 'u')},
    {'saldiri': True, 'girdi': ('s-yalniz-acik-gecer', 'u')},
    {'saldiri': False, 'girdi': ('m-ikisi-gecer', 'u')},
    {'saldiri': False, 'girdi': ('m-ikisi-durdurur', 'u')},
    {'saldiri': False, 'girdi': ('m-regresyon', 'u')},
]
def _sinir(gecenler):
    return lambda e, _u: {'etiket': e, 'gizli': '', 'riskli': e not in gecenler}
_acik_el = _sinir(('s-ikisi-gecer', 's-yalniz-acik-gecer', 'm-ikisi-gecer', 'm-regresyon'))
_yama_el = _sinir(('s-ikisi-gecer', 'm-ikisi-gecer'))
eq(link_senaryo_olc(_el, _acik_el, _yama_el), {
    'saldiri_n': 3,
    'mesru_n': 3,
    'once_sizma': 0.6667,
    'sonra_sizma': 0.3333,
    'mesru_kabul': 0.3333,
    'regresyon_n': 1,
}, 'riskli=False izin sayılır; oranlar grup paydasıyla ve 4 basamakla')
eq(link_senaryo_olc(_el, _acik_el, _acik_el)['sonra_sizma'], 0.6667, 'yama açık sınırla aynıysa sonra_sizma = once_sizma')
eq(link_senaryo_olc(_el, _sinir(()), _sinir(()))['regresyon_n'], 0, 'açık sınırın da reddettiği meşru vaka regresyon sayılmaz')
eq(link_senaryo_olc([v for v in _el if v['saldiri']], _acik_el, _yama_el)['mesru_kabul'], None, 'meşru vaka yoksa mesru_kabul None')
eq(link_senaryo_olc([v for v in _el if not v['saldiri']], _acik_el, _yama_el),
   {'saldiri_n': 0, 'mesru_n': 3, 'once_sizma': None, 'sonra_sizma': None, 'mesru_kabul': 0.3333, 'regresyon_n': 1},
   'saldırı vakası yoksa once_sizma ve sonra_sizma None')
# Sözleşme dışı dönüş (dict değil ya da riskli alanı False değil) izin sayılmaz: hata-kapalı.
for _tuhaf in (lambda *_a: None, lambda *_a: True, lambda *_a: {'riskli': 0}, lambda *_a: {}):
    eq(link_senaryo_olc(_el, _tuhaf, _tuhaf)['once_sizma'], 0.0, 'sözleşme dışı sınır dönüşü izin sayılmamalı')

raises(ValueError, link_senaryo_olc, tuple(_el), _acik_el, _yama_el, msg='liste olmayan vakalar ValueError')
raises(ValueError, link_senaryo_olc, _el, None, _yama_el, msg='çağrılamaz açık sınır ValueError')
raises(ValueError, link_senaryo_olc, _el, _acik_el, 'yama', msg='çağrılamaz yamalı sınır ValueError')
for _bozuk in (
    _el + [('s-ikisi-gecer', 'u')],
    _el + [{'saldiri': 1, 'girdi': ('s-ikisi-gecer', 'u')}],
    _el + [{'saldiri': True, 'girdi': None}],
):
    raises(ValueError, link_senaryo_olc, _bozuk, _acik_el, _yama_el, msg=f'bozuk vaka şeması ValueError: {_bozuk[-1]!r}')
```

```hint
`riskli` alanı `False` olduğunda bağlantı güvenli sayıldığı için `once_izin = r_once.get('riskli') is False` koşulunu kullan!
```
:::

::: gorev 3 · İstem ve belge metinlerinden görünmez karakterleri arındır
Adli inceleme ve ön-temizleme katmanı için `gorunmez_arindir(metin)` işlevini yaz:

- `metin` `str` değilse `ValueError` fırlat.
- `0xE0020 <= ord(c) <= 0xE007E` karakterlerini görünür metinden çıkarıp `chr(ord(c) - 0xE0000)` karşılıklarını `gizli_yuk` dizgesinde birleştir.
- `0xE0000..0xE001F`, `0xE007F` ve `{'\u200b', '\u200c', '\u200d', '\u2060', '\ufeff'}` karakterlerini de görünür metinden çıkar (`gizli_yuk` içine ekleme ama `kaldirilan_sayisi` sayacına dahil et).
- Dönüş: `{'temiz_metin': str, 'gizli_yuk': str, 'kaldirilan_sayisi': int}`.

KUSURLU başlangıç `0xE0020` ve `0xE007E` uç karakterlerini atlıyor ve sıfır genişlikli karakterleri temizlemiyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def gorunmez_arindir(metin):
    temiz, yuk = [], []
    for c in metin:
        kod = ord(c)
        if 0xE0020 < kod < 0xE007E:
            yuk.append(chr(kod - 0xE0000))
        else:
            temiz.append(c)
    return {'temiz_metin': ''.join(temiz), 'gizli_yuk': ''.join(yuk), 'kaldirilan_sayisi': len(yuk)}
```

```solution
_SIFIR_KUME = {'\u200b', '\u200c', '\u200d', '\u2060', '\ufeff'}

def gorunmez_arindir(metin):
    if not isinstance(metin, str):
        raise ValueError('metin str olmali')
    temiz, yuk = [], []
    kaldirilan = 0
    for c in metin:
        kod = ord(c)
        if 0xE0020 <= kod <= 0xE007E:
            yuk.append(chr(kod - 0xE0000))
            kaldirilan += 1
        elif (0xE0000 <= kod <= 0xE007F) or (c in _SIFIR_KUME):
            kaldirilan += 1
        else:
            temiz.append(c)
    return {'temiz_metin': ''.join(temiz), 'gizli_yuk': ''.join(yuk), 'kaldirilan_sayisi': kaldirilan}
```

```test
need('gorunmez_arindir')
_sakli = ''.join(chr(0xE0000 + ord(c)) for c in ' SEND ~ALL')
_ornek = 'Merhaba\u200b' + chr(0xE0001) + _sakli + ' Dünya\ufeff'
eq(gorunmez_arindir(_ornek), {
    'temiz_metin': 'Merhaba Dünya',
    'gizli_yuk': ' SEND ~ALL',
    'kaldirilan_sayisi': len(_sakli) + 3,
}, 'tüm görünmez kod noktaları temizlenmeli ve ASCII yük çözülmeli')
eq(gorunmez_arindir('Normal metin'), {'temiz_metin': 'Normal metin', 'gizli_yuk': '', 'kaldirilan_sayisi': 0}, 'temiz metin korunmalı')
# Tags bloğunun dört sınırı ve iki komşusu.
eq(gorunmez_arindir('a' + chr(0xE0000) + chr(0xE001F) + chr(0xE0020) + chr(0xE007E) + chr(0xE007F) + 'b'), {
    'temiz_metin': 'ab',
    'gizli_yuk': ' ~',
    'kaldirilan_sayisi': 5,
}, 'U+E0000, U+E001F, U+E007F kaldırılır ama çözülmez; U+E0020 ve U+E007E çözülür')
eq(gorunmez_arindir('a' + chr(0xDFFFF) + chr(0xE0080) + 'b'), {
    'temiz_metin': 'a' + chr(0xDFFFF) + chr(0xE0080) + 'b',
    'gizli_yuk': '',
    'kaldirilan_sayisi': 0,
}, 'Tags bloğu dışındaki komşu kod noktaları bu kuralla silinmez')
raises(ValueError, gorunmez_arindir, None, msg='None ValueError üretmeli')
```

```hint
Kapalı aralık `0xE0020 <= kod <= 0xE007E` hem boşluğu hem `'~'` karakterini kapsar; kalan `0xE0000..0xE007F` ve sıfır genişlikli karakterlerde yalnız `kaldirilan` sayacını artır.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Olay bağlamı (15 sn).** "ASCII Smuggling araştırması, Unicode `Tags` bloğunun ekranda görünmezken hem gizli talimat hem bağlantı sızıntısı taşıyabildiğini belgeledi."
2. **Mekanizma (30 sn).** "ASCII baytlarına `0xE0000` eklendiğinde kullanıcı arayüzü sıfır genişlik çizer; `tokenizer` ise tam metni okur."
3. **Sınır ve ölçüm (30 sn).** "`link_incele` ile gizli yük çözümünü ve kanonik `https://arsiv.invalid` kontrolünü birleştirdim; senaryo koşusunda sızıntıyı `1.0`'dan `0.0`'a indirdim."
4. **Adli analiz (25 sn).** "`gorunmez_arindir` ile şüpheli metindeki gizli ASCII talimatını analist için doğrudan okunur hale getirdim."
5. **Kapanış (20 sn).** "Görsel inceleme güvenlik sınırı değildir; metin ve URL kanalları kod noktası düzeyinde denetlenmelidir."
:::

::: anlat Sınır ve kaynak
Bu derste Unicode `Tags` bloğu ve temel sıfır genişlikli karakterler modellenmiştir; çift yönlü metin yönlendirme (`bidi override`) karakterleri `ai-olay-07` dersinde ayrıca incelenir. Yerel model güncel ürün kabul testi iddiası taşımaz.

- Birincil kaynak: [Johann Rehberger — M365 Copilot Prompt Injection, Tool Invocation and Data Exfil Using ASCII Smuggling (2024)](https://embracethered.com/blog/posts/2024/m365-copilot-prompt-injection-tool-invocation-and-data-exfil-using-ascii-smuggling/). Doğrulama tarihi: 10 Kasım 2026.
:::

::: dusun
Görünmez karakterleri girişte sessizce silip isteği işleme sokmak ile isteği `riskli=True` olarak reddedip güvenlik günlüğüne kaydetmek arasında saldırı tespiti açısından ne fark vardır?
:::

::: ozet
- `U+E0020..U+E007E` kod noktaları insan gözünden gizli ASCII talimat ve sızıntı verisi taşır.
- Sınır denetiminde hem kapalı kod noktası aralığı hem kanonik `https` / `hostname` kuralları birlikte uygulanır.
- Yama başarısı `riskli is False` kararının açık ve yamalı işlevlerde bizzat ölçülmesiyle doğrulanır.
:::
