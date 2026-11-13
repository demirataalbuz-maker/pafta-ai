---
id: ai-olay-14
title: "Mart 2023 Önbellek Olayı · İptal Edilen İstek ve Kiracı İzolasyonu"
summary: OpenAI Mart 2023 Redis/asyncio olay raporuna dayanarak iptal edilen istek kuyruğunda sahip (owner) doğrulamasını, canlı senaryo ölçümünü ve zarf bağlamasını kur.
esleme: ai-saldiri-39, ai-savunma-19, ai-savunma-04, ai-savunma-25
timeout: 30
---

::: anlat 1. Gerçek olay ve yerel kopya sınırı
Mart 2023'te **OpenAI**, ChatGPT'yi geçici olarak kapattığı kesintinin resmi olay sonrası raporunda (*postmortem*) çok kiracılı bir önbellek/kuyruk hatasını ayrıntılı biçimde paylaştı: `redis-py` istemcisi `asyncio` altında paylaşımlı bağlantı havuzuyla kullanılırken bir `async` istek iptal edildiğinde (`cancelled`), bağlantı üzerindeki okunmamış yanıt baytları kuyrukta kalıyor ve aynı bağlantıyı devralan **bir sonraki farklı kullanıcının** isteğine önceki kullanıcının önbellek verisi (sohbet başlıkları / sınırlı hesap bilgileri) dönebiliyordu.

> [!NOTE]
> **Yerel kopya ayrımı:** Bu ders Redis sunucusu veya `asyncio` soketi çalıştırmaz. Paylaşımlı bir yanıt kuyruğunda **iptal durumu (`cancelled is False`)** ve **kiracı sahipliği (`owner == beklenen`)** uygulama katmanında doğrulanmadığında neden çapraz kiracı sızıntısı oluştuğunu yerel Python modeliyle inceler.
:::

::: anlat 2. Mekanizma · sıra tabanlı kuyruk varsayımı neden kiracı sınırını deler?
Yüksek eşzamanlı sunucularda bağlantı havuzu "gönderdiğim 1. sorgunun yanıtı kuyruktan okuduğum 1. pakettir" varsayımı yapar. İstek zaman aşımı veya kullanıcı iptali yüzünden yarıda kesildiğinde (`cancelled=True`) bu birebir eşleşme kayar (`desynchronization`) (`ai-saldiri-39`, `ai-savunma-19`).

Savunma, bağlantının sırasına körü körüne güvenmek yerine dönen verinin **kendi içindeki zarf kimliğini (`envelope binding`)** doğrular:
1. Kuyruktan okunan kaydın `owner` alanı çağıran kullanıcıyla birebir eşleşmelidir.
2. `cancelled` alanı **tam olarak `False` (`is False`)** olmalıdır: `not r.get('cancelled')` yazmak tehlikelidir çünkü `'cancelled'` anahtarı hiç olmayan (`None`) veya `0` olan bozuk bir kaydı geçerli sanır!

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| Kuyruğun başındaki ilk kaydı sahibine bakmadan döndürmek | Önceki iptalden kalan başka kiracının kaydını sızdırır | `r.get('owner') == owner` açık sahip eşlemesi |
| `if not r.get('cancelled'):` kullanmak | `'cancelled'` alanı eksik (`None`) veya `0` olan bozuk kayıtları temiz kabul eder | `r.get('cancelled') is False` tam kimlik kontrolü |
| Kuyruk listesini `.pop(0)` ile yerinde tüketmek | Çağıran katmanın denetim/tekrar oynatma listesini bozar | Kuyruğu değiştirmeden (`read-only`) taramak |
:::

::: tahmin Eksik `'cancelled'` anahtarı `not r.get('cancelled')` kontrolünü nasıl yanıltır?
Bozuk bir önbellek kaydında `'cancelled'` alanı hiç yazılmamışsa iki kontrol arasındaki fark nedir?

```python
bozuk_kayit = {'owner': 'ayse', 'value': 'YARIM_VERI'}
gevsek = not bozuk_kayit.get('cancelled')
siki = bozuk_kayit.get('cancelled') is False
print('not get("cancelled"):', gevsek)
print('is False kontrolü:', siki)
```

???

```cikti
not get("cancelled"): True
is False kontrolü: False
```
`bozuk_kayit.get('cancelled')` `None` döndürür ve `not None` ifadesi `True` olur! Çok kiracılı önbelleklerde eksik durum bayrağı hiçbir zaman "iptal edilmedi" anlamına gelmez; `is False` ile kesin doğrulama yapılır.
:::

::: gorev 1 · Kiracı ve iptal doğrulamalı `cache_oku` sınırını kur
`cache_oku(kuyruk, owner)` işlevini yaz:

- `kuyruk` bir `list` değilse `ValueError` fırlat.
- `owner` boş olmayan `str` değilse (ör. `''` veya `None`) `None` döndür.
- `kuyruk` listesini **değiştirmeden** sırayla tara; bozuk öğeleri (`dict` olmayan, `'owner'`/`'value'` alanı `str` olmayan, `'cancelled'` alanı eksik veya `bool` olmayan) istisna fırlatmadan atla.
- `r.get('owner') == owner`, `isinstance(r.get('value'), str)` ve `r.get('cancelled') is False` koşullarının tümünü sağlayan **ilk** kaydın `value` dizgesini döndür; uygun kayıt yoksa `None` döndür.

KUSURLU başlangıç sahip kontrolü yapmıyor ve `not r.get('cancelled')` kullandığı için eksik bayraklı kayıtları kabul ediyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[\n  [\n    {\n      "owner": "a",\n      "value": "CANARY-A",\n      "cancelled": false\n    },\n    {\n      "owner": "b",\n      "value": "B",\n      "cancelled": false\n    }\n  ],\n  "b"\n]', encoding='utf-8')
```

```starter
def cache_oku(kuyruk, owner):
    for r in kuyruk:
        if isinstance(r, dict) and not r.get('cancelled'):
            return r.get('value')
    return None

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(cache_oku(*_args))
```

```solution
def cache_oku(kuyruk, owner):
    if not isinstance(kuyruk, list):
        raise ValueError('kuyruk list olmali')
    if not isinstance(owner, str) or not owner:
        return None
    for kayit in kuyruk:
        if (
            isinstance(kayit, dict)
            and isinstance(kayit.get('owner'), str)
            and kayit['owner'] == owner
            and isinstance(kayit.get('value'), str)
            and kayit.get('cancelled') is False
        ):
            return kayit['value']
    return None

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(cache_oku(*_args))
```

```test
need('cache_oku')
import copy

_kuyruk = [
    {'owner': 'a', 'value': 'CANARY-A', 'cancelled': False},
    {'owner': 'b', 'value': 'IPTAL-B', 'cancelled': True},
    {'owner': 'b', 'value': 'TEMIZ-B', 'cancelled': False},
]
_yedek = copy.deepcopy(_kuyruk)
eq(cache_oku(_kuyruk, 'b'), 'TEMIZ-B', 'başka kullanıcının ve iptal edilen kaydın üzerinden atlayıp TEMIZ-B dönmeli')
eq(_kuyruk, _yedek, 'kuyruk listesi değişmemeli')

eq(cache_oku([{'owner': 'b', 'value': 'EKSIK-BAYRAK'}], 'b'), None, 'cancelled anahtarı eksik kayıt kabul edilmemeli')
eq(cache_oku([{'owner': 'b', 'value': 'SIFIR-INT', 'cancelled': 0}], 'b'), None, 'cancelled=0 bool False değildir')
eq(cache_oku(['bozuk-eleman', {'owner': 'b', 'value': 123, 'cancelled': False}, {'owner': 'b', 'value': 'OK', 'cancelled': False}], 'b'), 'OK', 'bozuk kayıtlar atlanıp ilk geçerli kayıt dönmeli')
eq(cache_oku(_kuyruk, ''), None, 'boş owner None dönmeli')
eq(cache_oku([{'owner': '', 'value': 'BOS-SAHIP', 'cancelled': False}], ''), None, 'kuyrukta boş owner bulunsa bile boş aranan owner eşleşmemeli')
eq(cache_oku(_kuyruk, None), None, 'None owner None dönmeli')

for _bozuk_kuyruk in (None, 'kuyruk', {'owner': 'a'}, ('x',)):
    raises(ValueError, cache_oku, _bozuk_kuyruk, 'b', msg='list olmayan kuyruk ValueError fırlatmalı')
eq(cache_oku([{'value': 'SAHIPSIZ', 'cancelled': False}, {'owner': 'b', 'value': 'OK', 'cancelled': False}], 'b'), 'OK',
   'owner anahtarı olmayan kayıt hata fırlatmadan atlanmalı')
```

```hint
`isinstance(kuyruk, list)` kontrolünden sonra döngüde `kayit.get('owner') == owner`, `isinstance(kayit.get('value'), str)` ve `kayit.get('cancelled') is False` şartlarını birlikte ara.
```
:::

::: gorev 2 · Açık ve yamalı önbellek okuyucusunu senaryo vakalarında ölç
`cache_senaryo_olc(vakalar, acik_fn, yamali_fn)` işlevini yaz:

- Her vaka `{'saldiri': bool, 'girdi': (kuyruk, owner), 'beklenen': str|None}` sözlüğüdür. Şema veya çağrılabilirlik bozuksa `ValueError` fırlat.
- Saldırı vakasında (`saldiri is True`), sınır işlevinin döndürdüğü değer `sonuc != v['beklenen']` ise başka kiracının veya bozuk/iptal kaydın verisi sızmıştır (**`sizma`**).
- Meşru vakada (`saldiri is False`), `sonuc == v['beklenen']` ise hizmet doğru çalışmıştır (**`mesru_kabul`**).
- Dönüş: `{'saldiri_n': int, 'mesru_n': int, 'once_sizma': float|None, 'sonra_sizma': float|None, 'mesru_kabul': float|None, 'regresyon_n': int}`.

KUSURLU başlangıç `v['beklenen']` ile karşılaştırmak yerine `sonuc is not None` kontrolü yaptığı için yanlış kiracının verisi döndüğünde bile meşru sayıyor veya `None` beklenen boş kuyrukta hata yapıyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def cache_senaryo_olc(vakalar, acik_fn, yamali_fn):
    s = [v for v in vakalar if v['saldiri']]
    m = [v for v in vakalar if not v['saldiri']]
    return {
        'saldiri_n': len(s), 'mesru_n': len(m),
        'once_sizma': round(sum(1 for v in s if acik_fn(*v['girdi']) is not None) / len(s), 4) if s else None,
        'sonra_sizma': round(sum(1 for v in s if yamali_fn(*v['girdi']) is not None) / len(s), 4) if s else None,
        'mesru_kabul': round(sum(1 for v in m if yamali_fn(*v['girdi']) is not None) / len(m), 4) if m else None,
        'regresyon_n': 0,
    }
```

```solution
import copy

def cache_senaryo_olc(vakalar, acik_fn, yamali_fn):
    if not isinstance(vakalar, list) or not vakalar or not callable(acik_fn) or not callable(yamali_fn):
        raise ValueError('gecerli vakalar ve cagrilaiblir sinirlar gerekli')
    s_n = m_n = s_once = s_sonra = m_sonra = reg = 0
    for v in vakalar:
        if (not isinstance(v, dict) or type(v.get('saldiri')) is not bool
                or not isinstance(v.get('girdi'), (tuple, list)) or 'beklenen' not in v):
            raise ValueError('bozuk vaka semasi')
        beklenen = v['beklenen']
        r_once = acik_fn(*copy.deepcopy(v['girdi']))
        r_sonra = yamali_fn(*copy.deepcopy(v['girdi']))
        if v['saldiri']:
            s_n += 1
            s_once += int(r_once != beklenen)
            s_sonra += int(r_sonra != beklenen)
        else:
            m_n += 1
            once_dogru = (r_once == beklenen)
            sonra_dogru = (r_sonra == beklenen)
            m_sonra += int(sonra_dogru)
            if once_dogru and not sonra_dogru:
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
need('cache_senaryo_olc')
from sandbox.ai_olay_senaryo import acik_sinir, senaryo_vakalari

def _yama(kuyruk, owner):
    for r in kuyruk:
        if isinstance(r, dict) and r.get('owner') == owner and isinstance(r.get('value'), str) and r.get('cancelled') is False:
            return r['value']
    return None

_vakalar = senaryo_vakalari(14, tohum=14)
eq(cache_senaryo_olc(_vakalar, acik_sinir(14), _yama), {
    'saldiri_n': 3,
    'mesru_n': 2,
    'once_sizma': 1.0,
    'sonra_sizma': 0.0,
    'mesru_kabul': 1.0,
    'regresyon_n': 0,
}, 'açık okuyucu çapraz kiracı/eksik iptal vakalarının 3/3 tanesinde yanlış veri döndürür; yama 0.0 yapar')

eq(cache_senaryo_olc(_vakalar, acik_sinir(14), lambda _k, _o: 'SABIT')['regresyon_n'], 2, 'boş kuyruk ve doğru yanıt bozulduğunda 2 regresyon sayılmalı')
raises(ValueError, cache_senaryo_olc, [{'saldiri': True, 'girdi': ([], 'a')}], acik_sinir(14), _yama, msg='beklenen alanı eksik vaka reddedilmeli')
raises(ValueError, cache_senaryo_olc, [], acik_sinir(14), _yama, msg='boş vaka listesi ValueError')
raises(ValueError, cache_senaryo_olc, _vakalar, acik_sinir(14), None, msg='çağrılamayan sınır ValueError')

# Ölçüm mantığı alandan bağımsızdır: saldırıda beklenenden farklı yanıt sızıntıdır; meşru vakada
# yalnız beklenen yanıt doğrudur.
_el = [
    {'saldiri': True, 'girdi': ([], 's-ikisi-gecer'), 'beklenen': 'DOGRU'},
    {'saldiri': True, 'girdi': ([], 's-acik-de-durdurur'), 'beklenen': 'DOGRU'},
    {'saldiri': True, 'girdi': ([], 's-yalniz-acik-gecer'), 'beklenen': 'DOGRU'},
    {'saldiri': False, 'girdi': ([], 'm-ikisi-gecer'), 'beklenen': 'DOGRU'},
    {'saldiri': False, 'girdi': ([], 'm-ikisi-durdurur'), 'beklenen': 'DOGRU'},
    {'saldiri': False, 'girdi': ([], 'm-regresyon'), 'beklenen': 'DOGRU'},
]
def _sinir(gecenler):
    def _f(_k, etiket):
        if etiket.startswith('s-'):
            return 'SIZINTI' if etiket in gecenler else 'DOGRU'
        return 'DOGRU' if etiket in gecenler else None
    return _f
_acik_el = _sinir(('s-ikisi-gecer', 's-yalniz-acik-gecer', 'm-ikisi-gecer', 'm-regresyon'))
_yama_el = _sinir(('s-ikisi-gecer', 'm-ikisi-gecer'))
eq(cache_senaryo_olc(_el, _acik_el, _yama_el), {
    'saldiri_n': 3,
    'mesru_n': 3,
    'once_sizma': 0.6667,
    'sonra_sizma': 0.3333,
    'mesru_kabul': 0.3333,
    'regresyon_n': 1,
}, 'oranlar grup paydasıyla ve 4 basamakla; sıfırdan farklı sonra_sizma ve regresyon doğru sayılmalı')
eq(cache_senaryo_olc(_el, _acik_el, _acik_el)['sonra_sizma'], 0.6667, 'yama açık sınırla aynıysa sonra_sizma = once_sizma')
eq(cache_senaryo_olc(_el, _sinir(()), _sinir(()))['regresyon_n'], 0, 'açık sınırın da yanlış yanıtladığı meşru vaka regresyon sayılmaz')
eq(cache_senaryo_olc([v for v in _el if v['saldiri']], _acik_el, _yama_el)['mesru_kabul'], None, 'meşru vaka yoksa mesru_kabul None')
eq(cache_senaryo_olc([v for v in _el if not v['saldiri']], _acik_el, _yama_el),
   {'saldiri_n': 0, 'mesru_n': 3, 'once_sizma': None, 'sonra_sizma': None, 'mesru_kabul': 0.3333, 'regresyon_n': 1},
   'saldırı vakası yoksa once_sizma ve sonra_sizma None')
raises(ValueError, cache_senaryo_olc, tuple(_el), _acik_el, _yama_el, msg='liste olmayan vakalar ValueError')
raises(ValueError, cache_senaryo_olc, _el, None, _yama_el, msg='çağrılamaz açık sınır ValueError')
for _bozuk in (
    _el + [([], 's-ikisi-gecer')],
    _el + [{'saldiri': 1, 'girdi': ([], 's-ikisi-gecer'), 'beklenen': 'DOGRU'}],
    _el + [{'saldiri': True, 'girdi': None, 'beklenen': 'DOGRU'}],
):
    raises(ValueError, cache_senaryo_olc, _bozuk, _acik_el, _yama_el, msg=f'bozuk vaka şeması ValueError: {_bozuk[-1]!r}')
```

```hint
Karşılaştırma ölçütü `r_sonra == v['beklenen']` olmalıdır: saldırı vakalarında eşitsizlik (`!=`) sızıntıyı, meşru vakalarda eşitlik (`==`) kabulü gösterir (boş kuyrukta `None == None` dahil!).
```
:::

::: gorev 3 · İstek-yanıt zarf bağlamasını (`envelope binding`) ve bağlantı sıfırlama kararını kur
Gerçek bağlantı havuzlarında kuyrukta yabancı veya iptal edilmiş bir paket görüldüğünde yalnız o paketi atlamak yetmez; **bağlantı kirlenmiş (`desynchronized`)** kabul edilip havuzdan atılmalıdır! `zarf_dogrula(zarf, beklenen_owner, beklenen_istek_id)` işlevini yaz:

- `beklenen_owner` ve `beklenen_istek_id` boş olmayan `str` olmalı; değilse `ValueError` fırlat.
- `zarf` bir `dict` olmalı ve `'owner'` (`str`), `'istek_id'` (`str`), `'cancelled'` (`bool`), `'veri'` (`str`) alanlarını eksiksiz taşımalı. Şema eksik/bozuksa `{'gecerli': False, 'veri': None, 'baglantiyi_kapat': True}` döndür.
- `zarf['owner'] == beklenen_owner`, `zarf['istek_id'] == beklenen_istek_id` ve `zarf['cancelled'] is False` ise `{'gecerli': True, 'veri': zarf['veri'], 'baglantiyi_kapat': False}` döndür.
- Herhangi bir uyuşmazlıkta (farklı `owner`, farklı `istek_id` veya `cancelled is True`) veriyi sızdırma ve kirlenen bağlantının kapatılmasını iste: `{'gecerli': False, 'veri': None, 'baglantiyi_kapat': True}`.

KUSURLU başlangıç `istek_id` alanını karşılaştırmadığı için aynı kullanıcının iptal edilmiş eski sekmesinden kalan yanıtı yeni sekmesine karıştırıyor ve bağlantıyı açık bırakıyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def zarf_dogrula(zarf, beklenen_owner, beklenen_istek_id):
    if isinstance(zarf, dict) and zarf.get('owner') == beklenen_owner and not zarf.get('cancelled'):
        return {'gecerli': True, 'veri': zarf.get('veri'), 'baglantiyi_kapat': False}
    return {'gecerli': False, 'veri': None, 'baglantiyi_kapat': False}
```

```solution
def zarf_dogrula(zarf, beklenen_owner, beklenen_istek_id):
    if not isinstance(beklenen_owner, str) or not beklenen_owner.strip() or not isinstance(beklenen_istek_id, str) or not beklenen_istek_id.strip():
        raise ValueError('beklenen_owner ve beklenen_istek_id bos olmayan str olmali')
    if (
        isinstance(zarf, dict)
        and isinstance(zarf.get('owner'), str)
        and isinstance(zarf.get('istek_id'), str)
        and type(zarf.get('cancelled')) is bool
        and isinstance(zarf.get('veri'), str)
        and zarf['owner'] == beklenen_owner
        and zarf['istek_id'] == beklenen_istek_id
        and zarf['cancelled'] is False
    ):
        return {'gecerli': True, 'veri': zarf['veri'], 'baglantiyi_kapat': False}
    return {'gecerli': False, 'veri': None, 'baglantiyi_kapat': True}
```

```test
need('zarf_dogrula')
eq(zarf_dogrula({'owner': 'ayse', 'istek_id': 'req-42', 'cancelled': False, 'veri': 'Merhaba'}, 'ayse', 'req-42'), {
    'gecerli': True, 'veri': 'Merhaba', 'baglantiyi_kapat': False,
}, 'tam eşleşen zarf veriyi döndürmeli ve bağlantıyı korumalı')

for _bozuk_zarf in (
    {'owner': 'burak', 'istek_id': 'req-42', 'cancelled': False, 'veri': 'Gizli'},
    {'owner': 'ayse', 'istek_id': 'req-41', 'cancelled': False, 'veri': 'Eski istek'},
    {'owner': 'ayse', 'istek_id': 'req-42', 'cancelled': True, 'veri': 'İptal'},
    {'owner': 'ayse', 'istek_id': 'req-42', 'cancelled': 0, 'veri': 'Sayısal'},
    {'owner': 'ayse', 'istek_id': 'req-42', 'veri': 'Eksik bayrak'},
    None,
):
    eq(zarf_dogrula(_bozuk_zarf, 'ayse', 'req-42'), {
        'gecerli': False, 'veri': None, 'baglantiyi_kapat': True,
    }, f'uyumsuz veya bozuk zarfta veri None olmalı ve bağlantı kapatılmalı: {_bozuk_zarf!r}')

for _hatali in (({}, '', 'req-1'), ({}, 'ayse', ''), ({}, None, 'req-1'), ({}, 'ayse', None), ({}, 'ayse', '   ')):
    raises(ValueError, zarf_dogrula, *_hatali, msg=f'boş veya str olmayan beklenen kimlikler ValueError: {_hatali[1:]!r}')

# Eksik anahtarlı ya da str olmayan veri taşıyan zarf hata fırlatmadan reddedilir.
for _bozuk_zarf in (
    {'istek_id': 'req-42', 'cancelled': False, 'veri': 'Sahipsiz'},
    {'owner': 'ayse', 'cancelled': False, 'veri': 'Kimliksiz'},
    {'owner': 'ayse', 'istek_id': 'req-42', 'cancelled': False, 'veri': 123},
    {'owner': 'ayse', 'istek_id': 'req-42', 'cancelled': False},
):
    eq(zarf_dogrula(_bozuk_zarf, 'ayse', 'req-42'), {'gecerli': False, 'veri': None, 'baglantiyi_kapat': True},
       f'eksik/bozuk alanlı zarf reddedilmeli: {_bozuk_zarf!r}')
```

```hint
Eşleşme sağlandığında `baglantiyi_kapat: False`, şema veya kimlik uyuşmazlığında ise `veri: None` ve `baglantiyi_kapat: True` döndür.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Olay bağlamı (15 sn).** "OpenAI'ın Mart 2023 kesinti raporu, `asyncio` istek iptali sonrasında paylaşımlı `redis-py` bağlantısında kalan yanıtın sonraki kullanıcıya sızabildiğini belgeledi."
2. **Kök neden (30 sn).** "Asenkron bağlantı havuzlarında sıra varsayımı iptal anında kayar; dönen veride sahip (`owner`) doğrulanmazsa altyapı hatası gizlilik ihlaline dönüşür."
3. **Sınır ve ölçüm (30 sn).** "`cache_oku` içinde `owner == beklenen` ve `cancelled is False` kurallarını uyguladım; senaryo koşusunda çapraz kiracı sızıntısı `1.0`'dan `0.0`'a indi."
4. **Zarf bağlama (25 sn).** "`zarf_dogrula` ile her yanıtı `(owner, istek_id)` çiftine bağladım ve uyuşmazlıkta kirlenen bağlantıyı havuzdan kapattırdım."
5. **Kapanış (20 sn).** "Çok kiracılı AI servislerinde önbellek anahtarları ve yanıt zarfları kriptografik veya yapısal sahip kimliğiyle kendi kendini doğrulamalıdır."
:::

::: anlat Sınır ve kaynak
Bu dersteki model uygulama içi sözlük zarfını doğrular. Üretim önbelleklerinde ek olarak kiracı bazlı anahtar öneki + HMAC bağlama ve `asyncio.CancelledError` yakalandığında soketin havuza geri konulmadan doğrudan kapatılması (`connection discard on cancel`) uygulanır (`ai-savunma-19`).

- Birincil kaynak: [OpenAI — March 20 ChatGPT outage: Here's what happened (Mart 2023)](https://openai.com/index/march-20-chatgpt-outage/). Doğrulama tarihi: 10 Kasım 2026.
:::

::: dusun
Yalnız `owner` alanını doğrulayıp `istek_id` alanını doğrulamayan bir önbellek zarfı, aynı kurumsal müşteri hesabını paylaşan iki farklı departman kullanıcısında veya aynı kullanıcının iki farklı gizlilik seviyeli oturumunda hangi soruna yol açar?
:::

::: ozet
- Asenkron bağlantı havuzlarında iptal edilen istekler kuyruk senkronunu bozarak çapraz kiracı sızıntısı üretebilir.
- Önbellek okumalarında hem `owner` eşleşmesi hem `cancelled is False` kesin kontrolü zorunludur.
- Zarf uyuşmazlığı tespit edildiğinde hem veri reddedilir hem de kirlenmiş bağlantı havuzdan çıkarılır.
:::
