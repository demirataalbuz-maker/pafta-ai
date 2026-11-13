---
id: ai-olay-16
title: "Ticari Sohbet Botu Vaatleri · Sözleşme ve Politika Doğrulama Kapısı"
summary: Air Canada (2024 BCCRT 149) karar özetindeki sorumluluk ilkesinden yola çıkarak modelin ürettiği fiyat, para birimi ve iade politikası vaatlerini deterministik tabloyla doğrula.
esleme: ai-saldiri-09, ai-savunma-08, ai-savunma-29, ai-guvence-04
timeout: 30
---

::: anlat 1. Gerçek olay ve yerel kopya sınırı
Şubat 2024 tarihli **Moffatt v. Air Canada (2024 BCCRT 149)** uyuşmazlığında (CanLII Mart 2024 bülteninde karar kimliği ve özeti yer alır; CanLII tam karar sayfası otomatik erişimde HTTP 403 döndürdüğünden paragraf numaraları yerine yalnız doğrulanmış karar ilkesi aktarılmıştır), müşteri destek sohbet botu yolcuya cenaze indirimi için **yolculuktan sonra geriye dönük iade başvurusu yapılabileceğini** söylemiş; oysa şirketin resmi tarife sayfası geriye dönük başvuruyu açıkça reddediyordu. Uyuşmazlık mahkemesi, sohbet botunun şirketin web sitesinden bağımsız ayrı bir hukuki kişilik gibi tutulamayacağına işaret ederek şirketi sorumlu buldu.

*(Kaynak dürüstlüğü notu: Sosyal medyada sıkça paylaşılan "Chevrolet sohbet botunun 1 dolara araç satmayı kabul etmesi" öyküsü için doğrulanmış birincil mahkeme veya üretici olay kaydı bulunmadığından bu derste olgusal vaka olarak iddia edilmez; `1` birimlik fiyat yalnız sentetik sınır testi verisi olarak kullanılır.)*

> [!NOTE]
> **Yerel kopya ayrımı:** Bu ders hukuki danışmanlık vermez; üretken bir modelin müşteriye bağlayıcı fiyat, para birimi veya iade koşulu sunmadan önce neden **deterministik uygulama katmanı doğrulayıcısından (`authoritative policy gate`)** geçmesi gerektiğini yerel Python modeliyle inceler.
:::

::: anlat 2. Mekanizma · olasılıksal metin üreticisi neden sözleşme otoritesi olamaz?
Bir dil modeli kendi başına ne güncel veritabanı fiyatını ne de yürürlükteki tarife sürümünü garanti edebilir; halüsinasyonla eski sürüm bir kuralı (`'v1'`) veya yönlendirmeyle `1` birimlik teklifi "onaylı" ifadelerle sunabilir (`ai-saldiri-09`, `ai-savunma-08`).

Deterministik sözleşme kapısı modelin ürettiği doğal dildeki "onaylandı / garantilidir" süslemelerine hiç bakmaz; yapılandırılmış teklif alanlarını yetkili politika kaydıyla birebir eşleştirir:
1. **Tam sayı/tür bütünlüğü:** `fiyat` alanı `bool` olmayan pozitif `int` (`type(fiyat) is int and fiyat > 0`) olmalıdır.
2. **Çok alanlı tam uyum:** Yalnız `fiyat` eşitliğine bakmak ölümcül bir hatadır: `1200 TRY` ile `1200 USD` veya yürürlükten kalkmış `'2022-v1'` iade sürümü ile aktif `'2026-v2'` sürümü tamamen farklı ticari yükümlülüklerdir!

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| Yalnız `model_teklifi['fiyat'] == politika['fiyat']` kontrolü yapmak | `1200 TRY` yerine `1200 USD` veya iptal edilmiş eski sözleşme sürümünü (`surum`) geçirir | `('fiyat', 'para_birimi', 'surum')` üçlüsünün tamamında birebir eşitlik |
| `isinstance(fiyat, int)` ve `fiyat >= 0` kullanmak | `fiyat=True` (`1`) ve `fiyat=0` bedelsiz tekliflerini geçerli sayar | `type(fiyat) is int and fiyat > 0` |
| Geriye dönük iade gibi koşulları serbest metne bırakmak | *Moffatt* vakasındaki gibi resmi politikayla çelişen vaat üretir | Yapılandırılmış iade alanlarını resmi politika tablosuyla doğrulamak |
:::

::: tahmin Fiyat aynıyken para birimi ve politika sürümü farkı nasıl gözden kaçar?
Yalnız fiyat alanını karşılaştıran zayıf doğrulayıcı aşağıdaki iki teklife ne yanıt verir?

```python
politika = {'fiyat': 1200, 'para_birimi': 'USD', 'surum': '2026-v2'}
aday_kur = {'fiyat': 1200, 'para_birimi': 'TRY', 'surum': '2026-v2'}
aday_eski = {'fiyat': 1200, 'para_birimi': 'USD', 'surum': '2022-v1'}

for ad, teklif in [('kur farkı', aday_kur), ('eski sürüm', aday_eski)]:
    yalniz_fiyat = (teklif['fiyat'] == politika['fiyat'])
    tam_eslesme = all(teklif[k] == politika[k] for k in ('fiyat', 'para_birimi', 'surum'))
    print(ad, '-> yalnız fiyat:', yalniz_fiyat, '| tam eşleşme:', tam_eslesme)
```

???

```cikti
kur farkı -> yalnız fiyat: True | tam eşleşme: False
eski sürüm -> yalnız fiyat: True | tam eşleşme: False
```
Sayısal değer (`1200`) aynı kaldığı halde birincisi yanlış para birimiyle, ikincisi ise yürürlükten kalkmış eski sözleşme koşullarıyla bağlayıcı vaat üretir.
:::

::: gorev 1 · Fiyat, para birimi ve sürüm doğrulayıcısını (`teklif_dogrula`) kur
`teklif_dogrula(model_teklifi, politika)` işlevini yaz:

- Her iki argüman da `dict` olmalı ve her ikisi de şu şemayı sağlamalı:
  - `'fiyat'`: `bool` olmayan pozitif `int` (`type(r.get('fiyat')) is int and r['fiyat'] > 0`);
  - `'para_birimi'`: boş olmayan (ve kenar boşluksuz `s == s.strip()`) `str`;
  - `'surum'`: boş olmayan (ve kenar boşluksuz `s == s.strip()`) `str`.
- İki sözlük de geçerli şemadaysa ve `'fiyat'`, `'para_birimi'`, `'surum'` alanlarının **üçü birden** iki tarafta birebir eşitse `True`, diğer her durumda `False` döndür (sözlükteki `'onayli_metin'` gibi serbest doğal dil alanlarına güvenme).

KUSURLU başlangıç yalnız `fiyat` eşitliğine baktığı için para birimi ve politika sürümü uyuşmazlıklarını geçiriyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[\n  {\n    "fiyat": 1,\n    "para_birimi": "TRY",\n    "surum": "v1"\n  },\n  {\n    "fiyat": 100,\n    "para_birimi": "TRY",\n    "surum": "v1"\n  }\n]', encoding='utf-8')
```

```starter
def teklif_dogrula(model_teklifi, politika):
    if not isinstance(model_teklifi, dict) or not isinstance(politika, dict):
        return False
    return model_teklifi.get('fiyat') == politika.get('fiyat')

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(teklif_dogrula(*_args))
```

```solution
def _sozluk_gecerli(kayit):
    if not isinstance(kayit, dict):
        return False
    fiyat = kayit.get('fiyat')
    birim = kayit.get('para_birimi')
    surum = kayit.get('surum')
    return (
        type(fiyat) is int
        and fiyat > 0
        and isinstance(birim, str)
        and bool(birim)
        and birim == birim.strip()
        and isinstance(surum, str)
        and bool(surum)
        and surum == surum.strip()
    )

def teklif_dogrula(model_teklifi, politika):
    if not (_sozluk_gecerli(model_teklifi) and _sozluk_gecerli(politika)):
        return False
    return all(model_teklifi[k] == politika[k] for k in ('fiyat', 'para_birimi', 'surum'))

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(teklif_dogrula(*_args))
```

```test
need('teklif_dogrula')
_pol = {'fiyat': 1200, 'para_birimi': 'TRY', 'surum': '2026-v2'}
eq(teklif_dogrula({'fiyat': 1200, 'para_birimi': 'TRY', 'surum': '2026-v2'}, _pol), True, 'üç alanı da uyuşan geçerli teklif onaylanmalı')
eq(teklif_dogrula({'fiyat': 1200, 'para_birimi': 'TRY', 'surum': '2026-v2', 'not': 'onayli'}, _pol), True, 'ek bilgi alanı anahtar eşitliğini bozmaz')

_red_ciftler = [
    ({'fiyat': 1, 'para_birimi': 'TRY', 'surum': '2026-v2'}, _pol),
    ({'fiyat': 1200, 'para_birimi': 'USD', 'surum': '2026-v2'}, _pol),
    ({'fiyat': 1200, 'para_birimi': 'TRY', 'surum': '2022-v1'}, _pol),
    ({'fiyat': 0, 'para_birimi': 'TRY', 'surum': '2026-v2'}, {'fiyat': 0, 'para_birimi': 'TRY', 'surum': '2026-v2'}),
    ({'fiyat': -50, 'para_birimi': 'TRY', 'surum': '2026-v2'}, {'fiyat': -50, 'para_birimi': 'TRY', 'surum': '2026-v2'}),
    ({'fiyat': True, 'para_birimi': 'TRY', 'surum': '2026-v2'}, {'fiyat': 1, 'para_birimi': 'TRY', 'surum': '2026-v2'}),
    ({'fiyat': 1, 'para_birimi': 'TRY', 'surum': '2026-v2'}, {'fiyat': True, 'para_birimi': 'TRY', 'surum': '2026-v2'}),
    ({'fiyat': 1200.0, 'para_birimi': 'TRY', 'surum': '2026-v2'}, _pol),
    ({'fiyat': 1200, 'para_birimi': '', 'surum': '2026-v2'}, {'fiyat': 1200, 'para_birimi': '', 'surum': '2026-v2'}),
    ({'fiyat': 1200, 'para_birimi': ' TRY ', 'surum': '2026-v2'}, {'fiyat': 1200, 'para_birimi': ' TRY ', 'surum': '2026-v2'}),
    ({'fiyat': 1200, 'para_birimi': 'TRY', 'surum': ''}, {'fiyat': 1200, 'para_birimi': 'TRY', 'surum': ''}),
    (None, _pol),
    (_pol, 'politika'),
]
for _m, _p in _red_ciftler:
    eq(teklif_dogrula(_m, _p), False, f'uyumsuz veya bozuk teklif reddedilmeli: {(_m, _p)!r}')

_bir = {'fiyat': 1, 'para_birimi': 'TRY', 'surum': '2026-v2'}
eq(teklif_dogrula(_bir, dict(_bir)), True, 'en küçük pozitif fiyat (1) geçerli')
# Her iki tarafta da aynı bozuk değer: eşitlik geçer, yalnız şema kontrolü durdurur.
for _alan, _deger in (('para_birimi', 5), ('surum', 5), ('surum', ' 2026-v2 ')):
    _k = dict(_bir, **{_alan: _deger})
    eq(teklif_dogrula(_k, dict(_k)), False, f'iki tarafta aynı bozuk alan da reddedilmeli: {_alan}={_deger!r}')
```

```hint
Her iki sözlüğün de `_sozluk_gecerli` kontrolünden geçtiğini doğruladıktan sonra `('fiyat', 'para_birimi', 'surum')` anahtarlarının üçünde de eşitlik ara (`(0, 0)` veya `(True, 1)` ikilileri şemadan elenmelidir).
```
:::

::: gorev 2 · Açık ve yamalı sözleşme kapısını senaryo vakalarında ölç
`teklif_senaryo_olc(vakalar, acik_fn, yamali_fn)` işlevini yaz:

- Her vaka `{'saldiri': bool, 'girdi': (model_teklifi, politika), ...}` sözlüğüdür. Şema veya çağrılabilirlik bozuksa `ValueError` fırlat.
- Sınır işlevi `True` döndürdüğünde model teklifi **müşteriye iletildi** sayılır.
- Saldırı/halüsinasyon vakalarında iletim **yetkisiz ticari vaat (`sizma`)**, meşru vakalarda iletim **meşru kabul** demektir.
- Dönüş: `{'saldiri_n': int, 'mesru_n': int, 'once_sizma': float|None, 'sonra_sizma': float|None, 'mesru_kabul': float|None, 'regresyon_n': int}`.

KUSURLU başlangıç `sonra_sizma` ve `mesru_kabul` oranlarını yuvarlamadan ve boş grup kontrolü yapmadan hesaplıyor, ayrıca `regresyon_n` saymıyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def teklif_senaryo_olc(vakalar, acik_fn, yamali_fn):
    s = [v for v in vakalar if v['saldiri']]
    m = [v for v in vakalar if not v['saldiri']]
    return {
        'saldiri_n': len(s), 'mesru_n': len(m),
        'once_sizma': sum(1 for v in s if acik_fn(*v['girdi'])) / len(s),
        'sonra_sizma': sum(1 for v in s if yamali_fn(*v['girdi'])) / len(s),
        'mesru_kabul': sum(1 for v in m if yamali_fn(*v['girdi'])) / len(m),
        'regresyon_n': 0,
    }
```

```solution
import copy

def teklif_senaryo_olc(vakalar, acik_fn, yamali_fn):
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
need('teklif_senaryo_olc')
from sandbox.ai_olay_senaryo import acik_sinir, senaryo_vakalari

def _yama(m, p):
    def ok_s(r):
        return isinstance(r, dict) and type(r.get('fiyat')) is int and r['fiyat'] > 0 and isinstance(r.get('para_birimi'), str) and bool(r['para_birimi'].strip()) and isinstance(r.get('surum'), str) and bool(r['surum'].strip())
    return ok_s(m) and ok_s(p) and all(m[k] == p[k] for k in ('fiyat', 'para_birimi', 'surum'))

_vakalar = senaryo_vakalari(16, tohum=16)
eq(teklif_senaryo_olc(_vakalar, acik_sinir(16), _yama), {
    'saldiri_n': 4,
    'mesru_n': 2,
    'once_sizma': 1.0,
    'sonra_sizma': 0.0,
    'mesru_kabul': 1.0,
    'regresyon_n': 0,
}, 'açık sınır 1 birimlik, yanlış kurlu, eski sürümlü ve bool fiyatları geçirir (1.0); yama sıfırlar (0.0)')

_yalniz_fiyat = teklif_senaryo_olc(_vakalar, acik_sinir(16), lambda m, p: m.get('fiyat') == p.get('fiyat'))
eq(_yalniz_fiyat['sonra_sizma'], 0.75, 'yalnız fiyat kontrolü kur, sürüm ve True==1 vakalarını kaçırır (3/4 = 0.75)')
eq(teklif_senaryo_olc(_vakalar, acik_sinir(16), lambda *_a: False)['regresyon_n'], 2, 'tüm teklifleri reddeden kapı 2 regresyon üretir')
eq(teklif_senaryo_olc([v for v in _vakalar if v['saldiri']][:3], acik_sinir(16), lambda m, _p: m.get('fiyat') != 1)['sonra_sizma'], 0.6667, '4 ondalık yuvarlama çalışmalı')
raises(ValueError, teklif_senaryo_olc, [], acik_sinir(16), _yama, msg='boş liste ValueError')

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
eq(teklif_senaryo_olc(_el, _acik_el, _yama_el), {
    'saldiri_n': 3,
    'mesru_n': 3,
    'once_sizma': 0.6667,
    'sonra_sizma': 0.3333,
    'mesru_kabul': 0.3333,
    'regresyon_n': 1,
}, 'oranlar grup paydasıyla ve 4 basamakla; sıfırdan farklı sonra_sizma ve regresyon doğru sayılmalı')
eq(teklif_senaryo_olc(_el, _acik_el, _acik_el)['sonra_sizma'], 0.6667, 'yama açık sınırla aynıysa sonra_sizma = once_sizma')
eq(teklif_senaryo_olc(_el, lambda *_a: False, lambda *_a: False)['regresyon_n'], 0,
   'açık sınırın da reddettiği meşru vaka regresyon sayılmaz')
eq(teklif_senaryo_olc([v for v in _el if not v['saldiri']], _acik_el, _yama_el),
   {'saldiri_n': 0, 'mesru_n': 3, 'once_sizma': None, 'sonra_sizma': None, 'mesru_kabul': 0.3333, 'regresyon_n': 1},
   'saldırı vakası yoksa once_sizma ve sonra_sizma None')
eq(teklif_senaryo_olc([v for v in _el if v['saldiri']], _acik_el, _yama_el)['mesru_kabul'], None, 'meşru vaka yoksa mesru_kabul None')
raises(ValueError, teklif_senaryo_olc, tuple(_el), _acik_el, _yama_el, msg='liste olmayan vakalar ValueError')
raises(ValueError, teklif_senaryo_olc, _el, None, _yama_el, msg='çağrılamaz açık sınır ValueError')
raises(ValueError, teklif_senaryo_olc, _el, _acik_el, 'yama', msg='çağrılamaz yamalı sınır ValueError')
for _bozuk in (
    _el + [('s-ikisi-gecer',)],
    _el + [{'saldiri': 1, 'girdi': ('s-ikisi-gecer',)}],
    _el + [{'saldiri': True, 'girdi': None}],
):
    raises(ValueError, teklif_senaryo_olc, _bozuk, _acik_el, _yama_el, msg=f'bozuk vaka şeması ValueError: {_bozuk[-1]!r}')
```

```hint
`round(..., 4)` yuvarlamasını, boş grup `None` dönüşünü ve `once_ok and not sonra_ok` regresyon sayacını birlikte uygula.
```
:::

::: gorev 3 · İade ve indirim koşullarında geriye dönük vaat denetçisini kur
*Moffatt v. Air Canada* olayındaki asıl uyuşmazlık noktası olan **indirim tavanı, başvuru süresi ve geriye dönük iade hakkı** çelişkilerini yakalayan `iade_vaadi_denetle(model_vaadi, resmi_politika)` işlevini yaz:

- `model_vaadi`: `{'indirim_yuzdesi': int, 'basvuru_gun': int, 'geriye_donuk': bool, 'surum': str}` sözlüğü;
- `resmi_politika`: `{'maks_indirim_yuzdesi': int, 'maks_basvuru_gun': int, 'geriye_donuk_izin': bool, 'aktif_surum': str}` sözlüğü.
- Şema kontrolü: sayısal alanlar `bool` olmayan negatif olmayan `int` (`0 <= yuzde <= 100`, `gun >= 0`), mantıksal alanlar tam `bool`, sürüm alanları boş olmayan `str` olmalı; aksi halde `ValueError` fırlat.
- İhlalleri **tam şu sırayla** kontrol edip `ihlaller` listesine ekle:
  1. `'eski-surum'`: `model_vaadi['surum'] != resmi_politika['aktif_surum']`;
  2. `'indirim-asimi'`: `model_vaadi['indirim_yuzdesi'] > resmi_politika['maks_indirim_yuzdesi']`;
  3. `'sure-asimi'`: `model_vaadi['basvuru_gun'] > resmi_politika['maks_basvuru_gun']`;
  4. `'geriye-donuk-yasak'`: `resmi_politika['geriye_donuk_izin'] is False` iken `model_vaadi['geriye_donuk'] is True` vaat edilmesi! (Not: politika geriye dönük başvuruya izin veriyorsa `geriye_donuk=False` demek bir hak aşımı değildir.)
- Dönüş: `{'onay': len(ihlaller) == 0, 'ihlaller': ihlaller}`.

KUSURLU başlangıç `geriye_donuk` alanını eşitlikle (`!=`) kontrol ettiği için izinli politikada müşteriye "yolculuktan önce başvurabilirsiniz (`False`)" diyen doğru yanıtı bile ihlal sayıyor ve `indirim-asimi` sınırında `>=` hatası yapıyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def iade_vaadi_denetle(model_vaadi, resmi_politika):
    ihlaller = []
    if model_vaadi['indirim_yuzdesi'] >= resmi_politika['maks_indirim_yuzdesi']:
        ihlaller.append('indirim-asimi')
    if model_vaadi['geriye_donuk'] != resmi_politika['geriye_donuk_izin']:
        ihlaller.append('geriye-donuk-yasak')
    return {'onay': not ihlaller, 'ihlaller': ihlaller}
```

```solution
def iade_vaadi_denetle(model_vaadi, resmi_politika):
    if not isinstance(model_vaadi, dict) or not isinstance(resmi_politika, dict):
        raise ValueError('iki sozluk gerekli')
    ind = model_vaadi.get('indirim_yuzdesi')
    gun = model_vaadi.get('basvuru_gun')
    gd = model_vaadi.get('geriye_donuk')
    sur = model_vaadi.get('surum')
    m_ind = resmi_politika.get('maks_indirim_yuzdesi')
    m_gun = resmi_politika.get('maks_basvuru_gun')
    m_gd = resmi_politika.get('geriye_donuk_izin')
    a_sur = resmi_politika.get('aktif_surum')
    if (
        type(ind) is not int or not (0 <= ind <= 100)
        or type(gun) is not int or gun < 0
        or type(gd) is not bool
        or not isinstance(sur, str) or not sur.strip()
        or type(m_ind) is not int or not (0 <= m_ind <= 100)
        or type(m_gun) is not int or m_gun < 0
        or type(m_gd) is not bool
        or not isinstance(a_sur, str) or not a_sur.strip()
    ):
        raise ValueError('bozuk vaat veya politika semasi')
    ihlaller = []
    if sur != a_sur:
        ihlaller.append('eski-surum')
    if ind > m_ind:
        ihlaller.append('indirim-asimi')
    if gun > m_gun:
        ihlaller.append('sure-asimi')
    if (not m_gd) and gd:
        ihlaller.append('geriye-donuk-yasak')
    return {'onay': len(ihlaller) == 0, 'ihlaller': ihlaller}
```

```test
need('iade_vaadi_denetle')
_air_pol = {'maks_indirim_yuzdesi': 15, 'maks_basvuru_gun': 0, 'geriye_donuk_izin': False, 'aktif_surum': 'tarife-2026'}

eq(iade_vaadi_denetle({'indirim_yuzdesi': 15, 'basvuru_gun': 0, 'geriye_donuk': False, 'surum': 'tarife-2026'}, _air_pol), {
    'onay': True, 'ihlaller': [],
}, 'tam tavandaki (15%) ve geriye dönük olmayan teklif onaylanmalı')

eq(iade_vaadi_denetle({'indirim_yuzdesi': 20, 'basvuru_gun': 90, 'geriye_donuk': True, 'surum': 'tarife-2022'}, _air_pol), {
    'onay': False,
    'ihlaller': ['eski-surum', 'indirim-asimi', 'sure-asimi', 'geriye-donuk-yasak'],
}, 'dört ihlal tam belirtilen sırayla raporlanmalı')

_esnek_pol = {'maks_indirim_yuzdesi': 25, 'maks_basvuru_gun': 30, 'geriye_donuk_izin': True, 'aktif_surum': 'esnek-v1'}
eq(iade_vaadi_denetle({'indirim_yuzdesi': 10, 'basvuru_gun': 0, 'geriye_donuk': False, 'surum': 'esnek-v1'}, _esnek_pol), {
    'onay': True, 'ihlaller': [],
}, 'geriye dönük izinli politikada geriye_donuk=False demek hak aşımı değildir')

for _bozuk in (
    ({'indirim_yuzdesi': True, 'basvuru_gun': 0, 'geriye_donuk': False, 'surum': 'v1'}, _air_pol),
    ({'indirim_yuzdesi': 105, 'basvuru_gun': 0, 'geriye_donuk': False, 'surum': 'v1'}, _air_pol),
    ({'indirim_yuzdesi': 10, 'basvuru_gun': -1, 'geriye_donuk': False, 'surum': 'v1'}, _air_pol),
    (None, _air_pol),
):
    raises(ValueError, iade_vaadi_denetle, *_bozuk, msg='şema dışı girdi ValueError')

# Sınır değerleri: indirim 0 ve 100, politika tavanı 0 ve 100 geçerlidir; geriye dönük izinli politikada
# geriye dönük vaat ihlal değildir.
_vaat = {'indirim_yuzdesi': 10, 'basvuru_gun': 0, 'geriye_donuk': False, 'surum': 'esnek-v1'}
eq(iade_vaadi_denetle(dict(_vaat, indirim_yuzdesi=0), dict(_esnek_pol, maks_indirim_yuzdesi=0)), {'onay': True, 'ihlaller': []},
   'indirim 0 ve tavan 0 geçerli')
eq(iade_vaadi_denetle(dict(_vaat, indirim_yuzdesi=100), dict(_esnek_pol, maks_indirim_yuzdesi=100)), {'onay': True, 'ihlaller': []},
   'indirim 100 ve tavan 100 geçerli')
eq(iade_vaadi_denetle(dict(_vaat, geriye_donuk=True), _esnek_pol), {'onay': True, 'ihlaller': []},
   'geriye dönük izinli politikada geriye dönük vaat onaylanır')

# Her şema kuralı tek başına: vaat alanları, politika alanları ve politika türü.
raises(ValueError, iade_vaadi_denetle, _vaat, None, msg='sözlük olmayan politika ValueError')
for _alan, _deger in (('indirim_yuzdesi', -1), ('indirim_yuzdesi', 101), ('basvuru_gun', 1.0), ('geriye_donuk', 0), ('surum', 5), ('surum', '   ')):
    raises(ValueError, iade_vaadi_denetle, dict(_vaat, **{_alan: _deger}), _esnek_pol, msg=f'bozuk vaat alanı ValueError: {_alan}={_deger!r}')
for _alan, _deger in (('maks_indirim_yuzdesi', 15.0), ('maks_indirim_yuzdesi', 101), ('maks_indirim_yuzdesi', -1),
                      ('maks_basvuru_gun', 30.0), ('maks_basvuru_gun', -1), ('geriye_donuk_izin', 1),
                      ('aktif_surum', 5), ('aktif_surum', '   ')):
    raises(ValueError, iade_vaadi_denetle, _vaat, dict(_esnek_pol, **{_alan: _deger}), msg=f'bozuk politika alanı ValueError: {_alan}={_deger!r}')
```

```hint
Tavan kontrollerinde kesin büyüktür (`>`), geriye dönük yasakta ise `(not resmi_politika['geriye_donuk_izin']) and model_vaadi['geriye_donuk']` koşulunu kullan.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Olay ve kaynak sınırı (15 sn).** "*Moffatt v. Air Canada* (2024 BCCRT 149) özetinde mahkeme, sohbet botunun resmi tarifeye aykırı geriye dönük iade vaadini şirketin sorumluluk alanından ayrı saymadı; doğrulanmamış sosyal medya öykülerini ise kanıt dışına ayırdım."
2. **Mekanizma (30 sn).** "Olasılıksal dil modeli yetkili fiyat/tarife veritabanı değildir; yalnız fiyatı eşleyip para birimi ve sürümü unutmak yanlış sözleşme üretir."
3. **Sınır ve ölçüm (30 sn).** "`teklif_dogrula` ile pozitif `int` fiyat, para birimi ve sürüm üçlüsünü zorunlu kıldım; senaryo koşusunda yalnız fiyat bakan yamanın kaçırdığı `%75` sızıntıyı `0.0`'a indirdim."
4. **Politika kapısı (25 sn).** "`iade_vaadi_denetle` ile geriye dönük iade, indirim tavanı ve başvuru penceresi ihlallerini müşteriye gitmeden yakaladım."
5. **Kapanış (20 sn).** "Müşteriye dönük her bağlayıcı rakam ve kural LLM tarafından uydurulmaz; yetkili API'den okunup deterministik şemayla doğrulanır."
:::

::: anlat Sınır ve kaynak
Bu dersteki doğrulayıcılar yapılandırılmış teklif sözlüklerini denetler. Gerçek müşteri destek sistemlerinde model hem yapılandırılmış kart gösterip hem de yanındaki serbest metin paragrafında çelişkili bir cümle kurabilir; bu nedenle bağlayıcı teklifler serbest metin üretimi yerine doğrudan şablonlanmış UI bileşenleriyle (`server-rendered policy card`) sunulmalıdır (`ai-savunma-08`).

- Yayıncı özeti: [CanLII Blog — March 2024 (*Moffatt v. Air Canada*, 2024 BCCRT 149 özeti)](https://blog.canlii.org/2024/03/).
- Karar kaydı: [2024 BCCRT 149 (CanLII)](https://www.canlii.org/en/bc/bccrt/doc/2024/2024bccrt149/2024bccrt149.html) *(otomatik erişimde HTTP 403 döndürmüştür; Chevrolet 1 dolar iddiası için birincil kayıt doğrulanmamıştır)*. Doğrulama tarihi: 10 Kasım 2026.
:::

::: dusun
Bir müşteri destek botunun sayfasının en altına küçük harflerle "Sohbet botu hata yapabilir, resmi tarife geçerlidir" uyarısı koymak yerine mimari olarak fiyat ve iade hesaplamasını yalnız deterministik bir araçtan (`tool`) şablonlu kart olarak döndürmek neden hem teknik hem operasyonel olarak daha sağlamdır?
:::

::: ozet
- Üretken model çıktıları ticari fiyat, para birimi ve iade kuralları için tek başına kaynak olamaz.
- Teklif doğrulamasında `type(fiyat) is int and fiyat > 0`, `para_birimi` ve `surum` alanlarının tamamı birlikte eşleştirilir.
- Geriye dönük iade hakkı ve indirim tavanları müşteriye gösterilmeden önce deterministik politika motoruyla denetlenir.
:::
