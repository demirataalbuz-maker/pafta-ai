---
id: ai-olay-09
title: "Probllama ve OCI Digest · Yol Geçişi ve Değişmez İmaj Kilidi"
summary: CVE-2024-37032 (Probllama) bağlamında doğrulanmamış sha256 digest alanından kaynaklanan yol geçişini ve değişken etiket (:latest) riskini sıkı digest doğrulamasıyla kapat.
esleme: ai-savunma-20, ai-savunma-36, ai-savunma-21, ai-savunma-05
timeout: 30
---

::: anlat 1. Gerçek olay ve yerel kopya sınırı
Haziran 2024'te **Wiz Research** tarafından açıklanan **CVE-2024-37032 (*Probllama*)**, **Ollama** model sunucusunun özel bir kayıt defterinden (`registry`) model çekerken bildirim (`manifest`) içindeki `digest` alanını yeterli biçim doğrulaması yapmadan yerel dosya yolu üretiminde (`blobs/sha256-...`) kullanmasından kaynaklanan bir **yol geçişi (`path traversal`) ve uzaktan kod yürütme** zafiyetidir. Saldırgan `digest` alanına `../../...` bileşenleri yerleştirdiğinde sunucu model katmanı yerine dosya sistemindeki kritik yolları okuyup üzerine yazabiliyordu.

> [!NOTE]
> **Yerel kopya ayrımı:** Bu derste gerçek bir OCI kayıt defteri veya Ollama sunucusu çalıştırılmaz. Hem CVE-2024-37032'deki **kanonik `digest` -> yerel `blob` yolu** sınırı hem de konteyner/model dağıtımlarında değişken `:latest` etiketi yerine **değişmez (`immutable`) SHA-256 kilidi** kuralı çevrimdışı Python modeliyle incelenir.
:::

::: anlat 2. Mekanizma · kriptografik özet alanı neden dosya yolu olarak tehlikelidir?
Model ve kapsayıcı dağıtım sistemlerinde `sha256:<64-hex>` biçimindeki `digest` alanı aynı anda iki kritik işlev görür (`ai-savunma-20`, `ai-savunma-36`):

1. **Yerel depolama anahtarı (`Content-Addressable Storage`):** Sunucu indirilen katmanı `blobs/sha256-<HEX>` altında saklar. Eğer `digest` ayrıştırılırken `sha256:` sonrası için sıkı `^[0-9a-f]{64}$` doğrulaması yapılmazsa `sha256:../../../../etc/ld.so.preload` gibi bir değer dosya sistemi sınırını deler (`path traversal`). Üstelik böyle bozuk bir girdiyi `normpath` ile "temizlemeye" çalışmak da yanlıştır; bozuk `digest` derhal `ValueError` ile reddedilmelidir!
2. **Tedarik zinciri değişmezliği (`Immutability`):** `:latest` veya `:v1` gibi etiketler (`mutable tag`) kayıt defterinde her an farklı bir içeriğe yönlendirilebilir; yalnız 64 karakterlik küçük onaltılık SHA-256 özeti belirli tek bir bayt dizisini kilitler.

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| `'blobs/sha256-' + digest.split(':')[-1]` | `sha256:../../dosya` ile üst dizine yazar (CVE-2024-37032 mekanizması) | Tam `sha256:` öneki + tam 64 adet `[0-9a-f]` karakter doğrulaması |
| `s.isalnum() and s.islower()` ile hex kontrolü yapmak | `'g'..'z'` arasındaki onaltılık olmayan harfleri ve Unicode rakamları geçirir | Açık `'0123456789abcdef'` kümesi kontrolü |
| `re.match(r'^sha256:[0-9a-f]{64}$', digest)` kullanmak | Python'da `$` satır sonundaki `\n` karakterinden önce de eşleştiği için `'sha256:...64...\n'` girdisini kaçırır! | Uzunluk `== 71`, `startswith('sha256:')` ve karakter kümesi (veya `\Z`) |
:::

::: tahmin Python `re` modülünde `$` işareti sondaki `\n` karakterine ne yapar?
Güvenlik doğrulayıcılarında çok sık düşülen bir Python tuzağını tahmin et:

```python
import re

bozuk = 'sha256:' + ('a' * 64) + '\n'
dolar_eslesti = bool(re.match(r'^sha256:[0-9a-f]{64}$', bozuk))
kesin_son_eslesti = bool(re.match(r'^sha256:[0-9a-f]{64}\Z', bozuk))
print('uzunluk:', len(bozuk))
print('$ ile eşleşti mi:', dolar_eslesti)
print('\\Z ile eşleşti mi:', kesin_son_eslesti)
```

???

```cikti
uzunluk: 72
$ ile eşleşti mi: True
\Z ile eşleşti mi: False
```
Python düzenli ifadelerinde `$`, dizgenin en sonundaki tek bir `\n` karakterinden hemen önce de eşleşir! Bu yüzden dosya yolu üreten bir doğrulayıcıda `$` kullanılırsa sonuna satır sonu eklenmiş `'blobs/sha256-aaa...\n'` yolu kapıdan sızar. `\Z` veya açık `len(digest) == 71` kontrolü bu tuzağı tamamen kapatır.
:::

::: gorev 1 · Yol geçişini kapatan sıkı `digest_anahtari` sınırını kur
`digest_anahtari(digest)` işlevini yaz:

- Yalnız `str` türünde, tam `71` karakter uzunluğunda, `'sha256:'` ile başlayan ve devamındaki `64` karakterin tamamı küçük ASCII onaltılık (`'0123456789abcdef'`) olan girdileri kabul et; dönüş `'blobs/sha256-' + digest[7:]` olsun.
- Diğer tüm girdilerde (`'../../'`, `:latest`, büyük harf `A-F`, `63` veya `65` karakter, sondaki `\n`, `g-z` harfleri, `str` dışı türler) yol normalizasyonu ile düzeltmeye çalışmadan doğrudan `ValueError` fırlat.

KUSURLU başlangıç `:` sonrasını doğrulamadan birleştirdiği için `sha256:../../etc/passwd` yol geçişine izin veriyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[\n  "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"\n]', encoding='utf-8')
```

```starter
def digest_anahtari(digest):
    if not isinstance(digest, str) or ':' not in digest:
        raise ValueError('gecersiz digest')
    return 'blobs/sha256-' + digest.split(':', 1)[1]

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(digest_anahtari(*_args))
```

```solution
_HEX_KUME = frozenset('0123456789abcdef')

def digest_anahtari(digest):
    if not isinstance(digest, str) or len(digest) != 71 or not digest.startswith('sha256:'):
        raise ValueError('gecersiz sha256 digest bicimi')
    hex_kisim = digest[7:]
    if any(c not in _HEX_KUME for c in hex_kisim):
        raise ValueError('yalniz kucuk hexadecimal karakterler gecerlidir')
    return 'blobs/sha256-' + hex_kisim

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(digest_anahtari(*_args))
```

```test
need('digest_anahtari')
_gecerli = '0123456789abcdef' * 4
eq(digest_anahtari('sha256:' + _gecerli), 'blobs/sha256-' + _gecerli, '64 küçük hex karakterli sha256 kabul edilmeli')

_bozuklar = [
    'sha256:../../etc/passwd',
    'sha256:' + ('a' * 63),
    'sha256:' + ('a' * 65),
    'sha256:' + ('A' * 64),
    'sha256:' + ('g' * 64),
    'sha256:' + ('a' * 64) + '\n',
    ' sha256:' + ('a' * 64),
    'sha512:' + ('a' * 64),
    'latest',
    'ollama/llama3:latest',
    '',
    None,
    123,
]
for _d in _bozuklar:
    raises(ValueError, digest_anahtari, _d, msg=f'bozuk digest ValueError fırlatmalı: {_d!r}')
```

```hint
`len(digest) == 71`, `digest.startswith('sha256:')` ve `all(c in '0123456789abcdef' for c in digest[7:])` kontrolü hem `re` satır sonu tuzağından hem Unicode rakam/harf sürprizlerinden muaftır.
```
:::

::: gorev 2 · Açık ve yamalı digest kapısını senaryo vakalarında ölç
`digest_senaryo_olc(vakalar, acik_fn, yamali_fn)` işlevini yaz:

- Her vaka `{'saldiri': bool, 'girdi': (digest,), ...}` sözlüğüdür. Şema veya çağrılabilirlik bozuksa `ValueError` fırlat.
- Bu sınırda ret mekanizması `ValueError` fırlatmaktır! Sınır işlevi `ValueError` fırlatmadan bir `str` döndürürse girdiyi **kabul etmiş** sayılır; `ValueError` fırlatırsa **reddetmiş** sayılır.
- Saldırı vakalarında kabul **yol geçişi / etiket sızıntısı (`sizma`)**, meşru vakalarda kabul **meşru kabul** demektir.
- Dönüş: `{'saldiri_n': int, 'mesru_n': int, 'once_sizma': float|None, 'sonra_sizma': float|None, 'mesru_kabul': float|None, 'regresyon_n': int}`.

KUSURLU başlangıç `yamali_fn` fırlattığı `ValueError` istisnasını yakalamadığı için ilk saldırı vakasında çöküyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def digest_senaryo_olc(vakalar, acik_fn, yamali_fn):
    s = [v for v in vakalar if v['saldiri']]
    m = [v for v in vakalar if not v['saldiri']]
    return {
        'saldiri_n': len(s), 'mesru_n': len(m),
        'once_sizma': round(sum(1 for v in s if acik_fn(*v['girdi'])) / len(s), 4),
        'sonra_sizma': round(sum(1 for v in s if yamali_fn(*v['girdi'])) / len(s), 4),
        'mesru_kabul': round(sum(1 for v in m if yamali_fn(*v['girdi'])) / len(m), 4),
        'regresyon_n': 0,
    }
```

```solution
import copy

def _kabul_edildi(fn, girdi):
    try:
        sonuc = fn(*copy.deepcopy(girdi))
        return isinstance(sonuc, str) and bool(sonuc)
    except ValueError:
        return False

def digest_senaryo_olc(vakalar, acik_fn, yamali_fn):
    if not isinstance(vakalar, list) or not vakalar or not callable(acik_fn) or not callable(yamali_fn):
        raise ValueError('gecerli vakalar ve cagrilaiblir sinirlar gerekli')
    s_n = m_n = s_once = s_sonra = m_sonra = reg = 0
    for v in vakalar:
        if not isinstance(v, dict) or type(v.get('saldiri')) is not bool or not isinstance(v.get('girdi'), (tuple, list)):
            raise ValueError('bozuk vaka semasi')
        once_ok = _kabul_edildi(acik_fn, v['girdi'])
        sonra_ok = _kabul_edildi(yamali_fn, v['girdi'])
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
need('digest_senaryo_olc')
from sandbox.ai_olay_senaryo import acik_sinir, senaryo_vakalari

def _yama(d):
    if not isinstance(d, str) or len(d) != 71 or not d.startswith('sha256:') or any(c not in '0123456789abcdef' for c in d[7:]):
        raise ValueError('gecersiz')
    return 'blobs/sha256-' + d[7:]

_vakalar = senaryo_vakalari(9, tohum=1)
eq(digest_senaryo_olc(_vakalar, acik_sinir(9), _yama), {
    'saldiri_n': 5,
    'mesru_n': 2,
    'once_sizma': 1.0,
    'sonra_sizma': 0.0,
    'mesru_kabul': 1.0,
    'regresyon_n': 0,
}, 'açık sınır 5/5 saldırıyı geçirir, ValueError tabanlı yama 0.0 sızıntı sağlar')

def _hep_hata(_d):
    raise ValueError('kapali')

eq(digest_senaryo_olc(_vakalar, acik_sinir(9), _hep_hata)['regresyon_n'], 2, 'her şeye ValueError fırlatan sınır 2 regresyon üretir')
raises(ValueError, digest_senaryo_olc, [], acik_sinir(9), _yama, msg='boş liste ValueError')

# Ölçüm mantığı alandan bağımsızdır: sınır boş olmayan str döndürürse kabul, ValueError fırlatırsa red.
_el = [
    {'saldiri': True, 'girdi': ('s-ikisi-gecer',)},
    {'saldiri': True, 'girdi': ('s-acik-de-durdurur',)},
    {'saldiri': True, 'girdi': ('s-yalniz-acik-gecer',)},
    {'saldiri': False, 'girdi': ('m-ikisi-gecer',)},
    {'saldiri': False, 'girdi': ('m-ikisi-durdurur',)},
    {'saldiri': False, 'girdi': ('m-regresyon',)},
]
def _sinir(gecenler):
    def _f(d):
        if d not in gecenler:
            raise ValueError('reddedildi')
        return 'blobs/' + d
    return _f
_acik_el = _sinir(('s-ikisi-gecer', 's-yalniz-acik-gecer', 'm-ikisi-gecer', 'm-regresyon'))
_yama_el = _sinir(('s-ikisi-gecer', 'm-ikisi-gecer'))
eq(digest_senaryo_olc(_el, _acik_el, _yama_el), {
    'saldiri_n': 3,
    'mesru_n': 3,
    'once_sizma': 0.6667,
    'sonra_sizma': 0.3333,
    'mesru_kabul': 0.3333,
    'regresyon_n': 1,
}, 'oranlar grup paydasıyla ve 4 basamakla; sıfırdan farklı sonra_sizma ve regresyon doğru sayılmalı')
eq(digest_senaryo_olc(_el, _acik_el, _acik_el)['sonra_sizma'], 0.6667, 'yama açık sınırla aynıysa sonra_sizma = once_sizma')
eq(digest_senaryo_olc(_el, _sinir(()), _sinir(()))['regresyon_n'], 0, 'açık sınırın da reddettiği meşru vaka regresyon sayılmaz')
eq(digest_senaryo_olc([v for v in _el if v['saldiri']], _acik_el, _yama_el)['mesru_kabul'], None, 'meşru vaka yoksa mesru_kabul None')
eq(digest_senaryo_olc([v for v in _el if not v['saldiri']], _acik_el, _yama_el),
   {'saldiri_n': 0, 'mesru_n': 3, 'once_sizma': None, 'sonra_sizma': None, 'mesru_kabul': 0.3333, 'regresyon_n': 1},
   'saldırı vakası yoksa once_sizma ve sonra_sizma None')
# Kabul yalnız boş olmayan str'dir: boş dizge, bytes, None ve sayı kabul sayılmaz.
for _tuhaf in (lambda _d: '', lambda _d: b'blobs/x', lambda _d: None, lambda _d: 1):
    eq(digest_senaryo_olc(_el, _tuhaf, _tuhaf)['once_sizma'], 0.0, 'boş olmayan str dışındaki dönüş kabul sayılmamalı')
raises(ValueError, digest_senaryo_olc, tuple(_el), _acik_el, _yama_el, msg='liste olmayan vakalar ValueError')
raises(ValueError, digest_senaryo_olc, _el, None, _yama_el, msg='çağrılamaz açık sınır ValueError')
raises(ValueError, digest_senaryo_olc, _el, _acik_el, 'yama', msg='çağrılamaz yamalı sınır ValueError')
for _bozuk in (
    _el + [('s-ikisi-gecer',)],
    _el + [{'saldiri': 1, 'girdi': ('s-ikisi-gecer',)}],
    _el + [{'saldiri': True, 'girdi': None}],
):
    raises(ValueError, digest_senaryo_olc, _bozuk, _acik_el, _yama_el, msg=f'bozuk vaka şeması ValueError: {_bozuk[-1]!r}')
```

```hint
Yardımcı `_kabul_edildi(fn, girdi)` içinde `try: ... except ValueError: return False` kullanarak fırlatılan `ValueError` istisnasını güvenli ret kararına çevir.
```
:::

::: gorev 3 · Dağıtım kilit dosyasına (`lockfile`) karşı imaj referansını doğrula
Üretim ortamında `ai-runner` ve model kapsayıcılarının yalnız kilit dosyasındaki değişmez özetle çalışmasını sağlayan `manifest_kilit_dogrula(kilit_tablosu, servis, istek_ref)` işlevini yaz:

- `kilit_tablosu` `{servis_adi: 'depo/ad@sha256:<64-kucuk-hex>'}` biçiminde `dict`, `servis` ve `istek_ref` `str` olmalı; değilse `ValueError` fırlat.
- Kilit tablosunda `servis` yoksa `{'izin': False, 'neden': 'tanimsiz-servis'}` döndür.
- `istek_ref` içinde `'@'` yoksa (örneğin `'ollama/ollama:latest'` gibi değişken etiket) `{'izin': False, 'neden': 'digest-eksik'}` döndür.
- `istek_ref` `'@'` ile ikiye ayrıldığında (`isim_ve_etiket, digest = istek_ref.rsplit('@', 1)`):
  - `digest` Görev 1'deki geçerli `sha256:<64-kucuk-hex>` kuralına uymuyorsa `{'izin': False, 'neden': 'gecersiz-digest'}` döndür;
  - `isim_ve_etiket` içinde isteğe bağlı `:etiket` varsa etiket kısmını at (`depo = isim_ve_etiket.split(':', 1)[0]`); kilit tablosundaki kayıtla hem `depo` adı hem `digest` birebir eşleşmiyorsa `{'izin': False, 'neden': 'kilit-uyumsuz'}`, eşleşiyorsa `{'izin': True, 'neden': 'onaylandi'}` döndür.

KUSURLU başlangıç yalnız depo adına bakıp `@sha256:...` özetinin kilit tablosundaki özetle uyuşup uyuşmadığını kontrol etmiyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def manifest_kilit_dogrula(kilit_tablosu, servis, istek_ref):
    if servis not in kilit_tablosu:
        return {'izin': False, 'neden': 'tanimsiz-servis'}
    if '@' not in istek_ref:
        return {'izin': False, 'neden': 'digest-eksik'}
    return {'izin': True, 'neden': 'onaylandi'}
```

```solution
_HEX = frozenset('0123456789abcdef')

def _gecerli_sha(d):
    return isinstance(d, str) and len(d) == 71 and d.startswith('sha256:') and all(c in _HEX for c in d[7:])

def manifest_kilit_dogrula(kilit_tablosu, servis, istek_ref):
    if not isinstance(kilit_tablosu, dict) or not isinstance(servis, str) or not isinstance(istek_ref, str):
        raise ValueError('kilit_tablosu dict, servis ve istek_ref str olmali')
    if servis not in kilit_tablosu:
        return {'izin': False, 'neden': 'tanimsiz-servis'}
    kilit_ref = kilit_tablosu[servis]
    if not isinstance(kilit_ref, str) or '@' not in kilit_ref:
        raise ValueError('bozuk kilit kaydi')
    kilit_depo, kilit_digest = kilit_ref.rsplit('@', 1)
    if not kilit_depo or not _gecerli_sha(kilit_digest):
        raise ValueError('bozuk kilit kaydi')
    if '@' not in istek_ref:
        return {'izin': False, 'neden': 'digest-eksik'}
    sol, istek_digest = istek_ref.rsplit('@', 1)
    if not _gecerli_sha(istek_digest):
        return {'izin': False, 'neden': 'gecersiz-digest'}
    istek_depo = sol.split(':', 1)[0]
    if istek_depo != kilit_depo or istek_digest != kilit_digest:
        return {'izin': False, 'neden': 'kilit-uyumsuz'}
    return {'izin': True, 'neden': 'onaylandi'}
```

```test
need('manifest_kilit_dogrula')
_d1 = 'a' * 64
_d2 = 'b' * 64
_kilit = {'runner': f'ic-depo/ai-runner@sha256:{_d1}'}

eq(manifest_kilit_dogrula(_kilit, 'runner', f'ic-depo/ai-runner@sha256:{_d1}'), {'izin': True, 'neden': 'onaylandi'}, 'tam eşleşen digest geçmeli')
eq(manifest_kilit_dogrula(_kilit, 'runner', f'ic-depo/ai-runner:0.4@sha256:{_d1}'), {'izin': True, 'neden': 'onaylandi'}, 'etiket + doğru digest geçmeli')
eq(manifest_kilit_dogrula(_kilit, 'bilinmeyen', f'ic-depo/ai-runner@sha256:{_d1}'), {'izin': False, 'neden': 'tanimsiz-servis'}, 'tanımsız servis reddedilmeli')
eq(manifest_kilit_dogrula(_kilit, 'runner', 'ic-depo/ai-runner:latest'), {'izin': False, 'neden': 'digest-eksik'}, 'yalnız :latest etiketi reddedilmeli')
eq(manifest_kilit_dogrula(_kilit, 'runner', 'ic-depo/ai-runner@sha256:../../etc'), {'izin': False, 'neden': 'gecersiz-digest'}, 'bozuk digest reddedilmeli')
eq(manifest_kilit_dogrula(_kilit, 'runner', f'ic-depo/ai-runner@sha256:{_d2}'), {'izin': False, 'neden': 'kilit-uyumsuz'}, 'farklı digest reddedilmeli')
eq(manifest_kilit_dogrula(_kilit, 'runner', f'baska/ai-runner@sha256:{_d1}'), {'izin': False, 'neden': 'kilit-uyumsuz'}, 'farklı depo adı reddedilmeli')
raises(ValueError, manifest_kilit_dogrula, None, 'runner', 'x', msg='bozuk tablo ValueError')

# İstek digest'inin her biçim kuralı ayrı: 65 hex, yanlış algoritma öneki, hex dışı karakter,
# büyük harf, yalnız ilk karakteri bozuk. Hepsi "gecersiz-digest" olmalı, "kilit-uyumsuz" değil.
for _dig in ('sha256:' + 'a' * 65, 'sha512:' + 'a' * 64, 'sha256:' + 'g' * 64, 'sha256:' + 'A' * 64, 'sha256:g' + 'a' * 63):
    eq(manifest_kilit_dogrula(_kilit, 'runner', f'ic-depo/ai-runner@{_dig}'), {'izin': False, 'neden': 'gecersiz-digest'},
       f'biçimi bozuk digest gecersiz-digest dönmeli: {_dig[:12]}...')
# Son '@' ayırıcıdır: araya sokulmuş ikinci '@' depo adına kalır ve kilitle eşleşmez.
eq(manifest_kilit_dogrula(_kilit, 'runner', f'ic-depo/ai-runner@sha256:{_d2}@sha256:{_d1}'), {'izin': False, 'neden': 'kilit-uyumsuz'},
   'iki @ içeren istekte son digest alınır, depo adı uyuşmaz')
eq(manifest_kilit_dogrula({'x': f'kayit@ic/runner@sha256:{_d1}'}, 'x', f'kayit@ic/runner@sha256:{_d1}'), {'izin': True, 'neden': 'onaylandi'},
   'kilit kaydında da son @ ayırıcıdır')
# Üst argüman türleri ve bozuk kilit kayıtları.
for _arg in ((_kilit, 5, f'ic-depo/ai-runner@sha256:{_d1}'), (_kilit, 'runner', None)):
    raises(ValueError, manifest_kilit_dogrula, *_arg, msg=f'str olmayan servis veya istek ValueError: {_arg[1:]!r}')
for _kayit in (None, 'ic-depo/ai-runner', f'@sha256:{_d1}', 'ic-depo/ai-runner@sha256:kisa', f'ic-depo/ai-runner@md5:{_d1}'):
    raises(ValueError, manifest_kilit_dogrula, {'runner': _kayit}, 'runner', f'ic-depo/ai-runner@sha256:{_d1}',
           msg=f'bozuk kilit kaydı ValueError: {_kayit!r}')
```

```hint
`rsplit('@', 1)` ile digest kısmını ayırdıktan sonra önce `_gecerli_sha` kontrolünü yap, ardından `sol.split(':', 1)[0]` ile depo adını ve `digest` değerini kilit kaydıyla karşılaştır.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Olay bağlamı (15 sn).** "Wiz Research'ün bildirdiği CVE-2024-37032 (*Probllama*), dış kayıt defterinden gelen `digest` dizgesinin doğrulanmadan yerel `blob` yoluna eklenmesiyle yol geçişine ve RCE'ye yol açtı."
2. **Çift ders (30 sn).** "`digest` hem dosya sistemi sınırında güvenilmeyen bir girdidir hem de tedarik zincirinde değişken `:latest` etiketinin yerini alan kriptografik kilittir."
3. **Python tuzağı ve yama (30 sn).** "Regex `$` satır sonundaki `\n` karakterini kaçırabildiği için `digest_anahtari` içinde 71 karakterlik kesin `sha256:` + `[0-9a-f]{64}` kontrolü kurdum ve senaryo koşusunda doğruladım."
4. **Kilit dosyası (25 sn).** "`manifest_kilit_dogrula` ile üretim dağıtımlarında digest içermeyen veya kilit özetiyle uyuşmayan imajları kapıda durdurdum."
5. **Kapanış (20 sn).** "Dış manifestten gelen hiçbir alan, sıkı karakter kümesi doğrulamasından geçmeden yerel dosya yoluna dönüştürülemez."
:::

::: anlat Sınır ve kaynak
Bu derste `digest` biçimi ve kilit tablosu eşleşmesi doğrulanır; gerçek bir OCI/model istemcisinde indirilen katman baytlarının gerçek SHA-256 özeti de diske nihai olarak taşınmadan önce hesaplanıp manifestteki `digest` ile karşılaştırılmalıdır (`content verification` — bkz. `ai-savunma-36`).

- Birincil kaynak: [Wiz Research — Probllama: Ollama Vulnerability CVE-2024-37032 (Haziran 2024)](https://www.wiz.io/blog/probllama-ollama-vulnerability-cve-2024-37032). Doğrulama tarihi: 10 Kasım 2026.
:::

::: dusun
İmaj manifestindeki `digest` biçimini doğrulayıp katmanı indirdikten sonra indirilen baytların SHA-256 özetini yeniden hesaplamayan bir istemci, kötücül bir kayıt defteri (`rogue registry`) karşısında hangi saldırıya açık kalır?
:::

::: ozet
- Kayıt defterinden gelen `digest` alanı güvenilmeyen girdidir; `../../` yol geçişine karşı tam `sha256:[0-9a-f]{64}` biçimiyle doğrulanır.
- Python'da `re` modülündeki `$` sondaki `\n` karakterine izin verdiği için kesin uzunluk veya `\Z` kullanılır.
- Üretim dağıtımlarında `:latest` gibi değişken etiketler yerine kilitlenmiş `@sha256:...` özetleri zorunlu tutulur.
:::
