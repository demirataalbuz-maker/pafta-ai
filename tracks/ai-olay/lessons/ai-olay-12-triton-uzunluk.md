---
id: ai-olay-12
title: "Triton Çıkarım Sunucusu · Paylaşımlı Bellek Uzunluk ve Kota Sınırı"
summary: NVIDIA güvenlik bültenindeki CVE-2025-23320 bağlamında bildirilen/alınan bayt uzunluğu uyumsuzluğunu, tam sayı tip sınırını ve kiracılar arası paylaşımlı bellek çakışmasını denetle.
esleme: ai-savunma-31, ai-savunma-13, ai-savunma-04, ai-guvence-05
timeout: 30
---

::: anlat 1. Gerçek olay ve yerel kopya sınırı
Ağustos 2025'te yayımlanan **NVIDIA güvenlik bülteni (id 5687)**, **Triton Inference Server** Python arka ucunda paylaşımlı bellek (`shared memory`) sınırının çok büyük bir istekle aşılmasıyla bilgi ifşasına yol açabilen **CVE-2025-23320** kaydını tanımlar. Yüksek verimli çıkarım sunucuları büyük tensörleri ağ üzerinden kopyalamak yerine paylaşımlı bellek dilimleri (`offset`, `byte_size`) üzerinden taşır; üst bilgide bildirilen uzunluk ile gerçekte ayrılan/alınan bayt uzunluğu ve üst limit uyuşmadığında komşu bellek bölgeleri okunabilir hale gelir.

> [!NOTE]
> **Yerel kopya ayrımı:** Bu ders C++/CUDA paylaşımlı bellek sürücüsünü veya uydurulmuş bir model deposu istismarını çalıştırmaz. Çıkarım sunucularındaki **bildirilen uzunluk == alınan uzunluk <= limit** değişmezini ve kiracılar arası bellek aralığı yalıtımını saf Python modeliyle inceler.
:::

::: anlat 2. Mekanizma · üst bilgi uzunluğu ile gerçek tampon uzunluğu ayrıştığında ne olur?
İkili protokollerde istemci bir tensör paketi gönderirken üst bilgide `bildirilen = 64` bayt yazıp gerçekte `alinan = 512` bayt gönderebilir (veya tam tersi: `bildirilen = 512` diyerek yalnız `64` bayt gönderip sunucunun kalan `448` baytı paylaşımlı bellek havuzundaki eski veriden okumasını — *over-read* — tetikleyebilir) (`ai-savunma-13`, `ai-savunma-31`).

Güvenli tampon kabul sınırı dört kuralı tek adımda kilitler:
1. Üç değer de (`bildirilen`, `alinan`, `limit`) `bool` olmayan gerçek `int` (`type(x) is int`) olmalıdır.
2. Havuz sınırı pozitif olmalıdır (`limit > 0`; `limit == 0` geçerli bir tampon kapasitesi değildir).
3. Negatif uzunluklar yasaktır (`0 <= bildirilen` ve `0 <= alinan`).
4. Bildirilen uzunluk ile alınan uzunluk birebir eşit olmalı ve `limit` değerini aşmamalıdır (`0 <= bildirilen == alinan <= limit`).

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| Yalnız `bildirilen <= limit` kontrolü yapmak | `bildirilen=64, alinan=512` uyumsuzluğunu ve negatif `alinan` değerini kaçırır | `0 <= bildirilen == alinan <= limit` |
| `limit >= 0` yazıp `(0, 0, 0)` çağrısını kabul etmek | Sıfır kapasiteli bozuk tampon yapılandırmasını geçerli sayar | `limit > 0` kesin pozitiflik şartı |
| `isinstance(x, int)` kullanmak | `(1, True, 8)` çağrısında `True == 1` olduğu için `bool` bayrağını bayt boyutu kabul eder! | `all(type(x) is int for x in ...)` |
:::

::: tahmin `(1, True, 8)` çağrısı `isinstance(..., int)` kontrolünü nasıl yanıltır?
Python'da `1 == True` eşitliği ve `isinstance(True, int)` alt sınıf ilişkisi birleştiğinde uzunluk doğrulayıcısına ne olur?

```python
bildirilen, alinan, limit = 1, True, 8
gevsek = all(isinstance(x, int) for x in (bildirilen, alinan, limit)) and (0 <= bildirilen == alinan <= limit)
siki = all(type(x) is int for x in (bildirilen, alinan, limit)) and (0 <= bildirilen == alinan <= limit)
print('isinstance ile:', gevsek)
print('type is int ile:', siki)
```

???

```cikti
isinstance ile: True
type is int ile: False
```
JSON ayrıştırmasından gelen mantıksal `true` değeri Python'da `True` nesnesine dönüşür; `isinstance(True, int)` ve `1 == True` ikisi birden `True` olduğu için `type(x) is int` yazılmayan bir sınır `bool` değerini `1` bayt sanır!
:::

::: gorev 1 · Tampon uzunluk ve kapasite değişmezini (`buffer_izin`) kur
`buffer_izin(bildirilen, alinan, limit)` işlevini yaz:

- `bildirilen`, `alinan` ve `limit` argümanlarının üçü de `bool` olmayan tam `int` (`type(x) is int`) olmalı;
- `limit > 0` olmalı;
- `0 <= bildirilen == alinan <= limit` koşulu sağlanmalı.
- Koşulların tamamı doğruysa `True`, aksi her durumda `False` döndür (mod alma veya toplama ile sınırı sarmalama).

KUSURLU başlangıç `isinstance(..., int)`, `limit >= 0` ve yalnız `bildirilen <= limit` kullandığı için üç ayrı güvenlik hatasını birden barındırıyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[\n  8,\n  8,\n  8\n]', encoding='utf-8')
```

```starter
def buffer_izin(bildirilen, alinan, limit):
    if not all(isinstance(x, int) for x in (bildirilen, alinan, limit)):
        return False
    return limit >= 0 and 0 <= bildirilen <= limit

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(buffer_izin(*_args))
```

```solution
def buffer_izin(bildirilen, alinan, limit):
    return (
        all(type(x) is int for x in (bildirilen, alinan, limit))
        and limit > 0
        and 0 <= bildirilen == alinan <= limit
    )

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(buffer_izin(*_args))
```

```test
need('buffer_izin')
eq(buffer_izin(8, 8, 8), True, 'tam limit sınırındaki eşit uzunluk geçmeli')
eq(buffer_izin(0, 0, 8), True, 'pozitif limitte sıfır baytlık boş tensör geçmeli')
eq(buffer_izin(64, 64, 1024), True, 'limit altı eşit uzunluk geçmeli')

_red = [
    (0, 0, 0),
    (8, 8, -8),
    (64, 512, 1024),
    (512, 64, 1024),
    (1025, 1025, 1024),
    (-1, -1, 1024),
    (1, True, 8),
    (True, 1, 8),
    (1, 1, True),
    (False, 0, 8),
    (8.0, 8, 16),
    ('8', 8, 16),
    (None, 8, 16),
]
for _b, _a, _l in _red:
    eq(buffer_izin(_b, _a, _l), False, f'uyumsuz/taşan/bozuk tip reddedilmeli: {(_b, _a, _l)!r}')
eq(buffer_izin(1, 1, 1), True, 'en küçük pozitif limit (1) geçerli')
```

```hint
`all(type(x) is int for x in (bildirilen, alinan, limit)) and limit > 0 and 0 <= bildirilen == alinan <= limit` ifadesi hem `bool` alt türünü hem sıfır limiti hem de uzunluk uyumsuzluğunu tek seferde kapatır.
```
:::

::: gorev 2 · Açık ve yamalı tampon sınırını senaryo vakalarında ölç
`buffer_senaryo_olc(vakalar, acik_fn, yamali_fn)` işlevini yaz:

- Her vaka `{'saldiri': bool, 'girdi': (bildirilen, alinan, limit), ...}` sözlüğüdür. Şema veya çağrılabilirlik bozuksa `ValueError` fırlat.
- Sınır işlevi `True` döndürdüğünde tampon isteği **kabul edildi** sayılır.
- Saldırı vakalarında kabul **bellek sınırı aşımı (`sizma`)**, meşru vakalarda kabul **meşru kabul** demektir.
- Dönüş: `{'saldiri_n': int, 'mesru_n': int, 'once_sizma': float|None, 'sonra_sizma': float|None, 'mesru_kabul': float|None, 'regresyon_n': int}`.

KUSURLU başlangıç oranları 4 basamak yerine tam sayıya (`int`) yuvarladığı için kısmi sızıntıları `0` olarak gizliyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def buffer_senaryo_olc(vakalar, acik_fn, yamali_fn):
    s = [v for v in vakalar if v['saldiri']]
    m = [v for v in vakalar if not v['saldiri']]
    return {
        'saldiri_n': len(s), 'mesru_n': len(m),
        'once_sizma': float(int(sum(1 for v in s if acik_fn(*v['girdi'])) / len(s))) if s else None,
        'sonra_sizma': float(int(sum(1 for v in s if yamali_fn(*v['girdi'])) / len(s))) if s else None,
        'mesru_kabul': float(int(sum(1 for v in m if yamali_fn(*v['girdi'])) / len(m))) if m else None,
        'regresyon_n': 0,
    }
```

```solution
import copy

def buffer_senaryo_olc(vakalar, acik_fn, yamali_fn):
    if not isinstance(vakalar, list) or not vakalar or not callable(acik_fn) or not callable(yamali_fn):
        raise ValueError('gecerli vakalar ve cagrilaiblir sinirlar gerekli')
    s_n = m_n = s_once = s_sonra = m_sonra = reg = 0
    for v in vakalar:
        if not isinstance(v, dict) or type(v.get('saldiri')) is not bool or not isinstance(v.get('girdi'), (tuple, list)):
            raise ValueError('bozuk vaka semasi')
        once_ok = bool(acik_fn(*copy.deepcopy(v['girdi'])))
        sonra_ok = bool(yamali_fn(*copy.deepcopy(v['girdi'])))
        if v['saldiri']:
            s_n += 1
            s_once += int(once_ok)
            s_sonra += int(sonra_ok)
        else:
            m_n += 1
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
need('buffer_senaryo_olc')
from sandbox.ai_olay_senaryo import acik_sinir, senaryo_vakalari

def _yama(b, a, l):
    return all(type(x) is int for x in (b, a, l)) and l > 0 and 0 <= b == a <= l

_vakalar = senaryo_vakalari(12, tohum=12)
eq(buffer_senaryo_olc(_vakalar, acik_sinir(12), _yama), {
    'saldiri_n': 4,
    'mesru_n': 2,
    'once_sizma': 1.0,
    'sonra_sizma': 0.0,
    'mesru_kabul': 1.0,
    'regresyon_n': 0,
}, 'açık sınır 4/4 saldırıyı kabul eder, yama 0.0 sızıntı ve 1.0 meşru kabul sağlar')

_kismi = buffer_senaryo_olc(_vakalar, acik_sinir(12), lambda b, a, l: b == a and l >= 0)
eq(_kismi['sonra_sizma'], 0.5, '(0,0,0) ve (1,True,8) kaçtığında 2/4 = 0.5 tam gösterilmeli')
eq(buffer_senaryo_olc(_vakalar, acik_sinir(12), lambda *_a: False)['regresyon_n'], 2, '2 regresyon sayılmalı')
raises(ValueError, buffer_senaryo_olc, [], acik_sinir(12), _yama, msg='boş liste ValueError')

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
eq(buffer_senaryo_olc(_el, _acik_el, _yama_el), {
    'saldiri_n': 3,
    'mesru_n': 3,
    'once_sizma': 0.6667,
    'sonra_sizma': 0.3333,
    'mesru_kabul': 0.3333,
    'regresyon_n': 1,
}, 'oranlar grup paydasıyla ve 4 basamakla; sıfırdan farklı sonra_sizma ve regresyon doğru sayılmalı')
eq(buffer_senaryo_olc(_el, _acik_el, _acik_el)['sonra_sizma'], 0.6667, 'yama açık sınırla aynıysa sonra_sizma = once_sizma')
eq(buffer_senaryo_olc(_el, lambda *_a: False, lambda *_a: False)['regresyon_n'], 0,
   'açık sınırın da reddettiği meşru vaka regresyon sayılmaz')
eq(buffer_senaryo_olc([v for v in _el if not v['saldiri']], _acik_el, _yama_el),
   {'saldiri_n': 0, 'mesru_n': 3, 'once_sizma': None, 'sonra_sizma': None, 'mesru_kabul': 0.3333, 'regresyon_n': 1},
   'saldırı vakası yoksa once_sizma ve sonra_sizma None')
eq(buffer_senaryo_olc([v for v in _el if v['saldiri']], _acik_el, _yama_el)['mesru_kabul'], None, 'meşru vaka yoksa mesru_kabul None')
raises(ValueError, buffer_senaryo_olc, tuple(_el), _acik_el, _yama_el, msg='liste olmayan vakalar ValueError')
raises(ValueError, buffer_senaryo_olc, _el, None, _yama_el, msg='çağrılamaz açık sınır ValueError')
raises(ValueError, buffer_senaryo_olc, _el, _acik_el, 'yama', msg='çağrılamaz yamalı sınır ValueError')
for _bozuk in (
    _el + [('s-ikisi-gecer',)],
    _el + [{'saldiri': 1, 'girdi': ('s-ikisi-gecer',)}],
    _el + [{'saldiri': True, 'girdi': None}],
):
    raises(ValueError, buffer_senaryo_olc, _bozuk, _acik_el, _yama_el, msg=f'bozuk vaka şeması ValueError: {_bozuk[-1]!r}')
```

```hint
Kısmi sızıntıları gizlememek için `round(sayac / payda, 4)` kullan; payda sıfırken `None` döndür.
```
:::

::: gorev 3 · Çok kiracılı paylaşımlı bellek havuzunda bölge çakışmasını engelle
Paylaşımlı bellek havuzuna yeni bir dilim (`[ofset, ofset + uzunluk)`) kaydedilirken başka bir bölgeyle örtüşmediğini ve havuz sınırını aşmadığını doğrulayan `shm_bolge_kaydet(bolgeler, kiraci, ofset, uzunluk, havuz_boyutu)` işlevini yaz:

- `bolgeler`: her öğesi `{'kiraci': str, 'ofset': int, 'uzunluk': int}` olan `list`; `kiraci` boş olmayan `str`; `ofset`, `uzunluk`, `havuz_boyutu` `bool` olmayan `int` ve `havuz_boyutu > 0`. Üst şema bozuksa `ValueError` fırlat.
- İstenen dilim geçersizse (`ofset < 0` veya `uzunluk <= 0` veya `ofset + uzunluk > havuz_boyutu`) `{'izin': False, 'cakisan_kiraci': None, 'neden': 'sinir-disi'}` döndür.
- Mevcut `bolgeler` listesindeki herhangi bir kayıtla yarı-açık aralık `[ofset, ofset + uzunluk)` kesişiyorsa (`max(bas1, bas2) < min(bit1, bit2)`) ilk çakışan kaydın kiracısını döndür: `{'izin': False, 'cakisan_kiraci': b['kiraci'], 'neden': 'bolge-cakismasi'}` (aynı kiracının kendi bölgesiyle örtüşmesi de yasaktır!).
- Hiç çakışma yoksa `{'izin': True, 'cakisan_kiraci': None, 'neden': 'uygun'}` döndür.

KUSURLU başlangıç bitiş sınırında `<` yerine `<=` kullandığı için birbirine bitişik ama örtüşmeyen meşru `[0, 64)` ve `[64, 128)` dilimlerini çakışıyor sanıyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def shm_bolge_kaydet(bolgeler, kiraci, ofset, uzunluk, havuz_boyutu):
    if ofset < 0 or uzunluk <= 0 or ofset + uzunluk > havuz_boyutu:
        return {'izin': False, 'cakisan_kiraci': None, 'neden': 'sinir-disi'}
    for b in bolgeler:
        if max(ofset, b['ofset']) <= min(ofset + uzunluk, b['ofset'] + b['uzunluk']):
            return {'izin': False, 'cakisan_kiraci': b['kiraci'], 'neden': 'bolge-cakismasi'}
    return {'izin': True, 'cakisan_kiraci': None, 'neden': 'uygun'}
```

```solution
def shm_bolge_kaydet(bolgeler, kiraci, ofset, uzunluk, havuz_boyutu):
    if (not isinstance(bolgeler, list) or not isinstance(kiraci, str) or not kiraci.strip()
            or any(type(x) is not int for x in (ofset, uzunluk, havuz_boyutu)) or havuz_boyutu <= 0):
        raise ValueError('gecersiz parametre tipleri')
    for b in bolgeler:
        if (not isinstance(b, dict) or not isinstance(b.get('kiraci'), str) or not b['kiraci'].strip()
                or type(b.get('ofset')) is not int or type(b.get('uzunluk')) is not int
                or b['ofset'] < 0 or b['uzunluk'] <= 0):
            raise ValueError('bozuk bolge kaydi')
    if ofset < 0 or uzunluk <= 0 or ofset + uzunluk > havuz_boyutu:
        return {'izin': False, 'cakisan_kiraci': None, 'neden': 'sinir-disi'}
    bitis = ofset + uzunluk
    for b in bolgeler:
        b_bas = b['ofset']
        b_bit = b_bas + b['uzunluk']
        if max(ofset, b_bas) < min(bitis, b_bit):
            return {'izin': False, 'cakisan_kiraci': b['kiraci'], 'neden': 'bolge-cakismasi'}
    return {'izin': True, 'cakisan_kiraci': None, 'neden': 'uygun'}
```

```test
need('shm_bolge_kaydet')
_mevcut = [{'kiraci': 'kiraci-a', 'ofset': 0, 'uzunluk': 64}]

eq(shm_bolge_kaydet(_mevcut, 'kiraci-b', 64, 64, 128), {
    'izin': True, 'cakisan_kiraci': None, 'neden': 'uygun',
}, 'tam bitişik [0,64) ve [64,128) örtüşmez; kabul edilmeli')

eq(shm_bolge_kaydet(_mevcut, 'kiraci-b', 63, 16, 128), {
    'izin': False, 'cakisan_kiraci': 'kiraci-a', 'neden': 'bolge-cakismasi',
}, 'tek baytlık [63,64) örtüşmesi yakalanmalı')

for _ofs, _uz in ((-1, 16), (64, 0), (64, -8), (64, 65)):
    eq(shm_bolge_kaydet(_mevcut, 'kiraci-b', _ofs, _uz, 128), {
        'izin': False, 'cakisan_kiraci': None, 'neden': 'sinir-disi',
    }, f'havuz dışı dilim reddedilmeli: {(_ofs, _uz)}')

for _bozuk in ((_mevcut, '', 64, 16, 128), (_mevcut, 'b', True, 16, 128), (_mevcut, 'b', 64, 16, 0)):
    raises(ValueError, shm_bolge_kaydet, *_bozuk, msg='şema hatası ValueError')

# Alt sınırlar: ofset 0, 1 baytlık bölge, 1 baytlık havuz ve pozitif ofsetli mevcut bölgeler geçerlidir.
_uygun = {'izin': True, 'cakisan_kiraci': None, 'neden': 'uygun'}
eq(shm_bolge_kaydet([], 'b', 0, 1, 1), _uygun, '1 baytlık havuzun başındaki 1 baytlık bölge geçerli')
eq(shm_bolge_kaydet([{'kiraci': 'a', 'ofset': 0, 'uzunluk': 1}, {'kiraci': 'c', 'ofset': 100, 'uzunluk': 28}], 'b', 1, 99, 128),
   _uygun, 'pozitif ofsetli ve 1 baytlık mevcut bölgeler arasındaki boşluk kullanılabilir')

# Üst parametre ve mevcut bölge şeması: her kural tek başına.
raises(ValueError, shm_bolge_kaydet, tuple(_mevcut), 'b', 64, 16, 128, msg='liste olmayan bölgeler ValueError')
raises(ValueError, shm_bolge_kaydet, _mevcut, None, 64, 16, 128, msg='str olmayan kiracı ValueError')
_iyi = {'kiraci': 'c', 'ofset': 100, 'uzunluk': 8}
for _alan, _deger in (('kiraci', 5), ('kiraci', '  '), ('ofset', 100.0), ('ofset', -1), ('uzunluk', 8.0), ('uzunluk', 0), ('uzunluk', -1)):
    raises(ValueError, shm_bolge_kaydet, _mevcut + [dict(_iyi, **{_alan: _deger})], 'b', 64, 16, 128,
           msg=f'bozuk mevcut bölge ValueError: {_alan}={_deger!r}')
raises(ValueError, shm_bolge_kaydet, _mevcut + ['bolge'], 'b', 64, 16, 128, msg='dict olmayan bölge ValueError')
```

```hint
Yarı-açık `[a, b)` ve `[c, d)` aralıkları yalnız `max(a, c) < min(b, d)` olduğunda kesişir; `64 < 64` `False` olduğu için bitişik `[0, 64)` ve `[64, 128)` güvenle yan yana durur.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Olay bağlamı (15 sn).** "NVIDIA bülteni CVE-2025-23320, Triton çıkarım sunucusunun Python arka ucunda paylaşımlı bellek sınır kontrolünün kritikliğini gösterir."
2. **Mekanizma (30 sn).** "İkili protokolde bildirilen uzunluk ile gerçekte alınan uzunluk ayrıştığında veya `ofset + uzunluk` sınırı aştığında komşu kiracı verisi okunabilir."
3. **Sınır ve ölçüm (30 sn).** "`buffer_izin` ile `type(x) is int`, `limit > 0` ve `0 <= bildirilen == alinan <= limit` değişmezini kurdum; senaryo koşusunda `(0,0,0)` ve `(1,True,8)` dahil 4/4 sınır hatasını durdurdum."
4. **Havuz izolasyonu (25 sn).** "`shm_bolge_kaydet` ile yarı-açık `[ofset, ofset + uzunluk)` aralıklarında kiracılar arası tek baytlık örtüşmeleri bile engelledim."
5. **Kapanış (20 sn).** "Yüksek hızlı sıfır-kopya (`zero-copy`) çıkarım hatlarında her bellek dilimi hem uzunluk eşitliği hem aralık ayrıklığı ile doğrulanmalıdır."
:::

::: anlat Sınır ve kaynak
Python sınırsız duyarlıklı (`arbitrary-precision`) tam sayılar kullandığı için `ofset + uzunluk` toplamı Python'da taşmaz; ancak C/C++ tabanlı gerçek çıkarım sunucularında `uint64_t` tam sayı taşmasına (`integer overflow`: `ofset + uzunluk < ofset`) karşı `uzunluk <= havuz_boyutu - ofset` çıkarma biçimi zorunludur (`ai-savunma-13`).

- Birincil kaynak: [NVIDIA Security Bulletin: NVIDIA Triton Inference Server — August 2025 (id 5687, CVE-2025-23320)](https://nvidia.custhelp.com/app/answers/detail/a_id/5687). Doğrulama tarihi: 10 Kasım 2026.
:::

::: dusun
C dilinde yazılmış bir çıkarım arka ucunda `uint32_t ofset = 0xFFFFFFF0; uint32_t uzunluk = 0x20;` verildiğinde `if (ofset + uzunluk <= havuz_boyutu)` kontrolü neden `havuz_boyutu = 1024` iken bile yanlışlıkla `true` döner?
:::

::: ozet
- Çıkarım protokollerinde bildirilen boyut ile alınan boyut eşitliği ve pozitif kapasite sınırı birlikte doğrulanır.
- Python'da bayt boyutu kontrollerinde `bool` sızıntısını önlemek için `type(x) is int` kullanılır.
- Paylaşımlı bellek havuzlarında kiracı dilimleri yarı-açık aralık kesişimi (`max(bas) < min(bit)`) ile yalıtılır.
:::
