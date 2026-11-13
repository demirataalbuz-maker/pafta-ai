---
id: ai-olay-15
title: "Kurumsal Harici LLM Sızıntısı · Veri Sınıflandırma ve DLP Kapısı"
summary: Doğrulanmamış basın söylentilerini resmi kamu rehberinden ayır; kurumsal veri sınıfları (public/internal/secret) için DLP çıkış kapısını, senaryo ölçümünü ve içerik yükseltmesini kur.
esleme: ai-saldiri-48, ai-savunma-09, ai-savunma-14, ai-savunma-02
timeout: 30
---

::: anlat 1. Gerçek olay ve yerel kopya sınırı
2023 baharında basında çeşitli şirket çalışanlarının kaynak kodu ve toplantı notlarını tüketici tipi harici sohbet botlarına yapıştırdığına dair haberler geniş yer buldu (örneğin basında sıkça anılan Samsung haberleri). **Kaynak dürüstlüğü gereği not edilmelidir ki:** bu basın haberlerine ait doğrulanmış birincil bir resmi şirket olay raporu açık kaynaklarda mevcut değildir; dolayısıyla bu derste herhangi bir şirketin iç olay ayrıntısı **iddia edilmez**. Bunun yerine **Kanada Hükümeti'nin resmi Üretken Yapay Zekâ Kullanım Rehberi** (*Guide on the use of Generative AI*) gibi birincil kurumsal politika belgelerindeki temel kural model alınır: hassas/gizli veriler kamuya açık harici modellere gönderilemez, kurum içi veriler ise yalnız sözleşmeli/yönetilen (`managed`) ortamlara açık onayla iletilebilir.

> [!NOTE]
> **Yerel kopya ayrımı:** Bu derste harici bir API çağrılmaz. Kurumsal **Veri Kaybı Önleme (`DLP`)** çıkış matrisinin, canlı senaryo ölçümünün ve yanlış etiketlenmiş istemlerde içerik tabanlı sınıf yükseltmesinin nasıl çalıştığı yerel Python modeliyle incelenir.
:::

::: anlat 2. Mekanizma · veri sınıfı, hedef ortam ve onay bayrağı matrisi
Kurumsal AI ağ geçidinde (`AI Gateway`) her istem üç eksende değerlendirilir (`ai-savunma-02`, `ai-savunma-09`):

| Veri sınıfı (`sinif`) | `'external'` (Tüketici / Açık Model) | `'managed'` (Kurumsal Sözleşmeli Model) |
|---|---|---|
| `'public'` | İzinli (`onayli` `bool` olmak kaydıyla) | İzinli (`onayli` `bool` olmak kaydıyla) |
| `'internal'` | **Yasak (`False`)** | Yalnız `onayli is True` ise izinli |
| `'secret'` | **Yasak (`False`)** | **Yasak (`False`)** |

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| `if sinif == 'public': return True` satırını `hedef` kontrolünden önce yazmak | `('public', 'golge-ai', False)` gibi kayıt dışı gölge hedeflere ve `onayli=1` tür bozulmalarına izin verir | Önce `sinif`, `hedef` ve `type(onayli) is bool` şemasını doğrulamak |
| Kullanıcının seçtiği `'public'` etiketine içerik taraması yapmadan güvenmek | Etiket `'public'` seçilip gövdeye özel anahtar veya iç kod yapıştırıldığında sızıntı gerçekleşir | Beyan edilen sınıfı içerik duyarlı sır taramasıyla (`content-aware DLP`) yükseltmek |
| `if onayli:` gibi doğruluk (`truthiness`) kontrolü kullanmak | `'hayir'` dizgesi veya `1` tamsayısı `True` sanılarak kurumsal onayı atlar | Kesin `onayli is True` kontrolü |

:::

::: tahmin Yalnız `sinif == 'public'` kontrolü gölge (`shadow AI`) hedefi neden kaçırır?
Geliştirici `if sinif == 'public': return True` satırını `hedef` doğrulamasından **önce** yazarsa kayıt dışı bir hedef URL/ortama ne olur?

```python
def hatali_sira(sinif, hedef, onayli):
    if sinif == 'public':
        return True
    return hedef in ('external', 'managed') and sinif == 'internal' and onayli is True

def dogru_sira(sinif, hedef, onayli):
    if sinif not in ('public', 'internal', 'secret') or hedef not in ('external', 'managed') or type(onayli) is not bool:
        return False
    return sinif == 'public' or (sinif == 'internal' and hedef == 'managed' and onayli is True)

print('hatalı sıra (golge-ai):', hatali_sira('public', 'golge-ai', False))
print('doğru sıra (golge-ai):', dogru_sira('public', 'golge-ai', False))
```

???

```cikti
hatalı sıra (golge-ai): True
doğru sıra (golge-ai): False
```
Veri kamuya açık (`public`) olsa bile kurumsal ağ geçidi yalnız envanterdeki `'external'` ve `'managed'` hedeflere trafiğe izin verir; tanımsız `'golge-ai'` hedefleri telemetri ve denetim dışıdır.
:::

::: gorev 1 · Kurumsal DLP çıkış matrisini (`dlp_izin`) kur
`dlp_izin(sinif, hedef, onayli)` işlevini yaz:

- `sinif` yalnız `('public', 'internal', 'secret')` kümesinden, `hedef` yalnız `('external', 'managed')` kümesinden olmalı ve `type(onayli) is bool` olmalı; aksi her girdide `False` döndür.
- İzin kuralları:
  - `'public'`: geçerli her iki hedefe (`'external'` ve `'managed'`) `True`;
  - `'internal'`: **yalnız** `hedef == 'managed'` **ve** `onayli is True` iken `True`;
  - `'secret'`: hiçbir dış/yönetilen hedefe çıkmaz (`False`).

KUSURLU başlangıç `onayli` bayrağını hiç kontrol etmiyor ve `sinif == 'public'` dalında `hedef` kümesini doğrulamıyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[\n  "internal",\n  "external",\n  true\n]', encoding='utf-8')
```

```starter
def dlp_izin(sinif, hedef, onayli):
    if sinif == 'public':
        return True
    if sinif == 'internal' and hedef == 'managed':
        return True
    return False

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(dlp_izin(*_args))
```

```solution
def dlp_izin(sinif, hedef, onayli):
    if (
        sinif not in ('public', 'internal', 'secret')
        or hedef not in ('external', 'managed')
        or type(onayli) is not bool
    ):
        return False
    if sinif == 'public':
        return True
    return sinif == 'internal' and hedef == 'managed' and onayli is True

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(dlp_izin(*_args))
```

```test
need('dlp_izin')
_izinli = [
    ('public', 'external', False),
    ('public', 'external', True),
    ('public', 'managed', False),
    ('public', 'managed', True),
    ('internal', 'managed', True),
]
for _s, _h, _o in _izinli:
    eq(dlp_izin(_s, _h, _o), True, f'meşru DLP kombinasyonu geçmeli: {(_s, _h, _o)}')

_yasak = [
    ('internal', 'external', True),
    ('internal', 'external', False),
    ('internal', 'managed', False),
    ('internal', 'managed', 1),
    ('secret', 'external', True),
    ('secret', 'managed', True),
    ('secret', 'managed', False),
    ('public', 'golge-ai', True),
    ('public', 'external', 0),
    ('public', 'external', None),
    ('gizli', 'managed', True),
    (None, 'managed', True),
]
for _s, _h, _o in _yasak:
    eq(dlp_izin(_s, _h, _o), False, f'yasaklı veya şema dışı DLP çağrısı reddedilmeli: {(_s, _h, _o)!r}')
```

```hint
Önce üç argümanın şemasını (`sinif`, `hedef` ve `type(onayli) is bool`) doğrula; ardından `'public'` ve `('internal' + 'managed' + onayli is True)` dallarını döndür.
```
:::

::: gorev 2 · Açık ve yamalı DLP kapısını senaryo vakalarında ölç
`dlp_senaryo_olc(vakalar, acik_fn, yamali_fn)` işlevini yaz:

- Her vaka `{'saldiri': bool, 'girdi': (sinif, hedef, onayli), ...}` sözlüğüdür. Şema veya çağrılabilirlik bozuksa `ValueError` fırlat.
- Sınır işlevi `True` döndürdüğünde istem **dışarı gönderildi** sayılır.
- Saldırı vakalarında gönderim **kurumsal veri sızıntısı (`sizma`)**, meşru vakalarda gönderim **meşru kabul** demektir.
- Dönüş: `{'saldiri_n': int, 'mesru_n': int, 'once_sizma': float|None, 'sonra_sizma': float|None, 'mesru_kabul': float|None, 'regresyon_n': int}`.

KUSURLU başlangıç `mesru_kabul` oranını `yamali_fn` yerine `acik_fn` üzerinden hesapladığı için her şeyi engelleyen bozuk bir yamayı bile `1.0` kabul oranında gösteriyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def dlp_senaryo_olc(vakalar, acik_fn, yamali_fn):
    s = [v for v in vakalar if v['saldiri']]
    m = [v for v in vakalar if not v['saldiri']]
    return {
        'saldiri_n': len(s), 'mesru_n': len(m),
        'once_sizma': round(sum(1 for v in s if acik_fn(*v['girdi'])) / len(s), 4) if s else None,
        'sonra_sizma': round(sum(1 for v in s if yamali_fn(*v['girdi'])) / len(s), 4) if s else None,
        'mesru_kabul': round(sum(1 for v in m if acik_fn(*v['girdi'])) / len(m), 4) if m else None,
        'regresyon_n': 0,
    }
```

```solution
import copy

def dlp_senaryo_olc(vakalar, acik_fn, yamali_fn):
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
need('dlp_senaryo_olc')
from sandbox.ai_olay_senaryo import acik_sinir, senaryo_vakalari

def _yama(s, h, o):
    if s not in ('public', 'internal', 'secret') or h not in ('external', 'managed') or type(o) is not bool:
        return False
    return s == 'public' or (s == 'internal' and h == 'managed' and o is True)

_vakalar = senaryo_vakalari(15, tohum=15)
eq(dlp_senaryo_olc(_vakalar, acik_sinir(15), _yama), {
    'saldiri_n': 4,
    'mesru_n': 2,
    'once_sizma': 1.0,
    'sonra_sizma': 0.0,
    'mesru_kabul': 1.0,
    'regresyon_n': 0,
}, 'açık DLP 4/4 sızdırır, yamalı DLP sızıntıyı sıfırlar')

_hepsi_kapali = dlp_senaryo_olc(_vakalar, acik_sinir(15), lambda *_a: False)
eq(_hepsi_kapali['mesru_kabul'], 0.0, 'yamali_fn her şeyi reddettiğinde mesru_kabul 0.0 olmalı')
eq(_hepsi_kapali['regresyon_n'], 2, '2 meşru vaka regresyona düşmeli')
raises(ValueError, dlp_senaryo_olc, [], acik_sinir(15), _yama, msg='boş liste ValueError')

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
eq(dlp_senaryo_olc(_el, _acik_el, _yama_el), {
    'saldiri_n': 3,
    'mesru_n': 3,
    'once_sizma': 0.6667,
    'sonra_sizma': 0.3333,
    'mesru_kabul': 0.3333,
    'regresyon_n': 1,
}, 'oranlar grup paydasıyla ve 4 basamakla; sıfırdan farklı sonra_sizma ve regresyon doğru sayılmalı')
eq(dlp_senaryo_olc(_el, _acik_el, _acik_el)['sonra_sizma'], 0.6667, 'yama açık sınırla aynıysa sonra_sizma = once_sizma')
eq(dlp_senaryo_olc(_el, lambda *_a: False, lambda *_a: False)['regresyon_n'], 0,
   'açık sınırın da reddettiği meşru vaka regresyon sayılmaz')
eq(dlp_senaryo_olc([v for v in _el if not v['saldiri']], _acik_el, _yama_el),
   {'saldiri_n': 0, 'mesru_n': 3, 'once_sizma': None, 'sonra_sizma': None, 'mesru_kabul': 0.3333, 'regresyon_n': 1},
   'saldırı vakası yoksa once_sizma ve sonra_sizma None')
eq(dlp_senaryo_olc([v for v in _el if v['saldiri']], _acik_el, _yama_el)['mesru_kabul'], None, 'meşru vaka yoksa mesru_kabul None')
raises(ValueError, dlp_senaryo_olc, tuple(_el), _acik_el, _yama_el, msg='liste olmayan vakalar ValueError')
raises(ValueError, dlp_senaryo_olc, _el, None, _yama_el, msg='çağrılamaz açık sınır ValueError')
raises(ValueError, dlp_senaryo_olc, _el, _acik_el, 'yama', msg='çağrılamaz yamalı sınır ValueError')
for _bozuk in (
    _el + [('s-ikisi-gecer',)],
    _el + [{'saldiri': 1, 'girdi': ('s-ikisi-gecer',)}],
    _el + [{'saldiri': True, 'girdi': None}],
):
    raises(ValueError, dlp_senaryo_olc, _bozuk, _acik_el, _yama_el, msg=f'bozuk vaka şeması ValueError: {_bozuk[-1]!r}')
```

```hint
`mesru_kabul` oranını `yamali_fn` sonuçlarının toplamı üzerinden hesapla ve `once_ok and not sonra_ok` olduğunda `regresyon_n` artır.
```
:::

::: gorev 3 · Yanlış beyan edilen istemlerde içerik duyarlı sınıf yükseltmesi yap
Çalışan istemi yanlışlıkla `'public'` olarak etiketlese bile metnin içindeki sentetik kurumsal işaretçileri tarayıp etkin sınıfı **asla düşürmeden yalnızca yükselterek** DLP kararı veren `icerik_duyarli_dlp(metin, beyan_sinifi, hedef, onayli)` işlevini yaz:

- `metin` `str` olmalı, `beyan_sinifi` `('public', 'internal', 'secret')`, `hedef` `('external', 'managed')` ve `type(onayli) is bool` olmalı; aksi halde `ValueError` fırlat.
- Gizlilik sıralaması: `'public' < 'internal' < 'secret'`.
- İçerik taraması (büyük/küçük harf duyarsız, `casefold`):
  - Metinde `'begin private key'` veya `'api_secret_'` geçiyorsa içerik düzeyi `'secret'`;
  - Bunlar yok ama `'ic-kaynak-kodu'` veya `'gizli-toplanti-notu'` geçiyorsa içerik düzeyi `'internal'`;
  - Hiçbiri yoksa içerik düzeyi `'public'`.
- `etkin_sinif`: `beyan_sinifi` ile içerik düzeyinden **daha yüksek gizlilikte** olanı seç! (Örn. kullanıcı `'secret'` beyan ettiyse metin düz olsa bile `'secret'` kalır; kullanıcı `'public'` beyan etti ama metinde `'IC-KAYNAK-KODU'` varsa `'internal'` olur.)
- Ardından `etkin_sinif`, `hedef`, `onayli` üzerinde Görev 1'deki DLP kuralını uygula.
- Dönüş: `{'etkin_sinif': str, 'yukseltildi': bool, 'izin': bool}` (`yukseltildi`: `etkin_sinif != beyan_sinifi`).

KUSURLU başlangıç metin temiz göründüğünde kullanıcının `'secret'` beyanını `'public'` düzeyine düşürüyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def icerik_duyarli_dlp(metin, beyan_sinifi, hedef, onayli):
    k = metin.casefold()
    etkin = 'secret' if 'api_secret_' in k else ('internal' if 'ic-kaynak-kodu' in k else 'public')
    izin = etkin == 'public' or (etkin == 'internal' and hedef == 'managed' and onayli is True)
    return {'etkin_sinif': etkin, 'yukseltildi': etkin != beyan_sinifi, 'izin': izin}
```

```solution
_DERECE = {'public': 0, 'internal': 1, 'secret': 2}
_TERS = {0: 'public', 1: 'internal', 2: 'secret'}

def icerik_duyarli_dlp(metin, beyan_sinifi, hedef, onayli):
    if (
        not isinstance(metin, str)
        or beyan_sinifi not in _DERECE
        or hedef not in ('external', 'managed')
        or type(onayli) is not bool
    ):
        raise ValueError('gecersiz argumanlar')
    kucuk = metin.casefold()
    if 'begin private key' in kucuk or 'api_secret_' in kucuk:
        icerik_sinifi = 'secret'
    elif 'ic-kaynak-kodu' in kucuk or 'gizli-toplanti-notu' in kucuk:
        icerik_sinifi = 'internal'
    else:
        icerik_sinifi = 'public'
    etkin_derece = max(_DERECE[beyan_sinifi], _DERECE[icerik_sinifi])
    etkin_sinif = _TERS[etkin_derece]
    izin = etkin_sinif == 'public' or (etkin_sinif == 'internal' and hedef == 'managed' and onayli is True)
    return {
        'etkin_sinif': etkin_sinif,
        'yukseltildi': etkin_sinif != beyan_sinifi,
        'izin': izin,
    }
```

```test
need('icerik_duyarli_dlp')
eq(icerik_duyarli_dlp('Bu kodda IC-KAYNAK-KODU modülü var', 'public', 'external', True), {
    'etkin_sinif': 'internal', 'yukseltildi': True, 'izin': False,
}, 'public beyanlı kaynak kodu internal sınıfına yükseltilmeli ve external hedefe engellenmeli')

eq(icerik_duyarli_dlp('Bu kodda IC-KAYNAK-KODU modülü var', 'public', 'managed', True), {
    'etkin_sinif': 'internal', 'yukseltildi': True, 'izin': True,
}, 'internal seviyesine yükseltilen içerik onaylı managed hedefe gidebilmeli')

eq(icerik_duyarli_dlp('Baglanti anahtari API_SECRET_9912', 'internal', 'managed', True), {
    'etkin_sinif': 'secret', 'yukseltildi': True, 'izin': False,
}, 'secret işaretçisi managed hedefe bile çıkışı kapatmalı')

eq(icerik_duyarli_dlp('Düz metin görünen strateji özeti', 'secret', 'managed', True), {
    'etkin_sinif': 'secret', 'yukseltildi': False, 'izin': False,
}, 'kullanıcının yüksek gizlilikli secret beyanı asla public düzeyine düşürülmemeli!')

for _bozuk in ((None, 'public', 'external', False), ('x', 'hatali', 'external', False), ('x', 'public', 'golge', False), ('x', 'public', 'external', 1)):
    raises(ValueError, icerik_duyarli_dlp, *_bozuk, msg='şema hatası ValueError')

eq(icerik_duyarli_dlp('Kamuya açık duyuru metni', 'public', 'external', False), {
    'etkin_sinif': 'public', 'yukseltildi': False, 'izin': True,
}, 'işaretçisi olmayan public içerik public kalır ve dışarı çıkabilir')
eq(icerik_duyarli_dlp('-----BEGIN PRIVATE KEY-----\nMIIE...', 'internal', 'managed', True), {
    'etkin_sinif': 'secret', 'yukseltildi': True, 'izin': False,
}, 'özel anahtar başlığı (büyük/küçük harf fark etmez) secret işaretçisidir')
eq(icerik_duyarli_dlp('Ekte Gizli-Toplanti-Notu var', 'public', 'external', True), {
    'etkin_sinif': 'internal', 'yukseltildi': True, 'izin': False,
}, 'gizli-toplanti-notu da internal işaretçisidir')
eq(icerik_duyarli_dlp('Bu kodda IC-KAYNAK-KODU modülü var', 'public', 'managed', False), {
    'etkin_sinif': 'internal', 'yukseltildi': True, 'izin': False,
}, 'internal içerik managed hedefe de onaysız gidemez')
```

```hint
Gizlilik sınıflarına `0, 1, 2` sırası verip `max(beyan, icerik)` alırsan beyan edilen sınıf hiçbir zaman aşağı düşmez, yalnız yukarı yükselir (`monotonic classification`).
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Kaynak disiplini (15 sn).** "Basındaki doğrulanmamış şirket sızıntısı öykülerini kanıt saymak yerine Kanada Hükümeti'nin birincil Üretken AI Kullanım Rehberi'ndeki veri sınıflandırma ilkelerini temel aldım."
2. **Matris (30 sn).** "`public`, `internal` ve `secret` veriler tüketici (`external`) ve kurumsal sözleşmeli (`managed`) modellere aynı kuralla çıkamaz; kayıt dışı gölge hedefler ise tüm sınıflara kapalıdır."
3. **Ölçüm (30 sn).** "`dlp_izin` ve `dlp_senaryo_olc` ile onaysız iç veri ve gölge hedef sızıntılarını `1.0`'dan `0.0`'a indirdim."
4. **Monotonik yükseltme (25 sn).** "`icerik_duyarli_dlp` ile kullanıcının düşük beyanını içerik işaretçisiyle yukarı yükselttim ama yüksek beyanı asla aşağı düşürmedim."
5. **Kapanış (20 sn).** "Etkili AI yönetişimi yalnız yasak koymak değil, onaylı `managed` kanalı açık tutarak çalışanı gölge AI kullanımından uzaklaştırmaktır."
:::

::: anlat Sınır ve kaynak
Desen tabanlı DLP tarayıcıları yapılandırılmış sırları (`PRIVATE KEY`, API jeton önekleri, kurum içi başlıklar) yüksek doğrulukla yakalar; ancak bağlamsal ticari sırları (örneğin henüz açıklanmamış bir satın alma kararının düz cümlelerle anlatılması) yalnız kelime aramasıyla her zaman yakalayamaz (`ai-savunma-09`).

- Birincil politika kaynağı: [Government of Canada — Guide on the use of Generative AI](https://www.canada.ca/en/government/system/digital-government/digital-government-innovations/responsible-use-ai/generative-ai/guide-use-generative-ai.html) *(genel resmi rehber; herhangi bir özel şirket olayı kanıtı değildir)*. Doğrulama tarihi: 10 Kasım 2026.
:::

::: dusun
Bir kurum bütün harici ve yönetilen AI araçlarını tamamen yasaklarsa (`hedef` her zaman `False`), Görev 2'deki `mesru_kabul` oranı sıfırlanırken kurum içinde denetimsiz kişisel cihazlardan yapılan `shadow AI` riski nasıl değişir?
:::

::: ozet
- Doğrulanmamış ikincil basın haberleri olay kanıtı olarak sunulmaz; kurumsal DLP politikası açık sınıflandırma kurallarına dayandırılır.
- Ağ geçidi hem veri sınıfını (`public`/`internal`/`secret`), hem hedef envanterini (`external`/`managed`), hem açık onayı doğrular.
- İçerik taraması gizlilik sınıfını yalnız yukarı yükseltebilir (`monotonic`), kullanıcının yüksek gizlilik beyanını düşüremez.
:::
