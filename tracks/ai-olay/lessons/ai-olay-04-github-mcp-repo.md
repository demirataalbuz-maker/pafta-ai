---
id: ai-olay-04
title: "GitHub MCP · Toxic Agent Flow ve Repo Sınırı"
summary: Çok depolu MCP araç zincirinde açık issue okumasından özel depoya ve dış PR yazımına uzanan veri akışını (toxic agent flow) depo kapsamı ve oturum taint takibiyle durdur.
esleme: ai-saldiri-01, ai-saldiri-17, ai-saldiri-18, ai-savunma-12
timeout: 30
---

::: anlat 1. Gerçek olay ve yerel kopya sınırı
*Invariant Labs* araştırmacıları (Mayıs 2025), **GitHub MCP** sunucusunu kullanan kod ajanlarında **Toxic Agent Flow** adını verdikleri bir mimari zafiyet sınıfını belgeledi: GitHub MCP sunucusunun kendi kodunda klasik bir bellek veya kimlik doğrulama açığı olmasa bile, geniş kapsamlı kişisel erişim jetonu (`PAT`) taşıyan bir ajan **herkesin yazabildiği açık bir depodaki `issue` metnini** okuduğunda, oradaki dolaylı `prompt injection` ajanı kullanıcının **özel (`private`) deposundaki** dosyaları okuyup açık depoya `pull request` açmaya yönlendirebilmektedir.

> [!NOTE]
> **Yerel kopya ayrımı:** Bu ders GitHub API uçlarını veya gerçek MCP JSON-RPC soketini çağırmaz. Olayın özündeki **depo kapsam sınırı (`repo scope pinning`)** ve **araç zinciri boyunca `taint` izleme** mekanizmasını çevrimdışı Python verisiyle modeller.
:::

::: anlat 2. Mekanizma · sunucu sağlamken ajan akışı neden kırılır?
Klasik uygulama güvenliğinde her API çağrısı kullanıcının jetonuna bakar: geliştiricinin jetonu hem `kurum/acik-issue` hem `kurum/ozel-kasa` depolarına yetkiliyse iki çağrı da sunucu açısından "yetkilidir". Oysa ajan mimarisinde kararları insan değil, az önce güvenilmeyen `issue` metnini okumuş olan model verir (`confused deputy` — bkz. `ai-saldiri-01`, `ai-saldiri-17`):

1. **Adım 1 (Bulaşma):** Ajan `kurum/acik-issue` deposundaki saldırgan `issue` kaydını okur (`tainted` veri bağlama girer).
2. **Adım 2 (Yatay geçiş):** Ajan aynı oturumda `kurum/ozel-kasa` deposundan yapılandırma/kaynak okur.
3. **Adım 3 (Sızıntı):** Ajan okuduğu özel içeriği açık depoda veya çatalda yeni bir `pull request` / yorum olarak yazar.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| Yalnız organizasyon sahibini (`kurum/*`) kontrol etmek | Aynı organizasyonun açık `issue` deposundan özel `ozel-kasa` deposuna sızıntıya izin verir | Görev oturumunu tek bir hedef `kapsam` deposuna (`'kurum/depo'`) kilitlemek |
| `okunan == yazilan` kontrolü yapıp `kapsam` parametresini unutmak | Ajanın görev kapsamı dışındaki başka bir depoda (`'kurum/yan-depo'`) hem okuyup hem yazmasına izin verir | `okunan == kapsam and yazilan == kapsam` üçlü eşitliği |
| Her araç çağrısını tek başına değerlendirmek | Önceki adımda güvenilmeyen `issue` okunduktan sonra yapılan `pr_create` çağrısını masum sanır | Oturum boyunca `taint` bayrağını taşıyıp durum değiştiren yazma adımlarını durdurmak |
:::

::: tahmin Yalnız `okunan == yazilan` kontrolü görev kapsamını korur mu?
Geliştirici ajanı `'kurum/rehber'` deposunda çalışması için başlattı; ancak politika yalnız "okunan depo ile yazılan depo aynı olsun" derse ne olur?

```python
def kapsam_unutuldu(okunan, yazilan, kapsam):
    return okunan == yazilan

def tam_kapsam(okunan, yazilan, kapsam):
    return okunan == kapsam and yazilan == kapsam

print('hedef dışı depo:', kapsam_unutuldu('kurum/ozel-kasa', 'kurum/ozel-kasa', 'kurum/rehber'))
print('tam kapsam kontrolü:', tam_kapsam('kurum/ozel-kasa', 'kurum/ozel-kasa', 'kurum/rehber'))
```

???

```cikti
hedef dışı depo: True
tam kapsam kontrolü: False
```
`kapsam` parametresi karşılaştırmaya katılmazsa ajan kendisine verilen dar görev sınırının dışına çıkıp başka bir özel depoda okuma ve yazma yapabilir.
:::

::: gorev 1 · Tek-depo kapsam kapısını (`repo_akis`) kur
`repo_akis(okunan, yazilan, kapsam)` işlevini yaz:

- Üç argümanın her biri `'sahip/ad'` biçiminde geçerli bir depo kimliği olmalıdır: `str` türünde, kenar boşluksuz (`x == x.strip()` ve boşluk karakteri içermeyen), tam bir adet `'/'` içeren ve hem `sahip` hem `ad` bölümü boş olmayan dizge. Herhangi biri geçersizse `False` döndür (`TypeError` veya `AttributeError` fırlatma).
- Yalnız üç geçerli depo kimliği de birebir aynıysa (`okunan == kapsam and yazilan == kapsam`) `True`, aksi halde `False` döndür.

KUSURLU başlangıç yalnız organizasyon sahibini (`sahip`) karşılaştırdığı için aynı organizasyondaki açık depodan özel depoya veri akışına izin veriyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[\n  "kurum/cekirdek",\n  "kurum/cekirdek",\n  "kurum/cekirdek"\n]', encoding='utf-8')
```

```starter
def repo_akis(okunan, yazilan, kapsam):
    if not all(isinstance(x, str) and '/' in x for x in (okunan, yazilan, kapsam)):
        return False
    return okunan.split('/')[0] == kapsam.split('/')[0] and yazilan.split('/')[0] == kapsam.split('/')[0]

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(repo_akis(*_args))
```

```solution
def _gecerli_depo(deger):
    if not isinstance(deger, str) or deger != deger.strip() or any(c.isspace() for c in deger):
        return False
    parcalar = deger.split('/')
    return len(parcalar) == 2 and bool(parcalar[0]) and bool(parcalar[1])

def repo_akis(okunan, yazilan, kapsam):
    if not (_gecerli_depo(okunan) and _gecerli_depo(yazilan) and _gecerli_depo(kapsam)):
        return False
    return okunan == kapsam and yazilan == kapsam

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(repo_akis(*_args))
```

```test
need('repo_akis')
eq(repo_akis('kurum/cekirdek', 'kurum/cekirdek', 'kurum/cekirdek'), True, 'kapsam içi aynı depo akışı geçmeli')
eq(repo_akis('ekip-1/servis_a', 'ekip-1/servis_a', 'ekip-1/servis_a'), True, 'geçerli depo adları korunmalı')

_kotu = [
    ('kurum/acik-issue', 'kurum/ozel-kasa', 'kurum/ozel-kasa'),
    ('kurum/ozel-kasa', 'kurum/acik-issue', 'kurum/ozel-kasa'),
    ('kurum/yan-depo', 'kurum/yan-depo', 'kurum/ana-depo'),
    ('kurum/ozel-kasa', 'disari/toplama', 'kurum/ozel-kasa'),
    ('tekparca', 'tekparca', 'tekparca'),
    ('/ad', '/ad', '/ad'),
    ('sahip/', 'sahip/', 'sahip/'),
    ('a/b/c', 'a/b/c', 'a/b/c'),
    (' kurum/depo', 'kurum/depo', 'kurum/depo'),
    ('kurum/depo ', 'kurum/depo ', 'kurum/depo '),
    ('kurum/de po', 'kurum/de po', 'kurum/de po'),
    (None, 'kurum/depo', 'kurum/depo'),
    ('kurum/depo', 123, 'kurum/depo'),
]
for _o, _y, _k in _kotu:
    eq(repo_akis(_o, _y, _k), False, f'kapsam dışı veya bozuk depo kimliği reddedilmeli: {(_o, _y, _k)!r}')
```

```hint
Önce yardımcı bir `_gecerli_depo(x)` işleviyle `isinstance(x, str)`, boşluksuzluk, `len(x.split('/')) == 2` ve iki parçanın da boş olmamasını doğrula; sonra `okunan == kapsam and yazilan == kapsam` döndür.
```
:::

::: gorev 2 · Açık ve yamalı MCP depo sınırını senaryo vakalarında ölç
`repo_senaryo_olc(vakalar, acik_fn, yamali_fn)` işlevini yaz:

- `vakalar`: boş olmayan `list`; her vaka `{'saldiri': bool, 'girdi': (okunan, yazilan, kapsam), ...}` sözlüğüdür. Şema bozuksa veya işlevler `callable` değilse `ValueError` fırlat.
- Her vaka için `bool(acik_fn(*copy.deepcopy(girdi)))` ve `bool(yamali_fn(*copy.deepcopy(girdi)))` sonuçlarını ölç.
- Saldırı vakalarında `True` **çapraz depo sızıntısı**, meşru vakalarda `True` **hizmet kabulü** demektir.
- Dönüş: `{'saldiri_n': int, 'mesru_n': int, 'once_sizma': float|None, 'sonra_sizma': float|None, 'mesru_kabul': float|None, 'regresyon_n': int}` (4 ondalık yuvarlamalı, boş grupta `None`).

KUSURLU başlangıç `regresyon_n` sayacını hesaplamıyor ve boş saldırı/meşru gruplarında `ZeroDivisionError` fırlatıyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def repo_senaryo_olc(vakalar, acik_fn, yamali_fn):
    s = [v for v in vakalar if v['saldiri']]
    m = [v for v in vakalar if not v['saldiri']]
    return {
        'saldiri_n': len(s),
        'mesru_n': len(m),
        'once_sizma': round(sum(1 for v in s if acik_fn(*v['girdi'])) / len(s), 4),
        'sonra_sizma': round(sum(1 for v in s if yamali_fn(*v['girdi'])) / len(s), 4),
        'mesru_kabul': round(sum(1 for v in m if yamali_fn(*v['girdi'])) / len(m), 4),
        'regresyon_n': 0,
    }
```

```solution
import copy

def repo_senaryo_olc(vakalar, acik_fn, yamali_fn):
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
need('repo_senaryo_olc')
from sandbox.ai_olay_senaryo import acik_sinir, senaryo_vakalari

def _dogru_yama(o, y, k):
    return all(isinstance(x, str) and len(x.split('/')) == 2 and all(x.split('/')) for x in (o, y, k)) and o == k and y == k

_vakalar = senaryo_vakalari(4, tohum=9)
_r = repo_senaryo_olc(_vakalar, acik_sinir(4), _dogru_yama)
eq(_r, {
    'saldiri_n': 4,
    'mesru_n': 2,
    'once_sizma': 0.75,
    'sonra_sizma': 0.0,
    'mesru_kabul': 1.0,
    'regresyon_n': 0,
}, 'organizasyon içi 3 çapraz saldırı açık sınırda sızar (3/4 = 0.75), yamada 0.0 olur')

_kapsamsiz = repo_senaryo_olc(_vakalar, acik_sinir(4), lambda o, y, _k: o == y)
eq(_kapsamsiz['sonra_sizma'], 0.25, 'kapsam unutulursa yan-depo saldırısı kaçırılır (1/4 = 0.25)')

_kapali = repo_senaryo_olc(_vakalar, acik_sinir(4), lambda _o, _y, _k: False)
eq(_kapali['regresyon_n'], 2, '2 meşru vaka regresyona uğramalı')
eq(repo_senaryo_olc([v for v in _vakalar if v['saldiri']], acik_sinir(4), _dogru_yama)['mesru_kabul'], None, 'meşru vaka yoksa None')
eq(repo_senaryo_olc([v for v in _vakalar if not v['saldiri']], acik_sinir(4), _dogru_yama)['once_sizma'], None, 'saldırı vakası yoksa None')
raises(ValueError, repo_senaryo_olc, [], acik_sinir(4), _dogru_yama, msg='boş liste reddedilmeli')

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
eq(repo_senaryo_olc(_el, _acik_el, _yama_el), {
    'saldiri_n': 3,
    'mesru_n': 3,
    'once_sizma': 0.6667,
    'sonra_sizma': 0.3333,
    'mesru_kabul': 0.3333,
    'regresyon_n': 1,
}, 'oranlar grup paydasıyla ve 4 basamakla; sıfırdan farklı sonra_sizma ve regresyon doğru sayılmalı')
eq(repo_senaryo_olc(_el, _acik_el, _acik_el)['sonra_sizma'], 0.6667, 'yama açık sınırla aynıysa sonra_sizma = once_sizma')
eq(repo_senaryo_olc(_el, lambda *_a: False, lambda *_a: False)['regresyon_n'], 0,
   'açık sınırın da reddettiği meşru vaka regresyon sayılmaz')
eq(repo_senaryo_olc([v for v in _el if not v['saldiri']], _acik_el, _yama_el),
   {'saldiri_n': 0, 'mesru_n': 3, 'once_sizma': None, 'sonra_sizma': None, 'mesru_kabul': 0.3333, 'regresyon_n': 1},
   'saldırı vakası yoksa once_sizma ve sonra_sizma None')
eq(repo_senaryo_olc([v for v in _el if v['saldiri']], _acik_el, _yama_el)['mesru_kabul'], None, 'meşru vaka yoksa mesru_kabul None')
raises(ValueError, repo_senaryo_olc, tuple(_el), _acik_el, _yama_el, msg='liste olmayan vakalar ValueError')
raises(ValueError, repo_senaryo_olc, _el, None, _yama_el, msg='çağrılamaz açık sınır ValueError')
raises(ValueError, repo_senaryo_olc, _el, _acik_el, 'yama', msg='çağrılamaz yamalı sınır ValueError')
for _bozuk in (
    _el + [('s-ikisi-gecer',)],
    _el + [{'saldiri': 1, 'girdi': ('s-ikisi-gecer',)}],
    _el + [{'saldiri': True, 'girdi': None}],
):
    raises(ValueError, repo_senaryo_olc, _bozuk, _acik_el, _yama_el, msg=f'bozuk vaka şeması ValueError: {_bozuk[-1]!r}')
```

```hint
Senaryo kümesindeki 4 saldırıdan 3 tanesi aynı organizasyon içinde (`kurum/...`) gerçekleştiği için `acik_sinir(4)` bunlarda `0.75` sızıntı üretir; grup boşken bölmeye girmeyip `None` döndür.
```
:::

::: gorev 3 · Çok adımlı MCP araç izinde (`trace`) oturum `taint` denetimi
Aynı depo içinde bile dışarıdan bir kullanıcının açtığı `issue` (`guvenilmez_girdi=True`) okunduktan sonra ajanın otomatik olarak `pr_create` çalıştırması tehlikelidir. `arac_zinciri_denetle(adimlar, kapsam)` işlevini yaz:

- `kapsam` geçerli `'sahip/ad'` depo kimliği olmalı; `adimlar` boş olmayan `list` olmalı; her adım `{'arac': 'issue_read'|'file_read'|'pr_create', 'repo': str, 'guvenilmez_girdi': bool}` sözlüğü olmalı (geçerli `'sahip/ad'` `repo` ile). Şema bozuksa `ValueError` fırlat.
- Adımları `0` tabanlı indeksle sırayla işle ve oturumda `bulasti = False` bayrağı tut:
  1. Herhangi bir adımda `adim['repo'] != kapsam` ise hemen engelle: `{'izin': False, 'engel_adimi': i, 'neden': 'kapsam-disi-depo'}`.
  2. `adim['guvenilmez_girdi'] is True` ise oturum artık bulaşmıştır (`bulasti = True`).
  3. Oturum bulaşmışken (`bulasti is True`) `adim['arac'] == 'pr_create'` çağrılırsa hemen engelle: `{'izin': False, 'engel_adimi': i, 'neden': 'bulasmis-oturumda-yazma'}` (aynı adımda hem `guvenilmez_girdi=True` hem `arac='pr_create'` ise de bu kural tetiklenir).
- Tüm adımlar kurallara uyarsa `{'izin': True, 'engel_adimi': None, 'neden': 'temiz'}` döndür.

KUSURLU başlangıç `bulasti` durumunu adımlar arasında taşımadığı için 0. adımda güvenilmeyen `issue` okunup 2. adımda `pr_create` yapıldığında izin veriyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def arac_zinciri_denetle(adimlar, kapsam):
    for i, a in enumerate(adimlar):
        if a['repo'] != kapsam:
            return {'izin': False, 'engel_adimi': i, 'neden': 'kapsam-disi-depo'}
        if a['guvenilmez_girdi'] and a['arac'] == 'pr_create':
            return {'izin': False, 'engel_adimi': i, 'neden': 'bulasmis-oturumda-yazma'}
    return {'izin': True, 'engel_adimi': None, 'neden': 'temiz'}
```

```solution
_IZINLI_ARACLAR = {'issue_read', 'file_read', 'pr_create'}

def _depo_ok(d):
    return isinstance(d, str) and d == d.strip() and not any(c.isspace() for c in d) and len(d.split('/')) == 2 and all(d.split('/'))

def arac_zinciri_denetle(adimlar, kapsam):
    if not _depo_ok(kapsam) or not isinstance(adimlar, list) or not adimlar:
        raise ValueError('gecerli adimlar ve kapsam gerekli')
    for a in adimlar:
        if (not isinstance(a, dict) or a.get('arac') not in _IZINLI_ARACLAR
                or not _depo_ok(a.get('repo')) or type(a.get('guvenilmez_girdi')) is not bool):
            raise ValueError('bozuk adim semasi')
    bulasti = False
    for i, a in enumerate(adimlar):
        if a['repo'] != kapsam:
            return {'izin': False, 'engel_adimi': i, 'neden': 'kapsam-disi-depo'}
        if a['guvenilmez_girdi']:
            bulasti = True
        if bulasti and a['arac'] == 'pr_create':
            return {'izin': False, 'engel_adimi': i, 'neden': 'bulasmis-oturumda-yazma'}
    return {'izin': True, 'engel_adimi': None, 'neden': 'temiz'}
```

```test
need('arac_zinciri_denetle')
_saldiri_izi = [
    {'arac': 'issue_read', 'repo': 'kurum/cekirdek', 'guvenilmez_girdi': True},
    {'arac': 'file_read', 'repo': 'kurum/cekirdek', 'guvenilmez_girdi': False},
    {'arac': 'pr_create', 'repo': 'kurum/cekirdek', 'guvenilmez_girdi': False},
]
eq(arac_zinciri_denetle(_saldiri_izi, 'kurum/cekirdek'), {
    'izin': False,
    'engel_adimi': 2,
    'neden': 'bulasmis-oturumda-yazma',
}, '0. adımdaki taint 2. adımdaki PR yazımını durdurmalı')

_capraz_iz = [
    {'arac': 'file_read', 'repo': 'kurum/cekirdek', 'guvenilmez_girdi': False},
    {'arac': 'file_read', 'repo': 'kurum/gizli-kasa', 'guvenilmez_girdi': False},
]
eq(arac_zinciri_denetle(_capraz_iz, 'kurum/cekirdek'), {
    'izin': False,
    'engel_adimi': 1,
    'neden': 'kapsam-disi-depo',
}, 'kapsam dışı depo okuması anında durdurulmalı')

_mesru_salt_okuma = [
    {'arac': 'issue_read', 'repo': 'kurum/cekirdek', 'guvenilmez_girdi': True},
    {'arac': 'file_read', 'repo': 'kurum/cekirdek', 'guvenilmez_girdi': False},
]
eq(arac_zinciri_denetle(_mesru_salt_okuma, 'kurum/cekirdek'), {
    'izin': True,
    'engel_adimi': None,
    'neden': 'temiz',
}, 'yazma yapılmayan issue triyaj okuması korunmalı')

_mesru_ic_pr = [
    {'arac': 'file_read', 'repo': 'kurum/cekirdek', 'guvenilmez_girdi': False},
    {'arac': 'pr_create', 'repo': 'kurum/cekirdek', 'guvenilmez_girdi': False},
]
eq(arac_zinciri_denetle(_mesru_ic_pr, 'kurum/cekirdek'), {
    'izin': True,
    'engel_adimi': None,
    'neden': 'temiz',
}, 'güvenilir kaynaklarla kapsam içi PR açılabilmeli')

for _bozuk in (([], 'kurum/a'), (_mesru_ic_pr, 'hatali'), ([{'arac': 'sil', 'repo': 'k/a', 'guvenilmez_girdi': False}], 'k/a'), ([{'arac': 'file_read', 'repo': 'k/a', 'guvenilmez_girdi': 1}], 'k/a')):
    raises(ValueError, arac_zinciri_denetle, *_bozuk, msg='şema dışı girdi ValueError fırlatmalı')

# Her şema kuralı tek başına: adım listesi, adım türü ve depo kimliği biçimi.
raises(ValueError, arac_zinciri_denetle, tuple(_mesru_ic_pr), 'kurum/cekirdek', msg='liste olmayan adımlar ValueError')
raises(ValueError, arac_zinciri_denetle, _mesru_ic_pr + ['pr_create'], 'kurum/cekirdek', msg='dict olmayan adım ValueError')
for _repo in (5, 'tekparca', 'kurum/', 'kurum/de po', 'kurum/depo\t'):
    _adim = [{'arac': 'file_read', 'repo': _repo, 'guvenilmez_girdi': False}]
    raises(ValueError, arac_zinciri_denetle, _adim, 'kurum/cekirdek', msg=f'bozuk depo kimliği adımda ValueError: {_repo!r}')
for _kapsam in (5, 'kurum/', 'kurum/de po'):
    raises(ValueError, arac_zinciri_denetle, _mesru_ic_pr, _kapsam, msg=f'bozuk kapsam ValueError: {_kapsam!r}')
```

```hint
Önce bütün adımların şemasını doğrula; ardından yürütme döngüsünde `bulasti` değişkenini döngü dışında başlat ki önceki adımın `guvenilmez_girdi=True` etkisi sonraki tüm adımlarda hatırlansın.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Olay bağlamı (15 sn).** "Invariant Labs'ın GitHub MCP analizi, sunucu kodunda klasik açık yokken bile geniş yetkili bir ajanın açık `issue` verisinden tetiklenip özel depo verisini PR ile sızdırabildiğini gösterdi."
2. **Mekanizma (30 sn).** "Kullanıcının jetonu iki depoya da yetkilidir ama kararı insan değil, güvenilmeyen `issue` metnini okumuş olan model vermektedir (`toxic agent flow`)."
3. **Kapsam sınırı (30 sn).** "Yalnız organizasyon sahibini (`kurum/*`) veya `okunan == yazilan` eşitliğini kontrol etmek yetmez; görev oturumu tek `kapsam` deposuna kilitlenmelidir."
4. **Zincir takibi ve ölçüm (25 sn).** "Senaryo koşusunda çapraz sızıntıyı `0.75` oranından `0.0`'a indirdim; `arac_zinciri_denetle` ile de bulaşmış oturumda `pr_create` adımını insan onayına düşürdüm."
5. **Kapanış (20 sn).** "MCP güvenliği tekil araç şemasıyla bitmez; oturum boyunca veri akışı ve `taint` durumu izlenmelidir."
:::

::: anlat Sınır ve kaynak
Bu derste depo kapsamı tek bir `'sahip/ad'` dizgesiyle modellenmiştir. Gerçek mikroservis geliştirme görevlerinde bir ajanın iki iç depoyu birlikte okuması gerekebilir; bu durumda politika depo kümesini (`allowlist set`) tanımlamalı, açık depolardan gelen her metni `untrusted` işaretleyerek insan onayı (`human-in-the-loop`) olmadan dış yazma araçlarını kilitlemelidir (`ai-savunma-12`).

- Birincil kaynak: [Invariant Labs — GitHub MCP Exploited: Accessing private repositories via MCP (Mayıs 2025)](https://invariantlabs.ai/blog/mcp-github-vulnerability). Doğrulama tarihi: 10 Kasım 2026.
:::

::: dusun
Açık kaynak bir depoda kullanıcıların açtığı `issue` kayıtlarını okuyup otomatik hata düzeltme `pull request`'i hazırlayan bir otonom kod ajanında, `bulasmis-oturumda-yazma` kuralını tamamen yasaklamak yerine hangi iki aşamalı mimari (`Dual-LLM` / ayrıcalıksız taslak + insan onaylı yayın) hem işi yürütür hem gizli anahtar sızıntısını önler?
:::

::: ozet
- MCP sunucusunun kimlik doğrulaması sağlam olsa bile geniş kapsamlı jeton + güvenilmeyen girdi `toxic agent flow` doğurur.
- Oturum jetonları organizasyon geneline değil, görevin gerektirdiği tekil hedef depoya (`kapsam`) sınırlandırılır.
- Güvenilmeyen bir kaynak okunduğu anda oturum `tainted` işaretlenmeli ve durum değiştiren dış yazma araçları (`pr_create` vb.) durdurulmalıdır.
:::
