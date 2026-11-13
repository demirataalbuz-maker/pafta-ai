---
id: ai-olay-08
title: "Kötücül Model Yükleme · Pickle Riski ve Safetensors Kapısı"
summary: Model depolarındaki serileştirme arka kapılarına karşı safetensors biçim şartını, hata-kapalı (fail-closed) tarama kapısını, senaryo ölçümünü ve başlık ofset doğrulamasını kur.
esleme: ai-savunma-20, ai-savunma-36, ai-savunma-13, ai-guvence-11
timeout: 30
---

::: anlat 1. Gerçek olay ve yerel kopya sınırı
Şubat 2024'te **JFrog Security Research**, açık model paylaşım platformlarında veri bilimcileri hedef alan ve `pickle` tabanlı ağırlık dosyalarının (`pytorch_model.bin` / `.pkl`) yüklenme anında (`torch.load` deserialization) sessiz ters kabuk (`reverse shell`) çalıştırdığı gerçek kötücül modelleri belgeledi. Üstelik bazı yükler statik `pickle` opkod tarayıcılarını atlatacak biçimde kurgulanmıştı.

> [!NOTE]
> **Yerel kopya ayrımı:** Bu derste hiçbir gerçek model ağırlığı indirilmez ve hiçbir `pickle` baytı çözülmez (`pickle.loads` çağrılmaz). Otomatik model yükleme kapısının neden **veri-sadece (`safetensors`)** biçime kilitlenmesi ve tarayıcı belirsizliklerinde **hata-kapalı (`fail-closed`)** davranması gerektiği yerel Python modeliyle incelenir.
:::

::: anlat 2. Mekanizma · `pickle` sanal makinesi ile `safetensors` veri başlığı arasındaki fark
Python `pickle` bir veri biçimi değil, yığın tabanlı mini bir **sanal makinedir**: `REDUCE` opkodu herhangi bir Python çağrılabilirini keyfi argümanlarla çalıştırabilir. Bu yüzden "önce `pickle` tarayıcısından geçirelim, temiz derse otomatik yükleyelim" yaklaşımı yapısal olarak kırılgandır (`ai-savunma-20`, `ai-savunma-36`):

1. Tarayıcı `'unknown'` veya `'error'` döndürdüğünde "kötücül kanıt bulunamadı" diyerek yüklemeye devam etmek (`fail-open`) doğrudan kod yürütmeye kapı açar.
2. `safetensors` biçimi ise yürütülebilir opkod içermez: dosyanın başında sabit boyutlu bir JSON başlığı (tensör adları, `dtype`, `shape`, `[başlangıç, bitiş]` bayt ofsetleri) ve hemen arkasında ham tensör baytları yer alır. Yine de bozuk/taşan ofsetlerle bellek hatası oluşmaması için başlık ofsetleri yüklemeden önce doğrulanır!

**Yaygın yanlışlar**

| Yanlış yaklaşım | Neden kırılır? | Doğru sınır |
|---|---|---|
| `scan != 'infected'` ise `pickle` yüklemek | `'unknown'`/`'error'` durumlarında ve yeni `pickle` atlatmalarında kod çalışır | Otomatik kapıda yalnız `format == 'safetensors'` ve `scan == 'clean'` |
| `bool(hash_uyuyor)` ile doğruluk kontrolü | `hash_uyuyor = 1` veya `'evet'` gibi bozuk tipleri geçirir | `hash_uyuyor is True and inceleme is True` |
| `safetensors` başlığındaki `data_offsets` aralığını kontrol etmemek | Negatif, taşan veya örtüşen ofsetler bellek/dilimleme hatası üretir | `[bas, bit]` aralıklarının ardışık, taşmasız ve `shape * dtype` ile uyumlu olduğunu doğrulamak |
:::

::: tahmin Hata-açık (`fail-open`) tarayıcı kapısı belirsiz sonuca ne yapar?
Tarayıcı yeni bir sıkıştırma katmanı yüzünden `'unknown'` döndürdüğünde `scan != 'malicious'` ile `scan == 'clean'` arasındaki fark nedir?

```python
for durum in ('clean', 'unknown', 'error', 'malicious'):
    fail_open = (durum != 'malicious')
    fail_closed = (durum == 'clean')
    print(f'{durum:9s} -> fail_open: {fail_open!s:5s} | fail_closed: {fail_closed}')
```

???

```cikti
clean     -> fail_open: True  | fail_closed: True
unknown   -> fail_open: True  | fail_closed: False
error     -> fail_open: True  | fail_closed: False
malicious -> fail_open: False | fail_closed: False
```
Saldırgan tarayıcıda ayrıştırma hatası (`'error'` / `'unknown'`) tetikleyecek bozuk bir üst bilgi eklediğinde `fail-open` kapı modeli otomatik yükler; `fail-closed` kapı ise yalnız açıkça `'clean'` doğrulanmış artefaktı geçirir.
:::

::: gorev 1 · Hata-kapalı otomatik model yükleme kapısını (`model_kapisi`) kur
`model_kapisi(format, scan, hash_uyuyor, inceleme)` işlevini yaz:

- Yalnız aşağıdaki dört koşulun **tamamı** sağlandığında otomatik yükleme için `True`, diğer her kombinasyon ve bozuk tür için `False` döndür:
  1. `format == 'safetensors'` (`'pickle'`, `'pt'`, `'bin'`, `'onnx'` vb. otomatik yüklenmez);
  2. `scan == 'clean'` (`'unknown'`, `'error'`, `'infected'` vb. reddedilir);
  3. `hash_uyuyor is True`;
  4. `inceleme is True`.

KUSURLU başlangıç `scan != 'infected'` kullandığı ve `pickle` biçimini engellemediği için hem `pickle` dosyalarını hem tarayıcı hatalarını geçiriyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
Path('ornek.json').write_text('[\n  "safetensors",\n  "clean",\n  true,\n  true\n]', encoding='utf-8')
```

```starter
def model_kapisi(format, scan, hash_uyuyor, inceleme):
    return scan != 'infected' and bool(hash_uyuyor) and bool(inceleme)

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(model_kapisi(*_args))
```

```solution
def model_kapisi(format, scan, hash_uyuyor, inceleme):
    return (
        format == 'safetensors'
        and scan == 'clean'
        and hash_uyuyor is True
        and inceleme is True
    )

if __name__ == '__main__':
    import json
    from pathlib import Path
    _args = json.loads(Path('ornek.json').read_text(encoding='utf-8'))
    print(model_kapisi(*_args))
```

```test
need('model_kapisi')
eq(model_kapisi('safetensors', 'clean', True, True), True, 'dört koşulu sağlayan safetensors modeli geçmeli')

_red = [
    ('pickle', 'clean', True, True),
    ('pt', 'clean', True, True),
    ('SAFETENSORS', 'clean', True, True),
    ('safetensors', 'unknown', True, True),
    ('safetensors', 'error', True, True),
    ('safetensors', 'infected', True, True),
    ('safetensors', 'clean', False, True),
    ('safetensors', 'clean', 1, True),
    ('safetensors', 'clean', 'true', True),
    ('safetensors', 'clean', True, False),
    ('safetensors', 'clean', True, 1),
    (None, 'clean', True, True),
]
for _args in _red:
    eq(model_kapisi(*_args), False, f'eksik/güvensiz model kapıdan geçmemeli: {_args!r}')
```

```hint
Dört koşulu da tam eşitlik ve kimlik (`is True`) ile bağla: `format == 'safetensors' and scan == 'clean' and hash_uyuyor is True and inceleme is True`.
```
:::

::: gorev 2 · Açık ve yamalı model kapısını senaryo vakalarında ölç
`model_senaryo_olc(vakalar, acik_fn, yamali_fn)` işlevini yaz:

- Her vaka `{'saldiri': bool, 'girdi': (format, scan, hash_uyuyor, inceleme), ...}` sözlüğüdür. Şema veya çağrılabilirlik bozuksa `ValueError` fırlat.
- Sınır işlevi `True` döndürdüğünde model **otomatik yüklendi** sayılır.
- Saldırı vakalarında yükleme **tedarik zinciri sızıntısı (`sizma`)**, meşru vakalarda yükleme **meşru kabul** demektir.
- Dönüş: `{'saldiri_n': int, 'mesru_n': int, 'once_sizma': float|None, 'sonra_sizma': float|None, 'mesru_kabul': float|None, 'regresyon_n': int}`.

KUSURLU başlangıç `saldiri_n` yerine tüm vakaların sayısına bölerek risk oranını yapay biçimde düşürüyor.

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def model_senaryo_olc(vakalar, acik_fn, yamali_fn):
    n = len(vakalar)
    s_once = sum(1 for v in vakalar if v['saldiri'] and acik_fn(*v['girdi']))
    s_sonra = sum(1 for v in vakalar if v['saldiri'] and yamali_fn(*v['girdi']))
    m_sonra = sum(1 for v in vakalar if not v['saldiri'] and yamali_fn(*v['girdi']))
    return {
        'saldiri_n': sum(1 for v in vakalar if v['saldiri']),
        'mesru_n': sum(1 for v in vakalar if not v['saldiri']),
        'once_sizma': round(s_once / n, 4),
        'sonra_sizma': round(s_sonra / n, 4),
        'mesru_kabul': round(m_sonra / n, 4),
        'regresyon_n': 0,
    }
```

```solution
import copy

def model_senaryo_olc(vakalar, acik_fn, yamali_fn):
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
need('model_senaryo_olc')
from sandbox.ai_olay_senaryo import acik_sinir, senaryo_vakalari

def _yama(fmt, scan, h, inc):
    return fmt == 'safetensors' and scan == 'clean' and h is True and inc is True

_vakalar = senaryo_vakalari(8, tohum=6)
eq(model_senaryo_olc(_vakalar, acik_sinir(8), _yama), {
    'saldiri_n': 5,
    'mesru_n': 2,
    'once_sizma': 1.0,
    'sonra_sizma': 0.0,
    'mesru_kabul': 1.0,
    'regresyon_n': 0,
}, 'açık sınır 5/5 saldırıyı geçirir, hata-kapalı yama 0.0 yapar')
eq(model_senaryo_olc(_vakalar, acik_sinir(8), lambda *_a: False)['regresyon_n'], 2, 'tüm yüklemeleri reddeden kapı 2 regresyon üretir')
eq(model_senaryo_olc([v for v in _vakalar if v['saldiri']], acik_sinir(8), _yama)['mesru_kabul'], None, 'meşru vaka yoksa None')
raises(ValueError, model_senaryo_olc, [], acik_sinir(8), _yama, msg='boş liste ValueError')

# Elle kurulmuş vakalar: oranlar kesirli çıkar (2/3, 1/3), yama bir saldırıyı hâlâ geçirir
# ve açık kapının kabul ettiği bir meşru modeli reddeder (regresyon).
_el = [
    {'saldiri': True, 'girdi': ('safetensors', 'clean', True, True)},
    {'saldiri': True, 'girdi': ('pickle', 'clean', True, True)},
    {'saldiri': True, 'girdi': ('safetensors', 'unknown', True, True)},
    {'saldiri': False, 'girdi': ('safetensors', 'clean', True, True)},
    {'saldiri': False, 'girdi': ('safetensors', 'clean', True, False)},
    {'saldiri': False, 'girdi': ('safetensors', 'clean', False, True)},
]
_acik_el = lambda f, s, h, i: f != 'pickle' and i is True
eq(model_senaryo_olc(_el, _acik_el, _yama), {
    'saldiri_n': 3,
    'mesru_n': 3,
    'once_sizma': 0.6667,
    'sonra_sizma': 0.3333,
    'mesru_kabul': 0.3333,
    'regresyon_n': 1,
}, 'oranlar grup paydasıyla, 4 basamakla; sıfırdan farklı sonra_sizma ve regresyon doğru sayılmalı')
eq(model_senaryo_olc(_el, _acik_el, _acik_el)['sonra_sizma'], 0.6667, 'yama açık kapıyla aynıysa sonra_sizma = once_sizma')
eq(model_senaryo_olc(_el, lambda *_a: False, lambda *_a: False)['regresyon_n'], 0,
   'önce de reddedilen meşru vaka regresyon sayılmaz')
eq(model_senaryo_olc([v for v in _el if not v['saldiri']], _acik_el, _yama),
   {'saldiri_n': 0, 'mesru_n': 3, 'once_sizma': None, 'sonra_sizma': None, 'mesru_kabul': 0.3333, 'regresyon_n': 1},
   'saldırı vakası yoksa once_sizma ve sonra_sizma None')

raises(ValueError, model_senaryo_olc, tuple(_el), _acik_el, _yama, msg='liste olmayan vakalar ValueError')
raises(ValueError, model_senaryo_olc, _el, None, _yama, msg='çağrılamaz açık sınır ValueError')
raises(ValueError, model_senaryo_olc, _el, _acik_el, 'yama', msg='çağrılamaz yamalı sınır ValueError')
for _bozuk in (
    _el + [('safetensors', 'clean', True, True)],
    _el + [{'saldiri': 1, 'girdi': ('pickle', 'clean', True, True)}],
    _el + [{'saldiri': True, 'girdi': None}],
):
    raises(ValueError, model_senaryo_olc, _bozuk, _acik_el, _yama, msg=f'bozuk vaka şeması ValueError: {_bozuk[-1]!r}')
```

```hint
Oranları toplam `len(vakalar)` ile değil, `s_n` ve `m_n` grup paydalarıyla hesapla; payda sıfırsa `None` döndür.
```
:::

::: gorev 3 · `safetensors` tensör başlığı ve bayt ofset bütünlüğünü doğrula
`safetensors` kod çalıştırmaz ama bozuk başlıklarla bellek taşması veya yanlış dilimleme olmaması için yükleyici önce JSON başlığını doğrular. `safetensors_baslik_dogrula(baslik, veri_boyutu)` işlevini yaz:

- `baslik` bir `dict`, `veri_boyutu` ise `bool` olmayan negatif olmayan `int` (`>= 0`) olmalı; değilse `ValueError` fırlat.
- İzinli veri tipleri ve eleman başına bayt boyutları: `{'F32': 4, 'F16': 2, 'BF16': 2, 'I32': 4, 'I8': 1}`.
- `'__metadata__'` anahtarı isteğe bağlıdır; varsa değeri tüm anahtar ve değerleri `str` olan bir `dict` olmalıdır (değilse `False` döndür).
- Kalan her tensör kaydı için (`en az 1` tensör bulunmalı; hiç tensör yoksa `False`):
  - Anahtar boş olmayan `str`, değer `dict` olmalı;
  - `'dtype'` izinli tiplerden biri olmalı;
  - `'shape'` tüm öğeleri `bool` olmayan `int >= 0` olan bir `list` olmalı (eleman sayısı = boyutların çarpımı; boş `[]` skaler için çarpım `1`);
  - `'data_offsets'` iki elemanlı `[bas, bit]` `list` (`bool` olmayan `int`, `0 <= bas <= bit <= veri_boyutu`) olmalı ve `bit - bas == eleman_sayisi * bayt_boyutu` eşitliğini sağlamalı.
- Ayrıca tüm tensörlerin `[bas, bit]` aralıkları başlangıca göre sıralandığında `0` noktasından başlayıp boşluksuz ve örtüşmesiz biçimde tam `veri_boyutu` noktasında bitmelidir! Koşulların tümü sağlanırsa `True`, aksi halde `False` döndür.

KUSURLU başlangıç yalnız `dtype` kontrolü yapıyor; örtüşen veya `veri_boyutu` dışına taşan ofsetleri kabul ediyor!

```setup
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.modules['__main__'].__file__).resolve().parents[1]))
```

```starter
def safetensors_baslik_dogrula(baslik, veri_boyutu):
    tipler = {'F32': 4, 'F16': 2, 'BF16': 2, 'I32': 4, 'I8': 1}
    for ad, bilgi in baslik.items():
        if ad == '__metadata__':
            continue
        if bilgi.get('dtype') not in tipler:
            return False
    return True
```

```solution
import math

_DTYPE_BAYT = {'F32': 4, 'F16': 2, 'BF16': 2, 'I32': 4, 'I8': 1}

def safetensors_baslik_dogrula(baslik, veri_boyutu):
    if not isinstance(baslik, dict) or type(veri_boyutu) is not int or veri_boyutu < 0:
        raise ValueError('baslik dict ve veri_boyutu >=0 int olmali')
    if '__metadata__' in baslik:
        meta = baslik['__metadata__']
        if not isinstance(meta, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in meta.items()):
            return False
    araliklar = []
    for ad, bilgi in baslik.items():
        if ad == '__metadata__':
            continue
        if not isinstance(ad, str) or not ad or not isinstance(bilgi, dict):
            return False
        dtype = bilgi.get('dtype')
        shape = bilgi.get('shape')
        ofs = bilgi.get('data_offsets')
        if dtype not in _DTYPE_BAYT:
            return False
        if not isinstance(shape, list) or any(type(d) is not int or d < 0 for d in shape):
            return False
        if not isinstance(ofs, list) or len(ofs) != 2 or any(type(x) is not int for x in ofs):
            return False
        bas, bit = ofs
        beklenen_uzunluk = math.prod(shape) * _DTYPE_BAYT[dtype]
        if bas < 0 or bit < bas or bit > veri_boyutu or (bit - bas) != beklenen_uzunluk:
            return False
        araliklar.append((bas, bit))
    if not araliklar:
        return False
    araliklar.sort()
    imlec = 0
    for bas, bit in araliklar:
        if bas != imlec:
            return False
        imlec = bit
    return imlec == veri_boyutu
```

```test
need('safetensors_baslik_dogrula')
_gecerli = {
    '__metadata__': {'format': 'pt'},
    'w1': {'dtype': 'F32', 'shape': [2, 3], 'data_offsets': [0, 24]},
    'b1': {'dtype': 'F16', 'shape': [3], 'data_offsets': [24, 30]},
}
eq(safetensors_baslik_dogrula(_gecerli, 30), True, 'ardışık, tam eşleşen tensör ofsetleri geçmeli')
eq(safetensors_baslik_dogrula({'skaler': {'dtype': 'I8', 'shape': [], 'data_offsets': [0, 1]}}, 1), True, 'skaler [] shape 1 eleman sayılmalı')

_bozuk_basliklar = [
    ({'__metadata__': {'format': 'pt'}}, 0),
    ({'__metadata__': {'sayi': 1}, 'w': {'dtype': 'I8', 'shape': [1], 'data_offsets': [0, 1]}}, 1),
    ({'w': {'dtype': 'PICKLE', 'shape': [1], 'data_offsets': [0, 4]}}, 4),
    ({'w': {'dtype': 'F32', 'shape': [2, 2], 'data_offsets': [0, 12]}}, 12),
    ({'w1': {'dtype': 'F32', 'shape': [2], 'data_offsets': [0, 8]}, 'w2': {'dtype': 'F32', 'shape': [2], 'data_offsets': [4, 12]}}, 12),
    ({'w1': {'dtype': 'F32', 'shape': [2], 'data_offsets': [0, 8]}}, 10),
    ({'w1': {'dtype': 'F32', 'shape': [True], 'data_offsets': [0, 4]}}, 4),
]
for _b, _boyut in _bozuk_basliklar:
    eq(safetensors_baslik_dogrula(_b, _boyut), False, f'bozuk/örtüşen/eksik başlık reddedilmeli: {_b!r}')

# Her dtype'ın bayt boyutu ayrı ayrı sınanır (BF16 = 2, I32 = 4, I8 = 1).
eq(safetensors_baslik_dogrula({
    'a': {'dtype': 'BF16', 'shape': [3], 'data_offsets': [0, 6]},
    'b': {'dtype': 'I32', 'shape': [2], 'data_offsets': [6, 14]},
    'c': {'dtype': 'I8', 'shape': [2], 'data_offsets': [14, 16]},
}, 16), True, 'BF16/I32/I8 bayt boyutları doğru hesaplanmalı')
# Sıfır elemanlı tensör safetensors'ta geçerlidir: [8, 8] boş aralık.
eq(safetensors_baslik_dogrula({
    'w': {'dtype': 'F32', 'shape': [2], 'data_offsets': [0, 8]},
    'bos': {'dtype': 'F32', 'shape': [0, 4], 'data_offsets': [8, 8]},
}, 8), True, 'sıfır boyutlu (shape içinde 0) tensör geçmeli')

_gecerli_w = {'dtype': 'F32', 'shape': [2], 'data_offsets': [0, 8]}
_tek_kusur = [
    ({'__metadata__': 'pt', 'w': _gecerli_w}, 'metadata dict değil'),
    ({'__metadata__': {1: 'pt'}, 'w': _gecerli_w}, 'metadata anahtarı str değil'),
    ({'': _gecerli_w}, 'boş tensör adı'),
    ({1: _gecerli_w}, 'str olmayan tensör adı'),
    ({'w': ['F32', [2], [0, 8]]}, 'tensör kaydı dict değil'),
    ({'w': {'dtype': 'F32', 'shape': (2,), 'data_offsets': [0, 8]}}, 'shape list değil'),
    ({'w': {'dtype': 'F32', 'shape': [-1, -2], 'data_offsets': [0, 8]}}, 'negatif boyut (çarpım yine 2)'),
    ({'w': {'dtype': 'F32', 'shape': [-1, -1], 'data_offsets': [0, 4]}}, '-1 boyut (çarpım 1)'),
    ({'w': {'dtype': 'F32', 'shape': [2], 'data_offsets': (0, 8)}}, 'data_offsets list değil'),
    ({'w': {'dtype': 'F32', 'shape': [2], 'data_offsets': [0.0, 8.0]}}, 'float ofset'),
    ({'w': {'dtype': 'F32', 'shape': [2], 'data_offsets': [False, 8]}}, 'bool ofset'),
    ({'w': {'dtype': 'F32', 'shape': [2], 'data_offsets': [0, 8, 8]}}, 'üç elemanlı ofset'),
    ({'w': {'dtype': 'F32', 'shape': [2], 'data_offsets': [4, 12]}}, 'boşlukla başlayan aralık'),
]
for _b, _neden in _tek_kusur:
    eq(safetensors_baslik_dogrula(_b, 8 if 'çarpım 1' not in _neden else 4), False, f'tek kusurlu başlık reddedilmeli: {_neden}')

for _hatali in ((None, 10), ({}, -1), ({}, True)):
    raises(ValueError, safetensors_baslik_dogrula, *_hatali, msg='geçersiz üst argüman ValueError fırlatmalı')
```

```hint
Her tensör için `math.prod(shape) * bayt` uzunluğunu `bit - bas` ile eşleştir; ardından tüm `(bas, bit)` çiftlerini sıralayıp `imlec = 0` noktasından `veri_boyutu` sonuna kadar boşluksuz ve örtüşmesiz ilerlediklerini doğrula.
```
:::

::: anlat Bunu iki dakikada nasıl anlatırsın?
1. **Olay bağlamı (15 sn).** "JFrog araştırması, açık model depolarındaki `pickle` ağırlıklarının `torch.load` anında sessiz kod çalıştırabildiğini ve statik tarayıcıları atlatabildiğini gösterdi."
2. **Kök neden (30 sn).** "`pickle` yürütülebilir opkod sanal makinesidir; tarayıcı `'unknown'` veya `'error'` dediğinde yüklemeye izin veren `fail-open` kapılar kırılır."
3. **Sınır ve ölçüm (30 sn).** "`model_kapisi` ile yalnız `safetensors`, `scan == 'clean'`, `hash_uyuyor is True` ve `inceleme is True` şartını koydum; senaryo koşusunda 5/5 saldırı durduruldu."
4. **Yapısal doğrulama (25 sn).** "`safetensors_baslik_dogrula` ile tensör boyutlarının ve `[bas, bit]` bayt ofsetlerinin boşluksuz ve örtüşmesiz olduğunu doğruladım."
5. **Kapanış (20 sn).** "Güvenli model tedarik zinciri, yürütülemez veri biçimi (`safetensors`) + kriptografik özet/imza + hata-kapalı kapı birleşimidir."
:::

::: anlat Sınır ve kaynak
`safetensors` ağırlık yükleme anındaki `pickle` kod yürütme riskini kapatır; ancak model reposundaki `trust_remote_code=True` Python betikleri (`modeling_*.py`) veya ağırlıkların içine gömülmüş davranışsal `backdoor` / `trojan` tetikleyicileri `safetensors` biçiminde de taşınabilir (`ai-guvence-11`, `ai-savunma-36`).

- Birincil kaynak: [JFrog Security Research — Data Scientists Targeted by Malicious Hugging Face ML Models with Silent Backdoor (Şubat 2024)](https://jfrog.com/blog/data-scientists-targeted-by-malicious-hugging-face-ml-models-with-silent-backdoor/). Doğrulama tarihi: 10 Kasım 2026.
:::

::: dusun
`safetensors` kullanan bir ekip model yüklerken `AutoModel.from_pretrained(depo, trust_remote_code=True)` parametresini açık unutursa neden `pickle` kapatılmış olmasına rağmen yine keyfi Python kodu çalışır?
:::

::: ozet
- `pickle` ağırlık dosyaları serileştirme çözme anında keyfi kod çalıştırabilir; statik tarayıcı tek başına garanti vermez.
- Otomatik yükleme kapısı `safetensors` biçimine ve `scan == 'clean'` hata-kapalı (`fail-closed`) kuralına kilitlenir.
- Veri-sadece biçimlerde de başlık ofsetleri ve toplam bayt sınırı yükleme öncesinde doğrulanmalıdır.
:::
